import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import post_utils  # noqa: E402
import sprachkern  # noqa: E402


class EditorialScopeTest(unittest.TestCase):
    def rels(self, scope):
        return {post_utils.content_key(p) for p in post_utils.list_content_paths(scope)}

    def test_editorial_contains_posts_guides_and_newsletter(self):
        paths = self.rels("editorial")
        self.assertTrue(any(p.startswith("content/posts/") for p in paths))
        self.assertTrue(any(p.startswith("content/pillar/") for p in paths))
        self.assertIn("content/newsletter/index.md", paths)
        self.assertIn("content/methodik/index.md", paths)
        self.assertIn("content/ueber/index.md", paths)

    def test_legal_and_transactional_pages_are_excluded(self):
        paths = self.rels("editorial")
        forbidden = {
            "content/datenschutz/index.md",
            "content/impressum/index.md",
            "content/newsletter-abmelden/index.md",
            "content/newsletter-bestaetigung/index.md",
            "content/newsletter-praeferenzen/index.md",
        }
        self.assertFalse(paths & forbidden)

    def test_loaded_items_have_collision_free_keys_and_kinds(self):
        items = sprachkern.load_articles(scope="editorial", include_drafts=True)
        keys = [item["key"] for item in items]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(any(item["kind"] == "Newsletter-Landingpage" for item in items))
        self.assertTrue(any(item["kind"] == "Ratgeberseite" for item in items))

    def test_invalid_scope_fails_closed(self):
        with self.assertRaises(ValueError):
            post_utils.list_content_paths("everything")


if __name__ == "__main__":
    unittest.main()
