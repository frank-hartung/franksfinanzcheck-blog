"""Vertrag der Workflow-JS-Wache (WF-829B / #922, 29.10.2026).

Der Vorfall: Der Squash-Merge von PR #943 traf eine gewanderte `main`
(Environment-Gate #935). In `.github/workflows/alert-on-failure.yml` standen
danach zwei Zeichenketten ohne Komma – `SyntaxError: Unexpected string` im
`script:`-Block von `actions/github-script`. Der Runner führt diesen Block als
Funktion aus: **jeder** Lauf des Fehler-Alertings starb an der Ausführung, und
damit der Kanal, der solche Ausfälle meldet. Aufgefallen ist es nur, weil ein
Python-Test den Block über `new Function` nachbaut.

Diese Datei hält die Wache fest, die das künftig selbst und an der richtigen
Stelle tut: `scripts/workflow_js_wache.py` kompiliert jeden Inline-Block.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import workflow_js_wache as wj  # noqa: E402

GUELTIG = """name: Probe
jobs:
  a:
    steps:
      - name: Job
        uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        with:
          script: |
            const teile = ['a', 'b'];
            await github.rest.issues.create({ title: teile.join(' ') });
"""

# Die echte Bruchstelle vom 29.10.2026: zwei Zeichenketten, kein Komma.
ZUSAMMENGESCHNITTEN = """name: Probe
jobs:
  a:
    steps:
      - name: Job
        uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        with:
          script: |
            const rat = [
              '4. Runbook: siehe A4/D2.'
              '1. **Fail-closed – gewollt, kein Betriebsausfall.**'
            ];
"""

OHNE_SKRIPT = """name: Probe
jobs:
  a:
    steps:
      - name: Job
        uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        id: leer
"""

LEER = """name: Probe
jobs:
  a:
    steps:
      - name: Job
        uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        with:
          script: |

      - name: danach
        run: echo ok
"""


def baum(inhalt: dict[str, str]) -> tempfile.TemporaryDirectory:
    ordner = tempfile.TemporaryDirectory(prefix="workflow-js-test-")
    ziel = Path(ordner.name) / ".github" / "workflows"
    ziel.mkdir(parents=True)
    for name, text in inhalt.items():
        (ziel / name).write_text(text, encoding="utf-8")
    return ordner


class Extraktion(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(wj._selftest(), 0)

    def test_block_und_grenze(self):
        text = GUELTIG + """      - name: danach
        run: echo fertig
"""
        bloecke, befunde = wj.bloecke(text, "probe.yml")
        self.assertEqual(len(bloecke), 1)
        self.assertEqual(befunde, [])
        self.assertIn("await github.rest.issues.create", bloecke[0].code)
        self.assertNotIn("danach", bloecke[0].code)

    def test_mit_auskommentierter_aktion(self):
        """`# v7` zwischen `name:` und `uses:` beendet den Schritt nicht."""
        text = """name: Probe
jobs:
  a:
    steps:
      - name: Job
        # v7 – unveränderlich gepinnt
        uses: actions/github-script@1111111111111111111111111111111111111111 # v9.0.0
        with:
          script: |
            const x = 1;
