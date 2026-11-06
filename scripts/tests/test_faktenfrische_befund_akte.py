#!/usr/bin/env python3
"""Regressionen für den Schließweg offener Fachbefunde (#912, 03.11.2026).

Eingefroren wird die Kette, die am 02.11.2026 fehlte:

  * Der Befund ist an den TEXT gebunden – nicht an die Quellen. Eine
    automatische Quellenpflege darf keine Entscheidung öffnen (#912).
  * Eine Textänderung darf den Befund NICHT unschließbar machen. Genau das
    war der Zustand von 21 Ledger-Einträgen; eine Heilung vertiefte ihn.
  * `legacy-unbekannt` (Altbestand ohne Hash) ist am heutigen Text
    entscheidbar – sonst bleibt der Befund für immer offen.
  * Ohne Person und Begründung schreibt der Befehl nichts.
  * Die Akte nennt jede ID, den Fassungsstand, die Frist und den Befehl;
    sie entscheidet nichts.

Lauf: python3 -m unittest scripts.tests.test_faktenfrische_befund_akte
"""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische_befund_akte as akte  # noqa: E402
import faktenfrische_befund_ledger as ledger  # noqa: E402

TAG = dt.date(2026, 11, 3)
FINDING = {"typ": "luecke", "text": "BDEW-Durchschnittspreis ohne Beleg",
           "beleg": "https://www.bundesnetzagentur.de/x"}


def eintrag(slug="seite", fassung=None, text_hash=None, fid=None, alter=1):
    return {"id": fid or ledger.befund_id(slug, FINDING), "slug": slug,
            "fassung_sha256": fassung or ledger.body_hash(slug + "-pruef"),
            "text_sha256": text_hash or ledger.body_hash(slug + "-text"),
            **FINDING,
            "zuletzt_gesehen": (TAG - dt.timedelta(days=alter)).strftime(
                "%Y-%m-%d 10:00 UTC")}


