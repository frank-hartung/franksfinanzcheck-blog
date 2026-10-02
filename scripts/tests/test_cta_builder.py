#!/usr/bin/env python3
"""Regressionstest: cta_builder – End-CTA nach Intent-Kontrakt (WF-D4E0).

Anlass (Vorgang WF-D4E0, Issue #513, 02.10.2026): Drei Autoren der
Content-Pipeline (ki_shared.cta_block, engine_generate.save_article,
generate_drafts.write_draft) schrieben denselben End-CTA dreimal selbst –
immer mit roher Partner-URL und dem generischen Anker „Jetzt Angebote
vergleichen“. Link-Integrität (kein /go/-Redirect), IW8 (Anker nennt kein
Angebot) und IW3 („Vergleich“ vor Einzelangebot) verwarfen damit JEDEN
maschinell erzeugten Reserve-Kandidaten bei der Zertifizierung – die
Reserve leerte sich strukturell, obwohl alle Schritte „grün“ meldeten.

Dieser Test hält den Reparatur-Vertrag fest: Der End-CTA kommt aus
affiliate_intent_contract (derselben Wahrheit wie die Intent-Wache), das
Ziel ist immer die /go/-Übergabeseite, und Einzelanbieter-Routen (C24
Bank) nennen Marke und Produkt ehrlich – ohne „Vergleich“-Versprechen.
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import cta_builder  # noqa: E402
import affiliate_intent_contract as aic  # noqa: E402


def _assert_contract_selftest(testcase: unittest.TestCase) -> None:
    """Der Kontrakt ist die Wahrheit – sein Selbsttest muss fehlerfrei sein."""
    fehler = aic.selftest()
    testcase.assertEqual([], fehler, f"Intent-Kontrakt-Selbsttest: {fehler}")


class TestCtaBuilder(unittest.TestCase):
    def test_module_selftest(self):
        self.assertEqual([], cta_builder._selftest())

    def test_contract_selftest(self):
        _assert_contract_selftest(self)

    # -- Wurzel 1: keine rohen Partner-URLs mehr im End-CTA -------------
    def test_kein_roher_partner_link(self):
        for route in ("allgemein", "tagesgeld", "gas", "dsl", "girokonto"):
            block = cta_builder.cta_end_block(route=route, slug="probe-artikel")
            self.assertNotIn("http", block, f"Route {route}: rohe URL im CTA")
            self.assertIn(f"/go/{route}/", block, f"Route {route}: Ziel fehlt")

    def test_url_wird_auf_route_abgebildet(self):
        """Die historische Standard-URL (Portal aid=18) → /go/allgemein/."""
        alt = "https://a.check24.net/misc/click.php?pid=80968&aid=18"
        block = cta_builder.cta_end_block(affiliate_url=alt)
        self.assertIn("/go/allgemein/", block)
        self.assertNotIn("check24.net", block)

    def test_tagesgeld_url_wird_c24_route(self):
        import yaml
        with open(os.path.join(SCRIPTS, "check24_links.yaml"),
                  encoding="utf-8") as fh:
            links = (yaml.safe_load(fh) or {}).get("links", {}) or {}
        url = str(links.get("tagesgeld", ""))
        self.assertTrue(url, "check24_links.yaml ohne tagesgeld-URL")
        self.assertEqual("tagesgeld", cta_builder.route_fuer_url(url))

    # -- Wurzel 2: Anker nennt das Angebot (IW8) -------------------------
    def test_anker_nennt_angebot(self):
        _assert_contract_selftest(self)
        for route in ("allgemein", "tagesgeld", "gas"):
            _, anker = aic.cta_bausteine(route, "end", "probe-artikel")
            block = cta_builder.cta_end_block(route=route, slug="probe-artikel")
            self.assertIn(anker, block, f"Route {route}: Anker nicht kontraktgemäß")
            self.assertFalse(
                aic.anker_ist_generisch(anker),
                f"Route {route}: Kontrakt-Anker bliebe generisch (IW8)")

    # -- Wurzel 3: kein Vergleichs-Versprechen vor Einzelangebot (IW3) ---
    def test_einzelanbieter_ehrlich(self):
        block = cta_builder.cta_end_block(route="tagesgeld", slug="probe-artikel")
        self.assertIn("C24", block, "C24-Marke fehlt im Einzelanbieter-CTA")
        self.assertNotIn("ergleich", block.replace("CHECK24", ""),
                         "Einzelanbieter-CTA verspricht einen Vergleich")

    # -- Stabilität: gleiche Eingabe → gleiche Bytes ----------------------
    def test_determinismus(self):
        a = cta_builder.cta_end_block(route="gas", slug="probe-artikel")
        b = cta_builder.cta_end_block(route="gas", slug="probe-artikel")
        self.assertEqual(a, b)

    # -- Werbe-Offenlegung und Hausmarker bleiben Pflicht ----------------
    def test_offenlegung_und_marker(self):
        block = cta_builder.cta_end_block(route="dsl", slug="probe-artikel")
        self.assertIn("Werbung", block)
        self.assertTrue(block.lstrip("\n").startswith("---"),
                        "Trennlinie vor dem End-CTA fehlt")

    # -- Aufrufer-Integration: ki_shared delegiert auf die Werkstatt ------
    def test_ki_shared_nutzt_werkstatt(self):
        import ki_shared
        block = ki_shared.cta_block()
        self.assertIn("/go/allgemein/", block)
        self.assertNotIn("http", block)
        self.assertIn("CHECK24", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
