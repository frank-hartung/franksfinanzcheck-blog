#!/usr/bin/env python3
"""Preflight the stock on quiet days. Count proven articles, not reserve flags."""
import hashlib
import json
from pathlib import Path

import reserve_pool as rp
from publication_release import accept_candidate


def main():
    rows = []
    for index in rp.reserve_drafts():
        original = index.read_text(encoding='utf-8')
        try:
            rp.publish_one(index)
            ready = accept_candidate(index)
            rows.append({'slug': index.parent.name, 'ready': ready,
                         'sha256': hashlib.sha256(original.encode()).hexdigest()})
        finally:
            index.write_text(original, encoding='utf-8')
    report = {'target': 6, 'ready': sum(r['ready'] for r in rows), 'candidates': rows}
    Path('data/reserve-readiness.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['ready'] >= report['target'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
