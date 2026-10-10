"""Regressionen für die gepinnte, CDN-unabhängige Chromium-Versorgung."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ChromiumSetupContractTests(unittest.TestCase):
    def test_bundle_ist_exakt_im_manifest_und_lockfile_gepinnt(self):
        manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
        version = manifest["devDependencies"].get("@sparticuz/chromium")

        self.assertRegex(version or "", r"^\d+\.\d+\.\d+$")
        self.assertEqual(lock["packages"][""]["devDependencies"]["@sparticuz/chromium"], version)
        browser = lock["packages"]["node_modules/@sparticuz/chromium"]
        self.assertEqual(browser["version"], version)
        self.assertTrue(browser["resolved"].startswith("https://registry.npmjs.org/"))
        self.assertRegex(browser.get("integrity", ""), r"^sha512-")
        self.assertEqual(manifest["scripts"]["browser:setup"], "node scripts/browser_setup.mjs")

        nested = json.loads((ROOT / "tools/ff-voice-browser/package.json").read_text(encoding="utf-8"))
        nested_lock = json.loads((ROOT / "tools/ff-voice-browser/package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(nested["devDependencies"]["@sparticuz/chromium"], version)
        self.assertEqual(nested_lock["packages"]["node_modules/@sparticuz/chromium"]["version"], version)

    def test_setup_beweist_browserstart_und_javascript_rendering(self):
        source = (ROOT / "scripts" / "browser_setup.mjs").read_text(encoding="utf-8")
        for needle in (
            "resolveLaunchOptions",
            "chromium.launch",
            "document.querySelector('#render-proof').textContent",
            "JavaScript-Smoke-Test",
        ):
            self.assertIn(needle, source)
        self.assertNotIn("npx playwright install chromium", source.lower())

    def test_browser_resolver_hat_gepinnten_fallback_und_explizite_pfade(self):
        source = (ROOT / "e2e" / "browser.mjs").read_text(encoding="utf-8")
        for needle in (
            "FF_BROWSER_PATH",
            "CHROME_PATH",
            "pwChromium.executablePath()",
            "import('@sparticuz/chromium')",
            "withChromiumExtractionLock",
            "process.platform !== 'linux'",
            "mod.inflate",
        ):
            self.assertIn(needle, source)

    def test_alle_bundle_einstiegspunkte_verhindern_veraltete_oder_kollidierende_extraktion(self):
        cache = (ROOT / "scripts" / "chromium_cache.mjs").read_text(encoding="utf-8")
        for needle in ("franksfinanzcheck-chromium", "process.env.TMPDIR", "openSync(lockPath, 'wx', 0o600)", "process.kill(info.pid, 0)"):
            self.assertIn(needle, cache)
        for relative in (
            "scripts/ff_voice_browser_test.mjs",
            "scripts/themenwelten_browser_test.mjs",
        ):
            with self.subTest(script=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("prepareChromiumTemp", source)
                self.assertIn("withChromiumExtractionLock", source)

    def test_ci_prueft_browser_ohne_playwright_cdn_download(self):
        workflows = {
            ".github/workflows/e2e.yml": "npm run browser:setup",
            ".github/workflows/design-varianten.yml": "npm run browser:setup",
            ".github/workflows/werkbank.yml": "npm run browser:setup",
        }
        for relative, required in workflows.items():
            with self.subTest(workflow=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn(required, source)
                self.assertNotIn("npx playwright install", source)

        voice = (ROOT / ".github/workflows/lesehilfen-gate.yml").read_text(encoding="utf-8")
        self.assertIn("@sparticuz/chromium", voice)
        self.assertNotIn("playwright-core install", voice)

        themes = (ROOT / ".github/workflows/themenwelten-gate.yml").read_text(encoding="utf-8")
        self.assertIn("npm ci --prefix tools/ff-voice-browser", themes)
        self.assertNotIn("playwright-core install", themes)


if __name__ == "__main__":
    unittest.main()
