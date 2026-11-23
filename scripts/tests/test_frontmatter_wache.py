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
    # "ohne" heißt jetzt wirklich ohne: `None` bedeutet im Prüfer „nimm, was
    # da ist“, `False` heißt „bewusst kein Parser“. Vorher war der Zweig ein
    # No-Op und die Tests liefen still mit PyYAML.
    modul = False if yaml_modul == "ohne" else (w._yaml_modul() if yaml_modul == "auto" else yaml_modul)
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


class DoppelterSchluesselToetetDenBauTest(unittest.TestCase):
    """Der Fall vom 01.11.2026 (WF-990) – er hat `main` unbebaubar gemacht.

    Beim Squash-Merge von PR #1004 entstand in einer Datei eine zweite
    `description`-Zeile. Der Wächter sah sie, stufte sie aber als HINWEIS
    ein („YAML nimmt still den letzten Wert") – für PyYAML richtig, für
    Hugo falsch: Hugo bricht mit „mapping key already defined" ab. Der
    Schritt blieb grün, der Merge ging durch, `main` war tot.

    Die Lehre steht im zweiten Test: Die Doppelt-Prüfung ist die EINZIGE
    Instanz, die den Fall sieht. Der YAML-Parser verschweigt ihn, weil er
    den letzten Wert nimmt und den ersten still verwirft. Deshalb ist sie
    BLOCKER und nicht Hinweis – ein Befund, der den Bau tötet, darf kein
    Hinweis sein.
    """

    KAPUTT_DOPPELT = SAUBER.replace(
        "draft: false", "draft: false\ndescription: \"zweite Angabe\"")

    def test_ist_ein_blocker_nicht_bloss_ein_hinweis(self) -> None:
        befunde = pruefe(self.KAPUTT_DOPPELT)
        doppelt = [b for b in befunde if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "doppelter Schlüssel wird nicht erkannt")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"],
                         "ein Duplikat toetet den Hugo-Bau – es ist ein Blocker")

    # GEGENPROBE 21.11.2026: Der Falschbefund, der `main` lahmlegte.
    # ------------------------------------------------------------------
    # Am 19.11.2026 kam ein Artikel mit drei Quellen in einer Liste in den
    # Bestand:
    #     quellen:
    #     - id: Q1
    #     - id: Q3
    #     - id: Q5
    # Der Scanner entfernte das `- ` und zählte `id` dreimal als Schlüssel
    # derselben Ebene -> F3-BLOCKER. Der Bau blieb stehen, obwohl die Datei
    # einwandfrei baut. Diese drei Tests halten die Grenze fest: Listen sind
    # keine Duplikate, echte Duplikate bleiben Blocker.
    LISTE = SAUBER.replace(
        "draft: false",
        "draft: false\nquellen:\n- id: Q1\n  titel: Eins\n"
        "- id: Q3\n  titel: Drei\n- id: Q5\n  titel: Fünf")

    def test_listeneintraege_sind_keine_doppelten_schluessel(self) -> None:
        befunde = pruefe(self.LISTE)
        doppelt = [b for b in befunde if "steht doppelt" in b["meldung"]]
        self.assertEqual([], doppelt,
                         "dieselbe Kennung in MEHREREN Listen-Einträgen ist kein "
                         "doppelter Mapping-Schlüssel – die Datei baut")

    def test_listeneintraege_bleiben_auch_ohne_pyyaml_still(self) -> None:
        befunde = pruefe(self.LISTE, yaml_modul="ohne")
        self.assertEqual([], [b for b in befunde if "steht doppelt" in b["meldung"]])

    @unittest.skipUnless(HAT_YAML, "ohne PyYAML keine Gegenprobe möglich")
    def test_listengegenprobe_gegen_den_parser(self) -> None:
        """Was der Parser strikt ohne Duplikat liest, darf kein Blocker sein."""
        self.assertIsNotNone(yaml.safe_load(self.LISTE.split("---")[1]))

    def test_echtes_duplikat_neben_liste_bleibt_blocker(self) -> None:
        """Die Verschärfung darf nicht mit der Liste verschwinden."""
        text = self.LISTE.replace(
            "draft: false", "draft: false\ndescription: \"zweite Angabe\"")
        doppelt = [b for b in pruefe(text) if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "echtes Duplikat neben einer Liste bleibt unentdeckt")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])

    def test_ohne_pyyaml_ebenso_scharf(self) -> None:
        befunde = pruefe(self.KAPUTT_DOPPELT, yaml_modul="ohne")
        doppelt = [b for b in befunde if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "ohne PyYAML ist der Fall unsichtbar")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])

    def test_der_yaml_parser_ist_hier_blind(self) -> None:
        """Gegenprobe, die den Grund für die Einstufung festhält.

        Wenn ein YAML-Parser diesen Text anstandslos parst, dann NUR, weil
        er den ersten Wert still wegwirft. Genau darum darf man sich bei
        dieser Klasse nicht auf ihn verlassen – und genau darum steht die
        Prüfung ohne Parser (Schicht 1).
        """
        try:
            import yaml  # noqa: F401
        except ImportError:  # pragma: no cover – nackter Runner
            self.skipTest("PyYAML fehlt")
        import yaml
        fm = self.KAPUTT_DOPPELT.split("---\n")[1]
        daten = yaml.safe_load(fm)          # kein Fehler …
        # … und der erste Wert ist still weg. Das ist der Grund, warum der
        # Wächter hier NICHT auf den Parser baut.
        self.assertEqual("zweite Angabe", daten["description"])
        self.assertEqual(2, fm.count("description:"),
                         "hier müssen zwei Angaben im Text stehen – sonst "
                         "belegt der Test nichts")
        self.assertEqual(2, sum(1 for z in self.KAPUTT_DOPPELT.splitlines()
                                if z.startswith("description:")),
                         "und der Scanner muss genau zwei Zeilen sehen")


