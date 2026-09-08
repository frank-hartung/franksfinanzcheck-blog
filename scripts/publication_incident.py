#!/usr/bin/env python3
"""One stable delivery incident, closed only by a successful public receipt."""
import datetime as dt
import json
import os
import subprocess
from pathlib import Path


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def main():
    marker = '<!-- publication-delivery-slo -->'
    issues = json.loads(gh('issue', 'list', '--state', 'open', '--search',
                           'in:title "P1: Öffentliche Artikel-Auslieferung"',
                           '--json', 'number,body'))
    issue = next((i for i in issues if marker in i['body']), None)
    if os.environ.get('RECEIPT_OK') == 'true':
        if issue:
            gh('issue', 'close', str(issue['number']), '--comment',
               'Öffentlicher Nachweis erfolgreich: Mindestziel in Sitemap und Artikel-HTML bestätigt.')
        return
    path = Path('tmp/publication-receipt.json')
    evidence = path.read_text() if path.exists() else 'Nachweis konnte nicht ausgeführt werden.'
    body = (f'{marker}\n## Auslieferungsziel nicht bestätigt\n\n'
            f'UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}\n\n'
            f'```json\n{evidence}\n```\n\n'
            'Runbook: docs/publication-reliability.md. Keine Qualitätsgates umgehen.\n')
    if issue:
        gh('issue', 'edit', str(issue['number']), '--body', body)
    else:
        gh('issue', 'create', '--title', 'P1: Öffentliche Artikel-Auslieferung unter Mindestziel', '--body', body)
    # Bounded: only fixed monitoring slots trigger repair; no workflow_run cycle.
    gh('workflow', 'run', 'deploy.yml', '--ref', 'main')
    if dt.datetime.now(dt.timezone.utc).weekday() in {0, 2, 4}:
        gh('workflow', 'run', 'kadenz-endkontrolle.yml', '--ref', 'main')


if __name__ == '__main__':
    main()
