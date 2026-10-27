#!/usr/bin/env python3
"""Regressionstests für die Einbett-Wache (E1–E6, 27.10.2026).

Der Einbett-Block ist das einzige Angebot der Seite, das Fremde
kopieren sollen. Diese Tests halten die Zusagen fest, unter denen er
überhaupt einen Backlink verdient: absolute URLs, gleiches Ziel in Bild
und Quellenzeile, kein nofollow, kein Tracking, kein Fremdcode.
"""
from __future__ import annotations

import html
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import einbetten_wache as wache  # noqa: E402

SNIPPET = (
    '<figure><a href="https://franksfinanzcheck.de/x/">'
    '<img src="https://franksfinanzcheck.de/downloads/x.svg" width="1200" '
    'height="628" alt="Grafik"></a><figcaption>Grafik: '
    '<a href="https://franksfinanzcheck.de/x/">Quelle</a></figcaption></figure>'
)


def block(snippet: str = SNIPPET, knopf_ziel: str = "ff-einbetten-x") -> str:
    return (
        # Überschrift AUSSERHALB der <section>: Der Chunker-Vertrag
        # (scripts/layout_audit.py) erlaubt im Artikelinhalt keine H2 mit id
        # in einem Container. Der Name der Section hängt trotzdem daran.
        '<h2 id="ff-einbetten-x-titel">Grafik einbetten</h2>'
        '<section class="ff-einbetten" aria-labelledby="ff-einbetten-x-titel">'
        f'<pre class="ff-einbetten__code" id="ff-einbetten-x">'
        # Im Build steht der Code escaped im <pre> – der Test liest ihn genauso.
        f'<code>{html.escape(snippet, quote=False)}</code></pre>'
        f'<button data-ff-einbetten-kopieren="{knopf_ziel}">kopieren</button>'
        '<p role="status"></p></section>'
    )


def funde(markup: str) -> list[str]:
    """Prüft den Block so, wie die Wache ihn im Build liest (ohne bs4 –
    im Gate-Job ist nur requirements-ci.txt installiert)."""
    doc = wache.baum(markup)
    return wache.pruefe_block(doc.erste("section", "ff-einbetten"), "test", doc)


class EinbettenTests(unittest.TestCase):
    def test_sauberer_block_hat_keine_funde(self):
        self.assertEqual(funde(block()), [])

    def test_relativer_bildpfad_bricht_beim_fremden_einbau(self):
        markup = block(SNIPPET.replace(
            'src="https://franksfinanzcheck.de/downloads/x.svg"', 'src="/downloads/x.svg"'))
        self.assertTrue(any(f.startswith("E2:") and "nicht absolut" in f
                            for f in funde(markup)))

    def test_nofollow_im_snippet_wird_abgelehnt(self):
        markup = block(SNIPPET.replace(
            '<a href="https://franksfinanzcheck.de/x/"><img',
            '<a rel="nofollow" href="https://franksfinanzcheck.de/x/"><img'))
        self.assertTrue(any(f.startswith("E3:") and "nofollow" in f for f in funde(markup)))

    def test_tracking_parameter_im_link_wird_abgelehnt(self):
        markup = block(SNIPPET.replace(
            "https://franksfinanzcheck.de/x/",
            "https://franksfinanzcheck.de/x/?utm_source=linkedin"))
        treffer = [f for f in funde(markup) if f.startswith("E4:")]
        self.assertEqual(len(treffer), 1, treffer)

    def test_href_ist_kein_tracking_parameter(self):
        """Fehlalarm-Falle: `ref=` steckt in `href=`; nur echte Keys zählen."""
        self.assertFalse([f for f in funde(block()) if f.startswith("E4:")])

    def test_bild_und_quellenzeile_muessen_gleiches_ziel_haben(self):
        markup = block(SNIPPET.replace(
            '<a href="https://franksfinanzcheck.de/x/">Quelle',
            '<a href="https://franksfinanzcheck.de/y/">Quelle'))
        self.assertTrue(any("verschiedene URLs" in f for f in funde(markup)))

    def test_fremdcode_im_snippet_wird_abgelehnt(self):
        markup = block(SNIPPET + '<script src="https://x.test/t.js"></script>')
        self.assertTrue(any(f.startswith("E5:") for f in funde(markup)))

    def test_kopierknopf_ohne_ziel_id(self):
        markup = block(knopf_ziel="ff-einbetten-y")
        self.assertTrue(any("E6:" in f for f in funde(markup)))

    def test_block_ohne_namen(self):
        markup = block().replace(' aria-labelledby="ff-einbetten-x-titel"', "")
        self.assertIn('<section class="ff-einbetten">', markup)
        self.assertTrue(any(f.startswith("E1:") for f in funde(markup)))

    def test_unrenderte_template_reste(self):
        markup = block(SNIPPET + "{{ .Params }}")
        self.assertTrue(any("Template-Reste" in f for f in funde(markup)))


class BuildTests(unittest.TestCase):
    def test_selftest_laeuft_gruen(self):
        self.assertEqual(wache.selftest(), 0)

    def test_build_ohne_block_ist_rot(self):
        """Ein fehlender Block ist kein Nichts – das Angebot wäre weg."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_text("<html><body></body></html>", encoding="utf-8")
            blocke, f = wache.pruefe_public(tmp)
            self.assertEqual(blocke, 0)
            self.assertEqual(f, [])
            self.assertEqual(wache.main(["--public", tmp]), 1)


if __name__ == "__main__":
    unittest.main()
