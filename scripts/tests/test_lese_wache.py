#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für die Lese-Wache.

Die Wache existiert, weil `--json` die Baseline schrieb und damit den
`regression`-Job riss (23.11.2026). Diese Tests halten BEIDE Richtungen
fest: Sie muss den echten Fehler finden und bei der Heilung still bleiben.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import lese_wache as wache  # noqa: E402

# Der echte Fehler, aus `markdown_struktur_wache.py` vor der Heilung.
ECHTER_FEHLER = '''maschinenformat = args.json or args.md
baseline = lade_baseline()
if baseline:
    _schreibe_baseline(klinke_einrasten(stand, baseline), args.dry_run)
'''

GEHEILT = '''maschinenformat = args.json or args.md
schreibend = not maschinenformat and not args.dry_run
if baseline and schreibend:
    _schreibe_baseline(klinke_einrasten(stand, baseline), args.dry_run)
'''


class StatischTest(unittest.TestCase):
    """Die Regel: ein Schreibaufruf ohne Ausnahme für `--json`/`--md`."""

    def _befunde(self, quelle: str) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "probe.py"
            pfad.write_text(quelle, encoding="utf-8")
            return wache.statisch(pfad)

    def test_echter_fehler_wird_gefunden(self):
        """Das war der Fehler, der den regression-Job gerissen hat."""
        befunde = self._befunde(ECHTER_FEHLER)
        self.assertEqual(1, len(befunde), befunde)
        self.assertIn("_schreibe_baseline", befunde[0]["inhalt"])

    def test_heilung_bleibt_still(self):
        self.assertEqual([], self._befunde(GEHEILT))

    def test_not_maschinenformat_im_if_zaehlt(self):
        self.assertEqual([], self._befunde(
            "maschinenformat = args.json or args.md\n"
            "if baseline and not maschinenformat:\n"
            "    _schreibe_baseline(stand, args.dry_run)\n"))

    def test_seed_zweig_ist_erlaubt(self):
        self.assertEqual([], self._befunde(
            "maschinenformat = args.json or args.md\n"
            "if args.seed:\n"
            "    _schreibe_baseline(stand, args.dry_run)\n"
            "    return 0\n"))

    def test_seed_mit_vorlauf_ist_erlaubt(self):
        """In `titel_klinke.py` stehen sechs Zeilen zwischen if und Aufruf."""
        self.assertEqual([], self._befunde(
            "maschinenformat = args.json or args.md\n"
            "if args.seed:\n"
            "    stand_neu = {k: {\"titel\": v[\"titel\"],\n"
            "                     \"schwere\": v[\"schwere\"]}\n"
            "                  for k, v in stand.items()}\n"
            "    _schreibe_baseline(stand_neu, args.dry_run)\n"
            "    return 0\n"))

    def test_dry_run_argument_allein_schuetzt_nicht(self):
        """DER Fehlschluss beim ersten Wurf.

        `_schreibe_baseline(stand, args.dry_run)` schreibt genau dann, wenn
        `--dry-run` NICHT gesetzt ist – im `--json`-Lauf ist `dry_run` False.
        Die Anwesenheit des Arguments sagt nichts über das Schreiben.
        """
        befunde = self._befunde(
            "maschinenformat = args.json or args.md\n"
            "_schreibe_baseline(stand, args.dry_run)\n")
        self.assertEqual(1, len(befunde),
                         "dry_run als Argument darf nicht freisprechen")

    def test_skript_ohne_maschinenformat_wird_nicht_geprueft(self):
        self.assertEqual([], self._befunde(
            "def main():\n    _schreibe_baseline(stand)\n"))


class BestandTest(unittest.TestCase):
    """Der echte Bestand und die echten Skripte."""

    def test_repo_ist_ohne_befund(self):
        """Statisch UND dynamisch – der dynamische Teil ist der Beweis."""
        befunde = wache.pruefe()
        self.assertEqual(
            [], befunde,
            "eine Abfrage verändert den Bestand: "
            f"{[(b['datei'], b['zeile']) for b in befunde]}")

    def test_geheilte_skripte_sind_still(self):
        for name in ("markdown_struktur_wache.py", "titel_klinke.py"):
            self.assertEqual(
                [], wache.statisch(ROOT / "scripts" / name),
                f"{name} schreibt noch bei einer Abfrage")

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(0, wache.selftest())


if __name__ == "__main__":
    unittest.main()
