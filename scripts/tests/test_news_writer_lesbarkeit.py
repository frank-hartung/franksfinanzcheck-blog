"""Regressionstests für die Lesbarkeits-Sicherung des News-Schreibers (#712).

Warum diese Tests existieren
----------------------------
Der Governance-Report #712 führte neun Entwürfe unter der Publish-Schwelle –
der schlimmste („Energie-Update“, Flesch 38,2) kam aus **diesem** Schreiber.
Die Rolle „ChatGPT/News“ erzeugte News-Kompakt-Artikel und maß die Lesbarkeit
nie: Der Ausschuss entstand im Generator und musste von drei Wachen (Publish-
Gate, Endredaktion, Lesbarkeits-Wache) später eingesammelt werden. Dieselbe
Lehre wie WF-D4E0/#612: **Wer schreibt, muss messen, was über ihn entscheidet.**

Diese Datei friert die Zusagen der Sicherung ein:

1) **Importierte SSOT** – die Schwelle kommt aus `readability_check`
   (`NEW_FLESCH_MIN`), keine zweite Zahl im Haus (#585).
2) **Wirkung** – ein dichter Text wird über die Schwelle gehoben und dann
   geschrieben; ein klarer Text bleibt byte-identisch (Idempotenz).
3) **Ehrlichkeit** – reicht die deterministische Stufe nicht (oder fehlt das
   Modul), bleibt der Text stehen und der Status sagt es; ein stiller
   Ausschuss ist die einzige verbotene Sorte.
4) **Haus-Formel und Vertrag** – die `STAND_INTRO`-Zeile (#676) und das
   Frontmatter überleben die Heilung, die Länge bleibt ≥ 90 % (Tor T4).

Alle Tests laufen ohne Netz, ohne API-Keys und ohne Schreiben in den Bestand.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lesbarkeit_heiler as lh  # noqa: E402
import news_writer as nw  # noqa: E402
import readability_check as rc  # noqa: E402

STAND = nw.STAND_INTRO.format(today="2026-10-12")
KLAR = (
    "---\ntitle: \"Klarer Text\"\ndate: 2026-10-12\ndraft: true\n---\n\n"
    + STAND
    + "Die Kasse hebt den Beitrag an. Du zahlst im Monat mehr. "
    "Ein Blick auf die Abrechnung hilft dir sofort. Wer handelt, spart Geld. "
    "Die Frist steht im Vertrag. Du kannst sie online prüfen. "
    "Der Wechsel ist einfach. Der Anbieter hilft dir dabei. "
    "Mehr im [Vergleich](/go/konto/).\n"
)


def dicht() -> str:
    """Dichter Text: Frontmatter + Haus-Formel + Schachtelsätze + Link.

    Start bei Flesch ~58,8 (unter der Schwelle), Ziel nach Stufe A ~70,2 –
    dieselbe Fixture-Bauart wie die Wirkungsprobe des Heilers (WACHE-609),
    nur mit der News-Haus-Formel (#676) und einem `/go/`-Link davor.
    """
    teile = lh.PROBE_FIXTURE.split("---", 2)
    body = teile[2] + "\nMehr im [Vergleich](/go/konto/).\n"
    return teile[0] + "---" + teile[1] + "---\n\n" + STAND + body


class LesbarkeitSichernTests(unittest.TestCase):
    """Der Schreiber misst vor dem Schreiben – und zeigt die Restlücke."""

    def test_schwelle_ist_die_importierte_ssot(self):
        self.assertIs(nw.rc, rc)
        self.assertIs(nw.lesbarkeit_heiler, lh)

    def test_klarer_text_bleibt_byte_identisch(self):
        vorher = KLAR
        content, flesch, status = nw.lesbarkeit_sichern(KLAR, "probe-klar")
        self.assertEqual(content, vorher)
        self.assertIsNotNone(flesch)
        self.assertGreaterEqual(flesch, rc.NEW_FLESCH_MIN)
        self.assertIn("Schwelle erfüllt", status)

    def test_dichter_text_wird_ueber_die_schwelle_gehoben(self):
        content, flesch, status = nw.lesbarkeit_sichern(dicht(), "probe-dicht")
        self.assertIsNotNone(flesch)
        self.assertGreaterEqual(flesch, rc.NEW_FLESCH_MIN, status)
        self.assertIn("→", status)
        # Vertrag T4: Frontmatter byte-identisch, Link erhalten, ≥ 90 % Länge.
        self.assertEqual(content.split("---", 2)[1], dicht().split("---", 2)[1])
        self.assertIn("/go/konto/", content)
        self.assertGreaterEqual(len(content.split("---", 2)[2]),
                                0.9 * len(dicht().split("---", 2)[2]))
        self.assertEqual(lh.verifiziere("probe-dicht", dicht(), content), [])

    def test_haus_formel_ueberlebt_die_heilung(self):
        content, _, _ = nw.lesbarkeit_sichern(dicht(), "probe-haus")
        self.assertIn(STAND.strip(), content)

    def test_ohne_messung_bleibt_es_ehrlich(self):
        rettung = nw.rc
        nw.rc = None
        try:
            content, flesch, status = nw.lesbarkeit_sichern(dicht(), "probe-ohne")
        finally:
            nw.rc = rettung
        self.assertEqual(content, dicht())
        self.assertIsNone(flesch)
        self.assertIn("nicht verfügbar", status)

    def test_unmessbarer_text_wird_ehrlich_gemeldet(self):
        content, flesch, status = nw.lesbarkeit_sichern("ohne Frontmatter",
                                                        "probe-kaputt")
        self.assertEqual(content, "ohne Frontmatter")
        self.assertIsNone(flesch)
        self.assertIn("nicht messbar", status)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
