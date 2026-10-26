"""Vertragstest für den Bild-Renderhook (CLS-Fix am gebauten Baum).

Anlass (26.10.2026, Governance-Befund „10 <img>-Elemente ohne width/height"):
Markdown-Bilder in Artikeln wurden ohne intrinsische Maße ausgeliefert. Der
Wächter `scripts/cwv_guard.py` misst das jetzt über ALLE Seiten. Dieser Test
hält die beiden Fallen fest, die beim Heilungsversuch sichtbar wurden:

  1. `%q` auf einer Ganzzahl formatiert in Go ein RUNE („width=̠") – die Maße
     müssen vorher zu Text werden.
  2. SVGs liefern kein `.Width`/`.Height` – der Zugriff muss durch
     `reflect.IsImageResourceWithMeta` abgesichert sein, sonst bricht der
     gesamte Hugo-Bau ab.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "layouts" / "_markup" / "render-image.html"


class BildRenderhookVertrag(unittest.TestCase):
    def setUp(self):
        self.text = HOOK.read_text(encoding="utf-8")

    def test_masse_werden_nur_bei_bildmetadaten_gelesen(self):
        self.assertIn("reflect.IsImageResourceWithMeta", self.text)
        # SVG-Pfad: Maße aus width/height oder viewBox, ohne den Build zu kippen.
        self.assertIn("viewBox", self.text)

    def test_integergroessen_werden_als_text_formatiert(self):
        self.assertIn('printf "%v" $v', self.text,
                      "%q auf einer Ganzzahl erzeugt in Go ein Rune – Maße wären kaputt")
        self.assertNotIn('printf " %s=%q" $k $v', self.text)

    def test_autorenmasse_bleiben_unangetastet(self):
        self.assertIn('not (isset $attributes "width")', self.text)
        self.assertIn('not (isset $attributes "height")', self.text)


if __name__ == "__main__":
    unittest.main()
