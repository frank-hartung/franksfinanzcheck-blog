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
    python3 scripts/draft_triage.py --selftest          # deterministisch: 10 Fälle
                                                       # × 6 Testdaten × 4 Zeitzonen,
                                                       # unter Uhr-Zwang (strikt)
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
try:  # Uhr-Zwang für den Selbsttest: Determinismus wird bewiesen, nicht gehofft
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from selftest_clock import (MITTAG as _MITTAG, MODUS_STRIKT as _UHR_STRIKT,  # type: ignore
                                stempel as _stempel, uhr as _uhr)
except Exception:  # noqa: BLE001  – fehlende Hilfe ist ein Befund, kein Freibrief
    _MITTAG = _UHR_STRIKT = _stempel = _uhr = None
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


def as_md(rows: list, stale_days: int, stand: datetime.date | None = None) -> str:
    """Markdown-Tabelle. `stand` ist injizierbar: Ein Selbsttest, der den
    Berichts-Kopf erst zur Laufzeit datieren lässt, holt sich die echte Wanduhr
    ins Haus – und damit ein Verfallsdatum (siehe Modul-Doku)."""
    heute = (stand or datetime.date.today()).isoformat()
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
# DETERMINISMUS-VERTRAG dieses Selbsttests (Reparatur 18.09.2026):
#
#   1. Jeder Fall ist RELATIV zum Testdatum beschrieben („42 Tage alt"), nie
#      absolut („2026-08-01") und nie relativ zur echten Uhr („JETZT − 42 Tage").
#   2. Jedes Dateialter wird ABSOLUT gestempelt (scripts/selftest_clock.stempel,
#      lokaler Mittag) – damit liest kein Prüfpfad die Wanduhr.
#   3. Der ganze Ablauf läuft unter Uhr-Zwang im Modus `strikt`: Ein einziger
#      Lesezugriff auf date.today()/datetime.now()/time.localtime() bricht den
#      Selbsttest sofort, statt ihn still mit dem Kalender altern zu lassen.
#   4. Das gemessene Alter jedes Falls wird gegen das beabsichtigte geprüft.
#      Genau diese Zeile hätte den Ausfall vom 18.09.2026 am Tag des Einbaus
#      gemeldet: Damals maß der Fall „Auffrischung" 21 statt 27 Tage, weil die
#      Fixtures von der echten Uhr, die Erwartung aber von einem eingefrorenen
#      Testdatum abhing. Sechs Tage nach dem Einbau kippte das Qualitäts-Gate rot
#      (Run 35312783057) und Stufe 5 der Content-Reserve verbrannte 7½ Minuten
#      (Issue #310) – ohne dass jemand den Code angefasst hätte.
#   5. Das Szenario läuft unter SECHS Testdaten (inkl. Schalttag und dem Datum,
#      an dem audio_coverage_check kippte) und in VIER Zeitzonen: gleiche
#      Eingabe, gleiches Ergebnis – der Beweis, nicht die Behauptung.
#
# Spalten: alter = erwartetes GEMESSENES Alter in Tagen · praefix/datum = Versatz
# des Verzeichnispräfix bzw. des frontmatter `date` zum Testdatum · mtime = Alter
# des Datei-Stempels (nur wo es bewusst vom Git-Nachweis abweicht) · git_commit =
# Alter des Commits (beweist: Git-Nachweis schlägt Dateisystem, weil CI-Clones
# mtime willkürlich setzen).
FAELLE = (
    dict(kennung="gasrechnung", titel="Gasrechnung senken", alter=42,
         praefix=-42, datum=-42, zustand="VERWAIST",
         body="Werbung | Gas kostet. [Stromtarif](/posts/x/) und "
              "[Gaspreis](/go/gas/) und [Ratgeber](/pillar/y/).\n",
         lastmod=19),
    dict(kennung="geklebt", titel="Gasrechnung senken (zweite Fassung)", alter=41,
         praefix=-41, datum=-41, zustand="BLOCKIERT", hinder=("fm-grenze",),
         geklebt=True),
    dict(kennung="duenn", titel="Dünn", alter=1, praefix=-40, datum=-40,
         zustand="BLOCKIERT",
         hinder=("laenge", "struktur", "cover", "interne"),
         body="", fuell=False, cover=False, kurzantwort=""),
    dict(kennung="tagesgeld", titel="Tagesgeld Vergleich", alter=1,
         praefix=-39, datum=-39, zustand="BLOCKIERT",
         hinder=("interne", "go-route"),
         body="Werbung | Tagesgeld. [x](/posts/a/) "
              "[y](/go/tagesgeld-ohne-registrierung/)\n"),
    dict(kennung="weihnachten", titel="Weihnachtsgeld klug anlegen", alter=2,
         praefix=+103, datum=+103, zustand="WARTET"),
    dict(kennung="auffrischung", titel="Strom sparen im Haushalt", alter=27,
         praefix=-27, datum=0, zustand="VERWAIST",
         hinweis="datum: Verzeichnis"),
    dict(kennung="rueckstaendig", titel="DSL Tarifwechsel", alter=7,
         praefix=-7, datum=-42, zustand="BLOCKIERT",
         hinder=("datum: Verzeichnis",)),
    dict(kennung="schwelle", titel="Heizkörper richtig einstellen", alter=21,
         praefix=-21, datum=-21, zustand="REIF"),
    dict(kennung="schwelle-plus", titel="Warmwasser ohne Verschwendung", alter=22,
         praefix=-22, datum=-22, zustand="VERWAIST"),
    dict(kennung="git-alter", titel="Zinsen beim Festgeld sichern", alter=30,
         praefix=-30, datum=-30, zustand="VERWAIST", mtime=0, git_commit=30),
)
PROBETAGE = (
    datetime.date(2026, 9, 12),   # Ursprung: an diesem Tag war der Test zuletzt grün
    datetime.date(2026, 9, 18),   # der Tag, an dem das Qualitäts-Gate rot wurde
    datetime.date(2026, 12, 24),  # Heiligabend – hier starb audio_coverage_check
    datetime.date(2027, 2, 28),   # Vorabend des Schaltjahres
    datetime.date(2028, 2, 29),   # Schalttag
    datetime.date(2031, 5, 4),    # vier Jahre voraus
)
PROBE_ZONEN = ("UTC", "Europe/Berlin", "Pacific/Kiritimati", "Pacific/Niue")
# VERWAIST (gasrechnung, auffrischung, schwelle-plus, git-alter) + Quell-Defekt
# (geklebt). Hinweise allein zählen nie – sie sind keine Entscheidungsgründe.
ENTSCHEIDUNGEN = 5


