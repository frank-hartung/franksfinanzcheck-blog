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

Beide Richtungen werden hier eingefroren. Der Test liest das Muster direkt
aus dem Workflow, damit er nicht gegen eine Kopie prüft.

Hintergrund (Nebenbefund 15.09.2026): Die Verzeichnis-Einträge der Liste
hiessen `docs/`, `scripts/`, `.github/` … und waren wegen der Anker ^…$
wirkungslos – nur exakte Dateinamen trafen zu. Damit galt jeder Push unter
diesen Verzeichnissen als deploy-relevant.
"""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPLOY_YML = os.path.join(ROOT, ".github", "workflows", "deploy.yml")


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
                     "AFFILIATE-INTEGRITY-REPORT.md",
                     "PRODUKTIONS-STATUS.md",
                     "data/alert_router_state.json",
                     "data/integrity_history.jsonl"):
            self.assertFalse(self.relevant(path),
                             f"{path} ist ein Zustands-/Nachweis-Pfad und darf keinen "
                             f"Deploy auslösen")

    def test_zustands_und_doku_verzeichnisse_sind_gefiltert(self):
        for path in ("docs/README.md", "scripts/affiliate_integrity_gate.py",
                     ".github/workflows/affiliate-integrity-daily.yml",
                     "e2e/server.mjs", "data/social/plan.json",
                     "data/research/brief.md", "data/audit/2026-09-15.jsonl",
                     "static/images/social/pin.jpg"):
            self.assertFalse(self.relevant(path),
                             f"{path} liegt in einem Zustands-/Doku-Verzeichnis")

    def test_site_pfade_sind_immer_deploy_relevant(self):
        for path in ("content/posts/2026-09-15-test/index.md",
                     "layouts/_default/baseof.html",
                     "assets/css/extended/custom.css",
                     "static/images/cover.jpg",
                     "hugo.toml",
                     "data/themenwelten.json",
                     "data/aktuelle_entwicklungen.yaml"):
            self.assertTrue(self.relevant(path),
                            f"{path} verändert die Live-Site und MUSS einen Deploy auslösen")

    def test_neue_pfade_sind_per_default_relevant(self):
        """Fail-safe der Liste: alles Unbekannte wird deployt (nie still übersprungen)."""
        for path in ("static/js/neu.js", "data/neuer_state.json.bak",
                     ".affiliate_integrity_state.json.bak"):
            self.assertTrue(self.relevant(path),
                            "unbekannte Pfade sind per Default relevant (Fail-safe)")


if __name__ == "__main__":
    unittest.main()
