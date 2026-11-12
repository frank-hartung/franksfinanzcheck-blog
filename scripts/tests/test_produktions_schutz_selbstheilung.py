#!/usr/bin/env python3
"""Vertragstests der automatischen Selbstheilung (WF-829B / #922, 07.11.2026).

Jeder Test läuft offline. Das Netz wird ausschließlich über die injizierte
Testgrenze `transport=` nachgebaut; die Verdrahtung wird am echten Workflow
und am echten Deploy-Pfad geprüft, nicht an einer Kopie des Textes.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import produktions_schutz_selbstheilung as pss  # noqa: E402
import worker_environment_einrichten as einrichter  # noqa: E402
import worker_environment_guard as guard  # noqa: E402

REPO = "frank-hartung/franksfinanzcheck-blog"
TOKEN = "GIFT_GITHUB_TOKEN_NEVER_LOG"
ZEIT = "2026-11-07T00:00:00+00:00"


def vertrag():
    return pss.vertrag_laden(ROOT / pss.VERTRAG_PFAD)


def ergebnis(**kwargs):
    parameter = dict(repo=REPO, token=TOKEN, vertrag=vertrag(), ledger=None,
                     lauf="test", jetzt=ZEIT)
    parameter.update(kwargs)
    return pss.heilen(**parameter)


class VertragTests(unittest.TestCase):
    def test_01_vertrag_ist_gueltig_und_entspricht_den_regeln(self):
        daten = vertrag()
        self.assertEqual(pss.vertrag_fehler(daten), [])
        self.assertEqual(daten["environment"], guard.ENVIRONMENT)
        self.assertEqual(daten["zweig"], einrichter.ZWEIG)
        self.assertEqual(daten["ziele"], list(einrichter.ZIELE))
        self.assertIs(daten["nur_verschaerfen"], True)

    def test_02_jede_lockering_wird_abgelehnt(self):
        for aenderung in ({"nur_verschaerfen": False},
                          {"nur_verschaerfen": "true"},
                          {"ziele": ["reviewer"]},
                          {"dashboard_ziele": []},
                          {"environment": "github-pages"},
                          {"zweig": "develop"},
                          {"ledger": "../flucht.jsonl"},
                          {"ledger": "/etc/passwd"},
                          {"schema": 2},
                          {"reviewer_login": "kein login!"},
                          {"begruendung": ""},
                          {"extra": 1}):
            with self.subTest(aenderung=aenderung):
                probe = dict(vertrag())
                probe.update(aenderung)
                self.assertTrue(pss.vertrag_fehler(probe), aenderung)

    def test_03_doppelte_schluessel_sind_ein_bruch_kein_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "vertrag.json"
            pfad.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
            with self.assertRaises(pss.NichtBelegbar) as ctx:
                pss.vertrag_laden(pfad)
            self.assertIn("doppelte", str(ctx.exception))

    def test_04_unparsebarer_oder_fehlender_vertrag_ist_nicht_belegbar(self):
        with tempfile.TemporaryDirectory() as tmp:
            kaputt = Path(tmp) / "kaputt.json"
            kaputt.write_text("{", encoding="utf-8")
            with self.assertRaises(pss.NichtBelegbar):
                pss.vertrag_laden(kaputt)
            with self.assertRaises(pss.NichtBelegbar):
                pss.vertrag_laden(Path(tmp) / "fehlt.json")


class EichprobeTests(unittest.TestCase):
    def test_05_eichprobe_ist_gruen(self):
        self.assertEqual(pss.eichprobe(), [])

    def test_06_sabotage_am_pruefer_wird_erkannt(self):
        def immer_gruen(*_a, **_k):
            return [einrichter.Lage(z, einrichter.KLASSE_ERFUELLT, "ok", "")
                    for z in einrichter.ZIELE]

        with patch.object(einrichter, "planen", immer_gruen):
            self.assertTrue(pss.eichprobe())

    def test_07_zweiter_schreibweg_im_einrichter_wird_erkannt(self):
        with patch.object(einrichter, "SCHREIBEN_ERLAUBT",
                          {("PUT", "umgebung"), ("POST", "regeln"), ("DELETE", "umgebung")}):
            self.assertTrue(any("E5" in f for f in pss.eichprobe()))

    def test_08_sabotiertes_messgeraet_urteilt_nicht_und_schreibt_nicht(self):
        transport = pss.Transport()

        def immer_gruen(*_a, **_k):
            return [einrichter.Lage(z, einrichter.KLASSE_ERFUELLT, "ok", "")
                    for z in einrichter.ZIELE]

        with patch.object(einrichter, "planen", immer_gruen):
            erg = ergebnis(transport=transport)
        self.assertEqual(erg.klasse, pss.KLASSE_MESSGERAET)
        self.assertEqual(erg.code, 3)
        self.assertEqual([m for m, _u, _k in transport.rufe if m != "GET"], [])
        self.assertIn("E1", " ".join(erg.lage.gruende))


class HeilungsTests(unittest.TestCase):
    def test_09_vorfall_wird_teilweise_geheilt_und_nachgemessen(self):
        t = pss.Transport()
        erg = ergebnis(transport=t)
        # Der Bypass wurde NICHT gesendet und bleibt an: Ein realistischer
        # Stub darf daraus kein vollständig „geheilt“ erfinden.
        self.assertEqual(erg.klasse, pss.KLASSE_OFFEN)
        self.assertEqual(erg.code, 1)
        self.assertEqual(erg.lage.vorher["reviewer"], einrichter.KLASSE_MACHBAR)
        self.assertEqual(erg.lage.nachher["reviewer"], einrichter.KLASSE_ERFUELLT)
        self.assertEqual(erg.lage.nachher["branch"], einrichter.KLASSE_ERFUELLT)
        self.assertEqual(erg.lage.nachher["bypass"], einrichter.KLASSE_OBERFLAECHE)
        self.assertEqual(erg.beleg["eichprobe"], "bestanden")
        self.assertTrue(erg.lage.schritte)

    def test_10_nur_zwei_erlaubte_schreibwege_und_kein_bypass_im_koerper(self):
        t = pss.Transport()
        ergebnis(transport=t)
        schreibend = [(m, k) for m, _u, k in t.rufe if m in ("PUT", "POST")]
        self.assertEqual(len(schreibend), 2)
        self.assertEqual([m for m, _k in schreibend], ["PUT", "POST"])
        put_koerper = next(k for m, k in schreibend if m == "PUT")
        self.assertIn("reviewers", put_koerper)
        self.assertNotIn("can_admins_bypass", json.dumps(put_koerper))
        self.assertFalse(any(m == "DELETE" for m, _u, _k in t.rufe))

    def test_11_teilheilung_ist_niemals_vollstaendig_gruen(self):
        t = pss.Transport(danach={**pss.SICHER, "can_admins_bypass": True})
        erg = ergebnis(transport=t)
        self.assertEqual(erg.klasse, pss.KLASSE_OFFEN)
        self.assertEqual(erg.code, 1)
        self.assertTrue(erg.lage.schritte)
        self.assertEqual(erg.lage.nachher["bypass"], einrichter.KLASSE_OBERFLAECHE)
        self.assertTrue(any("bleiben offen" in g for g in erg.lage.gruende))

    def test_12_sicherer_zustand_ist_idempotent(self):
        t = pss.Transport(umgebung=dict(pss.SICHER), danach=dict(pss.SICHER),
                          regeln=list(pss.REGELN_MAIN))
        erg = ergebnis(transport=t)
        self.assertEqual(erg.klasse, pss.KLASSE_SICHER)
        self.assertEqual(erg.code, 0)
        self.assertEqual([m for m, _u, _k in t.rufe if m != "GET"], [])
        self.assertEqual(erg.lage.schritte, [])

    def test_13_http_403_ist_rechtebefund_und_nie_gruen(self):
        t = pss.Transport(schreiben=403)
        erg = ergebnis(transport=t)
        self.assertEqual(erg.klasse, pss.KLASSE_OFFEN)
        self.assertEqual(erg.code, 1)
        self.assertTrue(any(pss.KLASSE_RECHT in g for g in erg.lage.gruende))
        self.assertTrue(any("Administration: write" in g for g in erg.lage.gruende))
        self.assertNotIn("Environments: write", " ".join(erg.lage.gruende))
        self.assertTrue(any(pss.KLASSE_OBERFLAECHE in g for g in erg.lage.gruende))
        self.assertEqual(erg.lage.schritte, [])
        self.assertEqual(erg.lage.nachher["reviewer"], einrichter.KLASSE_MACHBAR)

    def test_14_schreibfehler_ohne_rechtebezug_ist_nicht_belegbar(self):
        def streik(_methode, _url, _token, _koerper):
            return 500, {}, b"{}"

        erg = ergebnis(transport=streik)
        self.assertEqual(erg.code, 2)

    def test_15_lesefehler_ist_nicht_belegbar_und_nie_ein_befund(self):
        def kaputt(_methode, _url, _token, _koerper):
            raise einrichter.WerkzeugFehler("Netz weg")

        erg = ergebnis(transport=kaputt)
        self.assertEqual(erg.klasse, pss.KLASSE_NICHT_BELEGBAR)
        self.assertEqual(erg.code, 2)
        self.assertEqual(erg.lage.nachher, {})

    def test_16_verschlechterung_bricht_ab(self):
        self.assertEqual(pss.verschlechterungen(
            {"reviewer": "ERFUELLT"}, {"reviewer": "MACHBAR"}),
            ["reviewer: ERFUELLT → MACHBAR"])
        self.assertEqual(pss.verschlechterungen(
            {"reviewer": "MACHBAR"}, {"reviewer": "ERFUELLT"}), [])
        self.assertTrue(pss.verschlechterungen(
            {"reviewer": "ERFUELLT"}, {"branch": "ERFUELLT"}))

    def test_17_fehlender_nachweis_nach_schreiben_ist_exit_2_und_benennt_teilaktion(self):
        # Selbst wenn GitHub beide Requests annimmt: fehlt danach der Reviewer,
        # gibt es kein Grün und die bereits angenommenen Schritte bleiben sichtbar.
        danach = {**pss.SICHER, "protection_rules": []}
        t = pss.Transport(danach=danach)
        erg = ergebnis(transport=t)
        self.assertEqual(erg.klasse, pss.KLASSE_NICHT_BELEGBAR)
        self.assertEqual(erg.code, 2)
        self.assertEqual(len(erg.lage.schritte), 2)
        self.assertTrue(any("Nachmessung" in g for g in erg.lage.gruende))

    def test_17a_bereits_geschuetztes_environment_wird_nicht_geaendert(self):
        start = {**pss.SICHER, "deployment_branch_policy": None}
        t = pss.Transport(umgebung=start)
        erg = ergebnis(transport=t)
        self.assertEqual(erg.klasse, pss.KLASSE_OFFEN)
        self.assertEqual(erg.lage.nachher["branch"], einrichter.KLASSE_ABWEICHUNG)
        self.assertFalse([m for m, _u, _k in t.rufe if m != "GET"])

    def test_17b_abweichung_bedeutet_nicht_automatisch_lockere_policy(self):
        self.assertEqual(pss.verschlechterungen(
            {"branch": "MACHBAR"}, {"branch": "ABWEICHUNG"}), [])

    def test_17c_verweigerter_branch_post_meldet_bereits_angenommenen_put(self):
        class PostVerweigert(pss.Transport):
            def __call__(self, methode, url, token, koerper):
                if methode == "POST":
                    self.rufe.append((methode, url, koerper))
                    return 403, {}, b"{}"
                return super().__call__(methode, url, token, koerper)

        erg = ergebnis(transport=PostVerweigert())
        self.assertEqual(erg.klasse, pss.KLASSE_OFFEN)
        self.assertEqual(len(erg.lage.schritte), 1)
        self.assertIn("Environment-PUT", erg.lage.schritte[0])
        self.assertEqual(erg.lage.nachher["branch"], einrichter.KLASSE_ABWEICHUNG)
        self.assertTrue(any("RECHT" in g for g in erg.lage.gruende))

    def test_17d_404_wird_nicht_automatisch_angelegt(self):
        rufe = []

        def nicht_sichtbar(methode, url, token, koerper):
            rufe.append(methode)
            return 404, {}, b"{}"

        erg = ergebnis(transport=nicht_sichtbar)
        self.assertEqual(erg.klasse, pss.KLASSE_NICHT_BELEGBAR)
        self.assertEqual(erg.code, 2)
        self.assertEqual(erg.lage.nachher, {})
        self.assertIn("404", " ".join(erg.lage.gruende))
        self.assertEqual(rufe, ["GET"])

    def test_17e_serverfehler_nach_schreibversuch_ist_nicht_belegbar(self):
        for methode_mit_fehler in ("PUT", "POST"):
            with self.subTest(methode=methode_mit_fehler):
                class Serverfehler(pss.Transport):
                    def __call__(self, methode, url, token, koerper):
                        antwort = super().__call__(methode, url, token, koerper)
                        return (500, {}, b"{}") if methode == methode_mit_fehler else antwort

                erg = ergebnis(transport=Serverfehler())
                self.assertEqual(erg.klasse, pss.KLASSE_NICHT_BELEGBAR)
                self.assertEqual(erg.code, 2)
                self.assertIn(methode_mit_fehler, " ".join(erg.lage.schritte))
                self.assertIn("unbekannt", " ".join(erg.lage.schritte))
                self.assertIn("HTTP 500", " ".join(erg.lage.gruende))
                self.assertIn("unbekannt", pss.als_md(erg))

    def test_18_pruefen_schreibt_nicht(self):
        t = pss.Transport()
        parameter = dict(repo=REPO, token=TOKEN, vertrag=vertrag(), transport=t,
                         ledger=None, lauf="test", jetzt=ZEIT,
                         schreiben_erlaubt=False)
        erg = pss.heilen(**parameter)
        self.assertEqual([m for m, _u, _k in t.rufe if m != "GET"], [])
        self.assertEqual(erg.klasse, pss.KLASSE_OFFEN)

    def test_19_bericht_enthält_weder_token_noch_fremdtext(self):
        erg = ergebnis(transport=pss.Transport(schreiben=403))
        text = pss.als_md(erg)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("Bearer", text)
        self.assertIn("OFFEN", text)
        self.assertIn("vorher", text)
        self.assertIn("nachher", text)

    def test_20_kein_pfad_zu_freigabe_oder_secrets_im_ausfuehrbaren_code(self):
        # Geprüft wird der CODE, nicht die Dokumentation: Der Modul-Docstring
        # nennt `pending_deployments` ausdrücklich als das, was verboten ist.
        import ast
        quelle = (ROOT / pss.SKRIPT).read_text(encoding="utf-8")
        baum = ast.parse(quelle)
        baum.body = [k for k in baum.body if not (
            isinstance(k, ast.Expr) and isinstance(k.value, ast.Constant)
            and isinstance(k.value.value, str))]
        code = ast.unparse(baum)
        # Der einzige Netzweg ist der bereits begrenzte `_senden` des
        # Einrichters. Ein eigener HTTP-Aufruf wäre ein zweiter Wahrheitsweg.
        for verboten in ("urllib.request", "urlopen(", "build_opener(", "Request("):
            with self.subTest(verboten=verboten):
                self.assertNotIn(verboten, code)
        # Und der Heil-Lauf selbst führt keine Deploy-Freigabe und keine
        # Fremd-Secrets – das prüft die Verdrahtungs-Wache am echten Workflow.
        wf = (ROOT / pss.ARBEITSFLUSS).read_text(encoding="utf-8")
        self.assertNotIn("pending_deployments", wf)
        self.assertNotIn("CF_WORKERS_DEPLOY_TOKEN", wf)
        self.assertNotIn("CLOUDFLARE_ACCOUNT_ID", wf)


class BelegkettenTests(unittest.TestCase):
    def test_21_anhaengen_erzeugt_eine_gueltige_kette(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "kette.jsonl"
            eins = pss.ledger_anhaengen(pfad, {"art": "messung", "ergebnis": "OFFEN"})
            zwei = pss.ledger_anhaengen(pfad, {"art": "messung", "ergebnis": "SICHER"})
            self.assertEqual([eins["seq"], zwei["seq"]], [1, 2])
            self.assertEqual(zwei["prev_sha256"], eins["sha256"])
            self.assertEqual(pss.ledger_zeilen_pruefen(pfad.read_text().splitlines()), [])
            self.assertEqual(pss.ledger_pruefen(pfad), [])

    def test_22_manipulation_wird_erkannt(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "kette.jsonl"
            pss.ledger_anhaengen(pfad, {"art": "messung", "ergebnis": "OFFEN"})
            zeilen = pfad.read_text(encoding="utf-8").splitlines()
            eintrag = json.loads(zeilen[0])
            eintrag["ergebnis"] = "SICHER"     # Ergebnis nachträglich umschreiben
            self.assertTrue(pss.ledger_zeilen_pruefen([json.dumps(eintrag)]))
            self.assertTrue(pss.ledger_zeilen_pruefen(["kein JSON"]))
            self.assertTrue(pss.ledger_zeilen_pruefen(['{"a":1,"a":2}']))
            self.assertTrue(pss.ledger_zeilen_pruefen(zeilen + zeilen))

    def test_23_kaputte_kette_wird_nicht_ueberschrieben(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "kette.jsonl"
            pfad.write_text('{"seq": 1, "sha256": "x"}\n', encoding="utf-8")
            with self.assertRaises(pss.KetteKaputt):
                pss.ledger_anhaengen(pfad, {"art": "messung"})
            self.assertEqual(len(pfad.read_text().splitlines()), 1)

    def test_24_geheimnisspur_kommt_nicht_in_die_kette(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "kette.jsonl"
            with self.assertRaises(pss.NichtBelegbar):
                pss.ledger_anhaengen(pfad, {"art": "messung", "token": "Bearer ghp_geheim"})
            self.assertFalse(pfad.exists())

    def test_25_bestandskette_ist_heil(self):
        self.assertEqual(pss.ledger_pruefen(ROOT / pss.LEDGER_PFAD), [])


class VerdrahtungsTests(unittest.TestCase):
    def setUp(self):
        self.wf = (ROOT / pss.ARBEITSFLUSS).read_text(encoding="utf-8")
        self.deploy = (ROOT / pss.DEPLOY_FLUSS).read_text(encoding="utf-8")

    def test_26_echte_verdrahtung_ist_heil(self):
        self.assertEqual(pss.verdrahtung(self.wf, self.deploy, root=ROOT), [])
        self.assertEqual(pss.wache(root=ROOT), [])

    def test_27_heilschritt_nur_im_kommentar_zaehlt_nicht(self):
        text = self.wf.replace(" --heilen ", " # --heilen ")
        self.assertTrue(any("W1" in f for f in pss.verdrahtung(text, self.deploy, root=ROOT)))

    def test_28_entfernter_heilschritt_wird_befund(self):
        text = self.wf.replace(" --heilen ", " --pruefen ")
        self.assertTrue(any("W1" in f for f in pss.verdrahtung(text, self.deploy, root=ROOT)))

    def test_29_tageslauf_und_ereignisheilung_sind_pflicht(self):
        for ersatz in ("  schedule:", "  workflow_run:"):
            with self.subTest(ersatz=ersatz):
                text = self.wf.replace(ersatz, "  #" + ersatz.strip() + ":")
                self.assertTrue(any("W2" in f for f in pss.verdrahtung(text, self.deploy, root=ROOT)))

    def test_30_asymmetrischer_pfadfilter_wird_befund(self):
        text = self.wf.replace(f'      - "{pss.SKRIPT}"\n', "", 1)
        self.assertTrue(any("W4" in f for f in pss.verdrahtung(text, self.deploy, root=ROOT)))

    def test_31_harter_stopp_im_deploy_darf_nicht_verschwinden(self):
        self.assertTrue(pss.verdrahtung(self.wf, "", root=ROOT))
        ersetzt = self.deploy.replace("worker_environment_guard.py --check",
                                     "worker_environment_einrichten.py --anwenden")
        self.assertTrue(any("W5" in f for f in pss.verdrahtung(self.wf, ersetzt, root=ROOT)))

    def test_32_selbstfreigabe_und_fremdsecrets_sind_gesperrt(self):
        for zusatz in ("\n# pending_deployments\n", "\n# CF_WORKERS_DEPLOY_TOKEN\n"):
            with self.subTest(zusatz=zusatz.strip()):
                self.assertTrue(any("W3" in f for f in pss.verdrahtung(
                    self.wf + zusatz, self.deploy, root=ROOT)))

    def test_33_einzeilige_run_bloecke_werden_mitgezaehlt(self):
        self.assertIn("worker_environment_guard.py --check",
                      "\n".join(pss.run_bloecke(self.deploy)))

    def test_34_pfadfilter_sind_symmetrisch_und_vollstaendig(self):
        links = pss.pfadliste(self.wf, "push")
        rechts = pss.pfadliste(self.wf, "pull_request")
        self.assertEqual(set(links), set(rechts))
        self.assertTrue(set(pss.PFlicht_PFADE) <= set(links))


class KommandozeilenTests(unittest.TestCase):
    def _rufe(self, argv, umgebung=None):
        umgebung = umgebung or {"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN}
        puffer = io.StringIO()
        with patch.dict(os.environ, umgebung, clear=True), \
             patch.object(sys, "argv", ["produktions_schutz_selbstheilung.py"] + argv), \
             contextlib.redirect_stdout(puffer):
            code = pss.main()
        return code, puffer.getvalue()

    def test_35_selftest_ist_gruen(self):
        code, text = self._rufe(["--selftest"])
        self.assertEqual(code, 0, text)
        self.assertIn("SELBSTTEST OK", text)

    def test_36_wache_ist_gruen(self):
        code, text = self._rufe(["--wache"])
        self.assertEqual(code, 0, text)
        self.assertIn("Verdrahtungs-Wache", text)

    def test_37_json_ausgabe_ist_vollstaendig(self):
        erg = pss.Ergebnis(pss.KLASSE_OFFEN, 1,
                           pss.Lage({"reviewer": "MACHBAR"}, {"reviewer": "MACHBAR"},
                                    [], ["RECHT"]),
                           {"eichprobe": "bestanden"})
        puffer = io.StringIO()
        with patch.object(pss, "heilen", return_value=erg), \
             patch.object(pss, "vertrag_laden", return_value=vertrag()), \
             patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN}), \
             patch.object(sys, "argv", ["x", "--pruefen", "--json"]), \
             contextlib.redirect_stdout(puffer):
            code = pss.main()
        daten = json.loads(puffer.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(daten["ergebnis"], pss.KLASSE_OFFEN)
        self.assertEqual(daten["nachher"]["reviewer"], "MACHBAR")

    def test_38_fehlendes_token_ist_exit_2_keine_ausnahme(self):
        code, text = self._rufe(["--pruefen"], {"GITHUB_REPOSITORY": REPO})
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", text)


if __name__ == "__main__":
    unittest.main()
