"""Prüfqueue #826 & #1024: Belegketten-Wache, Workflow-Vertrag und Faktenfrische-Schreibgrenze.

Alle Tests laufen ohne Netz: Die Wache bekommt einen injizierten Abruf bzw.
gepatchtes ``urllib.request.urlopen`` (damit der echte 3-Tupel-Vertrag mit
``net_safety.sicherer_abruf`` geprüft wird!), und die Shell-Blöcke aus
``.github/workflows/redaktionelle-ymyl-pruefung.yml`` werden unter
``bash -eo pipefail`` ausgeführt.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
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
        for code in (403, 408, 429, 500, 501, 503, 507, 404, 410):
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

        # Spiegel ebenfalls offline → bleibt fail-closed UNKLAR
        erg_offline = wache.pruefe_quelle(
            "https://www.gesetze-im-internet.de/vvg_2008/__40.html",
            abruf=runner_timeout,
            spiegel_abruf=lambda u, timeout=10.0: (_ for _ in ()).throw(OSError("offline")),
        )
        self.assertEqual(wache.UNKLAR, erg_offline["status"])

    def test_1024_echter_sicherer_abruf_3_tupel_vertrag_und_api_fallback(self):
        """#1024: Prüft den echten Produktionspfad abruf_gii_spiegel_http -> net_safety.sicherer_abruf."""
        bgb_md = (
            "---\nquelle: https://www.gesetze-im-internet.de/bgb/\n---\n\n"
            "###### § 502 Vorfälligkeitsentschädigung\n\n(1) Der Darlehensgeber ...\n"
        ).encode("utf-8")
        gesehene_anfragen: list[tuple[str, dict]] = []

        def fake_urlopen(req, timeout=10.0):
            ziel_url = req.full_url
            kopf = {k.lower(): v for k, v in req.header_items()}
            gesehene_anfragen.append((ziel_url, kopf))
            if "gesetze-im-internet.de" in ziel_url:
                raise wache.urllib.error.URLError("Runner TCP Timeout")
            if "raw.githubusercontent.com" in ziel_url:
                raise wache.urllib.error.HTTPError(ziel_url, 429, "Too Many Requests", None, None)
            if "api.github.com/repos/Gesetze-fuer-KI/bundesrecht/contents/bg/bgb.md" in ziel_url:
                return wache._OfflineAntwort(200, bgb_md, ziel_url)
            raise wache.urllib.error.HTTPError(ziel_url, 404, "Not Found", None, None)

        with patch.dict(os.environ, {"GH_TOKEN": "test-gh-token-1024"}, clear=False), \
             patch("urllib.request.urlopen", side_effect=fake_urlopen):
            erg = wache.pruefe_quelle("https://www.gesetze-im-internet.de/bgb/__502.html")

        self.assertEqual(wache.OK, erg["status"], erg)
        self.assertEqual(3, len(gesehene_anfragen))
        # Token darf ausschließlich an api.github.com gesendet werden – nie an GII oder raw!
        self.assertNotIn("authorization", gesehene_anfragen[0][1])
        self.assertNotIn("authorization", gesehene_anfragen[1][1])
        self.assertEqual("Bearer test-gh-token-1024", gesehene_anfragen[2][1].get("authorization"))
        self.assertEqual("application/vnd.github.raw", gesehene_anfragen[2][1].get("accept"))

    def test_1024_programmierfehler_wird_nicht_als_unklar_geschluckt(self):
        """#1024: ValueError/TypeError muss krachen, statt sich als URLError zu tarnen."""
        with self.assertRaises(ValueError):
            wache.pruefe_quelle(
                "https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                abruf=lambda u, timeout=10.0: (_ for _ in ()).throw(wache.urllib.error.URLError("block")),
                spiegel_abruf=lambda u, timeout=10.0: (_ for _ in ()).throw(ValueError("too many values")),
            )
        with self.assertRaises(TypeError):
            wache.pruefe_quelle(
                "https://www.verbraucherzentrale.de/wissen/a-1",
                abruf=lambda u, timeout=10.0: (_ for _ in ()).throw(TypeError("falscher Typ")),
            )

    def test_abruf_http_wiederholt_transiente_stoerung_einmal_aber_nicht_gii_oder_404(self):
        pausen: list[float] = []
        with patch("net_safety.sicherer_abruf_status", side_effect=[
            wache.urllib.error.URLError("kurzer Wackler"),
            (200, "https://www.verbraucherzentrale.de/wissen/a-1"),
        ]) as mock_status:
            code, end_url = wache.abruf_http(
                "https://www.verbraucherzentrale.de/wissen/a-1", schlaf=pausen.append
            )
        self.assertEqual(200, code)
        self.assertEqual(2, mock_status.call_count)
        self.assertEqual([1.5], pausen)

        # GII-Direktabruf versucht es genau 1×, damit der Spiegel sofort übernimmt.
        with patch("net_safety.sicherer_abruf_status",
                   side_effect=wache.urllib.error.URLError("block")) as mock_gii:
            with self.assertRaises(wache.urllib.error.URLError):
                wache.abruf_http("https://www.gesetze-im-internet.de/bgb/__502.html",
                                 schlaf=pausen.append)
        self.assertEqual(1, mock_gii.call_count)

    def test_strict_nur_bei_toter_quelle(self):
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


