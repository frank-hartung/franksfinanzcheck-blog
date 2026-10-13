#!/usr/bin/env python3
"""Regressionstests der Hashtag-Regel (P8, #729).

DER VORFALL (13.10.2026)
------------------------
Der Pinterest-Watchdog meldete für genau einen Artikel „5 Hashtags (max. 3)"
und heilte nichts: Für P8 gab es keinen Heiler, und das Issue (#729) konnte
per Konstruktion nie zugehen – der Report nannte diesen einen Befund, der
Workflow schließt aber nur bei Exit 0. Zwei weitere Defekte desselben Feldes
waren überhaupt nicht sichtbar, weil beide Prüfungen Hashtags mit einem
Muster zählten, das Umlaute ausschließt (`[a-z0-9]+` / `[A-Za-z0-9]+`):
`#zählerstand` und `#ersteWohnung` standen im Bestand, ohne je eine Meldung
zu erzeugen – die Umlaut-Prüfung daneben war toter Code.

Diese Datei friert deshalb drei Dinge ein:
  1. die Regel selbst (H1–H6) in `pinterest_hashtags.py`,
  2. die Heilung (kappen, falten, Block ans Ende) inkl. Idempotenz,
  3. die Abwesenheit der blauen Flecken: der reale Bestand ist konform.

Laufbar über die Repo-Konvention (kein pytest nötig):
    python3 -m unittest discover -s scripts/tests
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pinterest_hashtags as ph  # noqa: E402

SIEBEN_UND_ZWANZIG = ("*Werbung | Beim Umzug entscheidet die Reihenfolge über zwei Wochen "
                      "ohne Internet. Mehr Spartipps auf FranksFinanzcheck! "
                      "#umzug #internet #rufnummer #dsl #wechsel")
KONFORM = ("*Werbung | Beim Umzug entscheidet die Reihenfolge über zwei Wochen ohne "
           "Internet. Mehr Spartipps auf FranksFinanzcheck! "
           "#umzug #internet #rufnummer")


class HashtagRegelTests(unittest.TestCase):
    """H1–H6: erkennen, was Pinterest als Fehler liest."""

    def test_fuenf_tags_werden_gezaehlt(self):
        self.assertIn("5 Hashtags (max. 3)", ph.befunde(SIEBEN_UND_ZWANZIG))

    def test_umlaut_tag_wird_erkannt(self):
        """Der tote-Code-Fall: `#([a-z0-9]+)` sah hier nur '#z'."""
        funde = ph.befunde("*Werbung | Gaszähler ablesen. #zählerstand #gas")
        self.assertTrue(any("Umlaut-Hashtag" in f for f in funde), funde)

    def test_grossbuchstaben_tag_wird_erkannt(self):
        funde = ph.befunde("*Werbung | Erste Wohnung. #ersteWohnung #fixkosten")
        self.assertTrue(any("Großbuchstaben" in f for f in funde), funde)

    def test_doppelter_tag_wird_erkannt(self):
        self.assertTrue(any("doppelt" in f for f in ph.befunde("#umzug #Umzug")))

    def test_tag_mitten_im_satz_wird_erkannt(self):
        self.assertTrue(any("Block am Ende" in f
                            for f in ph.befunde("#umzug Wir zeigen dir die Reihenfolge.")))

    def test_zahlenschilder_sind_keine_hashtags(self):
        """„Rabatt #1 im Test #2" ist kein Hashtag-Fall (H4)."""
        self.assertEqual([], ph.befunde("Rabatt #1 im Test #2"))

    def test_konformer_text_bleibt_still(self):
        self.assertEqual([], ph.befunde(KONFORM))
        self.assertTrue(ph.ist_konform(KONFORM))

    def test_zu_kurzer_und_zu_langer_tag_gelten_als_ungueltig(self):
        self.assertFalse(ph.ist_gueltig("ab"))
        self.assertFalse(ph.ist_gueltig("a" * 25))
        self.assertTrue(ph.ist_gueltig("dslvergleich"))


