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
