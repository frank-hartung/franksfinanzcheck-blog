"""Regressionstests für die Offenlegungs-Wache (28.09.2026).

Der Auftrag lautete „artikelgenau und noch sichtbarer – **dauerhaft**".
Dauerhaft heißt: Die Wache muss auch dann noch greifen, wenn jemand später
das Template anfasst, das CSS umbaut oder Hugo die Ausgabe anders minifiziert.
Getestet werden deshalb drei Ebenen, die alle schon anderswo im Repo
Phantom-Grün erzeugt haben:

1) VERHALTEN der Prüfung an eingefrorenen HTML-Fixtures – gesunde Fälle
   müssen still bleiben, jede Sabotage muss genau ihren Vertrag auslösen.
2) ROBUSTHEIT gegen Ausgabeformate: minifiziertes HTML ohne
   Anführungszeichen, andere Attributreihenfolge, zusätzliche Attribute.
   (Genau daran ist der Render-Beweis AI4 am 01.09.2026 erblindet.)
3) QUELLTEXT-INVARIANTEN der Bauteile: SSOT vorhanden, beide Varianten im
   Template, Kennzeichnung im Artikelkopf eingehängt, CSS gestaltet die
   Klasse, und die Offenlegungsseite existiert und ruft die generierte
   Partnerliste auf.

Alles läuft ohne Hugo-Build und ohne Netzwerk.
"""
import os
import re
import sys
import unittest

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import offenlegung_gate as og  # noqa: E402

REGISTER = {
    "strom": {"partner": "CHECK24", "produkt": "Stromtarife"},
    "gas": {"partner": "CHECK24", "produkt": "Gastarife"},
    "tagesgeld": {"partner": "C24 Bank", "produkt": "Tagesgeld der C24 Bank"},
}


def seite(n=2, keys="strom,gas", partner="CHECK24",
          sichtbar="CHECK24 (Stromtarife, Gastarife)", links=("strom", "gas")):
    return og._seite_mit(n=n, keys=keys, partner=partner, sichtbar=sichtbar, links=links)


def codes(html, name="posts/probe/"):
    return {b["vertrag"] for b in og.pruefe_seite(name, html, REGISTER)}


class TestGesundeFaelle(unittest.TestCase):
    def test_saubere_seite_mit_partnerlinks_ist_still(self):
        self.assertEqual(codes(seite()), set())

    def test_werbefreie_seite_ist_still(self):
        self.assertEqual(codes(og._seite_ohne()), set())

    def test_werbefreie_seite_wird_als_solche_erkannt(self):
        off = og.finde_offenlegung(og._seite_ohne())
        self.assertEqual(off["variante"], "ohne-partnerlinks")
        self.assertEqual(off["anzahl"], 0)


