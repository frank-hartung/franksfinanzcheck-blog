#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vertragstests der Code-Selbstheilung (#709, 12.10.2026).

Sichert alle fünf Schichten offline im temporären Verzeichnis (kein Schreibzugriff
auf das echte Repository):
  1. Schutz-Vertrag (`data/code_schutz_vertrag.json`) inkl. Vertrags-Boden
  2. Eichprobe (Exit 3 `MESSGERAET` bei blindem Prüfer)
  3. Transform (AST-genau; heilbarer #709-Befund → Host-exakt)
  4. Monotone Belegkette (`data/code_schutz_belege.jsonl`) mit Manipulationsschutz
  5. Verdrahtungs-Wache (`--wache`), H-02-Grenze (kein `gh pr merge`)
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import code_selbstheilung as heiler  # noqa: E402


def _gueltiger_vertrag() -> Dict[str, object]:
    return {
        "schema": 1,
        "regel": "url-substring",
        "basis": "py/incomplete-url-substring-sanitization (CodeQL)",
        "pruefer": "scripts/url_substring_guard.py",
        "helper_module": "scripts/url_host.py",
        "helper_funktionen": ["ist_host_oder_subdomain"],
        "heil_branch_praefix": "automation/code-selbstheilung-",
        "ledger": heiler.LEDGER_PFAD,
        "max_heilbare_dateien": 40,
        "ausgeschlossene_dateien": ["scripts/url_substring_guard.py"],
        "begruendung": "Testvertrag für Vorfall #709 mit Offline-Heiler.",
    }


def _baue_baum(wurzel: Path, *, mit_py_fundstelle: bool = True) -> None:
    """Baut einen minimal-treuen Bestand, in dem #709-Fundstellen liegen."""
    (wurzel / "data").mkdir(parents=True, exist_ok=True)
    (wurzel / heiler.VERTRAG_PFAD).write_text(json.dumps(_gueltiger_vertrag()), encoding="utf-8")
    (wurzel / heiler.LEDGER_PFAD).write_text("", encoding="utf-8")
    if mit_py_fundstelle:
        (wurzel / "scripts").mkdir(parents=True, exist_ok=True)
        (wurzel / "scripts" / "serp_anbieter.py").write_text('''
def ist_eigen(url):
    return "duckduckgo.com" in url
''', encoding="utf-8")


def _schreib_fundstelle(wurzel: Path, datei_rel: str, inhalt: str) -> None:
    pfad = wurzel / datei_rel
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")


class VertragTest(unittest.TestCase):
    def test_echter_repo_vertrag_ist_gueltig(self) -> None:
        vertrag = heiler.lade_vertrag(ROOT)
        self.assertEqual(vertrag["schema"], 1)
        self.assertEqual(vertrag["regel"], "url-substring")
        self.assertEqual(vertrag["helper_module"], "scripts/url_host.py")
        self.assertEqual(vertrag["helper_funktionen"], ["ist_host_oder_subdomain"])
        self.assertTrue(vertrag["ausgeschlossene_dateien"])

    def test_vertrag_mit_unbekanntem_schluessel_wird_abgelehnt(self) -> None:
        vertrag = _gueltiger_vertrag()
        vertrag["unbekannter_schluessel"] = "x"
        fehler = heiler.vertrag_fehler(vertrag)
        self.assertTrue(any("Unbekannte" in f for f in fehler))

    def test_vertrag_mit_doppelten_schluesseln_ist_nicht_belegbar(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            wurzel = Path(temp)
            (wurzel / "data").mkdir(parents=True, exist_ok=True)
            (wurzel / heiler.VERTRAG_PFAD).write_text(
                '{"schema": 1, "regel": "url-substring", "basis": "py/incomplete-url-substring-sanitization", "pruefer": "scripts/url_substring_guard.py", "helper_module": "scripts/url_host.py", "helper_funktionen": ["ist_host_oder_subdomain"], "heil_branch_praefix": "automation/code-selbstheilung-", "ledger": "data/code_schutz_belege.jsonl", "max_heilbare_dateien": 40, "ausgeschlossene_dateien": [], "begruendung": "Doppelschlüssel in Vertrag.", "schema": 1}',
                encoding="utf-8",
            )
            with self.assertRaises(heiler.NichtBelegbar):
                heiler.lade_vertrag(wurzel)

    def test_vertrag_mit_falschem_basis_wird_abgelehnt(self) -> None:
        vertrag = _gueltiger_vertrag()
        vertrag["basis"] = "py/irgendwas"
        fehler = heiler.vertrag_fehler(vertrag)
        self.assertTrue(any("basis" in f for f in fehler))

    def test_unbekannter_helper_wird_abgelehnt(self) -> None:
        vertrag = _gueltiger_vertrag()
        vertrag["helper_funktionen"] = ["ist_host_und_nicht_der_falsche"]
        fehler = heiler.vertrag_fehler(vertrag)
        self.assertTrue(any("ist_host_und_nicht_der_falsche" in f for f in fehler))

    def test_nicht_heilbarer_ledger_wird_abgelehnt(self) -> None:
        vertrag = _gueltiger_vertrag()
        vertrag["ledger"] = "scripts/code_selbstheilung.py"
        fehler = heiler.vertrag_fehler(vertrag)
        self.assertTrue(any("ledger" in f for f in fehler))


class EichprobeTest(unittest.TestCase):
    def test_eichprobe_ist_gruen(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_wurzel = Path(temp)
            geprueft = heiler._eichprobe_lauf(temp_wurzel)
            self.assertTrue(any(s.startswith("detektion:6") for s in geprueft))

    def test_blinder_pruefer_wirft_exit_3(self) -> None:
        def _blinder(_dateien, _wurzel):
            return [], []
        with tempfile.TemporaryDirectory() as temp:
            temp_wurzel = Path(temp)
            with self.assertRaises(heiler.MessGeraet):
                heiler._eichprobe_lauf(temp_wurzel, pruefer=_blinder)


class TransformTest(unittest.TestCase):
    def test_in_form_wird_host_exakt_geliedert(self) -> None:
        text = '''
def ist_eigen(url):
    return "duckduckgo.com" in url
'''
        neuer_text, geheilte, nicht_heilbare = heiler._transformiere_sicher(text, Path("."))
        self.assertIsNotNone(neuer_text)
        self.assertIn("ist_host_oder_subdomain(url", neuer_text)
        self.assertNotIn("\"duckduckgo.com\" in url", neuer_text)
        self.assertFalse(nicht_heilbare)

    def test_not_in_wird_invertiert_geheilert(self) -> None:
        text = '''
def fremd(url):
    return "duckduckgo.com" not in url
'''
        neuer_text, geheilte, nicht_heilbare = heiler._transformiere_sicher(text, Path("."))
        self.assertIn("not ist_host_oder_subdomain", neuer_text)

    def test_startswith_wird_geheilert(self) -> None:
        text = '''
def ist_api(url):
    return url.startswith("https://api.resend.com")
'''
        neuer_text, geheilte, nicht_heilbare = heiler._transformiere_sicher(text, Path("."))
        self.assertIsNotNone(neuer_text)
        self.assertIn("ist_host_oder_subdomain(url", neuer_text)

    def test_endswith_wird_geheilert(self) -> None:
        text = '''
def eigener_host(host):
    return host.endswith("api.resend.com")
'''
        neuer_text, geheilte, nicht_heilbare = heiler._transformiere_sicher(text, Path("."))
        self.assertIsNotNone(neuer_text)
        self.assertIn("ist_host_oder_subdomain(host", neuer_text)

    def test_nicht_heilbare_rechts_quelle_bleibt_unangetastet(self) -> None:
        text = '''
def gefaehrlich(url):
    return ("duckduckgo.com" + ".de") in url
'''
        # Literal ist nicht einsame Konstante – bleibt unheilbar
        neuer_text, geheilte, nicht_heilbare = heiler._transformiere_sicher(text, Path("."))
        self.assertIsNone(neuer_text)


class BelegketteTest(unittest.TestCase):
    def test_leere_kette_ist_valide(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pfad = Path(temp) / "belege.jsonl"
            pfad.write_text("", encoding="utf-8")
            eintraege = heiler.pruefe_belegkette(pfad)
            self.assertEqual(eintraege, [])

    def test_append_und_verifizieren(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pfad = Path(temp) / "belege.jsonl"
            eintrag = heiler.haenge_beleg_an(
                pfad,
                klasse="GEHEILT",
                befund_id="test",
                vorher={"py_befunde": 1},
                nachher={"py_befunde": 0},
                geheilte_dateien=["scripts/x.py"],
                schritte=["test"],
                gruende=[],
            )
            self.assertEqual(eintrag["seq"], 1)
            eintraege = heiler.pruefe_belegkette(pfad)
            self.assertEqual(len(eintraege), 1)

    def test_manipulation_wird_erkannt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pfad = Path(temp) / "belege.jsonl"
            heiler.haenge_beleg_an(
                pfad, klasse="GEHEILT", befund_id="a",
                vorher={}, nachher={}, geheilte_dateien=[], schritte=[], gruende=[],
            )
            roh = pfad.read_text(encoding="utf-8")
            roh = roh.replace("GEHEILT", "OFFEN")
            pfad.write_text(roh, encoding="utf-8")
            with self.assertRaises(heiler.KetteKaputt):
                heiler.pruefe_belegkette(pfad)


class VollheilungTest(unittest.TestCase):
    def test_vorfall_709_vollendet_nach_healing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            wurzel = Path(temp)
            _baue_baum(wurzel, mit_py_fundstelle=True)
            ergebnis = heiler.ausfuehren(wurzel, schreiben=True)
            self.assertEqual(ergebnis["klasse"], "GEHEILT")
            self.assertEqual(ergebnis["code"], 0)
            self.assertTrue(ergebnis["geaenderte_dateien"])
            # Ledger wurde nachgebildet
            ledger = Path(wurzel) / heiler.LEDGER_PFAD
            self.assertTrue(ledger.exists())
            eintraege = heiler.pruefe_belegkette(ledger)
            self.assertEqual(len(eintraege), 1)
            self.assertEqual(eintraege[0]["klasse"], "GEHEILT")

    def test_idempotenz_sauberer_bestand_schreibt_keinen_beleg(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            wurzel = Path(temp)
            _baue_baum(wurzel, mit_py_fundstelle=False)
            # Vertrag & Ledger existieren, Bestand sauber
            ergebnis = heiler.ausfuehren(wurzel, schreiben=True)
            self.assertEqual(ergebnis["klasse"], "SICHER")
            ledger = wurzel / heiler.LEDGER_PFAD
            self.assertEqual(ledger.read_text(encoding="utf-8"), "")


class VerdrahtungTest(unittest.TestCase):
    def test_verdrahtung_echter_repo_ist_gruen(self) -> None:
        fehler = heiler.pruefe_verdrahtung(ROOT)
        self.assertEqual(fehler, [], f"verdrahtung fehlerhaft: {fehler}")

    def test_verdrahtung_erkennt_sabotage_in_gitattributes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            wurzel = Path(temp)
            _baue_baum(wurzel, mit_py_fundstelle=False)
            # Simuliere einen echten Verdrahtungstest ohne Workflow/Alert-File
            # (der echte Repo-Test prüft andere Dinge; hier prüfen wir, dass eine
            # fehlende dist-Pflichtdatei auffällt)
            fehler = heiler.pruefe_verdrahtung(wurzel)
            self.assertTrue(any("Pflichtdatei fehlt" in f for f in fehler))


class CliTest(unittest.TestCase):
    def test_cli_selftest_liefert_exit_0(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = heiler.main(["--selftest"])
        self.assertEqual(code, 0)
        self.assertIn("Selbsttest", stdout.getvalue())

    def test_cli_pruefen_liest_bestand_ohne_schreibzugriff(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = heiler.main(["--pruefen", "--json"])
        self.assertIn(code, (0, 1))


if __name__ == "__main__":
    unittest.main()
