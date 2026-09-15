"""Regressions-Tests der Content-Reserve-Produktionslinie (Issue #295).

Reparatur 15.09.2026: Der nächtliche Reserve-Lauf war tagelang rot, obwohl
Produktion/Veredelung/Zertifizierung technisch liefen. Die drei Ursachen
werden hier als Verträge festgenagelt:

  1. PUSH-KONFLIKT auf maschinengenerierten Artefakten (Zertifikat,
     Cover-Manifest) darf den Lauf nicht mehr abbrechen ->
     tests/test_git_sync.py (dort synthetisches Remote).
  2. LIVE-KORPUS-ISOLATION: Die Veredelungs-Kette enthält korpusweite
     Heiler; sie dürfen ausschließlich die Pool-Kandidaten verändern.
     Fremd-Änderungen werden bytegenau zurückgestellt, neue Fremd-Dateien
     wandern in Quarantäne.
  3. STAGING-POLITIK: Es wird nur Pool-Content committet – Live-Content
     bleibt liegen (Besitzverhältnis + Konfliktoberfläche).
  4. KONVERGENZ: Der Pool muss das Ziel in derselben Nacht erreichen können
     (begrenzte, zielgerichtete Runden statt eines wirkungslosen Einzelblocks).
  5. FRISCHE: Ein veraltetes Zertifikat ist kein Reife-Nachweis.
  6. HEILER-DECKUNG: Jedes Gate, das über die Reife entscheidet, braucht
     einen Heiler (Struktur → check_length, Meta-Satzende → meta_optimizer).
     Ein Gate ohne Heiler macht den Zielbestand unerreichbar.

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_length as cl            # noqa: E402
import meta_optimizer as mo          # noqa: E402
import reserve_converge as rc        # noqa: E402
import reserve_finisher as rf        # noqa: E402
import reserve_gate as rg            # noqa: E402
import reserve_stage_guard as rsg    # noqa: E402

LIVE_POST = "content/posts/2026-09-01-live/index.md"
POOL_POST = "content/posts/2026-09-15-pool/index.md"


def _git(root: Path, *args):
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                          text=True)


class IsolationTestBase(unittest.TestCase):
    """Synthetisches Repo – nie das Live-Repo, nie das Netz."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        for rel in ("content/posts/2026-09-01-live",
                    "content/posts/2026-09-15-pool",
                    "static/images/covers", "data/audit"):
            (self.repo / rel).mkdir(parents=True, exist_ok=True)
        self.write(LIVE_POST,
                   "---\ntitle: Live\ndate: 2026-09-01T06:00:00Z\n"
                   "draft: false\n---\nLive-Body\n")
        self.write(POOL_POST,
                   "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\n"
                   "draft: true\nreserve: true\n---\nPool-Body\n")
        self.write("data/covers_manifest.json", '{"x": {"title": "alt"}}\n')
        self.write("data/audit/2026-09-15.jsonl", '{"a": 1}\n')
        self.write("static/images/covers/2026-09-01-live.jpg", "BILD-LIVE\n")
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@example.com")
        _git(self.repo, "config", "user.name", "T")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        # Der Wächter arbeitet im übergebenen Repo (Monkeypatch, s. u.)
        self.patches = [
            patch.object(rf, "BLOG_DIR", self.repo),
            patch.object(rf, "QUARANTINE", Path(self.tmp.name) / "quarantäne"),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self, rel):
        return (self.repo / rel).read_text(encoding="utf-8")


