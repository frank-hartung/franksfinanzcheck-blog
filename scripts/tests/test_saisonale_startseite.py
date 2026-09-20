#!/usr/bin/env python3
"""Vertragstests für die saisonale Startseite (data/saisons.yaml + Wache).

Warum diese Datei existiert:
  Die saisonale Startseite hat drei Stellen, die still auseinanderlaufen
  können – die kuratierte Quelle (data/saisons.yaml), die Template-Logik
  (layouts/_partials/_funcs/saison-*.html) und die Farbwelt
  (assets/css/extended/zz-saisonale-startseite.css). Dazu kommt eine
  Datums-Logik mit einem echten Sonderfall (Winter über den Jahreswechsel)
  und eine Auswahl-Logik, deren Sortierung in Hugo schon einmal gekippt ist
  (zwei verkettete `sort`-Aufrufe sortieren die GESAMTE Liste neu – am
  20.09.2026 im Build beobachtet: statt der relevantesten kamen die
  neuesten Artikel).

  Diese Tests frieren beide Lehren ein und halten die Wache
  (scripts/saisonale_startseite_guard.py) selbst testbar: Ein Gate, das
  nie rot war, ist kein Gate.

Deterministisch: alle Zeitangaben relativ zur echten Uhr (Lehre aus
test_affiliate_freshness.py), alle Negativ-Fälle in temporären
Verzeichnissen – kein Test schreibt ins Repo.
"""
from __future__ import annotations

import datetime
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import saisonale_startseite_guard as wache  # noqa: E402

ROOT = wache.ROOT
VIER_SAISONS = [
    {"id": "herbst", "ab": "09-01", "bis": "11-30"},
    {"id": "winter", "ab": "12-01", "bis": "02-29"},
    {"id": "fruehling", "ab": "03-01", "bis": "05-31"},
    {"id": "sommer", "ab": "06-01", "bis": "08-31"},
]


def artikel(slug: str, *, titel: str, pillar: str, zeit: float,
            tags=None, keywords=None, beschreibung: str = "",
            draft: bool = False, datum: str = "2026-09-10") -> dict:
    """Artikel-Dict in der Form, die wache.auswahl() erwartet."""
    blob = " {} | {} | {} | {} | {} ".format(
        titel.lower(), beschreibung.lower(),
        " ".join(tags or []).lower(), " ".join(keywords or []).lower(),
        f"/posts/{slug}/".lower(),
    )
    return {"pfad": None, "slug": slug, "titel": titel, "pillar": pillar,
            "datum": datetime.date.fromisoformat(datum), "zeit": zeit,
            "blob": blob, "href": f"/posts/{slug}/", "draft": draft}


class TestFensterLogik(unittest.TestCase):
    """S2 – Datums-Fenster inkl. Jahreswechsel und Schalttag."""

    def test_schluessel_ohne_oktal_falle(self):
        # „09" ist in Go wie in Python ein Oktal-Kandidat – genau daran
        # starb der erste Build (strconv: invalid syntax).
        self.assertEqual(wache.fenster_schluessel("09-01"), 901)
        self.assertEqual(wache.fenster_schluessel("08-31"), 831)
        self.assertEqual(wache.fenster_schluessel("12-01"), 1201)
        self.assertEqual(wache.fenster_schluessel("02-29"), 229)

    def test_grenztage(self):
        faelle = {
            "2026-08-31": "sommer", "2026-09-01": "herbst", "2026-09-20": "herbst",
            "2026-11-30": "herbst", "2026-12-01": "winter", "2026-12-31": "winter",
            "2027-01-01": "winter", "2027-02-28": "winter", "2028-02-29": "winter",
            "2027-03-01": "fruehling", "2027-05-31": "fruehling", "2027-06-01": "sommer",
        }
        for datum, soll in faelle.items():
            with self.subTest(datum=datum):
                ist = wache.saison_fuer(datetime.date.fromisoformat(datum), VIER_SAISONS)
                self.assertIsNotNone(ist, f"{datum} fällt in keine Saison")
                self.assertEqual(ist["id"], soll)

    def test_alle_366_tage_lueckenlos(self):
        self.assertEqual(wache.kalender_abdeckung(VIER_SAISONS), [])

    def test_luecke_wird_gefunden(self):
        ohne_sommer = [s for s in VIER_SAISONS if s["id"] != "sommer"]
        funde = wache.kalender_abdeckung(ohne_sommer)
        self.assertTrue(funde)
        # Die Wache kappt lange Fundlisten (gleiche Ursache) – geprüft wird
        # deshalb der BEGINN des fehlenden Fensters, nicht ein Tag mittendrin.
        self.assertTrue(any("Lücke" in f and "2028-06-01" in f for f in funde),
                        f"der Juni muss als erster Lücken-Tag auffallen: {funde[:3]}")
        self.assertTrue(any("unterdrückt" in f for f in funde),
                        "lange Fundlisten müssen als gekappt kenntlich bleiben")

    def test_ueberlappung_wird_gefunden(self):
        doppelt = VIER_SAISONS + [{"id": "herbst", "ab": "09-01", "bis": "11-30"}]
        funde = wache.kalender_abdeckung(doppelt)
        self.assertTrue(any("Überlappung" in f for f in funde), funde[:3])

    def test_heute_ist_abgedeckt(self):
        daten, fehler = wache.quelle_laden(ROOT)
        self.assertEqual(fehler, [])
        saisons, schema_fehler = wache.validate_schema(daten)
        self.assertEqual(schema_fehler, [])
        heute = datetime.datetime.now(datetime.timezone.utc).date()
        self.assertIsNotNone(wache.saison_fuer(heute, saisons),
                             f"{heute} liegt in keiner Saison der echten Quelle")