def _szenario(today: datetime.date) -> tuple[list, list]:
    """Reserve-Bestand aufbauen und prüfen. Gibt (Zeilen, Abweichungen) zurück."""
    import shutil
    import tempfile
    errs: list[str] = []
    rows: list = []
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
                        f"belegt und nachgerechnet mit Belegrechnung 3\\/4.\n"
                        for i in range(6)) * 60

        def quelle(titel: str, datum: datetime.date, beschreibung: str,
                   kurzantwort: str | None = None, cover: bool = True,
                   lastmod: datetime.date | None = None) -> str:
            fm = [f"title: {titel}", f"date: {datum.isoformat()}T09:00:00Z",
                  "draft: true", f"description: {beschreibung}"]
            if kurzantwort:
                fm.append(f"kurzantwort: {kurzantwort}")
            if cover:
                fm.append("cover:\n  image: images/covers/g.jpg")
            if lastmod:
                fm.append(f"lastmod: {lastmod.isoformat()}")
            return "\n".join(fm)

        def ablegen(slug: str, text: str, tag: datetime.date) -> str:
            """Schreiben und das Alter ABSOLUT stempeln – nie „JETZT minus n Tage"."""
            p = os.path.join(d, slug)
            os.makedirs(p, exist_ok=True)
            pfad = os.path.join(p, "index.md")
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(text)
            _stempel(pfad, tag)
            return pfad

        slugs: dict[str, str] = {}
        for fall in FAELLE:
            kennung = fall["kennung"]
            praefix = today + datetime.timedelta(days=fall["praefix"])
            datum = today + datetime.timedelta(days=fall["datum"])
            tag = today - datetime.timedelta(days=fall.get("mtime", fall["alter"]))
            slug = f"{praefix.isoformat()}-{kennung}"
            slugs[kennung] = slug
            body = fall.get("body", "Werbung | Hier steht der Nutzwert im "
                                    "Vordergrund. [Ratgeber](/posts/x/) und "
                                    "[Säule](/pillar/y/).\n")
            if fall.get("geklebt"):
                fm = quelle(fall["titel"], datum,
                            f"Worum es bei {fall['titel'].lower()} wirklich geht",
                            "Kurze Antwort vor der Rechnung")
                # Der 12.09.-Fall: die schließende Grenze klebt am ersten Absatz.
                ablegen(slug, "---\n" + fm + "\n---Der erste Absatz klebt an der "
                        "Grenze. Werbung | Text [Link](/posts/a/) "
                        "[Link2](/posts/b/).\n" + FUELL, tag)
                continue
            if kennung == "duenn":
                fm = (f"title: {fall['titel']}\ndate: {datum.isoformat()}\n"
                      "draft: true\ndescription: kurz\n")
            else:
                fm = quelle(fall["titel"], datum,
                            f"Worum es bei {fall['titel'].lower()} wirklich geht",
                            fall.get("kurzantwort", "Kurze Antwort vor der Rechnung"),
                            cover=fall.get("cover", True),
                            lastmod=(datum + datetime.timedelta(days=fall["lastmod"])
                                     if "lastmod" in fall else None))
            ablegen(slug, "---\n" + fm + "\n---\n" + body.strip()
                    + (FUELL if fall.get("fuell", True) else ""), tag)

        # Git-Nachweis schlägt Dateisystem: CI-Clones setzen mtime beliebig,
        # deshalb liest die Wache das Alter zuerst aus dem Commit. Bewiesen mit
        # einem FRISCH gestempelten, aber ALT committeten Entwurf.
        git_fall = next((f for f in FAELLE if "git_commit" in f), None)
        git_moeglich = bool(shutil.which("git"))
        if git_fall and git_moeglich:
            tag_alt = today - datetime.timedelta(days=git_fall["git_commit"])
            iso = datetime.datetime.combine(tag_alt, _MITTAG).astimezone().isoformat()
            rel = os.path.relpath(os.path.join(d, slugs[git_fall["kennung"]],
                                               "index.md"), root)
            env = dict(os.environ, GIT_AUTHOR_DATE=iso, GIT_COMMITTER_DATE=iso)
            for args in (("add", "--", rel), ("commit", "-qm", "fixture: Rückdatum")):
                subprocess.run(("git", "-C", root,
                                "-c", "user.email=selftest@example.org",
                                "-c", "user.name=Selbsttest") + args,
                               capture_output=True, text=True, timeout=60, env=env)
        elif git_fall:
            errs.append("Git fehlt – der Fall „Git-Nachweis schlägt mtime“ ist "
                        "nicht prüfbar (keine stille Lücke)")

        rows = [r for r in (classify(os.path.join(d, s, "index.md"), root, today, 21)
                            for s in sorted(os.listdir(d))) if r]
        by = {r["slug"]: r for r in rows}

        if set(by) != set(slugs.values()):
            errs.append("Selbsttest liest fremde Artikel oder verliert Fälle: "
                        f"{sorted(set(by) ^ set(slugs.values()))}")
        for fall in FAELLE:
            kennung, hinder = fall["kennung"], fall.get("hinder", ())
            r = by.get(slugs[kennung])
            if not r:
                errs.append(f"{kennung}: Entwurf wurde nicht erfasst")
                continue
            if r["zustand"] != fall["zustand"]:
                errs.append(f"{kennung}: Zustand {r['zustand']} statt "
                            f"{fall['zustand']} (Hindernisse: {r['blocker']})")
            # Kern-Assert der Reparatur: gemessen == beabsichtigt
            if r["tage_seit_letzte_aenderung"] != fall["alter"]:
                errs.append(f"{kennung}: Alter {r['tage_seit_letzte_aenderung']} Tage "
                            f"gemessen, {fall['alter']} beabsichtigt – der Prüfpfad "
                            "liest eine andere Uhr als der Fixture-Bau")
            for anfang in hinder:
                if not any(b.startswith(anfang) for b in r["blocker"]):
                    errs.append(f"{kennung}: Hindernis „{anfang}“ fehlt "
                                f"(gefunden: {r['blocker']})")
            if not hinder and r["blocker"]:
                errs.append(f"{kennung}: freier Fall hat unerwartete Hindernisse "
                            f"{r['blocker']}")
            if "hinweis" in fall and not any(
                    h.startswith(fall["hinweis"]) for h in r["hinweise"]):
                errs.append(f"{kennung}: Hinweis „{fall['hinweis']}“ fehlt "
                            f"(gefunden: {r['hinweise']})")
        # Auffrischung = Hinweis, Rückdatierung = Hindernis (genau ein Fall)
        if len([r for r in rows
                if any(b.startswith("datum: Verzeichnis") for b in r["blocker"])]) != 1:
            errs.append("Rückdatierung nicht als Hindernis, oder Auffrischung "
                        "fälschlich hart")
        # Verfalls-Schwelle: 21 Tage sind reif, 22 Tage sind verwaist
        if by.get(slugs["schwelle"], {}).get("zustand") != "REIF":
            errs.append("Schwelle: genau 21 Tage dürfen noch nicht verwaist sein")
        if by.get(slugs["schwelle-plus"], {}).get("zustand") != "VERWAIST":
            errs.append("Schwelle: 22 Tage müssen verwaist sein")
        # --check-decisions: nur VERWAIST und Quell-Defekte lösen aus
        faellig = [r for r in rows if r["zustand"] == "VERWAIST"
                   or any(b.startswith("fm-") for b in r["blocker"])]
        if len(faellig) != ENTSCHEIDUNGEN:
            errs.append(f"Entscheidungs-Zähler verbiegt sich: {len(faellig)} statt "
                        f"{ENTSCHEIDUNGEN} ({[r['slug'] for r in faellig]})")
        md = as_md(rows, 21, stand=today)
        if "Reserve-Triage" not in md or slugs["gasrechnung"] not in md:
            errs.append("Markdown-Tabelle unvollständig")
        if f"Stand {today.isoformat()}" not in md:
            errs.append("Markdown-Kopf datiert sich selbst statt über `stand` "
                        "(echte Wanduhr im Selbsttest)")
    except Exception as exc:  # noqa: BLE001
        errs.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rows, errs


