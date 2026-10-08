"""Regression tests for the reserve-specific premium editorial contract.

The reserve may count a candidate only when hard editorial checks, sourced
figures, readable structure and the actual publication gates all agree.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import generate_drafts as gd  # noqa: E402
import redaktions_standard as rs  # noqa: E402
import reserve_readiness as rr  # noqa: E402


class ReserveEditorialContractTests(unittest.TestCase):
    def test_leerer_yaml_autor_umgeht_rs7_nicht(self):
        for author in ("", "null", "~", '""'):
            with self.subTest(author=author):
                article = f"---\nauthor: {author}\n---\nText."
                findings = rr.reserve_editorial_findings(Path("unused"), article)
                self.assertTrue(any(f.startswith("RS7:") for f in findings), findings)

    def test_defektes_frontmatter_bleibt_gesperrt(self):
        for article in ("Text ohne Frontmatter", "---\n- Liste\n---\nText",
                        "---\nauthor: [\n---\nText"):
            with self.subTest(article=article):
                self.assertTrue(rr.reserve_editorial_findings(Path("unused"), article))

    def test_ausfall_des_redaktionspruefers_bleibt_gesperrt(self):
        with patch.object(rs, "reserve_quality_findings", side_effect=RuntimeError("Test")):
            findings = rr.reserve_editorial_findings(
                Path("unused"), "---\nauthor: Frank Hartung\n---\nText")
        self.assertIn("nicht prüfbar", findings[0])

    def test_unbelegte_zahl_blockiert_rs5(self):
        findings = rs.reserve_quality_findings(
            "Ein Tarif kostet 240 Euro pro Jahr.", author="Frank Hartung")
        self.assertTrue(any(f.startswith("RS5:") for f in findings), findings)

    def test_satzbeleg_akzeptiert_externe_zahl(self):
        body = (
            "Die anfängliche Laufzeit darf 24 Monate nicht überschreiten "
            "([§ 56 TKG](https://www.gesetze-im-internet.de/tkg_2021/__56.html)).")
        self.assertEqual([], rs._reserve_numeric_claim_findings(body))

    def test_modellrechnung_braucht_klare_markierung(self):
        self.assertEqual([], rs._reserve_numeric_claim_findings(
            "Modellrechnung: Bei 5 Watt über 24 Stunden fallen 43,8 kWh an."))
        self.assertTrue(rs._reserve_numeric_claim_findings(
            "Ein Smart-Gerät verbraucht 5 Watt über 24 Stunden."))

    def test_jahreszahl_im_internen_link_ist_keine_zahlenbehauptung(self):
        body = "Weiterlesen: [Beispielartikel](../../posts/2026-09-20-puffer/)."
        self.assertEqual([], rs._reserve_numeric_claim_findings(body))

    def test_phantomquelle_und_doppelte_h2_blockieren(self):
        body = "\n".join((
            "Laut einer aktuellen Studie spart jeder Haushalt viel Geld.",
            "## Warum sparen?", "", "## Warum sparen?"))
        findings = rs.reserve_quality_findings(body, author="Frank Hartung")
        self.assertTrue(any(f.startswith("RS6:") for f in findings), findings)
        self.assertTrue(any("doppelte H2" in f for f in findings), findings)

    def test_generator_geburtsgate_wendet_rs5_und_rs6_an(self):
        summary = "**Das Wichtigste in Kürze**\n\n- Punkt eins\n- Punkt zwei\n- Punkt drei\n\n"
        headings = (
            "## Warum ist ein Budget hilfreich?\n\n"
            "## Wie startest du mit dem Plan?\n\n"
            "## Was gehört in die Übersicht?\n\n"
            "## So gehst du vor\n\n"
            "## Häufige Fragen\n\n"
            "### Wie oft prüfe ich mein Budget?\n\nAntwort.\n\n"
            "### Muss ich eine App nutzen?\n\nAntwort.\n\n"
            "### Was mache ich bei knappen Einnahmen?\n\nAntwort.\n\n"
            "### Wie plane ich größere Ausgaben?\n\nAntwort.\n\n")
        filler = "Dieser Absatz erklärt das Budget ruhig und klar. " * 300
        base = (summary + "Ein Budget hilft dir, Entscheidungen zu ordnen.\n\n"
                + headings + "**Faustregel:** Plane zuerst, was dir wichtig ist.\n\n"
                + "1. Schreibe deine Ausgaben auf.\n2. Prüfe feste Kosten.\n"
                + "3. Lege ein passendes Sparziel fest.\n\n" + filler)
        with patch.object(gd, "lesbarkeits_befund", return_value=None):
            ok, problems = gd.profi_quality_ok(base)
            self.assertTrue(ok, problems)
            for bad in (
                "Der Tarif kostet 240 Euro pro Jahr.",
                "Laut einer aktuellen Studie sparen Kunden viel Geld.",
            ):
                accepted, reasons = gd.profi_quality_ok(base + "\n\n" + bad)
                self.assertFalse(accepted, bad)
                self.assertTrue(any(tag in " ".join(reasons)
                                    for tag in ("RS5", "RS6")), reasons)

    def test_readiness_stoppt_vor_publish_gate_und_laesst_bytes_unveraendert(self):
        body = "Ein Tarif kostet 240 Euro pro Jahr. Laut einer aktuellen Studie sparen Kunden."
        article = (
            "---\ntitle: Test\ndescription: Test.\ndate: 2026-10-07T06:00:00Z\n"
            "draft: true\nreserve: true\nauthor: Frank Hartung\n---\n" + body)
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "test-reserve" / "index.md"
            index.parent.mkdir()
            index.write_text(article, encoding="utf-8")
            with patch.object(rr, "score_diagnosis", return_value={
                    "score": 0.95, "parts": {"meta": 1.0}}), \
                    patch.object(rr.rp, "publish_one") as publish:
                row = rr.certify_one(index)
            self.assertFalse(row["ready"])
            self.assertIn("Reserve-Qualitäts-Gate", row["reason"])
            self.assertTrue(any(f.startswith("RS5:") for f in row["details"]),
                            row["details"])
            self.assertTrue(any(f.startswith("RS6:") for f in row["details"]),
                            row["details"])
            publish.assert_not_called()
            self.assertEqual(index.read_text(encoding="utf-8"), article)


if __name__ == "__main__":
    unittest.main()
