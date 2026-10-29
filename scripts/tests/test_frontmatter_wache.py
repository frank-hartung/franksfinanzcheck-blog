#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit-Tests der Frontmatter-Wache (scripts/frontmatter_wache.py).

Anlass: Vorgang WF-9FD5 / Meldung #901. Am 26.10.2026 starb der
Layout-AI-Lauf am Bau, weil in EINER Content-Datei ein unquotierter
Doppelpunkt stand:

    description: Stromkosten senken: Balkonkraftwerk-Förderung regional …

Hugo meldete „assemble: failed to create page from pageMetaSource",
ohne Datei und ohne Zeile – und die Meldung riet zu „API-Key abgelaufen".
Diese Tests halten drei Dinge fest:

  1. Die Klasse wird erkannt (Zeile, Spalte, Regel) – und zwar auch dann,
     wenn PyYAML im Runner FEHLT (die `hugo-build`-Action baut nackt).
  2. Die Heilung ist verlustfrei: Wert identisch, Fließtext unangetastet,
     saubere Dateien bleiben unberührt.
  3. Der Bestand ist blockerfrei – und wo PyYAML vorhanden ist, stimmt der
     Scanner mit dem echten Parser überein (keine Fehlalarme).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import frontmatter_wache as w  # noqa: E402

try:
    import yaml  # noqa: F401
    HAT_YAML = True
except ImportError:                                       # pragma: no cover
    HAT_YAML = False

# Der Originalzustand vom 26.10.2026, Zeile 2 der Datei.
KAPUTT = (
    "---\n"
    'title: "Balkonkraftwerk Förderung: So holst du dir Geld zurück"\n'
    "description: Stromkosten senken: Balkonkraftwerk-Förderung regional – "
    "Antrag und Anmeldung\n"
    "date: 2026-10-14T14:57:58Z\n"
    "draft: false\n"
    "---\n"
    "\n"
    "Annahme: Die Anlage kostet 500 Euro. Rechenbeispiel: 600 kWh im Jahr.\n"
)
SAUBER = KAPUTT.replace(
    "description: Stromkosten senken: Balkonkraftwerk-Förderung regional – "
    "Antrag und Anmeldung",
    'description: "Stromkosten senken: Balkonkraftwerk-Förderung regional – '
    'Antrag und Anmeldung"')


def pruefe(text: str, *, yaml_modul="auto") -> list:
    modul = None if yaml_modul == "ohne" else (w._yaml_modul() if yaml_modul == "auto" else yaml_modul)
    befunde, _ = w.pruefe_datei(Path("content/posts/x/index.md"), text, yaml=modul)
    return befunde


class DerAusfallVom2610Test(unittest.TestCase):
    """Die Klasse, die den Bau getötet hat."""

    def test_doppelpunkt_wird_als_blocker_gemeldet(self) -> None:
        befunde = pruefe(KAPUTT)
        blocker = [b for b in befunde if b["schwere"] == w.BLOCKER]
        self.assertTrue(blocker, "Der 26.10.2026-Fall wird NICHT erkannt")
        f3 = [b for b in blocker if b["regel"] == "F3"]
        self.assertTrue(f3, f"keine F3-Meldung: {befunde}")

    def test_zeile_und_spalte_stimmen(self) -> None:
        # Die Zeile mit dem Fehler ist Zeile 3 der Datei (Zeile 1 ist der
        # Trenner), der Doppelpunkt steht hinter `description: Stromkosten senken`.
        f3 = [b for b in pruefe(KAPUTT) if b["regel"] == "F3"][0]
        self.assertEqual(3, f3["zeile"])
        self.assertEqual(3, KAPUTT.splitlines().index(
            [z for z in KAPUTT.splitlines() if z.startswith("description:")][0]) + 1)
        self.assertEqual(KAPUTT.splitlines()[2].index(": ", 13) + 1, f3["spalte"])

    def test_ohne_pyyaml_bleibt_die_wache_scharf(self) -> None:
        """Der wichtigste Fall: Die Action baut in einem nackten Runner."""
        befunde = pruefe(KAPUTT, yaml_modul="ohne")
        self.assertTrue([b for b in befunde if b["regel"] == "F3"],
                        "Ohne PyYAML ist die Wache blind – dann ist sie im "
                        "Bau wertlos")

    def test_saubere_datei_erzeugt_keinen_blocker(self) -> None:
        self.assertEqual([], [b for b in pruefe(SAUBER) if b["schwere"] == w.BLOCKER])


