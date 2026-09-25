#!/usr/bin/env python3
"""Tests für die Claude-Stilpolitur (scripts/claude_stilpolitur.py).

Auftrag (Frank, 25.09.2026): „Nutze für jeden bestehenden und zukünftigen
Blogartikel nach der Offline-Optimierung zusätzlich automatisch täglich
Claude 3.5 Sonnet mit einem personalisierten Prompt für meinen eigenen
Schreibstil auf Premium-Level einer Profi-Agentur."

Diese Tests nageln die Verträge der Lane fest (alles offline, ohne API):

  1. Personalisierung: Der System-Prompt enthält Franks Stilprofil
     (data/schreibstil.yaml) UND die Marken-Stimme (brand_brain.yaml).
  2. Modell-Bindung: ausdrücklich Claude 3.5 Sonnet – nie der 4.5-Default.
  3. Fakten-Schutz: Zahlen/Links/Überschriften byte-identisch, sonst
     wird die KI-Antwort verworfen (nie geschrieben).
  4. Rotation: Fingerprint-Dedupe (neu · geändert · auffrischen).

Läuft deterministisch ohne Netz (`python3 -m unittest discover -s scripts/tests`).
"""
from __future__ import annotations

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import claude_stilpolitur as cs  # noqa: E402


class TestSelbsttest(unittest.TestCase):
    def test_selbsttest_gruen(self):
        """Der eingefrorene Selbsttest muss grün sein (Sabotage-Schutz)."""
        self.assertEqual(cs.run_selftest(), [])


class TestPersonalisierung(unittest.TestCase):
    def test_prompt_traegt_franks_stil_und_marke(self):
        stil, brand = cs.load_stil()
        p = cs.render_system_prompt(stil, brand)
        self.assertIn("PREMIUM-LEVEL EINER PROFI-AGENTUR", p)
        self.assertIn("PERSÖNLICHEN SCHREIBSTIL", p)
        self.assertIn("Frank Hartung", p)
        self.assertIn("ehrlich, praxisnah, auf Augenhöhe", p)
        # Verbotsphrasen aus beiden Quellen landen im Tabu-Block
        self.assertIn("In der heutigen schnelllebigen Welt", p)
        self.assertIn("Zusammenfassend lässt sich sagen", p)

    def test_stilprofil_vollstaendig(self):
        stil, brand = cs.load_stil()
        for key in ("stilname", "haltung", "satzrhythmus", "tonfall",
                    "woerter", "hebel", "qualitaetsziele"):
            self.assertIn(key, stil, f"schreibstil.yaml: {key} fehlt")
        self.assertTrue((brand.get("voice") or {}).get("tone"))

    def test_modell_ist_claude_35_sonnet(self):
        cfg = cs.load_config()
        self.assertTrue(str(cfg["modell"]).startswith("claude-3-5-sonnet"))
        self.assertNotIn("4-5", str(cfg["modell"]))


class TestVerifikation(unittest.TestCase):
    def test_link_ziel_aenderung_verworfen(self):
        o = "Siehe [CHECK24](https://a.check24.net/x?pid=1) und spare rund 300 € im Jahr hier."
        n = "Siehe [CHECK24](https://evil.example/x) und spare rund 300 € im Jahr hier."
        self.assertFalse(cs.verify(o, n)[0])

    def test_anker_text_aenderung_verworfen(self):
        o = "Siehe [jetzt vergleichen](https://a.check24.net/x?pid=1) und sparen."
        n = "Siehe [jetzt ansehen](https://a.check24.net/x?pid=1) und sparen."
        self.assertFalse(cs.verify(o, n)[0])

    def test_ueberschrift_aenderung_verworfen(self):
        o = "## Sparpotenzial prüfen\n\nHier spart man rund 300 € pro Jahr hier."
        n = "## Sparpotenzial checken\n\nHier spart man rund 300 € pro Jahr hier."
        self.assertFalse(cs.verify(o, n)[0])

    def test_zahlen_aenderung_verworfen(self):
        o = "## Thema\n\nWer rund 300 € spart, spart viel Geld im Jahr hier."
        n = "## Thema\n\nWer rund 400 € spart, spart viel Geld im Jahr hier."
        self.assertFalse(cs.verify(o, n)[0])

    def test_shortcode_verlust_verworfen(self):
        o = "## Thema\n\n{{< check24 strom >}} spart bares Geld im Alltag hier."
        n = "## Thema\n\nSpares bares Geld im Alltag hier und hier."
        self.assertFalse(cs.verify(o, n)[0])

    def test_wortzahl_unter_90_prozent_verworfen(self):
        o = "## Thema\n\n" + ("Wort Wort Wort Wort Wort. " * 40)
        n = "## Thema\n\nWort Wort."
        self.assertFalse(cs.verify(o, n)[0])

    def test_legitime_stilaenderung_akzeptiert(self):
        o = ("## Thema\n\nDer erste Absatz folgt hier und ein zweiter Satz kommt "
             "dann mit rund 300 € pro Jahr.\n\nMehr Text folgt direkt danach hier.")
        n = ("## Thema\n\nDer erste Absatz beginnt hier, gefolgt von einem zweiten "
             "Satz mit rund 300 € pro Jahr.\n\nMehr Text folgt unmittelbar danach "
             "hier und schließt ab.")
        self.assertTrue(cs.verify(o, n)[0])


