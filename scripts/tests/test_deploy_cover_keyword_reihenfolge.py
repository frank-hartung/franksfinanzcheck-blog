"""Regression Run 45374581619: Keyword-Titeländerung vor Cover-Herkunft."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SLUG = "2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich"


class DeployCoverKeywordTest(unittest.TestCase):
    def test_workflow_ordnen_und_wache_unveraendert_hart(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["deploy"]["steps"]
        calls = [s.get("run", "") for s in steps]

        def position(text):
            matches = [i for i, run in enumerate(calls) if text in run]
            self.assertEqual(len(matches), 1, text)
            return matches[0]

        self.assertLess(position("scripts/check_titles.py --fix"), position("scripts/keyword_optimizer.py --fix"))
        self.assertLess(position("scripts/keyword_optimizer.py --fix"), position("scripts/check_covers.py --fix"))
        self.assertLess(position("scripts/keyword_gate.py --fix"), position("scripts/check_covers.py --fix"))
        self.assertLess(position("scripts/check_covers.py --fix"), position("scripts/ki_cover_herkunft.py --heilen"))
        guard = steps[position("scripts/ki_cover_herkunft.py --pruefen")]
        self.assertEqual(guard["run"].strip(), "python3 scripts/ki_cover_herkunft.py --pruefen")
        self.assertNotIn("continue-on-error", guard)
        self.assertNotIn("if", guard)
        self.assertLess(position("scripts/ki_cover_herkunft.py --heilen"), position("scripts/ki_cover_herkunft.py --pruefen"))

    def test_alter_vorfall_und_neue_reihenfolge_in_wegwerf_repo(self):
        with tempfile.TemporaryDirectory(prefix="cover-keyword-regression-") as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (root / "static/fonts").mkdir(parents=True)
            shutil.copy2(ROOT / "static/fonts/Inter-Bold.ttf", root / "static/fonts/Inter-Bold.ttf")
            post = root / "content/posts" / SLUG / "index.md"
            post.parent.mkdir(parents=True)
            original = (ROOT / "content/posts" / SLUG / "index.md").read_text(encoding="utf-8")
            # Das alte irrelevante Haupt-Keyword provoziert den CI-Schaden.
            fixed = 'keywords: ["WLAN-Verstärker vs. Mesh-WLAN", "DSL Hacks",'
            old = 'keywords: ["DSL Hacks", "WLAN-Verstärker vs. Mesh-WLAN",'
            self.assertIn(fixed, original)
            post.write_text(original.replace(fixed, old, 1), encoding="utf-8")
            covers = ROOT / "static/images/covers"
            for source in covers.rglob(SLUG + ".*"):
                if source.is_file():
                    target = root / "static/images/covers" / source.relative_to(covers)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            manifest = json.loads((ROOT / "data/covers_manifest.json").read_text(encoding="utf-8"))
            (root / "data").mkdir()
            (root / "data/covers_manifest.json").write_text(json.dumps({SLUG: manifest[SLUG]}), encoding="utf-8")

            def run(script, arg, expected=0):
                result = subprocess.run([sys.executable, str(root / "scripts" / script), arg],
                                        cwd=root, text=True, capture_output=True, timeout=120)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                return result.stdout + result.stderr

            run("ki_cover_herkunft.py", "--heilen")
            run("ki_cover_herkunft.py", "--pruefen")
            run("keyword_optimizer.py", "--fix")
            self.assertIn('title: "DSL Hacks:', post.read_text(encoding="utf-8"))
            before = run("ki_cover_herkunft.py", "--pruefen", expected=1)
            self.assertIn("Bild weicht vom Renderer ab", before)
            run("ki_cover_herkunft.py", "--heilen")
            self.assertIn("Bild weicht vom Renderer ab", run("ki_cover_herkunft.py", "--pruefen", expected=1))
            run("check_covers.py", "--fix")
            run("ki_cover_herkunft.py", "--heilen")
            run("ki_cover_herkunft.py", "--pruefen")

    def test_korrigierter_artikel_ist_keyword_fixpunkt(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import keyword_optimizer
        with tempfile.TemporaryDirectory(prefix="cover-keyword-fixed-") as tmp:
            post = Path(tmp) / SLUG / "index.md"
            post.parent.mkdir()
            shutil.copy2(ROOT / "content/posts" / SLUG / "index.md", post)
            before = post.read_bytes()
            changed, actions = keyword_optimizer.heal_article_file(str(post))
            self.assertFalse(changed, actions)
            self.assertEqual(post.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
