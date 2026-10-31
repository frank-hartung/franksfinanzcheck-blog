"""Regressionstests: Grammatik-Kongruenz LT5/LT6 (Auftrag 30.10.2026).

Verträge („Rechtschreib- und Grammatikprüfung dauerhaft auf Highend-Niveau
einer Profi-Agentur“):

  1) BEFUND: Der Vorfall-Artikel stand mit „Dein Schritt-für-Schritt-
     Anleitung“ in Titel, H1, Cover und Pinterest – und alle bisherigen
     Wachen meldeten 0 Funde (LT1–LT4 prüfen Wendungen, keine Morphologie).
  2) BEWEIS: Die Prüfung rät kein Genus. Sie liest es aus
     data/genus_lexikon.txt und rechnet die Lesungen der Artikelwörter
     dagegen. Nur wenn genau EIN Ziel übrig bleibt, wird geschrieben.
  3) KEINE FALSCH-POSITIVE: Relativpronomen, Demonstrativpronomen, schwache
     Adjektivdeklination, Komposita mit Leerzeichen und die Fügung
     „um … willen“ sind korrektes Deutsch und bleiben unangetastet.
  4) TITEL: Cover-Marken-Lock. Der Titel wird nur mit --fix-titel und nur
     bei eindeutigem Ziel geschrieben; die Cover-Varianten rendert danach
     check_covers.py --fix.
  5) IDEMPOTENZ: Ein zweiter Lauf ändert nichts mehr.

Ausführung: python3 -m unittest discover -s scripts/tests
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import grammar_check  # noqa: E402
import sprachkern  # noqa: E402


class LexikonTests(unittest.TestCase):
    """Das Genus-Lexikon ist die einzige Wissensquelle – sie muss sauber sein."""

    @classmethod
    def setUpClass(cls):
        cls.lexikon = grammar_check.lade_genus_lexikon()

    def test_lexikon_wird_geladen(self):
        self.assertGreaterEqual(len(self.lexikon), 400,
                                "Genus-Lexikon fehlt oder ist zu klein")

    def test_format_und_eindeutigkeit(self):
        probleme, _ = grammar_check.lexikon_pruefen(self.lexikon)
        self.assertEqual(probleme, [], f"Lexikon-Befunde: {probleme}")

    def test_vorfall_nomen_ist_erfasst(self):
        self.assertIn("schritt-für-schritt-anleitung", self.lexikon)
        self.assertEqual(self.lexikon["schritt-für-schritt-anleitung"],
                         (("f", "sg"),))

    def test_mehrdeutige_nomen_sind_mehrdeutig(self):
        # der Nutzen (m) / das Nutzen (n) – nie automatisch heilbar
        self.assertEqual(len(self.lexikon["nutzen"]), 2)
        # der Gehalt (m) / das Gehalt (n)
        self.assertEqual(len(self.lexikon["gehalt"]), 2)


class LexikonAnkerTests(unittest.TestCase):
    """Anker-Genera des Kernwortschatzes.

    Ein falsches Genus im Lexikon ist teurer als ein fehlender Eintrag: Es
    erzeugt einen FALSCHEN Fix. Am 30.10.2026 standen „internet“ als m und
    „unterschrift“ als m im Lexikon – beide hätten „der Internet“ bzw. „dem
    Unterschrift“ geschrieben. Diese Liste ist der billigste Schutz davor:
    die 40 häufigsten Wörter des Blogs, geprüft gegen das Duden-Genus.
    """

    ANKER = {
        # maskulin
        "preis": "m", "vertrag": "m", "tarif": "m", "anbieter": "m", "verbrauch": "m",
        "beitrag": "m", "betrag": "m", "monat": "m", "zähler": "m", "notgroschen": "m",
        "strompreis": "m", "zinssatz": "m", "kredit": "m", "rabatt": "m", "bonus": "m",
        "link": "m", "vergleich": "m", "kalender": "m", "kern": "m", "raum": "m",
        "urlaub": "m", "einstieg": "m", "schritt": "m", "grund": "m", "wert": "m",
        # feminin
        "rechnung": "f", "regel": "f", "bank": "f", "summe": "f", "kündigung": "f",
        "ersparnis": "f", "frist": "f", "anleitung": "f", "unterschrift": "f",
        "schritt-für-schritt-anleitung": "f", "einrichtung": "f", "optimierung": "f",
        "gebühr": "f", "rendite": "f", "sparrate": "f", "absicherung": "f",
        # neutrum
        "geld": "n", "konto": "n", "jahr": "n", "gerät": "n", "risiko": "n",
        "budget": "n", "ergebnis": "n", "internet": "n", "depot": "n", "foto": "n",
        "blatt": "n", "fundament": "n", "eigentum": "n", "unterkonto": "n",
        # nur Plural
        "mehrkosten": "pl", "kosten": "pl", "fixkosten": "pl", "bedingungen": "pl",
        "unterlagen": "pl", "zinsen": "pl",
        # absichtlich mehrdeutig → nie automatisch heilen
        "gehalt": "m/n", "nutzen": "m/n", "teil": "m/n", "thermostat": "n/m",
        "artikel": "m/pl",
    }

    def test_anker_genera(self):
        lexikon = grammar_check.lade_genus_lexikon()
        falsch = []
        for wort, erwartet in self.ANKER.items():
            ist = lexikon.get(wort)
            if ist is None:
                falsch.append(f"{wort}: fehlt (erwartet {erwartet})")
                continue
            tag = "/".join(sorted({g for g, _n in ist}))
            # m/pl und n/pl sind für ein Einzel-Genus die zulässige Erweiterung
            # (gleichlautender Plural: „die Anbieter“) – kein Widerspruch.
            ok = (tag == "/".join(sorted(erwartet.split("/")))
                  or (erwartet in ("m", "n", "f") and tag == erwartet + "/pl"))
            if not ok:
                falsch.append(f"{wort}: {tag} statt {erwartet}")
        self.assertEqual(falsch, [], "Lexikon-Anker falsch: " + "; ".join(falsch))

    def test_mehrdeutige_anker_heilen_nie(self):
        lexikon = grammar_check.lade_genus_lexikon()
        for satz in ("dein Nutzen", "das Gehalt", "der Teil", "den Thermostat"):
            funde = grammar_check.kongruenz_funde(satz, lexikon)
            self.assertTrue(all(f["fix"] is None for f in funde), satz)


class KongruenzBefundTests(unittest.TestCase):
    """Was gefunden werden MUSS (inkl. der Vorfall-Zeile)."""

    @classmethod
    def setUpClass(cls):
        cls.lexikon = grammar_check.lade_genus_lexikon()

    def funde(self, text):
        return grammar_check.kongruenz_funde(text, self.lexikon)

    def heile(self, text):
        return grammar_check.kongruenz_heilen(text, self.lexikon)[0]

    def test_titel_des_vorfalls(self):
        titel = "ETF-Sparplan starten: Dein Schritt-für-Schritt-Anleitung"
        funde = self.funde(titel)
        self.assertEqual(len(funde), 1)
        self.assertEqual(funde[0]["rule"], "LT5")
        self.assertEqual(funde[0]["fix"], "Deine")
        self.assertTrue(self.heile(titel).endswith("Deine Schritt-für-Schritt-Anleitung"))

    def test_genus_ueber_bestimmten_artikel(self):
        self.assertIn("das Geld", self.heile("die Geld liegt auf dem Konto."))

    def test_aeussere_anrede_grossschreibung_bleibt(self):
        # Satzanfang groß → Fix wird ebenfalls groß geschrieben
        self.assertTrue(self.heile("Dein Anleitung ist gut.").startswith("Deine "))

    def test_kasus_aus_praeposition(self):
        self.assertIn("mit deinem Konto", self.heile("Du sparst mit dein Konto."))
        self.assertIn("um einen Grad", self.heile("Senke die Temperatur um ein Grad."))
        self.assertIn("für die Kontrolle", self.heile("Du zahlst für der Kontrolle."))

    def test_wechselpraeposition_ist_kein_ausloeser(self):
        # „auf“ regiert zwei Kasus – keine Aussage möglich, also kein Fund
        self.assertEqual(self.funde("Leg es auf dein Konto."), [])

    def test_mehrdeutiges_ziel_bleibt_report(self):
        funde = self.funde("Dieser Konto ist leer.")  # n: dieses (nom) / diesem (dat)
        self.assertEqual(len(funde), 1)
        self.assertIsNone(funde[0]["fix"])
        self.assertIn("diesem", funde[0]["hinweis"])


class FalschPositivTests(unittest.TestCase):
    """Korrektes Deutsch, das eine Oberflächen-Regel zerstören würde."""

    @classmethod
    def setUpClass(cls):
        cls.lexikon = grammar_check.lade_genus_lexikon()

    def heile(self, text):
        return grammar_check.kongruenz_heilen(text, self.lexikon)[0]

    def test_relativpronomen_nach_komma(self):
        satz = "Personen, die Geld für Ziele brauchen, sparen früh."
        self.assertEqual(self.heile(satz), satz)

    def test_demonstrativpronomen(self):
        satz = "Sind das Werte, die deutlich darüber liegen?"
        self.assertEqual(self.heile(satz), satz)

    def test_schwache_adjektivdeklination(self):
        for satz in ("Auf dem einen Konto laufen alle Abbuchungen.",
                     "Arbeitsmittel auf der einen Seite, private Käufe auf der anderen."):
            self.assertEqual(self.heile(satz), satz)

    def test_kompositum_mit_leerzeichen(self):
        for satz in ("Kriterien für den Girokonto Vergleich",
                     "## Checkliste für den Heizung Vergleich",
                     "Die Energieausweis Kosten steigen."):
            self.assertEqual(self.heile(satz), satz)

    def test_fuegung_um_willen(self):
        satz = "Das Ziel ist nicht Kontrolle um der Kontrolle willen."
        self.assertEqual(self.heile(satz), satz)

    def test_plural_dativ_wird_nie_am_artikelwort_geheilt(self):
        # „den Preise“ bräuchte „den Preisen“ – das Nomen ändert sich mit
        funde = grammar_check.kongruenz_funde("Bei den Preise fehlt ein Wert.",
                                              self.lexikon)
        self.assertTrue(all(f["fix"] is None for f in funde))

    def test_gleichlautender_plural(self):
        for satz in ("Die Anbieter senken den Preis.",
                     "Manche Anbieter locken mit Boni.",
                     "Öffne die Fenster und drehe den Gashahn zu.",
                     "Entlüfte deine Heizkörper vor dem Winter."):
            self.assertEqual(self.heile(satz), satz)

    def test_markdown_und_links_bleiben(self):
        satz = "`Dein Anleitung` und [Dein Anleitung](../../posts/x/) bleiben."
        self.assertEqual(self.heile(satz), satz)


class TitelHeilungTests(unittest.TestCase):
    """Cover-Marken-Lock: Titel nur mit --fix-titel, nur bei Beweis."""

    @classmethod
    def setUpClass(cls):
        cls.lexikon = grammar_check.lade_genus_lexikon()

    FM = ('---\ntitle: "ETF-Sparplan starten: Dein Schritt-für-Schritt-Anleitung"\n'
          'description: "Ein Text."\n---\n')

    def test_titel_wird_geheilt_und_zitat_bleibt(self):
        fm, info = grammar_check.heile_titelzeile(self.FM, self.lexikon)
        self.assertIn('title: "ETF-Sparplan starten: Deine Schritt-für-Schritt-Anleitung"', fm)
        self.assertEqual(info[1], "ETF-Sparplan starten: Deine Schritt-für-Schritt-Anleitung")
        # Nur die Titelzeile ist betroffen
        self.assertIn('description: "Ein Text."', fm)
        self.assertEqual(fm.count("title:"), 1)

    def test_ohne_ziel_keine_schreibung(self):
        fm = '---\ntitle: "Die Anbieter und ihre Preise"\n---\n'
        neu, info = grammar_check.heile_titelzeile(fm, self.lexikon)
        self.assertEqual(neu, fm)
        self.assertIsNone(info)

    def test_analyze_meldet_titel_ohne_fix(self):
        a = {"body": "Ein sauberer Satz.", "description": "",
             "title": "ETF-Sparplan starten: Dein Schritt-für-Schritt-Anleitung",
             "slug": "x", "fm": self.FM, "content": "", "prefix": ""}
        funde = grammar_check.analyze(a, set(), self.lexikon)
        titel = [f for f in funde if f.get("zone") == "title"]
        self.assertEqual(len(titel), 1)
        self.assertIsNone(titel[0]["fix"])          # nie schreiben
        self.assertEqual(titel[0]["vorschlag"], "Deine")  # aber vorschlagen


class VertragsTests(unittest.TestCase):
    def test_selbsttest_gruen(self):
        self.assertEqual(grammar_check.run_selftest(), [])

    def test_idempotenz(self):
        lexikon = grammar_check.lade_genus_lexikon()
        einmal = grammar_check.kongruenz_heilen(
            "Dein Anleitung liegt neben die Geld.", lexikon)[0]
        zweimal = grammar_check.kongruenz_heilen(einmal, lexikon)[0]
        self.assertEqual(einmal, zweimal)

    def test_ohne_lexikon_keine_funde(self):
        """Fehlt das Lexikon, prüft die Wache nichts – statt zu raten."""
        self.assertEqual(grammar_check.kongruenz_funde("die Geld liegt da.", {}), [])

    def test_schutzzonen_von_sprachkern(self):
        """Die Kongruenz-Heilung benutzt denselben Schutzzonen-Kern."""
        text = ('`die Geld` und [die Geld](https://x.de) und '
                '{{< figure alt="die Geld" >}}')
        self.assertEqual(grammar_check.kongruenz_heilen(
            text, grammar_check.lade_genus_lexikon())[0], text)
        # Text IM Shortcode ist Inhalt und wird geprüft (die Tags selbst nicht)
        innen = "{{< box >}}die Geld{{< /box >}}"
        self.assertEqual(grammar_check.kongruenz_heilen(
            innen, grammar_check.lade_genus_lexikon())[0],
            "{{< box >}}das Geld{{< /box >}}")


if __name__ == "__main__":
    unittest.main()


class LexikonPflegeTests(unittest.TestCase):
    """Die drei Pflege-Wächter des Lexikons (30.10.2026).

    Alle drei sind aus echten Fehlern entstanden, die beim Aufbau passiert
    sind – ein Lexikon ohne diese Wächter verrottet leise und schreibt dann
    falsche Sätze „heil“.
    """

    def test_echtes_lexikon_ist_sauber(self):
        probleme, verteilung = grammar_check.lexikon_pruefen()
        self.assertEqual(probleme, [])
        self.assertGreaterEqual(sum(verteilung.values()), 400)

    def test_plural_gleichheit_wird_erkannt(self):
        # „das Kabel“ → „die Kabel“: Ohne /pl hielte die Wache „keine Kabel“
        # für falsch und schriebe „kein Kabel“ – passiert am 30.10.2026.
        lex = {"kabel": (("n", "sg"),)}
        funde = grammar_check.kongruenz_funde("Wir brauchen keine Kabel.", lex)
        self.assertTrue(any(f["fix"] for f in funde))
        lex_ok = {"kabel": (("n", "sg"), ("pl", "pl"))}
        self.assertEqual(grammar_check.kongruenz_funde("Wir brauchen keine Kabel.", lex_ok), [])

    def test_mehrdeutiges_genus_heilt_nie(self):
        lex = {"gehalt": (("m", "sg"), ("n", "sg"))}
        for satz in ("das Gehalt", "der Gehalt", "dem Gehalt"):
            self.assertTrue(all(f["fix"] is None
                                for f in grammar_check.kongruenz_funde(satz, lex)), satz)

    def test_ohne_lexikon_keine_funde(self):
        self.assertEqual(grammar_check.kongruenz_funde("Dein Schritt-für-Schritt-Anleitung", {}), [])

    def test_suffix_waechter_kennt_feminine_endungen(self):
        quelle = open(grammar_check.__file__, encoding="utf-8").read()
        self.assertIn("FEM_SUFFIX", quelle)
        for endung in ("ung", "heit", "keit", "schaft"):
            self.assertIn(endung, quelle)
