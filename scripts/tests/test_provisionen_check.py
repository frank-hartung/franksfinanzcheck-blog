#!/usr/bin/env python3
"""Vertragstests: scripts/provisionen_check.py (Provisions-Tabelle, 08.10.2026).

Festgehalten wird:
  1. Kopfzeile und Feldzahl sind bindend (sonst rutschen Summen in falsche Spalten).
  2. Monate, Partner, Ganzzahlen und Beträge werden hart geprüft.
  3. Eine Provision ohne Abrechnungsnummer ist ein Fehler.
  4. Personenbezogene Angaben (E-Mail, IBAN, lange Zahlen) werden abgewiesen.
  5. Fehlt die echte Datei, ist das „Datenlage offen“ und kein Fehler.
  6. Summen rechnen mit Cent-genauen Decimal-Werten, nicht mit Gleitkomma.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKRIPT = os.path.join(ROOT, "scripts", "provisionen_check.py")
VORLAGE = os.path.join(ROOT, "data", "provisionen", "provisionen-vorlage.csv")
KOPF = "monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n"
HEUTE = dt.date(2026, 10, 8)


def _load():
    spec = importlib.util.spec_from_file_location("provisionen_check", SKRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


pc = _load()


class KopfUndAufbau(unittest.TestCase):
    def test_vorlage_hat_genau_die_kopfzeile(self):
        with open(VORLAGE, encoding="utf-8") as f:
            self.assertEqual(f.read(), KOPF)

    def test_falsche_kopfzeile_ist_fehler(self):
        fehler = pc.pruefe_text("partner,monat,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n", HEUTE)
        self.assertTrue(any("Kopfzeile falsch" in f for f in fehler))

    def test_leere_datei_ist_fehler(self):
        self.assertTrue(pc.pruefe_text("", HEUTE))

    def test_falsche_feldzahl_ist_fehler(self):
        fehler = pc.pruefe_text(KOPF + "2026-09,CHECK24,1,0,0\n", HEUTE)
        self.assertTrue(any("Felder statt" in f for f in fehler))

    def test_leerzeilen_sind_erlaubt(self):
        self.assertEqual(pc.pruefe_text(KOPF + "\n2026-09,CHECK24,1,0,0,,\n\n", HEUTE), [])


class Feldregeln(unittest.TestCase):
    def pruefe(self, zeile: str):
        return pc.pruefe_text(KOPF + zeile + "\n", HEUTE)

    def test_monat_muss_jjjj_mm_sein(self):
        self.assertTrue(self.pruefe("2026-9,CHECK24,1,0,0,,"))
        self.assertTrue(self.pruefe("09.2026,CHECK24,1,0,0,,"))

    def test_aktueller_monat_ist_erlaubt_zukunft_nicht(self):
        self.assertEqual(self.pruefe("2026-10,CHECK24,0,0,0,,"), [])
        self.assertTrue(self.pruefe("2026-11,CHECK24,0,0,0,,"))

    def test_partner_nur_aus_der_liste(self):
        self.assertEqual(self.pruefe("2026-09,Tarifcheck,0,0,0,,"), [])
        self.assertEqual(self.pruefe("2026-09,sonstig,0,0,0,,"), [])
        self.assertTrue(self.pruefe("2026-09,Irgendwer,0,0,0,,"))

    def test_ganzzahlen_ohne_vorzeichen(self):
        self.assertTrue(self.pruefe("2026-09,CHECK24,-1,0,0,,"))
        self.assertTrue(self.pruefe("2026-09,CHECK24,1,1.5,0,,"))

    def test_betrag_mit_dezimalpunkt_und_zwei_stellen(self):
        self.assertEqual(self.pruefe("2026-09,CHECK24,1,0,126.5,CHECK24-1,"), [])
        self.assertTrue(self.pruefe('2026-09,CHECK24,1,0,"126,50",CHECK24-1,'))
        self.assertTrue(self.pruefe("2026-09,CHECK24,1,0,1.234,CHECK24-1,"))

    def test_provision_ohne_abrechnungsnummer_ist_fehler(self):
        fehler = self.pruefe("2026-09,CHECK24,1,0,10.00,,")
        self.assertTrue(any("abrechnung_ref fehlt" in f for f in fehler))

    def test_null_provision_braucht_keine_abrechnung(self):
        self.assertEqual(self.pruefe("2026-09,CHECK24,0,2,0,,Nur Stornos"), [])

    def test_notiz_hat_hoechstens_200_zeichen(self):
        self.assertEqual(self.pruefe("2026-09,CHECK24,0,0,0,,"), [])
        self.assertTrue(self.pruefe("2026-09,CHECK24,0,0,0,," + "x" * 201))


class Datenschutz(unittest.TestCase):
    def pruefe(self, zeile: str):
        return pc.pruefe_text(KOPF + zeile + "\n", HEUTE)

    def test_email_in_der_notiz_wird_abgewiesen(self):
        self.assertTrue(self.pruefe("2026-09,CHECK24,1,0,0,,kunde@example.de"))

    def test_iban_mit_und_ohne_leerzeichen_wird_abgewiesen(self):
        self.assertTrue(self.pruefe("2026-09,CHECK24,1,0,0,,DE89 3704 0044 0532 0130 00"))
        self.assertTrue(self.pruefe("2026-09,CHECK24,1,0,0,,DE89370400440532013000"))

    def test_lange_zahlenfolge_wird_abgewiesen(self):
        self.assertTrue(self.pruefe("2026-09,CHECK24,1,0,0,CHECK24-123456789,"))

    def test_abrechnungsnummer_im_jahr_monat_format_ist_ok(self):
        self.assertEqual(self.pruefe("2026-09,CHECK24,1,0,10.00,CHECK24-Abr-2026-09,"), [])

    def test_personenbezug_erkennung_direkt(self):
        self.assertEqual(pc.personenbezug("Frühjahrsaktion, Abrechnung 2026-09"), None)
        self.assertEqual(pc.personenbezug("max@example.de"), "E-Mail-Adresse")


class Summen(unittest.TestCase):
    def test_summen_je_partner_und_gesamt_cent_genau(self):
        text = KOPF + (
            "2026-08,CHECK24,2,0,10.10,CHECK24-1,\n"
            "2026-09,CHECK24,1,1,0.20,CHECK24-2,\n"
            "2026-09,Tarifcheck,4,0,7.00,TC-9,\n"
        )
        zeilen, fehler = pc.lese_text(text)
        self.assertEqual(fehler, [])
        z = pc.zusammenfassung(zeilen)
        self.assertEqual(z["je_partner"]["CHECK24"]["provision"], Decimal("10.30"))
        self.assertEqual(z["je_partner"]["CHECK24"]["stornos"], 1)
        self.assertEqual(z["abschluesse"], 7)
        self.assertEqual(z["provision"], Decimal("17.30"))
        self.assertEqual(z["schnitt_je_abschluss"], Decimal("17.30") / 7)

    def test_luecken_zwischen_erstem_und_letztem_monat(self):
        text = KOPF + "2026-07,CHECK24,1,0,0,,\n2026-09,CHECK24,1,0,0,,\n"
        zeilen, _ = pc.lese_text(text)
        self.assertEqual(pc.zusammenfassung(zeilen)["luecken"], ["2026-08"])

    def test_jahreswechsel_in_der_luecke(self):
        self.assertEqual(pc._monate_zwischen("2025-11", "2026-02"), ["2025-11", "2025-12", "2026-01", "2026-02"])

    def test_deutsche_zahlenschreibweise(self):
        self.assertEqual(pc.eur(Decimal("1234.5")), "1.234,50 €")
        self.assertEqual(pc.eur(Decimal("0")), "0,00 €")

    def test_keine_zeilen_kein_schnitt(self):
        z = pc.zusammenfassung([])
        self.assertIsNone(z["schnitt_je_abschluss"])


class Kommandozeile(unittest.TestCase):
    def main(self, argv):
        """Ausgabe des Skripts wegschreiben, damit das Testprotokoll lesbar bleibt."""
        with contextlib.redirect_stdout(io.StringIO()):
            return pc.main(argv)

    def test_selftest_ist_gruen(self):
        self.assertEqual(pc.selbsttest(), [])

    def test_fehlende_datei_ist_offen_nicht_fehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.main(["--datei", os.path.join(tmp, "nicht-da.csv")]), 0)

    def test_gueltige_datei_exit_null_mit_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "p.csv")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write(KOPF + "2026-09,CHECK24,2,0,20.00,CHECK24-1,\n")
            self.assertEqual(self.main(["--datei", pfad, "--summary", "--heute", "2026-10-08"]), 0)

    def test_ungueltige_datei_exit_eins(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "p.csv")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write(KOPF + "2026-09,CHECK24,2,0,20.00,,\n")
            self.assertEqual(self.main(["--datei", pfad, "--heute", "2026-10-08"]), 1)


if __name__ == "__main__":
    unittest.main()
