#!/usr/bin/env python3
"""Regressionstests der GSC-Abdeckungs-Zentrale (26.10.2026).

DER BEFUND, DEN DIESE DATEI EINFRIERT
-------------------------------------
Die Search Console meldete am 19.10.2026 **320 nicht indexierte** Seiten bei
117 indexierten – zusammengenommen 437 bekannte URLs. Der Build enthielt am
selben Tag 258 URLs, davon 99 indexierbar. Diese drei Zahlen standen nirgends
zusammen, weil der Abdeckungsbericht nur als CSV aus der Oberfläche kommt und
keine API hat. `scripts/gsc_abdeckung.py` holt sie zusammen und rechnet sie
gegeneinander.

Die Tests sichern vier Ebenen:

  1. LESEN – der Export wird tolerant gelesen (BOM, Semikolon, Tausenderpunkte,
     Anführungszeichen im Grund) und gegen sich selbst geprüft.
  2. NICHT-SCHREIBEN – ein widersprüchlicher Export wird nicht zum Artefakt.
     Die Lehre vom 21.10.2026: Ein Artefakt aus zwei Messungen ist keine Messung.
  3. GEGENRECHNEN – die Erwartung kommt aus dem Repo (noindex, Gateways,
     Weiterleitungen, Taxonomie), nicht aus einer gepflegten Liste. Neue
     noindex-Seiten oder ein neuer GSC-Grund werden erkannt.
  4. HERMETISCH – kein Netz, kein Hugo, kein Google-Konto; der Selbsttest darf
     den echten Verlauf nicht fortschreiben (Hausregel C15).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gsc_abdeckung as g  # noqa: E402

ABDECKUNG = ROOT / "data" / "gsc" / "abdeckung"
# Fester Betrachtungstag: Das Alter des Exports ist eine Eigenschaft des Laufs,
# kein Zufall des Kalenders. Tests, die von "heute" abhängen, sind Zeitbomben.
TAG = __import__("datetime").date(2026, 10, 20)


class ExportLesen(unittest.TestCase):
    """Der Parser muss die echten Exporte der Oberfläche aushalten."""

    def test_bom_anfuehrungszeichen_tausenderpunkt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Kritische Probleme.csv"
            p.write_text(
                '\ufeffGrund,Quelle,Validierung,Seiten\n'
                '"Durch ""noindex""-Tag ausgeschlossen",Website,Fehlgeschlagen,5\n'
                'Nicht gefunden (404),Website,Fehlgeschlagen,"1.234"\n',
                encoding="utf-8")
            zeilen = g.lese_csv(p)
            self.assertEqual(len(zeilen), 2)
            self.assertEqual(zeilen[0]["Grund"],
                             'Durch "noindex"-Tag ausgeschlossen')
            self.assertEqual(g.zahl(zeilen[1]["Seiten"]), 1234)

    def test_semikolon_und_leerzeilen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.csv"
            p.write_text("Datum;Nicht indexiert;Indexiert\n2026-10-19;320;117\n\n",
                         encoding="utf-8")
            zeilen = g.lese_csv(p)
            self.assertEqual(len(zeilen), 1)
            self.assertEqual(zeilen[0]["Datum"], "2026-10-19")

    def test_art_wird_am_kopf_erkannt_nicht_am_namen(self) -> None:
        self.assertEqual(g.erkenne_art([{"Grund": "", "Seiten": ""}]), "uebersicht")
        self.assertEqual(g.erkenne_art([{"Datum": ""}]), "verlauf")
        self.assertEqual(g.erkenne_art([{"URL": ""}]), "details")
        self.assertEqual(g.erkenne_art([{"Property": "", "Wert": ""}]), "metadaten")
        self.assertEqual(g.erkenne_art([]), "leer")

    def test_echter_export_ist_konsistent(self) -> None:
        """Der versionierte Export vom 19.10.2026 muss in sich stimmen."""
        ordner = ABDECKUNG / "export" / "2026-10-19"
        if not ordner.exists():
            self.skipTest("Export nicht versioniert")
        export = g.lade_export(ordner)
        hart = [b for b in g.pruefe_export(export) if b["schwere"] == "hart"]
        self.assertEqual(hart, [], f"Export widersprüchlich: {hart}")
        self.assertEqual(sum(e["seiten"] or 0 for e in export["uebersicht"]), 320)
        self.assertEqual(export["verlauf"][-1]["nicht_indexiert"], 320)
        self.assertEqual(export["verlauf"][-1]["indexiert"], 117)


class ExportPruefen(unittest.TestCase):
    def test_summe_gegen_diagramm_ist_hart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = g._fixture_export(Path(tmp) / "export", summe_abweichung=9)
            befunde = g.pruefe_export(g.lade_export(ordner))
            self.assertTrue(any(b["regel"] == "E8" and b["schwere"] == "hart"
                                for b in befunde))

    def test_widerspruechlicher_export_wird_nicht_geschrieben(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = g._fixture_export(Path(tmp) / "export", summe_abweichung=9)
            ziel = Path(tmp) / "ziel"
            ergebnis = g.importiere(ordner, ziel=ziel)
            self.assertEqual(ergebnis["status"], "ungueltig")
            self.assertFalse((ziel / "aktuell.json").exists())
            self.assertFalse((ziel / "verlauf.jsonl").exists())

    def test_fehlende_detail_liste_ist_hinweis_nicht_fehler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = g._fixture_export(Path(tmp) / "export")
            befunde = g.pruefe_export(g.lade_export(ordner))
            self.assertTrue(any(b["regel"] == "E10" and b["schwere"] == "hinweis"
                                for b in befunde))


class ImportUndVerlauf(unittest.TestCase):
    def test_import_schreibt_momentaufnahme_und_ist_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = g._fixture_export(Path(tmp) / "export")
            ziel = Path(tmp) / "ziel"
            erst = g.importiere(ordner, ziel=ziel)
            self.assertEqual(erst["status"], "ok")
            self.assertEqual(erst["datum"], "2026-10-19")
            self.assertTrue((ziel / "2026-10-19.json").exists())
            zweit = g.importiere(ordner, ziel=ziel)
            self.assertEqual(erst["snapshot"], zweit["snapshot"])
            zeilen = (ziel / "verlauf.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(zeilen), 1, "Verlauf darf nicht doppelt wachsen")

    def test_fehlende_momentaufnahme_ist_werkzeugfehler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                g.lade_snapshot(Path(tmp) / "nichts.json")

    def test_selbsttest_schreibt_nicht_in_den_echten_verlauf(self) -> None:
        """Hausregel C15: Prüfen prüft, es schreibt nicht."""
        echt = ABDECKUNG / "verlauf.jsonl"
        vorher = echt.read_text(encoding="utf-8") if echt.exists() else None
        with tempfile.TemporaryDirectory() as tmp:
            ordner = g._fixture_export(Path(tmp) / "export")
            g.importiere(ordner, ziel=Path(tmp) / "ziel")
        nachher = echt.read_text(encoding="utf-8") if echt.exists() else None
        self.assertEqual(vorher, nachher, "Ein Lauf in einem temporären Baum hat "
                                          "den echten Verlauf verändert")


class Gegenprobe(unittest.TestCase):
    """Die Erwartung kommt aus dem Repo – nicht aus einer gepflegten Liste."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_mini_repo_liefert_die_erwartungen(self) -> None:
        repo = g._mini_repo(self.tmp / "repo")
        wahrheit = g.repo_wahrheit(repo)
        self.assertEqual(wahrheit["anzahl_indexierbar"], 3)   # /, /posts/a/, /posts/b/
        self.assertEqual(wahrheit["anzahl_noindex"], 1)       # /suche/
        self.assertEqual(wahrheit["anzahl_gateways"], 2)       # /go/dsl/, /go/strom/
        self.assertEqual(wahrheit["anzahl_weiterleitungen"], 1)
        self.assertEqual(wahrheit["anzahl_entfallen"], 1)
        self.assertTrue(wahrheit["robots"]["go_gesperrt"])
        self.assertIn("/tags/sparen/", wahrheit["taxonomie_404"])

    def test_noindex_leck_ist_hart(self) -> None:
        repo = g._mini_repo(self.tmp / "repo")
        wahrheit = g.repo_wahrheit(repo)
        ordner = g._fixture_export(self.tmp / "export", noindex_seiten=7)
        a = g.auswerten(g.importiere(ordner, ziel=self.tmp / "ziel")["snapshot"], wahrheit,
                        heute=TAG)
        self.assertEqual(a["gate"]["status"], "rot")
        self.assertTrue(any(w["regel"] == "W2" for w in a["widersprueche"]))

    def test_unbekannter_grund_ist_hart(self) -> None:
        repo = g._mini_repo(self.tmp / "repo")
        wahrheit = g.repo_wahrheit(repo)
        ordner = g._fixture_export(self.tmp / "export",
                                   extra_grund="Vom Ausland blockiert")
        a = g.auswerten(g.importiere(ordner, ziel=self.tmp / "ziel")["snapshot"], wahrheit,
                        heute=TAG)
        self.assertEqual(a["gate"]["status"], "rot")
        self.assertTrue(any(w["regel"] == "W6" for w in a["widersprueche"]))

    def test_robots_sperre_ohne_gateway_ist_hart(self) -> None:
        """Eine Sperre auf Inhaltsseiten ist ein Indexierungsblocker."""
        repo = g._mini_repo(self.tmp / "repo")
        shutil.rmtree(repo / "static" / "go")
        wahrheit = g.repo_wahrheit(repo)
        ordner = g._fixture_export(self.tmp / "export")
        a = g.auswerten(g.importiere(ordner, ziel=self.tmp / "ziel")["snapshot"], wahrheit,
                        heute=TAG)
        self.assertEqual(wahrheit["anzahl_gateways"], 0)
        self.assertTrue(any(w["regel"] == "W3" for w in a["widersprueche"]))

    def test_echter_bestand_erklaert_die_noindex_zahl(self) -> None:
        """Die 5 noindex-Meldungen der Search Console == 5 Seiten im Inhalt."""
        wahrheit = g.repo_wahrheit()
        self.assertEqual(wahrheit["anzahl_noindex"], 5)
        self.assertEqual(len(wahrheit["noindex"]), 5)
        for url in wahrheit["noindex"]:
            self.assertTrue(url.startswith("/"), url)

    def test_weiterleitungskarte_liest_beide_quellen(self) -> None:
        wahrheit = g.repo_wahrheit()
        self.assertGreater(wahrheit["anzahl_weiterleitungen"], 100)
        self.assertGreater(wahrheit["anzahl_entfallen"], 0)
        for ziel in wahrheit["weiterleitungen"].values():
            self.assertTrue(ziel.startswith("/"), ziel)


