"""Offline-Regression für die redaktionelle Heilung von Issue #911.

Stand 30.10.2026. Geprüft werden BEDEUTUNGS-Invarianten und Rechenwege,
keine starren Formulierungen (Lehre aus #763/#823: Ein Test, den jede
harmlose Umformung bricht, schützt nichts). Nummerierung wie im Register
`data/faktenfrische_befunde_911.yaml`:

  B1  strom · luecke     – „große Lücken zwischen den Tarifen“ ohne Quelle
  B2  strom · luecke     – Bonus senkt den Preis im ersten Jahr „stark“
  B3  strom · praezision – Verbrauchsschwelle 3.000/2.000 kWh als Tarifregel
  B4  strom · praezision – Wechsel „kostet keinen Cent“, keine Abschiedsgebühr
  B5  strom · praezision – CHECK24 listet „fast alle Firmen und Tarife“
  B6  gas   · luecke     – Regulierungsrahmen der Bundesnetzagentur fehlte
  B7  gas   · luecke     – Preisgarantie „typischerweise sechs Monate“
  B8  gas   · luecke     – Thermostat spart „bis zu 10 Prozent“
  B9  gas   · luecke     – „2 °C = 6 % = 720 kWh“ ohne Quelle/Modellgrenze
  B10 gas   · praezision – CHECK24 zeigt „alle wichtigen Konditionen“

Dauerhaftigkeit heißt hier dreierlei:
  1. Die zehn Fehlbehauptungen dürfen behauptend nie zurückkehren;
     Dämpfungen, Verneinungen und ausdrücklich verworfene Beispiele
     bleiben erlaubt.
  2. Modellrechnungen müssen gekennzeichnet bleiben UND ihre Arithmetik
     muss aus den Zellen selbst nachgerechnet werden.
  3. Gate-Parität: Lesbarkeit (Score ≥ 75, Flesch ≥ 60), Zeichenkorridor,
     harte Textverständnis-Regeln, interne Links ≥ 2, GEO-Reife 6/6,
     Quellen-Allowlist und Registerbindung – sonst verrottet der Entwurf
     im Hold und die Heilung wirkt nur scheinbar.

Kein Ersatz für eine Fachprüfung: Rückfall-Schutz, kein Wahrheitsbeweis.
"""
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import faktenfrische  # noqa: E402

STROM = '2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen'
GAS = '2026-10-26-gastarife-vergleichen-vor-dem-herbst'
KORRIGIERT_AM = dt.date(2026, 10, 30)
LAUF_FAKTENCHECK = dt.date(2026, 10, 27)   # echter Recherchelauf vom 27.10.
REGISTER = ROOT / 'data' / 'faktenfrische_befunde_911.yaml'
DASHES = {
    '\u2013': '-', '\u2014': '-', '\u2012': '-', '\u2011': '-',
    '\u00a0': ' ', '\u202f': ' ', '\u2212': '-',
}
NEGATION = re.compile(r'\b(nicht|kein|keine|keinen|keinem|keiner|ohne|kaum|nie|niemals)\b')


def resolve(slug):
    """Slug über Lebenszyklus-Umbenennungen hinweg auflösen."""
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
    text = text.replace('€', ' euro ')
    return re.sub(r'\s+', ' ', text.lower()).strip()


def chunks(body):
    """Absatzweise, inklusive Tabellen-/Zitatblöcken als eigene Chunks."""
    return [norm(p) for p in re.split(r'\n\s*\n', body) if p.strip()]


def sentences(body):
    """Fließtext-Sätze; Überschriften-/Tabellen-/Listen-/Zitatzeilen raus."""
    flow = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s[0] in '#|*>-':
            continue
        flow.append(s)
    return [s for s in re.split(r'(?<=[.!?])\s+', norm(' '.join(flow))) if s]


def behauptend(body, phrase):
    """Steht die Wendung behauptend im Text? Verneinung im Satz schützt."""
    text = norm(body)
    p = norm(phrase)
    for m in re.finditer(re.escape(p), text):
        start = max(text.rfind('.', 0, m.start()),
                    text.rfind('!', 0, m.start()),
                    text.rfind('?', 0, m.start()))
        enden = [i for i in (text.find('.', m.end()),
                             text.find('!', m.end()),
                             text.find('?', m.end())) if i != -1]
        ende = min(enden) if enden else len(text)
        satz = text[start + 1:ende + 1]
        if not NEGATION.search(satz):
            return True
    return False


