#!/usr/bin/env python3
"""Tests für die Befund-Klassifikation des Bot-Watchdogs (Issue #272).

Der Watchdog darf einen Befund, den nur ein Mensch heilen kann, nicht
länger als „Problem mit der Content-Automatisierung" melden. Diese Tests
halten fest, wie der Pinterest-Kanal bewertet wird – inklusive der
Reihenfolge, die der Betrieb wirklich braucht:

    Domain gesperrt → Token-Neu-Autorisierung lohnt NICHT vorher.

Läuft deterministisch ohne Netz: der Prüfpfad wird auf ein temporäres
`data/`-Verzeichnis umgebogen.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import alert_router as ar  # noqa: E402
import bot_watchdog as bw  # noqa: E402

NOW = datetime.datetime(2026, 9, 12, 12, 0, tzinfo=datetime.timezone.utc)
FRISCH = (NOW - datetime.timedelta(hours=2)).isoformat()


def _state(state="dead", severity="red", checked_at=FRISCH, renewable=False,
           detail="Pinterest lehnt den Token ab (HTTP 401)", source="keine"):
    return {
        "state": state, "severity": severity, "checked_at": checked_at,
        "renewable": renewable, "detail": detail, "source_label": source,
        "next_action": "Einmalige Neu-Autorisierung nötig.",
    }


class WatchdogKanalTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        self.alt = bw.BLOG_DIR
        bw.BLOG_DIR = self.tmp

    def tearDown(self):
        bw.BLOG_DIR = self.alt
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, data):
        (self.tmp / "data" / name).write_text(json.dumps(data), encoding="utf-8")

    # --- Reihenfolge: erst die Domain, dann der Token ------------------- #
    def test_token_rot_bei_domainsperre_ist_ein_hinweis(self):
        self._write("pinterest_token_state.json", _state())
        self._write("pinterest_domain_block.json",
                    {"since": "2026-08-27T13:58:16Z",
                     "reason": "Pinterest hat die Domain gesperrt (Spam-Markierung).",
                     "policy": "Keine Pins bis zur Freigabe."})
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 2)
        for f in findings:
            self.assertEqual(f.owner, "human", f.id)
            self.assertEqual(f.channel, bw.PINTEREST_PARKED_CHANNEL, f.id)
            self.assertEqual(f.severity, "P3", f.id)
        self.assertIn("geparkt", text)
        # Wichtig: kein Automations-Ticket, und ein offenes geht zu.
        self.assertEqual(ar.plan_generic(findings, None, NOW).action, "none")
        offen = ar.IssueRef(number=272, created_at=NOW - datetime.timedelta(days=1))
        self.assertEqual(ar.plan_generic(findings, offen, NOW).action, "close")

    def test_token_rot_ohne_sperre_geht_ins_fach_ticket(self):
        self._write("pinterest_token_state.json", _state())
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual((f.owner, f.channel, f.severity),
                         ("human", bw.PINTEREST_TOKEN_CHANNEL, "P2"))
        self.assertIn("Runbook", f.next_step)
        self.assertEqual(ar.plan_generic(findings, None, NOW).action, "none")

    def test_ablaufender_token_mit_refresh_bleibt_maschinell(self):
        self._write("pinterest_token_state.json",
                    _state(state="expiring", severity="amber", renewable=True))
        findings, _ = bw.check_pinterest_channel()
        self.assertEqual(findings[0].owner, "auto")
        # maschinell ⇒ darf das Automations-Ticket öffnen
        self.assertEqual(ar.plan_generic(findings, None, NOW).action, "create")

    def test_ablaufender_token_ohne_refresh_braucht_menschen(self):
        self._write("pinterest_token_state.json",
                    _state(state="expiring", severity="amber", renewable=False))
        findings, _ = bw.check_pinterest_channel()
        self.assertEqual(findings[0].owner, "human")

    # --- Die Wache selbst ------------------------------------------------ #
    def test_veraltetes_lagebild_ist_ein_maschinen_befund(self):
        self._write("pinterest_token_state.json",
                    _state(checked_at=(NOW - datetime.timedelta(days=5)).isoformat()))
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].owner, "auto")
        self.assertEqual(findings[0].channel, ar.GENERIC_CHANNEL)
        self.assertIn("alt", text)

    def test_fehlendes_lagebild_ist_ein_maschinen_befund(self):
        findings, _ = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].owner, "auto")

    def test_gruener_token_meldet_nichts(self):
        self._write("pinterest_token_state.json",
                    _state(state="live", severity="green", detail="", source="store"))
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(findings, [])
        self.assertIn("OK", text)

    # --- Trennschärfe ---------------------------------------------------- #
    def test_split_findings_trennt_nach_besitzer(self):
        mensch = bw._f("pinterest-token", "Token tot", owner="human",
                       channel=bw.PINTEREST_TOKEN_CHANNEL)
        maschine = bw._f("cadence", "Kadenz", severity="P1", owner="auto")
        m, h = bw.split_findings([mensch, maschine])
        self.assertEqual([f.id for f in m], ["cadence"])
        self.assertEqual([f.id for f in h], ["pinterest-token"])

    def test_domainsperre_wird_erkannt(self):
        self.assertIsNone(bw.pinterest_domain_block())
        self._write("pinterest_domain_block.json", {"since": "2026-08-27T13:58:16Z"})
        self.assertIsNotNone(bw.pinterest_domain_block())


if __name__ == "__main__":
    unittest.main(verbosity=2)
