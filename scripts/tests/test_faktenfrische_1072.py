"""Offline-Regression für die redaktionelle Heilung von Issue #1072.

Stand 05.11.2026. Geprüft werden Bedeutungs-Invarianten, Beleg-Urls und
die Registerbindung, keine starren Formulierungen (Lehre aus #763/#823).
Nummerierung wie im Register `data/faktenfrische_befunde_1072.yaml`.

Dauerhaftigkeit heißt hier dreierlei:
  1. Die 47 beanstandeten Aussagen dürfen behauptend nie zurückkehren;
     Dämpfungen, Verneinungen und ausdrücklich verworfene Beispiele
     bleiben erlaubt.
  2. Jeder Befund ist an den aktuellen Text-Hash gebunden (nicht an eine
     Prüffassung); ein neuer `faktencheck`-Datum schließt keinen Befund.
  3. Gate-Parität: Beleg-Urls stammen aus der Allowlist und stehen in den
     Artikelquellen; Register und Ledger stimmen überein.

Kein Ersatz für eine Fachprüfung: Rückfall-Schutz, kein Wahrheitsbeweis.
"""
import datetime as dt
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

REGISTER = ROOT / 'data' / 'faktenfrische_befunde_1072.yaml'
QUEUE = ROOT / 'data' / 'faktenfrische_queue.json'
ENTSCHEIDUNGEN = ROOT / 'data' / 'faktenfrische_entscheidungen.yaml'
ALLOWLIST = ROOT / 'data' / 'agent_reach' / 'faktenfrische.yaml'

DASHES = {
    '\u2011': '-', '\u2013': '-', '\u2014': '-', '\u2212': '-',
    '\u00a0': ' ', '\u202f': ' ',
}
ENTITIES = {"&nbsp;": " ", "&ndash;": "-", "&mdash;": "-", "&amp;": "&",
            "&euro;": "€", "&quot;": '"', "&apos;": "'"}
NEGATION = re.compile(r'\b(nicht|kein|keine|keinen|keinem|keiner|ohne|kaum|nie|niemals|existiert nicht|ist nicht|gibt es nicht)\b')


def norm(text):
    for k, v in ENTITIES.items():
        text = text.replace(k, v)
    text = str(text).lower()
    for k, v in DASHES.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip()


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


def _kern(s):
    if len(s) > 10 and s[4] == '-' and s[7] == '-':
        if s[:4].isdigit() and s[5:7].isdigit() and s[8:10].isdigit():
            return s[10:]
    return s


def resolve(slug):
    """Slug über Lebenszyklus-Umbenennungen hinweg auflösen (posts + pillar)."""
    posts = ROOT / 'content' / 'posts'
    pillar = ROOT / 'content' / 'pillar'
    exact = posts / slug
    if (exact / 'index.md').is_file():
        return exact
    kern = _kern(slug)
    treffer = sorted(
        p for p in list(posts.glob('*')) + list(pillar.glob('*'))
        if (p / 'index.md').is_file() and _kern(p.name) == kern)
    if len(treffer) == 1:
        return treffer[0]
    raise FileNotFoundError(
        f'{slug}: weder exakt noch eindeutig als *-{kern} in content/posts '
        f'(Treffer: {[p.name for p in treffer]})')


def read(slug):
    text = (resolve(slug) / 'index.md').read_text(encoding='utf-8')
    _, fm, body = text.split('---', 2)
    return yaml.safe_load(fm), body


def register():
    return yaml.safe_load(REGISTER.read_text(encoding='utf-8'))


def allowlist_domains():
    data = yaml.safe_load(ALLOWLIST.read_text(encoding='utf-8'))
    return [q['domain'] for q in data['quellen_allowlist']]


