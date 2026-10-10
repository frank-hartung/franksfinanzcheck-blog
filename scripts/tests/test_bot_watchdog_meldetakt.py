#!/usr/bin/env python3
"""Tests für den Meldetakt des Bot-Watchdogs (Dauerheilung #676, Teil 2).

TEIL 1 (PR #686) hat die Auslieferung vor das Siegel gestellt und den Befund
`deploy-blockade` eingeführt. Geblieben ist die LATENZ: Der Watchdog lief
einmal täglich um 08:30 UTC, zwischen dem Beginn eines Ausfalls und seiner
Entdeckung lagen bis zu 23,5 Stunden. Der gesamte Ausfall vom 09.10.2026
(19 h 38 min ohne öffentliche Auslieferung) fand zwischen zwei Watchdog-Läufen
statt – und als das Ticket offen war, rechnete die Eskalationsleiter in Tagen
(0/3/7/14), meldete also während der 19 Stunden gar nichts.

Diese Tests frieren vier Verträge ein (Governance C35):

  1. TAKT     – die Wache misst die Ausfall-Klasse stündlich (:05) und der
                Voll-Lauf bleibt; der Ausfall-Takt ist read-only.
  2. MESSUNG  – eine übersprungene Prüfung ist kein Grün (C2), und eine
                Blockade wird auch ohne 404 zum Befund.
  3. MELDETAKT– der Router meldet einen laufenden Ausfall nach 0/1/6/24 h und
                danach alle 24 h – nicht 24× am Tag und nicht alle 72 h.
  4. GRENZE   – chronische Befunde behalten ihre 72-h-Kadenz (#272). Ein
                akuter Takt für alles wäre Taktfeuer, kein Meldetakt.

Läuft deterministisch ohne Netz: gh- und HTTP-Aufrufe sind ersetzt.
"""
from __future__ import annotations

import datetime
import os
import sys
import unittest
from unittest import mock

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import alert_router as ar  # noqa: E402
import bot_watchdog as bw  # noqa: E402
import governance_contract as gc  # noqa: E402

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKFLOW = os.path.join(BLOG_DIR, ".github", "workflows", "bot-watchdog.yml")

AUSFALL_CRON = "5 * * * *"
VOLL_CRON = "30 8 * * *"
SCORECARD_SCHRITT = "49. Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)"


def _workflow_text() -> str:
    with open(WORKFLOW, encoding="utf-8") as f:
        return f.read()


def _workflow() -> dict:
    """PyYAML liest den Schlüssel `on:` als boolesches True (YAML 1.1)."""
    return yaml.safe_load(_workflow_text())


def _ausloeser() -> dict:
    wf = _workflow()
    return wf["on"] if "on" in wf else wf[True]


def _schritte() -> list[dict]:
    return _workflow()["jobs"]["watchdog"]["steps"]


def _schritt(name_teil: str) -> dict:
    for st in _schritte():
        if name_teil in (st.get("name") or ""):
            return st
    raise AssertionError(f"Schritt ‚{name_teil}‘ fehlt in bot-watchdog.yml")


def blockade(akut: bool = True) -> ar.Finding:
    return ar.Finding(
        id="deploy-blockade", title="Auslieferung blockiert (Live-Stand eingefroren)",
        detail=f"blockierender Schritt: „{SCORECARD_SCHRITT}“", severity="P1",
        owner="auto", channel=ar.GENERIC_CHANNEL, akut=akut,
        next_step="scripts/watchdog_recovery.py --live-site")


def chronisch() -> ar.Finding:
    """Ein Befund ohne Ausfall-Charakter: 72-h-Kadenz (#272)."""
    return ar.Finding(id="pinterest-report", title="Pinterest-Report veraltet",
                      detail="Fingerabdruck 30 h alt", severity="P2", owner="auto",
                      channel=ar.GENERIC_CHANNEL, next_step="pinterest_check.py --fix")


