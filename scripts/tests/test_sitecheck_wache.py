"""Unit-Tests der Sitecheck-Wache (scripts/sitecheck_wache.py).

Die Fälle sind die echten Befunde der Optimierung vom 27.10.2026:
SVG-<title> in Charts, Description-Fenster, Überschriftensprünge, 42 tote
Inhaltsverzeichnis-Links, <b> in Shortcodes, KI-Sperren in der robots.txt
(die KEIN globales Disallow sind) und die Parität Sitemap ↔ Canonical.
"""
import tempfile
import unittest
from pathlib import Path

import scripts.sitecheck_wache as w


def regeln(text, datei="index.html"):
    return {f.regel for f in w.seiten_befunde(w.analysiere(datei, text))}


class MetaTests(unittest.TestCase):
    def test_saubere_seite_ist_gruen(self):
        self.assertEqual(w.seiten_befunde(w.analysiere("index.html", w.SAUBER)), [])

    def test_svg_title_ist_kein_seitentitel(self):
        text = w.SAUBER.replace(
            "<body>", "<body><svg><title>Diagramm mit drei Balken</title></svg>")
        self.assertNotIn("M4", regeln(text))

    def test_description_fenster_ist_das_marktfenster(self):
        """Seit 01.11.2026 misst die Wache das Fenster der SSOT (100–155).

        Vorher führte sie 110–156 – zwei Zahlen, die nirgends sonst galten.
        Der Test friert die Bindung ein, nicht die Zahl: er vergleicht gegen
        `serp_limits`, damit eine Änderung dort hier ankommt statt zu driften.
        """
        import serp_limits as sl
        self.assertEqual((w.DESC_MIN, w.DESC_MAX),
                         (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))
        alt = ("Eine Seitenbeschreibung im Fenster des Website Checks: Sie nennt "
               "das Thema, bleibt konkret und ist lang genug, damit Google sie "
               "nicht abschneidet.")
        self.assertIn("M5", regeln(w.SAUBER.replace(alt, "Zu kurz.")))
        self.assertIn("M5", regeln(w.SAUBER.replace(alt, alt * 2)))

    def test_title_max_60(self):
        self.assertIn("M4", regeln(w.SAUBER.replace(
            "Ein Titel mit genau sechzig Zeichen maximal im Fenster",
            "Ein deutlich zu langer Titel, der in der Suchergebnisliste "
            "abgeschnitten wird und damit sein Keyword verliert")))

    def test_generator_tag_wird_erkannt(self):
        self.assertIn("M7", regeln(w.SAUBER.replace(
            "<title>", '<meta name="generator" content="Hugo 0.168.0"><title>')))

    def test_duplikate_ueber_seiten_hinweg(self):
        dup = w.duplikat_befunde([w.analysiere("a/index.html", w.SAUBER),
                                  w.analysiere("b/index.html", w.SAUBER)])
        self.assertIn("M8", {f.regel for f in dup})


