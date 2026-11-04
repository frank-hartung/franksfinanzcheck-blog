"""Rückfallschutz für die redaktionellen Gas-Befunde #996, kein Faktencheck."""
import re
import unittest
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
POSTS = ROOT / 'content' / 'posts'
SLUGS = (
    '2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas',
    '2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026',
    '2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden',
    '2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen',
)
PRICE = 'https://www.bundesnetzagentur.de/DE/Vportal/Energie/PreiseAbschlaege/start.html'
HEAT = 'https://www.verbraucherzentrale.de/wissen/energie/heizen-und-warmwasser/heizung-10-einfache-tipps-zum-heizkosten-sparen-13892'
SUPPLY = 'https://www.bundesnetzagentur.de/DE/Vportal/Energie/Vertragsarten/start.html'


def article(slug):
    raw = (POSTS / slug / 'index.md').read_text(encoding='utf-8')
    _, front, body = raw.split('---', 2)
    return yaml.safe_load(front), body


class GasBefunde996(unittest.TestCase):
    def test_unbelegte_aussagen_und_werbeversprechen_bleiben_entfernt(self):
        forbidden = (
            r'die besten tarife (?:findest|mit)',
            r'11[,.]93\s*(?:cent|ct)',
            r'(?:11\s*[–-]\s*13|11[,.]5\s+bis\s+13[,.]5|10[,.]5\s+bis\s+13[,.]5)\s*(?:cent|ct)',
            r'(?:bundesnetzagentur.{0,80}360\s*€|360\s*€.{0,80}bundesnetzagentur)',
            r'(?:gasrechnung|gaskosten).{0,80}10\s+bis\s+15\s*%',
            r'(?:beste zeit|besseren preise|spart dir hunderte euro)',
        )
        for slug in SLUGS:
            fm, body = article(slug)
            surface = ' '.join(str(fm.get(k, '')) for k in ('title', 'description', 'kurzantwort', 'pin_description')) + ' ' + body
            surface = re.sub(r'\s+', ' ', surface.lower())
            for pattern in forbidden:
                with self.subTest(slug=slug, pattern=pattern):
                    self.assertNotRegex(surface, pattern)

    def test_pinterest_plan_schreibt_keine_alten_versprechen_zurueck(self):
        """Der tägliche Pin-Sync liest den Plan, nicht nur das Frontmatter."""
        plan = yaml.safe_load((ROOT / 'data' / 'pinterest_plan.yaml').read_text(encoding='utf-8'))['pins']
        for slug in (SLUGS[2], SLUGS[3]):
            matching = [p for p in plan if f'/posts/{slug}/' in str(p.get('url', ''))]
            self.assertTrue(matching, slug)
            fm, _ = article(slug)
            # Redaktionell gesperrte Texte müssen nicht identisch zum Plan sein.
            self.assertIs(fm.get('pin_text_sync'), False)
            for pin in matching:
                self.assertNotRegex(pin['beschreibung'].lower(),
                                    r'beste zeit|preise (?:anzieht|hochtreibt)|hundert euro|5 minuten|über 1\.000|ganzen winter gespart')

    def test_regulierungsrahmen_am_text_verlinkt(self):
        for slug in (SLUGS[0], SLUGS[1], SLUGS[3]):
            _, body = article(slug)
            with self.subTest(slug=slug):
                self.assertIn(PRICE, body)
                for term in ('Haushaltskunden', 'Monat', 'Sonderkündigungsrecht',
                             'Grundversorgung', 'Umsatzsteuer', 'separiert'):
                    self.assertIn(term, body)
        _, body = article(SLUGS[2])
        self.assertIn(SUPPLY, body)
        self.assertIn('Grund- oder Ersatzversorgung', body)
        self.assertIn('Wechselverzögerung', body)

    def test_heizfaustwerte_und_modellgrenzen(self):
        for slug in (SLUGS[2], SLUGS[3]):
            fm, body = article(slug)
            self.assertIn(HEAT, body)
            self.assertIn(HEAT, [q['url'] for q in fm['quellen']])
            self.assertRegex(body, r'6\s*%')
        _, body = article(SLUGS[2])
        self.assertIn('Anlageneinstellung', body)
        self.assertIn('nicht pauschal deine gesamte Gasrechnung', body)
        self.assertIn('angenommenen 18.000 kWh', body)
        self.assertIn('fiktive beispielrechnung', body.lower())

    def test_beispielrechnungen(self):
        self.assertEqual(Decimal('18000') * Decimal('.004'), Decimal('72'))
        self.assertEqual(Decimal('18000') * Decimal('.008'), Decimal('144'))
        _, body = article(SLUGS[0])
        # NBSP vor € ist Hausstil (unit_guard U3) – typografisches
        # Leerzeichen darf die Behauptung nicht unsichtbar machen.
        self.assertIn('72 bis 144 €', body.replace('\xa0', ' '))
        self.assertEqual(Decimal('18000') * Decimal('.115') + 195, Decimal('2265'))
        self.assertEqual(Decimal('2265') / 12, Decimal('188.75'))
        _, body = article(SLUGS[2])
        self.assertIn('2.265,00', body)
        self.assertIn('188,75', body)


