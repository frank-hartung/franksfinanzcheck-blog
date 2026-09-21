"""Wachen für die Workflow-Dateien selbst (Bau-Unfall 21.09.2026).

WARUM (Issue #338, Layout-Automatisierung):
Beim Umbau von `.github/workflows/layout-ai.yml` stand der Doppelpunkt in
einem ungeschützten Step-Namen (`- name: … (identisch zur Produktion:
`hugo --minify`)`). Das ist gültiges Aussehen, aber kein gültiges YAML –
GitHub legt die Datei mit „workflow file issue" still, der Lauf stirbt,
bevor der erste Step startet. Der Fehler war nur sichtbar, weil GitHub
für den Push einen Fehl-Lauf anlegt: kein Test, kein Lint, kein Signal
im Repo.

Diese Datei schließt die Lücke. Sie prüft ALLE Workflows auf:
  1. gültiges YAML (jede Datei, jede Zeile),
  2. keine doppelten Schlüssel (PyYAML nimmt sonst still den letzten –
     genau so verschwindet ein Step, ohne dass es auffällt),
  3. vorhandenen `on:`-Auslöser,
  4. je Job `runs-on` und Steps, die entweder `run` oder `uses` tragen,
  5. Step-Namen ohne YAML-Fallen (Doppelpunkt + Leerzeichen in einem
     unquotierten Skalar wäre wieder ein Parserfehler).

Läuft ohne Netz und ohne GitHub – Teil von `python3 -m unittest discover
-s scripts/tests`.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:                                     # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

STEP_KEYS = {"name", "id", "if", "uses", "with", "run", "env", "shell",
             "working-directory", "continue-on-error", "timeout-minutes",
             "strategy", "permissions"}


class UniqueKeyLoader(yaml.SafeLoader if yaml else object):
    """YAML-Loader, der doppelte Schlüssel NICHT still überschreibt."""

    def construct_mapping(self, node, deep=False):
        seen = {}
        for key_node, _value in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(
                    f"doppelter Schlüssel {key!r} in Zeile "
                    f"{key_node.start_mark.line + 1}")
            seen[key] = True
        return super().construct_mapping(node, deep=deep)


@unittest.skipIf(yaml is None, "PyYAML nicht installiert")
class WorkflowYamlTests(unittest.TestCase):
    def test_workflows_vorhanden(self):
        self.assertGreaterEqual(len(WORKFLOWS), 20,
                                "Workflow-Ordner wirkt leer – Pfad prüfen?")

    def test_yaml_parst_und_struktur_stimmt(self):
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                try:
                    data = yaml.load(text, Loader=UniqueKeyLoader)
                except Exception as err:                # Parser ODER Doppelkey
                    self.fail(f"{path.name}: {err}")
                self.assertIsInstance(data, dict, f"{path.name}: kein Mapping")
                # `on:` wird von YAML zu True (boolescher Schlüssel)
                trigger = data.get("on", data.get(True))
                self.assertIsNotNone(trigger, f"{path.name}: kein `on:`-Auslöser")
                jobs = data.get("jobs")
                self.assertIsInstance(jobs, dict, f"{path.name}: keine Jobs")
                for job_name, job in jobs.items():
                    with self.subTest(workflow=path.name, job=job_name):
                        self.assertIn("runs-on", job,
                                      f"{path.name}/{job_name}: ohne runs-on")
                        steps = job.get("steps")
                        if job.get("uses"):                 # Reusable-Workflow
                            continue
                        self.assertIsInstance(steps, list,
                                              f"{path.name}/{job_name}: keine Steps")
                        for i, step in enumerate(steps, 1):
                            if not isinstance(step, dict):
                                continue
                            self.assertTrue(
                                "run" in step or "uses" in step,
                                f"{path.name}/{job_name} Step {i}: "
                                "weder run noch uses")
                            unknown = set(step) - STEP_KEYS
                            self.assertFalse(
                                unknown,
                                f"{path.name}/{job_name} Step {i}: "
                                f"unbekannte Schlüssel {sorted(unknown)}")

    def test_eingebettetes_javascript_ist_syntaktisch_gueltig(self):
        """`actions/github-script` führt JS aus einem YAML-Block aus. Steht der
        Step auf `continue-on-error: true` (tut er im Layout-Workflow), bliebe
        ein Syntaxfehler unsichtbar: der Step wird still übersprungen, das
        Issue wird nie gepflegt. Also prüfen wir den Block wie Code."""
        if shutil.which("node") is None:
            self.skipTest("node nicht installiert")
        found = 0
        for path in WORKFLOWS:
            data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
            for job_name, job in (data.get("jobs") or {}).items():
                for i, step in enumerate(job.get("steps") or [], 1):
                    uses = str(step.get("uses", ""))
                    script = (step.get("with") or {}).get("script")
                    if "github-script" not in uses or not script:
                        continue
                    found += 1
                    # github-script führt den Block in einer async-Funktion
                    # aus – dort ist `await` auf Top-Level erlaubt. `node
                    # --check` prüft eine Datei aber als Modul/Skript und
                    # würde jedes `await` anmeckern; deshalb dieselbe Hülle
                    # wie die Action sie baut.
                    with tempfile.NamedTemporaryFile(
                            "w", suffix=".js", encoding="utf-8", delete=False) as fh:
                        fh.write("(async () => {\n" + script + "\n})();\n")
                        tmp = fh.name
                    try:
                        proc = subprocess.run(["node", "--check", tmp],
                                              capture_output=True, text=True)
                    finally:
                        os.unlink(tmp)
                    self.assertEqual(
                        proc.returncode, 0,
                        f"{path.name}/{job_name} Step {i}: JS-Syntaxfehler in "
                        f"github-script:\n{proc.stderr}")
        self.assertGreater(found, 0, "Kein github-script-Step gefunden?")

    def test_step_namen_sind_yaml_sicher(self):
        """Doppelpunkt + Leerzeichen in einem unquotierten Step-Namen ist ein
        Parserfehler – genau der Unfall vom 21.09.2026. Quotierte Namen sind
        erlaubt (dann ist der Doppelpunkt Teil der Zeichenkette)."""
        offender = re.compile(r"^\s*-\s+name:\s+[^\"'].*:\s")
        for path in WORKFLOWS:
            for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if offender.search(line):
                    self.fail(f"{path.name}:{no}: unquotierter Step-Name mit "
                              f"': ' – Anführungszeichen setzen: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
