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

Nachzug 22.09.2026 (#349, Run 35706157938): Befund 6 war nur für zwei Gates
handverdrahtet – der Intent-Wächter (publish_gate-Kriterium 5, IW0–IW9) lief
in der Reserve-Kette NICHT mit, obwohl sein Heil-Aufruf `--heal --file <pfad>`
genau dafür gebaut ist. Ein Kandidat mit „IW8 – Anker nennt kein Angebot“ war
damit strukturell unreif (5/6, End-Gate rot) – der Fund wurde sieben Minuten
später vom täglichen Affiliate-Lauf byte-identisch geheilt. Dazu zwei Befunde
aus demselben Lauf, ebenfalls hier festgenagelt:

  7. LAUF-ZÄHLUNG: Quarantäne zählt LÄUFE, nicht Zertifizierungen – ein
     einziger Nachtlauf zertifiziert mehrfach (Stufe 3 + Konvergenz-Runden).
     Vorher reichte EINE Nacht, um einen heilbaren Kandidaten auszumustern.
  8. NICHTS GEHT VERLOREN: Ausgemusterte Entwürfe (`reserve_blocked`) sind
     Reserve-Eigentum und werden gestagt; der Quarantäne-Zähler ist
     versioniert. Am 22.09. verschwand ein quarantänisierter Kandidat spurlos,
     weil die Staging-Politik ihn für fremden Content hielt.
"""
import contextlib
import datetime as dt
import os
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_length as cl            # noqa: E402
import engine_generate as eg         # noqa: E402
import meta_optimizer as mo           # noqa: E402
import reserve_pool as rp             # noqa: E402
import reserve_converge as rc        # noqa: E402
import reserve_finisher as rf        # noqa: E402
import reserve_gate as rg            # noqa: E402
import reserve_economy as re_        # noqa: E402
import reserve_healer_coverage as rhc  # noqa: E402
import reserve_quarantine as rq      # noqa: E402
import reserve_readiness as rr       # noqa: E402
import reserve_stage_guard as rsg    # noqa: E402


# Die Reserve-Linie führt zwei GEDÄCHTNISSE (Themen-Cooldowns, Pool-Besitz).
# Kein Test darf sie ins echte Repository schreiben: Ein Thema, das hier
# „scheitert", wäre sonst für die nächste echte Nacht drei Tage gesperrt.
_LEDGER_TMP = None


def setUpModule():  # noqa: N802 – unittest-API
    global _LEDGER_TMP
    _LEDGER_TMP = tempfile.TemporaryDirectory()
    os.environ["RESERVE_TOPIC_LEDGER"] = str(
        Path(_LEDGER_TMP.name) / "topics.json")
    os.environ["RESERVE_CUSTODY_LEDGER"] = str(
        Path(_LEDGER_TMP.name) / "custody.json")


def tearDownModule():  # noqa: N802 – unittest-API
    for key in ("RESERVE_TOPIC_LEDGER", "RESERVE_CUSTODY_LEDGER"):
        os.environ.pop(key, None)
    if _LEDGER_TMP is not None:
        _LEDGER_TMP.cleanup()

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
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

    def test_reserve_topup_wechselt_nach_gescheiterter_ki_generierung_thema(self):
        topics = [{"title": "Thema A"}, {"title": "Thema B"}]
        used_topics = set()
        versuchte_themen = []
        vorstufen_flags = []

        def fail(topic, *_args, **kwargs):
            versuchte_themen.append(topic["title"])
            vorstufen_flags.append(kwargs.get("reserve_vorstufe"))
            return None, "Profi-Gate abgelehnt"

        with patch.object(rp, "reserve_drafts", return_value=[]), \
                patch.object(eg.g, "topic_already_covered", return_value=False), \
                patch.object(eg, "_pool_conflicts", return_value=False), \
                patch.object(eg, "_weighted_choose", side_effect=lambda free, _weights: free[0]), \
                patch.object(eg, "try_generate", side_effect=fail), \
                patch.object(Path, "read_text", side_effect=OSError("kein Zertifikat")), \
                patch("builtins.print"):
            for _ in range(2):
                self.assertEqual(
                    eg._reserve_topup(topics, "test", set(), used_topics), 0)

        self.assertCountEqual(versuchte_themen, ["Thema A", "Thema B"])
        self.assertEqual(used_topics, {id(topics[0]), id(topics[1])})
        self.assertTrue(vorstufen_flags and all(vorstufen_flags),
                        "nur die Reserve muss die belegte Werkbank-Vorstufe nutzen")

    def test_reserve_vorstufe_nimmt_nur_belegt_heilbare_befunde_an(self):
        """#436: Kurze, substanzielle Antworten gehen zum Längenheiler.

        Live bleibt streng; hier wird lediglich der Vertrag der nachfolgenden
        Reserve-Werkbank geprüft.
        """
        body = ("## Abschnitt eins\n" + "Wort " * 150 +
                "\n## Abschnitt zwei\n" + "Wort " * 150 +
                "\n## Abschnitt drei\n" + "Wort " * 150 +
                "\n## Häufige Fragen\n" + "Wort " * 120)
        ok, heiler = eg._reserve_vorstufe_ok(body, [
            "nur 574 Wörter / 4200 Zeichen (Premium: ≥1.400 Wörter und ≥10.000 Zeichen)",
            "Keyword „ETF-Sparplan“ fehlt in H2/H3 (Premium #303)",
        ])
        self.assertTrue(ok)
        self.assertEqual(heiler, ["Keyword", "Länge"])
        # Fehlendes Pflichtmodul hat keinen zugesagten Geburts-Heiler.
        self.assertFalse(eg._reserve_vorstufe_ok(
            body, ["kein „Das Wichtigste in Kürze“-Modul (RS1)"])[0])
        # Ein nahezu leerer Text darf auch mit reinem Längenbefund nicht rein.
        self.assertFalse(eg._reserve_vorstufe_ok(
            "## A\nKurz.\n## B\nKurz.\n## C\nKurz.\n## D\nKurz.",
            ["nur 12 Wörter / 50 Zeichen (Premium: ≥1.400 Wörter und ≥10.000 Zeichen)"])[0])

    def test_live_generierung_bleibt_ohne_vorstufe_streng(self):
        """Die Werkbank-Ausnahme darf nicht in publish_one_article lecken."""
        body = ("## A\n" + "Wort " * 150 + "\n## B\n" + "Wort " * 150 +
                "\n## C\n" + "Wort " * 150 + "\n## D\n" + "Wort " * 120)
        raw = "TITLE: Test: Solider Rohtext\nDESCRIPTION: Test.\n" + body
        problems = ["nur 574 Wörter / 4200 Zeichen (Premium: ≥1.400 Wörter und ≥10.000 Zeichen)"]
        with patch.dict(os.environ, {"GROQ_API_KEY": "test", "GEMINI_API_KEY": ""}), \
                patch.object(eg.random, "shuffle", lambda _x: None), \
                patch.object(eg.g, "generate_article_text", return_value=(raw, "Groq")), \
                patch.object(eg.g, "profi_quality_ok", return_value=(False, problems)), \
                patch("builtins.print"):
            streng, _ = eg.try_generate({"title": "Test"}, [], None, set(),
                                        max_attempts=1)
            vorstufe, info = eg.try_generate(
                {"title": "Test"}, [], None, set(), max_attempts=1,
                reserve_vorstufe=True)
        self.assertIsNone(streng)
        self.assertIsNotNone(vorstufe)
        self.assertIn("VORSTUFE", info)

    def test_reserve_batch_faehrt_nach_einem_themenfehler_fort(self):
        used_topics = set()
        calls = []

        def fake_topup(_topics, _quelle, _titles, attempted, **_kwargs):
            calls.append(len(calls))
            if len(calls) > 4:
                return 0
            attempted.add(len(calls))
            return 0 if len(calls) == 1 else 1

        with patch.object(eg, "_reserve_topup", side_effect=fake_topup):
            produced = eg._reserve_topup_batch([], "test", set(), used_topics, 4)

        self.assertEqual(produced, 3)
        self.assertEqual(len(calls), 4)

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


class ProviderVertragTests(unittest.TestCase):
    """#436: Lange Artikel brauchen einen expliziten Gemini-Ausgabevertrag."""

    def test_gemini_hat_output_budget_und_verliert_keine_text_parts(self):
        gesehen = {}

        def fake_http(_url, data=None, headers=None, **_kwargs):
            gesehen["body"] = json.loads(data.decode("utf-8"))
            gesehen["headers"] = headers
            return {"candidates": [{"content": {"parts": [
                {"text": "Teil A"}, {"text": " + Teil B"},
            ]}}]}

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
                patch.object(eg.g, "http_json", side_effect=fake_http):
            text = eg.g.call_gemini("Langer Premium-Artikel")
        self.assertEqual(text, "Teil A + Teil B")
        cfg = gesehen["body"]["generationConfig"]
        self.assertEqual(cfg["maxOutputTokens"], 8192)
        self.assertGreater(cfg["temperature"], 0)

    def test_gemini_ohne_candidate_ist_ehrlich_leer(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
                patch.object(eg.g, "http_json", return_value={"candidates": []}):
            self.assertIsNone(eg.g.call_gemini("Test"))


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


class CtaHeilungTests(unittest.TestCase):
    """Nachzug #295 (Run 34967470666): eine CTA über zwei Zeilen.

    Der reale Befund war keine „CTA ohne Link“, sondern eine CTA, deren Link
    in der FOLGEZEILE stand. Das Gate prüft zeilenweise (AI1) und lehnte den
    Kandidaten ab; heilen durfte es im STRICT-DRY-RUN nicht, und die Wache sah
    nur Live-Artikel – der Pool-Kandidat (bewusst Entwurf) blieb dauerhaft
    unreif: 5/6, End-Gate rot.
    """

    KAPUTT = ("> \U0001f4b6 **Spar\u2011Tipp zwischendurch:** Faire Konditionen "
              "findest du online in wenigen Minuten \u2013\n"
              "> [**Vergleichen & sparen**](/go/allgemein/)")
    INTAKT = ("> \U0001f4b6 **Spar-Tipp zwischendurch:** faire Konditionen gibt "
              "es online in Minuten: [**Vergleichen & sparen**](/go/allgemein/)")

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import affiliate_integrity_gate as aig
        self.aig = aig
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "content" / "posts"

    def _entwurf(self, slug: str, body: str) -> Path:
        d = self.posts / slug
        d.mkdir(parents=True)
        (d / "index.md").write_text(
            "---\ntitle: \"T\"\npillar: \"frugalismus\"\ndraft: true\n"
            "reserve: true\n---\n\nIntro.\n\n" + body + "\n\nSchluss.\n",
            encoding="utf-8")
        return d / "index.md"

    def test_zweizeilige_cta_wird_geheilt_ohne_waise(self):
        index = self._entwurf("2026-09-15-doppel", self.KAPUTT + "\n\n"
                              + self.INTAKT)
        res = self.aig.heal_file(index, self.aig.load_registry())
        self.assertTrue(res["healed"], res)
        self.assertFalse(res["problems"], res)
        text = index.read_text(encoding="utf-8")
        self.assertNotIn("Spar\u2011Tipp", text,
                         "verstümmelte CTA muss weg sein")
        self.assertEqual(text.count("[**Vergleichen & sparen**](/go/allgemein/)"),
                         1, "die Link-Zeile darf nicht als Waise bleiben")
        self.assertNotIn("\n> [", text,
                         "keine Blockquote-Zeile darf mit einem nackten "
                         "Link beginnen")

    def test_einzelne_zweizeilige_cta_behaelt_den_link(self):
        """Ohne intakte Schwester muss der Link ERHALTEN bleiben."""
        index = self._entwurf("2026-09-15-solo", self.KAPUTT)
        res = self.aig.heal_file(index, self.aig.load_registry())
        self.assertFalse(res["problems"], res)
        text = index.read_text(encoding="utf-8")
        self.assertIn("/go/allgemein/", text,
                      "Affiliate-Link darf nicht verloren gehen")
        self.assertTrue(self.aig.MD_LINK_RE.search(
            [l for l in text.splitlines() if "Spar-Tipp" in l
             or "Spar\u2011Tipp" in l][0]),
            "nach der Heilung muss der Link IN der CTA-Zeile stehen")

    def test_heilung_ist_idempotent_und_dateibegrenzt(self):
        index = self._entwurf("2026-09-15-doppel", self.KAPUTT + "\n\n"
                              + self.INTAKT)
        andere = self._entwurf("2026-09-01-live",
                               "💡 **Schnell-Tipp von FranksFinanzcheck:** Die "
                               "besten Tarife: [**Vergleich**](/go/strom/)")
        vor = andere.read_text(encoding="utf-8")
        self.aig.heal_file(index, self.aig.load_registry())
        danach = index.read_text(encoding="utf-8")
        self.assertFalse(self.aig.heal_file(index, self.aig.load_registry())["gefunden"],
                         "zweiter Lauf darf nichts mehr ändern")
        self.assertEqual(index.read_text(encoding="utf-8"), danach)
        self.assertEqual(andere.read_text(encoding="utf-8"), vor,
                         "datei-bezirkelte Heilung darf nichts anderes anfassen")

    def test_heiler_ist_in_der_reserve_kette_verdrahtet(self):
        """Heiler-Deckung: Das Gate, das ablehnt, braucht einen Heiler."""
        cta_schritte = [e for e in rf.HEALER_CHAIN
                        if e[0] == "affiliate_integrity_gate.py"]
        self.assertTrue(cta_schritte,
                        "affiliate_integrity_gate.py fehlt in der Heiler-Kette")
        self.assertTrue(all("--heal" in e[1] and e[2] == "file"
                            for e in cta_schritte),
                        "CTA-Heilung muss datei-bezirkelt laufen (nie korpusweit)")
        self.assertGreaterEqual(len(cta_schritte), 2,
                                "nach jedem KI-Schritt und vor der "
                                "Zertifizierung heilen")


class QuarantaeneTests(unittest.TestCase):
    """Nachzug #295: Ein Dauer-Blocker darf den Zielbestand nicht erpressen."""

    FUND = ("Affiliate-Link-Integrität nicht bestanden: Kein vollständiger "
            "Markdown-Link in CTA-Zeile ('Spar-Tipp zwischendurch')")

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_quarantine as rq
        import reserve_pool as rp
        self.rq, self.rp = rq, rp
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "content" / "posts"
        self.state = Path(self.tmp.name) / "reserve-quarantine.json"
        d = self.posts / "2026-09-15-block"
        d.mkdir(parents=True)
        (d / "index.md").write_text(
            "---\ntitle: \"Block\"\ndraft: true\nreserve: true\n---\n\nText.\n",
            encoding="utf-8")

    def test_pool_verlaesst_den_zaehler_nach_schwelle(self):
        rows = [{"slug": "2026-09-15-block", "ready": False, "reason": self.FUND}]
        self.assertEqual(
            self.rq.record(rows, self.state, self.posts, run_key="run:1"), [])
        self.assertTrue(self.rp.reserve_drafts(self.posts),
                        "nach dem ersten Fund muss der Kandidat im Pool bleiben")
        blocked = self.rq.record(rows, self.state, self.posts,
                                 run_key="run:2")
        self.assertEqual([b["slug"] for b in blocked], ["2026-09-15-block"])
        self.assertEqual(self.rp.reserve_drafts(self.posts), [],
                         "ausgemusterter Kandidat darf nicht mehr im Pool zählen")

    def test_mehrere_zertifizierungen_eines_laufs_zaehlen_einmal(self):
        """#349: Eine Nacht zertifiziert mehrfach (Stufe 3 + Konvergenz)."""
        rows = [{"slug": "2026-09-15-block", "ready": False, "reason": self.FUND}]
        for _ in range(3):          # derselbe Workflow-Lauf
            self.assertEqual(
                self.rq.record(rows, self.state, self.posts, run_key="run:1"),
                [], "derselbe Lauf darf nicht mehrfach zählen")
        state = self.rq.load_state(self.state)
        self.assertEqual(state["2026-09-15-block"]["hits"], 1)
        self.assertIn("reserve: true",
                      (self.posts / "2026-09-15-block" / "index.md")
                      .read_text(encoding="utf-8"))
        # Zweiter Lauf mit demselben Fund -> Schwelle erreicht, Quarantäne.
        blocked = self.rq.record(rows, self.state, self.posts, run_key="run:2")
        self.assertEqual([b["slug"] for b in blocked], ["2026-09-15-block"])

    def test_lauf_kennung_kommt_aus_der_umgebung(self):
        import os
        alt = os.environ.get("GITHUB_RUN_ID")
        try:
            os.environ["GITHUB_RUN_ID"] = "35706157938"
            self.assertEqual(self.rq.lauf_kennung(), "run:35706157938")
            os.environ.pop("GITHUB_RUN_ID", None)
            self.assertTrue(self.rq.lauf_kennung().startswith("lokal:"))
        finally:
            if alt is None:
                os.environ.pop("GITHUB_RUN_ID", None)
            else:
                os.environ["GITHUB_RUN_ID"] = alt

    def test_werkzeugfehler_zaehlen_nicht(self):
        rows = [{"slug": "2026-09-15-block", "ready": False,
                 "reason": "Gate-Ausnahme: hugo timeout"}]
        self.rq.record(rows, self.state, self.posts, run_key="run:1")
        self.assertFalse(self.rq.record(rows, self.state, self.posts,
                                        run_key="run:2"))
        self.assertIn("reserve: true",
                      (self.posts / "2026-09-15-block" / "index.md")
                      .read_text(encoding="utf-8"))

    def test_ausgemusterter_entwurf_ist_reserve_eigentum(self):
        """#349: Der Entwurf bleibt im Bestand – und muss deshalb gestagt werden.

        Am 22.09.2026 verschwand `2026-09-22-50-30-20-im-test-…` spurlos:
        Quarantäne strich die reserve-Fahne, die Staging-Politik hielt die
        Datei danach für fremden Content, sie wurde nie committet.
        """
        self.assertEqual(
            self.rq.record([{"slug": "2026-09-15-block", "ready": False,
                             "reason": self.FUND}], self.state, self.posts,
                           run_key="run:1"), [])
        self.assertEqual(
            [b["slug"] for b in self.rq.record(
                [{"slug": "2026-09-15-block", "ready": False,
                  "reason": self.FUND}], self.state, self.posts,
                run_key="run:2")], ["2026-09-15-block"])
        index = self.posts / "2026-09-15-block" / "index.md"
        self.assertIn("reserve_blocked:", index.read_text(encoding="utf-8"))
        self.assertTrue(rsg.is_reserve_owned(index),
                        "ausgemusterter Entwurf ist Reserve-Eigentum")
        self.assertIn("data/reserve-quarantine.json", rsg.STAGE_PATHS,
                      "der Quarantäne-Zähler muss den Lauf überleben")
        self.assertIn("data/reserve-quarantine.json", rsg.ALLOWED_FILES)


class IntentHeilerTests(unittest.TestCase):
    """Nachzug 22.09.2026 (#349, Run 35706157938).

    publish_gate-Kriterium 5 (Intent-Wächter, IW0–IW9) hatte in der Reserve-
    Kette keinen Heiler. Der reale Nachtlauf erzeugte einen Kandidaten, der
    Wächter meldete „IW8 – Anker nennt kein Angebot“, die Zertifizierung läuft
    STRICT-DRY (schreibt nichts) → 5/6, End-Gate „Stock shortage must not look
    successful“ rot. Sieben Minuten später heilte der tägliche Affiliate-Lauf
    DENSELBEN Fund in DERSELBEN Datei byte-identisch – mit `--fix --heal
    --file`, also genau dem Aufruf, für den der Wächter gebaut ist.
    """

    KAPUTT = ("Intro zum Stromsparen im Haushalt.\n\n"
              "> 💶 **Spar-Tipp zwischendurch:** Vergleiche jetzt und sichere "
              "dir den besten Tarif: [**Zum Vergleich**](/go/strom/)\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = Path(self.tmp.name) / "2026-09-22-strom" / "index.md"
        self.index.parent.mkdir(parents=True)
        self.index.write_text(
            '---\ntitle: "Testartikel Strom"\ndescription: "Test"\n'
            "date: 2026-09-22T06:00:00Z\ndraft: true\nreserve: true\n"
            'tags: ["Strom sparen"]\ncategories: ["Ratgeber"]\n'
            'pillar: "strom-sparen"\nauthor: "Frank Hartung"\n---\n\n'
            + self.KAPUTT, encoding="utf-8")

    def _guard(self, *args) -> dict:
        """Wächter datei-bezirkelt, ohne Report-/State-Schreibzugriff."""
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "affiliate_intent_guard.py"),
             *args, "--file", str(self.index), "--json"],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertTrue(proc.stdout.strip(),
                        f"keine Auswertung: rc={proc.returncode} {proc.stderr}")
        return json.loads(proc.stdout)

    def test_iw8_fund_wird_vor_der_zertifizierung_geheilt(self):
        vorher = self._guard()
        self.assertEqual(vorher["exit_code"], 1, "IW8 muss als Fund erkannt werden")
        self.assertTrue(any(f["code"] == "IW8" for f in vorher["findings"]),
                        vorher["findings"])
        geheilt = self._guard("--fix", "--heal")
        self.assertEqual(geheilt["exit_code"], 0, geheilt["findings"])
        self.assertTrue(geheilt["healed"], "der Fund muss deterministisch geheilt werden")
        text = self.index.read_text(encoding="utf-8")
        self.assertIn("/go/strom/", text, "der Affiliate-Link darf nicht verloren gehen")
        # IW8 verlangt: Der Anker NENNT das Angebot (Route = Stromtarife) –
        # die konkrete Formulierung ist Sache des Kontrakts, nicht des Tests.
        self.assertRegex(text, r"\[\*\*[^*]*Strom[^*]*\*\*\]\(/go/strom/\)",
                         "der Anker muss das Angebot nennen (IW8)")
        # Idempotenz: der zweite Heil-Lauf ändert nichts mehr.
        nachher = text
        self.assertEqual(self._guard("--fix", "--heal")["exit_code"], 0)
        self.assertEqual(self.index.read_text(encoding="utf-8"), nachher)

    def test_iw3_ki_reserve_entfernt_unehrlichen_werbesatz(self):
        """#436: Ein KI-Entwurf darf nicht ewig an human-owned IW3 hängen.

        Das reale ETF-Muster versprach einen Broker-Vergleich, verlinkte aber
        das Einzelangebot der C24 Bank. Sicher ist weder Umrouten noch
        Umschreiben, sondern das Entkommerzialisieren genau dieses Satzes.
        """
        self.index.write_text(
            '---\ntitle: "ETF-Sparplan 2026: Vermögen aufbauen"\n'
            'description: "ETF-Sparplan verständlich erklärt."\n'
            "date: 2026-09-28T06:00:00Z\ndraft: true\nreserve: true\n"
            "ai_generated: true\n"
            'tags: ["ETF-Sparplan"]\ncategories: ["Ratgeber"]\n'
            'pillar: "frugalismus"\nauthor: "Frank Hartung"\n---\n\n'
            "💡 **Schnell-Tipp von FranksFinanzcheck:** Sichere Rücklagen "
            "verzinst parken: [**Jetzt C24 Bank Tagesgeld ansehen**]"
            "(/go/tagesgeld/)\n\n"
            "Nutze für den Vergleich der Broker unabhängige Portale. Ein "
            "Depotwechsel ist meist kostenlos. Ein passender Einstiegspunkt "
            "für den Vergleich findet sich hier: [/go/tagesgeld/ der C24 "
            "Bank](/go/tagesgeld/).\n\n"
            "👉 **Jetzt vergleichen und sparen:** [**→ Jetzt C24 Bank "
            "Tagesgeld ansehen**](/go/tagesgeld/)\n",
            encoding="utf-8")
        vorher = self._guard()
        iw3 = [f for f in vorher["findings"] if f["code"] == "IW3"]
        self.assertTrue(iw3 and iw3[0]["owner"] == "human", vorher)
        geheilt = self._guard("--fix", "--heal")
        self.assertEqual(geheilt["exit_code"], 0, geheilt)
        text = self.index.read_text(encoding="utf-8")
        self.assertNotIn("Ein passender Einstiegspunkt", text)
        self.assertIn("Nutze für den Vergleich der Broker unabhängige Portale.",
                      text, "redaktioneller Nachbarsatz muss erhalten bleiben")
        self.assertEqual(text.count("/go/tagesgeld/"), 2,
                         "nur der unehrliche Prosa-Link fällt; CTAs bleiben")
        self.assertEqual(self._guard("--fix", "--heal")["exit_code"], 0)

    def test_iw3_menschliche_prosa_bleibt_menschenverantwortung(self):
        """Die #436-Ausnahme darf nie auf Live-/Menschenprosa ausgreifen."""
        self.index.write_text(
            '---\ntitle: "ETF-Sparplan 2026: Vermögen aufbauen"\n'
            'description: "ETF-Sparplan verständlich erklärt."\n'
            "date: 2026-09-28T06:00:00Z\ndraft: true\nreserve: true\n"
            'tags: ["ETF-Sparplan"]\npillar: "frugalismus"\n---\n\n'
            "Ein passender Einstiegspunkt für den Vergleich findet sich "
            "hier: [Tagesgeld der C24 Bank](/go/tagesgeld/).\n",
            encoding="utf-8")
        vorher = self.index.read_text(encoding="utf-8")
        res = self._guard("--fix", "--heal")
        self.assertEqual(res["exit_code"], 1, res)
        self.assertEqual(self.index.read_text(encoding="utf-8"), vorher)

    def test_heiler_ist_dateibezirkelt_in_der_reserve_kette_verdrahtet(self):
        schritte = [e for e in rf.HEALER_CHAIN
                    if e[0] == "affiliate_intent_guard.py"]
        self.assertTrue(schritte,
                        "affiliate_intent_guard.py fehlt in der Heiler-Kette (#349)")
        self.assertTrue(all("--fix" in e[1] and "--heal" in e[1] and e[2] == "file"
                            for e in schritte),
                        "Intent-Heilung muss datei-bezirkelt laufen (nie korpusweit)")
        self.assertGreaterEqual(len(schritte), 2,
                                "nach jedem KI-Schritt und vor der Zertifizierung heilen")
        self.assertEqual(rf.HEALER_CHAIN[-1][0], "affiliate_intent_guard.py",
                         "das Intent-Gate ist ein hartes Publish-Gate-Kriterium "
                         "– nach ihm darf kein Heiler mehr am Kandidaten "
                         "schreiben (#349)")

    def test_kette_uebergibt_den_kandidatenpfad_an_den_waechter(self):
        """Beweist die Verdrahtung: Scope „file“ reicht --file durch.

        Der Test fängt den echten Aufruf ab (kein API-Zugriff, kein Schreiben)
        und prüft, dass genau der Kandidat als `--file` ankommt – eine Kette,
        die den Wächter korpusweit startet, wäre bei Entwürfen blind.
        """
        rufe = []

        class FakeProc:
            returncode = 0
            stdout = "ok\n"

        def fake_run(cmd, **kw):
            if "affiliate_intent_guard.py" in " ".join(cmd):
                rufe.append(cmd)
            return FakeProc()

        with patch.object(rf.subprocess, "run", fake_run):
            rf.run_chain([], [self.index], env={})
        self.assertTrue(rufe, "der Wächter wurde von der Kette nie aufgerufen")
        for cmd in rufe:
            self.assertIn("--file", cmd, cmd)
            self.assertEqual(cmd[cmd.index("--file") + 1], str(self.index), cmd)
            self.assertIn("--fix", cmd, cmd)


class DeckungsWacheTests(unittest.TestCase):
    """Nachzug 22.09.2026 (#349): Die Klasse, nicht nur der Einzelfall.

    Der Vertrag „jede ablehnende Publish-Gate-Regel hat einen Heiler in der
    Reserve-Kette“ war für zwei Gates handverdrahtet. Die Wache liest die Regeln
    aus publish_gate.py und prüft die Deckung – ein neues Gate ohne Heiler oder
    ein gelöschter Eintrag fällt sofort auf.
    """

    def test_alle_gate_regeln_sind_gedeckt(self):
        b = rhc.deckung()
        self.assertEqual(b["luecken"], [], "Gate-Regel ohne Heiler")
        self.assertEqual(b["tote_ausnahmen"], [], "Eintrag deckt nichts mehr")
        self.assertIn("affiliate_intent_failures",
                      {e["regel"] for e in b["gedeckt"]},
                      "der Intent-Wächter muss gedeckt sein (#349)")
        self.assertGreaterEqual(len(b["gedeckt"]), 9,
                                "die Regeln werden aus publish_gate.py gelesen")

    def test_fehlender_heiler_wird_erkannt(self):
        """Der reale #349-Fall: Regel im Gate, Heiler nicht in der Kette."""
        kette = [e for e in rf.HEALER_CHAIN
                 if e[0] != "affiliate_intent_guard.py"]
        b = rhc.deckung(chain=kette)
        self.assertIn(("affiliate_intent_failures", "nicht-in-der-kette"),
                      {(e["regel"], e["art"]) for e in b["luecken"]})

    def test_neue_gate_regel_ohne_deckung_wird_erkannt(self):
        text = (SCRIPTS / "publish_gate.py").read_text(encoding="utf-8")
        b = rhc.deckung(text + "\ndef branding_failures(candidates):\n    pass\n")
        self.assertIn(("branding_failures", "keine-deckung"),
                      {(e["regel"], e["art"]) for e in b["luecken"]})

    def test_luecke_stoppt_vor_jedem_schreibzugriff(self):
        """Struktur vor Arbeit: eine Lücke beendet `finish()` mit rc=1.

        Ohne diese Sperre liefe die Nacht wieder als stiller 5/6-Lauf aus:
        die Veredelung hätte den Pool gehoben, die Zertifizierung wäre an einer
        unheilbaren Gate-Regel gescheitert und der End-Gate hätte nur die
        Knappheit gemeldet (#349). Der Test verbietet jeden Zugriff auf den
        Pool, bevor die Deckung steht.
        """
        gerufen = {}

        def fake_write_report(results, targets, started, isolation=None,
                              deckung=None):
            gerufen["targets"] = targets
            gerufen["deckung"] = deckung

        luecke = {
            "gedeckt": [],
            "luecken": [{"regel": "affiliate_intent_failures",
                         "art": "nicht-in-der-kette",
                         "heiler": ["affiliate_intent_guard.py"]}],
            "tote_ausnahmen": [],
        }

        def platzt(*a, **kw):
            raise AssertionError("finish() hat den Pool angefasst, obwohl die "
                                 "Heiler-Deckung lückenhaft ist")

        with patch.object(rf, "heiler_deckung", lambda: luecke), \
                patch.object(rf, "write_report", fake_write_report), \
                patch.object(rf, "certified_slugs", platzt), \
                patch.object(rf, "now_utc_iso", lambda: "2026-09-22T09:00:00Z"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = rf.finish()
        self.assertEqual(rc, 1, "eine Deckungslücke muss den Lauf laut stoppen")
        self.assertIn("::error::", buf.getvalue(),
                      "GitHub muss die Lücke als Fehler sehen")
        self.assertEqual(gerufen["targets"], [],
                         "kein Kandidat darf vor der Deckungsprüfung gehoben sein")
        self.assertEqual(gerufen["deckung"], luecke)


class GateDiagnoseTests(unittest.TestCase):
    """Nachzug #295: Das Zertifikat muss den KONKRETEN Fund nennen."""

    LOG = (
        "Publish-Gate: 1 Kandidat(en) für heute → ['2026-09-15-pool']\n"
        "  🛑 2026-09-15-pool: WIRD VERWORFEN (kein Artefakt, nächster Lauf "
        "versucht neues Thema)\n"
        "     - Affiliate-Link-Integrität nicht bestanden (defekte/nicht "
        "gerenderte CTA): Kein vollständiger Markdown-Link in CTA-Zeile "
        "('Spar-Tipp zwischendurch')\n"
        "\nErgebnis: 1/1 Artikel am Gate scheitern (1 verworfen, 0 → draft).\n")

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_readiness as rr
        self.rr = rr

    def test_konkreter_fund_statt_platzhalter(self):
        funde = self.rr.gate_findings(self.LOG)
        self.assertTrue(any("Markdown-Link in CTA-Zeile" in f for f in funde),
                        funde)
        grund = self.rr.grund_aus_funden(funde)
        self.assertIn("Markdown-Link in CTA-Zeile", grund)
        self.assertNotIn("WIRD VERWORFEN", grund,
                         "die Überschriftszeile ist keine Begründung")
        self.assertNotIn("Workflow-Log", grund,
                         "der Platzhalter darf nicht mehr geschrieben werden")

    def test_ohne_fund_bleibt_eine_erklarung(self):
        self.assertIn("STRICT dry-run", self.rr.grund_aus_funden([]))


if __name__ == "__main__":
    unittest.main()


# ===========================================================================
#  Nachzug 26.09.2026 (#387) – „Content-Reserve rot, obwohl Content da war"
#  ---------------------------------------------------------------------
#  Der Lauf vom 26.09. war rot mit 2/6, und der Grund stand in keinem Log:
#  Der Pool hatte in 18 Stunden fünf Kandidaten verloren, von denen ZWEI
#  physisch noch im Repo lagen – ihnen fehlte nur die `reserve`-Fahne, weil
#  ein fremder Commit ihr Frontmatter neu geschrieben hatte. Gleichzeitig
#  produzierte der Nachschub sechsmal dasselbe Thema (er nahm immer das
#  erste freie), und eine zu scharfe Titelregel sperrte einen vollständigen
#  Titel aus. Jede dieser Ursachen bekommt hier ihren Vertrag.
# ===========================================================================
class BestandsWaechterTests(unittest.TestCase):
    """Leck 1: Ein Kandidat darf nicht durch eine fremde Umschreibung
    aus dem Pool fallen (Flag-Verlust = lautloser Vorrats-Verlust)."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_custody as rc
        self.rc = rc
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "posts"
        self.ledger = Path(self.tmp.name) / "custody.json"

    def _post(self, slug, fm):
        d = self.posts / slug
        d.mkdir(parents=True)
        (d / "index.md").write_text(f"---\n{fm}\n---\n\nBody.\n",
                                    encoding="utf-8")
        return d / "index.md"

    def test_verlorene_fahne_wird_zurueckgeholt(self):
        datei = self._post("2026-09-24-x",
                           'title: "X"\ndate: 2026-09-24\ndraft: true')
        self.rc.ledger_speichern({"x": {"zustand": "pool",
                                        "seit": "2026-09-24"}}, self.ledger)
        lage = self.rc.heilen(self.posts, pfad=self.ledger)
        self.assertEqual([e["slug"] for e in lage["geheilt"]], ["2026-09-24-x"])
        self.assertIn("reserve: true", datei.read_text(encoding="utf-8"))

    def test_fremder_entwurf_bleibt_fremd(self):
        """Nur wer NACHWEISLICH im Pool war, wird geheilt – sonst würde die
        Wache Franks Hand-Entwürfe einsammeln."""
        datei = self._post("2026-09-24-hand",
                           'title: "Hand"\ndate: 2026-09-24\ndraft: true')
        lage = self.rc.heilen(self.posts, pfad=self.ledger)
        self.assertEqual(lage["geheilt"], [])
        self.assertNotIn("reserve: true", datei.read_text(encoding="utf-8"))

    def test_redating_verliert_das_gedaechtnis_nicht(self):
        """Die Veredelung datiert Kandidaten auf heute um (Ordner-Umbenennung).
        Ein Gedächtnis mit Datumspräfix als Schlüssel wäre nach einer Nacht
        wertlos und würde Phantome melden."""
        self._post("2026-09-25-y",
                   'title: "Y"\ndate: 2026-09-25\ndraft: true\nreserve: true')
        self.rc.heilen(self.posts, pfad=self.ledger)
        (self.posts / "2026-09-25-y").rename(self.posts / "2026-09-26-y")
        lage = self.rc.bestandsaufnahme(self.posts, pfad=self.ledger)
        self.assertEqual(lage["verwaist"], [],
                         "Re-Dating darf keine Phantome erzeugen")
        self.assertIn("2026-09-26-y", [e["slug"] for e in lage["pool"]])

    def test_waechter_haengt_in_der_produktionslinie(self):
        """Eine Wache, die niemand ruft, ist Dekoration."""
        root = Path(__file__).resolve().parents[2]
        for datei in ("scripts/reserve_readiness.py",
                      "scripts/reserve_finisher.py",
                      "scripts/engine_generate.py"):
            text = (root / datei).read_text(encoding="utf-8")
            self.assertIn("reserve_custody", text,
                          f"{datei} ruft den Bestands-Wächter nicht")

    def test_gedaechtnis_ueberlebt_den_runner(self):
        """Ein Gedächtnis, das nicht committet wird, ist keines (#349-Klasse)."""
        root = Path(__file__).resolve().parents[2]
        guard = (root / "scripts" / "reserve_stage_guard.py").read_text(
            encoding="utf-8")
        for pfad in ("data/reserve-custody.json",
                     "data/reserve-topic-ledger.json"):
            self.assertIn(pfad, guard,
                          f"{pfad} wird nie gestagt – das Gedächtnis "
                          "verfällt mit dem Runner")


class ThemenDispositionTests(unittest.TestCase):
    """Leck 2: Der Nachschub nahm immer das ERSTE freie Thema – sechs
    Varianten desselben Themas, die der Dubletten-Schutz später wieder
    kassierte (verbrannte Arbeit, Pool bleibt leer)."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_topics as rt
        self.rt = rt

    def test_belegtes_thema_wird_nicht_erneut_vorgeschlagen(self):
        # Beide Themen sind bewusst NICHT-YMYL: Hier wird die
        # Leitbegriff-Kollision geprüft, nicht die Bahn-Trennung (die hat
        # ihren eigenen Test weiter unten). Vorher stand hier ein
        # Versicherungs-Thema – seit der Bahn-Trennung (#521) filtert die
        # AUTO-Bahn das korrekt weg und der Test maß zwei Dinge auf einmal.
        topics = [{"title": "Stromfresser finden: Die größten Energiediebe"},
                  {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
        bestand = {"2026-09-25-a":
                   "Stromfresser finden: So stoppst du teure Energiediebe"}
        with tempfile.TemporaryDirectory() as tmp:
            vorschlaege = self.rt.disponieren(
                topics, bestand=bestand, limit=5,
                pfad=Path(tmp) / "ledger.json")
        self.assertEqual([t["title"] for t in vorschlaege],
                         ["Haushaltsbuch führen: App, Excel oder Papier?"])

    # ---------------------------------------------------------------
    # Issue #521 (02.10.2026): Die Disposition war risikoblind.
    # Sie wählte YMYL-Themen (Versicherung, Rente, Kredit) für die
    # Automatik aus, obwohl deren Artikel per Vertrag (editorial_review_
    # gate, fail-closed) NIE ohne menschliche Freigabe live gehen. Jeder
    # solche Griff kostete einen LLM-Aufruf, einen Produktionsslot UND
    # sperrte das Thema 180 Tage – ohne dass je ein Artikel erscheinen
    # konnte. Am 02.10.2026 waren 2 der 4 produzierten Themen genau das.
    # ---------------------------------------------------------------
    def test_ymyl_thema_belegt_keinen_automatik_slot(self):
        topics = [{"title": "Reisekrankenversicherung: Das musst du wissen"},
                  {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
        with tempfile.TemporaryDirectory() as tmp:
            auto = self.rt.disponieren(topics, bestand={}, limit=5,
                                       pfad=Path(tmp) / "l.json")
        titel = [t["title"] for t in auto]
        self.assertNotIn("Reisekrankenversicherung: Das musst du wissen", titel,
                         "ein YMYL-Thema in der AUTO-Bahn verbrennt Slot und "
                         "Thema, ohne je live gehen zu können")
        self.assertIn("Haushaltsbuch führen: App, Excel oder Papier?", titel)

    def test_ymyl_thema_bleibt_fuer_die_fachbahn_erreichbar(self):
        """Nicht verbannt, nur umgeleitet – sonst stirbt die Hälfte des Pools."""
        topics = [{"title": "Reisekrankenversicherung: Das musst du wissen"},
                  {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "l.json"
            fach = self.rt.disponieren(topics, bestand={}, limit=5,
                                       pfad=pfad, bahn="fachfreigabe")
            alle = self.rt.disponieren(topics, bestand={}, limit=5,
                                       pfad=pfad, bahn=None)
        self.assertEqual([t["title"] for t in fach],
                         ["Reisekrankenversicherung: Das musst du wissen"])
        self.assertEqual(len(alle), 2,
                         "bahn=None muss weiterhin den ganzen Pool liefern")

    def test_bahn_default_ist_auto(self):
        """Altaufrufer (reserve_gate, reserve_pool) erben die sichere Bahn."""
        import inspect
        sig = inspect.signature(self.rt.disponieren)
        self.assertEqual(sig.parameters["bahn"].default,
                         self.rt.BAHN_DEFAULT)
        self.assertEqual(self.rt.BAHN_DEFAULT, "auto")

    def test_engine_nutzt_die_disposition_statt_des_ersten_freien(self):
        root = Path(__file__).resolve().parents[2]
        text = (root / "scripts" / "engine_generate.py").read_text(
            encoding="utf-8")
        self.assertIn("reserve_topics", text)
        self.assertIn("disponieren(", text)
        topup = text[text.index("def _reserve_topup"):]
        topup = topup[:topup.index("\ndef ")]
        # Nur CODE zählt – der Kommentarkopf erklärt die Reparatur und darf
        # das alte Muster zitieren.
        code = "\n".join(z for z in topup.splitlines()
                         if not z.lstrip().startswith("#"))
        self.assertNotIn("freie[0]", code,
                         "das erste freie Thema zu nehmen war die Ursache "
                         "der Themen-Monokultur (#387)")

    def test_batch_gibt_nicht_beim_ersten_fehlschlag_auf(self):
        """Eine zickige KI-Antwort darf nicht die ganze Nachtproduktion
        kosten: Der Batch läuft weiter, solange es freie Themen gibt."""
        root = Path(__file__).resolve().parents[2]
        text = (root / "scripts" / "engine_generate.py").read_text(
            encoding="utf-8")
        self.assertIn("RESERVE_LEERLAUF_MAX", text)
        self.assertIn('stop.get("stop")', text)


class VielfaltBeimVeroeffentlichenTests(unittest.TestCase):
    """Leck 3: Am 20.09. gingen vier Gasrechnungs-Varianten am selben Tag
    live; drei wurden danach zu Entwürfen zurückgestuft („Rückläufer")."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_gate as rg
        import reserve_pool as rp
        self.rp = rp
        self.rg = rg

    def test_dublette_wird_zurueckgestellt(self):
        frisch = {"2026-09-20-gas":
                  "Gasrechnung senken: Dein Strategieplan im Spätsommer"}
        self.assertTrue(self.rp.sperr_treffer(
            "Gasrechnung senken: Clevere Herbst-Vorbereitung im Check", frisch))

    def test_fremdes_thema_darf_raus(self):
        frisch = {"2026-09-20-gas":
                  "Gasrechnung senken: Dein Strategieplan im Spätsommer"}
        self.assertIsNone(self.rp.sperr_treffer(
            "Reisekrankenversicherung: Worauf du 2026 achten musst", frisch))

    def test_kadenz_schlaegt_vielfalt_wenn_sonst_luecke(self):
        """Ein Pool aus EINEM Thema muss den Tag trotzdem tragen: lieber ein
        thematischer Nachbar als eine leere Kadenz – aber nie zwei am
        selben Tag (das erzeugte die fünf Rückläufer)."""
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            gestern = (dt.date.today() - dt.timedelta(days=1)).isoformat()
            for name, draft, titel in (
                    ("live-a", "false", "Stromfresser finden: Die "
                                        "teuersten Energiediebe"),
                    ("pool-a", "true", "Stromfresser finden: So senkst du "
                                       "die Stromrechnung"),
                    ("pool-b", "true", "Stromfresser finden: So stoppst du "
                                       "die Energie-Lecks")):
                d = posts / name
                d.mkdir(parents=True)
                extra = "reserve: true\n" if draft == "true" else ""
                (d / "index.md").write_text(
                    f'---\ntitle: "{titel}"\ndate: {gestern}T06:00:00Z\n'
                    f"draft: {draft}\n{extra}---\n\nBody.\n",
                    encoding="utf-8")
            with self.rp._als_publikationstag():
                raus = self.rp.publish_to_min(2, posts_dir=posts,
                                              validator=lambda i: True)
        self.assertEqual(len(raus), 1,
                         "genau ein Artikel: Kadenz gerettet, Dublette "
                         "am selben Tag vermieden")

    def test_gleiche_thema_am_selben_tag_bleibt_ausgeschlossen(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            heute = dt.date.today().isoformat()
            for name, draft, titel in (
                    ("live-gas", "false", "Gasrechnung senken: Dein "
                                          "Strategieplan"),
                    ("pool-gas", "true", "Gasrechnung senken: Clevere "
                                         "Herbst-Vorbereitung")):
                d = posts / name
                d.mkdir(parents=True)
                extra = "reserve: true\n" if draft == "true" else ""
                (d / "index.md").write_text(
                    f'---\ntitle: "{titel}"\ndate: {heute}T06:00:00Z\n'
                    f"draft: {draft}\n{extra}---\n\nBody.\n",
                    encoding="utf-8")
            with self.rp._als_publikationstag():
                raus = self.rp.publish_to_min(2, posts_dir=posts,
                                              validator=lambda i: True)
        self.assertEqual(raus, [], "Dublette am selben Tag = Rückläufer "
                                   "von morgen (#387)")

    def test_vorrat_vielfalt_wird_benannt(self):
        """6 Varianten EINES Themas sind kein Vorrat von 6."""
        themen, familien = self.rg.themen_vielfalt([
            {"slug": "2026-09-26-stromfresser-finden-so-senkst-du-deine-"
                     "stromrechnung-massiv", "ready": True},
            {"slug": "2026-09-26-stromfresser-finden-so-stoppst-du-die-"
                     "energie-lecks", "ready": True},
            {"slug": "2026-09-26-50-30-20-regel-dein-finanz-kompass-fuer-"
                     "das-jahr-2026", "ready": True},
            {"slug": "egal", "ready": False}])
        self.assertEqual(themen, 2, familien)
        self.assertTrue(any(len(v) == 2 for v in familien.values()), familien)

    def test_sperre_ist_fail_open(self):
        """Der Notnagel darf nie an seiner eigenen Zusatzprüfung scheitern."""
        class Kaputt:
            @staticmethod
            def thema_kollision(*a, **k):
                raise RuntimeError("Modul defekt")
        self.assertIsNone(self.rp.sperr_treffer("Irgendein Titel",
                                                {"s": "Anderer Titel"},
                                                Kaputt))


class TitelIntegritaetTests(unittest.TestCase):
    """Leck 4: Die R5-Regel hielt vollständige Titel für abgeschnitten
    (Whitelist als Pflaster) – und es gab keinen Heiler für ihren Fund."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import check_titles as ct
        self.ct = ct

    def test_vollstaendiger_titel_ist_kein_abbruch(self):
        for titel in ("Stromfresser finden: So senkst du deine Stromrechnung "
                      "massiv",
                      "Nebenkosten-Abrechnung: Was 2026 wirklich zählt",
                      "Haushaltsbudget: Wie viel Puffer ist realistisch"):
            self.assertIsNone(self.ct.r5_truncation(titel), titel)

    def test_echter_abbruch_bleibt_ein_fund(self):
        for titel in ("Unfallversicherung im Vergleich: Sinnvoll? Kosten &",
                      "Stromkosten senken: Der beste Tarif für die",
                      "Tagesgeld-Vergleich 2026: Die besten Angebote und"):
            self.assertIsNotNone(self.ct.r5_truncation(titel), titel)

    def test_heiler_ist_verlustfrei_und_idempotent(self):
        roh = "Haushaltskasse: Diese Posten und was sie"
        geheilt = self.ct.heal_r5(roh)
        self.assertNotEqual(geheilt, roh, "der Fund wurde nicht geheilt")
        self.assertIsNone(self.ct.r5_truncation(geheilt),
                          "der geheilte Titel ist immer noch ein Fund")
        self.assertTrue(roh.startswith(geheilt),
                        "Heilung darf nur kürzen, nie dichten")
        self.assertEqual(self.ct.heal_r5(geheilt), geheilt,
                         "ein geheilter Titel darf nicht erneut wandern")

    def test_kein_raten_bei_zu_wenig_rest(self):
        """Lieber ein ehrlicher Fund als ein erfundener Titel: Bleibt nach
        dem Kürzen kein tragfähiger Titel übrig, bleibt der Text, wie er
        ist – der Fund geht an einen Menschen."""
        self.assertEqual(self.ct.heal_r5("Der Tarif für"), "Der Tarif für")


class GateDiagnoseUrsachenTests(unittest.TestCase):
    """Leck 5: Der End-Gate meldete „N/6" – aber nie, WARUM."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_gate as rg
        self.rg = rg

    def test_blocker_wird_benannt(self):
        zeilen = self.rg.diagnose(2, 6, [
            {"slug": "a", "ready": True},
            {"slug": "b", "ready": False, "reason": "Cover-Text-Komplettheit"}])
        self.assertTrue(any("BLOCKER" in z and "Cover-Text" in z
                            for z in zeilen), zeilen)

    def test_diagnose_faellt_nie_um(self):
        """Eine Diagnose, die selbst abstürzt, macht aus einem Engpass
        einen zweiten Vorfall."""
        self.assertIsInstance(self.rg.diagnose(0, 6, []), list)


class WorkflowVertragTests(unittest.TestCase):
    """Die Reparatur muss im Workflow verdrahtet sein, nicht nur im Repo."""

    def test_bestands_waechter_laeuft_vor_der_produktion(self):
        root = Path(__file__).resolve().parents[2]
        wf = (root / ".github" / "workflows" / "content-reserve.yml").read_text(
            encoding="utf-8")
        self.assertIn("reserve_custody.py --heal", wf)
        self.assertLess(
            wf.index("reserve_custody.py --heal"),
            wf.index("run: python3 scripts/engine_generate.py --reserve-only"),
            "erst den Bestand sichern, dann neu produzieren")

    def test_gedaechtnisse_ueberleben_den_rebase(self):
        root = Path(__file__).resolve().parents[2]
        sync = (root / "scripts" / "git_sync.sh").read_text(encoding="utf-8")
        self.assertIn("data/reserve-topic-ledger.json", sync)
        self.assertIn("data/reserve-custody.json", sync)


# ===========================================================================
#  #393 – DIE MESSLATTE GEHÖRT NICHT DEM GEMESSENEN
# ---------------------------------------------------------------------------
#  Am 26.09.2026 meldete der harte End-Gate „✅ Reserve-Pool gate-fertig:
#  4/4 Kandidaten zertifiziert" – bei einem Produktionsziel von 6. Möglich war
#  das, weil drei Stellen dieselbe Zahl unabhängig voneinander kannten und die
#  entscheidende davon IM GEPRÜFTEN ARTEFAKT stand:
#
#    * reserve_gate.evaluate()     las `target` aus dem Zertifikat
#    * reserve_converge.cert_state() ebenso – und reichte es als
#      RESERVE_TARGET an die Kindprozesse weiter, die es zurückschrieben
#    * bot_watchdog                hatte `minimum = 4` hart im Code
#
#  Ergebnis: eine einmal abgesenkte Latte hielt sich selbst fest (Ratsche),
#  und weil Alarmschwelle == Zielbestand war, öffnete sich Ticket #393 nach
#  JEDER Veröffentlichung neu. Die folgenden Verträge frieren beides ein.
# ===========================================================================
class MesslattenBesitzTests(unittest.TestCase):
    """Das Zertifikat ist Beweismittel, nicht Gesetzgeber."""

    def setUp(self):
        self._alt = {k: os.environ.get(k)
                     for k in ("RESERVE_TARGET", "RESERVE_PUFFER")}

    def tearDown(self):
        for k, v in self._alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _cert(self, tmp, payload):
        path = Path(tmp) / "reserve-readiness.json"
        path.write_text(json.dumps(payload, ensure_ascii=False),
                        encoding="utf-8")
        return path

    # --- Der Kern: ein magerer Lauf senkt die Latte nicht ------------------
    def test_zertifikat_setzt_sein_ziel_nicht_selbst(self):
        os.environ["RESERVE_TARGET"] = "6"
        with tempfile.TemporaryDirectory() as tmp:
            cert = self._cert(tmp, {
                "target": 4, "ready": 4,
                "generated_at": dt.datetime.now(dt.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"),
                "candidates": [{"slug": f"k{i}", "ready": True}
                               for i in range(4)],
            })
            ready, target, _ = rg.evaluate(cert)
        self.assertEqual(target, 6,
                         "Das Ziel muss aus der Produktionsumgebung kommen, "
                         "nicht aus dem geprüften Zertifikat")
        self.assertEqual(ready, 4)
        self.assertLess(ready, target,
                        "4 von 6 ist ein Engpass – und muss einer bleiben")

    def test_engpass_sieht_nicht_erfolgreich_aus(self):
        """„Stock shortage must not look successful" – jetzt auch, wenn das
        Zertifikat selbst behauptet, das Ziel sei erreicht."""
        os.environ["RESERVE_TARGET"] = "6"
        with tempfile.TemporaryDirectory() as tmp:
            cert = self._cert(tmp, {
                "target": 4, "ready": 4,
                "generated_at": dt.datetime.now(dt.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"),
                "candidates": [{"slug": f"k{i}", "ready": True}
                               for i in range(4)],
            })
            ready, target, cands = rg.evaluate(cert)
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                rg.report(ready, target, cands)
            text = puffer.getvalue()
        self.assertIn("ENGPA", text.upper(),
                      f"Ein 4/6 muss als Engpass gemeldet werden: {text}")
        self.assertNotIn("gate-fertig: 4/4", text)

    def test_ratsche_ist_tot_konvergenz_liest_produktionsziel(self):
        """Die Rückkopplung Zertifikat → RESERVE_TARGET → Zertifikat.

        Vorher: cert_state() meldete target 4, `brauche` war 0, die Nacht
        produzierte nichts nach – und schrieb die 4 erneut fest.
        """
        os.environ["RESERVE_TARGET"] = "6"
        with tempfile.TemporaryDirectory() as tmp:
            cert = self._cert(tmp, {
                "target": 4, "ready": 4,
                "candidates": [{"slug": f"k{i}", "ready": True}
                               for i in range(4)],
            })
            st = rc.cert_state(cert)
        self.assertEqual(st["target"], 6,
                         "Konvergenz muss auf das Produktionsziel hinarbeiten")
        self.assertEqual(st["zertifikat_ziel"], 4,
                         "…das Zertifikatsziel bleibt als Beweismittel lesbar")
        self.assertGreater(st["target"] - st["ready"], 0,
                           "Bei 4/6 muss echter Nachschub-Bedarf entstehen")

    def test_readiness_stempelt_das_produktionsziel(self):
        """Wer das Zertifikat schreibt, schreibt die Latte der Produktion."""
        os.environ["RESERVE_TARGET"] = "7"
        self.assertEqual(rr.target(), 7)
        self.assertEqual(rr.target(), re_.ziel(),
                         "reserve_readiness und SSOT dürfen nie auseinanderlaufen")

    def test_drift_wird_gemeldet_statt_verschwiegen(self):
        os.environ["RESERVE_TARGET"] = "6"
        self.assertIn("MESSLATTE", re_.messlatten_drift(4, 6) or "")
        self.assertIsNone(re_.messlatten_drift(6, 6))
        self.assertIsNone(re_.messlatten_drift(9, 6))
        self.assertIsNone(re_.messlatten_drift(None, 6))


class PufferInvarianteTests(unittest.TestCase):
    """Alarmschwelle < Ziel – die Hysterese, die #393 täglich neu öffnete."""

    def setUp(self):
        self._alt = {k: os.environ.get(k)
                     for k in ("RESERVE_TARGET", "RESERVE_PUFFER")}

    def tearDown(self):
        for k, v in self._alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_alarmschwelle_liegt_immer_echt_unter_dem_ziel(self):
        for z in range(re_.ZIEL_MIN, 21):
            for p in (1, 2, 3, 5, 50):
                os.environ["RESERVE_TARGET"] = str(z)
                os.environ["RESERVE_PUFFER"] = str(p)
                a = re_.alarmschwelle()
                self.assertGreaterEqual(a, 1, f"Ziel {z}, Puffer {p}")
                self.assertLess(
                    a, z,
                    f"Ziel {z}, Puffer {p}: Alarmschwelle {a} ist nicht "
                    f"kleiner als das Ziel – genau dieser Null-Puffer hat "
                    f"#393 jeden Tag neu geöffnet")

    def test_dokumentiertes_ziel_behaelt_die_alte_alarmsemantik(self):
        """Ziel 6 → Alarm unter 4: exakt der früher hart codierte Wert."""
        os.environ["RESERVE_TARGET"] = "6"
        os.environ.pop("RESERVE_PUFFER", None)
        self.assertEqual(re_.alarmschwelle(), 4)

    def test_watchdog_nutzt_die_abgeleitete_schwelle(self):
        """Kein hart codiertes 4 mehr – die Schwelle wandert mit dem Ziel."""
        quelle = (Path(__file__).resolve().parents[1]
                  / "bot_watchdog.py").read_text(encoding="utf-8")
        self.assertNotIn("minimum = 4", quelle,
                         "Die Alarmschwelle darf nicht wieder hart im "
                         "Watchdog stehen")
        self.assertIn("reserve_economy.alarmschwelle()", quelle)
        os.environ["RESERVE_TARGET"] = "10"
        os.environ.pop("RESERVE_PUFFER", None)
        self.assertEqual(re_.alarmschwelle(), 8,
                         "Ziel 10 muss die Schwelle auf 8 mitziehen")

    def test_kaputte_konfiguration_senkt_das_ziel_nicht_still(self):
        for murks in ("", "   ", "vier", "4,5"):
            os.environ["RESERVE_TARGET"] = murks
            self.assertEqual(re_.ziel(), re_.ZIEL_DEFAULT,
                             f"{murks!r} darf nicht als Ziel durchgehen")
        warnungen = []
        os.environ["RESERVE_TARGET"] = "1"
        self.assertEqual(re_.ziel(warnungen), re_.ZIEL_MIN)
        self.assertTrue(warnungen, "Eine Klemmung muss sich melden")


# ===========================================================================
#  VORGANG WF-B594 (Issue #594, 05.10.2026) – „Löschen braucht einen Beweis"
#
#  Achter Vorfall derselben Klasse (#251, #272, #281, #393, #446, #462, #520).
#  Diesmal war die Ursache nicht fehlende Produktion, sondern VERNICHTUNG:
#  Um 17:20 Uhr zertifizierte der Lauf acht Kandidaten mit ausschließlich
#  heilbaren Gründen, um 17:35 Uhr löschte `reserve_janitor.purge()` genau
#  diese acht Entwürfe samt 24 Cover-Dateien (Commit c56382b). Vier Verträge
#  werden hier festgenagelt:
#
#   B4  Die Triage darf ein langes Frontmatter nicht für einen Quelldefekt
#       halten (120-Zeilen-Fenster -> acht YMYL-Entwürfe „titel: leer").
#   B3/B2 Gelöscht wird nur, was unheilbar ist – belegt über zwei Läufe und
#       nach einer Karenz. Heilbares ist Material, kein Müll.
#   B5  Eine zweite Deckungswache prüft das LÖSCHRECHT: Jeder heilbare
#       Triage-Blocker braucht seinen Heiler in der Kette.
#   B1  Fertige, herrenlose Entwürfe werden dem Pool zugeführt, statt neben
#       ihm zu verhungern (Watchdog meldete 0/6, während 5 Kandidaten am
#       echten Gate 0,898–0,90 erreichten).
# ===========================================================================
class TriageFensterTests(unittest.TestCase):
    """B4: Das 120-Zeilen-Fenster der Frontmatter-Suche.

    `fm_and_body()` suchte die schließende `---`-Zeile nur in den ersten 120
    Zeilen. Die acht YMYL-Versicherungsentwürfe tragen ~246 Zeilen
    Frontmatter (Quellen, Zahlenprotokoll, Freigabe-Block) – die Triage hielt
    deshalb den gesamten Artikel für einen Quelldefekt und meldete
    „titel: leer", „datum: nicht lesbar". Beides stand in Wahrheit sauber im
    Kopf. Der Janitor löschte sie als BLOCKIERT.
    """

    def _entwurf(self, fm_zeilen: int) -> str:
        fm = ['title: "Ein ordentlicher Titel fuer den Fenster-Test"',
              "date: 2026-09-01", "lastmod: 2026-09-01",
              'description: "Eine ordentliche Beschreibung mit genug Zeichen '
              'fuer das Meta-Gate der Reserve dieses Blogs."',
              "draft: true", "reserve: true"]
        fm += ["quellen:"] + [f'  - titel: "Beleg {i}"'
                              for i in range(fm_zeilen)]
        body = "\n".join(f"## Abschnitt {i}\nNutzwert mit Zahlen."
                         for i in range(6))
        return "---\n" + "\n".join(fm) + "\n---\n\n" + body + "\n"

    def test_langes_frontmatter_ist_kein_quelldefekt(self):
        import draft_triage as triage
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "content" / "posts" / "2026-09-01-lang"
            posts.mkdir(parents=True)
            (posts / "index.md").write_text(self._entwurf(300),
                                            encoding="utf-8")
            zeilen = triage.collect(tmp, dt.date(2026, 9, 26), 21)
        self.assertEqual(len(zeilen), 1)
        blocker = zeilen[0]["blocker"]
        for verboten in ("fm-", "titel:", "datum:"):
            self.assertFalse(
                [b for b in blocker if b.startswith(verboten)],
                f"{verboten} darf bei langem Frontmatter nicht auftauchen: "
                f"{blocker}")

    def test_kein_zeilenfenster_mehr_in_der_quelle(self):
        quelle = (SCRIPTS / "draft_triage.py").read_text(encoding="utf-8")
        self.assertNotIn("lines[1:121]", quelle,
                         "Das 120-Zeilen-Fenster darf nicht zurückkehren")
        self.assertIn("WF-B594", quelle,
                      "Die Reparatur muss an Ort und Stelle erklärt sein")


class LoeschRechtTests(unittest.TestCase):
    """B3/B2: Wer unwiderruflich löscht, trägt die Beweislast."""

    def setUp(self):
        import reserve_blocker_klassen as bk
        import reserve_janitor as rj
        self.bk, self.rj = bk, rj
        self.umwelt = {k: os.environ.get(k) for k in
                       ("RESERVE_JANITOR_HITS", "RESERVE_JANITOR_KARENZ_TAGE")}
        os.environ["RESERVE_JANITOR_HITS"] = "2"
        os.environ["RESERVE_JANITOR_KARENZ_TAGE"] = "0"
        self.addCleanup(self._umwelt_zurueck)

    def _umwelt_zurueck(self):
        for k, v in self.umwelt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_der_reale_fall_594_waere_verschont(self):
        """Die Gründe aus dem Zertifikat 601030e, Wort für Wort."""
        loeschen, bewertet = self.bk.loeschbar([
            "laenge: 5677 Zeichen < Soll 10000 (Wache: length_guard.py)",
            "interne links: 1 (Soll ≥ 2) – link_density_guard.py zählt den "
            "Artikel als unterversorgt"])
        self.assertFalse(loeschen,
                         "heilbare Gründe dürfen keine Löschung tragen")
        self.assertTrue(all(e["klasse"] == self.bk.HEILBAR for e in bewertet))

    def test_unbekannter_blocker_ist_niemals_loeschbar(self):
        self.assertFalse(self.bk.loeschbar(["voellig neuer fund: xyz"])[0])
        self.assertFalse(self.bk.klassifiziere("voellig neuer fund: xyz")
                         ["bekannt"])

    def test_quelldefekt_bleibt_raeumbar(self):
        """Sonst entsteht eine Halde, die kein Werkzeug anfassen kann."""
        self.assertTrue(self.bk.loeschbar([
            "fm-grenze: keine schließende `---`-Zeile gefunden",
            "laenge: 80 Zeichen < Soll 10000"])[0])

    def test_menschensache_wird_nie_automatisch_geloescht(self):
        loeschen, bewertung = self.bk.gate_befund_loeschbar(
            "editorial_review: Freigabe fehlt (Risikoklasse hoch)")
        self.assertFalse(loeschen)
        self.assertEqual(bewertung["klasse"], self.bk.MENSCHLICH)

    def _repo(self, tmp: Path, body: str, fm_extra: str = "") -> Path:
        """Synthetischer Kandidat – alles in Ordnung außer dem Prüffall."""
        posts = tmp / "content" / "posts"
        d = posts / "2026-09-01-kandidat"
        d.mkdir(parents=True)
        covers = tmp / "static" / "images" / "covers"
        covers.mkdir(parents=True, exist_ok=True)
        (covers / "kandidat.jpg").write_text("img", encoding="utf-8")
        (d / "index.md").write_text(
            '---\ntitle: "Kandidat mit ordentlichem Titel"\n'
            "date: 2026-09-01\nlastmod: 2026-09-01\n"
            'description: "Eine ordentliche Beschreibung mit genug Zeichen '
            'fuer das Meta-Gate der Reserve dieses Blogs."\n'
            "draft: true\nreserve: true\n"
            'cover:\n  image: "images/covers/kandidat.jpg"\n'
            f"{fm_extra}---\n\n{body}\n",
            encoding="utf-8")
        return d / "index.md"

    def test_janitor_verschont_heilbares_und_sagt_warum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root, "## Anfang\nNoch viel zu kurz.")
            ziele, _, geschont = self.rj.find_targets(
                root, today=dt.date.today(), run_key="run:1",
                zaehler_schreiben=False)
        self.assertEqual(ziele, {}, "ein heilbarer Entwurf ist kein Löschziel")
        self.assertEqual(len(geschont), 1)
        self.assertEqual(geschont[0]["klasse"], self.bk.HEILBAR)
        self.assertTrue(geschont[0]["grund"],
                        "Verschonen ohne Begründung wäre stilles Horten")

    # Ein Körper, an dem NICHTS heilbar ist: lang genug, strukturiert,
    # verlinkt. So bleibt der geleerte Titel der einzige Befund – und damit
    # der einzige Grund, über eine Löschung überhaupt nachzudenken.
    VOLLER_KOERPER = ("[A](../../posts/live-a/) und [B](../../posts/live-b/)\n"
                      + "\n".join(f"## Abschnitt {i}\nNutzwert mit Zahlen."
                                  for i in range(6)) * 90)

    def test_unheilbares_braucht_zwei_laeufe(self):
        body = self.VOLLER_KOERPER
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = self._repo(root, body)
            # Titel leeren -> einziger, unheilbarer Befund.
            index.write_text(index.read_text(encoding="utf-8").replace(
                'title: "Kandidat mit ordentlichem Titel"', 'title: ""'),
                encoding="utf-8")
            heute = dt.date.today()
            ziele1, _, geschont1 = self.rj.find_targets(
                root, today=heute, run_key="run:1")
            self.assertEqual(ziele1, {},
                             "ein einziger Lauf ist kein Beweis")
            self.assertEqual(geschont1[0]["klasse"], "beleg")
            ziele2, _, _ = self.rj.find_targets(root, today=heute,
                                                run_key="run:2")
            self.assertIn("2026-09-01-kandidat", ziele2,
                          "zwei Läufe mit demselben Fund rechtfertigen die "
                          "Löschung")
            # Derselbe Lauf darf nicht doppelt zählen.
            zaehler = json.loads((root / self.rj.JANITOR_STATE)
                                 .read_text(encoding="utf-8"))
            self.assertEqual(zaehler["2026-09-01-kandidat"]["hits"], 2)

    def test_karenz_schuetzt_junge_entwuerfe(self):
        os.environ["RESERVE_JANITOR_KARENZ_TAGE"] = "2"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = self._repo(root, self.VOLLER_KOERPER)
            index.write_text(index.read_text(encoding="utf-8").replace(
                'title: "Kandidat mit ordentlichem Titel"', 'title: ""'),
                encoding="utf-8")
            ziele, _, geschont = self.rj.find_targets(
                root, today=dt.date.today(), run_key="run:1",
                zaehler_schreiben=False)
        self.assertEqual(ziele, {})
        self.assertEqual(geschont[0]["klasse"], "karenz")

    def test_trockenlauf_zaehlt_nicht(self):
        """Ein Bericht darf keine Löschung herbeirechnen."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root, "kurz")
            for lauf in ("run:a", "run:b", "run:c"):
                self.rj.purge(root, dry_run=True, today=dt.date.today(),
                              run_key=lauf)
            self.assertFalse((root / self.rj.JANITOR_STATE).exists(),
                             "der Trockenlauf hat den Beleg-Zähler geschrieben")

    def test_startsperre_bei_lueckenhafter_deckung(self):
        """Ohne belastbare Klassen wird gar nicht erst gelöscht."""
        import reserve_healer_coverage as rhc_
        luecke = {"luecken": [{"blocker": "interne links:",
                               "art": "nicht-in-der-kette",
                               "heiler": ["internal_linker.py"]}],
                  "tote_eintraege": []}
        with patch.object(rhc_, "loeschdeckung", lambda *a, **k: luecke):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = self.rj.loesch_wache()
        self.assertEqual(rc, 1)
        self.assertIn("::error::", buf.getvalue())

    def test_echtes_repo_darf_heute_nichts_verlieren(self):
        """Scharfer Lauf: Im echten Bestand steht kein Löschziel."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bericht = self.rj.purge(ROOT, dry_run=True)
        self.assertEqual(bericht["deleted_slugs"], [],
                         f"der Janitor würde heute löschen: "
                         f"{bericht['deleted_slugs']}")


class LoeschDeckungsWacheTests(unittest.TestCase):
    """B5: Der Weg nach UNTEN braucht dieselbe Wache wie der Weg nach OBEN."""

    def test_jeder_triage_blocker_ist_gedeckt(self):
        b = rhc.loeschdeckung()
        self.assertEqual(b["luecken"], [],
                         "ein Triage-Blocker ohne Heiler oder Klasse")
        self.assertEqual(b["tote_eintraege"], [])
        self.assertIn("interne links:", {e["blocker"] for e in b["heilbar"]},
                      "die #594-Klasse muss ausdrücklich gedeckt sein")

    def test_fehlender_linker_faellt_sofort_auf(self):
        """Der reale Zustand vor der Reparatur: Blocker ohne jeden Heiler."""
        kette = [e for e in rf.HEALER_CHAIN if e[0] != "internal_linker.py"]
        b = rhc.loeschdeckung(chain=kette)
        self.assertIn(("interne links:", "nicht-in-der-kette"),
                      {(e["blocker"], e["art"]) for e in b["luecken"]})

    def test_neuer_blocker_ohne_klasse_ist_eine_luecke(self):
        b = rhc.loeschdeckung(praefixe=["laenge:", "brandneu:"])
        self.assertIn(("brandneu:", "unklassifiziert"),
                      {(e["blocker"], e["art"]) for e in b["luecken"]})

    def test_linker_laeuft_datei_bezirkelt_in_der_kette(self):
        eintrag = [e for e in rf.HEALER_CHAIN if e[0] == "internal_linker.py"]
        self.assertEqual(len(eintrag), 1, "genau einmal, nicht korpusweit")
        self.assertEqual(eintrag[0][2], "file",
                         "nur --file: der Live-Korpus bleibt unberührt")
        quelle = (SCRIPTS / "internal_linker.py").read_text(encoding="utf-8")
        self.assertIn("def load_single_source", quelle)
        self.assertIn("sources = load_single_source", quelle)

    def test_luecke_stoppt_die_veredelung_vor_jedem_schreibzugriff(self):
        luecke = {"luecken": [{"blocker": "interne links:",
                               "art": "nicht-in-der-kette",
                               "heiler": ["internal_linker.py"]}],
                  "tote_eintraege": []}
        gerufen = {}

        def fake_write_report(results, targets, started, isolation=None,
                              deckung=None):
            gerufen["targets"] = targets

        def platzt(*a, **kw):
            raise AssertionError("finish() hat den Pool angefasst, obwohl das "
                                 "Löschrecht ungedeckt ist")

        with patch.object(rf, "loesch_deckung", lambda: luecke), \
                patch.object(rf, "write_report", fake_write_report), \
                patch.object(rf, "certified_slugs", platzt), \
                patch.object(rf, "now_utc_iso", lambda: "2026-10-05T18:00:00Z"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc_ = rf.finish()
        self.assertEqual(rc_, 1)
        self.assertIn("::error::", buf.getvalue())
        self.assertEqual(gerufen["targets"], [])


class BestandsaufnahmeTests(unittest.TestCase):
    """B1: Fertige Entwürfe dürfen nicht neben dem Pool verhungern."""

    def setUp(self):
        import reserve_intake as ri
        self.ri = ri

    def test_selbsttest_der_aufnahme_ist_gruen(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_ = self.ri.run_selftest()
        self.assertEqual(rc_, 0, buf.getvalue())

    def test_zertifizierung_nimmt_auf_bevor_sie_zaehlt(self):
        quelle = (SCRIPTS / "reserve_readiness.py").read_text(encoding="utf-8")
        self.assertIn("reserve_intake", quelle)
        self.assertLess(quelle.index("reserve_intake.bestandsaufnahme"),
                        quelle.index("for index in rp.reserve_drafts()"),
                        "erst zurückgeben, was dem Pool gehört – dann zählen")

    def test_ki_redaktion_kann_reserve_nicht_zweitverwerten(self):
        quelle = (SCRIPTS / "ki_redaktion.py").read_text(encoding="utf-8")
        self.assertIn("reserve:\\s*true", quelle.replace("\\\\s", "\\s"),
                      "Doppelbesitz-Sperre fehlt")

    def test_jede_ablehnung_traegt_einen_grund(self):
        bericht = self.ri.bestandsaufnahme()
        for b in bericht["befunde"]:
            self.assertTrue(b.get("grund"),
                            f"{b['slug']} wurde ohne Begründung einsortiert")

    def test_angebote_werden_nicht_still_uebernommen(self):
        """KI-Redaktions-Entwürfe gehören einem Menschen, bis er abgibt."""
        bericht = self.ri.bestandsaufnahme()
        for b in bericht["angebote"]:
            self.assertNotIn(b, bericht["uebernehmbar"])


# ---------------------------------------------------------------------------
#  VORGANG WF-B594, Nachtrag 2 (05.10.2026) – zwei Lecks, die beim scharfen
#  Durchlauf der reparierten Kette auffielen und beide dieselbe Handschrift
#  tragen: Automatik fasst etwas an, das ihr nicht gehört.
#
#  B7  IDENTITÄT STATT NAMENSÄHNLICHKEIT. Das Gedächtnis des Bestands-
#      Wächters ist datumslos verschlüsselt (`schluessel()`), damit das
#      Umdatieren der Veredelungs-Stufe keine Einträge verliert. Im Bestand
#      liegen aber zwei Entwürfe mit demselben Stamm
#      (`2026-09-22-konto-karten-update-…` und `2026-09-29-…`). `--heal`
#      setzte die Reserve-Fahne am falschen von beiden: ein nie
#      übernommener Entwurf wanderte still in den Pool, das Übernahme-
#      protokoll (data/reserve-intake.json) kannte ihn nicht, und der
#      Ledger-Eintrag zeigte anschließend auf den falschen Slug.
#  B8  CTA-BLÖCKE SIND KEIN FLIESSTEXT. Mit `--file` läuft der interne
#      Linker erstmals über Reserve-Entwürfe. Beim ersten scharfen Lauf
#      setzte er zwei Links mitten in die kanonische Schnell-Tipp-Zeile –
#      genau den Block, den affiliate_integrity_gate bytegenau prüft.
# ---------------------------------------------------------------------------
class CustodyIdentitaetTests(unittest.TestCase):
    """B7: Gleicher Slug-Stamm ist nicht derselbe Artikel."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import reserve_custody as rc
        self.rc = rc
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "posts"
        self.ledger = Path(self.tmp.name) / "custody.json"
        self.posts.mkdir(parents=True)
        for slug in ("2026-09-22-konto-karten-update",
                     "2026-09-29-konto-karten-update"):
            d = self.posts / slug
            d.mkdir()
            (d / "index.md").write_text(
                '---\ntitle: "Konto & Karten-Update"\ndraft: true\n---\n\n'
                "Body.\n", encoding="utf-8")
        self.ledger.write_text(json.dumps({
            "konto-karten-update": {
                "zustand": "pool", "seit": "2026-10-01",
                "slug": "2026-09-22-konto-karten-update"}}), encoding="utf-8")

    def _heal(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            lage = self.rc.heilen(self.posts, pfad=self.ledger)
        return lage, buf.getvalue()

    def test_nur_der_gemerkte_slug_bekommt_die_fahne_zurueck(self):
        self._heal()
        richtig = (self.posts / "2026-09-22-konto-karten-update"
                   / "index.md").read_text(encoding="utf-8")
        falsch = (self.posts / "2026-09-29-konto-karten-update"
                  / "index.md").read_text(encoding="utf-8")
        self.assertIn("reserve: true", richtig)
        self.assertNotIn("reserve: true", falsch,
                         "namensgleicher Fremdentwurf wurde in den Pool gezogen")

    def test_namensgleicher_entwurf_wird_berichtet_statt_verschwiegen(self):
        lage, _ = self._heal()
        gemeldet = [e["slug"] for e in lage.get("namensgleich", [])]
        self.assertIn("2026-09-29-konto-karten-update", gemeldet)
        self.assertIn("2026-09-29-konto-karten-update",
                      self.rc.markdown(lage))

    def test_gedaechtnis_behaelt_den_richtigen_slug(self):
        self._heal()
        eintrag = json.loads(self.ledger.read_text(
            encoding="utf-8"))["konto-karten-update"]
        self.assertEqual(eintrag["slug"], "2026-09-22-konto-karten-update")

    def test_altlast_ohne_slug_bleibt_ueber_den_stamm_heilbar(self):
        self.ledger.write_text(json.dumps({
            "konto-karten-update": {"zustand": "pool", "seit": "2026-10-01"}}),
            encoding="utf-8")
        lage, _ = self._heal()
        self.assertTrue(lage["geheilt"], "Alt-Eintrag ohne Slug blieb liegen")


class LinkerCtaSperrzoneTests(unittest.TestCase):
    """B8: Werbe- und Offenlegungsblöcke sind für den Linker tabu."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import internal_linker as il
        self.il = il

    def test_schnell_tipp_zeile_ist_sperrzone(self):
        body = ("💡 **Schnell-Tipp von FranksFinanzcheck:** Zinsen auf ein "
                "kostenloses Tagesgeldkonto gibt es bei der C24 Bank: "
                "[**Jetzt ansehen**](/go/tagesgeld/)\n\n"
                "Im Fließtext darf ein Tagesgeldkonto verlinkt werden.\n")
        treffer = self.il.find_anchor(body, "Tagesgeldkonto")
        self.assertIsNotNone(treffer, "Fließtext darf nicht mitgesperrt sein")
        self.assertGreater(treffer[0], body.index("Im Fließtext"))

    def test_offenlegung_und_spar_tipp_sind_sperrzone(self):
        for zeile in (
            "> 💶 **Spar-Tipp zwischendurch:** Dein Tagesgeld bei der C24 Bank.\n",
            "_(Dieser Artikel enthält Affiliate-Links (Werbung).)_\n",
            "👉 **Jetzt das Tagesgeld-Angebot ansehen:** [**Link**](/go/tagesgeld/)\n",
        ):
            with self.subTest(zeile=zeile[:32]):
                self.assertIsNone(self.il.find_anchor(zeile, "Tagesgeld"))

    def test_selbsttest_deckt_die_sperrzone_ab(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_ = self.il.selftest()
        self.assertEqual(rc_, 0, buf.getvalue())
        self.assertIn("CTA", buf.getvalue())

    def test_reparatur_ist_im_quelltext_begruendet(self):
        quelle = (SCRIPTS / "internal_linker.py").read_text(encoding="utf-8")
        self.assertIn("WF-B594", quelle)
        self.assertIn("def cta_ranges", quelle)


class UhrZwangDerReserveWachenTests(unittest.TestCase):
    """B9: Ein Selbsttest, der die Wanduhr liest, ist eine Verabredung mit
    dem Kalender.

    Beide in diesem Vorgang neu gebauten Wachen hatten genau diese Bauart:
    Fixtures mit der echten Uhr gealtert, Erwartung gegen ein gedachtes
    Heute. Unter der CI-Probe (+97/+1461 Tage) fiel der Reserve-Aufnahme
    jeder reife Entwurf auf „unreif", und beim Aufräumer griff die Karenz
    nicht mehr – ausgerechnet die Regel, die vor unwiderruflichem Löschen
    schützt. Das Gate hat es gefangen; dieser Vertrag hält es fest.
    """

    def _trap(self, script, offset):
        sc = SCRIPTS / "selftest_clock.py"
        p = subprocess.run(
            [sys.executable, str(sc), "--trap", f"scripts/{script}",
             "--offset", str(offset), "--selftest-args=--selftest"],
            cwd=str(SCRIPTS.parent), capture_output=True, text=True)
        return p

    def test_aufnahme_ist_uhrfest(self):
        for offset in (97, 1461):
            with self.subTest(offset=offset):
                p = self._trap("reserve_intake.py", offset)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_aufraeumer_ist_uhrfest(self):
        for offset in (97, 1461):
            with self.subTest(offset=offset):
                p = self._trap("reserve_janitor.py", offset)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_fixtures_stempeln_absolut(self):
        for name in ("reserve_intake.py", "reserve_janitor.py"):
            quelle = (SCRIPTS / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIn("_stempel(", quelle,
                              "Dateialter wird nicht absolut gestempelt")
                self.assertIn("PROBETAGE", quelle,
                              "Selbsttest läuft nicht gegen feste Testdaten")
