"""Offline-Regression für die redaktionelle Korrektur von Issue #823.

Stand 24.10.2026. Geprüft werden BEDEUTUNGS-Invarianten, keine starren
Formulierungen (Lehre aus #763: Ein Test, den jede harmlose Umformung bricht,
schützt nichts). Nummerierung wie im Issue:

  B1 saison · veraltet   – „Neukundenpreise stark nach unten“ vs. destatis +14,9 %
  B2 saison · luecke     – 420-€-Stromersparnis ohne Beleg/Kennzeichnung
  B3 saison · luecke     – 9,90-€-Kontogebühr / >1.300-€-Ersparnis ohne Beleg
  B4 saison · luecke     – „nach 24 Monaten massiv teurer“ ohne Quelle
  B5 dns    · luecke     – Regulierungsrahmen Bundesnetzagentur fehlte
  B6 dns    · praezision – „spürbar schneller“ ohne Mechanismus/Hardware-Grenzen
  B7 dns    · praezision – „Cloudflare oft die beste Wahl“ ohne Messdaten

Dauerhaftigkeit heißt hier dreierlei:
  1. Die sieben Fehlbehauptungen dürfen (behauptend) nie zurückkehren;
     Dämpfungen, Verneinungen und Leserfragen bleiben erlaubt.
  2. Modellrechnungen müssen gekennzeichnet bleiben UND ihre Arithmetik
     muss aus den Zellen selbst nachgerechnet werden (Zahlendreher fallen
     auf, unabhängig von der Schreibweise „€“/„Euro“/NBSP).
  3. Gate-Parität: Lesbarkeit (Score ≥ 75, Flesch ≥ 60), Zeichenkorridor,
     harte Textverständnis-Regeln, interne Links ≥ 2, GEO-Reife 6/6 –
     sonst verrottet der Entwurf im Hold und die Heilung wirkt nur scheinbar.

Kein Ersatz für eine Fachprüfung: Rückfall-Schutz, kein Wahrheitsbeweis.
"""
import datetime as dt
import json
from decimal import Decimal
from pathlib import Path
import re
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import faktenfrische  # noqa: E402

SAISON = '2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert'
DNS = '2026-10-16-dns-server-aendern-fuer-schnelleres-internet'
KORRIGIERT_AM = dt.date(2026, 10, 24)
LAUF_FAKTENCHECK = dt.date(2026, 10, 20)   # echter Recherchelauf vom 20.10.
DASHES = {
    '\u2013': '-', '\u2014': '-', '\u2012': '-', '\u2011': '-',
    '\u00a0': ' ', '\u202f': ' ', '\u2212': '-', '‑': '-',
}


def resolve(slug):
    """Slug über Lebenszyklus-Umbenennungen hinweg auflösen.

    Lehre vom 24.10.2026 (#763-Modul): Die Kadenz datiert Entwürfe zur
    Veröffentlichung um (`2026-10-14-…` → `2026-10-24-…`). Ein Test, der am
    Datumspräfix klebt, bricht bei jeder harmlosen Umbenennung. Exakter
    Treffer gewinnt, sonst eindeutiger Fund über den Namens-Kern.
    """
    posts = ROOT / 'content' / 'posts'
    exact = posts / slug
    if (exact / 'index.md').is_file():
        return exact
    kern = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)
    treffer = sorted(p for p in posts.glob(f'*-{kern}') if (p / 'index.md').is_file())
    if len(treffer) == 1:
        return treffer[0]
    raise FileNotFoundError(
        f'{slug}: weder exakt noch eindeutig als *-{kern} in content/posts '
        f'(Treffer: {[p.name for p in treffer]})')


def read(slug):
    text = (resolve(slug) / 'index.md').read_text(encoding='utf-8')
    _, fm, body = text.split('---', 2)
    return yaml.safe_load(fm), body


def raw_of(slug):
    return (resolve(slug) / 'index.md').read_text(encoding='utf-8')


