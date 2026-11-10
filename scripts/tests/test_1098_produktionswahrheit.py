#!/usr/bin/env python3
"""Dauerheilung #1098 – die Kette, die 20 Live-Artikel blockiert hat.

DIE GESCHICHTE (10.11.2026)
---------------------------
`fix_spaces.py` (Regel D: „fehlendes Leerzeichen nach .!?“) lief durch jedes
Markdown-Ziel. Aus `![Merkkarte](abbildung-merkkarte.svg)` wurde
`(abbildung-merkkarte. svg)`. Der Textverständnis-Guard meldete das zu Recht
als R8-URL-LEERZEICHEN (harter Fehler), die Release-Scorecard blockierte
20 Live-Artikel. Der Abbildungs-Nachzug erkannte die zerlegte Zeile nicht
und fügte eine ZWEITE, heile Zeile ein – der Artikel trug danach eine kaputte
und eine heile Einbindung.

Die Reparatur war jedes Mal ein PR; der nächste SEO-/Content-Lauf zerstörte
sie wieder (a5586fbe → 3a3c59a3 → 0019dbc5 → c5ea4970 → ef8085a7). Diese
Tests frieren die drei Glieder ein, die den Kreislauf beenden:

  1. Der Erzeuger fasst Ziele, Dateinamen und HTML-Attribute nicht an.
  2. Der Heiler erkennt JEDE Fassung, schreibt die kanonische und entfernt
     eine Doppelzeile (idempotent).
  3. Der Bestand trägt keine zerlegte Asset-URL mehr.

Ausführung: python3 -m unittest scripts.tests.test_1098_produktionswahrheit
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import abbildungen_ableiten as abb          # noqa: E402
import faktenfrische as ff                 # noqa: E402
import faktenfrische_befund_ledger as ledger  # noqa: E402
import fix_spaces                          # noqa: E402
import fix_url_hygiene as hygiene          # noqa: E402


class FixSpacesSchutzzonen(unittest.TestCase):
    """Regel D darf Prosa heilen – und Ziele in Ruhe lassen."""

    def test_markdown_ziel_bleibt_unangetastet(self):
        for zeile in (
            "![Merkkarte: Kernaussagen](abbildung-merkkarte.svg)",
            "![Gliederung](abbildung-ablauf. svg)",   # kaputt bleibt kaputt
            "[Beitrag](../2026-08-10-dsl-wechselbonus-sichern/index.md)",
            "[DSL vergleichen](/go/dsl/)",
            '[Angebot](https://example.de/a?b=1 "Titel")',
            '<img src="cover.webp" alt="Cover">',
            "Die Datei abbildung-merkkarte.svg liegt im Ordner.",
        ):
            neu, _ = fix_spaces.fix_line_safe(zeile)
            self.assertEqual(neu, zeile)

    def test_prosa_wird_weiter_geheilt(self):
        self.assertEqual(fix_spaces.fix_line_safe("Satz.Neuer Anfang")[0],
                         "Satz. Neuer Anfang")
        self.assertEqual(fix_spaces.fix_line_safe("Hallo,Welt")[0],
                         "Hallo, Welt")

    def test_fix_body_laesst_bildzeilen_bytegleich(self):
        body = ("Ein Satz.Neuer Satz.\n\n"
                "![Merkkarte: Kernaussagen](abbildung-merkkarte.svg)\n\n"
                "*Abbildung: Merkkarte (eigene Darstellung).*\n")
        neu, _ = fix_spaces.fix_body(body)
        self.assertIn("![Merkkarte: Kernaussagen](abbildung-merkkarte.svg)", neu)
        self.assertNotIn("abbildung-merkkarte. svg", neu)
        self.assertIn("Ein Satz. Neuer Satz.", neu)   # Prosa bleibt geheilt


class AbbildungsHeilung(unittest.TestCase):
    """Zerlegte Zeile + Doppelzeile → genau eine kanonische Zeile."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="abb1098-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_doppelzeile_wird_entfernt_und_ist_idempotent(self):
        caption = abb.caption_merkkarte("Probe")
        zeilen = [
            "![Merkkarte: Kernaussagen zu Probe](abbildung-merkkarte. svg)", "",
            "*Abbildung: alte Zeile (eigene Darstellung).*", "",
            "![Merkkarte: Kernaussagen zu Probe](abbildung-merkkarte.svg)", "",
            "## Kapitel",
        ]
        neu, gefunden = abb._setze_unterschrift(list(zeilen), abb.MERK, caption)
        self.assertTrue(gefunden)
        neu = abb._entferne_doppelte_bildzeilen(neu, abb.MERK)
        self.assertEqual(
            sum(1 for z in neu if z.startswith("![")), 1, neu)
        self.assertEqual(sum(1 for z in neu if z.startswith("*Abbildung:")), 1)
        self.assertIn("(abbildung-merkkarte.svg)", neu[0])
        nochmal, _ = abb._setze_unterschrift(list(neu), abb.MERK, caption)
        nochmal = abb._entferne_doppelte_bildzeilen(nochmal, abb.MERK)
        self.assertEqual(nochmal, neu, "Heilung ist nicht idempotent")

    def test_fremdes_bild_bleibt_unberuehrt(self):
        zeilen = ["![Cover](cover.webp)", "", "## Kapitel"]
        neu, gefunden = abb._setze_unterschrift(list(zeilen), abb.MERK,
                                                "Caption")
        self.assertFalse(gefunden)
        self.assertEqual(neu, zeilen)


