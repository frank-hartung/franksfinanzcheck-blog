"""#762: Editorial exemptions waive only the minimum-link requirement.

Temporary content/build fixtures exercise the public gate path including healing,
report and state. No network, Hugo installation or repository writes required.

WF-53E2 / #780 (16.10.2026): PR #776 added a second evaluation of the same
contract in two guards (re-read the file from disk, own ``split("---")``,
``except Exception`` → "not exempt") and dropped the visible note. The 27
tests here stayed green because every fixture wrote the post to disk; the
detector self-test (articles held in memory) went red and the daily guard
stood fail-closed. The classes below pin what was missing: the visible note,
one source of truth, one evaluation, the profi check A8 path and a structural
rule that keeps a second evaluator from coming back. The parallel repairs
#785 (in-memory proof, invalid exemption = both findings) and #784 (note with
reason, bestand gate) are kept as they are – their merge had left the gate
with an IndentationError, the selftest test below catches exactly that.
"""
from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import affiliate_exemption as contract
import affiliate_integrity_gate as gate
import affiliate_link_check as weekly
import affiliate_profi_check as profi

REASON = "Reiner DNS-Messtest ohne passendes Tarifangebot."
EXEMPT = f'affiliate_exempt: true\naffiliate_exempt_reason: "{REASON}"\n'
URL = "https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=strom"
CTA = "👉 **Jetzt vergleichen und sparen:** [**Stromtarife vergleichen**](/go/strom/)"
ANCHOR = '<a href="/go/strom/" rel="sponsored" data-klick="affiliate_click">Stromtarife vergleichen</a>'


