"""Vertrag des Worker-Deploys (Sicherheitsaudit 14.10.2026, M-14)."""
from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

try:
    import yaml
except ImportError:  # pragma: no cover - stdlib-Fallback für reine Offline-Runner
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_deploy_vorbereiten as wdv  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "worker-deploy.yml"


class Selbsttest(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(wdv._selftest(), 0)

    def test_alle_worker_ohne_workers_dev(self):
        for name, cfg in wdv.WORKER.items():
            text = (ROOT / cfg["verzeichnis"] / "wrangler.toml").read_text(encoding="utf-8")
            ohne = wdv._toml_ohne_kommentare(text)
            self.assertRegex(ohne, wdv.WORKERS_DEV_FALSE, f"{name}: workers_dev = false fehlt")
            self.assertNotRegex(ohne, wdv.WORKERS_DEV_TRUE, f"{name}: workers_dev = true")

    def test_platzhalter_werden_mit_gueltigen_ids_ersetzt(self):
        umgebung = {"KV_NAMESPACE_ID_ABO": "0123456789abcdef0123456789abcdef",
                    "D1_DATABASE_ID": "01234567-89ab-cdef-0123-456789abcdef"}
        for name in ("newsletter-worker", "klick-zaehler"):
            ok, gruende, text = wdv.pruefe(name, umgebung)
            self.assertTrue(ok, f"{name}: {gruende}")
            self.assertIsNone(wdv.PLATZHALTER_RE.search(wdv._toml_ohne_kommentare(text)))

    def test_ki_assistent_nie_automatisch(self):
        self.assertNotIn("ki-assistent", wdv.plan({"EREIGNIS": "push", "GEAENDERT": "*"}))
        self.assertEqual(wdv.plan({"EREIGNIS": "workflow_dispatch", "AUSWAHL": "ki-assistent",
                                   "REF": "refs/heads/main"}), ["ki-assistent"])
        self.assertEqual(wdv.plan({"EREIGNIS": "workflow_dispatch", "AUSWAHL": "ki-assistent",
                                   "REF": "refs/heads/arena/feature"}), [])


class WorkflowVertrag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.wf = yaml.safe_load(cls.text) if yaml is not None else None

    def test_deploy_braucht_environment_freigabe(self):
        if self.wf is not None:
            job = self.wf["jobs"]["deploy"]
            self.assertEqual(job["environment"]["name"], "cloudflare-produktion")
        else:
            self.assertRegex(self.text, r"environment:\s*\n\s+name:\s*cloudflare-produktion")

    def test_minimalrechte_und_keine_persistierten_credentials(self):
        if self.wf is not None:
            self.assertEqual(self.wf["permissions"], {"contents": "read"})
            for job in self.wf["jobs"].values():
                for schritt in job["steps"]:
                    if str(schritt.get("uses", "")).startswith("actions/checkout@"):
                        self.assertIs(schritt["with"]["persist-credentials"], False)
        else:
            self.assertRegex(self.text, r"permissions:\s*\n\s+contents:\s*read")
            self.assertEqual(self.text.count("actions/checkout@"),
                             self.text.count("persist-credentials: false"))

    def test_eigener_deploy_token_nicht_der_workers_ai_token(self):
        self.assertIn("secrets.CF_WORKERS_DEPLOY_TOKEN", self.text)
        self.assertNotIn("secrets.CLOUDFLARE_API_TOKEN", self.text)

    def test_wrangler_gepinnt_ohne_install_skripte(self):
        self.assertIn("npm ci --ignore-scripts", self.text)
        self.assertNotIn("npx wrangler", self.text)
        paket = (ROOT / "tools" / "wrangler" / "package.json").read_text(encoding="utf-8")
        self.assertRegex(paket, r'"wrangler":\s*"\d+\.\d+\.\d+"')

    def test_815_deploy_job_prueft_live_nachweis_nach_wrangler(self):
        pos_deploy = self.text.find("wrangler deploy")
        pos_nachweis = self.text.find('worker_deploy_vorbereiten.py --nachweis "$WORKER"')
        self.assertGreater(pos_deploy, -1)
        self.assertGreater(pos_nachweis, pos_deploy,
                           "Nach wrangler deploy muss der Live-Build-Stempel geprüft werden")

    def test_922_deploy_und_nachweis_sind_eigene_obligatorische_schritte(self):
        deploy = self.text.split("  deploy:\n", 1)[1].split("\n  abschluss:\n", 1)[0]
        schritt = deploy.split("- name: Deploy-Nachweis\n", 1)[1]
        self.assertLess(deploy.index("wrangler deploy --config"), deploy.index("- name: Deploy-Nachweis"))
        self.assertIn('python3 scripts/worker_deploy_vorbereiten.py --nachweis "$WORKER"', schritt)
        self.assertIn("set -euo pipefail", schritt)
        self.assertNotRegex(schritt, r"(?m)^\s+(if|continue-on-error):")


class KeinScheinGruen815(unittest.TestCase):
    """WF-E813/#815: Kein Skip-Grün; produktive Bindung statt Kopierzwang."""

    def test_manueller_deploy_ohne_kv_variable_bleibt_in_der_deploy_matrix(self):
        code, bereit, ann, summary = wdv.plan_auswerten(
            {"EREIGNIS": "workflow_dispatch", "AUSWAHL": "newsletter-worker",
             "REF": "refs/heads/main"})
        self.assertEqual(code, 0)
        self.assertEqual(bereit, ["newsletter-worker"])
        self.assertEqual(ann, [])
        self.assertIn("bestehender Produktions-Bindung", summary)
        self.assertIn("keinen Ersatzspeicher", summary)

    def test_manueller_deploy_auf_nicht_main_scheitert_vor_dem_environment(self):
        code, bereit, ann, summary = wdv.plan_auswerten(
            {"EREIGNIS": "workflow_dispatch", "AUSWAHL": "newsletter-worker",
             "REF": "refs/heads/arena/untrusted"})
        self.assertEqual(code, 1)
        self.assertEqual(bereit, [])
        self.assertTrue(any("ausschließlich" in a for a in ann))
        self.assertIn("kein Produktions-Environment", summary)

    def test_push_ohne_kv_variable_wird_nicht_mehr_gruen_uebersprungen(self):
        code, bereit, ann, summary = wdv.plan_auswerten(
            {"EREIGNIS": "push", "GEAENDERT": "newsletter-worker/src/index.js"})
        self.assertEqual(code, 0)
        self.assertEqual(bereit, ["newsletter-worker"])
        self.assertEqual(ann, [])
        self.assertNotIn("NICHT deployt", summary)

    def test_deploy_werkzeug_aenderung_rollt_beide_produktiven_worker_aus(self):
        for datei in ("scripts/worker_ressourcen.py", "scripts/worker_environment_guard.py"):
            with self.subTest(datei=datei):
                code, bereit, _, _ = wdv.plan_auswerten(
                    {"EREIGNIS": "push", "GEAENDERT": datei})
                self.assertEqual(code, 0)
                self.assertEqual(bereit, ["newsletter-worker", "klick-zaehler"])

    def test_newsletter_worker_traegt_build_stempel_und_nachweis_prueft_ihn(self):
        wrangler = (ROOT / "newsletter-worker" / "wrangler.toml").read_text(encoding="utf-8")
        m = wdv.BUILD_RE.search(wdv._toml_ohne_kommentare(wrangler))
        self.assertIsNotNone(m, "BUILD fehlt in newsletter-worker/wrangler.toml")
        soll = m.group(1)
        code_ok, text_ok = wdv.deploy_nachweis(
            "newsletter-worker", holen=lambda: soll, pausen=(), schlaf=lambda _: None)
        self.assertEqual(code_ok, 0)
        self.assertIn(soll, text_ok)
        code_alt, text_alt = wdv.deploy_nachweis(
            "newsletter-worker", holen=lambda: "alt", pausen=(0.0,), schlaf=lambda _: None)
        self.assertEqual(code_alt, 1)
        self.assertIn("fehlgeschlagen", text_alt)


class HealthNachweis(unittest.TestCase):
    """Ein passender Stempel auf einer kaputten /healthz-Seite ist kein Erfolg."""

    class Antwort(io.BytesIO):
        def __init__(self, body, status=200):
            super().__init__(body)
            self.status = status

    class Opener:
        def __init__(self, *antworten):
            self.antworten = list(antworten)
            self.rufe = []

        def open(self, request, timeout):
            self.rufe.append((request, timeout))
            wert = self.antworten.pop(0)
            if isinstance(wert, Exception):
                raise wert
            return wert

    def antwort(self, daten, status=200):
        return self.Antwort(json.dumps(daten).encode(), status)

    def nachweis(self, opener, *, pausen=()):
        with patch("urllib.request.build_opener", return_value=opener):
            return wdv.deploy_nachweis("newsletter-worker", holen=wdv._hole_oeffentlichen_bau,
                                      pausen=pausen, schlaf=lambda _: None)

    def setUp(self):
        text = (ROOT / "newsletter-worker" / "wrangler.toml").read_text(encoding="utf-8")
        self.soll = wdv.BUILD_RE.search(wdv._toml_ohne_kommentare(text)).group(1)

    def test_200_ok_true_und_stempel_beweisen_gesunden_deploy(self):
        opener = self.Opener(self.antwort({"ok": True, "bau": self.soll}))
        code, bericht = self.nachweis(opener)
        self.assertEqual(code, 0, bericht)
        request, _ = opener.rufe[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Cache-control"), "no-cache")

    def test_503_und_ungesundes_200_mit_passendem_stempel_sind_nicht_gruen(self):
        http_503 = urllib.error.HTTPError(wdv.NEWSLETTER_HEALTHZ, 503, "unavailable", {},
                                           io.BytesIO(json.dumps({"ok": False,
                                                                  "bau": self.soll}).encode()))
        for antwort in (http_503, self.antwort({"ok": False, "bau": self.soll}),
                        self.antwort({"bau": self.soll}),
                        self.antwort({"ok": "true", "bau": self.soll}),
                        self.antwort({"ok": True, "bau": self.soll}, status=503),
                        self.Antwort(b"{"), self.Antwort(b"x" * 65_537)):
            with self.subTest(antwort=repr(antwort)):
                code, bericht = self.nachweis(self.Opener(antwort))
                self.assertEqual(code, 1, bericht)
                self.assertIn("fehlgeschlagen", bericht)

    def test_voruebergehender_503_wird_erneut_geprueft(self):
        http_503 = urllib.error.HTTPError(wdv.NEWSLETTER_HEALTHZ, 503, "unavailable", {},
                                           io.BytesIO(b"{}"))
        opener = self.Opener(http_503, self.antwort({"ok": True, "bau": self.soll}))
        code, bericht = self.nachweis(opener, pausen=(0,))
        self.assertEqual(code, 0, bericht)
        self.assertEqual(len(opener.rufe), 2)

    def test_abweichender_stempel_oder_unlesbare_antwort_bleibt_offen(self):
        for antwort in (self.antwort({"ok": True, "bau": "alt"}),
                        self.antwort({"ok": True}), self.antwort([]),
                        self.Antwort(b"\xff"), urllib.error.URLError("GEHEIME_NETZDETAILS"),
                        TimeoutError("GEHEIME_NETZDETAILS")):
            with self.subTest(antwort=repr(antwort)):
                code, bericht = self.nachweis(self.Opener(antwort))
                self.assertEqual(code, 1, bericht)
                self.assertIn("fehlgeschlagen", bericht)
                self.assertNotIn("GEHEIME_NETZDETAILS", bericht)

    def test_weiterleitungen_werden_nicht_verfolgt_und_503_wird_benannt(self):
        with self.assertRaises(OSError):
            wdv._KeineWeiterleitung().redirect_request(None, None, 302, "Found", {},
                                                       "https://example.invalid/")
        for status in (302, 503):
            with self.subTest(status=status):
                fehler = urllib.error.HTTPError(wdv.NEWSLETTER_HEALTHZ, status,
                                                "GEHEIMER_ANTWORTTEXT", {}, io.BytesIO(b"{}"))
                code, bericht = self.nachweis(self.Opener(fehler))
                self.assertEqual(code, 1)
                self.assertIn(f"HTTP {status}", bericht)
                self.assertNotIn("GEHEIMER_ANTWORTTEXT", bericht)
                self.assertTrue(fehler.fp.closed)


if __name__ == "__main__":
    unittest.main()
