# -*- coding: utf-8 -*-
"""Tests für `scripts/ci_tests.py` – der Wächter über den Wächter.

Warum eigene Tests: Der Helfer entscheidet, ob ein roter CI-Lauf seine
Ursache mitliefert. Fällt er still aus (keine Annotation, falscher
Exit-Code), sieht der nächste Ausfall wieder aus wie „exit code 1" –
genau der Zustand, aus dem #1137 entstanden ist.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "ci_tests.py"


def rufe(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SKRIPT), *args],
        capture_output=True, text=True, check=False,
        cwd=str(cwd) if cwd else None,
    )


class CiTestsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ci-tests-"))

    def modul(self, name: str, inhalt: str) -> Path:
        pfad = self.tmp / f"{name}.py"
        pfad.write_text(textwrap.dedent(inhalt), encoding="utf-8")
        return pfad

    def test_roter_test_wird_mit_namen_annotiert(self) -> None:
        """Der Kern von #1137: aus „exit 1" wird der Testname."""
        self.modul("rot", """
            import unittest

            class Rot(unittest.TestCase):
                def test_kante(self):
                    self.assertGreaterEqual(49, 50)
        """)
        erg = rufe("--titel", "KI-Transparenz", "--",
                   sys.executable, "-m", "unittest", "rot", "-v", cwd=self.tmp)
        self.assertEqual(erg.returncode, 1, "ein rotes Gate darf nie grün werden")
        self.assertIn("::error title=KI-Transparenz::", erg.stdout)
        self.assertIn("test_kante", erg.stdout)
        self.assertIn("49 not greater than or equal to 50", erg.stdout)

    def test_gruener_lauf_annotiert_nichts(self) -> None:
        self.modul("gruen", """
            import unittest

            class Gruen(unittest.TestCase):
                def test_ok(self):
                    self.assertTrue(True)
        """)
        erg = rufe("--titel", "Probe", "--", sys.executable, "-m", "unittest", "gruen",
                   cwd=self.tmp)
        self.assertEqual(erg.returncode, 0)
        self.assertNotIn("::error", erg.stdout)

    def test_fehlschlag_ohne_unittest_format_nennt_die_log_spitze(self) -> None:
        """Absturz im Setup (fehlendes Hugo, Import-Fehler) hat keinen FAIL-Block."""
        erg = rufe("--titel", "Uhr-Probe", "--",
                   sys.executable, "-c", "raise SystemExit('hugo fehlt im PATH')")
        self.assertEqual(erg.returncode, 1)
        self.assertIn("::error title=Uhr-Probe::", erg.stdout)
        self.assertIn("hugo fehlt im PATH", erg.stdout)

    def test_exitcode_des_befehls_wird_durchgereicht(self) -> None:
        erg = rufe("--titel", "Probe", "--", sys.executable, "-c", "raise SystemExit(7)")
        self.assertEqual(erg.returncode, 7)

    def test_logdatei_wird_geschrieben_und_gekuerzt_angezeigt(self) -> None:
        self.modul("viel", """
            import unittest

            class Viel(unittest.TestCase):
                def test_ausgabe(self):
                    for i in range(400):
                        print(f"zeile {i}")
                    self.fail("viele Zeilen")
        """)
        log = self.tmp / "viel.log"
        erg = rufe("--titel", "Probe", "--log", str(log), "--zeigen", "5", "--",
                   sys.executable, "-m", "unittest", "viel", "-v", cwd=self.tmp)
        self.assertEqual(erg.returncode, 1)
        self.assertTrue(log.is_file(), "die vollständige Ausgabe muss auf Platte liegen")
        self.assertIn("zeile 399", log.read_text(encoding="utf-8"))
        # Der Schritt-Log bleibt lesbar: nur die letzten Zeilen werden gezeigt.
        self.assertNotIn("zeile 0\n", erg.stdout)

    def test_max_begrenzt_die_annotationsflut(self) -> None:
        self.modul("viele", """
            import unittest

            class Viele(unittest.TestCase):
                def test_a(self): self.fail("a")
                def test_b(self): self.fail("b")
                def test_c(self): self.fail("c")
        """)
        erg = rufe("--titel", "Probe", "--max", "2", "--",
                   sys.executable, "-m", "unittest", "viele", "-v", cwd=self.tmp)
        self.assertEqual(erg.stdout.count("::error title=Probe::"), 2)

    def test_selftest(self) -> None:
        erg = rufe("--selftest")
        self.assertEqual(erg.returncode, 0, erg.stdout + erg.stderr)


if __name__ == "__main__":
    unittest.main()
