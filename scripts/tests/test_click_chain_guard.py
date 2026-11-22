#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regressionstests der Klick-Messkette (#1247).

Anlass: Der Guard prüfte `home`, `/pillar/` und Artikel — eine kuratierte
Auswahl. Jede neue Seitengattung (`/werkzeuge/`, `/so-entstehen-unsere-
vergleiche/`, künftige Hubs) lag damit außerhalb des Vertrags: Ein CTA dort
konnte Event, SubID und Platzierung verlieren, ohne dass ein Lauf das
bemerkte. Zusätzlich verwarf der Guard die Seitenherkunft (`gaps.append(
problem)` statt `f"{lab}: {problem}"`) — im Issue stand dann viermal
derselbe Satz ohne Seite, was daraus eine Suchaufgabe statt einer Meldung
machte.

Diese Tests halten drei Dinge fest:
  1. Jede gebaute HTML-Seite wird gemessen (nicht eine Liste über dem Build).
  2. Jeder Befund nennt die Seite, auf der er steht.
  3. Legitimes HTML klagt nicht an — Minifizierung, Anbieterkennzeichnung,
     interne Navigation.

Der Guard prüft das GEBAUTE HTML. Die Tests hier bauen deshalb kleine
Kunst-Bäume statt einen Hugo-Lauf zu verlangen; nur so laufen sie offline
und in Sekunden.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import click_chain_guard as g  # noqa: E402

SAUBER = ('<a class="ff-btn" href="/go/strom/?subid=artikel-slug" '
          'rel="sponsored nofollow noopener" target="_blank" '
          'data-klick="affiliate_click" data-klick-slug="strom" '
          'data-klick-subid="artikel-slug" data-klick-placement="artikel" '
          'title="Weiter zu CHECK24 (Partnerlink = Werbung)">Strom</a>')


class VertragTest(unittest.TestCase):
    """Der Attribut-Vertrag pro /go/-CTA."""

    def test_sauberer_anker_ist_gruen(self) -> None:
        self.assertEqual([], g.scan_page(SAUBER, "probe"))

    def test_fehlendes_event_wird_gemeldet(self) -> None:
        html = SAUBER.replace('data-klick="affiliate_click"', "")
        texte = [p for _l, p in g.scan_page(html, "probe")]
        self.assertTrue(any("ohne data-klick=affiliate_click" in t for t in texte))

    def test_fehlende_subid_wird_gemeldet(self) -> None:
        html = SAUBER.replace("?subid=artikel-slug", "")
        texte = [p for _l, p in g.scan_page(html, "probe")]
        self.assertTrue(any("ohne ?subid=" in t for t in texte))

    def test_fehlende_platzierung_wird_gemeldet(self) -> None:
        html = SAUBER.replace(' data-klick-placement="artikel"', "")
        texte = [p for _l, p in g.scan_page(html, "probe")]
        self.assertTrue(any("ohne data-klick-placement" in t for t in texte))

    def test_fehlender_slug_wird_gemeldet(self) -> None:
        html = SAUBER.replace(' data-klick-slug="strom"', "")
        texte = [p for _l, p in g.scan_page(html, "probe")]
        self.assertTrue(any("ohne data-klick-slug" in t for t in texte))

    def test_roher_partnerlink_wird_gemeldet(self) -> None:
        html = '<a href="https://a.check24.net/misc/click.php?pid=1">direkt</a>'
        texte = [p for _l, p in g.scan_page(html, "probe")]
        self.assertTrue(any("roher Partnerlink" in t for t in texte))

    def test_interne_navigation_ist_kein_cta(self) -> None:
        """Ohne rel=sponsored ist ein /go/-Link Navigation, kein Affiliate-CTA."""
        html = '<a href="/go/allgemein/">Übersicht</a>'
        self.assertEqual([], g.scan_page(html, "probe"))


class MinifizierungTest(unittest.TestCase):
    """Hugo --minify entfernt Anführungszeichen: kein Messfehler, kein Befund."""

    def test_unquotierte_werte_sind_gruen(self) -> None:
        html = ('<a href="/go/strom/?subid=x" rel="sponsored nofollow noopener" '
                'data-klick=affiliate_click data-klick-slug=strom '
                'data-klick-placement=artikel>Strom</a>')
        self.assertEqual([], g.scan_page(html, "probe"))

    def test_unquotiert_aber_lueckenhaft_wird_gemeldet(self) -> None:
        html = ('<a href="/go/strom/" rel="sponsored nofollow noopener" '
                'data-klick=affiliate_click data-klick-slug=strom>Strom</a>')
        self.assertTrue(g.scan_page(html, "probe"),
                        "Minifizierung darf einen echten Mangel nicht verstecken")

    def test_mehrzeiliger_anker_ist_gruen(self) -> None:
        html = ('<a\n  href="/go/x/?a=1&amp;subid=slug"\n'
                "  rel='sponsored nofollow noopener'\n"
                '  data-klick="affiliate_click" data-klick-slug="x"\n'
                '  data-klick-placement="pillar">y</a>')
        self.assertEqual([], g.scan_page(html, "probe"))


