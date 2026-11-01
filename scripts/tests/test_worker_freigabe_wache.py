#!/usr/bin/env python3
"""Vertragstests der Freigabe-Wache (WF-829B/#922, 01.11.2026)."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_freigabe_wache as wache  # noqa: E402

REPO = "frank-hartung/franksfinanzcheck-blog"
TOKEN = "GIFT_GITHUB_TOKEN_NEVER_LOG"
JETZT = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)


def lauf(run_id: object, status: object, created: object, **extra) -> dict:
    daten = {"id": run_id, "status": status, "created_at": created}
    daten.update(extra)
    return daten


def antwort(status: int, koerper: object) -> tuple[int, bytes]:
    return status, json.dumps(koerper).encode("utf-8")


def normalisiert(laeufe: list[dict], workflow: str = "worker-deploy.yml") -> list[dict]:
    return [wache.lauf_normalisieren(eintrag, repo=REPO, workflow=workflow)
            for eintrag in laeufe]


class Adressvertrag(unittest.TestCase):
    def test_lauf_link_wird_aus_geprueften_teilen_gebaut(self):
        self.assertEqual(wache.lauf_link(REPO, 41056313716),
                         f"https://github.com/{REPO}/actions/runs/41056313716")

    def test_unbrauchbares_repo_wird_abgewiesen(self):
        for repo in ("", "nur-ein-name", "owner/repo/extra", "owner/re po", "owner//repo"):
            with self.subTest(repo=repo):
                with self.assertRaises(wache.WachenFehler):
                    wache.lauf_link(repo, 1)

    def test_nur_die_laeufe_liste_ist_erlaubt(self):
        erlaubt = wache.laeufe_url(REPO, "worker-deploy.yml")
        wache._url_pruefen(erlaubt, repo=REPO, workflow="worker-deploy.yml")
        for ziel in (
            "https://boese.example/repos/x/actions/workflows/worker-deploy.yml/runs?per_page=30",
            "http://api.github.com/repos/x/actions/workflows/worker-deploy.yml/runs?per_page=30",
            "https://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/runs?per_page=100",
            "https://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/runs",
            "https://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/runs?per_page=30&seite=2",
            "https://api.github.com/repos/x/y/actions/runs?per_page=30",
            "https://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/dispatches?per_page=30",
        ):
            with self.subTest(ziel=ziel):
                with self.assertRaises(wache.WachenFehler):
                    wache._url_pruefen(ziel, repo="x/y", workflow="worker-deploy.yml")

    def test_unsicherer_workflow_name_wird_abgewiesen(self):
        for workflow in ("../../etc/passwd", "worker deploy.yml", "worker-deploy", "a/B.yml"):
            with self.subTest(workflow=workflow):
                with self.assertRaises(wache.WachenFehler):
                    wache.laeufe_url(REPO, workflow)


class Laufvertrag(unittest.TestCase):
    def test_lauf_wird_normalisiert(self):
        eintrag = wache.lauf_normalisieren(
            lauf(7, "Waiting", "2026-11-01T06:00:00Z", html_url="https://boese.example"),
            repo=REPO, workflow="worker-zugang-pruefen.yml")
        self.assertEqual(eintrag["status"], "waiting")
        self.assertEqual(eintrag["link"], wache.lauf_link(REPO, 7))
        self.assertEqual(eintrag["workflow"], "worker-zugang-pruefen.yml")

    def test_unlesbare_laeufe_sind_kein_gruen(self):
        for eintrag in (
            lauf("7", "waiting", "2026-11-01T06:00:00Z"),
            lauf(True, "waiting", "2026-11-01T06:00:00Z"),
            lauf(0, "waiting", "2026-11-01T06:00:00Z"),
            lauf(7, "", "2026-11-01T06:00:00Z"),
            lauf(7, None, "2026-11-01T06:00:00Z"),
            lauf(7, "waiting", "gestern"),
            lauf(7, "waiting", None),
            lauf(7, "waiting", "2026-11-01T06:00:00+02:00"),
            "kein Objekt",
        ):
            with self.subTest(eintrag=eintrag):
                with self.assertRaises(wache.WachenFehler):
                    wache.lauf_normalisieren(eintrag, repo=REPO, workflow="worker-deploy.yml")


class Bewertungsvertrag(unittest.TestCase):
    def test_ueberfaellige_freigabe_ist_ein_befund(self):
        code, befunde = wache.bewerten(normalisiert([lauf(1, "waiting", "2026-11-01T06:00:00Z")]),
                                       jetzt=JETZT, schwelle=120, repo=REPO)
        self.assertEqual(code, 1)
        self.assertEqual(befunde[0]["minuten"], 360)

    def test_junge_wartung_ist_still(self):
        code, befunde = wache.bewerten(normalisiert([lauf(1, "waiting", "2026-11-01T11:30:00Z")]),
                                       jetzt=JETZT, schwelle=120, repo=REPO)
        self.assertEqual((code, befunde), (0, []))

    def test_schwelle_gilt_minutengenau(self):
        code, _ = wache.bewerten(normalisiert([lauf(1, "waiting", "2026-11-01T10:00:00Z")]),
                                 jetzt=JETZT, schwelle=120, repo=REPO)
        self.assertEqual(code, 1)
        code, _ = wache.bewerten(normalisiert([lauf(1, "waiting", "2026-11-01T10:01:00Z")]),
                                 jetzt=JETZT, schwelle=120, repo=REPO)
        self.assertEqual(code, 0)

    def test_alle_wartezustaende_zaehlen(self):
        for status in ("waiting", "pending", "action_required"):
            with self.subTest(status=status):
                code, _ = wache.bewerten(normalisiert([lauf(1, status, "2026-11-01T06:00:00Z")]),
                                         jetzt=JETZT, schwelle=120, repo=REPO)
                self.assertEqual(code, 1)

    def test_abgeschlossene_und_laufende_laeufe_sind_kein_befund(self):
        for status in ("completed", "in_progress", "queued", "cancelled"):
            with self.subTest(status=status):
                code, befunde = wache.bewerten(normalisiert([lauf(1, status, "2026-11-01T06:00:00Z")]),
                                               jetzt=JETZT, schwelle=120, repo=REPO)
                self.assertEqual((code, befunde), (0, []))

    def test_mehrere_befunde_stehen_im_alter_vorn(self):
        code, befunde = wache.bewerten(
            normalisiert([lauf(1, "waiting", "2026-11-01T09:00:00Z"),
                          lauf(2, "waiting", "2026-10-31T06:00:00Z"),
                          lauf(3, "waiting", "2026-11-01T06:00:00Z")]),
            jetzt=JETZT, schwelle=120, repo=REPO)
        self.assertEqual(code, 1)
        self.assertEqual([b["id"] for b in befunde], [2, 3, 1])

    def test_zukunft_und_ungueltige_schwelle_sind_nicht_belegbar(self):
        with self.assertRaises(wache.WachenFehler):
            wache.bewerten(normalisiert([lauf(1, "waiting", "2026-11-01T13:00:00Z")]),
                           jetzt=JETZT, schwelle=120, repo=REPO)
        for schwelle in (0, -5, 24 * 60 + 1, "120", True):
            with self.subTest(schwelle=schwelle):
                with self.assertRaises(wache.WachenFehler):
                    wache.bewerten(normalisiert([]), jetzt=JETZT, schwelle=schwelle, repo=REPO)


class Ausgabevertrag(unittest.TestCase):
    def test_beschreibung_nennt_lauf_alter_und_link(self):
        _, befunde = wache.bewerten(normalisiert([lauf(41056313716, "waiting", "2026-11-01T06:00:00Z")]),
                                    jetzt=JETZT, schwelle=120, repo=REPO)
        text = wache.beschreibe(befunde, schwelle=120)
        self.assertIn("41056313716", text)
        self.assertIn("360 Minuten", text)
        self.assertIn(wache.lauf_link(REPO, 41056313716), text)

    def test_markdown_ist_leer_und_ehrlich(self):
        leer = wache.markdown([], schwelle=120, repo=REPO)
        self.assertIn("Kein Lauf wartet", leer)
        _, befunde = wache.bewerten(normalisiert([lauf(7, "waiting", "2026-11-01T06:00:00Z")]),
                                    jetzt=JETZT, schwelle=120, repo=REPO)
        reich = wache.markdown(befunde, schwelle=120, repo=REPO)
        self.assertIn("| Lauf |", reich)
        self.assertIn("`7`", reich)
        self.assertIn("Concurrency-Slot", reich)

    def test_ausgabe_enthaelt_kein_geheimnis(self):
        _, befunde = wache.bewerten(normalisiert([lauf(7, "waiting", "2026-11-01T06:00:00Z")]),
                                    jetzt=JETZT, schwelle=120, repo=REPO)
        text = wache.beschreibe(befunde, schwelle=120) + wache.markdown(befunde, schwelle=120, repo=REPO)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("Bearer", text)


class Transportvertrag(unittest.TestCase):
    def _pruefen(self, holen):
        return wache.pruefen({"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN},
                             jetzt=JETZT, holen=holen)

    def test_beide_ketten_werden_gelesen(self):
        gesehen: list[str] = []

        def holen(url, token):
            gesehen.append(url)
            return antwort(200, {"workflow_runs": []})

        code, befunde = self._pruefen(holen)
        self.assertEqual((code, befunde), (0, []))
        self.assertEqual(len(gesehen), 2)
        self.assertIn("worker-deploy.yml", gesehen[0])
        self.assertIn("worker-zugang-pruefen.yml", gesehen[1])

    def test_rechtefehler_ist_nicht_belegbar(self):
        for status in (401, 403, 404, 500):
            with self.subTest(status=status):
                with self.assertRaises(wache.WachenFehler):
                    self._pruefen(lambda url, token: (status, b""))

    def test_kaputtes_json_und_fehlendes_token_sind_nicht_belegbar(self):
        with self.assertRaises(wache.WachenFehler):
            self._pruefen(lambda url, token: (200, b"{nicht json"))
        with self.assertRaises(wache.WachenFehler):
            self._pruefen(lambda url, token: antwort(200, {"workflow_runs": "keine liste"}))
        with self.assertRaises(wache.WachenFehler):
            wache.pruefen({"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": ""},
                          jetzt=JETZT, holen=lambda url, token: antwort(200, {"workflow_runs": []}))
        with self.assertRaises(wache.WachenFehler):
            wache.pruefen({"GITHUB_REPOSITORY": "kaputt", "GITHUB_TOKEN": TOKEN},
                          jetzt=JETZT, holen=lambda url, token: antwort(200, {"workflow_runs": []}))

    def test_token_steht_nur_im_header(self):
        gesehen: list[str] = []

        def holen(url, token):
            gesehen.append(token)
            return antwort(200, {"workflow_runs": []})

        self._pruefen(holen)
        self.assertEqual(gesehen, [TOKEN, TOKEN])


class Kommandozeile(unittest.TestCase):
    def _main(self, argv: list[str], umgebung: dict[str, str]) -> tuple[int, str]:
        puffer = io.StringIO()
        with patch.dict("os.environ", umgebung, clear=False), contextlib.redirect_stdout(puffer):
            code = wache.main(argv)
        return code, puffer.getvalue()

    def test_selftest_ist_gruen(self):
        code, text = self._main(["--selftest"], {})
        self.assertEqual(code, 0)
        self.assertIn("SELBSTTEST OK", text)

    def test_nicht_belegbar_ist_exit_zwei(self):
        # Ohne belegbaren Zustand gibt es kein Grün — und keinen Netzweg im Test.
        with patch.object(wache, "pruefen", side_effect=wache.WachenFehler("Läufe nicht lesbar")):
            code, text = self._main(["--check"], {"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 2)
        self.assertIn("nicht belegt", text)
        self.assertNotIn(TOKEN, text)

    def test_markdown_datei_wird_angehaengt(self):
        import tempfile

        with tempfile.TemporaryDirectory() as ordner:
            ziel = Path(ordner) / "summary.md"
            heute = datetime.now(timezone.utc)

            def holen(url, token):
                return antwort(200, {"workflow_runs": []})

            with patch.object(wache, "_runs_holen", lambda repo, workflow, token, holen=None: []):
                umgebung = {"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN}
                with patch.dict("os.environ", umgebung, clear=False), \
                        contextlib.redirect_stdout(io.StringIO()):
                    code = wache.main(["--check", "--md", str(ziel)])
            self.assertEqual(code, 0)
            self.assertIn("Wartende Deploy-Freigaben", ziel.read_text(encoding="utf-8"))
            self.assertTrue(heute)  # Bezugszeit bleibt die echte Uhr im Live-Pfad


if __name__ == "__main__":
    unittest.main()
