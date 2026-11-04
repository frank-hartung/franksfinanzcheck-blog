"""Der Cover-Heiler darf ein deklariertes KI-Original nicht überschreiben."""
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_covers as covers
import ki_cover_provenienz as provenance


class GeneratorSchutzTest(unittest.TestCase):
    def test_force_schuetzt_auch_referenzen_anderer_seiten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'static/images/covers'
            out.mkdir(parents=True)
            original = out / 'beitrag.jpg'
            original.write_bytes(b'KI-original')
            post = root / 'content/posts/beitrag/index.md'
            post.parent.mkdir(parents=True)
            post.write_text('---\ntitle: Beitrag\n---\nText\n', encoding='utf-8')
            # Die Herkunft kann auch auf einer anderen Seite deklariert sein.
            fake_lcp = types.SimpleNamespace(build_manifest=lambda: {}, write_manifest=lambda _: None)
            fake_fcp = types.SimpleNamespace(build_manifest=lambda: {}, write_manifest=lambda _: None)
            with mock.patch.object(covers, 'OUT_DIR', str(out)), \
                 mock.patch.object(covers, 'list_post_paths', return_value=[str(post)]), \
                 mock.patch.object(covers, 'load_manifest', return_value={}), \
                 mock.patch.object(covers, 'make_cover') as make, \
                 mock.patch.object(covers, 'ensure_responsive_variants') as variants, \
                 mock.patch.object(provenance, 'protected_paths', return_value={original.resolve()}), \
                 mock.patch.dict(sys.modules, {'lcp_image_optimizer': fake_lcp, 'fcp_image_optimizer': fake_fcp}), \
                 mock.patch.object(sys, 'argv', ['generate_covers.py', '--force', '--slug', 'beitrag', '--posts-only']):
                covers.main()
            make.assert_not_called()
            variants.assert_not_called()
            self.assertEqual(original.read_bytes(), b'KI-original')


if __name__ == '__main__':
    unittest.main()
