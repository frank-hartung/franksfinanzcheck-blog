#!/usr/bin/env python3
"""Haken-Wächter – Regressionssperre für die Selbstscharfstellung (WF-A4E0 / #552).

WARUM DIESE TESTS EXISTIEREN (04.10.2026)
-----------------------------------------
Die Commit-Sperre `.githooks/pre-commit` ist die erste von vier Schichten gegen
Betriebssprache im README. Nach der ersten Heilung blieb ein Rest: Git führt
mitgelieferte Haken nie von selbst aus – „einmal pro Arbeitskopie
`npm run hooks:install`" war eine Bitte, keine Leitplanke. Eine vergessene Bitte
fällt erst nach dem Push auf, also genau dort, wo es öffentlich wird.

`scripts/haken_wache.py` stellt die Sperre deshalb selbst scharf, an jedem
Eingang, den eine Arbeitskopie realistisch nimmt. Diese Tests sichern, dass das
Verfahren erhalten bleibt – auch gegen die typischen Rückfälle:

  1. Die Selbstscharfstellung wirkt und ist nachgeprüft (nicht nur gesetzt).
  2. Die Einhängung legt KEINE anderen Haken still (der erste Weg über
     `core.hooksPath` tat genau das – lautlos).
  3. Die Verdrahtung in package.json bleibt bestehen: `prepare`, jeder
     Marken-Lauf, `hooks:install` – fällt eine Zeile weg, fällt es hier auf.
  4. Das Wissen steht in der Entwicklerdoku, nicht im README (Markenfläche).

Lauf: python3 -m unittest scripts.tests.test_haken_wache
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WAECHTER = os.path.join(WURZEL, "scripts", "haken_wache.py")
PAKET = os.path.join(WURZEL, "package.json")
ENTWICKLERDOK = os.path.join(WURZEL, "docs", "ENTWICKLER-WERKZEUGE.md")
README = os.path.join(WURZEL, "README.md")

sys.path.insert(0, os.path.join(WURZEL, "scripts"))
import haken_wache as wache  # noqa: E402


def _lauf(argumente: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, WAECHTER, *argumente], cwd=WURZEL,
                          capture_output=True, text=True, timeout=300)


class SelbsttestLaeuft(unittest.TestCase):
    """Der Wächter beweist sich zuerst selbst – in echten Wegwerf-Repos."""

    def test_selbsttest_gruen(self):
        ergebnis = _lauf(["--selftest"])
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("Fallgruppen bestanden", ergebnis.stdout)


class ScharfstellenWirkt(unittest.TestCase):
    """Vom frischen Klon zur wirksamen Sperre – ohne Zutun eines Menschen."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.ordner.name, "kopie")
        wache._wegwerf_repo(self.repo, mit_wache=True)

    def tearDown(self):
        self.ordner.cleanup()

    def test_frische_arbeitskopie_ist_nicht_scharf(self):
        self.assertFalse(wache.befund(self.repo)["scharf"],
                         "Ein frischer Klon darf nicht als geschützt gelten – "
                         "sonst wiegt der Befund in falscher Sicherheit")

    def test_install_stellt_scharf_und_liest_zurueck(self):
        zustand, getan = wache.scharfstellen(self.repo)
        self.assertEqual(wache.NACHGEZOGEN, zustand["zustand"])
        self.assertTrue(zustand["scharf"])
        self.assertTrue(getan, "Scharfstellen ohne berichteten Schritt")
        # Nachprüfung aus zweiter Hand: der reine Befund sieht es genauso.
        self.assertTrue(wache.befund(self.repo)["scharf"])

    def test_sperre_haelt_betriebssprache_wirklich_auf(self):
        wache.scharfstellen(self.repo)
        rot = wache._commit_versuch(self.repo, wache.BETRIEBSSPRACHE)
        self.assertNotEqual(0, rot.returncode,
                            "Die scharfe Sperre ließ Betriebssprache durch")
        self.assertIn("Markenflächen-Sperre", rot.stdout + rot.stderr)

    def test_saubere_markenflaeche_bleibt_frei(self):
        wache.scharfstellen(self.repo)
        gruen = wache._commit_versuch(self.repo, wache.MARKENTEXT)
        self.assertEqual(0, gruen.returncode,
                         f"Saubere Markenfläche wurde blockiert: {gruen.stderr}")

    def test_zweiter_lauf_aendert_nichts(self):
        wache.scharfstellen(self.repo)
        zustand, getan = wache.scharfstellen(self.repo)
        self.assertEqual(wache.SCHARF, zustand["zustand"])
        self.assertEqual([], getan, "Der Wächter arbeitet bei jedem Lauf erneut")

    def test_check_meldet_unscharf_mit_exit_1(self):
        ergebnis = subprocess.run(
            [sys.executable, WAECHTER, "--check", "--wurzel", self.repo],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(1, ergebnis.returncode)
        self.assertIn("NICHT scharf", ergebnis.stdout)


class AndereHakenBleibenAmLeben(unittest.TestCase):
    """Der eigentliche Rückfall, den es zu verhindern gilt: stille Stilllegung."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.ordner.name, "kopie")
        wache._wegwerf_repo(self.repo, mit_wache=True)
        self.spur = os.path.join(self.repo, "spur.txt")

    def tearDown(self):
        self.ordner.cleanup()

    def _eigenen_haken_legen(self, name: str):
        ordner = os.path.join(self.repo, ".git", "hooks")
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, name)
        with open(pfad, "w", encoding="utf-8") as datei:
            datei.write(f"#!/bin/sh\necho {name} >> {self.spur}\n")
        os.chmod(pfad, 0o755)
        return pfad

    def test_vorhandener_pre_commit_wird_bewahrt_und_laeuft_weiter(self):
        self._eigenen_haken_legen("pre-commit")
        wache.scharfstellen(self.repo)
        wache._commit_versuch(self.repo, wache.MARKENTEXT)
        self.assertTrue(os.path.exists(self.spur),
                        "Der vorhandene Haken wurde überschrieben statt bewahrt")

    def test_fremde_haken_werden_nicht_stillgelegt(self):
        self._eigenen_haken_legen("commit-msg")
        wache.scharfstellen(self.repo)
        wache._commit_versuch(self.repo, wache.MARKENTEXT)
        self.assertTrue(os.path.exists(self.spur),
                        "commit-msg wurde durch die Einhängung stillgelegt – "
                        "genau das war der Fehler des ersten Weges")

    def test_altbestand_mit_hookspath_zieht_um_wenn_er_haken_stilllegt(self):
        subprocess.run(["git", "-C", self.repo, "config", "core.hooksPath",
                        wache.ABLAGE], check=True, timeout=30)
        self._eigenen_haken_legen("commit-msg")
        zustand, getan = wache.scharfstellen(self.repo)
        self.assertEqual("weiterleitung", zustand["weg"])
        self.assertEqual("", wache.hookspath_einstellung(self.repo))
        self.assertTrue(any("core.hooksPath" in schritt for schritt in getan),
                        "Der Umzug muss begründet im Protokoll stehen")

    def test_fremdes_hakenwerkzeug_wird_nicht_angefasst(self):
        os.makedirs(os.path.join(self.repo, ".husky"), exist_ok=True)
        subprocess.run(["git", "-C", self.repo, "config", "core.hooksPath",
                        ".husky"], check=True, timeout=30)
        zustand, getan = wache.scharfstellen(self.repo)
        self.assertEqual(wache.FREMD, zustand["zustand"])
        self.assertEqual([], getan)
        self.assertEqual(".husky", wache.hookspath_einstellung(self.repo))
        self.assertTrue(wache._reparaturweg(zustand),
                        "Fremde Ablage ohne Reparaturweg wäre eine Sackgasse")


class KeinSchadenAnSonderfaellen(unittest.TestCase):
    """Ein Wächter darf nirgends im Weg stehen."""

    def test_ohne_git_arbeitsbaum_bleibt_der_lauf_gruen(self):
        with tempfile.TemporaryDirectory() as ordner:
            os.makedirs(os.path.join(ordner, wache.ABLAGE))
            with open(os.path.join(ordner, wache.ABLAGE, "pre-commit"), "w") as datei:
                datei.write("#!/bin/sh\nexit 0\n")
            ergebnis = subprocess.run(
                [sys.executable, WAECHTER, "--install", "--leise", "--wurzel", ordner],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(0, ergebnis.returncode,
                             "npm install darf an einem Export nicht scheitern")

    def test_json_bericht_ist_maschinenlesbar(self):
        ergebnis = _lauf(["--status", "--json"])
        self.assertEqual(0, ergebnis.returncode)
        daten = json.loads(ergebnis.stdout)
        for feld in ("zustand", "scharf", "hakenordner", "weg"):
            self.assertIn(feld, daten)


class VerdrahtungBleibtBestehen(unittest.TestCase):
    """Eine Leitplanke, die niemand aufruft, ist keine."""

    def setUp(self):
        with open(PAKET, encoding="utf-8") as datei:
            self.paket = json.load(datei)
        self.skripte = self.paket["scripts"]

    def test_npm_install_stellt_scharf(self):
        self.assertIn("haken_wache.py", self.skripte.get("prepare", ""),
                      "`prepare` ist der Eingang, den jede Arbeitskopie nimmt")
        self.assertIn("--install", self.skripte["prepare"])

    def test_marken_lauf_stellt_scharf(self):
        self.assertIn("haken_wache.py", self.skripte["marke:check"],
                      "Wer die Markenfläche prüft, soll die Sperre gleich "
                      "mitbekommen – ohne daran zu denken")

    def test_hooks_befehle_stehen_bereit(self):
        for name in ("hooks:install", "hooks:status", "hooks:check", "test:haken"):
            self.assertIn(name, self.skripte, f"npm-Skript `{name}` fehlt")
            self.assertIn("haken_wache.py", self.skripte[name])

    def test_marken_tests_fahren_den_waechter_mit(self):
        self.assertIn("haken_wache.py --selftest", self.skripte["test:marke"])


class WissenAmRichtigenOrt(unittest.TestCase):
    """Dokumentiert wird in der Entwicklerdoku – nie auf der Markenfläche."""

    def setUp(self):
        with open(ENTWICKLERDOK, encoding="utf-8") as datei:
            self.doku = datei.read()
        with open(README, encoding="utf-8") as datei:
            self.readme = datei.read()

    def test_entwicklerdoku_erklaert_die_selbstscharfstellung(self):
        for begriff in ("haken_wache.py", "hooks:status", "pre-commit.lokal"):
            self.assertIn(begriff, self.doku,
                          f"`{begriff}` fehlt in docs/ENTWICKLER-WERKZEUGE.md")

    def test_readme_bleibt_frei_von_der_technik(self):
        self.assertNotIn("haken_wache", self.readme,
                         "Das README ist Markenfläche – Technik gehört in die Doku")


if __name__ == "__main__":
    unittest.main()
