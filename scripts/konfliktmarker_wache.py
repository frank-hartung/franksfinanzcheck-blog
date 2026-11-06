#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
konfliktmarker_wache.py – Der Konfliktmarker-Wächter (Repo-weit, fail-closed)
=============================================================================

WARUM ES DIESE WACHE GIBT (06.11.2026, Vorgang WF-8F6F / #1073, PR #1088)
-----------------------------------------------------------------------------
Am 05.11.2026 landete ein unaufgelöst aufgelöster Merge in `main`:
`BEFUND-AKTE.md` und `data/faktenfrische_befunde_state.json` enthielten die
Markerzeilen `<<<<<<< HEAD` … `=======` … `>>>>>>> f77c0af` – committet,
gepusht und auf `main` gemerged, obwohl der Bestand vorher grün war.

  * Der Artefakt-Wächter (A4) prüft nur `data/**` (JSON/JSONL/YAML) und
    Frontmatter – er sah die `.md` nicht, und die `.json` erst einen Tag
    später.
  * Der Deploy-Schritt „Merge-Marker-Schutz" prüft nur `content/`,
    `layouts/`, `static/`, `hugo.toml` mit drei Zeilenmustern – `data/**`
    und die Repo-Wurzel waren ungeschirmt.
  * Die Python-Syntax-Notbremse in `git_sync.sh` (#864) deckt nur `.py`.

Folge: Ein kaputtes Maschinen-Artefakt lag auf `main`, ohne dass irgendein
Tor es sah – und die Befund-Akte lieferte dem Menschen eine kaputte
Arbeitsliste. Genau die Klasse „Maschinen-Merge committet beide Seiten"
(GitHub-Merge-Button, manuelle Konfliktauflösung, vergessener Index).

WAS DIE WACHE TUT
-----------------
Sie durchsucht **alle getrackten Textdateien** (oder eine Auswahl) nach
unaufgelösten Merge-Blöcken – mit Zustandsautomat, nicht mit drei
Zeilenmustern:

    ACHTUNG: `=======` allein ist KEIN Fund. Haus-Docstrings benutzen
    Zeilen aus Sieben+ Gleichheitszeichen als Überschrift (z. B. „NUTZUNG\\n
    =======") – ein naiver `^={7,}$`-Grep meldet hunderte Falschpositive.

Ein Fund ist nur ein vollständiger oder verwaister Block:

  * `<<<<<<< …` öffnet einen Block (daneben steht nie eine gültige Zeile),
  * `=======` innerhalb eines offenen Blocks ist die Mitte,
  * `>>>>>>> …` schließt ihn,
  * `|||||||` (Basis, diff3-Stil) innerhalb eines Blocks wird genannt,
  * `<<<` ohne Schließen (EOF) und `>>>` ohne Öffnen sind Funde.

Modi:
  (Standard)          alle getrackten Dateien (`git ls-files`)
  --staged            der gestagete Stand (Index, `git show :<pfad>`) – für
                      den Commit-Pfad (git_sync.sh, pre-commit-Haken)
  --range A...B       nur die zwischen A und B geänderten Dateien – für den
                      Push-Pfad (git_sync.sh), liest die BLOBs aus HEAD
  --paths P …         nur diese Dateien (Arbeitsbaum)

Exit: 0 = sauber · 1 = mindestens ein Fund (fail-closed) · 2 = Werkzeugfehler
      oder Selbsttest rot.

NUTZUNG
    python3 scripts/konfliktmarker_wache.py            # ganzes Repo prüfen
    python3 scripts/konfliktmarker_wache.py --staged   # Index prüfen
    python3 scripts/konfliktmarker_wache.py --range origin/main...HEAD
    python3 scripts/konfliktmarker_wache.py --paths data/faktenfrische_befunde_state.json
    python3 scripts/konfliktmarker_wache.py --selftest
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KONFLIKT_START = re.compile(r"^<{7,}(\s|$)")   # Block-Anfang (<<<<<<< HEAD)
KONFLIKT_MITTE = re.compile(r"^={7,}(\s|$)")   # Block-Mitte  (=======)
KONFLIKT_ENDE = re.compile(r"^>{7,}(\s|$)")    # Block-Ende   (>>>>>>> branch)
KONFLIKT_BASIS = re.compile(r"^\|{7,}(\s|$)")  # diff3-Basis  (|||||||)

START, MITTE, ENDE, BASIS = (KONFLIKT_START, KONFLIKT_MITTE,
                             KONFLIKT_ENDE, KONFLIKT_BASIS)


def pruefe_text(text: str, pfad: str) -> list[tuple[int, str]]:
    """Zustandsmaschine: vollständige oder verwaiste Konfliktblöcke finden."""
    funde: list[tuple[int, str]] = []
    offen_zeile: int | None = None
    for nr, zeile in enumerate(text.splitlines(), 1):
        if START.match(zeile):
            if offen_zeile is not None:
                funde.append((offen_zeile,
                              f"{pfad}:{offen_zeile}: <<<<<<< ohne schlie\u00dfendes "
                              f">>>>>>> (neuer Block ab Zeile {nr})"))
            offen_zeile = nr
            continue
        if BASIS.match(zeile) and offen_zeile is not None:
            funde.append((nr, f"{pfad}:{nr}: diff3-Basismarker (|||||||) im "
                              f"unaufgel\u00f6sten Block (begonnen Zeile {offen_zeile})"))
            continue
        if MITTE.match(zeile):
            # Kein eigener Fund: die Mitte gehört zum offenen Block.
            continue
        if ENDE.match(zeile):
            if offen_zeile is not None:
                funde.append((offen_zeile,
                              f"{pfad}:{offen_zeile}: unaufgel\u00f6ster Merge-"
                              f"Konfliktblock (<<<<<<< \u2026 >>>>>>> Zeile {nr})"))
                offen_zeile = None
            else:
                funde.append((nr, f"{pfad}:{nr}: verwaistes >>>>>>> ohne "
                                  f"\u00f6ffnendes <<<<<<<"))
            continue
    if offen_zeile is not None:
        funde.append((offen_zeile, f"{pfad}:{offen_zeile}: <<<<<<< ohne "
                                   f"schlie\u00dfendes >>>>>>> (Datei-Ende)"))
    return funde


def _ist_binaer(daten: bytes) -> bool:
    return b"\x00" in daten[:8192]


def _git(args: list[str]) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE).stdout


def _namen_z(roh: bytes) -> list[str]:
    return [n for n in roh.decode("utf-8", "surrogateescape").split("\0") if n]


def _pruefe_dateien(paare: list[tuple[str, bytes]]) -> list[tuple[int, str]]:
    funde: list[tuple[int, str]] = []
    for pfad, daten in paare:
        if _ist_binaer(daten):
            continue
        try:
            text = daten.decode("utf-8")
        except UnicodeDecodeError:
            # Latin-1 o. ä.: besser grosszügig lesen statt übersehen.
            text = daten.decode("latin-1")
        funde.extend(pruefe_text(text, pfad))
    return funde


def _sammle(modus: str, range_spec: str | None,
            paths: list[str] | None) -> list[tuple[str, bytes]]:
    if modus == "staged":
        namen = _namen_z(_git(["diff", "--cached", "--name-only",
                               "--diff-filter=ACMR", "-z"]))
        paare = []
        for name in namen:
            try:
                paare.append((name, _git(["show", f":{name}"])))
            except subprocess.CalledProcessError:
                continue  # Nur im Index gelöscht o. ä.
        return paare
    if modus == "range":
        assert range_spec
        namen = _namen_z(_git(["diff", "--name-only", "--no-renames",
                               range_spec, "--", ]))
        paare = []
        for name in namen:
            try:
                paare.append((name, _git(["show", f"HEAD:{name}"])))
            except subprocess.CalledProcessError:
                continue  # Im Range gelöschte Datei
        return paare
    if modus == "paths":
        paare = []
        for name in paths or []:
            pfad = Path(name)
            if not pfad.is_file():
                print(f"::warning::konfliktmarker_wache.py: '{name}' nicht "
                      f"vorhanden – übersprungen.", file=sys.stderr)
                continue
            paare.append((name, pfad.read_bytes()))
        return paare
    # Standard: alle getrackten Dateien aus dem Arbeitsbaum.
    namen = _namen_z(_git(["ls-files", "-z"]))
    paare = []
    for name in namen:
        pfad = ROOT / name
        try:
            paare.append((name, pfad.read_bytes()))
        except OSError:
            continue
    return paare


def selftest() -> int:
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool) -> None:
        if not bedingung:
            fehler.append(name)

    # 1) Echter Konflikt wird gefunden – vollständig, alle Klassen.
    konflikt = ('{\n<<<<<<< HEAD\n  "a": 1,\n=======\n  "a": 2,\n'
                '>>>>>>> f77c0af\n}\n')
    funde = pruefe_text(konflikt, "data/x.json")
    pruefe("vollst\u00e4ndiger Konfliktblock erkannt",
           len(funde) == 1 and funde[0][0] == 2)

    # 2) diff3-Basis (|||||||) im Block wird genannt.
    diff3 = ('<<<<<<< HEAD\na\n||||||| base\nb\n=======\nc\n>>>>>>> main\n')
    funde = pruefe_text(diff3, "x.md")
    pruefe("diff3-Basis erkannt",
           any("|||||||" in f[1] for f in funde) and
           any("<<<<<<<" in f[1] for f in funde))

    # 3) Verwaister >>>>>>> (öffnender Block fehlt).
    funde = pruefe_text('text\n=======\nnur-mitte\n>>>>>>> main\n', "y.md")
    pruefe("verwaister >>>>>>> erkannt", any("verwaist" in f[1] for f in funde))

    # 4) <<<<<<< am Datei-Ende ohne Schließen.
    funde = pruefe_text('a\n<<<<<<< HEAD\nb\n', "z.md")
    pruefe("unbeendeter Block erkannt", any("Datei-Ende" in f[1] for f in funde))

    # 5) Haus-Docstrings sind KEIN Fund (======= allein, NUTZUNG-Stil).
    docstring = ('"""Wache.\n\nNUTZUNG\n=======\n'
                 '    python3 scripts/beispiel.py --selftest\n'
                 '"""\n\n=======\n\nmain()\n')
    pruefe("docstring-Ueberschriften sind kein Fund",
           pruefe_text(docstring, "d.py") == [])

    # 6) Gesunde Datei: kein Fund.
    pruefe("gesunde Datei sauber",
           pruefe_text('{"a": 1}\n', "ok.json") == [])

    # 7) Bin\u00e4rer Inhalt wird \u00fcbersprungen (Marker in Bytes, kein Text).
    roh = b'\x89PNG\r\n\x1a\n\x00<<<<<<< HEAD\x00\xff\xfe'
    pruefe("binaer erkannt", _ist_binaer(roh))

    # 8) --paths-Modus end-to-end im Wegwerf-Baum (C15: nichts im Repo).
    with tempfile.TemporaryDirectory(prefix="konflikt-wache-") as tmp:
        kaputt = Path(tmp) / "kaputt.md"
        kaputt.write_text(konflikt, encoding="utf-8")
        paare = _sammle("paths", None, [str(kaputt)])
        funde = _pruefe_dateien(paare)
        pruefe("paths-Modus findet den Konflikt", len(funde) == 1)

    if fehler:
        for name in fehler:
            print(f"❌ Selbsttest: {name}")
        return 2
    print("✅ Konfliktmarker-Wache: Block-Automat (vollst\u00e4ndig, diff3, "
          "verwaist, unbeendet), Haus-Docstrings bleiben sauber, Binärdateien "
          "übersprungen, --paths end-to-end.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true",
                        help="den gestageten Stand (Index) prüfen")
    parser.add_argument("--range", dest="range_spec", default=None,
                        help="nur die zwischen A...B geändert Dateien prüfen")
    parser.add_argument("--paths", nargs="+", default=None,
                        help="nur diese Dateien (Arbeitsbaum) prüfen")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    modus, range_spec = "all", None
    if args.staged:
        modus = "staged"
    elif args.range_spec:
        modus, range_spec = "range", args.range_spec
    elif args.paths:
        modus = "paths"

    try:
        paare = _sammle(modus, range_spec, args.paths)
    except subprocess.CalledProcessError as exc:
        print(f"::error::konfliktmarker_wache.py: git-Aufruf fehlgeschlagen "
              f"({exc})\u2013 Abbruch (fail-closed).", file=sys.stderr)
        return 2

    funde = _pruefe_dateien(paare)
    if funde:
        print(f"🛑 KONFLIKTMARKER: {len(funde)} Fund(e) – unaufgelöster "
              f"Merge im Baum. Kein Commit/Push ohne bewusste Auflösung:",
              file=sys.stderr)
        for _nr, text in funde:
            print(f"   {text}", file=sys.stderr)
        print("   Heilung: Konflikt bewusst auflösen (eine Seite je Block), "
              "danach neu erzeugen, falls die Datei maschinengeneriert ist "
              "(z. B. python3 scripts/faktenfrische_befund_akte.py --schreiben).",
              file=sys.stderr)
        return 1
    print(f"✅ Keine Merge-Marker in {len(paare)} Datei(en).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