class HerkunftTest(unittest.TestCase):
    """Ein Befund ohne Seite ist eine Suchaufgabe, keine Meldung (#1247)."""

    def test_befund_nennt_die_seite(self) -> None:
        html = '<a href="/go/strom/" rel="sponsored nofollow noopener">Strom</a>'
        befund = g.scan_page(html, "werkzeuge/fixkosten-scanner")
        self.assertTrue(befund)
        self.assertEqual("werkzeuge/fixkosten-scanner", befund[0][0])

    def test_bericht_nennt_die_seite_vor_dem_befund(self) -> None:
        """Die Zeile muss `seite: befund` heißen, nicht nur den Befund."""
        quelle = (ROOT / "scripts" / "click_chain_guard.py").read_text(encoding="utf-8")
        self.assertIn('gaps.append(f"{lab}: {problem}")', quelle,
                      "die Seitenherkunft wird wieder verworfen")


class SiteSucheTest(unittest.TestCase):
    """Gemessen wird der Build, nicht eine Liste über dem Build."""

    def test_findet_seiten_ausserhalb_der_alten_liste(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for rel in ("index.html", "werkzeuge/rechner/index.html",
                        "so-entstehen-unsere-vergleiche/index.html",
                        "tief/verschachtelt/seite.html"):
                pfad = os.path.join(td, rel)
                os.makedirs(os.path.dirname(pfad), exist_ok=True)
                Path(pfad).write_text("<html></html>", encoding="utf-8")
            gefunden = {os.path.relpath(p, td) for p, _l in g.walk_site(td)}
        self.assertIn("werkzeuge/rechner/index.html", gefunden)
        self.assertIn("so-entstehen-unsere-vergleiche/index.html", gefunden)
        self.assertIn("tief/verschachtelt/seite.html", gefunden)

    def test_gateways_werden_nicht_als_inhaltsseiten_geprueft(self) -> None:
        """`/go/`-Seiten sind Weiterleitungen; check_gateway prüft sie separat."""
        with tempfile.TemporaryDirectory() as td:
            for rel in ("index.html", "go/strom/index.html"):
                pfad = os.path.join(td, rel)
                os.makedirs(os.path.dirname(pfad), exist_ok=True)
                Path(pfad).write_text("<html></html>", encoding="utf-8")
            gefunden = {os.path.relpath(p, td) for p, _l in g.walk_site(td)}
        self.assertNotIn("go/strom/index.html", gefunden)

    def test_kennt_namen_der_bekannten_seiten(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for rel in ("index.html", "pillar/index.html"):
                pfad = os.path.join(td, rel)
                os.makedirs(os.path.dirname(pfad), exist_ok=True)
                Path(pfad).write_text("<html></html>", encoding="utf-8")
            labels = dict((os.path.relpath(p, td), l) for p, l in g.walk_site(td))
        self.assertEqual("Startseite", labels.get("index.html"))
        self.assertEqual("Ratgeber-Zentrale", labels.get("pillar/index.html"))


class GatewayTest(unittest.TestCase):
    """Das Gateway muss die SubID weiterreichen, sonst ist die Attribution tot."""

    def _gateway(self, td: str, key: str, inhalt: str) -> None:
        pfad = os.path.join(td, "go", key)
        os.makedirs(pfad, exist_ok=True)
        Path(os.path.join(pfad, "index.html")).write_text(inhalt, encoding="utf-8")

    def test_korrektes_gateway_ist_ruhig(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._gateway(td, "strom",
                          '<meta http-equiv="refresh" content="0; url=x?subid=y">')
            self.assertEqual("", g.check_gateway(td, "strom"))

    def test_gateway_ohne_subid_wird_gemeldet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._gateway(td, "gas", "<p>vergessen</p>")
            self.assertIn("SubID", g.check_gateway(td, "gas"))

    def test_fehlendes_gateway_wird_gemeldet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertIn("Build", g.check_gateway(td, "fehlt"))

    def test_gateway_ohne_weiterleitung_wird_gemeldet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._gateway(td, "dsl", "<p>subid= da, aber kein refresh</p>")
            self.assertIn("refresh", g.check_gateway(td, "dsl"))


class CliTest(unittest.TestCase):
    def test_selftest_gruen(self) -> None:
        lauf = subprocess.run([sys.executable,
                               str(ROOT / "scripts" / "click_chain_guard.py"),
                               "--selftest"],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)

    def test_ohne_build_wird_nicht_gemessen_statt_gruen(self) -> None:
        """Kein Build heißt NICHT GEMESSEN – nie GRÜN (C2)."""
        with tempfile.TemporaryDirectory() as td:
            lauf = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "click_chain_guard.py"),
                 "--public", os.path.join(td, "gibt-es-nicht")],
                capture_output=True, text=True, cwd=ROOT)
        self.assertIn("NICHT GEMESSEN", lauf.stdout)
        self.assertNotIn("GREEN", lauf.stdout,
                         "ohne Messung darf nie GRÜN stehen (C2)")

    def test_leeres_build_ist_amber_nicht_gruen(self) -> None:
        """Ein Build ohne /go/-Seiten ist ein Befund, keine Messlücke.

        Der Unterschied ist wichtig: „nicht gebaut" heißt „nichts geprüft",
        „gebaut, aber Gateways fehlen" heißt „Klicks laufen ins Leere". Die
        zweite Aussage ist eine Tatsache über den Build – sie darf nicht
        hinter „nicht gemessen" verschwinden.
        """
        with tempfile.TemporaryDirectory() as td:
            lauf = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "click_chain_guard.py"),
                 "--public", td],
                capture_output=True, text=True, cwd=ROOT)
        self.assertIn("AMBER", lauf.stdout)
        self.assertIn("kein /go/-Verzeichnis im Build", lauf.stdout)


if __name__ == "__main__":
    unittest.main()
