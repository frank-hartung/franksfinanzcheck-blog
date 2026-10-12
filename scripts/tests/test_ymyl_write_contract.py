"""Regression #713: SEO/Politur darf eine Fachfreigabe nicht entwerten."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editorial_review_gate as gate
import keyword_optimizer
import yaml


class YmylWriteContractTests(unittest.TestCase):
    def setUp(self):
        self.fm = {
            "title": "Privathaftpflicht vergleichen",
            "description": "Privathaftpflicht: Schutz vergleichen und Kosten prüfen.",
            "keywords": ["Privathaftpflicht"],
            "draft": True,
            "redaktionelle_pruefung": {
                "status": "freigegeben", "risikoklasse": "hoch",
                "naechste_pruefung": "2000-01-01", "inhalt_sha256": "altes-siegel",
            },
        }
        self.body = "Ein Moment der Unachtsamkeit reicht. " * 30 + "\n## Schutz\n\nKosten: 20 Euro.\n"

    def raw(self, fm=None, body=None):
        return "---\n" + yaml.safe_dump(self.fm if fm is None else fm, allow_unicode=True) + "---\n" + (self.body if body is None else body)

    def test_keyword_stempel_blockiert_auch_beschaedigtes_abgelaufenes_siegel(self):
        self.assertTrue(gate.automatic_change_findings(self.raw(), self.raw(body="Privathaftpflicht im Check: " + self.body)))

    def test_alle_gebundenen_felder_geschuetzt(self):
        for key in ("title", "description", "kurzantwort", "author", "quellen", "redaktionelle_pruefung"):
            with self.subTest(key=key):
                new = copy.deepcopy(self.fm)
                new[key] = [{"id": "Q-neu", "url": "https://example.org"}] if key == "quellen" else {} if key == "redaktionelle_pruefung" else "geändert"
                self.assertTrue(gate.automatic_change_findings(self.raw(), self.raw(new)))

    def test_automatisches_neusiegel_und_review_entfernen_verboten(self):
        new = copy.deepcopy(self.fm)
        new["redaktionelle_pruefung"]["inhalt_sha256"] = "neues-siegel"
        self.assertTrue(gate.automatic_change_findings(self.raw(), self.raw(new)))
        del new["redaktionelle_pruefung"]
        self.assertTrue(gate.automatic_change_findings(self.raw(), self.raw(new)))

    def test_betriebsmetadaten_und_typografie_erlaubt(self):
        new = copy.deepcopy(self.fm)
        new.update(date="2026-10-12", cadence_grund="Prüfung", endredaktion_status="geprüft")
        self.assertEqual([], gate.automatic_change_findings(self.raw(), self.raw(new, self.body.replace("20 Euro", "20\u00a0Euro"))))

    def test_unversiegelte_entwuerfe_bleiben_bearbeitbar(self):
        self.fm.pop("redaktionelle_pruefung")
        self.assertEqual([], gate.automatic_change_findings(self.raw(), self.raw(body="Neuer Text.")))

    def test_parsefehler_sperren(self):
        for invalid in ("kaputt", "---\n[kein, mapping]\n---\nText", "---\na: [\n---\nText"):
            self.assertTrue(gate.automatic_change_findings(self.raw(), invalid))
            self.assertTrue(gate.automatic_change_findings(invalid, self.raw()))

    def test_keyword_optimizer_schreibt_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text(self.raw(), encoding="utf-8")
            before = path.read_bytes()
            changed, reasons = keyword_optimizer.heal_article_file(str(path), include_drafts=True)
            self.assertFalse(changed)
            self.assertTrue(any("YMYL" in reason for reason in reasons), reasons)
            self.assertEqual(before, path.read_bytes())

    def test_endredaktion_sink_schreibt_nicht_und_setzt_arbeitsspeicher_zurueck(self):
        import endredaktion
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text(self.raw(), encoding="utf-8")
            before = path.read_bytes()
            article = endredaktion.artikel_laden(str(path))
            article["body"] += "Neue Aussage."
            self.assertFalse(endredaktion.artikel_speichern(article))
            self.assertEqual(before, path.read_bytes())
            self.assertNotIn("Neue Aussage.", article["body"])

    def test_vorpruefung_fail_closed(self):
        with patch.object(gate, "load_article", side_effect=OSError("nicht lesbar")):
            self.assertTrue(gate.automatic_write_protected("unlesbar.md"))

    def test_gemeinsamer_vertrag_erkennt_ymyl_aenderung(self):
        import publikations_vertrag
        reasons = publikations_vertrag.pruefe("test", self.raw(), self.raw(body=self.body + "Neue Aussage."))
        self.assertTrue(any("YMYL" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()
