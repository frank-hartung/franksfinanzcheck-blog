#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow-Vertrags-Wache: der stille Totalausfall darf nicht zurückkommen.

HINTERGRUND (Vorgang WF-SPRACHE, 31.10.2026)
--------------------------------------------
Die Sprach-Qualitäts-Pipeline stand monatelang in der Lauf-Liste – mit
20 von 20 roten Läufen, jedem in derselben Sekunde beendet und jedem mit
NULL Jobs. Der Grund war eine einzige Zeile:

    labels: ["qualitaet", "sprach-qualitaet", "automatisiert"]

`peter-evans/create-issue-from-file` deklariert `labels` als
kommagetrennte ZEICHENKETTE. GitHub prüft das beim Einlesen der Datei:

    Invalid workflow file: .github/workflows/sprach-qualitaet-pipeline.yml#L1
    (Line: 205, Col: 19): A sequence was not expected

Damit wird die Datei als GANZES verworfen. Kein Job, kein Check-Run am
Commit, keine Meldung, kein Hinweis im PR. Der Ausfall war unsichtbar –
und genau deshalb monatelang.

Warum keine bestehende Wache das gefunden hat: `yaml.safe_load` liefert
für diesen Block einen vollkommen normalen Dict. Ob die Action den Wert
als Liste verträgt, weiß PyYAML nicht. `trigger_wache.py` liest nur den
`on:`-Ausschnitt, `actions_version_guard.py` lässt SHA-Pins per Regel A3
absichtlich unangetastet.

DIESE SUITE HÄLT DIE KLASSE GESCHLOSSEN
---------------------------------------
* Der konkrete Fall (Liste statt Zeichenkette) wird erkannt.
* Der Fall ist im echten Repo nicht mehr vorhanden.
* Die toten Pins der Reparatur sind nicht zurückgekehrt (V1, offline über
  den mitgelieferten Vertragsspeicher – Netz wird im Test NICHT gebraucht).
* Die Wache selbst ist nicht stumm: eine kaputte Kopie des echten
  Workflows wird als kaputt erkannt (Sabotage-Probe).
* `--gate` liefert Exit 1 nur bei Befund, sonst 0 (CI-Vertrag).

Ausführung:
    python3 -m unittest scripts.tests.test_workflow_vertrag_wache -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "workflow_vertrag_wache.py"
PIPELINE = ROOT / ".github" / "workflows" / "sprach-qualitaet-pipeline.yml"

sys.path.insert(0, str(ROOT / "scripts"))

import workflow_vertrag_wache as wache  # noqa: E402


