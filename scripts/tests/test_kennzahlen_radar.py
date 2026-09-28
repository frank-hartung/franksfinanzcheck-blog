#!/usr/bin/env python3
"""Tests für den Kennzahlen-Radar (scripts/kennzahlen_radar.py).

Quick Win H5 (Konkurrenz-Analyse Finanztip, 28.09.2026): Der Radar
ist das Frühwarnsystem für harte Kennzahlen (Fälligkeit, Brief-Signale,
Artikel-Kopplung). Diese Tests nageln die Kernlogik fest:

  1. Priorisierung: P1 (fällig + Signal) > P2 (fällig) > P3 (Signal) > OK.
  2. Brief-Signale zählen nur, wenn der Brief NEUER ist als der
     Prüfstand – alte Briefe sind keine Frühwarnung.
  3. Artikel-Kopplung: lastmod vor Kennzahlenstand = Flag.
  4. Register-Validierung: Affiliate-/Nicht-Allowlist-Quellen werden
     abgelehnt (Anti-Halluzinations-Vertrag).
  5. Queue/Issue enthalten nur P1/P2 bzw. den Ablauf-Vertrag.

Läuft deterministisch ohne Netz
(`python3 -m unittest discover -s scripts/tests`).
"""
from __future__ import annotations

import datetime
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import kennzahlen_radar as kr  # noqa: E402

AS_OF = datetime.date(2026, 9, 28)


def _gruet(tmp):
    """Standard-Gerüst: Post (alt), Pillar (neu), neuer Brief, alter Brief."""
    os.makedirs(os.path.join(tmp, "content", "posts", "post-a"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "content", "pillar", "strom"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "data", "research"), exist_ok=True)
    with open(os.path.join(tmp, "content", "posts", "post-a", "index.md"), "w",
              encoding="utf-8") as f:
        f.write("---\ntitle: \"Post A\"\nlastmod: 2026-08-01\ndate: 2026-07-01\n---\nText")
    with open(os.path.join(tmp, "content", "pillar", "strom", "index.md"), "w",
              encoding="utf-8") as f:
        f.write("---\ntitle: \"Strom-Ratgeber\"\nlastmod: 2026-09-20\n---\nText")
    with open(os.path.join(tmp, "data", "research", "2026-09-21-internet-recherche.md"),
              "w", encoding="utf-8") as f:
        f.write("# Brief\n\nDer Strompreis steigt laut BDEW auf 40 ct/kWh.\n")
    with open(os.path.join(tmp, "data", "research", "2026-07-01-internet-recherche.md"),
              "w", encoding="utf-8") as f:
        f.write("# Alter Brief\n\nStrompreis-Altmodung (darf kein Signal sein).\n")


def _eintrag(**over):
    e = {
        "id": "k1", "name": "Strompreis", "einheit": "ct/kWh",
        "ist_wert": "37,0", "stand": datetime.date(2026, 8, 21),
        "quelle": {"name": "BDEW", "url": "https://www.bdew.de/x"},
        "rhythmus_tage": 30, "ymyl": True,
        "suchbegriffe": ["Strompreis", "BDEW"],
        "betroffene_slugs": ["post-a", "pillar/strom"],
    }
    e.update(over)
    return e


class TestPriorisierung(unittest.TestCase):
    def test_p1_faellig_mit_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag()], AS_OF, slug_check=False)
            self.assertEqual(regeln[0]["prioritaet"], "P1")

    def test_p2_faellig_ohne_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag(suchbegriffe=["gibtsnicht"])],
                                AS_OF, slug_check=False)
            self.assertEqual(regeln[0]["prioritaet"], "P2")

    def test_p3_signal_ohne_faelligkeit(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(
                tmp, [_eintrag(rhythmus_tage=365)], AS_OF, slug_check=False)
            self.assertEqual(regeln[0]["prioritaet"], "P3")

    def test_ok_im_rhythmus(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(
                tmp, [_eintrag(rhythmus_tage=365, suchbegriffe=["gibtsnicht"])],
                AS_OF, slug_check=False)
            self.assertEqual(regeln[0]["prioritaet"], "OK")

    def test_sortierung_p1_zuerst(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [
                _eintrag(id="ok", rhythmus_tage=365, suchbegriffe=["x"]),
                _eintrag(id="p1"),
            ], AS_OF, slug_check=False)
            self.assertEqual([r["id"] for r in regeln], ["p1", "ok"])


class TestBriefSignale(unittest.TestCase):
    def test_nur_neuere_briefs_zaehlen(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            signale = kr.scan_signale(tmp, ["Strompreis"],
                                      datetime.date(2026, 8, 21), AS_OF)
            self.assertTrue(signale)
            self.assertTrue(all(s["datum"] > "2026-08-21" for s in signale))

    def test_brief_ohne_datum_wird_ignoriert(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "research"), exist_ok=True)
            with open(os.path.join(tmp, "data", "research", "ohne-datum.md"), "w",
                      encoding="utf-8") as f:
                f.write("# Kopflos\n\nStrompreis ohne Datumsangabe.\n")
            signale = kr.scan_signale(tmp, ["Strompreis"],
                                      datetime.date(2026, 1, 1), AS_OF)
            self.assertEqual(signale, [])

    def test_brief_nach_as_of_zaehlt_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "research"), exist_ok=True)
            with open(os.path.join(tmp, "data", "research", "2026-10-30-zukunft.md"), "w",
                      encoding="utf-8") as f:
                f.write("# Zukunft\n\nStrompreis aus der Zukunft.\n")
            signale = kr.scan_signale(tmp, ["Strompreis"],
                                      datetime.date(2026, 1, 1), AS_OF)
            self.assertEqual(signale, [])


