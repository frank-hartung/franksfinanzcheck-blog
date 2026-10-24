#!/usr/bin/env python3
"""Regress-Tests für die Längen-Statussprache (Release-Scorecard #824).

ANLASS
------
`check_length.status_of()` meldete für BEIDE Seiten des Optimums
`unter-optimum`. Zwei Live-Beiträge mit 18.443 bzw. 18.940 Zeichen standen
dadurch in der Release-Scorecard als „Zeichenlänge unter-optimum“ – also
scheinbar zu kurz, obwohl sie das Optimum (12.000–18.000) überschritten.
Die Redaktion wurde damit in die falsche Richtung geschickt.

Die Scorecard-Schicht kannte `ueber-optimum` längst (`release_scorecard.py`,
SSOT `data/release_scorecard.yaml`: „Status unter-/ueber-optimum“); nur der
Erzeuger lieferte den Wert nie. Diese Tests halten die Begriffe zusammen:
jeder Status, den `check_length` vergibt, muss im Verbraucher bekannt sein.

Ausführung:  python3 -m unittest scripts.tests.test_check_length
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "scripts"))

import check_length as cl  # noqa: E402


class StatusspracheTests(unittest.TestCase):
    def test_beide_seiten_des_optimums_sind_unterscheidbar(self):
        self.assertEqual(cl.status_of(cl.OPT_MIN_CHARS - 1), "unter-optimum")
        self.assertEqual(cl.status_of(cl.OPT_MAX_CHARS + 1), "ueber-optimum")

    def test_grenzen_gehoeren_ins_optimum(self):
        for chars in (cl.OPT_MIN_CHARS, cl.OPT_MAX_CHARS):
            self.assertEqual(cl.status_of(chars), "ok", chars)
        self.assertEqual(cl.status_of(cl.OPT_MAX_CHARS - 1), "ok")

    def test_harte_grenzen_bleiben_hart(self):
        self.assertEqual(cl.status_of(cl.MIN_CHARS - 1), "zu-kurz")
        self.assertEqual(cl.status_of(cl.MAX_CHARS + 1), "zu-lang")
        # Zu lang, aber unter der harten Grenze: Hinweis, kein Stopp.
        self.assertEqual(cl.status_of(cl.MAX_CHARS), "ueber-optimum")

    def test_jeder_status_ist_beim_verbraucher_bekannt(self):
        """Der Erzeuger darf keinen Status erfinden, den die Scorecard nicht kennt."""
        quelle = (WURZEL / "scripts" / "release_scorecard.py").read_text(encoding="utf-8")
        bekannte = {"zu-kurz", "zu-lang", "unter-optimum", "ueber-optimum", "ok"}
        for chars in (5_000, 10_500, 14_000, 20_000, 24_000):
            status = cl.status_of(chars)
            self.assertIn(status, bekannte)
        for status in ("unter-optimum", "ueber-optimum"):
            self.assertIn(status, quelle,
                          f"Scorecard kennt den Status `{status}` nicht mehr")


if __name__ == "__main__":
    unittest.main()
