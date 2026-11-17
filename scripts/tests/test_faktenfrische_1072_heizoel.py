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
import editorial_review_gate as review_gate
import faktenfrische_befund_ledger as ledger
import park_state
import reserve_blocker_klassen
import reserve_custody
import reserve_pool

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
        self.assertNotIn("reserve", self.fm)
        self.assertIn("Redaktionelle Prüfung", self.fm["reserve_blocked"])
        self.assertIs(self.fm["affiliate_exempt"], True)
        self.assertNotIn("/go/", self.body)
        self.assertIn("keine Preisprognose", self.body)
        self.assertIn("redaktionelle Abnahme erforderlich", self.body)

    def test_hold_is_effective_and_not_eligible_for_automatic_deletion(self):
        raw = ARTICLE.read_text(encoding="utf-8")
        self.assertTrue(park_state.reserve_hold(raw))
        self.assertEqual(reserve_custody.zustand(raw), reserve_custody.ZUSTAND_BLOCKIERT)
        self.assertNotIn(ARTICLE, reserve_pool.reserve_drafts())
        loeschbar, bewertung = reserve_blocker_klassen.gate_befund_loeschbar(
            self.fm["reserve_blocked"])
        self.assertFalse(loeschbar)
        self.assertEqual(bewertung["klasse"], reserve_blocker_klassen.MENSCHLICH)
        reaktivierbar, _ = reserve_custody.rueckholbar(self.fm["reserve_blocked"])
        self.assertFalse(reaktivierbar)
        result = review_gate.evaluate_path(ARTICLE)
        self.assertEqual(result["risk"], review_gate.RISK_ELEVATED)
        self.assertEqual(result["status"], "ausstehend")
        # Elevated risk alone is not the YMYL high-risk publication gate; the
        # explicit reserve hold above is the operative publication safeguard.
        self.assertFalse(result["blocking"])

    def test_cover_alt_and_sources_do_not_reintroduce_old_claims(self):
        # The image actually carries the current title, not a promise of an
        # optimal purchase date. The rejected electricity/gas landing page
        # must not silently reappear as a heating-oil source.
        self.assertEqual(self.fm["cover"]["alt"], self.fm["title"])
        sources = self.fm["quellen"]
        self.assertTrue(sources)
        self.assertNotIn(
            "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html",
            [source["url"] for source in sources],
        )
        self.assertTrue(all(source.get("recherchiert_am") for source in sources))
        self.assertLess(str(self.fm["faktencheck"]),
                        str(sources[0]["recherchiert_am"]))

    def test_all_five_findings_are_closed_by_current_text_decisions(self):
        fassungen, aliases = ledger.bestand_identitaeten()
        offene = ledger.offene_befunde(aliases=aliases, fassungen=fassungen)
        noch_offen = FINDING_IDS.intersection(e["id"] for e in offene)
        self.assertEqual(noch_offen, set(),
                         f"Heizöl-F4-Befunde wieder offen: {sorted(noch_offen)}")

    def test_typografie_heilung_oeffnet_die_fuenf_befunde_nicht(self):
        """Der Lauf vom 16.11.2026, der dieses Gate zuletzt rot gemacht hat.

        `fix_spaces.py` und `fix_linebreaks.py` heilen ausschließlich
        Leerraum. Vor der Projektion `betrieb-v4` verschob jede eingefügte
        Leerstelle den Aussage-Hash und riss die fünf dokumentierten
        Entscheidungen auf – das PR-Gate verlangt sie aber geschlossen.
        Hier läuft der echte Produktionspfad (ohne Schreibzugriff) über den
        echten Artikel: Der Befundstand muss unverändert bleiben.
        """
        import fix_linebreaks
        import fix_spaces
        import post_utils

        raw = ARTICLE.read_text(encoding="utf-8")
        _, fm, body = post_utils.split_article(raw)
        geheilt, _ = fix_spaces.fix_body(body)
        geheilt, _ = fix_linebreaks.self_heal(geheilt)
        vorher = ledger.text_hash({"fm": fm, "body": body})
        # Gegenprobe: Die alte, byte-genaue Projektion ist NICHT der Anker –
        # sonst prüfte dieser Test nur, dass sich nichts bewegt.
        self.assertNotEqual(vorher, ledger.text_hash({"fm": fm, "body": body},
                                                    "betrieb-v3"),
                            "v3 und v4 sind identisch – der Test misst nichts")
        self.assertEqual(vorher, ledger.text_hash({"fm": fm, "body": geheilt}),
                         "Typografie-Heilung verschiebt den Aussage-Hash")
        fassungen, aliases = ledger.bestand_identitaeten()
        offen = ledger.offene_befunde(
            fassungen={SLUG: {"text": vorher,
                              "pruef": ledger.pruef_hash({"fm": fm, "body": geheilt})}},
            aliases=aliases)
        self.assertEqual(FINDING_IDS.intersection(e["id"] for e in offen), set(),
                         "Heilung hat einen der fünf Befunde wieder geöffnet")

if __name__ == "__main__":
    unittest.main()
