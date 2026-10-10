#!/usr/bin/env python3
"""Regressionstest: manueller Offline-Messimport → Trichter (10.10.2026).

Die Messkette hat drei Brücken (Umami-API, Awin-API, manuelle Messstand-Datei).
Der Free-Plan von Umami lässt die API-Brücke dauerhaft ausfallen – ohne die
manuelle Brücke meldete `data/revenue_funnel.json` seit Bestehen nur `null`
und die Redaktion optimierte gegen eine Geisterzahl. Diese Fälle sind hier
dauerhaft verankert:

  1. leer ≠ 0 – fehlt die Messstand-Datei, darf nirgends eine Null stehen.
  2. Herkunft – jede Meta-Datei muss `import: offline` + Dateinamen tragen,
     sonst ist nicht mehr unterscheidbar, ob die API oder ein Mensch gemessen hat.
  3. Datenschutz – UTM-Splitting wird zusammengeführt, IP-/Mail-Zeilen fallen
     raus (Repo ist öffentlich).
  4. replace vs. merge – Dashboard-Export ersetzt, Teilimport summiert.
  5. Provisions-Tabelle – Monatsaggregate werden übernommen, Awin überlagert
     sie nie (eine Wahrheit), und sie werden keinem Artikel zugeschrieben.
  6. Misch-Stern – Raten aus Monats-Sicht müssen im Report als solche
     gekennzeichnet sein (sonst liest jemand 176 €/100 Besuche wie eine Woche).
"""
from __future__ import annotations

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


MESSSTAND = {
    "window": {"start": "2026-07-12", "ende": "2026-10-10", "tage": 90},
    "totals": {"aufrufe": 412, "besuche": 268},
    "views": [
        {"pfad": "/posts/x/", "aufrufe": 96, "besuche": 61},
        {"pfad": "/posts/x/?utm_source=newsletter", "aufrufe": 14, "besuche": 9},
        {"pfad": "/pillar/strom-sparen/", "aufrufe": 88, "besuche": 57},
        {"pfad": "frank@example.com", "aufrufe": 999, "besuche": 999},
        {"pfad": "10.0.0.7", "aufrufe": 999, "besuche": 999},
    ],
    "klicks": [{"event": "affiliate_click", "slug": "gas",
                "article": "posts/x/index.md", "pillar": "strom-sparen", "zahl": 11}],
    "ctas": [{"event": "cta_click", "slug": "home-strom", "article": "home", "zahl": 7}],
}


