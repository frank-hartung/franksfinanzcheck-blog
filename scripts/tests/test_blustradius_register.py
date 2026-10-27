#!/usr/bin/env python3
"""Vertragstests für den Blustradius des deploy-Jobs (#740, C38).

GEPRÜFTER VERTRAG
-----------------
Am 14.10.2026 starb der `deploy`-Job zehnmal in Folge an der
„Quote-Nachfüllung" – einem Schritt, der niemals etwas über Inhalte
entscheidet. Die Live-Site fror ein, obwohl kein Artikel beanstandet war.

Die Heilung aus #676 (C34) hatte genau EINEN Schritt gelehrt, zwischen
Inhalt und Werkzeug zu unterscheiden. Dieser Test hält die Lehre für den
GANZEN Job fest:

  · jeder Schritt ist mit seiner Klasse deklariert (Register),
  · wer blockieren darf, ist eine Entscheidung auf Papier – keine Folge
    davon, wer zufällig ein `|| true` vergessen hat,
  · die Werkzeug-Schritte des Deploys fahren ihre Shell-Blöcke
    nachweislich so, wie der Vertrag es verlangt: Inhalt stoppt (Exit 1),
    Werkzeug meldet und liefert weiter (Exit 0).

Der dritte Punkt ist der wichtige: Er führt die ECHTEN `run`-Blöcke aus
deploy.yml gegen Attrappen aus. Eine Textprüfung („steht `case` drin?")
hätte den Ausfall nicht verhindert – der Block muss sich beweisen.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import blustradius_register as br  # noqa: E402

DEPLOY_YML = ROOT / ".github" / "workflows" / "deploy.yml"
ISOLATION = "Auslieferungs-Isolation (blockierte Kandidaten → hold, Quote → Min)"
KOSTENSPERRE = "Kostensperre belegen (vor jeder Geldflaeche)"
SAMMLER = "Werkzeugbefunde einsammeln (Material für das Siegel)"


def _steps() -> dict:
    workflow, _text = br.lade_workflow()
    return {br.schrittname(s): s
            for s in br.schritte_des_jobs(workflow, "deploy")}


class RegisterIstVollstaendig(unittest.TestCase):
    """Das Register beschreibt den Job, den es behauptet zu beschreiben."""

    def test_pruefung_ohne_befund(self):
        befunde = br.pruefe()
        self.assertEqual(befunde, [],
                         "Blustradius-Vertrag verletzt:\n  - "
                         + "\n  - ".join(befunde))

    def test_jeder_schritt_hat_eine_klasse(self):
        register = br.lade_register()
        for eintrag in register["schritte"]:
            self.assertIn(eintrag.get("klasse"), br.KLASSEN,
                          f"{eintrag.get('name')}: Klasse fehlt/unbekannt")
            self.assertTrue(str(eintrag.get("grund") or "").strip(),
                            f"{eintrag.get('name')}: Begründung fehlt – eine "
                            f"Klasse ohne Grund ist eine Behauptung")

    def test_mess_schritte_duerfen_nicht_blockieren(self):
        """Die Kernaussage des Vertrags, als Liste geprüft."""
        register = br.lade_register()
        for eintrag in register["schritte"]:
            if eintrag.get("klasse") != "werkzeug":
                continue
            info = br.klassifiziere(eintrag["name"], register)
            self.assertFalse(info["darf_blockieren"],
                             f"{eintrag['name']} ist als Werkzeug deklariert, "
                             f"dürfte aber blockieren")

    def test_urteil_nennt_den_weg(self):
        register = br.lade_register()
        werkzeug = next(e["name"] for e in register["schritte"]
                        if e.get("klasse") == "werkzeug")
        satz = br.urteil(werkzeug, register)
        self.assertIn("werkzeugbefund.py", satz)
        self.assertNotIn("?", satz,
                         "Das Urteil im Ticket stellt keine Frage (WF-A535)")

    def test_unbekannter_schritt_ist_kein_stilles_ok(self):
        info = br.klassifiziere("Schritt, den es nicht gibt")
        self.assertFalse(info["bekannt"])
        self.assertEqual(info["klasse"], "unbekannt")
        self.assertIn("Register", br.urteil("Schritt, den es nicht gibt"))


class SchrittbloeckeBeweisenSich(unittest.TestCase):
    """Die echten `run`-Blöcke aus deploy.yml gegen Attrappen fahren."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which("bash"):  # pragma: no cover - CI hat bash
            raise unittest.SkipTest("bash fehlt")
        cls.steps = _steps()

    def _fahre(self, schrittname: str, stubs: dict, env_extra=None):
        """Führt den Shell-Block wie GitHub aus (`bash -e`) und berichtet."""
        step = self.steps.get(schrittname)
        self.assertIsNotNone(step, f"Schritt „{schrittname}\" fehlt in deploy.yml")
        with tempfile.TemporaryDirectory() as tmp:
            arbeit = Path(tmp)
            (arbeit / "scripts").mkdir()
            # Der Schritt benutzt den gemeinsamen Kommando-Melder (WF-E813/#815,
            # 27.10.2026). Die Bühne muss deshalb dieselben Dateien tragen wie
            # das Repository – sonst prüft der Test einen Aufbau, den es nicht gibt.
            for datei in ("werkzeugbefund.py", "github_kommando.py"):
                shutil.copy(SCRIPTS / datei, arbeit / "scripts" / datei)
            for name, (selftest_code, code) in stubs.items():
                (arbeit / "scripts" / name).write_text(
                    "#!/usr/bin/env python3\nimport sys\n"
                    "if '--selftest' in sys.argv:\n"
                    f"    raise SystemExit({selftest_code})\n"
                    f"raise SystemExit({code})\n", encoding="utf-8")
            ausgabe = arbeit / "github_output.txt"
            ausgabe.touch()
            zusammenfassung = arbeit / "summary.md"
            zusammenfassung.touch()
            runner = arbeit / "runner_temp"
            runner.mkdir()
            # WICHTIG: `GITHUB_KOMMANDOS=aus` – diese Bühne SIMULIERT einen
            # Lauf, sie ist keiner. Ohne die Ansage würde der Melder in CI
            # `::`-Zeilen ausgeben, und diese Unit-Tests würden den Lauf, in
            # dem sie laufen, mit fremden Annotationen einfärben (Befund der
            # Stufe 4, WF-E813/#815). Geprüft wird der Befund, nicht die Farbe.
            env = dict(os.environ, GITHUB_OUTPUT=str(ausgabe),
                       GITHUB_STEP_SUMMARY=str(zusammenfassung),
                       RUNNER_TEMP=str(runner), GITHUB_SHA="0" * 40,
                       GITHUB_KOMMANDOS="aus")
            env.update(env_extra or {})
            skript = arbeit / "step.sh"
            skript.write_text(step["run"], encoding="utf-8")
            lauf = subprocess.run(["bash", "-e", str(skript)], cwd=arbeit,
                                  env=env, capture_output=True, text=True,
                                  timeout=120)
            ablage = runner / "werkzeugbefunde.txt"
            return {
                "exit": lauf.returncode,
                "stdout": lauf.stdout,
                "outputs": dict(
                    z.split("=", 1) for z in
                    ausgabe.read_text(encoding="utf-8").strip().splitlines()
                    if "=" in z),
                "befunde": (ablage.read_text(encoding="utf-8")
                            if ablage.exists() else ""),
            }

    # --- Isolation ---------------------------------------------------------
    def test_isolation_werkzeugfehler_liefert_weiter(self):
        """Exit 2 = Werkzeug: Das war #740 in Reinform."""
        r = self._fahre(ISOLATION, {"release_isolation.py": (0, 2)})
        self.assertEqual(r["exit"], 0,
                         "Ein Werkzeugfehler der Isolation blockiert wieder "
                         "die Auslieferung")
        self.assertIn("auslieferungs-isolation", r["befunde"])
        self.assertIn("Werkzeugfehler", r["befunde"])

    def test_isolation_inhaltsbefund_stoppt_hart(self):
        """Exit 1 = Inhalt: Ungeprüftes geht NICHT live (C2/C33)."""
        r = self._fahre(ISOLATION, {"release_isolation.py": (0, 1)})
        self.assertEqual(r["exit"], 1,
                         "Ein Inhaltsbefund stoppt die Auslieferung nicht "
                         "mehr – Scheingrün ginge live")
        self.assertEqual(r["befunde"], "",
                         "Ein Inhaltsbefund ist kein Werkzeugbefund")

    def test_isolation_roter_selbsttest_meldet_und_liefert(self):
        r = self._fahre(ISOLATION, {"release_isolation.py": (1, 0)})
        self.assertEqual(r["exit"], 0)
        self.assertIn("Selbsttest", r["befunde"])

    def test_isolation_gruen_meldet_nichts(self):
        r = self._fahre(ISOLATION, {"release_isolation.py": (0, 0)})
        self.assertEqual(r["exit"], 0)
        self.assertEqual(r["befunde"], "",
                         "Ein grüner Lauf darf keinen Befund erfinden")

    # --- Kostensperre ------------------------------------------------------
    def test_kostensperre_sperrt_geld_nicht_auslieferung(self):
        """Fail-closed fürs Geld, fail-open für die Auslieferung."""
        r = self._fahre(KOSTENSPERRE, {"kostensperre.py": (0, 1)})
        self.assertEqual(r["exit"], 0,
                         "Die Kostensperre blockiert wieder die Auslieferung")
        self.assertEqual(r["outputs"].get("gesperrt"), "true",
                         "Ohne `gesperrt=true` liefe die Geldfläche weiter – "
                         "das wäre die gefährliche Richtung")
        self.assertIn("kostensperre", r["befunde"])

    def test_kostensperre_gruen_gibt_geld_frei(self):
        r = self._fahre(KOSTENSPERRE, {"kostensperre.py": (0, 0)})
        self.assertEqual(r["exit"], 0)
        self.assertEqual(r["outputs"].get("gesperrt"), "false")
        self.assertEqual(r["befunde"], "")

    def test_bezahlte_vertonung_haengt_an_der_sperre(self):
        """Der Output muss auch verdrahtet sein, nicht nur existieren."""
        text = DEPLOY_YML.read_text(encoding="utf-8")
        self.assertIn("steps.kostensperre.outputs.gesperrt != 'true'", text,
                      "Die kostenpflichtige Vertonung prüft die Sperre nicht "
                      "– fail-closed fürs Geld wäre aufgehoben")

    # --- Sammler + Siegel --------------------------------------------------
    def test_sammler_faltet_altkanaele_ein(self):
        r = self._fahre(SAMMLER, {}, env_extra={
            "SCORECARD_WERKZEUGFEHLER": "true", "SCORECARD_EXIT": "2",
            "REFILL_WERKZEUGFEHLER": "true"})
        self.assertEqual(r["exit"], 0, "Der Sammler darf nie rot enden")
        self.assertEqual(r["outputs"].get("werkzeugbefunde_anzahl"), "2",
                         f"Altkanäle nicht eingefaltet: {r['outputs']}")
        self.assertIn("release-scorecard", r["outputs"]["werkzeugbefunde"])
        self.assertIn("quote_refill", r["outputs"]["werkzeugbefunde"])

    def test_sammler_ohne_befunde_bleibt_leer(self):
        r = self._fahre(SAMMLER, {})
        self.assertEqual(r["exit"], 0)
        self.assertEqual(r["outputs"].get("werkzeugbefunde_anzahl"), "0")

    def test_sammler_steht_vor_der_auslieferung(self):
        """Gesammelt wird vor dem Upload – gemeldet erst danach (C34)."""
        text = DEPLOY_YML.read_text(encoding="utf-8")
        self.assertLess(
            text.index("id: werkzeugbefunde"),
            text.index("- name: Artefakt für offizielles Pages-Deployment"),
                        "Der Sammler läuft nach dem Artefakt-Upload – dann "
                        "fehlt dem Siegel sein Material")
        siegel = text[text.index("  release-seal:"):]
        self.assertIn("WERKZEUGBEFUNDE", siegel,
                      "`release-seal` liest die Werkzeugbefunde nicht")
        self.assertIn("werkzeugbefunde_anzahl", text)


