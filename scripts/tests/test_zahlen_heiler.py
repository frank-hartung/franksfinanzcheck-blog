"""Zahlen-Beleg-Heiler am Geburtspunkt (WF-D4E0, #821 – 25.10.2026).

Befund des Laufs vom 25.10.2026: Vier frische Themen starben bei der Geburt
am harten RS5-Gate (16, 20 und 8 unbelegte Zahlenbehauptungen). Die
Wiederholung half nicht – sie verletzte dieselbe Regel mit derselben
Wahrscheinlichkeit erneut. Der vorhandene KI-Heiler kannte die REGEL, aber
nicht die SÄTZE.

Diese Tests verriegeln beide Richtungen: Der Heiler muss die abgelehnten Sätze
wörtlich in den Prompt legen – und er darf niemals eine schlechtere oder
kürzere Fassung zurückgeben. Ohne Befund wird kein Modell aufgerufen.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import engine_generate as eg  # noqa: E402
import redaktions_standard as rs  # noqa: E402

BELEGT = "Mehr dazu bei der [Verbraucherzentrale](https://example.org/beratung)."

BODY = f"""## Worum es geht

Ein Umzug kostet im Schnitt 1.450 Euro und die Kaution liegt bei 3 Monatsmieten.
Der Wechsel des Anbieters spart 220 Euro im Jahr und dauert 6 Wochen.

## Was du prüfen solltest

Prüfe zuerst deine Fixkosten und notiere jeden Vertrag mit Preis und Frist.
Ordne die Beträge nach Wirkung und streiche, was du nicht nutzt.

## So gehst du vor

1. Sammle alle Verträge an einem Ort.
2. Vergleiche die Preise und kündige, was zu teuer ist.
3. Lege die Ersparnis sofort auf ein separates Konto.

## Typische Fehler

Viele kündigen zu spät und zahlen 3 Monate doppelt.
Wer 500 Euro Notgroschen hat, ist ruhiger unterwegs.

{BELEGT}
"""

REPARIERT = f"""## Worum es geht

In der Beispielrechnung mit einer Annahme von zwei Umzugskartons ergibt sich ein Betrag.
Der Wechsel des Anbieters spart in der Beispielrechnung mit einer Annahme von 60 Euro im Monat Geld.

## Was du prüfen solltest

Prüfe zuerst deine Fixkosten und notiere jeden Vertrag mit Preis und Frist.
Ordne die Beträge nach Wirkung und streiche, was du nicht nutzt.

## So gehst du vor

1. Sammle alle Verträge an einem Ort.
2. Vergleiche die Preise und kündige, was zu teuer ist.
3. Lege die Ersparnis sofort auf ein separates Konto.

## Typische Fehler

Viele kündigen zu spät und zahlen doppelt.
Wer einen kleinen Notgroschen hat, ist ruhiger unterwegs.

{BELEGT}
"""


class PromptTests(unittest.TestCase):
    def test_prompt_nennt_die_abgelehnten_saetze_woertlich(self):
        funde = rs._reserve_numeric_claim_findings(BODY)
        self.assertTrue(funde)
        prompt = rs.build_zahlen_heiler_prompt(BODY, funde[:3], "Testtitel")
        for satz in funde[:3]:
            self.assertIn(satz, prompt, "der Heiler muss den Satz kennen, den er heilen soll")
        self.assertIn("Beispielrechnung", prompt)
        self.assertIn("WORTGLEICH", prompt)
        self.assertIn("keine neuen Links", prompt)

    def test_prompt_verbietet_hedge_als_beleg(self):
        prompt = rs.build_zahlen_heiler_prompt(BODY, ["Ein Satz mit 50 Euro."])
        self.assertIn("als Ersatz für die Kennzeichnung", prompt)


class WirkungTests(unittest.TestCase):
    def _ki(self, antwort):
        aufrufe = []

        def fake(prompt, max_tokens=None):
            aufrufe.append(prompt)
            return antwort
        fake.aufrufe = aufrufe
        return fake

    def test_ohne_befund_wird_kein_modell_aufgerufen(self):
        ki = self._ki(REPARIERT)
        neu, stelle = rs.zahlen_beleg_heiler(
            "Der Text ist sauber und nennt keine Beträge.", ki=ki)
        self.assertIsNone(neu)
        self.assertEqual([], stelle)
        self.assertEqual([], ki.aufrufe, "ohne Befund darf kein Kontingent verbrannt werden")

    def test_geheilte_fassung_wird_uebernommen(self):
        ki = self._ki(REPARIERT)
        neu, stelle = rs.zahlen_beleg_heiler(BODY, titel="Testtitel", ki=ki)
        self.assertIsNotNone(neu)
        self.assertTrue(stelle)
        self.assertLess(len(rs._reserve_numeric_claim_findings(neu)),
                        len(rs._reserve_numeric_claim_findings(BODY)))

    def test_wirkungslose_antwort_wird_verworfen(self):
        ki = self._ki(BODY)
        neu, _ = rs.zahlen_beleg_heiler(BODY, ki=ki)
        self.assertIsNone(neu, "keine Wirkung = keine Änderung")

    def test_veraenderte_links_werden_verworfen(self):
        kaputt = REPARIERT.replace("https://example.org/beratung",
                                   "https://example.org/andere")
        neu, _ = rs.zahlen_beleg_heiler(BODY, ki=self._ki(kaputt))
        self.assertIsNone(neu)

    def test_geschrumpfter_text_wird_verworfen(self):
        kurz = REPARIERT.split("## So gehst du vor")[0] + BELEGT
        neu, _ = rs.zahlen_beleg_heiler(BODY, ki=self._ki(kurz))
        self.assertIsNone(neu)

    def test_leere_antwort_wird_verworfen(self):
        neu, _ = rs.zahlen_beleg_heiler(BODY, ki=self._ki(None))
        self.assertIsNone(neu)


class GeburtsVertragTests(unittest.TestCase):
    def test_nur_zahlenbefund_erkennt_die_klasse(self):
        self.assertTrue(eg._nur_zahlenbefund(["RS5: 7 Zahlenbehauptung(en) …"]))
        self.assertFalse(eg._nur_zahlenbefund([
            "RS5: 7 Zahlenbehauptung(en) …", "nur 900 Wörter / 6.100 Zeichen"]))
        self.assertFalse(eg._nur_zahlenbefund([]))

    def test_heilung_wird_nur_bei_zahlenbefund_versucht(self):
        # Dokumentierter Vertrag: der Heiler läuft genau einmal pro Generation
        # und nur, wenn ausschließlich RS5 blockiert.
        self.assertEqual(1, eg.ZAHLEN_HEILER_MAX_VERSUCHE)


if __name__ == "__main__":
    unittest.main()
