"""Regressionen für den Ein-H1-Vertrag und seine Publish-Gate-Verdrahtung.

Anlass #492 (01.10.2026): Der neueste Live-Artikel enthielt zusätzlich zum
vom Layout gerenderten Titel ein Markdown-H1. Playwright sah korrekt zwei H1,
der vorhandene SEO-Audit zählte das Body-H1 zwar, wertete es aber nicht – und
sein Ergebnis nutzte ``<slug>.md``, während das Publish-Gate nackte Slugs
verglich. Beide Lücken werden hier unabhängig voneinander eingefroren.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_gate as pg  # noqa: E402
import seo_audit as seo  # noqa: E402


def post(body: str, slug: str = "beispiel") -> dict:
    return {
        "file": f"{slug}.md",
        "path": str(ROOT / "content" / "posts" / slug / "index.md"),
        "slug": slug,
        "title": "Ein ausreichend langer Titel für den SEO-Test",
        "description": (
            "Eine ausreichend lange Meta-Beschreibung für den isolierten "
            "SEO-Strukturtest ohne unerwünschte Nebentreffer."
        ),
        "keywords": "SEO-Test",
        "cover": "images/covers/beispiel.jpg",
        "draft": False,
        "body": body,
    }


class EinH1VertragTests(unittest.TestCase):
    def test_markdown_h1_im_body_ist_harter_fund(self):
        body = "# Zweites H1\n\n## Abschnitt A\n\n## Abschnitt B\n\n" + ("Wort " * 320)
        result = seo.audit_post(post(body))
        self.assertEqual(1, result["h1_body"])
        self.assertTrue(
            any("Markdown-H1" in issue for issue in result["issues"]),
            result,
        )
        self.assertGreater(result["score_issues"], 0)

    def test_h2_struktur_bleibt_erlaubt(self):
        body = "## Abschnitt A\n\n## Abschnitt B\n\n" + ("Wort " * 320)
        result = seo.audit_post(post(body))
        self.assertEqual(0, result["h1_body"])
        self.assertFalse(any("Markdown-H1" in issue for issue in result["issues"]))

    def test_live_bestand_hat_keine_zusaetzlichen_body_h1(self):
        funde = []
        for article in seo.load_posts():
            if article["draft"]:
                continue
            result = seo.audit_post(article)
            if result["h1_body"]:
                funde.append(f"{article['slug']}: {result['h1_body']}")
        self.assertEqual([], funde)


class PublishGateSlugTests(unittest.TestCase):
    def test_neue_slug_ausgabe_blockiert_den_richtigen_kandidaten(self):
        payload = {
            "details": [
                {"slug": "artikel-a", "file": "artikel-a.md", "score_issues": 1},
                {"slug": "artikel-b", "file": "artikel-b.md", "score_issues": 0},
            ],
            "sitemap_issues": [],
        }
        with patch.object(pg, "_run_json", return_value=payload):
            failed, warning = pg.seo_audit_failures()
        self.assertEqual({"artikel-a"}, failed)
        self.assertIsNone(warning)

    def test_legacy_dateiname_wird_ohne_md_normalisiert(self):
        payload = {
            "details": [{"file": "legacy-artikel.md", "score_issues": 1}],
            "sitemap_issues": [],
        }
        with patch.object(pg, "_run_json", return_value=payload):
            failed, _ = pg.seo_audit_failures()
        self.assertEqual({"legacy-artikel"}, failed)


if __name__ == "__main__":
    unittest.main()
