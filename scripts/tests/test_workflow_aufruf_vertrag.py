#!/usr/bin/env python3
"""Vertragstests für `scripts/workflow_aufruf_vertrag.py`.

Der Befund (14.11.2026): Der Deploy rief `ki_audio_markierung.py --check`, das
Werkzeug kannte nur `--gate`. Exit 2, Werkzeugbefund, dauerhaft rotes Siegel –
bei gesundem Inhalt. Diese Suite hält vier Eigenschaften der Wache fest:

  A1  ein gelöschtes Werkzeug ist rot,
  A2  ein unbekannter Schalter ist rot,
  der Rest bleibt grün (Kommentar, `--`, verschachtelter Aufruf, Adapter),
  A4  eine Weiterleitung, die niemand braucht, ist selbst ein Befund.

Die letzte Prüfung läuft gegen den ECHTEN Bestand: Der Vertrag muss im Repo
erfüllt sein. Wer einen Workflow mit einem fremden Schalter hinzufügt, sieht
es hier – nicht erst am roten Siegel.
"""
from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import workflow_aufruf_vertrag as wav  # noqa: E402

WERKZEUG = """\
import argparse
def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--gate", "--check", dest="gate", action="store_true")
    p.add_argument("--dir", default=".")
    p.add_argument("--selftest", action="store_true")
    return p.parse_args()
"""

# Ein Werkzeug, das `sys.argv` direkt liest – die im Repo häufigste Form.
WERKZEUG_ARGV = """\
import sys
def main():
    if "--fix" in sys.argv:
        return 1
    print("prüfen")
    return 0
"""


class Vertrag(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / "data").mkdir()
        (self.root / "scripts" / "werkzeug.py").write_text(WERKZEUG, encoding="utf-8")
        (self.root / "scripts" / "argv_werkzeug.py").write_text(WERKZEUG_ARGV,
                                                                encoding="utf-8")
    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _workflow(self, run: str) -> None:
        (self.root / ".github" / "workflows" / "wf.yml").write_text(
            "on: push\njobs:\n  j:\n    runs-on: ubuntu-24.04\n    steps:\n"
            "      - name: s\n        run: |\n"
            + textwrap.indent(run.strip("\n"), "          ") + "\n",
            encoding="utf-8")

    def _funde(self) -> list[dict]:
        return wav.befunde(self.root)[0]

    # ------------------------------------------------------------- A2: rot
    def test_unbekannter_schalter_ist_ein_befund(self) -> None:
        self._workflow("python3 scripts/werkzeug.py --gibtesnicht --dir x")
        funde = self._funde()
        self.assertEqual(len(funde), 1, funde)
        self.assertEqual(funde[0]["art"], "A2")
        self.assertIn("--gibtesnicht", funde[0]["meldung"])

    def test_argv_werkzeug_wird_ebenfalls_geprueft(self) -> None:
        """Auch ohne argparse: Ein Name, der nirgends steht, ist ein No-Op."""
        self._workflow("python3 scripts/argv_werkzeug.py --fix --erfunden")
        funde = self._funde()
        self.assertEqual([f["art"] for f in funde], ["A2"], funde)
        self.assertIn("--erfunden", funde[0]["meldung"])

    # ------------------------------------------------------------ A1: rot
    def test_fehlendes_skript_ist_ein_befund(self) -> None:
        self._workflow("python3 scripts/geloescht.py --gate")
        funde = self._funde()
        self.assertEqual([f["art"] for f in funde], ["A1"], funde)

    # ------------------------------------------------------------ grün
    def test_gueltiger_aufruf_ist_gruen(self) -> None:
        self._workflow("python3 scripts/werkzeug.py --dir public\n"
                       "python3 scripts/argv_werkzeug.py --fix")
        self.assertEqual(self._funde(), [])

    def test_alias_ist_gruen(self) -> None:
        self._workflow("python3 scripts/werkzeug.py --check")
        self.assertEqual(self._funde(), [])

    def test_shell_kommentar_ist_kein_aufruf(self) -> None:
        self._workflow("# python3 scripts/werkzeug.py --nur-im-kommentar\n"
                       "python3 scripts/werkzeug.py --gate")
        self.assertEqual(self._funde(), [])

    def test_backslash_fortsetzung_wird_gezogen(self) -> None:
        self._workflow("python3 scripts/werkzeug.py \\\n    --dir public")
        self.assertEqual(self._funde(), [])
        self._workflow("python3 scripts/werkzeug.py \\\n    --erfunden")
        self.assertEqual([f["art"] for f in self._funde()], ["A2"])

    def test_verschachtelter_aufruf_erbt_keine_schalter(self) -> None:
        """Schalter hinter einem zweiten Skriptaufruf gehören dem Kind.

        Hausform: `reserve_operations.py … --run python3 scripts/reserve_intake.py
        --apply` (argparse.REMAINDER). Ohne diese Grenze erbte der Wrapper die
        Schalter des Kindes – real 4 von 17 Fehlalarmen am 14.11.2026.
        """
        (self.root / "scripts" / "kind.py").write_text(WERKZEUG, encoding="utf-8")
        self._workflow("python3 scripts/argv_werkzeug.py --fix "
                       "python3 scripts/kind.py --gate")
        self.assertEqual(self._funde(), [])
        # Gegenprobe: Ein fremder Schalter des KINDES muss weiter auffallen.
        self._workflow("python3 scripts/argv_werkzeug.py --fix "
                       "python3 scripts/kind.py --erfunden")
        self.assertEqual([f["art"] for f in self._funde()], ["A2"])
        self.assertIn("--erfunden", self._funde()[0]["meldung"])

    def test_doppelstrich_beendet_die_optionen(self) -> None:
        self._workflow("python3 scripts/werkzeug.py --gate -- "
                       "python3 scripts/werkzeug.py --selftest")
        self.assertEqual(self._funde(), [])

    def test_variable_wird_nicht_geraten(self) -> None:
        self._workflow("python3 scripts/werkzeug.py $FLAG")
        self.assertEqual(self._funde(), [])

    # ------------------------------------------------------------ Adapter
    def test_weiterleitung_uebernimmt_die_schalter_des_ziels(self) -> None:
        (self.root / "scripts" / "adapter.py").write_text(WERKZEUG, encoding="utf-8")
        (self.root / "data" / "workflow_aufruf_weiterleitung.yaml").write_text(
            "adapter:\n  adapter.py:\n    ziel: werkzeug.py\n    grund: Testfall\n",
            encoding="utf-8")
        self._workflow("python3 scripts/adapter.py --selftest")
        self.assertEqual(self._funde(), [])

    def test_ungenutzte_weiterleitung_ist_ein_befund(self) -> None:
        (self.root / "scripts" / "adapter.py").write_text(WERKZEUG, encoding="utf-8")
        (self.root / "data" / "workflow_aufruf_weiterleitung.yaml").write_text(
            "adapter:\n  adapter.py:\n    ziel: werkzeug.py\n    grund: Testfall\n",
            encoding="utf-8")
        self._workflow("python3 scripts/werkzeug.py --gate")
        self.assertEqual([f["art"] for f in self._funde()], ["A4"], self._funde())

    # ------------------------------------------------------- echter Bestand
    def test_vertrag_gilt_im_ganzen_repo(self) -> None:
        funde, zahlen = wav.befunde(ROOT)
        self.assertGreater(zahlen["geprueft"], 100,
                           "die Wache hat kaum Aufrufe geprüft – Detektor defekt?")
        self.assertEqual(funde, [], "\n".join(f["meldung"] for f in funde))


if __name__ == "__main__":
    unittest.main()
