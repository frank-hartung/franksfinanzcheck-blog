#!/usr/bin/env python3
"""Strukturvertrag der beiden Wartungsläufe aus #1026 und #1024 (04.11.2026).

WARUM ES DIESE DATEI GIBT
-------------------------
Beide Vorfälle waren keine Sachfehler, sondern ORDNUNGSFEHLER: Die richtige
Logik stand im Code, wurde aber zum falschen Zeitpunkt oder mit der falschen
Fehlerklasse ausgeführt.

* `web-vitals-woche.yml` lud `scripts/lighthouse_live.mjs` VOR `npm ci`.
  Der statische Import von `lighthouse`/`playwright-core` warf
  `ERR_MODULE_NOT_FOUND`, und eine unverbindliche Labordiagnose nahm die
  verbindliche Feldmessung mit ins Rot (Lauf 41456548199).
* `redaktionelle-ymyl-pruefung.yml` verschluckte den Exit-Code der
  Belegketten-Wache über `continue-on-error`, und die Wache selbst tarnte
  einen `ValueError` (3-Tupel als 2-Tupel entpackt) als „Quelle unklar“.
  Vier gültige Gesetzeszitate standen dauerhaft in der Queue (#1024).

Ein Unit-Test gegen die Python-Funktion hätte in beiden Fällen nichts
gesehen: Die Funktionen waren richtig, die Umgebung war falsch. Diese Datei
prüft deshalb die STRUKTUR der YAML-Dateien – Reihenfolge, Fehlerbehandlung,
Kontingent und Sichtbarkeit – und hält die Regression dort fest, wo sie
entsteht.

Die Tests laufen offline und brauchen nur PyYAML.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
sys.path.insert(0, str(ROOT / "scripts"))


def lade(name: str) -> dict:
    """Lädt einen Workflow als dict. `on:` löst PyYAML zu `True` auf – egal,
    weil diese Datei nur `jobs` liest."""
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def schritte(job: dict) -> list[dict]:
    return list(job.get("steps") or [])


def namen(job: dict) -> list[str]:
    return [str(s.get("name") or s.get("uses") or "") for s in schritte(job)]


def index(job: dict, name: str) -> int:
    return namen(job).index(name)


def run_text(step: dict) -> str:
    return str(step.get("run") or "")


class WebVitalsWorkflowTests(unittest.TestCase):
    """#1026: Der Selbsttest darf nicht wieder an fehlenden Paketen sterben."""

    def setUp(self):
        self.job = lade("web-vitals-woche.yml")["jobs"]["feld"]
        self.namen = namen(self.job)

    def test_setup_node_steht_vor_jedem_node_aufruf(self):
        node_steps = [i for i, s in enumerate(schritte(self.job))
                      if "node " in run_text(s) or "node --test" in run_text(s)]
        setup = [i for i, s in enumerate(schritte(self.job))
                 if str(s.get("uses", "")).startswith("actions/setup-node")]
        self.assertTrue(setup, "kein actions/setup-node im Job")
        for i in node_steps:
            with self.subTest(step=self.namen[i]):
                self.assertLess(setup[0], i, "Node-Aufruf vor actions/setup-node")

    def test_selbsttest_laeuft_vor_npm_ci(self):
        selbst = index(self.job, "Selbsttests der Messungen (ohne Netz, ohne node_modules)")
        install = index(self.job, "Abhängigkeiten installieren")
        self.assertLess(selbst, install,
                        "Der Selbsttest muss VOR npm ci laufen – das ist die Lehre aus #1026")

    def test_selbsttest_ruft_beide_werkzeuge_auf(self):
        text = run_text(self.job["steps"][index(
            self.job, "Selbsttests der Messungen (ohne Netz, ohne node_modules)")])
        self.assertIn("scripts/cwv_feld_wache.py --selftest", text)
        self.assertIn("scripts/lighthouse_live.mjs --selftest", text)
        self.assertIn("scripts/tests/lighthouse_live.test.mjs", text)
        self.assertIn("scripts.tests.test_cwv_feld_wache", text)

    def test_paketfreiheit_wird_behauptet_und_belegt(self):
        """Der Selbsttest behauptet Offline-Fähigkeit nicht – er prüft sie."""
        text = run_text(self.job["steps"][index(
            self.job, "Selbsttests der Messungen (ohne Netz, ohne node_modules)")])
        self.assertIn("[ -d node_modules ]", text,
                      "Der Schritt muss prüfen, ob node_modules liegt – und es sagen")
        self.assertIn("warning::", text,
                      "Ein vorhandenes node_modules schwächt den Beweis: das gehört sichtbar")

    def test_kein_continue_on_error_ueber_exitcodes(self):
        for schritt_dict in schritte(self.job):
            if "continue-on-error" not in schritt_dict:
                continue
            with self.subTest(step=namen(self.job)[schritte(self.job).index(schritt_dict)]):
                self.assertTrue(str(schritt_dict["continue-on-error"]).startswith("${{"),
                                "continue-on-error über einem Gate-Schritt")

    def test_feld_und_labor_erfassen_ihren_exitcode_deterministisch(self):
        for name, id_ in (("Felddaten messen (CrUX über PageSpeed Insights)", "feld"),
                          ("Laborwerte messen (Lighthouse, Schwellen aus dem Regelwerk)", "labor")):
            with self.subTest(step=name):
                schritt = self.job["steps"][index(self.job, name)]
                self.assertEqual(id_, schritt.get("id"))
                text = run_text(schritt)
                self.assertIn("rc=0", text, "Exit-Code wird nicht vorbelegt")
                self.assertIn("|| rc=$?", text, "Exit-Code wird nicht erfasst")
                self.assertIn('echo "exit=${rc}" >> "$GITHUB_OUTPUT"', text,
                              "Exit-Code landet nicht in den Schritten-Ausgaben")
                self.assertIn("exit 0", text,
                              "Der Schritt selbst muss grün bleiben (Diagnose, kein Blocker)")

    def test_urteil_schliesst_bei_jedem_unklaren_exit_fail_closed(self):
        text = run_text(self.job["steps"][index(
            self.job, "Urteil (Felddaten entscheiden, Labor warnt)")])
        self.assertIn('case "$FELD" in', text)
        for zweig in ("0)", "1)", "2)", "*)"):
            self.assertIn(zweig, text, f"Fall {zweig} fehlt im Urteil")
        # Der leere Fall (kein Urteil) ist ausdrücklich fail-closed:
        # `*)` sammelt alles, was weder 0, 1 noch 2 ist – auch den leeren Wert.
        zweig = text.split("*)", 1)[1] if "*)" in text else ""
        self.assertTrue(zweig, "kein Default-Zweig (*)) im Urteil")
        self.assertIn("exit 1", zweig.split(";;", 1)[0],
                      "Der Default-Zweig muss abbrechen (fail-closed)")

    def test_berichte_landen_im_artefakt_und_in_der_zusammenfassung(self):
        self.assertTrue(any("$GITHUB_STEP_SUMMARY" in run_text(s) for s in schritte(self.job)))
        artefakt = [s for s in schritte(self.job)
                    if str(s.get("uses", "")).startswith("actions/upload-artifact")]
        self.assertTrue(artefakt, "kein Artefakt-Schritt")
        pfad = str(artefakt[0]["with"]["path"])
        for datei in ("feld-bericht.md", "feld-fehler.txt", "labor-bericht.md", "labor-fehler.txt"):
            self.assertIn(datei, pfad, f"{datei} fehlt im Artefakt")

    def test_der_jobname_bleibt_stabil(self):
        """`alert_resolve_gate.py` schließt Meldungen nur, wenn der GENANNTE
        Job im auflösenden Lauf grün ist. Ein umbenannter Job wäre ein
        Dauer-Alarm."""
        self.assertEqual("Felddaten (CrUX) + Labor (Lighthouse)",
                         self.job.get("name"))


