"""Render-Vertrag: maschinenlesbare KI-Kennzeichnung (#1028).

Baut echte Hugo-Fixtures mit den echten Vorlagen und prüft, was eine
Maschine aus dem Dokument lesen kann:

* `<meta name="ai-generated">` nur bei belegter KI-Erzeugung
* `ai-generated-scope` nennt genau die betroffenen Modalitäten
* `rel="describedby"` zeigt auf den Anker des Impressum-Hinweises
* schema.org `creditText` ist gültiges JSON und trennt Text/Bild/Ton
* das KI-Cover trägt `data-ai-generated` und das IPTC-Vokabular
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HUGO = os.environ.get("HUGO_BIN", "hugo")

TEILVORLAGEN = ("ki_provenienz.html", "schema_article.html", "article_dates.html", "cover.html")


def jsonld(html: str) -> dict:
    """Den Article-Knoten aus dem eingebetteten JSON-LD holen (streng geparst)."""
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        daten = json.loads(block)
        if daten.get("@type") == "Article":
            return daten
    raise AssertionError("kein Article-JSON-LD im Bauprodukt")


def meta(html: str, name: str) -> str | None:
    m = re.search(rf'<meta name="{name}" content="([^"]*)"', html)
    return m.group(1) if m else None


@unittest.skipUnless(shutil.which(HUGO), "Hugo nicht installiert")
class KiProvenienzRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)

        def write(rel, inhalt):
            datei = root / rel
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(inhalt, encoding="utf-8")

        write("hugo.toml", 'baseURL = "https://example.org/"\ntitle = "Test"\n'
                           '[params]\nauthor = "Frank Hartung"\n')
        for vorlage in TEILVORLAGEN:
            write("layouts/_partials/" + vorlage,
                  (ROOT / "layouts/_partials" / vorlage).read_text(encoding="utf-8"))
        write("layouts/_partials/asset_url.html", '{{ return . }}')
        write("layouts/_default/baseof.html",
              '<!doctype html><html><head>{{ block "kopf" . }}{{ end }}</head>'
              '<body>{{ block "main" . }}{{ end }}</body></html>')
        write("layouts/_default/single.html",
              '{{ define "kopf" }}{{ partial "ki_provenienz.html" . }}{{ end }}'
              '{{ define "main" }}{{ partial "schema_article.html" . }}'
              '{{ partial "cover.html" (dict "cxt" . "IsSingle" true "isHidden" false) }}{{ end }}')
        write("content/posts/_index.md", "---\ntitle: Posts\n---\n")

        proben = {
            # KI-Text, kein KI-Bild, Lesehilfe aktiv → text + audio
            "ki-text": "ai_generated: true\n",
            # Menschlicher Text, aber synthetische Tonspur → nur audio
            "mensch-text": "ai_generated: false\n",
            # KI-Text + belegtes KI-Bild + ohne Lesehilfe → text + image
            "ki-bild": ('ai_generated: true\nhideReaderToolbar: true\n'
                        'cover:\n  image: /bilder/ki.jpg\n  ai_generated: true\n'
                        '  ki_pruefung:\n    digital_source_type: trainedAlgorithmicMedia\n'
                        '    sha256: x\n    quelle: x\n    geprueft_am: 2026-11-03\n'
                        '    deepfake: false\n'),
            # KI-Bild ohne belegte Erzeugungsart → kein IPTC-Wert im DOM
            "ki-bild-ohne-typ": ('ai_generated: false\nhideReaderToolbar: true\n'
                                 'cover:\n  image: /bilder/unbekannt.jpg\n  ai_generated: true\n'),
            # Geprüfter KI-Artikel → creditText nennt Prüfer und Autor
            "ki-geprueft": ('ai_generated: true\nhideReaderToolbar: true\n'
                            'redaktionelle_pruefung:\n  status: freigegeben\n'
                            '  pruefer:\n    name: Dr. Test\n  pruefdatum: 2026-01-01\n'
                            '  naechste_pruefung: 2026-12-01\n'),
        }
        for slug, feld in proben.items():
            write(f"content/posts/{slug}/index.md", f"---\ntitle: {slug}\ndate: 2026-01-01\n{feld}---\nText\n")

        subprocess.run([HUGO, "--quiet"], cwd=root, check=True, capture_output=True, text=True)
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def html(self, slug: str) -> str:
        return (self.root / "public/posts" / slug / "index.html").read_text(encoding="utf-8")

    def test_meta_signal_nur_bei_belegter_ki(self):
        self.assertEqual(meta(self.html("ki-text"), "ai-generated"), "true")
        self.assertIsNone(meta(self.html("mensch-text"), "ai-generated"))
        self.assertIsNone(meta(self.html("ki-bild-ohne-typ"), "ai-generated"))

    def test_scope_nennt_betroffene_modalitaeten(self):
        self.assertEqual(meta(self.html("ki-text"), "ai-generated-scope"), "text,audio")
        self.assertEqual(meta(self.html("mensch-text"), "ai-generated-scope"), "audio")
        self.assertEqual(meta(self.html("ki-bild"), "ai-generated-scope"), "text,image")
        self.assertEqual(meta(self.html("ki-bild-ohne-typ"), "ai-generated-scope"), "image")

    def test_describedby_zeigt_auf_impressum_anker(self):
        m = re.search(r'<link rel="describedby" href="([^"]+)"', self.html("ki-text"))
        self.assertIsNotNone(m, "rel=\"describedby\" fehlt")
        self.assertTrue(m.group(1).endswith("/impressum/#ki-hinweis"))
        # Der Anker muss im Impressum wirklich existieren (M2 des Gates).
        impressum = (ROOT / "content/impressum/index.md").read_text(encoding="utf-8")
        self.assertIn("{#ki-hinweis}", impressum)

    def test_credit_text_ist_gueltiges_json_und_trennt_rollen(self):
        credit = jsonld(self.html("ki-text"))["creditText"]
        self.assertIn("Mit KI erstellt oder bearbeitet", credit)
        self.assertIn("Frank Hartung", credit)
        self.assertIn("Tonspur maschinell erzeugt", credit)

        mensch = jsonld(self.html("mensch-text"))["creditText"]
        self.assertNotIn("Mit KI erstellt", mensch)
        self.assertIn("Tonspur maschinell erzeugt", mensch)

        geprueft = jsonld(self.html("ki-geprueft"))["creditText"]
        self.assertIn("fachlich geprüft und freigegeben von Dr. Test", geprueft)
        self.assertIn("Redaktionelle Verantwortung: Frank Hartung", geprueft)

    def test_ki_cover_traegt_iptc_vokabular_im_dom(self):
        self.assertIn('data-ai-generated="true"', self.html("ki-bild"))
        self.assertIn('data-digital-source-type="trainedAlgorithmicMedia"', self.html("ki-bild"))
        # Ohne belegte Erzeugungsart wird kein Wert erfunden.
        self.assertIn('data-ai-generated="true"', self.html("ki-bild-ohne-typ"))
        self.assertNotIn("data-digital-source-type", self.html("ki-bild-ohne-typ"))
        # Menschlicher Artikel ohne KI-Bild: kein Bildsignal.
        self.assertNotIn("data-ai-generated", self.html("mensch-text"))

    def test_ki_cover_wird_ohne_varianten_ausgeliefert(self):
        # Deklarierte KI-Originale dürfen nicht neu kodiert werden, sonst
        # gehen Provenienz-Metadaten verloren (Vertrag aus cover.html).
        self.assertNotIn("<source", self.html("ki-bild"))
        self.assertNotIn("srcset=", self.html("ki-bild"))


if __name__ == "__main__":
    unittest.main()
