#!/usr/bin/env python3
"""Unit-Tests für scripts/ki_assistent_gate.py (2026-10-08)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ki_assistent_gate as gate


class TestRegistrierung(unittest.TestCase):
    """Alle 9 Regeln (KA1–KA9) müssen definiert sein."""

    def test_alle_regeln_definiert(self):
        for i in range(1, 10):
            key = f"KA{i}"
            self.assertIn(key, gate.REGELN, f"Regel {key} fehlt in REGELN")

    def test_regeln_sind_strings(self):
        for key, val in gate.REGELN.items():
            self.assertIsInstance(val, str, f"Regel {key} ist kein String")
            self.assertGreater(len(val), 5, f"Regel {key} ist zu kurz")


class TestPruefungen(unittest.TestCase):
    """Die Prüffunktionen müssen bei sauberem Repo grün sein."""

    def setUp(self):
        gate.ERGEBNISSE["bereit"].clear()
        gate.ERGEBNISSE["warnung"].clear()
        gate.ERGEBNISSE["defekt"].clear()

    def test_ka2_css_vorhanden(self):
        gate.pruefe_ka2()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA2", bereit)

    def test_ka3_js_vorhanden(self):
        gate.pruefe_ka3()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA3", bereit)

    def test_ka4_shortcode_vorhanden(self):
        gate.pruefe_ka4()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA4", bereit)

    def test_ka5_partial_vorhanden(self):
        gate.pruefe_ka5()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA5", bereit)

    def test_ka6_dsgvo_im_widget(self):
        gate.pruefe_ka6()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA6", bereit)

    def test_ka7_keine_api_keys(self):
        gate.pruefe_ka7()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA7", bereit)

    def test_ka8_kein_tracking(self):
        gate.pruefe_ka8()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA8", bereit)

    def test_ka9_worker_vorhanden(self):
        gate.pruefe_ka9()
        bereit = [e["regel"] for e in gate.ERGEBNISSE["bereit"]]
        self.assertIn("KA9", bereit)


class TestSabotage(unittest.TestCase):
    """Das Gate muss Sabotage erkennen."""

    def test_fehlende_css_wird_erkannt(self):
        css = ROOT / "assets" / "css" / "extended" / "ki-assistent.css"
        if not css.exists():
            self.skipTest("CSS-Datei existiert nicht")
        backup = css.read_bytes()
        css.unlink()
        try:
            gate.ERGEBNISSE["bereit"].clear()
            gate.ERGEBNISSE["warnung"].clear()
            gate.ERGEBNISSE["defekt"].clear()
            gate.pruefe_ka2()
            defekt = [e["regel"] for e in gate.ERGEBNISSE["defekt"]]
            self.assertIn("KA2", defekt)
        finally:
            css.write_bytes(backup)

    def test_fehlende_js_wird_erkannt(self):
        js = ROOT / "static" / "premium" / "ki-assistent.js"
        if not js.exists():
            self.skipTest("JS-Datei existiert nicht")
        backup = js.read_bytes()
        js.unlink()
        try:
            gate.ERGEBNISSE["bereit"].clear()
            gate.ERGEBNISSE["warnung"].clear()
            gate.ERGEBNISSE["defekt"].clear()
            gate.pruefe_ka3()
            defekt = [e["regel"] for e in gate.ERGEBNISSE["defekt"]]
            self.assertIn("KA3", defekt)
        finally:
            js.write_bytes(backup)

    def test_hardcoded_key_wird_erkannt(self):
        js = ROOT / "static" / "premium" / "ki-assistent.js"
        if not js.exists():
            self.skipTest("JS-Datei existiert nicht")
        backup = js.read_bytes()
        text = js.read_text(encoding="utf-8")
        text += '\nconst api_key = "sk-1234567890abcdef1234567890abcdef";\n'
        js.write_text(text, encoding="utf-8")
        try:
            gate.ERGEBNISSE["bereit"].clear()
            gate.ERGEBNISSE["warnung"].clear()
            gate.ERGEBNISSE["defekt"].clear()
            gate.pruefe_ka7()
            defekt = [e["regel"] for e in gate.ERGEBNISSE["defekt"]]
            self.assertIn("KA7", defekt)
        finally:
            js.write_bytes(backup)

    def test_tracking_wird_erkannt(self):
        js = ROOT / "static" / "premium" / "ki-assistent.js"
        if not js.exists():
            self.skipTest("JS-Datei existiert nicht")
        backup = js.read_bytes()
        text = js.read_text(encoding="utf-8")
        text += '\n// google-analytics\n'
        js.write_text(text, encoding="utf-8")
        try:
            gate.ERGEBNISSE["bereit"].clear()
            gate.ERGEBNISSE["warnung"].clear()
            gate.ERGEBNISSE["defekt"].clear()
            gate.pruefe_ka8()
            defekt = [e["regel"] for e in gate.ERGEBNISSE["defekt"]]
            self.assertIn("KA8", defekt)
        finally:
            js.write_bytes(backup)


class TestWorkerKonsistenz(unittest.TestCase):
    """Worker-Code muss konsistent sein."""

    def test_worker_keine_paid_spuren(self):
        worker = ROOT / "cloudflare" / "ki-assistent" / "worker.js"
        if not worker.exists():
            self.skipTest("Worker.js existiert nicht")
        code = worker.read_text(encoding="utf-8")
        self.assertNotIn("OPENAI_API_KEY", code)
        self.assertNotIn("ANTHROPIC_API_KEY", code)

    def test_worker_hat_provider(self):
        worker = ROOT / "cloudflare" / "ki-assistent" / "worker.js"
        if not worker.exists():
            self.skipTest("Worker.js existiert nicht")
        code = worker.read_text(encoding="utf-8")
        for provider in ["groq", "nvidia", "cloudflare", "gemini"]:
            self.assertIn(provider, code,
                          f"Provider '{provider}' fehlt im Worker")

    def test_worker_hat_rate_limit(self):
        worker = ROOT / "cloudflare" / "ki-assistent" / "worker.js"
        if not worker.exists():
            self.skipTest("Worker.js existiert nicht")
        code = worker.read_text(encoding="utf-8")
        self.assertIn("rate", code.lower())
        self.assertIn("limit", code.lower())

    def test_worker_hat_cors(self):
        worker = ROOT / "cloudflare" / "ki-assistent" / "worker.js"
        if not worker.exists():
            self.skipTest("Worker.js existiert nicht")
        code = worker.read_text(encoding="utf-8")
        self.assertIn("CORS", code)
        self.assertIn("Access-Control-Allow-Origin", code)


if __name__ == "__main__":
    unittest.main()