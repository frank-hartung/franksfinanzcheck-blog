#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Einzigartigkeits-Vertrag zum BNetzA-Vorfall (#1027 / #1060) – eingefrorene
Evidenz und Dauerheilung.

WARUM DIESE TESTS EXISTIEREN (06.11.2026)
-----------------------------------------
Am 03.11.2026 meldete das Tagesaudit zwei kritische live↔live-Überlappungen
zwischen den Gas-Artikeln 08-10-sicher-heizen und den Preisgarantie-Artikeln
vom 08-12 und 08-24 (16 bzw. 5 geteilte 7-Wort-Phrasen aus demselben
BNetzA-Absatz), dazu fünf weitere Paare (live↔Entwurf und Entwurf↔Entwurf,
bis zu 34 geteilte Phrasen in `10-23-stromanbieter-wechseln` ↔
`10-26-gastarife-vergleichen`). Ursache war ein Hand-Commit (69f08c40,
02.11.2026), der denselben Absatz wörtlich in drei Live-Artikel eintrug.

Die Dauerheilung hat fünf Ebenen (#1060):

  A) Der Bestand ist umformuliert (die Gas-Artikel wurden eigenständig;
     08-12/08-24 waren zusätzlich unter Flesch 60 – jetzt ≥ R6).
  B) `check_uniqueness.aenderung_befunde` (DIE V4-Messung, importierte
     KRITISCH_AB) misst geplante Änderungen gegen den Bestand – live UND
     Entwurf, nur NEU/VERSTÄRKT, Altlasten frei. Der Publikations-Vertrag
     wertet das fail-closed aus (V4).
  C) `scripts/bestand_einzigartigkeit_gate.py` misst den DIFF jeder Änderung
     gegen die Git-Basis (link-check.yml vor der Linkprüfung) – hier selbst
     nicht noch einmal getestet (siehe test_bestand_einzigartigkeit_gate.py),
     nur seine Verdrahtung (Schritt-Ordnung, Basis-Token, Schwert-Import).

