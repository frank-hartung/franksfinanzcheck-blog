import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.check_covers as covers


class CoverSourceSlugTests(unittest.TestCase):
    def test_bundle_and_flat_content_slugs(self):
        self.assertEqual(
            covers.content_slug("/repo/content/posts/mein-artikel/index.md"),
            "mein-artikel",
        )
        self.assertEqual(
            covers.content_slug("/repo/content/posts/mein-artikel.md"),
            "mein-artikel",
        )

    def test_stale_finding_keeps_source_and_image_slug_separate(self):
        """Regression: Ein umdatierter Artikel darf ein altes Cover referenzieren.

        Der Generator filtert nach dem Content-Slug. Ohne source_slug rief die
        Selbstheilung den Bild-Slug auf, fand keinen Artikel und blieb rot.
        """
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            data.mkdir()
            (data / "covers_manifest.json").write_text(
                json.dumps({"altes-bild": {"title": "Alter Titel"}}),
                encoding="utf-8",
            )
            item = {
                "file": os.path.join(td, "content", "posts", "neuer-artikel", "index.md"),
                "image": "images/covers/altes-bild.jpg",
                "title": "Neuer Titel",
                "source_slug": "neuer-artikel",
            }
            with mock.patch.object(covers, "BLOG_DIR", td):
                found = covers.check_stale([item])

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["slug"], "altes-bild")
        self.assertEqual(found[0]["source_slug"], "neuer-artikel")
        self.assertEqual(found[0]["image"], "images/covers/altes-bild.jpg")


if __name__ == "__main__":
    unittest.main()
