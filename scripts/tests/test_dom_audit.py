"""Regressionstests für das DOM-/Layout-Budget (Issue #338, 21.09.2026).

Warum diese Tests existieren
---------------------------
Der Layout-Audit hat jahrelang die FALSCHEN Seiten gemessen (Startseite + 3
neueste Artikel) und die Zahlen zudem mit einer selbst gebauten Kopie des
Browsers geschätzt. Beides ist repariert – und beides kann still zurückfallen:

1) Der Parser (scripts/dom_audit.py) muss den Baum so bauen, wie ein Browser
   mit aktivem JavaScript ihn baut. Die acht Fälle unten sind mit jsdom an
   genau diesen Zeichenketten gemessen (eine Ausnahme ist begründet), damit
   „browser-treu" kein Gefühl bleibt, sondern eine Zusage.
2) Die Budgets dürfen nur EINE Quelle haben. Der Browser-Audit trägt eine
   eingefrorene Kopie als Notfall-Wert; dieser Test hält sie identisch.
3) Die Befund-Zählung (kritisch = Lighthouse-Grenze, Warnung = Frühwarnung)
   entscheidet, ob ein Lauf rot wird und ein Issue entsteht. Vertauschte
   Grenzen wären entweder ein Dauer-Alarm (#338) oder ein Scheingrün.

Alle Tests laufen ohne Netz, ohne Hugo und ohne Browser.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import dom_audit  # noqa: E402
import layout_audit  # noqa: E402

PAGE_KOPF = ('<!DOCTYPE html><html lang="de"><head><meta charset=utf-8>'
             '<title>t</title></head><body>')


class ParserVertragTests(unittest.TestCase):
    """Der Parser muss dem Browser folgen, nicht der Bequemlichkeit."""

    def test_selftest_faelle(self):
        for i, (html, want) in enumerate(dom_audit.SELFTEST_CASES, 1):
            with self.subTest(fall=i):
                m = dom_audit.measure(html, f"/case{i}/")
                got = {"elements": m.elements, "depth": m.depth,
                       "maxchildren": m.max_children}
                if "headchildren" in want:
                    got["headchildren"] = m.head_children
                for key, value in want.items():
                    self.assertEqual(value, got[key],
                                     f"Fall {i}: {key}")

    def test_duplikat_html_erzeugt_kein_zweites_element(self):
        m = dom_audit.measure(
            '<html lang="de"><html class="x"><body><p>a</p></body></html>',
            "/d/")
        self.assertEqual(4, m.elements)      # html, head, body, p
        # Kontrolle über den Baum statt über die Zahl: genau EIN html-Element
        root, _ = dom_audit.parse_document('<html><html><body><p>a</p>')
        self.assertEqual("html", root.tag)
        self.assertEqual(["head", "body"],
                         [c.tag for c in root.children])   # implizit + einmalig

    def test_p_endet_am_block_starttag(self):
        # <p>a<div>b</div> → div ist GESCHWISTER von p, nicht Kind
        root, _ = dom_audit.parse_document(
            PAGE_KOPF + '<p>a<div>b</div></body></html>')
        body = next(c for c in root.children if c.tag == "body")
        self.assertEqual(["p", "div"], [c.tag for c in body.children])

    def test_noscript_ist_rohtext(self):
        root, _ = dom_audit.parse_document(
            '<html><head><noscript><style>a{}</style></noscript></head>'
            '<body></body></html>')
        head = next(c for c in root.children if c.tag == "head")
        self.assertEqual(1, len(head.children))
        self.assertEqual(0, len(head.children[0].children))

    def test_fremdinhalt_selbstschliessend(self):
        m = dom_audit.measure(
            PAGE_KOPF + '<svg viewBox="0 0 1 1"><path d="M0 0"/></svg>'
            '</body></html>', "/s/")
        # html, head, meta, title, body, svg, path
        self.assertEqual(7, m.elements)

    def test_pfadangaben_sind_reparierbar(self):
        html = (PAGE_KOPF + '<main id="m"><ul class="terms-tags">'
                + "".join(f"<li>{i}</li>" for i in range(70))
                + "</ul></main></body></html>")
        m = dom_audit.measure(html, "/tags/")
        self.assertIn("terms-tags", m.max_children_path)
        self.assertLessEqual(len(m.max_children_path.split(" > ")), 5)
        self.assertEqual(70, m.max_children)


class BudgetTests(unittest.TestCase):
    """Grenzen und Frühwarnungen – die Logik, die über rot/grün entscheidet."""

    def test_lighthouse_grenze_ist_kritisch(self):
        m = dom_audit.Metrics()
        m.rel = "/x/"
        m.max_children = dom_audit.LIMIT["children"] + 1
        crit, warn = dom_audit.violations(m)
        self.assertTrue(any("Lighthouse-Grenze" in c for c in crit))
        self.assertFalse(warn)

    def test_fruehwarnung_ist_kein_kritisches_ergebnis(self):
        m = dom_audit.Metrics()
        m.rel = "/x/"
        m.head_children = dom_audit.BUDGET["head_children"] + 1
        crit, warn = dom_audit.violations(m)
        self.assertFalse(crit)
        self.assertEqual(1, len(warn))

    def test_genau_auf_der_fruehwarnung_ist_gruen(self):
        m = dom_audit.Metrics()
        m.rel = "/x/"
        m.max_children = dom_audit.BUDGET["children"]
        crit, warn = dom_audit.violations(m)
        self.assertFalse(crit or warn)

    def test_fruehwarnung_liegt_unter_der_lighthouse_grenze(self):
        for key in ("children", "head_children", "depth", "elements"):
            with self.subTest(metrik=key):
                self.assertLess(dom_audit.BUDGET[key], dom_audit.LIMIT[key])

    def test_browser_audit_fallback_ist_identisch(self):
        """Die Notfall-Kopie im Browser-Audit darf nicht auseinanderlaufen."""
        text = (ROOT / "scripts/layout_browser_check.js").read_text(
            encoding="utf-8")
        block = text[text.index("const FALLBACK"):text.index("function loadDomAudit")]
        for key, value in dom_audit.BUDGET.items():
            self.assertRegex(block, rf"{key}:\s*{value}\b",
                             f"BUDGET.{key} fehlt/abweichend im JS-Fallback")
        for key, value in dom_audit.LIMIT.items():
            self.assertRegex(block, rf"{key}:\s*{value}\b",
                             f"LIMIT.{key} fehlt/abweichend im JS-Fallback")
        # Der Laufzeit-Satz (Frühwarnung für das DOM MIT Erweiterungsschicht)
        # muss ebenfalls gespiegelt sein – sonst prüft der Browser-Audit ohne
        # JSON gegen andere Zahlen als der statische Audit.
        self.assertRegex(block, r"fruehwarnung_runtime:\s*\{")
        for key, value in dom_audit.BUDGET_RUNTIME.items():
            self.assertRegex(block, rf"{key}:\s*{value}\b",
                             f"BUDGET_RUNTIME.{key} fehlt/abweichend im JS-Fallback")


class AuditLaufTests(unittest.TestCase):
    """End-to-End über das CLI: Ausgabe, JSON, Exit-Codes."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.base = self.tmp / "public"
        (self.base / "page" / "2").mkdir(parents=True)
        (self.base / "posts" / "a").mkdir(parents=True)

    def _write(self, rel, body):
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/dom_audit.py"),
             "--base", str(self.base), *args],
            capture_output=True, text=True, cwd=str(ROOT))

    def test_gruene_seite_ist_exit_0_und_ignoriert_paginierung(self):
        self._write("index.html", PAGE_KOPF + "<p>ok</p></body></html>")
        # Paginierung: 70 Kinder – darf den Lauf NICHT kippen (Kopie der Vorlage)
        self._write("page/2/index.html",
                    PAGE_KOPF + "<ul>" + "<li>x</li>" * 70 + "</ul></body></html>")
        out = self.tmp / "dom.json"
        res = self._run("--json", str(out))
        self.assertEqual(0, res.returncode, res.stdout + res.stderr)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(1, data["pages"])
        self.assertTrue(data["all_ok"])

    def test_zu_viele_kinder_sind_exit_1(self):
        self._write("posts/a/index.html",
                    PAGE_KOPF + "<ul>" + "<li>x</li>" * 70 + "</ul></body></html>")
        res = self._run()
        self.assertEqual(1, res.returncode)
        self.assertIn("Lighthouse-Grenze", res.stdout)

    def test_strict_kippt_bei_fruehwarnung(self):
        self._write("posts/a/index.html",
                    PAGE_KOPF + "<ul>" + "<li>x</li>" * 55 + "</ul></body></html>")
        self.assertEqual(0, self._run().returncode)          # Warnung allein: grün
        self.assertEqual(1, self._run("--strict").returncode)

    def test_fehlender_bau_ist_exit_2(self):
        shutil.rmtree(self.base)
        self.assertEqual(2, self._run().returncode)


