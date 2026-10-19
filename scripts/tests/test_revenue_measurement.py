#!/usr/bin/env python3
"""Regressionstest: die Umsatz-Messkette (19.09.2026, quellenehrlich seit 19.10.2026).

Fünf Rückschritte sind hier dauerhaft verankert – jeder einzelne hat schon
einmal Daten UNsinn erzeugt oder Lücken unsichtbar gemacht:

  1. Null vs. „unbekannt\": Eine nicht gemessene Quelle darf NIE als 0
     erscheinen – sonst optimiert die Redaktion gegen eine Geisterzahl.
  2. Klicks je Seite: Provision ist nicht je Seite messbar (die Abrechnung
     kennt nur Monatssummen) – sie darf keiner Seite zugeschrieben werden.
  3. Report-Protokoll: Der Governance-Gate klassifiziert über die
     Befund-Zeilen `| AMBER | funnel_gap | … |` und die Zeile
     `Messlücken: N`. Ändert jemand das Format, stirbt die Eskalation
     still – hier beißt der Test sofort.
  4. Betriebsgrenze statt Lücke: Ein bewusst ausgeschalteter Weg (Klickzähler
     `aktiv: false`, Provisions-Tabelle noch nie befüllt) ist INFO und hält die
     Ampel grün; eine Quelle, die laufen SOLL und nicht liefert, ist eine Lücke.
  5. Verdrahtung: Mess-Schritte MÜSSEN im Gate (STEPS), im Vertrag
     (MEASURE_STEPS + Signaturen) und vor der Scorecard laufen.

Dazu: CTA-Messvertrag (Event/Slug/SubID/Placement) und Gateway-Drift als
direkte Aufrufe – dieselben Fälle wie im --selftest, aber als dauerhafter
CI-Test über `python3 -m unittest discover -s scripts/tests`.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


rf = _load("revenue_funnel", os.path.join(SCRIPTS, "revenue_funnel.py"))
cc = _load("click_chain_guard", os.path.join(SCRIPTS, "click_chain_guard.py"))
gg = _load("governance_gate", os.path.join(SCRIPTS, "governance_gate.py"))
gc = _load("governance_contract", os.path.join(SCRIPTS, "governance_contract.py"))

MEIN_GUTES_SETUP = {"clicks": True}


class TestNullVsUnbekannt(unittest.TestCase):
    """Hausregel: nicht gemessen ⇒ unbekannt (None), NIE eine 0."""

    def test_alle_quellen_fehlen_ist_nichts_null(self):
        f = rf.compute([], set(), measured={"clicks": False})
        self.assertIsNone(f["affiliate_klicks"])
        self.assertIsNone(f["transaktionen"]["antraege"])
        self.assertIsNone(f["provision"]["gesamt"])
        for k, v in f["raten"].items():
            self.assertIsNone(v, f"Rate {k} trotz ungemessener Quelle nicht None")

    def test_gemessen_und_leer_ist_echte_null(self):
        f = rf.compute([], set(), measured=MEIN_GUTES_SETUP)
        self.assertEqual(f["affiliate_klicks"], 0)          # gemessen, wirklich 0
        # Ohne Provisions-Tabelle gibt es keine Anträge – unbekannt, nicht 0.
        self.assertIsNone(f["transaktionen"]["antraege"])
        # Provision ohne Wert im Dokument bleibt unbekannt – nicht erfunden.
        self.assertIsNone(f["provision"]["gesamt"])

    def test_keine_kennzahl_ohne_quelle(self):
        """Besuche gibt es nicht mehr – und damit weder CTR noch Provision je Besuch."""
        f = rf.compute([], set(), measured=MEIN_GUTES_SETUP)
        self.assertEqual(sorted(f["raten"]),
                         ["antrag_abschluss", "epc", "klick_antrag", "stornoquote"])
        self.assertNotIn("views", f)
        self.assertNotIn("platzierungen", f)

    def test_muell_in_den_zeilen_crashed_nicht(self):
        f = rf.compute([{"event": "affiliate_click", "count": "viel"},
                        {"event": "affiliate_click", "count": -5},
                        {"event": "affiliate_click", "count": None},
                        {"event": "affiliate_click", "count": "7"}, "kein dict", None],
                       set(), measured=MEIN_GUTES_SETUP)
        self.assertEqual(f["affiliate_klicks"], 7)


class TestKlicksJeSeite(unittest.TestCase):
    def _fixtures(self):
        clicks = [{"event": "affiliate_click", "article": "posts/a", "count": 3},
                  {"event": "affiliate_click", "article": "pillar/strom/index.md",
                   "count": 1},
                  {"event": "affiliate_click", "article": "", "count": 2},
                  {"event": "cta_click", "article": "home", "slug": "home-ratgeber",
                   "count": 9}]
        # Provisions-Tabelle (einzige Provisionsquelle): 3 Abschlüsse, 0 Stornos, 12 €.
        mp = {"summe": {"abschluesse": 3, "stornos": 0, "provision_eur": 12.0},
              "monate": ["2026-10"], "letzter_monat": "2026-10", "partner": ["CHECK24"]}
        paths = {"/posts/a/", "/pillar/strom/", "/pillar/"}
        return clicks, mp, paths

    def test_klicks_gesamt_zaehlt_nur_affiliate_ereignisse(self):
        clicks, mp, paths = self._fixtures()
        f = rf.compute(clicks, paths, measured=MEIN_GUTES_SETUP, manual_prov=mp)
        # Klicks gesamt = ALLE affiliate_clicks (6), fremde Ereignisse nie mitzählen.
        self.assertEqual(f["affiliate_klicks"], 6)

    def test_trichter_raten_aus_klicks_und_tabelle(self):
        clicks, mp, paths = self._fixtures()
        f = rf.compute(clicks, paths, measured=MEIN_GUTES_SETUP, manual_prov=mp)
        self.assertEqual(f["transaktionen"]["antraege"], 3)
        self.assertEqual(f["transaktionen"]["bestaetigt"], 3)
        self.assertAlmostEqual(f["raten"]["klick_antrag"], 3 / 6.0 * 100, places=4)
        self.assertAlmostEqual(f["raten"]["stornoquote"], 0.0, places=4)
        self.assertAlmostEqual(f["raten"]["epc"], 12.0 / 6.0, places=4)

    def test_seitentabelle_heimat_und_ausschluss(self):
        clicks, mp, paths = self._fixtures()
        f = rf.compute(clicks, paths, measured=MEIN_GUTES_SETUP, manual_prov=mp)
        by = {p["path"]: p for p in f["seiten"]}
        self.assertEqual(by["/posts/a/"]["clicks"], 3)
        self.assertEqual(by["/pillar/strom/"]["clicks"], 1)
        self.assertNotIn("/", by)            # Home ist keine kaufnahe Seite
        self.assertNotIn("/posts/b/", by)    # ohne Klicks → gar nicht erst zeigen
        # Monatssumme wird keiner Seite zugeschrieben – die Tabelle kennt keine Artikel.
        for seite in f["seiten"]:
            self.assertNotIn("revenue", seite)
            self.assertNotIn("epc", seite)

    def test_klicks_von_seiten_ausserhalb_der_kaufnahen_menge_fehlen_in_der_tabelle(self):
        f = rf.compute([{"event": "affiliate_click", "article": "posts/zufall", "count": 4}],
                       {"/pillar/"}, measured=MEIN_GUTES_SETUP)
        self.assertEqual(f["affiliate_klicks"], 4)       # gezählt …
        self.assertEqual(f["seiten"], [])                # … aber keiner kaufnahen Seite zugeordnet


class TestArtikelPfad(unittest.TestCase):
    """SubID/`article` → Blog-Pfad: die Brücke zwischen Zähler und Seiten."""

    def test_pfade(self):
        cases = {"home": "/", "pillar/_index": "/pillar/", "pillar": "/pillar/",
                 "_index": "", "posts": "", "posts/x/index.md": "/posts/x/",
                 "posts/x/_index.md": "/posts/x/", "strom": "/pillar/strom/",
                 "": "", "2026-01-01-a/index.md": ""}
        for art, want in cases.items():
            self.assertEqual(rf.article_to_path(art), want, f"article={art!r}")


class TestReportProtokoll(unittest.TestCase):
    """Gate-Klassifikation hängt an diesen Markern – Format = Vertrag."""

    def _f(self):
        return rf.compute([], set(), measured=MEIN_GUTES_SETUP)

    def test_luecke_meldet_amber_zeile_und_marker(self):
        out = rf.render(self._f(), ["Klicks: Import übersprungen (Zugang oder Konfiguration fehlt)"],
                        ["Zähler-Worker einrichten (docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md)"])
        self.assertIn("## 🚦 Gesamt-Ampel: **AMBER**", out)
        self.assertIn("**Messlücken: 1**", out)
        zeilen = [l for l in out.splitlines() if l.startswith("| AMBER | funnel_gap |")]
        self.assertEqual(len(zeilen), 1)
        zelle = zeilen[0].split("|")[3].strip()
        self.assertEqual(zelle, "Klicks: Import übersprungen (Zugang oder Konfiguration fehlt)")
        self.assertNotIn("|", zelle)  # Pipe im Befund würde die Tabelle sprengen

    def test_ohne_luecken_gruen_ohne_findings(self):
        out = rf.render(self._f(), [], [])
        self.assertIn("## 🚦 Gesamt-Ampel: **GREEN**", out)
        self.assertNotIn("funnel_gap", out)

    def test_unbekannt_wird_nicht_als_null_formatiert(self):
        f = rf.compute([], set(), measured={"clicks": False})
        out = rf.render(f, [], [])
        self.assertIn("unbekannt", out)
        self.assertNotIn("| Affiliate-Klicks | 0 |", out)

    def test_betriebsgrenze_ist_gruen_ohne_luecke(self):
        grenze = "Klickzähler aus (`aktiv: false` in `data/klickmessung.yaml`)"
        out = rf.render(self._f(), [], [], operating_boundaries=[grenze])
        self.assertIn("## 🚦 Gesamt-Ampel: **GREEN**", out)
        self.assertIn("**Messlücken: 0**", out)
        self.assertIn(f"| INFO | operating_boundary | {grenze} |", out)
        self.assertNotIn("funnel_gap", out)

    def test_report_nennt_keine_besuchszahlen(self):
        out = rf.render(self._f(), [], [])
        for wort in ("Besuche", "Outbound-CTR", "pro 100 Besuche"):
            self.assertNotIn(wort + " ", out + " ", f"„{wort}“ ist eine Kennzahl ohne Quelle")


class TestBetriebsgrenzeStattLuecke(unittest.TestCase):
    """Ein bewusst ausgeschalteter Weg ist INFO; eine Quelle, die laufen SOLL, nicht."""

    def test_zaehler_aus_und_tabelle_leer_ist_gruen_mit_zwei_hinweisen(self):
        src, measured, grenzen = rf.lage([], {}, {}, {}, zaehler_aktiv=False)
        self.assertEqual(rf.evaluate(src), [])
        self.assertFalse(measured["clicks"])
        self.assertEqual(len(grenzen), 2)

    def test_alte_zeilen_zaehlen_nicht_wenn_der_zaehler_aus_ist(self):
        _src, measured, _g = rf.lage([{"count": 9}], {"status": "ok", "stand": "2026-10-01T00:00:00Z"},
                                     {}, {}, zaehler_aktiv=False)
        self.assertFalse(measured["clicks"], "ausgeschaltet heißt nicht gemessen")

    def test_zaehler_an_ohne_lieferung_ist_eine_luecke(self):
        for meta, text in (({}, "noch nie importiert"),
                           ({"status": "nicht_konfiguriert"}, "übersprungen"),
                           ({"status": "fehler"}, "fehlgeschlagen")):
            src, _m, _g = rf.lage([], dict(meta, stand=rf.TODAY.isoformat() + "T06:00:00Z")
                                  if meta else {}, {}, {}, zaehler_aktiv=True)
            gaps = rf.evaluate(src)
            self.assertEqual(len(gaps), 1, f"meta={meta}")
            self.assertIn("Klickzähler", gaps[0])
            self.assertIn(text, gaps[0])

    def test_frischer_leerer_import_ist_eine_echte_null(self):
        src, measured, _g = rf.lage([], {"status": "ok", "stand": rf.TODAY.isoformat() + "T06:00:00Z"},
                                    {}, {}, zaehler_aktiv=True)
        self.assertEqual(rf.evaluate(src), [])
        self.assertTrue(measured["clicks"])

    def test_befuellte_aber_veraltete_tabelle_bleibt_eine_luecke(self):
        alt = (rf.TODAY.toordinal() - rf.STALE_DAYS - 1)
        alt_iso = rf.datetime.date.fromordinal(alt).isoformat()
        src, _m, _g = rf.lage([], {}, {"summe": {"abschluesse": 1}},
                              {"status": "ok", "written": alt_iso}, zaehler_aktiv=False)
        gaps = rf.evaluate(src)
        self.assertEqual(len(gaps), 1)
        self.assertIn("Provisions-Tabelle", gaps[0])

    def test_schalterdatei_aktiv_true_false_fehlt(self):
        with tempfile.TemporaryDirectory() as td:
            pfad = os.path.join(td, "klickmessung.yaml")
            for text, soll in (("aktiv: true\n", True), ("aktiv: false\n", False),
                               ("# aktiv: true\naktiv: false\n", False), ("", False)):
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(text)
                self.assertIs(rf.klickmessung_aktiv(pfad), soll, text)
            self.assertIs(rf.klickmessung_aktiv(os.path.join(td, "fehlt.yaml")), False)

    def test_schalter_im_repo_deckt_sich_mit_den_beiden_anderen_lesern(self):
        """Eine Wahrheit: Funnel, Klick-Ketten-Guard und /go/-Generator lesen denselben Schalter."""
        ags = _load("affiliate_shield_fuer_schalter", os.path.join(SCRIPTS, "affiliate_shield.py"))
        self.assertIs(rf.klickmessung_aktiv(), cc.klickmessung_aktiv())
        self.assertIs(rf.klickmessung_aktiv(), ags.klickmessung_aktiv())


class TestCtaMessvertrag(unittest.TestCase):
    """Guard-Stufe 1: Event + Slug + Placement + SubID am /go/-Anker."""

    def test_volles_attribut_set_ist_sauber(self):
        html = ('<a href="/go/strom/?subid=posts-x" rel="sponsored nofollow noopener" '
                'target="_blank" data-klick="affiliate_click" '
                'data-klick-slug="strom" '
                'data-klick-placement="artikel">↔</a>')
        self.assertEqual(cc.scan_page(html, "t"), [])

    def test_jede_einzelne_pflicht_fehlt_wird_gemeldet(self):
        basis = ('<a href="/go/gas/{sub}" rel="sponsored nofollow noopener" '
                 '{ev}{slug}{platz}>↔</a>')
        full = dict(sub="?subid=s", ev=' data-klick="affiliate_click"',
                    slug=' data-klick-slug="gas"',
                    platz=' data-klick-placement="artikel"')
        for feld in full:
            kaputt = dict(full)
            kaputt[feld] = ""
            probs = [p for _l, p in cc.scan_page(
                basis.format(**kaputt), "t")]
            self.assertTrue(probs, f"Entfernen von {feld} bleibt ohne Befund")

    def test_roher_partnerlink_umgeht_kette(self):
        probs = [p for _l, p in cc.scan_page(
            '<a href="https://a.check24.net/misc/click.php?pid=1" '
            'rel="sponsored">x</a>', "t")]
        self.assertEqual(len(probs), 1)
        self.assertIn("roher Partnerlink", probs[0])

    def test_ampersand_escapes_beim_subid_check(self):
        html = ('<a href="/go/dsl/?a=1&amp;subid=x" rel="sponsored nofollow noopener" '
                'data-klick="affiliate_click" data-klick-slug="dsl" '
                'data-klick-placement="artikel">y</a>')
        self.assertEqual(cc.scan_page(html, "t"), [])

    def test_hugo_minify_ohne_attribut_anfuehrungszeichen_ist_sauber(self):
        """Hugo darf sichere Attribut-Werte ohne Anführungszeichen ausgeben."""
        html = ('<a href="/go/strom/?subid=posts-x" rel="sponsored nofollow noopener" '
                'data-klick=affiliate_click data-klick-slug=strom '
                'data-klick-placement=artikel>↔</a>')
        self.assertEqual(cc.scan_page(html, "t"), [])


class TestVerdrahtung(unittest.TestCase):
    """Ohne diese Koppelungen melden die Wachen nie – oder zu spät."""

    NEUE_SCHRITTE = ("revenue-funnel", "click-chain")

    def test_gate_und_vertrag_kennen_die_messschritte(self):
        for step in self.NEUE_SCHRITTE:
            self.assertIn(step, gg.STEPS, f"gate STEPS fehlt {step}")
            self.assertIn(step, gc.MEASURE_STEPS, f"Vertrag MEASURE_STEPS fehlt {step}")
            self.assertIn(step, gc.STEP_SIGNATURES, f"STEP_SIGNATURES fehlt {step}")

    def test_gate_und_vertrag_sind_deckungsgleich(self):
        """Jede Gate-Kennung hat eine Vertrags-Signatur und umgekehrt – sonst
        meldet ein Schritt, den der Vertrag nie prüft (oder umgekehrt)."""
        # `automation` und `build` meldet der Workflow über eigene Schritte
        # (Branch-Schutz-Wache bzw. Hugo-Build); alles andere ist eine Messung
        # mit Signatur im Vertrag.
        gate = set(gg.STEPS) - {"automation", "build"}
        self.assertEqual(sorted(gate - set(gc.STEP_SIGNATURES)), [],
                         "Gate-Kennung ohne Signatur im Vertrag")
        self.assertEqual(sorted(set(gc.STEP_SIGNATURES) - gate), [],
                         "Signatur im Vertrag ohne Gate-Kennung")

    def test_findings_codes_sind_actionable(self):
        # funnel_gap/chain_gap müssen das Gate zur Issue-Aktion zwingen –
        # sonst versickert genau die Eskalation, wegen der alles hier gebaut wurde.
        self.assertIn("funnel_gap", gg.ACTIONABLE_AMBER)
        self.assertIn("chain_gap", gg.ACTIONABLE_AMBER)

    def test_workflow_reihenfolge_und_selbsttestliste(self):
        with open(os.path.join(ROOT, ".github", "workflows",
                               "premium-governance.yml"), encoding="utf-8") as fh:
            wf = fh.read()
        pos_score = wf.find("--emit scorecard")
        self.assertGreater(pos_score, 0, "Scorecard-Emit fehlt")
        selftekoloop = wf.split("Governance-Selbsttests")[1][:600]
        for step in self.NEUE_SCHRITTE:
            p = wf.find(f"--emit {step}")
            self.assertGreater(p, 0, f"premium-governance: --emit {step} fehlt")
            self.assertLess(p, pos_score, f"{step} muss VOR der Scorecard laufen (C1)")
            unter = step.replace("-", "_")
            self.assertIn(unter, selftekoloop,
                          f"Selbsttest-Preflight ignoriert scripts/{unter}.py")
            sig, datei = gc.STEP_SIGNATURES[step]
            self.assertRegex(wf, sig)
            self.assertRegex(wf, datei)

    def test_revenue_import_ohne_gate_und_csv_ignoriert(self):
        path = os.path.join(ROOT, ".github", "workflows", "revenue-import.yml")
        self.assertTrue(os.path.isfile(path), "revenue-import.yml fehlt")
        with open(path, encoding="utf-8") as fh:
            wf = fh.read()
        self.assertNotIn("--emit", wf,
                         "Der reine Import darf das Wochen-Ledger nicht zufüllen")
        for datendatei in ("data/revenue_funnel.json", "data/offline_import.meta.json",
                           "data/provisionen_aggregat.json"):
            self.assertIn(datendatei, wf, f"Commit-Liste fehlt {datendatei}")
        # Die Roh-Tabelle ist gitignored und darf nie in den Commit wandern. Geprüft
        # werden die `git add`-Zeilen, nicht die Kommentare (die sie nennen dürfen).
        git_add = [z for z in wf.splitlines() if z.strip().startswith("git add")]
        self.assertGreaterEqual(len(git_add), 2, "Commit-Schritt ohne git-add-Zeilen")
        for zeile in git_add:
            self.assertNotIn("provisionen/provisionen.csv", zeile,
                             "die gitignorierte Roh-Tabelle darf nie gestaged werden")

    def test_revenue_import_preflight_prueft_die_vorhandenen_skripte(self):
        """Der Preflight darf kein Skript nennen, das es nicht (mehr) gibt –
        sonst stirbt der Lauf am ersten Schritt, bevor irgendetwas gemessen wird."""
        import re
        with open(os.path.join(ROOT, ".github", "workflows", "revenue-import.yml"),
                  encoding="utf-8") as fh:
            wf = fh.read()
        schleife = re.search(r"for s in ([^;]+); do", wf)
        self.assertIsNotNone(schleife, "Selbsttest-Schleife fehlt")
        for s in schleife.group(1).replace("\\", " ").split():
            self.assertTrue(os.path.isfile(os.path.join(SCRIPTS, f"{s}.py")),
                            f"Preflight nennt scripts/{s}.py – die Datei gibt es nicht")

    def test_governance_preflight_nennt_nur_vorhandene_skripte(self):
        import re
        with open(os.path.join(ROOT, ".github", "workflows", "premium-governance.yml"),
                  encoding="utf-8") as fh:
            wf = fh.read()
        schleife = re.search(r"for s in ([^;]+); do", wf)
        self.assertIsNotNone(schleife, "Selbsttest-Schleife fehlt")
        for s in schleife.group(1).replace("\\", " ").split():
            self.assertTrue(os.path.isfile(os.path.join(SCRIPTS, f"{s}.py")),
                            f"Preflight nennt scripts/{s}.py – die Datei gibt es nicht")

    def test_gate_report_pfade_fuer_funnel_und_chain(self):
        # Falscher Pfad = Gate liest einen Report, den es nie gab: Stille statt Alarm.
        self.assertEqual(gg.STEPS["revenue-funnel"]["report"], "REVENUE-FUNNEL-REPORT.md")
        self.assertEqual(gg.STEPS["click-chain"]["report"], "CLICK-CHAIN-REPORT.md")


if __name__ == "__main__":
    unittest.main(verbosity=2)
