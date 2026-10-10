"""Regressionsschutz für den Lebenszyklus der Qualitäts-Gate-Issues (#701).

Ein grüner PR ist kein grüner Produktionsstand: nur main/master darf das
geteilte auto-report-Issue öffnen, aktualisieren oder schließen. Der PR-Check
selbst muss bei Fehlern weiter rot werden.
"""
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/link-check.yml"
MUTATING_STEPS = (
    "Label sicherstellen",
    "Funde melden (Issue pro Prüfer)",
    "Gate-Fehlschlag melden (Selbsttests, Vertrag oder Build)",
    "Meldung schließen (alles grün)",
)


class ReportingScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # BaseLoader bewahrt den YAML-Key `on` auch unter PyYAML 1.1 als Text.
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        cls.job = workflow["jobs"]["gate"]
        cls.steps = {s["name"]: s for s in cls.job["steps"]}

    def test_produktionszweig_und_ereignis_beide_erforderlich(self):
        guard = self.job["env"]["REPORT_PRODUCTION"]
        for term in ("github.event_name == 'push'", "github.event_name == 'schedule'",
                     "github.event_name == 'workflow_dispatch'",
                     "github.ref == 'refs/heads/main'",
                     "github.ref == 'refs/heads/master'"):
            self.assertIn(term, guard)
        self.assertNotIn("github.event_name == 'pull_request'", guard)
        self.assertIn("&&", guard, "Ereignis UND Produktionszweig sind nötig")

    def test_jede_issue_mutation_ist_auf_produktionslauf_begrenzt(self):
        for name in MUTATING_STEPS:
            with self.subTest(name=name):
                self.assertIn("env.REPORT_PRODUCTION == 'true'", self.steps[name]["if"])
        self.assertIn("failure()", self.steps[MUTATING_STEPS[2]]["if"])
        self.assertIn("success()", self.steps[MUTATING_STEPS[3]]["if"])

    def test_pr_bleibt_ein_harter_check(self):
        self.assertIn("pull_request", WORKFLOW.read_text(encoding="utf-8"))
        for name in ("Governance-Selbsttests (alle Wachen – entdeckt, uhrfest, schreibfrei)",
                     "Governance-Vertrag C1–C18 (Reihenfolge, Issue-Policy, Nachweise, Token-Lebenszyklus, Pflicht-Check)",
                     "Seite bauen", "Gate-Status (rot bei kaputten Links oder Schema-Funden)"):
            with self.subTest(name=name):
                self.assertNotIn("REPORT_PRODUCTION", self.steps[name].get("if", ""))
        self.assertNotIn("continue-on-error", self.steps[
            "Governance-Selbsttests (alle Wachen – entdeckt, uhrfest, schreibfrei)"])


if __name__ == "__main__":
    unittest.main()
