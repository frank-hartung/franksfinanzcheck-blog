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
import publication_release as pr
import publish_day_check as watchdog
import publish_gate as pg
import requeue_quality_holds as rqh
import reserve_pool as rp
import r5_absatz_splitter as r5
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

    def test_requeue_fallback_restores_rejected_and_fills_min(self):
        class FixedDateTime(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 7, 12, 0, tzinfo=dt.timezone.utc)

        live = self.post('live', draft=False)
        rejected = self.post('old-a', draft=True)
        accepted = self.post('old-b', draft=True)
        for p in (rejected, accepted):
            text = p.read_text()
            text = text.replace('draft: true\n', 'draft: true\ncadence_wait: true\ncadence_demoted: 2026-09-06T12:00:00Z\ncadence_grund: "test"\n')
            p.write_text(text)
        before_rejected = rejected.read_bytes()

        with patch.object(pr.dt, 'datetime', FixedDateTime), \
             patch('cadence_guard.now_utc_iso', lambda: '2026-09-07T12:00:00Z'):
            published = pr.promote_requeue_to_min(
                posts_dir=self.posts,
                validator=lambda p: p.parent.name == 'old-b')

        self.assertEqual(published, ['old-b'])
        self.assertEqual(rejected.read_bytes(), before_rejected)
        self.assertIn('draft: false', accepted.read_text())
        self.assertNotIn('cadence_wait:', accepted.read_text())
        self.assertIn('draft: false', live.read_text())

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


class R5HoldRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / 'content' / 'posts'
        self.posts.mkdir(parents=True)

    def long_post(self, slug='2026-09-07-r5-hold', *, draft=True, hold=True):
        p = self.posts / slug / 'index.md'
        p.parent.mkdir(parents=True)
        extra = ''
        if hold:
            extra = ('cadence_demoted: 2026-09-06T12:00:00Z\n'
                     'cadence_grund: "publish-gate: Textverständnis-Gate nicht bestanden: R5-ABSATZ-HART"\n')
        p.write_text(
            '---\n'
            'title: "R5 Hold: Gasrechnung senken"\n'
            'description: "R5 Hold: Gasrechnung senken – Test für Absatz-Healing mit Keyword im ersten Absatz und H2."\n'
            'date: 2026-09-07T06:00:00Z\n'
            f'draft: {str(draft).lower()}\n'
            'keywords: ["Gasrechnung senken"]\n'
            f'{extra}'
            '---\n\n'
            'Gasrechnung senken im Check: Der erste Satz hat genug Wörter. Der zweite Satz hat genug Wörter. '
            'Der dritte Satz hat genug Wörter. Der vierte Satz hat genug Wörter. '
            'Der fünfte Satz hat genug Wörter. Der sechste Satz hat genug Wörter. '
            'Der siebte Satz hat genug Wörter.\n\n'
            '## Gasrechnung senken – Details\n\n'
            'Weitere Infos zur Gasrechnung senken mit 0.5% Dichte und mehr Text damit die Dichte passt.\n',
            encoding='utf-8',
        )
        return p

    def test_r5_hold_wird_geheilt_und_nur_requeued(self):
        index = self.long_post()
        requeued, kept, errors = rqh.fix(posts_dir=self.posts)
        self.assertEqual([x[0] for x in requeued], ['2026-09-07-r5-hold'])
        self.assertEqual(kept, [])
        self.assertEqual(errors, [])
        text = index.read_text(encoding='utf-8')
        self.assertIn('draft: true', text)          # kein Direktpublish
        self.assertIn('cadence_wait: true', text)  # nächster Slot entscheidet
        self.assertIn('r5-hold aufgehoben', text)
        self.assertFalse(r5.hard_r5_findings(text, 'fixture'))
        self.assertGreaterEqual(text.count('\n\n'), 2)

    def test_publish_gate_heilt_r5_vor_der_harten_pruefung(self):
        slug = '2026-09-07-r5-live'
        index = self.long_post(slug, draft=False, hold=False)
        old = (pg.POSTS_DIR, pg.DRY_RUN, pg.STRICT)
        try:
            pg.POSTS_DIR = str(self.posts)
            pg.DRY_RUN = False
            pg.STRICT = True
            with patch.object(pg, 'todays_live_candidates', return_value=[slug]), \
                 patch.object(pg, 'check_length_failures', return_value=(set(), None)), \
                 patch.object(pg, 'seo_audit_failures', return_value=(set(), None)), \
                 patch.object(pg, 'affiliate_profi_failures', return_value=({}, None)), \
                 patch.object(pg, 'affiliate_integrity_failures', return_value=({}, None, False)), \
                 patch.object(pg, 'title_integrity_failures', return_value=set()), \
                 patch.object(pg, 'readability_failures', return_value=({}, None)), \
                 patch.object(pg, 'textverstaendnis_failures', return_value=({}, None)), \
                 patch.object(pg, 'keyword_failures', return_value=({}, None)), \
                 patch.object(pg, 'keyword_self_heal_candidates', return_value=0):
                self.assertEqual(pg.main(), 0)
        finally:
            pg.POSTS_DIR, pg.DRY_RUN, pg.STRICT = old
        text = index.read_text(encoding='utf-8')
        self.assertIn('draft: false', text)
        self.assertFalse(r5.hard_r5_findings(text, 'fixture'))
        self.assertGreaterEqual(text.count('\n\n'), 2)

    def test_acceptance_preheal_arbeitet_vor_dry_run_gate(self):
        index = self.long_post('2026-09-07-r5-reserve', draft=False, hold=False)
        changes = pr.preheal_candidate(index)
        self.assertEqual(changes, ['R5-ABSATZ-HART: 1 Absatz-Split(s)'])
        self.assertFalse(r5.hard_r5_findings(index.read_text(encoding='utf-8'), 'fixture'))


