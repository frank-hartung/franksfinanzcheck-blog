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
    def test_umami_und_analyse_banner_entfernt(self):
        # Umami wurde am 11.10.2026 entfernt (Kostenentscheidung, nicht Datenschutz).
        # Diese Prüfung belegt, dass keine Konfiguration und kein Banner mehr übrig sind.
        self.assertNotIn("umami", tomllib.loads(read("hugo.toml")).get("params", {}))
        self.assertNotIn("site.Params.umami", read("layouts/baseof.html"))
        self.assertFalse((ROOT / "layouts/_partials/consent_banner.html").exists())
        for datei in ("layouts/baseof.html", "layouts/_partials/extend_footer.html",
                      "layouts/_partials/deferred_scripts.html", "layouts/_partials/extend_head.html"):
            self.assertNotIn("site.Params.umami", read(datei), datei)
        # Rechtstext: Umami darf darin nicht mehr vorkommen, und die Aussage
        # „keine Analyse-Cookies“ muss stehen.
        policy = read("content/datenschutz/index.md")
        self.assertNotIn("umami", policy.lower())
        self.assertIn("Wir setzen keine Cookies für Analyse", policy)
        self.assertNotIn("Aktuell aktiv ist der cookieless-Modus", policy)

    def test_partner_hosts_stehen_in_der_datenschutzerklaerung(self):
        # Jeder Weiterleitungs-Host aus der Link-Registry muss offengelegt sein.
        import re
        registry = read("scripts/check24_links.yaml")
        policy = read("content/datenschutz/index.md")
        hosts = set(re.findall(r"https?://([a-z0-9.-]+)/", registry))
        self.assertTrue(hosts, "keine Hosts in der Registry gefunden")
        fehlend = sorted(h for h in hosts if h not in policy)
        self.assertEqual(fehlend, [], "Partner-Host nicht in der Datenschutzerklärung")

    def test_klickzaehler_beschreibung_und_cdn_aussage(self):
        # Der Beacon steht in den /go/-Seiten; die Erklärung muss ihn beschreiben.
        policy = read("content/datenschutz/index.md")
        self.assertIn("stats.franksfinanzcheck.de", policy)
        self.assertIn("keine IP-Adresse", policy)
        self.assertIn("13 Monate", policy)
        # Die Website liegt nach der DNS-Prüfung vom 11.10.2026 auf GitHub Pages ohne Cloudflare-Proxy.
        self.assertNotIn("Cloudflare-CDN", policy)

    def test_kein_umami_loader_und_altcookies_werden_geloescht(self):
        loader = read("layouts/_partials/deferred_scripts.html")
        self.assertNotIn("cloud.umami.is", loader)
        self.assertNotIn("ffConsentChange", loader)
        footer = read("layouts/_partials/extend_footer.html")
        self.assertIn("max-age=0", footer)
        self.assertIn("ff_analytics_consent_v2=;max-age=0", footer)
        self.assertIn("ff_cookie_consent=;max-age=0", footer)

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
