"""Regressionstests des Auto-Close-Gates (WF-E813 / #809).

Vorfall 15.–19.10.2026: Die Sicherheits-Wache meldete „Sicherheits-Wache ist
fehlgeschlagen“ (#767, #782, #798, #809) – vier Meldungen in fünf Tagen für
denselben offenen Befund. Der Fehler lag nicht in der Wache, sondern im
Auto-Close des Fehler-Alertings: Jeder GRÜNE Lauf des Workflows schloss die
offene Meldung mit „✅ Behoben: Der Vorgang läuft wieder fehlerfrei“ – auch
ein Push-Lauf, der nur den Offline-Job „Quellseite“ ausführte und die
Live-Messung aussparte. Belegt durch die Abschlussläufe selbst:

  #782 → geschlossen durch Run 38923824627 (push, Live-Messung: skipped)
  #798 → geschlossen durch Run 39125154809 (push, Live-Messung: skipped)

Diese Datei nagelt fest, was „Behoben“ künftig bedeuten darf: Jeder Job, den
die Meldung als fehlgeschlagen benannt hat, muss im auflösenden Lauf
vorhanden und `success` sein. Fehlt er (bedingte Jobs!), bleibt die Meldung
offen – dieselbe Ehrlichkeit, die die Wache selbst mit BEFUND/STOERUNG
eingeführt hat (C34), jetzt auf der Schließseite.

Ausführung:  python3 -m unittest scripts.tests.test_alert_resolve_gate -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alert_resolve_gate as gate  # noqa: E402

LIVE = "Live-Messung (täglich und auf Zuruf)"
QUELLE = "Quellseite (offline, mit Selbsttests)"


def _body_mit_marker(jobs: list[str], extra: str = "") -> str:
    return (f"<!-- alert-key: WF-E813 -->\n<!-- alert-runbook: sicherheit-header -->\n"
            f"<!-- alert-jobs: {json.dumps(jobs, ensure_ascii=False)} -->\n{extra}")


class JobBeweisStattIrgendeinGruen(unittest.TestCase):
    """Vertrag 1: Kein „Behoben“ ohne den Job, der rot war (#809)."""

    def test_push_ohne_live_job_schliesst_live_meldung_nicht(self):
        """Die exakte Wiederholung von #782/#798/#809: Push-Lauf auf main,
        Live-Messung ausgesetzt, Lauf insgesamt grün – die Meldung darf
        NICHT geschlossen werden."""
        e = gate.entscheiden(_body_mit_marker([LIVE]),
                             {"jobs": [{"name": QUELLE, "conclusion": "success"}]})
        self.assertFalse(e["schliessen"])
        self.assertIn(LIVE, e["grund"])

    def test_live_job_gruen_schliesst(self):
        e = gate.entscheiden(
            _body_mit_marker([LIVE]),
            {"jobs": [{"name": QUELLE, "conclusion": "success"},
                      {"name": LIVE, "conclusion": "success"}]})
        self.assertTrue(e["schliessen"])
        self.assertIn(LIVE, e["grund"])

    def test_skipped_ist_kein_beweis(self):
        e = gate.entscheiden(_body_mit_marker([LIVE]),
                             {"jobs": [{"name": LIVE, "conclusion": "skipped"}]})
        self.assertFalse(e["schliessen"])

    def test_nicht_gruener_job_schliesst_nicht(self):
        for schluss in ("failure", "timed_out", "cancelled", ""):
            with self.subTest(conclusion=schluss):
                e = gate.entscheiden(
                    _body_mit_marker([LIVE]),
                    {"jobs": [{"name": LIVE, "conclusion": schluss}]})
                self.assertFalse(e["schliessen"])

    def test_alle_gemeldeten_jobs_muessen_gruen_sein(self):
        body = _body_mit_marker([LIVE, QUELLE])
        e = gate.entscheiden(
            body,
            {"jobs": [{"name": LIVE, "conclusion": "success"},
                      {"name": QUELLE, "conclusion": "failure"}]})
        self.assertFalse(e["schliessen"])
        self.assertIn(QUELLE, e["grund"])
        e = gate.entscheiden(
            body,
            {"jobs": [{"name": LIVE, "conclusion": "success"},
                      {"name": QUELLE, "conclusion": "success"}]})
        self.assertTrue(e["schliessen"])

    def test_kein_job_beweis_im_lauf_bleibt_offen(self):
        for lauf in ([], {"jobs": []}, None, {}):
            with self.subTest(lauf=lauf):
                e = gate.entscheiden(_body_mit_marker([LIVE]), lauf)
                self.assertFalse(e["schliessen"])


class WorkerDeployNachweis922(unittest.TestCase):
    """Ein grünes Policy-Gate ist noch kein Deploy mit Live-Nachweis."""

    POLICY = "Produktions-Environment absichern (nur main, Reviewer, kein Admin-Bypass)"
    TESTS = "Worker-Tests (ohne Deployment)"
    PLAN = "Deploy planen"
    ABSCHLUSS = "Deploy-Beweis · kein stiller Skip"

    def body(self, jobs=None):
        namen = [self.POLICY] if jobs is None else jobs
        return ("<!-- alert-key: WF-829B -->\n"
                "<!-- alert-runbook: worker-deploy-zugang -->\n"
                "<!-- alert-jobs: " + json.dumps(namen) + " -->")

    def lauf(self, worker="newsletter-worker"):
        return {"jobs": [
            {"name": self.TESTS, "conclusion": "success"},
            {"name": self.PLAN, "conclusion": "success"},
            {"name": self.POLICY, "conclusion": "success"},
            {"name": "Deploy " + worker, "conclusion": "success", "steps": [
                {"name": "Deploy", "conclusion": "success"},
                {"name": "Deploy-Nachweis", "conclusion": "success"},
            ]},
            {"name": self.ABSCHLUSS, "conclusion": "success"},
        ]}

    def pruefen(self, lauf, *, body=None, ereignis="workflow_dispatch"):
        return gate.entscheiden(self.body() if body is None else body, lauf,
                                ereignis=ereignis)

    @staticmethod
    def deploy(lauf):
        return next(j for j in lauf["jobs"] if j["name"] == "Deploy newsletter-worker")

    def test_aktuelle_policy_meldung_braucht_newsletter_und_live_nachweis(self):
        self.assertFalse(self.pruefen({"jobs": [
            {"name": self.POLICY, "conclusion": "success"}]})["schliessen"])
        self.assertFalse(self.pruefen(self.lauf("klick-zaehler"))["schliessen"])
        self.assertTrue(self.pruefen(self.lauf())["schliessen"])

    def test_spezifischer_worker_muss_selbst_erfolgreich_ausgeliefert_sein(self):
        body = self.body(["Deploy klick-zaehler"])
        self.assertFalse(self.pruefen(self.lauf(), body=body)["schliessen"])
        self.assertTrue(self.pruefen(self.lauf("klick-zaehler"), body=body)["schliessen"])

    def test_kein_schliessen_bei_fehlendem_oder_uebersprungenem_beweis(self):
        for job_name in (self.TESTS, self.PLAN, self.POLICY, self.ABSCHLUSS, "Deploy newsletter-worker"):
            for zustand in ("skipped", "failure", "cancelled", None):
                with self.subTest(job=job_name, zustand=zustand):
                    lauf = self.lauf()
                    job = next(j for j in lauf["jobs"] if j["name"] == job_name)
                    job["conclusion"] = zustand
                    self.assertFalse(self.pruefen(lauf)["schliessen"])
        for schritt in ("Deploy", "Deploy-Nachweis"):
            for zustand in ("skipped", "failure", None):
                with self.subTest(schritt=schritt, zustand=zustand):
                    lauf = self.lauf()
                    steps = self.deploy(lauf)["steps"]
                    next(s for s in steps if s["name"] == schritt)["conclusion"] = zustand
                    self.assertFalse(self.pruefen(lauf)["schliessen"])
            lauf = self.lauf()
            self.deploy(lauf)["steps"] = [s for s in self.deploy(lauf)["steps"]
                                          if s["name"] != schritt]
            self.assertFalse(self.pruefen(lauf)["schliessen"])

    def test_doppelte_jobs_oder_schritte_sind_mehrdeutig(self):
        lauf = self.lauf()
        lauf["jobs"].append(dict(self.deploy(lauf)))
        self.assertFalse(self.pruefen(lauf)["schliessen"])
        lauf = self.lauf()
        self.deploy(lauf)["steps"].append({"name": "Deploy-Nachweis", "conclusion": "success"})
        self.assertFalse(self.pruefen(lauf)["schliessen"])

    def test_zuvor_roter_testjob_kann_im_deploy_lauf_nachgewiesen_werden(self):
        body = self.body([self.TESTS, self.ABSCHLUSS])
        lauf = self.lauf()
        self.assertFalse(self.pruefen(lauf, body=body, ereignis="push")["schliessen"])
        self.assertTrue(self.pruefen(lauf, body=body)["schliessen"])
        next(j for j in lauf["jobs"] if j["name"] == self.TESTS)["conclusion"] = "skipped"
        self.assertFalse(self.pruefen(lauf, body=body)["schliessen"])

    def test_nur_manueller_deploy_schliesst_niemals_push_oder_unbekannt(self):
        for ereignis in ("push", "pull_request", "schedule", "", None):
            with self.subTest(ereignis=ereignis):
                self.assertFalse(self.pruefen(self.lauf(), ereignis=ereignis)["schliessen"])

    def test_altmeldung_ohne_jobs_braucht_trotzdem_beweis(self):
        body = "<!-- alert-key: WF-829B -->\nAlter Text ohne Job-Marker"
        self.assertFalse(self.pruefen({"jobs": [{"name": self.POLICY,
                                                 "conclusion": "success"}]}, body=body)["schliessen"])
        self.assertTrue(self.pruefen(self.lauf(), body=body)["schliessen"])
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "body.md"
            pfad.write_text("Alte Meldung ohne Marker", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "alert_resolve_gate.py"),
                 "--body", str(pfad), "--nennt-jobs", "--workflow", "Cloudflare-Worker deployen"],
                capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class AltformenUndRobustheit(unittest.TestCase):
    """Vertrag 2: Bestandsmeldungen und Sonderfälle laufen durch dieselbe Regel."""

    def test_altform_ohne_marker_wird_gelernt(self):
        body = f"- Job **„{LIVE}“** ([Log](https://x/j)) – „Sicherheits-Header auswerten“"
        self.assertEqual(gate.jobs_aus_body(body), [LIVE])
        e = gate.entscheiden(body, {"jobs": [{"name": QUELLE, "conclusion": "success"}]})
        self.assertFalse(e["schliessen"], "Alt-Bestand (#809-Klasse) muss dieselbe Regel schützen")

    def test_marker_hat_vorrang_vor_lesbarer_zeile(self):
        body = _body_mit_marker([QUELLE], extra=f"- Job **„{LIVE}“**")
        self.assertEqual(gate.jobs_aus_body(body), [QUELLE])

    def test_kaputter_marker_faellt_auf_lesbare_zeile_zurueck(self):
        body = f"<!-- alert-jobs: [kein json -->\n- Job **„{LIVE}“**"
        self.assertEqual(gate.jobs_aus_body(body), [LIVE])

    def test_sonderzeichen_ueberleben_den_marker(self):
        name = 'Live-Messung (täglich & auf Zuruf) – „prüfen“ [x]'
        body = _body_mit_marker([name])
        self.assertEqual(gate.jobs_aus_body(body), [name])

    def test_duplikate_fallen_weg(self):
        body = f"- Job **„{LIVE}“**\n- Job **„{LIVE}“**"
        self.assertEqual(gate.jobs_aus_body(body), [LIVE])

    def test_altvertrag_ohne_jede_job_angabe(self):
        # Meldungen aus der Zeit vor der Job-Marker-Pflicht ohne lesbare
        # Job-Zeile: der Altvertrag (grüner Lauf genügt) bleibt – aber der
        # Grund benennt den Fallback ausdrücklich.
        e = gate.entscheiden("nur Fließtext",
                             {"jobs": [{"name": QUELLE, "conclusion": "success"}]})
        self.assertTrue(e["schliessen"])
        self.assertIn("Altvertrag", e["grund"])
        # Und ohne jeden Job-Beweis im Lauf gilt auch hier: offen.
        e = gate.entscheiden("nur Fließtext", {"jobs": []})
        self.assertFalse(e["schliessen"])

    def test_api_beide_shapes(self):
        liste = [{"name": "X", "conclusion": "success"}]
        self.assertEqual(gate.jobs_aus_lauf(liste)["X"], "success")
        self.assertEqual(gate.jobs_aus_lauf({"jobs": liste})["X"], "success")
        self.assertEqual(gate.jobs_aus_lauf({"total_count": 0}), {})
        self.assertEqual(gate.jobs_aus_lauf(None), {})


