"""WF-E813/#809: Ein öffentlicher/alter Healthcheck ist kein Betriebsnachweis.

Alle Netzaufrufe sind Attrappen. Keine Schlüssel, Exporte oder Live-KV-Daten
werden gelesen; Testberichte liegen ausschließlich im temporären Verzeichnis.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import worker_betrieb_wache as gate

BASE = "https://abos.franksfinanzcheck.de"
REPO = {"site_key": "0x4AAA", "sitekey_spiegel": "0x4AAA", "deckel": 100,
        "edge_vorlage": "Rate limiting\nTurnstile\nStrict-Transport-Security\nEnvironments\n"}
GUT = {"ok": True, "kv": "ok", "ts": "2026-10-19T12:00:00Z", "turnstile": "aktiv",
       "schluesselrollen": "getrennt", "exporte": [],
       "budget": {"anmeldung_heute": 3, "anmeldung_max": 100, "feedback_max": 200}}


def messen(stand, **kwargs):
    return gate.netz_pruefen(BASE, "test-only", schreibschluessel="test-write-only",
                             holen=lambda *_: stand, repo=REPO, pausen=(), **kwargs)


class AuthentifiziertesBetriebsbild(unittest.TestCase):
    def test_vollstaendiges_betriebsbild_wird_ausgewertet(self):
        code, _, daten = messen(GUT)
        self.assertEqual(code, 0)
        self.assertEqual(daten["klasse"], "OK")
        self.assertEqual(daten["gemessen"], 1)
        self.assertEqual(daten["fehlend"], [])

    def test_github_schreibschluessel_muss_vorhanden_und_getrennt_sein(self):
        for schreibschluessel, erwartung in (("", "fehlt"), ("test-only", "identisch")):
            with self.subTest(schreibschluessel=erwartung):
                code, bericht, daten = gate.netz_pruefen(
                    BASE, "test-only", schreibschluessel=schreibschluessel,
                    holen=lambda *_: GUT, repo=REPO, pausen=())
                self.assertEqual(code, 1)
                self.assertEqual(daten["klasse"], "BEFUND")
                self.assertIn("NEWSLETTER_WORKER_WRITE_KEY", bericht)
                self.assertIn(erwartung, bericht)

    def test_oeffentliche_200_antwort_ist_nicht_geprueft(self):
        code, bericht, daten = messen({"ok": True, "ts": GUT["ts"]})
        self.assertEqual(code, 2)
        self.assertEqual(daten["klasse"], "STOERUNG")
        self.assertEqual(daten["gemessen"], 0)
        self.assertEqual(daten["fehlend"], [])
        self.assertIn("Öffentliche /healthz-Antwort", bericht)
        self.assertNotIn("Turnstile inaktiv", bericht)
        self.assertNotIn("Tagesbudget im Rahmen", bericht)

    def test_alter_authentifizierter_deploy_wird_nicht_mit_sollwerten_aufgefuellt(self):
        code, bericht, daten = messen({"ok": True, "kv": "ok", "takt": {"crons": []}})
        self.assertEqual(code, 2)
        self.assertIn("veralteter Worker-Deploy", bericht)
        self.assertEqual(daten["fehlend"], [])

    def test_jedes_geschuetzte_pflichtfeld_ist_zwingend(self):
        for feld in ("ok", "kv", "budget", "turnstile", "schluesselrollen", "exporte"):
            with self.subTest(feld=feld):
                stand = {k: v for k, v in GUT.items() if k != feld}
                code, _, daten = messen(stand)
                self.assertEqual(code, 2)
                self.assertEqual(daten["gemessen"], 0)
                self.assertEqual(daten["fehlend"], [])

    def test_ungueltige_schutzwerte_sind_stoerung_kein_befund(self):
        for aenderung in ({"ok": "true"}, {"ok": 1}, {"kv": "unbekannt"},
                          {"kv": "fehler"}, {"turnstile": "unbekannt"},
                          {"schluesselrollen": None}, {"budget": []},
                          {"exporte": {}}, {"exporte": [{"status": "403"}]}):
            with self.subTest(aenderung=aenderung):
                code, _, daten = messen({**GUT, **aenderung})
                self.assertEqual(code, 2)
                self.assertEqual(daten["fehlend"], [])

    def test_budgetfelder_duerfen_nicht_fehlend_bool_string_oder_negativ_sein(self):
        for feld in GUT["budget"]:
            for wert in (None, True, "100", [], 1.5):
                with self.subTest(feld=feld, wert=wert):
                    code, _, _ = messen({**GUT, "budget": {**GUT["budget"], feld: wert}})
                    self.assertEqual(code, 2)
        for feld in ("anmeldung_heute", "feedback_max"):
            with self.subTest(feld=feld):
                self.assertEqual(messen({**GUT, "budget": {**GUT["budget"], feld: -1}})[0], 2)

    def test_falsche_json_wurzel_wird_sicher_abgewiesen(self):
        for stand in (None, [], "ok", True, 42):
            with self.subTest(stand=stand):
                self.assertEqual(messen(stand)[0], 2)

    def test_echter_kv_ausfall_ist_befund(self):
        code, bericht, daten = messen({**GUT, "ok": False, "kv": "fehler"})
        self.assertEqual(code, 1)
        self.assertEqual(daten["klasse"], "BEFUND")
        self.assertEqual(daten["gemessen"], 1)
        self.assertIn("Ausfall", bericht)

    def test_turnstile_widerspruch_bleibt_fail_closed(self):
        code, bericht, daten = messen({**GUT, "turnstile": "inaktiv"})
        self.assertEqual(code, 1)
        self.assertIn("Fassade", bericht)
        self.assertTrue(daten["fehlend"])
        code, bericht, _ = gate.netz_pruefen(
            BASE, "test-only", schreibschluessel="test-write-only",
            holen=lambda *_: GUT, repo={**REPO, "site_key": ""}, pausen=())
        self.assertEqual(code, 1)
        self.assertIn("nicht durch Entfernen des Secrets abschalten", bericht)
        self.assertNotIn("oder Secret entfernen", bericht)

    def test_keine_rohen_health_daten_oder_geheimnisse_im_report(self):
        gift = "GIFTWERTE_NIE_VEROEFFENTLICHEN"
        stand = {**GUT, "ts": gift, "secret": gift,
                 "exporte": [{"ts": gift, "route": gift, "key": gift,
                              "email": gift, "status": 403}]}
        _, bericht, daten = messen(stand)
        self.assertNotIn(gift, bericht)
        self.assertNotIn(gift, json.dumps(daten))
        self.assertNotIn("exporte", daten)

    def test_tagesdeckel_null_bleibt_echter_befund(self):
        code, bericht, _ = messen({**GUT, "budget": {**GUT["budget"], "anmeldung_max": 0}})
        self.assertEqual(code, 1)
        self.assertIn("Kein Tagesdeckel", bericht)

    def test_abweichender_und_kv_sprengender_deckel_wird_belegt(self):
        code, bericht, _ = messen({**GUT, "budget": {**GUT["budget"], "anmeldung_max": 300}})
        self.assertEqual(code, 1)
        self.assertIn("Repo-Stand ab", bericht)
        self.assertIn("Schreibbudget gefährdet", bericht)

    def test_ausgeschoepftes_budget_warnt_aber_geteilter_schluessel_ist_befund(self):
        code, bericht, daten = messen({**GUT, "schluesselrollen": "gemeinsam",
                                      "budget": {**GUT["budget"], "anmeldung_heute": 100}})
        self.assertEqual(code, 1)
        self.assertEqual(daten["klasse"], "BEFUND")
        self.assertIn("ausgeschöpft", bericht)
        self.assertIn("Getrennte Export-Schlüssel fehlen oder sind identisch", bericht)
        self.assertEqual(len(daten["warnungen"]), 1, "nur der ausgeschöpfte Budgetstand ist eine Warnung")


class RepoUndLiveVertrag(unittest.TestCase):
    def test_echter_repo_stand_produziert_keinen_erfundenen_worker_fehler(self):
        repo = gate.repo_stand()
        stand = {**GUT, "turnstile": "aktiv" if repo["site_key"] else "inaktiv",
                 "budget": {**GUT["budget"], "anmeldung_max": repo["deckel"]}}
        self.assertEqual(gate.vorlagen_fehler(repo["edge_vorlage"]), [])
        fehler, _, _ = gate.bewerte(stand, repo)
        self.assertEqual(fehler, [])
        self.assertEqual(gate.offline_pruefen()[0], 0)

    def test_809_reproduktion_verlorene_environments_anleitung_faellt_schon_offline_auf(self):
        for stichwort in ("Rate limiting", "Turnstile", "Strict-Transport-Security", "Environments"):
            with self.subTest(stichwort=stichwort):
                repo = {**REPO, "edge_vorlage": REPO["edge_vorlage"].replace(stichwort, "")}
                mit_vorlage = gate.bewerte(GUT, repo)[0]
                self.assertTrue(any(stichwort in f for f in mit_vorlage))
                with patch.object(gate, "repo_stand", return_value=repo):
                    code, bericht = gate.offline_pruefen()
                self.assertEqual(code, 1)
                self.assertIn(stichwort, bericht)


class WiederholungUndZugang(unittest.TestCase):
    def test_fehlender_schluessel_ist_stoerung_ohne_netz(self):
        holen = Mock(side_effect=AssertionError("Netzaufruf ohne Zugang"))
        for base, key in ((BASE, ""), (BASE, "   "), ("", "test-only")):
            with self.subTest(base=base, key=key):
                code, bericht, daten = gate.netz_pruefen(base, key, holen=holen, repo=REPO)
                self.assertEqual(code, 2)
                self.assertEqual(daten["versuche"], 0)
                self.assertIn("NICHT geprüft", bericht)
        holen.assert_not_called()

    def test_transiente_netzfehler_heilen_im_lauf(self):
        holen = Mock(side_effect=[OSError("GIFT_GEHEIMNIS"), TimeoutError(), GUT])
        schlaf = Mock()
        code, bericht, daten = gate.netz_pruefen(
            BASE, "test-only", schreibschluessel="test-write-only",
            holen=holen, repo=REPO, pausen=(2, 8), schlaf=schlaf)
        self.assertEqual(code, 0)
        self.assertEqual(daten["versuche"], 3)
        self.assertEqual(holen.call_count, 3)
        self.assertEqual([c.args for c in schlaf.call_args_list], [(2,), (8,)])
        self.assertNotIn("GIFT_GEHEIMNIS", bericht)

    def test_dauerhafte_stoerung_wird_nicht_zu_befund(self):
        holen = Mock(side_effect=OSError("GIFT_GEHEIMNIS"))
        code, bericht, daten = gate.netz_pruefen(
            BASE, "test-only", holen=holen, repo=REPO, pausen=(0, 0), schlaf=lambda _: None)
        self.assertEqual(code, 2)
        self.assertEqual(holen.call_count, 3)
        self.assertEqual(daten["gemessen"], 0)
        self.assertEqual(daten["fehlend"], [])
        self.assertNotIn("GIFT_GEHEIMNIS", bericht)

    def test_zugangs_und_schemafehler_werden_nicht_sinnlos_wiederholt(self):
        for ergebnis in (gate.MessStoerung("Leseschlüssel abgelehnt."), {"ok": True}):
            with self.subTest(ergebnis=ergebnis):
                holen = Mock(side_effect=ergebnis) if isinstance(ergebnis, Exception) else Mock(return_value=ergebnis)
                schlaf = Mock()
                self.assertEqual(gate.netz_pruefen(BASE, "test-only", holen=holen,
                                                 repo=REPO, schlaf=schlaf)[0], 2)
                self.assertEqual(holen.call_count, 1)
                schlaf.assert_not_called()

    def test_unerwarteter_programmfehler_ist_keine_netzstoerung(self):
        with self.assertRaises(NameError):
            gate.netz_pruefen(BASE, "test-only", holen=Mock(side_effect=NameError("Code kaputt")),
                             repo=REPO, pausen=())


class HTTPGrenze(unittest.TestCase):
    def test_leseschluessel_nur_an_eigene_https_domain(self):
        for base in ("http://abos.franksfinanzcheck.de", "https://fremd.example",
                     BASE + "/anderer-pfad", BASE + "?key=test", BASE + "#fragment",
                     "https://name@abos.franksfinanzcheck.de", BASE + ":444",
                     "https://abos.franksfinanzcheck.de:ungueltig", "https:\n//abos.franksfinanzcheck.de"):
            with self.subTest(base=base), patch.object(gate.urllib.request, "build_opener") as bauen:
                with self.assertRaises(gate.MessStoerung):
                    gate.hole_healthz(base, "test-only")
                bauen.assert_not_called()

    def test_ungueltiger_header_schluessel_kann_nicht_im_traceback_erscheinen(self):
        for key in ("GIFT\nKEY", "GIFT\rKEY", "GIFT KEY", "GIFT_ä", ""):
            with self.subTest(key=key), patch.object(gate.urllib.request, "build_opener") as bauen:
                with self.assertRaises(gate.MessStoerung) as cm:
                    gate.hole_healthz(BASE, key)
                self.assertNotIn("GIFT", str(cm.exception))
                bauen.assert_not_called()

    def test_get_uebermittelt_schluessel_nur_als_header(self):
        with patch.object(gate.urllib.request, "build_opener") as bauen:
            bauen.return_value.open.return_value = io.BytesIO(json.dumps(GUT).encode())
            self.assertEqual(gate.hole_healthz(BASE, "test-only"), GUT)
            anfrage = bauen.return_value.open.call_args.args[0]
            self.assertEqual(anfrage.full_url, BASE + "/healthz")
            self.assertEqual(anfrage.get_header("X-ff-key"), "test-only")
            self.assertIsInstance(bauen.call_args.args[0], gate.KeineWeiterleitung)

    def test_weiterleitung_reicht_den_schluessel_nicht_durch(self):
        with self.assertRaises(gate.MessStoerung):
            gate.KeineWeiterleitung().redirect_request(None, None, 302, "", {}, "https://fremd.example")

    def test_503_mit_authentifiziertem_kv_befund_bleibt_auswertbar(self):
        stand = {**GUT, "ok": False, "kv": "fehler"}
        fehler = urllib.error.HTTPError(BASE + "/healthz", 503, "Unavailable", {},
                                       io.BytesIO(json.dumps(stand).encode()))
        with patch.object(gate.urllib.request, "build_opener") as bauen:
            bauen.return_value.open.side_effect = fehler
            self.assertEqual(gate.hole_healthz(BASE, "test-only"), stand)

    def test_503_mit_ok_true_wird_nicht_versehentlich_gruen(self):
        with patch.object(gate.urllib.request, "build_opener") as bauen:
            bauen.return_value.open.side_effect = urllib.error.HTTPError(
                BASE + "/healthz", 503, "Unavailable", {}, io.BytesIO(json.dumps(GUT).encode()))
            with self.assertRaises(gate.MessStoerung) as cm:
                gate.hole_healthz(BASE, "test-only")
            self.assertTrue(cm.exception.wiederholbar)

    def test_nicht_json_und_http_fehler_werden_ohne_rohinhalt_gemeldet(self):
        for status, wiederholbar in ((401, False), (403, False), (429, True), (500, True), (503, True)):
            with self.subTest(status=status), patch.object(gate.urllib.request, "build_opener") as bauen:
                bauen.return_value.open.side_effect = urllib.error.HTTPError(
                    BASE + "/healthz", status, "GIFT_GEHEIMNIS", {}, io.BytesIO(b"GIFT_GEHEIMNIS"))
                with self.assertRaises(gate.MessStoerung) as cm:
                    gate.hole_healthz(BASE, "test-only")
                self.assertEqual(cm.exception.wiederholbar, wiederholbar)
                self.assertNotIn("GIFT_GEHEIMNIS", str(cm.exception))

    def test_ungueltiges_json_und_zu_grosse_antwort_werden_abgewiesen(self):
        for roh in (b"GIFT_GEHEIMNIS", b"\xff", b"x" * (gate.MAX_ANTWORT + 1)):
            with self.subTest(laenge=len(roh)), patch.object(gate.urllib.request, "build_opener") as bauen:
                bauen.return_value.open.return_value = io.BytesIO(roh)
                with self.assertRaises(gate.MessStoerung) as cm:
                    gate.hole_healthz(BASE, "test-only")
                self.assertNotIn("GIFT_GEHEIMNIS", str(cm.exception))


class CLI(unittest.TestCase):
    def test_fehlender_zugang_liefert_trotzdem_json_und_bericht(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            bericht = Path(tmp) / "worker.md"
            ausgabe = io.StringIO()
            with contextlib.redirect_stdout(ausgabe):
                code = gate.main(["--json", "--report", str(bericht)])
            daten = json.loads(ausgabe.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(daten["klasse"], "STOERUNG")
            self.assertEqual(bericht.read_text(), daten["bericht"])

    def test_offline_ist_explizit_kein_live_nachweis(self):
        ausgabe = io.StringIO()
        with contextlib.redirect_stdout(ausgabe):
            code = gate.main(["--offline", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(ausgabe.getvalue())["klasse"], "OFFLINE")


if __name__ == "__main__":
    unittest.main()
