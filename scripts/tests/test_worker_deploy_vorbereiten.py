"""Vertrag des Worker-Deploys (Sicherheitsaudit 14.10.2026, M-14)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

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
                    "D1_DATABASE_ID_KLICKS": "01234567-89ab-cdef-0123-456789abcdef"}
        for name in ("newsletter-worker", "klick-zaehler"):
            ok, gruende, text = wdv.pruefe(name, umgebung)
            self.assertTrue(ok, f"{name}: {gruende}")
            self.assertIsNone(wdv.PLATZHALTER_RE.search(wdv._toml_ohne_kommentare(text)))

    def test_ki_assistent_nie_automatisch(self):
        self.assertNotIn("ki-assistent", wdv.plan({"EREIGNIS": "push", "GEAENDERT": "*"}))
        self.assertEqual(wdv.plan({"EREIGNIS": "workflow_dispatch", "AUSWAHL": "ki-assistent"}),
                         ["ki-assistent"])


class WorkflowVertrag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.wf = yaml.safe_load(cls.text)

    def test_deploy_braucht_environment_freigabe(self):
        job = self.wf["jobs"]["deploy"]
        self.assertEqual(job["environment"]["name"], "cloudflare-produktion")

    def test_minimalrechte_und_keine_persistierten_credentials(self):
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        for job in self.wf["jobs"].values():
            for schritt in job["steps"]:
                if str(schritt.get("uses", "")).startswith("actions/checkout@"):
                    self.assertIs(schritt["with"]["persist-credentials"], False)

    def test_eigener_deploy_token_nicht_der_workers_ai_token(self):
        self.assertIn("secrets.CF_WORKERS_DEPLOY_TOKEN", self.text)
        self.assertNotIn("secrets.CLOUDFLARE_API_TOKEN", self.text)

    def test_wrangler_gepinnt_ohne_install_skripte(self):
        self.assertIn("npm ci --ignore-scripts", self.text)
        self.assertNotIn("npx wrangler", self.text)
        paket = (ROOT / "tools" / "wrangler" / "package.json").read_text(encoding="utf-8")
        self.assertRegex(paket, r'"wrangler":\s*"\d+\.\d+\.\d+"')


if __name__ == "__main__":
    unittest.main()
