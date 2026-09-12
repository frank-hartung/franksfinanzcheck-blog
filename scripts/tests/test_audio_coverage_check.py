#!/usr/bin/env python3
"""Regressionstest: audio_coverage_check (Empfehlung 4 des Premium-Audits 12.09.2026).

Der Befund des Audits lautete „nur 1 von 31 Artikeln mit Studio-Audio". Gezählt
war damit `static/audio/` im Quell-Repo – die fertigen Tonspuren liegen aber auf
dem gh-pages-Zweig (`deploy.yml` holt sie dort pro Lauf als Cache zurück). Der
Test hält zwei Dinge fest:

  1. Die Wache muss den Pages-Zweig lesen (Ref-Modus) und darf nicht den
    Quellbaum für die Wahrheit halten.
  2. Kein Nachweis ist KEIN Null-Ergebnis: „unbekannt" muss als Hinweis enden,
    nicht als Panik-Meldung „0 % Audio" (und nicht als grüner Lauf).
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ac = _load("audio_coverage_check", os.path.join(SCRIPTS, "audio_coverage_check.py"))
gc = _load("governance_contract", os.path.join(SCRIPTS, "governance_contract.py"))


class Zaehlen(unittest.TestCase):
    def test_live_bestand_zaehlt_drafts_und_zukunft_nicht(self):
        slugs = ac.live_artikel(ROOT)
        self.assertTrue(slugs, "kein Live-Artikel gefunden")
        draft = [os.path.basename(os.path.dirname(p)) for p in subprocess.run(
            ["grep", "-rl", "^draft: true", "content/posts"], cwd=ROOT,
            capture_output=True, text=True).stdout.split()]
        self.assertFalse(set(draft) & set(slugs), "Drafts dürfen nicht mitzählen")
        self.assertGreaterEqual(len(slugs), 25,
                                "Zu wenige Live-Artikel – Filter zu scharf?")

    def test_selbsttest_der_wache(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "audio_coverage_check.py"),
                             "--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_unbekannt_ist_nicht_null(self):
        t = ac.tabelle({"artikel": ["a", "b"], "spuren": set(), "quelle": "",
                        "fehlend": ["a", "b"]})
        self.assertIn("unbekannt", t)
        self.assertNotIn("❌", t)

    def test_lücke_wird_benannt_und_bleibt_ohne_strict_gruen(self):
        t = ac.tabelle({"artikel": ["a", "b"], "spuren": {"a"}, "quelle": "x",
                        "fehlend": ["b"]})
        self.assertIn("1/2", t)
        self.assertIn("audio_backfill=true", t)
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "audio_coverage_check.py"),
                             "--dir", "gibt-es-nicht"], cwd=ROOT,
                            capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)
        self.assertIn("unbekannt", rc.stdout)


class Verdrahtung(unittest.TestCase):
    def test_wache_ist_registriert_und_laeuft_taeglich(self):
        self.assertIn("audio_coverage_check.py", gc.GUARDS)
        yml = open(os.path.join(ROOT, ".github", "workflows", "lesehilfen-gate.yml"),
                   encoding="utf-8").read()
        self.assertIn("audio_coverage_check.py --ref origin/gh-pages", yml)
        self.assertIn("audio_coverage_check.py --selftest", yml)
        # Der Pages-Zweig ist im Default-Checkout nicht gemappt – ohne Read-Recht
        # würde der Nachhol-Fetch scheitern und die Zahl wäre für immer „unbekannt".
        self.assertIn("contents: read", yml)

    def test_ref_pfad_liest_den_pages_zweig_nicht_den_quellbaum(self):
        # Der Quellbaum allein darf nie die Antwort sein. Die fertigen
        # Tonspuren leben auf dem gh-pages-Zweig (deploy.yml: audio/articles),
        # im Quellbaum höchstens Überreste. Premium-Audit 12.09.2026: die
        # frühere harte Schwelle (>= 15) scheiterte in jedem vollen Clone
        # (gh-pages dort lesbar, aber nicht mit dem CI-Stand identisch) –
        # die Regression wird jetzt RELATIV geprüft: der Pages-Zweig muss
        # MEHR Spuren tragen als der Quellbaum, sonst ist der Vorpfad
        # (audio/articles) in deploy.yml vermutlich geändert.
        spur = ac.spuren_von_dir(os.path.join(ROOT, "static", "audio"))
        self.assertLessEqual(len(spur), 2)
        res = ac.auswerten(ROOT, "origin/gh-pages", "")
        if res["quelle"] == "origin/gh-pages":
            self.assertGreater(len(res["spuren"]), len(spur),
                               "Pages-Zweig trägt keine Spur mehr als der "
                               "Quellbaum – Vorpfad geändert? (deploy.yml "
                               "schreibt audio/articles)")
        else:
            self.assertIn("nicht verfügbar", res["quelle"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
