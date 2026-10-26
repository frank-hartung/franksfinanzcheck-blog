"""Tests für Regel F – Konsolidierung zweier Seiten mit identischer Suchabsicht.

Die drei Belege (Suchabsicht, Nachfrage, kein redaktioneller Inlink) sind keine
Ansichtssache. Diese Tests halten fest, dass jeder einzelne fehlen darf und das
Urteil dann rot wird – und dass die Wache in `weiterleitungen.py` dieselbe
Rechnung benutzt.

Ausführen: python3 -m unittest scripts.tests.test_konsolidierung
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import scripts.konsolidierung as k
import scripts.weiterleitungen as wl

BLOG_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Zwei Seiten im selben Themenfeld, deren Titel dieselbe Absicht tragen,
# eine dritte Seite im selben Feld mit anderer Absicht, eine vierte Seite in
# einem anderen Themenfeld.
BUCH_APP = "/posts/2026-10-01-haushaltsbuch-fuehren-app-excel/"
BUCH_EXCEL = "/posts/2026-10-02-haushaltsbuch-fuehren-mit-excel/"
KONTO = "/posts/2026-10-03-girokonto-ohne-gebuehren/"
STROM = "/posts/2026-10-04-strom-sparen-im-haushalt/"


def _seite(verzeichnis: Path, slug: str, titel: str, pillar: str, text: str = "Text") -> None:
    ziel = verzeichnis / "content" / "posts" / slug
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / "index.md").write_text(
        f'---\ntitle: "{titel}"\npillar: "{pillar}"\ndraft: false\n---\n\n{text}\n',
        encoding="utf-8")


def _leistungsdaten(root: Path, zeilen: list[dict]) -> None:
    pfad = root / "data" / "gsc" / "top_seiten_28t.json"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(zeilen), encoding="utf-8")


class Fixture:
    """Kleiner Blog im Temp-Verzeichnis – mit genau einem Inlink auf BUCH_EXCEL."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        posts = self.root / "content" / "posts"
        _seite(self.root, "2026-10-01-haushaltsbuch-fuehren-app-excel",
               "Haushaltsbuch führen: App oder Excel", "konto-karten")
        _seite(self.root, "2026-10-02-haushaltsbuch-fuehren-mit-excel",
               "Haushaltsbuch führen mit Excel", "konto-karten")
        _seite(self.root, "2026-10-03-girokonto-ohne-gebuehren",
               "Girokonto ohne Gebühren: der Vergleich", "konto-karten",
               f"Siehe [Haushaltsbuch](../../posts/2026-10-02-haushaltsbuch-fuehren-mit-excel/).")
        _seite(self.root, "2026-10-04-strom-sparen-im-haushalt",
               "Strom sparen im Haushalt", "strom-sparen")
        assert posts.exists()

    def aufraeumen(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class BelegSuchabsicht(unittest.TestCase):
    """Beleg 1: Titel-Überschneidung über der Schwelle und gleiches Themenfeld."""

    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.aufraeumen()

    def test_identische_absicht_belegt(self):
        befund = k.absicht(BUCH_EXCEL, BUCH_APP, self.fx.root)
        self.assertTrue(befund["belegt"], befund["grund"])
        self.assertGreaterEqual(befund["mass"], k.SCHWELLE_ABSICHT)
        self.assertEqual(befund["pillar"], "konto-karten")

    def test_andere_absicht_im_gleichen_feld_verneint(self):
        # Gleiches Themenfeld, aber „Girokonto ohne Gebühren“ ist keine
        # Haushaltsbuch-Frage: geteilte Füllwörter reichen nicht.
        befund = k.absicht(BUCH_EXCEL, KONTO, self.fx.root)
        self.assertFalse(befund["belegt"])
        self.assertIn("Titel-Überschneidung", befund["grund"])

    def test_anderes_themenfeld_verneint(self):
        befund = k.absicht(BUCH_EXCEL, STROM, self.fx.root)
        self.assertFalse(befund["belegt"])
        self.assertIn("Themenfelder", befund["grund"])

    def test_unbekannte_url_ist_nicht_belegt(self):
        befund = k.absicht("/posts/gibt-es-nicht/", BUCH_APP, self.fx.root)
        self.assertFalse(befund["belegt"])
        self.assertIn("nicht messbar", befund["grund"])


class BelegNachfrage(unittest.TestCase):
    """Beleg 2: Impressionen – Bekanntheit bei Google ist keine Nachfrage."""

    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.aufraeumen()

    def test_ohne_daten_nicht_belegt(self):
        befund = k.nachfrage(BUCH_EXCEL, self.fx.root)
        self.assertFalse(befund["belegt"])
        self.assertEqual(befund["impressionen"], 0)
        self.assertIn("Leistungsdaten", befund["grund"])

    def test_impressionen_belegen_nachfrage(self):
        _leistungsdaten(self.fx.root, [{"url": BUCH_EXCEL, "impressions": 4, "position": 12.0}])
        befund = k.nachfrage(BUCH_EXCEL, self.fx.root)
        self.assertTrue(befund["belegt"])
        self.assertEqual(befund["impressionen"], 4)
        self.assertIn("28 Tagen", befund["grund"])

    def test_null_impressionen_belegen_nichts(self):
        _leistungsdaten(self.fx.root, [{"url": BUCH_EXCEL, "impressions": 0}])
        self.assertFalse(k.nachfrage(BUCH_EXCEL, self.fx.root)["belegt"])

    def test_url_ohne_zeile_nicht_belegt(self):
        _leistungsdaten(self.fx.root, [{"url": BUCH_APP, "impressions": 9}])
        befund = k.nachfrage(BUCH_EXCEL, self.fx.root)
        self.assertFalse(befund["belegt"])
        self.assertIn("nicht vor", befund["grund"])

    def test_gsc_exportform_wird_erkannt(self):
        # Die Search Console nennt die Spalte `seite` und schreibt die volle
        # Adresse. Ein Vergleich nur gegen `url` wäre ein Messfehler: Jede
        # Nachfrage gälte als unbelegt und F blockierte aus dem falschen Grund.
        pfad = self.fx.root / "data" / "gsc" / "top_seiten_28t.json"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps([{
            "seite": "https://franksfinanzcheck.de" + BUCH_EXCEL,
            "clicks": 0, "impressions": 1, "position": 7.0}]), encoding="utf-8")
        befund = k.nachfrage(BUCH_EXCEL, self.fx.root)
        self.assertTrue(befund["belegt"], befund["grund"])
        self.assertEqual(befund["impressionen"], 1)

    def test_schwellen_sind_sichtbar(self):
        self.assertGreaterEqual(k.MIN_IMPRESSIONEN, 1)
        self.assertTrue(0 < k.SCHWELLE_ABSICHT < 1)


