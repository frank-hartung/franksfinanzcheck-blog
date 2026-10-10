#!/usr/bin/env python3
"""Vertragstests für scripts/duplikat_guard.py – Haus-Templates (Issue #676).

WARUM DIESE DATEI EXISTIERT
---------------------------
Am 09.10.2026 lieferte der neueste Artikel HTTP 404, obwohl er
veröffentlichungsreif im Repo lag. Ursache war nicht der Deploy, sondern ein
Widerspruch zwischen zwei Wachen:

  · `affiliate_intent_contract.py` schreibt den CTA-Wortlaut je Route
    verbindlich vor („Jetzt das Tagesgeld-Angebot der C24 Bank ansehen") –
    die Intent-Wache und die Affiliate-Integritäts-Wache PRÜFEN ihn.
  · `duplikat_guard.py` maß denselben Wortlaut über Artikel hinweg und
    meldete D3-X „Absatz wortgleich in 2 Artikeln".

RD1-duplikate ist in der Release-Scorecard blockierend, Cross-Artikel-Funde
werden nie auto-gefixed – der Deploy starb 13× in Folge und fror die
komplette öffentliche Auslieferung ein.

Der wichtigste Test hier ist `test_cta_vertrag_und_duplikatwache_einig`:
Er erzeugt den End-CTA für JEDE registrierte Route aus der SSOT selbst und
verlangt, dass die Duplikat-Wache ihn als Haus-Template erkennt. Damit kann
der Widerspruch nicht zurückkehren – auch nicht für einen Partner, den es
heute noch gar nicht gibt.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duplikat_guard as dg


# Originalbefund #676 – wortgleich in
#   content/posts/2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit
#   content/posts/2026-10-07-etf-sparplan-starten-schritt-fuer-schritt-…
CTA_676 = ("👉 **Jetzt das Tagesgeld-Angebot der C24 Bank ansehen:** "
           "[**→ Jetzt C24 Bank Tagesgeld ansehen**](/go/tagesgeld/)")

REDAKTION = ("Der Gaspreis je Kilowattstunde liegt aktuell etwa bei neun Cent, "
             "und wer früh vergleicht, sichert sich den günstigeren Tarif für "
             "ein ganzes Jahr im Voraus und spart damit deutlich mehr als mit "
             "einer verspäteten Entscheidung im Herbst.")


class HausTemplateTests(unittest.TestCase):
    """Die Ausnahme muss aus der SSOT kommen – und begründet sein."""

    def test_vertrags_cta_ist_haus_template(self):
        self.assertTrue(dg.is_boilerplate(CTA_676))

    def test_ausnahme_nennt_die_ssot(self):
        """Eine stille Ausnahme ist ein Scheingrün (Lektion #521, C19)."""
        grund = dg.haus_template_grund(CTA_676)
        self.assertIn("affiliate_intent_contract", grund)

    def test_register_wird_abgeleitet_nicht_abgeschrieben(self):
        """Der Registerinhalt muss aus dem Vertragsmodul kommen."""
        register = dg.haus_cta_register()
        self.assertGreater(len(register), 20)
        vereinigt = " ".join(register)
        self.assertIn("tagesgeld", vereinigt)
        # Der Satz der Route, die #676 ausgelöst hat, muss enthalten sein.
        self.assertTrue(any("tagesgeld-angebot der c24 bank" in b
                            for b in register))

    def test_neue_route_waere_automatisch_erfasst(self):
        """Probe: Ein erfundenes Vertragsziel wird ohne Codeänderung erkannt.

        Genau das fehlte der Whitelist – jede neue CTA-Variante machte den
        vertragstreuesten Block zum Plagiat, bis jemand die Liste nachzog."""
        import affiliate_intent_contract as aic

        original = dict(aic.ZIELE)
        try:
            ziel = aic.Ziel(
                key="probe-route-676", partner="Probe", produkt="Probeangebot",
                anzeige="Probe", gateway="Probe", landing="probe",
                saetze={"end": "Jetzt das Probeangebot der Probebank ansehen"},
                anker={"end": ("→ Jetzt Probeangebot ansehen",)})
            aic.ZIELE = dict(original, **{"probe-route-676": ziel})
            dg._HAUS_CTA_REGISTER = None          # Cache verwerfen
            block = ("👉 **Jetzt das Probeangebot der Probebank ansehen:** "
                     "[**→ Jetzt Probeangebot ansehen**](/go/probe-route-676/)")
            self.assertTrue(dg.is_boilerplate(block))
        finally:
            aic.ZIELE = original
            dg._HAUS_CTA_REGISTER = None

    def test_cta_ohne_go_link_ist_kein_haus_template(self):
        """Ohne internes Gateway ist der Block kein CTA, sondern Inhalt."""
        text = ("Jetzt das Tagesgeld-Angebot der C24 Bank ansehen: Jetzt C24 "
                "Bank Tagesgeld ansehen und dabei genau prüfen, welche "
                "Bedingungen gelten und wie lange die Zinsbindung läuft.")
        self.assertFalse(dg.ist_haus_cta(text))

    def test_redaktionssatz_hebt_die_ausnahme_auf(self):
        """Kein Freibrief: eigener Inhalt neben der CTA wird wieder gemessen."""
        erweitert = (CTA_676 + " Beachte aber, dass eine lange Zinsbindung "
                     "deiner Anlagestrategie widersprechen kann, wenn du "
                     "kurzfristig Liquidität brauchst und deshalb einen "
                     "Vergleich der Angebote lieber verschieben möchtest.")
        self.assertFalse(dg.is_boilerplate(erweitert))

    def test_redaktioneller_absatz_bleibt_gemessen(self):
        self.assertFalse(dg.is_boilerplate(REDAKTION))
        self.assertEqual(dg.haus_template_grund(REDAKTION), "")


class UnicodeUndFormelTests(unittest.TestCase):
    """Zwei weitere Klassen, die vor #676 als Duplikat galten."""

    def test_weicher_bindestrich_in_der_offenlegung(self):
        """U+2011 statt '-': gegen lower() traf das Muster nie."""
        text = ("***Transparenz:** Dieser Artikel enthält Affiliate\u2011Links "
                "(Werbung). Beim Abschluss über einen Link erhalten wir eine "
                "Provision – für dich entstehen keine Mehrkosten.*")
        self.assertTrue(dg.is_boilerplate(text))

    def test_vergleichsform_normalisiert_unicode(self):
        self.assertEqual(dg._vergleichsform("Affiliate\u2011Links"),
                         dg._vergleichsform("Affiliate-Links"))

    def test_rechtlicher_hinweis_ist_haus_text(self):
        text = ("_Wichtiger Hinweis: Dieser Artikel dient ausschließlich der "
                "allgemeinen Information und stellt keine Anlage-, Rechts- "
                "oder Steuerberatung dar. Prüfe Konditionen und Bedingungen "
                "immer beim jeweiligen Anbieter._")
        self.assertTrue(dg.is_boilerplate(text))
        self.assertIn("ki_shared.DISCLAIMER", dg.haus_template_grund(text))

    def test_news_dateline_mit_platzhalter(self):
        """Dasselbe Format, anderes Datum – kein Fast-Duplikat."""
        for datum in ("06.10.2026", "08.10.2026", "01.01.2027"):
            text = (f"**Stand: {datum}.** Dieser News\u2011Kompakt\u2011Artikel "
                    "ordnet eine aktuelle Entwicklung ein. Konditionen und "
                    "Regeln können sich ändern – prüfe Details immer beim "
                    "jeweiligen Anbieter.")
            self.assertTrue(dg.is_boilerplate(text), datum)

    def test_dateline_mit_eigenem_text_bleibt_gemessen(self):
        text = ("**Stand: 06.10.2026.** Dieser News-Kompakt-Artikel ordnet "
                "eine aktuelle Entwicklung ein, die vor allem Haushalte mit "
                "Wärmepumpe betrifft, weil der Netzbetreiber die "
                "Einspeisevergütung gesenkt hat und deshalb viele Verträge "
                "neu gerechnet werden müssen, bevor sich ein Wechsel lohnt.")
        self.assertFalse(dg.is_boilerplate(text))

    def test_formel_wird_aus_der_ssot_gelesen(self):
        """Die Dateline steht als Konstante im erzeugenden Modul.

        Bewusst ohne `import news_writer`: Das Modul zieht PyYAML nach. Die
        Ableitung liest die Konstante per AST – genau das ist der Punkt der
        Reparatur (#676: in pyyaml-freier Umgebung fiel die Ausnahme still
        aus und die Wache maß das Format wieder als Plagiat)."""
        wert, luecke = dg._ssot_wert("news_writer", "STAND_INTRO")
        self.assertEqual(luecke, "")
        self.assertIn("{today}", wert or "")
        self.assertIn("news_writer.STAND_INTRO",
                      [q for q, _ in dg.haus_formeln()])

    def test_ssot_luecken_werden_laut_gemeldet(self):
        """Eine verschobene Konstante ist eine Lücke, kein stiller Verzicht."""
        self.assertEqual(dg.haus_template_luecken(), [])
        _wert, grund = dg._ssot_wert("news_writer", "STAND_INTRO_GIBT_ES_NICHT")
        self.assertTrue(grund)


class MessungTests(unittest.TestCase):
    """Die Ausnahme darf die Wache nicht blind machen."""

    def _artikel(self, verzeichnis: Path, slug: str, body: str) -> Path:
        pfad = verzeichnis / slug / "index.md"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text('---\ntitle: "Probe"\ndraft: false\n---\n\n' + body,
                        encoding="utf-8")
        return pfad

    def test_exaktes_cross_artikel_duplikat_wird_weiter_erkannt(self):
        """D3-X bleibt scharf: echter Inhalt in zwei Artikeln ist ein Fund."""
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            pfade = [self._artikel(basis, "a", REDAKTION),
                     self._artikel(basis, "b", REDAKTION)]
            funde = dg.check_cross(pfade, root=basis)
            regeln = [f[1] for f in funde]
            self.assertIn("D3-X", regeln)

    def test_haus_cta_in_zwei_artikeln_ist_kein_fund(self):
        """Genau die Klasse #676: derselbe Vertrags-CTA, kein D3-X."""
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            pfade = [self._artikel(basis, "a", REDAKTION + "\n\n" + CTA_676),
                     self._artikel(basis, "b", REDAKTION.replace("Gaspreis", "Strompreis")
                                   .replace("neun Cent", "acht Cent") + "\n\n" + CTA_676)]
            funde = dg.check_cross(pfade, root=basis)
            self.assertEqual([f[1] for f in funde], [],
                             f"Haus-CTA wurde wieder gemessen: {funde}")

    def test_duplikat_im_artikel_wird_weiter_gefixt(self):
        """D1 bleibt heilbar – die Ausnahme gilt nur für Haus-Templates."""
        body = REDAKTION + "\n\n" + REDAKTION
        _out, entfernt, _details = dg.auto_fix("probe", body)
        self.assertEqual(entfernt, 1)

    def test_selftest_des_moduls_ist_gruen(self):
        """14 eingefrorene Fälle inkl. der #676-Klasse und der SSOT-Lesart."""
        self.assertEqual(dg.run_selftest(), [])


class CtaVertragTests(unittest.TestCase):
    """DER Dauertest: beide Wachen müssen denselben Wortlaut meinen.

    Zwei Stufen, damit der Beweis in JEDEM Pfad läuft (#676):
      1. `VertragsCtaTests` baut die CTA-Sätze direkt aus der Vertrags-SSOT
         (`affiliate_intent_contract`) – ohne PyYAML, läuft immer, auch im
         PR-Gate und im C6-Selbsttest-Pfad.
      2. `CtaVertragTests` lässt den echten `cta_builder` den Block bauen
         (Satz + Gateway-Anker + Werbe-Offenlegung) – braucht PyYAML und
         wird sonst mit Grund übersprungen, nie still ausgelassen."""

    def test_cta_vertrag_und_duplikatwache_einig(self):
        """Jede registrierte Route: ihr End-CTA ist ein Haus-Template.

        Ohne diesen Test kann der Widerspruch aus #676 jederzeit
        zurückkehren – ein neuer Partner in der SSOT wäre für die
        Duplikat-Messung unsichtbar und würde den nächsten Deploy
        einfrieren."""
        cta_builder = _lade_cta_builder()
        if cta_builder is None:
            self.skipTest("cta_builder braucht PyYAML (siehe VertragsCtaTests)")

        import affiliate_intent_contract as aic

        pruefende = []
        for key in sorted(aic.ZIELE):
            for slug in ("artikel-eins", "artikel-zwei", "probe-676"):
                block = cta_builder.cta_end_block(route=key, slug=slug)
                pruefende.append((key, slug, block))
        self.assertGreater(len(pruefende), 30)

        falsch = []
        for key, slug, block in pruefende:
            for absatz in [b for b in block.split("\n\n") if b.strip()]:
                # Die Trennlinie selbst ist kein Block (unter MIN_EXACT).
                if absatz.strip() == "---":
                    continue
                if not dg.is_boilerplate(absatz):
                    falsch.append(f"{key}/{slug}: {absatz[:70]}")
        self.assertEqual(falsch, [],
                         "Vertrags-CTAs, die die Duplikat-Wache als Inhalt "
                         "misst (Klasse #676):\n" + "\n".join(falsch[:10]))

    def test_jeder_cta_block_traegt_ein_go_gateway(self):
        """Die Ausnahme greift nur mit internem Gateway – Beweis je Route."""
        cta_builder = _lade_cta_builder()
        if cta_builder is None:
            self.skipTest("cta_builder braucht PyYAML (siehe VertragsCtaTests)")

        import affiliate_intent_contract as aic

        for key in sorted(aic.ZIELE):
            block = cta_builder.cta_end_block(route=key, slug="probe")
            self.assertIn("/go/", block, key)
            self.assertNotIn("http", block, key)


def _lade_cta_builder():
    """`cta_builder` nur liefern, wenn seine Abhängigkeiten vorhanden sind."""
    try:
        import cta_builder
    except ModuleNotFoundError:
        return None
    return cta_builder


class VertragsCtaTests(unittest.TestCase):
    """Abhängigkeitsfreier Kernbeweis der CTA-Einigkeit (#676).

    `affiliate_intent_contract` importiert ohne PyYAML. Wer also eine neue
    Route in die SSOT legt, sieht den Widerspruch hier sofort – auch in
    einem PR-Gate, das die schweren Abhängigkeiten gar nicht installiert."""

    def setUp(self):
        import affiliate_intent_contract as aic

        self.aic = aic

    def test_jede_route_liefert_register_satz_und_anker(self):
        """Jeder Anker kommt aus der SSOT; ein leerer Satz ist gedeckt.

        `CTA_SAETZE_DEFAULT['end']` ist bewusst leer: Ohne Abweichung baut
        `cta_builder` den End-Satz aus `_END_SATZ_FALLBACK`. Diese Kette muss
        geschlossen sein, sonst entsteht an genau dieser Stelle ein Haus-
        Text, den die Wache nicht kennt (#676 in neuem Gewand). Der Fallback
        wird per AST gelesen – ohne PyYAML, wie die Wache selbst."""
        fallback, luecke = dg._ssot_wert("cta_builder", "_END_SATZ_FALLBACK")
        self.assertEqual(luecke, "")
        self.assertTrue(fallback.strip(), "End-Satz-Fallback fehlt")
        self.assertTrue(dg.is_boilerplate(fallback),
                        "Der End-Satz-Fallback des Builders ist kein "
                        "Haus-Text – CTA-Blöcke würden wieder als Inhalt "
                        "gemessen (Klasse #676)")
        self.assertTrue(any(dg.is_boilerplate(form)
                            for _quelle, form in dg.haus_texte()),
                        "Kein abgeleiteter Haus-Text ist messbar")
        # Das `/go/`-Gateway setzt der Builder als Markdown-Link; die SSOT
        # liefert den reinen Ankertext. Fremdlink wäre ein Vertragsbruch.
        for key in sorted(self.aic.ZIELE):
            _satz, anker = self.aic.cta_bausteine(key, "end", "probe-676")
            self.assertTrue(anker.strip(), key)
            self.assertNotIn("http", anker, key)

    def test_vertrags_cta_aus_der_ssot_ist_haus_template(self):
        """Jede Route: ihre End-CTA-ZEILE ist ein Haus-Template.

        Geprüft wird die Bauform, die tatsächlich im Artikel steht
        (`👉 **Satz:** [**Anker**](/go/route/)`) – nicht der nackte Anker.
        Ein nackter Anker liegt unter MIN_EXACT und wird gar nicht gemessen;
        ihn zu prüfen, wäre eine Schein-Aussage."""
        falsch, geprueft = [], 0
        for key in sorted(self.aic.ZIELE):
            for slug in ("artikel-eins", "probe-676"):
                satz, anker = self.aic.cta_bausteine(key, "end", slug)
                zeile = f"👉 **{satz}:** [**{anker}**](/go/{key}/)"
                geprueft += 1
                if not dg.is_boilerplate(zeile):
                    falsch.append(f"{key}/{slug}: {zeile[:70]}")
        self.assertGreater(geprueft, 30, "zu wenige Vertragstexte geprüft")
        self.assertEqual(falsch, [],
                         "Vertrags-CTAs, die als Inhalt gemessen werden "
                         "(Klasse #676):\n" + "\n".join(falsch[:10]))

    def test_register_kennt_jeden_baustein_der_ssot(self):
        """Das Register ist die Brücke zwischen Vertrag und Messung."""
        register = dg.haus_cta_register()
        self.assertGreater(len(register), 20)
        fehlende = []
        for key in sorted(self.aic.ZIELE):
            satz, anker = self.aic.cta_bausteine(key, "end", "probe-676")
            for teil in (dg.normalize(satz), dg.normalize(anker)):
                if len(teil) >= dg.MIN_EXACT and teil not in register:
                    fehlende.append(f"{key}: {teil[:60]}")
        self.assertEqual(fehlende, [], "Registerlücken:\n" + "\n".join(fehlende))


if __name__ == "__main__":
    unittest.main()

    # Der Dauerkraft-Beweis „neue Route, die es heute nicht gibt" lebt in
    # `HausTemplateTests.test_neue_route_waere_automatisch_erfasst` – dort
    # mit der echten `Ziel`-Signatur (saetze/anker je Slot).


if __name__ == "__main__":
    unittest.main()
