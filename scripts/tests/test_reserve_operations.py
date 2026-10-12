"""Daily-reserve operational contracts; no API, model or production writes."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import reserve_artifacts as artifacts
import reserve_converge as converge
import reserve_finisher as finisher
import reserve_gate as gate
import reserve_intake as intake
import reserve_janitor as janitor
import reserve_operations as ops
import reserve_readiness as readiness
import reserve_recert as recert

NOW = dt.datetime(2026, 10, 12, 12, tzinfo=dt.timezone.utc)
STAMP = NOW.isoformat()
RAW = b"---\ntitle: Probe\ndate: 2026-10-12T06:00:00Z\ndraft: true\nreserve: true\n---\nProbe.\n"


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.posts = self.root / "content" / "posts"
        self.cert = self.root / "data" / "reserve-readiness.json"
        # Tests judge their input, not this runner's production environment.
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def draft(self, slug="probe", raw=RAW):
        path = self.posts / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def snapshot(self, count=2, **extra):
        rows = []
        for n in range(count):
            path = self.draft(f"probe-{n}")
            rows.append({"slug": path.parent.name, "ready": True,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "measured_at": STAMP})
        data = {"target": 2, "ready": count, "pool_size": count,
                "generated_at": STAMP, "candidates": rows, **extra}
        artifacts.write_object(self.cert, data)
        return data

    def assess(self):
        original = artifacts.proof_age_hours
        with patch.object(artifacts, "proof_age_hours", wraps=original) as age:
            age.side_effect = lambda data, row=None, **kw: original(data, row, now=NOW)
            return gate.assessment(self.cert, self.posts)


class BudgetTests(Sandbox):
    def test_default_local_limit_and_shared_deadline(self):
        self.assertEqual(30, ops.work_seconds(30, env={}, now=100))
        self.assertEqual(8, ops.work_seconds(30, env={ops.DEADLINE_ENV: "108"}, now=100))
        self.assertEqual(30, ops.work_seconds(30, env={ops.DEADLINE_ENV: "900"}, now=100))

    def test_malformed_or_expired_deadline_never_means_unlimited(self):
        for value in ("", "bad", "nan", "inf", "-inf", "0", "-1", "99"):
            with self.subTest(value=value):
                self.assertEqual(0, ops.work_seconds(30, env={ops.DEADLINE_ENV: value}, now=100))

    def test_invalid_local_limit_is_rejected(self):
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                ops.work_seconds(value, env={}, now=100)

    def test_failed_preflight_cannot_grant_a_writing_window(self):
        env_file = self.root / "env"
        self.assertEqual(3, ops.preflight(env_file=env_file, now=100,
                                         checker=lambda: (False, "dictionary broken")))
        self.assertFalse(env_file.exists())

    def test_start_is_a_clock_anchor_not_a_tool_proof(self):
        env_file = self.root / "env"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, ops.start_window(env_file=env_file, now=100))
        self.assertIn("kein Schreibrecht", output.getvalue())
        self.assertEqual("RESERVE_WORK_DEADLINE=4000.000000\n", env_file.read_text())

    def test_preflight_does_not_extend_the_initial_job_window(self):
        path = self.root / "env"
        with patch.dict(os.environ, {ops.DEADLINE_ENV: "4000"}):
            self.assertEqual(0, ops.preflight(minutes=65, env_file=path, now=1000,
                                             checker=lambda: (True, "real tools")))
        self.assertEqual("RESERVE_WORK_DEADLINE=4000.000000\n", path.read_text())

    def test_expired_preflight_preserves_environment_file(self):
        path = self.root / "env"
        path.write_bytes(b"existing=true\n")
        with patch.dict(os.environ, {ops.DEADLINE_ENV: "100"}):
            self.assertEqual(124, ops.preflight(env_file=path, now=100,
                                               checker=lambda: (True, "tools")))
        self.assertEqual(b"existing=true\n", path.read_bytes())

    def test_bad_cli_windows_never_write_environment(self):
        path = self.root / "env"
        for value in (0, -1, 91, float("nan"), float("inf")):
            self.assertEqual(3, ops.start_window(minutes=value, env_file=path, now=100))
            self.assertEqual(3, ops.preflight(minutes=value, env_file=path, now=100,
                                             checker=lambda: (True, "tools")))
        self.assertFalse(path.exists())

    def test_selftest_is_independent_of_ci_deadline_and_environment(self):
        with patch.dict(os.environ, {ops.DEADLINE_ENV: "broken", "GITHUB_ENV": str(self.root / "env")}):
            self.assertEqual(0, ops.run_selftest())
        self.assertFalse((self.root / "env").exists())


    def test_stage_wrapper_does_not_start_a_process_after_shared_deadline(self):
        calls = []
        with patch.dict(os.environ, {ops.DEADLINE_ENV: "invalid"}):
            self.assertEqual(124, ops.bounded_command(["python3", "writer.py"],
                                                     runner=lambda *a, **kw: calls.append(a)))
        self.assertEqual([], calls)

    def test_stage_wrapper_passes_only_remaining_time_and_real_return_code(self):
        received = []
        def run(command, **kwargs):
            received.append(kwargs["timeout"])
            return subprocess.CompletedProcess(command, 3, "real output\n", "")
        with patch.dict(os.environ, {ops.DEADLINE_ENV: "107"}), patch.object(ops.time, "time", return_value=100):
            self.assertEqual(3, ops.bounded_command(["python3", "writer.py"], cap=60, runner=run))
        self.assertEqual([7], received)

    def test_stage_wrapper_keeps_timeout_diagnostics(self):
        def run(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], b"actual partial output\n", b"actual error\n")
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(124, ops.bounded_command(["python3", "writer.py"], cap=60, runner=run))
        self.assertIn("actual partial output", output.getvalue())
        self.assertIn("actual error", errors.getvalue())

    def test_stage_wrapper_rejects_invalid_parameters(self):
        self.assertEqual(3, ops.bounded_command([]))
        for cap in (0, -1, float("nan"), float("inf")):
            self.assertEqual(3, ops.bounded_command(["python3"], cap=cap))


class ProcessTests(Sandbox):
    def test_captured_process_preserves_both_streams_and_exit(self):
        result = ops.run_healer([sys.executable, "-c",
                                "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"],
                               cwd=self.root, timeout=10)
        self.assertEqual(7, result.returncode)
        self.assertEqual("out\n", result.stdout)
        self.assertEqual("err\n", result.stderr)

    def test_timeout_reaps_grandchild_before_returning(self):
        pid_path = self.root / "child-pid"
        sentinel = self.root / "escaped-writer"
        child = ("import os,signal,time,pathlib; "
                 "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                 f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid())); "
                 f"time.sleep(1.5); pathlib.Path({str(sentinel)!r}).write_text('bad'); time.sleep(30)")
        parent = (f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(30)")
        with self.assertRaises(subprocess.TimeoutExpired):
            ops.run_healer([sys.executable, "-c", parent], cwd=self.root, timeout=0.8)
        self.assertTrue(pid_path.exists(), "the grandchild must actually have run")
        subprocess.run([sys.executable, "-c", "import time; time.sleep(1)"], check=True, timeout=5)
        pid = int(pid_path.read_text())
        # A zombie cannot write; an absent process is also correctly terminated.
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists():
            self.assertEqual("Z", stat.read_text().split()[2])
        self.assertFalse(sentinel.exists())

    def test_termination_handlers_nest_and_restore(self):
        previous = signal.getsignal(signal.SIGTERM)
        with ops.restore_on_termination():
            outer = signal.getsignal(signal.SIGTERM)
            with self.assertRaises(ops.WorkInterrupted):
                with ops.restore_on_termination():
                    signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            self.assertIs(outer, signal.getsignal(signal.SIGTERM))
        self.assertIs(previous, signal.getsignal(signal.SIGTERM))


class FinisherBudgetTests(Sandbox):
    def test_whole_chain_shares_one_budget_across_files(self):
        paths = [self.draft("a"), self.draft("b"), self.draft("c")]
        clock, timeouts, results = [0.0], [], []

        def run(cmd, **kw):
            timeouts.append(kw["timeout"])
            clock[0] += 4
            return subprocess.CompletedProcess(cmd, 0, "ok\n", "")

        with patch.object(finisher, "HEALER_CHAIN", [("healer.py", ["--fix"], "file")]):
            finisher.run_chain(results, paths, max_seconds=5,
                               now=lambda: clock[0], runner=run)
        self.assertEqual([5, 1], timeouts)
        self.assertEqual(124, results[-1]["rc"])
        self.assertIn("ZEIT-BUDGET", results[-1]["letzte_zeile"])

    def test_workflow_deadline_is_not_reset_per_healer(self):
        clock, timeouts, results = [0.0], [], []

        def run(cmd, **kw):
            timeouts.append(kw["timeout"])
            clock[0] += 3
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        with patch.dict(os.environ, {ops.DEADLINE_ENV: "103"}), \
                patch.object(ops.time, "time", side_effect=lambda: 100 + clock[0]), \
                patch.object(finisher, "HEALER_CHAIN", [("a.py", [], "corpus"), ("b.py", [], "corpus")]):
            finisher.run_chain(results, [self.draft()], max_seconds=30,
                               now=lambda: clock[0], runner=run)
        self.assertEqual([3], timeouts)
        self.assertEqual(124, results[-1]["rc"])

    def test_timeout_prevents_any_following_healer(self):
        calls, results = [], []

        def run(cmd, **kw):
            calls.append(cmd)
            raise subprocess.TimeoutExpired(cmd, kw["timeout"])

        with patch.object(finisher, "HEALER_CHAIN", [("a.py", [], "corpus"), ("b.py", [], "corpus")]):
            finisher.run_chain(results, [self.draft()], runner=run)
        self.assertEqual(1, len(calls))
        self.assertEqual(124, results[0]["rc"])

    def test_malformed_budget_does_not_start_a_writer(self):
        calls, results = [], []
        with patch.dict(os.environ, {ops.DEADLINE_ENV: "broken"}):
            finisher.run_chain(results, [self.draft()], runner=lambda *a, **kw: calls.append(a))
        self.assertEqual([], calls)
        self.assertEqual(124, results[0]["rc"])


    def test_full_fresh_stock_does_not_commission_optional_model_polish(self):
        data = self.snapshot()
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        data["generated_at"] = stamp
        for row in data["candidates"]:
            row["measured_at"] = stamp
        artifacts.write_object(self.cert, data)
        with patch.dict(os.environ, {"RESERVE_TARGET": "2"}), \
                patch.object(finisher, "READINESS", self.cert), \
                patch.object(finisher, "POSTS_DIR", self.posts), \
                patch.object(finisher, "heiler_deckung", return_value=None), \
                patch.object(finisher, "loesch_deckung", return_value=None), \
                patch.object(finisher, "write_report"), \
                patch("reserve_pool.reserve_drafts") as pool, \
                patch.object(finisher, "run_chain") as heal:
            self.assertEqual(0, finisher.finish(only_if_needed=True))
        pool.assert_not_called()
        heal.assert_not_called()

    def test_termination_rolls_back_today_and_promoted_drafts(self):
        for day in ("2026-10-12", "2026-10-07"):
            with self.subTest(day=day):
                path = self.draft(day + "-probe", raw=RAW.replace(b"\n", b"\r\n"))
                original = path.read_bytes()
                def interrupt(results, targets):
                    targets[0].write_bytes(b"partial model output")
                    raise ops.WorkInterrupted("SIGTERM")
                with patch.object(finisher, "POSTS_DIR", self.posts), \
                        patch.object(finisher, "today_prefix", return_value="2026-10-12"), \
                        patch.object(finisher, "heiler_deckung", return_value=None), \
                        patch.object(finisher, "loesch_deckung", return_value=None), \
                        patch.object(finisher, "certified_slugs", return_value={}), \
                        patch("reserve_pool.reserve_drafts", return_value=[path]), \
                        patch.object(finisher, "_canonical_cta_hygiene", return_value=0), \
                        patch.object(finisher, "isolation_baseline", return_value={}), \
                        patch.object(finisher, "isolation_enforce", return_value=[]) as isolation, \
                        patch.object(finisher, "run_chain", side_effect=interrupt), \
                        patch.object(finisher, "write_report"):
                    self.assertEqual(1, finisher.finish())
                isolation.assert_called_once()
                self.assertEqual(original, path.read_bytes())
                path.unlink()
                path.parent.rmdir()


class ProofTimeTests(Sandbox):
    def test_partial_recert_pins_unchanged_legacy_proof_time(self):
        data = self.snapshot()
        old = (NOW - dt.timedelta(hours=72)).isoformat()
        data["generated_at"] = old
        for row in data["candidates"]:
            row.pop("measured_at")
        drafts = {row["slug"]: self.posts / row["slug"] / "index.md" for row in data["candidates"]}
        fresh = dict(data["candidates"][0], measured_at=STAMP)
        with patch.object(readiness, "certify_one", return_value=fresh) as measure, \
                patch.object(recert, "_now", return_value=STAMP):
            result = recert.recertify(data, drafts, [fresh["slug"]])
        self.assertEqual(1, measure.call_count)
        self.assertEqual(old, result["candidates"][1]["measured_at"])
        self.assertEqual(STAMP, result["generated_at"])
        self.assertIsNone(artifacts.proof_problem(result, fresh, now=NOW))
        self.assertIn("veraltet", artifacts.proof_problem(result, result["candidates"][1], now=NOW))
        self.assertNotIn("measured_at", data["candidates"][1], "input must not be mutated")

    def test_refresh_stale_selects_only_aged_or_drifted_rows(self):
        data = self.snapshot()
        data["candidates"][0]["measured_at"] = (NOW - dt.timedelta(hours=37)).isoformat()
        drafts = {r["slug"]: self.posts / r["slug"] / "index.md" for r in data["candidates"]}
        self.assertEqual([], recert.drift(data, drafts))
        findings = recert.drift(data, drafts, refresh_stale=True, now=NOW)
        self.assertEqual([("probe-0", "veraltet")], [(f["slug"], f["art"]) for f in findings])

    def test_missing_future_and_invalid_times_are_not_measurements(self):
        for raw in (None, "bad", "2026-10-12T12:00:00", (NOW + dt.timedelta(minutes=6)).isoformat()):
            self.assertIsNotNone(artifacts.proof_problem({"generated_at": raw}, {}, now=NOW))
        self.assertIsNone(artifacts.proof_problem({"generated_at": STAMP}, {}, now=NOW))

    def test_invalid_explicit_row_time_cannot_fall_back_to_fresh_batch(self):
        row = {"slug": "probe", "ready": False, "measured_at": None}
        self.assertIsNotNone(artifacts.proof_problem({"generated_at": STAMP}, row, now=NOW))
        with self.assertRaises(ValueError):
            artifacts.certificate_rows({"candidates": [row]})

    def test_age_configuration_cannot_relax_the_36_hour_contract(self):
        with patch.dict(os.environ, {"RESERVE_CERT_MAX_AGE_H": "999"}):
            self.assertEqual(36, artifacts.max_age_hours())
            old = (NOW - dt.timedelta(hours=40)).isoformat()
            self.assertIsNotNone(artifacts.proof_problem({"generated_at": old}, {}, now=NOW))
        with patch.dict(os.environ, {"RESERVE_CERT_MAX_AGE_H": "12"}):
            self.assertEqual(12, artifacts.max_age_hours())

    def test_missing_legacy_time_requires_full_measurement(self):
        data = self.snapshot()
        data.pop("generated_at")
        for row in data["candidates"]:
            row.pop("measured_at")
        drafts = {r["slug"]: self.posts / r["slug"] / "index.md" for r in data["candidates"]}
        with self.assertRaises(recert.Abwertungsverdacht):
            recert.recertify(data, drafts, [])


class MeasurementTests(Sandbox):
    def test_unknown_score_is_a_tool_failure_before_publication_mutation(self):
        path = self.draft()
        with patch.object(readiness, "score_diagnosis", return_value={
                "score": 0.95, "measurement_errors": {"spelling": "broken"}}), \
                patch.object(readiness.rp, "publish_one") as publish:
            with self.assertRaises(readiness.MeasurementUnavailable):
                readiness.certify_one(path)
        publish.assert_not_called()
        self.assertEqual(RAW, path.read_bytes())

    def test_sigterm_restores_original_draft_bytes_and_handler(self):
        path = self.draft(raw=RAW.replace(b"\n", b"\r\n"))
        original = path.read_bytes()
        old_handler = signal.getsignal(signal.SIGTERM)

        def terminate(index):
            self.assertNotEqual(original, index.read_bytes(), "simulation must actually mutate")
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

        with patch.object(readiness, "score_diagnosis", return_value=None), \
                patch.object(readiness, "reserve_editorial_findings", return_value=[]), \
                patch.object(readiness, "capture_gate", side_effect=terminate):
            with self.assertRaises(ops.WorkInterrupted):
                readiness.certify_one(path)
        self.assertEqual(original, path.read_bytes())
        self.assertIs(old_handler, signal.getsignal(signal.SIGTERM))

    def test_mid_batch_tool_failure_does_not_replace_previous_proof_or_quarantine(self):
        data = self.snapshot()
        before = self.cert.read_bytes()
        paths = [self.posts / r["slug"] / "index.md" for r in data["candidates"]]
        with patch.dict(os.environ, {"RESERVE_WRITERS_ALLOWED": "0"}), \
                patch.object(readiness, "ROOT", self.root), \
                patch.object(recert, "gate_verfuegbar", return_value=(True, "tools")), \
                patch.object(readiness.rp, "reserve_drafts", return_value=paths), \
                patch.object(readiness, "certify_one", side_effect=[data["candidates"][0], readiness.MeasurementUnavailable("down")]), \
                patch("reserve_quarantine.record") as quarantine:
            self.assertEqual(3, readiness.main())
        quarantine.assert_not_called()
        self.assertEqual(before, self.cert.read_bytes())
        for path in paths:
            self.assertEqual(RAW, path.read_bytes())

    def test_readonly_measurement_has_no_intake_custody_or_quarantine_writes(self):
        data = self.snapshot(count=1)
        with patch.dict(os.environ, {"RESERVE_WRITERS_ALLOWED": "0"}), \
                patch.object(readiness, "ROOT", self.root), \
                patch.object(recert, "gate_verfuegbar", return_value=(True, "tools")), \
                patch.object(readiness.rp, "reserve_drafts", return_value=[self.posts / "probe-0" / "index.md"]), \
                patch.object(readiness, "certify_one", return_value=data["candidates"][0]), \
                patch("reserve_custody.heal_quiet") as custody, \
                patch("reserve_intake.bestandsaufnahme") as adopt, \
                patch("reserve_quarantine.record") as quarantine:
            self.assertEqual(1, readiness.main())  # 1/6 is still honestly short
        custody.assert_not_called()
        adopt.assert_not_called()
        quarantine.assert_not_called()

    def test_quality_score_keeps_tool_errors_separate_from_editorial_score(self):
        import quality_score
        path = self.draft()
        with patch("spellcheck.analyze_article", side_effect=RuntimeError("dictionary failure")), \
                patch.object(quality_score.glob, "glob", return_value=[]), \
                patch("readability_check.load_article", return_value={"probe": True}), \
                patch("readability_check.analyze", return_value={"score": 100}):
            score = quality_score.score_article(str(path))
        self.assertEqual(0.5, score["parts"]["spelling"])
        self.assertEqual({"spelling": "dictionary failure"}, score["measurement_errors"])

    def test_second_score_failure_cannot_be_accepted_by_production_gate(self):
        import publication_release
        path = self.draft()
        with patch.object(publication_release, "preheal_candidate", return_value=[]), \
                patch("quality_score.score_article", return_value={"score": 0.95, "measurement_errors": {"spelling": "down"}}), \
                patch.object(publication_release, "run") as render:
            with self.assertRaises(publication_release.ReleaseBuildCrash):
                publication_release.accept_candidate(path)
        render.assert_not_called()


    def test_publish_gate_unavailable_measurement_is_not_an_editorial_rejection(self):
        path = self.draft()
        with patch.object(readiness, "score_diagnosis", return_value=None), \
                patch.object(readiness, "reserve_editorial_findings", return_value=[]), \
                patch.object(readiness, "capture_gate", return_value=(False, "AFFILIATE-INTEGRITÄT NICHT BEWEISBAR: no render proof")):
            with self.assertRaises(readiness.MeasurementUnavailable):
                readiness.certify_one(path)
        self.assertEqual(RAW, path.read_bytes())

    def test_rs_parser_failure_does_not_reclassify_the_article_as_bad_content(self):
        path = self.draft()
        with patch.object(readiness, "score_diagnosis", return_value=None), \
                patch.object(readiness, "reserve_editorial_findings", return_value=["Reserve-Qualitäts-Gate nicht prüfbar: broken YAML"]):
            with self.assertRaises(readiness.MeasurementUnavailable):
                readiness.certify_one(path)
        self.assertEqual(RAW, path.read_bytes())

    def test_every_hunspell_query_is_utf8_bounded_and_exit_checked(self):
        import spellcheck
        calls = []

        def run(cmd, **kw):
            calls.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch.object(spellcheck.subprocess, "run", side_effect=run):
            spellcheck.batch_hunspell(["prüft"])
            spellcheck.is_noun_capitalized("probe")
            spellcheck.suggestions("Fheler")
            spellcheck.analyze_article({"body": "z. B. Wenn, Dadurch wird es gut.",
                                       "content": "", "description": ""}, set())
        self.assertTrue(calls)
        for cmd, kw in calls:
            self.assertIn("UTF-8", cmd)
            self.assertEqual(15, kw["timeout"])
            self.assertTrue(kw["check"])

    def test_dictionary_exit_error_cannot_be_interpreted_as_perfect_spelling(self):
        import spellcheck
        with patch.object(spellcheck.subprocess, "run", side_effect=subprocess.CalledProcessError(2, ["hunspell"])):
            with self.assertRaises(subprocess.CalledProcessError):
                spellcheck.batch_hunspell(["prüft"])

    def test_preflight_checks_umlauts_not_just_ascii_installation(self):
        calls = []
        def run(cmd, **kw):
            calls.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0, "Fheler\n", "")
        with patch.object(recert.subprocess, "run", side_effect=run), \
                patch("spellcheck.analyze_article", return_value=[]):
            self.assertTrue(recert.messkette_rechtschreibung()[0])
        self.assertIn("Rücklagen", calls[0][1]["input"])
        self.assertIn("behält", calls[0][1]["input"])
        self.assertIn("UTF-8", calls[0][0])


class EndGateTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.dict(os.environ, {"RESERVE_TARGET": "2"}))

    def test_green_report_is_retrievable_and_has_actionable_stage_outcomes(self):
        self.snapshot()
        result = self.assess()
        self.assertTrue(result["ok"])
        report = self.root / "report.json"
        summary = self.root / "summary.md"
        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
            gate.write_end_report(result, report)
        saved = artifacts.read_object(report)
        self.assertEqual("ok", saved["class"])
        self.assertIn("Keine zusätzliche KI-Produktion", saved["next_action"])
        self.assertIn("bestätigt", summary.read_text())

    def test_real_shortage_is_not_classified_ok_in_saved_history(self):
        self.snapshot(count=1)
        result = self.assess()
        self.assertFalse(result["ok"])
        self.assertEqual("engpass", result["class"])
        history = self.root / "history.jsonl"
        with patch.dict(os.environ, {"RESERVE_HISTORY": str(history)}):
            gate.chronik_schreiben(result["ready"], result["target"], result["candidates"], result["class"])
        self.assertEqual("engpass", json.loads(history.read_text())["klasse"])

    def test_hash_drift_has_proof_diagnosis_not_key_or_content_guess(self):
        self.snapshot()
        (self.posts / "probe-0" / "index.md").write_bytes(RAW + b"Changed.\n")
        result = self.assess()
        self.assertEqual("nachweis", result["class"])
        self.assertEqual(1, result["ready"])
        report = self.root / "report.json"
        gate.write_end_report(result, report)
        self.assertIn("reserve_recert", artifacts.read_object(report)["next_action"])
        self.assertEqual("probe-0", artifacts.read_object(report)["blockers"][0]["slug"])

    def test_stale_individual_proof_does_not_get_refreshed_by_batch_time(self):
        data = self.snapshot()
        data["candidates"][0]["measured_at"] = (NOW - dt.timedelta(hours=40)).isoformat()
        artifacts.write_object(self.cert, data)
        result = self.assess()
        self.assertEqual(1, result["ready"])
        self.assertEqual("nachweis", result["class"])

    def test_surplus_stale_row_does_not_block_sufficient_real_fresh_stock(self):
        data = self.snapshot(count=3)
        data["candidates"][0]["measured_at"] = (NOW - dt.timedelta(hours=40)).isoformat()
        artifacts.write_object(self.cert, data)
        result = self.assess()
        self.assertTrue(result["ok"])
        self.assertEqual(2, result["ready"])
        self.assertFalse(result["candidates"][0]["ready"])

    def test_duplicate_json_or_broken_memory_is_measurement_failure(self):
        self.snapshot()
        for filename, raw in ((self.cert, '{"candidates": [], "candidates": []}'),
                              (self.cert.parent / "reserve-custody.json", '{broken')):
            with self.subTest(filename=filename):
                self.snapshot()
                filename.write_text(raw)
                result = self.assess()
                self.assertEqual("artefakt", result["class"])
                self.assertFalse(result["ok"])
                filename.unlink()

    def test_current_attempt_required_but_convergence_may_recover_failed_stage(self):
        context = {"kind": "full", "run_id": "100", "run_attempt": "2"}
        self.snapshot(measurement=context)
        env = {"RESERVE_REQUIRE_CURRENT_RUN": "1", "GITHUB_RUN_ID": "100", "GITHUB_RUN_ATTEMPT": "2",
               "RESERVE_STUFE1_STATUS": "failure", "RESERVE_STUFE2_STATUS": "failure",
               "RESERVE_STUFE3_STATUS": "failure", "RESERVE_STUFE4_STATUS": "success"}
        with patch.dict(os.environ, env):
            result = self.assess()
            self.assertTrue(result["ok"])
            self.assertEqual("failure", result["stages"]["3"])
            with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "3"}):
                self.assertEqual("kette", self.assess()["class"])

    def test_other_run_cannot_pass_even_with_full_fresh_stock(self):
        data = self.snapshot(measurement={"kind": "full", "run_id": "old", "run_attempt": "1"})
        self.assertIsNotNone(artifacts.measurement_problem(data, env={
            "RESERVE_REQUIRE_CURRENT_RUN": "1", "GITHUB_RUN_ID": "new", "GITHUB_RUN_ATTEMPT": "1"}))
        self.assertIsNone(artifacts.measurement_problem(data, env={}))  # local/legacy compatibility

    def test_red_selftests_or_tool_preflight_never_pass(self):
        self.snapshot()
        for env, expected in (({"RESERVE_WACHEN_ROT": "1"}, "wachen"),
                              ({"RESERVE_TOOL_STATUS": "failure"}, "werkzeug"),
                              ({"RESERVE_SYNC_STATUS": "failure"}, "kette")):
            with patch.dict(os.environ, env):
                result = self.assess()
                self.assertEqual(expected, result["class"])
                self.assertFalse(result["ok"])

    def test_history_is_idempotent_per_run_attempt_not_entire_run_id(self):
        history = self.root / "history.jsonl"
        with patch.dict(os.environ, {"RESERVE_HISTORY": str(history), "GITHUB_RUN_ID": "100", "GITHUB_RUN_ATTEMPT": "1"}):
            gate.chronik_schreiben(1, 2, [], "engpass")
            gate.chronik_schreiben(1, 2, [], "engpass")
            with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}):
                gate.chronik_schreiben(2, 2, [], "ok")
                gate.chronik_schreiben(2, 2, [], "ok")
        rows = [json.loads(line) for line in history.read_text().splitlines()]
        self.assertEqual(["1", "2"], [r["versuch"] for r in rows])


class NoBlindProductionTests(Sandbox):
    def test_missing_measurement_is_repaired_before_any_production(self):
        calls = []
        states = iter([{"exists": False, "ready": 0, "target": 6, "pool_size": 0},
                       {"exists": True, "ready": 6, "target": 6, "pool_size": 6}])
        result = converge.converge(state_reader=lambda: next(states),
                                   runner=lambda cmd, *a, **kw: calls.append(Path(cmd[1]).name) or 0,
                                   log=lambda *_: None)
        self.assertTrue(result["ok"])
        self.assertEqual(["reserve_readiness.py"], calls)

    def test_failed_measurement_repair_never_commissions_new_text(self):
        calls = []
        state = {"exists": False, "ready": 0, "target": 6, "pool_size": 0}
        result = converge.converge(state_reader=lambda: dict(state),
                                   runner=lambda cmd, *a, **kw: calls.append(Path(cmd[1]).name) or 3,
                                   log=lambda *_: None)
        self.assertFalse(result["ok"])
        self.assertEqual("messung-fehlt", result["abbruch"])
        self.assertEqual(["reserve_readiness.py"], calls)


class AuxiliaryMemoryTests(Sandbox):
    def test_corrupt_janitor_memory_is_not_an_empty_deletion_counter(self):
        path = self.root / janitor.JANITOR_STATE
        path.parent.mkdir()
        path.write_bytes(b'{"a": {}, "a": {}}')
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            janitor.lade_zaehler(self.root)
        self.assertEqual(before, path.read_bytes())

    def test_intake_rolls_back_content_when_provenance_cannot_be_saved(self):
        path = self.draft(raw=RAW.replace(b"reserve: true\n", b"").replace(b"\n", b"\r\n"))
        original = path.read_bytes()
        with patch.object(intake, "_ledger_schreiben", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                intake.uebernehmen(path, "fixture", root=self.root, heute=NOW.date())
        self.assertEqual(original, path.read_bytes())

    def test_broken_intake_provenance_is_never_silently_replaced(self):
        path = self.root / intake.LEDGER
        path.parent.mkdir()
        path.write_bytes(b'{broken')
        with self.assertRaises(ValueError):
            intake._ledger_schreiben(self.root, {"slug": "probe"})
        self.assertEqual(b'{broken', path.read_bytes())


    def test_invalid_auxiliary_memory_invalidates_certificate_before_any_writes(self):
        self.snapshot()
        before = self.cert.read_bytes()
        for name, raw in (("reserve-intake.json", '{"uebernahmen": null}'),
                          ("reserve-intake.json", '{"uebernahmen": [{}]}'),
                          ("reserve-janitor-state.json", '{"probe": 3}')):
            path = self.cert.parent / name
            path.write_text(raw)
            with self.assertRaises(ValueError):
                artifacts.read_certificate(self.cert)
            with patch.object(readiness, "ROOT", self.root), \
                    patch("reserve_custody.heal_quiet") as heal:
                self.assertEqual(2, readiness.main())
            heal.assert_not_called()
            self.assertEqual(before, self.cert.read_bytes())
            import reserve_snapshot_heiler
            state_before = path.read_bytes()
            self.assertTrue(reserve_snapshot_heiler.repariere(self.root)["fehler"])
            self.assertEqual(state_before, path.read_bytes())
            self.assertEqual(before, self.cert.read_bytes())
            path.unlink()


class WorkflowContractTests(unittest.TestCase):
    def workflow(self):
        import yaml
        return yaml.safe_load((ROOT / ".github/workflows/content-reserve.yml").read_text())["jobs"]["reserve"]

    def test_all_content_writers_require_successful_selftests_tools_and_snapshot(self):
        job = self.workflow()
        steps = job["steps"]
        for step in steps:
            if step.get("id") in ("stock", "finish", "convergence", "bestand") or "Janitor" in step.get("name", ""):
                with self.subTest(name=step["name"]):
                    self.assertIn("steps.wachen.outcome == 'success'", step["if"])
                    self.assertIn("steps.tools.outcome == 'success'", step["if"])
                    self.assertIn("steps.snapshot.outcome == 'success'", step["if"])
                    if step.get("id") in ("stock", "finish", "convergence"):
                        self.assertIn("steps.bestand.outcome == 'success'", step["if"])
        readonly = next(s for s in steps if s.get("id") == "readiness")
        self.assertEqual("${{ !cancelled() }}", readonly["if"])
        self.assertIn("RESERVE_WRITERS_ALLOWED", readonly["env"])

    def test_stage_truth_uses_outcome_not_continue_on_error_conclusion(self):
        steps = self.workflow()["steps"]
        for step in steps:
            if "reserve_gate.py" in step.get("run", ""):
                for key, value in step.get("env", {}).items():
                    if key.startswith("RESERVE_STUFE"):
                        self.assertIn(".outcome", value)
                        self.assertNotIn(".conclusion", value)
        final = next(s for s in steps if s.get("id") == "end_gate")
        self.assertNotIn("continue-on-error", final)
        self.assertIn("pipefail", final["run"])

    def test_inventory_repair_precedes_model_generation(self):
        steps = self.workflow()["steps"]
        ids = [s.get("id") for s in steps]
        self.assertLess(ids.index("bestand"), ids.index("stock"))
        before = next(s for s in steps if s.get("id") == "bestand")
        self.assertIn("reserve_recert.py --fix --refresh-stale", before["run"])
        self.assertNotIn("secrets.", str(before.get("env", {})))

    def test_expensive_stages_bound_the_entire_process_not_only_the_next_batch(self):
        steps = self.workflow()["steps"]
        for id in ("stock", "readiness", "bestand"):
            step = next(s for s in steps if s.get("id") == id)
            self.assertIn("reserve_operations.py --timeout-sekunden", step["run"])
            self.assertIn("--run python3", step["run"])
        inventory = next(s for s in steps if s.get("id") == "bestand")
        self.assertIn('if [ "$CODE" -gt 1 ]; then exit "$CODE"; fi', inventory["run"])

    def test_diagnosis_survives_failure_and_cancellation_without_new_permissions(self):
        job = self.workflow()
        upload = next(s for s in job["steps"] if "upload-artifact" in s.get("uses", ""))
        self.assertEqual("${{ always() }}", upload["if"])
        self.assertIn("run_attempt", upload["with"]["name"])
        self.assertIn("reserve-end.json", upload["with"]["path"])
        self.assertEqual(21, upload["with"]["retention-days"])
        self.assertEqual("1", job["env"]["RESERVE_REQUIRE_CURRENT_RUN"])

    def test_all_reserve_owned_memories_are_in_staging_and_whole_file_merge_policy(self):
        import reserve_stage_guard
        for name in ("data/reserve-intake.json", "data/reserve-janitor-state.json"):
            self.assertIn(name, reserve_stage_guard.ALLOWED_FILES)
            self.assertIn(name, reserve_stage_guard.STAGE_PATHS)
            self.assertIn(name + " merge=binary", (ROOT / ".gitattributes").read_text())
            self.assertIn(name, (SCRIPTS / "git_sync.sh").read_text())


if __name__ == "__main__":
    unittest.main()
