"""#762: Editorial exemptions waive only the minimum-link requirement.

Temporary content/build fixtures exercise the public gate path including healing,
report and state. No network, Hugo installation or repository writes required.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import affiliate_exemption as contract
import affiliate_integrity_gate as gate
import affiliate_link_check as weekly

REASON = "Reiner DNS-Messtest ohne passendes Tarifangebot."
EXEMPT = f'affiliate_exempt: true\naffiliate_exempt_reason: "{REASON}"\n'
URL = "https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=strom"
CTA = "👉 **Jetzt vergleichen und sparen:** [**Stromtarife vergleichen**](/go/strom/)"
ANCHOR = '<a href="/go/strom/" rel="sponsored" data-klick="affiliate_click">Stromtarife vergleichen</a>'


class SharedContractTests(unittest.TestCase):
    def test_both_adapters_use_the_same_contract(self):
        cases = [
            ("", False, False),
            (EXEMPT, True, False),
            ("affiliate_exempt: false\n", False, False),
            ("affiliate_exempt: true\n", False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: "" # kein Grund\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: "   "\n', False, True),
            ('affiliate_exempt: "true"\naffiliate_exempt_reason: "Grund"\n', False, True),
            ('affiliate_exempt_reason: "Grund"\n', False, True),
            ('affiliate_exempt: false\naffiliate_exempt_reason: "Grund"\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: 42\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: [Grund]\n', False, True),
            ('title: [kaputt\n', False, True),
            ('- keine\n- Metadaten\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: >\n  DNS-Test\n  ohne Angebot\n', True, False),
        ]
        for fm, exempt, error in cases:
            with self.subTest(frontmatter=fm):
                expected = contract.affiliate_exemption(fm)
                self.assertEqual(expected[0], exempt)
                self.assertEqual(bool(expected[2]), error)
                self.assertEqual(weekly.affiliate_exemption({"frontmatter": fm}), expected)
                self.assertEqual(contract.exemption_for_article({"fm": fm}), expected)


class IntegrityExemptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.posts = self.root / "content" / "posts"
        self.post = self.posts / "messtest" / "index.md"
        self.post.parent.mkdir(parents=True)
        self.html = self.root / "public" / "posts" / "messtest" / "index.html"
        self.html.parent.mkdir(parents=True)
        self.html.write_text("<html><body>DNS-Messtest</body></html>")
        registry = self.root / "scripts" / "check24_links.yaml"
        registry.parent.mkdir()
        registry.write_text(f'links:\n  strom: "{URL}"\n')
        gateway = self.root / "public" / "go" / "strom" / "index.html"
        gateway.parent.mkdir(parents=True)
        gateway.write_text(
            '<meta name="robots" content="noindex,nofollow">'
            f'<meta http-equiv="refresh" content="0; url={URL}">')
        self.gateway = gateway
        self.report = self.root / "report.md"
        self.state = self.root / "state.json"
        for name, value in (("REPORT", self.report), ("STATE", self.state),
                            ("ONLY_SLUGS", [])):
            patcher = patch.object(gate, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.write_post()

    def write_post(self, fm=EXEMPT, body="DNS-Messtest ohne Tarifangebot.\n"):
        self.post.write_text(
            '---\ntitle: "Messtest"\ndraft: false\npillar: "internet-dsl"\n'
            + fm + "---\n\n" + body)

    def run_gate(self):
        return gate.run(self.root, self.posts, do_heal=True, allow_build=False)

    def test_exemption_is_green_auditable_idempotent_and_never_injects_ctas(self):
        before = self.post.read_bytes()
        first = self.run_gate()
        self.assertEqual(first["exit_code"], gate.EXIT_OK, first)
        self.assertEqual(first["checked"], 1)
        self.assertEqual(first["exemptions"], {"messtest": REASON})
        self.assertFalse(first["healed"])
        text = gate.write_report(first)
        gate.write_state(first)
        self.assertIn(REASON, text)
        self.assertIn("redaktionelle Ausnahme", text)
        self.assertNotIn("0 → 0 ✅", text)
        state = json.loads(self.state.read_text())
        self.assertEqual(state["exemptions"], {"messtest": REASON})
        self.assertEqual(state["unresolved_problems"], [])
        self.assertEqual(state["content_problems"], [])
        second = self.run_gate()
        gate.write_report(second)
        gate.write_state(second)
        self.assertFalse(second["verdict_changed"])
        self.assertFalse(second["report_changed"])
        self.assertEqual(self.post.read_bytes(), before)

    def test_missing_link_without_exemption_remains_red(self):
        self.write_post(fm="")
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("Kein einziger Affiliate-Link", result["render_problems"]["messtest"])

    def test_invalid_exemption_blocks_even_with_valid_links(self):
        self.write_post(fm="affiliate_exempt: true\n", body=CTA)
        self.html.write_text(ANCHOR)
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("nichtleere Begründung", result["render_problems"]["messtest"])
        self.assertIn("messtest", result["findings"])
        self.assertFalse(result["exemptions"])

    def test_exemption_does_not_hide_missing_source_link_in_html(self):
        self.write_post(body=CTA)
        article = gate.load_live_articles(self.posts)[0]
        result = gate.verify_article_render(article, {"strom": URL}, self.root / "public")
        self.assertTrue(any("NICHT im gebauten HTML" in p for p in result["problems"]))

    def test_exemption_does_not_hide_non_sponsored_link(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR.replace('rel="sponsored"', 'rel="nofollow"'))
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn('ohne rel="sponsored"', result["render_problems"]["messtest"])

    def test_exemption_does_not_hide_unregistered_gateway(self):
        self.html.write_text(ANCHOR.replace("strom/", "unbekannt/"))
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("nicht in check24_links.yaml registriert", result["render_problems"]["messtest"])

    def test_exemption_does_not_hide_raw_partner_links(self):
        self.html.write_text(f'<a href="{URL}">Partner</a>')
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("Roher Partner-Link", result["render_problems"]["messtest"])

    def test_exempt_article_with_valid_link_still_passes_full_proof(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_OK, result)
        self.assertEqual(result["per_article"][0]["expected"], 1)
        self.assertEqual(result["per_article"][0]["rendered"], 1)

    def test_exemption_does_not_hide_missing_gateway_noindex(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        self.gateway.write_text(f'<meta http-equiv="refresh" content="0; url={URL}">')
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("noindex", result["render_problems"]["messtest"])

    def test_exemption_does_not_hide_wrong_redirect(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        self.gateway.write_text('<meta name="robots" content="noindex">'
                                '<meta http-equiv="refresh" content="0; url=https://example.org/">')
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("messtest", result["render_problems"])

    def test_missing_built_page_is_not_exempt(self):
        self.html.unlink()
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("Gebaute Seite fehlt", result["render_problems"]["messtest"])

    def test_missing_build_is_tool_failure_not_green_exemption(self):
        import shutil
        shutil.rmtree(self.root / "public")
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_TOOL)
        self.assertTrue(result["errors"])

    def test_healed_cta_does_not_clear_invalid_exemption_metadata(self):
        self.write_post(fm="affiliate_exempt: true\n", body=CTA + ")")
        result = gate.heal_file(self.post, {"strom": URL, "allgemein": URL})
        self.assertTrue(result["healed"])
        self.assertTrue(any("nichtleere Begründung" in p for p in result["problems"]))
        second = gate.heal_file(self.post, {"strom": URL, "allgemein": URL})
        self.assertFalse(second["healed"])
        self.assertTrue(second["problems"])

    def test_exemption_does_not_hide_broken_cta_structure(self):
        self.write_post(body=CTA + ")")
        article = gate.load_live_articles(self.posts)[0]
        findings = gate.markdown_findings([article], {"strom"})
        self.assertIn("messtest", findings)
        self.assertTrue(findings["messtest"]["broken_kinds"])

    def test_actual_dns_article_remains_explicitly_exempt(self):
        slug = "2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt"
        article = next(a for a in gate.load_live_articles() if a["slug"] == slug)
        exempt, reason, error = contract.exemption_for_article(article)
        self.assertTrue(exempt)
        self.assertIn("passendes Tarifangebot", reason)
        self.assertEqual(error, "")
        self.assertFalse(gate.markdown_findings([article], set(gate.load_registry())))


if __name__ == "__main__":
    unittest.main()
