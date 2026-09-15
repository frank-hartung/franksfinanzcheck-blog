#!/usr/bin/env python3
"""Regressionstests für die Frische der Affiliate-Integritäts-Wache (#281).

Der P1-Fehlalarm aus Ticket #281 lautete: „Integritäts-Wache schweigt:
State 64 h alt (> 30 h)" – obwohl die Wache jeden Tag fehlerfrei lief.
Ursache war ein Konstruktionswiderspruch:

    · Das Gate schrieb Zustand und Report „konvergent" – bei unverändertem
      Befund wurde KEINE Datei angefasst, `generated_at` fror ein.
    · Der Watchdog las genau diesen Zeitstempel als LEBENSZEICHEN.

Ein Befund-Zeitstempel ist kein Lebenszeichen. Diese Tests frieren beide
Seiten der dauerhaften Behebung ein:

    1) HERZSCHLAG  – jeder Lauf erneuert den Zeitstempel (Report + Zustand),
       `verdict_changed` trennt Lage von Lebenszeichen.
    2) WATCHDOG    – Befund aus dem Zustand, Frische per Herzschlag ODER
       fehlerfreiem Lauf; ein ausgebliebener Push ist ein Hinweis, kein
       P1-Ausfall – und eine wirklich schweigende Wache bleibt sichtbar.

Deterministisch ohne Netz: alle Zeitangaben sind relativ zu now(), alle
Pfade liegen in temporären Verzeichnissen (kein Test schreibt ins Repo).
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

import affiliate_integrity_gate as gate  # noqa: E402
import bot_watchdog as bw  # noqa: E402

# Zeit-Anker relativ zur echten Uhr (Lehre vom 14.09.2026: absolute
# Datumsangaben in Fixtures werden zu Zeitbomben).
NOW = datetime.datetime.now(datetime.timezone.utc)


def _stamp(hours_ago: float) -> str:
    return (NOW - datetime.timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S UTC")


def _result(generated_at: str, exit_code: int = 0, problems: dict | None = None,
            errors: list | None = None) -> dict:
    """Minimaler Ergebnisdatensatz, wie ihn gate.run() liefert."""
    findings = problems if problems is not None else {}
    return {
        "generated_at": generated_at,
        "checked": 32,
        "findings": findings,
        "render_problems": {},
        "healed": [],
        "healed_count": 0,
        "per_article": [],
        "build": {"built": True, "reason": "public/ frisch", "ok": True},
        "registry_routes": 19,
        "errors": list(errors or []),
        "exit_code": exit_code,
    }


class HerzschlagTestCase(unittest.TestCase):
    """Seite 1: Der Herzschlag (Gate) darf nie wieder einfrieren."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.alt_state, self.alt_report = gate.STATE, gate.REPORT
        gate.STATE = self.tmp / ".affiliate_integrity_state.json"
        gate.REPORT = self.tmp / "AFFILIATE-INTEGRITY-REPORT.md"

    def tearDown(self):
        gate.STATE, gate.REPORT = self.alt_state, self.alt_report
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zweiter_lauf_mit_gleichem_befund_erneuert_den_herzschlag(self):
        """Der Kern von #281: ruhiger Tag = frischer Zeitstempel, gleiche Lage."""
        first = _result(_stamp(24))
        gate.write_report(first)
        gate.write_state(first)
        self.assertIs(first["verdict_changed"], True,
                      "der erste Befund muss als Lageänderung gelten")

        second = _result(_stamp(0))
        gate.write_report(second)
        gate.write_state(second)

        written = json.loads(gate.STATE.read_text(encoding="utf-8"))
        self.assertEqual(second["verdict_changed"], False,
                         "gleicher Befund darf NICHT als Lageänderung gelten")
        self.assertEqual(written["generated_at"], _stamp(0),
                         "DER HERZSCHLAG MUSS SICH ERNEUERN – genau das tat er in "
                         "#281 nicht, und der Watchdog meldete einen stillen Ausfall")
        self.assertEqual(written["exit_code"], 0)
        self.assertEqual(written["checked"], 32)

    def test_report_stand_ist_frisch_und_lage_unveraendert(self):
        first = _result(_stamp(24))
        gate.write_report(first)
        second = _result(_stamp(0))
        gate.write_report(second)
        self.assertIs(second["report_changed"], False,
                      "am ruhigen Tag darf sich nur der Report-Stand erneuern")
        report = gate.REPORT.read_text(encoding="utf-8")
        self.assertIn(f"**Stand:** {_stamp(0)}", report,
                      "der Report-Stand ist das Lebenszeichen für Menschen")

    def test_geaenderter_befund_gilt_als_lageaenderung(self):
        gate.write_state(_result(_stamp(24)))
        broken = _result(_stamp(0), exit_code=1,
                         problems={"2026-08-10-test": {"problems": ["CTA kaputt"],
                                                       "healed": []}})
        gate.write_state(broken)
        written = json.loads(gate.STATE.read_text(encoding="utf-8"))
        self.assertIs(broken["verdict_changed"], True,
                      "ein offener Fund muss als Lageänderung gelten")
        self.assertEqual(written["content_problems"], ["2026-08-10-test"])

    def test_verdict_changed_verfaelscht_die_lage_nicht(self):
        """`verdict_changed` ist ein Lebenszeichen-Feld – die Lage selbst zählt."""
        first = _result(_stamp(24))
        gate.write_state(first)
        gate.write_state(_result(_stamp(0)))
        third = _result(_stamp(-1))  # „Zukunft" = wieder ein neuer Lauf
        gate.write_state(third)
        written = json.loads(gate.STATE.read_text(encoding="utf-8"))
        self.assertEqual(written["content_problems"], [])
        self.assertEqual(written["exit_code"], 0)


