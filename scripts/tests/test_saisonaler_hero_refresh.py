"""Vertragstests für den saisonalen SEO/GEO-Hero-Refresh.

Die Tests sind absichtlich offline: Agent Reach und der Gratis-LLM-Transport
werden im Workflow integriert; Saisonfenster, Kandidatenvertrag, Rotation und
transaktionale Dateiänderungen müssen auch ohne Netz beweisbar bleiben.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

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

    def test_mehrzeiliger_lead_wird_zusammengezogen(self):
        """Issue #891: Ein umbrochener Lead galt als „Lead-Länge 6"."""
        lead = HERBST["hero_lead"]
        umbrochen = lead.replace(" – ", "\n– ").replace(". Du ", ".\nDu ")
        raw = f"TITLE: {HERBST['hero_title']}\nLEAD: {umbrochen}"
        geparst = hero.parse_answer(raw)
        self.assertEqual(geparst, (HERBST["hero_title"], lead))
        self.assertEqual(hero.validate_candidate(*geparst, HERBST, []), [])

    def test_markdown_und_aufzaehlungszeichen_werden_entfernt(self):
        raw = (f"- **TITLE:** {HERBST['hero_title']}\n"
               f"- **LEAD:** {HERBST['hero_lead']}")
        self.assertEqual(hero.parse_answer(raw), (HERBST["hero_title"], HERBST["hero_lead"]))

    def test_leere_oder_fehlende_felder_bleiben_ungueltig(self):
        self.assertIsNone(hero.parse_answer("TITLE: nur ein Feld"))
        self.assertIsNone(hero.parse_answer("LEAD: FranksFinanzcheck ohne Titel"))
        self.assertIsNone(hero.parse_answer(f"TITLE: {HERBST['hero_title']}\nLEAD:   "))
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

    SCHLUESSEL = ("GROQ_API_KEY", "GEMINI_API_KEY", "NVIDIA_API_KEY",
                  "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")

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
        """Seit 03.10.2026: ausschließlich kostenlose Hoster.

        Die alte Reihenfolge begann mit zwei kostenpflichtigen
        Anbietern. Das war harmlos, solange kein Schlüssel gesetzt war –
        und genau deshalb gefährlich: Ein versehentlich hinterlegter
        Paid-Schlüssel hätte den nächtlichen Hero-Lauf still
        kostenpflichtig gemacht. Beide sind jetzt entfernt.
        """
        self.assertEqual(hero.PROVIDER_ORDER,
                         ("groq", "nvidia", "cloudflare", "gemini"))

    def test_kein_kostenpflichtiger_anbieter_in_der_reihenfolge(self):
        import llm_client
        for p in hero.PROVIDER_ORDER:
            self.assertEqual(llm_client.KOSTENKLASSE[p], "gratis")

    def test_drei_unabhaengige_gratis_hoster_in_der_kette(self):
        import llm_client
        bahn = [p for p in hero.PROVIDER_ORDER if p in llm_client.OPENAI_BAHN]
        self.assertEqual(len(bahn), 3,
                         "Ein leeres Tageskontingent darf den Hero-Lauf nicht "
                         "anhalten (Lehre aus Issue #514).")

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
        anbieter = mock.patch.object(hero, "verfuegbare_anbieter", return_value=["groq"])
        anbieter.start()
        self.addCleanup(anbieter.stop)
        backoff = mock.patch.object(hero, "POLISH_BACKOFF_SECONDS", (0, 0, 0))
        backoff.start()
        self.addCleanup(backoff.stop)

    def test_zweiter_versuch_mit_korrekturauflage_gewinnt(self):
        antworten = ["unbrauchbar", gute_antwort()]
        gesehen = []

        def fake(system, user, provider=None):
            gesehen.append(user)
            return antworten.pop(0), "groq", "openai/gpt-oss-120b"

        hero.call_model = fake
        parsed, protokoll, quelle = hero.polish_candidate(
            HERBST, [], [], attempts=3, sleep=lambda _s: None)
        self.assertEqual(parsed, (NEUER_TITEL, NEUER_LEAD))
        self.assertEqual(len(protokoll), 2)
        self.assertIn("KORREKTURAUFLAGE", gesehen[1])
        self.assertEqual(quelle, "groq:openai/gpt-oss-120b")

    def test_dauerhafter_ausfall_liefert_protokoll_statt_absturz(self):
        hero.call_model = lambda system, user, provider=None: (None, "", "")
        parsed, protokoll, _quelle = hero.polish_candidate(
            HERBST, [], [], attempts=2, sleep=lambda _s: None)
        self.assertIsNone(parsed)
        self.assertEqual(len(protokoll), 2)

    def test_faktenverstoss_wird_nicht_durchgewunken(self):
        schlecht = HERBST["hero_lead"].replace("Herbst", "Herbst 2026")
        hero.call_model = lambda system, user, provider=None: (
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
                saved = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
                self.assertNotIn("fehler_serie", saved)
                self.assertNotIn("letzter_fehler", saved)
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


NEUER_TITEL = "Herbst-Check: Strom, Gas und Konto gezielt vergleichen"
NEUER_LEAD = (
    "FranksFinanzcheck hilft dir im Herbst, Strom, Gas, Internet, Konto und "
    "Versicherungen systematisch zu vergleichen. Du sammelst zuerst deine "
    "aktuellen Verträge und ordnest die laufenden Kosten, bevor du Tarifdetails "
    "und Wechselmöglichkeiten prüfst – unabhängig, verständlich und ohne Verkaufsdruck."
)


def gute_antwort():
    return json.dumps({"title": NEUER_TITEL, "lead": NEUER_LEAD}, ensure_ascii=False)


class Antwortformat(unittest.TestCase):
    def test_vollstaendiges_json_und_code_fence(self):
        for raw in (gute_antwort(), f"```json\n{gute_antwort()}\n```"):
            with self.subTest(raw=raw[:12]):
                self.assertEqual(hero.parse_answer(raw), (NEUER_TITEL, NEUER_LEAD))
                self.assertEqual(hero.validate_candidate(*hero.parse_answer(raw), HERBST, []), [])

    def test_unvollstaendige_oder_mehrdeutige_antworten_scheitern(self):
        marker = f"TITLE: {NEUER_TITEL}\nLEAD: {NEUER_LEAD}"
        bad = [
            gute_antwort()[:-1],
            '{"title":"x","title":"y","lead":"z"}',
            '{"title":"x","TITLE":"y","lead":"z"}',
            json.dumps({"title": NEUER_TITEL, "lead": NEUER_LEAD, "reason": "extra"}),
            json.dumps({"title": NEUER_TITEL, "lead": [NEUER_LEAD]}),
            json.dumps({"title": NEUER_TITEL, "lead": NEUER_LEAD + "\n\nZweiter Absatz."}),
            "Hier ist der Text:\n" + marker,
            marker + "\n\nHinweis: Bitte prüfen.",
            marker + "\nHinweis: Bitte prüfen.",
            marker + "\nLEAD: andere Variante",
            marker + "\nTITLE: weitere Variante",
            f"```json\n{gute_antwort()}\n```\nWeitere Hinweise.",
            "LEAD: zuerst\nTITLE: danach",
        ]
        for raw in bad:
            with self.subTest(raw=raw[:90]):
                self.assertIsNone(hero.parse_answer(raw))

    def test_inhalt_wird_nicht_durch_markdown_bereinigung_veraendert(self):
        raw = json.dumps({"title": NEUER_TITEL, "lead": NEUER_LEAD + " **Extra**"})
        parsed = hero.parse_answer(raw)
        self.assertIn("**Extra**", parsed[1])
        self.assertTrue(any("Markup" in e for e in hero.validate_candidate(*parsed, HERBST, [])))

    def test_abgeschnittener_lead_ohne_satzende_ist_unzulaessig(self):
        findings = hero.validate_candidate(NEUER_TITEL, NEUER_LEAD[:-1], HERBST, [])
        self.assertTrue(any("vollständigen Satz" in e for e in findings))

    def test_lead_muss_allein_saison_kategorien_und_du_erklaeren(self):
        no_categories = NEUER_LEAD.replace("Strom, Gas, Internet, Konto und Versicherungen", "Tarife")
        no_season = NEUER_LEAD.replace("Herbst", "Saison")
        no_du = NEUER_LEAD.replace("hilft dir", "hilft Menschen").replace("Du sammelst", "Man sammelt").replace("deine", "ihre").replace("du Tarifdetails", "man Tarifdetails")
        wrong_entity = NEUER_LEAD.replace("FranksFinanzcheck", "FranksFinanzcheckPlus", 1)
        for lead, expected in ((no_categories, "Kernkategorien im Lead"),
                               (no_season, "Saisonname fehlt im Lead"),
                               (no_du, "Du-Ansprache"),
                               (wrong_entity, "Entity")):
            with self.subTest(expected=expected):
                self.assertTrue(any(expected in e for e in hero.validate_candidate(NEUER_TITEL, lead, HERBST, [])))

    def test_prompt_bennt_exakt_die_geprueften_titelwoerter_und_floskeln(self):
        system, _ = hero.prompt_for(HERBST, [])
        for word in hero.TITLE_INTENT_WORDS + hero.BANNED_PHRASES:
            self.assertIn(word, system)
        self.assertTrue(any("Spar-/Vergleichsintention" in e for e in
                            hero.validate_candidate("Dein Überblick über Strom, Gas und Internet im Herbst", NEUER_LEAD, HERBST, [])))
        self.assertTrue(any("KI-Floskel" in e for e in
                            hero.validate_candidate(NEUER_TITEL, NEUER_LEAD + " Entdecke mehr.", HERBST, [])))

    def test_ausgeschriebene_zahlen_und_prozentangaben_werden_verworfen(self):
        lead = NEUER_LEAD.replace("im Herbst", "im Herbst um drei Prozent")
        self.assertTrue(any("Faktenvertrag" in e for e in hero.validate_candidate(NEUER_TITEL, lead, HERBST, [])))

    def test_prompt_hat_keine_widerspruechlichen_zahlenbeispiele(self):
        style = hero.style_summary()
        self.assertNotRegex(style.lower(), r"[0-9€%]|zahl|euro|preis|frist|quelle|studie")
        system, user = hero.prompt_for(HERBST, [])
        self.assertIn('"title"', system)
        self.assertIn('"lead"', system)
        self.assertIn("keine passenden Themenwörter gefunden", user)
        self.assertNotIn("KURATIERTER SAISONHINWEIS", user)


class RechercheNachweis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(hero, "RESEARCH_DIR", self.root)
        patch.start()
        self.addCleanup(patch.stop)
        self.day = dt.date(2026, 10, 29)
        self.brief = self.root / "2026-10-29-internet-recherche.md"
        self.meta = self.brief.with_suffix(".json")
        self.brief.write_text("Aktuelle Signale zu Strom und Gas.", encoding="utf-8")
        self.valid = {"datum": "2026-10-29", "agent_reach": "Agent Reach v1.5.0", "kanal_ok": 2}

    def test_brief_braucht_passenden_erfolgsnachweis(self):
        self.assertIsNone(hero.newest_research_brief(self.day))
        for meta in ({**self.valid, "datum": "2026-10-28"},
                     {**self.valid, "kanal_ok": 0},
                     {**self.valid, "kanal_ok": True},
                     {**self.valid, "agent_reach": ""},
                     []):
            self.meta.write_text(json.dumps(meta), encoding="utf-8")
            with self.subTest(meta=meta):
                self.assertIsNone(hero.newest_research_brief(self.day))
        self.meta.write_text("{ kaputt", encoding="utf-8")
        self.assertIsNone(hero.newest_research_brief(self.day))
        self.meta.write_text(json.dumps(self.valid), encoding="utf-8")
        self.assertEqual(hero.newest_research_brief(self.day), self.brief)
        self.brief.write_text("  ", encoding="utf-8")
        self.assertIsNone(hero.newest_research_brief(self.day))

    def test_nur_echte_treffer_und_keine_quellennamen_oder_fallbacks(self):
        # Im Markdown/Quellnamen stehen Strom und Gas, aber keine Treffer.
        season = {"keywords": ["Strom", "Gas", "Internet"]}
        metadata = {**self.valid, "ergebnisse": {"rss": {
            "Strom und Gas": {"treffer": [], "fehler": None},
            "kaputt": {"treffer": [{"titel": "Internet"}], "fehler": "Fehler"},
        }}}
        self.meta.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertEqual(hero.research_topics(self.brief, season), [])
        metadata["ergebnisse"]["rss"]["Strom und Gas"]["treffer"] = [
            {"titel": "Strom und Gas vergleichen", "url": "https://example.invalid/internet"}]
        self.meta.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertEqual(hero.research_topics(self.brief, season), ["strom", "gas"])


class ProviderRotation(unittest.TestCase):
    def setUp(self):
        self.patches = [
            mock.patch.object(hero, "verfuegbare_anbieter", return_value=["groq", "gemini"]),
            mock.patch.object(hero.llm_client, "model_for", side_effect=lambda p: f"model-{p}"),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_formatfehler_wechselt_sofort_den_anbieter(self):
        calls = []

        def answer(provider, **kwargs):
            calls.append((provider, kwargs))
            return "Kein parsebares Ergebnis" if provider == "groq" else gute_antwort()

        with mock.patch.object(hero.llm_client, "chat", side_effect=answer):
            parsed, log, model = hero.polish_candidate(HERBST, [], [], attempts=1, sleep=lambda _: None)
        self.assertEqual(parsed, (NEUER_TITEL, NEUER_LEAD))
        self.assertEqual(model, "gemini:model-gemini")
        self.assertEqual([p for p, _ in calls], ["groq", "gemini"])
        self.assertIn("ungültiges", log[0])
        self.assertIn("KORREKTURAUFLAGE", calls[1][1]["prompt"])
        for _, kwargs in calls:
            self.assertTrue(kwargs["require_complete"])
            self.assertTrue(kwargs["raise_on_error"])
            self.assertFalse(kwargs["log_errors"])
            self.assertGreater(kwargs["max_tokens"], 700)
            self.assertEqual(kwargs["attempts"], 1)

    def test_faktenfehler_wechselt_ebenfalls_und_erscheint_im_protokoll(self):
        bad = json.dumps({"title": NEUER_TITEL, "lead": NEUER_LEAD.replace("Herbst", "Herbst 2026")})
        with mock.patch.object(hero.llm_client, "chat", side_effect=[bad, gute_antwort()]):
            parsed, log, model = hero.polish_candidate(HERBST, [], [], attempts=1, sleep=lambda _: None)
        self.assertEqual(parsed, (NEUER_TITEL, NEUER_LEAD))
        self.assertIn("Faktenvertrag", log[0])
        self.assertEqual(model, "gemini:model-gemini")

    def test_issue_891_korrektur_und_gemini_budget_ohne_schwächung_des_vertrags(self):
        bad = json.dumps({"title": "Dein Überblick über Strom, Gas und Internet im Herbst", "lead": NEUER_LEAD})
        calls = []
        def answer(provider, **kwargs):
            calls.append((provider, kwargs))
            return bad if provider == "groq" else gute_antwort()
        with mock.patch.object(hero.llm_client, "chat", side_effect=answer):
            parsed, log, _ = hero.polish_candidate(HERBST, [], [], attempts=1, sleep=lambda _: None)
        self.assertEqual(parsed, (NEUER_TITEL, NEUER_LEAD))
        self.assertIn("Titel ohne Spar-/Vergleichsintention", log[0])
        self.assertIn("Titel ohne Spar-/Vergleichsintention", calls[1][1]["prompt"])
        self.assertEqual(calls[0][1]["max_tokens"], hero.POLISH_MAX_TOKENS)
        self.assertEqual(calls[1][1]["max_tokens"], hero.GEMINI_POLISH_MAX_TOKENS)
        self.assertTrue(calls[1][1]["require_complete"])

    def test_alle_fehler_sind_sichtbar_aber_keine_secrets(self):
        secret = "key-that-must-never-be-logged"
        err = urllib.error.HTTPError(f"https://example.invalid/{secret}", 401, secret, None, None)
        with mock.patch.object(hero.llm_client, "chat", side_effect=[err, hero.llm_client.IncompleteResponseError("MAX_TOKENS")]):
            parsed, log, model = hero.polish_candidate(HERBST, [], [], attempts=1, sleep=lambda _: None)
        self.assertIsNone(parsed)
        self.assertEqual(model, "")
        self.assertEqual(len(log), 2)
        self.assertIn("HTTP 401", log[0])
        self.assertIn("MAX_TOKENS", log[1])
        self.assertNotIn(secret, " ".join(log))

    def test_unveraenderter_live_lead_ist_auch_ohne_historie_keine_politur(self):
        same = json.dumps({"title": HERBST["hero_title"], "lead": HERBST["hero_lead"]})
        with mock.patch.object(hero.llm_client, "chat", side_effect=[same, gute_antwort()]):
            parsed, log, model = hero.polish_candidate(HERBST, [], [], attempts=1, sleep=lambda _: None)
        self.assertEqual(parsed, (NEUER_TITEL, NEUER_LEAD))
        self.assertEqual(model, "gemini:model-gemini")
        self.assertIn("aktuell ausgelieferten Fassung", log[0])

    def test_gruener_erster_anbieter_beendet_die_kette(self):
        with mock.patch.object(hero.llm_client, "chat", return_value=gute_antwort()) as chat:
            parsed, log, model = hero.polish_candidate(HERBST, [], [], attempts=3, sleep=lambda _: None)
        self.assertEqual(parsed, (NEUER_TITEL, NEUER_LEAD))
        self.assertEqual(model, "groq:model-groq")
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(len(log), 1)

    def test_alle_anbieter_werden_in_jeder_runde_protokolliert(self):
        waits = []
        with mock.patch.object(hero.llm_client, "chat", return_value=None) as chat:
            parsed, log, model = hero.polish_candidate(HERBST, [], [], attempts=2, sleep=waits.append)
        self.assertIsNone(parsed)
        self.assertEqual(model, "")
        self.assertEqual(chat.call_count, 4)
        self.assertEqual(len(log), 4)
        self.assertEqual(waits, [hero.POLISH_BACKOFF_SECONDS[1]])
        self.assertTrue(all("leere Antwort" in line for line in log))


class DurchlaufIntegration(unittest.TestCase):
    """Echte Dateikette mit simulierten APIs: kein Netz, kein Live-State."""

    def setUp(self):
        original_saisons = hero.SAISONS.read_bytes()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        data = self.root / "data"
        research = data / "research" / "saisonal"
        research.mkdir(parents=True)
        paths = {
            "ROOT": self.root,
            "SAISONS": data / "saisons.yaml",
            "STATE": data / "saisonaler_hero_state.json",
            "HISTORY": data / "saisonaler_hero_history.jsonl",
            "RESEARCH_DIR": research,
            "REPORT": self.root / "SAISONALER-HERO-REPORT.md",
        }
        for name, value in paths.items():
            patch = mock.patch.object(hero, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        hero.SAISONS.write_bytes(original_saisons)
        _, seasons = hero.load_seasons()
        self.season = hero.season_for(dt.date(2026, 10, 29), seasons)
        self.state = {"version": 1, "saisons": {"herbst": {
            "updated": "2026-10-02T22:40:15Z", "fingerprint": hero.fingerprint(self.season),
            "model": "approved-seasonal-baseline", "fehler_serie": 5,
            "letzter_fehler": {"code": "ki-ohne-gueltige-fassung"},
        }, "winter": {"fingerprint": "unberuehrt"}}}
        hero.save_json(hero.STATE, self.state)
        hero.HISTORY.write_text(json.dumps({"hero_lead": self.season["hero_lead"]}, ensure_ascii=False) + "\n", encoding="utf-8")
        self.before_yaml = hero.SAISONS.read_bytes()
        self.before_history = hero.HISTORY.read_bytes()
        self.brief = research / "2026-10-29-internet-recherche.md"
        self.brief.write_text("Recherche-Signal: Strom und Gas", encoding="utf-8")
        self.brief.with_suffix(".json").write_text(json.dumps({
            "datum": "2026-10-29", "agent_reach": "Agent Reach v1.5.0", "kanal_ok": 2,
        }), encoding="utf-8")
        self.output = self.root / "github-output.txt"
        patches = [
            mock.patch.object(hero, "now_utc", return_value=dt.datetime(2026, 10, 29, 12, 0, tzinfo=dt.timezone.utc)),
            mock.patch.object(hero, "guard_source", return_value=(True, "Wache grün")),
            mock.patch.object(hero, "verfuegbare_anbieter", return_value=["groq", "gemini"]),
            mock.patch.object(hero, "POLISH_BACKOFF_SECONDS", (0, 0, 0)),
            mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(self.output)}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    @staticmethod
    def _answer(system, user, provider=None):
        if provider == "groq":
            hero.LAST_BRIDGE_ERROR.append("groq/model-groq: HTTP 429")
            return None, "groq", "model-groq"
        return gute_antwort(), "gemini", "model-gemini"

    def test_faelliger_lauf_schreibt_nur_gepruefte_fassung_und_echten_nachweis(self):
        with mock.patch.object(hero, "call_model", side_effect=self._answer):
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 0)
        _, seasons = hero.load_seasons()
        changed = hero.season_for(dt.date(2026, 10, 29), seasons)
        self.assertEqual(changed["hero_title"], NEUER_TITEL)
        self.assertEqual(changed["hero_lead"], NEUER_LEAD)
        for key in self.season:
            if key not in {"hero_title", "hero_lead"}:
                self.assertEqual(changed[key], self.season[key], key)
        state = hero.load_json(hero.STATE, {})
        record = state["saisons"]["herbst"]
        self.assertEqual(record["model"], "gemini:model-gemini")
        self.assertEqual(record["fingerprint"], hero.fingerprint(changed))
        self.assertEqual(record["research_sha256"], hashlib.sha256(self.brief.read_bytes()).hexdigest())
        self.assertEqual(record["research_json_sha256"], hashlib.sha256(self.brief.with_suffix(".json").read_bytes()).hexdigest())
        self.assertEqual(record["research_json"], str(self.brief.with_suffix(".json").relative_to(self.root)))
        self.assertNotIn("fehler_serie", record)
        self.assertEqual(state["saisons"]["winter"], self.state["saisons"]["winter"])
        self.assertEqual(hero.read_history()[-1]["model"], "gemini:model-gemini")
        report = hero.REPORT.read_text(encoding="utf-8")
        self.assertIn("HTTP 429", report)
        self.assertIn("erst nach erfolgreichem Hugo-Build", report)
        self.assertIn("ampel=gruen", self.output.read_text(encoding="utf-8"))

    def test_kettenausfall_bleibt_rot_und_laesst_hero_und_historie_unveraendert(self):
        with mock.patch.object(hero, "call_model", return_value=("Nicht parsebar", "groq", "m")):
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 4)
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        self.assertEqual(hero.HISTORY.read_bytes(), self.before_history)
        record = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
        self.assertEqual(record["fehler_serie"], 6)
        self.assertEqual(record["fingerprint"], self.state["saisons"]["herbst"]["fingerprint"])
        self.assertEqual(record["letzter_fehler"]["code"], "ki-ohne-gueltige-fassung")
        self.assertIn("ampel=rot", self.output.read_text(encoding="utf-8"))

    def test_guard_rollback_und_state_sind_transaktional(self):
        with mock.patch.object(hero, "call_model", side_effect=self._answer), \
             mock.patch.object(hero, "guard_source", side_effect=[(True, "Basis okay"), (False, "Kandidat ungültig")]):
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 2)
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        self.assertEqual(hero.HISTORY.read_bytes(), self.before_history)
        record = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
        self.assertEqual(record["fehler_serie"], 6)
        self.assertEqual(record["letzter_fehler"]["code"], "wache-verwirft-kandidat")
        self.assertEqual(record["model"], "approved-seasonal-baseline")

    def test_fehler_nach_state_write_rollt_auch_fingerprint_und_historie_zurueck(self):
        with mock.patch.object(hero, "call_model", side_effect=self._answer), \
             mock.patch.object(hero, "append_history", side_effect=OSError("disk full")):
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 2)
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        self.assertEqual(hero.HISTORY.read_bytes(), self.before_history)
        record = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
        self.assertEqual(record["fehler_serie"], 6)
        self.assertEqual(record["fingerprint"], self.state["saisons"]["herbst"]["fingerprint"])
        self.assertEqual(record["letzter_fehler"]["code"], "schreibfehler")
        self.assertEqual(record["model"], "approved-seasonal-baseline")

    def test_basisbestaetigung_rollt_auch_teilweise_geschriebene_historie_zurueck(self):
        before_state = hero.STATE.read_bytes()
        before_history = hero.HISTORY.read_bytes()
        state_copy = json.loads(json.dumps(self.state))

        def partial_write(_row):
            hero.HISTORY.write_text("unvollständiger Eintrag", encoding="utf-8")
            raise OSError("simulierter Plattenfehler")

        with mock.patch.object(hero, "append_history", side_effect=partial_write):
            with self.assertRaises(OSError):
                hero.record_baseline(self.season, self.state, "Redaktion", "approved-seasonal-baseline")
        self.assertEqual(hero.STATE.read_bytes(), before_state)
        self.assertEqual(hero.HISTORY.read_bytes(), before_history)
        self.assertEqual(self.state, state_copy)

    def test_redaktion_loescht_keine_noch_offene_ki_stoerung(self):
        self.state["saisons"]["herbst"]["fingerprint"] = "vorheriger-redaktionsstand"
        hero.save_json(hero.STATE, self.state)
        with mock.patch.object(hero, "call_model", return_value=("Nicht parsebar", "groq", "m")) as call:
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 4)
        self.assertGreater(call.call_count, 0)
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        self.assertEqual(hero.HISTORY.read_bytes(), self.before_history)
        record = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
        self.assertEqual(record["fehler_serie"], 6)
        self.assertEqual(record["fingerprint"], "vorheriger-redaktionsstand")

    def test_redaktion_ohne_stoerung_wird_nach_pruefung_als_basis_uebernommen(self):
        record = self.state["saisons"]["herbst"]
        record["fingerprint"] = "vorheriger-redaktionsstand"
        record.pop("fehler_serie")
        record.pop("letzter_fehler")
        hero.save_json(hero.STATE, self.state)
        with mock.patch.object(hero, "call_model") as call:
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 0)
        call.assert_not_called()
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        saved = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
        self.assertEqual(saved["fingerprint"], hero.fingerprint(self.season))
        self.assertTrue(saved["set_current"])
        self.assertEqual(saved["model"], "approved-seasonal-baseline")

    def test_fehlender_recherche_nachweis_blockiert_die_ki(self):
        self.brief.with_suffix(".json").unlink()
        with mock.patch.object(hero, "call_model") as call:
            rc = hero.main(["--fix", "--date", "2026-10-29"])
        self.assertEqual(rc, 3)
        call.assert_not_called()
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        self.assertEqual(hero.HISTORY.read_bytes(), self.before_history)
        self.assertIn("JSON-Nachweis fehlt", hero.REPORT.read_text(encoding="utf-8"))

    def test_render_rollback_zaehlt_auf_ausgangsstand_und_markiert_report_rot(self):
        hero.REPORT.write_text("# Zwischenstand grün\n", encoding="utf-8")
        rc = hero.main(["--record-render-failure", "--date", "2026-10-29",
                        "--reason", "Hugo-Build=failure; Render-Gates=skipped"])
        self.assertEqual(rc, 0)
        self.assertEqual(hero.SAISONS.read_bytes(), self.before_yaml)
        self.assertEqual(hero.HISTORY.read_bytes(), self.before_history)
        record = hero.load_json(hero.STATE, {})["saisons"]["herbst"]
        self.assertEqual(record["fehler_serie"], 6)
        self.assertEqual(record["letzter_fehler"]["code"], "render-nachweis-fehlgeschlagen")
        report = hero.REPORT.read_text(encoding="utf-8")
        self.assertIn("Zustand:** rot", report)
        self.assertIn("Zwischenstand vor Rücknahme (nicht freigegeben)", report)


class Rueckfallvermeidung(unittest.TestCase):
    def test_nicht_faellige_aber_gescheiterte_politur_wird_erneut_versucht(self):
        now = dt.datetime(2026, 10, 29, tzinfo=dt.timezone.utc)
        state = {"saisons": {"herbst": {"updated": "2026-10-28T00:00:00Z",
                                        "fingerprint": hero.fingerprint(HERBST),
                                        "fehler_serie": 1}}}
        status = hero.due_state(HERBST, state, False, now)
        self.assertTrue(status["due"])
        self.assertEqual(status["code"], "wiederholung")


if __name__ == "__main__":
    unittest.main()
