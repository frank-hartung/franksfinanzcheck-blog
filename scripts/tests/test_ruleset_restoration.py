"""Regression: Ruleset-Ziel, PR-Scoping, Publish-Priorität und Bot/Cron-Evidenz.

Kein Netz und keine Repository-Schreibzugriffe. Bash-Tests führen den echten
Deploy-Step mit Git-/Push-Doubles unter Runner-Optionen (-e -o pipefail) aus.
"""
import contextlib
import datetime as dt
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import governance_contract as gc
import governance_gate as gate
import pflichtcheck_guard as pg

NOW = dt.datetime(2026, 9, 19, 12, tzinfo=dt.timezone.utc)
WORKFLOWS = {"engine.yml": '''permissions:
  contents: write
on:
  schedule:
    - cron: '0 * * * *'
jobs:
  engine:
    steps:
      - run: |
          git config user.email "content-bot@users.noreply.github.com"
          scripts/git_sync.sh --push-only
'''}


def commit(hours=25, bot=True):
    return {"author": None, "committer": None,
            "commit": {"author": {"email": "content-bot@users.noreply.github.com" if bot else "human@example.com"},
                       "committer": {"date": (NOW - dt.timedelta(hours=hours)).isoformat()}}}


def run(**overrides):
    return {"id": 42, "event": "schedule", "status": "completed", "head_branch": "main",
            "path": ".github/workflows/engine.yml", "created_at": "2026-09-19T11:00:00Z", **overrides}