class SharedContractTests(unittest.TestCase):
    def test_both_adapters_use_the_same_contract(self):
        cases = [
            ("", False, False),
            (EXEMPT, True, False),
            ("affiliate_exempt: false\n", False, False),
            ("affiliate_exempt: true\n", False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: "" # kein Grund\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: "   "\n', False, True),
            ('affiliate_exempt: "true"\naffiliate_exempt_reason: "Grund"\n', False, True),
            ('affiliate_exempt_reason: "Grund"\n', False, True),
            ('affiliate_exempt: false\naffiliate_exempt_reason: "Grund"\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: 42\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: [Grund]\n', False, True),
            ('title: [kaputt\n', False, True),
            ('- keine\n- Metadaten\n', False, True),
            ('affiliate_exempt: true\naffiliate_exempt_reason: >\n  DNS-Test\n  ohne Angebot\n', True, False),
        ]
        for fm, exempt, error in cases:
            with self.subTest(frontmatter=fm):
                expected = contract.affiliate_exemption(fm)
                self.assertEqual(expected[0], exempt)
                self.assertEqual(bool(expected[2]), error)
                self.assertEqual(weekly.affiliate_exemption({"frontmatter": fm}), expected)
                self.assertEqual(contract.exemption_for_article({"fm": fm}), expected)
                # #780: the raw-file adapter (profi check A8) reaches the
                # same verdict – Hugo's frontmatter boundary, no own split.
                self.assertEqual(contract.exemption_for_text(f"---\n{fm}---\n\nText\n"),
                                 expected)

    def test_text_adapter_without_frontmatter_has_no_exemption(self):
        self.assertEqual(contract.exemption_for_text(""), (False, "", ""))
        self.assertEqual(contract.exemption_for_text("Nur Text, kein Frontmatter."),
                         (False, "", ""))
        # A "---" inside a value is no boundary (a naive split("---", 2) would
        # cut the title in half and read garbage as frontmatter).
        text = f'---\ntitle: "DNS --- Messtest"\n{EXEMPT}---\n\nText\n'
        self.assertEqual(contract.exemption_for_text(text), (True, REASON, ""))


class IntegrityExemptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.posts = self.root / "content" / "posts"
        self.post = self.posts / "messtest" / "index.md"
        self.post.parent.mkdir(parents=True)
        self.html = self.root / "public" / "posts" / "messtest" / "index.html"
        self.html.parent.mkdir(parents=True)
        self.html.write_text("<html><body>DNS-Messtest</body></html>")
        registry = self.root / "scripts" / "check24_links.yaml"
        registry.parent.mkdir()
        registry.write_text(f'links:\n  strom: "{URL}"\n')
        gateway = self.root / "public" / "go" / "strom" / "index.html"
        gateway.parent.mkdir(parents=True)
        gateway.write_text(
            '<meta name="robots" content="noindex,nofollow">'
            f'<meta http-equiv="refresh" content="0; url={URL}">')
        self.gateway = gateway
        self.report = self.root / "report.md"
        self.state = self.root / "state.json"
        for name, value in (("REPORT", self.report), ("STATE", self.state),
                            ("ONLY_SLUGS", [])):
            patcher = patch.object(gate, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.write_post()

    def write_post(self, fm=EXEMPT, body="DNS-Messtest ohne Tarifangebot.\n"):
        self.post.write_text(
            '---\ntitle: "Messtest"\ndraft: false\npillar: "internet-dsl"\n'
            + fm + "---\n\n" + body)

    def run_gate(self):
        return gate.run(self.root, self.posts, do_heal=True, allow_build=False)

    def test_exemption_is_green_auditable_idempotent_and_never_injects_ctas(self):
        before = self.post.read_bytes()
        first = self.run_gate()
        self.assertEqual(first["exit_code"], gate.EXIT_OK, first)
        self.assertEqual(first["checked"], 1)
        self.assertEqual(first["exemptions"], {"messtest": REASON})
        self.assertFalse(first["healed"])
        notes = first["per_article"][0]["notes"]
        self.assertTrue(
            any("ausgenommen" in note.lower() and REASON in note for note in notes),
            f"gültige Ausnahme samt Begründung muss im Artikelbefund sichtbar sein: {notes}",
        )
        text = gate.write_report(first)
        gate.write_state(first)
        self.assertIn(REASON, text)
        self.assertIn("redaktionelle Ausnahme", text)
        self.assertNotIn("0 → 0 ✅", text)
        state = json.loads(self.state.read_text())
        self.assertEqual(state["exemptions"], {"messtest": REASON})
        self.assertEqual(state["unresolved_problems"], [])
        self.assertEqual(state["content_problems"], [])
        second = self.run_gate()
        gate.write_report(second)
        gate.write_state(second)
        self.assertFalse(second["verdict_changed"])
        self.assertFalse(second["report_changed"])
        self.assertEqual(self.post.read_bytes(), before)

    def test_missing_link_without_exemption_remains_red(self):
        self.write_post(fm="")
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("Kein einziger Affiliate-Link", result["render_problems"]["messtest"])

    def test_render_proof_uses_shared_exemption_without_reopening_source_file(self):
        """The parsed frontmatter is the SSOT; proof must not reread its path."""
        article = {
            "slug": "messtest",
            "path": self.root / "not-created" / "index.md",
            "fm": EXEMPT,
            "body": "DNS-Messtest ohne Tarifangebot.\n",
        }

        result = gate.verify_article_render(article, {"strom": URL}, self.root / "public")

        self.assertTrue(result["html_found"])
        self.assertTrue(result["exempt"])
        self.assertEqual(result["exempt_reason"], REASON)
        self.assertEqual(result["problems"], [])
        self.assertTrue(any(
            "ausgenommen" in note.lower() and REASON in note
            for note in result["notes"]
        ), "die begründete Ausnahme muss als sichtbarer Prüfhinweis erscheinen")

    def test_invalid_exemption_does_not_waive_the_missing_link_finding(self):
        article = {
            "slug": "messtest",
            "path": self.root / "not-created" / "index.md",
            "fm": "affiliate_exempt: true\n",
            "body": "DNS-Messtest ohne Tarifangebot.\n",
        }

        result = gate.verify_article_render(article, {"strom": URL}, self.root / "public")

        self.assertFalse(result["exempt"])
        self.assertTrue(any("Affiliate-Ausnahme ungültig" in p for p in result["problems"]))
        self.assertTrue(any("Kein einziger Affiliate-Link" in p for p in result["problems"]))

    def test_invalid_exemption_blocks_even_with_valid_links(self):
        self.write_post(fm="affiliate_exempt: true\n", body=CTA)
        self.html.write_text(ANCHOR)
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("nichtleere Begründung", result["render_problems"]["messtest"])
        self.assertIn("messtest", result["findings"])
        self.assertFalse(result["exemptions"])

    def test_exemption_does_not_hide_missing_source_link_in_html(self):
        self.write_post(body=CTA)
        article = gate.load_live_articles(self.posts)[0]
        result = gate.verify_article_render(article, {"strom": URL}, self.root / "public")
        self.assertTrue(any("NICHT im gebauten HTML" in p for p in result["problems"]))

    def test_exemption_does_not_hide_non_sponsored_link(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR.replace('rel="sponsored"', 'rel="nofollow"'))
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn('ohne rel="sponsored"', result["render_problems"]["messtest"])

    def test_exemption_does_not_hide_unregistered_gateway(self):
        self.html.write_text(ANCHOR.replace("strom/", "unbekannt/"))
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("nicht in check24_links.yaml registriert", result["render_problems"]["messtest"])

    def test_exemption_does_not_hide_raw_partner_links(self):
        self.html.write_text(f'<a href="{URL}">Partner</a>')
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("Roher Partner-Link", result["render_problems"]["messtest"])

    def test_exempt_article_with_valid_link_still_passes_full_proof(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_OK, result)
        self.assertEqual(result["per_article"][0]["expected"], 1)
        self.assertEqual(result["per_article"][0]["rendered"], 1)

    def test_exemption_does_not_hide_missing_gateway_noindex(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        self.gateway.write_text(f'<meta http-equiv="refresh" content="0; url={URL}">')
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("noindex", result["render_problems"]["messtest"])

    def test_exemption_does_not_hide_wrong_redirect(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        self.gateway.write_text('<meta name="robots" content="noindex">'
                                '<meta http-equiv="refresh" content="0; url=https://example.org/">')
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("messtest", result["render_problems"])

    def test_missing_built_page_is_not_exempt(self):
        self.html.unlink()
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_CONTENT)
        self.assertIn("Gebaute Seite fehlt", result["render_problems"]["messtest"])

    def test_missing_build_is_tool_failure_not_green_exemption(self):
        import shutil
        shutil.rmtree(self.root / "public")
        result = self.run_gate()
        self.assertEqual(result["exit_code"], gate.EXIT_TOOL)
        self.assertTrue(result["errors"])

    def test_healed_cta_does_not_clear_invalid_exemption_metadata(self):
        self.write_post(fm="affiliate_exempt: true\n", body=CTA + ")")
        result = gate.heal_file(self.post, {"strom": URL, "allgemein": URL})
        self.assertTrue(result["healed"])
        self.assertTrue(any("nichtleere Begründung" in p for p in result["problems"]))
        second = gate.heal_file(self.post, {"strom": URL, "allgemein": URL})
        self.assertFalse(second["healed"])
        self.assertTrue(second["problems"])

    def test_exemption_does_not_hide_broken_cta_structure(self):
        self.write_post(body=CTA + ")")
        article = gate.load_live_articles(self.posts)[0]
        findings = gate.markdown_findings([article], {"strom"})
        self.assertIn("messtest", findings)
        self.assertTrue(findings["messtest"]["broken_kinds"])

    def test_actual_dns_article_remains_explicitly_exempt(self):
        slug = "2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt"
        article = next(a for a in gate.load_live_articles() if a["slug"] == slug)
        exempt, reason, error = contract.exemption_for_article(article)
        self.assertTrue(exempt)
        self.assertIn("passendes Tarifangebot", reason)
        self.assertEqual(error, "")
        self.assertFalse(gate.markdown_findings([article], set(gate.load_registry())))

    # ---------------------------------------------------------------- #948
    # 30.10.2026: Die Tageswache meldete „Beweis nicht möglich (Werkzeug-
    # fehler, fail-closed)“. Der einzige fassbare Satz war ein Deep-Link-Fund
    # („Fehlt der passende Deep-Link“) – die URSACHE, nämlich `affiliate_exempt:
    # true` NEBEN einem vorhandenen CTA, stand nirgends. Diese Tests frieren
    # ein, dass der Widerspruch benannt wird, BEVOR das Symptom kommt – und
    # dass der Vertrag aus #762 dabei unangetastet bleibt.
    def test_ausnahme_mit_cta_wird_als_halbe_angabe_benannt(self):
        self.write_post(body=CTA)
        self.html.write_text(ANCHOR)
        result = self.run_gate()
        # Vertrag #762 unverändert: Die Ausnahme hebt nur die Mindestpflicht
        # auf, der vorhandene Link bleibt voll geprüft und grün.
        self.assertEqual(result["exit_code"], gate.EXIT_OK, result)
        self.assertEqual(result["exemptions_with_cta"], {"messtest": ["strom"]})
        report = gate.write_report(result)
        self.assertIn("Halbe Angabe", report)
        self.assertIn("/go/strom/", report)
        self.assertIn("Redaktionsentscheidung", report)

    def test_wochenchecker_nennt_den_widerspruch_vor_dem_deeplink_fund(self):
        problems = weekly.check_post({
            "path": "(test)", "slug": "messtest", "title": "Messtest",
            "pillar": "internet-dsl", "body": CTA, "content": CTA,
            "frontmatter": EXEMPT, "is_pillar": False,
        })
        self.assertEqual(problems[0]["severity"], "info", problems)
        self.assertIn("widersprechen sich", problems[0]["msg"])
        self.assertIn("/go/strom/", problems[0]["msg"])
        # Das Symptom bleibt unverändert stehen – nicht abgeschwächt:
        self.assertTrue(any(p["severity"] == "error" and "Deep-Link" in p["msg"]
                            for p in problems), problems)

    def test_ausnahme_ohne_cta_bleibt_ohne_widerspruch(self):
        result = self.run_gate()
        self.assertEqual(result["exemptions_with_cta"], {})
        report = gate.write_report(result)
        self.assertNotIn("Halbe Angabe", report)
        info = [p for p in weekly.check_post({
            "path": "(test)", "slug": "messtest", "title": "Messtest",
            "pillar": "internet-dsl", "body": "DNS-Messtest ohne CTA.",
            "content": "DNS-Messtest ohne CTA.",
            "frontmatter": EXEMPT, "is_pillar": False,
        }) if p["severity"] == "info"]
        self.assertFalse(any("widersprechen sich" in p["msg"] for p in info), info)

    def test_gate_run_keeps_the_exemption_note_visible(self):
        # #780: The note is part of the contract ("a hidden exemption is a
        # gap, not a contract"). #776 deleted it while every test stayed green.
        result = self.run_gate()
        notes = result["per_article"][0]["notes"]
        self.assertEqual(len([n for n in notes if "ausgenommen" in n.lower()]), 1,
                         f"genau EIN Ausnahme-Hinweis (zwei Texte waren der Merge-Bruch): {notes}")
        self.assertTrue(any("ausgenommen" in n.lower() and REASON in n for n in notes), notes)
        self.assertIn("## Hinweise (nicht blockierend)", gate.write_report(result))


class RenderProofSingleSourceTests(unittest.TestCase):
    """WF-53E2 / #780: the render proof judges the frontmatter the run LOADED.

    No second reading of ``article["path"]``, no own parser, no swallowed
    error. The file-less case itself is pinned by #785
    (``test_render_proof_uses_shared_exemption_without_reopening_source_file``);
    here the disk deliberately CONTRADICTS the loaded state in both
    directions – a re-read flips exactly one of them.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.public = self.root / "public"
        html = self.public / "posts" / "messtest" / "index.html"
        html.parent.mkdir(parents=True)
        html.write_text("<html><body><p>Reiner Messtest, kein CTA.</p></body></html>",
                        encoding="utf-8")
        self.md = self.root / "content" / "posts" / "messtest" / "index.md"

    def article(self, fm: str) -> dict:
        return {"slug": "messtest", "path": self.md, "content": "", "fm": fm,
                "body": "", "pillar": "internet-dsl"}

    def verify(self, fm: str) -> dict:
        return gate.verify_article_render(self.article(fm), {}, self.public)

    def write_md(self, fm: str) -> None:
        self.md.parent.mkdir(parents=True, exist_ok=True)
        self.md.write_text(f'---\ntitle: "Messtest"\n{fm}---\n\nKein CTA.\n',
                           encoding="utf-8")

    def test_disk_without_exemption_cannot_overrule_loaded_exemption(self):
        self.write_md("")
        result = self.verify(EXEMPT)
        self.assertEqual(result["problems"], [])
        self.assertTrue(any("ausgenommen" in n for n in result["notes"]))

    def test_exemption_only_on_disk_cannot_overrule_loaded_state(self):
        self.write_md(EXEMPT)
        result = self.verify("pillar: internet-dsl\n")
        self.assertTrue(any("Kein einziger Affiliate-Link" in p for p in result["problems"]))
        self.assertEqual(result["notes"], [])

    def test_contract_is_asked_exactly_once(self):
        with patch.object(contract, "affiliate_exemption",
                          wraps=contract.affiliate_exemption) as spy:
            self.verify(EXEMPT)
        self.assertEqual(spy.call_count, 1,
                         "one evaluation per article – a second one is a second truth")

    def test_contract_errors_are_not_swallowed_into_not_exempt(self):
        with patch.object(contract, "affiliate_exemption",
                          side_effect=RuntimeError("Vertrag defekt")):
            with self.assertRaises(RuntimeError):
                self.verify(EXEMPT)

    def test_detector_selftest_is_green(self):
        # The daily guard runs this file next to `--selftest`; the selftest's
        # in-memory cases are exactly what #776 broke. One red line here and
        # the unit layer knows it too.
        self.assertEqual(gate.run_selftest(), [])


class ProfiCheckA8ContractTests(unittest.TestCase):
    """#764/#780: A8 (minimum one CTA) reads the exemption from the contract.

    Valid → nothing written; invalid → finding and NO injected CTA even in
    FIX mode (the flag states the editorial intent); none → CTA as before.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.blog = Path(tmp.name)
        self.files = {}
        for slug, fm in (("gueltig", EXEMPT), ("halb", "affiliate_exempt: true\n"),
                         ("ohne", "")):
            path = self.blog / "content" / "posts" / slug / "index.md"
            path.parent.mkdir(parents=True)
            path.write_text(f'---\ntitle: "{slug}"\npillar: "internet-dsl"\n{fm}---\n\n'
                            "Text ohne Partnerlink.\n\n## Häufige Fragen\n\nFrage?\n",
                            encoding="utf-8")
            self.files[slug] = path
        self.before = {slug: p.read_bytes() for slug, p in self.files.items()}

    def run_a8(self, fix: bool):
        problems, fixed = [], []
        with patch.object(profi, "BLOG_DIR", str(self.blog)), \
                patch.object(profi, "DO_FIX", fix), \
                patch.object(profi, "PROBLEMS", problems), \
                patch.object(profi, "FIXED", fixed):
            profi._check_cta()
        return problems, fixed

    def test_fix_mode_respects_valid_and_invalid_exemptions(self):
        problems, fixed = self.run_a8(fix=True)
        self.assertEqual(self.files["gueltig"].read_bytes(), self.before["gueltig"])
        self.assertEqual(self.files["halb"].read_bytes(), self.before["halb"],
                         "an invalid exemption must never get an injected CTA")
        self.assertEqual([(c, s) for c, s, _m in problems], [("A8", "halb")])
        self.assertIn("Affiliate-Ausnahme ungültig", problems[0][2])
        self.assertEqual([(c, s) for c, s, _m in fixed], [("A8", "ohne")])
        self.assertIn("](/go/dsl/)", self.files["ohne"].read_text(encoding="utf-8"))

    def test_check_mode_writes_nothing(self):
        problems, fixed = self.run_a8(fix=False)
        self.assertEqual(fixed, [])
        self.assertEqual(sorted(s for _c, s, _m in problems), ["halb", "ohne"])
        for slug, path in self.files.items():
            self.assertEqual(path.read_bytes(), self.before[slug], slug)

    def test_profi_selftest_covers_the_a8_contract(self):
        self.assertEqual(profi._selftest(), [])


class SingleEvaluatorStructureTests(unittest.TestCase):
    """WF-53E2 / #780: one contract, one evaluator – enforced on the code.

    Behaviour tests prove today's code. This class keeps the #776 pattern from
    coming back in any guard: reading the keys itself, importing the
    exemption through another guard, or wrapping the contract in a catch-all
    that turns "could not evaluate" into "not exempt".
    """

    CONTRACT = "affiliate_exemption.py"
    KEYS = {"affiliate_exempt", "affiliate_exempt_reason"}
    ENTRY_POINTS = {"affiliate_exemption", "exemption_for_article", "exemption_for_text"}
    BROAD = {"Exception", "BaseException"}

    @classmethod
    def setUpClass(cls):
        cls.modules = {}
        for path in sorted(SCRIPTS.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "affiliate_exempt" in text or "exemption" in text:
                cls.modules[path.name] = ast.parse(text, filename=str(path))

    @staticmethod
    def _call_name(node: ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr
        return func.id if isinstance(func, ast.Name) else None

    def _is_broad(self, handler: ast.ExceptHandler) -> bool:
        kind = handler.type
        if kind is None:
            return True
        names = kind.elts if isinstance(kind, ast.Tuple) else [kind]
        return any(isinstance(n, ast.Name) and n.id in self.BROAD for n in names)

    def test_scan_sees_the_known_consumers(self):
        for name in (self.CONTRACT, "affiliate_integrity_gate.py",
                     "affiliate_link_check.py", "affiliate_profi_check.py"):
            self.assertIn(name, self.modules, "the scan must cover " + name)

    def test_only_the_contract_reads_the_exemption_keys(self):
        verstoesse = [
            f"{name}:{node.lineno} liest {node.value!r} selbst"
            for name, tree in self.modules.items() if name != self.CONTRACT
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and node.value in self.KEYS]
        self.assertEqual(verstoesse, [], "second evaluator – use affiliate_exemption.py")

    def test_exemption_is_imported_from_the_contract_only(self):
        verstoesse = [
            f"{name}:{node.lineno} importiert {alias.name} aus {node.module}"
            for name, tree in self.modules.items()
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            for alias in node.names
            if alias.name in self.ENTRY_POINTS and node.module != "affiliate_exemption"]
        self.assertEqual(verstoesse, [], "import the contract, not another guard's adapter")

    def test_contract_calls_are_never_wrapped_in_a_catch_all(self):
        verstoesse = []
        for name, tree in self.modules.items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.Try):
                    continue
                calls = {self._call_name(c) for stmt in node.body
                         for c in ast.walk(stmt) if isinstance(c, ast.Call)}
                if calls & self.ENTRY_POINTS and any(self._is_broad(h) for h in node.handlers):
                    verstoesse.append(f"{name}:{node.lineno}")
        self.assertEqual(verstoesse, [],
                         "a swallowed contract error silently becomes 'not exempt' (#780)")

    def test_guards_import_the_contract_module(self):
        for name in ("affiliate_integrity_gate.py", "affiliate_link_check.py",
                     "affiliate_profi_check.py"):
            imports = {alias.name for node in ast.walk(self.modules[name])
                       if isinstance(node, ast.Import) for alias in node.names}
            self.assertIn("affiliate_exemption", imports, name)


class RenderProofSinglePathTests(unittest.TestCase):
    """#778: Der Render-Beweis liest die Ausnahme AUSSCHLIESSLICH aus dem
    Vertrag `affiliate_exemption.py` – nie ein zweites Mal von der Platte.

    Am 16.10.2026 (WF-D4E0 #778) lag in `verify_article_render` zusätzlich
    ein dateibezirkelter Zweitausnahmeweg (#764): er überschrieb das
    Vertragsergebnis mit `exempt = False`, sobald `article['path']` nicht
    lesbar war, und warf die gültige Ausnahme still weg – der Selbsttest
    meldete „Kein einziger Affiliate-Link“ für einen redaktionell
    ausgenommenen Artikel. Zwei Ablesewege, zwei Wahrheiten (#714/#766).
    """

    def _artikel(self, fm):
        return {"slug": "messtest", "path": "/existiert/nicht/index.md",
                "content": "", "fm": fm, "body": "", "pillar": "internet-dsl"}

    def _public(self, tmp):
        public = Path(tmp) / "public"
        ziel = public / "posts" / "messtest"
        ziel.mkdir(parents=True)
        (ziel / "index.html").write_text(
            "<html><body><p>Reiner Messtest, kein CTA.</p></body></html>",
            encoding="utf-8")
        return public

    def test_in_memory_ausnahme_ohne_datei_bleibt_gueltig(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = self._public(tmp)
            res = gate.verify_article_render(self._artikel(EXEMPT), {}, public)
        self.assertFalse(
            any("Kein einziger Affiliate-Link" in p for p in res["problems"]),
            f"gültige Ausnahme ohne lesbare Datei verloren (#778): {res['problems']}")
        self.assertTrue(res["exempt"])

    def test_ausnahme_ist_als_hinweis_sichtbar(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = self._public(tmp)
            res = gate.verify_article_render(self._artikel(EXEMPT), {}, public)
        self.assertTrue(any("ausgenommen" in n for n in res["notes"]),
                        f"Ausnahme unsichtbar (#762/#778): {res['notes']}")
        self.assertTrue(any(REASON in n for n in res["notes"]),
                        f"Begründung fehlt im Hinweis: {res['notes']}")

    def test_ohne_ausnahme_bleibt_der_mindestbestand_ein_fund(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = self._public(tmp)
            res = gate.verify_article_render(self._artikel(""), {}, public)
        self.assertTrue(any("Kein einziger Affiliate-Link" in p
                            for p in res["problems"]), res["problems"])


class BestandGateSelftestDependencyTests(unittest.TestCase):
    def test_bestand_gate_reports_underlying_integrity_selftest_failure(self):
        import bestand_gate as bestand

        failure = SimpleNamespace(
            returncode=2,
            stdout="fixture output",
            stderr="fixture diagnostic",
        )
        with patch.object(bestand.subprocess, "run", return_value=failure) as run:
            ok, message = bestand.detector_selftest()

        self.assertFalse(ok)
        self.assertIn("fixture output", message)
        self.assertIn("fixture diagnostic", message)
        self.assertIn("affiliate_integrity_gate.py --selftest", message)
        self.assertNotIn("Render-Hook nötig", message,
                         "ein beliebiger Selbsttestfehler darf nicht als Hook-Drift etikettiert werden")
        run.assert_called_once()

    def test_bestand_gate_uses_the_current_green_integrity_contract(self):
        import bestand_gate as bestand

        ok, message = bestand.detector_selftest()

        self.assertTrue(ok, message)
        self.assertIn("grün", message)


if __name__ == "__main__":
    unittest.main()
