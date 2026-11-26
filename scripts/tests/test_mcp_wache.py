#!/usr/bin/env python3
"""Regressionstests für Standard, Diagnoseprofil und Export (ohne Browser/Netz).

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
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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

    def test_realer_standard_und_diagnose_sind_sauber(self):
        self.assertEqual(wache.lade(), {"mcpServers": {}})
        self.assertEqual(wache.main([]), 0)

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


class BedarfsprofilTests(unittest.TestCase):
    def setUp(self):
        self.standard = {"mcpServers": {}}
        self.einstellungen = {}
        self.agent = wache.lade_profil(wache.PROFIL)
        self.server = self.agent["mcpServers"][0]["playwright"]

    def befunde(self):
        return wache.pruefe_projekt(self.standard, self.agent, self.einstellungen)[1]

    def test_autostart_selbst_des_gehaerteten_servers_ist_ein_befund(self):
        self.standard = {"mcpServers": {"playwright": self.server}}
        self.assertTrue(any(f.startswith("M7") for f in self.befunde()))

    def test_kein_autostart_ueber_die_agent_einstellung(self):
        self.einstellungen["agent"] = "ff-browserdiagnose"
        self.assertTrue(any(f.startswith("M7") for f in self.befunde()))

    def test_werkzeugauswahl_ist_genau_und_ohne_wildcards(self):
        for tools in (None, [], ["mcp__playwright__*"], [*wache.DIAGNOSE_TOOLS, "Bash"],
                      [wache.DIAGNOSE_TOOLS[0]] * 5):
            with self.subTest(tools=tools):
                self.agent["tools"] = tools
                self.assertTrue(self.befunde())

    def test_nur_eine_inline_definition_keine_globale_referenz(self):
        for inline in ([], ["playwright"], [self.agent["mcpServers"][0], "anderer"], [{}]):
            with self.subTest(inline=inline):
                self.agent["mcpServers"] = inline
                self.assertTrue(self.befunde())

    def test_keine_stille_ausweitung_der_ausgabe_oder_befugnisse(self):
        args = self.server["args"]
        for flag, wert in (("--snapshot-mode", "full"), ("--codegen", "typescript"),
                           ("--console-level", "debug"), ("--output-dir", ".cache/../docs")):
            with self.subTest(flag=flag):
                i = args.index(flag) + 1
                self.server["args"] = args[:i] + [wert] + args[i + 1:]
                self.assertTrue(self.befunde())
        for extra in (["--snapshot-mode=full"], ["--snapshot-mode", "full"], ["--caps", "vision"]):
            with self.subTest(extra=extra):
                self.server["args"] = args + extra
                self.assertTrue(self.befunde())
        self.server["args"] = [a for a in args if a != "--no-webmcp"]
        self.assertTrue(self.befunde())

    def test_m1_bis_m6_pruefen_das_tatsaechlich_aktivierte_profil(self):
        self.server["args"][1] = "@playwright/mcp@latest"
        self.assertTrue(any(f.startswith("M3") for f in self.befunde()))
        self.server["command"] = "ein-anderer-starter"
        self.assertTrue(any(f.startswith("M7") for f in self.befunde()))

    def test_export_ist_reines_mcp_json_aus_der_geprueften_quelle(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(wache.main(["--export-profil"]), 0)
        config = json.loads(out.getvalue())
        self.assertEqual(config, {"mcpServers": {"playwright": self.server}})
        self.assertEqual(wache.pruefe(config), [])

    def test_export_schreibt_bei_fehlern_keine_konfiguration(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "agent.md"
            for inhalt in (None, "# Titel", "---\n{nope}\n---\n", "---\n[]\n---\n",
                           '---\n{"tools":[], "tools":["Bash"]}\n---\n'):
                with self.subTest(inhalt=inhalt), patch.object(wache, "PROFIL", f):
                    if inhalt is not None:
                        f.write_text(inhalt, encoding="utf-8")
                    out, err = StringIO(), StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        self.assertEqual(wache.main(["--export-profil"]), 1)
                    self.assertEqual(out.getvalue(), "")
                    self.assertTrue(err.getvalue().strip())


class DiagnoseAufrufTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()

    def event(self, tool, args):
        return {"hook_event_name": "PreToolUse", "tool_name": "mcp__playwright__browser_" + tool,
                "tool_input": args, "cwd": str(self.root)}

    def pruefe(self, tool, **args):
        return wache.pruefe_aufruf(self.event(tool, args), self.root)

    def test_textsuche_und_gezielter_snapshot_duerfen_durch(self):
        self.assertIsNone(self.pruefe("find", text="Suchbegriff"))
        self.assertIsNotNone(self.pruefe("find", text=" "))
        self.assertIsNone(self.pruefe("snapshot", target="#ff-suche-eingabe"))
        self.assertIsNone(self.pruefe("snapshot", depth=2))
        self.assertIsNotNone(self.pruefe("snapshot"))
        self.assertIsNotNone(self.pruefe("snapshot", target=" "))
        for wert in (0, -1, 4, True, None, "2"):
            with self.subTest(wert=wert):
                self.assertIsNotNone(self.pruefe("snapshot", depth=wert))

    def test_vollbaum_nur_in_lokale_belegdatei(self):
        self.assertIsNone(self.pruefe("snapshot", filename=".cache/mcp/befund.yml"))
        for ungueltig in ("", "/tmp/beleg", "docs/beleg", ".cache/mcp/../../datei", ".cache/mcp/..",
                          ".cache/mcp/../mcp/beleg", ".cache/mcp/unter/beleg", r".cache/mcp/..\datei"):
            with self.subTest(datei=ungueltig):
                self.assertIsNotNone(self.pruefe("snapshot", filename=ungueltig))
        event = self.event("snapshot", {"filename": ".cache/mcp/befund.yml"})
        self.assertIsNotNone(wache.pruefe_aufruf({**event, "cwd": str(self.root / "docs")}, self.root))

    def test_belege_folgen_keinem_symlink(self):
        ordner = self.root / ".cache" / "mcp"
        ordner.parent.mkdir()
        ordner.symlink_to(self.root, target_is_directory=True)
        self.assertIsNotNone(self.pruefe("find", text="Suche", filename=".cache/mcp/beleg.yml"))
        ordner.unlink()
        ordner.mkdir()
        (ordner / "beleg.yml").symlink_to(self.root / "anderer-pfad")
        self.assertIsNotNone(self.pruefe("snapshot", filename=".cache/mcp/beleg.yml"))

    def test_protokolle_nur_gezielt_oder_als_beleg(self):
        self.assertIsNotNone(self.pruefe("console_messages", level="debug"))
        self.assertIsNone(self.pruefe("console_messages", level="warning"))
        self.assertIsNotNone(self.pruefe("network_requests"))
        self.assertIsNotNone(self.pruefe("network_requests", filter="pagefind", static=True))
        self.assertIsNone(self.pruefe("network_requests", filter="pagefind"))
        self.assertIsNone(self.pruefe("network_requests", filename=".cache/mcp/netz.txt"))

    def test_hook_erhaelt_berechtigungsabfrage_und_blockiert_fehler_ohne_rohdaten(self):
        for daten, erwartet in ((self.event("snapshot", {"depth": 2}), 0),
                                (self.event("snapshot", {"target": " ", "privat": "NIE-AUSGEBEN"}), 2),
                                (self.event("evaluate", {}), 2), (None, 2), ("kaputt", 2)):
            with self.subTest(daten=daten):
                out, err = StringIO(), StringIO()
                stdin = StringIO(daten if isinstance(daten, str) else json.dumps(daten))
                with patch.object(sys, "stdin", stdin), redirect_stdout(out), redirect_stderr(err):
                    self.assertEqual(wache.main(["--vor-aufruf"]), erwartet)
                self.assertEqual(out.getvalue(), "")  # nie ein automatisches „allow“
                self.assertEqual(bool(err.getvalue()), erwartet == 2)
                self.assertNotIn("NIE-AUSGEBEN", err.getvalue())

    def test_hook_darf_im_echten_profil_nicht_fehlen(self):
        profil = wache.lade_profil(wache.PROFIL)
        profil["hooks"] = {}
        self.assertTrue(any(f.startswith("M7") for f in wache.pruefe_projekt(wache.lade(), profil, {})[1]))


class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        self.assertEqual(wache.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
