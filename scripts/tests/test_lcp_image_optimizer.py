"""Regressionsschutz für echte Bild-LCP-Kandidaten (kein Listen-Preload)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lcp_image_optimizer as optimierer  # noqa: E402


class LcpImagePolicy(unittest.TestCase):
    def test_manifest_nur_sichtbare_einzelartikel(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp)
            for slug, prefix, cover_option in (
                ("live", "", ""),
                ("verborgen", "", "  hiddenInSingle: true\n"),
                ("ohne-preload", "", "  preload: false\n"),
                ("entwurf", "draft: true\n", ""),
            ):
                datei = posts / slug / "index.md"
                datei.parent.mkdir(parents=True)
                datei.write_text(
                    "---\n" + prefix + "cover:\n  image: images/covers/beispiel.jpg\n"
                    + cover_option + "---\nText\n", encoding="utf-8",
                )
            with patch.object(optimierer, "CONTENT_POSTS", posts):
                manifest = optimierer.build_manifest()
        self.assertEqual(list(manifest["pages"]), ["/posts/live/"])
        self.assertNotIn("/", manifest["pages"])
        self.assertNotIn("/posts/", manifest["pages"])
        self.assertEqual(manifest["pages"]["/posts/live/"]["loading"], "eager")

    def test_eingechecktes_manifest_entspricht_quelle(self):
        gespeichert = json.loads(optimierer.MANIFEST.read_text(encoding="utf-8"))
        erwartet = optimierer.build_manifest()
        self.assertEqual(gespeichert["pages"], erwartet["pages"])
        self.assertTrue(gespeichert["pages"], "ohne Artikel wäre der Check bedeutungslos")
        self.assertFalse(any(p in gespeichert["pages"] for p in ("/", "/posts/")))

    def test_alte_listeneintraege_fallen_auf(self):
        manifest = optimierer.build_manifest()
        manifest["pages"]["/"] = {"image": "images/covers/beispiel.jpg"}
        funde = optimierer.check_manifest(manifest)
        self.assertTrue(any("Listen-Preloads" in f for f in funde), funde)


if __name__ == "__main__":
    unittest.main()