class LayoutAuditIntegrationTests(unittest.TestCase):
    """Der statische Audit zieht die DOM-Prüfungen selbst mit durch."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.base = self.tmp / "public"
        (self.base / "posts" / "a").mkdir(parents=True)
        self.old_base, self.old_json = layout_audit.BASE, layout_audit.DOM_JSON
        self.old_root = layout_audit.ROOT
        self.addCleanup(self._restore)
        layout_audit.BASE = str(self.base)
        layout_audit.DOM_JSON = str(self.tmp / ".cache" / "layout" / "dom-audit.json")
        layout_audit.ROOT = str(self.tmp)
        for bucket in (layout_audit.CRITICAL, layout_audit.WARN, layout_audit.OK):
            bucket.clear()

    def _restore(self):
        layout_audit.BASE = self.old_base
        layout_audit.DOM_JSON = self.old_json
        layout_audit.ROOT = self.old_root

    def test_dom_budget_schreibt_json_und_ok_zeile(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + "<p>ok</p></body></html>", encoding="utf-8")
        result = layout_audit.check_dom_budget()
        self.assertEqual(1, result["pages"])
        self.assertTrue(Path(layout_audit.DOM_JSON).is_file())
        self.assertTrue(any("DOM-Budget" in line for line in layout_audit.OK))
        self.assertFalse(layout_audit.CRITICAL)

    def test_gerissene_grenze_landet_kritisch(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + "<ul>" + "<li>x</li>" * 70 + "</ul></body></html>",
            encoding="utf-8")
        layout_audit.check_dom_budget()
        self.assertTrue(any("Lighthouse-Grenze" in line
                            for line in layout_audit.CRITICAL))

    def test_alt_pruefung_sieht_nur_den_gebauten_inhalt(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + "<article><img src=x.jpg></article></body></html>",
            encoding="utf-8")
        layout_audit.check_alts()
        self.assertTrue(any("Alt-Text" in line for line in layout_audit.WARN))
        layout_audit.WARN.clear()
        layout_audit.OK.clear()
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + '<article><img src=x.jpg alt="Sparschwein"></article>'
            '</body></html>', encoding="utf-8")
        layout_audit.check_alts()
        self.assertFalse(layout_audit.WARN)

    def test_generischer_alt_text_wird_gemeldet(self):
        for alt in ("cover.jpg", "bild", "hero-1200"):
            with self.subTest(alt=alt):
                layout_audit.WARN.clear()
                layout_audit.OK.clear()
                (self.base / "posts" / "a" / "index.html").write_text(
                    PAGE_KOPF + f'<article><img src=images/covers/hero.jpg alt="{alt}">'
                    '</article></body></html>', encoding="utf-8")
                layout_audit.check_alts()
                self.assertTrue(any("generischer Alt-Text" in line
                                    for line in layout_audit.WARN), alt)

    def test_beschreibender_alt_text_ist_gruen(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + '<article><img src=images/covers/hero.jpg '
            'alt="Sparschwein mit Münzen auf einem Notizbuch"></article>'
            '</body></html>', encoding="utf-8")
        layout_audit.check_alts()
        self.assertFalse(layout_audit.WARN)

    # ---------- hreflang-Hygiene (Issue #338) ----------

    def _page_mit_links(self, rel, links):
        (self.base / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.base / rel).write_text(
            PAGE_KOPF.replace("</head>", "".join(links) + "</head>")
            + "<p>ok</p></body></html>", encoding="utf-8")

    def test_hreflang_doppelt_ist_kritisch(self):
        self._page_mit_links("posts/a/index.html", [
            '<link rel="canonical" href="https://example.org/posts/a/">',
            '<link rel="alternate" hreflang="de" href="https://example.org/posts/a/">',
            '<link rel="alternate" hreflang="de" href="https://example.org/posts/a/">',
        ])
        layout_audit.check_hreflang()
        self.assertTrue(any("doppelte" in line for line in layout_audit.CRITICAL),
                        layout_audit.CRITICAL)

    def test_hreflang_selbstreferenz_muss_canonical_treffen(self):
        self._page_mit_links("posts/b/index.html", [
            '<link rel="canonical" href="https://example.org/posts/b/">',
            '<link rel="alternate" hreflang="de" href="https://example.org/posts/">',
        ])
        layout_audit.check_hreflang()
        self.assertTrue(any("Canonical" in line for line in layout_audit.CRITICAL),
                        layout_audit.CRITICAL)

    def test_hreflang_pager_abweichung_ist_warnung_nicht_kritisch(self):
        # Geerbt aus dem versiegelten head.html: Abschnitts-Wurzel statt Seite.
        self._page_mit_links("categories/x/page/2/index.html", [
            '<link rel="canonical" href="https://example.org/categories/x/page/2/">',
            '<link rel="alternate" hreflang="de" href="https://example.org/categories/x/">',
            '<link rel="alternate" hreflang="x-default" '
            'href="https://example.org/categories/x/page/2/">',
        ])
        layout_audit.check_hreflang()
        self.assertFalse(layout_audit.CRITICAL)
        self.assertTrue(any("Paginierungsseiten" in line for line in layout_audit.WARN),
                        layout_audit.WARN)

    def test_hreflang_sauber_ist_gruen(self):
        self._page_mit_links("posts/c/index.html", [
            '<link rel="canonical" href="https://example.org/posts/c/">',
            '<link rel="alternate" hreflang="de" href="https://example.org/posts/c/">',
            '<link rel="alternate" hreflang="x-default" href="https://example.org/posts/c/">',
        ])
        self._page_mit_links("page/1/index.html", [
            '<link rel="canonical" href="https://example.org/">',
            '<link rel="alternate" hreflang="de" href="https://example.org/">',
        ])
        layout_audit.check_hreflang()
        self.assertFalse(layout_audit.CRITICAL)
        self.assertFalse(layout_audit.WARN)
        self.assertTrue(any("hreflang" in line for line in layout_audit.OK))

    def test_dekoratives_leeres_alt_ist_erlaubt(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + '<article><img src=x.svg alt="" aria-hidden="true">'
            '</article></body></html>', encoding="utf-8")
        layout_audit.check_alts()
        self.assertFalse(layout_audit.WARN)

    def test_chunker_vertrag_meldet_verschachtelte_ueberschrift(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + '<article><div class="post-content md-content">'
            '<div class="ff-content-chunk"><h2 id="ok">A</h2></div>'
            '<div class="ff-cta"><h3 id="kaputt">B</h3></div>'
            '</div></article></body></html>', encoding="utf-8")
        layout_audit.check_chunker_contract()
        self.assertTrue(any("Chunker-Vertrag" in line
                            for line in layout_audit.CRITICAL))

    def test_chunker_vertrag_gruen_auf_blockebene(self):
        (self.base / "posts" / "a" / "index.html").write_text(
            PAGE_KOPF + '<article><div class="post-content md-content">'
            '<div class="ff-content-chunk"><h2 id="a">A</h2><h3 id="b">B</h3>'
            '</div></div></article></body></html>', encoding="utf-8")
        layout_audit.check_chunker_contract()
        self.assertFalse(layout_audit.CRITICAL)
        self.assertTrue(any("Chunker-Vertrag" in line for line in layout_audit.OK))


class TemplateVertragTests(unittest.TestCase):
    """Die Reparatur selbst bleibt sichtbar (sonst kehrt sie still zurück)."""

    def test_opengraph_ohne_head_ballast(self):
        text = (ROOT / "layouts/_partials/templates/opengraph.html").read_text(
            encoding="utf-8")
        self.assertNotIn('property="article:tag"', text)   # 6 Kinder gespart
        self.assertIn('property="og:image:type"', text)    # dokumentierte Entscheidung bleibt
        self.assertIn('property="og:image"', text)          # Kern bleibt
        self.assertIn("og:image:alt", text)

    def test_deferred_scripts_stehen_nicht_im_head(self):
        head = (ROOT / "layouts/_partials/extend_head.html").read_text(
            encoding="utf-8")
        self.assertNotIn("cloud.umami.is", head)
        self.assertNotIn("serviceWorker.register", head)
        foot = (ROOT / "layouts/_partials/footer.html").read_text(
            encoding="utf-8")
        self.assertIn('partial "deferred_scripts.html"', foot)
        deferred = (ROOT / "layouts/_partials/deferred_scripts.html").read_text(
            encoding="utf-8")
        self.assertIn("cloud.umami.is", deferred)
        self.assertIn("serviceWorker.register", deferred)

    def test_taxonomie_ist_gruppiert(self):
        text = (ROOT / "layouts/taxonomy.html").read_text(encoding="utf-8")
        self.assertIn("terms-group", text)
        self.assertIn("terms-index", text)
        # Die Gruppierung ist der Grund, warum kein Element mehr 136 Kinder hat
        self.assertNotRegex(text, r"<ul class=\"terms-tags\">\s*\{\{-\s*range\s+\$key")

    def test_chunker_teilt_auch_an_h3(self):
        text = (ROOT / "layouts/_partials/sectioned_content.html").read_text(
            encoding="utf-8")
        self.assertIn(r"<h[23] id=", text)


class JsdomParitaetTests(unittest.TestCase):
    """Optionaler Gegenbeweis gegen einen echten HTML-Parser (jsdom).

    jsdom ist keine Projekt-Abhängigkeit: fehlt es, wird der Test
    übersprungen – er ist ein Beweis-Werkzeug für die Entwicklung, keine
    CI-Pflicht. Ausgeführt werden die acht Parser-Fälle; erwartet wird
    Deckungsgleichheit bei Elementen, Tiefe und max. Kindern.
    """

    JS = """
