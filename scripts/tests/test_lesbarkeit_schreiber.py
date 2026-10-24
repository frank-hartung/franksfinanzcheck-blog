"""Regressionstests für die Schreiber-Garantie (Governance-Report #806).

Warum diese Tests existieren
----------------------------
Der Premium-Governance-Lauf vom 19.10.2026 meldete zwei Entwürfe unter der
Publish-Schwelle 60 (Flesch 54,2 / 54,9). Beide trugen `ki_redaktion:
"claude"` – sie kamen aus der Rolle „Claude“ (`scripts/claude_writer.py`),
dem Hauptproduzenten der langen Premium-Artikel. Die Lehre aus #612 und #712
(„Wer schreibt, muss messen, was über ihn entscheidet“) war nur EINER Rolle
gegeben worden: `news_writer.py` (Rolle „ChatGPT/News“) bekam eine
Sicherung, die Rolle „Claude“ und die Werkbank-Recycling-Bahn nicht.

Damit war die Klasse `read_draft` ein Dauerläufer: #712 (12.10.) und #806
(19.10.) meldeten dieselbe Klasse in zwei Wochen – nur mit anderen Namen.
Der Ausschuss entstand im Generator.

Diese Datei friert die Zusage ein:

1) **Eine Garantie für alle Schreiberbahnen** – `lesbarkeit_schreiber.py`
   (messen → Stufe A → Tor T1–T4 → ehrliche Restlücke).
2) **Importierte SSOT** – die Schwelle kommt aus `readability_check`
   (`NEW_FLESCH_MIN`), keine zweite Zahl im Haus (#585).
3) **Wirkung** – ein dichter Text wird über die Schwelle gehoben und dann
   geschrieben; ein klarer Text bleibt byte-identisch (Idempotenz).
4) **Tor** – was das Tor nicht freigibt, wird nicht geschrieben.
5) **Ehrlichkeit** – reicht die deterministische Stufe nicht, bleibt der
   Text stehen und der Status sagt es; ein stiller Ausschuss ist die einzige
   verbotene Sorte.
6) **Verdrahtung** – jeder Schreiber sichert VOR `write_post`; das ist die
   Zusage, die C41 im Governance-Vertrag prüft.

Alle Tests laufen ohne Netz, ohne API-Keys und ohne Schreiben in den Bestand.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lesbarkeit_heiler as lh  # noqa: E402
import lesbarkeit_schreiber as ls  # noqa: E402
import readability_check as rc  # noqa: E402

#: Jede Bahn, die einen Artikel schreibt – ohne Ausnahme (C41).
SCHREIBER = ("news_writer.py", "claude_writer.py", "poppy_repurpose.py")

KLAR = (
    "---\n"
    'title: "Klarer Text"\n'
    "date: 2026-10-24\n"
    "draft: true\n"
    "---\n\n"
    "Die Kasse hebt den Beitrag an. Du zahlst im Monat mehr. "
    "Ein Blick auf die Abrechnung hilft dir sofort. Wer handelt, spart Geld. "
    "Die Frist steht im Vertrag. Du kannst sie online prüfen. "
    "Der Wechsel ist einfach. Der Anbieter hilft dir dabei.\n"
)


def dicht() -> str:
    """Dichter Text: Frontmatter + Schachtelsätze + `/go/`-Link.

    Dieselbe Fixture-Bauart wie die Wirkungsprobe des Heilers (WACHE-609):
    Start unter der Schwelle, nach Stufe A deutlich darüber.
    """
    teile = lh.PROBE_FIXTURE.split("---", 2)
    body = teile[2] + "\nMehr im [Vergleich](/go/konto/).\n"
    return teile[0] + "---" + teile[1] + "---\n\n" + body


class GarantieTests(unittest.TestCase):
    """Die Hausgarantie misst, heilt, prüft und bleibt ehrlich."""

    def test_schwelle_ist_die_importierte_ssot(self):
        self.assertIs(ls.rc, rc)
        self.assertIs(ls.lesbarkeit_heiler, lh)
        # Keine eigene Zahl im Haus: das Modul liest die SSOT, es setzt sie nicht.
        quelle = (SCRIPTS / "lesbarkeit_schreiber.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"NEW_FLESCH_MIN\s*=\s*[0-9]", quelle))

    def test_klarer_text_bleibt_byte_identisch(self):
        inhalt, flesch, status = ls.sichern(KLAR, "probe-klar")
        self.assertEqual(inhalt, KLAR)
        self.assertIsNotNone(flesch)
        self.assertGreaterEqual(flesch, rc.NEW_FLESCH_MIN)
        self.assertIn("Schwelle erfüllt", status)

    def test_dichter_text_wird_ueber_die_schwelle_gehoben(self):
        vorher = ls.messen(dicht(), "probe-dicht")
        inhalt, flesch, status = ls.sichern(dicht(), "probe-dicht")
        self.assertIsNotNone(vorher)
        self.assertLess(vorher, rc.NEW_FLESCH_MIN)
        self.assertNotEqual(inhalt, dicht())
        self.assertIsNotNone(flesch)
        self.assertGreaterEqual(flesch, rc.NEW_FLESCH_MIN, status)
        self.assertIn("→", status)          # Wirkungsnachweis im Status
        # Tor T1–T4: Frontmatter byte-identisch, Link erhalten, Länge ≥ 90 %.
        self.assertEqual(inhalt.split("---", 2)[1], dicht().split("---", 2)[1])
        self.assertIn("/go/konto/", inhalt)
        self.assertGreaterEqual(len(inhalt.split("---", 2)[2]),
                                0.9 * len(dicht().split("---", 2)[2]))
        self.assertEqual(lh.verifiziere("probe-dicht", dicht(), inhalt), [])

    def test_ohne_messung_bleibt_es_ehrlich(self):
        inhalt, flesch, status = ls.sichern(dicht(), "probe-ohne",
                                            rc_mod=None, heiler=None)
        self.assertEqual(inhalt, dicht())
        self.assertIsNone(flesch)
        self.assertIn("nicht verfügbar", status)

    def test_unmessbarer_text_wird_ehrlich_gemeldet(self):
        inhalt, flesch, status = ls.sichern("ohne Frontmatter", "probe-kaputt")
        self.assertEqual(inhalt, "ohne Frontmatter")
        self.assertIsNone(flesch)
        self.assertIn("nicht messbar", status)

    def test_selbsttest_des_moduls_ist_gruen(self):
        self.assertEqual(ls.selftest(), 0)


class VerdrahtungTests(unittest.TestCase):
    """Jeder Schreiber sichert VOR dem Schreiben (die Zusage von C41)."""

    def _quelle(self, name: str) -> str:
        return (SCRIPTS / name).read_text(encoding="utf-8")

    def test_alle_schreiber_nutzen_die_garantie(self):
        for name in SCHREIBER:
            with self.subTest( Schreiber=name):
                quelle = self._quelle(name)
                self.assertIn("lesbarkeit_schreiber", quelle,
                              f"{name} nutzt die Schreiber-Garantie nicht")

    def test_kein_schreiber_schreibt_ohne_messung(self):
        for name in SCHREIBER:
            with self.subTest(Schreiber=name):
                quelle = self._quelle(name)
                aufrufe = []
                for m in re.finditer(
                        r"(?:lesbarkeit_schreiber\.sichern|lesbarkeit_sichern)\s*\(",
                        quelle):
                    davor = quelle[:m.start()].rstrip()
                    if davor.endswith("def"):
                        continue
                    aufrufe.append(m.start())
                self.assertTrue(aufrufe, f"{name}: die Garantie ist nicht verdrahtet")
                schreiben = re.search(r"\bwrite_post\s*\(", quelle)
                self.assertIsNotNone(schreiben, f"{name}: kein write_post gefunden")
                self.assertLess(min(aufrufe), schreiben.start(),
                                f"{name} schreibt, bevor es misst")

    def test_werbeblock_bleibt_ausserhalb_der_messung(self):
        """Der CTA/Disclaimer ist kein Fließtext – er wird erst nach der
        Sicherung angehängt. Sonst misst der Schreiber eine Länge, die er nur
        mit Werbung erreicht."""
        for name in SCHREIBER:
            with self.subTest(Schreiber=name):
                quelle = self._quelle(name)
                aufruf = re.search(r"sichern\(rumpf, slug\)", quelle)
                self.assertIsNotNone(aufruf, f"{name}: kein Aufruf auf dem Rumpf")
                cta = quelle.find("cta_block(")
                self.assertNotEqual(cta, -1, f"{name}: kein CTA-Block gefunden")
                # Im Claude-Writer wird der CTA VOR dem Aufruf gebaut, aber erst
                # NACH der Sicherung angehängt – entscheidend ist die Reihenfolge
                # von `content = rumpf` und `content +=`.
                self.assertIn("content = rumpf", quelle)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
