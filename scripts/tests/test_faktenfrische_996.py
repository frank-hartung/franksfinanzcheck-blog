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
        self.assertIn('72 bis 144 €', body)
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


if __name__ == '__main__':
    unittest.main()
