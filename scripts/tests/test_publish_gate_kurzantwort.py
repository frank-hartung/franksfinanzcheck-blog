#!/usr/bin/env python3
"""Vertrag: Publish-Gate blockiert veröffentlichte Posts ohne Kurzantwort.

#1110 (M4, Content-Bot 0b55fca): Ein automatischer Kadenz-/Titel-/Cover-
Lauf entfernte die artikelbezogene `kurzantwort` aus einem bereits
freigegebenen Post, und das Publish-Gate bemerkte es nicht – es gab keine
Prüfung für das Frontmatter-Feld.

Ab sofort gilt: Jeder veröffentlichte Beitrag aus `content/posts/` braucht
ein nicht-leeres `kurzantwort` im Frontmatter. Fehlt es, wird der Kandidat
vom Gate zurückgestellt (neue Artikel werden verworfen, ältere auf
`draft` gehalten; der Content bleibt erhalten).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_gate as pg  # noqa: E402


class KurzantwortGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.posts = self.root / "content" / "posts"
        self.original_posts_dir = pg.POSTS_DIR
        pg.POSTS_DIR = str(self.posts)

    def tearDown(self):
        pg.POSTS_DIR = self.original_posts_dir
        self.tmp.cleanup()

    def write_post(self, slug, kurzantwort=None, draft=False):
        path = self.posts / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        zeilen = ["---", "title: Test", f"draft: {str(draft).lower()}"]
        if kurzantwort is not None:
            zeilen.append(f'kurzantwort: "{kurzantwort}"')
        zeilen += ["---", "", "Ein Satz Fliesstext zum Füllen des Artikels."]
        path.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    def test_ohne_kurzantwort_ist_gate_fund(self):
        self.write_post("2026-11-10-ohne-kurzantwort")
        fehlend, werkzeugfehler = pg.kurzantwort_failures(
            ["2026-11-10-ohne-kurzantwort"]
        )
        self.assertIsNone(werkzeugfehler)
        self.assertIn("2026-11-10-ohne-kurzantwort", fehlend)
        self.assertTrue(any("kurzantwort" in grund for grund in fehlend["2026-11-10-ohne-kurzantwort"]))

    def test_leere_kurzantwort_ist_fehlend(self):
        self.write_post("2026-11-10-leer", kurzantwort="")
        fehlend, _ = pg.kurzantwort_failures(["2026-11-10-leer"])
        self.assertIn("2026-11-10-leer", fehlend)

    def test_mit_kurzantwort_geht_durch(self):
        self.write_post("2026-11-10-mit", kurzantwort="Eine knappe, belastbare Antwort.")
        fehlend, _ = pg.kurzantwort_failures(["2026-11-10-mit"])
        self.assertEqual({}, fehlend)

    # draft:true-Artikel werden bereits durch todays_live_candidates()
    # upstream ausgefiltert und gelangen nie in diese Collector-Funktion –
    # deshalb prüft kurzantwort_failures selbst nicht auf draft (gleiches
    # Muster wie duplicate_failures / uniqueness_failures).
    def test_leere_kandidatenliste_liefert_leeres_ergebnis(self):
        fehlend, _ = pg.kurzantwort_failures([])
        self.assertEqual({}, fehlend)


if __name__ == "__main__":
    unittest.main()
