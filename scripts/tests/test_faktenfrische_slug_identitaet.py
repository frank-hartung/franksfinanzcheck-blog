#!/usr/bin/env python3
"""Regressionen für WF-8F6F / #1073: Fachbefunde überleben Re-Dating.

Der Reserve-Finisher darf Entwürfe auf ein neues Datum heben. Dabei ändert
sich der Ordner-Slug, nicht aber die Identität der bereits erhobenen
Fachbefunde. Diese Tests verlangen eine eindeutige Alias-Kette vom alten
Ledger-Slug zum aktuellen Artikel – ohne einen Befund zu schließen.
"""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische_befund_akte as akte  # noqa: E402
import faktenfrische_befund_ledger as ledger  # noqa: E402
import publish_gate  # noqa: E402
import reserve_finisher  # noqa: E402

TAG = dt.date(2026, 11, 5)
FINDING = {"typ": "luecke", "text": "Saisonale Preisprognose ohne Beleg",
           "beleg": "https://www.bundesnetzagentur.de/x"}


class SlugIdentitaetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.queue = self.dir / "queue.json"
        self.decisions = self.dir / "entscheidungen.yaml"
        self.alt_hash = ledger.body_hash("alte Fassung")
        self.neu_hash = ledger.body_hash("neue Fassung")
        self.entry = {
            "id": ledger.befund_id("2026-11-01-thema", FINDING),
            "slug": "2026-11-01-thema",
            "fassung_sha256": self.alt_hash,
            "text_sha256": self.alt_hash,
            **FINDING,
            "zuletzt_gesehen": "2026-11-03 12:18 UTC",
        }
        self.queue.write_text(json.dumps({"fachbefunde": [self.entry]}),
                              encoding="utf-8")
        self.aliases = {"2026-11-01-thema": "2026-11-05-thema"}
        self.fassungen = {"2026-11-05-thema": {
            "text": self.neu_hash, "pruef": self.neu_hash}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_befund_folgt_dem_aktuellen_slug_und_bleibt_offen(self):
        stand = ledger.befunde_mit_status(
            self.queue, self.decisions, self.fassungen, TAG,
            aliases=self.aliases)
        self.assertEqual(len(stand), 1)
        self.assertEqual(stand[0]["slug"], "2026-11-05-thema")
        self.assertEqual(stand[0]["ursprungs_slug"], "2026-11-01-thema")
        self.assertEqual(stand[0]["id"], self.entry["id"])
        self.assertEqual(stand[0]["fassung_status"], "ueberholt")
        self.assertTrue(stand[0]["entscheidbar"])
        wache = ledger.wache(queue_path=self.queue,
                             decisions_path=self.decisions,
                             fassungen=self.fassungen, stichtag=TAG,
                             aliases=self.aliases)
        self.assertTrue(wache["gruen"])
        self.assertEqual(wache["offen"], 1, "Alias darf nichts schließen")
        zustand = akte.zustand_bauen(stand, {}, frist_tage=14,
                                     eskalation_tage=21, stichtag=TAG)
        self.assertEqual(zustand["befunde"][0]["ursprungs_slug"],
                         "2026-11-01-thema")
        dokument = akte.akte_bauen(stand, {}, zustand)
        self.assertIn("Herkunft nach Datums-Lift", dokument)
        self.assertIn("`2026-11-01-thema` → `2026-11-05-thema`", dokument)
        self.assertIn("keine fachliche Entscheidung", dokument)

    def test_publish_gate_blockiert_den_neuen_artikel_weiter(self):
        with patch.object(ledger, "fassungen_aus_bestand",
                          return_value=self.fassungen), \
             patch.object(ledger, "slug_aliases_aus_bestand",
                          return_value=self.aliases):
            # Die Produktionsfunktion lädt Bestand und Alias gemeinsam; die
            # Patches dokumentieren hier die beiden Datenquellen isoliert.
            with patch.object(ledger, "bestand_identitaeten",
                              return_value=(self.fassungen, self.aliases)):
                failed, warning, tool = publish_gate.fakten_befund_failures(
                    ["2026-11-05-thema"], queue_path=self.queue,
                    decisions_path=self.decisions)
        self.assertFalse(tool)
        self.assertIsNone(warning)
        self.assertIn("2026-11-05-thema", failed)
        self.assertIn(self.entry["id"], failed["2026-11-05-thema"][0])

    def test_mensch_entscheidet_am_neuen_text_mit_altbeleg(self):
        decision = ledger.entscheidung_anfuegen(
            self.entry["id"], "Redaktion",
            "Preisprognose im aktuellen Entwurf vollständig entfernt",
            queue_path=self.queue, decisions_path=self.decisions,
            fassungen=self.fassungen, heute=TAG, aliases=self.aliases)
        self.assertEqual(decision["slug"], "2026-11-05-thema")
        self.assertEqual(decision["befund_ursprung_slug"], "2026-11-01-thema")
        self.assertEqual(decision["befund_fassung"], self.alt_hash)
        self.assertEqual(decision["geprueft_fassung"], self.neu_hash)
        self.assertEqual(ledger.offene_befunde(
            self.queue, self.decisions, self.fassungen,
            aliases=self.aliases), [])
        roh = yaml.safe_load(self.decisions.read_text(encoding="utf-8"))
        self.assertEqual(roh["entscheidungen"][0]["befund_id"], self.entry["id"])
        # Ändert sich der geprüfte Text erneut, öffnet derselbe Befund wieder –
        # unter dem aktuellen Slug und mit derselben ID.
        spaeter = {"2026-11-05-thema": {"text": ledger.body_hash("spaeter"),
                                        "pruef": ledger.body_hash("spaeter")}}
        erneut = ledger.offene_befunde(
            self.queue, self.decisions, spaeter, aliases=self.aliases)
        self.assertEqual(len(erneut), 1)
        self.assertEqual(erneut[0]["slug"], "2026-11-05-thema")
        self.assertEqual(erneut[0]["id"], self.entry["id"])

    def test_alte_entscheidung_wird_fassungsgebunden_geprueft(self):
        """Eine Entscheidung am alten Slug gilt – aber nur an ihrer Fassung."""
        gleich = {"2026-11-05-thema": {
            "text": self.alt_hash, "pruef": self.alt_hash}}
        self._entscheidung("2026-11-01-thema", geprueft=self.alt_hash)
        self.assertEqual(ledger.offene_befunde(
            self.queue, self.decisions, gleich, aliases=self.aliases), [],
            "Die historische Entscheidung muss über den Alias auffindbar sein")
        # Der Mensch hat eine Fassung geprüft, die es heute nicht mehr gibt:
        # Der Alias verschiebt die Entscheidung, er beglaubigt sie nicht.
        self._entscheidung("2026-11-01-thema",
                           geprueft=ledger.body_hash("zwischenstand"))
        offen = ledger.offene_befunde(
            self.queue, self.decisions, self.fassungen, aliases=self.aliases)
        self.assertEqual(len(offen), 1)
        self.assertEqual(offen[0]["slug"], "2026-11-05-thema")
        self.assertEqual(offen[0]["ursprungs_slug"], "2026-11-01-thema")

    def _entscheidung(self, slug: str, geprueft: str) -> None:
        self.decisions.write_text(yaml.safe_dump({"entscheidungen": [{
            "slug": slug, "befund_id": self.entry["id"],
            "befund_fassung": self.alt_hash, "geprueft_fassung": geprueft,
            "entschieden_von": "Redaktion",
            "begruendung": "Die beanstandete Prognose wurde vollständig entfernt.",
        }]}), encoding="utf-8")

    def test_alias_kette_und_schleife(self):
        kette = {"2026-11-01-thema": "mitte", "mitte": "2026-11-05-thema"}
        self.assertEqual(ledger.canonical_slug("2026-11-01-thema", kette),
                         "2026-11-05-thema")
        projiziert = ledger.offene_befunde(
            self.queue, self.decisions, self.fassungen, aliases=kette)
        self.assertEqual(projiziert[0]["slug"], "2026-11-05-thema")
        self.assertEqual(projiziert[0]["ursprungs_slug"], "2026-11-01-thema")
        with self.assertRaises(ledger.LedgerFehler):
            ledger.canonical_slug("alt", {"alt": "mitte", "mitte": "alt"})
        with self.assertRaises(ledger.LedgerFehler):
            ledger.canonical_slug("alt", {"alt": "alt"})

    def test_echte_loeschung_bleibt_trotz_alias_rot(self):
        stand = ledger.wache(queue_path=self.queue,
                             decisions_path=self.decisions, fassungen={},
                             stichtag=TAG, aliases=self.aliases)
        self.assertFalse(stand["gruen"])
        self.assertEqual(stand["nicht_entscheidbar"], 1)
        self.assertIn("2026-11-05-thema", stand["funde"][0])

    def test_legacy_ohne_seite_ist_ebenfalls_nicht_entscheidbar(self):
        legacy = dict(self.entry, fassung_sha256=ledger.LEGACY, text_sha256="")
        self.assertEqual(ledger.fassung_status(legacy, {}, TAG)["status"],
                         "seite-fehlt")


class BestandAliasTests(unittest.TestCase):
    def test_frontmatter_aliases_werden_gelesen_und_kollisionen_sind_rot(self):
        seiten = [
            {"slug": "neu", "fm": 'title: "Neu"\nfaktenfrische_aliases:\n  - "alt"\n',
             "body": "Text"},
            {"slug": "andere", "fm": 'title: "Andere"\n', "body": "Text"},
        ]
        with patch.object(ledger, "_alle_artikel_fuer_identitaet", return_value=seiten):
            fassungen, aliases = ledger.bestand_identitaeten()
        self.assertEqual(aliases, {"alt": "neu"})
        self.assertEqual(set(fassungen), {"neu", "andere"})

        kollision = seiten + [{"slug": "alt", "fm": 'title: "Kollision"\n',
                               "body": "Zweite Seite"}]
        with patch.object(ledger, "_alle_artikel_fuer_identitaet", return_value=kollision):
            with self.assertRaises(ledger.LedgerFehler):
                ledger.bestand_identitaeten()

        mehrdeutig = seiten + [{
            "slug": "zweites-ziel", "body": "Text",
            "fm": 'title: "Zweites Ziel"\nfaktenfrische_aliases: ["alt"]\n'}]
        with patch.object(ledger, "_alle_artikel_fuer_identitaet",
                          return_value=mehrdeutig):
            with self.assertRaisesRegex(ledger.LedgerFehler, "zwei Artikel"):
                ledger.bestand_identitaeten()


class ReserveLiftAliasTests(unittest.TestCase):
    def test_redating_schreibt_alias_idempotent_und_kettenfaehig(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            original = posts / "2026-11-01-thema" / "index.md"
            original.parent.mkdir(parents=True)
            original.write_text(
                "---\ntitle: Thema\ndate: 2026-11-01T06:00:00Z\n"
                "draft: true\nreserve: true\n---\n\nUnveränderter Text.\n",
                encoding="utf-8")
            with patch.object(reserve_finisher, "POSTS_DIR", posts), \
                 patch.object(reserve_finisher, "today_prefix",
                              return_value="2026-11-05"):
                reserve_finisher.SNAPSHOTS.clear()
                aktuell = reserve_finisher.lift_to_today(original)
                erster = aktuell.read_text(encoding="utf-8")
                self.assertIn('faktenfrische_aliases:\n  - "2026-11-01-thema"', erster)
                self.assertTrue(aktuell.exists())
                self.assertFalse(original.exists())
                self.assertTrue(aktuell.read_text(encoding="utf-8").endswith(
                    "Unveränderter Text.\n"))
                # Kein zweites Datum-Lift am selben Tag: keine Alias-Dopplung,
                # keine neue Dateiversion durch den Identitätsmechanismus.
                wieder = reserve_finisher.lift_to_today(aktuell)
                self.assertEqual(wieder.read_text(encoding="utf-8"), erster)

            with patch.object(reserve_finisher, "POSTS_DIR", posts), \
                 patch.object(reserve_finisher, "today_prefix",
                              return_value="2026-11-06"):
                neu = reserve_finisher.lift_to_today(aktuell)
                text = neu.read_text(encoding="utf-8")
                self.assertIn('- "2026-11-01-thema"', text)
                self.assertIn('- "2026-11-05-thema"', text)
                self.assertEqual(text.count("faktenfrische_aliases:"), 1)


if __name__ == "__main__":
    unittest.main()
