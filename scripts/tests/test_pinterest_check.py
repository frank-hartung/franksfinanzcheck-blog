"""Regression tests for Pinterest check P11 affiliate-link density."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pinterest_check as pc


class PinterestAffiliateDensityTests(unittest.TestCase):
    def check_article(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            post = Path(tmp) / "content" / "posts" / "sample" / "index.md"
            post.parent.mkdir(parents=True)
            post.write_text(content, encoding="utf-8")
            with patch.object(pc, "BLOG_DIR", tmp):
                pc.PROBLEMS.clear()
                pc._check_affiliate_density()
                return list(pc.PROBLEMS)

    def test_five_affiliate_links_are_within_limit(self):
        content = " ".join("[Vergleich](/go/strom/)" for _ in range(5))
        self.assertEqual(self.check_article(content), [])

    def test_six_mixed_affiliate_links_report_p11(self):
        content = " ".join(
            ["[Strom](/go/strom/)"] * 4
            + ["[Tarif](https://a.check24.net/click)"]
            + ["[Police](https://a.partner-versicherung.de/click)"]
        )
        self.assertEqual(
            self.check_article(content),
            [("P11", "sample", "6 Affiliate-Links (> 5 – Profi-Limit)")],
        )


class PinterestReportProvenanceTests(unittest.TestCase):
    def test_source_fingerprint_changes_when_checked_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            post = root / "content" / "posts" / "sample" / "index.md"
            post.parent.mkdir(parents=True)
            post.write_text("---\ntitle: Eins\n---\nText\n", encoding="utf-8")
            with patch.object(pc, "BLOG_DIR", tmp):
                first = pc.source_fingerprint()
                post.write_text("---\ntitle: Zwei\n---\nText\n", encoding="utf-8")
                second = pc.source_fingerprint()
            self.assertRegex(first, r"^[0-9a-f]{64}$")
            self.assertNotEqual(first, second)

    def test_old_report_without_fingerprint_is_not_current(self):
        self.assertIsNone(pc.report_source_fingerprint("# 📌 PINTEREST-REPORT\nProbleme: 0\n"))
        fingerprint = "a" * 64
        self.assertEqual(
            pc.report_source_fingerprint(f"**Quellfingerabdruck:** `{fingerprint}`"),
            fingerprint,
        )


if __name__ == "__main__":
    unittest.main()
