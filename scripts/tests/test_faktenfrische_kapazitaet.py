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
  6. #1023: Das C45-Urteil prüft den PLAN, den der Lauf wirklich fährt
     (bei Auto-Skalierung das empfohlene Budget), nicht den Sockel als
     vermeintlichen Alltag. Reserve unter dem harten Limit ist Pflicht;
     Dauer-Spitzenbetrieb und strukturelle Unterdeckung sind rot.

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
                    "horizont_tage": 120, "min_deckung_prozent": 110},
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
        p = kap.plan(ueberfaellig(60), cfg_probe(), 3, 2 / 7, PROBETAG,
                     lauftage=kap.lauf_tage(["40 4 * * 2,4"], PROBETAG, 120))
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
                daten = json.loads(Path(md[:-3] + ".json").read_text(encoding="utf-8"))
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


class C45UrteilTest(unittest.TestCase):
    """Das Urteil der Deckungswache ist rein und prüfbar (C45, #1023).

    Der Vertrag darf nicht eine zweite, abweichende Schwelle erfinden.
    Diese Probe hält die drei Zustände fest, die #1023 ausgelöst haben:
    Plan mit Reserve (grün), Dauer-Spitzenbetrieb (rot) und strukturelle
    Unterdeckung (rot).
    """

    def basis(self, **overrides):
        werte = {
            "seiten": 112, "bedarf": 2.73, "mindest": 110, "laeufe": 1.0,
            "sockel": 4, "limit": 10, "budget": 4,
            "kapazitaet": 4.0, "kapazitaet_spitze": 10.0,
            "auto": True, "empfehlung_erreicht": True,
            "plan_puenktlich": True, "plan_rueckstand_abgebaut": True,
        }
        werte.update(overrides)
        return werte

    def test_plan_mit_reserve_ist_gruen(self):
        self.assertEqual(kap.c45_urteil(self.basis()), [])

    def test_dauer_spitzenbetrieb_ist_rot(self):
        funde = kap.c45_urteil(self.basis(budget=10, kapazitaet=10.0))
        self.assertTrue(any("Dauer-Spitzenbetrieb" in f for f in funde))

    def test_unterdeckung_ist_rot(self):
        funde = kap.c45_urteil(self.basis(budget=3, kapazitaet=3.0))
        self.assertTrue(any("unterdeckt" in f for f in funde))

    def test_strukturelle_unterdeckung_ist_rot(self):
        funde = kap.c45_urteil(self.basis(
            budget=10, kapazitaet=10.0, empfehlung_erreicht=False))
        self.assertTrue(any("strukturell" in f for f in funde))

    def test_fester_sockel_ist_pruefbar(self):
        # Ohne Auto-Skalierung ist der Sockel der Plan – hier mit Reserve.
        self.assertEqual(kap.c45_urteil(self.basis(auto=False)), [])

    def test_sockel_ueber_limit_ist_rot(self):
        funde = kap.c45_urteil(self.basis(
            sockel=11, limit=10, budget=11, kapazitaet=11.0,
            kapazitaet_spitze=10.0))
        self.assertTrue(any("Ungültiger Korridor" in f for f in funde))

    def test_fristbruch_ist_rot(self):
        funde = kap.c45_urteil(self.basis(plan_puenktlich=False))
        self.assertTrue(any("Frist" in f for f in funde))

    def test_zu_kleines_limit_ist_rot(self):
        funde = kap.c45_urteil(self.basis(
            bedarf=20.0, budget=10, kapazitaet=10.0, kapazitaet_spitze=10.0))
        self.assertTrue(any("strukturell" in f for f in funde))

    def test_spitzenlast_ist_rot(self):
        # 04.11.2026 (#1039): Der Stichtag war grün, drei Wochen später
        # standen 23 Seiten mit demselben Prüfdatum gemeinsam zu spät.
        funde = kap.c45_urteil(self.basis(
            spitze_stichtag="2026-11-26", spitze_offen=37,
            spitze_puenktlich=False))
        self.assertTrue(any("Spitzenlast" in f for f in funde))

    def test_spitzenlast_ohne_befund_bleibt_gruen(self):
        # Gegenprobe: Ein Bündeltag, den der Plan trägt, ist kein Befund.
        # Ohne diese Probe würde „Spitzenlast“ bei jeder Zeile anschlagen.
        self.assertEqual(kap.c45_urteil(self.basis(
            spitze_stichtag="2026-11-26", spitze_offen=0,
            spitze_puenktlich=True)), [])

    def test_spitzenlast_ohne_messung_ist_kein_freibrief(self):
        # Fehlt die Messung ganz (alter Aufrufer), darf das Urteil nicht
        # stillschweigend „grün“ bedeuten – es prüft dann nur den Stichtag.
        # Das ist Absicht: die Messung selbst ist die Pflicht (s. u.).
        self.assertEqual(kap.c45_urteil(self.basis()), [])

    def test_jeder_stichtag_wird_gebunden_geprueft(self):
        # Der Vertrag muss den Bündeltag MITMESSEN, nicht nur den Stichtag.
        import governance_contract as gc
        zahlen, fehler = gc._c45_deckung()
        self.assertIsNone(fehler, fehler)
        # Ohne Befund fehlt `spitze_stichtag` – aber nie der Beleg, DASS
        # gemessen wurde. Sonst wäre „nicht geprüft“ von „grün“ nicht zu
        # unterscheiden (C33).
        self.assertIn("spitze_geprueft", zahlen)
        self.assertGreater(int(zahlen["spitze_geprueft"]), 0,
                           "kein einziger Bündeltag geprüft – die Messung fehlt")

    def test_deckung_liefert_das_urteil(self):
        import governance_contract as gc
        zahlen, fehler = gc._c45_deckung()
        self.assertIsNone(fehler, fehler)
        self.assertIn("urteil", zahlen)
        self.assertEqual(zahlen["urteil"], [])


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

    def test_kadenz_deckt_den_bestand(self):
        laeufe, hinweise = kap.laeufe_aus_workflow()
        self.assertIsNotNone(laeufe, f"Laufplan nicht lesbar: {hinweise}")
        bedarf = kap.bedarf_je_tag(self.artikel, self.cfg)
        vorgaben = kap.budget_vorgaben(self.cfg)
        mindest = int(kap.planung(self.cfg)["min_deckung_prozent"])
        sockel = int(vorgaben["max_artikel_pro_lauf"])
        limit = int(vorgaben["hartes_limit_pro_lauf"])
        auto = bool(vorgaben.get("auto_skalierung"))
        # Der Plan, den der Lauf wirklich fährt: bei Auto-Skalierung das
        # empfohlene Budget (Sockel als Untergrenze), sonst der Sockel.
        empfehlung = kap.empfohlenes_budget(self.artikel, self.cfg, laeufe,
                                            PROBETAG)
        budget = max(sockel, int(empfehlung["budget"])) if auto else sockel
        kapazitaet = kap.kapazitaet_je_tag(budget, laeufe)
        self.assertGreater(
            kapazitaet, bedarf * mindest / 100.0,
            f"Kadenz unterdeckt: {kapazitaet:.2f}/Tag gegen {bedarf:.2f}/Tag "
            f"Bedarf ({mindest} % verlangt) – #912 kommt zurück")
        # Reserve: Der Plan darf das harte Limit nicht vollständig
        # verbrauchen – sonst ist die Kadenz nur im Dauer-Spitzenbetrieb
        # grün (#1023).
        self.assertLess(budget, limit,
                        "Der Plan verbraucht das harte Limit vollständig – "
                        "Dauer-Spitzenbetrieb statt Reserve (#1023)")
        self.assertTrue(empfehlung["erreicht"],
                        "Auch das harte Limit baut den Rückstand nicht "
                        "fristgerecht ab (#912)")
        spitze = kap.kapazitaet_je_tag(limit, laeufe)
        self.assertGreaterEqual(spitze, kapazitaet,
                                "hartes Limit muss über dem Plan liegen")

    def test_vollrueckstand_nach_97_tagen_behaelt_reserve(self):
        """Die reale +97-Tage-Falle vom 04.11.2026 bleibt geschlossen."""
        stichtag = dt.date(2027, 2, 9)  # 04.11.2026 + 97 Tage
        laeufe, hinweise = kap.laeufe_aus_workflow()
        self.assertIsNotNone(laeufe, f"Laufplan nicht lesbar: {hinweise}")
        horizont = int(kap.planung(self.cfg)["horizont_tage"])
        lauftage = kap.lauftage_aus_workflow(stichtag, horizont)
        self.assertIsNotNone(lauftage, "Der echte Laufkalender fehlt")
        emp = kap.empfohlenes_budget(self.artikel, self.cfg, laeufe, stichtag,
                                     lauftage=lauftage)
        plan = emp["plan"]
        self.assertTrue(emp["erreicht"],
                        "Das harte Limit baut den Vollrückstand nicht fristgerecht ab")
        self.assertTrue(plan["puenktlich"], "Neue oder Folgefrist gerissen")
        self.assertTrue(plan["rueckstand_abgebaut"],
                        "Der Alt-Rückstand bleibt über die Nachholfrist")
        self.assertLessEqual(plan["abbau_tage"],
                             int(kap.planung(self.cfg)["nachhol_frist_tage"]))
        self.assertLess(emp["budget"], emp["limit"],
                        "Der Vollrückstand verbraucht die gesamte Reserve")
        bedarf = kap.bedarf_je_tag(self.artikel, self.cfg, stichtag)
        mindest = int(kap.planung(self.cfg)["min_deckung_prozent"])
        self.assertGreater(kap.kapazitaet_je_tag(emp["budget"], laeufe),
                           bedarf * mindest / 100.0)

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