def _ziffer(token):
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', token):          # 3.200 / 1.144
        return Decimal(token.replace('.', ''))
    return Decimal(token.replace('.', '').replace(',', '.'))  # 0,32 / 57,60


def rechne(zelle):
    """Deutsche Rechenzelle auswerten: „3.200 × 0,32“, „1.024 + 120“."""
    wert, op = None, None
    for token in re.findall(r'\d[\d.,]*|[x×*+/-]|mal|durch', norm(zelle)):
        if token in ('mal', 'x', '×', '*'):
            op = '*'
            continue
        if token in ('durch', '/'):
            op = '/'
            continue
        if token in ('+', '-'):
            op = token
            continue
        z = _ziffer(token)
        if wert is None:
            wert = z
        elif op == '*':
            wert *= z
        elif op == '/':
            wert /= z
        elif op == '+':
            wert += z
        elif op == '-':
            wert -= z
        else:
            raise AssertionError(f'Zelle ohne Operator: {zelle!r}')
    return wert


def zahl(text):
    """Letzte Zahl einer Zelle, deutsche Schreibweise, als Decimal."""
    m = re.findall(r'\d{1,3}(?:\.\d{3})+,\d+|\d{1,3}(?:\.\d{3})+|\d+,\d+|\d+', norm(text))
    assert m, f'keine Zahl in Zelle: {text!r}'
    return _ziffer(m[-1])


def zeilen(body):
    """Tabellenzeilen als Zellenliste; Kopf und Trennzeile bleiben drin."""
    out = []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith('|'):
            continue
        zellen = [norm(z) for z in s.strip('|').split('|')]
        if zellen and all(re.fullmatch(r':?-{2,}:?', z.replace(' ', ''))
                          for z in zellen):
            continue
        out.append(zellen)
    return out


def zeile(body, label):
    for z in zeilen(body):
        if z and label in z[0]:
            return z
    raise AssertionError(f'Tabellenzeile „{label}“ fehlt')


def gleichung(zelle):
    """„… = Ergebnis“ → (linke Seite, Ergebnis) als Decimal-Paar."""
    teile = zelle.split('=')
    assert len(teile) == 2, f'keine Gleichung: {zelle!r}'
    return rechne(teile[0]), zahl(teile[1])


def register():
    return yaml.safe_load(REGISTER.read_text(encoding='utf-8'))


