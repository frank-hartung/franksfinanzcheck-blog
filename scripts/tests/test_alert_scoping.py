"""Regressions-Tests des Fehler-Alerting-Produktions-Scopings (Fehlalarm #343).

Vorfall vom 21.09.2026 (docs/INCIDENT-2026-09-21-layout-ai-fehlalarm-343.md):
Issue #343 meldete „Workflow fehlgeschlagen: Layout-AI" für einen
`pull_request`-Lauf des Arbeitszweigs arena/01a0c4dc-…, der mitten in der
Entwicklung rot war und 57 Minuten später aus sich heraus grün wurde.
Produktion (main) war zu keinem Zeitpunkt betroffen. Drei Strukturfehler
des alten Alertings („jeder rote Lauf = Issue", „jeder grüne Lauf = Issue
zu") werden seitdem durch Regeln ersetzt, und DIESE DATEI ist die Wache,
dass die Regeln nicht still zurückgebaut werden:

  1. PROD-SCOPING ALARM: Der alarm-Job meldet nur Läufe auf dem
     Default-Branch und niemals pull_request-Events – der Vergleich muss
     VOR jeder Issue-Erzeugung im Skript stehen (früher return).
  2. PROD-SCOPING RESOLVE: Der resolve-Job schließt Alarme nur bei Grün
     AUF DEM DEFAULT-BRANCH (symmetrische Regel; ein grüner Zweig-Lauf
     ist kein Produktionsbeweis – genau so wurde #343 falschgeschlossen).
  3. TITEL-VERTRAG: „⚠️ Workflow fehlgeschlagen: <name> (<conclusion>)"
     + Label auto-report bleiben byte-stabil – resolve-Job, Aufräum-
     Workflow (cleanup_issues.sh) und Herzschlag-Tests parsen darauf.
  4. WACHT-LISTEN-VERTRAG: on.workflow_run.workflows + types: [completed]
     bleiben lesbar für alerting_heartbeat.gelistete_workflows (SSOT des
     Alerting-Herzschlags; Handkopien sind die Fehlerklasse vom 18.09.).
  5. DIAGNOSE: Der Alarm trägt die fehlgeschlagenen Jobs/Schritte ins
     Issue (Lehre aus INCIDENT-2026-09-19: „die Meldung riet, das Log
     hätte es gewusst").
  6. VERHALTEN: Die Verhaltens-Simulation (scripts/tests/sim/
     alert_scoping_sim.mjs) führt das Inline-Skript mit gestubbtem
     github-script-Kontext aus – neun Szenarien, inkl. exakter
     #343-Reproduktion, Phantom-Filter (#218), Dedupe und Fail-open.

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

YAML_PATH = REPO / ".github" / "workflows" / "alert-on-failure.yml"

TITEL_PRÄFIX = "⚠️ Workflow fehlgeschlagen: "


def _text() -> str:
    return YAML_PATH.read_text(encoding="utf-8")


def _kommentarfrei(text: str) -> str:
    """YAML-/JS-Kommentarzeilen raus – Zusagen müssen im CODE stehen,
    nicht nur als Überschrift (Muster aus governance_contract.c14)."""
    return "\n".join(l for l in text.splitlines()
                     if not l.lstrip().startswith("#")
                     and not l.lstrip().startswith("//"))


class ProdScopingAlarm(unittest.TestCase):
    """Vertrag 1: Alarm nur für Produktions-Läufe."""

    def setUp(self):
        self.raw = _text()
        self.code = _kommentarfrei(self.raw)

    def test_scoping_vergleich_vorhanden(self):
        # default_branch wird aus dem Payload gelesen (nie hartkodiert
        # geraten) und gegen head_branch verglichen.
        self.assertIn("repository.default_branch", self.code)
        self.assertRegex(self.code, r"branch\s*===\s*defaultBranch")

    def test_pull_request_events_ausgeschlossen(self):
        self.assertRegex(self.code, r"event\s*!==\s*'pull_request'")

    def test_scoping_steht_vor_der_issue_erzeugung(self):
        # Der frühe return muss VOR issues.create stehen – sonst läuft
        # die Erzeugung für Dev-Läufe trotzdem.
        pos_scoping = self.code.find("isProdRun")
        pos_create = self.code.find("issues.create({")
        self.assertGreater(pos_scoping, -1, "isProdRun-Wächter fehlt im alarm-Skript")
        self.assertGreater(pos_create, -1, "issues.create fehlt im alarm-Skript")
        self.assertLess(pos_scoping, pos_create,
                        "PROD-SCOPING muss vor der Issue-Erzeugung prüfen (früher return)")

    def test_dedupe_und_phantomfilter_bleiben(self):
        # Bestandszusagen (Issue #218) dürfen durch das Scoping nicht fallen.
        self.assertIn("Verdrängter Wartelauf", self.code)
        self.assertRegex(self.code, r"indexOf\('Workflow fehlgeschlagen: '")

    def test_diagnose_fehlgeschlagene_schritte(self):
        # Vertrag 5: Der Alarm benennt die roten Jobs/Schritte im Issue.
        self.assertIn("listJobsForWorkflowRun", self.code)
        self.assertIn("Fehlgeschlagene Schritte", self.code)


class ProdScopingResolve(unittest.TestCase):
    """Vertrag 2: Auto-Close nur bei Grün auf dem Default-Branch."""

    def setUp(self):
        self.raw = _text()
        try:
            import yaml
            self.data = yaml.safe_load(self.raw) or {}
        except ImportError:
            self.data = None

    def test_resolve_if_bedingung(self):
        if self.data is not None:
            jobs = self.data.get("jobs") or {}
            resolve = jobs.get("resolve") or {}
            cond = str(resolve.get("if") or "")
        else:
            # Regex-Fallback: die if-Zeile(n) des resolve-Jobs.
            m = re.search(r"resolve:\s*\n(?:.*\n)*?\s+if:\s*>-?\s*\n((?:\s+\$\{[^\n]+\n?|\s+[^\n]+\n?)+)",
                          self.raw)
            self.assertIsNotNone(m, "resolve-Job ohne if-Bedingung gefunden")
            cond = m.group(1)
        cond_norm = " ".join(cond.split())
        self.assertIn("conclusion == 'success'", cond_norm)
        self.assertIn("head_branch", cond_norm)
        self.assertIn("default_branch", cond_norm)
        self.assertIn("!= 'pull_request'", cond_norm.replace("event != 'pull_request'",
                                                             "!= 'pull_request'"))


class TitelUndLabelVertrag(unittest.TestCase):
    """Vertrag 3: Titel/Label bleiben parse-stabil für resolve + cleanup."""

    def test_titel_format(self):
        code = _kommentarfrei(_text())
        self.assertIn("title: '" + TITEL_PRÄFIX + "' + wfName + ' (' + conclusion + ')'", code)

    def test_auto_report_label(self):
        code = _kommentarfrei(_text())
        self.assertIn("labels: ['auto-report']", code)
        self.assertIn("createLabel", code)  # Label-Garantie (C12-Klasse)

    def test_resolve_parse_titel_startswith(self):
        # Der resolve-Job muss denselben Präfix per startswith matchen.
        self.assertIn('startswith("' + TITEL_PRÄFIX + '" + $w)', _text())


class VerhaltensSimulation(unittest.TestCase):
    """Vertrag 6 (Verhalten, nicht nur Text): Das alarm-Skript wird mit
    gestubbtem github-script-Kontext WIRKLICH ausgeführt – neun Szenarien
    inkl. der exakten #343-Konstellation. Harness:
    scripts/tests/sim/alert_scoping_sim.mjs (node; GitHub-Runner bringen es
    mit, lokal ohne node/pyyaml → Skip, kein Scheingrün)."""

    def test_neun_szenarien(self):
        import shutil
        import subprocess
        import tempfile

        node = shutil.which("node")
        if node is None:
            self.skipTest("node fehlt lokal – CI (ubuntu-latest) hat es")
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML lokal nicht installiert (CI installiert es)")

        daten = yaml.safe_load(_text())
        skript = daten["jobs"]["alarm"]["steps"][0]["with"]["script"]
        harness = REPO / "scripts" / "tests" / "sim" / "alert_scoping_sim.mjs"
        self.assertTrue(harness.exists(), f"Simulations-Harness fehlt: {harness}")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(skript)
            tmp_path = tmp.name
        try:
            proc = subprocess.run([node, str(harness), tmp_path],
                                  capture_output=True, text=True, timeout=120)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0,
                         "Verhaltens-Simulation fehlgeschlagen:\n" + proc.stdout + proc.stderr)
        self.assertIn("Szenarien korrekt", proc.stdout)


class WachtListenVertrag(unittest.TestCase):
    """Vertrag 4: Herzschlag-SSOT bleibt intakt (alerting_heartbeat)."""

    def test_wacht_liste_lesbar(self):
        import alerting_heartbeat as ah
        namen = ah.gelistete_workflows(_text())
        self.assertGreaterEqual(len(namen), 35)
        self.assertEqual(len(namen), len(set(namen)), "Duplikate in der Wacht-Liste")
        self.assertIn("Layout-AI", namen)
        self.assertIn("Deploy auf GitHub Pages", namen)
        self.assertIn("Qualitäts-Gate (Build + interne Links)", namen)
        self.assertNotIn("Fehler-Alerting", namen, "Keine Selbstbeobachtung")

    def test_types_completed(self):
        # workflow_run muss auf `completed` feuern, sonst zählt der
        # Herzschlag Zustellungen, die es nicht gibt.
        self.assertRegex(_text(), r"types:\s*\n\s*-\s*completed")

    def test_yaml_valide(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML lokal nicht installiert (CI installiert es)")
        daten = yaml.safe_load(_text())
        self.assertIsInstance(daten, dict)
        # YAML-1.1-Falle: `on` wird zu True – beide Schlüssel akzeptieren.
        on = daten.get("on", daten.get(True))
        self.assertIn("workflow_run", on or {})


if __name__ == "__main__":
    unittest.main()
