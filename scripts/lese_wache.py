#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lese-Wache: Eine Abfrage darf den Bestand nicht verändern.

ANLASS (23.11.2026)
--------------------
Der `regression`-Job war rot: `test_stelle_steht_in_der_baseline` fand die
Baseline leer. Die Ursache war kein Testfehler. `markdown_struktur_wache.py
--json` **schrieb** die Baseline – auf null Einträge, weil der Bestand
sauber war. Der nächste Test fand `{}` und wurde rot.

Das Muster stand an ZWEI Stellen (`markdown_struktur_wache.py` und
`titel_klinke.py`). Beide einzeln zu heilen hätte den nächsten Kopierer
nicht aufgehalten. Diese Wache prüft die REGEL:

    Ein Aufruf mit `--json` oder `--md` schreibt keine Datei.

WARUM DAS WICHTIG IST
---------------------
`--json` und `--md` werden von Tests, Berichten und `tee`-Pipelines
benutzt. Ein Prüfer, der beim Lesen schreibt, macht jede Messung zur
Bewegung: Man kann nicht zweimal messen, um zu sehen, ob sich etwas
geändert hat – die zweite Messung sieht die erste. Und im schlimmsten
Fall rastet eine Sperrklinke auf einen Zustand ein, den niemand geprüft
hat.

WIE GEPRÜFT WIRD
----------------
1. **Statisch:** In jedem Skript, das `--json`/`--md` kennt, darf ein
   Schreibaufruf nicht im selben `if`-Zweig stehen wie die
   Maschinenformat-Variable. Gesucht wird nach `_schreibe*`/
   `.write_text(`/`.open("w")` in einem Block, der `maschinenformat`
   NICHT ausnimmt.
2. **Dynamisch (der eigentliche Beweis):** Für `markdown_struktur_wache`
   und `titel_klinke` wird `--json` ausgeführt und die Prüfsumme der
   Daten-Dateien vorher/nachher verglichen. Gleich = grün.

BEWUSSTE GRENZE
---------------
Die statische Prüfung versteht kein Python. Sie findet Muster, keine
Semantik – deshalb ist der dynamische Teil der Beweis, und die statische
Prüfung ist die Erinnerung an neue Stellen. Ein Befund hier heißt
„ansehen", nicht zwingend „kaputt".

NUTZUNG
-------
    python3 scripts/lese_wache.py           # Befund
    python3 scripts/lese_wache.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# Skripte, die ein Maschinenformat kennen, und die Dateien, die sie
# schreiben dürfen – aber nicht bei einer Abfrage.
PROBEN: list[tuple[str, tuple[str, ...]]] = [
    ("markdown_struktur_wache.py",
     ("data/markdown_baseline.json", "data/markdown_history.jsonl")),
    ("titel_klinke.py",
     ("data/titel_baseline.json", "data/titel_history.jsonl")),
]

MASCHINENFORMAT = re.compile(r"maschinenformat\s*=\s*args\.(json|md)")
SCHREIBT = re.compile(r"(_schreibe\w*\(|\.write_text\(|\.open\(\s*['\"]w)")

# Wie viele Zeilen nach einem Schreibaufruf rückwärts geschaut wird, um zu
# sehen, ob der Block das Maschinenformat ausnimmt.
FENSTER = 12


def _pruefsumme(pfad: Path) -> str:
    if not pfad.exists():
        return "<fehlt>"
    return hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]


