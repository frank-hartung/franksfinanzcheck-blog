#!/usr/bin/env python3
"""Vertragstests: Trigger-Trennung, Deploy-Beweis und ehrliche Ampel.

Alle Tests laufen offline. Die Verdrahtung wird am ECHTEN Workflow-Text
geprüft (nicht an einer Kopie), die Entscheidungen am echten Modul.
WF-829B / #922, 10.11.2026.
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_deploy_abschluss as abschluss  # noqa: E402
import produktions_schutz_selbstheilung as pss  # noqa: E402

DEPLOY = ROOT / ".github" / "workflows" / "worker-deploy.yml"
HEILUNG = ROOT / ".github" / "workflows" / "produktions-schutz-selbstheilung.yml"


def _laden(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


def _job(text: str, name: str) -> str:
    """Job-Block über Einrückung lesen, ohne PyYAML (wie die Haus-Wachen)."""
    zeilen = text.splitlines()
    start = next((i for i, z in enumerate(zeilen)
                  if z.startswith("  " + name + ":")), None)
    if start is None:
        return ""
    aus = [zeilen[start]]
    for zeile in zeilen[start + 1:]:
        if zeile.strip() and not zeile.startswith("    "):
            break
        aus.append(zeile)
    return "\n".join(aus)


def _trigger_pfade(text: str, ereignis: str) -> list[str]:
    zeilen = text.splitlines()
    block = ""
    im_block = False
    for zeile in zeilen:
        if zeile.startswith("  " + ereignis + ":"):
            im_block = True
            continue
        if im_block:
            if zeile.strip() and not zeile.startswith("    ") and not zeile.startswith("      "):
                break
            block += zeile + "\n"
    return [z.strip()[2:].strip().strip('"')
            for z in block.splitlines()
            if z.strip().startswith("- ") and z.strip().count("\"") >= 2]


class EntscheidungsTests(unittest.TestCase):
    def lage(self, **kwargs):
        lage = {
            "EREIGNIS": "workflow_dispatch", "REF": "refs/heads/main",
            "GEPLANT": '["newsletter-worker"]', "ERGEBNIS_PLAN": "success",
            "ERGEBNIS_TESTS": "success", "ERGEBNIS_POLICY": "success",
            "ERGEBNIS_DEPLOY": "success",
        }
        lage.update(kwargs)
        return lage

    def test_01_echter_deploy_ist_gruen(self):
        self.assertEqual(abschluss.entscheiden(self.lage())["code"], 0)

    def test_02_test_push_ist_gruen_ohne_deploy(self):
        lage = self.lage(EREIGNIS="push", GEPLANT="[]", ERGEBNIS_PLAN="skipped",
                         ERGEBNIS_TESTS="success", ERGEBNIS_POLICY="skipped",
                         ERGEBNIS_DEPLOY="skipped")
        urteil = abschluss.entscheiden(lage)
        self.assertEqual(urteil["code"], 0)
        self.assertIn("Kein Deploy", urteil["titel"])

    def test_03_jeder_skip_ist_rot_und_genannt(self):
        for feld in ("ERGEBNIS_TESTS", "ERGEBNIS_PLAN", "ERGEBNIS_POLICY", "ERGEBNIS_DEPLOY"):
            with self.subTest(feld=feld):
                urteil = abschluss.entscheiden(self.lage(**{feld: "skipped"}))
                self.assertEqual(urteil["code"], 1)
                self.assertTrue(any("`" in text for text in urteil["befunde"]))

    def test_04_push_mit_deploy_ist_harter_bruch(self):
        lage = self.lage(EREIGNIS="push", GEPLANT="[]", ERGEBNIS_PLAN="skipped",
                         ERGEBNIS_TESTS="success", ERGEBNIS_POLICY="skipped",
                         ERGEBNIS_DEPLOY="success")
        urteil = abschluss.entscheiden(lage)
        self.assertEqual(urteil["code"], 1)
        self.assertIn("ausschließlich", " ".join(urteil["befunde"]))

    def test_05_unbelegbare_lage_wird_nie_gruen(self):
        for aenderung in ({"GEPLANT": "kein json"}, {"EREIGNIS": "schedule"},
                          {"REF": ""}, {"ERGEBNIS_DEPLOY": ""}):
            with self.subTest(aenderung=aenderung):
                with self.assertRaises(abschluss.WerkzeugFehler):
                    abschluss.entscheiden(self.lage(**aenderung))

    def test_06_selftest_und_cli_sind_maschinell_lesbar(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(abschluss._selftest(), 0)
        lage = self.lage()
        with patch.dict(os.environ, lage, clear=True):
            with redirect_stdout(io.StringIO()) as ausgabe:
                code = abschluss.main(["--pruefen", "--json"])
        self.assertEqual(code, 0)
        zeilen = [z for z in ausgabe.getvalue().splitlines() if z.startswith("{")]
        self.assertEqual(json.loads(zeilen[0])["code"], 0)

    def test_07_urteil_ist_serialisierbar(self):
        urteil = abschluss.entscheiden(self.lage(ERGEBNIS_DEPLOY="skipped"))
        self.assertEqual(json.loads(json.dumps(urteil))["code"], 1)


class TriggerVertragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _laden(DEPLOY)

    def test_01_drei_ausloeser(self):
        for ereignis in ("workflow_dispatch", "push", "pull_request"):
            self.assertIn("\n  " + ereignis + ":", "\n" + self.text)

    def test_02_deploy_jobs_nur_auf_zuruf(self):
        for job in ("plan", "production-policy", "deploy"):
            block = _job(self.text, job)
            self.assertIn("github.event_name == 'workflow_dispatch'", block,
                          f"Job {job} ist nicht auf den Zuruf begrenzt")

    def test_03_testjob_laeuft_auch_auf_zuruf_vor_dem_plan(self):
        tests = _job(self.text, "tests")
        self.assertNotRegex(tests.split("    steps:", 1)[0], r"(?m)^    if:")
        self.assertNotIn("environment:", tests)
        self.assertNotIn("secrets.", tests)
        self.assertIn("needs: tests", _job(self.text, "plan"))

    def test_04_abschluss_immer_und_vollstaendig_verdrahtet(self):
        block = _job(self.text, "abschluss")
        self.assertIn("if: always()", block)
        for job in ("plan", "tests", "production-policy", "deploy"):
            self.assertIn(job, block.split("steps:")[0])
        self.assertIn("worker_deploy_abschluss.py --pruefen", "\n".join(
            pss.run_bloecke(block)))
        self.assertIn("GITHUB_STEP_SUMMARY", block)

    def test_05_harter_stopp_bleibt_vor_den_secrets(self):
        policy = _job(self.text, "production-policy")
        self.assertIn("worker_environment_guard.py --check",
                      "\n".join(pss.run_bloecke(policy)))
        deploy = _job(self.text, "deploy")
        self.assertIn("environment:", deploy)
        self.assertLess(deploy.index("environment:"), len(deploy))

    def test_06_kein_direktes_event_im_run_block(self):
        for block in pss.run_bloecke(self.text):
            self.assertNotIn("${{ github.event.", block)

    def test_07_pfadfilter_sind_symmetrisch_und_decken_die_skripte(self):
        links = set(_trigger_pfade(self.text, "push"))
        rechts = set(_trigger_pfade(self.text, "pull_request"))
        self.assertEqual(links, rechts)
        for pfad in ("scripts/worker_deploy_abschluss.py", "scripts/ci_tests.py",
                     "scripts/worker_environment_guard.py",
                     "scripts/worker_deploy_vorbereiten.py"):
            self.assertIn(pfad, links, f"Pfadfilter nennt {pfad} nicht")


class AmpelVertragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _laden(HEILUNG)
        cls.laeufe = "\n".join(pss.run_bloecke(cls.text))

    def test_01_checkrecht_und_endpunkt(self):
        self.assertIn("checks: write", _job(self.text, "selbstheilung"))
        self.assertIn("/check-runs", self.laeufe)
        self.assertIn("steps.messung.outputs.code", self.text)

    def test_02_drei_ehrliche_zustaende(self):
        for zustand in ("action_required", "SCHLUSS=success", "SCHLUSS=failure"):
            self.assertIn(zustand, self.laeufe)

    def test_03_schliesspfad_und_keine_fremdgeheimnisse(self):
        self.assertIn("issues/922", self.laeufe)
        for verboten in ("CF_WORKERS_DEPLOY_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
                         "pending_deployments"):
            self.assertNotIn(verboten, self.text)

    def test_04_heiler_bleibt_geeicht_und_verdrahtet(self):
        self.assertEqual(pss.wache(), [])


if __name__ == "__main__":
    unittest.main()
