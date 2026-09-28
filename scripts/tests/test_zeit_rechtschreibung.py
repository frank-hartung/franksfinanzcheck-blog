#!/usr/bin/env python3
"""Tests für die ZEIT-Niveau-Rechtschreib-Wache (scripts/zeit_rechtschreibung.py).

Auftrag (Frank, 28.09.2026): „Integriere dauerhaft eine professionelle
automatische Rechtschreibprüfung von zeit.de auf Premium-Level einer
Profi-Agentur in meinen Blog.“

Diese Tests nageln die Dauerverträge fest – vollständig OFFLINE via
Fixture-Transport (kein Netz, keine Fremdlibs):

  1. Selbsttest ST1–ST10 grün (Sabotage-Schutz).
  2. Maskierung längentreu (Offsets/Zeilen wahr) + Schutzzonen dicht.
  3. Chunking verlustfrei, Offsets lückenlos, Limit eingehalten.
  4. Offset-Mapping der API-Funde zeigt punktgenau in den Original-Text.
  5. Whitelist-/Ignorier-Filter arbeiten (Marken-Schutz, Begründungspflicht).
  6. Auto-Fix-Gatter: nur Allowlist + ein Vorschlag + keine Titel-Zone.
  7. Zugangs-Ermittlung: Premium-ENV → Premium, ohne ENV + ohne Opt-in →
     offline (Kosten-Regel / ToS-Treue).
  8. End-to-End offline: Fehler-Artikel wird geheilt, Link bleibt stehen,
     Zähler stimmen.
  9. Konfig-Datei data/zeit_rechtschreibung.json bleibt merge- & regeltreu.

Läuft deterministisch ohne Netz
(`python3 -m unittest discover -s scripts/tests`).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import zeit_rechtschreibung as zr  # noqa: E402


def _artikel_dict(path, title="Titel sauber", description="", body="Ein sauberer Satz."):
    content = ("---\n"
               f'title: "{title}"\n'
               f'description: "{description}"\n'
               "date: 2026-09-28T10:00:00Z\n"
               "draft: false\n"
               "---\n\n" + body + "\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return zr.load_articles([path])


class TestSelbsttest(unittest.TestCase):
    def test_selbsttest_gruen(self):
        self.assertEqual(zr.run_selftest(), [])


class TestMaskierung(unittest.TestCase):
    def test_laengentreu_und_zeilen_wahr(self):
        probe = ("# Kopf\n\nFließtext mit **Fett** und `code` und "
                 "[Anker](https://x.de) sowie <img src=\"a\">.\n\n"
                 "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
                 "{{< shortcode arg=\"tief\" >}}\n"
                 "> Zitatrand\n- Listenpunkt\n")
        m = zr.maskiere(probe)
        self.assertEqual(len(m), len(probe))
        self.assertEqual(m.count("\n"), probe.count("\n"))
        for geschuetzt in ("Anker", "img", "code", "shortcode"):
            self.assertNotIn(geschuetzt, m)
        for fliess in ("Kopf", "Fließtext", "Fett", "Zitatrand", "Listenpunkt"):
            self.assertIn(fliess, m)

    def test_echtestartikel_bleibt_offsettreu(self):
        probe = "Abstand zwischen **Preis** und 150&nbsp;Euro bleibt."
        m = zr.maskiere(probe)
        self.assertEqual(len(m), len(probe))
        self.assertIn("Preis", m)
        self.assertNotIn("nbsp", m)


class TestChunking(unittest.TestCase):
    def test_verlustfrei_und_lueckenlos(self):
        text = "\n\n".join(f"Absatz {i} mit einigen Worten." for i in range(150))
        chunks = zr.chunken(text, 800)
        self.assertEqual("".join(c for _, c in chunks), text)
        for i in range(1, len(chunks)):
            self.assertEqual(chunks[i][0], chunks[i - 1][0] + len(chunks[i - 1][1]))
        self.assertTrue(all(len(c) <= 800 for _, c in chunks))

    def test_monsterabsatz_wird_am_satzende_geteilt(self):
        text = " ".join(f"Satz Nummer {i} endet hier." for i in range(300))
        chunks = zr.chunken(text, 500)
        self.assertEqual("".join(c for _, c in chunks), text)
        self.assertTrue(all(len(c) <= 500 for _, c in chunks))


class TestZugang(unittest.TestCase):
    def _clean_env(self):
        for k in ("ZR_API_URL", "LT_API_URL", "ZR_USERNAME", "LT_USERNAME",
                  "ZR_API_KEY", "LT_API_KEY", "LT_APIKEY"):
            os.environ.pop(k, None)

    def test_premium_per_schluessel(self):
        self._clean_env()
        try:
            os.environ["ZR_USERNAME"] = "frank@example.de"
            os.environ["ZR_API_KEY"] = "geheim"
            z = zr.zugang_ermitteln(zr.DEFAULT_CONFIG, False)
            self.assertEqual(z["modus"], "premium")
            self.assertEqual(z["api_url"], zr.STANDARD_API_URL)
        finally:
            self._clean_env()

    def test_offline_ohne_jede_konfiguration(self):
        self._clean_env()
        z = zr.zugang_ermitteln(zr.DEFAULT_CONFIG, False)
        self.assertEqual(z["modus"], "offline")

    def test_oeffentlich_nur_mit_optin(self):
        self._clean_env()
        z = zr.zugang_ermitteln(zr.DEFAULT_CONFIG, True)
        self.assertEqual(z["modus"], "oeffentlich")
        self.assertIn("manuelle Nutzung", z["grund"])

    def test_eigener_endpunkt_hat_vorrang(self):
        self._clean_env()
        try:
            os.environ["ZR_API_URL"] = "https://lt.eigen.example/v2/check"
            z = zr.zugang_ermitteln(zr.DEFAULT_CONFIG, True)
            self.assertEqual(z["modus"], "premium")
            self.assertEqual(z["api_url"], "https://lt.eigen.example/v2/check")
        finally:
            self._clean_env()


class TestKostenRegel(unittest.TestCase):
    def test_require_online_wird_blockiert(self):
        cfg = zr._merge(zr.DEFAULT_CONFIG, {"anbieter": {"require_online": True}})
        with self.assertRaises(zr.KonfigFehler):
            zr.pruefe_konfig(cfg)

    def test_offline_fallback_kann_nicht_abgeschaltet_werden(self):
        cfg = zr._merge(zr.DEFAULT_CONFIG,
                        {"anbieter": {"offline_fallback": False}})
        with self.assertRaises(zr.KonfigFehler):
            zr.pruefe_konfig(cfg)

    def test_konfig_datei_baustein_bleibt_regeltreu(self):
        cfg = zr.load_config()
        self.assertFalse(cfg["anbieter"]["require_online"])
        self.assertTrue(cfg["anbieter"]["offline_fallback"])
        self.assertEqual(cfg["anfrage"]["language"], "de-DE")
        self.assertEqual(cfg["anfrage"]["level"], "picky")
        self.assertIn("GERMAN_SPELLER_RULE", cfg["auto_fix"]["regeln"])


class TestFundModell(unittest.TestCase):
    def test_normalisierung_und_zeile(self):
        bezug = "Zeile eins sauber.\nZeile zwei mit Fehlr."
        roh = {"matches": [{
            "message": "Tippfehler", "shortMessage": "Rechtschreibung",
            "replacements": [{"value": "Fehler"}],
            "offset": bezug.index("Fehlr"), "length": 5,
            "sentence": "Zeile zwei mit Fehlr.",
            "rule": {"id": "GERMAN_SPELLER_RULE", "issueType": "misspelling",
                     "category": {"id": "TYPOS", "name": "Typo"},
                     "isPremium": True}}]}
        funde = zr.normalisiere_matches(roh, bezug, 0, "a.md", "fluesstext")
        self.assertEqual(len(funde), 1)
        f = funde[0]
        self.assertEqual(f["fund"], "Fehlr")
        self.assertEqual(f["zeile"], 2)
        self.assertTrue(f["premium"])
        self.assertEqual(f["offset"], bezug.index("Fehlr"))


class TestWhitelistUndIgnorieren(unittest.TestCase):
    def _fund(self, fund, regel="X1", kategorie=""):
        return {"datei": "a", "zone": "fluesstext", "regel": regel,
                "kategorie": kategorie, "kategorie_name": "",
                "problem": "misspelling", "premium": False, "botschaft": "",
                "erklaerung": "", "fund": fund, "offset": 0,
                "laenge": len(fund), "zeile": 1, "vorschlaege": ["x"],
                "url": "", "satz": ""}

    def test_markenwort_geschuetzt(self):
        aktiv, unter = zr.filtere_funde(
            [self._fund("FritzBox"), self._fund("Rechnug")],
            zr.DEFAULT_CONFIG, {"fritzbox"})
        self.assertEqual([f["fund"] for f in aktiv], ["Rechnug"])
        self.assertEqual(len(unter), 1)
        self.assertIn("fritzbox", unter[0]["grund"])

    def test_ignorierte_regel_mit_begruendung(self):
        cfg = zr._merge(zr.DEFAULT_CONFIG,
                        {"ignorieren": {"regeln": ["REDUNDANZ_X"]}})
        aktiv, unter = zr.filtere_funde(
            [self._fund("gratis kostenlos", regel="REDUNDANZ_X")], cfg, set())
        self.assertEqual(aktiv, [])
        self.assertIn("REDUNDANZ_X", unter[0]["grund"])


class TestAutoFixGatter(unittest.TestCase):
    def _fund(self, **kw):
        base = {"datei": "a", "zone": "fluesstext",
                "regel": "GERMAN_SPELLER_RULE", "kategorie": "",
                "kategorie_name": "", "problem": "misspelling",
                "premium": False, "botschaft": "", "erklaerung": "",
                "fund": "Rechnug", "offset": 0, "laenge": 7, "zeile": 1,
                "vorschlaege": ["Rechnung"], "url": "", "satz": ""}
        base.update(kw)
        return base

    def test_eindeutiger_fall_erlaubt(self):
        self.assertTrue(zr.auto_fix_erlaubt(self._fund(), zr.DEFAULT_CONFIG))

    def test_stil_und_mehrfachvorschlaege_blockiert(self):
        self.assertFalse(zr.auto_fix_erlaubt(
            self._fund(problem="style"), zr.DEFAULT_CONFIG))
        self.assertFalse(zr.auto_fix_erlaubt(
            self._fund(vorschlaege=["Rechnung", "Rechnungen"]),
            zr.DEFAULT_CONFIG))

    def test_titel_und_struktur_tabu(self):
        self.assertFalse(zr.auto_fix_erlaubt(
            self._fund(zone="title"), zr.DEFAULT_CONFIG))
        self.assertFalse(zr.auto_fix_erlaubt(
            self._fund(vorschlaege=["[Rechnung](x)"]), zr.DEFAULT_CONFIG))

    def test_tatsaechliche_fixe_whitelist_aus_datei(self):
        cfg = zr.load_config()
        self.assertTrue(zr.auto_fix_erlaubt(self._fund(), cfg))


class TestCacheUndAnfragezaehlung(unittest.TestCase):
    def test_cache_spart_anfragen(self):
        antwort = {"matches": [{
            "message": "Meinten Sie?", "shortMessage": "",
            "replacements": [{"value": "besten"}],
            "offset": 19, "length": 6, "sentence": "…",
            "rule": {"id": "GERMAN_SPELLER_RULE", "issueType": "misspelling",
                     "category": {"id": "TYPOS", "name": "Typo"}}}]}

        def antworte(text):
            a = dict(antwort)
            a["matches"] = [dict(m) for m in antwort["matches"]]
            if "bestem" not in text:
                a["matches"] = []
            return a

        counter = [0]
        client = zr._fake_client([(None, antworte)], counter)
        with tempfile.TemporaryDirectory() as td:
            arts = _artikel_dict(os.path.join(td, "a.md"),
                                 body="Das Brot backt man am bestem heute frisch.")
            art = arts[0]
            cfg = dict(zr.DEFAULT_CONFIG)
            cache = {"version": 1, "eintraege": {}}
            aktiv1, unter1, roh1, hit1, noti1 = zr.online_funde_fuer_artikel(
                client, art, cfg, "a.md", "fp", cache, True, set())
            self.assertFalse(hit1)
            self.assertEqual(len(aktiv1), 1)
            stand = counter[0]
            aktiv2, _u, _r, hit2, _n = zr.online_funde_fuer_artikel(
                client, art, cfg, "a.md", "fp", cache, True, set())
            self.assertTrue(hit2)
            self.assertEqual(counter[0], stand)  # keine neue Anfrage
            self.assertEqual(aktiv1, aktiv2)     # gleiches Ergebnis
            # Premium-Chunking: mit Benutzer gilt das Premium-Limit
            self.assertGreater(counter[0], 0)


class TestEndToEndOffline(unittest.TestCase):
    def test_fehlerartikel_wird_geheilt_link_bleibt(self):
        with tempfile.TemporaryDirectory() as td:
            pfad = os.path.join(td, "fehler.md")
            body = ("Du sparst seid drei Jahren. "
                    "[Mein Ratgeber](../../posts/x/) bleibt stehen. "
                    "Vorallem im Winter lohnt sich das.")
            arts = _artikel_dict(pfad, description="Kurz, wo mit du sparst.",
                                 body=body)
            erg = zr.laufe(files=[pfad], do_fix=True, offline=True,
                           progress=lambda *a, **k: None)
            # Da --file basierend auf load_articles neu geladen wird:
            erg2 = zr.laufe(files=[pfad], do_fix=False, offline=True,
                            progress=lambda *a, **k: None)
            self.assertGreaterEqual(erg["geheilt"], 3)
            self.assertEqual(erg2["offen"], 0)
            with open(pfad, encoding="utf-8") as fh:
                inhalt = fh.read()
            self.assertIn("seit drei Jahren", inhalt)
            self.assertIn("womit du sparst", inhalt)
            self.assertRegex(inhalt, r"(?i)\bvor allem\b")
            self.assertIn("[Mein Ratgeber](../../posts/x/) bleibt stehen.",
                          inhalt)

    def test_besitzer_felder_vorhanden(self):
        with tempfile.TemporaryDirectory() as td:
            pfad = os.path.join(td, "f.md")
            _artikel_dict(pfad, body="Du sparst seid drei Jahren hier.")
            erg = zr.laufe(files=[pfad], offline=True,
                           progress=lambda *a, **k: None)
            self.assertTrue(erg["funde"])
            for f in erg["funde"]:
                for feld in ("owner", "severity", "channel"):
                    self.assertTrue(f.get(feld), f"Feld {feld} fehlt")


class TestBerichtsartefakte(unittest.TestCase):
    def test_report_und_history_schreiben(self):
        with tempfile.TemporaryDirectory() as td:
            alt_report = zr.REPORT_FILE
            alt_json = zr.JSON_FILE
            zr.REPORT_FILE = os.path.join(td, "R.md")
            zr.JSON_FILE = os.path.join(td, "r.json")
            try:
                cfg = zr._merge(zr.DEFAULT_CONFIG,
                                {"history": {"pfad": os.path.join(td, "h.jsonl"),
                                             "max": 50}})
                erg = {"modus": "offline", "provider_grund": "Test",
                       "produkt": "Test", "artikel": 2, "anfragen": 0,
                       "cache_treffer": 0, "funde": [], "unterdrueckt": [],
                       "geheilt": 1, "premium_funde": 0, "offen": 0,
                       "notizen": [], "items": []}
                zr.schreibe_report(erg)
                zr.schreibe_json(erg)
                zr.schreibe_history(cfg, erg)
                zr.schreibe_history(cfg, erg)  # Dedupe gleiches Datum
                with open(os.path.join(td, "h.jsonl"), encoding="utf-8") as fh:
                    zeilen = [l for l in fh if l.strip()]
                self.assertEqual(len(zeilen), 1)
                self.assertTrue(os.path.getsize(zr.REPORT_FILE) > 200)
                with open(zr.JSON_FILE, encoding="utf-8") as fh:
                    d = json.load(fh)
                self.assertEqual(d["engine"], "zeit_rechtschreibung")
                self.assertEqual(d["geheilt"], 1)
            finally:
                zr.REPORT_FILE = alt_report
                zr.JSON_FILE = alt_json


if __name__ == "__main__":
    unittest.main()
