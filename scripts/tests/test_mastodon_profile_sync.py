"""Offline-Vertrag für glaubwürdige Profiltexte und sichere Vorschau."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import mastodon_profile_sync as profile


class TestProfile(unittest.TestCase):
    def test_limits(self):
        profile.validate_lengths()
        self.assertEqual(len(profile.FIELDS), 4)

    def test_positionierung_ohne_veraltete_claims(self):
        text = profile.DISPLAY_NAME + profile.NOTE
        # Sparsumme/Zähler/Auto-Flirten bleiben verboten – die Publikationsroutine
        # Mo/Mi/Fr ist seit 06.11.2026 EINER verbindlichen Dauervorgabe entnommen
        # (docs/CADENCE-REPORT.md Regel 2) und daher AUSDRÜCKLICH erwünscht.
        for claim in ('1.800', '25+', 'antworte persönlich'):
            self.assertNotIn(claim, text)
        self.assertIn('Affiliate', text)
        self.assertIn('4K-Kompass', text)
        self.assertIn('Mo/Mi/Fr', text)

    def test_bio_nennt_publikationsroutine_als_dauervorgabe(self):
        # Die Bio muss die Mo/Mi/Fr-Veröffentlichungsroutine nennen (2–3 Artikel
        # pro Publikationstag) – einmalig und ohne Uhrzeitversprechen.
        self.assertIn('Mo/Mi/Fr', profile.NOTE)
        self.assertIn('Publikationstag', profile.NOTE)
        self.assertNotIn('MESZ', profile.NOTE)   # kein Uhrzeit-/Zeitversprechen
        self.assertNotIn('Uhr', profile.NOTE)
        self.assertLessEqual(len(profile.NOTE), 500)

    def test_dry_run_ohne_netz_oder_report(self):
        with patch.object(profile, 'DRY_RUN', True), \
             patch.object(profile.urllib.request, 'urlopen') as network, \
             patch.object(profile.Path, 'write_text') as write:
            profile.main()
        network.assert_not_called()
        write.assert_not_called()

    def test_fehlender_token_ist_kein_erfolg(self):
        with patch.object(profile, 'DRY_RUN', False), \
             patch.object(profile, 'MASTODON_TOKEN', ''):
            with self.assertRaises(SystemExit):
                profile.main()

    def test_ungueltige_bio_wird_abgelehnt(self):
        with patch.object(profile, 'NOTE', 'x' * 501):
            with self.assertRaises(SystemExit):
                profile.validate_lengths()

    def test_payload_erhaelt_bot_flag(self):
        with patch.object(profile, 'DRY_RUN', False), \
             patch.object(profile, 'MASTODON_TOKEN', 'test'), \
             patch.object(profile.urllib.request, 'urlopen', side_effect=OSError('offline')) as network:
            with self.assertRaises(SystemExit):
                profile.main()
        request = network.call_args.args[0]
        self.assertNotIn(b'name="bot"', request.data)
        self.assertIn(b'name="discoverable"', request.data)
        self.assertIn(b'name="indexable"', request.data)
        self.assertEqual(request.method, 'PATCH')

    def test_redaktionsvorlagen_passen_in_500_zeichen(self):
        import re
        doc = (SCRIPTS.parent / 'docs' / 'MASTODON-WACHSTUMSPLAN.md').read_text()
        posts = re.findall(r'```text\n(.*?)\n```', doc, re.S)
        self.assertEqual(len(posts), 9)
        for post in posts:
            with self.subTest(post=post[:50]):
                self.assertLessEqual(len(post), 500)
                self.assertNotIn('/go/', post)
                for url in re.findall(r'https://franksfinanzcheck.de(/[^\s]*)', post):
                    path = url.split('?')[0].strip('/')
                    self.assertTrue((SCRIPTS.parent / 'content' / path / 'index.md').is_file())