Jede Probe hier ist lesend und deterministisch; kein Artikel wird
überschrieben. Die Gas-Trio-Paare und die Entwurfs-Paare sind auf dem
Stand dieser Datei bei 0/1 bzw. 0/2 geteilten Phrasen – der Test schlägt
fehl, sobald jemand denselben Block wieder wörtlich einträgt.
"""
from __future__ import annotations

import os
import re
import unittest
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POSTS = os.path.join(WURZEL, "content", "posts")
sys.path.insert(0, os.path.join(WURZEL, "scripts"))

import check_uniqueness as cu  # noqa: E402
import readability_check  # noqa: E402

GAS_10 = "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas"
GAS_12 = "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026"
GAS_24 = "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"
UR_19 = "2026-10-19-urlaubskasse-clever-aufbessern"
UR_LM = "2026-11-02-last-minute-urlaubsangebote-sichern"
STROM_23 = "2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen"
GAS_26 = "2026-10-26-gastarife-vergleichen-vor-dem-herbst"

# Die im #1027-Audit dokumentierten 7-Wort-Phrasen (normierte Fassung) –
# eingefrorene Evidenz: genau diese Sequenzen hatte der BNetzA-Absatz.
DOKUMENTIERTE_PHRASEN = (
    "bei einer einseitigen preisaenderung koennen verbraucher grundsaetzlich",
    "grundsaetzlich ohne frist zum zeitpunkt der aenderung",
    "der vertrag endet am vortag der aenderung",
)


def _lese(slug: str) -> str:
    with open(os.path.join(POSTS, slug, "index.md"), encoding="utf-8") as fh:
        return fh.read()


def _bestand():
    return cu.lade_bestand()


def _paare(bestand, a, b):
    infos = {i["slug"]: i for i in bestand.values()}
    return len(cu.ngrams(infos[a]["body"], cu.PHRASE_LEN)
               & cu.ngrams(infos[b]["body"], cu.PHRASE_LEN))


class BestandHeiltTests(unittest.TestCase):
    """A) Der Bestand trägt den Vorfall nicht mehr – in beide Richtungen."""

    def test_gas_trio_paare_sind_unkritisch(self):
        bestand = _bestand()
        for a, b in ((GAS_10, GAS_12), (GAS_10, GAS_24), (GAS_12, GAS_24)):
            n = _paare(bestand, a, b)
            self.assertLess(
                n, cu.KRITISCH_AB,
                f"{a} ↔ {b}: {n} geteilte {cu.PHRASE_LEN}-Wort-Phrasen – der "
                f"BNetzA-Vorfall #1027 wäre wieder offen.")

    def test_entwurfspaare_der_vorfallsliste_sind_entschärft(self):
        bestand = _bestand()
        for a, b in ((UR_19, UR_LM), (STROM_23, GAS_26)):
            n = _paare(bestand, a, b)
            self.assertLess(
                n, cu.KRITISCH_AB,
                f"Entwurfspaar {a} ↔ {b}: {n} geteilte Phrasen – die Vorab-"
                f"Dopplung aus #1027 wäre wieder ungeklärt.")

    def test_heilung_traegt_keine_dokumentierte_vorfallsphrase(self):
        for slug in (GAS_10, GAS_12, GAS_24):
            norm = cu.norm(cu.clean_body(_lese(slug)))
            for phrase in DOKUMENTIERTE_PHRASEN:
                self.assertNotIn(
                    phrase, norm,
                    f"{slug}: dokumentierte Vorfallsphrase wieder gefunden – "
                    f"die Heilung wurde zurückgedreht: {phrase!r}")

    def test_gas_artikel_flesch_ueber_publish_schwelle(self):
        for slug, expect_min in ((GAS_12, readability_check.NEW_FLESCH_MIN),
                                 (GAS_24, readability_check.NEW_FLESCH_MIN)):
            artikel = readability_check.load_article(
                os.path.join(POSTS, slug, "index.md"))
            messwerte = readability_check.analyze(artikel)
            self.assertGreaterEqual(
                messwerte["flesch"], expect_min,
                f"{slug}: Flesch {messwerte['flesch']} < Publish-Schwelle "
                f"{expect_min} (R6) – der #1060-Auftrag verlangte ≥ 60.")
            self.assertGreaterEqual(
                messwerte["score"], 75,
                f"{slug}: Score {messwerte['score']} < Top-Level 75.")

    def test_die_dokumentierten_brueche_sind_weg(self):
        # de4d485f2-Klasse: zwei gebrochene Formulierungen aus der ersten
        # Umformulierung; beide gehören nicht mehr ins Repo.
        for slug in (GAS_10, GAS_12, GAS_24):
            text = _lese(slug)
            self.assertNotIn("Ihr Sonderkündigungsrecht", text,
                             f"{slug}: du-Artikel mit Sie-Form („Ihr “) – Bruch.")
            self.assertNotIn("Frist musst du dafür nicht warten", text,
                             f"{slug}: unfertige Umformulierung zurückgekehrt.")
        stand = _lese(GAS_24)
        self.assertNotRegex(
            stand, re.compile(r"Sonderrecht(?![a-zäöü])", re.I),
            "GAS_24: das erfundene „Sonderrecht“ ist zurück.")


class AenderungBefundeTests(unittest.TestCase):
    """B) V4: die Änderungs-Messung (erzeugt | verstärkt), sonst nichts."""

    PASSAGE = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
               "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung "
               "kuendigen; der Vertrag endet am Vortag der Aenderung.")
    PASSAGE_TEIL = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
                    "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung kuendigen.")
    EIGEN = ("Der eigene Text spricht über Heizkörper, Thermostate und den "
             "Blick auf die letzte Jahresrechnung des Hauses.")

    def _bestand(self):
        return {
            "a": {"slug": "2026-01-01-fremd-live",
                  "body": cu.clean_body(self.PASSAGE), "live": True,
                  "grund": "", "date": "2026-01-01T08:00:00Z"},
            "b": {"slug": "2026-01-02-fremd-entwurf",
                  "body": cu.clean_body(self.PASSAGE), "live": False,
                  "grund": "draft:true", "date": "2026-01-02T08:00:00Z"},
        }

    def test_alt_gleich_neu_erzeugt_keinen_befund(self):
        res = cu.aenderung_befunde(
            "2026-01-03-eigen", self.EIGEN + " " + self.PASSAGE,
            self.EIGEN + " " + self.PASSAGE, bestand=self._bestand())
        self.assertEqual([], res)

    def test_neu_doppelt_wird_erkannt(self):
        res = cu.aenderung_befunde(
            "2026-01-03-eigen", self.EIGEN,
            self.EIGEN + " " + self.PASSAGE, bestand=self._bestand())
        self.assertTrue(any("2026-01-01-fremd-live" in f for f in res), res)
        self.assertTrue(any("2026-01-02-fremd-entwurf" in f for f in res), res)

    def test_entwurfs_gegner_zaehlt_wie_live(self):
        # Vor der Veröffentlichung ist der Entwurf der richtige Zeitpunkt –
        # die Dopplung darf nicht erst im Tagesaudit nach dem Deploy auffallen.
        res = cu.aenderung_befunde(
            "2026-01-03-eigen", self.EIGEN,
            self.EIGEN + " " + self.PASSAGE, bestand=self._bestand())
        self.assertTrue(any("2026-01-02-fremd-entwurf" in f for f in res), res)

    def test_verstaerkung_ab_der_schwelle_wird_gemeldet(self):
        res = cu.aenderung_befunde(
            "2026-01-03-eigen", self.EIGEN + " " + self.PASSAGE_TEIL,
            self.EIGEN + " " + self.PASSAGE, bestand=self._bestand())
        self.assertTrue(any("2026-01-01-fremd-live" in f for f in res), res)

    def test_abschwaechung_ist_kein_befund(self):
        res = cu.aenderung_befunde(
            "2026-01-03-eigen", self.EIGEN + " " + self.PASSAGE,
            self.EIGEN + " " + self.PASSAGE_TEIL, bestand=self._bestand())
        self.assertEqual([], res)

    def test_befundtext_nennt_ab_welcher_schwelle_es_dopplung_ist(self):
        res = cu.aenderung_befunde(
            "2026-01-03-eigen", self.EIGEN,
            self.EIGEN + " " + self.PASSAGE, bestand=self._bestand())
        self.assertTrue(any(str(cu.KRITISCH_AB) in f for f in res), res)


class VorfallEvidenzTests(unittest.TestCase):
    """Die #1027-Evidenz ist eingefroren – der Vorfall darf nicht verblassen."""

    def test_dokumentierte_phrasen_sind_in_der_vorfallspassage_messbar(self):
        passage_grams = cu.ngrams(
            "Bei einer einseitigen Preisaenderung koennen Verbraucher "
            "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung kuendigen; "
            "der Vertrag endet am Vortag der Aenderung.", cu.PHRASE_LEN)
        for phrase in DOKUMENTIERTE_PHRASEN:
            self.assertIn(phrase, passage_grams,
                          f"Vorfallsphrase nicht messbar: {phrase}")

    def test_paar_klasse_schwelle_ist_inklusiv(self):
        self.assertEqual("kritisch", cu.paar_klasse(cu.KRITISCH_AB, False, False))
        self.assertEqual("unkritisch", cu.paar_klasse(cu.KRITISCH_AB - 1, False, False))
        self.assertEqual("entwurf", cu.paar_klasse(cu.KRITISCH_AB, True, False))
        self.assertEqual("entwurf", cu.paar_klasse(cu.KRITISCH_AB, False, True))
        self.assertEqual("ok", cu.paar_klasse(1, False, False))

    def test_echte_bestandsaenderung_vorgaenger_ist_still(self):
        # Live-Artikel UNVERÄNDERT: die Änderungs-Messung (alt == neu) meldet
        # nichts – Bestands-Altlasten sind kein Schreiber-Verstoß.
        bestand = _bestand()
        rohtext = _lese(GAS_12)
        self.assertEqual([], cu.aenderung_befunde(GAS_12, rohtext, rohtext,
                                                  bestand=bestand))

    def test_vorgaenger_kopierte_passage_wird_gemeldet(self):
        # Gegenprobe am echten Bestand: wer den 08-12-Absatz in einen anderen
        # Artikel einkopiert, wird VOR dem Schreiben angehalten.
        bestand = _bestand()
        infos = {i["slug"]: i for i in bestand.values()}
        eigen = ("Ein wirklich eigener Text über Katzen, Hypotheken und den "
                 "Herbst, der keine einzige Phrase mit dem Bestand teilt.")
        kopie = eigen + "\n\n" + infos[GAS_12]["body"]
        res = cu.aenderung_befunde("2026-11-06-testentwurf", eigen, kopie,
                                   bestand=bestand)
        self.assertTrue(any(GAS_12 in f for f in res),
                        "die Einkopie eines Bestandsartikels wird nicht gefunden – "
                        "die V4-Messung misst nicht (oder nicht gegen den Bestand).")


