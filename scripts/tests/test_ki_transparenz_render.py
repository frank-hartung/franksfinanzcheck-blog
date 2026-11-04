"""Render-Vertrag: Text- und Bildherkunft nicht vermischen (Issue #1028)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HUGO = os.environ.get("HUGO_BIN", "hugo")


@unittest.skipUnless(shutil.which(HUGO), "Hugo nicht installiert")
class KiTransparenzRenderTest(unittest.TestCase):
    def test_herkunft_und_ansichten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def write(path, content):
                f = root / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content, encoding="utf-8")

            write("hugo.toml", 'baseURL = "https://example.org/"\ntitle = "Test"\n')
            for partial in ("cover.html", "ff_pruefzeile.html", "article_dates.html"):
                write("layouts/_partials/" + partial, (ROOT / "layouts/_partials" / partial).read_text(encoding="utf-8"))
            write("layouts/_partials/asset_url.html", '{{ return . }}')
            write("layouts/_default/baseof.html", '<!doctype html><html><body>{{ block "main" . }}{{ end }}</body></html>')
            write("layouts/_default/single.html", '{{ define "main" }}{{ partial "ff_pruefzeile.html" . }}{{ partial "cover.html" (dict "cxt" . "IsSingle" true "isHidden" false) }}{{ end }}')
            write("layouts/_default/list.html", '{{ define "main" }}{{ range .Pages }}{{ partial "cover.html" (dict "cxt" . "IsSingle" false "isHidden" false) }}{{ end }}{{ end }}')
            write("content/posts/_index.md", '---\ntitle: Posts\n---\n')
            write("static/avif/360/test.avif", "variant")
            samples = {
                "ai": 'ai_generated: true\ncover:\n  image: /test.jpg\n  caption: Testbild\n',
                "review": 'ai_generated: true\nredaktionelle_pruefung:\n  status: freigegeben\n  pruefer:\n    name: Test\n  pruefdatum: 2026-01-01\n  naechste_pruefung: 2026-12-01\ncover:\n  image: /test.jpg\n  ai_generated: true\n  caption: Testbild\n',
                "image": 'ai_generated: false\ncover:\n  image: /test.jpg\n  ai_generated: true\n',
                "unknown": 'ai_generated: false\ncover:\n  image: /test.jpg\n',
                "false": 'ai_generated: false\ncover:\n  image: /test.jpg\n  ai_generated: false\n',
            }
            for slug, fm in samples.items():
                write(f"content/posts/{slug}/index.md", f'---\ntitle: {slug}\ndate: 2026-01-01\n{fm}---\nText\n')
            subprocess.run([HUGO, "--minify"], cwd=root, check=True, capture_output=True, text=True)
            def html(slug):
                return (root / "public/posts" / slug / "index.html").read_text(encoding="utf-8")
            for slug in ("ai", "review"):
                self.assertEqual(html(slug).count('data-ff-ki-label'), 1)
                self.assertIn('Mit KI erstellt oder bearbeitet', html(slug))
            for slug in ("image", "unknown", "false"):
                self.assertNotIn('data-ff-ki-label', html(slug))
            for slug in ("review", "image"):
                self.assertIn('data-ff-ki-image-label', html(slug))
            for slug in ("ai", "unknown", "false"):
                self.assertNotIn('data-ff-ki-image-label', html(slug))
            self.assertIn('Testbild', html("review"))
            self.assertNotIn('<source', html("review"))
            self.assertNotIn('srcset=', html("review"))
            self.assertIn('srcset=', html("ai"))
            self.assertEqual((root / 'public/posts/index.html').read_text(encoding='utf-8').count('data-ff-ki-image-label'), 2)


if __name__ == "__main__":
    unittest.main()
