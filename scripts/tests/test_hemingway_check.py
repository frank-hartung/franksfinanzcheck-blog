"""Vertragstests für den kostenlosen Hemingway-Editor-Begleiter."""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import hemingway_check as hc  # noqa: E402


class HemingwayAdapterTests(unittest.TestCase):
    def test_points_to_free_editor_and_has_no_network_client(self):
        self.assertEqual(hc.TOOL_NAME, "Hemingway Editor")
        self.assertEqual(hc.TOOL_URL, "https://hemingwayapp.com/")
        source = (ROOT / "scripts" / "hemingway_check.py").read_text(encoding="utf-8")
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("API_KEY", source)

    def test_selftest_is_forwarded_and_green(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = hc.main(["--selftest"])
        self.assertEqual(result, 0)
        self.assertIn("hemingway_check --selftest OK", output.getvalue())

    def test_cli_arguments_are_forwarded_without_editing_content(self):
        forwarded = []

        def fake_main():
            forwarded.extend(sys.argv[1:])
            print("Lesbarkeits-Audit: 0 Artikel")

        output = io.StringIO()
        with patch.object(hc._engine, "main", fake_main):
            with contextlib.redirect_stdout(output):
                result = hc.main(["--new-only"])

        self.assertEqual(result, 0)
        self.assertEqual(forwarded, ["--new-only"])
        self.assertIn("Hemingway-Lesbarkeitscheck", output.getvalue())


class HemingwayWorkflowTests(unittest.TestCase):
    def test_workflow_has_no_external_model_or_token(self):
        workflow = (ROOT / ".github" / "workflows" / "hemingway-check.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("name: Hemingway-Lesbarkeitscheck (Mo/Mi/Fr)", workflow)
        self.assertIn("scripts/hemingway_check.py --selftest", workflow)
        self.assertIn("scripts/hemingway_check.py \\", workflow)
        self.assertIn("--gate-bestand", workflow)
        self.assertIn("HEMINGWAY-REPORT.md", workflow)
        self.assertNotIn("PUTER_AUTH_TOKEN", workflow)
        self.assertNotIn("@heyputer", workflow)
        self.assertNotIn("Claude", workflow)

    def test_old_lane_is_gone(self):
        legacy_slug = "claude" + "-stilpolitur"
        legacy_module = "claude" + "_stilpolitur"
        for path in (
            ROOT / ".github" / "workflows" / f"{legacy_slug}.yml",
            ROOT / "scripts" / f"{legacy_module}.py",
            ROOT / "scripts" / f"{legacy_module}_wirkung.py",
            ROOT / "docs" / f"ANLEITUNG-{legacy_slug.upper()}.md",
        ):
            self.assertFalse(path.exists(), f"alte Lane noch vorhanden: {path}")


if __name__ == "__main__":
    unittest.main()