class BelegVerlinkung(unittest.TestCase):
    """Beleg 3: kein redaktioneller Link darf auf die Quelle zeigen."""

    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.aufraeumen()

    def test_inlink_wird_erkannt(self):
        befund = k.verlinkung(BUCH_EXCEL, self.fx.root)
        self.assertFalse(befund["belegt"])
        self.assertEqual(befund["ein"], 1)
        self.assertTrue(befund["quellen"])

    def test_ohne_inlink_gruen(self):
        befund = k.verlinkung(BUCH_APP, self.fx.root)
        self.assertTrue(befund["belegt"])
        self.assertEqual(befund["ein"], 0)


class Urteil(unittest.TestCase):
    """Das Urteil ist die UND-Verknüpfung – jeder fehlende Beleg kippt es."""

    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.aufraeumen()

    def test_ohne_nachfrage_und_inlink_rot(self):
        u = k.urteil(BUCH_EXCEL, BUCH_APP, "F", self.fx.root)
        self.assertFalse(u["erlaubt"])
        self.assertEqual(u["fehlend"], ["nachfrage", "verlinkung"])
        self.assertEqual(u["regel"], "F")

    def test_nur_inlink_fehlt(self):
        _leistungsdaten(self.fx.root, [{"url": BUCH_EXCEL, "impressions": 3}])
        u = k.urteil(BUCH_EXCEL, BUCH_APP, "F", self.fx.root)
        self.assertFalse(u["erlaubt"])
        self.assertEqual(u["fehlend"], ["verlinkung"])

    def test_alle_belege_gruen(self):
        _leistungsdaten(self.fx.root, [{"url": BUCH_APP, "impressions": 2}])
        u = k.urteil(BUCH_APP, BUCH_EXCEL, "F", self.fx.root)
        self.assertTrue(u["erlaubt"], u["fehlend"])
        self.assertIn("zulässig", u["empfehlung"])

    def test_empfehlung_passt_zum_fehlenden_beleg(self):
        self.assertIn("Rollen trennen", k.empfehlung(BUCH_EXCEL, KONTO, ["suchabsicht"]))
        self.assertIn("Regel D", k.empfehlung(BUCH_EXCEL, KONTO, ["nachfrage"]))
        self.assertIn("Link umhängen", k.empfehlung(BUCH_EXCEL, KONTO, ["verlinkung"]))


