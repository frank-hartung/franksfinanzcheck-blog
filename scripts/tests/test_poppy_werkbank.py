#!/usr/bin/env python3
"""Regressionstests für die Poppy-Werkbank (kostenloser Poppy.ai-Nachbau).

Friert die Kernversprechen der Werkbank ein – deterministisch und ohne
Netzwerk (alle Pfade in temporären Verzeichnissen):

  1) QUELLE ERKENNEN   – Typ-Erkennung für YouTube/Feed/PDF/Artikel/Notiz
  2) KARTEN            – Roundtrip speichern/laden + Dedupe über Quell-URL
  3) INSIGHTS          – Offline-Heuristik liefert Pillar + Punkte
  4) VERWERTEN         – Offline-Gerüst: draft: true, ki_redaktion: "poppy",
                         TODO-Marker (Promote-Sperre), Karten-Statuswechsel
  5) SOCIAL            – Mastodon/Pinterest-Grenzen werden hart geklemmt
  6) BOARD             – Payload-Zählungen + Platzhalter-Ersetzung
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import poppy_lib as lib  # noqa: E402
import poppy_board  # noqa: E402
import post_utils  # noqa: E402
import poppy_repurpose as rep  # noqa: E402


class WerkbankTempFall(unittest.TestCase):
    """Basis: Karten-Board, Posts-Ordner und Ausgaben ins Temp-Verzeichnis."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="poppy-test-")
        self.alt = {
            "CARD_DIR": lib.CARD_DIR,
            "REPORT_FILE": lib.REPORT_FILE,
            "BOARD_OUTPUT": lib.BOARD_OUTPUT,
            "POSTS_DIR": post_utils.POSTS_DIR,
        }
        lib.CARD_DIR = os.path.join(self.tmp, "cards")
        lib.REPORT_FILE = os.path.join(self.tmp, "report.md")
        lib.BOARD_OUTPUT = os.path.join(self.tmp, "board")
        post_utils.POSTS_DIR = os.path.join(self.tmp, "posts")

    def tearDown(self):
        lib.CARD_DIR = self.alt["CARD_DIR"]
        lib.REPORT_FILE = self.alt["REPORT_FILE"]
        lib.BOARD_OUTPUT = self.alt["BOARD_OUTPUT"]
        post_utils.POSTS_DIR = self.alt["POSTS_DIR"]
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestQuelltypErkennung(unittest.TestCase):
    def test_youtube_video(self):
        for url in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://youtu.be/dQw4w9WgXcQ?t=30",
                    "https://www.youtube.com/shorts/abcdefghijk"):
            self.assertEqual(lib.erkenne_typ(url)[0], "youtube", url)

    def test_youtube_kanal(self):
        for url in ("https://www.youtube.com/@Finanztip/videos",
                    "https://www.youtube.com/@Finanztip",
                    "https://www.youtube.com/feeds/videos.xml?channel_id=UCxx"):
            self.assertEqual(lib.erkenne_typ(url)[0], "youtube_kanal", url)

    def test_feed_und_podcast_präfix(self):
        self.assertEqual(lib.erkenne_typ("https://x.de/feed/")[0], "feed")
        self.assertEqual(lib.erkenne_typ("https://x.de/podcast.rss")[0], "feed")
        typ, wert = lib.erkenne_typ("podcast:https://x.de/feed.xml")
        self.assertEqual(typ, "feed")
        self.assertEqual(wert, "https://x.de/feed.xml")

    def test_pdf_artikel_text(self):
        self.assertEqual(lib.erkenne_typ("https://x.de/bericht.pdf")[0], "pdf")
        self.assertEqual(lib.erkenne_typ("https://x.de/artikel/")[0], "artikel")
        self.assertEqual(lib.erkenne_typ("Freie Notiz von Frank")[0], "text")

    def test_video_id(self):
        self.assertEqual(
            lib.youtube_video_id("https://youtu.be/dQw4w9WgXcQ?t=1"),
            "dQw4w9WgXcQ")
        self.assertEqual(lib.youtube_video_id("https://x.de/"), "")


