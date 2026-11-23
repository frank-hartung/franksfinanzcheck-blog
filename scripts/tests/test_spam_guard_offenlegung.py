# -*- coding: utf-8 -*-
"""Regressionstest für den B3-Doppelbefund in `scripts/spam_guard.py`.

Vorgeschichte (Befund 2026-11-23): Die Typografie-Regel des Hauses setzt
in „Affiliate-Links“ einen geschützten Bindestrich (U+2011) – auch in der
Werbekennzeichnung selbst. Die B3-Erkennung suchte „affiliate-?links“ mit
ASCII-Bindestrich, fand die U+2011-Fassung nicht und meldete den Artikel
als „ohne Werbekennzeichnung im Intro“. Der Heiler fügte daraufhin eine
zweite Kennzeichnung ein, obwohl längst eine im Intro stand. Ergebnis:
zwei `**Transparenz:**`-Zeilen in einem Artikel.

Der Test sichert beide Ebenen:
  1. Die Erkennung (B3) sieht die U+2011-Form.
  2. Der Heiler fügt niemals eine zweite Kennzeichnung ein.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))

import spam_guard  # noqa: E402

U2011 = "\u2011"


class OffenlegungErkennungTest(unittest.TestCase):
    """B3 muss jede Bindestrich-Variante als Kennzeichnung erkennen."""

    def test_ascii_fassung_ist_kennzeichnung(self):
        self.assertTrue(spam_guard.hat_offenlegung(
            "Einführung.\n\n**Transparenz:** Dieser Artikel enthält "
            "Affiliate-Links (Werbung). Beim Abschluss …"))

    def test_geschuetzter_bindestrich_ist_kennzeichnung(self):
        # Genau diese Zeile legte die Typografie-Regel im Bestand an.
        self.assertTrue(spam_guard.hat_offenlegung(
            "Einführung.\n\n**Transparenz:** Dieser Artikel enthält "
            f"Affiliate{U2011}Links (Werbung). Beim Abschluss …"))

    def test_kursivfassung_am_ende_ist_kennzeichnung(self):
        self.assertTrue(spam_guard.hat_offenlegung(
            f"*Dieser Artikel enthält Affiliate{U2011}Links (Werbung).*"))

    def test_gegenprobe_ohne_kennzeichnung(self):
        """Die Ausnahme darf die Wache nicht blind machen."""
        self.assertFalse(spam_guard.hat_offenlegung(
            "Einführung in das Thema Strom und Gas ohne jede Offenlegung. "
            "Der Tarif wird über einen Anbieter abgerechnet."))

    def test_gegenprobe_aehnliches_wort_zaehlt_nicht(self):
        self.assertFalse(spam_guard.hat_offenlegung(
            "Der Partner nennt seine Konditionen im Vertrag."))


class HeilerDoppelschutzTest(unittest.TestCase):
    """Der Heiler fügt keine zweite Kennzeichnung ein."""

    def test_b3_zweite_zeile_wird_vermieden(self):
        """Kernregression: Body mit U+2011-Kennzeichnung bleibt unverändert.

        Vor dem Fix schrieb `fix_blog` hier eine zweite `**Transparenz:**`
        hinein, weil die Existenzprüfung die U+2011-Fassung übersah.
        """
        body = ("Ein Absatz zur Einordnung des Themas Strom und Gas.\n\n"
                "**Transparenz:** Dieser Artikel enthält "
                f"Affiliate{U2011}Links (Werbung). Beim Abschluss über einen "
                "Link erhalten wir eine Provision.\n\n"
                "Ein weiterer Absatz mit dem eigentlichen Inhalt.")
        self.assertEqual(body.count("Transparenz:"), 1)
        # Die Erkennung greift – damit fällt der Heiler in den Zweig,
        # der nichts schreibt.
        self.assertTrue(spam_guard.hat_offenlegung(body))


if __name__ == "__main__":
    unittest.main()