class TaktImWorkflowTestCase(unittest.TestCase):
    """Vertrag 1: zwei Takte in einem Workflow – und der kleine ist read-only."""

    def test_ausfalltakt_laeuft_stuendlich_zur_minute_fuenf(self) -> None:
        crons = [c["cron"] for c in _ausloeser()["schedule"]]
        self.assertIn(AUSFALL_CRON, crons)
        self.assertIn(VOLL_CRON, crons)

    def test_takt_umschalter_ist_die_einzige_wahrheit(self) -> None:
        takt = [st for st in _schritte() if st.get("id") == "takt"]
        self.assertEqual(len(takt), 1, "genau ein Schritt darf den Takt bestimmen")
        self.assertIn(AUSFALL_CRON, takt[0]["run"])

    def test_ausfalltakt_ist_verdrahtet(self) -> None:
        self.assertIn("--triage", _schritt("Watchdog-Prüfungen")["run"])
        self.assertIn("--triage", _schritt("Nachmessung (geheilte Befunde")["run"])
        self.assertIn("--triage", _schritt("Alarm-Routing")["run"])

    def test_teure_und_schreibende_schritte_laufen_nur_im_voll_lauf(self) -> None:
        """Ein read-only-Takt, der Hugo baut oder nach main committet, ist keiner."""
        for name in gc.C35_NUR_VOLL_LAUF:
            bedingung = _schritt(name).get("if") or ""
            self.assertIn(gc.C35_TAKT_ANKER, bedingung,
                          f"Schritt ‚{name}‘ läuft ungetaktet – #676")

    def test_heilung_und_nachmessung_laufen_in_beiden_takten(self) -> None:
        """Der Punkt des Ausfall-Takts: innerhalb einer Stunde heilen."""
        for name in ("Deploy-Catchup bei nicht live-gegangenem Artikel",
                     "Nachmessung (geheilte Befunde"):
            bedingung = _schritt(name).get("if") or ""
            self.assertNotIn(gc.C35_TAKT_ANKER, bedingung,
                             f"Schritt ‚{name}‘ darf nicht auf den Voll-Lauf "
                             "beschränkt sein – sonst heilt der Ausfall-Takt nie")

    def test_dispatch_kann_den_takt_waehlen(self) -> None:
        eingaben = _ausloeser()["workflow_dispatch"]["inputs"]
        self.assertIn("takt", eingaben)
        self.assertEqual(
            set(eingaben["takt"]["options"]), {"auto", "triage", "voll"})


