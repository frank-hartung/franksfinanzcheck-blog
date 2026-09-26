"""Regressionstests für die zweistufige Inhaltsgruppierung (26.09.2026).

Warum diese Tests existieren
---------------------------
`layouts/_partials/sectioned_content.html` hält das DOM-Budget langer
Ratgeber ein, indem es den gerenderten Markdown-Inhalt gruppiert. Die
Bauweise wurde zweimal geändert, und beide Male hat sich das Problem nur
verschoben:

  nur an H2 geteilt   → ein H2-Abschnitt sammelte bis zu 58 Blöcke
  flach an H2 UND H3  → 59 Chunks lagen nebeneinander, also wieder 58 Kinder
  zweistufig (heute)  → 33 Kinder, größte Gruppe 7

Die dritte Fassung ist die einzige, die BEIDE Dimensionen beschränkt.
Ein Rückfall auf eine flache Teilung sähe im Diff harmlos aus und würde
erst Wochen später als Budget-Befund auffallen – deshalb steht die
Struktur hier als Zusage.

Zweitens: Beide Gruppierungsebenen MÜSSEN `display: contents` behalten.
Bekäme eine davon eine eigene Layout-Box, änderten sich schlagartig alle
Abstände im Artikel. Nachgewiesen wurde die Pixelgleichheit am
26.09.2026 mit 4832 verglichenen Element-Geometrien (4 Seiten × 2
Breiten, 0 Abweichungen > 1 px).

Die Tests laufen ohne Netz, ohne Hugo und ohne Browser; die
Budget-Prüfung überspringt sich selbst, wenn kein Build vorliegt.
"""
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import dom_audit  # noqa: E402

PARTIAL = ROOT / "layouts" / "_partials" / "sectioned_content.html"
CSS = ROOT / "assets" / "css" / "extended" / "z-premium-blog.css"

BUILDS = [
    ROOT / ".cache" / "design-varianten" / "basis" / "public",
    ROOT / "public",
]


class Gruppierung(unittest.TestCase):
    def setUp(self):
        self.quelle = PARTIAL.read_text(encoding="utf-8")
        # ALLE Go-Template-Kommentare entfernen, nicht nur den Kopf: Sie
        # beschreiben die Historie und nennen die alten Bauweisen
        # namentlich – ein Test darf nicht auf Dokumentation anschlagen.
        # (Ein `split("*/")[-1]` wäre falsch: Das Partial hat mehrere
        # Kommentarblöcke, und der letzte steht mitten im Code.)
        self.code = re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", " ",
                           self.quelle, flags=re.S)

    def test_zwei_ebenen_werden_erzeugt(self):
        self.assertIn("ff-content-section", self.code,
                      "Äußere Ebene fehlt – die Zahl der Chunks wäre wieder "
                      "selbst die Obergrenze.")
        self.assertIn("ff-content-chunk", self.code)

    def test_h2_oeffnet_die_aeussere_ebene(self):
        h2 = [z for z in self.code.splitlines() if "<h2 id=" in z]
        self.assertTrue(h2, "Keine H2-Regel gefunden.")
        self.assertTrue(any("ff-content-section" in z for z in h2),
                        "H2 muss eine neue äußere Gruppe beginnen.")

    def test_h3_bleibt_in_der_inneren_ebene(self):
        h3 = [z for z in self.code.splitlines() if "<h3 id=" in z]
        self.assertTrue(h3, "Keine H3-Regel gefunden.")
        self.assertFalse(any("ff-content-section" in z for z in h3),
                         "H3 darf KEINE äußere Gruppe öffnen – sonst ist die "
                         "Teilung wieder flach.")

    def test_leere_huellen_werden_entfernt(self):
        self.assertIn(r'<div class="ff-content-chunk">\s*</div>', self.code,
                      "Aufräumregel für leere Chunks fehlt.")
        self.assertIn(r'<div class="ff-content-section">\s*</div>', self.code,
                      "Aufräumregel für leere Gruppen fehlt.")

    def test_beide_ebenen_sind_display_contents(self):
        css = CSS.read_text(encoding="utf-8")
        regel = re.search(
            r"((?:\.[a-z-]+\s*,\s*)*\.ff-content-chunk\s*\{[^}]*\})", css)
        self.assertIsNotNone(regel, ".ff-content-chunk hat keine CSS-Regel.")
        block = regel.group(1)
        self.assertIn("display: contents", block)
        self.assertIn("ff-content-section", block,
                      "Die äußere Ebene braucht dieselbe Regel – sonst "
                      "erzeugt sie eine Layout-Box und verschiebt alles.")


class BudgetImBuild(unittest.TestCase):
    """Beweis am gebauten HTML – überspringt sich ohne Build."""

    @classmethod
    def setUpClass(cls):
        cls.build = next((b for b in BUILDS if (b / "index.html").exists()), None)
        if cls.build is None:
            raise unittest.SkipTest(
                "Kein Build vorhanden (hugo --destination public oder "
                "scripts/design_variant_lab.py --lauf basis).")

    def test_keine_seite_ueber_der_kinder_fruehwarnung(self):
        ergebnis = dom_audit.audit_dir(str(self.build))
        schlimmste = max(ergebnis["rows"], key=lambda r: r["maxchildren"])
        self.assertLessEqual(
            schlimmste["maxchildren"], dom_audit.BUDGET["children"],
            f"{schlimmste['rel']} hat {schlimmste['maxchildren']} Kinder in "
            f"{schlimmste['maxchildren_path']} (Frühwarnung "
            f"{dom_audit.BUDGET['children']}).")

    def test_kein_leerer_chunk_im_html(self):
        html = (self.build / "index.html").read_text(encoding="utf-8", errors="ignore")
        artikel = sorted((self.build / "posts").glob("*/index.html"))[:5]
        for pfad in artikel:
            text = pfad.read_text(encoding="utf-8", errors="ignore")
            self.assertNotRegex(
                text, r'<div class="ff-content-(chunk|section)">\s*</div>',
                f"Leere Gruppierungshülle in {pfad.parent.name} – kostet "
                "DOM-Knoten ohne jeden Nutzen.")
        self.assertIsInstance(html, str)


if __name__ == "__main__":
    unittest.main()
