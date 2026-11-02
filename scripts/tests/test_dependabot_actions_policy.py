#!/usr/bin/env python3
"""Dependabot-/Auto-Merge-Vertrag für GitHub-Actions seit PR #1014.

Eine gemischte Gruppe machte jeden Patch-/Minor-Bump vom Major-Review
abhängig. Die Gruppen trennen jetzt Major von Patch/Minor; der Auto-Merge
bleibt auf Patch/Minor begrenzt und checkt keinen PR-Code aus.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import actions_version_guard as pin_wache  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@unittest.skipIf(yaml is None, "PyYAML nicht installiert")
class DependabotActionsPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
        cls.workflow = yaml.safe_load(
            (ROOT / ".github/workflows/dependabot-automerge.yml").read_text())

    def test_actions_groups_partition_semver_types(self):
        entry = next(u for u in self.config["updates"]
                     if u["package-ecosystem"] == "github-actions")
        groups = entry["groups"]
        self.assertEqual(set(groups), {"github-actions", "github-actions-major"})
        self.assertEqual(set(groups["github-actions"]["update-types"]), {"minor", "patch"})
        self.assertEqual(set(groups["github-actions-major"]["update-types"]), {"major"})
        for group in groups.values():
            self.assertEqual(group["patterns"], ["*"])

    def test_cooldown_and_composite_coverage_remain(self):
        entry = next(u for u in self.config["updates"]
                     if u["package-ecosystem"] == "github-actions")
        self.assertGreaterEqual(entry["cooldown"]["default-days"], 7)
        self.assertIn("/", entry["directories"])
        self.assertIn("/.github/actions/*", entry["directories"])

    def test_automerge_is_explicitly_patch_or_minor_only(self):
        steps = self.workflow["jobs"]["automerge"]["steps"]
        auto = next(s for s in steps if "gh pr merge --auto" in (s.get("run") or ""))
        condition = auto["if"]
        self.assertIn("steps.meta.outputs.package-ecosystem == 'github_actions'", condition)
        self.assertIn("version-update:semver-patch", condition)
        self.assertIn("version-update:semver-minor", condition)
        self.assertNotIn("!= 'version-update:semver-major'", condition,
                        "Unbekannte Semver-Stufen dürfen nicht automatisch mergen")
        manual = next(s for s in steps if "Manuelle Prüfung nötig" in (s.get("run") or ""))
        self.assertIn("!= 'version-update:semver-patch'", manual["if"])
        self.assertIn("!= 'version-update:semver-minor'", manual["if"])

    def test_pull_request_target_never_checks_out_pr_code(self):
        trigger = self.workflow.get("on", self.workflow.get(True))
        self.assertIn("pull_request_target", trigger)
        self.assertNotIn("pull_request", trigger)
        for step in self.workflow["jobs"]["automerge"]["steps"]:
            self.assertNotIn("actions/checkout", step.get("uses", ""))
        self.assertEqual(self.workflow["jobs"]["automerge"]["if"],
                         "github.event.pull_request.user.login == 'dependabot[bot]'")

    def test_metadata_action_is_sha_pinned(self):
        raw = (ROOT / ".github/workflows/dependabot-automerge.yml").read_text()
        uses = [u for u in pin_wache.parse_uses(raw)
                if u.action == "dependabot/fetch-metadata"]
        self.assertEqual(len(uses), 1)
        self.assertTrue(pin_wache.is_pin(uses[0].ref))
        self.assertIsNotNone(uses[0].version)


if __name__ == "__main__":
    unittest.main()
