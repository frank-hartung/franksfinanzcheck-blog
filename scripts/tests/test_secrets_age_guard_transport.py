"""Secret-Wächter delegates model-key probes to the shared client."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import secrets_age_guard as sag  # noqa: E402


class ModelKeyProbeTests(unittest.TestCase):
    def test_groq_key_probe_uses_llm_client(self):
        with mock.patch.object(sag.llm_client, "probe_key", return_value=(200, None)) as probe:
            result = sag._probe_groq("groq-test-key")
        self.assertEqual(result, ("ok", "Groq /models 200"))
        probe.assert_called_once_with("groq", "groq-test-key", timeout=sag.PROBE_TIMEOUT)

    def test_gemini_key_probe_uses_llm_client(self):
        with mock.patch.object(sag.llm_client, "probe_key", return_value=(403, "HTTP 403")) as probe:
            result = sag._probe_gemini("gemini-test-key")
        self.assertEqual(result, ("dead", "Gemini Key abgelehnt (403)"))
        probe.assert_called_once_with("gemini", "gemini-test-key", timeout=sag.PROBE_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
