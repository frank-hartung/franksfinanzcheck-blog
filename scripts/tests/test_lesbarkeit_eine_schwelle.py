# -*- coding: utf-8 -*-
"""Eine Flesch-Zahl für „veröffentlichbar“ – der Befund vom 08./09.11.2026.

DER VORFALL
-----------
`2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` stand
bei **Flesch 59,7**. Für das Publish-Gate ist das zu wenig (R6: ≥ 60) – jeder
neue Artikel wäre daran gescheitert. Für die Wochen-Wache `--gate-bestand`
war es **OK**, weil deren Bestands-Boden bei 55 lag. Dieselbe Kennzahl, zwei
Urteile: Der Artikel trug die Zusage seiner eigenen Veröffentlichung nicht
mehr, und keine Wache sagte es. Aufgefallen ist es Wochen später einem
Vertragstest (#1027), der drei Gas-Artikel namentlich prüft.

DIE REGEL (seit 09.11.2026)
---------------------------
`FLOOR_MIN == NEW_FLESCH_MIN` – genau eine Zahl für den Bestand und für neue
Artikel. Am Umstellungstag gemessen: 80 von 80 Live-Artikeln ≥ 60,0
(Ø 64,9). Der Boden ist damit keine Toleranz mehr, sondern die Zusage.

Diese Tests halten beide Richtungen:
  * der Boden ist nicht wieder unter die Publish-Schwelle gerutscht,
  * und das Bestands-Urteil straft genau den Fall 59,7 ab (kein stilles Grün).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import readability_check as rc  # noqa: E402


def _artikel(flesch: float, draft: bool = False) -> dict:
    return {"file": f"fixture-{flesch}-{draft}.md", "flesch": flesch, "draft": draft,
            "score": 100, "issues": []}


class EineSchwelleTest(unittest.TestCase):
    def test_boden_ist_die_publish_schwelle(self):
        self.assertEqual(
            rc.FLOOR_MIN, rc.NEW_FLESCH_MIN,
            "Der Bestands-Boden muss die Publish-Schwelle sein – ein niedrigerer "
            "Boden lässt Live-Artikel unter ihrer eigenen Zusage stehen (59,7)")

    def test_boden_liegt_nicht_unter_dem_dokumentierten_minimum(self):
        """55 ist die untere Grenze des Vertrags (C20) – darunter wäre Aufweichung."""
        self.assertGreaterEqual(rc.FLOOR_MIN, 55.0)

    def test_zieldurchschnitt_bleibt_strenger_als_der_boden(self):
        self.assertGreater(rc.AVG_TARGET, rc.FLOOR_MIN)

    def test_bericht_nutzt_dieselben_zahlen(self):
        """Auch ein Bericht darf keine zweite Schwelle erfinden.

        `copy_editing_gate.py` wies im Copy-Editing-Report „Boden 55“ aus,
        während das Tor 60 verlangte. Ein Bericht, der eine aufgeweichte
        Schwelle nennt, macht das Leck wieder unsichtbar.
        """
        import copy_editing_gate as ceg

        self.assertEqual(ceg.THRESHOLDS["flesch_floor"], rc.FLOOR_MIN)
        self.assertEqual(ceg.THRESHOLDS["flesch_min_neu"], rc.NEW_FLESCH_MIN)
        self.assertEqual(ceg.THRESHOLDS["flesch_target_bestand"], rc.AVG_TARGET)


class BestandsUrteilTest(unittest.TestCase):
    def test_59_7_ist_rot(self):
        """Genau der Vorfall: derselbe Artikel, dieselbe Zahl, ein Urteil."""
        urteil = rc.gate_bestand_urteil([_artikel(59.7), _artikel(64.0),
                                         _artikel(70.0)])
        self.assertTrue(urteil["stop"], "Flesch 59,7 im Live-Bestand muss stoppen")
        self.assertEqual(urteil["ampel"], "RED")
        self.assertTrue(any("59.7" in s for s in urteil["stopper"]),
                        "Der Befund muss die Zahl nennen, nicht nur rot sein")

    def test_genau_60_0_ist_gruen(self):
        urteil = rc.gate_bestand_urteil([_artikel(60.0), _artikel(66.0)])
        self.assertFalse(urteil["stop"], "Die Schwelle ist ≥ 60, nicht > 60")

    def test_entwurf_unter_der_schwelle_blockiert_nicht(self):
        """Bestand und Entwurf bleiben getrennt (30.09.2026, Issue #476)."""
        urteil = rc.gate_bestand_urteil([_artikel(64.0), _artikel(41.7, draft=True)])
        self.assertFalse(urteil["stop"], "ein Entwurf darf die Wache nicht rot färben")
        self.assertTrue(urteil["hinweise"], "der Entwurf muss namentlich genannt werden")

    def test_leerer_bestand_ist_kein_gruen(self):
        """Null gemessene Artikel heißt: die Messung ist kaputt – nicht „alles gut“.

        Dieselbe Bauart wie die Blindheitsschwelle aus §6 der Schließakte:
        eine Prüfung, die über null Objekte läuft, darf nicht grün melden.
        """
        urteil = rc.gate_bestand_urteil([_artikel(41.7, draft=True)])
        self.assertTrue(urteil["stop"], "ohne Live-Artikel darf das Gate nicht grün sein")
        self.assertEqual(urteil["ampel"], "RED")
        self.assertTrue(any("kein Live-Artikel" in s for s in urteil["stopper"]))


if __name__ == "__main__":
    unittest.main()
