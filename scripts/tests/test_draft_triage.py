#!/usr/bin/env python3
"""Regressionstest: draft_triage (Empfehlung 6 des Premium-Audits 12.09.2026).

Der Anlass war kein Redaktions-, sondern ein Werkzeugfehler: acht Artikel hatten
eine an den ersten Absatz geklebte Frontmatter-Grenze (`---Text`). Hugo baute
den Text, die Regex-Wachen des Repos (check_uniqueness, length_guard,
link_density_guard) sahen ihn als Frontmatter und prüften ihn NICHT – grün,
obwohl blind. Die Triage meldet diese Klasse als Hindernis; dieser Test hält
beides fest: dass die Klasse auffällt und dass sie nicht heilt, indem die Triage
stillschweigend Content umschreibt.
"""
from __future__ import annotations

import datetime
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
HEUTE = datetime.date(2026, 9, 12)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


dt = _load("draft_triage", os.path.join(SCRIPTS, "draft_triage.py"))
gc = _load("governance_contract", os.path.join(SCRIPTS, "governance_contract.py"))

FUELL = "".join(f"\n## Abschnitt {i}\n\nSpartipp mit Zahlen, belegt und gerechnet.\n"
                for i in range(6)) * 60
FM = ("title: Gastarif sichern im Herbst\n"
      "date: {datum}\ndraft: true\ndescription: So sicherst du einen fairen Gastarif\n"
      "kurzantwort: Tarif vergleichen, Preisgarantie prüfen\n"
      "cover:\n  image: images/covers/g.jpg\n")
BODY = ("Werbung | Der Tarif entscheidet. [Strom](/posts/x/) und "
        "[Ratgeber](/pillar/y/) und [Gas](/go/gas/).\n")


