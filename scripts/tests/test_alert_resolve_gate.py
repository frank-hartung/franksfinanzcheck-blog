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
import re
import subprocess
import sys
import tempfile
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