class VertragsWacheTest(unittest.TestCase):
    """Klasse: eine formal gültige Datei, die GitHub trotzdem verwirft."""

    def test_selbsttest_ist_gruen(self):
        ergebnis = subprocess.run(
            [sys.executable, str(SKRIPT), "--selftest"],
            capture_output=True, text=True,
        )
        self.assertEqual(ergebnis.returncode, 0,
                         f"Selbsttest rot:\n{ergebnis.stdout}\n{ergebnis.stderr}")

    def test_der_echte_fall_wird_erkannt(self):
        """`labels` als YAML-Liste bei einer String-Eingabe → V2."""
        text = """
name: X
on: [push]
jobs:
  a:
    runs-on: ubuntu-24.04
    steps:
      - name: Melden
        uses: peter-evans/create-issue-from-file@433e51abf769039ee20ba1293a088ca19d573b7f
        with:
          title: "T"
          content-filepath: R.md
          labels: ["qualitaet", "sprach-qualitaet"]
"""
        befunde, daten = wache.pruefe_struktur(text, "probe.yml")
        self.assertEqual(befunde, [], "Strukturprüfung darf hier nichts melden")
        treffer = wache.pruefe_vertraege(
            ROOT, [("probe.yml", daten)],
            {"peter-evans/create-issue-from-file@433e51abf769039ee20ba1293a088ca19d573b7f":
             {"labels": "string", "title": "string", "content-filepath": "string"}},
            online=False,
        )
        self.assertEqual(len(treffer), 1, treffer)
        self.assertIn("A sequence was not expected", treffer[0].text)

    def test_zeichenkette_ist_erlaubt(self):
        text = PIPELINE.read_text(encoding="utf-8")
        befunde, _ = wache.pruefe_struktur(text, "sprach-qualitaet-pipeline.yml")
        self.assertEqual(befunde, [])

    def test_pipeline_hat_keine_liste_bei_labels(self):
        text = PIPELINE.read_text(encoding="utf-8")
        self.assertNotIn('labels: ["qualitaet"', text,
                         "`labels` muss eine kommagetrennte Zeichenkette sein")

    def test_pipeline_pins_sind_aufloesbar(self):
        """Die zwei toten Pins der Reparatur dürfen nicht zurückkehren.

        Geprüft über den echten Task ohne Netz: ein Pin, den der Anbieter
        nicht kennt, ist der einzige Weg zu einem V1-Befund – also darf die
        Datei offline keinen erzeugen, wenn alle Pins im Vertragsspeicher
        stehen. Zusätzlich die namentliche Sperre gegen die alten Werte.
        """
        text = PIPELINE.read_text(encoding="utf-8")
        for tot in ("959985ac0a2ee023b3cc256977ec1a093aa4a0bf",
                    "49538c08a0826eef0d640c58a59e7a5e2b50aaef"):
            self.assertNotIn(tot, text,
                             f"toter Pin ist zurück: {tot[:12]}…")
        self.assertIn("peter-evans/create-issue-from-file@433e51abf769", text)
        self.assertIn("actions/upload-artifact@cf430e030ddb", text)

    def test_alle_workflows_offline_ohne_befund(self):
        """V3–V6 gelten für den ganzen Bestand, nicht nur für die Pipeline."""
        befunde, geprueft, _ = wache.pruefen(ROOT, online=False)
        self.assertGreater(geprueft, 50)
        self.assertEqual(befunde, [], "\n".join(str(b) for b in befunde))

    def test_gate_vertrag(self):
        ergebnis = subprocess.run(
            [sys.executable, str(SKRIPT), "--gate"], capture_output=True, text=True)
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)

    def test_json_ausgabe_ist_maschinenlesbar(self):
        ergebnis = subprocess.run(
            [sys.executable, str(SKRIPT), "--json"], capture_output=True, text=True)
        daten = json.loads(ergebnis.stdout)
        self.assertIn("befunde", daten)
        self.assertIn("geprueft", daten)
        self.assertEqual(daten["befunde"], [])

    def test_wache_laeuft_nach_der_pyyaml_installation(self):
        """Im PR-Gate MUSS die Wache hinter der PyYAML-Installation stehen.

        Am 31.10.2026 stand sie beim ersten Versuch davor: `setup-python`
        bringt PyYAML nicht mit, der Selbsttest wurde rot (V0 „PyYAML
        fehlt") – der Befund war richtig, aber er sah aus wie ein Fehler in
        der Wache. Diese Probe hält die Reihenfolge fest.
        """
        text = (ROOT / ".github" / "workflows" / "integrity-lock.yml").read_text(
            encoding="utf-8")
        stelle_wache = text.find("workflow_vertrag_wache.py --selftest")
        stelle_pyyaml = text.find("requirements-ci.txt")
        self.assertGreater(stelle_wache, 0, "Wache fehlt im PR-Gate")
        self.assertGreater(stelle_pyyaml, 0, "PyYAML-Installation fehlt im PR-Gate")
        self.assertLess(stelle_pyyaml, stelle_wache,
                        "Wache steht VOR der PyYAML-Installation → Selbsttest rot")

    def test_ohne_pyyaml_klare_meldung_statt_folgebefunde(self):
        """Fehlt PyYAML, gibt es EINE verständliche Meldung – nicht zehn."""
        umgebung = {
            "PYTHONPATH": str(ROOT / "scripts"),
        }
        # Ein Import-Blocker im Subprozess: yaml wird nicht gefunden.
        skript = (
            "import runpy, sys\n"
            "class B:\n"
            "    def find_module(self, n, p=None): return self if n == 'yaml' else None\n"
            "    def load_module(self, n): raise ImportError(n)\n"
            "sys.meta_path.insert(0, B())\n"
            "sys.argv = ['w', '--selftest']\n"
            f"runpy.run_path(r'{SKRIPT}', run_name='__main__')\n"
        )
        ergebnis = subprocess.run([sys.executable, "-c", skript],
                                  capture_output=True, text=True, env=umgebung)
        self.assertEqual(ergebnis.returncode, 2, "ohne PyYAML muss fail-closed gelten")
        self.assertIn("PyYAML fehlt", ergebnis.stdout)
        self.assertNotIn("nicht erkannt", ergebnis.stdout,
                         "keine Folgebefunde – nur die eine klare Meldung")

    def test_sabotage_probe(self):
        """Eine kaputte Kopie des echten Workflows muss auffallen.

        Ohne diese Probe wäre die Suite ein Grünsager: sie würde auch dann
        bestehen, wenn die Wache jede Datei durchwinkt.
        """
        text = PIPELINE.read_text(encoding="utf-8")
        kaputt = text.replace("jobs:", "job:", 1)
        befunde, _ = wache.pruefe_struktur(kaputt, "kaputt.yml")
        self.assertTrue(any(b.regel == "V3" for b in befunde), befunde)

        kaputt2 = text.replace('labels: "qualitaet, sprach-qualitaet, automatisiert"',
                               'labels: ["qualitaet", "sprach-qualitaet", "automatisiert"]')
        self.assertNotEqual(kaputt2, text)
        befunde, daten = wache.pruefe_struktur(kaputt2, "kaputt2.yml")
        self.assertEqual(befunde, [])
        treffer = wache.pruefe_vertraege(
            ROOT, [("kaputt2.yml", daten)],
            {"peter-evans/create-issue-from-file@433e51abf769039ee20ba1293a088ca19d573b7f":
             {"labels": "string", "title": "string", "content-filepath": "string",
              "assignees": "string"}},
            online=False,
        )
        self.assertTrue(any(t.regel == "V2" for t in treffer), treffer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
