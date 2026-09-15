#!/usr/bin/env python3
"""Final acceptance, before quota accounting.

Premium-Fix 11.09.2026 (#258): Wenn der Tag nach den finalen Gates noch unter
Minimum liegt, versucht die Endabnahme zuerst weitere Re-Queue-Artikel und dann
den Reserve-Pool jeweils einzeln durch die echten Publish-Gates zu bekommen.
Der frühere On-demand-Reserve-Finish (lange KI-/Heiler-Kette) ist in dieser
letzten Brandschutzlinie standardmäßig deaktiviert: Die Endkontrolle muss
schnell, deterministisch und persistierbar bleiben.

Premium-Fix 15.09.2026 (#287): Gate-Verwurf im Deploy darf das Tagesmindestziel
nicht ungefüllt lassen. `refill_to_min()` ist die gemeinsame Brandschutzlinie
für Engine-Endabnahme, Kadenz-Backstop UND Deploy – nach jedem Verlust (discard
oder Hold) füllt sie Re-Queue und Reserve bis zum LIVE-Mindestziel nach.
Ohne diesen Schritt blieb am 14.09. nach dem Verwurf des Tages-Artikels nur
noch 1 LIVE-Post stehen, bis der nächtliche Backstop griff – der öffentliche
Nachweis meldete das Defizit zu Recht.
"""
import argparse
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


def preheal_candidate(index: Path) -> list[str]:
    """Deterministische Source-Heilung, bevor ein Kandidat im Dry-Run-Gate steht.

    `accept_candidate()` prüft Re-Queue/Reserve-Posts absichtlich mit
    `publish_gate` im STRICT+DRY-RUN-Modus. Dry-Run darf aber nicht schreiben;
    deshalb bekämen verlustfrei heilbare R5-Absatz-Hartfälle nie die Chance auf
    Annahme und blieben als Hold liegen (Issue #286). Der Aufrufer hält bereits
    einen bytegenauen Snapshot und stellt bei Ablehnung zurück – daher ist diese
    Vorheilung sicher: angenommen = verbesserter Text bleibt, abgelehnt =
    Originalbytes kommen zurück.
    """
    changes: list[str] = []
    try:
        import r5_absatz_splitter as r5
        text = index.read_text(encoding='utf-8')
        if r5.hard_r5_findings(text, f"content/posts/{index.parent.name}/index.md"):
            new_text, splits, warnings = r5.heal_text(text)
            if splits and new_text != text:
                index.write_text(new_text, encoding='utf-8')
                changes.append(f"R5-ABSATZ-HART: {splits} Absatz-Split(s)")
            for warning in warnings[:3]:
                print(f"  ⚠ {index.parent.name}: R5-Vorheilung: {warning}")
    except Exception as exc:  # noqa: BLE001 – echte Gate-Prüfung entscheidet danach
        print(f"  ⚠ {index.parent.name}: R5-Vorheilung nicht verfügbar: {exc}")
    return changes


def accept_candidate(index):
    """Candidate is temporarily live. Caller MUST restore draft on rejection/error.

    Uses exactly the production publish gate including rendered affiliate proof.
    Quality scores must meet the documented publish threshold, not merely avoid review.
    """
    prehealed = preheal_candidate(index)
    if prehealed:
        print(f"Reserve/Re-Queue vorgeheilt: {index.parent.name}: "
              + "; ".join(prehealed))
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


def live_count_today(posts_dir=None) -> tuple[int, int, dt.date]:
    """(live, minimum, today_utc) – Single Source für Defizit-Erkennung."""
    import cadence_guard as cg
    posts_dir = posts_dir or ROOT / 'content' / 'posts'
    today = dt.datetime.now(dt.timezone.utc).date()
    minimum, _ = cg.effective_limits()
    live = len(cg.published_on(cg.load_posts(str(posts_dir)), today))
    return live, minimum, today