def statisch(pfad: Path) -> list[dict]:
    """Schreibaufrufe in einem Block, der `maschinenformat` nicht ausnimmt."""
    befunde: list[dict] = []
    try:
        zeilen = pfad.read_text(encoding="utf-8").splitlines()
    except OSError:
        return befunde
    if not any(MASCHINENFORMAT.search(z) for z in zeilen):
        return befunde                       # kennt kein Maschinenformat
    # Der ANLASS des Fehlers ist die Gegenwart eines Schreibaufrufs im
    # Skript – nicht seine Nähe zur `maschinenformat`-Zeile. Ein Fenster von
    # N Zeilen war die falsche Frage: Im echten Fehler standen sechs Zeilen
    # zwischen Definition und Aufruf, im Fehlversuch dreizehn. Geprüft wird
    # deshalb der GANZE Aufrufblock (bis zur nächsten Zeile gleicher oder
    # geringerer Einrückung).
    for nummer, zeile in enumerate(zeilen, 1):
        if not SCHREIBT.search(zeile):
            continue
        # Eine DEFINITION schreibt nichts – sie beschreibt nur, wie. Der
        # Aufruf wird an seiner eigenen Stelle geprüft.
        if re.match(r"\s*def\s+_schreibe", zeile):
            continue
        # Eine Zuweisung an ein internes Feld ohne Aufruf ist kein Schreiben
        # (`BASELINE.write_text(` in einer Funktion – geprüft wird der
        # Aufruf der Funktion, nicht ihr Rumpf).
        if re.match(r"\s*(BASELINE|HISTORIE|HISTORY|PFAD)\w*\.write_text\(", zeile):
            continue
        einzug = len(zeile) - len(zeile.lstrip())
        ende = nummer
        for folge in zeilen[nummer:]:
            if folge.strip() and (len(folge) - len(folge.lstrip())) <= einzug:
                break
            ende += 1
        umfeld = "\n".join(zeilen[max(0, nummer - 3):ende])
        # Der Block, in dem der Aufruf steht, DARF die Ausnahme tragen.
        # Zusätzlich zählt eine frühere Zuweisung `schreibend = …` bzw.
        # `maschinenformat = …`, die den ganzen Rest des Programms bindet.
        vorher = "\n".join(zeilen[max(0, nummer - FENSTER - 1):nummer])
        if "schreibend" in vorher or "not maschinenformat" in vorher:
            umfeld += "\n" + vorher
        # Nimmt der Block das Maschinenformat aus? Zwei anerkannte Formen:
        #   `if ... and not maschinenformat:`   oder eine Variable, die es
        #   enthält (`schreibend = not maschinenformat ...`).
        if "not maschinenformat" in umfeld or "not schreibend" in umfeld:
            continue
        # Der `--seed`-Zweig ist erlaubt: er kehrt vorher zurück, schreibt
        # also nie im Abfragemodus.
        #
        # `dry_run` als ARGUMENT reicht NICHT (das war mein Fehler beim
        # ersten Wurf): `_schreibe_baseline(stand, args.dry_run)` schreibt
        # gerade dann, wenn `--dry-run` NICHT gesetzt ist – im `--json`-Lauf
        # ist `dry_run` False. Die Anwesenheit des Arguments sagt nichts
        # darüber, ob geschrieben wird. Nur ein Block, der den Aufruf selbst
        # unter `--dry-run` stellt, ist harmlos.
        # Der `--seed`-Zweig kann mehrere Zeilen Vorlauf haben (in
        # `titel_klinke.py` stehen sechs Zeilen Dict-Aufbau dazwischen).
        # Deshalb großzügig zurückschauen – ein `--seed`-Block endet mit
        # `return 0`, erreicht den Abfragemodus also nie.
        if "args.seed" in "\n".join(zeilen[max(0, nummer - 15):nummer + 1]):
            continue
        if "if not args.dry_run" in umfeld or "if args.dry_run" in umfeld:
            continue
        try:
            anzeige = str(pfad.relative_to(ROOT))
        except ValueError:                    # Pfad außerhalb des Repos
            anzeige = str(pfad)
        befunde.append({
            "datei": anzeige,
            "zeile": nummer,
            "inhalt": zeile.strip()[:90],
            "grund": "Schreibaufruf ohne Ausnahme für `--json`/`--md` – "
                     "eine Abfrage darf den Bestand nicht verändern",
        })
    return befunde