class YmylWorkflowTests(unittest.TestCase):
    """#1024: Quellenbefund und Werkzeugfehler dürfen nie mehr dasselbe sein."""

    def setUp(self):
        self.workflow = lade("redaktionelle-ymyl-pruefung.yml")
        self.job = self.workflow["jobs"]["belegketten"]
        self.namen = namen(self.job)

    def test_selbsttest_steht_vor_der_messung(self):
        selbst = index(self.job, "Selbsttest der Belegketten-Wache (offline)")
        messung = index(self.job, "Belegketten der Hochrisiko-Artikel prüfen")
        self.assertLess(selbst, messung)
        text = run_text(self.job["steps"][selbst])
        self.assertIn("scripts/belegketten_wache.py --selftest", text)
        self.assertIn("scripts.tests.test_belegketten_wache", text)

    def test_messung_erfasst_rc_statt_continue_on_error(self):
        schritt = self.job["steps"][index(
            self.job, "Belegketten der Hochrisiko-Artikel prüfen")]
        self.assertNotIn("continue-on-error", schritt,
                         "continue-on-error verschluckt den Exit-Code vor $GITHUB_OUTPUT")
        text = run_text(schritt)
        self.assertIn("rc=0", text)
        self.assertIn("|| rc=$?", text)
        self.assertIn('echo "exit=${rc}" >> "$GITHUB_OUTPUT"', text)
        self.assertIn("--strict --require-complete", text)

    def test_werkzeugfehler_hat_ein_eigenes_hartes_gate(self):
        name = "Werkzeug-Integrität der Belegketten-Wache"
        self.assertIn(name, self.namen, "eigenes Gate für Exit 2 fehlt")
        text = run_text(self.job["steps"][index(self.job, name)])
        self.assertIn("0|1)", text, "0 und 1 müssen als Urteil gelten")
        self.assertIn("exit 1", text, "Werkzeugfehler muss hart abbrechen")
        # Ein Urteil (0/1) darf das Gate NICHT rot machen.
        self.assertRegex(text, r"0\|1\)[^\n]*\n(?:.*\n)*?\s+;;",
                         )

    def test_messweg_wird_live_bewiesen_und_bleibt_unverbindlich(self):
        name = "Bundesrechts-Spiegel live prüfen (Messweg-Nachweis)"
        self.assertIn(name, self.namen)
        schritt = self.job["steps"][index(self.job, name)]
        self.assertIn("--probe-bundesrecht", run_text(schritt))
        self.assertEqual("always()", schritt.get("if"))
        self.assertIs(True, schritt.get("continue-on-error"),
                      "Die Live-Probe braucht Netz und darf das Gate nicht rot machen")
        self.assertIn("GITHUB_STEP_SUMMARY", run_text(schritt))

    def test_spiegel_kontingent_bekommt_einen_token(self):
        schritt = self.job["steps"][index(
            self.job, "Belegketten der Hochrisiko-Artikel prüfen")]
        env = schritt.get("env") or {}
        self.assertIn("GH_TOKEN", env,
                      "Ohne Token antwortet api.github.com unauthentifiziert bei 60 Abrufen/h")
        self.assertIn("secrets.GITHUB_TOKEN", str(env["GH_TOKEN"]))

    def test_auschecken_laesst_keine_aneignung_zurueck(self):
        for job_name, job in self.workflow["jobs"].items():
            for schritt in schritte(job):
                if str(schritt.get("uses", "")).startswith("actions/checkout"):
                    with self.subTest(job=job_name):
                        self.assertIs(False, (schritt.get("with") or {}).get(
                            "persist-credentials", False) is not False)

    def test_ticket_regel_kennt_drei_zustaende(self):
        name = "Arbeits-Ticket pflegen"
        text = run_text(self.job["steps"][index(self.job, name)])
        self.assertIn("WACHE_EXIT", text)
        self.assertIn("WACHE_GRUEN", text)
        self.assertIn("0) ;;", text.replace("0) ;;", "0) ;;"))
        # Ohne Exit-Code (Job davor abgebrochen) darf nichts als grün gelten.
        self.assertIn("fail-closed", text)
        # Der alte, falsche Vergleich auf die Schritt-Lage ist verschwunden.
        self.assertNotIn('[ "${WACHE}" != "success" ]', text)


