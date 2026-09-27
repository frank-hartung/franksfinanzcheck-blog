"""Vertragstests für den saisonalen SEO/GEO-Hero-Refresh.

Die Tests sind absichtlich offline: Agent Reach und Claude werden im Workflow
integriert, die gefährlichen Entscheidungen (Saisonfenster, Kandidatenvertrag,
YAML-Update) müssen aber auch ohne Netz beweisbar bleiben.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import saisonaler_hero_refresh as hero  # noqa: E402


HERBST = {
    "id": "herbst",
    "name": "Herbst",
    "ab": "09-01",
    "bis": "11-30",
    "hero_title": "Herbst-Check: Bei Strom, Gas & Versicherung Geld sparen",
    "hero_lead": "FranksFinanzcheck hilft dir im Herbst, Strom, Gas, Internet und Versicherungen strukturiert zu vergleichen – unabhängig, verständlich und ohne Verkaufsdruck. Du prüfst zuerst die teuerste Rechnung, erkennst relevante Tarifangaben und findest den passenden nächsten Schritt.",
}


class Saisonlogik(unittest.TestCase):
    def test_herbst_grenzen_sind_inklusive(self):
        self.assertEqual(hero.season_for(dt.date(2026, 9, 1), [HERBST])["id"], "herbst")
        self.assertEqual(hero.season_for(dt.date(2026, 11, 30), [HERBST])["id"], "herbst")
        self.assertIsNone(hero.season_for(dt.date(2026, 8, 31), [HERBST]))

    def test_jahreswechsel_funktioniert(self):
        winter = dict(HERBST, id="winter", name="Winter", ab="12-01", bis="02-29")
        self.assertEqual(hero.season_for(dt.date(2026, 12, 1), [winter])["id"], "winter")
        self.assertEqual(hero.season_for(dt.date(2027, 2, 28), [winter])["id"], "winter")


class GeoVertrag(unittest.TestCase):
    def test_kuratierte_basis_besteht(self):
        self.assertEqual(hero.validate_candidate(HERBST["hero_title"], HERBST["hero_lead"], HERBST, []), [])

    def test_zahlen_und_formelle_ansprache_werden_verworfen(self):
        candidate = HERBST["hero_lead"].replace("Herbst", "Herbst 2026").replace("dir", "Ihnen")
        findings = hero.validate_candidate(HERBST["hero_title"], candidate, HERBST, [])
        self.assertTrue(any("Zahl" in finding for finding in findings))
        self.assertTrue(any("Sie-Anrede" in finding for finding in findings))

    def test_entity_und_kategorien_sind_pflicht(self):
        candidate = HERBST["hero_lead"].replace("FranksFinanzcheck", "Dieser Ratgeber")
        findings = hero.validate_candidate(HERBST["hero_title"], candidate, HERBST, [])
        self.assertTrue(any("Entity" in finding for finding in findings))

    def test_format_parser_akzeptiert_nur_beide_felder(self):
        raw = f"TITLE: {HERBST['hero_title']}\nLEAD: {HERBST['hero_lead']}"
        self.assertEqual(hero.parse_answer(raw), (HERBST["hero_title"], HERBST["hero_lead"]))
        self.assertIsNone(hero.parse_answer("TITLE: nur ein Feld"))


class SicheresSchreiben(unittest.TestCase):
    def test_rewrite_beruehrt_nur_den_angegebenen_saisonblock(self):
        original_path = hero.SAISONS
        source = """saisons:
  - id: herbst
    hero_title: \"alt herbst\"
    hero_lead: \"alt lead herbst\"
  - id: winter
    hero_title: \"alt winter\"
    hero_lead: \"alt lead winter\"
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "saisons.yaml"
            target.write_text(source, encoding="utf-8")
            hero.SAISONS = target
            try:
                hero.rewrite_fields("herbst", "neu herbst", "neu lead herbst")
            finally:
                hero.SAISONS = original_path
            result = target.read_text(encoding="utf-8")
        self.assertIn('hero_title: "neu herbst"', result)
        self.assertIn('hero_lead: "neu lead herbst"', result)
        self.assertIn('hero_title: "alt winter"', result)
        self.assertIn('hero_lead: "alt lead winter"', result)


if __name__ == "__main__":
    unittest.main()
