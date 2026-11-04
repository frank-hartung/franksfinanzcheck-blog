#!/usr/bin/env python3
# ============================================================
#  BESTANDS-SWEEP EINZIGARTIGKEIT (#1027, Dauerheilung)
#  ------------------------------------------------------------
#  Das Tagesaudit misst live↔live-Paare – aber erst NACH dem Deploy.
#  Dieser Test misst denselben Bestand mit derselben Messung
#  (`lade_bestand` + `ngrams` + `KRITISCH_AB` aus check_uniqueness,
#  keine zweite Schwelle) bereits in der PR-Regression: Eine Änderung,
#  die einen Live-Artikel in eine kritische Überlappung schiebt,
#  fällt vor dem Merge – nicht einen Tag später im Audit-Ticket.
#  Entwurfs-Paare werden bewusst NICHT behauptet: Sie blockieren
#  den Bestand nicht; ihre Messung ist die Änderungs-Messung V4
#  (`aenderung_befunde`) vor dem Schreiben bzw. vor dem Livegehen.
# ============================================================
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import check_uniqueness as cu  # noqa: E402


class BestandSweepTest(unittest.TestCase):
    def test_kein_kritisches_live_paar_im_bestand(self):
        bestand = cu.lade_bestand()
        live = {s: i for s, i in
                ((info["slug"], info) for info in bestand.values())
                if i["live"]}
        self.assertGreater(len(live), 50, "Bestand unerwartet klein – Sweep leer?")
        grams = {s: cu.ngrams(i["body"], cu.PHRASE_LEN) for s, i in live.items()}
        kritisch = []
        slugs = sorted(live)
        for idx, a in enumerate(slugs):
            for b in slugs[idx + 1:]:
                n = len(grams[a] & grams[b])
                if cu.paar_klasse(n, False, False) == "kritisch":
                    kritisch.append(f"{a} ↔ {b}: {n} Phrasen")
        self.assertEqual([], kritisch,
                         "Kritische live↔live-Überlappung(en) – Passage "
                         "eigenständig formulieren (#1027): " + "; ".join(kritisch))


class AenderungBefundeTest(unittest.TestCase):
    """V4: Die Änderungs-Messung findet die Kopie und schont die Altlast."""

    PASSAGE = ("Bei einer einseitigen Preisänderung können Verbraucher "
               "grundsätzlich ohne Frist zum Zeitpunkt der Änderung "
               "kündigen; der Vertrag endet am Vortag der Änderung.")
    EIGEN = ("Der eigene Text spricht über Heizkörper, Thermostate "
             "und den Blick auf die letzte Jahresrechnung des Hauses.")

    def _bestand(self):
        return {
            "a": {"slug": "2026-01-01-fremd",
                  "body": cu.clean_body(self.PASSAGE), "live": True},
            "b": {"slug": "2026-01-02-eigen",
                  "body": cu.clean_body(self.EIGEN), "live": True},
        }

    def test_kopierte_passage_wird_erkannt(self):
        befunde = cu.aenderung_befunde(
            "2026-01-02-eigen", self.EIGEN, self.EIGEN + " " + self.PASSAGE,
            bestand=self._bestand())
        self.assertTrue(any("2026-01-01-fremd" in b for b in befunde), befunde)

    def test_unveraenderter_text_bleibt_still(self):
        self.assertEqual([], cu.aenderung_befunde(
            "2026-01-02-eigen", self.EIGEN, self.EIGEN,
            bestand=self._bestand()))

    def test_altlast_wird_nicht_neu_erzeugt(self):
        kopie = self.EIGEN + " " + self.PASSAGE
        self.assertEqual([], cu.aenderung_befunde(
            "2026-01-02-eigen", kopie, kopie, bestand=self._bestand()))


if __name__ == "__main__":
    unittest.main()
