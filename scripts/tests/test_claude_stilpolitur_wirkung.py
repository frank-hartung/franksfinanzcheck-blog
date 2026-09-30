#!/usr/bin/env python3
"""Urteil über die WIRKSAMKEIT der Claude-Stilpolitur (Reparatur #468).

Ein Lauf, der 44 Kandidaten sieht, jeden Versuch verwirft und trotzdem
grün endet, ist kein Erfolg – er ist ein abgelaufenes Gratis-Token.
Diese Tests frieren genau diese Unterscheidung ein.
"""

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODUL = ROOT / "scripts" / "claude_stilpolitur_wirkung.py"

spec = importlib.util.spec_from_file_location("claude_stilpolitur_wirkung", MODUL)
wirkung = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wirkung)


class WirkungsUrteilTest(unittest.TestCase):
    def test_selftest_is_green(self):
        self.assertEqual(wirkung.selftest(), 0)

    def test_polished_run_is_ok(self):
        status, text = wirkung.urteil({"kandidaten": 3, "poliert": 2, "verworfen": 1})
        self.assertEqual(status, "ok")
        self.assertIn("2 poliert", text)

    def test_nothing_to_do_is_ok(self):
        self.assertEqual(wirkung.urteil({"kandidaten": 0, "poliert": 0,
                                         "verworfen": 0})[0], "ok")

    def test_budget_rotation_without_attempts_is_ok(self):
        """Kandidaten in der Warteschlange sind kein Defekt."""
        self.assertEqual(wirkung.urteil({"kandidaten": 12, "poliert": 0,
                                         "verworfen": 0})[0], "ok")

    def test_all_attempts_failed_is_useless(self):
        status, text = wirkung.urteil({
            "kandidaten": 44, "poliert": 0, "verworfen": 2,
            "items": [{"ergebnis": "verworfen – KI-Antwort leer (Token/Netz/Modell)"},
                      {"ergebnis": "verworfen – KI-Antwort leer (Token/Netz/Modell)"}],
        })
        self.assertEqual(status, "wirkungslos")
        self.assertIn("0 poliert", text)
        self.assertIn("KI-Antwort leer", text)

    def test_missing_report_is_unclear(self):
        self.assertEqual(wirkung.urteil(None)[0], "unklar")
        self.assertIsNone(wirkung.lade(str(ROOT / "gibt-es-nicht.json")))

    def test_cli_prints_single_parsable_line(self, ):
        import io, contextlib, tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "report.json")
            with open(pfad, "w", encoding="utf-8") as fh:
                json.dump({"kandidaten": 1, "poliert": 1, "verworfen": 0}, fh)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = wirkung.main(["--report", pfad])
        self.assertEqual(rc, 0)
        zeilen = buf.getvalue().strip().splitlines()
        self.assertEqual(len(zeilen), 1)
        self.assertTrue(zeilen[0].startswith("ok|"))


if __name__ == "__main__":
    unittest.main()
