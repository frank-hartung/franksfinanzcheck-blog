"""WF-E813/#809: Offline-Grün und unvollständige Messungen schließen nicht.

Der echte resolve-Shellblock läuft mit Bash -e und einem ausschließlich
lokalen gh-Doppelgänger. Kein Test kann GitHub-Issues verändern.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import blog_header_gate as header
import sicherheits_nachweis as nachweis
import worker_betrieb_wache as worker
import alert_issue_identity as identitaet


def gute_messungen():
    # Genau wie main() gehört der Markdown-Bericht auch in die JSON-Datei.
    # Die gute Ausgangslage enthält ausdrücklich auch einen abgeschlossenen
    # B7-Text; so testen Fachfälle nicht versehentlich mit einem Abschlussblocker.
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        datenschutz = wurzel / "content" / "datenschutz" / "index.md"
        datenschutz.parent.mkdir(parents=True)
        datenschutz.write_text("Cloudflare-Proxy und Zugriffsdaten sind beschrieben.", encoding="utf-8")
        with patch.object(header, "WURZEL", wurzel):
            _, bericht, kopf = header.netz_pruefen(
                holen=lambda *_: (200, {**header.GUTE_KOPFZEILEN, **header.PROXY_KENNUNG}),
                pausen=(), schlaf=lambda _: None)
    kopf["bericht"] = bericht
    stand = {"ok": True, "kv": "ok", "turnstile": "inaktiv", "schluesselrollen": "getrennt",
             "budget": {"anmeldung_heute": 3, "anmeldung_max": 100, "feedback_max": 200}, "exporte": []}
    _, _, betrieb = worker.netz_pruefen(
        "https://abos.franksfinanzcheck.de", "test-only",
        schreibschluessel="test-write-only", holen=lambda *_: stand, pausen=())
    return kopf, betrieb


def gute_jobs():
    return [{"name": nachweis.LIVE_JOB, "conclusion": "success", "steps": [
        {"name": name, "conclusion": "success"} for name in nachweis.LIVE_SCHRITTE]}]


def run_block(datei: Path, marker: str) -> str:
    rest = datei.read_text().split(marker, 1)[1]
    zeilen = rest.split("        run: |\n", 1)[1].splitlines()
    block = []
    for zeile in zeilen:
        if zeile and not zeile.startswith("          "):
            break
        block.append(zeile)
    return textwrap.dedent("\n".join(block))


class Messvertrag(unittest.TestCase):
    def test_echte_gruene_messungen_passen_zum_vertrag(self):
        kopf, betrieb = gute_messungen()
        nachweis.pruefe_messung(kopf, "header", "0")
        nachweis.pruefe_messung(betrieb, "worker", "0")
        self.assertTrue(nachweis.live_pruefen(kopf, betrieb)[0])

    def test_leere_falsche_und_offline_nachweise_sind_wache_fehler(self):
        _, gut = gute_messungen()
        for stand in (None, [], {}, {**gut, "klasse": "OFFLINE"}, {**gut, "klasse": None},
                      {**gut, "exit": True}, {**gut, "gemessen": True}, {**gut, "gemessen": 0},
                      {**gut, "bericht": ""}, {**gut, "warnungen": "alles ok"},
                      {**gut, "abschluss_blocker": "offen"}, {**gut, "abschluss_blocker": [""]},
                      {**gut, "fehlend": ["offener Befund"]}, {**gut, "stoerung": ["offline"]},
                      {**gut, "klasse": "BEFUND", "exit": 1},
                      {**gut, "klasse": "STOERUNG", "exit": 2},
                      {**gut, "klasse": "TEILWEISE"}):
            with self.subTest(stand=stand), self.assertRaises(nachweis.NachweisFehler):
                nachweis.pruefe_messung(stand, "worker", "0")

    def test_exit_aus_dem_prozess_muss_zum_json_passen(self):
        kopf, _ = gute_messungen()
        for code in ("", "1", "2", "3", "127", "null", "0\n1"):
            with self.subTest(code=code), self.assertRaises(nachweis.NachweisFehler):
                nachweis.pruefe_messung(kopf, "header", code)

    def test_stoerung_darf_keine_sicherheitsluecke_behaupten(self):
        _, _, daten = worker.netz_pruefen("", "", pausen=())
        nachweis.pruefe_messung(daten, "worker", "2")
        with self.assertRaises(nachweis.NachweisFehler):
            nachweis.pruefe_messung({**daten, "fehlend": ["erfundene Lücke"]}, "worker", "2")

    def test_teilweise_genuegt_nicht_fuer_abschluss(self):
        def holen(url, weg):
            if url == header.ZIELE[0]:
                return 200, header.GUTE_KOPFZEILEN
            raise OSError("Netz unterbrochen")
        _, bericht, kopf = header.netz_pruefen(holen=holen, pausen=(), schlaf=lambda _: None)
        kopf["bericht"] = bericht
        nachweis.pruefe_messung(kopf, "header", "0")  # CLI-Vertrag bleibt erhalten.
        _, betrieb = gute_messungen()
        ok, grund = nachweis.live_pruefen(kopf, betrieb)
        self.assertFalse(ok)
        self.assertIn("TEILWEISE", grund)

    def test_jedes_vorgesehene_ziel_und_sein_http_status_sind_erforderlich(self):
        kopf, betrieb = gute_messungen()
        for aendern in (
                lambda d: d.update(ziele=[]),
                lambda d: d.update(gemessen=1),
                lambda d: d.update(nicht_gemessen=[header.ZIELE[0]]),
                lambda d: d["ziele"][0].update(url="https://fremd.example/"),
                lambda d: d["ziele"][0].update(url=[]),
                lambda d: d["ziele"][0].update(url=None),
                lambda d: d["ziele"][0].update(status=503),
                lambda d: d["ziele"][0].update(klasse="STOERUNG"),
                lambda d: d["ziele"][0].update(fehlend=["offener Befund"]),
                lambda d: d["ziele"][1].update(url=header.ZIELE[0])):
            with self.subTest(aendern=aendern):
                stand = copy.deepcopy(kopf)
                aendern(stand)
                self.assertFalse(nachweis.live_pruefen(stand, betrieb)[0])

    def test_ungueltige_zieldaten_duerfen_nicht_abstuerzen(self):
        kopf, betrieb = gute_messungen()
        for wert in (None, "unerwartet", [None], [[], {}]):
            with self.subTest(wert=wert):
                self.assertFalse(nachweis.live_pruefen({**kopf, "ziele": wert}, betrieb)[0])

    def test_815_live_pruefen_nennt_beide_roten_saeulen_und_deckt_worker_wachefehler_auf(self):
        kopf, betrieb = gute_messungen()
        kopf_rot = {**kopf, "exit": 1, "klasse": "BEFUND", "fehlend": ["HSTS fehlt"]}
        worker_stoerung = {**betrieb, "exit": 2, "klasse": "STOERUNG", "gemessen": 0,
                           "fehlend": [], "stoerung": ["Öffentliche /healthz-Antwort"]}
        ok, grund = nachweis.live_pruefen(kopf_rot, worker_stoerung)
        self.assertFalse(ok)
        self.assertIn("header: BEFUND", grund)
        self.assertIn("worker: STOERUNG", grund)
        # Ein kaputtes Worker-JSON darf hinter einem roten Header-Befund nicht verschwinden.
        ok2, grund2 = nachweis.live_pruefen(kopf_rot, {})
        self.assertFalse(ok2)
        self.assertIn("Messklasse", grund2)

    def test_815_datenschutz_b7_blockiert_abschluss_trotz_technisch_gruener_header(self):
        kopf, betrieb = gute_messungen()
        kopf["abschluss_blocker"] = ["Datenschutz-Folge B7 offen: Vor-Proxy-Text"]
        nachweis.pruefe_messung(kopf, "header", "0")
        ok, grund = nachweis.live_pruefen(kopf, betrieb)
        self.assertFalse(ok)
        self.assertIn("Abschlussblocker", grund)
        self.assertIn("Datenschutz-Folge B7 offen", grund)

    def test_815_frisch_deployter_worker_im_zustand_wartet_erlaubt_live_nachweis(self):
        kopf, _ = gute_messungen()
        stand = {"ok": True, "kv": "ok", "turnstile": "wartet", "schluesselrollen": "getrennt",
                 "bau": worker.repo_stand()["build"],
                 "budget": {"anmeldung_heute": 1, "anmeldung_max": 100, "feedback_max": 200},
                 "exporte": []}
        _, bericht, betrieb = worker.netz_pruefen(
            "https://abos.franksfinanzcheck.de", "test-only",
            schreibschluessel="test-write-only", holen=lambda *_: stand, pausen=())
        betrieb["bericht"] = bericht
        ok, grund = nachweis.live_pruefen(kopf, betrieb)
        self.assertTrue(ok, grund)


class Auswertung(unittest.TestCase):
    def auswerten(self, daten, code="0", *, json_text=None, markdown=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if json_text is not None:
                (root / "messung.json").write_text(json_text)
            elif daten is not None:
                (root / "messung.json").write_text(json.dumps(daten))
            if markdown is not None:
                (root / "messung.md").write_text(markdown)
            elif daten is not None:
                (root / "messung.md").write_text(daten["bericht"])
            stdout = io.StringIO()
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(root / "summary"),
                                         # Ausdrückliche Ansage: Diese Tests prüfen
                                         # die Sendezeile, nicht die Teststille.
                                         "GITHUB_KOMMANDOS": "an"}), \
                    contextlib.redirect_stdout(stdout):
                ergebnis = nachweis.auswerten("worker", code, str(root / "messung.json"), str(root / "messung.md"))
            return ergebnis, stdout.getvalue(), (root / "summary").read_text()

    def test_gueltiger_bericht_geht_in_summary(self):
        _, daten = gute_messungen()
        code, stdout, summary = self.auswerten(daten)
        self.assertEqual(code, 0)
        self.assertIn("::notice::Worker grün", stdout)
        self.assertEqual(summary.strip(), daten["bericht"].strip())

    def test_keine_dateien_kaputtes_json_und_leerer_exit_sind_wache_fehler(self):
        _, daten = gute_messungen()
        for stand, code, roh in ((None, "0", None), (None, "0", "GIFT_ROHANTWORT"),
                                 (daten, "", None), (daten, "127", None)):
            with self.subTest(code=code, roh=roh):
                status, stdout, summary = self.auswerten(stand, code, json_text=roh)
                self.assertEqual(status, 1)
                self.assertIn("WACHE-FEHLER", stdout)
                self.assertIn("WACHE-FEHLER", summary)
                self.assertNotIn("GIFT_ROHANTWORT", stdout + summary)

    def test_json_und_markdown_muessen_dieselbe_messung_sein(self):
        _, daten = gute_messungen()
        status, stdout, _ = self.auswerten(daten, markdown="alter Bericht")
        self.assertEqual(status, 1)
        self.assertIn("WACHE-FEHLER", stdout)

    def test_einzelne_befunde_sind_als_annotationen_lesbar(self):
        _, daten = gute_messungen()
        daten.update(exit=1, klasse="BEFUND", fehlend=["Turnstile widersprüchlich", "Budget abweichend"])
        code, stdout, _ = self.auswerten(daten, "1")
        self.assertEqual(code, 1)
        self.assertIn("::error::Worker BEFUND: Turnstile widersprüchlich", stdout)
        self.assertIn("::error::Worker BEFUND: Budget abweichend", stdout)

    def test_annotationen_sind_gegen_neue_kommandos_geschuetzt(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_KOMMANDOS": "an"}), \
                contextlib.redirect_stdout(stdout):
            nachweis.annotation("error", "Messfehler 100%\r\n::notice::Falschgrün")
        self.assertEqual(stdout.getvalue().splitlines(), [
            "::error::Messfehler 100%25%0D%0A::notice::Falschgrün"])

    def test_summary_schreibfehler_werden_nicht_verschluckt(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                "GITHUB_STEP_SUMMARY": str(Path(tmp) / "fehlt" / "summary")}):
            with self.assertRaises(OSError):
                nachweis.zusammenfassung("Messbericht")


class Abschlussvertrag(unittest.TestCase):
    def test_schedule_und_manueller_live_lauf_duerfen_schliessen(self):
        for ereignis in ("schedule", "workflow_dispatch"):
            with self.subTest(ereignis=ereignis):
                self.assertTrue(nachweis.abschluss_pruefen(gute_jobs(), ereignis)[0])

    def test_exakte_798_regression_push_mit_uebersprungenem_live_job(self):
        jobs = [{"name": "Quellseite (offline, mit Selbsttests)", "conclusion": "success"},
                {"name": nachweis.LIVE_JOB, "conclusion": "skipped", "steps": []}]
        self.assertFalse(nachweis.abschluss_pruefen(jobs, "push")[0])
        self.assertFalse(nachweis.abschluss_pruefen(jobs, "schedule")[0])

    def test_andere_ereignisse_sind_keine_live_freigabe(self):
        for event in ("push", "pull_request", "workflow_run", "", "unbekannt"):
            with self.subTest(event=event):
                self.assertFalse(nachweis.abschluss_pruefen(gute_jobs(), event)[0])

    def test_jeder_mess_auswerte_und_nachweisschritt_muss_erfolgreich_sein(self):
        for name in nachweis.LIVE_SCHRITTE:
            for zustand in ("skipped", "failure", "cancelled", None):
                with self.subTest(name=name, zustand=zustand):
                    jobs = gute_jobs()
                    next(s for s in jobs[0]["steps"] if s["name"] == name)["conclusion"] = zustand
                    self.assertFalse(nachweis.abschluss_pruefen(jobs, "schedule")[0])

    def test_alte_gruene_laeufe_ohne_neuen_nachweis_schliessen_nicht(self):
        jobs = gute_jobs()
        jobs[0]["steps"] = [s for s in jobs[0]["steps"] if s["name"] != nachweis.LIVE_NACHWEIS]
        self.assertFalse(nachweis.abschluss_pruefen(jobs, "schedule")[0])

    def test_unbekannte_doppelte_und_fehlgeschlagene_jobs_schliessen_nicht(self):
        for jobs in (None, {}, [], [None], gute_jobs() * 2,
                     [{**gute_jobs()[0], "conclusion": "failure"}],
                     [{**gute_jobs()[0], "steps": None}]):
            with self.subTest(jobs=jobs):
                self.assertFalse(nachweis.abschluss_pruefen(jobs, "schedule")[0])

    def test_workflow_und_abschluss_benutzen_dieselben_schrittnamen(self):
        text = (ROOT / ".github/workflows/sicherheits-wache.yml").read_text()
        for name in nachweis.LIVE_SCHRITTE:
            self.assertIn("- name: " + name, text)
        self.assertIn("name: " + nachweis.LIVE_JOB, text)
        self.assertNotIn("continue-on-error:", text)
        for pfad in ("scripts/sicherheits_nachweis.py", "scripts/tests/test_sicherheits_nachweis.py",
                     "scripts/tests/test_worker_betrieb_wache.py", ".github/workflows/alert-on-failure.yml"):
            self.assertEqual(text.count('      - "' + pfad + '"'), 2, pfad)


@unittest.skipUnless(shutil.which("jq"), "jq fehlt; GitHub-Runner enthält jq")
class EchteResolveShell(unittest.TestCase):
    def run_resolve(self, jobs, event, *, api_fehler=False, kaputtes_json=False, wf_name="Sicherheits-Wache"):
        block = run_block(ROOT / ".github/workflows/alert-on-failure.yml",
                          "- name: Behobene Fehlermeldung schließen")
        ident = identitaet.identitaet(wf_name)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
            if kaputtes_json:
                job_text = "kein JSON"
            else:
                job_text = "\n".join(json.dumps(j) for j in jobs)
            (root / "jobs").write_text(job_text)
            (root / "issues").write_text(json.dumps([
                {"number": 809, "title": ident["titel"], "body": ident["marker"]}]))
            fake = '''gh() {
  printf '%s\\n' "$*" >> "$CALLS"
  if [ "$1" = "api" ]; then
    if [ "$API_FEHLER" = "1" ]; then return 1; fi
    cat jobs
  elif [ "$1" = "issue" ] && [ "$2" = "list" ]; then
    cat issues
  elif [ "$1" = "issue" ] && [ "$2" = "close" ]; then
    echo 'Test: Issue-Abschluss abgefangen'
  else
    echo 'Unerwarteter gh-Aufruf' >&2
    return 99
  fi
}
'''
            env = {**os.environ, "WF_NAME": wf_name, "RUN_EVENT": event, "RUN_ID": "39254264963",
                   "RUN_BRANCH": "main", "RUN_URL": "https://github.com/example/run/1",
                   "GITHUB_REPOSITORY": "test/repo", "API_FEHLER": "1" if api_fehler else "0",
                   "CALLS": str(root / "calls")}
            proc = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", fake + block],
                                  cwd=root, env=env, capture_output=True, text=True, timeout=15)
            calls = (root / "calls").read_text() if (root / "calls").exists() else ""
            return proc, calls

    def test_798_darf_nicht_wieder_durch_offline_gruen_geschlossen_werden(self):
        proc, calls = self.run_resolve([
            {"name": nachweis.LIVE_JOB, "conclusion": "skipped", "steps": []}], "push")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("issue close", calls)
        self.assertIn("bleibt offen", proc.stdout)

    def test_erst_der_vollstaendige_live_nachweis_darf_schliessen(self):
        proc, calls = self.run_resolve(gute_jobs(), "schedule")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("issue close 809", calls)

    def test_api_ausfall_kaputte_antwort_und_fehlender_nachweis_sind_fail_closed(self):
        alt = gute_jobs()
        alt[0]["steps"] = []
        for jobs, optionen in ((gute_jobs(), {"api_fehler": True}),
                              (gute_jobs(), {"kaputtes_json": True}), (alt, {})):
            with self.subTest(optionen=optionen):
                proc, calls = self.run_resolve(jobs, "workflow_dispatch", **optionen)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertNotIn("issue close", calls)

    def test_andere_workflows_behalten_ihren_abschlussweg(self):
        proc, calls = self.run_resolve([], "push", wf_name="Layout-AI")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("issue close 809", calls)
        self.assertNotIn("actions/runs", calls)


class AnnotationsVertrag972(unittest.TestCase):
    """Lauf 42044923993 (05.11.2026) als Regression, ohne Netz nachgebaut.

    Zehn fehlende Pflicht-Header auf zwei Zielen füllten das Fehler-Budget des
    Auswerte-Schritts genau aus. Die elfte Zeile mit der Proxy-Diagnose und
    dem nächsten Schritt war im Check-Run nicht mehr da – obwohl die Meldung
    #972 ausdrücklich auf „die Header-Annotation“ verwies. Geprüft wird hier
    die gesendete Fassade, nicht nur der Bericht im Artefakt.
    """

    def _f01_befund_mit_zehn_fehlern(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            datenschutz = wurzel / "content" / "datenschutz" / "index.md"
            datenschutz.parent.mkdir(parents=True)
            datenschutz.write_text("Cloudflare-Proxy und Zugriffsdaten sind beschrieben.",
                                   encoding="utf-8")
            with patch.object(header, "WURZEL", wurzel):
                code, bericht, daten = header.netz_pruefen(
                    holen=lambda *_: (200, {"cf-ray": "9a1b2c3d4e5f6a7b-FRA"}),
                    pausen=(), schlaf=lambda _: None)
        self.assertEqual(code, 1)
        self.assertEqual(len(daten["fehlend"]), 10)
        daten["bericht"] = bericht
        return daten

    def _auswerten(self, quelle, daten):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "messung.json").write_text(json.dumps(daten), encoding="utf-8")
            (root / "messung.md").write_text(daten["bericht"], encoding="utf-8")
            puffer = io.StringIO()
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(root / "summary"),
                                         "GITHUB_KOMMANDOS": "an"}), \
                    contextlib.redirect_stdout(puffer):
                code = nachweis.auswerten(quelle, str(daten["exit"]),
                                          str(root / "messung.json"),
                                          str(root / "messung.md"))
            zeilen = [z for z in puffer.getvalue().splitlines() if z.startswith("::error::")]
            return code, zeilen, (root / "summary").read_text(encoding="utf-8")

    def test_zehn_f01_befunde_verdraengen_diagnose_und_schritt_nicht(self):
        daten = self._f01_befund_mit_zehn_fehlern()
        code, zeilen, summary = self._auswerten("header", daten)
        self.assertEqual(code, 1)
        self.assertLessEqual(len(zeilen), nachweis.MELDE_BUDGET_ROT,
                             "Neun eigene Fehlerzeilen, die zehnte gehört dem Runner")
        self.assertEqual(len(zeilen) + 1, 10)
        self.assertIn(daten["diagnose"], zeilen[0], "Die Diagnose muss die erste Zeile sein")
        self.assertIn("Diagnose:", zeilen[0])
        self.assertIn("FF Sicherheits-Header", zeilen[1], "Der nächste Schritt muss überleben")
        self.assertTrue(any("weitere" in z for z in zeilen), "Der Verlust muss benannt sein")
        # Gekappt wird nur die Fassade: alle zehn Funde bleiben im Nachweis.
        for befund in daten["fehlend"]:
            self.assertIn(befund, summary)
        self.assertIn("**Diagnose:**", summary)

    def test_die_aussage_der_meldung_972_ist_jetzt_durch_die_annotation_gedeckt(self):
        meldung = (ROOT / ".github" / "workflows" / "alert-on-failure.yml").read_text(
            encoding="utf-8")
        self.assertIn("Die Header-Annotation nennt die Diagnose", meldung)
        daten = self._f01_befund_mit_zehn_fehlern()
        _, zeilen, _ = self._auswerten("header", daten)
        self.assertTrue(any("Proxy ist" in z for z in zeilen),
                        "Der Rat in #972 zeigt auf eine Zeile, die es geben muss")
        self.assertTrue(any("FF Sicherheits-Header" in z for z in zeilen))

    def test_worker_stoerung_behaelt_alle_zeilen_und_braucht_keine_sammelzeile(self):
        daten = {"exit": 2, "klasse": "STOERUNG", "gemessen": 0, "fehlend": [],
                 "warnungen": [], "stoerung": ["Schema unvollständig", "Deploy veraltet",
                                               "Leseschlüssel prüfen"],
                 "bericht": "Messbericht", "naechster_schritt": "Runbook D2 lesen"}
        code, zeilen, _ = self._auswerten("worker", daten)
        self.assertEqual(code, 1)
        self.assertEqual(len(zeilen), 4)
        self.assertIn("Runbook D2 lesen", zeilen[0])
        self.assertFalse(any("weitere" in z for z in zeilen))

    def test_ungueltige_diagnose_ist_wache_fehler_kein_freibrief(self):
        kopf, _ = gute_messungen()
        for diagnose in ({"proxy": "aktiv"}, "   ", 7, ["aktiv"]):
            with self.subTest(diagnose=diagnose):
                with self.assertRaises(nachweis.NachweisFehler):
                    nachweis.pruefe_messung({**kopf, "diagnose": diagnose}, "header", "0")

    def test_gruene_messung_erfindet_keine_diagnose(self):
        kopf, _ = gute_messungen()
        self.assertNotIn("diagnose", kopf, "Nur ein belegter BEFUND trägt eine Diagnose")
        _, zeilen, _ = self._auswerten("header", kopf)
        self.assertFalse(any(z.startswith("::error::") for z in zeilen))


if __name__ == "__main__":
    unittest.main()
