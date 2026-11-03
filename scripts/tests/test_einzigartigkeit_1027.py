"""Regressionstests zur Meldung #1027 – „Einzigartigkeits-Audit:
Bestandsüberlappungen gefunden" (03.11.2026).

ANLASS
------
Das Tagesaudit meldete zwei kritische Bestandsüberlappungen zwischen
LIVE-Artikeln (08-10 ↔ 08-12 mit 5, 08-10 ↔ 08-24 mit 16 geteilten
Sieben-Wort-Phrasen) und vier weitere zwischen nicht veröffentlichten
Artikeln. Ursache: Der Commit 69f08c40 (#1017, 02.11.2026) hatte denselben
BNetzA-Absatz in drei live Gas-Artikeln eingefügt – und niemand hatte es
gemessen, weil das Publish-Gate (U1/U2) ausschließlich KANDIDATEN prüft. Eine
redaktionelle Änderung an einem bereits live geschalteten Artikel lief
daran vorbei. Das Audit schlug zwei Tage später Alarm, die Meldung kam
einen Tag später als der Deploy.

ZWEI HALTEN WIR FEST
--------------------
1. DER BESTAND: Die sieben im Audit genannten Paare bleiben unter der
   Schwelle. Wer sie erneut auflöst, hat den alten Schaden zurückgebracht.
2. DIE LÜCKE: Eine GEPLANTE Änderung (noch nicht geschrieben) misst ihre
   Einzigartigkeit gegen den gesamten Bestand – live wie Entwurf. Diese
   Messung (V4 im Publikations-Vertrag) ist die Ursache der Behebung; ohne
   sie wäre nur der Bestand geputzt, nicht die Ursache beseitigt.

Ausführung:  python3 -m unittest discover -s scripts/tests -v
"""
import os
import sys
import unittest
from pathlib import Path

SCRIPTS = str(Path(__file__).resolve().parents[1])
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import check_uniqueness as cu  # noqa: E402
import governance_contract as gc  # noqa: E402
import publikations_vertrag as pv  # noqa: E402

# Die sieben Paare aus dem Audit vom 03.11.2026 (Kritisch 2 + Nicht-Live 4).
PAARE_AUS_1027 = [
    # live ↔ live (kritisch im Audit)
    ("2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas",
     "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026"),
    ("2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas",
     "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"),
    ("2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026",
     "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"),
    # nicht live ↔ live (Vorab-Aufgabe)
    ("2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet",
     "2026-10-16-dns-server-aendern-fuer-schnelleres-internet"),
    ("2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle",
     "2026-10-28-dsl-und-internet-flat-guenstig-sichern"),
    ("2026-10-19-urlaubskasse-clever-aufbessern",
     "2026-11-02-last-minute-urlaubsangebote-sichern"),
    ("2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen",
     "2026-10-26-gastarife-vergleichen-vor-dem-herbst"),
]

FREMDE_PASSAGE = (
    "Lies die Laufzeit in deinem Vertrag bevor du ein neues Angebot annimmst "
    "denn die erste feste Laufzeit darf hoechstens vierundzwanzig Monate "
    "dauern und danach kannst du jederzeit mit einer Frist von einem Monat "
    "kuendigen wenn der Vertrag still weiterlaeuft."
)

EIGENER_TEXT = (
    "Ein Konto meldet sich selten von selbst, dann aber mit einer Zahl, die "
    "niemand erwartet hat. Wer den Posten am selben Tag prueft, verhindert "
    "die naechste Diskussion am Telefon."
)


def _rohtext(body: str) -> str:
    return "---\ntitle: \"X\"\ndraft: false\n---\n\n" + body + "\n"


def _bestand_mit(paare) -> dict:
    """Synthetischer Bestand (live oder Entwurf) für die Messung."""
    bestand = {}
    for slug, body, live in paare:
        bestand[f"/k/posts/{slug}/index.md"] = {
            "slug": slug, "title": slug, "body": body, "live": live,
            "grund": "" if live else "Draft", "date": "2026-10-01T08:00:00Z",
        }
    return bestand


