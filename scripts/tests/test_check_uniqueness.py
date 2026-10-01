"""Regressions-Tests zum Einzigartigkeits-Audit (Issue #490, 01.10.2026).

ANLASS: Der Quartalslauf meldete 10 „kritische" Bestandsüberlappungen. Die
Nachprüfung zeigte zwei verschiedene Fehlerklassen in EINER Liste:

  1. MESSFEHLER – die Wache zählte Dinge, die kein Duplicate Content sind:
     · Ankertexte interner Links (`internal_linker.py` setzt dort per
       Konstruktion den TITEL des Zielartikels – zwei Ratgeber, die denselben
       Pillar verlinken, „teilten" dadurch bis zu acht 7-Wort-Phrasen),
     · zurückgespiegelte Prompt-Köpfe der KI-Auffrischung
       („ARTIKEL-TITEL: …", in acht Live-Artikeln gelandet),
     · Entwürfe (draft: true), die Hugo gar nicht baut und die deshalb
       weder indexiert werden noch kannibalisieren können.
  2. ECHTE DOPPLUNG – gleiche Sätze, Tabellen und Kennzahl-Formulierungen in
     zwei veröffentlichten Artikeln. Die gehören umgeschrieben.

Eine Wache, die beides gleich laut meldet, wird nicht abgearbeitet. Diese
Tests frieren die Trennung ein – gegen einen SYNTHETISCHEN Korpus, nie gegen
den Live-Bestand (sonst wäre der Test vom Tagesgeschäft abhängig).

Ausführung:  python3 -m unittest discover -s scripts/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_uniqueness as cu
import template_boilerplate as tb


class SelbsttestTests(unittest.TestCase):
    """Der eingebaute Sabotage-Schutz muss grün sein – sonst misst nichts."""

    def test_selbsttest_gruen(self):
        self.assertEqual(cu.run_selftest(), [])

    def test_boilerplate_selbsttest_gruen(self):
        self.assertEqual(tb.run_selftest(), [])


class BefundKlassenTests(unittest.TestCase):
    """live↔live ist ein Bestandsschaden, Entwürfe sind eine Vorab-Aufgabe."""

    def test_live_paar_ab_fuenf_phrasen_kritisch(self):
        self.assertEqual(cu.paar_klasse(5, False, False), "kritisch")
        self.assertEqual(cu.paar_klasse(30, False, False), "kritisch")

    def test_entwurf_beteiligt_eigene_klasse(self):
        for a, b in ((True, False), (False, True), (True, True)):
            self.assertEqual(cu.paar_klasse(9, a, b), "entwurf",
                             f"draft-Kombination {a}/{b}")

    def test_standardformulierungen_bleiben_unkritisch(self):
        self.assertEqual(cu.paar_klasse(1, False, False), "ok")
        self.assertEqual(cu.paar_klasse(4, False, False), "unkritisch")

    def test_schwelle_ist_benannt_und_inklusiv(self):
        self.assertEqual(cu.KRITISCH_AB, 5)
        self.assertEqual(cu.paar_klasse(cu.KRITISCH_AB - 1, False, False),
                         "unkritisch")
        self.assertEqual(cu.paar_klasse(cu.KRITISCH_AB, False, False),
                         "kritisch")


class NavigationZaehltNichtTests(unittest.TestCase):
    """Interne Verlinkung darf nicht als Duplikat bestraft werden."""

    ZIEL = "So findest du den richtigen DSL-Tarif für dein Zuhause"

    def _artikel(self, eigener_satz: str) -> str:
        return (
            "---\ntitle: \"T\"\ndraft: false\n---\n\n"
            f"{eigener_satz}\n\n"
            f"**Weiterlesen:** [{self.ZIEL}]"
            "(../../posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif/)\n"
        )

    def test_gleicher_anker_erzeugt_keine_ueberlappung(self):
        a = cu.clean_body(self._artikel(
            "Der Wechselbonus ist bei Bestandskunden oft die einzige Stelle, "
            "an der sich Verhandeln noch messbar auszahlt."))
        b = cu.clean_body(self._artikel(
            "Im Keller entscheidet die Technik, im Vertrag entscheidet der "
            "Effektivpreis über 24 Monate."))
        gemeinsam = cu.ngrams(a, cu.PHRASE_LEN) & cu.ngrams(b, cu.PHRASE_LEN)
        self.assertEqual(gemeinsam, set(),
                         f"Ankertext zählt noch als Fließtext: {gemeinsam}")

    def test_externer_linktext_bleibt_messbar(self):
        satz = ("Laut [Bundesnetzagentur](https://www.bundesnetzagentur.de/) "
                "musst du Preisänderungen transparent angekündigt bekommen.")
        a = cu.clean_body("---\ntitle: \"A\"\n---\n\n" + satz)
        b = cu.clean_body("---\ntitle: \"B\"\n---\n\n" + satz)
        gemeinsam = cu.ngrams(a, cu.PHRASE_LEN) & cu.ngrams(b, cu.PHRASE_LEN)
        self.assertTrue(gemeinsam,
                        "Externe Linktexte sind Redaktion – echte Dopplung "
                        "rund um Quellenangaben darf nicht verschwinden")


class EchteDopplungBleibtSichtbarTests(unittest.TestCase):
    """Gegenprobe: Der Strip darf keine echte Textdopplung schlucken."""

    SATZ = ("Der BDEW nennt für 2026 bislang durchschnittlich 11,93 Cent pro "
            "Kilowattstunde im Einfamilienhaus und dieser Wert bildet den "
            "Markt ab.")

    def test_gleicher_fliesstext_wird_kritisch(self):
        a = cu.clean_body("---\ntitle: \"A\"\ndraft: false\n---\n\n" + self.SATZ)
        b = cu.clean_body("---\ntitle: \"B\"\ndraft: false\n---\n\n" + self.SATZ)
        overlap = len(cu.ngrams(a, cu.PHRASE_LEN) & cu.ngrams(b, cu.PHRASE_LEN))
        self.assertGreaterEqual(overlap, cu.KRITISCH_AB)
        self.assertEqual(cu.paar_klasse(overlap, False, False), "kritisch")

    def test_eigene_formulierung_derselben_kennzahl_ist_sauber(self):
        """Die Zahl darf überall stehen – der Satz darum muss eigen sein."""
        a = cu.clean_body("---\ntitle: \"A\"\n---\n\n" + self.SATZ)
        b = cu.clean_body(
            "---\ntitle: \"B\"\n---\n\n"
            "Zur Einordnung: Im Einfamilienhaus lag der Gaspreis 2026 laut "
            "BDEW im Mittel bei 11,93 Cent je Kilowattstunde.")
        overlap = len(cu.ngrams(a, cu.PHRASE_LEN) & cu.ngrams(b, cu.PHRASE_LEN))
        self.assertLess(overlap, cu.KRITISCH_AB)


if __name__ == "__main__":
    unittest.main()
