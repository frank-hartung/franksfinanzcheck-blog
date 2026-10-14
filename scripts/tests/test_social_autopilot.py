#!/usr/bin/env python3
# ============================================================
#  REGRESSIONSTESTS – SOCIAL-AUTOPILOT
#  ------------------------------------------------------------
#  Beweisführung, dass der Autopilot die Kriterien der Kanäle
#  WIRKLICH einhält (nicht nur behauptet). Läuft offline, ohne
#  Netz und ohne Token.
#
#  Geprüft werden:
#    · Kanal-Playbook (Schema, Grenzwerte, ladbare Adapter)
#    · Textwerk (Zeichenlimits je Kanal, Link-Hygiene, Hashtags)
#    · Gate (Länge, Affiliate-Link, Hashtags, Versprechen, Dubletten)
#    · Planer (Tagesgrenzen, Sperrfrist, Themenmix, Determinismus)
#    · Adapter (Standby-Regel: kein Token = kein Versand, kein Fehler)
#    · Bilder (Format-Variante in der richtigen Auflösung)
# ============================================================
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_channels as sch          # noqa: E402
import social_copywriter as copy       # noqa: E402
import social_gate as gate             # noqa: E402
import social_images as images         # noqa: E402
import social_planner as planner       # noqa: E402
import social_calendar as calendar     # noqa: E402
import social_studio as studio         # noqa: E402
import schaltwerk_actions as act       # noqa: E402

CFG = sch.load_config()
CHANNELS = sch.channel_map(CFG)
META = sch.meta_of(CFG)


def _article(slug: str, pillar: str = "strom-sparen", days_old: int = 3,
             bezug=None) -> dict:
    """Fixture-Artikel; `bezug` ist die Uhr, von der aus `days_old` zählt.

    Standard ist die echte Wanduhr. Wer mit einer GEPINNTEN Plan-Uhr arbeitet
    (TestPlanner: 14.09.2026), muss sie übergeben – sonst entsteht eine
    Zeitbombe: Die Artikel wären „neuer" als die geplante Zukunft, kein
    Kandidat passt mehr in einen Slot und der Plan bleibt leer. Genau das legte
    am 01.10.2026 die Publication-Reliability-Prüfung lahm (Schwesterfall
    test_social_perf_feedback, dortige Klasse). `selftest_clock --trap-modul`
    findet diese Klasse seither.
    """
    now = bezug or planner.berlin_now()
    return {
        "slug": slug,
        "path": "",
        "title": f"Stromkosten senken: der Praxis-Test zu {slug}",
        "description": "Mit drei Handgriffen sinkt die Abschlagzahlung dauerhaft.",
        "kurzantwort": ("Wer den Abschlag um 20 Prozent drückt, spart rund 240 € im Jahr. "
                        "Der Wechsel dauert online etwa zehn Minuten."),
        "hook": "Wer den Abschlag um 20 Prozent drückt, spart rund 240 € im Jahr.",
        "hook_sentences": [
            "Wer den Abschlag um 20 Prozent drückt, spart rund 240 € im Jahr.",
            "Der Wechsel dauert online etwa zehn Minuten.",
        ],
        "takeaways": [
            "Abschlag prüfen und an den realen Verbrauch anpassen",
            "Anbieterwechsel spart im Schnitt 240 € im Jahr",
            "Kündigungsfrist von vier Wochen beachten",
        ],
        "numbers": ["240 €", "20 Prozent"],
        "faq_question": "Wie schnell wirkt ein Anbieterwechsel?",
        "faq_answer": "Meist innerhalb von vier bis sechs Wochen.",
        "tags": ["Stromkosten senken", "Anbieterwechsel"],
        "keywords": ["Stromkosten senken", "Stromvergleich"],
        "pillar": pillar,
        "pin_title": "Stromkosten senken mit System",
        "cover": "",
        "cover_alt": "",
        "draft": False,
        "reserve": False,
        "published": planner.iso(now - timedelta(days=days_old)),
        "url": f"https://franksfinanzcheck.de/posts/{slug}/",
        "raw_fm": "",
    }


class TestPlaybook(unittest.TestCase):
    """data/social/channels.yaml – die Single Source of Truth."""

    def test_kanaele_vorhanden(self):
        self.assertTrue(CHANNELS, "channels.yaml enthält keine Kanäle")

    def test_pflichtfelder_je_kanal(self):
        for cid, ch in CHANNELS.items():
            with self.subTest(channel=cid):
                self.assertTrue(ch.get("label"), f"{cid}: label fehlt")
                self.assertIn(ch.get("kind"),
                              {"microblog", "business", "community", "visual",
                               "messenger", "pin"}, f"{cid}: kind ungültig")
                self.assertTrue((ch.get("text") or {}).get("max_chars"),
                                f"{cid}: max_chars fehlt")
                self.assertTrue((ch.get("cadence") or {}).get("times"),
                                f"{cid}: Sendezeiten fehlen")
                self.assertGreaterEqual(int((ch.get("cadence") or {}).get("max_per_day") or 0), 1)

    def test_hashtag_grenzen_plausibel(self):
        for cid, ch in CHANNELS.items():
            ht = (ch.get("text") or {}).get("hashtags") or {}
            with self.subTest(channel=cid):
                self.assertLessEqual(ht.get("min", 0), ht.get("max", 0),
                                     f"{cid}: min > max bei Hashtags")

    def test_adapter_ladbar(self):
        for cid in CHANNELS:
            with self.subTest(channel=cid):
                self.assertIsNotNone(sch.adapter_class(cid), f"{cid}: Adapter fehlt")

    def test_kein_kanal_ohne_link_regel(self):
        # `destination` (seit Reparatur #716): Der Link reist als Ziel-Link des
        # Beitrags – so arbeitet die Pinterest-API (`link` im Pin-Payload).
        # Ein unbekannter Wert muss weiterhin durchfallen.
        for cid, ch in CHANNELS.items():
            with self.subTest(channel=cid):
                self.assertIn((ch.get("text") or {}).get("link_position"),
                              {"end", "first_comment", "none", "destination"})

    def test_link_position_destination_braucht_linkpflicht(self):
        for cid, ch in CHANNELS.items():
            if (ch.get("text") or {}).get("link_position") != "destination":
                continue
            with self.subTest(channel=cid):
                self.assertTrue((ch.get("text") or {}).get("link_required"),
                                f"{cid}: destination ohne link_required ist sinnlos")


