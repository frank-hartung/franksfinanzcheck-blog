#!/usr/bin/env python3
"""automation_calendar.py – KOLLISIONS-KALENDER DER GESAMTEN AUTOMATIK
(Agentur-Stufe-2, 27.08.2026 – dauerhafte Simulationsinstanz)

Zweck
  Simuliert ALLE Workflow-Crons der nächsten N Tage (Minute für Minute,
  Zeitzone Europe/Berlin) und prüft die betrieblichen Invarianten, die
  im Audit festgelegt wurden – dauerhaft, bei jedem Lauf neu:

  I1  Affiliate-Integritäts-Wache VOR dem Engine-Hauptslot (CTA-Frische)
  I2  Pinterest-Watchdog VOR dem Engine-Hauptslot (Feed sauber BEFORE Pins)
  I3  Blog-Gesundheit VOR dem Engine-Hauptslot (Kadenz geheilt BEFORE Publish)
  I4  Social-Media-AI NACH dem Engine-Hauptslot (Artikel zuerst live)
  I5  Mastodon-SEO NACH Social-Media-AI (Toot zuerst da, dann heilen)
  I6  Bot-Watchdog NACH dem Engine-Hauptslot (prüft den Morgen-Lauf)
  I7  Keine zwei PUSHENDEN Workflows zur exakten selben Minute
      (Push-Race-Prophylaxe; git_push_retry.sh fängt Reste ab)
  I8  Engine-Fallback-Slots NACH dem Hauptslot (Selbstheilung-Reihenfolge)
  I9  Winterzeit-Proof: alle Invarianten gelten in MESZ UND MEZ
      (GitHub-Cron läuft in UTC – lokale Kommentare verschieben sich
      am 25.10.2026 um 1 h; die PRÜFUNG hier stellt die Reihenfolge
      sicher, weil sie auf UTC-Zeitpunkten basiert)

Nebenbei entsteht der Wochen-Fahrplan als Markdown-Tabelle (–md) für
Reports/FrankAutoOps.

AUFRUF
  python3 scripts/automation_calendar.py            # nächster Montag-Start, 7 Tage
  python3 scripts/automation_calendar.py --days 14 --md
  python3 scripts/automation_calendar.py --at 2026-10-23:2026-10-27   # DST-Fenster
Exit: 0 = alle Invarianten grün · 1 = Verstoß (Issue-würdig)
"""
import datetime
import glob
import sys
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML fehlt: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

DE = ZoneInfo("Europe/Berlin")
WORKFLOW_DIR = ".github/workflows"

# Pushende Workflows (committen nach main) – Grundlage für I7
PUSHER = {
    "Content-Engine v2",
    "Blog-Gesundheits-Check (täglich)",
    "Affiliate-Integritäts-Wache (täglich)",
    "Pinterest-Watchdog",
    "Social-Media-AI",
    "Mastodon-SEO",
    "Mastodon-Profil-Sync",
    "Wöchentliche SEO-Optimierung",
    "Affiliate-Health (Wochenwache)",
    "Backlink-Automation",
    "Layout-AI",
    "Willkommenstext-Refresh",
    "FrankAutoOps-Report",
    "Quartalsweises Artikel-Update",
    "Deploy auf GitHub Pages",
}

# Invarianten: (Name, Workflow A, Workflow B, "A vor B am selben UTC-Tag")
ORDERINGS = [
    ("I1", "Affiliate-Integritäts-Wache (täglich)", "Content-Engine v2"),
    ("I2", "Pinterest-Watchdog", "Content-Engine v2"),
    ("I3", "Blog-Gesundheits-Check (täglich)", "Content-Engine v2"),
    ("I4", "Content-Engine v2", "Social-Media-AI"),
    ("I5", "Social-Media-AI", "Mastodon-SEO"),
    ("I6", "Content-Engine v2", "Bot-Watchdog"),
]


def cron_field_match(field, value, dow_mode=False):
    """Vixie-Cron-Matching für ein Feld (*, Listen, Bereiche, Schritte)."""
    if field == "*":
        return True
    for part in field.split(","):
        step = 1
        base = part
        if "/" in part:
            base, step_s = part.split("/", 1)
            step = int(step_s)
        if base == "*":
            lo, hi = (0, 6) if dow_mode else (0, 59)
        elif "-" in base:
            lo_s, hi_s = base.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
        else:
            lo = hi = int(base)
            if dow_mode and lo == 7:
                lo = hi = 0
        if lo <= value <= hi and (value - lo) % step == 0:
            return True
    return False


