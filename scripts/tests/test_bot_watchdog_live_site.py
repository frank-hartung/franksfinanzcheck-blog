#!/usr/bin/env python3
"""Tests für die Auslieferungs-Diagnose des Bot-Watchdogs (Dauerheilung #676).

Ticket #676 meldete „Neuester Artikel nicht live" mit dem nächsten Schritt
„Deploy prüfen, ggf. Deploy-Catchup triggern" – eine Arbeitsanweisung an
einen Menschen, obwohl der Befund den Besitzer `auto` trägt („eine Maschine
kann ihn heilen"). Die Ursache stand nicht im Ticket: deploy.yml war 20× in
Folge am Release-Scorecard-Schritt abgebrochen, VOR dem Hochladen des
Pages-Artefakts, und hatte die Live-Site 19 h 38 min eingefroren.

Diese Tests frieren drei Verträge ein:

  1. DIAGNOSE  – der Watchdog erkennt am deploy-Job, ob die Auslieferung
     blockiert ist, und benennt den blockierenden Schritt.
  2. BEFUND    – der 404-Befund trägt Ursache und Heilungsweg; ein
     blockierter Auslieferungsweg ist zusätzlich ein EIGENER Befund, damit
     die eingefrorene Site auch ohne neuen 404-Artikel auffällt (#537-Klasse).
  3. HEILUNG   – `watchdog_recovery.py --live-site` löst den Catchup nur aus,
     wenn ein Dispatch überhaupt heilen kann, und nie doppelt.

Läuft deterministisch ohne Netz: alle gh-Aufrufe sind ersetzt.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import bot_watchdog as bw  # noqa: E402
import watchdog_recovery as recovery  # noqa: E402

SCORECARD_SCHRITT = "Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)"
ARTEFAKT_SCHRITT = bw.ARTEFAKT_SCHRITT
PAGES_JOB = bw.PAGES_JOB_NAME


def deploy_job(fazit: str, schritte: list) -> dict:
    return {"name": bw.DEPLOY_JOB_NAME, "conclusion": fazit, "steps": schritte}


def schritt(name: str, fazit: str) -> dict:
    return {"name": name, "conclusion": fazit}


class ClassifyDeployJobsTestCase(unittest.TestCase):
    """Rein funktional: Job-Liste rein, Lage + Ursache raus."""

    def test_blockierter_auslieferungsweg_wird_benannt(self) -> None:
        """Der #676-Fall: Scorecard rot, Artefakt gesprungen, Pages gar nicht."""
        lage, block, beleg = bw.classify_deploy_jobs([
            deploy_job("failure", [
                schritt("Publish-Gate (harte Qualitäts-, Affiliate-, Fakten- und YMYL-Freigaben)", "success"),
                schritt(SCORECARD_SCHRITT, "failure"),
                schritt("Deploy auf gh-pages", "skipped"),
                schritt(ARTEFAKT_SCHRITT, "skipped"),
            ]),
            {"name": PAGES_JOB, "conclusion": "skipped"},
        ])
        self.assertEqual(lage, "blockiert")
        self.assertEqual(block, SCORECARD_SCHRITT,
                         "Das Ticket muss den blockierenden Schritt nennen")
        self.assertIn("failure", beleg)

    def test_erster_fehlerschritt_zaehlt_nicht_der_letzte(self) -> None:
        lage, block, _ = bw.classify_deploy_jobs([
            deploy_job("failure", [
                schritt("Publish-Gate (harte Qualitäts-, Affiliate-, Fakten- und YMYL-Freigaben)", "failure"),
                schritt(SCORECARD_SCHRITT, "skipped"),
                schritt(ARTEFAKT_SCHRITT, "skipped"),
            ]),
        ])
        self.assertEqual(lage, "blockiert")
        self.assertEqual(block, "Publish-Gate (harte Qualitäts-, Affiliate-, Fakten- und YMYL-Freigaben)")

    def test_belegte_auslieferung_ist_gruen(self) -> None:
        lage, block, beleg = bw.classify_deploy_jobs([
            deploy_job("success", [schritt(ARTEFAKT_SCHRITT, "success")]),
            {"name": PAGES_JOB, "conclusion": "success"},
        ])
        self.assertEqual(lage, "ausgeliefert")
        self.assertEqual(block, "")
        self.assertIn("Pages-Deployment erfolgreich", beleg)

    def test_ausgebliebenes_pages_deployment_ist_blockiert(self) -> None:
        """Issue-#537-Klasse: Artefakt da, aber öffentlich nie ausgeliefert."""
        lage, block, _ = bw.classify_deploy_jobs([
            deploy_job("success", [schritt(ARTEFAKT_SCHRITT, "success")]),
            {"name": PAGES_JOB, "conclusion": "skipped"},
        ])
        self.assertEqual(lage, "blockiert")
        self.assertIn(PAGES_JOB, block)

    def test_uebersprungener_deploy_ist_kein_befund(self) -> None:
        lage, _, beleg = bw.classify_deploy_jobs([deploy_job("skipped", [])])
        self.assertEqual(lage, "uebersprungen")
        self.assertIn("kein Deploy verlangt", beleg)

    def test_verdraengter_lauf_ist_kein_befund(self) -> None:
        """`cancelled` ist gewolltes Verdrängen (Issue #218)."""
        lage, _, beleg = bw.classify_deploy_jobs([deploy_job("cancelled", [])])
        self.assertEqual(lage, "uebersprungen")
        self.assertIn("verdrängt", beleg)

    def test_leere_jobliste_erfindet_kein_urteil(self) -> None:
        for eingabe in ([], None, "kaputt"):
            lage, block, _ = bw.classify_deploy_jobs(eingabe)
            self.assertEqual(lage, "unbekannt")
            self.assertEqual(block, "")

    def test_fehlender_deploy_job_erfindet_kein_urteil(self) -> None:
        lage, _, beleg = bw.classify_deploy_jobs([
            {"name": "irgendein anderer Job", "conclusion": "failure", "steps": []},
        ])
        self.assertEqual(lage, "unbekannt")
        self.assertIn("nicht gefunden", beleg)

    def test_gruener_deploy_job_ohne_artefakt_bleibt_unbekannt(self) -> None:
        """Ein success ohne Artefakt-Schritt ist kein erfundener Befund."""
        lage, _, _ = bw.classify_deploy_jobs([
            deploy_job("success", [schritt("Irgendein Schritt", "success")]),
        ])
        self.assertEqual(lage, "unbekannt")


