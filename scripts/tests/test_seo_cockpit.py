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
<meta name=robots content="{robots}"><meta name=description content="Dieser ausführliche Ratgeber erklärt dir wichtige Grundlagen, typische Fehler und die nächsten Schritte für deinen Alltag.">
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
        doc = seo.Document('<html><head><title>A &amp; B</title></head><body><meta name=robots content=NOINDEX><script type=application/ld+json>{"@graph":[{"@type":"Article"}]}</script></body></html>')
        self.assertEqual(doc.title, 'A & B')
        self.assertTrue(doc.noindex)
        self.assertIn('Article', seo.schema_types(doc.schemas))

    def test_parser_ignores_svg_titles_when_reading_document_title(self):
        doc = seo.Document(
            '<html><head><title>Der echte Seitentitel</title></head><body>'
            '<svg role="img"><title>Sehr lange SVG-Beschreibung, die kein Seitentitel ist</title>'
            '<g><title>Weiterer SVG-Titel</title></g></svg>'
            '<title>Ungültiger Titel außerhalb des Head</title></body></html>'
        )
        self.assertEqual(doc.title, 'Der echte Seitentitel')

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

    def test_sitemap_ignores_image_loc_entries(self):
        # GEO/SEO-PREMIUM 21.09.2026: Google-Bild-Tags (image:loc) sind
        # Discovery-Hinweise, keine Seiten – sie dürfen weder als
        # sitemap-target noch als Duplikat gewertet werden.
        self.write('sitemap.xml',
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                   'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                   '<url><loc>https://example.org/</loc>'
                   '<image:image><image:loc>https://example.org/images/covers/a.jpg</image:loc>'
                   '<image:title>Beispiel &amp; Test</image:title></image:image>'
                   '</url></urlset>')
        self.assertEqual(self.run_audit()['findings'], [])

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

    # ------------------------------------------------------------------
    #  Screaming-Frog-Spiegel, 27.10.2026
    #  Ein fremder Crawl meldete vier Dinge, die dieses Cockpit nicht sah:
    #  Description > 155 Zeichen, Description > 985 px, internen Link ohne
    #  Ankertext und „mehrere H2". Die drei ersten sind echte Befunde, das
    #  vierte ist eine Rangfolgen-Frage. Genau so prüft es das Cockpit jetzt.
    # ------------------------------------------------------------------

    def beschreibung(self, text):
        self.write('index.html', page().replace(
            'content="Dieser ausführliche Ratgeber erklärt dir wichtige Grundlagen, typische Fehler und die nächsten Schritte für deinen Alltag."',
            f'content="{text}"'))

    def test_description_ueber_155_zeichen_ist_p2(self):
        self.beschreibung('S' * 156)
        befund = [f for f in self.run_audit()['findings'] if f['code'] == 'description-length']
        self.assertEqual(len(befund), 1)
        self.assertEqual(befund[0]['severity'], 'P2')
        self.assertIn('156 Zeichen', befund[0]['detail'])

    def test_description_ueber_985_pixel_ist_p2(self):
        # 135 Zeichen – innerhalb der Zeichengrenze, ausserhalb des Snippets.
        breit = ('Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe und Wartung '
                 'zusammengehören. Wer Wohnraum warm hält, spart mit Wärmedämmung.')
        self.assertLessEqual(len(breit), seo.serp_limits.DESC_MAX_ZEICHEN)
        self.beschreibung(breit)
        befund = [f for f in self.run_audit()['findings'] if f['code'] == 'description-breite']
        self.assertEqual(len(befund), 1)
        self.assertIn('985', befund[0]['detail'])

    def test_description_ohne_breitenmass_ist_hinweis(self):
        self.beschreibung('Dieser ausführliche Ratgeber erklärt dir wichtige Grundlagen '
                          'und die nächsten Schritte für deinen Alltag. 💡')
        self.assertIn('description-messbar', self.codes())

    def test_interner_link_ohne_ankertext_ist_p2(self):
        self.write('ziel/index.html', page('/ziel/', title='Ein eigener Titel für die Zielseite'))
        self.sitemap('/', '/ziel/')
        self.write('index.html', page(body='<a class="entry-link" aria-label="Weiterlesen: Ziel" href="ziel/"></a>'))
        befund = [f for f in self.run_audit()['findings'] if f['code'] == 'link-no-anchor']
        self.assertEqual(len(befund), 1)
        self.assertEqual(befund[0]['severity'], 'P2')
        self.assertIn('nur aria-label', befund[0]['detail'])

    def test_sr_only_text_und_bild_alt_sind_ankertext(self):
        self.write('ziel/index.html', page('/ziel/', title='Ein eigener Titel für die Zielseite'))
        self.sitemap('/', '/ziel/')
        self.write('index.html', page(
            body='<a href="ziel/"><span class="sr-only">Weiterlesen: Ziel</span></a>'
                 '<a href="ziel/"><img src="data:image/gif;base64,R0lGOD" alt="Ziel"></a>'))
        self.assertNotIn('link-no-anchor', self.codes())

    def test_externer_link_ohne_text_ist_kein_befund(self):
        self.write('index.html', page(body='<a href="https://example.com/x"><svg></svg></a>'))
        self.assertNotIn('link-no-anchor', self.codes())

    def test_icon_title_zaehlt_nicht_als_ankertext(self):
        # Der <title> im SVG ist ein Tooltip der Grafik, kein Linktext.
        self.write('ziel/index.html', page('/ziel/', title='Ein eigener Titel für die Zielseite'))
        self.sitemap('/', '/ziel/')
        self.write('index.html', page(body='<a href="ziel/"><svg><title>Ziel</title></svg></a>'))
        self.assertIn('link-no-anchor', self.codes())

    def test_ueberschriften_sprung_ist_p3(self):
        self.write('index.html', page(body='<h2>Abschnitt</h2><h4>Zu tief</h4>'))
        befund = [f for f in self.run_audit()['findings'] if f['code'] == 'heading-order']
        self.assertEqual(len(befund), 1)
        self.assertIn('h2→h4', befund[0]['detail'])

    def test_mehrere_h2_sind_kein_befund(self):
        # „H2: Mehrere" aus dem Fremdcrawl ist eine Rangfolgen-Frage, keine
        # Fehlermeldung: HTML erlaubt beliebig viele H2.
        self.write('index.html', page(body='<h2>Eins</h2><h2>Zwei</h2><h2>Drei</h2>'))
        self.assertNotIn('heading-order', self.codes())

    def test_fail_on_sperrt_nur_die_genannten_codes(self):
        self.beschreibung('S' * 156)
        output = Path(self.tmp.name) / 'report'
        with patch.object(sys, 'argv', ['seo_cockpit.py', '--build', str(self.build),
                                        '--output', str(output),
                                        '--fail-on', 'description-length']):
            self.assertEqual(seo.main(), 1)
        with patch.object(sys, 'argv', ['seo_cockpit.py', '--build', str(self.build),
                                        '--output', str(output),
                                        '--fail-on', 'broken-link']):
            self.assertEqual(seo.main(), 0)

    def test_all_findings_have_owner_and_priority(self):
        self.write('index.html', '<html>Kaputt</html>')
        for f in self.run_audit()['findings']:
            self.assertIn(f['owner'], ('auto', 'human'))
            self.assertIn(f['severity'], ('P1', 'P2', 'P3'))
            self.assertEqual(f['channel'], 'seo-cockpit')
            self.assertTrue(f['action'])


