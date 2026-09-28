#!/usr/bin/env python3
"""
KENNZAHLEN-RADAR – Frühwarnsystem für harte Kennzahlen im Blogbestand
(Quick Win H5 aus der Konkurrenz-Analyse Finanztip, 28.09.2026)

WARUM: Finanztip baut laut Stellenanzeige eine KI-gestützte
„Änderungserkennung“ für Produkt-/Konditionsdaten (Rolle „Product
Data & AI Automation Manager“). Dieses Skript ist das Pendant für
FranksFinanzcheck – ohne Personal, ohne Paid-API, ohne Netz:

  1. FÄLLIGKEIT:   Welche Kennzahlen aus data/kennzahlen_register.yaml
                   sind über ihrem Prüfintervall (rhythmus_tage)?
  2. BRIEF-SIGNAL: Erwähnt ein Agent-Reach-Recherche-Brief
                   (data/research/*.md, data/research/artikel/*.md)
                   ein Suchwort der Kennzahl – und ist der Brief NEUER
                   als der letzte Prüfstand? → Frühwarnung vor Fälligkeit.
  3. ARTIKEL-KOPPLUNG: Welche betroffenen Artikel haben ein lastmod,
                   das ÄLTER ist als der Kennzahlenstand? Deren Zahlen
                   spiegeln den neuesten Stand vermutlich nicht.

WAS ER NICHT TUT (Vertrag, wie faktenfrische.py):
  * Er schreibt NIE das Register (menschlich kuratierte SSOT).
  * Er ändert NIE Artikeltexte – Befunde gehen als Report/Issue
    an einen Menschen (KI-Redaktions-Statut, CLAUDE.md).
  * Er ruft NIE das Netz auf – Signale kommen aus den lokalen
    Agent-Reach-Briefs, die ohnehin wöchentlich entstehen.

AUSGABE:
  KENNZAHLEN-RADAR.md            – Chefredakteur-Report
  data/kennzahlen_radar.json     – maschinenlesbare Queue (P1/P2)
  --issue                        – Issue-Body auf stdout
  --selftest                     – eingefrorene Fälle (Regression)

Exit-Codes: 0 = alles grün · 1 = fällige Kennzahlen (Handlung nötig)
            2 = Selftest fehlgeschlagen / Register ungültig.

Nutzung:
  python3 scripts/kennzahlen_radar.py
  python3 scripts/kennzahlen_radar.py --issue
  python3 scripts/kennzahlen_radar.py --as-of 2026-11-15   # Forecast
  python3 scripts/kennzahlen_radar.py --selftest
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_PATH = os.path.join(BLOG_DIR, "data", "kennzahlen_register.yaml")
ALLOWLIST_PATH = os.path.join(BLOG_DIR, "data", "agent_reach", "faktenfrische.yaml")
RESEARCH_DIRS = (
    os.path.join(BLOG_DIR, "data", "research"),
    os.path.join(BLOG_DIR, "data", "research", "artikel"),
)
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
PILLAR_DIR = os.path.join(BLOG_DIR, "content", "pillar")
REPORT_PATH = os.path.join(BLOG_DIR, "KENNZAHLEN-RADAR.md")
QUEUE_PATH = os.path.join(BLOG_DIR, "data", "kennzahlen_radar.json")

try:
    import yaml  # pyyaml: auch CI-Dependency (faktenfrische.yml)
except ImportError:  # pragma: no cover
    print("❌ pyyaml fehlt: python3 -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

_ISO_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
_ISO_IN_TEXT = re.compile(r"(\d{4}-\d{2}-\d{2})")


# ------------------------------------------------------------ Helfer


def _parse_date(value, fallback=None):
    if not value:
        return fallback
    s = str(value).strip().strip('"').strip("'")
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return datetime.date.fromisoformat(m.group(1))
        except ValueError:
            return fallback
    return fallback


def _resolve_as_of():
    """`--as-of YYYY-MM-DD` (Forecast) sonst heute."""
    for i, arg in enumerate(sys.argv):
        if arg == "--as-of" and i + 1 < len(sys.argv):
            d = _parse_date(sys.argv[i + 1])
            if not d:
                raise SystemExit(f"❌ --as-of braucht YYYY-MM-DD, erhielt: {sys.argv[i+1]}")
            return d
    return datetime.date.today()


def _article_path(base_dir, slug):
    """Slug -> Dateipfad. 'pillar/xyz' = Ratgeber-Seite, sonst Post."""
    if slug.startswith("pillar/"):
        return os.path.join(base_dir, "content", "pillar", slug[len("pillar/"):], "index.md")
    return os.path.join(base_dir, "content", "posts", slug, "index.md")


def _article_dates(path):
    """lastmod/date/Titel leichtgewichtig aus dem Frontmatter lesen."""
    out = {"title": "", "lastmod": None, "date": None}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read(20000)
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1]
    for key in ("title", "lastmod", "date"):
        m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
        if m:
            val = m.group(1).strip().strip('"').strip("'")
            if key == "title":
                out["title"] = val
            else:
                out[key] = _parse_date(val)
    out["ref"] = out["lastmod"] or out["date"]
    return out


# ------------------------------------------------------------ Laden + Validieren


def load_allowlist(path=ALLOWLIST_PATH):
    """Beleg-Allowlist (Domain -> Rang) aus faktenfrische.yaml – nur lesend."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {e.get("domain"): e.get("rang") for e in (data.get("quellen_allowlist") or [])}


