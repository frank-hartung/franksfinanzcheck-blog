#!/usr/bin/env python3
"""Regressionstests: Der Watchdog darf sich nicht selbst blenden (#864).

WARUM (25.10.2026)
------------------
Am 25.10.2026 stand `scripts/redaktions_standard.py` mit einem
IndentationError auf `main`. Der Watchdog SAH das – und tötete sich
daran: Sein Selbsttest verlangte ein syntaxgrünes Repo, der
Workflow-Schritt „Selftest (Wache muss sehen können)" starb, und damit
standen ALLE folgenden Schritte auf `skipped`: keine Nachmessung, keine
Reserve-Heilung, kein Alarm-Routing, und am Ende ein roter Lauf ohne
einen einzigen Bericht. Das Ticket entstand nur, weil der Routing-Schritt
`always()` läuft und selbst nachgemessen hat.

Der Vertrag, den diese Tests festhalten:

  1. Ein fremder Syntaxfehler ist ein BEFUND (Check 2) – kein
     Werkzeugfehler. Der Selbsttest bleibt grün.
  2. Ein blinder Detektor ist ein WERKZEUGFEHLER – der Selbsttest wird
     rot (Exit 2), denn dann ist keine Aussage möglich.
  3. Der Befund nennt Datei, Zeile und Herkunft und den maschinellen
     Heilweg – er ist nicht länger eine Arbeitsanweisung an den Menschen.
  4. Die Verdrahtung bleibt: Selbstheilung im Lauf, Syntax-Wache im
     Push-Lauf, Notbremse im gemeinsamen Push-Weg.

Lauf: python3 -m unittest scripts.tests.test_bot_watchdog_syntax_sicht
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import yaml

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "scripts"))

import bot_watchdog as bw  # noqa: E402


class FremderFund:
    """Steht für einen Befund der Syntax-Wache (Datei, Zeile, Art)."""

    datei = "scripts/redaktions_standard.py"
    zeile = 424
    art = "IndentationError: unexpected indent"
    quelle = "        r\"\\b(?:rechenbeispiel…"

    def text(self) -> str:
        return f"{self.datei}:{self.zeile}: {self.art}"


class SelbsttestSichtTests(unittest.TestCase):
    """Befund ≠ Werkzeugfehler."""

    def test_fremder_syntaxfehler_kippt_den_selbsttest_nicht(self):
        """Der Kernfall von #864: Das Repo ist rot, die Wache ist es nicht."""
        with mock.patch.object(bw, "syntax_fehler", return_value=[FremderFund()]), \
             mock.patch.object(bw, "syntax_detektor_sichtbar", return_value=(True, "")):
            self.assertEqual(0, bw.selftest(),
                             "ein fremder Syntaxfehler hat den Watchdog abgeschaltet")

    def test_blinder_detektor_ist_ein_werkzeugfehler(self):
        with mock.patch.object(bw, "syntax_fehler", return_value=[]), \
             mock.patch.object(bw, "syntax_detektor_sichtbar",
                               return_value=(False, "Detektor übersieht Fehler")):
            self.assertEqual(2, bw.selftest())

    def test_detektorprobe_erkennt_wirklich(self):
        sichtbar, grund = bw.syntax_detektor_sichtbar()
        self.assertTrue(sichtbar, grund)

    def test_syntaxmessung_meldet_heutigen_stand(self):
        ok, meldung = bw.check_syntax()
        self.assertTrue(ok, meldung)
        self.assertEqual("", meldung)


class BefundTests(unittest.TestCase):
    """Der Befund trägt Ort, Herkunft und den maschinellen Heilweg."""

    def _run(self):
        with mock.patch.object(bw, "check_workflow_liveness", return_value=(3, "")), \
             mock.patch.object(bw, "check_syntax",
                               return_value=(False, "scripts/x.py:424: IndentationError: x")), \
             mock.patch.object(bw, "syntax_fehler", return_value=[FremderFund()]), \
             mock.patch.object(bw, "deploy_blockade",
                               return_value=("ausgeliefert", "", "Beleg")), \
             mock.patch.object(bw, "newest_slug", return_value=("slug", None)), \
             mock.patch.object(bw, "check_live_site", return_value=(True, "200")):
            return bw.run_all(triage=True)

    def test_befund_ist_maschinenbesitz_mit_heilweg(self):
        env, befunde, _slug = self._run()
        self.assertEqual("FAIL", env["CHECK2"])
        syntax = [f for f in befunde if f.id == "skript-syntax"]
        self.assertEqual(1, len(syntax))
        befund = syntax[0]
        self.assertEqual("auto", befund.owner,
                         "ein Befund ohne Heilweg darf nicht als Maschinenbesitz gelten")
        self.assertIn("skript_syntax_heiler.py", befund.next_step)
        self.assertIn("skript_syntax_heilungen.jsonl", befund.next_step)
        self.assertTrue(any("scripts/redaktions_standard.py" in e
                            for e in befund.evidence), befund.evidence)

    def test_befund_nennt_datei_und_zeile(self):
        _env, befunde, _slug = self._run()
        befund = [f for f in befunde if f.id == "skript-syntax"][0]
        self.assertIn("scripts/x.py:424", befund.detail)


