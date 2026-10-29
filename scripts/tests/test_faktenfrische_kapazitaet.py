#!/usr/bin/env python3
"""Regressionstests für die Frischhalte-Deckung (Issue #912, 29.10.2026).

DER BEFUND, DEN DIESE DATEI FESTSCHREIBT
========================================
Die Release-Scorecard („Produktionswahrheit“) war ab dem 27.10.2026 jeden
Tag rot, und Ticket #912 ließ sich nicht schließen. Gemeldet wurde das
Symptom: „Faktenalter blockiert“ bei zehn, dann dreizehn Artikeln.

Die Ursache stand nirgends, weil sie niemand rechnete:

    Bedarf   = Σ 1/Intervall über den Bestand
             = 2,58 Faktenprüfungen je Tag (≈ 18/Woche bei 106 Seiten)
    Angebot  = 3 Artikel je Lauf × 2 Läufe je Woche = 0,86/Tag
    Deckung  = 33 %

Jede Woche wurden also zwölf Seiten mehr überfällig, als geprüft werden
konnten. Die Scorecard konnte NIE grün werden – ein Dauer-Alarm ohne
Schließpfad, den die eigene Governance (C14) verbietet.

Die Intervalle waren richtig. Geliefert wurde zu wenig. Diese Datei hält
die Reparatur in fünf Richtungen fest:

  1. BEDARF ist eine Rechnung, keine Zählung: 1/Intervall je Seite.
  2. ANGEBOT kommt aus dem echten Plan (cron) und dem echten Budget.
  3. EDF statt Klassenrang: Die früheste Frist zuerst – sonst verhungern
     Standard-Seiten (90 Tage) hinter saisonalen (30 Tage) unbegrenzt.
  4. VORLAUF: Arbeit beginnt vor der roten Kante, nicht an ihr.
  5. Der REPO-ZUSTAND ist gedeckt – die Kadenz hält den Bestand, und die
     Scorecard nennt die Ursache statt nur das Symptom.

Alle Proben laufen gegen eingefrorene Tage (Uhr-Zwang, `selftest_clock`):
Ein Test, der die Wanduhr liest, ist eine Verabredung mit dem Kalender.
"""
from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische as ff                      # noqa: E402
import faktenfrische_kapazitaet as kap          # noqa: E402

PROBETAG = dt.date(2026, 10, 29)


def cfg_probe(budget: int = 3, limit: int = 10) -> dict:
    return {
        "intervalle": {"ymyl_tage": 45, "standard_tage": 90, "saison_tage": 30,
                       "erstrecherche_bei_erstellung": True},
        "budget": {"max_artikel_pro_lauf": budget, "auto_skalierung": True,
                   "hartes_limit_pro_lauf": limit},
        "planung": {"vorlauf_tage": 7, "nachhol_frist_tage": 7,
                    "horizont_tage": 60, "min_deckung_prozent": 110},
    }


def ueberfaellig(n: int, start: int = 0) -> list[dict]:
    """n saisonale Seiten (Intervall 30), alle seit gestern überfällig."""
    basis = PROBETAG - dt.timedelta(days=31)
    return [{"slug": f"probe-{start + i:03d}",
             "titel": "Heizung Winter saisonal", "beschreibung": "",
             "keywords": ["Heizung"], "pillar": "energie",
             "faktencheck": basis}
            for i in range(n)]


