#!/usr/bin/env python3
"""Vertrag zwischen Affiliate-State und täglicher Issue-Pflege (#446).

Die Python-Wache schützt den Bot-Watchdog. Dieses kleine Regressionstest-Modul
schützt zusätzlich den zweiten Meldeweg im GitHub-Workflow: Eine im selben
Lauf geheilte Fundhistorie darf ein offenes Fach-Issue schließen, ein echter
Restfund oder Werkzeugfehler dagegen nicht.

Der Test liest bewusst den ausgeführten github-script-Block statt Kommentare
zu prüfen. So fällt eine Rückkehr zur früheren Abkürzung ``exit_code == 0``
ohne kanonische Restmenge direkt in CI auf.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "affiliate-integrity-daily.yml"


def _workflow_code() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


class AffiliateIntegrityWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.code = _workflow_code()

    def test_state_step_uses_the_shared_restmengen_contract(self):
        """Workflow, Gate und Watchdog dürfen keine eigene Semantik erfinden."""
        self.assertIn(
            "from affiliate_integrity_state import unresolved_problems, state_contract_error",
            self.code,
        )
        self.assertIn("open_problems = unresolved_problems(state)", self.code)
        self.assertIn("unresolved_problems={len(open_problems)}", self.code)

    def test_issue_close_path_requires_empty_canonical_restmenge(self):
        """Historie ≠ Restmenge; nur die explizit leere Restmenge ist grün."""
        self.assertIn("UNRESOLVED_PROBLEMS: ${{ steps.state.outputs.unresolved_problems }}",
                      self.code)
        self.assertIn(
            "const unresolvedProblems = Number(process.env.UNRESOLVED_PROBLEMS || 0);",
            self.code,
        )
        self.assertRegex(
            self.code,
            re.compile(
                r"const green = exitCode === '0' && unresolvedProblems === 0\s*"
                r"&& toolErrors === 0 && !stateContractError;"
            ),
        )


if __name__ == "__main__":
    unittest.main()
