#!/usr/bin/env python3
"""Vertragstests für die Affiliate-Restmenge (#446).

Der Status wird von drei technischen Grenzen konsumiert (Gate, Bot-Watchdog,
GitHub-Workflow). Diese Tests halten die migrationsfähige, fail-closed
Semantik ohne Dateisystem oder Netzwerk fest.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from affiliate_integrity_state import (  # noqa: E402
    STATE_SCHEMA_VERSION,
    state_contract_error,
    unresolved_problems,
)


class AffiliateIntegrityStateContractTests(unittest.TestCase):
    def test_gruener_legacy_lauf_migriert_historie_zu_leerer_restmenge(self):
        state = {"exit_code": 0, "content_problems": ["im-lauf-geheilt"]}
        self.assertEqual(unresolved_problems(state), [])
        self.assertIsNone(state_contract_error(state))

    def test_roter_legacy_lauf_behaelt_content_problems_fail_closed(self):
        state = {"exit_code": 1, "content_problems": ["noch-offen"]}
        self.assertEqual(unresolved_problems(state), ["noch-offen"])
        self.assertIsNone(state_contract_error(state))

    def test_v2_restmenge_hat_vorrang_vor_audit_historie(self):
        state = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "exit_code": 0,
            "content_problems": ["historisch-geheilt"],
            "unresolved_problems": [],
        }
        self.assertEqual(unresolved_problems(state), [])
        self.assertIsNone(state_contract_error(state))

    def test_v2_widerspruch_ist_fail_closed(self):
        state = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "exit_code": 0,
            "content_problems": ["historisch"],
            "unresolved_problems": ["widerspruch"],
        }
        self.assertIn("grüner Lauf", state_contract_error(state) or "")

    def test_v2_roter_inhaltslauf_braucht_restmenge(self):
        state = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "exit_code": 1,
            "content_problems": ["fehlerhaft"],
            "unresolved_problems": [],
        }
        self.assertIn("keine offene Restmenge", state_contract_error(state) or "")

    def test_v2_restmenge_enthält_nur_funde_aus_diesem_lauf(self):
        """Eine fremde Restmenge wäre ein neuer Phantom-Alarm (#446)."""
        state = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "exit_code": 1,
            "content_problems": ["geheilt", "noch-offen"],
            "unresolved_problems": ["phantom"],
        }
        self.assertIn("keinen Fund der Laufhistorie",
                      state_contract_error(state) or "")

    def test_v2_teilheilung_behält_nur_den_echten_restfund(self):
        state = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "exit_code": 1,
            "content_problems": ["geheilt", "noch-offen"],
            "unresolved_problems": ["noch-offen"],
        }
        self.assertEqual(unresolved_problems(state), ["noch-offen"])
        self.assertIsNone(state_contract_error(state))

    def test_v2_restmenge_muss_liste_sein(self):
        state = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "exit_code": 0,
            "content_problems": [],
            "unresolved_problems": "nicht-valide",
        }
        self.assertEqual(unresolved_problems(state), [])
        self.assertIn("keine Liste", state_contract_error(state) or "")


if __name__ == "__main__":
    unittest.main()
