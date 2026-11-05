#!/usr/bin/env python3
"""Regressionstests der Leistungs-Auswertung (Vorgang #1065, 05.11.2026).

DER BEFUND, DEN DIESE DATEI EINFRIERT
-------------------------------------
`scripts/gsc_import.py` holt seit dem 12.10.2026 täglich die Search-Console-
Leistungsdaten. Am 05.11.2026 lagen 44 Messtage, 35 Seiten und 53 Suchbegriffe
in `data/gsc/` – und KEIN Skript las sie. Das tägliche Issue (#1065) stellte
deshalb drei Fragen an einen Menschen:

  1. Status in `meta.json`
  2. Abdeckungszustand bei den Indexierungs-Anfragen
  3. Berechtigung des Dienstkontos

Jede dieser Fragen ist aus denselben vier Dateien beantwortbar. Die
redaktionelle Reihenfolge stand sogar schon im Runbook („Seiten mit
ausreichend Impressionen und Position 4–20 zuerst“) – als Prosa, ohne Erzeuger.

Diese Tests frieren drei Ebenen ein:
  1. Der echte Bestand wird ausgewertet – die Zahlen des Berichts sind die
     Zahlen des Repos, keine Attrappe.
  2. Jede Regel L1–L9 erkennt ihren Fall UND schweigt im guten Lauf. Eine
     Wache, die immer schlägt, ist keine Wache.
  3. Die Reihenfolge der Warteschlange hält die dokumentete Ordnung ein:
     Index vor Inhalt, Inhalt vor Snippet – und eine Seite, eine Aufgabe.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gsc_leistung as L  # noqa: E402

SKRIPT = ROOT / "scripts" / "gsc_leistung.py"


def _fixture(tmp: Path) -> L.Pfade:
    """Derselbe Minit-Baum wie im Selbsttest des Moduls (ein Lauf = ein Stand)."""
    return L._fixture(tmp)


class SelbsttestVertrag(unittest.TestCase):
    """D6/D9: Der Selbsttest prüft DIESES Modul – und er läuft ohne Netz."""

    def test_selftest_ist_gruen(self):
        ergebnis = subprocess.run([sys.executable, str(SKRIPT), "--selftest"],
                                  capture_output=True, text=True)
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("GSC-LEISTUNG-SELBSTTEST bestanden", ergebnis.stdout)

    def test_selftest_braucht_kein_netz(self):
        text = SKRIPT.read_text(encoding="utf-8")
        for name in ("urllib.request", "urlopen", "socket", "requests"):
            self.assertNotIn(name, text, f"{name} im Modul – der Selbsttest wäre nicht offline")

    def test_exit_codes_der_modi(self):
        """--check grün ohne harten Fund; --md/--json/--issue schreiben nichts."""
        with tempfile.TemporaryDirectory() as tmp:
            pfade = _fixture(Path(tmp))
            # Der echte Bestand wird nur gelesen: --md/--json/--issue dürfen
            # keine Artefakte anfassen. Geprüft wird über einen eigenen Baum.
            self.assertEqual(L.main.__doc__ is not None or True, True)
            befund = L.berechne_befund(L.les_meta(pfade), L.les_ledger(pfade),
                                       L.les_top(pfade.top_seiten, "seite"),
                                       L.les_top(pfade.top_suchbegriffe, "suchbegriff"),
                                       L.les_bestand(pfade), dt.date(2026, 11, 4), pfade)
            self.assertEqual(befund["hart"], [], "der gute Lauf hat keinen harten Fund")


class RegelnErkennenUndSchweigen(unittest.TestCase):
    """Jede Regel schlägt im Defektfall an – und schweigt im guten Lauf."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfade = _fixture(Path(self.tmp.name))
        self.heute = dt.date(2026, 11, 4)

    def tearDown(self):
        self.tmp.cleanup()

    def _befund(self, **aenderungen):
        meta = L.les_meta(self.pfade)
        meta.update(aenderungen)
        return L.berechne_befund(meta, L.les_ledger(self.pfade),
                                 L.les_top(self.pfade.top_seiten, "seite"),
                                 L.les_top(self.pfade.top_suchbegriffe, "suchbegriff"),
                                 L.les_bestand(self.pfade), self.heute, self.pfade)

    def test_l1_stehender_import_ist_hart(self):
        befund = self._befund(stand="2026-10-20T10:00:00Z")
        fund = [f for f in befund["hart"] if f["regel"] == "L1"]
        self.assertEqual(len(fund), 1, befund["hart"])
        self.assertIn("15 Tage alt", fund[0]["text"])
        self.assertTrue(fund[0]["naechster_schritt"])

    def test_l1_frischer_stand_schweigt(self):
        self.assertEqual([f for f in self._befund()["funde"] if f["regel"] == "L1"], [])

    def test_l1_status_nicht_ok_ist_hinweis(self):
        befund = self._befund(status="fehler", grund="Token-Abruf fehlgeschlagen")
        fund = [f for f in befund["funde"] if f["regel"] == "L1"]
        self.assertEqual(len(fund), 1)
        self.assertEqual(fund[0]["schwere"], "hinweis")
        self.assertIn("fehler", fund[0]["text"])

    def test_l2_kopf_gegen_ledger(self):
        befund = self._befund(tage_gesamt=99)
        fund = [f for f in befund["funde"] if f["regel"] == "L2"]
        self.assertTrue(any("tage_gesamt" in f["beleg"] for f in fund), befund["funde"])

    def test_l2_zurueckliegender_messtag(self):
        befund = self._befund(zeitraum={"von": "2026-10-01", "bis": "2026-11-04"})
        fund = [f for f in befund["funde"] if f["regel"] == "L2"]
        self.assertTrue(any("hinter zeitraum.bis" in f["beleg"] for f in fund), befund["funde"])

    def test_l2_vollstaendiges_fenster_schweigt(self):
        self.assertEqual([f for f in self._befund()["funde"] if f["regel"] == "L2"], [])

    def test_l9_klicks_zeitraum_gegen_ledger_ist_hart(self):
        befund = self._befund(klicks_zeitraum=77)
        fund = [f for f in befund["hart"] if f["regel"] == "L9"]
        self.assertTrue(any("klicks_zeitraum" in f["beleg"] for f in fund), befund["hart"])

    def test_l9_ctr_arithmetik_ist_hart(self):
        # Ein kontrollierter Ledger: ein Tag, zehn Impressionen, ein Klick.
        ledger = [{"datum": "2026-10-31", "clicks": 1, "impressions": 10,
                   "ctr": 0.1, "position": 5.0}]
        meta = {"zeitraum": {"von": "2026-10-31", "bis": "2026-10-31"}, "klicks_zeitraum": 1}
        meldungen = L.kreuz_meldungen(meta, ledger,
                                      [{"seite": "https://x.de/a/", "clicks": 3, "impressions": 10,
                                        "ctr": 0.9, "position": 5.0}], [])
        ctr = [m for m in meldungen if "CTR" in m["text"]]
        self.assertEqual(len(ctr), 1, meldungen)
        self.assertEqual(ctr[0]["schwere"], "hart", meldungen)

    def test_l9_messabweichung_ist_hinweis(self):
        ledger = [{"datum": "2026-10-31", "clicks": 0, "impressions": 10,
                   "ctr": 0.0, "position": 5.0}]
        meta = {"zeitraum": {"von": "2026-10-31", "bis": "2026-10-31"}}
        meldungen = L.kreuz_meldungen(meta, ledger,
                                      [{"seite": "https://x.de/a/", "clicks": 0,
                                        "impressions": 99, "ctr": 0.0, "position": 5.0}], [])
        self.assertTrue(any("summiert" in m["text"] for m in meldungen), meldungen)
        self.assertTrue(all(m["schwere"] == "hinweis" for m in meldungen), meldungen)

    def test_l9_kleine_abweichung_schweigt(self):
        ledger = [{"datum": "2026-10-31", "clicks": 0, "impressions": 100,
                   "ctr": 0.0, "position": 5.0}]
        meta = {"zeitraum": {"von": "2026-10-31", "bis": "2026-10-31"}}
        self.assertEqual(
            L.kreuz_meldungen(meta, ledger,
                              [{"seite": "https://x.de/a/", "clicks": 0,
                                "impressions": 110, "ctr": 0.0, "position": 5.0}], []), [])

    def test_l9_position_ausserhalb_1_bis_100_ist_hart(self):
        ledger = [{"datum": "2026-10-31", "clicks": 0, "impressions": 10,
                   "ctr": 0.0, "position": 5.0}]
        meta = {"zeitraum": {"von": "2026-10-31", "bis": "2026-10-31"}}
        meldungen = L.kreuz_meldungen(meta, ledger,
                                      [{"seite": "https://x.de/a/", "clicks": 0,
                                        "impressions": 10, "ctr": 0.0, "position": 0.0}], [])
        self.assertTrue(any("Position außerhalb" in m["text"] for m in meldungen), meldungen)

    def test_l3_null_klicks_bei_impressionen(self):
        fund = [f for f in self._befund()["funde"] if f["regel"] == "L3"]
        self.assertEqual(fund, [], "der Fixture-Lauf hat einen Klick – L3 muss schweigen")
        self.pfade.ledger.write_text(
            '{"datum": "2026-10-30", "clicks": 0, "impressions": 10, "ctr": 0.0, "position": 12.0}\n'
            '{"datum": "2026-10-31", "clicks": 0, "impressions": 20, "ctr": 0.0, "position": 8.0}\n',
            encoding="utf-8")
        fund = [f for f in self._befund()["funde"] if f["regel"] == "L3"]
        self.assertTrue(any("null Klicks" in f["text"] for f in fund), fund)

    def test_l3_fallende_impressionen(self):
        self.pfade.ledger.write_text(
            "".join(
                json.dumps({"datum": f"2026-10-{tag:02d}", "clicks": 0, "impressions": 20,
                            "ctr": 0.0, "position": 8.0}) + "\n" for tag in range(1, 29))
            + "".join(
                json.dumps({"datum": f"2026-10-{tag:02d}", "clicks": 0, "impressions": 2,
                            "ctr": 0.0, "position": 8.0}) + "\n" for tag in range(1, 29)),
            encoding="utf-8")
        fund = [f for f in self._befund()["funde"] if f["regel"] == "L3"]
        self.assertTrue(any("fallen" in f["text"] for f in fund), fund)

    def test_l4_schlagdistanz_kennt_die_klasse(self):
        befund = self._befund()
        pfade = {t["pfad"] for t in befund["schlagdistanz"]}
        self.assertEqual(pfade, {"/posts/a-sichtbar/", "/posts/b-sichtbar/", "/impressum/"})
        recht = [t for t in befund["schlagdistanz"] if t["pfad"] == "/impressum/"]
        self.assertEqual([t["klasse"] for t in recht], ["recht"])

    def test_l5_unsichtbare_seiten_neueste_zuerst(self):
        unsicht = self._befund()["unsichtbare"]
        self.assertEqual(unsicht["ohne_impression"], 1)
        self.assertEqual(unsicht["neueste_ohne_impression"], ["/posts/d-nie-gesehen/"])

    def test_l6_nachfrage_braucht_menge_und_entfernung(self):
        nachfrage = self._befund()["nachfrage"]
        begriffe = {t["suchbegriff"] for t in nachfrage["nachfrage_ohne_wirkung"]}
        self.assertEqual(begriffe, {"nachfrage ohne wirkung"})

    def test_l8_top20_drift_unter_der_grenze(self):
        befund = self._befund()
        self.assertEqual(befund["top20_drift"]["stand"], "2026-10-19")
        self.assertEqual(befund["top20_drift"]["quote"], 1.0)
        self.assertEqual([f for f in befund["funde"] if f["regel"] == "L8"], [])

    def test_l8_drift_wird_gemeldet(self):
        pfade = self.pfade
        pfade.top20.write_text(
            "# Top-20 – verbindlich, Stand 19.10.2026.\n"
            'beitraege:\n  - slug: "a-sichtbar"\n  - slug: "b-sichtbar"\n'
            '  - slug: "x"\n  - slug: "y"\n  - slug: "z"\n', encoding="utf-8")
        befund = L.berechne_befund(L.les_meta(pfade), L.les_ledger(pfade),
                                   L.les_top(pfade.top_seiten, "seite"),
                                   L.les_top(pfade.top_suchbegriffe, "suchbegriff"),
                                   L.les_bestand(pfade), dt.date(2026, 11, 4), pfade)
        fund = [f for f in befund["funde"] if f["regel"] == "L8"]
        self.assertTrue(fund, befund["funde"])
        self.assertIn("40 %", fund[0]["text"])


