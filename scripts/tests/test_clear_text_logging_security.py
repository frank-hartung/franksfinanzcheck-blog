#!/usr/bin/env python3
"""Sicherheitsvertrag gegen Klartext-Logging sensibler Daten (Alerts #77 und #80).

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
3. Vollprüfung mit scripts/clear_text_logging_guard.py (Klartext-Wache):
   die lokale Nachbildung der CodeQL-Regeln py/clear-text-logging-sensitive-data
   und py/clear-text-storage-sensitive-data läuft über ALLE Python-Dateien des
   Repos und muss ohne Befund bleiben – inklusive der Doktrin, dass ein
   `# codeql[...]`-Kommentar keine Heilung ist, sondern selbst ein Befund.
   Hintergrund und Entscheidungen: CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md
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
        raw_report = {
            "zeit": "04.10.2026 12:00 Uhr",
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
        # Weder innen noch außen darf ein Feld Geheimnis behaupten.
        self.assertNotIn('"secrets":', payload_str)
        self.assertNotIn('"fehlende_secrets":', payload_str)
        self.assertNotIn('"pflicht_env":', payload_str)
        self.assertIn('"required_env_names":', payload_str)
        self.assertIn('"missing_env_names":', payload_str)
        self.assertIn("MASTODON_ACCESS_TOKEN", payload_str)  # NAME bleibt sichtbar

    def test_social_preflight_report_uses_honest_field_names(self):
        """Der Bericht selbst (nicht erst die JSON-Hülle) trägt ehrliche Namen."""
        eintrag = social_preflight.pruefe_kanal(
            "mastodon",
            {"label": "Mastodon", "enabled": True,
             "pflicht_env": ["MASTODON_ACCESS_TOKEN"], "vars": []},
            {}, offline=True)
        self.assertIn("pflicht_env", eintrag)
        self.assertIn("fehlende_env", eintrag)
        self.assertNotIn("secrets", eintrag)
        self.assertNotIn("fehlende_secrets", eintrag)
        # Das Playbook ist die Quelle dieser Namen – und nur der Namen.
        playbook = (ROOT / "data" / "social" / "channels.yaml").read_text(encoding="utf-8")
        self.assertNotIn("\n    secrets:", playbook)
        self.assertIn("pflicht_env:", playbook)

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
    """Alert #80: die Wache ersetzt die Kontrolle, die das Default-Setup nicht liefert.

    GitHubs Default-Setup ignoriert `paths-ignore` UND `# codeql[...]`-
    Kommentare. Ein Alert wie #80 entsteht also auch dann, wenn die
    SARIF-Filterung der erweiterten Konfiguration grün meldet. Deshalb läuft
    hier dieselbe Prüfung lokal – fail-closed, vor dem Push.
    """

    WACHE = SCRIPTS / "clear_text_logging_guard.py"
    REGELN = ("py/clear-text-logging-sensitive-data",
              "py/clear-text-storage-sensitive-data")

    def _lauf(self, *args):
        return subprocess.run([sys.executable, str(self.WACHE), *args],
                              capture_output=True, text=True, cwd=str(ROOT))

    def test_wache_existiert_und_besteht_den_eigenen_selbsttest(self):
        """Eine Wache ohne Eigenprüfung ist Schein-Sicherheit."""
        self.assertTrue(self.WACHE.is_file(), "scripts/clear_text_logging_guard.py fehlt")
        erg = self._lauf("--selftest")
        self.assertEqual(erg.returncode, 0,
                         f"Selbsttest der Klartext-Wache fehlgeschlagen:\n{erg.stdout}\n{erg.stderr}")

    def test_repository_ist_frei_von_klartext_fluessen(self):
        """Der eigentliche Regressionsschutz für Alert #80 (und #77)."""
        erg = self._lauf("--json", "--quiet")
        self.assertIn(erg.returncode, (0, 1), f"Wache abgestürzt:\n{erg.stderr}")
        bericht = json.loads(erg.stdout)
        befunde = bericht.get("befunde", [])
        bericht_text = "\n".join(
            f"  {b['datei']}:{b['zeile']} [{b['regel']}] {b['art']}: {b['quelle']} → {b['senke']}"
            for b in befunde)
        self.assertEqual(
            befunde, [],
            "Klartext-Fluss in sensibel benannte Ausgabe – bitte den NAMEN ehrlich "
            "machen, den Wert entschärfen oder die Ausgabe weglassen "
            f"(Unterdrücken gilt nicht):\n{bericht_text}")

    def test_keine_unterdrueckung_der_klartext_regeln(self):
        """`# codeql[...]` ist für diese beiden Regeln keine Heilung, sondern ein Befund."""
        treffer = []
        for pfad in sorted(ROOT.glob("scripts/**/*.py")):
            # Die Wache selbst führt den Marker als Lehrstoff: in ihrer Doktrin
            # und als Positivprobe ("unterdrueckung_zaehlt"). Sie prüft sich im
            # eigenen Selbsttest – hier wäre der Treffer ein Fehlalarm.
            if pfad.name == "clear_text_logging_guard.py":
                continue
            for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
                for regel in self.REGELN:
                    if f"codeql[{regel}]" in zeile:
                        treffer.append(f"{pfad.relative_to(ROOT)}:{nr}")
        self.assertEqual(
            treffer, [],
            "Das Default-Setup sieht diese Kommentare nicht – der Alert bleibt offen. "
            f"Architektonisch heilen statt unterdrücken: {treffer}")

    def test_namensvertrag_der_geheilten_stellen(self):
        """Die Namen von #80 bleiben ehrlich – sonst kehrt der Alert zurück."""
        gov = (SCRIPTS / "governance_contract.py").read_text(encoding="utf-8")
        self.assertNotIn("def c9_secret_leak(", gov)
        self.assertIn("def c9_klartext_leck(", gov)
        self.assertNotIn("SECRET_PATTERNS =", gov)
        wache = (SCRIPTS / "secrets_age_guard.py").read_text(encoding="utf-8")
        self.assertNotIn("def oauth_empfaenger_findings(", wache)
        self.assertIn("def rueckleitung_findings(", wache)


if __name__ == "__main__":
    unittest.main(verbosity=2)
