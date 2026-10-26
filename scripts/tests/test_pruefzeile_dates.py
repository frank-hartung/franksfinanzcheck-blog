"""The editorial revision indicator must use actual dates from article_dates."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PruefzeileDates(unittest.TestCase):
    def test_dates_contract(self):
        template = (ROOT / "layouts/_partials/ff_pruefzeile.html").read_text()
        source = (ROOT / "layouts/_partials/article_dates.html").read_text()
        self.assertIn('"published" $published "modified" $modified', source)
        self.assertIn('$dates.modified.After $dates.published', template)
        self.assertNotIn('$dates.firstindexed', template)
        self.assertNotIn('dateFormat "YYYYMMdd"', template)
