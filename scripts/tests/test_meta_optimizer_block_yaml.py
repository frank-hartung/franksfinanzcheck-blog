#!/usr/bin/env python3
"""Dauerschutz #1384: meta_optimizer parst YAML-Blocklisten für `keywords:` korrekt."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import meta_optimizer as mo  # noqa: E402


BLOCK_POST = """---
title: "Kfz-Versicherung vergleichen: Was ändert sich beim Beitrag?"
description: "Vergleiche Kfz-Tarife mit gleicher Fahrleistung und Selbstbeteiligung. Prüfe Vertragsende, Kündigungsfrist und bestätigten Versicherungsbeginn."
draft: false
cover:
  image: images/covers/probe.jpg
  alt: Probe
keywords:
- Kfz-Versicherung Vergleich
- Kfz-Versicherung wechseln
- Autoversicherung Vergleich
- Schadenfreiheitsklasse
---

Ein kurzer Beispieltext.
"""


class MetaOptimizerBlockYamlTest(unittest.TestCase):
    def test_blockliste_keywords_und_cover_werden_vollstaendig_erkannt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "2026-11-26-probe" / "index.md"
            p.parent.mkdir(parents=True)
            p.write_text(BLOCK_POST, encoding="utf-8")
            arts = mo.load_articles(files=[str(p)])
            self.assertEqual(len(arts), 1)
            res = mo.audit(arts[0])
            self.assertEqual(res["kw"], 4)
            self.assertEqual(res["issues"], [], f"Unerwartete Meta-Funde: {res['issues']}")


if __name__ == "__main__":
    unittest.main()