class ZusammenspielTests(unittest.TestCase):
    """Was nur im Zusammenspiel schiefgehen kann."""

    def test_werkzeuge_tragen_ihren_selbsttest_im_namen(self):
        """Repo-Regel D6: Ein `--selftest` prüft das Modul, dessen Namen er
        trägt – er reicht die Flagge nie bloß weiter."""
        import subprocess

        for werkzeug, datei in (("lighthouse_live.mjs", "lighthouse_live.mjs"),
                                ("belegketten_wache.py", "belegketten_wache.py"),
                                ("cwv_feld_wache.py", "cwv_feld_wache.py")):
            with self.subTest(werkzeug=werkzeug):
                quelle = (ROOT / "scripts" / datei).read_text(encoding="utf-8")
                self.assertIn("--selftest", quelle, f"{werkzeug} kennt kein --selftest")
                self.assertIn("selftest", quelle)

    def test_lighthouse_live_hat_keinen_fremdimport_am_modulkopf(self):
        quelle = (ROOT / "scripts" / "lighthouse_live.mjs").read_text(encoding="utf-8")
        statisch = [z.strip() for z in quelle.splitlines()
                    if z.lstrip().startswith("import ")]
        self.assertTrue(statisch)
        for zeile in statisch:
            self.assertRegex(zeile, r"from '(node:|\.)",
                             f"Fremdpaket am Modulkopf: {zeile}")
        self.assertNotIn("from 'lighthouse'", quelle)
        self.assertNotIn("from 'playwright-core'", quelle)

    def test_belegketten_wache_faengt_nur_netzfehler(self):
        """`except Exception` und `except:` waren die Tarngrube für #1024.

        Geprüft wird der SYNTAXBAUM, nicht der Text: Der Vorfall selbst steht
        im Modul-Docstring (er soll ja dokumentiert sein), und ein Textvergleich
        würde die Erklärung mit der Ursache verwechseln. Der AST sieht nur
        echte Handler – und ist damit die härtere Prüfung.
        """
        import ast

        quelle = (ROOT / "scripts" / "belegketten_wache.py").read_text(encoding="utf-8")
        baum = ast.parse(quelle)

        def funktion_von(zeile: int) -> str:
            for knoten in ast.walk(baum):
                if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if knoten.lineno <= zeile <= max(
                            [n.lineno for n in ast.walk(knoten) if hasattr(n, "lineno")]):
                        return knoten.name
            return "<modul>"

        handler = [knoten for knoten in ast.walk(baum) if isinstance(knoten, ast.ExceptHandler)]
        self.assertTrue(handler, "keine Fehlerbehandlung gefunden – das wäre auch falsch")
        for knoten in handler:
            with self.subTest(zeile=knoten.lineno, funktion=funktion_von(knoten.lineno)):
                self.assertIsNotNone(knoten.type, f"blankes `except:` in Zeile {knoten.lineno}")
                typen = (knoten.type.elts if isinstance(knoten.type, ast.Tuple)
                         else [knoten.type])
                namen = {getattr(t, "id", getattr(t, "attr", "")) for t in typen}
                # Erlaubt ist nur eine benannte, enge Klasse. `Exception`,
                # `BaseException` und `ValueError` sind genau die Breite,
                # die #1024 zugedeckt hat.
                self.assertTrue(
                    namen <= {"NETZ_AUSNAHMEN", "HTTPError", "ValueError",
                              "AttributeError", "OSError", "KeyError", "TypeError",
                              "YAMLError"},
                    f"zu breite Fehlerklasse in Zeile {knoten.lineno}: {sorted(namen)}")
                wer = funktion_von(knoten.lineno)
                # DIE REGEL, an der #1024 zerbrach: Es gibt zwei Arten von
                # Fehlerbehandlung, und nur eine davon darf breit sein.
                #
                #   (a) AUSWERTUNG – entscheidet, WAS abgerufen/geparst wird
                #       (kaputter URL-String, unlesbare Datei). Ein
                #       ValueError ist hier der NORMALE Fall.
                #   (b) ERGEBNIS – entscheidet, WAS DAS ERGEBNIS BEDEUTET
                #       (abruf_http, pruefe_quelle, _pruefe_gii_spiegel).
                #       Hier darf AUSSCHLIESSLICH eine Netzklasse stehen:
                #       Nur der Messweg darf „unklar“ erzeugen.
                #
                # Der Defekt war ein ValueError aus dem Tupel-Entpacken im
                # ERGEBNISPFAD – getarnt als Netzbefund. Deshalb ist (b) die
                # harte Grenze, und (a) bleibt bewusst erlaubt.
                if wer in {"abruf_http", "pruefe_quelle", "_pruefe_gii_spiegel",
                           "abruf_gii_spiegel", "abruf_gii_spiegel_http",
                           "_spiegel_abruf", "probe_bundesrecht"}:
                    self.assertTrue(
                        namen <= {"NETZ_AUSNAHMEN", "HTTPError"},
                        f"Ergebnispfad {wer} faengt {sorted(namen)} – "
                        "nur der Messweg darf 'unklar' erzeugen (#1024)")
                if wer == "belegketten":
                    self.assertTrue(namen <= {"OSError", "ValueError", "YAMLError",
                                              "KeyError", "TypeError"},
                                    f"belegketten faengt zu breit: {sorted(namen)}")

        # Die breite Klasse ist im GESAMTEN Modul verbannt.
        for knoten in handler:
            namen = set()
            if knoten.type is not None:
                typen = (knoten.type.elts if isinstance(knoten.type, ast.Tuple)
                         else [knoten.type])
                namen = {getattr(t, "id", getattr(t, "attr", "")) for t in typen}
            with self.subTest(zeile=knoten.lineno):
                self.assertNotIn("Exception", namen, f"`except Exception` in Zeile {knoten.lineno}")

    def test_belegketten_selbsttest_laeuft_ohne_netz(self):
        import subprocess

        ergebnis = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "belegketten_wache.py"), "--selftest"],
            capture_output=True, text=True, timeout=180, cwd=ROOT)
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)


if __name__ == "__main__":
    unittest.main()
