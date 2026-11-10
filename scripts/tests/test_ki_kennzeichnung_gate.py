"""Fail-closed-Vertrag der KI-Ausnahme „redaktionelle Verantwortung“ (#1028)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import editorial_review_gate as redaktion
from scripts import ki_kennzeichnung_gate as gate


class KiKennzeichnungGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "posts"

    def schreibe(self, slug: str, fm: dict, body: str = "Geprüfter Text.\n") -> Path:
        pfad = self.posts / slug / "index.md"
        pfad.parent.mkdir(parents=True)
        yaml = redaktion._yaml_module()
        pfad.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
                        + "---\n" + body, encoding="utf-8")
        return pfad

    def freigabe(self) -> dict:
        return {
            "title": "Sachlicher Ratgeber",
            "author": "Frank Hartung",
            "ai_generated": False,
            "redaktionelle_pruefung": {
                "status": "freigegeben",
                "pruefer": {
                    "name": "Redaktion FranksFinanzcheck",
                    "rolle": "Redaktionelle Prüfung und Verantwortung der Fassung",
                },
                "pruefdatum": "2026-11-10",
            },
        }

    def versiegle(self, pfad: Path) -> None:
        fm, body, _ = redaktion.load_article(pfad)
        fm["redaktionelle_pruefung"]["inhalt_sha256"] = redaktion.content_fingerprint(fm, body)
        yaml = redaktion._yaml_module()
        pfad.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
                        + "---\n" + body, encoding="utf-8")

    def test_menschlich_eintrag_ist_kein_pruefnachweis(self) -> None:
        self.schreibe("unbelegt", {"title": "T", "ai_generated": False})
        funde = gate.pruefen(self.posts, {"maschinell": set(), "menschlich": {"unbelegt"}})
        self.assertEqual([p.parent.name for p, _ in funde], ["unbelegt"])
        self.assertIn("kein Nachweis", funde[0][1])

    def test_status_und_name_ohne_fassungshash_reichen_nicht(self) -> None:
        self.schreibe("status", self.freigabe())
        funde = gate.pruefen(self.posts)
        self.assertEqual(len(funde), 1)
        self.assertIn("Fassungs-Hash", funde[0][1])

    def test_fassungsgebundene_redaktionsfreigabe_ist_zulaessig(self) -> None:
        pfad = self.schreibe("geprueft", self.freigabe())
        self.versiegle(pfad)
        self.assertEqual(gate.pruefen(self.posts), [])

    def test_nachtraegliche_textaenderung_entwertet_ausnahme(self) -> None:
        pfad = self.schreibe("geaendert", self.freigabe())
        self.versiegle(pfad)
        pfad.write_text(pfad.read_text(encoding="utf-8") + "Neue Aussage.\n", encoding="utf-8")
        funde = gate.pruefen(self.posts)
        self.assertEqual(len(funde), 1)
        self.assertIn("stimmt nicht", funde[0][1])

    def test_heilung_kennzeichnet_statt_pruefung_zu_erfinden(self) -> None:
        pfad = self.schreibe("unbelegt", {"title": "T", "ai_generated": False})
        self.assertTrue(gate.heilen(pfad))
        self.assertEqual(gate.pruefen(self.posts), [])
        self.assertIn("ai_generated: true", pfad.read_text(encoding="utf-8"))
        self.assertNotIn("redaktionelle_pruefung:", pfad.read_text(encoding="utf-8"))

    def test_realbestand_hat_keine_unbelegte_menschlich_ausnahme(self) -> None:
        register = gate.register_lesen()
        self.assertFalse(register["menschlich"])
        self.assertEqual(gate.pruefen(), [])


if __name__ == "__main__":
    unittest.main()
