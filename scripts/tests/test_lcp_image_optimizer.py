"""Regressionsschutz für echte Bild-LCP-Kandidaten (kein Listen-Preload)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
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

    def test_write_manifest_is_idempotent_for_unchanged_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "lcp_images.json"
            manifest = optimierer.build_manifest()
            with patch.object(optimierer, "MANIFEST", manifest_path):
                optimierer.write_manifest(manifest)
                first = manifest_path.read_bytes()
                optimierer.write_manifest(optimierer.build_manifest())
                self.assertEqual(manifest_path.read_bytes(), first)
                changed = optimierer.build_manifest()
                changed["pages"]["/posts/neu/"] = optimierer.image_rule(
                    "images/covers/neu.jpg", page_type="single", reason="Test",
                    sizes="100vw",
                )
                optimierer.write_manifest(changed)
                self.assertNotEqual(manifest_path.read_bytes(), first)
                self.assertIn("/posts/neu/", json.loads(manifest_path.read_text())["pages"])


class DeployWiringTest(unittest.TestCase):
    def test_deploy_refreshes_lcp_after_final_content_gates_and_before_rebuild(self):
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        ymyl = workflow.index("name: YMYL-Bestand – nur fachlich freigegebene Live-Artikel")
        lcp = workflow.index("name: LCP-Manifest aus finalem Live-Bestand erzeugen")
        gate_diff = workflow.index("name: Gate-Heilungsdiff merken (alle Gates, inkl. Publish-Gate)")
        rebuild = workflow.index("name: Rebuild nach Heilungen (nur wenn sich Content geändert hat)")
        upload = workflow.index("name: Artefakt für offizielles Pages-Deployment hochladen")
        self.assertLess(ymyl, lcp)
        self.assertLess(lcp, gate_diff)
        self.assertLess(lcp, rebuild)
        self.assertLess(lcp, upload)
        self.assertIn("python3 scripts/lcp_image_optimizer.py --fix", workflow[lcp:gate_diff])
        register = (ROOT / "data/blustradius-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("name: LCP-Manifest aus finalem Live-Bestand erzeugen", register)


if __name__ == "__main__":
    unittest.main()
