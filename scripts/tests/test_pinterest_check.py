"""Regressionstests des Pinterest-Checks – P11 (Link-Dichte) und P8 (#729).

P8 hatte bis zum 13.10.2026 keinen Heiler: Der Watchdog meldete denselben
Text jeden Tag neu, das Issue konnte nie zugehen („Befund ohne
Schließpfad"). Diese Datei friert beide Hälften ein – Erkennung UND
Heilung – und den Sonderfall, dass der Build in demselben Lauf noch den
Stand von vor der Heilung trägt.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pinterest_hashtags as ph
import pinterest_check as pc

FNF = pc.SITE

FNF_DESC_5_TAGS = ("*Werbung | Beim Umzug entscheidet die Reihenfolge über zwei Wochen "
                   "ohne Internet. Mehr Spartipps auf FranksFinanzcheck! "
                   "#umzug #internet #rufnummer #dsl #wechsel")
FNF_DESC_3_TAGS = ("*Werbung | Beim Umzug entscheidet die Reihenfolge über zwei Wochen "
                   "ohne Internet. Mehr Spartipps auf FranksFinanzcheck! "
                   "#umzug #internet #rufnummer")


def _pin_html(desc: str, slug: str = "sample") -> str:
    import urllib.parse
    media = urllib.parse.quote(f"{pc.SITE}/images/covers/{slug}.jpg", safe="")
    q = (f"url={urllib.parse.quote(pc.SITE + '/posts/' + slug + '/', safe='')}"
         f"&media={media}&description={urllib.parse.quote(desc, safe='')}")
    return (f'<html><body><a href="https://www.pinterest.de/pin/create/button/?{q}">'
            f'Pin It</a></body></html>')


class PinterestAffiliateDensityTests(unittest.TestCase):
    def check_article(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            post = Path(tmp) / "content" / "posts" / "sample" / "index.md"
            post.parent.mkdir(parents=True)
            post.write_text(content, encoding="utf-8")
            with patch.object(pc, "BLOG_DIR", tmp):
                pc.PROBLEMS.clear()
                pc._check_affiliate_density()
                return list(pc.PROBLEMS)

    def test_five_affiliate_links_are_within_limit(self):
        content = " ".join("[Vergleich](/go/strom/)" for _ in range(5))
        self.assertEqual(self.check_article(content), [])

    def test_six_mixed_affiliate_links_report_p11(self):
        content = " ".join(
            ["[Strom](/go/strom/)"] * 4
            + ["[Tarif](https://a.check24.net/click)"]
            + ["[Police](https://a.partner-versicherung.de/click)"]
        )
        self.assertEqual(
            self.check_article(content),
            [("P11", "sample", "6 Affiliate-Links (> 5 – Profi-Limit)")],
        )


class PinterestReportProvenanceTests(unittest.TestCase):
    def test_source_fingerprint_changes_when_checked_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            post = root / "content" / "posts" / "sample" / "index.md"
            post.parent.mkdir(parents=True)
            post.write_text("---\ntitle: Eins\n---\nText\n", encoding="utf-8")
            with patch.object(pc, "BLOG_DIR", tmp):
                first = pc.source_fingerprint()
                post.write_text("---\ntitle: Zwei\n---\nText\n", encoding="utf-8")
                second = pc.source_fingerprint()
            self.assertRegex(first, r"^[0-9a-f]{64}$")
            self.assertNotEqual(first, second)

    def test_old_report_without_fingerprint_is_not_current(self):
        self.assertIsNone(pc.report_source_fingerprint("# 📌 PINTEREST-REPORT\nProbleme: 0\n"))
        fingerprint = "a" * 64
        self.assertEqual(
            pc.report_source_fingerprint(f"**Quellfingerabdruck:** `{fingerprint}`"),
            fingerprint,
        )


    def test_prosa_aenderung_entwertet_den_report_nicht(self):
        """#462: Der Nachweis gilt dem PIN-RELEVANTEN Quellenstand.

        Vorher hashte der Fingerabdruck die kompletten Artikel-Bytes. Jede
        Stilpolitur und jeder neue Absatz machte den Pinterest-Report
        „veraltet“, obwohl keine einzige Pinterest-Prüfung ein anderes
        Ergebnis geliefert hätte – ein täglicher Alarm ohne Erkenntnis.
        """
        with tempfile.TemporaryDirectory() as tmp:
            post = Path(tmp) / "content" / "posts" / "a" / "index.md"
            post.parent.mkdir(parents=True)
            fm = ('---\ntitle: Eins\npin_title: "Pin Eins"\n'
                  'pin_description: "Text"\n---\n')
            post.write_text(fm + "Absatz eins.\n", encoding="utf-8")
            with patch.object(pc, "BLOG_DIR", tmp):
                vorher = pc.source_fingerprint()
                post.write_text(fm + "Absatz eins, sprachlich poliert.\n",
                                encoding="utf-8")
                nach_politur = pc.source_fingerprint()
                post.write_text(fm.replace("Pin Eins", "Pin Zwei")
                                + "Absatz eins.\n", encoding="utf-8")
                nach_pin_feld = pc.source_fingerprint()
                post.write_text(fm + "Absatz [Angebot](/go/check24-strom/).\n",
                                encoding="utf-8")
                nach_gateway = pc.source_fingerprint()
        self.assertEqual(vorher, nach_politur,
                         "Prosa-Politur darf den Pinterest-Nachweis nicht entwerten")
        self.assertNotEqual(vorher, nach_pin_feld,
                            "Pin-Felder MÜSSEN den Nachweis entwerten")
        self.assertNotEqual(vorher, nach_gateway,
                            "Affiliate-Gateways (P11/P12) MÜSSEN zählen")


class PinterestHashtagHealingTests(unittest.TestCase):
    """P8: Quelle prüfen, heilen, idempotent – fail-closed ohne Heilerfolg."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="p8-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.post = self.root / "content" / "posts" / "sample" / "index.md"
        self.post.parent.mkdir(parents=True)
        self.html = self.root / "public" / "posts" / "sample" / "index.html"
        self.html.parent.mkdir(parents=True)
        media = self.root / "static" / "images" / "covers" / "sample.jpg"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"\0" * (pc.MEDIA_MIN + 1024))
        self.patches = [
            patch.object(pc, "BLOG_DIR", self.tmp.name),
            patch.object(pc, "PUBLIC", str(self.root / "public")),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        pc.PROBLEMS.clear()
        pc.FIXED.clear()
        pc.SOURCE_FINDINGS.clear()
        pc.SOURCE_HEALED.clear()
        self.addCleanup(pc.PROBLEMS.clear)
        self.addCleanup(pc.FIXED.clear)
        self.addCleanup(pc.SOURCE_FINDINGS.clear)
        self.addCleanup(pc.SOURCE_HEALED.clear)

    def _schreibe_post(self, desc):
        self.post.write_text(
            "---\ntitle: \"Umzug mit Internet\"\n"
            f'pin_description: "{desc}"\n'
            "---\n\nText.\n", encoding="utf-8")

    def _quelle(self):
        import re
        return re.search(r'^pin_description:\s*"(.*)"\s*$',
                         self.post.read_text(encoding="utf-8"), re.M).group(1)

    def test_fix_kappt_die_quelle_auf_drei_tags(self):
        self._schreibe_post(FNF_DESC_5_TAGS)
        with patch.object(pc, "DO_FIX", True):
            pc._check_pin_descriptions()
        self.assertEqual(FNF_DESC_3_TAGS, self._quelle())
        self.assertEqual([], pc.PROBLEMS, "geheilter Befund darf offen bleiben?")
        self.assertTrue(pc.FIXED and pc.FIXED[0][0] == "P8", pc.FIXED)
        self.assertEqual([], ph.befunde(self._quelle()))

    def test_check_meldet_ohne_fix_den_befund(self):
        self._schreibe_post(FNF_DESC_5_TAGS)
        with patch.object(pc, "DO_FIX", False):
            pc._check_pin_descriptions()
        self.assertEqual([("P8", "sample", "5 Hashtags (max. 3)")], pc.PROBLEMS)
        self.assertEqual(FNF_DESC_5_TAGS, self._quelle(), "Check darf nicht schreiben")

    def test_heilung_ist_idempotent(self):
        self._schreibe_post(FNF_DESC_5_TAGS)
        with patch.object(pc, "DO_FIX", True):
            pc._check_pin_descriptions()
            pc.PROBLEMS.clear()
            pc.FIXED.clear()
            pc.SOURCE_FINDINGS.clear()
            pc.SOURCE_HEALED.clear()
            pc._check_pin_descriptions()
        self.assertEqual([], pc.PROBLEMS)
        self.assertEqual([], pc.FIXED, "zweiter Lauf darf nichts mehr ändern")
        self.assertEqual(FNF_DESC_3_TAGS, self._quelle())

    def test_umlaut_und_grossbuchstabe_sind_keine_unsichtbaren_faelle_mehr(self):
        """Der Blindfleck: `[a-z0-9]+` sah nur '#z' bzw. '#erste'."""
        for desc, muss in (
            ("*Werbung | Gaszähler ablesen. #zählerstand #gas", "Umlaut-Hashtag"),
            ("*Werbung | Erste Wohnung. #ersteWohnung #fixkosten", "Großbuchstaben"),
        ):
            with self.subTest(muss=muss):
                self._schreibe_post(desc)
                pc.PROBLEMS.clear()
                with patch.object(pc, "DO_FIX", False):
                    pc._check_pin_descriptions()
                self.assertTrue(any(muss in msg for _c, _s, msg in pc.PROBLEMS),
                                f"{muss} nicht erkannt: {pc.PROBLEMS}")

    def test_heilung_schreibt_nur_das_pin_feld(self):
        """Ein Heiler darf genau den Defekt ändern – keine zweite Zeile."""
        self._schreibe_post(FNF_DESC_5_TAGS)
        vorher = self.post.read_text(encoding="utf-8").splitlines()
        with patch.object(pc, "DO_FIX", True):
            pc._check_pin_descriptions()
        nachher = self.post.read_text(encoding="utf-8").splitlines()
        veraendert = [(a, b) for a, b in zip(vorher, nachher) if a != b]
        self.assertEqual(1, len(veraendert), f"mehr als eine Zeile geändert: {veraendert}")
        self.assertTrue(veraendert[0][0].startswith("pin_description:"))
        self.assertEqual(len(vorher), len(nachher), "Zeilen kamen/verschwanden")

    def test_build_befund_nach_heilung_ist_kein_offener_fund(self):
        """Der Watchdog baut VOR dem Check: Der Build trägt den alten Stand."""
        self._schreibe_post(FNF_DESC_5_TAGS)
        self.html.write_text(_pin_html(FNF_DESC_5_TAGS), encoding="utf-8")
        with patch.object(pc, "DO_FIX", True):
            pc._check_pin_descriptions()
            pc._check_pin_buttons()
        self.assertEqual([], pc.PROBLEMS, "Heilung und Meldung widersprechen sich")
        self.assertTrue(any("vor der Heilung" in msg for _c, _s, msg in pc.FIXED),
                        pc.FIXED)

    def test_build_drift_wird_gemeldet(self):
        """Quelle sauber, Build defekt = Template-/Reihenfolgen-Defekt."""
        self._schreibe_post(FNF_DESC_3_TAGS)
        self.html.write_text(_pin_html(FNF_DESC_5_TAGS), encoding="utf-8")
        with patch.object(pc, "DO_FIX", True):
            pc._check_pin_descriptions()
            pc._check_pin_buttons()
        self.assertTrue(any("Build weicht von der Quelle ab" in msg
                            for _c, _s, msg in pc.PROBLEMS), pc.PROBLEMS)

    def test_build_befund_ohne_quellbefund_bei_sauberem_stand_bleibt_still(self):
        self._schreibe_post(FNF_DESC_3_TAGS)
        self.html.write_text(_pin_html(FNF_DESC_3_TAGS), encoding="utf-8")
        with patch.object(pc, "DO_FIX", True):
            pc._check_pin_descriptions()
            pc._check_pin_buttons()
        self.assertEqual([], [p for p in pc.PROBLEMS if p[0] == "P8"], pc.PROBLEMS)

    def test_fm_set_ueberlebt_backslashes(self):
        """Ein Backslash im Wert war für `re.sub` ein Escape (Härtung)."""
        content = '---\ntitle: "T"\npin_description: "alt"\n---\n\nText\n'
        neu = pc._fm_set(content, "pin_description", "Preis \\1 \\g<0> Test")
        self.assertIn("pin_description: ", neu)
        self.assertNotIn("alt", neu)


class PinterestP4ErzeugerTests(unittest.TestCase):
    """Auch die P4-Generatoren liefern nur SSOT-konforme Texte (#729).

    Die beiden Erzeuger bauen Pin-Texte für Duplikat-Heilungen. Ihr Suffix
    („Variante 3 mit Checkliste") landet im Prosa-Teil – die Schlusskontrolle
    über die SSOT hält den Tag-Block am Ende und unter drei Tags.
    """

    KWS = ["Umzug Internet", "Rufnummer mitnehmen", "DSL Umzug"]

    def test_check_generator_bleibt_konform(self):
        for attempt in (0, 3, 7):
            with self.subTest(attempt=attempt):
                text = pc._build_unique_pin_description(
                    "2026-09-04-umzug-mit-internet", "Umzug mit Internet",
                    "Beim Umzug entscheidet die Reihenfolge über zwei Wochen "
                    "ohne Internet.", self.KWS, set(), attempt=attempt)
                self.assertEqual([], ph.befunde(text))
                self.assertLessEqual(len(text), pc.DESC_MAX)

    def test_duplicate_guard_generator_bleibt_konform(self):
        import pinterest_duplicate_guard as pdg
        for attempt in (0, 3, 7):
            with self.subTest(attempt=attempt):
                text = pdg._unique_desc(
                    "2026-09-04-umzug-mit-internet", "Umzug mit Internet",
                    "Beim Umzug entscheidet die Reihenfolge über zwei Wochen "
                    "ohne Internet.", self.KWS, set(), attempt=attempt)
                self.assertEqual([], ph.befunde(text))
                self.assertLessEqual(len(text), pdg.DESC_MAX)


class PinterestReportHonestyTests(unittest.TestCase):
    """C2: Eine nicht ausgeführte Messung ist kein Grün – auch im Report."""

    def test_report_nennt_uebersprungene_html_pruefungen(self):
        zeilen = pc._report_zeilen(["P3", "P6", "P7", "P10", "P12"])
        text = "\n".join(zeilen)
        self.assertIn("Nicht gemessen", text)
        self.assertIn("P3", text)
        self.assertNotIn("Alle Pinterest-Signale im Profi-Bereich", text)

    def test_report_ist_gruen_wenn_alles_gemessen_ist(self):
        text = "\n".join(pc._report_zeilen([]))
        self.assertIn("Alle Pinterest-Signale im Profi-Bereich", text)
        self.assertNotIn("Nicht gemessen", text)


if __name__ == "__main__":
    unittest.main()
