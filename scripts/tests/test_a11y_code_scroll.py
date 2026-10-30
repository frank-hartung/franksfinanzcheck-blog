"""#900-Nachtrag: Der Codeblock scrollt am fokussierbaren `pre`, nicht am `code`.

DER BEFUND (30.10.2026)
-----------------------
Der Playwright-Lauf meldete auf `/pillar/strom-sparen/` (nur `[mobile]`) einen
WCAG-Verstoß:

    ■ scrollable-region-focusable (serious) – Scrollable region must have
      keyboard access · wcag2a, wcag211, wcag213
      · Knoten: <code class="language-text" data-lang="text">

Ursache war keine Gestaltung, sondern eine Theme-Regel: PaperMod setzt
`.md-content pre code { overflow-x: auto }`. Chroma liefert
`<pre tabindex="0"><code>…` – der Fokus liegt also auf `pre`, der Scrollbereich
aber im nicht fokussierbaren `code`. Auf schmalen Viewports läuft die
Rechenformel über, und Tastatur-/Schalter-Nutzung kommt nicht an den Rest.

WARUM DIESER TEST
-----------------
Die Heilung ist eine CSS-Überschreibung an genau zwei Stellen. Sie ist still:
Niemand sieht beim Entfernen, dass eine WCAG-Regel wieder aufgeht – außer im
nächsten (teuren) Browser-Lauf. Dieser Test hält die Überschreibung fest und
prüft, dass sie im Kaskadenfenster bleibt (die Datei muss nach der Theme-CSS
geladen werden, sonst verliert sie).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTENDED = ROOT / "assets" / "css" / "extended"
LETZTE = EXTENDED / "zzz-agency-polish.css"
THEME = ROOT / "themes" / "PaperMod" / "assets" / "css" / "common" / "md-content.css"


def lies(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


class CodeblockScrollTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = lies(LETZTE)

    def test_code_scrollt_nicht_mehr(self):
        """Die Theme-Regel `.md-content pre code { overflow-x: auto }` muss
        überschrieben sein – sonst ist `code` wieder der Scrollbereich."""
        treffer = re.search(
            r"\.md-content pre code\s*,[^{]*\{[^}]*overflow-x:\s*visible", self.css)
        self.assertIsNotNone(
            treffer,
            "Die Überschreibung für `.md-content pre code` fehlt – axe meldet "
            "scrollable-region-focusable erneut (WCAG 2.1.1)")

    def test_pre_traegt_den_scrollbereich(self):
        treffer = re.search(r"\.md-content pre\s*,[^{]*\{[^}]*overflow-x:\s*auto", self.css)
        self.assertIsNotNone(treffer, "`pre` (tabindex=0) muss scrollen dürfen")

    def test_keine_spaetere_datei_dreht_die_ueberschreibung_zurueck(self):
        """Hugo hängt `assets/css/extended/` alphabetisch hinter die Theme-CSS.

        Die Überschreibung muss also nur *nach* der Theme-Regel kommen – und
        keine später geladene Datei darf `overflow-x: auto` auf `pre code`
        wieder einführen (sonst ist `code` erneut der Scrollbereich).
        """
        for datei in sorted(EXTENDED.glob("*.css")):
            if datei.name <= LETZTE.name:
                continue
            text = lies(datei)
            self.assertIsNone(
                re.search(r"pre\s+code\s*\{[^}]*overflow-x:\s*auto", text),
                f"{datei.name}: setzt wieder `overflow-x: auto` auf `pre code`")

    def test_theme_regel_ist_noch_die_alte(self):
        """Wird die Theme-Regel einmal korrigiert, darf dieser Test nicht
        stillschweigend weiterlaufen (dann ist die Überschreibung überflüssig)."""
        theme = lies(THEME)
        self.assertRegex(
            theme, r"\.md-content pre code\s*\{[^}]*overflow-x:\s*auto",
            "Der Theme-Vertrag hat sich geändert – Überschreibung und Test prüfen")


if __name__ == "__main__":
    unittest.main()