class BestandRegressionTests(unittest.TestCase):
    """Die sieben Paare aus #1027 bleiben unter der kritischen Schwelle."""

    @classmethod
    def setUpClass(cls):
        cls.bestand = cu.lade_bestand()
        cls.by_slug = {info["slug"]: info for info in cls.bestand.values()}

    def test_alle_paare_sind_bekannt(self):
        """Der Bestand enthält die genannten Artikel (sonst prüft der Test nichts)."""
        fehlend = [s for paar in PAARE_AUS_1027 for s in paar
                   if s not in self.by_slug]
        self.assertEqual(fehlend, [],
                         f"Artikel aus #1027 fehlen im Bestand: {fehlend}")

    def test_kein_paar_aus_1027_ist_kritisch(self):
        for a, b in PAARE_AUS_1027:
            mit_a = self.by_slug[a]
            mit_b = self.by_slug[b]
            gemeinsam = (cu.ngrams(mit_a["body"], cu.PHRASE_LEN)
                         & cu.ngrams(mit_b["body"], cu.PHRASE_LEN))
            self.assertLess(
                len(gemeinsam), cu.KRITISCH_AB,
                f"{a} <-> {b}: {len(gemeinsam)} geteilte 7-Wort-Phrasen "
                f"({sorted(gemeinsam)[:3]}) – die Dublette aus #1027 ist zurück")

    def test_kein_kritisches_live_paar_im_gesamten_bestand(self):
        """Der ganze Live-Bestand: kein Paar über der Schwelle."""
        live = [s for s, i in self.by_slug.items() if i["live"]]
        grams = {s: cu.ngrams(self.by_slug[s]["body"], cu.PHRASE_LEN) for s in live}
        kritisch = []
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                gemeinsam = grams[a] & grams[b]
                if len(gemeinsam) >= cu.KRITISCH_AB:
                    kritisch.append((a, b, len(gemeinsam)))
        self.assertEqual(kritisch, [],
                         f"Kritische Live-Überlappungen: {kritisch}")


class V4MessungTests(unittest.TestCase):
    """Die geplante Änderung misst gegen den Bestand – vor dem Schreiben."""

    def test_fremde_passage_wird_erkannt(self):
        befunde = cu.aenderung_befunde(
            "2026-11-01-probe", _rohtext(FREMDE_PASSAGE), _rohtext(EIGENER_TEXT),
            bestand=_bestand_mit([("2026-10-01-fremd", FREMDE_PASSAGE, True)]))
        self.assertEqual(len(befunde), 1, befunde)
        self.assertIn("2026-10-01-fremd", befunde[0])

    def test_eigener_text_bleibt_stumm(self):
        befunde = cu.aenderung_befunde(
            "2026-11-01-probe", _rohtext(EIGENER_TEXT), _rohtext(EIGENER_TEXT),
            bestand=_bestand_mit([("2026-10-01-fremd", FREMDE_PASSAGE, True)]))
        self.assertEqual(befunde, [])

    def test_altlast_wird_nicht_angelastet(self):
        """Wer eine Dublette abbaut, wird nicht bestraft."""
        befunde = cu.aenderung_befunde(
            "2026-11-01-probe", _rohtext(FREMDE_PASSAGE), _rohtext(FREMDE_PASSAGE),
            bestand=_bestand_mit([("2026-10-01-fremd", FREMDE_PASSAGE, True)]))
        self.assertEqual(befunde, [])

    def test_entwurf_ist_gegenseite(self):
        """Ein Entwurf kann live gehen – die Dublette darf nicht warten."""
        befunde = cu.aenderung_befunde(
            "2026-11-01-probe", _rohtext(FREMDE_PASSAGE), _rohtext(EIGENER_TEXT),
            bestand=_bestand_mit([("2026-10-03-entwurf", FREMDE_PASSAGE, False)]))
        self.assertEqual(len(befunde), 1, befunde)

    def test_eigener_artikel_ist_keine_gegenseite(self):
        befunde = cu.aenderung_befunde(
            "2026-10-01-fremd", _rohtext(FREMDE_PASSAGE), _rohtext(EIGENER_TEXT),
            bestand=_bestand_mit([("2026-10-01-fremd", FREMDE_PASSAGE, True)]))
        self.assertEqual(befunde, [])

    def test_leerer_bestand_ist_fail_closed(self):
        with self.assertRaises(ValueError):
            cu.aenderung_befunde("2026-11-01-probe", _rohtext(EIGENER_TEXT),
                                 _rohtext(EIGENER_TEXT), bestand={})

    def test_schwelle_ist_die_des_audits(self):
        """Keine zweite Zahl: derselbe Maßstab wie im Tagesaudit."""
        self.assertEqual(cu.KRITISCH_AB, 5)
        # 7 Wörter genau = eine Phrase; zwei Texte teilen sie.
        kurz = "eins zwei drei vier fuenf sechs sieben"
        befunde = cu.aenderung_befunde(
            "2026-11-01-probe", _rohtext(kurz + " und ein Rest"), _rohtext(EIGENER_TEXT),
            bestand=_bestand_mit([("2026-10-01-fremd", kurz + " noch mehr text", True)]))
        self.assertEqual(befunde, [], "eine einzelne Phrase ist keine Dublette")


