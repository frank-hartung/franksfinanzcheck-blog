#!/usr/bin/env python3
"""Diagnose-Vertrag der Reserve-Zertifizierung (#661-Nachbarn, 14.11.2026).

BEFUND (Reserve-Lauf 43609259760): Das Ticket meldete als Erstes

    Reserve-Messung abgebrochen: Produktions-Gate nicht messbar:
    Publish-Gate: 1 Kandidat(en) für heute → ['2026-11-01-…']

Die erste Zeile einer Fehlermeldung ist die, die gelesen wird – und sie war
eine Fortschrittsmeldung. Zwei Ursachen:

  1. `certify_one` warf bei „… NICHT BEWEISBAR“ ABSICHTLICH ein
     `MeasurementUnavailable`; der eigene `except Exception` fing es wieder
     ab und verpackte es ein zweites Mal („Produktions-Gate nicht messbar“).
  2. Der Text war die vollständige Gate-Ausgabe, beginnend mit dem Echo der
     Kandidatenliste statt mit dem Grund.

Dieser Test hält beides fest: Der Abbruch reist unverpackt, und die
Diagnosezeile ist der Befund – nicht das Rauschen davor.
"""
from __future__ import annotations

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import reserve_readiness as rr  # noqa: E402

KANDIDAT = "2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten"

GATE_TEXT = f"""Publish-Gate: 1 Kandidat(en) für heute → ['{KANDIDAT}']

🛑 AFFILIATE-INTEGRITÄT NICHT BEWEISBAR → Publish-Gate stoppt (fail-closed,
kein Artikel wird verworfen oder zurückgestuft):
   Render-Beweis fehlt: public/ wurde nicht gebaut
   Diagnose: python3 scripts/affiliate_integrity_gate.py --selftest
"""


class Diagnosezeile(unittest.TestCase):
    def test_grund_beginnt_mit_dem_befund_nicht_mit_dem_echo(self) -> None:
        text = rr.nicht_beweisbar_grund(GATE_TEXT)
        self.assertTrue(text.startswith("🛑"), text)
        self.assertIn("AFFILIATE-INTEGRITÄT NICHT BEWEISBAR", text)
        self.assertIn("Render-Beweis fehlt", text)
        self.assertNotIn("Publish-Gate: 1 Kandidat(en) für heute", text)

    def test_ohne_marker_bleibt_das_echo_aus(self) -> None:
        text = rr.nicht_beweisbar_grund("Publish-Gate: 2 Kandidat(en) für heute → [x]\n"
                                        "irgendetwas anderes\n")
        self.assertEqual(text, "irgendetwas anderes")

    def test_leere_eingabe_ist_ehrlich(self) -> None:
        self.assertIn("nicht beweisbar", rr.nicht_beweisbar_grund(""))

    def test_diagnose_ist_begrenzt(self) -> None:
        lang = "\n".join(["🛑 WACHE NICHT BEWEISBAR:"] + [f"   Zeile {i}" for i in range(50)])
        self.assertLessEqual(len(rr.nicht_beweisbar_grund(lang)), 600)


class AbbruchReistUnverpackt(unittest.TestCase):
    """Der eigene Abbruch darf nicht als Werkzeugfehler umetikettiert werden."""

    def _lauf(self, gate_antwort: tuple[bool, str], *, publish_fehler: Exception | None = None):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / KANDIDAT / "index.md"
            index.parent.mkdir(parents=True)
            index.write_text("---\ntitle: x\n---\n\ntext\n", encoding="utf-8")
            fehlend = {"score": 0.95, "parts": {"sprache": 0.95}}
            with mock.patch.object(rr, "score_diagnosis", return_value=fehlend), \
                    mock.patch.object(rr, "reserve_editorial_findings", return_value=[]), \
                    mock.patch.object(rr, "capture_gate", return_value=gate_antwort), \
                    mock.patch.object(rr.rp, "publish_one",
                                      side_effect=publish_fehler), \
                    mock.patch.object(rr.ops, "work_seconds", return_value=600.0), \
                    mock.patch.object(rr.ops, "restore_on_termination",
                                      lambda: contextlib.nullcontext()), \
                    mock.patch("lesbarkeit_heiler.flesch", return_value=61.0):
                return rr.certify_one(index)

    def test_nicht_beweisbar_kommt_als_eigener_grund_an(self) -> None:
        with self.assertRaises(rr.MeasurementUnavailable) as ctx:
            self._lauf((False, GATE_TEXT))
        text = str(ctx.exception)
        self.assertTrue(text.startswith("🛑"), text)
        self.assertNotIn("Produktions-Gate nicht messbar", text)
        self.assertNotIn("Publish-Gate: 1 Kandidat(en)", text)

    def test_echter_werkzeugausfall_bleibt_als_solcher_benannt(self) -> None:
        with self.assertRaises(rr.MeasurementUnavailable) as ctx:
            self._lauf((True, ""), publish_fehler=RuntimeError("hugo fehlt"))
        self.assertIn("Produktions-Gate nicht messbar", str(ctx.exception))
        self.assertIn("hugo fehlt", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
