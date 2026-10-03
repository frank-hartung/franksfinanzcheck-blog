#!/usr/bin/env python3
"""test_n8n_bridge.py — Unit-Tests für die n8n-Bridge."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import n8n_bridge


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

        # Cleanup
        draft_dir = os.path.dirname(res["file"])
        if os.path.exists(draft_dir):
            shutil.rmtree(draft_dir)

    def test_handle_inbound_ping(self) -> None:
        payload = {"typ": "ping"}
        res = n8n_bridge.handle_inbound_payload(payload)
        self.assertEqual(res["status"], "ok")

    def test_ping_n8n_offline_graceful(self) -> None:
        # Auf nicht erreichbarem Port muss es graceful mit standby/offline antworten
        res = n8n_bridge.ping_n8n("http://127.0.0.1:59999")
        self.assertEqual(res["status"], "offline_or_standby")
        self.assertIn("message", res)


if __name__ == "__main__":
    unittest.main()
