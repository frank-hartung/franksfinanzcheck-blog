#!/usr/bin/env python3
"""Vertragstests für die Suche (Pagefind, 08.10.2026).

Geprüft wird die Verdrahtung, nicht das Ranking:
  · Pagefind ist exakt gepinnt (kein ^ und kein ~) – Lockfile und package.json
  · der Index wird im Deploy nach dem letzten Hugo-Build und vor der
    Veröffentlichung gebaut, fail-closed
  · die Suchseite ist aus Index und Sitemap ausgeschlossen (noindex)
  · das Such-Skript setzt nie HTML aus Fremdtext ein und lädt nichts von
    fremden Hosts; die Eingabe wandert nicht per GET in die URL
  · der Newsletter-Streifen bleibt ein Block pro Seite

Aufruf:  python3 -m unittest scripts.tests.test_suche_pagefind
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def lies(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def ohne_js_kommentare(js: str) -> str:
    """Blockkommentare und Zeilenkommentare entfernen: geprüft wird Code, nicht Begründung."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", js)


class PagefindVertrag(unittest.TestCase):
    def test_version_ist_exakt_gepinnt(self):
        pkg = json.loads(lies("package.json"))
        self.assertEqual(pkg["dependencies"]["pagefind"], "1.5.2",
                         "exakt pinnen: kein ^ und kein ~ bei einem Such-Werkzeug im Deploy")
        lock = json.loads(lies("package-lock.json"))
        self.assertEqual(lock["packages"][""]["dependencies"]["pagefind"], "1.5.2")
        self.assertIn("node_modules/pagefind", lock["packages"])

    def test_suchindex_skript_baut_public(self):
        pkg = json.loads(lies("package.json"))
        self.assertIn("--site public", pkg["scripts"]["suchindex"])
        self.assertIn("--force-language de", pkg["scripts"]["suchindex"])

    def test_deploy_baut_index_nach_hugo_und_vor_veroeffentlichung(self):
        wf = lies(".github/workflows/deploy.yml")
        i_index = wf.index("name: Suchindex bauen (Pagefind)")
        i_gh = wf.index("name: Deploy auf gh-pages")
        self.assertLess(i_index, i_gh, "der Index muss vor dem gh-pages-Deploy entstehen")
        zwischen = wf[i_index:i_gh]
        self.assertNotIn("hugo", zwischen, "nach dem Index darf nichts mehr neu bauen")
        self.assertIn("npm run --silent suchindex", zwischen)
        self.assertIn("set -euo pipefail", zwischen)
        self.assertIn("test -s public/pagefind/pagefind.js", zwischen, "fail-closed: ohne Index kein Deploy")

    def test_baseof_indexiert_nur_den_inhalt(self):
        base = lies("layouts/baseof.html")
        self.assertIn('id="main-content" data-pagefind-body', base,
                      "nur <main> wird indexiert – sonst Navigation und Footer in jeder Suche")
        self.assertIn('data-pagefind-ignore="all"', base)
        self.assertIn('hasPrefix .RelPermalink "/suche/"', base)
        self.assertIn("with .Paginator", base)
        self.assertIn("gt .PageNumber 1", base,
                      "Blätterseiten ab Seite 2 bleiben aus dem Index")
        self.assertIn("$listenseite", base,
                      "der Paginator wird nur auf Listenseiten abgefragt (404 wirft sonst einen Fehler)")
        self.assertIn('partial "seo_indexierbar.html" .', base,
                      "noindex-Seiten (404, Newsletter-Abmeldung) gehören nicht in die Suche – "
                      "dieselbe Quelle wie robots-Meta und Sitemap")

    def test_suchseite_ist_aus_index_und_sitemap(self):
        seite = lies("content/suche/index.md")
        self.assertIn("robotsNoIndex: true", seite)
        self.assertIn("sitemap:\n  disable: true", seite)
        self.assertIn("{{< suche >}}", seite)

    def test_footer_verlinkt_die_suche(self):
        footer = lies("layouts/_partials/footer.html")
        self.assertIn('<a href="{{ "suche/" | absURL }}">Suche</a>', footer)

    def test_formular_ohne_get_uebergabe_und_ohne_innerhtml(self):
        sc = lies("layouts/shortcodes/suche.html")
        formular = re.search(r"<form[^>]*>", sc)
        self.assertIsNotNone(formular)
        self.assertNotIn("action=", formular.group(0), "kein GET-Submit: die Eingabe bliebe in der URL")
        self.assertIn("hidden", formular.group(0), "ohne JavaScript bleibt das Formular verborgen")
        js = ohne_js_kommentare(lies("static/premium/ff-suche.js"))
        for verboten in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(verboten, js, f"{verboten} setzt Fremdtext als HTML ein")
        self.assertIn("preventDefault", js, "die Eingabe wird im Skript abgefangen")

    def test_js_laedt_nichts_von_fremden_hosts(self):
        js = ohne_js_kommentare(lies("static/premium/ff-suche.js"))
        self.assertIsNone(re.search(r"https?://", js), "keine externen Hosts im Such-Skript")

    def test_js_ohne_tracking_und_speicher(self):
        js = ohne_js_kommentare(lies("static/premium/ff-suche.js"))
        for wort in ("umami", "localStorage", "sessionStorage", "document.cookie", "sendBeacon"):
            self.assertNotIn(wort, js, f"{wort} ist im Such-Skript nicht erlaubt")

    def test_werkzeug_streifen_bleibt_ein_block_pro_seite(self):
        streifen = lies("layouts/_partials/newsletter_strip.html")
        self.assertIn("$werkzeug", streifen)
        self.assertIn("Dienstags", streifen, "Werkzeug-Zusage nennt den Dienstag")
        self.assertIn("Freitags", streifen, "Werkzeug-Zusage nennt den Freitag")
        self.assertEqual(streifen.count('class="newsletter-footer ff-nl-strip"'), 1,
                         "genau ein Anmeldeblock-Wrapper – kein zweiter Hinweis pro Seite")
        self.assertEqual(streifen.count('<p class="ff-nl-strip__text">'), 2,
                         "ein Textzweig für Werkzeuge, einer für alle übrigen Seiten")

    def test_css_liegt_in_extended(self):
        self.assertTrue((ROOT / "assets/css/extended/ff-suche.css").exists(),
                        "PaperMod bindet css/extended/*.css automatisch ein")


if __name__ == "__main__":
    unittest.main()
