"""Regressionstests für verschachtelte Markdown-Links."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import internal_linker


class MarkdownLinkSafetyTests(unittest.TestCase):
    def test_existing_nested_link_is_fully_blocked(self):
        body = "Wer **[[Heizkoste](../../posts/heizkosten/)n senken](../../posts/preisgarantie/)** will."
        self.assertIsNone(internal_linker.find_anchor(body, "Heizkosten"))
        self.assertIsNone(internal_linker.find_anchor(body, "n senken"))

    def test_plain_anchor_remains_linkable(self):
        body = "Wer Heizkosten senken will, spart Geld."
        self.assertIsNotNone(internal_linker.find_anchor(body, "Heizkosten senken"))

if __name__ == "__main__":
    unittest.main()
