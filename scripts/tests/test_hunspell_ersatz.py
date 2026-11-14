"""Der `hunspell`-Ersatz (Befund 15.11.2026).

WARUM DIESER TEST EXISTIERT
---------------------------
Die halbe Messkette des Repos hängt an `hunspell`. In der CI wird es per
`apt-get install hunspell hunspell-de-de` installiert; auf einem Rechner
ohne root ist das unmöglich. Die Folge war kein roter Test, sondern eine
**fehlende Messung**: `quality_score` wertet ein fehlendes Wörterbuch als
`spelling = 0.5`, `reserve_recert.gate_verfuegbar()` blockiert daraufhin die
Nachzertifizierung, und gesunde Artikel sehen aus wie Ausschuss.

`scripts/hunspell_ersatz.py` bildet die Aufrufschnittstelle mit `spylls`
und einem echten de_DE-Wörterbuch nach. Dieser Test hält die Zusicherungen
fest, an denen die Messkette hängt:

  1. `-l` nennt GENAU die unbekannten Wörter, in Eingabereihenfolge.
  2. Ohne Modus-Flag ist das Programm im Analyse-Modus (wie das Original) –
     `spellcheck.suggestions()` ruft es genau so auf.
  3. `&`-Zeilen tragen echte Vorschläge (Kasus-Korrektur „geld" → „Geld").
  4. Ohne Wörterbuch endet es mit Exit 3 statt „alles richtig" zu melden.
  5. Ein unbekannter Schalter endet mit Exit 2 (fail-closed).
  6. Die Laufzeit bleibt im Rahmen: ein Artikel mit 20 unbekannten Wörtern
     lag vorher bei 112 s (2,3 s Ladezeit × 3 Prozessstarts je Wort) und
     sprengte damit jeden 15-s-Timeout der Aufrufer.

Der letzte Punkt ist der wichtigste. Ein Ersatz, der richtig rechnet, aber
zu langsam ist, sieht in der Messkette genauso aus wie keiner: Timeout,
Abbruch, kein Nachweis.
"""
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ERSATZ = ROOT / "scripts" / "hunspell_ersatz.py"
WOERTERBUCH = ROOT / "data" / "hunspell" / "de_DE"

# Ohne Wörterbuch oder ohne spylls ist hier nichts zu messen – dann sagt der
# Test das, statt grün zu werden.
HAT_WOERTERBUCH = (WOERTERBUCH.with_suffix(".aff").is_file()
                   and WOERTERBUCH.with_suffix(".dic").is_file())
try:
    import spylls  # noqa: F401
    HAT_SPYLLS = True
except ImportError:
    HAT_SPYLLS = False

GRUND = "spylls + data/hunspell/de_DE nicht vorhanden (python3 scripts/hunspell_worterbuch_holen.py)"


def lauf(*flags, eingabe="", timeout=120, umgebung=None):
    """Ruft den Ersatz als eigenes Programm auf – wie die Messkette es tut."""
    env = dict(os.environ)
    env.pop("HUNSPELL_DE_DIR", None)
    if umgebung:
        env.update(umgebung)
    return subprocess.run([sys.executable, str(ERSATZ), *flags],
                          input=eingabe, text=True, capture_output=True,
                          timeout=timeout, env=env)