const {JSDOM} = require('jsdom');
const cases = JSON.parse(process.env.DOM_CASES);
// runScripts: 'dangerously' schaltet das Scripting-Flag ein – genau dann
// behandelt der HTML-Parser (parse5) den Inhalt von <noscript> als Rohtext,
// wie jeder Browser mit aktivem JavaScript. Ohne das Flag sähe jsdom dort
// einen echten Teilbaum und würde eine Abweichung erfinden, die es im
// Browser nicht gibt. Die Test-Fixtures enthalten keine Skripte.
for (const html of cases) {
  const dom = new JSDOM(html, {runScripts: 'dangerously'});
  const doc = dom.window.document;
  const all = doc.querySelectorAll('*');
  let depth = 0, maxKids = 0;
  for (const el of all) {
    let d = 0, n = el;
    while (n && n.nodeType === 1 && n !== doc.documentElement) { d++; n = n.parentElement; }
    if (d > depth) depth = d;
    if (el.children.length > maxKids) maxKids = el.children.length;
  }
  console.log(JSON.stringify({elements: all.length, depth, maxchildren: maxKids}));
}
"""

    def test_paritaet_wenn_jsdom_verfuegbar(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("kein node vorhanden")
        probe = subprocess.run([node, "-e", "require.resolve('jsdom')"],
                               capture_output=True, text=True,
                               cwd=str(ROOT))
        if probe.returncode != 0:
            self.skipTest("jsdom nicht installiert (optionaler Beweis)")
        htmls = [html for html, _want in dom_audit.SELFTEST_CASES]
        env = dict(os.environ, DOM_CASES=json.dumps(htmls))
        res = subprocess.run([node, "-e", self.JS],
                             capture_output=True, text=True, cwd=str(ROOT), env=env)
        self.assertEqual(0, res.returncode, res.stderr)
        for line, html in zip(res.stdout.strip().splitlines(), htmls):
            js = json.loads(line)
            m = dom_audit.measure(html, "/x/")
            self.assertEqual(js["elements"], m.elements, html[:40])
            self.assertEqual(js["depth"], m.depth, html[:40])
            self.assertEqual(js["maxchildren"], m.max_children, html[:40])


if __name__ == "__main__":
    unittest.main()