class TestSchemaUndTon(unittest.TestCase):
    """S1/S3 – Schema-Pflichten und Marken-Stimme."""

    def test_reale_quelle_ist_sauber(self):
        daten, fehler = wache.quelle_laden(ROOT)
        self.assertEqual(fehler, [])
        saisons, funde = wache.validate_schema(daten)
        self.assertEqual(funde, [], f"Schema-Funde: {funde}")
        self.assertEqual(sorted(s["id"] for s in saisons), sorted(wache.SAISON_IDS))
        self.assertEqual(wache.validate_stimme(saisons), [])
        self.assertEqual(wache.validate_pillars(saisons, ROOT), [])

    def test_formelle_anrede_ist_ein_fund(self):
        saisons = [{"id": "herbst", "name": "Herbst", "emoji": "🍂",
                    "zeitraum": "1. September bis 30. November",
                    "badge": "Herbst-Check", "headline": "Heizsaison",
                    "hinweis": "Prüfen Sie jetzt Ihre Verträge.",
                    "tipp": "Tipp", "pillar_link": "Zum Ratgeber",
                    "saison_pillars": ["strom-sparen"],
                    "keywords": ["a", "b", "c", "d"], "min_artikel": 3,
                    "akzent": "#9A5B12", "akzent_dunkel": "#E9A94C",
                    "hero_text": "#FFD15A", "linie": "#B26A00",
                    "linie_dunkel": "#E9A94C"}]
        funde = wache.validate_stimme(saisons)
        self.assertTrue(any("formelle Anrede" in f for f in funde), funde)

    def test_floskel_ist_ein_fund(self):
        saisons = [dict(VIER_SAISONS[0], hinweis="In der heutigen Zeit lohnt sich ein Check.")]
        self.assertTrue(any("Floskel" in f for f in wache.validate_stimme(saisons)))

    def test_grossgeschriebene_keywords_werden_abgelehnt(self):
        daten = {"saisons": [dict(VIER_SAISONS[0], name="Herbst", emoji="🍂",
                                  zeitraum="x", badge="b", headline="h", hinweis="i",
                                  tipp="t", pillar_link="p", saison_pillars=["strom-sparen"],
                                  keywords=["Heizkosten", "gas", "herbst", "winter"],
                                  min_artikel=3, akzent="#9A5B12", akzent_dunkel="#E9A94C",
                                  hero_text="#FFD15A", linie="#B26A00",
                                  linie_dunkel="#E9A94C")]}
        _, funde = wache.validate_schema(daten)
        self.assertTrue(any("klein geschrieben" in f for f in funde), funde)

    def test_badge_laenge_begrenzt(self):
        daten = {"saisons": [dict(VIER_SAISONS[0], name="Herbst", emoji="🍂",
                                  zeitraum="x", badge="x" * 60, headline="h", hinweis="i",
                                  tipp="t", pillar_link="p", saison_pillars=["strom-sparen"],
                                  keywords=["a", "b", "c", "d"], min_artikel=3,
                                  akzent="#9A5B12", akzent_dunkel="#E9A94C",
                                  hero_text="#FFD15A", linie="#B26A00",
                                  linie_dunkel="#E9A94C")]}
        _, funde = wache.validate_schema(daten)
        self.assertTrue(any("badge" in f and "52" in f for f in funde), funde)


