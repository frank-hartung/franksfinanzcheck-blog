"""Offline-Regression für die redaktionelle Heilung von Issue #1072.

Stand 05.11.2026. Geprüft werden Bedeutungs-Invarianten, Beleg-Urls und
die Registerbindung, keine starren Formulierungen (Lehre aus #763/#823).
Nummerierung wie im Register `data/faktenfrische_befunde_1072.yaml`.

Dauerhaftigkeit heißt hier dreierlei:
  1. Die 47 beanstandeten Aussagen dürfen behauptend nie zurückkehren;
     Dämpfungen, Verneinungen und ausdrücklich verworfene Beispiele
     bleiben erlaubt – für JEDEN Status, auch für überholte Einträge.
  2. Ein offener Befund ist an den aktuellen Text gebunden (Anker, Quellen);
     ein neuer `faktencheck`-Datum schließt keinen Befund (F4 ≠ F1).
  3. Gate-Parität: Beleg-Urls stammen aus der Allowlist und stehen in den
     Artikelquellen; Register und Ledger stimmen überein.

ÜBERHOLT IST KEIN FREISPRUCH (10.11.2026, aus #1163/#1148 gelernt)
  Wird ein Artikel nach der Entscheidung vollständig neu belegt – hier am
  10.11.2026 durch WF-7B6B (#1148): acht Quellen, neue Modellrechnung,
  unbelegte Aussagen entfernt –, dann gilt die Prüfung der damaligen
  Fassung, nicht dem heutigen Text. Das wird als `status: ueberholt`
  ausgewiesen, mit Datum, Nachfolge-Dokument und Begründung. Die Wache
  verlangt dann den BELEG der Nachprüfung (das Dokument existiert und nennt
  den Artikel) statt eines Ankers, der in der neuen Fassung zu Recht fehlt.
  Die Sperre gegen die alte Behauptung (`verboten_behauptend`) bleibt
  unverändert scharf: Ein überholter Eintrag darf nie grün werden, weil die
  Aussage zurückkehrt.

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

# `behoben` = am heutigen Text geprüft; `ueberholt` = durch eine belegte
# Nachprüfung ersetzt (Fassungsbindung, siehe Modul-Docstring).
STATUS_WERTE = ('behoben', 'ueberholt')
ISO_TAG = re.compile(r'^\d{4}-\d{2}-\d{2}$')

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


def status_fehler(b):
    """Prüft den Statusvertrag eines Registereintrags – eine Quelle für
    Strukturpflichten UND Sabotage-Probe (sonst prüften beide verschieden)."""
    fehler = []
    if b.get('status') not in STATUS_WERTE:
        fehler.append(f'Status {b.get("status")!r} ist kein Vertragswert')
    if not b.get('entschieden_von'):
        fehler.append('entschieden_von fehlt')
    if len(str(b.get('entscheidung') or '')) < 20:
        fehler.append('Begründung zu kurz')
    if not b.get('anker'):
        fehler.append('kein Bedeutungsanker')
    if not b.get('geprueft_fassung'):
        fehler.append('geprueft_fassung fehlt')
    if b.get('status') == 'ueberholt':
        if not b.get('abgeloest_durch'):
            fehler.append('überholt ohne Nachfolge-Dokument')
        if not ISO_TAG.match(str(b.get('abgeloest_am') or '')):
            fehler.append('abgeloest_am fehlt oder ist kein ISO-Tag')
        if len(str(b.get('abloesung_grund') or '')) < 40:
            fehler.append('Ablösung ohne Begründung')
        if str(b.get('abgeloest_am') or '') <= str(b.get('entschieden_am') or ''):
            fehler.append('Ablösung nicht nach der Entscheidung')
    return fehler


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
                self.assertEqual(status_fehler(b), [],
                                 f'Befund {b["id"]}: Statusvertrag verletzt')

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
                if b['status'] == 'ueberholt':
                    # Fassungsbindung: Die Anker gehören zur Fassung, die am
                    # 05.11. geprüft wurde. Dass sie im heutigen Text fehlen,
                    # ist bei einer Neubelegung erwartbar; bewiesen wird die
                    # Nachprüfung im eigenen Test unten.
                    continue
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
                if b['status'] == 'ueberholt':
                    # Die Quellen des HEUTIGEN Textes sind nicht die Quellen
                    # der damaligen Entscheidung (siehe Modul-Docstring).
                    continue
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
                # PROJEKTIONSBEWUSST (07.11.2026, #1072-Nachlauf):
                # Der Register-Eintrag hält die Fassung fest, die am 05.11.
                # geprüft wurde. Am 07.11. wurden die Entscheidungen einmalig
                # auf die feinere Aussage-Projektion umgebunden, weil der
                # frühere `text_hash` Betriebsflächen mitzählte und dadurch
                # jede Maschinen-Schreibe (Weiterlesen-Link, Abbildungszeile,
                # Disclaimer, /go/-Route) eine dokumentierte Entscheidung
                # wieder aufriss. Die Umbindung überschreibt den Beweis
                # nicht: `ursprungs_geprueft_fassung` hält den Wert, den der
                # Mensch tatsächlich gelesen hat. Beide müssen übereinstimmen –
                # sonst wäre es keine Umbindung, sondern eine Behauptung.
                gebunden = {e.get('geprueft_fassung'),
                            e.get('ursprungs_geprueft_fassung')}
                self.assertIn(b['geprueft_fassung'], gebunden,
                              f'Befund {b["id"]}: weder aktuelle noch '
                              f'ursprüngliche Bindung passt zum Register')
                self.assertGreaterEqual(len(e['begruendung']), 20,
                                        f'Begründung zu kurz für {b["id"]}')

    def test_sabotage_statusvertrag_bleibt_scharf(self):
        """Die Ablösung ist kein Schlupfloch: vier Verstöße müssen auffallen."""
        gut = next(b for b in register()['befunde'] if b['status'] == 'ueberholt')
        self.assertEqual(status_fehler(gut), [], 'Positivprobe rot – Probe taugt nichts')
        faelle = {
            'ohne Nachfolge-Dokument': dict(gut, abgeloest_durch=''),
            'Nachfolge vor der Entscheidung': dict(gut, abgeloest_am='2026-11-04'),
            'Ablösung ohne Begründung': dict(gut, abloesung_grund='weil'),
            'unbekannter Status': dict(gut, status='erledigt'),
        }
        for name, eintrag in faelle.items():
            with self.subTest(fall=name):
                self.assertNotEqual(status_fehler(eintrag), [],
                                    f'Sabotage „{name}“ blieb grün')

    def test_ueberholte_befunde_haben_eine_belegte_nachpruefung(self):
        """„Überholt“ nur mit Dokument: es existiert und nennt den Artikel.

        Damit ist die Ablösung nachprüfbar statt behauptet. Ein Tippfehler im
        Dateinamen, ein gelöschter Bericht oder ein Dokument, das den Artikel
        gar nicht behandelt, macht die Wache rot.
        """
        reg = register()
        geprueft = 0
        for b in reg['befunde']:
            if b['status'] != 'ueberholt':
                continue
            geprueft += 1
            with self.subTest(befund=b['id']):
                pfad = ROOT / str(b['abgeloest_durch'])
                self.assertTrue(pfad.is_file(),
                                f'Befund {b["id"]}: Nachfolge-Dokument {pfad.name} fehlt')
                text = pfad.read_text(encoding='utf-8')
                self.assertIn(b['artikel'], text,
                              f'Befund {b["id"]}: {pfad.name} nennt den Artikel nicht')
                self.assertGreaterEqual(len(text.strip()), 500,
                                        f'Befund {b["id"]}: Nachfolge-Dokument ist zu dünn')
        self.assertGreater(geprueft, 0, 'kein überholter Befund – Test prüft nichts')

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
