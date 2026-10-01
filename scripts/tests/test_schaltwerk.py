#!/usr/bin/env python3
"""Tests für das Schaltwerk (scripts/schaltwerk.py) – den Zapier-Nachbau.

Hintergrund: Ab dem 01.10.2026 verdrahtet das Schaltwerk die Social-Media-
Automatisierung ohne Zapier und ohne Fremdkosten. Weil es scharf posten
und Issues anlegen kann, nageln diese Tests die Sicherheitsversprechen fest:

  1. Dedupe: dasselbe Ereignis feuert niemals zweimal.
  2. Throttle: Tageslimit und Sperrfrist greifen hart.
  3. Probelauf: `--dry-run` verändert weder State noch Dateien.
  4. Fail-safe: eine kaputte Regel killt den Lauf nicht.
  5. Standby ≠ Fehler: ein Kanal ohne Token lässt den Lauf grün.
  6. Self-Healing: eine gescheiterte Kette wird NICHT als erledigt markiert.
  7. Leitplanke: Agent-Reach-Signale werden nie direkt gepostet.
  8. Pfad-Schutz: `datei_anhaengen` darf das Repository nicht verlassen.

Läuft deterministisch ohne Netz:
    python3 -m unittest scripts.tests.test_schaltwerk
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import schaltwerk as sw            # noqa: E402
import schaltwerk_actions as act   # noqa: E402
import schaltwerk_triggers as trg  # noqa: E402

JETZT = sw.berlin_now()


def leerer_state() -> dict:
    return {"version": 1, "ausgeloest": {}, "zaehler": {},
            "letzter_lauf": {}, "slots": {}, "marker": {}}


def regelwerk(aktionen=None, **extra) -> dict:
    regel = {
        "id": "probe",
        "name": "Probe",
        "enabled": True,
        "trigger": {"typ": "manuell", "params": {}},
        "aktionen": aktionen or [{"typ": "protokoll", "params": {"text": "hallo"}}],
        "dedupe_key": "fix",
    }
    regel.update(extra)
    return {"version": 1, "meta": {}, "regeln": [regel]}


class TestFilterOperatoren(unittest.TestCase):
    daten = {"artikel": {"title": "Strom sparen 2026", "slug": "abc", "draft": False},
             "zahl": 12}

    def test_textoperatoren(self):
        for op, wert, erwartet in [
            ("enthaelt", "strom", True),
            ("enthaelt", "gas", False),
            ("enthaelt_nicht", "gas", True),
            ("beginnt_mit", "Strom", True),
            ("endet_mit", "2026", True),
            ("regex", r"\d{4}$", True),
        ]:
            with self.subTest(op=op):
                ok, _ = sw.pruefe_filter(
                    {"feld": "artikel.title", "operator": op, "wert": wert}, self.daten)
                self.assertIs(ok, erwartet)

    def test_zahlenoperatoren(self):
        self.assertTrue(sw.pruefe_filter(
            {"feld": "zahl", "operator": "groesser", "wert": 5}, self.daten)[0])
        self.assertFalse(sw.pruefe_filter(
            {"feld": "zahl", "operator": "kleiner", "wert": 5}, self.daten)[0])

    def test_unbekannter_operator_ist_fail_closed(self):
        ok, grund = sw.pruefe_filter({"feld": "zahl", "operator": "xyz"}, self.daten)
        self.assertFalse(ok)
        self.assertIn("unbekannter Operator", grund)

    def test_fehlendes_feld_blockiert_statt_zu_krachen(self):
        ok, _ = sw.pruefe_filter(
            {"feld": "gibt.es.nicht", "operator": "nicht_leer"}, self.daten)
        self.assertFalse(ok)

    def test_filterkette_ist_und_verknuepft(self):
        regel = {"filter": [
            {"feld": "artikel.title", "operator": "enthaelt", "wert": "Strom"},
            {"feld": "artikel.title", "operator": "enthaelt", "wert": "Gas"},
        ]}
        self.assertFalse(sw.filter_erfuellt(regel, self.daten)[0])


class TestDedupeUndThrottle(unittest.TestCase):
    def test_dedupe_verhindert_zweiten_lauf(self):
        state = leerer_state()
        regeln = regelwerk()
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "state.json")
            sw.STATE_PATH, alt = pfad, sw.STATE_PATH
            sw.LOG_PATH, alt_log = os.path.join(tmp, "log.jsonl"), sw.LOG_PATH
            try:
                b1 = sw.run(regeln, state=state, jetzt=JETZT)
                b2 = sw.run(regeln, state=sw.load_state(), jetzt=JETZT)
            finally:
                sw.STATE_PATH, sw.LOG_PATH = alt, alt_log
        self.assertEqual(b1["regeln"][0]["treffer"], 1)
        self.assertEqual(b2["regeln"][0]["treffer"], 0, "Dedupe hat nicht gegriffen")

    def test_tageslimit_sperrt(self):
        state = leerer_state()
        state["zaehler"]["probe"] = {JETZT.date().isoformat(): 3}
        ok, grund = sw.throttle_ok({"id": "probe", "throttle": {"max_pro_tag": 3}},
                                   state, JETZT)
        self.assertFalse(ok)
        self.assertIn("Tageslimit", grund)

    def test_sperrfrist_greift(self):
        state = leerer_state()
        state["letzter_lauf"]["probe"] = sw.iso(JETZT)
        ok, _ = sw.throttle_ok({"id": "probe", "throttle": {"cooldown_minuten": 120}},
                               state, JETZT)
        self.assertFalse(ok)

    def test_dedupe_key_vorlage(self):
        key = sw.dedupe_key({"dedupe_key": "u:{artikel.slug}"},
                            {"daten": {"artikel": {"slug": "xy"}}})
        self.assertEqual(key, "u:xy")


class TestProbelauf(unittest.TestCase):
    def test_dry_run_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "state.json")
            log = os.path.join(tmp, "log.jsonl")
            sw.STATE_PATH, alt = pfad, sw.STATE_PATH
            sw.LOG_PATH, alt_log = log, sw.LOG_PATH
            try:
                sw.run(regelwerk(), dry_run=True, state=leerer_state(), jetzt=JETZT)
                self.assertFalse(os.path.exists(pfad), "Probelauf hat State geschrieben")
                self.assertFalse(os.path.exists(log), "Probelauf hat protokolliert")
            finally:
                sw.STATE_PATH, sw.LOG_PATH = alt, alt_log

    def test_datei_anhaengen_im_probelauf(self):
        res = act.aktion_datei_anhaengen(
            {"datei": "data/test.log", "text": "x"}, {}, {"dry_run": True})
        self.assertEqual(res["status"], "uebersprungen")


class TestFailSafe(unittest.TestCase):
    def test_unbekannte_aktion_meldet_fehler_statt_absturz(self):
        res = sw.fuehre_aktionen({"id": "x", "aktionen": [{"typ": "gibtsnicht"}]},
                                 {"daten": {}}, {"jetzt": JETZT, "dry_run": True})
        self.assertEqual(res[0]["status"], "fehler")

    def test_unbekannter_trigger_stoppt_den_lauf_nicht(self):
        regeln = {"version": 1, "meta": {}, "regeln": [
            {"id": "kaputt", "trigger": {"typ": "gibtsnicht"},
             "aktionen": [{"typ": "protokoll", "params": {"text": "a"}}]},
            {"id": "heil", "trigger": {"typ": "manuell"},
             "aktionen": [{"typ": "protokoll", "params": {"text": "b"}}]},
        ]}
        bericht = sw.run(regeln, dry_run=True, state=leerer_state(), jetzt=JETZT)
        self.assertIn("unbekannter Trigger", bericht["regeln"][0]["notiz"])
        self.assertEqual(bericht["regeln"][1]["treffer"], 1)

    def test_aktion_die_wirft_wird_gefangen(self):
        def bombe(params, daten, ctx):
            raise RuntimeError("peng")

        act.AKTION["testbombe"] = bombe
        try:
            res = sw.fuehre_aktionen({"id": "x", "aktionen": [{"typ": "testbombe"}]},
                                     {"daten": {}}, {"jetzt": JETZT, "dry_run": True})
        finally:
            act.AKTION.pop("testbombe", None)
        self.assertEqual(res[0]["status"], "fehler")
        self.assertIn("peng", res[0]["meldung"])


class TestStandbyUndSelfHealing(unittest.TestCase):
    def test_standby_ist_kein_fehler(self):
        res = act.aktion_social_post({"kanal": "mastodon"}, {}, {"dry_run": True})
        self.assertIn(res["status"], ("standby", "uebersprungen", "fehler"))
        if res["status"] == "fehler":
            self.fail(f"Fehlendes Token darf kein Fehler sein: {res['meldung']}")

    def test_unbekannter_kanal_ist_ein_fehler(self):
        res = act.aktion_social_post({"kanal": "gibtsnicht"}, {}, {"dry_run": True})
        self.assertEqual(res["status"], "fehler")

    def test_gescheiterte_kette_wird_nicht_als_erledigt_markiert(self):
        regeln = regelwerk(aktionen=[{"typ": "gibtsnicht"}])
        state = leerer_state()
        with tempfile.TemporaryDirectory() as tmp:
            sw.STATE_PATH, alt = os.path.join(tmp, "s.json"), sw.STATE_PATH
            sw.LOG_PATH, alt_log = os.path.join(tmp, "l.jsonl"), sw.LOG_PATH
            try:
                sw.run(regeln, state=state, jetzt=JETZT)
                neu = sw.load_state()
            finally:
                sw.STATE_PATH, sw.LOG_PATH = alt, alt_log
        self.assertEqual(neu.get("ausgeloest"), {},
                         "Fehlgeschlagene Kette darf nicht als erledigt gelten")


class TestLeitplanken(unittest.TestCase):
    def test_pfad_ausbruch_wird_abgelehnt(self):
        for pfad in ("../geheim.txt", "/etc/passwd"):
            res = act.aktion_datei_anhaengen({"datei": pfad, "text": "x"}, {},
                                             {"dry_run": False})
            self.assertEqual(res["status"], "fehler", pfad)

    def test_regelwerk_postet_keine_reach_signale(self):
        regeln = sw.load_regeln()
        for r in regeln.get("regeln") or []:
            if (r.get("trigger") or {}).get("typ") != "recherche_signal":
                continue
            for a in r.get("aktionen") or []:
                self.assertNotIn((a or {}).get("typ"),
                                 ("social_post", "social_welle", "social_autopilot_lauf"),
                                 f"Regel {r.get('id')} postet Recherche-Signale direkt")

    def test_regelwerk_verdrahtet_keinen_kostenpflichtigen_kanal(self):
        regeln = sw.load_regeln()
        teuer = {str(k).lower() for k in
                 (regeln.get("meta") or {}).get("kostenpflichtige_kanaele") or []}
        for r in regeln.get("regeln") or []:
            for a in r.get("aktionen") or []:
                params = (a or {}).get("params") or {}
                self.assertNotIn(str(params.get("kanal") or "").lower(), teuer)
                for k in params.get("kanaele") or []:
                    self.assertNotIn(str(k).lower(), teuer)

    def test_jede_regel_ist_ausfuehrbar(self):
        regeln = sw.load_regeln()
        self.assertTrue(regeln.get("regeln"))
        for r in regeln["regeln"]:
            self.assertIn((r.get("trigger") or {}).get("typ"), trg.PROVIDER, r.get("id"))
            for a in r.get("aktionen") or []:
                self.assertIn((a or {}).get("typ"), act.AKTION, r.get("id"))

    def test_selftest_der_engine_besteht(self):
        self.assertEqual(sw.selftest(), 0)


class TestTrigger(unittest.TestCase):
    def test_zeitplan_feuert_nur_im_toleranzfenster(self):
        state = leerer_state()
        ctx = {"jetzt": JETZT, "state": state}
        zeit = JETZT.strftime("%H:%M")
        self.assertEqual(len(trg.trigger_zeitplan({"zeiten": [zeit]}, ctx)), 1)
        # zweiter Aufruf im selben Slot → nichts (Slot verbraucht)
        self.assertEqual(len(trg.trigger_zeitplan({"zeiten": [zeit]}, ctx)), 0)

    def test_zeitplan_ausserhalb_des_fensters_schweigt(self):
        ctx = {"jetzt": JETZT, "state": leerer_state()}
        fremd = (JETZT.hour + 5) % 24
        self.assertEqual(trg.trigger_zeitplan(
            {"zeiten": [f"{fremd:02d}:00"], "toleranz_minuten": 10}, ctx), [])

    def test_datei_geaendert_feuert_beim_erstkontakt_nicht(self):
        state = leerer_state()
        ctx = {"jetzt": JETZT, "state": state}
        params = {"datei": "data/automationen.yaml"}
        self.assertEqual(trg.trigger_datei_geaendert(params, ctx), [],
                         "Erstkontakt darf nicht feuern (Rollout-Lawine)")
        self.assertEqual(trg.trigger_datei_geaendert(params, ctx), [])
        state["marker"]["datei:data/automationen.yaml"] = "andererhash"
        self.assertEqual(len(trg.trigger_datei_geaendert(params, ctx)), 1)

    def test_webhook_filtert_nach_typ(self):
        ctx = {"jetzt": JETZT, "state": leerer_state(),
               "event": {"typ": "sofortpost", "kanal": "mastodon"}}
        self.assertEqual(len(trg.trigger_webhook({"typ": "sofortpost"}, ctx)), 1)
        self.assertEqual(trg.trigger_webhook({"typ": "anderes"}, ctx), [])
        self.assertEqual(trg.trigger_webhook({}, {"jetzt": JETZT, "event": None}), [])

    def test_alle_trigger_laufen_ohne_netz_durch(self):
        ctx = {"jetzt": JETZT, "state": leerer_state(), "dry_run": True}
        for name, fn in trg.PROVIDER.items():
            with self.subTest(trigger=name):
                try:
                    res = fn({}, ctx)
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"Trigger {name} wirft {exc!r} statt leer zu liefern")
                self.assertIsInstance(res, list)


class TestCockpit(unittest.TestCase):
    def test_cockpit_wird_geschrieben(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "COCKPIT.md")
            text = sw.schreibe_cockpit(sw.load_regeln(), state=leerer_state(), pfad=pfad)
        self.assertIn("SCHALTWERK", text)
        self.assertIn("| Kanal |", text)
        for r in sw.load_regeln().get("regeln") or []:
            self.assertIn(str(r.get("id")), text)


class TestStatePflege(unittest.TestCase):
    def test_alte_marken_verfallen(self):
        state = leerer_state()
        alt = sw.iso(JETZT - __import__("datetime").timedelta(days=90))
        state["ausgeloest"] = {"a::alt": alt, "a::neu": sw.iso(JETZT)}
        sw.prune_state(state)
        self.assertNotIn("a::alt", state["ausgeloest"])
        self.assertIn("a::neu", state["ausgeloest"])

    def test_render_entfernt_unbekannte_platzhalter(self):
        self.assertEqual(sw.render("x {fehlt.da} y", {}), "x  y")

    def test_render_arbeitet_rekursiv_in_params(self):
        out = sw.render({"a": "{n}", "b": ["{n}", {"c": "{n}"}]}, {"n": 5})
        self.assertEqual(out, {"a": "5", "b": ["5", {"c": "5"}]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
