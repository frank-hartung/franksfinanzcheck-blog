"""Regression: Ein leeres Verzeichnis unter content/ darf den Build nie töten.

BEFUND 03.10.2026 (Lauf 37149404892, Schritt „Seite bauen")
-----------------------------------------------------------
`layouts/_partials/sitemap_kandidaten.html` hängte das Ergebnis seiner
Rekursion als EINEN Wert an und verließ sich darauf, dass Hugos `append`
eine Liste flachklopft. Das tut es nur bei passendem Elementtyp. Ein
leeres Verzeichnis liefert eine leere, typlose Liste – die landete
verschachtelt im Ergebnis, und `sitemap.xml` rief `site.GetPage` mit einer
Liste statt einem Pfad auf:

    render of "/_sitemap.xml" failed: … expected string; got []string

Der ganze Build starb nach einer Sekunde. Ausgelöst hatte es
`content/drafts/`, das der n8n-Bridge-Selbsttest leer liegen ließ – im
selben Job, eine Stufe vor dem Build. Git zeigt leere Verzeichnisse nicht,
also war der Auslöser im Diff unsichtbar.

WARUM DIESER TEST EINE SABOTAGEPROBE ENTHÄLT
--------------------------------------------
Ob der Defekt zuschlägt, hängt von der SORTIERREIHENFOLGE ab: Nur ein
leerer Ordner, der nach dem ersten Treffer und vor dem Ende einsortiert,
bringt den Build um (`drafts` ✱ tötet, `zz` ✱ nicht – gemessen am
zerbrechlichen Stand). Ein Test, der sich einen Ordnernamen ausdenkt,
wäre also still blind, sobald sich content/ umsortiert – und würde grün
melden, dass etwas geprüft sei, das nie geprüft wurde.

Deshalb prüft der Beweis in beide Richtungen: Mit dem ZERBRECHLICHEN
Template muss der Build sterben (sonst ist die Probe stumpf), mit dem
echten muss er laufen. Das Template wird dafür kurz ersetzt und im
`finally` wortgleich zurückgeschrieben.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARTIAL = os.path.join(BLOG_DIR, "layouts", "_partials", "sitemap_kandidaten.html")

# Sortiert nach "_index.md" und vor den übrigen Einträgen – an dieser Stelle
# ist der Defekt nachweislich tödlich (siehe Sabotageprobe unten).
PROBE_ORDNER = "aa-regression-leerer-ordner"

# Der historische, zerbrechliche Kern: Rekursion als EIN Wert angehängt.
ZERBRECHLICH = (
    '{{- $dir := . -}}\n'
    '{{- $out := slice -}}\n'
    '{{- range os.ReadDir $dir -}}\n'
    '  {{- if .IsDir -}}\n'
    '    {{- $out = $out | append (partial "sitemap_kandidaten.html"'
    ' (path.Join $dir .Name)) -}}\n'
    '  {{- else if or (eq .Name "index.md") (eq .Name "_index.md") -}}\n'
    '    {{- $pfad := strings.TrimPrefix "content" $dir -}}\n'
    '    {{- $out = $out | append (cond (eq $pfad "") "/" $pfad) -}}\n'
    '  {{- end -}}\n'
    '{{- end -}}\n'
    '{{- return $out -}}\n'
)


def _quelltext() -> str:
    with open(PARTIAL, encoding="utf-8") as fh:
        return fh.read()


class Vertrag(unittest.TestCase):
    """Das zerbrechliche Muster darf nicht zurückkehren (läuft ohne Hugo)."""

    def test_partial_existiert(self):
        self.assertTrue(os.path.isfile(PARTIAL), f"{PARTIAL} fehlt")

    def test_rekursion_wird_nicht_als_ein_wert_angehaengt(self):
        code = _quelltext()
        # Kommentare raus: der WARUM-Block nennt das alte Muster absichtlich.
        ohne_kommentar = re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", "", code, flags=re.S)
        self.assertEqual(
            re.findall(r"append\s*\(\s*partial\b", ohne_kommentar), [],
            "sitemap_kandidaten.html hängt die Rekursion wieder als EINEN Wert "
            "an. Ein leeres Verzeichnis unter content/ tötet damit den "
            "gesamten Hugo-Build (expected string; got []string). "
            "Stattdessen über das Ergebnis iterieren und Zeichenketten "
            "einzeln anhängen.")

    def test_es_wird_ueber_die_rekursion_iteriert(self):
        self.assertRegex(
            _quelltext(), r"range\s*\(\s*partial\s+\"sitemap_kandidaten\.html\"",
            "Die Rekursion muss durchlaufen werden, damit nur Zeichenketten "
            "ins Ergebnis wandern.")


@unittest.skipUnless(shutil.which("hugo"), "Hugo nicht installiert")
class Beweis(unittest.TestCase):
    """Mit echtem Hugo – inklusive Nachweis, dass die Probe scharf ist."""

    def _bauen(self) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(prefix="sitemap-regression-") as ziel:
            erg = subprocess.run(
                # Ohne --quiet: Der Fehlertext ist hier der Beweis,
                # nicht nur der Rückgabewert.
                ("hugo", "--minify", "--destination", ziel),
                cwd=BLOG_DIR, capture_output=True, text=True, timeout=600)
            erg.sitemap = ""  # type: ignore[attr-defined]
            pfad = os.path.join(ziel, "sitemap.xml")
            if os.path.isfile(pfad):
                with open(pfad, encoding="utf-8") as fh:
                    erg.sitemap = fh.read()  # type: ignore[attr-defined]
            return erg

    def test_build_ueberlebt_leeres_verzeichnis_unter_content(self):
        leeres = os.path.join(BLOG_DIR, "content", PROBE_ORDNER)
        self.assertFalse(os.path.exists(leeres), "Probenordner liegt schon da")
        echtes_template = _quelltext()
        os.makedirs(leeres)
        try:
            # 1) Sabotageprobe: Mit dem alten Muster MUSS der Build sterben.
            #    Sonst prüft Schritt 2 nichts und meldet trotzdem grün.
            with open(PARTIAL, "w", encoding="utf-8") as fh:
                fh.write(ZERBRECHLICH)
            kaputt = self._bauen()
            self.assertNotEqual(
                kaputt.returncode, 0,
                f"Die Probe ist stumpf: Mit dem zerbrechlichen Template und "
                f"content/{PROBE_ORDNER}/ läuft der Build durch. Dieser Test "
                "beweist dann nichts – Ordnernamen so wählen, dass er nach dem "
                "ersten Treffer einsortiert.")
            self.assertIn("expected string", kaputt.stderr + kaputt.stdout,
                          "Anderer Fehler als erwartet – Probe neu justieren")

            # 2) Mit dem echten Template muss derselbe Baum sauber bauen.
            with open(PARTIAL, "w", encoding="utf-8") as fh:
                fh.write(echtes_template)
            heil = self._bauen()
            self.assertEqual(
                heil.returncode, 0,
                "Ein leeres Verzeichnis unter content/ hat den Build getötet:\n"
                f"{heil.stdout[-1500:]}\n{heil.stderr[-1500:]}")
            self.assertIn("<loc>", heil.sitemap,  # type: ignore[attr-defined]
                          "Sitemap ohne Einträge")
        finally:
            # Niemals eine Leiche hinterlassen – weder Ordner noch Sabotage.
            with open(PARTIAL, "w", encoding="utf-8") as fh:
                fh.write(echtes_template)
            if os.path.isdir(leeres):
                os.rmdir(leeres)


if __name__ == "__main__":
    unittest.main(verbosity=2)
