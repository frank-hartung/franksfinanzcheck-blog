"""Regressionstest für den redaktionellen Datumsnachweis im Hugo-Template.

Die Produktion brach ab, weil das Template ein Go-Datumsformat wie einen
JavaScript-Formatstring behandelte und danach ein Feld las, das
article_dates.html gar nicht zurückgibt. Dieser Vertrag hält Vergleich und
Datenquelle zusammen.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "layouts" / "_partials" / "ff_pruefzeile.html"
DATES = ROOT / "layouts" / "_partials" / "article_dates.html"


class PruefzeileDatumsvertrag(unittest.TestCase):
    def test_vergleicht_die_beiden_tatsaechlich_gelieferten_zeitwerte(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        dates = DATES.read_text(encoding="utf-8")
        self.assertIn('$dates.modified.After $dates.published', template)
        self.assertIn('"published" $published "modified" $modified', dates)

    def test_keine_ungueltige_layout_formatierung_oder_phantomspalte(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn('dateFormat "YYYYMMdd"', template)
        self.assertNotIn("$dates.firstindexed", template)


if __name__ == "__main__":
    unittest.main()
