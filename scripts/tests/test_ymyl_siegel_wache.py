"""Siegelwache prüft Fassungsdrift, ersetzt aber keine Fachprüfung."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editorial_review_gate as gate
import ymyl_siegel_wache as wache


class SiegelwacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'index.md'
        self.fm = {'title': 'Versicherung', 'description': 'Geprüft', 'draft': True,
                   'redaktionelle_pruefung': {'status': 'freigegeben', 'naechste_pruefung': '2000-01-01'}}
        self.body = '\nText.\n'
        self.fm['redaktionelle_pruefung']['inhalt_sha256'] = gate.content_fingerprint(self.fm, self.body)

    def write(self, fm=None, body=None):
        self.path.write_text('---\n' + gate._yaml_module().safe_dump(
            fm if fm is not None else self.fm, allow_unicode=True, sort_keys=False) +
            '---\n' + (self.body if body is None else body), encoding='utf-8')

    def test_siegel_gueltig_auch_wenn_review_abgelaufen(self):
        self.write()
        self.assertIsNone(wache.pruefe_pfad(self.path))

    def test_beschreibung_text_und_protokoll_drift(self):
        for field in ('description', 'body', 'review'):
            fm = copy.deepcopy(self.fm)
            body = self.body
            if field == 'description': fm['description'] = 'Gekürzt'
            elif field == 'body': body += 'Verändert.\n'
            else: fm['redaktionelle_pruefung']['naechste_pruefung'] = '2030-01-01'
            self.write(fm, body)
            self.assertIn('E17', wache.pruefe_pfad(self.path), field)

    def test_fehlendes_siegel_bei_approved_blockiert(self):
        fm = copy.deepcopy(self.fm)
        fm['redaktionelle_pruefung'] = {'status': 'approved'}
        self.write(fm)
        self.assertIn('E17', wache.pruefe_pfad(self.path))
        self.assertTrue(gate.automatic_write_protected(self.path))
        old = self.path.read_text()
        self.assertTrue(gate.automatic_change_findings(old, old.replace('Geprüft', 'Gekürzt')))

    def test_offener_entwurf_und_betriebsdaten_erlaubt(self):
        fm = copy.deepcopy(self.fm)
        fm['draft'] = False
        self.write(fm)
        self.assertIsNone(wache.pruefe_pfad(self.path))
        fm['redaktionelle_pruefung'] = {'status': 'ausstehend'}
        self.write(fm)
        self.assertIsNone(wache.pruefe_pfad(self.path))

    def test_parsefehler_und_lesefehler_blockieren(self):
        self.path.write_text('---\ntitle: [\n---\nText', encoding='utf-8')
        self.assertIn('nicht prüfbar', wache.pruefe_pfad(self.path))
        self.path.unlink()
        self.assertIn('nicht prüfbar', wache.pruefe_pfad(self.path))

    def test_cli_blockiert_drift(self):
        self.write(body='\nGeändert.\n')
        with patch.object(gate, 'all_post_paths', return_value=[self.path]), patch.object(gate, 'ROOT', self.path.parent):
            self.assertEqual(wache.main([]), 1)

    def test_siegelrueckzug_nur_ausdruecklich_als_entwurf(self):
        self.write()
        old = self.path.read_text(encoding='utf-8')
        fm = copy.deepcopy(self.fm)
        fm.pop('redaktionelle_pruefung')
        self.write(fm)
        self.assertIn('still entfernt', wache.pruefe_rueckzug(old, self.path.read_text()))
        fm['redaktionelle_pruefung'] = {'status': 'ausstehend', 'vorheriger_pruefer': {'name': 'Archiv'}}
        fm['draft'] = False
        self.write(fm)
        self.assertIn('still entfernt', wache.pruefe_rueckzug(old, self.path.read_text()))
        fm['draft'] = True
        fm['redaktionelle_pruefung']['pruefer'] = {'name': 'Alt'}
        self.write(fm)
        self.assertIn('still entfernt', wache.pruefe_rueckzug(old, self.path.read_text()))
        fm['redaktionelle_pruefung'].pop('pruefer')
        self.write(fm)
        self.assertIsNone(wache.pruefe_rueckzug(old, self.path.read_text()))
        self.assertIn('nicht prüfbar', wache.pruefe_rueckzug('unlesbar', self.path.read_text()))

    def test_git_basisvergleich_erkennt_stillen_rueckzug(self):
        import subprocess
        def git(root, *args):
            return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, 'init', '-q')
            path = root / 'content/posts/a/index.md'
            path.parent.mkdir(parents=True)
            self.write()
            path.write_text(self.path.read_text(), encoding='utf-8')
            git(root, 'add', '.')
            git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'Basis')
            base = git(root, 'rev-parse', 'HEAD')
            fm = copy.deepcopy(self.fm)
            fm.pop('redaktionelle_pruefung')
            self.write(fm)
            path.write_text(self.path.read_text(), encoding='utf-8')
            git(root, 'add', '.')
            git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-qm', 'Aenderung')
            with patch.object(gate, 'ROOT', root):
                errors = wache.pruefe_base(base)
                self.assertEqual(len(errors), 1)
                self.assertIn('still entfernt', errors[0][1])
                with patch.object(gate, 'all_post_paths', return_value=[]):
                    self.assertEqual(wache.main(['--base', 'ungueltig']), 1)
                    self.assertEqual(wache.main(['--base', '']), 1)

    def test_workflow_pr_push_ohne_ticket_schreibrecht(self):
        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/ymyl-siegelwache.yml'
        config = gate._yaml_module().load(workflow.read_text(), Loader=gate._yaml_module().BaseLoader)
        self.assertIn('pull_request', config['on'])
        self.assertIn('push', config['on'])
        self.assertEqual(config['permissions'], {'contents': 'read'})
        steps = config['jobs']['siegel']['steps']
        commands = '\n'.join(step.get('run', '') for step in steps)
        self.assertIn('scripts/ymyl_siegel_wache.py', commands)
        self.assertIn('scripts.tests.test_metadaten_wache', commands)


if __name__ == '__main__':
    unittest.main()
