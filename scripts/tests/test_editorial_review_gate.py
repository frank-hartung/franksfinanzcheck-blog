import copy
import datetime as dt
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit_log
import editorial_review_gate as gate
import publish_gate


class EditorialReviewGateTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 2)

    def body(self, *, early_cta=False, stale=False):
        lead = "[Jetzt vergleichen](/go/kredit/)\n\n" if early_cta else ""
        text = lead + ("Sachliche Einordnung mit nachvollziehbaren Kriterien. " * 170)
        text += "\n\nDie passende Finanzierung hängt von individuellen Annahmen ab.\n"
        text += "\n## Voraussetzungen\n\nKontext.\n\n## Risiken und Gegenfälle\n\nKontext.\n"
        text += "\n**Rechenbeispiel:** Die Modellrate nutzt 300.000 Euro als freie Annahme.\n"
        if not early_cta:
            text += "\n[Jetzt vergleichen](/go/kredit/)\n"
        if stale:
            text += "\nAktuelle Konditionen (Stand 2024).\n"
        return text

    def frontmatter(self, body=None):
        body = body or self.body()
        fm = {
            "title": "Baufinanzierung: Angebote belastbar vergleichen",
            "description": "Kriterien für ein Immobiliendarlehen.",
            "author": "Frank Hartung",
            "quellen": [
                {"id": "Q1", "titel": "Verbraucherschutz Baufinanzierung",
                 "url": "https://www.verbraucherzentrale.de/wissen/geld-versicherungen/bau-immobilienfinanzierung/a",
                 "herausgeber": "Verbraucherzentrale", "datum": "2026-09-10"},
                {"id": "Q2", "titel": "Rechtsgrundlage",
                 "url": "https://www.gesetze-im-internet.de/bgb/b",
                 "herausgeber": "Bundesministerium der Justiz", "datum": "2026-09-12"},
            ],
            "redaktionelle_pruefung": {
                "risikoklasse": "hoch",
                "status": "freigegeben",
                "pruefer": {
                    "name": "Redaktion FranksFinanzcheck",
                    "rolle": "Faktenprüfung anhand Primär- und Verbraucherquellen",
                    "typ": "redaktion-mit-externer-belegkette",
                },
                "pruefdatum": "2026-10-02",
                "naechste_pruefung": "2026-11-16",
                "aenderungsgrund": "Erstprüfung vor der Veröffentlichung",
                "gepruefte_aussagen": [{
                    "textanker": "Die passende Finanzierung hängt von individuellen Annahmen ab.",
                    "pruefung": "Als fallabhängige Einordnung bestätigt",
                    "quellen": ["Q1", "Q2"],
                }],
                "gepruefte_zahlen": [{
                    "aussage": "Modellhafte Monatsrate",
                    "wert": "300.000 Euro Darlehen als freie Annahme",
                    "fundstelle": "Die Modellrate nutzt 300.000 Euro als freie Annahme.",
                    "pruefung": "Formel und Rundung nachgerechnet",
                    "konsistenzpruefung": "Fließtext und dokumentierter Rechenweg stimmen überein",
                    "rechenweg": "Darlehensbetrag mal Annuität geteilt durch zwölf",
                    "quellen": ["Q1", "Q2"],
                }],
            },
        }
        fm["redaktionelle_pruefung"]["inhalt_sha256"] = gate.content_fingerprint(fm, body)
        return fm

    def codes(self, result):
        return {finding["code"] for finding in result["findings"]}

    def test_vier_kritische_themen_sind_hochrisiko(self):
        for title in (
            "Baufinanzierung für den Hauskauf",
            "Altersvorsorge und Rentenlücke",
            "Ratenkredit richtig umschulden",
            "Wohngebäudeversicherung prüfen",
        ):
            with self.subTest(title=title):
                self.assertEqual(gate.classify_text(title), gate.RISK_HIGH)

    def test_kreditkarte_wird_nicht_durch_wortpraefix_hochgestuft(self):
        self.assertNotEqual(gate.classify_text("Kreditkarte vergleichen"), gate.RISK_HIGH)

    def test_vollstaendige_freigabe_besteht(self):
        body = self.body()
        result = gate.validate_article(self.frontmatter(body), body, today=self.TODAY)
        self.assertTrue(result["approved"])
        self.assertFalse(result["findings"])

    def test_fehlender_review_blockiert_baufinanzierung(self):
        fm = {"title": "Baufinanzierung für Familien", "author": "Frank Hartung"}
        result = gate.validate_article(fm, "Text", today=self.TODAY)
        self.assertTrue(result["blocking"])
        self.assertIn("E03", self.codes(result))

    def test_textaenderung_entwertet_freigabe(self):
        body = self.body()
        result = gate.validate_article(self.frontmatter(body), body + "\nNeue Aussage.", today=self.TODAY)
        self.assertIn("E17", self.codes(result))

    def test_aenderung_am_pruefprotokoll_entwertet_freigabe(self):
        body = self.body()
        fm = self.frontmatter(body)
        fm["redaktionelle_pruefung"]["pruefer"]["name"] = "Andere Person"
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E17", self.codes(result))

    def test_frueher_affiliate_cta_blockiert(self):
        body = self.body(early_cta=True)
        fm = self.frontmatter(body)
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E15", self.codes(result))

    def test_veralteter_stand_blockiert(self):
        body = self.body(stale=True)
        fm = self.frontmatter(body)
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E16", self.codes(result))

    def test_pauschale_bankbehauptung_ohne_textanker_blockiert(self):
        body = self.body() + "\nBanken akzeptieren immer jedes Einkommen.\n"
        fm = self.frontmatter(body)
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E18", self.codes(result))

    def test_nicht_protokollierte_zahl_blockiert(self):
        body = self.body() + "\nDie Zusatzgebühr beträgt 500 Euro.\n"
        fm = self.frontmatter(body)
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E19", self.codes(result))

    def test_widerspruechliche_gepruefte_werte_blockieren(self):
        body = self.body()
        fm = self.frontmatter(body)
        zweiter_wert = copy.deepcopy(fm["redaktionelle_pruefung"]["gepruefte_zahlen"][0])
        zweiter_wert["wert"] = "250.000 Euro Darlehen als freie Annahme"
        fm["redaktionelle_pruefung"]["gepruefte_zahlen"].append(zweiter_wert)
        fm["redaktionelle_pruefung"]["inhalt_sha256"] = gate.content_fingerprint(fm, body)
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E14", self.codes(result))

    def test_unbekannte_quellenreferenz_blockiert(self):
        body = self.body()
        fm = self.frontmatter(body)
        fm["redaktionelle_pruefung"]["gepruefte_zahlen"][0]["quellen"] = ["Q9"]
        fm["redaktionelle_pruefung"]["inhalt_sha256"] = gate.content_fingerprint(fm, body)
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E13", self.codes(result))

    def test_ueberfaelliger_review_blockiert(self):
        body = self.body()
        fm = self.frontmatter(body)
        fm["redaktionelle_pruefung"]["pruefdatum"] = "2026-08-01"
        fm["redaktionelle_pruefung"]["naechste_pruefung"] = "2026-09-15"
        result = gate.validate_article(fm, body, today=self.TODAY)
        self.assertIn("E09", self.codes(result))
        self.assertIn("E10", self.codes(result))

    def test_published_modus_ignoriert_hold_aber_blockiert_manuellen_live_flip(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            article = posts / "alter-ymyl-artikel" / "index.md"
            article.parent.mkdir(parents=True)
            article.write_text(
                "---\n"
                'title: "Baufinanzierung im Test"\n'
                "draft: true\n"
                'author: "Frank Hartung"\n'
                "redaktionelle_pruefung:\n"
                '  risikoklasse: "hoch"\n'
                '  status: "ausstehend"\n'
                '  aenderungsgrund: "Fachliche Prüfung ist noch offen"\n'
                "---\n\nText.\n",
                encoding="utf-8",
            )
            with patch.object(gate, "POSTS", posts), redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main(["--published", "--strict", "--json"]), 0)
                article.write_text(
                    article.read_text(encoding="utf-8").replace("draft: true", "draft: false"),
                    encoding="utf-8",
                )
                self.assertEqual(gate.main(["--published", "--strict", "--json"]), 1)

    def test_deploy_hat_published_bestands_gate(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("editorial_review_gate.py --published --strict", workflow)

    def test_publish_gate_behaelt_ymyl_entwurf_statt_ihn_zu_loeschen(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            slug = dt.date.today().isoformat() + "-baufinanzierung-test"
            article = posts / slug / "index.md"
            article.parent.mkdir(parents=True)
            article.write_text(
                "---\n"
                'title: "Baufinanzierung: Test"\n'
                'description: "Prüfpflichtiger Test."\n'
                f"date: {dt.date.today().isoformat()}\n"
                "draft: false\n"
                'author: "Frank Hartung"\n'
                'keywords: ["Baufinanzierung"]\n'
                "---\n\nText.\n",
                encoding="utf-8",
            )
            old = (publish_gate.POSTS_DIR, publish_gate.DRY_RUN, publish_gate.STRICT)
            try:
                publish_gate.POSTS_DIR = str(posts)
                publish_gate.DRY_RUN = False
                publish_gate.STRICT = True
                with patch.object(publish_gate, "todays_live_candidates", return_value=[slug]), \
                     patch.object(publish_gate, "r5_self_heal_candidates", return_value=0), \
                     patch.object(publish_gate, "keyword_self_heal_candidates", return_value=0), \
                     patch.object(publish_gate, "check_length_failures", return_value=(set(), None)), \
                     patch.object(publish_gate, "seo_audit_failures", return_value=(set(), None)), \
                     patch.object(publish_gate, "faktenfrische_failures", return_value=({}, None, False)), \
                     patch.object(publish_gate, "affiliate_profi_failures", return_value=({}, None)), \
                     patch.object(publish_gate, "affiliate_integrity_failures", return_value=({}, None, False)), \
                     patch.object(publish_gate, "affiliate_intent_failures", return_value=({}, None, False)), \
                     patch.object(publish_gate, "offenlegung_failures", return_value=({}, None, False)), \
                     patch.object(publish_gate, "title_integrity_failures", return_value=set()), \
                     patch.object(publish_gate, "keyword_failures", return_value=({}, None)), \
                     patch.object(publish_gate, "readability_failures", return_value=({}, None)), \
                     patch.object(publish_gate, "textverstaendnis_failures", return_value=({}, None)), \
                     patch.object(audit_log, "log_event"), \
                     redirect_stdout(io.StringIO()):
                    self.assertEqual(publish_gate.main(), 1)
            finally:
                publish_gate.POSTS_DIR, publish_gate.DRY_RUN, publish_gate.STRICT = old
            self.assertTrue(article.exists())
            text = article.read_text(encoding="utf-8")
            self.assertIn("draft: true", text)
            self.assertIn("cadence_grund: \"ymyl-review:", text)
            self.assertNotIn("cadence_wait:", text)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(gate.selftest(), [])


if __name__ == "__main__":
    unittest.main()