"""
        bloecke, befunde = wj.bloecke(text, "probe.yml")
        self.assertEqual((len(bloecke), befunde), (1, []))

    def test_schritt_ohne_skript_ist_ein_befund(self):
        _, befunde = wj.bloecke(OHNE_SKRIPT, "probe.yml")
        self.assertTrue(any(b.startswith("J2") for b in befunde), befunde)

    def test_leerer_block_ist_ein_befund(self):
        _, befunde = wj.bloecke(LEER, "probe.yml")
        self.assertTrue(any(b.startswith("J3") for b in befunde), befunde)


class ErkenntDenZusammenschnitt(unittest.TestCase):
    def test_der_echte_bruch_vom_29_10(self):
        with baum({"kaputt.yml": ZUSAMMENGESCHNITTEN}) as ordner:
            status, befunde, markdown = wj.pruefen(Path(ordner), node="node")
        self.assertEqual(status, 1)
        text = "\n".join(befunde)
        self.assertIn("J1", text)
        self.assertIn("kaputt.yml", text)
        self.assertIn("Workflow-Zeile", text, "Der Befund muss die Stelle nennen")
        self.assertIn("github-script-Block kompiliert nicht", text)
        self.assertIn("Befunde: **1**", markdown)

    def test_gueltiger_bestand_ist_gruen(self):
        with baum({"gut.yml": GUELTIG}) as ordner:
            status, befunde, markdown = wj.pruefen(Path(ordner), node="node")
        self.assertEqual((status, befunde), (0, []))
        self.assertIn("Blöcke geprüft: **1**", markdown)

    def test_ohne_node_wird_nicht_gruen_gemeldet(self):
        """Eine ausgefallene Messung ist kein Grün (Vertrag C33)."""
        with baum({"gut.yml": GUELTIG}) as ordner:
            status, befunde, _ = wj.pruefen(Path(ordner), node=None)
        self.assertEqual(status, 2)
        self.assertTrue(any(b.startswith("J0") for b in befunde), befunde)

    def test_prueferfehler_wird_zum_befund(self):
        with baum({"gut.yml": GUELTIG}) as ordner:
            status, befunde, _ = wj.pruefen(
                Path(ordner), node="node",
                prüfer=lambda code, node: (False, "block.js:7 (SyntaxError)"))
        self.assertEqual(status, 1)
        self.assertIn("Workflow-Zeile 13", " ".join(befunde))


class DerBestandIstSauber(unittest.TestCase):
    """Die Wache muss am echten Repository grün sein – sonst ist sie Deko."""

    def test_echter_bestand_kompiliert(self):
        status, befunde, _ = wj.pruefen()
        self.assertEqual((status, befunde), (0, []), befunde)

    def test_jeder_github_schritt_wird_erreicht(self):
        """Kein Workflow mit github-script darf ungeprüft bleiben."""
        bloecke, befunde = wj.sammeln(ROOT)
        self.assertGreaterEqual(len(bloecke), 14, "verdächtig wenige Blöcke")
        # Nur echte Schritte zählen – ein `uses:` im Kommentar ist keiner
        # (content-engine-v2.yml erklärt dort die alte Bauweise).
        echt = re.compile(r"^\s*(-\s+)?uses:\s*actions/github-script@", re.MULTILINE)
        aufrufe = sum(1 for p in (ROOT / ".github" / "workflows").glob("*.yml")
                      if echt.search(p.read_text(encoding="utf-8")))
        geprüfte_dateien = {b.datei for b in bloecke}
        self.assertEqual(len(geprüfte_dateien), aufrufe,
                         "Ein Workflow mit github-script wurde nicht erfasst")
        self.assertEqual(befunde, [])


class Ausgabe(unittest.TestCase):
    def test_cli_json_ist_maschinenlesbar(self):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = wj.main(["--json"])
        self.assertEqual(code, 0)
        daten = json.loads(puffer.getvalue())
        self.assertEqual(daten["status"], 0)
        self.assertEqual(daten["befunde"], [])

    def test_cli_check_meldet_gruen(self):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(wj.main(["--check"]), 0)
        self.assertIn("alle github-script-Blöcke kompilieren", puffer.getvalue())


class Verdrahtung(unittest.TestCase):
    """Ein Befund ohne Meldeweg ist die nächste stille Lücke."""

    def setUp(self):
        self.syntax = (ROOT / ".github" / "workflows" / "skript-syntax.yml").read_text(encoding="utf-8")
        self.paket = (ROOT / "package.json").read_text(encoding="utf-8")
        self.alert = (ROOT / ".github" / "workflows" / "alert-on-failure.yml").read_text(encoding="utf-8")

    def test_lauf_prueft_die_bloecke_und_sich_selbst(self):
        self.assertIn("workflow_js_wache.py --selftest", self.syntax)
        self.assertIn("workflow_js_wache.py --check", self.syntax)
        # Der Filter des Laufs deckt Workflows und Skripte ab (Trigger-Wache W1).
        for pfad in ("'.github/workflows/**.yml'", "'scripts/**.py'"):
            self.assertEqual(self.syntax.count(pfad), 2, "push und pull_request müssen gleich sein")

    def test_paketskripte_und_vertrag(self):
        self.assertIn("workflow_js_wache.py --check", self.paket)
        self.assertIn("scripts.tests.test_workflow_js_wache", self.paket)

    def test_rat_nennt_die_neue_pruefung(self):
        self.assertIn("workflow_js_wache.py", self.alert)


if __name__ == "__main__":
    unittest.main()