class HeilungTest(unittest.TestCase):
    """Die Heilung muss beweisbar verlustfrei sein."""

    def test_wert_bleibt_zeichengleich(self) -> None:
        geheilt, belege = w.heile_datei(Path("content/posts/x/index.md"), KAPUTT)
        self.assertTrue(belege, "nichts geheilt")
        soll = ("Stromkosten senken: Balkonkraftwerk-Förderung regional – "
                "Antrag und Anmeldung")
        self.assertIn(f'description: "{soll}"', geheilt)
        if HAT_YAML:
            _, fm, _, _, _ = w.frontmatter_bereich(geheilt)
            self.assertEqual(soll, (yaml.safe_load(fm) or {})["description"])

    def test_heilt_die_wache_selbst(self) -> None:
        geheilt, _ = w.heile_datei(Path("content/posts/x/index.md"), KAPUTT)
        self.assertEqual([], [b for b in pruefe(geheilt) if b["schwere"] == w.BLOCKER])

    def test_fliess_text_wird_nie_zitiert(self) -> None:
        """Regression der Generalprobe: `Annahme: …` im Body ist Prosa."""
        geheilt, _ = w.heile_datei(Path("content/posts/x/index.md"), KAPUTT)
        self.assertIn("Annahme: Die Anlage kostet 500 Euro.", geheilt)
        self.assertNotIn('Annahme: "', geheilt)

    def test_saubere_datei_bleibt_unberuehrt(self) -> None:
        geheilt, belege = w.heile_datei(Path("content/posts/x/index.md"), SAUBER)
        self.assertEqual(SAUBER, geheilt)
        self.assertEqual([], belege)

    def test_toml_wird_nicht_angefasst(self) -> None:
        text = '+++\ntitle = "x: y"\n+++\n\nText.\n'
        geheilt, belege = w.heile_datei(Path("content/posts/x/index.md"), text)
        self.assertEqual(text, geheilt)
        self.assertEqual([], belege)


class GeruestTest(unittest.TestCase):
    def test_offenes_frontmatter_ist_ein_blocker(self) -> None:
        befunde = pruefe("---\ntitle: \"x\"\n\nText.\n")
        self.assertEqual(["F1"], [b["regel"] for b in befunde if b["schwere"] == w.BLOCKER])

    def test_toml_fehler_ist_ein_blocker(self) -> None:
        befunde = pruefe("+++\ntitle = \"x\"\ndate = \n+++\n\nText.\n")
        self.assertEqual(["F2"], [b["regel"] for b in befunde if b["schwere"] == w.BLOCKER])

    def test_json_fehler_ist_ein_blocker(self) -> None:
        befunde = pruefe('{"title": "x",}\n\nText.\n')
        self.assertTrue([b for b in befunde if b["schwere"] == w.BLOCKER])

    def test_datei_ohne_frontmatter_ist_kein_blocker(self) -> None:
        self.assertEqual([], [b for b in pruefe("# Überschrift\n\nText.\n")
                              if b["schwere"] == w.BLOCKER])


class BestandTest(unittest.TestCase):
    """Der ausgelieferte Bestand muss blockerfrei sein."""

    def test_bestand_ohne_blocker(self) -> None:
        befunde, dateien, _ = w.run(["content"])
        self.assertGreater(dateien, 50, "zu wenige Inhaltsdateien gefunden")
        blocker = [b for b in befunde if b["schwere"] == w.BLOCKER]
        self.assertEqual([], blocker, f"Blocker im Bestand: {blocker[:5]}")

    @unittest.skipUnless(HAT_YAML, "ohne PyYAML keine Gegenprobe möglich")
    def test_scanner_stimmt_mit_dem_parser_ueberein(self) -> None:
        """Kein Fehlalarm: Was PyYAML annimmt, darf der Scanner nicht sperren.

        Die Gegenrichtung gilt bewusst NICHT (der Scanner ist strenger als
        nötig nur dort, wo YAML wirklich bricht) – aber ein BLOCKER auf einer
        Datei, die Hugo klaglos baut, wäre ein Bau-Stopp ohne Grund.
        """
        falsch = []
        for pfad, anzeige in w.sammle_dateien(["content"]):
            text = pfad.read_text(encoding="utf-8")
            art, fm, start, fehler, _ = w.frontmatter_bereich(text)
            if art != "yaml" or fehler:
                continue
            try:
                yaml.safe_load(fm)
            except yaml.YAMLError:
                continue          # Parser lehnt ab – Scanner darf sperren
            blockend = [b for b in w.scanne_yaml(fm, start, anzeige)
                        if b["schwere"] == w.BLOCKER]
            if blockend:
                falsch.append((anzeige, blockend[0]["regel"], blockend[0]["meldung"]))
        self.assertEqual([], falsch, f"Fehlalarme im Bestand: {falsch[:3]}")


