#!/usr/bin/env python3
"""Vertragstests für den SHA-Pin-Vertrag seit PR #1014.

Der alte Tag-Vergleich war nach der SHA-Pflicht blind. Diese Proben halten
insbesondere Teil-Bumps, CodeQL-Unteraktionen, Composite-Actions und den
Unterschied zwischen Kommentar-Korrektur und Release-Auswahl fest.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import actions_version_guard as avg  # noqa: E402

OLD = avg.Pin("5fda3b95a4ea91299a34e894583c3862153e4b97", "v7.0.0")
NEW = avg.Pin("6d4fd22b20465ccc0f7354476588e8df7c9ca0e0", "v7.1.0")
ACTION = "actions/setup-python"


def use(path: str, pin: avg.Pin, action: str = ACTION, line: int = 1) -> avg.Use:
    return avg.Use(path, line, action, pin.ref, pin.version)


def line(pin: avg.Pin, action: str = ACTION) -> str:
    return f"        uses: {action}@{pin.ref} # {pin.version}\n"


class ParserTest(unittest.TestCase):
    def test_step_plain_quotes_and_comments(self):
        text = (
            "jobs:\n  build:\n    steps:\n"
            f"      - uses: {ACTION}@{OLD.ref} # v7.0.0\n"
            f'        uses: "{ACTION}@{OLD.ref}"  # v7.0.0\n'
            "        uses: ./.github/actions/install-hugo\n"
            f"#       uses: {ACTION}@{NEW.ref} # v7.1.0\n"
        )
        uses = avg.parse_uses(text)
        self.assertEqual(len(uses), 3)
        self.assertEqual([u.version for u in uses[:2]], ["v7.0.0", "v7.0.0"])
        self.assertEqual([u.line for u in uses[:2]], [4, 5])
        self.assertTrue(avg.is_local(uses[2].action))

    def test_only_full_lowercase_sha_is_a_pin(self):
        self.assertTrue(avg.is_pin(OLD.ref))
        for ref in (None, "v7", "main", "master", "latest", "HEAD",
                    OLD.ref[:39], OLD.ref.upper(), OLD.ref + "0"):
            with self.subTest(ref=ref):
                self.assertFalse(avg.is_pin(ref))

    def test_invalid_version_comments_are_not_versions(self):
        for comment in ("# v7", "# 7.0.0", "# v7.0.0-beta.1", "# v7.0.0 weiterer Text", ""):
            with self.subTest(comment=comment):
                source = f"uses: {ACTION}@{OLD.ref} {comment}\n"
                self.assertIsNone(avg.parse_uses(source)[0].version)


class PinContractTest(unittest.TestCase):
    def test_uniform_pin_is_green(self):
        findings, kanon = avg.analyze([use("a.yml", OLD), use("b.yml", OLD)])
        self.assertEqual(findings, [])
        self.assertEqual(kanon[ACTION], OLD)

    def test_partial_sha_bump_is_red_even_when_comments_look_plausible(self):
        findings, kanon = avg.analyze([use("a.yml", OLD), use("b.yml", NEW)])
        self.assertEqual([f.rule for f in findings], ["A1", "A1"])
        self.assertEqual(kanon, {}, "kein Release aus Kommentar oder SHA-Sortierung raten")

    def test_same_sha_with_different_versions_is_red(self):
        findings, kanon = avg.analyze([
            use("a.yml", OLD), use("b.yml", avg.Pin(OLD.ref, NEW.version)),
        ])
        self.assertEqual([f.rule for f in findings], ["A3", "A3"])
        self.assertEqual(kanon, {})

    def test_codeql_subactions_share_one_release(self):
        findings, _ = avg.analyze([
            use("codeql.yml", OLD, "github/codeql-action/init"),
            use("codeql.yml", NEW, "github/codeql-action/analyze", 2),
            use("codeql.yml", NEW, "github/codeql-action/upload-sarif", 3),
        ])
        self.assertEqual([f.rule for f in findings], ["A1", "A1", "A1"])

    def test_different_actions_do_not_share_a_pin(self):
        findings, _ = avg.analyze([
            use("a.yml", OLD), use("a.yml", NEW, "actions/setup-node", 2),
        ])
        self.assertEqual(findings, [])

    def test_tags_and_branches_are_not_accepted_as_pins(self):
        for ref in ("v7.0.0", "v7", "main", "master", "latest", "HEAD", None):
            with self.subTest(ref=ref):
                findings, _ = avg.analyze([avg.Use("a.yml", 1, ACTION, ref, "v7.0.0")])
                self.assertEqual([f.rule for f in findings], ["A2"])

    def test_missing_comment_is_red_but_repairable_for_unique_sha(self):
        uses = [use("a.yml", OLD), avg.Use("b.yml", 2, ACTION, OLD.ref)]
        findings, kanon = avg.analyze(uses)
        self.assertEqual([f.rule for f in findings], ["A3"])
        fixed, count = avg.fix_text(f"uses: {ACTION}@{OLD.ref}\n", kanon)
        self.assertEqual((fixed, count), (line(OLD).lstrip(), 1))
        self.assertEqual(avg.analyze(avg.parse_uses(fixed))[0], [])

    def test_local_and_docker_are_out_of_scope(self):
        for action in ("./.github/actions/hugo-build", "docker://alpine:3"):
            with self.subTest(action=action):
                self.assertEqual(avg.analyze([avg.Use("a.yml", 1, action, None)])[0], [])


class RepairTest(unittest.TestCase):
    def test_repairs_only_comment_and_preserves_format(self):
        source = (
            "      - name: Python\r\n"
            "        # Kommentar bleibt stehen\r\n"
            f'        uses: "{ACTION}@{OLD.ref}"  # v6.0.0\r\n'
            "        with:\r\n          python-version: '3.12'\r\n"
        )
        fixed, count = avg.fix_text(source, {ACTION: OLD})
        self.assertEqual(count, 1)
        self.assertIn(f'"{ACTION}@{OLD.ref}"  # v7.0.0\r\n', fixed)
        self.assertIn("# Kommentar bleibt stehen", fixed)
        self.assertIn("python-version: '3.12'", fixed)
        self.assertEqual(fixed.count("\r\n"), source.count("\r\n"))

    def test_never_selects_between_releases(self):
        source = line(OLD) + line(NEW)
        _, kanon = avg.analyze(avg.parse_uses(source))
        self.assertEqual(avg.fix_text(source, kanon), (source, 0))

    def test_does_not_touch_unpinned_or_local_or_commented_lines(self):
        source = (
            f"uses: {ACTION}@{NEW.ref} # v7.1.0\n"
            "uses: ./.github/actions/install-hugo\n"
            f"# uses: {ACTION}@{NEW.ref} # v7.1.0\n"
        )
        self.assertEqual(avg.fix_text(source, {ACTION: OLD}), (source, 0))

    def test_fix_is_idempotent(self):
        once, _ = avg.fix_text(f"uses: {ACTION}@{OLD.ref}\n", {ACTION: OLD})
        twice, count = avg.fix_text(once, {ACTION: OLD})
        self.assertEqual((twice, count), (once, 0))

    def test_dry_run_does_not_write_and_real_fix_is_narrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / ".github/workflows/a.yml"
            path.parent.mkdir(parents=True)
            source = f"uses: {ACTION}@{OLD.ref}\n"
            path.write_text(source)
            avg.apply_fix(root, {ACTION: OLD}, dry_run=True)
            self.assertEqual(path.read_text(), source)
            avg.apply_fix(root, {ACTION: OLD})
            self.assertEqual(path.read_text(), line(OLD).lstrip())


class RepositoryContractTest(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(avg.run_selftest(), [])

    def test_repository_is_drift_free(self):
        uses = avg.collect(ROOT)
        findings, kanon = avg.analyze(uses)
        self.assertEqual(findings, [], avg.report(findings, kanon))
        external = {avg.repository(u.action) for u in uses if not avg.is_local(u.action)}
        self.assertTrue(external)
        self.assertEqual(set(kanon), external, "jede fremde Action braucht genau einen Pin")

    def test_scan_includes_workflows_and_composite_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ("workflows", "actions/example"):
                path = root / ".github" / directory / "action.yml"
                path.parent.mkdir(parents=True)
                path.write_text(line(OLD))
            self.assertEqual(len(avg.collect(root)), 2)
            self.assertEqual(avg.analyze(avg.collect(root))[0], [])

    def test_gate_is_wired_before_online_contract_check(self):
        workflow = (ROOT / ".github/workflows/integrity-lock.yml").read_text()
        self.assertLess(workflow.index("actions_version_guard.py --selftest"),
                        workflow.index("actions_version_guard.py --gate"))
        self.assertLess(workflow.index("actions_version_guard.py --gate"),
                        workflow.index("workflow_vertrag_wache.py --online --gate"))

    def test_empty_tree_and_unresolved_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(avg.main(["--root", tmp, "--gate"]), 1)
            root = Path(tmp)
            path = root / ".github/workflows/a.yml"
            path.parent.mkdir(parents=True)
            path.write_text(line(OLD) + line(NEW))
            self.assertEqual(avg.main(["--root", tmp, "--fix", "--gate"]), 1)
            self.assertEqual(path.read_text(), line(OLD) + line(NEW))

    def test_json_reports_machine_readable_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / ".github/workflows/a.yml"
            path.parent.mkdir(parents=True)
            path.write_text(line(OLD) + line(NEW))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = avg.main(["--root", tmp, "--gate", "--json"])
            self.assertEqual(result, 1)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["drift"], 2)
            self.assertEqual(payload["kanon"], {})


if __name__ == "__main__":
    unittest.main()
