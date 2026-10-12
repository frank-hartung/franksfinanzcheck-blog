"""Prompt↔Gate-Vertrag für Zahlen (WF-D4E0, #710).

Befund: Der Geburts-Prompt in generate_drafts.py lehrte das Modell jahrelang,
harte Zahlen mit „ca./rund/etwa“ einzuordnen – das harte RS5-Gate
(redaktions_standard._reserve_numeric_claim_findings) wertet solche
Abschwächungen ausdrücklich NICHT als Beleg und verlangt im selben Satz einen
Quellenlink oder eine Modell-Kennzeichnung. Prompt und Gate widersprachen
sich: Jeder frisch erzeugte Reserve-Kandidat trug die ablehnende Klasse
bereits bei der Geburt in sich, wurde im Geburts-Gate verworfen oder parkte
in der Reserve (12.10.2026: 6 von 11 Kandidaten allein an RS5 blockiert,
Vorrat 5/6, Lauf rot).

Dieser Test verriegelt die Heilung: Fällt der Prompt je wieder auf die
Hedge-Formel zurück, wird der Lauf rot – bevor ein einziger Kandidat
geboren wird.
"""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import extend_articles as ea  # noqa: E402
import generate_drafts as gd  # noqa: E402
import profi_polish as pp  # noqa: E402
import redaktions_standard as rs  # noqa: E402
import update_articles as ua  # noqa: E402


class ZahlenPromptVertragTests(unittest.TestCase):
    def setUp(self):
        self.prompt_quelle = inspect.getsource(gd.generate_article_text)

    def test_prompt_verlangt_modell_kennzeichnung_im_selben_satz(self):
        self.assertIn("Beispielrechnung/Modellrechnung", self.prompt_quelle)
        self.assertIn("SELBEN", self.prompt_quelle)
        self.assertIn("RS5", self.prompt_quelle)

    def test_prompt_lehrt_keine_hedge_einordnung_mehr(self):
        # Die alte Formel erklärte „ca./rund“ zur ausreichenden Einordnung
        # und erzeugte damit RS5-Funde am Fließband.
        self.assertNotIn("Harte Zahlen nur mit Einordnung", self.prompt_quelle)
        self.assertNotIn("Zahlen nur als Spannen", self.prompt_quelle)
        self.assertNotIn("überraschende Zahl", self.prompt_quelle)

    def test_alle_heiler_prompts_befolgen_rs5_vertrag(self):
        # WF-D4E0 (#710): Nicht nur generate_drafts.py, sondern auch die
        # nachgelagerten Heiler (profi_polish, redaktions_standard,
        # extend_articles, update_articles) dürfen niemals „ca. X–Y €“ als
        # ausreichende Zahlen-Einordnung lehren.
        for name, fn in (
            ("profi_polish.build_polish_prompt", pp.build_polish_prompt),
            ("redaktions_standard.heal_article_ai", rs.heal_article_ai),
            ("extend_articles.build_prompt", ea.build_prompt),
            ("update_articles.ai_update_article", ua.ai_update_article),
        ):
            src = inspect.getsource(fn)
            self.assertNotIn("ca. X–Y €", src, f"{name} lehrt noch 'ca. X–Y €'")
            self.assertNotIn("ca. 30–40 €", src, f"{name} lehrt noch 'ca. 30–40 €'")
            self.assertNotIn("Zahlen nur mit ca./rund/Spanne", src,
                             f"{name} lehrt noch 'Zahlen nur mit ca./rund/Spanne'")
            self.assertIn("Beispielrechnung", src,
                          f"{name} nennt 'Beispielrechnung' nicht als RS5-Anker")

    def test_system_prompt_und_gate_sind_sich_einig(self):
        self.assertIn("macht eine unbelegte Zahl nicht belastbar", gd.SYSTEM_PROMPT)

    def test_gate_wertet_hedge_nicht_als_beleg(self):
        hedged = "Das spart dir ca. 50 € im Jahr bei deiner Bank."
        self.assertTrue(rs._reserve_numeric_claim_findings(hedged))

    def test_gate_akzeptiert_modell_kennzeichnung(self):
        modell = ("Das spart in der Beispielrechnung oft 50 € bis 150 € im Jahr, "
                  "wenn deine Bank heute eine Grundgebühr verlangt.")
        self.assertFalse(rs._reserve_numeric_claim_findings(modell))

    def test_gate_akzeptiert_quellenlink_im_satz(self):
        belegt = ("Der Beitrag liegt bei 50 € im Jahr "
                  "[laut Anbieter](https://example.org/tarif).")
        self.assertFalse(rs._reserve_numeric_claim_findings(belegt))


if __name__ == "__main__":
    unittest.main()
