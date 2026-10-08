#!/usr/bin/env python3
"""Vertragstests für die Suche (Pagefind, 08.10.2026).

Geprüft wird die Verdrahtung, nicht das Ranking:
  · Pagefind ist exakt gepinnt (kein ^ und kein ~) – Lockfile und package.json
  · der Index wird im Deploy nach dem letzten Hugo-Build und vor der
    Veröffentlichung gebaut, fail-closed
  · die Suchseite ist aus Index und Sitemap ausgeschlossen (noindex)
  · das Such-Skript setzt nie HTML aus Fremdtext ein und lädt nichts von
    fremden Hosts; die Eingabe wandert nicht per GET in die URL
  · der Newsletter-Streifen bleibt ein Block pro Seite
  · package.json ist gültiges JSON ohne doppelte Schlüssel, Lockfile passt dazu
  · es gibt genau eine Suchoberfläche (kein zweiter pagefind-ui-Pfad)
  · die Suchseite trägt keine Front-Matter-Reste im Fließtext
  · die Index-Wache (scripts/suchindex_check.py) besteht ihren Selbsttest

Aufruf:  python3 -m unittest scripts.tests.test_suche_pagefind
"""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def lies(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def ohne_js_kommentare(js: str) -> str:
    """Blockkommentare und Zeilenkommentare entfernen: geprüft wird Code, nicht Begründung."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", js)


class PagefindVertrag(unittest.TestCase):
    def test_version_ist_exakt_gepinnt(self):
        pkg = json.loads(lies("package.json"))
        self.assertEqual(pkg["dependencies"]["pagefind"], "1.5.2",
                         "exakt pinnen: kein ^ und kein ~ bei einem Such-Werkzeug im Deploy")
        lock = json.loads(lies("package-lock.json"))
        self.assertEqual(lock["packages"][""]["dependencies"]["pagefind"], "1.5.2")
        self.assertIn("node_modules/pagefind", lock["packages"])

    def test_suchindex_skript_baut_public(self):
        pkg = json.loads(lies("package.json"))
        self.assertIn("--site public", pkg["scripts"]["suchindex"])
        self.assertIn("--force-language de", pkg["scripts"]["suchindex"])

    def test_deploy_baut_index_nach_hugo_und_vor_veroeffentlichung(self):
        wf = lies(".github/workflows/deploy.yml")
        i_index = wf.index("name: Suchindex bauen (Pagefind)")
        i_gh = wf.index("name: Deploy auf gh-pages")
        self.assertLess(i_index, i_gh, "der Index muss vor dem gh-pages-Deploy entstehen")
        zwischen = wf[i_index:i_gh]
        self.assertNotIn("hugo", zwischen, "nach dem Index darf nichts mehr neu bauen")
        self.assertIn("npm run --silent suchindex", zwischen)
        self.assertIn("set -euo pipefail", zwischen)
        self.assertIn("test -s public/pagefind/pagefind.js", zwischen, "fail-closed: ohne Index kein Deploy")

    def test_baseof_indexiert_nur_den_inhalt(self):
        base = lies("layouts/baseof.html")
        self.assertIn('id="main-content" data-pagefind-body', base,
                      "nur <main> wird indexiert – sonst Navigation und Footer in jeder Suche")
        self.assertIn('data-pagefind-ignore="all"', base)
        self.assertIn('hasPrefix .RelPermalink "/suche/"', base)
        self.assertIn("with .Paginator", base)
        self.assertIn("gt .PageNumber 1", base,
                      "Blätterseiten ab Seite 2 bleiben aus dem Index")
        self.assertIn("$listenseite", base,
                      "der Paginator wird nur auf Listenseiten abgefragt (404 wirft sonst einen Fehler)")
        self.assertIn('partial "seo_indexierbar.html" .', base,
                      "noindex-Seiten (404, Newsletter-Abmeldung) gehören nicht in die Suche – "
                      "dieselbe Quelle wie robots-Meta und Sitemap")

    def test_suchseite_ist_aus_index_und_sitemap(self):
        seite = lies("content/suche/index.md")
        self.assertIn("robotsNoIndex: true", seite)
        self.assertIn("sitemap:\n  disable: true", seite)
        self.assertIn("{{< suche >}}", seite)

    def test_ohne_js_hinweis_verlinkt_nur_vorhandene_seiten(self):
        sc = lies("layouts/shortcodes/suche.html")
        self.assertNotIn('"blog/"', sc, "/blog/ gibt es nicht – der Blog liegt unter /posts/ (Layout-Gate 08.10.2026)")
        for ziel in ("posts/", "pillar/", "werkzeuge/"):
            self.assertIn(f'"{ziel}" | relURL', sc)

    def test_footer_verlinkt_die_suche(self):
        footer = lies("layouts/_partials/footer.html")
        self.assertIn('<a href="{{ "suche/" | absURL }}">Suche</a>', footer)

    def test_formular_ohne_get_uebergabe_und_ohne_innerhtml(self):
        sc = lies("layouts/shortcodes/suche.html")
        formular = re.search(r"<form[^>]*>", sc)
        self.assertIsNotNone(formular)
        self.assertNotIn("action=", formular.group(0), "kein GET-Submit: die Eingabe bliebe in der URL")
        self.assertIn("hidden", formular.group(0), "ohne JavaScript bleibt das Formular verborgen")
        js = ohne_js_kommentare(lies("static/premium/ff-suche.js"))
        for verboten in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(verboten, js, f"{verboten} setzt Fremdtext als HTML ein")
        self.assertIn("preventDefault", js, "die Eingabe wird im Skript abgefangen")

    def test_js_laedt_nichts_von_fremden_hosts(self):
        js = ohne_js_kommentare(lies("static/premium/ff-suche.js"))
        self.assertIsNone(re.search(r"https?://", js), "keine externen Hosts im Such-Skript")

    def test_js_ohne_tracking_und_speicher(self):
        js = ohne_js_kommentare(lies("static/premium/ff-suche.js"))
        for wort in ("umami", "localStorage", "sessionStorage", "document.cookie", "sendBeacon"):
            self.assertNotIn(wort, js, f"{wort} ist im Such-Skript nicht erlaubt")

    def test_werkzeug_streifen_bleibt_ein_block_pro_seite(self):
        streifen = lies("layouts/_partials/newsletter_strip.html")
        self.assertIn("$werkzeug", streifen)
        self.assertIn("Dienstags", streifen, "Werkzeug-Zusage nennt den Dienstag")
        self.assertIn("Freitags", streifen, "Werkzeug-Zusage nennt den Freitag")
        self.assertEqual(streifen.count('class="newsletter-footer ff-nl-strip"'), 1,
                         "genau ein Anmeldeblock-Wrapper – kein zweiter Hinweis pro Seite")
        self.assertEqual(streifen.count('<p class="ff-nl-strip__text">'), 2,
                         "ein Textzweig für Werkzeuge, einer für alle übrigen Seiten")

    def test_css_liegt_in_extended(self):
        self.assertTrue((ROOT / "assets/css/extended/ff-suche.css").exists(),
                        "PaperMod bindet css/extended/*.css automatisch ein")


def _ohne_doppelte_schluessel(paare):
    schluessel = [k for k, _ in paare]
    doppelt = sorted({k for k in schluessel if schluessel.count(k) > 1})
    if doppelt:
        raise ValueError(f"doppelte Schlüssel: {doppelt}")
    return dict(paare)


class PackageVertrag(unittest.TestCase):
    """Dauerheilung #644: ein kaputtes package.json hat Deploy, E2E und alle npm-Wachen gestoppt."""

    def test_package_json_ist_gueltig_ohne_doppelte_schluessel(self):
        json.loads(lies("package.json"), object_pairs_hook=_ohne_doppelte_schluessel)

    def test_pagefind_ist_einzige_produktionsabhaengigkeit_exakt(self):
        pkg = json.loads(lies("package.json"))
        self.assertEqual(pkg["dependencies"], {"pagefind": "1.5.2"},
                         "Deploy installiert mit --omit=dev: pagefind muss in dependencies stehen")
        self.assertNotIn("pagefind", pkg.get("devDependencies", {}),
                         "pagefind darf nicht zusätzlich als Dev-Abhängigkeit stehen")

    def test_build_schliesst_suchindex_mit_ein(self):
        pkg = json.loads(lies("package.json"))
        self.assertIn("npm run --silent suchindex", pkg["scripts"]["build"],
                      "Lokaler Build und Deploy-Build müssen denselben Suchindex liefern")

    def test_suchindex_leert_ausgabe_und_schliesst_anker_aus(self):
        pkg = json.loads(lies("package.json"))
        befehl = pkg["scripts"]["suchindex"]
        self.assertIn("rm -rf public/pagefind", befehl,
                      "alte Fragmente aus früheren Läufen dürfen nicht im Index landen")
        self.assertIn("--exclude-selectors 'a.anchor'", befehl,
                      "Anker-Zeichen „#“ dürfen nicht in den Auszügen stehen")

    def test_suchindex_ist_fail_closed_mit_wache(self):
        pkg = json.loads(lies("package.json"))
        self.assertIn("scripts/suchindex_check.py", pkg["scripts"]["suchindex"])
        self.assertIn("scripts/suchindex_check.py", pkg["scripts"]["test:suche"].replace(" --selftest", ""),
                      "test:suche prüft die Wache")
        self.assertIn("--selftest", pkg["scripts"]["test:suche"])

    def test_lockfile_passt_zu_package_json(self):
        pkg = json.loads(lies("package.json"))
        lock = json.loads(lies("package-lock.json"))
        wurzel = lock["packages"][""]
        self.assertEqual(wurzel.get("dependencies", {}), pkg.get("dependencies", {}))
        self.assertEqual(wurzel.get("devDependencies", {}), pkg.get("devDependencies", {}))
        self.assertFalse(lock["packages"]["node_modules/pagefind"].get("dev"),
                         "pagefind darf im Lock nicht als dev-only markiert sein")
        for name, eintrag in lock["packages"].items():
            if name.startswith("node_modules/@pagefind/"):
                self.assertFalse(eintrag.get("dev"), f"{name} ist im Lock dev-only")


class EinSuchOberflaeche(unittest.TestCase):
    """#644 brachte eine zweite Suche (pagefind-ui). Die Site hat genau eine: ff-suche."""

    def test_keine_pagefind_ui_reste_in_templates_css_und_skripten(self):
        for rel in ("layouts", "assets", "static/premium"):
            for pfad in (ROOT / rel).rglob("*"):
                if pfad.is_file() and pfad.suffix in {".html", ".css", ".js", ".mjs"}:
                    text = pfad.read_text(encoding="utf-8", errors="ignore")
                    self.assertNotIn("pagefind-ui", text,
                                     f"zweite Suchoberfläche in {pfad.relative_to(ROOT)}")

    def test_toter_such_layout_ordner_ist_entfernt(self):
        self.assertFalse((ROOT / "layouts" / "search").exists())
        self.assertFalse((ROOT / "assets" / "css" / "extended" / "zz-pagefind.css").exists())


class SuchseiteFrontMatter(unittest.TestCase):
    def test_suchseite_hat_kein_titelbild_damit_das_suchfeld_oben_steht(self):
        text = lies("content/suche/index.md")
        self.assertNotRegex(text, r"(?m)^cover\s*:",
                            "ein Titelbild schiebt das Suchfeld unter den Falz (Screenshot 08.10.2026)")

    def test_genau_ein_front_matter_block(self):
        text = lies("content/suche/index.md")
        self.assertTrue(text.startswith("---\n"), "Front Matter beginnt am Dateianfang")
        ende = text.index("\n---\n", 4)
        koerper = text[ende + len("\n---\n"):]
        self.assertNotRegex(
            koerper, r"(?m)^(title|description|layout|url|robotsNoIndex|sitemap|draft)\s*:",
            "Front-Matter-Reste im Fließtext (sichtbar auf der Seite, Merge-Fehler aus #644/#647)")


class SuchindexWache(unittest.TestCase):
    def _wache(self):
        spec = importlib.util.spec_from_file_location(
            "suchindex_check", ROOT / "scripts" / "suchindex_check.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_selbsttest_besteht_mit_sabotagen(self):
        fehler, proben = self._wache().selftest()
        self.assertEqual(fehler, [])
        self.assertGreaterEqual(proben, 13)

    def test_gebauter_stand_stimmt_wenn_vorhanden(self):
        public = ROOT / "public"
        if not (public / "pagefind" / "pagefind-entry.json").exists():
            self.skipTest("kein gebauter Stand (npm run build)")
        code, befunde, _ = self._wache().pruefe(public)
        self.assertEqual(code, 0, befunde)

    def test_e2e_spec_der_suche_liegt_vor(self):
        self.assertTrue((ROOT / "e2e" / "suche.spec.mjs").exists())

    def test_e2e_baut_den_index_selbst(self):
        """Der E2E-Job baut ohne npm run build – die Suite muss den Index selbst sicherstellen."""
        self.assertIn("globalSetup: './e2e/suchindex.setup.mjs'", lies("playwright.config.mjs"))
        setup = lies("e2e/suchindex.setup.mjs")
        self.assertIn("'suchindex'", setup)
        self.assertIn("E2E_ROOT", setup, "Varianten-Builds dürfen nicht überschrieben werden")


if __name__ == "__main__":
    unittest.main()
