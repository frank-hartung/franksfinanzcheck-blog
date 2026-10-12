#!/usr/bin/env python3
"""Verträge für die Phrasen-Einzigartigkeit im Publish-Gate (Issue #714).

ANLASS (12.10.2026): Zwei Reserve-Artikel – „DSL-Anbieter wechseln“ und
„Handyvertrag kündigen“ – passierten um 06:02 Uhr quality_score und
publish_gate STRICT. Um 13:35 Uhr meldete das Tagesaudit
(`check_uniqueness.py`) dasselbe Paar als KRITISCH: 14 gleiche
Sieben-Wort-Phrasen aus einem geteilten § 56-TKG-Absatz, dazu einen
Titel-Zwilling („…: Kosten und Fristen richtig prüfen“ ↔ „…: Frist und
Kosten richtig prüfen“).

Das Gate war nicht zu lasch – es kannte die Messung nicht. `duplikat_guard`
(D3/D4) vergleicht ganze Absätze mit Ratio ≥ 0,85; ein Absatz, der
„DSL-Vertrag“ gegen „Handyvertrag“ tauscht und einen Satz anhängt, liegt
darunter. `quality_score` bewertet eine kritische Überlappung mit −0,01.
Bestandswache und Gate hatten zwei Wahrheiten – und die strengere kam erst
nach dem Deploy zu Wort (dieselbe Bauart wie #583 Faktenfrische und #674
Duplikate).

Diese Tests frieren ein:
  1. Das Gate liest DENSELBEN Collector wie das Tagesaudit (eine Messregel).
  2. Ein Kandidat mit geteilter Passage trägt U1 – gegen Live-Artikel und
     gegen Mit-Kandidaten (beide Seiten), nie gegen Entwürfe im Vorrat.
  3. Titel-Zwillinge (U2) treffen zwischen zwei Kandidaten nur den jüngeren.
  4. Ein roter Selbsttest ist ein Werkzeugfehler, kein Freispruch.
  5. Die Scorecard misst über denselben Adapter (RD2 deklariert, blockierend).
  6. Der konkrete Fall #714 bleibt gegen den echten Bestand sauber.
  7. Redaktionsvokabeln („richtig prüfen“) machen keine Titel-Zwillinge mehr.

Ausführung:  python3 -m unittest scripts.tests.test_publish_gate_uniqueness -v
"""
from __future__ import annotations

import inspect
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_uniqueness as cu  # noqa: E402
import publish_gate as pg  # noqa: E402

PASSAGE = (
    "Lies die Laufzeit in deinem Vertrag bevor du ein neues Angebot annimmst "
    "denn die erste feste Laufzeit darf höchstens vierundzwanzig Monate dauern "
    "und danach kannst du jederzeit mit einer Frist von einem Monat kündigen "
    "wenn der Vertrag still weiterläuft."
)
EIGEN_A = (
    "Ein Router steht selten am besten Platz; wer ihn vom Boden auf das Regal "
    "hebt, gewinnt oft mehr als ein neuer Tarif verspricht."
)
EIGEN_B = (
    "Eine offene Gerätezahlung läuft oft weiter, wenn der Mobilfunkdienst endet; "
    "wer die Raten nicht getrennt sieht, zahlt für ein Telefon in der Schublade."
)
EIGEN_C = (
    "Der Notgroschen ist kein Sparziel, sondern ein Puffer gegen den Dienstag, "
    "an dem die Waschmaschine stirbt. Drei Nettogehälter sind eine Faustregel."
)


class _KorpusMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.posts = Path(self.tmp.name) / "content" / "posts"
        self.original_posts_dir = pg.POSTS_DIR
        pg.POSTS_DIR = str(self.posts)

    def tearDown(self):
        pg.POSTS_DIR = self.original_posts_dir
        self.tmp.cleanup()

    def write_post(self, slug: str, title: str, body: str, *, draft: bool = False,
                   date: str = "2026-10-07T08:00:00Z") -> None:
        path = self.posts / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\ntitle: \"{title}\"\ndate: {date}\ndraft: "
            f"{'true' if draft else 'false'}\n---\n\n{body}\n",
            encoding="utf-8",
        )


