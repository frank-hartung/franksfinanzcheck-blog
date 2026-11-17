#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Marken-Lauf muss die Flächen sehen, die er BEURTEILT (17.11.2026).

WARUM DIESE TESTS EXISTIEREN
----------------------------
`entity_marken_gate.py --source-only` prüft E6 über `content/**` und
`layouts/**`: Jede Falschschreibung der Marke („Franks Finanzcheck“ statt
„FranksFinanzcheck“) ist ein harter Fehler. Der Workflow triggerte aber nur
auf Marken-Flächen (`content/ueber/**`, `hugo.toml`, `static/llms.txt` …) –
Beiträge standen nicht in der Liste.

Am 17.11.2026 hat genau das zugeschlagen: Die Redaktion schrieb
„…den bewährten 4K-Prüfpfad von Franks Finanzcheck“ in den neuen Beitrag
`content/posts/2026-11-17-wertvolle-gebrauchte-moebel-finden-…`. Kein Lauf
sprang an – der Beitrag ging mit der Falschschreibung auf `main`, und der
Fehler tauchte erst auf, als ein fremder Commit (das `static/llms.txt` des
Reparatur-PRs) den Lauf zufällig auslöste. Ein Gate, das nur auf Zuruf
hinsieht, ist keine Wache.

Diese Tests halten beide Hälften fest:
  1. Der Trigger deckt die Flächen, die die Quellprüfung liest.
  2. Die Prüfung ist scharf: eine Falschschreibung im Beitrag wird gemeldet,
     die korrekte Schreibweise nicht (Gegenprobe gegen Schein-Sicherheit).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import entity_marken_gate as gate  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "entity-marken-gate.yml"

BEITRAG = """---
title: "Beitrag"
date: 2026-11-17T09:00:00Z
---

Beim Kauf nutzen wir den bewährten 4K-Prüfpfad von {marke}. So behältst du
die Kontrolle über deine Fixkosten.
"""


class TriggerTest(unittest.TestCase):
    """Die Pfadliste ist der Adressat der Wache – nicht die Deko."""

    @classmethod
    def setUpClass(cls):
        import yaml  # requirements-ci; der Lauf installiert es vorher

        # BaseLoader: `on` bleibt der Schlüssel „on“ – PyYAML liest ihn
        # sonst als boolesches True (YAML 1.1) und der Test prüfte nichts.
        cls.workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"),
                                 Loader=yaml.BaseLoader)

    def test_beide_ereignisse_ueberwachen_die_beiraege(self):
        for ereignis in ("push", "pull_request"):
            with self.subTest(ereignis=ereignis):
                pfade = self.workflow["on"][ereignis]["paths"]
                self.assertIn(
                    "content/posts/**", pfade,
                    f"`{ereignis}` muss auf content/posts/** laufen – sonst "
                    f"sieht die E6-Prüfung neue Beiträge nie")

    def test_pfadliste_deckt_die_suchraeume_der_quellpruefung(self):
        """Was `check_source` liest, muss den Lauf auslösen können."""
        quelle = (SCRIPTS / "entity_marken_gate.py").read_text(encoding="utf-8")
        self.assertIn('suchraeume = [root / "content", root / "layouts"]', quelle)
        pfade = set(self.workflow["on"]["push"]["paths"])
        for flaeche in ("content/posts/**", "layouts/_partials/footer.html",
                        "hugo.toml"):
            with self.subTest(flaeche=flaeche):
                self.assertIn(flaeche, pfade)


class SchreibweisenTest(unittest.TestCase):
    """Gegenprobe: Die Meldung darf nicht nur auf dem Papier stehen."""

    def _befunde(self, marke: str):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            gate._fixture(wurzel)
            beitrag = wurzel / "content/posts/2026-11-17-probe/index.md"
            beitrag.parent.mkdir(parents=True, exist_ok=True)
            beitrag.write_text(BEITRAG.format(marke=marke), encoding="utf-8")
            befunde = gate.Findings()
            gate.check_source(wurzel, befunde)
            return [f for f in befunde.hart
                    if f[1] == "content/posts/2026-11-17-probe/index.md"]

    def test_falschschreibung_im_beitrag_wird_gemeldet(self):
        treffer = self._befunde("Franks Finanzcheck")
        self.assertTrue(treffer, "Die Falschschreibung im Beitrag bleibt unsichtbar")
        self.assertEqual(treffer[0][0], "E6")
        self.assertIn("Falschschreibung", treffer[0][2])

    def test_korrekte_schreibweise_bleibt_still(self):
        self.assertEqual(self._befunde("FranksFinanzcheck"), [],
                         "Die Wache meldet die korrekte Marke – Fehlalarm")


if __name__ == "__main__":
    unittest.main()
