#!/usr/bin/env python3
"""Dauerheilung 14.11.2026 – Platzhalter des Leerzeichen-Generators.

DIE GESCHICHTE
--------------
`fix_spaces.py` maskierte Ziele, Domains, Marken, Abkürzungen und
Dezimalzahlen mit dem Paragrafenzeichen und stellte nach Regel D mit
`.replace("§", ".")`, nach Regel E mit `.replace("§§", ",")` zurück – also
jedes „§“ der Zeile. Griff eine der beiden Regeln, wurden

  * die Schutz-Token der Schutzzone (#1098) zerstört und nie zurückgetauscht
    („Die Datei tabelle.csv liegt bereit.Öffne sie.“ → „Die Datei .Z0. …“),
  * echte Paragrafenzeichen zu Satzzeichen („Nach § 20 EStG gilt das.Mehr“
    → „Nach . 20 EStG …“; „§§ 305 ff. BGB gilt,dass“ → „, 305 ff. …“).

Der Bestand war noch sauber, der Defekt scharf: Der Generator läuft in
`content-engine-v2.yml` und `seo-weekly.yml` über jeden Artikel.

Diese Tests frieren drei Dinge ein:
  1. Kein Platzhalter ist ein Zeichen, das im Text stehen kann.
  2. Was geschützt ist, bleibt bytegleich – auch wenn auf derselben Zeile
     eine Regel greift (Kreuzprodukt Auslöser × Schutzgut).
  3. Der ausgelieferte Bestand verliert durch den Generator kein „§“, kein
     Ziel und trägt danach kein Platzhalter-Zeichen.

Ausführung: python3 -m unittest scripts.tests.test_fix_spaces_platzhalter
"""
from __future__ import annotations

import glob
import re
import sys
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fix_spaces  # noqa: E402

# Auslöser: jede Zeile lässt genau eine Regel greifen, deren Rückstellung
# früher fremde Platzhalter mitnahm (D = Satzzeichen, E = Komma). Ein „!“
# zwischen zwei Wortteilen ist bewusst KEIN Auslöser (FRITZ!Box-Schutz).
AUSLOESER = (
    ("Ein Satz.Neuer Satz", "Ein Satz. Neuer Satz"),
    ("Stimmt das?Ja klar", "Stimmt das? Ja klar"),
    ("Hallo,Welt", "Hallo, Welt"),
)

# Schutzgut: muss bytegleich aus dem Generator kommen.
SCHUTZGUT = (
    "![Merkkarte: Kernaussagen](abbildung-merkkarte.svg)",
    "[Rechner](/werkzeuge/rechner/)",
    "[Beitrag](../2026-08-10-dsl-wechselbonus-sichern/index.md)",
    '[Angebot](https://example.de/a?b=1.5 "Titel")',
    '<img src="cover.webp" alt="Cover">',
    '<a href="https://example.de/a.html">Angebot</a>',
    "tabelle.csv",
    "www.example.de",
    "FRITZ!Box",
    "§ 20 EStG",
    "§§ 305 ff. BGB",
    "§ 309 Nr. 9 BGB",
    "3,5 %".replace(" ", "\u00a0"),
    "z. B. heute",
    "§Z0§",          # die frühere Token-Schreibweise ist gewöhnlicher Text
)

RE_ZIEL = re.compile(r"\]\([^)\n]*\)")


