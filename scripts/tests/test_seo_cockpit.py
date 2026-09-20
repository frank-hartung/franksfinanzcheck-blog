"""Hermetische Regressionstests: keine APIs, kein Hugo, keine externen Pakete."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seo_cockpit as seo
import schema_seo_gate as gate

BASE = 'https://example.org/'


def page(path='/', title='Ein individueller Ratgeber für deinen Alltag', extra='', body='', robots='index, follow'):
    return f'''<html lang=de><head><title>{title}</title>
<meta name=robots content="{robots}"><meta name=description content="Dieser ausführliche Ratgeber erklärt dir wichtige Grundlagen und nächste Schritte für den Alltag.">
<link rel=canonical href="{BASE.rstrip('/') + path}">
<meta property=og:title content="{title}"><meta property=og:description content="Beschreibung">
<meta property=og:image content="{BASE}cover.jpg"><meta name=twitter:card content=summary_large_image>
{extra}</head><body><h1>{title}</h1>{body}</body></html>'''


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.build = Path(self.tmp.name) / 'public'
        self.build.mkdir()
        self.write('index.html', page())
        self.sitemap('/')

    def write(self, name, text):
        p = self.build / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def sitemap(self, *paths):
        self.write('sitemap.xml', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{BASE.rstrip("/") + path}</loc></url>' for path in paths) + '</urlset>')

    def run_audit(self):
        return seo.audit(self.build, BASE)

    def codes(self):
        return {f['code'] for f in self.run_audit()['findings']}

    def test_clean_minified_document(self):
        self.assertEqual(self.run_audit()['findings'], [])

    def test_missing_build_fails_closed(self):
        (self.build / 'sitemap.xml').unlink()
        with self.assertRaises(ValueError): self.run_audit()

    def test_parser_decodes_entities_and_graph(self):
        doc = seo.Document('<title>A &amp; B</title><meta name=robots content=NOINDEX><script type=application/ld+json>{"@graph":[{"@type":"Article"}]}</script>')
        self.assertEqual(doc.title, 'A & B')
        self.assertTrue(doc.noindex)
        self.assertIn('Article', seo.schema_types(doc.schemas))

    def test_pager_regression(self):
        self.write('page/2/index.html', page('/page/2/').replace(BASE + 'page/2/', BASE))
        self.assertTrue({'index-control', 'pager-canonical'} <= self.codes())
        self.write('page/2/index.html', page('/page/2/', robots='noindex, follow'))
        self.assertNotIn('index-control', self.codes())
        self.assertNotIn('pager-canonical', self.codes())

    def test_existing_gate_also_detects_pager(self):
        p = self.write('page/2/index.html', page('/page/2/'))
        with patch.object(gate, 'PUBLIC', str(self.build)):
            findings = gate.Findings()
            gate.check_page(str(p), BASE.rstrip('/'), findings)
        self.assertTrue(any(f[0] == 'S6' for f in findings.hard))

    def test_duplicate_metadata_only_on_indexable_pages(self):
        self.write('second/index.html', page('/second/'))
        self.assertIn('duplicate-title', self.codes())
        self.write('second/index.html', page('/second/', robots='noindex'))
        self.assertNotIn('duplicate-title', self.codes())

    def test_sitemap_target_missing_noindex_and_redirect(self):
        self.sitemap('/', '/missing/', '/tags/a/', '/old/')
        self.write('tags/a/index.html', page('/tags/a/', robots='noindex'))
        self.write('old/index.html', '<meta http-equiv=refresh content="0;url=/">')
        self.assertEqual(sum(f['code'] == 'sitemap-target' for f in self.run_audit()['findings']), 3)

    def test_sitemap_duplicate_and_canonical_mismatch(self):
        self.sitemap('/', '/')
        self.write('index.html', page().replace(f'href="{BASE}"', f'href="{BASE}other/"'))
        self.assertTrue({'sitemap-duplicate', 'sitemap-canonical', 'canonical-target'} <= self.codes())

    def test_relative_links_fragments_and_depth(self):
        self.write('index.html', page(body='<a href="a/">A</a>'))
        self.write('a/index.html', page('/a/', title='Anderer passender Titel für Unterseite', body='<a href="../#fehlt">Defekt</a><a href="../missing/">Fehlt</a><img src="/missing.jpg">'))
        self.sitemap('/', '/a/')
        report = self.run_audit()
        a = next(p for p in report['pages'] if p['path'] == '/a/')
        self.assertEqual((a['depth'], a['incoming']), (1, 1))
        self.assertTrue({'broken-link', 'broken-anchor', 'image-missing', 'image-alt'} <= self.codes())

    def test_valid_encoded_fragment_and_decorative_image(self):
        self.write('index.html', page(body='<h2 id="größe">Test</h2><a href="#gr%C3%B6%C3%9Fe">Link</a><img alt="" src="data:image/png;base64,xx">'))
        self.assertEqual(self.codes(), set())

    def test_external_similar_host_not_internal(self):
        self.write('index.html', page(body='<a href="https://example.org.evil/missing/">Extern</a>'))
        self.assertNotIn('broken-link', self.codes())
        self.assertIsNone(seo.local_file(self.build, 'https://example.org.evil/a/', BASE))

    def test_directory_traversal_and_wrong_origin(self):
        for url in [BASE + '%2e%2e/secret', 'http://example.org/', 'https://example.org:444/a']:
            self.assertIsNone(seo.local_file(self.build, url, BASE))

    def test_invalid_schema_and_multiple_canonical(self):
        self.write('index.html', page(extra='<script type=application/ld+json>{oops}</script><link rel=canonical href="/">'))
        self.assertTrue({'schema-json', 'canonical-count'} <= self.codes())

    def test_static_oauth_excluded_but_regular_noindex_checked(self):
        self.write('pinterest-oauth/index.html', '<html><meta name=robots content=noindex>OAuth</html>')
        self.assertEqual(len(self.run_audit()['pages']), 1)
        self.write('tags/a/index.html', '<html><meta name=robots content=noindex>Taxonomy</html>')
        self.assertIn('canonical-count', self.codes())

    def test_report_escapes_script_injection(self):
        data = self.run_audit()
        data['pages'][0]['title'] = '</script><script>alert(1)</script>'
        output = Path(self.tmp.name) / 'output'
        seo.write_report(data, output)
        html = (output / 'index.html').read_text()
        self.assertNotIn(data['pages'][0]['title'], html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertEqual(json.loads((output / 'audit.json').read_text())['pages'][0]['title'], data['pages'][0]['title'])

    def test_csv_formula_injection(self):
        text = seo.safe_csv([['=1+1', '  @SUM(1)', '+2', '-3', 'normal']])
        self.assertEqual(text, "'=1+1,'  @SUM(1),'+2,'-3,normal\r\n")

    def test_all_findings_have_owner_and_priority(self):
        self.write('index.html', '<html>Kaputt</html>')
        for f in self.run_audit()['findings']:
            self.assertIn(f['owner'], ('auto', 'human'))
            self.assertIn(f['severity'], ('P1', 'P2', 'P3'))
            self.assertEqual(f['channel'], 'seo-cockpit')
            self.assertTrue(f['action'])


if __name__ == '__main__':
    unittest.main()
