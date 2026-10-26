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
