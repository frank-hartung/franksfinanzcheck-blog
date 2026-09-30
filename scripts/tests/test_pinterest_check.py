"""Regression tests for Pinterest check P11 affiliate-link density."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pinterest_check as pc


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


if __name__ == "__main__":
    unittest.main()
