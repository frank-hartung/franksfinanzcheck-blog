#!/usr/bin/env python3
"""Regressionstests der Search-Console-Artefakt-Wache (24.10.2026).

DER BEFUND, DEN DIESE DATEI EINFRIERT
-------------------------------------
Am 21.10.2026 hat Git drei Dateien aus `data/gsc/` als TEXT zusammengeführt:

  * `meta.json` trug danach vier `stand`-Schlüssel in einem Objekt – kein
    gültiges JSON,
  * `top_seiten_28t.json` enthielt drei Fragmente ohne Trennkomma mitten im
    Eintrag „impressum“,
  * `top_suchbegriffe_28t.json` enthielt einen Suchbegriff samt den Kennzahlen
    des NÄCHSTEN Laufs.

Vier Tage lang war `Integritäts-Siegel` für jeden Pull-Request rot
(Artefakt-Wächter, A1-JSON-SYNTAX), ohne dass jemand die Ursache lesen konnte.
`scripts/gsc_artefakte_guard.py` beantwortet die Fragen, die eine reine
Syntaxprüfung offenlässt – und heilt nur mit Beleg aus dem Git.

Die Tests decken drei Ebenen ab:
  1. Der echte Bestand ist gesund (die Heilung ist nicht nur behauptet).
  2. Jede Defektklasse wird erkannt – auch die, die gültiges JSON erzeugt
     (zwei Läufe in einer Liste, doppelter Ledger-Tag, Kopf gegen Zahlen).
  3. Die Heilung erfindet nichts: ohne belegbaren Stand bleibt die Datei
     unangetastet, und ein Gesamtstand ist ganz oder gar nicht.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gsc_artefakte_guard as g  # noqa: E402

GIT = shutil.which("git") is not None
SKRIPT = ROOT / "scripts" / "gsc_artefakte_guard.py"


# --------------------------------------------------------------------- Fixtures

def meta(**aenderungen) -> dict:
    daten = {
        "stand": "2026-10-20T10:01:45Z",
        "quelle": "google-search-console-api (Dienstkonto, nur lesen)",
        "site": "sc-domain:franksfinanzcheck.de",
        "zeitraum": {"von": "2026-07-20", "bis": "2026-10-17"},
        "status": "ok",
        "grund": "",
        "datenschutz": "nur aggregierte Kennzahlen",
        "tage_neu": 3,
        "tage_gesamt": 3,
        "klicks_zeitraum": 0,
    }
    daten.update(aenderungen)
    return daten


def top(dimension: str, schluessel=("a", "b")) -> list[dict]:
    return [{dimension: k, "clicks": 0, "impressions": 1, "ctr": 0.0, "position": 5.0}
            for k in schluessel]


def ledger(tage=("2026-10-15", "2026-10-16", "2026-10-17")) -> str:
    return "".join(json.dumps({"datum": d, "clicks": 0, "impressions": 1,
                               "ctr": 0.0, "position": 5.0}) + "\n" for d in tage)


def satz(wurzel: Path, meta_daten=None, seiten=None, begriffe=None,
         ledger_text: str | None = None) -> None:
    d = wurzel / g.GSC
    d.mkdir(parents=True, exist_ok=True)
    (d / g.META).write_text(json.dumps(meta_daten if meta_daten is not None else meta(),
                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / g.TOP_SEITEN).write_text(json.dumps(
        seiten if seiten is not None else top("seite"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (d / g.TOP_SUCHBEGRIFFE).write_text(json.dumps(
        begriffe if begriffe is not None else top("suchbegriff"),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / g.LEDGER).write_text(ledger_text if ledger_text is not None else ledger(),
                              encoding="utf-8")


def git(wurzel: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(wurzel), capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


def git_repo(wurzel: Path) -> None:
    git(wurzel, "init", "-q")
    git(wurzel, "config", "user.email", "test@example.invalid")
    git(wurzel, "config", "user.name", "Test")
    git(wurzel, "add", "-A")
    git(wurzel, "commit", "-qm", "Stand")


def codes(funde: list[g.Fund]) -> set[str]:
    return {f.pruefung for f in funde}


# ------------------------------------------------------------------ Echter Bestand

class EchterBestandTest(unittest.TestCase):
    """Der ausgelieferte Stand muss gesund sein – nicht nur der Test-Fixture."""

    def test_bestand_ist_gueltig_eindeutig_und_passend(self):
        funde = g.pruefe_alle(ROOT)
        self.assertEqual([], [str(f) for f in funde],
                         "data/gsc/ ist nicht gesund – Reparatur: "
                         "python3 scripts/gsc_artefakte_guard.py --heal")

    def test_vier_artefakte_werden_geprueft(self):
        namen = sorted(p.name for p in g.dateien(ROOT))
        self.assertEqual(sorted([g.META, g.LEDGER, g.TOP_SEITEN, g.TOP_SUCHBEGRIFFE]), namen)

    def test_selbsttest_der_wache_bestanden(self):
        r = subprocess.run([sys.executable, str(SKRIPT), "--selftest"],
                           capture_output=True, text=True, timeout=180)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)


# ------------------------------------------------------- Erkennen: Syntax & Sinne

class ErkennenTest(unittest.TestCase):
    def test_verkettete_meta_ist_kein_json(self):
        with self.assertRaises(ValueError):
            g._json('{"stand": "a",\n "stand": "b"}')

    def test_meta_ohne_pflichtfeld(self):
        daten = meta()
        daten.pop("datenschutz")
        self.assertTrue(any("datenschutz" in m for m in g.pruefe_meta(daten)))

    def test_meta_status_unbekannt(self):
        self.assertTrue(any("status" in m for m in g.pruefe_meta(meta(status="vielleicht"))))

    def test_meta_zeitraum_verdreht(self):
        self.assertTrue(any("verdreht" in m
                            for m in g.pruefe_meta(meta(zeitraum={"von": "2026-10-17",
                                                                 "bis": "2026-07-20"}))))

    def test_meta_kennzahl_fehlt_bei_status_ok(self):
        daten = meta()
        daten.pop("tage_neu")
        self.assertTrue(any("tage_neu" in m for m in g.pruefe_meta(daten)))

    def test_top_liste_mit_zwei_laeufen_ist_gueltiges_json_aber_doppelt(self):
        """Der Fall, den ein Text-Merge mit `union` erzeugt: Syntax grün, Aussage falsch."""
        doppelt = top("suchbegriff") + top("suchbegriff")
        json.loads(json.dumps(doppelt))  # gültiges JSON – und trotzdem kaputt
        fehler = g.pruefe_top(doppelt, "suchbegriff")
        self.assertTrue(any("doppelt" in m for m in fehler), fehler)

    def test_top_eintrag_mit_fremden_schluesseln(self):
        kaputt = top("seite")
        kaputt[0]["clicks_alt"] = 3
        self.assertTrue(any("Schlüssel" in m for m in g.pruefe_top(kaputt, "seite")))

    def test_top_ctr_ausserhalb(self):
        kaputt = top("seite")
        kaputt[0]["ctr"] = 71.0
        self.assertTrue(any("ctr" in m for m in g.pruefe_top(kaputt, "seite")))

    def test_leere_top_liste_ist_gueltig(self):
        """Kein Traffic im Fenster ist ein Zustand, kein Defekt."""
        self.assertEqual([], g.pruefe_top([], "seite"))

    def test_ledger_mit_doppeltem_tag(self):
        self.assertTrue(any("doppelt" in m
                            for m in g.pruefe_ledger(ledger(("2026-10-16", "2026-10-16")))))

    def test_ledger_laeuft_rueckwaerts(self):
        self.assertTrue(any("rückwärts" in m
                            for m in g.pruefe_ledger(ledger(("2026-10-17", "2026-10-15")))))

    def test_ledger_zeile_ohne_json(self):
        self.assertTrue(g.pruefe_ledger("{\"datum\": \"2026-10-17\",\n"))

    def test_kreuz_fenster_hinter_dem_letzten_tag(self):
        fehler = g.pruefe_kreuz(meta(zeitraum={"von": "2026-07-20", "bis": "2026-10-29"}),
                                ledger())
        self.assertTrue(any("hinter dem letzten Ledger-Tag" in m for m in fehler), fehler)

    def test_kreuz_kopf_zaehlt_mehr_tage_als_gemessen(self):
        fehler = g.pruefe_kreuz(meta(tage_neu=9, tage_gesamt=9), ledger())
        self.assertTrue(any("tage_gesamt" in m for m in fehler), fehler)

    def test_ohne_zugang_ist_nur_der_kopf_da_und_das_ist_kein_fund(self):
        """Ein Repo ohne Search-Console-Zugang hat eine Datei – und die sagt warum."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / g.GSC).mkdir(parents=True)
            ohne = meta(status="nicht_konfiguriert", site=None, tage_neu=None,
                        tage_gesamt=None, klicks_zeitraum=None)
            ohne["grund"] = "GSC_SITE_URL fehlt"
            (wurzel / g.GSC / g.META).write_text(json.dumps(ohne), encoding="utf-8")
            self.assertEqual([], [str(f) for f in g.pruefe_alle(wurzel)])

    def test_gemessen_aber_liste_fehlt_ist_ein_fund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel)
            (wurzel / g.GSC / g.TOP_SEITEN).unlink()
            self.assertIn("G2", codes(g.pruefe_alle(wurzel)))


