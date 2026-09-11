"""Regressionstests: Rechtschreib-Score darf Wörterbuch-Lücken nicht bestrafen.

Issue #251 (11.09.2026): `quality_score` wertete JEDEN Spellcheck-Befund
(außer entity/nbsp) als Rechtschreibfehler – auch „unknown“ (gültige deutsche
Komposita/Fachbegriffe, die hunspell de_DE nicht kennt). 10 solcher Lücken
drückten den Rechtschreib-Score auf 0.00 → Gesamt-Score < 0.80 → Massen-Parking
→ Tagesdefizit → Content-Engine rot → Bot-Watchdog #251.

Verträge des Fixes:
  1) „unknown“-Befunde zählen nur schwach (je −0.02), nie hart (−0.1).
  2) Echte Fehler (typo/phrase/noun_case) zählen weiterhin hart.
  3) Stil-Befunde (Satzanfang, Zeichensetzung, Anrede, „zuhause“) gehören
     nicht zur Rechtschreibung und fließen gar nicht ein.

Ausführung wie Bestands-Tests: python3 -m unittest discover -s scripts/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import quality_score as qs


class SpellingScoreTests(unittest.TestCase):
    def test_dictionary_gaps_are_soft_not_hard(self):
        # 10 Wörterbuch-Lücken: vor #251 = 0.0, jetzt 0.8 (nie Nullpunkt).
        self.assertEqual(
            qs._spelling_score([{"type": "unknown"}] * 10), 0.8)

    def test_genuine_errors_still_hard(self):
        self.assertEqual(qs._spelling_score([{"type": "typo"}] * 3), 0.7)
        self.assertEqual(qs._spelling_score([{"type": "phrase"}] * 2), 0.8)
        self.assertEqual(qs._spelling_score([{"type": "noun_case"}] * 1), 0.9)

    def test_mixed_weighting(self):
        score = qs._spelling_score(
            [{"type": "typo"}] * 3 + [{"type": "unknown"}] * 10)
        self.assertAlmostEqual(score, 0.5)

    def test_style_findings_do_not_count(self):
        style = [{"type": t} for t in (
            "zuhause", "heading_start", "satzanfang", "punctuation",
            "comma_cap", "anrede", "desc_punkt")]
        self.assertEqual(qs._spelling_score(style), 1.0)

    def test_floor_zero(self):
        self.assertEqual(qs._spelling_score([{"type": "typo"}] * 30), 0.0)


if __name__ == "__main__":
    unittest.main()