class Faktenfrische911Tests(unittest.TestCase):
    """Die zehn Befunde aus dem Lauf vom 27.10.2026 – je einer pro Art."""

    # --- B1: „große Lücken zwischen den Tarifen“ (luecke) ------------------
    def test_b1_angebotsvielfalt_statt_unbelegter_marktluecke(self):
        _, body = read(STROM)
        joined = norm(body)
        self.assertFalse(behauptend(body, 'große Lücken zwischen den Tarifen'),
                         'Unbelegte Marktlücke ist behauptend zurück.')
        self.assertIn('angebotsvielfalt', joined,
                      'Der belegte Gegenanker „Angebotsvielfalt“ fehlt.')
        self.assertIn('ein pauschales sparversprechen ist damit nicht verbunden', joined)
        # Die Ersparnis muss an die eigenen Werte gebunden sein.
        self.assertRegex(joined, r'(verbrauch|tarif)[^.]{0,120}angebot')

    # --- B2: Bonus-Versprechen (luecke) ------------------------------------
    def test_b2_bonus_nur_als_gekennzeichnete_rechengroesse(self):
        _, body = read(STROM)
        joined = norm(body)
        for verboten in ('Bonus senkt den Preis im ersten Jahr stark',
                         'Bonus macht den Tarif im ersten Jahr deutlich billiger'):
            self.assertFalse(behauptend(body, verboten),
                             f'Bonus-Werbeversprechen zurück: {verboten!r}')
        self.assertIn('ein bonus ist eine eigene rechengröße', joined)
        self.assertIn('rechne den tarif zusätzlich ohne bonus', joined)
        # Der Bonus muss zusätzlich in der Tabelle als bedingt markiert sein.
        bonus = zeile(body, 'bonus')
        self.assertIn('bedingungen', bonus[1])
        self.assertNotIn('garantiert', bonus[2])

    # --- B3: Verbrauchsschwelle als Tarifregel (praezision) ----------------
    def test_b3_keine_verbrauchsschwelle_als_tarifregel(self):
        _, body = read(STROM)
        for verboten in ('ab 3.000 kWh', 'ab 3000 kWh', 'über 3.000 kWh'):
            self.assertFalse(behauptend(body, verboten),
                             f'Pauschale Verbrauchsschwelle zurück: {verboten!r}')
        joined = norm(body)
        self.assertIn('bei kleinen haushalten wiegt der grundpreis schwerer', joined)
        self.assertIn('rechne deshalb immer den jahresbetrag für deinen eigenen verbrauch', joined)

    # --- B4: „kostenlos“ ohne Zielgruppe/Norm (praezision) -----------------
    def test_b4_kostenfrei_nur_fuer_haushaltskunden_mit_norm(self):
        _, body = read(STROM)
        joined = norm(body)
        for satz in sentences(body):
            if 'kostenfrei' in satz:
                self.assertTrue('haushaltskund' in satz or '§ 20' in satz,
                                f'„kostenfrei“ ohne Zielgruppe/Norm: {satz!r}')
        self.assertIn('§ 20 stromgvv', joined)
        self.assertIn('§ 20a absatz 3 enwg', joined)
        self.assertIn('für andere kundengruppen gilt diese aussage nicht automatisch', joined)
        for verboten in ('Abschiedsgebühr', 'immer kostenfrei', 'kostet keinen Cent'):
            self.assertFalse(behauptend(body, verboten),
                             f'Unbelegte Gebührenbehauptung zurück: {verboten!r}')

    # --- B5: Portal-Vollständigkeit (praezision) ---------------------------
    def test_b5_kein_vollstaendigkeitsversprechen_fuer_portale(self):
        _, body = read(STROM)
        joined = norm(body)
        for verboten in ('fast alle Firmen und Tarife', 'fast alle Anbieter',
                         'alle Tarife und Anbieter'):
            self.assertFalse(behauptend(body, verboten),
                             f'Vollständigkeitsversprechen zurück: {verboten!r}')
        self.assertIn('ein portal hilft beim ersten überblick', joined)
        self.assertIn('dass ein portal alle anbieter und tarife abbildet', joined)
        self.assertIn('vor dem abschluss die unterlagen zu prüfen', joined)

    # --- B6: Regulierungsrahmen Gas (luecke) -------------------------------
    def test_b6_gas_regulierungsrahmen_und_keine_preisgenehmigung(self):
        _, body = read(GAS)
        joined = norm(body)
        self.assertIn('beaufsichtigt den gasmarkt', joined,
                      'Der Regulierungsrahmen der Bundesnetzagentur fehlt (Befund 6).')
        self.assertIn('eine staatliche genehmigung der endkundenpreise gibt es nicht', joined)
        self.assertIn('die preise für haushalte genehmigt sie nicht', joined)
        for verboten in ('nicht jeden Preis', 'die Preise werden genehmigt',
                         'Preise werden von der Behörde festgelegt'):
            self.assertFalse(behauptend(body, verboten),
                             f'Preisgenehmigung behauptet: {verboten!r}')
        self.assertIn('in der grundversorgung gilt eine eigene kündigungsfrist von zwei wochen', joined)

    def test_b6b_24_stunden_regel_nur_fuer_strom(self):
        """Die 24-Stunden-Regel gilt für Strom, nicht pauschal für Gas."""
        _, body = read(GAS)
        joined = norm(body)
        self.assertIn('beim strom ist der technische wechsel seit dem 6. juni 2025', joined)
        self.assertIn('für gas gelten die regulären fristen des wechselprozesses', joined)
        self.assertFalse(behauptend(body, 'Der technische Wechsel ist seit dem 6. Juni 2025'),
                         '24-Stunden-Regel wird pauschal auf Gas übertragen.')

    # --- B7: Preisgarantie-Standarddauer (luecke) --------------------------
    def test_b7_preisgarantie_ohne_erfundene_standarddauer(self):
        _, body = read(GAS)
        joined = norm(body)
        self.assertIn('keine einheitliche standarddauer', joined)
        for verboten in ('dauert typischerweise sechs Monate',
                         'Standarddauer von sechs Monaten',
                         'Garantie gilt sechs Monate'):
            self.assertFalse(behauptend(body, verboten),
                             f'Erfundene Garantiedauer zurück: {verboten!r}')
        # Das verworfene Beispiel darf als Absage stehen bleiben.
        self.assertIn('typisch sechs monate', joined)
        self.assertFalse(behauptend(body, 'typisch sechs Monate'))
        self.assertIn('welcher preis gilt nach dem ende', joined)

    # --- B8: Thermostat/10 Prozent (luecke) --------------------------------
    def test_b8_thermostat_richtwert_der_verbraucherzentrale(self):
        _, body = read(GAS)
        joined = norm(body)
        self.assertIn('ein grad weniger raumtemperatur senkt den verbrauch um etwa sechs prozent', joined)
        para = [c for c in chunks(body) if 'sechs prozent' in c]
        self.assertTrue(any('verbraucherzentrale' in p or 'q3' in p for p in para),
                        'Sechs-Prozent-Richtwert ohne Zuordnung zur Verbraucherzentrale.')
        for verboten in ('bis zu 10 Prozent', 'bis zu zehn Prozent', '10 % Einsparung'):
            self.assertFalse(behauptend(body, verboten),
                             f'Unbelegte 10-Prozent-Behauptung zurück: {verboten!r}')
        self.assertIn('unter 16 grad solltest du nicht dauerhaft heizen', joined)

    # --- B9: 2 °C / 6 % / 720 kWh (luecke) ---------------------------------
    def test_b9_temperaturmodell_ohne_scheinpraezision(self):
        _, body = read(GAS)
        joined = norm(body)
        m = re.search(r'bei ([\d.]+) kwh wären sechs prozent ([\d.]+) kwh', joined)
        self.assertIsNotNone(m, 'Das 720-kWh-Modell fehlt oder ist verstümmelt.')
        verbrauch, ersparnis = (_ziffer(x) for x in m.groups())
        self.assertEqual(verbrauch, Decimal(12000))
        self.assertEqual(verbrauch * Decimal('0.06'), ersparnis)      # 720
        m2 = re.search(r'bei angenommenen ([\d,]+) euro je kwh entspricht das ([\d,]+) euro', joined)
        self.assertIsNotNone(m2, 'Der Euro-Wert des Modells fehlt.')
        preis, kosten = (_ziffer(x) for x in m2.groups())
        self.assertEqual(ersparnis * preis, kosten)                   # 57,60
        self.assertIn('zwei grad weniger bedeuten nicht automatisch zwölf prozent', joined)
        # Der 720er-Wert muss als Modell gekennzeichnet sein (Prosachunk davor/danach).
        cks = chunks(body)
        for i, c in enumerate(cks):
            if '720 kwh' in c:
                kontext = ' '.join(cks[max(0, i - 1):i + 1])
                self.assertTrue(re.search(r'(modell|rechenbeispiel|annahme)', kontext),
                                '720 kWh stehen ohne Modell-Kennzeichnung im Text.')
        for verboten in ('zwei Grad weniger senken den Verbrauch um sechs Prozent',
                         'spart damit 720 kWh'):
            self.assertFalse(behauptend(body, verboten),
                             f'Unzulässige Temperaturrechnung zurück: {verboten!r}')

    # --- B10: „alle wichtigen Konditionen“ (praezision) -------------------
    def test_b10_portal_zeigt_keine_vollstaendigen_konditionen(self):
        _, body = read(GAS)
        joined = norm(body)
        self.assertIn('ein portal zeigt eine auswahl, nicht den gesamten markt', joined)
        for verboten in ('alle wichtigen Konditionen', 'alle Konditionen im Überblick'):
            self.assertFalse(behauptend(body, verboten),
                             f'Konditionen-Vollständigkeit zurück: {verboten!r}')
        self.assertIn('prüfe die bedingungen beim anbieter', joined)
        self.assertIn('vergleiche die vollständigen kosten', joined)


