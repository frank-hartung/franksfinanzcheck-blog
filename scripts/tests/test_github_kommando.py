#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vertragstests des Kommando-Melders (WF-E813/#815, 27.10.2026).

Drei Zusagen, jeweils mit Gegenprobe:

1. FLUCHTSCHUTZ: Ein Befund bleibt EIN Kommando. Zeilenumbrüche, `%`, `,`
   und `:` in Dateinamen, Titeln und Texten können kein zweites Kommando
   erzeugen und keine Eigenschaft (z. B. `line=`) einschmuggeln.
2. TESTSTILLE: Ein Prozess unter `unittest`/`pytest` sendet nichts, auch
   wenn er in GitHub Actions läuft. Genau diese Lücke ließ den grünen Job
   „Abhängigkeiten“ in Lauf 40499567144 drei rote Annotationen tragen.
3. NOTAUSGANG: `GITHUB_KOMMANDOS=an|aus` schlägt jede Automatik – in beide
   Richtungen. Ohne diesen Schalter wäre die Stille nicht mehr aufhebbar.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import github_kommando as gk  # noqa: E402


def ausgabe(funktion, *args, **kwargs):
    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        ergebnis = funktion(*args, **kwargs)
    return ergebnis, puffer.getvalue()


class FluchtschutzTest(unittest.TestCase):
    def test_einfaches_kommando(self) -> None:
        self.assertEqual(gk.kommando("error", "Header fehlt"), "::error::Header fehlt")

    def test_eigenschaften_in_fester_reihenfolge(self) -> None:
        zeile = gk.kommando("warning", "Text", datei="content/a.md", zeile=7,
                            titel="Wache A1")
        self.assertEqual(zeile, "::warning file=content/a.md,line=7,title=Wache A1::Text")

    def test_zeilenumbruch_erzeugt_kein_zweites_kommando(self) -> None:
        """Der Runner liest Kommandos ZEILENWEISE – also darf es nur eine geben."""
        boese = "Befund\n::error::erfunden\r\n::warning::auch erfunden"
        zeile = gk.kommando("error", boese)
        self.assertEqual(len(zeile.splitlines()), 1, "Ein Befund ist EINE Zeile")
        self.assertTrue(zeile.startswith("::error::"), zeile)
        self.assertIn("%0A", zeile, "LF muss kodiert sein")
        self.assertIn("%0D", zeile, "CR muss kodiert sein")
        self.assertNotIn("\n", zeile)
        self.assertNotIn("\r", zeile)

    def test_prozentzeichen_wird_nicht_doppelt_gedeutet(self) -> None:
        zeile = gk.kommando("error", "Quote 100% – %0A ist nur Text")
        self.assertIn("100%25", zeile)
        self.assertNotIn("100%", zeile.replace("100%25", ""))

    def test_dateiname_kann_keine_eigenschaft_einschmuggeln(self) -> None:
        """Der Runner trennt Eigenschaften am `,` – ein `,` im Wert darf nicht
        als Trenner wirken. Geprüft wird die Eigenschaftsliste, nicht der Text:
        nach dem Trennen müssen es GENAU drei Eigenschaften sein."""
        zeile = gk.kommando("error", "Text", datei="requirements-x.txt,line=999,title=gefälscht",
                            zeile=1, titel="Wache")
        kopf, _, nutzlast = zeile.partition("::Text")
        self.assertEqual(nutzlast, "", "Der Text ist die Nutzlast, nicht Teil der Eigenschaften")
        eigenschaften = kopf.split(" ", 1)[1].split(",")
        self.assertEqual(eigenschaften, [
            "file=requirements-x.txt%2Cline=999%2Ctitle=gefälscht",
            "line=1",
            "title=Wache",
        ])

    def test_titel_kann_kein_kommando_einschmuggeln(self) -> None:
        zeile = gk.kommando("error", "Text", titel="a::b\n::error::c")
        self.assertEqual(len(zeile.splitlines()), 1)
        self.assertNotIn("\n", zeile)
        self.assertIn("a%3A%3Ab", zeile)

    def test_unbekannte_ebene_wird_abgelehnt(self) -> None:
        with self.assertRaises(ValueError):
            gk.kommando("fatal", "Text")

    def test_leere_eigenschaften_erscheinen_nicht(self) -> None:
        self.assertEqual(gk.kommando("notice", "Text", datei="", titel=""), "::notice::Text")