class UebersprungeneMessungTestCase(unittest.TestCase):
    """Vertrag 2 (C2): Was der Ausfall-Takt nicht misst, ist kein Grün."""

    def test_triage_skip_liest_sich_nicht_als_urteil(self) -> None:
        for token in ("OK", "WARN", "FAIL"):
            self.assertNotIn(token, bw.TRIAGE_SKIP)
        self.assertIn("ÜBERSPRUNGEN", bw.TRIAGE_SKIP)

    def test_ausfalltakt_misst_nur_die_ausfallklasse(self) -> None:
        verboten = ("check_tls", "check_affiliate_integrity", "workflow_run_evidence",
                    "check_pinterest_channel", "pinterest_domain_block",
                    "check_content_reserve", "check_pinterest_duplicate",
                    "check_pinterest_report_freshness", "build_bilanz")

        def _verboten(name):
            def _aufruf(*_a, **_k):
                raise AssertionError(f"{name} darf im Ausfall-Takt nicht laufen")
            return _aufruf

        patches = {name: mock.patch.object(bw, name, side_effect=_verboten(name))
                   for name in verboten}
        patches.update({
            "check_workflow_liveness": mock.patch.object(
                bw, "check_workflow_liveness", return_value=(3, "")),
            "check_syntax": mock.patch.object(bw, "check_syntax", return_value=(True, "")),
            "deploy_blockade": mock.patch.object(
                bw, "deploy_blockade", return_value=("ausgeliefert", "", "Beleg")),
            "newest_slug": mock.patch.object(
                bw, "newest_slug", return_value=("2026-10-09-artikel", None)),
            "check_live_site": mock.patch.object(
                bw, "check_live_site", return_value=(True, "200")),
        })
        for p in patches.values():
            p.start()
        try:
            env, befunde, slug = bw.run_all(triage=True)
        finally:
            for p in patches.values():
                p.stop()

        self.assertEqual(slug, "2026-10-09-artikel")
        self.assertEqual(befunde, [])
        self.assertTrue(env["MODUS"].startswith("AUSFALL-TAKT"))
        # Gemessen wurde die Ausfall-Klasse …
        for key in ("CHECK1A", "CHECK2", "CHECK3", "CHECK3B"):
            self.assertTrue(env[key].startswith(("OK", "FAIL", "WARN", "UNKNOWN")),
                            f"{key} wurde im Ausfall-Takt nicht gemessen")
        # … und alles andere ist ausdrücklich nicht gemessen, nie grün.
        for key in ("CHECK1B", "CHECK4", "CHECK5", "CHECK5B", "CHECK6", "CHECK7",
                    "CHECK8", "CHECK9", "CHECK9B", "CHECK10"):
            self.assertEqual(env[key], bw.TRIAGE_SKIP, f"{key} ist kein ÜBERSPRUNGEN")
        # Keine Workflow-Bedingung darf daraus einen Befund oder ein Grün lesen.
        for key, wert in env.items():
            if wert == bw.TRIAGE_SKIP:
                self.assertNotIn("WARN", wert)
                self.assertNotIn("FAIL", wert)

    def test_voll_lauf_misst_weiter_alles(self) -> None:
        """Der Ausfall-Takt ergänzt die Messkette, er ersetzt sie nicht."""
        with mock.patch.object(bw, "check_workflow_liveness", return_value=(3, "")), \
             mock.patch.object(bw, "check_syntax", return_value=(True, "")), \
             mock.patch.object(bw, "deploy_blockade",
                               return_value=("ausgeliefert", "", "Beleg")), \
             mock.patch.object(bw, "newest_slug", return_value=("slug", None)), \
             mock.patch.object(bw, "check_live_site", return_value=(True, "200")), \
             mock.patch.object(bw, "check_tls", return_value=True) as tls, \
             mock.patch.object(bw, "check_content_reserve",
                               return_value=(True, "6 Kandidaten")) as reserve:
            env, _befunde, _slug = bw.run_all(triage=False)
        tls.assert_called_once()
        reserve.assert_called_once()
        self.assertNotIn("MODUS", env)
        self.assertNotEqual(env["CHECK8"], bw.TRIAGE_SKIP)


class BlockadeOhneVierNullVierTestCase(unittest.TestCase):
    """Vertrag 2: Die Blockade ist ein Befund – auch wenn noch alles live ist."""

    def _run(self, live_ok, lage="blockiert"):
        with mock.patch.object(bw, "check_workflow_liveness", return_value=(3, "")), \
             mock.patch.object(bw, "check_syntax", return_value=(True, "")), \
             mock.patch.object(bw, "deploy_blockade",
                               return_value=(lage, SCORECARD_SCHRITT, "Lauf 1")), \
             mock.patch.object(bw, "newest_slug", return_value=("slug", None)), \
             mock.patch.object(bw, "check_live_site", return_value=live_ok):
            return bw.run_all(triage=True)

    def test_blockade_wird_ohne_404_gemeldet(self) -> None:
        """Der #676-Fall: CHECK3 grün, CHECK3B rot – vorher entstand kein Befund."""
        env, befunde, _slug = self._run((True, "200"))
        self.assertTrue(env["CHECK3"].startswith("OK"))
        self.assertTrue(env["CHECK3B"].startswith("FAIL"))
        self.assertEqual([f.id for f in befunde], ["deploy-blockade"])
        self.assertTrue(befunde[0].akut)

    def test_blockade_mit_404_bleibt_ein_befund_nicht_zwei(self) -> None:
        _env, befunde, _slug = self._run((False, "404"))
        ids = [f.id for f in befunde]
        self.assertEqual(ids.count("deploy-blockade"), 1)
        self.assertEqual(sorted(ids), ["deploy-blockade", "live-site"])
        self.assertTrue(all(f.akut for f in befunde))

    def test_offline_ist_kein_ausfall(self) -> None:
        _env, befunde, _slug = self._run((None, "offline"), lage="unbekannt")
        self.assertEqual(befunde, [])

    def test_eine_404_ist_ein_befund_nicht_zwei(self) -> None:
        """PR #684 und #686 bauten je einen `live-site`-Befund – derselbe
        Ausfall stand zweimal im Ticket, einmal ohne Heilungsweg."""
        _env, befunde, _slug = self._run((False, "404"))
        ids = [f.id for f in befunde]
        self.assertEqual(ids.count("live-site"), 1,
                         f"doppelter Befund: {ids}")
        live = [f for f in befunde if f.id == "live-site"][0]
        self.assertIn("watchdog_recovery.py", live.next_step,
                      "ein Befund mit Besitzer `auto` braucht einen "
                      "maschinellen Heilungsweg (C34)")
        self.assertTrue(live.akut)

    def test_deploy_spur_landet_als_beleg_im_befund(self) -> None:
        """Die Fehlschlag-Serie aus #684 bleibt erhalten – als Beleg, nicht
        als zweiter Befund."""
        spur = {"laeufe_fehlend": 6, "job": "deploy",
                "schritt": SCORECARD_SCHRITT, "lauf_id": 38046560460}
        befunde = bw.live_site_findings("slug", "404", "ausgeliefert", "", "",
                                        spur=spur)
        self.assertEqual(len(befunde), 1)
        self.assertIn("DEPLOY_FEHLERSCHLAEGE=6", befunde[0].evidence)
        self.assertIn(f"DEPLOY_SCHRITT={SCORECARD_SCHRITT}", befunde[0].evidence)
        self.assertIn("DEPLOY_RUN=38046560460", befunde[0].evidence)
        self.assertIn(SCORECARD_SCHRITT, befunde[0].detail)
        self.assertTrue(all(e for e in befunde[0].evidence))

    def test_blockadebefund_traegt_ursache_und_heilungsweg(self) -> None:
        befund = bw.deploy_blockade_finding(SCORECARD_SCHRITT, "Lauf 1")
        self.assertIn(SCORECARD_SCHRITT, befund.detail)
        self.assertIn("watchdog_recovery.py", befund.next_step)
        self.assertEqual(befund.owner, "auto")
        self.assertTrue(befund.akut)
        self.assertNotIn("", befund.evidence)


