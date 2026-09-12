#!/usr/bin/env python3
# ============================================================
#  SOCIAL-PLANNER – der Redaktionskalender des Autopiloten
#  ------------------------------------------------------------
#  Plant, WELCHER Artikel WANN auf WELCHEM Kanal mit WELCHEM Winkel
#  erscheint – 14 Tage im Voraus, rollierend, versioniert.
#
#  PLANUNGSREGELN (Agentur-Standard):
#    1. LAUNCH-WELLE: Ein neuer Artikel läuft über alle Kanäle –
#       gestaffelt nach deren Optimalzeiten und Verzögerung
#       (launch_delay_hours), damit nichts im Minutentakt überall
#       gleichzeitig aufschlägt.
#    2. EVERGREEN-RECYCLING: Wer einmal lief, kommt erst nach der
#       Sperrfrist (recycle_cooldown_days) wieder – und dann mit einem
#       ANDEREN Winkel. So altern die Ratgeber nicht im Feed.
#    3. FREQUENZSCHUTZ: Tagesobergrenze je Kanal, Mindestabstand je
#       Kanal, globale Tagesobergrenze. Kein Kanal wird zugespammt.
#    4. THEMENMIX: Auf demselben Kanal folgt nie zweimal hintereinander
#       derselbe Pillar (Rotations-Zwang, wenn möglich).
#    5. NACHVOLLZIEHBARKEIT: Der Plan liegt als YAML im Repo – jeder
#       Lauf ist reproduzierbar (deterministische Sortierung).
# ============================================================
from __future__ import annotations

import hashlib
import os
import sys
from datetime import date, datetime, timedelta, timezone

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DATA_DIR = os.path.join(BLOG_DIR, "data", "social")
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.yaml")
STATE_FILE = os.path.join(DATA_DIR, "state.yaml")

HISTORY_LIMIT = 800
# Ein Artikel darf pro Tag auf maximal so vielen Kanälen erscheinen
# (die Launch-Welle bewusst begrenzen – nie 10 Kanäle gleichzeitig).
MAX_CHANNELS_PER_ARTICLE_PER_DAY = 2


# ---------------------------------------------------------------- Zeitzonen
def _eu_offset(dt_utc: datetime) -> int:
    """MEZ/MESZ ohne tzdata: EU-Regel (letzter Sonntag März/Oktober)."""
    year = dt_utc.year
    march = date(year, 3, 31)
    start = march - timedelta(days=(march.weekday() + 1) % 7)
    october = date(year, 10, 31)
    end = october - timedelta(days=(october.weekday() + 1) % 7)
    start_utc = datetime(start.year, start.month, start.day, 1, tzinfo=timezone.utc)
    end_utc = datetime(end.year, end.month, end.day, 1, tzinfo=timezone.utc)
    return 2 if start_utc <= dt_utc < end_utc else 1


def berlin_tz(dt_utc: datetime | None = None):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Europe/Berlin")
    except Exception:  # noqa: BLE001 – ohne tzdata: EU-Regel selbst gerechnet
        dt_utc = dt_utc or datetime.now(timezone.utc)
        return timezone(timedelta(hours=_eu_offset(dt_utc)))


def berlin_now() -> datetime:
    return datetime.now(berlin_tz())


def localize(naive: datetime) -> datetime:
    """Berliner Wandzeit → zeitzonenbewusste Zeit."""
    return naive.replace(tzinfo=berlin_tz())


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = localize(dt)
    return dt


def iso(dt: datetime) -> str:
    return dt.isoformat()


# ------------------------------------------------------------------- Dateien
def _load_yaml(path: str, default):
    try:
        import yaml

        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or default
    except FileNotFoundError:
        return default
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ {os.path.basename(path)} nicht lesbar ({exc}) – starte neu.")
        return default


def _save_yaml(path: str, data) -> None:
    import yaml

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)


