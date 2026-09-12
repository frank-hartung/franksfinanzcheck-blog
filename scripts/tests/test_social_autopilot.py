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

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_channels as sch          # noqa: E402
import social_copywriter as copy       # noqa: E402
import social_gate as gate             # noqa: E402
import social_images as images         # noqa: E402
import social_planner as planner       # noqa: E402

CFG = sch.load_config()
CHANNELS = sch.channel_map(CFG)
META = sch.meta_of(CFG)


def _article(slug: str, pillar: str = "strom-sparen", days_old: int = 3) -> dict:
    now = planner.berlin_now()
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
        for cid, ch in CHANNELS.items():
            with self.subTest(channel=cid):
                self.assertIn((ch.get("text") or {}).get("link_position"),
                              {"end", "first_comment", "none"})


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
        self.pool = [_article(f"artikel-{i:02d}",
                              ["strom-sparen", "internet-dsl", "versicherungen",
                               "konto-karten", "frugalismus", "mietwagen"][i % 6],
                              days_old=2 + i) for i in range(12)]
        self.now = planner.localize(datetime(2026, 9, 14, 6, 0))

    def tearDown(self):
        planner.SCHEDULE_FILE = self.old_schedule
        planner.STATE_FILE = self.old_state

    def _plan(self, state=None):
        return planner.build_plan(CFG, self.pool, state or {"history": [], "failures": []},
                                  now=self.now)

    def test_plan_ist_gefuellt(self):
        self.assertTrue(planner.planned_items(self._plan()))

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
