"""Regressionen des echten Defekts sowie Daten-/Build-Vertrag der Themenwelten."""
from copy import deepcopy
from html import escape
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import themenwelten_guard as guard

DATA = json.loads((ROOT / "data/themenwelten.json").read_text(encoding="utf-8"))


class ThemenweltenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / "public"
        (self.root / "data").mkdir()
        (self.root / "data/themenwelten.json").write_text(json.dumps(DATA), encoding="utf-8")
        (self.root / "content/posts").mkdir(parents=True)
        (self.root / "content/posts/_index.md").write_text("---\ntitle: Blog\n---\nHier findest du alle Ratgeber.", encoding="utf-8")
        for topic in DATA["topics"]:
            self.write(f"content/pillar/{topic['id']}/index.md", "---\ndraft: false\n---\nRatgeber")
        self.build_fixture()

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        return file

    def build_fixture(self, prefix="/"):
        for topic in DATA["topics"]:
            key = topic["id"]
            self.write(f"public/pillar/{key}/index.html", f'<h1>Ratgeber</h1><a aria-label="Weiterlesen: Artikel" href="{prefix}posts/{key}-artikel/">Artikel</a>')
            self.write(f"public/posts/{key}-artikel/index.html", "<h1>Artikel</h1>")
        for home in (False, True):
            heading = "home-themenwelten" if home else guard.TITLE_ID
            cards = []
            for topic in DATA["topics"]:
                key = topic["id"]
                card_id = heading + "-" + key
                cards.append(f'''<li><a class=ff-topic-card data-topic="{key}" href="{prefix}pillar/{key}/"
                  aria-labelledby="{card_id}-title" aria-describedby="{card_id}-description {card_id}-count">
                  <h3 id="{card_id}-title">{escape(topic['title'])}</h3>
                  <p class=ff-topic-description id="{card_id}-description">{escape(topic['description'])}</p>
                  <span class=ff-topic-count id="{card_id}-count" data-article-count=1>1 Artikel</span>
                  <span aria-hidden=true><svg><path d="M0 0"/></svg>Zum Thema</span></a></li>''')
            markup = f'''<main><section class=ff-topics aria-labelledby="{heading}">
              <span id={guard.LEGACY_ID} aria-hidden=true></span>
              <h2 id="{heading}">{DATA['title']}</h2><ul>{''.join(cards)}</ul></section>
              <header id=neueste-artikel><h2>Neueste Ratgeber</h2></header>
              <div class=ff-posts-feed></div></main>'''
            self.write("public/index.html" if home else "public/posts/index.html", markup)
        self.write("public/posts/page/2/index.html", f'<a href="{prefix}posts/#{guard.TITLE_ID}">Themenwelten</a><div class=ff-posts-feed></div>')

    def mutate_html(self, before, after):
        file = self.public / "posts/index.html"
        text = file.read_text(encoding="utf-8")
        self.assertIn(before, text)
        file.write_text(text.replace(before, after, 1), encoding="utf-8")

    def findings(self):
        return guard.validate_build(self.public, DATA)

    def test_valid_sources_and_minified_html(self):
        self.assertEqual(guard.validate_source(self.root)[1], [])
        self.assertEqual(self.findings(), [])

    def test_frontmatter_comment_is_not_a_second_markdown_heading(self):
        self.write("content/posts/_index.md", "---\n# Themen aus data/themenwelten.json\ntitle: Blog\n---\nHier findest du alle Ratgeber.")
        self.assertEqual(guard.validate_source(self.root)[1], [])
        self.write("content/posts/_index.md", "---\ntitle: Blog\n---\n## Deine 6 Themenwelten\n")
        self.assertTrue(guard.validate_source(self.root)[1])

    def test_bad_headings_including_original_incident(self):
        for title in ("Ddeine6 Themenwelten", "Deine6 Themenwelten", "Deine 7 Themenwelten", ""):
            with self.subTest(title=title):
                data = deepcopy(DATA)
                data["title"] = title
                self.assertTrue(guard.validate_data(data))

    def test_original_intro_corruption_is_blocking_not_report_only(self):
        file = self.root / "content/posts/_index.md"
        for typo in ("Hhierfindest du", "HHerfindestdu"):
            with self.subTest(typo=typo):
                file.write_text(typo + " alle Ratgeber.", encoding="utf-8")
                before = file.read_bytes()
                self.assertEqual(guard.main(["--root", str(self.root), "--source-only"]), 1)
                self.assertEqual(file.read_bytes(), before, "Das Gate schreibt keine Texte um.")

    def test_missing_duplicate_and_unknown_topics(self):
        for change in (lambda topics: topics.pop(),
                       lambda topics: topics.append(deepcopy(topics[0])),
                       lambda topics: topics[0].update(id=topics[1]["id"]),
                       lambda topics: topics[0].update(id="../../escape")):
            data = deepcopy(DATA)
            change(data["topics"])
            self.assertTrue(guard.validate_data(data))

    def test_invalid_data_types_and_empty_or_markup_text(self):
        for data in (None, [], {"topics": None}, {"topics": [None] * 6}):
            self.assertTrue(guard.validate_data(data))
        for value in (None, [], "", "   ", "<script>alert(1)</script>", "SStrom sparen"):
            data = deepcopy(DATA)
            data["topics"][0]["description"] = value
            self.assertTrue(guard.validate_data(data))

    def test_no_build_is_an_error(self):
        self.assertTrue(guard.validate_build(self.root / "missing", DATA))

    def test_missing_source_and_invalid_json(self):
        (self.root / "content/pillar/mietwagen/index.md").unlink()
        self.assertTrue(guard.validate_source(self.root)[1])
        (self.root / "data/themenwelten.json").write_text("{broken", encoding="utf-8")
        self.assertTrue(guard.validate_source(self.root)[1])

    def test_missing_and_redirected_target(self):
        file = self.public / "pillar/mietwagen/index.html"
        file.unlink()
        self.assertTrue(any("Themen-Ziel fehlt" in error for error in self.findings()))
        file.write_text('<meta http-equiv=refresh content="0;url=/">', encoding="utf-8")
        self.assertTrue(any("kein veröffentlichter Ratgeber" in error for error in self.findings()))

    def test_bad_heading_and_duplicate_ids_in_rendered_html(self):
        self.mutate_html("Deine 6 Themenwelten", "Ddeine6 Themenwelten")
        self.assertTrue(self.findings())
        self.build_fixture()
        self.mutate_html("</main>", '<span id="deine-6-themenwelten"></span></main>')
        self.assertTrue(self.findings())

    def test_wrong_url_and_nested_controls(self):
        self.mutate_html('href="/pillar/strom-sparen/"', 'href="https://example.com/"')
        self.assertTrue(self.findings())
        self.build_fixture()
        self.mutate_html("Zum Thema", '<a href="/">Zum Thema</a>')
        self.assertTrue(any("verschachtelten" in error for error in self.findings()))

    def test_missing_name_description_or_hidden_card(self):
        for before, after in (
            ('aria-labelledby="deine-6-themenwelten-strom-sparen-title"', 'aria-labelledby="missing"'),
            ('class=ff-topic-description', 'class=missing'),
            ('class=ff-topic-card', 'class=ff-topic-card hidden'),
        ):
            with self.subTest(before=before):
                self.build_fixture()
                self.mutate_html(before, after)
                self.assertTrue(self.findings())

    def test_live_counter_and_target_article_integrity(self):
        self.mutate_html("data-article-count=1", "data-article-count=999")
        self.assertTrue(any("Artikelzahl" in error for error in self.findings()))
        self.build_fixture()
        (self.public / "posts/strom-sparen-artikel/index.html").unlink()
        self.assertTrue(any("Themen-Artikel fehlt" in error for error in self.findings()))

    def test_zero_articles_keeps_useful_basis_ratgeber(self):
        for topic in DATA["topics"]:
            self.write(f"public/pillar/{topic['id']}/index.html", "<h1>Basis-Ratgeber</h1>")
        for rel in ("index.html", "posts/index.html"):
            file = self.public / rel
            file.write_text(file.read_text(encoding="utf-8").replace("data-article-count=1>1 Artikel", "data-article-count=0>Basis-Ratgeber"), encoding="utf-8")
        self.assertEqual(self.findings(), [])

    def test_legacy_anchor_does_not_leak_typo_into_text(self):
        self.assertEqual(self.findings(), [])
        self.mutate_html(f'id={guard.LEGACY_ID}', 'id=removed-legacy-anchor')
        self.assertTrue(self.findings())

    def test_duplicate_pseudo_filter_and_repeated_intro(self):
        self.mutate_html("</main>", '<nav class=ff-filter-bar></nav></main>')
        self.assertTrue(self.findings())
        self.build_fixture()
        self.write("public/posts/page/2/index.html", '<section class=ff-topics></section>')
        self.assertTrue(any("Folgeseiten" in error for error in self.findings()))

    def test_deploy_checks_sources_and_final_artifact_without_soft_failure(self):
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        source = re.search(r"- name: Themenwelten – Quellvertrag[^\n]*\n\s+run: ([^\n]+)", workflow)
        final = re.search(r"- name: Themenwelten – finales Veröffentlichungs-Gate\n\s+run: ([^\n]+)", workflow)
        self.assertIsNotNone(source)
        self.assertIsNotNone(final)
        self.assertEqual(source[1], "python3 scripts/themenwelten_guard.py --source-only")
        self.assertEqual(final[1], "python3 scripts/themenwelten_guard.py --public public")
        builds = list(re.finditer(r"run: hugo --minify", workflow))
        self.assertTrue(builds)
        self.assertLess(source.start(), builds[0].start())
        self.assertGreater(final.start(), builds[-1].start())
        self.assertLess(final.start(), workflow.index("- name: Deploy auf gh-pages"))

    def test_subdirectory_links_and_path_traversal(self):
        self.build_fixture("/blog/")
        self.assertEqual(guard.validate_build(self.public, DATA, "/blog/"), [])
        self.assertIsNone(guard.output_path(self.public, "/blog/../../outside/", "/blog/"))
        self.assertIsNone(guard.output_path(self.public, "//example.com/", "/"))