def norm(text):
    """Kleinschreibung, Euro-Zeichen, Striche und Leerläufe glätten."""
    for a, b in DASHES.items():
        text = text.replace(a, b)
    text = text.replace('€', ' euro')
    return re.sub(r'\s+', ' ', text.lower()).strip()


def chunks(body):
    """Absatz-weise, inklusive Tabellen-/Zitat-Blöcken als eigene Chunks."""
    return [norm(p) for p in re.split(r'\n\s*\n', body) if p.strip()]


def sentences(text):
    """Fließtext-Sätze; Überschriften-/Tabellen-/Listen-/Zitatzeilen raus."""
    flow = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] in '#|*>-' and not re.match(r'^-\d', s):
            continue
        if re.match(r'^[-+\d].{0,3}[.)]\s', s):
            continue
        flow.append(s)
    return [s for s in re.split(r'(?<=[.!?])\s+', norm(' '.join(flow))) if s]


def zahl(text):
    """Letzte Zahl einer Zelle, deutsche Schreibweise, als Decimal."""
    m = re.findall(r'\d{1,3}(?:\.\d{3})+,\d+|\d{1,3}(?:\.\d{3})+|\d+,\d+|\d+', text)
    assert m, f'keine Zahl in Zelle: {text!r}'
    return Decimal(m[-1].replace('.', '').replace(',', '.'))


def _ziffer(token):
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', token):       # 3.500 / 1.470
        return Decimal(token.replace('.', ''))
    return Decimal(token.replace('.', '').replace(',', '.'))  # 0,42 / 118,80 / 15


def rechne(zelle):
    """Deutsche Rechenzelle auswerten: „3.500 × 0,42“, „1.470 − 1.050“."""
    wert, op = None, None
    z = zelle.lower()
    for a, b in DASHES.items():
        z = z.replace(a, b)
    for token in re.findall(r'\d[\d.,]*|[x×*+\-/]|mal|durch', z):
        if token in ('mal', 'x', '×', '*'):
            op = '*'; continue
        if token in ('durch', '/'):
            op = '/'; continue
        if token == '+':
            op = '+'; continue
        if token == '-':
            op = '-'; continue
        z2 = _ziffer(token)
        if wert is None:
            wert = z2
        elif op == '*':
            wert *= z2
        elif op == '/':
            wert /= z2
        elif op == '+':
            wert += z2
        elif op == '-':
            wert -= z2
        else:
            raise AssertionError(f'Zelle ohne Operator: {zelle!r}')
    return wert


