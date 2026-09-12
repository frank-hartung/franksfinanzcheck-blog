#!/usr/bin/env python3
"""Regressionstest: live_policy_guard (Empfehlung 8 des Premium-Audits 12.09.2026).

Lockt genau die zwei Rückschritte, für die die Wache gebaut wurde:

  1. Cloudflare/CDN überschreiben die Live-Auslieferung, das Repo bleibt grün –
     also muss jede Regel (L1 robots, L2 Sitemap, L3 Seite, L4 HTTP) nachweislich
     einen Befund auslösen, wenn live vom Build abweicht.
  2. Eine Wache, die ohne Netz „grün" meldet, ist teurer als keine. Deshalb ist
     der Netz-Ausfall doppelt verankert: ohne --require-live Hinweis, mit
     --require-live ROT – und der Code dafür heißt bewusst nicht `unreachable`.

Zusätzlich die Ledger-Kopplung: wer die Wache aus premium-governance.yml oder aus
governance_gate.STEPS löst, verliert die Messung still – beide Richtungen sind
hier asserted.
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


lp = _load("live_policy_guard", os.path.join(SCRIPTS, "live_policy_guard.py"))
gc = _load("governance_contract", os.path.join(SCRIPTS, "governance_contract.py"))
gg = _load("governance_gate", os.path.join(SCRIPTS, "governance_gate.py"))

BOTS = ("Pinterestbot",) + lp.ANSWER_BOTS


class LiveRobotsUndSitemap(unittest.TestCase):
    """L1/L2: Cloudflare-Rewrite und gecachte Duplikat-Sitemap werden gesehen."""

    def _robots(self, text: str, local: str) -> list:
        F: list = []
        lp.check_robots(text, local, F, [])
        return [m for _, m in F]

    def test_pinterest_und_antwortbots_muessen_leben(self):
        ok = "\n".join(f"User-agent: {b}\nAllow: /" for b in BOTS) + \
             f"\nSitemap: {lp.BASE}/sitemap.xml\n"
        for bot in BOTS:
            ohne = "\n".join(l for l in ok.splitlines() if l != f"User-agent: {bot}")
            with self.subTest(bot=bot):
                self.assertTrue(self._robots(ohne, ok))
        self.assertFalse(self._robots(ok, ok))

    def test_disallow_fuer_eine_maschine_ist_rot(self):
        ok = ("User-agent: Pinterestbot\nAllow: /\nSitemap: https://x/sitemap.xml\n")
        self.assertTrue(self._robots("User-agent: Pinterestbot\nDisallow: /\n"
                                     "Sitemap: https://x/sitemap.xml\n", ok))

    def test_content_signal_search_no_wird_rot(self):
        text = ("User-agent: *\nContent-Signal: search=no, ai-train=no\n"
                "Sitemap: https://x/sitemap.xml\n")
        self.assertTrue(any("Content-Signal" in m for m in self._robots(text, text)))

    def test_sitemap_duplikate_und_fehlende_money_urls(self):
        for bad in (f"<urlset><url><loc>{lp.BASE}/tags/x/</loc></url></urlset>",
                    f"<urlset><url><loc>{lp.BASE}/page/2/</loc></url></urlset>"):
            F: list = []
            lp.check_sitemap(bad, "", F, [])
            with self.subTest(bad=bad[:40]):
                self.assertTrue(F)
        F, S = [], []
        lp.check_sitemap(f"<urlset><url><loc>{lp.BASE}/posts/a/</loc></url></urlset>",
                         f"<urlset><url><loc>{lp.BASE}/posts/a/</loc></url>"
                         f"<url><loc>{lp.BASE}/posts/b/</loc></url></urlset>", F, S)
        self.assertTrue(any("Money-URL" in m for _, m in F))


class LiveSeitencheck(unittest.TestCase):
    """L3/L4: canonical, og:image, Escape im gecachten JSON-LD, Manifest-MIME."""

    def _page(self, live: str, local: str) -> list:
        F: list = []
        lp.check_page(live, local, "/posts/a/", F, [])
        return [m for _, m in F]

    def _fmt(self, can: str, og: str, ld: str) -> str:
        return (f'<html><head><link rel="canonical" href="{can}">'
                f'<meta property="og:image" content="{og}">'
                f'<script type="application/ld+json">{ld}</script></head></html>')

    def test_abweichende_live_werte_werden_gesehen(self):
        local = self._fmt(f"{lp.BASE}/posts/a/", f"{lp.BASE}/c.png",
                          '{"a":1}')
        self.assertTrue(self._page(self._fmt(f"{lp.BASE}/alt/", f"{lp.BASE}/c.png",
                                             '{"a":1}'), local))
        self.assertTrue(self._page(self._fmt(f"{lp.BASE}/posts/a/", "", '{"a":1}'),
                                   local))
        self.assertFalse(self._page(local, local))

    def test_doppeltes_escaping_im_cache_ist_rot(self):
        local = self._fmt(f"{lp.BASE}/posts/a/", f"{lp.BASE}/c.png", '{"a":1}')
        stale = self._fmt(f"{lp.BASE}/posts/a/", f"{lp.BASE}/c.png",
                          '{"@graph":[{\\"a\\":1}]}')
        self.assertTrue(any("escap" in m for m in self._page(stale, local)))
        kaputt = self._fmt(f"{lp.BASE}/posts/a/", f"{lp.BASE}/c.png", '{"a":')
        self.assertTrue(any("JSON" in m for m in self._page(kaputt, local)))

    def test_build_ohne_og_image_loest_keinen_false_positive_aus(self):
        live = self._fmt(f"{lp.BASE}/posts/a/", "", '{"a":1}')
        self.assertFalse(self._page(live, live))


class Ledgerkopplung(unittest.TestCase):
    """Registriert, gemessen, committbar – in beide Richtungen."""

    def test_wache_ist_vertragsregister_und_ledger(self):
        self.assertIn("live_policy_guard.py", gc.GUARDS)
        # Nur wer im Messketten-Vertrag steht, kann die Scorecard und das Issue
        # erreichen – ein Signatureintrag allein wäre noch keine Messung.
        self.assertIn("live-policy", gc.MEASURE_STEPS)
        self.assertIn("live-policy", gc.STEP_SIGNATURES)
        self.assertEqual(gg.STEPS["live-policy"]["report"], "LIVE-POLICY-REPORT.md")

    def test_premium_governance_misst_und_hebt_die_produktion_rot_auf(self):
        yml = open(os.path.join(ROOT, ".github", "workflows", "premium-governance.yml"),
                   encoding="utf-8").read()
        schritte = [s.strip() for s in yml.split("      - name: ")[1:]]
        idx = {n: i for i, (n, s) in enumerate(
            [(s.splitlines()[0].strip('"'), s) for s in schritte])}
        step = schritte[idx["Live-Konsistenz (Cloudflare, CDN-Cache, Auslieferung)"]]
        self.assertIn("live_policy_guard.py --require-live", step)
        self.assertIn("--emit live-policy", step)
        # Der Report ist Lauf-Artefakt, kein Root-Müll: kein git add dafür.
        self.assertNotIn("git add LIVE-POLICY-REPORT.md", yml)
        # Scorecard ist Ansicht und muss nach der Messung laufen (Regel C1)
        self.assertLess(idx["Live-Konsistenz (Cloudflare, CDN-Cache, Auslieferung)"],
                        idx["Chefredakteur-Scorecard"])

    def test_unerreichbarkeit_ist_nur_mit_require_live_rot(self):
        def tot(url):
            return (0, "", "")
        alt = lp.fetch
        try:
            lp.fetch = tot
            hard, soft, live = lp.run(False, public="/nonexistent")
            self.assertFalse(live)
            self.assertEqual([], hard)
            self.assertEqual(1, len(soft))
            hard2, _, live2 = lp.run(True, public="/nonexistent")
            self.assertTrue(live2 is False)
            self.assertEqual(1, len(hard2))
            self.assertEqual("site_unreachable", lp.CODES[hard2[0][0]])
            # `site_unreachable` darf nicht in der Info-Liste stehen – die Wache
            # misst die Site selbst, ihr Ausfall ist der Alarm, nicht das Rauschen.
            self.assertNotIn("site_unreachable", gg.INFO_AMBER)
            self.assertIn("unreachable", gg.INFO_AMBER)
        finally:
            lp.fetch = alt

    def test_report_format_liest_das_ledger(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "LIVE-POLICY-REPORT.md")
            lp.write_report(path, [("L1", "robots.txt live ohne Pinterestbot")], [], True)
            text = open(path, encoding="utf-8").read()
            self.assertIn("## Gesamt-Ampel: **RED**", text)
            self.assertIn("robots_drift", text)
            info = gg.classify("live-policy", text, "", 1, "LIVE-POLICY-REPORT.md")
            self.assertEqual("red", info["level"])
            self.assertTrue(info["actionable"])
            lp.write_report(path, [], [("Netz", "keine Verbindung")], False)
            info2 = gg.classify("live-policy", open(path, encoding="utf-8").read(),
                                "", 0, "x")
            self.assertEqual("green", info2["level"])


class SelbsttestWache(unittest.TestCase):
    def test_selbsttest_gruen_ohne_netz(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "live_policy_guard.py"),
                             "--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
