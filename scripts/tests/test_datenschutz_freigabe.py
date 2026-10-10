"""Source contract: published privacy claims must match the safe default config.

This is NOT a legal review or a substitute for a production/network audit.
"""
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class DatenschutzQuellvertrag(unittest.TestCase):
    def test_analytics_deaktiviert_und_banner_nur_bei_aktivierter_instanz(self):
        params = tomllib.loads(read("hugo.toml"))["params"]["umami"]
        self.assertEqual(params["websiteId"], "")
        self.assertTrue(params["consentRequired"])
        self.assertIn('with site.Params.umami.websiteId', read("layouts/baseof.html"))
        self.assertIn('with site.Params.umami.websiteId', read("layouts/_partials/extend_footer.html"))
        self.assertIn('with site.Params.umami.websiteId', read("layouts/_partials/deferred_scripts.html"))
        policy = read("content/datenschutz/index.md")
        self.assertIn("Reichweitenmessung mit Umami deaktiviert", policy)
        self.assertNotIn("Aktuell aktiv ist der cookieless-Modus", policy)

    def test_widerruf_und_altes_cookie(self):
        loader = read("layouts/_partials/deferred_scripts.html")
        self.assertIn("getConsent() !== 'all'", loader)
        self.assertIn("window.location.reload()", loader)
        self.assertNotIn("if (!shouldLoad) return", loader)
        self.assertIn("max-age=0", read("layouts/_partials/extend_footer.html"))
        banner = read("layouts/_partials/consent_banner.html")
        self.assertIn("Cookies auf externen Partnerseiten verwalten wir hier nicht", banner)

    def test_newsletter_retention_contract(self):
        worker = read("newsletter-worker/src/index.js")
        self.assertIn("TTL_UNSUB_SEK = 29 * 24 * 60 * 60", worker)
        self.assertIn("PFLEGE_CRON = '13 2 * * *'", worker)
        self.assertIn("await env.ABO.delete(key)", worker)
        self.assertIn("eintrag.token === sauber", worker)
        wrangler = read("newsletter-worker/wrangler.toml")
        self.assertIn('"13 2 * * *"', wrangler)
        self.assertNotIn('placement = "eu"\n', wrangler)
        self.assertRegex(wrangler, r"kv namespace create ABO --jurisdiction=eu")
        self.assertIn("GitHub-Actions-Läufe", read("content/datenschutz/index.md"))


if __name__ == "__main__":
    unittest.main()
