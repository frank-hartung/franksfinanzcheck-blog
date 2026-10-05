#!/usr/bin/env python3
"""Regressionstests für WF-54C4/#583.

Ein best-effort-Recherchelauf darf einen neuen `draft: false`-Artikel nicht
bis zur Release-Scorecard durchreichen. Publish-Gate und Scorecard nutzen den
selben, reinen Collector; ein fehlender Nachweis ist ein Befund, ein defekter
Beweisweg ein Werkzeugfehler.
"""
from __future__ import annotations

import datetime as dt
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_gate  # noqa: E402
import faktenfrische  # noqa: E402


class FaktenfrischeCollectorTests(unittest.TestCase):
    def fake_module(self, articles):
        module = types.SimpleNamespace()
        module.lade_config = lambda: {"intervalle": {"standard_tage": 90}}
        module.alle_artikel = lambda scope: articles

        def faelligkeit(article, cfg, stichtag=None):
            if article.get("faktencheck") is None:
                return {"faellig": True, "grund": "Erstrecherche – noch nie faktengeprüft"}
            if article["faktencheck"] <= dt.date(2026, 7, 1):
                return {"faellig": True, "grund": "95 Tage seit letzter Prüfung"}
            return {"faellig": False, "grund": "frisch geprüft"}

        module.faelligkeit = faelligkeit
        return module

    def test_fehlender_faktencheck_blockiert_kandidaten(self):
        fake = self.fake_module([{
            "slug": "2026-10-05-neu", "faktencheck": None,
        }])
        with patch.dict(sys.modules, {"faktenfrische": fake}):
            failures, warning, tool_error = publish_gate.faktenfrische_failures(
                ["2026-10-05-neu"], stichtag=dt.date(2026, 10, 5))

        self.assertFalse(tool_error)
        self.assertIsNone(warning)
        self.assertIn("2026-10-05-neu", failures)
        self.assertIn("Erstrecherche", failures["2026-10-05-neu"][0])

    def test_ueberfaelliger_faktencheck_blockiert_kandidaten(self):
        fake = self.fake_module([{
            "slug": "alter-kandidat", "faktencheck": dt.date(2026, 6, 1),
        }])
        with patch.dict(sys.modules, {"faktenfrische": fake}):
            failures, warning, tool_error = publish_gate.faktenfrische_failures(
                ["alter-kandidat"], stichtag=dt.date(2026, 10, 5))

        self.assertFalse(tool_error)
        self.assertIsNone(warning)
        self.assertIn("alter-kandidat", failures)

    def test_unbekannter_kandidat_ist_fail_closed(self):
        fake = self.fake_module([])
        with patch.dict(sys.modules, {"faktenfrische": fake}):
            failures, warning, tool_error = publish_gate.faktenfrische_failures(
                ["nicht-lesbar"], stichtag=dt.date(2026, 10, 5))

        self.assertEqual(failures, {})
        self.assertTrue(tool_error)
        self.assertIn("nicht-lesbar", warning)

    def test_frischer_faktencheck_passiert(self):
        fake = self.fake_module([{
            "slug": "frisch", "faktencheck": dt.date(2026, 9, 30),
        }])
        with patch.dict(sys.modules, {"faktenfrische": fake}):
            failures, warning, tool_error = publish_gate.faktenfrische_failures(
                ["frisch"], stichtag=dt.date(2026, 10, 5))

        self.assertEqual(failures, {})
        self.assertIsNone(warning)
        self.assertFalse(tool_error)

    def test_erfolgreiche_recherche_rearmt_nur_fakten_hold(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hold" / "index.md"
            path.parent.mkdir()
            path.write_text(
                "---\n"
                "title: Hold\n"
                "draft: true\n"
                "cadence_demoted: 2026-10-05T12:00:00Z\n"
                'cadence_grund: "faktenfrische: Erstrecherche"\n'
                "---\nText.\n",
                encoding="utf-8",
            )
            art = {"pfad": str(path), "slug": "hold",
                   "cadence_grund": "faktenfrische: Erstrecherche"}

            self.assertTrue(faktenfrische.rearm_faktenfrische_hold(
                art, "faktencheck: 2026-10-05"))
            text = path.read_text(encoding="utf-8")
            self.assertIn("cadence_wait: true", text)
            self.assertIn("faktenfrische aufgehoben", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