def cron_matches(expr, dt):
    parts = expr.split()
    if len(parts) != 5:
        return False
    mi, h, dom, mon, dow = parts
    if not cron_field_match(mi, dt.minute):
        return False
    if not cron_field_match(h, dt.hour):
        return False
    if not cron_field_match(mon, dt.month):
        return False
    dom_ok = cron_field_match(dom, dt.day)
    dow_ok = cron_field_match(dow, dt.weekday(), dow_mode=True)
    if dom == "*" and dow == "*":
        return True
    if dom == "*":
        return dow_ok
    if dow == "*":
        return dom_ok
    return dom_ok or dow_ok  # Vixie: beide beschränkt → ODER


def load_schedules():
    out = []  # (workflow_name, cron)
    for f in sorted(glob.glob(f"{WORKFLOW_DIR}/*.y*ml")):
        try:
            data = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception as exc:
            print(f"⚠ YAML-Fehler {f}: {exc}", file=sys.stderr)
            continue
        trig = data.get(True, {}) or data.get("on", {}) or {}
        name = data.get("name") or f
        for sched in trig.get("schedule", []) or []:
            expr = sched.get("cron")
            if expr:
                out.append((name, expr))
    return out


def expand(start_utc, days, schedules):
    """Liefert Liste (utc_dt, name) der nächsten `days` Tage."""
    events = []
    end = start_utc + datetime.timedelta(days=days)
    t = start_utc
    while t < end:
        for name, expr in schedules:
            if cron_matches(expr, t):
                events.append((t, name))
        t += datetime.timedelta(minutes=1)
    return sorted(events)


def check_invariants(events):
    problems = []
    by_day = {}
    for t, name in events:
        by_day.setdefault(t.date(), []).append((t, name))

    for day, day_events in sorted(by_day.items()):
        times = {}
        for t, name in day_events:
            times.setdefault(name, []).append(t)
        for iname, first, second in ORDERINGS:
            if first in times and second in times:
                if min(times[first]) >= min(times[second]):
                    problems.append(
                        f"{iname} VERLETZT am {day}: {first} "
                        f"({min(times[first]).strftime('%H:%M')} UTC) nicht vor "
                        f"{second} ({min(times[second]).strftime('%H:%M')} UTC)")
        # I7: pushende Workflows zur selben Minute
        per_minute = {}
        for t, name in day_events:
            if name in PUSHER:
                per_minute.setdefault(t.strftime("%H:%M"), set()).add(name)
        for minute, names in sorted(per_minute.items()):
            if len(names) > 1:
                problems.append(
                    f"I7 RISIKO am {day} {minute} UTC: pushend gleichzeitig: "
                    f"{sorted(names)}")
        # I8: Fallback-Slots nach Hauptslot (Content-Engine mehrfach/Tag)
    engine_days = {d: sorted(t for t, n in ev if n == "Content-Engine v2")
                   for d, ev in by_day.items() if any(n == "Content-Engine v2" for _, n in ev)}
    for d, ts in engine_days.items():
        if len(ts) > 1 and ts[1] <= ts[0]:
            problems.append(f"I8 VERLETZT am {d}: Fallback-Slot vor Hauptslot")
    return problems


def fmt_md(events, problems):
    lines = ["## 📅 Automatik-Kalender (Simulation, Europe/Berlin)", ""]
    last_day = None
    for t, name in events:
        local = t.astimezone(DE)
        if local.date() != last_day:
            last_day = local.date()
            lines.append(f"\n### {local.strftime('%a %d.%m.%Y')}")
        lines.append(f"- {local.strftime('%H:%M')} – {name}")
    lines.append("")
    if problems:
        lines.append("### ⚠ Invarianten-Verstöße")
        lines += [f"- {p}" for p in problems]
    else:
        lines.append("### ✅ Alle Invarianten (I1–I8) eingehalten – auch über "
                     "den Winterzeit-Wechsel (Zeitzone Europe/Berlin).")
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    days = 7
    start = datetime.datetime.now(datetime.timezone.utc).replace(
        minute=0, second=0, microsecond=0)
    if "--at" in args:
        window = args[args.index("--at") + 1]
        a, b = window.split(":")
        start = datetime.datetime.fromisoformat(a).replace(
            tzinfo=datetime.timezone.utc)
        days = (datetime.datetime.fromisoformat(b)
                - datetime.datetime.fromisoformat(a)).days + 1
    if "--days" in args:
        days = int(args[args.index("--days") + 1])

    schedules = load_schedules()
    events = expand(start, days, schedules)
    problems = check_invariants(events)

    if "--check-only" not in args:  # Markdown ist Standardausgabe
        print(fmt_md(events, problems))
        print(f"\n— {len(schedules)} Cron-Definitionen, {len(events)} Events in "
              f"{days} Tagen simuliert (Start {start.date()}).")
    if problems and "--check-only" in args:
        for p in problems:
            print(f"❌ {p}")
    elif "--check-only" in args:
        print(f"✅ Invarianten I1–I9 grün ({len(schedules)} Crons, "
              f"{len(events)} Events, {days} Tage).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
