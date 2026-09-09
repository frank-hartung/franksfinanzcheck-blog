import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot_status
import grammar_check
import profi_polish
import publication_check as pc
import publish_day_check as watchdog
import reserve_pool as rp
import spellcheck


class Monday(dt.date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 7)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name)

    def post(self, slug, draft=True, reserve=False):
        p = self.posts / slug / 'index.md'
        p.parent.mkdir()
        p.write_text(f'---\ntitle: Test\ndate: 2026-09-07T06:00:00Z\ndraft: {str(draft).lower()}\nreserve: {str(reserve).lower()}\n---\nBody')
        return p

    def test_weekend_expected_day(self):
        for day in (5, 6, 7):
            self.assertEqual(pc.expected_day(dt.date(2026, 9, day)), dt.date(2026, 9, 4) if day < 7 else dt.date(2026, 9, 7))

    def test_drafts_never_satisfy_quota(self):
        self.post('a', draft=False)
        self.post('b')
        self.assertFalse(pc.check(dt.date(2026, 9, 7), posts_dir=self.posts)['ok'])

    def test_two_live_satisfy_source_only(self):
        self.post('a', draft=False)
        self.post('b', draft=False)
        self.assertTrue(pc.check(dt.date(2026, 9, 7), posts_dir=self.posts)['ok'])

    @patch('reserve_pool.now_utc_iso', lambda: '2026-09-07T12:00:00Z')
    @patch('reserve_pool.datetime.date', Monday)
    def test_rejected_reserve_restored_next_candidate_fills(self):
        rejected = self.post('a', reserve=True)
        before = rejected.read_bytes()
        self.post('b', reserve=True)
        self.post('c', reserve=True)
        manual = self.post('manual')
        published = rp.publish_to_min(posts_dir=self.posts, validator=lambda p: p.parent.name != 'a')
        self.assertEqual(published, ['b', 'c'])
        self.assertEqual(rejected.read_bytes(), before)
        self.assertIn('draft: true', manual.read_text())
        self.assertEqual(rp.publish_to_min(posts_dir=self.posts, validator=lambda p: True), [])

    @patch('reserve_pool.now_utc_iso', lambda: '2026-09-07T12:00:00Z')
    @patch('reserve_pool.datetime.date', Monday)
    def test_validator_error_restores_and_fails_closed(self):
        p = self.post('a', reserve=True)
        before = p.read_bytes()
        with self.assertRaises(RuntimeError):
            rp.publish_to_min(posts_dir=self.posts, validator=lambda p: (_ for _ in ()).throw(RuntimeError('gate unavailable')))
        self.assertEqual(p.read_bytes(), before)

    def test_offday_does_not_publish(self):
        class Tuesday(Monday):
            @classmethod
            def today(cls):
                return cls(2026, 9, 8)
        p = self.post('a', reserve=True)
        before = p.read_bytes()
        with patch('reserve_pool.datetime.date', Tuesday):
            self.assertEqual(rp.publish_to_min(posts_dir=self.posts, validator=lambda p: True), [])
        self.assertEqual(p.read_bytes(), before)

    def test_over_capacity_fails(self):
        for slug in ('a', 'b', 'c', 'd'):
            self.post(slug, draft=False)
        self.assertFalse(pc.check(dt.date(2026, 9, 7), posts_dir=self.posts)['ok'])

    @patch('reserve_pool.now_utc_iso', lambda: '2026-09-07T12:00:00Z')
    @patch('reserve_pool.datetime.date', Monday)
    def test_empty_reserve_cannot_fake_success(self):
        self.assertEqual(rp.publish_to_min(posts_dir=self.posts, validator=lambda p: True), [])
        self.assertFalse(pc.check(dt.date(2026, 9, 7), posts_dir=self.posts)['ok'])

    @patch('reserve_pool.now_utc_iso', lambda: '2026-09-08T00:00:00Z')
    @patch('reserve_pool.datetime.date', Monday)
    def test_midnight_rollover_keeps_draft(self):
        p = self.post('a', reserve=True)
        before = p.read_bytes()
        self.assertEqual(rp.publish_to_min(posts_dir=self.posts, validator=lambda p: True), [])
        self.assertEqual(p.read_bytes(), before)

    def test_real_html_class_list_and_soft_404(self):
        class Response:
            status = 200
            url = pc.BASE + '/posts/a/'
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'<div class="post-content md-content">Article</div>'
        self.assertTrue(pc.public_article('a', opener=lambda *a, **k: Response()))
        Response.url = pc.BASE + '/'
        self.assertFalse(pc.public_article('a', opener=lambda *a, **k: Response()))

    def test_network_errors_fail_closed(self):
        self.post('a', draft=False)
        self.post('b', draft=False)
        with patch('urllib.request.urlopen', side_effect=OSError('offline')):
            result = pc.check(dt.date(2026, 9, 7), True, self.posts)
        self.assertFalse(result['ok'])
        self.assertTrue(result['errors'])

    def test_watchdog_following_day_one_live_is_failure(self):
        class Tuesday(Monday):
            @classmethod
            def today(cls): return cls(2026, 9, 8)
        with patch.object(watchdog.datetime, 'date', Tuesday), patch.object(watchdog, 'articles_on', return_value=(['a'], ['b'])), redirect_stdout(io.StringIO()):
            self.assertEqual(watchdog.main(), 1)


class DraftScopedHealerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.post = Path(self.tmp.name) / 'draft-post' / 'index.md'
        self.post.parent.mkdir(parents=True)
        self.post.write_text(
            '---\n'
            'title: "Test"\n'
            'description: "Testbeschreibung."\n'
            'date: 2026-09-09T06:00:00Z\n'
            'draft: true\n'
            'ai_generated: true\n'
            '---\n\n'
            'Das ist ein Testtext.\n',
            encoding='utf-8',
        )

    def test_spellcheck_scoped_include_drafts(self):
        self.assertEqual(spellcheck.load_articles([str(self.post)]), [])
        arts = spellcheck.load_articles([str(self.post)], include_drafts=True)
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]['path'], str(self.post))

    def test_grammar_scoped_include_drafts(self):
        self.assertEqual(grammar_check.load_articles([str(self.post)]), [])
        arts = grammar_check.load_articles([str(self.post)], include_drafts=True)
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]['path'], str(self.post))

    def test_profi_polish_include_drafts(self):
        self.assertIsNone(profi_polish.load_article(str(self.post)))
        article = profi_polish.load_article(str(self.post), include_drafts=True)
        self.assertIsNotNone(article)
        self.assertEqual(article['path'], str(self.post))

    def test_engine_snapshot_uses_final_source_truth(self):
        posts = [
            {'slug': 'a', 'date': dt.date(2026, 9, 9), 'draft': True, 'state': 'hold'},
            {'slug': 'b', 'date': dt.date(2026, 9, 9), 'draft': True, 'state': 'manual'},
        ]
        level, note = bot_status.engine_snapshot(posts, dt.date(2026, 9, 9), 2, 3)
        self.assertEqual(level, 'WARN')
        self.assertIn('0 Artikel live heute', note)
        self.assertIn('2 Entwurf', note)
        self.assertIn('unter LIVE-Mindestziel', note)


if __name__ == '__main__':
    unittest.main()
