#!/usr/bin/env python3
"""Regressionen für Nachlauf und rennsicheren Nachzug (#1120)."""
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import faktenfrische_befund_akte as akte
import veroeffentlichungs_wache as nachlauf


class ProjektionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.state = root / 'state.json'
        self.md = root / 'akte.md'
        self.tag = dt.date(2026, 11, 7)
        self.alt = {'erzeugt': 'alt', 'stichtag': str(self.tag), 'offen': 1,
                    'befunde': [{'id': 'alt', 'fassung_status': 'aktuell'}]}
        self.state.write_text(json.dumps(self.alt), encoding='utf-8')
        self.md.write_text('original', encoding='utf-8')
        self.projektion = ('original', dict(self.alt, erzeugt='neu'))
        for name, value in [('STATE_PATH', self.state), ('AKTE_PATH', self.md)]:
            p = patch.object(akte, name, value)
            p.start(); self.addCleanup(p.stop)
        p = patch.object(akte.ledger, 'wache', return_value={'offen': 1, 'gruen': True})
        p.start(); self.addCleanup(p.stop)
        p = patch.object(akte, 'projektion', side_effect=lambda tag: self.projektion)
        self.projektions_mock = p.start(); self.addCleanup(p.stop)

    def test_zeitstempel_allein_ist_keine_aenderung(self):
        self.assertFalse(akte.wache()['veraltet'])
        self.projektions_mock.assert_called_once_with(self.tag)

    def test_gleiche_anzahl_anderer_befund_oder_fassung(self):
        for befund in ({'id': 'neu', 'fassung_status': 'aktuell'},
                       {'id': 'alt', 'fassung_status': 'ueberholt'}):
            with self.subTest(befund=befund):
                self.projektion = ('original', dict(self.alt, befunde=[befund]))
                self.assertTrue(akte.wache()['veraltet'])
                funde, fehler = nachlauf.pruefe_akte(str(ROOT))
                self.assertEqual(len(funde), 1)
                self.assertEqual(fehler, [])

    def test_markdown_fehlt_oder_ist_veraendert(self):
        self.md.write_text('veraltet', encoding='utf-8')
        self.assertTrue(akte.wache()['veraltet'])
        self.md.unlink()
        self.assertTrue(akte.wache()['veraltet'])

    def test_kaputter_zustand_ist_nicht_gruen(self):
        for text in ('null', '{}', '{', json.dumps(dict(self.alt, stichtag='9999-01-01'))):
            self.state.write_text(text, encoding='utf-8')
            self.assertTrue(akte.wache()['veraltet'])

    def test_ledgerfehler_bleibt_werkzeugfehler(self):
        with patch.object(akte, 'projektion', side_effect=akte.ledger.LedgerFehler('kaputt')):
            with self.assertRaises(akte.ledger.LedgerFehler):
                akte.wache()