class CronPlanTest(unittest.TestCase):
    """Das Angebot wird gelesen, nicht abgetippt (slot_wache-Prinzip)."""

    def test_taeglicher_plan_ist_ein_lauf(self):
        self.assertEqual(kap.laeufe_je_tag(["40 4 * * *"])[0], 1.0)

    def test_zwei_wochentage_sind_zwei_siebentel(self):
        self.assertEqual(kap.laeufe_je_tag(["40 4 * * 2,4"])[0], 2 / 7)

    def test_stundenraster_und_werktage(self):
        self.assertEqual(kap.laeufe_je_tag(["0 */6 * * *"])[0], 4.0)
        self.assertEqual(kap.laeufe_je_tag(["0 6 * * 1-5"])[0], 5 / 7)

    def test_sonntag_ist_null_und_sieben(self):
        self.assertEqual(kap.laeufe_je_tag(["0 6 * * 7"])[0], 1 / 7)

    def test_kalenderbindung_wird_nicht_geraten(self):
        # Monatsgebundene Pläne sind keine Tagesrate – lieber „nicht lesbar“.
        self.assertIsNone(kap.laeufe_je_tag(["0 6 1 * *"])[0])
        self.assertIsNone(kap.laeufe_je_tag(["quatsch"])[0])
        self.assertIsNone(kap.laeufe_je_tag([])[0])
        self.assertIsNone(kap.feld_werte("*/0", 0, 23))

    def test_workflow_datei_liefert_den_plan(self):
        laeufe, hinweise = kap.laeufe_aus_workflow()
        self.assertIsNotNone(laeufe, f"Plan nicht lesbar: {hinweise}")
        self.assertGreaterEqual(laeufe, 0.9,
                                "Der Bestands-Takt muss mindestens täglich "
                                "laufen – sonst ist #912 zurück")


class BedarfTest(unittest.TestCase):
    """Σ 1/Intervall – unabhängig davon, wie viele Seiten heute rot sind."""

    def test_dreissig_saisonale_seiten_brauchen_eine_pruefung_je_tag(self):
        self.assertAlmostEqual(
            kap.bedarf_je_tag(ueberfaellig(30), cfg_probe(), PROBETAG), 1.0,
            places=6)

    def test_ueberfaelligkeit_erhoeht_den_bedarf_nicht(self):
        cfg = cfg_probe()
        frisch = [{"slug": "f1", "titel": "Heizung Winter saisonal",
                   "beschreibung": "", "keywords": ["Heizung"], "pillar": "",
                   "faktencheck": PROBETAG}]
        alt = [dict(frisch[0], faktencheck=PROBETAG - dt.timedelta(days=31))]
        self.assertAlmostEqual(kap.bedarf_je_tag(frisch, cfg, PROBETAG),
                               kap.bedarf_je_tag(alt, cfg, PROBETAG), places=6)

    def test_klassen_haben_die_ssot_intervalle(self):
        cfg = cfg_probe()
        saison = ff.faelligkeit({"titel": "Heizung", "keywords": [],
                                 "faktencheck": PROBETAG}, cfg, PROBETAG)
        stino = ff.faelligkeit({"titel": "Aufräumen", "keywords": [],
                                "faktencheck": PROBETAG}, cfg, PROBETAG)
        self.assertEqual((saison["intervall"], stino["intervall"]), (30, 90))


class FristTest(unittest.TestCase):
    """Die Frist kommt aus der EINEN Fälligkeitsregel (C19, keine zweite)."""

    def test_faelligkeit_liefert_frist_und_restlaufzeit(self):
        cfg = cfg_probe()
        art = {"titel": "Heizung", "keywords": [],
               "faktencheck": PROBETAG - dt.timedelta(days=24)}
        status = ff.faelligkeit(art, cfg, PROBETAG)
        self.assertEqual(status["frist"], PROBETAG + dt.timedelta(days=6))
        self.assertEqual(status["restlaufzeit"], 6)
        self.assertFalse(status["faellig"])

    def test_erstrecherche_hat_keine_frist(self):
        status = ff.faelligkeit({"titel": "Heizung", "keywords": [],
                                 "faktencheck": None},
                                cfg_probe(), PROBETAG)
        self.assertIsNone(status["frist"])
        self.assertTrue(status["faellig"])


