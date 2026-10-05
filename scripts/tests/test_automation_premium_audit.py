"""Regressionstests für den statischen GitHub-Actions-Audit.

Insbesondere darf der dependency-freie Fallback einen fehlenden
`permissions:`-Block nicht als vorhanden melden. Genau diese Scheinsicherheit
ließ die OpenSSF-Scorecard-Fundklasse „Workflow does not contain permissions"
bis zum externen Scan durch.
"""
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
