#!/usr/bin/env python3
"""Regressionstest: die komplette Umsatz-Messkette (19.09.2026).

Vier Rückschritte sind hier dauerhaft verankert – jeder einzelne hat schon
einmal Daten UNsinn erzeugt oder Lücken unsichtbar gemacht:

  1. Null vs. „unbekannt": Eine nicht gemessene Quelle darf NIE als 0
     erscheinen – sonst optimiert die Redaktion gegen eine Geisterzahl.
  2. Kaufnahe Schiene: Home ist Reichweiten-Seite, kein Wechsel-Traffic –
     sie gehört in den Nenner der Outbound-CTR nicht hinein.
  3. Report-Protokoll: Der Governance-Gate klassifiziert über die
     Befund-Zeilen `| AMBER | funnel_gap | … |` und die Zeile
     `Messlücken: N`. Ändert jemand das Format, stirbt die Eskalation
     still – hier beißt der Test sofort.
  4. Verdrahtung: neue Mess-Schritte MÜSSEN im Gate (STEPS), im Vertrag
     (MEASURE_STEPS + Signaturen) und vor der Scorecard laufen; die
     CTA-Platzierungs-Pflicht gehört in Guard UND Workflow-Commit-Liste.

Dazu: CTA-Messvertrag (Event/Slug/SubID/Placement) und Gateway-Drift als
direkte Aufrufe – dieselben Fälle wie im --selftest, aber als dauerhafter
CI-Test über `python3 -m unittest discover -s scripts/tests`.
"""
from __future__ import annotations

import importlib.util
import os
import sys
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

MEIN_GUTES_SETUP = {"views": True, "clicks": True, "awin": True}


class TestNullVsUnbekannt(unittest.TestCase):
    """Hausregel: nicht gemessen ⇒ unbekannt (None), NIE eine 0."""

    def test_alle_quellen_fehlen_ist_nichts_null(self):
        f = rf.compute({}, [], [], [], set(), measured={
            "views": False, "clicks": False, "awin": False})
        self.assertIsNone(f["affiliate_klicks"])
        self.assertIsNone(f["views"]["kaufnah"])
        self.assertIsNone(f["views"]["total"])
        self.assertIsNone(f["transaktionen"]["antraege"])
        self.assertIsNone(f["provision"]["gesamt"])
        for k, v in f["raten"].items():
            self.assertIsNone(v, f"Rate {k} trotz ungemessener Quelle nicht None")

    def test_gemessen_und_leer_ist_echte_null(self):
        f = rf.compute({"pages": []}, [], {}, [], set(), measured=MEIN_GUTES_SETUP)
        self.assertEqual(f["affiliate_klicks"], 0)          # gemessen, wirklich 0
        self.assertEqual(f["views"]["kaufnah"], 0)
        self.assertEqual(f["transaktionen"]["antraege"], 0)
        # Provision ohne Wert im Dokument bleibt unbekannt – nicht erfunden.
        self.assertIsNone(f["provision"]["gesamt"])


