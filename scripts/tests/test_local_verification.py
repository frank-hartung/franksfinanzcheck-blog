"""C25: lokale Prüfung braucht dieselben echten Abhängigkeiten wie CI."""
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


class LocalVerificationTests(unittest.TestCase):
    def test_local_setup_is_hash_locked_and_fail_closed(self):
        script = (ROOT / 'scripts/verify_local.sh').read_text()
        self.assertIn('set -euo pipefail', script)
        self.assertIn('--require-hashes -r requirements-ci.txt -r requirements-hugo.txt', script)
        self.assertIn('python -m unittest discover', script)
        self.assertIn('hugo --minify', script)
        self.assertIn('mktemp -d', script)

    def test_hugo_pin_matches_ci_fallback(self):
        pin = (ROOT / 'requirements-hugo.txt').read_text().splitlines()[-1]
        version, digest = pin.removeprefix('hugo==').split(' --hash=sha256:')
        action = (ROOT / '.github/actions/install-hugo/action.yml').read_text()
        self.assertIn(f'["{version}"]="{digest}"', action)

    def test_regression_runs_real_build_even_after_failure(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/publication-reliability-tests.yml').read_text())
        steps = workflow['jobs']['regression']['steps']
        build = next(s for s in steps if s.get('uses') == './.github/actions/hugo-build')
        self.assertEqual('${{ !cancelled() }}', build['if'])
        self.assertIn('--cleanDestinationDir', build['with']['args'])
        self.assertTrue(any(s.get('uses') == './.github/actions/install-hugo' for s in steps))