class AkuterMeldetaktTestCase(unittest.TestCase):
    """Vertrag 3: Der Takt rechnet in Stunden, solange der Ausfall steht."""

    def setUp(self) -> None:
        self.now = datetime.datetime(2026, 10, 10, 12, 0, tzinfo=datetime.timezone.utc)

    def _ticket(self, seit_stunden, stufe=0, letzter_kommentar=None):
        geboren = self.now - datetime.timedelta(hours=seit_stunden)
        return ar.IssueRef(
            number=676, created_at=geboren,
            body=ar.render_generic_body([blockade()], [], geboren),
            last_tier=stufe,
            last_bot_comment_at=(None if letzter_kommentar is None else
                                 self.now - datetime.timedelta(hours=letzter_kommentar)))

    def test_leiter_rechnet_in_stunden(self) -> None:
        self.assertEqual(ar.akut_tier_for_age(0.4), 0)
        self.assertEqual(ar.akut_tier_for_age(1.0), 1)
        self.assertEqual(ar.akut_tier_for_age(5.9), 1)
        self.assertEqual(ar.akut_tier_for_age(6.0), 2)
        self.assertEqual(ar.akut_tier_for_age(23.9), 2)
        self.assertEqual(ar.akut_tier_for_age(24.0), 3)

    def test_ausfall_eroeffnet_sofort_ein_ticket(self) -> None:
        d = ar.plan_generic([blockade()], None, self.now)
        self.assertEqual(d.action, "create")
        self.assertIn("Meldetakt", d.body)

    def _simulation(self, stunden: int) -> list[int]:
        """Kommentarstufen über `stunden` stündliche Ausfall-Takt-Runden."""
        geboren = self.now - datetime.timedelta(hours=stunden)
        ticket = ar.IssueRef(number=676, created_at=geboren,
                             body=ar.render_generic_body([blockade()], [], geboren),
                             last_tier=0, last_bot_comment_at=None)
        stufen = []
        for offset in range(1, stunden + 1):
            uhr = geboren + datetime.timedelta(hours=offset)
            d = ar.plan_generic([blockade()], ticket, uhr)
            if d.action != "comment":
                continue
            stufen.append(d.tier)
            ticket.last_tier = d.tier
            ticket.last_bot_comment_at = uhr
        return stufen

    def test_24_stunden_ausfall_ergeben_drei_staende_nicht_vierundzwanzig(self) -> None:
        self.assertEqual(self._simulation(24), [1, 2, 3])

    def test_endstufe_verstummt_nicht(self) -> None:
        """Ein Ausfall, der länger steht, bekommt weiter alle 24 h einen Stand."""
        self.assertEqual(self._simulation(48), [1, 2, 3, 3])
        self.assertEqual(self._simulation(96), [1, 2, 3, 3, 3, 3])

    def test_der_ausfall_vom_09_10_waere_gemeldet_worden(self) -> None:
        """19 h 38 min: die alte 72-h-Kadenz hätte in der ganzen Zeit geschwiegen."""
        stufen = self._simulation(19)
        self.assertEqual(stufen, [1, 2])
        self.assertGreaterEqual(len(stufen), 2)

    def test_stufe_wird_nicht_uebersprungen(self) -> None:
        d = ar.plan_generic([blockade()],
                            self._ticket(19 + 38 / 60, stufe=2, letzter_kommentar=13),
                            self.now)
        self.assertEqual(d.action, "none")
        self.assertIn("nächster Stand in 4.4 h", d.reason)

    def test_akuter_stand_nennt_dauer_und_naechsten_stand(self) -> None:
        d = ar.plan_generic([blockade()],
                            self._ticket(19 + 38 / 60, stufe=1, letzter_kommentar=18),
                            self.now)
        self.assertEqual(d.action, "comment")
        self.assertEqual(d.tier, 2)
        self.assertIn("19 h 38 min", d.body)
        self.assertIn("Nächster Stand in 4.4 h", d.body)
        self.assertIn(ar.TIER_MARKER.format(channel=ar.GENERIC_CHANNEL, tier=2), d.body)

    def test_mindestabstand_bremst_auch_im_ausfall(self) -> None:
        d = ar.plan_generic([blockade()], self._ticket(19.6, stufe=1,
                                                       letzter_kommentar=0.2), self.now)
        self.assertEqual(d.action, "none")

    def test_geheilter_ausfall_schliesst_den_kanal(self) -> None:
        d = ar.plan_generic([], self._ticket(3), self.now)
        self.assertEqual(d.action, "close")

    def test_dauer_text(self) -> None:
        self.assertEqual(ar._dauer_text(19 + 38 / 60), "19 h 38 min")
        self.assertEqual(ar._dauer_text(0.5), "30 min")
        self.assertEqual(ar._dauer_text(1.0), "1 h 00 min")
        self.assertEqual(ar._dauer_text(26.25), "1 T 2 h 15 min")


