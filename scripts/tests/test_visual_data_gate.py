import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("visual_data_gate", ROOT / "scripts" / "visual_data_gate.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MOD)


class VisualDataGateTests(unittest.TestCase):
    def test_repository_datasets_and_references_are_valid(self):
        result = MOD.run()
        self.assertGreaterEqual(result["datasets"], 2)
        self.assertGreaterEqual(result["references"], 2)
        self.assertGreaterEqual(result["production_references"], 2)
        self.assertEqual([], result["errors"])

    def test_draft_reference_cannot_satisfy_production_gate(self):
        with tempfile.TemporaryDirectory(prefix="visual-data-") as tmp_name:
            tmp = Path(tmp_name)
            data_dir = tmp / "data" / "datasets"
            post = tmp / "content" / "posts" / "test" / "index.md"
            data_dir.mkdir(parents=True)
            post.parent.mkdir(parents=True)
            (data_dir / "dsl_effektivpreis_modell.yaml").write_text(
                (ROOT / "data" / "datasets" / "dsl_effektivpreis_modell.yaml")
                .read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            post.write_text(
                '---\ntitle: "Test"\ndraft: true\n---\n\n'
                '{{< chart dataset="dsl_effektivpreis_modell" >}}\n',
                encoding="utf-8",
            )
            old = MOD.ROOT, MOD.DATA_DIR, MOD.CONTENT_DIR
            try:
                MOD.ROOT = tmp
                MOD.DATA_DIR = data_dir
                MOD.CONTENT_DIR = tmp / "content"
                result = MOD.run()
                self.assertEqual(1, result["references"])
                self.assertEqual(0, result["production_references"])
                self.assertTrue(any("Produktionsreferenz" in e for e in result["errors"]))

                post.write_text(
                    post.read_text(encoding="utf-8").replace("draft: true", "draft: false"),
                    encoding="utf-8",
                )
                result = MOD.run()
                self.assertEqual(1, result["production_references"])
                self.assertEqual([], result["errors"])
            finally:
                MOD.ROOT, MOD.DATA_DIR, MOD.CONTENT_DIR = old

    def test_missing_source_fails_closed(self):
        doc = {
            "schema_version": "1.0", "id": "test-reihe", "title": "Test",
            "description": "Beschreibung", "owner": "Redaktion",
            "status": "beobachtung", "chart_type": "line", "unit": "Euro",
            "x_label": "Zeit", "y_label": "Wert", "updated": "2026-09-28",
            "update_frequency": "monatlich", "sources": [],
            "methodology": {"summary": "Test", "version": "1.0.0", "url": "https://example.org/methode"},
            "changelog": [{"date": "2026-09-28", "note": "Start"}],
            "license": "CC BY 4.0",
            "values": [{"label": "A", "value": 1}, {"label": "B", "value": 2}],
        }
        errors, _ = MOD.validate_dataset(Path("test.yaml"), doc)
        self.assertTrue(any("mindestens eine Quelle" in error for error in errors))

    def test_negative_values_are_rejected_in_v1(self):
        doc = {
            "schema_version": "1.0", "id": "test-reihe", "title": "Test",
            "description": "Beschreibung", "owner": "Redaktion",
            "status": "beobachtung", "chart_type": "bar", "unit": "Euro",
            "x_label": "Kategorie", "y_label": "Wert", "updated": "2026-09-28",
            "update_frequency": "statisch",
            "sources": [{"title": "Quelle", "url": "https://example.org", "publisher": "Test", "accessed": "2026-09-28"}],
            "methodology": {"summary": "Test", "version": "1.0.0", "url": "https://example.org/methode"},
            "changelog": [{"date": "2026-09-28", "note": "Start"}],
            "license": "CC BY 4.0",
            "values": [{"label": "A", "value": -1}, {"label": "B", "value": 2}],
        }
        errors, _ = MOD.validate_dataset(Path("test.yaml"), doc)
        self.assertTrue(any("keine negativen Werte" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
