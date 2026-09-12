#!/usr/bin/env python3
"""Tests für den Alarm-Router (scripts/alert_router.py).

Hintergrund: Issue #272 – der Bot-Watchdog öffnete für jeden Befund
dasselbe Automations-Ticket, auch wenn nur ein Mensch ihn heilen konnte.
Dadurch war der automatische Schließpfad unmöglich und das Issue kehrte
täglich zurück. Diese Tests nageln die drei Regeln fest:

  1. Besitz-Trennung: menschliche Befunde öffnen kein Automations-Ticket.
  2. Schließpfad: ohne maschinellen Befund geht das Ticket zu – auch
     dann, wenn ein menschlicher Befund offen ist (die Sackgasse #272).
  3. Kadenz: ein offenes Ticket wird nicht täglich kommentiert, sondern
     genau einmal pro Eskalationsstufe (frühestens alle 72 h).

Läuft deterministisch ohne Netz (`python3 -m unittest discover -s scripts/tests`).
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import alert_router as ar  # noqa: E402

NOW = datetime.datetime(2026, 9, 12, 12, 0, tzinfo=datetime.timezone.utc)


def mensch(fid="pinterest-token", severity="P2", channel="pinterest-token",
           detail="HTTP 401", **kw):
    return ar.Finding(id=fid, title="Nur ein Mensch kann das heilen",
                      detail=detail, severity=severity, owner="human",
                      channel=channel, **kw)


def maschine(fid="cadence", severity="P1", **kw):
    return ar.Finding(id=fid, title="Kadenz nicht erfüllt", detail="0 von 2",
                      severity=severity, owner="auto", **kw)


class TestKlassifikation(unittest.TestCase):
    def test_besitzer_werden_getrennt(self):
        m, h = [], []
        findings = [mensch(), maschine()]
        m = ar.machine_findings(findings)
        h = ar.human_findings(findings)
        self.assertEqual([f.id for f in m], ["cadence"])
        self.assertEqual([f.id for f in h], ["pinterest-token"])

    def test_finding_ohne_kanal_bekommt_einen(self):
        self.assertEqual(ar.Finding(id="x", title="y", owner="auto").channel,
                         ar.GENERIC_CHANNEL)
        self.assertEqual(ar.Finding(id="x", title="y", owner="human").channel,
                         "human-action")

    def test_ungueltige_werte_werden_abgelehnt(self):
        with self.assertRaises(ValueError):
            ar.Finding(id="x", title="y", severity="P9")
        with self.assertRaises(ValueError):
            ar.Finding(id="x", title="y", owner="vielleicht")

    def test_json_rundlauf(self):
        f = mensch(evidence=("a", "b"), ladder=ar.PINTEREST_PARKED_LADDER
                   if hasattr(ar, "PINTEREST_PARKED_LADDER") else ((0, "Meldung"),))
        self.assertEqual(ar.Finding.from_dict(f.as_dict()), f)


class TestSchliesspfad(unittest.TestCase):
    """Die Kernregel: kein Ticket ohne Ausweg (#272)."""

    def test_menschlicher_befund_oeffnet_kein_ticket(self):
        d = ar.plan_generic([mensch()], None, NOW)
        self.assertEqual(d.action, "none")

    def test_maschinen_befund_oeffnet_ticket(self):
        d = ar.plan_generic([maschine()], None, NOW)
        self.assertEqual(d.action, "create")

    def test_ticket_geht_zu_wenn_nur_mensch_offen_ist(self):
        offen = ar.IssueRef(number=272, created_at=NOW - datetime.timedelta(days=1))
        d = ar.plan_generic([mensch()], offen, NOW)
        self.assertEqual(d.action, "close")
        self.assertEqual(d.issue, 272)

    def test_schliess_kommentar_nennt_den_menschkanal(self):
        text = ar.render_close_comment([mensch()], NOW)
        self.assertIn("pinterest-token", text)
        self.assertIn(ar.MARKER.format(channel=ar.GENERIC_CHANNEL), text)

    def test_kein_befund_kein_ticket(self):
        self.assertEqual(ar.plan_generic([], None, NOW).action, "none")


class TestKadenz(unittest.TestCase):
    def test_unveraenderter_befund_kommentiert_nicht_taeglich(self):
        f = maschine()
        issue = ar.IssueRef(number=1, created_at=NOW - datetime.timedelta(days=2),
                            body=ar.render_generic_body([f], [], NOW),
                            last_bot_comment_at=NOW - datetime.timedelta(hours=6))
        self.assertEqual(ar.plan_generic([f], issue, NOW).action, "none")

    def test_kadenz_erreicht_bringt_statuskommentar(self):
        f = maschine()
        issue = ar.IssueRef(number=1, created_at=NOW - datetime.timedelta(days=2),
                            body=ar.render_generic_body([f], [], NOW),
                            last_bot_comment_at=NOW - datetime.timedelta(hours=80))
        self.assertEqual(ar.plan_generic([f], issue, NOW).action, "comment")

    def test_geaenderte_befundmenge_aktualisiert_den_body(self):
        alt = ar.render_generic_body([maschine(fid="cadence")], [], NOW)
        issue = ar.IssueRef(number=1, body=alt,
                            created_at=NOW - datetime.timedelta(hours=1),
                            last_bot_comment_at=NOW)
        d = ar.plan_generic([maschine(fid="live-site")], issue, NOW)
        self.assertEqual(d.action, "update")

    def test_signatur_aendert_sich_mit_befund(self):
        self.assertNotEqual(ar.signature([maschine()]),
                            ar.signature([maschine(), mensch()]))


class TestEskalationsleiter(unittest.TestCase):
    def test_stufen_nach_tagen(self):
        self.assertEqual(ar.tier_for_age(0), 0)
        self.assertEqual(ar.tier_for_age(3), 1)
        self.assertEqual(ar.tier_for_age(7), 2)
        self.assertEqual(ar.tier_for_age(40), 3)

    def test_fachkanal_ohne_ticket_wird_eroeffnet(self):
        plans = ar.plan_channels([mensch()], {}, NOW, {})
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].action, "create")
        self.assertEqual(plans[0].channel, "pinterest-token")

    def test_abgedecktes_ticket_bleibt_still(self):
        issue = ar.IssueRef(number=246, created_at=NOW - datetime.timedelta(days=8),
                            last_tier=2, last_bot_comment_at=NOW - datetime.timedelta(days=1))
        plans = ar.plan_channels([mensch()], {"pinterest-token": issue}, NOW, {})
        self.assertEqual(plans[0].action, "none")
        self.assertEqual(plans[0].issue, 246)

    def test_eskalation_genau_einmal_pro_stufe(self):
        issue = ar.IssueRef(number=246, created_at=NOW - datetime.timedelta(days=9),
                            last_tier=0, last_bot_comment_at=NOW - datetime.timedelta(days=9))
        plans = ar.plan_channels([mensch()], {"pinterest-token": issue}, NOW, {})
        self.assertEqual(plans[0].action, "comment")
        self.assertGreaterEqual(plans[0].tier, 2)

        # Direkt danach: 72 h sind noch nicht rum → Ruhe.
        kommentiert = ar.IssueRef(number=246, created_at=NOW - datetime.timedelta(days=9),
                                  last_tier=0,
                                  last_bot_comment_at=NOW - datetime.timedelta(hours=2))
        self.assertEqual(ar.plan_channels([mensch()], {"pinterest-token": kommentiert},
                                          NOW, {})[0].action, "none")

    def test_eigene_leiter_pro_kanal(self):
        """Ein geparkter Kanal eskaliert langsamer (Wochen, nicht Tage)."""
        langsam = ((0, "Meldung"), (14, "Erinnerung"), (30, "Eskalation"))
        self.assertEqual(ar.tier_for_age(7, langsam), 0)
        self.assertEqual(ar.tier_for_age(20, langsam), 1)

    def test_once_kanal_meldet_nur_einmal(self):
        state = {"channels": {"tls-hint": {"done": True}}}
        plans = ar.plan_channels([mensch(channel="tls-hint", once=True)],
                                 {}, NOW, state)
        self.assertEqual(plans[0].action, "none")

    def test_geaenderte_fakten_aktualisieren_den_body(self):
        alt = mensch()
        neu = mensch(detail="HTTP 401 + Domain gesperrt", severity="P3")
        ticket = ar.IssueRef(number=246, created_at=NOW - datetime.timedelta(days=2),
                             body=ar.render_channel_body("pinterest-token", [alt], NOW))
        plans = ar.plan_channels([neu], {"pinterest-token": ticket}, NOW, {})
        self.assertEqual(plans[0].action, "update")
        self.assertIn("Domain gesperrt", plans[0].body)

    def test_fremdes_ticket_wird_nicht_umgeschrieben(self):
        ticket = ar.IssueRef(number=246, created_at=NOW - datetime.timedelta(days=2),
                             body="von Hand geschrieben – Hände weg!")
        plans = ar.plan_channels([mensch(severity="P3")], {"pinterest-token": ticket}, NOW, {})
        self.assertNotEqual(plans[0].action, "update")

    def test_kadenz_text_nutzt_die_leiter_des_kanals(self):
        langsam = ((0, "Meldung"), (14, "Erinnerung"), (30, "Eskalation"))
        body = ar.render_channel_body("pinterest-parked",
                                      [mensch(channel="pinterest-parked", ladder=langsam)], NOW)
        self.assertIn("14 Tage", body)
        self.assertIn("30 Tage", body)
        self.assertNotIn("Kanal-Review nach 14 Tagen", body)