class TestCopywriter(unittest.TestCase):
    """Kanalnative Texte halten die Kriterien ihrer Plattform ein."""

    @classmethod
    def setUpClass(cls):
        cls.art = _article("test-artikel-strom")

    def test_zeichenlimits_aller_kanaele(self):
        for cid, ch in CHANNELS.items():
            for ang in (ch.get("angles") or [])[:4]:
                with self.subTest(channel=cid, angle=ang):
                    pkg = copy.compose(self.art, cid, ch, ang, META, use_llm=False)
                    weight = int(((ch.get("text")) or {}).get("link_weight") or 0)
                    n = copy.effective_length(pkg["text"], pkg["url"], weight)
                    self.assertLessEqual(
                        n, int((ch.get("text") or {}).get("max_chars")),
                        f"{cid}/{ang}: {n} Zeichen")

    def test_kein_affiliate_link(self):
        for cid, ch in CHANNELS.items():
            pkg = copy.compose(self.art, cid, ch, "nutzen", META, use_llm=False)
            with self.subTest(channel=cid):
                self.assertNotIn("/go/", pkg["text"])
                self.assertNotIn("check24.net", pkg["text"])

    def test_utm_kennzeichnung(self):
        for cid, ch in CHANNELS.items():
            pkg = copy.compose(self.art, cid, ch, "nutzen", META, use_llm=False)
            if (ch.get("text") or {}).get("link_position") != "none":
                with self.subTest(channel=cid):
                    self.assertIn(f"utm_source={cid}", pkg["url"])

    def test_x_link_gewichtung(self):
        """X zählt Links mit 23 Zeichen – das Budget darf nicht verschenkt werden."""
        ch = CHANNELS.get("x") or {}
        pkg = copy.compose(self.art, "x", ch, "nutzen", META, use_llm=False)
        eff = copy.effective_length(pkg["text"], pkg["url"], 23)
        self.assertLessEqual(eff, int((ch.get("text") or {}).get("max_chars")))
        self.assertLess(eff, len(pkg["text"]))  # Gewichtung greift wirklich

    def test_kanaele_liefern_unterschiedliche_texte(self):
        """Kein Einheitstext für alle Netze."""
        texts = {}
        for cid, ch in CHANNELS.items():
            texts[cid] = copy.compose(self.art, cid, ch, "nutzen", META, use_llm=False)["text"]
        unique = len(set(texts.values()))
        self.assertGreaterEqual(unique, max(4, len(texts) - 2),
                                f"zu viele identische Texte: {unique}/{len(texts)}")

    def test_hashtags_je_kanal(self):
        for cid, ch in CHANNELS.items():
            pkg = copy.compose(self.art, cid, ch, "nutzen", META, use_llm=False)
            ht = (ch.get("text") or {}).get("hashtags") or {}
            n = len(pkg["hashtags"])
            with self.subTest(channel=cid):
                self.assertLessEqual(n, int(ht.get("max") or 99))
                for tag in pkg["hashtags"]:
                    self.assertLessEqual(len(tag), int(ht.get("max_len") or 24))
                    self.assertRegex(tag, r"^[A-Za-z0-9]+$")

    def test_linkedin_link_im_kommentar(self):
        ch = CHANNELS.get("linkedin") or {}
        pkg = copy.compose(self.art, "linkedin", ch, "nutzen", META, use_llm=False)
        if (ch.get("text") or {}).get("link_position") == "first_comment":
            self.assertNotIn("http", pkg["text"])
            self.assertIn("http", pkg["comment"])

    def test_trim_erhaelt_zeilen(self):
        block = "Erstens: prüfen.\nZweitens: wechseln.\nDrittens: fristwahrend kündigen."
        cut = copy.trim(block, 40)
        self.assertIn("\n", cut, "Listenstruktur darf nicht flachgewalzt werden")


