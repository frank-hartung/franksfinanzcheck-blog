import sys
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ki_cover_render_audit as audit


class KiCoverRenderAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / 'static/images/test.jpg'
        self.image.parent.mkdir(parents=True)
        self.image.write_bytes(b'original')
        self.entry = {'title': 'Test', 'design': {'badge': 'TEST', 'savings': '', 'v': 3}}

    def run_render(self, generated, pixels=False):
        def render(gc, title, badge, savings, output):
            Path(output).write_bytes(generated)
        checker = types.SimpleNamespace(_gc=lambda: None, render_to=render,
                                        same_pixels=lambda a, b: pixels)
        with mock.patch.object(audit, 'ROOT', self.root), mock.patch.dict(sys.modules, {'cover_render_check': checker}):
            return audit.render_one(('images/test.jpg', self.entry))

    def test_identisch_nur_bei_gleichem_hash(self):
        r = self.run_render(b'original')
        self.assertEqual(r['status'], 'byte_identisch')
        self.assertEqual(r['sha256'], r['vergleich_sha256'])
        self.assertEqual(self.image.read_bytes(), b'original')

    def test_pixel_und_abweichung_werden_getrennt(self):
        self.assertEqual(self.run_render(b'anders', pixels=True)['status'], 'pixel_identisch')
        self.assertEqual(self.run_render(b'anders')['status'], 'abweichend')

    def test_fehlender_manifest_eintrag_bleibt_unbekannt(self):
        with mock.patch.object(audit, 'ROOT', self.root):
            r = audit.render_one(('images/test.jpg', {}))
            self.assertEqual(r['status'], 'unbekannt')
            self.assertIn('sha256', r)
            self.assertEqual(audit.render_one(('../../etc/passwd', {}) )['status'], 'fehler')


if __name__ == '__main__':
    unittest.main()
