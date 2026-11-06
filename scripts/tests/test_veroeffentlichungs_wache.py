#!/usr/bin/env python3
# ============================================================
#  TESTS: VEROEFFENTLICHUNGS-WACHE – der Nachlauf für Automatik-Commits
#  ------------------------------------------------------------
#  Befund 06.11.2026 (#1097-Familie): Reserve, GSC-Heilung und Scorecard
#  schreiben mit `GITHUB_TOKEN` direkt auf `main`; solche Commits lösen
#  KEINE PR-Prüfung aus. `main` war rot, ohne dass es jemand merkte
#  (fehlende Kurzantwort, veraltetes Register, veraltete Befund-Akte,
#  stiller Kanalausfall bei Reddit). Diese Wache ist der Nachlauf – und
#  diese Tests halten fest, dass sie meldet, dedupliziert und NICHT
#  heimlich schweigt.
# ============================================================
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

import veroeffentlichungs_wache as wache  # noqa: E402


class BefundUndDedupe(unittest.TestCase):
    """Ein Befund wird gemeldet – und zwar genau einmal."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        wache._fixture(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_befund_wird_erkannt(self) -> None:
        bericht = wache.pruefe(self.root, bereiche=("metadaten",))
        self.assertFalse(bericht["gruen"])
        self.assertTrue(bericht["befunde"])
        self.assertEqual({b["bereich"] for b in bericht["befunde"]}, {"metadaten"})
        self.assertIn("kurzantwort", " ".join(b["text"].lower() for b in bericht["befunde"]))

    def test_zweiter_lauf_ist_kein_neuer_befund(self) -> None:
        erster = wache.pruefe(self.root, bereiche=("metadaten",))
        self.assertTrue(erster["neu"])
        wache._schreiben(erster, root=self.root)
        zweiter = wache.pruefe(self.root, bereiche=("metadaten",))
        self.assertFalse(zweiter["neu"], "derselbe Befund darf kein zweites Issue erzeugen")
        self.assertEqual(erster["fingerabdruck"], zweiter["fingerabdruck"])

    def test_heilung_macht_gruen(self) -> None:
        pfad = os.path.join(self.root, "content", "posts", "2026-11-06-probe",
                            "index.md")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(wache._artikel("Ja, das ist der Fall."))
        bericht = wache.pruefe(self.root, bereiche=("metadaten",))
        self.assertTrue(bericht["gruen"], bericht["befunde"])
        self.assertFalse(bericht["neu"])

    def test_leerer_befund_hat_keinen_fingerabdruck(self) -> None:
        self.assertEqual(wache._fingerabdruck([]), "")


class DoppelterSchluessel(unittest.TestCase):
    """Der Bau-Brecher vom 06.11.2026: ein Schlüssel, zwei Werte."""

    def test_doppelter_schluessel_faellt_auf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "content", "posts", "2026-11-06-doppelt")
            os.makedirs(pfad, exist_ok=True)
            with open(os.path.join(pfad, "index.md"), "w", encoding="utf-8") as fh:
                fh.write('---\ntitle: "Doppelt"\n'
                         'description: "Eine ausreichend lange Beschreibung für '
                         'das Snippet-Fenster des Hauses im Testfall hier."\n'
                         'kurzantwort: "Der erste Wert."\n'
                         'date: 2026-11-06T00:00:00Z\ndraft: false\n'
                         'kurzantwort: "Der zweite Wert."\n---\n\nText.\n')
            befunde, werkzeug = wache.pruefe_frontmatter(tmp)
        self.assertEqual(werkzeug, [])
        self.assertEqual(len(befunde), 1, befunde)
        self.assertIn("kurzantwort", befunde[0]["text"])
        self.assertEqual(befunde[0]["bereich"], "frontmatter")

    def test_bestand_ist_geruestfrei(self) -> None:
        befunde, _ = wache.pruefe_frontmatter(ROOT)
        self.assertEqual(befunde, [], "doppelte Frontmatter-Schlüssel im Bestand")


class WerkzeugGetrennt(unittest.TestCase):
    """Ein Umgebungsfehler ist kein Inhaltsbefund – und fällt trotzdem auf."""

    def test_kaputte_wache_wird_als_werkzeugfehler_gemeldet(self) -> None:
        original = wache.PRUEFUNGEN.get("metadaten")

        def kaputt(_root: str):
            raise RuntimeError("Absicht")

        wache.PRUEFUNGEN["metadaten"] = kaputt
        try:
            with tempfile.TemporaryDirectory() as tmp:
                bericht = wache.pruefe(tmp, bereiche=("metadaten",))
        finally:
            if original is not None:
                wache.PRUEFUNGEN["metadaten"] = original
        self.assertTrue(bericht["werkzeugfehler"])
        self.assertEqual(bericht["befunde"], [])
        self.assertFalse(bericht["gruen"], "auch ein Werkzeugfehler ist nicht grün")

    def test_unbekannter_bereich_ist_werkzeugfehler(self) -> None:
        bericht = wache.pruefe(".", bereiche=("gibtsnicht",))
        self.assertTrue(bericht["werkzeugfehler"])


class Kanaltreue(unittest.TestCase):
    """Der stille Kanalausfall (#716) muss auffallen."""

    def test_kanal_mit_zusatzsperre_faellt_auf(self) -> None:
        import social_channels as sch
        cfg = sch.load_config()
        meta = dict(sch.meta_of(cfg))
        channels = dict(sch.channel_map(cfg))
        # Ein Kanal, der ein Wort sperrt, das in jedem Artikel vorkommt,
        # ist für JEDEN Artikel unsendbar – genau der Zustand, den die
        # Wache sichtbar machen muss.
        kanal = dict(channels["mastodon"])
        kanal["gate"] = {"blocked_terms": ["wechsel"]}
        channels = {"mastodon": kanal}
        befunde, werkzeug = wache.pruefe_winkel(ROOT, meta=meta, channels=channels)
        self.assertEqual(werkzeug, [])
        self.assertEqual(len(befunde), 1)
        self.assertIn("mastodon", befunde[0]["text"])
        self.assertIn("keinem Winkel sendbar", befunde[0]["text"])

    def test_bestand_ist_kanaltreu(self) -> None:
        """Der heutige Bestand: jeder aktive Kanal hat je Artikel einen Winkel."""
        bericht = wache.pruefe(ROOT, bereiche=("winkel",))
        self.assertTrue(bericht["gruen"], bericht["befunde"])


class Issue(unittest.TestCase):
    """Ein Issue je Befundmenge – kein täglicher Nachtlauf-Alarm."""

    def _bericht(self) -> dict:
        return {"stand": "2026-11-06T15:00:00Z", "fingerabdruck": "abc123abc123abcd",
                "befunde": [{"bereich": "metadaten", "text": "M4: Kurzantwort fehlt",
                             "datei": "content/posts/x/index.md"}],
                "werkzeugfehler": [], "gruen": False, "neu": True,
                "geprueft": ["metadaten"], "bisher_gemeldet": ""}

    def test_issue_wird_geoeffnet(self) -> None:
        aufrufe: list[list[str]] = []

        def runner(args: list[str]) -> str:
            aufrufe.append(args)
            return "0\n" if args[0] == "issue" and args[1] == "list" else "https://x/1\n"

        titel = wache.issue_oeffnen(self._bericht(), runner=runner)
        self.assertIsNotNone(titel)
        self.assertIn("abc123abc123abcd", titel)
        self.assertEqual(len(aufrufe), 2)
        self.assertIn("--label", aufrufe[1])

    def test_kein_zweites_issue(self) -> None:
        aufrufe: list[list[str]] = []

        def runner(args: list[str]) -> str:
            aufrufe.append(args)
            return "7\n"

        self.assertIsNone(wache.issue_oeffnen(self._bericht(), runner=runner))
        self.assertEqual(len(aufrufe), 1, "bei offenem Issue darf nichts erzeugt werden")

    def test_ohne_befund_kein_issue(self) -> None:
        bericht = self._bericht()
        bericht["befunde"] = []
        self.assertIsNone(wache.issue_oeffnen(bericht, runner=lambda a: "0\n"))

    def test_koerper_nennt_bereich_und_reproduktion(self) -> None:
        koerper = wache._issue_koerper(self._bericht())
        self.assertIn("metadaten", koerper)
        self.assertIn("veroeffentlichungs_wache.py --wache", koerper)
        self.assertIn("blockiert die Auslieferung", koerper)


class SelbsttestLaeuft(unittest.TestCase):
    def test_selftest_gruen(self) -> None:
        self.assertEqual(wache.selbsttest(), 0)


if __name__ == "__main__":
    unittest.main()