class GrenzeZumTaktfeuerTestCase(unittest.TestCase):
    """Vertrag 4 (#272): chronisch bleibt bei 72 h – sonst ist es Taktfeuer."""

    def setUp(self) -> None:
        self.now = datetime.datetime(2026, 10, 10, 12, 0, tzinfo=datetime.timezone.utc)

    def _ticket(self, befund, letzter_kommentar_stunden):
        geboren = self.now - datetime.timedelta(days=8)
        return ar.IssueRef(
            number=600, created_at=geboren,
            body=ar.render_generic_body([befund], [], geboren),
            last_bot_comment_at=self.now - datetime.timedelta(hours=letzter_kommentar_stunden))

    def test_chronischer_befund_bleibt_still(self) -> None:
        d = ar.plan_generic([chronisch()], self._ticket(chronisch(), 24), self.now)
        self.assertEqual(d.action, "none")
        self.assertIn("72 h", d.reason)

    def test_chronischer_befund_meldet_erst_nach_72_stunden(self) -> None:
        d = ar.plan_generic([chronisch()], self._ticket(chronisch(), 73), self.now)
        self.assertEqual(d.action, "comment")

    def test_chronisches_ticket_verspricht_keinen_stundentakt(self) -> None:
        self.assertNotIn("Meldetakt", ar.render_generic_body([chronisch()], [], self.now))

    def test_akut_und_chronisch_zusammen_binden_den_takt(self) -> None:
        """Steht ein Ausfall daneben, gilt der Ausfall-Takt für das Ticket."""
        zusammen = [chronisch(), blockade()]
        self.assertTrue(ar.akuter_takt(zusammen))
        self.assertNotIn("Meldetakt", ar.render_generic_body([chronisch()], [], self.now))
        self.assertIn("Meldetakt", ar.render_generic_body(zusammen, [], self.now))

    def test_json_roundtrip_behaelt_die_ausfallklasse(self) -> None:
        b = blockade()
        self.assertTrue(ar.Finding.from_dict(b.as_dict()).akut)
        self.assertFalse(ar.Finding.from_dict(chronisch().as_dict()).akut)

    def test_watchdog_markiert_nur_die_ausfallklasse_akut(self) -> None:
        self.assertTrue(bw.deploy_blockade_finding("X", "Beleg").akut)
        for f in bw.live_site_findings("slug", "404", "blockiert", "X", "Beleg"):
            self.assertTrue(f.akut, f.id)
        self.assertFalse(bw._f("kadenz", "Kadenz", severity="P1").akut)
        self.assertFalse(bw._f("produktions-wache", "Wache", severity="P1").akut)