class VerdrahtungTests(unittest.TestCase):
    """C) Das Diff-Tor ist verdrahtet – und zwar VOR der Linkprüfung."""

    LINK_CHECK = os.path.join(WURZEL, ".github", "workflows", "link-check.yml")
    TOR = os.path.join(WURZEL, "scripts", "bestand_einzigartigkeit_gate.py")
    VERTRAG = os.path.join(WURZEL, "scripts", "publikations_vertrag.py")
    GOV = os.path.join(WURZEL, "scripts", "governance_contract.py")

    def _lesen(self, pfad):
        with open(pfad, encoding="utf-8") as fh:
            return fh.read()

    def test_link_check_diff_tor_step_vor_der_linkpruefung(self):
        yaml_text = self._lesen(self.LINK_CHECK)
        i_diff = yaml_text.find("Bestands-Einzigartigkeit (Diff-Tor")
        i_links = yaml_text.find("Interne Links prüfen")
        self.assertGreaterEqual(i_diff, 0, "Der Diff-Tor-Schritt fehlt im "
                                           "Qualitäts-Gate.")
        self.assertGreaterEqual(i_links, 0, "Interne Links fehlen.")
        self.assertLess(i_diff, i_links,
                        "Der Diff-Tor-Schritt steht HINTER der Linkprüfung – "
                        "ein doppelt erzeugter Artikel wäre beim Build schon "
                        "live-nah.")

    def test_link_check_basis_tokens_kommen_nicht_geraten(self):
        yaml_text = self._lesen(self.LINK_CHECK)
        for marker in ("pull_request.base.sha", "github.event.before", "HEAD~1",
                       "bestand_einzigartigkeit_gate.py"):
            self.assertIn(marker, yaml_text,
                          f"Der Diff-Tor-Schritt nennt `{marker}` nicht.")

    def test_diff_tor_importiert_schwert_statt_zweiter_schwelle(self):
        gate = self._lesen(self.TOR)
        self.assertIn("import check_uniqueness", gate)
        self.assertIn("KRITISCH_AB = cu.KRITISCH_AB", gate)
        self.assertNotRegex(gate, re.compile(r"(?m)^\s*KRITISCH_AB\s*=\s*[0-9]+"))

    def test_publikations_vertrag_wertet_v4_aus_fail_closed(self):
        vertrag = self._lesen(self.VERTRAG)
        self.assertIn("aenderung_befunde", vertrag)
        self.assertIn("Einzigartigkeit", vertrag)
        self.assertIn("V4", vertrag)

    def test_governance_pinnt_den_weg_c48(self):
        gov = self._lesen(self.GOV)
        self.assertIn("c48_diff_tor_bestands_einzigartigkeit", gov)
        self.assertIn('"bestand_einzigartigkeit_gate.py"', gov)
        self.assertIn("checks += c48_diff_tor_bestands_einzigartigkeit", gov)
        self.assertIn('"C48"', gov)

    def test_vorfalls_dokumentiert_im_tor_docstring(self):
        tor = self._lesen(self.TOR)
        for marker in ("#1027", "#1060", "69f08c40"):
            self.assertIn(marker, tor,
                          f"Das Tor dokumentiert den Vorfall nicht (`{marker}` "
                          f"fehlt im Docstring) – ein zukünftiger Leser weiß "
                          f"nicht, warum es existiert.")


if __name__ == "__main__":
    unittest.main()