class Grundgeruest(unittest.TestCase):
    """Ein Gerüst aus Scripts/Statik/Registrierung, damit jede Klasse prüfbar ist."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="triage-test-")
        self.root = os.path.join(self.tmp.name, "repo")
        for sub in ("scripts", "static/images/covers", "content/posts"):
            os.makedirs(os.path.join(self.root, sub), exist_ok=True)
        with open(os.path.join(self.root, "scripts", "check24_links.yaml"), "w") as f:
            f.write("links:\n  gas: https://a.check24.net/misc/click.php?pid=1&deep=g\n"
                    "  strom: https://a.check24.net/misc/click.php?pid=1&deep=s\n")
        open(os.path.join(self.root, "static", "images", "covers", "g.jpg"), "w").write("x")

    def tearDown(self):
        self.tmp.cleanup()

    def _artikel(self, slug: str, text: str, alt_tage: int = 2) -> str:
        d = os.path.join(self.root, "content", "posts", slug)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "index.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        stamp = (datetime.datetime.now() - datetime.timedelta(days=alt_tage)).timestamp()
        os.utime(p, (stamp, stamp))
        return p

    def _reif(self, datum: str = "2026-09-10") -> str:
        return ("---\n" + FM.format(datum=datum) + "---\n" + BODY + FUELL)

    def test_reifer_entwurf_ist_sofort_raus(self):
        r = dt.classify(self._artikel("2026-09-10-gastarif-sichern", self._reif(), alt_tage=2),
                        self.root, HEUTE, 21)
        self.assertEqual("REIF", r["zustand"], r["blocker"])
        self.assertEqual([], r["blocker"])

    def test_verfall_nur_ohne_hindernis(self):
        r = dt.classify(self._artikel("2026-09-10-gastarif-sichern", self._reif(), alt_tage=40),
                        self.root, HEUTE, 21)
        self.assertEqual("VERWAIST", r["zustand"])
        # derselbe Entwurf, aber ohne Cover -> BLOCKIERT, kein Verfalls-Alarm
        ohne = self._reif().replace("cover:\n  image: images/covers/g.jpg\n", "")
        r2 = dt.classify(self._artikel("2026-08-11-ohne-cover", ohne, alt_tage=40),
                         self.root, HEUTE, 21)
        self.assertEqual("BLOCKIERT", r2["zustand"])
        self.assertTrue(any(b.startswith("cover:") for b in r2["blocker"]))

    def test_geklebte_frontmatter_grenze_ist_hindernis(self):
        # Der 12.09.-Fall: `---` + Text in einer Zeile.
        text = "---\n" + FM.format(datum="2026-09-09") + "---" + "Der erste Absatz klebt.\n" + FUELL
        r = dt.classify(self._artikel("2026-09-09-geklebt", text), self.root, HEUTE, 21)
        self.assertTrue(any(b.startswith("fm-grenze") for b in r["blocker"]), r["blocker"])

    def test_zukunftsdatum_ist_warten_nicht_vergammeln(self):
        r = dt.classify(self._artikel("2026-12-24-weihnachtsgeld",
                                      self._reif(datum="2026-12-24T09:00:00Z"), alt_tage=4),
                        self.root, HEUTE, 21)
        self.assertEqual("WARTET", r["zustand"], r["blocker"])
        self.assertEqual("2026-12-24", r["wartet_bis"])
        # Quell-Defekt in der Warteschleife bleibt trotzdem ein Hindernis
        kaputt = ("---\n" + FM.format(datum="2026-12-24") + "---" + "Klebt.\n" + FUELL)
        r2 = dt.classify(self._artikel("2026-12-24-mit-defekt", kaputt, alt_tage=4),
                         self.root, HEUTE, 21)
        self.assertEqual("BLOCKIERT", r2["zustand"])

    def test_go_route_ohne_registrierung_und_ohne_werbekennzeichnung(self):
        text = ("---\n" + FM.format(datum="2026-09-08") + "---\n"
                "Der Tarif entscheidet ohne Hinweis. [a](/posts/x/) [b](/pillar/y/) "
                "[c](/go/nicht-vorhanden/).\n" + FUELL)
        r = dt.classify(self._artikel("2026-09-08-locher", text), self.root, HEUTE, 21)
        self.assertTrue(any(b.startswith("go-route") for b in r["blocker"]), r["blocker"])
        self.assertTrue(any(b.startswith("werbekennzeichnung") for b in r["blocker"]), r["blocker"])

    def test_auffrischung_ist_hinweis_rueckdatierung_hindernis(self):
        hoch = self._reif(datum=HEUTE.isoformat())
        r = dt.classify(self._artikel("2026-08-16-auffrischung", hoch, alt_tage=3),
                        self.root, HEUTE, 21)
        self.assertEqual("REIF", r["zustand"], r["blocker"])
        self.assertTrue(any(h.startswith("datum: Verzeichnis") for h in r["hinweise"]))
        runter = self._reif(datum="2026-07-01")
        r2 = dt.classify(self._artikel("2026-09-05-rueckstaendig", runter, alt_tage=3),
                         self.root, HEUTE, 21)
        self.assertTrue(any(b.startswith("datum: Verzeichnis") for b in r2["blocker"]))

    def test_lastmod_vor_publishdatum_wird_gemeldet(self):
        text = ("---\n" + FM.format(datum="2026-09-11T09:00:00Z")
                + "lastmod: 2026-09-02\n" + "---\n" + BODY + FUELL)
        r = dt.classify(self._artikel("2026-09-11-alt-lastmod", text), self.root, HEUTE, 21)
        self.assertTrue(any(b.startswith("lastmod:") for b in r["blocker"]), r["blocker"])


class BestandUndVertrag(unittest.TestCase):
    def test_selbsttest_der_wache(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "draft_triage.py"),
                             "--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_triage_der_echten_reserve_liest_alle_entwuerfe(self):
        rows = dt.collect(ROOT, HEUTE, 21)
        drafts = [p for p in subprocess.run(
            ["grep", "-rl", "^draft: true", "content/posts"], cwd=ROOT,
            capture_output=True, text=True).stdout.split()]
        self.assertEqual(len(drafts), len(rows),
                         f"{len(drafts)} Entwürfe im Baum, {len(rows)} in der Triage – "
                         "die Triage übersieht welche")
        # keine echte Datei wird verändert (die Wache liest nur)
        self.assertTrue(all(r["pfad"].startswith("content/") for r in rows))

    def test_verdrahtung_in_gemaess_vertrag(self):
        self.assertIn("draft_triage.py", gc.GUARDS)
        yml = open(os.path.join(ROOT, ".github", "workflows", "content-reserve.yml"),
                   encoding="utf-8").read()
        self.assertIn("draft_triage.py --selftest", yml)
        self.assertIn("draft_triage.py --check-decisions", yml)
        self.assertIn("draft_triage.py --md", yml)
        # Und sie darf den Root nicht zumüllen: kein Report-Schreibpfad im Workflow
        self.assertNotIn("--report", yml)
        self.assertNotIn("DRAFT-TRIAGE-REPORT", yml)
        self.assertIn("draft_triage", open(os.path.join(ROOT, ".github", "workflows",
                                      "link-check.yml"), encoding="utf-8").read())

    def test_selbsttest_beruehrt_nie_den_echten_bestand(self):
        with tempfile.TemporaryDirectory() as td:
            fake = os.path.join(td, "keEin-repo")
            rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "draft_triage.py"),
                                 "--check-decisions", "--root", fake],
                                cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(0, rc.returncode)
            self.assertIn("kein Git-Worktree", rc.stdout + rc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
