"""#826: maintenance must not invalidate even stale/broken editorial seals."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editorial_review_gate as gate
import meta_optimizer
import profi_polish
import unit_guard
import check_titles


class MaintenanceWritersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'index.md'
        self.raw = ('---\ntitle: "Tierkrankenversicherung für Hund & Katze: Kosten realistisch"\n'
                    'description: "Kurzer Text ohne Satzende"\ndraft: true\n'
                    'redaktionelle_pruefung:\n  status: freigegeben\n'
                    '  inhalt_sha256: absichtlich-ungueltig\n  naechste_pruefung: 2000-01-01\n'
                    '---\nKosten: 35 Euro und 71 Prozent.\n')
        self.path.write_text(self.raw)
        self.article = {'path': str(self.path), 'content': self.raw}

    def test_meta_optimizer_preserves_file_and_memory(self):
        self.assertFalse(meta_optimizer.fix_meta(self.article, use_ai=False))
        self.assertEqual(self.raw, self.path.read_text())
        self.assertEqual(self.raw, self.article['content'])

    def test_polish_cannot_touch_broken_seal(self):
        self.assertFalse(profi_polish.write_polished(self.article, 'Neue Aussage.'))
        self.assertEqual(self.raw, self.path.read_text())

    def test_units_keep_words_and_explicitly_report_skipped_article(self):
        report = Path(self.tmp.name) / 'report.md'
        with patch.object(unit_guard, 'target_files', return_value=[self.path]), \
             patch.object(unit_guard, 'ROOT', Path(self.tmp.name)), \
             patch.object(unit_guard, 'REPORT', report), \
             patch.object(unit_guard, 'DO_FIX', True), \
             patch.object(unit_guard, 'DRY_RUN', False):
            unit_guard.main()
        self.assertEqual(self.raw, self.path.read_text())
        self.assertIn('nicht stilistisch freigegeben', report.read_text())

    def test_title_protection_does_not_hide_unfixed_findings(self):
        post = {'file': str(self.path), 'title': 'x'}
        with patch.object(check_titles, 'collect', return_value=[post]), \
             patch.object(sys, 'argv', ['check_titles.py', '--fix']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, check_titles.main())
        self.assertEqual(self.raw, self.path.read_text())

    def test_reported_incidents_are_not_normalized_out_of_the_seal(self):
        fm_text, body = gate.split_article(self.raw)
        fm = gate._yaml_module().safe_load(fm_text)
        for new_body in (body.replace('Euro', '€'), body.replace('Prozent', '%'),
                         body.replace('Kosten', '[Kosten](/anderes-ziel/)')):
            self.assertNotEqual(gate.content_fingerprint(fm, body),
                                gate.content_fingerprint(fm, new_body))


if __name__ == '__main__':
    unittest.main()
