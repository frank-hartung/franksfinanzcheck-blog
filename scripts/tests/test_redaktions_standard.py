#!/usr/bin/env python3
"""Regressionstests für den REDAKTIONS-STANDARD-Schreiber (Vorgang WF-54C4/#607).

Am 05.10.2026 schrieb die KI-Heilung (`--fix --ai`) einen Live-Artikel von
Flesch 68,7 auf 44,3 und fügte „In diesem Beitrag erfährst du …“ ein. Ihre
Struktur-Prüfung (`_verify`: Links, H2-Anzahl, Länge, Trennlinien) fand
nichts – blockiert hat den Artikel erst der nächste Deploy-Lauf (Exit 1,
Produktionsalarm WF-54C4). Diese Tests frieren die fehlende Stufe ein:

  1) Der Publikations-Vertrag sitzt VOR dem Schreiben: Eine KI-Änderung, die
     die Publish-Schwelle reißt (V1) oder eine harte Verständnis-Regel neu
     einführt (V2), wird verworfen – `heal_article_ai` liefert None.
  2) Fail-closed: Ist der Vertrag nicht verfügbar, wird ebenfalls nichts
     geschrieben (V3) – „nicht gemessen“ ist kein Freispruch.
  3) Die Schwelle ist importiert, nicht kopiert: Wer `NEW_FLESCH_MIN` in
     `readability_check` anhebt, hebt auch das Urteil des Schreibers.
  4) Die gute Heilung bleibt möglich (kein Totstell-Test).

Alles läuft offline in temporären Verzeichnissen; die echten Artikel werden
nicht angefasst.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import readability_check  # noqa: E402
import redaktions_standard as rs  # noqa: E402


FM = ('title: "Stromkosten senken: so gehst du vor"\n'
      'description: "Stromkosten senken: prüfe Verträge und vergleiche Tarife."\n'
      'date: "2026-10-07T06:00:00Z"\n'
      'author: "Frank Hartung"\n')

# Nur RS1 fehlt (keine „Das Wichtigste in Kürze“-Box). RS2/RS3/RS4/RS7 sind
# erfüllt, damit der Test genau die neue Vertragsstufe misst.
BODY_SOLL = (
    "Der Strompreis steigt und viele Haushalte spüren es. Wer den eigenen "
    "Tarif prüft, findet oft eine bessere Option.\n"
    "Der Wechsel ist unkompliziert und lohnt sich meist schon im ersten "
    "Jahr. Vorher hilft ein Blick auf den eigenen Verbrauch.\n\n"
    "## Warum lohnt sich der Wechsel?\n"
    "Ein Vergleich zeigt dir schnell den passenden Tarif. Schon kleine "
    "Unterschiede summieren sich über die Monate.\n"
    "**Faustregel:** Wer jedes Jahr vergleicht, spart meist mehr als beim "
    "ersten Wechsel.\n\n"
    "## Was kostet der Wechsel?\n"
    "Der Wechsel selbst kostet nichts. Der neue Anbieter übernimmt die "
    "Kündigung für dich. So gehst du vor:\n\n"
    "1. Prüfe den eigenen Verbrauch.\n"
    "2. Vergleiche mehrere Tarife.\n"
    "3. Schließe den Wechsel ab.\n")

BOX_OK = (
    "**Das Wichtigste in Kürze**\n\n"
    "- Ein Vergleich der Stromtarife lohnt sich fast immer.\n"
    "- Der Wechsel selbst kostet dich nichts.\n"
    "- Neue Anbieter übernehmen meist die Kündigung.\n\n")

# Gute KI-Antwort: schließt RS1, hält H2-Anzahl und Länge, bleibt leicht.
ANTWORT_OK = BOX_OK + BODY_SOLL

# V1-Sabotage: Box ergänzt, aber lange Schachtelsätze drücken unter Flesch 60.
SCHWER = ("Die vorgenommene Umstrukturierung der Tariflandschaft, die sich "
          "insbesondere durch die Anpassung der Netzentgelte sowie der "
          "CO₂-Bepreisung im Kontext der fortschreitenden Dekarbonisierung "
          "der Energieversorgungssysteme ergibt, erfordert eine grundlegende "
          "Neubewertung der individuellen Vertragskonstellationen, wobei die "
          "Berücksichtigung der jeweiligen Verbrauchsprofile unabdingbar "
          "erscheint.")
ANTWORT_SCHWER = BOX_OK + SCHWER + "\n\n" + BODY_SOLL

# V2-Sabotage: Box ergänzt, aber die gesperrte Intro-Formel neu eingeführt.
ANTWORT_INTRO = BOX_OK + BODY_SOLL.replace(
    "Der Strompreis steigt und viele Haushalte spüren es.",
    "In diesem Beitrag erfährst du alles Wichtige.")


def _artikel(tmpdir):
    pfad = os.path.join(tmpdir, "index.md")
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("---\n" + FM + "---\n" + BODY_SOLL)
    a = rs.load_article(pfad)
    assert a, "Testartikel muss ladbar sein"
    return pfad, a


class VertragImSchreiberTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad, self.a = _artikel(self.tmp.name)
        self.res = rs.analyse_article(self.a)
        # Nur RS1 offen – die Heilung hat genau einen Auftrag.
        self.assertEqual(["RS1"], self.res["hart_missing"])
        env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
        env.start()
        self.addCleanup(env.stop)

    def _heile(self, antwort):
        verworfen = []
        with mock.patch.object(rs, "_call_ai", return_value=antwort):
            neu = rs.heal_article_ai(self.a, self.res, verworfen)
        return neu, verworfen

    def test_gute_heilung_wird_uebernommen(self):
        neu, verworfen = self._heile(ANTWORT_OK)
        self.assertIsNotNone(neu, f"gute KI-Antwort wurde verworfen: {verworfen}")
        self.assertIn("Das Wichtigste in Kürze", neu)
        res2 = rs.analyse_article(dict(self.a, body=neu))
        self.assertEqual([], res2["hart_missing"])
        self.assertEqual([], verworfen)

    def test_flesch_absturz_wird_verworfen(self):
        neu, verworfen = self._heile(ANTWORT_SCHWER)
        self.assertIsNone(neu, "KI-Änderung unter Flesch 60 wurde geschrieben (#607)")
        self.assertTrue(verworfen, "Ablehnung wurde nicht protokolliert")
        self.assertTrue(any("V1" in str(v.get("grund", "")) for v in verworfen),
                        f"V1-Grund fehlt: {verworfen}")

    def test_neue_intro_formel_wird_verworfen(self):
        neu, verworfen = self._heile(ANTWORT_INTRO)
        self.assertIsNone(neu, "neue R7-Formel wurde geschrieben (#607)")
        self.assertTrue(any("R7-INTRO-FORMEL" in str(v.get("grund", ""))
                            for v in verworfen), f"V2-Grund fehlt: {verworfen}")

    def test_fail_closed_ohne_vertrag(self):
        verworfen = []
        with mock.patch.object(rs, "_vertrag_pruefe", None), \
                mock.patch.object(rs, "_VERTRAG_FEHLER", "Importfehler (Test)"), \
                mock.patch.object(rs, "_call_ai", return_value=ANTWORT_OK):
            neu = rs.heal_article_ai(self.a, self.res, verworfen)
        self.assertIsNone(neu, "ohne prüfbaren Vertrag darf nichts geschrieben werden")
        self.assertTrue(any("V3" in str(v.get("grund", "")) for v in verworfen),
                        f"V3-Grund fehlt: {verworfen}")

    def test_schwelle_ist_importiert(self):
        # Hebt die SSOT die Schwelle an, muss dieselbe (importierte) Zahl hier
        # greifen – eine Kopie im Schreiber würde das nicht mitmachen (#585).
        with mock.patch.object(readability_check, "NEW_FLESCH_MIN", 99.0):
            gruende = rs._vertrag_gruende(self.a, ANTWORT_OK)
        self.assertTrue(any(g.startswith("V1") for g in gruende),
                        f"angehobene SSOT-Schwelle greift nicht: {gruende}")

    def test_datei_bleibt_bei_ablehnung_unberuehrt(self):
        vorher = open(self.pfad, encoding="utf-8").read()
        neu, _ = self._heile(ANTWORT_INTRO)
        self.assertIsNone(neu)
        nachher = open(self.pfad, encoding="utf-8").read()
        self.assertEqual(vorher, nachher)


class VorfallsmaterialTest(unittest.TestCase):
    """Der echte WF-54C4-Text bleibt als Beweis eingefroren (kein Nachbau)."""

    def test_fixtures_existieren(self):
        sim = os.path.join(BLOG_DIR, "scripts", "tests", "sim", "wf54c4")
        for name in ("vorher.md", "nachher.md"):
            pfad = os.path.join(sim, name)
            self.assertTrue(os.path.exists(pfad), f"Vorfall-Material fehlt: {pfad}")
            self.assertGreater(os.path.getsize(pfad), 5000, pfad)

    def test_echter_vorfall_wird_erkannt(self):
        import publikations_vertrag as pv
        sim = os.path.join(BLOG_DIR, "scripts", "tests", "sim", "wf54c4")
        with open(os.path.join(sim, "vorher.md"), encoding="utf-8") as fh:
            vorher = fh.read()
        with open(os.path.join(sim, "nachher.md"), encoding="utf-8") as fh:
            nachher = fh.read()
        gruende = pv.pruefe("2026-09-10-energie-update", vorher, nachher)
        self.assertTrue(any(g.startswith("V1") for g in gruende),
                        f"Flesch-Absturz des realen Vorfalls fehlt: {gruende}")
        self.assertTrue(any("R7-INTRO-FORMEL" in g for g in gruende),
                        f"R7-Fund des realen Vorfalls fehlt: {gruende}")


if __name__ == "__main__":
    unittest.main()
