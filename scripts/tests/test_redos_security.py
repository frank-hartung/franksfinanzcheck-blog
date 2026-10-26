#!/usr/bin/env python3
"""Sicherheitsvertrag zu Code-Scanning-Alert Nr. 87 (`py/redos`, 26.10.2026).

Fünf Ebenen, damit die Heilung nicht von einem grünen Scanner-Screenshot
abhängt:

1. **Schärfe der Wache** – Selbsttest, historische Rückfallprobe in einem
   Wegwerf-Repository, Fail-closed bei Syntaxfehlern, Gegenproben für
   Kommentare und unbekannte Laufzeitmuster.
2. **Bestand** – der echte Python-Baum ist frei von R1-Strukturen; keine
   Inline-Unterdrückung für die ReDoS-Regeln.
3. **Produktheilung** – `sitemap_deaktiviert` ist zeilenweise, linear,
   bereichsscharf und wird von `inhalts_seiten` tatsächlich benutzt.
4. **Betriebsvertrag** – `py/redos` und `py/polynomial-redos` stehen im
   harten Security-Gate, die lokale Wache hat einen eigenen CI-Job, npm-
   Kurzbefehle und einen Platz im vertraglichen Minimum `GUARDS`.
5. **Dokumentation** – SECURITY.md und der datierte Report sind Wahrheitsort,
   nicht nur Begleittext.

Hintergrund: CODE-SCANNING-ALERT-87-REDAUERHEILUNG-HIGHEND-2026-10-26.md.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import governance_contract  # noqa: E402
import gsc_abdeckung  # noqa: E402
import redos_guard  # noqa: E402

WACHE = SCRIPTS / "redos_guard.py"
GSC = SCRIPTS / "gsc_abdeckung.py"
WORKFLOW = ROOT / ".github" / "workflows" / "codeql.yml"
PAKET = ROOT / "package.json"
SECURITY = ROOT / "SECURITY.md"
REPORT = ROOT / "CODE-SCANNING-ALERT-87-REDAUERHEILUNG-HIGHEND-2026-10-26.md"


def _lauf(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(WACHE), *args],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300, check=False)


def _historische_quelle() -> str:
    muster = redos_guard._historisch()
    return (f"import re\n\n"
            f"def pruefe(fm):\n    return re.search({muster!r}, fm)\n")


def _funktion(quelle: str, name: str) -> ast.FunctionDef | None:
    for knoten in ast.parse(quelle).body:
        if isinstance(knoten, ast.FunctionDef) and knoten.name == name:
            return knoten
    return None


class WacheIstScharf(unittest.TestCase):
    """Ein Detektor ohne Rückfallprobe ist nur ein guter Glaube."""

    def test_selftest_ist_gruen(self) -> None:
        ergebnis = _lauf("--selftest")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("12 Fälle grün", ergebnis.stdout)

    def test_historische_fundstelle_wird_im_wegwerf_repo_erkannt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / "scripts").mkdir()
            for nummer in range(21):
                (wurzel / "scripts" / f"leer{nummer}.py").write_text(
                    "WERT = 1\n", encoding="utf-8")
            (wurzel / "scripts" / "historisch.py").write_text(
                _historische_quelle(), encoding="utf-8")
            ergebnis = subprocess.run(
                [sys.executable, str(WACHE), "--root", str(wurzel), "--json"],
                capture_output=True, text=True, cwd=str(ROOT), timeout=300, check=False)
            self.assertEqual(ergebnis.returncode, 1, ergebnis.stdout + ergebnis.stderr)
            bericht = json.loads(ergebnis.stdout)
            funde = [f for f in bericht["funde"] if f["regel"] == redos_guard.REGEL_PUMPE]
            self.assertEqual(len(funde), 1, bericht)
            self.assertEqual(funde[0]["pfad"], "scripts/historisch.py")

    def test_kommentar_und_laufzeitmuster_sind_keine_funde(self) -> None:
        muster = redos_guard._historisch()
        nur_kommentar = f"# {muster}\ndef lese(fm):\n    return fm.splitlines()\n"
        self.assertEqual(redos_guard.analysiere_quelle(nur_kommentar), [])
        dynamisch = ("import re\n"
                     "def lese(fm, muster):\n    return re.search(muster, fm)\n")
        self.assertEqual(redos_guard.analysiere_quelle(dynamisch), [])

    def test_syntaxfehler_ist_fail_closed(self) -> None:
        funde = redos_guard.analysiere_quelle("def halb(:\n    pass\n")
        self.assertEqual(len(funde), 1)
        self.assertEqual(funde[0].regel, redos_guard.REGEL_SYNTAX)


class BestandIstFrei(unittest.TestCase):
    def test_repository_lauf_ist_gruen(self) -> None:
        ergebnis = _lauf("--json")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)
        bericht = json.loads(ergebnis.stdout)
        self.assertTrue(bericht["ok"], bericht)
        self.assertEqual(bericht["funde"], [])
        self.assertGreater(bericht["geprueft"], 400,
                           "Dateiauswahl zu klein – die Wache prüft nicht mehr den Bestand")

    def test_keine_unterdrueckung_fuer_redos_regeln(self) -> None:
        marker = "codeql[" + "py/redos]"
        marker2 = "codeql[" + "py/polynomial-redos]"
        for pfad in redos_guard.dateien(ROOT):
            text = pfad.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn(marker, text, f"Unterdrückung in {pfad}")
            self.assertNotIn(marker2, text, f"Unterdrückung in {pfad}")


class HeilungBleibtBestehen(unittest.TestCase):
    def test_parser_ist_linear(self) -> None:
        angriff = "sitemap:\n" + "\t\n" * 30000
        start = time.perf_counter()
        ergebnis = gsc_abdeckung.sitemap_deaktiviert(angriff)
        dauer = time.perf_counter() - start
        self.assertFalse(ergebnis)
        self.assertLess(dauer, 2.0, f"{dauer:.3f}s für {len(angriff)} Zeichen")

    def test_parser_kennt_bedeutung_und_blockgrenzen(self) -> None:
        self.assertTrue(gsc_abdeckung.sitemap_deaktiviert(
            "sitemap:\n  disable: true\nletzteZeile: x\n"))
        self.assertFalse(gsc_abdeckung.sitemap_deaktiviert(
            "sitemap:\n  priority: 0.6\nletzteZeile:\n  disable: true\n"))
        self.assertTrue(gsc_abdeckung.sitemap_deaktiviert(
            "sitemap: {disable: true}\n"))

    def test_sitemap_deaktiviert_benutzt_kein_regex(self) -> None:
        quelle = GSC.read_text(encoding="utf-8")
        funktion = _funktion(quelle, "sitemap_deaktiviert")
        self.assertIsNotNone(funktion)
        for knoten in ast.walk(funktion):  # type: ignore[arg-type]
            if not isinstance(knoten, ast.Call):
                continue
            ziel = knoten.func
            self.assertFalse(
                isinstance(ziel, ast.Attribute)
                and isinstance(ziel.value, ast.Name)
                and ziel.value.id == "re",
                "sitemap_deaktiviert darf kein re.* aufrufen")
        self.assertIn("splitlines()", ast.unparse(funktion))  # type: ignore[arg-type]

    def test_inhalts_seiten_ruft_den_parser_auf(self) -> None:
        quelle = GSC.read_text(encoding="utf-8")
        funktion = _funktion(quelle, "inhalts_seiten")
        self.assertIsNotNone(funktion)
        code = ast.unparse(funktion)  # type: ignore[arg-type]
        self.assertIn("sitemap_deaktiviert(fm)", code)
        self.assertNotIn("re.search", code)


class BetriebsvertragCI(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.paket = json.loads(PAKET.read_text(encoding="utf-8"))

    def test_redos_regeln_sind_security_hart(self) -> None:
        block = self.workflow.split("DOKU_SEC='", 1)[1].split("'", 1)[0]
        self.assertIn("py/redos", block)
        self.assertIn("py/polynomial-redos", block)
        self.assertNotIn("py/redos auf uncritical-Pfaden", self.workflow,
                         "ReDoS ist kein reiner Qualitäts-Hinweis")

    def test_redos_wache_laeuft_als_eigener_job(self) -> None:
        self.assertIn("redos-wache:", self.workflow)
        for aufruf in ("python3 scripts/redos_guard.py --selftest",
                       "python3 scripts/redos_guard.py",
                       "python3 -m unittest scripts.tests.test_redos_security",
                       "python3 -m unittest scripts.tests.test_gsc_abdeckung"):
            self.assertIn(aufruf, self.workflow, f"CI ruft `{aufruf}` nicht auf")

    def test_npm_und_guards_kennen_die_wache(self) -> None:
        skripte = self.paket["scripts"]
        self.assertIn("redos:wache", skripte)
        self.assertIn("test:redos", skripte)
        self.assertIn("scripts/redos_guard.py", skripte["redos:wache"])
        self.assertIn("scripts.tests.test_redos_security", skripte["test:redos"])
        self.assertIn("redos_guard.py", governance_contract.GUARDS)

    def test_dokumentation_ist_wahrheitsort(self) -> None:
        self.assertTrue(REPORT.is_file())
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("Alert Nr. 87", SECURITY.read_text(encoding="utf-8"))
        self.assertIn("py/redos", text)
        self.assertIn("sitemap_deaktiviert", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