class PlatzhalterSindKeinText(unittest.TestCase):
    """Ein Platzhalter darf im Text nicht vorkommen können."""

    def test_platzhalter_liegen_im_privaten_bereich(self):
        self.assertEqual(len(set(fix_spaces.PLATZHALTER)),
                         len(fix_spaces.PLATZHALTER), "Platzhalter doppelt belegt")
        for zeichen in fix_spaces.PLATZHALTER:
            self.assertEqual(len(zeichen), 1)
            self.assertEqual(unicodedata.category(zeichen), "Co",
                             f"U+{ord(zeichen):04X} ist kein privates Zeichen")

    def test_keine_regel_kann_einen_platzhalter_treffen(self):
        muster = [getattr(fix_spaces, name) for name in dir(fix_spaces)
                  if name.startswith(("RE_", "ABK_RE", "BANG_RE"))
                  and name != "RE_PLATZHALTER"
                  and isinstance(getattr(fix_spaces, name), re.Pattern)]
        self.assertGreater(len(muster), 8, "Regelmuster nicht gefunden")
        for zeichen in fix_spaces.PLATZHALTER:
            for regel in muster:
                self.assertIsNone(
                    regel.fullmatch(zeichen),
                    f"{regel.pattern!r} trifft den Platzhalter U+{ord(zeichen):04X}")

    def test_quelle_stellt_kein_textzeichen_pauschal_zurueck(self):
        """Die Fehlerklasse selbst: Rückstellung über ein Zeichen des Textes."""
        quelle = (ROOT / "scripts" / "fix_spaces.py").read_text(encoding="utf-8")
        code = "\n".join(z for z in quelle.split("\n")
                         if not z.lstrip().startswith("#"))
        code = code.split("SELBSTTEST = [", 1)[0]          # Fälle sind Daten
        code = re.sub(r'"""[\s\S]*?"""', "", code)         # Docstrings sind Prosa
        self.assertNotIn("§", code,
                         "Das Paragrafenzeichen ist Text, kein Platzhalter")

    def test_token_sind_je_art_und_nummer_eindeutig(self):
        token = {fix_spaces._token(art, nr)
                 for art in ("Z", "DOM", "BANG") for nr in range(12)}
        self.assertEqual(len(token), 36)
        for a in token:
            for b in token:
                if a != b:
                    self.assertNotIn(a, b, "Ein Token steckt in einem anderen")


class SchutzgutBleibtBytegleich(unittest.TestCase):
    """Kreuzprodukt: jede greifende Regel × jedes Schutzgut, beide Reihenfolgen."""

    def _pruefe(self, eingang: str, erwartet: str):
        neu, n = fix_spaces.fix_line_safe(eingang)
        self.assertEqual(neu, erwartet)
        self.assertGreaterEqual(n, 1, "Die Regel hat nicht gegriffen")
        self.assertIsNone(fix_spaces.RE_PLATZHALTER.search(neu))
        nochmal, n2 = fix_spaces.fix_line_safe(neu)
        self.assertEqual((nochmal, n2), (neu, 0), "nicht idempotent")

    def test_schutzgut_hinter_dem_ausloeser(self):
        for kaputt, heil in AUSLOESER:
            for gut in SCHUTZGUT:
                with self.subTest(ausloeser=kaputt, schutzgut=gut):
                    self._pruefe(f"{kaputt} und {gut} am Ende",
                                 f"{heil} und {gut} am Ende")

    def test_schutzgut_vor_dem_ausloeser(self):
        for kaputt, heil in AUSLOESER:
            for gut in SCHUTZGUT:
                if gut.startswith(("[Angebot](https://", "<a href")):
                    # Eine nackte http(s)-URL schützt bewusst den Rest der
                    # Zeile (RE_URL, Altbestand mit Leerzeichen in URLs).
                    # Das ist Zurückhaltung, kein Schaden – eigener Test unten.
                    continue
                with self.subTest(ausloeser=kaputt, schutzgut=gut):
                    self._pruefe(f"Erst {gut} und dann: {kaputt}",
                                 f"Erst {gut} und dann: {heil}")

    def test_url_schuetzt_den_zeilenrest_ohne_schaden(self):
        for gut in SCHUTZGUT:
            if not gut.startswith(("[Angebot](https://", "<a href")):
                continue
            for kaputt, _heil in AUSLOESER:
                zeile = f"Erst {gut} und dann: {kaputt}"
                neu, _n = fix_spaces.fix_line_safe(zeile)
                self.assertIn(gut, neu)
                self.assertIsNone(fix_spaces.RE_PLATZHALTER.search(neu))

    def test_mehrere_schutzgueter_auf_einer_zeile(self):
        zeile = ("Laut § 309 Nr. 9 BGB kündigst du monatlich.Mehr im "
                 "[Rechner](/werkzeuge/rechner/), in tabelle.csv,auf "
                 "www.example.de und zur FRITZ!Box.")
        soll = ("Laut § 309 Nr. 9 BGB kündigst du monatlich. Mehr im "
                "[Rechner](/werkzeuge/rechner/), in tabelle.csv,auf "
                "www.example.de und zur FRITZ!Box.")
        self.assertEqual(fix_spaces.fix_line_safe(zeile)[0], soll)

    def test_zwoelf_ziele_tauschen_sich_nicht_ineinander(self):
        """Token 1 darf nicht in Token 10/11 stecken (Rücktausch per replace)."""
        ziele = " ".join(f"[L{i}](/ziel-{i}/a.html)" for i in range(12))
        neu, _ = fix_spaces.fix_line_safe(f"Satz.Neuer Satz {ziele}")
        self.assertEqual(neu, f"Satz. Neuer Satz {ziele}")

    def test_tabellenzeile_behaelt_paragraf_und_ziel(self):
        zeile = "| § 20 EStG | [Rechner](/werkzeuge/rechner/) | 25 % | z.B. Zinsen |"
        neu, _ = fix_spaces.fix_body(zeile)
        self.assertEqual(
            neu, "| § 20 EStG | [Rechner](/werkzeuge/rechner/) | 25\u00a0% | z. B. Zinsen |")


