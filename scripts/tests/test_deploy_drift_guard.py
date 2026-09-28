#!/usr/bin/env python3
"""Vertragstests für scripts/deploy_drift_guard.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import deploy_drift_guard as ddg


class DeployDriftGuardTestCase(unittest.TestCase):
    def test_selftest_passes(self):
        failures = ddg.run_selftest()
        self.assertEqual(failures, [], f"Selftest fehlerhaft: {failures}")

    def test_commit_sha_parsing(self):
        self.assertEqual(
            ddg.parse_deployed_sha("deploy: abcdef0123456789abcdef0123456789abcdef01"),
            "abcdef0123456789abcdef0123456789abcdef01",
        )
        self.assertEqual(
            ddg.parse_deployed_sha("Deploy: ABCDEF0123456789ABCDEF0123456789ABCDEF01\nSome description"),
            "abcdef0123456789abcdef0123456789abcdef01",
        )
        self.assertIsNone(ddg.parse_deployed_sha("feat: update feature"))
        self.assertIsNone(ddg.parse_deployed_sha(""))
        self.assertIsNone(ddg.parse_deployed_sha(None))

    def test_relevance_classification(self):
        self.assertTrue(ddg.is_site_relevant("content/posts/test.md"))
        self.assertTrue(ddg.is_site_relevant("layouts/partials/header.html"))
        self.assertTrue(ddg.is_site_relevant("assets/css/style.css"))
        self.assertTrue(ddg.is_site_relevant("data/themenwelten.json"))
        self.assertTrue(ddg.is_site_relevant("hugo.toml"))

        self.assertFalse(ddg.is_site_relevant(".github/workflows/deploy.yml"))
        self.assertFalse(ddg.is_site_relevant("docs/ANLEITUNG.md"))
        self.assertFalse(ddg.is_site_relevant("scripts/deploy_drift_guard.py"))
        self.assertFalse(ddg.is_site_relevant("data/alert_router_state.json"))
        self.assertFalse(ddg.is_site_relevant(".affiliate_integrity_state.json"))
        self.assertFalse(ddg.is_site_relevant("data/revenue_funnel.json"))

    def test_drift_states(self):
        sha1 = "1111111111111111111111111111111111111111"
        sha2 = "2222222222222222222222222222222222222222"

        # 1. In Sync
        res_sync = ddg.analyze_drift(sha1, sha1, [], auto_detect=False)
        self.assertEqual(res_sync["status"], "IN_SYNC")
        self.assertFalse(res_sync["needs_deploy"])
        self.assertFalse(res_sync["is_drift"])

        # 2. State-Only Diff
        res_state = ddg.analyze_drift(
            sha1, sha2, ["docs/TEST.md", "data/integrity_history.jsonl"], auto_detect=False
        )
        self.assertEqual(res_state["status"], "STATE_ONLY_DIFF")
        self.assertFalse(res_state["needs_deploy"])
        self.assertFalse(res_state["is_drift"])

        # 3. Site-Drift
        res_drift = ddg.analyze_drift(
            sha1,
            sha2,
            ["docs/TEST.md", "content/posts/artikel/index.md"],
            auto_detect=False,
        )
        self.assertEqual(res_drift["status"], "SITE_DRIFT")
        self.assertTrue(res_drift["needs_deploy"])
        self.assertTrue(res_drift["is_drift"])
        self.assertEqual(res_drift["relevant_files"], ["content/posts/artikel/index.md"])

        # 4. Unknown base
        res_unk = ddg.analyze_drift(None, sha1, [], auto_detect=False)
        self.assertEqual(res_unk["status"], "UNKNOWN_BASE")
        self.assertTrue(res_unk["needs_deploy"])
        self.assertTrue(res_unk["is_drift"])

    def test_markdown_report_generation(self):
        sha1 = "1111111111111111111111111111111111111111"
        sha2 = "2222222222222222222222222222222222222222"
        res = ddg.analyze_drift(
            sha1, sha2, ["content/posts/neuer-beitrag/index.md", "docs/test.md"], auto_detect=False
        )
        rep = ddg.generate_markdown_report(res)
        self.assertIn("DEPLOY-DRIFT-BERICHT", rep)
        self.assertIn("SITE_DRIFT", rep)
        self.assertIn("content/posts/neuer-beitrag/index.md", rep)


if __name__ == "__main__":
    unittest.main()