class KennzahlenUndGate(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = g._mini_repo(self.tmp / "repo")
        self.wahrheit = g.repo_wahrheit(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_anomalie_und_delta(self) -> None:
        ordner = g._fixture_export(self.tmp / "export")
        snapshot = g.importiere(ordner, ziel=self.tmp / "ziel")["snapshot"]
        a = g.auswerten(snapshot, self.wahrheit,
                        verlauf_pfad=self.tmp / "ziel" / "verlauf.jsonl", heute=TAG)
        self.assertTrue(any(x["datum"] == "2026-10-17" for x in a["kennzahlen"]["anomalien"]))
        # Fixture-Verlauf: 2026-10-16 = 261, ab 2026-10-17 = 320 (drei Tage zurück).
        self.assertEqual(a["kennzahlen"]["delta_3_nicht_indexiert"], 320 - 261)

    def test_rueckschritt_im_gate(self) -> None:
        vorher = {"nicht_indexiert": 200, "quote_indexiert": 45.0, "summe_gruende": 200}
        kenn = {"nicht_indexiert": 300, "quote_indexiert": 31.0,
                "summe_gruende": 300, "bekannt": 400}
        ergebnis = g.gate({"kennzahlen": kenn, "widersprueche": []}, vorher)
        self.assertEqual(ergebnis["status"], "rot")
        self.assertTrue(any(f["regel"] in ("G2", "G3") for f in ergebnis["funde"]))

    def test_stabiler_verlauf_bleibt_gruen(self) -> None:
        vorher = {"nicht_indexiert": 320, "quote_indexiert": 26.8, "summe_gruende": 320}
        kenn = {"nicht_indexiert": 320, "quote_indexiert": 26.8,
                "summe_gruende": 320, "bekannt": 437}
        ergebnis = g.gate({"kennzahlen": kenn, "widersprueche": []}, vorher)
        self.assertEqual(ergebnis["status"], "gruen")

    def test_obergrenze_wird_nicht_als_exakte_erwartung_ausgegeben(self) -> None:
        ordner = g._fixture_export(self.tmp / "export")
        snapshot = g.importiere(ordner, ziel=self.tmp / "ziel")["snapshot"]
        a = g.auswerten(snapshot, self.wahrheit, heute=TAG)
        nach = {x["schluessel"]: x for x in a["gruende"]}
        self.assertEqual(nach["discovered_not_indexed"]["erwartung_art"], "hoechstens")
        self.assertEqual(nach["noindex"]["erwartung_art"], "genau")

    def test_massnahmen_sind_priorisiert_und_belegt(self) -> None:
        ordner = g._fixture_export(self.tmp / "export")
        snapshot = g.importiere(ordner, ziel=self.tmp / "ziel")["snapshot"]
        a = g.auswerten(snapshot, self.wahrheit, heute=TAG)
        self.assertTrue(a["massnahmen"])
        rang = {"P1": 0, "P2": 1, "P3": 2}
        folge = [rang[m["dringlichkeit"]] for m in a["massnahmen"]]
        self.assertEqual(folge, sorted(folge))
        for m in a["massnahmen"]:
            self.assertTrue(m["beleg"], f"{m['id']} ohne Beleg")
            self.assertIn(m["owner"], ("Mensch", "Automat", "Mensch (Export) + Automat",
                                       "Automat + Redaktion", "Redaktion",
                                       "Mensch + Automat", "Mensch (Export) + Automat"))


class Vorschlaege(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.wahrheit = g.repo_wahrheit(g._mini_repo(self.tmp / "repo"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_gleicher_slug_ist_ein_vorschlag(self) -> None:
        v = g.vorschlaege(["/posts/2026-10-01-a/"], self.wahrheit)[0]
        self.assertEqual(v["vorschlag"], "/posts/a/")
        self.assertEqual(v["sicherheit"], "hoch")

    def test_vorhandene_entscheidung_wird_nicht_ueberschrieben(self) -> None:
        v = g.vorschlaege(["/posts/alt-a/"], self.wahrheit)[0]
        self.assertEqual(v["weg"], "bereits entschieden")

    def test_bewusst_404_bleibt_bewusst_404(self) -> None:
        v = g.vorschlaege(["/posts/weg/"], self.wahrheit)[0]
        self.assertEqual(v["weg"], "bewusst 404")
        self.assertIsNone(v["vorschlag"])

    def test_fremde_url_ohne_deckung_bleibt_ohne_vorschlag(self) -> None:
        v = g.vorschlaege(["/posts/qqqqq-zzzzz/"], self.wahrheit)[0]
        self.assertIsNone(v["vorschlag"])


class Artefakte(unittest.TestCase):
    """Was versioniert ist, muss lesbar und in sich stimmig sein."""

    def test_snapshot_und_befund_sind_gueltiges_json(self) -> None:
        for name in ("2026-10-19.json", "aktuell.json"):
            pfad = ABDECKUNG / name
            if not pfad.exists():
                self.skipTest(f"{name} fehlt")
            daten = json.loads(pfad.read_text(encoding="utf-8"))
            self.assertEqual(daten["schema"], 1)
            self.assertEqual(daten["datum"], "2026-10-19")
            self.assertEqual(sum(e["seiten"] for e in daten["uebersicht"]), 320)

    def test_verlauf_ist_jsonl_und_append_only(self) -> None:
        pfad = ABDECKUNG / "verlauf.jsonl"
        if not pfad.exists():
            self.skipTest("Verlauf fehlt")
        daten = [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z]
        self.assertTrue(daten)
        self.assertEqual([d["datum"] for d in daten], sorted(d["datum"] for d in daten))

    def test_befund_nennt_quelle_und_gate(self) -> None:
        pfad = ABDECKUNG / "befund.json"
        if not pfad.exists():
            self.skipTest("Befund fehlt")
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        self.assertIn("kennzahlen", daten)
        self.assertIn(daten["gate"]["status"], ("gruen", "rot"))
        self.assertTrue(daten["quellen"]["export"])


class CockpitAnbindung(unittest.TestCase):
    """Der Befund muss im Cockpit sichtbar sein, ohne es zu verbiegen."""

    def test_zeile_und_quelle_erscheinen(self) -> None:
        import cockpit
        abdeckung = {"kennzahlen": {"stand_datum": "2026-10-19", "indexiert": 117,
                                    "bekannt": 437, "quote_indexiert": 26.8,
                                    "nicht_indexiert": 320},
                     "gruende": [{"offen": 193}],
                     "gate": {"status": "gruen"}}
        lvl, lines, quellen = cockpit.bucket_seo({"steps": {}}, abdeckung)
        self.assertTrue(any("Search Console (2026-10-19)" in z for z in lines))
        self.assertTrue(any("193" in z for z in lines))
        self.assertIn("data/gsc/abdeckung/befund.json", quellen)
        self.assertNotEqual(lvl, "gelb")

    def test_rotes_gate_bleibt_nicht_unsichtbar(self) -> None:
        import cockpit
        abdeckung = {"kennzahlen": {"stand_datum": "2026-10-19", "indexiert": 1,
                                    "bekannt": 2, "quote_indexiert": 50.0,
                                    "nicht_indexiert": 1},
                     "gruende": [], "gate": {"status": "rot"}}
        lvl, lines, _ = cockpit.bucket_seo({"steps": {}}, abdeckung)
        self.assertEqual(lvl, "gelb")
        self.assertTrue(any("Gate ROT" in z for z in lines))

    def test_ohne_befund_bleibt_alles_wie_bisher(self) -> None:
        import cockpit
        lvl, lines, quellen = cockpit.bucket_seo({"steps": {}})
        self.assertEqual(lines, ["in Ordnung"])
        self.assertNotIn("data/gsc/abdeckung/befund.json", quellen)


class Massnahmenplan(unittest.TestCase):
    """Die Ebenen, die den Maßnahmenplan tragen (M1–M9).

    Was hier eingefroren wird, ist nicht die Zahl von heute, sondern die
    Eigenschaft: Eine Triage darf getroffene Entscheidungen nicht erneut
    vorschlagen, ein Verlinkungsauftrag darf den Goldkorridor nicht sprengen,
    und ein gebrochener Vertrag muss das Tor rot machen.
    """

    def setUp(self) -> None:
        import datetime
        import tempfile

        self.dt = datetime
        self.tmp = Path(tempfile.mkdtemp())
        self.wahrheit = {
            "indexierbar": ["/posts/a/", "/posts/b/", "/posts/c/"],
            "noindex": ["/suche/"], "gateways": ["/go/x/"],
            "weiterleitungen": {"/posts/alt/": "/posts/a/"},
            "entfallen": {"/posts/weg/": "D"},
            "taxonomie_404": ["/tags/x/"], "anzahl_taxonomie": 1,
            "top_nicht_live": [{"url": "/posts/alt2/", "impressionen": 8, "position": 4.0}],
            "robots": {"go_gesperrt": True, "sperrt_go_gruppen": 3},
            "bau": {"gateway_liste": ["/go/x/"]},
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_triage_schlaegt_entschiedenes_nicht_neu_vor(self) -> None:
        t = g.triage([{"url": "/posts/alt/", "grund": "Nicht gefunden (404)"},
                      {"url": "/posts/weg/", "grund": "Nicht gefunden (404)"},
                      {"url": "/posts/a/", "grund": "Nicht gefunden (404)"}],
                     self.wahrheit, {})
        aktionen = {z["url"]: z["aktion"] for z in t["zeilen"]}
        self.assertIn("bereits entschieden", aktionen["/posts/alt/"])
        self.assertIn("bereits entschieden", aktionen["/posts/weg/"])
        self.assertIn("Bestand", aktionen["/posts/a/"])
        self.assertEqual(t["offen"], [])

    def test_triage_erkennt_nachfrage_als_p1(self) -> None:
        t = g.triage([{"url": "/posts/alt2/", "grund": "Nicht gefunden (404)"}],
                     self.wahrheit, {})
        zeile = t["zeilen"][0]
        self.assertEqual(zeile["prioritaet"], "P1")
        self.assertIn("Impressionen", zeile["beleg"])

    def test_triage_macht_aus_fehlendem_inlink_p1(self) -> None:
        t = g.triage([{"url": "/posts/neu/",
                       "grund": "Gefunden – zurzeit nicht indexiert"}],
                     self.wahrheit, {}, {"ohne_ein": ["/posts/neu/"]})
        self.assertEqual(t["zeilen"][0]["prioritaet"], "P1")
        self.assertIn("Inlink", t["zeilen"][0]["aktion"])

    def test_vertrag_meldet_noindex_ohne_begruendung(self) -> None:
        with mock.patch.dict(g.NOINDEX_VERTRAG, {}, clear=True):
            v = g.vertrag(self.wahrheit)
        self.assertEqual(v["status"], "rot")
        self.assertTrue(any(f["regel"] == "V1" for f in v["funde"]))

    def test_vertrag_meldet_veralteten_eintrag(self) -> None:
        with mock.patch.dict(g.NOINDEX_VERTRAG, {"/suche/": "ok", "/weg/": "alt"},
                             clear=True):
            v = g.vertrag(self.wahrheit)
        self.assertTrue(any(f["regel"] == "V2" for f in v["funde"]))

    def test_vertrag_prueft_gateway_sperre(self) -> None:
        wahrheit = dict(self.wahrheit)
        wahrheit["robots"] = {"go_gesperrt": False, "sperrt_go_gruppen": 0}
        with mock.patch.dict(g.NOINDEX_VERTRAG, {"/suche/": "ok"}, clear=True):
            v = g.vertrag(wahrheit)
        self.assertTrue(any(f["regel"] == "V4" for f in v["funde"]))

    def test_gebrochener_vertrag_macht_das_gate_rot(self) -> None:
        gate = g.gate({"kennzahlen": {}, "widersprueche": [],
                       "vertrag": {"funde": [{"regel": "V1", "schwere": "hart",
                                              "text": "Leck"}]}}, None)
        self.assertEqual(gate["status"], "rot")
        self.assertTrue(any(f["regel"] == "G6" for f in gate["funde"]))

    def test_kandidatenraum_ist_obergrenze_ohne_live_urls(self) -> None:
        k = g.kandidatenraum(self.wahrheit)
        # Dokumentierte Entscheidungen (Weiterleitung, bewusst 404) sind keine
        # offenen Kandidaten – sie stehen als "dokumentiert" in der Bilanz.
        self.assertNotIn("/posts/alt/", k["ohne_entscheidung"])
        self.assertIn("/posts/alt2/", k["ohne_entscheidung"])
        self.assertGreaterEqual(k["davon_dokumentiert"], 2)
        self.assertFalse([u for u in k["ohne_entscheidung"]
                          if u in set(self.wahrheit["indexierbar"])])

    def test_verlinkungsauftrag_haelt_den_goldkorridor(self) -> None:
        # Quelle mit schon neun Links darf nichts mehr bekommen – der Guard
        # zählt Vorkommen, nicht Ziele (Lehre vom 26.10.2026).
        posts = self.tmp / "content" / "posts"
        for slug in ("a", "b", "c", "voll"):
            (posts / slug).mkdir(parents=True)
        links = " ".join(f"[x](../../posts/{s}/)" for s in ("a", "b", "c"))
        for slug in ("a", "b", "c"):
            (posts / slug / "index.md").write_text(
                f"---\ntitle: {slug}\ndate: 2026-10-01\n---\n\nText.\n", encoding="utf-8")
        (posts / "voll" / "index.md").write_text(
            "---\ntitle: voll\ndate: 2026-10-01\n---\n\n"
            + " ".join(f"[{i}](../../posts/a/)" for i in range(9)) + "\n",
            encoding="utf-8")
        verlinkung = g.redaktionelle_links(self.tmp)
        auftrag = g.verlinkungs_auftrag(self.wahrheit, verlinkung, root=self.tmp)
        self.assertFalse([a for a in auftrag if a["quelle"] == "/posts/voll/"])
        self.assertTrue(links)

    def test_link_einfuegen_ist_idempotent(self) -> None:
        datei = self.tmp / "artikel.md"
        datei.write_text("Text.\n\n**Weiterlesen:** [A](/posts/a/)\n", encoding="utf-8")
        ok1, _ = g.link_einfuegen(datei, "/posts/b/", "B")
        ok2, meldung = g.link_einfuegen(datei, "/posts/b/", "B")
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertIn("bereits", meldung)
        self.assertEqual(datei.read_text(encoding="utf-8").count("/posts/b/"), 1)

    def test_anker_bleibt_ein_titelteil(self) -> None:
        anker = g.anker_kurz("Bankgebühren senken: 7 Schritte zum günstigeren Konto")
        self.assertEqual(anker, "Bankgebühren senken")
        self.assertLessEqual(len(g.anker_kurz("Ein wirklich sehr langer Titel mit "
                                              "vielen Wörtern über alles").split()), 6)

    def test_abnahme_nennt_naechsten_schritt(self) -> None:
        a = g.abnahme({"kennzahlen": {"export_alter_tage": 30},
                       "gate": {"status": "gruen"}, "gruende": []})
        offen = [x for x in a if x["status"] == "offen"]
        self.assertTrue(offen)
        self.assertTrue(all(x["naechster_schritt"] for x in offen))

    def test_ursachen_ohne_beleg_erfindet_keine_ursache(self) -> None:
        kenn = {"anomalien": [{"datum": "2026-10-17", "feld": "nicht_indexiert",
                               "delta": 59}]}
        u = g.ursachen(kenn, self.wahrheit)
        self.assertEqual(u[0]["bewertung"], "kein Beleg im Repo gefunden")
        self.assertEqual(u[0]["kandidaten"], [])


class GitBeleg(unittest.TestCase):
    """M7: Ein Sprung wird erklärt, nicht behauptet."""

    def test_ohne_historie_kein_beleg(self) -> None:
        import datetime
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            e = g.git_ereignisse(datetime.date(2026, 1, 1), datetime.date(2026, 1, 2),
                                 root=Path(tmp))
        self.assertFalse(e["verfuegbar"])
        self.assertTrue(e["grund"])

    def test_beleg_wird_als_beleg_gelesen(self) -> None:
        import datetime

        ereignisse = {"verfuegbar": True, "shallow": False, "commits": 1, "tage": {
            "2026-10-14": {"commits": 18, "content_dateien": 251, "draft_saldo": 32,
                           "draft_neu": 36, "draft_neu_posts": 36, "posts_saldo": 32,
                           "post_dateien": 89, "top": []}}}
        kenn = {"anomalien": [{"datum": "2026-10-17", "feld": "nicht_indexiert",
                               "delta": 59}]}
        u = g.ursachen(kenn, {}, ereignisse)
        self.assertIn("belegt", u[0]["bewertung"])
        self.assertEqual(u[0]["git"]["verzug_tage"], 3)
        self.assertEqual(u[0]["git"]["saldo"], 32)

    def test_ohne_fenster_bleibt_es_eine_hypothese(self) -> None:
        ereignisse = {"verfuegbar": True, "shallow": False, "commits": 1, "tage": {
            "2026-09-01": {"commits": 1, "content_dateien": 2, "draft_saldo": 3,
                           "draft_neu": 3, "draft_neu_posts": 3, "posts_saldo": 3,
                           "post_dateien": 2, "top": []}}}
        kenn = {"anomalien": [{"datum": "2026-10-17", "feld": "nicht_indexiert",
                               "delta": 59}]}
        self.assertIsNone(g.ursachen(kenn, {}, ereignisse)[0]["git"])


class Hermetik(unittest.TestCase):
    def test_index_gate_base_gilt_nur_fuer_dieses_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fremd = Path(tmp) / "repo"
            (fremd / "public").mkdir(parents=True)
            with mock.patch.dict(os.environ, {"INDEX_GATE_BASE": "/gibt/es/nicht"}):
                self.assertEqual(g._oeffentlich(ROOT), ROOT / "public")
            with mock.patch.dict(os.environ, {"INDEX_GATE_BASE": str(fremd / "public")}):
                self.assertEqual(g._oeffentlich(ROOT), fremd / "public")
                self.assertEqual(g._oeffentlich(fremd), fremd / "public")

    def test_kein_netzzugriff_import(self) -> None:
        """Das Modul darf nichts Netzendes importieren (offline lauffähig)."""
        quelle = (ROOT / "scripts" / "gsc_abdeckung.py").read_text(encoding="utf-8")
        for verboten in ("urllib.request", "http.client", "requests", "socket"):
            self.assertNotIn(f"import {verboten}", quelle,
                             f"{verboten} macht den Befund nicht reproduzierbar")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TriageAusDateien(unittest.TestCase):
    """M1: Aus der CSV der Oberfläche wird eine Arbeitsliste – offline geprüft."""

    def test_detail_ordner_wird_gelesen_und_triagiert(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "Nicht gefunden (404).csv").write_text(
                "URL,Zuletzt gecrawlt\n"
                "https://franksfinanzcheck.de/posts/alt/,2026-10-18\n"
                "https://franksfinanzcheck.de/posts/weg/,2026-10-17\n",
                encoding="utf-8")
            export = g.lade_export(ordner)
            self.assertTrue(export["details"])
            wahrheit = {
                "indexierbar": [], "noindex": [], "gateways": [],
                "weiterleitungen": {"/posts/alt/": "/posts/a/"}, "entfallen": {},
                "taxonomie_404": [], "anzahl_taxonomie": 0,
                "top_nicht_live": [], "robots": {"go_gesperrt": False,
                                                 "sperrt_go_gruppen": 0},
            }
            eintraege = [{"url": d["url"], "grund": Path(d["datei"]).stem}
                         for d in export["details"]]
            t = g.triage(eintraege, wahrheit, {})
            self.assertEqual(t["anzahl"], 2)
            self.assertTrue(all(z["prioritaet"] in ("P0", "P1", "P2", "P3")
                                for z in t["zeilen"]))
            self.assertIn("Weiterleitung", t["zeilen"][0]["aktion"])

    def test_detail_alter_wird_aus_stand_gelesen(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(g, "DETAILS", Path(tmp)):
                (Path(tmp) / ".stand").write_text("2026-10-01\n", encoding="utf-8")
                stand = g.detail_stand(g.dt.date(2026, 10, 15))
        self.assertEqual(stand["stand"], "2026-10-01")
        self.assertEqual(stand["alter_tage"], 14)


class EntscheidungenUndFristen(unittest.TestCase):
    """Der Kreislauf: Vorschlag → Entscheidung → Frist → Wirkungsprüfung.

    Der Befund vom 26.10.2026 war nicht „zu wenige Aufgaben", sondern dass
    eine Aufgabe nach dem ersten Bericht verschwand. Diese Tests frieren ein,
    dass eine Entscheidung eine Frist hat, dass eine Frist abläuft und dass
    nach Ablauf der lastmod der Seite entscheidet – nicht das Gefühl.
    """

    def setUp(self) -> None:
        import datetime
        import tempfile

        self.dt = datetime
        self.tmp = Path(tempfile.mkdtemp())
        self.register = self.tmp / "entscheidungen.yaml"
        self.wahrheit = {
            "indexierbar": ["/posts/a/"], "noindex": [], "gateways": [],
            "weiterleitungen": {}, "entfallen": {}, "taxonomie_404": [],
            "anzahl_taxonomie": 0, "top_nicht_live": [],
            "robots": {"go_gesperrt": False, "sperrt_go_gruppen": 0},
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _entscheiden(self, url: str = "/posts/a/", faellig: str = "2026-11-25",
                     am: str = "2026-10-26", root: Path | None = None) -> dict:
        return g.entscheidung_eintragen(
            url, "Rolle festlegen", "Cluster ohne Eintrag",
            wiedervorlage=faellig, heute=self.dt.date.fromisoformat(am),
            pfad=self.register)

    def _triage(self, heute: str, root: Path | None = None) -> dict:
        return g.triage([{"url": "/posts/a/", "grund": "Nicht gefunden (404)"}],
                        self.wahrheit, {}, {"ohne_ein": []},
                        heute=self.dt.date.fromisoformat(heute),
                        verlauf=[], register=g.entscheidungen(self.register),
                        root=root or self.tmp / "leer")

    def test_entscheidung_haelt_frist_und_ersatz(self) -> None:
        self._entscheiden()
        self._entscheiden(am="2026-10-27")
        eintraege = g.entscheidungen(self.register)
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege["/posts/a/"]["am"], "2026-10-27")
        self.assertEqual(eintraege["/posts/a/"]["wiedervorlage"], "2026-11-25")
        self.assertEqual(eintraege["/posts/a/"]["erwartung"], "indexiert")

    def test_ohne_frist_kein_eintrag(self) -> None:
        with self.assertRaises(ValueError):
            self._entscheiden(faellig="25.11.2026")

    def test_standardfrist_ist_die_sla(self) -> None:
        werte = g.entscheidung_eintragen(
            "/posts/a/", "Rolle festlegen", heute=self.dt.date(2026, 10, 26),
            pfad=self.register)
        self.assertEqual(werte["wiedervorlage"], "2026-11-25")

    def test_vor_der_frist_ist_die_sache_entschieden(self) -> None:
        self._entscheiden()
        t = self._triage("2026-11-01")
        self.assertEqual(t["offen"], [])
        self.assertIn("Wiedervorlage", t["zeilen"][0]["aktion"])

    def test_frist_abgelaufen_und_nichts_geaendert_ist_p1(self) -> None:
        self._entscheiden()
        t = self._triage("2026-12-02")
        zeile = t["offen"][0]
        self.assertEqual(zeile["prioritaet"], "P1")
        self.assertIn("umsetzen", zeile["aktion"])

    def test_frist_abgelaufen_und_geaendert_ist_p2(self) -> None:
        self._entscheiden()
        repo = self.tmp / "repo"
        (repo / "content" / "posts" / "a").mkdir(parents=True)
        (repo / "content" / "posts" / "a" / "index.md").write_text(
            '---\ntitle: "A"\nlastmod: 2026-12-01\n---\n\nText\n', encoding="utf-8")
        t = self._triage("2026-12-02", root=repo)
        self.assertEqual(t["offen"][0]["prioritaet"], "P2")
        self.assertIn("erneut anfragen", t["offen"][0]["aktion"])

    def test_nicht_mehr_gemeldet_belegt_wirkung(self) -> None:
        self._entscheiden()
        t = g.triage([{"url": "/posts/anders/", "grund": "Nicht gefunden (404)"}],
                     self.wahrheit, {}, {"ohne_ein": []},
                     heute=self.dt.date(2026, 12, 2), verlauf=[],
                     register=g.entscheidungen(self.register),
                     root=self.tmp / "leer")
        self.assertEqual(t["wirkung_belegt"], ["/posts/a/"])

    def test_ueberfaellige_aufgabe_steigt_eine_stufe(self) -> None:
        wahrheit = dict(self.wahrheit)
        t = g.triage([{"url": "/posts/a/",
                       "grund": "Gecrawlt – zurzeit nicht indexiert"}],
                     wahrheit, {}, {"ohne_ein": []},
                     heute=self.dt.date(2026, 10, 26),
                     verlauf=[{"datum": "2026-09-01", "url": "/posts/a/",
                               "prioritaet": "P2"}],
                     register={}, root=self.tmp / "leer")
        self.assertEqual(t["eskaliert"], ["/posts/a/"])
        self.assertEqual(t["zeilen"][0]["prioritaet"], "P1")

    def test_verlauf_zaehlt_einmal_je_url_und_tag(self) -> None:
        pfad = self.tmp / "verlauf.jsonl"
        zeilen = [{"url": "/posts/a/", "prioritaet": "P2", "aktion": "x"},
                  {"url": "/posts/b/", "prioritaet": "P3", "aktion": "y"}]
        self.assertEqual(g.verlauf_schreiben(zeilen, self.dt.date(2026, 10, 26), pfad), 1)
        self.assertEqual(g.verlauf_schreiben(zeilen, self.dt.date(2026, 10, 26), pfad), 0)
        self.assertEqual(len(g.verlauf_laden(pfad)), 1)


class TitelUeberschneidung(unittest.TestCase):
    """Kannibalisierung wird am Titel gemessen, nicht am Slug.

    Am 26.10.2026 meldete die Triage „2 ähnliche Titel", weil zwei Artikel
    „…-schritt-fuer-schritt" heißen. Das war ein Fehlalarm aus dem Slug –
    und ein Fehlalarm in einem Bericht ist teurer als eine Lücke.
    """

    def test_fuellwoerter_zaehlen_nicht(self) -> None:
        mass = g.titel_ueberschneidung(
            "Dein Weg zu geringeren Monatskosten: Schritt für Schritt",
            "ETF-Sparplan starten: Schritt für Schritt zum Investieren")
        self.assertEqual(mass["mass"], 0.0)
        self.assertEqual(mass["gemeinsam"], [])

    def test_echte_ueberschneidung_wird_erkannt(self) -> None:
        mass = g.titel_ueberschneidung("Haushaltsbuch führen: App oder Excel",
                                       "Haushaltsbuch führen mit Excel")
        self.assertEqual(mass["mass"], 1.0)
        self.assertIn("haushaltsbuch", mass["gemeinsam"])

    def test_themenfeld_wird_dem_cluster_zugeordnet(self) -> None:
        treffer = g.cluster_fuer_pillar("frugalismus")
        self.assertIsNotNone(treffer)
        self.assertEqual(treffer["cluster"], "K3-frugalismus")
        self.assertIsNone(g.cluster_fuer_pillar("gibt-es-nicht"))
