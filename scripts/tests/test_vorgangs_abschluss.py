#!/usr/bin/env python3
"""Vorgangs-Abschluss – Regressionssperre für den Abschlussvermerk (WF-A4E0 / #552).

WARUM DIESE TESTS EXISTIEREN (04.10.2026)
-----------------------------------------
Meldung #552 schloss sich beim Zusammenführen automatisch – aber stumm, weil das
persönliche Zugangsrecht keine Kommentare schreiben darf (HTTP 403). Der Befund
dahinter ist nicht „ein Kommentar fehlt", sondern: der Abschluss eines Vorgangs
hing am Recht einer einzelnen Person. Jetzt schreibt das Repository selbst.

Gesichert wird deshalb nicht nur der Text, sondern das VERFAHREN:

  1. Der Vermerk ist markenrein – Issue-Kommentare sind öffentlich.
  2. Nichts gilt als erledigt, was nicht zurückgelesen wurde.
  3. Der Lauf, der schreiben darf, existiert und hat genau das Recht dafür –
     und er hat einen Nachlauf, falls das Ereignis einmal ausfällt.

Lauf: python3 -m unittest scripts.tests.test_vorgangs_abschluss
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WERKZEUG = os.path.join(WURZEL, "scripts", "vorgangs_abschluss.py")
LAUF = os.path.join(WURZEL, ".github", "workflows", "vorgangs-abschluss.yml")
PAKET = os.path.join(WURZEL, "package.json")

sys.path.insert(0, os.path.join(WURZEL, "scripts"))
import vorgangs_abschluss as abschluss  # noqa: E402

PR = {"number": 558, "merged_at": "2026-10-04T09:30:30Z",
      "title": "fix(marke): README-Markenfläche heilen (WF-A4E0, #552)",
      "body": "Begründung …\n\nCloses #552"}
MELDUNG = {"number": 552, "title": "🔧 Wartung · Betriebspflege · Vorgang WF-A4E0"}


class SelbsttestLaeuft(unittest.TestCase):
    def test_selbsttest_gruen(self):
        ergebnis = subprocess.run([sys.executable, WERKZEUG, "--selftest"],
                                  cwd=WURZEL, capture_output=True, text=True,
                                  timeout=120)
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)


class VermerkIstMarkenrein(unittest.TestCase):
    """Ein Issue-Kommentar ist eine öffentliche Fläche – wie das README."""

    def test_vermerk_traegt_keine_betriebssprache(self):
        text, hinweise = abschluss.vermerk(PR, MELDUNG)
        self.assertEqual([], abschluss._markenfunde(text),
                         "Der öffentliche Vermerk trägt Betriebssprache")
        self.assertEqual([], hinweise)

    def test_lauter_titel_wird_nicht_durchgereicht(self):
        laut = dict(PR, title="chore: Workflow-Gates in scripts/ nachziehen")
        text, hinweise = abschluss.vermerk(laut, MELDUNG)
        self.assertEqual([], abschluss._markenfunde(text))
        self.assertTrue(any("Kurzform" in h for h in hinweise),
                        "Der Rückfall auf die Kurzform muss im Protokoll stehen")

    def test_vermerk_nennt_vorschlag_datum_und_vorgang(self):
        text, _ = abschluss.vermerk(PR, MELDUNG)
        for teil in ("#558", "04.10.2026", "WF-A4E0"):
            self.assertIn(teil, text)

    def test_marker_ist_unsichtbar_und_eindeutig(self):
        self.assertTrue(abschluss.marker(558).startswith("<!--"))
        self.assertNotEqual(abschluss.marker(558), abschluss.marker(559))


class VerfahrenIstBelastbar(unittest.TestCase):
    """Geschrieben gilt nur, was zurückgelesen wurde."""

    def test_planmodus_schreibt_nichts(self):
        api = abschluss._ProbeApi({558: PR}, {552: MELDUNG})
        getan, offen = abschluss.vermerke_vorschlag(api, 558, anwenden=False)
        self.assertEqual(0, api.schreibzugriffe)
        self.assertEqual([], offen)
        self.assertEqual(1, len(getan))

    def test_zweiter_lauf_schreibt_nicht_noch_einmal(self):
        api = abschluss._ProbeApi({558: PR}, {552: MELDUNG})
        abschluss.vermerke_vorschlag(api, 558, anwenden=True)
        abschluss.vermerke_vorschlag(api, 558, anwenden=True)
        self.assertEqual(1, api.schreibzugriffe)

    def test_fehlendes_schreibrecht_ist_sichtbar(self):
        api = abschluss._ProbeApi({558: PR}, {552: MELDUNG}, schreibfehler=True)
        _, offen = abschluss.vermerke_vorschlag(api, 558, anwenden=True)
        self.assertTrue(offen)
        self.assertIn("issues: write", offen[0])

    def test_ohne_nachweis_kein_erfolg(self):
        api = abschluss._ProbeApi({558: PR}, {552: MELDUNG}, luegt=True)
        getan, offen = abschluss.vermerke_vorschlag(api, 558, anwenden=True)
        self.assertEqual([], getan)
        self.assertTrue(offen)

    def test_offener_vorschlag_wird_nicht_abgeschlossen(self):
        offener = {"number": 559, "merged_at": None, "title": "x",
                   "body": "Closes #1"}
        api = abschluss._ProbeApi({559: offener}, {1: {"number": 1, "title": "x"}})
        getan, offen = abschluss.vermerke_vorschlag(api, 559, anwenden=True)
        self.assertEqual(0, api.schreibzugriffe)
        self.assertEqual([], getan)
        self.assertTrue(offen)

    def test_meldungen_werden_aus_allen_schluesselwoertern_gelesen(self):
        self.assertEqual([552], abschluss.meldungen_aus({"title": "", "body": "Closes #552"}))
        self.assertEqual([12, 13], abschluss.meldungen_aus(
            {"title": "fixes #12", "body": "resolved #13"}))
        self.assertEqual([], abschluss.meldungen_aus(
            {"title": "", "body": "siehe #99"}),
            "Eine bloße Erwähnung ist kein Abschluss")


class LaufHatDasRecht(unittest.TestCase):
    """Der Kern der Heilung: das Recht hängt am Repo, nicht an einer Person."""

    def setUp(self):
        with open(LAUF, encoding="utf-8") as datei:
            self.lauf = datei.read()

    def test_lauf_existiert_mit_schreibrecht_auf_meldungen(self):
        self.assertIn("issues: write", self.lauf)

    def test_lauf_reagiert_auf_zusammenfuehrung_und_hat_einen_nachlauf(self):
        self.assertIn("pull_request_target", self.lauf)
        self.assertIn("schedule", self.lauf)
        self.assertIn("--nachtrag", self.lauf)

    def test_lauf_prueft_sich_zuerst_selbst(self):
        self.assertIn("--selftest", self.lauf)

    def test_lauf_fuehrt_keinen_fremden_code_aus(self):
        self.assertIn("default_branch", self.lauf,
                      "pull_request_target muss den Zielzweig auschecken")

    def test_npm_befehle_stehen_bereit(self):
        with open(PAKET, encoding="utf-8") as datei:
            skripte = json.load(datei)["scripts"]
        for name in ("vorgang:abschluss", "vorgang:nachtrag", "test:vorgang"):
            self.assertIn(name, skripte)


if __name__ == "__main__":
    unittest.main()