class LedgerBindungTests(unittest.TestCase):
    """Zwei Hashes: Quellenpflege öffnet nicht, Textänderung schon."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.queue = self.dir / "queue.json"
        self.decisions = self.dir / "entscheidungen.yaml"
        self.entry = eintrag()
        self.queue.write_text(json.dumps({"fachbefunde": [self.entry]}),
                              encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _fassungen(self, text, pruef=None):
        """Echte SHA-256 der Aussageflächen – der Befehl prüft das."""
        h = ledger.body_hash(text)
        return {"seite": {"text": h, "pruef": pruef or h}}

    def test_quellenpflege_oeffnet_keine_entscheidung(self):
        """Der Lauf schreibt `quellen` – das darf kein Grün/Rot drehen."""
        ledger.entscheidung_anfuegen(self.entry["id"], "Redaktion",
                                     "Preisangabe geprüft und entfernt",
                                     queue_path=self.queue,
                                     decisions_path=self.decisions,
                                     fassungen=self._fassungen("t1"),
                                     heute=TAG)
        # Prüffassung ändert sich (neue Quellen), Text bleibt gleich.
        self.assertEqual(ledger.offene_befunde(
            self.queue, self.decisions,
            {"seite": {"text": ledger.body_hash("t1"), "pruef": "f" * 64}}), [])

    def test_textaenderung_macht_befund_nicht_unschliessbar(self):
        """Heilung ist der Normalfall – sie darf den Schließweg nicht kappen."""
        # Der Befund wurde an einem älteren Text erhoben.
        fassungen = self._fassungen("neuer-text")
        stand = ledger.befunde_mit_status(self.queue, self.decisions,
                                          fassungen, TAG)
        self.assertEqual(stand[0]["fassung_status"], "ueberholt")
        self.assertTrue(stand[0]["entscheidbar"])
        ledger.entscheidung_anfuegen(self.entry["id"], "Redaktion",
                                     "Aussage im heutigen Text belegt",
                                     queue_path=self.queue,
                                     decisions_path=self.decisions,
                                     fassungen=fassungen, heute=TAG)
        self.assertEqual(ledger.offene_befunde(self.queue, self.decisions,
                                               fassungen), [])

    def test_legacy_altbestand_ist_entscheidbar(self):
        alt = eintrag(fid="legacy01")
        alt["fassung_sha256"] = "legacy-unbekannt"
        alt["text_sha256"] = ""
        self.queue.write_text(json.dumps({"fachbefunde": [alt]}), encoding="utf-8")
        fassungen = self._fassungen("heute")
        stand = ledger.befunde_mit_status(self.queue, self.decisions,
                                          fassungen, TAG)
        self.assertEqual(stand[0]["fassung_status"], "ohne-fassung")
        ledger.entscheidung_anfuegen("legacy01", "Redaktion",
                                     "Altbefund am heutigen Text geprüft",
                                     queue_path=self.queue,
                                     decisions_path=self.decisions,
                                     fassungen=fassungen, heute=TAG)
        self.assertEqual(ledger.offene_befunde(self.queue, self.decisions,
                                               fassungen), [])

    def test_ohne_person_und_begruendung_keine_entscheidung(self):
        for von, begruendung in (("", "x" * 40), ("Redaktion", "ok")):
            with self.assertRaises(ledger.LedgerFehler):
                ledger.entscheidung_anfuegen(
                    self.entry["id"], von, begruendung,
                    queue_path=self.queue, decisions_path=self.decisions,
                    fassungen=self._fassungen("t1"), heute=TAG)
        self.assertFalse(self.decisions.exists(),
                         "Datei wurde trotz ungültiger Entscheidung geschrieben")

    def test_entscheidung_ist_an_die_gelesene_fassung_gebunden(self):
        ledger.entscheidung_anfuegen(self.entry["id"], "Redaktion",
                                     "Aussage im Text belegt und geprüft",
                                     queue_path=self.queue,
                                     decisions_path=self.decisions,
                                     fassungen=self._fassungen("t1"), heute=TAG)
        daten = yaml.safe_load(self.decisions.read_text(encoding="utf-8"))
        eintrag_ = daten["entscheidungen"][0]
        self.assertEqual(eintrag_["geprueft_fassung"], ledger.body_hash("t1"))
        self.assertEqual(eintrag_["befund_fassung"], self.entry["fassung_sha256"])
        self.assertEqual(eintrag_["entschieden_von"], "Redaktion")
        # Der Kommentarkopf der Schließakte bleibt erhalten.
        self.assertIn("Menschliche Schließakte", self.decisions.read_text(
            encoding="utf-8"))

    def test_wache_meldet_unlesbare_seite_statt_gruen(self):
        stand = ledger.wache(queue_path=self.queue,
                             decisions_path=self.decisions,
                             fassungen={"andere": {"text": "x" * 64,
                                                   "pruef": "x" * 64}},
                             stichtag=TAG)
        self.assertFalse(stand["gruen"])
        self.assertEqual(stand["nicht_entscheidbar"], 1)

    def test_falsches_ledger_ist_werkzeugfehler(self):
        self.queue.write_text("{kaputt", encoding="utf-8")
        with self.assertRaises(ledger.LedgerFehler):
            ledger.befunde_mit_status(self.queue, self.decisions, {}, TAG)


class AkteTests(unittest.TestCase):
    """Die Akte ist eine Arbeitsliste, keine Entscheidung."""

    def _befunde(self):
        return [
            dict(eintrag(slug="live-a", fid="aaaa"), fassung_status="ueberholt",
                 entscheidbar=True, alter_tage=9),
            dict(eintrag(slug="live-a", fid="aaab"), fassung_status="aktuell",
                 entscheidbar=True, alter_tage=2),
            dict(eintrag(slug="entwurf", fid="bbbb"), fassung_status="ohne-fassung",
                 entscheidbar=True, alter_tage=30),
        ]

    def test_akte_nennt_id_frist_fassung_und_befehl(self):
        live = {"live-a": {"urteil": "blockiert", "risikoklasse": "standard"}}
        zustand = akte.zustand_bauen(self._befunde(), live, frist_tage=14,
                                     eskalation_tage=21, stichtag=TAG)
        text = akte.akte_bauen(self._befunde(), live, zustand)
        self.assertIn("--entscheiden aaaa", text)
        self.assertIn("--von", text)
        self.assertIn("HEUTIGEN Text", text)
        self.assertIn("14 Tage", text)
        self.assertIn("**LIVE**", text)
        self.assertIn("1", text.split("Über der Frist")[1][:40])
        self.assertEqual(zustand["live_seiten"], 1)
        self.assertEqual(zustand["live_befunde"], 2)
        self.assertEqual(zustand["ueber_frist"], 1)
        self.assertEqual(zustand["in_eskalation"], 1)
        self.assertEqual(zustand["aeltester_tage"], 30)

    def test_akte_entscheidet_nichts(self):
        live = {}
        zustand = akte.zustand_bauen(self._befunde(), live, frist_tage=14,
                                     eskalation_tage=21, stichtag=TAG)
        text = akte.akte_bauen(self._befunde(), live, zustand)
        self.assertNotIn("entschieden von", text)
        self.assertIn("entscheidet nichts", text)
        self.assertIn("Ein neues `faktencheck`-Datum schließt **keinen** Befund",
                      text)

    def test_leere_akte_ist_gruen_und_sagt_warum(self):
        zustand = akte.zustand_bauen([], {}, frist_tage=14, eskalation_tage=21,
                                     stichtag=TAG)
        text = akte.akte_bauen([], {}, zustand)
        self.assertIn("Keine offenen Befunde", text)
        self.assertEqual(zustand["offen"], 0)
        self.assertIsNone(zustand["aeltester_tage"])


class LiveBestandTests(unittest.TestCase):
    """Der heutige Bestand ist gelesen, nicht behauptet."""

    def test_akte_im_repo_ist_auf_dem_stand_der_queue(self):
        """Eine veraltete Arbeitsliste führt zu Arbeit an falschen Texten.

        GEMESSEN AM EIGENEN STICHTAG (06.11.2026, #1097-Familie): Hier stand
        ein festes Datum (TAG = 2026-11-03). Damit blieb die Prüfung grün,
        während die Akte 11 Befunde auswies und der Ledger 19 kannte – ein
        Falsch-Grün, das genau die Arbeit an falschen Texten erlaubt, die
        der Test verhindern soll. Jetzt gilt: Die Akte belegt ihren eigenen
        Stand, und sie darf nicht älter sein als der jüngste Befund.
        """
        zustand = json.loads(
            (ROOT / "data" / "faktenfrische_befunde_state.json")
            .read_text(encoding="utf-8"))
        stichtag = dt.date.fromisoformat(str(zustand.get("stichtag") or TAG))
        befunde = ledger.befunde_mit_status(stichtag=stichtag)
        self.assertEqual(zustand["offen"], len(befunde))
        self.assertEqual(zustand["nicht_entscheidbar"], 0)
        # Frische: Der Stichtag der Akte liegt nicht vor dem jüngsten Beleg.
        juengster = max((str(b.get("zuletzt_gesehen") or "")[:10] for b in befunde),
                        default="")
        if juengster:
            self.assertLessEqual(juengster, stichtag.isoformat(),
                                 "die Akte ist älter als der jüngste Befund")
        self.assertTrue((ROOT / "BEFUND-AKTE.md").exists())
        self.assertIn("--entscheiden", (ROOT / "BEFUND-AKTE.md").read_text(
            encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
