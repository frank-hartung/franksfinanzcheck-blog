#!/usr/bin/env python3
"""test_n8n_bridge.py — Unit-Tests für die n8n-Bridge."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import n8n_bridge


# ----------------------------------------------------------------------
#  Die GANZE Testdatei laeuft in einem Wegwerf-Ordner.
#
#  WARUM (03.10.2026): Mehrere Tests rufen handle_inbound_payload() bzw.
#  dispatch_event_to_n8n() direkt auf. Jeder Lauf haengte damit echte
#  Zeilen an data/n8n_bridge_log.jsonl und verbog
#  data/n8n_bridge_state.json – Diff-Rauschen, das versehentlich
#  mitcommittet werden konnte. Ein Testlauf darf den Bestand so wenig
#  veraendern wie ein Pruef-Aufruf (C15).
# ----------------------------------------------------------------------
_SANDKASTEN = None


def setUpModule() -> None:
    global _SANDKASTEN
    _SANDKASTEN = n8n_bridge._ablage_im_sandkasten()
    _SANDKASTEN.__enter__()


def tearDownModule() -> None:
    if _SANDKASTEN is not None:
        _SANDKASTEN.__exit__(None, None, None)


class TestN8nBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="test_n8n_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_state_load_and_save(self) -> None:
        state_file = os.path.join(self.tmp_dir, "bridge_state.json")
        orig_state_path = n8n_bridge.BRIDGE_STATE_PATH
        n8n_bridge.BRIDGE_STATE_PATH = state_file

        try:
            st = n8n_bridge.load_bridge_state()
            self.assertEqual(st.get("version"), 1)
            st["gesendete_events"] = 42
            n8n_bridge.save_bridge_state(st)

            reloaded = n8n_bridge.load_bridge_state()
            self.assertEqual(reloaded["gesendete_events"], 42)
        finally:
            n8n_bridge.BRIDGE_STATE_PATH = orig_state_path

    def test_dispatch_dry_run(self) -> None:
        res = n8n_bridge.dispatch_event_to_n8n(
            event_type="test_event",
            payload={"key": "value"},
            webhook_url="http://localhost:5678/webhook/test",
            dry_run=True,
        )
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["event_type"], "test_event")

    def test_handle_inbound_voice_memo(self) -> None:
        payload = {
            "typ": "voice_memo",
            "data": {
                "titel": "Kostenloses Girokonto 2026",
                "inhalt": "Wir vergleichen kostenlose Girokonten und Gebührenfallen im Alltag.",
                "kategorie": "konto-karten",
            },
        }
        res = n8n_bridge.handle_inbound_payload(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "draft_created")
        self.assertTrue(os.path.exists(res["file"]))

        # Cleanup – inklusive des Elternordners, falls dieser Test ihn
        # erzeugt hat. Ein leer zurueckgelassenes content/-Verzeichnis
        # toetet den Hugo-Build (Befund 03.10.2026, Lauf 37149404892).
        draft_dir = os.path.dirname(res["file"])
        if os.path.exists(draft_dir):
            shutil.rmtree(draft_dir)
        eltern = os.path.dirname(draft_dir)
        if os.path.isdir(eltern) and not os.listdir(eltern):
            os.rmdir(eltern)

    def test_handle_inbound_ping(self) -> None:
        payload = {"typ": "ping"}
        res = n8n_bridge.handle_inbound_payload(payload)
        self.assertEqual(res["status"], "ok")

    def test_ping_n8n_offline_graceful(self) -> None:
        # Auf nicht erreichbarem Port muss es graceful mit standby/offline antworten
        res = n8n_bridge.ping_n8n("http://127.0.0.1:59999")
        self.assertEqual(res["status"], "offline_or_standby")
        self.assertIn("message", res)


class SelbsttestHinterlaesstNichts(unittest.TestCase):
    """C15 fuer den Selbsttest: kein Diff, keine Datei, KEIN leerer Ordner.

    BEFUND 03.10.2026 (Lauf 37149404892)
    `n8n_bridge.selftest()` legte content/drafts/<slug>/ an und raeumte nur
    den <slug>-Ordner weg. Der leere Elternordner blieb liegen. Git meldet
    leere Verzeichnisse prinzipiell nicht, der Selbsttest-Runner sah also
    nichts – der Hugo-Build im selben Job starb danach mit einem Typfehler
    in der Sitemap. Zwei Wachen gruen, Produktion rot.
    """

    def _zustand(self):
        wurzel = n8n_bridge.BLOG_DIR
        r = subprocess.run(("git", "-C", wurzel, "status", "--porcelain"),
                           capture_output=True, text=True, timeout=120)
        dateien = {z.strip() for z in r.stdout.splitlines() if z.strip()}
        leer = set()
        for basis in ("content", "data"):
            start = os.path.join(wurzel, basis)
            if not os.path.isdir(start):
                continue
            for ordner, unter, dateien_im in os.walk(start):
                if not unter and not dateien_im:
                    leer.add(os.path.relpath(ordner, wurzel))
        return dateien, leer

    def test_selftest_laesst_weder_datei_noch_leeren_ordner_zurueck(self) -> None:
        vorher_dateien, vorher_leer = self._zustand()
        self.assertTrue(n8n_bridge.selftest(), "Selbsttest selbst ist rot")
        nachher_dateien, nachher_leer = self._zustand()

        self.assertEqual(
            sorted(nachher_dateien - vorher_dateien), [],
            "Der Selbsttest hat in den Arbeitsbaum geschrieben (C15).")
        self.assertEqual(
            sorted(nachher_leer - vorher_leer), [],
            "Der Selbsttest hat ein LEERES Verzeichnis zurueckgelassen. Git "
            "zeigt das nicht an, Hugo stirbt daran: content/drafts/ liess am "
            "03.10.2026 den gesamten Build abbrechen.")

    def test_echte_ablage_bleibt_unberuehrt(self) -> None:
        """Der Sandkasten darf den Live-Zustand nicht veraendern."""
        pfad = n8n_bridge.BRIDGE_STATE_PATH
        vorher = None
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                vorher = fh.read()
        n8n_bridge.selftest()
        self.assertEqual(pfad, n8n_bridge.BRIDGE_STATE_PATH,
                         "Pfad wurde nicht zurueckgebaut")
        if vorher is not None:
            with open(pfad, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), vorher,
                                 "Der echte Bruecken-Zustand wurde veraendert")


if __name__ == "__main__":
    unittest.main()
