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
import net_safety
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

    def test_gii_spiegel_normpruefung_heilt_runner_blockade_fail_closed(self):
        """#826: GII blockt Runner-IPs; Spiegel bestätigt aktive Normen, entlarvt Wegfall."""
        spiegel_dateien = {
            "/vv/vvg_2008.md": (
                "---\nquelle: https://www.gesetze-im-internet.de/vvg_2008/\n---\n\n"
                "### § 40 Kündigung bei Prämienerhöhung\n\n(1) Text.\n\n"
                "### § 40a Sonderregel\n\nText.\n\n"
                "### § 41 (weggefallen)\n"
            ),
            "/bg/bgb.md": (
                "---\nquelle: https://www.gesetze-im-internet.de/bgb/\n---\n\n"
                "### § 502 Vorfälligkeitsentschädigung\n\n(1) Text.\n"
            ),
            "/go/got_2022.md": (
                "---\nquelle: https://www.gesetze-im-internet.de/got_2022/\n---\n\n"
                "### § 2 Gebührenhöhe\n\n### § 4 Gebühren für tierärztlichen Notdienst\n"
            ),
            "/fa/falsch.md": (
                "---\nquelle: https://boese-gesetze-im-internet.de/falsch/\n---\n\n"
                "### § 1 Text\n"
            ),
        }

        def runner_timeout(url, timeout=10.0):
            raise wache.urllib.error.URLError("timed out")

        def spiegel(url, timeout=10.0):
            for suffix, inhalt in spiegel_dateien.items():
                if url.endswith(suffix):
                    return 200, inhalt
            return 404, ""

        for zitat in (
            "https://www.gesetze-im-internet.de/vvg_2008/__40.html",
            "https://www.gesetze-im-internet.de/bgb/__502.html",
            "https://www.gesetze-im-internet.de/got_2022/",
        ):
            with self.subTest(zitat=zitat):
                erg = wache.pruefe_quelle(zitat, abruf=runner_timeout, spiegel_abruf=spiegel)
                self.assertEqual(wache.OK, erg["status"], erg)
                self.assertIn("Bundesrechts-Spiegel", erg["hinweis"])

        # § 4 darf NICHT auf § 40 oder § 40a matchen!
        erg_fehlt = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/vvg_2008/__4.html",
            abruf=runner_timeout, spiegel_abruf=spiegel,
        )
        self.assertEqual(wache.TOT, erg_fehlt["status"])

        # Weggefallener Paragraph → TOT
        erg_weg = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/vvg_2008/__41.html",
            abruf=runner_timeout, spiegel_abruf=spiegel,
        )
        self.assertEqual(wache.TOT, erg_weg["status"])
        self.assertIn("weggefallen", erg_weg["befund"])

        # Aufgehobenes Gesetz (404 im Spiegel) → TOT
        erg_alt = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/aufgehoben_1999/__1.html",
            abruf=runner_timeout, spiegel_abruf=spiegel,
        )
        self.assertEqual(wache.TOT, erg_alt["status"])

        # Gefälschter quelle:-Kopf → bleibt fail-closed UNKLAR
        erg_spoof = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/falsch/__1.html",
            abruf=runner_timeout, spiegel_abruf=spiegel,
        )
        self.assertEqual(wache.UNKLAR, erg_spoof["status"])
        self.assertTrue(erg_spoof["spiegel_url"].endswith("/fa/falsch.md"), erg_spoof)
        self.assertIn("Herkunft nicht", erg_spoof["hinweis"])

        # Spiegel ebenfalls offline → bleibt fail-closed UNKLAR
        erg_offline = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/vvg_2008/__40.html",
            abruf=runner_timeout,
            spiegel_abruf=lambda u, timeout=10.0: (_ for _ in ()).throw(OSError("offline")),
        )
        self.assertEqual(wache.UNKLAR, erg_offline["status"])

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