def norm(text):
    return re.sub(r'\s+', ' ', str(text).lower())


class Register996(unittest.TestCase):
    """Schließakte-Vertrag nach dem #911-Muster, Stand 03.11.2026."""

    @classmethod
    def setUpClass(cls):
        cls.register = yaml.safe_load(
            (ROOT / 'data' / 'faktenfrische_befunde_996.yaml')
            .read_text(encoding='utf-8'))
        import json
        queue = json.loads(
            (ROOT / 'data' / 'faktenfrische_queue.json').read_text(encoding='utf-8'))
        cls.queue = {(e['slug'], e['id']): e for e in queue['fachbefunde']
                     if e['slug'] in SLUGS}
        cfg = yaml.safe_load(
            (ROOT / 'data' / 'agent_reach' / 'faktenfrische.yaml')
            .read_text(encoding='utf-8'))
        cls.domains = {e['domain'] for e in cfg['quellen_allowlist']}

    def test_register_deckt_genau_die_16_ledger_befunde_ab(self):
        entries = self.register['befunde']
        self.assertEqual(len(entries), 16)
        self.assertEqual(len(self.queue), 16)
        self.assertEqual(
            {(e['artikel'], e['ledger_id']) for e in entries}, set(self.queue))
        for e in entries:
            with self.subTest(id=e['id']):
                self.assertEqual(e['status'], 'behoben')
                # Ehrlichkeitsvertrag: redaktionell behoben ist keine
                # menschliche Ledger-Signatur.
                self.assertEqual(e['ledger_signatur'], 'ausstehend')
                queue_entry = self.queue[(e['artikel'], e['ledger_id'])]
                self.assertEqual(e['ledger_fassung_sha256'],
                                 queue_entry['fassung_sha256'])
                self.assertTrue(e['anker'])
                self.assertTrue(e['rest_risiko'].strip())

    def test_belege_allowlist_und_artikelquellen(self):
        for e in self.register['befunde']:
            fm, _ = article(e['artikel'])
            quellen = [q['url'] for q in fm['quellen']]
            with self.subTest(id=e['id']):
                if e['beleg_url'] is None:
                    self.assertEqual(e['belegtyp'], 'streichung')
                else:
                    from urllib.parse import urlparse
                    domain = urlparse(e['beleg_url']).netloc.removeprefix('www.')
                    self.assertIn(domain, self.domains)
                    self.assertIn(e['beleg_url'], quellen)

    def test_anker_tragen_die_entscheidung_im_artikel(self):
        for e in self.register['befunde']:
            fm, body = article(e['artikel'])
            surface = norm(' '.join(str(fm.get(k, '')) for k in
                                    ('title', 'description', 'kurzantwort',
                                     'pin_title', 'pin_description'))
                           + ' ' + body)
            for anker in e['anker']:
                with self.subTest(id=e['id'], anker=anker[:40]):
                    self.assertIn(norm(anker), surface)
            for verboten in e['verboten_behauptend']:
                with self.subTest(id=e['id'], verboten=verboten[:40]):
                    self.assertNotIn(norm(verboten), surface)


class Werbeflaechen996(unittest.TestCase):
    """Pin-Texte sind Aussageflächen – dort lagen am 03.11.2026 die Rückfälle."""

    FORBIDDEN_PIN = (
        r'beste zeit',
        r'sparst bis zu \d+\s*euro',
        r'mehrere hundert euro ersparnis',
        r'preise (?:ziehen|anziehen|hochtreibt)',
        r'ziehen viele anbieter die preise an',
        r'preissprünge einfach aussitzen',
        r'gefeit',
    )

    def test_pins_neutral_und_gekennzeichnet(self):
        for slug in SLUGS:
            fm, _ = article(slug)
            pin = norm(f"{fm.get('pin_title', '')} {fm.get('pin_description', '')}")
            with self.subTest(slug=slug):
                self.assertIn('*werbung', pin)
                for pattern in self.FORBIDDEN_PIN:
                    self.assertNotRegex(pin, pattern)

    def test_bonus_kein_stark_versprechen_mehr(self):
        _, body = article(SLUGS[0])
        self.assertNotIn('drückt den Preis im ersten Jahr stark', body)
        self.assertIn('senkt die Rechnung im ersten Jahr nur, wenn Höhe '
                      'und Bedingungen erfüllt sind', body)


