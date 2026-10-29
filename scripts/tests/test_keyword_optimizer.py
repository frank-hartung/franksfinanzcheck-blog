#!/usr/bin/env python3
"""Regressionstests des Description-Schreibers (scripts/keyword_optimizer.py).

WF-7B6B / #925 (29.10.2026): Dieser Schreiber legte am 27.10.2026
„DSL Hacks: " vor eine passende Description – 153 Zeichen, 1011 px. Sein
eigenes Limit (160 Zeichen) ließ das durch, das Snippet-Gate des Marktes
(155 Zeichen / 985 px) nicht. Der nächtliche E2E-Lauf fand es 15 Stunden
später. Diese Tests halten fest, was seitdem gilt:

  · die Grenzen kommen aus der SSOT (serp_limits), nicht aus dem Schreiber,
  · der #925-Fall wird geheilt statt reproduziert,
  · die Heilung ist idempotent,
  · was nicht ins Fenster passt, wird nicht geschrieben.

Aufruf: python3 -m unittest scripts.tests.test_keyword_optimizer
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import keyword_optimizer as ko  # noqa: E402
import serp_limits as sl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VORFALL_925 = ("WLAN-Verstärker oder Mesh-WLAN? So findest du 2026 heraus, "
               "was dein Zuhause wirklich braucht – mit klaren Kosten und "
               "einer Entscheidungshilfe.")


class SsotBindung(unittest.TestCase):
    def test_grenzen_kommen_aus_der_ssot(self):
        self.assertIs(ko.serp_limits, sl)
        self.assertEqual((ko.DESC_MIN, ko.DESC_MAX),
                         (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))
        self.assertEqual(ko.DESC_OPT_MAX, sl.DESC_MAX_ZEICHEN)

    def test_keine_zweite_grenze_im_code(self):
        with open(os.path.join(REPO, "scripts", "keyword_optimizer.py"),
                  encoding="utf-8") as fh:
            quelle = fh.read()
        self.assertNotRegex(quelle, r"(?m)^DESC_(MIN|MAX)\s*=\s*\(?\s*\d")


class Vorfall925(unittest.TestCase):
    def test_praefix_wird_ins_fenster_gebracht(self):
        geheilt = ko.heal_description(VORFALL_925, "DSL Hacks")
        self.assertIn("dsl hacks", ko.norm(geheilt))          # Keyword steht vorn
        self.assertEqual(sl.befunde(geheilt), [])              # und passt ins Snippet
        self.assertTrue(geheilt.endswith("…"))                 # Schnitt ist markiert

    def test_heilung_ist_idempotent(self):
        einmal = ko.heal_description(VORFALL_925, "DSL Hacks")
        self.assertEqual(ko.heal_description(einmal, "DSL Hacks"), einmal)

    def test_passende_description_mit_keyword_bleibt_liegen(self):
        self.assertEqual(ko.heal_description(VORFALL_925, "Mesh-WLAN"), VORFALL_925)

    def test_breite_description_wird_geheilt(self):
        breit = ("Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe und "
                 "Wartung zusammengehören. Wer Wohnraum warm hält, spart mit "
                 "Wärmedämmung.")
        geheilt = ko.heal_description(breit, "Wärmewende")
        self.assertEqual(sl.befunde(geheilt), [])

    def test_kurze_description_wird_verlaengert(self):
        geheilt = ko.heal_description("Mesh-WLAN ist oft die bessere Wahl.", "Mesh-WLAN")
        self.assertEqual(sl.befunde(geheilt), [])
        self.assertGreaterEqual(len(geheilt), ko.DESC_OPT_MIN)

    def test_leere_description_wird_aus_dem_body_gebaut(self):
        geheilt = ko.heal_description("", "Strom sparen",
                                      "Einleitung über den Stromverbrauch im "
                                      "Haushalt und was wirklich hilft.")
        self.assertEqual(sl.befunde(geheilt), [])
        self.assertIn("strom sparen", ko.norm(geheilt))

    def test_unheilbarer_text_bleibt_unberuehrt(self):
        # Ein einziges riesiges Wort: Kein Schnitt passt – der Schreiber
        # erfindet keine Verletzung und keine halbe Zeile.
        self.assertEqual(ko.heal_description("W" * 300, "Strom"), "W" * 300)

    def test_satzende_wird_ergaenzt_ohne_die_ssot_zu_verletzen(self):
        ohne_punkt = VORFALL_925[:-1]
        geheilt = ko.heal_description(ohne_punkt, "Mesh-WLAN")
        self.assertTrue(geheilt.endswith("."))
        self.assertEqual(sl.befunde(geheilt), [])


class SelftTest(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        # _selftest läuft über main(); hier direkt die Fehlerliste prüfen.
        self.assertEqual(ko._selftest(), [])


if __name__ == "__main__":
    unittest.main()