class Transportvertrag1024Tests(unittest.TestCase):
    """#1024: Der ECHTE Spiegel-Adapter gegen den ECHTEN net_safety-Transport.

    Die bestehenden Tests injizieren ``spiegel_abruf`` als 2-Tupel. Damit
    prüfen sie die Normlogik, aber nicht die Verbindung dorthin. Genau in
    dieser Lücke stand vier Tage lang ein ``ValueError: too many values to
    unpack``: grüne Tests, rotes Ticket. Diese Klasse schließt die Lücke,
    vollständig offline (kein Host wird wirklich aufgerufen).
    """

    # Kopf und Überschriftenebenen entsprechen den echten Spiegeldateien
    # (vvg_2008.md: ``#####``, bgb.md: ``######``, Stand 03.11.2026).
    VVG_MD = (
        "---\n"
        "abkuerzung: VVG\n"
        "titel: Gesetz über den Versicherungsvertrag\n"
        "quelle: https://www.gesetze-im-internet.de/vvg_2008/\n"
        "builddate: '20260630215604'\n"
        "---\n\n"
        "# Gesetz über den Versicherungsvertrag (VVG)\n\n"
        "##### § 40 Kündigung bei Prämienerhöhung\n\n(1) Text.\n\n"
        "##### § 96 Kündigung nach Veräußerung\n\n(1) Text.\n\n"
        "##### § 41 (weggefallen)\n"
    )
    BGB_MD = (
        "---\n"
        "quelle: https://www.gesetze-im-internet.de/bgb/\n"
        "---\n\n"
        "##### § 501 Vorzeitige Rückzahlung\n\n"
        "###### § 502 Vorfälligkeitsentschädigung\n\n(1) Text.\n"
    )
    GII_40 = "https://www.gesetze-im-internet.de/vvg_2008/__40.html"
    GII_502 = "https://www.gesetze-im-internet.de/bgb/__502.html"

    def _transport(self, text):
        return 200, {"Content-Type": "text/markdown; charset=utf-8"}, text.encode("utf-8")

    @staticmethod
    def _blockiert(url, timeout=10.0):
        raise wache.urllib.error.URLError("timed out (GII-Runner-Filter)")

    def test_net_safety_sicherer_abruf_liefert_drei_werte(self):
        """Gegenprobe: der Transport, den der Adapter zu entpacken hat."""
        class Antwort:
            status = 200
            headers = {"Content-Type": "text/markdown"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, anzahl):
                return b"norm"

            def geturl(self):
                return "https://raw.githubusercontent.com/beispiel.md"

        with patch.object(net_safety.urllib.request, "urlopen", return_value=Antwort()):
            ergebnis = net_safety.sicherer_abruf(
                "https://raw.githubusercontent.com/beispiel.md")
        self.assertEqual(3, len(ergebnis), ergebnis)
        self.assertEqual(b"norm", ergebnis[2])

    def test_adapter_entpackt_dreiteiligen_transport(self):
        """Der Regressionstest für #1024: 2er-Unpack würde hier werfen."""
        with patch.object(net_safety, "sicherer_abruf",
                          return_value=self._transport(self.VVG_MD)) as transport:
            status, text = wache.abruf_gii_spiegel_http(
                wache._gii_spiegel_url("vvg_2008"))
        self.assertEqual(200, status)
        self.assertIn("§ 40", text)
        self.assertTrue(transport.called)

    def test_echter_adapter_heilt_runner_blockade_mit_herkunft(self):
        with patch.object(net_safety, "sicherer_abruf",
                          return_value=self._transport(self.VVG_MD)):
            erg = wache.pruefe_quelle(
                self.GII_40, abruf=self._blockiert,
                spiegel_abruf=wache.abruf_gii_spiegel_http)
        self.assertEqual(wache.OK, erg["status"], erg)
        self.assertEqual(wache.PFAD_SPIEGEL, erg["pruefpfad"])
        self.assertTrue(erg["spiegel_url"].endswith("/vv/vvg_2008.md"), erg)
        self.assertIn("Bundesrechts-Spiegel", erg["hinweis"])

    def test_bgb_heading_level_und_einzelnormschaerfe(self):
        def transport(url, **kwargs):
            return self._transport(self.BGB_MD)

        with patch.object(net_safety, "sicherer_abruf", side_effect=transport):
            ok = wache.pruefe_quelle(
                self.GII_502, abruf=self._blockiert,
                spiegel_abruf=wache.abruf_gii_spiegel_http)
            fehlt = wache.pruefe_quelle(
                "https://www.gesetze-im-internet.de/bgb/__503.html",
                abruf=self._blockiert,
                spiegel_abruf=wache.abruf_gii_spiegel_http)
        self.assertEqual(wache.OK, ok["status"], ok)
        self.assertEqual(wache.TOT, fehlt["status"], fehlt)
        self.assertIn("vor jeder Textänderung", fehlt["hinweis"])

    def test_transportausfall_bleibt_fail_closed_und_begruendet(self):
        with patch.object(net_safety, "sicherer_abruf",
                          side_effect=wache.urllib.error.URLError("offline")):
            erg = wache.pruefe_quelle(
                self.GII_40, abruf=self._blockiert,
                spiegel_abruf=wache.abruf_gii_spiegel_http)
        self.assertEqual(wache.UNKLAR, erg["status"], erg)
        self.assertEqual(wache.PFAD_UNKLAR, erg["pruefpfad"])
        self.assertIn("Spiegel", erg["hinweis"])
        self.assertTrue(erg["spiegel_url"].endswith("/vv/vvg_2008.md"), erg)
        # Der Bericht muss auch den fehlgeschlagenen Ersatzweg lokalisieren.
        # ``pruefe_alle`` ergänzt slug/id erst bei der Artikel-Zuordnung.
        zeile = wache._zeile({**erg, "slug": "kfz", "id": "Q3"})
        self.assertIn("URLError", zeile)
        self.assertIn("/vv/vvg_2008.md", zeile)

    def test_direktes_404_wird_nicht_ueberstimmt(self):
        def tot(url, timeout=10.0):
            raise wache.urllib.error.HTTPError(url, 404, "Not Found", None, None)

        with patch.object(net_safety, "sicherer_abruf",
                          return_value=self._transport(self.VVG_MD)):
            erg = wache.pruefe_quelle(
                self.GII_40, abruf=tot,
                spiegel_abruf=wache.abruf_gii_spiegel_http)
        self.assertEqual(wache.TOT, erg["status"], erg)
        self.assertNotEqual(wache.PFAD_SPIEGEL, erg["pruefpfad"])

    def test_produktionsweg_ist_gruen_und_zaehlt_ersatzpruefungen(self):
        """Ohne Injektion: echter Direkt- UND echter Spiegel-Adapter, offline."""
        artikel = [
            {"slug": slug, "risk": "hoch", "approved": True,
             "quellen": [{"id": "Q3", "titel": "§ 40 VVG", "url": self.GII_40}]}
            for slug in ("kfz", "versicherungsupdate")
        ]
        with patch.object(wache, "belegketten", return_value=artikel), patch.object(
                wache, "abruf_http", side_effect=self._blockiert), patch.object(
                net_safety, "sicherer_abruf",
                return_value=self._transport(self.VVG_MD)):
            ergebnis = wache.pruefe_alle(nur_hochrisiko=True)
            with redirect_stdout(io.StringIO()):
                code = wache.main(["--nur-hochrisiko", "--strict", "--require-complete"])
        self.assertEqual(2, ergebnis["geprueft"])
        self.assertEqual(2, ergebnis["zaehler"][wache.OK])
        self.assertEqual([], ergebnis["befunde"])
        self.assertEqual([], ergebnis["blockierend"])
        self.assertEqual(2, len(ergebnis["spiegel_bestaetigt"]))
        self.assertEqual(
            ["kfz", "versicherungsupdate"],
            [e["slug"] for e in ergebnis["spiegel_bestaetigt"]])
        self.assertEqual(0, code)

    def test_report_nennt_ersatzpruefung_statt_falschem_freispruch(self):
        erg = {
            "geprueft": 1,
            "zaehler": {wache.OK: 1, wache.TOT: 0, wache.UNKLAR: 0, wache.UMGELEITET: 0},
            "befunde": [], "blockierend": [],
            "spiegel_bestaetigt": [{
                "slug": "kfz", "id": "Q3", "zitat": self.GII_40,
                "spiegel_url": wache._gii_spiegel_url("vvg_2008"),
                "hinweis": "aktiver Normbestand über täglichen Bundesrechts-Spiegel bestätigt",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "BELEGKETTEN-WACHE-REPORT.md"
            with patch.object(wache, "REPORT", ziel):
                wache.report_schreiben(erg)
            text = ziel.read_text(encoding="utf-8")
        self.assertIn("Über Bundesrechts-Spiegel bestätigt: **1**", text)
        self.assertIn("Unverändert direkt erreichbar: **0**", text)
        self.assertIn("## Ersatzprüfung über den Bundesrechts-Spiegel", text)
        self.assertIn("/vv/vvg_2008.md", text)
        self.assertIn("keine fachliche Freigabe", text)
        self.assertNotIn("alle Belegketten unverändert erreichbar", text)
        self.assertNotIn("Unverändert erreichbar: **1**", text)


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
