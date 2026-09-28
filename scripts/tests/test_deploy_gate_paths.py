#!/usr/bin/env python3
"""Vertragstest für die Deploy-Negativliste (`deploy-gate` in deploy.yml).

Das Deploy-Gate entscheidet per Pfad-Muster, ob ein Push den vollen Deploy
(Hugo-Build + Vertonung, bis 150 Min.) auslöst oder ob es ein reiner
Zustands-/Doku-Push ist. Zwei Fehlerrichtungen sind teuer:

  * ZU VIEL Deploy: Ein Lebenszeichen der Wachen (z. B. der neue Herzschlag
    der Affiliate-Integritäts-Wache, #281) darf keinen Livegang anstoßen –
    sonst verstopft genau die Queue, die der Premium-Audit 12.09.2026
    entlastet hat (Befund F1).
  * ZU WENIG Deploy: Ein Site-Pfad (content/, layouts/, static/, hugo.toml)
    darf NIE als „irrelevant" durchrutschen – dann bliebe ein Artikel
    unveröffentlicht.

Hintergrund Issue #433 (28.09.2026):
Wenn ein site-relevanter PR (#431) in der pages-deploy-Queue von einem
reinen Workflow-PR (#432) verdrängt wird, vergleicht das Gate nicht
mehr nur `event.before...after`, sondern diffed seit dem letzten ECHTEN
Live-Stand auf `gh-pages` (SSOT).
"""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPLOY_YML = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
CATCHUP_YML = os.path.join(ROOT, ".github", "workflows", "deploy-catchup.yml")


def state_only_pattern() -> re.Pattern:
    """Das STATE_ONLY-Muster aus deploy.yml (SSOT, keine Kopie im Test)."""
    with open(DEPLOY_YML, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"STATE_ONLY='([^']+)'", text)
    if not m:
        raise AssertionError("STATE_ONLY-Muster nicht in deploy.yml gefunden")
    return re.compile(m.group(1))