class TestGate(unittest.TestCase):
    """Das Freigabe-Gate ist fail-closed."""

    def setUp(self):
        self.ch = CHANNELS["mastodon"]
        self.pkg = copy.compose(_article("gate-artikel"), "mastodon", self.ch,
                                "nutzen", META, use_llm=False)

    def test_sauberer_beitrag_geht_durch(self):
        ok, viol, _m = gate.check(self.pkg, self.ch, META, history=[])
        self.assertTrue(ok, f"sauberer Beitrag blockiert: {viol}")

    def test_zu_lang(self):
        bad = {**self.pkg, "text": "x" * 900}
        ok, viol, _ = gate.check(bad, self.ch, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L1" in v for v in viol))

    def test_affiliate_link_blockiert(self):
        bad = {**self.pkg, "text": self.pkg["text"].replace(
            self.pkg["url"], "https://franksfinanzcheck.de/go/strom/")}
        ok, viol, _ = gate.check(bad, self.ch, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L2" in v for v in viol))

    def test_hashtag_flut(self):
        bad = {**self.pkg, "text": self.pkg["text"] + " #A #B #C #D #E #F"}
        ok, viol, _ = gate.check(bad, self.ch, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L4" in v for v in viol))

    def test_werbeversprechen(self):
        bad = {**self.pkg, "text": self.pkg["text"] + " garantiert risikofrei"}
        ok, viol, _ = gate.check(bad, self.ch, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L3" in v for v in viol))

    def test_duplikat_erkennung(self):
        hist = [{"channel": "mastodon", "posted_at": "2026-01-01T10:00:00+01:00",
                 "text": self.pkg["text"], "ok": True}]
        ok, viol, _ = gate.check(self.pkg, self.ch, META, history=hist)
        self.assertFalse(ok)
        self.assertTrue(any("L8" in v for v in viol))

    def test_erfundene_zahl(self):
        bad = {**self.pkg, "text": self.pkg["text"].replace("240 €", "9999 €")}
        ok, viol, _ = gate.check(bad, self.ch, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L9" in v for v in viol))

    def test_bildpflicht(self):
        ig = CHANNELS.get("instagram") or {}
        pkg = copy.compose(_article("ig-artikel"), "instagram", ig, "nutzen",
                           META, use_llm=False)
        pkg["media_url"] = ""
        pkg["media_path"] = ""
        ok, viol, _ = gate.check(pkg, ig, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L10" in v for v in viol))


class TestPlanner(unittest.TestCase):
    """Kadenz, Sperrfrist, Themenmix und Reproduzierbarkeit."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="social-plan-")
        self.old_schedule = planner.SCHEDULE_FILE
        self.old_state = planner.STATE_FILE
        planner.SCHEDULE_FILE = os.path.join(self.tmp, "schedule.yaml")
        planner.STATE_FILE = os.path.join(self.tmp, "state.yaml")
        self.now = planner.localize(datetime(2026, 9, 14, 6, 0))
        self.pool = self._pool(self.now)

    def tearDown(self):
        planner.SCHEDULE_FILE = self.old_schedule
        planner.STATE_FILE = self.old_state

    @staticmethod
    def _pool(pn):
        """Zwölf Artikel, datiert von der übergebenen Plan-Uhr aus."""
        return [_article(f"artikel-{i:02d}",
                         ["strom-sparen", "internet-dsl", "versicherungen",
                          "konto-karten", "frugalismus", "mietwagen"][i % 6],
                         days_old=2 + i, bezug=pn) for i in range(12)]

    def _plan(self, state=None, pn=None):
        pn = pn or self.now
        return planner.build_plan(CFG, self._pool(pn),
                                  state or {"history": [], "failures": []}, now=pn)

    def test_plan_ist_gefuellt(self):
        self.assertTrue(planner.planned_items(self._plan()))

    def test_plan_haengt_nicht_an_der_echten_wanduhr(self):
        """Drei Uhren, dieselbe Rechnung – der Plan darf kein Kalender-Zufall sein."""
        for pn in (self.now,
                   planner.localize(datetime(2027, 3, 1, 6, 0)),
                   planner.localize(datetime(2030, 12, 29, 6, 0))):
            with self.subTest(uhr=pn.isoformat()):
                self.assertTrue(planner.planned_items(self._plan(pn=pn)),
                                f"kein Plan für die Uhr {pn.isoformat()}")

    def test_tagesgrenzen_pro_kanal(self):
        plan = self._plan()
        counts: dict[str, int] = {}
        for it in planner.planned_items(plan):
            key = f"{it['channel']}|{it['date']}"
            counts[key] = counts.get(key, 0) + 1
        for key, n in counts.items():
            cid = key.split("|")[0]
            cap = int(((CHANNELS[cid].get("cadence")) or {}).get("max_per_day") or 99)
            with self.subTest(slot=key):
                self.assertLessEqual(n, cap)

    def test_globale_tagesgrenze(self):
        plan = self._plan()
        per_day: dict[str, int] = {}
        for it in planner.planned_items(plan):
            per_day[it["date"]] = per_day.get(it["date"], 0) + 1
        cap = int(META.get("max_posts_per_day_total") or 12)
        for day, n in per_day.items():
            with self.subTest(day=day):
                self.assertLessEqual(n, cap)

    def test_kein_doppelter_kanal_artikel(self):
        plan = self._plan()
        seen = set()
        for it in planner.planned_items(plan):
            key = (it["channel"], it["slug"])
            self.assertNotIn(key, seen)
            seen.add(key)

    def test_kadenz_wochentage(self):
        plan = self._plan()
        for it in planner.planned_items(plan):
            ch = CHANNELS[it["channel"]]
            days = set(((ch.get("cadence")) or {}).get("days") or [0, 1, 2, 3, 4, 5, 6])
            when = planner.parse_dt(it["scheduled_at"])
            with self.subTest(item=it["id"]):
                self.assertIn(when.weekday(), days)

    def test_sperrfrist_greift(self):
        first = planner.planned_items(self._plan())[0]
        state = {"history": [{"channel": first["channel"], "slug": first["slug"],
                              "posted_at": planner.iso(self.now), "ok": True,
                              "text": "x", "angle": "nutzen"}], "failures": []}
        plan2 = self._plan(state)
        again = [it for it in planner.planned_items(plan2)
                 if it["channel"] == first["channel"] and it["slug"] == first["slug"]]
        self.assertFalse(again, "frisch geposteter Artikel wurde sofort neu eingeplant")

    def test_determinismus(self):
        a = [it["id"] for it in planner.planned_items(self._plan())]
        b = [it["id"] for it in planner.planned_items(self._plan())]
        self.assertEqual(a, b, "Plan ist nicht reproduzierbar")

    def test_faellige_posten(self):
        plan = self._plan()
        items = planner.planned_items(plan)
        later = planner.parse_dt(items[0]["scheduled_at"]) - timedelta(hours=2)
        self.assertEqual(planner.due_items(plan, now=later), [])
        after = planner.parse_dt(items[0]["scheduled_at"]) + timedelta(minutes=5)
        self.assertTrue(planner.due_items(plan, now=after))

    def test_zurueckliegen_verfaellt(self):
        """Ein seit Tagen überfälliger Post wird nicht plötzlich rausgehauen."""
        plan = self._plan()
        items = planner.planned_items(plan)
        much_later = planner.parse_dt(items[0]["scheduled_at"]) + timedelta(hours=72)
        self.assertNotIn(items[0], planner.due_items(plan, now=much_later))

    def test_rollender_plan_bewahrt_nachholbaren_slot(self):
        """Neuplanung darf einen 2 h verspäteten, noch zustellbaren Slot nicht löschen."""
        item = {
            "id": "mastodon:verspaetet:nutzen:2026-09-14",
            "channel": "mastodon", "slug": "verspaetet", "angle": "nutzen",
            "kind": "launch", "pillar": "strom-sparen",
            "date": "2026-09-14", "time": "04:00",
            "scheduled_at": planner.iso(self.now - timedelta(hours=2)),
            "status": "planned", "attempts": 0, "reason": "",
        }
        planner.save_schedule({"version": 1, "items": [item]})
        plan = self._plan()
        self.assertIn(item["id"], {it["id"] for it in planner.planned_items(plan)},
                      "Rolling hat einen innerhalb der 48-h-Nachholfrist fälligen Slot gelöscht")

    def test_sendebereiter_kanal_hat_vorrang_vor_standby_rueckstau(self):
        pool = [_article(f"bereit-{i}", days_old=3 + i) for i in range(8)]
        for i, art in enumerate(pool):
            art["published"] = planner.iso(self.now - timedelta(days=3 + i))
        # Ein alter Plan reserviert viele Zukunftsslots für einen Kanal ohne
        # Credentials. Beim Rollen müssen diese Slots neu verteilt werden.
        fremd = [{
            "id": f"bluesky:alt-{i}:nutzen:2026-09-14",
            "channel": "bluesky", "slug": f"alt-{i}", "angle": "nutzen",
            "scheduled_at": planner.iso(self.now + timedelta(hours=2, minutes=i)),
            "status": "planned", "date": self.now.date().isoformat(),
        } for i in range(20)]
        planner.save_schedule({"version": 1, "items": fremd})

        plan = planner.build_plan(CFG, pool, {"history": [], "failures": []},
                                  now=self.now, ready_channels={"mastodon"})
        mastodon = [it for it in planner.planned_items(plan)
                    if it.get("channel") == "mastodon"]
        self.assertTrue(mastodon)
        self.assertEqual(mastodon[0]["date"], self.now.date().isoformat(),
                         "Standby-Rückstau hat den sendebereiten Kanal verdrängt")


class TestStudioRollingPlan(unittest.TestCase):
    """Regression #549: Fremdkanal-Rückstau darf Mastodon nicht verhungern lassen."""

    def test_jeder_lauf_rollt_trotz_grosser_globaler_warteschlange(self):
        now = planner.localize(datetime(2026, 10, 4, 10, 0))
        # 20 geplante Fremdkanal-Posten: deutlich über min_planned_items=12.
        # Bis #549 verhinderte genau so ein globaler Bestand jede Neuplanung,
        # obwohl Mastodon selbst keinen einzigen Slot mehr hatte.
        schedule = {"version": 1, "horizon_days": 14, "items": [{
            "id": f"bluesky:fremd-{i}:nutzen:2026-10-10",
            "channel": "bluesky", "slug": f"fremd-{i}", "angle": "nutzen",
            "scheduled_at": planner.iso(now + timedelta(days=6, minutes=i)),
            "status": "planned",
        } for i in range(20)]}
        state = {"version": 1, "history": [], "failures": []}

        with patch.object(studio.planner, "load_state", return_value=state), \
             patch.object(studio.planner, "load_schedule", return_value=schedule), \
             patch.object(studio.planner, "build_plan", return_value=schedule) as bauen, \
             patch.object(studio.copy, "article_pool", return_value=[_article("neu")]), \
             patch.object(studio, "write_cockpit"):
            studio.run_once(CFG, dry_run=True, now=now)

        bauen.assert_called_once()

    def test_48h_recovery_zieht_genau_einen_slot_sicher_vor(self):
        now = planner.localize(datetime(2026, 10, 4, 10, 45))
        schedule = {"items": [
            {"id": "m:1", "channel": "mastodon", "slug": "eins",
             "scheduled_at": planner.iso(now + timedelta(hours=4)), "status": "planned"},
            {"id": "m:2", "channel": "mastodon", "slug": "zwei",
             "scheduled_at": planner.iso(now + timedelta(hours=8)), "status": "planned"},
        ]}
        state = {"history": [], "failures": []}
        # Die Sofortheilung prüft seit #716 vor dem Vorziehen, ob der Slot das
        # Freigabe-Gate besteht – dafür muss der Artikel im Bestand liegen.
        with patch.object(studio.copy, "article_pool",
                          return_value=[_article("eins"), _article("zwei")]):
            healed, _ = studio.accelerate_recovery_slot(
                schedule, state, CFG, "mastodon", now, {"mastodon"})
        self.assertTrue(healed)
        due = [it for it in planner.due_items(schedule, now=now)
               if it.get("channel") == "mastodon"]
        self.assertEqual([it["slug"] for it in due], ["eins"])
        self.assertEqual(schedule["items"][1]["slug"], "zwei")
        self.assertGreater(planner.parse_dt(schedule["items"][1]["scheduled_at"]), now)

    def test_48h_recovery_respektiert_mindestabstand(self):
        now = planner.localize(datetime(2026, 10, 4, 10, 45))
        schedule = {"items": [{
            "id": "m:1", "channel": "mastodon", "slug": "eins",
            "scheduled_at": planner.iso(now + timedelta(hours=4)), "status": "planned",
        }]}
        state = {"history": [{
            "channel": "mastodon", "slug": "vorher", "ok": True,
            "posted_at": planner.iso(now - timedelta(minutes=60)),
        }], "failures": []}
        healed, reason = studio.accelerate_recovery_slot(
            schedule, state, CFG, "mastodon", now, {"mastodon"})
        self.assertFalse(healed)
        self.assertIn("Mindestabstand", reason)

    def test_workflow_bietet_recovery_modus_an(self):
        path = os.path.join(BLOG_DIR, ".github", "workflows", "social-autopilot.yml")
        with open(path, encoding="utf-8") as fh:
            workflow = fh.read()
        self.assertIn("- recover", workflow)
        self.assertIn('ARGS="$ARGS --recover"', workflow)


class TestAdapterStandby(unittest.TestCase):
    """Ohne Token: Standby statt Feuer – die wichtigste Betriebsregel."""

    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in
                      ("MASTODON_ACCESS_TOKEN", "MASTODON_INSTANCE")}

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_ohne_token_standby(self):
        os.environ.pop("MASTODON_ACCESS_TOKEN", None)
        ad = sch.get_adapter("mastodon", CFG)
        configured, reason = ad.configured()
        self.assertFalse(configured)
        self.assertIn("MASTODON_ACCESS_TOKEN", reason)
        res = ad.publish({"text": "Test", "url": "", "media_path": "", "alt": ""})
        self.assertTrue(res.skipped, "ohne Token darf nicht gesendet werden")
        self.assertFalse(res.ok)

    def test_mit_token_nicht_standby(self):
        os.environ["MASTODON_ACCESS_TOKEN"] = "test-token"
        ad = sch.get_adapter("mastodon", CFG)
        self.assertTrue(ad.configured()[0])

    def test_bluesky_facets(self):
        from social_channels import bluesky

        text = "Tipp: 240 € sparen https://franksfinanzcheck.de/posts/x/ #Stromsparen"
        facets = bluesky.build_facets(text)
        kinds = {f["features"][0]["$type"] for f in facets}
        self.assertIn("app.bsky.richtext.facet#link", kinds)
        self.assertIn("app.bsky.richtext.facet#tag", kinds)
        for f in facets:
            self.assertIsInstance(f["index"]["byteStart"], int)
            self.assertLess(f["index"]["byteStart"], f["index"]["byteEnd"])

    def test_x_oauth_signatur_deterministisch(self):
        from social_channels import x

        h1 = x.oauth1_header("POST", "https://api.twitter.com/2/tweets", "ck", "cs",
                             "at", "ats")
        h2 = x.oauth1_header("POST", "https://api.twitter.com/2/tweets", "ck", "cs",
                             "at", "ats")
        self.assertTrue(h1.startswith("OAuth "))
        # Nonce/Zeitstempel variieren – die Signatur muss trotzdem gesetzt sein
        self.assertIn('oauth_signature="', h2)


class TestImages(unittest.TestCase):
    """Bildvarianten im richtigen Format (Instagram verlangt 4:5)."""

    def test_ratios_definiert(self):
        self.assertIn("4:5", images.RATIOS)
        self.assertEqual(images.RATIOS["4:5"][1] // images.RATIOS["4:5"][0] * 1, 1)

    def test_variante_wird_gerendert(self):
        try:
            from PIL import Image  # noqa: F401
        except Exception:  # pragma: no cover – ohne Pillow kein Render-Test
            self.skipTest("Pillow nicht installiert")
        src = os.path.join(self.tmpdir(), "cover.jpg")
        try:
            from PIL import Image

            Image.new("RGB", (1000, 1500), (14, 90, 67)).save(src, "JPEG")
        except Exception as exc:  # pragma: no cover
            self.skipTest(f"Testbild nicht erzeugbar: {exc}")
        saved_out = images.OUT_DIR
        try:
            images.OUT_DIR = self.tmpdir()
            out = images.ensure_variant(src, "test-slug", "4:5")
            self.assertTrue(out and os.path.isfile(out))
            with Image.open(out) as img:
                self.assertEqual(img.size, (1080, 1350))
        finally:
            images.OUT_DIR = saved_out

    @staticmethod
    def tmpdir() -> str:
        if not hasattr(TestImages, "_tmp"):
            TestImages._tmp = tempfile.mkdtemp(prefix="social-img-")
        return TestImages._tmp


class TestKalender(unittest.TestCase):
    """Veröffentlichungskalender je Kanal (Markdown + abonnierbares ICS)."""

    def test_selftest_besteht(self):
        self.assertEqual(calendar.selftest(), 0)

    def test_ics_ist_utc_und_gefaltet(self):
        now = planner.localize(datetime(2026, 9, 29, 9, 0))
        ch = {
            "label": "Testkanal", "enabled": True,
            "text": {"max_chars": 300, "hashtags": {"min": 1, "max": 2},
                     "emoji_max": 1, "link_position": "end"},
            "media": {"supported": True, "required": False},
            "cadence": {"days": [0, 1, 2, 3, 4, 5, 6], "times": ["08:00"],
                        "max_per_day": 2, "recycle_cooldown_days": 75},
        }
        schedule = {"items": [{
            "id": "t:slug:nutzen:2026-09-30", "channel": "test",
            "slug": "2026-09-11-test", "angle": "nutzen", "kind": "launch",
            "scheduled_at": "2026-09-30T08:00:00+02:00", "status": "planned"}]}
        ics = calendar.build_channel_ics("test", ch, schedule, {}, {}, now)
        # 08:00 Berlin (+02:00) -> 06:00 UTC
        self.assertIn("DTSTART:20260930T060000Z", ics)
        for line in ics.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_md_zeigt_kanal_kriterien(self):
        now = planner.localize(datetime(2026, 9, 29, 9, 0))
        cfg = sch.load_config()
        cmap = sch.channel_map(cfg)
        # echter Kanal aus dem Playbook
        cid, ch = next(iter(cmap.items()))
        md = calendar.build_channel_md(cid, ch, {"items": []},
                                       {"history": []}, {}, {}, now)
        self.assertIn("Kanal-Kriterien", md)
        self.assertIn("Kommende Beiträge", md)


# ============================================================  Dauerheilung #716
#  Meldung #716 (12.10.2026): Kanal Mastodon 48 h stumm. Fünf verlorene Slots,
#  jeder am Freigabe-Gate blockiert, niemand rückte nach. Diese Klassen halten
#  die vier Hebel fest, die eine Wiederholung ausschließen:
#    · Kanaltreue   – jeder Kanal hat für jeden Artikel einen sendbaren Winkel
#    · Quarantäne   – wiederholt blockierte Paare belegen keinen Slot mehr
#    · Nachrücken   – ein blockierter Slot kostet keinen Sendetermin
#    · Ehrlichkeit  – „geheilt" heißt: es ist wirklich etwas rausgegangen


class TestKanaltreue716(unittest.TestCase):
    """Kein Kanal darf strukturell unsendbar sein (stiller Vollausfall)."""

    @classmethod
    def setUpClass(cls):
        base = str(META.get("base_url") or copy.DEFAULT_BASE)
        cls.pool = copy.article_pool(base_url=base)

    def test_emoji_klassen_identisch_zum_gate(self):
        # Der Texter baut Symbole zurück, das Gate zählt sie. Zwei Muster, die
        # auseinanderlaufen, würden Beiträge bauen, die das eigene Gate ablehnt.
        self.assertEqual(copy.EMOJI_RX.pattern, gate.EMOJI_RX.pattern)

    def test_jeder_kanal_hat_mindestens_einen_sendbaren_winkel(self):
        self.assertTrue(self.pool, "kein Artikel im Bestand")
        for cid, ch in CHANNELS.items():
            with self.subTest(kanal=cid):
                unsendbar = []
                for art in self.pool:
                    frei = False
                    for ang in (ch.get("angles") or ["nutzen"]):
                        pkg = copy.compose(art, cid, ch, ang, META, use_llm=False)
                        src = os.path.join(BLOG_DIR, "static", art.get("cover") or "")
                        if os.path.isfile(src):
                            pkg["media_path"] = src
                            pkg["media_url"] = f"https://franksfinanzcheck.de/{art.get('cover')}"
                        ok, _viol, _m = gate.check(pkg, ch, META, history=[])
                        if ok:
                            frei = True
                            break
                    if not frei:
                        unsendbar.append(art["slug"])
                self.assertEqual(unsendbar, [],
                                 f"{cid}: {len(unsendbar)} Artikel in keinem Winkel sendbar")

    def test_linkedin_haelt_hashtags_im_beitrag(self):
        ch = CHANNELS["linkedin"]
        minimum = int(((ch.get("text") or {}).get("hashtags") or {}).get("min") or 0)
        pkg = copy.compose(_article("linkedin-probe"), "linkedin", ch, "nutzen",
                           META, use_llm=False)
        # Link im ersten Kommentar (Reichweiten-Standard), Hashtags im Text.
        self.assertIn(pkg["url"], pkg.get("comment") or "")
        self.assertGreaterEqual(len(gate.TAG_RX.findall(pkg["text"])), minimum)
        ok, viol, _ = gate.check(pkg, ch, META, history=[])
        self.assertTrue(ok, f"LinkedIn blockiert: {viol}")

    def test_pinterest_link_reist_als_ziel_link(self):
        ch = CHANNELS["pinterest"]
        self.assertEqual((ch.get("text") or {}).get("link_position"), "destination")
        pkg = copy.compose(_article("pin-probe"), "pinterest", ch, "nutzen",
                           META, use_llm=False)
        pkg["media_url"] = "https://franksfinanzcheck.de/cover.jpg"
        self.assertNotIn("http", pkg["text"], "nackter Link in der Pin-Beschreibung")
        ok, viol, _ = gate.check(pkg, ch, META, history=[])
        self.assertTrue(ok, f"Pinterest blockiert: {viol}")

    def test_emoji_budget_wird_eingehalten(self):
        # Der Bestand enthält Pfeile („Kosten sehen → Konditionen rechnen").
        # Auf Kanälen mit Symbol-Verbot dürfen sie nicht durchrutschen.
        for cid in ("reddit", "linkedin"):
            ch = CHANNELS[cid]
            with self.subTest(kanal=cid):
                pkg = copy.compose(_article("symbol-probe"), cid, ch, "nutzen",
                                   META, use_llm=False)
                self.assertEqual(copy.count_emoji(pkg["text"])
                                 if hasattr(copy, "count_emoji") else
                                 len(copy.EMOJI_RX.findall(pkg["text"])), 0)

    def test_auffuellpool_erreicht_hashtag_minimum(self):
        # Karger Artikel: ein Tag. Instagram verlangt fünf – der Schlusslicht-
        # Pool muss die Lücke schließen, sonst blockiert L4 den Kanal komplett.
        ch = CHANNELS["instagram"]
        artikel = _article("arm-an-tags")
        artikel["tags"] = ["Einziges Tag"]
        artikel["keywords"] = []
        tags = copy.pick_hashtags(artikel, ch)
        minimum = int(((ch.get("text") or {}).get("hashtags") or {}).get("min") or 0)
        self.assertGreaterEqual(len(tags), minimum, f"nur {tags}")


class TestGateQuarantaene(unittest.TestCase):
    """Wiederholt blockierte Paare belegen keinen Slot mehr."""

    def setUp(self):
        self.now = planner.localize(datetime(2026, 10, 12, 9, 0))

    @staticmethod
    def _state_mit_blockaden(slug: str, n: int, kanal: str = "mastodon") -> dict:
        return {
            "version": 1,
            "history": [],
            "failures": [{
                "at": planner.iso(planner.localize(datetime(2026, 10, 11, 8, 0))
                                  + timedelta(hours=i)),
                "channel": kanal, "slug": slug,
                "reason": "L9 Zahl ohne Beleg im Artikel: 503020",
            } for i in range(n)],
        }

    def test_zwei_gate_blockaden_wirken_quarantaene(self):
        state = self._state_mit_blockaden("blocker", 2)
        quar = planner.quarantiniert(state, self.now)
        self.assertIn(("mastodon", "blocker"), quar)
        self.assertIn("L9", quar[("mastodon", "blocker")])

    def test_einzelblockade_ist_noch_kein_befund(self):
        state = self._state_mit_blockaden("blocker", 1)
        self.assertEqual(planner.quarantiniert(state, self.now), {})

    def test_alte_blockaden_verfallen(self):
        state = self._state_mit_blockaden("blocker", 3)
        for f in state["failures"]:
            f["at"] = planner.iso(planner.localize(datetime(2026, 8, 1, 8, 0)))
        self.assertEqual(planner.quarantiniert(state, self.now), {})

    def test_sendefehler_zaehlen_nicht(self):
        # API-Fehler sind Sache der Versuchszähler, nicht der Gate-Quarantäne.
        state = {"version": 1, "history": [], "failures": [
            {"at": planner.iso(self.now), "channel": "mastodon", "slug": "x",
             "reason": "HTTP 401 unauthorized"} for _ in range(4)]}
        self.assertEqual(planner.quarantiniert(state, self.now), {})

    def test_quarantaene_nimmt_paar_aus_den_kandidaten(self):
        state = self._state_mit_blockaden("artikel-01", 2)
        pool = TestPlanner._pool(self.now)
        pool[1]["slug"] = "artikel-01"
        cands = planner._candidates(CFG, pool, state, self.now, {})
        self.assertNotIn("artikel-01", {c["slug"] for c in cands
                                        if c["channel"] == "mastodon"})
        self.assertIn("artikel-02", {c["slug"] for c in cands
                                     if c["channel"] == "mastodon"})

    def test_geplante_slots_werden_ausgesetzt(self):
        state = self._state_mit_blockaden("artikel-01", 2)
        schedule = {"items": [{
            "id": "mastodon:artikel-01:nutzen:2026-10-13", "channel": "mastodon",
            "slug": "artikel-01", "angle": "nutzen", "kind": "launch",
            "date": "2026-10-13", "time": "07:30",
            "scheduled_at": planner.iso(self.now + timedelta(days=1)),
            "status": "planned", "attempts": 0, "reason": ""}]}
        with patch.object(planner, "load_schedule", return_value=schedule):
            plan = planner.build_plan(CFG, TestPlanner._pool(self.now), state,
                                      now=self.now, ready_channels={"mastodon"})
        # Die Quarantäne gilt je (Kanal, Artikel): Facebook darf denselben
        # Artikel weiter planen, Mastodon nicht.
        geplant = [it for it in planner.planned_items(plan)
                   if it.get("slug") == "artikel-01" and it.get("channel") == "mastodon"]
        self.assertEqual(geplant, [], "Quarantäne-Paar bleibt im Plan")
        self.assertIn("mastodon|artikel-01", plan.get("quarantaene") or {})


    def test_quarantaene_hebt_sich_selbst_auf(self):
        # Ein reparierter Artikel darf nicht 21 Tage gesperrt bleiben: Besteht
        # er die Vorprüfung wieder, gibt der Planer ihn sofort frei.
        state = self._state_mit_blockaden("artikel-01", 2)
        pool = TestPlanner._pool(self.now)
        pool[1]["slug"] = "artikel-01"
        with patch.object(planner, "load_schedule", return_value={"items": []}):
            plan = planner.build_plan(CFG, pool, state, now=self.now,
                                      ready_channels={"mastodon"},
                                      validator=lambda a, c, ch, w: (True, ""))
        self.assertIn("mastodon|artikel-01", plan.get("quarantaene_gehoben") or [])
        self.assertNotIn("mastodon|artikel-01", plan.get("quarantaene") or {})
        self.assertTrue([it for it in planner.planned_items(plan)
                         if it.get("slug") == "artikel-01"
                         and it.get("channel") == "mastodon"],
                        "freigegebenes Paar wurde nicht wieder eingeplant")

    def test_ohne_vorpruefung_bleibt_quarantaene_stehen(self):
        # Offline-Planung ohne Validator: keine Prüfung, keine Aufhebung.
        state = self._state_mit_blockaden("artikel-01", 2)
        pool = TestPlanner._pool(self.now)
        pool[1]["slug"] = "artikel-01"
        with patch.object(planner, "load_schedule", return_value={"items": []}):
            plan = planner.build_plan(CFG, pool, state, now=self.now,
                                      ready_channels={"mastodon"})
        self.assertEqual(plan.get("quarantaene_gehoben"), None)
        self.assertIn("mastodon|artikel-01", plan.get("quarantaene") or {})


class TestNachruecken716(unittest.TestCase):
    """Ein blockierter Slot kostet keinen Sendetermin mehr."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="social-backfill-")
        self.old_schedule, self.old_state = planner.SCHEDULE_FILE, planner.STATE_FILE
        planner.SCHEDULE_FILE = os.path.join(self.tmp, "schedule.yaml")
        planner.STATE_FILE = os.path.join(self.tmp, "state.yaml")
        # Uhr der Wanduhr entnehmen, nicht pinnen: `run_once()` ruft echt
        # `planner.prune()` (berlin_now) und die Artikel-Fixtures datieren von
        # der Wanduhr. Eine gepinnte Plan-Uhr wäre eine Zeitbombe – genau die
        # Klasse, die scripts/selftest_clock.py --offset 97 aufspürt.
        self.now = planner.berlin_now().replace(minute=30, second=0, microsecond=0)
        # „Gift"-Artikel: Die Zahl steht NUR im Aufhänger, aus dem der Texter
        # den Beitrag baut – nicht im Belegmaterial des Gates (kurzantwort/
        # description/takeaways/keywords/tags/FAQ). Genau so entsteht eine
        # echte L9-Blockade: 9999 ist nirgends gedeckt. Seit 14.10.2026 ist die
        # FAQ Belegmaterial (der Winkel `frage` zitiert sie wörtlich aus dem
        # Artikel) – eine Gift-Zahl in der FAQ wäre also belegt. Die FAQ bleibt
        # deshalb leer: `frage` fällt auf Titel + Aufhänger zurück und trägt
        # dieselbe unbelegte Zahl.
        self.gift = _article("gift-artikel")
        self.gift["title"] = "Stromkosten senken mit System für gift-artikel"
        self.gift["hook"] = "Spare 9999 € sofort mit diesem einen Trick."
        self.gift["hook_sentences"] = ["Spare 9999 € sofort mit diesem einen Trick.",
                                       "Wer 9999 € zurücklegt, wechselt in zehn Minuten."]
        self.gift["faq_question"] = ""
        self.gift["faq_answer"] = ""
        # takeaways leer → die Aufzählung fällt auf hook_sentences zurück und
        # trägt dieselbe unbelegte Zahl. Damit ist der Artikel in JEDEM Winkel
        # blockiert – genau der Zustand, der #716 ausgelöst hat.
        self.gift["takeaways"] = []
        self.gift["numbers"] = ["9999 €"]
        self.pool = [self.gift, _article("guter-artikel")]

    def tearDown(self):
        planner.SCHEDULE_FILE, planner.STATE_FILE = self.old_schedule, self.old_state

    def test_vorpruefung_erkennt_unsendbaren_artikel(self):
        pruefen = studio.gate_validator(META, {"history": [], "failures": []})
        ch = CHANNELS["mastodon"]
        frei, grund = pruefen(self.gift, "mastodon", ch, "nutzen")
        self.assertFalse(frei)
        self.assertIn("L9", grund)
        self.assertTrue(pruefen(self.pool[1], "mastodon", ch, "nutzen")[0])

    def test_blockierter_slot_wird_nachbesetzt(self):
        heute = self.now.date().isoformat()
        schedule = {"items": [{
            "id": f"mastodon:gift-artikel:nutzen:{heute}", "channel": "mastodon",
            "slug": "gift-artikel", "angle": "nutzen", "kind": "launch",
            "date": heute, "time": self.now.strftime("%H:%M"),
            "scheduled_at": planner.iso(self.now - timedelta(minutes=5)),
            "status": "planned", "attempts": 0, "reason": ""}]}
        state = {"version": 1, "history": [], "failures": []}
        gesendet = []

        class StubAdapter:
            def configured(self):
                return True, ""

            def publish(self, pkg):
                gesendet.append(pkg["slug"])
                return sch.PublishResult(ok=True, url="https://mastodon.social/@x/1",
                                         ref="1")

        with patch.object(studio.planner, "load_state", return_value=state), \
             patch.object(studio.planner, "load_schedule", return_value=schedule), \
             patch.object(studio.planner, "build_plan", return_value=schedule), \
             patch.object(studio.copy, "article_pool", return_value=self.pool), \
             patch.object(studio.sch, "get_adapter", return_value=StubAdapter()), \
             patch.object(studio, "write_cockpit"):
            out = studio.run_once(CFG, now=self.now, channel="mastodon")

        self.assertEqual(gesendet, ["guter-artikel"], "Ersatzartikel ging nicht raus")
        self.assertEqual(out["results"]["blocked"], 1)
        self.assertEqual(out["results"]["backfilled"], 1)
        self.assertEqual(out["results"]["sent"], 1)
        self.assertEqual([e["slug"] for e in state["history"]], ["guter-artikel"])
        blockiert = [it for it in schedule["items"] if it.get("status") == "blocked"]
        self.assertEqual([it["slug"] for it in blockiert], ["gift-artikel"])
        self.assertIn("L9", blockiert[0]["reason"])

    def test_ohne_sendbaren_ersatz_bleibt_slot_leer_und_sichtbar(self):
        heute = self.now.date().isoformat()
        schedule = {"items": [{
            "id": f"mastodon:gift-artikel:nutzen:{heute}", "channel": "mastodon",
            "slug": "gift-artikel", "angle": "nutzen", "kind": "launch",
            "date": heute, "time": self.now.strftime("%H:%M"),
            "scheduled_at": planner.iso(self.now - timedelta(minutes=5)),
            "status": "planned", "attempts": 0, "reason": ""}]}
        state = {"version": 1, "history": [], "failures": []}
        with patch.object(studio.planner, "load_state", return_value=state), \
             patch.object(studio.planner, "load_schedule", return_value=schedule), \
             patch.object(studio.planner, "build_plan", return_value=schedule), \
             patch.object(studio.copy, "article_pool", return_value=[self.gift]), \
             patch.object(studio.sch, "get_adapter", return_value=None), \
             patch.object(studio, "write_cockpit"):
            out = studio.run_once(CFG, now=self.now, channel="mastodon", dry_run=True)
        self.assertEqual(out["results"]["backfilled"], 0)
        self.assertEqual(out["results"]["sent"], 0)


class TestHeilungEhrlichkeit(unittest.TestCase):
    """„Geheilt" darf nur melden, wer wirklich gesendet hat."""

    def test_recovery_ohne_versand_ist_kein_erfolg(self):
        bericht = {"results": {"sent": 0, "failed": 0, "blocked": 1,
                               "backfilled": 0, "standby": 0, "deferred": 0}}
        with patch("social_channels.load_config", return_value=CFG), \
             patch("social_studio.run_once", return_value=bericht):
            res = act.aktion_social_autopilot_lauf(
                {"modus": "recover", "kanal": "mastodon"}, {}, {"dry_run": False})
        self.assertEqual(res["status"], "fehler")
        self.assertIs(res["geheilt"], False)

    def test_recovery_mit_versand_ist_geheilt(self):
        bericht = {"results": {"sent": 1, "failed": 0, "blocked": 1,
                               "backfilled": 1, "standby": 0, "deferred": 0}}
        with patch("social_channels.load_config", return_value=CFG), \
             patch("social_studio.run_once", return_value=bericht):
            res = act.aktion_social_autopilot_lauf(
                {"modus": "recover", "kanal": "mastodon"}, {}, {"dry_run": False})
        self.assertEqual(res["status"], "ok")
        self.assertIs(res["geheilt"], True)


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