class WachenSelbsttest(unittest.TestCase):
    def test_selftest_gruen(self):
        lauf = subprocess.run(
            [sys.executable, str(SCRIPTS / "blustradius_register.py"),
             "--selftest"], capture_output=True, text=True, timeout=300)
        self.assertEqual(lauf.returncode, 0,
                         f"Selbsttest rot:\n{lauf.stdout}\n{lauf.stderr}")

    def test_check_gruen(self):
        lauf = subprocess.run(
            [sys.executable, str(SCRIPTS / "blustradius_register.py"),
             "--check"], capture_output=True, text=True, timeout=300)
        self.assertEqual(lauf.returncode, 0,
                         f"--check rot:\n{lauf.stdout}\n{lauf.stderr}")


class WatchdogUrteiltStattZuFragen(unittest.TestCase):
    """Der Befund im Ticket nennt die Klasse und den nächsten Schritt."""

    def test_blockade_klasse_nutzt_das_register(self):
        import bot_watchdog as bw
        klasse, satz = bw.blockade_klasse(
            "Quote-Nachfüllung nach Gate-Verlust (Re-Queue + Reserve → Min)")
        self.assertEqual(klasse, "werkzeug",
                         "Der Schritt aus #740 wird nicht als Werkzeug erkannt")
        self.assertIn("werkzeugbefund.py", satz)

    def test_blockade_klasse_faellt_nie_um(self):
        import bot_watchdog as bw
        for name in ("", None, "Unbekannter Schritt"):
            klasse, satz = bw.blockade_klasse(name)
            self.assertIsInstance(klasse, str)
            self.assertIsInstance(satz, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