def refill_to_min(posts_dir=None, validator=None, *, finalize: bool = True) -> list[str]:
    """Deterministische Quote-Nachfüllung nach Gate-Verlust (#287).

    Reihenfolge (bewusst, ohne KI):
      1. Re-Queue-Fallback (bereits redaktionell akzeptierte Wartende)
      2. optionaler On-demand-Finish (Default: aus)
      3. Reserve-Pool bis LIVE-Mindestziel

    Wenn `finalize` und Artikel nachgefüllt wurden: Draft-Links heilen und
    Hugo + Publish-Gate erneut laufen lassen, damit der nachgefüllte Stand
    denselben Vertrag erfüllt wie ein normaler Publish.
    """
    import cadence_guard as cg
    import reserve_pool

    posts_dir = posts_dir or ROOT / 'content' / 'posts'
    live, minimum, today = live_count_today(posts_dir)
    if today.weekday() not in cg.PUBLICATION_DAYS:
        print(f"Quote-Nachfüllung: kein Publikationstag ({cg.DAYS_DE[today.weekday()]})"
              " – übersprungen.")
        return []
    if live >= minimum:
        print(f"Quote-Nachfüllung: LIVE {live}/{minimum} bereits erfüllt – nichts zu tun.")
        return []

    print(f"🛟 Quote-Nachfüllung (#287): LIVE {live}/{minimum} – "
          "Re-Queue, dann Reserve.")
    published = list(promote_requeue_to_min(posts_dir=posts_dir, validator=validator))
    finish_reserve_if_needed()
    published.extend(reserve_pool.publish_to_min(posts_dir=posts_dir, validator=validator))

    live_after, _, _ = live_count_today(posts_dir)
    print(f"Quote-Nachfüllung: {len(published)} Artikel nachgeschoben – "
          f"jetzt {live_after}/{minimum} live.")

    if finalize and published:
        # Nachgefüllte Artikel sind bereits einzeln durch accept_candidate
        # (STRICT dry-run) gelaufen. Draft-Links + erneuter Hugo/Gate-Lauf
        # sichern den Gesamtstand ab, den Deploy und Engine committen.
        try:
            run(sys.executable, 'scripts/draft_link_healer.py', '--fix')
        except Exception as exc:  # noqa: BLE001 – Nachfüllung bleibt trotzdem stehen
            print(f"⚠ Draft-Link-Heiler nach Nachfüllung: {exc}")
        try:
            run('hugo', '--minify', '--cleanDestinationDir')
            run(sys.executable, 'scripts/publish_gate.py')
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ Finalize nach Nachfüllung: {exc}")
    return published


def hold_under_score_candidates() -> list[str]:
    """Parkt LIVE-Kandidaten unter dem Publish-Score, bevor das harte Gate läuft."""
    import publish_gate
    import quality_score as qs
    import park_state
    held = []
    for slug in publish_gate.todays_live_candidates():
        index = ROOT / 'content' / 'posts' / slug / 'index.md'
        if not index.exists():
            continue
        score = qs.score_article(str(index))
        if score['score'] < qs.THRESHOLD_PUBLISH:
            park_state.hold(
                str(index),
                f"quality-score: {score['score']} < {qs.THRESHOLD_PUBLISH}; "
                f"finale Freigabe fehlt",
            )
            held.append(slug)
            print(f"  ⏸ {slug}: Score {score['score']} < {qs.THRESHOLD_PUBLISH} → hold")
    return held


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        '--refill-only',
        action='store_true',
        help='Nur Quote nachfüllen (nach publish_gate im Deploy). Kein Vorab-Gate.',
    )
    ap.add_argument(
        '--selftest',
        action='store_true',
        help='Sabotage-Schutz: Refill-Vertrag ohne Netz/Hugo.',
    )
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.refill_only:
        # Deploy-Pfad (#287): publish_gate hat gerade verworfen/gehalten.
        # Hier nur nachfüllen – Commit/Rebuild macht der Aufrufer.
        # Zwei Pässe: falls finalize's zweites publish_gate einen Nachschub
        # wieder verwirft, greift der zweite Pass den nächsten Kandidaten.
        published = list(refill_to_min(finalize=True))
        live, minimum, _ = live_count_today()
        if live < minimum:
            published.extend(refill_to_min(finalize=True))
        live, minimum, today = live_count_today()
        import cadence_guard as cg
        if today.weekday() not in cg.PUBLICATION_DAYS:
            return 0
        ok = live >= minimum
        print({
            'mode': 'refill-only',
            'day': str(today),
            'live': live,
            'minimum': minimum,
            'published': published,
            'ok': ok,
        })
        # Deploy soll Heilungen trotzdem committen dürfen – Defizit bleibt
        # über publication_check/Endkontrolle rot, blockiert den Build nicht
        # hart (sonst ginge auch der eine gute Artikel nicht live). Exit 0.
        return 0

    # Vollständige Endabnahme (Engine + Kadenz-Backstop).
    hold_under_score_candidates()
    run('hugo', '--minify', '--cleanDestinationDir')
    run(sys.executable, 'scripts/publish_gate.py')
    # Nach Gate-Verlust sofort nachfüllen – nicht erst auf den nächsten Slot warten.
    refill_to_min(finalize=False)
    run(sys.executable, 'scripts/draft_link_healer.py', '--fix')
    run('hugo', '--minify', '--cleanDestinationDir')
    run(sys.executable, 'scripts/publish_gate.py')
    # Falls das zweite Gate erneut etwas verworfen hat: noch einmal nachfüllen.
    refill_to_min(finalize=True)

    import publication_check as receipt
    day = dt.datetime.now(dt.timezone.utc).date()
    if day.weekday() not in receipt.cg.PUBLICATION_DAYS:
        return 0
    result = receipt.check(day)
    print(result)
    return 0 if result['ok'] else 1


