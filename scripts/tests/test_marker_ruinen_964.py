"""Regression: zerstückelte Pflicht-Kennzeichnungen (#964, 01.11.2026).

DER VORFALL
-----------
Der deterministische RS5-Heiler (`redaktions_standard._heal_rs5_block`)
suchte die ERSTE Satzgrenze eines Absatzes und setzte dort
„ im Modellfall“ / „ als Beispielwert“ ein – ohne zu prüfen, ob dieser
Punkt eine Satzgrenze IST. Bei „ca.“, „z. B.“, einer Ordnungszahl
(„3. **Tür“) oder einem Datum („30. November“) landete die Kennzeichnung
mitten im Wort, bei „… 460 €. Rechne“ im nächsten Satz. Ergebnis im
Bestand: hunderte zerstückelte Kennzeichnungen, live und in den
Faktenfrische-Befunden von #964 („ca im Modellfall. 500 €“,
„bis zum 30 als Beispielwert. November“).

WAS HIER GEPRÜFT WIRD
---------------------
1. Der Heiler setzt die Kennzeichnung nur an ein ECHTES Satzende.
2. Die Reparatur (`sprachkern.pflicht_marker_heilen`) stellt die
   zerschnittene Stelle wieder her und verliert keine Aussage.
3. `write_verified` verweigert jede Schrift, die eine NEUE Ruine einführt –
   und lässt bestehende Ruinen heilen (kein Einfrieren).
4. Der Bestand trägt keine R18-Ruine mehr (Dauerheilung, nicht Einzelfall).

Kein Ersatz für eine Fachprüfung: Rückfall-Schutz, kein Wahrheitsbeweis.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import redaktions_standard as rs  # noqa: E402
import sprachkern  # noqa: E402


class HeilerSatzgrenzeTests(unittest.TestCase):
    """Der Heiler darf eine Kennzeichnung nie mitten in einen Satz setzen."""

    def test_kennzeichnung_landet_hinter_dem_betrag(self):
        zeile = 'Der Tarif kostet 460 € im Jahr. Rechne den Bonus getrennt.'
        neu = rs._kennzeichnung_ans_satzende(zeile, 'als Beispielwert')
        self.assertEqual(
            neu,
            'Der Tarif kostet 460 € im Jahr; das ist ein Beispielwert. '
            'Rechne den Bonus getrennt.')
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [],
                         'Der Heiler hat eine neue Ruine erzeugt.')

    def test_abkuerzung_und_datum_sind_keine_satzgrenze(self):
        # „ca.“ darf nicht als Satzende gelten – sonst entsteht „ca als
        # Modellwert. 24 Monate“, genau der #964-Fund.
        neu = rs._kennzeichnung_ans_satzende(
            'Eine Garantie von ca. 24 Monaten kostet 480 €.', 'als Modellwert')
        self.assertNotIn('ca; ', neu)
        self.assertIn('480 €', neu)
        self.assertTrue(neu.endswith('das ist ein Modellwert.'), neu)
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [])

        neu = rs._kennzeichnung_ans_satzende(
            'Bis zum 30. November spart der Wechsel 150 € jährlich.',
            'im Modellfall')
        self.assertIn('30. November', neu,
                      'Der Heiler hat das Datum zerschnitten.')
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [])

    def test_ordnungszahl_bleibt_ganz(self):
        # Realfall #964: „… solltest du: 1 als Modellannahme. **Ca. 2 Monate“.
        neu = rs._kennzeichnung_ans_satzende(
            '1. Prüfe das Ende der Preisgarantie. Das ist wichtig.',
            'im Modellfall')
        self.assertTrue(neu.startswith('1. Prüfe'), neu)
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [])

    def test_absatz_ohne_punkt_bekommt_eigenen_satz(self):
        neu = rs._kennzeichnung_ans_satzende(
            'Der Abschlag liegt bei 89 € monatlich', 'im Modellfall')
        self.assertEqual(neu,
                         'Der Abschlag liegt bei 89 € monatlich. '
                         'Das ist ein Modellwert.')
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [])

    def test_heiler_ist_idempotent(self):
        zeile = 'Der Tarif kostet 460 €. Rechne nach.'
        einmal = rs._kennzeichnung_ans_satzende(zeile, 'als Beispielwert')
        zweimal = rs._kennzeichnung_ans_satzende(zeile, 'als Beispielwert')
        self.assertEqual(einmal, zweimal)


class RuinenDetektorTests(unittest.TestCase):
    """R18 erkennt die drei Zerstückelungs-Arten aus #964."""

    def test_abkuerzung_klebt_an_der_kennzeichnung(self):
        regeln = {r for r, _f, _p in sprachkern.pflicht_marker_funde(
            'Der Preis liegt bei ca als Modellannahme. 11 Cent.')}
        self.assertIn('R18-MARKER-ABKUERZUNG', regeln)

    def test_nackte_zahl_klebt_an_der_kennzeichnung(self):
        regeln = {r for r, _f, _p in sprachkern.pflicht_marker_funde(
            'Der Wechsel bis zum 30 als Beispielwert. November.')}
        self.assertIn('R18-MARKER-ZAHL', regeln)

    def test_satz_wird_zerschnitten(self):
        regeln = {r for r, _f, _p in sprachkern.pflicht_marker_funde(
            'Es fehlen 460 € im Modellfall. 500 € kommen dazu.')}
        self.assertIn('R18-MARKER-SATZ', regeln)

    def test_korrekte_kennzeichnungen_bleiben_frei(self):
        for satz in (
                'Der Betrag ist eine Modellannahme.',
                'Der Tarif kostet 460 € im Jahr; das ist ein Beispielwert.',
                'Nach 24 Monaten kostet der Tarif 480 €; das ist ein Modellwert.',
                'Ein Haus braucht oft rund 18.000 kWh im Jahr; das ist ein Modellwert.'):
            with self.subTest(satz=satz):
                self.assertEqual(sprachkern.pflicht_marker_funde(satz), [])

    def test_politur_ruine_funde_meldet_r18_mit(self):
        regeln = {r for r, _ in sprachkern.politur_ruine_funde(
            'Der Preis liegt bei ca als Modellannahme. 11 Cent.')}
        self.assertIn('R18-MARKER-ABKUERZUNG', regeln)


