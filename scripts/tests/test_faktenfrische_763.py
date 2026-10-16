"""Offline-Regression für die redaktionelle Korrektur von Issue #763.

Kein Ersatz für eine Fachprüfung: schützt vor Rückkehr der konkreten
Fehler, falscher Quellenattribution und stiller Rechen-/Metadaten-Drift.
Die vorhandene Publication-reliability-CI entdeckt dieses Modul automatisch.
"""
import datetime as dt
from decimal import Decimal
from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import faktenfrische

HEIZ = '2026-10-14-heizperiode-vorbereiten-im-spaetsommer'
REISE = '2026-10-14-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen'


def article(slug):
    text = (ROOT / 'content/posts' / slug / 'index.md').read_text()
    _, fm, body = text.split('---', 2)
    return yaml.safe_load(fm), body


class Faktenfrische763Tests(unittest.TestCase):
    def test_metadaten_und_geo(self):
        for slug in (HEIZ, REISE):
            with self.subTest(slug=slug):
                fm, body = article(slug)
                self.assertEqual(fm['lastmod'], dt.date(2026, 10, 15))
                self.assertGreaterEqual(fm['faktencheck'], dt.date(2026, 10, 15))
                self.assertIn('15. Oktober 2026', body)
                self.assertTrue(fm['kurzantwort'])
                self.assertTrue(fm['quellen'])
                geo = faktenfrische.geo_reife(dict(
                    body=body, kurzantwort=fm['kurzantwort'],
                    quellen_vorhanden=bool(fm['quellen']), faktencheck=fm['faktencheck']))
                self.assertEqual(geo['prozent'], 100)

    def test_keine_erfundenen_quellendaten_oder_portalempfehlungen(self):
        for slug in (HEIZ, REISE):
            fm, body = article(slug)
            self.assertNotIn('datum', fm['quellen'][0])
            self.assertIn('kein fachlicher Beleg', body)
            self.assertIn('Werbung', body)
            self.assertIn('Modellrechnung', body)
            self.assertIn('Annahmen', body)

    def test_heizung_keine_pauschalen_spar_und_sicherheitsversprechen(self):
        _, body = article(HEIZ)
        for old in ('sparst du etwa 5 Prozent', 'Router braucht oft 5 Watt',
                    'CHECK24 zeigt dir schnell alle Preise', '13.140 Wh',
                    'Stelle die Wärme am Kessel auf 60 °C', 'Spart bis zu 10 %'):
            self.assertNotIn(old, body)
        # Jede Schutz-Aussage bleibt Pflicht; gleichwertige Formulierungen
        # im aktuellen Artikeltext sind ausdrücklich zugelassen, damit der
        # Test den fachlichen Vertrag statt einzelner Wörter prüft.
        safeguards = {
            'keine pauschale Idealtemperatur': (
                'kein allgemeines Optimum',
                'kein festes Gesetz für alle Menschen',
            ),
            'keine garantierte Sparquote': (
                'keine konkrete Prozentangabe',
                'keine festen Prozente',
                'keine sichere Ersparnis',
            ),
            'hygienisches Risiko': ('Legionellen',),
            'Brenner-/Gasarbeiten nur durch Fachleute': (
                'Keine Arbeiten am Brenner',
                'Fass den Brenner oder die Rohre für Gas nie selbst an',
                'Der Brenner und die Filter sind keine Dinge für Laien',
            ),
            'Werbelink ist kein Fachbeleg': (
                'kein Beleg',
                'kein fachlicher Beleg',
            ),
        }
        for contract, variants in safeguards.items():
            with self.subTest(contract=contract):
                self.assertTrue(any(variant in body for variant in variants),
                                f'Keine zulässige Formulierung für: {contract}')

    def test_heizung_rechnungen_mit_korrekten_einheiten(self):
        _, body = article(HEIZ)
        kwh = Decimal(3 * 5 * 24 * 365) / 1000
        self.assertEqual(kwh, Decimal('131.4'))
        self.assertEqual(kwh * Decimal('0.30'), Decimal('39.420'))
        self.assertIn('131,4 kWh', body)
        # Der Fließtext schreibt die Währung aus (statt des Symbols); beide
        # gebräuchlichen Darstellungen müssen mit einem echten Betragseintrag
        # übereinstimmen, nicht nur als Zahl irgendwo im Artikel vorkommen.
        for amount in ('39,42', '13,14', '105', '120'):
            with self.subTest(amount=amount):
                self.assertRegex(body, rf'(?<![0-9]){amount}(?: *€| +Euro)(?![A-Za-z])')
        self.assertTrue(any(phrase in body for phrase in
                            ('gleichem Grundpreis', 'Grundpreis gleich bleibt')))

    def test_reise_keine_unbelegten_markt_und_cashback_annahmen(self):
        fm, body = article(REISE)
        for old in ('Preise für Unterkünfte und Flüge stabilisiert',
                    'Viele Banken bieten mittlerweile integrierte Cashback',
                    'Cashback-Rate von 2 Prozent', 'Transparenz digitaler Verträge',
                    'oft bessere Konditionen als direkt beim Vermieter', '620 Euro'):
            self.assertNotIn(old, body)
        self.assertNotIn('Cashback-Tipps', fm['description'])
        for caveat in ('frei gewählte Annahmen', 'keine Bank-Cashback-Rate',
                       'keine Empfehlung unseres Werbepartners',
                       'ohne Cashback', 'Datenschutzhinweise'):
            self.assertIn(caveat, body)

    def test_reise_budget_ohne_ungewissen_bonus(self):
        _, body = article(REISE)
        self.assertEqual((1800 - 600) / 10, 120)
        self.assertEqual(120 + 12 * 25 + 80, 500)
        self.assertIn('120 € pro Monat', body)
        self.assertIn('120 € + 12 × 25 € + 80 €', body)
        self.assertIn('500 €', body)
        self.assertIn('nur 150 € statt 300 €', body)

    def test_fachpruefung_unterscheidet_belegluecke_modell_und_werbung(self):
        prompt = faktenfrische.SYSTEM_PROMPT
        for rule in ('Modellannahmen sind keine Marktdaten',
                     'Fehlende Erwähnung ist kein Gegenbeweis',
                     'keine behördliche Empfehlung', 'Quellen-Publikationsdatum'):
            self.assertIn(rule, prompt)


if __name__ == '__main__':
    unittest.main()
