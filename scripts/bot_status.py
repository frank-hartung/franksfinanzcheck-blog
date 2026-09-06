#!/usr/bin/env python3
"""bot_status.py – schreibt BOT-STATUS.md am Ende jedes Engine-Laufs.

Von content-engine-v2.yml Phase 4 aufgerufen. Fehlt das Skript, bleibt
das Dashboard eingefroren (genau der Produktions-Blindflug, den
PRODUKTIONS-WACHE schließen soll).
"""
from __future__ import annotations

import datetime
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import cadence_guard as cg  # noqa: E402

OUT = os.path.join(BLOG_DIR, "BOT-STATUS.md")


def _topics_stats() -> tuple[int, int]:
    try:
        import generate_drafts as g
        topics = g.load_topics()
        used = g.existing_titles()
        frei = sum(1 for t in topics if not g.topic_already_covered(t.get("title", ""), used))
        return len(topics), frei
    except Exception:
        return 0, 0


def main() -> int:
    today = datetime.date.today()
    posts = cg.load_posts()
    live_today = [p for p in posts if not p["draft"] and p["date"] == today]
    drafts_today = [p for p in posts if p["draft"] and p["date"] == today]
    min_n = int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2")
    max_n = int(os.environ.get("MAX_ARTIKEL_PRO_TAG") or "3")
    if min_n < 2:
        min_n = 2
    if max_n < min_n:
        max_n = min_n
    total, frei = _topics_stats()
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M Uhr (lokal)")
    weekday = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][today.weekday()]
    is_pub = today.weekday() in cg.PUBLICATION_DAYS
    lines = [
        "# 🤖 Bot-Status",
        "",
        f"> Automatisch aktualisiert: {now}",
        "",
        "## Heutiger Stand",
        "",
        f"- **Publikationstag:** {'ja (Mo/Mi/Fr)' if is_pub else 'nein'}",
        f"- **Veröffentlicht heute:** {len(live_today)}/{max_n} Artikel (Mindestziel {min_n})",
        f"- **Entwürfe heute:** {len(drafts_today)}",
        "",
        "## System",
        "",
        f"- **Themenpool:** {total} Themen, **{frei} frei**",
        f"- **Letzter Content-Tag:** {today.isoformat()} ({weekday}.): "
        f"{len(live_today)} live, {len(drafts_today)} Entwurf(e)",
        f"- **Tageslimit:** {min_n}–{max_n} Artikel pro Publikationstag "
        "(Mo/Mi/Fr; MIN_ARTIKEL_PRO_TAG / MAX_ARTIKEL_PRO_TAG)",
        "",
        "## Bei Problemen",
        "",
        "- Offene Issues prüfen (Fehler-Alerting + Produktions-Wache)",
        "- API-Keys: Settings → Secrets and variables → Actions",
        "- Workflow: Actions → „Content-Engine v2“ → Run workflow",
        "",
        "---",
        "*Erzeugt von scripts/bot_status.py am Ende jedes Bot-Laufs.*",
        "",
    ]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"BOT-STATUS.md geschrieben ({len(live_today)} live heute).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