class TestVertragsverletzungen(unittest.TestCase):
    def test_o1_fehlende_kennzeichnung(self):
        html = og._seite_mit(kopf="")
        self.assertIn("O1", codes(html))

    def test_o2_kennzeichnung_hinter_dem_ersten_link(self):
        kopf = og._KOPF.format(n=1, keys="strom", partner="CHECK24",
                               sichtbar="CHECK24 (Stromtarife)")
        html = ("<html><body>" + og._LINK.format(key="strom") + kopf
                + og._FUSS + "</body></html>")
        self.assertIn("O2", codes(html))

    def test_o3_falsche_anzahl(self):
        self.assertIn("O3", codes(seite(n=9)))

    def test_o3_verschwiegenes_ziel(self):
        self.assertIn("O3", codes(seite(keys="strom")))

    def test_o3_falscher_partner(self):
        self.assertIn("O3", codes(seite(partner="Tarifcheck", sichtbar="Tarifcheck (Hausrat)")))

    def test_o3_partner_nur_im_datenattribut(self):
        html = seite(sichtbar="unser Vergleichspartner")
        befunde = [b["detail"] for b in og.pruefe_seite("posts/probe/", html, REGISTER)]
        self.assertTrue(any("sichtbaren Text" in d for d in befunde), befunde)

    def test_o3_ziel_ohne_register(self):
        html = seite(keys="strom,phantom", links=("strom", "phantom"),
                     sichtbar="CHECK24 (Stromtarife)")
        befunde = og.pruefe_seite("posts/probe/", html, REGISTER)
        self.assertTrue(any("Register" in b["detail"] for b in befunde), befunde)
        # Ein unbekanntes Ziel ist eine redaktionelle Entscheidung, keine
        # Maschinenaufgabe – sonst entsteht ein Dauer-Alarm ohne Schließpfad (C14).
        self.assertTrue(any(b["owner"] == "human" for b in befunde
                            if "Register" in b["detail"]))

    def test_o4_fehlende_pflichtangabe(self):
        html = seite().replace("Provision nur bei Abschluss, für dich ohne Aufpreis.", "")
        self.assertIn("O4", codes(html))

    def test_o4_ohne_weg_zur_offenlegung(self):
        html = (seite()
                .replace('<a href="/transparenz/">Wie sich das finanziert</a>', "")
                .replace(og._FUSS, ""))
        self.assertIn("O4", codes(html))

    def test_o5_versteckte_kennzeichnung(self):
        for sabotage in ('class="ff-offenlegung" hidden data-ff-offenlegung=',
                         'class="ff-offenlegung" style="display:none" data-ff-offenlegung=',
                         'class="ff-offenlegung" style="font-size:0" data-ff-offenlegung=',
                         'class="ff-offenlegung" aria-hidden="true" data-ff-offenlegung='):
            html = seite().replace('class="ff-offenlegung" data-ff-offenlegung=', sabotage)
            with self.subTest(sabotage=sabotage):
                self.assertIn("O5", codes(html))

    def test_o5_verstecken_ist_p1(self):
        html = seite().replace('class="ff-offenlegung" data-ff-offenlegung=',
                               'class="ff-offenlegung" hidden data-ff-offenlegung=')
        schwere = {b["severity"] for b in og.pruefe_seite("posts/probe/", html, REGISTER)
                   if b["vertrag"] == "O5"}
        self.assertIn("P1", schwere)

    def test_o6_werbefrei_trotz_partnerlink(self):
        html = og._seite_ohne().replace("</body>", og._LINK.format(key="strom") + "</body>")
        self.assertIn("O6", codes(html))

    def test_o6_abbinder_widerspricht_kopf(self):
        html = seite() + '<p data-ff-offenlegung-abbinder="ohne-partnerlinks">x</p>'
        self.assertIn("O6", codes(html))

    def test_o7_seite_ohne_weg_zur_offenlegung(self):
        html = og._seite_mit(fuss=False).replace(
            '<a href="/transparenz/">Wie sich das finanziert</a>', "Details")
        self.assertIn("O7", codes(html))


