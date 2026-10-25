"""Regression tests for the weekly Affiliate-Link-Check (#742).

The previous checker let a broad pillar override a specific commercial intent:
a Handyvertrag article in ``internet-dsl`` was expected to link to DSL even
though its CTA correctly linked to Handytarife. These tests keep the checker
aligned with the shared intent contract and ensure explicit editorial
exemptions do not become a route-validation bypass.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    import affiliate_link_check as checker
except ModuleNotFoundError as exc:  # pragma: no cover - CI installs PyYAML
    if exc.name == "yaml":
        raise unittest.SkipTest("PyYAML fehlt; die SEO-Workflow-Umgebung installiert es")
    raise


HANDY_TITLE = "Handyvertrag kündigen: Enddatum, Nachweis und Rufnummer"
HANDY_BODY = "👉 **Jetzt vergleichen:** [**Jetzt Handytarife vergleichen**](/go/handytarife/)"


def article(slug, title, body, pillar="internet-dsl", frontmatter=""):
    return {
        "path": "(test)",
        "slug": slug,
        "title": title,
        "pillar": pillar,
        "body": body,
        "content": body,
        "frontmatter": frontmatter,
        "is_pillar": False,
    }


class IntentBeforePillarTests(unittest.TestCase):
    def test_new_handy_article_in_internet_pillar_uses_handytarife(self):
        post = article("neuer-handyvertrag", HANDY_TITLE, HANDY_BODY)

        self.assertEqual(
            checker.expected_target(post),
            ("check24", "handytarife", "Handytarife"),
        )
        self.assertFalse([
            problem for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ])

    def test_live_ticket_article_is_green_and_matches_the_intent_contract(self):
        post = next(
            post for post in checker.load_posts()
            if post["slug"] == "2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung"
        )

        self.assertEqual(
            checker.expected_target(post),
            ("check24", "handytarife", "Handytarife"),
        )
        self.assertFalse([
            problem for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ])

    def test_a_cta_cannot_self_certify_its_own_topic(self):
        post = article(
            "neutraler-netzratgeber",
            "So prüfst du deine Verbindung",
            "[Jetzt Handytarife vergleichen](/go/handytarife/)",
        )

        # Der CTA ist kein Themenbeweis. Ohne Produktbezug im redaktionellen
        # Inhalt greift der breite Pillar-Fallback – und erkennt den Fehl-Link.
        self.assertEqual(
            checker.expected_target(post),
            ("check24", "dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
        )
        self.assertTrue(any(
            "Fehlt der passende Deep-Link" in problem["msg"]
            for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ))

    def test_body_cross_selling_does_not_override_article_pillar(self):
        post = article(
            "wlan-mesh-ratgeber",
            "WLAN verbessern: Mesh und Empfang",
            "Ein Stromtarif kann die Fixkosten senken.",
        )

        # Inhaltliche Erwähnungen sind nicht automatisch Kaufabsicht. Im
        # Bestand sind solche Querverweise bewusst redaktionell möglich.
        self.assertEqual(
            checker.expected_target(post),
            ("check24", "dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
        )

    def test_live_vacation_budget_article_is_green_and_matches_the_intent_contract(self):
        post = next(
            post for post in checker.load_posts()
            if post["slug"] == "2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen"
        )

        self.assertEqual(
            checker.expected_target(post)[:2],
            ("check24", "pauschalreisen-vergleich&cat=9"),
        )
        self.assertFalse([
            problem for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ])

    def test_new_vacation_budget_article_in_mietwagen_pillar_uses_pauschalreisen(self):
        post = article(
            "2026-10-19-urlaubskasse-clever-aufbessern",
            "Urlaubskasse clever aufbessern",
            "👉 **Jetzt vergleichen:** [**Pauschalreisen vergleichen**](/go/reisen/)",
            pillar="mietwagen",
        )

        self.assertEqual(
            checker.expected_target(post),
            ("check24", "pauschalreisen-vergleich&cat=9", "Pauschalreisen"),
        )
        self.assertFalse([
            problem for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ])

    def test_mietwagen_pillar_family_accepts_reisen_for_general_vacation_but_blocks_strict_mietwagen_mismatch(self):
        general_vacation = article(
            "sommerreise-planen-tipps",
            "Sommerreise planen: So behältst du die Kosten im Griff",
            "[Jetzt Reiseangebote vergleichen](/go/reisen/)",
            pillar="mietwagen",
        )
        findings = checker.check_post(general_vacation)
        self.assertFalse([p for p in findings if p["severity"] == "error"])
        self.assertTrue(any(
            p["severity"] == "info" and "Produktfamilie des Pillars „mietwagen“" in p["msg"]
            for p in findings
        ))

        strict_mietwagen = article(
            "2026-10-21-mietwagen-fallen-im-urlaub-vermeiden",
            "Mietwagen-Fallen im Urlaub vermeiden",
            "[Jetzt Reiseangebote vergleichen](/go/reisen/)",
            pillar="mietwagen",
        )
        self.assertTrue(any(
            "mietwagen-preisvergleich&cat=10" in p["msg"]
            for p in checker.check_post(strict_mietwagen)
            if p["severity"] == "error"
        ))

    def test_konto_karten_explicit_product_routes_and_pillar_family(self):
        kredit_post = article(
            "2026-10-20-ratenkredit-zinsen-vergleichen",
            "Ratenkredit Zinsen vergleichen: Worauf du achten musst",
            "[Jetzt Ratenkredit vergleichen](/go/kredit/)",
            pillar="konto-karten",
        )
        self.assertEqual(
            checker.expected_target(kredit_post),
            ("check24", "kredit-vergleich", "Ratenkredit"),
        )
        self.assertFalse([p for p in checker.check_post(kredit_post) if p["severity"] == "error"])

        banking_fees_post = article(
            "2026-10-06-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto",
            "Bankgebühren senken: 7 Schritte zum günstigeren Konto",
            "[Kreditkarten ohne Jahresgebühr vergleichen](/go/kreditkarte/)",
            pillar="konto-karten",
        )
        self.assertFalse([p for p in checker.check_post(banking_fees_post) if p["severity"] == "error"])

        strict_girokonto = article(
            "kostenloses-girokonto-wechseln",
            "Girokonto wechseln: Schritt für Schritt",
            "[Jetzt Ratenkredit vergleichen](/go/kredit/)",
            pillar="konto-karten",
        )
        self.assertTrue(any(
            "c24bank&cat=14" in p["msg"]
            for p in checker.check_post(strict_girokonto)
            if p["severity"] == "error"
        ))

    def test_versicherungen_explicit_product_routes_enforce_exact_sparte(self):
        wohngebaeude = article(
            "2026-10-20-wohngebaeudeversicherung-leistungen",
            "Wohngebäudeversicherung Vergleich: Worauf Eigentümer achten müssen",
            "[Jetzt Hausrat vergleichen](/go/hausrat/)",
            pillar="versicherungen",
        )
        self.assertEqual(
            checker.expected_target(wohngebaeude),
            ("tarifcheck", "wohngebaeudeversicherung", "Wohngebäudeversicherung"),
        )
        self.assertTrue(any(
            "deep=wohngebaeudeversicherung" in p["msg"]
            for p in checker.check_post(wohngebaeude)
            if p["severity"] == "error"
        ))

    def test_all_configured_deeps_exist_in_central_gateway_registry(self):
        registered_targets = {
            (t[0], t[1])
            for route in checker._REGISTRY
            for t in (checker._target_from_registered_route(route),)
            if t and t[1] is not None
        }
        for slug, (deep_val, _name) in checker.SLUG_DEEP.items():
            self.assertIn(("check24", deep_val), registered_targets, slug)
        for pillar_key, entries in checker.PILLAR_DEEP_ALT.items():
            for deep_val, _name in entries:
                self.assertIn(("check24", deep_val), registered_targets, pillar_key)
        for slug, deep_val in checker.TARIF_SLUG_DEEP.items():
            self.assertIn(("tarifcheck", deep_val), registered_targets, slug)

    def test_all_live_posts_and_pillars_pass_without_errors(self):
        offenders = {}
        for post in checker.load_posts():
            errors = [
                p["msg"] for p in checker.check_post(post)
                if p["severity"] == "error"
            ]
            if errors:
                offenders[post["slug"]] = errors
        self.assertEqual(offenders, {})


class EditorialExemptionTests(unittest.TestCase):
    REASON = "Reiner DNS-Messtest ohne passendes Tarifangebot."

    def test_reasoned_exemption_allows_an_informational_article_without_cta(self):
        post = article(
            "dns-messtest",
            "DNS-Antwortzeiten testen",
            "Vergleiche die Antwortzeiten mehrerer Resolver mit dig.",
            frontmatter=(
                "affiliate_exempt: true\n"
                f'affiliate_exempt_reason: "{self.REASON}"\n'
            ),
        )

        self.assertEqual(checker.affiliate_exemption(post), (True, self.REASON, ""))
        findings = checker.check_post(post)
        self.assertFalse([p for p in findings if p["severity"] == "error"])
        self.assertTrue(any(
            p["severity"] == "info" and self.REASON in p["msg"]
            for p in findings
        ))

    def test_live_dns_measurement_article_is_explicitly_exempt(self):
        post = next(
            post for post in checker.load_posts()
            if post["slug"] == "2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt"
        )

        exempt, reason, metadata_error = checker.affiliate_exemption(post)
        self.assertTrue(exempt)
        self.assertIn("passendes Tarifangebot", reason)
        self.assertEqual(metadata_error, "")
        self.assertFalse([
            problem for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ])

    def test_missing_link_remains_blocking_without_explicit_exemption(self):
        post = article("unmarkierter-ratgeber", "Technikratgeber", "Nur redaktioneller Text.")

        self.assertEqual(
            checker.check_post(post),
            [{"severity": "error", "msg": "KEIN Affiliate-Link vorhanden"}],
        )

    def test_exemption_without_reason_fails_closed(self):
        post = article(
            "dns-ohne-grund", "DNS-Messtest", "Nur redaktioneller Text.",
            frontmatter="affiliate_exempt: true\n",
        )

        self.assertTrue(any(
            "braucht eine nichtleere Begründung" in problem["msg"]
            for problem in checker.check_post(post)
        ))

    def test_empty_yaml_reason_with_comment_fails_closed(self):
        post = article(
            "dns-leerer-grund", "DNS-Messtest", "Nur redaktioneller Text.",
            frontmatter=(
                "affiliate_exempt: true\n"
                'affiliate_exempt_reason: "" # Ein Kommentar ist kein Grund\n'
            ),
        )

        self.assertTrue(any(
            "braucht eine nichtleere Begründung" in problem["msg"]
            for problem in checker.check_post(post)
        ))

    def test_exemption_does_not_hide_a_wrong_link_if_one_exists(self):
        post = article(
            "handyvertrag-mit-falschem-link",
            HANDY_TITLE,
            "[Jetzt DSL vergleichen](/go/dsl/)",
            frontmatter=(
                "affiliate_exempt: true\n"
                f'affiliate_exempt_reason: "{self.REASON}"\n'
            ),
        )

        self.assertTrue(any(
            "Fehlt der passende Deep-Link" in problem["msg"]
            for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ))

    def test_malformed_exemption_does_not_skip_existing_link_validation(self):
        post = article(
            "handyvertrag-mit-fehlerhafter-ausnahme",
            HANDY_TITLE,
            "[Jetzt DSL vergleichen](/go/dsl/)",
            frontmatter="affiliate_exempt: true\n",
        )

        messages = [
            problem["msg"] for problem in checker.check_post(post)
            if problem["severity"] == "error"
        ]
        self.assertTrue(any("nichtleere Begründung" in message for message in messages))
        self.assertTrue(any("Fehlt der passende Deep-Link" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
