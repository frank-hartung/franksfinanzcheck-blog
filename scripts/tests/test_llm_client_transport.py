"""Offline contract tests for the shared provider transports."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import llm_client as lc  # noqa: E402


class _Response:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, amount: int = -1):
        if amount == 1:
            return self._body[:1]
        return self._body


class SharedTransportTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "GROQ_API_KEY": "groq-test-key",
            "GEMINI_API_KEY": "gemini-test-key",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_groq_chat_uses_the_central_endpoint_and_reasoning_flag(self):
        calls = []

        def fake_post(url, headers, payload, timeout):
            calls.append((url, headers, payload, timeout))
            return {"choices": [{"message": {"content": "Antwort"}}]}

        with mock.patch.object(lc, "_post_json", side_effect=fake_post):
            answer = lc.chat("groq", prompt="Test", attempts=1)

        self.assertEqual(answer, "Antwort")
        self.assertEqual(len(calls), 1)
        url, headers, payload, _timeout = calls[0]
        self.assertEqual(url, lc.GROQ_CHAT_URL)
        self.assertEqual(headers["Authorization"], "Bearer groq-test-key")
        self.assertFalse(payload["include_reasoning"])

    def test_gemini_key_is_never_put_in_the_url(self):
        calls = []

        def fake_post(url, headers, payload, timeout):
            calls.append((url, headers, payload, timeout))
            return {"candidates": [{"content": {"parts": [{"text": "Antwort"}]}}]}

        with mock.patch.object(lc, "_post_json", side_effect=fake_post):
            answer = lc.chat("gemini", prompt="Test", attempts=1)

        self.assertEqual(answer, "Antwort")
        url, headers, _payload, _timeout = calls[0]
        self.assertNotIn("gemini-test-key", url)
        self.assertNotIn("?key=", url)
        self.assertEqual(headers["x-goog-api-key"], "gemini-test-key")

    def test_gemini_key_probe_uses_header_and_returns_only_status(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request, timeout))
            return _Response(b"{}", 200)

        with mock.patch.object(lc.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = lc.probe_key("gemini", "gemini-probe-key", timeout=7)

        self.assertEqual(result, (200, None))
        request, timeout = calls[0]
        self.assertEqual(request.full_url, lc.GEMINI_MODELS_URL)
        self.assertNotIn("gemini-probe-key", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-probe-key")
        self.assertEqual(timeout, 7)

    def test_audio_transcription_uses_central_multipart_transport(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request, timeout))
            return _Response(json.dumps({"text": "Gesprochene Worte"}).encode())

        with mock.patch.object(lc.urllib.request, "urlopen", side_effect=fake_urlopen):
            answer = lc.transcribe_audio(
                b"audio-bytes", filename="../episode\r\nInjected.mp3", attempts=1)

        self.assertEqual(answer, "Gesprochene Worte")
        request, timeout = calls[0]
        self.assertEqual(request.full_url, lc.GROQ_AUDIO_TRANSCRIPTIONS_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer groq-test-key")
        body = request.data.decode("utf-8", errors="replace")
        self.assertIn('name="model"', body)
        self.assertIn("whisper-large-v3-turbo", body)
        self.assertIn('filename="episode__Injected.mp3"', body)
        self.assertNotIn("\r\nInjected.mp3", body)
        self.assertIn("audio-bytes", body)
        self.assertTrue(request.get_header("Content-type").startswith("multipart/form-data; boundary="))
        self.assertEqual(timeout, 300)


if __name__ == "__main__":
    unittest.main()
