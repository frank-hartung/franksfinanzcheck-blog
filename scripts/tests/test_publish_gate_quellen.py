#!/usr/bin/env python3
"""Vertrag: Das Publish-Gate veröffentlicht nichts ohne Quellenbasis.

Ticket-Klasse der Nachlauf-Wache (#1146, #1150, #1155, #1156, #1158, #1178,
#1186, #1190, #1200, #1202, #1204): Elf Tickets in fünf Tagen meldeten
„[metadaten] M4: Keine Quelle im Frontmatter (quellen)“ – jedes Mal an einem
Artikel, der bereits LIVE war. Die Metadaten-Wache erkennt den Mangel, blockt
aber nicht (C34); das Publish-Gate hatte für dieses Feld keine Regel. Der
Melder hat also korrekt gemeldet, und niemand hat vorher entschieden.

Ab sofort gilt: jeder Kandidat mit `draft: false` braucht einen nicht-leeren
`quellen:`-Block. Fehlt er, wird der Kandidat zurückgestellt – der Text bleibt
erhalten, die Redaktion ergänzt die Belege. Kein Heiler erfindet Quellen.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_gate as pg  # noqa: E402


class QuellenGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.posts = self.root / "content" / "posts"
        self.original_posts_dir = pg.POSTS_DIR
        pg.POSTS_DIR = str(self.posts)

    def tearDown(self):
        pg.POSTS_DIR = self.original_posts_dir
        self.tmp.cleanup()

    def write_post(self, slug, quellen_block=None, draft=False):
        path = self.posts / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        zeilen = ["---", "title: Test", f"draft: {str(draft).lower()}"]
        if quellen_block is not None:
            zeilen.append(quellen_block.rstrip("\n"))
        zeilen += ["---", "", "Ein Satz Fliesstext zum Füllen des Artikels."]
        path.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    def test_ohne_quellen_ist_gate_fund(self):
        self.write_post("2026-11-13-ohne-quellen")
        fehlend, werkzeugfehler = pg.quellen_failures(["2026-11-13-ohne-quellen"])
        self.assertIsNone(werkzeugfehler)
        self.assertIn("2026-11-13-ohne-quellen", fehlend)
        gruende = fehlend["2026-11-13-ohne-quellen"]
        self.assertTrue(any("Quellenbasis fehlt" in g for g in gruende), gruende)

    def test_leere_liste_ist_fehlend(self):
        self.write_post("2026-11-13-leer", quellen_block="quellen: []")
        fehlend, _ = pg.quellen_failures(["2026-11-13-leer"])
        self.assertIn("2026-11-13-leer", fehlend)

    def test_nackter_schluessel_ohne_inhalt_ist_fehlend(self):
        # Ein `quellen:` ohne Listeneinträge sieht im Diff gefüllt aus, ist
        # aber kein Beleg – genau dieser Fall darf nicht durchrutschen.
        self.write_post("2026-11-13-nackt", quellen_block="quellen:\nkeywords:\n  - a")
        fehlend, _ = pg.quellen_failures(["2026-11-13-nackt"])
        self.assertIn("2026-11-13-nackt", fehlend)

    def test_mit_quellenliste_geht_durch(self):
        self.write_post(
            "2026-11-13-mit",
            quellen_block=(
                "quellen:\n"
                '  - titel: "Verbraucherzentrale: Tagesgeld"\n'
                '    url: "https://www.verbraucherzentrale.de/"\n'
            ),
        )
        fehlend, _ = pg.quellen_failures(["2026-11-13-mit"])
        self.assertEqual({}, fehlend)

    def test_inline_liste_zaehlt_als_beleg(self):
        self.write_post(
            "2026-11-13-inline",
            quellen_block='quellen: ["https://www.bundesbank.de/"]',
        )
        fehlend, _ = pg.quellen_failures(["2026-11-13-inline"])
        self.assertEqual({}, fehlend)

    def test_entwurf_ist_nicht_zustaendig(self):
        # Entwürfe filtert bereits `todays_live_candidates()`; die Regel ist
        # trotzdem explizit auf `draft: false` begrenzt (kein Fehlalarm, wenn
        # die Funktion einmal direkt aufgerufen wird).
        self.write_post("2026-11-13-entwurf", draft=True)
        fehlend, _ = pg.quellen_failures(["2026-11-13-entwurf"])
        self.assertEqual({}, fehlend)

    def test_leere_kandidatenliste_und_fehlende_datei(self):
        fehlend, _ = pg.quellen_failures([])
        self.assertEqual({}, fehlend)
        fehlend, _ = pg.quellen_failures(["2026-11-13-gibt-es-nicht"])
        self.assertEqual({}, fehlend)

    def test_kein_heiler_erfindet_quellen(self):
        # Die Deckungswache muss die Regel als redaktionelle Ausnahme führen –
        # ein Reserve-Heiler, der Belege ergänzt, wäre eine erfundene Quelle.
        import reserve_healer_coverage as rhc

        bericht = rhc.deckung()
        self.assertEqual([], bericht["luecken"], "Gate-Regel ohne Heiler")
        self.assertEqual([], bericht["tote_ausnahmen"], "Eintrag deckt nichts mehr")
        ausnahmen = {e["regel"]: e["grund"] for e in bericht["ausnahmen"]}
        self.assertIn("quellen_failures", ausnahmen)
        self.assertIn("redaktionell", ausnahmen["quellen_failures"])
        self.assertNotIn("quellen_failures", rhc.REGEL_HEILER)

    def test_regel_ist_im_gate_verdrahtet(self):
        # Ein Detektor ohne Verdrahtung wäre ein Bericht, keine Sperre.
        quelle = (ROOT / "scripts" / "publish_gate.py").read_text(encoding="utf-8")
        self.assertIn("quellen_fail, quellen_tool_error = quellen_failures(candidates)",
                      quelle)
        self.assertIn("if slug in quellen_fail:", quelle)


if __name__ == "__main__":
    unittest.main()