def load_register(path=REGISTER_PATH):
    """Register laden + hart validieren. Rückgabe: (meta, eintraege, fehler[])."""
    fehler = []
    if not os.path.exists(path):
        return {}, [], [f"Register fehlt: {path}"]
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    meta = data.get("meta") or {}
    eintraege = data.get("kennzahlen") or []
    if not eintraege:
        fehler.append("Register enthält keine Kennzahlen (`kennzahlen:` ist leer).")

    ids, domains = set(), {}
    allowlist = load_allowlist()
    for i, e in enumerate(eintraege):
        kid = e.get("id") or f"eintrag-{i}"
        if e.get("id") in ids:
            fehler.append(f"[{kid}] Doppelte id.")
        ids.add(e.get("id"))
        if not _parse_date(e.get("stand")):
            fehler.append(f"[{kid}] `stand` fehlt oder ist kein Datum (YYYY-MM-DD).")
        if not isinstance(e.get("rhythmus_tage"), int) or e.get("rhythmus_tage", 0) <= 0:
            fehler.append(f"[{kid}] `rhythmus_tage` muss eine positive Ganzzahl sein.")
        if not e.get("suchbegriffe"):
            fehler.append(f"[{kid}] `suchbegriffe` fehlen (Brief-Matching unmöglich).")
        url = ((e.get("quelle") or {}).get("url") or "")
        m = re.match(r"https?://([^/]+)", url)
        domain = m.group(1).lower().removeprefix("www.") if m else ""
        domains[kid] = domain
        if not domain:
            fehler.append(f"[{kid}] `quelle.url` fehlt.")
        elif allowlist and domain not in allowlist:
            fehler.append(
                f"[{kid}] Quelldomain '{domain}' steht NICHT auf der Beleg-"
                f"Allowlist (data/agent_reach/faktenfrische.yaml). "
                f"Affiliate-Partner sind als Kennzahlenquelle verboten."
            )
        if not e.get("betroffene_slugs"):
            fehler.append(f"[{kid}] `betroffene_slugs` fehlen.")
    return meta, eintraege, fehler


# ------------------------------------------------------------ Brief-Signale


def _research_files(base_dir):
    """Alle Recherche-Briefs (wöchentlich + Faktenfrische-Dossiers)."""
    out = []
    for d in (
        os.path.join(base_dir, "data", "research"),
        os.path.join(base_dir, "data", "research", "artikel"),
    ):
        out += sorted(glob.glob(os.path.join(d, "*.md")))
    return out


def _research_date(path):
    """Datum eines Briefs: erst Dateiname (2026-09-21-…), sonst erste
    ISO-Datumszeile im Kopf („Automatisch erzeugt … am 2026-09-27“)."""
    m = _ISO_IN_NAME.search(os.path.basename(path))
    if m:
        return _parse_date(m.group(1))
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(3000)
    except OSError:
        return None
    m = _ISO_IN_TEXT.search(head)
    return _parse_date(m.group(1)) if m else None