def modell_zeilen(body):
    """3-Spalten-Modellrechnungs-Zeilen → {label: (rechnung, ergebnis)}."""
    z = body
    for a, b in DASHES.items():
        z = z.replace(a, b)
    zeilen = re.findall(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$', z, re.M)
    return {norm(a): (b, c) for a, b, c in zeilen
            if norm(a) not in ('schritt der rechnung',) and ':-' not in b}


class Faktenfrische823Tests(unittest.TestCase):
    """Die sieben Befunde aus dem Report vom 20.10.2026 – je einer pro Art."""

    # --- B1: „Neukundenpreise stark nach unten“ (veraltet) -----------------
    def test_b1_kein_preisrutsch_behauptet_destatis_zahl_steht(self):
        _, body = read(SAISON)
        for sent in sentences(body):
            trend = re.search(r'(nach unten|gesunken|gefallen|billiger geworden'
                              r'|günstiger geworden|preisrutsch|stark gefallen)', sent)
            bezug = re.search(r'(neukunde|preise|tarife|strompreise)', sent)
            if trend and bezug:
                self.assertTrue(re.search(r'(nicht|kein|lässt sich .{0,30} nicht)', sent),
                                f'Unbelegter Preis-Trend behauptend zurück: {sent!r}')
        joined = norm(body)
        # Die amtliche Einordnung muss als Gegenanker stehen (destatis, Q1).
        self.assertIn('14,9 %', body, 'destatis-Zahl 14,9 % fehlt (Befund 1).')
        para = [c for c in chunks(body) if '14,9' in c]
        self.assertTrue(para and any('statistische' in p and 'bundesamt' in p for p in para),
                        'Die 14,9 % müssen dem Statistischen Bundesamt zugeordnet sein.')
        self.assertTrue(re.search(r'energie[^.]{0,80}14,9|14,9[^.]{0,80}(energie|gestiegen)',
                                  joined), '14,9 % müssen als Energiepreis-Anstieg stehen.')

    # --- B2: 420-€-Stromersparnis ohne Beleg (luecke) ----------------------
    def test_b2_strom_ersparnis_nur_als_gekennzeichnetes_modell(self):
        _, body = read(SAISON)
        cks = chunks(body)
        # Die Kennzeichnung muss als PROSA vor der Tabelle stehen – ein
        # „im Modell“ in der Zeilenbeschriftung allein ist keine Kennzeichnung
        # (Sabotage-Lehre S3, 24.10.).
        for i, c in enumerate(cks):
            if c.startswith('|') and re.search(r'(420|9,90|1\.338)', c):
                vor = cks[i - 1] if i else ''
                self.assertTrue(re.search(r'frei gewählt', vor),
                                f'Modelltabelle ohne „frei gewählt“-Kennzeichnung davor: {c[:120]}')
        joined = norm(body)
        self.assertIn('keine marktdaten', joined,
                      'Die Abgrenzung „keine Marktdaten“ fehlt bei den Modellrechnungen.')
        for i, c in enumerate(cks):
            if '420' in c:
                kontext = ' '.join(cks[max(0, i - 1):i + 1])
                self.assertTrue(re.search(r'(frei gewählt|modell|annahme)', kontext),
                                f'420-Euro-Wert ohne Modell-Kennzeichnung: {c[:140]}')
        zeilen = modell_zeilen(body)
        alt = zeilen.get('kosten im alten tarif bei 0,42 euro je kwh')
        neu = zeilen.get('kosten im neuen tarif bei 0,30 euro je kwh')
        ersp = zeilen.get('mögliche ersparnis im modell')
        verbrauch = zeilen.get('verbrauch im jahr (annahme)')
        for name, z in (('Verbrauch', verbrauch), ('Alt', alt), ('Neu', neu),
                        ('Ersparnis', ersp)):
            self.assertIsNotNone(z, f'Modellrechnungs-Zeile „{name}“ fehlt')
        self.assertEqual(zahl(verbrauch[1]), Decimal(3500))
        self.assertEqual(rechne(alt[0]), zahl(alt[1]))          # 3.500 × 0,42 = 1.470
        self.assertEqual(rechne(neu[0]), zahl(neu[1]))          # 3.500 × 0,30 = 1.050
        self.assertEqual(rechne(ersp[0]), zahl(ersp[1]))        # 1.470 − 1.050 = 420
        self.assertEqual(zahl(alt[1]) - zahl(neu[1]), zahl(ersp[1]))
        # Cent-Faustregel: 3.500 kWh × 0,01 € = 35 € – schreibweisenunabhängig.
        m = re.search(r'ein cent[^.]*?(\d[\d.]*) kilowattstunden[^.]*?(\d+) ?(?:€|euro)',
                      norm(body))
        self.assertIsNotNone(m, 'Cent-Faustregel fehlt (Ersatz-Anker für Befund 2).')
        self.assertEqual(_ziffer(m.group(1)) * Decimal('0.01'), Decimal(m.group(2)))

    # --- B3: 9,90-€-Gebühr / >1.300-€-Ersparnis ohne Beleg (luecke) --------
    def test_b3_konto_ersparnis_nur_als_gekennzeichnetes_modell(self):
        _, body = read(SAISON)
        cks = chunks(body)
        for i, c in enumerate(cks):
            if re.search(r'(9,90|1\.338|1\.300)', c):
                kontext = ' '.join(cks[max(0, i - 1):i + 1])
                self.assertTrue(re.search(r'(frei gewählt|modell|annahme)', kontext),
                                f'Konto-Gebühr/Ersparnis ohne Modell-Kennzeichnung: {c[:140]}')
        # Kennzeichnung als Prosa vor der Konto-Tabelle (Sabotage-Lehre S3).
        for i, c in enumerate(cks):
            if c.startswith('|') and re.search(r'(9,90|1\.338)', c):
                vor = cks[i - 1] if i else ''
                self.assertTrue(re.search(r'frei gewählt', vor),
                                f'Konto-Modelltabelle ohne „frei gewählt“ davor: {c[:120]}')
        zeilen = modell_zeilen(body)
        grund = zeilen.get('grundgebühr im jahr bei 9,90 euro im monat')
        karte = zeilen.get('kreditkarte im jahr (annahme)')
        fix = zeilen.get('fixkosten im jahr zusammen')
        zehn = zeilen.get('über zehn jahre gerechnet')
        for name, z in (('Grundgebühr', grund), ('Karte', karte), ('Fixkosten', fix),
                        ('Zehn Jahre', zehn)):
            self.assertIsNotNone(z, f'Konto-Modellzeile „{name}“ fehlt')
        self.assertEqual(rechne(grund[0]), zahl(grund[1]))      # 9,90 × 12 = 118,80
        self.assertEqual(zahl(karte[1]), Decimal(15))
        self.assertEqual(zahl(grund[1]) + zahl(karte[1]), zahl(fix[1]))
        self.assertEqual(rechne(fix[0]), zahl(fix[1]))          # 118,80 + 15 = 133,80
        self.assertEqual(rechne(zehn[0]), zahl(zehn[1]))        # 133,80 × 10 = 1.338
        # Echte Gebühren gehören ins Preisverzeichnis der Bank verweisen.
        self.assertIn('preisverzeichnis', norm(body),
                      'Der Verweis auf das Preisverzeichnis der Bank fehlt (Befund 3).')

    # --- B4: „nach 24 Monaten massiv teurer“ ohne Quelle (luecke) ----------
    def test_b4_keine_pauschale_preissprung_behauptung(self):
        _, body = read(SAISON)
        joined = norm(body)
        self.assertNotIn('massiv steigen', joined,
                         'Die unbelegte Pauschale „kann der Preis massiv steigen“ ist zurück.')
        for sent in sentences(body):
            if re.search(r'(24 monate|mindestlaufzeit|erste laufzeit|aktionsphase)', sent) \
               and re.search(r'(teurer|steigt|steigen|erhöht|preis.{0,20}hoch)', sent):
                self.assertTrue(re.search(r'(kann|manche|andere|nicht|vertrag|bedingungen'
                                          r'|prüf|steht in)', sent),
                                f'Laufzeit-Preissprung als Pauschale: {sent!r}')
        # Heilung: Vertragsmechanik statt Marktbehauptung.
        self.assertTrue(re.search(r'(vertragsbedingungen|dein vertrag|deinen vertrag'
                                  r'|vertragsunterlagen)', joined),
                        'Der Verweis auf die Vertragsbedingungen fehlt (Befund 4).')

    # --- B5: Bundesnetzagentur-Rahmen fehlte (luecke) -----------------------
    def test_b5_regulierungsrahmen_bundesnetzagentur_genannt(self):
        _, body = read(DNS)
        joined = norm(body)
        self.assertIn('bundesnetzagentur', joined,
                      'Die Bundesnetzagentur muss als Aufsicht vorkommen (Befund 5).')
        # Die Aufsicht muss in einem echten Fließtext-Satz stehen – eine
        # Überschrift allein trägt die Einordnung nicht (Sabotage-Lehre S6).
        aufsichts_satz = [s for s in sentences(body)
                          if 'bundesnetzagentur' in s
                          and re.search(r'(aufsicht|überwacht|pflichten|zuständig)', s)]
        self.assertTrue(aufsichts_satz,
                        'Kein Fließtext-Satz verknüpft Bundesnetzagentur mit Aufsicht/Pflichten.')
        # Eine Leugnung der Aufsicht darf nie behauptend stehen.
        for sent in sentences(body):
            if re.search(r'(frei von aufsicht|ohne aufsicht|keine aufsicht'
                         r'|nicht reguliert|ohne regulierung|frei von regulierung)', sent):
                self.fail(f'Aufsichts-Leugnung behauptet (Befund 5 kehrt um): {sent!r}')
        self.assertTrue(re.search(r'(unternehmenspflichten|pflichten[^.]{0,80}unternehmen'
                                  r'|unternehmen[^.]{0,80}pflichten)', joined),
                        'Die Unternehmenspflichten als Beispiel fehlen (Befund 5).')
        # Präzision: Privatnutzer brauchen keine Erlaubnis – und das muss so stehen.
        for sent in sentences(body):
            if 'erlaubnis' in sent:
                self.assertTrue(re.search(r'(nicht|kein)', sent),
                                f'Erlaubnis-Pflicht für Privatnutzer behauptet: {sent!r}')
        self.assertTrue(re.search(r'(privatnutzer|privatsache)[^.]{0,120}frei'
                                  r'|frei wählen', joined),
                        'Die freie DNS-Wahl für Privatnutzer muss genannt sein.')

    # --- B6: „spürbar schneller“ ohne Mechanismus/Grenzen (praezision) ------
    def test_b6_dns_versprechen_mit_mechanismus_und_hardware_grenzen(self):
        _, body = read(DNS)
        joined = norm(body)
        for sent in sentences(body):
            if 'schneller' in sent and re.search(r'(dns|server|wechsel)', sent):
                self.assertTrue(re.search(r'(kann|oft|nicht|auflösung|fühlt|wirken'
                                          r'|mess|leitung|bandbreite)', sent),
                                f'Unbedingtes Schneller-Versprechen: {sent!r}')
        # Mechanismus-Trennung: Namensauflösung ≠ Bandbreite/Leitung.
        self.assertIn('namensauflösung', joined,
                      'Der betroffene Mechanismus (Namensauflösung) muss genannt sein.')
        self.assertTrue(re.search(r'(leitung|bandbreite|tarif)[^.]{0,120}(nicht'
                                  r'|bleibt|obergrenze|grenze)', joined),
                        'Die Leitungs-/Bandbreiten-Grenze muss benannt sein (Befund 6).')
        # Hardware-Grenze inkl. Beleganker heise (Q2).
        self.assertTrue(re.search(r'(hardware|router[^.]{0,60}wlan|wlan[^.]{0,60}router)',
                                  joined), 'Hardware-Grenzen fehlen (Befund 6).')
        self.assertIn('heise', joined,
                      'Der heise-Beleganker zur Hardware-Grenze fehlt (Befund 6, Q2).')
        # „kein Turbo“-Einordnung: DNS darf nicht als Allheilmittel stehen.
        self.assertTrue(re.search(r'(kein turbo|nicht.{0,40}(turbo|allheilmittel)'
                                  r'|kleine stellschraube|feinjustierung)', joined),
                        'Die Einordnung „DNS ist nur Feinjustierung“ fehlt.')

    # --- B7: „Cloudflare oft die beste Wahl“ ohne Daten (praezision) --------
    def test_b7_kein_anbieter_ranking_ohne_messung(self):
        _, body = read(DNS)
        joined = norm(body)
        self.assertNotIn('beste wahl', joined,
                         'Das Pauschal-Ranking „oft die beste Wahl“ ist zurück (Befund 7).')
        self.assertNotIn('schwächste lösung', joined,
                         'Die Pauschale „meist die schwächste Lösung“ ist zurück.')
        for sent in sentences(body):
            if re.search(r'(cloudflare|google|opendns)', sent) \
               and re.search(r'(schnellste|extrem fix|am schnellsten|beste)', sent):
                self.assertTrue(re.search(r'(wirbt|gibt an|kann|mess|eigene|hängt)', sent),
                                f'Anbieter-Tempo-Pauschale ohne Mess-Vorbehalt: {sent!r}')
        # Tabellenzelle: Cloudflare-Vorteil darf kein nacktes „schnell“ sein.
        for line in body.splitlines():
            if line.startswith('|') and 'cloudflare' in line.lower():
                zellen = [norm(z) for z in line.strip('|').split('|')]
                vorteil = zellen[2] if len(zellen) > 2 else ''
                if re.search(r'\bschnell\b', vorteil):
                    self.assertTrue(re.search(r'(wirbt|kann|mess)', vorteil),
                                    f'Cloudflare-Vorteilszelle mit nackter Tempo-Behauptung: {vorteil!r}')
        # Heilung: eigene Messung statt Pauschalurteil.
        self.assertTrue(re.search(r'(rangliste gibt es nicht|miss[^.]{0,30}selbst'
                                  r'|eigene messung|pauschalurteil)', joined),
                        'Die Mess-Empfehlung als Ranking-Ersatz fehlt (Befund 7).')


class Faktenfrische823MetaTests(unittest.TestCase):
    """Metadaten, Geometrie, Gates und Verträge – damit der Fix nicht wegfault."""

    def test_metadaten_dauerhaft_korrekt(self):
        for slug in (SAISON, DNS):
            with self.subTest(slug=slug):
                fm, body = read(slug)
                self.assertIsNotNone(fm.get('lastmod'), 'lastmod fehlt')
                self.assertGreaterEqual(fm['lastmod'], KORRIGIERT_AM,
                                        'lastmod muss den Texteingriff vom 24.10. dokumentieren.')
                # Der Maschinen-Stamp vom echten Lauf (20.10.) darf nicht
                # zurückdatiert werden; eine Obergrenze ist kein Testthema –
                # faktenfrische.py setzt neue Stempel nur nach echten Läufen.
                self.assertIsNotNone(fm.get('faktencheck'), 'faktencheck fehlt')
                self.assertGreaterEqual(fm['faktencheck'], LAUF_FAKTENCHECK)
                self.assertTrue(fm.get('kurzantwort'), 'kurzantwort (GEO) fehlt')
                self.assertTrue(70 <= len(fm['description']) <= 165,
                                f'description außerhalb SEO-Korridor: {len(fm["description"])}')
                self.assertFalse(re.search(r':\s*[^:|]*:', fm['description']),
                                 'Doppel-Doppelpunkt-Muster in der description (Maschinen-Klebe).')
                geo = faktenfrische.geo_reife(dict(
                    body=body, kurzantwort=fm['kurzantwort'],
                    quellen_vorhanden=bool(fm.get('quellen')),
                    faktencheck=fm.get('faktencheck')))
                self.assertEqual(geo['prozent'], 100, f'GEO-Kriterien offen: {geo["offen"]}')
        # Sichtbarer Stand im Saison-Artikel (Datum darf gepflegt werden,
        # die Sichtbarkeit selbst ist die Invariante).
        _, saison_body = read(SAISON)
        self.assertRegex(saison_body, r'\*\*Stand: \d{2}\.\d{2}\.\d{4}\.\*\*')

    def test_quellen_bleiben_an_das_dossier_gebunden(self):
        """Anti-Halluzinations-Parität für redaktionelle Handarbeit: Jede URL
        im Frontmatter muss wörtlich im Recherche-Dossier des Laufs stehen."""
        for slug in (SAISON, DNS):
            with self.subTest(slug=slug):
                dossier = ROOT / 'data' / 'research' / 'artikel' / f'{slug}.json'
                if not dossier.is_file():
                    self.skipTest(f'Dossier für {slug} nicht vorhanden')
                urls = {t['url'] for t in json.loads(
                    dossier.read_text(encoding='utf-8')).get('treffer', [])}
                fm, _ = read(slug)
                for q in fm.get('quellen') or []:
                    self.assertIn(q['url'], urls,
                                  f'Quelle nicht vom Dossier gedeckt: {q["url"]}')
                # Das heise-Quellendatum muss zum Dossier passen (nicht erfunden).
                if slug == DNS:
                    d = json.loads(dossier.read_text(encoding='utf-8'))
                    heise = next((t for t in d['treffer'] if 'heise.de' in t['url']), None)
                    q2 = next((q for q in fm['quellen'] if 'heise.de' in q['url']), None)
                    if heise and heise.get('datum') and q2 and q2.get('datum'):
                        self.assertTrue(heise['datum'].startswith(str(q2['datum'])),
                                        f'Quellen-Datum weicht vom Dossier ab: {q2["datum"]}')

    def test_rechenbeispiele_dns_rechnen_auf(self):
        """Die ms-Modelle im DNS-Artikel: Zellen müssen untereinander stimmen,
        unabhängig von Schreibweise (Punkte, Bindestriche, NBSP)."""
        _, body = read(DNS)
        z = body
        for a, b in DASHES.items():
            z = z.replace(a, b)
        z = z.replace('\u00a0', ' ').replace('\u202f', ' ')
        z = z.replace('×', 'x').replace('·', 'x')  # Mal-Zeichen vereinheitlichen
        m = re.search(r'(\d+) seiten x (\d+) suchen x (\d+) ms = ([\d.]+) ms', z.lower())
        self.assertIsNotNone(m, 'Einzelnutzer-Formel fehlt/verstümmelt')
        seiten, suchen, ms, gesamt = (Decimal(x.replace('.', '')) for x in m.groups())
        self.assertEqual(seiten * suchen * ms, gesamt)               # 12.000
        m2 = re.search(r'das sind ([\d.]+) sekunden', z.lower())
        self.assertIsNotNone(m2, 'Sekunden-Ergebnis fehlt')
        self.assertEqual(Decimal(m2.group(1).replace('.', '')), gesamt / 1000)  # 12
        f1 = re.search(r'(\d[\d.]*) x (\d+) = ([\d.]+) stück', z.lower())
        self.assertIsNotNone(f1, 'Familien-Abfrageformel fehlt')
        q = lambda s: Decimal(s.replace('.', ''))  # noqa: E731
        self.assertEqual(q(f1.group(1)) * q(f1.group(2)), q(f1.group(3)))       # 20.000
        f2 = re.search(r'([\d.]+) x (\d+) ms = ([\d.]+) ms', z.lower())
        self.assertIsNotNone(f2, 'Familien-Zeitformel fehlt')
        self.assertEqual(q(f2.group(1)) * q(f2.group(2)), q(f2.group(3)))       # 1.000.000
        self.assertEqual(q(f2.group(1)), q(f1.group(3)))
        f3 = re.search(r'das sind ([\d.]+) sekunden oder fast (\d+) minuten', z.lower())
        self.assertIsNotNone(f3, 'Familien-Ergebnis fehlt')
        self.assertEqual(q(f3.group(1)), q(f2.group(3)) / 1000)                 # 1.000
        self.assertLessEqual(abs(q(f3.group(2)) - q(f3.group(1)) / 60), 1)      # ~17
        # Modell-Kennzeichnung + Cache-Einordnung müssen bei den Beispielen stehen.
        self.assertIn('frei gewählte annahmen', norm(body),
                      'Die ms-Modelle müssen als frei gewählte Annahmen gekennzeichnet sein.')
        self.assertIn('cache', norm(body),
                      'Die Cache-Einordnung zu den Modellen fehlt (Ehrlichkeits-Anker).')

    def test_publish_gates_fuer_beide_entwuerfe_gruen(self):
        """Gate-Parität: Ein #823-Fix, der am Lesbarkeits-, Längen- oder
        Link-Gate scheitert, wird von der Kadenz gehalten – der Entwurf
        verrottet im Hold. Deshalb werden genau diese Gates hier mitgeprüft."""
        import readability_check as rc
        import length_policy as lp
        import link_density_guard as ldg
        from textverstaendnis_guard import (
            split_body, load_terminologie, check_article, frontmatter_keywords)
        try:
            from publish_gate import HARTE_REGELN
        except Exception:  # pragma: no cover - Fallback, falls Refactor
            HARTE_REGELN = {'R2-KEYWORD-DUMP', 'R3-TERMINOLOGIE', 'R5-ABSATZ-HART',
                            'R7-INTRO-FORMEL', 'R8-URL-LEERZEICHEN', 'R8-NESTED-LINK',
                            'R9-KLEBEWORT', 'R10-DOPPELWORT', 'R11-JAHRESZAHL-SPLIT',
                            'R12-ZAHL-RUINE', 'R13-DATUM-PUNKT', 'R14-MARKER-RUINE',
                            'R15-PHRASEN-DOPPEL', 'R16-PROMPT-ECHO',
                            'R16-PROMPT-ECHO-META', 'R17-KEYWORD-KASUS',
                            'R17-KEYWORD-DOPPEL'}
        floor, ceiling = lp.POSTS['target_min_chars'], lp.POSTS['fat_chars']
        term = load_terminologie()
        for slug in (SAISON, DNS):
            with self.subTest(slug=slug):
                path = resolve(slug) / 'index.md'
                raw = path.read_text(encoding='utf-8')
                res = rc.analyze(rc.parse_article(raw, slug))
                self.assertGreaterEqual(res['score'], 75, f"Score: {res['issues']}")
                self.assertGreaterEqual(res['flesch'], rc.NEW_FLESCH_MIN,
                                        f"Flesch {res['flesch']} < {rc.NEW_FLESCH_MIN}")
                _, chars = lp.measure(raw)
                self.assertTrue(floor <= chars <= ceiling,
                                f'{chars} Zeichen außerhalb Korridor {floor}-{ceiling}')
                findet = [f for f in check_article(str(path), split_body(raw), term,
                                                   frontmatter_keywords(raw))
                          if f[1] in HARTE_REGELN]
                self.assertFalse(findet, f'Harte Textverständnis-Regeln: {findet}')
                body = raw.split('---', 2)[2]
                self.assertGreaterEqual(len(ldg.count_links(body)), ldg.MIN_LINKS,
                                        'Unter MIN_LINKS: der Entwurf wäre link-unterversorgt.')

    def test_faktenfrische_queue_haelt_befunde_geschlossen(self):
        """Die offene Queue darf die zwei Slugs nicht mehr führen. Ein neuer
        Lauf, der dieselben Fehler zurückmeldet, macht hier rot."""
        try:
            queue = json.loads((ROOT / 'data' / 'faktenfrische_queue.json')
                               .read_text(encoding='utf-8'))
        except FileNotFoundError:
            self.skipTest('Queue-Datei nicht vorhanden')
        kerne = {re.sub(r'^\d{4}-\d{2}-\d{2}-', '', s) for s in (SAISON, DNS)}
        for eintrag in queue.get('offen', []):
            slug = eintrag.get('slug') or ''
            kern = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)
            self.assertNotIn(kern, kerne,
                             f'Queue meldet offene Befunde für {slug}')

    def test_systemprompt_prueft_die_823_befundklassen(self):
        prompt = faktenfrische.SYSTEM_PROMPT.lower()
        for rule in ('befund-klassen aus #823',
                     'modellrechnung mit frei gewählten annahmen',
                     'namensauflösung ist nicht bandbreite',
                     'oft die beste wahl'):
            self.assertIn(rule, prompt,
                          f'Die #823-Prüfanweisung fehlt im Systemprompt: {rule!r}')


if __name__ == '__main__':
    unittest.main()
