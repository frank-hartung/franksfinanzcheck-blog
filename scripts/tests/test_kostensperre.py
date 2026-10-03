"""Vertragstests der Kostensperre – Schreibschutz vor allen Geldflächen.

AUFTRAG (Frank, 03.10.2026)
„Bitte für beide einen dauerhaften Schreibschutz einrichten, damit
Kostenpflicht dauerhaft verhindert wird."

Gemeint sind die zwei Geldflächen außerhalb der Textkette: die
Vorlese-Stimme (ElevenLabs) und die Rechtschreibung auf ZEIT-Niveau.
Beide sollten ausdrücklich NICHT gelöscht werden – die Vorlese-Stimme
ist hörbar besser als der Gratis-Weg. Gesperrt, nicht amputiert.

Diese Datei prüft die drei Eigenschaften, auf die es ankommt:
  1. FAIL-CLOSED  – im Zweifel gesperrt, nie offen.
  2. VERDRAHTET   – die Geldpfade fragen die Sperre wirklich.
  3. UMKEHRBAR    – eine begründete Freigabe wirkt weiterhin. Sonst wäre
                    es Löschen mit Extraschritten, und das war nicht der
                    Auftrag.
"""
from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import kostensperre as ks  # noqa: E402

FLAECHEN = ("vorlese_stimme", "rechtschreibung_premium")


class SsotVertrag(unittest.TestCase):
    """Die SSOT muss die Wirklichkeit beschreiben."""

    def setUp(self):
        self.ssot = ks.lade_ssot()

    def test_ssot_ist_lesbar(self):
        self.assertFalse(self.ssot.get("_defekt"),
                         "data/kostensperre.yaml ist unlesbar.")

    def test_beide_geldflaechen_sind_verzeichnet(self):
        for fid in FLAECHEN:
            self.assertIsNotNone(
                ks.flaeche(fid, self.ssot),
                f"Geldfläche `{fid}` fehlt in der SSOT – was nicht "
                "verzeichnet ist, wird auch nicht bewacht.")

    def test_alle_geldflaechen_sind_gesperrt(self):
        for fid in FLAECHEN:
            self.assertFalse(
                ks.erlaubt(fid, self.ssot),
                f"`{fid}` ist entsichert. Das ist erlaubt, aber nur mit "
                "Begründung und Datum – und nie unbemerkt.")

    def test_jede_flaeche_nennt_einen_gratis_weg(self):
        for eintrag in self.ssot["flaechen"]:
            self.assertTrue(
                str(eintrag.get("gratis_weg", "")).strip(),
                f"`{eintrag.get('id')}` ohne kostenlosen Weg – eine Sperre "
                "ohne Rückfall wäre ein Ausfall, kein Schutz.")

    def test_wache_meldet_keinen_befund(self):
        self.assertEqual(ks.pruefen(self.ssot), [])


class FailClosed(unittest.TestCase):
    """Im Zweifel gesperrt – jede Lücke wäre eine Rechnung."""

    def setUp(self):
        self.ssot = ks.lade_ssot()

    def test_unbekannte_flaeche_ist_gesperrt(self):
        self.assertFalse(ks.erlaubt("gibt_es_nicht", self.ssot))

    def test_kaputte_ssot_sperrt_alles(self):
        kaputt = {"_defekt": True, "regeln": {}, "flaechen": []}
        for fid in FLAECHEN:
            self.assertFalse(ks.erlaubt(fid, kaputt))

    def test_fehlende_ssot_datei_sperrt_alles(self):
        with tempfile.TemporaryDirectory() as ordner:
            daten = ks.lade_ssot(Path(ordner) / "gibt-es-nicht.yaml")
            self.assertTrue(daten.get("_defekt"))
            for fid in FLAECHEN:
                self.assertFalse(ks.erlaubt(fid, daten))

    def test_freigabe_ohne_begruendung_wirkt_nicht(self):
        """Eine Freigabe ohne Grund ist ein Ausrutscher, kein Beschluss."""
        kopie = copy.deepcopy(self.ssot)
        kopie["flaechen"][0]["freigegeben"] = True
        kopie["flaechen"][0].pop("grund", None)
        kopie["flaechen"][0].pop("datum", None)
        self.assertFalse(ks.erlaubt(kopie["flaechen"][0]["id"], kopie))
        self.assertTrue(ks.pruefen(kopie),
                        "Die Wache meldet die unbegründete Freigabe nicht.")

    def test_wahrheitswert_nicht_true_zaehlt_nicht_als_freigabe(self):
        """„ja", 1 oder „true" sind keine Freigabe – nur echtes True."""
        for wert in ("true", "ja", 1, "1", [], {}):
            kopie = copy.deepcopy(self.ssot)
            kopie["flaechen"][0].update(freigegeben=wert, grund="x",
                                        datum="2026-10-03")
            self.assertFalse(
                ks.erlaubt(kopie["flaechen"][0]["id"], kopie),
                f"Wert {wert!r} wurde als Freigabe gewertet.")

    def test_wache_liefert_false_und_bleibt_ruhig_wenn_leise(self):
        ks._GEMELDET.clear()
        self.assertFalse(ks.wache(FLAECHEN[0], self.ssot, leise=True))


