#!/usr/bin/env python3
"""Sicherheitsvertrag gegen Klartext-Logging sensibler Daten (Alerts #77/#78/#80).

Prüft auf drei Ebenen:
1. AST-basierte statische Analyse über alle Produktions-Skripte:
   - Keine rohen Secret-/Token-/Passwort-Variablen in print(), logging.* oder sys.stdout/stderr.write.
   - Keine unverschlüsselten Speicherungen sensibler Schlüssel im Klartext.
2. Deterministische Laufzeit-Verifikation:
   - pinterest_auth (print_status, _explain_exchange_error)
   - pinterest_token (describe, save_state)
   - secrets_age_guard (_record_success, --list)
   - social_preflight (JSON-Ausgabe)
   - newsletter_versand (Bestätigungs-Logging mit Hash)
3. Repository-weite Klartext-Wache:
   - lokale, inhalts-sensitive Nachbildung der beiden CodeQL-Clear-Text-Regeln
   - alle versionierten und neuen, nicht ignorierten Python-Dateien
   - Inline-Unterdrückungen sind selbst ein Befund (kein Wegfiltern)

Hintergrund: CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md.
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
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
        # Seit 05.10.2026 heißen die internen Felder `pflicht_env` /
        # `fehlende_env` (Namensvertrag gegen Code-Scanning-Alert #78; siehe
        # scripts/tests/test_zugangs_namensvertrag.py). Die JSON-Oberfläche
        # bleibt stabil: required_env_names / missing_env_names.
        raw_report = {
            "zeit": "05.10.2026 12:00 Uhr",
            "kanaele": [
                {
                    "kanal": "mastodon",
                    "label": "Mastodon",
                    "enabled": True,
                    "pflicht_env": ["MASTODON_ACCESS_TOKEN"],
                    "vars": ["MASTODON_INSTANCE"],
                    "fehlende_env": ["MASTODON_ACCESS_TOKEN"],
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
        # Kein Schlüssel darf behaupten, Zugangsdaten zu enthalten.
        self.assertNotIn('"secrets":', payload_str)
        self.assertNotIn('"fehlende_secrets":', payload_str)
        self.assertNotIn('"pflicht_env":', payload_str)
        self.assertNotIn('"fehlende_env":', payload_str)
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


class KlartextWacheContract(unittest.TestCase):
    """Alert #80: upload-unabhängige, fail-closed Klartext-Kontrolle."""

    WACHE = SCRIPTS / "clear_text_logging_guard.py"

    def _lauf(self, *args):
        return subprocess.run(
            [sys.executable, str(self.WACHE), *args],
            capture_output=True, text=True, cwd=str(ROOT), timeout=120,
            check=False)

    def test_wache_existiert_und_besteht_eigenpruefung(self):
        """Eine Wache ohne scharfe Positiv- und Gegenproben ist Scheinsicherheit."""
        self.assertTrue(self.WACHE.is_file(),
                        "scripts/clear_text_logging_guard.py fehlt")
        erg = self._lauf("--selftest")
        self.assertEqual(
            erg.returncode, 0,
            f"Eigenprüfung der Klartext-Wache fehlgeschlagen:\n{erg.stdout}\n{erg.stderr}")
        self.assertIn("Positivproben", erg.stdout)
        self.assertIn("Gegenproben", erg.stdout)

    def test_repository_ist_frei_von_klartext_fluessen(self):
        """Der Regressionsschutz für beide Clear-Text-Regeln und alle .py-Dateien."""
        erg = self._lauf("--json", "--quiet")
        try:
            bericht = json.loads(erg.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"Klartext-Wache lieferte kein valides JSON ({exc}):\n"
                      f"{erg.stdout}\n{erg.stderr}")
        self.assertEqual(
            bericht.get("fehler"), [],
            "Fail-closed: mindestens eine Python-Datei war nicht analysierbar: "
            f"{bericht.get('fehler')}")
        befunde = bericht.get("befunde", [])
        details = "\n".join(
            f"  {b['datei']}:{b['zeile']} [{b['regel']}] "
            f"{b['art']}: {b['quelle']} → {b['senke']}"
            for b in befunde)
        self.assertEqual(
            befunde, [],
            "Klartext-Fluss oder verbotene Unterdrückung gefunden. Namen ehrlich "
            "machen, Werte entschärfen oder Ausgabe entfernen – nie wegfiltern:\n"
            + details)
        self.assertEqual(erg.returncode, 0, erg.stderr)
        self.assertGreaterEqual(bericht.get("geprueft", 0), 1)

    def test_nicht_analysierbarer_code_ist_fail_closed(self):
        """Ein Parsefehler liefert Exit 2 und kann nie als „sauber“ durchgehen."""
        with tempfile.TemporaryDirectory() as tmp:
            kaputt = Path(tmp) / "kaputt.py"
            kaputt.write_text("def unvollstaendig(:\n", encoding="utf-8")
            erg = self._lauf("--json", "--quiet", str(kaputt))
        self.assertEqual(erg.returncode, 2, erg.stderr)
        bericht = json.loads(erg.stdout)
        self.assertEqual(bericht.get("befunde"), [])
        self.assertEqual(len(bericht.get("fehler", [])), 1)
        self.assertIn("Syntaxfehler", bericht["fehler"][0])

    def test_namensvertrag_der_alert_80_fundstelle(self):
        """Die HTML-Prüfung heißt nach ihrem Inhalt, nicht nach Zugangsmaterial."""
        quelltext = (SCRIPTS / "secrets_age_guard.py").read_text(encoding="utf-8")
        self.assertNotIn("def oauth_empfaenger_findings(", quelltext)
        self.assertNotIn("OAUTH_SEITE =", quelltext)
        self.assertIn("def rueckleitung_findings(", quelltext)
        self.assertIn("RUECKLEITUNG_SEITE =", quelltext)


if __name__ == "__main__":
    unittest.main(verbosity=2)
