# -*- coding: utf-8 -*-
"""Wer auf `main` schreibt, wartet aufeinander – der Vertrag, nicht die Absicht.

DER VORGANG (#1244–#1246, Meldung des Inhabers vom 21.11.2026)
==============================================================
Drei Läufe scheiterten am 16.11.2026 – einem **Montag** – beim Committen oder
Pushen: `FrankAutoOps-Report`, `ZEIT-Rechtschreib-Wache`, `Hemingway-Check`.
Ihre Cron-Zeiten: **04:45, 04:35, 04:50**. Gemessene Laufzeit von AutoOps:
**693 s (11,6 min)**; damit reicht 04:45 bis über 04:56 und überlappt beide
anderen, obwohl keine zwei in derselben Minute starten.

Jeder der drei hatte eine `concurrency`-Gruppe:

    group: frankautoops-report
    group: zeit-rechtschreibung
    group: hemingway-check

Eine eigene Gruppe serialisiert einen Workflow gegen SICH SELBST. Drei
verschiedene Gruppen bedeuten: drei Läufe dürfen gleichzeitig denselben
Branch committen. Auf `main` liegen an diesem Morgen `ab677efe` 14:02,
`17151fad` 14:04, `32976dca` 14:05, `551f12a9` 14:12.

DIE ENTSCHEIDUNG DES INHABERS (21.11.2026)
==========================================
„Nur belegte Kollisionen" – nicht alle 61 Schreiber. Begründung aus den
Zahlen: Eine Gruppe über alle hätte als Obergrenze die Summe der
Job-Timeouts (2.015 min = 33,6 h), inklusive `deploy.yml` (170 min). Ein
hängender Deploy würde die gesamte Nachtkette blockieren.

DIESE DATEI BEWACHT
===================
1. Die Regel selbst (`schreiber_serialisierung.pruefe`).
2. Die drei Fehlversuche beim Bau der Wache – Textsuche statt YAML-Struktur.
   Ohne sie wäre `alert-on-failure.yml` als Schreiber geführt worden, weil
   er `git_sync.sh` in einem JS-**String** nennt (Rat-Text, kein Befehl).
3. Den Zuschnitt: Die belegten Kollisionen MÜSSEN serialisiert sein, und
   `deploy.yml` muss eine begründete eigene Gruppe behalten.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import schreiber_serialisierung as ss  # noqa: E402


class RegelTest(unittest.TestCase):
    """Die eine Regel: wer schreibt, teilt die Sperre."""

    def _wf(self, gruppe, schreibt=True, timeouts=(20,), pr=False, nur_main=False):
        return {"name": "x.yml", "messbar": True, "gruppe": gruppe,
                "schreibt": schreibt, "timeouts": list(timeouts),
                "cron": [], "nur_main": nur_main, "hat_pr_trigger": pr}

    def test_eigene_gruppe_ist_ein_befund(self):
        befunde = ss.pruefe(self._wf("mein-eigener-name"))
        self.assertTrue(befunde)
        self.assertIn("teilt aber die Sperre nicht", befunde[0])

    def test_geteilte_gruppe_ist_gruen(self):
        self.assertEqual([], ss.pruefe(self._wf(ss.SCHREIBER_GRUPPE)))

    def test_ohne_timeout_ist_ein_befund(self):
        befunde = ss.pruefe(self._wf(ss.SCHREIBER_GRUPPE, timeouts=()))
        self.assertTrue(any("timeout-minutes" in b for b in befunde),
                        "Ohne Timeout blockiert ein hängender Lauf alle anderen")

    def test_nicht_schreiber_wird_nicht_geprueft(self):
        self.assertEqual([], ss.pruefe(self._wf("egal", schreibt=False)))

    def test_pr_trigger_ohne_main_grenze_ist_ein_befund(self):
        befunde = ss.pruefe(self._wf(ss.SCHREIBER_GRUPPE, pr=True, nur_main=False))
        self.assertTrue(any("pull_request" in b for b in befunde))

    def test_pr_trigger_mit_main_grenze_ist_gruen(self):
        self.assertEqual([], ss.pruefe(self._wf(ss.SCHREIBER_GRUPPE,
                                               pr=True, nur_main=True)))

    def test_ausnahme_behaelt_nur_die_timeout_pflicht(self):
        """`deploy.yml` darf seine eigene Gruppe haben – aber nicht schutzlos."""
        name = "deploy.yml"
        self.assertIn(name, ss.EIGENE_GRUPPE)
        wf = dict(self._wf("pages-deploy"), name=name)
        self.assertEqual([], ss.pruefe(wf), "begründete Ausnahme")
        ohne = dict(wf, timeouts=())
        self.assertTrue(ss.pruefe(ohne), "Ausnahme ohne Timeout ist keine")


class TextsucheIstDerFalscheHebelTest(unittest.TestCase):
    """Die drei Fehlversuche – sie sind der Grund für YAML-Lesen.

    Alle drei Attrappen enthalten `git_sync.sh` im DATEITEXT. Nur die letzte
    führt es aus. Wer hier auf Textsuche zurückfällt, macht die Wache blind
    für Meldungen und taub für Befehle – je nach Richtung.
    """

    def _schreibt(self, yaml_text: str) -> bool:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "wf.yml"
            p.write_text(yaml_text, encoding="utf-8")
            return ss.erfasse(p)["schreibt"]

    def test_js_kommentar_ist_kein_befehl(self):
        text = ("on:\n  workflow_run:\njobs:\n  a:\n    steps:\n"
                "      - uses: actions/github-script@v7\n"
                "        with:\n          script: |\n"
                "            // git_sync.sh benutzt kein Modell.\n")
        self.assertFalse(self._schreibt(text))

    def test_js_string_ist_kein_befehl(self):
        """Der echte Fall: `alert-on-failure.yml` nennt den Dateinamen im RAT."""
        text = ("on:\n  workflow_run:\njobs:\n  a:\n    steps:\n"
                "      - uses: actions/github-script@v7\n"
                "        with:\n          script: |\n"
                "            const h = 'Ein API-Key kann das nicht: git_sync.sh "
                "benutzt keinen';\n")
        self.assertFalse(self._schreibt(text),
                         "Ein Rat-Text ist kein ausgeführtes Kommando")

    def test_yaml_kommentar_ist_kein_befehl(self):
        text = ("on:\n  push:\njobs:\n  a:\n    steps:\n"
                "      # - run: scripts/git_sync.sh --push-only\n"
                "      - run: echo nur-lesen\n")
        self.assertFalse(self._schreibt(text))

    def test_echter_aufruf_wird_erkannt(self):
        for befehl in ("scripts/git_sync.sh --push-only", "git push origin HEAD",
                       "git -c user.name=X push origin HEAD"):
            with self.subTest(befehl=befehl):
                text = ("on:\n  push:\njobs:\n  a:\n    steps:\n"
                        f"      - run: {befehl}\n")
                self.assertTrue(self._schreibt(text),
                                "Ein echter Aufruf MUSS erkannt werden – sonst "
                                "ist die Wache blind")


class DerZuschnittTest(unittest.TestCase):
    """Die belegten Kollisionen sind serialisiert, deploy.yml nicht."""

    # 04:35/04:45/04:50 – der Montag, an dem die drei Vorgänge rot waren.
    MONTAGSKETTE = ("zeit-rechtschreibung.yml", "frankautoops-report.yml",
                    "hemingway-check.yml")
    # Die im Bericht belegten Minuten-Kollisionen (02.21.2026 gemessen).
    KOLLISIONEN = ("newsletter-daily.yml", "pinterest-watchdog.yml",
                   "sprach-qualitaet-pipeline.yml", "layout-ai.yml",
                   "update-quarterly.yml", "affiliate-health.yml",
                   "redaktions-standard-bestand.yml")

    def _gruppe(self, name: str) -> str:
        return ss.erfasse(ss.WORKFLOWS / name)["gruppe"]

    def test_montagskette_teilt_die_sperre(self):
        for name in self.MONTAGSKETTE:
            with self.subTest(workflow=name):
                self.assertEqual(ss.SCHREIBER_GRUPPE, self._gruppe(name),
                                 "Genau diese drei Läufe waren am 16.11. rot")

    def test_belegte_minutenkollisionen_teilen_die_sperre(self):
        for name in self.KOLLISIONEN:
            with self.subTest(workflow=name):
                self.assertEqual(ss.SCHREIBER_GRUPPE, self._gruppe(name))

    def test_deploy_bleibt_aussen(self):
        self.assertNotEqual(ss.SCHREIBER_GRUPPE, self._gruppe("deploy.yml"),
                            "Ein Deploy darf nicht hinter Bot-Läufen warten")
        self.assertIn("deploy.yml", ss.EIGENE_GRUPPE)

    def test_cancel_in_progress_bleibt_false(self):
        """`true` würde laufende Schreiber MITTEN im Push abschneiden."""
        for name in self.MONTAGSKETTE + self.KOLLISIONEN:
            with self.subTest(workflow=name):
                text = (ss.WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertNotIn("cancel-in-progress: true", text,
                                 "Ein abgebrochener Lauf zwischen Commit und "
                                 "Push hinterlässt einen halben Stand")

    def test_alle_ausnahmen_haben_einen_grund(self):
        for name, grund in ss.EIGENE_GRUPPE.items():
            with self.subTest(workflow=name):
                self.assertGreater(len(grund.strip()), 30,
                                   "Eine Ausnahme ohne Begründung ist eine Lücke")


class MessbarkeitTest(unittest.TestCase):
    def test_bericht_ist_reproduzierbar(self):
        d = ss.bericht()
        self.assertGreater(d["workflows"], 90)
        self.assertGreaterEqual(d["serialisiert"], 10,
                                "Der Zuschnitt muss im Bericht ankommen")
        self.assertIsInstance(d["kollisionen"], list)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(0, ss.main(["--selftest"]))


if __name__ == "__main__":
    unittest.main()
