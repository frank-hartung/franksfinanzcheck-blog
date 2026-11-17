"""C25: lokale Prüfung braucht dieselben echten Abhängigkeiten wie CI."""
import re
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

    def test_every_hugo_workflow_uses_the_one_version(self):
        pin = (ROOT / 'requirements-hugo.txt').read_text().splitlines()[-1]
        version = re.fullmatch(r'hugo==([0-9.]+) --hash=sha256:[0-9a-f]{64}', pin)
        self.assertIsNotNone(version, 'one reviewed Linux wheel hash, not a multi-platform grab-bag')
        expected = version.group(1)
        action = (ROOT / '.github/actions/install-hugo/action.yml').read_text()
        self.assertIn(f'default: "{expected}"', action)
        self.assertIn(f'["{expected}"]=', action)
        self.assertIn('hugo v${EINGABE_VERSION}-', action,
                      'an older preinstalled Extended binary must not bypass the pin')
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            text = path.read_text()
            for found in re.findall(r'^\s+(?:version|HUGO_VERSION):\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', text, re.M):
                if 'install-hugo' in text:
                    with self.subTest(path=path.name):
                        self.assertEqual(expected, found)

    def test_dependabot_bumpt_hugo_nicht_allein(self):
        """`hugo` ist dreifach gekoppelt gepinnt – kein automatischer Bump.

        WARUM (17.11.2026, PR #1241)
        ---------------------------
        Dependabot schreibt bei `hugo` ALLE Plattform-Hashes derselben
        Version in eine Zeile. C25 erwartet genau EINEN geprüften
        Linux-Wheel-Hash, der zum verifizierten PyPI-Fallback der
        install-hugo-Action passt. Ein Dependabot-PR kann die drei Stellen
        (requirements-hugo.txt, action.yml, Workflow-Default) nicht mitziehen
        und ist deshalb strukturell rot. Ohne diese Sperre kommt derselbe
        rote PR jede Woche wieder – die Schleife ist der Fehler, nicht der PR.
        """
        cfg = yaml.safe_load((ROOT / '.github/dependabot.yml').read_text())
        pip_bloecke = [u for u in cfg['updates']
                       if u.get('package-ecosystem') == 'pip']
        self.assertTrue(pip_bloecke, 'pip-Block fehlt – Dependabot deckt Python nicht mehr ab')
        ignores = {i.get('dependency-name')
                   for block in pip_bloecke for i in (block.get('ignore') or [])}
        self.assertIn('hugo', ignores,
                      'hugo darf nicht automatisch gebumpt werden (C25, #1241)')

    def test_regression_runs_real_build_even_after_failure(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/publication-reliability-tests.yml').read_text())
        steps = workflow['jobs']['regression']['steps']
        build = next(s for s in steps if s.get('uses') == './.github/actions/hugo-build')
        self.assertEqual('${{ !cancelled() }}', build['if'])
        self.assertIn('--cleanDestinationDir', build['with']['args'])
        self.assertTrue(any(s.get('uses') == './.github/actions/install-hugo' for s in steps))