class AktivTest(unittest.TestCase):
    def test_lokal_ohne_runner_still(self) -> None:
        self.assertFalse(gk.aktiv({"PATH": "/usr/bin"}, {}))

    def test_in_actions_ohne_testrunner_laut(self) -> None:
        self.assertTrue(gk.aktiv({"GITHUB_ACTIONS": "true"}, {}))

    def test_unter_unittest_still_auch_in_actions(self) -> None:
        self.assertFalse(gk.aktiv({"GITHUB_ACTIONS": "true"}, {"unittest": object()}))

    def test_unter_pytest_still_auch_in_actions(self) -> None:
        self.assertFalse(gk.aktiv({"GITHUB_ACTIONS": "true"}, {"pytest": object()}))

    def test_notausgang_an_schlaegt_automatik(self) -> None:
        self.assertTrue(gk.aktiv({"GITHUB_KOMMANDOS": "an"}, {"unittest": object()}))
        self.assertTrue(gk.aktiv({"GITHUB_KOMMANDOS": " AN "}, {}))

    def test_notausgang_aus_schlaegt_actions(self) -> None:
        self.assertFalse(gk.aktiv({"GITHUB_ACTIONS": "true", "GITHUB_KOMMANDOS": "aus"}, {}))
        self.assertFalse(gk.aktiv({"GITHUB_ACTIONS": "true", "GITHUB_KOMMANDOS": "off"}, {}))

    def test_actions_wert_wird_nicht_geraten(self) -> None:
        self.assertFalse(gk.aktiv({"GITHUB_ACTIONS": "false"}, {}))
        self.assertFalse(gk.aktiv({"GITHUB_ACTIONS": "1"}, {}))


class AnnotationTest(unittest.TestCase):
    def test_erzwingen_sendet_kommando_und_meldet_true(self) -> None:
        gesendet, text = ausgabe(gk.annotation, "error", "Befund", datei="a.md",
                                zeile=3, erzwingen=True)
        self.assertTrue(gesendet)
        self.assertEqual(text, "::error file=a.md,line=3::Befund\n")

    def test_ohne_runner_nur_klartext_und_false(self) -> None:
        gesendet, text = ausgabe(gk.annotation, "warning", "Keine Auth", datei="a.md",
                                zeile=3)
        self.assertFalse(gesendet)
        self.assertNotIn("::", text)
        self.assertEqual(text, "[warning] a.md:3: Keine Auth\n")

    def test_klartext_ohne_ort(self) -> None:
        self.assertEqual(gk.klartext("notice", "ok"), "[notice] ok")
        self.assertEqual(gk.klartext("error", "x", zeile=4), "[error] Zeile 4: x")

    def test_klartext_traegt_denselben_inhalt_wie_das_kommando(self) -> None:
        """Lokal lesbar, was in CI annotiert würde – nichts geht verloren."""
        self.assertEqual(
            gk.klartext("error", "Befund", datei="a.md", zeile=3, titel="Wache A1"),
            "[error] Wache A1: a.md:3: Befund")


class ProbeTest(unittest.TestCase):
    def test_probe_zeigt_zustand_und_faerbt_nichts(self) -> None:
        status, text = ausgabe(gk.main, ["--probe"])
        self.assertEqual(status, 0)
        self.assertIn("Workflow-Kommandos: AUS", text)
        self.assertEqual([z for z in text.splitlines() if z.startswith("::")], [],
                         "Die Selbstdiagnose darf selbst kein Kommando senden")
        self.assertIn("%0A", text, "Das Beispiel muss kodiert gezeigt werden")


class BetriebsBeweisTest(unittest.TestCase):
    """Die drei falschen Annotationen aus Lauf 40499567144 dürfen nicht
    wiederkommen: Ein Testbaum, der die Wache absichtlich vergiftet, darf im
    Log des laufenden Jobs kein einziges Workflow-Kommando hinterlassen."""

    def _keine_kommandos(self, funktion, *args, **kwargs):
        _, text = ausgabe(funktion, *args, **kwargs)
        kommandos = [z for z in text.splitlines() if z.startswith("::")]
        self.assertEqual(kommandos, [], f"Workflow-Kommando aus einem Test: {kommandos}")
        return text

    def test_abhaengigkeits_wache_ist_im_test_still(self) -> None:
        import tempfile

        from scripts import abhaengigkeits_wache as wache

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "requirements-x.txt").write_text("pyyaml>=6.0\n", encoding="utf-8")
            self.assertEqual(wache.main(["--check", "--root", tmp]), 1)
            self._keine_kommandos(wache.main, ["--check", "--root", tmp])

    def test_abhaengigkeits_wache_meldet_in_actions_wieder(self) -> None:
        """Gegenprobe: Mit ausdrücklicher Ansage ist das Kommando da."""
        import tempfile

        from scripts import abhaengigkeits_wache as wache

        alt = {k: os.environ.get(k) for k in ("GITHUB_ACTIONS", "GITHUB_KOMMANDOS")}
        try:
            os.environ["GITHUB_ACTIONS"] = "true"
            os.environ["GITHUB_KOMMANDOS"] = "an"
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "requirements-x.txt").write_text("pyyaml>=6.0\n",
                                                              encoding="utf-8")
                puffer = io.StringIO()
                with contextlib.redirect_stdout(puffer):
                    wache.main(["--check", "--root", tmp])
                kommandos = [z for z in puffer.getvalue().splitlines() if z.startswith("::")]
        finally:
            for schluessel, wert in alt.items():
                if wert is None:
                    os.environ.pop(schluessel, None)
                else:
                    os.environ[schluessel] = wert
        self.assertTrue(kommandos, "Ohne Kommando wäre der Notausgang wirkungslos")
        self.assertTrue(any(z.startswith("::error file=requirements-x.txt,line=1")
                            for z in kommandos), kommandos)


if __name__ == "__main__":
    unittest.main()