class TestRouteAusfuehrung(unittest.TestCase):
    """Der Melder darf nie selbst zum Vorfall werden (Lehre aus #209/#227)."""

    def _client(self, script):
        def runner(args, timeout=60):
            key = " ".join(args)
            for muster, antwort in script.items():
                if muster in key:
                    return antwort
            return (0, "[]", "")
        return ar.GhClient(repo="o/r", runner=runner,
                           state_path=os.path.join(tempfile.mkdtemp(), "state.json"))

    def test_route_schliesst_ohne_maschinen_befund(self):
        client = self._client({
            "issue list": (0, json.dumps([{"number": 272, "title": "Alarm",
                                           "body": ar.MARKER.format(channel=ar.GENERIC_CHANNEL),
                                           "labels": [], "createdAt": "2026-09-11T00:00:00Z"}]), ""),
            "issue close": (0, "", ""),
            "issue comment": (0, "", ""),
            "label create": (0, "", ""),
            "comments": (0, "", ""),
        })
        report = ar.route([mensch()], client, now=NOW)
        self.assertEqual(report["actions"][0]["action"], "close")
        self.assertEqual(report["actions"][0]["issue"], 272)

    def test_route_legt_fachkanal_an(self):
        client = self._client({
            "issue list": (0, "[]", ""),
            "issue create": (0, "https://github.com/o/r/issues/300\n", ""),
            "label create": (0, "", ""),
        })
        report = ar.route([mensch()], client, now=NOW)
        create = [a for a in report["actions"] if a["action"] == "create"]
        self.assertEqual(len(create), 1)
        self.assertEqual(create[0]["channel"], "pinterest-token")
        self.assertEqual(create[0]["issue"], 300)

    def test_fehlgeschlagene_aktion_wird_nicht_als_erledigt_vermerkt(self):
        """Ein nicht zugestellter Kommentar darf die Eskalationsstufe nicht verbrauchen."""

        def runner(args, timeout=60):
            key = " ".join(args)
            if "issue list" in key:
                return (0, json.dumps([{"number": 246, "title": "Token",
                                        "body": ar.MARKER.format(channel="pinterest-token"),
                                        "labels": [], "createdAt": "2026-08-20T00:00:00Z"}]), "")
            return (1, "", "boom")          # comment/create/edit schlagen fehl

        client = ar.GhClient(repo="o/r", runner=runner,
                             state_path=os.path.join(tempfile.mkdtemp(), "state.json"))
        ar.route([mensch()], client, now=NOW)
        with open(client.state_path, encoding="utf-8") as f:
            state = json.load(f)
        kanal = state.get("channels", {}).get("pinterest-token", {})
        self.assertNotIn("last_tier", kanal)

    def test_gh_fehler_lassen_den_lauf_gruen(self):
        client = self._client({"issue list": (1, "", "boom"),
                               "issue create": (1, "", "boom")})
        report = ar.route([maschine()], client, now=NOW)
        self.assertFalse(report["ok"])
        self.assertTrue(report["errors"])          # sichtbar im Bericht …
        self.assertIsInstance(report["actions"], list)  # … aber kein Absturz

    def test_ticket_wird_ohne_label_per_marker_gefunden(self):
        """Label verloren (eingeschränktes Token) → kein zweites Ticket."""
        body = ar.render_channel_body("pinterest-parked", [mensch()], NOW)

        def runner(args, timeout=60):
            key = " ".join(args)
            if "--label" in key:
                return (0, "[]", "")           # per Label: nichts gefunden
            if "issue list" in key:
                return (0, json.dumps([{"number": 279, "title": "geparkt", "body": body,
                                        "labels": [], "createdAt": "2026-09-12T00:00:00Z"}]), "")
            return (0, "[]", "")

        client = ar.GhClient(repo="o/r", runner=runner,
                             state_path=os.path.join(tempfile.mkdtemp(), "state.json"))
        ticket = client.find_ticket("pinterest-parked")
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.number, 279)
        # und der Router eröffnet deshalb KEIN zweites Ticket:
        report = ar.route([mensch(channel="pinterest-parked")], client, now=NOW)
        self.assertNotIn("create", [a["action"] for a in report["actions"]])

    def test_zustand_wird_geschrieben(self):
        client = self._client({
            "issue list": (0, "[]", ""),
            "issue create": (0, "https://github.com/o/r/issues/301\n", ""),
            "label create": (0, "", ""),
        })
        ar.route([mensch()], client, now=NOW)
        with open(client.state_path, encoding="utf-8") as f:
            state = json.load(f)
        self.assertEqual(state["channels"]["pinterest-token"]["ticket"], 301)


if __name__ == "__main__":
    unittest.main(verbosity=2)
