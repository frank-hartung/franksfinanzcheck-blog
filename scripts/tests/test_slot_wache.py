"""Regressions-Tests der Slot-Wache (Issue #601 – Tagesdefizit 05.10.2026).

Am Montag, den 05.10.2026, lieferte GitHubs Scheduler 4 von 7 planmäßigen
Slots der Content-Linie nicht: Engine-Haupt-Slot 06:10 UTC und Engine-
Fallback 17:40 UTC starteten nie, Kadenz 10:35/16:35 kamen erst um 19:22
UTC. Ein Lauf, der nie startet, wird nie rot – am Abend stand der Tag bei
1/2 LIVE, und das Defizit-Issue empfahl Themen-Kapazität statt der
Ursache. Die Slot-Wache (scripts/slot_wache.py + slot-wache.yml) schließt
diese Lücke. Diese Tests frieren ihre Zusagen ein:

  1. Der Slot-Plan stammt aus den Workflow-Dateien selbst (geparst, nie
     abgetippt) – Engine 3 Slots (06:10/14:10/17:40), Kadenz 4 Slots
     (10:35/16:35/19:35/21:35), nur an Mo/Mi/Fr.
  2. Das Urteil: Soll + Gnadenfrist ohne einzigen Laufversuch = verpasst.
     Ein FEHLGESCHLAGENER oder LAUFENDER Lauf bedient den Slot (laut,
     kein Auto-Retry) – exakt die Newsletter-Kadenz-Disziplin.
  3. Die Eingriffe sind begrenzt: Quote erfüllt → schweigen; ein Dispatch
     je Workflow und Tick; Defizit-Meldung erst, wenn nichts mehr
     nachholbar ist oder der Dispatch scheiterte.
  4. Der Workflow-Vertrag: slot-wache.yml ruft den Selbsttest VOR der
     Messung, hat actions:write (Nachhol-Dispatch) und issues:write
     (Defizit-Notmeldung) und steht in der Wacht-Liste des Fehler-
     Alertings. Engine und Kadenz brauchen workflow_dispatch – ohne ihn
     kann die Wache nicht heilen (der Vertrag wird unten erzwungen).
  5. Die Wache steht in governance_contract.GUARDS (der Vertrag verlangt
     ihren Selbsttest) und ist selbst nicht ihr eigener Wachtposten.
  6. Das Defizit-Issue nennt die Ursache: engine_issue._diagnose() hängt
     das Slot-Protokoll an den Alarm (fail-open).

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import datetime as dt
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slot_wache as sw  # noqa: E402

MONTAG = dt.date(2026, 10, 5)          # der Vorfallstag (Mo, Publikationstag)
DIENSTAG = dt.date(2026, 10, 6)
SAMSTAG = dt.date(2026, 10, 10)


def lauf(cid, erstellt, status="completed", conclusion="success"):
    return {"id": cid, "status": status, "conclusion": conclusion,
            "created_at": erstellt,
            "url": f"https://example.invalid/{cid}", "event": "schedule"}


def slots_montag():
    slots, _warnungen = sw.slots_fuer_tag(MONTAG)
    return slots


class SlotPlanTests(unittest.TestCase):
    """Der Soll-Plan kommt aus den Workflow-Dateien – geparsed, nie kopiert."""

    def test_allebenannte_workflows_existieren(self):
        for datei, _name in sw.WORKFLOWS:
            self.assertTrue((REPO / ".github" / "workflows" / datei).exists(),
                            f"{datei} fehlt")

    def test_geplante_slots_engine_und_kadenz(self):
        slots = slots_montag()
        engine = [s["soll"].strftime("%H:%M") for s in slots
                  if s["datei"] == "content-engine-v2.yml"]
        kadenz = [s["soll"].strftime("%H:%M") for s in slots
                  if s["datei"] == "kadenz-endkontrolle.yml"]
        self.assertEqual(engine, ["06:10", "14:10", "17:40"])
        self.assertEqual(kadenz, ["10:35", "16:35", "19:35", "21:35"])

    def test_nur_an_publikationstagen(self):
        for tag in (DIENSTAG, SAMSTAG):
            slots, _w = sw.slots_fuer_tag(tag)
            self.assertEqual(slots, [], f"{tag} darf keine Slots planen")

    def test_fehlende_workflow_datei_macht_laut(self):
        slots, warnungen = sw.slots_fuer_tag(
            MONTAG, workflows=(("gibt-es-nicht.yml", "Phantom"),),
            workflows_dir=str(REPO / ".github" / "workflows"))
        self.assertEqual(slots, [])
        self.assertTrue(any("nicht lesbar" in w for w in warnungen),
                        f"Warnung fehlt: {warnungen}")

    def test_cron_syntax_kanone(self):
        """Nicht verstandene Syntax wird abgelehnt, nicht geraten."""
        self.assertEqual(sw.cron_zeiten_heute("*/20 * * * *", MONTAG), [])
        self.assertEqual(sw.cron_zeiten_heute("10 6 5 10 *", MONTAG), [])
        self.assertEqual(sw.cron_zeiten_heute("10-12 6 * * 1", MONTAG), [])
        # DOW-Wandlung: cron zählt Sonntag=0, Python Montag=0.
        sonntag = sw.cron_zeiten_heute("10 6 * * 0", dt.date(2026, 10, 11))
        self.assertEqual([z.weekday() for z in sonntag], [6])
        dienstag = sw.cron_zeiten_heute("10 6 * * 1,3,5", DIENSTAG)
        self.assertEqual(dienstag, [])
        ok = sw.cron_zeiten_heute("10 6 * * 1,3,5", MONTAG)
        self.assertEqual([z.strftime("%H:%M") for z in ok], ["06:10"])


class EntscheidungsTests(unittest.TestCase):
    """Die reine Entscheidung – ohne Netz, ohne Schreibzugriff."""

    def setUp(self):
        self.slots = slots_montag()
        self.jetzt = dt.datetime(2026, 10, 5, 19, 30, tzinfo=dt.timezone.utc)
        # Der reale 05.10.: Engine lief nur 14:32 (rot), Kadenz nur 19:22 (rot).
        self.laeufe = {
            "content-engine-v2.yml": [lauf("e1", "2026-10-05T14:32:15Z",
                                           conclusion="failure")],
            "kadenz-endkontrolle.yml": [lauf("k1", "2026-10-05T19:22:22Z",
                                             conclusion="failure")],
        }

    def test_vorfall_nachgestellt(self):
        erg = sw.entscheide(self.jetzt, self.slots, self.laeufe, 1, 2)
        z = {(s["datei"], s["soll"][11:16]): s["zustand"] for s in erg["slots"]}
        self.assertEqual(z[("content-engine-v2.yml", "06:10")], "bedient")
        self.assertEqual(z[("content-engine-v2.yml", "14:10")], "bedient")
        self.assertEqual(z[("content-engine-v2.yml", "17:40")], "verpasst")
        self.assertEqual(z[("kadenz-endkontrolle.yml", "10:35")], "bedient")
        self.assertEqual(z[("kadenz-endkontrolle.yml", "16:35")], "bedient")
        self.assertEqual(z[("kadenz-endkontrolle.yml", "19:35")], "wartet")
        self.assertEqual(erg["handlung"], "nachholen")
        self.assertEqual(erg["nachholen"], ["content-engine-v2.yml"])

    def test_ziel_erreicht_schweigt(self):
        erg = sw.entscheide(self.jetzt, self.slots, self.laeufe, 2, 2)
        self.assertEqual(erg["handlung"], "ziel-erreicht")
        self.assertEqual(erg["nachholen"], [])

    def test_gnadenfrist_grenze(self):
        """45 Minuten: um 06:54 wartet der 06:10-Slot, um 06:56 ist er weg."""
        for uhr, erwartet in ((dt.time(6, 54), "wartet"),
                              (dt.time(6, 56), "verpasst")):
            jetzt = dt.datetime.combine(MONTAG, uhr,
                                        tzinfo=dt.timezone.utc)
            erg = sw.entscheide(jetzt, self.slots, {}, 0, 2)
            zustand = [s for s in erg["slots"]
                       if s["datei"] == "content-engine-v2.yml"
                       and s["soll"][11:16] == "06:10"][0]["zustand"]
            self.assertEqual(zustand, erwartet, f"{uhr}: {zustand}")

    def test_rote_und_laufende_laeufe_bedienen(self):
        laeufe = {"content-engine-v2.yml": [
            lauf("rot", "2026-10-05T06:12:00Z", conclusion="failure"),
            lauf("weg", "2026-10-05T06:15:00Z", status="in_progress")]}
        erg = sw.entscheide(dt.datetime(2026, 10, 5, 7, 0,
                                        tzinfo=dt.timezone.utc),
                            self.slots, laeufe, 0, 2)
        erster = erg["slots"][0]
        self.assertEqual(erster["zustand"], "bedient")
        self.assertEqual(erster["lauf"]["id"], "rot")
        self.assertNotIn("content-engine-v2.yml", erg["nachholen"])

    def test_muell_timestamp_bedient_nichts(self):
        laeufe = {"content-engine-v2.yml": [
            {"id": "x", "status": "completed", "conclusion": "success",
             "created_at": "Müll", "url": "", "event": "schedule"}]}
        erg = sw.entscheide(dt.datetime(2026, 10, 5, 7, 0,
                                        tzinfo=dt.timezone.utc),
                            self.slots, laeufe, 0, 2)
        self.assertEqual(erg["slots"][0]["zustand"], "verpasst")

    def test_ein_dispatch_je_workflow(self):
        jetzt = dt.datetime(2026, 10, 5, 20, 30, tzinfo=dt.timezone.utc)
        erg = sw.entscheide(jetzt, self.slots,
                            {d: [] for d, _n in sw.WORKFLOWS}, 1, 2)
        self.assertEqual(erg["nachholen"],
                         ["content-engine-v2.yml", "kadenz-endkontrolle.yml"])

    def test_defizit_fenster(self):
        """Nach letztem Slot + Gnadenfrist (22:20 UTC) wird gemeldet –
        außer ein Slot ist noch nachholbar, dann wiegt der Dispatch."""
        spaet = dt.datetime(2026, 10, 5, 22, 21, tzinfo=dt.timezone.utc)
        alles = {**self.laeufe,
                 "content-engine-v2.yml": self.laeufe[
                     "content-engine-v2.yml"] + [
                     lauf("e2", "2026-10-05T18:00:00Z", conclusion="failure")],
                 "kadenz-endkontrolle.yml": self.laeufe[
                     "kadenz-endkontrolle.yml"] + [
                     lauf("k2", "2026-10-05T21:40:00Z", conclusion="failure")]}
        erg = sw.entscheide(spaet, self.slots, alles, 1, 2)
        self.assertEqual(erg["handlung"], "defizit-melden")
        self.assertTrue(erg["defizit"])
        # Noch nachholbar → Dispatch zuerst, kein vorzeitiger Alarm.
        erg = sw.entscheide(spaet, self.slots, self.laeufe, 1, 2)
        self.assertEqual(erg["handlung"], "nachholen")

    def test_ruhetag(self):
        erg = sw.entscheide(dt.datetime(2026, 10, 10, 12, 0,
                                        tzinfo=dt.timezone.utc),
                            [], {}, 0, 2)
        self.assertEqual(erg["handlung"], "ruhetag")

    def test_blindheit_ist_befund(self):
        erg = sw.entscheide(self.jetzt, [], {}, 0, 2)
        self.assertEqual(erg["handlung"], "blind")


class VerdrahtungsTests(unittest.TestCase):
    """pruefen()-Verträge: Trockenlauf, Messbarkeit, kein stiller Dispatch."""

    def setUp(self):
        self.slots = slots_montag()
        self.jetzt = dt.datetime(2026, 10, 5, 19, 30, tzinfo=dt.timezone.utc)
        self.laeufe = {
            "content-engine-v2.yml": [lauf("e1", "2026-10-05T14:32:15Z")],
            "kadenz-endkontrolle.yml": [lauf("k1", "2026-10-05T19:22:22Z")],
        }

    def test_trockenlauf_befund_rc1(self):
        erg = sw.pruefen("org/repo", jetzt=self.jetzt, ohne_dispatch=True,
                         laeufe_je_workflow=self.laeufe, live_heute=1,
                         minimum=2, slots=self.slots)
        self.assertEqual(erg["rc"], 1)
        self.assertTrue(all("übersprungen" in d for d in erg["dispatches"]))

    def test_ziel_rc0(self):
        erg = sw.pruefen("org/repo", jetzt=self.jetzt, ohne_dispatch=True,
                         laeufe_je_workflow=self.laeufe, live_heute=2,
                         minimum=2, slots=self.slots)
        self.assertEqual(erg["rc"], 0)

    def test_ohne_repo_kein_stiller_dispatch(self):
        erg = sw.pruefen("", jetzt=self.jetzt, ohne_dispatch=False,
                         laeufe_je_workflow=self.laeufe, live_heute=1,
                         minimum=2, slots=self.slots)
        self.assertEqual(erg["rc"], 1)
        self.assertTrue(all("nicht möglich" in d for d in erg["dispatches"]))

    def test_ruhetag_ohne_netz_und_ohne_gh(self):
        """An Di/Do/Sa/So wird kein Laufbuch gelesen und nichts verlangt."""
        erg = sw.pruefen("org/repo",
                         jetzt=dt.datetime(2026, 10, 10, 12, 0,
                                           tzinfo=dt.timezone.utc),
                         ohne_dispatch=False)
        self.assertEqual(erg["rc"], 0)
        self.assertEqual(erg["handlung"], "ruhetag")
        self.assertEqual(erg["dispatches"], [])

    def test_defizit_meldung_nur_wenn_nichts_mehr_nachholbar(self):
        spaet = dt.datetime(2026, 10, 5, 22, 21, tzinfo=dt.timezone.utc)
        alles = {"content-engine-v2.yml": [
                    lauf("e1", "2026-10-05T14:32:15Z"),
                    lauf("e2", "2026-10-05T18:00:00Z")],
                 "kadenz-endkontrolle.yml": [
                     lauf("k1", "2026-10-05T19:22:22Z"),
                     lauf("k2", "2026-10-05T21:40:00Z")]}
        erg = sw.pruefen("org/repo", jetzt=spaet, ohne_dispatch=True,
                         laeufe_je_workflow=alles, live_heute=1, minimum=2,
                         slots=self.slots)
        self.assertEqual(erg["handlung"], "defizit-melden")
        self.assertIn("übersprungen", erg["defizit_meldung"])

    def test_blinde_messung_handelt_nicht(self):
        """Ist das Laufbuch nicht lesbar, zeigt der Bericht „unbekannt“
        statt „verpasst“ – und es wird nicht blind dispatcht."""
        jetzt = dt.datetime(2026, 10, 5, 19, 30, tzinfo=dt.timezone.utc)

        def kaputter_lader(_repo, datei):
            if datei == "content-engine-v2.yml":
                raise RuntimeError("Laufbuch nicht lesbar")
            return [lauf("k1", "2026-10-05T19:22:22Z")]

        erg = sw.pruefen("org/repo", jetzt=jetzt, ohne_dispatch=False,
                         live_heute=1, minimum=2, slots=slots_montag(),
                         lade_laeufe_fn=kaputter_lader)
        self.assertEqual(erg["rc"], 1)
        self.assertNotIn("content-engine-v2.yml", erg["nachholen"])
        engine_slots = [(s["soll"][11:16], s["zustand"]) for s in erg["slots"]
                        if s["datei"] == "content-engine-v2.yml"]
        self.assertIn(("17:40", "unbekannt"), engine_slots)
        self.assertNotIn(("17:40", "verpasst"), engine_slots)


class WorkflowVertragTests(unittest.TestCase):
    """Die Wache ist nur so gut wie ihr Arbeitsgerät (slot-wache.yml)."""

    def setUp(self):
        self.wache = (REPO / ".github" / "workflows" / "slot-wache.yml").read_text(
            encoding="utf-8")

    def test_selbsttest_vor_messung(self):
        self.assertLess(self.wache.index("--selftest"),
                        self.wache.index("--pruefen"))

    def test_rechte_fuer_nachhol_und_defizit(self):
        self.assertIn("actions: write", self.wache)
        self.assertIn("issues: write", self.wache)

    def test_haeufiger_cron(self):
        """Ein Netz am selben Haken braucht viele Ticks: min. alle 30 min."""
        self.assertIn('cron: "*/20 * * * *"', self.wache)

    def test_engine_und_kadenz_sind_dispatchfaehig(self):
        """Ohne workflow_dispatch kann die Wache nicht heilen – Vertrag."""
        for datei, _name in sw.WORKFLOWS:
            text = (REPO / ".github" / "workflows" / datei).read_text(
                encoding="utf-8")
            self.assertIn("workflow_dispatch", text,
                          f"{datei} ohne workflow_dispatch – Nachholen unmöglich")

    def test_wache_steht_in_der_wacht_liste_des_alertings(self):
        alerting = (REPO / ".github" / "workflows" /
                    "alert-on-failure.yml").read_text(encoding="utf-8")
        self.assertIn("Slot-Wache (Content-Slots nachziehen)", alerting)

    def test_wache_im_governance_vertrag(self):
        governance = (REPO / "scripts" / "governance_contract.py").read_text(
            encoding="utf-8")
        self.assertIn("slot_wache.py", governance)

    def test_defizit_issue_nennt_slot_protokoll(self):
        """engine_issue._diagnose() hängt das Slot-Protokoll an (fail-open)."""
        quelle = (REPO / "scripts" / "engine_issue.py").read_text(
            encoding="utf-8")
        self.assertIn("slot_wache", quelle)
        self.assertIn("Slot-Protokoll", quelle)


class SelbsttestVertrag(unittest.TestCase):
    """Der Selbsttest selbst muss grün sein – und rot bei Sabotage."""

    def test_selbsttest_exit0(self):
        r = subprocess.run([sys.executable,
                            str(REPO / "scripts" / "slot_wache.py"),
                            "--selftest"], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_sabotage_gnadenfrist_wird_rote_wache(self):
        """Verdoppelt jemand die Gnadenfrist still, muss ein Test rot werden:
        Die Grenze 45 min ist eine Entscheidung, kein Vorschlag."""
        quelle = (REPO / "scripts" / "slot_wache.py").read_text(
            encoding="utf-8")
        self.assertIn("GNADENFRIST = dt.timedelta(minutes=45)", quelle)


if __name__ == "__main__":
    unittest.main()
