#!/usr/bin/env python3
"""Regression: Weiterleitungsstubs sind keine Inhaltsseiten für layout_audit.

19.10.2026: Die 114 Stubs aus scripts/weiterleitungen.py (Marker
ff-weiterleitung, noindex, ohne Beschreibung) meldete der Layout-Audit als
kritisch („Meta-Description fehlt auf 114 Seiten“) und blockierte damit den
Job layout-audit. Der Test prüft beides: Stubs werden übersprungen, echte
Inhaltsseiten ohne Beschreibung bleiben kritisch.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_audit as la  # noqa: E402

STUB = (
    '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
    '<meta name="ff-weiterleitung" content="regel-C">'
    '<meta name="robots" content="noindex,follow">'
    '<meta http-equiv="refresh" content="0; url=https://franksfinanzcheck.de/x/">'
    '<title>Diese Seite ist umgezogen</title></head><body><h1>Umgezogen</h1></body></html>'
)
INHALT_OHNE_BESCHREIBUNG = (
    '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
    '<title>Artikel</title></head><body><h1>Artikel</h1></body></html>'
)


class StubsAusgenommenTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._alt = (la.BASE, list(la.CRITICAL), list(la.WARN), list(la.OK))
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "public"
        la.BASE = str(self.base)
        la.CRITICAL.clear(); la.WARN.clear(); la.OK.clear()

    def tearDown(self) -> None:
        la.BASE = self._alt[0]
        la.CRITICAL[:] = self._alt[1]; la.WARN[:] = self._alt[2]; la.OK[:] = self._alt[3]
        self._tmp.cleanup()

    def _seite(self, slug: str, text: str) -> None:
        d = self.base / "posts" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(text, encoding="utf-8")

    def test_stub_ist_kein_kritischer_befund(self) -> None:
        self._seite("alt-adresse", STUB)
        self._seite("alt-adresse-2", STUB)
        la.check_schema_and_meta()
        self.assertEqual(la.CRITICAL, [], f"Stubs dürfen nicht kritisch sein: {la.CRITICAL}")

    def test_inhaltsseite_ohne_beschreibung_bleibt_kritisch(self) -> None:
        self._seite("alt-adresse", STUB)
        self._seite("artikel", INHALT_OHNE_BESCHREIBUNG)
        la.check_schema_and_meta()
        self.assertEqual(la.CRITICAL, ["Meta-Description fehlt auf 1 Seiten."])

    def test_stubs_werden_in_der_ok_zeile_genannt(self) -> None:
        self._seite("alt-adresse", STUB)
        la.check_schema_and_meta()
        self.assertTrue(any("1 Weiterleitungsstubs ausgenommen" in z for z in la.OK), la.OK)


if __name__ == "__main__":
    unittest.main()
