#!/usr/bin/env python3
"""Schnittstellen-Vertrag des Copy-Editing-Gates (Reparatur 31.10.2026).

HINTERGRUND
-----------
Das PR-Gate lief nach #977 rot, weil `copy_editing_gate.py --selftest` den
Arbeitsbaum beschmutzte (C15). Ursache war nicht der Gate selbst, sondern
`lektor_guard.py`: Es kannte keinen reinen Beweispfad, `--selftest` startete
den VOLLEN Bestandslauf und hängte eine Zeile an `data/lektor_history.jsonl`.
Damit war die Beweisführung genau der Vorgang, den C15 verbietet.

Zweiter Befund derselben Prüfung: Der Gate reichte EINEN gemeinsamen
Argument-Satz an alle sechs Engines – auch `--file` und `--include-drafts` an
Engines, die den Schalter gar nicht auswerten. Ein Lauf „ein einzelner
Artikel“ prüfte in Wahrheit den ganzen Bestand, und niemand konnte das im
Log sehen. Diese Suite hält beide Fehlerklassen geschlossen:

  1. `reiner Beweislauf`  – `--selftest` prüft Fälle und schreibt nichts.
  2. `Schalter-Vertrag`   – nur was die Engine wirklich kann, wird übergeben;
                            Abweichungen zwischen Tabelle und Quelltext sind rot.

Ausführung:  python3 -m unittest scripts.tests.test_copy_editing_gate_schnittstelle -v
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import copy_editing_gate as gate  # noqa: E402


class SchalterVertragTest(unittest.TestCase):
    """Die Fähigkeitstabelle ist die Wahrheit über die Engine-Schnittstelle."""

    def test_tabelle_stimmt_mit_dem_quelltext(self):
        """Beide Drift-Richtungen sind rot – sonst prüft der Gate anders als er sagt."""
        self.assertEqual(gate._faehigkeiten_pruefen(), [])

    def test_jede_engine_kann_einzeldatei(self):
        """`--file` ist Pflicht: Ohne Einzeldatei-Modus wäre der Gate-Scope falsch."""
        for engine in gate.SCRIPTS:
            self.assertIn(
                "--file", gate.ENGINE_FAEHIGKEITEN[engine],
                f"{engine} kennt keinen Einzeldatei-Modus – scope=file wäre gelogen.",
            )

    def test_nur_unterstuetzte_schalter_werden_uebergeben(self):
        """Alles an: jede Engine bekommt exakt ihre Fähigkeiten, nichts Fremdes."""
        for engine in gate.SCRIPTS:
            args = gate._engine_args(
                engine, fix=True, strict=True, new_only=True,
                include_drafts=True, only_file="content/posts/x/index.md",
            )
            uebergeben = {a for a in args if a.startswith("--")}
            fremd = uebergeben - gate.ENGINE_FAEHIGKEITEN[engine] - {"--file"}
            self.assertEqual(fremd, set(), f"{engine} bekam fremde Schalter: {sorted(fremd)}")

    def test_lesende_engine_bekommt_kein_fix(self):
        """readability_check heilt nie – ein --fix wäre eine Lüge im Log."""
        args = gate._engine_args(
            "readability", fix=True, strict=False, new_only=False,
            include_drafts=False, only_file=None,
        )
        self.assertNotIn("--fix", args)
        self.assertNotIn("--strict", args)

    def test_engines_ohne_json_bekommen_kein_json(self):
        """hardcases/lektor liefern Markdown-Reports; `--json` wäre ein Placebo."""
        for engine in ("hardcases", "lektor"):
            args = gate._engine_args(
                engine, fix=False, strict=False, new_only=False,
                include_drafts=False, only_file=None,
            )
            self.assertNotIn("--json", args, f"{engine} kann kein JSON-Report.")

    def test_einzeldatei_ohne_engine_support_bricht_ab(self):
        """Negativfall: Statt stillem Bestandslauf muss der Gate laut abbrechen."""
        with mock.patch.dict(
            gate.ENGINE_FAEHIGKEITEN, {"readability": {"--json", "--new-only"}}, clear=False
        ):
            with self.assertRaises(SystemExit) as ctx:
                gate._engine_args(
                    "readability", fix=False, strict=False, new_only=False,
                    include_drafts=False, only_file="content/posts/x/index.md",
                )
        self.assertEqual(ctx.exception.code, 2)

    def test_tabelle_darf_keinen_schalter_erfinden(self):
        """Negativfall: Tabelle verspricht, was die Engine nicht kann → Befund."""
        with mock.patch.dict(
            gate.ENGINE_FAEHIGKEITEN,
            {"readability": gate.ENGINE_FAEHIGKEITEN["readability"] | {"--strict"}},
            clear=False,
        ):
            befunde = gate._faehigkeiten_pruefen()
        self.assertTrue(
            any("--strict" in b and "readability" in b for b in befunde),
            f"Erfundener Schalter blieb unbemerkt: {befunde}",
        )

    def test_tabelle_darf_keinen_schalter_verschweigen(self):
        """Negativfall: Engine kann mehr, Tabelle weiß es nicht → Befund."""
        with mock.patch.dict(
            gate.ENGINE_FAEHIGKEITEN,
            {"grammar": gate.ENGINE_FAEHIGKEITEN["grammar"] - {"--file"}},
            clear=False,
        ):
            befunde = gate._faehigkeiten_pruefen()
        self.assertTrue(
            any("--file" in b and "grammar" in b for b in befunde),
            f"Verschwiegener Schalter blieb unbemerkt: {befunde}",
        )


class BeweislaufSchreibtNichtTest(unittest.TestCase):
    """C15: Ein Selbsttest, der Dateien anfasst, ist kein Beweis."""

    def test_gate_selftest_laesst_den_arbeitsbaum_unveraendert(self):
        vorher = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        if vorher.returncode != 0:
            self.skipTest("kein git-Arbeitsbaum – Schreibschutz nicht messbar")

        lauf = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "copy_editing_gate.py"), "--selftest"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        )
        nachher = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(lauf.returncode, 0, f"Selbsttest rot:\n{lauf.stdout}\n{lauf.stderr}")
        self.assertEqual(
            vorher.stdout, nachher.stdout,
            "Der Beweislauf hat den Arbeitsbaum verändert (C15) – "
            f"vorher:\n{vorher.stdout}\nnachher:\n{nachher.stdout}",
        )

    def test_lektor_selftest_schreibt_keine_historie(self):
        """Der Ursprung des C15-Befunds: lektor_guard kannte keinen Beweispfad."""
        historie = ROOT / "data" / "lektor_history.jsonl"
        vorher = historie.read_bytes() if historie.exists() else None
        lauf = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "lektor_guard.py"), "--selftest"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300,
        )
        nachher = historie.read_bytes() if historie.exists() else None
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        self.assertEqual(vorher, nachher, "lektor_guard --selftest hat Geschichte geschrieben.")
        self.assertIn("kein Schreiben", lauf.stdout)


class EinzeldateiReichweiteTest(unittest.TestCase):
    """`--file` prüft genau eine Datei im eigenen Blog – nicht irgendetwas."""

    def test_datei_ausserhalb_des_repos_wird_abgewiesen(self):
        for skript in ("lektor_guard.py", "hardcases_guard.py"):
            lauf = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / skript), "--file", "/etc/hostname"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(lauf.returncode, 2, f"{skript} prüfte ein Fremdziel: {lauf.stdout}")
            self.assertIn("außerhalb des Repos", lauf.stdout)

    def test_fehlende_datei_wird_abgewiesen(self):
        for skript in ("lektor_guard.py", "hardcases_guard.py"):
            lauf = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / skript), "--file",
                 "content/posts/gibt-es-nicht/index.md"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(lauf.returncode, 2, f"{skript}: {lauf.stdout}")
            self.assertIn("existiert nicht", lauf.stdout)


if __name__ == "__main__":
    unittest.main()