class ReparaturTests(unittest.TestCase):
    """Die Reparatur stellt den Satz wieder her, ohne die Aussage zu ändern."""

    def test_abkuerzung_wird_wiederhergestellt(self):
        neu, n = sprachkern.pflicht_marker_heilen(
            'Der Bereich liegt bei ca als Modellannahme. 11–13 Cent je kWh.')
        self.assertEqual(n, 1)
        self.assertIn('ca. 11–13 Cent je kWh', neu)
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [])

    def test_datum_wird_wiederhergestellt(self):
        neu, n = sprachkern.pflicht_marker_heilen(
            'Kündige bis zum 30 als Beispielwert. November, sonst verlierst '
            'du 150 €.')
        self.assertEqual(n, 1)
        self.assertIn('30. November', neu)
        self.assertEqual(sprachkern.pflicht_marker_funde(neu), [])

    def test_zahlen_bleiben_erhalten(self):
        vorher = 'Es fehlen 460 € im Rechenfall. Dazu kommen 250 €.'
        neu, _n = sprachkern.pflicht_marker_heilen(vorher)
        for zahl in ('460', '250'):
            self.assertIn(zahl, neu, 'Die Reparatur hat eine Zahl verschluckt.')

    def test_strukturzeilen_bleiben_unberuehrt(self):
        table = '| Kosten als Modellwert | 460 € |'
        neu, n = sprachkern.pflicht_marker_heilen(table)
        self.assertEqual((neu, n), (table, 0))

    def test_idempotent(self):
        einmal, _ = sprachkern.pflicht_marker_heilen(
            'Bis zum 30 als Beispielwert. November spart 150 €.')
        zweimal, n = sprachkern.pflicht_marker_heilen(einmal)
        self.assertEqual(einmal, zweimal)
        self.assertEqual(n, 0)


class SchreibVerifikationTests(unittest.TestCase):
    """write_verified: keine NEUE Ruine, bestehende Ruinen bleiben heilbar."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'index.md')
        # Unversiegelter Entwurf: `write_verified` verweigert sonst jede
        # Schrift (YMYL-Siegel, editorial_review_gate) – hier wird die
        # Ruinen-Prüfung gemessen, nicht der Siegelpfad.
        Path(self.path).write_text(
            '---\ntitle: Test\ndraft: true\n---\nText.\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_neue_ruine_wird_verweigert(self):
        a = {'content': 'Ein sauberer Satz ohne Zahlen.', 'path': self.path}
        ok, grund = sprachkern.write_verified(
            a, 'Ein sauberer Satz. Der Preis liegt bei ca als Modellannahme. 11 Cent.',
            'test')
        self.assertFalse(ok)
        self.assertIn('Politur-Ruine eingeführt', grund)

    def test_bestehende_ruine_darf_geheilt_werden(self):
        a = {'content': 'Der Preis liegt bei ca als Modellannahme. 11 Cent.',
             'path': self.path}
        ok, grund = sprachkern.write_verified(
            a, 'Der Preis liegt bei ca. 11 Cent je kWh; das ist ein Modellwert.',
            'test')
        self.assertTrue(ok, grund)


class BestandTests(unittest.TestCase):
    """Dauerheilung: der Bestand trägt keine zerstückelte Kennzeichnung mehr."""

    def test_kein_artikel_traegt_eine_r18_ruine(self):
        treffer = []
        for pfad in sorted((ROOT / 'content').rglob('index.md')):
            text = pfad.read_text(encoding='utf-8')
            for regel, fund, _pos in sprachkern.pflicht_marker_funde(text):
                treffer.append(f'{pfad.relative_to(ROOT)}: {regel} „{fund}“')
        self.assertEqual(treffer[:10], [],
                         'Zerstückelte Kennzeichnung im Bestand – '
                         f'python3 scripts/pflicht_marker_reparatur.py --apply '
                         f'({len(treffer)} Funde)')


if __name__ == '__main__':
    unittest.main()