class HeilungTests(unittest.TestCase):
    """Die Heilung ist deterministisch, minimal und idempotent."""

    def test_fuenf_tags_werden_auf_drei_gekappt(self):
        neu, aenderungen = ph.heile(SIEBEN_UND_ZWANZIG)
        self.assertEqual(KONFORM, neu)
        self.assertTrue(aenderungen)
        self.assertNotIn("#dsl", neu)
        self.assertNotIn("#wechsel", neu)

    def test_die_reihenfolge_im_text_ist_die_prioritaet(self):
        """Gekappt wird hinten – die ersten drei Tags sind die wichtigsten."""
        neu, _ = ph.heile("#a1b #b2c #c3d #d4e")
        self.assertEqual("#a1b #b2c #c3d", neu)

    def test_umlaut_wird_gefaltet(self):
        self.assertEqual("zaehlerstand", ph.normalisiere("#zählerstand"))
        neu, _ = ph.heile("*Werbung | Gaszähler. #zählerstand")
        self.assertIn("#zaehlerstand", neu)
        self.assertEqual([], ph.befunde(neu))

    def test_grossbuchstabe_wird_gekleinert(self):
        neu, _ = ph.heile("*Werbung | Erste Wohnung. #ersteWohnung #fixkosten")
        self.assertIn("#erstewohnung #fixkosten", neu)
        self.assertEqual([], ph.befunde(neu))

    def test_heilung_erfindet_kein_thema(self):
        """Kein Tag dazu, keiner umbenannt: nur der Defekt wird beseitigt."""
        neu, _ = ph.heile("Text #a1b #b2c #c3d #d4e")
        self.assertEqual({"a1b", "b2c", "c3d"}, set(ph.tags_normalisiert(neu)))

    def test_heilung_ist_idempotent(self):
        einmal, _ = ph.heile(SIEBEN_UND_ZWANZIG)
        zweimal, aenderungen = ph.heile(einmal)
        self.assertEqual(einmal, zweimal)
        self.assertEqual([], aenderungen)

    def test_konformer_text_wird_nicht_angefasst(self):
        neu, aenderungen = ph.heile(KONFORM)
        self.assertEqual(KONFORM, neu)
        self.assertEqual([], aenderungen)

    def test_heilung_respektiert_die_beschreibungsgrenze(self):
        lang = "*Werbung | " + ("Ein langer Satz über Fixkosten und Sparen. " * 12)
        lang += "#umzug #internet #rufnummer #dsl"
        neu, _ = ph.heile(lang)
        self.assertLessEqual(len(neu), ph.BESCHREIBUNG_MAX)
        self.assertEqual([], ph.befunde(neu))

    def test_tags_werden_wieder_ans_ende_gestellt(self):
        """Ein Suffix hinter dem Block (Einzigartigkeits-Guard) wird geheilt."""
        neu, _ = ph.heile("Text. #umzug #internet Inkl. Checkliste für 3 Schritte.")
        self.assertTrue(neu.endswith("#umzug #internet"), neu)
        self.assertEqual([], ph.befunde(neu))

    def test_tags_bauen_haelt_die_ordnung_keywords_vor_slug(self):
        self.assertEqual(["umzug", "internet", "dslvergleich"],
                         ph.tags_bauen(["Umzug Internet", "DSL-Vergleich"],
                                       "umzug-mit-internet"))
        self.assertEqual([], ph.tags_bauen([], ""))


class BestandsprobeTests(unittest.TestCase):
    """Der reale Bestand trägt keine Hashtag-Fehler mehr (Wirkung von #729).

    Diese Probe ist die Gegenrichtung zur Prüfung: Wird ein Artikel künftig
    mit einem Defekt geboren, ist der Test rot – fail-closed, bevor der
    Watchdog ein Issue eröffnet.
    """

    def test_alle_pin_descriptions_sind_hashtag_konform(self):
        muster = re.compile(r'^pin_description:\s*"?(.*?)"?\s*$', re.M)
        befunde = {}
        for pfad in sorted((ROOT / "content" / "posts").glob("*/index.md")):
            treffer = muster.search(pfad.read_text(encoding="utf-8"))
            if not treffer:
                continue
            funde = ph.befunde(treffer.group(1))
            if funde:
                befunde[pfad.parent.name] = funde
        self.assertEqual({}, befunde,
                         f"Hashtag-Defekte im Bestand: {befunde}")


