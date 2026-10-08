"""#634: whole snapshots, real READY identities and hermetic merge regressions."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import reserve_artifacts as ra
import reserve_converge as converge
import reserve_custody as custody
import reserve_finisher as finisher
import reserve_gate as gate
import reserve_janitor as janitor
import reserve_pool as pool
import reserve_quarantine as quarantine
import reserve_readiness as readiness
import reserve_recert as recert


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.posts = self.root / "content" / "posts"
        self.cert = self.root / "data" / "reserve-readiness.json"
        self.enterContext(patch.dict(os.environ, {"RESERVE_TARGET": "6"}))

    def draft(self, slug="kandidat", raw=None):
        index = self.posts / slug / "index.md"
        index.parent.mkdir(parents=True, exist_ok=True)
        raw = raw if raw is not None else b"---\ndraft: true\nreserve: true\n---\nText.\n"
        index.write_bytes(raw)
        return {"slug": slug, "ready": True, "sha256": hashlib.sha256(raw).hexdigest()}

    def write_cert(self, rows):
        data = {"target": 6, "ready": sum(r["ready"] for r in rows),
                "pool_size": len(rows), "generated_at": "2026-10-08T12:00:00Z",
                "candidates": rows}
        ra.write_object(self.cert, data)
        return data


class StrictJsonTests(Sandbox):
    def test_duplicates_and_invalid_json_are_rejected_at_every_depth(self):
        for text in ('{"generated_at":"a","generated_at":"b"}',
                     '{"x":{"hits":1,"hits":2}}', '{"x":1,',
                     '[]', 'null', '{"x":NaN}', '{"x":Infinity}',
                     '{"x":-Infinity}', '{"x":1e999}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ra.parse_object(text)
        self.assertEqual({"x": {"hits": 2}}, ra.parse_object('{"x":{"hits":2}}'))

    def test_duplicate_candidates_cannot_inflate_stock(self):
        row = self.draft()
        self.write_cert([row, dict(row)])
        with self.assertRaisesRegex(ValueError, "doppelter Kandidaten-Slug"):
            ra.read_certificate(self.cert)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual((0, 6, []), gate.evaluate(self.cert, self.posts))
        self.assertEqual(0, converge.cert_state(self.cert, self.posts)["ready"])
        self.assertIsNone(recert.load_cert(self.cert))
        with patch.object(finisher, "READINESS", self.cert):
            self.assertEqual({}, finisher.certified_slugs())

    def test_bad_candidate_shapes_types_and_hashes_are_fail_closed(self):
        row = self.draft()
        variants = [None, "Text", {}, dict(row, slug="../outside"),
                    dict(row, slug="a/b"), dict(row, slug="a\\b"),
                    dict(row, ready="true"), dict(row, ready=1),
                    dict(row, sha256=None), dict(row, sha256="x")]
        for bad in variants:
            with self.subTest(row=bad), self.assertRaises(ValueError):
                ra.certificate_rows({"candidates": [bad]})
        for bad in (None, "Text", {}, 1):
            with self.subTest(candidates=bad), self.assertRaises(ValueError):
                ra.certificate_rows({"candidates": bad})

    def test_state_corruption_never_resets_history_to_empty(self):
        self.cert.parent.mkdir()
        for reader in (custody.ledger_laden, quarantine.load_state):
            for raw in ('{"hits":1,"hits":2}', '{"hits":'):
                with self.subTest(reader=reader.__name__, raw=raw):
                    self.cert.write_text(raw)
                    with self.assertRaises(ValueError):
                        reader(self.cert)
                    self.assertEqual(raw, self.cert.read_text())
            self.cert.unlink()
            self.assertEqual({}, reader(self.cert), "new ledger may start empty")


class SourceProofTests(Sandbox):
    def test_ready_needs_real_draft_bytes_not_a_summary_flag(self):
        row = self.draft()
        data = self.write_cert([row])
        data["ready"] = 6  # summary fields cannot manufacture five more articles
        ra.write_object(self.cert, data)
        self.assertEqual(1, gate.evaluate(self.cert, self.posts)[0])
        self.assertEqual(1, converge.cert_state(self.cert, self.posts)["ready"])
        self.assertTrue(any("ready stimmt nicht" in f
                            for f in ra.snapshot_findings(self.root)))
        index = self.posts / row["slug"] / "index.md"
        index.write_bytes(index.read_bytes() + b"changed\n")
        ready, _target, rows = gate.evaluate(self.cert, self.posts)
        self.assertEqual(0, ready)
        self.assertIn("SHA-256", rows[0]["reason"])
        self.assertEqual(6, ra.read_certificate(self.cert)["ready"], "readers never rewrite evidence")

    def test_deleted_live_blocked_retired_and_duplicate_yaml_drafts_do_not_count(self):
        for raw in (b"---\ndraft: false\nreserve: true\n---\nText.",
                    b"---\ndraft: true\n---\nreserve: true\n",
                    b"---\ndraft: true\nreserve: true\nreserve_blocked: reason\n---\nText.",
                    b"---\ndraft: true\nreserve: true\nreserve_retired: true\n---\nText.",
                    b"---\ndraft: true\nreserve: true\nreserve_published: 2026-10-07\n---\nText.",
                    b"---\ndraft: true\nreserve: true\ntags: [A]\ntags: [B]\n---\nText."):
            with self.subTest(raw=raw):
                self.write_cert([self.draft(raw=raw)])
                self.assertEqual(0, gate.evaluate(self.cert, self.posts)[0])
        self.write_cert([self.draft()])
        (self.posts / "kandidat" / "index.md").unlink()
        self.assertEqual(0, gate.evaluate(self.cert, self.posts)[0])

    def test_symlink_cannot_substitute_content_outside_the_pool(self):
        row = self.draft()
        index = self.posts / "kandidat" / "index.md"
        outside = self.root / "outside.md"
        outside.write_bytes(index.read_bytes())
        index.unlink()
        index.symlink_to(outside)
        self.assertIn("außerhalb", ra.candidate_problem(row, self.posts))

    def test_pool_never_prioritizes_a_hashless_ready_row(self):
        first = self.draft("first")
        second = self.draft("second")
        self.write_cert([dict(second, sha256=None)])
        paths = [self.posts / r["slug"] / "index.md" for r in (first, second)]
        with patch.object(pool, "ROOT", self.root):
            self.assertEqual(paths, pool._prefer_certified(paths))
        self.write_cert([second])
        with patch.object(pool, "ROOT", self.root):
            self.assertEqual(list(reversed(paths)), pool._prefer_certified(paths))

    def test_missing_invalid_future_and_old_timestamps_are_not_fresh(self):
        now = dt.datetime.now(dt.timezone.utc)
        for stamp in (None, "", "2026-10-08", "not-a-date",
                      (now + dt.timedelta(days=1)).isoformat(),
                      (now - dt.timedelta(hours=72)).isoformat()):
            with self.subTest(stamp=stamp):
                ra.write_object(self.cert, {"generated_at": stamp})
                self.assertFalse(gate.freshness(self.cert)[0])
        ra.write_object(self.cert, {"generated_at": now.isoformat()})
        self.assertTrue(gate.freshness(self.cert)[0])
        for override in ("nan", "inf", "-1", "0", "bad"):
            with self.subTest(override=override), patch.dict(
                    os.environ, {"RESERVE_CERT_MAX_AGE_H": override}):
                self.assertEqual(gate.CERT_MAX_AGE_H, gate.max_age_hours())

    def test_certification_restores_and_hashes_crlf_bytes_even_on_failure(self):
        raw = b"---\ndraft: true\nreserve: true\n---\nText.\n".replace(b"\n", b"\r\n")
        self.draft(raw=raw)
        index = self.posts / "kandidat" / "index.md"
        for gate_result in ((True, ""), RuntimeError("Gate down")):
            with self.subTest(result=gate_result), \
                    patch.object(readiness, "score_diagnosis", return_value=None), \
                    patch.object(readiness, "reserve_editorial_findings", return_value=[]), \
                    patch.object(readiness, "capture_gate") as capture:
                if isinstance(gate_result, Exception):
                    capture.side_effect = gate_result
                else:
                    capture.return_value = gate_result
                result = readiness.certify_one(index)
                self.assertEqual(raw, index.read_bytes())
                self.assertEqual(hashlib.sha256(raw).hexdigest(), result["sha256"])
                self.assertEqual(not isinstance(gate_result, Exception), result["ready"])

    def test_gate_cannot_certify_a_prehealed_version_but_hash_the_original(self):
        row = self.draft()
        index = self.posts / row["slug"] / "index.md"
        original = index.read_bytes()

        def prehealed(_index):
            index.write_bytes(index.read_bytes() + b"Healed.\n")
            return True, ""

        with patch.object(readiness, "score_diagnosis", return_value=None), \
                patch.object(readiness, "reserve_editorial_findings", return_value=[]), \
                patch.object(readiness, "capture_gate", side_effect=prehealed):
            result = readiness.certify_one(index)
        self.assertFalse(result["ready"])
        self.assertIn("Vorheilung", result["reason"])
        self.assertEqual(original, index.read_bytes())

    def test_duplicate_yaml_keys_block_before_the_production_gate(self):
        raw = "---\ndraft: true\nreserve: true\nauthor: Frank\nauthor: Other\n---\nText."
        self.assertTrue(readiness.reserve_editorial_findings(Path("unused"), raw))
        self.draft(raw=raw.encode())
        index = self.posts / "kandidat" / "index.md"
        with patch.object(readiness, "score_diagnosis", return_value=None), \
                patch.object(readiness.rp, "publish_one") as publish:
            self.assertFalse(readiness.certify_one(index)["ready"])
        publish.assert_not_called()

    def test_markdown_fence_inside_yaml_value_is_not_the_body_boundary(self):
        raw = '---\ndescription: "A --- B"\nauthor: Frank\n---\nBody.'
        with patch("redaktions_standard.reserve_quality_findings", return_value=[]) as detector:
            self.assertEqual([], readiness.reserve_editorial_findings(Path("unused"), raw))
        self.assertEqual("Body.", detector.call_args.args[0])


class AtomicWriteTests(Sandbox):
    def test_round_trip_and_permissions(self):
        ra.write_object(self.cert, {"text": "Prüfung", "nested": {"hits": 2}})
        self.cert.chmod(0o640)
        ra.write_object(self.cert, {"text": "neu"})
        self.assertEqual({"text": "neu"}, ra.read_object(self.cert))
        self.assertEqual(0o640, self.cert.stat().st_mode & 0o777)
        self.assertEqual([self.cert], list(self.cert.parent.iterdir()))

    def test_write_and_rename_failures_preserve_the_old_snapshot(self):
        ra.write_object(self.cert, {"old": True})
        old = self.cert.read_bytes()
        for method in ("fsync", "replace"):
            with self.subTest(method=method), patch.object(
                    ra.os, method, side_effect=OSError("storage failure")):
                with self.assertRaises(OSError):
                    ra.write_object(self.cert, {"new": True})
            self.assertEqual(old, self.cert.read_bytes())
            self.assertEqual([self.cert], list(self.cert.parent.iterdir()))

    def test_readback_and_serialization_failures_preserve_the_old_snapshot(self):
        ra.write_object(self.cert, {"old": True})
        old = self.cert.read_bytes()
        with patch.object(ra, "read_object", return_value={"corrupt": True}):
            with self.assertRaises(ValueError):
                ra.write_object(self.cert, {"new": True})
        with self.assertRaises(ValueError):
            ra.write_object(self.cert, {"number": float("nan")})
        self.assertEqual(old, self.cert.read_bytes())
        self.assertEqual([self.cert], list(self.cert.parent.iterdir()))

    def test_janitor_prunes_only_strict_states_and_writes_atomically(self):
        self.cert.parent.mkdir()
        self.cert.write_text('{"k": {"hits": 1}, "k": {"hits": 2}}')
        with patch.object(ra, "write_object") as atomic, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, janitor.prune_json_file(self.cert, lambda *_: True))
        atomic.assert_not_called()
        ra.write_object(self.cert, {"k": {"hits": 1}})
        with patch.object(ra, "write_object") as atomic:
            self.assertEqual(1, janitor.prune_json_file(self.cert, lambda *_: True))
        atomic.assert_called_once_with(self.cert, {})

    def test_all_state_writers_use_atomic_replacement(self):
        for writer in (custody.ledger_speichern, quarantine.save_state):
            with self.subTest(writer=writer.__name__), patch.object(ra, "write_object") as atomic:
                writer({"state": "kept"}, self.cert)
                atomic.assert_called_once_with(self.cert, {"state": "kept"}, sort_keys=True)


class ReaderCoverageTests(Sandbox):
    def test_corrupt_neighbor_memory_invalidates_an_otherwise_good_certificate(self):
        self.write_cert([self.draft()])
        neighbor = self.cert.parent / 'reserve-quarantine.json'
        for text in ('{"k":{},"k":{}}', '{"k":42}'):
            neighbor.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                ra.read_certificate(self.cert)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, gate.evaluate(self.cert, self.posts)[0])
            self.assertFalse(converge.cert_state(self.cert, self.posts)['exists'])

    def test_full_run_stops_before_mutation_of_corrupt_memory(self):
        self.write_cert([self.draft()])
        original = self.cert.read_bytes()
        neighbor = self.cert.parent / 'reserve-custody.json'
        neighbor.write_text('{"k":{},"k":{}}')
        with patch.object(readiness, 'ROOT', self.root), \
                patch.object(custody, 'heal_quiet') as heal, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(2, readiness.main())
            heal.assert_not_called()
        self.assertEqual(original, self.cert.read_bytes())
        self.assertEqual('{"k":{},"k":{}}', neighbor.read_text())

    def test_intake_never_turns_duplicate_custody_into_ownerless_stock(self):
        import reserve_intake
        ledger = self.cert.parent / "reserve-custody.json"
        ledger.parent.mkdir()
        ledger.write_text('{"k": {"slug":"a"}, "k": {"slug":"b"}}')
        with self.assertRaises(ValueError):
            reserve_intake.custody_slugs(self.root)
        with self.assertRaises(ValueError):
            reserve_intake.bestandsaufnahme(self.root)
        ledger.unlink()
        self.assertEqual(set(), reserve_intake.custody_slugs(self.root))

    def test_economy_never_accepts_duplicate_target_as_another_measurement(self):
        import reserve_economy
        self.cert.parent.mkdir()
        self.cert.write_text('{"target": 6, "target": 4}')
        self.assertIsNone(reserve_economy.zertifikat_ziel(self.cert))

    def test_healer_does_not_select_an_unsafe_or_merged_candidate(self):
        import lesbarkeit_heiler
        self.cert.parent.mkdir()
        for text in ('{"candidates":[{"slug":"../../outside","ready":false}]}',
                     '{"candidates":[],"candidates":[{}]}'):
            self.cert.write_text(text)
            with patch.object(lesbarkeit_heiler, 'BLOG_DIR', str(self.root)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual([], lesbarkeit_heiler.hole_blocked())

    def test_cockpit_uses_sources_and_marks_unproven_stock_not_green(self):
        import cockpit
        data = self.write_cert([self.draft()])
        data['ready'] = 6  # misleading summary must not appear as 6/6
        data['generated_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        ra.write_object(self.cert, data)
        self.assertEqual({'target': 6, 'ready': 1},
                         cockpit.load_reserve(self.cert, self.posts))
        (self.posts / 'kandidat' / 'index.md').write_text('Changed.')
        self.assertEqual(0, cockpit.load_reserve(self.cert, self.posts)['ready'])
        data['generated_at'] = 'invalid'
        ra.write_object(self.cert, data)
        status = cockpit.load_reserve(self.cert, self.posts)
        self.assertIsNone(status['ready'])
        level, lines, _ = cockpit.bucket_content({'steps': {}}, status)
        self.assertEqual('gelb', level)
        self.assertIn('ungeprüft', ' '.join(lines))
        self.cert.write_text('{"candidates":[],"candidates":[]}')
        self.assertIsNone(cockpit.load_reserve(self.cert, self.posts)['ready'])


class RepositoryContractTests(unittest.TestCase):
    def test_current_snapshot_is_whole_and_editorially_valid(self):
        self.assertEqual([], ra.snapshot_findings(ROOT))

    def test_snapshot_writers_cannot_bypass_atomic_replacement(self):
        for name in ("reserve_readiness.py", "reserve_recert.py"):
            with self.subTest(name=name):
                source = (SCRIPTS / name).read_text()
                self.assertIn("artifacts.write_object", source)
                self.assertIn("artifacts.certificate_rows", source)

    def test_pr_gate_covers_state_only_changes_and_runs_before_the_suite(self):
        workflow = (ROOT / ".github/workflows/publication-reliability-tests.yml").read_text()
        self.assertIn("'data/reserve-*.json'", workflow)
        self.assertIn("'.gitattributes'", workflow)
        self.assertLess(workflow.index("reserve_artifacts.py --check"),
                        workflow.index("unittest discover"))
        self.assertIn('"scripts/reserve_artifacts.py"', (SCRIPTS / "integrity_guard.py").read_text())

    def test_text_merges_cannot_create_a_snapshot_or_certified_draft_chimera(self):
        attrs = (ROOT / ".gitattributes").read_text()
        protected = ["data/" + name for name in ra.STATE_FILES]
        protected += ["content/posts/2026-12-01-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md"]
        for relative in protected:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)

                def git(*args, check=True):
                    return subprocess.run(["git", *args], cwd=root, check=check,
                                          capture_output=True, text=True,
                                          env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                                                   GIT_CONFIG_NOSYSTEM="1"), timeout=20)

                git("init", "-q", "-b", "base")
                git("config", "user.name", "Test")
                git("config", "user.email", "test@example.org")
                (root / ".gitattributes").write_text(attrs)
                file = root / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('{\n  "a": 1,\n  "b": 1\n}\n')
                git("add", ".")
                git("commit", "-qm", "base")
                git("branch", "other")
                file.write_text('{\n  "a": 2,\n  "b": 1\n}\n')
                git("commit", "-qam", "change a")
                git("checkout", "-q", "other")
                file.write_text('{\n  "a": 1,\n  "b": 2\n}\n')
                git("commit", "-qam", "change b")
                result = git("merge", "base", "--no-edit", check=False)
                self.assertNotEqual(0, result.returncode, "semantic snapshots must not be auto-merged")
                self.assertIn(relative, git("diff", "--name-only", "--diff-filter=U").stdout)
                for stage in (2, 3):
                    self.assertIsInstance(ra.parse_object(git("show", f":{stage}:{relative}").stdout), dict)


if __name__ == "__main__":
    unittest.main()
