#!/usr/bin/env python3
"""Regressionstests der MCP-Wache (`.mcp.json`).

Der Vertrag in vier Sätzen (26.10.2026):
  1. Jeder Server ist exakt gepinnt – ein Range ist eine Hoffnung.
  2. Kein Wert in der Datei sieht wie ein Geheimnis aus; `${VAR}` ist erlaubt.
  3. Nur Server aus der Allowlist, nur Ziele aus der Origin-Liste.
  4. Der Browser-Server startet isoliert, blockt Service-Worker, bleibt
     headless und bekommt keinen freien Dateizugriff.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_wache as wache  # noqa: E402


def gute_config() -> dict:
    return copy.deepcopy(wache._gute_config())


class PinningTests(unittest.TestCase):
    def test_exakte_version_ist_sauber(self):
        self.assertEqual(wache.pruefe(gute_config()), [])

    def test_latest_ist_kein_pin(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"][1] = "@playwright/mcp@latest"
        self.assertTrue(any(f.startswith("M3") for f in wache.pruefe(config)))

    def test_range_ist_kein_pin(self):
        for paket in ("@playwright/mcp@^0.0.83", "@playwright/mcp@~0.0.83", "@playwright/mcp@*"):
            config = gute_config()
            config["mcpServers"]["playwright"]["args"][1] = paket
            self.assertTrue(any(f.startswith("M3") for f in wache.pruefe(config)), paket)

    def test_paket_ohne_version_ist_kein_pin(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"][1] = "@playwright/mcp"
        self.assertTrue(any(f.startswith("M3") for f in wache.pruefe(config)))

    def test_ohne_paketangabe_ist_kein_pin(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"] = ["--headless"]
        self.assertTrue(any(f.startswith("M3") for f in wache.pruefe(config)))


class GeheimnisTests(unittest.TestCase):
    def test_klartext_token_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["env"] = {"GH": "ghp_" + "b" * 24}
        self.assertTrue(any(f.startswith("M2") for f in wache.pruefe(config)))

    def test_bearer_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["headers"] = {"Authorization": "Bearer abcdef123456789"}
        self.assertTrue(any(f.startswith("M2") for f in wache.pruefe(config)))

    def test_umgebungsverweis_ist_erlaubt(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["env"] = {"GH": "${GITHUB_TOKEN}"}
        self.assertEqual(wache.pruefe(config), [])

    def test_platzhalter_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"][-1] = "https://CHANGE_ME"
        self.assertTrue(any(f.startswith("M6") for f in wache.pruefe(config)))


class AllowlistTests(unittest.TestCase):
    def test_fremder_server_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["github"] = {"command": "npx",
                                          "args": ["-y", "@modelcontextprotocol/server-github@1.0.0"]}
        self.assertTrue(any(f.startswith("M4") for f in wache.pruefe(config)))

    def test_fremdes_ziel_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"][-1] = "https://beispielbank.de"
        self.assertTrue(any("fremdes Ziel" in f for f in wache.pruefe(config)))

    def test_wildcard_ziel_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"][-1] = "*"
        self.assertTrue(any("*" in f for f in wache.pruefe(config)))


class HaertungsTests(unittest.TestCase):
    def test_fehlende_schalter_fallen_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"] = [
            "-y", "@playwright/mcp@0.0.83", "--allowed-origins", "https://franksfinanzcheck.de"]
        gemeldet = " ".join(wache.pruefe(config))
        for schalter in ("--isolated", "--block-service-workers", "--headless"):
            self.assertIn(schalter, gemeldet)

    def test_freier_dateizugriff_faellt_auf(self):
        config = gute_config()
        config["mcpServers"]["playwright"]["args"].append("--allow-unrestricted-file-access")
        self.assertTrue(any("unrestricted" in f for f in wache.pruefe(config)))

    def test_ablage_ausserhalb_des_arbeitsordners_faellt_auf(self):
        config = gute_config()
        args = config["mcpServers"]["playwright"]["args"]
        args[args.index("--output-dir") + 1] = "docs/belege"
        self.assertTrue(any("Belege" in f for f in wache.pruefe(config)))

    def test_fehlende_origin_grenze_faellt_auf(self):
        config = gute_config()
        args = config["mcpServers"]["playwright"]["args"]
        stelle = args.index("--allowed-origins")
        del args[stelle:stelle + 2]
        self.assertTrue(any("allowed-origins" in f for f in wache.pruefe(config)))


class DateiTests(unittest.TestCase):
    def _lauf(self, *args: str) -> tuple[int, str]:
        out = StringIO()
        with redirect_stdout(out):
            code = wache.main(list(args))
        return code, out.getvalue()

    def test_echte_konfiguration_ist_sauber(self):
        self.assertEqual(wache.pruefe(wache.lade()), [])

    def test_fehlende_datei_ist_ein_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self._lauf("--datei", str(Path(tmp) / "gibtsnicht.json"))
        self.assertEqual(code, 1)
        self.assertIn("fehlt", out)

    def test_kaputtes_json_ist_ein_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / ".mcp.json"
            datei.write_text("{nope", encoding="utf-8")
            code, out = self._lauf("--datei", str(datei))
        self.assertEqual(code, 1)
        self.assertIn("gültiges JSON", out)

    def test_json_ausgabe_traegt_die_befunde(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / ".mcp.json"
            datei.write_text(json.dumps({"mcpServers": {"playwright": {"command": "npx", "args": []}}}),
                             encoding="utf-8")
            code, out = self._lauf("--datei", str(datei), "--json")
        self.assertEqual(code, 1)
        daten = json.loads(out)
        self.assertTrue(daten["befunde"])


class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        self.assertEqual(wache.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