class SequenzSchluesselSindKeinDuplikatTest(unittest.TestCase):
    """WF-B16A/#1291 (21.11.2026): Gleich benannte Schlüssel in Listen.

    DER FEHLALARM: Ein `quellen:`-Block listet je Eintrag `id`, `titel`,
    `url`. Das ist gültiges YAML – jeder Eintrag ist ein EIGENES Mapping.
    Der Scanner schnitt den Eintragsmarker `- ` ab, BEVOR er die
    Doppelt-Prüfung fragte (`rest_zeile.startswith("-")` war danach immer
    falsch). Ergebnis: „Schlüssel `id` steht doppelt" als BLOCKER auf einer
    Datei, die PyYAML und Hugo fehlerfrei lesen. Der Fehlalarm stand ab
    20.11.2026 auf `main` (Nachlauf-Wache #1285/#1287) und hätte jeden
    Artikel mit Quellenliste als unbaubar gebrandmarkt.

    Beide Richtungen werden geprüft: kein Fehlalarm auf Listen – und die
    echte Erkennung bleibt scharf (sonst wäre der Fehlalarm gegen einen
    Blindfleck getauscht, und genau davor warnt der Test oben).
    """

    QUELLEN = (
        "---\n"
        'title: "Probe"\n'
        'description: "Eine ausreichend lange Beschreibung für das Snippet."\n'
        "date: 2026-11-21T00:00:00Z\n"
        "draft: false\n"
        "quellen:\n"
        '  - id: "Q1"\n'
        '    titel: "Bundesnetzagentur"\n'
        '    url: "https://example.org/a"\n'
        '  - id: "Q2"\n'
        '    titel: "Verbraucherzentrale"\n'
        '    url: "https://example.org/b"\n'
        '  - id: "Q3"\n'
        '    titel: "Gesetze im Internet"\n'
        '    url: "https://example.org/c"\n'
        "---\n\nText.\n")

    def test_gleiche_schluessel_in_mehreren_eintraegen_sind_kein_blocker(self):
        befunde = pruefe(self.QUELLEN)
        doppelt = [b for b in befunde if "steht doppelt" in b["meldung"]]
        self.assertEqual([], doppelt,
                         "drei Quellen mit je eigenem `id` sind gültiges YAML – "
                         "kein Duplikat, kein Blocker")

    def test_ohne_pyyaml_kein_fehlalarm(self):
        befunde = pruefe(self.QUELLEN, yaml_modul="ohne")
        self.assertEqual([], [b for b in befunde if "steht doppelt" in b["meldung"]])

    def test_blocksequenz_mit_eingebettetem_eintrag(self):
        text = self.QUELLEN.replace(
            '  - id: "Q2"', "  -\n    id: \"Q2\"").replace(
            '  - id: "Q3"', "  -\n    id: \"Q3\"")
        self.assertEqual([], [b for b in pruefe(text)
                              if "steht doppelt" in b["meldung"]])

    def test_echtes_duplikat_bleibt_scharf(self):
        """Gegenprobe: Die Reparatur darf die Erkennung nicht abschalten."""
        befunde = pruefe(SAUBER.replace("draft: false",
                                        "draft: false\ndraft: true"))
        self.assertTrue([b for b in befunde if "steht doppelt" in b["meldung"]],
                        "ein echtes Duplikat auf oberster Ebene muss Blocker bleiben")

    def test_bestand_hat_keinen_quellen_fehlalarm(self):
        """Der konkrete Artikel, an dem der Fehlalarm auffiel (Hugo baut ihn)."""
        pfad = (ROOT / "content" / "posts"
                / "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen"
                / "index.md")
        if not pfad.is_file():
            self.skipTest("Artikel nicht vorhanden")
        befunde = pruefe(pfad.read_text(encoding="utf-8"))
        self.assertEqual([], [b for b in befunde if "steht doppelt" in b["meldung"]])


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


