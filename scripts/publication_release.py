#!/usr/bin/env python3
"""Final acceptance, before quota accounting.

Premium-Fix 09.09.2026 (#237): Wenn der Tag nach den finalen Gates noch unter
Minimum liegt, versucht die Endabnahme vor dem Reserve-Publish eine
bedarfsgetriebene Reserve-Veredelung. So kann dieselbe Engine-Ausführung einen
unterreifen Pool noch am Publikationstag nachziehen, statt blind mit 0 READY in
`publish_to_min()` zu laufen und erst am nächsten Morgen auf die Reserve-Linie
zu warten.
"""
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True, timeout=240)


def finish_reserve_if_needed() -> bool:
    """Best-effort: veredelt Reserve-Kandidaten on demand bei Tagesdefizit.

    Die tägliche Reserve-Linie hält den Pool normalerweise bereit. Wenn ein
    Publikationstag aber bis zur finalen Abnahme unter dem LIVE-Minimum bleibt,
    lohnt ein letzter lokaler Finish-Pass auf vorhandene Reserve-Entwürfe,
    bevor `publish_to_min()` Kandidaten verwirft. Fehler bremsen die finale
    Freigabe nicht – die Reserve-Prüfung selbst bleibt die Autorität.
    """
    import cadence_guard as cg
    import reserve_pool

    today = dt.datetime.now(dt.timezone.utc).date()
    if today.weekday() not in cg.PUBLICATION_DAYS:
        return False
    minimum, _ = cg.effective_limits()
    live = len(cg.published_on(cg.load_posts(), today))
    pool = reserve_pool.reserve_drafts()
    if live >= minimum or not pool:
        return False
    try:
        import reserve_finisher
        print(f"Reserve-Finish on demand: LIVE {live}/{minimum}, "
              f"Pool {len(pool)} – Veredelung vor Reserve-Freigabe.")
        rc = reserve_finisher.finish()
        if rc != 0:
            print(f"⚠ Reserve-Finish on demand unvollständig (rc={rc}) – "
                  "trotzdem weiter mit harter Reserve-Prüfung.")
        return True
    except Exception as exc:  # noqa: BLE001 – finale Gates bleiben robust
        print(f"⚠ Reserve-Finish on demand fehlgeschlagen: {exc}")
        return False


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
    finish_reserve_if_needed()
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