class CollectorTests(_KorpusMixin, unittest.TestCase):
    """Der Gate-Adapter misst wie das Tagesaudit – nicht strenger, nicht milder."""

    def test_geteilte_passage_gegen_live_artikel_ist_u1(self):
        self.write_post("2026-10-07-dsl", "DSL-Anbieter wechseln: was es kostet",
                        PASSAGE + "\n\n" + EIGEN_A)
        kandidat = "2026-10-12-handy"
        self.write_post(kandidat, "Handyvertrag kündigen: Enddatum sichern",
                        PASSAGE + "\n\n" + EIGEN_B, date="2026-10-12T06:02:00Z")

        failures, tool_error = pg.uniqueness_failures([kandidat])

        self.assertIsNone(tool_error)
        self.assertIn(kandidat, failures)
        self.assertTrue(any(d.startswith("U1-PHRASEN") and "2026-10-07-dsl" in d
                            for d in failures[kandidat]), failures)
        self.assertNotIn("2026-10-07-dsl", failures,
                         "Der Live-Artikel ist Zeuge, nicht Kandidat")

    def test_mit_kandidaten_tragen_beide_den_befund(self):
        a, b = "2026-10-12-dsl", "2026-10-12-handy"
        self.write_post(a, "DSL-Anbieter wechseln: was es kostet", PASSAGE + "\n\n" + EIGEN_A)
        self.write_post(b, "Handyvertrag kündigen: Enddatum sichern", PASSAGE + "\n\n" + EIGEN_B)

        failures, tool_error = pg.uniqueness_failures([a, b])

        self.assertIsNone(tool_error)
        for slug in (a, b):
            self.assertTrue(any(d.startswith("U1-PHRASEN") for d in failures.get(slug, [])),
                            f"{slug} ohne U1: {failures}")

    def test_entwuerfe_im_vorrat_sind_keine_gegenseite(self):
        self.write_post("2026-09-01-entwurf", "Alter Entwurf", PASSAGE, draft=True)
        kandidat = "2026-10-12-handy"
        self.write_post(kandidat, "Handyvertrag kündigen: Enddatum sichern",
                        PASSAGE + "\n\n" + EIGEN_B)

        failures, tool_error = pg.uniqueness_failures([kandidat])

        self.assertIsNone(tool_error)
        self.assertEqual({}, failures,
                         "Ein Entwurf kann nichts kannibalisieren – sonst blockiert "
                         "die Reserve sich selbst")

    def test_eigenstaendiger_kandidat_bleibt_sauber(self):
        self.write_post("2026-10-07-dsl", "DSL-Anbieter wechseln: was es kostet",
                        PASSAGE + "\n\n" + EIGEN_A)
        kandidat = "2026-10-12-notgroschen"
        self.write_post(kandidat, "Notgroschen: wie viel Puffer reicht", EIGEN_C)

        failures, tool_error = pg.uniqueness_failures([kandidat])

        self.assertIsNone(tool_error)
        self.assertEqual({}, failures)

    def test_titel_zwilling_trifft_nur_den_juengeren_kandidaten(self):
        alt = "2026-10-12-notgroschen"
        jung = "2026-10-12-notgroschen-aufbauen"
        self.write_post(alt, "Notgroschen: wie viel Puffer reicht", EIGEN_C,
                        date="2026-10-12T08:00:00Z")
        self.write_post(jung, "Notgroschen aufbauen: wie viel reicht", EIGEN_A,
                        date="2026-10-12T10:00:00Z")

        failures, tool_error = pg.uniqueness_failures([alt, jung])

        self.assertIsNone(tool_error)
        self.assertNotIn(alt, failures, "der ältere Zwilling ist kanonisch")
        self.assertTrue(any(d.startswith("U2-ZWILLING") for d in failures.get(jung, [])),
                        failures)

    def test_titel_zwilling_gegen_live_artikel_blockiert_den_kandidaten(self):
        self.write_post("2026-10-12-notgroschen", "Notgroschen: wie viel Puffer reicht",
                        EIGEN_C)
        kandidat = "2026-10-12-notgroschen-aufbauen"
        self.write_post(kandidat, "Notgroschen aufbauen: wie viel reicht", EIGEN_A,
                        date="2026-10-12T10:00:00Z")

        failures, _ = pg.uniqueness_failures([kandidat])

        self.assertTrue(any(d.startswith("U2-ZWILLING") for d in failures.get(kandidat, [])))

    def test_leere_kandidatenliste_misst_nichts(self):
        self.assertEqual(({}, None), pg.uniqueness_failures([]))


