"""Regressionstests für den statischen GitHub-Actions-Audit.

Insbesondere darf der dependency-freie Fallback einen fehlenden
`permissions:`-Block nicht als vorhanden melden. Genau diese Scheinsicherheit
ließ die OpenSSF-Scorecard-Fundklasse „Workflow does not contain permissions"
bis zum externen Scan durch.
"""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts import automation_premium_audit as audit


MINIMAL = """name: Test
on:
  workflow_dispatch: {}
concurrency:
  group: test
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: true
"""


class AutomationPremiumAuditTests(TestCase):
    def audit_fallback(self, text: str) -> dict:
        # Unterhalb des Repos anlegen, weil audit_file bewusst einen relativen
        # Dateinamen für seinen Bericht erzeugt. TemporaryDirectory räumt auf.
        with TemporaryDirectory(dir=audit.ROOT) as folder:
            path = Path(folder) / "workflow.yml"
            path.write_text(text, encoding="utf-8")
            with patch.object(audit, "yaml", None):
                return audit.audit_file(path)

    def test_fallback_erkennt_fehlende_permissions(self):
        row = self.audit_fallback(MINIMAL)
        self.assertFalse(row["has_permissions"])
        self.assertEqual(
            [row["file"]],
            audit.build_report([row])["missing_permissions"])

    def test_fallback_erkennt_explizites_mapping(self):
        text = MINIMAL.replace(
            "concurrency:\n",
            "permissions:\n  contents: read\nconcurrency:\n")
        row = self.audit_fallback(text)
        self.assertTrue(row["has_permissions"])
        self.assertEqual([], audit.build_report([row])["missing_permissions"])

    def test_breite_permissions_kurzform_zaehlt_nicht(self):
        text = MINIMAL.replace(
            "concurrency:\n",
            "permissions: write-all\nconcurrency:\n")
        self.assertFalse(self.audit_fallback(text)["has_permissions"])

    def test_job_level_concurrency_ist_ein_gueltiger_vertrag(self):
        text = MINIMAL.replace(
            "concurrency:\n  group: test\njobs:",
            "jobs:").replace(
                "  test:\n    runs-on:",
                "  test:\n    concurrency:\n      group: per-job-${{ github.run_id }}\n"
                "      cancel-in-progress: false\n    runs-on:")
        with TemporaryDirectory(dir=audit.ROOT) as folder:
            path = Path(folder) / "workflow.yml"
            path.write_text(text, encoding="utf-8")
            with patch.object(audit, "yaml", audit.yaml):
                parsed_row = audit.audit_file(path)
            with patch.object(audit, "yaml", None):
                fallback_row = audit.audit_file(path)
        self.assertTrue(parsed_row["has_concurrency"])
        self.assertTrue(fallback_row["has_concurrency"])

    def test_unvollstaendige_concurrency_ist_kein_vertrag(self):
        self.assertFalse(audit.valid_concurrency({"group": "test"}))
        self.assertFalse(audit.valid_concurrency({"cancel-in-progress": False}))
        self.assertFalse(audit.valid_concurrency({"group": " ", "cancel-in-progress": False}))
        self.assertFalse(audit.valid_concurrency({"group": "test", "cancel-in-progress": "true-ish"}))
        self.assertTrue(audit.valid_concurrency({"group": "test", "cancel-in-progress": "${{ github.ref == 'refs/heads/main' }}"}))

    def test_continue_on_error_zaehlt_yaml_keys_statt_kommentare(self):
        text = MINIMAL.replace(
            "      - run: true",
            "      # continue-on-error: false (Kommentar)\n"
            "      - run: true\n        continue-on-error: false")
        parsed = audit.load if audit.yaml is not None else None
        if parsed is None:
            self.skipTest("PyYAML nicht installiert")
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(dir=audit.ROOT) as folder:
            path = Path(folder) / "workflow.yml"
            path.write_text(text, encoding="utf-8")
            row = audit.audit_file(path)
        self.assertEqual(1, row["continue_on_error_count"])
        self.assertEqual(2, row["continue_on_error_source_mentions"])

    def test_repository_workflows_inklusive_job_level_vertraegen(self):
        rows = [audit.audit_file(path)
                for path in sorted(audit.WORKFLOWS.glob("*.yml"))]
        report = audit.build_report(rows)
        self.assertEqual([], report["missing_concurrency"])
        auto_assign = next(row for row in rows
                           if row["file"].endswith("auto-assign-pr.yml"))
        self.assertTrue(auto_assign["has_concurrency"])

    def test_dependency_fallback_behauptet_keine_semantische_coe_abdeckung(self):
        text = MINIMAL.replace(
            "      - run: true",
            "      - run: false\n        continue-on-error: true")
        row = self.audit_fallback(text)
        self.assertEqual(1, row["continue_on_error_count"])
        self.assertEqual("unclassified",
                         row["continue_on_error_fallback_evidence"][0]["signal"])

    def test_continue_on_error_ohne_signal_wird_als_restpunkt_gemeldet(self):
        data = {"jobs": {"test": {"steps": [
            {"name": "silent", "continue-on-error": True, "run": "exit 1"},
            {"name": "later", "run": "echo done"},
        ]}}}
        evidence = audit.continue_on_error_evidence(data, "")
        self.assertEqual("unclassified", evidence[0]["signal"])
        data["jobs"]["test"]["steps"].append(
            {"name": "summary", "run": 'echo "failure" >> "$GITHUB_STEP_SUMMARY"'})
        evidence = audit.continue_on_error_evidence(data, "")
        self.assertEqual("downstream-report-marker", evidence[0]["signal"])

    def test_alle_repository_continue_on_error_schritte_besitzen_signal(self):
        rows = [audit.audit_file(path)
                for path in sorted(audit.WORKFLOWS.glob("*.yml"))]
        report = audit.build_report(rows)
        self.assertEqual(115, report["continue_on_error_total"])
        self.assertEqual([], report["continue_on_error_unclassified"])
        self.assertEqual(
            115, sum(report["continue_on_error_fallback_signal_counts"].values()))

    def test_prioritaeten_berichten_den_gemessenen_stand(self):
        row = {
            "file": ".github/workflows/example.yml", "name": "Example",
            "scheduled": False, "jobs": 1, "has_permissions": True,
            "has_concurrency": False, "missing_timeout_jobs": [],
            "floating_action_refs": [], "continue_on_error_count": 2,
            "continue_on_error_fallback_evidence": [
                {"job": "test", "step": "one", "signal": "in-step-diagnostic"},
                {"job": "test", "step": "two", "signal": "step-result-consumer"},
            ],
        }
        report = audit.build_report([row])
        output = StringIO()
        with redirect_stdout(output):
            audit.print_text(report)
        text = output.getvalue()
        self.assertIn("Drittanbieter-Actions sind auf Commit-SHAs gepinnt", text)
        self.assertIn("alle Jobs haben Timeouts", text)
        self.assertIn("Concurrency-Lücken der 1 betroffenen Workflows prüfen", text)
        self.assertIn("alle 2 continue-on-error-Schritte haben ein klassifiziertes Fallback-Signal", text)
        self.assertNotIn("kritische Drittanbieter-Actions auf Commit-SHAs pinnen", text)