class VertragV4Tests(unittest.TestCase):
    """Der Publikations-Vertrag (V4) nutzt die geteilte Messung."""

    def test_uebernommene_passage_wird_verweigert(self):
        gruende = pv.pruefe(
            "2026-11-01-probe", _rohtext(EIGENER_TEXT),
            _rohtext(FREMDE_PASSAGE),
            bestand=_bestand_mit([("2026-10-01-fremd", FREMDE_PASSAGE, True)]))
        v4 = [g for g in gruende if g.startswith("V4")]
        self.assertEqual(len(v4), 1, gruende)
        self.assertIn("2026-10-01-fremd", v4[0])

    def test_saubere_aenderung_ist_erlaubt(self):
        gruende = pv.pruefe(
            "2026-11-01-probe", _rohtext(EIGENER_TEXT),
            _rohtext(EIGENER_TEXT + " Noch ein eigener Satz."),
            bestand=_bestand_mit([("2026-10-01-fremd", FREMDE_PASSAGE, True)]))
        self.assertEqual([g for g in gruende if g.startswith("V4")], [], gruende)

    def test_ohne_messung_fails_closed(self):
        """Kein Bestand = keine Messung = kein Freispruch."""
        gruende = pv.pruefe(
            "2026-11-01-probe", _rohtext(EIGENER_TEXT), _rohtext(EIGENER_TEXT),
            bestand={})
        self.assertTrue(any(g.startswith("V3") for g in gruende),
                        f"fail-closed fehlt: {gruende}")

    def test_signatur_bleibt_rueckwaertskompatibel(self):
        """Sechs Verbraucher rufen `pruefe` positional mit drei Argumenten."""
        gruende = pv.pruefe("2026-11-01-probe", _rohtext(EIGENER_TEXT),
                            _rohtext(EIGENER_TEXT))
        self.assertIsInstance(gruende, list)

    def test_selbsttest_des_vertrags_ist_gruen(self):
        self.assertEqual(pv.selftest(), 0)


class GovernanceC22Tests(unittest.TestCase):
    """C22 pinnt V4 – wer die Messung abschaltet, wird gefunden."""

    @classmethod
    def setUpClass(cls):
        cls.echte = {
            name: gc._read(os.path.join(gc.BLOG_DIR, "scripts", name))
            for name in ("publikations_vertrag.py", "redaktions_standard.py",
                         "publish_gate.py", "check_uniqueness.py")
        }

    def test_echter_zustand_ist_still(self):
        self.assertEqual(gc.c22_publikations_vertrag(self.echte), [])

    def test_sabotage_v4_weg(self):
        sabo = dict(self.echte, **{
            "publikations_vertrag.py":
                self.echte["publikations_vertrag.py"].replace(
                    "aenderung_befunde", "abgeschaltete_messung")})
        befunde = gc.c22_publikations_vertrag(sabo)
        self.assertTrue([f for f in befunde if "aenderung_befunde" in f[1]],
                        f"Sabotage unentdeckt: {befunde}")

    def test_sabotage_eigene_schwelle(self):
        sabo = dict(self.echte, **{
            "publikations_vertrag.py":
                "KRITISCH_AB = 5\n" + self.echte["publikations_vertrag.py"]})
        befunde = gc.c22_publikations_vertrag(sabo)
        self.assertTrue([f for f in befunde if "KRITISCH_AB" in f[1]],
                        f"Sabotage unentdeckt: {befunde}")

    def test_sabotage_messung_entfernt(self):
        sabo = dict(self.echte, **{
            "check_uniqueness.py":
                self.echte["check_uniqueness.py"].replace(
                    "def aenderung_befunde(", "def entfernt(")})
        befunde = gc.c22_publikations_vertrag(sabo)
        self.assertTrue([f for f in befunde if "aenderung_befunde" in f[1]],
                        f"Sabotage unentdeckt: {befunde}")


if __name__ == "__main__":
    unittest.main()