class FailClosed(unittest.TestCase):
    """Unterscheidbarkeit verloren → Zeile bleibt, wie sie ist."""

    def test_zeile_mit_platzhalter_bleibt_unberuehrt(self):
        for zeichen in fix_spaces.PLATZHALTER:
            zeile = f"Fremdes {zeichen} Zeichen.Bleibt,so"
            self.assertEqual(fix_spaces.fix_line_safe(zeile), (zeile, 0))
            self.assertEqual(fix_spaces.fix_body(zeile), (zeile, 0))
            self.assertEqual(fix_spaces.fix_body(f"| {zeile} | 5 % |"),
                             (f"| {zeile} | 5 % |", 0))

    def test_beschaedigtes_token_verwirft_die_aenderung(self):
        """Verliert eine Regel ein Token, bleibt das Original stehen."""
        original = fix_spaces.fix_line

        def kaputte_regel(zeile):
            neu, n = original(zeile)
            return neu.replace(fix_spaces.T_ZU, ""), n + 1

        fix_spaces.fix_line = kaputte_regel
        try:
            zeile = "Satz.Neuer Satz mit [Rechner](/werkzeuge/rechner/)"
            self.assertEqual(fix_spaces.fix_line_safe(zeile), (zeile, 0))
        finally:
            fix_spaces.fix_line = original


class BestandVerliertNichts(unittest.TestCase):
    """Der Generator über den echten Bestand: kein „§“, kein Ziel geht verloren."""

    def test_bestand(self):
        dateien = (sorted(glob.glob(str(ROOT / "content" / "posts" / "*" / "index.md")))
                   + sorted(glob.glob(str(ROOT / "content" / "pillar" / "*" / "index.md"))))
        self.assertGreater(len(dateien), 50, "Bestand nicht gefunden")
        for datei in dateien:
            text = Path(datei).read_text(encoding="utf-8")
            teile = text.split("---", 2)
            if len(teile) < 3:
                continue
            body = teile[2]
            neu, _ = fix_spaces.fix_body(body)
            name = Path(datei).parent.name
            self.assertIsNone(fix_spaces.RE_PLATZHALTER.search(neu),
                              f"{name}: Platzhalter im Ergebnis")
            self.assertEqual(neu.count("§"), body.count("§"),
                             f"{name}: Paragrafenzeichen verändert")
            self.assertEqual(RE_ZIEL.findall(neu), RE_ZIEL.findall(body),
                             f"{name}: Markdown-Ziel verändert")
            self.assertEqual(fix_spaces.fix_body(neu), (neu, 0),
                             f"{name}: nicht idempotent")


if __name__ == "__main__":
    unittest.main()
