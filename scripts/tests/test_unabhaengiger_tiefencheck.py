#!/usr/bin/env python3
"""Regressions- und Sabotage-Suite zum unabhängigen Tiefencheck (30.10.2026).

Sichert die sechs gehärteten Fehler- und Sicherheitsklassen dauerhaft ab:
  1. XML-Härtung (`safe_xml.py`): Billion-Laughs, XXE, externe DTD, Größenlimit
  2. Netz-/SSRF-/LFI-Schutz (`net_safety.py`, Adapter, `render.mjs`)
  3. Laufzeitfehler `F823` (`UnboundLocalError: re`) in `engine_generate.py`
  4. Keyword-Splitting-Bug (`r"[,\\n;]"` -> `r"[,\n;]"`) in `keyword_optimizer.py`
  5. URL-Host-Spoofing-Abwehr in `pinterest_plan_guard.py` (`url_host.py`)
  6. GitHub-Actions-Template-Injection-Freiheit (`run:`), Job-Permissions & Docker
"""
from __future__ import annotations

import ast
import glob
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import net_safety  # noqa: E402
import safe_xml  # noqa: E402


class SafeXmlHaertungTests(unittest.TestCase):
    """Beweist Schutz vor XML-Entitäten/XXE bei voller Sitemap-Kompatibilität."""

    def test_selftest_gruen(self):
        self.assertEqual(safe_xml.selftest(), 0)

    def test_blockiert_billion_laughs_und_xxe_in_konsumenten(self):
        import gsc_abdeckung
        import indexierbare_seiten

        bombe = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>https://franksfinanzcheck.de/&lol2;/</loc></url>"
            "</urlset>"
        )
        with self.assertRaises(indexierbare_seiten.SitemapFehler):
            indexierbare_seiten.parse_sitemap(bombe)

        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "sitemap.xml"
            pfad.write_text(bombe, encoding="utf-8")
            self.assertEqual(gsc_abdeckung.sitemap_seiten(pfad), [])


