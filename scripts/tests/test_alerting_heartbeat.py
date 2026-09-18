"""Regressions-Tests des Alerting-Herzschlags (Folge-Befund 4 / Befund E).

Der Herzschlag (scripts/alerting_heartbeat.py + alerting-heartbeat.yml) zählt
die `workflow_run`-Zustellung des Fehler-Alertings täglich nach – weil der
Qualitäts-Gate-Vorfall vom 18.09.2026 gezeigt hat, dass ~35 % der Ereignisse
nie ankamen (14 rote Gate-Läufe, 0 Meldungen). Aussage ohne Wache wäre eine
Leihgabe; hier liegen die Verträge:

  1. Die Wacht-Liste wird aus alert-on-failure.yml GELESEN, nicht abgetippt
     (Handkopien sind Befund C des Vorfalls), inkl. der YAML-1.1-Falle
     (`on:` wird von safe_load zu True).
  2. Das Zähl-Urteil ist scharf: ungedeckter ROTER Lauf = sofort Befund,
     >= 2 verlorene Ereignisse = Befund, Einzelverlust = Hinweis.
  3. Der Workflow ist unabhängig vom beobachteten Kanal (cron, nie
     workflow_run) und meldet sich selbst (Issue bei Befund, Schließpfad
     bei Grün) – nach dem Muster der Gate-Eigenmeldung vom 18.09.2026.
  4. Der Herzschlag steht in governance_contract.GUARDS (der Vertrag
     verlangt seinen Selbsttest) und nicht in der eigenen Wacht-Liste.

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import datetime as dt
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alerting_heartbeat as ah  # noqa: E402

JETZT = dt.datetime(2026, 9, 18, 12, 0, tzinfo=dt.timezone.utc)


def mk(name, conclusion, fertig, rid="1"):
    return {"name": name, "conclusion": conclusion, "id": rid,
            "url": f"https://example.invalid/runs/{rid}",
            "created_at": fertig - dt.timedelta(minutes=3),
            "completed_at": fertig}


class WachtListe(unittest.TestCase):
    def setUp(self):
        pfad = REPO / ".github" / "workflows" / "alert-on-failure.yml"
        self.text = pfad.read_text(encoding="utf-8")

    def test_liste_kommt_aus_der_datei(self):
        namen = ah.gelistete_workflows(self.text)
        self.assertGreaterEqual(len(namen), 35)
        self.assertIn("Qualitäts-Gate (Build + interne Links)", namen)
        self.assertIn("Deploy auf GitHub Pages", namen)
        self.assertEqual(len(namen), len(set(namen)), "Duplikate in der Wacht-Liste")

    def test_kein_selbst_beobachten(self):
        namen = ah.gelistete_workflows(self.text)
        self.assertNotIn("Fehler-Alerting", namen)
        # Der Herzschlag selbst gehört ebenfalls nicht hinein (Kopf-Kommentar
        # des Workflows begründet es – die Regel ist hier die Wache).
        herz = (REPO / ".github" / "workflows" / "alerting-heartbeat.yml")
        self.assertTrue(herz.exists(), "alerting-heartbeat.yml fehlt")
        import re as _re
        m = _re.search(r"^name:\s*(.+?)\s*$", herz.read_text(encoding="utf-8"),
                       _re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertNotIn(m.group(1), namen,
                         "Der Herzschlag darf nicht über den workflow_run-Kanal "
                         "beobachtet werden, dessen Zustellung er selbst misst.")

    def test_beide_parser_gleich(self):
        """PyYAML-Pfad (mit der `on:`→True-Falle) und Regex-Fallback lesen
        dieselbe Wahrheit – sonst verschiebt sich die Zählung je nachdem,
        welches Paket zufällig installiert ist."""
        y = ah.gelistete_workflows(self.text, use_yaml=True)
        r = ah.gelistete_workflows(self.text, use_yaml=False)
        self.assertEqual(y, r)


class ZaehlUrteil(unittest.TestCase):
    def _alarm(self, fertig, delta=2):
        return [fertig + dt.timedelta(minutes=delta)]

    def test_vollstaendig_bleibt_gruen(self):
        f = dt.datetime(2026, 9, 18, 4, 58, tzinfo=dt.timezone.utc)
        erg = ah.abgleich([mk("A", "success", f)], self._alarm(f), JETZT)
        self.assertEqual(erg["befunde"], [])
        self.assertEqual(erg["fehlend"], 0)

    def test_roter_lauf_ohne_alarm_ist_sofort_befund(self):
        f = dt.datetime(2026, 9, 18, 4, 58, tzinfo=dt.timezone.utc)
        erg = ah.abgleich([mk("Gate", "failure", f)], [], JETZT)
        self.assertTrue(any("rote Läufe" in b for b in erg["befunde"]))
        # Das ist exakt die Vorfalls-Lage: Rot, von dem niemand erfährt.
        self.assertEqual(len(erg["rot_offen"]), 1)

    def test_einzelverlust_ist_hinweis_kein_alarm(self):
        f = dt.datetime(2026, 9, 18, 4, 58, tzinfo=dt.timezone.utc)
        erg = ah.abgleich([mk("A", "success", f)], [], JETZT)
        self.assertEqual(erg["befunde"], [])
        self.assertEqual(len(erg["hinweise"]), 1)

    def test_zwei_verluste_sind_befund(self):
        f1 = dt.datetime(2026, 9, 18, 4, 58, tzinfo=dt.timezone.utc)
        f2 = dt.datetime(2026, 9, 18, 6, 0, tzinfo=dt.timezone.utc)
        erg = ah.abgleich([mk("A", "success", f1, "1"), mk("B", "success", f2, "2")],
                          [], JETZT)
        self.assertTrue(any("2 von 2" in b for b in erg["befunde"]))

    def test_zuordnungstoleranz(self):
        f = dt.datetime(2026, 9, 18, 4, 0, tzinfo=dt.timezone.utc)
        for delta, fehlend in ((89, 0), (91, 1), (-4, 0), (-6, 1)):
            erg = ah.abgleich([mk("A", "success", f)],
                              [f + dt.timedelta(minutes=delta)], JETZT)
            self.assertEqual(erg["fehlend"], fehlend, f"delta={delta} min")

    def test_gnadenfrist_und_fenster(self):
        # frisch abgeschlossen (nach bis) -> noch nicht gezählt
        frisch = mk("A", "success", dt.datetime(2026, 9, 18, 11, 30,
                                                tzinfo=dt.timezone.utc))
        self.assertEqual(ah.abgleich([frisch], [], JETZT)["gesamt"], 0)
        # vor dem Fenster -> nicht gezählt
        alt = mk("A", "success", dt.datetime(2026, 9, 16, 9, 0,
                                             tzinfo=dt.timezone.utc))
        self.assertEqual(ah.abgleich([alt], [], JETZT)["gesamt"], 0)

    def test_skipped_loest_kein_ereignis_aus(self):
        f = dt.datetime(2026, 9, 18, 4, 58, tzinfo=dt.timezone.utc)
        erg = ah.abgleich([mk("A", "skipped", f)], [], JETZT)
        self.assertEqual(erg["gesamt"], 0)
        self.assertEqual(erg["fehlend"], 0)


class HerzschlagWorkflow(unittest.TestCase):
    """Die Verdrahtung über den Mechanismus, nicht über das Vorhandensein
    einer Datei: Was macht den Herzschlag unabhängig und selbstmeldend?"""

    def setUp(self):
        self.pfad = REPO / ".github" / "workflows" / "alerting-heartbeat.yml"
        self.text = self.pfad.read_text(encoding="utf-8")
        self.code = "\n".join(z for z in self.text.splitlines()
                              if not z.lstrip().startswith("#"))

    def test_unabhaengig_vom_beobachteten_kanal(self):
        self.assertIn("schedule:", self.code)
        self.assertRegex(self.code, r"cron:")
        self.assertNotRegex(self.code, r"workflow_run\s*:",
                            "ein Herzschlag über workflow_run schweigt genau "
                            "dann, wenn der Kanal verliert")
        self.assertIn("workflow_dispatch:", self.code)

    def test_rechte(self):
        self.assertIn("actions: read", self.code,
                      "ohne actions:read kann der Herzschlag keine Läufe zählen")
        self.assertIn("issues: write", self.code,
                      "ohne issues:write kann er sich nicht melden")

    def test_zaehlung_liegt_im_skript_nicht_im_yaml(self):
        self.assertIn("scripts/alerting_heartbeat.py --selftest", self.code)
        self.assertIn("scripts/alerting_heartbeat.py --md", self.code)
        self.assertNotIn("gh api", "\n".join(
            z for z in self.code.splitlines()
            if "alerting_heartbeat" not in z and not z.strip().startswith("gh label")),
            "die Messung gehört ins (selbsttestbare) Skript, nicht in YAML-Zeilen")

    def test_selbstmeldung_mit_schliesspfad(self):
        self.assertRegex(self.code, r"if:\s*\$\{\{\s*steps\.messung\.outcome == 'failure'\s*\}\}")
        self.assertRegex(self.code, r"if:\s*\$\{\{\s*success\(\)\s*\}\}")
        self.assertIn("gh issue create", self.code, "Befund muss ein Issue öffnen")
        self.assertIn("gh issue close", self.code, "Grün muss die Meldung schließen")
        # Der Titel kommt aus dem Skript (SSOT), nicht aus einer YAML-Kopie:
        self.assertIn("ISSUE_TITEL", self.code)
        self.assertIn("auto-report", self.code)


class Vertrag(unittest.TestCase):
    def test_im_regelwerk(self):
        sys.path.insert(0, str(REPO / "scripts"))
        import governance_contract as gc
        self.assertIn("alerting_heartbeat.py", gc.GUARDS,
                      "der Vertrag muss den Herzschlag-Selbsttest verlangen")

    def test_selbsttest_gruen_und_schreibfrei(self):
        vorher = subprocess.run(["git", "status", "--porcelain"],
                                capture_output=True, text=True, cwd=REPO).stdout
        r = subprocess.run([sys.executable, "scripts/alerting_heartbeat.py",
                            "--selftest"], capture_output=True, text=True, cwd=REPO)
        nachher = subprocess.run(["git", "status", "--porcelain"],
                                 capture_output=True, text=True, cwd=REPO).stdout
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-600:])
        self.assertEqual(vorher, nachher, "der Herzschlag-Selbsttest muss "
                                          "den Arbeitsbaum unberührt lassen (C15)")


if __name__ == "__main__":
    unittest.main()
