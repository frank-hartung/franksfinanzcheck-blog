"""Offline-Regression für die redaktionelle Heilung von Issue #1072.

Stand 12.11.2026 (zweite Runde). Geprüft werden Bedeutungs-Invarianten,
Beleg-Urls und die Registerbindung, keine starren Formulierungen
(Lehre aus #763/#823). Nummerierung wie im Register
`data/faktenfrische_befunde_1072.yaml`.

Dauerhaftigkeit heißt hier viererlei:
  1. Die 47 beanstandeten Aussagen dürfen behauptend nie zurückkehren –
     auch nicht auf den Meta-Flächen. Genau dort saß der Rückfall vom
     11.11.2026: `description` und `pin_description` behaupteten weiter
     „senkt deine Fixkosten“, während der Body längst gedämpft war. Eine
     Prüfung nur über den Body hätte ihn nie gesehen.
  2. Jeder Befund trägt Bedeutungsanker im aktuellen Text. Der Anker ist
     die Invariante, der Hash ist die Provenienz: `geprueft_fassung` hält
     fest, welche Fassung der Mensch gelesen hat. Verschiebt ein Umbau den
     Satz, wird der Anker rot – dann wird der Befund neu entschieden und
     die Runde im Register dokumentiert. Stilles Weiterlaufen gibt es nicht.
  3. Die jüngste Runde (`stand`) ist am heutigen Text gefasst: Für jeden an
     diesem Tag entschiedenen Befund muss `geprueft_fassung` exakt dem
     aktuellen Aussage-Hash entsprechen. Ältere Runden bleiben als
     dokumentierte Historie gebunden und werden nicht rückwirkend
     umgeschrieben.
  4. Gate-Parität: `beleg_url` stammt aus der Allowlist, steht wörtlich in
     den Artikelquellen und ist bei `belegtyp: streichung` `null`; Register
     und Ledger-Kette stimmen überein.

Kein Ersatz für eine Fachprüfung: Rückfall-Schutz, kein Wahrheitsbeweis.
"""
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

META_FELDER = ('title', 'description', 'kurzantwort', 'pin_title', 'pin_description')
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


def read_raw(slug):
    """Roh-Frontmatter (Hash-Form des Ledgers) und Body."""
    text = (resolve(slug) / 'index.md').read_text(encoding='utf-8')
    _, fm, body = text.split('---', 2)
    return fm, body


def read(slug):
    fm, body = read_raw(slug)
    return yaml.safe_load(fm), body


def register():
    return yaml.safe_load(REGISTER.read_text(encoding='utf-8'))


def ledger():
    return yaml.safe_load(ENTSCHEIDUNGEN.read_text(encoding='utf-8'))['entscheidungen']


def allowlist_domains():
    data = yaml.safe_load(ALLOWLIST.read_text(encoding='utf-8'))
    return [q['domain'] for q in data['quellen_allowlist']]


def meta_flaeche(fm):
    return ' '.join(str(fm.get(k, '')) for k in META_FELDER)