class WatchdogFrischeTestCase(unittest.TestCase):
    """Seite 2: Der Watchdog liest Befund und Frische getrennt."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.alt_dir = bw.BLOG_DIR
        self.alt_evidence = bw.workflow_run_evidence
        bw.BLOG_DIR = self.tmp
        self.state = self.tmp / ".affiliate_integrity_state.json"

    def tearDown(self):
        bw.BLOG_DIR = self.alt_dir
        bw.workflow_run_evidence = self.alt_evidence
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _state(self, hours_ago: float, exit_code: int = 0, problems=(),
               errors=()) -> None:
        self.state.write_text(json.dumps({
            "generated_at": _stamp(hours_ago),
            "verdict_changed": False,
            "exit_code": exit_code,
            "checked": 32,
            "healed": [],
            "healed_count": 0,
            "content_problems": list(problems),
            "errors": list(errors),
            "build": {"built": True, "reason": "public/ frisch", "ok": True},
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def _evidence(self, total: int, success: int, running: int = 0) -> None:
        bw.workflow_run_evidence = (
            lambda workflow_file, hours=30: (total, success, running, ""))

    def _evidence_offline(self) -> None:
        bw.workflow_run_evidence = (
            lambda workflow_file, hours=30: (None, None, None, "gh Fehler: offline"))

    def test_frischer_gruener_zustand_ist_ok(self):
        self._state(6)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, True)
        self.assertIn("Herzschlag", msg)

    def test_roter_befund_gilt_unabhaengig_vom_alter(self):
        self._state(1, problems=["slug-a", "slug-b"])
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, False)
        self.assertIn("2 offene Affiliate-Probleme", msg)

    def test_werkzeugfehler_im_zustand_ist_rot(self):
        self._state(2, exit_code=2, errors=["kein public/ – fail-closed"])
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, False)
        self.assertIn("exit 2", msg)

    def test_alter_herzschlag_mit_fehlerfreiem_lauf_ist_kein_p1(self):
        """Genau der #281-Fall: Push ausgeblieben, Wache lebt → Hinweis, kein Alarm."""
        self._state(40)
        self._evidence(total=2, success=2)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, None,
                      "ein einzelner ausgebliebener Zustands-Push darf keinen "
                      "P1-Fehlalarm auslösen (#281)")
        self.assertIn("Beweis über den Lauf", msg)

    def test_dauerhaft_fehlender_nachweis_wird_gemeldet(self):
        self._state(60)
        self._evidence(total=3, success=3)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, False)
        self.assertIn("Nachweis landet nicht im Repo", msg)

    def test_schweigende_wache_bleibt_sichtbar(self):
        self._state(40)
        self._evidence(total=0, success=0)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, False)
        self.assertIn("schweigt", msg)

    def test_nur_rote_laeufe_sind_kein_gruen(self):
        """C2: eine nicht ausgeführte Messung ist kein Grün."""
        self._state(40)
        self._evidence(total=3, success=0)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, False)
        self.assertIn("keiner fehlerfrei", msg)

    def test_ohne_gh_kein_falscher_befund(self):
        """Offline ist kein Ausfall – der Check darf nur warnen."""
        self._state(40)
        self._evidence_offline()
        ok, _ = bw.check_affiliate_integrity()
        self.assertIs(ok, None)

    def test_unlesbarer_zeitstempel_wird_ueber_den_lauf_bewertet(self):
        """Ein kaputter Zeitstempel darf den Befund nicht mitreißen."""
        self.state.write_text(json.dumps({
            "generated_at": "irgendwann",
            "exit_code": 0, "checked": 32, "healed": [], "healed_count": 0,
            "content_problems": [], "errors": [],
            "build": {"built": True, "reason": "x", "ok": True},
        }) + "\n", encoding="utf-8")
        self._evidence(total=1, success=1)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, None, "unlesbares Alter ist ein Hinweis, kein P1-Befund")
        self.assertIn("unlesbar", msg)

    def test_laufende_wache_wartet(self):
        self._state(40)
        self._evidence(total=1, success=0, running=1)
        ok, msg = bw.check_affiliate_integrity()
        self.assertIs(ok, None)
        self.assertIn("läuft gerade", msg)

    def test_fehlerfreie_laeufe_zaehlen_auch_ohne_das_created_flag(self):
        """`workflow_run_evidence` filtert im Python-Code (gh 2.23 ohne --created)."""
        rows = json.dumps([
            {"createdAt": (NOW - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "status": "completed", "conclusion": "success"},
            {"createdAt": (NOW - datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "status": "completed", "conclusion": "failure"},
            {"createdAt": (NOW - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "status": "in_progress", "conclusion": ""},
            {"createdAt": (NOW - datetime.timedelta(hours=400)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "status": "completed", "conclusion": "success"},
        ])
        alt_run = bw.run_cmd
        bw.run_cmd = lambda cmd, timeout=25: (0, rows, "")
        try:
            total, success, running, err = bw.workflow_run_evidence("x.yml", hours=30)
        finally:
            bw.run_cmd = alt_run
        self.assertEqual((total, success, running, err), (3, 1, 1, ""),
                         "alter Lauf außerhalb des Fensters darf nicht mitzählen")
        self.assertNotIn("--created", "x")  # Dokumentation: Flag wird nicht genutzt


if __name__ == "__main__":
    unittest.main()
