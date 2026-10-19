"""Tests für Weiterleitungen (data/weiterleitungen.yaml), URL-Wache und Gate-Erweiterung H9.

Ausführen: python3 -m unittest scripts.tests.test_weiterleitungen
"""
import os
import unittest

import scripts.weiterleitungen as wl
import scripts.url_wache as uw
import scripts.index_hygiene_gate as gate

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class QuelleBestand(unittest.TestCase):
    """Der echte Bestand muss grün sein. Schlägt das fehl, ist die Quelle oder der Live-Stand kaputt."""

    @classmethod
    def setUpClass(cls):
        cls.eintraege, cls.entfallen = wl.lade_quelle(BLOG_DIR)
        cls.live = wl.live_urls(BLOG_DIR)

    def test_quelle_ist_gruen(self):
        self.assertEqual(wl.pruefe(self.eintraege, self.entfallen, self.live), [])

    def test_umfang(self):
        # 118 ehemals veröffentlichte URLs: 115 mit Ziel, 3 bewusst 404 (Regel D)
        self.assertEqual(len(self.eintraege), 115)
        self.assertEqual(sum(1 for e in self.entfallen if e["regel"] == "D"), 3)

    def test_geparkter_hausvorsorge_beitrag_hat_pillar_fallback(self):
        url = "/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/"
        route = next((e for e in self.eintraege if e["von"] == url), None)
        self.assertIsNotNone(route)
        self.assertEqual(route["nach"], "/pillar/versicherungen/")
        self.assertEqual(route["regel"], "C")

    def test_tags_nie_weitergeleitet(self):
        self.assertFalse(any(e["von"].startswith("/tags/") for e in self.eintraege))
        self.assertTrue(all(e["regel"] == "E" for e in self.entfallen if e["von"].startswith("/tags/")))

    def test_keine_kette(self):
        von = {e["von"] for e in self.eintraege}
        self.assertFalse(any(e["nach"] in von for e in self.eintraege))

    def test_ziele_sind_live(self):
        self.assertTrue(all(e["nach"] in self.live for e in self.eintraege))

    def test_erzeugte_seiten_stimmen(self):
        # Schlägt fehl, wenn data/weiterleitungen.yaml geändert, aber --build nicht ausgeführt wurde
        self.assertEqual(wl.verify(BLOG_DIR, self.eintraege), [])

    def test_keine_fremden_markierten_seiten(self):
        self.assertEqual(wl.verify(BLOG_DIR, self.eintraege), [])


class Regeln(unittest.TestCase):
    LIVE = {"/posts/2026-10-07-neu/", "/pillar/konto-karten/"}

    def test_regel_a_verlangt_gleichen_rest(self):
        e = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-10-07-neu/", "regel": "A", "grund": "Umbenennung Test"}]
        self.assertTrue(any("Slug-Rest" in x for x in wl.pruefe(e, [], self.LIVE | {"/posts/2026-10-07-alt/"})))

    def test_regel_c_nur_pillar(self):
        e = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-10-07-neu/", "regel": "C", "grund": "Pillar-Fallback Test"}]
        self.assertTrue(any("Pillar" in x for x in wl.pruefe(e, [], self.LIVE)))

    def test_startseite_nie_ziel(self):
        e = [{"von": "/posts/2026-09-21-alt/", "nach": "/", "regel": "C", "grund": "Startseite als Ziel Test"}]
        self.assertTrue(any("ungültig" in x for x in wl.pruefe(e, [], self.LIVE)))

    def test_entwurf_als_ziel_verboten(self):
        e = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-08-18-entwurf/", "regel": "B", "grund": "Entwurf als Ziel"}]
        self.assertTrue(any("nicht live" in x for x in wl.pruefe(e, [], self.LIVE)))


class Selbsttests(unittest.TestCase):
    def test_weiterleitungen_selftest(self):
        self.assertEqual(wl.selftest(), 0)

    def test_url_wache_selftest(self):
        self.assertEqual(uw.selftest(), 0)

    def test_gate_selftest_mit_h9(self):
        self.assertEqual(gate.selftest(), 0)


class Snapshot(unittest.TestCase):
    def test_snapshot_ist_aktuell(self):
        # Ein Befund hier heißt: Live-URLs haben sich geändert, ohne dass die Wache es gesehen hat.
        # Dann Befund prüfen und erst danach `python3 scripts/url_wache.py --snapshot` ausführen.
        eintraege, entfallen = wl.lade_quelle(BLOG_DIR)
        live = wl.live_urls(BLOG_DIR)
        befunde, _ = uw.vergleiche(uw.lade_snapshot(), live, eintraege, entfallen)
        self.assertEqual(befunde, [])


if __name__ == "__main__":
    unittest.main()