class Faktenfrische1072RegisterTests(unittest.TestCase):
    """Register-Struktur und -Konsistenz mit Ledger/Queue."""

    def test_register_issue_und_stand(self):
        reg = register()
        self.assertEqual(reg['issue'], 1072)
        self.assertRegex(str(reg['stand']), r'^\d{4}-\d{2}-\d{2}$')
        self.assertGreaterEqual(str(reg['stand']), '2026-11-05',
                                'Der Registerstand darf nicht zurückfallen.')
        self.assertTrue(str(reg['lauf']).startswith(str(reg['stand'])),
                        'Lauf und Stand müssen denselben Tag nennen.')
        runden = reg['runden']
        self.assertGreaterEqual(len(runden), 2,
                                'Beide Runden müssen dokumentiert bleiben.')
        for runde in runden:
            with self.subTest(stand=runde.get('stand')):
                self.assertRegex(str(runde['stand']), r'^\d{4}-\d{2}-\d{2}$')
                self.assertGreaterEqual(len(runde['umfang']), 20,
                                        'Runde ohne belastbare Beschreibung.')
        self.assertEqual(str(runden[-1]['stand']), str(reg['stand']),
                         'Die jüngste Runde trägt den Registerstand.')

    def test_register_enthaelt_alle_47_befunde(self):
        reg = register()
        befunde = reg['befunde']
        self.assertEqual(len(befunde), 47)
        for b in befunde:
            with self.subTest(befund=b['id']):
                self.assertEqual(b['status'], 'behoben')
                self.assertTrue(b['entschieden_von'])
                self.assertIn(b['entschieden_am'], [str(r['stand']) for r in reg['runden']],
                              f'Befund {b["id"]} gehört zu keiner dokumentierten Runde.')
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
                    cache[b['artikel']] = norm(meta_flaeche(fm) + ' ' + body)
                joined = cache[b['artikel']]
                for anker in b['anker']:
                    self.assertIn(
                        norm(anker), joined,
                        f'Anker fehlt: {anker!r} ({b["id"]}). Der Text wurde nach der '
                        f'Entscheidung vom {b["entschieden_am"]} geändert – Befund neu '
                        f'entscheiden (Register + Ledger), Anker an die heutige Fassung binden.')

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

    def test_verbote_gelten_auch_auf_den_meta_flaechen(self):
        """Lehre vom 12.11.2026: Der Rückfall saß in `description` und `pin_description`.

        Solange nur der Body geprüft wird, kann eine Behauptung in den
        Werbeflächen überleben und über Pinterest und Suchergebnis wirken.
        """
        reg = register()
        cache = {}
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                if b['artikel'] not in cache:
                    cache[b['artikel']] = meta_flaeche(read(b['artikel'])[0])
                meta = cache[b['artikel']]
                for verboten in b.get('verboten_behauptend') or []:
                    self.assertFalse(behauptend(meta, verboten),
                                     f'Fehlbehauptung auf einer Meta-Fläche: {verboten!r} '
                                     f'({b["id"]})')

    def test_fixkosten_versprechen_bleibt_moeglichkeitsform(self):
        """Der konkrete Rückfall vom 11.11.2026, formunabhängig gesperrt."""
        muster = re.compile(
            r'(?:beladen|befüllen)\s+senkt\s+(?:dir\s+)?(?:deine\s+)?fixkosten'
            r'|senkt\s+die\s+betriebskosten[^.]{0,40}nachhaltig')
        for slug in ('2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang',):
            fm, body = read(slug)
            with self.subTest(slug=slug):
                for feld in ('description', 'pin_description'):
                    self.assertNotRegex(norm(fm[feld]), muster,
                                        f'{feld} behauptet weiter einen Fixkosten-Effekt.')
                self.assertNotRegex(norm(body), muster,
                                    'Body behauptet weiter einen Fixkosten-Effekt.')

    def test_beleg_url_auf_allowlist_und_in_artikelquellen(self):
        """Beleg-Parität ohne Ausnahme: beleglos ist nur die Streichung.

        Die frühere Fassung übersprang die Quellenprüfung, wenn ein Artikel
        gar kein `quellen`-Verzeichnis hatte – dort stand der Beleg dann
        nirgends. Genau so blieben die Reise-Befunde scheinbar gedeckt.
        """
        domains = allowlist_domains()
        reg = register()
        cache = {}
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                self.assertIn(b.get('belegtyp'), ('ergaenzt', 'streichung'),
                              f'Unbekannter Belegtyp bei {b["id"]}')
                if b['beleg_url'] is None:
                    self.assertEqual(b['belegtyp'], 'streichung',
                                     'Beleglos ist nur eine Streichung zulässig.')
                    continue
                self.assertTrue(b['beleg_url'].startswith('https://'),
                                f'Beleg-Url nicht https: {b["beleg_url"]}')
                self.assertTrue(any(b['beleg_url'].split('/')[2].endswith(d)
                                    for d in domains),
                                f'Beleg nicht auf der Allowlist: {b["beleg_url"]}')
                if b['artikel'] not in cache:
                    cache[b['artikel']] = read(b['artikel'])[0]
                fm = cache[b['artikel']]
                quellen = [q['url'] for q in (fm.get('quellen') or [])]
                self.assertIn(b['beleg_url'], quellen,
                              f'Beleg steht nicht in den Artikelquellen: {b["beleg_url"]}')

    def test_runden_sind_belegt_und_die_neue_runde_am_heute_text(self):
        """Stand ≥ 05.11., jede Runde dokumentiert, die jüngste am heutigen Text."""
        import faktenfrische_befund_ledger as ledger_mod
        reg = register()
        stand = str(reg['stand'])
        runden = [str(r['stand']) for r in reg['runden']]
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                self.assertIn(b['entschieden_am'], runden,
                              f'Befund {b["id"]} nicht an eine Runde gebunden.')
                self.assertRegex(b['geprueft_fassung'], r'^[0-9a-f]{64}$',
                                 f'geprueft_fassung ist kein SHA-256: {b["geprueft_fassung"]}')
                if b['entschieden_am'] != stand:
                    continue
                fm, body = read_raw(b['artikel'])
                projektion = b.get('projektion', 'betrieb-v3')
                self.assertEqual(
                    b['geprueft_fassung'],
                    ledger_mod.text_hash({'fm': fm, 'body': body}, projektion),
                    f'Befund {b["id"]} trägt die Runde vom {stand}, ist aber nicht an '
                    f'die heutige Fassung gebunden (Projektion {projektion}).')

    def test_register_referenziert_entscheidungen_mit_begruendung(self):
        """Jeder Befund hängt an einer Ledger-Kette, der Register-Hash stammt daraus.

        Die Kette umfasst alle Einträge eines Befunds und alle dort genannten
        Fassungen (`geprueft_fassung`, `ursprungs_geprueft_fassung`,
        `vorgaenger_geprueft_fassung`, `befund_fassung`). Damit kann das
        Register keinen Hash erfinden, und eine Umbindung bleibt als
        Provenienz sichtbar, statt den Beweis zu überschreiben.
        """
        reg = register()
        kette = {}
        runden = {}
        for e in ledger():
            felder = ('geprueft_fassung', 'ursprungs_geprueft_fassung',
                      'vorgaenger_geprueft_fassung', 'befund_fassung')
            kette.setdefault(e['befund_id'], set()).update(
                e[f] for f in felder if e.get(f))
            runden.setdefault(e['befund_id'], {})[e['entschieden_am']] = e
        for b in reg['befunde']:
            with self.subTest(befund=b['id']):
                self.assertIn(b['id'], kette,
                              f'Befund {b["id"]} fehlt im Ledger.')
                self.assertIn(b['geprueft_fassung'], kette[b['id']],
                              f'Befund {b["id"]}: geprueft_fassung stammt aus keiner '
                              f'dokumentierten Ledger-Fassung.')
                runde = runden[b['id']].get(b['entschieden_am'])
                self.assertIsNotNone(runde,
                                     f'Befund {b["id"]} hat keine Ledger-Entscheidung '
                                     f'vom {b["entschieden_am"]}.')
                self.assertGreaterEqual(len(runde['begruendung']), 20,
                                        f'Begründung zu kurz für {b["id"]}')
                # Ältere Runden wurden am 07.11.2026 auf die feinere Projektion
                # umgebunden; dort hält das Register den Wert, den der Mensch
                # gelesen hat (`ursprungs_geprueft_fassung`). Für die jüngste
                # Runde müssen Register und Ledger dagegen dieselbe Fassung
                # nennen – sonst wäre sie keine Entscheidung am heutigen Text.
                if b['entschieden_am'] == str(reg['stand']):
                    self.assertEqual(runde['geprueft_fassung'], b['geprueft_fassung'],
                                     f'Register und Ledger nennen für {b["id"]} '
                                     f'verschiedene Fassungen der Runde '
                                     f'{b["entschieden_am"]}.')

    def test_beschreibungsaenderung_oeffnet_die_entscheidung(self):
        """Systemischer Schutz für Paket B: Meta-Flächen gehören zum Hash."""
        import faktenfrische_befund_ledger as ledger_mod
        basis = {'fm': 'title: "T"\ndescription: "harmlos"\npin_description: "harmlos"\n',
                 'body': 'Text'}
        geaendert = {'fm': 'title: "T"\ndescription: "senkt deine Fixkosten"\n'
                           'pin_description: "harmlos"\n',
                     'body': 'Text'}
        self.assertNotEqual(ledger_mod.text_hash(basis),
                            ledger_mod.text_hash(geaendert))

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