class TestFarben(unittest.TestCase):
    """S4 – WCAG gemessen, nicht geraten."""

    def test_referenzwerte(self):
        self.assertEqual(wache.kontrast("#000000", "#FFFFFF"), 21.0)
        self.assertAlmostEqual(wache.kontrast("#767676", "#FFFFFF"), 4.54, delta=0.05)
        # PRODUCT.md: Signalgelb ist auf hellem Grund 1.79:1 → nie Textfarbe.
        self.assertLess(wache.kontrast("#FFB300", "#FFFFFF"), 2.0)

    def test_reale_palette_besteht(self):
        daten, _ = wache.quelle_laden(ROOT)
        saisons, _ = wache.validate_schema(daten)
        self.assertEqual(wache.validate_farben(saisons), [])

    def test_gelber_text_auf_weiss_fliegt_auf(self):
        saison = dict(VIER_SAISONS[0], akzent="#FFB300", akzent_dunkel="#FFD15A",
                      hero_text="#FFD15A", linie="#FFB300", linie_dunkel="#FFB300")
        funde = wache.validate_farben([saison])
        self.assertTrue(any("akzent" in f and "Weiß" in f for f in funde), funde)
        self.assertTrue(any("linie" in f for f in funde), funde)


class TestCssDeckung(unittest.TestCase):
    """S5 – YAML und CSS sind EINE Wahrheit."""

    def css(self, *, akzent="#9A5B12", linie="#B26A00", hero="#FFD15A",
            dunkel_akzent="#E9A94C", dunkel_linie="#E9A94C", auto_gleich=True):
        auto = (f'{dunkel_akzent}', f'{dunkel_linie}') if auto_gleich else ("#123456", "#123456")
        return (
            f".ff-saison--herbst {{ --ff-saison-akzent: {akzent}; --ff-saison-linie: {linie}; "
            f"--ff-saison-hero-text: {hero}; }}\n"
            f':root[data-theme="dark"] .ff-saison--herbst {{ --ff-saison-akzent: {dunkel_akzent}; '
            f"--ff-saison-linie: {dunkel_linie}; }}\n"
            f"@media (prefers-color-scheme: dark) {{ :root[data-theme=\"auto\"] "
            f".ff-saison--herbst {{ --ff-saison-akzent: {auto[0]}; --ff-saison-linie: {auto[1]}; }} }}\n"
            "@media (max-width: 768px) { main.main > section.ff-saison { order: 5 } }\n"
            "@media (prefers-reduced-motion: reduce) { .ff-saison-card { transition: none } }\n"
        )

    SAISON = {"id": "herbst", "akzent": "#9A5B12", "akzent_dunkel": "#E9A94C",
              "hero_text": "#FFD15A", "linie": "#B26A00", "linie_dunkel": "#E9A94C"}

    def test_deckung_ok(self):
        self.assertEqual(wache.validate_css_parity([self.SAISON], self.css()), [])

    def test_reale_css_datei_ist_deckungsgleich(self):
        daten, _ = wache.quelle_laden(ROOT)
        saisons, _ = wache.validate_schema(daten)
        css = wache.CSS_DATEI.read_text(encoding="utf-8")
        self.assertEqual(wache.validate_css_parity(saisons, css), [])
        self.assertEqual(wache.validate_lcp_schutz(css), [])

    def test_drift_wird_gefunden(self):
        funde = wache.validate_css_parity([self.SAISON], self.css(linie="#000000"))
        self.assertTrue(any("CSS-Drift" in f for f in funde), funde)

    def test_dark_auto_pfad_muss_da_sein(self):
        ohne_auto = self.css().replace(
            '@media (prefers-color-scheme: dark) { :root[data-theme="auto"] '
            '.ff-saison--herbst { --ff-saison-akzent: #E9A94C; --ff-saison-linie: #E9A94C; } }\n', "")
        funde = wache.validate_css_parity([self.SAISON], ohne_auto)
        self.assertTrue(any("noscript" in f for f in funde), funde)

    def test_unterschiedliche_dark_pfade_werden_gefunden(self):
        funde = wache.validate_css_parity([self.SAISON], self.css(auto_gleich=False))
        self.assertTrue(any("zwei Wahrheiten" in f for f in funde), funde)

    def test_order_regel_wird_geprueft(self):
        self.assertTrue(wache.validate_lcp_schutz(".ff-saison { color: red; }"))
        self.assertTrue(any("order: 0" in f for f in wache.validate_lcp_schutz(
            "@media (max-width: 768px) { main.main > section.ff-saison { order: 0 } } "
            "@media (prefers-reduced-motion: reduce) {}")))
        self.assertTrue(wache.validate_lcp_schutz(
            "@media (max-width: 768px) { main.main > section.ff-saison { order: 6 } } "
            "@media (prefers-reduced-motion: reduce) {}"))


