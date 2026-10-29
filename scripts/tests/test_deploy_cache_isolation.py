#!/usr/bin/env python3
"""WF-54C4/#932: Cache-Störung darf Pages nicht als Geisel nehmen."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(yaml is None, "PyYAML nicht installiert")
class CacheIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.safe_load((ROOT / '.github/workflows/deploy.yml').read_text(encoding='utf-8'))
        cls.jobs = cls.workflow['jobs']
        cls.steps = cls.jobs['deploy']['steps']
        cls.cache = next(s for s in cls.steps if s.get('id') == 'gh_pages_cache')
        cls.seal = cls.jobs['release-seal']['steps'][0]

    def test_cache_ist_begrenzt_und_nicht_blockierend(self):
        self.assertTrue(self.cache['uses'].startswith('peaceiris/actions-gh-pages@'))
        self.assertIs(self.cache.get('continue-on-error'), True)
        self.assertGreater(self.cache.get('timeout-minutes', 0), 0)
        self.assertLessEqual(self.cache['timeout-minutes'], 15)
        self.assertFalse(self.cache.get('if'))
        self.assertTrue(self.cache['with']['force_orphan'])
        self.assertEqual(self.cache['with']['publish_branch'], 'gh-pages')
        upload = next(i for i, s in enumerate(self.steps) if s.get('uses', '').startswith('actions/upload-pages-artifact@'))
        self.assertLess(self.steps.index(self.cache), upload)
        # Die Upload- und Inhaltsgates dürfen nicht weichgeschaltet werden.
        self.assertFalse(self.steps[upload].get('continue-on-error', False))
        scorecard = next(s for s in self.steps if s.get('id') == 'scorecard')
        self.assertIn('exit 1', scorecard['run'])
        pages = self.jobs['pages-deployment']
        self.assertIn('deploy', pages['needs'])
        self.assertNotIn('always()', pages.get('if', ''))

    def test_urspruengliches_outcome_erreicht_siegel(self):
        self.assertIn('steps.gh_pages_cache.outcome', self.jobs['deploy']['outputs']['gh_pages_cache_outcome'])
        self.assertIn('needs.deploy.outputs.gh_pages_cache_outcome', self.seal['env']['GH_PAGES_CACHE_OUTCOME'])
        self.assertIn('pages-deployment', self.jobs['release-seal']['needs'])
        self.assertIn('always()', self.jobs['release-seal']['if'])

    def run_seal(self, **overrides):
        env = dict(os.environ, DEPLOY_ERGEBNIS='success', PAGES_ERGEBNIS='success',
                   ARTEFAKT_OK='true', GH_PAGES_CACHE_OUTCOME='success', SCORECARD_EXIT='0',
                   SCORECARD_WERKZEUGFEHLER='false', REFILL_WERKZEUGFEHLER='false',
                   WERKZEUGBEFUNDE='', WERKZEUGBEFUNDE_ANZAHL='0')
        env.update(overrides)
        with tempfile.TemporaryDirectory() as tmp:
            env['GITHUB_STEP_SUMMARY'] = str(Path(tmp) / 'summary')
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', self.seal['run']],
                                    env=env, text=True, capture_output=True, check=False)
            summary = Path(env['GITHUB_STEP_SUMMARY']).read_text(encoding='utf-8')
        return result, summary

    def test_siegel_faelle(self):
        cases = [
            ({}, 0, 'Auslieferungs-Siegel grün'),
            ({'GH_PAGES_CACHE_OUTCOME': 'failure'}, 1, 'gh-pages-Cache nicht aktualisiert'),
            ({'GH_PAGES_CACHE_OUTCOME': ''}, 1, 'gh-pages-Cache nicht aktualisiert'),
            ({'GH_PAGES_CACHE_OUTCOME': 'skipped'}, 1, 'gh-pages-Cache nicht aktualisiert'),
            ({'PAGES_ERGEBNIS': 'failure'}, 1, 'offizielle Pages-Deployment'),
            ({'ARTEFAKT_OK': '', 'DEPLOY_ERGEBNIS': 'failure', 'PAGES_ERGEBNIS': 'skipped',
              'GH_PAGES_CACHE_OUTCOME': ''}, 1, 'VOR der Auslieferung abgebrochen'),
            ({'SCORECARD_WERKZEUGFEHLER': 'true'}, 1, 'WERKZEUGFEHLER'),
        ]
        for overrides, code, message in cases:
            with self.subTest(overrides=overrides):
                result, summary = self.run_seal(**overrides)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertIn(message, result.stdout)
                self.assertIn('| gh-pages-Cache |', summary)
        result, _ = self.run_seal(GH_PAGES_CACHE_OUTCOME='failure')
        self.assertIn('Auslieferung belegt', result.stdout)
        self.assertIn('öffentlich raus', result.stdout)
        result, _ = self.run_seal(GH_PAGES_CACHE_OUTCOME='failure', PAGES_ERGEBNIS='failure')
        self.assertIn('NICHT belegt', result.stdout)


if __name__ == '__main__':
    unittest.main()
