#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regressionstests der Markdown-Struktur-Wache (#1263).

Anlass: Sechs Live-Artikel trugen eine FAQ-Frage am Ende des vorigen
Absatzes (`… dauerhaft.### Was kostet ein Kontowechsel?`). Markdown rendert
das als Fließtext – aber `extend_head.html` splittet das FAQ-Schema an der
ZEICHENKETTE `### `, nicht an Zeilenanfängen. Die Frage stand damit im
JSON-LD und nicht auf der Seite: strukturierte Daten, die etwas anderes
behaupten als das Dokument.

Diese Tests halten drei Dinge fest:
  1. Die Klasse wird erkannt (M1–M3), mit Zeile und Spalte.
  2. Legitimes `#` (Code, Hashtags, Fragmente, `C#`) klagt NICHT an –
     eine Wache, die bei jedem Hashtag rot wird, wird abgeschaltet.
  3. Die eine Ausnahme aus #1263 ist befristet, benannt und läuft ab;
     sie verdeckt keine andere Regel derselben Datei.
"""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import markdown_struktur_wache as m  # noqa: E402

HEUTE = _dt.date(2026, 11, 22)
GAS = ("content/posts/2026-10-02-gasabschlag-berechnen-so-planst-du-"
       "die-heizsaison-richtig/index.md")

GUT = """---
title: "Probe"
---

Ein Absatz.

## Überschrift

Noch ein Absatz.

## Häufige Fragen

