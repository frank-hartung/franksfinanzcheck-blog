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
 9. LAGEBILD (WF-9E5A / #761; Lagebild-Verfall WF-E813 / #815, 26.10.2026):
    Eine offene Meldung behält nicht für immer den Rat des ersten roten
    Laufs. Die Klasse des Rats steht als Marker im Body
    (<!-- alert-runbook: … -->); ändert sie sich, schreibt der nächste
    rote Lauf die Meldung neu – nur bei bekannter Job-Lage und fail-open.
    Bleibt die Klasse gleich, vergleicht der Skript die im Body
    aufgezeichnete Lauf-ID mit der aktuellen: Ein jüngerer Lauf erneuert
    den Lauf-Nachweis (Lagebild-Verfall), ein gleicher oder älterer Lauf
    (Redelivery, verspätete Zustellung) lässt den Body unangetastet.
 10. JOBBEWEIS (WF-E813 / #809): „Behoben“ schließt nur noch Meldungen,
     deren gemeldete Jobs im auflösenden Lauf vorhanden und `success` sind
     (Marker <!-- alert-jobs: [...] -->, scripts/alert_resolve_gate.py).
     Ein grüner Push-Lauf, der die bedingte Live-Messung aussparte, schloss
     zuvor #782/#798 mit „läuft wieder fehlerfrei“ – WF-E813 meldete sich
     deshalb viermal in fünf Tagen. Verhalten: eigene Unit-Tests in
     scripts/tests/test_alert_resolve_gate.py.

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

    def test_wf_9e5a_backup_einrichtung_hat_eigenes_runbook(self):
        # Issue #761: Ein fail-closed roter „Voraussetzungen prüfen“-Schritt im
        # Offsite-Backup ist eine Einrichtungsaufgabe. Der Rat „API-Key (GROQ/
        # GEMINI) / neu starten“ führte in die Irre. Die Klassen sind an den
        # Workflow gebunden und verweisen auf die Anleitung, die der Prüfer
        # (scripts/backup_einrichtung.py) ebenfalls nennt.
        self.assertIn("wfName === 'Offsite-Backup'", self.code)
        self.assertIn("includes('Voraussetzungen prüfen')", self.code)
        self.assertIn("includes('Fristwarnung')", self.code)
        self.assertIn("Einrichtung unvollständig – ein Neustart hilft nicht", self.code)
        anleitung = REPO / "docs" / "ANLEITUNG-OFFSITE-BACKUP.md"
        self.assertIn("`docs/ANLEITUNG-OFFSITE-BACKUP.md`", self.code)
        self.assertTrue(anleitung.is_file(), "Die im Alarm genannte Anleitung muss existieren.")
        # Der Rat verlinkt die Läufe über den Dateinamen des Workflows. Wird die
        # Datei umbenannt, zeigt der Link ins Leere; heißt der Workflow anders,
        # greift die Bindung an wfName nicht mehr.
        self.assertIn("/actions/workflows/backup-offsite.yml'", self.code)
        workflow = REPO / ".github" / "workflows" / "backup-offsite.yml"
        self.assertTrue(workflow.is_file(), "Link-Ziel backup-offsite.yml fehlt.")
        self.assertRegex(workflow.read_text(encoding="utf-8"), r"(?m)^name:\s*Offsite-Backup\s*$",
                         "backup-offsite.yml muss der Workflow „Offsite-Backup“ sein (wfName-Bindung).")

    def test_wf_53e2_roter_selbsttest_hat_eigenes_runbook(self):
        # WF-53E2 / #780 (16.10.2026): Der Detektor-Selbsttest der Affiliate-
        # Wache war nach einem Merge rot; die Meldung riet zu GROQ/GEMINI und
        # zum Neustart. Selbsttests laufen offline mit Attrappen-Schlüsseln –
        # rot ist dort immer Code. Entscheidend ist der ERSTE rote Schritt
        # (die Schlussbewertung danach ist Folge), und jede spezifische
        # Klasse behält Vorrang: der Selbsttest-Rat steht direkt vor dem
        # Rückfall „allgemein“. Verhalten: Simulation (#780-Szenarien).
        self.assertIn("const ersterRoterSchritt = String(failedStepNames[0] || '');", self.code)
        self.assertIn("/Selbsttest|Selftest/i.test(ersterRoterSchritt)", self.code)
        m = re.search(r"const runbookKlasse = (.*?);", self.code, re.S)
        self.assertIsNotNone(m)
        klassen = re.findall(r"'([a-z-]+)'", m.group(1))
        self.assertEqual(klassen[-2:], ["selbsttest", "allgemein"],
                         "Selbsttest-Rat gehört hinter alle spezifischen Klassen, vor den Rückfall")
        self.assertIn("python3 scripts/selftest_runner.py", self.code)
        self.assertIn("ein Neustart liefert dasselbe Rot", self.code)
        self.assertTrue((REPO / "scripts" / "selftest_runner.py").is_file(),
                        "der im Rat genannte Runner muss existieren")

    def test_wf_7b6b_925_messgate_hat_eigenes_runbook(self):
        # WF-7B6B / #925 (29.10.2026): Der nächtliche E2E-Lauf wurde rot im
        # Schritt „Snippet-Gate – Snippetfenster und Rangfolge" (Description
        # 153 Zeichen / 1011 px). Die Meldung riet zu API-Schlüsseln,
        # GitHub-Ausfall und Neustart – drei Ursachen, die einen Messschritt
        # am gebauten HTML nicht rot machen können. Seitdem haben die
        # Messgates des E2E-Laufs einen eigenen Rat; spezifische Klassen
        # (Engine, Backup, Sicherheit, CodeQL, Skript-Syntax) behalten
        # Vorrang, der Selbsttest-Rat bleibt direkt vor dem Rückfall.
        self.assertIn("const istE2E = wfName === 'E2E-Tests (Playwright)';", self.code)
        self.assertIn("/Snippet-Gate|Metadaten-Wache|Linktext-Wache|H1-Wache/i.test(String(s))",
                      self.code)
        m = re.search(r"const runbookKlasse = (.*?);", self.code, re.S)
        self.assertIsNotNone(m)
        klassen = re.findall(r"'([a-z-]+)'", m.group(1))
        self.assertIn("messgate-bestand", klassen)
        self.assertEqual(klassen[-2:], ["selbsttest", "allgemein"],
                         "der Selbsttest-Rat bleibt direkt vor dem Rückfall")
        self.assertIn("scripts/serp_limits.py", self.code)
        self.assertIn("metadaten_wache.py --fix", self.code)
        self.assertIn("scripts.tests.test_keyword_optimizer", self.code)
        # Statische Absicherung der Verhaltens-Probe: wo node fehlt, überspringt
        # die Simulation. Das Szenario muss trotzdem existieren, sonst fällt
        # die Klasse unbemerkt aus der Simulation heraus.
        sim_pfad = REPO / "scripts" / "tests" / "sim" / "alert_scoping_sim.mjs"
        sim_text = sim_pfad.read_text(encoding="utf-8")
        self.assertIn("messgate-bestand", sim_text,
                      "Simulation ohne #925-Szenario – die Klasse wäre dort nicht geprüft")
        self.assertIn("Snippet-Gate – Snippetfenster und Rangfolge", sim_text)
        self.assertIn("#925-Gegenprobe", sim_text,
                      "ohne Gegenprobe fehlt der Beleg, dass nur die Messgates umziehen")

    def test_offene_meldung_wird_bei_klassenwechsel_nachgefuehrt(self):
        # WF-9E5A / #761: Die Meldung entstand, bevor es die Klasse
        # „Einrichtung unvollständig“ gab, und riet zu GROQ/GEMINI. Der
        # Dedupe-Pfad fasste offene Meldungen nie an – der falsche Rat wäre bis
        # zum ersten grünen Lauf stehen geblieben. Vertrag: Die Klasse des Rats
        # steht als Marker im Body; nachgeführt wird nur bei Klassenwechsel,
        # nur bei bekannter Job-Lage und fail-open. Verhalten: Simulation.
        self.assertIn("const runbookMarker = '<!-- alert-runbook: ' + runbookKlasse + ' -->';", self.code)
        m = re.search(r"const runbookKlasse = (.*?);", self.code, re.S)
        self.assertIsNotNone(m, "runbookKlasse fehlt – ohne Klasse kein Nachführen")
        deklariert = re.findall(r"'([a-z-]+)'", m.group(1))
        self.assertEqual(deklariert[-1], "allgemein", "Rückfallklasse muss „allgemein“ sein")
        self.assertEqual(len(deklariert), len(set(deklariert)), "Klassennamen doppelt vergeben")
        gewaehlt = re.findall(r"runbookKlasse === '([a-z-]+)'", self.code)
        # Jede Klasse hat genau einen Rat – und jeder Rat eine deklarierte Klasse.
        self.assertEqual(sorted(gewaehlt), sorted(deklariert[:-1]),
                         "Runbook-Wahl und Klassen laufen auseinander")
        pos_dedupe = self.code.find("if (open.length > 0)")
        pos_waechter = self.code.find("if (!jobsKnown)", pos_dedupe)
        pos_gleich = self.code.find("treffer.body.indexOf(runbookMarker) !== -1", pos_dedupe)
        pos_nach = self.code.find("nachzufuehren = treffer;", pos_dedupe)
        self.assertTrue(-1 < pos_dedupe < pos_waechter < pos_gleich < pos_nach,
                        "Reihenfolge im Dedupe-Pfad: Job-Lage → gleiche Klasse → nachführen")
        self.assertRegex(self.code, r"ident\.marker,\s*\n\s*runbookMarker,",
                         "Klassen-Marker gehört direkt hinter den Identitäts-Marker")
        # Den Block exakt eingrenzen: vom Nachführen bis zum Anlegen. Ein
        # großzügiges Fenster sähe sonst das catch der Label-Garantie dahinter.
        # Seit dem Lagebild-Verfall (WF-E813/#815, 26.10.2026) bedient derselbe
        # Block auch die Frischhaltung bei gleichem Rat und jüngerem Lauf.
        start = self.code.find("if (nachzufuehren) {\n              try {")
        ende = self.code.find("github.rest.issues.createLabel(", start)
        self.assertTrue(-1 < start < ende < self.code.find("github.rest.issues.create(", ende),
                        "Nachführen muss vor dem Anlegen entscheiden (sonst Duplikat)")
        block = self.code[start:ende]
        self.assertIn("github.rest.issues.update(", block)
        self.assertIn("} catch (e) {", block, "Nachführen muss fail-open sein")
        self.assertIn("return;", block, "Nach dem Nachführen darf kein Duplikat entstehen")

    def test_stille_frischhaltung_bei_gleichem_rat_aber_neuem_lauf(self):
        # WF-9E5A / #761 und WF-E813 / #815 (26.10.2026): Eine offene Meldung
        # verwies tagelang auf einen alten Lauf, obwohl ihr Body behauptete,
        # aktuell zu sein – der alte Dedupe-Pfad schwieg bei gleichem
        # Klassen-Marker komplett. Vertrag: Bei gleichem Rat wird die im Body
        # aufgezeichnete Lauf-ID mit der aktuellen verglichen. Ein jüngerer
        # Lauf schreibt die Meldung über den bestehenden Nachführ-Pfad neu;
        # ein gleicher oder älterer Lauf (Redelivery, verspätete Zustellung)
        # bleibt unangetastet.
        code = self.code
        pos_dedupe = code.find("if (open.length > 0)")
        pos_marker = code.find("treffer.body.indexOf(runbookMarker) !== -1", pos_dedupe)
        # Die Lauf-ID wird per Regex aus dem Body gelesen (Run- und Job-URL).
        self.assertIn("/(?:actions\\/)?runs\\/(\\d+)/", code)
        pos_regex = code.find("/(?:actions\\/)?runs\\/(\\d+)/", pos_marker)
        pos_reihe = code.find("aufgezeichnetId >= Number(run.id", pos_marker)
        pos_nach = code.find("nachzufuehren = treffer;", pos_marker)
        self.assertTrue(-1 < pos_marker < pos_regex < pos_reihe < pos_nach,
                        "Im Gleiche-Klasse-Zweig erst Lauf-Alter prüfen, dann nachführen")
        # Idempotenz/Reihenfolge: aktueller oder jüngerer Body → ohne Update zurück.
        fenster = code[pos_marker:pos_nach]
        self.assertIn("return;", fenster, "Kein älteres Ereignis darf ein jüngeres Lagebild überschreiben")
        # Bei veraltetem Lauf-Nachweis fällt der Pfad auf denselben
        # fail-open-Update-Block wie der Klassenwechsel (dort bereits begrenzt).
        start = code.find("if (nachzufuehren) {\n              try {")
        ende = code.find("github.rest.issues.createLabel(", start)
        block = code[start:ende]
        self.assertIn("github.rest.issues.update(", block)
        self.assertIn("} catch (e) {", block, "Frischhaltung muss fail-open sein")
        self.assertIn("return;", block, "Nach der Frischhaltung kein Duplikat erzeugen")
        # Verhaltenstiefe: Die Simulation beweist Verfall-Erneuerung,
        # Idempotenz und den Reihenfolgeschutz gegen ältere Ereignisse.
        sim = (REPO / "scripts" / "tests" / "sim" / "alert_scoping_sim.mjs").read_text(encoding="utf-8")
        self.assertIn("Lagebild-Verfall", sim)
        self.assertIn("Reihenfolgeschutz", sim)
        self.assertIn("Nachführung idempotent", sim)

    def test_809_gleichzeitige_header_und_worker_befunde_haben_vorrang(self):
        code = _kommentarfrei(_text())
        self.assertIn("headerGateFailed && workerGateFailed ? 'sicherheit-live'", code)
        klassen = re.search(r"const runbookKlasse = (.*?);", code, re.S).group(1)
        self.assertLess(klassen.index("'sicherheit-live'"), klassen.index("'sicherheit-header'"))
        self.assertIn("workerGateFailed ? 'sicherheit-worker'", code)
        self.assertIn("liveNachweisFailed ? 'sicherheit-nachweis'", code)

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

    def test_809_live_nachweis_wird_vor_jedem_issue_abschluss_geprueft(self):
        resolve = self.raw.split("  resolve:", 1)[1]
        self.assertIn('if [ "$WF_NAME" = "Sicherheits-Wache" ]; then', resolve)
        self.assertIn("sicherheits_nachweis.py --abschluss", resolve)
        self.assertIn("RUN_EVENT:", resolve)
        self.assertIn("RUN_ID:", resolve)
        self.assertLess(resolve.index("sicherheits_nachweis.py --abschluss"), resolve.index("gh issue close"))


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

    def test_resolve_schliesst_nur_mit_jobbeweis(self):
        """Vertrag 10 (WF-E813 / #809): Ein grüner Lauf genügt nicht – der
        Job, der rot war, muss im Lauf vorhanden und grün sein. Sonst
        wiederholt sich #809 bei jedem bedingt ausgeführten Job."""
        roh = _text()
        self.assertIn("alert_resolve_gate.py", roh)
        self.assertIn("alert-jobs:", roh)
        pos_gate = roh.find("alert_resolve_gate.py")
        pos_close = roh.find("gh issue close")
        self.assertLess(pos_gate, pos_close,
                        "die Job-Prüfung muss vor `gh issue close` fallen")


class VerhaltensSimulation(unittest.TestCase):
    """Vertrag 7 (Verhalten, nicht nur Text): Das alarm-Skript wird mit
    gestubbtem github-script-Kontext WIRKLICH ausgeführt – alle Kern-
    Szenarien inkl. der exakten #343-Konstellation. Harness:
    scripts/tests/sim/alert_scoping_sim.mjs (node; GitHub-Runner bringen es
    mit; PyYAML ist für die Verhaltensprobe nicht erforderlich)."""

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
            # Der Sicherheits-Offline-Job braucht keine pip-Abhängigkeit.
            # Den einen literalen script-Block einlesen statt die wichtigste
            # Verhaltensprobe auf einem Standard-Python still zu überspringen.
            import textwrap
            zeilen = _text().split("          script: |\n", 1)[1].splitlines()
            block = []
            for zeile in zeilen:
                if zeile and not zeile.startswith("            "):
                    break
                block.append(zeile)
            skript = textwrap.dedent("\n".join(block))
            self.assertTrue(skript.strip(), "alarm-Skript fehlt")
        else:
            daten = yaml.safe_load(_text())
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
            # E2E + Deploy: WF-7B6B / #654 (Install-Diagnose) und Veröffentlichung.
            # F-09 (Sicherheitsaudit 15.10.2026): Der fünfte Name ist ABSICHTLICH
            # feindlich (Markdown, Mention, Umbruch). Die Simulation beweist, dass
            # er den Issue-Body nicht steuern kann – ein Test mit einem braven
            # Namen würde genau die Lücke nicht prüfen.
            # Offsite-Backup: WF-9E5A / #761 (Einrichtungs- und Fristklasse).
            # 26.10.2026 (WF-E813-Folgebefund): „Cloudflare-Worker deployen“
            # und „CodeQL-Sicherheitswache“ waren still rot, ohne Meldung –
            # beide gehören jetzt zur Wacht-Liste und bekommen ihre eigene
            # Triage in der Simulation geprüft.
            boeser_name = "Layout-AI` @all [Klick](http://boese.example)\nZweite Zeile"
            # „Sicherheits-Wache": WF-E813 (15.10.2026) – die Simulation prüft,
            # dass dieser Kanal seine eigene Triage bekommt und nicht den
            # Schlüssel-Rat, der für eine reine Kopfzeilen-Messung nie zutreffen
            # kann.
            # WF-53E2 / #780 (16.10.2026): Affiliate-Wache und Content-Reserve –
            # beide fielen am 16.10. an roten Selbsttests (ein Merge), beide
            # bekamen den Schlüssel-Rat. Die Simulation prüft den Selbsttest-Rat
            # an genau diesen zwei echten Kanälen.
            identitaeten = {name: ident_modul.identitaet(name)
                            for name in ("Layout-AI", "Content-Engine v2",
                                         "E2E-Tests (Playwright)", "Deploy auf GitHub Pages",
                                         "Offsite-Backup",
                                         "Sicherheits-Wache",
                                         "Affiliate-Integritäts-Wache (täglich)",
                                         "Content-Reserve (täglicher Vorrat)",
                                         "Cloudflare-Worker deployen",
                                         "CodeQL-Sicherheitswache",
                                         "Skript-Syntax (liegender Stand)",
                                         boeser_name)}
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
