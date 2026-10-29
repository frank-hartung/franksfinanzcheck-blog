#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow-Vertrag: Ein toter Bau wird als toter Bau gemeldet (WF-9FD5).

DER VORFALL (Meldung #901, 26.10.2026)
---------------------------------------
Der wöchentliche Layout-AI-Lauf auf `main` scheiterte am Schritt
„Website bauen". Danach stand in der Meldung:

    Statisches Audit: Exit 1 · Browser-Audit: Exit 0

Beide Zahlen waren **erfunden**. Das statische Audit war gar nicht gelaufen
(`skipped`), und im Skript stand `Number(process.env.STATIC_EXIT ?? '1')` –
ein fehlender Wert wurde stillschweigend zur 1, also zu „kritische Befunde".
Der Mensch vor der Meldung suchte daraufhin Layout-Fehler, die es nicht gab.

Diese Tests halten die Reparatur fest:
  1. Der Bau hat eine `id`, sein Fehlschlag wird toleriert (damit Bericht,
     Meldung und Zusammenfassung noch geschrieben werden) und sein Exit-Code
     landet in `BAU_EXIT`.
  2. Statisches Audit und Browser-Audit laufen nur nach grünem Bau.
  3. Die Meldung kennt den Zustand „Bau gescheitert" und behauptet dort
     KEINE Befunde; `STATIC_EXIT` hat keinen erfundenen Standardwert mehr.
  4. Der Schluss-Schritt wird WIRKLICH ausgeführt (bash) und muss in jeder
     Lage die Wahrheit sagen – acht Kombinationen, acht Erwartungen.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "layout-ai.yml"
ACTION = ROOT / ".github" / "actions" / "hugo-build" / "action.yml"

try:
    import yaml
except ImportError:                                       # pragma: no cover
    yaml = None


@unittest.skipUnless(yaml is not None, "PyYAML fehlt – Workflow nicht lesbar")
class WorkflowStrukturTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.steps = cls.wf["jobs"]["layout-audit"]["steps"]
        cls.nach_name = {s.get("name"): s for s in cls.steps}

    def _schritt(self, anfang: str) -> dict:
        for schritt in self.steps:
            if (schritt.get("name") or "").startswith(anfang):
                return schritt
        raise AssertionError(f"Schritt „{anfang}*“ nicht gefunden")

    def test_bau_hat_id_und_tolerierten_fehlschlag(self) -> None:
        bau = self._schritt("Website bauen")
        self.assertEqual("build", bau.get("id"))
        self.assertTrue(bau.get("continue-on-error"),
                        "Ohne continue-on-error sterben Bericht und Meldung "
                        "mit dem Bau – genau das war der Ausfall vom 26.10.")

    def test_bau_exit_wird_verankert(self) -> None:
        schritt = self._schritt("Bauergebnis verankern")
        self.assertIn("steps.build.outputs.rc", schritt["env"]["BAU_RC"])
        self.assertIn("BAU_EXIT=", schritt["run"])
        self.assertIn("GITHUB_ENV", schritt["run"])
        # Kein erfundener Standardwert: leer heißt „unbekannt", nicht 0.
        self.assertIn('bau_rc="unbekannt"', schritt["run"])

    def test_audits_laufen_nur_nach_gruenem_bau(self) -> None:
        for name in ("Statisches Layout-Audit", "Browser-Audit"):
            schritt = self._schritt(name)
            self.assertIn("env.BAU_EXIT == '0'", schritt.get("if", ""),
                          f"{name} läuft auch ohne gebaute Seite")

    @staticmethod
    def _ohne_kommentarzeilen(js: str) -> str:
        """Nur der CODE zählt. Ein Kommentar, der den alten Fehler erklärt,
        darf nicht als Fehler gewertet werden – und ein Fehler, der nur im
        Kommentar steht, ist keiner."""
        return "\n".join(z for z in js.splitlines()
                         if not z.lstrip().startswith("//"))

    def test_meldung_kennt_den_bauausfall(self) -> None:
        schritt = self._schritt("Issue aktualisieren")
        skript = self._ohne_kommentarzeilen(schritt["with"]["script"])
        self.assertNotIn("STATIC_EXIT ?? '1'", skript,
                         "Der erfundene Standardwert ist zurück")
        self.assertIn("bauOk", skript)
        self.assertIn("der Bau ist gescheitert", skript)
        self.assertIn("nicht gelaufen", skript)
        # Die Ursache reist über die Umgebung, nicht über den Skripttext –
        # so kann ein Fehlertext nie als Code ausgeführt werden.
        self.assertIn("erste-fehlerzeile", schritt["env"]["BAU_URSACHE"],
                      "Die Meldung bekommt die Ursache nicht geliefert")

    def test_action_liefert_die_erste_fehlerzeile(self) -> None:
        action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
        self.assertIn("erste-fehlerzeile", action["outputs"])
        bau = [s for s in action["runs"]["steps"] if s.get("id") == "bauen"][0]
        self.assertIn('echo "erste-fehlerzeile=${SAUBER}"', bau["run"])

    def test_summary_nennt_den_bauausfall(self) -> None:
        schritt = self._schritt("Bericht in die Job-Summary")
        self.assertIn("Kein Bau – keine Messung", schritt["run"])
        self.assertIn("BAU_URSACHE", schritt["run"])


@unittest.skipUnless(shutil.which("bash"), "bash fehlt")
@unittest.skipUnless(yaml is not None, "PyYAML fehlt")
class SchlussSchrittWahrheitstabelleTest(unittest.TestCase):
    """Der Schluss-Schritt wird ausgeführt, nicht gelesen.

    Eine Prüfung, die nur Wörter zählt, ist mit einem Kommentar zu betrügen.
    Hier entscheidet das Verhalten: Exit 0 nur dann, wenn Bau, statisches
    Audit und Browser-Audit wirklich grün sind.
    """

    @classmethod
    def setUpClass(cls) -> None:
        wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.rumpf = [s for s in wf["jobs"]["layout-audit"]["steps"]
                     if (s.get("name") or "").startswith("Lauf rot stellen")][0]["run"]

    def _lauf(self, env: dict) -> subprocess.CompletedProcess:
        basis = {k: v for k, v in os.environ.items()
                 if k not in ("BAU_EXIT", "STATIC_EXIT", "BROWSER_EXIT")}
        with tempfile.NamedTemporaryFile("w", suffix=".md") as summary:
            basis.update(env)
            basis["GITHUB_STEP_SUMMARY"] = summary.name
            return subprocess.run(["bash", "-e", "-c", self.rumpf], env=basis,
                                  capture_output=True, text=True)

    def test_wahrheitstabelle(self) -> None:
        faelle = [
            ("grün", {"BAU_EXIT": "0", "STATIC_EXIT": "0", "BROWSER_EXIT": "0"}, 0),
            ("Bau tot (26.10.)", {"BAU_EXIT": "1"}, 1),
            ("Bau tot, Browser lief", {"BAU_EXIT": "1", "BROWSER_EXIT": "2"}, 1),
            ("Bau grün, statisches Audit nie gelaufen", {"BAU_EXIT": "0"}, 1),
            ("Bau grün, Browser übersprungen", {"BAU_EXIT": "0", "STATIC_EXIT": "0",
                                                "BROWSER_EXIT": "2"}, 0),
            ("Bau grün, Browser ohne Ergebnis", {"BAU_EXIT": "0", "STATIC_EXIT": "0"}, 1),
            ("Bau grün, Browser-Werkzeugfehler", {"BAU_EXIT": "0", "STATIC_EXIT": "0",
                                                  "BROWSER_EXIT": "7"}, 1),
            ("Bau grün, statische Befunde", {"BAU_EXIT": "0", "STATIC_EXIT": "1",
                                             "BROWSER_EXIT": "0"}, 1),
        ]
        for name, env, soll in faelle:
            with self.subTest(fall=name):
                lauf = self._lauf(env)
                self.assertEqual(soll, lauf.returncode,
                                 f"{name}: Exit {lauf.returncode} statt {soll}\n{lauf.stdout}")

    def test_bauausfall_wird_als_solcher_benannt(self) -> None:
        lauf = self._lauf({"BAU_EXIT": "1",
                           "BAU_URSACHE": "mapping value is not allowed"})
        self.assertEqual(1, lauf.returncode)
        self.assertIn("Bau gescheitert", lauf.stdout)
        self.assertIn("mapping value is not allowed", lauf.stdout)
        self.assertNotIn("kritische Befunde", lauf.stdout,
                         "Ein toter Bau darf nicht als Befund gemeldet werden")


if __name__ == "__main__":
    unittest.main()