class Faktenfrische911RechenTests(unittest.TestCase):
    """Modellrechnungen werden aus den Zellen selbst nachgerechnet."""

    def test_strom_modell_rechnet_zelle_fuer_zelle(self):
        _, body = read(STROM)
        alt = zeile(body, 'kosten für verbrauch')
        self.assertEqual(gleichung(alt[1]), (Decimal(1024), Decimal(1024)))  # 3.200 × 0,32
        self.assertEqual(gleichung(alt[2]), (Decimal(896), Decimal(896)))    # 3.200 × 0,28
        grund = zeile(body, 'grundpreis pro jahr')
        self.assertEqual(gleichung(grund[1]), (Decimal(120), Decimal(120)))
        self.assertEqual(gleichung(grund[2]), (Decimal(96), Decimal(96)))
        jahr = zeile(body, 'kosten im jahr')
        self.assertEqual(gleichung(jahr[1]), (Decimal(1144), Decimal(1144)))
        self.assertEqual(gleichung(jahr[2]), (Decimal(992), Decimal(992)))
        ersp = zeile(body, 'ersparnis im modell')
        links, rechts = gleichung(ersp[2])
        self.assertEqual(links, Decimal(152))
        self.assertEqual(rechts, Decimal(152))
        self.assertEqual(zahl(jahr[1].split('=')[-1]) - zahl(jahr[2].split('=')[-1]),
                         rechts)
        # Kennzeichnung muss als Prosa VOR der Tabelle stehen.
        cks = chunks(body)
        for i, c in enumerate(cks):
            if c.startswith('|') and '1.024' in c:
                vor = cks[i - 1] if i else ''
                self.assertIn('frei gewählt', vor,
                              'Modelltabelle ohne „frei gewählt“-Kennzeichnung davor.')

    def test_gas_modell_rechnet_zelle_fuer_zelle(self):
        _, body = read(GAS)
        verbrauch = zeile(body, 'kosten für verbrauch')
        links, rechts = gleichung(f'{verbrauch[1]} = {verbrauch[2]}')
        self.assertEqual(links, Decimal(960))                          # 12.000 × 0,08
        self.assertEqual(rechts, Decimal(960))
        grund = next(z for z in zeilen(body)
                     if len(z) == 3 and z[0] == 'grundpreis' and '12' in z[1])
        self.assertEqual(gleichung(f'{grund[1]} = {grund[2]}'),
                         (Decimal(120), Decimal(120)))                 # 12 × 10
        summe = zeile(body, 'kosten im modell')
        self.assertEqual(gleichung(f'{summe[1]} = {summe[2]}'),
                         (Decimal(1080), Decimal(1080)))               # 960 + 120
        cks = chunks(body)
        for i, c in enumerate(cks):
            if c.startswith('|') and '960' in c:
                vor = cks[i - 1] if i else ''
                self.assertIn('frei gewählte modellrechnung', vor,
                              'Gas-Modell ohne Kennzeichnung als frei gewählte Rechnung.')


