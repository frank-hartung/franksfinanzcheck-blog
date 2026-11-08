#!/usr/bin/env python3
"""Regression: Betriebsflächen öffnen keine menschliche Entscheidung (#1072).

DER DEFEKT (07.11.2026, Vorgang #1072-Nachlauf)
----------------------------------------------
Der Ledger band eine Entscheidung an den vollständigen Body. Damit riss
jede Maschinen-Schreibe eine dokumentierte Entscheidung wieder auf:

  * `gsc_abdeckung.py --verlinkung --heilen` hängt seit dem 06.11.2026
    einen Link an die `**Weiterlesen:**`-Zeile (Selbstheilung #1097).
  * Der Abbildungs-Lauf schreibt `![…](…)` und `*Abbildung: …*` nach.

Folge auf `main`: **8 von 11** bereits entschiedene Befunde standen wieder
offen – bei Gas 08-12 und 08-24 waren die Aussageflächen am
Entscheidungstag und heute nachweislich identisch. Die Scorecard meldete
„F4 blockiert“ für Sätze, die niemand angefasst hatte, und die Redaktion
sollte Texte erneut lesen, an denen sich nichts geändert hatte.

DIE REGEL, DIE HIER EINGEFROREN WIRD
------------------------------------
1. Betriebsflächen (Weiterlesen, Lesetipp, Transparenz, Abbildung,
   Affiliate-Disclaimer, Werkzeug-Anhang `## Weiterrechnen und vertiefen`)
   ändern den Aussage-Hash NICHT.
2. Eine echte Textänderung öffnet die Entscheidung SOFORT – auch ein
   einziger Satz, auch eine Zahl, auch eine Überschrift.
3. Eine Regeländerung darf keine Redaktionsarbeit löschen: Entscheidungen,
   die an die alte, breitere Fassung gebunden sind (`text_alt`), bleiben
   gültig, solange der heutige Text sie deckt.
4. Die Prüffassung (`pruef_hash`) bleibt vollständig: Die KI-Fachprüfung
   sieht weiterhin alles, inklusive Quellen und Betriebsflächen.

Lauf: python3 -m unittest scripts.tests.test_faktenfrische_betriebsflaechen
"""
import datetime as dt
import json
import sys
import tempfile
import unittest

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische_befund_ledger as ledger  # noqa: E402

TAG = dt.date(2026, 11, 7)
FM = 'title: "T"\ndescription: "D"\nkurzantwort: "K"\n'
SATZ = "Der Abschlag bleibt eine Vorauszahlung.\n"

# Was der Betrieb schreibt – jede Zeile ist im Bestand belegt.
BETRIEB = (
    "\n![Merkkarte: Kernaussagen](abbildung-merkkarte.svg)\n"
    "\n*Abbildung: Merkkarte (eigene Darstellung aus diesem Beitrag).*\n"
    "\n**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung). "
    "Beim Abschluss über einen Link erhalten wir eine Provision.\n"
    "\n💡 **Schnell-Tipp von FranksFinanzcheck:** Vergleiche nicht nur die "
    "Rabattphase, sondern den Effektivpreis: [**Tarife vergleichen**](/go/dsl/)\n"
    "_(Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über "
    "einen Link erhalten wir eine Provision – für dich entstehen keine "
    "Mehrkosten.)_\n"
    "\n**Weiterlesen:** [A](../../posts/a/) · [B](../../posts/b/) "
    "· [Ratgeber](../../pillar/c/)\n"
)
WERKZEUG_ANHANG = (
    "\n## Weiterrechnen und vertiefen\n\n"
    "- **Rechner:** [Haushaltsbudget](/werkzeuge/haushaltsbudget/)\n"
)


def art(body, fm=FM):
    return {"fm": fm, "body": body}


def mit_betrieb(substanz="# H\n\n" + SATZ):
    return art(substanz + BETRIEB + WERKZEUG_ANHANG)