class TestAuswahlSpiegel(unittest.TestCase):
    """S7 – Relevanz vor Datum, dazu beide Fallback-Stufen."""

    def test_relevanz_schlaegt_datum(self):
        bestand = [
            artikel("alt-aber-passend", titel="Heizkosten senken", pillar="strom-sparen",
                    zeit=100.0, tags=["Heizkosten"], keywords=["Gas", "Herbst"], datum="2026-08-01"),
            # bewusst OHNE Keyword-Treffer („Heizung" ≠ „heizkosten") –
            # newest darf nicht allein wegen des Datums gewinnen
            artikel("neu-ohne-treffer", titel="Heizung", pillar="strom-sparen",
                    zeit=900.0, datum="2026-09-18"),
            artikel("neu-und-passend", titel="Gasrechnung im Herbst", pillar="strom-sparen",
                    zeit=800.0, keywords=["Gas", "Herbst"], datum="2026-09-17"),
        ]
        saison = {"id": "herbst", "keywords": ["heizkosten", "gas", "herbst"],
                  "saison_pillars": ["strom-sparen"], "min_artikel": 2}
        aus, quelle, kandidaten = wache.auswahl(saison, bestand, 2)
        self.assertEqual(quelle, "keywords")
        self.assertEqual(kandidaten, 2)
        self.assertEqual([a["href"] for a in aus],
                         ["/posts/alt-aber-passend/", "/posts/neu-und-passend/"])

    def test_gleichstand_wird_ueber_datum_gebrochen(self):
        bestand = [
            artikel("a", titel="Gas", pillar="strom-sparen", zeit=500.0, datum="2026-09-05"),
            artikel("b", titel="Gas", pillar="strom-sparen", zeit=700.0, datum="2026-09-07"),
        ]
        aus, quelle, _ = wache.auswahl(
            {"id": "winter", "keywords": ["gas"], "saison_pillars": [], "min_artikel": 1},
            bestand, 1)
        self.assertEqual(quelle, "keywords")
        self.assertEqual(aus[0]["href"], "/posts/b/")

    def test_fallback_auf_saison_pillars(self):
        bestand = [
            artikel("a", titel="Budget", pillar="frugalismus", zeit=300.0, datum="2026-09-03"),
            artikel("b", titel="Konto", pillar="konto-karten", zeit=500.0, datum="2026-09-05"),
            artikel("c", titel="Notgroschen", pillar="frugalismus", zeit=400.0, datum="2026-09-04"),
        ]
        aus, quelle, _ = wache.auswahl(
            {"id": "fruehling", "keywords": ["gibt-es-nicht"],
             "saison_pillars": ["frugalismus"], "min_artikel": 2}, bestand, 2)
        self.assertEqual(quelle, "pillar")
        self.assertEqual([a["href"] for a in aus], ["/posts/c/", "/posts/a/"])

    def test_letzte_stufe_neueste_artikel(self):
        bestand = [artikel("x", titel="Irgendwas", pillar="mietwagen", zeit=zeit,
                           datum="2026-09-01") for zeit, _ in [(1.0, 0), (2.0, 0)]]
        aus, quelle, _ = wache.auswahl(
            {"id": "sommer", "keywords": [], "saison_pillars": ["konto-karten"],
             "min_artikel": 2}, bestand, 2)
        self.assertEqual(quelle, "neueste")
        self.assertEqual(len(aus), 2)

    def test_alle_vier_saisons_finden_genug_aus_dem_bestand(self):
        """Integration gegen den echten Bestand: keine Saison darf auf eine
        Fallback-Stufe angewiesen sein (sonst passt die Kuratierung nicht
        zum Bestand – genau das soll die Wache melden)."""
        daten, _ = wache.quelle_laden(ROOT)
        saisons, _ = wache.validate_schema(daten)
        bestand = wache.live_artikel(ROOT)
        self.assertGreater(len(bestand), 10, "Content-Bestand fehlt – Test sinnlos")
        for saison in saisons:
            with self.subTest(saison=saison["id"]):
                mindest = int(saison.get("min_artikel") or 3)
                aus, quelle, _ = wache.auswahl(saison, bestand, mindest)
                self.assertEqual(quelle, "keywords",
                                 f"Saison {saison['id']} fällt auf {quelle} zurück")
                self.assertEqual(len(aus), mindest)
                self.assertEqual(len({a["href"] for a in aus}), mindest,
                                 "dieselbe Karte mehrfach ausgewählt")