HUGO = os.environ.get("HUGO_BINARY") or shutil.which("hugo")


@unittest.skipUnless(HUGO, "Hugo fehlt – reine Python-Vertragstests laufen trotzdem; CI installiert Hugo.")
class HugoPublicationTests(unittest.TestCase):
    """Echte Hugo-Builds: Quelle kopieren, niemals den Checkout manipulieren."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.content = self.dir / "content"
        shutil.copytree(ROOT / "content", self.content)
        self.public = self.dir / "public"

    def build(self):
        return subprocess.run([HUGO, "--minify", "--contentDir", str(self.content),
                               "--destination", str(self.public)], cwd=ROOT,
                              capture_output=True, text=True, timeout=90)

    def test_drafts_future_and_expired_articles_not_counted_or_linked(self):
        for slug, metadata in (
            ("qa-draft", "date: 2020-01-01\ndraft: true"),
            ("qa-future", "date: 2999-01-01\ndraft: false"),
            ("qa-future-publish", "date: 2020-01-01\npublishDate: 2999-01-01\ndraft: false"),
            ("qa-expired", "date: 2020-01-01\nexpiryDate: 2021-01-01\ndraft: false"),
        ):
            file = self.content / f"posts/{slug}/index.md"
            file.parent.mkdir()
            file.write_text(f'---\ntitle: "QA nicht veröffentlichen"\npillar: strom-sparen\n{metadata}\n---\nTest.\n', encoding="utf-8")
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(guard.validate_build(self.public, DATA), [])
        for slug in ("qa-draft", "qa-future", "qa-future-publish", "qa-expired"):
            self.assertFalse((self.public / f"posts/{slug}/index.html").exists())
            self.assertNotIn(slug, (self.public / "pillar/strom-sparen/index.html").read_text(encoding="utf-8"))

    def test_missing_pillar_fails_the_actual_hugo_build(self):
        shutil.rmtree(self.content / "pillar/mietwagen")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Themenwelten:", result.stderr)

    def test_draft_pillar_fails_the_actual_hugo_build(self):
        file = self.content / "pillar/mietwagen/index.md"
        file.write_text(file.read_text(encoding="utf-8").replace("draft: false", "draft: true"), encoding="utf-8")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Themenwelten:", result.stderr)

    def test_future_pillar_fails_the_actual_hugo_build(self):
        file = self.content / "pillar/mietwagen/index.md"
        text = file.read_text(encoding="utf-8").replace("date: 2026-08-08", "date: 2999-01-01")
        file.write_text(text, encoding="utf-8")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Themenwelten:", result.stderr)


if __name__ == "__main__":
    unittest.main()
