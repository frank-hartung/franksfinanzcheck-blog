#!/usr/bin/env python3
"""Regressionstests für die Linktext-/Alt-Wache (SEO-Sicht, 27.10.2026)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import linktext_wache as wache  # noqa: E402


class LinktextTests(unittest.TestCase):
    def test_overlay_link_mit_aria_label_ist_ein_befund(self):
        """Der Seobility-Befund: Linktext nur im Attribut ist kein Linktext."""
        html = ('<main><h1>T</h1><a class="entry-link" aria-label="Weiterlesen: Karte" '
                'href="/karte/"></a></main>')
        befunde, statistik = wache.pruefe_html(html)
        self.assertTrue(any(b.startswith("L1:") and "/karte/" in b for b in befunde))
        self.assertEqual(statistik["ohne_text"], 1)

    def test_titelanker_ist_sauber(self):
        html = ('<main><h1>T</h1><article class="post-entry"><h2>'
                '<a class="entry-title-link" href="/karte/">Karte lesen</a></h2></article></main>')
        self.assertEqual(wache.pruefe_html(html)[0], [])

    def test_bild_im_link_traegt_den_text(self):
        html = '<main><h1>T</h1><a href="/x/"><img src="/a.jpg" alt="Ein Bild"></a></main>'
        self.assertEqual(wache.pruefe_html(html)[0], [])

    def test_bild_ohne_alt_ist_kein_linktext(self):
        html = '<main><h1>T</h1><a href="/x/"><img src="/a.jpg"></a></main>'
        befunde, _ = wache.pruefe_html(html)
        self.assertTrue(any(b.startswith("L1:") for b in befunde))
        self.assertTrue(any(b.startswith("L2:") for b in befunde))

    def test_svg_ist_kein_linktext(self):
        html = ('<main><h1>T</h1><a href="/x/"><svg viewBox="0 0 1 1">'
                '<path d="M0 0"></path></svg></a></main>')
        befunde, _ = wache.pruefe_html(html)
        self.assertTrue(any(b.startswith("L1:") for b in befunde))

    def test_sprungziel_ohne_href_ist_kein_link(self):
        html = '<main><h1>T</h1><a id="partner-kennzeichnung"></a></main>'
        self.assertEqual(wache.pruefe_html(html)[0], [])

    def test_bewusste_ausnahme_wird_respektiert(self):
        html = ('<main><h1>T</h1><a href="/karte/" data-ff-linktext-frei '
                'aria-label="Karte"></a></main>')
        self.assertEqual(wache.pruefe_html(html)[0], [])

    def test_noscript_linktext_zaehlt(self):
        """Ohne JavaScript-Crawl ist der noscript-Inhalt sichtbar."""
        html = ('<main><h1>T</h1><noscript><p><a href="/posts/">Blog</a></p>'
                '</noscript></main>')
        self.assertEqual(wache.pruefe_html(html)[0], [])

    def test_dekoratives_alt_ist_hinweis_und_kein_fehler(self):
        html = '<main><h1>T</h1><img src="/logo.svg" alt=""></main>'
        befunde, statistik = wache.pruefe_html(html)
        self.assertEqual(befunde, [])
        self.assertEqual(statistik["alt_leer"], 1)

    def test_langer_ankertext_ist_hinweis_und_kein_fehler(self):
        lang = " ".join(["Wort"] * 20)
        html = f'<main><h1>T</h1><a href="/x/">{lang}</a></main>'
        befunde, statistik = wache.pruefe_html(html)
        self.assertEqual(befunde, [])
        self.assertEqual(statistik["lang"], 1)


class KartenlinkTests(unittest.TestCase):
    """L4: Kartenlinks müssen kurz sein – redaktionelle Links nicht."""

    LANG = "Ein Kartenlink, der Titel, Anriss, Zähler und Handlungsaufforderung in einem einzigen Linknamen vereint"

    def test_kartenlink_ueber_grenze_ist_ein_befund(self):
        html = (f'<main><h1>T</h1><a class="ff-topic-card__title-link" '
                f'href="/x/">{self.LANG}</a></main>')
        befunde, statistik = wache.pruefe_html(html)
        self.assertTrue(any(b.startswith("L4:") for b in befunde), befunde)
        self.assertEqual(statistik["zu_lang"], 1)

    def test_redaktioneller_link_darf_lang_sein(self):
        """Fließtext, Inhaltsverzeichnis und Quellen sind keine Karten."""
        for klasse in ("ff-quellen__link", "", "toc-link"):
            with self.subTest(klasse=klasse):
                attr = f' class="{klasse}"' if klasse else ""
                html = f'<main><h1>T</h1><a{attr} href="/x/">{self.LANG}</a></main>'
                befunde, _ = wache.pruefe_html(html)
                self.assertEqual(befunde, [])

    def test_noindex_seite_ist_ausgenommen(self):
        """Die /go/-Weiterleitungen nennen ihr Ziel ausführlich und ehrlich –
        sie sind noindex,nofollow, also kein Ranking-Signal."""
        html = ('<head><meta name="robots" content="noindex,nofollow"></head>'
                f'<main><h1>T</h1><a class="ff-related-card__title-link" href="/x/">{self.LANG}</a></main>')
        befunde, _ = wache.pruefe_html(html)
        self.assertEqual(befunde, [])

    def test_kartenlink_unter_grenze_ist_sauber(self):
        html = ('<main><h1>T</h1><a class="ff-saison-card__titel-link" '
                'href="/x/">Heizkosten senken: Strategien</a></main>')
        befunde, _ = wache.pruefe_html(html)
        self.assertEqual(befunde, [])


class BuildTests(unittest.TestCase):
    def _seite(self, root: Path, name: str, html: str) -> None:
        pfad = root / name
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(html, encoding="utf-8")

    def test_build_pruefung_meldet_datei_und_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            self._seite(public, "index.html", '<main><h1>T</h1><a href="/x/" aria-label="x"></a></main>')
            self._seite(public, "posts/index.html", '<main><h1>T</h1><a href="/x/">Text</a></main>')
            ergebnis = wache.pruefe_build(public)
        self.assertEqual(ergebnis["seiten"], 2)
        self.assertEqual(len(ergebnis["befunde"]), 1)
        self.assertIn("index.html", ergebnis["befunde"][0])
        self.assertIn("L1:", ergebnis["befunde"][0])

    def test_fehlendes_build_ist_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ergebnis = wache.pruefe_build(Path(tmp) / "gibt-es-nicht")
        self.assertTrue(ergebnis["befunde"])
        self.assertEqual(ergebnis["statistik"], {})

    def test_main_liefert_exitcode_und_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            self._seite(public, "index.html", '<main><h1>T</h1><a href="/x/">Text</a></main>')
            with redirect_stdout(StringIO()):
                self.assertEqual(wache.main(["--public", str(public), "--json"]), 0)
                self._seite(public, "kaputt.html", '<main><h1>T</h1><img src="/y.jpg"></main>')
                self.assertEqual(wache.main(["--public", str(public), "--json"]), 1)
                ausgabe = StringIO()
                with redirect_stdout(ausgabe):
                    wache.main(["--public", str(public), "--json"])
                daten = json.loads(ausgabe.getvalue())
        self.assertTrue(any("L2:" in b for b in daten["befunde"]))

    def test_selftest_ist_gruen(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(wache.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