class StrukturTests(unittest.TestCase):
    def test_zwei_h1_sind_befund(self):
        self.assertIn("S1", regeln(w.SAUBER.replace(
            "<h2>Erster Abschnitt</h2>",
            "<h1>Noch eine Hauptüberschrift</h1><h2>Erster Abschnitt</h2>")))

    def test_ueberschriftensprung(self):
        self.assertIn("S2", regeln(w.SAUBER.replace(
            "<h2>Erster Abschnitt</h2>", "<h3>Erster Abschnitt</h3>")))

    def test_obsolete_tags_und_hinweise(self):
        befunde = w.seiten_befunde(w.analysiere("index.html", w.SAUBER.replace(
            "<body>", '<body><font color="red">Alt</font><b>Fett</b>')))
        self.assertIn("S3", {f.regel for f in befunde if f.schwere == "fehler"})
        self.assertTrue(any(f.regel == "S3" and f.schwere == "hinweis"
                            for f in befunde))

    def test_bild_ohne_alt(self):
        self.assertIn("S4", regeln(w.SAUBER.replace('alt="Beispiel"', "")))

    def test_layout_tabelle_ohne_th(self):
        self.assertIn("S5", regeln(w.SAUBER.replace(
            "<th>Spalte</th>", "<td>Spalte</td>")))

    def test_tote_und_verwaiste_anker(self):
        self.assertIn("S7", regeln(w.SAUBER.replace(
            '<a href="/impressum/">', '<a href="#"')))
        self.assertIn("S7", regeln(w.SAUBER.replace(
            '<a href="/impressum/">', '<a href="#gibts-nicht"')))

    def test_sprungziel_ohne_href_ist_kein_link(self):
        self.assertNotIn("S7", regeln(w.SAUBER.replace(
            "<body>", '<body><a id="sprungziel">Ziel</a>')))

    def test_duennes_dokument(self):
        self.assertIn("S8", regeln(w.SAUBER.replace(
            "Dies ist ein lesbarer Fließtext über Fixkosten. " * 20, "Kurz.")))


class TechnikTests(unittest.TestCase):
    def test_skript_ohne_defer(self):
        self.assertIn("T2", regeln(w.SAUBER.replace(
            '<script defer src="/premium/ff-premium.js">',
            '<script src="/premium/ff-premium.js">')))

    def test_fremder_skript_host(self):
        self.assertIn("T3", regeln(w.SAUBER.replace(
            '<script defer src="/premium/ff-premium.js">',
            '<script defer src="https://cdn.example.org/track.js">')))

    def test_frames_und_plugins(self):
        self.assertIn("T1", regeln(w.SAUBER.replace(
            "<body>", "<body><frameset><frame src='/x.html'></frameset>")))
        self.assertIn("T1", regeln(w.SAUBER.replace(
            "<body>", '<body><embed src="/spiel.swf">')))

    def test_zu_viele_stylesheets(self):
        self.assertIn("T4", regeln(w.SAUBER.replace(
            "<title>", '<link rel="stylesheet" href="/a.css">'
                       '<link rel="stylesheet" href="/b.css">'
                       '<link rel="stylesheet" href="/c.css"><title>')))


class KonfigurationTests(unittest.TestCase):
    def _site(self, ordner, robots=None, sitemap=None):
        w._temp_site(Path(ordner), robots=robots or w.ROBOTS,
                     sitemap=sitemap or w.SITEMAP)

    def test_saubere_testseite_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._site(tmp)
            befunde, werte = w.pruefe_site(Path(tmp))
            self.assertEqual([f.regel for f in befunde], [])
            self.assertEqual(werte["indexierbare_seiten"], 10)

    def test_ki_sperre_ist_kein_globales_disallow(self):
        robots = (w.ROBOTS + "\nUser-agent: GPTBot\nDisallow: /\n")
        with tempfile.TemporaryDirectory() as tmp:
            self._site(tmp, robots=robots)
            befunde, _ = w.pruefe_site(Path(tmp))
            self.assertNotIn("K1", {f.regel for f in befunde})
        with tempfile.TemporaryDirectory() as tmp:
            self._site(tmp, robots="User-agent: *\nDisallow: /\n"
                                   "Sitemap: https://franksfinanzcheck.de/sitemap.xml\n")
            befunde, _ = w.pruefe_site(Path(tmp))
            self.assertIn("K1", {f.regel for f in befunde})

    def test_sitemap_paritaet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._site(tmp, sitemap=w.SITEMAP.replace(
                '<url><loc>https://franksfinanzcheck.de/beispiel/</loc></url>', ""))
            befunde, _ = w.pruefe_site(Path(tmp))
            self.assertIn("K3", {f.regel for f in befunde})

    def test_fehlendes_build_verzeichnis_ist_setupfehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                w.pruefe_site(Path(tmp) / "gibts-nicht")

    def test_selftest_ist_scharf(self):
        self.assertEqual(w.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
