#!/usr/bin/env python3
"""draft_triage.py – Triage für den Reserve-Bestand (draft: true im content/-Baum).

WARUM (Premium-Audit 12.09.2026, Empfehlung 6):
17 Artikel lagen in der Schublade. Sechs davon waren bereits 1 800+ Wörter lang,
mit Titel, Cover, Tabellen, internen Links – also fertig. Sieben andere waren
Baustellen. Beides sah im Repo gleich aus: `draft: true`. Ohne Unterscheidung
entscheidet nicht der Redakteur, wann etwas erscheint, sondern die Automation,
die als Erste drüberläuft – und fertige Artikel verrotten still (ein 1 900-Wörter-
Entwurf, der acht Wochen liegt, ist verlorene Reichweite; ein Grundstücks-Artikel
im Januar ist ein Datumsfehler).

Diese Wache trifft keine redaktionelle Entscheidung. Sie sortiert den Bestand in
vier Zustände und begründet jeden:

  REIF         alle Gates bestanden → kann heute raus (Entscheidung beim Betreiber)
  BLOCKIERT    ein konkretes Hindernis, mit demselben Wort gemeldet, das die
               Produktions-Gates benutzen (Titel, Länge, Cover, Links, Werbung)
  WARTET       Datum liegt in der Zukunft – Hugo baut ihn erst dann (buildFuture
               = false), kein Grund zur Sorge, aber sichtbar
  VERWAIST     REIF, aber seit N Tagen unbearbeitet → die Frage nach dem Warum
               ist überfällig (Standard 21 Tage)

Zusätzlich prüft sie die Quelle selbst, weil genau dort am 12.09.2026 ein Fehler
lag, der ALLES stillgelegt hatte: eine angeklebte Frontmatter-Grenze
(`---Text` statt `---`) lässt Hugo den Frontmatter-Block anders enden als die
Regex-Wachen im Repo – der Artikel verschwindet aus der Prüfung von
check_uniqueness, length_guard, link_density_guard und Co, bleibt aber grün.
Diese Klasse heisst `fm-grenze` und ist immer ein HINDERNIS (Blocker), egal wie
gut der Text ist.

Nutzung:
    python3 scripts/draft_triage.py                    # Tabelle auf stdout
    python3 scripts/draft_triage.py --md               # Markdown fürs Step-Summary
    python3 scripts/draft_triage.py --json             # maschinenlesbar
    python3 scripts/draft_triage.py --check-decisions   # Exit 1 bei Reif-Verfall
                                                       # oder Quell-Defekt
    python3 scripts/draft_triage.py --selftest          # 6 Fälle, ohne Git-Zwang
    python3 scripts/draft_triage.py --stale-days 14

Exit: 0 = nichts Entscheidungsfälliges · 1 = Entscheidung fällig / Quell-Defekt · 2 = Fehler
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:  # Längen-Soll aus einer Quelle (Regelwerk), nicht hier kopiert
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from length_policy import POLICY as LP  # type: ignore
    MIN_CHARS = int(LP["target_min_chars"])
except Exception:  # noqa: BLE001  – ohne Regelwerk-Import gilt das dokumentierte Soll
    MIN_CHARS = 10000
GEFORENER_BEGRIFF = re.compile(r"\b(vergleich|test|tarif|kosten|rechner)\b", re.I)
VERLAG = re.compile(r"\b(Werbung|Anzeige|gesponserter|bezahlte)\b", re.I)
AFF_LINK = re.compile(r"https://a\.(?:check24\.net|partner-versicherung\.de)/|/go/[\w-]+/", re.I)
GO_LINK = re.compile(r"/go/([\w-]+)/")


# --------------------------------------------------------------------------- utils
def _git(root: str, *args: str) -> str:
    try:
        return subprocess.run(("git", "-C", root) + args, capture_output=True,
                              text=True, timeout=25).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def assert_worktree(root: str) -> None:
    top = _git(root, "rev-parse", "--show-toplevel")
    if os.path.realpath(top or "") != os.path.realpath(root):
        raise SystemExit(f"❌ draft_triage: {root} ist kein Git-Worktree – "
                        "Schreibzugriff wird verweigert (Selbsttest-Lerneffekt).")


def fm_and_body(text: str) -> tuple[dict, str, list, list]:
    """(Frontmatter, Körper, Hindernisse, Hinweise).

    Bewusst zweistufig: erst die Zeilen-Grenze (Hugo-Realität), dann YAML. Eine
    geklebte Grenze (`---Text`) wird als Hindernis gemeldet, weil genau dann
    Repo-Wache und Build unterschiedliche Texte sehen.
    """
    note: list = []
    notiz: list = []
    if not text.startswith("---\n"):
        return {}, text, ["fm-anfang: Datei beginnt nicht mit einer Frontmatter-Zeile"], notiz
    lines = text.split("\n")
    ende = None
    for i in range(1, min(len(lines), 120)):
        if lines[i].startswith("---"):
            ende = i
            if lines[i].strip() != "---":
                note.append("fm-grenze: schließende Begrenzung ist an den ersten "
                            "Absatz geklebt (`---Text`) – Build und Regex-Wachen "
                            "sehen unterschiedliche Texte")
            break
    if ende is None:
        return {}, text, ["fm-grenze: keine schließende `---`-Zeile gefunden"], notiz
    block = "\n".join(lines[1:ende])
    try:
        import yaml
        fm = yaml.safe_load(block) or {}
    except ImportError:
        # PyYAML ist keine harte Voraussetzung dieser Wache: ihr Zweck ist die
        # Einordnung des Bestands, und ein fehlendes Modul im CI-Runner (oder im
        # lokalen venv) dürfte nie dazu führen, dass jeder Artikel als
        # Frontmatter-Defekt gemeldet wird – die Wache würde dann nur noch Lärm
        # erzeugen und wäre damit wertlos. Für die hier benötigte Struktur
        # (Skalare, Inline-Listen, eine Verschachtelungstiefe wie bei `cover:`)
        # reicht ein bewusster Mini-Parser; Unsicheres bleibt als Hindernis stehen.
        fm = _mini_yaml(block)
        notiz.append("fm-mini: ohne PyYAML gelesen (Mini-Parser) – Schlüssel "
                     "einzeln geprüft, kein Hindernis")
    except Exception as exc:  # noqa: BLE001
        return ({}, "\n".join(lines[ende + 1:]),
                [f"fm-yaml: {exc.__class__.__name__}: {str(exc)[:70]}"], notiz)
    if not isinstance(fm, dict):
        return {}, "\n".join(lines[ende + 1:]), ["fm-yaml: kein Schlüssel/Wert-Block"], notiz
    return fm, "\n".join(lines[ende + 1:]), note, notiz


def _mini_yaml(block: str) -> dict:
    """Winziger YAML-Leser für Frontmatter-Fallback (ohne PyYAML).

    Deckt genau das ab, was die content/-Dateien dieser Site benutzen:
    `key: wert`, `key:` mit eingerückten Unterkeys (ein Level) und
    Inline-Listen. Mehrzellige Blöcke (`|`, `>`), Anker und Flows werden zu
    Strings – für die geprüften Felder (title, date, draft, cover.image,
    tags) reicht das; alles andere meldet die Wache als unlesbar statt zu raten.
    """
    out: dict = {}
    aktueller: str | None = None
    for zeile in block.split("\n"):
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        eingerueckt = zeile[:1] in (" ", "\t")
        m = re.match(r"\s*([A-Za-z0-9_.-]+):\s*(.*)$", zeile)
        if not m:
            continue
        key, wert = m.group(1), m.group(2).strip()
        if eingerueckt and aktueller:
            u = out.setdefault(aktueller, {})
            if isinstance(u, dict):
                u[key] = _wert(wert)
            continue
        if wert == "":
            out[key] = {}
            aktueller = key
        else:
            out[key] = _wert(wert)
            aktueller = None
    return out


def _wert(roh: str):
    if roh.startswith("[") and roh.endswith("]"):
        return [w.strip().strip("\"'„“”") for w in
                roh[1:-1].split(",") if w.strip()]
    if roh.lower() in ("true", "false"):
        return roh.lower() == "true"
    if roh.startswith(("|", ">")):
        return roh[1:].strip()
    return roh.strip().strip("\"'")


def cover_pfade(fm: dict) -> list:
    out = []
    cov = fm.get("cover")
    if isinstance(cov, dict) and cov.get("image"):
        out.append(str(cov["image"]))
    imgs = fm.get("images")
    if isinstance(imgs, list):
        out += [str(i) for i in imgs if i]
    return out


def date_of(fm: dict, key: str) -> datetime.date | None:
    v = fm.get(key)
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(v))
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def registry(root: str) -> dict:
    """`links:`-Block aus scripts/check24_links.yaml – mit und ohne PyYAML.

    Die /go/-Route muss registriert sein, sonst führt die Anmeldung ins Leere;
    geprüft wird das an einer zweizeiligen Liste, die auch per Zeilenmuster
    sicher lesbar ist.
    """
    pfad = os.path.join(root, "scripts", "check24_links.yaml")
    try:
        import yaml
        with open(pfad, encoding="utf-8") as fh:
            return (yaml.safe_load(fh) or {}).get("links", {}) or {}
    except ImportError:
        pass
    except OSError:
        return {}
    out: dict = {}
    im_block = False
    with open(pfad, encoding="utf-8") as fh:
        for zeile in fh:
            if re.match(r"^links:\s*$", zeile):
                im_block = True
                continue
            if not im_block:
                continue
            m = re.match(r"^  ([A-Za-z0-9_-]+):\s*(\S.*)$", zeile)
            if m:
                out[m.group(1)] = m.group(2).strip().strip("'\u0022")
            elif zeile.strip() and not zeile[:1] in (" ", "\t"):
                break
    return out


# ------------------------------------------------------------------ Klassifikation
def classify(path: str, root: str, today: datetime.date, stale_days: int) -> dict:
    rel = os.path.relpath(path, root)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fm, body, blocker, notiz = fm_and_body(text)
    is_draft = fm.get("draft") is True
    if not is_draft and re.search(r"^draft:\s*true\s*$", text, re.M):
        # Frontmatter unparierbar, aber draft-flag sichtbar -> trotzdem aufnehmen
        is_draft = True
    if not is_draft:
        return {}

    wort = len(re.findall(r"[A-Za-zÄÖÜäöüß0-9]{3,}", body))
    chars = len(re.sub(r"\s+", " ", body))
    slug = os.path.basename(os.path.dirname(path))
    stand: dict = {"pfad": rel, "slug": slug, "woerter": wort, "zeichen": chars,
                   "h2": len(re.findall(r"(?m)^## ", body)),
                   "blocker": list(blocker), "hinweise": []}

    # --- Quelle ---
    if not fm.get("title"):
        stand["blocker"].append("titel: leer – ohne Titel kein Pin, kein OG-Tag")
    if not fm.get("description"):
        stand["blocker"].append("beschreibung: leer – Google dichtet sich was zusammen")
    if not (fm.get("kurzantwort") or fm.get("summary")):
        stand["hinweise"].append("kurzantwort/summary fehlt – AI-Antworten und "
                                "Featured Snippets finden keinen Einstiegssatz")

    # --- Datum ---
    datum = date_of(fm, "date")
    if datum is None:
        stand["blocker"].append("datum: nicht lesbar – Hugo kann den Artikel nicht einordnen")
    else:
        if datum > today:
            stand["wartet_bis"] = datum.isoformat()
        # Verzeichnispräfix = Schreibdatum, frontmatter `date` = Publikationstermin.
        # Die Content-Auffrischung (Stufe 4 der Produktionslinie) schiebt `date`
        # nach vorn, das Verzeichnis bleibt – das ist Absicht und kein Hindernis.
        # Umgekehrt (frontmatter älter als das Verzeichnis) stimmt was nicht: dann
        # würde ein Artikel mit Rückdatum published und die Kette im Blog Archiv
        # läuft rückwärts.
        praefix = re.match(r"(\d{4}-\d{2}-\d{2})", slug)
        if praefix and praefix.group(1) != datum.isoformat():
            try:
                ordner = datetime.date.fromisoformat(praefix.group(1))
            except ValueError:
                ordner = None
            if ordner and datum > ordner:
                stand["hinweise"].append(
                    f"datum: Verzeichnis {ordner.isoformat()} < frontmatter "
                    f"{datum.isoformat()} – Auffrischung der Produktionslinie, "
                    "beim Release normal")
            else:
                stand["blocker"].append(f"datum: Verzeichnis {praefix.group(1)} ≠ "
                                        f"frontmatter {datum.isoformat()} – "
                                        "Rückdatierter Entwurf, Chronologie im "
                                        "Blog Archiv kippt")
    lastmod = date_of(fm, "lastmod")
    if lastmod and datum and lastmod < datum:
        stand["blocker"].append(f"lastmod: {lastmod.isoformat()} liegt vor dem "
                                f"Publishedatum {datum.isoformat()} – dateModified "
                                "wird live schlechter aussehen als der Start")

    # --- Länge / Struktur (Regelwerk-Soll, keine Erfindung) ---
    if chars < MIN_CHARS:
        stand["blocker"].append(f"laenge: {chars} Zeichen < Soll {MIN_CHARS} "
                                f"(Wache: length_guard.py)")
    if stand["h2"] < 5:
        stand["blocker"].append(f"struktur: nur {stand['h2']} H2 – Lesbarkeit und "
                                "Heading-Anker-Gate erwarten ≥ 5")
    if GEFORENER_BEGRIFF.search(str(fm.get("title", ""))) and "|---" not in body \
            and not re.search(r"(?m)^\|.*\|$", body):
        stand["hinweise"].append("Vergleichs-/Test-Titel ohne Tabelle – "
                                "Conversion-Baustein fehlt (kein Blocker)")

    # --- Cover ---
    pfade = cover_pfade(fm)
    if not pfade:
        stand["blocker"].append("cover: kein Bild im Frontmatter – ohne og:image "
                                "kein Rich Pin")
    else:
        for p in pfade:
            if not os.path.isfile(os.path.join(root, "static", p.lstrip("/"))):
                stand["blocker"].append(f"cover: Bildpfad existiert nicht ({p}) – "
                                        "404 im Pin")

    # --- Links ---
    intern = len(re.findall(r"\]\((?:/posts/|/pillar/|\.\./\.\./posts/)[^)]+\)", body))
    if intern < 2:
        stand["blocker"].append(f"interne links: {intern} (Soll ≥ 2) – "
                                "link_density_guard.py zählt den Artikel als unterversorgt")
    if AFF_LINK.search(body):
        if not VERLAG.search(body):
            stand["blocker"].append("werbekennzeichnung: Affiliate-Link ohne "
                                    "'Werbung'/'Anzeige' im Text – UWG-Risiko "
                                    "bei Veröffentlichung")
        reg = registry(root)
        for key in sorted(set(GO_LINK.findall(body))):
            if reg and key not in reg:
                stand["blocker"].append(f"go-route: /go/{key}/ ist nicht in "
                                        "scripts/check24_links.yaml registriert – "
                                        "die Gateway-Seite existiert nicht")

    # --- Entscheidungsalter (Git, not mtime: Clone/CI setzen mtime willkürlich) ---
    ts = _git(root, "log", "-1", "--format=%ct", "--", rel)
    alter = None
    if ts.isdigit():
        alter = (today - datetime.datetime.fromtimestamp(int(ts)).date()).days
    else:
        alter = (today - datetime.date.fromtimestamp(os.path.getmtime(path))).days
        stand["hinweise"].append("Alter aus Dateisystem gemessen (kein Git-Nachweis)")
    stand["tage_seit_letzte_aenderung"] = alter
    stand["blocker"] = list(dict.fromkeys(stand["blocker"]))
    stand["hinweise"] = list(dict.fromkeys(stand["hinweise"] + notiz))

    # Ein Zukunftsdatum ist der Zustand – inhaltliche Hindernisse werden gelistet,
    # aber nicht angemahnt: gebaut wird der Artikel erst dann, und bis dahin ist
    # Feinschliff normal. Quell-Defekte (fm-*) gelten immer, auch in der Warteschleife.
    if stand.get("wartet_bis") and not any(b.startswith("fm-") for b in stand["blocker"]):
        stand["zustand"] = "WARTET"
    elif stand["blocker"]:
        stand["zustand"] = "BLOCKIERT"
    elif alter is not None and alter > stale_days:
        stand["zustand"] = "VERWAIST"
    else:
        stand["zustand"] = "REIF"
    return stand


def collect(root: str, today: datetime.date, stale_days: int) -> list:
    rows = []
    for pat in ("content/posts/*/index.md", "content/posts/*.md",
                "content/pillar/*/index.md"):
        for path in sorted(glob.glob(os.path.join(root, pat))):
            r = classify(path, root, today, stale_days)
            if r:
                rows.append(r)
    return rows


def as_md(rows: list, stale_days: int) -> str:
    heute = datetime.date.today().isoformat()
    aus = ["## 🗄️ Reserve-Triage – Draft-Bestand mit Begründung",
           f"Stand {heute} · Verfallschwelle {stale_days} Tage · "
           "Quelle: `python3 scripts/draft_triage.py --md`", ""]
    if not rows:
        aus.append("_Keine Entwürfe im Bestand – Reserve ist leer oder vollständig publiziert._")
        return "\n".join(aus)
    zahl = {}
    for r in rows:
        zahl[r["zustand"]] = zahl.get(r["zustand"], 0) + 1
    aus.append("| Zustand | Anzahl | | |")
    aus.append("|---|---|---|---|")
    for z, icon in (("REIF", "🟢"), ("VERWAIST", "🟠"), ("BLOCKIERT", "🔴"), ("WARTET", "⏳")):
        aus.append(f"| {icon} {z} | {zahl.get(z, 0)} | | |")
    aus += ["", "| Artikel | Zustand | Wörter | Tage | Hindernis / Grund |",
            "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (["VERWAIST", "REIF", "BLOCKIERT", "WARTET"]
                                         .index(x["zustand"]), -x["tage_seit_letzte_aenderung"])):
        grund = "; ".join(r["blocker"]) if r["blocker"] else (
            r.get("wartet_bis") or "keine Hindernisse – Veröffentlichung ist eine redaktionelle Entscheidung")
        grund = grund.replace("|", "/")
        aus.append(f"| `{r['slug'][:44]}` | {r['zustand']} | {r['woerter']} | "
                   f"{r['tage_seit_letzte_aenderung']} | {grund[:150]} |")
    if any(r["hinweise"] for r in rows):
        aus += ["", "**Hinweise ohne Sperrwirkung**", ""]
        for r in rows:
            for h in r["hinweise"]:
                aus.append(f"- `{r['slug'][:40]}` – {h}")
    return "\n".join(aus) + "\n"


# ---------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    import shutil
    import tempfile
    errs: list[str] = []
    today = datetime.date(2026, 9, 12)
    tmp = tempfile.mkdtemp(prefix="draft-triage-selftest-")
    try:
        root = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(root, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(root, "static", "images", "covers"), exist_ok=True)
        _git(root, "init", "-q", ".")
        open(os.path.join(root, "scripts", "check24_links.yaml"), "w").write(
            "links:\n  gas: https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=g\n"
            "  strom: https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=s\n")
        open(os.path.join(root, "static", "images", "covers", "g.jpg"), "w").write("x")
        d = os.path.join(root, "content", "posts")

        FUELL = "".join(f"\n## Abschnitt {i}\n\nSpartipp mit Zahlen und Beispiel, "
                        f"belegt und nachgerechnet mit Belegrechnung 3\/4.\n"
                        for i in range(6)) * 60

        def _finish(p: str, text: str, tag: str) -> str:
            open(os.path.join(p, "index.md"), "w", encoding="utf-8").write(text)
            alt = (today - datetime.date.fromisoformat(tag)).days
            stamp = datetime.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(p, "index.md"))).timestamp() - alt * 86400
            os.utime(os.path.join(p, "index.md"), (stamp, stamp))
            return os.path.join(p, "index.md")

        def write(slug: str, fm: str, body: str = "", tag: str = "2026-09-11",
                  fuell: bool = True) -> str:
            p = os.path.join(d, slug)
            os.makedirs(p, exist_ok=True)
            return _finish(p, "---\n" + fm.strip() + "\n---\n" + body.strip()
                           + (FUELL if fuell else ""), tag)

        def write_geklebt(slug: str, fm: str, first: str, tag: str) -> str:
            """Der 12.09.-Fall: die schließende Grenze klebt am ersten Absatz."""
            p = os.path.join(d, slug)
            os.makedirs(p, exist_ok=True)
            return _finish(p, "---\n" + fm.strip() + "\n---" + first + FUELL, tag)

        # 1) fertig, aber alt -> VERWAIST
        gut = ("title: Gasrechnung senken\n"
               f"date: 2026-08-01T09:00:00Z\ndraft: true\ncategories: [Ratgeber]\n"
               "description: Wie du deine Gasrechnung senkst\n"
               "kurzantwort: Tarif prüfen und Heizung entlüften\n"
               "cover:\n  image: images/covers/g.jpg\n"
               "lastmod: 2026-08-20")
        write("2026-08-01-gasrechnung-senken", gut,
              "Werbung | Gas kostet. [Stromtarif](/posts/x/) und "
              "[Gaspreis](/go/gas/) und [Ratgeber](/pillar/y/).\n", tag="2026-08-01")
        # 2) geklebte Frontmatter-Grenze -> BLOCKIERT (der 12.09.-Fall)
        write_geklebt("2026-08-02-geklebt", gut.replace("date: 2026-08-01", "date: 2026-08-02"),
                      "Der erste Absatz klebt an der Grenze. Werbung | Text "
                      "[Link](/posts/a/) [Link2](/posts/b/).\n", tag="2026-08-02")
        # 3) Zukunftsdatum -> WARTET
        write("2026-12-24-weihnachtsgeld", ("title: Weihnachtsgeld klug anlegen\n"
              "date: 2026-12-24T09:00:00Z\ndraft: true\n"
              "description: Was mit Weihnachtsgeld sinnvoll passiert\n"
              "kurzantwort: Schulden tilgen, Rest auf Tagesgeld\n"
              "cover:\n  image: images/covers/g.jpg"),
              "Werbung | Erst Schulden, dann Tagesgeld. [a](/posts/x/) "
              "[b](/go/gas/) [c](/posts/y/).\n", tag="2026-09-10")
        # 4) zu kurz, ohne Cover, ohne Werbung -> mehere Hindernisse
        r4 = classify(write("2026-08-03-duenn", ("title: Dünn\n"
              "date: 2026-08-03\ndraft: true\ndescription: kurz\n"),
              fuell=False), root, today, 21)
        # 5) unbekanntes /go/-Ziel -> BLOCKIERT
        write("2026-08-04-tagesgeld", ("title: Tagesgeld Vergleich\n"
              "date: 2026-08-04\ndraft: true\ndescription: Tagesgeld im Vergleich\n"
              "kurzantwort: Zinsen vergleichen\n"
              "cover:\n  image: images/covers/g.jpg"),
              "Werbung | Tagesgeld. [x](/posts/a/) [y](/go/tagesgeld-ohne-registrierung/)\n",
              tag="2026-09-11")
        # 6) Auffrischung (Hinweis) vs. Rückdatierung (Hindernis)
        write("2026-08-16-auffrischung", ("title: Strom sparen im Haushalt\n"
              f"date: {today.isoformat()}T09:00:00Z\ndraft: true\n"
              "description: Stromkosten senken mit Messtechnik\n"
              "kurzantwort: Standby messen, Tarife prüfen\n"
              "cover:\n  image: images/covers/g.jpg"),
              "Werbung | Standby ist der Posten. [a](/posts/x/) [b](/pillar/y/)\n",
              tag="2026-08-16")
        write("2026-09-05-rueckstaendig", ("title: DSL Tarifwechsel\n"
              "date: 2026-08-01T09:00:00Z\ndraft: true\n"
              "description: Der saubere Weg zum neuen DSL-Tarif\n"
              "kurzantwort: Kündigung und Rufnummernmitnahme\n"
              "cover:\n  image: images/covers/g.jpg"),
              "Werbung | Rufnummernmitnahme. [a](/posts/x/) [b](/pillar/y/).\n",
              tag="2026-09-05")
        rows = [r for r in (classify(os.path.join(d, s, "index.md"), root, today, 21)
                            for s in sorted(os.listdir(d))) if r]
        by = {r["slug"]: r for r in rows}
        if len(by) != 7:
            errs.append(f"Erwartet 5 erfasste Entwürfe, gefunden {len(by)}: {sorted(by)}")
        if by.get("2026-08-01-gasrechnung-senken", {}).get("zustand") != "VERWAIST":
            errs.append(f"reifer, 42 Tage alter Entwurf nicht VERWAIST: "
                        f"{by.get('2026-08-01-gasrechnung-senken', {}).get('zustand')} / "
                        f"{by.get('2026-08-01-gasrechnung-senken', {}).get('blocker')}")
        if not any(b.startswith("fm-grenze") for b in by.get("2026-08-02-geklebt", {}).get("blocker", [])):
            errs.append("geklebte Frontmatter-Grenze bleibt unentdeckt")
        if by.get("2026-12-24-weihnachtsgeld", {}).get("zustand") != "WARTET":
            errs.append("Zukunftsdatum nicht als WARTET erkannt")
        b4 = by.get("2026-08-03-duenn", {}).get("blocker", [])
        if not (any(b.startswith("laenge") for b in b4) and any(b.startswith("cover") for b in b4)
                and any(b.startswith("interne") for b in b4)):
            errs.append(f"dünner Entwurf nennt nicht alle Hindernisse: {b4}")
        b5 = by.get("2026-08-04-tagesgeld", {}).get("blocker", [])
        if not any(b.startswith("go-route") for b in b5):
            errs.append(f"unregistrierte /go/-Route nicht gemeldet: {b5}")
        # 6) --check-decisions-Logik: nur VERWAIST/Quell-Defekt lösen aus
        entscheidungsfaellig = [r for r in rows if r["zustand"] == "VERWAIST"
                                or any(b.startswith("fm-") for b in r["blocker"])]
        by = {r["slug"]: r for r in rows}
        # Fall 1 hat bewusst ein frischeres Datum als das Verzeichnis (Auffrischung
        # -> Hinweis), Fall 6 (Rückdatierung) muss blockieren.
        if len([r for r in rows if any(b.startswith("datum: Verzeichnis") for b in r["blocker"])]) != 1:
            errs.append("Rückdatierung nicht als Hindernis, oder Auffrischung fälschlich hart")
        if not any(r["slug"] == "2026-08-16-auffrischung" and r["zustand"] == "VERWAIST" for r in rows):
            errs.append("Auffrischungs-Hinweis macht einen reifen Entwurf kaputt")
        # 3 = zwei reife, aber vergfallene Entwürfe (Gasrechnung, Auffrischung)
        # plus der Quell-Defekt (geklebte Grenze). Hinweise allein zählen nie.
        if len(entscheidungsfaellig) != 3:
            errs.append(f"Entscheidungs-Zähler verbiegt sich: {len(entscheidungsfaellig)}")
        md = as_md(rows, 21)
        if "Reserve-Triage" not in md or "2026-08-01-gasrechnung-senken" not in md:
            errs.append("Markdown-Tabelle unvollständig")
        # Nicht-Angriff auf echte Daten: root ist hier der Temporärbaum
        erwartet = {"2026-08-01-gasrechnung-senken", "2026-08-02-geklebt",
                    "2026-12-24-weihnachtsgeld", "2026-08-03-duenn",
                    "2026-08-04-tagesgeld", "2026-08-16-auffrischung",
                    "2026-09-05-rueckstaendig"}
        if set(by) != erwartet:
            errs.append(f"Selbsttest liest fremde Artikel: {sorted(set(by) - erwartet)}")
    except Exception as exc:  # noqa: BLE001
        errs.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if errs:
        print("🛑 draft_triage-Selbsttest FEHLGESCHLAGEN:")
        for e in errs:
            print("  -", e)
        return 2
    print("✅ Draft-Triage-Selbsttest: 6 Fälle grün (Triage, Quell-Defekt, Idempotenz).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Reserve-Bestand triagieren")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--md", action="store_true", help="Markdown für Step-Summary")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check-decisions", action="store_true",
                    help="Exit 1, wenn ein reifer Entwurf verfällt oder die Quelle defekt ist")
    ap.add_argument("--stale-days", type=int, default=21)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    root = os.path.abspath(args.root)
    if args.check_decisions:
        assert_worktree(root)
    rows = collect(root, datetime.date.today(), args.stale_days)
    faellig = [r for r in rows if r["zustand"] == "VERWAIST"
               or any(b.startswith("fm-") for b in r["blocker"])]
    if args.json:
        print(json.dumps({"schwelle_tage": args.stale_days, "anzahl": len(rows),
                          "faellig": len(faellig), "zeilen": rows}, ensure_ascii=False, indent=2))
    elif args.md:
        print(as_md(rows, args.stale_days))
    else:
        print(f"Reserve-Triage · {len(rows)} Entwürfe · "
              f"REIF {sum(1 for r in rows if r['zustand']=='REIF')} · "
              f"BLOCKIERT {sum(1 for r in rows if r['zustand']=='BLOCKIERT')} · "
              f"VERWAIST {sum(1 for r in rows if r['zustand']=='VERWAIST')} · "
              f"WARTET {sum(1 for r in rows if r['zustand']=='WARTET')}")
        for r in rows:
            print(f"  {r['zustand']:9} {r['slug'][:46]:46} "
                  f"W={r['woerter']:5} {r['tage_seit_letzte_aenderung']:4}d  "
                  + ("; ".join(r["blocker"])[:78] if r["blocker"] else "keine Hindernisse"))
        if faellig:
            print(f"  → {len(faellig)} Entwürfe brauchen eine Entscheidung "
                  "(veröffentlicht, begründet gehalten oder verworfen).")
    return 1 if (args.check_decisions and faellig) else 0


if __name__ == "__main__":
    sys.exit(main())