class LiveSiteBefundTestCase(unittest.TestCase):
    """Der 404-Befund trägt Ursache + Heilungsweg, nicht nur den Status."""

    def test_blockade_nennt_ursache_und_schritt(self) -> None:
        befunde = bw.live_site_findings(
            "2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust",
            "404", "blockiert", SCORECARD_SCHRITT, "deploy-Job failure (Lauf 1)")
        self.assertEqual([f.id for f in befunde], ["live-site", "deploy-blockade"])
        live = befunde[0]
        self.assertEqual(live.severity, "P1")
        self.assertEqual(live.owner, "auto")
        self.assertIn(SCORECARD_SCHRITT, live.detail)
        self.assertIn("HTTP 404", live.detail)
        self.assertIn(f"BLOCKIERENDER_SCHRITT={SCORECARD_SCHRITT}", live.evidence)

    def test_heilungsweg_ist_maschinell_nicht_menschlich(self) -> None:
        befunde = bw.live_site_findings("irgendein-slug", "404", "unbekannt", "", "")
        self.assertEqual(len(befunde), 1, "Ohne Blockade gibt es genau einen Befund")
        self.assertIn("watchdog_recovery.py --live-site", befunde[0].next_step)
        self.assertNotIn("BLOCKIERENDER_SCHRITT", "".join(befunde[0].evidence))

    def test_blockade_ist_eigener_befund_auch_ohne_404(self) -> None:
        """Die eingefrorene Site muss auch ohne neuen 404-Artikel auffallen."""
        befunde = bw.live_site_findings("slug", "404", "blockiert", "X-Schritt", "Beleg")
        blockade = [f for f in befunde if f.id == "deploy-blockade"]
        self.assertEqual(len(blockade), 1)
        self.assertEqual(blockade[0].severity, "P1")
        self.assertEqual(blockade[0].owner, "auto")
        self.assertIn("X-Schritt", blockade[0].detail)

    def test_befund_ohne_beleg_hat_keine_leeren_zeilen(self) -> None:
        befunde = bw.live_site_findings("slug", "404", "ausgeliefert", "", "")
        self.assertTrue(all(e for e in befunde[0].evidence),
                        "Leere Beweis-Zeilen verwässern das Ticket")


