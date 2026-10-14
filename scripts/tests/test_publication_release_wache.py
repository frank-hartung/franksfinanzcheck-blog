"""Regressions-Tests: Endabnahme-Wache (WF-A535 #529).

02.10.2026: Die Content-Engine-Läufe 19:15 und 21:26 (Vorgang WF-A535 #529)
scheiterten an „Do not report a quota deficit as success“ – nicht an einem
Tagesdefizit, sondern am ERSTEN Hugo-Build der Endabnahme: Ein Markdown-Link
im rechner-Shortcode-Parameter (typ="[notgroschen](../../posts/…)", Commit
c181d75) tötete den Build blog-weit. publication_release endete in einem
rohen CalledProcessError-Traceback, der Reserve-Refill lief nie (im 21:26-
Lauf trotz 6/6 zertifizierter Reserve-Kandidaten) und das Auto-Issue riet
zu API-Keys/GitHub-Status statt zur echten Ursache.

WF-1F8C (#522) machte den Linker shortcode-blind. Diese Tests beweisen
die zweite Schicht (eine Quelle, alle Aufrufer – Engine, Kadenz-Backstop,
Deploy-Refill):

  1. heal_shortcode_damage(): führt die Shortcode-Wache aus, warnt bei
     Wachen-Fehler, blockiert die Endabnahme aber nie.
  2. build_site(): ein toter Hugo-Build wird strukturiert diagnostiziert
     (echte Fehlerzeile + Reparaturpfad) und als ReleaseBuildCrash
     weitergereicht – nie geschluckt, nie roher Traceback.
  3. Exit-Code-Vertrag: 0 = ok · 1 = Tagesdefizit · 3 = Release-Crash;
     main() übersetzt Crashs in Exit 3 statt zu crashen.
  4. Engine-Verdrahtung: Die Workflow führt die Shortcode-Wache VOR der
     Endabnahme aus und die Endkontrolle benennt die Fehlerklasse.

Ausführung wie Bestands-Tests:
  python3 -m unittest discover -s scripts/tests -v
"""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[2]

import datetime as dt

import audit_log
import publication_release as pr
import selftest_clock as uhr_zwang

# Gepinnter Publikationstag (Mittwoch): `--refill-only` füllt nur an
# cadence_guard.PUBLICATION_DAYS nach. Der Test gilt damit an jedem
# Kalendertag – vorher war er am Wochenende und unter jeder vorgestellten
# Uhr rot, weil der Lauf dann gar nichts tut.
_POSTTAG = dt.datetime(2026, 11, 4, 12, 0, tzinfo=dt.timezone.utc)


# Das echte Hugo-Log des fehlgeschlagenen Laufs 37052950135 (WF-A535 #529):
# „Start building sites“-Fortschritt steht auf stdout, die ERROR-Zeilen auf
# stderr – hier als ein kombinierter Text, wie build_site() ihn auswertet.
ECHTES_HUGO_LOG = (
    "Start building sites … \n"
    "hugo v0.164.0-ce2470e7… linux/amd64 BuildDate:2026-07-06\n"
    'ERROR rechner: unbekannter typ "[notgroschen](../../posts/2026-09-09-'
    'notgroschen-die-wahrheit-ueber-das-finanzielle-polster/)" '
    "(erlaubt: notgroschen, budget-503020, strom-abschlag, gas-abschlag, dsl-effektiv)\n"
    "Total in 1321 ms\n"
    "ERROR error building site: logged 1 error(s)\n"
)


class _Rc:
    def __init__(self, rc):
        self.returncode = rc


class HeilungsVertragTests(unittest.TestCase):
    """heal_shortcode_damage(): best-effort, niemals blockierend."""

    def test_ruft_die_wache_mit_fix(self):
        aufrufe = []

        def runner(cmd):
            aufrufe.append(cmd)
            return _Rc(0)

        self.assertTrue(pr.heal_shortcode_damage(runner=runner))
        self.assertEqual(len(aufrufe), 1)
        self.assertIn('shortcode_guard.py', ' '.join(aufrufe[0]))
        self.assertIn('--fix', aufrufe[0])

    def test_wachen_fehler_wird_warnung_nicht_blockade(self):
        with patch('builtins.print'):  # Diagnose-Ausgabe ist kein Testgegenstand
            self.assertFalse(pr.heal_shortcode_damage(runner=lambda cmd: _Rc(2)))

    def test_wachen_absturz_wird_warnung_nicht_blockade(self):
        def kaputt(cmd):
            raise OSError("Wache nicht startbar")

        with patch('builtins.print'):
            self.assertFalse(pr.heal_shortcode_damage(runner=kaputt))