def scan_signale(base_dir, suchbegriffe, stand, as_of):
    """Sucht Briefs nach Begriffen; zählt nur Treffer NEUER als `stand`.

    Ein Brief, der älter ist als der letzte Prüfstand, hat seine
    Information (per Definition) bereits eingebracht – kein Frühwarn-Signal.
    """
    signale = []
    for path in _research_files(base_dir):
        datum = _research_date(path)
        if not datum or not (stand < datum <= as_of):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read().lower()
        except OSError:
            continue
        treffer = sorted({b for b in suchbegriffe if b.lower() in text})
        if treffer:
            signale.append({
                "datei": os.path.relpath(path, base_dir),
                "datum": datum.isoformat(),
                "begriffe": treffer,
            })
    signale.sort(key=lambda s: s["datum"], reverse=True)
    return signale


# ------------------------------------------------------------ Bewertung


def _status(faellig, signale):
    if faellig and signale:
        return "P1", "AKTION (fällig + neues Brief-Signal)"
    if faellig:
        return "P2", "FÄLLIG (Prüfintervall überschritten)"
    if signale:
        return "P3", "SIGNAL (Brief erwähnt Änderung, Prüfung vorziehen)"
    return "OK", "im Rhythmus"


def bewerte(base_dir, eintraege, as_of, slug_check=True):
    """Kern: Bewertung je Kennzahl inkl. Artikel-Kopplung."""
    regeln = []
    for e in eintraege:
        kid = e.get("id", "?")
        stand = _parse_date(e.get("stand")) or as_of
        rhythmus = int(e.get("rhythmus_tage") or 1)
        alter = (as_of - stand).days
        faellig = alter > rhythmus
        signale = scan_signale(base_dir, e.get("suchbegriffe") or [], stand, as_of)

        artikel = []
        for slug in e.get("betroffene_slugs") or []:
            path = _article_path(base_dir, slug)
            info = _article_dates(path) if os.path.exists(path) else None
            if info is None:
                if slug_check:
                    artikel.append({"slug": slug, "problem": "Slug nicht gefunden"})
                continue
            eintrag = {
                "slug": slug,
                "titel": info.get("title") or slug,
                "lastmod": info["ref"].isoformat() if info.get("ref") else None,
            }
            # Artikel älter als der geprüfte Kennzahlenstand?
            if info.get("ref") and info["ref"] < stand:
                eintrag["hinterher"] = (
                    f"Artikel-Stand {info['ref'].isoformat()} liegt VOR dem "
                    f"Kennzahlenstand {stand.isoformat()} – Zahlen ggf. veraltet"
                )
            artikel.append(eintrag)

        prio, status = _status(faellig, signale)
        if e.get("ymyl") and prio in ("P1", "P2"):
            prio = prio  # P1/P2 sind bereits Eskalationsstufen; ymyl nur im Report
        regeln.append({
            "id": kid,
            "name": e.get("name") or kid,
            "einheit": e.get("einheit") or "",
            "ist_wert": e.get("ist_wert"),
            "stand": stand.isoformat(),
            "rhythmus_tage": rhythmus,
            "alter_tage": alter,
            "ymyl": bool(e.get("ymyl")),
            "quelle": (e.get("quelle") or {}).get("name") or "",
            "quelle_url": (e.get("quelle") or {}).get("url") or "",
            "signale": signale,
            "artikel": artikel,
            "prioritaet": prio,
            "status": status,
        })
    order = {"P1": 0, "P2": 1, "P3": 2, "OK": 3}
    regeln.sort(key=lambda r: (order[r["prioritaet"]], -r["alter_tage"]))
    return regeln


def flag_action(regeln):
    return any(r["prioritaet"] in ("P1", "P2") for r in regeln)


# ------------------------------------------------------------ Ausgaben


