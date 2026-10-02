import csv
import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("authority_engine", ROOT / "scripts/authority_engine.py")
ae = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ae)


class AuthorityEngineTest(unittest.TestCase):
    def test_quarters(self):
        self.assertEqual(ae.quarter_for(dt.date(2026, 12, 31)), "2026-Q4")
        self.assertEqual(ae.quarter_for(dt.date(2027, 1, 1)), "2027-Q1")

    def test_repository_contract_is_valid(self):
        errors = ae.validate(ae.load_yaml(ae.STRATEGY), ae.load_yaml(ae.EVIDENCE))
        self.assertEqual(errors, [])

    def test_current_quarter_has_live_asset(self):
        strategy = ae.load_yaml(ae.STRATEGY)
        quarter, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, dt.date(2026, 10, 2))
        self.assertEqual(quarter, "2026-Q4")
        self.assertFalse(any("Quartals-Asset" in text for _, text in actions))

    def test_gsc_import_keeps_only_aggregates(self):
        original = ae.MEASUREMENTS
        try:
            with tempfile.TemporaryDirectory() as tmp:
                ae.MEASUREMENTS = Path(tmp)
                export = Path(tmp) / "gsc.csv"
                export.write_text("Suchanfragen,Klicks,Impressionen\nFranks Finanzcheck,4,20\nstrom sparen,6,80\n", encoding="utf-8")
                target = ae.import_gsc(export, "2026-10")
                data = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(data["gsc"]["clicks"], 10)
                self.assertEqual(data["gsc"]["brand_clicks"], 4)
                self.assertNotIn("Franks Finanzcheck", target.read_text(encoding="utf-8"))
        finally:
            ae.MEASUREMENTS = original


if __name__ == "__main__":
    unittest.main()
