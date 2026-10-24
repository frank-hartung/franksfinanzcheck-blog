#!/usr/bin/env python3
"""Regress-Tests für die artikelgenauen Bildzeilen (Issue #824, 24.10.2026).

ANLASS
------
`scripts/abbildungen_ableiten.py` schrieb in jeden der 20 Top-Beiträge
wörtlich dieselbe Unterschrift:

    *Abbildung: Gliederung des Beitrags in seinen Zwischenüberschriften
     (eigene Darstellung).*

Die Duplikat-Wache meldete das als D3-X „Absatz wortgleich in 20 Artikeln“,
das Einzigartigkeits-Audit als U1-PHRASEN. Beide hatten recht: 20 Artikel
trugen denselben Absatz. RD1-duplikate ist in der Release-Scorecard
blockierend, Cross-Artikel-Funde werden nie auto-geheilt – 25 Live-Artikel
standen dauerhaft auf „blockiert“ (Release-Scorecard #824).

DIESE TESTS FRIEREN DEN HEILWEG EIN
-----------------------------------
  1. Zwei Beiträge erzeugen NIEMALS dieselbe Bildzeile.
  2. Die Bildzeile ist Metadaten: keine Beträge/Prozentwerte (sonst landen
     ungeprüfte Zahlen im YMYL-Prüfpfad `fachpruefung_register.py`).
  3. Eine Altfassung wird ERSETZT, nicht verdoppelt – und der zweite Lauf
     ändert nichts mehr (idempotent).
  4. `--check` erkennt Altfassung und doppelte Unterschrift (Exit 1).

Ausführung:  python3 -m unittest scripts.tests.test_abbildungen_ableiten
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import abbildungen_ableiten as abb

ARTIKEL = """---
title: "{title}"
kurzantwort: "{kurz}"
draft: false
---

Einleitung dieses Beitrags mit genug Inhalt für die Gliederung.

## {h2a}

Text A.

## {h2b}

