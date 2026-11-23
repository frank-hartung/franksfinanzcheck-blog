#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKDOWN-STRUKTUR-WACHE – eine geklebte Überschrift ist keine Überschrift.

ANLASS (#1263, 17.11.2026)
=========================
Sechs Live-Artikel trugen eine FAQ-Frage **am Ende des vorigen Absatzes**:

    … senkt deine festen Kosten dauerhaft.### Was kostet ein Kontowechsel?

Markdown erkennt das nicht als Überschrift: Die Frage bleibt Fließtext,
bekommt keinen Anker, fehlt im Inhaltsverzeichnis – und zwei FAQ-Antworten
kleben zu einem Absatz zusammen.

SCHLIMMER ALS KOSMETIK: DIE ZWEI EBENEN WIDERSPRECHEN SICH
---------------------------------------------------------
`layouts/_partials/extend_head.html` baut das FAQPage-Schema, indem es den
FAQ-Abschnitt an der ZEICHENKETTE `### ` splittet – nicht an Zeilenanfängen.
Die geklebte Frage landet deshalb TROTZDEM als `Question` im JSON-LD.
Ergebnis: Die strukturierten Daten behaupten eine Frage, die der Leser
nicht als solche sieht. Genau die Sorte Abweichung, die Google als
irreführend einstuft.

WAS HIER GEPRÜFT WIRD (Markdown-Struktur-Lint, M1–M3)
----------------------------------------------------
  M1  GEKLEBTE ÜBERSCHRIFT  `[^\\s#]#{2,6} ` – Überschriftenzeichen direkt
      hinter Text. Das ist die Klasse aus #1263.
  M2  ÜBERSCHRIFT OHNE TRENNER  `##Titel` (Raute, aber kein Leerzeichen
      danach) mitten in einer Zeile – gleiche Wirkung, andere Schreibweise.
  M3  FLOW-ÜBERSCHRIFT IM ZITAT  Ein `### ` innerhalb einer Zeile, die
      kein Zeilenanfang ist, aber im FAQ-Abschnitt liegt: Diese Frage
      geht ins Schema und nicht in die Seite.

Bewusst NICHT: Stilurteile über Überschriften-Texte (das macht
`check_titles.py`), Abschnittslängen (das macht `struktur_guard.py`).
Diese Wache prüft ausschließlich, ob Markdown noch Markdown IST.

AUSNAHMEN GEHÖREN INS TICKET, NICHT IN DIE WACHE
------------------------------------------------
#1263 lässt EINE Stelle bewusst stehen (Gasabschlag-Artikel), weil dort
noch fünf inhaltliche Befunde offen sind – eine Heilung würde an eine
unentschiedene Textänderung binden. Statt einer stillen Ausnahme im Code
steht sie hier namentlich, mit Datum und Grund, und die Wache sagt bei
jedem Lauf, dass sie greift. Läuft die Frist ab, wird die Ausnahme selbst
zum Befund (fail-closed: eine Ausnahme ohne Ablaufdatum ist eine stille
Abschaltung).

SPERRKLINKE (Haus-Muster wie struktur_guard.py)
-----------------------------------------------
`data/markdown_baseline.json` hält je Datei die akzeptierten Fundstellen.
Bekanntes bleibt still, Neues ist Exit 1, Geheiltes rastet ein.

NUTZUNG
-------
  python3 scripts/markdown_struktur_wache.py            # prüfen
  python3 scripts/markdown_struktur_wache.py --json
  python3 scripts/markdown_struktur_wache.py --md
  python3 scripts/markdown_struktur_wache.py --seed     # Baseline einfrieren
  python3 scripts/markdown_struktur_wache.py --dry-run
  python3 scripts/markdown_struktur_wache.py --selftest

EXIT: 0 = keine neuen Funde · 1 = neuer Fund · 2 = Selbsttest/Setup defekt

KEIN AUTO-FIX – bewusst: Eine geklebte Überschrift zu trennen ändert den
gerenderten Text (Absatzgrenze). Ob dort ein Absatz endet, ist eine
redaktionelle Entscheidung; die Wache nennt Datei und Zeile, sie schreibt
nicht in Artikel.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "markdown_baseline.json"
HISTORY = ROOT / "data" / "markdown_history.jsonl"

CONTENT_GLOBS = (
    "content/posts/*/index.md",
    "content/posts/*.md",
    "content/pillar/*/index.md",
    "content/werkzeuge/*/index.md",
)
SKIP_BASENAMES = {"_index.md"}

# M1/M2: Überschriftenzeichen, das NICHT am Zeilenanfang steht.
#   `[^\s#]` davor schließt den legitimen Fall `  ### Titel` (Einrückung)
#   aus; `#{2,6}` verlangt eine echte Überschrift (ein einzelnes `#`
#   kommt in Hashtags und in `C#` vor und ist kein gliedender Marker).
RE_GESCHWEISST = re.compile(r"[^\s#]#{2,6}[ \t]")
# `##Titel`: eine Raute-Folge, direkt von Text gefolgt. Das Muster braucht
# KEIN Zeichen davor – genau am Zeilenanfang sitzt der häufigste Fall.
# (Die erste Fassung verlangte `[^\s#]` davor und sah deshalb `##Titel`
# am Zeilenanfang nie.)
RE_OHNE_TRENNER = re.compile(r"#{2,6}(?=[^\s#])")
# Zeilen, in denen ein `#` ohnehin Text ist: Code, URLs, HTML, Zitate.
# ACHTUNG: `^\s*#` gehört NICHT hierher – das ist eine gültige Überschrift,
# und M2 (`##Titel`) beginnt ebenfalls mit `#`. Die erste Fassung hatte
# beides vermischt und damit jede Überschrift vor der Prüfung weggeschoben.
RE_ZEILE_AUSGENOMMEN = re.compile(
    r"^\s*(?:>|\||\[|https?://)|`[^`]*`|<[^>]+>")
# Eine Zeile, die SAUBER mit einem gliedernen Marker beginnt (`## Titel`) –
# dort ist die Raute am Zeilenanfang legitim.
RE_ECHTE_UEBERSCHRIFT = re.compile(r"^\s*#{1,6}(?:\s|$)")
RE_FENCE = re.compile(r"^\s*(```|~~~)")

# ----------------------------------------------------------------------
#  Befristete Baseline-Einträge (die EINE Stelle aus #1263)
#  ------------------------------------------------------------------
#  #1263 lässt eine Fundstelle bewusst stehen: Der Gasabschlag-Artikel hat
#  fünf offene inhaltliche Befunde, eine Heilung würde an unentschiedenen
#  Text binden. Statt einer Ausnahme im Code (die bei jedem Lauf still
#  wirkt) steht die Stelle HIER mit Ablaufdatum: Sie ist im Bericht
#  sichtbar als „bekannt (befristet)“, und nach dem Stichtag wird sie
#  automatisch zum NEUEN Befund (fail-closed). Ein Eintrag ohne Datum ist
#  ein Konfigurationsfehler, kein Freibrief.
# ----------------------------------------------------------------------
# LEER seit 23.11.2026. Der einzige Eintrag (Gasabschlag, bis 31.01.2027)
# ist gegengestandslos geworden: `main` hat die geklebte Überschrift in
# #1329 (`371835702`) geheilt – `erhebe()` findet im Bestand 0 Funde.
#
# Eine Befristung, die einen nicht mehr existierenden Befund schützt, ist
# nicht harmlos: Die Uhr-Probe („muss an jedem Kalendertag grün sein") hätte
# ab dem 31.01.2027 einen Befund erwartet, den es nicht gibt, und wäre an
# einem Datum rot geworden, an dem niemand etwas geändert hat. Genau diese
# Zeitbombe war der Anlass für das Verfallsdatum – sie darf nicht durch die
# eigene Ausnahme entstehen.
#
# Die Struktur bleibt (die Selbsttests prüfen sie weiter): Ein künftiger
# Eintrag braucht Datei, `bis` und `grund`, und die Uhr-Probe fängt ihn.
BEFRISTET: list[dict] = []


def befristete_grenze(datei: str) -> _dt.date | None:
    for e in BEFRISTET:
        if e["datei"] == datei:
            return _dt.date.fromisoformat(e["bis"])
    return None


def befristet_abgelaufen(heute: _dt.date) -> list[dict]:
    return [e for e in BEFRISTET
            if heute > _dt.date.fromisoformat(e["bis"])]


# ======================================================================
#  Befund
# ======================================================================
def _befund(datei: str, zeile: int, spalte: int, regel: str, text: str) -> dict:
    return {"datei": datei, "zeile": zeile, "spalte": spalte,
            "regel": regel, "text": text}


# ======================================================================
#  Prüfung einer Datei
# ======================================================================
def pruefe_text(text: str, datei: str = "x.md",
                heute: _dt.date | None = None) -> list[dict]:
    """Markdown-Struktur-Lint. Gibt Befunde als Liste von dicts."""
    heute = heute or _dt.date.today()
    befunde: list[dict] = []
    im_fence = False
    im_faq = False

    for nr, roh in enumerate(text.splitlines(), 1):
        zeile = roh.rstrip("\r")

        # Code-Blöcke sind Text, kein Markdown.
        if RE_FENCE.match(zeile):
            im_fence = not im_fence
            continue
        if im_fence or not zeile.strip():
            continue
        # Frontmatter überspringen (zwischen zwei `---`).
        if nr == 1 and zeile.strip() == "---":
            im_frontmatter = True
            continue
        if "im_frontmatter" in dir() and locals().get("im_frontmatter"):
            if zeile.strip() == "---":
                im_frontmatter = False
            continue

        # FAQ-Kontext: Das Schema liest ab der FAQ-Überschrift.
        if re.match(r"^#{2,3}\s+(?:Häufige Fragen|FAQ|Fragen\s*&\s*Antworten)",
                    zeile, re.I):
            im_faq = True

        if RE_ZEILE_AUSGENOMMEN.search(zeile):
            continue
        # Gültige Überschrift am Zeilenanfang: Raute legitim. Ein Duplikat
        # ODER ein Fehler kann trotzdem im Text dahinter stecken, deshalb
        # wird der Text nach dem Marker weiter geprüft (nicht der Marker).
        echte = RE_ECHTE_UEBERSCHRIFT.match(zeile)
        pruefzeile = zeile[echte.end():] if echte else zeile
        versatz = echte.end() if echte else 0

        # M1: Überschrift klebt am Text davor.
        for treffer in RE_GESCHWEISST.finditer(pruefzeile):
            stelle = treffer.start() + versatz
            befunde.append(_befund(
                datei, nr, stelle + 1, "M1",
                f"Überschrift klebt am Text davor: "
                f"„…{zeile[max(0, stelle - 18):stelle + 22].strip()}…“ – "
                f"Markdown rendert sie als Fließtext (kein Anker, kein "
                f"Inhaltsverzeichnis)."))
            break                          # eine Meldung je Zeile genügt

        # M2: Raute ohne Leerzeichen (`##Titel`). Feuert M1 auf dieser
        # Zeile, ist die Ursache schon benannt – keine zweite Meldung für
        # dieselbe Stelle.
        for treffer in ([] if any(b["regel"] == "M1" and b["zeile"] == nr
                                  for b in befunde)
                        else RE_OHNE_TRENNER.finditer(pruefzeile)):
            stelle = treffer.start() + versatz
            befunde.append(_befund(
                datei, nr, stelle + 1, "M2",
                f"Überschrift ohne Leerzeichen nach der Raute: "
                f"„…{zeile[stelle:stelle + 24].strip()}…“ "
                f"– ohne Trenner liest Markdown sie nicht als Überschrift."))
            break

        # M3: Flow-Frage im FAQ-Abschnitt, die ins Schema, aber nicht in
        # die Seite geht (die Klasse, die #1263 erst gefährlich macht).
        if im_faq and re.search(r"\S[ \t]*#{3}[ \t]+\S", pruefzeile):
            befunde.append(_befund(
                datei, nr, 1, "M3",
                "FAQ-Frage steht mitten in einer Textzeile – sie landet im "
                "FAQPage-Schema (Split an der Zeichenkette „### “), ist auf "
                "der Seite aber keine Überschrift. Schema und Seite sagen "
                "dann nicht dasselbe."))
            break

    return befunde


def datei_pruefen(pfad: Path, heute: _dt.date | None = None) -> list[dict]:
    try:
        text = pfad.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return pruefe_text(text, relativ(pfad), heute)


def relativ(pfad: Path) -> str:
    try:
        return pfad.relative_to(ROOT).as_posix()
    except ValueError:
        return str(pfad)


def sammle_dateien(root: Path = ROOT) -> list[Path]:
    dateien: list[Path] = []
    for muster in CONTENT_GLOBS:
        dateien.extend(sorted(root.glob(muster)))
    return [p for p in sorted(set(dateien))
            if p.is_file() and p.name not in SKIP_BASENAMES]


def erhebe(root: Path = ROOT, heute: _dt.date | None = None) -> tuple[dict, int]:
    """{datei: [fundstellen…]} für alle Dateien mit Befunden."""
    heute = heute or _dt.date.today()
    stand: dict[str, list[dict]] = {}
    dateien = sammle_dateien(root)
    for pfad in dateien:
        befunde = datei_pruefen(pfad, heute)
        if befunde:
            stand[relativ(pfad)] = befunde
    return stand, len(dateien)


# ======================================================================
#  Baseline (Sperrklinke)
# ======================================================================
def lade_baseline() -> dict:
    if not BASELINE.exists():
        return {}
    try:
        daten = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return daten.get("dateien") or {}


def _schreibe_baseline(stand: dict, dry_run: bool = False) -> None:
    if dry_run:
        return
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps({
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "hinweis": "Sperrklinke: nur abwärts. Erzeugt von "
                   "scripts/markdown_struktur_wache.py --seed.",
        "dateien": dict(sorted(stand.items())),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _schreibe_history(neu: int, bekannt: int, dateien: int,
                      dry_run: bool) -> None:
    if dry_run:
        return
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    zeile = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "module": "markdown_struktur_wache", "action": "check",
             "input": {"dateien": dateien},
             "output": {"neue_funde": neu, "bekannte_funde": bekannt},
             "status": "issues" if neu else "ok",
             "critical": False, "commit": None}
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def _signatur(fund: dict) -> str:
    """Eine Fundstelle ist (Regel, Zeile, Spalte) – Zeilennummern verschieben
    sich beim Redigieren, deshalb zählt die Regel je Datei und Zeile."""
    return f"{fund['regel']}@{fund['zeile']}"


def vergleiche(stand: dict, baseline: dict,
               heute: _dt.date | None = None) -> dict:
    """Bewertet den Stand gegen die Sperrklinke.

    `ablauf`: Dateien, deren befristeter Eintrag heute abgelaufen ist. Sie
    zählen als NEU – eine Befristung, die nach dem Stichtag nichts bewirkt,
    wäre eine stille Abschaltung (genau der Fehler, den #1263 verhindert).
    """
    heute = heute or _dt.date.today()
    neu, bekannt, geheilt, ablauf = [], [], [], []
    for datei, befunde in sorted(stand.items()):
        alt = baseline.get(datei)
        if alt is None:
            neu.append(datei)
            continue
        bis = befristete_grenze(datei)
        if bis is not None and heute > bis:
            ablauf.append(datei)
            neu.append(datei)
            continue
        alt_sig = {_signatur(f) if isinstance(f, dict) else str(f) for f in alt}
        jetzt = {_signatur(f) for f in befunde}
        if jetzt - alt_sig:
            neu.append(datei)
        else:
            bekannt.append(datei)
    for datei in baseline:
        if datei not in stand:
            geheilt.append(datei)
    return {"neu": neu, "bekannt": bekannt, "geheilt": geheilt,
            "ablauf": ablauf}


def klinke_einrasten(stand: dict, baseline: dict) -> dict:
    """Bekannte Funde einfrieren, NEUE nicht (kein Wegwischer)."""
    neu = {}
    for datei, befunde in sorted(stand.items()):
        alt = baseline.get(datei)
        if alt is None:
            neu[datei] = befunde
            continue
        alt_sig = {_signatur(f) if isinstance(f, dict) else str(f) for f in alt}
        jetzt = {_signatur(f) for f in befunde}
        if jetzt <= alt_sig:
            neu[datei] = befunde            # gleich oder besser: übernehmen
        else:
            neu[datei] = alt                # Verschlechterung nicht einfrieren
    return neu


# ======================================================================
#  Ausgabe
# ======================================================================
def bericht_md(stand: dict, ergebnis: dict, heute: _dt.date) -> str:
    anz = sum(len(v) for v in stand.values())
    zeilen = ["### 🔗 Markdown-Struktur (#1263)", ""]
    zeilen.append(f"**{anz} Fundstelle(n)** in **{len(stand)} Datei(en)** · "
                  f"**{len(ergebnis['neu'])} neu** · "
                  f"**{len(ergebnis['bekannt'])} bekannt** · "
                  f"**{len(ergebnis['geheilt'])} geheilt**")
    if ergebnis["neu"]:
        zeilen += ["", "| Datei:Zeile | Regel | Befund |", "|---|---|---|"]
        for datei in ergebnis["neu"]:
            for f in stand[datei]:
                zeilen.append(f"| `{datei}:{f['zeile']}` | {f['regel']} | "
                              f"{f['text'].replace('|', chr(92) + '|')} |")
    if ergebnis["bekannt"]:
        zeilen += ["", f"{len(ergebnis['bekannt'])} bekannte Fundstelle(n) "
                       "(Baseline, #1263):", ""]
        for datei in ergebnis["bekannt"]:
            for f in stand[datei]:
                zeilen.append(f"- `{datei}:{f['zeile']}` ({f['regel']})")
    for e in BEFRISTET:
        bis = _dt.date.fromisoformat(e["bis"])
        if heute > bis:
            zeilen += ["", f"❌ **Befristung abgelaufen ({e['bis']})** – die "
                           f"Stelle ist jetzt ein NEUER Befund: "
                           f"`{e['datei']}`"]
        else:
            zeilen += ["", f"⏳ **Befristet bis {e['bis']}:** "
                           f"`{e['datei'].split('/')[-2]}` – {e['grund']}"]
    return "\n".join(zeilen) + "\n"


# ======================================================================
#  Selbsttest
# ======================================================================
_GUT = """---
title: "Probe"
---

Ein Absatz mit normalem Text.

## Eine echte Überschrift

Noch ein Absatz.

### Frage? Antwort steht hier.

## Häufige Fragen

### Was kostet das?
Eine Antwort mit ausreichend Text, damit sie zählt.
"""

_GEKLEBT = _GUT.replace(
    "Noch ein Absatz.",
    "Noch ein Absatz.### Was kostet das?")

_OHNE_TRENNER = _GUT.replace("## Eine echte Überschrift", "##Eine echte Überschrift")


def run_selftest() -> int:
    fehler: list[str] = []
    heute = _dt.date(2026, 11, 22)

    def regeln(text: str) -> list[str]:
        return sorted({b["regel"] for b in pruefe_text(text, "x.md", heute)})

    # 1) Die saubere Fassung darf NICHTS melden (kein Fehlalarm-Generator).
    if regeln(_GUT):
        fehler.append(f"sauberes Markdown meldet {regeln(_GUT)}")
    # 2) Die Klasse aus #1263 – Wort für Wort.
    if "M1" not in regeln(_GEKLEBT):
        fehler.append("geklebte Überschrift wird nicht erkannt")
    # 3) Raute ohne Leerzeichen.
    if "M2" not in regeln(_OHNE_TRENNER):
        fehler.append("`##Titel` ohne Trenner wird nicht erkannt")
    # 4) Ein `#` im Code-Block ist Text, keine Überschrift.
    if regeln("```\nnpm run x ### y\n```\n"):
        fehler.append("Code-Block wird als Überschrift gelesen")
    # 5) Ein Hashtag ist keine Überschrift (`#finanzen`).
    if regeln("Ein Absatz über #finanzen und #sparen.\n"):
        fehler.append("Hashtag wird als Überschrift gelesen")
    # 6) Ein Link mit Fragment ist Text.
    if regeln("Siehe [die FAQ](/posts/x/#antwort) für Details.\n"):
        fehler.append("Link mit Fragment wird als Überschrift gelesen")
    # 7) `C#` und ähnliche Einzelzeichen sind kein Marker.
    if regeln("Wir programmieren in C# und F#.\n"):
        fehler.append("`C#` wird als Überschrift gelesen")
    # 8) M3: Flow-Frage im FAQ-Abschnitt – Schema und Seite widersprechen sich.
    faq_flow = _GUT.replace(
        "### Was kostet das?",
        "### Was kostet das? Und was ### Wann zählt es?")
    if "M3" not in regeln(faq_flow):
        fehler.append("Flow-Frage im FAQ wird nicht erkannt")
    # 9) Dieselbe Flow-Frage AUSSERHALB des FAQ ist kein M3 (sie geht dann
    #    auch nicht ins Schema).
    if "M3" in regeln(_GUT.replace("Noch ein Absatz.",
                                   "Noch ein Absatz mit ### Erwähnung.")):
        fehler.append("M3 schlägt außerhalb des FAQ an")
    # 10) Die Befristung: Die Stelle ist ein ganz normaler Befund und steht
    #     als BEKANNT in der Baseline – sichtbar in jedem Bericht, nicht
    #     still im Code weggedrückt.
    #
    #     23.11.2026: Der echte Eintrag (Gasabschlag, #1263) ist entfallen,
    #     weil `main` die Stelle in #1329 geheilt hat. Der MECHANISMUS muss
    #     aber weiter geprüft werden – sonst wäre die nächste Ausnahme
    #     ungeprüft. Deshalb trägt der Selbsttest seinen eigenen, klar
    #     markierten Fall ein und räumt ihn wieder ab. Eine Ausnahme, die
    #     niemand mehr testet, ist genau die stille Abschaltung, gegen die
    #     sie gebaut wurde.
    probe_datei = "content/posts/__selbsttest__/index.md"
    probe_eintrag = {"datei": probe_datei, "bis": "2027-01-31",
                     "grund": "Selbsttest: prüft den Ablauf-Mechanismus."}
    if not pruefe_text(_GEKLEBT, probe_datei, heute):
        fehler.append("Testaufbau: die geklebte Stelle wird nicht erkannt")
    probe_stand = {probe_datei: pruefe_text(_GEKLEBT, probe_datei, heute)}
    BEFRISTET.append(probe_eintrag)
    try:
        e = vergleiche(probe_stand, probe_stand, heute)
        if e["bekannt"] != [probe_datei] or e["neu"]:
            fehler.append(f"Befristung: bekannte Stelle nicht als bekannt: {e}")
        # 11) NACH dem Stichtag ist dieselbe Stelle ein NEUER Befund –
        #     eine Befristung, die nichts bewirkt, wäre eine stille Abschaltung.
        nach_ablauf = _dt.date(2027, 2, 1)
        e = vergleiche(probe_stand, probe_stand, nach_ablauf)
        if e["neu"] != [probe_datei] or e["ablauf"] != [probe_datei]:
            fehler.append(f"Befristung: nach Ablauf kein neuer Befund: {e}")
        if not befristet_abgelaufen(nach_ablauf):
            fehler.append("abgelaufene Befristung wird nicht benannt")
    finally:
        BEFRISTET.remove(probe_eintrag)
    # 12) Ein Eintrag ohne ISO-Datum oder ohne Grund ist ein Setup-Fehler.
    for b in BEFRISTET:
        try:
            _dt.date.fromisoformat(b["bis"])
        except ValueError:
            fehler.append(f"Befristung {b['datei']} hat kein ISO-Datum")
        if not b.get("grund"):
            fehler.append(f"Befristung {b['datei']} hat keinen Grund")
    # 13) Sperrklinke: bekannt bleibt still, neu wird rot, geheilt rastet ein.
    stand = {"a": [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]}
    basis = {"a": [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]}
    if vergleiche(stand, basis)["neu"]:
        fehler.append("Klinke: bekannter Fund als neu gemeldet")
    if vergleiche(stand, {})["neu"] != ["a"]:
        fehler.append("Klinke: neuer Fund nicht gemeldet")
    if vergleiche({}, basis)["geheilt"] != ["a"]:
        fehler.append("Klinke: Heilung nicht erkannt")
    schlechter = {"a": [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""},
                        {"regel": "M1", "zeile": 9, "spalte": 1, "text": ""}]}
    if not vergleiche(schlechter, basis)["neu"]:
        fehler.append("Klinke: zusätzliche Fundstelle nicht gemeldet")
    eingefroren = klinke_einrasten(schlechter, basis)
    if len(eingefroren["a"]) != 1:
        fehler.append("Klinke: neuer Fund wurde eingefroren (Wegwischer)")

    if fehler:
        print("🛑 Markdown-Struktur-Wache Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("   -", f)
        return 2
    print("✅ Markdown-Struktur-Wache Selbsttest: 22 Proben bestanden.")
    return 0


# ======================================================================
#  main
# ======================================================================
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Markdown-Struktur-Wache (#1263)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    # Hausregel: erst der Detektor, dann der Prüfling. Der Selbsttest läuft
    # IMMER – eine kaputte Wache darf keinen Stand einfrieren. Bei --json/--md
    # wandert sein Bericht nach stderr, damit der Datenstrom sauber bleibt
    # (ein Grußtext vor dem JSON bricht jeden Parser).
    maschinenformat = args.json or args.md
    puffer = io.StringIO()
    if run_selftest_redirect(puffer) != 0:
        sys.stderr.write(puffer.getvalue())
        return 2
    if args.selftest:
        sys.stdout.write(puffer.getvalue())
        return 0
    if not maschinenformat:
        sys.stderr.write(puffer.getvalue())

    heute = _dt.date.today()
    stand, dateien = erhebe(heute=heute)
    baseline = lade_baseline()
    ergebnis = vergleiche(stand, baseline, heute)

    if args.seed:
        _schreibe_baseline(stand, args.dry_run)
        print(f"🔒 Baseline eingefroren: {len(stand)} Datei(en) mit Funden → "
              f"{BASELINE.relative_to(ROOT)}")
        return 0

    # 23.11.2026: `--json` und `--md` sind ABFRAGEN, keine Läufe, die den
    # Bestand verändern. Vorher schrieb ein `--json`-Aufruf die Baseline neu
    # (mit leerem Bestand: auf 0 Einträge) und riss damit den nachfolgenden
    # Test um – der Fehler saß nicht im Test, sondern hier. Wer den Bestand
    # verändern will, sagt es: `--seed` (einfrieren) oder ein Lauf ohne
    # Maschinenformat (einrasten). Dieselbe Regel gilt für die Historie.
    schreibend = not maschinenformat and not args.dry_run
    if baseline and schreibend:
        _schreibe_baseline(klinke_einrasten(stand, baseline), args.dry_run)
    _schreibe_history(len(ergebnis["neu"]), len(ergebnis["bekannt"]),
                      dateien, args.dry_run or not schreibend)

    if args.json:
        print(json.dumps({
            "dateien": dateien,
            "fundstellen": sum(len(v) for v in stand.values()),
            "neu": ergebnis["neu"], "bekannt": ergebnis["bekannt"],
            "geheilt": ergebnis["geheilt"],
            "befristet_abgelaufen": [e["datei"] for e in
                                     befristet_abgelaufen(heute)],
            "funde": stand,
        }, ensure_ascii=False, indent=2))
    elif args.md:
        print(bericht_md(stand, ergebnis, heute))
    else:
        by = sum(len(v) for v in stand.values())
        print(f"Markdown-Struktur: {dateien} Dateien | {by} Fundstelle(n) | "
              f"neu: {len(ergebnis['neu'])} | bekannt: "
              f"{len(ergebnis['bekannt'])} | geheilt: {len(ergebnis['geheilt'])}")
        for datei in ergebnis["neu"]:
            for f in stand[datei]:
                print(f"  ❌ NEU {datei}:{f['zeile']}:{f['spalte']} "
                      f"({f['regel']}) {f['text']}")
        for datei in ergebnis["bekannt"]:
            for f in stand[datei]:
                print(f"  · bekannt {datei}:{f['zeile']} ({f['regel']})")
        for e in befristet_abgelaufen(heute):
            print(f"  ❌ Befristung abgelaufen: {e['datei']} ({e['bis']}) – "
                  f"jetzt ein NEUER Befund")

    return 1 if ergebnis["neu"] else 0


def run_selftest_redirect(ziel) -> int:
    """Selbsttest mit umgeleiteter Ausgabe (für --json/--md saubere Ströme)."""
    alt = sys.stdout
    sys.stdout = ziel
    try:
        return run_selftest()
    finally:
        sys.stdout = alt


if __name__ == "__main__":
    sys.exit(main())
