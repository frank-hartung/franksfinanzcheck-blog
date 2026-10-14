#!/usr/bin/env python3
"""Vertragstests für scripts/werkzeugbefund.py (Dauerheilung #740, C38).

GEPRÜFTER VERTRAG
-----------------
Ein Werkzeugbefund ist eine MELDUNG, kein Abbruch. Der Melder läuft in
Schritten, die gerade etwas Unangenehmes festgestellt haben – wenn er
dabei selbst den Lauf rot macht, blockiert ausgerechnet das Melden die
Auslieferung. Deshalb:

  · `melden()` endet IMMER mit Exit 0 (auch bei kaputtem Pfad, #227),
  · mehrzeilige Begründungen zerlegen die Ablage nicht,
  · `sammeln()` fasst alles zu EINER Zeile für `$GITHUB_OUTPUT`,
  · ohne Befunde ist das Ergebnis leer und die Anzahl 0 (kein Scheinbefund).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import werkzeugbefund as wb  # noqa: E402


class WerkzeugbefundKanal(unittest.TestCase):
    """Melden → Lesen → Sammeln auf einer Wegwerf-Ablage."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ablage = Path(self._tmp.name) / "werkzeugbefunde.txt"
        self._alt = os.environ.get("WERKZEUGBEFUNDE_DATEI")
        os.environ["WERKZEUGBEFUNDE_DATEI"] = str(self.ablage)

    def tearDown(self):
        os.environ.pop("WERKZEUGBEFUNDE_DATEI", None)
        if self._alt is not None:
            os.environ["WERKZEUGBEFUNDE_DATEI"] = self._alt
        self._tmp.cleanup()

    def test_melden_und_lesen(self):
        wb.melden("quote_refill", "hunspell fehlt (Exit 1)")
        wb.melden("kostensperre", "Beleg nicht lesbar (Exit 2)")
        befunde = wb.lesen()
        self.assertEqual([schritt for schritt, _ in befunde],
                         ["quote_refill", "kostensperre"])
        self.assertIn("hunspell", befunde[0][1])

    def test_mehrzeiliger_grund_bleibt_ein_befund(self):
        """Ein Traceback im Grund darf die Ablage nicht zerlegen."""
        wb.melden("quote_refill", "Zeile 1\nZeile 2\nTraceback: boom")
        befunde = wb.lesen()
        self.assertEqual(len(befunde), 1, "Mehrzeiler erzeugt Phantombefunde")
        self.assertIn("Zeile 2", befunde[0][1])

    def _output(self) -> dict:
        """`sammeln()` gegen eine echte $GITHUB_OUTPUT-Datei fahren."""
        ziel = Path(self._tmp.name) / "github_output.txt"
        ziel.write_text("", encoding="utf-8")
        alt = os.environ.get("GITHUB_OUTPUT")
        os.environ["GITHUB_OUTPUT"] = str(ziel)
        try:
            self.assertEqual(wb.sammeln(), 0, "sammeln() endet nie rot")
        finally:
            os.environ.pop("GITHUB_OUTPUT", None)
            if alt is not None:
                os.environ["GITHUB_OUTPUT"] = alt
        zeilen = ziel.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(zeilen), 2,
                         f"Output muss zwei Zeilen haben, ist: {zeilen}")
        return dict(z.split("=", 1) for z in zeilen)

    def test_sammeln_ist_eine_zeile(self):
        wb.melden("a", "Grund A")
        wb.melden("b", "Grund B")
        werte = self._output()
        self.assertEqual(werte["werkzeugbefunde_anzahl"], "2")
        self.assertIn("a: Grund A", werte["werkzeugbefunde"])
        self.assertIn("b: Grund B", werte["werkzeugbefunde"])

    def test_ohne_befunde_leer_und_null(self):
        werte = self._output()
        self.assertEqual(werte["werkzeugbefunde"], "",
                         "Ohne Befund darf kein Scheinbefund entstehen")
        self.assertEqual(werte["werkzeugbefunde_anzahl"], "0")

    def test_melden_endet_nie_rot(self):
        """Auch ein unbeschreibbarer Pfad darf den Schritt nicht töten."""
        os.environ["WERKZEUGBEFUNDE_DATEI"] = "/proc/dieses/gibt/es/nicht.txt"
        self.assertEqual(wb.main(["--melden", "x", "kaputter Pfad"]), 0)

    def test_cli_melden_und_sammeln(self):
        """Der echte CLI-Weg, so wie ihn der Workflow benutzt."""
        env = dict(os.environ, WERKZEUGBEFUNDE_DATEI=str(self.ablage))
        melden = subprocess.run(
            [sys.executable, str(SCRIPTS / "werkzeugbefund.py"), "--melden",
             "auslieferungs-isolation", "Werkzeugfehler (Exit 2)"],
            capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(melden.returncode, 0, melden.stderr)
        ausgabe = Path(tempfile.mkdtemp()) / "out.txt"
        ausgabe.touch()
        env["GITHUB_OUTPUT"] = str(ausgabe)
        sammeln = subprocess.run(
            [sys.executable, str(SCRIPTS / "werkzeugbefund.py"), "--sammeln"],
            capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(sammeln.returncode, 0, sammeln.stderr)
        text = ausgabe.read_text(encoding="utf-8")
        self.assertIn("werkzeugbefunde=", text)
        self.assertIn("werkzeugbefunde_anzahl=1", text)
        self.assertEqual(len(text.strip().splitlines()), 2,
                         "Output muss genau zwei Zeilen schreiben")


class WerkzeugbefundSelbsttest(unittest.TestCase):
    def test_selftest_gruen(self):
        lauf = subprocess.run(
            [sys.executable, str(SCRIPTS / "werkzeugbefund.py"), "--selftest"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(lauf.returncode, 0,
                         f"Selbsttest rot:\n{lauf.stdout}\n{lauf.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