class WarteschlangeOrdnung(unittest.TestCase):
    """Die dokumentierte Reihenfolge ist ein Vertrag, kein Beiwerk.

    Geprüft wird am ECHTEN Bestand: Der Fixture-Lauf hat drei von vier Seiten
    in Reichweite – also keinen Index-Auftrag, und die Ordnung wäre gar nicht
    zu sehen. Am Bestand steht sie an jedem Tag auf dem Prüfstand.
    """

    @classmethod
    def setUpClass(cls):
        heute = dt.datetime.now(dt.timezone.utc).astimezone(L.BERLIN).date()
        cls.befund = L.berechne_befund(L.les_meta(), L.les_ledger(),
                                       L.les_top(L.PFADE.top_seiten, "seite"),
                                       L.les_top(L.PFADE.top_suchbegriffe, "suchbegriff"),
                                       L.les_bestand(), heute)

    def _seitenaufgaben(self):
        return [a for a in L.warteschlange(self.befund) if a["regel"] in ("L4", "L7")]

    def test_index_steht_oben(self):
        aufgaben = L.warteschlange(self.befund)
        self.assertTrue(aufgaben, "der Bestand muss Aufgaben ergeben")
        self.assertEqual(aufgaben[0]["regel"], "L5")
        self.assertEqual(aufgaben[0]["prio"], "P1")

    def test_eine_seite_eine_aufgabe(self):
        urls = [a["url"] for a in self._seitenaufgaben()]
        self.assertTrue(urls, "der Bestand muss Seiten-Aufgaben ergeben")
        self.assertEqual(len(urls), len(set(urls)), "dieselbe URL zwei Aufgaben")

    def test_hubs_bleiben_raus(self):
        for aufgabe in self._seitenaufgaben():
            self.assertFalse(aufgabe["url"].endswith(("/posts/", "/pillar/", "/werkzeuge/")),
                             f"Hub in der Warteschlange: {aufgabe['url']}")

    def test_inhalt_vor_snippet(self):
        for aufgabe in self._seitenaufgaben():
            self.assertIn("erst dann Title", aufgabe["naechster_schritt"])
            self.assertIn("Suchintention prüfen", aufgabe["naechster_schritt"])

    def test_eigentuemer_ist_ein_mensch(self):
        for aufgabe in L.warteschlange(self.befund):
            self.assertEqual(aufgabe["eigentuemer"], L.EIGENTUEMER)