class TestBestandsLeser(unittest.TestCase):
    """Der Spiegel muss denselben Bestand sehen wie das Template."""

    def test_drafts_index_und_versteckte_zaehlen_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            posts = root / "content" / "posts"
            (posts / "live").mkdir(parents=True)
            (posts / "live" / "index.md").write_text(
                '---\ntitle: "Live"\ndate: 2026-09-10\npillar: "strom-sparen"\n---\nText\n',
                encoding="utf-8")
            (posts / "draft").mkdir()
            (posts / "draft" / "index.md").write_text(
                '---\ntitle: "Draft"\ndate: 2026-09-11\ndraft: true\n---\nText\n', encoding="utf-8")
            (posts / "versteckt").mkdir()
            (posts / "versteckt" / "index.md").write_text(
                '---\ntitle: "Versteckt"\ndate: 2026-09-12\nhiddenInHomeList: "true"\n---\nText\n',
                encoding="utf-8")
            (posts / "_index.md").write_text(
                '---\ntitle: "Alle Ratgeber"\ndate: 2026-09-13\n---\nSektion\n', encoding="utf-8")
            bestand = wache.live_artikel(root)
            self.assertEqual([a["slug"] for a in bestand], ["live"],
                             "nur der LIVE-Artikel ohne hiddenInHomeList darf zählen")
            self.assertEqual(bestand[0]["href"], "/posts/live/")
            self.assertIn("live", bestand[0]["blob"])


