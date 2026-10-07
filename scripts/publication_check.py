#!/usr/bin/env python3
"""Delivery SLO: source is not a delivery receipt. UTC cadence, matching workflows.

WF-7C1F #611 (07.10.2026) – die Klasse geht dem Kanal vor:
`ok` ist die Summe zweier Wahrheiten mit zwei Besitzern. Am 05./06.10.2026 hat
die Site vollständig ausgeliefert (delivered == source, keine Fehler), aber die
Quelle trug den Montag nur mit 1/2 LIVE. Die SLO fiel damit ehrlich rot – und
das zentrale Fehler-Alerting legte, weil der Lauf keine Klasse nannte, das
generische Wartungs-Issue #611 mit API-Key-Runbook an, obwohl der Fachkanal
`engine-deficit` für genau diesen Zustand längst existiert. Deshalb trägt der
Beleg jetzt seine Klasse (`klasse()`), und der Workflow antwortet der Klasse
statt dem Sammel-Boolean:

  * `quelle_unter` – der Bestand trägt den Tag nicht (unter dem Mindestziel)
    → Besitzer: Defizit-Wache/Fachkanal `engine-deficit` (Nachfüllung),
  * `quelle_ueber` – der Bestand überfüllt den Tag (über dem Tagesmaximum)
    → Besitzer: Kadenz-Gate (stuft zurück und heilt im nächsten Deploy),
  * `auslieferung`  – der Bestand liegt im Zielband, öffentlich fehlt etwas
    → Besitzer: die Auslieferung selbst (Deploy/CDN, P1-Auslieferungskanal),
  * `unbekannt`     – kein lesbarer Beleg (fail-closed: bleibt laut).

Die Klasse ist additiv: `ok` behält seine Bedeutung (Mindestziel bis
Tagesmaximum öffentlich bestätigt), kein Aufrufer verliert ein Feld.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser

import cadence_guard as cg

BASE = 'https://franksfinanzcheck.de'


class ArticleHTML(HTMLParser):
    found = False

    def handle_starttag(self, tag, attrs):
        if 'post-content' in dict(attrs).get('class', '').split():
            self.found = True


def expected_day(today):
    """Der Tag, den die Auslieferungs-SLO bewertet: jüngster Publikationstag.

    Die Logik liegt seit WF-1F8C #608 in `cadence_guard` – EINE Quelle für
    Kadenz-Endkontrolle, Defizit-Wache und Produktions-Wache. Diese Funktion
    bleibt als Name bestehen (Aufrufer und Tests), entscheidet aber nichts
    mehr selbst: Am 06.10.2026 maßen drei Werkzeuge drei verschiedene Tage,
    und der Alarm über den einen Tag hatte keinen Fachkanal für den anderen.
    """
    return cg.letzter_publikationstag(today)


def public_article(slug, opener=urllib.request.urlopen):
    url = f'{BASE}/posts/{slug}/'
    req = urllib.request.Request(url, headers={'User-Agent': 'FFC-Publication-Watch/1.0', 'Cache-Control': 'no-cache'})
    with opener(req, timeout=30) as response:
        html = response.read().decode('utf-8')
        # Reject redirects to home/error pages and soft 404s.
        parser = ArticleHTML()
        parser.feed(html)
        return response.status == 200 and response.url.rstrip('/') == url.rstrip('/') and parser.found


# ===========================================================================
#  KLASSE (WF-7C1F #611, 07.10.2026)
#  ---------------------------------------------------------------------------
#  Warum: Am 06.10.2026 lief „Publication Delivery“ zweimal rot. Der Beleg
#  sprach für sich selbst – `source: 1`, `delivered: 1`, `errors: []`: Die
#  Auslieferung war vollständig, die Quelle trug den gemessenen Montag
#  (05.10.) nur mit 1/2 LIVE. Der rote Lauf konnte diesen Tag nicht heilen
#  (Nachtragen von Inhalten ist verboten), und weil der Lauf die Ursache nicht
#  benannte, legte das zentrale Fehler-Alerting das generische Wartungs-Issue
#  #611 mit API-Key-/Transient-Runbook an – eine Meldung an den falschen
#  Besitzer. Es ist dieselbe Klasse wie #602/#608 für die Kadenz-Endkontrolle,
#  nur beim zweiten Melder derselben Sache: Die Auslieferungs-SLO.
#
#  Die Aufteilung nutzt eine Eigenschaft des Belegs: `delivered` ist immer eine
#  Teilmenge von `source`. Liegt `source` außerhalb des Zielbands
#  (Mindestziel..Tagesmaximum), kann die Auslieferung den Tag gar nicht
#  bestätigen – dann ist der BESTAND der Fall. Liegt `source` im Band, kann
#  jede Abweichung (fehlende Slugs, Sitemap-Fehler) nur von der Auslieferung
#  kommen. Diese Zweiteilung ist vollständig und überschneidungsfrei.
# ===========================================================================
KLASSE_OK = 'ok'
KLASSE_QUELLE_UNTER = 'quelle_unter'
KLASSE_QUELLE_UEBER = 'quelle_ueber'
KLASSE_AUSLIEFERUNG = 'auslieferung'
KLASSE_UNBEKANNT = 'unbekannt'

KLASSEN = (KLASSE_OK, KLASSE_QUELLE_UNTER, KLASSE_QUELLE_UEBER,
           KLASSE_AUSLIEFERUNG, KLASSE_UNBEKANNT)


def klasse(result):
    """Wem gehört ein nicht bestätigter Tag? (reine Funktion, fail-closed)

    Reihenfolge: `ok` zuerst (ein bestätigter Tag hat keine Klasse nötig),
    danach das Bestandsband, zuletzt die Auslieferung. Ein fehlender oder
    unlesbarer Beleg ist `unbekannt` – und unbekannt ist niemals still.
    """
    if not isinstance(result, dict) or 'ok' not in result:
        return KLASSE_UNBEKANNT
    if result.get('ok'):
        return KLASSE_OK
    try:
        n = len(result.get('source') or [])
        minimum = int(result.get('minimum'))
        maximum = int(result.get('maximum'))
    except (TypeError, ValueError):
        return KLASSE_UNBEKANNT
    if n < minimum:
        return KLASSE_QUELLE_UNTER
    if n > maximum:
        return KLASSE_QUELLE_UEBER
    return KLASSE_AUSLIEFERUNG


def klasse_aus_beleg(report='tmp/publication-receipt.json'):
    """Klasse des gespeicherten Belegs – ohne Netz, ohne Schreiben.

    Rückgabe: (klasse, meldung). Ein fehlender/unlesbarer Beleg liefert
    `unbekannt` samt Meldung; der Aufrufer entscheidet laut, nie still.
    """
    pfad = Path(report)
    try:
        daten = json.loads(pfad.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return KLASSE_UNBEKANNT, (f'Kein lesbarer Beleg unter {pfad} '
                                  f'({exc.__class__.__name__}) – fail-closed: '
                                  'ohne Beleg keine Klasse.')
    return klasse(daten), ''


# WF-54C4 #610 (07.10.2026): Ein Beleg gehört seinem Tag.
# Die Auslieferungs-SLO misst den jüngsten Publikationstag. Der generische
# Beleg `tmp/publication-receipt.json` wird aber bei JEDEM Lauf überschrieben –
# ein Issue über den 05.10. wurde so später mit dem Beleg des 07.10.
# geschlossen. Deshalb: tagesgenauer Beleg unter
# `tmp/publication-receipt-<tag>.json` UND eine versionierte Zeile in
# `data/publication-delivery-history.jsonl` – der Fehltag eines vergangenen
# Publikationstages darf nicht mit dem Lauf verschwinden.
HISTORY = Path('data/publication-delivery-history.jsonl')


def beleg_schreiben(result, report='tmp/publication-receipt.json'):
    """Schreibt Beleg (generisch + tagesgenau) und die versionierte Historie.

    WF-7C1F #611: Jeder Beleg trägt seine Klasse. Gibt ein Aufrufer sie nicht
    mit, wird sie nachgerechnet – ein Beleg ohne Klasse wäre ein Beleg, den der
    Workflow nicht zuordnen kann (`--klasse` meldete dann fail-closed laut).
    """
    daten = dict(result)
    daten['klasse'] = daten.get('klasse') or klasse(daten)
    pfad = Path(report)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(daten, ensure_ascii=False, indent=2) + '\n'
    pfad.write_text(text, encoding='utf-8')
    tagespfad = pfad.with_name(f"{pfad.stem}-{daten['day']}{pfad.suffix}")
    tagespfad.write_text(text, encoding='utf-8')
    zeile = json.dumps({
        'ts': dt.datetime.now(dt.timezone.utc).isoformat(),
        'day': daten['day'],
        'mode': daten['mode'],
        'minimum': daten['minimum'],
        'maximum': daten['maximum'],
        'source': len(daten['source']),
        'delivered': len(daten['delivered']),
        'ok': bool(daten['ok']),
        # WF-7C1F #611: Die Klasse gehört in die Historie – sonst lässt sich
        # ein roter Tag später nicht mehr seinem Besitzer zuordnen.
        'klasse': daten['klasse'],
        'errors': daten.get('errors') or [],
    }, ensure_ascii=False)
    try:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open('a', encoding='utf-8') as fh:
            fh.write(zeile + '\n')
    except OSError as exc:  # Historie ist Beweis, kein Gate
        print(f'⚠ Auslieferungs-Historie nicht schreibbar: {exc}')
    return pfad, tagespfad


def check(day, online=False, posts_dir=None):
    minimum, maximum = cg.effective_limits()
    posts = cg.published_on(cg.load_posts(posts_dir), day)
    slugs = sorted(p['slug'] for p in posts)
    delivered, errors = [], []
    if online:
        try:
            req = urllib.request.Request(BASE + '/sitemap.xml', headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=30) as response:
                root = ET.fromstring(response.read())
            urls = {node.text for node in root.iter() if node.tag.endswith('}loc') or node.tag == 'loc'}
            for slug in slugs:
                try:
                    if f'{BASE}/posts/{slug}/' in urls and public_article(slug):
                        delivered.append(slug)
                except Exception as exc:
                    errors.append(f'{slug}: {exc}')
        except Exception as exc:
            errors.append(f'sitemap: {exc}')
    else:
        delivered = slugs
    result = {'day': str(day), 'mode': 'public' if online else 'source',
              'minimum': minimum, 'maximum': maximum, 'source': slugs,
              'delivered': delivered, 'errors': errors,
              'ok': minimum <= len(delivered) <= maximum and not errors}
    result['klasse'] = klasse(result)
    return result


def besitzer(kls):
    """Wer einen roten Tag heilt – dieselbe Zuordnung wie im Workflow."""
    return {
        KLASSE_OK: 'keiner – der Tag ist bestätigt',
        KLASSE_QUELLE_UNTER: 'Fachkanal engine-deficit (Nachfüllung)',
        KLASSE_QUELLE_UEBER: 'Kadenz-Gate (Zurückstufung im Deploy)',
        KLASSE_AUSLIEFERUNG: 'Auslieferung selbst (Deploy/CDN, P1-Kanal)',
        KLASSE_UNBEKANNT: 'unbekannt – fail-closed laut (kein Beleg)',
    }.get(kls, 'unbekannt – fail-closed laut')


def _selftest():
    """Logik-Beweis der Klasse – ohne Netz, ohne Repo-Schreiben, uhrfest.

    Läuft automatisch im Qualitäts-Gate (scripts/selftest_runner.py entdeckt
    jedes Skript mit echtem `--selftest`) und zusätzlich unter der um 97 und
    1461 Tage vorgestellten Uhr: Der Beweis darf an keinem Kalendertag kippen.
    Beleg und Historie werden in ein temporäres Verzeichnis geschrieben –
    ein Prüf-Aufruf heilt nicht und fabriziert keine Beweise (C15/C27).
    """
    import tempfile

    fehler = []

    def pruefe(name, ist, soll):
        if ist != soll:
            fehler.append(f'{name}: {ist!r} statt {soll!r}')

    # 1) Die Klasse: `ok` zuerst, Band links/rechts, Auslieferung im Band,
    #    fehlende/kaputte Belege fail-closed.
    pruefe('ok', klasse({'ok': True, 'source': ['a', 'b'],
                         'minimum': 2, 'maximum': 3}), KLASSE_OK)
    pruefe('ok-vor-band', klasse({'ok': True, 'source': [],
                                  'minimum': 2, 'maximum': 3}), KLASSE_OK)
    pruefe('quelle_unter', klasse({'ok': False, 'source': ['a'],
                                   'minimum': 2, 'maximum': 3}),
           KLASSE_QUELLE_UNTER)
    pruefe('quelle_ueber', klasse({'ok': False, 'source': ['a', 'b', 'c', 'd'],
                                   'minimum': 2, 'maximum': 3}),
           KLASSE_QUELLE_UEBER)
    pruefe('auslieferung', klasse({'ok': False, 'source': ['a', 'b'],
                                   'minimum': 2, 'maximum': 3}),
           KLASSE_AUSLIEFERUNG)
    for kaputt in (None, {}, {'ok': False}, {'ok': False, 'source': ['a'],
                                             'minimum': 'x', 'maximum': 3},
                   'kaputt'):
        pruefe(f'unbekannt({kaputt!r})', klasse(kaputt), KLASSE_UNBEKANNT)

    # 2) Der Lesepfad: ein fehlender Beleg ist laut, nie still.
    kls, meldung = klasse_aus_beleg('/gibt-es-nicht/publication-receipt.json')
    pruefe('beleg-fehlt-klasse', kls, KLASSE_UNBEKANNT)
    pruefe('beleg-fehlt-meldung', bool(meldung), True)

    # 3) Beleg + Historie: die Klasse gehört in beide (Besitzer-Zuordnung).
    with tempfile.TemporaryDirectory() as tmp:
        alt_historie = HISTORY
        try:
            globals()['HISTORY'] = Path(tmp) / 'historie.jsonl'
            roh = {'day': '2026-10-05', 'mode': 'public', 'minimum': 2,
                   'maximum': 3, 'source': ['a'], 'delivered': ['a'],
                   'errors': [], 'ok': False}
            pfad, tagespfad = beleg_schreiben(dict(roh),
                                              report=f'{tmp}/receipt.json')
            gelesen = json.loads(Path(pfad).read_text(encoding='utf-8'))
            pruefe('beleg-klasse', gelesen.get('klasse'), KLASSE_QUELLE_UNTER)
            pruefe('tagesbeleg-existent', Path(tagespfad).exists(), True)
            zeile = json.loads(
                Path(globals()['HISTORY']).read_text(
                    encoding='utf-8').strip().splitlines()[-1])
            pruefe('historie-klasse', zeile.get('klasse'), KLASSE_QUELLE_UNTER)
            pruefe('beleg-lesen', klasse_aus_beleg(str(pfad))[0],
                   KLASSE_QUELLE_UNTER)
        finally:
            globals()['HISTORY'] = alt_historie

    # 4) Die Zuordnung nennt dieselben Besitzer wie der Workflow.
    pruefe('besitzer-unter', 'engine-deficit' in besitzer(KLASSE_QUELLE_UNTER),
           True)
    pruefe('besitzer-ueber', 'Kadenz' in besitzer(KLASSE_QUELLE_UEBER), True)
    pruefe('besitzer-auslieferung',
           'P1' in besitzer(KLASSE_AUSLIEFERUNG), True)

    if fehler:
        for f in fehler:
            print(f'❌ publication_check-Selbsttest: {f}')
        return 1
    print('✅ publication_check-Selbsttest grün (Klasse, fail-closed, Beleg + '
          'Historie; ohne Netz, ohne Repo-Schreiben).')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--online', action='store_true')
    ap.add_argument('--attempts', type=int, default=1)
    ap.add_argument('--delay', type=int, default=60)
    ap.add_argument('--report', default='tmp/publication-receipt.json')
    ap.add_argument('--klasse', action='store_true',
                    help='nur die Klasse des vorhandenen Belegs ausgeben '
                         '(kein Netz, kein Schreiben); Exit 2 = kein Beleg')
    ap.add_argument('--selftest', action='store_true',
                    help='Logik-Beweis (Klasse, Beleg, Historie) – ohne Netz, '
                         'ohne Repo-Schreiben')
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.klasse:
        kls, meldung = klasse_aus_beleg(args.report)
        if meldung:
            print(f'⚠ {meldung}', file=sys.stderr)
        print(kls)
        return 0 if kls != KLASSE_UNBEKANNT else 2
    # Pin the target across retries/midnight; never backdate content.
    day = expected_day(dt.datetime.now(dt.timezone.utc).date())
    for attempt in range(max(1, args.attempts)):
        result = check(day, args.online)
        print(json.dumps(result, ensure_ascii=False))
        if result['ok']:
            break
        if attempt + 1 < args.attempts:
            time.sleep(args.delay)
    path, tagespfad = beleg_schreiben(result, args.report)
    print(f'Beleg: {path} · tagesgenau: {tagespfad} · '
          f'Historie: {HISTORY}')
    print(f'Auslieferungsklasse: {result["klasse"]} · '
          f'Besitzer: {besitzer(result["klasse"])}')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
