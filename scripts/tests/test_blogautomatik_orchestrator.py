#!/usr/bin/env python3
"""test_blogautomatik_orchestrator.py — Unit-Tests für den Master-Orchestrator."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import blogautomatik_orchestrator


class TestBlogautomatikOrchestrator(unittest.TestCase):
    def test_get_system_status(self) -> None:
        status = blogautomatik_orchestrator.get_system_status()
        self.assertIn("timestamp", status)
        self.assertIn("overall_healthy", status)
        self.assertIn("whisper_lokal", status)
        self.assertIn("n8n_self_hosted", status)
        self.assertIn("github_pages", status)
        self.assertTrue(status["whisper_lokal"]["0_euro_kosten"])
        self.assertTrue(status["n8n_self_hosted"]["0_euro_kosten"])
        self.assertTrue(status["github_pages"]["0_euro_kosten"])

    def test_agency_cost_audit(self) -> None:
        audit = blogautomatik_orchestrator.run_agency_cost_audit()
        self.assertEqual(audit["monatliche_laufende_kosten"], 0.0)
        self.assertEqual(audit["ersparnis_prozent"], 100.0)
        self.assertGreater(audit["vergleich_monat_saas"], 200.0)
        self.assertGreater(audit["vergleich_jahr_saas"], 2400.0)
        self.assertIn("whisper_lokal", audit["eigene_komponenten"])
        self.assertIn("n8n_self_hosted", audit["eigene_komponenten"])

    def test_pipeline_dry_run(self) -> None:
        res = blogautomatik_orchestrator.run_pipeline("omnichannel-sync", dry_run=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["pipeline"], "omnichannel-sync")

    def test_unknown_pipeline(self) -> None:
        res = blogautomatik_orchestrator.run_pipeline("fantasy-pipeline")
        self.assertEqual(res["status"], "unknown_pipeline")


if __name__ == "__main__":
    unittest.main()
