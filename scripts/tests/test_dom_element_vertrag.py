"""#900: Der Laufzeit-DOM kostet höchstens zwei Elemente je Überschrift.

WARUM DIESER VERTRAG EXISTIERT
------------------------------
Der Layout-Audit hatte am 30.10.2026 genau ein Problem, das kein Fehler war,
sondern eine Summe: Die längste Artikelseite lieferte 1033 Elemente aus und
hatte zur Laufzeit **1401**. Die 368 zusätzlichen Elemente kamen aus
`static/premium/ff-premium.js` – und fast alle aus einer einzigen Stelle:

  je Überschrift  1 × `<span class="ff-heading-text">`
                + 1 × `<button class="ff-heading-copy">`
                + 1 × `<svg>` + 3 × `<path>`           ← 4 Knoten für ein Symbol
                ---------------------------------------
                = 6 Elemente × 48 Überschriften = 288

Dazu kamen TOC-Knoten (Titel-`<span>` je Eintrag) und ein Griff aus `<svg>`
mit sechs `<circle>`. Das Symbol gehört ins Stylesheet, nicht in den DOM:
Seit #900 zeichnet CSS es als Maske (`::before`), der Kopier-Zustand ist die
Klasse `.ff-copied`, der Griff ist ein `radial-gradient`, der TOC-Titel ein
Textknoten. Ergebnis: 1033 + 162 = **1195** statt 1401.

WAS HIER GEPRÜFT WIRD
---------------------
1. Je Überschrift entstehen höchstens ZWEI Elemente (Etikett + Knopf).
2. Im Knopf wird nichts mehr per `innerHTML` gesetzt (kein zweites SVG).
3. Der TOC-Eintrag ist ein `<a>` (plus optional die Zahl), kein Text-Span.
4. Das Stylesheet liefert das Symbol (Maske + Haken-Zustand + Griff).
5. Die Messung ist verdrahtet (`layout-ai` misst Laufzeit, Ziel 1200) und die
   Wache prüft im Browser-DOM null Kindknoten.

Der Test ist absichtlich streng an der QUELLE: Wer das Symbol zurück in den
DOM holt, bekommt hier sofort Rot – nicht erst im nächsten Browser-Lauf.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREMIUM = ROOT / "static" / "premium" / "ff-premium.js"
STYLE = ROOT / "assets" / "css" / "extended" / "z-premium-blog.css"
GATE = ROOT / ".github" / "workflows" / "layout-ai.yml"
GLYPH_GUARD = ROOT / "scripts" / "ff_heading_glyph_guard_test.mjs"


def quelle(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


def funktion(text: str, name: str) -> str:
    """Schneidet den Rumpf einer Funktion auf oberster Ebene heraus."""
    start = text.find("function " + name + "(")
    if start < 0:
        raise AssertionError(f"Funktion {name}() fehlt")
    tiefe, i = 0, text.find("{", start)
    beginn = i
    while i < len(text):
        if text[i] == "{":
            tiefe += 1
        elif text[i] == "}":
            tiefe -= 1
            if tiefe == 0:
                return text[beginn:i + 1]
        i += 1
    raise AssertionError(f"Funktion {name}() ist nicht geschlossen")


class UeberschriftKostenTest(unittest.TestCase):
    """Vier Knoten je Symbol waren der größte Posten im Budget."""

    @classmethod
    def setUpClass(cls):
        cls.js = quelle(PREMIUM)

    def test_etikett_und_knopf_sind_die_einzigen_knoten(self):
        for name in ("headingLabel", "addHeadingCopyButtons"):
            with self.subTest(funktion=name):
                rumpf = funktion(self.js, name)
                erzeugt = len(re.findall(r"\bdoc\.createElement\(", rumpf))
                self.assertLessEqual(
                    erzeugt, 1,
                    f"{name}() erzeugt {erzeugt} Elemente – erlaubt ist eines "
                    "(Etikett bzw. Knopf); alles andere gehört ins Stylesheet")

    def test_kein_inline_symbol_mehr_im_knopf(self):
        self.assertNotIn("ff-heading-copy__ico", self.js,
                         "Der alte Inline-SVG-Klassenname ist zurück")
        self.assertNotRegex(self.js, r"innerHTML\s*=\s*(LINK_ICON|CHECK_ICON)",
                            "Das Symbol wird wieder per innerHTML in den DOM gelegt")
        for konstante in ("LINK_ICON", "CHECK_ICON"):
            self.assertNotRegex(self.js, rf"var {konstante}\s*=",
                                f"{konstante} ist zurück – das sind 4 Knoten je Überschrift")

    def test_haken_ist_ein_zustand_kein_zweites_symbol(self):
        self.assertIn("classList.add('ff-copied')", self.js)
        self.assertIn("classList.remove('ff-copied')", self.js)


class VerzeichnisKostenTest(unittest.TestCase):
    """Titel-<span>, Griff-SVG und Zierlinien gehörten ins CSS."""

    @classmethod
    def setUpClass(cls):
        cls.js = quelle(PREMIUM)

    def test_titel_ist_ein_textknoten(self):
        rumpf = funktion(self.js, "createMiniToc")
        self.assertIn("createTextNode(miniTocLabel(", rumpf)
        self.assertNotIn("ff-mini-toc__txt", rumpf,
                         "Der Titel-<span> ist zurück (ein Knoten je Eintrag)")

    def test_zahl_bleibt_das_einzige_zusatzelement(self):
        rumpf = funktion(self.js, "createMiniToc")
        erzeugt = len(re.findall(r"\bdoc\.createElement\(", rumpf))
        # nav, head, strong, counter, pos, rail, railfill, list, a, num-Span
        self.assertLessEqual(erzeugt, 10, f"createMiniToc() erzeugt {erzeugt} Elemente")

    def test_griff_ist_ein_css_muster(self):
        self.assertNotIn("grip.innerHTML", self.js,
                         "Der Griff mal wieder sechs <circle> in den DOM")


class StylesheetTest(unittest.TestCase):
    """Das Symbol muss im Stylesheet existieren, sonst ist es unsichtbar."""

    @classmethod
    def setUpClass(cls):
        cls.css = quelle(STYLE)

    def test_maske_und_haken(self):
        self.assertRegex(self.css,
                         r"\.ff-heading-copy::before\s*\{[^}]*mask\s*:",
                         "Die Maske für das Link-Symbol fehlt")
        self.assertRegex(self.css,
                         r"\.ff-heading-copy\.ff-copied::before\s*\{[^}]*mask-image",
                         "Der Haken-Zustand fehlt")

    def test_symbolgroesse_und_farbe_wie_zuvor(self):
        block = re.search(r"\.ff-heading-copy::before\s*\{[^}]*\}", self.css)
        self.assertIsNotNone(block)
        self.assertIn("width: 15px", block.group(0))
        self.assertIn("background-color: currentColor", block.group(0))

    def test_griff_ist_ein_verlauf(self):
        block = re.search(r"\.ff-mini-toc__grip\s*\{[^}]*\}", self.css)
        self.assertIsNotNone(block)
        self.assertIn("radial-gradient", block.group(0))


class WachenVerdrahtungTest(unittest.TestCase):
    """Eine Regel ohne Fahrer ist keine Regel (Lehre aus #822)."""

    def test_layout_lauf_misst_die_laufzeit(self):
        gate = quelle(GATE)
        self.assertIn("scripts/dom_laufzeit_messung.mjs", gate)
        self.assertIn("LAUFZEIT_EXIT", gate)
        self.assertIn('if [ "$laufzeit_exit" = "1" ]', gate)

    def test_aenderungen_an_der_quelle_loesen_den_lauf_aus(self):
        gate = quelle(GATE)
        self.assertEqual(gate.count('- "static/premium/**"'), 2,
                         "static/premium/** muss in push- UND pull_request-Pfaden stehen")

    def test_browser_wache_prueft_null_kindknoten(self):
        guard = quelle(GLYPH_GUARD)
        self.assertIn("b.children.length === 0", guard)
        self.assertIn("cssGlyph", guard)


if __name__ == "__main__":
    unittest.main()
