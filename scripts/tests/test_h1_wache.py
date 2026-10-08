#!/usr/bin/env python3
"""Regressionen der H1-Wache („genau eine H1 pro Seite“, Dauerheilung #623).

Warum diese Tests existieren: Die Meldung #623 war nur das Symptom. Der
Befund darunter war ein toter Template-Zweig (zwei Kopien der Einzel-
ansicht, von denen eine nie rendert) und ein Audit, das 20 von 107
Seiten sah und deshalb eine dritte Doppel-H1 übersah. Beides fällt erst
auf, wenn es wehtut – genau dann prüfen diese Fälle, dass die Wache
zieht.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import h1_wache as wache  # noqa: E402

SKRIPT = ROOT / "scripts" / "h1_wache.py"


class MarkdownErkennungTests(unittest.TestCase):
    def test_fliestext_h1_wird_mit_zeilennummer_erkannt(self):
        text = "---\ntitle: \"x\"\n---\n\n## Zwischenzeile\n\n# Schirmzeile\n"
        self.assertEqual(wache.markdown_ohne_huelle(text), [(7, "Schirmzeile")])

    def test_frontmatter_und_code_zaun_sind_geschuetzt(self):
        text = ("---\ntitle: \"x\"\n# Kommentar im Frontmatter\n---\n\n"
                "```\n# Beispiel im Code\n```\n\n~~~\n# auch das nicht\n~~~\n")
        self.assertEqual(wache.markdown_ohne_huelle(text), [])

    def test_hashtag_und_tiefere_ebenen_sind_keine_h1(self):
        self.assertEqual(wache.markdown_ohne_huelle("#ohneLeerzeichen\n"), [])
        self.assertEqual(wache.markdown_ohne_huelle("## Ebene zwei\n"), [])
        self.assertEqual(wache.markdown_ohne_huelle("###### Ebene sechs\n"), [])

    def test_jede_h1_einer_datei_wird_gemeldet(self):
        self.assertEqual(len(wache.markdown_ohne_huelle("# eins\n\n# zwei\n")), 2)

    def test_ohne_frontmatter_wird_ab_zeile_eins_gelesen(self):
        self.assertEqual(wache.markdown_ohne_huelle("# direkt los\n"), [(1, "direkt los")])


class QuellWacheTests(unittest.TestCase):
    def test_echte_quelle_ist_gruen(self):
        self.assertEqual(wache.s1_quelle(ROOT), [])
        self.assertEqual(wache.s2_layout(ROOT), [])

    def test_h1_in_einem_beliebigen_baum_wird_zum_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / "content").mkdir()
            (wurzel / "archetypes").mkdir()
            (wurzel / "content" / "seite.md").write_text(
                "---\ntitle: \"x\"\n---\n\n# Doppelt gemoppelt\n", encoding="utf-8")
            funde = wache.s1_quelle(wurzel)
            self.assertEqual(len(funde), 1)
            self.assertIn("seite.md:5", funde[0])
            self.assertIn("heading:", funde[0])  # der Handgriff steht im Befund

    def test_archetypen_werden_mitgeprueft(self):
        # Eine H1 in einer Vorlage vererbt sich an jeden neuen Artikel.
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / "content").mkdir()
            (wurzel / "archetypes").mkdir()
            (wurzel / "archetypes" / "posts.md").write_text("---\n---\n\n# Titel\n", encoding="utf-8")
            funde = wache.s1_quelle(wurzel)
            self.assertTrue(any("archetypes/posts.md" in f for f in funde))

    def test_fehlender_quellbaum_ist_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(wache.s1_quelle(Path(tmp)))


class LayoutWacheTests(unittest.TestCase):
    def test_einzel_templates_binden_den_gemeinsamen_baustein_ein(self):
        # Der Befund vom 07.10.2026: zwei Kopien der Einzelansicht, von
        # denen eine nie rendert. Beide Templates müssen denselben
        # Baustein einbinden – sonst ist wieder ein Zweig im Leeren.
        for name in ("_default/single.html", "single.html"):
            with self.subTest(datei=name):
                text = (ROOT / "layouts" / name).read_text(encoding="utf-8")
                self.assertIn('partial "artikel_einzeln.html"', text)
                self.assertNotIn("<h1", text)

    def test_baustein_traegt_genau_eine_h1_und_ehrt_heading(self):
        text = wache._lesen(wache.ARTIKEL_BAUSTEIN)
        self.assertEqual(len(wache.h1_der_seite(text)), 1)
        self.assertIn(".Params.heading", text)

    def test_zweiter_baustein_im_template_ist_ein_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / "layouts" / "_partials").mkdir(parents=True)
            (wurzel / "layouts" / "_default").mkdir(parents=True)
            (wurzel / "layouts" / "_partials" / "artikel_einzeln.html").write_text(
                '<h1>{{ .Params.heading | default .Title }}</h1>', encoding="utf-8")
            (wurzel / "layouts" / "_default" / "single.html").write_text(
                '<h1>{{ .Title }}</h1>', encoding="utf-8")
            (wurzel / "layouts" / "single.html").write_text(
                '{{ partial "artikel_einzeln.html" . }}', encoding="utf-8")
            (wurzel / "layouts" / "_default" / "list.html").write_text(
                '<h1>{{ .Params.heading | default .Title }}</h1>', encoding="utf-8")
            funde = wache.s2_layout(wurzel)
            self.assertTrue(funde, "eine eigene H1 im Template muss auffallen")


class HTMLH1ParserTests(unittest.TestCase):
    def test_echte_h1_werden_gezaehlt_skript_kommentar_und_template_nicht(self):
        html = (
            '<!-- <h1>Kommentar</h1> -->'
            '<script>const markup = "<h1>Skript</h1>";</script>'
            '<template><h1>Inerte Vorlage</h1></template>'
            '<h1>Text &amp; <em>Mehr</em></h1>'
        )
        self.assertEqual(wache.h1_der_seite(html), ["Text & Mehr"])

    def test_entities_sind_text_und_unicode_leerzeichen_bleiben_leer(self):
        self.assertEqual(wache.h1_der_seite("<h1>&amp;</h1>"), ["&"])
        self.assertEqual(wache.h1_der_seite("<h1>&nbsp;&#160;&#xA0;</h1>"), [""])

    def test_unvollstaendige_h1_wird_trotzdem_gezaehlt(self):
        self.assertEqual(wache.h1_der_seite("<h1>Offene Überschrift"), ["Offene Überschrift"])


class BuildWacheTests(unittest.TestCase):
    def _public(self, tmp: str, seiten: dict[str, str]) -> Path:
        public = Path(tmp) / "public"
        for rel, inhalt in seiten.items():
            ziel = public / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
        return public

    def test_doppel_h1_mit_texten_und_leere_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = self._public(tmp, {
                "index.html": "<html lang=de><h1>Startseite</h1></html>",
                "presse/index.html": "<html lang=de><h1>Eins</h1><h1>Zwei</h1></html>",
                "leer/index.html": "<html lang=de><h1>   </h1></html>",
            })
            funde = wache.s3_build(public)
            self.assertTrue(any("presse/index.html" in f and "2 H1" in f for f in funde))
            self.assertTrue(any("Zwei" in f for f in funde))
            self.assertTrue(any("leer/index.html" in f for f in funde))
            self.assertFalse(any("index.html" == f.split(" ")[1] for f in funde))

    def test_ausnahmen_sind_begruendet_und_nicht_zu_weit(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = self._public(tmp, {
                "google123.html": "google-site-verification: x",
                "page/2/index.html": "<html>weiter</html>",
                "go/strom/index.html": "<html lang=de><h1>Weiter</h1></html>",
            })
            self.assertEqual(wache.s3_build(public), [])
            # Ohne Ausnahme muss der Redirect auffallen – sonst wäre die
            # Ausnahme eine Lücke mit Etikett.
            self.assertTrue(any("page/2/index.html" in f for f in wache.s3_build(public, ausnahmen=())))

    def test_ausnahmen_sind_routenscharf(self):
        self.assertTrue(wache.ausnahme_grund("google123.html"))
        self.assertTrue(wache.ausnahme_grund("page/2/index.html"))
        self.assertTrue(wache.ausnahme_grund("posts/page/2/index.html"))
        self.assertEqual(wache.ausnahme_grund("docs/google123.html"), "")
        self.assertEqual(wache.ausnahme_grund("page/2/inhalt.html"), "")
        self.assertEqual(wache.ausnahme_grund("go/strom/index.html"), "")
        self.assertTrue(wache.ausnahme_grund("go/strom/index.html", wache.AUSNAHMEN_SEITE))

    def test_jede_ausnahme_traegt_einen_grund(self):
        for muster, grund in wache.AUSNAHMEN_H1 + wache.AUSNAHMEN_SEITE:
            self.assertGreater(len(grund.strip()), 10, f"Ausnahme {muster} ohne Begründung")

    def test_h1_wache_prueft_strenger_als_das_vollaudit(self):
        # /go/ hat eine H1, aber keine Seitennavigation: die H1-Wache
        # prüft sie (eine H1 ist eine H1), das Komplett-Audit nicht.
        self.assertTrue(any(m == r"^go/[^/]+/index\.html$" for m, _ in wache.AUSNAHMEN_SEITE))
        self.assertFalse(any(m == r"^go/" for m, _ in wache.AUSNAHMEN_H1))

    def test_echter_build_ist_gruen(self):
        public = ROOT / "public"
        if not public.is_dir():
            self.skipTest("public/ fehlt – Hugo-Build vorher ausführen")
        self.assertEqual(wache.s3_build(public), [])


class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        self.assertEqual(wache.selftest(ROOT), [])

    def test_skript_selbsttest_laeuft_gruen(self):
        r = subprocess.run([sys.executable, str(SKRIPT), "--selftest"],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, (r.stdout or "")[-800:] + (r.stderr or "")[-400:])

    def test_sabotage_in_der_quelle_faellt_auf(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            for ordner in ("content", "archetypes"):
                (wurzel / ordner).mkdir()
            (wurzel / "content" / "seite.md").write_text("---\n---\n\n# Sabotage\n", encoding="utf-8")
            self.assertTrue(wache.selftest(wurzel), "Sabotage im Quellbaum muss den Selbsttest brechen")


if __name__ == "__main__":
    unittest.main()
