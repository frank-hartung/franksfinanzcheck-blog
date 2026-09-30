#!/usr/bin/env python3
"""Tests für die Befund-Klassifikation des Bot-Watchdogs (Issue #272).

Der Watchdog darf einen Befund, den nur ein Mensch heilen kann, nicht
länger als „Problem mit der Content-Automatisierung" melden. Diese Tests
halten fest, wie der Pinterest-Kanal bewertet wird – inklusive der
Reihenfolge, die der Betrieb wirklich braucht:

    Domain gesperrt → Token-Neu-Autorisierung lohnt NICHT vorher.

Läuft deterministisch ohne Netz: der Prüfpfad wird auf ein temporäres
`data/`-Verzeichnis umgebogen.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import alert_router as ar  # noqa: E402
import bot_watchdog as bw  # noqa: E402

# Zeit-Anker relativ zur echten Uhr: der Watchdog misst die Lagebild-Frische an
# now() (Fenster: STATE_MAX_AGE_HOURS = 48 h). Ein absolut datierter Anker ist eine
# Zeitbombe – am 14.09.2026 sind genau vier dieser Tests umgefallen, weil ihr „NOW"
# der 12.09. war und jeder Lauf danach in den Zweig „Lagebild veraltet" lief.
# Deterministisch bleibt es trotzdem: eine Stunde alt ist frisch, fünf Tage alt ist
# veraltet – unabhängig vom Laufdatum.
NOW = datetime.datetime.now(datetime.timezone.utc)
FRISCH = (NOW - datetime.timedelta(hours=1)).isoformat()


def _state(state="dead", severity="red", checked_at=FRISCH, renewable=False,
           detail="Pinterest lehnt den Token ab (HTTP 401)", source="keine"):
    return {
        "state": state, "severity": severity, "checked_at": checked_at,
        "renewable": renewable, "detail": detail, "source_label": source,
        "next_action": "Einmalige Neu-Autorisierung nötig.",
    }


class WatchdogKanalTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        self.alt = bw.BLOG_DIR
        bw.BLOG_DIR = self.tmp
        # Zielbestand für die Dauer des Tests festnageln (#393): Die
        # Alarmschwelle wird aus dem Ziel abgeleitet, also darf eine gesetzte
        # Repository-Variable die Erwartungen hier nicht verschieben. Genau
        # diese Abhängigkeit hat den reserve_gate-Selbsttest in Workflow #24
        # rot gemacht, als die Umgebung ein anderes Ziel setzte.
        self.alt_target = os.environ.get("RESERVE_TARGET")
        self.alt_puffer = os.environ.get("RESERVE_PUFFER")
        os.environ["RESERVE_TARGET"] = "6"    # → Alarmschwelle 4
        os.environ.pop("RESERVE_PUFFER", None)

    def tearDown(self):
        bw.BLOG_DIR = self.alt
        for name, wert in (("RESERVE_TARGET", self.alt_target),
                           ("RESERVE_PUFFER", self.alt_puffer)):
            if wert is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = wert
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, data):
        (self.tmp / "data" / name).write_text(json.dumps(data), encoding="utf-8")

    def _write_reserve_certificate(self, candidates, generated_at=FRISCH):
        self._write("reserve-readiness.json", {
            "target": 6,
            "ready": sum(c.get("ready") is True for c in candidates),
            "generated_at": generated_at,
            "candidates": candidates,
        })

    def _write_reserve_draft(self, slug):
        path = self.tmp / "content" / "posts" / slug / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"---\ntitle: {slug}\ndraft: true\nreserve: true\n---\nBody\n"
        path.write_text(content, encoding="utf-8")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    # --- Reihenfolge: erst die Domain, dann der Token ------------------- #
    def test_token_rot_bei_domainsperre_ist_ein_hinweis(self):
        self._write("pinterest_token_state.json", _state())
        self._write("pinterest_domain_block.json",
                    {"since": "2026-08-27T13:58:16Z",
                     "reason": "Pinterest hat die Domain gesperrt (Spam-Markierung).",
                     "policy": "Keine Pins bis zur Freigabe."})
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 2)
        for f in findings:
            self.assertEqual(f.owner, "human", f.id)
            self.assertEqual(f.channel, bw.PINTEREST_PARKED_CHANNEL, f.id)
            self.assertEqual(f.severity, "P3", f.id)
        self.assertIn("geparkt", text)
        # Wichtig: kein Automations-Ticket, und ein offenes geht zu.
        self.assertEqual(ar.plan_generic(findings, None, NOW).action, "none")
        offen = ar.IssueRef(number=272, created_at=NOW - datetime.timedelta(days=1))
        self.assertEqual(ar.plan_generic(findings, offen, NOW).action, "close")

    def test_token_rot_ohne_sperre_geht_ins_fach_ticket(self):
        self._write("pinterest_token_state.json", _state())
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual((f.owner, f.channel, f.severity),
                         ("human", bw.PINTEREST_TOKEN_CHANNEL, "P2"))
        self.assertIn("Runbook", f.next_step)
        self.assertEqual(ar.plan_generic(findings, None, NOW).action, "none")

    def test_ablaufender_token_mit_refresh_bleibt_maschinell(self):
        self._write("pinterest_token_state.json",
                    _state(state="expiring", severity="amber", renewable=True))
        findings, _ = bw.check_pinterest_channel()
        self.assertEqual(findings[0].owner, "auto")
        # maschinell ⇒ darf das Automations-Ticket öffnen
        self.assertEqual(ar.plan_generic(findings, None, NOW).action, "create")

    def test_ablaufender_token_ohne_refresh_braucht_menschen(self):
        self._write("pinterest_token_state.json",
                    _state(state="expiring", severity="amber", renewable=False))
        findings, _ = bw.check_pinterest_channel()
        self.assertEqual(findings[0].owner, "human")

    # --- Die Wache selbst ------------------------------------------------ #
    def test_veraltetes_lagebild_ist_ein_maschinen_befund(self):
        self._write("pinterest_token_state.json",
                    _state(checked_at=(NOW - datetime.timedelta(days=5)).isoformat()))
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].owner, "auto")
        self.assertEqual(findings[0].channel, ar.GENERIC_CHANNEL)
        self.assertIn("alt", text)

    def test_fehlendes_lagebild_ist_ein_maschinen_befund(self):
        findings, _ = bw.check_pinterest_channel()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].owner, "auto")

    def test_gruener_token_meldet_nichts(self):
        self._write("pinterest_token_state.json",
                    _state(state="live", severity="green", detail="", source="store"))
        findings, text = bw.check_pinterest_channel()
        self.assertEqual(findings, [])
        self.assertIn("OK", text)

    # --- Trennschärfe ---------------------------------------------------- #
    def test_split_findings_trennt_nach_besitzer(self):
        mensch = bw._f("pinterest-token", "Token tot", owner="human",
                       channel=bw.PINTEREST_TOKEN_CHANNEL)
        maschine = bw._f("cadence", "Kadenz", severity="P1", owner="auto")
        m, h = bw.split_findings([mensch, maschine])
        self.assertEqual([f.id for f in m], ["cadence"])
        self.assertEqual([f.id for f in h], ["pinterest-token"])

    def test_domainsperre_wird_erkannt(self):
        self.assertIsNone(bw.pinterest_domain_block())
        self._write("pinterest_domain_block.json", {"since": "2026-08-27T13:58:16Z"})
        self.assertIsNotNone(bw.pinterest_domain_block())

    def test_content_reserve_zaehlt_nur_hashgesicherte_reife_kandidaten(self):
        candidates = []
        for i in range(4):
            slug = f"reserve-{i}"
            candidates.append({
                "slug": slug, "ready": True,
                "sha256": self._write_reserve_draft(slug),
            })
        self._write_reserve_certificate(candidates)

        ok, text = bw.check_content_reserve()

        self.assertTrue(ok)
        # #393: Der Befund nennt beide Zahlen getrennt. Das frühere „4/4
        # gate-fertige" las sich wie ein Vollbestand, obwohl die 4 im Nenner
        # nur die Alarmschwelle war – der Vorrat lag damit auf der Alarmgrenze.
        self.assertIn("4 gate-fertige Artikel", text)
        self.assertIn("Ziel 6", text)
        self.assertIn("Alarm unter 4", text)
        self.assertNotIn("4/4 gate-fertige", text)

    def test_content_reserve_meldet_konkrete_gate_blocker(self):
        candidates = []
        for i in range(2):
            slug = f"reserve-{i}"
            candidates.append({
                "slug": slug, "ready": True,
                "sha256": self._write_reserve_draft(slug),
            })
        candidates.append({
            "slug": "blockiert", "ready": False,
            "reason": "Cover-Text unvollständig",
        })
        self._write_reserve_draft("blockiert")
        self._write_reserve_certificate(candidates)

        ok, text = bw.check_content_reserve()

        self.assertFalse(ok)
        self.assertIn("2 gate-fertige Artikel", text)
        self.assertIn("Alarm unter 4", text)
        self.assertIn("Cover-Text unvollständig", text)

    def test_content_reserve_verwirft_nachtraeglich_geaenderte_kandidaten(self):
        candidates = []
        paths = []
        for i in range(4):
            slug = f"reserve-{i}"
            candidates.append({
                "slug": slug, "ready": True,
                "sha256": self._write_reserve_draft(slug),
            })
            paths.append(self.tmp / "content" / "posts" / slug / "index.md")
        self._write_reserve_certificate(candidates)
        paths[0].write_text(paths[0].read_text(encoding="utf-8") + "Changed\n",
                            encoding="utf-8")

        ok, text = bw.check_content_reserve()

        self.assertFalse(ok)
        self.assertIn("3 gate-fertige Artikel", text)
        self.assertIn("Zertifikat passt nicht mehr", text)

    def test_content_reserve_ignoriert_veraltetes_zertifikat(self):
        slug = "alter-nachweis"
        candidates = [{
            "slug": slug, "ready": True,
            "sha256": self._write_reserve_draft(slug),
        }]
        alt = (NOW - datetime.timedelta(hours=48)).isoformat()
        self._write_reserve_certificate(candidates, generated_at=alt)

        ok, text = bw.check_content_reserve()

        self.assertFalse(ok)
        self.assertIn("Zertifikat ungültig", text)
        self.assertIn("veraltet", text)


class ReserveBefundRoutetNachUrsache(unittest.TestCase):
    """#462: Der nächste Schritt muss zur Ursache passen.

    Zertifikats-Drift (Heiler-Lauf nach der Zertifizierung) ist ein
    NACHWEIS-Problem und in Sekunden nachzertifiziert. Ein echter Engpass
    ist ein PRODUKTIONS-Problem. Beide teilten sich bis #462 denselben
    Befundtext – das Ticket war damit nie abarbeitbar und kam täglich zurück.
    """

    def tearDown(self):
        bw.RESERVE_DIAGNOSE.clear()

    def _diagnose(self, certified, drifted, minimum=4):
        bw.RESERVE_DIAGNOSE.clear()
        bw.RESERVE_DIAGNOSE.update({"certified": certified, "minimum": minimum,
                                    "ziel": 6, "drifted": drifted, "pool": 8})

    def test_drift_verweist_auf_die_nachzertifizierung(self):
        self._diagnose(certified=2, drifted=["a", "b"])
        f = bw.reserve_finding("Reserve unter Mindestbestand (…)")
        self.assertIn("Zertifikat veraltet", f.title)
        self.assertIn("reserve_recert.py --fix", f.next_step)
        self.assertEqual(f.owner, "auto")

    def test_echter_engpass_verweist_weiter_auf_die_produktionslinie(self):
        self._diagnose(certified=1, drifted=[])
        f = bw.reserve_finding("Reserve unter Mindestbestand (…)")
        self.assertIn("Content-Reserve niedrig", f.title)
        self.assertIn("content-reserve.yml", f.next_step)

    def test_drift_ohne_tragfaehigen_bestand_bleibt_produktionsbefund(self):
        # 0 zertifiziert + 1 gedriftet trägt die Schwelle 4 NICHT: Auch nach
        # perfekter Nachzertifizierung fehlt Content – dann darf der Befund
        # nicht beschwichtigen.
        self._diagnose(certified=0, drifted=["a"])
        f = bw.reserve_finding("Reserve unter Mindestbestand (…)")
        self.assertIn("Content-Reserve niedrig", f.title)


if __name__ == "__main__":
    unittest.main(verbosity=2)