def render_report(regeln, as_of, fehler=()):
    p1 = [r for r in regeln if r["prioritaet"] == "P1"]
    p2 = [r for r in regeln if r["prioritaet"] == "P2"]
    p3 = [r for r in regeln if r["prioritaet"] == "P3"]
    ok = [r for r in regeln if r["prioritaet"] == "OK"]

    def block(sub, emoji):
        if not sub:
            return "_Keine_\n"
        out = []
        for r in sub:
            wert = f" ({r['ist_wert']} {r['einheit']})" if r.get("ist_wert") else ""
            out.append(f"### {emoji} {r['name']}{wert}")
            out.append(f"- **Prüfstand:** {r['stand']} · **Intervall:** {r['rhythmus_tage']} d "
                       f"· **Alter:** {r['alter_tage']} d{' · **YMYL**' if r['ymyl'] else ''}")
            out.append(f"- **Quelle:** [{r['quelle']}]({r['quelle_url']})" if r["quelle_url"]
                       else "- **Quelle:** –")
            for s in r["signale"][:3]:
                out.append(f"- 📡 **Brief-Signal:** {s['datei']} ({s['datum']}) – "
                           f"Treffer: {', '.join(s['begriffe'][:5])}")
            if r["artikel"]:
                for a in r["artikel"]:
                    if "problem" in a:
                        out.append(f"- ⚠️ `{a['slug']}`: {a['problem']}")
                    elif a.get("hinterher"):
                        out.append(f"- 🕰️ `{a['slug']}`: {a['hinterher']}")
            out.append("")
        return "\n".join(out) + "\n"

    lines = [
        "# 📡 Kennzahlen-Radar (Frühwarnung)",
        f"**Stand:** {as_of.isoformat()} · **Auftrag:** Veränderungen früher erkennen "
        "(Konkurrenz-Parität Finanztip, H5)",
        "",
        f"- 🔴 **P1 – AKTION** (fällig + neues Brief-Signal): **{len(p1)}**",
        f"- 🟠 **P2 – FÄLLIG** (Prüfintervall überschritten): **{len(p2)}**",
        f"- 🟡 **P3 – SIGNAL** (Brief erwähnt Änderung): **{len(p3)}**",
        f"- 🟢 **OK** (im Rhythmus): **{len(ok)}**",
        "",
    ]
    if fehler:
        lines += ["---", "", "## ⛔ Register-Fehler (vor allem anderen fixen)", ""]
        lines += [f"- {f}" for f in fehler]
        lines += [""]
    lines += [
        "---", "",
        "## 🔴 P1 – sofort prüfen",
        block(p1, "🔴"),
        "",
        "## 🟠 P2 – fällig",
        block(p2, "🟠"),
        "",
        "## 🟡 P3 – Signale beobachten",
        block(p3, "🟡"),
        "",
        "---",
        "",
        "### Nächste Schritte (Chefredakteur)",
        "",
        "1. **P1 zuerst:** Brief-Signal lesen (`data/research/…`), neuen Wert an der",
        "   Quelle prüfen, dann `ist_wert` + `stand` im Register von Hand aktualisieren",
        "   (Register ist menschlich kuratiert – die Maschine schreibt es nie).",
        "2. **Artikel hinterherhängend:** Zahlen im Artikel aktualisieren, danach",
        "   `scripts/set_lastmod.py --git-changed` laufen lassen.",
        "3. **Recherche anstoßen:** `python3 scripts/faktenfrische.py --apply --max 3`",
        "   frischt die Belegketten (`quellen`/`faktencheck`) der betroffenen Artikel auf.",
        "",
        f"_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am {as_of.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"


def write_queue(regeln, as_of, path=QUEUE_PATH):
    """P1/P2 als maschinenlesbare Queue (analog data/decay_queue.json)."""
    queue = [r for r in regeln if r["prioritaet"] in ("P1", "P2")]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"generated": as_of.isoformat(), "count": len(queue), "queue": queue},
                  f, ensure_ascii=False, indent=2)
    return queue


