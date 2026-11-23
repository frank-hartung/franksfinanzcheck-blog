#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für die E2E-Textanker-Wache.

Die Wache existiert, weil ein E2E-Test einen redaktionellen Satz wörtlich
festgeschrieben hatte und deshalb rot wurde, obwohl die Seite in Ordnung
war (#1329, 23.11.2026). Diese Tests halten beide Richtungen fest: Die
Wache muss anschlagen, wenn ein Anker fehlt, und still bleiben, wenn er
im Bestand steht.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import e2e_textanker_wache as wache  # noqa: E402


class AnkerFindenTest(unittest.TestCase):
    """Die Wache muss fehlende Anker finden – und nur die."""

    BESTAND = ("Alle Zahlen sind freie Modellwerte, keine echten Angebote. "
               "Beim Notgroschen zählt schneller Zugriff ohne Bindung.\n")

    def _probe(self, inhalt: str) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "probe.spec.mjs"
            pfad.write_text(inhalt, encoding="utf-8")
            return wache.pruefe([pfad], self.BESTAND)

    def test_anker_im_bestand_bleibt_still(self):
        befunde = self._probe(
            "const inhalt = page.locator('.post-content');\n"
            "await expect(inhalt).toContainText('freie Modellwerte');\n")
        self.assertEqual([], befunde)

    def test_veralteter_satz_wird_gemeldet(self):
        """GENAU der Fehler vom 23.11.2026: Der Text wurde geglättet."""
        befunde = self._probe(
            "const inhalt = page.locator('.post-content');\n"
            "await expect(inhalt).toContainText('frei gewählte Modellannahmen');\n"
            "await expect(inhalt).toContainText('keine Angebote');\n")
        self.assertEqual(2, len(befunde), befunde)
        self.assertIn("frei gewählte Modellannahmen", befunde[0]["text"])

    def test_markdown_auszeichnung_wird_ignoriert(self):
        """`**freie Modellwerte**` steht im DOM als „freie Modellwerte"."""
        befunde = self._probe(
            "const inhalt = page.locator('.post-content');\n"
            "await expect(inhalt).toContainText('**freie** Modellwerte');\n")
        self.assertEqual([], befunde)

    def test_ui_text_ohne_artikelbezug_ist_frei(self):
        """Kopfdaten und Rechner-Ausgaben sind Produkt, nicht Redaktion."""
        befunde = self._probe(
            "const box = page.locator('.newsletter-footer');\n"
            "await expect(box).toContainText('Dienstag & Freitag');\n"
            "await expect(ausgabe.locator('[data-ff-wz-kennzahlen]'))"
            ".toContainText('1 Jahr und 6 Monate');\n")
        self.assertEqual([], befunde)

    def test_kurzer_text_ist_kein_anker(self):
        befunde = self._probe(
            "const inhalt = page.locator('.post-content');\n"
            "await expect(inhalt).toContainText('Kfz');\n")
        self.assertEqual([], befunde)


class ReDoSTest(unittest.TestCase):
    """Der Parser muss linear bleiben – CodeQL py/redos hat hier angeschlagen.

    Die erste Fassung nutzte `(["'])(?:(?!\\1).)*\\1`. Auf einer Zeile aus
    vielen Backslashes wächst der Suchbaum exponentiell. Diese Tests halten
    fest, dass die Heilung (ein Durchlauf statt Regex) bleibt.
    """

    def test_viele_backslashes_bleiben_schnell(self):
        import time
        boese = 'toContainText("' + "\\a" * 40000
        start = time.monotonic()
        ergebnis = wache._anker_in_zeile(boese)
        dauer = time.monotonic() - start
        self.assertLess(dauer, 2.0,
                        f"Parser braucht {dauer:.2f}s für 40.000 Wiederholungen "
                        "– das ist die ReDoS-Form, die CodeQL meldet")
        self.assertEqual([], ergebnis)

    def test_mehrere_anker_in_einer_zeile(self):
        zeile = ('await expect(a).toContainText(\'freie Modellwerte\'); '
                 'await expect(b).toContainText("keine echten Angebote");')
        self.assertEqual(["freie Modellwerte", "keine echten Angebote"],
                         wache._anker_in_zeile(zeile))

    def test_regex_argument_ist_kein_textanker(self):
        self.assertEqual([], wache._anker_in_zeile("toContainText(/abc/i)"))

    def test_unabgeschlossene_zeichenkette_bricht_ab(self):
        self.assertEqual([], wache._anker_in_zeile('toContainText("offen'))


class BestandTest(unittest.TestCase):
    """Der echte Bestand muss durch die Wache gehen."""

    def test_repo_ist_ohne_befund(self):
        befunde = wache.pruefe()
        self.assertEqual(
            [], befunde,
            "E2E-Anker ohne Deckung im Artikelbestand: der betroffene Test "
            f"wird im CI rot: {befunde}")

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(0, wache.selftest())


if __name__ == "__main__":
    unittest.main()