class DeutschesSchlusszeichenTest(unittest.TestCase):
    """Die Klasse, die am 29.10.2026 auf `main` stand (#941).

    Eine Textumformung ersetzte das deutsche Schlusszeichen „ durch ein
    ASCII-Zeichen: `"… Klasse „heilbar" ist heilbar …"`. Das erste `"`
    beendet den YAML-Wert zu früh – Hugo bricht ab, und der Deploy steht.
    """

    # Ausgangspunkt ist die SAUBERE Fassung – ihr Wert ist korrekt zitiert.
    # Genau dieses Zitat wird durch die fehlerhafte Umformung ersetzt.
    TEXT = SAUBER.replace(
        'description: "Stromkosten senken: Balkonkraftwerk-Förderung regional – '
        'Antrag und Anmeldung"',
        'description: "Klasse \u201eheilbar" ist heilbar, mit Nachweis."')

    def test_wird_erkannt(self) -> None:
        befunde = [b for b in pruefe(self.TEXT) if b["regel"] == "F3"]
        self.assertTrue(befunde, "Text hinter dem schließenden Zitat bleibt unentdeckt")
        self.assertIn("schließenden Anführungszeichen", befunde[0]["meldung"])

    def test_wird_ohne_pyyaml_erkannt(self) -> None:
        befunde = [b for b in pruefe(self.TEXT, yaml_modul="ohne")
                   if b["regel"] == "F3"]
        self.assertTrue(befunde, "ohne PyYAML ist die Klasse unsichtbar")

    def test_heilung_setzt_das_deutsche_schlusszeichen(self) -> None:
        geheilt, belege = w.heile_datei(Path("content/posts/x/index.md"), self.TEXT)
        self.assertTrue(belege)
        self.assertIn('description: "Klasse \u201eheilbar\u201c ist heilbar, mit Nachweis."',
                      geheilt)
        self.assertEqual([], [b for b in pruefe(geheilt) if b["schwere"] == w.BLOCKER])
        # Der Text selbst wird nicht umgeschrieben – nur das eine Zeichen.
        self.assertIn("ist heilbar, mit Nachweis.", geheilt)


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


