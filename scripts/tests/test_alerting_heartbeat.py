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
import os
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
        # WF-829B/#922: Schließen ist an eine ECHTE Zählung gebunden, nicht an
        # den Job-Erfolg. Bei totem Meldeweg bleibt die Zählung aus; `success()`
        # wäre trotzdem wahr und würde die Zustellungs-Meldung ungemessen
        # schließen. Wer nicht gemessen hat, darf nicht schließen.
        self.assertRegex(self.code,
                         r"if:\s*\$\{\{\s*steps\.kanal\.outputs\.kanal-code == '0'"
                         r"\s*&&\s*steps\.messung\.outcome == 'success'\s*\}\}")
        self.assertNotIn("${{ success() }}", self.code)
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

    def test_kanal_probe_erkennt_toten_meldeweg(self):
        def js(status, befunde):
            return lambda *a, **k: (status, list(befunde), "")

        original = ah.workflow_js_wache.pruefen
        try:
            ah.workflow_js_wache.pruefen = js(1, ["J1 .github/workflows/"
                                                  "alert-on-failure.yml:218: x"])
            erg = ah.kanal_pruefen()
            self.assertEqual(erg["status"], 1)
            self.assertTrue(erg["befunde"])
            self.assertFalse(erg["kanal"])
            self.assertIn("nicht lauffähig", ah.kanal_md(erg))

            ah.workflow_js_wache.pruefen = js(1, ["J1 .github/workflows/andere.yml:9: x"])
            self.assertEqual(ah.kanal_pruefen()["status"], 0)

            ah.workflow_js_wache.pruefen = js(2, ["J0 node fehlt"])
            self.assertEqual(ah.kanal_pruefen()["status"], 2)

            ah.workflow_js_wache.pruefen = js(0, [])
            self.assertTrue(ah.kanal_pruefen()["kanal"])
        finally:
            ah.workflow_js_wache.pruefen = original

    def test_kanal_befund_traegt_eigene_meldungsidentitaet(self):
        self.assertNotEqual(ah.ISSUE_TITEL_KANAL, ah.ISSUE_TITEL)
        self.assertIn("Kanal", ah.ISSUE_TITEL_KANAL)
        self.assertIn("Zustellung", ah.ISSUE_TITEL)

    def test_kanal_probe_laeuft_im_workflow_vor_der_zaehlung(self):
        text = (REPO / ".github" / "workflows" / "alerting-heartbeat.yml").read_text(
            encoding="utf-8")
        self.assertIn("--kanal", text)
        self.assertIn("ISSUE_TITEL_KANAL", text)
        # Erst der Kanal, dann die Zählung: Ein toter Meldeweg darf nicht
        # eine Zustellquote erzeugen, die es gar nicht geben kann.
        self.assertLess(text.index("--kanal"), text.index("--md | tee"))

    def test_toter_kanal_schliesst_keine_zustellungsmeldung(self):
        text = (REPO / ".github" / "workflows" / "alerting-heartbeat.yml").read_text(
            encoding="utf-8")
        # Schließen nur nach einer echten Zählung – ein toter Kanal ergibt
        # einen „erfolgreichen“ Job ohne Messung. Wer nicht gemessen hat,
        # darf keine offene Meldung schließen.
        self.assertIn("steps.messung.outcome == 'success'", text)
        self.assertNotIn("if: ${{ success() }}", text)

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