class TestFeedUndHtmlFallback(unittest.TestCase):
    def test_mini_feed_parser(self):
        xml = ("<?xml version='1.0'?><rss><channel>"
               "<item><title><![CDATA[Gaspreise sinken]]></title>"
               "<link>https://beispiel.de/gas</link>"
               "<description>Laut Quelle sinken die Preise um 5 Prozent.</description>"
               '<enclosure url="https://beispiel.de/ep.mp3" type="audio/mpeg"/>'
               "<pubDate>Tue, 30 Sep 2026 08:00:00 +0200</pubDate></item>"
               "</channel></rss>")
        eintraege = lib.mini_feed_parser(xml)
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0]["titel"], "Gaspreise sinken")
        self.assertTrue(eintraege[0]["audio_url"].endswith(".mp3"))
        self.assertIn("5 Prozent", eintraege[0]["beschreibung"])

    def test_html_lesetext(self):
        html = ("<html><head><title>Strombericht</title></head><body>"
                "<nav>menü</nav>"
                "<p>Die Netzentgelte steigen zum Jahreswechsel spürbar "
                "an, heißt es im Bericht.</p>"
                "<script>alert(1)</script></body></html>")
        text, titel = lib._html_lesetext(html)
        self.assertEqual(titel, "Strombericht")
        self.assertIn("Netzentgelte", text)
        self.assertNotIn("alert", text)
        self.assertNotIn("menü", text)


class TestJsonExtraktion(unittest.TestCase):
    def test_varianten(self):
        for probe in ('{"a": 1}', '```json\n{"a": 1}\n```',
                      'Klar, hier: {"a": 1} – fertig!'):
            self.assertEqual(lib.extrahiere_json(probe), {"a": 1})

    def test_kaputt(self):
        self.assertIsNone(lib.extrahiere_json("gar kein json"))
        self.assertIsNone(lib.extrahiere_json(""))


class TestKarten(WerkbankTempFall):
    def test_roundtrip_und_dedupe(self):
        karte = lib.neue_karte(
            "artikel", titel="Strompreis-Analyse 2026",
            url="https://beispiel.de/strom/", rohtext="Text " * 100,
            methode="trafilatura")
        lib.speichere_karte(karte)
        karten = lib.lade_karten()
        self.assertEqual(len(karten), 1)
        self.assertEqual(karten[0]["id"], karte["id"])
        self.assertEqual(karten[0]["status"], "neu")
        # Dedupe: gleiche URL (auch mit Slash-Variante) wird erkannt
        self.assertTrue(lib.karte_existiert("https://beispiel.de/strom"))
        self.assertFalse(lib.karte_existiert("https://andere.de/x"))

    def test_insights_offline(self):
        karte = lib.neue_karte(
            "text", titel="DSL-Preise im Herbst", url="",
            rohtext="Die DSL-Preise steigen 2026 um durchschnittlich 4 Euro "
                    "pro Monat. Ein Wechsel zum günstigeren Provider spart "
                    "im Jahr rund 48 Euro. Router-Miete kostet oft zusätzlich "
                    "3 Euro im Monat.")
        lib.insights_generieren(karte)  # ohne Key → Heuristik
        self.assertTrue(karte["insights"])
        self.assertEqual(karte["pillar"], "internet-dsl")
        self.assertTrue(karte["winkel"])
        for insight in karte["insights"]:
            self.assertLessEqual(len(insight), 220)

    def test_insights_pillar_fail_closed(self):
        karte = lib.neue_karte("text", titel="x", url="",
                               rohtext="Ein Satz ohne jeden Bezug.")
        lib.insights_generieren(karte)
        self.assertIn(karte["pillar"], lib.lade_pillars() + [""])