class EchteProjektionTests(unittest.TestCase):
    def test_wechsel_bei_gleicher_anzahl_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            fund = {'slug': 'seite', 'id': 'alt', 'typ': 'luecke',
                    'text': 'Unbelegte Zahl', 'beleg': '', 'alter_tage': 1,
                    'fassung_status': 'aktuell', 'entscheidbar': True}
            with patch.object(akte, 'ROOT', root), \
                 patch.object(akte, 'AKTE_PATH', root / 'BEFUND-AKTE.md'), \
                 patch.object(akte, 'STATE_PATH', root / 'data/state.json'), \
                 patch.object(akte.ledger, 'wache', return_value={'offen': 1, 'gruen': True}), \
                 patch.object(akte.ledger, 'befunde_mit_status', return_value=[fund]) as messen, \
                 patch.object(akte, 'live_seiten', return_value={}), \
                 patch.object(akte, '_config', return_value={'frist_tage': 14, 'eskalation_tage': 21}):
                akte.erstellen(dt.date(2026, 11, 7))
                self.assertFalse(akte.wache()['veraltet'])
                messen.return_value = [dict(fund, id='neu')]
                self.assertTrue(akte.wache()['veraltet'])
                self.assertIn('--entscheiden alt', (root / 'BEFUND-AKTE.md').read_text())
                akte.erstellen(dt.date(2026, 11, 7))
                self.assertFalse(akte.wache()['veraltet'])
                self.assertIn('--entscheiden neu', (root / 'BEFUND-AKTE.md').read_text())


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.origin = self.base / 'origin.git'
        self.seed = self.base / 'seed'
        self.worker = self.base / 'worker'
        self.other = self.base / 'other'
        self.git('init', '--bare', str(self.origin))
        self.git('init', '-b', 'main', str(self.seed))
        self.git('-C', str(self.seed), 'config', 'user.email', 'test@example.org')
        self.git('-C', str(self.seed), 'config', 'user.name', 'Test')
        (self.seed / 'scripts').mkdir(); (self.seed / 'data').mkdir()
        shutil.copy(ROOT / 'scripts/befund_akte_sync.sh', self.seed / 'scripts')
        (self.seed / 'quelle').write_text('eins', encoding='utf-8')
        (self.seed / 'BEFUND-AKTE.md').write_text('alt', encoding='utf-8')
        (self.seed / 'data/faktenfrische_befunde_state.json').write_text('alt', encoding='utf-8')
        (self.seed / 'scripts/faktenfrische_befund_akte.py').write_text(
            "from pathlib import Path\ns = Path('quelle').read_text()\n"
            "Path('BEFUND-AKTE.md').write_text(s)\n"
            "Path('data/faktenfrische_befunde_state.json').write_text(s)\n", encoding='utf-8')
        (self.seed / 'scripts/konfliktmarker_wache.py').write_text('pass\n', encoding='utf-8')
        self.git('-C', str(self.seed), 'add', '.')
        self.git('-C', str(self.seed), 'commit', '-m', 'initial')
        self.git('-C', str(self.seed), 'remote', 'add', 'origin', str(self.origin))
        self.git('-C', str(self.seed), 'push', 'origin', 'main')
        self.git('clone', '-b', 'main', str(self.origin), str(self.worker))
        self.git('clone', '-b', 'main', str(self.origin), str(self.other))
        self.git('-C', str(self.other), 'config', 'user.email', 'test@example.org')
        self.git('-C', str(self.other), 'config', 'user.name', 'Test')
        self.env = dict(os.environ, GITHUB_ACTIONS='true', GITHUB_REF='refs/heads/main')

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout

    def sync(self, env=None):
        return subprocess.run(['bash', 'scripts/befund_akte_sync.sh'], cwd=self.worker,
                              env=env or self.env, capture_output=True, text=True)

    def test_nachzug_und_idempotenz(self):
        r = self.sync(); self.assertEqual(r.returncode, 0, r.stderr)
        sha = self.git('--git-dir', str(self.origin), 'rev-parse', 'main')
        r = self.sync(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sha, self.git('--git-dir', str(self.origin), 'rev-parse', 'main'))
        self.assertEqual(self.git('--git-dir', str(self.origin), 'show', 'main:BEFUND-AKTE.md'), 'eins')

    def test_push_rennen_berechnet_auf_neuem_stand(self):
        bindir = self.base / 'bin'; bindir.mkdir()
        wrapper = bindir / 'git'
        real_git = shutil.which('git')
        wrapper.write_text(f'''#!/usr/bin/env bash
if [[ "$1" == push && ! -e "$RACE_DONE" ]]; then
  touch "$RACE_DONE"
  echo -n zwei > "$OTHER/quelle"
  "{real_git}" -C "$OTHER" add quelle
  "{real_git}" -C "$OTHER" commit -m fremd
  "{real_git}" -C "$OTHER" push origin main
fi
exec "{real_git}" "$@"
''', encoding='utf-8')
        wrapper.chmod(0o755)
        env = dict(self.env, PATH=str(bindir) + os.pathsep + os.environ['PATH'],
                   OTHER=str(self.other), RACE_DONE=str(self.base / 'done'))
        r = self.sync(env); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for path in ('quelle', 'BEFUND-AKTE.md', 'data/faktenfrische_befunde_state.json'):
            self.assertEqual(self.git('--git-dir', str(self.origin), 'show', 'main:' + path), 'zwei')

    def test_unsauberes_checkout_und_falscher_ref_stoppen(self):
        (self.worker / 'quelle').write_text('lokal', encoding='utf-8')
        self.assertNotEqual(self.sync().returncode, 0)
        self.assertEqual((self.worker / 'quelle').read_text(), 'lokal')
        env = dict(self.env, GITHUB_REF='refs/heads/anderer')
        self.assertNotEqual(self.sync(env).returncode, 0)

    def test_wiederholte_pushfehler_bleiben_rot(self):
        bindir = self.base / 'bin'; bindir.mkdir()
        wrapper = bindir / 'git'
        real_git = shutil.which('git')
        wrapper.write_text(f'''#!/usr/bin/env bash
if [[ "$1" == push ]]; then exit 1; fi
exec "{real_git}" "$@"
''', encoding='utf-8')
        wrapper.chmod(0o755)
        env = dict(self.env, PATH=str(bindir) + os.pathsep + os.environ['PATH'])
        r = self.sync(env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('fünf Versuchen', r.stderr)
        self.assertEqual(self.git('--git-dir', str(self.origin), 'show',
                                  'main:BEFUND-AKTE.md'), 'alt')


class WorkflowTests(unittest.TestCase):
    def test_zeitlauf_und_sicherer_sync_sind_verdrahtet(self):
        import yaml
        workflow = yaml.load((ROOT / '.github/workflows/befund-akte-nachziehen.yml')
                             .read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
        self.assertTrue(workflow['on']['schedule'])
        self.assertEqual(workflow['jobs']['nachziehen']['if'],
                         "github.ref == 'refs/heads/main'")
        commands = '\n'.join(step.get('run', '') for step in
                             workflow['jobs']['nachziehen']['steps'])
        self.assertIn('scripts/befund_akte_sync.sh', commands)
        self.assertIn('scripts.tests.test_befund_akte_nachlauf', commands)
        self.assertIn('scripts/faktenfrische_befund_ledger.py --struktur-pruefen', commands)

    def test_faktenlauf_committet_auch_nur_akte(self):
        text = (ROOT / '.github/workflows/faktenfrische.yml').read_text(encoding='utf-8')
        self.assertIn('git status --porcelain -- content/ data/ FAKTENFRISCHE-REPORT.md BEFUND-AKTE.md', text)


if __name__ == '__main__':
    unittest.main()