### Was kostet das?
Eine Antwort mit ausreichend Text.
"""


class ErkennungTest(unittest.TestCase):
    def regeln(self, text: str, datei: str = "content/posts/x/index.md") -> list[str]:
        return sorted({b["regel"] for b in m.pruefe_text(text, datei, HEUTE)})

    def test_sauberes_markdown_ist_gruen(self) -> None:
        self.assertEqual([], self.regeln(GUT))

    def test_geklebte_ueberschrift_ist_m1(self) -> None:
        """VOR dem FAQ-Abschnitt: reiner M1-Fall."""
        text = GUT.replace("Ein Absatz.", "Ein Absatz.### Frage?")
        befunde = m.pruefe_text(text, "content/posts/x/index.md", HEUTE)
        self.assertEqual(["M1"], [b["regel"] for b in befunde])
        self.assertEqual(5, befunde[0]["zeile"])

    def test_geklebt_im_faq_ist_m1_und_m3(self) -> None:
        """IM FAQ wiegt es doppelt: kaputte Seite UND falsches Schema.

        Der Absatz mit der geklebten Frage steht NACH der FAQ-Überschrift –
        genau die Lage der sechs Fundstellen aus #1263.
        """
        text = GUT.replace(
            "Eine Antwort mit ausreichend Text.",
            "Eine Antwort.### Was ist der Unterschied?")
        befunde = m.pruefe_text(text, "content/posts/x/index.md", HEUTE)
        self.assertEqual(["M1", "M3"], [b["regel"] for b in befunde])
        self.assertEqual(14, befunde[0]["zeile"])

    def test_raute_ohne_trenner_ist_m2(self) -> None:
        text = GUT.replace("## Überschrift", "##Überschrift")
        self.assertEqual(["M2"], self.regeln(text))

    def test_ueberschrift_am_zeilenanfang_ist_kein_fund(self) -> None:
        text = GUT.replace("## Überschrift", "### Überschrift")
        self.assertEqual([], self.regeln(text))

    def test_verschachtelte_ueberschrift_ist_kein_fund(self) -> None:
        """`### Frage?` innerhalb des FAQ ist die RICHTIGE Form."""
        self.assertEqual([], self.regeln(GUT))

    def test_einrueckung_ist_kein_fund(self) -> None:
        text = GUT.replace("## Überschrift", "  ## Überschrift")
        self.assertEqual([], self.regeln(text))

    def test_code_block_ist_kein_fund(self) -> None:
        self.assertEqual([], self.regeln("```\nnpm ### x\n```\n"))

    def test_hashtag_ist_kein_fund(self) -> None:
        self.assertEqual([], self.regeln("Ein Absatz über #finanzen.\n"))

    def test_link_mit_fragment_ist_kein_fund(self) -> None:
        self.assertEqual([], self.regeln("Siehe [FAQ](/posts/x/#antwort).\n"))

    def test_c_sharp_ist_kein_fund(self) -> None:
        self.assertEqual([], self.regeln("Wir schreiben C# und F#.\n"))

    def test_zitatzeile_ist_kein_fund(self) -> None:
        self.assertEqual([], self.regeln("> Zitat mit ### darin\n"))

    def test_tabelle_ist_kein_fund(self) -> None:
        self.assertEqual([], self.regeln("| a | b ### c |\n|---|---|\n"))

    def test_flow_frage_im_faq_ist_m1_und_m3(self) -> None:
        text = GUT.replace("### Was kostet das?",
                           "### Was kostet das? Antwort.### Und wann?")
        self.assertEqual(["M1", "M3"], self.regeln(text))


class BefristungTest(unittest.TestCase):
    """Der Ablauf-Mechanismus der befristeten Ausnahme (#1263).

    23.11.2026: Der einzige echte Eintrag (Gasabschlag) ist entfallen – `main`
    hat die geklebte Überschrift in #1329 (`371835702`) geheilt, `erhebe()`
    findet im Bestand 0 Funde. Eine Ausnahme, die einen nicht mehr
    existierenden Befund schützt, wird ab ihrem Stichtag rot, ohne dass
    jemand etwas geändert hat.

    Was bleibt, ist der MECHANISMUS – und der wird hier weiter geprüft, mit
    einer synthetischen Ausnahme. Sonst wäre die nächste echte Ausnahme
    ungeprüft, und genau davor soll die Wache schützen.
    """

    PROBE = "content/posts/__test__/index.md"
    EINTRAG = {"datei": PROBE, "bis": "2027-01-31",
               "grund": "Testfall für den Ablauf-Mechanismus."}

    def _mit_probe(self):
        """Kontext: die Probe-Ausnahme gilt nur innerhalb des Tests."""
        import contextlib

        @contextlib.contextmanager
        def _cm():
            m.BEFRISTET.append(self.EINTRAG)
            try:
                yield
            finally:
                m.BEFRISTET.remove(self.EINTRAG)
        return _cm()

    def test_stelle_wird_erkannt(self) -> None:
        text = GUT.replace("Noch ein Absatz.", "Noch ein Absatz.### Frage?")
        self.assertTrue(m.pruefe_text(text, self.PROBE, HEUTE),
                        "die zurückgestellte Stelle läuft durch die Prüfung")

    def test_vor_ablauf_ist_sie_bekannt(self) -> None:
        f = [{"regel": "M1", "zeile": 191, "spalte": 1, "text": ""}]
        with self._mit_probe():
            e = m.vergleiche({self.PROBE: f}, {self.PROBE: f}, HEUTE)
        self.assertEqual([], e["neu"], "vor dem Stichtag kein neuer Befund")
        self.assertEqual([self.PROBE], e["bekannt"])

    def test_nach_ablauf_ist_sie_neu(self) -> None:
        nach_ablauf = _dt.date(2027, 2, 1)
        f = [{"regel": "M1", "zeile": 191, "spalte": 1, "text": ""}]
        with self._mit_probe():
            self.assertTrue(m.befristet_abgelaufen(nach_ablauf),
                            "die abgelaufene Ausnahme wird benannt")
            e = m.vergleiche({self.PROBE: f}, {self.PROBE: f}, nach_ablauf)
        self.assertEqual([self.PROBE], e["neu"], "fail-closed nach dem Stichtag")
        self.assertEqual([self.PROBE], e["ablauf"])

    def test_gilt_nur_fuer_ihre_datei(self) -> None:
        f = [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]
        with self._mit_probe():
            e = m.vergleiche({"content/posts/anderer/index.md": f}, {}, HEUTE)
        self.assertEqual(["content/posts/anderer/index.md"], e["neu"])

    def test_jede_echte_befristung_hat_datum_und_grund(self) -> None:
        for e in m.BEFRISTET:
            self.assertTrue(_dt.date.fromisoformat(e["bis"]))
            self.assertTrue(e["grund"].strip())

    def test_befristung_ist_nicht_ewig(self) -> None:
        for e in m.BEFRISTET:
            bis = _dt.date.fromisoformat(e["bis"])
            self.assertLess(bis, _dt.date(2027, 12, 31),
                            f"Befristung {e['datei']} läuft zu lange")

    def test_probe_ist_wieder_weg(self) -> None:
        """Kein Zustand leckt: die Probe-Ausnahme lebt nur im Test."""
        with self._mit_probe():
            self.assertIn(self.EINTRAG, m.BEFRISTET)
        self.assertNotIn(self.EINTRAG, m.BEFRISTET)


class KlinkeTest(unittest.TestCase):
    def test_bekannt_bleibt_still(self) -> None:
        f = [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]
        self.assertEqual([], m.vergleiche({"a": f}, {"a": f})["neu"])

    def test_neuer_fund_wird_gemeldet(self) -> None:
        f = [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]
        self.assertEqual(["a"], m.vergleiche({"a": f}, {})["neu"])

    def test_heilung_rastet_ein(self) -> None:
        f = [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]
        self.assertEqual(["a"], m.vergleiche({}, {"a": f})["geheilt"])

    def test_zusaetzliche_fundstelle_ist_neu(self) -> None:
        alt = [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]
        neu = alt + [{"regel": "M1", "zeile": 9, "spalte": 1, "text": ""}]
        self.assertEqual(["a"], m.vergleiche({"a": neu}, {"a": alt})["neu"])

    def test_neuer_fund_wird_nicht_eingefroren(self) -> None:
        alt = [{"regel": "M1", "zeile": 5, "spalte": 1, "text": ""}]
        neu = alt + [{"regel": "M1", "zeile": 9, "spalte": 1, "text": ""}]
        self.assertEqual(alt, m.klinke_einrasten({"a": neu}, {"a": alt})["a"])


class BestandTest(unittest.TestCase):
    """Gegenprobe am echten Bestand."""

    def test_bestand_hat_keine_neuen_funde(self) -> None:
        """Gegenprobe am echten Bestand – mit Stichtag.

        `heute` MUSS an `vergleiche` gehen: Ohne Datum greift die Befristung
        aus #1263 nicht, und die eine bewusst zurückgestellte Stelle wird als
        „neu" gemeldet. Genau das ist im CI rot geworden (22.11.2026) – der
        Test hat die Klinke geprüft, aber ohne den Parameter, der sie
        steuert. Hier steht deshalb derselbe Stichtag wie in der Erhebung.
        """
        stand, dateien = m.erhebe(heute=HEUTE)
        self.assertGreater(dateien, 100, "zu wenige Inhaltsdateien")
        ergebnis = m.vergleiche(stand, m.lade_baseline(), HEUTE)
        self.assertEqual([], ergebnis["neu"],
                         f"neue Markdown-Struktur-Funde: {ergebnis['neu']}")
        self.assertEqual([], ergebnis["ablauf"],
                         "die Befristung ist abgelaufen – die Stelle muss "
                         "jetzt geheilt oder neu verhandelt werden")

    def test_alle_fuenf_reparierten_stellen_bleiben_repariert(self) -> None:
        """#1263 nennt sechs Dateien; fünf sind geheilt und dürfen es bleiben."""
        namen = [
            "2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren",
            "2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss",
            "2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest",
            "2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit",
            "2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet",
        ]
        funde = []
        for name in namen:
            pfad = ROOT / "content" / "posts" / name / "index.md"
            if not pfad.is_file():
                continue
            if m.datei_pruefen(pfad, HEUTE):
                funde.append(name)
        self.assertEqual([], funde, f"wieder geklebte Überschriften: {funde}")


class CliTest(unittest.TestCase):
    def _lauf(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "markdown_struktur_wache.py"),
             *args], capture_output=True, text=True, cwd=ROOT)

    def test_selftest_gruen(self) -> None:
        lauf = self._lauf("--selftest")
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)

    def test_json_ist_sauber_parsebar(self) -> None:
        lauf = self._lauf("--json")
        self.assertEqual(0, lauf.returncode, lauf.stderr)
        daten = json.loads(lauf.stdout)     # Selftest-Bericht darf nicht stören
        for feld in ("dateien", "fundstellen", "neu", "bekannt", "geheilt",
                     "befristet_abgelaufen"):
            self.assertIn(feld, daten)

    def test_json_schreibt_weder_baseline_noch_historie(self) -> None:
        """23.11.2026: `--json` ist eine ABFRAGE, kein Lauf.

        Der Fehler, der den regression-Job riss: `--json` schrieb die
        Baseline neu – auf 0 Einträge, weil der Bestand sauber war. Der
        nächste Test fand eine leere Baseline und wurde rot. Der Fehler saß
        nicht im Test, sondern im Schreibpfad der Wache. `--seed` friert
        ein, ein Lauf ohne Maschinenformat rastet ein; `--json`/`--md`
        berichten nur.
        """
        baseline = ROOT / "data" / "markdown_baseline.json"
        hist = ROOT / "data" / "markdown_history.jsonl"
        vorher_b = baseline.read_text(encoding="utf-8") if baseline.exists() else None
        vorher_h = hist.read_text(encoding="utf-8") if hist.exists() else None
        lauf = self._lauf("--json")
        self.assertEqual(0, lauf.returncode, lauf.stderr)
        nachher_b = baseline.read_text(encoding="utf-8") if baseline.exists() else None
        nachher_h = hist.read_text(encoding="utf-8") if hist.exists() else None
        self.assertEqual(vorher_b, nachher_b,
                         "`--json` hat die Baseline verändert")
        self.assertEqual(vorher_h, nachher_h,
                         "`--json` hat die Historie verändert")

    def test_dry_run_schreibt_nichts(self) -> None:
        hist = ROOT / "data" / "markdown_history.jsonl"
        vorher = hist.read_text(encoding="utf-8") if hist.exists() else ""
        lauf = self._lauf("--dry-run")
        nachher = hist.read_text(encoding="utf-8") if hist.exists() else ""
        self.assertEqual(0, lauf.returncode, lauf.stderr)
        self.assertEqual(vorher, nachher)


if __name__ == "__main__":
    unittest.main()
