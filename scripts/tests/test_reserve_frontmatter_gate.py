#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regressionen des Reserve-Frontmatter-Gates (WF-D4E0 / #947, 30.10.2026).

Warum diese Tests existieren: Der Reserve-Lauf 40856100639 (29.10.2026) war
rot – nicht am Vorrat, sondern an EINER Zeile Content:

    content/posts/2026-10-12-dein-weg-…/index.md:5
    reserve_reaktiviert: "… Klasse „heilbar" ist heilbar, …"

Commit `3d050ea1` (#941, WF-D0C9) hat beim Neu-Tippen von Frontmatter das
deutsche Schlusszeichen durch ein ASCII-`"` ersetzt. YAML beendet den Wert
beim ersten `"`, Hugo kann die Seite nicht bauen. Der Artefakt-Wächter
erkannte den Fund (A6), konnte ihn aber nicht heilen und meldete ihn in
Parser-Sprache; im Ticket blieb „Stock shortage“ stehen.

Diese Fälle frieren den Vertrag des Gates ein:

  1. ERKENNUNG über die SSOT (`frontmatter_wache`) – keine zweite Wahrheit.
  2. BESITZ: Reserve-Eigentum wird geheilt, Live-Content NIE angefasst,
     sondern gemeldet (Engine-/Deploy-Kette besitzt ihn).
  3. BEWEIS: Artikeltext bytegleich, kein neuer Blocker, Belege vorhanden –
     sonst bleiben die Originalbytes stehen (B1–B4, fail-closed).
  4. KEIN GRÜN AUS UNWISSEN: ohne SSOT ist das Urteil ein Ausfall (Exit 2).
  5. LESEMODUS schreibt nicht (C15) und die Heilung ist idempotent.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import frontmatter_wache as fw          # noqa: E402
import reserve_frontmatter_gate as gate  # noqa: E402

SKRIPT = ROOT / "scripts" / "reserve_frontmatter_gate.py"

# Der Vorfall in Originalform (Zeile 5, deutsche Anführungszeichen).
VORFALL_FM = (
    '---\n'
    'title: "Dein Weg zu geringeren Monatskosten: Schritt für Schritt"\n'
    'description: "Geringere Monatskosten: So senkst du systematisch deine '
    'laufenden Ausgaben."\n'
    'date: 2026-10-19T01:20:46Z\n'
    'draft: true\n'
    'reserve: true\n'
    'reserve_reaktiviert: "2026-10-07 – Rückholung (#614): Befund der Klasse '
    '„heilbar" ist heilbar, Wirkungsnachweis lesbarkeit_heiler.py"\n'
    '---\n'
    '\n'
    'Der Artikeltext bleibt unangetastet.\n'
)

LIVE_FM = (
    VORFALL_FM.replace("draft: true\nreserve: true\n",
                       "draft: false\nreserve_published: 2026-10-19\n")
)

SAUBER_FM = (
    '---\n'
    'title: "Sauber"\n'
    'date: 2026-10-19T01:20:46Z\n'
    'draft: true\n'
    'reserve: true\n'
    '---\n'
    '\n'
    'Annahme: Die Anlage kostet 500 Euro.\n'
)


def _baum(faelle: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="fm-gate-test-"))
    for rel, inhalt in faelle.items():
        ziel = tmp / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
    return tmp


