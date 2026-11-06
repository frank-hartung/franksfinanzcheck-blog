"""Regressionen für Index, Löschungen und fail-closed Fehlerpfade."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import konfliktmarker_wache as wache


class KonfliktmarkerTest(unittest.TestCase):
    def test_marker_und_ueberschrift(self):
        self.assertFalse(wache.pruefe_text('Titel\n=======\n', 'x'))
        self.assertTrue(wache.pruefe_text('<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> main\n', 'x'))
        self.assertTrue(wache.pruefe_text('>>>>>>> main\n', 'x'))

    def test_index_statt_arbeitsbaum_und_loeschung(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                subprocess.run(['git', *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init')
            git('config', 'user.email', 'test@example.org')
            git('config', 'user.name', 'Test')
            (root / 'x.md').write_text('sauber\n')
            git('add', 'x.md')
            git('commit', '-m', 'base')
            (root / 'x.md').write_text('<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> main\n')
            git('add', 'x.md')
            (root / 'x.md').write_text('sauber\n')
            with patch.object(wache, 'ROOT', root):
                self.assertTrue(wache._pruefe_dateien(wache._sammle('staged', None, None)))
                git('rm', '-f', 'x.md')
                self.assertEqual(wache._sammle('staged', None, None), [])

    def test_fehler_nicht_unterdruecken(self):
        with patch.object(wache, '_git', side_effect=subprocess.CalledProcessError(1, 'git')):
            with self.assertRaises(subprocess.CalledProcessError):
                wache._sammle('staged', None, None)
        with self.assertRaises(OSError):
            wache._sammle('paths', None, ['/pfad/nicht/vorhanden'])


if __name__ == '__main__':
    unittest.main()
