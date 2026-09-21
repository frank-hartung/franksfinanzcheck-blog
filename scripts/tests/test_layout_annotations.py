"""Tests für `scripts/layout_annotations.py` (Issue #338).

Der Annotations-Übersetzer entscheidet nichts – aber wenn er falsch übersetzt,
verschwinden Befunde oder ein grüner Lauf wird rot annotiert. Beides ist genau
die Klasse Fehler, die #338 zum Dauer-Issue gemacht hat. Deshalb: feste
Fixtures, feste Erwartungen.
"""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "layout_annotations.py"
sys.path.insert(0, str(ROOT / "scripts"))
import layout_annotations as la  # noqa: E402


def dom_fixture(critical=None, warnings=None):
    return {
        "pages": 213,
        "worst": {"maxchildren": 51, "maxchildren_path": "html > head",
                  "headchildren": 51, "depth": 12, "elements": 969},
        "critical": [{"rel": rel, "critical": msgs} for rel, msgs in critical or []],
        "warnings": [{"rel": rel, "warnings": msgs} for rel, msgs in warnings or []],
    }


def browser_fixture(critical=None, warnings=None, metrics=None, drift=None):
    return {
        "domMetrics": metrics or {"maxChildren": 52, "maxChildrenElement": "html > head",
                                  "maxHeadChildren": 52, "maxDepth": 12,
                                  "maxElements": 971},
        "parserCheck": {"compared": 16, "drift": drift or []},
        "criticalPages": [{"url": u, "viewport": v, "issues": i}
                          for u, v, i in critical or []],
        "warningPages": [{"url": u, "viewport": v, "warnings": w}
                         for u, v, w in warnings or []],
    }


class UebersetzerTests(unittest.TestCase):
    def run_report(self, dom, browser, max_annotations=10):
        out = io.StringIO()
        counts = la.report(dom, browser, max_annotations, out=out)
        return counts, out.getvalue()

    def test_notiz_trennt_laufzeit_und_html_messung(self):
        browser = browser_fixture()
        browser["domMetricsHtmlOnly"] = {"maxElements": 968, "maxDepth": 12,
                                         "maxChildren": 50, "maxHeadChildren": 50}
        browser["erweiterungsschicht"] = {"min": 92, "max": 171}
        _counts, text = self.run_report(dom_fixture(), browser)
        self.assertIn("Browser-Laufzeit:", text)
        self.assertIn("HTML ohne Fremd-Skripte: max. Elemente 968", text)
        self.assertIn("Erweiterungsschicht der Site (Laufzeit − HTML): +92 bis +171", text)

    def test_gruener_lauf_hat_keine_fehler_annotation(self):
        counts, text = self.run_report(dom_fixture(), browser_fixture())
        self.assertEqual(0, counts["errors"])
        self.assertNotIn("::error::", text)
        self.assertIn("::notice::", text)
        self.assertIn("Statisch: 213 Seiten vermessen", text)
        self.assertIn("Parser-Gegenrechnung an 16 Messungen, Drift: 0", text)

    def test_kritischer_befund_wird_error_annotation(self):
        dom = dom_fixture(critical=[("/tags/", ["Kinder/Elements: 136 > 60"])])
        counts, text = self.run_report(dom, browser_fixture())
        self.assertEqual(1, counts["errors"])
        self.assertIn("::error::Layout-Audit: /tags/: Kinder/Elements: 136 > 60", text)

    def test_fruehwarnung_wird_warning_ohne_fehler(self):
        dom = dom_fixture(warnings=[("/", ["Kinder: 55 > 54 (Frühwarnung)"])])
        counts, text = self.run_report(dom, browser_fixture())
        self.assertEqual(0, counts["errors"])
        self.assertEqual(1, counts["warnings"])
        self.assertIn("::warning::Layout-Audit (Frühwarnung): /", text)
        self.assertNotIn("::error::", text)

    def test_browser_befunde_und_drift_sind_fehler(self):
        browser = browser_fixture(
            critical=[("http://127.0.0.1:8099/tags/", "1280x800",
                       ["Max. Kinder 136 > 60 (Lighthouse-Grenze)"])],
            drift=["/posts/a/: headchildren: Browser 53 vs. Parser 51 (Δ2 > 2)"])
        counts, text = self.run_report(dom_fixture(), browser)
        self.assertEqual(1, counts["errors"])
        self.assertIn("Max. Kinder 136 > 60", text)

    def test_browser_fruehwarnung_bleibt_gruen(self):
        browser = browser_fixture(warnings=[("http://127.0.0.1:8099/", "390x844",
                                             ["Head-Kinder 53 > 52 (Frühwarnung)"])])
        counts, text = self.run_report(dom_fixture(), browser)
        self.assertEqual(0, counts["errors"])
        self.assertEqual(1, counts["warnings"])

    def test_wird_gedeckelt_und_sagt_es(self):
        dom = dom_fixture(critical=[(f"/page-{i}/", ["zu viele Kinder"])
                                    for i in range(13)])
        counts, text = self.run_report(dom, browser_fixture(), max_annotations=10)
        self.assertEqual(13, counts["errors"])
        self.assertEqual(10, text.count("::error::") - 1)  # 10 Befunde + 1 Rest-Hinweis
        self.assertIn("+3 weitere kritische Befunde", text)

    def test_steuerzeichen_werden_escaped(self):
        dom = dom_fixture(critical=[("/a/", ["Zeile1\nZeile2 100% verbraucht"])])
        _counts, text = self.run_report(dom, browser_fixture())
        line = [l for l in text.splitlines() if l.startswith("::error::")][0]
        self.assertNotIn("\n", line)
        self.assertIn("%0A", line)
        self.assertIn("100%25", line)
        self.assertIn("Zeile2", line)

    def test_leere_berichte_sind_kein_fehler(self):
        counts, text = self.run_report({}, {})
        self.assertEqual({"errors": 0, "warnings": 0}, counts)
        self.assertIn("::notice::", text)

    def test_toolfehler_des_browsers_ist_hart(self):
        browser = browser_fixture()
        browser["toolError"] = True
        counts, text = self.run_report(dom_fixture(), browser)
        self.assertEqual(1, counts["errors"])
        self.assertIn("Werkzeugfehler", text)


class CliTests(unittest.TestCase):
    def test_cli_liest_dateien_und_zaehlt(self):
        with tempfile.TemporaryDirectory() as tmp:
            dom_path = Path(tmp) / "dom.json"
            browser_path = Path(tmp) / "browser.json"
            dom_path.write_text(json.dumps(dom_fixture(
                warnings=[("/tags/", ["Kinder: 55 > 54 (Frühwarnung)"])])),
                encoding="utf-8")
            browser_path.write_text(json.dumps(browser_fixture()), encoding="utf-8")
            res = subprocess.run(
                [sys.executable, str(SCRIPT), "--dom", str(dom_path),
                 "--browser", str(browser_path)],
                capture_output=True, text=True, cwd=str(ROOT))
            self.assertEqual(0, res.returncode, res.stderr)
            self.assertIn("::warning::", res.stdout)
            self.assertIn("::notice::", res.stdout)
            self.assertIn("keine kritischen Befunde, 1 Frühwarnung", res.stdout)

    def test_cli_ohne_berichte_ist_kein_fehler(self):
        res = subprocess.run(
            [sys.executable, str(SCRIPT), "--dom", "/nicht/da.json",
             "--browser", "/auch/nicht/da.json"],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(0, res.returncode)
        self.assertIn("nichts zu annotieren", res.stdout)


if __name__ == "__main__":
    unittest.main()
