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
             patch.object(pr, '_dispatch', crash):
            rc = pr.main([])
        self.assertEqual(rc, pr.EXIT_CRASH)

    def test_ok_bleibt_exit_0_defizit_bleibt_exit_1(self):
        with patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, '_dispatch', lambda args: pr.EXIT_DEFIZIT):
            self.assertEqual(pr.main([]), 1)
        with patch.object(pr, 'heal_shortcode_damage', lambda *a, **kw: True), \
             patch.object(pr, '_dispatch', lambda args: 0):
            self.assertEqual(pr.main([]), 0)


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