class AussageflaechenTest(unittest.TestCase):
    """Was eine Aussage ist – und was nur Betrieb ist."""

    def test_betriebsflaechen_aendern_den_aussage_hash_nicht(self):
        ohne = art("# H\n\n" + SATZ)
        mit = mit_betrieb()
        self.assertEqual(ledger.text_hash(ohne), ledger.text_hash(mit))

    def test_prueffassung_sieht_die_betriebsflaechen_weiterhin(self):
        """Die KI-Prüfung darf nicht blind werden – nur die Bindung wird feiner."""
        ohne = art("# H\n\n" + SATZ)
        mit = mit_betrieb()
        self.assertNotEqual(ledger.pruef_hash(ohne), ledger.pruef_hash(mit))

    def test_echter_satz_oeffnet(self):
        ohne = art("# H\n\n" + SATZ)
        for neu in (
            art("# H\n\nDer Abschlag ist gesetzlich festgelegt.\n" + BETRIEB),
            art("# H\n\n" + SATZ + "Ein zweiter Satz kommt hinzu.\n" + BETRIEB),
            art("# H\n\n" + SATZ + "\n## Neue Überschrift\n\n" + BETRIEB),
        ):
            with self.subTest(neu=neu["body"][:40]):
                self.assertNotEqual(ledger.text_hash(ohne), ledger.text_hash(neu))

    def test_zahl_im_satz_oeffnet(self):
        ohne = art("# H\n\nDer Abschlag liegt bei 80 Euro.\n")
        mit = art("# H\n\nDer Abschlag liegt bei 95 Euro.\n")
        self.assertNotEqual(ledger.text_hash(ohne), ledger.text_hash(mit))

    def test_titel_und_kurzantwort_bleiben_gebunden(self):
        """Nur der Body hat Betriebsflächen – Kopffelder sind immer Aussage."""
        a = art("# H\n\n" + SATZ, FM.replace('"T"', '"Titel A"'))
        b = art("# H\n\n" + SATZ, FM.replace('"T"', '"Titel B"'))
        self.assertNotEqual(ledger.text_hash(a), ledger.text_hash(b))

    def test_werkzeug_anhang_endet_an_der_naechsten_ueberschrift(self):
        """Der Anhang schluckt keinen Redaktionstext – auch keinen nach ihm."""
        danach = art("# H\n\n" + SATZ + WERKZEUG_ANHANG
                     + "\n## Häufige Fragen\n\nEine echte Antwort.\n")
        ohne_danach = art("# H\n\n" + SATZ + WERKZEUG_ANHANG)
        self.assertNotEqual(ledger.text_hash(danach), ledger.text_hash(ohne_danach))