class Faktenfrische1072RegisterTests(unittest.TestCase):
    """Register-Struktur und -Konsistenz mit Ledger/Queue."""

    def test_register_issue_und_stand(self):
        reg = register()
        self.assertEqual(reg['issue'], 1072)
        self.assertEqual(str(reg['stand']), '2026-11-05')
        self.assertIn('2026-11-05', reg['lauf'])

    def test_register_enthält_alle_47_befunde(self):
        reg = register()
        befunde = reg['befunde']
        self.assertEqual(len(befunde), 47)
        for b in befunde:
            with self.subTest(befund=b['id']):
                self.assertEqual(b['status'], 'behoben')
                self.assertTrue(b['entschieden_von'])
                self.assertGreaterEqual(len(b['entscheidung']), 20,
                                        f'Begründung zu kurz für {b["id"]}')
                self.assertTrue(b['anker'], f'Befund {b["id"]} ohne Bedeutungsanker.')
                self.assertTrue(b['geprueft_fassung'],
                                f'Befund {b["id"]} ohne geprueft_fassung.')

    def test_befunde_verteilen_sich_auf_artikel(self):
        reg = register()
        pro_artikel = Counter(b['artikel'] for b in reg['befunde'])
        self.assertEqual(sum(pro_artikel.values()), 47)
        for artikel in reg['artikel']:
            self.assertEqual(artikel['befunde'], pro_artikel[artikel['slug']],
                             f'Artikel {artikel["slug"]}: Zaehler stimmt nicht.')

    def test_anker_stehen_im_aktuellen_artikeltext(self):
        reg = register()
        cache = {}
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                if b['artikel'] not in cache:
                    fm, body = read(b['artikel'])
                    meta = ' '.join(str(fm.get(k, '')) for k in
                                    ('title', 'description', 'kurzantwort',
                                     'pin_title', 'pin_description'))
                    cache[b['artikel']] = norm(meta + ' ' + body)
                joined = cache[b['artikel']]
                for anker in b['anker']:
                    self.assertIn(norm(anker), joined,
                                  f'Anker fehlt: {anker!r} ({b["id"]})')

    def test_verboten_behauptend_kehrt_nicht_zurueck(self):
        reg = register()
        cache = {}
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                if b['artikel'] not in cache:
                    cache[b['artikel']] = read(b['artikel'])[1]
                body = cache[b['artikel']]
                for verboten in b.get('verboten_behauptend') or []:
                    self.assertFalse(behauptend(body, verboten),
                                     f'Fehlbehauptung zurück: {verboten!r} ({b["id"]})')

    def test_beleg_url_auf_allowlist_und_in_artikelquellen(self):
        domains = allowlist_domains()
        reg = register()
        cache = {}
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                self.assertTrue(b['beleg_url'].startswith('https://'),
                                f'Beleg-Url nicht https: {b["beleg_url"]}')
                self.assertTrue(any(b['beleg_url'].split('/')[2].endswith(d)
                                    for d in domains),
                                f'Beleg nicht auf der Allowlist: {b["beleg_url"]}')
                if b['artikel'] not in cache:
                    cache[b['artikel']] = read(b['artikel'])[0]
                fm = cache[b['artikel']]
                quellen = [q['url'] for q in (fm.get('quellen') or [])]
                if quellen:
                    self.assertIn(b['beleg_url'], quellen,
                                  f'Beleg steht nicht in den Artikelquellen: {b["beleg_url"]}')

    def test_entscheidungen_sind_gefasst_am_heute_text(self):
        reg = register()
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                self.assertEqual(b['entschieden_am'], '2026-11-05',
                                 f'Befund {b["id"]} nicht am heutigen Text entschieden.')
                self.assertRegex(b['geprueft_fassung'],
                                 r'^[0-9a-f]{64}$',
                                 f'geprueft_fassung ist kein SHA-256: {b["geprueft_fassung"]}')

    def test_register_referenziert_entscheidungen_mit_begruendung(self):
        reg = register()
        ents = yaml.safe_load(ENTSCHEIDUNGEN.read_text(encoding='utf-8'))['entscheidungen']
        heute = {e['befund_id']: e for e in ents if e.get('entschieden_am') == '2026-11-05'}
        self.assertEqual(len(heute), 47)
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                self.assertIn(b['id'], heute, f'Befund {b["id"]} nicht im Ledger vom 05.11.')
                e = heute[b['id']]
                self.assertEqual(e['geprueft_fassung'], b['geprueft_fassung'])
                self.assertGreaterEqual(len(e['begruendung']), 20,
                                        f'Begründung zu kurz für {b["id"]}')

    def test_faktencheck_datum_schliesst_keinen_befund(self):
        """Ein neuer faktencheck-Datum schließt per se keinen F4-Befund (F4 ≠ F1)."""
        reg = register()
        cache = {}
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                if b['artikel'] not in cache:
                    cache[b['artikel']] = read(b['artikel'])[0]
                fm = cache[b['artikel']]
                self.assertIsNotNone(fm.get('faktencheck'),
                                     f'Artikel {b["artikel"]} ohne faktencheck-Datum')


if __name__ == '__main__':
    unittest.main()
