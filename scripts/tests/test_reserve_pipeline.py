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
import meta_optimizer as mo          # noqa: E402
import reserve_converge as rc        # noqa: E402
import reserve_finisher as rf        # noqa: E402
import reserve_gate as rg            # noqa: E402
import reserve_healer_coverage as rhc  # noqa: E402
import reserve_quarantine as rq      # noqa: E402
import reserve_stage_guard as rsg    # noqa: E402

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
        topics = [{"title": "Stromfresser finden: Die größten Energiediebe"},
                  {"title": "Reisekrankenversicherung: Das musst du wissen"}]
        bestand = {"2026-09-25-a":
                   "Stromfresser finden: So stoppst du teure Energiediebe"}
        with tempfile.TemporaryDirectory() as tmp:
            vorschlaege = self.rt.disponieren(
                topics, bestand=bestand, limit=5,
                pfad=Path(tmp) / "ledger.json")
        self.assertEqual([t["title"] for t in vorschlaege],
                         ["Reisekrankenversicherung: Das musst du wissen"])

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
        import reserve_pool as rp
        self.rp = rp

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
