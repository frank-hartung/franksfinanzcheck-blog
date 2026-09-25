#!/usr/bin/env python3
"""Unit-Tests: newsletter_digest.py – Eigenbetrieb-Versand + Capture-Wache.

Architektur (2026): der Capture läuft über den Cloudflare-Worker (KV + Tokens),
der Versand über GitHub Actions. Pro Empfänger werden die Studio-Marken in
`marken_einsetzen` aufgelöst – mit Token zeigen die Links auf die Journey-
Endpunkte des Workers, ohne Token (Testversand) auf die ehrlichen Infoseiten.

Hermetisch: kein Netz, kein echtes Datum, Schreibzugriffe nur in Temp-Verzeichnisse.
Die End-to-End-Lifecycle-Spielfähre (komplett → idempotent → Teilverband →
Nachgang) lebt im Modul-Selftest (`--selftest`), hier ist die Verdrahtung.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load(name: str, rel: str):
    pfad = os.path.join(ROOT, "scripts", rel)
    spec = importlib.util.spec_from_file_location(name, pfad)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


digest = _load("newsletter_digest", "newsletter_digest.py")
# derselbe Modul-Objekt, den der Digest referenziert (Patches wirken nur darauf)
versand = digest.versand

MAT = [
    {"slug": "s1", "titel": "Stromrechnung prüfen", "beschreibung": "Bis zu 240 € sind drin.",
     "url": "/posts/s1/", "path": "", "datum": "2026-09-22", "pillar": "strom-sparen",
     "quelle_text": "Beim Wechsel lassen sich 240 € im Jahr sparen."},
    {"slug": "s2", "titel": "DSL-Wechselbonus", "beschreibung": "Bonus: 120 €.",
     "url": "/posts/s2/", "path": "", "datum": "2026-09-22", "pillar": "internet-dsl",
     "quelle_text": "Der Bonus liegt bei 120 €."},
    {"slug": "s3", "titel": "Kaputt ist nicht gleich kaputt", "beschreibung": "Reparatur lohnt sich.",
     "url": "/posts/s3/", "path": "", "datum": "2026-09-22", "pillar": "kaputt",
     "quelle_text": "Reparatur statt Neukauf."},
]
WERKER = "https://abos.beispiel.de"


class MarkenTest(unittest.TestCase):
    """`marken_einsetzen`: ein Vertrag, zwei Ziele – Worker oder Infoseite."""

    def test_mit_token_gehen_die_links_auf_den_worker(self):
        html, text = digest.marken_einsetzen(
            "A {{unsubscribe}} B {{update_profile}} C {{mirror}}",
            "a {{unsubscribe}} b {{update_profile}} c {{mirror}}",
            "tok-123", worker_basis=WERKER)
        self.assertIn(f"{WERKER}/abmeldung?token=tok-123", html)
        self.assertIn(f"{WERKER}/praferenzen?token=tok-123", html)
        self.assertIn(f"{WERKER}/abmeldung?token=tok-123", text)
        self.assertNotIn("{{unsubscribe}}", html + text)
        self.assertNotIn("{{update_profile}}", html + text)

    def test_mit_token_zeigt_mirror_auf_die_uebersicht(self):
        html, _ = digest.marken_einsetzen("{{mirror}}", "", "tok-1", worker_basis=WERKER)
        self.assertIn("/newsletter/", html)
        self.assertNotIn("?token=", html)  # die Übersicht kennt kein Token

    def test_ohne_token_fallen_die_links_auf_infoseiten_zurueck(self):
        html, text = digest.marken_einsetzen(
            "A {{unsubscribe}} B {{update_profile}}", "a {{unsubscribe}}",
            "", worker_basis=WERKER)
        self.assertIn("/newsletter/abmelden/", html)
        self.assertIn("/newsletter/praeferenzen/", html)
        self.assertIn("/newsletter/abmelden/", text)
        # ein Testempfaenger muss keine scheinbare Abmeldung klickbar kriegen
        self.assertNotIn("?token=", html)
        self.assertNotIn("?token=", text)

    def test_basis_mit_schliessendem_schlash_keine_doppelten_schlaeche(self):
        html, _ = digest.marken_einsetzen("{{unsubscribe}}", "", "t",
                                          worker_basis=WERKER + "/")
        self.assertIn(f"{WERKER}/abmeldung?token=t", html)
        self.assertNotIn("//abmeldung", html)

    def test_fehlende_marke_wird_nicht_erschuettet(self):
        html, text = digest.marken_einsetzen("keine Marken hier", "auch keine",
                                             "t", worker_basis=WERKER)
        self.assertEqual(html, "keine Marken hier")
        self.assertEqual(text, "auch keine")

    def test_leere_basis_ist_kein_worker(self):
        html, _ = digest.marken_einsetzen("{{unsubscribe}}", "", "t", worker_basis="")
        self.assertIn("/newsletter/abmelden/", html)
        self.assertNotIn("?token=", html)


class ThemenFilterTest(unittest.TestCase):
    """`themen_filter`: die Auswahl des Abonnenten ist die Grenze der Ausgabe."""

    def test_ohne_auswahl_kommt_alles(self):
        self.assertEqual(len(digest.themen_filter(MAT, [])), 3)

    def test_mit_auswahl_kommt_nur_das_ausgewaehlte(self):
        sel = digest.themen_filter(MAT, ["strom-sparen"])
        self.assertEqual([a["slug"] for a in sel], ["s1"])

    def test_nichts_passt_ist_leer_nicht_erschlagen(self):
        self.assertEqual(digest.themen_filter(MAT, ["mietwagen"]), [])


class AusgabeTest(unittest.TestCase):
    """`baue_ausgabe`/`baue_digest`: Material wird zu einer Mail – Marken bleiben stehen."""

    def test_ausgabe_traegt_artikel_und_marken(self):
        e = digest.baue_ausgabe(MAT, "2026-09-22",
                                "Zweimal pro Woche: dienstags und freitags.",
                                root=ROOT)
        self.assertEqual(e["anzahl"], 3)
        self.assertIn("Stromrechnung prüfen", e["html"])
        self.assertIn("Stromrechnung prüfen", e["text"])
        self.assertIn("{{unsubscribe}}", e["html"])
        self.assertTrue(e["betreff"])

    def test_baue_digest_fassade_liefert_dreier(self):
        html, text, anzahl = digest.baue_digest(MAT, "2026-09-22", "zw.")
        self.assertEqual(anzahl, 3)
        self.assertIn("{{mirror}}", html)


class StateTest(unittest.TestCase):
    """Zustandsdatei: schreiben/lesen ist deterministisch (Sortierung!)."""

    def test_roundtrip_haltert_sortierte_verseichnisse(self):
        with tempfile.TemporaryDirectory() as td:
            state = {"pending": ["s3", "s1"], "zuletzt_versandt": "2026-09-22",
                     "letzte_ausgabe": {"datum": "2026-09-22", "betreff": "B",
                                        "transport": "resend"}}
            digest.speichere_state(td, state)
            roh = open(os.path.join(td, "data", "newsletter_state.json"),
                       encoding="utf-8").read()
            gelesenes = digest.lade_state(td)
            self.assertEqual(gelesenes["pending"], state["pending"])
            self.assertEqual(gelesenes["letzte_ausgabe"]["betreff"], "B")
            self.assertIn("letzte_ausgabe", roh)

    def test_kaputtes_json_liefert_leeren_zustand(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "data"), exist_ok=True)
            open(os.path.join(td, "data", "newsletter_state.json"), "w").write("{kaputt")
            self.assertEqual(digest.lade_state(td), {})

    def test_leere_state_datei_liefert_leeren_zustand(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(digest.lade_state(td), {})


class AdressTest(unittest.TestCase):
    """Testadressen: streng, denn ein falsches Ziel ist die Mail, die niemand will."""

    def test_mehrere_adressen_trennung_und_duplikate(self):
        liste, fehler = digest.test_adressen_lesen(
            "a@beispiel.de, b@beispiel.de\na@beispiel.de; C@Beispiel.de")
        self.assertEqual(fehler, "")
        self.assertEqual(liste, ["a@beispiel.de", "b@beispiel.de", "c@beispiel.de"])

    def test_ungueltig_bricht_ab(self):
        liste, fehler = digest.test_adressen_lesen("a@beispiel.de, kein@adresse")
        self.assertEqual(liste, [])
        self.assertIn("keine gültige", fehler.lower())

    def test_klammerform_wird_entleert(self):
        self.assertEqual(digest.email_aus_text('Max Mustermann <MAX@Beispiel.DE >'),
                         "max@beispiel.de")

    def test_muell_wird_ablehnt(self):
        self.assertEqual(digest.email_aus_text("a@b"), "")
        self.assertEqual(digest.email_aus_text(".a@b.de"), "")
        self.assertEqual(digest.email_aus_text("a@b.de."), "")
        self.assertEqual(digest.email_aus_text(""), "")


class WorkerListeTest(unittest.TestCase):
    """`worker_liste` fragt den geschützten Export ab – fail-closed bei Fehlern."""

    def test_liste_wird_geliefert(self):
        echt = versand.worker_abfrage

        def fake(pfad, body, *, base=None, key=None):
            self.assertEqual(pfad, "/export/abonnenten")
            self.assertEqual(base, WERKER)
            self.assertEqual(key, "k")
            return {"abonnenten": [{"email": "a@b.de", "token": "t", "themen": []}]}

        versand.worker_abfrage = fake
        try:
            liste = digest.worker_liste(WERKER, "k")
        finally:
            versand.worker_abfrage = echt
        self.assertEqual(liste[0]["email"], "a@b.de")

    def test_kein_liste_feld_liefert_leer(self):
        echt = versand.worker_abfrage
        versand.worker_abfrage = lambda *a, **k: {"status": "ok"}
        try:
            self.assertEqual(digest.worker_liste(WERKER, "k"), [])
        finally:
            versand.worker_abfrage = echt


class CaptureWacheTest(unittest.TestCase):
    """`pruefe_capture`: der Live-Repo ist aktiv; ein leerer Root ist INERT, nicht rot."""

    def test_live_repo_ist_aktiv(self):
        # Die Live-Prüfung braucht den gebauten Bestand (public/). Ein
        # CI-Checkout ohne Build ist keine Fundlage: Der Qualitäts-Gate
        # (link-check.yml) läuft dieselbe Wache am frischen Hugo-Build.
        if not os.path.isdir(os.path.join(ROOT, "public")):
            self.skipTest("kein public/-Build – vom Qualitäts-Gate abgedeckt")
        funde, note, zustand = digest.pruefe_capture(ROOT)
        self.assertEqual(zustand, "aktiv", f"Funde: {funde}")

    def test_leerer_root_ist_inert(self):
        with tempfile.TemporaryDirectory() as td:
            funde, note, zustand = digest.pruefe_capture(td)
            self.assertEqual(zustand, "inert", f"Funde: {funde}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