class BuildDiagnoseTests(unittest.TestCase):
    """build_site(): toter Build → strukturierte Diagnose + Crash-Klasse."""

    def test_diagnose_findet_die_echte_fehlerzeile(self):
        funde = pr.diagnose_hugo_failure(ECHTES_HUGO_LOG)
        self.assertTrue(funde, "Diagnose findet keine Fehlerzeile")
        self.assertIn('unbekannter typ', funde[0])
        self.assertIn('error building site', ' '.join(funde))

    def test_diagnose_schweigt_auf_saugerem_log(self):
        self.assertEqual(pr.diagnose_hugo_failure("Total in 42 ms\n"), [])
        self.assertEqual(pr.diagnose_hugo_failure(""), [])

    def _toter_build(self):
        class Proc:
            returncode = 1
            stdout = ""
            stderr = ECHTES_HUGO_LOG
        return Proc()

    def test_toter_build_wird_diagnostiziert_und_weitergereicht(self):
        with patch.object(audit_log, 'log_event', lambda **kw: '/dev/null'), \
             patch('builtins.print') as fake_print:
            with self.assertRaises(pr.ReleaseBuildCrash):
                pr.build_site(runner=lambda cmd: self._toter_build())
        ausgabe = '\n'.join(str(c) for c in fake_print.call_args_list)
        self.assertIn('unbekannter typ', ausgabe)          # echte Ursache
        self.assertIn('shortcode_guard.py', ausgabe)        # Reparaturpfad
        self.assertIn('KEIN Tagesdefizit', ausgabe)         # Klassen-Trennung

    def test_gesunder_build_durchlaessig(self):
        class Proc:
            returncode = 0
            stdout = "Start building sites … \nTotal in 900 ms\n"
            stderr = ""
        with patch('builtins.print') as fake_print:
            pr.build_site(runner=lambda cmd: Proc())
        fake_print.assert_called_once()  # Fortschritt bleibt sichtbar


class ExitCodeVertragTests(unittest.TestCase):
    """Exit-Codes: 1 = Defizit (unverändert), 3 = Release-Crash."""

    def test_vertrag_ist_piniert(self):
        self.assertEqual(pr.EXIT_DEFIZIT, 1)
        self.assertEqual(pr.EXIT_CRASH, 3)

    def test_crash_der_endabnahme_wird_exit_3(self):
        """Genau das 02.10.-Muster: refill stirbt am Build → Exit 3, kein Traceback."""
        def toter_build(*a, **kw):
            raise subprocess.CalledProcessError(1, ['hugo', '--minify'])

        # Die Uhr wird auf einen Publikationstag (Mittwoch) gepinnt: An
        # Nicht-Publikationstagen füllt `--refill-only` nichts nach
        # (cadence_guard.PUBLICATION_DAYS) und der Crash-Vertrag wäre gar nicht
        # prüfbar – der Test würde am Wochenende bzw. unter einer vorgestellten
        # Uhr rot, ohne dass der Code sich geändert hätte.
        with uhr_zwang.uhr(_POSTTAG, uhr_zwang.MODUS_VERSCHOBEN,
                           module=[pr]), \
             patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, 'refill_to_min', toter_build), \
             patch.object(audit_log, 'log_event', lambda **kw: '/dev/null'), \
             patch('builtins.print'):
            rc = pr.main(['--refill-only'])
        self.assertEqual(rc, pr.EXIT_CRASH)

    def test_release_build_crash_wird_exit_3(self):
        def crash(*a, **kw):
            raise pr.ReleaseBuildCrash("hugo --minify: Exit 1")

        with patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, '_dispatch', crash), \
             patch('builtins.print'):
            rc = pr.main([])
        self.assertEqual(rc, pr.EXIT_CRASH)

    def test_ok_bleibt_exit_0_defizit_bleibt_exit_1(self):
        with patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, '_dispatch', lambda args: pr.EXIT_DEFIZIT):
            self.assertEqual(pr.main([]), 1)
        with patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, '_dispatch', lambda args: 0):
            self.assertEqual(pr.main([]), 0)