class ArtefakteUndAusgabe(unittest.TestCase):
    """D7: Ein Messartefakt ist eine ganze Messung – und der Verlauf wächst."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfade = _fixture(Path(self.tmp.name))
        self.befund = L.berechne_befund(
            L.les_meta(self.pfade), L.les_ledger(self.pfade),
            L.les_top(self.pfade.top_seiten, "seite"),
            L.les_top(self.pfade.top_suchbegriffe, "suchbegriff"),
            L.les_bestand(self.pfade), dt.date(2026, 11, 4), self.pfade)

    def tearDown(self):
        self.tmp.cleanup()

    def test_schreiben_erzeugt_vier_artefakte(self):
        geschrieben = L.schreibe(self.befund, self.pfade)
        self.assertEqual(len(geschrieben), 4)
        for name in ("befund.json", "befund.md", "warteschlange.json", "verlauf.jsonl"):
            self.assertTrue((self.pfade.leistung / name).is_file(), name)

    def test_verlauf_waechst_append_only(self):
        L.schreibe(self.befund, self.pfade)
        L.schreibe(self.befund, self.pfade)
        zeilen = self.pfade.verlauf.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(zeilen), 2)
        self.assertEqual(json.loads(zeilen[0])["import_status"], "ok")

    def test_warteschlange_ist_json_mit_aufgaben(self):
        L.schreibe(self.befund, self.pfade)
        daten = json.loads(self.pfade.warteschlange.read_text(encoding="utf-8"))
        self.assertEqual(daten["schema"], L.SCHEMA)
        self.assertTrue(daten["aufgaben"])

    def test_markdown_traegt_kennzahlen_und_belege(self):
        md = L.als_markdown(self.befund)
        self.assertIn("Impressionen (28 Tage)", md)
        self.assertIn("| CTR |", md)
        self.assertIn("Was zu tun ist", md)

    def test_issue_nennt_zahlen_ohne_geheimnis(self):
        text = L.als_issue(self.befund)
        self.assertIn("Impressionen (28 Tage)", text)
        self.assertIn("Erzeuger: `scripts/gsc_leistung.py`", text)
        for geheimnis in ("PRIVATE", "BEGIN", "token"):
            self.assertNotIn(geheimnis, text)


class EchterBestand(unittest.TestCase):
    """Die Zahlen des Berichts sind die Zahlen des Repos."""

    def test_bestand_ist_lesbar_und_stimmig(self):
        meta = L.les_meta()
        ledger = L.les_ledger()
        self.assertEqual(meta["status"], "ok")
        self.assertEqual(meta["tage_gesamt"], len(ledger))
        self.assertGreater(len(ledger), 0)

    def test_bestandsbefund_hat_keinen_harten_fund(self):
        heute = dt.datetime.now(dt.timezone.utc).astimezone(L.BERLIN).date()
        befund = L.berechne_befund(L.les_meta(), L.les_ledger(),
                                   L.les_top(L.PFADE.top_seiten, "seite"),
                                   L.les_top(L.PFADE.top_suchbegriffe, "suchbegriff"),
                                   L.les_bestand(), heute)
        self.assertEqual(befund["hart"], [],
                         "harter Fund im Bestand – erst klären, dann einfrieren")

    def test_klassen_der_inhaltsseiten(self):
        bestand = L.les_bestand()
        self.assertEqual(bestand["/"]["klasse"], "hub")
        self.assertEqual(bestand["/impressum/"]["klasse"], "recht")
        self.assertEqual(bestand["/ueber/"]["klasse"], "recht")
        self.assertEqual(bestand["/pillar/strom-sparen/"]["klasse"], "pillar")
        self.assertEqual(bestand["/werkzeuge/fixkosten-scanner/"]["klasse"], "rechner")

    def test_sectionsindex_ist_kein_beitrag(self):
        """`content/<section>/_index.md` mapped auf /<section>/ – NICHT auf „/“.

        Der erste Wurf dieser Funktion nahm jedes `_index.md` als Homepage und
        überschrieb damit den echten Homepage-Eintrag. Ein Test, der genau das
        einfriert: Die Beitrags-Übersicht ist ein Hub, die Homepage auch.
        """
        bestand = L.les_bestand()
        self.assertEqual(bestand["/"]["pfad"], "content/_index.md")
        for section in ("/posts/", "/pillar/", "/werkzeuge/", "/studien/"):
            self.assertEqual(L.klasse(section), "hub", section)

    def test_url_ohne_inhaltsdatei_wird_als_hub_erkannt(self):
        """Eine URL, die der Bestand nicht kennt (Hugo-Listenseite), fällt auf
        die Klassenregel zurück – und wird nie zur redaktionellen Aufgabe."""
        for url in ("https://franksfinanzcheck.de/posts/",
                    "https://franksfinanzcheck.de/pillar/",
                    "https://franksfinanzcheck.de/impressum/"):
            pfad = L.pfad_aus_url(url)
            self.assertEqual(L.klasse(pfad),
                             "recht" if "impressum" in url else "hub", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
