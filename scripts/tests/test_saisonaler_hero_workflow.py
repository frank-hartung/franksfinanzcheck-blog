"""Veröffentlichungs- und Alerting-Vertrag des Saison-Hero-Workflows.

Die Commit-Stufe wird in Wegwerf-Repositories mit echten Git-Kommandos
geprobt. Kein Test pusht, ändert das Arbeits-Repository oder ruft APIs auf.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/saisonaler-hero-refresh.yml"


def load_workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def step(workflow: dict, name: str) -> dict:
    return next(s for s in workflow["jobs"]["refresh"]["steps"] if s.get("id") == name)


class HeroWorkflowVertrag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_workflow(WORKFLOW)

    def test_render_proof_and_rollback_are_ordered_before_publication(self):
        steps = self.workflow["jobs"]["refresh"]["steps"]
        ids = [s.get("id") for s in steps]
        self.assertLess(ids.index("politur"), ids.index("render"))
        self.assertLess(ids.index("render"), ids.index("render_gates"))
        self.assertLess(ids.index("render_gates"), ids.index("rollback"))
        self.assertLess(ids.index("rollback"), ids.index("commit"))
        rollback = step(self.workflow, "rollback")
        self.assertIn("always()", rollback["if"])
        self.assertIn("steps.render.conclusion != 'success'", rollback["if"])
        self.assertIn("steps.render_gates.conclusion != 'success'", rollback["if"])
        self.assertLess(rollback["run"].index("git restore"),
                        rollback["run"].index("--record-render-failure"))

    def test_contract_tests_run_before_model_calls(self):
        checks = step(self.workflow, "checks")["run"]
        self.assertIn("scripts.tests.test_saisonaler_hero_refresh", checks)
        self.assertIn("scripts.tests.test_llm_client_transport", checks)
        self.assertIn("scripts.tests.test_saisonaler_hero_workflow", checks)

    def test_alerts_and_closure_are_default_branch_only(self):
        steps = self.workflow["jobs"]["refresh"]["steps"]
        alert = next(s for s in steps if s.get("name", "").startswith("Ausfall sichtbar"))
        close = next(s for s in steps if s.get("name", "").startswith("Behobene Störung"))
        self.assertIn("failure()", alert["if"])
        self.assertNotIn("steps.politur.conclusion != 'skipped'", alert["if"])
        for entry in (alert, close):
            self.assertIn("github.ref_type == 'branch'", entry["if"])
            self.assertIn("github.ref_name == github.event.repository.default_branch", entry["if"])
        self.assertIn("success()", close["if"])
        self.assertIn("steps.politur.outputs.ampel == 'gruen'", close["if"])
        self.assertIn("RESEARCH_RESULT", alert["env"])
        self.assertIn("RENDER_RESULT", alert["env"])

    def test_alerting_and_deploy_catchup_follow_actual_workflow_name(self):
        name = self.workflow["name"]
        for filename in ("alert-on-failure.yml", "deploy-catchup.yml"):
            watched = load_workflow(ROOT / ".github/workflows" / filename)
            triggers = watched.get("on", watched.get(True))
            with self.subTest(workflow=filename):
                self.assertIn(name, triggers["workflow_run"]["workflows"])
                self.assertIn("completed", triggers["workflow_run"]["types"])


class HeroCommitStufe(unittest.TestCase):
    @staticmethod
    def git(root: Path, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, text=True,
                                capture_output=True, check=True)
        return result.stdout.strip()

    def build_fixture(self, root: Path) -> None:
        for directory in ("data/research/saisonal", "scripts"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        files = {
            "data/saisons.yaml": "alter geprüfter Hero\n",
            "data/saisonaler_hero_state.json": "alter Nachweis\n",
            "data/saisonaler_hero_history.jsonl": "alte Historie\n",
            "data/research/saisonal/alt.md": "alte Recherche\n",
            "scripts/git_sync.sh": "#!/bin/sh\nexit 0\n",
        }
        for name, value in files.items():
            (root / name).write_text(value, encoding="utf-8")
        (root / "scripts/git_sync.sh").chmod(0o755)
        self.git(root, "init", "--quiet")
        self.git(root, "config", "user.name", "Test")
        self.git(root, "config", "user.email", "test@example.invalid")
        self.git(root, "config", "commit.gpgsign", "false")
        self.git(root, "add", ".")
        self.git(root, "commit", "--quiet", "-m", "Basis")
        (root / "data/saisons.yaml").write_text("Kandidat\n", encoding="utf-8")
        (root / "data/saisonaler_hero_state.json").write_text("neuer State\n", encoding="utf-8")
        (root / "data/saisonaler_hero_history.jsonl").write_text("neue Historie\n", encoding="utf-8")
        (root / "data/research/saisonal/neu.md").write_text("neue Recherche\n", encoding="utf-8")

    def test_realer_rollback_und_commit_nach_renderfehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_fixture(root)
            for name in ("saisonaler_hero_refresh.py", "llm_client.py", "groq_config.py"):
                shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
            saisons = ("saisons:\n  - id: test\n    name: Test\n"
                       "    ab: '01-01'\n    bis: '12-31'\n"
                       "    hero_title: 'Alter Titel'\n    hero_lead: 'Alter Lead'\n")
            initial = {"version": 1, "saisons": {"test": {
                "updated": "2026-10-01T00:00:00Z", "fingerprint": "alt", "fehler_serie": 5}}}
            (root / "data/saisons.yaml").write_text(saisons, encoding="utf-8")
            (root / "data/saisonaler_hero_state.json").write_text(json.dumps(initial), encoding="utf-8")
            (root / "data/saisonaler_hero_history.jsonl").write_text("alte Historie\n", encoding="utf-8")
            self.git(root, "add", "data", "scripts")
            self.git(root, "commit", "--quiet", "-m", "Ausgangsstand")

            (root / "data/saisons.yaml").write_text(saisons.replace("Alter Titel", "Kandidat"), encoding="utf-8")
            (root / "data/saisonaler_hero_state.json").write_text(
                json.dumps({"saisons": {"test": {"fingerprint": "ungeprueft"}}}), encoding="utf-8")
            (root / "data/saisonaler_hero_history.jsonl").write_text("Kandidat\n", encoding="utf-8")
            (root / "SAISONALER-HERO-REPORT.md").write_text("# Vorläufig grün\n", encoding="utf-8")
            (root / "data/research/saisonal/neu.md").write_text("Recherche\n", encoding="utf-8")
            env = os.environ.copy()
            env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
            env.update({"RENDER_RESULT": "failure", "GATES_RESULT": "skipped"})
            rollback = step(load_workflow(WORKFLOW), "rollback")["run"]
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", rollback],
                                    cwd=root, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual((root / "data/saisons.yaml").read_text(encoding="utf-8"), saisons)
            self.assertEqual((root / "data/saisonaler_hero_history.jsonl").read_text(encoding="utf-8"), "alte Historie\n")
            restored = json.loads((root / "data/saisonaler_hero_state.json").read_text(encoding="utf-8"))
            record = restored["saisons"]["test"]
            self.assertEqual(record["fingerprint"], "alt")
            self.assertEqual(record["fehler_serie"], 6)
            self.assertEqual(record["letzter_fehler"]["code"], "render-nachweis-fehlgeschlagen")
            report = (root / "SAISONALER-HERO-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("Zustand:** rot", report)
            self.assertIn("Zwischenstand vor Rücknahme (nicht freigegeben)", report)

            env.update({"POLITUR_RESULT": "success", "POLITUR_AMPEL": "gruen",
                        "POLITUR_ZUSTAND": "grün", "ROLLBACK_RESULT": "success"})
            commit = step(load_workflow(WORKFLOW), "commit")["run"]
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", commit],
                                    cwd=root, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            committed = set(self.git(root, "show", "--format=", "--name-only", "HEAD").splitlines())
            self.assertEqual(committed, {"data/saisonaler_hero_state.json", "data/research/saisonal/neu.md"})
            saved = json.loads(self.git(root, "show", "HEAD:data/saisonaler_hero_state.json"))
            self.assertEqual(saved["saisons"]["test"]["fingerprint"], "alt")
            self.assertEqual(saved["saisons"]["test"]["fehler_serie"], 6)

    def test_commit_matrix_prevents_unverified_content_and_success_fingerprints(self):
        candidate = "data/saisons.yaml"
        state = "data/saisonaler_hero_state.json"
        history = "data/saisonaler_hero_history.jsonl"
        research = "data/research/saisonal/neu.md"
        cases = [
            ("alle Gates grün", "success", "gruen", "grün", "success", "success", "skipped",
             {candidate, state, history, research}),
            ("politur rot", "failure", "rot", "rot – Textkette", "skipped", "skipped", "skipped",
             {state, research}),
            ("gelb trotz Render-Beweis", "success", "gelb", "gelb", "success", "success", "skipped",
             {state, research}),
            ("Ampel fehlt trotz Render-Beweis", "success", "", "", "success", "success", "skipped",
             {research}),
            ("Build rot, Rücknahme belegt", "success", "gruen", "grün", "failure", "skipped", "success",
             {state, research}),
            ("Render-Gate rot, Rücknahme belegt", "success", "gruen", "grün", "success", "failure", "success",
             {state, research}),
            ("Rollback rot", "success", "gruen", "grün", "success", "failure", "failure",
             {research}),
            ("Gate übersprungen", "success", "gruen", "grün", "success", "skipped", "skipped",
             {research}),
            ("unerwarteter Python-Absturz", "failure", "", "", "skipped", "skipped", "skipped",
             {research}),
            ("Quell-Rollback rot", "failure", "rot", "rot – Rollback fehlgeschlagen", "skipped", "skipped", "skipped",
             {research}),
        ]
        script = step(load_workflow(WORKFLOW), "commit")["run"]
        for name, politur, ampel, zustand, render, gate, rollback, expected in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.build_fixture(root)
                env = os.environ.copy()
                env.update({"POLITUR_RESULT": politur, "POLITUR_AMPEL": ampel,
                            "POLITUR_ZUSTAND": zustand, "RENDER_RESULT": render,
                            "GATES_RESULT": gate, "ROLLBACK_RESULT": rollback})
                result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                                        cwd=root, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                committed = set(self.git(root, "show", "--format=", "--name-only", "HEAD").splitlines())
                self.assertEqual(committed, expected)
                if candidate not in expected:
                    self.assertEqual(self.git(root, "show", f"HEAD:{candidate}"), "alter geprüfter Hero")
                    self.assertEqual((root / candidate).read_text(encoding="utf-8"), "alter geprüfter Hero\n")
                    self.assertEqual(self.git(root, "show", f"HEAD:{history}"), "alte Historie")
                if state not in expected:
                    self.assertEqual(self.git(root, "show", f"HEAD:{state}"), "alter Nachweis")


if __name__ == "__main__":
    unittest.main()