def issue_body(regeln, as_of, fehler=()):
    p1 = [r for r in regeln if r["prioritaet"] == "P1"]
    p2 = [r for r in regeln if r["prioritaet"] == "P2"]
    body = [
        "## 📡 Kennzahlen-Radar: Diese Werte brauchen eine Prüfung",
        "",
        f"**{len(p1)} P1 (fällig + Brief-Signal)** · **{len(p2)} P2 (fällig)** "
        f"(Stand: {as_of.isoformat()})",
        "",
    ]
    if fehler:
        body += ["### ⛔ Register-Fehler", ""]
        body += [f"- {f}" for f in fehler]
        body += [""]
    for r in p1 + p2:
        sig = f" · Signal: {', '.join(r['signale'][0]['begriffe'][:3])}" if r["signale"] else ""
        body.append(f"- **{r['name']}** – Stand {r['stand']} ({r['alter_tage']} d alt, "
                    f"Intervall {r['rhythmus_tage']} d){sig}")
        for a in r["artikel"]:
            if "problem" in a:
                body.append(f"  - ⚠️ `{a['slug']}`: {a['problem']}")
            elif a.get("hinterher"):
                body.append(f"  - 🕰️ `{a['slug']}`: {a['hinterher']}")
    body += [
        "",
        "> **Ablauf:** Quelle prüfen → `ist_wert`/`stand` im Register von Hand "
        "aktualisieren → betroffene Artikelzahlen aktualisieren → "
        "`scripts/set_lastmod.py --git-changed`. Der Radar schreibt das Register "
        "nie selbst (menschlich kuratierte SSOT).",
        "",
        "---",
        "_Automatisch vom Kennzahlen-Radar. Kein Artikel wurde geändert._",
    ]
    return "\n".join(body)


# ------------------------------------------------------------ Selftest


