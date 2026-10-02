#!/usr/bin/env python3
"""Regressionstest: social_gate L6 (deutsch-Erkennung) – Flexions-Robustheit.

Anlass (PR #530, 02.10.2026): Sobald der Urlaubskasse-Artikel der jüngste
Eintrag des Social-Pools wurde, fielen die CI-Checks „gate“ und
„regression“ rot – per `social_studio --selftest`. Ursache: L6 prüfte
deutsche Funktionswörter flexionsblind mit `" die " in text`. Der
komponierte Mastodon-Text des Live-Artikels („Du willst deine
Urlaubskasse aufbessern?“ – deine, ohne, willst) enthielt keinen
Marker in Grundform → falsch-negativ in einer fail-closed-Wache.

Der Test hält beide Seiten des Vertrags fest: deformierter deutscher
Text mit Flexionsformen muss durchkommen, englischer Text muss weiterhin
blockieren (L6 ist und bleibt eine Anti-Satzleichen-Heuristik).
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import social_gate as gate  # noqa: E402


class TestSocialGateL6(unittest.TestCase):
    DEUTSCH = [
        # Der Befund aus PR #530 – Titel + Hook des Live-Artikels:
        ("Urlaubskasse aufbessern: Reisebudget ohne Nebenjob finden\n"
         "Du willst deine Urlaubskasse aufbessern?\n#Reise #AboAudit"),
        "Sieben Wege, wie du dein Budget ohne Verzicht planst.",
        "So planst du deinen Gasabschlag: die Formel mit Modellrechnung.",
        "Wir zeigen dir, worauf es beim Wechsel wirklich ankommt.",
        "Keine Panik: Mit diesen fünf Hebeln senkst du deine Fixkosten.",
        "Deine Heizkosten steigen? So reagierst du rechtzeitig.",
    ]
    ENGLISCH = [
        "This article shows you the best hacks of the web. Check it out now!",
        "Save money fast with these tricks — best deals only, no strings attached.",
        "Get the ultimate guide for free today and boost your income instantly.",
    ]

    def test_deutsche_texte_mit_flexion_bestanden(self):
        for text in self.DEUTSCH:
            self.assertTrue(gate._german_hit(text),
                            f"fälschlich als nicht-deutsch verworfen: {text[:60]}")

    def test_englische_satzleichen_blockieren_weiter(self):
        for text in self.ENGLISCH:
            self.assertFalse(gate._german_hit(text),
                             f"fälschlich als deutsch durchgelassen: {text[:60]}")

    def test_grundwort_abgleich_unveraendert(self):
        self.assertTrue(gate._german_hit("Der Artikel und die Regel sind kurz."))
        self.assertFalse(gate._german_hit("a b c d e"))

    def test_marker_liste_ungekuerzt(self):
        """Die ursprünglichen Marker dürfen nicht verwässert worden sein."""
        for w in ["der", "die", "das", "und", "nicht", "für", "mit", "ein",
                  "eine", "ist", "sind", "du", "dein", "kann", "sparen"]:
            self.assertIn(w, gate.GERMAN_MARKERS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
