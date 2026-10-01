"""Verdrahtungs-Vertrag: #490 darf nicht wieder nur im Quartalslauf leben."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOG_HEALTH = ROOT / ".github" / "workflows" / "blog-health-daily.yml"
QUARTERLY = ROOT / ".github" / "workflows" / "update-quarterly.yml"


class UniquenessWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daily = BLOG_HEALTH.read_text(encoding="utf-8")
        cls.quarterly = QUARTERLY.read_text(encoding="utf-8")

    def _assert_audit_lifecycle(self, workflow: str, report_path: str):
        self.assertIn("id: uniqueness", workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("python3 scripts/check_uniqueness.py | tee " + report_path, workflow)
        self.assertIn('echo "exit_code=$code" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("Audit-Sabotage-Schutz erzwingen", workflow)
        self.assertIn("steps.uniqueness.outputs.exit_code != '1'", workflow)
        self.assertIn("uniqueness_issue_sync.py --status critical --report " + report_path, workflow)
        self.assertIn("uniqueness_issue_sync.py --status clean", workflow)
        self.assertIn("UNIQUE_PRODUCTION_REF", workflow)
        self.assertIn("github.ref == format('refs/heads/{0}', github.event.repository.default_branch)", workflow)

    def test_daily_health_is_the_actual_not_just_documented_main_watch(self):
        self._assert_audit_lifecycle(self.daily, "/tmp/uniqueness_audit.txt")
        self.assertRegex(self.daily, r"(?m)^\s+issues:\s+write\s*$")
        # Exit 1 may not be turned into a harmless `|| echo` inside the step.
        audit_step = self.daily.split("- name: Einzigartigkeits-Audit", 1)[1].split(
            "- name: Audit-Sabotage-Schutz", 1
        )[0]
        self.assertNotIn("||", audit_step)

    def test_quarterly_second_measurement_uses_the_same_issue_lifecycle(self):
        self._assert_audit_lifecycle(self.quarterly, "/tmp/update_uniqueness.txt")
        self.assertNotIn("Issue bei Bestandsüberlappungen erstellen", self.quarterly,
                         "der alte, separate Issue-Pfad würde Lifecycle-Drift erzeugen")

    def test_workflows_keep_the_exact_issue_title_in_the_shared_script_only(self):
        # Die Workflows dürfen keine zweite Titel-SSOT einführen. Der eindeutige
        # Titel liegt in scripts/uniqueness_issue_sync.py.
        title = "Einzigartigkeits-Audit: Bestandsüberlappungen gefunden"
        self.assertNotIn(title, self.daily)
        self.assertNotIn(title, self.quarterly)
        script = (ROOT / "scripts" / "uniqueness_issue_sync.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(re.escape(title), script)), 1)


if __name__ == "__main__":
    unittest.main()
