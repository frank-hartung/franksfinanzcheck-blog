"""Hermetische Tests der Linkvorschläge (scripts/link_vorschlaege.py).

Der Kern dieser Tests ist eine Zusage: Dieses Werkzeug SCHREIBT NICHTS in
`content/`. Ein Vorschlag, der den Artikel schon verändert, ist kein
Vorschlag – und die Redaktion würde ihn nie wieder lesen. Zusätzlich werden
Sperrzonen, Selbstverlinkung, Deckel und CSV-Sicherheit geprüft.
"""
import os
import tempfile
import unittest

import scripts.link_vorschlaege as lv

BODY = (
    "Ein Absatz über Tagesgeld und Zinsen.\n\n"
    "[Schon verlinkt](../../posts/schon-da/).\n\n"
    "Hier steht ein Notgroschen im Text, später noch ein zweiter Notgroschen.\n\n"
    '{{< rechner typ="notgroschen" >}}\n'
)


def seite(titel="Tagesgeld Ratgeber", keywords=None, tags=None, body=BODY, pfad="content/posts/q/index.md"):
    return {"title": titel, "keywords": keywords or ["tagesgeld", "zinsen"],
            "tags": tags or ["konto"], "body": body, "score": 60, "path": pfad}


def lage():
    pages = {
        "q": seite(),
        "schon-da": seite("Schon da", ["tagesgeld"], [], "", pfad="content/posts/schon-da/index.md"),
        "notgroschen": seite("Notgroschen aufbauen", ["notgroschen"], ["konto"], "",
                             pfad="content/posts/notgroschen/index.md"),
        "fremd": seite("Fremdes Thema", ["mietwagen"], ["reisen"], "",
                       pfad="content/posts/fremd/index.md"),
    }
    graph = {
        "schon-da": {"eingehend": 0, "cornerstone": False},
        "notgroschen": {"eingehend": 0, "cornerstone": True},
    }
    kandidaten = [
        ("tagesgeld", "schon-da", 70),      # bereits verlinkt
        ("notgroschen", "notgroschen", 70),  # frei im Fließtext
        ("rechner", "notgroschen", 70),      # nur im Shortcode
        ("mietwagen", "fremd", 50),          # kein Bezug, niedriger Score
    ]
    return pages, graph, kandidaten


class VorschlagTests(unittest.TestCase):
    def vorschlaege(self, **kwargs):
        pages, graph, kandidaten = lage()
        return lv.bewerte("q", pages["q"], kandidaten, pages, graph, **kwargs)

    def test_bereits_verlinktes_ziel_wird_nicht_vorgeschlagen(self):
        self.assertNotIn("schon-da", [v["ziel"] for v in self.vorschlaege()])

    def test_selbstverlinkung_und_fremdthema_entfallen(self):
        ziele = [v["ziel"] for v in self.vorschlaege()]
        self.assertNotIn("q", ziele)
        self.assertNotIn("fremd", ziele)

    def test_shortcode_ist_sperrzone(self):
        anker = [v["anker"].lower() for v in self.vorschlaege()]
        self.assertNotIn("rechner", anker)

    def test_markdown_ist_einfuegefertig(self):
        v = next(v for v in self.vorschlaege() if v["ziel"] == "notgroschen")
        self.assertEqual(v["markdown"], "[Notgroschen](../../posts/notgroschen/)")
        self.assertEqual(v["ziel_url"], "/posts/notgroschen/")

    def test_gruende_nennen_cornerstone_und_verwaist(self):
        v = next(v for v in self.vorschlaege() if v["ziel"] == "notgroschen")
        self.assertTrue(any("Cornerstone" in g for g in v["gruende"]))
        self.assertTrue(any("eingehenden Link" in g for g in v["gruende"]))
        self.assertGreater(v["score"], 100)

    def test_begrenzung_und_deckel(self):
        pages, graph, kandidaten = lage()
        begrenzt = lv.bewerte("q", pages["q"], kandidaten, pages, graph, max_vorschlaege=1)
        self.assertEqual(len(begrenzt), 1)
        voll = seite(body="\n\n".join(f"[a{i}](../../posts/z{i}/)" for i in range(9))
                     + "\n\nEin Notgroschen im Text.\n")
        am_deckel = lv.bewerte("voll", voll, [("notgroschen", "notgroschen", 70)],
                               {**pages, "voll": voll}, graph)
        self.assertTrue(am_deckel[0]["deckel_erreicht"])
        self.assertIn("deckel", am_deckel[0]["hinweis"].lower())

    def test_verwaist_filter(self):
        pages, kandidaten = lage()[0], lage()[2]
        graph = {"notgroschen": {"eingehend": 4, "cornerstone": False},
                 "schon-da": {"eingehend": 0, "cornerstone": False}}
        self.assertEqual(lv.bewerte("q", pages["q"], kandidaten, pages, graph,
                                    nur_verwaiste=True), [])

    def test_csv_neutralisiert_formeln_und_haelt_markdown(self):
        v = next(v for v in self.vorschlaege() if v["ziel"] == "notgroschen")
        with tempfile.TemporaryDirectory() as tmp:
            ziel = os.path.join(tmp, "v.csv")
            lv.schreibe_csv([dict(v, anker='=HYPERLINK("http://x")')], ziel)
            with open(ziel, encoding="utf-8-sig") as fh:
                inhalt = fh.read()
        self.assertIn("'=HYPERLINK", inhalt)
        self.assertIn("../../posts/notgroschen/", inhalt)

    def test_bericht_sagt_dass_er_nichts_aendert(self):
        md = lv.bericht_md(self.vorschlaege())
        self.assertIn("Diese Liste ändert nichts", md)
        self.assertIn("../../posts/notgroschen/", md)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(lv.selftest(), 0)

    @unittest.skipUnless(os.path.isdir("content/posts"), "kein Repo-Inhalt vorhanden")
    def test_lauf_im_repo_schreibt_keine_inhalte(self):
        """Der echte Lauf über den Bestand darf keine Artikel anfassen."""
        dateien = []
        for dp, _, fs in os.walk("content"):
            dateien += [os.path.join(dp, f) for f in fs if f.endswith(".md")]
        vorher = {d: (os.path.getmtime(d), os.path.getsize(d)) for d in dateien}
        vorschlaege = lv.erzeuge(max_vorschlaege=1)
        nachher = {d: (os.path.getmtime(d), os.path.getsize(d)) for d in dateien}
        self.assertEqual(vorher, nachher)
        self.assertTrue(all(v["markdown"].startswith("[") for v in vorschlaege))


if __name__ == "__main__":
    unittest.main()