class Faktenfrische911MetaTests(unittest.TestCase):
    """Register, Metadaten, Gates und Verträge – damit der Fix nicht wegfault."""

    def test_register_schliesst_alle_zehn_befunde_mit_beleg(self):
        reg = register()
        self.assertEqual(reg['issue'], 911)
        self.assertEqual(str(reg['stand']), '2026-10-30')
        befunde = reg['befunde']
        self.assertEqual(len(befunde), 10)
        self.assertEqual({b['artikel'] for b in befunde}, {STROM, GAS})
        pro_artikel = {slug: sum(1 for b in befunde if b['artikel'] == slug)
                       for slug in (STROM, GAS)}
        self.assertEqual(pro_artikel, {STROM: 5, GAS: 5})
        allow = yaml.safe_load((ROOT / 'data' / 'agent_reach' / 'faktenfrische.yaml')
                               .read_text(encoding='utf-8'))
        domains = [q['domain'] for q in allow['quellen_allowlist']]
        for b in befunde:
            with self.subTest(befund=b['id']):
                self.assertEqual(b['status'], 'behoben')
                fm, body = read(b['artikel'])
                joined = norm(body + '\n' + fm.get('kurzantwort', ''))
                self.assertTrue(b['anker'], 'Befund ohne Bedeutungsanker.')
                for anker in b['anker']:
                    self.assertIn(norm(anker), joined,
                                  f'Anker fehlt: {anker!r} ({b["id"]})')
                for verboten in b.get('verboten_behauptend') or []:
                    self.assertFalse(behauptend(body, verboten),
                                     f'Fehlbehauptung zurück: {verboten!r} ({b["id"]})')
                if b['beleg_url']:
                    self.assertTrue(b['beleg_url'].startswith('https://'))
                    self.assertTrue(any(b['beleg_url'].split('/')[2].endswith(d)
                                        for d in domains),
                                    f'Beleg nicht auf der Allowlist: {b["beleg_url"]}')
                    self.assertIn(b['beleg_url'],
                                  [q['url'] for q in (fm.get('quellen') or [])],
                                  f'Beleg steht nicht in den Artikelquellen: {b["beleg_url"]}')
                else:
                    self.assertEqual(b['belegtyp'], 'streichung',
                                     'Beleglos ist nur eine Streichung zulässig.')

    def test_quellen_bleiben_allowlist_und_dossierfaehig(self):
        for slug in (STROM, GAS):
            with self.subTest(slug=slug):
                fm, _ = read(slug)
                self.assertGreaterEqual(len(fm.get('quellen') or []), 2)
                for q in fm['quellen']:
                    self.assertTrue(q['url'].startswith('https://'))
                    self.assertTrue(q.get('herausgeber'))
                    self.assertRegex(q['url'], r'bundesnetzagentur\.de|verbraucherzentrale\.de')

    def test_metadaten_und_geo_reife_dauerhaft_korrekt(self):
        for slug in (STROM, GAS):
            with self.subTest(slug=slug):
                fm, body = read(slug)
                self.assertIs(fm.get('draft'), True,
                              'Heilung darf den Entwurfsstatus nicht aufheben.')
                self.assertIsNotNone(fm.get('lastmod'), 'lastmod fehlt')
                self.assertGreaterEqual(fm['lastmod'], KORRIGIERT_AM,
                                        'lastmod muss den Texteingriff vom 30.10. dokumentieren.')
                self.assertIsNotNone(fm.get('faktencheck'), 'faktencheck fehlt')
                self.assertGreaterEqual(fm['faktencheck'], LAUF_FAKTENCHECK)
                self.assertTrue(fm.get('kurzantwort'), 'kurzantwort (GEO) fehlt')
                self.assertTrue(70 <= len(fm['description']) <= 165,
                                f'description außerhalb SEO-Korridor: {len(fm["description"])}')
                self.assertFalse(re.search(r':\s*[^:|]*:', fm['description']),
                                 'Doppel-Doppelpunkt-Muster in der description.')
                geo = faktenfrische.geo_reife(dict(
                    body=body, kurzantwort=fm['kurzantwort'],
                    quellen_vorhanden=bool(fm.get('quellen')),
                    faktencheck=fm.get('faktencheck')))
                self.assertEqual(geo['prozent'], 100, f'GEO-Kriterien offen: {geo["offen"]}')
                self.assertRegex(body, r'\*\*Fachlich überarbeitet am 30\.10\.2026\.\*\*')

    def test_publish_gates_fuer_beide_entwuerfe_gruen(self):
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
        for slug in (STROM, GAS):
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

    def test_keine_sie_anrede_im_du_artikel(self):
        for slug in (STROM, GAS):
            with self.subTest(slug=slug):
                _, body = read(slug)
                for wort in ('Ihnen', 'Ihre', 'Ihren', 'Ihrem', 'Ihrer'):
                    self.assertNotRegex(body, rf'\b{wort}\b',
                                        f'Formelle Anrede mitten im Du-Artikel: {wort}')
                self.assertFalse(re.search(r'\bfür Sie\b|\ban Sie\b|\bbei Ihnen\b', body),
                                 'Formelle Anrede im Du-Artikel.')

    def test_queue_und_register_halten_die_befunde_geschlossen(self):
        try:
            queue = json.loads((ROOT / 'data' / 'faktenfrische_queue.json')
                               .read_text(encoding='utf-8'))
        except FileNotFoundError:
            self.skipTest('Queue-Datei nicht vorhanden')
        kerne = {re.sub(r'^\d{4}-\d{2}-\d{2}-', '', s) for s in (STROM, GAS)}
        for eintrag in queue.get('offen', []):
            slug = eintrag.get('slug') or ''
            kern = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)
            self.assertNotIn(kern, kerne, f'Queue meldet offene Befunde für {slug}')
        # Der Register-Eintrag muss den Lauf und die Heilung datieren.
        reg = register()
        self.assertIn('2026-10-27', reg['lauf'])
        self.assertEqual(reg['recherche']['abrufe'][0]['abgerufen'], dt.date(2026, 10, 30))

    def test_systemprompt_prueft_die_911_befundklassen(self):
        prompt = faktenfrische.SYSTEM_PROMPT.lower()
        for regel in ('befund-klassen aus #911',
                      'alle wichtigen konditionen',
                      'ab 3.000 kwh',
                      'abschiedsgebühr',
                      'aufsicht ist keine preisgenehmigung',
                      '2 °c = 6 %'):
            self.assertIn(regel, prompt,
                          f'Die #911-Prüfanweisung fehlt im Systemprompt: {regel!r}')


if __name__ == '__main__':
    unittest.main()
