#!/usr/bin/env python3
"""Regressionstests für den Themennachschub (WF-D4E0 / #821).

DER BEFUND, DEN DIESE DATEI FESTSCHREIBT (25.10.2026)
=====================================================
Der Vorrat der Content-Reserve fiel zwischen dem 19.10. und dem 25.10. von
sechs auf einen gate-fertigen Kandidaten. Der Lauf war jede Nacht rot, und
jede Nacht stand im Ticket nur der Vorrat.

Zwei Ursachen – beide hier als Test festgehalten:

1. DEKLINATIONS-LÜCKE IN DER DUBLETTENPRÜFUNG.
   `reserve_topics.FUELLWOERTER` kannte „guenstig", aber nicht „guenstige(n)".
   Ergebnis: Ein einziges Artikel-Wort sperrte 15 völlig verschiedene Themen;
   154 von 202 Themen galten als „belegt", die restlichen 21 waren
   ausschließlich YMYL-Hochrisiko. In der AUTO-Bahn war **0** frei.

2. EIN BEFUND, DER DIE FALSCHE BAUSTELLE NENNT.
   `reserve_gate.diagnose()` meldete „Die Disposition findet kein freies Thema
   (alles thematisch belegt oder im Cooldown)" – obwohl 21 Themen frei waren.
   Wer das liest, prüft Cooldowns, Dubletten und Provider-Keys, aber nicht den
   Themennachschub.

Die Tests prüfen die Reparatur in beide Richtungen: Was frei werden MUSS, wird
frei – und was eine echte Dublette ist, bleibt eine.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reserve_gate as gate  # noqa: E402
import reserve_topics as rt  # noqa: E402
import themen_nachschub_waechter as wache  # noqa: E402


class DeklinationsLueckeTest(unittest.TestCase):
    """Füllwörter wirken auch in gebeugter Form – sonst leert sich der Pool."""

    def test_beugte_fuellwoerter_blockieren_kein_fremdes_thema(self):
        # Genau diese Paare waren am 25.10. gesperrt – nur über „guenstige".
        paare = [
            ("Günstige Tarife fürs Handy",
             "Günstige Gasanbieter für den Haushalt finden"),
            ("Günstige Flüge für den Spätsommer finden",
             "Günstige Reisekreditkarten für den Urlaub"),
            ("Die besten Tarife für ein günstiges Handy-Abonnement",
             "Die besten DSL-Tarife für Zuhause und unterwegs"),
        ]
        for thema, bestand in paare:
            with self.subTest(thema=thema):
                self.assertIsNone(
                    rt.thema_kollision(thema, {"x": bestand}),
                    f"„{thema}“ darf nicht an „{bestand}“ scheitern – "
                    f"gemeinsam ist nur ein Füllwort")

    def test_echte_dubletten_bleiben_dubletten(self):
        # Die Schutzrichtung ist wichtiger als die Freigabe: Diese Paare
        # bedienen dieselbe Suchabsicht und MÜSSEN kollidieren.
        paare = [
            ("Stromfresser im Haushalt entlarven",
             "Energiediebe stoppen: So kannst du Stromfresser finden"),
            ("Günstige Reiseversicherungen für den Winterurlaub",
             "Günstige Reiseversicherungen für den Sommerurlaub finden"),
            ("Kreditkarten mit Reiseversicherung im Test",
             "Die besten Kreditkarten für Reisen"),
            ("Gasrechnung senken vor dem Winter",
             "Gasrechnung senken: Warum ich meine Heizung im August prüfe"),
        ]
        for thema, bestand in paare:
            with self.subTest(thema=thema):
                self.assertIsNotNone(
                    rt.thema_kollision(thema, {"x": bestand}),
                    f"„{thema}“ ist eine Dublette von „{bestand}“")

    def test_produkte_bleiben_leitbegriffe(self):
        # Eine bequeme Füllwort-Liste würde die Prüfung entwerten: Produkte
        # und Sachthemen dürfen NICHT als Füllwort enden.
        for wort in ("mietwagen", "kreditkarte", "internet", "stromfresser",
                     "fixkosten", "gebuehren", "wechselbonus", "urlaub"):
            with self.subTest(wort=wort):
                self.assertNotIn(wort, rt.FUELLWOERTER)


class VorlaufTest(unittest.TestCase):
    """Stück-Vorrat in Produktionstage: die Zahl, die man planen kann."""

    def test_vorlauf_formel(self):
        self.assertEqual(wache.vorlauf_tage(55, 2), 27.5)
        self.assertEqual(wache.vorlauf_tage(0, 2), 0.0)
        # Division durch Null ist kein Absturz, sondern der Mindestbedarf 1.
        self.assertEqual(wache.vorlauf_tage(3, 0), 3.0)


class DiagnoseEhrlichkeitTest(unittest.TestCase):
    """Der Engpass-Befund nennt die Bahn – nicht „alles belegt"."""

    def _setze_lage(self, daten):
        original = gate.nachschub_lage
        gate.nachschub_lage = lambda: daten
        self.addCleanup(setattr, gate, "nachschub_lage", original)

    def _lage(self, **overrides):
        daten = {
            "verdikt": "ok", "befund": "", "frei_auto": 40,
            "frei_fachfreigabe": 20, "vorlauf_tage": 20.0,
            "mindestvorlauf_tage": 14, "tagesbedarf": 2,
            "fehlende_themen": 0, "themen_gesamt": 238,
            "themen_belegt": 127, "themen_im_cooldown": 47,
            "warnungen": [],
        }
        daten.update(overrides)
        return daten

    def test_nur_fachfreigabe_frei_wird_als_auto_luecke_gemeldet(self):
        # Der reale Zustand vom 25.10.2026, 08:45 UTC.
        self._setze_lage(self._lage(verdikt="erschoepft", frei_auto=0,
                                    frei_fachfreigabe=21, vorlauf_tage=0.0,
                                    fehlende_themen=28))
        zeilen = gate.diagnose(1, 6, [])
        text = " ".join(zeilen)
        self.assertIn("AUTO-BAHN", text)
        self.assertIn("Fachfreigabe", text)
        self.assertNotIn("alles thematisch belegt oder im Cooldown", text,
                         "genau dieser Satz schickte die Redaktion drei "
                         "Wochen lang auf die falsche Fährte")

    def test_beide_bahnen_leer_ist_ein_anderer_befund(self):
        self._setze_lage(self._lage(verdikt="erschoepft", frei_auto=0,
                                    frei_fachfreigabe=0, vorlauf_tage=0.0))
        text = " ".join(gate.diagnose(1, 6, []))
        self.assertIn("BEIDE BAHNEN", text)
        self.assertIn("127", text)   # belegt wird beziffert, nicht behauptet

    def test_knapper_vorlauf_wird_vorgewarnt(self):
        self._setze_lage(self._lage(verdikt="knapp", frei_auto=6,
                                    vorlauf_tage=3.0, fehlende_themen=22))
        text = " ".join(gate.diagnose(1, 6, []))
        self.assertIn("THEMENVORLAUF KNAPP", text)
        self.assertIn("22", text)

    def test_gesunder_vorlauf_erzeugt_keinen_dauer_alarm(self):
        self._setze_lage(self._lage())
        text = " ".join(gate.diagnose(1, 6, []))
        self.assertNotIn("THEMENMANGEL", text)
        self.assertNotIn("THEMENVORLAUF", text)

    def test_produktionsbefund_nennt_den_vorlauf(self):
        self._setze_lage(self._lage(frei_auto=55, vorlauf_tage=27.5))
        text = " ".join(gate.diagnose(1, 6, []))
        self.assertIn("PRODUKTION", text)
        self.assertIn("27.5", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
