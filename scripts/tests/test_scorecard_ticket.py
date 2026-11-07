#!/usr/bin/env python3
"""Regressionen für den Scorecard-Ticket-Text (#912, 03.11.2026).

Am 02.11.2026 meldete das Ticket bei jedem `faktenalter`-Fund „Kadenz, kein
Inhaltsbefund“ und „danach schließt sich dieses Ticket selbst“. Beides war
falsch: F1 war grün (0 überfällig, 146 % Deckung), F4 blockierte zehn
Artikel. Diese Tests frieren ein:

  * Ursache je Check – nicht je Dimension.
  * F4 nennt Zahl, Frist, Arbeitsdatei und Entscheidungsbefehl.
  * Die Kadenz-Erzählung erscheint nur, wenn F1 wirklich blockiert.
  * Der Schließpfad wird je Ursache benannt; kein Selbstschluss für F4.
  * Grün beschuldigt niemanden und erfindet keine Ursache.

Lauf: python3 -m unittest scripts.tests.test_scorecard_ticket
"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import scorecard_ticket as ticket  # noqa: E402

KAPAZITAET = {"faellig": 3, "ueberfaellig": 0, "deckung_prozent": 146,
              "bedarf_je_tag": 2.73, "bedarf_je_woche": 19.1,
              "kapazitaet_je_tag": 4.0, "budget": 4, "laeufe_je_tag": 1.0,
              "abbau_tage": 0, "nachhol_frist_tage": 7}
BEFUNDLAGE = {"offen": 57, "seiten": 13, "live_befunde": 42, "live_seiten": 10,
              "aeltester_tage": 4, "frist_tage": 14, "ueber_frist": 0,
              "ueberholt": 21, "nicht_entscheidbar": 0}


def artikel(urteil="blockiert", checks=("F4-fachbefund",), dim="faktenalter"):
    return {"urteil": urteil, "risikoklasse": "standard",
            "dimensionen": {dim: "blockiert", "technik": "bestanden"},
            "checks": [{"check": c, "dimension": dim, "wirkung": "blockiert"}
                       for c in checks]}


def state(ursachen, befundlage=None, kapazitaet=None, artikel_map=None):
    return {"artikel": artikel_map or {"a": artikel()},
            "ursachen": ursachen, "befundlage": befundlage or BEFUNDLAGE,
            "kapazitaet": kapazitaet or KAPAZITAET}


F4_URSACHE = [{"check": "F4-fachbefund", "dimension": "faktenalter",
               "wirkung": "blockiert", "entscheidung": "human", "anzahl": 1}]
F1_URSACHE = [{"check": "F1-faktenfrische", "dimension": "faktenalter",
               "wirkung": "blockiert", "entscheidung": "auto", "anzahl": 1}]


class UrsacheTests(unittest.TestCase):
    def test_f4_wird_als_ursache_genannt_und_nicht_als_kadenz(self):
        body = ticket.ticket_body(state(F4_URSACHE))
        self.assertIn("offene Fachbefunde (F4)", body)
        self.assertIn("57** offene Fachbefunde", body)
        self.assertIn("ältester", body)
        self.assertIn("Frist **14** Tage", body)
        self.assertIn("BEFUND-AKTE.md", body)
        self.assertIn("--entscheiden", body)
        self.assertIn("Ein Prüfdatum schließt keinen Fachbefund", body)
        self.assertNotIn("Kadenz der Faktenfrische (F1)", body)
        self.assertNotIn("Deckung **146 %**", body)
        self.assertNotIn("kein Inhaltsbefund", body)

    def test_f1_allein_erklaert_die_kadenz(self):
        body = ticket.ticket_body(state(F1_URSACHE))
        self.assertIn("Kadenz der Faktenfrische (F1)", body)
        self.assertIn("Deckung **146 %**", body)
        self.assertIn("F1 schließt sich", body)
        self.assertNotIn("offene Fachbefunde (F4)", body)
        self.assertNotIn("BEFUND-AKTE.md", body)

    def test_beide_ursachen_sind_getrennt_benannt(self):
        body = ticket.ticket_body(state(F4_URSACHE + F1_URSACHE))
        self.assertIn("offene Fachbefunde (F4)", body)
        self.assertIn("Kadenz der Faktenfrische (F1)", body)
        self.assertIn("F4 schließt **nur**", body)
        self.assertIn("F1 schließt sich", body)

    def test_einzelfund_ohne_kadenz_und_ohne_f4(self):
        ursache = [{"check": "A3-offenlegung", "dimension": "affiliate",
                    "wirkung": "blockiert", "entscheidung": "auto", "anzahl": 1}]
        body = ticket.ticket_body(state(ursache, artikel_map={
            "a": artikel(checks=("A3-offenlegung",), dim="affiliate")}))
        self.assertIn("fachliche Einzelfunde", body)
        self.assertNotIn("Kadenz der Faktenfrische (F1)", body)
        self.assertNotIn("offene Fachbefunde (F4)", body)

    def test_f4_eskaliert_ueber_der_frist(self):
        lage = dict(BEFUNDLAGE, ueber_frist=3)
        body = ticket.ticket_body(state(F4_URSACHE, befundlage=lage))
        self.assertIn("Eskalation", body)
        self.assertIn("Herausgeber", body)

    def test_tabelle_nennt_die_blockierende_pruefung(self):
        body = ticket.ticket_body(state(F4_URSACHE))
        self.assertIn("| Artikel | Urteil | Risikoklasse | Blockierende Prüfung(en) |",
                      body)
        self.assertIn("`F4-fachbefund`", body)


class EhrlichkeitsTests(unittest.TestCase):
    def test_gruen_ohne_ursache_und_ohne_schuld(self):
        body = ticket.ticket_body(
            {"artikel": {"a": {"urteil": "freigabe-reif",
                               "dimensionen": {}, "checks": []}},
             "ursachen": [], "befundlage": {}, "kapazitaet": {}},
            ergebnis="success")
        self.assertIn("Bestand grün", body)
        self.assertIn("frei von blockierenden Funden", body)
        self.assertNotIn("Blockierende Prüfung", body)

    def test_marker_ist_im_ticket(self):
        body = ticket.ticket_body(state(F4_URSACHE))
        self.assertNotIn("wache-id", body)   # Marker setzt der Aufrufer
        self.assertIn("wache-id: release-scorecard", ticket.MARKER)

    def test_nicht_beweisbare_befundlage_ist_kein_gruen(self):
        lage = {"nicht_beweisbar": "Ledger nicht lesbar"}
        body = ticket.ticket_body(state(F4_URSACHE, befundlage=lage))
        self.assertIn("nicht beweisbar", body)
        self.assertIn("Ledger nicht lesbar", body)
        self.assertNotIn("0** offene Fachbefunde", body)

    def test_kein_selbstschluss_bei_f4(self):
        body = ticket.ticket_body(state(F4_URSACHE))
        self.assertNotIn("danach schließt sich dieses Ticket selbst", body)
        self.assertIn("F4 schließt **nur** durch dokumentierte menschliche "
                      "Entscheidungen", body)


class WorkflowVertragTests(unittest.TestCase):
    def test_workflow_nutzt_die_getestete_funktion(self):
        text = (ROOT / ".github" / "workflows" / "release-scorecard.yml").read_text(
            encoding="utf-8")
        self.assertIn("scripts/scorecard_ticket.py", text)
        self.assertNotIn("python3 - <<'PY'", text)

    def test_akte_ist_im_faktenfrische_workflow_verdrahtet(self):
        text = (ROOT / ".github" / "workflows" / "faktenfrische.yml").read_text(
            encoding="utf-8")
        self.assertIn("faktenfrische_befund_akte.py --schreiben", text)
        self.assertIn("faktenfrische_befund_akte.py --wache", text)
        self.assertIn("BEFUND-AKTE.md", text)
        self.assertIn("gh issue close", text)



class StaleStateSchutzTests(unittest.TestCase):
    """#1098: Pipeline-Ausfall ist kein inhaltlicher Bestandbefund."""

    def test_uebersprungene_messung_liest_altes_siegel_nicht_als_rot(self):
        state = {"generated_at": "2026-01-01T00:00:00Z", "artikel": {
            "a": {"urteil": "blockiert", "checks": [{"check": "T6", "wirkung": "blockiert"}]}}}
        body = ticket.ticket_body(state, ergebnis="skipped")
        self.assertIn("Messung nicht beweisbar", body)
        self.assertIn("historisch", body)
        self.assertNotIn("| `a` |", body)

    def test_fremder_oder_alter_commit_ist_kein_aktueller_befund(self):
        state = {"commit": "alt", "generated_at": "2026-11-07T10:00:00Z",
                 "artikel": {"a": {"urteil": "blockiert", "checks": []}}}
        body = ticket.ticket_body(state, erwarteter_commit="neu",
                                  frisch_ab="2026-11-07T09:00:00Z")
        self.assertIn("Messung nicht beweisbar", body)
        self.assertIn("gehört nicht zu diesem Lauf", body)
        body2 = ticket.ticket_body(state, erwarteter_commit="alt",
                                   frisch_ab="2026-11-07T11:00:00Z")
        self.assertIn("Messung nicht beweisbar", body2)

    def test_ursachen_fingerabdruck_ist_zeitunabhaengig_und_aenderungssensitiv(self):
        a = {"generated_at": "gestern", "artikel": {
            "x": {"urteil": "blockiert", "checks": [{"check": "F4-fachbefund", "wirkung": "blockiert"}]}}}
        b = copy.deepcopy(a); b["generated_at"] = "heute"
        self.assertEqual(ticket.ursachen_fingerabdruck(a), ticket.ursachen_fingerabdruck(b))
        b["artikel"]["x"]["checks"][0]["check"] = "T6-textverstaendnis"
        self.assertNotEqual(ticket.ursachen_fingerabdruck(a), ticket.ursachen_fingerabdruck(b))
        self.assertNotEqual(ticket.ursachen_fingerabdruck(a, "failure"),
                            ticket.ursachen_fingerabdruck(a, "skipped"))

    def test_werkzeugfehler_im_siegel_bleibt_sichtbar(self):
        state = {"artikel": {}, "tool_fehler": {"sammlung": "ausgefallen"}}
        body = ticket.ticket_body(state, ergebnis="failure")
        self.assertIn("Messung nicht beweisbar", body)
        self.assertIn("sammlung", body)
        self.assertIn("ausgefallen", body)


if __name__ == "__main__":
    unittest.main()
