#!/usr/bin/env python3
"""Befristete Cover-Ausnahmen: Grund, Datum, Ablauf (24.11.2026).

Der Anlass ist unangenehm ehrlich: Ein Cover ließ sich im CI-Renderer nicht
pixelgleich reproduzieren (fünf rote Deploy-Läufe an einem Tag). Die Wache hat
recht – aber sie hielt die Auslieferung an, und `heilen()` darf Pixel nicht
anfassen. Also gibt es eine Ausnahme, die man LESEN kann: Grund, Prüfdatum,
Ablauf. Diese Tests halten die Liste ehrlich.
"""
from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import ki_cover_herkunft as kh  # noqa: E402


class AusnahmenTest(unittest.TestCase):
    def test_liste_ist_lesbar(self):
        daten = kh.render_ausnahmen()
        self.assertIsInstance(daten, dict)

    def test_jede_ausnahme_hat_grund_und_pruefdatum(self):
        daten = kh.render_ausnahmen()
        for slug, eintrag in daten.items():
            self.assertGreaterEqual(len((eintrag.get("grund") or "").strip()), 20,
                                    f"Grund zu dünn: {slug}")
            self.assertRegex(str(eintrag.get("pruefung")), r"^\d{4}-\d{2}-\d{2}$",
                             f"Prüfdatum fehlt: {slug}")
            self.assertRegex(str(eintrag.get("geprueft_am")), r"^\d{4}-\d{2}-\d{2}$",
                             f"Prüftag fehlt: {slug}")

    def test_abgelaufene_ausnahme_wird_ignoriert(self):
        """Nach `pruefung` ist der Befund wieder hart – ohne Eingriff."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data" / "cover_render_ausnahmen.yaml").write_text(
                'ausnahmen:\n'
                '  - slug: "a"\n'
                '    grund: "ein ausreichend langer Grund für den Test"\n'
                '    geprueft_am: "2026-11-24"\n'
                '    pruefung: "2026-11-25"\n', encoding="utf-8")
            aktiv = kh.render_ausnahmen(root, heute=dt.date(2026, 12, 1))
            self.assertEqual(aktiv, {}, "abgelaufene Ausnahme gilt weiter")
            gilt = kh.render_ausnahmen(root, heute=dt.date(2026, 11, 24))
            self.assertIn("a", gilt)

    def test_ohne_grund_gilt_keine_ausnahme(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data" / "cover_render_ausnahmen.yaml").write_text(
                'ausnahmen:\n'
                '  - slug: "b"\n'
                '    grund: "zu kurz"\n'
                '    geprueft_am: "2026-11-24"\n'
                '    pruefung: "2026-12-08"\n', encoding="utf-8")
            self.assertEqual(kh.render_ausnahmen(root, heute=dt.date(2026, 11, 24)), {})


if __name__ == "__main__":
    unittest.main()
