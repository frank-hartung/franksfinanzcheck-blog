#!/usr/bin/env python3
"""One stable delivery incident, closed only by a successful public receipt.

Premium-Fix 15.09.2026 (#287): Bei Source-Defizit (LIVE unter Minimum im
Repo) stößt die Recovery zuerst die Kadenz-Endkontrolle an – die füllt über
`publication_release.refill_to_min()` Re-Queue + Reserve nach. Deploy allein
reicht nicht, wenn der Source-Stand schon unter dem Mindestziel liegt.
Bei Source ok / Public defizit (CDN-Lag) bleibt Deploy der richtige Hebel.
"""
import datetime as dt
import json
import os
import subprocess
from pathlib import Path


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def _receipt() -> dict:
    path = Path('tmp/publication-receipt.json')
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001 – Belegtext bleibt roh im Issue
        return {}


def main():
    marker = '<!-- publication-delivery-slo -->'
    issues = json.loads(gh('issue', 'list', '--state', 'open', '--search',
                           'in:title "P1: Öffentliche Artikel-Auslieferung"',
                           '--json', 'number,body'))
    issue = next((i for i in issues if marker in i.get('body', '')), None)
    if os.environ.get('RECEIPT_OK') == 'true':
        if issue:
            gh('issue', 'close', str(issue['number']), '--comment',
               'Öffentlicher Nachweis erfolgreich: Mindestziel in Sitemap und Artikel-HTML bestätigt.')
        return
    path = Path('tmp/publication-receipt.json')
    evidence = path.read_text() if path.exists() else 'Nachweis konnte nicht ausgeführt werden.'
    receipt = _receipt()
    source_n = len(receipt.get('source') or [])
    delivered_n = len(receipt.get('delivered') or [])
    minimum = int(receipt.get('minimum') or 2)
    source_deficit = source_n < minimum
    body = (f'{marker}\n## Auslieferungsziel nicht bestätigt\n\n'
            f'UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}\n\n'
            f'- **Source LIVE:** {source_n}/{minimum}\n'
            f'- **Öffentlich geliefert:** {delivered_n}/{minimum}\n'
            f'- **Diagnose:** '
            + ('Source unter Mindestziel → Kadenz-Endkontrolle füllt nach '
               '(Re-Queue + Reserve). '
               if source_deficit else
               'Source ok, Public defizit → Deploy/CDN-Propagation. ')
            + '\n\n'
            f'```json\n{evidence}\n```\n\n'
            'Runbook: docs/publication-reliability.md. Keine Qualitätsgates umgehen.\n'
            'Reparatur #287: Deploy füllt nach Gate-Verwurf selbst nach; '
            'Endkontrolle bleibt der Tages-Backstop.\n')
    if issue:
        gh('issue', 'edit', str(issue['number']), '--body', body)
    else:
        gh('issue', 'create',
           '--title', 'P1: Öffentliche Artikel-Auslieferung unter Mindestziel',
           '--body', body)
    # Bounded recovery: fixed monitoring slots only; no workflow_run cycle.
    # Source-Defizit → zuerst Endkontrolle (Quote), dann Deploy.
    # Public-only-Defizit → Deploy reicht (CDN/Build).
    now = dt.datetime.now(dt.timezone.utc)
    if source_deficit and now.weekday() in {0, 2, 4}:
        gh('workflow', 'run', 'kadenz-endkontrolle.yml', '--ref', 'main')
    gh('workflow', 'run', 'deploy.yml', '--ref', 'main')
    if (not source_deficit) and now.weekday() in {0, 2, 4}:
        # Public hinkt hinterher: Backstop noch einmal, falls Source
        # zwischenzeitlich durch parallelen Gate-Verwurf gelitten hat.
        gh('workflow', 'run', 'kadenz-endkontrolle.yml', '--ref', 'main')


if __name__ == '__main__':
    main()