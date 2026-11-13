"""Regression guard for the five Heizöl findings tracked by issue #1072.

These findings had previously been marked resolved while the held draft still
contained the unsupported prices and seasonal advice. The test protects the
actual copy and verifies the fassungsgebundene follow-up decisions; it does
not certify the article for publication.
"""
from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import faktenfrische_befund_ledger as ledger

SLUG = "2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu"
ARTICLE = ROOT / "content" / "posts" / SLUG / "index.md"
FINDING_IDS = {
    "0b564f460c41218244bd",  # Januar/Februar-Tief
    "3ad2eefed314eb172c26",  # 10–20 % Herbst-Ersparnis
    "43788c2cdcdfda52e753",  # 0,80 €/Liter
    "5eedec8afbdef6a4ca49",  # bis zu 15 % Mehrkosten
    "81881c5bc61824d25f5a",  # 4-Wochen-/12-Monats-Regel
}


class Heizol1072Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = ARTICLE.read_text(encoding="utf-8")
        _, frontmatter, cls.body = raw.split("---", 2)
        cls.fm = yaml.safe_load(frontmatter)

    def test_unsupported_price_and_season_claims_stay_removed(self):
        text = (str(self.fm) + "\n" + self.body).casefold()
        for fragment in (
            "0,80", "1,10", "300 €", "10 bis 20", "15 %",
            "12 monaten", "vier wochen", "januar", "februar",
            "november", "dezember", "saisonalen tiefpunkt",
        ):
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, text)

    def test_replacement_is_held_and_has_no_irrelevant_affiliate_route(self):
        self.assertIs(self.fm["draft"], True)
        self.assertIs(self.fm["reserve"], True)
        self.assertIs(self.fm["affiliate_exempt"], True)
        self.assertNotIn("/go/", self.body)
        self.assertIn("keine Preisprognose", self.body)
        self.assertIn("redaktionelle Abnahme erforderlich", self.body)

    def test_all_five_findings_are_closed_by_current_text_decisions(self):
        fassungen, aliases = ledger.bestand_identitaeten()
        offene = ledger.offene_befunde(aliases=aliases, fassungen=fassungen)
        noch_offen = FINDING_IDS.intersection(e["id"] for e in offene)
        self.assertEqual(noch_offen, set(),
                         f"Heizöl-F4-Befunde wieder offen: {sorted(noch_offen)}")


if __name__ == "__main__":
    unittest.main()