class DeckungsTest(unittest.TestCase):
    """Die Rechnung, die den Dauer-Alarm #912 erklärt."""

    def test_unterdeckte_kadenz_wird_rot_gerechnet(self):
        # 60 überfällige Seiten (Bedarf 2,0/Tag) gegen 2 Läufe/Woche mit 3:
        # 0,86/Tag = 43 % – dieselbe Klasse wie der Produktionsbefund.
        p = kap.plan(ueberfaellig(60), cfg_probe(), 3, 2 / 7, PROBETAG)
        self.assertEqual(round(p["deckung_prozent"]), 43)
        self.assertFalse(p["rueckstand_abgebaut"])

    def test_taeglicher_takt_deckt_den_bestand(self):
        # 15 überfällige Seiten, 3 je Tag: in 4 Tagen weg (Frist 7).
        p = kap.plan(ueberfaellig(15), cfg_probe(), 3, 1.0, PROBETAG)
        self.assertGreaterEqual(p["deckung_prozent"], 110)
        self.assertTrue(p["rueckstand_abgebaut"])

    def test_grosser_rueckstand_zieht_die_auto_skalierung_nach(self):
        # 60 Seiten bei 3 je Tag bräuchten 19 Tage – die Frist ist 7. Genau
        # dafür existiert `budget.auto_skalierung` (Sockel 3, Limit 10).
        p = kap.plan(ueberfaellig(60), cfg_probe(), 3, 1.0, PROBETAG)
        self.assertFalse(p["rueckstand_abgebaut"])
        emp = kap.empfohlenes_budget(ueberfaellig(60), cfg_probe(), 1.0, PROBETAG)
        self.assertTrue(emp["erreicht"])
        self.assertGreater(emp["budget"], 3)

    def test_abbau_dauert_bei_kleiner_kapazitaet_laenger(self):
        seiten = ueberfaellig(60)
        schnell = kap.plan(seiten, cfg_probe(), 10, 1.0, PROBETAG)["abbau_tage"]
        langsam = kap.plan(seiten, cfg_probe(), 4, 1.0, PROBETAG)["abbau_tage"]
        self.assertLess(schnell, langsam)

    def test_leerer_bestand_ist_kein_alarm(self):
        p = kap.plan([], cfg_probe(), 3, 1.0, PROBETAG)
        self.assertEqual((p["faellig"], p["puenktlich"]), (0, True))
        self.assertEqual(p["deckung_prozent"], 100.0)


class ReihenfolgeTest(unittest.TestCase):
    """EDF statt Klassenrang – sonst verhungert die Standard-Klasse."""

    def test_frueheste_frist_zuerst(self):
        seiten = ueberfaellig(4)
        # Eine Standard-Seite (90 Tage), die LÄNGST überfällig ist, muss vor
        # einer gerade fälligen saisonalen Seite drankommen.
        standard = {"slug": "standard-alt", "titel": "Aufräumen mit System",
                    "beschreibung": "", "keywords": ["Ordnung"], "pillar": "",
                    "faktencheck": PROBETAG - dt.timedelta(days=200)}
        saison = {"slug": "saison-gerade", "titel": "Heizung Winter saisonal",
                  "beschreibung": "", "keywords": ["Heizung"], "pillar": "",
                  "faktencheck": PROBETAG - dt.timedelta(days=30)}
        eintraege = kap.eintraege_bauen(seiten + [standard, saison],
                                        cfg_probe(), PROBETAG)
        nach_ziel = sorted(eintraege, key=lambda e: (e["ziel"], e["frist"]))
        self.assertEqual(nach_ziel[0]["slug"], "standard-alt")

    def test_keine_seite_verhungert_im_horizont(self):
        # Genug Kapazität: Jede Seite wird innerhalb ihres Horizonts erledigt.
        eingabe = ueberfaellig(10) + [
            {"slug": f"std-{i}", "titel": "Aufräumen mit System",
             "beschreibung": "", "keywords": ["Ordnung"], "pillar": "",
             "faktencheck": PROBETAG - dt.timedelta(days=30 + i * 5)}
            for i in range(10)]
        p = kap.plan(eingabe, cfg_probe(), 10, 1.0, PROBETAG)
        self.assertEqual(p["verletzungen_neu"], 0)
        self.assertTrue(p["rueckstand_abgebaut"])


class VorlaufTest(unittest.TestCase):
    """Arbeit beginnt vor der roten Kante (#912: Der Vorlauf ist die Heilung)."""

    def test_zieltag_liegt_vor_der_frist(self):
        eintrag = kap.eintraege_bauen(
            [{"slug": "x", "titel": "Heizung", "keywords": [],
              "faktencheck": PROBETAG - dt.timedelta(days=5)}],
            cfg_probe(), PROBETAG)[0]
        self.assertEqual((eintrag["frist"] - eintrag["ziel"]).days, 7)

    def test_ohne_vorlauf_bleibt_die_frist(self):
        cfg = cfg_probe()
        cfg["planung"]["vorlauf_tage"] = 0
        eintrag = kap.eintraege_bauen(
            [{"slug": "x", "titel": "Heizung", "keywords": [],
              "faktencheck": PROBETAG - dt.timedelta(days=5)}], cfg, PROBETAG)[0]
        self.assertEqual(eintrag["ziel"], eintrag["frist"])