class WorkflowVertragTests(unittest.TestCase):
    """Prüft die echten Shell-Blöcke aus redaktionelle-ymyl-pruefung.yml unter bash -eo pipefail."""

    def test_arbeits_ticket_und_werkzeug_integritaet(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash fehlt")
        daten = yaml.safe_load(
            (ROOT / ".github" / "workflows" / "redaktionelle-ymyl-pruefung.yml").read_text(encoding="utf-8")
        )
        schritte = {s["name"]: s for s in daten["jobs"]["belegketten"]["steps"]}
        self.assertNotIn("continue-on-error", schritte["Belegketten der Hochrisiko-Artikel prüfen"])
        ticket_run = schritte["Arbeits-Ticket pflegen"]["run"]
        integritaet_run = schritte["Werkzeug-Integrität der Belegketten-Wache"]["run"]

        # 1. Alles grün (Gate=0, Wache=0) → schließt offenes Issue #1024!
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            bin_dir = basis / "bin"
            bin_dir.mkdir()
            log_datei = basis / "gh.log"
            gh_stub = bin_dir / "gh"
            gh_stub.write_text(
                textwrap.dedent(f"""\
                    #!/usr/bin/env bash
                    echo "$*" >> "{log_datei}"
                    if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                      echo "1024"
                    fi
                """),
                encoding="utf-8",
            )
            gh_stub.chmod(0o755)
            env = dict(
                os.environ,
                PATH=f"{bin_dir}:{os.environ.get('PATH', '')}",
                GITHUB_REPOSITORY="owner/repo",
                GH_TOKEN="x",
                GATE_RESULT="success",
                GATE_OPEN="0",
                WACHE_EXIT="0",
            )
            p_close = subprocess.run([bash, "-eo", "pipefail", "-c", ticket_run],
                                     cwd=basis, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, p_close.returncode, p_close.stdout + p_close.stderr)
            self.assertIn("issue close 1024", log_datei.read_text(encoding="utf-8"))

            p_int_ok = subprocess.run([bash, "-eo", "pipefail", "-c", integritaet_run],
                                      cwd=basis, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, p_int_ok.returncode)

            # 2. Werkzeugfehler (Wache=2) → Ticket bleibt offen UND Integritäts-Schritt wird rot!
            log_datei.write_text("", encoding="utf-8")
            env_crash = dict(env, WACHE_EXIT="2")
            p_open = subprocess.run([bash, "-eo", "pipefail", "-c", ticket_run],
                                    cwd=basis, env=env_crash, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, p_open.returncode, p_open.stdout + p_open.stderr)
            self.assertIn("issue edit 1024", log_datei.read_text(encoding="utf-8"))
            self.assertNotIn("issue close", log_datei.read_text(encoding="utf-8"))

            p_int_err = subprocess.run([bash, "-eo", "pipefail", "-c", integritaet_run],
                                       cwd=basis, env=env_crash, capture_output=True, text=True, timeout=10)
            self.assertEqual(1, p_int_err.returncode)
            self.assertIn("::error::", p_int_err.stdout)


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
