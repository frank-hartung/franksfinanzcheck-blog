import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from crawler import PageParser, crawl, csv_text, normalize_url, parse_sitemap, public_host
from compare import compare_pages


def response(url, body='', status=200, content_type='text/html', final_url=None, headers=None):
    return {'status': status, 'body': body, 'content_type': content_type, 'final_url': final_url or url,
            'bytes': len(body), 'truncated': False, 'elapsed_ms': 3, 'x_robots': '', 'headers': headers or {}}


class CrawlerTests(unittest.TestCase):
    def test_normalize_strips_fragments_trackers_and_rejects_unsafe_urls(self):
        self.assertEqual(normalize_url('HTTPS://Example.com/a?utm_source=x&id=3#x'), 'https://example.com/a?id=3')
        self.assertIsNone(normalize_url('javascript:alert(1)'))
        self.assertIsNone(normalize_url('https://user:pass@example.com/'))
        self.assertIsNone(normalize_url('https://example.com:invalid/'))
        self.assertEqual(normalize_url('https://[2606:4700:4700::1111]/'), 'https://[2606:4700:4700::1111]/')

    def test_local_address_is_not_public(self):
        self.assertFalse(public_host('http://127.0.0.1/'))
        self.assertFalse(public_host('http://[::1]/'))

    def test_parser_extracts_onpage_social_image_heading_and_schema_fields(self):
        parser = PageParser()
        parser.feed('''<!doctype html><html lang="de"><head><title> Hallo   Welt </title>
          <meta name="description" content="Kurz"><meta name="robots" content="noindex">
          <meta name="viewport" content="width=device-width"><meta property="og:title" content="OG">
          <meta property="og:description" content="Social"><meta name="twitter:card" content="summary">
          <link rel="canonical" href="/x"><link rel="alternate" hreflang="de" href="/x"></head>
          <body><h1>Erste <b>Seite</b></h1><h2>Kapitel</h2><h4>Sprung</h4>
          <a href="/intern" rel="nofollow">Weiter</a><img src="/bild.jpg"><img src="/deko.png" alt="">
          <script type="application/ld+json">{"@type":"Article"}</script><p>Guter sichtbarer Seitentext</p></body></html>''')
        data = parser.result()
        self.assertEqual(data['title'], 'Hallo Welt')
        self.assertEqual(data['description'], 'Kurz')
        self.assertEqual(data['h1'], ['Erste Seite'])
        self.assertEqual(data['h2'], ['Kapitel'])
        self.assertEqual(data['canonical'], ['/x'])
        self.assertEqual(data['links'], [{'href':'/intern','rel':'nofollow','anchor':'Weiter'}])
        self.assertEqual(data['images_missing_alt'], 1)
        self.assertEqual(data['images_empty_alt'], 1)
        self.assertEqual(data['schema_types'], ['Article'])
        self.assertEqual(data['lang'], 'de')
        self.assertTrue(data['viewport'] and data['doctype'])
        self.assertEqual(data['hreflang'], [{'lang':'de','href':'/x'}])

    def test_sitemap_only_same_host_urls(self):
        sitemap = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/a</loc></url><url><loc>https://other.example/b</loc></url></urlset>'
        self.assertEqual(parse_sitemap(sitemap, 'example.com'), ['https://example.com/a'])

    @patch('crawler.public_host', return_value=True)
    @patch('crawler.time.sleep')
    def test_crawl_discovers_pages_respects_nofollow_and_marks_broken_links(self, _sleep, _public):
        html = '<!doctype html><html lang="de"><head><title>Start</title><meta name="description" content="' + ('guter Text ' * 12) + '"><meta name="viewport" content="width=device-width"><link rel="canonical" href="/"><meta property="og:title" content="Start"><meta property="og:description" content="Beschreibung"><meta name="twitter:card" content="summary"></head><body><h1>Start</h1><a href="/missing">Missing</a><a href="/ok" rel="nofollow">No follow</a></body></html>'
        def fake_fetch(_opener, url, _timeout=12):
            if url.endswith('/robots.txt'): return response(url, 'User-agent: *\nAllow: /', content_type='text/plain')
            if url.endswith('/missing'): return response(url, '<title>Missing</title>', 404)
            return response(url, html)
        with patch('crawler.fetch', side_effect=fake_fetch):
            result = crawl('https://example.com/', max_pages=10, delay=0.2)
        by_url = {row['url']: row for row in result['pages']}
        self.assertIn('https://example.com/missing', by_url)
        self.assertNotIn('https://example.com/ok', by_url)
        self.assertEqual(by_url['https://example.com/missing']['status'], 404)
        self.assertIn('Broken internal link', by_url['https://example.com/']['issues'])
        self.assertEqual(by_url['https://example.com/']['outlinks'], 2)

    @patch('crawler.public_host', return_value=True)
    @patch('crawler.time.sleep')
    def test_sitemap_index_crawl_and_orphan_detection(self, _sleep, _public):
        def fake_fetch(_opener, url, _timeout=12):
            if url.endswith('/robots.txt'):
                return response(url, 'User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap-index.xml', 200, 'text/plain')
            if url.endswith('/sitemap-index.xml'):
                return response(url, '<sitemapindex><sitemap><loc>https://example.com/part.xml</loc></sitemap></sitemapindex>', content_type='application/xml')
            if url.endswith('/part.xml'):
                return response(url, '<urlset><url><loc>https://example.com/</loc></url><url><loc>https://example.com/orphan/</loc></url></urlset>', content_type='application/xml')
            link = '<a href="/linked/">Link</a>' if url == 'https://example.com/' else ''
            html = '<!doctype html><html lang="de"><head><title>Eine Seite</title><meta name="description" content="' + ('Gute Kurzbeschreibung ' * 6) + '"><meta name="viewport" content="width=device-width"><link rel="canonical" href="' + url + '"><meta property="og:title" content="Title"><meta property="og:description" content="Description"><meta name="twitter:card" content="summary"></head><body><h1>Überschrift</h1>' + link + '</body></html>'
            return response(url, html)
        with patch('crawler.fetch', side_effect=fake_fetch):
            result = crawl('https://example.com/', max_pages=10, delay=0.2)
        self.assertEqual(result['sitemaps_found'], 2)
        orphan = next(p for p in result['pages'] if p['url'].endswith('/orphan/'))
        self.assertTrue(orphan['orphan'])
        self.assertEqual(orphan['depth_origin'], 'Sitemap')
        self.assertIn('Sitemap orphan', orphan['issues'])
        linked = next(p for p in result['pages'] if p['url'].endswith('/linked/'))
        self.assertEqual(linked['depth'], 1)
        self.assertEqual(linked['depth_origin'], 'Start-URL')

    @patch('crawler.public_host', return_value=True)
    @patch('crawler.time.sleep')
    def test_optional_external_head_check_is_reported(self, _sleep, _public):
        html = '<!doctype html><html lang="de"><head><title>Start</title><meta name="description" content="' + ('guter Text ' * 12) + '"><meta name="viewport" content="width=device-width"><link rel="canonical" href="/"><meta property="og:title" content="Start"><meta property="og:description" content="Beschreibung"><meta name="twitter:card" content="summary"></head><body><h1>Start</h1><a href="https://other.example/out">Externer Link</a></body></html>'
        def fake_fetch(_opener, url, _timeout=12): return response(url, 'User-agent: *\nAllow: /', content_type='text/plain') if url.endswith('/robots.txt') else response(url, html)
        with patch('crawler.fetch', side_effect=fake_fetch), patch('crawler._head_check', return_value={'status':404,'final_url':'https://other.example/out','elapsed_ms':7}) as checker:
            result = crawl('https://example.com/', max_pages=2, delay=0.2, check_external=True)
        self.assertEqual(checker.call_count, 1)
        self.assertEqual(result['external_checked'], 1)
        self.assertIn('Broken external link', result['pages'][0]['issues'])
        self.assertEqual(result['links'][0]['status'], 404)

    def test_report_comparison_identifies_added_removed_and_changed(self):
        baseline = [{'url':'https://example.com/a','title':'Old','status':200,'description':'same'}, {'url':'https://example.com/gone','title':'Gone','status':200}]
        current = [{'url':'https://example.com/a#fragment','title':'New','status':200,'description':'same'}, {'url':'https://example.com/new','title':'Added','status':200}]
        result = compare_pages(current, baseline)
        self.assertEqual(result['summary'], {'added':1,'removed':1,'changed':1,'unchanged':0})
        self.assertEqual(result['changed'][0]['changes'][0]['field'], 'title')
        self.assertEqual(result['added'], ['https://example.com/new'])
        self.assertEqual(result['removed'], ['https://example.com/gone'])

    def test_csv_quotes_and_formula_protection(self):
        text = csv_text([{'url':'https://example.com/','title':'A, B','status':200}])
        self.assertIn('"A, B"', text)
        self.assertTrue(text.startswith('url,status,title'))
        protected = csv_text([{'url':'https://example.com/','title':'=HYPERLINK("https://bad")','status':200}])
        self.assertIn("'=HYPERLINK", protected)


if __name__ == '__main__':
    unittest.main()
