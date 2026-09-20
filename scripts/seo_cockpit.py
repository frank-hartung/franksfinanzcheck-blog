#!/usr/bin/env python3
"""Kostenloser, rein lokaler SEO-Audit des Hugo-Builds (Python-Standardbibliothek).

Kein Netzwerk, keine Accounts, keine Content-Änderungen. Ausgabe ist ein
privates Werkzeug in .cache/seo-cockpit/, KEIN Bestandteil des Blog-Deploys.
Exit: 0 erfolgreich, 1 bei --strict und P1-Funden, 2 bei Eingabefehlern.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
from datetime import datetime, timezone
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    """Struktureller Parser: funktioniert auch mit Hugos unquoted/minified HTML."""
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.meta = defaultdict(list)
        self.canonicals = []
        self.links = set()
        self.ids = set()
        self.images = []
        self.headings = Counter()
        self.schemas = []
        self.schema_errors = 0
        self.redirect = False
        self.lang = ''
        self.in_title = False
        self.in_schema = False
        self.schema_text = []
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'html':
            self.lang = a.get('lang', '')
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            key = (a.get('name') or a.get('property') or '').lower()
            self.meta[key].append(a.get('content') or '')
            if (a.get('http-equiv') or '').lower() == 'refresh':
                self.redirect = True
        if tag == 'link' and 'canonical' in (a.get('rel') or '').split():
            self.canonicals.append(a.get('href') or '')
        if tag == 'a' and a.get('href'):
            self.links.add(a['href'])
        if tag == 'img':
            self.images.append(a)
        if tag in ('h1', 'h2', 'h3'):
            self.headings[tag] += 1
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.in_schema = True
            self.schema_text = []

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script' and self.in_schema:
            try:
                self.schemas.append(json.loads(''.join(self.schema_text)))
            except ValueError:
                self.schema_errors += 1
            self.in_schema = False

    def handle_data(self, value):
        if self.in_title:
            self.title_parts.append(value)
        if self.in_schema:
            self.schema_text.append(value)

    @property
    def title(self):
        return re.sub(r'\s+', ' ', ''.join(self.title_parts)).strip()

    @property
    def noindex(self):
        return any('noindex' in v.lower() for v in self.meta['robots'])


def local_file(build: Path, url: str, base: str) -> Path | None:
    """Exakte Origin-Prüfung; niemals außerhalb des Build-Verzeichnisses lesen."""
    parts, origin = urlsplit(url), urlsplit(base)
    if (parts.scheme, parts.netloc) != (origin.scheme, origin.netloc):
        return None
    relative = unquote(parts.path).lstrip('/')
    target = (build / relative).resolve()
    if not target.is_relative_to(build.resolve()):
        return None
    if target.is_dir() or not target.suffix:
        target /= 'index.html'
    return target


def schema_types(value):
    result = set()
    if isinstance(value, dict):
        types = value.get('@type', [])
        result.update([types] if isinstance(types, str) else [t for t in types if isinstance(t, str)] if isinstance(types, list) else [])
        for child in value.values():
            result.update(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            result.update(schema_types(child))
    return result


def audit(build: Path, base: str) -> dict:
    build = build.resolve()
    if not (build / 'index.html').is_file() or not (build / 'sitemap.xml').is_file():
        raise ValueError('Build unvollständig: zuerst hugo --minify --cleanDestinationDir ausführen.')
    if urlsplit(base).scheme != 'https' or not urlsplit(base).netloc:
        raise ValueError('baseURL muss eine absolute HTTPS-Adresse sein.')
    base = base.rstrip('/') + '/'
    docs, urls = {}, {}
    for path in sorted(build.rglob('*.html')):
        # Eigenständige Verifikations-/OAuth-Dateien sind keine Blogseiten.
        if path.name not in ('index.html', '404.html') or (ROOT / 'static' / path.relative_to(build)).is_file():
            continue
        doc = Document(path.read_text(encoding='utf-8'))
        if doc.redirect:
            continue
        rel = '/' + path.relative_to(build).as_posix()
        if rel.endswith('index.html'):
            rel = rel[:-10]
        docs[rel] = doc
        urls[path] = rel
    sitemap = ET.parse(build / 'sitemap.xml')
    locations = [node.text or '' for node in sitemap.findall('.//{*}loc')]
    findings, pages = [], []

    def add(url, code, severity, detail, action, owner='human'):
        findings.append(dict(url=url, code=code, severity=severity, detail=detail,
                             action=action, owner=owner, channel='seo-cockpit'))

    for value, count in Counter(locations).items():
        if count > 1:
            add('/sitemap.xml', 'sitemap-duplicate', 'P2', value, 'Doppelte URL aus der Sitemap entfernen.')
    for value in locations:
        path = local_file(build, value, base)
        rel = urls.get(path)
        if rel is None or docs[rel].noindex:
            add('/sitemap.xml', 'sitemap-target', 'P1', value,
                'Nur existierende, indexierbare Originalseiten in die Sitemap aufnehmen.')
        elif docs[rel].canonicals != [value]:
            add(rel, 'sitemap-canonical', 'P1', value,
                'Sitemap und Canonical müssen auf dieselbe Original-URL verweisen.')

    incoming = defaultdict(set)
    graph = defaultdict(set)
    for rel, doc in docs.items():
        url = urljoin(base, rel)
        pager = bool(re.search(r'/page/\d+/$', rel))
        if (pager or rel.startswith(('/tags/', '/categories/')) or rel == '/404.html') and not doc.noindex:
            add(rel, 'index-control', 'P1', 'Archiv/Folgeseite/404 ist indexierbar.', 'noindex im gerenderten Head setzen.')
        if len(doc.canonicals) != 1:
            add(rel, 'canonical-count', 'P1', f'{len(doc.canonicals)} Canonicals', 'Genau ein Canonical ausgeben.')
        else:
            target = local_file(build, doc.canonicals[0], base)
            if target is None or not target.is_file():
                add(rel, 'canonical-target', 'P1', doc.canonicals[0], 'Erreichbare HTTPS-Originaladresse verwenden.')
            if pager and doc.canonicals[0] != url:
                add(rel, 'pager-canonical', 'P2', doc.canonicals[0], 'Folgeseite mit eigener Canonical-URL auszeichnen.')
        if doc.schema_errors:
            add(rel, 'schema-json', 'P1', 'Ungültiges JSON-LD', 'JSON-LD sicher serialisieren und erneut prüfen.')
        indexable = not doc.noindex and rel != '/404.html'
        if indexable:
            if url not in locations:
                add(rel, 'sitemap-missing', 'P2', 'Indexierbare Seite fehlt in Sitemap.', 'Sitemap-Aufnahme redaktionell prüfen.', 'human')
            if not doc.title:
                add(rel, 'title-missing', 'P1', 'Seitentitel fehlt.', 'Aussagekräftigen, individuellen Title setzen.')
            elif not 25 <= len(doc.title) <= 65:
                add(rel, 'title-length', 'P3', f'{len(doc.title)} Zeichen', 'Snippet-Vorschau prüfen; Zeichenlängen sind Richtwerte, kein Rankingfaktor.', 'human')
            descriptions = doc.meta['description']
            if len(descriptions) != 1 or not descriptions[0].strip():
                add(rel, 'description-missing', 'P2', 'Description fehlt oder ist mehrfach vorhanden.', 'Eine individuelle Meta-Description setzen.')
            elif not 70 <= len(descriptions[0]) <= 165:
                add(rel, 'description-length', 'P3', f'{len(descriptions[0])} Zeichen', 'Suchintention und Nutzen knapp beschreiben; keine starre Zeichengarantie.', 'human')
            if doc.headings['h1'] != 1:
                add(rel, 'h1-count', 'P2', f'{doc.headings["h1"]} H1-Überschriften', 'Eine klare Hauptüberschrift im sichtbaren Inhalt verwenden.')
            if not doc.lang:
                add(rel, 'language', 'P2', 'HTML-Sprache fehlt.', 'lang="de" am HTML-Element ausgeben.')
            for key in ('og:title', 'og:description', 'og:image', 'twitter:card'):
                if not doc.meta[key]:
                    add(rel, 'social-meta', 'P2', key, 'Social-Metadaten im Template ergänzen.')
        broken, anchors = [], []
        for href in sorted(doc.links):
            absolute = urljoin(url, href)
            dest = local_file(build, absolute, base)
            if dest is None:
                continue
            if not dest.is_file():
                broken.append(href)
                continue
            target = urls.get(dest)
            if target and target != rel:
                incoming[target].add(rel)
                graph[rel].add(target)
            fragment = unquote(urlsplit(absolute).fragment)
            if target and fragment and not fragment.startswith(':~:text=') and fragment not in docs[target].ids:
                anchors.append(href)
        if broken:
            add(rel, 'broken-link', 'P1', '\n'.join(broken), 'Interne Linkziele korrigieren oder wiederherstellen.')
        if anchors:
            add(rel, 'broken-anchor', 'P2', '\n'.join(anchors), 'Anker mit vorhandenen Abschnitts-IDs abgleichen; dynamische IDs manuell prüfen.', 'human')
        missing_alt = sum('alt' not in img for img in doc.images)
        if missing_alt:
            add(rel, 'image-alt', 'P2', f'{missing_alt} Bilder ohne alt-Attribut', 'Informative Alt-Texte ergänzen; dekorative Bilder erhalten alt="".')
        for image in doc.images:
            src = image.get('src')
            target = local_file(build, urljoin(url, src), base) if src else None
            if target is not None and not target.is_file():
                add(rel, 'image-missing', 'P1', src, 'Bildpfad korrigieren.')
        pages.append(dict(path=rel, url=url, title=doc.title, description=next(iter(doc.meta['description']), ''),
                          indexable=indexable, canonical=next(iter(doc.canonicals), ''),
                          in_sitemap=url in locations, h1=doc.headings['h1'], h2=doc.headings['h2'],
                          schema=sorted(schema_types(doc.schemas)), images=len(doc.images)))
    depths, queue = {'/': 0}, deque(['/'])
    while queue:
        current = queue.popleft()
        for target in sorted(graph[current]):
            if target not in depths:
                depths[target] = depths[current] + 1
                queue.append(target)
    for page in pages:
        rel = page['path']
        page.update(incoming=len(incoming[rel]), depth=depths.get(rel))
        if page['indexable'] and rel != '/' and not incoming[rel]:
            add(rel, 'orphan-page', 'P2', 'Keine internen eingehenden Links im Build.', 'Von passender Themenwelt und thematisch verwandten Artikeln verlinken.', 'human')
    for field in ('title', 'description'):
        groups = defaultdict(list)
        for page in pages:
            if page['indexable'] and page[field]:
                groups[page[field].casefold()].append(page['path'])
        for group in groups.values():
            if len(group) > 1:
                for rel in group:
                    add(rel, f'duplicate-{field}', 'P2', ', '.join(group), 'Individuelle Metadaten nach Suchintention formulieren.', 'human')
    findings.sort(key=lambda x: (x['severity'], x['url'], x['code']))
    counts = Counter(f['severity'] for f in findings)
    for page in pages:
        page['findings'] = sum(f['url'] == page['path'] for f in findings)
    return dict(version=1, generated_at=datetime.now(timezone.utc).isoformat(), base_url=base,
                source='Lokaler Hugo-Build, keine Live- oder Rankingmessung', pages=pages, findings=findings,
                summary=dict(pages=len(pages), indexable=sum(p['indexable'] for p in pages),
                             sitemap=len(locations), p1=counts['P1'], p2=counts['P2'], p3=counts['P3']))


def safe_csv(rows):
    """Spreadsheet-Formeln auch bei extern importierten Metadaten neutralisieren."""
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    for row in rows:
        writer.writerow(["'" + str(v) if str(v).lstrip().startswith(('=', '+', '-', '@')) else v for v in row])
    return stream.getvalue()


def write_report(result: dict, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'tools' / 'seo-cockpit'
    payload = json.dumps(result, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (assets / 'index.html').read_text(encoding='utf-8')
    (output / 'index.html').write_text(template.replace('/*AUDIT_DATA*/', payload), encoding='utf-8')
    for name in ('app.js', 'style.css'):
        shutil.copyfile(assets / name, output / name)
    (output / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    rows = [['Priorität', 'URL', 'Prüfung', 'Befund', 'Maßnahme', 'Besitzer', 'Kanal']]
    rows += [[f[k] for k in ('severity', 'url', 'code', 'detail', 'action', 'owner', 'channel')] for f in result['findings']]
    (output / 'massnahmen.csv').write_text(safe_csv(rows), encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=ROOT / 'public')
    parser.add_argument('--output', type=Path, default=ROOT / '.cache' / 'seo-cockpit')
    parser.add_argument('--strict', action='store_true', help='Exit 1 bei technischen P1-Befunden')
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        for unsafe in ('public', 'static', 'content', 'layouts', '.git'):
            if output.is_relative_to(ROOT / unsafe):
                raise ValueError('SEO-Ausgabe gehört nicht in öffentliche, Inhalts- oder Git-Verzeichnisse.')
        if output.is_relative_to(args.build.resolve()) or args.build.resolve().is_relative_to(output):
            raise ValueError('Build und SEO-Ausgabe dürfen sich nicht überlappen.')
        with (ROOT / 'hugo.toml').open('rb') as f:
            base = tomllib.load(f)['baseURL']
        result = audit(args.build, base)
        write_report(result, output)
    except (OSError, ValueError, ET.ParseError) as error:
        print(f'SEO-Cockpit: {error}', file=sys.stderr)
        return 2
    s = result['summary']
    print(f"SEO-Cockpit: {s['pages']} Seiten, {s['indexable']} indexierbar; P1: {s['p1']}, P2: {s['p2']}, P3: {s['p3']}.")
    print(f"Öffnen: {output / 'index.html'}")
    return 1 if args.strict and s['p1'] else 0


if __name__ == '__main__':
    sys.exit(main())