Text B.
"""


def _post(basis: Path, slug: str, title: str, kurz: str, h2a: str, h2b: str) -> Path:
    pfad = basis / slug / "index.md"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(ARTIKEL.format(title=title, kurz=kurz, h2a=h2a, h2b=h2b),
                    encoding="utf-8")
    return pfad


class BildzeilenTests(unittest.TestCase):
    """Die Bildzeile gehört zum Artikel – nicht zur Schablone."""

    def test_zwei_beitraege_teilen_keine_bildzeile(self):
        a = abb.caption_merkkarte("DSL-Wechselbonus sichern", [])
        b = abb.caption_merkkarte("Tagesgeld im Vergleich", [])
        self.assertNotEqual(a, b)
        a2 = abb.caption_ablauf("DSL-Wechselbonus sichern", ["Kosten", "Tarif", "Wechsel"])
        b2 = abb.caption_ablauf("Tagesgeld im Vergleich", ["Zinsen", "Sicherung", "Fazit"])
        self.assertNotEqual(a2, b2)

    def test_gliederungszeile_nennt_die_abschnitte(self):
        caption = abb.caption_ablauf("Preisgarantie Gas", ["Was du prüfst", "Wie du kündigst"])
        self.assertIn("Was du prüfst", caption)
        self.assertIn("Wie du kündigst", caption)
        self.assertIn("2 Stationen", caption)

    def test_bildzeile_enthaelt_keine_betraege(self):
        """Keine zweite Aussage über Geld – Zahlen gehören in den Prüfpfad."""
        captions = [
            abb.caption_merkkarte("Energiekosten senken", ["Spart 12 % und 150 €."]),
            abb.caption_ablauf("Energiekosten senken", ["Kosten", "Fazit"]),
        ]
        for caption in captions:
            for wert in ("€", "Euro", "Prozent", "%"):
                self.assertNotIn(wert, caption, caption)

    def test_alte_schablone_ist_nicht_mehr_die_erwartung(self):
        """Der eingefrorene Originalbefund darf nie wieder erzeugt werden."""
        alt = ("*Abbildung: Gliederung des Beitrags in seinen "
               "Zwischenüberschriften (eigene Darstellung).*")
        for steps in (["Kosten", "Tarif"], ["Zinsen", "Fazit"]):
            self.assertNotEqual(abb.caption_ablauf("Beitrag", steps), alt)
            self.assertNotEqual(abb.caption_merkkarte("Beitrag"), alt)


class EinbindungTests(unittest.TestCase):
    """Altfassung wird ersetzt (Migration), nicht verdoppelt (Idempotenz)."""

    def test_altfassung_wird_ersetzt(self):
        caption = abb.caption_merkkarte("Probe")
        zeilen = [f"![Merkkarte: Kernaussagen zu Probe]({abb.MERK})", "",
                  "*Abbildung: Merkkarte mit den Kernaussagen (eigene "
                  "Darstellung aus diesem Beitrag).*", "", "## Kapitel"]
        neu, gefunden = abb._setze_unterschrift(list(zeilen), abb.MERK, caption)
        self.assertTrue(gefunden)
        self.assertEqual(neu[2], caption)
        self.assertEqual(len(neu), len(zeilen), "Altfassung wurde verdoppelt")
        self.assertEqual(sum(1 for z in neu if z.startswith("*Abbildung:")), 1)

    def test_zweiter_lauf_ist_idempotent(self):
        caption = abb.caption_ablauf("Probe", ["A", "B"])
        zeilen = [f"![Gliederung: Probe]({abb.ABLAUF})", "", caption, "", "## Kapitel"]
        einmal, _ = abb._setze_unterschrift(list(zeilen), abb.ABLAUF, caption)
        zweimal, _ = abb._setze_unterschrift(list(einmal), abb.ABLAUF, caption)
        self.assertEqual(einmal, zweimal)

    def test_fehlende_bildzeile_wird_gemeldet(self):
        _neu, gefunden = abb._setze_unterschrift(["## Kapitel"], abb.MERK, "*x*")
        self.assertFalse(gefunden)

    def test_render_heilt_und_pruefe_post_ist_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            pfad = _post(basis, "2026-01-01-probe", "Beitrag Eins",
                         "Kurzantwort Eins.", "Erster Abschnitt", "Zweiter Abschnitt")
            # Altfassung einbauen, wie sie vor #824 im Bestand stand
            roh = pfad.read_text(encoding="utf-8")
            roh += ("\n![Merkkarte: Kernaussagen zu Beitrag Eins]"
                    f"({abb.MERK})\n\n*Abbildung: Merkkarte mit den "
                    "Kernaussagen (eigene Darstellung aus diesem Beitrag).*\n")
            pfad.write_text(roh, encoding="utf-8")
            self.assertTrue(abb.pruefe_post(pfad, [], {}),
                            "Altfassung wurde von der Prüfung nicht gemeldet")
            abb.render(str(pfad), write=True)
            self.assertEqual(abb.pruefe_post(pfad, [], {}), [])
            # Zweiter Lauf ändert nichts mehr
            vorher = pfad.read_text(encoding="utf-8")
            abb.render(str(pfad), write=True)
            self.assertEqual(pfad.read_text(encoding="utf-8"), vorher)

    def test_gleiche_unterschrift_in_zwei_beitraegen_ist_ein_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            pfad = _post(basis, "2026-01-01-probe", "Beitrag Eins",
                         "Kurzantwort Eins.", "Erster Abschnitt", "Zweiter Abschnitt")
            abb.render(str(pfad), write=True)
            problems, gesehen = [], {}
            abb.pruefe_post(pfad, problems, gesehen)
            self.assertEqual(problems, [])
            # Zweiter Beitrag mit derselben Fassung → Identitätsbefund
            zweiter = basis / "2026-01-02-kopie" / "index.md"
            zweiter.parent.mkdir(parents=True, exist_ok=True)
            zweiter.write_text(pfad.read_text(encoding="utf-8"), encoding="utf-8")
            (zweiter.parent / abb.MERK).write_bytes((pfad.parent / abb.MERK).read_bytes())
            (zweiter.parent / abb.ABLAUF).write_bytes((pfad.parent / abb.ABLAUF).read_bytes())
            probleme2 = abb.pruefe_post(zweiter, [], gesehen)
            self.assertTrue(any("identisch" in p for p in probleme2), probleme2)


class SelbsttestTests(unittest.TestCase):
    def test_modulselbsttest_gruen(self):
        self.assertEqual(abb.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
