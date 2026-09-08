#!/usr/bin/env python3
"""Kadenz-Watchdog: mindestens zwei freigegebene Artikel, niemals Entwürfe.
UTC Mo/Mi/Fr; vor 21 Uhr WARN bei Defizit, danach/folgenden Tagen FAIL.
Der öffentliche Auslieferungsnachweis erfolgt separat via publication_check.py.
"""
import datetime
import glob
import json
import os
import re
import sys

# Konsistent mit scripts/cadence_guard.py (Mo=0, Mi=2, Fr=4)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from cadence_guard import PUBLICATION_DAYS  # noqa: F401 – eine Quelle der Wahrheit
except Exception:  # Fallback, falls cadence_guard nicht importierbar ist
    PUBLICATION_DAYS = {0, 2, 4}

DAY_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
             "Freitag", "Samstag", "Sonntag"]
DATE_RE = re.compile(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.M)
DRAFT_RE = re.compile(r"^draft:\s*true\b", re.M)


def last_publish_day(today=None):
    """Der letzte Mo/Mi/Fr-Tag bis heute (inkl. heute)."""
    d = today or datetime.date.today()
    while d.weekday() not in PUBLICATION_DAYS:
        d -= datetime.timedelta(days=1)
    return d


def articles_on(day):
    """Zählt Artikel (live/entwurf) mit Frontmatter-datum == Tag."""
    live, drafts = [], []
    for f in sorted(glob.glob("content/posts/*/index.md")):
        try:
            head = open(f, encoding="utf-8").read(2500)
        except OSError:
            continue
        m = DATE_RE.search(head)
        if m and m.group(1) == day.isoformat():
            slug = f.split(os.sep)[-2]
            (drafts if DRAFT_RE.search(head) else live).append(slug)
    return live, drafts


def main():
    as_json = "--json" in sys.argv
    today = datetime.date.today()
    is_publish_day = today.weekday() in PUBLICATION_DAYS
    expected = last_publish_day(today)

    from cadence_guard import effective_limits
    minimum, maximum = effective_limits()
    live, drafts = articles_on(expected)
    now = datetime.datetime.now(datetime.timezone.utc)
    pending = is_publish_day and (now.hour, now.minute) < (21, 0)
    if minimum <= len(live) <= maximum:
        verdict, exit_code = "OK", 0
    elif pending and len(live) < minimum:
        verdict, exit_code = "WARN", 3
    else:
        verdict, exit_code = "FAIL", 1
    detail = (f"Publikationstag {expected}: {len(live)} freigegeben, "
              f"{len(drafts)} Entwürfe; Ziel {minimum}–{maximum}. "
              "Entwürfe zählen nicht. Öffentlicher Nachweis: publication_check.py --online.")

    payload = {
        "verdict": verdict,
        "today": today.isoformat(),
        "weekday": DAY_NAMES[today.weekday()],
        "is_publish_day": is_publish_day,
        "expected_publish_day": expected.isoformat(),
        "detail": detail,
        "live": len(live), "drafts": len(drafts), "minimum": minimum,
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        icon = {"OK": "✅", "WARN": "🟡", "FAIL": "❌"}[verdict]
        print(f"{icon} {detail}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
