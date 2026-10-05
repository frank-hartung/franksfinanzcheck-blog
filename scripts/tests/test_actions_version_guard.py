#!/usr/bin/env python3
"""Vertragstests für scripts/actions_version_guard.py.

Hintergrund: Dependabot-PR #571 (actions/setup-python v5 → v7) traf nur einen
Teil der Workflows. Diese Tests halten fest, dass die Wache Drift findet,
sie heilt, Absichtliches (SHA-Pins, lokale Actions, Kommentare) nie anfasst –
und dass der Bestand des Repositories drift-frei ist.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import actions_version_guard as avg  # noqa: E402


class SelftestTestCase(unittest.TestCase):
    def test_selftest_passes(self):
        self.assertEqual(avg.run_selftest(), [])


class ParserTestCase(unittest.TestCase):
    def test_parses_step_and_plain_form(self):
        uses = avg.parse_uses(
            "jobs:\n"
            "  a:\n"
            "    steps:\n"
            "      - uses: actions/checkout@v5\n"
            "      - name: Python\n"
            '        uses: "actions/setup-python@v7"\n'
            "      - uses: ./.github/actions/install-hugo\n"
            "#       uses: actions/checkout@v4\n"
        )
        self.assertEqual(
            [(u.action, u.ref) for u in uses],
            [
                ("actions/checkout", "v5"),
                ("actions/setup-python", "v7"),
                ("./.github/actions/install-hugo", None),
            ],
        )

    def test_sha_pin_and_local_detection(self):
        self.assertTrue(avg.is_pin("11d5960a326750d5838078e36cf38b85af677262"))
        self.assertFalse(avg.is_pin("v7"))
        self.assertFalse(avg.is_pin(None))
        self.assertTrue(avg.is_local("./.github/actions/hugo-build"))
        self.assertTrue(avg.is_local("docker://alpine:3"))
        self.assertFalse(avg.is_local("actions/checkout"))


class KanonTestCase(unittest.TestCase):
    def test_highest_major_wins(self):
        uses = [
            avg.Use("a.yml", 1, "actions/setup-python", "v6"),
            avg.Use("b.yml", 1, "actions/setup-python", "v7"),
            avg.Use("c.yml", 1, "actions/setup-python", "v5"),
        ]
        findings, kanon = avg.analyze(uses)
        self.assertEqual(kanon["actions/setup-python"], "v7")
        self.assertEqual({f.path for f in findings}, {"a.yml", "c.yml"})
        self.assertTrue(all(f.soll == "v7" and f.rule == "A1" for f in findings))

    def test_sha_pin_is_never_a_finding(self):
        uses = [
            avg.Use("a.yml", 1, "actions/checkout", "v5"),
            avg.Use("b.yml", 1, "actions/checkout", "11d5960a326750d5838078e36cf38b85af677262"),
        ]
        findings, kanon = avg.analyze(uses)
        self.assertEqual(findings, [])
        self.assertEqual(kanon["actions/checkout"], "v5")

    def test_moving_ref_is_a2(self):
        findings, _ = avg.analyze([
            avg.Use("a.yml", 1, "foo/bar", "main"),
            avg.Use("b.yml", 1, "foo/bar", "v2"),
        ])
        self.assertEqual([f.rule for f in findings], ["A2"])


class FixTestCase(unittest.TestCase):
    KANON = {"actions/setup-python": "v7", "actions/checkout": "v5"}

    def test_fixes_only_the_reference(self):
        src = (
            "      - name: Python\n"
            "        # Kommentar bleibt stehen\n"
            "        uses: actions/setup-python@v6\n"
            "        with:\n"
            '          python-version: "3.11"\n'
        )
        out, n = avg.fix_text(src, self.KANON)
        self.assertEqual(n, 1)
        self.assertIn("uses: actions/setup-python@v7", out)
        self.assertIn("# Kommentar bleibt stehen", out)
        self.assertIn('python-version: "3.11"', out)

    def test_never_touches_pins_locals_or_comments(self):
        src = (
            "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
            "        uses: ./.github/actions/install-hugo\n"
            "#       uses: actions/checkout@v4\n"
        )
        out, n = avg.fix_text(src, self.KANON)
        self.assertEqual((out, n), (src, 0))

    def test_idempotent(self):
        once, _ = avg.fix_text("      - uses: actions/checkout@v4\n", self.KANON)
        twice, n = avg.fix_text(once, self.KANON)
        self.assertEqual(n, 0)
        self.assertEqual(twice, once)


class BestandTestCase(unittest.TestCase):
    """Der eigentliche Dauerschutz: das Repo selbst bleibt drift-frei."""

    def test_repository_is_drift_free(self):
        findings, _ = avg.analyze(avg.collect(ROOT))
        self.assertEqual(
            findings, [],
            "Actions-Versions-Drift – heilen mit: python3 scripts/actions_version_guard.py --fix",
        )

    def test_setup_python_is_uniform(self):
        refs = {
            u.ref for u in avg.collect(ROOT)
            if u.action == "actions/setup-python" and not avg.is_pin(u.ref)
        }
        self.assertEqual(refs, {"v7"}, f"setup-python uneinheitlich: {refs}")

    def test_gate_runs_in_pull_request_workflow(self):
        wf = (ROOT / ".github/workflows/integrity-lock.yml").read_text(encoding="utf-8")
        self.assertIn("actions_version_guard.py --gate", wf)
        self.assertIn("actions_version_guard.py --selftest", wf)


if __name__ == "__main__":
    unittest.main()
