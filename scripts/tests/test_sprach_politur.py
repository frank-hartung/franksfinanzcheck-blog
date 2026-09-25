"""Regressionstests: Offline-Sprach-Politur (grammar_check + sprachglatt).

Verträge (Auftrag 25.09.2026, „kostenlos ohne API nachbauen"):
  1) grammar_check.py läuft KOMPLETT offline – kein urllib, kein Netz, kein
     api.languagetool.org mehr (alter Vertrag: „Exit 2 bei API-Ausfall“ ist
     ersatzlos gestrichen; Sabotage-Schutz = Selbsttest, Exit 2).
  2) sprachglatt.py glättet DeepL-Write-artig offline (DW1–DW9) und meldet
     die Grauzonen als V1-Vorschlag (nie Auto-Fix).
  3) Beide Engines: Schutzzonen unangetastet, Titel nie geschrieben,
     Identity-Funde (fix == found) sind Falsch-Alarme und zählen nicht.
  4) Idempotenz: zweiter Lauf ändert nichts mehr.

Ausführung: python3 -m unittest discover -s scripts/tests
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import grammar_check  # noqa: E402
import sprachglatt  # noqa: E402
import sprachkern  # noqa: E402


class OfflineVertragTests(unittest.TestCase):
    def test_grammar_check_ohne_netz_bibliotheken(self):
        """Der LanguageTool-API-Aufruf ist verschwunden (Auftrag: ohne API)."""
        src = (ROOT / "scripts" / "grammar_check.py").read_text(encoding="utf-8")
        # Kein Netz-Import, kein urlopen, keine externe HTTP-Lib
        self.assertNotIn("import urllib", src)
        self.assertNotIn("from urllib", src)
        self.assertNotIn("urlopen", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("http.client", src)
        # Keine echte API-URL im ausführbaren Code (Docstring-Erwähnung ok)
        code_lines = [l for l in src.splitlines()
                      if not l.strip().startswith("#") and '"""' not in l and "'''" not in l]
        code = "\n".join(code_lines)
        # Wenn doch, dann nur in der Historie-Doku, nicht als String für fetch
        self.assertNotIn("languagetool.org/v2/check", code)

    def test_sprachglatt_ohne_api_referenzen(self):
        src = (ROOT / "scripts" / "sprachglatt.py").read_text(encoding="utf-8")
        self.assertNotIn("import urllib", src)
        self.assertNotIn("from urllib", src)
        self.assertNotIn("urlopen", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("deepl.com/v2/write", src)

    def test_selbsttests_gruen(self):
        self.assertEqual(grammar_check.run_selftest(), [])
        self.assertEqual(sprachglatt.run_selftest(), [])


class GrammatikOfflineTests(unittest.TestCase):
    def fix(self, t):
        out, _, _ = sprachkern.apply_rules(t, grammar_check.RULES)
        return out

    def test_seid_zeitangabe_mit_zahl(self):
        self.assertEqual(self.fix("Du sparst seid drei Jahren."),
                         "Du sparst seit drei Jahren.")

    def test_seid_als_verb_bleibt(self):
        self.assertEqual(self.fix("Ihr seid bereit."), "Ihr seid bereit.")

    def test_seid_dem_kurs_gefolgt_bleibt(self):
        self.assertEqual(self.fix("Ihr seid dem Kurs gefolgt."),
                         "Ihr seid dem Kurs gefolgt.")

    def test_wieder_erkwart_verb_bleibt(self):
        self.assertEqual(self.fix("Ich hoffe, ihn wieder erwarten zu können."),
                         "Ich hoffe, ihn wieder erwarten zu können.")

    def test_kollokation_nur_fehlerform(self):
        self.assertEqual(self.fix("Im Gegensatz dazu spart du."),
                         "Im Gegensatz dazu spart du.")  # korrekt = kein Fund
        self.assertIn("im Gegensatz", self.fix("im gegensatz dazu spart du."))

    def test_da_fuer_bleibt(self):
        self.assertEqual(self.fix("Ich bin da für dich."), "Ich bin da für dich.")

    def test_schutzzonen(self):
        s = "`vorallem` und [aufjedenfall](https://x.de) bleiben so."
        self.assertEqual(self.fix(s), s)

    def test_case_erhalt(self):
        self.assertIn("Anhand der Daten", self.fix("An Hand der Daten spart jeder."))

    def test_idempotenz(self):
        einmal = self.fix("Vorallem wo mit wir seid drei Jahren rechnen.")
        self.assertEqual(self.fix(einmal), einmal)


class GlattTests(unittest.TestCase):
    def fix(self, t):
        out, _, _ = sprachkern.apply_rules(t, sprachglatt.RULES)
        return out

    def test_dw2_koennen_hebel(self):
        self.assertEqual(self.fix("Du bist in der Lage, Geld zu sparen."),
                         "Du kannst Geld sparen.")

    def test_dw1_meinung(self):
        self.assertEqual(self.fix("Er ist der Meinung, dass es klappt."),
                         "Er meint, dass es klappt.")
        self.assertEqual(self.fix("Er ist der Meinung des Chefs."),
                         "Er ist der Meinung des Chefs.")

    def test_dw5_negativ_in_betracht_kommen(self):
        self.assertEqual(self.fix("Das kommt nicht in Betracht."),
                         "Das kommt nicht in Betracht.")

    def test_dw6_entscheidung(self):
        self.assertEqual(self.fix("Wir müssen eine Entscheidung treffen."),
                         "Wir müssen entscheiden.")
        # Mit Pronomen dazwischen bleibt es (zu riskant für Auto-Fix) – V1-Vorschlag
        self.assertEqual(self.fix("Triffst du eine Entscheidung?"),
                         "Triffst du eine Entscheidung?")

    def test_dw8_sodass(self):
        self.assertEqual(
            self.fix("Die Kosten steigen, mit der Folge, dass du mehr zahlst."),
            "Die Kosten steigen, sodass du mehr zahlst.")

    def test_dw9_anwendung(self):
        self.assertIn("wird genutzt", self.fix("Das Verfahren findet Anwendung."))

    def test_v1_nur_vorschlag(self):
        funde = sprachglatt.scan_vorschlaege("Eine Vielzahl von Tarifen wartet.")
        self.assertEqual(len(funde), 1)
        self.assertIsNone(funde[0]["fix"])

    def test_idempotenz(self):
        einmal = self.fix("Du bist in der Lage, eine Entscheidung zu treffen.")
        self.assertEqual(self.fix(einmal), einmal)


class KernVertragTests(unittest.TestCase):
    def test_identity_fund_ist_kein_fund(self):
        rules = [("T1", __import__("re").compile(r"\bGeld\b"),
                  (lambda m: "Geld"), "identity")]
        self.assertEqual(sprachkern.scan_rules("Geld sparen.", rules), [])
        _, n, funde = sprachkern.apply_rules("Geld sparen.", rules)
        self.assertEqual(n, 0)
        self.assertEqual(funde, [])

    def test_schutzmasken_shortcodes_und_html(self):
        text = "Hallo {{< tarif >}} <b>Welt</b> ```code vorallem```"
        masked, origs = sprachkern.protect_zones(text)
        self.assertNotIn("vorallem", masked)
        self.assertEqual(sprachkern.unprotect(masked, origs), text)

    def test_write_verified_blockt_linkverlust(self):
        a = {"content": "Sieh [an](/x/).", "path": "/tmp/sprachkern_test.md"}
        ok, grund = sprachkern.write_verified(a, "Sieh an.", "test")
        self.assertFalse(ok)
        self.assertIn("Link", grund)


if __name__ == "__main__":
    unittest.main()
