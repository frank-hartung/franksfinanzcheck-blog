#!/usr/bin/env python3
"""Regressionstest: newsletter_cadence (23.09.2026, still ausgefallener Cron).

Der planmäßige Newsletter-Daily-Lauf (05:05 UTC, Mo–Fr) blieb an einem
Werktag komplett aus – kein Lauf, kein Rotton, keine Meldung, denn ein
Lauf, der nie startet, erzeugt kein Ereignis für irgendein Alerting.
Diese Datei friert die Entscheidungslogik der Kadenz-Wache ein:

  * Werktag ohne jeden Laufversuch (der Vorfall) → nachholen;
  * Ruhetag, bedienter Tag, laufender oder roter Lauf → keine Aktion;
  * die Fenstergrenze 03:30 UTC und die Vortags-Abgrenzung;
  * Trockenlauf: Befund ohne Dispatch ist rc 1, kein Netz-Call.

Ergänzt 25.09.2026 (zweiter Vorfall – Cron UND Wache blieben aus): der
Cloudflare-Worker ruft die Wache um 05:05 UTC (Taktgeber). Deshalb ist der
Tag ab SOLL+30 min (05:00 UTC) fällig, nicht erst ab 08:11 – und der
Zeitpunkt ist aus dem Versandvertrag gerechnet, nicht abgeschrieben.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


nc = _load("newsletter_cadence", os.path.join(ROOT, "scripts", "newsletter_cadence.py"))

# 25.09.2026 = Freitag: Ausfall-Szenarien unter der neuen Di/Fr-Kadenz.
FREITAG = dt.datetime(2026, 9, 25, 8, 11, tzinfo=dt.timezone.utc)
SAMSTAG = dt.datetime(2026, 9, 26, 8, 11, tzinfo=dt.timezone.utc)


def lauf(cid: str, erstellt: str, status: str = "completed",
         conclusion: str = "success") -> dict:
    return {"id": cid, "status": status, "conclusion": conclusion,
            "created_at": erstellt, "url": f"https://example.invalid/{cid}",
            "event": "schedule"}


class Taktgeber(unittest.TestCase):
    """Der Worker ruft um 05:05 UTC – die Wache muss dann schon entscheiden."""

    def test_faelligkeit_aus_dem_versandvertrag_gerechnet(self):
        self.assertEqual(dt.time(4, 30), nc.SOLL_UTC)
        self.assertEqual(dt.time(5, 0), nc.FAELLIG_AB)
        self.assertEqual(dt.time(3, 30), nc.FENSTER_START_UHRZEIT)

    def test_taktgeber_ruf_05_05_ohne_lauf_holt_nach(self):
        takt = dt.datetime(2026, 9, 25, 5, 5, tzinfo=dt.timezone.utc)
        erg = nc.entscheide([], takt)
        self.assertEqual("nachholen", erg["handlung"])

    def test_taktgeber_ruf_mit_taktgeber_gestartetem_lauf_ist_bedient(self):
        takt = dt.datetime(2026, 9, 25, 5, 5, tzinfo=dt.timezone.utc)
        erg = nc.entscheide([lauf("digest", "2026-09-25T04:30:12Z", status="in_progress",
                                  conclusion=None)], takt)
        self.assertEqual("bedient", erg["handlung"])

    def test_vor_der_faelligkeit_ist_ruhe(self):
        frueh = dt.datetime(2026, 9, 25, 4, 59, tzinfo=dt.timezone.utc)
        erg = nc.entscheide([], frueh)
        self.assertEqual("ruhetag", erg["handlung"])
        self.assertIn("05:00", erg["befund"])

    def test_verspaeteter_github_cron_08_11_entscheidet_weiterhin(self):
        erg = nc.entscheide([], FREITAG)
        self.assertEqual("nachholen", erg["handlung"])


class Entscheidung(unittest.TestCase):
    def test_vorfall_werktag_ohne_jeden_versuch_wird_nachgeholt(self):
        erg = nc.entscheide([lauf("alt", "2026-09-22T10:05:00Z")], FREITAG)
        self.assertEqual("nachholen", erg["handlung"])
        self.assertIn("04:30", erg["befund"], "Befund nennt den Soll-Termin")
        self.assertIsNone(erg["heutiger_lauf"])

    def test_ruhetag_fordert_nichts(self):
        erg = nc.entscheide([], SAMSTAG)
        self.assertEqual("ruhetag", erg["handlung"])

    def test_fenstergrenze_03_30_utc(self):
        zu_frueh = nc.entscheide([lauf("x", "2026-09-25T03:29:00Z")], FREITAG)
        puenktlich = nc.entscheide([lauf("y", "2026-09-25T03:31:00Z")], FREITAG)
        self.assertEqual("nachholen", zu_frueh["handlung"])
        self.assertEqual("bedient", puenktlich["handlung"])

    def test_gestriger_lauf_zaehlt_nicht_fuer_heute(self):
        erg = nc.entscheide([lauf("gestern", "2026-09-22T10:05:00Z")], FREITAG)
        self.assertEqual("nachholen", erg["handlung"],
                         "der verschobene Cron vom Dienstag ist kein heutiger")

    def test_laufender_und_roter_lauf_brauchen_kein_nachholen(self):
        unterwegs = nc.entscheide(
            [lauf("u", "2026-09-25T06:30:00Z", status="in_progress")], FREITAG)
        self.assertEqual("bedient", unterwegs["handlung"])
        rot = nc.entscheide(
            [lauf("r", "2026-09-25T05:07:00Z", conclusion="failure")], FREITAG)
        self.assertEqual("bedient", rot["handlung"])
        self.assertIn("ROT", rot["befund"],
                      "roter Lauf wird laut gemeldet, aber nicht wiederholt")

    def test_muell_timestamp_bricht_nichts(self):
        erg = nc.entscheide([{"id": "x", "status": "completed",
                              "conclusion": "success", "created_at": "Müll",
                              "url": "", "event": "schedule"}], FREITAG)
        self.assertEqual("nachholen", erg["handlung"])

    def test_fenster_start_faellt_in_den_vortag_vor_dem_fenster(self):
        frueh = dt.datetime(2026, 9, 25, 2, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(dt.datetime(2026, 9, 24, 3, 30, tzinfo=dt.timezone.utc),
                         nc.fenster_start(frueh))


class Verdrahtung(unittest.TestCase):
    def test_trockenlauf_meldet_befund_ohne_dispatch(self):
        erg = nc.pruefen("org/repo", jetzt=FREITAG, ohne_dispatch=True,
                         laeufe=[lauf("alt", "2026-09-22T10:05:00Z")])
        self.assertEqual(1, erg["rc"])
        self.assertTrue(erg["dispatch"].startswith("uebersprungen"))
        self.assertIn("nachgeholt", erg["befund"])

    def test_bedienter_tag_und_ruhetag_sind_gruen(self):
        erg = nc.pruefen("org/repo", jetzt=FREITAG, ohne_dispatch=True,
                         laeufe=[lauf("heute", "2026-09-25T05:06:00Z")])
        self.assertEqual(0, erg["rc"])
        leer = nc.pruefen("org/repo", jetzt=SAMSTAG, ohne_dispatch=True, laeufe=[])
        self.assertEqual(0, leer["rc"])

    def test_md_report_traegt_befund_und_aktion(self):
        erg = nc.pruefen("org/repo", jetzt=FREITAG, ohne_dispatch=True,
                         laeufe=[lauf("heute", "2026-09-25T05:06:00Z")])
        md = nc.als_md(erg)
        self.assertIn("Newsletter-Kadenz", md)
        self.assertIn("Kadenz gewahrt", md)

    def test_wache_haengt_an_ihrem_workflow(self):
        """Die Wache zählt genau den Workflow, den sie nachholt – ein
        abweichender Name würde still die Leere zählen."""
        self.assertEqual("newsletter-daily.yml", nc.WORKFLOW_DATEI)
        contract = os.path.join(ROOT, "scripts", "governance_contract.py")
        import io
        with io.open(contract, encoding="utf-8") as fh:
            self.assertIn("newsletter_digest.py", fh.read(),
                          "newsletter_digest bleibt Vertrags-Wache")


if __name__ == "__main__":
    unittest.main()
