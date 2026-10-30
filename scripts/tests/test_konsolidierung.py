"""Tests für Regel F – Konsolidierung zweier Seiten mit identischer Suchabsicht.

Die drei Belege (Suchabsicht, Nachfrage, kein redaktioneller Inlink) sind keine
Ansichtssache. Diese Tests halten fest, dass jeder einzelne fehlen darf und das
Urteil dann rot wird – und dass die Wache in `weiterleitungen.py` dieselbe
Rechnung benutzt.

Ausführen: python3 -m unittest scripts.tests.test_konsolidierung
"""
import datetime as dt
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
        #
        # Die Tageszahl selbst wird hier bewusst NICHT festgenagelt: jede
        # GSC-Lieferung verschiebt sie, und ein Test, der montags rot wird,
        # weil der Bot Impressionen dazugezählt hat, misst das Wetter statt
        # den Vertrag. Festgehalten wird der Vertrag: belegt heißt, es gibt
        # eine Zahl > 0 – nicht ein Gefühl.
        befund = self.urteil["pruefungen"]["nachfrage"]
        self.assertTrue(befund["belegt"], befund["grund"])
        self.assertEqual(befund["quelle"], "top_seiten_28t.json")
        self.assertGreater(befund["impressionen"], 0, befund["grund"])

    # ------------------------------------------------------------------
    #  Rollenvertrag (Dauerheilung 30.10.2026)
    #
    #  Bis hierher stand hier EINE Zusicherung: „der Zwilling hat weniger als
    #  10 Impressionen“. Am 30.10.2026 hatte er 14 (Position 40,9, 0 Klicks),
    #  und der Test war rot. Er sagte damit das Richtige – „Konsolidierung
    #  prüfen“ –, verlangte aber eine kleine Zahl. Wer ihn reparieren will,
    #  senkt die Schwelle; genau das darf nicht passieren.
    #
    #  Die Zahl bleibt, aber sie verlangt ab jetzt eine ANTWORT statt einer
    #  Restnachfrage: Über 10 Impressionen muss die Entscheidung die
    #  Nachfrage tragen (Erwartung `impressionen`), die Frist laufen lassen
    #  (Wiedervorlage), und die Rollentrennung muss strukturell belegt sein
    #  (keine gemeinsamen Zwischenüberschriften, keine wörtlichen Sätze) und
    #  in beide Richtungen verlinkt. Das ist strenger als vorher: Eine
    #  gelöschte Entscheidung, eine überfällige Frist, ein fehlender
    #  Rollenlink oder eine zusammengewachsene Struktur macht rot – eine
    #  kleine Zahl war vorher schon grün, ohne dass jemand etwas geprüft hat.
    # ------------------------------------------------------------------
    def test_nachfrage_ueber_der_schwelle_ist_beantwortet(self):
        befund = k.nachfrage(self.ZIEL, BLOG_DIR)
        self.assertTrue(befund["belegt"], befund["grund"])
        register = k._gsc().entscheidungen()
        for url in (self.ZIEL, self.QUELLE):
            eintrag = register.get(url) or {}
            self.assertTrue(eintrag, f"{url}: keine dokumentierte Rollen-Entscheidung")
            self.assertEqual(eintrag.get("erwartung"), "impressionen",
                             f"{url}: die Entscheidung beantwortet die Nachfrage nicht")
            self.assertGreaterEqual(eintrag.get("wiedervorlage", ""), "2026-10-30",
                                    f"{url}: Wiedervorlage ist überfällig")
        if befund["impressionen"] >= k.SCHWELLE_NACHFRAGE_ROLLE:
            # Der Fall, der am 30.10. eingetreten ist: Die Zahl ist über der
            # Schwelle – und die Antwort steht im Register, nicht in einer
            # angepassten Schwelle.
            self.assertIn("Kontrollpfad", register[self.ZIEL]["entscheidung"])

    def test_rollenpaar_ist_beidseitig_dokumentiert(self):
        register = k._gsc().entscheidungen()
        self.assertEqual((register.get(self.ZIEL) or {}).get("paar"), self.QUELLE)
        self.assertEqual((register.get(self.QUELLE) or {}).get("paar"), self.ZIEL)
        self.assertEqual(k.rollenpaare(BLOG_DIR, register),
                         [{"a": self.ZIEL, "b": self.QUELLE}])

    def test_die_beiden_seiten_sind_strukturell_verschieden(self):
        st = k.struktur(self.ZIEL, self.QUELLE, BLOG_DIR)
        self.assertTrue(st["messbar"], st.get("grund", st))
        self.assertEqual(st["gemeinsam"], [],
                         "gemeinsame Zwischenüberschriften – dann ist es eine Dublette")
        self.assertLessEqual(st["ueberschneidung"], k.SCHWELLE_STRUKTUR,
                             f"{st['ueberschneidung']:.1%} wörtliche Sätze")

    def test_rollenlink_in_beide_richtungen(self):
        self.assertTrue(k._verlinkt(self.ZIEL, self.QUELLE, BLOG_DIR),
                        "Der Kontrollpfad verlinkt den Jahresplan nicht")
        self.assertTrue(k._verlinkt(self.QUELLE, self.ZIEL, BLOG_DIR),
                        "Der Jahresplan verlinkt den Kontrollpfad nicht")

    def test_der_lebende_bestand_ist_am_entscheidungstag_rollenklar(self):
        """Die ganze Wache am echten Bestand – mit FESTEM Datum.

        Die Frist (Wiedervorlage) ist eine Zusage und läuft ab; die Wache
        meldet das dann zu Recht (R2 hart, `--rollenpaare` im Deploy-Gate).
        Ein Test, der dafür die Wanduhr liest, wäre selbst eine Zeitbombe:
        Am 14.11.2026 wäre er rot geworden, ohne dass jemand etwas geändert
        hätte – genau die Klasse, die die Uhr-Probe (+97 Tage) findet, und
        dieser Test hat sie am 30.10.2026 ausgelöst. Das Datum ist deshalb
        der Entscheidungstag: Was hier geprüft wird (Struktur, Entscheidung,
        Rollenlink), hängt nicht am Kalender; was am Kalender hängt, prüft
        der Lauf zur Laufzeit.
        """
        self.assertEqual(k.rollenpaare_pruefen(BLOG_DIR, heute=dt.date(2026, 10, 30)), [])