class VerschachtelterDoppelterSchluesselTest(unittest.TestCase):
    """Issue #1313 (22.11.2026): Duplikate UNTERHALB von Einrückung 0.

    Der Fall vom 21.11.2026: In `redaktionelle_pruefung` stand
    `aenderungsgrund` zweimal – zwei Zeilen mit Einrückung 2. Der
    Textscanner prüfte Duplikate nur bei `einzug == 0` und schwieg;
    PyYAML nahm still den letzten Wert; Hugo brach `main` den Bau ab.
    Der strenge Loader liest das Frontmatter deshalb mit
    Ebenen-Gedächtnis – der Parser kennt die Verschachtelung, der
    Zeilenscanner muss sie raten.
    """

    VERSCHACHTELT = SAUBER.replace(
        "draft: false",
        "draft: false\n"
        "redaktionelle_pruefung:\n"
        "  pruefdatum: 2026-11-21\n"
        "  aenderungsgrund: Erstprüfung\n"
        "  aenderungsgrund: Zweitprüfung")

    def test_verschachteltes_duplikat_ist_blocker(self) -> None:
        befunde = pruefe(self.VERSCHACHTELT)
        doppelt = [b for b in befunde if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "verschachteltes Duplikat bleibt unentdeckt")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])
        self.assertIn("aenderungsgrund", doppelt[0]["meldung"])

    def test_auch_ohne_pyyaml_scharf(self) -> None:
        """Der CI-Schritt läuft VOR dem `pip install` – dort gibt es kein PyYAML.

        Genau deshalb prüft der Scanner die Ebenen selbst: Ein Wächter, der
        nur mit Parser scharf ist, ist im entscheidenden Lauf stumpf.
        """
        doppelt = [b for b in pruefe(self.VERSCHACHTELT, yaml_modul="ohne")
                   if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "ohne PyYAML bleibt #1313 unsichtbar")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])
        self.assertIn("aenderungsgrund", doppelt[0]["meldung"])

    @unittest.skipUnless(HAT_YAML, "ohne PyYAML keine Ebenen-Prüfung")
    def test_zeile_zeigt_auf_das_zweite_vorkommen(self) -> None:
        befunde = pruefe(self.VERSCHACHTELT)
        doppelt = [b for b in befunde if "steht doppelt" in b["meldung"]][0]
        zeilen = self.VERSCHACHTELT.splitlines()
        # Die gemeldete Zeile muss die ZWEITE Angabe sein – dort bricht Hugo.
        self.assertIn("Zweitprüfung", zeilen[doppelt["zeile"] - 1])
        self.assertEqual("aenderungsgrund", doppelt["meldung"].split("`")[1])

    def test_gleicher_schluessel_in_verschiedenen_bloecken_ist_kein_duplikat(self) -> None:
        """`a.x` und `b.x` sind zwei Mappings – YAML erlaubt das."""
        text = SAUBER.replace(
            "draft: false",
            "draft: false\n"
            "quelle_a:\n  id: Q1\n"
            "quelle_b:\n  id: Q2")
        self.assertEqual([], [b for b in pruefe(text)
                              if "steht doppelt" in b["meldung"]])

    def test_listen_mit_gleichen_schluesseln_bleiben_still(self) -> None:
        """Die #1291-Gegenprobe gilt auch unterhalb von Einrückung 0."""
        text = SAUBER.replace(
            "draft: false",
            "draft: false\n"
            "redaktionelle_pruefung:\n  quellen:\n"
            "  - id: Q1\n    titel: Eins\n"
            "  - id: Q3\n    titel: Drei\n"
            "  - id: Q5\n    titel: Fünf")
        self.assertEqual([], [b for b in pruefe(text)
                              if "steht doppelt" in b["meldung"]])

    def test_duplikat_im_selben_listen_eintrag(self) -> None:
        """#1329-Idee, hier gegen die Bereichsprüfung verifiziert.

        Zwei `id` im SELBEN Eintrag sind ein Duplikat; zwei `id` in
        verschiedenen Einträgen nicht (Gegenprobe steht darüber).
        """
        text = SAUBER.replace(
            "draft: false", "draft: false\nquellen:\n- id: Q1\n  id: Q2")
        doppelt = [b for b in pruefe(text) if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "Duplikat im selben Listen-Eintrag bleibt unentdeckt")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])

    def test_duplikat_im_selben_listen_eintrag_ohne_parser(self) -> None:
        doppelt = [b for b in pruefe(
            SAUBER.replace("draft: false",
                           "draft: false\nquellen:\n- id: Q1\n  id: Q2"),
            yaml_modul="ohne") if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "Scanner verliert das Duplikat im Listen-Eintrag")

    @unittest.skipUnless(HAT_YAML, "Flow-Mappings liest nur der Parser")
    def test_duplikat_im_flow_mapping(self) -> None:
        """Bekannte Grenze des Scanners – hier als Parser-Beleg festgehalten."""
        text = SAUBER.replace("draft: false", 'draft: false\nmeta: {a: "1", a: "2"}')
        doppelt = [b for b in pruefe(text) if "steht doppelt" in b["meldung"]]
        self.assertTrue(doppelt, "Flow-Mapping-Duplikat bleibt unentdeckt")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])

    def test_top_level_duplikat_bleibt_erkannt(self) -> None:
        """Die Verschärfung darf den WF-990-Fall nicht verlieren."""
        doppelt = [b for b in pruefe(DoppelterSchluesselToetetDenBauTest.KAPUTT_DOPPELT)
                   if "steht doppelt" in b["meldung"]]
        self.assertEqual(1, len(doppelt), "ein Duplikat, nicht zwei Meldungen")
        self.assertEqual(w.BLOCKER, doppelt[0]["schwere"])

    def test_scanner_kuerzt_normale_schluessel_nicht_ab(self) -> None:
        """#1230-Regression: Ein verirrtes `rest_zeile[2:]` im else-Zweig
        kappte `title:` zu `tle:` und `date:` zu `te:` – F5 und F4 fielen
        im Scanner still aus und ließen `frontmatter_wache.py --selftest`
        in `content-reserve.yml` rot laufen.
        """
        fm_yes = 'title: yes\ndate: 2026-10-26\ndraft: false\n'
        befunde_yes = w.scanne_yaml(fm_yes, 2, "probe.md")
        self.assertIn("F5", [b["regel"] for b in befunde_yes],
                      "Scanner muss `title: yes` ohne PyYAML als F5 erkennen")

        fm_date = 'title: "Sauber"\ndate: 2026/10/26\ndraft: false\n'
        befunde_date = w.scanne_yaml(fm_date, 2, "probe.md")
        self.assertIn("F4", [b["regel"] for b in befunde_date],
                      "Scanner muss unzulässiges `date` ohne PyYAML als F4 erkennen")


if __name__ == "__main__":
    unittest.main()
