#!/usr/bin/env python3
"""Regression: Die Sitemap muss ihren Bestand ABLEITEN, nicht aufzählen.

BEFUND 01.10.2026 (Vorgang WF-54C4, Deploy-Stopp)
`layouts/sitemap.xml` pflegte eine Namensliste der aufzunehmenden Seiten
(sechs Pillar-Slugs, zwei Hubs, die Rechtsseiten). Eine neue Seite war damit
nicht in der Sitemap, bis jemand den Namen nachtrug – die Index-Hygiene-Wache
meldete H1 („indexierbar, fehlt in der Sitemap") und stoppte den Deploy auf
GitHub Pages. Betroffen nacheinander: /transparenz/, /aenderungsprotokoll/,
/cockpit/.

Die Reparatur ist strukturell: `sitemap_kandidaten.html` läuft den
content-Baum ab, `seo_indexierbar.html` entscheidet als einzige Stelle über
die Indexierbarkeit (head.html nutzt dieselbe Partial). Dieser Test hält den
Zustand fest – er schlägt an, sobald jemand wieder Seitennamen ins
Sitemap-Template schreibt oder die Ableitung entfernt.
"""
from __future__ import annotations

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITEMAP = os.path.join(ROOT, "layouts", "sitemap.xml")
KANDIDATEN = os.path.join(ROOT, "layouts", "_partials", "sitemap_kandidaten.html")
INDEXIERBAR = os.path.join(ROOT, "layouts", "_partials", "seo_indexierbar.html")
HEAD = os.path.join(ROOT, "layouts", "_partials", "head.html")
CONTENT = os.path.join(ROOT, "content")

KOMMENTAR = re.compile(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", re.S)


def ohne_kommentare(pfad: str) -> str:
    with open(pfad, encoding="utf-8") as fh:
        return KOMMENTAR.sub(" ", fh.read())


def inhalts_slugs() -> list[str]:
    """Top-Level-Seiten im content-Baum (ohne Sektionen mit Unterseiten)."""
    out = []
    for name in sorted(os.listdir(CONTENT)):
        pfad = os.path.join(CONTENT, name)
        if not os.path.isdir(pfad):
            continue
        if os.path.exists(os.path.join(pfad, "index.md")):
            out.append(name)
    return out


class SitemapAbleitung(unittest.TestCase):
    def test_partials_vorhanden(self) -> None:
        for pfad in (SITEMAP, KANDIDATEN, INDEXIERBAR, HEAD):
            self.assertTrue(os.path.exists(pfad), f"fehlt: {pfad}")

    def test_sitemap_nutzt_die_ableitung(self) -> None:
        code = ohne_kommentare(SITEMAP)
        self.assertIn("sitemap_kandidaten.html", code,
                      "Sitemap leitet ihren Bestand nicht mehr aus dem content-Baum ab")
        self.assertIn("seo_indexierbar.html", code,
                      "Sitemap entscheidet Indexierbarkeit wieder selbst")

    def test_kandidaten_laufen_den_content_baum_rekursiv_ab(self) -> None:
        code = ohne_kommentare(KANDIDATEN)
        self.assertIn("os.ReadDir", code, "Kandidatensuche liest das Dateisystem nicht")
        self.assertIn("sitemap_kandidaten.html", code,
                      "Kandidatensuche steigt nicht rekursiv in Unterordner ab")
        for datei in ("index.md", "_index.md"):
            self.assertIn(datei, code, f"Seitenbündel {datei} wird nicht erkannt")

    def test_head_und_sitemap_teilen_eine_entscheidung(self) -> None:
        self.assertIn("seo_indexierbar.html", ohne_kommentare(HEAD),
                      "head.html entscheidet die Indexierbarkeit wieder eigenständig – "
                      "robots-Meta und Sitemap können auseinanderlaufen (H1/H8)")

    def test_keine_seitennamen_im_sitemap_template(self) -> None:
        """Kein Slug einer Inhaltsseite darf im Template stehen.

        Ausnahmen: `posts` und `pillar` sind Sektions-/Gruppennamen für
        Priorität und Bild-Sitemap, keine Aufzählung einzelner Seiten.
        """
        code = ohne_kommentare(SITEMAP)
        erlaubt = {"posts", "pillar"}
        gefunden = [s for s in inhalts_slugs()
                    if s not in erlaubt and re.search(rf'["/\s]{re.escape(s)}\b', code)]
        self.assertEqual(
            gefunden, [],
            "Seitennamen im Sitemap-Template gefunden: "
            f"{gefunden} – genau diese Handpflege verursachte WF-54C4. "
            "Feinsteuerung gehört ins Frontmatter der Seite "
            "(sitemap.priority / sitemap.changefreq).")


if __name__ == "__main__":
    unittest.main()