class RollenpaarWache(unittest.TestCase):
    """Die Wache muss rot können – sonst ist sie Dekoration.

    Jede Zusicherung des Rollenvertrags wird einzeln verletzt: fehlende
    Entscheidung, überfällige Frist, Nachfrage ohne Antwort, gemeinsame
    Struktur, fehlender Rollenlink. Dieselbe Bauart wie die Fixtures der
    drei F-Belege oben.
    """

    A = "/posts/2026-10-12-jahresplan-test/"
    B = "/posts/2026-10-12-kontrollpfad-test/"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rollenpaar-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._seite("2026-10-12-jahresplan-test",
                    "Am Anfang sammelst du alle Abbuchungen eines Jahres. "
                    "Danach ordnest du sie nach Kategorien und Fristen.",
                    "## Alle Zahlungen sammeln", "## Fristen sichern")
        self._seite("2026-10-12-kontrollpfad-test",
                    "Der Prüfpfad geht an einem Nachmittag durch alle Fixkosten. "
                    "Am Ende steht die Entscheidung über jeden Vertrag.",
                    "## Preistreiber finden", "## Konditionen rechnen")
        self.register = {
            self.A: {"url": self.A, "paar": self.B, "wiedervorlage": "2026-11-13",
                     "eigentuemer": "redaktion", "erwartung": "impressionen"},
            self.B: {"url": self.B, "paar": self.A, "wiedervorlage": "2026-11-13",
                     "eigentuemer": "redaktion", "erwartung": "impressionen"},
        }
        self.heute = __import__("datetime").date(2026, 10, 30)

    def _seite(self, slug, text, h2a, h2b, link=None):
        ziel = self.tmp / "content" / "posts" / slug
        ziel.mkdir(parents=True, exist_ok=True)
        koerper = f"{text}\n\n{h2a}\n\nInhalt.\n\n{h2b}\n\nInhalt.\n"
        if link:
            koerper = f"Mehr dazu im {link}.\n\n" + koerper
        (ziel / "index.md").write_text(
            f'---\ntitle: "{slug}"\n---\n\n{koerper}', encoding="utf-8")

    def _pruefen(self, register=None):
        return k.rollenpaar_pruefen(self.A, self.B, self.tmp,
                                    register=self.register if register is None else register,
                                    heute=self.heute)

    def _verlinken(self):
        self._seite("2026-10-12-jahresplan-test",
                    "Am Anfang sammelst du alle Abbuchungen eines Jahres. "
                    "Danach ordnest du sie nach Kategorien und Fristen.",
                    "## Alle Zahlungen sammeln", "## Fristen sichern",
                    link=f"[Kontrollpfad](../../posts/{k._verzeichnis(self.B)}/)")
        self._seite("2026-10-12-kontrollpfad-test",
                    "Der Prüfpfad geht an einem Nachmittag durch alle Fixkosten. "
                    "Am Ende steht die Entscheidung über jeden Vertrag.",
                    "## Preistreiber finden", "## Konditionen rechnen",
                    link=f"[Jahresplan](../../posts/{k._verzeichnis(self.A)}/)")

    def test_ohne_rollenlink_rot(self):
        # Nur eine Richtung verlinkt: Die Seite B kennt A, A kennt B nicht.
        self._seite("2026-10-12-kontrollpfad-test",
                    "Der Prüfpfad geht an einem Nachmittag durch alle Fixkosten. "
                    "Am Ende steht die Entscheidung über jeden Vertrag.",
                    "## Preistreiber finden", "## Konditionen rechnen",
                    link=f"[Jahresplan](../../posts/{k._verzeichnis(self.A)}/)")
        befunde = self._pruefen()
        self.assertTrue(any("verlinkt" in b["text"] for b in befunde), befunde)

    def test_fehlende_entscheidung_rot(self):
        self._verlinken()
        befunde = self._pruefen({})
        self.assertTrue(any("Keine dokumentierte Rollen-Entscheidung" in b["text"]
                            for b in befunde), befunde)

    def test_ueberfaellige_frist_rot(self):
        self._verlinken()
        alt = {u: dict(e, wiedervorlage="2026-09-30") for u, e in self.register.items()}
        befunde = self._pruefen(alt)
        self.assertTrue(any("überfällig" in b["text"] for b in befunde), befunde)

    def test_nachfrage_ohne_antwort_rot(self):
        self._verlinken()
        _leistungsdaten(self.tmp, [{"url": self.A,
                                    "impressions": k.SCHWELLE_NACHFRAGE_ROLLE,
                                    "position": 40.9}])
        ohne = {u: dict(e, erwartung="indexiert") for u, e in self.register.items()}
        befunde = self._pruefen(ohne)
        self.assertTrue(any("Impressionen" in b["text"] for b in befunde), befunde)

    def test_gemeinsame_struktur_rot(self):
        self._verlinken()
        self._seite("2026-10-12-kontrollpfad-test",
                    "Der Prüfpfad geht an einem Nachmittag durch alle Fixkosten. "
                    "Am Ende steht die Entscheidung über jeden Vertrag.",
                    "## Fristen sichern", "## Konditionen rechnen",
                    link=f"[Jahresplan](../../posts/{k._verzeichnis(self.A)}/)")
        befunde = self._pruefen()
        self.assertTrue(any("Struktur gleich" in b["text"] for b in befunde), befunde)

    def test_einseitige_dokumentation_rot(self):
        # Nur der Jahresplan trägt eine Entscheidung, die Gegenseite nicht:
        # Der Rollenlink steht, die Zusage fehlt – das zählt nicht.
        self._verlinken()
        befunde = self._pruefen({self.A: dict(self.register[self.A])})
        self.assertTrue(any("Keine dokumentierte Rollen-Entscheidung" in b["text"]
                            for b in befunde), befunde)
        self.assertEqual(befunde[0]["url"], self.B)

    def test_vollstaendig_belegt_gruen(self):
        self._verlinken()
        self.assertEqual(self._pruefen(), [])

if __name__ == "__main__":
    unittest.main()