class DeployGatePfadTestCase(unittest.TestCase):
    """Relevanz = NICHT STATE_ONLY (vgl. den `grep -vE`-Schritt im Gate)."""

    def setUp(self):
        self.pattern = state_only_pattern()

    def relevant(self, path: str) -> bool:
        return not bool(self.pattern.match(path))

    def test_lebenszeichen_loest_keinen_deploy_aus(self):
        """Der Herzschlag der Affiliate-Wache (#281) ist kein Site-Inhalt."""
        for path in (".affiliate_integrity_state.json",
                     ".affiliate_intent_state.json",
                     ".bestand_gate_state.json",
                     ".casing_report.json",
                     ".indexnow_submitted.json",
                     ".meta_cache.json",
                     "AFFILIATE-INTEGRITY-REPORT.md",
                     "PRODUKTIONS-STATUS.md",
                     "BOT-WATCHDOG-REPORT.md",
                     "data/alert_router_state.json",
                     "data/integrity_history.jsonl",
                     "data/integrity_lock.json",
                     "data/spam_history.jsonl",
                     "data/social_log.jsonl",
                     "data/revenue_funnel.json",
                     "data/revenue_funnel_history.jsonl",
                     "data/cwv_history.jsonl",
                     "data/cwv_state.json",
                     "data/awin_fetch.meta.json",
                     "data/umami_clicks.meta.json",
                     "data/governance_status.json",
                     "data/governance_history.jsonl",
                     "data/alerting_heartbeat.json"):
            self.assertFalse(self.relevant(path),
                             f"{path} ist ein Zustands-/Nachweis-Pfad und darf keinen "
                             f"Deploy auslösen")

    def test_zustands_und_doku_verzeichnisse_sind_gefiltert(self):
        for path in ("docs/README.md", "scripts/affiliate_integrity_gate.py",
                     "scripts/deploy_drift_guard.py",
                     ".github/workflows/affiliate-integrity-daily.yml",
                     ".github/workflows/deploy.yml",
                     ".github/workflows/deploy-catchup.yml",
                     "e2e/server.mjs", "e2e/newsletter.spec.mjs",
                     "data/social/plan.json",
                     "data/research/brief.md", "data/audit/2026-09-15.jsonl",
                     "static/images/social/pin.jpg",
                     "package.json", "package-lock.json", ".gitignore"):
            self.assertFalse(self.relevant(path),
                             f"{path} liegt in einem Zustands-/Doku-Verzeichnis")

    def test_site_pfade_sind_immer_deploy_relevant(self):
        for path in ("content/posts/2026-09-15-test/index.md",
                     "content/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/index.md",
                     "layouts/_default/baseof.html",
                     "layouts/pillar/single.html",
                     "assets/css/extended/custom.css",
                     "assets/css/extended/zzz-agency-polish.css",
                     "static/images/cover.jpg",
                     "hugo.toml",
                     "data/themenwelten.json",
                     "data/aktuelle_entwicklungen.yaml",
                     "data/design/varianten.yaml",
                     "data/saisons.yaml",
                     "data/affiliate_ziele.yaml",
                     "data/newsletter_studio.json",
                     "data/newsletter_kadenz.json"):
            self.assertTrue(self.relevant(path),
                            f"{path} verändert die Live-Site und MUSS einen Deploy auslösen")

    def test_neue_pfade_sind_per_default_relevant(self):
        """Fail-safe der Liste: alles Unbekannte wird deployt (nie still übersprungen)."""
        for path in ("static/js/neu.js", "data/neuer_state.json.bak",
                     ".affiliate_integrity_state.json.bak"):
            self.assertTrue(self.relevant(path),
                            "unbekannte Pfade sind per Default relevant (Fail-safe)")

    def test_incident_433_simulation(self):
        """Simuliert den Incident #433:
        1. Live auf gh-pages: Commit A
        2. PR #431 (Commit B) ändert CSS + Pillar-Layout
        3. PR #432 (Commit C) ändert nur .github/workflows
        4. Alter Fehler: Diff B..C = nur .github -> deploy=false (BUG!)
        5. Neuer Vertrag: Diff A..C = CSS + Pillar + .github -> deploy=true (BEHOBEN!)
        """
        import deploy_drift_guard as ddg

        sha_a = "a263bcb3d67d08a81ce8407b4768dad5a2808979"
        sha_b = "1d3a0b0d67d08a81ce8407b4768dad5a2808979"
        sha_c = "ada8606867d08a81ce8407b4768dad5a2808979"

        # Diff nur B..C (alter fehlerhafter Weg)
        diff_b_c = [".github/workflows/upload-artifact.yml"]
        rel_b_c = [f for f in diff_b_c if not bool(self.pattern.match(f))]
        self.assertEqual(len(rel_b_c), 0, "B..C enthält nur Workflows")

        # Diff A..C (neuer gehärteter Weg seit letztem Live-Stand)
        diff_a_c = [
            "assets/css/extended/zzz-agency-polish.css",
            "layouts/pillar/single.html",
            "content/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/index.md",
            ".github/workflows/upload-artifact.yml",
        ]
        rel_a_c = [f for f in diff_a_c if not bool(self.pattern.match(f))]
        self.assertGreater(len(rel_a_c), 0, "A..C enthält site-relevante Dateien!")
        self.assertIn("assets/css/extended/zzz-agency-polish.css", rel_a_c)
        self.assertIn("layouts/pillar/single.html", rel_a_c)

        # Drift-Guard Prüfung
        drift_res = ddg.analyze_drift(sha_a, sha_c, diff_a_c, auto_detect=False)
        self.assertEqual(drift_res["status"], "SITE_DRIFT")
        self.assertTrue(drift_res["needs_deploy"])
        self.assertTrue(drift_res["is_drift"])

    def test_workflow_dateien_enthalten_gh_pages_pruefung(self):
        """Stellt sicher, dass deploy.yml und deploy-catchup.yml gh-pages als SSOT prüfen."""
        with open(DEPLOY_YML, encoding="utf-8") as f:
            deploy_text = f.read()
        self.assertIn("LIVE_DEPLOY_SHA", deploy_text)
        self.assertIn("commits/gh-pages", deploy_text)

        with open(CATCHUP_YML, encoding="utf-8") as f:
            catchup_text = f.read()
        self.assertIn("ref: 'gh-pages'", catchup_text)
        self.assertIn("liveDeploySha", catchup_text)
        self.assertIn("deployJob.conclusion === 'success'", catchup_text)


if __name__ == "__main__":
    unittest.main()
