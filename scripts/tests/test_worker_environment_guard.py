#!/usr/bin/env python3
"""Vertragstests des Produktions-Environment-Gates (WF-E813/#815, 29.10.2026)."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_environment_guard as guard  # noqa: E402

REPO = "frank-hartung/franksfinanzcheck-blog"
TOKEN = "GIFT_GITHUB_TOKEN_NEVER_LOG"
REVIEWER = {"type": "User", "reviewer": {"id": 42, "login": "frank-hartung"}}
ENV = {
    "protection_rules": [{"type": "required_reviewers", "reviewers": [REVIEWER]}],
    "can_admins_bypass": False,
    "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
}
POLICIES = [{"name": "main", "type": "branch"}]


def response(status: int, body: object, headers: dict | None = None):
    return status, headers or {}, json.dumps(body).encode("utf-8")


class Policyvertrag(unittest.TestCase):
    def test_sichere_policy_wird_akzeptiert(self):
        self.assertEqual(guard.abweichungen(ENV, POLICIES), [])

    def test_fehlende_reviewer_branchbeschraenkung_und_admin_bypass_sind_rot(self):
        offen = {
            "protection_rules": [],
            "can_admins_bypass": True,
            "deployment_branch_policy": None,
        }
        gruende = " ".join(guard.abweichungen(offen, None))
        self.assertIn("Required Reviewer fehlt", gruende)
        self.assertIn("Administrator-Bypass", gruende)
        self.assertIn("Branch-Policy fehlt", gruende)

    def test_leere_oder_ungueltige_reviewer_liste_faellt_auf(self):
        for reviewer in ([], [{"type": "Bot", "reviewer": {"id": 7}}],
                         [{"type": "User", "reviewer": {"login": "owner"}}], "owner"):
            with self.subTest(reviewer=reviewer):
                daten = {**ENV, "protection_rules": [
                    {"type": "required_reviewers", "reviewers": reviewer}
                ]}
                gruende = " ".join(guard.abweichungen(daten, POLICIES))
                self.assertIn("Reviewer", gruende)

    def test_nur_main_als_branch_und_keine_tags_oder_zusatzmuster(self):
        for policies in (
            [{"name": "main", "type": "tag"}],
            [{"name": "main", "type": "branch"}, {"name": "release/*", "type": "branch"}],
            [],
            None,
        ):
            with self.subTest(policies=policies):
                self.assertTrue(guard.abweichungen(ENV, policies))
        self.assertEqual(guard.abweichungen(ENV, POLICIES), [])

    def test_protected_branches_allein_genuegt_nicht(self):
        daten = {**ENV, "deployment_branch_policy": {
            "protected_branches": True, "custom_branch_policies": False
        }}
        gruende = " ".join(guard.abweichungen(daten, None))
        self.assertIn("Selected branches and tags", gruende)

    def test_ungueltige_environment_antwort_ist_nicht_gruen(self):
        for daten in (None, [], {"protection_rules": "broken"}):
            with self.subTest(daten=daten):
                self.assertTrue(guard.abweichungen(daten, None))

    def test_repository_und_token_sind_pflicht_ohne_netzaufruf(self):
        for env, nadel in (
            ({}, "owner/repo"),
            ({"GITHUB_REPOSITORY": REPO}, "GITHUB_TOKEN"),
        ):
            with self.subTest(nadel=nadel):
                with self.assertRaisesRegex(guard.ApiFehler, nadel):
                    guard.pruefen(env, holen=lambda *_: self.fail("unerwarteter Netzaufruf"))

    def test_pruefung_liest_environment_und_alle_branch_policies_read_only(self):
        basis = f"{guard.API}/repos/{REPO}/environments/{guard.ENVIRONMENT}"
        policies_url = basis + "/deployment-branch-policies?per_page=100"
        calls = []

        def holen(url, token):
            calls.append((url, token))
            if url == basis:
                return response(200, ENV)
            if url == policies_url:
                return response(200, {"total_count": 1, "branch_policies": POLICIES})
            self.fail(f"unerwarteter API-Aufruf: {url}")

        self.assertEqual(guard.pruefen({
            "GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN,
        }, holen=holen), [])
        self.assertEqual(calls, [(basis, TOKEN), (policies_url, TOKEN)])
        self.assertNotIn("PUT", guard._api_roh.__code__.co_names)

    def test_paginierung_wird_vollstaendig_geprueft(self):
        basis = f"{guard.API}/repos/{REPO}/environments/{guard.ENVIRONMENT}"
        policies = basis + "/deployment-branch-policies"
        erste = policies + "?per_page=100"
        zweite = policies + "?per_page=100&page=2"
        calls = []

        def holen(url, _token):
            calls.append(url)
            if url == basis:
                return response(200, ENV)
            if url == erste:
                return response(200, {"total_count": 2, "branch_policies": POLICIES}, {
                    "Link": f'<{zweite}>; rel="next", <{zweite}>; rel="last"'
                })
            if url == zweite:
                return response(200, {"total_count": 2, "branch_policies": [
                    {"name": "release/*", "type": "branch"}
                ]})
            self.fail(f"unerwarteter API-Aufruf: {url}")

        gruende = guard.pruefen({"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN}, holen=holen)
        self.assertEqual(len(calls), 3)
        self.assertTrue(any("genau den Branch `main`" in g for g in gruende))

    def test_paginierung_muss_total_count_vollstaendig_erfuellen(self):
        basis = f"{guard.API}/repos/{REPO}/environments/{guard.ENVIRONMENT}"
        policies = basis + "/deployment-branch-policies?per_page=100"

        for antwort in (
            {"total_count": 2, "branch_policies": POLICIES},
            {"branch_policies": POLICIES},
        ):
            with self.subTest(antwort=antwort):
                def holen(url, _token):
                    if url == basis:
                        return response(200, ENV)
                    if url == policies:
                        return response(200, antwort)
                    self.fail(f"unerwarteter API-Aufruf: {url}")

                with self.assertRaisesRegex(guard.ApiFehler, "total_count|unvollständig"):
                    guard.pruefen({"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN}, holen=holen)

    def test_paginierung_darf_nicht_auf_fremden_host_ausweichen(self):
        basis = f"{guard.API}/repos/{REPO}/environments/{guard.ENVIRONMENT}"
        policies = basis + "/deployment-branch-policies"
        with self.assertRaisesRegex(guard.ApiFehler, "Unsicheres GitHub-API-Ziel"):
            guard._naechste_seite(
                f'<https://attacker.invalid{policies}?per_page=100&page=2>; rel="next"',
                aktuelle_url=policies + "?per_page=100", repo=REPO)

    def test_api_und_redirect_grenze_ist_exakt(self):
        with self.assertRaisesRegex(guard.ApiFehler, "Nicht erlaubter GitHub-API-Pfad"):
            guard._api_url_pruefen(
                f"{guard.API}/repos/{REPO}/actions/runs", repo=REPO, policies=False)
        handler = guard._KeineWeiterleitung()
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(
                None, None, 302, "Found", {}, "https://attacker.invalid/steal")

    def test_environment_404_ist_ein_einrichtungsbefund(self):
        basis = f"{guard.API}/repos/{REPO}/environments/{guard.ENVIRONMENT}"
        with self.assertRaisesRegex(guard.PruefFehler, "Environment.*fehlt"):
            guard.pruefen({"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": TOKEN},
                          holen=lambda _url, _token: (404, {}, b""))

    def test_api_fehler_und_geheime_rohtexte_leaken_nicht(self):
        basis = f"{guard.API}/repos/{REPO}/environments/{guard.ENVIRONMENT}"

        class Opener:
            method = None

            def open(self, request, timeout):
                self.method = request.get_method()
                self.assert_no_body = request.data is None
                self.assert_token_header = request.get_header("Authorization") == f"Bearer {TOKEN}"
                raise urllib.error.HTTPError(
                    request.full_url, 403, "forbidden", {}, io.BytesIO(TOKEN.encode()))

        opener = Opener()
        with patch("urllib.request.build_opener", return_value=opener):
            status, _, _ = guard._api_roh(basis, TOKEN, repo=REPO, policies=False)
        self.assertEqual(status, 403)
        self.assertEqual(opener.method, "GET")
        self.assertTrue(opener.assert_no_body)
        self.assertTrue(opener.assert_token_header)

        with self.assertRaises(guard.ApiFehler) as gefangen:
            guard._json_holen(basis, TOKEN, repo=REPO, policies=False,
                              holen=lambda *_: (403, {}, TOKEN.encode()))
        self.assertIn("403", str(gefangen.exception))
        self.assertNotIn(TOKEN, str(gefangen.exception))

    def test_workflow_guard_ist_vor_dem_secrets_environment_und_main_gebunden(self):
        text = (ROOT / ".github" / "workflows" / "worker-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("production-policy:", text)
        policy = text.split("  production-policy:\n", 1)[1].split("\n  deploy:\n", 1)[0]
        deploy = text.split("  deploy:\n", 1)[1]
        plan = text.split("  plan:\n", 1)[1].split("\n  production-policy:\n", 1)[0]
        self.assertIn("actions: read", policy)
        self.assertNotIn("environment:", policy)
        self.assertNotIn("secrets.CF_WORKERS_DEPLOY_TOKEN", policy)
        self.assertIn("worker_environment_guard.py --check", policy)
        self.assertIn("Environment-Guard selbsttesten (offline)", policy)
        access_step = policy.split(
            "- name: Produktions-Environment absichern (vor Zugriff auf Secrets)", 1)[1]
        self.assertNotIn("--selftest", access_step)
        self.assertIn("needs: [plan, production-policy]", deploy)
        self.assertIn("github.ref == 'refs/heads/main'", deploy)
        self.assertIn("REF: ${{ github.ref }}", plan)
        self.assertIn("scripts/worker_environment_guard.py", text.split("  push:\n", 1)[1])

    def test_trigger_und_sicherheitssuite_beobachten_guard_und_tests(self):
        workflow = (ROOT / ".github" / "workflows" / "sicherheits-wache.yml").read_text(encoding="utf-8")
        package = (ROOT / "package.json").read_text(encoding="utf-8")
        for text in (workflow, package):
            self.assertIn("worker_environment_guard.py", text)
            self.assertIn("test_worker_environment_guard", text)
        transport_source = (ROOT / "scripts" / "ki_transportweg.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/worker_environment_guard.py")', transport_source)
        quelltext = (ROOT / "scripts" / "worker_environment_guard.py").read_text(encoding="utf-8")
        self.assertIn('API = "https://api.github.com"', quelltext)
        self.assertNotIn("api.cloudflare.com", quelltext)
        for verboten in ("/ai/run", "generativelanguage", "api.groq.com", "workers.ai"):
            self.assertNotIn(verboten, quelltext)

    def test_selftest(self):
        self.assertEqual(guard._selbsttest(), 0)


if __name__ == "__main__":
    unittest.main()