class FailClosedTests(_KorpusMixin, unittest.TestCase):
    """Eine Messung, die sich nicht selbst beweist, ist kein Freispruch."""

    def test_roter_selbsttest_ist_werkzeugfehler(self):
        kandidat = "2026-10-12-handy"
        self.write_post(kandidat, "Handyvertrag kündigen", EIGEN_B)
        original = cu.run_selftest
        cu.run_selftest = lambda: ["  Fall 1: erwartet „True“, bekam „False“"]
        try:
            failures, tool_error = pg.uniqueness_failures([kandidat])
        finally:
            cu.run_selftest = original
        self.assertEqual({}, failures)
        self.assertIsNotNone(tool_error)
        self.assertIn("Selbsttest", tool_error)

    def test_gate_stoppt_bei_werkzeugfehler_statt_zu_verwerfen(self):
        quelle = inspect.getsource(pg.main)
        self.assertIn("uniqueness_failures(candidates)", quelle)
        self.assertIn("if uniq_tool_error:", quelle)
        stopp = quelle.index("if uniq_tool_error:")
        self.assertIn("return 1", quelle[stopp:stopp + 900],
                      "Werkzeugfehler muss das Gate fail-closed stoppen")
        self.assertIn("Einzigartigkeits-Gate U1–U2 nicht bestanden", quelle)

    def test_kein_heiler_sondern_begruendete_ausnahme(self):
        """C29-Deckung: Die Regel ist bewusst Menschensache – dokumentiert."""
        import reserve_healer_coverage as rhc
        self.assertIn("uniqueness_failures", rhc.AUSNAHMEN)
        self.assertNotIn("uniqueness_failures", rhc.REGEL_HEILER)
        self.assertIn("#714", rhc.AUSNAHMEN["uniqueness_failures"])


class ScorecardVertragTests(unittest.TestCase):
    """RD2 ist Teil der Produktionswahrheit – über denselben Adapter."""

    def test_scorecard_misst_ueber_den_gate_adapter(self):
        import release_scorecard as rs
        quelle = inspect.getsource(rs.sammle)
        self.assertIn("publish_gate.uniqueness_failures", quelle)
        self.assertNotIn('_importiere_gate_module("check_uniqueness")', quelle)
        self.assertEqual(rs.PUBLISH_GATE_HART_FAMILIEN.get("RD2-einzigartigkeit"),
                         "check_uniqueness.py")

    def test_rd2_in_der_ssot_deklariert_und_blockierend(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML fehlt")
        import release_scorecard as rs
        register = rs.check_register(rs.ssot_laden())
        check = register.get("RD2-einzigartigkeit")
        self.assertIsNotNone(check, "RD2-einzigartigkeit fehlt in data/release_scorecard.yaml")
        self.assertEqual(check["wirkung"], "blockiert")
        self.assertEqual(check["dimension"], "redundanz")
        self.assertIn("publish_gate.uniqueness_failures", check["quelle"])


class Fall714Tests(unittest.TestCase):
    """Die konkrete Reparatur bleibt vor einem Rückfall geschützt."""

    DSL = "2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet"
    HANDY = "2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung"

    def test_paar_ist_gegen_den_echten_bestand_eigenstaendig(self):
        if not (ROOT / "content" / "posts" / self.DSL / "index.md").exists():
            self.skipTest("Artikel nicht im Bestand")
        failures, tool_error = pg.uniqueness_failures([self.DSL, self.HANDY])
        self.assertIsNone(tool_error)
        self.assertEqual({}, failures, failures)

    def test_schablonen_titel_sind_keine_zwillinge(self):
        self.assertFalse(cu.same_day_twin(
            "DSL-Anbieter wechseln: Kosten und Fristen richtig prüfen",
            "Handyvertrag kündigen: Frist und Kosten richtig prüfen"))

    def test_themen_zwilling_bleibt_trotz_schablone_erkannt(self):
        self.assertTrue(cu.same_day_twin(
            "Stromfresser im Haushalt richtig prüfen",
            "Stromfresser finden: So prüfst du deinen Haushalt"))
        # Der historische Gas-Fall vom 11.08.2026 bleibt der Maßstab.
        self.assertTrue(cu.same_day_twin(
            "Gaspreisgarantie: So sicherst du dich gegen Preissprünge ab",
            "Preisgarantie Gas: So schützt du dich vor Preiserhöhungen"))

    def test_keyword_dichte_saetze_sind_aus_dem_handy_artikel_verschwunden(self):
        pfad = ROOT / "content" / "posts" / self.HANDY / "index.md"
        if not pfad.exists():
            self.skipTest("Artikel nicht im Bestand")
        text = pfad.read_text(encoding="utf-8")
        self.assertNotIn("Darum geht es hier konkret:", text)
        self.assertNotIn("Genau das ist der Hebel:", text)


if __name__ == "__main__":
    unittest.main()