class VerdrahtungTests(unittest.TestCase):
    """Ein Vertrag ohne Lauf ist Prosa – die Verdrahtung wird mitgeprüft."""

    def setUp(self):
        self.watchdog = WURZEL / ".github" / "workflows" / "bot-watchdog.yml"
        self.daten = yaml.safe_load(self.watchdog.read_text(encoding="utf-8"))
        self.schritte = self.daten["jobs"]["watchdog"]["steps"]

    def _schritt(self, name_teil: str) -> dict:
        for schritt in self.schritte:
            if name_teil in (schritt.get("name") or ""):
                return schritt
        self.fail(f"Workflow-Schritt fehlt: {name_teil!r}")

    def test_selbstheilung_laeuft_in_beiden_takten(self):
        schritt = self._schritt("Skript-Syntax heilen")
        assert "run" in schritt
        self.assertIn("skript_syntax_heiler.py", schritt["run"])
        self.assertIn("--commit", schritt["run"])
        # Kein Takt-Filter: Die Ausfall-Klasse muss auch im Stunden-Takt
        # heilbar sein – sonst misst der Takt, was er nicht heilen darf.
        self.assertNotIn("takt.outputs.modus", str(schritt.get("if", "")))
        self.assertTrue(schritt.get("continue-on-error"),
                        "eine misslungene Heilung darf den Melder nicht röten")

    def test_selbsttest_toetet_den_lauf_nicht_mehr(self):
        schritt = self._schritt("Selftest (Wache muss sehen")
        lauf = schritt["run"]
        # Jeder Selbsttest einzeln, kein Abbruch beim ersten Fehler …
        self.assertIn("set +e", lauf)
        self.assertIn("skript_syntax_wache.py --selftest", lauf)
        self.assertIn("skript_syntax_heiler.py --selftest", lauf)
        self.assertNotIn("set -euo pipefail", lauf)
        # … und der Messkern wird VORHER geprüft (dann ist keine Aussage möglich).
        self.assertLess(lauf.index("py_compile scripts/bot_watchdog.py"),
                        lauf.index("--selftest"),
                        "der Messkern wird erst nach den Selbsttests geprüft")

    def test_roter_lauf_erst_nach_der_meldung(self):
        namen = [s.get("name") or "" for s in self.schritte]
        bilanz = next((s for s in self.schritte
                       if "Selbsttest-Bilanz" in (s.get("name") or "")), None)
        self.assertIsNotNone(bilanz, f"kein Bilanz-Schritt in {namen}")
        self.assertIn("always()", str(bilanz.get("if")))
        position = namen.index(bilanz["name"])
        routing = next(i for i, n in enumerate(namen) if "Alarm-Routing" in n)
        self.assertLess(routing, position,
                        "der rote Lauf darf erst NACH dem Alarm-Routing entstehen")

    def test_syntax_wache_laeuft_im_push_und_pr_lauf(self):
        pfad = WURZEL / ".github" / "workflows" / "skript-syntax.yml"
        self.assertTrue(pfad.is_file(), "Push-Lauf für die Skript-Syntax fehlt")
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        trigger = daten.get("on", daten.get(True)) or {}
        self.assertIn("pull_request", trigger, "PRs werden nicht geprüft")
        self.assertIn("push", trigger, "Pushes auf main werden nicht geprüft")
        self.assertIn("permissions", daten)
        self.assertIn("concurrency", daten)
        text = pfad.read_text(encoding="utf-8")
        self.assertIn("skript_syntax_wache.py", text)
        self.assertIn("--check", text)

    def test_gemeinsamer_push_weg_hat_eine_notbremse(self):
        git_sync = (WURZEL / "scripts" / "git_sync.sh").read_text(encoding="utf-8")
        self.assertIn("syntax_notbremse", git_sync,
                      "git_sync.sh prüft die Skripte nicht vor dem Push")

    def test_wachen_vertrag_kennt_beide_neuen_skripte(self):
        sys.path.insert(0, str(WURZEL / "scripts"))
        import governance_contract as gc
        self.assertIn("skript_syntax_wache.py", gc.GUARDS)
        self.assertIn("skript_syntax_heiler.py", gc.GUARDS)


if __name__ == "__main__":
    unittest.main()
