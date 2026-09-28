#!/usr/bin/env python3
"""Vertragstests für .github/workflows/deploy-catchup.yml."""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEPLOY_CATCHUP_YML = ROOT / ".github" / "workflows" / "deploy-catchup.yml"
DEPLOY_YML = ROOT / ".github" / "workflows" / "deploy.yml"


class DeployCatchupWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.catchup_text = DEPLOY_CATCHUP_YML.read_text(encoding="utf-8")
        self.deploy_text = DEPLOY_YML.read_text(encoding="utf-8")

    def test_workflow_has_schedule_and_events(self):
        self.assertIn("workflow_dispatch:", self.catchup_text)
        self.assertIn("schedule:", self.catchup_text)
        self.assertIn("cron:", self.catchup_text)
        self.assertIn("workflow_run:", self.catchup_text)

    def test_catchup_queries_gh_pages_commit(self):
        """Catchup muss gh-pages Ref als SSOT für den Live-Stand abfragen (#433)."""
        self.assertIn("ref: 'gh-pages'", self.catchup_text)
        self.assertIn("match(/deploy:\\s*([0-9a-f]{40})/i)", self.catchup_text)

    def test_catchup_checks_deploy_job_conclusion(self):
        """Catchup darf nicht nur Workflow-Status success prüfen, sondern muss deploy-JOB prüfen."""
        self.assertIn("listJobsForWorkflowRun", self.catchup_text)
        self.assertIn("deployJob.conclusion === 'success'", self.catchup_text)

    def test_catchup_checks_in_flight_runs(self):
        """Catchup verhindert doppeltes Auslösen bei laufenden Deploys."""
        self.assertIn("in_progress", self.catchup_text)
        self.assertIn("queued", self.catchup_text)

    def test_catchup_compares_relevant_files(self):
        """Catchup filtert mit Compare-API gegen STATE_ONLY."""
        self.assertIn("compareCommits", self.catchup_text)
        self.assertIn("STATE_ONLY", self.catchup_text)

    def test_state_only_patterns_match_between_deploy_and_catchup(self):
        """STATE_ONLY in deploy.yml und deploy-catchup.yml müssen konsistent sein."""
        m_deploy = re.search(r"STATE_ONLY='([^']+)'", self.deploy_text)
        self.assertIsNotNone(m_deploy, "STATE_ONLY in deploy.yml nicht gefunden")
        pattern_deploy = m_deploy.group(1)

        m_catchup = re.search(r"STATE_ONLY_PATTERN = '([^']+)'", self.catchup_text)
        self.assertIsNotNone(m_catchup, "STATE_ONLY_PATTERN in deploy-catchup.yml nicht gefunden")
        pattern_catchup = m_catchup.group(1).replace(r"\\", "\\")

        self.assertEqual(
            pattern_deploy,
            pattern_catchup,
            "STATE_ONLY Muster in deploy.yml und deploy-catchup.yml weichen voneinander ab!",
        )


if __name__ == "__main__":
    unittest.main()
