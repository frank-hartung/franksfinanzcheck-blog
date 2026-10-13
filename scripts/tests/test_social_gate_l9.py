#!/usr/bin/env python3
"""Regressionstest: social_gate L9 (Fakten-Treue) + Thread-Bewertung.

Anlass (Meldung #716, 12.10.2026): Der Kanal Mastodon sendete 48 Stunden
nicht. Ursache war ein FALSCHURTEIL der Fakten-Regel: Der Texter baut aus
dem Keyword „50-30-20-Regel" das Hashtag „#503020Regel". Die Ziffernfolge
503020 steht so in keinem Artikel – wohl aber die drei Einzelzahlen
50 / 30 / 20. L9 prüfte den rohen Text inklusive Hashtag-Block, meldete
„L9 Zahl ohne Beleg im Artikel: 503020" und blockierte den Ratgeber in
jedem Winkel dauerhaft. Fünf verlorene Slots später war der Kanal stumm.

Nebenbefund derselben Meldung: Das Gate bewertete nur `pkg["text"]`. Bei
Threads stehen Link und Hashtags aber im Schlussteil – damit meldete L2
„Link fehlt" und L4 „zu wenige Hashtags" für JEDEN Thread, der Winkel
`thread` war auf Mastodon und Bluesky unbenutzbar.

Dieser Test hält beide Seiten des Vertrags fest:
  · Zahlen aus dem Artikel bleiben erlaubt (auch als Hashtag-Verkettung),
  · erfundene Zahlen blockieren weiterhin – im Fließtext WIE im Hashtag.
Ein Gate, das nur noch durchwinkt, wäre genauso kaputt wie eines, das
grundlos blockiert.
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import social_channels as sch     # noqa: E402
import social_copywriter as copy  # noqa: E402
import social_gate as gate        # noqa: E402

CFG = sch.load_config()
CHANNELS = sch.channel_map(CFG)
META = sch.meta_of(CFG)
MASTODON = CHANNELS["mastodon"]
# Der echte Artikel aus dem Vorfall – bewusst kein Kunst-Fixture, damit der
# Test am Bestand urteilt, der den Ausfall verursacht hat.
VORFALL_SLUG = "2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026"


def _artikel_pool() -> dict:
    base = str(META.get("base_url") or copy.DEFAULT_BASE)
    return {a["slug"]: a for a in copy.article_pool(base_url=base)}


def _artikel(slug: str) -> dict:
    pool = _artikel_pool()
    if slug not in pool:
        raise unittest.SkipTest(f"Artikel {slug} nicht im Bestand")
    return pool[slug]


def _pkg(artikel: dict, winkel: str = "nutzen", kanal: str = "mastodon") -> dict:
    ch = CHANNELS[kanal]
    pkg = copy.compose(artikel, kanal, ch, winkel, META, use_llm=False)
    src = os.path.join(ROOT, "static", artikel.get("cover") or "")
    if os.path.isfile(src):
        pkg["media_path"] = src
        pkg["media_url"] = f"https://franksfinanzcheck.de/{artikel.get('cover')}"
    return pkg


class TestZahlBelegt(unittest.TestCase):
    """Die Beleg-Logik isoliert – Verkettung, Trennzeichen, Erfindung."""

    def test_verkettung_aus_artikelzahlen(self):
        self.assertTrue(gate.zahl_belegt("503020", {"50", "30", "20"}))
        self.assertTrue(gate.zahl_belegt("503020", {"20", "30", "50", "2.800"}))

    def test_erfundene_zahl_bleibt_erfunden(self):
        self.assertFalse(gate.zahl_belegt("1234", {"50", "30", "20"}))
        self.assertFalse(gate.zahl_belegt("9999", {"240", "20"}))
        # Verkettung gilt nur, wenn sie RESTLOS aus belegten Zahlen besteht:
        # „5030" = 50 + 30 ist gedeckt, „5031" ist es nicht (31 steht nirgends).
        self.assertTrue(gate.zahl_belegt("5030", {"50", "30", "20"}))
        self.assertFalse(gate.zahl_belegt("5031", {"50", "30", "20"}))

    def test_tausendertrenner_sind_schreibweise(self):
        self.assertTrue(gate.zahl_belegt("2800", {"2.800"}))
        self.assertTrue(gate.zahl_belegt("2.800", {"2800"}))

    def test_direkter_treffer(self):
        self.assertTrue(gate.zahl_belegt("240", {"240", "20"}))


class TestL9Vorfall716(unittest.TestCase):
    """Der blockierte Ratgeber muss wieder durch das Gate kommen."""

    def test_alle_winkel_sendbar(self):
        art = _artikel(VORFALL_SLUG)
        winkel = [a for a in (MASTODON.get("angles") or []) if a != "thread"]
        self.assertTrue(winkel, "Playbook ohne Winkel?")
        for ang in winkel:
            with self.subTest(winkel=ang):
                ok, viol, _ = gate.check(_pkg(art, ang), MASTODON, META, history=[])
                self.assertTrue(ok, f"{ang}: {viol}")

    def test_hashtag_503020_ist_belegt(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "nutzen")
        self.assertIn("#503020Regel", pkg["text"],
                      "Ausgangsfall verändert – Test bitte am echten Text prüfen")
        ok, viol, _ = gate.check(pkg, MASTODON, META, history=[])
        self.assertTrue(ok, f"L9 blockiert weiterhin: {viol}")

    def test_erfundene_zahl_im_fliestext_blockiert(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "nutzen")
        pkg["text"] = pkg["text"].replace("50 %", "9876 %", 1)
        ok, viol, _ = gate.check(pkg, MASTODON, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L9 Zahl ohne Beleg im Artikel" in v for v in viol), viol)

    def test_erfundene_zahl_im_hashtag_blockiert(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "nutzen")
        pkg["text"] = pkg["text"].replace("#503020Regel", "#1234EuroRegel", 1)
        ok, viol, _ = gate.check(pkg, MASTODON, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L9 Zahl im Hashtag ohne Beleg" in v for v in viol), viol)


class TestThreadBewertung(unittest.TestCase):
    """Ein Thread wird als GANZER Beitrag bewertet, je Teil auf Länge."""

    def test_thread_winkel_ist_sendbar(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "thread")
        self.assertGreater(len(pkg.get("thread") or []), 1, "kein Thread gebaut")
        ok, viol, _ = gate.check(pkg, MASTODON, META, history=[])
        self.assertTrue(ok, f"Thread blockiert: {viol}")

    def test_link_im_schlussteil_zaehlt(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "thread")
        self.assertNotIn(pkg["url"], pkg["text"], "Link steht nicht mehr nur im Schluss")
        self.assertIn(pkg["url"], "\n".join(pkg["thread"]))

    def test_ueberlanges_teil_faellt_auf(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "thread")
        pkg["thread"] = [pkg["thread"][0], "x" * 900]
        ok, viol, _ = gate.check(pkg, MASTODON, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any(v.startswith("L1 zu lang") for v in viol), viol)

    def test_zu_viele_teile_faellt_auf(self):
        art = _artikel(VORFALL_SLUG)
        pkg = _pkg(art, "thread")
        maximum = int(((MASTODON.get("text") or {}).get("thread") or {}).get("max_parts") or 5)
        pkg["thread"] = pkg["thread"] + ["Teil"] * (maximum + 3)
        ok, viol, _ = gate.check(pkg, MASTODON, META, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("Thread zu lang" in v for v in viol), viol)


class TestL7Kennzahl(unittest.TestCase):
    """Geschrei wird am Fließtext gemessen – nicht an CamelCase-Hashtags."""

    def test_hashtags_zaehlen_nicht_als_geschrei(self):
        ruhig = ("Dein Tarifwechsel läuft in zehn Minuten.\n\n"
                 "#DNSServerWechseln #WLAN #DSL #SchnelleresInternet #DNS")
        self.assertLess(gate.shouting_ratio(ruhig), 0.12)

    def test_geschrieener_text_faellt_weiter_auf(self):
        laut = "JETZT SOFORT WECHSELN UND SPAREN, SONST ZAHLST DU DRAUF!"
        self.assertGreater(gate.shouting_ratio(laut), 0.12)

    def test_urls_zaehlen_nicht_mit(self):
        text = ("Dein Wechsel in drei Schritten. "
                "https://franksfinanzcheck.de/posts/x/?utm_source=mastodon&utm_medium=social")
        self.assertLess(gate.shouting_ratio(text), 0.12)


if __name__ == "__main__":
    unittest.main()
