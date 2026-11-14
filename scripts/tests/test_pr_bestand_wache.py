#!/usr/bin/env python3
"""Tests für die PR-Bestands-Wache (14.11.2026).

Am 14.11.2026 lagen fünf Änderungsvorschläge offen, vier davon seit drei
Tagen ohne Bewegung. In dieser Zeit war `main` um 170 bis 210 Commits
weitergelaufen; die Vorschläge waren überholt, keiner ließ sich mehr
zusammenführen (`PR-BESTAND-HIGHEND-2026-11-14.md`). Keine Wache sah offene
Vorschläge an.

Diese Tests frieren vier Verträge ein:

  1. MESSUNG   – genau die Ruhefrist zählt schon; Entwürfe und maschinell
                 erzeugte Vorschläge zählen mit.
  2. KEIN STILLES GRÜN (C2) – nicht lesbar, abgeschnitten oder ohne
                 Leserecht ist „nicht messbar“, nie „keiner liegt“.
  3. BESITZ (D12) – der Bot-Watchdog führt den Befund mit menschlichem
                 Besitzer, im Voll-Lauf, nicht im Ausfall-Takt.
  4. NUR LESEN – die Wache ruft die GitHub-CLI ausschließlich lesend auf,
                 und der Workflow gibt ihr nur das Leserecht.

Läuft deterministisch ohne Netz: Der gh-Aufruf ist ersetzt.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import types
import unittest

import yaml

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import bot_watchdog as bw  # noqa: E402
import pr_bestand_wache as pbw  # noqa: E402

JETZT = dt.datetime(2026, 11, 14, 12, 0, tzinfo=dt.timezone.utc)


def vorschlag(nummer, bewegt, erstellt=None, **felder):
    eintrag = {"number": nummer, "updatedAt": bewegt,
               "createdAt": erstellt or bewegt, "isDraft": False,
               "mergeable": "MERGEABLE", "author": {"is_bot": False}}
    eintrag.update(felder)
    return eintrag


def antwort(eintraege, rc=0, stderr=""):
    """Ersatz für subprocess.run – merkt sich, was aufgerufen wurde."""
    aufrufe = []

    def lauf(argv, **_kw):
        aufrufe.append(list(argv))
        return types.SimpleNamespace(returncode=rc, stderr=stderr,
                                     stdout=json.dumps(eintraege))
    lauf.aufrufe = aufrufe
    return lauf


class Messung(unittest.TestCase):
    def test_genau_die_ruhefrist_zaehlt_schon(self):
        liegend = pbw.urteile([
            vorschlag(1, "2026-11-11T12:00:00Z"),   # genau 3 Tage
            vorschlag(2, "2026-11-11T12:00:01Z"),   # eine Sekunde weniger
        ], JETZT)
        self.assertEqual([e["nummer"] for e in liegend], [1])
        self.assertEqual(liegend[0]["ruhe_tage"], 3)

    def test_aeltester_stillstand_steht_vorn(self):
        liegend = pbw.urteile([
            vorschlag(30, "2026-11-10T09:00:00Z"),
            vorschlag(10, "2026-11-02T09:00:00Z"),
            vorschlag(20, "2026-11-10T08:00:00Z"),
        ], JETZT)
        self.assertEqual([e["nummer"] for e in liegend], [10, 20, 30])

    def test_entwurf_und_maschine_zaehlen_mit(self):
        liegend = pbw.urteile([
            vorschlag(5, "2026-11-01T00:00:00Z", isDraft=True),
            vorschlag(6, "2026-11-01T00:00:00Z", author={"is_bot": True}),
        ], JETZT)
        self.assertEqual(len(liegend), 2)
        self.assertTrue(liegend[0]["entwurf"])
        self.assertTrue(liegend[1]["maschinell"])

    def test_alter_ist_nie_kleiner_als_der_stillstand(self):
        liegend = pbw.urteile([vorschlag(
            7, "2026-11-04T12:00:00Z", erstellt="2026-11-01T12:00:00Z")], JETZT)
        self.assertEqual((liegend[0]["ruhe_tage"], liegend[0]["alter_tage"]),
                         (10, 13))

    def test_ausgabe_nennt_keine_fremden_texte(self):
        # Titel und Zweigname sind fremder Text (CLAUDE.md): Sie werden gar
        # nicht erst gelesen, also können sie in keinem Ticket landen.
        self.assertNotIn("title", pbw.FELDER)
        self.assertNotIn("headRefName", pbw.FELDER)
        self.assertNotIn("body", pbw.FELDER)

    def test_bestand_vom_14_november(self):
        # Die vier, die den Anlass gaben (Stand 14.11.2026, 12:00 UTC).
        lauf = antwort([
            vorschlag(1217, "2026-11-14T08:00:00Z"),
            vorschlag(1174, "2026-11-11T07:10:00Z"),
            vorschlag(1173, "2026-11-11T06:50:00Z", mergeable="CONFLICTING"),
            vorschlag(1171, "2026-11-10T22:00:00Z"),
            vorschlag(1167, "2026-11-10T20:00:00Z"),
        ])
        messung = pbw.messe(JETZT, lauf)
        self.assertEqual(messung["offen"], 5)
        self.assertEqual([e["nummer"] for e in messung["liegend"]],
                         [1167, 1171, 1173, 1174])
        self.assertIn("4 von 5", messung["kurztext"])
        self.assertIn("Konflikt", pbw.zeile(messung["liegend"][2]))


class KeinStillesGruen(unittest.TestCase):
    def test_fehlendes_leserecht_ist_nicht_messbar(self):
        with self.assertRaises(pbw.NichtMessbar):
            pbw.messe(JETZT, antwort([], rc=1, stderr="HTTP 403: Resource "
                                                      "not accessible by integration"))

    def test_fehlende_cli_ist_nicht_messbar(self):
        def lauf(*_a, **_kw):
            raise FileNotFoundError("gh")
        with self.assertRaises(pbw.NichtMessbar):
            pbw.messe(JETZT, lauf)

    def test_zeitueberschreitung_ist_nicht_messbar(self):
        def lauf(argv, **_kw):
            raise subprocess.TimeoutExpired(argv, 60)
        with self.assertRaises(pbw.NichtMessbar):
            pbw.messe(JETZT, lauf)

    def test_unlesbare_antwort_ist_nicht_messbar(self):
        for kaputt in ("", "nicht json", "{}", '[{"number": 1}]',
                       '[{"number": 1, "updatedAt": "gestern", "createdAt": "x"}]'):
            def lauf(_argv, _text=kaputt, **_kw):
                return types.SimpleNamespace(returncode=0, stderr="", stdout=_text)
            with self.subTest(antwort=kaputt), self.assertRaises(pbw.NichtMessbar):
                pbw.messe(JETZT, lauf)

    def test_volle_seite_ist_nicht_messbar(self):
        voll = [vorschlag(n, "2026-11-14T08:00:00Z")
                for n in range(1, pbw.LESE_GRENZE + 1)]
        with self.assertRaises(pbw.NichtMessbar):
            pbw.messe(JETZT, antwort(voll))
        # Eine Seite darunter ist vollständig gelesen.
        self.assertEqual(pbw.messe(JETZT, antwort(voll[:-1]))["liegend"], [])

    def test_exit_codes_trennen_gruen_befund_blind(self):
        hier = {"cwd": ROOT, "capture_output": True, "text": True, "timeout": 60}
        ohne_cli = dict(os.environ, PATH="/nonexistent")
        lauf = subprocess.run([sys.executable, "scripts/pr_bestand_wache.py"],
                              env=ohne_cli, check=False, **hier)
        self.assertEqual(lauf.returncode, 2, lauf.stdout + lauf.stderr)
        self.assertNotIn("✅", lauf.stdout)


class Besitz(unittest.TestCase):
    LIEGT = {"kurztext": "1 von 2 offenen seit 3 Tagen oder länger ohne "
                         "Bewegung, ältester Stillstand 5 Tage (#7)",
             "liegend": [{"nummer": 7, "ruhe_tage": 5, "alter_tage": 9,
                          "entwurf": False, "konflikt": True,
                          "maschinell": False}]}

    def test_befund_hat_menschlichen_besitzer_und_naechsten_schritt(self):
        befund, text = bw.check_pr_bestand(lambda: self.LIEGT)
        self.assertEqual((befund.id, befund.owner, befund.severity),
                         ("pr-bestand", "human", "P3"))
        self.assertFalse(befund.akut)
        self.assertTrue(befund.next_step)
        self.assertEqual(len(befund.evidence), 1)
        self.assertIn("#7", befund.evidence[0])
        self.assertTrue(text.startswith("HUMAN ("))

    def test_ohne_liegenden_vorschlag_kein_befund(self):
        befund, text = bw.check_pr_bestand(
            lambda: {"kurztext": "1 offen, keiner …", "liegend": []})
        self.assertIsNone(befund)
        self.assertTrue(text.startswith("OK ("))

    def test_nicht_messbar_ist_weder_befund_noch_gruen(self):
        def blind():
            raise pbw.NichtMessbar("GitHub-CLI Exit 1: HTTP 403")
        befund, text = bw.check_pr_bestand(blind)
        self.assertIsNone(befund)
        self.assertTrue(text.startswith("UNKNOWN"))
        for wort in ("OK", "WARN", "FAIL"):
            self.assertNotIn(wort, text)

    def test_befund_geht_nicht_ins_automations_ticket(self):
        befund, _text = bw.check_pr_bestand(lambda: self.LIEGT)
        maschine, mensch = bw.split_findings([befund])
        self.assertEqual((len(maschine), len(mensch)), (0, 1))


class NurLesen(unittest.TestCase):
    def test_aufruf_liest_nur(self):
        lauf = antwort([])
        pbw.messe(JETZT, lauf)
        self.assertEqual(len(lauf.aufrufe), 1)
        argv = lauf.aufrufe[0]
        self.assertEqual(argv[:5], ["gh", "pr", "list", "--state", "open"])
        for verb in ("close", "merge", "comment", "edit", "review", "ready"):
            self.assertNotIn(verb, argv)

    def test_quelltext_kennt_kein_schreibendes_gh_kommando(self):
        with open(os.path.join(SCRIPTS, "pr_bestand_wache.py"), encoding="utf-8") as f:
            quelle = f.read()
        for verb in ('"close"', '"merge"', '"comment"', '"edit"', '"review"'):
            self.assertNotIn(verb, quelle)

    def test_workflow_gibt_nur_das_leserecht(self):
        with open(os.path.join(ROOT, ".github", "workflows", "bot-watchdog.yml"),
                  encoding="utf-8") as f:
            text = f.read()
        rechte = yaml.safe_load(text)["permissions"]
        self.assertEqual(rechte.get("pull-requests"), "read")
        self.assertIn("scripts/pr_bestand_wache.py --selftest", text)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(pbw.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
