"""Vertragstests für den saisonalen SEO/GEO-Hero-Refresh.

Die Tests sind absichtlich offline: Agent Reach und Claude werden im Workflow
integriert, die gefährlichen Entscheidungen (Saisonfenster, Kandidatenvertrag,
YAML-Update) müssen aber auch ohne Netz beweisbar bleiben.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import saisonaler_hero_refresh as hero  # noqa: E402


HERBST = {
    "id": "herbst",
    "name": "Herbst",
    "ab": "09-01",
    "bis": "11-30",
    "hero_title": "Herbst-Check: Bei Strom, Gas & Versicherung Geld sparen",
    "hero_lead": "FranksFinanzcheck hilft dir im Herbst, Strom, Gas, Internet und Versicherungen strukturiert zu vergleichen – unabhängig, verständlich und ohne Verkaufsdruck. Du prüfst zuerst die teuerste Rechnung, erkennst relevante Tarifangaben und findest den passenden nächsten Schritt.",
}


class Saisonlogik(unittest.TestCase):
    def test_herbst_grenzen_sind_inklusive(self):
        self.assertEqual(hero.season_for(dt.date(2026, 9, 1), [HERBST])["id"], "herbst")
        self.assertEqual(hero.season_for(dt.date(2026, 11, 30), [HERBST])["id"], "herbst")
        self.assertIsNone(hero.season_for(dt.date(2026, 8, 31), [HERBST]))

    def test_jahreswechsel_funktioniert(self):
        winter = dict(HERBST, id="winter", name="Winter", ab="12-01", bis="02-29")
        self.assertEqual(hero.season_for(dt.date(2026, 12, 1), [winter])["id"], "winter")
        self.assertEqual(hero.season_for(dt.date(2027, 2, 28), [winter])["id"], "winter")


class GeoVertrag(unittest.TestCase):
    def test_kuratierte_basis_besteht(self):
        self.assertEqual(hero.validate_candidate(HERBST["hero_title"], HERBST["hero_lead"], HERBST, []), [])

    def test_zahlen_und_formelle_ansprache_werden_verworfen(self):
        candidate = HERBST["hero_lead"].replace("Herbst", "Herbst 2026").replace("dir", "Ihnen")
        findings = hero.validate_candidate(HERBST["hero_title"], candidate, HERBST, [])
        self.assertTrue(any("Zahl" in finding for finding in findings))
        self.assertTrue(any("Sie-Anrede" in finding for finding in findings))

    def test_entity_und_kategorien_sind_pflicht(self):
        candidate = HERBST["hero_lead"].replace("FranksFinanzcheck", "Dieser Ratgeber")
        findings = hero.validate_candidate(HERBST["hero_title"], candidate, HERBST, [])
        self.assertTrue(any("Entity" in finding for finding in findings))

    def test_format_parser_akzeptiert_nur_beide_felder(self):
        raw = f"TITLE: {HERBST['hero_title']}\nLEAD: {HERBST['hero_lead']}"
        self.assertEqual(hero.parse_answer(raw), (HERBST["hero_title"], HERBST["hero_lead"]))
        self.assertIsNone(hero.parse_answer("TITLE: nur ein Feld"))


class Faelligkeit(unittest.TestCase):
    """Der Grundcode trennt redaktionelle Änderung von abgelaufener Rotation.

    Genau diese Vermischung war die Ursache von Issue #514: Ein redaktionell
    geänderter Hero galt dauerhaft als „fällig", also lief täglich ein
    Claude-Zwangsversuch – und jeder Ausfall erzeugte einen roten Lauf.
    """

    JETZT = dt.datetime(2026, 10, 2, 6, 0, tzinfo=dt.timezone.utc)

    def _state(self, updated: str, fingerprint: str) -> dict:
        return {"version": 1, "saisons": {"herbst": {"updated": updated, "fingerprint": fingerprint}}}

    def test_frischer_nachweis_ist_nicht_faellig(self):
        state = self._state("2026-09-30T06:00:00Z", hero.fingerprint(HERBST))
        status = hero.due_state(HERBST, state, False, self.JETZT)
        self.assertFalse(status["due"])
        self.assertEqual(status["code"], "aktuell")

    def test_redaktionelle_aenderung_bekommt_eigenen_code(self):
        state = self._state("2026-09-30T06:00:00Z", "fremder-fingerprint")
        self.assertEqual(hero.due_state(HERBST, state, False, self.JETZT)["code"], "redaktion")

    def test_abgelaufene_rotation_bleibt_rotation(self):
        state = self._state("2026-08-01T06:00:00Z", hero.fingerprint(HERBST))
        status = hero.due_state(HERBST, state, False, self.JETZT)
        self.assertEqual(status["code"], "rotation")
        self.assertGreaterEqual(status["age_days"], hero.MAX_AGE_DAYS)

    def test_ohne_nachweis_ist_die_saison_neu(self):
        self.assertEqual(hero.due_state(HERBST, {}, False, self.JETZT)["code"], "neu")
        self.assertEqual(
            hero.due_state(HERBST, {"saisons": {"herbst": {"updated": "x"}}}, False, self.JETZT)["code"],
            "neu")

    def test_force_sticht_alles(self):
        state = self._state("2026-10-01T06:00:00Z", hero.fingerprint(HERBST))
        self.assertEqual(hero.due_state(HERBST, state, True, self.JETZT)["code"], "force")

    def test_kompatible_kurzfassung_bleibt_erhalten(self):
        state = self._state("2026-09-30T06:00:00Z", hero.fingerprint(HERBST))
        self.assertEqual(hero.is_due(HERBST, state, False, self.JETZT), (False, "aktuell"))


class Eskalation(unittest.TestCase):
    """Gelb statt rot, solange die ausgelieferte Basis geprüft und frisch ist."""

    def test_einzelner_ausfall_bei_gesunder_basis_ist_gelb(self):
        hart, _ = hero.escalate("rotation", hero.MAX_AGE_DAYS + 1, 1, True)
        self.assertFalse(hart)

    def test_serie_eskaliert(self):
        hart, grund = hero.escalate("rotation", hero.MAX_AGE_DAYS + 1, hero.FAILURE_STREAK_LIMIT, True)
        self.assertTrue(hart)
        self.assertIn("Folge", grund)

    def test_ueberalterung_eskaliert(self):
        hart, grund = hero.escalate("rotation", hero.HARD_STALE_DAYS, 1, True)
        self.assertTrue(hart)
        self.assertIn("alt", grund)

    def test_defekte_basis_eskaliert_sofort(self):
        hart, _ = hero.escalate("redaktion", 1, 0, False)
        self.assertTrue(hart)


class Anbieterkette(unittest.TestCase):
    """Transportweg ist der gemeinsame LLM-Zugang – nicht die tote Puter-Brücke."""

    SCHLUESSEL = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY")

    def _ohne_schluessel(self):
        gesichert = {k: os.environ.pop(k) for k in self.SCHLUESSEL if k in os.environ}
        self.addCleanup(os.environ.update, gesichert)

    def test_ohne_schluessel_wird_nichts_erfunden_und_nichts_geworfen(self):
        self._ohne_schluessel()
        hero.LAST_BRIDGE_ERROR.clear()
        antwort, provider, modell = hero.call_model("system", "user")
        self.assertIsNone(antwort)
        self.assertEqual((provider, modell), ("", ""))
        self.assertIn("Schlüssel", hero.LAST_BRIDGE_ERROR[-1])

    def test_reihenfolge_ist_dokumentiert_und_vollstaendig(self):
        self.assertEqual(hero.PROVIDER_ORDER, ("claude", "openai", "groq", "gemini"))

    def test_kettennachweis_meldet_fehlende_anbieter(self):
        self._ohne_schluessel()
        chain = hero.chain_status(dt.date(2026, 10, 2))
        self.assertFalse(chain["anbieter_vorhanden"])
        self.assertEqual(chain["anbieter"], [])
        self.assertTrue(chain["llm_client"], "scripts/llm_client.py muss importierbar sein")


class Wiederholung(unittest.TestCase):
    """Ein Formatfehler darf den Lauf nicht mehr sofort rot machen."""

    def setUp(self):
        self._original = hero.call_model
        self.addCleanup(setattr, hero, "call_model", self._original)

    def test_zweiter_versuch_mit_korrekturauflage_gewinnt(self):
        antworten = ["unbrauchbar", f"TITLE: {HERBST['hero_title']}\nLEAD: {HERBST['hero_lead']}"]
        gesehen = []

        def fake(system, user):
            gesehen.append(user)
            return antworten.pop(0), "groq", "openai/gpt-oss-120b"

        hero.call_model = fake
        parsed, protokoll, quelle = hero.polish_candidate(
            HERBST, [], [], attempts=3, sleep=lambda _s: None)
        self.assertEqual(parsed, (HERBST["hero_title"], HERBST["hero_lead"]))
        self.assertEqual(len(protokoll), 2)
        self.assertIn("KORREKTURAUFLAGE", gesehen[1])
        self.assertEqual(quelle, "groq:openai/gpt-oss-120b")

    def test_dauerhafter_ausfall_liefert_protokoll_statt_absturz(self):
        hero.call_model = lambda system, user: (None, "", "")
        parsed, protokoll, _quelle = hero.polish_candidate(
            HERBST, [], [], attempts=2, sleep=lambda _s: None)
        self.assertIsNone(parsed)
        self.assertEqual(len(protokoll), 2)

    def test_faktenverstoss_wird_nicht_durchgewunken(self):
        schlecht = HERBST["hero_lead"].replace("Herbst", "Herbst 2026")
        hero.call_model = lambda system, user: (
            f"TITLE: {HERBST['hero_title']}\nLEAD: {schlecht}", "gemini", "gemini-2.0-flash")
        parsed, protokoll, _quelle = hero.polish_candidate(
            HERBST, [], [], attempts=2, sleep=lambda _s: None)
        self.assertIsNone(parsed)
        self.assertTrue(all("verworfen" in eintrag for eintrag in protokoll))


class Ausfallzaehler(unittest.TestCase):
    """Die Serie muss persistent sein – sonst eskaliert nie etwas."""

    def test_zaehler_steigt_und_wird_zurueckgesetzt(self):
        original = hero.STATE
        with tempfile.TemporaryDirectory() as tmp:
            hero.STATE = Path(tmp) / "state.json"
            try:
                state = {"version": 1, "saisons": {}}
                self.assertEqual(hero.note_failure(HERBST, state, "test", "x"), 1)
                self.assertEqual(hero.note_failure(HERBST, state, "test", "x"), 2)
                self.assertEqual(hero.failure_streak(HERBST, state), 2)
                hero.clear_failure(HERBST, state)
                self.assertEqual(hero.failure_streak(HERBST, state), 0)
            finally:
                hero.STATE = original


class SicheresSchreiben(unittest.TestCase):
    def test_rewrite_beruehrt_nur_den_angegebenen_saisonblock(self):
        original_path = hero.SAISONS
        source = """saisons:
  - id: herbst
    hero_title: \"alt herbst\"
    hero_lead: \"alt lead herbst\"
  - id: winter
    hero_title: \"alt winter\"
    hero_lead: \"alt lead winter\"
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "saisons.yaml"
            target.write_text(source, encoding="utf-8")
            hero.SAISONS = target
            try:
                hero.rewrite_fields("herbst", "neu herbst", "neu lead herbst")
            finally:
                hero.SAISONS = original_path
            result = target.read_text(encoding="utf-8")
        self.assertIn('hero_title: "neu herbst"', result)
        self.assertIn('hero_lead: "neu lead herbst"', result)
        self.assertIn('hero_title: "alt winter"', result)
        self.assertIn('hero_lead: "alt lead winter"', result)


if __name__ == "__main__":
    unittest.main()