class Wache(unittest.TestCase):
    """`pruefe()` bewertet ausschließlich Regel F – der Bestand bleibt unberührt."""

    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.aufraeumen()

    def test_fehlender_beleg_wird_hart_gemeldet(self):
        befunde = k.pruefe([{"von": BUCH_EXCEL, "nach": BUCH_APP, "regel": "F", "grund": "Test"}],
                           self.fx.root)
        self.assertEqual(len(befunde), 1)
        self.assertEqual(befunde[0]["regel"], "F1")
        self.assertEqual(befunde[0]["schwere"], "hart")
        self.assertIn("Konsolidierung ohne Beleg", befunde[0]["text"])
        # Absicht und Themenfeld stimmen hier, es fehlen Nachfrage und Inlink –
        # die Empfehlung muss also Regel D nennen, nicht die Rollentrennung.
        self.assertIn("Regel D", befunde[0]["text"])

    def test_belegter_fall_ist_gruen(self):
        _leistungsdaten(self.fx.root, [{"url": BUCH_APP, "impressions": 2}])
        sauber = [{"von": BUCH_APP, "nach": BUCH_EXCEL, "regel": "F", "grund": "Test"}]
        self.assertEqual(k.pruefe(sauber, self.fx.root), [])

    def test_alte_regeln_werden_nicht_nachbewertet(self):
        alt = [{"von": BUCH_EXCEL, "nach": BUCH_APP, "regel": r, "grund": "Altbestand"}
               for r in ("A", "B", "C")]
        self.assertEqual(k.pruefe(alt, self.fx.root), [])

    def test_weiterleitungen_ruft_dieselbe_wache(self):
        # Eine Wahrheit, zwei Aufrufer: `weiterleitungen.pruefe` muss den
        # F-Befund übernehmen, ohne dass die Quelle live ist.
        eintraege = [{"von": BUCH_EXCEL, "nach": BUCH_APP, "regel": "F", "grund": "Test"}]
        live = {BUCH_APP}
        befunde = wl.pruefe(eintraege, [], live)
        self.assertTrue(any("Konsolidierung ohne Beleg" in x for x in befunde), befunde)

    def test_regel_f_im_weiterleitungs_regelwerk(self):
        self.assertIn("F", wl.REGELN_WEITERLEITUNG)


