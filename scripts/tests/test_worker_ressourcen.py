"""Vertrag der produktionsnahen Worker-Ressourcen-Auflösung (WF-E813/#815)."""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_ressourcen as wr  # noqa: E402

KONTO = "a" * 32
KV = "b" * 32
D1 = "12345678-1234-1234-1234-123456789abc"
TOKEN = "GIFT_TOKEN_NIEMALS_LOGGEN"


def env(**extra):
    return {
        "CLOUDFLARE_API_TOKEN": TOKEN,
        "CLOUDFLARE_ACCOUNT_ID": KONTO,
        **extra,
    }


def settings(bindings):
    return {"success": True, "result": {"bindings": bindings}}


class Aufloesung(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(wr.selftest(), 0)

    def test_kv_wird_aus_bestehender_produktionsbindung_gelesen(self):
        holen = Mock(return_value=settings([
            {"type": "kv_namespace", "name": "ABO", "namespace_id": KV},
        ]))
        ergebnis = wr.aufloesen("newsletter-worker", env(), holen=holen)
        self.assertEqual(ergebnis.wert, KV)
        self.assertEqual(ergebnis.ressource.variable, "KV_NAMESPACE_ID_ABO")
        holen.assert_called_once_with(TOKEN, KONTO, "ff-newsletter")

    def test_d1_wird_aus_bestehender_produktionsbindung_gelesen(self):
        holen = Mock(return_value=settings([
            {"type": "d1", "name": "DB", "id": D1},
        ]))
        ergebnis = wr.aufloesen("klick-zaehler", env(), holen=holen)
        self.assertEqual(ergebnis.wert, D1)
        holen.assert_called_once_with(TOKEN, KONTO, "klick-zaehler")

    def test_explizite_variable_bleibt_fuer_bootstrap_und_bestand_kompatibel(self):
        holen = Mock(side_effect=AssertionError("Netzaufruf trotz expliziter ID"))
        ergebnis = wr.aufloesen(
            "newsletter-worker", env(KV_NAMESPACE_ID_ABO=KV.upper()), holen=holen)
        self.assertEqual(ergebnis.wert, KV)
        self.assertEqual(ergebnis.quelle, "Repository-Variable")
        holen.assert_not_called()

    def test_ungueltige_explizite_id_faellt_nicht_auf_andere_ressource_zurueck(self):
        holen = Mock(return_value=settings([
            {"type": "kv_namespace", "name": "ABO", "namespace_id": KV},
        ]))
        with self.assertRaisesRegex(wr.RessourcenFehler, "kein gültiges Format"):
            wr.aufloesen("newsletter-worker", env(KV_NAMESPACE_ID_ABO="ABO"), holen=holen)
        holen.assert_not_called()

    def test_worker_ohne_ressource_braucht_keine_zugaenge(self):
        self.assertIsNone(wr.aufloesen("ki-assistent", {}))

    def test_unbekannter_worker_ist_fail_closed(self):
        with self.assertRaisesRegex(wr.RessourcenFehler, "Unbekannter Worker"):
            wr.aufloesen("unbekannt", {})


class Bindungsvertrag(unittest.TestCase):
    def setUp(self):
        self.ressource = wr.RESSOURCEN["newsletter-worker"]

    def test_fehlende_bindung_wird_nicht_erraten(self):
        with self.assertRaisesRegex(wr.RessourcenFehler, "genau eine produktive ABO-Bindung"):
            wr.binding_id(settings([]), self.ressource)

    def test_falscher_name_oder_typ_reicht_nicht(self):
        for binding in (
            {"type": "kv_namespace", "name": "ANDERES", "namespace_id": KV},
            {"type": "d1", "name": "ABO", "id": D1},
        ):
            with self.subTest(binding=binding), self.assertRaises(wr.RessourcenFehler):
                wr.binding_id(settings([binding]), self.ressource)

    def test_mehrdeutige_bindung_ist_gesperrt(self):
        binding = {"type": "kv_namespace", "name": "ABO", "namespace_id": KV}
        with self.assertRaisesRegex(wr.RessourcenFehler, "gefunden: 2"):
            wr.binding_id(settings([binding, binding]), self.ressource)

    def test_ungueltige_oder_fehlende_id_ist_gesperrt(self):
        for wert in (None, "ABO", "x" * 32, 42):
            with self.subTest(wert=wert), self.assertRaises(wr.RessourcenFehler):
                wr.binding_id(settings([
                    {"type": "kv_namespace", "name": "ABO", "namespace_id": wert},
                ]), self.ressource)

    def test_kaputte_antworthuellen_sind_gesperrt(self):
        for antwort in (None, {}, {"success": False}, {"success": True, "result": {}},
                        {"success": True, "result": {"bindings": "ABO"}}):
            with self.subTest(antwort=antwort), self.assertRaises(wr.RessourcenFehler):
                wr.binding_id(antwort, self.ressource)


class ZugangUndTransport(unittest.TestCase):
    def test_fehlende_zugaenge_nennen_environment_ohne_netzaufruf(self):
        holen = Mock(side_effect=AssertionError("unerwarteter Netzaufruf"))
        for umgebung, stichwort in (({}, "CF_WORKERS_DEPLOY_TOKEN"),
                                    ({"CLOUDFLARE_API_TOKEN": TOKEN}, "CLOUDFLARE_ACCOUNT_ID"),
                                    (env(CLOUDFLARE_ACCOUNT_ID="konto"), "32-Hex")):
            with self.subTest(stichwort=stichwort), self.assertRaisesRegex(wr.RessourcenFehler, stichwort):
                wr.aufloesen("newsletter-worker", umgebung, holen=holen)
        holen.assert_not_called()

    def test_http_fehler_ist_verstaendlich_und_gibt_token_nicht_aus(self):
        class Opener:
            def open(self, anfrage, timeout):
                raise urllib.error.HTTPError(
                    anfrage.full_url, 403, "forbidden", {}, io.BytesIO(b"GIFT_ROHANTWORT"))

        with patch("urllib.request.build_opener", return_value=Opener()):
            with self.assertRaises(wr.RessourcenFehler) as gefangen:
                wr._einstellungen_holen(TOKEN, KONTO, "ff-newsletter")
        text = str(gefangen.exception)
        self.assertIn("HTTP 403", text)
        self.assertIn("Workers Scripts: Read", text)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("GIFT_ROHANTWORT", text)

    def test_exakter_endpoint_und_keine_fremden_urls(self):
        gesehen = []

        class Antwort:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return json.dumps(settings([
                    {"type": "kv_namespace", "name": "ABO", "namespace_id": KV},
                ])).encode()

        class Opener:
            def open(self, anfrage, timeout):
                gesehen.append((anfrage.full_url, timeout))
                return Antwort()

        with patch("urllib.request.build_opener", return_value=Opener()):
            antwort = wr._einstellungen_holen(TOKEN, KONTO, "ff-newsletter")
        self.assertEqual(wr.binding_id(antwort, wr.RESSOURCEN["newsletter-worker"]), KV)
        self.assertEqual(gesehen, [(
            f"{wr.CF_API}/accounts/{KONTO}/workers/scripts/ff-newsletter/settings", 30)])

    def test_redirect_handler_gibt_token_nicht_weiter(self):
        handler = wr._KeineWeiterleitung()
        with self.assertRaises(OSError):
            handler.redirect_request(None, None, 302, "Found", {}, "https://fremd.invalid")


class TransportVertrag(unittest.TestCase):
    """Enge T6-Ausnahme: nur Cloudflare-Verwaltung, niemals Modellverkehr."""

    def test_ausnahme_ist_im_gate_eingetragen(self):
        gate = (ROOT / "scripts" / "ki_transportweg.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/worker_ressourcen.py")', gate)

    def test_nur_fester_settings_endpoint_und_kein_modellaufruf(self):
        quelltext = (ROOT / "scripts" / "worker_ressourcen.py").read_text(encoding="utf-8")
        hosts = set(re.findall(r"https://([a-z0-9.-]+)", quelltext))
        self.assertEqual(hosts, {"api.cloudflare.com"})
        self.assertIn('CF_API = "https://api.' + 'cloudflare.com/client/v4"', quelltext)
        self.assertIn('/workers/scripts/{script}/settings', quelltext)
        for verboten in ("/ai/run", "/ai/", "generativelanguage", "api.groq.com",
                         "nvidia", "pollinations", "llm_client", "/chat/completions",
                         "workers.ai"):
            self.assertNotIn(verboten, quelltext)

    def test_script_ausserhalb_der_allowlist_erreicht_das_netz_nicht(self):
        with patch("urllib.request.build_opener") as opener:
            with self.assertRaisesRegex(wr.RessourcenFehler, "Workername"):
                wr._einstellungen_holen(TOKEN, KONTO, "beliebiger-worker")
        opener.assert_not_called()


class CliUndWorkflow(unittest.TestCase):
    def test_cli_schreibt_id_nur_in_output_nicht_in_log_oder_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "output"
            summary = root / "summary"
            umgebung = env(GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = wr.befehl_aufloesen(
                    "newsletter-worker", umgebung,
                    holen=lambda *_: settings([
                        {"type": "kv_namespace", "name": "ABO", "namespace_id": KV},
                    ]))
            self.assertEqual(code, 0)
            self.assertEqual(output.read_text(), f"kv_namespace_id_abo={KV}\n")
            oeffentlich = stdout.getvalue() + summary.read_text()
            self.assertIn("bestehende ABO-Bindung", oeffentlich)
            self.assertNotIn(KV, oeffentlich)
            self.assertNotIn(TOKEN, oeffentlich)

    def test_cli_fehler_ist_rot_und_leakt_keine_rohdaten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            umgebung = env(GITHUB_OUTPUT=str(output))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = wr.befehl_aufloesen(
                    "newsletter-worker", umgebung,
                    holen=lambda *_: settings([{
                        "type": "kv_namespace", "name": "ABO", "namespace_id": "GIFT_ROHWERT",
                    }]))
            self.assertEqual(code, 1)
            self.assertIn("::error::", stdout.getvalue())
            self.assertIn("fail-closed", stdout.getvalue())
            self.assertNotIn("GIFT_ROHWERT", stdout.getvalue())
            self.assertFalse(output.exists())

    def test_workflow_loest_vor_config_und_deploy_im_geschuetzten_environment_auf(self):
        text = (ROOT / ".github" / "workflows" / "worker-deploy.yml").read_text(encoding="utf-8")
        resolver = text.index("python3 scripts/worker_ressourcen.py --aufloesen")
        vorbereiten = text.index("worker_deploy_vorbereiten.py --vorbereiten")
        deploy = text.index("wrangler deploy --config")
        self.assertLess(resolver, vorbereiten)
        self.assertLess(vorbereiten, deploy)
        deploy_job = text.split("  deploy:\n", 1)[1]
        self.assertIn("name: cloudflare-produktion", deploy_job)
        self.assertIn("secrets.CF_WORKERS_DEPLOY_TOKEN", deploy_job)
        self.assertIn("steps.ressourcen.outputs.kv_namespace_id_abo", deploy_job)
        self.assertIn("steps.ressourcen.outputs.d1_database_id", deploy_job)
        self.assertNotIn("secrets.CLOUDFLARE_API_TOKEN", deploy_job)

    def test_deploy_kette_ist_in_sicherheitsworkflow_und_manifest_verdrahtet(self):
        sicherheit = (ROOT / ".github" / "workflows" / "sicherheits-wache.yml").read_text(encoding="utf-8")
        paket = (ROOT / "package.json").read_text(encoding="utf-8")
        for text in (sicherheit, paket):
            self.assertIn("worker_ressourcen.py", text)
            self.assertIn("test_worker_ressourcen", text)


if __name__ == "__main__":
    unittest.main()