# --------------------------------------------------------------------- Heilung

@unittest.skipUnless(GIT, "git nicht verfügbar")
class HeilungTest(unittest.TestCase):
    def test_heilt_aus_dem_git_und_prueft_danach(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel)
            git_repo(wurzel)
            (wurzel / g.GSC / g.META).write_text('{\n "stand": "a"\n "stand": "b"\n}\n',
                                                 encoding="utf-8")
            self.assertTrue(g.pruefe_datei(wurzel / g.GSC / g.META))
            bericht, rest = g.heile(wurzel)
            self.assertEqual([], [str(f) for f in rest])
            self.assertTrue(any("zurückgeholt" in z for z in bericht), bericht)
            self.assertIsInstance(json.loads((wurzel / g.GSC / g.META).read_text()), dict)

    def test_ohne_belegbaren_stand_wird_nichts_erfunden(self):
        """Es gibt keinen gültigen Stand: Dann bleibt die kaputte Datei stehen.

        Genau das ist der Unterschied zwischen Heilen und Erfinden. Ein
        zusammengesetztes Messartefakt lässt sich nicht zurückrechnen – wer es
        versucht, schreibt Zahlen, die nie gemessen wurden.
        """
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel)
            kaputt = "[{\"seite\": 1}]"
            # Die kaputte Fassung ist die EINZIGE, die je committet wurde.
            (wurzel / g.GSC / g.TOP_SEITEN).write_text(kaputt, encoding="utf-8")
            git_repo(wurzel)
            bericht, rest = g.heile(wurzel)
            self.assertEqual(kaputt, (wurzel / g.GSC / g.TOP_SEITEN).read_text(encoding="utf-8"))
            self.assertTrue(any("keine Heilung" in z for z in bericht), bericht)
            self.assertIn("G2", codes(rest))

    def test_gesamtstand_ist_ganz_oder_gar_nicht(self):
        """Ein Lauf ist eine Messung: meta und beide Top-Listen aus EINEM Commit."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel, meta_daten=meta(stand="2026-10-19T10:00:00Z"))
            git_repo(wurzel)
            erster = git(wurzel, "rev-parse", "HEAD")
            satz(wurzel, meta_daten=meta(stand="2026-10-20T10:00:00Z"),
                 seiten=top("seite", ("neu",)))
            git(wurzel, "add", "-A")
            git(wurzel, "commit", "-qm", "Lauf zwei")
            bericht, rest = g.heile(wurzel, rev=erster)
            self.assertTrue(any("Gesamtstand" in z for z in bericht), bericht)
            self.assertEqual("2026-10-19T10:00:00Z",
                             json.loads((wurzel / g.GSC / g.META).read_text())["stand"])
            self.assertEqual(["a", "b"],
                             [e["seite"] for e in
                              json.loads((wurzel / g.GSC / g.TOP_SEITEN).read_text())])
            self.assertEqual([], [str(f) for f in rest])

    def test_gesamtstand_mit_kaputtem_glied_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel)
            git_repo(wurzel)
            (wurzel / g.GSC / g.TOP_SEITEN).write_text("[{\"seite\": 1}]", encoding="utf-8")
            git(wurzel, "add", "-A")
            git(wurzel, "commit", "-qm", "kaputt")
            kaputt_rev = git(wurzel, "rev-parse", "HEAD")
            vorher = (wurzel / g.GSC / g.META).read_text(encoding="utf-8")
            bericht, _ = g.heile(wurzel, rev=kaputt_rev)
            self.assertTrue(any("kein Gesamtstand" in z for z in bericht), bericht)
            self.assertEqual(vorher, (wurzel / g.GSC / g.META).read_text(encoding="utf-8"))

    def test_ledger_wird_nie_zurueckgerollt(self):
        """Tage sind unabhängige Messungen: Ein alter Stand darf keinen Tag löschen."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel)
            git_repo(wurzel)
            alter_tag = (wurzel / g.GSC / g.LEDGER).read_text(encoding="utf-8")
            with (wurzel / g.GSC / g.LEDGER).open("a", encoding="utf-8") as f:
                f.write(json.dumps({"datum": "2026-10-18", "clicks": 0, "impressions": 1,
                                    "ctr": 0.0, "position": 5.0}) + "\n")
            g.heile(wurzel, rev=git(wurzel, "rev-parse", "HEAD"))
            nachher = (wurzel / g.GSC / g.LEDGER).read_text(encoding="utf-8")
            self.assertNotEqual(alter_tag, nachher)
            self.assertIn("2026-10-18", nachher)


class VertragDerWacheTest(unittest.TestCase):
    """Die Wache darf nicht still grün melden, wenn sie nichts messen konnte."""

    def test_falscher_commit_ist_ein_bericht_und_kein_schreiben(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            satz(wurzel)
            vorher = (wurzel / g.GSC / g.META).read_text(encoding="utf-8")
            bericht, _ = g.heile(wurzel, rev="0000000000000000000000000000000000000000")
            self.assertTrue(any("nicht auflösbar" in z for z in bericht), bericht)
            self.assertEqual(vorher, (wurzel / g.GSC / g.META).read_text(encoding="utf-8"))

    def test_markdown_nennt_die_reparatur(self):
        text = g.als_markdown([g.Fund("G2", "data/gsc/meta.json", "Test")])
        self.assertIn("--heal", text)


if __name__ == "__main__":
    unittest.main()