class DeployBlockadeIOTestCase(unittest.TestCase):
    """deploy_blockade() liest gh – hier ersetzt, damit es offline läuft."""

    def _patch(self, antworten):
        aufrufe = []

        def fake_run_cmd(argv, timeout=30):
            aufrufe.append(list(argv))
            return antworten[len(aufrufe) - 1]

        return fake_run_cmd, aufrufe

    def test_blockierter_lauf_wird_erkannt(self) -> None:
        lauf_id = "37964399723"
        runs = json.dumps([{
            "databaseId": int(lauf_id), "status": "completed",
            "conclusion": "failure", "createdAt": _jetzt_iso(),
        }])
        jobs = json.dumps({"jobs": [
            deploy_job("failure", [
                schritt(SCORECARD_SCHRITT, "failure"),
                schritt(ARTEFAKT_SCHRITT, "skipped"),
            ]),
            {"name": PAGES_JOB, "conclusion": "skipped"},
        ]})
        fake, aufrufe = self._patch([(0, runs, ""), (0, jobs, "")])
        with mock.patch.object(bw, "run_cmd", fake):
            lage, block, beleg = bw.deploy_blockade()
        self.assertEqual(lage, "blockiert")
        self.assertEqual(block, SCORECARD_SCHRITT)
        self.assertIn(lauf_id, beleg)
        self.assertIn(lauf_id, aufrufe[1])

    def test_gh_fehler_ist_kein_ausfall(self) -> None:
        fake, _ = self._patch([(1, "", "gh: not found")])
        with mock.patch.object(bw, "run_cmd", fake):
            lage, block, beleg = bw.deploy_blockade()
        self.assertEqual(lage, "unbekannt")
        self.assertEqual(block, "")
        self.assertIn("gh Fehler", beleg)

    def test_offenes_json_ist_kein_ausfall(self) -> None:
        fake, _ = self._patch([(0, "{kein json", "")])
        with mock.patch.object(bw, "run_cmd", fake):
            lage, _, beleg = bw.deploy_blockade()
        self.assertEqual(lage, "unbekannt")
        self.assertIn("unparsable", beleg)

    def test_lauf_ausserhalb_des_fensters_zaehlt_nicht(self) -> None:
        alt = "2026-10-01T00:00:00Z"
        fake, _ = self._patch([(0, json.dumps([{
            "databaseId": 1, "status": "completed",
            "conclusion": "failure", "createdAt": alt,
        }]), "")])
        with mock.patch.object(bw, "run_cmd", fake):
            lage, _, beleg = bw.deploy_blockade(hours=30)
        self.assertEqual(lage, "unbekannt")
        self.assertIn("kein abgeschlossener Deploy-Lauf", beleg)

    def test_laufender_lauf_wird_nicht_bewertet(self) -> None:
        fake, _ = self._patch([(0, json.dumps([{
            "databaseId": 1, "status": "in_progress",
            "conclusion": None, "createdAt": _jetzt_iso(),
        }]), "")])
        with mock.patch.object(bw, "run_cmd", fake):
            lage, _, _ = bw.deploy_blockade()
        self.assertEqual(lage, "unbekannt")


class LiveSiteRecoveryTestCase(unittest.TestCase):
    """--live-site heilt nur, wenn ein Dispatch überhaupt heilen kann."""

    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {"GH_TOKEN": "x"}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.which = mock.patch.object(recovery.shutil, "which", return_value="/usr/bin/gh")
        self.which.start()
        self.addCleanup(self.which.stop)

    def test_blockierte_auslieferung_loest_keinen_dispatch_aus(self) -> None:
        """Ein erneuter Catchup würde am selben Schritt scheitern."""
        with mock.patch.object(recovery, "deploy_chain_blocked",
                               return_value=(True, "Schritt „X“")), \
             mock.patch.object(recovery, "_run") as run:
            code = recovery.trigger_deploy_catchup()
        self.assertEqual(code, 3)
        run.assert_not_called()

    def test_laufender_deploy_wird_nicht_verdraengt(self) -> None:
        with mock.patch.object(recovery, "deploy_chain_blocked",
                               return_value=(False, "alles gut")), \
             mock.patch.object(recovery, "deploy_in_flight", return_value=True), \
             mock.patch.object(recovery, "_run") as run:
            code = recovery.trigger_deploy_catchup()
        self.assertEqual(code, 0)
        run.assert_not_called()

    def test_fehlender_artikel_stoest_catchup_an(self) -> None:
        with mock.patch.object(recovery, "deploy_chain_blocked",
                               return_value=(False, "ausgeliefert")), \
             mock.patch.object(recovery, "deploy_in_flight", return_value=False), \
             mock.patch.object(recovery, "_run",
                               return_value=_proc(0)) as run:
            code = recovery.trigger_deploy_catchup()
        self.assertEqual(code, 0)
        argv = run.call_args[0][0]
        self.assertEqual(argv[:3], ["gh", "workflow", "run"])
        self.assertIn("deploy-catchup.yml", argv)
        self.assertIn("main", argv)

    def test_ohne_token_kein_dispatch(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(recovery, "_run") as run:
            code = recovery.trigger_deploy_catchup()
        self.assertEqual(code, 2)
        run.assert_not_called()

    def test_unmessbare_kette_heilt_trotzdem(self) -> None:
        """Unklarheit darf die einzige Reparaturroute nicht abschalten."""
        with mock.patch.object(recovery, "deploy_chain_blocked",
                               return_value=(False, "nicht messbar")), \
             mock.patch.object(recovery, "deploy_in_flight", return_value=False), \
             mock.patch.object(recovery, "_run", return_value=_proc(0)) as run:
            self.assertEqual(recovery.trigger_deploy_catchup(), 0)
        run.assert_called_once()

    def test_selftest_bleibt_gruen(self) -> None:
        self.assertEqual(recovery.selftest(), 0)


def _jetzt_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _proc:
    """Minimaler CompletedProcess-Ersatz für die gh-Aufrufe."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


if __name__ == "__main__":
    unittest.main()
