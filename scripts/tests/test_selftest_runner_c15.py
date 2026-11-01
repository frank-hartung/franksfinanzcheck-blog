#!/usr/bin/env python3
"""C15-Arbeitsbaum-Wache des Selbsttest-Runners (Dauerheilung WF-D4E0 #983).

HINTERGRUND
-----------
Am 31.10.2026 machte der nächtliche Vorrat rot, weil `copy_editing_gate.py
--selftest` über `lektor_guard.py` eine Zeile an `data/lektor_history.jsonl`
hängte – ein Prüflauf, der nebenbei heilt (Vertragsregel C15). Der Runner
(`selftest_runner.py`) fing das über seinen Arbeitsbaum-Vergleich
(`nachher − vorher`) und #987 gab dem Lektor einen reinen Beweispfad.

Diese Suite schließt die KLASSE an der Wächter-Wache selbst. Befund bei der
Analyse: `arbeitsbaum()` las nur die `git status`-ZEILE (`M pfad`). Eine Datei,
die ein früherer Schritt schon geändert hatte, bleibt `M pfad`, auch wenn ein
Selbsttest sie EIN WEITERES MAL beschreibt – der Vergleich blieb leer, der
zweite Schreibvorgang war unsichtbar. `copy_editing_gate.py` härte sich seit
#987 mit einem Inhalts-Abdruck (Status + SHA-256); diese Suite hält den Runner
auf demselben Stand und beweist die Grenzen (kein Falschalarm, fail-closed ohne
Git, bewusst ignorierte Reports).

Ausführung:  python3 -m unittest scripts.tests.test_selftest_runner_c15 -v
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import selftest_runner as runner  # noqa: E402


class ArbeitsbaumC15Test(unittest.TestCase):
    """Jede Spur, die ein schreibender Selbsttest hinterlässt, muss sichtbar sein."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="c15-runner-")
        self.addCleanup(self._aufraeumen)
        self._git("init", "-q", ".")
        self._git("config", "user.email", "selftest@local")
        self._git("config", "user.name", "selftest")

    def _aufraeumen(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(("git", "-C", self.tmp, *args),
                              capture_output=True, text=True, timeout=60)

    def _schreiben(self, rel: str, text: str) -> None:
        pfad = Path(self.tmp) / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")

    def _haengen(self, rel: str, text: str) -> None:
        with open(Path(self.tmp) / rel, "a", encoding="utf-8") as fh:
            fh.write(text)

    def _versionieren(self, rel: str, text: str) -> None:
        self._schreiben(rel, text)
        self._git("add", rel)
        self._git("commit", "-qm", f"baseline {rel}")

    def _delta(self, vorher: set) -> set:
        nachher = runner.arbeitsbaum(self.tmp)
        self.assertIsNotNone(nachher, "Git antwortet – arbeitsbaum darf nicht None sein")
        return nachher - vorher

    # ------------------------------------------------------------------ Kernfälle

    def test_append_an_saubere_chronik_wird_gesehen(self) -> None:
        """Der nackte #983-Fall: Append an eine saubere, versionierte Chronik."""
        self._versionieren("data/lektor_history.jsonl", '{"baseline": 1}\n')
        vorher = runner.arbeitsbaum(self.tmp)
        self._haengen("data/lektor_history.jsonl", '{"selftest heilt": 2}\n')
        delta = self._delta(vorher)
        self.assertTrue(delta, "Append an saubere Chronik muss C15 auslösen")
        self.assertTrue(any("lektor_history.jsonl" in s for s in delta))

    def test_append_an_schon_geaenderter_chronik_wird_gesehen(self) -> None:
        """DIE Lücke, die #983 erst vollständig schließt: die Datei war schon
        vorher geändert. Die Statuszeile bleibt `M …jsonl` – nur der Inhalts-
        Abdruck sieht den zweiten Append. Ohne ihn wäre delta leer."""
        self._versionieren("chronik.jsonl", '{"baseline": 1}\n')
        self._haengen("chronik.jsonl", '{"frueherer schritt": 2}\n')  # schon schmutzig
        vorher = runner.arbeitsbaum(self.tmp)
        self.assertTrue(any("chronik.jsonl" in s for s in vorher),
                        "Ausgangslage: Datei ist bereits geändert")
        self._haengen("chronik.jsonl", '{"selftest heilt": 3}\n')      # der Beweis-Append
        delta = self._delta(vorher)
        self.assertTrue(delta, "Append an schon geänderte Datei war bisher unsichtbar")
        self.assertTrue(any("chronik.jsonl" in s for s in delta))

    def test_gleiche_statuszeile_aber_anderer_inhalt_ist_anderer_abdruck(self) -> None:
        """Mechanismus direkt: zwei Inhalte derselben schmutzigen Datei ergeben
        zwei verschiedene Arbeitsbaum-Mengen (Status allein wäre identisch)."""
        self._versionieren("chronik.jsonl", "A\n")
        self._haengen("chronik.jsonl", "B\n")
        zustand_b = runner.arbeitsbaum(self.tmp)
        self._haengen("chronik.jsonl", "C\n")
        zustand_c = runner.arbeitsbaum(self.tmp)
        self.assertNotEqual(zustand_b, zustand_c,
                            "Inhaltsänderung muss den Abdruck ändern, nicht nur die Zeile")

    def test_neue_unversionierte_datei_wird_gesehen(self) -> None:
        vorher = runner.arbeitsbaum(self.tmp)
        self._schreiben("heiler-rest.md", "x")
        delta = self._delta(vorher)
        self.assertTrue(any("heiler-rest.md" in s for s in delta))

    def test_leeres_verzeichnis_unter_content_wird_gesehen(self) -> None:
        """Git meldet leere Ordner nie – die eigene Spur muss sie fangen
        (reale Hugo-Build-Lücke vom 03.10.2026)."""
        vorher = runner.arbeitsbaum(self.tmp)
        os.makedirs(Path(self.tmp) / "content" / "entwuerfe")
        delta = self._delta(vorher)
        self.assertTrue(any("LEERES VERZEICHNIS content/entwuerfe" in s for s in delta))

    def test_geloeschte_datei_wird_gesehen(self) -> None:
        self._versionieren("data/weg.json", "{}\n")
        vorher = runner.arbeitsbaum(self.tmp)
        os.remove(Path(self.tmp) / "data" / "weg.json")
        delta = self._delta(vorher)
        self.assertTrue(any("weg.json" in s for s in delta))

    # ------------------------------------------------------------------ Grenzen

    def test_sauberer_leselauf_ist_kein_falschalarm(self) -> None:
        """Ein Selbsttest, der nur liest, hinterlässt keine Spur – sonst würde
        die Wache jeden grünen Lauf rot reden."""
        self._versionieren("data/chromik.jsonl", '{"baseline": 1}\n')
        self._haengen("data/chromik.jsonl", '{"schmutzig": 2}\n')
        vorher = runner.arbeitsbaum(self.tmp)
        # zweiter, rein lesender Durchlauf:
        delta = self._delta(vorher)
        self.assertFalse(delta, "Reines Lesen darf keinen C15-Befund erzeugen")

    def test_ohne_git_ist_none_fail_closed(self) -> None:
        """Ohne beweiskräftiges Git darf die Wache nicht still 'grün' sein."""
        ohne = tempfile.mkdtemp(prefix="c15-ohne-git-")
        self.addCleanup(lambda: __import__("shutil").rmtree(ohne, ignore_errors=True))
        self.assertIsNone(runner.arbeitsbaum(ohne),
                          "Ein Nicht-Git-Verzeichnis muss None liefern (fail-closed)")

    def test_ignorierter_report_ist_bewusst_ausserhalb_der_wache(self) -> None:
        """Bewusste Grenze (wie copy_editing_gate seit #987): Reports sind per
        .gitignore ausgenommen – sie werden je Lauf neu geschrieben und sind
        kein Betriebszustand. Ein Selbsttest, der NUR einen ignorierten Report
        schreibt, ist kein C15-Befund. Diese Grenze ist hier festgehalten,
        damit eine künftige Änderung sie bewusst trifft, nicht versehentlich."""
        self._versionieren(".gitignore", ".copy_editing_report.json\n")
        vorher = runner.arbeitsbaum(self.tmp)
        self._schreiben(".copy_editing_report.json", '{"report": true}')
        delta = self._delta(vorher)
        self.assertFalse(any(".copy_editing_report.json" in s for s in delta),
                         "Ignorierte Reports liegen bewusst außerhalb von C15")

    def test_pfad_mit_leerzeichen_wird_korrekt_gelesen(self) -> None:
        """-z liest unquotierte Pfade: ein Pfad mit Leerzeichen darf nicht
        zerfallen (sonst zeigt die Wache auf die falsche Datei)."""
        self._versionieren("data/mit leerzeichen.jsonl", "1\n")
        vorher = runner.arbeitsbaum(self.tmp)
        self._haengen("data/mit leerzeichen.jsonl", "2\n")
        delta = self._delta(vorher)
        self.assertTrue(any("mit leerzeichen.jsonl" in s for s in delta))

    def test_umbenennung_verursacht_keinen_fehlalarm_auf_den_quellpfad(self) -> None:
        """Bei einer Umbenennung folgt der Quellpfad als eigenes -z-Feld.
        Er darf nicht als eigenständige, fehlgelesene Spur auftauchen."""
        self._versionieren("alt.jsonl", "1\n")
        self._git("mv", "alt.jsonl", "neu.jsonl")
        zustand = runner.arbeitsbaum(self.tmp)
        self.assertIsNotNone(zustand)
        # Der neue Pfad ist erfasst; der Quellpfad wird nicht als eigene Datei
        # mit Inhalt fehlgelesen (kein 'alt.jsonl#<hash>' als separate Spur).
        self.assertTrue(any("neu.jsonl" in s for s in zustand))
        self.assertFalse(any(s.endswith("alt.jsonl#—") for s in zustand),
                         "Quellpfad der Umbenennung darf nicht als fehlgelesene Spur erscheinen")


if __name__ == "__main__":
    unittest.main(verbosity=2)
