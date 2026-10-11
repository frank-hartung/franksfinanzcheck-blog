#!/usr/bin/env python3
"""Regressionstests: Selbsttests von GSC-Import, Klick-Import und Klick-Attribution (offline)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gsc_import  # noqa: E402
import klick_import  # noqa: E402


class GscImportTest(unittest.TestCase):
    def test_selbsttest_bestanden(self):
        self.assertEqual(gsc_import._selftest(), 0)

    def test_ohne_zugang_status_nicht_konfiguriert(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            meta = gsc_import.lauf(7, env={}, out_dir=Path(tmp))
        self.assertEqual(meta["status"], "nicht_konfiguriert")


class KlickImportTest(unittest.TestCase):
    def test_selbsttest_bestanden(self):
        self.assertEqual(klick_import._selftest(), 0)

    def test_schluessel_drift_frei(self):
        self.assertTrue(klick_import.pruefe_keys())


class WranglerTomlTest(unittest.TestCase):
    def test_routes_vor_tabellen(self):
        text = (ROOT / "cloudflare" / "klick-zaehler" / "wrangler.toml").read_text(encoding="utf-8")
        zeilen = [z.strip() for z in text.splitlines()]
        routes = next(i for i, z in enumerate(zeilen) if z.startswith("routes ="))
        tabellen = [i for i, z in enumerate(zeilen) if z.startswith("[")]
        self.assertTrue(not tabellen or routes < tabellen[0])


if __name__ == "__main__":
    unittest.main()
