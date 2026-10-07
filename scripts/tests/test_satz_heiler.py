"""Regressionen für Koordinaten, Satzschutz und Teilfortschritt in #614."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import satz_heiler as sh  # noqa: E402


class SatzHeilerRegressionen(unittest.TestCase):
    def setUp(self):
        self.raw = sh._fixture()
        self.schwerer_satz = next(iter(sh.LEICHT))

    def _teilfortschritt(self, werte, tor, *, nur_ganz=None):
        with (patch.object(sh, "KI_CALL", sh._fake_ki),
              patch.object(sh.lh, "flesch", side_effect=werte),
              patch.object(sh.lh, "verifiziere", return_value=tor)):
            return sh.heile_text("probe", self.raw, max_ki=1,
                                 nur_ganz=nur_ganz)

    def _teilfortschritt_datei(self, raw: str, neu_raw: str, *, fix: bool):
        with tempfile.TemporaryDirectory(prefix="satz-heiler-test-") as tmp:
            post_dir = Path(tmp) / "kandidat"
            post_dir.mkdir()
            pfad = post_dir / "index.md"
            pfad.write_text(raw, encoding="utf-8")
            ergebnis = {
                "slug": "kandidat", "ok": True, "neu_raw": neu_raw,
                "vor": 59.0, "nach": 59.4, "ersetzt": [{"vorher": "alt"}],
                "verworfen": [], "anfragen": 1, "gruende": ["Teilfortschritt"],
                "teilfortschritt": True, "vollstaendig": False,
                "geschrieben": False,
            }
            with patch.object(sh, "heile_text", return_value=ergebnis):
                berichte, befund = sh._verarbeite(
                    [str(pfad)], fix=fix, max_n=None, max_ki=1, ki=True)
            return pfad.read_text(encoding="utf-8"), berichte, befund

    def test_wirkungsprobe_nutzt_die_echte_formel_und_heilt(self):
        ok, meldung = sh.wirkungsprobe()
        self.assertTrue(ok, meldung)
        self.assertIn("73.6", meldung)
        self.assertIn("Satzschutz", meldung)
        self.assertGreaterEqual(sh._body_offset(self.raw), 2532)

    def test_kurzer_kopf_aus_altprobe_bleibt_unversehrt(self):
        raw = ("---\ntitle: Probe\ndate: 2026-10-07\ndraft: true\n---\n\n"
               + sh.SCHWER)
        with patch.object(sh, "KI_CALL", sh._fake_ki):
            result = sh.heile_text("probe", raw)
        self.assertTrue(result["ok"], result["gruende"])
        self.assertIn("Notiere die Zählerstände.", result["neu_raw"])
        self.assertIn(sh.LEICHT[self.schwerer_satz].split(".", 1)[0],
                      result["neu_raw"])
        self.assertEqual(sh._kopf_bis_body(raw),
                         sh._kopf_bis_body(result["neu_raw"]))

    def test_wirkungsprobe_bewahrt_den_kopf_exakt(self):
        with patch.object(sh, "KI_CALL", sh._fake_ki):
            result = sh.heile_text("probe", self.raw)
        self.assertTrue(result["ok"], result["gruende"])
        self.assertEqual(sh._kopf_bis_body(self.raw),
                         sh._kopf_bis_body(result["neu_raw"]))

    def test_finder_liefert_datei_und_nicht_body_koordinaten(self):
        start = sh._finde_satz(self.raw, self.schwerer_satz)
        self.assertGreater(start, sh._body_offset(self.raw))
        self.assertEqual(self.schwerer_satz,
                         self.raw[start:start + len(self.schwerer_satz)])

    def test_finder_sucht_nie_im_frontmatter(self):
        mit_satz_im_kopf = self.raw.replace(
            'title: "Probe: Satz-Heiler"\n',
            f'title: "Probe: Satz-Heiler"\nprobe_text: "{self.schwerer_satz}"\n',
            1)
        start = sh._finde_satz(mit_satz_im_kopf, self.schwerer_satz)
        self.assertGreaterEqual(start, sh._body_offset(mit_satz_im_kopf))
        self.assertEqual(self.schwerer_satz,
                         mit_satz_im_kopf[start:start + len(self.schwerer_satz)])

    def test_finder_gibt_null_fuer_nicht_vorhandene_saetze(self):
        self.assertEqual(0, sh._finde_satz(self.raw, "Dieser Satz steht nirgends."))

    def test_finder_null_bleibt_fail_closed_und_selbsttest_meldet_sabotage(self):
        with patch.object(sh, "KI_CALL", sh._fake_ki), \
                patch.object(sh, "_finde_satz", return_value=0):
            result = sh.heile_text("probe", self.raw, max_ki=1)
            self.assertFalse(result["ok"])
            self.assertEqual(self.raw, result["neu_raw"])
            self.assertEqual([], result["ersetzt"])
            self.assertTrue(any(
                "vollständiger Satz im Body nicht gefunden" in v["gruende"]
                for v in result["verworfen"]))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(1, sh.run_selftest())
            self.assertIn("FEHLGESCHLAGEN", output.getvalue())

    def test_unversehrte_saetze_erlaubt_vollstaendigen_ersatz(self):
        neuer_satz = sh.LEICHT[self.schwerer_satz]
        start = sh._finde_satz(self.raw, self.schwerer_satz)
        neu = (self.raw[:start] + neuer_satz
               + self.raw[start + len(self.schwerer_satz):])
        self.assertEqual([], sh.unversehrte_saetze(
            self.raw, neu, [(self.schwerer_satz, neuer_satz)]))

    def test_unversehrte_saetze_verwirft_zerstueckelten_nachbarsatz(self):
        neuer_satz = sh.LEICHT[self.schwerer_satz]
        start = sh._finde_satz(self.raw, self.schwerer_satz)
        neu = (self.raw[:start] + neuer_satz
               + self.raw[start + len(self.schwerer_satz):])
        neu = neu.replace("So findest du teure Verträge schnell.",
                          "So findest du Verträge schnell.", 1)
        fehler = sh.unversehrte_saetze(
            self.raw, neu, [(self.schwerer_satz, neuer_satz)])
        self.assertTrue(any("Satz-Zerstückelung" in f for f in fehler), fehler)

    def test_kopf_tor_ist_unabhaengig_vom_ganztexttor(self):
        veraendert = self.raw.replace(
            'title: "Probe: Satz-Heiler"', 'title: "Kopf verändert"', 1)
        with patch.object(sh.lh, "verifiziere", return_value=[]):
            fehler = sh.unversehrte_saetze(self.raw, veraendert, [])
        self.assertTrue(any("Kopf-Tor" in f for f in fehler), fehler)

    def test_finder_rechnet_nach_vorheriger_laengenaenderung_frisch(self):
        zweiter_satz = "Ein Blick auf das Typenschild hilft dabei."
        erster_satz = "So findest du teure Verträge schnell."
        start_alt = sh._finde_satz(self.raw, erster_satz)
        zweiter_alt = sh._finde_satz(self.raw, zweiter_satz)
        ersatz = "Finde teure Verträge schnell."
        verschoben = (self.raw[:start_alt] + ersatz
                      + self.raw[start_alt + len(erster_satz):])
        start_neu = sh._finde_satz(verschoben, zweiter_satz)
        self.assertEqual(zweiter_alt + len(ersatz) - len(erster_satz), start_neu)
        self.assertEqual(zweiter_satz,
                         verschoben[start_neu:start_neu + len(zweiter_satz)])

    def test_sauberer_teilfortschritt_ab_0_3_flesch_wird_angenommen(self):
        t1 = "T1 Lesbarkeit: Flesch 59.4 < Schwelle 60 (nicht veröffentlichungsfähig)"
        result = self._teilfortschritt([59.0, 59.4, 59.4], [t1])
        self.assertTrue(result["ok"], result["gruende"])
        self.assertTrue(result["teilfortschritt"])
        self.assertFalse(result["vollstaendig"])
        self.assertEqual(self.raw[:sh._body_offset(self.raw)],
                         result["neu_raw"][:sh._body_offset(result["neu_raw"])])

    def test_teilfortschritt_unter_0_3_flesch_wird_verworfen(self):
        t1 = "T1 Lesbarkeit: Flesch 59.2 < Schwelle 60 (nicht veröffentlichungsfähig)"
        result = self._teilfortschritt([59.0, 59.2, 59.2], [t1])
        self.assertFalse(result["ok"])
        self.assertEqual(self.raw, result["neu_raw"])

    def test_teilfortschritt_mit_anderen_torfunden_wird_verworfen(self):
        t1 = "T1 Lesbarkeit: Flesch 59.4 < Schwelle 60 (nicht veröffentlichungsfähig)"
        t2 = "T2 Textverständnis: harter Fund R7 im Ergebnis"
        result = self._teilfortschritt([59.0, 59.4, 59.4], [t1, t2])
        self.assertFalse(result["ok"])
        self.assertEqual(self.raw, result["neu_raw"])
        self.assertTrue(any("T2" in g for g in result["gruende"]))

    def test_nur_ganz_aktiviert_alles_oder_nichts(self):
        t1 = "T1 Lesbarkeit: Flesch 59.4 < Schwelle 60 (nicht veröffentlichungsfähig)"
        result = self._teilfortschritt([59.0, 59.4, 59.4], [t1], nur_ganz=True)
        self.assertFalse(result["ok"])
        self.assertEqual(self.raw, result["neu_raw"])

    def test_umgebungsvariable_aktiviert_alles_oder_nichts(self):
        t1 = "T1 Lesbarkeit: Flesch 59.4 < Schwelle 60 (nicht veröffentlichungsfähig)"
        with patch.dict(os.environ, {sh.SATZ_NUR_GANZ_ENV: "1"}):
            result = self._teilfortschritt([59.0, 59.4, 59.4], [t1])
        self.assertFalse(result["ok"])
        self.assertEqual(self.raw, result["neu_raw"])

    def test_verarbeite_schreibt_teilfortschritt_nur_mit_fix(self):
        neu = self.raw.replace("Wechsle den Anbieter", "Prüfe den Anbieter", 1)
        inhalt, berichte, befund = self._teilfortschritt_datei(
            self.raw, neu, fix=True)
        self.assertEqual(neu, inhalt)
        self.assertTrue(berichte[0]["geschrieben"])
        self.assertTrue(berichte[0]["teilfortschritt"])
        self.assertEqual(0, befund)

    def test_verarbeite_trockenlauf_schreibt_keinen_teilfortschritt(self):
        neu = self.raw.replace("Wechsle den Anbieter", "Prüfe den Anbieter", 1)
        inhalt, berichte, befund = self._teilfortschritt_datei(
            self.raw, neu, fix=False)
        self.assertEqual(self.raw, inhalt)
        self.assertFalse(berichte[0]["geschrieben"])
        self.assertEqual(1, befund)

    def test_cli_reicht_nur_ganz_und_keine_ki_durch(self):
        with patch.object(sh, "_verarbeite", return_value=([], 0)) as verarbeite:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = sh.main(["--file", "kandidat/index.md", "--fix",
                                "--nur-ganz", "--keine-ki", "--json"])
        self.assertEqual(0, code)
        self.assertTrue(verarbeite.called)
        self.assertTrue(verarbeite.call_args.kwargs["nur_ganz"])
        self.assertFalse(verarbeite.call_args.kwargs["ki"])


if __name__ == "__main__":
    unittest.main()