class Automation(unittest.TestCase):
    def classify(self, hours=25, runs=None):
        return pg.automation_befund(NOW - dt.timedelta(hours=hours),
                                    [run()] if runs is None else runs, ["engine.yml"], NOW)

    def test_exact_boundary_and_over_boundary(self):
        for hours, level in [(0, "green"), (23, "green"), (24, "green"),
                             (24 + 1/3600, "red"), (100, "red")]:
            with self.subTest(hours=hours):
                self.assertEqual(level, self.classify(hours)["level"])

    def test_missing_or_future_bot_is_unknown(self):
        self.assertEqual("info", self.classify(-1)["level"])
        self.assertEqual("info", pg.automation_befund(None, [run()], ["engine.yml"], NOW)["level"])

    def test_no_cron_no_red(self):
        self.assertEqual("info", self.classify(runs=[])["level"])

    def test_only_relevant_completed_crons_on_main_in_window(self):
        for changes in ({"event": "workflow_dispatch"}, {"event": "push"},
                        {"head_branch": "feature"}, {"status": "queued"},
                        {"status": "in_progress"}, {"path": ".github/workflows/read-only.yml"},
                        {"created_at": "2026-09-18T11:59:59Z"},
                        {"created_at": "2026-09-20T11:00:00Z"}):
            with self.subTest(changes=changes):
                self.assertEqual("info", self.classify(runs=[run(**changes)])["level"])
        for conclusion in ("success", "failure", "cancelled"):
            # Nicht nur grüne Crons: Schutz-Ablehnung macht gerade rote Runs.
            self.assertEqual("red", self.classify(runs=[run(conclusion=conclusion)])["level"])

    def test_commit_uses_committer_time_and_custom_workflow_identity(self):
        c = commit(1)
        c["commit"]["author"]["date"] = "2000-01-01T00:00:00Z"
        self.assertEqual([NOW - dt.timedelta(hours=1)], pg.bot_zeitpunkte([c], pg.bot_emails(WORKFLOWS)))

    def test_humans_do_not_reset_clock(self):
        self.assertEqual([], pg.bot_zeitpunkte([commit(1, False)], pg.bot_emails(WORKFLOWS)))

    def test_github_bot_identity_with_null_author_is_supported(self):
        c = commit(25, False)
        c["committer"] = {"type": "Bot", "login": "github-actions[bot]"}
        self.assertEqual([NOW - dt.timedelta(hours=25)], pg.bot_zeitpunkte([c], set()))

    def test_readonly_workflow_does_not_supply_bot_identity(self):
        readonly = WORKFLOWS["engine.yml"].replace("contents: write", "contents: read")
        self.assertNotIn("content-bot@users.noreply.github.com", pg.bot_emails({"readonly.yml": readonly}))

    def measure(self, responses):
        with patch.object(pg, "api_get", side_effect=responses) as api, \
                patch.object(pg, "workflows_laden", return_value=WORKFLOWS):
            result = pg.automation_messen("o/r", "unused", NOW)
        return result, api.call_args_list

    def test_pagination_commits_and_runs(self):
        result, calls = self.measure([([commit(1, False)] * 100, ""), ([commit()], ""),
                                     ({"workflow_runs": [run(event="push")] * 100}, ""),
                                     ({"workflow_runs": [run()]}, "")])
        self.assertEqual("red", result["level"])
        self.assertIn("sha=main", calls[0].args[0])
        self.assertIn("page=2", calls[1].args[0])
        self.assertIn("branch=main", calls[2].args[0])
        self.assertIn("event=schedule", calls[2].args[0])
        self.assertIn("page=2", calls[3].args[0])

    def test_recent_bot_needs_no_run_api(self):
        result, calls = self.measure([([commit(1)], "")])
        self.assertEqual("green", result["level"])
        self.assertEqual(1, len(calls))

    def test_api_failures_and_malformed_data_never_red_or_green(self):
        for responses in ([ (None, "HTTP 403") ], [(None, "HTTP 500")],
                          [({}, "")], [([{}], "")], [([commit()], ""), (None, "HTTP 403")],
                          [([commit()], ""), ({"workflow_runs": None}, "")],
                          [([commit()], ""), ({"workflow_runs": [run(created_at="bad")]}, "")]):
            with self.subTest(responses=responses):
                self.assertEqual("info", self.measure(responses)[0]["level"])

    def test_no_bot_in_bounded_history_is_unknown(self):
        self.assertEqual("info", self.measure([([], "")])[0]["level"])
        result, calls = self.measure([([commit(1, False)] * 100, "")] * 10)
        self.assertEqual("info", result["level"])
        self.assertEqual(10, len(calls))

    def test_governance_consumes_red_finding_not_merely_exit_code(self):
        finding = gate.classify("automation", pg.automation_report(self.classify()), exit_code=1)
        self.assertEqual("red", finding["level"])
        self.assertIn("Automation durch Branch-Schutz blockiert", finding["message"])
        self.assertEqual(("RED", "report"), gate.decide_policy({"automation": finding})[:2])
        unknown = gate.classify("automation", pg.automation_report(self.classify(runs=[])))
        self.assertEqual("info", unknown["level"])
        self.assertFalse(unknown["actionable"])

    def test_red_governance_decision_exit_and_body(self):
        classified = gate.classify("automation", pg.automation_report(self.classify()))
        classified["ts"] = gate.NOW.isoformat()
        state = {"steps": {"automation": classified}}
        with patch.object(gate, "_load_state", return_value=state), \
                patch.object(gate, "_save_state"), patch.object(gate, "_append_history"), \
                patch.object(gate, "STATE", "/not-present/governance-state.json"), \
                patch.dict(os.environ, {"GITHUB_OUTPUT": ""}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, gate.decide(fail_on="red"))
        self.assertEqual("report", state["issue_action"])
        self.assertIn("Automation durch Branch-Schutz blockiert", gate._render_from(state))

    def test_report_cli_exit_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            with patch.object(pg, "automation_messen", return_value=self.classify()), \
                    patch.object(pg, "step_summary") as summary, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(1, pg.main(["--automation", "--repo", "o/r", "--report", str(report)]))
            self.assertIn("automation_blocked", report.read_text())
            summary.assert_called_once()

    def test_governance_workflow_wiring(self):
        text = (ROOT / ".github/workflows/premium-governance.yml").read_text()
        steps = dict(gc.step_blocks(text))
        probe = next(body for name, body in steps.items() if name.startswith("Automation durch"))
        self.assertIn("pflichtcheck_guard.py --automation --report /tmp/automation-report.md", probe)
        self.assertIn("governance_gate.py --emit automation --report /tmp/automation-report.md", probe)
        self.assertIn('--exit "$rc"', probe)
        self.assertIn("GH_TOKEN: ${{ github.token }}", probe)
        self.assertIn("actions: read", text)
        self.assertLess(text.index("governance_gate.py --reset"), text.index("pflichtcheck_guard.py --automation"))
        self.assertLess(text.index("--emit automation"), text.index("--decide --fail-on red"))