class VertragC35TestCase(unittest.TestCase):
    """Der Vertrag selbst: echter Baum still, Sabotagen erkannt."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wflows = {WORKFLOW: _workflow_text()}
        cls.scripts = {}
        for name in ("bot_watchdog.py", "alert_router.py"):
            with open(os.path.join(BLOG_DIR, "scripts", name), encoding="utf-8") as f:
                cls.scripts[name] = f.read()

    def test_echter_baum_bleibt_still(self) -> None:
        self.assertEqual(
            gc.c35_meldetakt_an_den_ausfall(self.scripts, self.wflows, root=BLOG_DIR), [])

    def _nur_workflow(self, alt, neu):
        return {WORKFLOW: self.wflows[WORKFLOW].replace(alt, neu, 1)}

    def _nur_skript(self, datei, alt, neu):
        texte = dict(self.scripts)
        self.assertIn(alt, texte[datei])
        texte[datei] = texte[datei].replace(alt, neu, 1)
        return texte

    def test_ohne_ausfalltakt(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self.scripts, self._nur_workflow(gc.C35_AUSFALL_CRON, "# entfernt"),
            root=BLOG_DIR)
        self.assertTrue(any("23,5 h unbemerkt" in f[1] for f in funde))

    def test_ohne_voll_lauf(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self.scripts, self._nur_workflow(gc.C35_VOLL_CRON, "# entfernt"),
            root=BLOG_DIR)
        self.assertTrue(any("Voll-Lauf" in f[1] and "fehlt" in f[1] for f in funde))

    def test_ohne_takt_umschalter(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self.scripts, self._nur_workflow(gc.C35_TAKT_ID, "# entfernt"),
            root=BLOG_DIR)
        self.assertTrue(any("Takt-Umschalter" in f[1] for f in funde))

    def test_schreibender_schritt_ohne_taktsperre(self) -> None:
        wf = self._nur_workflow("if: ${{ always() && steps.takt.outputs.modus == 'voll' }}",
                                "if: always()")
        funde = gc.c35_meldetakt_an_den_ausfall(self.scripts, wf, root=BLOG_DIR)
        self.assertTrue(any("Routing-Zustand sichern" in f[1] for f in funde))

    def test_router_ohne_akuten_takt(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self._nur_skript("alert_router.py", "if akuter_takt(machine):", "if False:"),
            self.wflows, root=BLOG_DIR)
        self.assertTrue(any("nutzt den akuten Takt nicht" in f[1] for f in funde))

    def test_taktfeuer_statt_meldetakt(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self._nur_skript("alert_router.py", "MIN_COMMENT_INTERVAL_HOURS = 72",
                             "MIN_COMMENT_INTERVAL_HOURS = 1"),
            self.wflows, root=BLOG_DIR)
        self.assertTrue(any("Taktfeuer" in f[1] for f in funde))

    def test_blockade_ohne_ausfallklasse(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self._nur_skript("bot_watchdog.py",
                             '                              blockade_beleg) if e],\n        akut=True)',
                             '                              blockade_beleg) if e])'),
            self.wflows, root=BLOG_DIR)
        self.assertTrue(any("nicht als akut markiert" in f[1] for f in funde))

    def test_nicht_messung_als_gruen_getarnt(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self._nur_skript("bot_watchdog.py",
                             'TRIAGE_SKIP = "ÜBERSPRUNGEN (Ausfall-Takt – Voll-Lauf 08:30 UTC)"',
                             'TRIAGE_SKIP = "OK (im Ausfall-Takt nicht gemessen)"'),
            self.wflows, root=BLOG_DIR)
        self.assertTrue(any("TRIAGE_SKIP enthält" in f[1] for f in funde))

    def test_blockade_ohne_maschinellen_heilungsweg(self) -> None:
        funde = gc.c35_meldetakt_an_den_ausfall(
            self._nur_skript("bot_watchdog.py",
                             "`scripts/watchdog_recovery.py --live-site`) und LÄSST es ",
                             "und LÄSST es "),
            self.wflows, root=BLOG_DIR)
        self.assertTrue(any("Sackgasse" in f[1] for f in funde))

    def test_vertrag_ist_registriert_und_laeuft_im_selftest_mit(self) -> None:
        with open(os.path.join(BLOG_DIR, "scripts", "governance_contract.py"),
                  encoding="utf-8") as f:
            quelltext = f.read()
        self.assertIn("checks += c35_meldetakt_an_den_ausfall(", quelltext)
        self.assertIn("C35: der echte Zustand wird beanstandet", quelltext)


class AnkerDisziplinTestCase(unittest.TestCase):
    """Ein Vertrag, der den echten Baum beanstandet, erzieht zum Wegsehen (C2).

    Am 10.10.2026 meldete die Blustradius-Klausel von #684
    „deploy.yml: die Isolation steht NACH der finalen Release-Scorecard“ –
    auf einem Baum, in dem sie 130 Zeilen VOR ihr steht. Ursache: Der Anker
    war der blanke Schritt-TEXT, und genau der steht seit #686 auch in einem
    Kommentar am Kopf der Datei. `find` fand den Kommentar. Sichtbar wurde
    das erst, nachdem der Syntaxfehler desselben PRs behoben war – bis dahin
    war `governance_contract.py` gar nicht importierbar und das Qualitäts-Gate
    auf main tot.
    """

    def test_governance_contract_ist_importierbar(self) -> None:
        """Der Melder selbst muss laufen – sonst prüft niemand etwas."""
        self.assertTrue(hasattr(gc, "c35_meldetakt_an_den_ausfall"))
        self.assertTrue(hasattr(gc, "c34_blustradius"))

    def test_rechter_baum_hat_keine_befunde(self) -> None:
        self.assertEqual(gc.run_all(quick=True), [])

    def test_scorecard_anker_trifft_den_schritt_nicht_den_kommentar(self) -> None:
        with open(os.path.join(BLOG_DIR, ".github", "workflows", "deploy.yml"),
                  encoding="utf-8") as f:
            deploy = f.read()
        anker = "- name: Release-Scorecard (Produktionswahrheit versiegeln"
        i_score = deploy.find(anker)
        i_iso = deploy.find("release_isolation.py --commit-sha")
        self.assertGreater(i_score, 0, "Scorecard-Schritt nicht gefunden")
        self.assertGreater(i_iso, 0, "Isolations-Aufruf nicht gefunden")
        self.assertLess(i_iso, i_score,
                        "die Isolation muss VOR der finalen Scorecard stehen")
        # Gegenprobe: Der blanke Text steht auch in einem Kommentar – genau
        # darüber stolperte die alte Fassung.
        blank = "Release-Scorecard (Produktionswahrheit versiegeln"
        self.assertLess(deploy.find(blank), i_iso,
                        "Gegenprobe hinfällig: der blanke Text steht nicht mehr "
                        "vor der Isolation – der Anker wäre wieder beliebig")


class SelbsttestsTestCase(unittest.TestCase):
    """Fail-closed: Die Wache und der Router prüfen sich selbst."""

    def test_router_selftest(self) -> None:
        self.assertEqual(ar._selftest(), 0)

    def test_watchdog_selftest(self) -> None:
        self.assertEqual(bw.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
