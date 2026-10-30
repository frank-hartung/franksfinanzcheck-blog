"""#900: Bytegebundene Reserve-Entwürfe sind für Hygiene-Heiler schreibgeschützt.

Der Vorfall: `data/reserve-readiness.json` belegte drei Reserve-Entwürfe mit
ihrer SHA-256. Danach heilte der Pinterest-Watchdog dieselben Dateien
(Transparenz-Zeile via `spam_guard`, gekürzte `keywords` via Pin-Heiler) und
committete sie – der Nachweis zeigte auf Bytes, die es nicht mehr gab. Beide
Vorgänge waren für sich „grün“; der Widerspruch fiel erst im nächsten Gate auf.

Diese Tests halten die Regel fest, die den Fehler an der Wurzel schließt:

  · `draft: true` **und** `reserve: true` = bytegebunden → Heiler schreiben nicht.
  · die Heiler verschweigen den Fund nicht, sie melden ihn.
  · ohne die zweite Marke bleibt der Heiler scharf (kein stiller Ausfall der
    Heilung – ein Schutz, der zu viel sperrt, wäre derselbe Fehler andersherum).
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import reserve_schreibschutz as schutz  # noqa: E402
import spam_guard as sg  # noqa: E402
import pinterest_duplicate_guard as pdg  # noqa: E402
import pinterest_seo_healer as seo  # noqa: E402

RESERVE_ENTWURF = """---
title: "Testartikel"
draft: true
reserve: true
pin_description: "Alter Pin-Text"
keywords: ["A", "B"]
---

Erster Absatz mit Inhalt.
"""

NORMALER_ENTWURF = RESERVE_ENTWURF.replace("reserve: true\n", "")
LIVE_ARTIKEL = RESERVE_ENTWURF.replace("draft: true\n", "")


class RegelTest(unittest.TestCase):
    """Die Marke selbst: zwei Zeilen, beide nötig, Reihenfolge egal."""

    def test_beide_marken_ergeben_bytebindung(self):
        self.assertTrue(schutz.ist_bytegebunden(RESERVE_ENTWURF))

    def test_nur_draft_ist_kein_reserve_entwurf(self):
        self.assertFalse(schutz.ist_bytegebunden(NORMALER_ENTWURF))

    def test_nur_reserve_ist_kein_entwurf(self):
        self.assertFalse(schutz.ist_bytegebunden(LIVE_ARTIKEL))

    def test_ohne_frontmatter_kein_schutz(self):
        self.assertFalse(schutz.ist_bytegebunden(""))
        self.assertFalse(schutz.ist_bytegebunden("# Nur Markdown\n\nText.\n"))

    def test_windows_zeilenenden_brechen_die_marke_nicht(self):
        self.assertTrue(schutz.ist_bytegebunden(
            RESERVE_ENTWURF.replace("\n", "\r\n")))

    def test_marken_ausserhalb_des_frontmatters_zaehlen_nicht(self):
        text = ("---\ntitle: \"X\"\ndraft: true\n---\n\nreserve: true\n")
        self.assertFalse(schutz.ist_bytegebunden(text))

    def test_geschuetzte_slugs_findet_nur_reserve_entwuerfe(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            for slug, inhalt in (("reserve", RESERVE_ENTWURF),
                                 ("entwurf", NORMALER_ENTWURF),
                                 ("live", LIVE_ARTIKEL)):
                (wurzel / slug).mkdir()
                (wurzel / slug / "index.md").write_text(inhalt, encoding="utf-8")
            self.assertEqual({"reserve"}, schutz.geschuetzte_slugs(wurzel))


class SpamGuardTest(unittest.TestCase):
    """B3/B8: Der Heiler, der die Transparenz-Zeile in den Entwurf schrieb."""

    def _fix(self, inhalt, regel="B3"):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "index.md"
            pfad.write_text(inhalt, encoding="utf-8")
            post = {"slug": "kandidat", "path": str(pfad), "content": inhalt}
            with patch.object(sg, "DRY_RUN", False), \
                    patch.object(sg, "audit", lambda *_a, **_k: None):
                geheilt = sg.fix_blog({"kandidat": (post, [(regel, "hard", "Test")])})
            return pfad.read_bytes(), inhalt.encode("utf-8"), geheilt

    def test_reserve_entwurf_bleibt_bytegleich(self):
        danach, vorher, geheilt = self._fix(RESERVE_ENTWURF)
        self.assertEqual(vorher, danach, "bytegebundener Entwurf wurde geschrieben")
        self.assertTrue(any("unangetastet" in zeile for zeile in geheilt),
                        geheilt)

    def test_normaler_entwurf_wird_weiterhin_geheilt(self):
        danach, vorher, _geheilt = self._fix(NORMALER_ENTWURF)
        self.assertNotEqual(vorher, danach, "Heilung ist ausgefallen")
        self.assertIn("Transparenz", danach.decode("utf-8"))


class DuplicateGuardTest(unittest.TestCase):
    """Der Heiler, der die `keywords` der zertifizierten Entwürfe kürzte."""

    def _run(self, inhalt_reserve):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            posts = wurzel / "content" / "posts"
            for slug, inhalt in (("erst", RESERVE_ENTWURF.replace(
                                      "Alter Pin-Text", "Gleicher Text")),
                                 ("zweit", inhalt_reserve)):
                (posts / slug).mkdir(parents=True)
                (posts / slug / "index.md").write_text(inhalt, encoding="utf-8")
            with patch.object(pdg, "BLOG_DIR", str(wurzel)), \
                    patch.object(pdg, "DO_FIX", True):
                pdg.main()
            return (posts / "zweit" / "index.md").read_text(encoding="utf-8")

    def test_reserve_entwurf_behaelt_seinen_pin_text(self):
        vorher = RESERVE_ENTWURF.replace("Alter Pin-Text", "Gleicher Text")
        self.assertEqual(vorher, self._run(vorher))

    def test_normaler_entwurf_wird_weiterhin_eindeutig(self):
        nachher = self._run(NORMALER_ENTWURF.replace("Alter Pin-Text",
                                                     "Gleicher Text"))
        self.assertNotIn('"Gleicher Text"', nachher,
                         "Der Guard hat den normalen Entwurf nicht mehr geheilt")


class SeoHealerTest(unittest.TestCase):
    def test_heal_article_verweigert_reserve_entwurf(self):
        artikel = {"slug": "kandidat", "reserve": True, "content": RESERVE_ENTWURF,
                   "path": "/tmp/nie-geschrieben.md", "title": "Testartikel"}
        geaendert, aktionen = seo.heal_article(artikel)
        self.assertFalse(geaendert)
        self.assertTrue(any("unangetastet" in a for a in aktionen), aktionen)

    def test_load_articles_setzt_die_marke_aus_dem_frontmatter(self):
        quelle = (SCRIPTS / "pinterest_seo_healer.py").read_text(encoding="utf-8")
        self.assertIn('"reserve": schutz.ist_bytegebunden(content)', quelle)


class VertragTest(unittest.TestCase):
    """Strukturvertrag: keine der drei Dateien darf den Haken wieder verlieren."""

    DATEIEN = ("spam_guard.py", "pinterest_duplicate_guard.py",
               "pinterest_seo_healer.py")

    def test_jeder_heiler_fragt_den_schutz(self):
        for name in self.DATEIEN:
            with self.subTest(datei=name):
                quelle = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertIn("reserve_schreibschutz", quelle)
                self.assertIn("ist_bytegebunden", quelle)


if __name__ == "__main__":
    unittest.main()