class RueckwaertsbindungTest(unittest.TestCase):
    """Eine Regeländerung darf keine dokumentierte Entscheidung löschen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.queue = self.dir / "queue.json"
        self.decisions = self.dir / "decisions.yaml"
        self.finding = {"typ": "luecke", "text": "Zahl ohne Beleg"}
        self.vorher = art("# H\n\n" + SATZ)
        # Die Fassung, an die VOR der Regeländerung entschieden wurde: der
        # damalige `text_hash` rechnete über den ROHEN Body (mit Betriebs-
        # flächen). Am 07.11.2026 für 104 Entscheidungen nachgewiesen.
        self.alt_fassung = ledger._text_hash_roh(self.vorher, "roh")
        self.entry = {
            "id": ledger.befund_id("seite", self.finding), "slug": "seite",
            "fassung_sha256": self.alt_fassung,
            "text_sha256": self.alt_fassung,
            **self.finding, "beleg": "", "zuletzt_gesehen": "2026-11-07 09:00 UTC",
        }
        self.queue.write_text(json.dumps({"fachbefunde": [self.entry]}),
                              encoding="utf-8")
        self.fassungen = {"seite": self._fassung(self.vorher)}

    def _fassung(self, artikel):
        """Genau die Lesarten, die `bestand_identitaeten()` liefert."""
        return {"text": ledger.text_hash(artikel),
                "pruef": ledger.pruef_hash(artikel),
                "text_alt": ledger._text_hash_roh(artikel, "roh"),
                "text_alt_nackt": ledger._text_hash_roh(artikel, "nackt"),
                "text_alt_ein": ledger._text_hash_roh(artikel, "ein"),
                "text_v1": ledger._text_hash_nackt(artikel, "betrieb-v1"),
                "text_v1_rand": ledger._text_hash_nackt(artikel, "betrieb-v1-rand")}

    def tearDown(self):
        self.tmp.cleanup()

    def _entscheiden(self):
        """Entscheidung im ALTEN Schema: gebunden an den nackten Body-Hash.

        Genau so stehen die 115 Entscheidungen im Bestand, die vor dem
        07.11.2026 geschrieben wurden – und genau die dürfen die
        Betriebsflächen nicht mitreißen.
        """
        self.decisions.write_text(yaml.safe_dump({"entscheidungen": [{
            "slug": "seite", "befund_id": self.entry["id"],
            "befund_fassung": self.alt_fassung,
            "geprueft_fassung": self.alt_fassung,
            "entschieden_von": "Redaktion",
            "begruendung": "Satz am heutigen Text geprüft und belegt",
        }]}), encoding="utf-8")

    def test_entschieden_ist_entschieden(self):
        self._entscheiden()
        self.assertEqual(
            ledger.offene_befunde(self.queue, self.decisions, self.fassungen), [])

    def test_feine_projektion_ueberlebt_die_verlinkung(self):
        """Der historische Defekt – mit der feinen Projektion behoben.

        Die Entscheidung wird hier an `text` gebunden (so schreibt es
        `--entscheiden` seit dem 07.11.2026). Dann öffnet der
        Verlinkungs-Heiler nichts mehr.
        """
        entscheidung_anfuegen = ledger.entscheidung_anfuegen
        entscheidung_anfuegen(
            self.entry["id"], "Redaktion",
            "Satz am heutigen Text geprüft und belegt",
            queue_path=self.queue, decisions_path=self.decisions,
            fassungen=self.fassungen, heute=TAG)
        neu = {"seite": self._fassung(mit_betrieb())}
        self.assertNotEqual(self.alt_fassung, neu["seite"]["text_alt"])
        self.assertEqual(
            ledger.offene_befunde(self.queue, self.decisions, neu), [],
            "Betriebsfläche hat eine dokumentierte Entscheidung geöffnet")

    def test_altbindung_oeffnet_bis_zur_umbindung(self):
        """Dokumentiert den Zustand, den die Umbindung heilt (und warum)."""
        self._entscheiden()                      # Altbindung an den rohen Body
        neu = {"seite": self._fassung(mit_betrieb())}
        self.assertEqual(
            len(ledger.offene_befunde(self.queue, self.decisions, neu)), 1,
            "Altbindung sollte den Betriebseingriff sehen – sonst prüft der "
            "Umbindungs-Test nichts")

    def test_neue_entscheidung_bindet_an_die_feine_fassung(self):
        """Nur der Rückweg ist breit – neue Entscheidungen nicht."""
        d = ledger.entscheidung_anfuegen(
            self.entry["id"], "Redaktion",
            "Satz am heutigen Text geprüft und belegt",
            queue_path=self.queue, decisions_path=self.decisions,
            fassungen=self.fassungen, heute=TAG)
        self.assertEqual(d["geprueft_fassung"], ledger.text_hash(self.vorher))
        self.assertNotEqual(d["geprueft_fassung"],
                            ledger._text_hash_nackt(self.vorher))

    def test_umbindung_hebt_die_altbindung_an(self):
        """Ohne Umbindung reißt eine CTA-Route die Altentscheidung auf."""
        self._entscheiden()
        cta = "\n👉 **Jetzt vergleichen:** [**→ Gastarife prüfen**](/go/gas/)\n"
        nachher = {"seite": self._fassung(art("# H\n\n" + SATZ + cta))}
        self.assertEqual(len(ledger.offene_befunde(
            self.queue, self.decisions, nachher)), 1)
        bericht = ledger.bindung_auf_feine_projektion(
            decisions_path=self.decisions, fassungen=self.fassungen)
        self.assertEqual(len(bericht["umgebunden"]), 1)
        self.assertEqual(ledger.offene_befunde(
            self.queue, self.decisions, nachher), [],
            "Umbindung hat die Betriebstoleranz nicht hergestellt")
        # Der historische Beweis bleibt erhalten.
        d = ledger.entscheidungen_laden(self.decisions)[
            ("seite", self.entry["id"])]
        self.assertEqual(d["ursprungs_geprueft_fassung"], self.alt_fassung)

    def test_echte_aenderung_oeffnet_trotz_rueckwaertsbindung(self):
        self._entscheiden()
        echt = art("# H\n\n" + SATZ + "Ein neuer Satz mit einer Zahl von 95 Euro.\n"
                   + BETRIEB)
        neu = {"seite": self._fassung(echt)}
        self.assertEqual(
            len(ledger.offene_befunde(self.queue, self.decisions, neu)), 1)


class RueckfallTest(unittest.TestCase):
    """Die Fälle, die den Bestand am 07.11.2026 tatsächlich geöffnet haben."""

    def test_retarget_der_schnell_tipp_route_oeffnet_nicht(self):
        """affiliate_marketer.py tauscht /go/<route>/ – Betrieb, keine Aussage."""
        vorher = art("# H\n\n" + SATZ
                     + "\n💡 **Schnell-Tipp von FranksFinanzcheck:** Prüfe den "
                       "Effektivpreis: [**Tarife vergleichen**](/go/dsl/)\n")
        nachher = art("# H\n\n" + SATZ
                      + "\n💡 **Schnell-Tipp von FranksFinanzcheck:** Prüfe den "
                        "Effektivpreis: [**Tarife vergleichen**](/go/allgemein/)\n")
        self.assertEqual(ledger.text_hash(vorher), ledger.text_hash(nachher))

    def test_schnell_tipp_mit_prozentwert_bleibt_gebunden(self):
        """Ein Zinsversprechen im Werbebaustein ist eine Marktbehauptung."""
        zeile = ("💡 **Schnell-Tipp von FranksFinanzcheck:** Sichere dir "
                 "[**3,5 % Zinsen**](/go/tagesgeld/)\n")
        self.assertFalse(ledger.betriebsflaeche(zeile.strip()))

    def test_redaktionelles_transparenz_bullet_bleibt_gebunden(self):
        """„Das Wichtigste in Kürze“ enthält ein Bullet, das so heißt."""
        zeile = ("* **Transparenz:** Intelligente Steckdosen entlarven "
                 "Standby-Sünder in deinem Haushalt.")
        self.assertFalse(ledger.betriebsflaeche(zeile))

    def test_offenlegungssatz_ist_betriebsflaeche(self):
        for zeile in (
            "**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung).",
            "> **Transparenz:** Dieser Blog enthält Affiliate-Links (Werbung).",
            "Transparenz: Dieser Beitrag enthält Affiliate-Links (Werbung).",
        ):
            with self.subTest(zeile=zeile):
                self.assertTrue(ledger.betriebsflaeche(zeile))

    def test_weiterlesen_prosa_bleibt_gebunden(self):
        """5 Artikel im Bestand haben dort Fließtext statt Linkliste."""
        zeile = ("**Weiterlesen:** Der [Ratgeber](../../pillar/strom-sparen/) "
                 "erklärt weitere Wege zur Tarifwahl.")
        self.assertFalse(ledger.betriebsflaeche(zeile))

    def test_abbildung_mit_gliederung_traegt_keine_aussage(self):
        """Die Zahlen der Merkkarte sind Ableitung, nicht Redaktion."""
        zeile = ("*Abbildung: Gliederung zu „DSL-Wechselbonus sichern“ – "
                 "5 Stationen von „Was du brauchst“ bis „Fazit“*")
        self.assertTrue(ledger.betriebsflaeche(zeile))

    def test_projektion_v1_bleibt_unveraendert(self):
        """Die eingefrorene Vorgänger-Regel darf sich nicht mitändern."""
        # v1 kannte den Schnell-Tipp noch nicht: Dort ist die Zeile Aussage.
        zeile = ("💡 **Schnell-Tipp von FranksFinanzcheck:** "
                 "[**Tarife vergleichen**](/go/dsl/)")
        self.assertFalse(ledger._betriebsflaeche_v1(zeile))
        self.assertTrue(ledger.betriebsflaeche(zeile))

    def test_projektionswechsel_entwertet_keine_entscheidung(self):
        """Der Grund für PROJEKTIONEN: v2 verschärfen ≠ Arbeit löschen."""
        body = ("# H\n\n" + SATZ
                + "\n* **Transparenz:** Intelligente Steckdosen entlarven "
                  "Standby-Sünder.\n")
        a = art(body)
        # Ein am 07.11. um 10:00 UTC entschiedener Hash (Projektion v1).
        alt_v1 = ledger._text_hash_nackt(a, "betrieb-v1")
        fassungen = {"seite": {"text": ledger.text_hash(a),
                               "pruef": ledger.pruef_hash(a),
                               "text_alt": ledger._text_hash_nackt(a),
                               "text_v1": alt_v1}}
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "q.json"
            dec = Path(tmp) / "d.yaml"
            finding = {"typ": "luecke", "text": "Zahl ohne Beleg"}
            entry = {"id": ledger.befund_id("seite", finding), "slug": "seite",
                     "fassung_sha256": alt_v1, "text_sha256": alt_v1,
                     **finding, "beleg": ""}
            queue.write_text(json.dumps({"fachbefunde": [entry]}),
                             encoding="utf-8")
            dec.write_text(yaml.safe_dump({"entscheidungen": [{
                "slug": "seite", "befund_id": entry["id"],
                "befund_fassung": alt_v1, "geprueft_fassung": alt_v1,
                "entschieden_von": "Redaktion",
                "begruendung": "Am heutigen Text geprüft und erledigt",
            }]}), encoding="utf-8")
            self.assertEqual(ledger.offene_befunde(queue, dec, fassungen), [])


class BestandTest(unittest.TestCase):
    """Der echte Bestand: zwischen Betriebsflächen und Aussage unterscheidbar."""

    def test_jede_live_seite_hat_einen_aussage_hash(self):
        fassungen = ledger.fassungen_aus_bestand()
        self.assertTrue(fassungen)
        for slug, f in fassungen.items():
            with self.subTest(slug=slug):
                self.assertRegex(f["text"], r"^[0-9a-f]{64}$")
                self.assertRegex(f["text_alt"], r"^[0-9a-f]{64}$")

    def test_weiterlesen_zeile_ist_nicht_teil_der_aussage(self):
        """Der Fall, der am 07.11.2026 acht Entscheidungen öffnete."""
        vorher = art("# H\n\n" + SATZ)
        nachher = art("# H\n\n" + SATZ
                      + "\n**Weiterlesen:** [Ökostrom](../../posts/oekostrom/)\n")
        self.assertEqual(ledger.text_hash(vorher), ledger.text_hash(nachher))


if __name__ == "__main__":
    unittest.main()