class Sandbox(unittest.TestCase):
    """Import in eine Wegwerf-Kopie der Datenpfade (echter Repo-Bestand bleibt).

    `offline_import.import_messstand()` nimmt `ziele` + `provisionen` als
    Überschreibung – genau das nutzen die Tests. So bleibt der echte
    Repo-Bestand (data/umami_*.json, data/provisionen/) unberührt, und die
    Tests sind in jeder Umgebung gleich (kein Abhängig-vom-Zufallsbestand).
    """

    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="offline-import-")
        d = lambda n: os.path.join(self.td, n)  # noqa: E731
        self.ziele = {"views": d("views.json"), "views_meta": d("views.meta.json"),
                      "clicks": d("clicks.json"), "clicks_meta": d("clicks.meta.json"),
                      "ctas": d("ctas.json"), "ctas_meta": d("ctas.meta.json"),
                      "provisionen_agg": d("provisionen_aggregat.json"),
                      "offline_meta": d("offline_import.meta.json")}
        self.prov = d("provisionen.csv")
        self.datei = d("messstand.json")
        with open(self.datei, "w", encoding="utf-8") as fh:
            json.dump(MESSSTAND, fh, ensure_ascii=False)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def imp(self, **kw):
        kw.setdefault("datei", self.datei)
        kw.setdefault("provisionen", self.prov)
        kw.setdefault("ziele", self.ziele)
        return oi.import_messstand(**kw)

    def read(self, key):
        with open(self.ziele[key], encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------- 1 + 2
    def test_leere_quelle_erfindet_nichts(self):
        res = self.imp(datei=os.path.join(self.td, "fehlt.json"))
        self.assertEqual(res["status"], "leer")
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p), f"{p} wurde trotz leerer Quelle geschrieben")

    def test_leere_datei_ist_keine_null(self):
        leer = os.path.join(self.td, "leer.json")
        with open(leer, "w", encoding="utf-8") as fh:
            fh.write("   \n")
        self.assertEqual(self.imp(datei=leer)["status"], "leer")

    def test_meta_traegt_herkunft_ohne_api_meta_anzufassen(self):
        self.imp()
        meta = self.read("offline_meta")
        self.assertEqual(meta["status"], "ok")
        self.assertEqual(meta["modus"], "ueberschreiben")
        self.assertTrue(meta["datei"].endswith("messstand.json"))
        self.assertEqual(meta["days"], 90)
        self.assertEqual(meta["window_start"], "2026-07-12")
        self.assertEqual(len(meta["written_files"]), 3)
        # Die Meta der API-Skripte gehört denen allein – sie darf hier nicht
        # entstehen, sonst verliert die Kette ihr Gedächtnis (falscher Alarm
        # „Import zu alt“, obwohl der API-Schritt nie gelaufen ist).
        self.assertFalse(os.path.exists(self.ziele["views_meta"]))
        self.assertFalse(os.path.exists(self.ziele["clicks_meta"]))

    # ------------------------------------------------------------- 3
    def test_utm_wird_nicht_zwei_seiten_und_datenmuell_faellt_raus(self):
        self.imp()
        views = self.read("views")
        pfade = [p["path"] for p in views["pages"]]
        self.assertEqual(pfade.count("/posts/x/"), 1, "UTM-Variante spaltet die Seite")
        x = next(p for p in views["pages"] if p["path"] == "/posts/x/")
        self.assertEqual(x["views"], 110)
        self.assertEqual(x["visits"], 70)
        self.assertNotIn("/", [p for p in pfade if "example.com" in p or "10.0.0" in p])
        self.assertFalse(any("@" in p or "10.0.0" in p for p in pfade),
                         "personenbezogene/Netz-Zeilen sind im Repo gelandet")

    def test_klicks_aggregieren_und_ctas_seit_trennt_sich(self):
        self.imp()
        clicks = self.read("clicks")
        ctas = self.read("ctas")
        self.assertEqual(sum(c["count"] for c in clicks), 11)
        self.assertEqual(sum(c["count"] for c in ctas), 7)
        self.assertTrue(all(c["event"] == "affiliate_click" for c in clicks))

    # ------------------------------------------------------------- 4
    def test_eigener_bestand_ersetzt_teilimport_summiert(self):
        self.imp()
        teil = os.path.join(self.td, "teil.json")
        json.dump({"views": [{"pfad": "/posts/y/", "aufrufe": 5, "besuche": 4}],
                   "totals": {"aufrufe": 5, "besuche": 4}},
                  open(teil, "w", encoding="utf-8"))
        self.imp(datei=teil)
        views = self.read("views")
        self.assertEqual([p["path"] for p in views["pages"]], ["/posts/y/"],
                         "eigener Vorgänger-Bestand muss ersetzt werden")
        self.imp(ueberschreiben=False)
        views = self.read("views")
        pfade = {p["path"]: p["views"] for p in views["pages"]}
        self.assertEqual(pfade["/posts/y/"], 5, "merge darf bestehende Seiten löschen")
        self.assertEqual(pfade["/posts/x/"], 110)
        self.assertEqual(views["totals"]["pageviews"], 417, "merge muss totals summieren")

    def test_api_bestand_bleibt_stehen(self):
        """Die manuelle Brücke darf einen frischen API-Lauf nie löschen."""
        with open(self.ziele["views_meta"], "w", encoding="utf-8") as fh:
            json.dump({"status": "ok", "written": str(rf.TODAY)}, fh)
        with open(self.ziele["views"], "w", encoding="utf-8") as fh:
            json.dump({"totals": {"pageviews": 500, "visits": 300},
                       "pages": [{"path": "/posts/api-seite/",
                                   "views": 500, "visits": 300}]}, fh)
        self.imp()
        views = self.read("views")
        pfade = {p["path"]: p["views"] for p in views["pages"]}
        self.assertEqual(pfade.get("/posts/api-seite/"), 500,
                         "API-Zeile wurde von der manuellen Datei überschrieben")
        self.assertEqual(pfade.get("/posts/x/"), 110)

    def test_unbekanntes_format_crashed_nicht(self):
        kaputt = os.path.join(self.td, "kaputt.json")
        with open(kaputt, "w", encoding="utf-8") as fh:
            fh.write('{"views": [1, null, "text"]}')
        self.assertEqual(self.imp(datei=kaputt)["status"], "leer")
        schief = os.path.join(self.td, "schief.csv")
        with open(schief, "w", encoding="utf-8") as fh:
            fh.write("url,pageViews\n/posts/a/,7\n")
        res = self.imp(datei=schief)
        self.assertEqual(res["seiten"], 1)

    # ------------------------------------------------------------- 5
    def test_provisionstabelle_aggregiert_nach_monat_und_partner(self):
        with open(self.prov, "w", encoding="utf-8") as fh:
            fh.write("monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n")
            fh.write("2026-08,CHECK24,2,0,33.00,A-08,\n")
            fh.write("2026-09,CHECK24,3,1,49.50,A-09,\n")
            fh.write("2026-09,Tarifcheck,1,0,18.00,B-09,\n")
            fh.write("falsch,CHECK24,9,9,9.00,x,\n")
        prov = oi.read_provisionen(self.prov)
        self.assertEqual(prov["letzter_monat"], "2026-09")
        self.assertEqual(prov["summe"]["abschluesse"], 6)
        self.assertEqual(prov["summe"]["provision_eur"], 100.5)
        self.assertEqual(len(prov["monate"]), 2)
        self.assertEqual(prov["monate"][1]["partner"], ["CHECK24", "Tarifcheck"])
        self.assertEqual(oi.read_provisionen(os.path.join(self.td, "none.csv")), {})

    def test_aggregat_wird_beim_import_geschrieben(self):
        with open(self.prov, "w", encoding="utf-8") as fh:
            fh.write("monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n")
            fh.write("2026-09,CHECK24,3,1,49.50,A-09,\n")
        self.imp()
        agg = self.read("provisionen_agg")
        self.assertEqual(agg["summe"]["provision_eur"], 49.5)
        # und der Trichter übernimmt sie, ohne sie einer Seite zuzuschreiben
        f = rf.compute({"totals": {"visits": 268, "pageviews": 412},
                        "pages": [{"path": "/posts/x/", "views": 110, "visits": 70}]},
                       [{"event": "affiliate_click", "slug": "gas",
                         "article": "posts/x/index.md", "count": 11}],
                       {}, [], {"/posts/x/"},
                       measured={"views": True, "clicks": True, "awin": False},
                       manual_prov=agg)
        self.assertEqual(f["provision"]["gesamt"], 49.5)
        self.assertEqual(f["provision"]["quelle"], "provisionen-tabelle")
        self.assertEqual(f["provision"]["zeitbezug"], "monat")
        self.assertIsNone(f["seiten"][0]["revenue"],
                          "Monats-Aggregat darf nicht auf eine Seite fallen")
        rep = rf.render(f, [], [], [], prov_monate=agg["monate"])
        self.assertIn("Abrechnungstabelle", rep)
        self.assertIn("* Diese drei Zeilen mischen zwei Zeitbezüge", rep,
                      "Misch-Stern fehlt – jemand läse die Rate als Wochenwert")

    def test_awin_ueberlagert_die_tabelle_nie(self):
        prov = {"monate": [{"monat": "2026-09", "partner": ["CHECK24"],
                            "abschluesse": 3, "stornos": 0, "provision_eur": 49.5}],
                "summe": {"monate": 1, "abschluesse": 3, "stornos": 0,
                          "provision_eur": 49.5}, "letzter_monat": "2026-09"}
        f = rf.compute({}, [], {"status_totals": {"approved": {"count": 2}},
                                "total_commission": 33.0, "total_paid": 33.0},
                       [], set(), measured={"views": False, "clicks": False, "awin": True},
                       manual_prov=prov)
        self.assertEqual(f["provision"]["gesamt"], 33.0)
        self.assertEqual(f["provision"]["quelle"], "awin")
        self.assertEqual(f["provision"]["zeitbezug"], "fenster")
        self.assertNotIn("* Diese drei Zeilen", rf.render(f, [], [], []))

    def test_monatsalter_der_buchfuehrung(self):
        self.assertEqual(rf._month_age(rf.TODAY.strftime("%Y-%m")), 0)
        self.assertEqual(rf._month_age("2026-01"), 9)
        for schlecht in ("2099-01", "quatsch", ""):
            with self.assertRaises((ValueError, AttributeError)):
                rf._month_age(schlecht)

    def test_dry_run_schreibt_nicht(self):
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p))
        res = self.imp(dry_run=True)
        self.assertEqual(res["status"], "ok")
        for p in self.ziele.values():
            self.assertFalse(os.path.exists(p), "dry-run hat geschrieben")
        self.assertEqual(self.imp(dry_run=True)["affiliate_klicks"], res["affiliate_klicks"])

    def test_status_in_sandbox(self):
        self.imp()
        st = oi.status(datei=self.datei, provisionen=self.prov, ziele=self.ziele)
        self.assertTrue(st["datei_da"])
        self.assertEqual(st["import_status"], "ok")
        self.assertEqual(st["seiten"], 2)
        self.assertEqual(st["affiliate_klicks"], 11)
        self.assertEqual(st["api_views_status"], "nie versucht",
                         "status() darf der API-Brücke nichts erfinden")


class TestSelbsttest(unittest.TestCase):
    def test_selftest_gruen(self):
        self.assertEqual(oi._selftest(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