def load_schedule(path: str | None = None) -> dict:
    # Der Pfad wird zur Laufzeit aufgelöst (nicht als Default-Argument
    # gebunden) – sonst zeigt ein Test, der SCHEDULE_FILE umbiegt,
    # weiterhin auf die echte Plan-Datei.
    data = _load_yaml(path or SCHEDULE_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("items", [])
    return data


def save_schedule(schedule: dict, path: str | None = None) -> None:
    _save_yaml(path or SCHEDULE_FILE, schedule)


def load_state(path: str | None = None) -> dict:
    data = _load_yaml(path or STATE_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("history", [])
    data.setdefault("failures", [])
    return data


def save_state(state: dict, path: str | None = None) -> None:
    state["updated_at"] = iso(berlin_now())
    if len(state.get("history") or []) > HISTORY_LIMIT:
        state["history"] = state["history"][-HISTORY_LIMIT:]
    _save_yaml(path or STATE_FILE, state)


def record_history(state: dict, entry: dict) -> None:
    state.setdefault("history", []).append(entry)


def record_failure(state: dict, entry: dict) -> None:
    failures = state.setdefault("failures", [])
    failures.append(entry)
    state["failures"] = failures[-100:]


# ------------------------------------------------------------- Auswertung
def last_post(state: dict, channel: str, slug: str) -> dict | None:
    """Letzter erfolgreicher Post zu (Kanal, Artikel)."""
    hits = [e for e in (state.get("history") or [])
            if e.get("channel") == channel and e.get("slug") == slug and e.get("ok")]
    if not hits:
        return None
    return sorted(hits, key=lambda e: e.get("posted_at") or "")[-1]


def posts_on_day(state: dict, channel: str, day: date) -> int:
    prefix = day.isoformat()
    return sum(1 for e in (state.get("history") or [])
               if e.get("channel") == channel and (e.get("posted_at") or "").startswith(prefix)
               and e.get("ok"))


def total_on_day(state: dict, day: date) -> int:
    prefix = day.isoformat()
    return sum(1 for e in (state.get("history") or [])
               if (e.get("posted_at") or "").startswith(prefix) and e.get("ok"))


def used_angles(state: dict, channel: str, slug: str) -> set[str]:
    return {e.get("angle") for e in (state.get("history") or [])
            if e.get("channel") == channel and e.get("slug") == slug and e.get("angle")}


def last_channel_post(state: dict, channel: str) -> datetime | None:
    stamps = [parse_dt(e.get("posted_at") or "") for e in (state.get("history") or [])
              if e.get("channel") == channel and e.get("ok")]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


# ---------------------------------------------------------------- Winkelwahl
def pick_angle(channel_cfg: dict, channel_id: str, slug: str, state: dict,
               taken: set[str], day: date, sequence: int) -> str:
    """Wählt einen Winkel, der für (Kanal, Artikel) noch nicht lief.

    Rotation ist deterministisch: gleicher Tag + gleicher Artikel +
    gleicher Kanal ergibt immer denselben Winkel – der Plan bleibt
    reproduzierbar und bei einem zweiten Lauf stabil.
    """
    angles = list(channel_cfg.get("angles") or ["nutzen"])
    used = used_angles(state, channel_id, slug) | taken
    fresh = [a for a in angles if a not in used]
    pool = fresh or [a for a in angles if a not in taken] or angles
    seed = f"{channel_id}|{slug}|{day.isoformat()}|{sequence}"
    idx = int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[idx]


# ------------------------------------------------------------------ Planung
def _candidates(cfg, pool, state, now):
    """Baut die (Kanal × Artikel)-Kandidaten mit Frühzeit und Rang."""
    meta = cfg.get("meta") or {}
    window = int(meta.get("new_article_window_days") or 10)
    cands = []
    for cid, ch in (cfg.get("channels") or {}).items():
        if not (ch or {}).get("enabled"):
            continue
        cadence = ch.get("cadence") or {}
        cooldown = int(cadence.get("recycle_cooldown_days")
                       or meta.get("recycle_cooldown_days") or 75)
        delay = float(cadence.get("launch_delay_hours") or 0)
        min_age = float(ch.get("min_article_age_days") or 0)

        for art in pool:
            published = parse_dt(art.get("published") or "")
            last = last_post(state, cid, art["slug"])
            if last:
                last_at = parse_dt(last.get("posted_at") or "")
                if not last_at:
                    continue
                earliest = last_at + timedelta(days=cooldown)
                if earliest > now + timedelta(days=30):
                    continue
                tier = 2
                rank = -(now - last_at).days          # am längsten nicht gesehen zuerst
                kind = "evergreen"
            else:
                base = published or now
                earliest = base + timedelta(hours=delay)
                if min_age and published:
                    earliest = max(earliest, published + timedelta(days=min_age))
                age_days = (now - (published or now)).days
                tier = 0 if age_days <= window else 1
                rank = -age_days                       # FIFO: ältere zuerst
                kind = "launch"
            cands.append({
                "channel": cid, "slug": art["slug"], "article": art,
                "earliest": earliest, "tier": tier, "rank": rank, "kind": kind,
            })
    return cands


def _not_in_cooldown(item: dict, cfg: dict, state: dict, now: datetime) -> bool:
    """True, wenn dieser geplante Posten die Sperrfrist noch einhält."""
    if item.get("status") != "planned":
        return True
    meta = (cfg or {}).get("meta") or {}
    ch = ((cfg or {}).get("channels") or {}).get(item.get("channel") or "") or {}
    cooldown = int((((ch.get("cadence")) or {}).get("recycle_cooldown_days"))
                   or meta.get("recycle_cooldown_days") or 75)
    last = last_post(state, item.get("channel") or "", item.get("slug") or "")
    if not last:
        return True
    at = parse_dt(last.get("posted_at") or "")
    if not at:
        return True
    return (now - at) >= timedelta(days=cooldown)


def build_plan(cfg: dict, pool: list[dict], state: dict, now: datetime | None = None,
               horizon: int | None = None, keep_existing: bool = True) -> dict:
    """Erzeugt den rollierenden Plan (heute + horizon Tage)."""
    import social_channels as sch

    meta = sch.meta_of(cfg)
    channels = sch.channel_map(cfg)
    now = now or berlin_now()
    horizon = int(horizon or meta.get("plan_horizon_days") or 14)
    cap_total = int(meta.get("max_posts_per_day_total") or 12)

    schedule = load_schedule()
    items = [it for it in (schedule.get("items") or [])
             if keep_existing and it.get("status") == "planned"
             and (parse_dt(it.get("scheduled_at") or "") or now) > now - timedelta(hours=1)]
    # Bereits veröffentlichte/gescheiterte Einträge als Historie mitführen
    carried = [it for it in (schedule.get("items") or [])
               if it.get("status") in ("published", "failed", "blocked")]
    items = carried[-120:] + items

    # Selbstheilung im Altbestand des Plans: Ein bereits geplanter Posten
    # wird verworfen, wenn er inzwischen gegen die Sperrfrist verstößt
    # (z. B. weil der Artikel zwischenzeitlich von Hand oder von einem
    # früheren Lauf gesendet wurde). Sonst bliebe eine überholte Planung
    # stehen und würde trotz Sperrfrist rausgehen.
    items = [it for it in items if _not_in_cooldown(it, cfg, state, now)]

    cands = _candidates(cfg, pool, state, now)
    used_pairs = {(it.get("channel"), it.get("slug")) for it in items
                  if it.get("status") == "planned"}
    day_count: dict[str, int] = {}          # "channel|YYYY-MM-DD" → Anzahl
    article_day_count: dict[str, int] = {}  # "slug|YYYY-MM-DD"   → Anzahl
    total_day_count: dict[str, int] = {}    # "YYYY-MM-DD"        → Anzahl
    last_pillar: dict[str, str] = {}
    last_slot_time: dict[str, datetime] = {}

    # Bestehende Plandaten in die Zähler einrechnen (Fortschreibung!)
    for it in items:
        if it.get("status") != "planned":
            continue
        key = f"{it.get('channel')}|{it.get('date')}"
        day_count[key] = day_count.get(key, 0) + 1
        akey = f"{it.get('slug')}|{it.get('date')}"
        article_day_count[akey] = article_day_count.get(akey, 0) + 1
        total_day_count[it.get("date")] = total_day_count.get(it.get("date"), 0) + 1

    for offset in range(horizon + 1):
        day = (now + timedelta(days=offset)).date()
        for cid in sorted((cfg.get("channels") or {}).keys(),
                          key=lambda c: int((channels.get(c) or {}).get("priority") or 99)):
            ch = channels.get(cid) or {}
            if not ch.get("enabled"):
                continue
            cadence = ch.get("cadence") or {}
            allowed_days = set(cadence.get("days") or [0, 1, 2, 3, 4, 5, 6])
            if day.weekday() not in allowed_days:
                continue
            max_day = int(cadence.get("max_per_day") or 1)
            min_gap = int(cadence.get("min_gap_min") or 0)
            times = list(cadence.get("times") or ["09:00"])

            for t in times:
                hh, mm = (t.split(":") + ["0"])[:2]
                slot = localize(datetime(day.year, day.month, day.day, int(hh), int(mm)))
                if slot < now - timedelta(minutes=30):
                    continue
                key = f"{cid}|{day.isoformat()}"
                if day_count.get(key, 0) + posts_on_day(state, cid, day) >= max_day:
                    continue
                if total_day_count.get(day.isoformat(), 0) + total_on_day(state, day) >= cap_total:
                    continue
                if min_gap:
                    prev = last_slot_time.get(cid)
                    if prev and abs((slot - prev).total_seconds()) / 60 < min_gap:
                        continue

                usable = [c for c in cands
                          if c["channel"] == cid
                          and (c["channel"], c["slug"]) not in used_pairs
                          and c["earliest"] <= slot
                          and article_day_count.get(f"{c['slug']}|{day.isoformat()}", 0)
                          < MAX_CHANNELS_PER_ARTICLE_PER_DAY]
                if not usable:
                    continue

                # Themenmix: anderer Pillar als der zuletzt geplante.
                prefer = [c for c in usable
                          if (c["article"].get("pillar") or "") != last_pillar.get(cid)]
                chosen_pool = prefer or usable
                chosen_pool.sort(key=lambda c: (c["tier"], c["rank"], c["slug"]))
                pick = chosen_pool[0]

                angle = pick_angle(ch, cid, pick["slug"], state,
                                   {it.get("angle") for it in items
                                    if it.get("channel") == cid and it.get("slug") == pick["slug"]},
                                   day, len(items))
                item_id = f"{cid}:{pick['slug']}:{angle}:{day.isoformat()}"
                if any(it.get("id") == item_id for it in items):
                    used_pairs.add((cid, pick["slug"]))
                    continue
                items.append({
                    "id": item_id,
                    "channel": cid,
                    "slug": pick["slug"],
                    "angle": angle,
                    "kind": pick["kind"],
                    "pillar": pick["article"].get("pillar") or "",
                    "date": day.isoformat(),
                    "time": t,
                    "scheduled_at": iso(slot),
                    "status": "planned",
                    "attempts": 0,
                    "reason": "",
                })
                used_pairs.add((cid, pick["slug"]))
                day_count[key] = day_count.get(key, 0) + 1
                akey = f"{pick['slug']}|{day.isoformat()}"
                article_day_count[akey] = article_day_count.get(akey, 0) + 1
                total_day_count[day.isoformat()] = total_day_count.get(day.isoformat(), 0) + 1
                last_pillar[cid] = pick["article"].get("pillar") or ""
                last_slot_time[cid] = slot

    items.sort(key=lambda it: (it.get("scheduled_at") or "", it.get("channel") or ""))
    return {
        "version": 1,
        "generated_at": iso(now),
        "horizon_days": horizon,
        "timezone": "Europe/Berlin",
        "items": items,
    }


def planned_items(schedule: dict) -> list[dict]:
    return [it for it in (schedule.get("items") or []) if it.get("status") == "planned"]


def due_items(schedule: dict, now: datetime | None = None,
              late_grace_hours: int = 48) -> list[dict]:
    """Fällige Posten: geplant, Zeit erreicht, nicht hoffnungslos veraltet."""
    now = now or berlin_now()
    out = []
    for it in planned_items(schedule):
        at = parse_dt(it.get("scheduled_at") or "")
        if not at:
            continue
        if at <= now and (now - at) <= timedelta(hours=late_grace_hours):
            out.append(it)
    out.sort(key=lambda it: (it.get("scheduled_at") or "", it.get("channel") or ""))
    return out


def set_status(schedule: dict, item_id: str, status: str, reason: str = "") -> None:
    for it in (schedule.get("items") or []):
        if it.get("id") == item_id:
            it["status"] = status
            it["reason"] = (reason or "")[:300]
            it["attempts"] = int(it.get("attempts") or 0) + 1
            return


def prune(schedule: dict, keep_days: int = 30) -> dict:
    """Alte Einträge entfernen (Plan-Datei bleibt schlank)."""
    limit = berlin_now() - timedelta(days=keep_days)
    items = []
    for it in (schedule.get("items") or []):
        at = parse_dt(it.get("scheduled_at") or "")
        if it.get("status") == "planned" or (at and at >= limit):
            items.append(it)
    schedule["items"] = items[-600:]
    return schedule
