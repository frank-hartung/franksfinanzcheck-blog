#!/usr/bin/env python3
"""Regressionstests für das Deckungs-Ticket (#1039, Dauerheilung 06.11.2026).

Der Deckungs-Nachweis der Faktenfrische kann seit dem 04.11.2026 auch am
Bündeltag rot sein (`spitzenlast_stichtag`). Ohne diesen Schließpfad war
der rote Job ein Dauer-Alarm ohne Auftrag und ohne Schließpfad (C14) –
und ein Dauer-Alarm ohne Schließpfad verkommt zur Rauschquelle.

Diese Tests frieren den Vertrag ein:
  1. Genau DREI Zustände, rein aus der Messung: grün / rot / nicht beweisbar.
  2. Der Ticket-Text nennt Zahlen, Schließpfade und die menschliche
     Entscheidung – und behauptet nie eine Heilung, die es nicht gab.
  3. `spitze_geprueft` steht immer in der Tabelle (C33).
  4. Der Selbsttest des Tickets (`--selftest`) läuft offline.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODUL = ROOT / "scripts" / "faktenfrische_deckung_ticket.py"


def _lade():
    spec = importlib.util.spec_from_file_location("faktenfrische_deckung_ticket", MODUL)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


ticket = _lade()

PROBEDATUM = dt.date(2026, 11, 6)


def messung(**over) -> dict:
    basis = {"artikel": 115, "faellig": 3, "ueberfaellig": 1,
             "bedarf_je_tag": 2.82, "bedarf_je_woche": 19.7,
             "laeufe_je_tag": 1.0, "budget": 12, "sockel": 12,
             "hartes_limit": 16, "empfohlenes_budget": 12,
             "empfehlung_erreicht": True, "puenktlich": True,
             "rueckstand_abgebaut": True, "deckung_prozent": 425.0,
             "spitze_geprueft": 52}
    basis.update(over)
    return basis


class BewertungTest(unittest.TestCase):
    """Das Urteil ist eine reine Funktion der Messung (C19)."""

    def test_gruen_nur_wenn_alles_traegt(self):
        self.assertEqual(ticket.bewertung(messung(), None), "gruen")

    def test_strukturell_unterdeckt_ist_rot(self):
        self.assertEqual(
            ticket.bewertung(messung(empfehlung_erreicht=False), None), "rot")

    def test_fristbruch_ist_rot(self):
        self.assertEqual(ticket.bewertung(messung(puenktlich=False), None), "rot")

    def test_rueckstand_nicht_abbaubar_ist_rot(self):
        self.assertEqual(
            ticket.bewertung(messung(rueckstand_abgebaut=False), None), "rot")

    def test_spitzentag_befund_ist_rot(self):
        self.assertEqual(
            ticket.bewertung(messung(spitze_stichtag="2026-11-26",
                                     spitze_offen=38, spitze_frisch=83,
                                     spitze_puenktlich=False), None),
            "rot")

    def test_spitzentag_ohne_befund_bleibt_gruen(self):
        self.assertEqual(
            ticket.bewertung(messung(spitze_stichtag="2026-11-26",
                                     spitze_offen=0, spitze_puenktlich=True),
                             None),
            "gruen")

    def test_beweislos_ist_nie_gruen(self):
        self.assertEqual(ticket.bewertung(None, "Wache Exit 2"), "beweislos")
        self.assertEqual(ticket.bewertung(messung(), "kaputt"), "beweislos")


class SpitZeBefundTest(unittest.TestCase):
    def test_ohne_befund_none(self):
        self.assertIsNone(ticket.spitze_befund(messung()))

    def test_befund_nennt_tag_und_zahlen(self):
        satz = ticket.spitze_befund(messung(spitze_stichtag="2026-11-26",
                                            spitze_offen=38, spitze_frisch=83,
                                            spitze_puenktlich=False))
        self.assertIn("2026-11-26", satz)
        self.assertIn("38", satz)
        self.assertIn("83", satz)


class TicketBodyTest(unittest.TestCase):
    """Der Text ist eine reine Funktion der Messung (deterministisch)."""

    def test_rot_nennt_zahlen_schliesswege_und_marker(self):
        body = ticket.ticket_body(
            messung(spitze_stichtag="2026-11-26", spitze_offen=38,
                    spitze_frisch=83, spitze_puenktlich=False),
            None, run_url="https://example.invalid/run/1", heute=PROBEDATUM)
        for gefordert in (ticket.MARKER, "Spitzentag (#1039)", "2026-11-26",
                          "38", "Bündelung entzerren", "faktenfrische.yml",
                          "faktenfrische.yaml", "Herausgeber",
                          "schließt", "52 Bündeltage",
                          "https://example.invalid/run/1"):
            self.assertIn(gefordert, body)

    def test_rot_behauptet_nie_eine_heilung(self):
        body = ticket.ticket_body(
            messung(spitze_stichtag="2026-11-26", spitze_offen=38,
                    spitze_frisch=83, spitze_puenktlich=False),
            None, heute=PROBEDATUM)
        self.assertNotIn("Kein Befund", body)
        self.assertNotIn("grün\n\n|", body)
        self.assertTrue(body.startswith("## Faktenfrische-Deckung: rot"))

    def test_gruen_behauptet_nie_einen_befund(self):
        body = ticket.ticket_body(messung(), None, heute=PROBEDATUM)
        self.assertNotIn("Spitzentag (#1039): Am", body)
        self.assertNotIn("Strukturell unterdeckt", body)
        self.assertIn("Kein Befund", body)
        self.assertIn(ticket.MARKER, body)

    def test_beweislos_ist_fail_closed_und_ehrlich(self):
        body = ticket.ticket_body(None, "Wache Exit 2 (fail-closed)",
                                  heute=PROBEDATUM)
        self.assertIn("nicht beweisbar", body)
        self.assertIn("kein grünes Signal", body)
        self.assertIn("Schließpfad", body)
        self.assertIn(ticket.MARKER, body)
        self.assertNotIn("Bündelung entzerren", body)

    def test_titel_folgt_dem_urteil(self):
        self.assertIn("grün", ticket.ticket_body(messung(), None,
                                                heute=PROBEDATUM).splitlines()[0])
        self.assertIn("rot", ticket.ticket_body(
            messung(puenktlich=False), None,
            heute=PROBEDATUM).splitlines()[0])
        self.assertIn("nicht beweisbar",
                      ticket.ticket_body(None, "weg",
                                         heute=PROBEDATUM).splitlines()[0])


if __name__ == "__main__":
    unittest.main()
