#!/usr/bin/env python3
"""Final acceptance, before quota accounting. No relaxed gate or network AI required."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True, timeout=240)


def accept_candidate(index):
    """Candidate is temporarily live. Caller MUST restore draft on rejection/error.

    Uses exactly the production publish gate including rendered affiliate proof.
    Quality scores must meet the documented publish threshold, not merely avoid review.
    """
    import publish_gate as gate
    import quality_score as qs
    result = qs.score_article(str(index))
    if result['score'] < qs.THRESHOLD_PUBLISH:
        print(f"Reserve nicht bereit: {index.parent.name}: {result}")
        return False
    run('hugo', '--minify', '--cleanDestinationDir')
    old_candidates, old_dry, old_strict = gate.todays_live_candidates, gate.DRY_RUN, gate.STRICT
    try:
        gate.todays_live_candidates = lambda: [index.parent.name]
        gate.DRY_RUN, gate.STRICT = True, True
        return gate.main() == 0
    finally:
        gate.todays_live_candidates = old_candidates
        gate.DRY_RUN, gate.STRICT = old_dry, old_strict


def main():
    # Run after ALL editorial mutations; source quota must survive final gates.
    import publish_gate
    import quality_score as qs
    import park_state
    for slug in publish_gate.todays_live_candidates():
        index = ROOT / 'content' / 'posts' / slug / 'index.md'
        score = qs.score_article(str(index))
        if score['score'] < qs.THRESHOLD_PUBLISH:
            park_state.hold(str(index), f"quality-score: {score['score']} < {qs.THRESHOLD_PUBLISH}; finale Freigabe fehlt")
    run('hugo', '--minify', '--cleanDestinationDir')
    run(sys.executable, 'scripts/publish_gate.py')
    import reserve_pool
    reserve_pool.publish_to_min()
    run(sys.executable, 'scripts/draft_link_healer.py', '--fix')
    run('hugo', '--minify', '--cleanDestinationDir')
    run(sys.executable, 'scripts/publish_gate.py')
    # Delivery itself is verified independently after deploy.
    import publication_check as receipt
    import datetime as dt
    day = dt.datetime.now(dt.timezone.utc).date()
    if day.weekday() not in receipt.cg.PUBLICATION_DAYS:
        return 0
    result = receipt.check(day)
    print(result)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