class TestKiAntwortGate(unittest.TestCase):
    def _orig(self):
        return ("## Thema\n\nEin kurzer Anfang mit 300 € als Zahl für den Fakten-"
                "Schutz und genug Wörter für die Längenprüfung hier und dort. "
                "Der zweite Satz liefert weitere Substanz für die Längenprüfung "
                "und klingt nachher hoffentlich besser als vorher im Raum. "
                "Der dritte Satz rundet den Absatz ab und bleibt faktentreu. "
                "Ein weiterer Absatz kommt hier dazu und sorgt für reichlich "
                "Fließtext, damit die Untergrenze von fünfhundert Zeichen auf "
                "jeden Fall überschritten wird und der Selbsttest ehrlich bleibt. "
                "Der Schlusssatz macht den Text deutlich länger als nötig.")

    def test_boesartige_antwort_verworfen(self):
        orig = self._orig()
        bösartig = orig.replace("300 €", "999 €")
        r, m = cs.polish_body("s", "u", orig, dict(cs.DEFAULT_CONFIG),
                              caller=lambda s, u, c: bösartig)
        self.assertIsNone(r)
        self.assertIn("Verifikation", m)

    def test_code_wrapping_wird_entfernt(self):
        orig = self._orig()
        wrapped = "```markdown\n" + orig.replace("Ein kurzer Anfang",
                                                 "Der kurze Einstieg") + "\n```"
        r, _ = cs.polish_body("s", "u", orig, dict(cs.DEFAULT_CONFIG),
                              caller=lambda s, u, c: wrapped)
        self.assertIsNotNone(r)
        self.assertFalse(r.startswith("```"))

    def test_leere_antwort_graceful(self):
        r, m = cs.polish_body("s", "u", self._orig(), dict(cs.DEFAULT_CONFIG),
                              caller=lambda s, u, c: None)
        self.assertIsNone(r)
        self.assertIn("leer", m)


class TestRotation(unittest.TestCase):
    def test_fingerprint_stabil_und_empfindlich(self):
        self.assertEqual(cs.fingerprint("gleich"), cs.fingerprint("gleich"))
        self.assertNotEqual(cs.fingerprint("gleich"), cs.fingerprint("anders"))

    def test_auswahl_neu_geaendert_auffrischen(self):
        now = datetime.datetime(2026, 9, 25, 12, 0, tzinfo=datetime.timezone.utc)
        state = {"version": 1, "artikel": {
            "frisch": {"fp": cs.fingerprint("b1"), "status": "ok",
                       "last": "2026-09-24T04:50:00+00:00"},
            "alt": {"fp": cs.fingerprint("b2"), "status": "ok",
                    "last": "2026-09-01T04:50:00+00:00"},
            "geaendert": {"fp": cs.fingerprint("alt-text"), "status": "ok",
                          "last": "2026-09-24T04:50:00+00:00"},
        }}
        self.assertEqual(cs.auswahl("neuer", "b0", state, 7, now)[1:], (0, "neu"))
        self.assertIsNone(cs.auswahl("frisch", "b1", state, 7, now)[1])
        self.assertEqual(cs.auswahl("geaendert", "b-neu", state, 7, now)[1], 1)
        prio, grund = cs.auswahl("alt", "b2", state, 7, now)[1:]
        self.assertEqual(prio, 2)
        self.assertIn("auffrischen", grund)


if __name__ == "__main__":
    unittest.main()