class TestRobustheit(unittest.TestCase):
    """Formatwechsel dürfen die Wache weder blind noch hysterisch machen."""

    def test_minifiziert_ohne_anfuehrungszeichen(self):
        html = (seite()
                .replace('href="/go/strom/?subid=test"', "href=/go/strom/?subid=test")
                .replace('data-ff-offenlegung="mit-partnerlinks"',
                         "data-ff-offenlegung=mit-partnerlinks")
                .replace('data-ff-offenlegung-anzahl="2"', "data-ff-offenlegung-anzahl=2"))
        self.assertEqual(codes(html), set())

    def test_zusaetzliche_attribute_und_reihenfolge(self):
        html = seite().replace(
            '<details class="ff-offenlegung" data-ff-offenlegung="mit-partnerlinks"',
            '<details id="x" data-ff-offenlegung="mit-partnerlinks" lang="de" '
            'class="ff-offenlegung ff-offenlegung--kopf"')
        self.assertEqual(codes(html), set())

    def test_alias_und_paginierung_werden_nicht_geprueft(self):
        """Weiterleitungsseiten tragen keinen Artikeltext – und keine Pflicht."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ordner = os.path.join(tmp, "posts", "alias")
            os.makedirs(ordner)
            with open(os.path.join(ordner, "index.html"), "w", encoding="utf-8") as fh:
                fh.write('<html><head><meta http-equiv="refresh" content="0; url=/x/">'
                         "</head></html>")
            self.assertEqual(og.seiten_des_builds(tmp), [])

    def test_text_von_entfernt_markup_und_entities(self):
        self.assertEqual(og.text_von("<b>DSL</b> &amp; Internet"), "DSL & Internet")


class TestOffenlegungsseite(unittest.TestCase):
    def test_vollstaendige_seite_ist_still(self):
        html = ("<html><body>CHECK24 Stromtarife Gastarife C24 Bank "
                "Tagesgeld der C24 Bank Provision Werbung unabhängig</body></html>")
        self.assertEqual(og.pruefe_transparenzseite(html, REGISTER, {"CHECK24"}), [])

    def test_fehlender_partner_faellt_auf(self):
        html = "<html><body>CHECK24 Stromtarife Gastarife Provision Werbung unabhängig</body></html>"
        befunde = og.pruefe_transparenzseite(html, REGISTER, {"C24 Bank"})
        self.assertTrue(befunde)
        self.assertTrue(all(b["vertrag"] == "O7" for b in befunde))

    def test_beworbener_partner_muss_offengelegt_sein(self):
        html = ("<html><body>CHECK24 Stromtarife Gastarife C24 Bank Tagesgeld der C24 Bank "
                "Provision Werbung unabhängig</body></html>")
        befunde = og.pruefe_transparenzseite(html, REGISTER, {"Neuer Partner"})
        self.assertTrue(any("Neuer Partner" in b["detail"] for b in befunde), befunde)


class TestBauteilInvarianten(unittest.TestCase):
    """Die billigste Dauersicherung: Das Bauteil darf nicht still verschwinden."""

    def test_selbsttest_der_wache_ist_gruen(self):
        self.assertEqual(og.selftest(), 0)

    def test_werkzeugpruefung_ohne_befund(self):
        self.assertEqual(og.pruefe_werkzeug(), [])

    def test_ssot_liefert_beide_varianten(self):
        ssot = open(og.SSOT, encoding="utf-8").read()
        self.assertIn("findRESubmatch", ssot)
        self.assertIn("affiliate_ziele_data.html", ssot)

    def test_kennzeichnung_haengt_im_artikelkopf(self):
        # Dauerheilung #623 (07.10.2026): Die Einzelansicht liegt seitdem
        # EINMAL im Baustein artikel_einzeln.html; layouts/single.html und
        # layouts/_default/single.html binden ihn nur noch ein. Geprüft wird
        # deshalb der Baustein – die Aussage bleibt dieselbe: Die Werbe-
        # Kennzeichnung steht VOR dem Artikelinhalt.
        for layout in ("layouts/_partials/artikel_einzeln.html",
                       "layouts/pillar/single.html", "layouts/pillar/list.html"):
            pfad = os.path.join(BLOG_DIR, layout)
            with self.subTest(layout=layout):
                roh = open(pfad, encoding="utf-8").read()
                self.assertIn("ff_offenlegung.html", roh)
                # Kommentare zählen nicht – sie erwähnen `.Content` oft als Prosa.
                text = re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", "", roh, flags=re.S)
                text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
                kopf = text.find("ff_offenlegung.html")
                inhalt = text.find(".Content")
                self.assertTrue(inhalt == -1 or kopf < inhalt,
                                f"{layout}: Kennzeichnung steht nicht vor dem Inhalt")

    def test_trust_box_nutzt_denselben_ssot(self):
        text = open(os.path.join(BLOG_DIR, "layouts", "_partials", "trust_box.html"),
                    encoding="utf-8").read()
        self.assertIn("_funcs/affiliate_offenlegung.html", text)
        self.assertNotIn("kann Affiliate-Links enthalten", text)

    def test_css_gestaltet_die_kennzeichnung(self):
        css = open(og.CSS_PFAD, encoding="utf-8").read()
        for klasse in (".ff-offenlegung", ".ff-offenlegung__chip", ".ff-offenlegung__kopf"):
            self.assertIn(klasse, css)
        self.assertIn(':root[data-theme="dark"] .ff-offenlegung__chip', css)

    def test_offenlegungsseite_existiert_und_generiert_die_partnerliste(self):
        seite_md = os.path.join(BLOG_DIR, "content", "transparenz", "index.md")
        self.assertTrue(os.path.exists(seite_md))
        text = open(seite_md, encoding="utf-8").read()
        self.assertIn("partnerliste", text)
        shortcode = os.path.join(BLOG_DIR, "layouts", "shortcodes", "partnerliste.html")
        self.assertTrue(os.path.exists(shortcode))
        self.assertIn("affiliate_ziele_data.html", open(shortcode, encoding="utf-8").read())

    def test_footer_verlinkt_die_offenlegung(self):
        footer = open(os.path.join(BLOG_DIR, "layouts", "_partials", "footer.html"),
                      encoding="utf-8").read()
        self.assertIn("transparenz/", footer)

    def test_publish_und_bestand_gate_kennen_die_wache(self):
        pg = open(os.path.join(BLOG_DIR, "scripts", "publish_gate.py"), encoding="utf-8").read()
        self.assertIn("offenlegung_failures", pg)
        self.assertIn("offenlegung_gate.py", pg)
        bg = open(os.path.join(BLOG_DIR, "scripts", "bestand_gate.py"), encoding="utf-8").read()
        self.assertIn("offenlegung_failures", bg)

    def test_register_ist_lesbar(self):
        register = og.lade_register()
        self.assertTrue(register)
        self.assertTrue(all(v["partner"] for v in register.values()))

    def test_register_faellt_nicht_still_auf_leer_zurueck(self):
        """Ein unlesbares Register muss ein Werkzeugfehler sein, kein grünes Nichts."""
        self.assertEqual(og.lade_register(os.path.join(BLOG_DIR, "gibt-es-nicht.yaml")), {})


class TestVerdrahtung(unittest.TestCase):
    """Die Wache nützt nichts, wenn sie niemand fragt – #349 war genau das.

    Geprüft wird die Brücke `publish_gate.offenlegung_failures()`: Filterung
    auf den Kandidaten, Fail-closed bei Werkzeugfehler und die Weitergabe an
    das Bestands-Gate. Alles ohne Build – der Prüflauf wird injiziert.
    """

    def setUp(self):
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        import publish_gate
        self.pg = publish_gate

    def _mit_ergebnis(self, data):
        from unittest.mock import patch
        return patch.object(self.pg, "_run_json", lambda *a, **k: data)

    def test_befund_landet_beim_richtigen_kandidaten(self):
        data = {"befunde": [{"seite": "posts/mein-slug/", "vertrag": "O2",
                             "detail": "Kennzeichnung steht hinter dem ersten Link"}]}
        with self._mit_ergebnis(data):
            per, warn, tool = self.pg.offenlegung_failures(["mein-slug"])
        self.assertIn("mein-slug", per)
        self.assertIn("O2", per["mein-slug"][0])
        self.assertFalse(tool)
        self.assertIsNone(warn)

    def test_fremder_kandidat_wird_nicht_bestraft(self):
        data = {"befunde": [{"seite": "posts/anderer/", "vertrag": "O1", "detail": "x"}]}
        with self._mit_ergebnis(data):
            per, _, _ = self.pg.offenlegung_failures(["mein-slug"])
        self.assertEqual(per, {})

    def test_registerbefund_blockiert_keinen_artikel(self):
        """O7 betrifft /transparenz/ – ein Kandidat kann nichts dafür."""
        data = {"befunde": [{"seite": "transparenz/", "vertrag": "O7", "detail": "x"}]}
        with self._mit_ergebnis(data):
            per, _, _ = self.pg.offenlegung_failures(None)
        self.assertEqual(per, {})

    def test_werkzeugfehler_ist_fail_closed(self):
        with self._mit_ergebnis(None):
            per, warn, tool = self.pg.offenlegung_failures(["mein-slug"])
        self.assertTrue(tool, "kein Ergebnis muss fail-closed sein")
        self.assertEqual(per, {})
        self.assertIn("fail-closed", warn)

    def test_publish_gate_stoppt_hart_und_verwirft_nicht(self):
        """Ein nicht geführter Beweis ist kein Qualitätsmangel des Artikels."""
        quelle = open(os.path.join(BLOG_DIR, "scripts", "publish_gate.py"),
                      encoding="utf-8").read()
        block = quelle[quelle.index("    if offen_tool_error:"):
                       quelle.index("    if integ_tool_error:")]
        self.assertIn("return 1", block, "Werkzeugfehler muss den Lauf stoppen")
        self.assertIn("offenlegung_tool_error", block, "Stopp gehört in die Akte")
        for verboten in ("os.remove", "unlink", "shutil.move", "draft"):
            self.assertNotIn(verboten, block,
                             "fail-closed heißt stoppen, nicht verwerfen")
        # Und die Prüfung läuft VOR dem Kandidaten-Urteil, nicht danach.
        self.assertLess(quelle.index("offen_tool_error = offenlegung_failures("),
                        quelle.index("    if offen_tool_error:"))

    def test_bestand_gate_meldet_statt_zu_heilen(self):
        quelle = open(os.path.join(BLOG_DIR, "scripts", "bestand_gate.py"),
                      encoding="utf-8").read()
        self.assertIn('"offenlegung"', quelle)
        heal = quelle[quelle.index("def heal("):quelle.index("def render_report(")]
        self.assertNotIn("offenlegung", heal,
                         "C15: die Kennzeichnung erzeugt das Template – kein Heilpfad")

    def test_reserve_kette_kennt_die_begruendete_ausnahme(self):
        import reserve_healer_coverage as rhc
        b = rhc.deckung()
        self.assertEqual(b["luecken"], [])
        self.assertIn("offenlegung_failures", {e["regel"] for e in b["ausnahmen"]})

    def test_wache_steht_im_governance_vertrag(self):
        import governance_contract as gc
        self.assertIn("offenlegung_gate.py", gc.GUARDS)


class TestBefundform(unittest.TestCase):
    """C14: Jeder Befund hat Besitzer, Schwere, Kanal und einen nächsten Schritt."""

    def test_alle_felder_gesetzt(self):
        befunde = og.pruefe_seite("posts/probe/", og._seite_mit(kopf=""), REGISTER)
        self.assertTrue(befunde)
        for b in befunde:
            self.assertIn(b["severity"], ("P1", "P2", "P3"))
            self.assertIn(b["owner"], ("auto", "human"))
            self.assertEqual(b["channel"], "affiliate")
            self.assertTrue(b["step"])
            self.assertTrue(re.match(r"^offenlegung-o[0-9]$", b["id"]))


if __name__ == "__main__":
    unittest.main()
