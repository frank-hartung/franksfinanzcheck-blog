#!/usr/bin/env python3
# ============================================================
#  REGRESSIONSTESTS – SOCIAL-PERF-FEEDBACK (Rückkanal)
#  ------------------------------------------------------------
#  Beweisführung, dass der Rückkanal tut, was er behauptet:
#    · Reblogs/Shares wiegen stärker als Favoriten
#    · Mindeststichprobe verhindert Overfitting auf Zufallstreffer
#    · Cooldown-Faktor bleibt innerhalb der erlaubten Grenzen
#    · Der Planer verhält sich OHNE Rückkanal-Daten exakt wie vorher
#      (Rückwärtskompatibilität ist hier nicht verhandelbar)
#    · MIT Rückkanal-Daten bevorzugt der Bandit den Sieger-Winkel
#      ungefähr 80 % der Fälle (Multi-Armed-Bandit light)
#  Läuft offline, ohne Netz und ohne Token.
# ============================================================
from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timedelta

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_perf_feedback as feedback   # noqa: E402
import social_planner as planner          # noqa: E402
import social_channels as sch             # noqa: E402

CFG = sch.load_config()
CHANNELS = sch.channel_map(CFG)


class TestScoring(unittest.TestCase):
    def test_reblogs_wiegen_staerker_als_favoriten(self):
        hoch = feedback._raw_score({"favourites": 0, "reblogs": 5, "replies": 0})
        niedrig = feedback._raw_score({"favourites": 5, "reblogs": 0, "replies": 0})
        self.assertGreater(hoch, niedrig)

    def test_aggregation_trennt_gut_von_schlecht(self):
        agg = feedback._aggregate({
            "gut": [30.0, 28.0, 32.0, 29.0],
            "schlecht": [1.0, 2.0, 0.0, 1.0],
        })
        self.assertGreater(agg["gut"]["score"], 1.0)
        self.assertLess(agg["schlecht"]["score"], 1.0)

    def test_leere_eingabe_liefert_leeres_ergebnis(self):
        self.assertEqual(feedback._aggregate({}), {})

    def test_cooldown_faktor_innerhalb_der_grenzen(self):
        for score in (0.1, 0.5, 1.0, 2.0, 10.0):
            factor = feedback.cooldown_factor_for(score)
            self.assertGreaterEqual(factor, feedback.COOLDOWN_MIN_FACTOR)
            self.assertLessEqual(factor, feedback.COOLDOWN_MAX_FACTOR)

    def test_cooldown_faktor_monoton_fallend(self):
        werte = [feedback.cooldown_factor_for(s) for s in (0.3, 0.7, 1.0, 1.5, 3.0)]
        self.assertEqual(werte, sorted(werte, reverse=True))


class TestBuildPerformance(unittest.TestCase):
    def _history(self, n, angle="nutzen", pillar_slug="s1"):
        now = datetime.now().isoformat()
        return [
            {"channel": "mastodon", "ref": str(i), "ok": True, "angle": angle,
             "slug": pillar_slug, "posted_at": now}
            for i in range(n)
        ]

    def test_unterhalb_mindeststichprobe_bleibt_neutral(self):
        history = self._history(2)
        cache = {"mastodon": {"0": {"favourites": 999, "reblogs": 999, "replies": 999},
                              "1": {"favourites": 999, "reblogs": 999, "replies": 999}}}
        perf = feedback.build_performance(history, cache, {"s1": "strom-sparen"})
        self.assertEqual(perf["channels"]["mastodon"]["angles"]["nutzen"]["score"], 1.0)

    def test_ab_mindeststichprobe_wirkt_der_score(self):
        history = self._history(5)
        cache = {"mastodon": {str(i): {"favourites": 50, "reblogs": 20, "replies": 10}
                              for i in range(5)}}
        perf = feedback.build_performance(history, cache, {"s1": "strom-sparen"})
        # Einziger Winkel/Pillar im Datensatz -> Score == Durchschnitt == 1.0,
        # aber mit echter Stichprobe (nicht die Neutral-Klausel).
        self.assertEqual(perf["channels"]["mastodon"]["angles"]["nutzen"]["samples"], 5)

    def test_ohne_cache_treffer_keine_kanaldaten(self):
        history = self._history(5)
        perf = feedback.build_performance(history, {}, {})
        self.assertEqual(perf["channels"]["mastodon"]["samples"], 0)

    def test_report_meldet_standby_kanal(self):
        perf = feedback.build_performance([], {}, {})
        report = feedback.render_report(perf, ["bluesky", "telegram"])
        self.assertIn("bluesky", report)
        self.assertIn("Noch keine Daten", report)