def run_selftest() -> int:
    """Leichte Vertrags-Tests ohne Hugo/Netz – schützt die Refill-API."""
    import tempfile
    import unittest.mock as mock

    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        posts = Path(tmp) / 'content' / 'posts'
        posts.mkdir(parents=True)

        def _write(slug, *, draft=True, wait=False, reserve=False, day='2026-09-14'):
            p = posts / slug / 'index.md'
            p.parent.mkdir(parents=True, exist_ok=True)
            extra = ''
            if wait:
                extra += 'cadence_wait: true\ncadence_demoted: 2026-09-13T12:00:00Z\n'
            if reserve:
                extra += 'reserve: true\n'
            p.write_text(
                f"---\ntitle: T\ndate: {day}T12:00:00Z\n"
                f"draft: {str(draft).lower()}\n{extra}---\nBody\n",
                encoding='utf-8',
            )
            return p

        # 1) An einem Publikationstag mit 1 LIVE und Reserve → füllt auf 2.
        _write('live-a', draft=False)
        _write('reserve-b', draft=True, reserve=True)
        _write('reserve-c', draft=True, reserve=True)

        class FixedDate(dt.date):
            @classmethod
            def today(cls):
                return cls(2026, 9, 14)  # Montag

        class FixedDateTime(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 14, 15, 0, tzinfo=dt.timezone.utc)

        with mock.patch.object(dt, 'date', FixedDate), \
             mock.patch.object(dt, 'datetime', FixedDateTime), \
             mock.patch('cadence_guard.now_utc_iso',
                        lambda: '2026-09-14T15:00:00Z'), \
             mock.patch('reserve_pool.now_utc_iso',
                        lambda: '2026-09-14T15:00:00Z'), \
             mock.patch('reserve_pool.datetime.date', FixedDate):
            published = refill_to_min(
                posts_dir=posts,
                validator=lambda p: True,
                finalize=False,
            )
        if published != ['reserve-b']:
            # nur bis Minimum=2 → genau einer aus der Reserve
            if len(published) != 1 or not published[0].startswith('reserve-'):
                errors.append(f"Refill sollte 1 Reserve heben, war: {published}")
        live_text = (posts / 'reserve-b' / 'index.md').read_text(encoding='utf-8')
        if 'draft: false' not in live_text and published:
            # publish_one schreibt draft:false – wenn published leer, anderer Fehler
            other = (posts / published[0] / 'index.md').read_text(encoding='utf-8') \
                if published else ''
            if 'draft: false' not in other:
                errors.append("nachgefüllter Reserve-Artikel nicht live")

        # 2) Off-Day: keine Nachfüllung.
        _write('off-reserve', draft=True, reserve=True, day='2026-09-15')

        class Tuesday(dt.date):
            @classmethod
            def today(cls):
                return cls(2026, 9, 15)

        class TuesdayDT(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 15, 12, 0, tzinfo=dt.timezone.utc)

        before = (posts / 'off-reserve' / 'index.md').read_bytes()
        with mock.patch.object(dt, 'date', Tuesday), \
             mock.patch.object(dt, 'datetime', TuesdayDT), \
             mock.patch('reserve_pool.datetime.date', Tuesday):
            off = refill_to_min(posts_dir=posts, validator=lambda p: True, finalize=False)
        if off:
            errors.append(f"Off-Day darf nicht nachfüllen, tat: {off}")
        if (posts / 'off-reserve' / 'index.md').read_bytes() != before:
            errors.append("Off-Day hat Reserve-Datei verändert")

    if errors:
        print("🛑 PUBLICATION-RELEASE-SELFTEST FEHLGESCHLAGEN:")
        for e in errors:
            print(f"   - {e}")
        return 2
    print("✅ publication_release-Selbsttest grün "
          "(Refill bis Minimum, Off-Day-Schutz).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