class TestKaufnaheSchiene(unittest.TestCase):
    def _fixtures(self):
        views = {"totals": {"visits": 1000, "pageviews": 2400},
                 "pages": [{"path": "/posts/a/", "views": 150, "visits": 100},
                           {"path": "/", "views": 900, "visits": 700},
                           {"path": "/pillar/strom/", "views": 80, "visits": 50},
                           {"path": "/posts/b/", "views": 7, "visits": 5}]}
        clicks = [{"event": "affiliate_click", "article": "posts/a", "count": 3},
                  {"event": "affiliate_click", "article": "pillar/strom/index.md",
                   "count": 1},
                  {"event": "affiliate_click", "article": "", "count": 2}]
        ctas = [{"event": "cta_click", "slug": "home-ratgeber", "count": 9}]
        awin = {"status_totals": {"approved": {"count": 2}, "pending": {"count": 1}},
                "total_commission": 12.0, "total_paid": 10.0,
                "articles": {"a": {"article": "posts/a", "commission": 9.0,
                                   "orders": 2}}}
        paths = {"/posts/a/", "/pillar/strom/", "/pillar/"}
        return views, clicks, awin, ctas, paths

    def test_kaufnah_nenner_und_ctr(self):
        views, clicks, awin, ctas, paths = self._fixtures()
        f = rf.compute(views, clicks, awin, ctas, paths, measured=MEIN_GUTES_SETUP)
        # Home (700 Besuche) und ferne Seite /posts/b/ (5) bleiben draußen.
        self.assertEqual(f["views"]["kaufnah"], 150)  # a(100)+strom(50); b fehlt in paths = nicht kaufnah
        # Klicks gesamt = ALLE affiliate_clicks (6), cta_click nie mitzählen.
        self.assertEqual(f["affiliate_klicks"], 6)
        self.assertAlmostEqual(f["raten"]["outbound_ctr"], 6 / 150.0 * 100, places=4)  # Prozent-Skala (4 %)
        # Trichter-Raten aus Awin: 3 Anträge, 2 bestätigt, Storno 0 → quotiert.
        self.assertEqual(f["transaktionen"]["antraege"], 3)
        self.assertEqual(f["transaktionen"]["bestaetigt"], 2)
        self.assertAlmostEqual(f["raten"]["klick_antrag"], 3 / 6.0 * 100, places=4)
        self.assertAlmostEqual(f["raten"]["stornoquote"], 0.0, places=4)
        self.assertAlmostEqual(f["raten"]["epc"], 12.0 / 6.0, places=4)

    def test_seitentabelle_heimat_und_ausschluss(self):
        views, clicks, awin, ctas, paths = self._fixtures()
        f = rf.compute(views, clicks, awin, ctas, paths, measured=MEIN_GUTES_SETUP)
        by = {p["path"]: p for p in f["seiten"]}
        self.assertIn("/posts/a/", by)      # Klicks + Provision zugeordnet
        self.assertNotIn("/", by)            # Home ist keine Trichter-Seite
        self.assertNotIn("/posts/b/", by)    # ohne Messwert → gar nicht erst zeigen
        self.assertEqual(by["/posts/a/"]["clicks"], 3)
        self.assertAlmostEqual(by["/posts/a/"]["revenue"], 9.0, places=2)

    def test_platzierungstabellen_aus_cta_und_markdown_klicks(self):
        views, clicks, awin, ctas, paths = self._fixtures()
        clicks = clicks + [{"event": "cta_click", "article": "home", "count": 4,
                            "slug": "home-strom"}]
        f = rf.compute(views, clicks, awin, ctas, paths, measured=MEIN_GUTES_SETUP)
        self.assertEqual(f["platzierungen"]["home-ratgeber"], 9)
        self.assertEqual(f["platzierungen"]["home-strom"], 4)
        # …und trotzdem KEIN Affiliate-Klick:
        self.assertEqual(f["affiliate_klicks"], 6)


class TestArtikelPfad(unittest.TestCase):
    """SubID/Umami-`article` → Blog-Pfad: die Brücke zwischen beiden Systemen."""

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
        return rf.compute({"pages": [], "totals": {"visits": 0, "pageviews": 0}},
                          [], {}, [], set(), measured=MEIN_GUTES_SETUP)

    def test_luecke_meldet_amber_zeile_und_marker(self):
        out = rf.render(self._f(), ["Views: Import übersprungen (Secret fehlt)"],
                        ["UMAMI_API_TOKEN anlegen (docs/UMSATZ-MESSUNG-PREMIUM.md)"])
        self.assertIn("## 🚦 Gesamt-Ampel: **AMBER**", out)
        self.assertIn("**Messlücken: 1**", out)
        zeilen = [l for l in out.splitlines() if l.startswith("| AMBER | funnel_gap |")]
        self.assertEqual(len(zeilen), 1)
        zelle = zeilen[0].split("|")[3].strip()
        self.assertEqual(zelle, "Views: Import übersprungen (Secret fehlt)")
        self.assertNotIn("|", zelle)  # Pipe im Befund würde die Tabelle sprengen

    def test_ohne_luecken_gruen_ohne_findings(self):
        out = rf.render(self._f(), [], [])
        self.assertIn("## 🚦 Gesamt-Ampel: **GREEN**", out)
        self.assertNotIn("funnel_gap", out)

    def test_unbekannt_wird_nicht_als_null_formatiert(self):
        f = rf.compute({}, [], [], [], set(), measured={
            "views": False, "clicks": False, "awin": False})
        out = rf.render(f, [], [])
        self.assertIn("unbekannt", out)
        self.assertNotIn("| Affiliate-Klicks | 0 |", out)