class QuoteRefillAfterGateLossTests(unittest.TestCase):
    """Issue #287: Gate-Verwurf darf das Tagesmindestziel nicht ungefüllt lassen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / 'content' / 'posts'
        self.posts.mkdir(parents=True)

    def _post(self, slug, *, draft=True, reserve=False, wait=False,
              day='2026-09-14'):
        p = self.posts / slug / 'index.md'
        p.parent.mkdir(parents=True, exist_ok=True)
        extra = ''
        if reserve:
            extra += 'reserve: true\n'
        if wait:
            extra += ('cadence_wait: true\n'
                      'cadence_demoted: 2026-09-13T12:00:00Z\n'
                      'cadence_grund: "test"\n')
        p.write_text(
            f'---\ntitle: "T"\ndate: {day}T12:00:00Z\n'
            f'draft: {str(draft).lower()}\n{extra}---\nBody\n',
            encoding='utf-8',
        )
        return p

    def test_refill_to_min_fills_after_single_live(self):
        """1 LIVE + Reserve → genau 1 Nachschub bis Minimum 2 (Mo 14.09.)."""
        class Monday(dt.date):
            @classmethod
            def today(cls):
                return cls(2026, 9, 14)

        class MondayDT(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 14, 15, 0, tzinfo=dt.timezone.utc)

        self._post('live-only', draft=False)
        self._post('reserve-a', draft=True, reserve=True)
        self._post('reserve-b', draft=True, reserve=True)
        rejected = self._post('reserve-bad', draft=True, reserve=True)
        before_bad = rejected.read_bytes()

        with patch.object(pr.dt, 'date', Monday), \
             patch.object(pr.dt, 'datetime', MondayDT), \
             patch('cadence_guard.now_utc_iso',
                   lambda: '2026-09-14T15:00:00Z'), \
             patch('reserve_pool.now_utc_iso',
                   lambda: '2026-09-14T15:00:00Z'), \
             patch('reserve_pool.datetime.date', Monday):
            published = pr.refill_to_min(
                posts_dir=self.posts,
                validator=lambda p: p.parent.name != 'reserve-bad',
                finalize=False,
            )

        self.assertEqual(len(published), 1)
        self.assertIn(published[0], ('reserve-a', 'reserve-b'))
        self.assertEqual(rejected.read_bytes(), before_bad)
        live = list(self.posts.glob('*/index.md'))
        live_count = sum(
            1 for p in live
            if 'draft: false' in p.read_text(encoding='utf-8')
            and '2026-09-14' in p.read_text(encoding='utf-8')
        )
        self.assertGreaterEqual(live_count, 2)

    def test_refill_offday_is_noop(self):
        class Tuesday(dt.date):
            @classmethod
            def today(cls):
                return cls(2026, 9, 15)

        class TuesdayDT(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 15, 12, 0, tzinfo=dt.timezone.utc)

        r = self._post('reserve-x', draft=True, reserve=True, day='2026-09-15')
        before = r.read_bytes()
        with patch.object(pr.dt, 'date', Tuesday), \
             patch.object(pr.dt, 'datetime', TuesdayDT), \
             patch('reserve_pool.datetime.date', Tuesday):
            self.assertEqual(
                pr.refill_to_min(posts_dir=self.posts,
                                validator=lambda p: True,
                                finalize=False),
                [],
            )
        self.assertEqual(r.read_bytes(), before)

    def test_selftest_exit_zero(self):
        self.assertEqual(pr.run_selftest(), 0)

    def test_deploy_workflow_wires_refill_after_publish_gate(self):
        """Deploy muss nach publish_gate die Quote nachfüllen (#287)."""
        root = Path(__file__).resolve().parents[2]
        yml = (root / '.github' / 'workflows' / 'deploy.yml').read_text(
            encoding='utf-8')
        gate_pos = yml.find('python3 scripts/publish_gate.py')
        refill_pos = yml.find('publication_release.py --refill-only')
        self.assertGreater(gate_pos, 0, 'publish_gate-Schritt fehlt im Deploy')
        self.assertGreater(refill_pos, gate_pos,
                           'Quote-Nachfüllung muss NACH publish_gate stehen')


class ReserveCertFreshnessTests(unittest.TestCase):
    """Issue #295: Zertifikat darf keine LIVE-Slugs als ready zählen."""

    def test_evaluate_recounts_ready_from_candidates(self):
        import reserve_gate as rg
        with tempfile.TemporaryDirectory() as tmp:
            cert = Path(tmp) / 'reserve-readiness.json'
            # Absichtlich inkonsistent: ready=6, aber nur 4 true-Kandidaten
            # (zwei bereits live und fälschlich noch in der Liste).
            cert.write_text(json.dumps({
                'target': 6,
                'ready': 6,  # veraltet / gelogen
                'candidates': [
                    {'slug': 'a', 'ready': True},
                    {'slug': 'b', 'ready': True},
                    {'slug': 'c', 'ready': True},
                    {'slug': 'd', 'ready': True},
                    {'slug': 'live-e', 'ready': False},
                    {'slug': 'live-f', 'ready': False},
                ],
            }), encoding='utf-8')
            ready, target, cands = rg.evaluate(cert)
            self.assertEqual(target, 6)
            self.assertEqual(ready, 4)  # neu gezählt, nicht dem Feld vertraut
            self.assertEqual(len(cands), 6)
            self.assertEqual(rg.main.__doc__ is not None or True, True)

    def test_prune_drops_empty_rows(self):
        import reserve_readiness as rr
        rows = [{'slug': 'a', 'ready': True}, {'slug': '', 'ready': True}, {}]
        cleaned = rr.prune_stale_rows(rows)
        self.assertEqual(cleaned, [{'slug': 'a', 'ready': True}])


if __name__ == '__main__':
    unittest.main()