def _selftest() -> int:
    import time as _zeit
    if _stempel is None or _uhr is None or _MITTAG is None:
        print("🛑 draft_triage-Selbsttest FEHLGESCHLAGEN:\n"
              "  - scripts/selftest_clock.py fehlt oder ist nicht importierbar –\n"
              "    ohne Uhr-Zwang wäre der Selbsttest wieder eine Verabredung mit\n"
              "    dem Kalender (Ausfall vom 18.09.2026, Run 35312783057).")
        return 2
    fehler: list[str] = []
    for tag in PROBETAGE:
        # Uhr-Zwang `strikt`: jede echte Wanduhr-Lesung im Prüfpfad ist ein Fehler
        with _uhr(datetime.datetime.combine(tag, _MITTAG,
                                            tzinfo=datetime.timezone.utc),
                  _UHR_STRIKT, module=[sys.modules[__name__]]):
            _, errs = _szenario(tag)
            fehler += [f"[Testdatum {tag.isoformat()}] {e}" for e in errs]
    # Zeitzone: CI läuft UTC, der Betreiber Europe/Berlin – beides muss dasselbe
    # Ergebnis liefern, sonst entscheidet der Standort über die Ampel.
    if hasattr(_zeit, "tzset"):
        alt = os.environ.get("TZ")
        try:
            for zone in PROBE_ZONEN:
                os.environ["TZ"] = zone
                _zeit.tzset()
                with _uhr(datetime.datetime.combine(PROBETAGE[1], _MITTAG,
                                                    tzinfo=datetime.timezone.utc),
                          _UHR_STRIKT, module=[sys.modules[__name__]]):
                    _, errs = _szenario(PROBETAGE[1])
                    fehler += [f"[TZ={zone}] {e}" for e in errs]
        finally:
            if alt is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = alt
            _zeit.tzset()
    if fehler:
        print("🛑 draft_triage-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ Draft-Triage-Selbsttest: {len(FAELLE)} Fälle × {len(PROBETAGE)} Testdaten"
          f" + {len(PROBE_ZONEN)} Zeitzonen grün (Zustände, Alter exakt, Quell-Defekt,"
          " Schwelle, Git-Nachweis, Uhr-Zwang strikt).")
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
