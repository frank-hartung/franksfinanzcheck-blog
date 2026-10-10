#!/usr/bin/env python3
"""
OFFLINE-MESSIMPORT – der dritte Weg in die Umsatz-Messkette (Manuelle Messstände)

WARUM: Die Messkette ist gebaut, aber ihre einzige Datenbrücke ist die
Umami-API – und die liegt im Free-Plan nicht frei (`data/monetization.yaml:
umami_api_import_enabled: false`, `docs/UMSATZ-MESSUNG-PREMIUM.md §2`).
Ergebnis: `data/revenue_funnel.json` meldet seit Bestehen durchgehend
`null` – „unbekannt“ statt Messwert. Zwei Wege zum Ziel kannte das Repo
bisher: API-Token (kostet) oder nichts tun. Dieser Import ist der dritte:
**Zahlen, die im Dashboard längst sichtbar sind, kommen per Datei hinein**
(Export aus dem Umami-Dashboard oder ein von Hand gepflegtes JSON).

DIESES SKRIPT:
  1. Liest eine Messstand-Datei (JSON oder CSV) aus `data/offline/`.
  2. Normalisiert Pfade und Event-Attribute genauso wie die API-Importe (eine Wahrheit,
     kein zweites Regelwerk): Query/Fragment runter, keine IPs, keine Mails.
  3. Schreibt die drei Import-Ziele der Kette – `data/umami_views.json`,
     `data/umami_clicks.json`, `data/umami_ctas.json`. API-Eigene Meta-Dateien
     (`data/umami_*.meta.json`) bleiben den API-Skripten überlassen; dieser
     Import führt seine eigene Provenienz in `data/offline_import.meta.json`
     (`status: ok`, `import: offline`, Modus, Zeitzähler). So kann niemand eine
     API-Messung vortäuschen, die nie stattgefunden hat.
  4. Füttert zusätzlich die Provisions-Monatssummen (Partnerabrechnungen, lokal
     unter `data/provisionen/provisionen.csv`) in `data/provisionen_aggregat.json` –
     die einzige Provisions-Wahrheit, die ohne Netz-Pipeline existiert.

EHRLICHE REGELN (Hausrecht der Messkette, identisch zu umami_clicks.py):
  - Datei fehlt/leer ⇒ es wird NIX geschrieben, Exit 0, Hinweis. Ein
    ausgelassener Manuell-Import darf nie wie „0 Besuche“ aussehen.
  - Nur Aggregat je Pfad im Repo – keine IPs, keine Sitzungen, keine
    Adressen. Zeilen mit Personenbezug werden verworfen, nicht gefixt.
  - Standard ersetzt die Zeilen dieses Importlaufs (Dashboard-Export = volles
    Fenster); `--merge` summiert Teilimporte auf. Zeilen einer aktiven API-
    Brücke bleiben in beiden Fällen stehen – die API ist die bessere Wahrheit.

Nutzung:
  python3 scripts/offline_import.py --template        # Gerüst nach data/offline/messstand.json
  python3 scripts/offline_import.py                   # importieren + Trichter neu rechnen
  python3 scripts/offline_import.py --datei pfad.json # andere Datei
  python3 scripts/offline_import.py --dry-run         # zeigen, was passieren würde
  python3 scripts/offline_import.py --status          # Stand der Messkette
  python3 scripts/offline_import.py --selftest

Exit-Codes: 0 = importiert oder sauber übersprungen, 1 = Datei unlesbar,
             2 = Selbsttest/Hausfehler.
Runbook: docs/UMSATZ-MESSUNG-PREMIUM.md (Abschnitt 5a, „Weg 3“) – oder kurz:
`npm run mess:vorlage` → Datei ausfüllen → `npm run mess:import`.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

DATA = os.path.join(BLOG_DIR, "data")
OFFLINE_DIR = os.path.join(DATA, "offline")
STANDARD_DATEI = os.path.join(OFFLINE_DIR, "messstand.json")

VIEWS = os.path.join(DATA, "umami_views.json")
VIEWS_META = os.path.join(DATA, "umami_views.meta.json")
CLICKS = os.path.join(DATA, "umami_clicks.json")
CLICKS_META = os.path.join(DATA, "umami_clicks.meta.json")
CTAS = os.path.join(DATA, "umami_ctas.json")
CTAS_META = os.path.join(DATA, "umami_ctas.meta.json")
PROVISIONEN = os.path.join(DATA, "provisionen", "provisionen.csv")
# Aggregat der Monatssummen – die einzige Provisions-Datei, die versioniert
# werden darf (keine Abrechnungs-Details, keine Personenbezüge).
PROVISIONEN_AGG = os.path.join(DATA, "provisionen_aggregat.json")
# Eigene Meta der manuellen Brücke: sie dokumentiert den Import, OHNE die
# API-Meta der Umami-Skripte zu überschreiben (die gehören denen allein).
OFFLINE_META = os.path.join(DATA, "offline_import.meta.json")

TODAY = datetime.date.today()
MAX_PATH = 160
MAX_ROWS = 2000
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

# Die Trichter-Rechnung (Pfad-Brücke Klick↔Seite) hat revenue_funnel.py – sie
# wird wiederverwendet, nicht kopiert. Ohne das Modul (z. B. in einer Test-
# Sandbox) gilt ein deutlich engeres Fallback, damit nichts erfunden wird.
try:
    from revenue_funnel import article_to_path, kaufnahe_paths, norm_path_ok  # type: ignore
except Exception:  # noqa: BLE001
    article_to_path = None  # type: ignore
    kaufnahe_paths = None  # type: ignore
    norm_path_ok = None  # type: ignore


# ------------------------------------------------------------------ Normalisieren

def norm_path(raw) -> str:
    """/posts/x/?utm=1 → /posts/x/ – identische Normalisierung wie umami_views.py.

    Query/Fragment runter (UTM-Kanäle dürfen dieselbe Seite nicht spalten),
    fehlende Schrägstriche ergänzen, Domain kappen. Alles, was nach
    Personenbezug oder Code aussieht, wird zu '' (Zeile fällt raus).
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    if EMAIL_RE.search(s) or IPV4_RE.search(s):
        return ""
    if s.startswith(("http://", "https://")):
        s = s.split("://", 1)[1]
        s = "/" + s.split("/", 1)[1] if "/" in s else "/"
    s = s.split("?", 1)[0].split("#", 1)[0]
    if not s.startswith("/"):
        s = "/" + s
    if not s.endswith("/"):
        s += "/"
    if re.search(r"[\x00-\x1f\"'<>\\]", s):
        return ""
    return s[:MAX_PATH]


