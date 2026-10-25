#!/usr/bin/env python3
"""Regressionstests für den Skript-Syntax-Heiler (Bot-Watchdog #864).

WARUM (25.10.2026)
------------------
Der Befund `skript-syntax` trug seit jeher den Besitzer `auto`, aber es
gab keinen Heilweg: Das Ticket konnte sich nur schließen, wenn ein
Mensch ein fremdes Skript reparierte. Der Heiler schließt die Lücke –
und diese Tests frieren seine Sicherungen ein:

  1. Er stellt AUSSCHLIESSLICH die jüngste Fassung her, die kompiliert.
  2. Er heilt nie eine Datei, die nie gültig war (kein Erfinden).
  3. Er fasst nichts außerhalb von `scripts/**` an.
  4. Er ist idempotent und schreibt jede Heilung ins Audit-Ledger.
  5. Er heilt dieselbe Datei nicht im Kreis (Wiederholungsbremse).

Alle Proben laufen in Wegwerf-Repositories mit echtem git – kein Test
berührt die Geschichte dieses Repos.

Lauf: python3 -m unittest scripts.tests.test_skript_syntax_heiler
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(WURZEL, "scripts"))

import skript_syntax_heiler as heiler  # noqa: E402
import skript_syntax_wache as wache  # noqa: E402

GUT = "def addiere(a, b):\n    return a + b\n"
KAPUTT = "def addiere(a, b):\n    return a + b\n        return 0\n"


def git(*argumente, cwd):
    proc = subprocess.run(["git", *argumente], cwd=str(cwd),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(argumente)}: {proc.stderr}")
    return proc.stdout


class RepoFall(unittest.TestCase):
    """Gemeinsames Wegwerf-Repository mit echter Geschichte."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / "scripts").mkdir()
        (self.repo / "data").mkdir()
        git("init", "-q", "-b", "main", cwd=self.repo)
        git("config", "user.name", "Test", cwd=self.repo)
        git("config", "user.email", "test@example.invalid", cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def commit(self, datei: str, text: str, nachricht: str = "inhalt") -> None:
        pfad = self.repo / datei
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")
        git("add", datei, cwd=self.repo)
        git("commit", "-q", "-m", nachricht, cwd=self.repo)

    def ledger(self) -> list[dict]:
        pfad = heiler.audit_pfad(self.repo)
        if not pfad.is_file():
            return []
        return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


class HeilungTests(RepoFall):
    def setUp(self):
        super().setUp()
        self.commit("scripts/rechner.py", GUT, "gut")
        self.commit("scripts/rechner.py", KAPUTT, "kaputt")

    def test_heilung_stellt_die_letzte_gueltige_fassung_her(self):
        ergebnis = heiler.heile(self.repo)
        self.assertEqual(["scripts/rechner.py"], [h.datei for h in ergebnis.geheilt])
        self.assertEqual(GUT, (self.repo / "scripts/rechner.py").read_text(encoding="utf-8"))
        self.assertEqual([], wache.finde(self.repo))

    def test_ledger_belegt_beide_fassungen(self):
        heiler.heile(self.repo)
        eintraege = self.ledger()
        self.assertEqual(1, len(eintraege))
        eintrag = eintraege[0]
        for feld in heiler.AUDIT_PFLICHTFELDER:
            self.assertIn(feld, eintrag)
        self.assertNotEqual(eintrag["verworfen_sha"], eintrag["wiederhergestellt_sha"])
        self.assertEqual("scripts/rechner.py", eintrag["datei"])
        self.assertEqual(3, eintrag["zeile"])
        # Der Ledger ist lesbarer JSONL-Nachweis, kein Halbzustand.
        json.loads(json.dumps(eintrag, ensure_ascii=False))

    def test_zweiter_lauf_ist_still_und_idempotent(self):
        heiler.heile(self.repo)
        zweite = heiler.heile(self.repo)
        self.assertEqual([], zweite.geheilt)
        self.assertEqual([], zweite.offen)
        self.assertEqual(1, len(self.ledger()))

    def test_dry_run_schreibt_nichts(self):
        vorher = (self.repo / "scripts/rechner.py").read_text(encoding="utf-8")
        ergebnis = heiler.heile(self.repo, dry_run=True)
        self.assertEqual(1, len(ergebnis.geheilt))
        self.assertEqual(vorher, (self.repo / "scripts/rechner.py").read_text(encoding="utf-8"))
        self.assertFalse(heiler.audit_pfad(self.repo).exists())

    def test_kein_heilweg_ohne_kompilierenden_vorgaenger(self):
        self.commit("scripts/neu.py", KAPUTT, "von Anfang an kaputt")
        ergebnis = heiler.heile(self.repo)
        gruende = {o["datei"]: o["grund"] for o in ergebnis.offen}
        self.assertEqual("kein-vorgaenger", gruende.get("scripts/neu.py"))
        self.assertEqual(KAPUTT, (self.repo / "scripts/neu.py").read_text(encoding="utf-8"))

    def test_wiederholungsbremse_nach_zwei_heilungen(self):
        jetzt = datetime.datetime.now(datetime.timezone.utc)
        for lauf in range(heiler.MAX_HEILUNGEN_PRO_DATEI_24H):
            ergebnis = heiler.heile(self.repo, jetzt=jetzt)
            self.assertEqual(1, len(ergebnis.geheilt), f"Lauf {lauf}")
            git("add", "-A", cwd=self.repo)
            git("commit", "-q", "-m", f"heilung {lauf}", cwd=self.repo)
            self.commit("scripts/rechner.py", KAPUTT, f"wieder kaputt {lauf}")
        dritter = heiler.heile(self.repo, jetzt=jetzt)
        self.assertEqual([], dritter.geheilt)
        self.assertEqual("wiederholungsbremse", dritter.offen[0]["grund"])

    def test_bremse_zaehlt_nur_die_eigene_datei(self):
        jetzt = datetime.datetime.now(datetime.timezone.utc)
        self.commit("scripts/zweite.py", GUT, "gut")
        for lauf in range(heiler.MAX_HEILUNGEN_PRO_DATEI_24H):
            heiler.heile(self.repo, jetzt=jetzt)
            git("add", "-A", cwd=self.repo)
            git("commit", "-q", "-m", f"heilung {lauf}", cwd=self.repo)
            self.commit("scripts/rechner.py", KAPUTT, f"wieder kaputt {lauf}")
        self.commit("scripts/zweite.py", KAPUTT, "zweite kaputt")
        ergebnis = heiler.heile(self.repo, jetzt=jetzt)
        self.assertEqual(["scripts/zweite.py"], [h.datei for h in ergebnis.geheilt])


class HeilbereichTests(RepoFall):
    def test_nur_skripte_sind_heilbar(self):
        self.assertFalse(heiler._darf_geheilt_werden("layouts/partial.html", self.repo)[0])
        self.assertFalse(heiler._darf_geheilt_werden("hugo.toml", self.repo)[0])
        self.assertFalse(heiler._darf_geheilt_werden("scripts/notiz.txt", self.repo)[0])
        self.assertTrue(heiler._darf_geheilt_werden("scripts/tief/x.py", self.repo)[0])

    def test_lokale_aenderung_wird_nicht_ueberschrieben(self):
        self.commit("scripts/lokal.py", GUT, "gut")
        self.commit("scripts/lokal.py", KAPUTT, "kaputt")
        (self.repo / "scripts/lokal.py").write_text(KAPUTT + "# lokal\n", encoding="utf-8")
        ergebnis = heiler.heile(self.repo)
        self.assertEqual([], ergebnis.geheilt)
        self.assertEqual("arbeitsbaum-schmutzig", ergebnis.offen[0]["grund"])

    def test_head_sha_steht_im_ledger(self):
        self.commit("scripts/lokal.py", GUT, "gut")
        self.commit("scripts/lokal.py", KAPUTT, "kaputt")
        kopf = git("rev-parse", "HEAD", cwd=self.repo).strip()
        heiler.heile(self.repo)
        self.assertEqual(kopf, self.ledger()[0]["verworfen_sha"])


class SelftestTests(unittest.TestCase):
    def test_selbsttest_gruen(self):
        self.assertEqual(0, heiler.selftest())

    def test_check_auf_gruenem_baum(self):
        self.assertEqual(0, heiler.main(["--check", "--wurzel", WURZEL]))


if __name__ == "__main__":
    unittest.main()