class ApiGrenzeTests(unittest.TestCase):
    """Die letzte Instanz vor Pinterest: kein zweiter Block, kein Schnitt im Tag.

    Zwei Writer bauen den Text erst an der API-Grenze: `pinterest_engine`
    (Token-Pfad) und `generate_pins` (Repin-Rotation). `generate_pins` addierte
    früher blind `#GeldSparen #Spartipps #FranksFinanzcheck` HINTER den
    kuratierten Block – aus drei Quell-Tags wurden sechs Pin-Tags in
    CamelCase. Genau diese Stelle hätte #729 nach der Quell-Heilung wieder
    hergestellt.
    """

    def test_engine_pin_text_heilt_die_quelle(self):
        import pinterest_engine as pe
        text = pe.pin_text({"title": "T", "description": "D", "slug": "s",
                            "tags": ["DSL-Vergleich"], "keywords": ["Umzug Internet"],
                            "pin_description": "*Werbung | Text. #zählerstand #a1b #b2c #c3d"})
        self.assertEqual([], ph.befunde(text))
        self.assertEqual(["zaehlerstand", "a1b", "b2c"], ph.tags_normalisiert(text))

    def test_engine_fallback_haengt_den_block_ans_ende(self):
        import pinterest_engine as pe
        text = pe.pin_text({"title": "T", "description": "Satz. " * 60,
                            "slug": "lang-text", "tags": ["Fixkosten senken"],
                            "keywords": ["Haushalt sparen"]})
        self.assertLessEqual(len(text), ph.BESCHREIBUNG_MAX)
        self.assertEqual([], ph.befunde(text))
        self.assertEqual(3, len(ph.tags_normalisiert(text)))

    def test_generate_pins_addiert_keinen_zweiten_block(self):
        import generate_pins as gp
        text = gp.build_api_description({
            "description": "*Werbung | Text. #umzug #internet #rufnummer"})
        self.assertEqual(["umzug", "internet", "rufnummer"],
                         ph.tags_normalisiert(text))
        self.assertNotIn("GeldSparen", text)

    def test_generate_pins_fallback_bleibt_konform(self):
        import generate_pins as gp
        text = gp.build_api_description({"description": "Text ohne Tags"})
        self.assertEqual([], ph.befunde(text))
        self.assertTrue(ph.tags_normalisiert(text))
        self.assertLessEqual(len(text), ph.BESCHREIBUNG_MAX)

    def test_api_texte_der_ganzen_rede_bleiben_konform(self):
        """Jeder Bestandsartikel durch beide API-Bauer – die Wirkung, nicht die Absicht."""
        import generate_pins as gp
        import pinterest_engine as pe
        for post in gp.load_posts():
            for name, text in (
                ("generate_pins", gp.build_api_description(post)),
                ("pinterest_engine", pe.pin_text({
                    "title": post["title"], "description": post["description"],
                    "slug": post["slug"], "tags": [], "keywords": [],
                    "pin_description": post["description"]})),
            ):
                with self.subTest(slug=post["slug"], bauer=name):
                    self.assertEqual([], ph.befunde(text))
                    self.assertLessEqual(len(text), ph.BESCHREIBUNG_MAX)


class WirkungsprobeTests(unittest.TestCase):
    """Der Selbsttest und die Wirkungsprobe müssen Exit 0 liefern (C6/C29-Muster)."""

    def test_selftest_ist_grün(self):
        self.assertEqual([], ph._selftest())

    def test_selftest_als_skript(self):
        import subprocess
        lauf = subprocess.run([sys.executable, str(ROOT / "scripts" / "pinterest_hashtags.py"),
                               "--selftest"], capture_output=True, text=True,
                              cwd=ROOT, timeout=120)
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)

    def test_wirkungsprobe_als_skript(self):
        import subprocess
        lauf = subprocess.run([sys.executable, str(ROOT / "scripts" / "pinterest_hashtags.py"),
                               "--wirkungsprobe"], capture_output=True, text=True,
                              cwd=ROOT, timeout=120)
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)
        self.assertIn("#729", lauf.stdout)


if __name__ == "__main__":
    unittest.main()