class WfD4e0Issue947Tests(unittest.TestCase):
    """Der Vorfall selbst: eine Zeile Frontmatter, ein toter Vorratslauf."""

    def test_vorfallzeile_ist_ein_blocker_der_ssot(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        befunde, _ = fw.pruefe_datei(
            baum / "content/posts/p/index.md", VORFALL_FM, anzeige="x")
        blocker = [b for b in befunde if b["schwere"] == fw.BLOCKER]
        self.assertTrue(blocker, "die #947-Zeile muss ein Blocker sein")
        kaputte_zeile = next(nr for nr, zeile in enumerate(
            VORFALL_FM.splitlines(), 1) if '\u201eheilbar"' in zeile)
        self.assertTrue(any(b["zeile"] == kaputte_zeile for b in blocker),
                        f"der Fund muss Zeile {kaputte_zeile} nennen "
                        f"(gemeldet: {[b['zeile'] for b in blocker]})")

    def test_gate_heilt_vorfall_im_reserve_eigentum(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        bericht = gate.pruefe(baum, fix=True)
        self.assertEqual(len(bericht["geheilt"]), 1)
        self.assertEqual(bericht["offen"], [])
        neu = (baum / "content/posts/p/index.md").read_text(encoding="utf-8")
        self.assertIn('\u201eheilbar\u201c', neu)
        # B2: der Artikeltext ist bytegleich geblieben.
        self.assertEqual(gate.koerper(neu), gate.koerper(VORFALL_FM))
        self.assertEqual(fw.pruefe_datei(baum / "content/posts/p/index.md",
                                         neu, anzeige="x")[0], [])

    def test_gate_fasst_live_content_nie_an(self):
        baum = _baum({"content/posts/l/index.md": LIVE_FM})
        vorher = (baum / "content/posts/l/index.md").read_bytes()
        bericht = gate.pruefe(baum, fix=True)
        self.assertEqual(bericht["geheilt"], [])
        self.assertEqual(len(bericht["offen"]), 2,
                         "F3 (Ursache) und F2 (Parser) müssen gemeldet werden")
        self.assertTrue(all(e["besitz"] == gate.BESITZ_FREMD
                            for e in bericht["offen"]))
        self.assertEqual((baum / "content/posts/l/index.md").read_bytes(),
                         vorher, "Live-Content darf NIE verändert werden")
        self.assertIn("Live-Bestand", gate.bericht_text(bericht))

    def test_lesemodus_schreibt_nicht_und_meldet_den_fund(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM,
                      "content/posts/gut/index.md": SAUBER_FM})
        vorher = (baum / "content/posts/p/index.md").read_bytes()
        bericht = gate.pruefe(baum)
        self.assertEqual((baum / "content/posts/p/index.md").read_bytes(),
                         vorher)
        self.assertEqual(bericht["geheilt"], [])
        self.assertEqual({e["pfad"] for e in bericht["offen"]},
                         {"content/posts/p/index.md"})
        self.assertEqual(bericht["reserve_dateien"], 1)

    def test_heilung_ist_idempotent(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        gate.pruefe(baum, fix=True)
        stand = (baum / "content/posts/p/index.md").read_bytes()
        zweiter = gate.pruefe(baum, fix=True)
        self.assertEqual((baum / "content/posts/p/index.md").read_bytes(),
                         stand)
        self.assertEqual(zweiter["geheilt"], [])
        self.assertEqual(zweiter["offen"], [])


class BeweiseDesGatesTests(unittest.TestCase):
    """B1–B4: ohne Beweis bleibt die Datei bytegenau stehen (fail-closed)."""

    def setUp(self):
        self._echt = fw.heile_datei

    def tearDown(self):
        fw.heile_datei = self._echt

    def test_b1_aenderung_ohne_beleg_wird_verworfen(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})

        def stumm(pfad, text):
            neu, _ = self._echt(pfad, text)
            return neu, []

        fw.heile_datei = stumm
        bericht = gate.pruefe(baum, fix=True)
        self.assertEqual(bericht["geheilt"], [])
        self.assertEqual(len(bericht["verworfen"]), 1)
        self.assertIn("B1", bericht["verworfen"][0]["grund"])
        self.assertEqual((baum / "content/posts/p/index.md")
                         .read_text(encoding="utf-8"), VORFALL_FM)

    def test_b2_heilung_die_prosa_aendert_wird_verworfen(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})

        def pfuscher(pfad, text):
            neu, belege = self._echt(pfad, text)
            return neu + "\nNachtrag.\n", belege

        fw.heile_datei = pfuscher
        bericht = gate.pruefe(baum, fix=True)
        self.assertEqual(bericht["geheilt"], [])
        self.assertIn("B2", bericht["verworfen"][0]["grund"])
        self.assertEqual((baum / "content/posts/p/index.md")
                         .read_text(encoding="utf-8"), VORFALL_FM)

    def test_werfender_heiler_laesst_die_datei_stehen(self):
        """Ein Ausfall des Heilers ist kein Freibrief (fail-closed)."""
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})

        def kaputt(pfad, text):
            raise RuntimeError("Heiler explodiert")

        fw.heile_datei = kaputt
        bericht = gate.pruefe(baum, fix=True)
        self.assertEqual(bericht["geheilt"], [])
        self.assertEqual(len(bericht["verworfen"]), 1)
        self.assertIn("gescheitert", bericht["verworfen"][0]["grund"])
        self.assertTrue(bericht["offen"])
        self.assertEqual((baum / "content/posts/p/index.md")
                         .read_text(encoding="utf-8"), VORFALL_FM)

    def test_b3_neuer_blocker_wird_verworfen(self):
        """Eine Heilung, die den Fund nur verschiebt, ist keine Heilung."""
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        pfad = baum / "content/posts/p/index.md"
        vorher = [b for b in fw.pruefe_datei(pfad, VORFALL_FM, anzeige="x")[0]
                  if b["schwere"] == fw.BLOCKER]
        ok, grund, nachher = gate.heilung_beweisen(
            pfad, VORFALL_FM, VORFALL_FM.replace("reserve: true",
                                                 "reserve: true\ndraft: false"),
            [{"meldung": "angeblich geheilt"}], vorher)
        self.assertFalse(ok, "eine Änderung ohne Blocker-Abbau ist kein Beweis")
        self.assertTrue(grund)

    def test_b4_ohne_blockerabbau_keine_heilung(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        pfad = baum / "content/posts/p/index.md"
        vorher = [b for b in fw.pruefe_datei(pfad, VORFALL_FM, anzeige="x")[0]
                  if b["schwere"] == fw.BLOCKER]
        ok, grund, _ = gate.heilung_beweisen(pfad, VORFALL_FM, VORFALL_FM,
                                            [{"meldung": "x"}], vorher)
        self.assertFalse(ok)
        self.assertIn("nichts zu heilen", grund)


class EineWahrheitTests(unittest.TestCase):
    """Das Gate hat keinen eigenen Parser – es folgt der SSOT."""

    def test_ohne_ssot_kein_gruenes_urteil(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        echt = gate.fw
        try:
            gate.fw = None
            bericht = gate.pruefe(baum)
        finally:
            gate.fw = echt
        self.assertEqual(bericht["klasse"], "ssot")
        self.assertIn("NICHTS geprüft", gate.bericht_text(bericht))

    def test_gate_folgt_der_ssot_bei_neuen_klassen(self):
        """Was die SSOT als Blocker führt, ist ein Blocker – auch neu Erfundenes."""
        baum = _baum({"content/posts/p/index.md": SAUBER_FM})
        echt = fw.pruefe_datei

        def streng(pfad, text, **kw):
            return [fw.Befund("F9", fw.BLOCKER, "content/posts/p/index.md",
                              2, 1, "Probe der SSOT")], True

        fw.pruefe_datei = streng
        try:
            bericht = gate.pruefe(baum)
        finally:
            fw.pruefe_datei = echt
        self.assertEqual(len(bericht["offen"]), 1)
        self.assertEqual(bericht["offen"][0]["regel"], "F9")

    def test_besitzregel_ist_die_des_staging_waechters(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM,
                      "content/posts/l/index.md": LIVE_FM})
        self.assertTrue(gate.rsg.is_reserve_owned(
            baum / "content/posts/p/index.md"))
        self.assertFalse(gate.rsg.is_reserve_owned(
            baum / "content/posts/l/index.md"))


class CliVertragTests(unittest.TestCase):
    """Die Aufrufe, die der Workflow wirklich macht."""

    def _lauf(self, *args):
        return subprocess.run([sys.executable, str(SKRIPT), *args],
                              capture_output=True, text=True, timeout=120)

    def test_selftest_und_wirkungsprobe_sind_gruen(self):
        for flagge in ("--selftest", "--wirkungsprobe"):
            with self.subTest(flagge=flagge):
                proc = self._lauf(flagge)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_check_auf_dem_echten_korpus_ist_gruen_und_schreibfrei(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                                capture_output=True, text=True).stdout
        proc = self._lauf("--root", str(ROOT))
        after = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                               capture_output=True, text=True).stdout
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(before, after, "Prüf-Aufruf hat den Korpus verändert")

    def test_fix_auf_einem_vorfallskorpus_ist_gruen(self):
        baum = _baum({"content/posts/p/index.md": VORFALL_FM})
        proc = self._lauf("--fix", "--root", str(baum))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("GEHEILT", proc.stdout)

    def test_offener_fremdbefund_ist_rot_und_nennt_den_befehl(self):
        baum = _baum({"content/posts/l/index.md": LIVE_FM})
        proc = self._lauf("--root", str(baum))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("frontmatter_wache.py --fix", proc.stdout)


if __name__ == "__main__":
    unittest.main()
