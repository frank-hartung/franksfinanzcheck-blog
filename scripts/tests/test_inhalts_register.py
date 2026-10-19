"""Tests für Inhalts-Wache (FF1–FF5), Fachprüfungs-Register und Kannibalisierungs-Map.

Ausführen: python3 -m unittest discover -s scripts/tests
"""
import glob
import os
import re
import unittest

import scripts.ff_inhalts_wache as ff
import scripts.fachpruefung_register as fpr
import scripts.abbildungen_ableiten as abb

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ExperienceTests(unittest.TestCase):
    def test_ich_habe_wird_erkannt(self):
        self.assertTrue(ff.find_experience("Ich habe alle drei Methoden getestet."))

    def test_meine_erfahrung_wird_erkannt(self):
        self.assertTrue(ff.find_experience("Meine Erfahrung: Wer antizyklisch sucht, gewinnt."))

    def test_fallstudie_ohne_fiktiv_wird_erkannt(self):
        self.assertTrue(ff.find_experience("Fallstudie: Max, 28, Software-Entwickler"))

    def test_fallstudie_als_fiktiv_gekennzeichnet_ist_ok(self):
        self.assertFalse(ff.find_experience("Rechenbeispiel mit einer fiktiven Person: Max, 28"))

    def test_zitierte_vorlage_ist_ok(self):
        self.assertFalse(ff.find_experience('Vorlage: „Ich habe am 18.40 Uhr eine Störung gemeldet“'))

    def test_mixed_quote_vorlage_ist_ok(self):
        # Regression: Vorlage mit öffnendem „ und schließendem geraden " (Störungs-Beitrag, 19.10.)
        line = 'Schreibe danach: „Ich habe am heutigen Tag um 18:40 Uhr eine Störung gemeldet."'
        self.assertFalse(ff.find_experience(line))

    def test_checkliste_ist_ok(self):
        self.assertFalse(ff.find_experience("- [ ] Ich habe ein separates Konto für die Reserve"))

    def test_selftest_laeuft_durch(self):
        self.assertEqual(ff.selftest(), 0)


class FormulaAndLiveTests(unittest.TestCase):
    def test_formel_titel_erkannt(self):
        self.assertIsNotNone(ff.FORMULA.search("Internet & DSL: Was sich jetzt für dich ändert"))

    def test_front_und_live(self):
        front, body = ff._front_and_body('---\ntitle: "X"\ndraft: true\n---\nText')
        self.assertIn('title: "X"', front)
        self.assertFalse(ff._is_live(front))
        self.assertEqual(body.strip(), "Text")

    def test_template_links_fuer_versiegelte_und_reserve_beitraege(self):
        sealed = 'pillar: "versicherungen"\nredaktionelle_pruefung:\n  inhalt_sha256: "' + ("a" * 64) + '"'
        self.assertTrue(ff._has_template_links(sealed))
        reserve_future = 'pillar: "strom-sparen"\nreserve_published: 2026-10-21'
        self.assertTrue(ff._has_template_links(reserve_future))
        reserve_old = 'pillar: "strom-sparen"\nreserve_published: 2026-10-10'
        self.assertFalse(ff._has_template_links(reserve_old))
        no_pillar = 'inhalt_sha256: "' + ("a" * 64) + '"'
        self.assertFalse(ff._has_template_links(no_pillar))

    def test_live_wache_ist_gruen(self):
        """Der Repo-Stand muss die Wache bestehen (FF1–FF5)."""
        self.assertEqual(ff.run_checks(), [])


class AbbildungenTests(unittest.TestCase):
    def test_slugs_ohne_pyyaml(self):
        slugs = abb.load_slugs()
        self.assertEqual(len(slugs), 20)
        self.assertEqual(len(set(slugs)), 20)

    def test_top20_haben_zwei_abbildungen(self):
        self.assertEqual(abb.check(abb.load_slugs()), [])


class FachpruefungRegisterTests(unittest.TestCase):
    def test_register_ist_aktuell(self):
        self.assertEqual(fpr.main(["--check"]), 0)

    def test_keine_freigabe_und_kein_pruefer_erfunden(self):
        text = fpr.render(fpr.collect())
        self.assertIn("pruefer: null", text)
        self.assertNotIn("freigegeben", text.lower())


class KannibalisierungMapTests(unittest.TestCase):
    def test_alle_slugs_existieren(self):
        ids = {os.path.basename(os.path.dirname(p))
               for p in glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md"))}
        with open(os.path.join(BLOG_DIR, "data", "kannibalisierung_map.yaml"), encoding="utf-8") as fh:
            slugs = re.findall(r'slug: "([^"]+)"', fh.read())
        self.assertGreater(len(slugs), 20)
        missing = [s for s in slugs if s not in ids]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