class TestDatenpfadUndBuild(unittest.TestCase):
    """B6/B3 – dokumentierter Build-Killer und Render-Beweis."""

    def test_site_data_im_layout_wird_gefunden(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "t.html"
            pfad.write_text("{{/* site.Data ist verboten */}}\n{{ with site.Data.x }}y{{ end }}\n",
                            encoding="utf-8")
            self.assertTrue(wache.validate_datenpfad([pfad]))
            pfad.write_text("{{/* nur ein Kommentar über hugo.Data */}}\n<p>ok</p>\n",
                            encoding="utf-8")
            self.assertEqual(wache.validate_datenpfad([pfad]), [])

    def test_neue_layouts_fassen_kein_site_data_an(self):
        self.assertEqual(wache.validate_datenpfad(list(wache.LAYOUTS)), [])

    def test_build_pruefung_an_synthetischem_html(self):
        # Hinweis: SICHTBARKEIT (display:none) prüft der HTMLParser bewusst
        # nicht – das ist die Aufgabe von e2e/saisonale-startseite.spec.mjs
        # im echten Browser.
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            (public / "posts" / "a").mkdir(parents=True)
            (public / "posts" / "a" / "index.html").write_text("<html></html>", encoding="utf-8")
            (public / "pillar" / "strom-sparen").mkdir(parents=True)
            (public / "pillar" / "strom-sparen" / "index.html").write_text("x", encoding="utf-8")
            gut = (
                "<html><body><main class=main>"
                "<article class='first-entry home-info'><h1>Start</h1>"
                "<div class='ff-saison-badge ff-saison--herbst' data-ff-saison=herbst>Herbst-Check</div>"
                "<p class='ff-saison-hinweis' data-ff-saison=herbst>Die Heizsaison startet.</p></article>"
                "<div class=ff-pinterest-cta></div>"
                "<section class='ff-saison ff-saison--herbst' data-ff-saison=herbst "
                "data-ff-saison-quelle=keywords data-ff-saison-treffer=1>"
                "<a class=ff-saison-pillar href=/pillar/strom-sparen/ data-umami-event=cta_click>"
                "Zum Ratgeber</a>"
                "<a class=ff-saison-card href=/posts/a/ data-umami-event=cta_click "
                "data-umami-event-placement=start-saison data-umami-event-saison=herbst "
                "data-umami-event-slug=saison-herbst-a aria-labelledby=a-title>"
                "<span class=ff-saison-card-titel id=a-title>Artikel A</span></a>"
                "</section><article class='post-entry lcp-card'></article></main>"
                "<style>.ff-saison-card{}.ff-saison--herbst{}</style></body></html>"
            )
            saison = {"id": "herbst", "badge": "Herbst-Check",
                      "hinweis": "Die Heizsaison startet."}
            (public / "index.html").write_text(gut, encoding="utf-8")
            self.assertEqual(wache.validate_build(public, saison, [{"href": "/posts/a/"}],
                                                  "keywords", 1), [])
            for name, variante, erwartung in [
                ("toter Link", gut.replace("/posts/a/", "/posts/fehlt/"), "ins Leere"),
                ("falsche Saison", gut.replace("data-ff-saison=herbst", "data-ff-saison=sommer"), "B2"),
                ("zwei H1", gut.replace("<h1>Start</h1>", "<h1>Start</h1><h1>zwei</h1>"), "B1"),
                ("ohne Messkette", gut.replace("data-umami-event-placement=start-saison", ""), "B4"),
                ("Karte ohne Titel", gut.replace(">Artikel A</span>", "></span>"), "B3"),
                ("Block ohne Auswahl-Quelle", gut.replace("data-ff-saison-quelle=keywords",
                                                           "data-ff-saison-quelle=neueste"), "B2"),
            ]:
                with self.subTest(fall=name):
                    (public / "index.html").write_text(variante, encoding="utf-8")
                    funde = wache.validate_build(public, saison, [{"href": "/posts/a/"}],
                                                 "keywords", 1)
                    self.assertTrue(funde, f"{name} blieb unbemerkt")
                    self.assertTrue(any(erwartung in f for f in funde), funde)

    def test_fehlender_build_ist_ein_fehler_kein_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            funde = wache.validate_build(Path(tmp), {"id": "herbst"}, [], "keywords", 3)
            self.assertTrue(any("Build fehlt" in f for f in funde), funde)

    @unittest.skipUnless((ROOT / "public" / "index.html").is_file(),
                         "public/ fehlt – vorher `hugo --destination public`")
    def test_echter_build_ist_kohärent(self):
        """End-to-End gegen den echten Build (lokal/CI, sonst übersprungen)."""
        heute = datetime.datetime.now(datetime.timezone.utc).date()
        exit_code, bericht = wache.pruefe_build(ROOT / "public", ROOT, heute)
        self.assertEqual(bericht["fehler"], [])
        self.assertEqual(exit_code, 0)


class TestGesamtlauf(unittest.TestCase):
    def test_quellen_pruefung_ist_gruen(self):
        heute = datetime.datetime.now(datetime.timezone.utc).date()
        exit_code, bericht = wache.pruefe_quelle(ROOT, heute)
        self.assertEqual(bericht["fehler"], [], bericht["fehler"][:4])
        self.assertEqual(exit_code, 0)

    def test_selbsttest_des_gates_ist_gruen(self):
        self.assertEqual(wache.selbsttest(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
