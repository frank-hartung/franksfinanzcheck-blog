# -*- coding: utf-8 -*-
"""Tests für die Spam-Schutz-Wache (scripts/spam_schutz_wache.py).

Die Wache ist die tägliche Google-Spam-Policy-Kontrolle des Blogs:
KPIs messen, gegen Budgets bewerten, bei ROT automatisch die
Notbremse ziehen (Endredaktion → manuell) und den Status-Handshake
für die Endredaktion schreiben. Diese Tests sichern die Kernlogik
offline ab – inklusive der beiden Maskierungsfallen (Thin-Content
und Titel-Duplikate), die im echten Betrieb nur zu leicht ein
falsches ROT/GELB überlagern.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))

import post_utils  # noqa: E402
import spam_schutz_wache as ssw  # noqa: E402


ABSATZ = ("Du prüfst deine Verträge genau. Das spart im Alltag bares "
          "Geld, weil du Fristen kennst und nachhaken kannst. ")

# Fünf thematisch verschiedene Langtexte (SimHash unterscheidet
# Wortverteilungen) – verhindert, dass zufällig identische Fixture-
# Körper die Near-Dup-KPI überlagern (Maskierungsfalle).
BODIES = [
    ABSATZ * 160,
    "Die Rate bleibt gleich, doch dein Anspruch wächst mit jedem "
    "Vertragsjahr. Nachfragen lohnt sich immer. " * 150,
    "Vergleiche deine Tarife am Jahresende und kündige fristgerecht "
    "mit klaren Worten. " * 160,
    "Ein Notgroschen auf dem Tagesgeldkonto beruhigt und ersetzt "
    "teure Dispozinsen im Alltag. " * 150,
    "Versicherungen braucht jeder, aber nur die richtigen: Deckung "
    "prüfen, doppelte Bausteine streichen. " * 150,
]
_body_i = 0


class SpamWacheTempFall(unittest.TestCase):
    """Basis: Posts und Ausgaben ins Temp-Verzeichnis lenken."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="spam-wache-test-")
        posts = os.path.join(self.tmp, "posts")
        os.makedirs(posts)
        self.posts = posts
        self.alt = {
            "POSTS_DIR": post_utils.POSTS_DIR,
            "CONFIG_FILE": ssw.CONFIG_FILE,
            "STATUS_FILE": ssw.STATUS_FILE,
            "REPORT_FILE": ssw.REPORT_FILE,
            "ENDREDAKTION_CONFIG": ssw.ENDREDAKTION_CONFIG,
        }
        post_utils.POSTS_DIR = posts
        ssw.CONFIG_FILE = os.path.join(self.tmp, "spam_schutz.yaml")
        ssw.STATUS_FILE = os.path.join(self.tmp, "spam_status.json")
        ssw.REPORT_FILE = os.path.join(self.tmp, "report.md")
        ssw.ENDREDAKTION_CONFIG = os.path.join(
            self.tmp, "endredaktion.yaml")
        with open(ssw.ENDREDAKTION_CONFIG, "w", encoding="utf-8") as fh:
            fh.write("modus: automatisch\nmax_freigaben_pro_lauf: 1\n")

    def tearDown(self):
        post_utils.POSTS_DIR = self.alt["POSTS_DIR"]
        ssw.CONFIG_FILE = self.alt["CONFIG_FILE"]
        ssw.STATUS_FILE = self.alt["STATUS_FILE"]
        ssw.REPORT_FILE = self.alt["REPORT_FILE"]
        ssw.ENDREDAKTION_CONFIG = self.alt["ENDREDAKTION_CONFIG"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- Fixtures ----------
    def schreibe_post(self, slug, *, draft=False, ai=False,
                      datum=None, titel=None, body=None,
                      auto_freigabe=False, offenlegung=True):
        global _body_i
        heute = (datum or datetime.date.today().isoformat())
        fm = ["---"]
        fm.append(f'title: "{titel or f"Titel zu {slug}"}"')
        fm.append("description: \"Ehrliche Zahlen und klare Schritte "
                  "fuer deinen Haushalt im Alltag ohne Werbeblabla.\"")
        fm.append(f"date: {heute}T08:00:00Z")
        if draft:
            fm.append("draft: true")
        if ai:
            fm.append("ai_generated: true")
        if auto_freigabe:
            fm.append("endredaktion_status: freigegeben")
        fm.append("---")
        eigenbody = body if body is not None else BODIES[
            _body_i % len(BODIES)]
        _body_i += 1
        if ai and offenlegung:
            koerper = ("Transparenz: dieser Text entstand mit "
                       "KI-Unterstützung. " + eigenbody)
        else:
            koerper = eigenbody
        pfad = os.path.join(self.posts, f"{slug}.md")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write("\n".join(fm) + "\n\n" + koerper + "\n")
        return pfad


class TestLiveLeseLogic(SpamWacheTempFall):

    def test_drafts_werden_ignoriert(self):
        self.schreibe_post("2026-10-01-live-beitrag")
        self.schreibe_post("2026-10-02-entwurf", draft=True)
        posts = ssw.lese_live_posts()
        self.assertEqual([p["slug"] for p in posts],
                         ["2026-10-01-live-beitrag"])

    def test_felder_werden_erkannt(self):
        self.schreibe_post("2026-10-01-ki-beitrag", ai=True,
                           auto_freigabe=True,
                           titel="Stromkosten senken im Herbst")
        p = ssw.lese_live_posts()[0]
        self.assertTrue(p["ai"])
        self.assertTrue(p["hat_offenlegung"])
        self.assertTrue(p["endredaktion_freigabe"])
        self.assertEqual(p["titel"], "stromkosten senken im herbst")


class TestKpiMessung(SpamWacheTempFall):

    def test_sauberer_bestand_liefert_gruene_werte(self):
        for i in range(1, 5):
            self.schreibe_post(f"2026-09-2{i}-sauber-{i}",
                               datum=f"2026-09-2{i}")
        self.schreibe_post("2026-10-03-ki-offen", ai=True)
        k = ssw.kpis_berechnen(ssw.lese_live_posts(), ssw.DEFAULT_BUDGETS)
        self.assertEqual(k["live_artikel"], 5)
        self.assertEqual(k["ki_anteil_prozent"], 20.0)
        self.assertEqual(k["tempo_max_pro_tag"], 1)
        self.assertEqual(k["tempo_letzte7_tage"], 1)
        self.assertEqual(k["near_dup_paare"], 0)
        self.assertEqual(k["thin_live"], [])
        self.assertEqual(k["titel_duplikate"], [])
        self.assertEqual(k["offenlegung_fehlt"], [])

    def test_pathologien_werden_alle_erreicht(self):
        # Zwei Klone (Near-Dup), dünner Live-Artikel, KI ohne
        # Offenlegung, doppelter Titel, 4 Veröffentlichungen an einem Tag
        self.schreibe_post("2026-10-03-a-klon", body=BODIES[1])
        self.schreibe_post("2026-10-03-b-klon",
                           titel="Titel zu 2026-10-03-a-klon",
                           body=BODIES[1])  # identischer Körper
        self.schreibe_post("2026-10-03-c-thin",
                           body="Viel zu kurzer Text. ")
        self.schreibe_post("2026-10-03-d-ki-ohne-offenlegung",
                           ai=True, offenlegung=False,
                           body=BODIES[2])  # Marker fehlt im Body
        k = ssw.kpis_berechnen(ssw.lese_live_posts(), ssw.DEFAULT_BUDGETS)
        self.assertGreaterEqual(k["near_dup_paare"], 1)
        self.assertIn("2026-10-03-c-thin", k["thin_live"])
        self.assertIn("2026-10-03-d-ki-ohne-offenlegung",
                      k["offenlegung_fehlt"])
        self.assertEqual(len(k["titel_duplikate"]), 1)
        self.assertEqual(k["tempo_max_pro_tag"], 4)
        self.assertEqual(k["tempo_letzte7_tage"], 4)


class TestVerdict(SpamWacheTempFall):

    def bauen(self, **werte):
        k = {"live_artikel": 38, "ki_artikel": 12,
             "ki_anteil_prozent": 31.6, "tempo_max_pro_tag": 1,
             "tempo_letzte7_tage": 5, "auto_freigaben_letzte7_tage": 1,
             "near_dup_paare": 0, "near_dup_beispiele": [],
             "thin_live": [], "titel_duplikate": [],
             "offenlegung_fehlt": []}
        k.update(werte)
        return k

    def test_ist_zustand_ist_gruen(self):
        urteil, probleme = ssw.kpi_verdict(
            self.bauen(), ssw.DEFAULT_BUDGETS)
        self.assertEqual(urteil, "gruen")
        self.assertEqual(probleme, [])

    def test_gelb_stufen(self):
        urteil, probleme = ssw.kpi_verdict(
            self.bauen(tempo_letzte7_tage=8), ssw.DEFAULT_BUDGETS)
        self.assertEqual(urteil, "gelb")
        self.assertTrue(probleme)
        urteil, _ = ssw.kpi_verdict(
            self.bauen(ki_anteil_prozent=55), ssw.DEFAULT_BUDGETS)
        self.assertEqual(urteil, "gelb")

    def test_rot_stufen(self):
        for werte in ({"tempo_max_pro_tag": 4},
                      {"tempo_letzte7_tage": 11},
                      {"ki_anteil_prozent": 70},
                      {"auto_freigaben_letzte7_tage": 4},
                      {"near_dup_paare": 4},
                      {"thin_live": ["x"]},
                      {"titel_duplikate": ["x"]},
                      {"offenlegung_fehlt": ["x"]}):
            urteil, probleme = ssw.kpi_verdict(
                self.bauen(**werte), ssw.DEFAULT_BUDGETS)
            self.assertEqual(urteil, "rot", f"rot erwartet bei {werte}")
            self.assertTrue(probleme)


class TestNotbremse(SpamWacheTempFall):

    def test_rot_setzt_manuell_mit_marker(self):
        aktion = ssw.notbremse_anwenden("rot")
        self.assertIn("NOTBREMSE AKTIV", aktion)
        text = open(ssw.ENDREDAKTION_CONFIG, encoding="utf-8").read()
        self.assertRegex(text, r"(?m)^modus:\s*manuell")
        self.assertIn(ssw.NOTBREMSE_MARKER, text)

    def test_gruen_loest_nur_eigene_bremse(self):
        ssw.notbremse_anwenden("rot")
        aktion = ssw.notbremse_anwenden("gruen")
        self.assertIn("NOTBREMSE GELÖST", aktion)
        text = open(ssw.ENDREDAKTION_CONFIG, encoding="utf-8").read()
        self.assertRegex(text, r"(?m)^modus:\s*automatisch")
        self.assertNotIn(ssw.NOTBREMSE_MARKER, text)

    def test_frank_manuell_bleibt_unangetastet(self):
        with open(ssw.ENDREDAKTION_CONFIG, "w", encoding="utf-8") as fh:
            fh.write("modus: manuell  # Frank hat entschieden\n")
        aktion = ssw.notbremse_anwenden("rot")
        self.assertIn("unangetastet", aktion)
        aktion = ssw.notbremse_anwenden("gruen")
        self.assertIn("Keine Notbremse", aktion)
        text = open(ssw.ENDREDAKTION_CONFIG, encoding="utf-8").read()
        self.assertIn("Frank hat entschieden", text)

    def test_nur_messen_aendert_nichts(self):
        aktion = ssw.notbremse_anwenden("rot", nur_messen=True)
        self.assertIn("Nur-Messen", aktion)
        text = open(ssw.ENDREDAKTION_CONFIG, encoding="utf-8").read()
        self.assertRegex(text, r"(?m)^modus:\s*automatisch")


class TestStatusHandshake(SpamWacheTempFall):

    def test_statusfile_ist_maschinen_wahrheit(self):
        k = ssw.kpis_berechnen([], ssw.DEFAULT_BUDGETS)
        ssw.status_schreiben(k, "gruen", [])
        with open(ssw.STATUS_FILE, encoding="utf-8") as fh:
            status = json.load(fh)
        self.assertEqual(status["urteil"], "gruen")
        self.assertEqual(status["probleme"], [])
        self.assertIn("stand", status)
        self.assertIn("kpis", status)

    def test_bericht_enthaelt_urteil_und_budgets(self):
        k = ssw.kpis_berechnen([], ssw.DEFAULT_BUDGETS)
        ssw.bericht_schreiben(k, ssw.DEFAULT_BUDGETS, "gelb",
                              ["Tempo 8/Woche"], "Keine Notbremse nötig.")
        text = open(ssw.REPORT_FILE, encoding="utf-8").read()
        self.assertIn("GELB", text)
        self.assertIn("Tempo 8/Woche", text)


class TestBudgetDatei(SpamWacheTempFall):

    def test_yaml_budgets_ueberschreiben_defaults(self):
        with open(ssw.CONFIG_FILE, "w", encoding="utf-8") as fh:
            fh.write("tempo_rot_pro_woche: 12\nnear_dup_hamming: 12\n")
        b = ssw.lade_budgets()
        self.assertEqual(b["tempo_rot_pro_woche"], 12)
        self.assertEqual(b["near_dup_hamming"], 12)
        # Nicht genannte Budgets kommen aus den Defaults
        self.assertEqual(b["thin_live_max"], 0)


if __name__ == "__main__":
    unittest.main()