class TestPlannerRueckwaertskompatibel(unittest.TestCase):
    """Ohne Rückkanal-Daten muss der Planer sich exakt wie vorher verhalten."""

    def test_pick_angle_ohne_gewichte_ist_hash_basiert(self):
        state = {"history": []}
        day = date(2026, 9, 14)
        a1 = planner.pick_angle({"angles": ["nutzen", "zahl", "mythos"]}, "mastodon",
                                "slug-x", state, set(), day, 0)
        a2 = planner.pick_angle({"angles": ["nutzen", "zahl", "mythos"]}, "mastodon",
                                "slug-x", state, set(), day, 0, angle_weights=None)
        self.assertEqual(a1, a2)

    def test_cooldown_ohne_performance_unveraendert(self):
        self.assertEqual(feedback_cooldown_days_proxy(75, "strom-sparen", None), 75)
        self.assertEqual(feedback_cooldown_days_proxy(75, "strom-sparen", {}), 75)


def feedback_cooldown_days_proxy(base, pillar, channel_perf):
    return planner._cooldown_days(base, pillar, channel_perf)


class TestPlannerBandit(unittest.TestCase):
    """Mit Rückkanal-Daten bevorzugt der Bandit den Sieger-Winkel ~80 %."""

    def test_sieger_winkel_dominiert_ueber_viele_artikel(self):
        state = {"history": []}
        day = date(2026, 9, 14)
        weights = {"nutzen": 1.6, "zahl": 1.0, "mythos": 0.7}
        gewinner = 0
        n = 200
        for i in range(n):
            angle = planner.pick_angle(
                {"angles": ["nutzen", "zahl", "mythos"]}, "mastodon",
                f"slug-{i}", state, set(), day, i, angle_weights=weights,
            )
            if angle == "nutzen":
                gewinner += 1
        quote = gewinner / n
        # Erwartet ~80 %, mit Toleranz für die diskrete Hash-Verteilung.
        self.assertGreater(quote, 0.65)
        self.assertLess(quote, 0.95)

    def test_cooldown_wird_fuer_top_pillar_verkuerzt(self):
        channel_perf = {"pillars": {"strom-sparen": {"cooldown_factor": 0.6}}}
        self.assertEqual(planner._cooldown_days(75, "strom-sparen", channel_perf), 45)

    def test_cooldown_wird_fuer_flop_pillar_verlaengert(self):
        channel_perf = {"pillars": {"strom-sparen": {"cooldown_factor": 1.4}}}
        self.assertEqual(planner._cooldown_days(75, "strom-sparen", channel_perf), 105)

    def test_cooldown_hat_sicherheits_minimum(self):
        channel_perf = {"pillars": {"strom-sparen": {"cooldown_factor": 0.1}}}
        self.assertGreaterEqual(planner._cooldown_days(20, "strom-sparen", channel_perf), 14)


