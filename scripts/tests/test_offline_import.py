#!/usr/bin/env python3
"""Regressionstest: manueller Provisions-Import → Trichter.

Die Provision ist die einzige Zahl der Messkette, die kein Automat liefert: Sie
steht in den Abrechnungen der Partner. Ohne den Import meldete
`data/revenue_funnel.json` seit Bestehen nur `null` und die Redaktion
optimierte gegen eine Geisterzahl. Diese Fälle sind hier dauerhaft verankert:

  1. leer ≠ 0 – fehlt die Tabelle (oder hat sie nur die Kopfzeile), darf
     nirgends eine Null stehen und nichts geschrieben werden.
  2. Herkunft – die Meta-Datei trägt Stand, Status und Zahl der Monate, sonst
     ist nicht mehr nachvollziehbar, woher die Zahlen kommen.
  3. Datenschutz – ins öffentliche Aggregat gehören nur Summen je Monat und
     Partner: keine Abrechnungsnummern, keine Notizen.
  4. Provisions-Tabelle – Monatsaggregate werden übernommen (einzige Wahrheit
     für Provision), und sie werden keinem Artikel zugeschrieben.
  5. Misch-Stern – Raten aus Monats-Sicht müssen im Report als solche
     gekennzeichnet sein (sonst liest jemand eine Monatsrate wie eine Woche).
  6. Abwesenheit – der Import kennt keinen Messstand-/Dashboard-Export mehr;
     die Dashboard-Export-Brücke ist entfernt und kommt nicht zurück
     (fremdmessung_sperre.py).
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


oi = _load("offline_import", os.path.join(SCRIPTS, "offline_import.py"))
rf = _load("revenue_funnel_regress", os.path.join(SCRIPTS, "revenue_funnel.py"))

HEUTE = datetime.date.today()


def monat(rueckwaerts=0):
    """JJJJ-MM `rueckwaerts` Monate vor dem aktuellen Monat – Fixtures dürfen
    nie auf einen Kalender geheftet sein (scripts/selftest_clock.py)."""
    m = HEUTE.year * 12 + (HEUTE.month - 1) - rueckwaerts
    return f"{m // 12:04d}-{m % 12 + 1:02d}"


MONAT_A, MONAT_B = monat(2), monat(1)          # zwei aufeinanderfolgende Monate
KOPF = "monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n"


class Sandbox(unittest.TestCase):
    """Import in eine Wegwerf-Kopie der Datenpfade (echter Repo-Bestand bleibt).

    `offline_import.import_provisionen()` nimmt `ziele` + `provisionen` als
    Überschreibung – genau das nutzen die Tests. So bleibt der echte
    Repo-Bestand (data/provisionen/, data/provisionen_aggregat.json) unberührt,
    und die Tests sind in jeder Umgebung gleich.
    """

    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="offline-import-")
        d = lambda n: os.path.join(self.td, n)  # noqa: E731
        self.ziele = {"provisionen_agg": d("provisionen_aggregat.json"),
                      "offline_meta": d("offline_import.meta.json")}
        self.prov = d("provisionen.csv")

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def tabelle(self, *zeilen):
        with open(self.prov, "w", encoding="utf-8") as fh:
            fh.write(KOPF)
            for z in zeilen:
                fh.write(z + "\n")

    def imp(self, **kw):
        kw.setdefault("provisionen", self.prov)
        kw.setdefault("ziele", self.ziele)
        return oi.import_provisionen(**kw)

    def read(self, key):
        with open(self.ziele[key], encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------- 1
    def test_fehlende_tabelle_erfindet_nichts(self):
        res = self.imp()
        self.assertEqual(res["status"], "leer")
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p), f"{p} wurde trotz fehlender Tabelle geschrieben")

    def test_tabelle_nur_mit_kopfzeile_ist_keine_null(self):
        self.tabelle()
        self.assertEqual(self.imp()["status"], "leer")
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p))

    def test_kaputte_tabelle_crashed_nicht(self):
        with open(self.prov, "w", encoding="utf-8") as fh:
            fh.write("das,ist\nkein,schema\n")
        self.assertEqual(self.imp()["status"], "leer")
        with open(self.prov, "wb") as fh:
            fh.write(b"\xff\xfe\x00 kein utf-8")
        self.assertEqual(self.imp()["status"], "leer")

    # ------------------------------------------------------------- 2
    def test_meta_traegt_herkunft(self):
        self.tabelle(f"{MONAT_B},CHECK24,3,1,49.50,A-{MONAT_B[-2:]},")
        self.imp()
        meta = self.read("offline_meta")
        self.assertEqual(meta["status"], "ok")
        self.assertEqual(meta["written"], HEUTE.isoformat())
        self.assertEqual(meta["provisionen_monate"], 1)
        self.assertEqual(meta["letzter_monat"], MONAT_B)
        self.assertEqual(len(meta["written_files"]), 1)

    # ------------------------------------------------------------- 3
    def test_aggregat_enthaelt_keine_abrechnungsdetails(self):
        self.tabelle(f"{MONAT_B},CHECK24,3,1,49.50,GEHEIME-REF-4711,Notiz mit Details")
        self.imp()
        roh = json.dumps(self.read("provisionen_agg"))
        for verboten in ("GEHEIME-REF-4711", "Notiz mit Details", "abrechnung_ref"):
            self.assertNotIn(verboten, roh, f"{verboten} gehört nicht ins öffentliche Aggregat")

    # ------------------------------------------------------------- 4
    def test_provisionstabelle_aggregiert_nach_monat_und_partner(self):
        self.tabelle(f"{MONAT_A},CHECK24,2,0,33.00,A-{MONAT_A[-2:]},",
                     f"{MONAT_B},CHECK24,3,1,49.50,A-{MONAT_B[-2:]},",
                     f"{MONAT_B},Tarifcheck,1,0,18.00,B-{MONAT_B[-2:]},",
                     "falsch,CHECK24,9,9,9.00,x,")
        prov = oi.read_provisionen(self.prov)
        self.assertEqual(prov["letzter_monat"], MONAT_B)
        self.assertEqual(prov["summe"]["abschluesse"], 6)
        self.assertEqual(prov["summe"]["provision_eur"], 100.5)
        self.assertEqual(len(prov["monate"]), 2)
        self.assertEqual(prov["monate"][1]["partner"], ["CHECK24", "Tarifcheck"])
        self.assertEqual(oi.read_provisionen(os.path.join(self.td, "none.csv")), {})

    def test_aggregat_wird_beim_import_geschrieben_und_vom_trichter_gelesen(self):
        self.tabelle(f"{MONAT_B},CHECK24,3,1,49.50,A-{MONAT_B[-2:]},")
        self.imp()
        agg = self.read("provisionen_agg")
        self.assertEqual(agg["summe"]["provision_eur"], 49.5)
        # und der Trichter übernimmt sie, ohne sie einer Seite zuzuschreiben
        f = rf.compute([{"event": "affiliate_click", "slug": "gas",
                         "article": "posts/x/index.md", "count": 11}],
                       {"/posts/x/"}, measured={"clicks": True}, manual_prov=agg)
        self.assertEqual(f["provision"]["gesamt"], 49.5)
        self.assertEqual(f["provision"]["quelle"], "provisionen-tabelle")
        self.assertEqual(f["provision"]["zeitbezug"], "monat")
        self.assertNotIn("revenue", f["seiten"][0],
                         "Monats-Aggregat darf nicht auf eine Seite fallen")
        # 5) Misch-Stern: Klicks (Zähler) und Provision (Monat) mischen zwei Bezüge
        rep = rf.render(f, [], [], [], prov_monate=agg["monate"])
        self.assertIn("Abrechnungstabelle", rep)
        self.assertIn("_* Diese beiden Zeilen mischen zwei Zeitbezüge", rep,
                      "Misch-Stern fehlt – jemand läse die Rate als Wochenwert")

    def test_monatsalter_der_buchfuehrung(self):
        self.assertEqual(rf._month_age(rf.TODAY.strftime("%Y-%m")), 0)
        self.assertEqual(rf._month_age(monat(9)), 9)
        self.assertEqual(rf._month_age(monat(0)), 0)
        n = HEUTE.year * 12 + HEUTE.month      # der Monat nach heute = Zukunft
        for schlecht in (f"{n // 12:04d}-{n % 12 + 1:02d}", "quatsch", ""):
            with self.assertRaises((ValueError, AttributeError)):
                rf._month_age(schlecht)

    def test_dry_run_schreibt_nicht(self):
        self.tabelle(f"{MONAT_B},CHECK24,3,1,49.50,A-{MONAT_B[-2:]},")
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p))
        res = self.imp(dry_run=True)
        self.assertEqual(res["status"], "ok")
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p), "dry-run hat geschrieben")

    def test_status_in_sandbox(self):
        self.tabelle(f"{MONAT_B},CHECK24,3,1,49.50,A-{MONAT_B[-2:]},")
        self.imp()
        st = oi.status(provisionen=self.prov, ziele=self.ziele,
                       klick_meta=os.path.join(self.td, "keine.meta.json"))
        self.assertTrue(st["tabelle_da"])
        self.assertEqual(st["import_status"], "ok")
        self.assertEqual(st["provision_monate"], 1)
        self.assertEqual(st["klickzaehler_status"], "nie versucht",
                         "status() darf dem Klickzähler nichts erfinden")

    # ------------------------------------------------------------- 6
    def test_import_kennt_keinen_messstand_export_mehr(self):
        for name in ("import_messstand", "from_json", "from_csv", "merge_views",
                     "merge_rows", "norm_path", "STANDARD_DATEI", "VIEWS", "CLICKS", "CTAS"):
            self.assertFalse(hasattr(oi, name),
                             f"{name}: die Dashboard-Export-Brücke ist entfernt und kommt nicht zurück")

    def test_vorlage_wird_angelegt_ohne_bestand_zu_ueberschreiben(self):
        vorlage = os.path.join(self.td, "vorlage.csv")
        with open(vorlage, "w", encoding="utf-8") as fh:
            fh.write(KOPF)
        ziel = os.path.join(self.td, "neu", "provisionen.csv")
        self.assertEqual(oi.anlegen(ziel=ziel, vorlage=vorlage), 0)
        with open(ziel, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), KOPF)
        with open(ziel, "a", encoding="utf-8") as fh:
            fh.write(f"{MONAT_B},CHECK24,1,0,5.00,x,\n")
        self.assertEqual(oi.anlegen(ziel=ziel, vorlage=vorlage), 1)
        with open(ziel, encoding="utf-8") as fh:
            self.assertIn("CHECK24", fh.read(), "bestehende Tabelle wurde überschrieben")
        self.assertEqual(oi.anlegen(ziel=ziel, vorlage=vorlage, force=True), 0)

    def test_echte_vorlage_im_repo_ist_nur_die_kopfzeile(self):
        with open(oi.VORLAGE, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), KOPF, "die Vorlage darf keine echten Daten tragen")


class TestSelbsttest(unittest.TestCase):
    def test_selftest_gruen(self):
        self.assertEqual(oi._selftest(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
