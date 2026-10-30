#!/usr/bin/env python3
"""Meta-Regel des Publish-Scores (scripts/quality_score.py) gegen die SSOT.

WF-7B6B / #925 (29.10.2026): Der Publish-Score erlaubte Descriptions bis
160 Zeichen – die letzte eigene Zahl im Haus. Das Snippet-Gate kürzt bei
155 Zeichen UND 985 px: Ein Score, der 159 Zeichen grün nennt, publiziert
einen Kandidaten, den das eigene Nacht-Gate rot macht. Seitdem liest die
Regel die SSOT. Die Untergrenze (100 Zeichen) gehört NICHT diesem Score –
sie ist Meldebestand der Metadaten-Wache.

Aufruf: python3 -m unittest scripts.tests.test_quality_score_meta
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import quality_score as qs  # noqa: E402
import serp_limits as sl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def meta_score(title, desc, kurzantwort="da"):
    """Die Meta-Teilnote isoliert betrachten – so wie quality_score sie rechnet."""
    m = {"title": title, "description": desc, "kurzantwort": kurzantwort}
    score = 1.0
    if not m.get("title") or len(m["title"]) > 60:
        score -= 0.3
    if (not desc or not sl.passt(desc, min_zeichen=0)
            or desc[-1] not in ".!?…"):
        score -= 0.3
    if not m.get("kurzantwort"):
        score -= 0.15
    return max(0.0, score)


class SsotBindung(unittest.TestCase):
    def test_score_liest_die_ssot(self):
        self.assertIs(qs.serp_limits, sl)

    def test_keine_eigene_zahl_im_code(self):
        with open(os.path.join(REPO, "scripts", "quality_score.py"),
                  encoding="utf-8") as fh:
            quelle = fh.read()
        self.assertIn("import serp_limits", quelle)
        self.assertNotIn("len(desc) > 160", quelle)


class MetaRegel(unittest.TestCase):
    def test_155_schmale_zeichen_sind_gruen(self):
        self.assertEqual(meta_score("Titel ok", "i" * 154 + "."), 1.0)

    def test_160_zeichen_kosten(self):
        self.assertEqual(meta_score("Titel ok", "i" * 159 + "."), 0.7)

    def test_925_breite_kostet(self):
        vorfall = ("DSL Hacks: WLAN-Verstärker oder Mesh-WLAN? So findest du "
                   "2026 heraus, was dein Zuhause wirklich braucht – mit "
                   "klaren Kosten und einer Entscheidungshilfe.")
        self.assertEqual(meta_score("Titel ok", vorfall), 0.7)

    def test_untergrenze_ist_nicht_dieses_scores_sache(self):
        # 90 schmale Zeichen: für das Snippet zu kurz, aber der Publish-Score
        # bewertet das nicht – das ist Meldebestand der Metadaten-Wache.
        self.assertEqual(meta_score("Titel ok", "i" * 89 + "."), 1.0)


if __name__ == "__main__":
    unittest.main()
