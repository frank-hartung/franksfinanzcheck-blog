#!/usr/bin/env python3
"""bot_status.py – schreibt BOT-STATUS.md und ENGINE-STATUS.md.

Von content-engine-v2.yml Phase 4 aufgerufen. Der Schritt läuft NACH allen
finalen Gates; deshalb werden beide Statusdateien hier aus dem tatsächlichen
Quellzustand neu berechnet. So kann ENGINE-STATUS nicht mehr einen frühen
Zwischenstand (z. B. "2 live") konservieren, wenn finale Gates die Artikel
später wieder auf Draft zurückstufen.
"""
from __future__ import annotations

import datetime
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import cadence_guard as cg  # noqa: E402

BOT_OUT = os.path.join(BLOG_DIR, "BOT-STATUS.md")
ENGINE_OUT = os.path.join(BLOG_DIR, "ENGINE-STATUS.md")


def _topics_stats() -> tuple[int, int]:
    try:
        import generate_drafts as g
        topics = g.load_topics()
        used = g.existing_titles()
        frei = sum(1 for t in topics if not g.topic_already_covered(t.get("title", ""), used))
        return len(topics), frei
    except Exception:
        return 0, 0


def effective_limits() -> tuple[int, int]:
    min_n = int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2")
    max_n = int(os.environ.get("MAX_ARTIKEL_PRO_TAG") or "3")
    if min_n < 2:
        min_n = 2
    if max_n < min_n:
        max_n = min_n
    return min_n, max_n


def engine_snapshot(posts: list[dict], today: datetime.date,
                    min_n: int, max_n: int) -> tuple[str, str]:
    """Liefert (level, note) für ENGINE-STATUS aus dem finalen Bestand."""
    is_pub = today.weekday() in cg.PUBLICATION_DAYS
    if not is_pub:
        day = cg.DAYS_DE[today.weekday()]
        return "OK", f"Kein Publikationstag ({day}) – Publikation nur Mo/Mi/Fr (2–3 Artikel)."

    try:
        import engine_generate as eg
        # Stichtag mitgeben: die Bilanz gilt für DIESEN Tag (deterministisch).
        bilanz = eg.tages_bilanz(posts, set(), max_n, min_n, today=today)
    except Exception:
        live_today = [p for p in posts if not p["draft"] and p["date"] == today]
        drafts_today = [p for p in posts if p["draft"] and p["date"] == today]
        bilanz = {
            "total": len(live_today),
            "neu": len(live_today),
            "recycelt": 0,
            "drafts": len(drafts_today),
        }

    holds_today = sum(1 for p in posts if p["date"] == today and p.get("state") == "hold")
    queued_today = sum(1 for p in posts if p["date"] == today and p.get("state") == "queue")
    note = (f"{bilanz['total']} Artikel live heute ({bilanz['neu']} NEU · "
            f"{bilanz['recycelt']} recycelt · {bilanz['drafts']} Entwurf")
    extras = []
    if holds_today:
        extras.append(f"{holds_today} hold")
    if queued_today:
        extras.append(f"{queued_today} Re-Queue")
    if extras:
        note += " · " + ", ".join(extras)
    note += f") | Ziel: {min_n}-{max_n} LIVE an Mo/Mi/Fr"
    if bilanz["neu"] == 0 and bilanz["total"] > 0:
        note += " | ⚠ KEINE Neuproduktion – Recycling zählt nicht als Produktion"
    if bilanz["total"] < min_n:
        note += " | ⚠ unter LIVE-Mindestziel"
    level = "WARN" if bilanz["total"] < min_n else "OK"
    return level, note


def write_engine_status(posts: list[dict], today: datetime.date,
                        min_n: int, max_n: int) -> str:
    level, note = engine_snapshot(posts, today, min_n, max_n)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 🤖 ENGINE-STATUS (Content-Engine v2)",
        "",
        f"**Letzter Lauf:** {now}",
        f"**Status:** {level}",
        "",
        note,
        "",
        "_Wird bei jedem Lauf der Content-Engine v2 aktualisiert._",
        "",
    ]
    with open(ENGINE_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return level


def main() -> int:
    today = datetime.date.today()
    posts = cg.load_posts()
    live_today = [p for p in posts if not p["draft"] and p["date"] == today]
    drafts_today = [p for p in posts if p["draft"] and p["date"] == today]
    min_n, max_n = effective_limits()
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
    with open(BOT_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    level = write_engine_status(posts, today, min_n, max_n)
    print(f"BOT-STATUS.md + ENGINE-STATUS.md geschrieben ({len(live_today)} live heute, Level {level}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