class LiveKorpusIsolationTests(IsolationTestBase):
    def test_fremdaenderungen_werden_zurueckgestellt(self):
        allowed = rf.allowed_paths_for([self.repo / "content/posts/"
                                        "2026-09-15-pool" / "index.md"])
        baseline = rf.isolation_baseline(allowed)
        # Sabotage: korpusweite Heiler fassen ALLES an.
        self.write(LIVE_POST,
                   "---\ntitle: Live\ndate: 2026-09-01T06:00:00Z\n"
                   "draft: false\n---\nLIVE GEHEILT\n")
        self.write(POOL_POST,
                   "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\n"
                   "draft: true\nreserve: true\n---\nPOOL VEREDELT\n")
        self.write("static/images/covers/2026-09-01-live.jpg", "NEU GERENDERT\n")
        self.write("static/images/covers/fremd-neu.jpg", "FREMD\n")
        self.write("data/covers_manifest.json", '{"x": {"title": "neu"}}\n')
        self.write("data/audit/2026-09-15.jsonl", '{"a": 1}\n{"b": 2}\n')
        with patch("sys.stdout"):
            eingriffe = rf.isolation_enforce(baseline)
        pfade = {e["pfad"] for e in eingriffe}
        # Zurückgestellt: Live-Post, Live-Cover, neue Fremd-Datei
        self.assertIn(LIVE_POST, pfade)
        self.assertIn("static/images/covers/2026-09-01-live.jpg", pfade)
        self.assertIn("static/images/covers/fremd-neu.jpg", pfade)
        self.assertEqual(self.read(LIVE_POST).endswith("Live-Body\n"), True,
                         "Live-Post muss bytegenau zurückgestellt sein")
        self.assertEqual(self.read("static/images/covers/2026-09-01-live.jpg"),
                         "BILD-LIVE\n")
        self.assertFalse((self.repo / "static/images/covers/fremd-neu.jpg")
                         .exists(), "Fremd-Datei muss in Quarantäne liegen")
        # Erlaubt: Pool-Kandidat, Zertifikat/Manifest, Append-only-Historien
        self.assertNotIn(POOL_POST, pfade)
        self.assertEqual(self.read(POOL_POST).endswith("POOL VEREDELT\n"), True)
        self.assertIn("neu", self.read("data/covers_manifest.json"))
        self.assertIn('{"b": 2}', self.read("data/audit/2026-09-15.jsonl"))

    def test_ohne_fremdaenderung_keine_eingriffe(self):
        allowed = rf.allowed_paths_for([self.repo / POOL_POST])
        baseline = rf.isolation_baseline(allowed)
        self.write(POOL_POST,
                   "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\n"
                   "draft: true\nreserve: true\n---\nPOOL VEREDELT\n")
        with patch("sys.stdout"):
            self.assertEqual(rf.isolation_enforce(baseline), [])

    def test_geloeschte_live_datei_wird_wiederhergestellt(self):
        allowed = rf.allowed_paths_for([self.repo / POOL_POST])
        baseline = rf.isolation_baseline(allowed)
        (self.repo / LIVE_POST).unlink()
        with patch("sys.stdout"):
            eingriffe = rf.isolation_enforce(baseline)
        self.assertIn(LIVE_POST, {e["pfad"] for e in eingriffe})
        self.assertTrue((self.repo / LIVE_POST).exists())


class StagingPolicyTests(IsolationTestBase):
    def test_nur_pool_content_wird_gestagt(self):
        self.write(LIVE_POST,
                   "---\ntitle: Live\ndate: 2026-09-01T06:00:00Z\n"
                   "draft: false\n---\nFREMD\n")
        self.write(POOL_POST,
                   "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\n"
                   "draft: true\nreserve: true\n---\nVEREDELT\n")
        with patch("sys.stdout"):
            bericht = rsg.stage(root=self.repo)
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                                cwd=str(self.repo), capture_output=True,
                                text=True).stdout.split()
        self.assertIn(POOL_POST, staged)
        self.assertNotIn(LIVE_POST, staged)
        self.assertIn(LIVE_POST, bericht["entfernt"])
        # Live-Content bytegenau auf HEAD – kein stiller Fremd-Commit.
        self.assertTrue(self.read(LIVE_POST).endswith("Live-Body\n"))

    def test_sabotage_selbsttests_bleiben_gruen(self):
        with patch("sys.stdout"):
            self.assertEqual(rsg.run_selftest(), 0)
            self.assertEqual(rf.selftest(), 0)


