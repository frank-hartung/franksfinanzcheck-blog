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
        with open(DEPLOY_YML, encoding="utf-8") as f:
            self.workflow_text = f.read()

    def test_top_level_permissions_allow_pages_deployment(self) -> None:
        # Sicherheitsaudit 14.10.2026 (M-09): Rechte je Job. Job-Rechte
        # ersetzen die Workflow-Rechte vollständig – `pages: write` und
        # `id-token: write` gehören deshalb an den Job, der actions/deploy-pages
        # ausführt, nicht an alle Jobs (inkl. Dritt-Action peaceiris).
        perms = self.workflow.get("permissions") or {}
        self.assertNotEqual(perms.get("id-token"), "write",
                            "id-token: write gehört nur an den Job pages-deployment.")
        job_perms = self.jobs["pages-deployment"].get("permissions") or {}
        self.assertEqual(
            job_perms.get("pages"), "write",
            "pages-deployment braucht 'pages: write' – sonst bleibt actions/deploy-pages wirkungslos.",
        )
        self.assertEqual(
            job_perms.get("id-token"), "write",
            "pages-deployment braucht 'id-token: write' – Voraussetzung für actions/deploy-pages.",
        )
        deploy_perms = self.jobs["deploy"].get("permissions") or {}
        self.assertEqual(deploy_perms.get("contents"), "write",
                         "Der Build-Job committet Heilungen und pflegt gh-pages.")
        self.assertEqual(deploy_perms.get("pages"), "write",
                         "configure-pages im Build-Job liest/konfiguriert Pages.")

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

    def test_deploy_gate_uses_successful_official_deployment_as_live_receipt(self) -> None:
        """WF-7C1F/#538: Ein frischer gh-pages-Cache ist kein Live-Beleg.

        Der erste #537-Fix wurde nach dem Merge vom Entlastungs-Gate
        übersprungen, weil dieses nur die Commit-Nachricht auf gh-pages las.
        Das Gate muss deshalb zusätzlich die echte Deployment-Historie und
        ihren letzten Status prüfen.
        """
        self.assertIn(
            "deployments?environment=github-pages",
            self.workflow_text,
            "Das Gate muss das echte github-pages-Environment abfragen.",
        )
        self.assertIn(
            "/statuses?per_page=1",
            self.workflow_text,
            "Ein Deployment-Objekt ohne success-Status ist kein Live-Beleg.",
        )
        self.assertIn('PAGES_DEPLOY_STATUS" != "success"', self.workflow_text)
        self.assertIn('PAGES_DEPLOY_SHA" != "$LIVE_DEPLOY_SHA"', self.workflow_text)

    def test_official_receipt_is_checked_before_any_skip(self) -> None:
        """Kein Shortcut darf den Reparatur-Deploy erneut überspringen."""
        invariant = self.workflow_text.index(
            'PAGES_DEPLOY_STATUS" != "success"'
        )
        skip = self.workflow_text.index(
            'Cache und offizielles Pages-Deployment sind auf Stand'
        )
        path_filter = self.workflow_text.index("STATE_ONLY='")
        self.assertLess(invariant, skip)
        self.assertLess(invariant, path_filter)

    def test_selftest(self) -> None:
        """Smoke-Test: Die Testdatei selbst muss ohne Fixtures importierbar sein."""
        self.assertTrue(os.path.exists(DEPLOY_YML))


