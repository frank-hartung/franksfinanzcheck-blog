#!/usr/bin/env python3
"""Regressionstests für die Skript-Syntax-Wache (Bot-Watchdog #864).

WARUM (25.10.2026)
------------------
Am 25.10.2026 stand `scripts/redaktions_standard.py` mit einem
IndentationError auf `main` – entstanden beim Squash-Merge von PR #869
auf eine gewanderte `main`. Vier weitere Commits gingen unbemerkt
darüber. Die Wache friert die drei Eigenschaften ein, die damals
gefehlt haben:

  1. Der Befund nennt DATEI, ZEILE und QUELLZEILE – nicht nur
     „Sorry: IndentationError (redaktions_standard.py, line 424)".
  2. Die Prüfung schreibt nichts in den Arbeitsbaum (kein
     `__pycache__`) und liest nur `.py`.
  3. Ihr Selbsttest prüft DEN DETEKTOR, nicht den Repo-Stand. Ein
     Detektor, dessen Selbsttest am kaputten Prüfling scheitert, ist
     in genau dem Moment blind, für den er gebaut ist.

Lauf: python3 -m unittest scripts.tests.test_skript_syntax_wache
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(WURZEL, "scripts"))

import skript_syntax_wache as wache  # noqa: E402

GUT = "def addiere(a, b):\n    return a + b\n"
KAPUTT = "def addiere(a, b):\n    return a + b\n        return 0\n"


class DetektorTests(unittest.TestCase):
    """Der Detektor erkennt, was er erkennen muss – und schweigt sonst."""

    def test_fehlerfreier_text_bleibt_still(self):
        self.assertIsNone(wache.pruefe_quelle(GUT))

    def test_indentationerror_mit_zeile_und_quelle(self):
        fund = wache.pruefe_quelle(KAPUTT, "scripts/beispiel.py")
        self.assertIsNotNone(fund)
        self.assertEqual("scripts/beispiel.py:3", f"{fund.datei}:{fund.zeile}")
        self.assertIn("IndentationError", fund.art)
        self.assertIn("return 0", fund.quelle)
        self.assertEqual("scripts/beispiel.py:3: " + fund.art, fund.text())

    def test_fehlender_doppelpunkt_wird_erkannt(self):
        fund = wache.pruefe_quelle("def f()\n    pass\n", "probe.py")
        self.assertIsNotNone(fund)
        self.assertEqual(1, fund.zeile)

    def test_nullbyte_ist_ein_befund_kein_absturz(self):
        fund = wache.pruefe_quelle("x = 1\x00\n", "probe.py")
        self.assertIsNotNone(fund)


class BaumTests(unittest.TestCase):
    """Was zählt als Skript – und was nicht."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        (self.tmp / "scripts" / "tief").mkdir(parents=True)
        (self.tmp / "scripts" / "gut.py").write_text(GUT, encoding="utf-8")
        (self.tmp / "scripts" / "tief" / "kaputt.py").write_text(KAPUTT, encoding="utf-8")
        (self.tmp / "scripts" / "notiz.txt").write_text("kein python(\n", encoding="utf-8")
        (self.tmp / "scripts" / "__pycache__").mkdir()
        (self.tmp / "scripts" / "__pycache__" / "muell.py").write_text(
            "kein python(\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_unterordner_zaehlen_und_cache_nicht(self):
        namen = [p.relative_to(self.tmp).as_posix() for p in wache.dateien(self.tmp)]
        self.assertEqual(["scripts/gut.py", "scripts/tief/kaputt.py"], namen)

    def test_funde_sind_repo_relativ(self):
        funde = wache.finde(self.tmp)
        self.assertEqual(["scripts/tief/kaputt.py"], [f.datei for f in funde])
        self.assertEqual(["scripts/tief/kaputt.py"], wache.betroffene_dateien(funde))

    def test_pruefung_schreibt_nichts(self):
        vorher = sorted(p.as_posix() for p in self.tmp.rglob("*"))
        wache.finde(self.tmp)
        nachher = sorted(p.as_posix() for p in self.tmp.rglob("*"))
        self.assertEqual(vorher, nachher, "die Wache hat den Arbeitsbaum verändert")

    def test_berichte_nennen_datei_und_zeile(self):
        funde = wache.finde(self.tmp)
        self.assertIn("scripts/tief/kaputt.py:3", wache.bericht(funde))
        self.assertIn("scripts/tief/kaputt.py:3", wache.markdown(funde, 2))
        self.assertTrue(wache.bericht([]).startswith("✅"))

    def test_json_ist_serialisierbar(self):
        daten = json.loads(json.dumps([f.as_dict() for f in wache.finde(self.tmp)]))
        self.assertEqual(3, daten[0]["zeile"])


class SelbsttestTests(unittest.TestCase):
    """Der Selbsttest darf nie am Repo-Stand hängen (#864)."""

    def test_selbsttest_gruen(self):
        self.assertEqual(0, wache.selftest())

    def test_selbsttest_bewertet_nicht_den_repo_stand(self):
        """Der Selbsttest darf den Prüfling (das Repo) gar nicht erst lesen.

        Genau diese Verwechslung hat am 25.10.2026 den Melder abgeschaltet:
        Ein kaputtes Fremdskript kippte den Selbsttest und damit den ganzen
        Lauf – vor jeder Messung, jeder Heilung und jeder Meldung.
        """
        original = wache.finde
        gesehen = []

        def aufzeichnen(root=None):
            gesehen.append(root)
            return original(root)

        try:
            wache.finde = aufzeichnen
            self.assertEqual(0, wache.selftest())
        finally:
            wache.finde = original
        self.assertTrue(gesehen, "der Selbsttest prüft den Baum nicht einmal")
        for wurzel in gesehen:
            self.assertIsNotNone(wurzel, "Selbsttest liest den echten Repo-Baum")
            self.assertNotEqual(wache.BLOG_DIR, Path(wurzel),
                                "Selbsttest bewertet den Repo-Stand statt des Detektors")


class BestandTests(unittest.TestCase):
    """Der heutige Stand des Repos ist Syntax-grün (kein Dauerbefund)."""

    def test_repo_kompiliert(self):
        funde = wache.finde()
        self.assertEqual([], [f.text() for f in funde])


if __name__ == "__main__":
    unittest.main()