class KonvergenzTests(unittest.TestCase):
    def test_selftest_gruen(self):
        with patch("sys.stdout"):
            self.assertEqual(rc.run_selftest(), 0)

    def test_ziel_erreicht_loest_keine_produktion_aus(self):
        rufe = []
        res = rc.converge(runner=lambda *a, **kw: rufe.append(a) or 0,
                          state_reader=lambda: {"target": 6, "ready": 6,
                                                "pool_size": 6, "exists": True},
                          log=lambda *_: None)
        self.assertTrue(res["ok"])
        self.assertEqual(rufe, [])

    def test_kein_fortschritt_bricht_nach_einer_runde_ab(self):
        rufe = []
        zustand = {"target": 6, "ready": 2, "pool_size": 2, "exists": True}
        res = rc.converge(runner=lambda *a, **kw: rufe.append(a) or 0,
                          state_reader=lambda: dict(zustand),
                          log=lambda *_: None)
        self.assertFalse(res["ok"])
        self.assertEqual(res["abbruch"], "kein-fortschritt")
        self.assertEqual(len(rufe), 3, "genau eine Runde (3 Kommandos)")

    def test_batch_folgt_dem_fehlbestand_und_ist_gedeckelt(self):
        envs = []

        def runner(cmd, env_extra=None, timeout=0):
            # nur die Produktions-Aufrufe tragen die Konvergenz-Env
            if any("engine_generate" in str(c) for c in cmd):
                envs.append(env_extra or {})
            return 0

        fortschritt = {"n": 0}

        def reader():
            fortschritt["n"] += 1
            return {"target": 12, "ready": fortschritt["n"] - 1,
                    "pool_size": fortschritt["n"], "exists": True}

        rc.converge(runner=runner, state_reader=reader, max_runden=3,
                    log=lambda *_: None)
        self.assertEqual([e["RESERVE_TOPUP_BATCH"] for e in envs],
                         ["4", "4", "4"])
        self.assertEqual([e["RESERVE_FORCE_TOPUP"] for e in envs],
                         ["1", "1", "1"],
                         "Der In-Flight-Schutz muss im Nachschub aufgehoben sein")

    def test_zeitbudget_stoppt_vor_dem_job_timeout(self):
        """#295: Eine langsame Nacht darf den 90-Minuten-Job nicht sprengen –
        sonst killt GitHub den Job samt „sichern“ und End-Gate (roter Lauf
        OHNE Diagnose und ohne gepushten Pool-Stand)."""
        rufe = []
        uhr = {"t": 0.0}
        runde = {"n": 0}

        def runner(cmd, env_extra=None, timeout=0):
            rufe.append(timeout)
            uhr["t"] += 400.0
            return 0

        def reader():
            runde["n"] += 1
            return {"target": 6, "ready": runde["n"],
                    "pool_size": runde["n"] + 1, "exists": True}

        res = rc.converge(runner=runner, state_reader=reader, max_runden=3,
                          max_sekunden=900, now=lambda: uhr["t"] + 1.0,
                          log=lambda *_: None)
        self.assertEqual(res["abbruch"], "zeit-budget")
        self.assertEqual(res["runden"], 1, "nur die erste Runde lief")
        self.assertEqual(len(rufe), 3, "drei Schritte, dann kein weiterer")
        self.assertTrue(all(0 < t <= 900 for t in rufe),
                        f"Restbudget muss als Schritt-Timeout gelten: {rufe}")


