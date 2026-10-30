#!/usr/bin/env python3
"""Regressionen für #912: Kalender, Prüfumfang und dauerhafte Fachbefunde."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import faktenfrische as ff
from scripts import faktenfrische_befund_ledger as ledger
from scripts import faktenfrische_kapazitaet as kap
from scripts import publish_gate as pg
from scripts import release_scorecard as rs

TAG = dt.date(2026, 10, 30)


def artikel(slug, alter, titel="Heizung Winter"):
    return {"slug": slug, "titel": titel, "beschreibung": "", "keywords": [],
            "pillar": "", "bereich": "artikel", "faktencheck": TAG - dt.timedelta(days=alter)}


class KalenderTests(unittest.TestCase):
    def test_wochenende_hat_keine_geliehenen_plaetze(self):
        # Freitag geprüft, Montag wieder fällig. Di+Do kann diese Frist nicht halten.
        cfg = {"intervalle": {"saison_tage": 3},
               "planung": {"vorlauf_tage": 0, "nachhol_frist_tage": 7, "horizont_tage": 7}}
        a = artikel("freitag", 0)
        tage = kap.lauf_tage(["0 4 * * 2,4"], TAG, 7)
        p = kap.plan([a], cfg, 10, 2 / 7, TAG, lauftage=tage)
        self.assertFalse(p["puenktlich"])
        self.assertGreater(p["verletzungen_neu"], 0)

    def test_tagesbudget_wird_nicht_angеспart(self):
        entries = kap.eintraege_bauen([artikel("a", 40), artikel("b", 40)],
                                      ff.lade_config(), TAG)
        result = kap.simuliere(entries, 1, TAG, 0, {TAG})
        self.assertEqual(len(result["erledigt"]), 1)

    def test_auswahl_und_simulation_benutzen_denselben_schluessel(self):
        a = [artikel("alt-standard", 200, "Aufräumen"),
             artikel("neu-saison", 31), artikel("noch-saison", 35)]
        cfg = ff.lade_config()
        for item in a:
            item["_faellig"] = ff.faelligkeit(item, cfg, TAG)
        real = sorted(a, key=lambda x: ff.edf_schluessel(x, x["_faellig"]))
        entries = kap.eintraege_bauen(a, cfg, TAG)
        for e in entries:
            e["_faellig"] = {"prio": e["prio"], "frist": e["frist"]}
        geplant = sorted(entries, key=lambda x: ff.edf_schluessel(x, x["_faellig"]))
        self.assertEqual([x["slug"] for x in real], [x["slug"] for x in geplant])

    def test_folgetermin_zaehlt_ab_echtem_prueftag(self):
        cfg = {"intervalle": {"saison_tage": 3},
               "planung": {"vorlauf_tage": 0, "horizont_tage": 5}}
        e = kap.eintraege_bauen([artikel("a", 10)], cfg, TAG)
        p = kap.plan([artikel("a", 10)], cfg, 1, 1.0, TAG, horizont_tage=5)
        self.assertEqual(p["abbau_tage"], 0)
        self.assertEqual(p["verletzungen_folge"], 0)
        self.assertEqual(e[0]["frist"], TAG - dt.timedelta(days=7))

    def test_kalenderfehler_ist_nicht_gruen(self):
        self.assertIsNone(kap.lauf_tage(["0 4 1 * *"], TAG, 7))
        self.assertIsNone(kap.lauf_tage(["ungültig"], TAG, 7))
        with self.assertRaises(ValueError):
            kap.plan([], ff.lade_config(), 3, 2 / 7, TAG)

    def test_doppelter_slug_ist_werkzeugfehler(self):
        e = kap.eintraege_bauen([artikel("a", 1)], ff.lade_config(), TAG)
        with self.assertRaises(ValueError):
            kap.simuliere(e + e, 1, TAG, 1, {TAG})


class PruefumfangTests(unittest.TestCase):
    def test_pruefung_erhaelt_den_gesamten_text_und_bindet_die_antwort(self):
        body = "Anfang. " + "Mitte. " * 2000 + "LETZTER ABSATZ mit Preisangabe."
        art = {"titel": "Test", "beschreibung": "", "body": body}
        digest = ledger.pruef_hash(art)
        dossier = {"treffer": [{"url": "https://www.destatis.de/x", "titel": "Quelle"}]}
        answer = json.dumps({"artikel_sha256": digest, "befunde": [], "quellen": []})
        with patch.object(ff, "verfuegbare_anbieter", return_value=["groq"]), \
             patch.object(ff.llm_client, "model_for", return_value="modell"), \
             patch.object(ff.llm_client, "chat", return_value=answer) as chat:
            self.assertTrue(ff.claude_fachpruefung(art, dossier, {})[2].startswith("geprüft"))
            prompt = chat.call_args.kwargs["prompt"]
            self.assertIn("LETZTER ABSATZ", prompt)
            self.assertIn(digest, prompt)
            self.assertNotIn("ARTIKELTEXT (gekürzt)", prompt)

    def test_falsche_fassung_ist_keine_pruefung(self):
        art = {"titel": "Test", "beschreibung": "", "body": "A"}
        dossier = {"treffer": [{"url": "https://www.destatis.de/x", "titel": "Quelle"}]}
        answer = json.dumps({"artikel_sha256": "0" * 64, "befunde": [], "quellen": []})
        with patch.object(ff, "verfuegbare_anbieter", return_value=["groq"]), \
             patch.object(ff.llm_client, "model_for", return_value="modell"), \
             patch.object(ff.llm_client, "chat", return_value=answer):
            self.assertIn("Prüfversion passt nicht", ff.claude_fachpruefung(art, dossier, {})[2])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.finding = {"typ": "praezision", "text": "Preis ohne Beleg", "beleg": ""}
        self.entry = {"id": ledger.befund_id("a", self.finding), "slug": "a",
                      "fassung_sha256": ledger.body_hash("Fassung A"), **self.finding}
        self.tmp = tempfile.TemporaryDirectory()
        self.queue = Path(self.tmp.name) / "queue.json"
        self.decisions = Path(self.tmp.name) / "decisions.yaml"
        self.queue.write_text(json.dumps({"fachbefunde": [self.entry]}))
        self.decisions.write_text("entscheidungen: []\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_spaeterer_lauf_loescht_befund_nicht(self):
        self.assertEqual(ledger.offene_befunde(self.queue, self.decisions), [self.entry])
        self.assertEqual(ledger.zusammenfuehren({"fachbefunde": [self.entry]}, []), [self.entry])

    def test_menschliche_entscheidung_ist_fassungsgebunden(self):
        decision = {"slug": "a", "befund_id": self.entry["id"],
                    "fassung_sha256": self.entry["fassung_sha256"],
                    "entschieden_von": "Redaktion", "begruendung": "Preisangabe entfernt"}
        self.decisions.write_text(yaml.safe_dump({"entscheidungen": [decision]}))
        self.assertEqual(ledger.offene_befunde(self.queue, self.decisions), [])
        changed = dict(self.entry, fassung_sha256=ledger.body_hash("Fassung B"))
        self.queue.write_text(json.dumps({"fachbefunde": [changed]}))
        self.assertEqual(ledger.offene_befunde(self.queue, self.decisions), [changed])

    def test_legacy_migration_verliert_keinen_befund(self):
        old = {"erzeugt": "2026-10-27", "laeufe": [{"slug": "a", "befunde": [self.finding]}]}
        entries = ledger.eintraege_aus_queue(old)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["fassung_sha256"], "legacy-unbekannt")

    def test_beschaedigtes_ledger_ist_werkzeugfehler(self):
        self.queue.write_text('{kaputt')
        failed, warning, tool = pg.fakten_befund_failures(
            ["a"], queue_path=self.queue, decisions_path=self.decisions)
        self.assertTrue(tool)
        self.assertEqual(failed, {})
        self.assertIn("nicht beweisbar", warning)
        with self.assertRaises(ledger.LedgerFehler):
            ledger.offene_befunde(self.queue, self.decisions)
        self.decisions.write_text("entscheidungen: [null]\n")
        with self.assertRaises(ledger.LedgerFehler):
            ledger.offene_befunde(self.queue, self.decisions)

    def test_scorecard_und_publish_gate_lesen_denselben_collector(self):
        failed = {"a": ["Preis ohne Beleg"]}
        with patch.object(pg, "fakten_befund_failures", return_value=(failed, None, False)) :
            ctx = rs.bewerte_artikel("a", {"a": {"F4-fachbefund": ["Preis ohne Beleg"]}},
                                     {}, {"erg": {}, "fakten": {}},
                                     rs.check_register(rs.ssot_laden()), {}, TAG)
            self.assertEqual(ctx["dimensionen"]["faktenalter"], "blockiert")
        self.assertIn("publish_gate.fakten_befund_failures", Path(rs.__file__).read_text())
        self.assertIn("fakten_befund_failures(candidates)", Path(pg.__file__).read_text())

    def test_unbekannte_legacy_fassung_kann_nicht_unterschrieben_werden(self):
        self.decisions.write_text(yaml.safe_dump({"entscheidungen": [{
            "slug": "a", "befund_id": self.entry["id"], "fassung_sha256": "legacy-unbekannt",
            "entschieden_von": "Redaktion", "begruendung": "nicht zulässig"}]}))
        with self.assertRaises(ledger.LedgerFehler):
            ledger.offene_befunde(self.queue, self.decisions)


if __name__ == "__main__":
    unittest.main()
