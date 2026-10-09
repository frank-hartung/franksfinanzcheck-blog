#!/usr/bin/env python3
"""Verträge für die gemeinsame Duplikat-Messung von Publish-Gate und Scorecard.

WF-54C4 / #674: Eine doppelte CTA wurde erst in der Release-Scorecard
gefunden, obwohl der Publish-Pfad zuvor grün war. Diese Tests sichern zwei
Dinge: Der Publish-Collector prüft Kandidaten gegen den gesamten Bestand und
bei Cross-Artikel-Funden zählt jede betroffene Seite – unabhängig von der
lexikografischen Pfadreihenfolge.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_gate as pg  # noqa: E402


class DuplicateCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.posts = self.root / "content" / "posts"
        self.original_posts_dir = pg.POSTS_DIR
        pg.POSTS_DIR = str(self.posts)

    def tearDown(self):
        pg.POSTS_DIR = self.original_posts_dir
        self.tmp.cleanup()

    def write_post(self, slug: str, body: str) -> None:
        path = self.posts / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\ntitle: Test\ndraft: false\n---\n\n" + body + "\n",
            encoding="utf-8",
        )

    def test_cross_fund_blockiert_den_lexikografisch_zweiten_kandidaten(self):
        # Der historische Bug schrieb D3/D4 nur rel_a zu. Der Kandidat ist
        # hier absichtlich rel_b und muss trotzdem einen harten Befund tragen.
        repeated = (
            "Diese eigenständige, ausreichend lange Passage darf nicht in zwei "
            "Artikeln stehen, weil Leser dann dieselbe Information doppelt lesen."
        )
        self.write_post("2026-10-01-bestand", repeated)
        candidate = "2026-10-09-kandidat"
        self.write_post(candidate, repeated)

        failures, tool_error = pg.duplicate_failures([candidate])

        self.assertIsNone(tool_error)
        self.assertIn(candidate, failures)
        self.assertTrue(any(detail.startswith("D3-X:")
                            for detail in failures[candidate]))

    def test_unbeteiligte_bestandsduplikate_blockieren_keinen_kandidaten(self):
        repeated = (
            "Dieser alte, lange Bestandssatz ist absichtlich doppelt, damit der "
            "Collector seine Prüfung gegen unbeteiligte Kandidaten beweisen kann."
        )
        self.write_post("2026-09-01-alt-a", repeated)
        self.write_post("2026-09-02-alt-b", repeated)
        candidate = "2026-10-09-eigenstaendig"
        self.write_post(candidate, "Dieser Kandidat bringt einen eigenen, klaren Gedanken mit.")

        failures, tool_error = pg.duplicate_failures([candidate])

        self.assertIsNone(tool_error)
        self.assertEqual({}, failures)

    def test_674_tagesgeld_cta_ist_gegen_den_bestand_eigenstaendig(self):
        """Die konkrete Reparatur bleibt vor einem Rückfall geschützt."""
        slug = "2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit"
        failures, tool_error = pg.duplicate_failures([slug])

        self.assertIsNone(tool_error)
        self.assertNotIn(slug, failures)


if __name__ == "__main__":
    unittest.main()