class AuslieferungsProbenTestCase(unittest.TestCase):
    """Live-Proben 25.10.2026: Zwei Auslieferungs-Verträge, die tagelang
    unbemerkt gebrochen waren, werden hier eingefroren.

    Befund 1 (security.txt): /.well-known/security.txt (RFC 9116, seit
    14.10.2026 im Bestand, #750 I-03) lieferte live HTTP 404. Ursache:
    actions/upload-pages-artifact archiviert seit v4 mit --exclude=.[^/]*
    – versteckte Dateien kamen nie ins Pages-Deployment, während der
    gh-pages-Zweig (peaceiris, ohne Ausschluss) sie trug. Reparatur:
    `include-hidden-files: true` in BEIDEN Deploy-Pfaden.

    Befund 2 (sw.js ohne SHA): /sw.js lief live mit VERSION="dev" und alle
    Asset-URLs ohne ?v=<sha>, weil deploy.yml HUGO_JSDELIVR_SHA nie
    injizierte – obwohl asset_url.html, cover.html, ff_fontfaces.html und
    index.sw.js genau darauf ihren Cache-Generationen-Vertrag bauen
    (e2e/layout-ai/pinterest-watchdog setzten die Variable längst).

    Ohne diese Tests kippt ein wohlmeinendes Aufräumen (Action-Update,
    Job-Umbau) die Reparatur still zurück – dieselbe Klasse wie #537.
    """

    NOTFALL_YML = os.path.join(ROOT, ".github", "workflows", "notfall-deploy.yml")

    def _laden(self, pfad: str) -> tuple[dict, str]:
        with open(pfad, encoding="utf-8") as f:
            text = f.read()
        return yaml.safe_load(text), text

    def _upload_schritt(self, job: dict) -> dict:
        schritte = [s for s in job.get("steps", [])
                    if str(s.get("uses", "")).startswith("actions/upload-pages-artifact@")]
        self.assertEqual(len(schritte), 1,
                         "Genau ein upload-pages-artifact-Schritt je Build-Job erwartet.")
        return schritte[0]

    def test_pages_artefakt_publiziert_versteckte_dateien(self) -> None:
        for pfad, jobname in ((DEPLOY_YML, "deploy"), (self.NOTFALL_YML, "bauen")):
            workflow, _ = self._laden(pfad)
            upload = self._upload_schritt(workflow["jobs"][jobname])
            with_wert = (upload.get("with") or {}).get("include-hidden-files")
            self.assertIn(str(with_wert).lower(), ("true", "yes"),
                          f"{os.path.basename(pfad)}: include-hidden-files fehlt – "
                          "/.well-known/security.txt würde live wieder 404 liefern.")

    def test_deploy_pfade_injizieren_asset_sha(self) -> None:
        for pfad, jobname in ((DEPLOY_YML, "deploy"), (self.NOTFALL_YML, "bauen")):
            workflow, _ = self._laden(pfad)
            env = workflow["jobs"][jobname].get("env") or {}
            self.assertEqual(env.get("HUGO_JSDELIVR_SHA"), "${{ github.sha }}",
                             f"{os.path.basename(pfad)}: Job '{jobname}' muss "
                             "HUGO_JSDELIVR_SHA injizieren, sonst rotiert die "
                             "sw.js-Cache-Generation nicht und Asset-URLs "
                             "tragen kein ?v=<sha>.")

    def test_security_txt_quelle_ist_lieferfaehig(self) -> None:
        """Die Quelle muss im Build landen können UND RFC-9116-Kerne tragen."""
        quelle = os.path.join(ROOT, "static", ".well-known", "security.txt")
        self.assertTrue(os.path.exists(quelle),
                        "static/.well-known/security.txt fehlt – die Live-Probe "
                        "(Contact: unter /.well-known/security.txt) wäre nie grün.")
        with open(quelle, encoding="utf-8") as f:
            inhalt = f.read()
        self.assertIn("Contact:", inhalt, "RFC 9116 verlangt mindestens ein Contact-Feld.")
        self.assertIn("Expires:", inhalt, "Ohne Expires gilt die Datei als verwaist.")

    def test_versteckter_build_bestand_bleibt_klein(self) -> None:
        """include-hidden-files publiziert ALLE Dotfiles des Builds. Damit das
        eine bewusste Entscheidung bleibt, darf static/ keine neuen
        versteckten Pfade ansammeln, die niemand live erwartet."""
        erlaubt = {".well-known", ".nojekyll"}
        static_versteckt = set()
        static_root = os.path.join(ROOT, "static")
        for eintrag in os.listdir(static_root):
            if eintrag.startswith("."):
                static_versteckt.add(eintrag)
        self.assertTrue(static_versteckt <= erlaubt,
                        f"Neue versteckte Pfade in static/ ({sorted(static_versteckt - erlaubt)}) "
                        "würden durch include-hidden-files ungeprüft live gehen – "
                        "bewusst freigeben oder entfernen.")


if __name__ == "__main__":
    unittest.main()