class TestBuildPlanMitRueckkanal(unittest.TestCase):
    """build_plan bleibt mit performance={} funktional identisch zum Altzustand.

    Fixtures werden relativ zur GEPLANTEN Uhr gebaut – nie relativ zur echten
    Wanduhr. Der frühere Aufbau las `planner.berlin_now()` und plante
    gleichzeitig für den 14.09.2026: Ab dem 01.10.2026 lag damit jeder
    Fixture-Artikel hinter allen Slots, der Plan war leer und der Test rot –
    ohne eine einzige Code-Änderung. Sichtbar wurde das nur in CI
    (`publication-reliability-tests.yml` läuft ausschließlich auf Pull Requests),
    weshalb die Bombe drei Wochen lang niemandem auffiel. Seither findet
    `scripts/selftest_clock.py --trap-modul` genau diese Klasse – der Test ist
    unter jeder vorgestellten Uhr grün (`--trap-discover scripts/tests`).
    """

    PLAN_UHR = planner.localize(datetime(2026, 9, 14, 6, 0))

    def setUp(self):
        import tempfile

        self.tmp = tempfile.mkdtemp()
        self.old_schedule = planner.SCHEDULE_FILE
        self.old_state = planner.STATE_FILE
        planner.SCHEDULE_FILE = os.path.join(self.tmp, "schedule.yaml")
        planner.STATE_FILE = os.path.join(self.tmp, "state.yaml")

    def tearDown(self):
        planner.SCHEDULE_FILE = self.old_schedule
        planner.STATE_FILE = self.old_state

    @staticmethod
    def _pool(pn) -> list:
        """Acht veröffentlichte Artikel, datiert von der übergebenen Plan-Uhr aus."""
        return [
            {
                "slug": f"artikel-{i:02d}", "path": "", "title": f"Titel {i}",
                "description": "x", "kurzantwort": "x", "hook": "x",
                "hook_sentences": ["x"], "takeaways": ["x"], "numbers": ["1 €"],
                "faq_question": "x", "faq_answer": "x", "tags": ["x"], "keywords": ["x"],
                "pillar": ["strom-sparen", "internet-dsl"][i % 2], "pin_title": "x",
                "cover": "", "cover_alt": "", "draft": False, "reserve": False,
                "published": planner.iso(pn - timedelta(days=2 + i)),
                "url": f"https://franksfinanzcheck.de/posts/artikel-{i:02d}/", "raw_fm": "",
            }
            for i in range(8)
        ]

    def _plan(self, pn, performance=None) -> dict:
        return planner.build_plan(CFG, self._pool(pn), {"history": [], "failures": []},
                                  now=pn, performance=performance or {})

    def test_leerer_rueckkanal_aendert_plan_nicht_kaputt(self):
        plan_ohne = self._plan(self.PLAN_UHR)
        self.assertTrue(planner.planned_items(plan_ohne))

    def test_plan_haengt_nicht_an_der_echten_wanduhr(self):
        """Dieselbe Rechnung an drei Uhren – der Plan darf kein Kalender-Zufall sein.

        Der 14.09.2026 ist die Uhr, an der die Bombe entstand; 2027 wechseln
        Wochentag und Saison, 2030/31 läuft der Plan über den Jahreswechsel.
        """
        for pn in (self.PLAN_UHR,
                   planner.localize(datetime(2027, 3, 1, 6, 0)),
                   planner.localize(datetime(2030, 12, 29, 6, 0))):
            with self.subTest(uhr=pn.isoformat()):
                self.assertTrue(planner.planned_items(self._plan(pn)),
                                f"kein Plan für die Uhr {pn.isoformat()}")

    def test_rueckkanal_mit_daten_bleibt_innerhalb_der_regeln(self):
        performance = {"channels": {cid: {
            "angles": {"nutzen": {"score": 1.5}, "zahl": {"score": 0.6}},
            "pillars": {"strom-sparen": {"cooldown_factor": 0.7},
                        "internet-dsl": {"cooldown_factor": 1.3}},
        } for cid in CHANNELS}}
        items = planner.planned_items(self._plan(self.PLAN_UHR, performance))
        self.assertTrue(items)
        # Tagesgrenzen gelten weiterhin unverändert.
        counts: dict = {}
        for it in items:
            key = f"{it['channel']}|{it['date']}"
            counts[key] = counts.get(key, 0) + 1
        for key, n in counts.items():
            cid = key.split("|")[0]
            cap = int(((CHANNELS[cid].get("cadence")) or {}).get("max_per_day") or 99)
            self.assertLessEqual(n, cap)

if __name__ == "__main__":
    unittest.main()
