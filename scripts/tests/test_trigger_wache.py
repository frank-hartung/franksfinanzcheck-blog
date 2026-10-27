#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vertragstests der Trigger-Wache (WF-E813/#815, 27.10.2026).

WARUM DIESE TESTS EXISTIEREN
----------------------------
Die Wache selbst ist nur so gut wie ihre zwei Zusagen:

1. SIE SIEHT, WAS EIN LAUF AUFRUFT. Der Parser liest nur einen Ausschnitt
   von YAML – ohne PyYAML, weil der Lauf, in dem sie läuft, keine
   Abhängigkeiten installiert. Ein Ausschnitt-Parser, der anders liest als
   ein vollständiger, wäre die nächste stille Wache. Deshalb wird er bei
   JEDEM Lauf gegen PyYAML verglichen (Schritt „Parser-Gegenprobe“), sofern
   das Modul vorhanden ist.
2. SIE FEUERT UND SCHWEIGT AM RICHTIGEN ORT. Für jede Regel (W1 Referenz,
   W2 Waise, W3 Symmetrie) gibt es einen vergifteten Baum, in dem genau
   diese Regel anschlägt – und einen sauberen, in dem sie schweigt.

Der wichtigste Test ist der dritte: **DER ECHTE BESTAND IST SAUBER.** Er
hält die am 27.10.2026 gefundenen zwölf Lücken geschlossen. Wer einen
Prüfer aus einem Workflow aufruft, ohne ihn in den `paths`-Filter zu
schreiben, macht diesen Test rot – und nicht erst irgendwann ein Gate, das
nicht anspringt.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import trigger_wache as wache  # noqa: E402

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover - lokal ohne requirements-ci
    yaml = None


def workflow(pfade_push, pfade_pr=None, *, quelle: str = "scripts/probe.py",
             ereignis: str = "push") -> str:
    def block(name: str, liste) -> list[str]:
        return [f"  {name}:", "    paths:"] + [f'      - "{p}"' for p in liste]

    zeilen = ["name: Probe", "on:"]
    zeilen += block(ereignis, pfade_push)
    if pfade_pr is not None:
        zeilen += block("pull_request", pfade_pr)
    zeilen += [
        "",
        "jobs:",
        "  pruefen:",
        "    runs-on: ubuntu-24.04",
        "    steps:",
        "      - name: Ausführen",
        "        run: |",
        "          set -euo pipefail",
        f"          python3 {quelle} --selftest",
    ]
    return "\n".join(zeilen) + "\n"


