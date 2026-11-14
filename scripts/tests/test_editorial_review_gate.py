import copy
import datetime as dt
import io
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
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

    def test_hoehere_manuelle_risikoklasse_ist_wirksam(self):
        fm = {"title": "WLAN-Reichweite verbessern",
              "redaktionelle_pruefung": {"risikoklasse": "hoch",
                                         "status": "ausstehend"}}
        result = gate.validate_article(fm, "Text", today=self.TODAY)
        self.assertEqual(result["risk"], gate.RISK_HIGH)
        self.assertTrue(result["blocking"])
        self.assertIn("E05", self.codes(result))
        fm["redaktionelle_pruefung"]["risikoklasse"] = "erhoeht"
        result = gate.validate_article(fm, "Text", today=self.TODAY)
        self.assertEqual(result["risk"], gate.RISK_ELEVATED)
        self.assertFalse(result["blocking"])

    def test_automatisches_risiko_darf_nicht_herabgestuft_werden(self):
        fm = {"title": "Baufinanzierung für Familien",
              "redaktionelle_pruefung": {"risikoklasse": "standard",
                                         "status": "ausstehend"}}
        result = gate.validate_article(fm, "Text", today=self.TODAY)
        self.assertEqual(result["risk"], gate.RISK_HIGH)
        self.assertTrue(result["blocking"])
        self.assertIn("E02", self.codes(result))

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

    def test_historischer_pruefer_ersetzt_keine_neue_freigabe(self):
        body = self.body()
        fm = self.frontmatter(body)
        review = fm['redaktionelle_pruefung']
        review.pop('inhalt_sha256')
        review['vorheriger_pruefer'] = review.pop('pruefer')
        review['vorheriges_pruefdatum'] = review.pop('pruefdatum')
        review['vorheriger_reviewtermin'] = review.pop('naechste_pruefung')
        # Selbst ein fälschlich auf freigegeben gesetzter Status kann alte
        # Prüfdaten nicht als Beweis für die neue Fassung wiederverwenden.
        result = gate.validate_article(fm, body, today=self.TODAY, ignore_hash=True)
        self.assertTrue({'E07', 'E08', 'E09', 'E10'} <= self.codes(result))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'index.md'
            raw = '---\n' + gate._yaml_module().safe_dump(fm, allow_unicode=True, sort_keys=False) + '---\n' + body
            path.write_text(raw, encoding='utf-8')
            with self.assertRaises(gate.ParseError):
                gate.seal(path, today=self.TODAY)
            self.assertEqual(path.read_text(encoding='utf-8'), raw)

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

    def test_reserve_hold_blocks_a_direct_live_flip_at_any_risk(self):
        for marker in ('reserve_blocked', 'reserve_retired'):
            with self.subTest(marker=marker):
                fm = {"title": "WLAN-Reichweite verbessern", "draft": True,
                      marker: "Redaktionelle Prüfung ausstehend"}
                draft = gate.validate_article(fm, "Text", today=self.TODAY)
                self.assertTrue(draft["reserve_hold"])
                self.assertFalse(draft["blocking"])
                fm["draft"] = False
                live = gate.validate_article(fm, "Text", today=self.TODAY)
                self.assertTrue(live["blocking"])
                self.assertIn("E20", self.codes(live))
                del fm["draft"]  # Hugo's default is live, not draft.
                self.assertIn("E20", self.codes(
                    gate.validate_article(fm, "Text", today=self.TODAY)))

    def test_published_gate_finds_a_direct_live_flip_with_a_reserve_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            article = posts / "held" / "index.md"
            article.parent.mkdir(parents=True)
            article.write_text(
                '---\ntitle: "Heizölpreise vergleichen"\ndraft: true\n'
                'reserve_blocked: "Redaktionelle Prüfung"\n---\nText.\n',
                encoding="utf-8")
            with patch.object(gate, "POSTS", posts), redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main(["--published", "--strict"]), 0)
                article.write_text(article.read_text(encoding="utf-8").replace(
                    "draft: true", "draft: false"), encoding="utf-8")
                self.assertEqual(gate.main(["--published", "--strict"]), 1)

    def test_deploy_hat_published_bestands_gate(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("editorial_review_gate.py --published --strict", workflow)

    def test_publish_gate_behaelt_ymyl_entwurf_statt_ihn_zu_loeschen(self):
        """Review-Hold isoliert messen; ausgefallene Faktenakte bleibt fail-closed."""
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
                # Unabhängige Gates isolieren: Eine kaputte Produktions-Queue
                # darf diesen Review-Test nicht unbemerkt in einen Test des
                # Fakten-Hartstopps verwandeln (Vorfall 14.11.2026).
                rueckgaben = {
                    "todays_live_candidates": [slug],
                    "r5_self_heal_candidates": 0,
                    "keyword_self_heal_candidates": 0,
                    "check_length_failures": (set(), None),
                    "seo_audit_failures": (set(), None),
                    "faktenfrische_failures": ({}, None, False),
                    "fakten_befund_failures": ({}, None, False),
                    "affiliate_profi_failures": ({}, None),
                    "affiliate_integrity_failures": ({}, None, False),
                    "affiliate_intent_failures": ({}, None, False),
                    "offenlegung_failures": ({}, None, False),
                    "title_integrity_failures": set(),
                    "keyword_failures": ({}, None),
                    "readability_failures": ({}, None),
                    "textverstaendnis_failures": ({}, None),
                    "duplicate_failures": ({}, None),
                    "uniqueness_failures": ({}, None),
                    "kurzantwort_failures": ({}, None),
                }
                with ExitStack() as stack:
                    for name, wert in rueckgaben.items():
                        stack.enter_context(patch.object(publish_gate, name, return_value=wert))
                    stack.enter_context(patch.object(audit_log, "log_event"))
                    stack.enter_context(redirect_stdout(io.StringIO()))
                    original = article.read_bytes()
                    # Eine ausgefallene Messung darf nicht als roter Inhalt
                    # behandelt werden: weder zurückstufen noch löschen.
                    with patch.object(publish_gate, "fakten_befund_failures",
                                      return_value=({}, "Faktenakte defekt", True)):
                        self.assertEqual(publish_gate.main(), 1)
                        self.assertEqual(article.read_bytes(), original)
                    # Erst mit messbarer Faktenakte wird der YMYL-Hold geprüft.
                    self.assertEqual(publish_gate.main(), 1)

                    # Ein versehentlich live gesetzter Reserve-Hold kann auch
                    # bei geringerem Risiko und einem neuen Slug nicht als
                    # mangelhafter Neu-Artikel verworfen werden (E20).
                    held_slug = dt.date.today().isoformat() + "-heizoel-hold"
                    held = posts / held_slug / "index.md"
                    held.parent.mkdir()
                    held.write_text(
                        "---\n"
                        'title: "Heizölpreise vergleichen"\n'
                        f"date: {dt.date.today().isoformat()}\n"
                        "draft: false\n"
                        'reserve_blocked: "Redaktionelle Prüfung ausstehend"\n'
                        'redaktionelle_pruefung:\n  risikoklasse: "erhoeht"\n'
                        '  status: "ausstehend"\n'
                        "---\n\nFachlicher Entwurf bleibt erhalten.\n",
                        encoding="utf-8",
                    )
                    with patch.object(publish_gate, "todays_live_candidates",
                                      return_value=[held_slug]):
                        self.assertEqual(publish_gate.main(), 1)
                    self.assertTrue(held.exists())
                    held_text = held.read_text(encoding="utf-8")
                    self.assertIn("draft: true", held_text)
                    self.assertIn("reserve_blocked:", held_text)
                    self.assertIn('cadence_grund: "redaktioneller-hold:', held_text)
                    self.assertIn("Fachlicher Entwurf bleibt erhalten", held_text)
            finally:
                publish_gate.POSTS_DIR, publish_gate.DRY_RUN, publish_gate.STRICT = old
            self.assertTrue(article.exists())
            text = article.read_text(encoding="utf-8")
            self.assertIn("draft: true", text)
            self.assertIn("cadence_grund: \"ymyl-review:", text)
            self.assertNotIn("cadence_wait:", text)

    def test_defekte_faktenakte_ist_ein_werkzeugfehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "queue.json"
            decisions = Path(tmp) / "entscheidungen.yaml"
            queue.write_text('{"fachbefunde": [', encoding="utf-8")
            decisions.write_text("entscheidungen: []\n", encoding="utf-8")
            findings, warning, tool_error = publish_gate.fakten_befund_failures(
                ["baufinanzierung-test"], queue_path=queue, decisions_path=decisions)
        self.assertEqual(findings, {})
        self.assertTrue(tool_error)
        self.assertIn("nicht beweisbar", warning)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(gate.selftest(), [])

    # --- #1069 (Dauerheilung 05.11.2026): Siegel bindet die Meta-Qualität ---
    # Ab dem Siegel ist die Fassung für die Meta-Heiler gesperrt. Eine hier
    # versiegelte Meta-Befund-Description würde das Wochen-Gate dauerhaft rot
    # machen. Das Siegel verweigert sie deshalb – gemessen mit den vorhandenen
    # Messstellen (meta_optimizer.desc_has_sentence_end + serp_limits).

    def _write_article(self, tmp, fm, body):
        path = Path(tmp) / "index.md"
        raw = "---\n" + gate._yaml_module().safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
        path.write_text(raw, encoding="utf-8")
        return path, raw

    def test_siegel_verweigert_description_ohne_satzende(self):
        body = self.body()
        fm = self.frontmatter(body)
        fm["description"] = "Kriterien für ein Immobiliendarlehen ohne Schlusspunkt"
        with tempfile.TemporaryDirectory() as tmp:
            path, raw = self._write_article(tmp, fm, body)
            history = Path(tmp) / "history.jsonl"
            with patch.object(gate, "HISTORY", history):
                with self.assertRaisesRegex(gate.ParseError, "Meta-Qualitäts-Gate"):
                    gate.seal(path, today=self.TODAY)
            self.assertEqual(path.read_text(encoding="utf-8"), raw)
            self.assertFalse(history.exists())

    def test_siegel_verweigert_description_ausserhalb_snippet_fenster(self):
        body = self.body()
        fm = self.frontmatter(body)
        fm["description"] = "W " * 120 + "Ende."  # > 155 Zeichen und > 985 px
        with tempfile.TemporaryDirectory() as tmp:
            path, raw = self._write_article(tmp, fm, body)
            with patch.object(gate, "HISTORY", Path(tmp) / "history.jsonl"):
                with self.assertRaisesRegex(gate.ParseError, "Meta-Qualitäts-Gate"):
                    gate.seal(path, today=self.TODAY)
            self.assertEqual(path.read_text(encoding="utf-8"), raw)

    def test_siegel_akzeptiert_meta_sauberere_description(self):
        body = self.body()
        fm = self.frontmatter(body)  # Description mit Satzende, im Fenster
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._write_article(tmp, fm, body)
            history = Path(tmp) / "history.jsonl"
            with patch.object(gate, "HISTORY", history):
                result = gate.seal(path, today=self.TODAY)
            self.assertTrue(result["approved"])
            sealed_fm, sealed_body, _ = gate.load_article(path)
            self.assertEqual(sealed_fm["redaktionelle_pruefung"]["inhalt_sha256"],
                             gate.content_fingerprint(sealed_fm, sealed_body))
            self.assertEqual(len(history.read_text(encoding="utf-8").splitlines()), 1)

    def test_versiegelte_fassungen_sind_meta_sauber(self):
        # Bestands-Invariante: Jede versiegelte Fassung muss die Description-Regel
        # des Meta-Gates bestehen. Hätte dieser Test am 30.10. existiert, wäre die
        # Neusiegelung der punktlosen Description (#1069) im PR aufgefallen.
        for path in gate.all_post_paths():
            fm, _, _ = gate.load_article(path)
            review = fm.get("redaktionelle_pruefung") or {}
            sealed = bool(review.get("inhalt_sha256")) or str(review.get("status") or "").strip().lower() in gate.APPROVED_STATUSES
            if not sealed:
                continue
            with self.subTest(slug=path.parent.name):
                self.assertEqual(gate.meta_befunde_description(fm), [])


if __name__ == "__main__":
    unittest.main()