class Bilanz(unittest.TestCase):
    def test_zaehlt_je_regel(self):
        ergebnis = k.bilanz([{"von": "/a/", "regel": "A"},
                             {"von": "/b/", "regel": "B"},
                             {"von": "/c/", "regel": "F"}])
        self.assertEqual(ergebnis["gesamt"], 3)
        self.assertEqual(ergebnis["nach_regel"], {"A": 1, "B": 1, "F": 1})
        self.assertEqual(ergebnis["konsolidierungen"], 1)


class Bestand(unittest.TestCase):
    """Der echte Bestand: 115 Einträge, keine Konsolidierung ohne Beleg."""

    @classmethod
    def setUpClass(cls):
        cls.eintraege, cls.entfallen = wl.lade_quelle(str(BLOG_DIR))

    def test_keine_konsolidierung_im_bestand(self):
        self.assertEqual(k.bilanz(self.eintraege)["konsolidierungen"], 0)

    def test_bestand_ist_belegfrei_gruen(self):
        self.assertEqual(k.pruefe(self.eintraege, BLOG_DIR), [])

    def test_regelwerk_kennt_f(self):
        self.assertLessEqual({"A", "B", "C", "D", "E", "F"},
                             wl.REGELN_WEITERLEITUNG | wl.REGELN_ENTFALLEN)

    def test_doku_erklaert_die_drei_belege(self):
        doku = (BLOG_DIR / "docs" / "ANLEITUNG-WEITERLEITUNGEN.md").read_text(encoding="utf-8")
        self.assertIn("Regel F", doku)
        for beleg in ("Suchabsicht", "Nachfrage", "Live-Verlinkung"):
            self.assertIn(beleg, doku)


class FallZwilling(unittest.TestCase):
    """Der belegte Fall vom 26.10.2026: zwei P2-Seiten, zwei verschiedene Antworten.

    Der Test hält die Entscheidung fest, damit sie nicht durch ein späteres
    „die sehen sich ähnlich“ wieder aufgemacht wird – ohne Beleg kein F.
    """

    QUELLE = "/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/"
    ZIEL = "/posts/2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/"

    @classmethod
    def setUpClass(cls):
        cls.urteil = k.urteil(cls.QUELLE, cls.ZIEL, "F", BLOG_DIR)

    def test_keine_konsolidierung_der_beiden_p2_seiten(self):
        self.assertFalse(self.urteil["erlaubt"])
        self.assertIn("suchabsicht", self.urteil["fehlend"])

    def test_titel_ueberschneidung_ist_null(self):
        # Kein gemeinsames sinntragendes Wort – die frühere Messung „2 ähnliche
        # Titel“ war ein Messfehler (siehe Bericht §7.3).
        self.assertEqual(self.urteil["pruefungen"]["suchabsicht"]["gemeinsam"], [])
        self.assertEqual(self.urteil["pruefungen"]["suchabsicht"]["mass"], 0.0)

    def test_empfehlung_ist_rollentrennung(self):
        self.assertIn("Rollen trennen", self.urteil["empfehlung"])

    def test_kein_kandidat_im_themenfeld(self):
        self.assertIsNone(k.bester_kandidat(self.QUELLE, BLOG_DIR))

    def test_nachfrage_ist_eine_zahl_nicht_eine_meinung(self):
        # 19.10.2026: die Seite hatte 1 Impression, Position 7,0 in 28 Tagen.
        # Das ist wenig – aber es ist belegt und damit eine Zahl.
        befund = self.urteil["pruefungen"]["nachfrage"]
        self.assertTrue(befund["belegt"], befund["grund"])
        self.assertEqual(befund["impressionen"], 1)

    def test_der_zwilling_hat_keine_belegte_nachfrage(self):
        # Die andere P2-Seite kommt in den Top-Seiten nicht vor. Für sie wäre
        # ein Zusammenführen die falsche Antwort – belegt ist belegt.
        befund = k.nachfrage(self.ZIEL, BLOG_DIR)
        self.assertFalse(befund["belegt"])
        self.assertEqual(befund["impressionen"], 0)


if __name__ == "__main__":
    unittest.main()
