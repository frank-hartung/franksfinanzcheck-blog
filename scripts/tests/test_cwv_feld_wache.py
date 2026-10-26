#!/usr/bin/env python3
"""Regressionstests der CWV-Feld-Wache (CrUX über PageSpeed Insights).

Der Vertrag in vier Sätzen (26.10.2026):
  1. Die Bewertung kommt aus der API (`category`), nicht aus einer eigenen
     Schwelle. Wer hier Zahlen erfindet, hat zwei Wahrheiten.
  2. Das schlechteste Einzelurteil bestimmt das Gesamturteil einer Seite.
  3. Ohne Felddaten steht UNGEPRÜFT – niemals GUT.
  4. Ein Netzfehler ist Störung (Exit 2), kein Befund – und der Selbsttest
     fasst niemals das Netz an.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cwv_feld_wache as wache  # noqa: E402


def _antwort(lcp="FAST", inp="FAST", cls="FAST", seite=True) -> dict:
    metriken = {
        "LARGEST_CONTENTFUL_PAINT_MS": {"category": lcp, "percentile": 2100},
        "INTERACTION_TO_NEXT_PAINT": {"category": inp, "percentile": 180},
        "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"category": cls, "percentile": 5},
    }
    schluessel = "loadingExperience" if seite else "originLoadingExperience"
    return {
        schluessel: {"metrics": metriken},
        "lighthouseResult": {"categories": {
            "performance": {"score": 0.94}, "accessibility": {"score": 1.0},
            "best-practices": {"score": 1.0}, "seo": {"score": 1.0}}},
        "analysisUTCTimestamp": "2026-10-26T05:00:00.000Z",
    }


class BewertungTests(unittest.TestCase):
    def test_api_sprache_wird_abgebildet(self):
        self.assertEqual(wache.bewerte_metrik({"category": "FAST"})["urteil"], "GUT")
        self.assertEqual(wache.bewerte_metrik({"category": "AVERAGE"})["urteil"],
                         "VERBESSERUNGSWUERDIG")
        self.assertEqual(wache.bewerte_metrik({"category": "SLOW"})["urteil"], "SCHLECHT")

    def test_unbekannte_kategorie_ist_nicht_gut(self):
        self.assertEqual(wache.bewerte_metrik({})["urteil"], "UNGEPRUEFT")
        self.assertEqual(wache.bewerte_metrik({"category": "NEU"})["urteil"], "UNGEPRUEFT")

    def test_schlechteste_metrik_bestimmt_das_urteil(self):
        self.assertEqual(wache.bewerte_seite(_antwort())["urteil"], "GUT")
        self.assertEqual(wache.bewerte_seite(_antwort(inp="AVERAGE"))["urteil"],
                         "VERBESSERUNGSWUERDIG")
        self.assertEqual(wache.bewerte_seite(_antwort(cls="SLOW"))["urteil"], "SCHLECHT")

    def test_ohne_felddaten_ungerpueft_niemals_gut(self):
        leer = {"lighthouseResult": {"categories": {"performance": {"score": 1.0}}}}
        befund = wache.bewerte_seite(leer)
        self.assertEqual(befund["urteil"], "UNGEPRUEFT")
        self.assertEqual(befund["feld"], {})

    def test_origin_felddaten_als_rueckfallebene(self):
        befund = wache.bewerte_seite(_antwort(seite=False))
        self.assertEqual(befund["feld_quelle"], "originLoadingExperience")
        self.assertEqual(befund["urteil"], "GUT")

    def test_laborwerte_werden_mitgefuehrt(self):
        befund = wache.bewerte_seite(_antwort())
        self.assertEqual(befund["labor_scores"]["performance"], 94)
        self.assertEqual(befund["labor_scores"]["seo"], 100)


class GesamturteilTests(unittest.TestCase):
    def test_keine_gepruefte_seite_ist_stoerung(self):
        urteil, anzahl = wache.gesamturteil([{"pfad": "/", "urteil": "UNGEPRUEFT"}])
        self.assertEqual((urteil, anzahl), ("STOERUNG", 0))

    def test_befund_gewinnt_gegen_ungerpueft(self):
        urteil, anzahl = wache.gesamturteil([
            {"pfad": "/", "urteil": "UNGEPRUEFT"},
            {"pfad": "/x/", "urteil": "SCHLECHT"},
        ])
        self.assertEqual((urteil, anzahl), ("SCHLECHT", 1))

    def test_leere_liste_ist_stoerung(self):
        self.assertEqual(wache.gesamturteil([]), ("STOERUNG", 0))


class ZieleTests(unittest.TestCase):
    def test_echte_zielliste_ist_lesbar(self):
        ziele = wache.lade_ziele()
        self.assertTrue(ziele)
        for ziel in ziele:
            self.assertTrue(ziel["pfad"].startswith("/"), ziel)

    def test_ziel_ohne_schraegstrich_ist_ein_fehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "ziele.json"
            datei.write_text(json.dumps({"ziele": [{"pfad": "cockpit/"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                wache.lade_ziele(datei)

    def test_leere_zielliste_ist_ein_fehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "ziele.json"
            datei.write_text(json.dumps({"ziele": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                wache.lade_ziele(datei)


class UrlTests(unittest.TestCase):
    def test_basis_und_pfad_ergeben_genau_einen_schraegstrich(self):
        self.assertEqual(wache.baue_url("https://a.de", "/x/"), "https://a.de/x/")
        self.assertEqual(wache.baue_url("https://a.de/", "/x/"), "https://a.de/x/")

    def test_psi_abfrage_traegt_url_und_strategie(self):
        url = wache.psi_url("https://a.de/x/", "desktop")
        self.assertIn("strategy=desktop", url)
        self.assertIn("url=https%3A%2F%2Fa.de%2Fx%2F", url)
        self.assertIn("category=seo", url)


class LaufTests(unittest.TestCase):
    def _lauf(self, *args: str) -> tuple[int, str, str]:
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = wache.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_fixture_lauf_schreibt_nichts_und_ist_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "antwort.json"
            datei.write_text(json.dumps(_antwort()), encoding="utf-8")
            code, out, _ = self._lauf("--fixture", str(datei), "--ziel", "/cockpit/",
                                      "--datum", "2026-10-26")
        self.assertEqual(code, 0, out)
        self.assertIn("GUT", out)

    def test_befund_ergibt_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "antwort.json"
            datei.write_text(json.dumps(_antwort(lcp="SLOW")), encoding="utf-8")
            code, out, _ = self._lauf("--fixture", str(datei), "--ziel", "/", "--json")
        self.assertEqual(code, 1, out)
        self.assertIn('"urteil": "SCHLECHT"', out)

    def test_ohne_felddaten_ungerpueft_ist_kein_befund_aber_stoerung(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "antwort.json"
            datei.write_text(json.dumps({"lighthouseResult": {"categories": {}}}), encoding="utf-8")
            code, out, _ = self._lauf("--fixture", str(datei), "--ziel", "/", "--json")
        self.assertEqual(code, 2, out)
        self.assertIn("UNGEPRUEFT", out)

    def test_netzfehler_ist_stoerung_nicht_befund(self):
        with patch.object(wache, "hole", side_effect=urllib.error.URLError("kein Netz")):
            code, _, err = self._lauf("--ziel", "/", "--datum", "2026-10-26")
        self.assertEqual(code, 2)
        self.assertIn("Störung", err)

    def test_der_schluessel_wird_nie_ausgegeben(self):
        with patch.dict("os.environ", {"PSI_API_KEY": "geheim-123"}), \
             patch.object(wache, "hole", return_value=_antwort()):
            code, out, err = self._lauf("--ziel", "/", "--datum", "2026-10-26")
        self.assertEqual(code, 0)
        self.assertNotIn("geheim-123", out + err)


class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        self.assertEqual(wache.selftest(), 0)

    def test_selbsttest_beruehrt_das_netz_nicht(self):
        with patch.object(wache, "hole", side_effect=AssertionError("Netz im Selbsttest")):
            self.assertEqual(wache.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
