#!/usr/bin/env python3
"""Regressionstests für den REDAKTIONS-STANDARD-Schreiber (Vorgang WF-54C4/#607).

Am 05.10.2026 schrieb die KI-Heilung (`--fix --ai`) einen Live-Artikel von
Flesch 68,7 auf 44,3 und fügte „In diesem Beitrag erfährst du …“ ein. Ihre
Struktur-Prüfung (`_verify`: Links, H2-Anzahl, Länge, Trennlinien) fand
nichts – blockiert hat den Artikel erst der nächste Deploy-Lauf (Exit 1,
Produktionsalarm WF-54C4). Diese Tests frieren die fehlende Stufe ein:

  1) Der Publikations-Vertrag sitzt VOR dem Schreiben: Eine KI-Änderung, die
     die Publish-Schwelle reißt (V1) oder eine harte Verständnis-Regel neu
     einführt (V2), wird verworfen – `heal_article_ai` liefert None.
  2) Fail-closed: Ist der Vertrag nicht verfügbar, wird ebenfalls nichts
     geschrieben (V3) – „nicht gemessen“ ist kein Freispruch.
  3) Die Schwelle ist importiert, nicht kopiert: Wer `NEW_FLESCH_MIN` in
     `readability_check` anhebt, hebt auch das Urteil des Schreibers.
  4) Die gute Heilung bleibt möglich (kein Totstell-Test).
  5) Die Faustregel wird GEWÄHLT, nicht gesetzt (#766): Der deterministische
     Heiler darf nie wieder denselben Satz in den Bestand schreiben –
     `ersetze_generische_faustregel` ersetzt den eingefrorenen Alt-Satz
     einmalig und meldet Stillstand statt Massensatz, wenn der Pool belegt
     ist.
  6) Der Pool selbst erzeugt keinen Befund: Themen/Sätze eindeutig, ohne
     Zahlen, untereinander unter der Audit-Schwelle.

Alles läuft offline in temporären Verzeichnissen; die echten Artikel werden
nicht angefasst.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import readability_check  # noqa: E402
import redaktions_standard as rs  # noqa: E402


FM = ('title: "Stromkosten senken: so gehst du vor"\n'
      'description: "Stromkosten senken: prüfe Verträge und vergleiche Tarife."\n'
      'date: "2026-10-07T06:00:00Z"\n'
      'author: "Frank Hartung"\n')

# Nur RS1 fehlt (keine „Das Wichtigste in Kürze“-Box). RS2/RS3/RS4/RS7 sind
# erfüllt, damit der Test genau die neue Vertragsstufe misst.
BODY_SOLL = (
    "Der Strompreis steigt und viele Haushalte spüren es. Wer den eigenen "
    "Tarif prüft, findet oft eine bessere Option.\n"
    "Der Wechsel ist unkompliziert und lohnt sich meist schon im ersten "
    "Jahr. Vorher hilft ein Blick auf den eigenen Verbrauch.\n\n"
    "## Warum lohnt sich der Wechsel?\n"
    "Ein Vergleich zeigt dir schnell den passenden Tarif. Schon kleine "
    "Unterschiede summieren sich über die Monate.\n"
    "**Faustregel:** Wer jedes Jahr vergleicht, spart meist mehr als beim "
    "ersten Wechsel.\n\n"
    "## Was kostet der Wechsel?\n"
    "Der Wechsel selbst kostet nichts. Der neue Anbieter übernimmt die "
    "Kündigung für dich. So gehst du vor:\n\n"
    "1. Prüfe den eigenen Verbrauch.\n"
    "2. Vergleiche mehrere Tarife.\n"
    "3. Schließe den Wechsel ab.\n")

BOX_OK = (
    "**Das Wichtigste in Kürze**\n\n"
    "- Ein Vergleich der Stromtarife lohnt sich fast immer.\n"
    "- Der Wechsel selbst kostet dich nichts.\n"
    "- Neue Anbieter übernehmen meist die Kündigung.\n\n")

# Gute KI-Antwort: schließt RS1, hält H2-Anzahl und Länge, bleibt leicht.
ANTWORT_OK = BOX_OK + BODY_SOLL

# V1-Sabotage: Box ergänzt, aber lange Schachtelsätze drücken unter Flesch 60.
SCHWER = ("Die vorgenommene Umstrukturierung der Tariflandschaft, die sich "
          "insbesondere durch die Anpassung der Netzentgelte sowie der "
          "CO₂-Bepreisung im Kontext der fortschreitenden Dekarbonisierung "
          "der Energieversorgungssysteme ergibt, erfordert eine grundlegende "
          "Neubewertung der individuellen Vertragskonstellationen, wobei die "
          "Berücksichtigung der jeweiligen Verbrauchsprofile unabdingbar "
          "erscheint.")
ANTWORT_SCHWER = BOX_OK + SCHWER + "\n\n" + BODY_SOLL

# V2-Sabotage: Box ergänzt, aber die gesperrte Intro-Formel neu eingeführt.
ANTWORT_INTRO = BOX_OK + BODY_SOLL.replace(
    "Der Strompreis steigt und viele Haushalte spüren es.",
    "In diesem Beitrag erfährst du alles Wichtige.")


def _artikel(tmpdir):
    pfad = os.path.join(tmpdir, "index.md")
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("---\n" + FM + "---\n" + BODY_SOLL)
    a = rs.load_article(pfad)
    assert a, "Testartikel muss ladbar sein"
    return pfad, a


class VertragImSchreiberTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad, self.a = _artikel(self.tmp.name)
        self.res = rs.analyse_article(self.a)
        # Nur RS1 offen – die Heilung hat genau einen Auftrag.
        self.assertEqual(["RS1"], self.res["hart_missing"])
        env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
        env.start()
        self.addCleanup(env.stop)

    def _heile(self, antwort):
        verworfen = []
        with mock.patch.object(rs, "_call_ai", return_value=antwort):
            neu = rs.heal_article_ai(self.a, self.res, verworfen)
        return neu, verworfen

    def test_gute_heilung_wird_uebernommen(self):
        neu, verworfen = self._heile(ANTWORT_OK)
        self.assertIsNotNone(neu, f"gute KI-Antwort wurde verworfen: {verworfen}")
        self.assertIn("Das Wichtigste in Kürze", neu)
        res2 = rs.analyse_article(dict(self.a, body=neu))
        self.assertEqual([], res2["hart_missing"])
        self.assertEqual([], verworfen)

    def test_flesch_absturz_wird_verworfen(self):
        neu, verworfen = self._heile(ANTWORT_SCHWER)
        self.assertIsNone(neu, "KI-Änderung unter Flesch 60 wurde geschrieben (#607)")
        self.assertTrue(verworfen, "Ablehnung wurde nicht protokolliert")
        self.assertTrue(any("V1" in str(v.get("grund", "")) for v in verworfen),
                        f"V1-Grund fehlt: {verworfen}")

    def test_neue_intro_formel_wird_verworfen(self):
        neu, verworfen = self._heile(ANTWORT_INTRO)
        self.assertIsNone(neu, "neue R7-Formel wurde geschrieben (#607)")
        self.assertTrue(any("R7-INTRO-FORMEL" in str(v.get("grund", ""))
                            for v in verworfen), f"V2-Grund fehlt: {verworfen}")

    def test_fail_closed_ohne_vertrag(self):
        verworfen = []
        with mock.patch.object(rs, "_vertrag_pruefe", None), \
                mock.patch.object(rs, "_VERTRAG_FEHLER", "Importfehler (Test)"), \
                mock.patch.object(rs, "_call_ai", return_value=ANTWORT_OK):
            neu = rs.heal_article_ai(self.a, self.res, verworfen)
        self.assertIsNone(neu, "ohne prüfbaren Vertrag darf nichts geschrieben werden")
        self.assertTrue(any("V3" in str(v.get("grund", "")) for v in verworfen),
                        f"V3-Grund fehlt: {verworfen}")

    def test_schwelle_ist_importiert(self):
        # Hebt die SSOT die Schwelle an, muss dieselbe (importierte) Zahl hier
        # greifen – eine Kopie im Schreiber würde das nicht mitmachen (#585).
        with mock.patch.object(readability_check, "NEW_FLESCH_MIN", 99.0):
            gruende = rs._vertrag_gruende(self.a, ANTWORT_OK)
        self.assertTrue(any(g.startswith("V1") for g in gruende),
                        f"angehobene SSOT-Schwelle greift nicht: {gruende}")

    def test_datei_bleibt_bei_ablehnung_unberuehrt(self):
        with open(self.pfad, encoding="utf-8") as fh:
            vorher = fh.read()
        neu, _ = self._heile(ANTWORT_INTRO)
        self.assertIsNone(neu)
        with open(self.pfad, encoding="utf-8") as fh:
            nachher = fh.read()
        self.assertEqual(vorher, nachher)


class VorfallsmaterialTest(unittest.TestCase):
    """Der echte WF-54C4-Text bleibt als Beweis eingefroren (kein Nachbau)."""

    def test_fixtures_existieren(self):
        sim = os.path.join(BLOG_DIR, "scripts", "tests", "sim", "wf54c4")
        for name in ("vorher.md", "nachher.md"):
            pfad = os.path.join(sim, name)
            self.assertTrue(os.path.exists(pfad), f"Vorfall-Material fehlt: {pfad}")
            self.assertGreater(os.path.getsize(pfad), 5000, pfad)

    def test_echter_vorfall_wird_erkannt(self):
        import publikations_vertrag as pv
        sim = os.path.join(BLOG_DIR, "scripts", "tests", "sim", "wf54c4")
        with open(os.path.join(sim, "vorher.md"), encoding="utf-8") as fh:
            vorher = fh.read()
        with open(os.path.join(sim, "nachher.md"), encoding="utf-8") as fh:
            nachher = fh.read()
        gruende = pv.pruefe("2026-09-10-energie-update", vorher, nachher)
        self.assertTrue(any(g.startswith("V1") for g in gruende),
                        f"Flesch-Absturz des realen Vorfalls fehlt: {gruende}")
        self.assertTrue(any("R7-INTRO-FORMEL" in g for g in gruende),
                        f"R7-Fund des realen Vorfalls fehlt: {gruende}")


class FaustregelDauerheilungTest(unittest.TestCase):
    """#766: Ein Heiler darf nie wieder EINEN Satz in den Bestand schreiben.

    Am 15.10.2026 meldete das Einzigartigkeits-Audit 435 kritische Paare –
    C(30,2): `fix_rs2_rs3_deterministic()` hatte 30 Live-Artikeln denselben
    generischen Heiler-Satz eingesetzt. Diese Tests frieren die Dauerheilung
    ein: Der Satz wird GEWÄHLT (Pool + Bestandsmessung), der Altbestand
    einmalig ersetzt, der Wiederholungsfall schreibt NICHTS.
    """

    def test_pool_ist_gross_eindeutig_und_nummernfrei(self):
        pool = rs.FAUSTREGEL_POOL
        self.assertGreaterEqual(
            len(pool), 40,
            "Pool zu klein für den Bestand – die Heilung endet im Stillstand")
        themen = [thema for thema, _satz, _worte in pool]
        saetze = rs.faustregel_saetze()
        self.assertEqual(len(set(themen)), len(themen), f"Themen doppelt: {themen}")
        self.assertEqual(len(set(saetze)), len(saetze), "Pool-Sätze doppelt")
        for satz in saetze:
            self.assertFalse(any(c.isdigit() for c in satz),
                             f"Zahl im Faustregel-Satz (RS5): {satz}")
        self.assertNotIn(rs.FAUSTREGEL_LEGACY, saetze,
                         "der verbannte Alt-Satz steht wieder im Pool")
        # Kein Paar teilt KRITISCH_AB 7-Gramme – sonst erzeugt der Pool den
        # Befund selbst, den er heilt (eine Messregel, wie im Audit).
        cu = rs._messung()
        for i, a in enumerate(saetze):
            for b in saetze[i + 1:]:
                gemeinsam = len(cu.ngrams(a, cu.PHRASE_LEN)
                                & cu.ngrams(b, cu.PHRASE_LEN))
                self.assertLess(gemeinsam, cu.KRITISCH_AB,
                                f"Pool-Paar über der Audit-Schwelle: {a} / {b}")

    def test_legacy_satz_wird_ersetzt_und_punkt_bleibt_einfach(self):
        body = ("Text davor.\n\n**Faustregel:** " + rs.FAUSTREGEL_LEGACY
                + "\n\n## Fazit\n\nText danach.\n")
        neu, n, meldung = rs.ersetze_generische_faustregel(
            body, slug="test-artikel", titel="Testartikel")
        self.assertEqual(1, n, meldung)
        self.assertNotIn(rs.FAUSTREGEL_LEGACY, neu)
        self.assertIn(rs.FAUSTREGEL_MARKER, neu)
        self.assertNotIn("..", neu, "doppelter Satzpunkt (erster Echtlauf #766)")
        self.assertIn("Text davor.", neu)
        self.assertIn("## Fazit", neu)
        # Idempotent: der zweite Lauf findet den Alt-Satz nicht mehr.
        neu2, n2, meldung2 = rs.ersetze_generische_faustregel(
            neu, slug="test-artikel", titel="Testartikel")
        self.assertEqual(0, n2, meldung2)
        self.assertEqual(neu, neu2)

    def test_zwei_artikel_bekommen_verschiedene_saetze(self):
        kontext = rs.faustregel_kontext({})
        vorrat_vorher = rs.faustregel_vorrat(kontext)
        genommen = []
        for slug in ("artikel-a", "artikel-b", "artikel-c"):
            body = "**Faustregel:** " + rs.FAUSTREGEL_LEGACY + "\n"
            neu, n, meldung = rs.ersetze_generische_faustregel(
                body, slug=slug, kontext=kontext)
            self.assertEqual(1, n, meldung)
            genommen.append(neu.replace(rs.FAUSTREGEL_MARKER, "").strip())
            rs._kontext_aktualisieren(kontext, slug, neu)
        self.assertEqual(len(set(genommen)), len(genommen),
                         f"derselbe Satz mehrfach im Lauf: {genommen}")
        self.assertEqual(vorrat_vorher - len(genommen),
                         rs.faustregel_vorrat(kontext),
                         "Vorrat zählt die vergebenen Sätze nicht")

    def test_satz_aus_dem_bestand_wird_gemieden(self):
        belegt = rs.faustregel_saetze()[0]
        kontext = rs.faustregel_kontext(
            {"fremder-artikel": "**Faustregel:** " + belegt + "\n"})
        body = "**Faustregel:** " + rs.FAUSTREGEL_LEGACY + "\n"
        neu, n, meldung = rs.ersetze_generische_faustregel(
            body, slug="neuer-artikel", kontext=kontext)
        self.assertEqual(1, n, meldung)
        self.assertNotIn(belegt, neu, "Satz aus dem Bestand erneut vergeben")

    def test_leerer_pool_schreibt_nichts(self):
        kontext = {"belegung": set(), "index": {},
                   "vermeiden": set(rs.faustregel_saetze())}
        body = "**Faustregel:** " + rs.FAUSTREGEL_LEGACY + "\n"
        neu, n, meldung = rs.ersetze_generische_faustregel(
            body, slug="x", kontext=kontext)
        self.assertEqual(0, n, "ohne freien Satz darf nichts geschrieben werden")
        self.assertEqual(body, neu, "Text wurde ohne freien Satz verändert")
        self.assertIn("RS3-EINZIGARTIG", meldung)

    def test_eigener_satz_bleibt_unberuehrt(self):
        body = ("**Faustregel:** Wer die Abschläge prüft und den Verbrauch "
                "kennt, zahlt am Jahresende nicht drauf.\n")
        neu, n, _meldung = rs.ersetze_generische_faustregel(body, slug="x")
        self.assertEqual(0, n)
        self.assertEqual(body, neu)

    def test_unmarkierte_erwaehnung_erfuellt_rs3_nicht(self):
        ok, detail = rs.detect_rs3("Die Faustregel steht im Fließtext.\n")
        self.assertFalse(ok)
        self.assertIn("markierte", detail)

    def test_markierte_blockquote_mit_folgezeile_erfuellt_rs3(self):
        body = "> **Faustregel:**\n> Prüfe erst den Bedarf und dann den Tarif.\n"
        self.assertEqual((True, "1 markierte Faustregel(n)"), rs.detect_rs3(body))

    def test_benannte_faustregel_marker_bleiben_kompatibel(self):
        examples = (
            "**Faustregel für deine Sparguthaben:**\nTeile das Risiko passend auf.\n",
            "**Meine Faustregel aus der Praxis:** Miss erst, dann kauf.\n",
        )
        for body in examples:
            with self.subTest(body=body):
                self.assertTrue(rs.detect_rs3(body)[0], body)

    def test_produktionsaufruf_akzeptiert_kontext_und_nur_faustregel(self):
        """Friert die Keywords ein, die der tägliche --fix-Lauf übergibt."""
        context = rs.faustregel_kontext({})
        body = "## Was kostet der Anschluss?\n\nDer Text enthält keine Regel.\n"
        neu, geheilt = rs.fix_rs2_rs3_deterministic(
            body, slug="warmwasser-sparen", kontext=context,
            titel="Warmwasser sparen", nur_rs3=True)
        self.assertEqual(["RS3"], geheilt)
        satz = next(
            line[len(rs.FAUSTREGEL_MARKER):].strip()
            for line in neu.splitlines()
            if line.startswith(rs.FAUSTREGEL_MARKER)
        )
        self.assertIn(satz, rs.faustregel_saetze(),
                      "der Produktionspfad muss nur geprüfte Pool-Sätze schreiben")
        self.assertIn("## Was kostet der Anschluss?", neu,
                      "--nur-faustregel darf RS2 nicht verändern")

    def test_main_produktionslauf_heilt_rs3_und_wahrt_den_publish_vertrag(self):
        """Der echte --fix-Pfad schreibt nur nach bestandenem Vertrag."""
        body = (
            "## Wie nutzt du warmes Wasser?\n\n"
            "Warmes Wasser gehört zum Alltag. Wir nutzen es beim Duschen, "
            "Waschen und Spülen. Der Bedarf ist in jedem Haushalt anders. "
            "Prüfe deinen Verbrauch regelmäßig. Ein Blick auf den Zähler hilft. "
            "Notiere den Stand, wenn du ihn abliest. So erkennst du Änderungen. "
            "Achte auch auf die Dauer der Dusche. Ein kürzeres Bad senkt den "
            "Bedarf. Beim Händewaschen reicht oft wenig Wasser.\n\n"
            "## Welche Spararmatur passt?\n\n"
            "Warmes Wasser gehört zum Alltag. Wir nutzen es beim Duschen, "
            "Waschen und Spülen. Der Bedarf ist in jedem Haushalt anders. "
            "Prüfe deinen Verbrauch regelmäßig. Ein Blick auf den Zähler hilft. "
            "Notiere den Stand, wenn du ihn abliest. So erkennst du Änderungen. "
            "Achte auch auf die Dauer der Dusche. Ein kürzeres Bad senkt den "
            "Bedarf. Beim Händewaschen reicht oft wenig Wasser.\n\n"
            "## Was kannst du prüfen?\n\n"
            "1. Prüfe deinen Verbrauch.\n"
            "2. Achte auf deine Nutzung.\n"
            "3. Wähle eine passende Armatur.\n"
        )
        frontmatter = (
            'title: "Warmwasser sparen"\n'
            'description: "Warmwasser prüfen und passende Spararmaturen wählen."\n'
            'date: "2026-10-16T12:00:00Z"\n'
            'author: "Test"\n'
        )
        with tempfile.TemporaryDirectory(prefix="rs3-production-") as temp_dir:
            article = Path(temp_dir) / "warmwasser-sparen.md"
            article.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
            original_article = rs.load_article(str(article))
            result = subprocess.run(
                [sys.executable, os.path.join(BLOG_DIR, "scripts",
                                              "redaktions_standard.py"),
                 "--fix", "--nur-faustregel", "--file", str(article)],
                cwd=BLOG_DIR, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("Deterministisch geheilt", result.stdout)
            self.assertNotIn("RS3-EINZIGARTIG offen", result.stdout)
            updated = article.read_text(encoding="utf-8")
            self.assertIn(body, updated, "der bestehende Artikeltext muss erhalten bleiben")
            selected = next(
                line[len(rs.FAUSTREGEL_MARKER):].strip()
                for line in updated.splitlines()
                if line.startswith(rs.FAUSTREGEL_MARKER)
            )
            self.assertIn(selected, rs.faustregel_saetze(),
                          "der Produktionspfad darf nur geprüfte Pool-Sätze schreiben")
            updated_body = updated.split("---", 2)[2]
            self.assertFalse(rs._vertrag_gruende(original_article, updated_body))

    def test_themenhinweis_steuert_die_auswahl_ohne_freie_textausgabe(self):
        context = rs.faustregel_kontext({})
        artikel = (
            "Warmwasser sparen: Warmwasserverbrauch und Spararmaturen. "
            "Prüfe den Verbrauch und vergleiche passende Spararmaturen "
            "für deinen Haushalt."
        )
        satz, grund = rs.waehle_faustregel(
            artikel, set(), slug="warmwasser-sparen", kontext=context)
        warmwasser = next(s for thema, s, _keys in rs.FAUSTREGEL_POOL
                          if thema == "warmwasser")
        self.assertEqual(warmwasser, satz,
                         f"spezifischer Warmwasser-Pool-Satz wurde nicht priorisiert: {grund}")
        self.assertIn(satz, rs.faustregel_saetze())

    def test_eingebetteter_selbsttest_bleibt_gruen(self):
        """Der Unit-Lauf soll Strukturdrift der Selbsttest-Fixtures mitfangen."""
        self.assertEqual(0, rs.selftest())


if __name__ == "__main__":
    unittest.main()
