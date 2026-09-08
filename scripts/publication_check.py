#!/usr/bin/env python3
"""Delivery SLO: source is not a delivery receipt. UTC cadence, matching workflows."""
import argparse
import datetime as dt
import json
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
    while today.weekday() not in cg.PUBLICATION_DAYS:
        today -= dt.timedelta(days=1)
    return today


def public_article(slug, opener=urllib.request.urlopen):
    url = f'{BASE}/posts/{slug}/'
    req = urllib.request.Request(url, headers={'User-Agent': 'FFC-Publication-Watch/1.0', 'Cache-Control': 'no-cache'})
    with opener(req, timeout=30) as response:
        html = response.read().decode('utf-8')
        # Reject redirects to home/error pages and soft 404s.
        parser = ArticleHTML()
        parser.feed(html)
        return response.status == 200 and response.url.rstrip('/') == url.rstrip('/') and parser.found


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
    return {'day': str(day), 'mode': 'public' if online else 'source',
            'minimum': minimum, 'maximum': maximum, 'source': slugs,
            'delivered': delivered, 'errors': errors,
            'ok': minimum <= len(delivered) <= maximum and not errors}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--online', action='store_true')
    ap.add_argument('--attempts', type=int, default=1)
    ap.add_argument('--delay', type=int, default=60)
    ap.add_argument('--report', default='tmp/publication-receipt.json')
    args = ap.parse_args()
    # Pin the target across retries/midnight; never backdate content.
    day = expected_day(dt.datetime.now(dt.timezone.utc).date())
    for attempt in range(max(1, args.attempts)):
        result = check(day, args.online)
        print(json.dumps(result, ensure_ascii=False))
        if result['ok']:
            break
        if attempt + 1 < args.attempts:
            time.sleep(args.delay)
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
