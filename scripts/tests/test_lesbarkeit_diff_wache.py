# -*- coding: utf-8 -*-
"""Regressionstests der Lesbarkeits-Diff-Wache (#1247, 22.11.2026).

Der Anlass ist konkret: Drei Live-Artikel wurden am 19.11.2026 überarbeitet
und liegen seither unter dem Haus-Boden Flesch 60, ohne dass ein Lauf die
Veröffentlichung verhindert hat. Das Publish-Gate prüft nur neue Kandidaten
(heutiges Datum/Ordner-Präfix), nicht die Überarbeitung eines Live-Artikels.

Diese Tests halten die Urteilslogik fest – in beide Richtungen:
  * eine Verschlechterung unter den Boden blockiert,
  * Altbestand unter dem Boden blockiert nicht jede Routinemeldung,
    solange er nicht schlechter wird (sonst wäre die Wache ein Dauerrot).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import lesbarkeit_diff_wache as wache  # noqa: E402
import readability_check as rc  # noqa: E402


class Schwelle(unittest.TestCase):
    def test_boden_ist_die_publish_schwelle(self):
        self.assertEqual(rc.FLOOR_MIN, rc.NEW_FLESCH_MIN)
        self.assertGreaterEqual(rc.FLOOR_MIN, 60.0)


class Urteil(unittest.TestCase):
    def test_neuer_artikel_unter_boden_blockiert(self):
        self.assertIsNotNone(wache.bewerte(rc.FLOOR_MIN - 1.0, None, True))

    def test_neuer_artikel_auf_boden_ist_frei(self):
        self.assertIsNone(wache.bewerte(rc.FLOOR_MIN, None, True))

    def test_verschlechterung_unter_den_boden_blockiert(self):
        self.assertIsNotNone(
            wache.bewerte(rc.FLOOR_MIN - 2.0, rc.FLOOR_MIN + 1.0, False))

    def test_altbestand_wird_nicht_wegen_alter_schuld_blockiert(self):
        self.assertIsNone(
            wache.bewerte(rc.FLOOR_MIN - 5.0, rc.FLOOR_MIN - 5.0, False))

    def test_verbesserung_im_altbestand_ist_kein_befund(self):
        self.assertIsNone(
            wache.bewerte(rc.FLOOR_MIN - 2.0, rc.FLOOR_MIN - 3.0, False))

    def test_weitere_verschlechterung_im_altbestand_blockiert(self):
        self.assertIsNotNone(
            wache.bewerte(rc.FLOOR_MIN - 4.0, rc.FLOOR_MIN - 2.0, False))

    def test_nicht_messbar_ist_nie_gruen(self):
        self.assertIsNotNone(wache.bewerte(None, 70.0, False))

    def test_messrauschen_allein_blockiert_nicht(self):
        # 0,03 Punkte sind Wortstellung, keine Verschlechterung.
        self.assertIsNone(
            wache.bewerte(rc.FLOOR_MIN - 1.03, rc.FLOOR_MIN - 1.0, False))


class Selbsttest(unittest.TestCase):
    def test_selbsttest_laeuft(self):
        self.assertEqual(wache.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
