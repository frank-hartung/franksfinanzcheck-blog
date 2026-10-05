#!/usr/bin/env python3
"""Tests für das Cockpit (scripts/cockpit.py).

Das Cockpit aggregiert ausschließlich bereits bestehende Zustandsdateien
(governance_status.json, secrets_state.json, social/state.yaml, newsletter
journal/state) zu EINER Ampel-Seite (COCKPIT.md). Es misst nichts selbst
nach und ruft kein Netz auf. Diese Tests nageln die Aggregations-/
Ampel-Logik fest – unabhängig vom echten Datenbestand des Repos, damit
sie nicht brechen, sobald sich reale Werte ändern.

Läuft deterministisch ohne Netz
(`python3 -m unittest discover -s scripts/tests`).
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cockpit  # noqa: E402

NOW = datetime.datetime(2026, 10, 3, 10, 0, tzinfo=datetime.timezone.utc)


class WorstUndMappingTest(unittest.TestCase):
    def test_worst_ignoriert_grau_wenn_moeglich(self):
        self.assertEqual(cockpit.worst(["grau", "gruen"]), "gruen")
        self.assertEqual(cockpit.worst(["grau", "gelb", "gruen"]), "gelb")
        self.assertEqual(cockpit.worst(["rot", "gelb"]), "rot")

    def test_worst_leere_liste_ist_grau(self):
        self.assertEqual(cockpit.worst([]), "grau")

    def test_level_from_governance(self):
        self.assertEqual(cockpit._level_from_governance("green"), "gruen")
        self.assertEqual(cockpit._level_from_governance("amber"), "gelb")
        self.assertEqual(cockpit._level_from_governance("red"), "rot")
        self.assertEqual(cockpit._level_from_governance("info"), "grau")
        self.assertEqual(cockpit._level_from_governance("unbekannt"), "grau")

    def test_parse_ts_z_und_offset_gleichwertig(self):
        a = cockpit._parse_ts("2026-10-01T10:00:00Z")
        b = cockpit._parse_ts("2026-10-01T12:00:00+02:00")
        self.assertEqual(a, b)

    def test_parse_ts_ohne_wert(self):
        self.assertIsNone(cockpit._parse_ts(None))
        self.assertIsNone(cockpit._parse_ts(""))
        self.assertIsNone(cockpit._parse_ts("kein-datum"))

    def test_slug_date(self):
        self.assertEqual(
            cockpit._slug_date("2026-09-27-wlan-verstaerker-vs-mesh"),
            datetime.date(2026, 9, 27),
        )
        self.assertIsNone(cockpit._slug_date("ohne-datum"))


class BucketContentTest(unittest.TestCase):
    def test_rote_lesbarkeit_zieht_bereich_auf_rot(self):
        gov = {"steps": {
            "lesbarkeit": {"level": "red", "message": "Flesch zu niedrig"},
            "decay": {"level": "green", "message": "ok"},
        }}
        lvl, lines, _ = cockpit.bucket_content(gov, {"ready": 6, "target": 6})
        self.assertEqual(lvl, "rot")
        self.assertTrue(any("lesbarkeit" in l for l in lines))

    def test_volle_reserve_wird_vermerkt(self):
        lvl, lines, _ = cockpit.bucket_content({"steps": {}}, {"ready": 6, "target": 6})
        self.assertEqual(lvl, "grau")
        self.assertTrue(any("6/6" in l for l in lines))

    def test_leere_reserve_ist_rot(self):
        lvl, _, _ = cockpit.bucket_content({"steps": {}}, {"ready": 0, "target": 6})
        self.assertEqual(lvl, "rot")

    def test_knappe_reserve_ist_gelb(self):
        lvl, _, _ = cockpit.bucket_content({"steps": {}}, {"ready": 2, "target": 6})
        self.assertEqual(lvl, "gelb")

    def test_fehlende_governance_bricht_nicht(self):
        lvl, lines, _ = cockpit.bucket_content({}, {})
        self.assertEqual(lvl, "grau")
        self.assertTrue(lines)


class BucketSeoTest(unittest.TestCase):
    def test_info_only_bleibt_gruen(self):
        gov = {"steps": {
            "cwv": {"level": "green", "message": "ok"},
            "build": {"level": "green", "message": "ok"},
            "umami": {"level": "info", "message": "keine Daten"},
        }}
        lvl, lines, _ = cockpit.bucket_seo(gov)
        self.assertEqual(lvl, "gruen")
        self.assertTrue(any("Standby" in l for l in lines))

    def test_rotes_cwv_zieht_auf_rot(self):
        gov = {"steps": {"cwv": {"level": "red", "message": "LCP zu langsam"}}}
        lvl, lines, _ = cockpit.bucket_seo(gov)
        self.assertEqual(lvl, "rot")
        self.assertTrue(any("cwv" in l for l in lines))


class BucketAffiliateTest(unittest.TestCase):
    def test_amber_click_chain_ist_gelb(self):
        gov = {"steps": {"click-chain": {"level": "amber", "message": "Tracking fehlt"}}}
        lvl, lines, _ = cockpit.bucket_affiliate(gov)
        self.assertEqual(lvl, "gelb")
        self.assertTrue(any("click-chain" in l for l in lines))

    def test_nur_info_ist_grau_keine_datenlage(self):
        gov = {"steps": {"awin": {"level": "info", "message": "keine Daten"}}}
        lvl, lines, _ = cockpit.bucket_affiliate(gov)
        self.assertEqual(lvl, "grau")
        self.assertTrue(any("keine Datenlage" in l for l in lines))

    def test_gruenes_plus_info_bleibt_gruen(self):
        gov = {"steps": {
            "click-chain": {"level": "green", "message": "ok"},
            "awin": {"level": "info", "message": "keine Daten"},
        }}
        lvl, lines, _ = cockpit.bucket_affiliate(gov)
        self.assertEqual(lvl, "gruen")
        self.assertTrue(any("ohne Datenlage" in l for l in lines))


class BucketZugaengeTest(unittest.TestCase):
    def test_totes_token_ist_rot_mit_beiden_listen(self):
        gov = {"steps": {"secrets": {"level": "red", "message": "Pinterest tot"}}}
        zugang_state = {"entries": {
            "GEMINI_API_KEY": {"quality": "proven"},
            "PINTEREST_ACCESS_TOKEN": {"verify": "dead"},
        }}
        lvl, lines, _ = cockpit.bucket_zugaenge(gov, zugang_state)
        self.assertEqual(lvl, "rot")
        joined = " ".join(lines)
        self.assertIn("GEMINI_API_KEY", joined)
        self.assertIn("PINTEREST_ACCESS_TOKEN", joined)

    def test_alles_proven_ist_gruen(self):
        zugang_state = {"entries": {"GEMINI_API_KEY": {"quality": "proven"}}}
        lvl, lines, _ = cockpit.bucket_zugaenge({}, zugang_state)
        self.assertEqual(lvl, "gruen")

    def test_keine_daten_ist_grau(self):
        lvl, lines, _ = cockpit.bucket_zugaenge({}, {})
        self.assertEqual(lvl, "grau")


class BucketSocialTest(unittest.TestCase):
    CHANNELS = {"channels": {
        "mastodon": {"enabled": True, "label": "Mastodon", "pflicht_env": ["MASTODON_ACCESS_TOKEN"]},
        "pinterest": {"enabled": True, "label": "Pinterest", "pflicht_env": ["PINTEREST_ACCESS_TOKEN"]},
        "bluesky": {"enabled": True, "label": "Bluesky",
                    "pflicht_env": ["BLUESKY_IDENTIFIER", "BLUESKY_APP_PASSWORD"]},
        "x": {"enabled": False, "label": "X (deaktiviert)", "pflicht_env": ["X_TOKEN"]},
    }}

    def test_kein_kanal_live_ist_rot(self):
        lvl, lines, _ = cockpit.bucket_social({"entries": {}}, self.CHANNELS,
                                               {"history": [], "failures": []}, NOW)
        self.assertEqual(lvl, "rot")
        self.assertTrue(any("0/3" in l for l in lines))  # X ist deaktiviert, zählt nicht mit

    def test_live_kanal_mit_frischem_post_ist_gruen(self):
        zugang_state = {"entries": {"MASTODON_ACCESS_TOKEN": {"quality": "proven"}}}
        state = {"history": [{"ok": True, "posted_at": "2026-10-02T10:00:00+00:00"}], "failures": []}
        lvl, lines, _ = cockpit.bucket_social(zugang_state, self.CHANNELS, state, NOW)
        self.assertEqual(lvl, "gruen")

    def test_totes_token_zieht_auf_gelb_trotz_frischem_post(self):
        zugang_state = {"entries": {
            "MASTODON_ACCESS_TOKEN": {"quality": "proven"},
            "PINTEREST_ACCESS_TOKEN": {"verify": "dead"},
        }}
        state = {"history": [{"ok": True, "posted_at": "2026-10-02T10:00:00+00:00"}], "failures": []}
        lvl, lines, _ = cockpit.bucket_social(zugang_state, self.CHANNELS, state, NOW)
        self.assertEqual(lvl, "gelb")

    def test_alter_post_ist_rot(self):
        zugang_state = {"entries": {"MASTODON_ACCESS_TOKEN": {"quality": "proven"}}}
        state = {"history": [{"ok": True, "posted_at": "2026-09-01T10:00:00+00:00"}], "failures": []}
        lvl, lines, _ = cockpit.bucket_social(zugang_state, self.CHANNELS, state, NOW)
        self.assertEqual(lvl, "rot")

    def test_keine_kanaele_konfiguriert_ist_grau_nicht_rot(self):
        lvl, _, _ = cockpit.bucket_social({}, {"channels": {}}, {}, NOW)
        self.assertEqual(lvl, "grau")

    def test_standby_kanaele_werden_aufgelistet(self):
        zugang_state = {"entries": {"MASTODON_ACCESS_TOKEN": {"quality": "proven"}}}
        state = {"history": [{"ok": True, "posted_at": "2026-10-02T10:00:00+00:00"}], "failures": []}
        _, lines, _ = cockpit.bucket_social(zugang_state, self.CHANNELS, state, NOW)
        self.assertTrue(any("Standby" in l and "Bluesky" in l for l in lines))


class BucketNewsletterTest(unittest.TestCase):
    def test_nie_versendet_und_alte_warteschlange_ist_rot(self):
        journal = [{"modus": "sendefile", "ausgabe": "test-2026-09-20", "status": "zugestellt",
                    "ts": "2026-09-20T10:00:00+00:00"}]
        state = {"pending": ["2026-09-10-alter-artikel"]}
        lvl, lines, _ = cockpit.bucket_newsletter(journal, state, NOW)
        self.assertEqual(lvl, "rot")

    def test_nie_versendet_leere_warteschlange_ist_grau(self):
        lvl, _, _ = cockpit.bucket_newsletter([], {"pending": []}, NOW)
        self.assertEqual(lvl, "grau")

    def test_frischer_echter_versand_ist_gruen(self):
        journal = [{"modus": "sendefile", "ausgabe": "2026-10-02-ausgabe", "status": "zugestellt",
                    "ts": "2026-10-02T06:30:00+00:00"}]
        lvl, _, _ = cockpit.bucket_newsletter(journal, {"pending": []}, NOW)
        self.assertEqual(lvl, "gruen")

    def test_testmails_zaehlen_nicht_als_echter_versand(self):
        journal = [
            {"modus": "sendefile", "ausgabe": "test-2026-10-02", "status": "zugestellt",
             "ts": "2026-10-02T06:30:00+00:00"},
            {"modus": "sendefile", "ausgabe": "bestaetigung-abc", "status": "zugestellt",
             "ts": "2026-10-02T06:31:00+00:00"},
        ]
        lvl, lines, _ = cockpit.bucket_newsletter(journal, {"pending": []}, NOW)
        self.assertTrue(any("noch kein echter Listenversand" in l for l in lines))

    def test_versand_mit_fehlerstatus_zaehlt_nicht(self):
        journal = [{"modus": "sendefile", "ausgabe": "2026-10-02-ausgabe", "status": "fehler",
                    "ts": "2026-10-02T06:30:00+00:00"}]
        lvl, lines, _ = cockpit.bucket_newsletter(journal, {"pending": []}, NOW)
        self.assertTrue(any("noch kein echter Listenversand" in l for l in lines))


class BuildAndRenderTest(unittest.TestCase):
    def setUp(self):
        self.gov = {"steps": {"lesbarkeit": {"level": "red", "message": "zu schwer"}}}
        self.channels = {"channels": {
            "mastodon": {"enabled": True, "label": "Mastodon", "pflicht_env": ["MASTODON_ACCESS_TOKEN"]},
        }}
        self.zugang_state = {"entries": {"MASTODON_ACCESS_TOKEN": {"quality": "proven"}}}
        self.social_state = {"history": [{"ok": True, "posted_at": "2026-10-02T10:00:00+00:00"}],
                              "failures": []}
        self.journal = [{"modus": "sendefile", "ausgabe": "2026-10-02-ausgabe", "status": "zugestellt",
                          "ts": "2026-10-02T06:30:00+00:00"}]

    def test_gesamtbild_ist_schlechteste_einzelampel(self):
        overall, buckets = cockpit.build_cockpit(
            NOW, self.gov, {"ready": 6, "target": 6}, self.zugang_state, self.channels,
            self.social_state, self.journal, {"pending": []},
        )
        self.assertEqual(overall, "rot")  # wegen Content-Pipeline
        self.assertEqual(buckets["Content-Pipeline"][0], "rot")
        self.assertEqual(buckets["Social-Automation"][0], "gruen")

    def test_alles_grau_ist_gesamt_grau(self):
        overall, _ = cockpit.build_cockpit(
            NOW, {}, {}, {}, {"channels": {}}, {}, [], {},
        )
        self.assertEqual(overall, "grau")

    def test_render_markdown_enthaelt_alle_bereiche(self):
        overall, buckets = cockpit.build_cockpit(
            NOW, self.gov, {"ready": 6, "target": 6}, self.zugang_state, self.channels,
            self.social_state, self.journal, {"pending": []},
        )
        md = cockpit.render_markdown(NOW, overall, buckets)
        self.assertTrue(md.startswith("# 🚦 COCKPIT"))
        for name in cockpit.BUCKET_ORDER:
            self.assertIn(name, md)
        self.assertIn("🔴", md)

    def test_status_json_ist_serialisierbar(self):
        overall, buckets = cockpit.build_cockpit(
            NOW, self.gov, {"ready": 6, "target": 6}, self.zugang_state, self.channels,
            self.social_state, self.journal, {"pending": []},
        )
        status = cockpit.build_status_json(NOW, overall, buckets)
        rehydrated = json.loads(json.dumps(status))
        self.assertEqual(rehydrated["overall"], "rot")
        self.assertIn("Content-Pipeline", rehydrated["buckets"])


class SelftestTest(unittest.TestCase):
    def test_eingebautes_selftest_ist_gruen(self):
        self.assertTrue(cockpit.selftest())


if __name__ == "__main__":
    unittest.main()
