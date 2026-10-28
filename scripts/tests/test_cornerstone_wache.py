"""Hermetische Tests der Cornerstone-Wache (scripts/cornerstone_wache.py).

Sie prüfen die Regeln an einem Mini-Repo im Temp-Verzeichnis: kein Hugo,
kein Netz, keine echten Inhalte. Der wichtigste Fall ist die ZÄHLUNG – ein
Selbstverweis darf einen Cornerstone nicht künstlich verlinkt aussehen
lassen, und zwei Linkformen derselben Quelle sind EIN eingehender Link.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import scripts.cornerstone_wache as cw
import scripts.seo_cockpit as seo

GUT = ("keywords_fokus: [\"strom sparen\"]\n"
       "kurzantwort: \"Kurz.\"\n"
       "quellen:\n  - titel: \"Q\"\n    url: \"https://example.org\"\n"
       "cover:\n  image: \"x.jpg\"\n  alt: \"Alt\"\n")


def artikel(titel, links="", extra="", datum="2026-10-01", draft=False, pillar="strom"):
    return (f'---\ntitle: "{titel}"\ndescription: "Beschreibung"\ndate: {datum}\n'
            f'lastmod: {datum}\ndraft: {"true" if draft else "false"}\n'
            f'pillar: "{pillar}"\n{extra}---\n\nText.\n\n{links}\n')


class CornerstoneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def schreibe(self, slug, text):
        ordner = os.path.join(self.root, "content", "posts", slug)
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, "index.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def quellen(self, ziel, anzahl, pillar="strom"):
        for i in range(anzahl):
            self.schreibe(f"quelle-{ziel}-{i}",
                          artikel(f"Quelle {i}", links=f"[Ziel](/posts/{ziel}/)",
                                  pillar=f"{pillar}{i % 2}"))

    def pruefe(self, **kwargs):
        return cw.pruefe(self.root, heute="2026-10-28", **kwargs)

    def regeln(self, stand=None):
        stand = stand or self.pruefe()
        return {(b["slug"], b["regel"]) for b in stand["befunde"]}

    def test_sauberer_cornerstone_ohne_befund(self):
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: true\n"))
        self.quellen("ziel", 5)
        stand = self.pruefe()
        self.assertEqual([b for b in stand["befunde"] if b["slug"] == "ziel"], [])

    def test_zu_wenig_eingehende_links(self):
        self.schreibe("ziel", artikel("Ziel", links="[Selbst](/posts/ziel/)",
                                      extra=GUT + "cornerstone: true\n"))
        self.quellen("ziel", 2)  # 2 < 5, Selbstverweis zählt nicht
        regeln = self.regeln()
        self.assertIn(("ziel", "C3"), regeln)
        self.assertEqual(self.pruefe()["seiten"]["ziel"]["eingehend"], 2)

    def test_selbstverweis_zaehlt_nicht_und_doppelte_linkform_auch_nicht(self):
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: true\n"))
        self.schreibe("eine-quelle", artikel(
            "Quelle", links="[A](/posts/ziel/) [B](../../posts/ziel/) "
                            "[C](https://franksfinanzcheck.de/posts/ziel/)"))
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: true\n",
                                      links="[Selbst](/posts/ziel/)"))
        seite = self.pruefe()["seiten"]["ziel"]
        # Eine Quelle, drei Linkformen = EIN eingehender Link.
        self.assertEqual(seite["eingehend"], 1)

    def test_veralteter_cornerstone(self):
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: true\n",
                                      datum="2025-01-01"))
        self.quellen("ziel", 5)
        self.assertIn(("ziel", "C4"), self.regeln())

    def test_unvollstaendig_und_fehlende_hauptintention(self):
        self.schreibe("ziel", artikel("Ziel", extra="cornerstone: true\n"))
        self.quellen("ziel", 5)
        befunde = [b for b in self.pruefe()["befunde"] if b["slug"] == "ziel"]
        # keywords_fokus, kurzantwort, quellen, cover.alt → vier C5-Befunde
        self.assertEqual(len([b for b in befunde if b["regel"] == "C5"]), 4)

    def test_draft_ist_kein_cornerstone(self):
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: true\n", draft=True))
        self.quellen("ziel", 5)
        self.assertIn(("ziel", "C2"), self.regeln())

    def test_string_flag_wird_als_datenfehler_gemeldet(self):
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: \"ja\"\n"))
        self.quellen("ziel", 5)
        befunde = [b for b in self.pruefe()["befunde"] if b["regel"] == "C1"]
        self.assertEqual(len(befunde), 1)
        self.assertIn("Boolean", befunde[0]["massnahme"])

    def test_kandidaten_nur_ohne_markierung_und_ohne_draft(self):
        self.schreibe("kandidat", artikel("Kandidat"))
        self.quellen("kandidat", 5)
        self.schreibe("draft-kandidat", artikel("Draft", draft=True))
        self.quellen("draft-kandidat", 6)
        self.schreibe("markiert", artikel("Markiert", extra=GUT + "cornerstone: true\n"))
        self.quellen("markiert", 7)
        slugs = {k["slug"] for k in self.pruefe()["kandidaten"]}
        self.assertIn("kandidat", slugs)
        self.assertNotIn("draft-kandidat", slugs)
        self.assertNotIn("markiert", slugs)

    def test_bericht_ist_ehrlich_und_paste_fertig(self):
        self.schreibe("kandidat", artikel("Kandidat"))
        self.quellen("kandidat", 5)
        md = cw.bericht_md(self.pruefe())
        self.assertIn("cornerstone: true", md)
        self.assertIn("Bekenntnis mit Folgen", md)

    def test_pruefung_schreibt_nichts(self):
        self.schreibe("ziel", artikel("Ziel", extra=GUT + "cornerstone: true\n"))
        self.quellen("ziel", 5)
        dateien = {os.path.join(dp, f) for dp, _, fs in os.walk(self.root) for f in fs}
        vorher = {d: os.path.getmtime(d) for d in dateien}
        self.pruefe()
        nachher = {d: os.path.getmtime(d) for d in dateien}
        self.assertEqual(vorher, nachher)

    def test_selbsttest_laeuft_gruen(self):
        self.assertEqual(cw.selftest(), 0)

    def test_cockpit_uebernimmt_befunde_nur_fuer_gebauten_seiten(self):
        """Die Brücke ins SEO-Cockpit: Regel-ID → Befund-Code, nur für
        Seiten, die im Build wirklich existieren. Sonst entstünden im
        Cockpit Befunde für URLs, die der Build gar nicht kennt."""
        stand = {
            "seiten": {"a": {"datei": "content/posts/a/index.md"},
                       "b": {"datei": "content/posts/b/index.md"}},
            "befunde": [{"slug": "a", "regel": "C3", "schwere": "P1",
                         "text": "zu wenig Links", "massnahme": "verlinken"},
                        {"slug": "b", "regel": "C4", "schwere": "P2",
                         "text": "alt", "massnahme": "aktualisieren"}],
            "kandidaten": [{"slug": "a", "eingehend": 7}],
        }
        gesammelt = []
        with patch.object(seo, "cornerstone_stand", return_value=stand):
            seo.add_cornerstone_findings(
                lambda url, code, schwere, detail, aktion, besitzer: gesammelt.append(
                    (url, code, schwere)), [{"path": "/posts/a/"}])
        self.assertEqual([(u, c) for u, c, _ in gesammelt],
                         [("/posts/a/", "cornerstone-eingehend"),
                          ("/posts/a/", "cornerstone-kandidat")])
        self.assertTrue(all(u == "/posts/a/" for u, _, _ in gesammelt))

    def test_cockpit_ohne_cornerstone_daten_crasht_nicht(self):
        gesammelt = []
        with patch.object(seo, "cornerstone_stand", return_value=None):
            seo.add_cornerstone_findings(lambda *a: gesammelt.append(a),
                                         [{"path": "/posts/a/"}])
        self.assertEqual(gesammelt, [])


if __name__ == "__main__":
    unittest.main()