class DeckungsWache(unittest.TestCase):
    """Wurzelheilung H (23.11.2026): Die Wacht-Liste muss den Bestand decken.

    Der Herzschlag zählte korrekt, aber per Vertrag nur GELISTETE Läufe. Am
    23.11.2026 standen 37 der 105 Workflow-Dateien nicht auf der Liste –
    darunter vier der sechs PR-Gates und die KI-Provenienz-Wache. Die lief 8/8
    rot (12 ungeklärte Register-Fälle, 9 Tage vor der Frist 2026-12-02) und
    erzeugte KEIN Issue, obwohl ihr Befund wörtlich „braucht Menschen" sagt.
    Acht offene auto-report-Meldungen, keine für sie. Das ist Befund E
    (18.09.2026: 14 rote Gate-Läufe, null Meldungen) eine Ebene höher: Dort
    verlor der Kanal Ereignisse, hier gab es nie eines.
    """

    BESTAND = {
        ".github/workflows/gate.yml":
            {"name": "Gate", "trigger": frozenset({"push", "pull_request"})},
        ".github/workflows/nacht.yml":
            {"name": "Nachtlauf", "trigger": frozenset({"schedule"})},
        ".github/workflows/pr.yml":
            {"name": "PR-Gate", "trigger": frozenset({"pull_request"})},
    }

    def test_bestand_ist_vollstaendig_gedeckt(self):
        """Der echte Bestand: jede Datei beobachtet oder begründet ausgenommen."""
        erg = ah.deckung_pruefen()
        self.assertEqual(erg["status"], 0,
                         "Deckungslücke im echten Bestand – Rot in einem nicht "
                         "gelisteten Lauf erzeugt keine Meldung: "
                         + " | ".join(erg["befunde"]))
        self.assertEqual(erg["blind"], [])
        self.assertEqual(erg["scheindeckung"], [])
        self.assertEqual(erg["unbegruendet"], [])
        self.assertEqual(erg["verwaist"], [])
        # Gegen die leere Messung: Der Bestand muss wirklich gezählt worden sein.
        self.assertGreaterEqual(erg["bestand"], 50)
        self.assertGreaterEqual(len(erg["gelistet"]), 50)
        bestand = ah.workflow_bestand()
        namen = {info["name"] for info in bestand.values()}
        self.assertEqual(len(namen), erg["bestand"],
                         "jede Workflow-Datei muss einen Namen tragen, sonst ist "
                         "die Deckung nicht vollständig messbar")
        abgedeckt = set(erg["gelistet"]) | set(erg["ausnahmen"])
        self.assertEqual(sorted(namen - abgedeckt), [],
                         "Workflow ohne Deckung und ohne begründete Ausnahme")

    def test_blinder_workflow_wird_benannt(self):
        """Richtung 1: ein main-fähiger Lauf ohne Eintrag ist ein Befund."""
        erg = ah.deckung_pruefen(gelistet=["Gate"], bestand=self.BESTAND,
                                 ausnahmen={"PR-Gate"})
        self.assertEqual(erg["status"], 1)
        self.assertEqual([n for _p, n, _t in erg["blind"]], ["Nachtlauf"])
        self.assertIn("Nachtlauf", erg["befunde"][0],
                      "der Befund muss den blinden Workflow beim Namen nennen – "
                      "eine Zahl ohne Namen ist nicht handelbar")

    def test_begruendete_ausnahme_heilt_denselben_fall(self):
        """Richtung 2: dieselbe Lücke, mit Grund ausgenommen, ist grün."""
        erg = ah.deckung_pruefen(gelistet=["Gate"], bestand=self.BESTAND,
                                 ausnahmen={"PR-Gate", "Nachtlauf"})
        self.assertEqual(erg["status"], 0, erg["befunde"])
        self.assertEqual(erg["blind"], [])

    def test_scheindeckung_pr_only_gelistet(self):
        """PR-only gelistet = Schein-Deckung: #343 unterdrückt jede Meldung."""
        erg = ah.deckung_pruefen(gelistet=["Gate", "Nachtlauf", "PR-Gate"],
                                 bestand=self.BESTAND, ausnahmen=set())
        self.assertEqual(erg["status"], 1)
        self.assertEqual([n for _p, n, _t in erg["scheindeckung"]], ["PR-Gate"])

    def test_unbegruendete_luecke_pr_only(self):
        """PR-only ohne Eintrag und ohne Grund ist eine unbegründete Lücke."""
        erg = ah.deckung_pruefen(gelistet=["Gate", "Nachtlauf"],
                                 bestand=self.BESTAND, ausnahmen=set())
        self.assertEqual(erg["status"], 1)
        self.assertEqual([n for _p, n, _t in erg["unbegruendet"]], ["PR-Gate"])

    def test_verwaister_listeneintrag(self):
        """Ein Name ohne passende Datei feuert nie wieder – stille Blindheit."""
        erg = ah.deckung_pruefen(gelistet=["Gate", "Nachtlauf", "Alt-Name"],
                                 bestand=self.BESTAND, ausnahmen={"PR-Gate"})
        self.assertEqual(erg["status"], 1)
        self.assertEqual(erg["verwaist"], ["Alt-Name"])

    def test_leere_liste_ist_nicht_gruen(self):
        """Keine Wacht-Liste = nicht messbar (C33), niemals grün."""
        erg = ah.deckung_pruefen(gelistet=[], bestand=self.BESTAND,
                                 ausnahmen=set())
        self.assertEqual(erg["status"], 2)

    def test_ausnahmen_werden_gelesen_nicht_abgetippt(self):
        """Die Ausnahmen kommen aus dem Kopf der Datei; fehlt der Marker, gilt
        alles als blind – fail-closed in die sichere Richtung."""
        text = ('# BEWUSST NICHT ÜBERWACHT:\n'
                '#    - "Fehler-Alerting" selbst (kann sich nicht selbst '
                'beobachten)\n'
                '#    - "PR-Gate" – läuft ausschließlich auf pull_request\n'
                '# ============================================================\n')
        self.assertEqual(ah.bewusst_nicht_beobachtet(text),
                         {"Fehler-Alerting", "PR-Gate"})
        self.assertEqual(ah.bewusst_nicht_beobachtet("# Kopf ohne Marker\n"),
                         set(), "Ausnahmen dürfen nie erfunden werden")
        self.assertEqual(ah.bewusst_nicht_beobachtet(
            '# BEWUSST NICHT ÜBERWACHT:\n#    - "X"\nname: Echt\n'), {"X"},
            "der Ausnahmeblock muss am Ende des Kopfblocks enden")

    def test_sabotage_gegenprobe_ist_rot(self):
        """Ohne einen echten Namen MUSS die Wache rot werden – sonst ist das
        Grün oben leer (dieselbe Lehre wie die Sabotage-Proben in sprachkern)."""
        echt = ah.deckung_pruefen()
        self.assertIn("KI-Provenienz-Wache", echt["gelistet"],
                      "der belegte Schadensfall muss auf der Wacht-Liste stehen")
        sabotiert = [n for n in echt["gelistet"] if n != "KI-Provenienz-Wache"]
        erg = ah.deckung_pruefen(gelistet=sabotiert,
                                 bestand=ah.workflow_bestand(),
                                 ausnahmen=set(echt["ausnahmen"]))
        self.assertEqual(erg["status"], 1)
        self.assertIn("KI-Provenienz-Wache",
                      [n for _p, n, _t in erg["blind"]])

    def test_gates_des_auftrags_sind_gelistet(self):
        """Die sechs Gates des Auftrags dürfen nie wieder blind sein."""
        erg = ah.deckung_pruefen()
        for name in ("Entity-Marken-Gate (Marken-Identität)",
                     "YMYL-Siegelwache",
                     "Integritäts-Lock (PR-Gate)",
                     "E2E-Tests (Playwright)",
                     "Skript-Syntax (liegender Stand)",
                     "Qualitäts-Gate (Build + interne Links)",
                     "KI-Provenienz-Wache"):
            self.assertIn(name, erg["gelistet"],
                          f"`{name}` fehlt auf der Wacht-Liste – rot auf main "
                          "würde keine Meldung erzeugen")
        # SEO-Parität trägt den Job „Gate (Frontmatter, ohne Build)".
        self.assertTrue(any(n.startswith("SEO-Parität") for n in erg["gelistet"]),
                        "SEO-Parität trägt den Job „Gate (Frontmatter, ohne "
                        "Build)“ und fehlt auf der Wacht-Liste")

    def test_deckung_laeuft_ohne_token(self):
        """Die Prüfung ist statisch: ohne Token/API bleibt sie aussagefähig."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
        r = subprocess.run([sys.executable, "scripts/alerting_heartbeat.py"],
                           capture_output=True, text=True, cwd=REPO, env=env)
        self.assertEqual(r.returncode, 2, "ohne Token darf nichts grün sein")
        self.assertIn("Deckung der Wacht-Liste", r.stdout,
                      "die netzunabhängige Deckung muss auch ohne Token "
                      "gemessen und gemeldet werden")

    def test_deckung_als_zuruf(self):
        r = subprocess.run([sys.executable, "scripts/alerting_heartbeat.py",
                            "--deckung"], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-700:])
        self.assertIn("BLIND", r.stdout)


if __name__ == "__main__":
    unittest.main()
