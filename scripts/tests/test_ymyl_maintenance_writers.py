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

    def test_dash_guard_preserves_sealed_article(self):
        import dash_guard
        dash_raw = self.raw.replace(
            'Kosten: 35 Euro und 71 Prozent.\n',
            'Kosten: 35 Euro - und 71 Prozent - im Vergleich.\n',
        )
        self.path.write_text(dash_raw, encoding='utf-8')
        report = Path(self.tmp.name) / 'dash_report.md'
        with patch.object(dash_guard, 'target_files', return_value=[self.path]), \
             patch.object(dash_guard, 'ROOT', Path(self.tmp.name)), \
             patch.object(dash_guard, 'REPORT', report), \
             patch.object(dash_guard, 'DO_FIX', True), \
             patch.object(dash_guard, 'DRY_RUN', False), \
             contextlib.redirect_stdout(io.StringIO()):
            dash_guard.main()
        self.assertEqual(dash_raw, self.path.read_text(encoding='utf-8'))

    def test_draft_link_healer_and_url_hygiene_preserve_sealed_article(self):
        import draft_link_healer
        import fix_url_hygiene
        link_raw = self.raw + '\nSiehe [Entwurf](../../posts/fehlt-komplett/) und [Spalt](/posts/a%20b/).\n'
        post_dir = Path(self.tmp.name) / 'posts' / 'sealed-post'
        post_dir.mkdir(parents=True)
        p = post_dir / 'index.md'
        p.write_text(link_raw, encoding='utf-8')
        with patch.object(draft_link_healer, 'list_post_paths', return_value=[str(p)]), \
             patch.object(draft_link_healer, 'list_section_pages', return_value=[]):
            draft_link_healer.scan(do_fix=True, dry_run=False)
        self.assertEqual(link_raw, p.read_text(encoding='utf-8'))

        slug_dir = Path(self.tmp.name) / 'posts' / 'ab'
        slug_dir.mkdir(parents=True)
        with patch.object(fix_url_hygiene, 'ROOT', Path(self.tmp.name)), \
             contextlib.redirect_stdout(io.StringIO()):
            fix_url_hygiene.run_fix(root=Path(self.tmp.name) / 'posts',
                                    posts_dir=Path(self.tmp.name) / 'posts',
                                    do_write=True)
        self.assertEqual(link_raw, p.read_text(encoding='utf-8'))

    def test_pinterest_seo_healer_keeps_title_and_description_sealed(self):
        import pinterest_seo_healer
        post_dir = Path(self.tmp.name) / '2026-09-21-test-haftpflicht'
        post_dir.mkdir(parents=True)
        p = post_dir / 'index.md'
        p.write_text(self.raw, encoding='utf-8')
        with patch.object(pinterest_seo_healer, 'list_post_paths', return_value=[str(p)]):
            art = pinterest_seo_healer.load_articles()[0]
        pinterest_seo_healer.heal_article(art)
        after = p.read_text(encoding='utf-8')
        self.assertEqual([], gate.automatic_change_findings(self.raw, after))

    def test_kurzantwort_and_update_articles_refuse_sealed_mutation(self):
        import generate_kurzantworten
        import update_articles
        self.assertFalse(generate_kurzantworten.set_kurzantwort(
            str(self.path),
            'Eine neue Kurzantwort, die das Siegel brechen würde.',
        ))
        self.assertEqual(self.raw, self.path.read_text(encoding='utf-8'))

        fm_part, body_part = gate.split_article(self.raw)
        art = {'path': str(self.path), 'content': self.raw, 'fm': fm_part, 'body': body_part}
        self.assertIsNone(update_articles.set_lastmod(art, 'Geänderter Body.\n'))
        self.assertEqual(self.raw, self.path.read_text(encoding='utf-8'))

    def test_all_scheduled_unlocked_writers_enforce_ymyl_guard(self):
        scripts_dir = Path(__file__).resolve().parents[1]
        expected = (
            'affiliate_intent_guard.py',
            'affiliate_link_check.py',
            'affiliate_profi_check.py',
            'compound_guard.py',
            'dash_guard.py',
            'draft_link_healer.py',
            'duplikat_guard.py',
            'emoji_guard.py',
            'fix_linebreaks.py',
            'fix_url_hygiene.py',
            'generate_kurzantworten.py',
            'pinterest_seo_healer.py',
            'table_guard.py',
            'update_articles.py',
        )
        for name in expected:
            with self.subTest(script=name):
                src = (scripts_dir / name).read_text(encoding='utf-8')
                self.assertIn('automatic_change_findings', src)


if __name__ == '__main__':
    unittest.main()