class DoppelmodulRegressionTests(unittest.TestCase):
    """Dauerheilung #740: by-name-Import baute eine zweite Modulinstanz.

    14.10.2026: Der Deploy starb 8× in Folge am Schritt „Quote-Nachfüllung
    nach Gate-Verlust“ und fror die Live-Site ein. Zwei Schichten:

    1. `reserve_pool.publish_to_min` (validator=None) importierte
       `publication_release` by name. In `__main__`-Ausführung
       (`python3 scripts/publication_release.py`) ist das der SKRIPT-Modul
       `__main__` – der Import baute eine ZWEITE Instanz mit eigener
       ReleaseBuildCrash-Klasse. Ein dort geworfener Crash entkam dem
       `except ReleaseBuildCrash` in main(): roher Traceback, Exit 1
       statt des Diagnose-Vertrags (Exit 3).
    2. Der Deploy-Job hatte die Messkette unvollständig (kein hunspell) –
       die Qualitätsmessung eines jeden Reserve-Kandidaten fiel aus und
       schickte den Crash erst gar in Gang.

    Schicht 1 wird hier regressionsgesichert (Modul-Identität,
    Crash-Vertrag über den Import-Pfad, benannte Ursache). Schicht 2 ist
    Workflow-Verdrahtung (deploy.yml installiert hunspell, Schritt
    bewertet den Exit-Code statt ihn durchzureichen – Dauerheilung #676).
    """

    def test_import_pfad_teilt_modul_und_crash_klasse(self):
        """Jeder by-name-Import in einem Prozess sieht dieselbe Instanz."""
        import importlib

        mod = importlib.import_module('publication_release')
        self.assertIs(mod, pr,
                      "by-name-Import liefert eine andere Modulinstanz")
        self.assertIs(mod.ReleaseBuildCrash, pr.ReleaseBuildCrash,
                      "Zweite ReleaseBuildCrash-Klasse – Crashes entkommen "
                      "dem except-Haken (Befund #740)")

    def test_skriptlauf_im_main_modus_haelt_den_ganzen_vertrag(self):
        """Produktions-Aufruf `python3 scripts/…` (Deploy-Modus): Der
        Selbsttest prüft in seinen Sektionen 4–6 die Modul-Identität,
        den Crash-Vertrag über den Import-Pfad und die Validator-Wiring
        aus DEM Prozess. Bei Abweichung ist er rot (Exit 2) – dieser Test
        hält den __main__-Pfad als Ganzes fest, nicht nur das Modul."""
        script = REPO / 'scripts' / 'publication_release.py'
        proc = subprocess.run(
            [sys.executable, str(script), '--selftest'],
            capture_output=True, text=True, timeout=300, cwd=REPO)
        self.assertEqual(
            proc.returncode, 0,
            f"Selbsttest im __main__-Modus rot "
            f"(rc={proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
        self.assertIn('#740-Modul-Identität', proc.stdout,
                      "Die #740-Prüfsektionen fehlen aus dem Selbsttest")

    def test_release_crash_nennt_die_ursache(self):
        """Ein ReleaseBuildCrash wird exit 3 – UND die Ursache steht
        namentlich im Log (WF-A535-Lektion: ein roter Schritt, der die
        Ursache nicht nennt, erzieht zum Wegsehen)."""
        def mess_crash(*a, **kw):
            raise pr.ReleaseBuildCrash(
                "Qualitätsmessung ausgefallen: {'spelling': "
                "\"[Errno 2] No such file or directory: 'hunspell'\"}")

        with patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, '_dispatch', mess_crash), \
             patch('builtins.print') as fake_print:
            rc = pr.main(['--refill-only'])
        self.assertEqual(rc, pr.EXIT_CRASH)
        ausgabe = '\n'.join(str(c) for c in fake_print.call_args_list)
        self.assertIn('Ursache', ausgabe)
        self.assertIn('hunspell', ausgabe,
                      "Die Mess-Lücke muss namentlich benannt sein")
        self.assertIn('KEIN Tagesdefizit', ausgabe,
                      "Crash und Defizit bleiben getrennte Klassen")