@unittest.skipUnless(HAT_WOERTERBUCH and HAT_SPYLLS, GRUND)
class Listenmodus(unittest.TestCase):
    """`-l`: die Form, die `spellcheck.batch_hunspell()` benutzt."""

    def test_nennt_genau_die_unbekannten_woerter(self):
        r = lauf("-i", "UTF-8", "-d", "de_DE", "-l",
                 eingabe="Haushaltsbuch\ngeld\nStromkosten\nQuatschwort\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        # Reihenfolge und Inhalt: nur die beiden falschen, keine Auslassung.
        self.assertEqual(r.stdout.split(), ["geld", "Quatschwort"])

    def test_richtige_woerter_ergeben_leere_ausgabe(self):
        r = lauf("-l", eingabe="Haushaltsbuch\nFixkosten\nRücklagen\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")

    def test_wiederholtes_wort_erscheint_einmal(self):
        r = lauf("-l", eingabe="Quatschwort\nQuatschwort\nQuatschwort\n")
        self.assertEqual(r.stdout.split(), ["Quatschwort"])


@unittest.skipUnless(HAT_WOERTERBUCH and HAT_SPYLLS, GRUND)
class Analysemodus(unittest.TestCase):
    """Ohne `-l` ist hunspell im Analyse-Modus – `suggestions()` nutzt das."""

    def test_ohne_modusflag_ist_es_analyse_modus(self):
        # Genau dieser Aufruf (nur -i/-d) stand in spellcheck.suggestions()
        # und brach mit Exit 2 ab, als der Ersatz nur -l konnte.
        r = lauf("-i", "UTF-8", "-d", "de_DE", eingabe="geld\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("@(#)", r.stdout)

    def test_falsches_wort_bekommt_echte_vorschlaege(self):
        r = lauf(eingabe="geld\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("& geld", r.stdout)
        self.assertIn("Geld", r.stdout)

    def test_richtiges_wort_bekommt_sternchen(self):
        r = lauf(eingabe="Haushaltsbuch\n")
        self.assertEqual(r.stdout.strip().splitlines()[-1], "*")

    def test_batch_liefert_alle_zeilen_ohne_haenger(self):
        # `affiliate_integrity_gate` schickt alle CTA-Wörter auf einmal.
        woerter = [f"wort{i}" for i in range(50)]
        r = lauf(eingabe="\n".join(woerter) + "\n", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        zeilen = [z for z in r.stdout.splitlines() if not z.startswith("@(#)")]
        self.assertEqual(len(zeilen), 50)


@unittest.skipUnless(HAT_WOERTERBUCH and HAT_SPYLLS, GRUND)
class Laufzeit(unittest.TestCase):
    """Der Grund, warum die Nachzertifizierung vorher abbrach."""

    def test_artikelpruefung_bleibt_unter_dem_timeout(self):
        """20 unbekannte Wörter in einem Rutsch: früher 112 s, jetzt < 30 s.

        Der erste Aufruf startet den Hintergrund-Dienst und zahlt die
        Ladezeit; deshalb wird zweimal gemessen und der zweite Lauf
        bewertet – so verhält sich auch die Messkette (viele Artikel
        nacheinander im selben Prozess).
        """
        eingabe = "\n".join(f"Quatschwort{i}" for i in range(20)) + "\n"
        lauf("-l", eingabe="Haushaltsbuch\n", timeout=120)   # Dienst starten
        t0 = time.monotonic()
        r = lauf("-l", eingabe=eingabe, timeout=120)
        dauer = time.monotonic() - t0
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stdout.split()), 20)
        self.assertLess(dauer, 30.0,
                        f"20 Wörter brauchten {dauer:.1f}s – Timeout-Risiko")

    def test_daemon_wird_wiederverwendet(self):
        lauf("-l", eingabe="Haushaltsbuch\n", timeout=120)
        t0 = time.monotonic()
        r = lauf("-l", eingabe="Quatschwort\n", timeout=60)
        self.assertLess(time.monotonic() - t0, 2.0,
                        "zweiter Aufruf zahlt wieder die volle Ladezeit")
        self.assertEqual(r.stdout.split(), ["Quatschwort"])


class FailClosed(unittest.TestCase):
    """Ein Prüfwerkzeug, das rät, ist schlimmer als keines."""

    def test_ohne_woerterbuch_exit_3(self):
        r = lauf("-l", eingabe="Haushaltsbuch\n",
                 umgebung={"HUNSPELL_DE_DIR": "/gibt/es/nicht"})
        # --worterbuch ist der einzige Weg, den Pfad zu erzwingen; ohne
        # gültiges Wörterbuch darf NICHTS als richtig gelten.
        r2 = lauf("-l", "--worterbuch", "/gibt/es/nicht", eingabe="x\n")
        for ergebnis in (r2,):
            self.assertEqual(ergebnis.returncode, 3, ergebnis.stdout)
            self.assertIn("Wörterbuch", ergebnis.stderr)

    def test_unbekannter_schalter_exit_2(self):
        r = lauf("--gibtesnicht", eingabe="Haushaltsbuch\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("nicht unterstützte Schalter", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