class TestCtaMessvertrag(unittest.TestCase):
    """Guard-Stufe 1: Event + Slug + Placement + SubID am /go/-Anker."""

    def test_volles_attribut_set_ist_sauber(self):
        html = ('<a href="/go/strom/?subid=posts-x" rel="sponsored nofollow noopener" '
                'target="_blank" data-umami-event="affiliate_click" '
                'data-umami-event-slug="strom" '
                'data-umami-event-placement="artikel">↔</a>')
        self.assertEqual(cc.scan_page(html, "t"), [])

    def test_jede_einzelne_pflicht_fehlt_wird_gemeldet(self):
        basis = ('<a href="/go/gas/{sub}" rel="sponsored nofollow noopener" '
                 '{ev}{slug}{platz}>↔</a>')
        full = dict(sub="?subid=s", ev=' data-umami-event="affiliate_click"',
                    slug=' data-umami-event-slug="gas"',
                    platz=' data-umami-event-placement="artikel"')
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
                'data-umami-event="affiliate_click" data-umami-event-slug="dsl" '
                'data-umami-event-placement="artikel">y</a>')
        self.assertEqual(cc.scan_page(html, "t"), [])


class TestVerdrahtung(unittest.TestCase):
    """Ohne diese Koppelungen melden die neuen Wachen nie – oder zu spät."""

    NEUE_SCHRITTE = ("umami-views", "awin-fetch", "revenue-funnel", "click-chain")

    def test_gate_und_vertrag_kennen_die_messschritte(self):
        for step in self.NEUE_SCHRITTE:
            self.assertIn(step, gg.STEPS, f"gate STEPS fehlt {step}")
            self.assertIn(step, gc.MEASURE_STEPS, f"Vertrag MEASURE_STEPS fehlt {step}")
            self.assertIn(step, gc.STEP_SIGNATURES, f"STEP_SIGNATURES fehlt {step}")

    def test_findings_codes_sind_actionable(self):
        # funnel_gap/chain_gap müssen das Gate zur Issue-Aktion zwingen –
        # sonst versickert genau die Eskalation, wegen der alles hier gebaut wurde.
        self.assertIn("funnel_gap", gg.ACTIONABLE_AMBER)
        self.assertIn("chain_gap", gg.ACTIONABLE_AMBER)

    def test_workflow_reihenfolge_und_selbsttestliste(self):
        import re as _re
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
        for datendatei in ("data/revenue_funnel.json", "data/umami_views.json",
                           "data/awin_fetch.meta.json", "data/umami_ctas.json"):
            self.assertIn(datendatei, wf, f"Commit-Liste fehlt {datendatei}")
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            gi = fh.read()
        self.assertIn("data/awin_transactions.csv", gi.splitlines(),
                      "Roh-CSV gehört in .gitignore (Auftragsdaten, kein Repo)")

    def test_gate_report_pfade_fuer_funnel_und_chain(self):
        # Falscher Pfad = Gate liest einen Report, den es nie gab: Stille statt Alarm.
        self.assertEqual(gg.STEPS["revenue-funnel"]["report"], "REVENUE-FUNNEL-REPORT.md")
        self.assertEqual(gg.STEPS["click-chain"]["report"], "CLICK-CHAIN-REPORT.md")


if __name__ == "__main__":
    unittest.main(verbosity=2)
