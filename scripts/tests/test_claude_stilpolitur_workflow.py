#!/usr/bin/env python3
"""Vertragsprüfungen für den ausfallsicheren Stilpolitur-Workflow (#468)."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "claude-stilpolitur.yml"


class ClaudeStilpoliturWorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_missing_external_token_is_graceful_degradation(self):
        """Ein fehlender Fremdzugang darf die Offline-Redaktion nicht stoppen."""
        preflight = self.workflow.split(
            "- name: Voraussetzungen prüfen", 1
        )[1].split("- name: Python-Abhängigkeiten", 1)[0]

        self.assertIn('echo "puter_available=false" >> "$GITHUB_OUTPUT"', preflight)
        self.assertIn("::warning title=Claude-Zugang nicht konfiguriert", preflight)
        self.assertNotIn("PUTER_AUTH_TOKEN fehlt::", preflight)
        self.assertNotRegex(
            preflight,
            re.compile(r"PUTER_AUTH_TOKEN[^\n]*\n(?:.*\n){0,8}\s*exit 1"),
        )

    def test_claude_and_sdk_are_only_used_with_token(self):
        guard = "if: steps.preflight.outputs.puter_available == 'true'"
        self.assertGreaterEqual(self.workflow.count(guard), 2)
        self.assertIn("@heyputer/puter.js@2.6.3", self.workflow)
        self.assertIn("python3 scripts/claude_stilpolitur.py --fix", self.workflow)

    def test_offline_polish_and_commit_are_unconditional(self):
        offline = self.workflow.split(
            "- name: Offline-Optimierung", 1
        )[1].split("- name: Claude (", 1)[0]
        commit = self.workflow.split(
            "- name: Änderungen committen & pushen", 1
        )[1]

        self.assertNotIn("\n        if:", offline)
        self.assertIn("grammar_check.py --fix", offline)
        self.assertIn("sprachglatt.py --fix", offline)
        self.assertNotIn("\n        if:", commit)
        self.assertIn("scripts/git_sync.sh --push-only", commit)

    def test_no_paid_or_alternate_model_fallback(self):
        self.assertIn("NUR claude-sonnet-5", self.workflow)
        self.assertNotIn("ANTHROPIC_API_KEY", self.workflow)
        self.assertNotIn("GEMINI_API_KEY", self.workflow)
        self.assertNotIn("GROQ_API_KEY", self.workflow)


if __name__ == "__main__":
    unittest.main()
