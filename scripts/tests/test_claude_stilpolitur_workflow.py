#!/usr/bin/env python3
"""Vertragsprüfungen für den ausfallsicheren Stilpolitur-Workflow (#468).

WARUM DIESE DATEI (Reparatur Issue #468, 25./30.09.2026)
--------------------------------------------------------
Der Workflow „Claude-Stilpolitur (Mo/Mi/Fr)" fiel planmäßig rot aus, weil
ein FREMDER Zugang (Puter-Token) fehlte – obwohl die eigene, vollständig
offline laufende Premium-Politur einwandfrei gearbeitet hätte. Der Lauf
brach im Preflight ab: nichts poliert, nichts committet, und die
Fehlermeldung suggerierte einen Defekt im Repository.

Der Vertrag lautet seitdem: ZWEI LANES, GETRENNT BEWERTET.

  * INTERNE LANE – fail-closed (roter Lauf):
    Pflichtdateien, Selbsttests, Grammatik- und Sprachglatt-Politur.
    Diese Schritte dürfen NICHT maskiert werden (`|| echo`, `|| true`),
    sonst läuft eine echte Regression still grün durch.

  * EXTERNE LANE – best effort (gelbe Warnung, grüner Lauf):
    Fehlendes Token, npm-Transient, Puter-Ausfall oder erschöpftes
    Gratis-Kontingent degradieren ehrlich auf die Offline-Politur.
    Kein Ersatzmodell, kein Anthropic-Key, keine kostenpflichtige API.
    Einzige Ausnahme: Exit 2 (Sabotage-Schutz im eigenen Skript) ist
    KEIN Fremdausfall und muss rot bleiben.

  * Der Commit-Schritt sichert das Ergebnis der internen Lane immer –
    auch wenn der externe Zusatz danach degradiert (sonst wiederholt
    jeder Lauf dieselbe Arbeit) – aber niemals nach einem Absturz der
    Offline-Engines (kein halb angewandter Bestand).

Die Prüfungen arbeiten auf dem geparsten YAML statt auf Textfragmenten:
Ein Umbau der Kommentare darf den Test nicht rot färben, ein Umbau der
Ausfallsicherheit dagegen sehr wohl.
"""

from pathlib import Path
import re
import unittest

try:
    import yaml
except ImportError:                                     # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "claude-stilpolitur.yml"

TOKEN_GUARD = "steps.preflight.outputs.puter_available == 'true'"


def _ohne_kommentare(text: str) -> str:
    """Nur die ausführbaren Shell-Zeilen (Kommentare erklären, sie laufen nicht)."""
    return "\n".join(
        zeile for zeile in text.splitlines()
        if not zeile.lstrip().startswith("#")
    )


