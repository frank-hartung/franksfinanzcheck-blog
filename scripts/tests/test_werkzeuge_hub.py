#!/usr/bin/env python3
"""Regression: Werkzeug-Übersicht bleibt eine Seite und sagt die richtige Zahl.

Hintergrund (19.10.2026): Mit dem neunten Werkzeug (Balkonkraftwerk) bei
`pagerSize = 8` erzeugte Hugo `/werkzeuge/page/2/`. Das ist eine Dublette der
Übersicht, die als indexierbar galt, aber nicht in der Sitemap stand (H1 der
Index-Hygiene, harter Fund, Deploy rot).

Behebung: `layouts/_partials/seo_context.html` behandelt Blätterseiten jeder
Sektion als Pager (noindex, nicht in der Sitemap). `hugo.toml` bleibt unverändert,
weil es im Integritäts-Siegel als kritisch geführt wird.

Dieser Test schützt davor, dass die Lücke still wieder entsteht:
  1. seo_context kennt die Sektions-Regel (Quelle).
  2. Die ausgeschriebene Zahl im Hub-Text stimmt mit der Anzahl überein.
  3. Der gebaute Stand wird zusätzlich durch H1 in index_hygiene_gate.py geprüft.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

ZAHLWORT = {
    6: "Sechs", 7: "Sieben", 8: "Acht", 9: "Neun",
    10: "Zehn", 11: "Elf", 12: "Zwölf",
}
ZIFFER_TITEL = re.compile(r"\b(\d+) kostenlose Finanz-Rechner\b")


def _werkzeuge() -> list[dict]:
    daten = yaml.safe_load((ROOT / "data" / "werkzeuge.yaml").read_text(encoding="utf-8"))
    return daten["werkzeuge"]


class WerkzeugeHubTestCase(unittest.TestCase):
    def test_seo_context_regelt_blaetterseiten_jeder_sektion(self) -> None:
        text = (ROOT / "layouts" / "_partials" / "seo_context.html").read_text(encoding="utf-8")
        self.assertIn('{{- else if eq .Kind "section" -}}', text,
                      "seo_context: Sektions-Regel für Blätterseiten fehlt")
        self.assertIn(".Paginator", text,
                      "seo_context: Blätterseiten der Sektion werden nicht erkannt")

    def test_hub_kicker_nennt_richtige_zahl(self) -> None:
        anzahl = len(_werkzeuge())
        daten = yaml.safe_load((ROOT / "data" / "werkzeuge.yaml").read_text(encoding="utf-8"))
        wort = ZAHLWORT.get(anzahl)
        self.assertIsNotNone(wort, f"Zahlwort für {anzahl} fehlt in ZAHLWORT")
        self.assertTrue(
            daten["hub_kicker"].startswith(wort + " "),
            f"hub_kicker {daten['hub_kicker']!r} passt nicht zu {anzahl} Werkzeugen",
        )
        self.assertTrue(
            daten["positionierung"].startswith(wort + " "),
            f"positionierung beginnt nicht mit „{wort}“ ({anzahl} Werkzeuge)",
        )

    def test_seo_titel_nennt_richtige_zahl(self) -> None:
        anzahl = len(_werkzeuge())
        text = (ROOT / "content" / "werkzeuge" / "_index.md").read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        titel = frontmatter.get("seoTitle", "")
        m = ZIFFER_TITEL.search(titel)
        self.assertIsNotNone(m, "seoTitle muss die Zahl und kostenlose Finanz-Rechner nennen")
        self.assertEqual(int(m.group(1)), anzahl, "seoTitle nennt eine andere Anzahl")
        self.assertLessEqual(len(titel), 65, "Meta-Titel darf nicht wieder zu lang werden")

    def test_e2e_spec_prueft_richtige_werkzeug_anzahl(self) -> None:
        anzahl = len(_werkzeuge())
        spec = (ROOT / "e2e" / "werkzeuge.spec.mjs").read_text(encoding="utf-8")
        self.assertIn(f".toHaveCount({anzahl})", spec)
        self.assertIn(f"expect(new Set(ziele).size, 'jede Karte führt woanders hin').toBe({anzahl})", spec)


if __name__ == "__main__":
    unittest.main()
