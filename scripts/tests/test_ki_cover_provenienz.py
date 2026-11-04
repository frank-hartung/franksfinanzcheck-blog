import datetime as dt
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts import ki_cover_provenienz as gate


class CoverProvenienzTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / 'static/images/test.jpg'
        self.image.parent.mkdir(parents=True)
        self.image.write_bytes(b'original')
        self.post = self.root / 'content/posts/x/index.md'
        self.post.parent.mkdir(parents=True)
        self.sha = hashlib.sha256(self.image.read_bytes()).hexdigest()

    def put(self, body):
        self.post.write_text('---\ntitle: Test\n' + body + '\n---\nText\n', encoding='utf-8')

    def valid(self, **kw):
        sha = kw.get('sha', self.sha)
        deepfake = kw.get('deepfake', 'false')
        self.put(f'cover:\n  image: /images/test.jpg\n  ai_generated: true\n  ki_pruefung:\n    sha256: {sha}\n    quelle: "Generator-Auftrag 17"\n    geprueft_am: 2026-01-01\n    deepfake: {deepfake}')

    def test_unknown_is_not_invented(self):
        self.put('cover:\n  image: /images/test.jpg')
        rows, errors = gate.audit(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]['herkunft'], 'nicht_belegt')
        self.assertFalse(gate.protected_paths(self.root))

    def test_valid_and_changed_original(self):
        self.valid()
        self.assertEqual(gate.audit(self.root)[1], [])
        self.assertEqual(gate.protected_paths(self.root), {self.image.resolve()})
        self.image.write_bytes(b'changed')
        self.assertIn('sha256', gate.audit(self.root)[1][0])

    def test_unverified_or_deepfake_fails(self):
        self.put('cover:\n  image: /images/test.jpg\n  ai_generated: true')
        self.assertIn('ki_pruefung', gate.audit(self.root)[1][0])
        self.valid(deepfake='true')
        self.assertIn('Deepfake nicht freigegeben', gate.audit(self.root)[1][0])
        self.valid(deepfake='"false"')
        self.assertIn('Deepfake-Einzelfallprüfung', gate.audit(self.root)[1][0])

    def test_bad_flag_and_unsafe_path(self):
        self.put('cover:\n  image: /images/test.jpg\n  ai_generated: "true"')
        self.assertIn('muss true oder false', gate.audit(self.root)[1][0])
        self.put('cover:\n  image: /../../secret.jpg\n  ai_generated: true')
        self.assertIn('außerhalb', gate.audit(self.root)[1][0])

    def test_toml_and_json_frontmatter_are_not_skipped(self):
        for text in (
            '+++\ntitle = "Test"\n[cover]\nimage = "/images/test.jpg"\nai_generated = true\n+++\n',
            '{"title":"Test", "cover":{"image":"/images/test.jpg", "ai_generated":true}}\n',
        ):
            self.post.write_text(text, encoding='utf-8')
            self.assertIn('ki_pruefung', gate.audit(self.root)[1][0])
            self.assertEqual(gate.protected_paths(self.root), {self.image.resolve()})

    def test_shared_original_must_be_declared_on_every_page(self):
        self.valid()
        other = self.root / 'content/posts/other/index.md'
        other.parent.mkdir(parents=True)
        other.write_text('---\ntitle: Other\ncover:\n  image: images/../images/test.jpg\n---\n', encoding='utf-8')
        errors = gate.audit(self.root)[1]
        self.assertEqual(len(errors), 1)
        self.assertIn('dieselbe Datei', errors[0])
        self.assertIn('other/index.md', errors[0])
        other.write_text(self.post.read_text(encoding='utf-8'), encoding='utf-8')
        self.assertEqual(gate.audit(self.root)[1], [])

    def test_unfinished_frontmatter_fails(self):
        self.post.write_text('---\ntitle: x\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            gate.audit(self.root)


if __name__ == '__main__':
    unittest.main()