class CliTest(unittest.TestCase):
    """Exit-Codes sind der Vertrag mit dem Bau."""

    def _lauf(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "frontmatter_wache.py"), *args],
                              capture_output=True, text=True, cwd=cwd or ROOT)

    def test_selftest_gruen(self) -> None:
        lauf = self._lauf("--selftest")
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)

    def test_kaputte_datei_exit_1_und_kurzbefund(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "content" / "posts" / "x"
            ziel.mkdir(parents=True)
            (ziel / "index.md").write_text(KAPUTT, encoding="utf-8")
            lauf = self._lauf("--pfad", str(Path(tmp) / "content"))
            self.assertEqual(1, lauf.returncode, lauf.stdout)
            kurz = self._lauf("--pfad", str(Path(tmp) / "content"), "--kurzbefund")
            self.assertEqual(1, kurz.returncode)
            self.assertIn("index.md:3", kurz.stdout)
            self.assertEqual(1, len(kurz.stdout.strip().splitlines()))

    def test_sauber_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "content" / "posts" / "x"
            ziel.mkdir(parents=True)
            (ziel / "index.md").write_text(SAUBER, encoding="utf-8")
            self.assertEqual(0, self._lauf("--pfad", str(Path(tmp) / "content")).returncode)

    def test_streng_erhoeht_hinweise_zu_befunden(self) -> None:
        text = SAUBER.replace("draft: false", "draft: false # Prüfung offen")
        # Ein Kommentar hinter einem Einzelwort ist normaler YAML-Stil und
        # damit KEIN Hinweis – erst Prosa davor wird einer.
        self.assertEqual(0, self._lauf_mit(tmp_text=text))
        text2 = SAUBER.replace('title: "Balkonkraftwerk Förderung: So holst du dir Geld zurück"',
                               "title: Strom sparen # so geht es")
        self.assertEqual(0, self._lauf_mit(tmp_text=text2))
        self.assertEqual(1, self._lauf_mit(tmp_text=text2, extra="--streng"))

    def _lauf_mit(self, *, tmp_text: str, extra: str | None = None) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "content" / "posts" / "x"
            ziel.mkdir(parents=True)
            (ziel / "index.md").write_text(tmp_text, encoding="utf-8")
            args = ["--pfad", str(Path(tmp) / "content")]
            if extra:
                args.append(extra)
            return self._lauf(*args).returncode

    def test_json_und_md_bericht(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "content" / "posts" / "x"
            ziel.mkdir(parents=True)
            (ziel / "index.md").write_text(KAPUTT, encoding="utf-8")
            md = Path(tmp) / "bericht.md"
            lauf = self._lauf("--pfad", str(Path(tmp) / "content"),
                              "--json", "--md-datei", str(md))
            self.assertEqual(1, lauf.returncode)
            daten = json.loads(lauf.stdout)
            # Zwei Blocker sind RICHTIG: F3 (Scanner) und F2 (Parser) sehen
            # denselben Fehler aus zwei Richtungen – ein Befund, zwei Belege.
            self.assertGreaterEqual(daten["blocker"], 1)
            self.assertEqual(1, daten["dateien"])
            self.assertIn("Frontmatter-Vertrag", md.read_text(encoding="utf-8"))

    def test_fix_heilt_im_bestand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "content" / "posts" / "x"
            ziel.mkdir(parents=True)
            datei = ziel / "index.md"
            datei.write_text(KAPUTT, encoding="utf-8")
            lauf = self._lauf("--pfad", str(Path(tmp) / "content"), "--fix")
            self.assertEqual(0, lauf.returncode, lauf.stdout)
            self.assertEqual(0, self._lauf("--pfad", str(Path(tmp) / "content")).returncode)
            self.assertIn("Antrag und Anmeldung\"", datei.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