class DeployQuoteRefillVerdrahtungTests(unittest.TestCase):
    """Dauerheilung #740, Workflow-Schicht: Der Deploy darf die Quote-Messung
    nicht unvollständig ausführen und ihr Werkzeugfehler dürfen die
    öffentliche Auslieferung nicht blockieren (Dauerheilung #676-Muster:
    erst liefern, dann siegeln).
    """

    def setUp(self):
        import yaml  # pragma: no cover - CI hat PyYAML

        self.yaml = yaml
        self.deploy = yaml.safe_load(
            (REPO / '.github' / 'workflows' / 'deploy.yml')
            .read_text(encoding='utf-8'))
        self.job = (self.deploy.get('jobs') or {}).get('deploy') or {}
        self.steps = self.job.get('steps') or []
        self.raw = (REPO / '.github' / 'workflows' / 'deploy.yml') \
            .read_text(encoding='utf-8')

    def _step(self, name: str) -> dict:
        for step in self.steps:
            if isinstance(step, dict) and step.get('name') == name:
                return step
        raise AssertionError(f"Schritt fehlt im deploy-Job: {name}")

    def test_deploy_installiert_die_messkette(self):
        """Ohne hunspell fällt die Qualitätsmessung aus (Befund #740).
        Alle übrigen Workflows der Messkette installieren es – der Deploy
        genauso."""
        self.assertIn('hunspell hunspell-de-de', self.raw,
                      "Der deploy-Job installiert die Messkette (hunspell) "
                      "nicht – die Quote-Nachfüllung crascht am ersten "
                      "Kandidaten (Befund #740)")

    def test_refill_schritt_bewertet_den_exit_code(self):
        step = self._step(
            "Quote-Nachfüllung nach Gate-Verlust (Re-Queue + Reserve → Min)")
        self.assertEqual(step.get('id'), 'quote_refill')
        run = step.get('run') or ""
        self.assertIn('case "$refill" in', run,
                      "Der Schritt muss seinen Exit-Code AUSWERTELN statt "
                      "ihn durchzureichen (Dauerheilung #676/#740)")
        self.assertNotIn('exit 1', run,
                         "Ein Werkzeugfehler der Quote-Nachfüllung darf den "
                         "Deploy nicht hart stoppen (Geiselhaltung #740)")
        self.assertIn('werkzeugfehler=true', run,
                      "Der Werkzeugfehler muss nach außen gegeben werden "
                      "(release-seal wertet ihn rot)")
        self.assertIn('::error::', run,
                      "Der Befund muss laut bleiben – leise weiter wäre "
                      "Scheingrün (C33)")

    def test_job_veroeffentlicht_den_refill_befund(self):
        outputs = self.job.get('outputs') or {}
        self.assertIn('refill_werkzeugfehler', outputs)
        self.assertIn('steps.quote_refill.outputs.werkzeugfehler',
                      outputs['refill_werkzeugfehler'])

    def test_siegel_wertet_den_refill_befund_rot(self):
        seal = (self.deploy.get('jobs') or {}).get('release-seal') or {}
        self.assertTrue(seal, "release-seal fehlt in deploy.yml")
        run = ((seal.get('steps') or [{}])[0]).get('run') or ""
        self.assertIn('REFILL_WERKZEUGFEHLER', run,
                      "Das Siegel muss den Refill-Werkzeugfehler lesen")
        self.assertIn('REFILL_WERKZEUGFEHLER" = "true"', run,
                      "Der Befund muss das Siegel rot machen (nach der "
                      "Auslieferung, nicht vor)")
        self.assertIn('::error::', run)


class EngineVerdrahtungTests(unittest.TestCase):
    """Die Engine-Workflow muss die Wache vor der Endabnahme verdrahten.

    Spiegelt test_deploy_workflow_wires_refill_after_publish_gate (#287):
    Verdrahtung ist Vertrag – ein Refactoring darf die Fangnetze nicht
    still entfernen.
    """

    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.yml = (root / '.github' / 'workflows' / 'content-engine-v2.yml'
                    ).read_text(encoding='utf-8')

    def test_wache_steht_vor_der_endabnahme(self):
        wache = self.yml.find('python3 scripts/shortcode_guard.py --fix')
        endabnahme = self.yml.find('python3 scripts/publication_release.py')
        self.assertGreater(wache, 0, 'Shortcode-Wache fehlt in der Engine')
        self.assertGreater(endabnahme, 0, 'Endabnahme fehlt in der Engine')
        self.assertGreater(
            endabnahme, wache,
            'Shortcode-Wache muss VOR der Endabnahme laufen (WF-A535 #529)')

    def test_endkontrolle_benennt_die_fehlerklasse(self):
        self.assertIn('steps.final_release.outputs.rc', self.yml,
                      'Exit-Code der Endabnahme muss lesbar sein')
        self.assertIn('TAGESDEFIZIT', self.yml,
                      'Defizit-Klasse muss benannt werden')
        self.assertIn('RELEASE-CRASH', self.yml,
                      'Crash-Klasse muss benannt werden (WF-A535 #529)')


if __name__ == '__main__':
    unittest.main()
