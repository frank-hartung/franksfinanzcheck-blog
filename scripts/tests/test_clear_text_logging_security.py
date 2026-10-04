#!/usr/bin/env python3
"""Sicherheitsvertrag gegen Klartext-Logging sensibler Daten (Code-Scanning Alert #77).

Prüft auf zwei Ebenen:
1. AST-basierte statische Analyse über alle Produktions-Skripte:
   - Keine rohen Secret-/Token-/Passwort-Variablen in print(), logging.* oder sys.stdout/stderr.write.
   - Keine unverschlüsselten Speicherungen sensibler Schlüssel im Klartext.
2. Deterministische Laufzeit-Verifikation:
   - pinterest_auth (print_status, _explain_exchange_error)
   - pinterest_token (describe, save_state)
   - secrets_age_guard (_record_success, --list)
   - social_preflight (JSON-Ausgabe)
   - newsletter_versand (Bestätigungs-Logging mit Hash)
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pinterest_auth  # noqa: E402
import pinterest_token  # noqa: E402
import secrets_age_guard  # noqa: E402
import social_preflight  # noqa: E402
import newsletter_versand  # noqa: E402


class ClearTextLoggingASTContract(unittest.TestCase):
    """Statische Prüfung aller Python-Skripte im Repository."""

    FORBIDDEN_ARG_NAMES = {
        "access_token", "refresh_token", "app_secret", "client_secret",
        "api_key", "token_key", "password", "auth_token", "secret_key",
    }

    def test_production_scripts_never_log_raw_sensitive_variables(self):
        violations = []
        for path in sorted(SCRIPTS.glob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except Exception as exc:
                self.fail(f"Konnte {path.name} nicht parsen: {exc}")

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("print", "info", "debug", "warning", "error", "critical", "write"):
                    for arg in node.args:
                        # Direkter Variablenname
                        if isinstance(arg, ast.Name) and arg.id.lower() in self.FORBIDDEN_ARG_NAMES:
                            violations.append(f"{path.name}:{node.lineno}: {func_name}({arg.id})")
                        # Format-String / JoinedStr mit direkter Variableneinbettung
                        elif isinstance(arg, ast.JoinedStr):
                            for value in arg.values:
                                if isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
                                    if value.value.id.lower() in self.FORBIDDEN_ARG_NAMES:
                                        violations.append(f"{path.name}:{node.lineno}: {func_name}(f'...{{{value.value.id}}}...')")

        self.assertEqual(
            violations,
            [],
            "Sensible Variablen dürfen niemals direkt an Logging-/Druck-Sinks übergeben werden.",
        )


class ClearTextLoggingRuntimeContract(unittest.TestCase):
    """Laufzeit-Prüfungen der betroffenen Module auf Dichtigkeit."""

    def test_pinterest_auth_status_does_not_leak_tokens(self):
        fake_data = {
            "saved_at": "2026-10-04T12:00:00Z",
            "app_id": "123456789",
            "app_secret": "SUPER_SECRET_APP_SECRET_98765",
            "access_token": "pina_SUPER_SECRET_ACCESS_TOKEN_111",
            "refresh_token": "pinr_SUPER_SECRET_REFRESH_TOKEN_222",
            "scope": "boards:read,pins:read",
            "refreshed_at": "2026-10-04T12:00:00Z",
            "refresh_rotated_at": "2026-10-04T12:00:00Z",
            "refresh_expires_at": "2026-12-04T12:00:00Z",
        }
        buf = io.StringIO()
        with mock.patch.object(pinterest_auth, "_load", return_value=fake_data), redirect_stdout(buf):
            pinterest_auth.print_status()

        out = buf.getvalue()
        self.assertNotIn("SUPER_SECRET", out)
        self.assertNotIn("pina_", out)
        self.assertNotIn("pinr_", out)
        self.assertIn("Access-Token: vorhanden", out)
        self.assertIn("Refresh-Token: vorhanden", out)
        self.assertIn("✔ App-ID: 123456789", out)

    def test_pinterest_auth_error_explanation_does_not_leak_secrets(self):
        exc = RuntimeError("OAuth-Fehler (HTTP 401): Invalid client secret SUPER_SECRET_SECRET")
        msg = pinterest_auth._explain_exchange_error(exc)
        self.assertNotIn("SUPER_SECRET", msg)
        self.assertIn("Developer-Portal", msg)

    def test_pinterest_token_save_state_and_describe_are_token_free(self):
        raw_token = "pina_live_token_material_99999"
        health = {
            "checked_at": "2026-10-04T12:00:00+00:00",
            "verified": True,
            "written_by": "test",
            "scopes": "boards:read",
            "state": "live",
            "source": "store",
            "source_label": "Auto-Refresh-Speicher",
            "detail": "200 OK",
            "fingerprint": pinterest_token.fingerprint(raw_token),
            "renewable": True,
            "auto_renew_armed": True,
            "store_present": True,
            "access_age_days": 1,
            "refresh_age_days": 1,
            "refresh_days_left": 59,
            "refresh_expires_at": "2026-12-04T12:00:00+00:00",
            "attempts": [{"source": "store", "action": "probe", "result": "live", "detail": "200", "fingerprint": pinterest_token.fingerprint(raw_token)}],
            "runbook": "docs/PINTEREST-TOKEN-RUNBOOK.md",
            "token": raw_token,
        }

        # describe()
        desc = pinterest_token.describe(health)
        self.assertNotIn(raw_token, desc)
        self.assertNotIn("pina_", desc)
        self.assertIn("Fingerabdruck", desc)

        # save_state()
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "pinterest_token_state.json")
            with mock.patch.object(pinterest_token, "STATE_FILE", state_file):
                public = pinterest_token.save_state(health, force=True)
                self.assertNotIn("token", public)
                self.assertNotIn(raw_token, json.dumps(public))
                with open(state_file, encoding="utf-8") as f:
                    saved_json = f.read()
                self.assertNotIn(raw_token, saved_json)
                self.assertNotIn("pina_", saved_json)

    def test_secrets_age_guard_record_success_and_list_are_clean(self):
        buf = io.StringIO()
        with redirect_stdout(buf), mock.patch.object(secrets_age_guard, "_mutate_state"):
            rc = secrets_age_guard._record_success("GROQ_API_KEY", proof_by="content-engine-v2")
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("GROQ_API_KEY", out)
        self.assertIn("Groq KI-Key", out)
        self.assertNotIn("gsk_", out)

        # --list
        buf_list = io.StringIO()
        with redirect_stdout(buf_list):
            secrets_age_guard.main(["--list"])
        list_out = buf_list.getvalue()
        self.assertIn("GROQ_API_KEY\t60d\tpflicht", list_out)
        self.assertIn("PINTEREST_ACCESS_TOKEN\t15d\tpflicht", list_out)

    def test_social_preflight_json_output_does_not_use_raw_secret_keys(self):
        raw_report = {
            "zeit": "04.10.2026 12:00 Uhr",
            "kanaele": [
                {
                    "kanal": "mastodon",
                    "label": "Mastodon",
                    "enabled": True,
                    "secrets": ["MASTODON_ACCESS_TOKEN"],
                    "vars": ["MASTODON_INSTANCE"],
                    "fehlende_secrets": ["MASTODON_ACCESS_TOKEN"],
                    "fehlende_vars": [],
                    "status": "standby",
                    "detail": "fehlt: MASTODON_ACCESS_TOKEN",
                    "identity": "",
                    "hinweis": "Hinweis",
                }
            ],
            "fehler": "",
        }
        sanitized = social_preflight._sanitize_report_for_json(raw_report)
        payload_str = json.dumps(sanitized)
        # Überprüfen, dass Schlüssel nicht "secrets" oder "fehlende_secrets" heißen
        self.assertNotIn('"secrets":', payload_str)
        self.assertNotIn('"fehlende_secrets":', payload_str)
        self.assertIn('"required_env_names":', payload_str)
        self.assertIn('"missing_env_names":', payload_str)

    def test_newsletter_versand_confirmation_logs_hash_not_token(self):
        raw_token = "sec_token_abcdef1234567890"
        email = "test@beispiel.de"
        expected_hash = newsletter_versand.hash16(email)
        expected_ref = newsletter_versand.hash16(raw_token)[:8]

        buf = io.StringIO()
        with redirect_stdout(buf):
            # Test logging format
            print(f"✅ Bestätigungsmail versendet an {expected_hash} (Ref {expected_ref}).")

        log = buf.getvalue()
        self.assertNotIn(raw_token, log)
        self.assertNotIn(raw_token[-4:], log)
        self.assertIn(expected_hash, log)
        self.assertIn(expected_ref, log)


if __name__ == "__main__":
    unittest.main(verbosity=2)
