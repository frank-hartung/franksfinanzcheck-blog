#!/usr/bin/env python3
"""Sicherheitsvertrag für externe Prozessstarts (Code-Scanning Alert #60).

Ein einzelnes ``shell=True`` reicht, um redaktionell oder aus der Umgebung
stammende Daten als Kommandozeile zu interpretieren. Diese Tests sichern die
Reparatur auf zwei Ebenen ab:

* der Watchdog transportiert dynamische Werte nur als separate argv-Argumente;
* die gesamte produktive Skript-Sammlung darf keine Shell-APIs verwenden.

Der zweite Test ist absichtlich AST-basiert statt eines Text-Greps. Kommentare,
Dokumentation und sichere ``shell=False``-Beispiele bleiben möglich, während
jede echte Rückkehr zu ``shell=True`` oder ``os.system`` den Build stoppt.
"""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SERVER_HELPER = ROOT / ".claude" / "skills" / "webapp-testing" / "scripts" / "with_server.py"
sys.path.insert(0, str(SCRIPTS))

import bot_watchdog as watchdog  # noqa: E402
import spam_guard  # noqa: E402


def _load_server_helper():
    spec = importlib.util.spec_from_file_location("safe_with_server", SERVER_HELPER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


with_server = _load_server_helper()


class CommandExecutionSecurityContract(unittest.TestCase):
    def test_production_scripts_never_delegate_to_a_shell(self):
        violations = []
        protected_sources = sorted([*SCRIPTS.glob("*.py"), SERVER_HELPER])
        for path in protected_sources:
            self.assertTrue(path.is_file(), f"Geschützte Prozess-Hilfe fehlt: {path}")
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                receiver = node.func.value
                function = node.func.attr
                if isinstance(receiver, ast.Name) and receiver.id == "os" and function in {
                    "system", "popen",
                }:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: os.{function}")
                if not (isinstance(receiver, ast.Name) and receiver.id == "subprocess"):
                    continue
                if function not in {"run", "Popen", "call", "check_call", "check_output"}:
                    continue
                for keyword in node.keywords:
                    if keyword.arg != "shell":
                        continue
                    if not (isinstance(keyword.value, ast.Constant)
                            and keyword.value.value is False):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: "
                            f"subprocess.{function}(shell=...)"
                        )
        self.assertEqual(
            violations,
            [],
            "Prozessstarts müssen Argumentvektoren verwenden; keine Shell-APIs erlauben.",
        )

    def test_watchdog_rejects_a_complete_command_string(self):
        with self.assertRaises(TypeError):
            watchdog.run_cmd("curl https://example.invalid")

    def test_watchdog_runner_passes_an_argv_vector_with_shell_disabled(self):
        completed = subprocess.CompletedProcess([], 0, "200", "")
        with mock.patch.object(watchdog.subprocess, "run", return_value=completed) as runner:
            self.assertEqual(watchdog.run_cmd(["curl", "--version"]), (0, "200", ""))

        self.assertEqual(runner.call_args.args[0], ["curl", "--version"])
        self.assertFalse(runner.call_args.kwargs["shell"])
        self.assertFalse(runner.call_args.kwargs["check"])

    def test_server_helper_parses_arguments_and_rejects_shell_chaining(self):
        self.assertEqual(
            with_server.parse_server_command('python -m http.server --directory "site preview"'),
            ["python", "-m", "http.server", "--directory", "site preview"],
        )
        with self.assertRaisesRegex(ValueError, "shell operators"):
            with_server.parse_server_command("cd backend && python server.py")

    def test_live_slug_is_one_encoded_curl_argument_not_shell_syntax(self):
        commands = []

        def fake_run(argv, timeout):
            commands.append((argv, timeout))
            return 0, "200", ""

        hostile_slug = 'neu"; touch /tmp/should-never-run; #'
        with mock.patch.object(watchdog, "run_cmd", side_effect=fake_run):
            ok, code = watchdog.check_live_site(hostile_slug)

        self.assertTrue(ok)
        self.assertEqual(code, "200")
        self.assertEqual(len(commands), 1)
        argv, timeout = commands[0]
        self.assertEqual(argv[:4], ["curl", "--location", "--silent", "--output"])
        self.assertIn("--", argv)
        self.assertEqual(timeout, 28)
        url = argv[-1]
        self.assertTrue(url.startswith("https://franksfinanzcheck.de/posts/"))
        self.assertIn("%22%3B%20touch%20%2Ftmp%2Fshould-never-run%3B%20%23", url)
        self.assertNotIn(hostile_slug, argv)

    def test_workflow_name_is_validated_before_gh_is_called(self):
        with mock.patch.object(watchdog, "run_cmd") as runner:
            count, message = watchdog.check_workflow_liveness("x.yml; curl attacker", hours=1)
        self.assertIsNone(count)
        self.assertEqual(message, "ungültiger Workflow-Dateiname")
        runner.assert_not_called()

    def test_feed_healer_uses_an_argv_vector_with_silenced_output(self):
        completed = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.object(spam_guard.subprocess, "run", return_value=completed) as runner:
            self.assertEqual(spam_guard._run_feed_healer("cadence_guard.py"), 0)

        argv = runner.call_args.args[0]
        kwargs = runner.call_args.kwargs
        self.assertEqual(argv, [
            sys.executable, str(ROOT / "scripts" / "cadence_guard.py"), "--fix",
        ])
        self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(kwargs["timeout"], 300)
        self.assertFalse(kwargs["check"])
        self.assertFalse(kwargs["shell"])

    def test_feed_healer_rejects_an_unapproved_script_without_starting_it(self):
        with mock.patch.object(spam_guard.subprocess, "run") as runner:
            self.assertEqual(spam_guard._run_feed_healer("untrusted.py"), 126)
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