class NetSafetyUndSsrfTests(unittest.TestCase):
    """Beweist Schema-Zwang, LFI-/SSRF-Abwehr und Cross-Zone-Redirect-Sperre."""

    def test_selftest_gruen(self):
        self.assertEqual(net_safety.selftest(), 0)

    def test_blockiert_lfi_metadaten_privatnetze_und_cross_zone_redirect(self):
        for ziel in (
            "file:///etc/passwd",
            "ftp://example.org/x",
            "javascript:alert(1)",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::ffff:169.254.169.254]/",
            "http://10.1.2.3/",
            "http://172.20.0.1/",
            "http://192.168.0.1/",
            "http://127.0.0.1:8765/health",
        ):
            ok, _ = net_safety.pruefe_url_ziel(ziel, erlaube_loopback=False, aufloesen=False)
            self.assertFalse(ok, f"Unsicheres Ziel nicht blockiert: {ziel}")

        handler = net_safety._SichererRedirectHandler(erlaube_loopback=True)
        start = urllib.request.Request("https://93.184.216.34/start")
        with self.assertRaises(net_safety.UnsicheresZielFehler):
            handler.redirect_request(
                start, None, 302, "Found", {}, "http://127.0.0.1:5678/"
            )

    def test_adapter_weisen_datei_und_metadaten_urls_ab(self):
        import agent_reach_research
        import faktenfrische
        import schaltwerk_triggers
        import werkbank_adapters

        self.assertEqual(
            schaltwerk_triggers.trigger_rss({"url": "file:///etc/passwd"}, {}),
            [],
        )
        dok, fehler = faktenfrische.sammle_web("http://169.254.169.254/latest/", ["strom"], 500)
        self.assertIsNone(dok)
        self.assertIn("abgelehnt", fehler or "")

        dok2, fehler2 = agent_reach_research.sammle_web("file:///etc/passwd", 500, 5)
        self.assertIsNone(dok2)
        self.assertIn("abgelehnt", fehler2 or "")

        gelesen = werkbank_adapters.lies(["file:///etc/passwd", "http://169.254.169.254/"], {})
        self.assertIn("gesperrt", gelesen["file:///etc/passwd"]["fehler"])
        self.assertIn("gesperrt", gelesen["http://169.254.169.254/"]["fehler"])

        beweis = werkbank_adapters.browser_beweis("http://127.0.0.1:8765/health", {})
        self.assertEqual(beweis["zustand"], werkbank_adapters.DEFEKT)
        self.assertIn("gesperrt", beweis["grund"])

    def test_playwright_bruecke_selftest(self):
        if not shutil.which("node"):
            self.skipTest("node nicht im PATH")
        proc = subprocess.run(
            ["node", str(ROOT / "tools" / "werkbank" / "render.mjs"), "--selftest"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)


class LaufzeitUndLogikRegressionenTests(unittest.TestCase):
    """Sichert behobene Python-/JS-Logikfehler gegen Rückfälle ab."""

    def test_engine_generate_hat_kein_lokales_re_shadowing(self):
        quelltext = (ROOT / "scripts" / "engine_generate.py").read_text(encoding="utf-8")
        baum = ast.parse(quelltext)
        for knoten in ast.walk(baum):
            if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for kind in ast.walk(knoten):
                    if isinstance(kind, ast.Import):
                        namen = [alias.asname or alias.name for alias in kind.names]
                        self.assertNotIn(
                            "re",
                            namen,
                            f"Lokales `import re` in Funktion `{knoten.name}` erzeugt UnboundLocalError (F823)",
                        )

    def test_keyword_optimizer_trennt_zeilenumbrueche_statt_buchstabe_n(self):
        import re

        quelltext = (ROOT / "scripts" / "keyword_optimizer.py").read_text(encoding="utf-8")
        self.assertNotIn(r'r"[,\\n;]"', quelltext)
        self.assertIn(r'r"[,\n;]"', quelltext)
        roh = '"Nebenkosten senken"\n"Stromtarif wechseln"; Internetvertrag kündigen'
        teile = [p.strip().strip("\"'„“”‚‘") for p in re.split(r"[,\n;]", roh) if p.strip()]
        self.assertEqual(
            teile,
            ["Nebenkosten senken", "Stromtarif wechseln", "Internetvertrag kündigen"],
        )

    def test_pinterest_plan_guard_wehrt_host_spoofing_ab(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML nicht installiert")
        import pinterest_plan_guard as ppg

        for boese in (
            "https://franksfinanzcheck.de.angreifer.tld/posts/x/",
            "https://evilfranksfinanzcheck.de/posts/x/",
            "https://angreifer.tld/franksfinanzcheck.de",
            "https://franksfinanzcheck.de@angreifer.tld/posts/x/",
        ):
            code, _ = ppg.pruefe_ziel_url(boese)
            self.assertEqual(code, "fremd", f"Spoofing-URL nicht abgewiesen: {boese}")
        code_ok, _ = ppg.pruefe_ziel_url("https://franksfinanzcheck.de/posts/strom-sparen/")
        self.assertIsNone(code_ok)

    def test_seo_cockpit_regel_label_nicht_ueberschrieben(self):
        if not shutil.which("node"):
            self.skipTest("node nicht im PATH")
        proc = subprocess.run(
            ["node", "--test", str(ROOT / "tools" / "seo-cockpit" / "app.test.cjs")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)


class WorkflowUndContainerHaertungTests(unittest.TestCase):
    """Prüft Template-Injection-Freiheit in `run:`, Job-Permissions und Dockerfile."""

    def test_keine_github_expression_in_run_bloecken(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML nicht installiert")
        verstoesse: list[str] = []
        for wf_pfad in sorted(glob.glob(str(ROOT / ".github" / "workflows" / "*.yml"))):
            daten = yaml.safe_load(Path(wf_pfad).read_text(encoding="utf-8")) or {}
            for job_id, job in (daten.get("jobs") or {}).items():
                for idx, schritt in enumerate(job.get("steps") or []):
                    skript = schritt.get("run")
                    if isinstance(skript, str) and "${{" in skript:
                        verstoesse.append(f"{Path(wf_pfad).name}:{job_id}:step[{idx}]")
        self.assertEqual(
            verstoesse,
            [],
            f"Direkte ${{}}-Interpolation in `run:` gefunden (Template-Injection-Risiko): {verstoesse}",
        )

    def test_least_privilege_auf_mehrjob_workflows(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML nicht installiert")
        for datei, lese_jobs in (
            ("codeql.yml", ("klartext-wache", "url-wache", "redos-wache")),
            ("redaktionelle-ymyl-pruefung.yml", ("pruefung",)),
        ):
            daten = yaml.safe_load(
                (ROOT / ".github" / "workflows" / datei).read_text(encoding="utf-8")
            )
            self.assertEqual(daten.get("permissions"), {"contents": "read"})
            for jname in lese_jobs:
                self.assertNotIn(
                    "permissions",
                    daten["jobs"][jname],
                    f"{datei}:{jname} soll ausschliesslich lesend bleiben",
                )

    def test_dockerfile_whisper_entfernt_compiler_und_laeuft_unprivilegiert(self):
        inhalt = (ROOT / "tools" / "n8n" / "Dockerfile.whisper").read_text(encoding="utf-8")
        self.assertIn("apt-get purge -y --auto-remove git build-essential", inhalt)
        self.assertIn("USER whisper", inhalt)


if __name__ == "__main__":
    unittest.main()
