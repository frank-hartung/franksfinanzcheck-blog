#!/usr/bin/env python3
"""Vertragstests: scripts/geo_protokoll.py (GEO-Protokoll, 08.10.2026).

Festgehalten wird:
  1. Die 10 festen Fragen und 3 Engines sind eingefroren (Vergleich über Monate).
  2. Perplexity ist nicht dabei (CLAUDE.md, Abschnitt Werkbank).
  3. Nur https-URLs auf franksfinanzcheck.de gelten als Quelle (keine Fremd-Domains,
     keine Userinfo-Tricks).
  4. Eine Datei wird nie überschrieben.
  5. Die Auswertung läuft nur auf geprüften Dateien.
  6. Die vorhandenen Dateien im Repo sind gültig.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "geo_protokoll.py"


def _load():
    spec = importlib.util.spec_from_file_location("geo_protokoll", SKRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gp = _load()


class Festlegungen(unittest.TestCase):
    def test_zehn_feste_fragen_mit_fortlaufenden_ids(self):
        self.assertEqual(len(gp.FRAGEN), 10)
        self.assertEqual([fid for fid, _ in gp.FRAGEN], [f"F{i:02d}" for i in range(1, 11)])

    def test_drei_engines_ohne_perplexity(self):
        self.assertEqual(gp.ENGINES, ("chatgpt-free", "gemini-free", "google-ki-uebersicht"))
        self.assertFalse(any("perplexity" in e for e in gp.ENGINES))

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(gp.selbsttest(), [])

    def test_leere_datei_hat_30_zeilen(self):
        self.assertEqual(len(gp.leere_zeilen("2026-10")), 30)


class Quelle(unittest.TestCase):
    def test_eigene_domain_mit_https_ist_gueltig(self):
        self.assertTrue(gp.url_ist_eigene_seite("https://franksfinanzcheck.de/konto/"))
        self.assertTrue(gp.url_ist_eigene_seite("https://www.franksfinanzcheck.de/"))

    def test_fremde_und_getarnte_domains_sind_ungueltig(self):
        for url in (
            "http://franksfinanzcheck.de/",
            "https://franksfinanzcheck.de.evil.example/",
            "https://franksfinanzcheck.de@evil.example/",
            "https://example.com/franksfinanzcheck.de",
            "javascript:alert(1)",
        ):
            self.assertFalse(gp.url_ist_eigene_seite(url), url)


class Pruefung(unittest.TestCase):
    def setUp(self):
        self.basis = gp.leere_zeilen("2026-10")

    def _mit(self, index, **kw):
        z = [dict(x) for x in self.basis]
        z[index].update(kw)
        return z

    def test_leere_zeilen_sind_offen_nicht_fehlerhaft(self):
        self.assertEqual(gp.pruefe(self.basis, "2026-10"), [])

    def test_datum_muss_im_monat_liegen(self):
        self.assertTrue(gp.pruefe(self._mit(0, datum="2026-09-30", genannt="nein", zitiert="nein"), "2026-10"))

    def test_zitiert_braucht_genannt_und_url(self):
        self.assertTrue(gp.pruefe(self._mit(0, datum="2026-10-02", genannt="nein", zitiert="ja",
                                            quelle_url="https://franksfinanzcheck.de/"), "2026-10"))
        self.assertTrue(gp.pruefe(self._mit(0, datum="2026-10-02", genannt="ja", position="1", zitiert="ja"), "2026-10"))

    def test_veraenderter_fragetext_faellt_auf(self):
        self.assertTrue(gp.pruefe(self._mit(0, frage="Andere Frage?"), "2026-10"))

    def test_doppelte_und_fehlende_zeilen(self):
        z = [dict(x) for x in self.basis]
        z.append(dict(self.basis[0]))
        self.assertTrue(any("doppelt" in f for f in gp.pruefe(z, "2026-10")))
        self.assertTrue(any("fehlt" in f for f in gp.pruefe(self.basis[1:], "2026-10")))

    def test_notiz_ohne_email(self):
        self.assertTrue(gp.pruefe(self._mit(2, datum="2026-10-02", genannt="nein", zitiert="nein",
                                            notiz="kontakt@example.de"), "2026-10"))


class Datei(unittest.TestCase):
    def test_neu_ueberschreibt_nie(self):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            original = gp.ORDNER
            gp.ORDNER = ordner
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(gp.main(["--neu", "2026-11"]), 0)
                    self.assertEqual(gp.main(["--neu", "2026-11"]), 1)
                self.assertEqual(len(gp.lese_csv(ordner / "protokoll-2026-11.csv")[0]), 30)
            finally:
                gp.ORDNER = original

    def test_auswertung_verweigert_fehlerhafte_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "protokoll-2026-10.csv"
            zeilen = gp.leere_zeilen("2026-10")
            zeilen[0].update(datum="2026-10-02", genannt="ja", position="", zitiert="nein")
            gp.schreibe_csv(pfad, zeilen)
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                code = gp.main(["--auswerten", "--datei", str(pfad)])
            self.assertEqual(code, 1)
            self.assertIn("Auswertung nur für geprüfte Dateien", puffer.getvalue())

    def test_monatsname_ist_pflicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "irgendwas.csv"
            gp.schreibe_csv(pfad, gp.leere_zeilen("2026-10"))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gp.main(["--datei", str(pfad)]), 1)

    def test_vorhandene_dateien_im_repo_sind_gueltig(self):
        for pfad in sorted((ROOT / "data" / "geo").glob("protokoll-*.csv")):
            monat = gp.monat_aus_datei(pfad)
            self.assertIsNotNone(monat, pfad.name)
            zeilen, fehler = gp.lese_csv(pfad)
            self.assertEqual(fehler, [], pfad.name)
            self.assertEqual(gp.pruefe(zeilen, monat), [], pfad.name)


class Doku(unittest.TestCase):
    def test_runbook_existiert_und_nennt_die_regeln(self):
        text = (ROOT / "docs" / "ANLEITUNG-GEO-PROTOKOLL.md").read_text(encoding="utf-8")
        for stichwort in ("manuell", "Perplexity", "franksfinanzcheck.de", "--pruefen", "--auswerten"):
            self.assertIn(stichwort, text)

    def test_redaktionsprotokoll_bleibt_mit_der_anleitung_verwaehlt(self):
        """#644 brachte das GEO-Redaktionsprotokoll, niemand verlinkte es (Befund 11)."""
        standard = ROOT / "docs" / "GEO-REDAKTIONSPROTOKOLL.md"
        self.assertTrue(standard.exists(), "GEO-Redaktionsprotokoll fehlt")
        anleitung = (ROOT / "docs" / "ANLEITUNG-GEO-PROTOKOLL.md").read_text(encoding="utf-8")
        self.assertIn("GEO-REDAKTIONSPROTOKOLL.md", anleitung,
                      "verwaistes Protokoll: die Anleitung nennt es nicht mehr")


if __name__ == "__main__":
    unittest.main()
