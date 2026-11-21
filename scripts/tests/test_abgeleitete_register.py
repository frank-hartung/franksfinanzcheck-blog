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


class BefundAkteRegisterTest(unittest.TestCase):
    """WF-B16A/#1229 (21.11.2026): Die Befund-Akte ist eine Ableitung.

    ANLASS: Fünf offene „🩺 Nachlauf-Wache"-Meldungen innerhalb von fünf Tagen
    (#1229, #1251, #1252, #1266, #1267, #1271) – jedes Mal „BEFUND-AKTE.md
    oder Zustand stimmt nicht mit dem Ledger überein". Die Akte hatte keinen
    Nachzug am Erzeuger, weil sie in diesem Verzeichnis fehlte. Diese Tests
    halten die Einhängung fest, damit die Klasse nicht beim nächsten Register
    von vorn beginnt.
    """

    def test_akte_ist_registriert(self):
        pfade = {r.pfad for r in ar.REGISTER}
        self.assertIn("BEFUND-AKTE.md", pfade,
                      "Die Befund-Akte ist wieder aus dem Verzeichnis "
                      "abgeleiteter Register verschwunden – dann läuft sie "
                      "ihrer Quelle wieder hinterher (#1229)")

    def test_akte_nennt_schreiber_und_unterbefehle(self):
        reg = next(r for r in ar.REGISTER if r.pfad == "BEFUND-AKTE.md")
        self.assertEqual(reg.skript, "scripts/faktenfrische_befund_akte.py")
        self.assertEqual(reg.check, "--check")
        self.assertEqual(reg.fix, "--schreiben",
                         "Der Nachzug muss über --schreiben laufen, den "
                         "einzigen erlaubten Schreiber")

    def test_schreiber_bietet_check_und_schreiben(self):
        """Das Interface, das `abgeleitete_register.py` aufruft, muss da sein."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import faktenfrische_befund_akte as akte
        self.assertTrue(callable(getattr(akte, "pruefen", None)),
                        "pruefen() fehlt – --check wäre blind")
        self.assertTrue(callable(getattr(akte, "erstellen", None)),
                        "--schreiben-Implementierung fehlt")

    def test_akte_folgt_im_selben_commit(self):
        """Der Nachzug am Erzeuger (git_sync.sh) darf nicht verschwinden."""
        sync = (ROOT / "scripts" / "git_sync.sh").read_text(encoding="utf-8")
        self.assertIn("faktenfrische_akte_nachziehen", sync)
        self.assertGreaterEqual(
            sync.count("faktenfrische_akte_nachziehen "), 2,
            "Der Haken muss in BEIDEN Modi stehen (Vollbedienung und "
            "--push-only) – sonst bleibt die Lücke für fremde Workflows offen")
        for pfad in ("BEFUND-AKTE.md", "data/faktenfrische_befunde_state.json"):
            self.assertIn(pfad, sync)


class SchreiberIdempotenzTest(unittest.TestCase):
    """Der Nachzug im Commit-Pfad darf keinen Leerlauf-Commit erzeugen.

    `deploy.yml` committet jede Änderung, die `git status --short` sieht, und
    der strukturelle Gate-Rebuild hängt daran. Ein Schreiber, der bei jedem
    Aufruf einen neuen Zeitstempel stempelt, hätte damit eine Endlosschleife
    aus Commit → Rebuild → Commit erzeugt.
    """

    def test_zweiter_lauf_aendert_keine_bytes(self):
        import datetime as dt
        sys.path.insert(0, str(ROOT / "scripts"))
        import faktenfrische_befund_akte as akte
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            md, state = root / "BEFUND-AKTE.md", root / "data/state.json"
            text, zustand = "Akte\n", {"erzeugt": "2026-11-21T00:00:00Z",
                                       "offen": 1, "stichtag": "2026-11-21"}
            with patch.object(akte, "AKTE_PATH", md), \
                 patch.object(akte, "STATE_PATH", state):
                akte._schreiben(text, dict(zustand))
                erste = state.read_text(encoding="utf-8")
                # Zweiter Lauf mit neuem Zeitstempel im Eingangswert:
                akte._schreiben(text, dict(zustand,
                                           erzeugt="2026-11-22T09:09:09Z"))
                self.assertEqual(state.read_text(encoding="utf-8"), erste,
                                 "Der Schreiber stempelt erneut – das wäre im "
                                 "Commit-Pfad ein Commit ohne Änderung")
                self.assertEqual(md.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
