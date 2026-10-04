#!/usr/bin/env python3
"""Markenfläche README – Regressionssperre für Vorgang WF-A4E0 (Meldung #552).

WARUM DIESE TESTS EXISTIEREN (04.10.2026)
-----------------------------------------
Das README ist die öffentliche Markenfläche des Projekts. Am 01.10. und erneut
am 03.10.2026 wanderte Betriebssprache dorthin zurück („Blogautomatik",
„Workflow-Orchestrierung", „Qualitäts-Gates", `scripts/...`). Beide Male fiel es
erst nach dem Push auf – als roter Lauf mit öffentlich sichtbarer Fehlermeldung.

Die Wache allein reicht als Antwort nicht: Sie meldete korrekt, wurde aber zu
spät gefragt. Diese Tests sichern deshalb die drei Teile der dauerhaften Lösung:

  1. Der echte Bestand ist sauber (`README.md` heute, nicht nur im Fixture).
  2. Die Commit-Sperre existiert, ist ausführbar und prüft den GESTAGETEN Stand.
  3. Das Wissen ist nicht verloren, sondern steht am richtigen Ort
     (`docs/ENTWICKLER-WERKZEUGE.md`) – sonst schreibt es der Nächste wieder ins
     README, weil es nirgends sonst zu finden ist.

Lauf: python3 -m unittest scripts.tests.test_markenflaeche_readme
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WACHE = os.path.join(WURZEL, "scripts", "brand_surface_guard.py")
README = os.path.join(WURZEL, "README.md")
HAKEN = os.path.join(WURZEL, ".githooks", "pre-commit")
ENTWICKLERDOK = os.path.join(WURZEL, "docs", "ENTWICKLER-WERKZEUGE.md")

sys.path.insert(0, os.path.join(WURZEL, "scripts"))
import brand_surface_guard as wache  # noqa: E402


def _lauf(argumente: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, WACHE, *argumente], cwd=WURZEL,
                          capture_output=True, text=True, timeout=120)


class MarkenflaecheBestand(unittest.TestCase):
    """Der echte Stand – kein Fixture kann das ersetzen."""

    def test_readme_ist_frei_von_betriebssprache(self):
        funde = wache.pruefe_readme(README, wache.lies_allowlist())
        self.assertEqual(
            [], [f"{b.text} ({b.detail})" for b in funde],
            "README.md trägt wieder Betriebssprache – technische Abschnitte "
            "gehören nach docs/ENTWICKLER-WERKZEUGE.md, Ausnahmen mit "
            "Begründung in data/brand_surface_allowlist.txt.")

    def test_gate_laeuft_offline_gruen(self):
        ergebnis = _lauf(["--only", "readme", "--gate", "--offline"])
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)

    def test_selbsttest_der_wache_bleibt_gruen(self):
        ergebnis = _lauf(["--selftest"])
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)


class GestageterStand(unittest.TestCase):
    """`--datei`: der Haken prüft, was commitet wird – nicht den Arbeitsbaum."""

    def test_saubere_fassung_ist_gruen(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "README.md")
            with open(pfad, "w", encoding="utf-8") as datei:
                datei.write("# FranksFinanzcheck\n\nUnabhängiger Finanz-Ratgeber "
                            "von Frank Hartung: Strom, Gas, DSL, Versicherungen.\n")
            self.assertEqual(0, _lauf(["--only", "readme", "--gate", "--offline",
                                       "--datei", pfad]).returncode)

    def test_betriebssprache_wird_rot(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "README.md")
            with open(pfad, "w", encoding="utf-8") as datei:
                datei.write("# FranksFinanzcheck\n\n## Blogautomatik\n"
                            "Workflow-Orchestrierung über `scripts/n8n_bridge.py`.\n")
            ergebnis = _lauf(["--only", "readme", "--gate", "--offline", "--datei", pfad])
            self.assertEqual(1, ergebnis.returncode, ergebnis.stdout)
            self.assertIn("README.md:", ergebnis.stdout)

    def test_fehlende_datei_ist_kein_gruen(self):
        ergebnis = _lauf(["--only", "readme", "--gate", "--offline",
                          "--datei", "/nicht/vorhanden/README.md"])
        self.assertEqual(2, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)

    def test_datei_ohne_only_readme_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "README.md")
            with open(pfad, "w", encoding="utf-8") as datei:
                datei.write("# FranksFinanzcheck\n")
            self.assertEqual(2, _lauf(["--gate", "--offline", "--datei", pfad]).returncode)


class CommitSperre(unittest.TestCase):
    """Eine Sperre, die niemand startet, ist Dekoration."""

    def setUp(self):
        self.assertTrue(os.path.exists(HAKEN), ".githooks/pre-commit fehlt")
        with open(HAKEN, encoding="utf-8") as datei:
            self.inhalt = datei.read()

    def test_haken_ist_ausfuehrbar(self):
        self.assertTrue(os.access(HAKEN, os.X_OK),
                        "chmod +x .githooks/pre-commit – sonst läuft der Haken nie")

    def test_haken_prueft_den_gestageten_stand(self):
        self.assertIn("git show :README.md", self.inhalt,
                      "Der Haken muss den gestageten Blob prüfen, nicht den Arbeitsbaum")
        self.assertIn("--datei", self.inhalt)
        self.assertIn("--selftest", self.inhalt,
                      "Erst der Detektor-Beweis, dann das Urteil")

    def test_haken_nennt_den_richtigen_ablageort(self):
        self.assertIn("docs/ENTWICKLER-WERKZEUGE.md", self.inhalt)
        self.assertIn("data/brand_surface_allowlist.txt", self.inhalt)

    def test_npm_skripte_vorhanden(self):
        with open(os.path.join(WURZEL, "package.json"), encoding="utf-8") as datei:
            skripte = json.load(datei)["scripts"]
        for name in ("marke:check", "test:marke", "hooks:install", "prepare"):
            self.assertIn(name, skripte, f"npm-Skript `{name}` fehlt")
        self.assertIn("core.hooksPath", skripte["hooks:install"])
        self.assertIn("core.hooksPath", skripte["prepare"],
                      "`npm install` muss die Sperre mitschalten")

    def test_haken_blockiert_einen_echten_commit(self):
        """End-to-End in einem Wegwerf-Repo: README mit Betriebssprache, Commit scheitert."""
        with tempfile.TemporaryDirectory() as ordner:
            def git(*args, pruefen=True):
                return subprocess.run(["git", "-C", ordner, *args], capture_output=True,
                                      text=True, check=pruefen)

            git("init", "-q")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Markenflächen-Test")
            os.makedirs(os.path.join(ordner, "scripts"))
            os.makedirs(os.path.join(ordner, "data"))
            os.makedirs(os.path.join(ordner, ".githooks"))
            for quelle, ziel in ((WACHE, "scripts/brand_surface_guard.py"),
                                 (os.path.join(WURZEL, "data", "brand_surface_allowlist.txt"),
                                  "data/brand_surface_allowlist.txt"),
                                 (HAKEN, ".githooks/pre-commit")):
                with open(quelle, encoding="utf-8") as lies, \
                        open(os.path.join(ordner, ziel), "w", encoding="utf-8") as schreib:
                    schreib.write(lies.read())
            os.chmod(os.path.join(ordner, ".githooks", "pre-commit"), 0o755)
            git("config", "core.hooksPath", ".githooks")

            with open(os.path.join(ordner, "README.md"), "w", encoding="utf-8") as datei:
                datei.write("# FranksFinanzcheck\n\n## Blogautomatik\n"
                            "Vollautomatische Workflows über `scripts/publish.py`.\n")
            git("add", "README.md")
            rot = git("commit", "-m", "Betriebssprache", pruefen=False)
            self.assertNotEqual(0, rot.returncode,
                                "Die Commit-Sperre hat Betriebssprache durchgelassen")
            self.assertIn("Markenflächen-Sperre", rot.stdout + rot.stderr)

            with open(os.path.join(ordner, "README.md"), "w", encoding="utf-8") as datei:
                datei.write("# FranksFinanzcheck\n\nUnabhängiger Finanz-Ratgeber von "
                            "Frank Hartung: Strom, Gas, DSL, Versicherungen.\n")
            git("add", "README.md")
            gruen = git("commit", "-m", "Markenfläche", pruefen=False)
            self.assertEqual(0, gruen.returncode,
                             f"Saubere Markenfläche wurde blockiert: "
                             f"{gruen.stdout}{gruen.stderr}")


class WissenAmRichtigenOrt(unittest.TestCase):
    """Verschoben heißt: woanders lesbar – nicht gelöscht."""

    def setUp(self):
        with open(ENTWICKLERDOK, encoding="utf-8") as datei:
            self.doku = datei.read()
        with open(README, encoding="utf-8") as datei:
            self.readme = datei.read()

    def test_technikwissen_steht_in_der_entwicklerdoku(self):
        for begriff in ("Whisper", "n8n", "blogautomatik:status"):
            self.assertIn(begriff, self.doku,
                          f"`{begriff}` ist beim Verschieben verloren gegangen")

    def test_readme_verweist_auf_die_entwicklerdoku(self):
        self.assertIn("docs/ENTWICKLER-WERKZEUGE.md", self.readme,
                      "Ohne Verweis sucht der Nächste die Technik wieder im README")

    def test_entwicklerdoku_erklaert_die_commit_sperre(self):
        self.assertIn("hooks:install", self.doku)
        self.assertIn(".githooks/pre-commit", self.doku)


if __name__ == "__main__":
    unittest.main()
