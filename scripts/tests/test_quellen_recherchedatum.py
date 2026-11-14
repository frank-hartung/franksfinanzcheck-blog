"""Eine nachgetragene Quelle bekommt keinen erfundenen alten Recherchezeitpunkt."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml
from scripts import faktenfrische

ROOT = Path(__file__).resolve().parents[2]
HUGO = os.environ.get("HUGO_BIN", "hugo")


@unittest.skipUnless(shutil.which(HUGO), "Hugo nicht installiert")
class QuellenDatumRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)

        def write(pfad, text):
            ziel = cls.root / pfad
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(text, encoding="utf-8")

        write("hugo.toml", 'baseURL = "https://example.org/"\ntitle = "Test"\n')
        for partial in ("ff_quellen_box.html", "schema_article.html", "article_dates.html",
                        "_funcs/ki_modalitaeten.html"):
            write("layouts/_partials/" + partial,
                  (ROOT / "layouts/_partials" / partial).read_text(encoding="utf-8"))
        write("layouts/_default/single.html", '<html><body>{{ partial "ff_quellen_box.html" . }}'
              '{{ partial "schema_article.html" . }}</body></html>')
        write("layouts/_default/list.html", "")
        quellen = ('quellen:\n  - titel: Beleg\n    url: https://example.org/a\n'
                   '    datum: "2026-10-30"\n')
        samples = {
            "automatisch": f'faktencheck: 2026-11-01\n{quellen}',
            "nachtrag": (f'faktencheck: 2026-11-01\n{quellen}'
                         '    recherchiert_am: 2026-11-13\n'
                         '  - titel: Zweiter\n    url: https://example.org/b\n'),
            "ohne-faktencheck": (f'{quellen}'
                                  '    recherchiert_am: 2026-11-13\n'),
            "ohne-quellen": 'faktencheck: 2026-11-01\n',
        }
        for slug, fm in samples.items():
            write(f"content/posts/{slug}/index.md",
                  f'---\ntitle: {slug}\ndate: 2026-01-01\n{fm}---\nText\n')
        subprocess.run([HUGO, "--minify"], cwd=cls.root, check=True,
                       capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def html(self, slug):
        return (self.root / "public/posts" / slug / "index.html").read_text(encoding="utf-8")

    def test_bisherige_quellen_behalten_den_bisherigen_stempel(self):
        html = self.html("automatisch")
        self.assertIn("Quellen recherchiert am", html)
        self.assertIn("01.11.2026", html)

    def test_nachtrag_zeigt_eigenes_datum_getrennt_vom_faktencheck(self):
        html = self.html("nachtrag")
        self.assertIn("Faktencheck", html)
        self.assertIn("01.11.2026", html)
        self.assertNotIn("Quellen recherchiert am", html)
        self.assertIn("recherchiert am", html)
        self.assertIn("13.11.2026", html)
        self.assertEqual(html.count("recherchiert am"), 1,
                         "Für eine undatierte zweite Quelle kein Datum erfinden")

    def test_einzelquelle_auch_ohne_allgemeinen_faktencheck(self):
        html = self.html("ohne-faktencheck")
        self.assertIn("recherchiert am", html)
        self.assertIn("13.11.2026", html)
        self.assertNotIn("01.11.2026", html)

    def test_ohne_quellen_keine_quellenbox(self):
        self.assertNotIn('ff-quellen', self.html("ohne-quellen"))

    def test_schema_erfindet_kein_veroeffentlichungsdatum_der_strukturierten_daten(self):
        for slug in ("automatisch", "nachtrag", "ohne-faktencheck", "ohne-quellen"):
            with self.subTest(slug=slug):
                html = self.html(slug)
                match = re.search(r'<script type=["\']?application/ld\+json["\']?>'
                                  r'(.*?)</script>', html)
                self.assertIsNotNone(match)
                daten = json.loads(match.group(1))
                self.assertNotIn("sdDatePublished", daten)
                if slug != "ohne-quellen":
                    self.assertEqual(daten["citation"][0]["url"], "https://example.org/a")
                    self.assertEqual(daten["citation"][0]["datePublished"], "2026-10-30")
                if slug == "nachtrag":
                    self.assertNotIn("datePublished", daten["citation"][1],
                                     "Kein Publikationsdatum aus dem alten Faktencheck ableiten")


class QuellenNeurechercheTest(unittest.TestCase):
    def test_ersetzter_quellenblock_uebernimmt_keinen_fremden_einzelstempel(self):
        alt = ('title: Test\nquellen:\n  - titel: Alt\n    url: https://example.org/alt\n'
               '    recherchiert_am: 2026-11-13\nfaktencheck: 2026-11-01')
        neu = faktenfrische.fm_setze_quellen(
            alt, [{"titel": "Neu", "url": "https://example.org/neu"}])
        neu = faktenfrische.fm_setze_faktencheck(neu, "2026-11-20")
        daten = yaml.safe_load(neu)
        self.assertNotIn("recherchiert_am", daten["quellen"][0])
        self.assertEqual(daten["quellen"][0]["url"], "https://example.org/neu")
        self.assertEqual(str(daten["faktencheck"]), "2026-11-20")


if __name__ == "__main__":
    unittest.main()
