"""Vertragstests: Struktur-Heiler #1099 heilt Gerüst, nie Prosa."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import einzigartigkeit_struktur_heiler as heiler  # noqa: E402


class StrukturHeilerTests(unittest.TestCase):
    def test_selftest_gruen(self):
        self.assertEqual(heiler.selftest(), [])

    def test_pool_varianten_sind_paarweise_audit_sicher(self):
        basis = heiler._artikel("a", False, "2026-01-01",
                                "Stromkosten senken beginnt beim Zaehlerstand.")
        original = basis["body"]
        koerper = []
        for v in heiler.POOL:
            body = heiler.cu.clean_body(
                "---\ntitle: x\n---\n" + heiler.ersetze_struktur(basis["_roh"], v))
            self.assertLess(heiler.ueberlappung(body, original), heiler.KRITISCH_AB)
            koerper.append(body)
        for i, a in enumerate(koerper):
            for b in koerper[i + 1:]:
                self.assertLess(heiler.ueberlappung(a, b), heiler.KRITISCH_AB)

    def test_echte_prosa_wird_nicht_geheilt(self):
        prosa = " ".join(f"wort{i}" for i in range(30))
        bestand = {"a/index.md": heiler._artikel("a", False, "2026-01-01", prosa),
                   "b/index.md": heiler._artikel("b", False, "2026-01-02", prosa)}
        geheilt, offen = heiler.heilen(bestand, schreibe=False)
        self.assertEqual(geheilt, [])
        self.assertEqual(len(offen), 1)

    def test_generatoren_schreiben_kein_generisches_geruest_mehr_vor(self):
        for datei in ("scripts/claude_writer.py", "scripts/poppy_repurpose.py"):
            text = (ROOT / datei).read_text(encoding="utf-8")
            self.assertNotIn('Kapitel „Häufige Fehler und wie du sie vermeidest"',
                             text, datei)
            self.assertNotIn("\n## Häufige Fehler und wie du sie vermeidest\n",
                             text, datei)

    def test_workflow_heilt_vor_dem_audit(self):
        wf = (ROOT / ".github/workflows/blog-health-daily.yml").read_text(encoding="utf-8")
        self.assertIn("einzigartigkeit_struktur_heiler.py --selftest", wf)
        self.assertIn("einzigartigkeit_struktur_heiler.py --fix", wf)
        self.assertLess(wf.index("einzigartigkeit_struktur_heiler.py --fix"),
                        wf.index("- name: Einzigartigkeits-Audit"))

    def test_bestand_ist_struktur_sauber(self):
        bestand = heiler.cu.lade_bestand()
        struktur = [t for t in heiler.befunde(bestand) if t["art"] == "struktur"]
        self.assertEqual(struktur, [])


if __name__ == "__main__":
    unittest.main()
