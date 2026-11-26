#!/usr/bin/env python3
"""Dauerschutz #1230: Fazit-Schmiede erzeugt niemals RS5-Blocker oder Denglisch.

Warum dieser Test existiert:
  Vor der Bereinigung erzeugte `scripts/fazit_schmiede.py` auf 19/19 Fazit-Routen
  („fünf Minuten reichen.“, bei `handytarife` zusätzlich „auf zwei Jahre gerechnet“)
  und auf 12/17 FAQ-Routen unbelegte Zahlenbehauptungen, die das strenge
  Reserve-Qualitäts-Gate (`redaktions_standard._reserve_numeric_claim_findings`)
  sofort blockierte → Reserve fiel auf 0/6 (#1230 → #1382/#1378/#1280).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fazit_schmiede as fs  # noqa: E402
import redaktions_standard as rs  # noqa: E402


class FazitSchmiedeRs5VertragTest(unittest.TestCase):
    """Alle Fazit- und FAQ-Bausteine müssen das strenge Reserve-RS5-Gate bestehen."""

    def test_alle_fazit_routen_sind_rs5_frei(self):
        routen = sorted(
            set(fs.FAQ_POOL.keys())
            | {"standard", "allgemein", "strom", "gas", "heizoel", "kreditkarte",
               "girokonto", "tagesgeld", "dsl", "handytarife", "kfz", "haftpflicht",
               "hausrat", "bu", "reise", "mietwagen", "urlaub", "haushalt", "sparen",
               "hunde"}
        )
        verstoesse = []
        for route in routen:
            txt = fs.generate_fazit_text("Strompreis 2026: Kosten ehrlich prüfen", route)
            hits = rs._reserve_numeric_claim_findings(txt)
            if hits:
                verstoesse.append(f"{route}: {hits}")
        self.assertEqual(verstoesse, [], "Fazit-Schmiede erzeugt RS5-Blocker:\n" + "\n".join(verstoesse))

    def test_alle_faq_pool_routen_sind_rs5_und_denglisch_frei(self):
        verstoesse = []
        for route, eintraege in sorted(fs.FAQ_POOL.items()):
            for idx, (frage, antwort) in enumerate(eintraege):
                if "What is" in frage or "What is" in antwort:
                    verstoesse.append(f"{route}#{idx}: Denglisch-Tippfehler in {frage!r}")
                hits = rs._reserve_numeric_claim_findings(f"### {frage}\n\n{antwort}")
                if hits:
                    verstoesse.append(f"{route}#{idx}: RS5 {hits}")
        self.assertEqual(verstoesse, [], "FAQ_POOL erzeugt RS5-/Sprachfehler:\n" + "\n".join(verstoesse))

    def test_selbsttest_gruen(self):
        self.assertEqual(fs.selftest(), [])


if __name__ == "__main__":
    unittest.main()
