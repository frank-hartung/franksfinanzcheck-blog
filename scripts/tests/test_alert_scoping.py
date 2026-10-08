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
  3. IDENTITÄTS-VERTRAG (neu seit 01.10.2026, Marken-Oberfläche #496):
     Issue-Titel sind eine öffentliche, indexierte Markenfläche. Der
     Titel ist deshalb markenneutral („🔧 Wartung · <Bereich> ·
     Vorgang WF-XXXX") und taugt NICHT mehr als Schlüssel; die
     Identität ist der unsichtbare Marker im Body
     (<!-- alert-key: WF-XXXX -->) aus scripts/alert_issue_identity.py.
     Diese Datei bewacht: Anlegen und Auto-Close benutzen denselben
     Marker, die Alt-Titel-Erkennung bleibt bis zum Abklingen stehen
     (sonst Doppel-Issues bzw. ewig offene Meldungen), Label
     auto-report bleibt byte-stabil, und der erzeugte Titel enthält
     keine Betriebssprache (geprüft mit der Marken-Wache selbst).
  4. WACHT-LISTEN-VERTRAG: on.workflow_run.workflows + types: [completed]
     bleiben lesbar für alerting_heartbeat.gelistete_workflows (SSOT des
     Alerting-Herzschlags; Handkopien sind die Fehlerklasse vom 18.09.).
  5. DIAGNOSE: Der Alarm trägt die fehlgeschlagenen Jobs/Schritte ins
     Issue (Lehre aus INCIDENT-2026-09-19: „die Meldung riet, das Log
     hätte es gewusst").
  6. FACHKANAL: Ein ausdrücklich klassifiziertes Tagesdefizit erzeugt
     kein zweites generisches auto-report-Issue, wenn das engine-deficit-
     Fach-Issue offen nachweisbar ist (#602); fehlt der Fachkanal,
     bleibt das Alerting fail-open.
  7. ENGINE-DIAGNOSE (#632): Wenn Phase 0.5 und der Schluss-Classifier
     gemeinsam fehlschlagen, erklärt das Issue den Frühabbruch und liefert
     das KI-Probe-Runbook statt pauschal API-Key-/GitHub-Tipps.
  8. VERHALTEN: Die Verhaltens-Simulation (scripts/tests/sim/
     alert_scoping_sim.mjs) führt das Inline-Skript mit gestubbtem
     github-script-Kontext aus – die Produktionsszenarien inkl. exakter
     #343- und #632-Reproduktion, Phantom-Filter (#218), Dedupe,
     Fachkanal-Stummschaltung und Fail-open.

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

YAML_PATH = REPO / ".github" / "workflows" / "alert-on-failure.yml"

TITEL_PRÄFIX = "⚠️ Workflow fehlgeschlagen: "   # Alt-Form: nur noch Übergangs-Erkennung


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
        # Dedupe läuft jetzt über den Marker (Identität) …
        self.assertIn("ident.marker", self.code)
        # … und erkennt die Alt-Titel weiter, solange Meldungen von vorher
        # offen stehen können – ohne diesen Pfad gäbe es Doppel-Issues.
        self.assertRegex(self.code, r"indexOf\(altTitel\)")
        self.assertRegex(self.code, r"'Workflow fehlgeschlagen: '")

    def test_diagnose_fehlgeschlagene_schritte(self):
        # Vertrag 5: Der Alarm benennt die roten Jobs/Schritte im Issue.
        self.assertIn("listJobsForWorkflowRun", self.code)
        self.assertIn("Fehlgeschlagene Schritte", self.code)

    def test_wf_a535_phase05_hat_eigenes_runbook(self):
        # Issue #632: Die Schlussklassifikation kann ebenfalls rot sein;
        # entscheidend ist die Kombination mit dem fehlgeschlagenen Phase-0.5-
        # Gate. In diesem Fall sind Tagesdefizit/API-Key-Ratschläge irreführend.
        self.assertIn("wfName === 'Content-Engine v2'", self.code)
        self.assertIn("engineFinalClassifierFailed", self.code)
        self.assertIn("Phase 0.5 – Kadenz-Gate sicherstellen", self.code)
        self.assertIn("Do not report a quota deficit as success", self.code)
        self.assertIn("selftest_ki.py --trap <skript>", self.code)
        self.assertIn("weder ein Tagesdefizit noch einen API-Key-Ausfall", self.code)

    def test_tagesdefizit_fachkanal_verhindert_duplikat(self):
        # Vertrag 6 (#602): Ein ehrlich roter Quotenschritt darf nur dann
        # stummgeschaltet werden, wenn das engine-deficit-Fach-Issue mit
        # Marker offen nachweisbar ist; sonst bleibt das Alerting fail-open.
        self.assertIn("engine-deficit", self.code)
        self.assertIn("engine-deficit-id: tagesdefizit", self.code)
        self.assertIn("routedToEngineDeficit", self.code)
        self.assertIn("freshForThisRun", self.code)
        self.assertIn("updated_at", self.code)
        self.assertIn("kein generisches auto-report-Duplikat", self.code)
        self.assertIn("fail-open", self.code)

    def test_timeout_ist_echter_produktionsfehler(self):
        # GitHub unterscheidet `timed_out` von `failure`. Ohne diese explizite
        # Conclusion würde ein festgefahrener Produktionslauf trotz rotem
        # Herzschlag nie direkt gemeldet.
        self.assertRegex(self.code, r"conclusion\s*==\s*'timed_out'")
        self.assertRegex(self.code, r"j\.conclusion\s*===\s*'timed_out'")
        self.assertRegex(self.code, r"s\.conclusion\s*===\s*'timed_out'")

    def test_github_script_unveraenderlich_gepinnt(self):
        self.assertRegex(self.code, r"uses:\s*actions/github-script@[0-9a-f]{40}")


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
    """Vertrag 3: Identität = Marker, Titel = Markenfläche."""

    def test_titel_kommt_aus_der_identitaets_quelle(self):
        code = _kommentarfrei(_text())
        self.assertIn("title: ident.titel", code)
        # Der Alt-Titel darf nur noch ERKANNT (altTitel, Übergang), nie mehr
        # GESCHRIEBEN werden – sonst stünde Betriebssprache wieder im Index.
        self.assertNotIn("title: '" + TITEL_PRÄFIX, code,
                         "Alt-Titel darf nicht mehr erzeugt werden (Markenfläche #496)")
        self.assertNotRegex(code, r"title:\s*'[^']*fehlgeschlagen")
        self.assertIn("alert_issue_identity.py", _text())

    def test_marker_steht_im_body(self):
        code = _kommentarfrei(_text())
        pos_marker = code.find("ident.marker")
        pos_create = code.find("issues.create({")
        self.assertGreater(pos_marker, -1, "Marker fehlt – die Meldung hätte keine Identität")
        self.assertLess(pos_marker, pos_create,
                        "Der Marker muss im Body stehen, bevor die Meldung erzeugt wird")

    def test_erzeugter_titel_ist_markenfrei(self):
        """Der Titel wird mit der Marken-Wache selbst geprüft – derselbe
        Detektor, der den Befund O6 erhoben hat (kein zweiter Maßstab)."""
        import alert_issue_identity as ident
        import brand_surface_guard as wache
        namen = ident.wacht_liste()
        self.assertGreaterEqual(len(namen), 35, "Wacht-Liste nicht lesbar")
        for name in namen:
            funde = wache.pruefe_text(ident.titel(name), "titel",
                                      "O6 Öffentliche Issue-Titel", [])
            self.assertEqual(funde, [], f"Betriebssprache im Titel für „{name}“")

    def test_codes_sind_eindeutig(self):
        import alert_issue_identity as ident
        namen = ident.wacht_liste()
        codes = [ident.code(n) for n in namen]
        self.assertEqual(len(codes), len(set(codes)),
                         "Code-Kollision – zwei Workflows teilten sich eine Identität")

    def test_auto_report_label(self):
        code = _kommentarfrei(_text())
        self.assertIn("labels: ['auto-report']", code)
        self.assertIn("createLabel", code)  # Label-Garantie (C12-Klasse)

    def test_resolve_schliesst_ueber_marker_und_alt_titel(self):
        """Symmetrie-Zusage: Was über den Marker angelegt wird, muss auch
        über den Marker schließen – sonst bleibt jede Meldung ewig offen.
        Der Alt-Titel-Pfad bleibt für Meldungen aus der Zeit davor."""
        roh = _text()
        self.assertIn("alert_issue_identity.py --workflow", roh)
        self.assertIn('contains($m)', roh)
        self.assertIn('startswith($t)', roh)
        self.assertIn(TITEL_PRÄFIX, roh)


class VerhaltensSimulation(unittest.TestCase):
    """Vertrag 7 (Verhalten, nicht nur Text): Das alarm-Skript wird mit
    gestubbtem github-script-Kontext WIRKLICH ausgeführt – alle Kern-
    Szenarien inkl. der exakten #343-Konstellation. Harness:
    scripts/tests/sim/alert_scoping_sim.mjs (node; GitHub-Runner bringen es
    mit, lokal ohne node/pyyaml → Skip, kein Scheingrün)."""

    def test_kern_szenarien(self):
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
        # Den github-script-Schritt suchen statt auf eine Position zu wetten:
        # vor ihm stehen Checkout, Selbsttest und Identitäts-Schritt.
        schritte = daten["jobs"]["alarm"]["steps"]
        kandidaten = [s for s in schritte if "github-script" in str(s.get("uses", ""))]
        self.assertEqual(len(kandidaten), 1,
                         "genau ein github-script-Schritt im alarm-Job erwartet")
        skript = kandidaten[0]["with"]["script"]
        harness = REPO / "scripts" / "tests" / "sim" / "alert_scoping_sim.mjs"
        self.assertTrue(harness.exists(), f"Simulations-Harness fehlt: {harness}")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(skript)
            tmp_path = tmp.name
        # Identität aus der ECHTEN Quelle erzeugen (wie der Lauf es tut):
        # die Simulation darf keine eigene Namensgebung erfinden.
        import json
        import os
        import alert_issue_identity as ident_modul
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as idf:
            # Simulation deckt mehrere echte Workflows ab, insbesondere die
            # markenneutrale Identität der Content-Engine (WF-A535 / #632).
            identitaeten = {name: ident_modul.identitaet(name)
                            for name in ("Layout-AI", "Content-Engine v2")}
            json.dump(identitaeten, idf, ensure_ascii=False)
            ident_pfad = idf.name
        umgebung = dict(os.environ, ALARM_IDENTITAET=ident_pfad)
        try:
            proc = subprocess.run([node, str(harness), tmp_path],
                                  capture_output=True, text=True, timeout=120,
                                  env=umgebung)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
            Path(ident_pfad).unlink(missing_ok=True)
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