def norm_article(raw) -> str:
    """Umami-`article`-Attribut → Blog-Pfad. Bewusst eng: was nicht zu den
    bekannten Sektionen gehört, wird zu '' (landet in „sonstiges“, erfindet
    keine Seite)."""
    s = str(raw or "").strip().strip("/")
    if not s or EMAIL_RE.search(s) or IPV4_RE.search(s):
        return ""
    if article_to_path is not None:
        try:
            return article_to_path(s)
        except Exception:  # noqa: BLE001
            return ""
    m = re.match(r"^posts/(.+?)(?:/index\.md|\.md)?$", s)
    if m:
        return f"/posts/{m.group(1)}/"
    m = re.match(r"^pillar/(.+?)(?:/index\.md|\.md)?$", s)
    if m:
        return f"/pillar/{m.group(1)}/" if m.group(1) != "_index" else "/pillar/"
    if s in ("home", "start", ""):
        return "/"
    return ""


def to_int(v, default=0) -> int:
    try:
        n = int(float(str(v).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return default
    return max(0, min(10 ** 9, n))


# ------------------------------------------------------------------ Eingabe-Formate

def from_json(obj: dict) -> dict:
    """Messstand-JSON → {views, totals, clicks, ctas, window}.

    Akzeptiert bewusst drei Schreibweisen: (a) das eigene Gerüst, (b) den
    API-Export `{"pages": [{"url": …, "pageViews": …}]}`, (c) schlanze
    Handarbeit `{"views": [{"/posts/x/": 12}]}`.
    """
    out = {"views": {}, "totals": {}, "clicks": [], "ctas": [], "window": {}}
    if not isinstance(obj, dict):
        return out

    win = obj.get("window") or {}
    if isinstance(win, dict):
        for k in ("start", "ende"):
            v = str(win.get(k) or "")[:10]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                out["window"][k] = v
        if isinstance(win.get("tage"), int):
            out["window"]["days"] = max(1, min(365, win["tage"]))

    # --- totals: {"besuche": , "aufrufe": } oder {visits, pageviews}
    tot = obj.get("totals") or obj.get("gesamt") or {}
    if isinstance(tot, dict):
        out["totals"] = {
            "visits": to_int(tot.get("besuche", tot.get("visits"))),
            "pageviews": to_int(tot.get("aufrufe", tot.get("pageviews", tot.get("views")))),
        }

    # --- Seiten: Liste von Objekten ODER Pfad→Zahl-Dict
    rows = obj.get("views") or obj.get("pages") or []
    if isinstance(rows, dict):
        rows = [{"path": k, "views": v} for k, v in rows.items()]
    if isinstance(rows, list):
        for item in rows[:MAX_ROWS]:
            if not isinstance(item, dict):
                continue
            path = norm_path(item.get("pfad") or item.get("path") or item.get("url")
                             or item.get("seite") or item.get("title") or "")
            if not path:
                continue
            d = out["views"].setdefault(path, {"path": path, "views": 0, "visits": 0})
            d["views"] += to_int(item.get("aufrufe", item.get("pageViews", item.get("views"))))
            d["visits"] += to_int(item.get("besuche", item.get("visits", d["views"])))

    # --- Events: klicks[] (Aggregat) oder events[] (Einzelsätze)
    for key, target in (("klicks", "clicks"), ("events", "clicks"), ("ctas", "ctas")):
        block = obj.get(key) or []
        if isinstance(block, dict):
            block = [{"count": v, "slug": k} for k, v in block.items()]
        if not isinstance(block, list):
            continue
        for item in block[:MAX_ROWS]:
            if not isinstance(item, dict):
                continue
            ev = str(item.get("event") or "").strip()[:60]
            row = {
                "event": ev or ("affiliate_click" if target == "clicks" else "cta_click"),
                "slug": str(item.get("slug") or "")[:80],
                "article": str(item.get("article") or "")[:80],
                "pillar": str(item.get("pillar") or "")[:60],
                "count": to_int(item.get("zahl", item.get("count")), default=1),
            }
            if key == "events":
                # props-Variante wie im API-Export: {"type": …, "x": 12}
                props = item.get("eventProps") or item.get("props") or {}
                if isinstance(props, dict):
                    for pk in ("slug", "article", "pillar"):
                        if props.get(pk):
                            row[pk] = str(props[pk])[:80]
                if item.get("type"):
                    row["event"] = str(item["type"])[:60]
            if row["event"] in ("affiliate_click", "cta_click"):
                out[target].append(row)
    return out


def _pick(row: dict, *keys):
    for k in keys:
        for rk in row:
            if rk.strip().lower().replace(" ", "") == k:
                v = row[rk]
                if v not in (None, ""):
                    return v
    return ""


def from_csv(text: str, typ: str = "views") -> dict:
    """CSV-Export aus dem Umami-Dashboard (Seiten ODER Events) → Messstand.

    `typ: "views"`  → Spalten url|path|seite + pageViews|views|aufrufe + visits|besuche
    `typ: "events"` → Spalten event|type + slug + article + pillar; Zeilen ohne
                      `count`-Spalte zählen als Einzelsatz (1 Klick je Zeile).
    """
    out = {"views": {}, "totals": {}, "clicks": [], "ctas": [], "window": {}}
    try:
        sample = text[:8192]
        delim = "," if sample.count(",") >= sample.count(";") else ";"
        rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    except (csv.Error, UnicodeDecodeError):
        return out
    for row in rows[:MAX_ROWS]:
        if not isinstance(row, dict):
            continue
        if typ == "events":
            ev = str(_pick(row, "event", "type", "ereignis")).strip()[:60]
            if ev not in ("affiliate_click", "cta_click"):
                continue
            target = "ctas" if ev == "cta_click" else "clicks"
            out[target].append({
                "event": ev,
                "slug": str(_pick(row, "slug", "subid"))[:80],
                "article": str(_pick(row, "article", "artikel", "path", "url"))[:80],
                "pillar": str(_pick(row, "pillar"))[:60],
                "count": to_int(_pick(row, "count", "total", "zahl"), default=1) or 1,
            })
            continue
        path = norm_path(_pick(row, "url", "path", "seite", "page", "title"))
        if not path:
            continue
        views = to_int(_pick(row, "pageviews", "views", "aufrufe", "total"))
        visits = to_int(_pick(row, "visits", "besuche", "uniquevisitors")) or views
        if not views and not visits:
            continue
        d = out["views"].setdefault(path, {"path": path, "views": 0, "visits": 0})
        d["views"] += views
        d["visits"] += visits
    return out


def read_file(path: str) -> tuple[dict, str]:
    """→ (messstand, quelle). Leere/nicht existierende Datei → ({}, pfad)."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return {}, path
    if not text.strip():
        return {}, path
    if path.lower().endswith(".csv"):
        typ = "events" if re.search(r"(?i)\bevent\b", text[:512]) else "views"
        return from_csv(text, typ=typ), path
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}, path
    # Ein Combini-Format: {"views": …, "events": …} oder mehrere CSV-Blöcke
    return from_json(obj if isinstance(obj, dict) else {}), path


# ------------------------------------------------------------------ Provisions-Tabelle

def read_provisionen(path: str | None = None) -> dict:
    """Monatssummen der Partnerabrechnungen → Provision TRUE für den Trichter.

    Die Datei ist bewusst NICHT versioniert (`data/provisionen/provisionen.csv`
    liegt nur lokal, Schema + Prüfung: `scripts/provisionen_check.py`).
    Unbekannt bleibt unbekannt: fehlt die Datei, liefert das {} – der Trichter
    schreibt dann nirgends eine 0 hin.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return {}
    zeilen = []
    try:
        for row in csv.DictReader(io.StringIO(text)):
            monat = str(row.get("monat") or "").strip()
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", monat):
                continue
            provision = str(row.get("provision_eur") or "0").strip().replace(",", ".")
            if not re.fullmatch(r"\d+(\.\d{1,2})?", provision):
                continue
            zeilen.append({
                "monat": monat,
                "partner": str(row.get("partner") or "sonstig").strip()[:40],
                "abschluesse": to_int(row.get("abschluesse")),
                "stornos": to_int(row.get("stornos")),
                "provision_eur": round(float(provision), 2),
            })
    except (csv.Error, ValueError):
        return {}
    if not zeilen:
        return {}
    monate = {}
    for z in zeilen:
        m = monate.setdefault(z["monat"], {"monat": z["monat"], "partner": set(),
                                           "abschluesse": 0, "stornos": 0,
                                           "provision_eur": 0.0})
        m["partner"].add(z["partner"])
        m["abschluesse"] += z["abschluesse"]
        m["stornos"] += z["stornos"]
        m["provision_eur"] = round(m["provision_eur"] + z["provision_eur"], 2)
    monatsliste = sorted(monate.values(), key=lambda d: d["monat"])
    letzter = monatsliste[-1]
    return {
        "monate": [{**m, "partner": sorted(m["partner"])} for m in monatsliste],
        "summe": {
            "monate": len(monatsliste),
            "abschluesse": sum(m["abschluesse"] for m in monatsliste),
            "stornos": sum(m["stornos"] for m in monatsliste),
            "provision_eur": round(sum(m["provision_eur"] for m in monatsliste), 2),
        },
        "letzter_monat": letzter["monat"],
        "provision_letzter_monat": letzter["provision_eur"],
        "written": TODAY.isoformat(),
        "quelle": "provisionen-tabelle (manuell, Abrechnungsnummer je Zeile)",
    }


# ------------------------------------------------------------------ Schreiben

def _write_atomic(path: str, text: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _read_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def _key_row(row: dict) -> tuple:
    return (str(row.get("event") or ""), str(row.get("slug") or ""),
            str(row.get("article") or ""), str(row.get("pillar") or ""))


def _aggregate(rows: list) -> list:
    agg = {}
    for r in rows:
        k = _key_row(r)
        d = agg.setdefault(k, {"event": k[0], "slug": k[1], "article": k[2],
                              "pillar": k[3], "count": 0})
        d["count"] += int(r.get("count") or 1)
    return sorted(agg.values(), key=lambda d: -int(d["count"]))


def merge_views(alt, neu, keep=None):
    """Seiten-Zähler zusammenführen.

    `keep(row) -> bool`: True ⇒ bestehende Zeile bleibt UNANGETASTET stehen
    (sie stammt von einer anderen Quelle), False ⇒ sie wird durch den frischen
    Import ersetzt. Ohne `keep` gilt `neu` als vollständiger Ersatz
    (Normalbetrieb: der letzte Manuell-Lauf gewinnt). Zusammenführung erfolgt
    je Pfad, damit ein API-Lauf und eine Dashboard-Datei dasselbe Bild malen."""
    keep = keep or (lambda _row: False)
    seiten = {}
    for row in (alt or {}).get("pages") or []:
        if not isinstance(row, dict) or not row.get("path"):
            continue
        if not keep(row):
            continue
        p = norm_path(row["path"])
        if p:
            seiten[p] = {"path": p, "views": to_int(row.get("views")),
                         "visits": to_int(row.get("visits"))}
    for p, row in (neu.get("views") or {}).items():
        d = seiten.setdefault(p, {"path": p, "views": 0, "visits": 0})
        d["views"] += to_int(row.get("views"))
        d["visits"] += to_int(row.get("visits"))
    liste = sorted(seiten.values(), key=lambda d: (-d["views"], d["path"]))[:400]
    totals = {k: to_int(v) for k, v in (neu.get("totals") or {}).items() if v is not None}
    if any(keep(r) for r in ((alt or {}).get("pages") or []) if isinstance(r, dict)) \
            and (alt or {}).get("totals"):
        for k in ("visits", "pageviews"):
            if totals.get(k) is not None:
                totals[k] += to_int((alt["totals"] or {}).get(k))
    return {"totals": totals, "pages": liste}


def merge_rows(alt, neu, keep=None):
    """Event-Zeilen zusammenführen (gleiches Prinzip wie `merge_views`)."""
    keep = keep or (lambda _row: False)
    basis = [r for r in (alt or []) if isinstance(r, dict) and keep(r)]
    return _aggregate(basis + [r for r in neu if isinstance(r, dict)])


def _quellen(pfade: dict | None = None) -> dict:
    """Wer hat die drei Import-Dateien zuletzt geschrieben? `api` | `offline`.

    Die API-Skripte schreiben ihre eigene Meta – daraus liest diese Funktion
    die Herkunft, ohne sie zu besitzen. Eine fremde Quelle wird nie gelöscht.
    `pfade` erlaubt dasselbe in einer Sandbox (Tests)."""
    p = pfade or {}
    out = {}
    for key, meta_path, event in (("views", p.get("views_meta", VIEWS_META), None),
                                  ("clicks", p.get("clicks_meta", CLICKS_META),
                                   "affiliate_click"),
                                  ("ctas", p.get("clicks_meta", CLICKS_META), "cta_click")):
        meta = _read_json(meta_path, {})
        if not isinstance(meta, dict):
            meta = {}
        api_live = meta.get("status") == "ok" and meta.get("import") != "offline"
        if event and meta.get("event") and meta.get("event") != event:
            api_live = False  # die CTA-Datei wurde von einem anderen Event geschrieben
        out[key] = "api" if api_live else "offline"
    return out


def import_messstand(datei: str | None = None, ueberschreiben: bool = True,
                     dry_run: bool = False, provisionen: str | None = None,
                     ziele: dict | None = None) -> dict:
    """Eine Datei → drei Import-Ziele. Gibt die Zusammenfassung zurück.

    `ziele` überschreibt die Zielpfade, `provisionen` den Pfad der
    Abrechnungs-Tabelle: Selbsttests und Unit-Tests laufen damit in einer
    Wegwerf-Kopie und fassen den echten Repo-Bestand nie an.

    `ueberschreiben=True` (Standard) ersetzt den Bestand derselben Quelle –
    Bestand einer ANDEREN Quelle (API-Lauf) bleibt immer stehen. False summiert
    Teilimporte auf (`--merge`).
    """
    z = ziele or {}
    p_views = z.get("views", VIEWS)
    p_views_meta = z.get("views_meta", VIEWS_META)
    p_clicks = z.get("clicks", CLICKS)
    p_clicks_meta = z.get("clicks_meta", CLICKS_META)
    p_ctas = z.get("ctas", CTAS)
    p_ctas_meta = z.get("ctas_meta", CTAS_META)
    p_prov = z.get("provisionen_agg", PROVISIONEN_AGG)
    p_meta = z.get("offline_meta", OFFLINE_META)
    datei = datei or STANDARD_DATEI
    stand, quelle = read_file(datei)
    prov = read_provisionen(provisionen or PROVISIONEN)
    if not (stand.get("views") or stand.get("clicks") or stand.get("ctas")) and not prov:
        return {"status": "leer", "datei": quelle, "provisionen": bool(prov)}

    quellen = _quellen(z)

    def _fremd(schluessel):
        return lambda _row: quellen.get(schluessel) == "api"
    # Standard: eigene (manuelle) Vorgänger werden ersetzt, API-Zeilen bleiben.
    # --merge: gar nichts wird ersetzt, alles wird addiert.
    keep_views = _fremd("views") if ueberschreiben else (lambda _r: True)
    keep_clicks = _fremd("clicks") if ueberschreiben else (lambda _r: True)
    keep_ctas = _fremd("ctas") if ueberschreiben else (lambda _r: True)
    seiten = merge_views(_read_json(p_views, {}), stand, keep=keep_views)
    seiten["generated"] = TODAY.isoformat()
    klicks = merge_rows(_read_json(p_clicks, []), stand.get("clicks") or [],
                        keep=keep_clicks)
    ctas = merge_rows(_read_json(p_ctas, []), stand.get("ctas") or [], keep=keep_ctas)
    win = stand.get("window") or {}

    summary = {
        "status": "ok",
        "datei": quelle,
        "modus": "ueberschreiben" if ueberschreiben else "merge",
        "fremde_quelle_erhalten": not ueberschreiben,
        "seiten": len(seiten.get("pages") or []),
        "besuche_gesamt": (seiten.get("totals") or {}).get("visits"),
        "aufrufe_gesamt": (seiten.get("totals") or {}).get("pageviews"),
        "affiliate_klicks": sum(int(r.get("count") or 0) for r in klicks),
        "cta_klicks": sum(int(r.get("count") or 0) for r in ctas),
        "provisionen": prov,
        "window": win,
    }
    if dry_run:
        return summary

    _write_atomic(p_views, json.dumps(seiten, ensure_ascii=False, indent=2) + "\n")
    _write_atomic(p_clicks, json.dumps(klicks, ensure_ascii=False, indent=2) + "\n")
    _write_atomic(p_ctas, json.dumps(ctas, ensure_ascii=False, indent=2) + "\n")
    # Herkunfts-Nachweis: EINE eigene Meta, nicht die der API-Skripte. Die
    # Umami-Meta gehört `umami_views.py`/`umami_clicks.py` – würden wir sie
    # überschreiben, verlöre die Kette ihr Gedächtnis (und der Trichter meldete
    # „Import zu alt“, obwohl der API-Schritt nie gelaufen ist).
    _write_atomic(p_meta, json.dumps({
        "written": TODAY.isoformat(),
        "status": "ok",
        "datei": quelle,
        "modus": summary["modus"],
        "window_start": win.get("start"),
        "window_end": win.get("ende"),
        "days": win.get("days") or 90,
        "seiten": summary["seiten"],
        "affiliate_klicks": summary["affiliate_klicks"],
        "cta_klicks": summary["cta_klicks"],
        "besuche": summary["besuche_gesamt"],
        "provisionen_monate": len((prov or {}).get("monate") or []),
        "written_files": [os.path.relpath(x, BLOG_DIR) for x in
                          [p_views, p_clicks, p_ctas] + ([p_prov] if prov else [])],
        "hinweis": "API-Meta (data/umami_*.meta.json) bleibt im Besitz der "
                   "API-Skripte – hier steht nur die manuelle Brücke.",
    }, ensure_ascii=False, indent=2) + "\n")
    if prov:
        _write_atomic(p_prov, json.dumps(prov, ensure_ascii=False, indent=2) + "\n")
    return summary


def status(datei: str | None = None, provisionen: str | None = None,
           ziele: dict | None = None) -> dict:
    """Stand der manuellen Brücke + was die API-Brücke meldet (read-only)."""
    z = ziele or {}
    meta = _read_json(z.get("offline_meta", OFFLINE_META), {})
    views_meta = _read_json(z.get("views_meta", VIEWS_META), {})
    clicks_meta = _read_json(z.get("clicks_meta", CLICKS_META), {})
    views = _read_json(z.get("views", VIEWS), {})
    clicks = _read_json(z.get("clicks", CLICKS), [])
    prov = read_provisionen(provisionen or PROVISIONEN)
    return {
        "datei_da": os.path.isfile(datei or STANDARD_DATEI),
        "zuletzt_importiert": meta.get("written", "nie"),
        "import_status": meta.get("status", "unbekannt"),
        "modus": meta.get("modus", "unbekannt"),
        "seiten": len(views.get("pages") or []),
        "affiliate_klicks": sum(int(r.get("count") or 0) for r in clicks
                                if isinstance(r, dict)),
        "cta_klicks": meta.get("cta_klicks", "unbekannt"),
        "provision_monate": len(prov.get("monate") or []),
        "provision_summe": (prov.get("summe") or {}).get("provision_eur"),
        "api_views_status": views_meta.get("status", "nie versucht"),
        "api_klicks_status": clicks_meta.get("status", "nie versucht"),
    }


TEMPLATE = {
    "window": {"start": "", "ende": "", "tage": 90},
    "totals": {"aufrufe": 0, "besuche": 0},
    "views": [{"pfad": "/posts/BEISPIEL-SLUG/", "aufrufe": 0, "besuche": 0}],
    "klicks": [{"event": "affiliate_click", "slug": "strom",
                "article": "posts/BEISPIEL-SLUG/index.md", "pillar": "strom-sparen",
                "zahl": 0}],
    "ctas": [{"event": "cta_click", "slug": "home-strom", "article": "home",
              "zahl": 0}],
}


# ------------------------------------------------------------------ Selftest

def _selftest() -> int:
    import tempfile
    failures = []
    # 1) Pfad-Normalisierung: Query/Fragment/Domain runter, Müll raus
    for raw, want in (("/posts/x/?utm_source=newsletter", "/posts/x/"),
                      ("https://franksfinanzcheck.de/pillar/strom#top", "/pillar/strom/"),
                      ("frank@example.com", ""), ("10.0.0.7", ""),
                      ('/a" onclick=alert(1)/', ""), ("", "")):
        got = norm_path(raw)
        if got != want:
            failures.append(f"norm_path({raw!r}) = {got!r}, erwartet {want!r}")
    # 2) Artikel-Brücke bleibt eng
    if norm_article("posts/2026-08-16-gas-anbieter-wechseln/index.md") != \
            "/posts/2026-08-16-gas-anbieter-wechseln/":
        failures.append("article-Brücke schlägt fehl")
    if norm_article("irgendwas/privates") != "":
        failures.append("unbekannter article darf keine Seite erfinden")
    # 3) JSON-Gerüst roundtrip
    stand = from_json(TEMPLATE)
    if not stand["views"] or stand["clicks"][0]["count"] != 0:
        failures.append("TEMPLATE wird nicht sauber gelesen")
    # 4) API-Export-Variante {pages:[{url,pageViews,visits}]}
    api = {"pages": [{"url": "/posts/a/", "pageViews": 30, "visits": 20},
                     {"url": "/posts/a/", "pageViews": 10, "visits": 5}]}
    s2 = from_json(api)
    a = s2["views"].get("/posts/a/")
    if not a or a["views"] != 40 or a["visits"] != 25:
        failures.append(f"API-Export nicht zusammengeführt: {a}")
    # 5) Events: Einzelsätze zählen, unbekannte Events fallen raus
    ev = from_json({"events": [{"type": "affiliate_click", "count": 1,
                                "eventProps": {"slug": "strom",
                                               "article": "posts/a/index.md"}},
                               {"type": "irgendwas", "count": 1}]})
    if len(ev["clicks"]) != 1 or ev["clicks"][0]["slug"] != "strom":
        failures.append(f"Event-Aggregation: {ev['clicks']}")
    # 6) CSV-Export Seiten + Events
    csv_pages = "url,pageViews,visits,bounces\n/posts/a/,12,9,3\n,0,0,0\n"
    c1 = from_csv(csv_pages, typ="views")
    if c1["views"]["/posts/a/"]["views"] != 12:
        failures.append("CSV Seiten export")
    csv_ev = "event,slug,article\naffiliate_click,gas,posts/b/index.md\naffiliate_click,gas,posts/b/index.md\n"
    c2 = from_csv(csv_ev, typ="events")
    if len(c2["clicks"]) != 2:
        failures.append(f"CSV Events als Einzelsätze: {c2['clicks']}")
    if _aggregate(c2["clicks"])[0]["count"] != 2:
        failures.append("gleiche Zeilen müssen zu einem Zähler aggregieren")
    # 7) merge/replace Verhalten
    alt = {"totals": {"visits": 10, "pageviews": 20},
           "pages": [{"path": "/posts/a/", "views": 20, "visits": 10}]}
    neu = {"views": {"/posts/a/": {"path": "/posts/a/", "views": 5, "visits": 3}},
           "totals": {"visits": 3, "pageviews": 5}}
    r = merge_views(alt, neu)
    if r["pages"][0]["views"] != 5 or r["totals"]["visits"] != 3:
        failures.append(f"Standard muss den Bestand derselben Quelle ersetzen: {r}")
    m = merge_views(alt, neu, keep=lambda _row: True)
    if m["pages"][0]["views"] != 25 or m["totals"]["visits"] != 13:
        failures.append(f"merge muss summieren: {m}")
    k = merge_views(alt, neu, keep=lambda row: row.get("path") == "/posts/a/")
    if k["pages"][0]["views"] != 25:
        failures.append(f"keep-Prädikat wird ignoriert: {k}")
    if merge_rows([{"slug": "s", "count": 2}], [{"slug": "s", "count": 3}],
                  keep=lambda _r: True)[0]["count"] != 5:
        failures.append("merge_rows aggregiert nicht über keep-Bestand hinweg")
    # 8) Leere Quelle erfindet nichts – und die Sandbox fasst den echten Bestand nie an
    with tempfile.TemporaryDirectory() as td:
        z = {k: os.path.join(td, f"{k}.json") for k in
             ("views", "views_meta", "clicks", "clicks_meta", "ctas",
              "ctas_meta", "provisionen_agg", "offline_meta")}
        pv = os.path.join(td, "provisionen.csv")
        if import_messstand(datei=os.path.join(td, "fehlt.json"), provisionen=pv,
                            ziele=z)["status"] != "leer":
            failures.append("fehlende Datei muss status=leer melden")
        leer = os.path.join(td, "leer.json")
        with open(leer, "w", encoding="utf-8") as fh:
            fh.write("   \n")
        if import_messstand(datei=leer, provisionen=pv, ziele=z)["status"] != "leer":
            failures.append("leere Datei muss status=leer melden")
        for pfad in z.values():
            if os.path.exists(pfad):
                failures.append("leere Quelle hat in der Sandbox Dateien geschrieben")
        # 9) Echter Durchschrieb – alles in der Wegwerf-Kopie
        good = os.path.join(td, "messstand.json")
        with open(good, "w", encoding="utf-8") as fh:
            json.dump({"views": [{"pfad": "/posts/x/?utm_source=a", "aufrufe": 5, "besuche": 3},
                                 {"pfad": "/posts/x/", "aufrufe": 2, "besuche": 2},
                                 {"pfad": "frank@example.com", "aufrufe": 9, "besuche": 9}],
                       "totals": {"aufrufe": 7, "besuche": 5},
                       "klicks": [{"event": "affiliate_click", "slug": "strom",
                                   "article": "posts/x/index.md", "zahl": 4}],
                       "ctas": [{"event": "cta_click", "slug": "home-strom",
                                 "article": "home", "zahl": 2}],
                       "window": {"tage": 30}}, fh)
        res = import_messstand(datei=good, provisionen=pv, ziele=z)
        if res["affiliate_klicks"] != 4 or res["seiten"] != 1:
            failures.append(f"Import-Zusammenfassung: {res}")
        meta = _read_json(z["offline_meta"], {})
        if meta.get("status") != "ok" or meta.get("modus") != "ueberschreiben":
            failures.append(f"Meta-Herkunft fehlt: {meta}")
        if not str(meta.get("datei", "")).endswith("messstand.json"):
            failures.append("Meta nennt die Quelle-Datei nicht")
        if sorted(meta.get("written_files") or []) != sorted(
                [os.path.relpath(x, BLOG_DIR) for x in
                 (z["views"], z["clicks"], z["ctas"])]):
            failures.append(f"Meta listet falsche Schreibziele: {meta.get('written_files')}")
        if os.path.exists(z["views_meta"]) or os.path.exists(z["clicks_meta"]):
            failures.append("manuelle Brücke hat die API-Meta angefasst – verboten")
        doc = _read_json(z["views"], {})
        pfade = [p["path"] for p in doc.get("pages") or []]
        if pfade != ["/posts/x/"] or doc["pages"][0]["views"] != 7:
            failures.append(f"UTM-Splitting oder Personenmüll: {doc}")
        # API-Bestand bleibt stehen, wenn die API gerade „lebt"
        with open(z["views_meta"], "w", encoding="utf-8") as fh:
            json.dump({"status": "ok", "written": TODAY.isoformat()}, fh)
        with open(z["views"], "w", encoding="utf-8") as fh:
            json.dump({"totals": {"pageviews": 500, "visits": 300},
                       "pages": [{"path": "/posts/api/", "views": 500, "visits": 300}]}, fh)
        res2 = import_messstand(datei=good, provisionen=pv, ziele=z)
        doc3 = _read_json(z["views"], {})
        pfade3 = {p["path"]: p["views"] for p in doc3.get("pages") or []}
        if pfade3.get("/posts/api/") != 500 or pfade3.get("/posts/x/") != 7:
            failures.append(f"API-Bestand wurde überschrieben: {pfade3}")
        # Teilimport: eigene Quelle wird ADDIERT, API-Bestand bleibt
        m4 = import_messstand(datei=good, ueberschreiben=False, provisionen=pv, ziele=z)
        doc4 = _read_json(z["views"], {})
        pfade4 = {p["path"]: p["views"] for p in doc4.get("pages") or []}
        if pfade4.get("/posts/api/") != 500 or pfade4.get("/posts/x/") != 14:
            failures.append(f"merge muss summieren: {pfade4}")
        if status(datei=good, provisionen=pv, ziele=z)["import_status"] != "ok":
            failures.append("status() meldet die manuelle Brücke nicht als aktiv")
        # 10) Provisions-Tabelle: Monatsaggregate, keine erfundenen Nullen
        with open(pv, "w", encoding="utf-8") as fh:
            fh.write("monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n")
            fh.write("2026-09,CHECK24,3,1,49.50,CHECK24-Abr-2026-09,\n")
            fh.write("2026-09,Tarifcheck,1,0,18.00,TC-2026-09,\n")
            fh.write("falsch,CHECK24,9,9,9.00,x,\n")
        pr = read_provisionen(pv)
        if pr["summe"]["abschluesse"] != 4 or pr["summe"]["provision_eur"] != 67.5:
            failures.append(f"Provisions-Aggregat: {pr}")
        if len(pr["monate"][0]["partner"]) != 2:
            failures.append("Partner je Monat nicht zusammengeführt")
        if read_provisionen(os.path.join(td, "keine.csv")):
            failures.append("fehlende Provisionsdatei muss leer sein (unbekannt ≠ 0)")
        res2 = import_messstand(datei=good, provisionen=pv, ziele=z)
        if not res2.get("provisionen"):
            failures.append("Import meldet die Provisions-Tabelle nicht")
        if _read_json(z["provisionen_agg"], {}).get("letzter_monat") != "2026-09":
            failures.append("Aggregat der Abrechnungstabelle wurde nicht geschrieben")
    if failures:
        print("❌ OFFLINE-IMPORT-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ OFFLINE-IMPORT-SELFTEST bestanden (Pfad-/Artikel-Brücke, JSON+CSV-"
          "Formate, merge/ersetzen, leer≠0, Meta-Herkunft, Provisions-Aggregat).")
    return 0


def run_funnel() -> int:
    try:
        import revenue_funnel
    except ImportError:  # pragma: no cover
        print("::warning:: revenue_funnel.py nicht importierbar – Trichter im "
              "nächsten Importlauf aktualisiert")
        return 0
    return revenue_funnel.main([])


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--status" in argv:
        st = status()
        print("Offline-Messimport – Stand der Messkette")
        for k, v in st.items():
            print(f"  {k:22} {v}")
        return 0
    if "--template" in argv:
        os.makedirs(OFFLINE_DIR, exist_ok=True)
        target = STANDARD_DATEI
        if os.path.exists(target) and "--force" not in argv:
            print(f"⛔ existsiert bereits: {os.path.relpath(target, BLOG_DIR)} "
                  f"(--force überschreibt nicht ungefragt)")
            return 1
        _write_atomic(target, json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n")
        print(f"📝 Gerüst angelegt: {os.path.relpath(target, BLOG_DIR)} – ausfüllen, "
              f"dann `python3 scripts/offline_import.py`")
        return 0
    datei = STANDARD_DATEI
    if "--datei" in argv:
        try:
            datei = argv[argv.index("--datei") + 1]
        except IndexError:
            print("::error::--datei braucht einen Pfad")
            return 1
    res = import_messstand(datei=datei, ueberschreiben="--merge" not in argv,
                           dry_run="--dry-run" in argv or "--print" in argv)
    if "--print" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if res.get("status") == "leer":
        print(f"⏭️  Kein manueller Messstand gefunden ({os.path.relpath(res['datei'], BLOG_DIR)}) "
              "– Datenlücke bleibt dokumentiert, keine erfundenen Nullen.")
        print("    Vorlage: python3 scripts/offline_import.py --template")
        return 0
    if "--dry-run" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    print(f"📥 Offline-Import ({res['modus']}): {res['seiten']} Seiten · "
          f"{res['affiliate_klicks']} Affiliate-Klicks · {res['cta_klicks']} CTA-Klicks"
          + (f" · Provisionen: {res['provisionen']['summe']['provision_eur']:.2f} €"
             if res.get("provisionen") else ""))
    return run_funnel()


if __name__ == "__main__":
    sys.exit(main())