@unittest.skipIf(yaml is None, "PyYAML nicht verfügbar")
class ClaudeStilpoliturWorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.text)
        cls.steps = cls.doc["jobs"]["stilpolitur"]["steps"]

    def schritt(self, praefix: str) -> dict:
        treffer = [s for s in self.steps
                   if (s.get("name") or s.get("uses") or "").startswith(praefix)]
        self.assertEqual(
            len(treffer), 1,
            f"Genau ein Schritt muss mit '{praefix}' beginnen, gefunden: {len(treffer)}",
        )
        return treffer[0]

    # ------------------------------------------------------------------
    #  Externe Lane: ein fehlender Fremdzugang stoppt die Redaktion nie
    # ------------------------------------------------------------------
    def test_missing_external_token_is_graceful_degradation(self):
        preflight = self.schritt("Voraussetzungen prüfen")
        self.assertEqual(preflight.get("id"), "preflight")
        run = preflight["run"]

        self.assertIn('echo "puter_available=false" >> "$GITHUB_OUTPUT"', run)
        self.assertIn('echo "puter_available=true" >> "$GITHUB_OUTPUT"', run)
        self.assertIn("::warning title=Claude-Zugang nicht konfiguriert", run)
        self.assertNotIn("PUTER_AUTH_TOKEN fehlt::", run)
        self.assertNotRegex(
            _ohne_kommentare(run),
            re.compile(r"PUTER_AUTH_TOKEN[^\n]*\n(?:.*\n){0,8}\s*exit 1"),
            "Ein fehlendes Fremd-Token darf den Lauf nicht abbrechen.",
        )

    def test_claude_and_sdk_are_only_used_with_token(self):
        sdk = self.schritt("Puter-Brücke installieren")
        claude = self.schritt("Claude (kostenlos ohne API)")

        self.assertEqual(sdk.get("id"), "sdk")
        self.assertEqual(claude.get("id"), "claude")
        self.assertIn(TOKEN_GUARD, sdk["if"])
        self.assertIn(TOKEN_GUARD, claude["if"])
        self.assertIn("steps.sdk.outputs.claude_ready == 'true'", claude["if"])
        self.assertIn("@heyputer/puter.js@2.6.3", sdk["run"])
        self.assertIn("python3 scripts/claude_stilpolitur.py --fix", claude["run"])

    def test_external_transients_never_turn_the_run_red(self):
        """npm-Blip, Puter-Ausfall oder leeres Gratis-Kontingent = gelb, nicht rot."""
        sdk = self.schritt("Puter-Brücke installieren")
        claude = self.schritt("Claude (kostenlos ohne API)")

        # SDK: Wiederholversuche und ehrliche Degradierung statt Abbruch.
        self.assertIn('echo "claude_ready=false" >> "$GITHUB_OUTPUT"', sdk["run"])
        self.assertIn('echo "claude_ready=true" >> "$GITHUB_OUTPUT"', sdk["run"])
        self.assertIn("::warning title=Puter-Brücke nicht installierbar", sdk["run"])
        self.assertRegex(sdk["run"], r"for versuch in 1 2 3")

        # Claude-Lauf: Exit-Code wird ausgewertet, nicht verschluckt.
        self.assertIn("|| rc=$?", claude["run"])
        self.assertIn('echo "claude_status=degradiert" >> "$GITHUB_OUTPUT"',
                      claude["run"])
        self.assertIn("::warning title=Claude-Zusatz gestört", claude["run"])

    def test_silent_uselessness_is_reported_not_faked_green(self):
        """Exit 0 ohne einen einzigen polierten Artikel ist KEIN Erfolg."""
        claude = self.schritt("Claude (kostenlos ohne API)")
        run = claude["run"]
        self.assertIn("python3 scripts/claude_stilpolitur_wirkung.py", run)
        self.assertIn("::warning title=Claude-Zusatz wirkungslos", run)
        self.assertIn('echo "claude_status=unklar" >> "$GITHUB_OUTPUT"', run)

        preflight = self.schritt("Voraussetzungen prüfen")
        self.assertIn("scripts/claude_stilpolitur_wirkung.py", preflight["run"])
        self.assertIn("python3 scripts/claude_stilpolitur_wirkung.py --selftest",
                      self.schritt("Selbsttest HART")["run"])

    def test_sabotage_exit_two_stays_red(self):
        """Exit 2 ist eine Regression im EIGENEN Code – niemals wegdegradieren."""
        run = self.schritt("Claude (kostenlos ohne API)")["run"]
        self.assertIn('if [ "$rc" -eq 2 ]; then', run)
        self.assertIn("::error title=Claude-Stilpolitur: Selbsttest rot", run)
        block = run.split('if [ "$rc" -eq 2 ]; then', 1)[1].split("fi", 1)[0]
        self.assertIn("exit 1", block)

    # ------------------------------------------------------------------
    #  Interne Lane: fail-closed, niemals maskiert
    # ------------------------------------------------------------------
    def test_offline_polish_is_unconditional_and_fail_closed(self):
        offline = self.schritt("Offline-Optimierung")
        run = offline["run"]

        self.assertEqual(offline.get("id"), "offline")
        self.assertNotIn("if", offline, "Die Offline-Politur läuft in JEDEM Lauf.")
        self.assertIn("set -Eeuo pipefail", run)
        self.assertIn("grammar_check.py --fix", run)
        self.assertIn("sprachglatt.py --fix", run)
        # Ohne --strict liefern beide Engines nur bei echtem Defekt ≠ 0.
        for zeile in _ohne_kommentare(run).splitlines():
            if "--fix" in zeile:
                self.assertNotIn(
                    "||", zeile,
                    f"Offline-Fehler dürfen nicht maskiert werden: {zeile!r}")

    def test_selftests_run_before_any_write(self):
        selftest = self.schritt("Selbsttest HART")
        run = selftest["run"]
        self.assertNotIn("if", selftest)
        self.assertIn("set -Eeuo pipefail", run)
        for skript in ("grammar_check.py", "sprachglatt.py", "claude_stilpolitur.py"):
            self.assertIn(f"python3 scripts/{skript} --selftest", run)

        namen = [(s.get("name") or "") for s in self.steps]
        self.assertLess(
            next(i for i, n in enumerate(namen) if n.startswith("Selbsttest HART")),
            next(i for i, n in enumerate(namen) if n.startswith("Offline-Optimierung")),
            "Der Sabotage-Schutz muss VOR dem ersten Schreibvorgang laufen.",
        )

    def test_commit_survives_a_degraded_external_lane(self):
        commit = self.schritt("Änderungen committen & pushen")
        bedingung = commit["if"]

        self.assertIn("!cancelled()", bedingung)
        self.assertIn("steps.offline.outcome == 'success'", bedingung)
        self.assertNotIn("steps.claude", bedingung,
                         "Ein gestörter Fremdzugang darf die Offline-Ergebnisse "
                         "nicht verwerfen.")
        self.assertIn("scripts/git_sync.sh --push-only", commit["run"])

    def test_run_summary_is_always_written(self):
        bilanz = self.schritt("Lauf-Bilanz")
        self.assertIn("!cancelled()", bilanz["if"])
        self.assertIn("$GITHUB_STEP_SUMMARY", bilanz["run"])
        gemeldet = " ".join(str(v) for v in (bilanz.get("env") or {}).values())
        for quelle in ("steps.preflight.outputs.puter_available",
                       "steps.sdk.outputs.claude_ready",
                       "steps.claude.outputs.claude_status",
                       "steps.offline.outcome"):
            self.assertIn(quelle, gemeldet)

    # ------------------------------------------------------------------
    #  Mandat: kostenlos, ohne API, ausschließlich claude-sonnet-5
    # ------------------------------------------------------------------
    def test_no_paid_or_alternate_model_fallback(self):
        self.assertIn("NUR claude-sonnet-5", self.text)
        for verboten in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY",
                         "OPENAI_API_KEY"):
            self.assertNotIn(verboten, self.text)

    def test_schedule_stays_monday_wednesday_friday(self):
        ausloeser = self.doc[True] if True in self.doc else self.doc["on"]
        self.assertEqual([e["cron"] for e in ausloeser["schedule"]],
                         ["50 4 * * 1,3,5"])
        self.assertIn("workflow_dispatch", ausloeser)


if __name__ == "__main__":
    unittest.main()
