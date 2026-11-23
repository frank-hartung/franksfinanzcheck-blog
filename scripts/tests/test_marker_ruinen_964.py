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
import re
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


class RechtsnormStattModellwertTests(unittest.TestCase):
    """Wurzel zum Modellwert-Artefakt (BEFUND 22.11.2026).

    Live stand der Satz: „Die DSGVO (Verordnung (EU) 2016/679) regelt die
    Verarbeitung personenbezogener Daten; das ist ein Modellwert.“ Eine
    Rechtsnorm ist kein Modellwert, sie ist geltendes Recht – der Stempel war
    faktisch falsch, in einem YMYL-Satz über die DSGVO.

    Ursache war `_ZAHLBEHAUPTUNG`: Der Ausdruck verknüpfte zwei sehr
    unterschiedliche Fälle mit ODER – Zahl MIT Einheit (immer eine Behauptung)
    und NACKTE Zahl ab drei Ziffern (nur manchmal eine). Der nackte Zweig fraß
    die `2016` der Fundstellenangabe, `_marker_reparatur` sah „der Satz trägt
    eine Zahl“ und hängte den Teilsatz an.

    #1318 hat den Satz von Hand korrigiert. Die Ursache blieb im Baum, mit
    gemessenen 44 Zeilen Exposition im Bestand (1 Fundstelle, 40
    Paragraphenverweise, 3 Link-Pfade mit Datum); der Bestand war nur deshalb
    sauber, weil diese Marker gerade nicht zerstückelt waren. Hier steht die
    Sicherung der Wurzelheilung – in BEIDE Richtungen, denn ein zu grober Guard
    wäre eine Scheinheilung in die Gegenrichtung: Er nähme echten
    Modellrechnungen ihre Kennzeichnungspflicht und verstieße damit still
    gegen genau das, was #964 durchgesetzt hat.
    """

    def test_selbsttest_laeuft_durch(self):
        self.assertEqual(sprachkern.selbsttest(), 0)

    def test_rechtsnorm_ist_keine_zahlenbehauptung(self):
        for satz in [
            'Die DSGVO (Verordnung (EU) 2016/679) regelt die Verarbeitung '
            'personenbezogener Daten',
            'Nach § 5 Abs. 2 UWG ist diese Werbung unzulässig',
            'Art. 6 DSGVO erlaubt die Verarbeitung nur mit Rechtsgrundlage',
            'Siehe Ziff. 12 des Vertrags',
            'Vergleiche S. 240 des Berichts',
            'Das Aktenzeichen lautet 2016/679',
        ]:
            self.assertFalse(sprachkern._zaahlbehauptung(satz),
                             f'Rechtsverweis als Zahlenbehauptung gelesen: {satz}')

    def test_linkziel_ist_keine_zahlenbehauptung(self):
        satz = ('Die Zahlen stehen in der [Pressemeldung]'
                '(https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/10)')
        self.assertFalse(sprachkern._zaahlbehauptung(satz),
                         'Datumpfad eines Link-Ziels als Zahlenbehauptung gelesen')

    def test_echte_modellrechnung_bleibt_kennzeichnungspflichtig(self):
        """Gegenrichtung – der Guard darf nichts wegnehmen, was Pflicht ist."""
        for satz in [
            'Ein Haus braucht 18.000 kWh im Jahr',
            'Nach 24 Monaten kostet der Tarif 460 €',
            'Der Preis liegt bei ca. 11 Cent je kWh',
            'Die Ersparnis beträgt 12 Prozent',
            'Rund 1500 Nutzer haben teilgenommen',
            'Der Tarif bietet 500 GB Datenvolumen',
        ]:
            self.assertTrue(sprachkern._zaahlbehauptung(satz),
                            f'echte Zahlenbehauptung wegmaskiert: {satz}')

    def test_mischfall_behaelt_die_behauptung(self):
        """Ein Satz darf einen Paragraphen zitieren UND eine Zahl behaupten.

        Deshalb prüft der Guard den Kontext um den EINZELNEN Treffer, nicht den
        ganzen Satz. Ein satzweiser Guard würde hier die Kennzeichnung
        verlieren.
        """
        for satz in ['Nach § 5 kostet das 460 € im Monat',
                     'Gemäß Art. 15 DSGVO fallen dafür 25 Euro an']:
            self.assertTrue(sprachkern._zaahlbehauptung(satz),
                            f'Kennzeichnungspflicht im Mischfall verloren: {satz}')

    def test_heilung_setzt_den_stempel_nicht_an_eine_rechtsnorm(self):
        roh = ('Die DSGVO (Verordnung (EU) 2016/679) regelt die Verarbeitung '
               'personenbezogener Daten als Modellwert. Du kannst Auskunft '
               'verlangen.')
        neu, eingriffe = sprachkern.pflicht_marker_heilen(roh)
        self.assertNotIn('das ist ein Modellwert', neu,
                         f'Modellwert-Stempel an einer Rechtsnorm: {neu}')
        self.assertIn('Du kannst Auskunft verlangen', neu,
                      'Aussage nach dem Marker verloren')
        self.assertGreaterEqual(eingriffe, 1)
        # Die Heilung muss idempotent sein – sonst heilt jeder Lauf weiter.
        nochmal, n2 = sprachkern.pflicht_marker_heilen(neu)
        self.assertEqual((nochmal, n2), (neu, 0))

    def test_heilung_behaelt_den_stempel_an_einer_modellrechnung(self):
        roh = 'Ein Haus braucht 18.000 kWh im Jahr als Modellwert. Rechne selbst nach.'
        neu, _eingriffe = sprachkern.pflicht_marker_heilen(roh)
        self.assertIn('das ist ein Modellwert', neu,
                      f'Kennzeichnungspflicht verloren: {neu}')

    def test_bestand_traegt_keinen_stempel_an_einer_rechtsnorm(self):
        """Der Bestand: kein Modellwert-Stempel an einem Rechtsnorm-Satz.

        Das ist die Prüfung, die am 22.11.2026 gefehlt hat. #1318 heilte den
        einen Satz, den ein anderer Test zufällig sah; diese Probe sieht die
        Klasse.
        """
        norm = re.compile(r'\b(?:DSGVO|BGB|UWG|StVO|GG|EStG|HGB|SGB|AO|ZPO|'
                          r'OWiG|VVG|Verordnung|Richtlinie|Gesetz)\b|§\s*\d|'
                          r'Art\.\s*\d', re.I)
        treffer = []
        for pfad in sorted((ROOT / 'content').rglob('index.md')):
            text = pfad.read_text(encoding='utf-8')
            for satz in re.split(r'(?<=[.!?])\s+', text):
                if 'das ist ein Modellwert.' in satz and norm.search(satz):
                    treffer.append(f'{pfad.relative_to(ROOT)}: {satz.strip()[:90]}')
        self.assertEqual(treffer[:5], [],
                         'Modellwert-Stempel an einem Rechtsnorm-Satz – '
                         'eine Rechtsnorm ist geltendes Recht, kein Modellwert')


if __name__ == '__main__':
    unittest.main()
