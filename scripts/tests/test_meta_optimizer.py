#!/usr/bin/env python3
"""Regressionstests des zweiten Description-Schreibers (scripts/meta_optimizer.py).

WF-7B6B / #925 (29.10.2026): Das Keyword-Gate schrieb eine Description mit
1011 px, weil es eigene Grenzen (160 Zeichen) hatte. `meta_optimizer` hatte
dieselben eigenen Zahlen (70–160) – sie ist bisher nicht zugeschlagen, aber
eine zweite Grenze im Code ist ein Befund, auch wenn sie gerade niemand
verletzt. Diese Tests binden auch diesen Schreiber an die SSOT.

Aufruf: python3 -m unittest scripts.tests.test_meta_optimizer
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import meta_optimizer as mo  # noqa: E402
import serp_limits as sl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SsotBindung(unittest.TestCase):
    def test_grenzen_kommen_aus_der_ssot(self):
        self.assertIs(mo.serp_limits, sl)
        self.assertEqual((mo.DESC_MIN, mo.DESC_MAX),
                         (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))

    def test_keine_zweite_grenze_im_code(self):
        with open(os.path.join(REPO, "scripts", "meta_optimizer.py"),
                  encoding="utf-8") as fh:
            quelle = fh.read()
        self.assertNotRegex(quelle, r"(?m)^DESC_(MIN|MAX)\s*=\s*\(?\s*\d")


class Generierung(unittest.TestCase):
    def test_generate_description_bleibt_im_fenster(self):
        a = {"body": ("# Überschrift\n\nEinleitung über den Stromverbrauch im "
                      "Haushalt und was wirklich hilft, wenn die Rechnung zu "
                      "hoch ausfällt und der Tarif seit Jahren nicht geprüft "
                      "wurde. Noch ein Satz mit Substanz für die Länge.\n"),
             "keywords": "Strom sparen"}
        desc = mo.generate_description(a)
        self.assertEqual(sl.befunde(desc), [])

    def test_praefix_preisst_nicht_ueber_die_grenzen(self):
        # Ein breiter Präfix („Wohngebäude und Wärmewende: ") vor einen
        # body-Auszug darf die Description nicht über 985 px schieben.
        a = {"body": ("# Überschrift\n\nEinleitung über die Wärmewende im "
                      "Gebäudebestand und warum Wärmeverlust, Wärmepumpe und "
                      "Wartung zusammengehören, wenn Wohnraum warm bleiben "
                      "soll und die Kosten nicht steigen dürfen.\n"),
             "keywords": "Wohngebäude und Wärmewende"}
        desc = mo.generate_description(a)
        self.assertEqual(sl.befunde(desc), [])

    def test_extend_description_respektiert_die_obergrenzen(self):
        a = {"keywords": "Strom sparen"}
        desc = mo.extend_description("Strom sparen im Alltag.", a)
        self.assertEqual(sl.befunde(desc), [])

    def test_extend_erreicht_die_ctr_vorliebe(self):
        a = {"keywords": "Strom sparen"}
        desc = mo.extend_description("Strom sparen im Alltag.", a)
        self.assertGreaterEqual(len(desc), mo.DESC_OPT_MIN)

    def test_audit_meldet_ssot_verstoesse(self):
        zu_lang = "x" * 200
        a = {"file": "x.md", "title": "Strom sparen: Ratgeber für den Alltag",
             "description": zu_lang, "keywords": "a, b, c", "cover": "c.jpg"}
        self.assertIn("Description zu lang", " ".join(mo.audit(a)["issues"]))


class SatzendeAmLimit(unittest.TestCase):
    """Der deterministische Satzende-Heiler (#295) am SSOT-Limit.

    WF-7B6B / #925: Ein Punkt am Limit ist kein Satzende, sondern ein
    Breiten-Verstoß. Der Heiler muss deshalb in DERSELBEN Schneidestelle
    kürzen (`serp_limits.auf_snippet_kuerzen`) – und zwar mit dem Punkt als
    Marker, statt hinterher eine zweite, augenmaßliche Grenze zu erfinden.
    """

    AM_LIMIT = ("Erfahre, wie du im Spätsommer deine Gasrechnung senken "
                "kannst. Mit diesen Tipps startest du vorbereitet in den "
                "Herbst und sparst bei der Heizung bares Geld")

    def test_limit_heilt_mit_punkt_und_bleibt_im_fenster(self):
        self.assertEqual([c for c, _ in sl.befunde(self.AM_LIMIT, min_zeichen=0)],
                         ["zu-breit"], "Probe steht nicht am Limit")
        self.assertFalse(mo.desc_has_sentence_end(self.AM_LIMIT))
        k = sl.auf_snippet_kuerzen(self.AM_LIMIT, satzende=".")
        self.assertIsNotNone(k)
        self.assertTrue(k.endswith("."))
        self.assertEqual(sl.befunde(k), [])
        self.assertTrue(mo.desc_has_sentence_end(k))

    def test_kurzer_text_bekommt_den_punkt_ungekuerzt(self):
        # Zu kurz ist Schritt 1 (`extend_description`), nicht das Satzende.
        kurz = "Erfahre, wie du im Spätsommer deine Gasrechnung senken kannst"
        self.assertEqual(sl.befunde(kurz, min_zeichen=0), [])
        self.assertEqual(sl.auf_snippet_kuerzen(kurz, satzende="."), kurz)


if __name__ == "__main__":
    unittest.main()