class SelbsttestUndAufruf(unittest.TestCase):
    """Vertrag 3: Der Selbsttest des Gates ist grün und der CLI-Vertrag hält."""

    def test_selftest_gruen(self):
        self.assertEqual(gate.selftest(), 0)

    def test_cli_liefert_json_entscheidung(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.md"
            jobs = Path(tmp) / "jobs.json"
            body.write_text(_body_mit_marker([LIVE]), encoding="utf-8")
            jobs.write_text(json.dumps({"jobs": [
                {"name": QUELLE, "conclusion": "success"}]}), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "alert_resolve_gate.py"),
                 "--body", str(body), "--jobs", str(jobs), "--json"],
                capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        entscheidung = json.loads(proc.stdout)
        self.assertFalse(entscheidung["schliessen"])
        self.assertIn(LIVE, entscheidung["grund"])

    def test_cli_ohne_argumente_ist_werkzeugfehler(self):
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "alert_resolve_gate.py")],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2)


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "bash und jq erforderlich")
class ResolveEndToEnd(unittest.TestCase):
    """Führt den echten Resolve-Shellblock mit lokaler GitHub-Attrappe aus."""

    def resolve(self, jobs, *, body, ereignis="workflow_dispatch",
                workflow="Cloudflare-Worker deployen", nenner_exit=None, api_fehler=False):
        workflow_text = (REPO / ".github" / "workflows" / "alert-on-failure.yml").read_text(
            encoding="utf-8")
        block = workflow_text.split("- name: Behobene Fehlermeldung schließen", 1)[1]
        shell = textwrap.dedent(block.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Der produktive Block nutzt /tmp. Im Test gehen alle Dateien in
            # ein eigenes Verzeichnis; GH und API sind vollständig gestubbt.
            shell = shell.replace("/tmp/", str(tmp) + "/")
            issues = [{"number": 922, "title": "⚠️ Workflow fehlgeschlagen: " + workflow,
                       "body": body}]
            (tmp / "issues.json").write_text(json.dumps(issues, ensure_ascii=False), encoding="utf-8")
            (tmp / "jobs.jsonl").write_text(
                "\n".join(json.dumps(j, ensure_ascii=False) for j in jobs) + "\n", encoding="utf-8")
            (tmp / "gh").write_text(textwrap.dedent('''\
                #!/usr/bin/env bash
                set -euo pipefail
                if [ "$1" = issue ] && [ "$2" = list ]; then cat "$ISSUES"; exit 0; fi
                if [ "$1" = api ]; then
                  if [ "${API_FEHLER:-0}" = 1 ]; then exit 1; fi
                  cat "$JOBS"; exit 0
                fi
                if [ "$1" = issue ] && [ "$2" = close ]; then
                  printf '%s\\n' "$@" >> "$CLOSED"; exit 0
                fi
                exit 2
            '''), encoding="utf-8")
            (tmp / "gh").chmod(0o755)
            (tmp / "python3").write_text(textwrap.dedent('''\
                #!/usr/bin/env bash
                if [[ " $* " == *" --nennt-jobs "* ]] && [ -n "${NENNER_EXIT:-}" ]; then
                  exit "$NENNER_EXIT"
                fi
                exec "$REAL_PYTHON" "$@"
            '''), encoding="utf-8")
            (tmp / "python3").chmod(0o755)
            umgebung = dict(os.environ, PATH=str(tmp) + os.pathsep + os.environ["PATH"],
                            REAL_PYTHON=sys.executable, ISSUES=str(tmp / "issues.json"),
                            JOBS=str(tmp / "jobs.jsonl"), CLOSED=str(tmp / "closed"),
                            NENNER_EXIT=str(nenner_exit) if nenner_exit is not None else "",
                            API_FEHLER="1" if api_fehler else "0", GH_TOKEN="dummy",
                            GITHUB_REPOSITORY="frank-hartung/franksfinanzcheck-blog",
                            WF_NAME=workflow, RUN_BRANCH="main", RUN_ID="123",
                            RUN_URL="https://github.com/example/example/actions/runs/123",
                            RUN_EVENT=ereignis)
            proc = subprocess.run(["bash", "-c", shell], cwd=REPO, env=umgebung,
                                  capture_output=True, text=True, timeout=30)
            geschlossen = (tmp / "closed").read_text(encoding="utf-8") if (tmp / "closed").exists() else ""
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return geschlossen, proc.stdout, proc.stderr

    def test_aktuelles_issue_nur_mit_passendem_lauf_schliessen(self):
        fixture = WorkerDeployNachweis922()
        body = fixture.body()
        for jobs, event in ((fixture.lauf("klick-zaehler")["jobs"], "workflow_dispatch"),
                            (fixture.lauf()["jobs"], "push")):
            with self.subTest(event=event, jobs=jobs):
                closed, out, _ = self.resolve(jobs, body=body, ereignis=event)
                self.assertFalse(closed)
                self.assertIn("bleibt offen", out)
        closed, _, _ = self.resolve(fixture.lauf()["jobs"], body=body)
        self.assertIn("close\n922\n", closed)

    def test_unlesbare_belege_und_werkzeugfehler_schliessen_nicht(self):
        fixture = WorkerDeployNachweis922()
        for opts in ({"api_fehler": True}, {"nenner_exit": 2}):
            with self.subTest(opts=opts):
                closed, out, _ = self.resolve(fixture.lauf()["jobs"], body=fixture.body(), **opts)
                self.assertFalse(closed)
                self.assertIn("bleibt", out)

    def test_altmeldung_ohne_jobs_hat_keinen_deploy_freipass(self):
        fixture = WorkerDeployNachweis922()
        closed, _, _ = self.resolve([], body="Alter Text ohne Job-Marker")
        self.assertFalse(closed)
        closed, _, _ = self.resolve(fixture.lauf()["jobs"], body="Alter Text ohne Job-Marker")
        self.assertTrue(closed)
        # Der Übergangsvertrag für andere Workflows bleibt erhalten und der
        # Markdown-Branchname wird nicht als Shell-Befehl interpretiert.
        closed, _, err = self.resolve([], body="Alter Text", workflow="Layout-AI")
        self.assertIn("`main`", closed)
        self.assertNotIn("command not found", err)


class WorkflowVertrag(unittest.TestCase):
    """Vertrag 4: resolve nutzt das Gate, der Alarm schreibt den Job-Marker.
    Ein Test, der nur die Datei prüft, ohne die Verdrahtung, bemerkt den
    Rückfall zum nackten `gh issue close` nicht."""

    def _text(self) -> str:
        return (REPO / ".github" / "workflows" / "alert-on-failure.yml").read_text(
            encoding="utf-8")

    def test_resolve_ruft_das_gate_auf(self):
        text = self._text()
        self.assertIn("alert_resolve_gate.py", text)
        m = re.search(r"alert_resolve_gate\.py\s*\\?\s*--body", text)
        self.assertIsNotNone(m, "resolve muss das Gate mit --body aufrufen")
        pos_close = text.find("gh issue close")
        self.assertGreater(pos_close, -1)
        self.assertLess(m.start(), pos_close,
                        "die Entscheidung muss VOR `gh issue close` fallen")

    def test_alarm_schreibt_den_job_marker(self):
        self.assertIn("alert-jobs:", self._text())

    def test_resolve_loggt_den_offen_grund(self):
        # Wer offen bleibt, muss hören WARUM – sonst sucht der Mensch weiter.
        self.assertIn("bleibt offen", self._text())


if __name__ == "__main__":
    unittest.main()
