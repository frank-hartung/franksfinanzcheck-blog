#!/usr/bin/env python3
"""Vertragstest: Offizielles GitHub-Pages-Deployment in deploy.yml (Issue #537).

Befund 03.10.2026: Die Pages-Konfiguration des Repos steht auf
`build_type: workflow` und das Environment `github-pages` erwartet ein
Deployment über `actions/deploy-pages`. `deploy.yml` pushte bis dahin nur
auf den Branch `gh-pages` (`peaceiris/actions-gh-pages`) – das wurde von
GitHub Pages seit dem 30.09.2026 ~13:00 UTC stillschweigend ignoriert.
Jeder Deploy-Lauf meldete `success`, ohne dass je wieder ein Artikel
öffentlich ausgeliefert wurde (Issue #537, drei Tage eingefroren).

Dieser Test friert den Reparatur-Vertrag ein: Ein zusätzlicher Job muss
per `actions/deploy-pages` an das Environment `github-pages` ausliefern,
mit den dafür nötigen Rechten (`pages: write`, `id-token: write`) und nach
demselben `public/`-Build, den auch der `gh-pages`-Push verwendet. Fällt
dieser Vertrag aus `deploy.yml` heraus, friert die Live-Site erneut ein,
während alle anderen Signale (Source, Gates, `gh-pages`-Branch) grün
bleiben – genau das Muster, das Issue #537 drei Tage lang verdeckt hat.
"""
from __future__ import annotations

import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPLOY_YML = os.path.join(ROOT, ".github", "workflows", "deploy.yml")


def _load_workflow() -> dict:
    with open(DEPLOY_YML, encoding="utf-8") as f:
        # YAML 1.1 parst `on:` als Boolean-Key True -> explizit roundtrip-fest
        # laden reicht hier; wir brauchen nur die jobs/permissions-Struktur.
        return yaml.safe_load(f)


class PagesDeploymentGuardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = _load_workflow()
        self.jobs = self.workflow["jobs"]

    def test_top_level_permissions_allow_pages_deployment(self) -> None:
        perms = self.workflow.get("permissions") or {}
        self.assertEqual(
            perms.get("pages"), "write",
            "deploy.yml braucht 'pages: write' – sonst bleibt actions/deploy-pages wirkungslos.",
        )
        self.assertEqual(
            perms.get("id-token"), "write",
            "deploy.yml braucht 'id-token: write' – Voraussetzung für actions/deploy-pages.",
        )

    def test_build_job_uploads_pages_artifact(self) -> None:
        build_job = self.jobs["deploy"]
        uses = [step.get("uses", "") for step in build_job["steps"]]
        self.assertTrue(
            any(u.startswith("actions/upload-pages-artifact@") for u in uses),
            "Der Build-Job muss den public/-Stand als Pages-Artefakt hochladen.",
        )
        upload_step = next(
            step for step in build_job["steps"]
            if step.get("uses", "").startswith("actions/upload-pages-artifact@")
        )
        self.assertEqual(upload_step.get("with", {}).get("path"), "./public")

        # Der Upload darf nicht VOR dem fertigen Build (inkl. etwaiger
        # Heilungs-Rebuilds und Audio) passieren, sonst landet ein
        # unvollständiger Stand im Pages-Deployment.
        gh_pages_push_idx = next(
            i for i, u in enumerate(uses) if u.startswith("peaceiris/actions-gh-pages@")
        )
        upload_idx = next(
            i for i, u in enumerate(uses) if u.startswith("actions/upload-pages-artifact@")
        )
        self.assertGreaterEqual(
            upload_idx, gh_pages_push_idx,
            "Pages-Artefakt-Upload sollte frühestens so spät wie der gh-pages-Push "
            "passieren, damit derselbe fertige public/-Stand ausgeliefert wird.",
        )

    def test_dedicated_pages_deployment_job_exists(self) -> None:
        self.assertIn(
            "pages-deployment", self.jobs,
            "Ein eigener Job muss an das Environment 'github-pages' deployen (actions/deploy-pages).",
        )
        job = self.jobs["pages-deployment"]
        needs = job.get("needs")
        needs_list = [needs] if isinstance(needs, str) else list(needs or [])
        self.assertIn("deploy", needs_list)
        # `deploy-gate` muss ebenfalls in needs stehen, sonst ist
        # `needs.deploy-gate.outputs.deploy` im `if:` nicht auswertbar und
        # der Job würde nie laufen (stiller Ausfall wie bei Issue #537).
        self.assertIn("deploy-gate", needs_list)
        self.assertEqual(job.get("environment", {}).get("name"), "github-pages")

        perms = job.get("permissions") or {}
        self.assertEqual(perms.get("pages"), "write")
        self.assertEqual(perms.get("id-token"), "write")

        uses = [step.get("uses", "") for step in job["steps"]]
        self.assertTrue(
            any(u.startswith("actions/deploy-pages@") for u in uses),
            "pages-deployment muss actions/deploy-pages ausführen.",
        )

    def test_pages_deployment_job_only_runs_when_deploy_gate_allows(self) -> None:
        job = self.jobs["pages-deployment"]
        condition = job.get("if", "")
        self.assertIn("deploy-gate.outputs.deploy", condition)

    def test_selftest(self) -> None:
        """Smoke-Test: Die Testdatei selbst muss ohne Fixtures importierbar sein."""
        self.assertTrue(os.path.exists(DEPLOY_YML))


if __name__ == "__main__":
    unittest.main()