class TestArtikelKopplung(unittest.TestCase):
    def test_artikel_hinkt_hinterher(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag()], AS_OF, slug_check=False)
            post = next(a for a in regeln[0]["artikel"] if a["slug"] == "post-a")
            self.assertIn("hinterher", post)

    def test_aktueller_artikel_ohne_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag()], AS_OF, slug_check=False)
            pillar = next(a for a in regeln[0]["artikel"]
                          if a["slug"] == "pillar/strom")
            self.assertNotIn("hinterher", pillar)

    def test_unbekannter_slug_wird_markiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag(betroffene_slugs=["gibts-nicht"])],
                                AS_OF, slug_check=True)
            self.assertTrue(any("problem" in a for a in regeln[0]["artikel"]))


class TestRegisterValidierung(unittest.TestCase):
    def _schreibe_register(self, tmp, url):
        path = os.path.join(tmp, "register.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "meta: {version: 1}\n"
                "kennzahlen:\n"
                "  - id: k1\n"
                "    name: Test\n"
                "    stand: 2026-09-01\n"
                f"    quelle: {{name: Q, url: '{url}'}}\n"
                "    rhythmus_tage: 30\n"
                "    suchbegriffe: [Strom]\n"
                "    betroffene_slugs: [post-a]\n"
            )
        return path

    def test_affiliate_quelle_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "agent_reach"), exist_ok=True)
            with open(os.path.join(tmp, "data", "agent_reach", "faktenfrische.yaml"),
                      "w", encoding="utf-8") as f:
                f.write("quellen_allowlist:\n  - {domain: bdew.de, rang: 2}\n")
            old = kr.ALLOWLIST_PATH
            kr.ALLOWLIST_PATH = os.path.join(
                tmp, "data", "agent_reach", "faktenfrische.yaml")
            try:
                _, _, fehler = kr.load_register(self._schreibe_register(
                    tmp, "https://check24.net/vergleiche"))
                self.assertTrue(any("Allowlist" in f for f in fehler))
            finally:
                kr.ALLOWLIST_PATH = old

    def test_erlaubte_quelle_durchlaeuft(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "agent_reach"), exist_ok=True)
            with open(os.path.join(tmp, "data", "agent_reach", "faktenfrische.yaml"),
                      "w", encoding="utf-8") as f:
                f.write("quellen_allowlist:\n  - {domain: bdew.de, rang: 2}\n")
            old = kr.ALLOWLIST_PATH
            kr.ALLOWLIST_PATH = os.path.join(
                tmp, "data", "agent_reach", "faktenfrische.yaml")
            try:
                _, _, fehler = kr.load_register(self._schreibe_register(
                    tmp, "https://www.bdew.de/strompreisanalyse"))
                self.assertFalse(fehler)
            finally:
                kr.ALLOWLIST_PATH = old

    def test_echte_register_datei_ist_valide(self):
        """Guard: das produktive Register muss die Validierung bestehen."""
        if not os.path.exists(kr.REGISTER_PATH):
            self.skipTest("Register noch nicht angelegt")
        _, _, fehler = kr.load_register()
        self.assertEqual(fehler, [], f"Register-Fehler: {fehler}")


class TestAusgaben(unittest.TestCase):
    def test_queue_nur_p1_p2(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [
                _eintrag(),
                _eintrag(id="ok", rhythmus_tage=365, suchbegriffe=["x"]),
            ], AS_OF, slug_check=False)
            qpath = os.path.join(tmp, "queue.json")
            queue = kr.write_queue(regeln, AS_OF, path=qpath)
            self.assertEqual({r["prioritaet"] for r in queue}, {"P1"})

    def test_issue_body_enthält_vertrag(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag()], AS_OF, slug_check=False)
            body = kr.issue_body(regeln, AS_OF)
            self.assertIn("nie selbst", body)       # Register-Vertrag
            self.assertIn("post-a", body)           # betroffener Artikel

    def test_report_enthält_prioritaeten(self):
        with tempfile.TemporaryDirectory() as tmp:
            _gruet(tmp)
            regeln = kr.bewerte(tmp, [_eintrag()], AS_OF, slug_check=False)
            rep = kr.render_report(regeln, AS_OF)
            for marker in ("P1", "Prüfstand", "BDEW"):
                self.assertIn(marker, rep)


if __name__ == "__main__":
    unittest.main()
