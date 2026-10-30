#!/usr/bin/env python3
"""Messfrische & Protokoll-Wahrheit der Governance-Kette (Befund #888, 30.10.2026).

Hintergrund – zwei Fehler derselben Klasse, beide unsichtbar:

1. `.casing_report.json` wurde NUR von `casing_guard.py --json` geschrieben,
   und diesen Schalter rief kein Workflow auf. Das Cockpit zeigte deshalb am
   30.10.2026 eine 32 Tage alte Messung als aktuellen Befund (Gelb) – für
   einen Zustand, den der frische Lauf längst nicht mehr hatte. Ein Messwert
   ohne Frische-Urteil ist keine Steuerung, sondern eine Behauptung.

2. `spam_guard.fix_blog()` schrieb bei JEDEM Lauf ein „blog-fix“-Audit, auch
   wenn es nichts tat (Warn-Befund, Artikel schon Entwurf). Für einen einzigen
   Artikel entstanden so fünf Einträge am Tag; `data/spam_history.jsonl` hatte
   25.713 Zeilen und war als Beweismittel wertlos.

Die Tests frieren die Regeln ein, nicht die Zahlen:

  * Zustandsbericht: jeder Voll-Lauf schreibt, `--new-only`/`--dry-run` nicht.
  * Cockpit: veraltete Messung = Datenlücke (⚪), nie Befund (🟡/🔴);
    die Wert-Spalte nennt das Alter statt einer historischen Fundzahl.
  * Score: Blindflug kostet Punkte – „nie mehr messen“ darf kein Freifahrtschein
    für eine grüne Zahl sein.
  * Protokoll: nur echte Handlungen werden auditiert.

Lauf: python3 -m unittest scripts.tests.test_governance_messfrische
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import casing_guard as cg  # noqa: E402
import editorial_scorecard as es  # noqa: E402
import spam_guard as sg  # noqa: E402


class ZustandsberichtTests(unittest.TestCase):
    """Wer misst, schreibt den Zustand mit – sonst altert das Cockpit."""

    def test_vollauf_schreibt_zustand(self):
        self.assertTrue(cg.schreibe_zustand(json_flag=False, dry_run=False,
                                            new_only=False))

    def test_new_only_schreibt_keinen_zustand(self):
        # Winz-Nenner („heute geändert“) wäre eine Schein-Deliktquote.
        self.assertFalse(cg.schreibe_zustand(json_flag=False, dry_run=False,
                                             new_only=True))

    def test_dry_run_schreibt_nie(self):
        self.assertFalse(cg.schreibe_zustand(json_flag=False, dry_run=True,
                                             new_only=False))

    def test_ausdrueckliches_json_schreibt_auch_im_new_only(self):
        self.assertTrue(cg.schreibe_zustand(json_flag=True, dry_run=False,
                                            new_only=True))

    def test_write_state_liefert_vollstaendigen_snapshot(self):
        rows = [{"pfad": "content/posts/x/index.md",
                 "funde": [{"regel": "C1"}],
                 "erkannte_befunde": 1, "woerter": 500}]
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / ".casing_report.json"
            with mock.patch.object(cg, "JSON_OUT", ziel):
                cg.write_state(rows, [], scanned_files=111,
                               scanned_words=202920, total=1,
                               mode="fix · Bestand")
            daten = json.loads(ziel.read_text(encoding="utf-8"))
        for feld in ("stand", "modus", "gepruefte_dateien", "woerter",
                     "befunde", "hart", "gefixt", "geparkt", "dateien_liste"):
            self.assertIn(feld, daten)
        self.assertEqual(daten["gepruefte_dateien"], 111)
        self.assertEqual(daten["woerter"], 202920)
        self.assertEqual(daten["befunde"], 1)
        # C1 ist eine harte Regel, C2 nicht – der Zustand zählt wie der Report.
        self.assertEqual(daten["hart"], 1)
        self.assertEqual(daten["dateien_liste"][0]["pfad"],
                         "content/posts/x/index.md")
        # Der Zeitstempel ist der Frische-Beweis: ISO-8601 in UTC, sekundengenau.
        self.assertRegex(daten["stand"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class CockpitFrischeTests(unittest.TestCase):
    """Veraltet ist eine Datenlücke – keine Warnung und keine Entwarnung."""

    def test_veraltete_messung_ist_weiss(self):
        self.assertEqual(es._casing_lamp({"casing": 1, "casing_alter": 32,
                                          "casing_veraltet": True}), "⚪")

    def test_veraltet_schlaegt_befund(self):
        # Ein alter roter Befund darf das Cockpit nicht dauerhaft rot färben.
        self.assertEqual(es._casing_lamp({"casing": 9, "casing_alter": 99,
                                          "casing_veraltet": True}), "⚪")

    def test_frische_null_ist_gruen(self):
        self.assertEqual(es._casing_lamp({"casing": 0, "casing_alter": 0,
                                          "casing_veraltet": False}), "🟢")

    def test_frische_befunde_sind_gelb(self):
        self.assertEqual(es._casing_lamp({"casing": 2, "casing_alter": 1,
                                          "casing_veraltet": False}), "🟡")

    def test_ohne_bericht_weiss(self):
        self.assertEqual(es._casing_lamp({"casing": None}), "⚪")

    def test_wertspalte_nennt_alter_statt_historischer_zahl(self):
        text = es._casing_display({"casing": 1, "casing_alter": 32,
                                   "casing_veraltet": True})
        self.assertIn("32 Tage alt", text)
        self.assertNotIn("1 ", text)

    def test_wertspalte_zeigt_frische_zahl_mit_bezugsgroesse(self):
        text = es._casing_display({"casing": 0, "casing_alter": 0,
                                   "casing_veraltet": False,
                                   "casing_dichte": 0.0,
                                   "casing_woerter": 202920})
        self.assertIn("202.920", text)

    def test_datalage_urteilt_veraltet(self):
        text = es._casing_datalage({"casing": 1, "casing_alter": 32,
                                    "casing_veraltet": True})
        self.assertIn("historisch", text)

    def test_score_straft_blindflug(self):
        basis = {"live": 72, "decay_count": 0, "cwv_state": "OK",
                 "cwv_verdict": "GREEN", "readability": 66.0, "lektor": 0,
                 "zugangsalter_rot": 0, "zugangsalter_gelb": 0,
                 "total_clicks": 0, "click_articles": 0}
        frisch = dict(basis, casing_veraltet=False)
        veraltet = dict(basis, casing_veraltet=True)
        self.assertEqual(es._score(frisch), 100)
        self.assertEqual(es._score(frisch) - es._score(veraltet), 3)


class ProtokollWahrheitTests(unittest.TestCase):
    """Das Audit-Log beweist Handlungen – nicht das Dasein der Wache."""

    def _post(self, tmp, draft_false=False):
        p = Path(tmp) / "index.md"
        p.write_text("---\ndraft: false\n---\n\nText.\n" if draft_false
                     else "---\ndraft: true\n---\n\nText.\n", encoding="utf-8")
        return {"slug": "demo", "path": str(p),
                "content": p.read_text(encoding="utf-8")}

    def test_warn_befund_ohne_handlung_wird_nicht_auditiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            post = self._post(tmp)
            with mock.patch.object(sg, "audit") as audit:
                healed = sg.fix_blog({"demo": (post, [("B5", "warn", "39 %")])})
        audit.assert_not_called()
        self.assertEqual(healed, [])

    def test_demotion_wird_auditiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            post = self._post(tmp, draft_false=True)
            with mock.patch.object(sg, "audit") as audit:
                sg.fix_blog({"demo": (post, [("B5", "hard", "30 %")])})
            self.assertIn("draft: true", Path(post["path"]).read_text(encoding="utf-8"))
        self.assertEqual(audit.call_count, 1)

    def test_schon_entwurf_erzeugt_kein_zweites_audit(self):
        # Genau der Dauerläufer aus #888: Warn-Befund, Artikel ist Entwurf,
        # fünf Läufe am Tag – früher fünf Protokollzeilen ohne Inhalt.
        with tempfile.TemporaryDirectory() as tmp:
            post = self._post(tmp)
            with mock.patch.object(sg, "audit") as audit:
                sg.fix_blog({"demo": (post, [("B5", "hard", "30 %")])})
        audit.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