def selftest():
    """Eingefrorene Fälle (kein Netz, keine echten Pfade)."""
    import tempfile

    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + name)
        ok = ok and bool(cond)

    with tempfile.TemporaryDirectory() as tmp:
        # Gerüst: 1 Post, 1 Pillar, 1 Brief (neu), 1 Brief (alt)
        os.makedirs(os.path.join(tmp, "content", "posts", "post-a"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "content", "pillar", "strom"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "data", "research"), exist_ok=True)
        with open(os.path.join(tmp, "content", "posts", "post-a", "index.md"), "w",
                  encoding="utf-8") as f:
            f.write("---\ntitle: \"Post A\"\nlastmod: 2026-08-01\ndate: 2026-07-01\n---\nText")
        with open(os.path.join(tmp, "content", "pillar", "strom", "index.md"), "w",
                  encoding="utf-8") as f:
            f.write("---\ntitle: \"Strom-Ratgeber\"\nlastmod: 2026-09-20\n---\nText")
        with open(os.path.join(tmp, "data", "research", "2026-09-21-internet-recherche.md"),
                  "w", encoding="utf-8") as f:
            f.write("# Brief\n\nDer Strompreis steigt laut BDEW auf 40 ct/kWh.\n")
        with open(os.path.join(tmp, "data", "research", "2026-07-01-internet-recherche.md"),
                  "w", encoding="utf-8") as f:
            f.write("# Alter Brief\n\nStrompreis Altmodung (darf kein Signal sein).\n")

        as_of = datetime.date(2026, 9, 28)
        eintraege = [{
            "id": "k1", "name": "Strompreis", "einheit": "ct/kWh",
            "ist_wert": "37,0", "stand": datetime.date(2026, 8, 21),
            "quelle": {"name": "BDEW", "url": "https://www.bdew.de/x"},
            "rhythmus_tage": 30, "ymyl": True,
            "suchbegriffe": ["Strompreis", "BDEW"],
            "betroffene_slugs": ["post-a", "pillar/strom"],
        }, {
            "id": "k2", "name": "Evergreen", "einheit": "",
            "ist_wert": None, "stand": datetime.date(2026, 9, 25),
            "quelle": {"name": "VZ", "url": "https://www.verbraucherzentrale.de/x"},
            "rhythmus_tage": 365, "ymyl": False,
            "suchbegriffe": ["Girokonto"],
            "betroffene_slugs": ["post-a"],
        }]

        regeln = bewerte(tmp, eintraege, as_of, slug_check=False)
        by_id = {r["id"]: r for r in regeln}

        check("P1: fällig (38 d > 30 d) + neues Brief-Signal",
              by_id["k1"]["prioritaet"] == "P1")
        check("Signal verweist auf den neuen Brief, nicht den alten",
              any("2026-09-21" in s["datum"] for s in by_id["k1"]["signale"]) and
              all("2026-07-01" not in s["datum"] for s in by_id["k1"]["signale"]))
        check("Artikel-Kopplung: post-a (08-01) hinkt Stand 08-21 hinterher",
              any(a.get("hinterher") for a in by_id["k1"]["artikel"]
                  if a["slug"] == "post-a"))
        check("Pillar (09-20) hinkt NICHT hinterher",
              not any(a.get("hinterher") for a in by_id["k1"]["artikel"]
                      if a["slug"] == "pillar/strom"))
        check("OK: Kennzahl im Rhythmus (3 d < 365 d)",
              by_id["k2"]["prioritaet"] == "OK")

        # Slug-Validierung
        regeln_x = bewerte(tmp, [{**eintraege[0], "betroffene_slugs": ["gibts-nicht"]}],
                           as_of, slug_check=True)
        check("Unbekannter Slug wird als Problem markiert",
              any("problem" in a for a in regeln_x[0]["artikel"]))

        # Report + Queue + Issue
        rep = render_report(regeln, as_of)
        check("Report enthält P1-Kennzahl", "Strompreis" in rep and "P1" in rep)
        q = write_queue(regeln, as_of, path=os.path.join(tmp, "q.json"))
        check("Queue enthält nur P1/P2", {r["prioritaet"] for r in q} <= {"P1", "P2"})
        ib = issue_body(regeln, as_of)
        check("Issue-Body nennt Ablauf-Vertrag", "nie selbst" in ib)

        # Allowlist-Verstoß
        _, _, fehler = load_register(path=os.path.join(tmp, "reg.yaml")) if False else ({}, [], [])
        # (load_register-Validierung wird über einen echten Register-Pfad geprüft:)
        reg_bad = os.path.join(tmp, "reg_bad.yaml")
        with open(reg_bad, "w", encoding="utf-8") as f:
            f.write(
                "meta: {version: 1}\n"
                "kennzahlen:\n"
                "  - id: bad\n"
                "    name: Schlechte Quelle\n"
                "    stand: 2026-09-01\n"
                "    quelle: {name: Partner, url: 'https://check24.net/x'}\n"
                "    rhythmus_tage: 30\n"
                "    suchbegriffe: [Strom]\n"
                "    betroffene_slugs: [post-a]\n"
            )
        # Allowlist ins Temp-Verzeichnis legen, damit die Prüfung dort liest
        os.makedirs(os.path.join(tmp, "data", "agent_reach"), exist_ok=True)
        with open(os.path.join(tmp, "data", "agent_reach", "faktenfrische.yaml"), "w",
                  encoding="utf-8") as f:
            f.write("quellen_allowlist:\n  - {domain: bdew.de, rang: 2}\n")
        global ALLOWLIST_PATH
        old = ALLOWLIST_PATH
        ALLOWLIST_PATH = os.path.join(tmp, "data", "agent_reach", "faktenfrische.yaml")
        try:
            _, _, fehler = load_register(reg_bad)
            check("Allowlist-Verstoß (Affiliate-Domain) wird erkannt",
                  any("Allowlist" in f for f in fehler))
        finally:
            ALLOWLIST_PATH = old

    print("\n" + ("✅ SELFTEST OK" if ok else "❌ SELFTEST FEHLGESCHLAGEN"))
    return ok


# ------------------------------------------------------------ Main


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 2)

    as_of = _resolve_as_of()
    meta, eintraege, fehler = load_register()
    if fehler:
        print("⛔ REGISTER UNGÜLTIG – der Radar läuft nicht gegen ein kaputtes Register:")
        for f in fehler:
            print(f"  - {f}")
        sys.exit(2)

    regeln = bewerte(BLOG_DIR, eintraege, as_of)
    report = render_report(regeln, as_of)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    queue = write_queue(regeln, as_of)

    print(report)
    print(f"→ Report: {os.path.relpath(REPORT_PATH, BLOG_DIR)} · "
          f"Queue: {os.path.relpath(QUEUE_PATH, BLOG_DIR)} ({len(queue)} P1/P2)")

    if "--issue" in sys.argv:
        print("\n" + "=" * 60 + " ISSUE-BODY " + "=" * 60 + "\n")
        print(issue_body(regeln, as_of))

    sys.exit(1 if flag_action(regeln) else 0)


if __name__ == "__main__":
    main()
