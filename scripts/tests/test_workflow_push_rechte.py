#!/usr/bin/env python3
"""Push-Rechte-Vertrag der Workflows (Reparatur 31.10.2026).

HINTERGRUND
-----------
Die Sprach-Qualitäts-Pipeline committete die History und rief danach

    git push || true

Sie stand aber auf `permissions: contents: read`. Der Push konnte also
NIE gelingen – und weil der Fehler mit `|| true` verschluckt wurde, sah der
Lauf monatelang grün aus, während die History im Runner verfiel. Zwei Fehler
in einer Zeile: fehlendes Recht (der Push ist technisch unmöglich) und
geschlucktes Ergebnis (niemand merkt es).

Der Push selbst läuft jetzt über `scripts/git_sync.sh --push-only`
(Push-Wache, `test_push_wache.py`). Diese Suite sichert die zweite Hälfte:
**Wer committet und pusht, muss schreiben dürfen.** Das gilt als Klasse für
alle Workflows, nicht nur für die reparierte Datei – ein neuer Bot mit
demselben Muster fällt sofort auf.

Dazu die Beweiskette des Gate-Schritts: Der Exit-Code des Copy-Editing-Gates
muss wirklich erfasst werden. `cmd || true` und danach `echo $?` liest den
Exit von `true` (immer 0) – der Strict-Modus war damit wirkungslos.

Ausführung:  python3 -m unittest scripts.tests.test_workflow_push_rechte -v
"""
from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

try:
    import yaml
except ImportError:  # pragma: no cover – CI hat PyYAML, lokal ggf. nicht
    yaml = None


def _lade(pfad: Path) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}


def _effektive_rechte(daten: dict, job: dict):
    """Job-Rechte schlagen Workflow-Rechte; None = keine Deklaration."""
    return job.get("permissions", daten.get("permissions"))


class PushRechteTest(unittest.TestCase):
    """Klasse: committen + pushen ohne `contents: write` ist ein toter Push."""

    def setUp(self):
        if yaml is None:
            self.skipTest("PyYAML nicht installiert")

    def test_jeder_pushende_schritt_darf_schreiben(self):
        verstoesse = []
        for pfad in sorted(glob.glob(str(WORKFLOWS / "*.yml"))):
            daten = _lade(Path(pfad))
            for job_id, job in (daten.get("jobs") or {}).items():
                for schritt in job.get("steps") or []:
                    lauf = schritt.get("run") or ""
                    if "git_sync.sh --push-only" not in lauf or "git commit" not in lauf:
                        continue
                    rechte = _effektive_rechte(daten, job)
                    if not (isinstance(rechte, dict) and rechte.get("contents") == "write"):
                        verstoesse.append(
                            f"{Path(pfad).name}:{job_id}:{schritt.get('name', '?')} "
                            f"(permissions={rechte!r})"
                        )
        self.assertEqual(
            verstoesse, [],
            "Workflow committet und pusht, darf aber nicht schreiben – der Push "
            f"kann nie gelingen: {verstoesse}",
        )

    def test_sprach_pipeline_pusht_ueber_die_push_wache(self):
        """Die reparierte Datei selbst: sanktionierter Push-Weg, echtes Schreibrecht."""
        daten = _lade(WORKFLOWS / "sprach-qualitaet-pipeline.yml")
        self.assertEqual(daten.get("permissions", {}).get("contents"), "write")
        text = (WORKFLOWS / "sprach-qualitaet-pipeline.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/git_sync.sh --push-only", text)
        # Kein roher Push, kein verschluckter Push – beides fängt zusätzlich die
        # Push-Wache ab; hier steht es sichtbar an der Datei.
        self.assertNotRegex(text, r"(?m)^\s*git push\b")
        self.assertNotRegex(text, r"git_sync\.sh[^|\n]*\|\|\s*true")


class GateExitErfassungTest(unittest.TestCase):
    """C15-Anschluss: Die Pipeline muss den Gate-Exit wirklich sehen."""

    def setUp(self):
        if yaml is None:
            self.skipTest("PyYAML nicht installiert")
        self.daten = _lade(WORKFLOWS / "sprach-qualitaet-pipeline.yml")

    def _schritt(self, name: str) -> dict:
        for schritt in self.daten["jobs"]["sprach-qualitaet"]["steps"]:
            if schritt.get("name") == name:
                return schritt
        self.fail(f"Schritt »{name}« fehlt in der Pipeline.")

    def test_keine_github_expressions_im_run_block(self):
        """Template-Injection-Freiheit (Klasse, zusätzlich zur Sammelprüfung)."""
        for schritt in self.daten["jobs"]["sprach-qualitaet"]["steps"]:
            lauf = schritt.get("run")
            if isinstance(lauf, str):
                self.assertNotIn("${{", lauf, f"Schritt »{schritt.get('name')}« interpoliert im run-Block.")

    def test_gate_exit_wird_echt_erfasst(self):
        lauf = self._schritt("Copy-Editing-Gate (Selbsttest + alle Engines)")["run"]
        # Kein `|| true` direkt am Gate – sonst geht der Code verloren.
        self.assertNotRegex(
            lauf, r"copy_editing_gate\.py[^\n]*\|\|",
            "Der Gate-Exit wird mit `||` verschluckt.",
        )
        # `$?` muss unmittelbar nach dem Gate gelesen werden, nicht nach `true`.
        self.assertRegex(lauf, r"set \+e[\s\S]*copy_editing_gate\.py[\s\S]*RC=\$\?")
        self.assertIn("gate_exit_code=$RC", lauf)
        self.assertNotIn("gate_exit_code=$?", lauf)

    def test_status_kennt_sabotage_und_verstoss(self):
        lauf = self._schritt("Qualitäts-Status auswerten")["run"]
        self.assertIn("qualitaet=sabotage", lauf)
        self.assertIn("qualitaet=verstoß", lauf)
        # Unbekannter/fehlender Code darf nicht als „ok“ durchrutschen.
        self.assertRegex(lauf, r"-z \"\$GATE_EXIT\"")
        # Ein unbekannter Code fällt in den Fallback-Zweig (fail-closed).
        self.assertRegex(lauf, r"(?m)^\s*\*\)")

    def test_labels_werden_vor_dem_issue_angelegt(self):
        """C12: fehlendes Label = HTTP 422, das Issue entsteht nie (#209)."""
        namen = [s.get("name", "") for s in self.daten["jobs"]["sprach-qualitaet"]["steps"]]
        label_idx = next(i for i, n in enumerate(namen) if n.startswith("Labels sicherstellen"))
        issue_idx = next(i for i, n in enumerate(namen) if n.startswith("Issue bei Qualitätsverstoß"))
        self.assertLess(label_idx, issue_idx, "Labels müssen vor dem Issue angelegt werden.")

        lauf = self.daten["jobs"]["sprach-qualitaet"]["steps"][label_idx]["run"]
        for label in ("qualitaet", "sprach-qualitaet", "automatisiert"):
            self.assertRegex(lauf, rf"gh label create {re.escape(label)}\b")
        self.assertEqual(lauf.count("--force"), 3)


if __name__ == "__main__":
    unittest.main()