class KleinerBaum:
    """Wegwerf-Repository: echte Dateien, echte Workflow-Dateien."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        for name in ("probe.py", "anders.py"):
            (self.root / "scripts" / name).write_text("", encoding="utf-8")
        (self.root / ".github" / "workflows").mkdir(parents=True)

    def workflow(self, name: str, inhalt: str) -> None:
        (self.root / ".github" / "workflows" / name).write_text(inhalt, encoding="utf-8")

    def __enter__(self) -> "KleinerBaum":
        return self

    def __exit__(self, *_):
        self._tmp.cleanup()


class BestandTest(unittest.TestCase):
    def test_selftest_gruen(self) -> None:
        self.assertEqual(wache.main(["--selftest"]), 0)

    def test_dauervertrag_bestand_ohne_befund(self) -> None:
        """DAUERVERTRAG: Kein Workflow ruft einen Prüfer auf, den sein Filter
        nicht auslöst; kein Filter zeigt ins Leere; push und pull_request
        tragen dieselbe Liste."""
        befunde = wache.pruefe(ROOT)
        self.assertEqual(befunde, [], "\n".join(
            f"{b.regel} · {b.workflow} ({b.ereignis}): {b.text}" for b in befunde))

    def test_check_exit_null_auf_dem_bestand(self) -> None:
        self.assertEqual(wache.main(["--check", "--root", str(ROOT)]), 0)

    def test_md_bericht_ist_markdown_und_nennt_die_anzahl(self) -> None:
        text = wache.bericht([], len(wache.workflow_dateien(ROOT)))
        self.assertTrue(text.startswith("# Trigger-Wache"))
        self.assertIn(f"Workflows geprüft: **{len(wache.workflow_dateien(ROOT))}**", text)

    @unittest.skipIf(yaml is None, "PyYAML nicht installiert (requirements-ci)")
    def test_parser_liest_wie_pyyaml(self) -> None:
        """Gegenprobe gegen den vollständigen YAML-Parser, Datei für Datei.

        Formatvielfalt ist der Feind eines Ausschnitt-Parsers. Deshalb wird
        nicht ein Beispiel verglichen, sondern JEDER Workflow des Bestands –
        Ereignismenge, `paths` und `paths-ignore`.
        """
        geprueft = 0
        for datei in wache.workflow_dateien(ROOT):
            text = datei.read_text(encoding="utf-8")
            mein = wache.trigger(text)
            # PyYAML 1.1 liest das Schlüsselwort `on` als Wahrheitswert True;
            # BaseLoader liefert die Zeichenketten so, wie sie dastehen.
            geladen = yaml.load(text, Loader=yaml.BaseLoader)
            self.assertIsInstance(geladen, dict, datei)
            soll = geladen.get("on")
            if not isinstance(soll, dict):
                self.assertEqual(mein, {}, f"{datei.name}: Ereignisform nicht gelesen")
                continue
            self.assertEqual(sorted(mein), sorted(soll), f"{datei.name}: Ereignismenge")
            for ereignis, conf in soll.items():
                for art in ("paths", "paths-ignore"):
                    erwartet = conf.get(art, []) if isinstance(conf, dict) else []
                    self.assertEqual(sorted(mein[ereignis].get(art, [])),
                                     sorted(str(wert) for wert in erwartet),
                                     f"{datei.name}: {ereignis}.{art}")
            geprueft += 1
        self.assertGreater(geprueft, 50, "Der Bestand hat zu wenige Workflows für diese Probe")


class RegelTest(unittest.TestCase):
    def test_w1_meldet_fehlenden_pfad(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("rot.yml", workflow(["scripts/anders.py"]))
            befunde = wache.pruefe(baum.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_REFERENZ])
        self.assertIn("scripts/probe.py", befunde[0].text)

    def test_w1_schweigt_wenn_gedeckt(self) -> None:
        for muster in ("scripts/probe.py", "scripts/*.py", "scripts/**", "**/*.py"):
            with self.subTest(muster=muster), KleinerBaum() as baum:
                baum.workflow("gruen.yml", workflow([muster]))
                self.assertEqual(wache.pruefe(baum.root), [])

    def test_w1_gilt_fuer_beide_ereignisse(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("halb.yml", workflow(["scripts/anders.py"],
                                               ["scripts/anders.py"]))
            befunde = wache.pruefe(baum.root)
        self.assertEqual(sorted(b.ereignis for b in befunde), ["pull_request", "push"])

    def test_workflow_ohne_pfadfilter_ist_immer_gedeckt(self) -> None:
        """Ein Lauf ohne `paths` springt bei jeder Änderung an – nichts zu prüfen."""
        with KleinerBaum() as baum:
            baum.workflow("immer.yml",
                          "name: Immer\non:\n  push:\n    branches: [main]\n"
                          "jobs:\n  a:\n    runs-on: ubuntu-24.04\n    steps:\n"
                          "      - run: python3 scripts/probe.py\n")
            self.assertEqual(wache.pruefe(baum.root), [])

    def test_w2_meldet_toten_trigger(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("waise.yml", workflow(["scripts/probe.py", "docs/weg.md"]))
            befunde = wache.pruefe(baum.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_WAISE])
        self.assertIn("docs/weg.md", befunde[0].text)

    def test_w2_ignoriert_platzhalter(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("platzhalter.yml", workflow(["scripts/probe.py", "docs/**"]))
            self.assertEqual(wache.pruefe(baum.root), [])

    def test_w3_meldet_einseitige_liste(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("schief.yml", workflow(["scripts/probe.py"],
                                                 ["scripts/probe.py", "scripts/anders.py"]))
            befunde = wache.pruefe(baum.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_SYMMETRIE])
        self.assertIn("scripts/anders.py", befunde[0].text)
        self.assertIn("`push`", befunde[0].text)

    def test_w3_schweigt_bei_gleicher_liste(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("gleich.yml", workflow(["scripts/probe.py"], ["scripts/probe.py"]))
            self.assertEqual(wache.pruefe(baum.root), [])

    def test_fliessform_wird_gemeldet_statt_geraten(self) -> None:
        with KleinerBaum() as baum:
            baum.workflow("fliess.yml", "on:\n  push:\n    paths: [scripts/probe.py]\n")
            self.assertEqual(wache.main(["--check", "--root", str(baum.root)]), 2)


class AufrufTest(unittest.TestCase):
    def test_inline_und_blockform_und_unittest_module(self) -> None:
        with KleinerBaum() as baum:
            (baum.root / "scripts" / "tests").mkdir()
            (baum.root / "scripts" / "tests" / "test_c.py").write_text("", encoding="utf-8")
            text = (
                "jobs:\n  a:\n    steps:\n"
                "      - run: python3 scripts/probe.py\n"
                "      - run: |\n"
                "          python3 -m unittest scripts.tests.test_c\n"
            )
            self.assertEqual(wache.aufrufe(text, baum.root),
                             {"scripts/probe.py", "scripts/tests/test_c.py"})

    def test_kommentar_und_fehlende_datei_zaehlen_nicht(self) -> None:
        with KleinerBaum() as baum:
            text = ("jobs:\n  a:\n    steps:\n"
                    "      - run: |\n"
                    "          # python3 scripts/anders.py\n"
                    "          python3 scripts/gibt-es-nicht.py\n")
            self.assertEqual(wache.aufrufe(text, baum.root), set())

    def test_gedeckt_kennt_die_beiden_glob_formen(self) -> None:
        self.assertTrue(wache.gedeckt("scripts/a.py", ["scripts/*.py"]))
        self.assertTrue(wache.gedeckt("scripts/tests/a.py", ["scripts/**"]))
        self.assertFalse(wache.gedeckt("scripts/tests/a.py", ["scripts/*.py"]))
        self.assertFalse(wache.gedeckt("tools/a.py", ["scripts/**"]))


if __name__ == "__main__":
    unittest.main()