class Umkehrbar(unittest.TestCase):
    """Gesperrt heißt nicht gelöscht – sonst wäre der Auftrag verfehlt."""

    def test_begruendete_freigabe_wirkt(self):
        kopie = copy.deepcopy(ks.lade_ssot())
        kopie["flaechen"][0].update(freigegeben=True,
                                    grund="Hörprobe für die Startseite",
                                    datum="2026-10-03")
        self.assertTrue(
            ks.erlaubt(kopie["flaechen"][0]["id"], kopie),
            "Eine ordentlich begründete Freigabe muss wirken – sonst ist "
            "die Sperre eine Einbahnstraße und faktisch eine Löschung.")

    def test_begruendete_freigabe_erzeugt_keinen_befund(self):
        kopie = copy.deepcopy(ks.lade_ssot())
        kopie["flaechen"][0].update(freigegeben=True, grund="x",
                                    datum="2026-10-03")
        self.assertEqual(ks.pruefen(kopie), [])


class Verdrahtung(unittest.TestCase):
    """Eine Sperre, die niemand ruft, ist Dekoration."""

    def setUp(self):
        self.ssot = ks.lade_ssot()

    def test_jede_flaeche_hat_ihre_engstelle_im_code(self):
        for eintrag in self.ssot["flaechen"]:
            modul = ROOT / eintrag["modul"]
            self.assertTrue(modul.is_file(), f"{modul} fehlt")
            quelle = modul.read_text(encoding="utf-8", errors="ignore")
            self.assertIn(f"def {eintrag['funktion']}", quelle,
                          f"{eintrag['modul']} hat keine Funktion "
                          f"`{eintrag['funktion']}` mehr.")
            self.assertIn("kostensperre", quelle,
                          f"{eintrag['modul']} fragt die Sperre nicht.")
            self.assertIn(eintrag["id"], quelle,
                          f"{eintrag['modul']} nennt die Fläche "
                          f"`{eintrag['id']}` nicht.")

    def test_elevenlabs_schluessel_wird_trotz_env_nicht_geliefert(self):
        """Der harte Beweis: Secret gesetzt, Ausgabe trotzdem null."""
        import ff_voice_backends as vb
        alt = os.environ.get("ELEVENLABS_API_KEY")
        os.environ["ELEVENLABS_API_KEY"] = "sk-sabotage-probe"
        ks._GEMELDET.clear()
        try:
            self.assertEqual(
                vb.get_elevenlabs_api_key(), "",
                "Ein gesetztes Secret aktiviert die Premium-Stimme – genau "
                "das sollte der Schreibschutz verhindern.")
        finally:
            if alt is None:
                os.environ.pop("ELEVENLABS_API_KEY", None)
            else:
                os.environ["ELEVENLABS_API_KEY"] = alt

    def test_rechtschreibung_bleibt_offline_trotz_env(self):
        import zeit_rechtschreibung as zr
        sicherung = {k: os.environ.get(k)
                     for k in ("ZR_USERNAME", "ZR_API_KEY", "ZR_API_URL")}
        os.environ["ZR_USERNAME"] = "probe"
        os.environ["ZR_API_KEY"] = "geheim"
        os.environ.pop("ZR_API_URL", None)
        ks._GEMELDET.clear()
        try:
            modus = zr.zugang_ermitteln(zr.DEFAULT_CONFIG, False)["modus"]
            self.assertEqual(
                modus, "offline",
                "Gesetzte Zugangsdaten schalten den Premium-Dienst scharf – "
                "der Schreibschutz greift nicht.")
        finally:
            for k, v in sicherung.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class GateKennThema(unittest.TestCase):
    """T10 muss dieselbe Lage sehen – zwei Verträge dürfen nicht driften."""

    def test_t10_ist_registriert_und_gruen(self):
        import ki_transportweg as kt
        self.assertIn("T10", kt.REGELN)
        self.assertIn("T10", kt.PRUEFER)
        self.assertEqual(kt.t10_kostensperre(kt.lade_ssot()), [])

    def test_t10_meldet_eine_entsicherte_flaeche(self):
        """Entsichern ist erlaubt – aber es muss im Gate sichtbar werden."""
        import ki_transportweg as kt
        import yaml
        echte = ks.SSOT
        with tempfile.TemporaryDirectory() as ordner:
            daten = ks.lade_ssot()
            daten["flaechen"][0].update(freigegeben=True, grund="Testlauf",
                                        datum="2026-10-03")
            pfad = Path(ordner) / "kostensperre.yaml"
            pfad.write_text(yaml.safe_dump(daten, allow_unicode=True),
                            encoding="utf-8")
            ks.SSOT = pfad
            try:
                befunde = kt.t10_kostensperre(kt.lade_ssot())
            finally:
                ks.SSOT = echte
        self.assertTrue(any("ENTSICHERT" in b for b in befunde),
                        "T10 schweigt zu einer offenen Geldfläche.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
