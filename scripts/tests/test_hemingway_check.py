"""Vertragstests für den kostenlosen Hemingway-Editor-Begleiter."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import hemingway_check as hc  # noqa: E402


class HemingwayAdapterTests(unittest.TestCase):
    def test_points_to_free_editor_and_has_no_network_client(self):
        self.assertEqual(hc.TOOL_NAME, "Hemingway Editor")
        self.assertEqual(hc.TOOL_URL, "https://hemingwayapp.com/")
        source = (ROOT / "scripts" / "hemingway_check.py").read_text(encoding="utf-8")
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("API_KEY", source)

    # ------------------------------------------------------------------
    #  Der Vorgänger dieses Tests lautete:
    #
    #      result = hc.main(["--selftest"])
    #      self.assertIn("hemingway_check --selftest OK", output.getvalue())
    #
    #  Er war grün, prüfte aber nichts: Die Zeichenkette entstand erst durch
    #  die Suchen-und-Ersetzen-Logik des Adapters, die „readability_check"
    #  im Text der ENGINE durch „hemingway_check" tauschte. Der Test
    #  bestätigte also die Fälschung, die er hätte aufdecken sollen.
    #  Ersatz: Der Selbsttest muss grün sein UND belegen, was er geprüft hat.
    # ------------------------------------------------------------------
    def test_selftest_is_own_and_green(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = hc.main(["--selftest"])
        text = output.getvalue()
        self.assertEqual(result, 0, text)
        self.assertIn("A1–A7", text)
        self.assertIn("Fälschungsprobe", text)
        self.assertIn("Engine-Selbsttest readability_check grün", text)

    def test_selftest_does_not_merely_forward_the_flag(self):
        """Der Adapter darf --selftest nicht an die Engine durchreichen.

        Täte er es, wäre sein grünes Häkchen wieder nur die umbenannte
        Zeile der Engine – und kein Satz über ihn selbst.
        """
        gesehen = []

        def fake_main():
            gesehen.extend(sys.argv[1:])
            print("✅ readability_check --selftest OK")

        with patch.object(hc._engine, "main", fake_main):
            with contextlib.redirect_stdout(io.StringIO()):
                hc.main(["--selftest"])
        self.assertEqual(
            gesehen, [],
            "--selftest wurde weitergereicht statt selbst beantwortet")

    def test_selftest_catches_a_swallowed_exit_code(self):
        """Empfindlichkeitsnachweis: eine Wache, die nie rot wird, ist Deko.

        Hier wird der Adapter real sabotiert (Exit-Codes verschlucken) und
        der Selbsttest MUSS das melden.
        """
        quelle = (ROOT / "scripts" / "hemingway_check.py").read_text(encoding="utf-8")
        kaputt = quelle.replace("status = int(exc.code or 0)", "status = 0", 1)
        self.assertNotEqual(kaputt, quelle, "Sabotage-Anker nicht gefunden")
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(ROOT / "scripts", Path(tmp) / "scripts")
            ziel = Path(tmp) / "scripts" / "hemingway_check.py"
            ziel.write_text(kaputt, encoding="utf-8")
            lauf = subprocess.run([sys.executable, str(ziel), "--selftest"],
                                  capture_output=True, text=True, cwd=tmp,
                                  timeout=120)
        self.assertNotEqual(lauf.returncode, 0,
                            "Sabotierter Adapter bleibt grün:\n" + lauf.stdout)
        self.assertIn("A2", lauf.stdout)

    def test_json_mode_stays_machine_readable(self):
        """Kosmetik darf maschinenlesbare Ausgabe nicht anfassen."""
        roh = json.dumps({"werkzeug": "readability_check",
                          "befund": "Lesbarkeits-Wache"})

        def fake_main():
            print(roh, end="")

        output = io.StringIO()
        with patch.object(hc._engine, "main", fake_main):
            with contextlib.redirect_stdout(output):
                hc.main(["--json"])
        daten = json.loads(output.getvalue())
        self.assertEqual(daten["werkzeug"], "readability_check")

    def test_engine_really_implements_the_flag(self):
        """Ohne echtes --selftest in der Engine wäre jeder Aufruf ein Gate-Lauf.

        Genau diese Verwechslung (publish_gate.py, 18.09.2026) stufte beinahe
        einen Live-Artikel auf draft herab.
        """
        quelle = Path(hc._engine.__file__).read_text(encoding="utf-8")
        self.assertTrue("'--selftest'" in quelle or '"--selftest"' in quelle)

    def test_cli_arguments_are_forwarded_without_editing_content(self):
        forwarded = []

        def fake_main():
            forwarded.extend(sys.argv[1:])
            print("Lesbarkeits-Audit: 0 Artikel")

        output = io.StringIO()
        with patch.object(hc._engine, "main", fake_main):
            with contextlib.redirect_stdout(output):
                result = hc.main(["--new-only"])

        self.assertEqual(result, 0)
        self.assertEqual(forwarded, ["--new-only"])
        self.assertIn("Hemingway-Lesbarkeitscheck", output.getvalue())


class HemingwayWorkflowTests(unittest.TestCase):
    def test_workflow_has_no_external_model_or_token(self):
        workflow = (ROOT / ".github" / "workflows" / "hemingway-check.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("name: Hemingway-Lesbarkeitscheck (Mo/Mi/Fr)", workflow)
        self.assertIn("scripts/hemingway_check.py --selftest", workflow)
        self.assertIn("scripts/hemingway_check.py \\", workflow)
        self.assertIn("--gate-bestand", workflow)
        self.assertIn("HEMINGWAY-REPORT.md", workflow)
        self.assertNotIn("PUTER_AUTH_TOKEN", workflow)
        self.assertNotIn("@heyputer", workflow)
        self.assertNotIn("Claude", workflow)

    def test_old_lane_is_gone(self):
        legacy_slug = "claude" + "-stilpolitur"
        legacy_module = "claude" + "_stilpolitur"
        for path in (
            ROOT / ".github" / "workflows" / f"{legacy_slug}.yml",
            ROOT / "scripts" / f"{legacy_module}.py",
            ROOT / "scripts" / f"{legacy_module}_wirkung.py",
            ROOT / "docs" / f"ANLEITUNG-{legacy_slug.upper()}.md",
        ):
            self.assertFalse(path.exists(), f"alte Lane noch vorhanden: {path}")


if __name__ == "__main__":
    unittest.main()
