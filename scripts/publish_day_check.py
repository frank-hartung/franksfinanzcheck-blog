#!/usr/bin/env python3
"""publish_day_check.py – KADENZ-BEWUSSTE CONTENT-ERWARTUNG (Audit 27.08.2026)

PROBLEM (gelöst durch dieses Skript):
  1) Der Bot-Watchdog prüfte „Content-Commit in den letzten 30 h
     (erwartet: 2/Tag)“. Die Dauervorgabe ist aber Mo/Mi/Fr (2–3
     Artikel an Publikationstagen). Folge: JEDEN Sonntag einen
     Fehlalarm (Fr → So = ~50 h Lücke, Issue #57 vom 23.08.2026).
  2) Der Check hing an `git log --grep='^content:'` – nach der
     History-Konsolidierung (27.08. 00:00) findet der kein Commit
     mehr → dauerhafter Fehlalarm „noch nie ein Content-Commit“.

LÖSUNG: Der Check liest den CONTENT selbst (Frontmatter-datum der
Artikel) und vergleicht mit dem ERWARTETEN Publikationstag
(inkl. Fallback-Slots des Content-Engines):

  · Heute IST Publikationstag (Mo/Mi/Fr):
      – Artikel (live ODER draft) von heute vorhanden  → OK (Exit 0)
      – noch keiner → WARN (Exit 3): Haupt-Slot 08:10 könnte
        gelaufen sein, aber Fallback-Slots 16:10/19:40 stehen
        noch aus → kein Issue, nur Hinweis im Log. Engine-Phase 6
        (engine_issue.py --deficit) meldet sich abends selbst.
  · Heute IST KEIN Publikationstag (Di/Do/Sa/So):
      – Erwartungstag = letzter Mo/Mi/Fr ≤ heute.
        Kein Artikel an DIESEM Tag → FAIL (Exit 1) = echter
        Komplettausfall der Engine → Issue vom Watchdog.

Exit-Codes: 0 = OK · 3 = WARN (Publikationstag, Slots laufen noch)
            1 = FAIL (erwarteter Publikationstag ohne Artikel)

AUFRUF:
  python3 scripts/publish_day_check.py            # Mensch-Text + Exit
  python3 scripts/publish_day_check.py --json     # Machine-JSON
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

    if is_publish_day:
        live, drafts = articles_on(today)
        if live or drafts:
            verdict, exit_code = "OK", 0
            detail = (f"Publikationstag {DAY_NAMES[today.weekday()]}: "
                      f"{len(live)} live, {len(drafts)} Entwurf(er) – Kadenz erfüllt.")
        else:
            verdict, exit_code = "WARN", 3
            detail = (f"Publikationstag {DAY_NAMES[today.weekday()]} bislang ohne "
                      f"Artikel – Fallback-Slots 16:10/19:40 stehen noch aus "
                      f"(kein Alarm, Engine-Phase 6 meldet sich abends).")
    else:
        live, drafts = articles_on(expected)
        if live or drafts:
            verdict, exit_code = "OK", 0
            detail = (f"Kein Publikationstag heute ({DAY_NAMES[today.weekday()]}) – "
                      f"letzter Publikationstag {expected.isoformat()} "
                      f"({DAY_NAMES[expected.weekday()]}): {len(live)} live, "
                      f"{len(drafts)} Entwurf(er). Alles konform.")
        else:
            verdict, exit_code = "FAIL", 1
            detail = (f"KEIN Artikel am erwarteten Publikationstag "
                      f"{expected.isoformat()} ({DAY_NAMES[expected.weekday()]}) – "
                      f"Komplettausfall der Content-Engine. Bot prüfen "
                      f"(API-Keys, Actions-Logs Content-Engine v2).")

    payload = {
        "verdict": verdict,
        "today": today.isoformat(),
        "weekday": DAY_NAMES[today.weekday()],
        "is_publish_day": is_publish_day,
        "expected_publish_day": expected.isoformat(),
        "detail": detail,
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        icon = {"OK": "✅", "WARN": "🟡", "FAIL": "❌"}[verdict]
        print(f"{icon} {detail}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
