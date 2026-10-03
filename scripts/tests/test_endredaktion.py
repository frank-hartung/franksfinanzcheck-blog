#!/usr/bin/env python3
"""Regressionstests für die ENDREDAKTION (Prüfen · Optimieren · Freigeben).

Frieren die Kernversprechen ein – deterministisch, offline, alle Pfade
in temporären Verzeichnissen:

  1) GATE-SUITE   – guter Entwurf wird grün, TODO-Gerüst blockiert,
                    Duplikat blockiert nur den NEUEREN Entwurf
  2) FREIGABE     – nur über park_state.rearm (cadence_wait: true),
                    draft bleibt true; Deckel + Kill-Switch werden respektiert
  3) POLITUR      – Sicherheitsvertrag: veränderte Links werden verworfen,
                    saubere Politur wird übernommen und macht grün
  4) MASTODON     – Poppy-Text wird erst gepostet, wenn der Artikel live
                    ist; danach Dedupe über mastodon_gesendet
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import endredaktion as er  # noqa: E402
import poppy_lib  # noqa: E402
import post_utils  # noqa: E402
import readability_check  # noqa: E402

GUTER_TITEL = "Stromkosten senken: so gehst du vor"
GUTE_DESC = ("Stromkosten senken: prüfe Verträge, vergleiche Tarife und "
             "sichere dir die Preisgarantie – Schritt für Schritt erklärt.")

ABSATZ = ("Du prüfst deine Verträge. Das spart im Alltag bares Geld. "
          "Ein Wechsel dauert wenige Minuten. Du liest die Frist. "
          "Du schreibst einen Brief. Der Anbieter bestätigt die Kündigung. "
          "Danach wählst du einen neuen Tarif. Achte auf die Preisgarantie. "
          "Kleine Schritte zählen. Dein Haushalt profitiert davon.")


def guter_body(mit_link=True):
    teile = []
    for i, h2 in enumerate(("Was du zuerst prüfst", "So vergleichst du Tarife",
                            "Fristen und Preisgarantie")):
        teile.append(f"## {h2}\n\n{ABSATZ} " * 12)
        teile.append(ABSATZ + "\n")
    body = "\n\n".join(teile)
    if mit_link:
        body += "\n\nMehr Details findest du im [Vergleich](https://a.de/x).\n"
    return body


class EndredaktionTempFall(unittest.TestCase):
    """Basis: Posts, Karten und Ausgaben ins Temp-Verzeichnis lenken."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="endredaktion-test-")
        posts = os.path.join(self.tmp, "posts")
        os.makedirs(posts)
        self.posts = posts
        self.alt = {
            "POSTS_DIR": post_utils.POSTS_DIR,
            "READ_POSTS_DIR": readability_check.POSTS_DIR,
            "CONFIG_FILE": er.CONFIG_FILE,
            "REPORT_FILE": er.REPORT_FILE,
            "SPAM_STATUS_FILE": er.SPAM_STATUS_FILE,
            "CARD_DIR": poppy_lib.CARD_DIR,
        }
        post_utils.POSTS_DIR = posts
        readability_check.POSTS_DIR = posts
        er.CONFIG_FILE = os.path.join(self.tmp, "endredaktion.yaml")
        er.REPORT_FILE = os.path.join(self.tmp, "report.md")
        er.SPAM_STATUS_FILE = os.path.join(self.tmp, "spam_status.json")
        poppy_lib.CARD_DIR = os.path.join(self.tmp, "cards")
        with open(er.CONFIG_FILE, "w", encoding="utf-8") as fh:
            fh.write("modus: automatisch\nmax_freigaben_pro_lauf: 1\n")
        # Spam-Schutz-Handshake: gültig grün (wie nach dem täglichen
        # Wachen-Lauf). Die Sperre testen die eigenen Tests unten.
        with open(er.SPAM_STATUS_FILE, "w", encoding="utf-8") as fh:
            json.dump({"urteil": "gruen", "probleme": []}, fh)

    def tearDown(self):
        post_utils.POSTS_DIR = self.alt["POSTS_DIR"]
        readability_check.POSTS_DIR = self.alt["READ_POSTS_DIR"]
        er.CONFIG_FILE = self.alt["CONFIG_FILE"]
        er.REPORT_FILE = self.alt["REPORT_FILE"]
        er.SPAM_STATUS_FILE = self.alt["SPAM_STATUS_FILE"]
        poppy_lib.CARD_DIR = self.alt["CARD_DIR"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- Fixtures ----------
    def schreibe_post(self, slug, *, draft=True, body=None, titel=GUTER_TITEL,
                      description=GUTE_DESC, ai_generated=False,
                      extra_fm=""):
        heute = datetime.date.today().isoformat()
        fm = (
            "---\n"
            f"title: {json.dumps(titel, ensure_ascii=False)}\n"
            f"description: {json.dumps(description, ensure_ascii=False)}\n"
            f"date: {heute}T08:00:00Z\n"
            + ("draft: true\n" if draft else "draft: false\n")
            + 'tags: ["Strom sparen"]\n'
            + ("ai_generated: true\n" if ai_generated else "")
            + extra_fm
            + "---\n\n")
        d = os.path.join(self.posts, slug)
        os.makedirs(d, exist_ok=True)
        pfad = os.path.join(d, "index.md")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(fm + (body if body is not None else guter_body()))
        return pfad

    def lies(self, pfad):
        with open(pfad, encoding="utf-8") as fh:
            return fh.read()


class TestGateSuite(EndredaktionTempFall):
    def test_guter_entwurf_ist_gruen(self):
        pfad = self.schreibe_post("2026-10-03-guter-entwurf")
        artikel = er.artikel_laden(pfad)
        funde = er.pruefe_artikel(artikel)
        self.assertEqual(er.urteil(funde), "gruen",
                         msg=str([f for f in funde if f["schwere"] != "hinweis"]))

    def test_todo_geruest_blockiert(self):
        pfad = self.schreibe_post(
            "2026-10-03-geruest",
            body="## A\n\nTODO(KI-REDAKTION: Einstieg schreiben.)\n\n"
                 "## B\n\n" + ABSATZ + "\n\n## C\n\n" + ABSATZ)
        artikel = er.artikel_laden(pfad)
        funde = er.pruefe_artikel(artikel)
        self.assertEqual(er.urteil(funde), "blockiert")
        codes = {f["code"] for f in funde}
        self.assertIn("E1", codes)

    def test_duplikat_blockiert_nur_neueren(self):
        self.schreibe_post("2026-10-03-older-duplikat")
        pfad_neu = self.schreibe_post("2026-10-04-neuer-duplikat")
        alt = er.artikel_laden(os.path.join(
            self.posts, "2026-10-03-older-duplikat", "index.md"))
        neu = er.artikel_laden(pfad_neu)
        self.assertEqual(er.urteil(er.pruefe_artikel(alt)), "gruen")
        funde = er.pruefe_artikel(neu)
        self.assertEqual(er.urteil(funde), "blockiert")
        self.assertIn("E10", {f["code"] for f in funde})

    def test_ki_floskel_ist_gelb(self):
        pfad = self.schreibe_post(
            "2026-10-03-floskel",
            body="## A\n\nHeutzutage sparen viele Haushalte Geld. " + ABSATZ
                 + "\n\n## B\n\n" + ABSATZ + "\n\n## C\n\n" + ABSATZ)
        funde = er.pruefe_artikel(er.artikel_laden(pfad))
        self.assertEqual(er.urteil(funde), "optimieren")
        self.assertIn("E4", {f["code"] for f in funde})

    def test_description_fix_fehlendes_feld(self):
        # Description-Zeile fehlt komplett → _fm_set fügt nach title ein
        pfad = self.schreibe_post("2026-10-03-ohne-desc")
        with open(pfad, encoding="utf-8") as fh:
            text = fh.read()
        text = re.sub(r"(?m)^description:.*\n", "", text)
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(text)
        artikel = er.artikel_laden(pfad)
        artikel["description"] = ""
        fixes = er.deterministische_fixes(
            artikel, er.pruefe_artikel(artikel))
        self.assertTrue(any("Description" in f for f in fixes), fixes)
        self.assertIn("description:", self.lies(pfad))


class TestFreigabe(EndredaktionTempFall):
    def test_gruener_entwurf_wird_eingereiht(self):
        pfad = self.schreibe_post("2026-10-03-freigabe")
        cfg = er.lade_config()
        summary = er.lauf(cfg)
        inhalt = self.lies(pfad)
        self.assertEqual(summary["freigaben"], 1, str(summary["details"]))
        self.assertRegex(inhalt, r"(?m)^cadence_wait:\s*true$")
        self.assertRegex(inhalt, r"(?m)^draft:\s*true$")  # NIE selbst live
        self.assertRegex(inhalt, r"(?m)^endredaktion_status:\s*freigegeben$")

    def test_deckel_max_eine_freigabe(self):
        self.schreibe_post("2026-10-03-a-gruen")
        self.schreibe_post("2026-10-04-b-gruen")
        cfg = er.lade_config()
        summary = er.lauf(cfg)
        self.assertEqual(summary["freigaben"], 1)
        # der ältere (Slug aufsteigend) bekommt den Vorzug
        self.assertTrue(any(z["freigabe"] and z["slug"].endswith("a-gruen")
                            for z in summary["details"]))

    def test_kill_switch_manuell(self):
        pfad = self.schreibe_post("2026-10-03-manuell")
        with open(er.CONFIG_FILE, "w", encoding="utf-8") as fh:
            fh.write("modus: manuell\n")
        summary = er.lauf(er.lade_config())
        self.assertEqual(summary["freigaben"], 0)
        self.assertNotIn("cadence_wait", self.lies(pfad))

    def test_blockierter_entwurf_wird_nicht_freigegeben(self):
        pfad = self.schreibe_post(
            "2026-10-03-blockiert",
            body="## A\n\nTODO(POPPY: Inhalt fehlt.)\n\n## B\n\n" + ABSATZ)
        summary = er.lauf(er.lade_config())
        self.assertEqual(summary["freigaben"], 0)
        self.assertNotIn("cadence_wait", self.lies(pfad))


class TestPolitur(EndredaktionTempFall):
    def test_saubere_politur_macht_gruen(self):
        # Langer Körper (über Floor) MIT Floskel – die Politur entfernt nur
        # die Floskel und hält jeden Link + die Länge.
        body_mit_floskel = ("## A\n\nHeutzutage gilt: prüfe deine Verträge. "
                            + guter_body())
        pfad = self.schreibe_post("2026-10-03-politur",
                                  body=body_mit_floskel)
        sauber = body_mit_floskel.replace("Heutzutage gilt: ", "")
        self.assertGreater(len(sauber), 10000)  # Floor erreichbar
        with mock.patch.object(er.llm_client, "chat",
                               return_value=sauber) as m:
            summary = er.lauf(er.lade_config())
        self.assertTrue(m.called)
        self.assertEqual(summary["freigaben"], 1,
                         str(summary["details"]))
        self.assertNotIn("Heutzutage", self.lies(pfad))

    def test_vertragsbruch_wird_verworfen(self):
        body = "## A\n\nHeutzutage prüfst du Verträge. " + guter_body()
        pfad = self.schreibe_post("2026-10-03-vertragsbruch", body=body)
        # Antwort ändert den Link (Verstoß gegen den Sicherheitsvertrag)
        schlecht = body.replace("[Vergleich](https://a.de/x)",
                                "[Angebot](https://b.de/y)")
        original = self.lies(pfad)
        with mock.patch.object(er.llm_client, "chat",
                               return_value=schlecht.replace("Heutzutage ", "")):
            summary = er.lauf(er.lade_config())
        self.assertEqual(summary["freigaben"], 0)
        self.assertEqual(self.lies(pfad), original)  # Body unangetastet


class TestMastodon(EndredaktionTempFall):
    def karte(self, slug):
        karte = poppy_lib.neue_karte(
            "text", titel="Mastodon-Testkarte", url="https://q.de/x",
            rohtext="Strompreis sinkt um 10 Prozent laut Beispiel.")
        karte["status"] = "verwertet"
        karte["erzeugnisse"] = {
            "blog": {"slug": slug},
            "mastodon": "Neuer Ratgeber online: Stromkosten senken. #Finanzen",
            "artikel_url": f"https://franksfinanzcheck.de/posts/{slug}/",
        }
        poppy_lib.speichere_karte(karte)
        return karte

    def test_post_nur_wenn_artikel_live(self):
        self.schreibe_post("2026-10-03-noch-draft")  # draft: true
        self.karte("2026-10-03-noch-draft")
        with mock.patch.object(er, "_mastodon_post",
                               return_value=(True, "https://m.social/@f/1")):
            zeilen = er.mastodon_lauf(er.lade_config())
        self.assertTrue(any("Keine neuen" in z or "übersprungen" in z
                            for z in zeilen), zeilen)
        karten = poppy_lib.lade_karten()
        self.assertNotIn("mastodon_gesendet", karten[0]["erzeugnisse"])

    def test_post_und_dedupe(self):
        self.schreibe_post("2026-10-03-live-artikel", draft=False)
        self.karte("2026-10-03-live-artikel")
        with mock.patch.object(er, "_mastodon_post",
                               return_value=(True, "https://m.social/@f/1")
                               ) as m:
            er.mastodon_lauf(er.lade_config())
            self.assertEqual(m.call_count, 1)
            # zweiter Lauf: Karte ist als gesendet markiert → kein Post
            er.mastodon_lauf(er.lade_config())
            self.assertEqual(m.call_count, 1)
        karte = poppy_lib.lade_karten()[0]
        self.assertTrue(karte["erzeugnisse"].get("mastodon_gesendet"))
        self.assertEqual(m.call_args[0][0].count("https://franksfinanzcheck"
                                                ".de/posts/"), 1)


class TestSpamSchutz(EndredaktionTempFall):
    """Premium-Spam-Schutz: E12, Spam-Status-Handshake, Wochenbudget."""

    def test_e12_near_dup_blockiert_freigabe(self):
        # LIVE-Artikel mit demselben Körper → Entwurf ist ein Klon
        self.schreibe_post("2026-10-03-live-original", draft=False)
        pfad = self.schreibe_post("2026-10-04-klon-entwurf")
        summary = er.lauf(er.lade_config())
        zeile = next(z for z in summary["details"]
                     if z["slug"] == "2026-10-04-klon-entwurf")
        self.assertEqual(zeile["zustand"], "blockiert")
        self.assertIn("E12", {f["code"] for f in zeile["funde"]})
        self.assertFalse(zeile["freigabe"])
        self.assertNotIn("cadence_wait", self.lies(pfad))

    def test_spam_status_rot_sperrt_auto_freigabe(self):
        self.schreibe_post("2026-10-03-gruen-aber-rot-status")
        with open(er.SPAM_STATUS_FILE, "w", encoding="utf-8") as fh:
            json.dump({"urteil": "rot",
                       "probleme": ["KI-Anteil live: 90 %"]}, fh)
        summary = er.lauf(er.lade_config())
        self.assertEqual(summary["freigaben"], 0)
        zeile = summary["details"][0]
        self.assertEqual(zeile["zustand"], "gruen")
        self.assertIn("Spam-Schutz", zeile.get("freigabe_grund", ""))

    def test_fehlendes_statusfile_sperrt_fail_closed(self):
        self.schreibe_post("2026-10-03-ohne-status")
        os.remove(er.SPAM_STATUS_FILE)
        summary = er.lauf(er.lade_config())
        self.assertEqual(summary["freigaben"], 0)
        self.assertIn("kein Spam-Statusfile",
                      summary["details"][0].get("freigabe_grund", ""))

    def test_wochenbudget_voll_sperrt(self):
        # Budget 1/Woche ist bereits durch eine Freigabe von heute belegt.
        # (Eigenständiger Körper/Titel, damit nicht E10/E12 vorher greifen.)
        anderer = ("## Andere Preise\n\n" + ABSATZ + " " + ABSATZ + "\n\n"
                   "## Andere Fristen\n\n" + ABSATZ + "\n\n"
                   "## Anderer Vertrag\n\n" + ABSATZ + "\n\n"
                   + ("Die Rate bleibt gleich. " * 400))
        self.schreibe_post(
            "2026-10-03-bereits-freigegeben", draft=False,
            extra_fm="endredaktion_status: freigegeben\n",
            titel="Gaskosten senken: der andere Weg",
            description="Gaskosten senken mit klaren Schritten und "
                        "ehrlichen Zahlen für deinen Haushalt im Alltag.",
            body=anderer)
        with open(er.CONFIG_FILE, "w", encoding="utf-8") as fh:
            fh.write("modus: automatisch\nmax_freigaben_pro_lauf: 1\n"
                     "auto_freigaben_max_pro_woche: 1\n")
        pfad = self.schreibe_post("2026-10-04-zweiter-gruener")
        summary = er.lauf(er.lade_config())
        self.assertEqual(summary["freigaben"], 0)
        self.assertIn("Wochenbudget",
                      summary["details"][0].get("freigabe_grund", ""))
        self.assertNotIn("cadence_wait", self.lies(pfad))


if __name__ == "__main__":
    unittest.main()
