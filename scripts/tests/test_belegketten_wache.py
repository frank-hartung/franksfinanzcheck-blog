"""Prüfqueue #826: Belegketten-Wache und Faktenfrische-Schreibgrenze.

Beide Tests laufen ohne Netz: Die Wache bekommt einen injizierten Abruf,
Faktenfrische arbeitet auf temporären Artikeln. Der Punkt ist nicht die
Netzwerkfunktion, sondern die Entscheidung: Was gilt als Befund, und was darf
ein Wartungslauf an einem versiegelten YMYL-Artikel ändern?
"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import belegketten_wache as wache
import faktenfrische
import yaml

ARTIKEL = """---
title: "{titel}"
description: "Beschreibung"
author: "Frank Hartung"
{extra}quellen:
  - id: "Q1"
    titel: "Quelle"
    url: "https://www.verbraucherzentrale.de/wissen/a-1"
    herausgeber: "Verbraucherzentrale"
    datum: "2026-10-01"
---

Ein Text mit 20 Euro und einer Aussage.
"""


def artikel_text(*, titel="Kreditvergleich", quarantäne="", extra=""):
    return ARTIKEL.format(titel=titel, extra=extra)


class BelegkettenWacheTests(unittest.TestCase):
    def test_status_kette(self):
        ziel = "https://www.verbraucherzentrale.de/wissen/alt-1"

        def ok(url, timeout=10.0):
            return 200, url

        def umzug(url, timeout=10.0):
            return 200, "https://www.verbraucherzentrale.de/wissen/neu-1"

        def netz(url, timeout=10.0):
            raise OSError("kein Netz")

        self.assertEqual(wache.OK, wache.pruefe_quelle(ziel, abruf=ok)["status"])
        self.assertEqual(wache.UMGELEITET, wache.pruefe_quelle(ziel, abruf=umzug)["status"])
        self.assertEqual(wache.UNKLAR, wache.pruefe_quelle(ziel, abruf=netz)["status"])

    def test_sprachpfad_ist_kein_inhaltswechsel(self):
        """#826: `/` → `/de` belegt weiterhin dieselbe Seite."""
        def abruf(url, timeout=10.0):
            return 200, "https://kontenvergleich.bafin.de/de"

        ergebnis = wache.pruefe_quelle("https://kontenvergleich.bafin.de/", abruf=abruf)
        self.assertEqual(wache.OK, ergebnis["status"])
        self.assertIn("Sprachpfad", ergebnis["hinweis"])

    def test_echter_umzug_bleibt_pruefauftrag(self):
        for ziel in ("https://kontenvergleich.bafin.de/de/andere-seite",
                     "https://www.bafin.de/de",
                     "https://kontenvergleich.bafin.de/de?x=1"):
            with self.subTest(ziel=ziel):
                ergebnis = wache.pruefe_quelle(
                    "https://kontenvergleich.bafin.de/",
                    abruf=lambda u, timeout=10.0: (200, ziel))
                self.assertEqual(wache.UMGELEITET, ergebnis["status"], ziel)

    def test_nicht_https_ist_tot(self):
        ergebnis = wache.pruefe_quelle("http://example.org/x", abruf=lambda u, timeout=10.0: (200, u))
        self.assertEqual(wache.TOT, ergebnis["status"])

    def test_netzfehler_blockiert_nicht(self):
        """Eine Wache, die bei jedem Wackler rot wird, wird abgeschaltet."""
        ergebnis = wache.pruefe_alle(abruf=lambda u, timeout=10.0: (_ for _ in ()).throw(OSError("x")))
        self.assertEqual([], ergebnis["blockierend"])
        self.assertGreater(ergebnis["zaehler"][wache.UNKLAR], 0)

    def test_lesefehler_blockiert_statt_zu_verschwinden(self):
        artikel = {"slug": "kaputt", "path": "content/posts/kaputt/index.md",
                   "risk": "unbekannt", "quellen": [], "lesefehler": "YAML defekt"}
        with patch.object(wache, "belegketten", return_value=[artikel]):
            ergebnis = wache.pruefe_alle(nur_hochrisiko=True)
        self.assertEqual(1, len(ergebnis["blockierend"]))
        self.assertEqual("YAML defekt", ergebnis["befunde"][0]["befund"])

    def test_url_wird_einmal_abgerufen_zuordnung_bleibt_erhalten(self):
        artikel = [{"slug": slug, "risk": "hoch", "approved": True,
                    "quellen": [{"id": "Q1", "titel": "Beleg", "url": "https://example.org/a"}]}
                   for slug in ("eins", "zwei")]
        with patch.object(wache, "belegketten", return_value=artikel), patch.object(
                wache, "abruf_http", return_value=(404, "https://example.org/a")) as abruf:
            ergebnis = wache.pruefe_alle()
        self.assertEqual(1, abruf.call_count)
        self.assertEqual(["eins", "zwei"], [e["slug"] for e in ergebnis["befunde"]])

    def test_http_status_konsistent_mit_und_ohne_exception(self):
        for code in (403, 429, 500, 501, 503, 507, 404, 410):
            erwartet = wache.TOT if code in (404, 410) else wache.UNKLAR
            def fehler(url, timeout=10.0):
                raise wache.urllib.error.HTTPError(url, code, "Fehler", None, None)
            for abruf in (fehler, lambda url, timeout: (code, url)):
                with self.subTest(code=code, abruf=abruf):
                    self.assertEqual(erwartet, wache.pruefe_quelle(
                        "https://example.org/a", abruf=abruf)["status"])

    def test_queue_erledigung_erfordert_vollstaendigen_abruf(self):
        for status in (wache.UNKLAR, wache.UMGELEITET):
            ergebnis = {"geprueft": 1, "zaehler": dict.fromkeys(
                (wache.OK, wache.TOT, wache.UNKLAR, wache.UMGELEITET), 0),
                "befunde": [{"status": status}], "blockierend": []}
            ergebnis["zaehler"][status] = 1
            with patch.object(wache, "pruefe_alle", return_value=ergebnis), redirect_stdout(io.StringIO()):
                self.assertEqual(0, wache.main(["--strict", "--json"]))
                self.assertEqual(1, wache.main(["--strict", "--require-complete", "--json"]))

    def test_selbsttest(self):
        self.assertEqual([], wache.selftest())

    def test_strict_nur_bei_toter_quelle(self):
        def tot(url, timeout=10.0):
            raise wache.urllib.error.HTTPError(url, 404, "Not Found", None, None)

        original = wache.pruefe_alle
        wache.pruefe_alle = lambda **kwargs: {
            "geprueft": 1, "zaehler": {wache.OK: 0, wache.UMGELEITET: 0, wache.TOT: 1, wache.UNKLAR: 0},
            "befunde": [{"status": wache.TOT, "slug": "x", "id": "Q1",
                          "befund": "HTTP 404", "zitat": "https://a", "end_url": "", "risk": "hoch"}],
            "blockierend": [{"status": wache.TOT, "slug": "x", "id": "Q1",
                              "befund": "HTTP 404", "zitat": "https://a", "end_url": "", "risk": "hoch"}],
        }
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(1, wache.main(["--strict"]))
                self.assertEqual(0, wache.main([]))
        finally:
            wache.pruefe_alle = original


class FaktenfrischeSchreibgrenzeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self.tmp.name) / "posts" / "2026-10-01-kredit" / "index.md"
        self.pfad.parent.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _schreibe(self, text):
        self.pfad.write_text(text, encoding="utf-8")
        return faktenfrische.lade_artikel(str(self.pfad))

    def _quellen(self):
        return [{"titel": "Signal", "url": "https://www.destatis.de/x",
                 "herausgeber": "Statistisches Bundesamt", "datum": ""}]

    def test_hochrisiko_bekommt_keine_recherche_quellen(self):
        """Ein Signal ist keine Belegkette (Fund 15.10.2026)."""
        art = self._schreibe(artikel_text(
            extra="redaktionelle_pruefung:\n  risikoklasse: \"hoch\"\n  status: \"ausstehend\"\n"))
        ergebnis = faktenfrische.artikel_anwenden(art, self._quellen(), "2026-10-24", trocken=False)
        self.assertTrue(any("Belegkette bleibt redaktionell" in z for z in ergebnis), ergebnis)
        roh = self.pfad.read_text(encoding="utf-8")
        self.assertNotIn("destatis.de", roh)

    def test_versiegelter_artikel_bleibt_unangetastet(self):
        """Eine Wartung darf kein Siegel brechen, ohne dass jemand prüft."""
        from editorial_review_gate import content_fingerprint, split_article

        text = artikel_text(extra="redaktionelle_pruefung:\n  risikoklasse: \"hoch\"\n"
                                  "  status: \"freigegeben\"\n")
        fm_text, body = split_article(text)
        fm = yaml.safe_load(fm_text)
        fm["redaktionelle_pruefung"]["inhalt_sha256"] = content_fingerprint(fm, body)
        versiegelt = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
        art = self._schreibe(versiegelt)
        ergebnis = faktenfrische.artikel_anwenden(art, self._quellen(), "2026-10-24", trocken=False)
        self.assertTrue(any(z.startswith("ABGEBROCHEN") for z in ergebnis), ergebnis)
        self.assertEqual(versiegelt, self.pfad.read_text(encoding="utf-8"))

    def test_auto_bahn_bekommt_quellen(self):
        art = self._schreibe(artikel_text(titel="DSL-Anschluss finden"))
        ergebnis = faktenfrische.artikel_anwenden(art, self._quellen(), "2026-10-24", trocken=False)
        self.assertTrue(any(z.startswith("quellen:") for z in ergebnis), ergebnis)
        self.assertIn("destatis.de", self.pfad.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
