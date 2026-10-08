#!/usr/bin/env python3
"""Vertragstests: Bildteile im gemeinsamen Modell-Client (08.10.2026).

Auch Bildaufrufe gehen durch scripts/llm_client.py (T6 des KI-Transportwegs).
Festgehalten wird:
  1. Gemini bekommt text + inline_data (base64) in derselben Nachricht.
  2. OpenAI-kompatible Hoster bekommen Inhalts-Teile mit data-URL.
  3. Ungültige Bildangaben wirfen laut (ValueError), nie still verzerrt.
  4. chat() reicht die Bildteile an den jeweiligen Pfad durch – ohne Netz.
"""
from __future__ import annotations

import base64
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "llm_client.py"


def _load():
    spec = importlib.util.spec_from_file_location("llm_client_bilder_ziel", SKRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


lc = _load()

JPEG_1PX = b"\xff\xd8\xff\xe0test"


class BildTeile(unittest.TestCase):
    def test_normalisierung_akzeptiert_nur_bytes(self):
        erwartet = base64.b64encode(JPEG_1PX).decode("ascii")
        self.assertEqual(lc._bild_teile([{"mime": "image/jpeg", "data": JPEG_1PX}]),
                         [("image/jpeg", erwartet)])
        with self.assertRaises(ValueError):
            lc._bild_teile([{"mime": "image/png", "data": "aGVsbG8="}])
        with self.assertRaises(ValueError):
            lc._bild_teile([{"data": b"x"}])
        with self.assertRaises(ValueError):
            lc._bild_teile(["image/png"])

    def test_gemini_payload_traegt_text_und_inline_data(self):
        aufgefangen = {}

        def fake_post(url, headers, payload, timeout):
            aufgefangen.update(url=url, payload=payload)
            return {"candidates": [{"content": {"parts": [{"text": "Beschreibung"}]}}]}

        ursprung = lc._post_json
        lc._post_json = fake_post
        try:
            antwort = lc._call_gemini(
                [{"role": "user", "content": "Beschreibe das Bild"}],
                None, "gemini-3-flash-preview", 0.2, 300, 10,
                lc._bild_teile([{"mime": "image/jpeg", "data": JPEG_1PX}]))
        finally:
            lc._post_json = ursprung
        self.assertEqual(antwort, "Beschreibung")
        teile = aufgefangen["payload"]["contents"][0]["parts"]
        self.assertEqual(teile[0], {"text": "Beschreibe das Bild"})
        self.assertEqual(teile[1]["inline_data"]["mime_type"], "image/jpeg")
        self.assertEqual(teile[1]["inline_data"]["data"],
                         lc._bild_teile([{"mime": "image/jpeg", "data": JPEG_1PX}])[0][1])

    def test_gemini_payload_ohne_bild_bleibt_text_only(self):
        aufgefangen = {}

        def fake_post(url, headers, payload, timeout):
            aufgefangen.update(payload=payload)
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

        ursprung = lc._post_json
        lc._post_json = fake_post
        try:
            lc._call_gemini([{"role": "user", "content": "Hallo"}],
                            None, "m", 0.2, 300, 10)
        finally:
            lc._post_json = ursprung
        self.assertEqual(aufgefangen["payload"]["contents"][0]["parts"],
                         [{"text": "Hallo"}])

    def test_openai_kompatible_hoster_bekommen_data_urls(self):
        aufgefangen = {}

        def fake_post(url, headers, payload, timeout):
            aufgefangen.update(url=url, payload=payload)
            return {"choices": [{"message": {"content": "ok"}}]}

        ursprung = lc._post_json
        lc._post_json = fake_post
        try:
            antwort = lc._call_openai_like(
                "https://integrate.api.nvidia.com/v1/chat/completions", "k",
                [{"role": "user", "content": "Beschreibe"}], None, "m",
                0.2, 300, 10,
                lc._bild_teile([{"mime": "image/png", "data": b"\x00\x01"}]))
        finally:
            lc._post_json = ursprung
        self.assertEqual(antwort, "ok")
        inhalt = aufgefangen["payload"]["messages"][0]["content"]
        self.assertEqual(inhalt[0], {"type": "text", "text": "Beschreibe"})
        self.assertEqual(inhalt[1]["type"], "image_url")
        self.assertEqual(inhalt[1]["image_url"]["url"], "data:image/png;base64,AAE=")

    def test_chat_reicht_bilder_an_gemini_durch(self):
        aufgefangen = {}
        urspruenge = (lc.available, lc.key_for, lc._call_gemini)
        lc.available = lambda provider: True
        lc.key_for = lambda provider: "x"

        def fake_gemini(messages, system, model, temperature, max_tokens,
                        timeout, bild_teile=None):
            aufgefangen["bild_teile"] = bild_teile
            return "Beschreibung"

        lc._call_gemini = fake_gemini
        try:
            antwort = lc.chat("gemini", prompt="p",
                              bilder=[{"mime": "image/webp", "data": b"\x00"}])
        finally:
            lc.available, lc.key_for, lc._call_gemini = urspruenge
        self.assertEqual(antwort, "Beschreibung")
        self.assertEqual(aufgefangen["bild_teile"], [("image/webp", "AA==")])

    def test_chat_ohne_key_bleibt_none_auch_mit_bildern(self):
        ursprung = lc.available
        lc.available = lambda provider: False
        try:
            self.assertIsNone(lc.chat("gemini", prompt="p",
                                      bilder=[{"mime": "image/png", "data": b"x"}]))
        finally:
            lc.available = ursprung


if __name__ == "__main__":
    unittest.main()
