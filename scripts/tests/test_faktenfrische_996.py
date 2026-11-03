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
            self.assertIn(fm['pin_description'], [pin['beschreibung'] for pin in matching])
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
        self.assertIn('72 bis 144 €', body)
        self.assertEqual(Decimal('18000') * Decimal('.115') + 195, Decimal('2265'))
        self.assertEqual(Decimal('2265') / 12, Decimal('188.75'))
        _, body = article(SLUGS[2])
        self.assertIn('2.265,00', body)
        self.assertIn('188,75', body)


if __name__ == '__main__':
    unittest.main()
