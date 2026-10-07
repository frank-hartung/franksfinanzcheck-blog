"""Regressionstests für den Politur-Heiler und die Marker-Klasse (BOT-WATCHDOG #614).

Warum diese Tests existieren
----------------------------
`data/reserve-readiness.json` meldete am 07.10.2026 „Ziel 6, bereit 2" – und
zehn Kandidaten waren geparkt. Drei davon trugen einen **harten**
Textverständnis-Fund, für den es keinen Heiler gab (R14-Marker-Ruine „SATZ:",
R7-Intro-Formel, R15-PHrasen-Doppel). Weil das Tor T2 des Lesbarkeits-Heilers
(`lesbarkeit_heiler.verifiziere`) jede Schrift verwirft, die danach noch einen
harten Fund trägt, war jede KI-Heilung dieser Artikel von vornherein
aussichtslos: Der Heiler hatte eine Deckung, aber keine Wirkung.

Diese Datei friert die Zusagen des neuen Heilers und der Vorbeugung ein:

1) **Wirkung** – die Wirkungsprobe heilt die reale Ruinen-Klasse (R7/R11/R13/
   R14/R15/R16) und beweist das als Maschinenvertrag (`--wirkungsprobe`), ohne
   Netz, ohne Hugo, ohne API-Kontingent. Dieselbe Probe verlangt C25.
2) **Fail-closed** – das Tor T1–T3 schreibt nichts, was einen neuen harten
   Fund einführt, nichts behoben hat oder die Form verletzt; ein Trockenlauf
   fasst keine Datei an und meldet den offenen Punkt trotzdem (Exit 1).
3) **Vorbeugung an der Quelle** – die Prompt-Vorlagen in `lektor_guard.py`
   beginnen mit „SATZ: {satz}". Antwortet das Modell mit genau diesem
   Präfix, wird es entfernt, BEVOR es zur Zeile im Artikel wird. Die Marker
   kommen aus der SSOT `sprachkern.POLITUR_RUINEN` – geraten wird nichts.
4) **Verdrahtung** – die Kette fährt den Heiler VOR dem Lesbarkeits-Heiler
   (genau deshalb, weil dessen Tor T2 Rest-Hartfunde verwirft), die Deckung
   kennt ihn, das Regelwerk verlangt ihn.

Alle Tests laufen ohne Netz, ohne hugo, ohne API-Keys und ohne Schreiben in
den Bestand (Fixtures liegen in temporären Verzeichnissen).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import politur_heiler as ph  # noqa: E402
import sprachkern as sk  # noqa: E402


def _lauf(*args: str, timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "politur_heiler.py"),
                           *args], cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout)


MARKER_FIXTURE = (
    "---\n"
    "title: \"Probe: Marker-Ruine\"\n"
    "date: 2026-10-07\n"
    "draft: true\n"
    "reserve: true\n"
    "---\n\n"
    "## Überblick\n\n"
    "Stell dir vor, du senkst die Kosten in wenigen Minuten.\n\n"
    "| Gerät | Leistung |\n"
    "|-------|----------|\n"
    "SATZ: | Funk | 0,5 Watt |\n"
    "\n"
    "Der Vergleich beginnt mit dem eigenen Verbrauch. Notiere jede Position, "
    "damit jede Aussage nachrechenbar bleibt.\n"
)


class WirkungTests(unittest.TestCase):
    """Die Wirkung ist der Punkt – eine Deckung ohne sie ist Papier."""

    def test_selftest_des_heilers_gruen(self):
        r = _lauf("--selftest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_wirkungsprobe_als_maschinenvertrag(self):
        r = _lauf("--wirkungsprobe", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        daten = json.loads(r.stdout)
        self.assertTrue(daten["ok"], daten)
        self.assertTrue(set(daten["regeln"]) <= set(ph.HEILBARE_REGELN))

    def test_regelliste_ist_aus_der_ssot_gelesen(self):
        """Regeln und Schwellen sind gelesen, nicht abgetippt (SSOT)."""
        import publish_gate as pg
        import textverstaendnis_guard as tv
        ruinen = {name for name, _muster, _text in sk.POLITUR_RUINEN}
        self.assertTrue(ruinen - {"R12-ZAHL-RUINE"} <= set(ph.HEILBARE_REGELN),
                        "eine Ruine der SSOT hat keinen Heiler mehr")
        self.assertTrue(set(ph.HEILBARE_REGELN) <= set(pg.HARTE_REGELN),
                        "der Heiler fährt weiche Regeln – die lohnen keinen Umbau")
        self.assertIn("R7-INTRO-FORMEL", ph.HEILBARE_REGELN)
        self.assertIn("R15-PHRASEN-DOPPEL", ph.HEILBARE_REGELN)
        self.assertTrue(tv.INTRO_FORMELN, "R7-SSOT ist leer")
        self.assertEqual(ph.R15_N, tv.R15_N, "R15-Schwelle abgetippt statt importiert")


class HeilungTests(unittest.TestCase):
    """Heilen, ohne zu schaden: Form, Idempotenz, Trockenlauf."""

    def test_marker_ruine_faellt_tabellenzeile_bleibt(self):
        ergebnis = ph.heile_text("probe", MARKER_FIXTURE)
        self.assertTrue(ergebnis["ok"], ergebnis["gruende"])
        neu = ergebnis["neu_raw"]
        self.assertNotIn("SATZ:", neu)
        self.assertIn("| Funk | 0,5 Watt |", neu)
        self.assertNotIn("R14-MARKER-RUINE",
                         {f.split(":", 1)[0] for f in ergebnis["rest"]})

    def test_frontmatter_bleibt_byte_gleich(self):
        alt, neu = ph.PROBE_FIXTURE, ph.heile_text("probe", ph.PROBE_FIXTURE)["neu_raw"]
        self.assertEqual(alt.split("---", 2)[1], neu.split("---", 2)[1])

    def test_trockenlauf_schreibt_nicht_und_meldet(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "index.md"
            pfad.write_text(ph.PROBE_FIXTURE, encoding="utf-8")
            vorher = pfad.read_bytes()
            r = _lauf("--file", str(pfad), "--json")
            self.assertEqual(r.returncode, 1, "--fix fehlt – der offene Punkt "
                                              "muss trotzdem Befund sein")
            self.assertEqual(vorher, pfad.read_bytes(),
                             "der Trockenlauf hat den Artikel angefasst")

    def test_zweiter_lauf_ist_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "index.md"
            pfad.write_text(ph.PROBE_FIXTURE, encoding="utf-8")
            self.assertEqual(_lauf("--file", str(pfad), "--fix").returncode, 0)
            nach_heilung = pfad.read_bytes()
            r = _lauf("--file", str(pfad), "--fix")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(nach_heilung, pfad.read_bytes())

    def test_verworfene_heilung_wird_nie_geschrieben(self):
        """Fail-closed: was das Tor verwirft (hier: zu starke Kürzung durch die
        R15-Heilung), bleibt liegen und wird als offener Punkt gemeldet."""
        zu_kurz = ("---\ntitle: \"Probe\"\ndate: 2026-10-07\ndraft: true\n---\n\n"
                   "Dein Weg zu geringeren im Check: Dein Weg zu geringeren im "
                   "Check: Dein Weg zu geringeren im Check – und noch ein Satz "
                   "mit genug Wörtern für die Wiederholungs-Erkennung des "
                   "Wächters, damit die Sequenz wirklich doppelt vorkommt.\n")
        ergebnis = ph.heile_text("probe", zu_kurz)
        self.assertFalse(ergebnis["ok"])
        self.assertTrue(ergebnis["gruende"], "ein verworfener Text braucht Gründe")
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "index.md"
            pfad.write_text(zu_kurz, encoding="utf-8")
            vorher = pfad.read_bytes()
            r = _lauf("--file", str(pfad), "--fix")
            self.assertEqual(vorher, pfad.read_bytes(),
                             "das Tor hat verworfen, aber die Datei wurde geschrieben")
            self.assertEqual(r.returncode, 1,
                             "verworfene Heilung ist ein offener Punkt, kein grüner Lauf")


class QuellVorbeugungTests(unittest.TestCase):
    """R14/R16 entstehen in `lektor_guard.py` – dort muss die Vorbeugung greifen."""

    def _alternativen(self, regel: str) -> list[str]:
        """Die Marker-Wörter genau aus der SSOT-Regel ziehen (nicht abtippen)."""
        for name, muster, _text in sk.POLITUR_RUINEN:
            if name != regel:
                continue
            treffer = re.search(r"\(([A-Z0-9]+(?:\|[A-Z0-9]+)+)\)", muster.pattern)
            self.assertIsNotNone(treffer, f"{regel}: Alternativen nicht lesbar – "
                                          "SSOT-Format geändert?")
            return treffer.group(1).split("|")
        self.fail(f"{regel} fehlt in sprachkern.POLITUR_RUINEN")

    def test_jeder_marker_der_ssot_verschwindet_am_zeilenanfang(self):
        import lektor_guard as lg
        for regel in ("R14-MARKER-RUINE", "R16-PROMPT-ECHO"):
            for marker in self._alternativen(regel):
                satz = f"{marker}: Die Kasse hebt den Beitrag jedes Jahr an."
                rest = lg._ohne_marker_echo(satz)
                self.assertEqual(rest,
                                 "Die Kasse hebt den Beitrag jedes Jahr an.",
                                 f"{marker}: konnte nicht entfernt werden")
                muster = [m for n, m, _ in sk.POLITUR_RUINEN if n == regel][0]
                self.assertIsNone(muster.search(rest),
                                  f"{marker}: würde weiter als Ruine gelten")

    def test_normaler_satz_und_kleinschreibung_bleiben_unberuehrt(self):
        import lektor_guard as lg
        for satz in ("Die Kasse hebt den Beitrag jedes Jahr an.",
                     "Satz: bleibt unangetastet (kein SSOT-Marker).",
                     "Marktwirtschaft bleibt Marktwirtschaft."):
            self.assertEqual(satz, lg._ohne_marker_echo(satz))

    def test_nur_marker_ohne_inhalt_wird_leer_und_nie_geschrieben(self):
        import lektor_guard as lg
        self.assertEqual("", lg._ohne_marker_echo("SATZ:"),
                         "eine Zeile, die nur ein Marker wäre, darf nicht durch")
        self.assertEqual("Die Kasse hebt den Beitrag.",
                         lg._ohne_marker_echo("```SATZ: Die Kasse hebt den "
                                              "Beitrag.```"))


class VerdrahtungTests(unittest.TestCase):
    """Deckung heißt Wirkung: Kette, Deckung, Vertrag und Workflow kennen ihn."""

    def test_kette_faehrt_politur_vor_lesbarkeit(self):
        import reserve_finisher as rf
        namen = [e[0] for e in rf.HEALER_CHAIN]
        self.assertIn("politur_heiler.py", namen)
        eintrag = [e for e in rf.HEALER_CHAIN if e[0] == "politur_heiler.py"][0]
        self.assertIn("--fix", eintrag[1])
        self.assertEqual(eintrag[2], "file")
        self.assertLess(namen.index("politur_heiler.py"),
                        namen.index("lesbarkeit_heiler.py"),
                        "der Lesbarkeits-Heiler würde die Heilung sonst als "
                        "Rest-Hartfund verwerfen")

    def test_ordnung_ist_durch_das_T2_tor_begruendet(self):
        """Der Grund der Reihenfolge ist messbar, nicht Geschmack."""
        import lesbarkeit_heiler as lh
        vorher = lh.harte_funde(ph.PROBE_FIXTURE, "probe")
        self.assertTrue(vorher, "Fixture trägt keinen harten Fund – Test blind")
        geheilt = ph.heile_text("probe", ph.PROBE_FIXTURE)["neu_raw"]
        self.assertEqual(set(), lh.harte_funde(geheilt, "probe"),
                         "nach der Politur darf kein Rest-Hartfund übrig sein, "
                         "sonst verwirft T2 jede KI-Heilung")

    def test_deckung_kennt_den_heiler_und_beweist_ihn(self):
        import reserve_healer_coverage as rhc
        b = rhc.volldeckung()
        gedeckt = {e["regel"]: e["heiler"] for e in b["gedeckt"]}
        self.assertIn("politur_heiler.py", gedeckt.get("textverstaendnis_failures", []))
        self.assertEqual([], b["wirkung"]["luecken"])
        self.assertTrue(b["wirkung"]["nachgewiesen"])

    def test_governance_verlangt_den_heiler(self):
        import governance_contract as gc
        import selftest_runner as sr
        self.assertIn("politur_heiler.py", gc.GUARDS)
        self.assertEqual([], sr.verdrahtet("politur_heiler.py"),
                         "das Regelwerk verlangt den Heiler, aber er läuft nicht")

    def test_content_reserve_faehrt_die_kette(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "content-reserve.yml").read_text(encoding="utf-8")
        self.assertIn("reserve_finisher.py --finish", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=1)
