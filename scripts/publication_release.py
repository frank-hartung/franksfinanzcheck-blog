#!/usr/bin/env python3
"""Final acceptance, before quota accounting.

Premium-Fix 11.09.2026 (#258): Wenn der Tag nach den finalen Gates noch unter
Minimum liegt, versucht die Endabnahme zuerst weitere Re-Queue-Artikel und dann
den Reserve-Pool jeweils einzeln durch die echten Publish-Gates zu bekommen.
Der frühere On-demand-Reserve-Finish (lange KI-/Heiler-Kette) ist in dieser
letzten Brandschutzlinie standardmäßig deaktiviert: Die Endkontrolle muss
schnell, deterministisch und persistierbar bleiben.
"""
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True, timeout=240)


def finish_reserve_if_needed() -> bool:
    """Optionaler, bewusst deaktivierter Reserve-Finish-Pass.

    Premium-Fix 11.09.2026 (#258): Die finale Kadenz-Endkontrolle ist die
    letzte, deterministische Brandschutzlinie des Tages. Dort darf kein
    langer KI-/Heiler-Marathon mehr starten: genau dieser On-demand-Finish
    konnte die Endabnahme so lange blockieren, dass trotz vorhandener
    Kandidaten kein zweiter LIVE-Post persistiert wurde.

    Die Reserve wird weiterhin in `content-reserve.yml` veredelt und
    zertifiziert. In der Endkontrolle veröffentlichen wir nur noch bereits
    vorhandene Kandidaten, die die echten Publish-Gates sofort bestehen.
    Wer den alten Notfall-Finish gezielt testen will, kann ihn explizit mit
    `ENABLE_ON_DEMAND_RESERVE_FINISH=1` aktivieren. Default: aus.
    """
    if os.environ.get("ENABLE_ON_DEMAND_RESERVE_FINISH") != "1":
        print("Reserve-Finish on demand: übersprungen (deterministische Endkontrolle; "
              "Reserve-Veredelung läuft separat in content-reserve.yml).")
        return False

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
              f"Pool {len(pool)} – explizit aktiviert.")
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



def promote_requeue_to_min(posts_dir=None, validator=None) -> list[str]:
    """Validiert wartende Re-Queue-Artikel einzeln und füllt nur bis Minimum.

    Warum zusätzlich zu `cadence_guard --fix`? Das Kadenz-Gate kann vor der
    finalen Endabnahme mehrere wartende Artikel live setzen. Fällt einer davon
    später am harten Publish-Gate wieder heraus, blieb der Tag bisher unter
    Minimum, obwohl weitere wartende, potenziell bessere Artikel vorhanden
    waren. Diese Funktion ist der deterministische zweite Griff: Kandidat
    temporär freigeben, echte Gates ausführen, bei Ablehnung bytegenau
    zurückstellen und den nächsten Kandidaten versuchen.
    """
    import cadence_guard as cg
    import park_state

    posts_dir = posts_dir or ROOT / 'content' / 'posts'
    today = dt.datetime.now(dt.timezone.utc).date()
    if today.weekday() not in cg.PUBLICATION_DAYS:
        print("Re-Queue-Fallback: kein Publikationstag – übersprungen.")
        return []
    minimum, _ = cg.effective_limits()
    validator = validator or accept_candidate
    published: list[str] = []

    def _load():
        return cg.load_posts(str(posts_dir))

    while len(cg.published_on(_load(), today)) < minimum:
        waiting = [p for p in _load() if p['draft'] and p['wait']]
        waiting.sort(key=lambda p: (p['date_raw'], p['slug']))
        if not waiting:
            break
        progressed = False
        for post in waiting:
            if len(cg.published_on(_load(), today)) >= minimum:
                break
            index = Path(post['path'])
            original = index.read_text(encoding='utf-8')
            accepted = False
            try:
                iso = cg.now_utc_iso()
                if iso[:10] != today.isoformat():
                    print("Re-Queue-Fallback: Mitternachtsgrenze erreicht – Abbruch ohne Backdate.")
                    return published
                text = re.sub(r"(?m)^date:\s*.*$", f"date: {iso}", original, count=1)
                index.write_text(text, encoding='utf-8')
                park_state.release(str(index), do_fix=True)
                accepted = bool(validator(index))
            finally:
                if not accepted:
                    index.write_text(original, encoding='utf-8')
            if accepted:
                published.append(index.parent.name)
                progressed = True
                print(f"  ♻️  Re-Queue-Fallback live geschaltet: {index.parent.name}")
            else:
                print(f"  Re-Queue-Fallback abgelehnt, bleibt wartend: {index.parent.name}")
        if not progressed:
            break
    if published:
        print(f"Re-Queue-Fallback: {len(published)} Artikel veröffentlicht – "
              f"jetzt {len(cg.published_on(_load(), today))}/{minimum} live.")
    return published


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
    promote_requeue_to_min()
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
