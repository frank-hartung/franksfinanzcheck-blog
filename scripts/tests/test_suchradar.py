#!/usr/bin/env python3
"""Tests für das Suchradar (scripts/suchradar.py + scripts/serp_anbieter.py).

Hintergrund: Seit dem 12.10.2026 erfasst das Suchradar Suchergebnisse ohne
API-Anbindung – ohne Schlüssel, ohne Konto, ohne Kosten. Weil es fremde
Server abfragt und Befunde erzeugt, an denen redaktionelle Entscheidungen
hängen, nageln diese Tests die Betriebsversprechen fest:

  1. Budget:  kein Lauf reißt das Tageslimit – auch nicht im Fehlerfall.
  2. Cache:   ein Nachlauf am selben Tag kostet kein Abrufbudget.
  3. Kette:   ein ausgefallener Anbieter ist eine Umschaltung, kein Abbruch.
  4. Stille Leere: liefert niemand etwas, ist der Lauf rot (Exit 3).
  5. Probelauf: `--dry-run` schreibt weder Zustand noch Bericht.
  6. Isolation: Tests berühren data/suchradar/ nicht.
  7. Parser:  Anzeigen fallen raus, Umleitungen werden ausgepackt,
              Titel sind keine Adressen.
  8. Sperre:  bezahlte Anbieter bleiben ohne Freigabe unbrauchbar.

Läuft deterministisch ohne Netz:
    python3 -m unittest scripts.tests.test_suchradar
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import serp_anbieter as sa      # noqa: E402
import serp_html as sh          # noqa: E402
import suchradar as sr          # noqa: E402
from url_host import ist_host_oder_subdomain  # noqa: E402

PROBEN = Path(__file__).resolve().parent / "serp_proben"


def probe(name: str) -> str:
    return (PROBEN / name).read_text(encoding="utf-8")


def treffer(url: str, rang: int, domaene: str = "", titel: str = "",
            merkmale: list | None = None, anfrage: str = "strom") -> dict:
    """Ein Treffer im Normalformat – für die Auswertungstests."""
    return sa.normalisieren(
        anfrage=anfrage, url=url, titel=titel or f"Titel {rang}",
        beschreibung="Beschreibung", rang=rang, anbieter="mojeek",
        merkmale=merkmale or [])


class SandboxFall(unittest.TestCase):
    """Lenkt alle Schreibpfade des Suchradars in ein Wegwerfverzeichnis.

    Ohne diese Umlenkung würde jeder Testlauf data/suchradar/ der
    Arbeitskopie beschreiben – und ein Test, der Produktionszustand
    verändert, ist kein Test mehr, sondern ein Seiteneffekt. Genau diese
    Klasse von Fehler prüft das Repo unter C27.
    """

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="suchradar-test-"))
        self._pfade = {
            "ZUSTAND": sr.ZUSTAND,
            "CACHE_VERZEICHNIS": sr.CACHE_VERZEICHNIS,
            "QUOTEN_DATEI": sr.QUOTEN_DATEI,
            "INSTANZEN_DATEI": sr.INSTANZEN_DATEI,
            "VERLAUF_DATEI": sr.VERLAUF_DATEI,
            "RANKING_DATEI": sr.RANKING_DATEI,
            "RANKING_VERLAUF": sr.RANKING_VERLAUF,
            "WETTBEWERB_DATEI": sr.WETTBEWERB_DATEI,
            "ERGEBNIS_DATEI": sr.ERGEBNIS_DATEI,
            "COCKPIT": sr.COCKPIT,
            "KONFIG": sr.KONFIG,
        }
        sr.ZUSTAND = self.temp / "zustand"
        sr.CACHE_VERZEICHNIS = sr.ZUSTAND / "cache"
        sr.QUOTEN_DATEI = sr.ZUSTAND / "quota.json"
        sr.INSTANZEN_DATEI = sr.ZUSTAND / "instanzen.json"
        sr.VERLAUF_DATEI = sr.ZUSTAND / "verlauf.jsonl"
        sr.RANKING_DATEI = sr.ZUSTAND / "rankings.json"
        sr.RANKING_VERLAUF = sr.ZUSTAND / "rankings.jsonl"
        sr.WETTBEWERB_DATEI = sr.ZUSTAND / "wettbewerb.json"
        sr.ERGEBNIS_DATEI = sr.ZUSTAND / "letzte_ergebnisse.json"
        sr.COCKPIT = self.temp / "SUCHRADAR-RADAR.md"
        sr.KONFIG = self.temp / "suchradar.yaml"

    def tearDown(self):
        for name, wert in self._pfade.items():
            setattr(sr, name, wert)
        shutil.rmtree(self.temp, ignore_errors=True)

    def konfig(self, **uebersteuerung) -> dict:
        return {**sr.VORGABEN, **uebersteuerung}


# ====================================================================
#  KONFIGURATION
# ====================================================================
class TestKonfiguration(SandboxFall):

    def test_fehlende_ssot_faellt_auf_vorgaben_zurueck(self):
        konfig = sr.lade_konfiguration(self.temp / "gibt-es-nicht.yaml")
        self.assertEqual(konfig["eigene_domaene"], "franksfinanzcheck.de")
        self.assertIn("fehlt", konfig.get("_hinweis", ""))

    def test_kaputte_ssot_faellt_auf_vorgaben_zurueck(self):
        pfad = self.temp / "kaputt.yaml"
        pfad.write_text("version: 1\n  fehlerhafte: einrückung\n\ttab",
                        encoding="utf-8")
        konfig = sr.lade_konfiguration(pfad)
        self.assertEqual(konfig["max_treffer"], sr.VORGABEN["max_treffer"])
        self.assertEqual(konfig.get("_hinweis"), "SSOT unlesbar")

    def test_werte_aus_der_ssot_setzen_sich_durch(self):
        pfad = self.temp / "eigen.yaml"
        pfad.write_text("max_treffer: 5\neigene_domaene: beispiel.de\n",
                        encoding="utf-8")
        konfig = sr.lade_konfiguration(pfad)
        self.assertEqual(konfig["max_treffer"], 5)
        self.assertEqual(konfig["eigene_domaene"], "beispiel.de")

    def test_reale_ssot_ist_lesbar_und_vollstaendig(self):
        """Die ausgelieferte data/suchradar.yaml muss dem Vertrag genügen."""
        konfig = sr.lade_konfiguration(sr.ROOT / "data" / "suchradar.yaml")
        self.assertEqual(konfig["eigene_domaene"], "franksfinanzcheck.de")
        self.assertGreater(konfig["max_abfragen_pro_tag"], 0)
        self.assertTrue(konfig["reihenfolge"])
        self.assertTrue(konfig["searxng_instanzen"])
        # Nur schlüssellose Anbieter dürfen in der Standardkette stehen.
        for anbieter in konfig["reihenfolge"]:
            self.assertTrue(
                sa.ANBIETER[anbieter]["schluessellos"],
                f"Bezahlter Anbieter `{anbieter}` in der Standardkette")


# ====================================================================
#  ANFRAGEN
# ====================================================================
class TestAnfragen(SandboxFall):

    def test_deterministisch_und_entdoppelt(self):
        konfig = self.konfig(anfragen=["Stromkosten senken", "stromkosten  SENKEN!",
                                       "Notgroschen aufbauen"])
        erste = sr.ermittle_anfragen(konfig)
        zweite = sr.ermittle_anfragen(konfig)
        self.assertEqual(erste, zweite)
        normiert = [sr.schlank(e["anfrage"]) for e in erste]
        self.assertEqual(len(normiert), len(set(normiert)))

    def test_anfragenlimit_wird_gehalten(self):
        konfig = self.konfig(max_anfragen_pro_lauf=4,
                             anfragen=[f"begriff nummer {i}" for i in range(40)],
                             schluesselbegriffe_aus_themenpool=False)
        self.assertLessEqual(len(sr.ermittle_anfragen(konfig)), 4)

    def test_eigene_marke_ist_immer_dabei(self):
        konfig = self.konfig(anfragen=[], schluesselbegriffe_aus_themenpool=False)
        begriffe = [e["anfrage"] for e in sr.ermittle_anfragen(konfig)]
        self.assertIn("franksfinanzcheck.de", begriffe)

    def test_prioritaet_sortiert_vor(self):
        konfig = self.konfig(anfragen=[{"anfrage": "niedrig", "prioritaet": 0.1},
                                       {"anfrage": "hoch", "prioritaet": 0.9}],
                             schluesselbegriffe_aus_themenpool=False)
        ergebnis = sr.ermittle_anfragen(konfig)
        selbst = [e["anfrage"] for e in ergebnis]
        self.assertLess(selbst.index("hoch"), selbst.index("niedrig"))

    def test_themenpool_liefert_begriffe_aus_dem_repo(self):
        begriffe = sr._themenpool_begriffe(sr.ROOT, 5)
        # Der Pool hat Schlüsselbegriffe; leer hieße: die Anbindung ist tot.
        self.assertTrue(begriffe, "Themenpool liefert keine Schlüsselbegriffe")
        self.assertLessEqual(len(begriffe), 5)

    def test_themenpool_liefert_flache_strings_keine_listenrepr(self):
        """Regression 25.10.2026: 15 Keywords wurden als EINE Python-Liste
        verschickt – sichtbar als Störung im Cockpit. Der alte Test prüfte
        nur `bool(begriffe)` und `len <= 5`; eine Liste mit einer Liste
        bestand beide Prüfungen. Deshalb hier die Form, nicht nur die Zahl.
        """
        begriffe = sr._themenpool_begriffe(sr.ROOT, 15)
        self.assertEqual(len(begriffe), 15)
        for begriff in begriffe:
            self.assertIsInstance(begriff, str)
            self.assertFalse(begriff.startswith("["))
            self.assertNotIn("', '", begriff)
        auftraege = sr.ermittle_anfragen(
            self.konfig(anfragen=[], max_anfragen_pro_lauf=30))
        self.assertTrue(all(not e["anfrage"].startswith("[")
                            for e in auftraege))

    def test_themenpool_auswahl_ist_datumsstabil(self):
        erste = sr._themenpool_begriffe(sr.ROOT, 5)
        zweite = sr._themenpool_begriffe(sr.ROOT, 5)
        self.assertEqual(erste, zweite)

    def test_schlank_normalisiert(self):
        self.assertEqual(sr.schlank("  Strom­kosten  SENKEN! "), "stromkosten senken")


# ====================================================================
#  ZWISCHENSPEICHER
# ====================================================================
class TestZwischenspeicher(SandboxFall):

    def opts(self, **uebersteuerung) -> dict:
        """Cache-relevante Optionen – dieselbe Quelle wie im Code.

        Ein handgebauter Ausschnitt driftet vom echten Schlüssel ab; der
        Test wäre dann grün, während der Cache im Betrieb nie trifft.
        """
        return {**sr.cache_relevante_optionen(self.konfig()), **uebersteuerung}

    def test_rundlauf(self):
        liste = [treffer("https://a.de/", 1)]
        sr.cache_schreiben("strom", self.opts(), liste, "mojeek")
        self.assertEqual(sr.cache_lesen("strom", self.opts(), 18), liste)

    def test_anderer_suchbegriff_trifft_den_cache_nicht(self):
        sr.cache_schreiben("strom", self.opts(), [treffer("https://a.de/", 1)], "mojeek")
        self.assertIsNone(sr.cache_lesen("gas", self.opts(), 18))

    def test_anderes_land_trifft_den_cache_nicht(self):
        sr.cache_schreiben("strom", self.opts(), [treffer("https://a.de/", 1)], "mojeek")
        self.assertIsNone(sr.cache_lesen("strom", self.opts(land="at"), 18))

    def test_abgelaufener_eintrag_zaehlt_nicht(self):
        sr.CACHE_VERZEICHNIS.mkdir(parents=True, exist_ok=True)
        alt = {"anfrage": "strom", "anbieter": "mojeek",
               "zeitstempel": (sr.berlin_now() - timedelta(hours=99)).isoformat(),
               "treffer": [treffer("https://alt.de/", 1)]}
        (sr.CACHE_VERZEICHNIS
         / f"{sr.cache_schluessel('strom', self.opts())}.json").write_text(
            json.dumps(alt), encoding="utf-8")
        self.assertIsNone(sr.cache_lesen("strom", self.opts(), 18))

    def test_stunden_null_schaltet_den_cache_ab(self):
        sr.cache_schreiben("strom", self.opts(), [treffer("https://a.de/", 1)], "mojeek")
        self.assertIsNone(sr.cache_lesen("strom", self.opts(), 0))

    def test_kaputter_cache_wird_ignoriert_statt_zu_krachen(self):
        sr.CACHE_VERZEICHNIS.mkdir(parents=True, exist_ok=True)
        pfad = (sr.CACHE_VERZEICHNIS
                / f"{sr.cache_schluessel('strom', self.opts())}.json")
        pfad.write_text("{ kein json", encoding="utf-8")
        self.assertIsNone(sr.cache_lesen("strom", self.opts(), 18))

    def test_cache_raeumen_loescht_nur_altes(self):
        sr.cache_schreiben("frisch", self.opts(), [treffer("https://a.de/", 1)], "mojeek")
        sr.CACHE_VERZEICHNIS.mkdir(parents=True, exist_ok=True)
        alt = sr.CACHE_VERZEICHNIS / "alt.json"
        alt.write_text(json.dumps({"zeitstempel": "2020-01-01T00:00:00+02:00",
                                   "treffer": []}), encoding="utf-8")
        self.assertGreaterEqual(sr.cache_raeumen(), 1)
        self.assertFalse(alt.exists())
        self.assertIsNotNone(sr.cache_lesen("frisch", self.opts(), 18))

    def test_suchen_und_cache_teilen_denselben_schluessel(self):
        """Der Fehler, den der erste Entwurf hatte.

        `suchen()` baute seinen Schlüssel aus der vollen Optionen-Menge,
        `lauf()` aus einem handgebauten Ausschnitt. Beide waren für sich
        richtig – und trafen einander nie.
        """
        konfig = self.konfig()
        liste = [treffer("https://a.de/", 1)]
        with patch.object(sa, "hole_treffer", return_value=liste):
            sr.suchen("strom", konfig)
            self.assertIsNotNone(
                sr.cache_lesen("strom", sr.cache_relevante_optionen(konfig), 18),
                "suchen() und lauf() nutzen unterschiedliche Cache-Schlüssel")


# ====================================================================
#  QUOTE
# ====================================================================
class TestQuote(SandboxFall):

    def test_anbieterlimit_stoppt_den_abruf(self):
        quota = {sr.heute(): {"searxng": 10 ** 6}}
        self.assertEqual(sr.quota_verbleibend("searxng", self.konfig(), quota), 0)

    def test_gesamtbudget_stoppt_auch_einen_frischen_anbieter(self):
        """Der Fall, den der erste Entwurf falsch machte.

        Ein überschrittenes Gesamtbudget wurde weggefiltert statt auf 0
        geklemmt – und gab damit ausgerechnet dann unbegrenzt frei.
        """
        quota = {sr.heute(): {"searxng": 5, "mojeek": 5}}
        konfig = self.konfig(max_abfragen_pro_tag=6)
        self.assertEqual(sr.quota_verbleibend("duckduckgo", konfig, quota), 0)

    def test_frischer_tag_hat_budget(self):
        self.assertGreater(sr.quota_verbleibend("duckduckgo", self.konfig(), {}), 0)

    def test_buchen_schreibt_dauerhaft(self):
        sr.quota_buchen("mojeek", 2)
        sr.quota_buchen("mojeek", 1)
        daten = json.loads(sr.QUOTEN_DATEI.read_text(encoding="utf-8"))
        self.assertEqual(daten[sr.heute()]["mojeek"], 3)

    def test_alte_tage_werden_abgeraeumt(self):
        daten = {f"2026-09-{d:02d}": {"mojeek": 1} for d in range(1, 20)}
        daten[sr.heute()] = {"mojeek": 1}
        sr.quota_buchen("mojeek", 1, quota=daten)
        self.assertLessEqual(len(daten), 8)


# ====================================================================
#  INSTANZEN-GESUNDHEIT
# ====================================================================
class TestInstanzen(SandboxFall):

    def test_bewaehrte_zuerst_ausfaelle_zuletzt(self):
        zustand = {
            "https://tot.example": {"erfolge": 0, "fehler": 9, "letzte_dauer_ms": 5},
            "https://gut.example": {"erfolge": 9, "fehler": 0, "letzte_dauer_ms": 900},
        }
        reihe = sr.instanzen_sortieren(
            ["https://tot.example", "https://neu.example", "https://gut.example"],
            zustand)
        self.assertEqual(reihe[0], "https://gut.example")
        self.assertEqual(reihe[-1], "https://tot.example")
        self.assertLess(reihe.index("https://neu.example"),
                        reihe.index("https://tot.example"))

    def test_bei_gleicher_quote_entscheidet_die_antwortzeit(self):
        zustand = {
            "https://langsam.example": {"erfolge": 5, "fehler": 0, "letzte_dauer_ms": 3000},
            "https://schnell.example": {"erfolge": 5, "fehler": 0, "letzte_dauer_ms": 120},
        }
        reihe = sr.instanzen_sortieren(
            ["https://langsam.example", "https://schnell.example"], zustand)
        self.assertEqual(reihe[0], "https://schnell.example")

    def test_doppelte_eintraege_werden_zusammengefasst(self):
        reihe = sr.instanzen_sortieren(
            ["https://a.example/", "https://a.example", "https://b.example"], {})
        self.assertEqual(len(reihe), 2)

    def test_erfolg_und_fehler_werden_vermerkt(self):
        sr.instanz_merken("https://a.example", True, 120.0)
        sr.instanz_merken("https://a.example", False, 0, "Zeitüberschreitung")
        daten = json.loads(sr.INSTANZEN_DATEI.read_text(encoding="utf-8"))
        self.assertEqual(daten["https://a.example"]["erfolge"], 1)
        self.assertEqual(daten["https://a.example"]["fehler"], 1)
        self.assertEqual(daten["https://a.example"]["letzter_fehler"], "Zeitüberschreitung")

    def test_kaputte_instanzdatei_bricht_nichts_ab(self):
        sr.ZUSTAND.mkdir(parents=True, exist_ok=True)
        sr.INSTANZEN_DATEI.write_text("{ defekt", encoding="utf-8")
        self.assertEqual(sr.instanzen_laden(), {})
        self.assertEqual(len(sr.instanzen_sortieren(["https://a.example"], None)), 1)


# ====================================================================
#  SUCHLAUF (mit simuliertem Anbieter – kein Netz)
# ====================================================================
class TestSuchlauf(SandboxFall):

    def _simuliere(self, trefferliste):
        return patch.object(sa, "hole_treffer", return_value=trefferliste)

    def test_erfolg_schreibt_zustand_und_cache(self):
        liste = [treffer("https://franksfinanzcheck.de/x", 1, anfrage="strom")]
        with self._simuliere(liste):
            ergebnis = sr.suchen("strom", self.konfig())
        self.assertEqual(ergebnis["status"], "ok")
        self.assertEqual(len(ergebnis["treffer"]), 1)
        self.assertTrue(sr.QUOTEN_DATEI.exists())
        self.assertIsNotNone(
            sr.cache_lesen("strom", sr.cache_relevante_optionen(self.konfig()), 18))

    def test_zweiter_lauf_kommt_aus_dem_cache(self):
        liste = [treffer("https://a.de/", 1)]
        with self._simuliere(liste):
            sr.suchen("strom", self.konfig())
            zweiter = sr.suchen("strom", self.konfig())
        self.assertEqual(zweiter["status"], "cache")
        self.assertEqual(zweiter["quelle"], "cache")
        # Genau ein Abruf gebucht, nicht zwei.
        daten = json.loads(sr.QUOTEN_DATEI.read_text(encoding="utf-8"))
        self.assertEqual(sum(daten[sr.heute()].values()), 1)

    def test_dry_run_schreibt_nichts(self):
        liste = [treffer("https://a.de/", 1)]
        with self._simuliere(liste):
            ergebnis = sr.suchen("strom", self.konfig(), trocken=True)
        self.assertEqual(ergebnis["status"], "ok")
        self.assertFalse(sr.QUOTEN_DATEI.exists())
        self.assertIsNone(
            sr.cache_lesen("strom", sr.cache_relevante_optionen(self.konfig()), 18))

    def test_anbieterfehler_wird_zum_befund_statt_zum_abbruch(self):
        with patch.object(sa, "hole_treffer",
                          side_effect=sa.AnfrageFehler("alle Anbieter tot", 0)):
            ergebnis = sr.suchen("strom", self.konfig())
        self.assertEqual(ergebnis["status"], "fehler")
        self.assertIn("tot", ergebnis["fehler"])
        self.assertEqual(ergebnis["treffer"], [])

    def test_instanz_wird_aus_dem_merkmal_gelesen(self):
        liste = [treffer("https://a.de/", 1, merkmale=["instanz:https://searx.be"])]
        with self._simuliere(liste):
            sr.suchen("strom", self.konfig())
        daten = json.loads(sr.INSTANZEN_DATEI.read_text(encoding="utf-8"))
        self.assertEqual(daten["https://searx.be"]["erfolge"], 1)


class TestLaufEndeZuEnde(SandboxFall):

    def _antwort(self, anfrage: str, optionen=None):
        """Simulierter Anbieter: eigene Domaene auf Rang 2."""
        return [
            treffer("https://www.verivox.de/strom/", 1, anfrage=anfrage,
                    merkmale=["zusatzzeile"]),
            treffer("https://franksfinanzcheck.de/strom-sparen/", 2, anfrage=anfrage),
            treffer("https://www.check24.de/strom/", 3, anfrage=anfrage,
                    merkmale=["sitelinks"]),
        ]

    def test_lauf_schreibt_alle_schichten(self):
        anfragen = [{"anfrage": "Stromkosten senken", "herkunft": "test",
                     "prioritaet": 1.0}]
        with patch.object(sa, "hole_treffer", side_effect=self._antwort):
            befund = sr.lauf(self.konfig(), anfragen)
        self.assertEqual(befund["zaehlung"]["ok"], 1)
        self.assertEqual(befund["treffer_gesamt"], 3)
        for pfad in (sr.ERGEBNIS_DATEI, sr.RANKING_DATEI, sr.WETTBEWERB_DATEI,
                     sr.VERLAUF_DATEI, sr.RANKING_VERLAUF):
            self.assertTrue(pfad.exists(), f"{pfad.name} wurde nicht geschrieben")

    def test_lauf_erkennt_die_eigene_sichtbarkeit(self):
        anfragen = [{"anfrage": "Stromkosten senken", "herkunft": "test",
                     "prioritaet": 1.0}]
        with patch.object(sa, "hole_treffer", side_effect=self._antwort):
            befund = sr.lauf(self.konfig(), anfragen)
        rang = befund["rang"][0]
        self.assertTrue(rang["sichtbar"])
        self.assertEqual(rang["eigener_rang"], 2)
        self.assertEqual(rang["quelle"], "mojeek")

    def test_dry_run_schreibt_weder_zustand_noch_bericht(self):
        anfragen = [{"anfrage": "Stromkosten senken", "herkunft": "test",
                     "prioritaet": 1.0}]
        with patch.object(sa, "hole_treffer", side_effect=self._antwort):
            sr.lauf(self.konfig(), anfragen, trocken=True)
        self.assertFalse(sr.ZUSTAND.exists())
        self.assertFalse(sr.COCKPIT.exists())

    def test_delta_gegen_den_letzten_stand_derselben_anfrage(self):
        anfragen = [{"anfrage": "Stromkosten senken", "herkunft": "test",
                     "prioritaet": 1.0}]
        with patch.object(sa, "hole_treffer", side_effect=self._antwort):
            sr.lauf(self.konfig(), anfragen)          # Rang 2 wird vermerkt
        # Jetzt rutscht die eigene Seite auf Rang 5 ab.
        def schlechter(anfrage, optionen=None):
            return [treffer(f"https://www.gegner{i}.de/", i, anfrage=anfrage)
                    for i in range(1, 5)] + \
                   [treffer("https://franksfinanzcheck.de/x", 5, anfrage=anfrage)]
        with patch.object(sa, "hole_treffer", side_effect=schlechter):
            befund = sr.lauf(self.konfig(), anfragen, ohne_cache=True)
        rang = befund["rang"][0]
        self.assertEqual(rang["eigener_rang"], 5)
        self.assertEqual(rang["vorher"], 2)
        self.assertEqual(rang["delta"], -3)

    def test_totalausfall_liefert_keine_treffer_und_meldet(self):
        anfragen = [{"anfrage": "Stromkosten senken", "herkunft": "test",
                     "prioritaet": 1.0}]
        with patch.object(sa, "hole_treffer",
                          side_effect=sa.AnfrageFehler("nichts geht", 0)):
            befund = sr.lauf(self.konfig(), anfragen)
            code = sr.main(["--anfrage", "Stromkosten senken", "--kein-bericht"])
        self.assertEqual(befund["zaehlung"]["fehler"], 1)
        self.assertEqual(befund["treffer_gesamt"], 0)
        self.assertEqual(code, 3, "Ein Lauf ohne einen einzigen Treffer muss rot sein")

    def test_budget_schuetzt_vor_zu_vielen_abfragen(self):
        konfig = self.konfig(max_abfragen_pro_tag=2)
        anfragen = [{"anfrage": f"begriff {i}", "herkunft": "test", "prioritaet": 1.0}
                    for i in range(10)]
        with patch.object(sa, "hole_treffer", side_effect=self._antwort):
            befund = sr.lauf(konfig, anfragen)
        abgerufen = befund["zaehlung"]["ok"] + befund["zaehlung"]["cache"]
        self.assertLessEqual(abgerufen, 2)
        self.assertGreater(befund["zaehlung"]["uebersprungen"], 0)


# ====================================================================
#  DATENQUALITÄT (Live-SERP-Prüfung 25.10.2026)
# ====================================================================
class TestDatenqualitaet(SandboxFall):
    """Ein Wissens-Rückfall ist kein Ranking – weder für Rang noch Radar."""

    @staticmethod
    def _treffer(domaene: str, rang: int, quelle: str) -> dict:
        return {"domaene": domaene, "rang": rang, "quelle": quelle,
                "titel": f"Titel {rang}", "anfrage": "q", "merkmale": []}

    def test_wikipedia_ist_kein_organischer_treffer(self):
        liste = [self._treffer("de.wikipedia.org", 1, "wikipedia"),
                 self._treffer("ing.de", 1, "searxng")]
        self.assertEqual([t["domaene"] for t in sr.organische_treffer(liste)],
                         ["ing.de"])

    def test_unbekannte_quelle_ist_fail_closed(self):
        self.assertFalse(sr.ist_organisch({"quelle": "neuermysteriöser Dienst"}))
        self.assertFalse(sr.ist_organisch({}))

    def test_datenqualitaet_zaehlt_rueckfall_ehrlich(self):
        ergebnisse = [
            {"anfrage": "a", "quelle": "wikipedia",
             "treffer": [self._treffer("de.wikipedia.org", i, "wikipedia")
                         for i in range(1, 7)]},
            {"anfrage": "b", "quelle": "searxng",
             "treffer": [self._treffer("ing.de", 1, "searxng")]},
        ]
        dq = sr.datenqualitaet(ergebnisse)
        self.assertEqual(dq["anfragen_erfolgreich"], 2)
        self.assertEqual(dq["anfragen_organisch"], 1)
        self.assertEqual(dq["treffer_rueckfall"], 6)
        self.assertEqual(dq["treffer_organisch"], 1)
        self.assertEqual(dq["aussagekraft"], "eingeschraenkt")
        self.assertEqual(dq["anbieter"]["wikipedia"], 1)

    def test_rueckfall_erfindet_keinen_eigenen_rang(self):
        ergebnisse = [{"anfrage": "a", "quelle": "wikipedia",
                       "treffer": [self._treffer("franksfinanzcheck.de", 1,
                                                "wikipedia")]}]
        rang = sr.rang_verfolgung(ergebnisse, "franksfinanzcheck.de")
        self.assertEqual(rang[0]["eigener_rang"], 0)
        self.assertFalse(rang[0]["sichtbar"])

    def test_lauf_schreibt_nur_organische_treffer_ins_wettbewerbs_radar(self):
        antib = [self._treffer("de.wikipedia.org", 1, "wikipedia"),
                 self._treffer("de.wikipedia.org", 2, "wikipedia"),
                 self._treffer("ing.de", 3, "searxng")]
        anfragen = [{"anfrage": "Fixkosten senken", "herkunft": "test",
                     "prioritaet": 1.0}]
        with patch.object(sa, "hole_treffer", return_value=antib):
            befund = sr.lauf(self.konfig(), anfragen)
        self.assertEqual(befund["treffer_gesamt"], 3)
        self.assertEqual(befund["treffer_organisch"], 1)
        self.assertEqual([e["domaene"] for e in
                          befund["wettbewerb"]["domaenen"]], ["ing.de"])
        self.assertEqual(befund["datenqualitaet"]["aussagekraft"], "voll")

    def test_cockpit_weist_rueckfall_aus(self):
        text = sr.bericht({
            "zeitstempel": sr.berlin_now().isoformat(),
            "zaehlung": {"ok": 1}, "anfragen_geplant": 1,
            "treffer_gesamt": 6, "treffer_organisch": 0,
            "datenqualitaet": sr.datenqualitaet([
                {"anfrage": "q", "quelle": "wikipedia",
                 "treffer": [self._treffer("de.wikipedia.org", 1,
                                          "wikipedia")]}]),
            "rang": [], "wettbewerb": {"domaenen": [], "merkmale": {}},
            "fehler": []}, sr.VORGABEN)
        self.assertIn("## Datenqualität", text)
        self.assertIn("keine", text)


# ====================================================================
#  AUSWERTUNG
# ====================================================================
class TestAuswertung(SandboxFall):

    def test_wettbewerbs_radar_trennt_haeufigkeit_und_tiefe(self):
        liste = [
            treffer("https://a.de/1", 9, anfrage="q1"),
            treffer("https://a.de/2", 9, anfrage="q2"),
            treffer("https://b.de/1", 1, anfrage="q1", merkmale=["sitelinks"]),
        ]
        radar = sr.wettbewerbs_radar(liste)
        praef = {e["domaene"]: e for e in radar["domaenen"]}
        self.assertEqual(praef["a.de"]["treffer"], 2)
        self.assertEqual(praef["a.de"]["durchschnitts_rang"], 9.0)
        self.assertEqual(praef["a.de"]["top3"], 0)
        self.assertEqual(praef["b.de"]["top3"], 1)
        self.assertEqual(praef["b.de"]["bester_rang"], 1)

    def test_technik_merkmale_gehoeren_nicht_in_den_bericht(self):
        liste = [treffer("https://a.de/1", 1, merkmale=[
            "instanz:https://searx.be", "engine:google", "faq", "vorschaubild"])]
        radar = sr.wettbewerbs_radar(liste)
        self.assertNotIn("instanz:https://searx.be", radar["merkmale"])
        self.assertNotIn("engine:google", radar["merkmale"])
        self.assertIn("faq", radar["merkmale"])
        self.assertIn("vorschaubild", radar["merkmale"])

    def test_rang_verfolgung_ohne_eigenen_treffer(self):
        ergebnisse = [{"anfrage": "irgendwas", "quelle": "mojeek",
                       "treffer": [treffer("https://fremd.de/", 1)]}]
        rang = sr.rang_verfolgung(ergebnisse, "franksfinanzcheck.de")
        self.assertFalse(rang[0]["sichtbar"])
        self.assertEqual(rang[0]["eigener_rang"], 0)

    def test_teildomaene_zaehlt_nicht_als_eigene(self):
        """`franksfinanzcheck.de.example` ist nicht die eigene Seite."""
        ergebnisse = [{"anfrage": "x", "quelle": "mojeek",
                       "treffer": [treffer("https://franksfinanzcheck.de.evil.example/", 1)]}]
        rang = sr.rang_verfolgung(ergebnisse, "franksfinanzcheck.de")
        self.assertFalse(rang[0]["sichtbar"])

    def test_bericht_enthaelt_die_kernabschnitte(self):
        befund = {"zeitstempel": sr.berlin_now().isoformat(),
                  "zaehlung": {"ok": 2, "cache": 1, "fehler": 0, "uebersprungen": 0},
                  "anfragen_geplant": 3, "treffer_gesamt": 6,
                  "rang": [{"anfrage": "Stromkosten senken", "eigener_rang": 2,
                            "vorher": 3, "delta": 1, "titel": "T", "url": "U",
                            "quelle": "searxng", "sichtbar": True}],
                  "wettbewerb": sr.wettbewerbs_radar(
                      [treffer("https://a.de/1", 1, merkmale=["sitelinks"])]),
                  "fehler": []}
        text = sr.bericht(befund, sr.VORGABEN)
        for abschnitt in ("SUCHRADAR", "## Lauf", "## Eigene Sichtbarkeit",
                          "## Wettbewerb", "## Einordnung"):
            self.assertIn(abschnitt, text)
        self.assertIn("▲", text, "Verbesserung wird nicht angezeigt")
        self.assertNotIn("data/suchradar/", text)

    def test_bericht_schreibt_die_datei(self):
        befund = {"zeitstempel": sr.berlin_now().isoformat(), "zaehlung": {},
                  "anfragen_geplant": 0, "treffer_gesamt": 0, "rang": [],
                  "wettbewerb": {"domaenen": [], "merkmale": {}}, "fehler": []}
        pfad = sr.bericht_schreiben(befund, sr.VORGABEN)
        self.assertTrue(pfad.exists())
        self.assertIn("SUCHRADAR", pfad.read_text(encoding="utf-8"))


# ====================================================================
#  PARSER (echte HTML-Proben, kein Netz)
# ====================================================================
class TestParser(SandboxFall):

    def test_duckduckgo_filtert_anzeigen_und_entpackt_umleitungen(self):
        liste = sa.parse_duckduckgo("stromkosten senken", probe("duckduckgo.html"))
        self.assertEqual(len(liste), 3, "Anzeige wurde mitgezählt oder Treffer fehlt")
        for t in liste:
            self.assertNotIn("duckduckgo.com", t["url"])
            self.assertNotIn("uddg", t["url"])
        self.assertTrue(any(t["domaene"] == "franksfinanzcheck.de" for t in liste))
        self.assertEqual(liste[0]["rang"], 1)

    def test_duckduckgo_snippet_wird_geglättet(self):
        liste = sa.parse_duckduckgo("x", probe("duckduckgo.html"))
        self.assertNotIn("\n", liste[0]["beschreibung"])
        self.assertNotIn("<b>", liste[0]["beschreibung"])
        self.assertIn("vergleichen", liste[0]["beschreibung"])

    def test_searxng_titel_ist_keine_adresse(self):
        """Regression gegen den Selektor-Fehler des ersten Entwurfs."""
        liste = sa.parse_searxng("stromkosten senken", probe("searxng.html"))
        self.assertEqual(len(liste), 3)
        for t in liste:
            self.assertTrue(t["titel"], "Titel ist leer")
            self.assertNotEqual(t["titel"], t["anzeigedomaene"],
                                "Titel ist die Adresse – Selektor-Reihenfolge")
            self.assertNotIn("http", t["titel"])

    def test_searxng_merkt_die_beteligten_suchmaschinen(self):
        liste = sa.parse_searxng("x", probe("searxng.html"))
        self.assertIn("engine:google", liste[0]["merkmale"])
        self.assertIn("engine:bing", liste[0]["merkmale"])

    def test_mojeek_filtert_den_eigenlink(self):
        liste = sa.parse_mojeek("stromkosten senken", probe("mojeek.html"))
        self.assertEqual(len(liste), 3, "Mojeek-Eigenlink zählt als Treffer")
        self.assertTrue(all(not ist_host_oder_subdomain(t["url"], "mojeek.com")
                            for t in liste))
        self.assertEqual(liste[1]["domaene"], "franksfinanzcheck.de")

    def test_umleitung_auspacken_ist_host_exakt(self):
        """Alert #83: `"duckduckgo.com" in netloc` ist eine Vermutung, keine Prüfung.

        Beweis, dass die Lücke real war: Vor der Heilung wurde die Suffix-Domain
        `duckduckgo.com.angreifer.example` zu `https://evil.example` „entpackt“.
        Ein Angreifer-Ziel wäre damit als organischer Treffer in den
        Suchradar-Bericht und in die Rang-Verfolgung gelangt.
        """
        ziel = "https%3A%2F%2Fexample.com%2Fa"
        # Legitime Umleitung – absolut UND schema-relativ (so liefert DuckDuckGo
        # die Treffer: `//duckduckgo.com/l/?uddg=…`).
        self.assertEqual(
            sh.uddg_entpacken(f"https://duckduckgo.com/l/?uddg={ziel}"),
            "https://example.com/a")
        self.assertEqual(
            sh.uddg_entpacken(f"//duckduckgo.com/l/?uddg={ziel}"),
            "https://example.com/a", "schema-relative Form wird nicht mehr ausgepackt")
        # Echte Subdomain gehört dazu (html.duckduckgo.com ist die Lite-Variante).
        self.assertEqual(
            sh.uddg_entpacken(f"https://html.duckduckgo.com/l/?uddg={ziel}"),
            "https://example.com/a")
        # FEINDPROBE 1: Suffix-Domain – der Host ist angreifer.example.
        suffix = ("https://duckduckgo.com.angreifer.example/l/"
                  "?uddg=https%3A%2F%2Fevil.example")
        self.assertEqual(sh.uddg_entpacken(suffix), suffix,
                         "Suffix-Domain wurde als DuckDuckGo-Umleitung entpackt")
        # FEINDPROBE 2: Hostname als Query-Parameter einer fremden URL.
        param = ("https://angreifer.example/l/"
                 "?x=duckduckgo.com&uddg=https%3A%2F%2Fevil.example")
        self.assertEqual(sh.uddg_entpacken(param), param,
                         "Query-Parameter wurde als DuckDuckGo-Host fehlgedeutet")
        # Gegenprobe: fremde URLs bleiben unangetastet.
        self.assertEqual(sh.uddg_entpacken("https://example.com/b"),
                         "https://example.com/b")

    def test_eigenlink_filter_ist_host_exakt(self):
        """Alert #83: Der Eigenlink-Filter darf nicht per Teilzeichenkette entscheiden.

        Zwei Richtungen, beide vorher falsch:
          · eine fremde URL, die den Hostnamen nur im Query trägt, wurde
            fälschlich als Eigenlink WEGGEWORFEN (stiller Trefferverlust),
          · eine Suffix-Domain der Suchmaschine wurde fälschlich BEHALTEN.
        """
        html = """
        <ul class="results-standard">
          <li><a class="ob" href="https://franksfinanzcheck.de/strom-sparen/">Eigen</a>
              <h2>Titel eins</h2><p class="s">Snippet eins</p></li>
          <li><a class="ob" href="https://beispiel.example/?quelle=mojeek.com">Fremd</a>
              <h2>Titel zwei</h2><p class="s">Snippet zwei</p></li>
          <li><a class="ob" href="https://mojeek.com.einbrecher.example/x">Suffix</a>
              <h2>Titel drei</h2><p class="s">Snippet drei</p></li>
          <li><a class="ob" href="https://www.mojeek.com/about">Eigenlink</a>
              <h2>Titel vier</h2><p class="s">Snippet vier</p></li>
        </ul>"""
        urls = [t["url"] for t in sa.parse_mojeek("stromkosten senken", html)]
        self.assertIn("https://franksfinanzcheck.de/strom-sparen/", urls)
        self.assertIn("https://beispiel.example/?quelle=mojeek.com", urls,
                      "Query-Parameter wurde als Mojeek-Host fehlgedeutet")
        self.assertIn("https://mojeek.com.einbrecher.example/x", urls,
                      "Suffix-Domain wurde als Mojeek-Eigenlink weggeworfen")
        self.assertNotIn("https://www.mojeek.com/about", urls,
                         "Mojeek-Eigenlink zählt als Treffer")

    def test_lite_trennt_titel_und_snippet_aus_geschwisterzeilen(self):
        liste = sa.parse_duckduckgo_lite("stromkosten senken",
                                         probe("duckduckgo_lite.html"))
        self.assertEqual(len(liste), 3, "Anzeige mitgezählt oder Treffer fehlt")
        self.assertEqual(liste[0]["titel"], "Strom vergleichen und sparen")
        self.assertIn("Preisgarantie", liste[0]["beschreibung"])
        self.assertNotEqual(liste[0]["titel"], liste[0]["beschreibung"],
                            "Titel und Snippet sind verrutscht")

    def test_lite_filtert_anzeigen(self):
        liste = sa.parse_duckduckgo_lite("x", probe("duckduckgo_lite.html"))
        for t in liste:
            self.assertNotIn("duckduckgo.com", t["url"])
            self.assertNotIn("y.js", t["url"])
            self.assertNotIn("Anzeige", t["titel"])

    def test_lite_verschiebt_die_liste_nicht_bei_fehlendem_snippet(self):
        """Ein Snippet weniger darf nicht alle folgenden Zuordnungen kippen.

        Genau das wäre der stille Fehler: Der Lauf bliebe grün, nur die
        Beschreibungen gehörten ab der Lücke zum jeweils vorherigen Titel.
        """
        html = probe("duckduckgo_lite.html").replace(
            '<td class="result-snippet">Mit Rechnung: was Abschlag, Grundpreis und\n      Verbrauch wirklich ausmachen.</td>', "")
        liste = sa.parse_duckduckgo_lite("x", html)
        erster = next((t for t in liste if "franksfinanzcheck.de" in t["url"]), None)
        if erster is not None:
            self.assertEqual(erster["beschreibung"], "",
                             "Fehlendes Snippet wurde aus der Nachbarzeile ergänzt")
        letzter = next((t for t in liste if "stromspar-initiative.de" in t["url"]), None)
        if letzter is not None:
            self.assertIn("Rechnung dauerhaft", letzter["beschreibung"],
                          "Zuordnung nach der Lücke ist verrutscht")

    def test_lite_ist_als_anbieter_registriert_und_in_der_kette(self):
        self.assertIn("duckduckgo_lite", sa.ANBIETER)
        self.assertIn("duckduckgo_lite", sa.AUSFUEHRER)
        self.assertIn("duckduckgo_lite", sa.STANDARD_REIHENFOLGE)
        self.assertTrue(sa.ANBIETER["duckduckgo_lite"]["schluessellos"])

    def test_lite_steht_vor_dem_fremden_index(self):
        """Ausweichen innerhalb derselben Quelle, bevor der Index wechselt."""
        reihe = sa.STANDARD_REIHENFOLGE
        self.assertLess(reihe.index("duckduckgo_lite"), reihe.index("mojeek"))
        self.assertGreater(reihe.index("duckduckgo_lite"), reihe.index("duckduckgo"))

    def test_leeres_html_liefert_leere_liste_statt_fehler(self):
        self.assertEqual(sa.parse_duckduckgo("x", ""), [])
        self.assertEqual(sa.parse_duckduckgo_lite("x", ""), [])
        self.assertEqual(sa.parse_searxng("x", ""), [])
        self.assertEqual(sa.parse_mojeek("x", ""), [])

    def test_scriptinhalt_wird_nicht_zum_snippet(self):
        liste = sa.parse_duckduckgo("x", probe("duckduckgo.html"))
        for t in liste:
            self.assertNotIn("dataLayer", t["beschreibung"])
            self.assertNotIn("dataLayer", t["titel"])


# ====================================================================
#  GATTER
# ====================================================================
class TestGatter(SandboxFall):

    def test_bezahlte_anbieter_sind_gesperrt(self):
        for anbieter in ("apify", "serpapi", "serper"):
            erlaubt, grund = sa.pruefe_freigabe(anbieter)
            self.assertFalse(erlaubt, f"`{anbieter}` ist ohne Freigabe nutzbar")
            self.assertIn("serp_premium", grund)

    def test_schluessellose_anbieter_brauchen_keine_freigabe(self):
        for anbieter in ("searxng", "duckduckgo", "mojeek", "wikipedia"):
            self.assertTrue(sa.pruefe_freigabe(anbieter)[0])

    def test_unbekannter_anbieter_ist_gesperrt(self):
        self.assertFalse(sa.pruefe_freigabe("erfundener_dienst")[0])

    def test_ssrf_gatter_blockiert_fremde_ziele(self):
        for url in ("http://169.254.169.254/latest/meta-data/",
                    "file:///etc/passwd", "https://evil.example/search"):
            self.assertFalse(sa.host_erlaubt(url), f"SSRF-Gatter lässt {url} durch")

    def test_ssrf_gatter_lässt_bekannte_anbieter_durch(self):
        self.assertTrue(sa.host_erlaubt("https://html.duckduckgo.com/html/?q=x"))
        self.assertTrue(sa.host_erlaubt("https://www.mojeek.com/search?q=x"))

    def test_konfigurierte_instanz_wird_freigegeben(self):
        sa.instanzen_zulassen(["https://meine-instanz.example"])
        self.assertTrue(sa.host_erlaubt("https://meine-instanz.example/search"))
        sa.instanzen_zulassen([])

    def test_kette_ueberspringt_gesperrte_anbieter(self):
        """Auch mit gesetztem Token darf ein gesperrter Anbieter nicht laufen."""
        umgebung = {"APIFY_TOKEN": "geheim"}
        erlaubt, _ = sa.pruefe_freigabe("apify", umgebung)
        self.assertFalse(erlaubt,
                         "Ein gesetztes Token hebelt die Kostensperre aus")

    def test_kette_faellt_durch_bis_zum_lieferanten(self):
        aufrufe = []

        def kaputt(anfrage, optionen):
            aufrufe.append("kaputt")
            raise sa.AnfrageFehler("ausgefallen", 0)

        def heil(anfrage, optionen):
            aufrufe.append("heil")
            return [treffer("https://a.de/", 1)]

        with patch.dict(sa.AUSFUEHRER, {"mojeek": kaputt, "wikipedia": heil}):
            liste = sa.hole_treffer("strom", {"reihenfolge": ["mojeek", "wikipedia"]})
        self.assertEqual(aufrufe, ["kaputt", "heil"])
        self.assertEqual(len(liste), 1)

    def test_leere_anfrage_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            sa.hole_treffer("   ")


# ====================================================================
#  SICHTBARKEIT DES ERGEBNISSES
# ====================================================================
class TestCockpitSichtbar(unittest.TestCase):
    """Das Ergebnis muss im Repo ankommen, nicht nur im CI-Artefakt.

    Ein vollautomatischer Lauf, dessen einziger menschenlesbarer Output
    als Build-Artefakt endet, ist für den Betreiber unsichtbar – er muss
    jedes Mal in die Actions-Ansicht klicken. Genau das war der Zustand
    des ersten Entwurfs: Der Name `SUCHRADAR-STATUS.md` fiel unter die
    .gitignore-Regel `/*-STATUS.md` und wurde damit still verworfen.
    """

    def test_cockpit_faellt_nicht_unter_die_ignore_regel(self):
        """Regression: `*-STATUS.md` und `*-REPORT.md` sind ignoriert."""
        name = sr.COCKPIT.name
        self.assertFalse(name.endswith("-STATUS.md"),
                         f"{name} fällt unter .gitignore /*-STATUS.md")
        self.assertFalse(name.endswith("-REPORT.md"),
                         f"{name} fällt unter .gitignore /*-REPORT.md")

    def test_git_ignoriert_das_cockpit_nicht(self):
        """Der echte Beweis – nicht nur die Namensregel nachgebaut."""
        import subprocess
        rel = sr.COCKPIT.name
        try:
            r = subprocess.run(["git", "check-ignore", "-q", rel],
                               cwd=sr.ROOT, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git nicht verfügbar")
        # Exit 0 = ignoriert, 1 = nicht ignoriert.
        self.assertEqual(r.returncode, 1,
                         f"{rel} wird von .gitignore verschluckt – das "
                         "Cockpit käme nie im Repo an")

    def test_workflow_committet_das_cockpit(self):
        """Die Datei nützt nichts, wenn der Workflow sie nicht staged."""
        wf = (sr.ROOT / ".github" / "workflows" / "suchradar.yml")
        text = wf.read_text(encoding="utf-8")
        self.assertIn(sr.COCKPIT.name, text,
                      "Workflow erwähnt das Cockpit nicht")
        pfade = text.split("PFADE=(", 1)[1].split(")", 1)[0]
        self.assertIn(sr.COCKPIT.name, pfade,
                      "Cockpit steht nicht in der Stage-Liste des Workflows")

    def test_zustand_ist_vollstaendig_gelistet(self):
        """Jede Auswertungsdatei muss mitkommen, sonst fehlt morgen das Delta."""
        wf = (sr.ROOT / ".github" / "workflows" / "suchradar.yml")
        pfade = wf.read_text(encoding="utf-8").split("PFADE=(", 1)[1].split(")", 1)[0]
        for datei in ("quota.json", "instanzen.json", "rankings.json",
                      "rankings.jsonl", "wettbewerb.json"):
            self.assertIn(datei, pfade, f"{datei} wird nicht committet")

    def test_cache_bleibt_ignoriert(self):
        """Der Zwischenspeicher ist flüchtig und darf das Repo nicht füllen."""
        import subprocess
        try:
            r = subprocess.run(["git", "check-ignore", "-q",
                                "data/suchradar/cache/x.json"],
                               cwd=sr.ROOT, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git nicht verfügbar")
        self.assertEqual(r.returncode, 0,
                         "data/suchradar/cache/ ist nicht ignoriert")


# ====================================================================
#  CLI
# ====================================================================
class TestCli(SandboxFall):

    def test_selftest_laueft_durch(self):
        self.assertEqual(sr.selbsttest(), 0)
        self.assertEqual(sa.selbsttest(), 0)

    def test_status_ohne_lauf_meldet_statt_zu_krachen(self):
        self.assertEqual(sr.main(["--status"]), 1)

    def test_json_ausgabe_ist_maschinenlesbar(self):
        import contextlib
        import io
        puffer = io.StringIO()
        with patch.object(sa, "hole_treffer",
                          return_value=[treffer("https://a.de/", 1)]):
            with contextlib.redirect_stdout(puffer):
                code = sr.main(["--anfrage", "Stromkosten senken",
                                "--json", "--kein-bericht"])
        self.assertEqual(code, 0)
        daten = json.loads(puffer.getvalue())
        self.assertEqual(daten["treffer_gesamt"], 1)
        self.assertNotIn("ergebnisse", daten, "Rohdaten gehören nicht in die Ausgabe")

    def test_probe_meldet_gruen_wenn_ein_anbieter_liefert(self):
        def liefert(anfrage, optionen):
            return [treffer("https://a.de/", 1)]

        fakes = {aid: liefert for aid in sa.ANBIETER if sa.ANBIETER[aid]["schluessellos"]}
        with patch.dict(sa.AUSFUEHRER, fakes):
            befund = sr.probe(self.konfig(), "test")
        ok = [e for e in befund["anbieter"] if e["status"] == "ok"]
        erwartet = sum(1 for a in sa.ANBIETER.values() if a["schluessellos"])
        self.assertEqual(len(ok), erwartet,
                         "Nicht jeder schlüssellose Anbieter wurde gemessen")
        self.assertTrue(all(e["treffer"] == 1 for e in ok))

    def test_probe_meldet_rot_bei_totalausfall(self):
        def kaputt(anfrage, optionen):
            raise sa.AnfrageFehler("unerreichbar", 0)

        fakes = {aid: kaputt for aid in sa.ANBIETER if sa.ANBIETER[aid]["schluessellos"]}
        with patch.dict(sa.AUSFUEHRER, fakes):
            befund = sr.probe(self.konfig(), "test")
        selbst = [e for e in befund["anbieter"] if e["schluessellos"]]
        self.assertTrue(all(e["status"] == "fehler" for e in selbst))
        self.assertTrue(all("unerreichbar" in e["fehler"] for e in selbst))

    def test_probe_nennt_gesperrte_anbieter_statt_sie_still_zu_uebergehen(self):
        def liefert(anfrage, optionen):
            return [treffer("https://a.de/", 1)]

        fakes = {aid: liefert for aid in sa.ANBIETER}
        with patch.dict(sa.AUSFUEHRER, fakes):
            befund = sr.probe(self.konfig(), "test")
        gesperrt = {e["anbieter"]: e["status"] for e in befund["anbieter"]
                    if not e["freigegeben"]}
        self.assertIn("apify", gesperrt)
        self.assertEqual(gesperrt["apify"], "gesperrt")


if __name__ == "__main__":
    unittest.main()