class TestVerwertenOffline(WerkbankTempFall):
    def test_kompletter_lauf_geruest(self):
        karte = lib.neue_karte(
            "youtube", titel="Stromtarife wechseln – Video", url="https://youtu.be/x",
            rohtext="Im Video: Neukunden zahlen 2026 laut Beispiel 12 Prozent "
                    "weniger. Wechsel dauert rund drei Wochen.")
        lib.insights_generieren(karte)
        lib.speichere_karte(karte)

        ok = rep.karte_verwerten(karte, offline=True)
        self.assertTrue(ok)
        self.assertEqual(karte["status"], "verwertet")

        slug = karte["erzeugnisse"]["blog"]["slug"]
        pfad = os.path.join(post_utils.POSTS_DIR, slug, "index.md")
        self.assertTrue(os.path.exists(pfad), pfad)
        with open(pfad, encoding="utf-8") as fh:
            inhalt = fh.read()
        self.assertRegex(inhalt, r"(?m)^draft:\s*true$")
        self.assertIn('ki_redaktion: "poppy"', inhalt)
        # Promote-Sperre: Offline-Gerüste tragen TODO-Marker
        self.assertIn("TODO(KI-REDAKTION", inhalt)
        # Kategorie/Tags nach Repo-Konvention
        self.assertRegex(inhalt, r"(?m)^categories:")

    def test_social_grenzen(self):
        karte = lib.neue_karte(
            "text", titel="Sehr langer Titel über Stromkosten im Jahr 2026",
            url="", rohtext="Stromkosten sinken um 10 Prozent laut Beispiel.")
        karte["insights"] = ["Laut Beispiel sinken die Stromkosten um "
                             "10 Prozent."]
        sozial = rep.sozial_texte_generieren(karte, "test-slug", offline=True)
        self.assertLessEqual(len(sozial["mastodon"]), 470)
        self.assertIn("https://franksfinanzcheck.de/posts/test-slug/",
                      sozial["artikel_url"])
        self.assertLessEqual(len(sozial["pinterest"]["titel"]), 100)
        self.assertLessEqual(len(sozial["pinterest"]["beschreibung"]), 490)
        self.assertTrue(sozial["newsletter"]["betreff"])
        self.assertLessEqual(len(sozial["newsletter"]["betreff"]), 70)

    def test_prompts_quellenverwurzelt(self):
        # Anti-Halluzinations-Versprechen: Brief nennt Quelle + Insights
        karte = {"quelle": {"titel": "Quelle X", "typ": "artikel",
                            "url": "https://q.de/x", "autor": "Institut Y"},
                 "insights": ["Zahl A"], "schlagworte": ["Strom"],
                 "pillar": "strom-sparen", "artikel_titel": "Strom sparen",
                 "winkel": "w", "inhalt": {"rohtext": "Beispieltext."}}
        brief = rep._brief(karte)
        self.assertIn("Quelle X", brief)
        self.assertIn("Zahl A", brief)
        self.assertIn("ERFINDE NIEMALS", rep.SYSTEM_PROMPT)


class TestBoard(WerkbankTempFall):
    def test_payload_und_html(self):
        neu = lib.neue_karte("youtube", titel="NeuVideo", url="https://youtu.be/a",
                             rohtext="x" * 50)
        neu["insights"] = ["Punkt 1"]
        fertig = lib.neue_karte("pdf", titel="FertigPDF", url="https://x.de/f.pdf",
                                rohtext="y" * 50)
        fertig["status"] = "verwertet"
        fertig["erzeugnisse"] = {"blog": {"slug": "s", "zeichen": 1000,
                                          "freigabe": "cmd"}, "mastodon": "m",
                                 "newsletter": {"betreff": "b", "text": "t"},
                                 "pinterest": {"titel": "p", "beschreibung": "d"}}
        lib.speichere_karte(neu)
        lib.speichere_karte(fertig)

        payload = poppy_board.board_payload()
        self.assertEqual(payload["gesamt"], 2)
        self.assertEqual(payload["neu"], 1)
        self.assertEqual(payload["verwertet"], 1)

        pfad = poppy_board.board_bauen(payload, os.path.join(self.tmp, "out"))
        with open(pfad, encoding="utf-8") as fh:
            html = fh.read()
        self.assertNotIn("/*BOARD_DATA*/", html)   # Platzhalter ersetzt
        self.assertIn("NeuVideo", html)
        self.assertIn("FertigPDF", html)
        for name in ("app.js", "style.css", "board.json"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "out", name)))

    def test_vorlage_im_repo_vollständig(self):
        for name in ("index.html", "app.js", "style.css"):
            pfad = os.path.join(BLOG_DIR, "tools", "poppy-board", name)
            self.assertTrue(os.path.exists(pfad), pfad)
        with open(os.path.join(BLOG_DIR, "tools", "poppy-board", "index.html"),
                  encoding="utf-8") as fh:
            self.assertIn("/*BOARD_DATA*/", fh.read())


if __name__ == "__main__":
    unittest.main()