class UrlHygieneDateien(unittest.TestCase):
    """Eine zerlegte Datei-URL ist heilbar – wenn die Datei existiert."""

    def test_datei_url_wird_geheilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            (basis / "abbildung-merkkarte.svg").write_text("<svg/>",
                                                          encoding="utf-8")
            self.assertEqual(
                hygiene.heal_url("abbildung-merkkarte. svg", [], basis),
                "abbildung-merkkarte.svg")
            self.assertIsNone(
                hygiene.heal_url("nicht-da. svg", [], basis),
                "Heilung ohne existierende Datei wäre geraten")

    def test_ohne_ordnerkontext_keine_heilung(self):
        self.assertIsNone(hygiene.heal_url("abbildung-merkkarte. svg", []))


class AussageHash(unittest.TestCase):
    """Ein abgeleiteter Block darf keine Entscheidung öffnen (v3)."""

    @staticmethod
    def _art(body):
        return {"fm": 'title: "Probe"', "body": body}

    def test_leerzeilen_und_abbildung_aendern_v3_nicht(self):
        mit_block = self._art(
            "Absatz eins.\n\n![](abbildung-merkkarte.svg)\n\n"
            "*Abbildung: X (eigene Darstellung).*\n\nAbsatz zwei.\n")
        ohne_block = self._art("Absatz eins.\n\n\nAbsatz zwei.\n")
        self.assertEqual(ledger.text_hash(mit_block, "betrieb-v3"),
                         ledger.text_hash(ohne_block, "betrieb-v3"))
        # v2 bleibt als Rückwärtsanker unverändert – sie darf NICHT mitheilen.
        self.assertNotEqual(ledger.text_hash(mit_block, "betrieb-v2"),
                            ledger.text_hash(ohne_block, "betrieb-v2"))

    def test_echte_textaenderung_oeffnet_v3(self):
        a = self._art("Absatz eins.\n\nAbsatz zwei.\n")
        b = self._art("Absatz eins geändert.\n\nAbsatz zwei.\n")
        self.assertNotEqual(ledger.text_hash(a, "betrieb-v3"),
                            ledger.text_hash(b, "betrieb-v3"))


class BestandUndErzeuger(unittest.TestCase):
    """Der Live-Bestand und die Fachprüfung bleiben beweisfähig."""

    def test_keine_zerlegte_asset_url_im_bestand(self):
        # Muster: ein Markdown-Ziel mit Dateiendung, in dem nach dem Punkt
        # ein Leerzeichen steht (`abbildung-merkkarte. svg`).
        kaputt = re.compile(
            r"\]\([^)\n]*\.\s+(?:svg|png|jpe?g|webp|avif|gif|pdf|md|html|css|js|json)\b",
            re.I)
        treffer = []
        for pfad in sorted((ROOT / "content").rglob("*.md")):
            for nr, zeile in enumerate(
                    pfad.read_text(encoding="utf-8").splitlines(), 1):
                if kaputt.search(zeile):
                    treffer.append(f"{pfad.relative_to(ROOT)}:{nr}")
        self.assertEqual(treffer, [])

    def test_top20_bildzeilen_sind_kanonisch(self):
        self.assertEqual(abb.check(abb.load_slugs()), [])

    def test_eigene_belegkette_steht_im_pruefauftrag(self):
        art = {"fm": 'title: "X"\nquellen:\n  - titel: "BDEW-Analyse"\n'
                     '    url: "https://www.bdew.de/x"\n'
                     '    herausgeber: "BDEW"\n    datum: "2026-10-28"\n'}
        block = ff._belegketten_block(art)
        self.assertIn("BDEW-Analyse", block)
        self.assertIn("https://www.bdew.de/x", block)
        self.assertIn("KEINE Beleglücke", block)

    def test_befund_ohne_textanker_wird_verworfen(self):
        body = "Laut BDEW kostet die Kilowattstunde 11,93 Cent."
        antwort = ('{"artikel_sha256":"x","befunde":[{"typ":"luecke",'
                   '"text":"Beleglücke","stelle":"Diese Zahl steht nicht im Text",'
                   '"beleg":""}],"quellen":[]}')
        verworfen = []
        befunde, _ = ff.claude_antwort_pruefen(
            antwort, {"treffer": []}, {}, artikel_body=body,
            verworfen=verworfen)
        self.assertEqual(befunde, [])
        self.assertEqual(len(verworfen), 1)

    def test_befund_mit_textanker_bleibt(self):
        body = "Laut BDEW kostet die Kilowattstunde 11,93 Cent."
        antwort = ('{"artikel_sha256":"x","befunde":[{"typ":"luecke",'
                   '"text":"Beleglücke","stelle":"kostet die Kilowattstunde 11,93 Cent",'
                   '"beleg":""}],"quellen":[]}')
        befunde, _ = ff.claude_antwort_pruefen(
            antwort, {"treffer": []}, {}, artikel_body=body)
        self.assertEqual(len(befunde), 1)


if __name__ == "__main__":
    unittest.main()