class DossierSerialisierungTest(unittest.TestCase):
    """Der Lauf darf nicht am ersten echten Prüfdatum sterben.

    `faelligkeit()` trägt seit #912 die Frist als `datetime.date`. Das
    Dossier-JSON schreibt den ganzen Fälligkeitsblock mit – ohne Rückfall
    stirbt der ERSTE Lauf mit echtem Prüfdatum an „Object of type date is
    not JSON serializable“. Ein Fehler, der erst in Produktion auffällt,
    ist genau die Klasse, die diese Reparatur beenden soll.
    """

    def test_dossier_json_mit_frist_ist_serialisierbar(self):
        import json
        import tempfile
        art = {"slug": "probe", "titel": "Heizung Winter saisonal",
               "pfad": str(ROOT / "content" / "posts" / "probe" / "index.md"),
               "pillar": "energie", "keywords": [], "beschreibung": "",
               "faktencheck": PROBETAG - dt.timedelta(days=40)}
        faellig = ff.faelligkeit(art, cfg_probe(), PROBETAG)
        self.assertIsInstance(faellig["frist"], dt.date)
        dossier = {"erzeugt": "2026-10-29 10:00 UTC", "begriffe": [],
                   "kanaele": [], "treffer": [], "fehler": []}
        geo = ff.geo_reife(art)
        with tempfile.TemporaryDirectory() as tmp:
            alt = ff.DOSSIER_DIR
            ff.DOSSIER_DIR = tmp
            try:
                md = ff.dossier_schreiben(art, dossier, geo, faellig, [],
                                          trocken=False)
                self.assertTrue(md.endswith(".md"))
                daten = json.load(open(md[:-3] + ".json", encoding="utf-8"))
            finally:
                ff.DOSSIER_DIR = alt
        self.assertEqual(daten["faellig"]["frist"],
                         (PROBETAG - dt.timedelta(days=10)).isoformat())
        self.assertEqual(daten["faellig"]["restlaufzeit"], -10)


class EmpfehlungTest(unittest.TestCase):
    """Das Budget folgt dem Bedarf – mit Sockel, Limit und ehrlichem Nein."""

    def test_empfehlung_baut_rueckstand_fristgerecht_ab(self):
        emp = kap.empfohlenes_budget(ueberfaellig(60), cfg_probe(), 1.0, PROBETAG)
        self.assertTrue(emp["erreicht"])
        self.assertGreaterEqual(emp["budget"], emp["sockel"])
        self.assertLessEqual(emp["budget"], emp["limit"])
        self.assertTrue(emp["plan"]["rueckstand_abgebaut"])

    def test_empfehlung_bleibt_nie_unter_dem_sockel(self):
        emp = kap.empfohlenes_budget(ueberfaellig(1), cfg_probe(budget=3),
                                     1.0, PROBETAG)
        self.assertEqual(emp["budget"], 3)

    def test_strukturelle_unterdeckung_wird_ausgesprochen(self):
        emp = kap.empfohlenes_budget(ueberfaellig(200), cfg_probe(), 1.0, PROBETAG)
        self.assertFalse(emp["erreicht"])
        self.assertEqual(emp["budget"], emp["limit"])

    def test_automatik_schaltet_sich_ab_wenn_gewuenscht(self):
        cfg = cfg_probe()
        cfg["budget"]["auto_skalierung"] = False
        budget, info = ff.budget_fuer_lauf(cfg, ueberfaellig(60), PROBETAG)
        self.assertEqual(budget, 3)
        self.assertIn("Sockel", info["quelle"])

    def test_erstellungstakt_bleibt_beim_sockel(self):
        # `--neu` fragt „was ist neu?“, nicht „wie viel Rückstand ist da?“.
        budget, info = ff.budget_fuer_lauf(cfg_probe(), ueberfaellig(60),
                                           PROBETAG, auto_erlaubt=False)
        self.assertEqual(budget, 3)
        self.assertIn("Erstellungstakt", info["quelle"])

    def test_handbetrieb_gewinnt(self):
        budget, info = ff.budget_fuer_lauf(cfg_probe(), ueberfaellig(60),
                                           PROBETAG, explizit=1)
        self.assertEqual((budget, info["quelle"]), (1, "--max"))


