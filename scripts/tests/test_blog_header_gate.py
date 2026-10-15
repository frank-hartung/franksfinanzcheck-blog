#!/usr/bin/env python3
"""Tests der Sicherheits-Header-Wache (scripts/blog_header_gate.py).

Hintergrund: Vorgang WF-E813, 15.10.2026. Der erste planmäßige Live-Lauf der
Sicherheits-Wache wurde rot. Zwei Fehler steckten in derselben Zeile:

  1. **Die Wache log.** Jede Netzstörung landete in der Liste der fehlenden
     Pflicht-Header. Ein TLS-Abbruch wurde zu „❌ Pflicht-Header fehlen oder
     sind falsch" umgedeutet – obwohl im Satz daneben stand, dass ohne
     Messung der Stand *ungeprüft* gilt. Ungeprüft ist nicht fehlend.
  2. **Der Melder riet.** Die automatische Meldung bot als „häufigste
     Ursachen" einen abgelaufenen API-Schlüssel an. Diese Wache misst
     Kopfzeilen und kennt keinen Schlüssel.

Diese Datei ist die Wache, dass weder das eine noch das andere zurückkommt:
Die vier Klassen (OK · TEILWEISE · BEFUND · STOERUNG) sind festgenagelt, die
Selbstheilung gegen transiente Netzfehler ist belegt, und die Verdrahtung im
Workflow (Auswertung statt Durchreichen, Vertrag C34) wird mitgeprüft – ein
Mess-Schritt, der seinen Exit-Code wieder durchreicht, macht jede
Klassifikation wertlos.

Läuft deterministisch ohne Netz
(`python3 -m unittest scripts.tests.test_blog_header_gate`).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import blog_header_gate as gate  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "sicherheits-wache.yml"

GUT = dict(gate.GUTE_KOPFZEILEN)
PROXY = dict(gate.PROXY_KENNUNG)
ABBRUCH = OSError("TLS/SSL connection has been closed (EOF)")


def _attrappe(ablauf):
    """Baut eine `holen`-Funktion, die die Ablaufliste abspielt und mitzählt."""
    probe = gate._Probe(ablauf)
    return probe.holen, probe


def _messen(ablauf, *, pausen=(), ziele=None):
    holen, probe = _attrappe(ablauf)
    return gate.netz_pruefen(holen=holen, pausen=pausen, schlaf=lambda _: None,
                             ziele=ziele), probe


class StoerungIstKeinBefund(unittest.TestCase):
    """Kernregression WF-E813: Eine Nicht-Messung ist kein Sicherheitsbefund."""

    def test_unerreichbare_seite_wird_als_stoerung_klassifiziert(self):
        (code, bericht, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_STOERUNG)
        self.assertEqual(daten["klasse"], gate.KLASSE_STOERUNG)
        self.assertEqual(daten["gemessen"], 0)
        self.assertEqual(daten["nicht_gemessen"], [gate.ZIELE[0]])

    def test_netzstoerung_wandert_nie_in_die_liste_fehlender_header(self):
        """Genau das war der Fehler: `fehlend_gesamt.append(... nicht erreichbar ...)`."""
        (_, _, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        self.assertEqual(daten["fehlend"], [],
                         "Eine Netzstörung darf nie als fehlender Header erscheinen")
        self.assertTrue(daten["stoerung"], "Die Störung muss eigenständig benannt werden")

    def test_der_bericht_behauptet_keine_fehlenden_header(self):
        (_, bericht, _), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        self.assertNotIn("fehlen oder sind falsch", bericht)
        self.assertIn("kein Header-Befund", bericht)
        self.assertIn("ungeprüft", bericht)

    def test_stoerung_und_befund_haben_unterschiedliche_exit_codes(self):
        # Der Auswerte-Schritt im Workflow trennt anhand dieser Codes. Wären
        # sie gleich, wäre die ganze Klassifikation wirkungslos.
        self.assertNotEqual(gate.EXIT_BEFUND, gate.EXIT_STOERUNG)
        self.assertNotEqual(gate.EXIT_OK, gate.EXIT_STOERUNG)
        self.assertEqual(gate.EXIT_BEFUND, 1)   # Bestandsvertrag: rot bleibt 1
        self.assertEqual(gate.EXIT_STOERUNG, 2)

    def test_stoerung_nennt_einen_naechsten_schritt_ohne_cloudflare_eingriff(self):
        (_, _, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        schritt = daten["naechster_schritt"]
        self.assertTrue(schritt, "Eine Störung ohne nächsten Schritt ist Ratlosigkeit")
        self.assertIn("curl -sI", schritt)
        self.assertNotIn("Proxied", schritt)

    def test_versuche_werden_protokolliert(self):
        (_, bericht, daten), _ = _messen([ABBRUCH], pausen=(0.0, 0.0),
                                         ziele=[gate.ZIELE[0]])
        self.assertEqual(daten["ziele"][0]["versuche"], 3)
        self.assertIn("Versuch 3", bericht)


class Selbstheilung(unittest.TestCase):
    """Transiente Netzfehler heilt die Wache selbst, statt zu alarmieren."""

    def test_ein_abgebrochener_versuch_wird_wiederholt(self):
        (code, _, daten), probe = _messen(
            [ABBRUCH, ABBRUCH, (200, {**PROXY, **GUT})],
            pausen=(0.0,), ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertEqual(daten["klasse"], gate.KLASSE_OK)
        self.assertEqual(probe.wege, ["HEAD", "GET", "HEAD"])

    def test_head_mit_fehlerstatus_löst_get_nachfrage_aus(self):
        def holen(url, weg):
            if weg == "HEAD":
                return (405, {"server": "cloudflare"})
            return (200, {**PROXY, **GUT})
        code, _, daten = gate.netz_pruefen(holen=holen, pausen=(),
                                           schlaf=lambda _: None, ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK, "Ein HEAD-Verbot darf kein Befund sein")
        self.assertEqual(daten["ziele"][0]["weg"], "GET")

    def test_pausen_sind_aufsteigend_und_endlich(self):
        # Sonst wäre „Wiederholung" entweder wirkungslos (0 s) oder eine
        # Endlosschleife im täglichen Lauf.
        self.assertTrue(gate.PAUSEN)
        self.assertEqual(list(gate.PAUSEN), sorted(gate.PAUSEN))
        self.assertLess(sum(gate.PAUSEN), 120.0,
                        "Die Selbstheilung muss in den 15-Minuten-Job passen")


class TeilweiseGemessen(unittest.TestCase):
    """Ein Ziel sauber, ein Ziel tot: kein Alarm, aber kein Freibrief."""

    def test_sauberer_host_alarmiert_nicht(self):
        def holen(url, weg):
            if url == gate.ZIELE[0]:
                return (200, {**PROXY, **GUT})
            raise OSError("Name or service not known")
        code, bericht, daten = gate.netz_pruefen(holen=holen, pausen=(),
                                                 schlaf=lambda _: None)
        self.assertEqual(code, gate.EXIT_OK)
        self.assertEqual(daten["klasse"], gate.KLASSE_TEILWEISE)
        self.assertEqual(daten["nicht_gemessen"], [gate.ZIELE[1]])

    def test_das_nicht_gemessene_ziel_wird_benannt(self):
        def holen(url, weg):
            if url == gate.ZIELE[0]:
                return (200, {**PROXY, **GUT})
            raise OSError("Name or service not known")
        _, bericht, _ = gate.netz_pruefen(holen=holen, pausen=(),
                                          schlaf=lambda _: None)
        self.assertIn(gate.ZIELE[1], bericht)

    def test_ein_gemessener_befund_sticht_die_stoerung(self):
        def holen(url, weg):
            if url == gate.ZIELE[0]:
                return (200, {**PROXY, "x-content-type-options": "nosniff"})
            raise OSError("Connection reset by peer")
        code, _, daten = gate.netz_pruefen(holen=holen, pausen=(),
                                           schlaf=lambda _: None)
        self.assertEqual(code, gate.EXIT_BEFUND)
        self.assertEqual(daten["klasse"], gate.KLASSE_BEFUND)
        self.assertEqual(daten["gemessen"], 1)
        self.assertTrue(any(gate.ZIELE[0] in f for f in daten["fehlend"]))


class ProxyDiagnose(unittest.TestCase):
    """Der Bericht nennt die Ursache, nicht nur das Symptom."""

    def test_proxy_erkennung(self):
        self.assertEqual(gate.proxy_lage({"cf-ray": "abc-FRA"}), gate.PROXY_AKTIV)
        self.assertEqual(gate.proxy_lage({"server": "cloudflare"}), gate.PROXY_AKTIV)
        self.assertEqual(gate.proxy_lage({"server": "GitHub.com"}), gate.PROXY_FEHLT)
        self.assertEqual(gate.proxy_lage({}), gate.PROXY_UNBEKANNT)

    def test_proxy_fehlt_zeigt_auf_den_dashboard_schritt(self):
        (code, bericht, daten), _ = _messen([(200, {"server": "GitHub.com"})],
                                            ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_BEFUND)
        self.assertEqual(daten["proxy"], gate.PROXY_FEHLT)
        self.assertIn("A1 Schritt 1", daten["naechster_schritt"])
        self.assertIn("gar nicht wirken", bericht)

    def test_proxy_aktiv_zeigt_auf_die_regel_nicht_auf_den_proxy(self):
        (code, _, daten), _ = _messen(
            [(200, {**PROXY, "content-security-policy": "default-src 'self'",
                    "x-content-type-options": "nosniff", "x-frame-options": "DENY",
                    "referrer-policy": "strict-origin-when-cross-origin",
                    "strict-transport-security": "max-age=300"})],
            ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_BEFUND)
        self.assertEqual(daten["proxy"], gate.PROXY_AKTIV)
        self.assertIn("FF Sicherheits-Header", daten["naechster_schritt"])
        self.assertNotIn("Proxied", daten["naechster_schritt"])


class WorkflowVerdrahtung(unittest.TestCase):
    """Vertrag C34: Der Workflow wertet aus, er reicht nicht durch.

    Ohne diese Verdrahtung wäre die gesamte Klassifikation nur Kosmetik:
    GitHub kennt am Schritt nur rot oder grün, und der Melder müßte wieder
    raten, was rot bedeutet.
    """

    def setUp(self):
        if not WORKFLOW.exists():
            self.skipTest("sicherheits-wache.yml fehlt")
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_mess_schritt_reicht_seinen_exit_nicht_durch(self):
        self.assertNotRegex(
            self.text, r"run: python3 scripts/blog_header_gate\.py\s*\n",
            "Der Mess-Schritt darf kein nackter Durchreicher sein (Vertrag C34)")

    def test_exit_code_wird_festgehalten(self):
        self.assertIn("code=$?", self.text)
        self.assertIn("steps.header.outputs.code", self.text)

    def test_auswerte_schritt_unterscheidet_befund_und_stoerung(self):
        self.assertIn("F-01 BEFUND", self.text)
        self.assertIn("F-01 STOERUNG", self.text)
        self.assertIn("F-01 WACHE-FEHLER", self.text)

    def test_bericht_geht_in_die_zusammenfassung(self):
        # Lehre aus INCIDENT-2026-09-19: Die Wahrheit steht in der
        # Zusammenfassung, nicht versteckt im Log.
        self.assertIn("GITHUB_STEP_SUMMARY", self.text)

    def test_auswerte_schritt_bleibt_vom_alarm_routing_findbar(self):
        # Das Fehler-Alerting ordnet die Sicherheits-Wache über die Zeichen-
        # kette „Sicherheits-Header" im Schrittnamen zu (WF-E813). Würde der
        # Schritt umbenannt, fiele die Meldung still auf den Schlüssel-Rat
        # zurück – deshalb ist die Kopplung hier festgenagelt.
        self.assertIn("Sicherheits-Header auswerten", self.text)

    def test_worker_messung_wird_von_rotem_f01_nicht_verdeckt(self):
        self.assertIn("if: always()", self.text)


class AlarmRouting(unittest.TestCase):
    """Die Meldung darf nicht auf einen Schlüssel raten (WF-E813, zweiter Fehler)."""

    def setUp(self):
        self.pfad = REPO / ".github" / "workflows" / "alert-on-failure.yml"
        if not self.pfad.exists():
            self.skipTest("alert-on-failure.yml fehlt")
        self.text = self.pfad.read_text(encoding="utf-8")

    def test_sicherheits_wache_hat_eigene_triage(self):
        self.assertIn("istSicherheitsWache", self.text)
        self.assertIn("headerGateFailed", self.text)
        self.assertIn("wfName === 'Sicherheits-Wache'", self.text)

    def test_die_triage_haengt_an_der_runbook_klasse(self):
        # WF-9E5A / #761 (15.10.2026): Der Rat in einer offenen Meldung wird
        # nur nachgeführt, wenn die Klasse einen EIGENEN Namen hat. Hängt die
        # Sicherheits-Wache an der allgemeinen Klasse, bleibt in offenen
        # Meldungen der alte Rat stehen – genau der befundete Schaden.
        self.assertIn("runbookKlasse === 'sicherheit-header'", self.text)
        self.assertIn("runbookKlasse === 'sicherheit-wache'", self.text)
        self.assertIn("headerGateFailed ? 'sicherheit-header'", self.text)
        self.assertIn("istSicherheitsWache ? 'sicherheit-wache'", self.text)

    def test_die_triage_verweist_auf_die_beiden_runsbooks(self):
        self.assertIn("docs/SICHERHEIT-BETRIEB-RUNBOOK.md", self.text)
        self.assertIn("cloudflare/edge-schutz.md", self.text)


if __name__ == "__main__":
    unittest.main()
