"""Regressionstests des Edge-Freigabe-Werkzeugs (WF-E813 / #809).

Zwei Verträge:

  1. TRANSPORTWEG (Ausgleich für die T6-Ausnahme in scripts/ki_transportweg.py):
     Das Werkzeug spricht die Cloudflare-VERWALTUNGS-API an (Zone, DNS, SSL,
     Transform Rules) – nie ein Modell, nie einen zweiten Anbieter. Genau das
     ist der Handel hinter dem Ausnahmeeintrag: Die Ausnahme gilt nur, solange
     dieser Vertrag sie deckt. Vorbild: test_backup_einrichtung.TransportVertrag
     (Sicherheitsaudit 14.10.2026, M-11).
  2. SELBSTSTAND: Der Selbsttest des Werkzeugs ist grün, der Sollstand kommt
     aus der Vorlage (eine Quelle), und die Werkzeugfehler laufen fail-safe
     (Exit 2, nie „alles im Soll“ ohne Messung).

Ausführung:  python3 -m unittest scripts.tests.test_cloudflare_edge_freigabe -v
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_edge_freigabe", SCRIPTS / "cloudflare_edge_freigabe.py")
edge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(edge)


class TransportVertrag(unittest.TestCase):
    """Ausgleich für die T6-Ausnahme: Verwaltungs-Pfade ja, Modell nie."""

    def test_ausnahme_ist_im_gate_eingetragen(self):
        gate = (SCRIPTS / "ki_transportweg.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/cloudflare_edge_freigabe.py")', gate)

    def test_nur_verwaltungspfade_kein_modellaufruf(self):
        quelltext = (SCRIPTS / "cloudflare_edge_freigabe.py").read_text(encoding="utf-8")
        hosts = set(re.findall(r"https://([a-z0-9.-]+)", quelltext))
        self.assertLessEqual(hosts, {"api.cloudflare.com"},
                             f"unerwartete Hosts: {hosts}")
        for verboten in ("/ai/run", "/ai/", "generativelanguage", "api.groq.com",
                         "nvidia", "pollinations", "llm_client",
                         "/chat/completions", "workers.ai"):
            self.assertNotIn(verboten, quelltext,
                             f"Modellbezug im Edge-Werkzeug: {verboten}")
        pfade = set(re.findall(r"_api\(\s*token,\s*f?[\"']([^\"']+)[\"']", quelltext))
        self.assertTrue(pfade, "keine API-Pfade gefunden – der Vertrag wäre blind")
        for pfad in pfade:
            self.assertTrue(pfad.startswith("/zones"),
                            f"Pfad ausserhalb der Zonen-Verwaltung: {pfad}")

    def test_kein_schreibzugriff_ohne_apply(self):
        """--pruefen (Standard) darf nur GET senden; Schreiben hängt an --apply."""
        quelltext = (SCRIPTS / "cloudflare_edge_freigabe.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--apply"', quelltext)
        # PATCH/POST/PUT tauchen nur in anwenden() auf – und das Skript
        # verzweigt dort ausschliesslich auf --apply.
        self.assertIn("anwenden if args.apply else pruefen", quelltext)


class Selbststand(unittest.TestCase):
    """Der Sollstand hat eine Quelle, und der Selbsttest deckt die Fehlerfälle."""

    def test_selbsttest_gruen(self):
        self.assertEqual(edge.selftest(), 0)

    def test_sollstand_kommt_aus_der_vorlage(self):
        kopfzeilen = edge.vorlage_kopfzeilen()
        self.assertEqual(len(kopfzeilen), 8)
        namen = [n for n, _ in kopfzeilen]
        self.assertIn("Strict-Transport-Security", namen)
        self.assertIn("Content-Security-Policy", namen)

    def test_ohne_token_ist_explizit_nichts_behauptet(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "cloudflare_edge_freigabe.py"), "--pruefen"],
            capture_output=True, text=True, timeout=30,
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("CLOUDFLARE_API_TOKEN", proc.stderr)


class HighendHaertung815(unittest.TestCase):
    """WF-E813 / #815: Kein SSL-Downgrade, Regel-Vollprüfung, Token-Hygiene, B7."""

    def _mock_api_antworten(self, *, ssl="strict", proxied=True, regel="ok", fehler_regel=False,
                            eigene_zuerst=False):
        kopf = edge.vorlage_kopfzeilen()
        regel_obj = edge.regel_koerper(kopf)
        if regel == "deaktiviert":
            regel_obj["enabled"] = False
        elif regel == "falscher_filter":
            regel_obj["expression"] = '(http.host eq "franksfinanzcheck.de")'

        dns = {
            "franksfinanzcheck.de": [
                {"id": "dns1", "type": "A", "name": "franksfinanzcheck.de", "proxied": proxied},
                {"id": "mail1", "type": "MX", "name": "franksfinanzcheck.de", "proxied": False},
            ],
            "www.franksfinanzcheck.de": [
                {"id": "dns2", "type": "CNAME", "name": "www.franksfinanzcheck.de", "proxied": proxied},
            ],
        }
        zustand = {
            "ssl": ssl,
            "ruleset": regel != "fehlt",
            "eigene": [] if regel == "fehlt" else [regel_obj],
        }
        if regel == "duplikat":
            import copy
            zustand["eigene"].append(copy.deepcopy(regel_obj))
        aufrufe = []

        def fake_api(token, weg, *, methode="GET", daten=None):
            aufrufe.append((methode, weg, daten))
            if weg.startswith("/zones?name="):
                return {"success": True, "result": [{"id": "zone123456", "name": "franksfinanzcheck.de"}]}
            if "/dns_records?name=" in weg and methode == "GET":
                # Der Name ist bereits URL-kodiert; Punkte bleiben unverändert.
                name = "www.franksfinanzcheck.de" if "www.franksfinanzcheck.de" in weg else "franksfinanzcheck.de"
                return {"success": True, "result": dns[name]}
            if weg.startswith("/zones/zone123456/dns_records/") and methode == "PATCH":
                rekord_id = weg.rsplit("/", 1)[1]
                treffer = next(e for eintraege in dns.values() for e in eintraege if e["id"] == rekord_id)
                treffer["proxied"] = daten["proxied"]
                return {"success": True, "result": dict(treffer)}
            if weg == "/zones/zone123456/settings/ssl" and methode == "GET":
                return {"success": True, "result": {"value": zustand["ssl"]}}
            if weg == "/zones/zone123456/settings/ssl" and methode == "PATCH":
                zustand["ssl"] = daten["value"]
                return {"success": True, "result": {"value": zustand["ssl"]}}
            if weg.endswith("/entrypoint") and methode == "GET":
                if not zustand["ruleset"]:
                    raise RuntimeError("HTTP 404")
                fremd = {"id": "fremd", "description": "Bestehende Regel"}
                regeln = ([*zustand["eigene"], fremd] if eigene_zuerst
                          else [fremd, *zustand["eigene"]])
                return {"success": True, "result": {"id": "rs1", "rules": regeln}}
            if weg == "/zones/zone123456/rulesets/rs1" and methode == "PUT":
                if fehler_regel:
                    raise RuntimeError("HTTP 403: Transform Rules fehlt")
                zustand["eigene"] = [r for r in daten["rules"] if r.get("description") == edge.REGEL]
                return {"success": True, "result": {"id": "rs1"}}
            if weg == "/zones/zone123456/rulesets" and methode == "POST":
                if fehler_regel:
                    raise RuntimeError("HTTP 403: Transform Rules fehlt")
                zustand["ruleset"] = True
                zustand["eigene"] = list(daten["rules"])
                return {"success": True, "result": {"id": "rs1"}}
            raise AssertionError(f"Unerwarteter API-Aufruf: {methode} {weg}")

        return fake_api, aufrufe, dns, zustand

    def test_ssl_strict_wird_bei_pruefen_akzeptiert_und_bei_apply_nie_herabgestuft(self):
        from unittest.mock import patch
        fake_api, aufrufe, _, _ = self._mock_api_antworten(ssl="strict", proxied=True, regel="ok")
        with patch.object(edge, "_api", side_effect=fake_api):
            code, bericht = edge.pruefen("attrappen-token", "franksfinanzcheck.de")
            self.assertEqual(code, 0, bericht)
            self.assertIn("strict", bericht)
            code_apply, bericht_apply = edge.anwenden("attrappen-token", "franksfinanzcheck.de")
            self.assertEqual(code_apply, 0, bericht_apply)
            self.assertIn("kein Downgrade", bericht_apply)
        ssl_patches = [a for a in aufrufe if a[0] == "PATCH" and "settings/ssl" in a[1]]
        self.assertEqual(ssl_patches, [], "strict darf niemals auf full herabgestuft werden!")

    def test_deaktivierte_oder_falsch_gefilterte_regel_faellt_bei_pruefen_auf(self):
        from unittest.mock import patch
        for modus, stichwort in (("deaktiviert", "deaktiviert"), ("falscher_filter", "Host-Filter")):
            with self.subTest(modus=modus):
                fake_api, _, _, _ = self._mock_api_antworten(ssl="strict", proxied=True, regel=modus)
                with patch.object(edge, "_api", side_effect=fake_api):
                    code, bericht = edge.pruefen("attrappen-token", "franksfinanzcheck.de")
                self.assertEqual(code, 1, bericht)
                self.assertIn(stichwort, bericht)

    def test_apply_hebt_flexible_an_und_erhaelt_fremde_regeln(self):
        from unittest.mock import patch
        fake_api, aufrufe, _, _ = self._mock_api_antworten(ssl="flexible", proxied=False, regel="deaktiviert")
        with patch.object(edge, "_api", side_effect=fake_api):
            code, bericht = edge.anwenden("attrappen-token", "franksfinanzcheck.de")
        self.assertEqual(code, 0, bericht)
        ssl_patches = [a for a in aufrufe if a[0] == "PATCH" and "settings/ssl" in a[1]]
        self.assertEqual(len(ssl_patches), 1)
        self.assertEqual(ssl_patches[0][2], {"value": "full"})
        put_calls = [a for a in aufrufe if a[0] == "PUT" and "rulesets/rs1" in a[1]]
        self.assertEqual(len(put_calls), 1)
        regeln = put_calls[0][2]["rules"]
        self.assertEqual(len(regeln), 2, "bestehende andere Regel muss erhalten bleiben")
        eigene = next(r for r in regeln if r["description"] == edge.REGEL)
        self.assertIs(eigene["enabled"], True)

    def test_regelupdate_behaelt_position_zu_fremden_regeln(self):
        from unittest.mock import patch
        fake_api, aufrufe, _, _ = self._mock_api_antworten(
            regel="deaktiviert", eigene_zuerst=True)
        with patch.object(edge, "_api", side_effect=fake_api):
            code, bericht = edge.anwenden("attrappen-token", "franksfinanzcheck.de")
        self.assertEqual(code, 0, bericht)
        put = next(a for a in aufrufe if a[0] == "PUT" and "rulesets/rs1" in a[1])
        self.assertEqual([r["description"] for r in put[2]["rules"]],
                         [edge.REGEL, "Bestehende Regel"])

    def test_sichere_schreibreihenfolge_regel_ssl_dann_erst_dns(self):
        from unittest.mock import patch
        fake_api, aufrufe, _, _ = self._mock_api_antworten(
            ssl="flexible", proxied=False, regel="deaktiviert")
        with patch.object(edge, "_api", side_effect=fake_api):
            code, bericht = edge.anwenden("attrappen-token", "franksfinanzcheck.de")
        self.assertEqual(code, 0, bericht)
        writes = [(methode, weg) for methode, weg, _ in aufrufe if methode != "GET"]
        self.assertEqual(len(writes), 4)
        self.assertIn("rulesets/rs1", writes[0][1])
        self.assertIn("settings/ssl", writes[1][1])
        self.assertTrue(all("dns_records/" in weg for _, weg in writes[2:]))
        self.assertNotIn("mail1", repr(writes), "Mail-DNS darf niemals verändert werden")
        self.assertIn("API-SOLL NACHGEWIESEN", bericht)

    def test_fehler_an_header_regel_laesst_dns_und_ssl_unangetastet(self):
        from unittest.mock import patch
        fake_api, aufrufe, dns, zustand = self._mock_api_antworten(
            ssl="flexible", proxied=False, regel="deaktiviert", fehler_regel=True)
        with patch.object(edge, "_api", side_effect=fake_api):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                edge.anwenden("attrappen-token", "franksfinanzcheck.de")
        writes = [(methode, weg) for methode, weg, _ in aufrufe if methode != "GET"]
        self.assertEqual(len(writes), 1, "Nur die scheiternde Regel wurde versucht")
        self.assertIn("rulesets/rs1", writes[0][1])
        self.assertEqual(zustand["ssl"], "flexible")
        self.assertFalse(dns["franksfinanzcheck.de"][0]["proxied"])
        self.assertFalse(dns["www.franksfinanzcheck.de"][0]["proxied"])

    def test_preflight_ohne_www_schreibt_nichts(self):
        from unittest.mock import patch
        fake_api, aufrufe, dns, _ = self._mock_api_antworten(proxied=False, regel="deaktiviert")
        dns["www.franksfinanzcheck.de"] = []
        with patch.object(edge, "_api", side_effect=fake_api):
            with self.assertRaisesRegex(RuntimeError, "Preflight ohne Änderung"):
                edge.anwenden("attrappen-token", "franksfinanzcheck.de")
        self.assertFalse(any(methode != "GET" for methode, _, _ in aufrufe))

    def test_doppelte_regel_ist_drift_und_wird_eindeutig_geheilt(self):
        from unittest.mock import patch
        fake_api, _, _, _ = self._mock_api_antworten(regel="duplikat")
        with patch.object(edge, "_api", side_effect=fake_api):
            code, bericht = edge.pruefen("attrappen-token", "franksfinanzcheck.de")
        self.assertEqual(code, 1)
        self.assertIn("genau einmal", bericht)

        fake_api, _, _, zustand = self._mock_api_antworten(regel="duplikat")
        with patch.object(edge, "_api", side_effect=fake_api):
            code, bericht = edge.anwenden("attrappen-token", "franksfinanzcheck.de")
        self.assertEqual(code, 0, bericht)
        self.assertEqual(len(zustand["eigene"]), 1)

    def test_ungueltiger_token_und_fremder_pfad_scheitern_ohne_leak(self):
        gift = "GIFT_BEARER_NIE_LOGGEN\nZWEITE_ZEILE"
        with self.assertRaises(RuntimeError) as cm:
            edge._api(gift, "/zones")
        self.assertNotIn("GIFT_BEARER", str(cm.exception))
        with self.assertRaises(RuntimeError):
            edge._api("sauberer-token", "/accounts")

    def test_apply_schliesst_b7_erst_nach_api_gegenmessung_an(self):
        import tempfile
        from unittest.mock import patch
        original = (REPO / "content" / "datenschutz" / "index.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "index.md"
            ziel.write_text(original, encoding="utf-8")
            fake_api, _, _, _ = self._mock_api_antworten(ssl="strict", proxied=False, regel="deaktiviert")
            with patch.object(edge, "_api", side_effect=fake_api), patch.object(edge, "DATENSCHUTZ", ziel):
                code, bericht = edge.anwenden("attrappen-token", "franksfinanzcheck.de", b7=True)
            self.assertEqual(code, 0, bericht)
            umgestellt = ziel.read_text(encoding="utf-8")
            self.assertEqual(edge.datenschutz_b7_offen(umgestellt), [])
            self.assertIn("muss noch committed", bericht)

    def test_b7_transformation_bleibt_kompatibel_mit_datenschutz_quellvertrag(self):
        import tempfile
        original = (REPO / "content" / "datenschutz" / "index.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "index.md"
            ziel.write_text(original, encoding="utf-8")
            code_vor, _ = edge.b7_kommando(ziel, schreiben=False)
            self.assertEqual(code_vor, 1)
            code_apply, _ = edge.b7_kommando(ziel, schreiben=True)
            self.assertEqual(code_apply, 0)
            umgestellt = ziel.read_text(encoding="utf-8")
            self.assertNotIn("kein Proxy von Cloudflare", umgestellt)
            self.assertNotIn("keine Informationen über Seitenaufrufe", umgestellt)
            self.assertNotIn("Cloudflare-CDN", umgestellt)
            self.assertIn("CDN von Cloudflare, Inc.", umgestellt)
            self.assertIn("stats.franksfinanzcheck.de", umgestellt)
            self.assertIn("GitHub-Actions-Läufe", umgestellt)


if __name__ == "__main__":
    unittest.main()