class WorkflowContractTests(unittest.TestCase):
    def test_pr_gate_uebergibt_genau_die_gate_codes(self):
        # Eine Sperrliste, die im Workflow anders lautet als im Code, ist
        # keine Sperre: Der PR wäre grün, während das Cockpit rot sieht.
        workflow = (Path(__file__).resolve().parents[2] / '.github' / 'workflows' / 'e2e.yml').read_text(encoding='utf-8')
        self.assertIn('--fail-on ' + ','.join(seo.GATE_CODES), workflow)
        self.assertIn('scripts/metadaten_wache.py', workflow)

    def test_final_build_seo_audit_is_reported_and_ticketed_weekly(self):
        workflow = (Path(__file__).resolve().parents[2] / '.github' / 'workflows' / 'seo-weekly.yml').read_text(encoding='utf-8')
        bestand_build = workflow.index('name: Seite neu bauen (Grundlage des Bestand-Gates)')
        bestand_gate = workflow.index('name: Bestand-Gate (aktuelle Publish-Gate-Regeln')
        text_battery = workflow.index('name: Textbatterie hinterher (Kanon-Ordnung nach KI-/SEO-Edits)')
        lastmod = workflow.index('name: lastmod für geänderte Artikel setzen (Frische-Signal)')
        final_build = workflow.index('name: Finalen Website-Stand für das SEO-Cockpit bauen')
        cockpit = workflow.index('name: SEO-Cockpit – final gerenderte Seiten, Snippets und Sitemap')
        self.assertLess(bestand_build, bestand_gate)
        self.assertLess(bestand_gate, text_battery)
        self.assertLess(text_battery, lastmod)
        self.assertLess(lastmod, final_build)
        self.assertLess(final_build, cockpit)
        audit_step = workflow[cockpit:]
        self.assertIn('id: seo_cockpit', audit_step)
        self.assertIn('scripts/seo_cockpit.py --build public --strict', audit_step)
        self.assertIn('$GITHUB_STEP_SUMMARY', audit_step)
        self.assertIn('SEO-Cockpit-Befundticket pflegen', workflow)
        self.assertIn('steps.seo_cockpit.outcome', workflow)
        self.assertIn('github.paginate(github.rest.issues.listForRepo', workflow)
        self.assertIn("openIssues.find(issue => issue.title === title", workflow)
        self.assertIn("state: 'closed'", workflow)


if __name__ == '__main__':
    unittest.main()