class Systemik996(unittest.TestCase):
    def test_systemprompt_prueft_die_996_befundklassen(self):
        prompt = (ROOT / 'scripts' / 'faktenfrische.py').read_text(encoding='utf-8')
        self.assertIn('aus #996', prompt)
        for begriff in ('Übersichtsseite', 'Saisonale Preisprognosen',
                        'Grund- und Ersatzversorgung', 'pin_title'):
            self.assertIn(begriff, prompt)
        self.assertIn('PIN-BESCHREIBUNG', prompt)

    def test_fassungs_hash_umfasst_die_werbeflaechen(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        import faktenfrische_befund_ledger as ledger
        basis = {'fm': 'title: "T"\npin_description: "neutral"\n',
                 'body': 'Text'}
        geaendert = {'fm': 'title: "T"\npin_description: "sparst bis zu 650 Euro"\n',
                     'body': 'Text'}
        self.assertNotEqual(ledger.pruef_hash(basis),
                            ledger.pruef_hash(geaendert))

    def test_metadaten_korridor(self):
        import datetime
        for slug in SLUGS:
            fm, _ = article(slug)
            with self.subTest(slug=slug):
                # Maschinenstempel bleibt der echte Lauf; Handänderung
                # läuft ehrlich über lastmod.
                self.assertEqual(str(fm['faktencheck']), '2026-11-01')
                self.assertGreaterEqual(str(fm['lastmod']), '2026-11-03')
                self.assertTrue(70 <= len(fm["description"]) <= 155,
                                fm['description'])
                self.assertFalse(fm['draft'])


class PinterestRueckfallschutz996(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        import pinterest_pin_text_sync
        cls.sync = pinterest_pin_text_sync

    def test_sync_selbsttest(self):
        self.assertEqual([], self.sync._selftest())

    def test_plan_und_redaktionelle_sperre(self):
        pins = self.sync.load_pins()
        self.assertTrue(pins)
        self.assertEqual([], self.sync.plan_rueckfaelle(pins))
        posts = {p['slug']: p for p in self.sync.load_posts()}
        for slug in SLUGS:
            with self.subTest(slug=slug):
                self.assertTrue(posts[slug]['sync_geschuetzt'])
                self.assertTrue(article(slug)[0]['pin_description'].startswith('*Werbung |'))

    def test_schlechte_planquelle_stoppt_vor_jeder_schreibaktion(self):
        from unittest.mock import patch
        with patch.object(self.sync, 'load_pins', return_value=[
                {'tag': 5, 'titel': 'Gas', 'beschreibung': 'Die BESTE\nZeit'}]), \
             patch.object(self.sync, 'load_posts') as laden:
            self.assertEqual(1, self.sync.main())
            laden.assert_not_called()

    def test_geschuetzte_felder_bleiben_bei_sync_und_duplikat_unveraendert(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = '---\ntitle: Gas\npin_description: "*Werbung | redaktionell geprüft"\npin_text_sync: false\n---\nText'
            paths = [root / 'geschuetzt.md', root / 'zweiter.md']
            for path in paths:
                path.write_text(original, encoding='utf-8')
            base = {'content': original, 'title': 'Gas', 'description': 'Ein sachlicher langer Text über Gastarife',
                    'tags': [], 'keywords': [], 'pin_title': '', 'pinwand': '', 'pillar': '',
                    'affiliate': False, 'draft': False, 'pin_description': '*Werbung | redaktionell geprüft'}
            posts = [dict(base, slug='geschuetzt', path=str(paths[0]), sync_geschuetzt=True),
                     dict(base, slug='zweiter', path=str(paths[1]), sync_geschuetzt=False)]
            pins = [{'tag': 1, 'titel': 'Gas vergleichen', 'beschreibung':
                     '*Werbung | Ein ausreichend langer Text zum Vergleich von Gastarifen.', 'pinwand': 'Gas'}]
            with patch.object(self.sync, '_selftest', return_value=[]), \
                 patch.object(self.sync, 'load_pins', return_value=pins), \
                 patch.object(self.sync, 'load_posts', return_value=posts), \
                 patch.object(self.sync, 'load_board_pillar_map', return_value={}), \
                 patch.object(self.sync, 'match_score', side_effect=lambda post, *_: 2 if post['slug'] == 'geschuetzt' else 0), \
                 patch.object(self.sync, 'score', return_value=1.5), \
                 patch.object(self.sync, 'DO_APPLY', True), \
                 patch.object(self.sync, 'REPORT', str(root / 'report.md')), \
                 patch('audit_log.log_event'):
                self.assertEqual(0, self.sync.main())
            self.assertEqual(original, paths[0].read_text(encoding='utf-8'))
            self.assertNotEqual(original, paths[1].read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