class Ruleset(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "docs/integritaets-lock-ruleset.json").read_text())

    def test_runbook_body_is_exact_payload(self):
        text = (ROOT / "docs/PFLICHT-CHECK-RUNBOOK.md").read_text()
        body = text.split("```json\n", 1)[1].split("```", 1)[0]
        self.assertEqual(self.payload, json.loads(body))
        self.assertIn("23695872", text)
        self.assertIn("23710849", text)
        self.assertIn("404", text)

    def test_complete_admin_payload(self):
        self.assertEqual("active", self.payload["enforcement"])
        self.assertEqual("branch", self.payload["target"])
        self.assertEqual({"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}, self.payload["conditions"])
        self.assertEqual([{"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always"}], self.payload["bypass_actors"])
        rules = {r["type"]: r for r in self.payload["rules"]}
        self.assertEqual({"deletion", "non_fast_forward", "required_status_checks", "pull_request"}, set(rules))
        self.assertEqual([{"context": "Integritäts-Siegel", "integration_id": 15368}],
                         rules["required_status_checks"]["parameters"]["required_status_checks"])
        self.assertEqual(0, rules["pull_request"]["parameters"]["required_approving_review_count"])
        self.assertEqual(pg.VERLANGT, pg.beurteilen(self.payload["rules"], gc.PFLICHT_CHECK_NAME, pr_pflicht=True)["urteil"])
        self.assertEqual([], pg.blockiert_direkte_pushes([self.payload]))

    def test_pr_missing_or_approval_count_changed_is_not_scoped(self):
        for count in (None, 1):
            rules = [r for r in self.payload["rules"] if r["type"] != "pull_request"]
            if count is not None:
                rules.append({"type": "pull_request", "parameters": {"required_approving_review_count": count}})
            self.assertEqual(pg.PR_SCOPING_FEHLT, pg.beurteilen(rules, gc.PFLICHT_CHECK_NAME, pr_pflicht=True)["urteil"])

    def test_arbitrary_bypass_does_not_clear_warning(self):
        for bypass in (None, [], [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
                       [{"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "pull_request"}],
                       [{"actor_id": 42, "actor_type": "Integration", "bypass_mode": "always"}]):
            self.payload["bypass_actors"] = bypass
            self.assertTrue(pg.blockiert_direkte_pushes([self.payload]), bypass)

    def test_omitted_bypass_field_is_unknown_not_empty(self):
        self.payload.pop("bypass_actors")
        self.assertFalse(pg.blockiert_direkte_pushes([self.payload]))
        with patch.object(pg, "api_get", side_effect=[([{"id": 42}], ""), (dict(self.payload, id=42), "")]):
            messages = pg.bypass_pruefung("o/r", "", "main")
        self.assertIn("nicht prüfbar", " ".join(messages))
        self.assertNotIn("Schein-Sicherheit", " ".join(messages))

    def test_other_ruleset_can_still_block(self):
        other = dict(self.payload, bypass_actors=[], id=123)
        self.assertEqual([123], [r["id"] for r in pg.blockiert_direkte_pushes([self.payload, other])])

    def test_pr_only_rule_also_needs_actions_bypass(self):
        self.payload["rules"] = [{"type": "pull_request"}]
        self.payload["bypass_actors"] = []
        self.assertTrue(pg.blockiert_direkte_pushes([self.payload]))
        self.payload["rules"] = [{"type": "deletion"}, {"type": "non_fast_forward"}]
        self.assertFalse(pg.blockiert_direkte_pushes([self.payload]))

    def test_default_branch_is_not_pr_head(self):
        self.assertFalse(pg.zielt_auf(self.payload, "feature"))


class PublishPriority(unittest.TestCase):
    def script(self):
        steps = dict(gc.step_blocks((ROOT / ".github/workflows/deploy.yml").read_text()))
        body = steps["Gate-Heilungen committen (konvergent)"]
        import textwrap
        self.assertNotIn("continue-on-error", body.split("run: |")[0])
        return textwrap.dedent(body.split("run: |", 1)[1]).strip()

    def execute(self, push_rc, diff_rc=1, commit_rc=0):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "bin").mkdir()
            git = root / "bin/git"
            git.write_text(f'''#!/bin/bash
case "$1" in
  diff) exit {diff_rc} ;;
  commit) exit {commit_rc} ;;
  *) exit 0 ;;
esac
''')
            push = root / "scripts/git_sync.sh"
            push.write_text(f'#!/bin/bash\necho "Push-Doppel ausgeführt"\nexit {push_rc}\n')
            git.chmod(0o755)
            push.chmod(0o755)
            env = {**os.environ, "PATH": str(root / "bin") + ":" + os.environ["PATH"]}
            return subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c",
                                   self.script() + '\necho "DEPLOY_ERREICHT"'], cwd=root,
                                  env=env, capture_output=True, text=True, timeout=10)

    def test_rejected_push_annotates_error_but_publish_continues(self):
        result = self.execute(1)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("::error::", result.stdout)
        self.assertIn("DEPLOY_ERREICHT", result.stdout)
        self.assertNotIn("✅ Gate-Heilungen gepusht", result.stdout)

    def test_success_push_is_success_only(self):
        result = self.execute(0)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("✅ Gate-Heilungen gepusht", result.stdout)
        self.assertNotIn("::error::", result.stdout)

    def test_no_change_no_push(self):
        result = self.execute(1, diff_rc=0)
        self.assertEqual(0, result.returncode)
        self.assertNotIn("Push-Doppel", result.stdout)
        self.assertNotIn("::error::", result.stdout)

    def test_commit_failure_is_not_swallowed(self):
        result = self.execute(0, commit_rc=1)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("DEPLOY_ERREICHT", result.stdout)

    def test_actual_deploy_and_content_gates_not_unconditionally_enabled(self):
        steps = dict(gc.step_blocks((ROOT / ".github/workflows/deploy.yml").read_text()))
        for name in ("Deploy auf gh-pages", "Themenwelten – finales Veröffentlichungs-Gate"):
            self.assertNotIn("if: always()", steps[name])
            self.assertNotIn("continue-on-error: true", steps[name])


if __name__ == "__main__":
    unittest.main()
