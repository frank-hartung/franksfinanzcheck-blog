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

        def spiegel(slug, timeout=10.0):
            """Spiegel-Abruf im Vertrag der Abrufschicht: (slug, timeout) -> (status, text)."""
            for suffix, inhalt in spiegel_dateien.items():
                if suffix.endswith(f"/{slug}.md"):
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

        # Spiegel ebenfalls offline → bleibt fail-closed UNKLAR
        erg_offline = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/vvg_2008/__40.html",
            abruf=runner_timeout,
            spiegel_abruf=lambda slug, timeout=10.0: (_ for _ in ()).throw(OSError("offline")),
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


class BelegkettenSpiegelTests(unittest.TestCase):
    """#1024 (04.11.2026): Der Messweg für Bundesrecht – dauerhaft geheilt.

    Der Vorfall war kein Netzproblem, sondern ein VERTRAGSBRUCH im Code:
    `sicherer_abruf()` liefert ein 3-Tupel, entpackt wurde ein 2-Tupel, und
    `except Exception:` verkaufte den `ValueError` als „Quelle unklar“.
    Vier gültige Gesetzeszitate standen dadurch dauerhaft als unprüfbar in
    der YMYL-Queue. Diese Klasse hält den Vertrag an allen vier Flanken fest.
    """

    VVG = (
        "---\n"
        "titel: Versicherungsvertragsgesetz\n"
        "quelle: https://www.gesetze-im-internet.de/vvg_2008/\n"
        "---\n\n"
        "### § 40 Kündigung bei Prämienerhöhung\n\n(1) Text.\n"
    )

    def test_sicherer_abruf_3_tupel_wird_korrekt_entpackt(self):
        """Der Kern von #1024: `(status, kopf, roh)` – nicht `(status, roh)`."""
        import net_safety

        gesehen = {}

        def attrappe(url, *, headers=None, timeout=20.0, max_bytes=0,
                     erlaube_loopback=False):
            gesehen["url"] = url
            gesehen["headers"] = headers or {}
            return 200, {"content-type": "text/markdown"}, self.VVG.encode("utf-8")

        with patch.object(net_safety, "sicherer_abruf", attrappe):
            status, inhalt = wache._spiegel_abruf(
                wache._gii_spiegel_url("vvg_2008"), timeout=5.0)

        self.assertEqual(200, status)
        # _spiegel_abruf gibt den ROHEN Inhalt zurück (Dekodieren ist Sache
        # der Abrufschicht) – die Prüfung ist deshalb auf Bytes formuliert.
        self.assertIn(b"quelle: https://www.gesetze-im-internet.de/vvg_2008/", inhalt)
        self.assertIn("vv/vvg_2008.md", gesehen["url"])
        self.assertIn("FranksFinanzcheck", gesehen["headers"].get("User-Agent", ""))

    def test_api_abruf_fragt_rohen_inhalt_und_version_an(self):
        import net_safety

        kopf = {}

        def attrappe(url, *, headers=None, timeout=20.0, max_bytes=0,
                     erlaube_loopback=False):
            kopf.update(headers or {})
            return 200, {}, self.VVG.encode("utf-8")

        with patch.object(net_safety, "sicherer_abruf", attrappe):
            wache._spiegel_abruf(wache._gii_spiegel_api_url("bgb"), timeout=5.0)

        self.assertEqual("application/vnd.github.raw", kopf.get("Accept"))
        self.assertEqual("2022-11-28", kopf.get("X-GitHub-Api-Version"))

    def test_token_geht_nur_an_die_api_und_nie_in_die_ausgabe(self):
        """`GH_TOKEN` ist ein Kontingent-Schlüssel, kein Quellenparameter."""
        import net_safety

        koepfe = []

        def attrappe(url, *, headers=None, timeout=20.0, max_bytes=0,
                     erlaube_loopback=False):
            koepfe.append((url, dict(headers or {})))
            return 200, {}, self.VVG.encode("utf-8")

        with patch.dict("os.environ", {"GH_TOKEN": "ghs_geheim_123"}), \
             patch.object(net_safety, "sicherer_abruf", attrappe):
            wache._spiegel_abruf(wache._gii_spiegel_url("vvg_2008"), timeout=5.0)
            wache._spiegel_abruf(wache._gii_spiegel_api_url("vvg_2008"), timeout=5.0)

        raw_url, raw_kopf = koepfe[0]
        api_url, api_kopf = koepfe[1]
        from url_host import ist_host_oder_subdomain

        self.assertTrue(ist_host_oder_subdomain(raw_url, "raw.githubusercontent.com"))
        self.assertNotIn("Authorization", raw_kopf, "Token darf nicht an raw gehen")
        self.assertTrue(ist_host_oder_subdomain(api_url, "api.github.com"))
        self.assertEqual("Bearer ghs_geheim_123", api_kopf.get("Authorization"))

    def test_spiegel_rueckfall_auf_die_api_bei_kontingentfehler(self):
        aufrufe = []
        from url_host import ist_host_oder_subdomain

        def abruf(url, timeout=10.0):
            aufrufe.append(url)
            # Host-Wahrheit statt Textsuche (Code-Scanning-Alert #83): Die
            # Zeichenkette „raw.githubusercontent.com“ darf an beliebiger
            # Stelle einer URL stehen und wäre keine Prüfung.
            if ist_host_oder_subdomain(url, "raw.githubusercontent.com"):
                raise wache.urllib.error.HTTPError(url, 429, "rate limited", None, None)
            return 200, self.VVG.encode("utf-8")

        status, inhalt = wache.abruf_gii_spiegel("vvg_2008", abruf=abruf)
        self.assertEqual(200, status)
        self.assertIn("gesetze-im-internet.de/vvg_2008/", inhalt)
        self.assertEqual(2, len(aufrufe), "genau ein Raw-Versuch, dann die API")
        self.assertTrue(ist_host_oder_subdomain(aufrufe[-1], "api.github.com"))
        self.assertIn("/vv/vvg_2008.md", aufrufe[-1])
        self.assertIn("ref=main", aufrufe[-1])

    def test_404_des_spiegels_ist_endgueltig_und_wird_nicht_wiederholt(self):
        aufrufe = []

        def abruf(url, timeout=10.0):
            aufrufe.append(url)
            raise wache.urllib.error.HTTPError(url, 404, "Not Found", None, None)

        status, _ = wache.abruf_gii_spiegel("aufgehoben_1999", abruf=abruf)
        self.assertEqual(404, status)
        self.assertEqual(1, len(aufrufe), "ein 404 darf nicht wiederholt werden")

    def test_403_wird_nicht_wiederholt_wohl_aber_503(self):
        zaehler = {"n": 0}

        def dauerhaft_403(url, timeout=10.0):
            zaehler["n"] += 1
            raise wache.urllib.error.HTTPError(url, 403, "Forbidden", None, None)

        status, _ = wache.abruf_gii_spiegel_http("https://x/y.md", 1.0,
                                                abruf=dauerhaft_403, versuche=3)
        self.assertEqual((403, 1), (status, zaehler["n"]))

        zaehler["n"] = 0

        def einmal_503(url, timeout=10.0):
            zaehler["n"] += 1
            if zaehler["n"] == 1:
                raise wache.urllib.error.HTTPError(url, 503, "Service Unavailable", None, None)
            return 200, b"---"

        status, roh = wache.abruf_gii_spiegel_http("https://x/y.md", 1.0,
                                                  abruf=einmal_503, versuche=3)
        self.assertEqual((200, 2), (status, zaehler["n"]))
        self.assertEqual(b"---", roh)

    def test_programmierfehler_ist_kein_quellenbefund(self):
        """#1024: Ein ValueError aus dem Tupel-Entpacken darf nicht „unklar“ werden."""
        def typfehler_direkt(url, timeout=10.0):
            raise ValueError("too many values to unpack (expected 2)")

        with self.assertRaises(ValueError):
            wache.pruefe_quelle("https://www.verbraucherzentrale.de/wissen/a-1",
                                abruf=typfehler_direkt)

        def typfehler_spiegel(slug, timeout=10.0):
            raise AttributeError("'NoneType' object has no attribute 'decode'")

        def netzfehler(url, timeout=10.0):
            raise wache.urllib.error.URLError("timed out")

        with self.assertRaises(AttributeError):
            wache.pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                                abruf=netzfehler, spiegel_abruf=typfehler_spiegel)

    def test_netzfehlerliste_ist_abgeschlossen_und_breit_genug(self):
        import http.client
        import ssl

        for klasse in (wache.urllib.error.URLError, wache.urllib.error.HTTPError,
                       http.client.HTTPException, TimeoutError, ConnectionResetError,
                       ssl.SSLError):
            with self.subTest(klasse=klasse.__name__):
                self.assertTrue(issubclass(klasse, wache.NETZ_AUSNAHMEN))
        # Ein Programmierfehler gehört ausdrücklich NICHT dazu.
        for klasse in (ValueError, TypeError, AttributeError, KeyError, NameError):
            with self.subTest(klasse=klasse.__name__):
                self.assertFalse(issubclass(klasse, wache.NETZ_AUSNAHMEN))

    def test_ablageordnung_des_spiegels_ist_eine_stelle(self):
        self.assertEqual("vv", wache._gii_shard("vvg_2008"))
        self.assertEqual("bg", wache._gii_shard("bgb"))
        self.assertEqual("go", wache._gii_shard("got_2022"))
        self.assertEqual("es", wache._gii_shard("estg"))
        self.assertEqual("0-9", wache._gii_shard("1wofg"))
        self.assertTrue(wache._gii_spiegel_url("bgb").endswith("/bg/bgb.md"))

    def test_echter_spiegelfall_aus_dem_vorfall_1024(self):
        """Alle vier Zitate aus #1024 müssen über den Spiegel belegbar sein."""
        dateien = {
            "vvg_2008": self.VVG,
            "bgb": ("---\nquelle: https://www.gesetze-im-internet.de/bgb/\n---\n\n"
                    "###### § 502 Vorfälligkeitsentschädigung\n"),
            "got_2022": ("---\nquelle: https://www.gesetze-im-internet.de/got_2022/\n---\n\n"
                         "# Gebührenordnung für Tierärztinnen und Tierärzte (GOT)\n"),
        }

        def spiegel(slug, timeout=10.0):
            return (200, dateien[slug]) if slug in dateien else (404, "")

        def netzfehler(url, timeout=10.0):
            raise wache.urllib.error.URLError("<urlopen error [SSL: KRB5_S_TKT_EXPIRED]>")

        for zitat in ("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                      "https://www.gesetze-im-internet.de/bgb/__502.html",
                      "https://www.gesetze-im-internet.de/got_2022/"):
            with self.subTest(zitat=zitat):
                ergebnis = wache.pruefe_quelle(zitat, abruf=netzfehler, spiegel_abruf=spiegel)
                self.assertEqual(wache.OK, ergebnis["status"], ergebnis)
                self.assertIn("Bundesrechts-Spiegel", ergebnis["hinweis"])

    def test_probe_bundesrecht_ist_ein_live_nachweis_und_kein_gate(self):
        """`--probe-bundesrecht` meldet Erfolg/Misserfolg, ohne das Gate zu ändern."""
        def spiegel(slug, timeout=10.0):
            return (200, self.VVG) if slug == "vvg_2008" else (404, "")

        original = wache.abruf_gii_spiegel
        wache.abruf_gii_spiegel = lambda slug, timeout=15.0, **_: spiegel(slug)
        try:
            ausgabe = io.StringIO()
            with redirect_stdout(ausgabe):
                code_ok = wache.probe_bundesrecht(
                    ["https://www.gesetze-im-internet.de/vvg_2008/__40.html"])
                self.assertEqual(0, code_ok, ausgabe.getvalue())
                self.assertIn("aktiv", ausgabe.getvalue())

            ausgabe = io.StringIO()
            with redirect_stdout(ausgabe):
                code_fehler = wache.probe_bundesrecht(
                    ["https://www.gesetze-im-internet.de/bgb/__502.html"])
            self.assertEqual(1, code_fehler)
            self.assertIn("404", ausgabe.getvalue())
        finally:
            wache.abruf_gii_spiegel = original


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
