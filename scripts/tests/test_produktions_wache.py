#!/usr/bin/env python3
# ============================================================
#  PRODUKTIONS-WACHE (#1054): Der verzögerte Plan-Lauf darf
#  keinen falschen P1-Alarm auf den Folgetag legen.
#  Belegt die reine Bewertung + die Verdrahtung im Workflow:
#  Der Workflow darf die Bewertung nicht wieder als Heredoc
#  kopieren (eine Logik, ein Wahrheitsort), und die C23-Anker
#  (Cron, WARTEND-Bedingung, Fachkanal-Beleg) bleiben stehen.
# ============================================================
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import produktions_wache as pw  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
MI = datetime.date(2026, 11, 4)
MO = datetime.date(2026, 11, 2)


def _bew(heute, h, m, **kw):
    jetzt = datetime.datetime(heute.year, heute.month, heute.day, h, m,
                              tzinfo=datetime.timezone.utc)
    basis = dict(heute=heute, jetzt_utc=jetzt, ist_pubtag=True,
                 anzahl_heute=0, anzahl_letzter=2, letzter_pubtag=MO,
                 minimum=2, modus="schedule", engine_conclusion="")
    basis.update(kw)
    return pw.bewertung(**basis)


class BewertungTest(unittest.TestCase):
    def test_rollover_um_0032_bleibt_wartend(self):
        stufe, meldung = _bew(MI, 0, 32)
        self.assertEqual("WARTEND", stufe)
        self.assertNotIn("alle Slots vorbei", meldung)

    def test_nach_letztem_slot_ist_p1(self):
        stufe, _ = _bew(MI, 19, 0)
        self.assertEqual("P1", stufe)

    def test_engine_failure_ist_sofort_p1(self):
        stufe, _ = _bew(MI, 7, 0, modus="workflow_run",
                        engine_conclusion="failure")
        self.assertEqual("P1", stufe)

    def test_unter_mindestziel_ist_p2(self):
        stufe, _ = _bew(MI, 19, 0, anzahl_heute=1, anzahl_letzter=1,
                        letzter_pubtag=MI)
        self.assertEqual("P2", stufe)

    def test_ziel_erfuellt_ist_ok(self):
        stufe, _ = _bew(MI, 19, 0, anzahl_heute=2, anzahl_letzter=2,
                        letzter_pubtag=MI)
        self.assertEqual("OK", stufe)

    def test_selbsttest_gruen(self):
        self.assertEqual(0, pw.selftest())


class WorkflowVerdrahtungTest(unittest.TestCase):
    def test_workflow_ruft_modul_auf_und_haelt_c23_anker(self):
        with open(os.path.join(ROOT, ".github", "workflows",
                               "produktions-wache.yml"),
                  encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("import produktions_wache as pw", text)
        self.assertIn('cron: "0 20 * * *"', text)
        self.assertIn("steps.check.outputs.level != 'WARTEND'", text)
        self.assertIn("engine_issue.py --deficit", text)
        self.assertNotIn("alle Slots vorbei, **0 Artikel** erschienen \"\n"
                         "                             f\"(Ziel:", text)


if __name__ == "__main__":
    unittest.main()