class RepoZustandTest(unittest.TestCase):
    """Der ausgelieferte Zustand selbst muss gedeckt sein – sonst ist #912 zurück."""

    def setUp(self):
        self.cfg = ff.lade_config()
        self.artikel = ff.alle_artikel("alle")

    def test_ssot_nennt_alle_planungsgroessen(self):
        planung = self.cfg.get("planung") or {}
        budget = self.cfg.get("budget") or {}
        for feld in ("vorlauf_tage", "nachhol_frist_tage", "horizont_tage",
                     "min_deckung_prozent"):
            self.assertIsNotNone(planung.get(feld), f"planung.{feld} fehlt")
        for feld in ("auto_skalierung", "hartes_limit_pro_lauf",
                     "max_artikel_pro_lauf"):
            self.assertIsNotNone(budget.get(feld), f"budget.{feld} fehlt")
        self.assertTrue(budget["auto_skalierung"],
                        "Ein festes Budget unter wachsendem Bestand war #912")

    def test_kadenz_deckt_den_bestand_statisch(self):
        laeufe, hinweise = kap.laeufe_aus_workflow()
        self.assertIsNotNone(laeufe, f"Laufplan nicht lesbar: {hinweise}")
        bedarf = kap.bedarf_je_tag(self.artikel, self.cfg)
        vorgaben = kap.budget_vorgaben(self.cfg)
        mindest = int(kap.planung(self.cfg)["min_deckung_prozent"])
        # Der Alltag (Sockel), nicht die Spitze (hartes Limit), muss den
        # Bedarf decken – sonst ist die Kadenz nur rechnerisch grün.
        kapazitaet = kap.kapazitaet_je_tag(int(vorgaben["max_artikel_pro_lauf"]),
                                           laeufe)
        self.assertGreater(
            kapazitaet, bedarf * mindest / 100.0,
            f"Kadenz unterdeckt: {kapazitaet:.2f}/Tag gegen {bedarf:.2f}/Tag "
            f"Bedarf ({mindest} % verlangt) – #912 kommt zurück")
        spitze = kap.kapazitaet_je_tag(int(vorgaben["hartes_limit_pro_lauf"]),
                                       laeufe)
        self.assertGreaterEqual(spitze, kapazitaet,
                                "hartes Limit muss über dem Sockel liegen")

    def test_empfehlung_ist_im_korridor(self):
        laeufe, _ = kap.laeufe_aus_workflow()
        emp = kap.empfohlenes_budget(self.artikel, self.cfg, laeufe, PROBETAG)
        self.assertGreaterEqual(emp["budget"], emp["sockel"])
        self.assertLessEqual(emp["budget"], emp["limit"])

    def test_scorecard_nennt_die_ursache(self):
        quelle = (ROOT / "scripts" / "release_scorecard.py").read_text(encoding="utf-8")
        self.assertIn("faktenfrische_kapazitaet", quelle,
                      "Ohne Deckungsrechnung nennt das Ticket nur das Symptom")
        self.assertIn("Deckung", quelle)

    def test_workflow_faehrt_den_deckungs_nachweis(self):
        wf = (ROOT / ".github" / "workflows" / "faktenfrische.yml").read_text(
            encoding="utf-8")
        self.assertIn("faktenfrische_kapazitaet.py", wf)
        self.assertIn("--wache", wf)

    def test_kapazitaet_misst_ueber_die_eine_regel(self):
        quelle = (ROOT / "scripts" / "faktenfrische_kapazitaet.py").read_text(
            encoding="utf-8")
        self.assertIn("ff.faelligkeit", quelle,
                      "Eine eigene Fälligkeitsregel wäre eine zweite Wahrheit")
        for eigen in ("alter >=", "timedelta(days=30)", "timedelta(days=45)"):
            self.assertNotIn(eigen, quelle,
                             f"`{eigen}` riecht nach zweiter Intervallrechnung")


if __name__ == "__main__":
    unittest.main()