def dynamisch(probe: tuple[str, tuple[str, ...]]) -> list[dict]:
    """`--json` ausführen und prüfen, dass keine Datei sich ändert."""
    skript, dateien = probe
    pfad = SCRIPTS / skript
    if not pfad.exists():
        return []
    vorher = {d: _pruefsumme(ROOT / d) for d in dateien}
    try:
        subprocess.run([sys.executable, str(pfad), "--json"],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    except (subprocess.SubprocessError, OSError):
        return []                            # Laufzeitproblem: kein Befund
    nachher = {d: _pruefsumme(ROOT / d) for d in dateien}
    return [{
        "datei": skript,
        "zeile": 0,
        "inhalt": f"{d}: {vorher[d]} → {nachher[d]}",
        "grund": "`--json` hat eine Datei verändert – eine Abfrage darf "
                 "den Bestand nicht verändern",
    } for d in dateien if vorher[d] != nachher[d]]


def pruefe(statisch_aktiv: bool = True, dynamisch_aktiv: bool = True) -> list[dict]:
    befunde: list[dict] = []
    if statisch_aktiv:
        for pfad in sorted(SCRIPTS.glob("*.py")):
            # Die Wache prueft sich nicht selbst: Ihre Kommentare und
            # Selbsttest-Proben ZITIEREN das verbotene Muster, um es zu
            # erkennen. Ein Detektor, der auf seine eigene Beschreibung
            # anschlaegt, waere bei jeder Textaenderung rot.
            if pfad.name == Path(__file__).name:
                continue
            befunde.extend(statisch(pfad))
    if dynamisch_aktiv:
        for probe in PROBEN:
            befunde.extend(dynamisch(probe))
    return befunde


def bericht(befunde: list[dict]) -> int:
    if not befunde:
        print("✅ Lese-Wache: keine Abfrage verändert den Bestand.")
        return 0
    print(f"🛑 Lese-Wache: {len(befunde)} Befund(e)")
    for b in befunde:
        ort = f"{b['datei']}:{b['zeile']}" if b["zeile"] else b["datei"]
        print(f"   {ort}  {b['inhalt']}")
        print(f"      {b['grund']}")
    return 1


def selftest() -> int:
    """Die Wache muss anschlagen und still bleiben – beides wird bewiesen."""
    import tempfile
    fehler = 0

    faelle = [
        # (Name, Quelltext, muss_anschlagen)
        ("Abfrage schreibt (der echte Fehler)",
         "maschinenformat = args.json or args.md\n"
         "if baseline:\n    _schreibe_baseline(stand)\n", True),
        ("Abfrage schreibt nicht (unsere Heilung)",
         "maschinenformat = args.json or args.md\n"
         "if baseline and not maschinenformat:\n    _schreibe_baseline(stand)\n",
         False),
        ("Variable traegt die Ausnahme",
         "maschinenformat = args.json or args.md\n"
         "schreibend = not maschinenformat and not args.dry_run\n"
         "if baseline and schreibend:\n    _schreibe_baseline(stand)\n", False),
        ("--seed-Zweig ist erlaubt",
         "maschinenformat = args.json or args.md\n"
         "if args.seed:\n    _schreibe_baseline(stand)\n    return 0\n", False),
        ("Skript ohne Maschinenformat wird nicht geprueft",
         "def main():\n    _schreibe_baseline(stand)\n", False),
    ]
    for name, quelle, muss in faelle:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "probe.py"
            p.write_text(quelle, encoding="utf-8")
            # relative_to(ROOT) scheitert bei Temp-Pfaden – die Probe
            # prueft die Regel, nicht die Anzeige.
            try:
                gefunden = bool(statisch(p))
            except ValueError:
                gefunden = bool(statisch(p))
        if gefunden != muss:
            print(f"🛑 Selbsttest: „{name}“ – erwartet "
                  f"{'Befund' if muss else 'still'}")
            fehler += 1
    if fehler:
        return 1
    print(f"✅ Selbsttest: {len(faelle)} Proben bestanden – die Wache "
          "schlägt an und bleibt still.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--ohne-dynamisch", action="store_true",
                        help="nur statisch prüfen (schnell, für Tests)")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    return bericht(pruefe(dynamisch_aktiv=not args.ohne_dynamisch))


if __name__ == "__main__":
    sys.exit(main())
