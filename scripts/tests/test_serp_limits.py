#!/usr/bin/env python3
"""Tests der Snippet-Grenzen (scripts/serp_limits.py) – die SSOT.

Warum diese Datei existiert (27.10.2026): Am 27.10.2026 meldete ein fremder
Crawl zwei Befunde an derselben Description – „über 155 Zeichen" und „über
985 Pixel". Unser Haus hatte an zwei Stellen zwei andere Grenzen (160 in
`metadaten_wache`, 165 im `seo_cockpit`) und schwieg. Diese Tests halten den
Sollstand fest:

  · die Grenzen (100/155 Zeichen, 985 px in Arial 14 px),
  · das Breitenmaß (Helvetica-Kernmetrik; Arial ist metrisch identisch),
  · die Ehrlichkeit bei unbekannten Zeichen (`None` statt Schätzung),
  · die Bindung: beide Messstellen lesen aus dieser Datei, nicht aus einer Kopie.

Läuft ohne Netz, ohne Font, ohne Zusatzpakete:
`python3 -m unittest scripts.tests.test_serp_limits`
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import serp_limits as sl  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class Grenzen(unittest.TestCase):
    def test_grenzen_sind_marktgerecht(self):
        self.assertEqual((sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN), (100, 155))
        self.assertEqual(sl.DESC_MAX_PX, 985)
        self.assertEqual(sl.SCHRIFT_PX, 14.0)

    def test_exakt_155_zeichen_passen(self):
        # Schmale Zeichen: die Zeichengrenze ist hier der einzige Maßstab.
        self.assertEqual(sl.befunde('i' * 155), [])
        self.assertEqual(sl.befunde('i' * 156)[0][0], 'zu-lang')

    def test_zeichenzahl_allein_reicht_nicht(self):
        # 155 breite Zeichen laufen über das Snippet hinaus – „passt in
        # Zeichen" ist kein Beleg für „passt ins Snippet".
        self.assertGreater(sl.breite_px('W' * 155), sl.DESC_MAX_PX)
        self.assertEqual([code for code, _ in sl.befunde('W' * 155)], ['zu-breit'])

    def test_leere_description_ist_zu_kurz(self):
        self.assertEqual([code for code, _ in sl.befunde('')], ['zu-kurz'])
        self.assertEqual([code for code, _ in sl.befunde(None)], ['zu-kurz'])
        self.assertEqual([code for code, _ in sl.befunde('   ')], ['zu-kurz'])

    def test_zu_kurz_ist_einstellbar(self):
        text = 'a' * 90
        self.assertEqual([code for code, _ in sl.befunde(text)], ['zu-kurz'])
        self.assertEqual(sl.befunde(text, min_zeichen=70), [])


class Breitenmass(unittest.TestCase):
    def test_bekannte_breiten(self):
        # Adobe-Kernmetrik (1/1000 em) – veröffentlichte Stichproben.
        self.assertEqual(sl.BREITEN['a'], 556)
        self.assertEqual(sl.BREITEN['W'], 944)
        self.assertEqual(sl.BREITEN['i'], 222)
        self.assertEqual(sl.BREITEN[' '], 278)
        self.assertEqual(sl.BREITEN['ä'], 556)

    def test_pixel_bei_14_px(self):
        # 1000/1000 em * 14 px = 14 px
        self.assertAlmostEqual(sl.breite_px('W' * 1000), 944 * 14, places=3)
        self.assertAlmostEqual(sl.breite_px('Hallo Welt'), 63.784, places=3)

    def test_tabelle_ist_plausibel(self):
        self.assertGreaterEqual(len(sl.BREITEN), 200)
        for zeichen, breite in sl.BREITEN.items():
            self.assertEqual(len(zeichen), 1, zeichen)
            self.assertGreaterEqual(breite, 0, zeichen)
            self.assertLessEqual(breite, 1100, zeichen)  # @ ist mit 1015 der Ausreißer

    def test_deutsche_zeichen_sind_abgedeckt(self):
        for zeichen in 'äöüßÄÖÜ€„“”–—…§%&':
            self.assertIn(zeichen, sl.BREITEN, zeichen)

    def test_unbekanntes_zeichen_wird_nicht_geschaetzt(self):
        self.assertIsNone(sl.breite_px('Strom sparen 💡'))
        self.assertEqual([code for code, _ in sl.befunde('a' * 120 + '💡')], ['unmessbar'])
        self.assertEqual(sl.unbekannte_zeichen('Strom 💡 sparen 💡'), ['💡'])

    def test_breite_grenze_ist_scharf(self):
        # 135 Zeichen aus breiten Wörtern: Zeichenzahl passt, Breite nicht.
        breit = ('Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe und Wartung '
                 'zusammengehören. Wer Wohnraum warm hält, spart mit Wärmedämmung.')
        self.assertLessEqual(len(breit), sl.DESC_MAX_ZEICHEN)
        self.assertGreater(sl.breite_px(breit), sl.DESC_MAX_PX)
        self.assertEqual([code for code, _ in sl.befunde(breit)], ['zu-breit'])

    def test_schmale_zeichen_bleiben_im_fenster(self):
        # viele „i": 155 Zeichen, weit unter 985 px
        text = ('i' * 60) + ' ' + ('i' * 94)
        self.assertEqual(len(text), 155)
        self.assertLess(sl.breite_px(text), sl.DESC_MAX_PX)
        self.assertEqual(sl.befunde(text), [])


class Normalisierung(unittest.TestCase):
    def test_leerraum_wird_kollabiert(self):
        self.assertEqual(sl.normalisiere('  a   b\n\tc  '), 'a b c')
        self.assertEqual(sl.normalisiere('a\u00a0b'), 'a b')
        self.assertEqual(sl.normalisiere('a&nbsp;b'), 'a b')

    def test_gezaehlt_wird_was_der_nutzer_sieht(self):
        # Doppelte Leerzeichen blähen den Code auf, nicht das Snippet.
        self.assertEqual(len(sl.normalisiere('a' * 100 + ' ' * 40 + 'b' * 20)), 121)

    def test_masse_liefert_zeichen_und_pixel(self):
        zeichen, px = sl.masse('Hallo Welt')
        self.assertEqual(zeichen, 10)
        self.assertAlmostEqual(px, 63.784, places=3)
        self.assertEqual(sl.masse('💡'), (1, None))


class Kuerzen(unittest.TestCase):
    """`auf_snippet_kuerzen` – die EINE Stelle, an der geschnitten wird.

    WF-7B6B / #925 (29.10.2026): Ein Heiler, der „augenmaß" schneidet,
    produziert das nächste Rot. Geprüft wird deshalb: Wortgrenze, BEIDE
    Grenzen, ehrliches Ende, und die Ehrlichkeit des Nicht-Könnens.
    """

    VORFALL = ("DSL Hacks: WLAN-Verstärker oder Mesh-WLAN? So findest du 2026 "
               "heraus, was dein Zuhause wirklich braucht – mit klaren Kosten "
               "und einer Entscheidungshilfe.")

    def test_vorfall_925_passt_nach_dem_schnitt(self):
        self.assertEqual([c for c, _ in sl.befunde(self.VORFALL)], ["zu-breit"])
        k = sl.auf_snippet_kuerzen(self.VORFALL)
        self.assertIsNotNone(k)
        self.assertEqual(sl.befunde(k), [])
        self.assertTrue(k.endswith("…"))  # der Schnitt wird markiert
        self.assertGreaterEqual(len(k), sl.DESC_MIN_ZEICHEN)

    def test_schnitt_liegt_an_der_wortgrenze(self):
        k = sl.auf_snippet_kuerzen(self.VORFALL)
        # Der Schnitt ist ein Präfix des Originals, und im Original folgt
        # an der Schnittstelle ein Leerzeichen – mitten im Wort wird nicht
        # geschnitten.
        self.assertTrue(self.VORFALL.startswith(k[:-1]))
        self.assertEqual(self.VORFALL[len(k) - 1], " ")

    def test_passender_text_bleibt_unberuehrt(self):
        for text in ("i" * 155, "Hallo Welt, das ist eine Probe.", "W" * 60):
            self.assertEqual(sl.auf_snippet_kuerzen(text), sl.normalisiere(text))

    def test_leer_und_unheilbar(self):
        self.assertIsNone(sl.auf_snippet_kuerzen(""))
        self.assertIsNone(sl.auf_snippet_kuerzen(None))
        self.assertIsNone(sl.auf_snippet_kuerzen("W" * 300))  # ein Wort, zu breit

    def test_ein_wort_wird_an_der_zeichengrenze_geschnitten(self):
        k = sl.auf_snippet_kuerzen("i" * 160)
        self.assertEqual(len(k), 155)
        self.assertTrue(k.endswith("…"))
        self.assertEqual(sl.befunde(k), [])

    def test_untergrenze_wird_respektiert(self):
        # Jedes Präfix ab 100 Zeichen ist zu breit, jedes messbare zu kurz.
        self.assertIsNone(sl.auf_snippet_kuerzen("W" * 60 + " " + "W" * 60 + " " + "W" * 60))

    def test_idempotent(self):
        k = sl.auf_snippet_kuerzen(self.VORFALL)
        self.assertEqual(sl.auf_snippet_kuerzen(k), sl.normalisiere(k))

    def test_satzende_ist_parameter_nicht_zweite_schneidestelle(self):
        # Der Satzende-Heiler von meta_optimizer punktet am Limit. Vorher
        # schnitt der Schreiber selbst „augenmaß" – zwei Schneidestellen,
        # zwei Grenzen (#925). Deshalb nimmt der Heiler das Satzzeichen als
        # Parameter DERSELBEN Funktion.
        #
        # 1) Ein Text, der OHNE Punkt schon ins Fenster passt, bleibt
        #    unberührt – Kürzen wäre Zerstörung, nicht Heilung. Sein
        #    Satzzeichen ist bereits ein gültiges.
        ohne_punkt = ("Erfahre, wie du im Spätsommer deine Gasrechnung senken "
                      "kannst: Mit diesen Tipps startest du vorbereitet in "
                      "den Herbst und sparst bares Geld")
        self.assertEqual(sl.befunde(ohne_punkt), [])
        for marker in (".", "!", "?", "…"):
            self.assertEqual(sl.auf_snippet_kuerzen(ohne_punkt + marker,
                                                    satzende="."),
                             ohne_punkt + marker,
                             f"Satzende {marker!r} durfte nichts ändern")
        # 2) Am Limit entscheidet der Parameter, womit der Schnitt endet.
        k_punkt = sl.auf_snippet_kuerzen(self.VORFALL, satzende=".")
        k_mal = sl.auf_snippet_kuerzen(self.VORFALL)
        self.assertTrue(k_punkt.endswith("."), "Punkt-Schnitt endet nicht mit Punkt")
        self.assertTrue(k_mal.endswith("…"), "Standard-Schnitt markiert nicht mit …")
        for k in (k_punkt, k_mal):
            self.assertEqual(sl.befunde(k), [])
        # Der Punkt ist schmaler als das Auslassungszeichen – beides muss
        # gegen BEIDE Grenzen geprüft sein, nicht nur gegen die Zeichenzahl.
        self.assertGreaterEqual(len(k_punkt), sl.DESC_MIN_ZEICHEN)


class Bindung(unittest.TestCase):
    """Die Grenzen stehen EINMAL – beide Messstellen lesen sie hier."""

    def test_metadaten_wache_liest_die_ssot(self):
        import metadaten_wache as mw
        self.assertEqual((mw.DESC_MIN, mw.DESC_MAX),
                         (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))
        quelle = (REPO / 'scripts' / 'metadaten_wache.py').read_text(encoding='utf-8')
        self.assertNotRegex(quelle, r'(?m)^DESC_(MIN|MAX)\s*=\s*\(?\s*\d')
        self.assertIn('serp_limits', quelle)

    def test_keyword_optimizer_liest_die_ssot(self):
        """Der Schreiber des Deploy-Pfads – Verursacher von #925."""
        import keyword_optimizer as ko
        self.assertEqual((ko.DESC_MIN, ko.DESC_MAX),
                         (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))
        quelle = (REPO / "scripts" / "keyword_optimizer.py").read_text(encoding="utf-8")
        self.assertIn("import serp_limits", quelle)
        self.assertNotRegex(quelle, r"(?m)^DESC_(MIN|MAX)\s*=\s*\(?\s*\d")

    def test_meta_optimizer_liest_die_ssot(self):
        """Der zweite Schreiber – bis #925 ungebunden, aber gleiche Klasse."""
        import meta_optimizer as mo
        self.assertEqual((mo.DESC_MIN, mo.DESC_MAX),
                         (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))
        quelle = (REPO / "scripts" / "meta_optimizer.py").read_text(encoding="utf-8")
        self.assertIn("import serp_limits", quelle)
        self.assertNotRegex(quelle, r"(?m)^DESC_(MIN|MAX)\s*=\s*\(?\s*\d")

    def test_quality_score_liest_die_ssot(self):
        """Der Publish-Score – die letzte eigene Zahl (160) im Haus."""
        import quality_score as qs
        self.assertIs(qs.serp_limits, sl)
        quelle = (REPO / "scripts" / "quality_score.py").read_text(encoding="utf-8")
        self.assertIn("import serp_limits", quelle)
        self.assertNotIn("len(desc) > 160", quelle)

    def test_seo_cockpit_liest_die_ssot(self):
        import seo_cockpit as sc
        self.assertIs(sc.serp_limits, sl)
        quelle = (REPO / 'scripts' / 'seo_cockpit.py').read_text(encoding='utf-8')
        # Keine zweite Grenze im Code: 155 und 985 dürfen dort nicht als
        # eigene Zahl gesetzt werden (in Kommentaren dürfen sie stehen).
        self.assertNotRegex(quelle, r'=\s*155\b')
        self.assertNotRegex(quelle, r'=\s*985\b')

    def test_grenzen_stehen_in_keiner_dritten_datei(self):
        for relativ in ('scripts/metadaten_wache.py', 'scripts/seo_cockpit.py',
                        'scripts/blog_header_gate.py'):
            text = (REPO / relativ).read_text(encoding='utf-8')
            self.assertNotIn('DESC_MAX_ZEICHEN = 155', text, relativ)


if __name__ == '__main__':
    unittest.main()
