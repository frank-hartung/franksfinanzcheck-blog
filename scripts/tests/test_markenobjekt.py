"""Vertragstests für die kanonischen FranksFinanzcheck-Markenobjekte."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MarkenobjektVertrag(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_kostenprofil_ist_auf_startseite_und_artikel(self):
        home = self.read("layouts/_partials/home_info.html")
        article = self.read("layouts/single.html")
        self.assertIn('partial "kostenprofil.html"', home)
        self.assertIn('"mode" "home"', home)
        self.assertIn('partial "kostenprofil.html"', article)
        self.assertIn('"mode" "article"', article)

    def test_kostenprofil_hat_vier_kanonische_achsen_und_keinen_score(self):
        profile = self.read("layouts/_partials/kostenprofil.html")
        for label in ("Kosten", "Konditionen", "Frist", "Kurs"):
            self.assertIn(f"<strong>{label}</strong>", profile)
        self.assertEqual(4, len(re.findall(r"<li>", profile)))
        self.assertNotRegex(profile.lower(), r"\bscore\b|\bprozent\b|%")

    def test_echtes_autorenbild_ist_dimensioniert_und_verlinkt(self):
        profile = self.read("layouts/_partials/kostenprofil.html")
        self.assertIn('images/frank-hartung.jpg', profile)
        self.assertIn('width="800" height="800"', profile)
        self.assertIn('"ueber/" | relURL', profile)
        self.assertTrue((ROOT / "static/images/frank-hartung.jpg").is_file())

    def test_datenblatt_kennzeichnung_ist_im_chart_renderer(self):
        chart = self.read("layouts/shortcodes/chart.html")
        self.assertIn("FF—DATENBLATT", chart)
        self.assertIn("data-ff-chart", chart)
        self.assertIn("ff-chart__table", chart)

    def test_basis_ist_die_einzige_aktive_produktionswahrheit(self):
        config = self.read("hugo.toml")
        register = self.read("data/design/varianten.yaml")
        self.assertRegex(config, r'(?m)^\s*designVariante\s*=\s*""\s*$')
        self.assertRegex(register, r'(?m)^aktiv:\s*""\s*$')
        self.assertEqual(1, len(re.findall(r"(?m)^\s+status:\s+live\s*$", register)))


if __name__ == "__main__":
    unittest.main()
