# -*- coding: utf-8 -*-
"""Tests für `scripts/abgeleitete_register.py` – die Ableitung folgt der Quelle.

Warum eigene Tests: Der Befund vom 09.11.2026 war kein Inhaltsfehler, sondern
eine fehlende Verbindung zwischen Heiler und Ableitung. Ein einzelner
Nachzug hätte ihn geheilt; erst diese Tests halten die Verbindung.

  1. Der Nachzug steht im Commit-Pfad von `deploy.yml` – und VOR dem Commit.
  2. Der Selbsttest des Werkzeugs läuft (Sabotage-Schutz).
  3. Jedes deklarierte Register ist aktuell (Drift ist ein roter Test).
  4. Das Verzeichnis ist nicht leer und nennt für jeden Pfad einen Schreiber.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "abgeleitete_register.py"
DEPLOY = ROOT / ".github" / "workflows" / "deploy.yml"

sys.path.insert(0, str(ROOT / "scripts"))
import abgeleitete_register as ar  # noqa: E402


def _schritte() -> list[dict]:
    """Schritte des deploy-Jobs in Reihenfolge (nur Name + run reichen hier)."""
    import yaml

    daten = yaml.safe_load(DEPLOY.read_text(encoding="utf-8"))
    schritte = []
    for _job, inhalt in daten["jobs"].items():
        for schritt in inhalt.get("steps") or []:
            schritte.append(schritt)
    return schritte


class VerzeichnisTest(unittest.TestCase):
    def test_verzeichnis_ist_nicht_leer_und_hat_schreiber(self):
        self.assertTrue(ar.REGISTER, "leeres Verzeichnis – der Wächter prüft nichts")
        for register in ar.REGISTER:
            self.assertTrue((ROOT / register.skript).is_file(), register.skript)
            self.assertTrue(register.zweck.strip(), register.pfad)

    def test_selftest(self):
        erg = subprocess.run([sys.executable, str(SKRIPT), "--selftest"],
                             capture_output=True, text=True, check=False)
        self.assertEqual(erg.returncode, 0, erg.stdout + erg.stderr)


class DriftTest(unittest.TestCase):
    def test_alle_register_sind_aktuell(self):
        """Der Befund selbst: eine Ableitung, die ihrer Quelle hinterherläuft."""
        erg = subprocess.run([sys.executable, str(SKRIPT), "--check"],
                             capture_output=True, text=True, check=False)
        self.assertEqual(erg.returncode, 0,
                         "Register veraltet – python3 scripts/abgeleitete_register.py --fix\n"
                         + erg.stdout + erg.stderr)

    def test_abweichung_nennt_die_zeile(self):
        zeilen = ar._abweichung("a\nb\nc\n", "a\nX\nc\n")
        self.assertEqual(len(zeilen), 1)
        self.assertIn("Zeile 2", zeilen[0])
        self.assertIn("'X'", zeilen[0])
        self.assertEqual(ar._abweichung("a\n", "a\n"), [])


class EinhaengungTest(unittest.TestCase):
    """Der Nachzug darf nicht aus dem Commit-Pfad verschwinden."""

    @classmethod
    def setUpClass(cls):
        cls.schritte = _schritte()

    def _index(self, muster: str) -> list[int]:
        treffer = re.compile(muster)
        return [nr for nr, schritt in enumerate(self.schritte)
                if treffer.search(str(schritt.get("run", ""))
                                  + " " + str(schritt.get("uses", ""))
                                  + " " + str(schritt.get("name", "")))]

    def test_schritt_zieht_register_nach(self):
        self.assertTrue(self._index(r"abgeleitete_register\.py\s+--fix"),
                        "deploy.yml zieht abgeleitete Register nicht mehr nach")

    def test_selbsttest_steht_davor(self):
        selbst, fix = self._index(r"abgeleitete_register\.py\s+--selftest"), \
            self._index(r"abgeleitete_register\.py\s+--fix")
        self.assertTrue(selbst, "Selbsttest des Nachzugs fehlt in deploy.yml")
        self.assertLess(min(selbst), min(fix),
                        "Der Selbsttest muss VOR dem Nachzug laufen (fail-closed)")

    def test_nachzug_steht_vor_dem_gate_commit(self):
        commit = self._index(r"Gate-Heilungen committen")
        fix = self._index(r"abgeleitete_register\.py\s+--fix")
        self.assertTrue(commit, "`Gate-Heilungen committen` fehlt – Anker weg")
        self.assertLess(min(fix), min(commit),
                        "Register-Nachzug muss VOR dem Commit stehen, sonst bleibt "
                        "die Ableitung im selben Lauf wieder alt")


if __name__ == "__main__":
    unittest.main()