class GateFrischeTests(unittest.TestCase):
    def _cert(self, tmp, payload):
        path = Path(tmp) / "reserve-readiness.json"
        path.write_text(json.dumps(payload, ensure_ascii=False),
                        encoding="utf-8")
        return path

    def test_veraltetes_zertifikat_ist_kein_nachweis(self):
        now = dt.datetime.now(dt.timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            cert = self._cert(tmp, {
                "target": 6, "ready": 6,
                "generated_at": (now - dt.timedelta(hours=72)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"),
                "candidates": [{"slug": f"k{i}", "ready": True}
                               for i in range(6)],
            })
            frisch, meldung = rg.freshness(cert)
            self.assertFalse(frisch)
            self.assertIn("veraltet", meldung)

    def test_frisches_zertifikat_traegt(self):
        now = dt.datetime.now(dt.timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            cert = self._cert(tmp, {
                "target": 6, "ready": 6,
                "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "candidates": [{"slug": f"k{i}", "ready": True}
                               for i in range(6)],
            })
            frisch, _ = rg.freshness(cert)
            self.assertTrue(frisch)
            ready, target, _ = rg.evaluate(cert)
            self.assertEqual((ready, target), (6, 6))


class LaengenHeilungTests(unittest.TestCase):
    """#295: Der Sammellauf übersprang Entwürfe – Pool-Kandidaten wurden
    deshalb nie verlängert (Struktur-Score 0.70 bei < 1200 Wörtern)."""

    def test_entwuerfe_werden_gescopt_mitgeprueft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content" / "posts" / "2026-09-15-pool"
            root.mkdir(parents=True)
            index = root / "index.md"
            index.write_text(
                "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\n"
                "draft: true\nreserve: true\n---\n" + "Wort " * 50,
                encoding="utf-8")
            # Standardverhalten (Korpus): Entwürfe bleiben unsichtbar
            self.assertEqual(cl.collect(str(index)), [])
            # Datei-bezirkelt + Entwürfe erlaubt: Kandidat wird gesehen
            arts = cl.collect(str(index), include_drafts=True)
            self.assertEqual(len(arts), 1)
            self.assertEqual(arts[0]["slug"], "2026-09-15-pool")
            self.assertEqual(arts[0]["status"], "zu-kurz")

    def test_korpuslauf_ohne_flag_bleibt_unveraendert(self):
        # Regressionsschutz: der Live-Korpuslauf darf durch die neue Signatur
        # keine Entwürfe einsammeln (Aufruf ohne Argumente).
        self.assertEqual(cl.collect.__defaults__, (None, False))


class MetaSatzendeHeilungTests(unittest.TestCase):
    """#295 (zweiter Befund derselben Klasse): Das Meta-Gate
    (quality_score: `desc[-1] in ".!?…"`, sonst −0,3) hatte KEINEN Heiler –
    meta_optimizer prüfte nur die Länge. Ein Pool-Kandidat mit korrekt langer,
    aber punktloser Description hing deshalb dauerhaft bei meta 0.70 unter der
    Publish-Schwelle 0.85 (genau der Zustand, in dem der harte End-Gate jede
    Nacht „Stock shortage“ meldete und den Pool nie auf RESERVE_TARGET kam).
    """

    DESC_OHNE_PUNKT = ("Erfahre, wie du im Spätsommer deine Gasrechnung senken "
                       "kannst. Mit diesen Tipps startest du vorbereitet in den "
                       "Herbst und sparst bei der Heizung bares Geld")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.post = Path(self.tmp.name) / "2026-09-15-kandidat" / "index.md"
        self.post.parent.mkdir(parents=True)

    def _write(self, desc: str) -> None:
        self.post.write_text(
            "---\n"
            'title: "Gasrechnung senken: Dein Strategieplan im Spätsommer"\n'
            f"description: {desc}\n"
            "date: 2026-09-15T06:00:00Z\n"
            "draft: true\n"
            "reserve: true\n"
            "kurzantwort: \"Kurz gesagt: Vor dem Herbst prüfen und vergleichen.\"\n"
            'keywords: ["Gasrechnung senken", "Heizkosten sparen", "Herbst"]\n'
            "---\n\nText.\n",
            encoding="utf-8")

    def _article(self) -> dict:
        return mo.load_articles([str(self.post)])[0]

    def _description(self) -> str:
        return self._article()["description"]

    def test_audit_erkennt_fehlendes_satzende(self):
        self._write(self.DESC_OHNE_PUNKT)
        issues = mo.audit(self._article())["issues"]
        self.assertIn("Description ohne Satzende (Punkt/!/?/… fehlt)", issues)
        # Regressionsschutz: gültige Satzenden bleiben beanstandungsfrei.
        for ok in (".", "!", "?", "…"):
            self._write(f'"{self.DESC_OHNE_PUNKT}{ok}"')
            self._assert_no_satzende_issue()

    def _assert_no_satzende_issue(self):
        issues = mo.audit(self._article())["issues"]
        self.assertNotIn("Description ohne Satzende (Punkt/!/?/… fehlt)", issues)

    def test_fix_ergaenzt_satzende_deterministisch(self):
        # Ohne KI, ohne Netz: der Heiler muss das Gate-Hindernis selbst lösen.
        self._write(self.DESC_OHNE_PUNKT)
        self.assertTrue(mo.fix_meta(self._article(), use_ai=False))
        self.assertTrue(self._description().endswith("."))
        # Der Heiler und das Gate stimmen jetzt überein (SSOT-Vertrag).
        import quality_score as qs
        self.assertEqual(qs.score_article(str(self.post))["parts"]["meta"], 1.0)
        # Satzende-Marker für das Meta-Gate ist erfüllt (Ende oder Zitat-Ende).
        self.assertTrue(mo.desc_has_sentence_end(self._description()))

    def test_fix_ist_idempotent(self):
        self._write(f'"{self.DESC_OHNE_PUNKT}."')
        self.assertFalse(mo.fix_meta(self._article(), use_ai=False),
                         "Ein geheilter Kandidat darf nicht erneut geändert werden")

    def test_langenlimit_wird_nicht_ueberschritten(self):
        lang = "Wort " * 34  # 170 Zeichen, kein Satzende
        self._write(lang.strip())
        mo.fix_meta(self._article(), use_ai=False)
        desc = self._description()
        self.assertLessEqual(len(desc), mo.DESC_MAX)
        self.assertTrue(desc.endswith("."))


if __name__ == "__main__":
    unittest.main()
