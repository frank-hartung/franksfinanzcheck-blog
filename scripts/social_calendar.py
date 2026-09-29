#!/usr/bin/env python3
# ============================================================
#  🗓️  SOCIAL-KALENDER – Veröffentlichungskalender je Kanal
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 29.09.2026): „Ich benötige Veröffentlichungs-
#  kalender für jeden einzelnen Social-Media-Kanal.“ – dauerhaft,
#  auf Premium-Niveau einer Profi-Agentur.
#
#  Dieses Skript ERZEUGT NICHTS NEUES an Plan-Logik: es liest den
#  bestehenden, versionierten Plan (data/social/schedule.yaml), den
#  Sende-Stand (data/social/state.yaml) und das Kanal-Playbook
#  (data/social/channels.yaml) und macht daraus für JEDEN Kanal:
#
#    · data/social/kalender/<kanal>.md    – lesbarer Wochenkalender
#    · data/social/kalender/<kanal>.ics   – abonnierbar (Handy/Outlook/
#                                            Google/Apple Kalender)
#    · data/social/kalender/UEBERSICHT.md – alle Kanäle auf einen Blick
#    · data/social/kalender/README.md     – Kurzanleitung
#
#  Jeder Kalender trägt oben die AKTUELLEN Kanal-Kriterien (Zeichen-
#  budget, Hashtag-Regel, Bildpflicht, Sendezeiten, Frequenz) – so ist
#  sofort sichtbar, nach welchen Regeln der Autopilot für diesen Kanal
#  veröffentlicht.
#
#  Läuft automatisch am Ende jedes Autopilot-Laufs (social-autopilot.yml)
#  sowie der Shorts-Schmiede – die Kalender bleiben damit dauerhaft aktuell,
#  ohne dass Frank etwas tun muss.
#
#  CLI:
#    python3 scripts/social_calendar.py --build            # alle Kalender
#    python3 scripts/social_calendar.py --build --channel mastodon
#    python3 scripts/social_calendar.py --selftest         # fail-closed
# ============================================================
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import social_channels as sch          # noqa: E402
import social_planner as planner       # noqa: E402

try:
    import social_copywriter as copy    # noqa: E402
except Exception:  # pragma: no cover - Kalender darf auch ohne Pool laufen
    copy = None

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BLOG_DIR, "data", "social", "kalender")
# Öffentlich ausgelieferte Kopie: Hugo kopiert static/ → Domain-Wurzel, d. h.
# static/kalender/<kanal>.ics ist live unter https://franksfinanzcheck.de/kalender/<kanal>.ics
STATIC_DIR = os.path.join(BLOG_DIR, "static", "kalender")
VIDEO_FILE = os.path.join(BLOG_DIR, "data", "social", "video.yaml")
VIDEO_STATE_FILE = os.path.join(BLOG_DIR, "data", "social", "video_state.yaml")

# Wochentage (Berliner Ortszeit, Montag = 0)
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

STATUS_LABEL = {
    "planned": ("⏳", "geplant"),
    "published": ("✅", "veröffentlicht"),
    "standby": ("⚪", "Standby (Zugang fehlt)"),
    "blocked": ("🚫", "blockiert"),
    "failed": ("❌", "fehlgeschlagen"),
    "skipped": ("⏭️", "übersprungen"),
}


# --------------------------------------------------------------------- Helfer
def _emoji(status: str) -> str:
    return STATUS_LABEL.get(status, ("•", status))[0]


def _status_text(status: str) -> str:
    return STATUS_LABEL.get(status, ("•", status))[1]


def _title_map() -> dict[str, str]:
    """slug -> Artikel-Titel (best effort; Kalender läuft auch ohne Pool)."""
    out: dict[str, str] = {}
    if copy is None:
        return out
    try:
        for art in copy.article_pool():
            if art.get("slug"):
                out[art["slug"]] = art.get("title") or art["slug"]
    except Exception:
        pass
    return out


def _url_map() -> dict[str, str]:
    out: dict[str, str] = {}
    if copy is None:
        return out
    try:
        for art in copy.article_pool():
            if art.get("slug"):
                out[art["slug"]] = art.get("url") or ""
    except Exception:
        pass
    return out


def _pretty_slug(slug: str, titles: dict[str, str]) -> str:
    if slug in titles:
        return titles[slug]
    # Datum vorn abschneiden und in Klartext wandeln
    rest = slug
    parts = slug.split("-")
    if len(parts) > 3 and parts[0].isdigit():
        rest = "-".join(parts[3:])
    return rest.replace("-", " ").strip().capitalize() or slug


def _fmt_dt(iso_str: str) -> datetime | None:
    return planner.parse_dt(iso_str) if iso_str else None


def _day_header(d) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day:02d}. {MONTHS[d.month]} {d.year}"


def _channel_criteria_lines(ch: dict) -> list[str]:
    """Die aktuellen Kanal-Kriterien als lesbarer Block (aus channels.yaml)."""
    text = ch.get("text") or {}
    media = ch.get("media") or {}
    cad = ch.get("cadence") or {}
    ht = text.get("hashtags") or {}

    max_chars = text.get("max_chars")
    soft = text.get("soft_max_chars")
    zeichen = f"max. {max_chars} Zeichen" if max_chars else "–"
    if soft:
        zeichen += f" (optimal ≈ {soft})"

    ht_line = "keine" if (ht.get("max") in (0, None)) else \
        f"{ht.get('min', 0)}–{ht.get('max')} ({ht.get('style', 'camel')})"

    link_pos = {
        "end": "Link am Ende",
        "first_comment": "Link im ersten Kommentar",
        "none": "kein klickbarer Link",
    }.get(text.get("link_position"), text.get("link_position") or "–")

    bild = "Pflicht" if media.get("required") else ("möglich" if media.get("supported") else "aus")
    if media.get("variant"):
        bild += f" · Format {media.get('variant')}"

    times = ", ".join(cad.get("times") or []) or "–"
    days = cad.get("days") or []
    tage = "täglich" if sorted(days) == [0, 1, 2, 3, 4, 5, 6] else \
        (", ".join(WEEKDAYS[d] for d in days) if days else "–")
    freq = cad.get("max_per_day")
    cooldown = cad.get("recycle_cooldown_days")

    lines = [
        "> **Kanal-Kriterien (verbindlich, aus dem Playbook):**  ",
        f"> Text: {zeichen} · Hashtags: {ht_line} · Emojis max. {text.get('emoji_max', 0)}  ",
        f"> Link: {link_pos} · Bild: {bild}  ",
        f"> Sendetage: {tage} · Uhrzeiten: {times} · max. {freq}/Tag  ",
        f"> Evergreen-Sperrfrist: {cooldown} Tage",
    ]
    return lines


# ------------------------------------------------------------------- Sammeln
def _items_for(channel_id: str, schedule: dict) -> list[dict]:
    items = [it for it in (schedule.get("items") or [])
             if (it.get("channel") == channel_id)]
    items.sort(key=lambda it: it.get("scheduled_at") or it.get("date") or "")
    return items


def _history_for(channel_id: str, state: dict) -> list[dict]:
    hist = [h for h in (state.get("history") or []) if h.get("channel") == channel_id]
    hist.sort(key=lambda h: h.get("posted_at") or "")
    return hist


# ------------------------------------------------------------------- Markdown
def build_channel_md(channel_id: str, ch: dict, schedule: dict, state: dict,
                     titles: dict[str, str], urls: dict[str, str],
                     now: datetime) -> str:
    label = ch.get("label") or channel_id
    profile = ch.get("profile") or ""
    enabled = ch.get("enabled", True)

    lines = [
        f"# 🗓️ Veröffentlichungskalender – {label}",
        "",
        f"> Automatisch aktualisiert: {now:%d.%m.%Y %H:%M} (Europe/Berlin)"
        f"{'' if enabled else ' · Kanal in channels.yaml deaktiviert'}  ",
    ]
    if profile:
        lines.append(f"> Profil: {profile}  ")
    lines.append(f"> Zum Abonnieren im Handy/Outlook/Google-Kalender: `{channel_id}.ics`")
    lines.append("")
    lines += _channel_criteria_lines(ch)
    lines.append("")

    items = _items_for(channel_id, schedule)

    # Kommende (geplant / heute+) nach Tag gruppieren
    upcoming = []
    for it in items:
        dt = _fmt_dt(it.get("scheduled_at") or "")
        if dt is None:
            continue
        if it.get("status") in ("planned", "standby") and dt >= now - timedelta(hours=6):
            upcoming.append((dt, it))
    upcoming.sort(key=lambda t: t[0])

    lines.append("## Kommende Beiträge")
    lines.append("")
    if not upcoming:
        lines.append("_Aktuell nichts eingeplant – der Autopilot füllt den Plan beim nächsten Lauf._")
        lines.append("")
    else:
        cur_day = None
        for dt, it in upcoming:
            day = dt.date()
            if day != cur_day:
                cur_day = day
                lines.append(f"### {_day_header(dt)}")
            slug = it.get("slug") or ""
            title = _pretty_slug(slug, titles)
            url = urls.get(slug) or ""
            em = _emoji(it.get("status"))
            angle = it.get("angle") or ""
            kind = it.get("kind") or ""
            kind_tag = " · Launch" if kind == "launch" else (" · Evergreen" if kind else "")
            line = f"- **{dt:%H:%M}** {em} {title} — _{angle}_{kind_tag}"
            if url:
                line += f"  \n  {url}"
            elif it.get("status") == "standby":
                line += "  \n  ⚪ wartet auf Zugangsdaten (Secret fehlt)"
            lines.append(line)
        lines.append("")

    # Zuletzt veröffentlicht (aus dem Sende-Stand)
    hist = _history_for(channel_id, state)[-10:][::-1]
    lines.append("## Zuletzt veröffentlicht")
    lines.append("")
    if not hist:
        lines.append("_Noch nichts über diesen Kanal versendet._")
        lines.append("")
    else:
        for h in hist:
            dt = _fmt_dt(h.get("posted_at") or "")
            when = f"{dt:%d.%m.%Y %H:%M}" if dt else (h.get("posted_at") or "")[:16]
            slug = h.get("slug") or ""
            title = h.get("title") or _pretty_slug(slug, titles)
            url = h.get("url") or urls.get(slug) or ""
            tail = f" → {url}" if url and url.startswith("http") else ""
            lines.append(f"- ✅ {when} · {title}{tail}")
        lines.append("")

    # Blockaden / Standby als ehrlicher Hinweis
    blocked = [it for it in items if it.get("status") in ("blocked", "failed")]
    if blocked:
        lines.append("## Zurückgestellt (Autopilot hat blockiert)")
        lines.append("")
        for it in blocked[-8:]:
            dt = _fmt_dt(it.get("scheduled_at") or "")
            when = f"{dt:%d.%m. %H:%M}" if dt else it.get("date") or ""
            reason = it.get("reason") or "ohne Angabe"
            lines.append(f"- 🚫 {when} · {_pretty_slug(it.get('slug') or '', titles)} · {reason}")
        lines.append("")

    lines += [
        "---",
        "*Erzeugt von `scripts/social_calendar.py` aus dem versionierten Plan "
        "`data/social/schedule.yaml`. Der Plan selbst kommt vom Social-Autopilot "
        "(`scripts/social_studio.py`). Regeln: `data/social/channels.yaml`.*",
    ]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------- ICS
def _ics_dt(dt: datetime) -> str:
    """Als UTC (…Z) – robust in allen Kalender-Apps."""
    u = dt.astimezone(planner.timezone.utc) if dt.tzinfo else dt
    return u.strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;") \
                    .replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """ICS: Zeilen auf 75 Oktette falten."""
    out = []
    while len(line.encode("utf-8")) > 73:
        # grob nach Zeichen schneiden (ausreichend für unsere Inhalte)
        cut = 70
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)


def build_channel_ics(channel_id: str, ch: dict, schedule: dict,
                      titles: dict[str, str], urls: dict[str, str],
                      now: datetime) -> str:
    label = ch.get("label") or channel_id
    ev = []
    for it in _items_for(channel_id, schedule):
        dt = _fmt_dt(it.get("scheduled_at") or "")
        if dt is None:
            continue
        status = it.get("status")
        if status not in ("planned", "published", "standby"):
            continue
        slug = it.get("slug") or ""
        title = _pretty_slug(slug, titles)
        url = urls.get(slug) or ""
        uid = (it.get("id") or f"{channel_id}:{slug}:{it.get('angle')}") \
            .replace(" ", "_") + "@franksfinanzcheck.de"
        summary = f"{label}: {title} ({it.get('angle') or ''})"
        desc_bits = [
            f"Status: {_status_text(status)}",
            f"Winkel: {it.get('angle') or '-'}",
            f"Kanal: {label}",
        ]
        if url:
            desc_bits.append(f"Artikel: {url}")
        end = dt + timedelta(minutes=15)
        ev.append("\r\n".join([
            "BEGIN:VEVENT",
            _fold(f"UID:{uid}"),
            f"DTSTAMP:{_ics_dt(now)}",
            f"DTSTART:{_ics_dt(dt)}",
            f"DTEND:{_ics_dt(end)}",
            _fold(f"SUMMARY:{_ics_escape(summary)}"),
            _fold(f"DESCRIPTION:{_ics_escape(chr(10).join(desc_bits))}"),
            _fold(f"URL:{url}") if url else "",
            f"STATUS:{'CONFIRMED' if status == 'published' else 'TENTATIVE'}",
            "END:VEVENT",
        ]).replace("\r\n\r\n", "\r\n"))

    head = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FranksFinanzcheck//Social-Autopilot Kalender//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        _fold(f"X-WR-CALNAME:FranksFinanzcheck – {label}"),
        "X-WR-TIMEZONE:Europe/Berlin",
    ]
    return "\r\n".join(head + ev + ["END:VCALENDAR"]) + "\r\n"


# ------------------------------------------------------------------ Video-Kal
def _load_video_cal(now: datetime, titles: dict[str, str]) -> tuple[list[str], list[str]]:
    """Kalender-Zeilen + ICS-Events für die Shorts-Schmiede (Reels/Shorts)."""
    import yaml
    if not os.path.exists(VIDEO_FILE):
        return [], []
    try:
        vcfg = yaml.safe_load(open(VIDEO_FILE, encoding="utf-8")) or {}
    except Exception:
        return [], []
    kanaele = vcfg.get("kanaele") or {}
    aktive = [v.get("label") or k for k, v in kanaele.items() if v.get("aktiv")]

    # Produziert bislang (aus video_state.yaml)
    produziert = []
    if os.path.exists(VIDEO_STATE_FILE):
        try:
            vs = yaml.safe_load(open(VIDEO_STATE_FILE, encoding="utf-8")) or {}
            produziert = vs.get("produziert") or []
        except Exception:
            produziert = []

    md = [
        "# 🎬 Veröffentlichungskalender – Reels · Shorts · Video",
        "",
        f"> Automatisch aktualisiert: {now:%d.%m.%Y %H:%M} (Europe/Berlin)  ",
        f"> Aktive Ziel-Plattformen: {', '.join(aktive) or '–'}  ",
        "> Zum Abonnieren: `video.ics`",
        "",
        "> **Format-Kriterien (verbindlich, aus video.yaml):**  ",
        "> 9:16 · 1080×1920 · 24–52 s · Untertitel eingebrannt · "
        "Pflichthinweis „keine Anlageberatung“ · keine Musik",
        "",
        "## Produktionsrhythmus",
        "",
        "- **Dienstag & Samstag, 07:20 (MESZ)** — die Shorts-Schmiede baut "
        "je Lauf bis zu 2 Videos aus jungen Artikeln und lädt sie hoch "
        "(YouTube Shorts / Instagram Reels), sobald der Zugang steht.",
        "",
        "## Nächste Produktionstermine",
        "",
    ]
    ics = []
    # nächste 6 Di/Sa-Termine
    count = 0
    d = now
    while count < 6:
        d = d + timedelta(days=1)
        if d.weekday() in (1, 5):  # Di, Sa
            slot = d.replace(hour=7, minute=20, second=0, microsecond=0)
            md.append(f"- 🎬 {_day_header(slot)} · 07:20 — Shorts-Produktion "
                      f"(bis zu 2 Videos)")
            uid = f"video-{slot:%Y%m%d}@franksfinanzcheck.de"
            end = slot + timedelta(minutes=45)
            ics.append("\r\n".join([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{_ics_dt(now)}",
                f"DTSTART:{_ics_dt(slot)}",
                f"DTEND:{_ics_dt(end)}",
                "SUMMARY:Shorts-Schmiede: Reels & Shorts produzieren",
                _fold("DESCRIPTION:Bis zu 2 vertikale Kurzvideos (9:16) aus "
                      "jungen Artikeln\\, Upload auf YouTube Shorts / Instagram Reels."),
                "STATUS:TENTATIVE",
                "RRULE:FREQ=WEEKLY;BYDAY=TU,SA;COUNT=1",
                "END:VEVENT",
            ]))
            count += 1
    md.append("")

    if produziert:
        md += ["## Zuletzt produziert", ""]
        for p in produziert[-8:][::-1]:
            if isinstance(p, dict):
                slug = p.get("slug") or ""
                when = (p.get("erstellt") or p.get("datum") or "")[:16]
                md.append(f"- ✅ {when} · {_pretty_slug(slug, titles)}")
            else:
                md.append(f"- ✅ {p}")
        md.append("")

    md += [
        "---",
        "*Erzeugt von `scripts/social_calendar.py`. Regie: `data/social/video.yaml` · "
        "Produktion: `scripts/social_video.py` (Workflow „Shorts-Schmiede“).*",
    ]

    head = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FranksFinanzcheck//Shorts-Schmiede Kalender//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:FranksFinanzcheck – Reels & Shorts",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]
    ics_full = "\r\n".join(head + ics + ["END:VCALENDAR"]) + "\r\n"
    return md, [ics_full]


# -------------------------------------------------------------------- Übersicht
def build_overview(cfg: dict, schedule: dict, state: dict,
                   titles: dict[str, str], urls: dict[str, str],
                   now: datetime) -> str:
    cmap = sch.channel_map(cfg)
    lines = [
        "# 🗓️ Social-Media-Veröffentlichungskalender – Übersicht",
        "",
        f"> Automatisch aktualisiert: {now:%d.%m.%Y %H:%M} (Europe/Berlin)",
        "",
        "Für **jeden Kanal** gibt es hier einen eigenen, laufend aktualisierten "
        "Veröffentlichungskalender – als lesbare Markdown-Datei und als "
        "abonnierbare `.ics`-Datei fürs Handy, Outlook, Google- oder Apple-Kalender.",
        "",
        "## Kanäle",
        "",
        "| Kanal | Status | Geplant | Nächster Beitrag | Kalender |",
        "|---|---|---:|---|---|",
    ]

    for cid, ch in sorted(cmap.items(), key=lambda kv: kv[1].get("priority", 99)):
        items = _items_for(cid, schedule)
        planned = [it for it in items if it.get("status") == "planned"]
        standby = [it for it in items if it.get("status") == "standby"]
        missing = sch.missing_env(ch)
        enabled = ch.get("enabled", True)
        if not enabled:
            status = "⚫ aus"
        elif missing:
            status = "⚪ Standby"
        else:
            status = "🟢 aktiv"
        # nächster geplanter Beitrag
        nxt = "–"
        fut = sorted(
            [it for it in (planned + standby)
             if (_fmt_dt(it.get("scheduled_at") or "") or now) >= now - timedelta(hours=6)],
            key=lambda it: it.get("scheduled_at") or "")
        if fut:
            dt = _fmt_dt(fut[0].get("scheduled_at") or "")
            when = f"{WEEKDAYS[dt.weekday()]} {dt:%d.%m. %H:%M}" if dt else "?"
            nxt = f"{when} · {_pretty_slug(fut[0].get('slug') or '', titles)[:32]}"
        label = ch.get("label") or cid
        lines.append(
            f"| {label} | {status} | {len(planned)} | {nxt} | "
            f"[md]({cid}.md) · [ics]({cid}.ics) |")

    # Video-Zeile
    lines.append("| 🎬 Reels & Shorts | 🟢 aktiv | Di+Sa | Nächste Produktion | "
                 "[md](video.md) · [ics](video.ics) |")

    # Zusammengeführte Timeline der nächsten 14 Tage über alle Kanäle
    lines += ["", "## Nächste 14 Tage – alle Kanäle zusammen", ""]
    merged = []
    for cid, ch in cmap.items():
        for it in _items_for(cid, schedule):
            dt = _fmt_dt(it.get("scheduled_at") or "")
            if dt is None or it.get("status") not in ("planned", "standby"):
                continue
            if now - timedelta(hours=6) <= dt <= now + timedelta(days=14):
                merged.append((dt, cid, ch, it))
    merged.sort(key=lambda t: t[0])
    if not merged:
        lines.append("_Der Plan ist gerade leer – der Autopilot füllt ihn beim nächsten Lauf._")
    else:
        cur_day = None
        for dt, cid, ch, it in merged:
            day = dt.date()
            if day != cur_day:
                cur_day = day
                lines.append(f"### {_day_header(dt)}")
            em = _emoji(it.get("status"))
            label = ch.get("label") or cid
            lines.append(f"- **{dt:%H:%M}** {em} {label} · "
                         f"_{it.get('angle') or ''}_ · "
                         f"{_pretty_slug(it.get('slug') or '', titles)}")
    lines += [
        "",
        "---",
        "*Legende: ⏳ geplant · ✅ veröffentlicht · ⚪ Standby (Zugang fehlt) · "
        "🚫 zurückgestellt.*  ",
        "*Erzeugt von `scripts/social_calendar.py`.*",
    ]
    return "\n".join(lines) + "\n"


def build_index_html(cfg: dict, base_url: str, now: datetime) -> str:
    """Öffentliche Abo-Seite unter /kalender/ – ein Feed-Link je Kanal."""
    cmap = sch.channel_map(cfg)
    host = base_url.replace("https://", "").replace("http://", "").rstrip("/")

    def _card(cid: str, label: str) -> str:
        ics_https = f"{base_url.rstrip('/')}/kalender/{cid}.ics"
        ics_webcal = f"webcal://{host}/kalender/{cid}.ics"
        # Google „per URL abonnieren“ nimmt die HTTPS-Adresse entgegen.
        google = ("https://calendar.google.com/calendar/r/settings/addbyurl"
                  f"?cid={ics_https}")
        return f"""      <article class="card">
        <h3>{label}</h3>
        <div class="btns">
          <a class="btn primary" href="{ics_webcal}">Abonnieren (Apple · Outlook)</a>
          <a class="btn" href="{google}" target="_blank" rel="noopener">Google Kalender</a>
          <a class="btn ghost" href="{ics_https}" download>.ics laden</a>
        </div>
        <p class="url"><code>{ics_https}</code></p>
      </article>"""

    cards = [_card(cid, ch.get("label") or cid)
             for cid, ch in sorted(cmap.items(),
                                   key=lambda kv: kv[1].get("priority", 99))]
    cards.append(_card("video", "🎬 Reels &amp; Shorts"))

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, follow">
<title>Veröffentlichungskalender · FranksFinanzcheck</title>
<style>
  :root {{ --bg:#0E1B2A; --card:#132538; --gold:#E9B44C; --text:#F4F7FB; --muted:#9DB0C6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
         font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:920px; margin:0 auto; padding:2.5rem 1.25rem 4rem; }}
  h1 {{ font-size:1.8rem; margin:0 0 .3rem; }}
  .lead {{ color:var(--muted); margin:0 0 2rem; }}
  .grid {{ display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); }}
  .card {{ background:var(--card); border:1px solid #20344b; border-radius:14px; padding:1.1rem 1.2rem; }}
  .card h3 {{ margin:0 0 .8rem; font-size:1.15rem; }}
  .btns {{ display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:.7rem; }}
  .btn {{ display:inline-block; padding:.45rem .7rem; border-radius:9px; text-decoration:none;
          font-size:.86rem; border:1px solid #2d445f; color:var(--text); }}
  .btn.primary {{ background:var(--gold); color:#20160a; border-color:var(--gold); font-weight:600; }}
  .btn.ghost {{ color:var(--muted); }}
  .url code {{ color:var(--muted); font-size:.72rem; word-break:break-all; }}
  .note {{ margin-top:2.2rem; color:var(--muted); font-size:.9rem; border-top:1px solid #20344b; padding-top:1.2rem; }}
  a {{ color:var(--gold); }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>🗓️ Veröffentlichungskalender</h1>
    <p class="lead">Für jeden Social-Media-Kanal ein eigener, automatisch
      aktualisierter Kalender. Einmal abonnieren – dann erscheinen alle geplanten
      Beiträge von selbst in deinem Kalender. Stand: {now:%d.%m.%Y}.</p>
    <div class="grid">
{chr(10).join(cards)}
    </div>
    <p class="note">
      <strong>So geht Abonnieren:</strong><br>
      · <strong>iPhone / Mac / Outlook:</strong> auf „Abonnieren“ tippen – die
        <code>webcal://</code>-Adresse öffnet direkt die Kalender-App.<br>
      · <strong>Google Kalender:</strong> auf „Google Kalender“ klicken und die
        vorbefüllte Adresse bestätigen (Andere Kalender → Per URL).<br>
      Die Feeds werden nach jedem Autopilot-Lauf neu erzeugt und aktualisieren
      sich im Abo automatisch. Erzeugt von <code>scripts/social_calendar.py</code>.
    </p>
  </div>
</body>
</html>
"""


def _readme() -> str:
    return (
        "# Social-Media-Veröffentlichungskalender\n\n"
        "Dieser Ordner enthält für **jeden Social-Media-Kanal** einen eigenen, "
        "automatisch aktualisierten Veröffentlichungskalender.\n\n"
        "- **`UEBERSICHT.md`** – alle Kanäle auf einen Blick + gemeinsame 14-Tage-Timeline.\n"
        "- **`<kanal>.md`** – lesbarer Kalender eines Kanals (kommende & vergangene Beiträge, "
        "inkl. der verbindlichen Kanal-Kriterien).\n"
        "- **`<kanal>.ics`** – denselben Kalender **abonnieren**: Link/Datei in Google "
        "Kalender, Apple Kalender oder Outlook hinzufügen, dann erscheinen alle geplanten "
        "Posts automatisch in deinem Kalender.\n"
        "- **`video.md` / `video.ics`** – Produktionsrhythmus für Reels & Shorts.\n\n"
        "## Öffentlich abonnieren\n\n"
        "Die Feeds werden zusätzlich nach `static/kalender/` gespiegelt und sind "
        "nach dem nächsten Deploy live unter:\n\n"
        "- Abo-Seite: `https://franksfinanzcheck.de/kalender/`\n"
        "- Einzelfeed: `https://franksfinanzcheck.de/kalender/<kanal>.ics` "
        "(bzw. `webcal://franksfinanzcheck.de/kalender/<kanal>.ics` fürs Ein-Klick-Abo).\n\n"
        "## Woher die Termine kommen\n\n"
        "Die Kalender werden **nicht von Hand gepflegt**. Sie werden aus dem versionierten "
        "Redaktionsplan `data/social/schedule.yaml` erzeugt, den der Social-Autopilot "
        "(`scripts/social_studio.py`) alle 2 Stunden fortschreibt. Nach jedem Lauf werden "
        "diese Kalender neu geschrieben – du musst dich um nichts kümmern.\n\n"
        "## Selbst neu erzeugen\n\n"
        "```bash\npython3 scripts/social_calendar.py --build\n```\n"
    )


# --------------------------------------------------------------------- Build
def build_all(only_channel: str | None = None, now: datetime | None = None) -> dict:
    now = now or planner.berlin_now()
    cfg = sch.load_config()
    if not cfg:
        raise SystemExit("channels.yaml fehlt oder ist leer")
    schedule = planner.load_schedule()
    state = planner.load_state()
    titles = _title_map()
    urls = _url_map()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    base_url = str(sch.meta_of(cfg).get("base_url") or "https://franksfinanzcheck.de")
    written = []
    cmap = sch.channel_map(cfg)
    for cid, ch in cmap.items():
        if only_channel and cid != only_channel:
            continue
        md = build_channel_md(cid, ch, schedule, state, titles, urls, now)
        ics = build_channel_ics(cid, ch, schedule, titles, urls, now)
        with open(os.path.join(OUT_DIR, f"{cid}.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(OUT_DIR, f"{cid}.ics"), "w", encoding="utf-8") as fh:
            fh.write(ics)
        # öffentlich abonnierbare Kopie unter /kalender/<kanal>.ics
        with open(os.path.join(STATIC_DIR, f"{cid}.ics"), "w", encoding="utf-8") as fh:
            fh.write(ics)
        written += [f"{cid}.md", f"{cid}.ics"]

    if not only_channel or only_channel == "video":
        vmd, vics = _load_video_cal(now, titles)
        if vmd:
            with open(os.path.join(OUT_DIR, "video.md"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(vmd) + "\n")
            written.append("video.md")
        if vics:
            with open(os.path.join(OUT_DIR, "video.ics"), "w", encoding="utf-8") as fh:
                fh.write(vics[0])
            with open(os.path.join(STATIC_DIR, "video.ics"), "w", encoding="utf-8") as fh:
                fh.write(vics[0])
            written.append("video.ics")

    if not only_channel:
        overview = build_overview(cfg, schedule, state, titles, urls, now)
        with open(os.path.join(OUT_DIR, "UEBERSICHT.md"), "w", encoding="utf-8") as fh:
            fh.write(overview)
        with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as fh:
            fh.write(_readme())
        # öffentliche Abo-Landingpage unter /kalender/
        index_html = build_index_html(cfg, base_url, now)
        with open(os.path.join(STATIC_DIR, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(index_html)
        written += ["UEBERSICHT.md", "README.md", "static/kalender/index.html"]

    return {"written": written, "channels": list(cmap.keys())}


# ------------------------------------------------------------------- Selftest
def selftest() -> int:
    """Fail-closed: prüft, dass Kalender & ICS aus Testdaten valide entstehen."""
    fails = []
    now = planner.localize(datetime(2026, 9, 29, 9, 0))

    ch = {
        "label": "Testkanal", "enabled": True, "priority": 1,
        "text": {"max_chars": 300, "hashtags": {"min": 1, "max": 2},
                 "emoji_max": 1, "link_position": "end"},
        "media": {"supported": True, "required": False},
        "cadence": {"days": [0, 1, 2, 3, 4, 5, 6], "times": ["08:00"],
                    "max_per_day": 2, "recycle_cooldown_days": 75},
    }
    schedule = {"items": [
        {"id": "t:slug-a:nutzen:2026-09-30", "channel": "test",
         "slug": "2026-09-11-test-artikel", "angle": "nutzen", "kind": "launch",
         "date": "2026-09-30", "time": "08:00",
         "scheduled_at": "2026-09-30T08:00:00+02:00", "status": "planned"},
        {"id": "t:slug-b:zahl:2026-09-25", "channel": "test",
         "slug": "2026-09-11-test-artikel", "angle": "zahl", "kind": "launch",
         "date": "2026-09-25", "time": "08:00",
         "scheduled_at": "2026-09-25T08:00:00+02:00", "status": "blocked",
         "reason": "Testblock"},
    ]}
    state = {"history": [
        {"posted_at": "2026-09-20T08:00:00+02:00", "channel": "test",
         "slug": "2026-09-11-test-artikel", "title": "Test", "url": "https://x/y/"},
    ]}

    md = build_channel_md("test", ch, schedule, state, {}, {}, now)
    if "Kommende Beiträge" not in md:
        fails.append("MD ohne Abschnitt 'Kommende Beiträge'")
    if "Kanal-Kriterien" not in md:
        fails.append("MD ohne Kriterien-Block")
    if "08:00" not in md:
        fails.append("MD ohne geplante Uhrzeit")

    ics = build_channel_ics("test", ch, schedule, {}, {}, now)
    if not ics.startswith("BEGIN:VCALENDAR"):
        fails.append("ICS-Kopf fehlt")
    if "END:VCALENDAR" not in ics:
        fails.append("ICS-Ende fehlt")
    if ics.count("BEGIN:VEVENT") != 1:
        fails.append(f"ICS erwartet 1 Event (nur 'planned'), hat {ics.count('BEGIN:VEVENT')}")
    if "DTSTART:20260930T060000Z" not in ics:
        fails.append("ICS DTSTART nicht als UTC (+02:00 → 06:00Z) umgerechnet")

    # ICS-Zeilenlänge (grobe RFC-5545-Faltung)
    for ln in ics.split("\r\n"):
        if len(ln.encode("utf-8")) > 75:
            fails.append(f"ICS-Zeile > 75 Oktette: {ln[:40]}…")
            break

    vmd, vics = _load_video_cal(now, {})
    # video.yaml existiert im Repo → Kalender sollte kommen; wenn nicht, kein harter Fehler
    if os.path.exists(VIDEO_FILE) and not vmd:
        fails.append("Video-Kalender konnte trotz video.yaml nicht erzeugt werden")

    # Öffentliche Abo-Seite baubar und mit Live-URLs versehen?
    try:
        cfg = sch.load_config()
        html = build_index_html(cfg, "https://franksfinanzcheck.de", now)
        if "webcal://franksfinanzcheck.de/kalender/" not in html:
            fails.append("Abo-Seite ohne webcal-Feed-Link")
        if "https://franksfinanzcheck.de/kalender/" not in html:
            fails.append("Abo-Seite ohne HTTPS-Feed-URL")
        if "considerable" in html:
            fails.append("Abo-Seite enthält kaputtes CSS")
    except Exception as exc:  # pragma: no cover
        fails.append(f"Abo-Seite nicht baubar: {exc}")

    if fails:
        print("❌ Selftest fehlgeschlagen:")
        for f in fails:
            print("   -", f)
        return 1
    print("✅ Selbsttest bestanden – Kalender & ICS werden korrekt erzeugt.")
    return 0


# ------------------------------------------------------------------------ CLI
def main() -> int:
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()

    only = None
    if "--channel" in argv:
        i = argv.index("--channel")
        if i + 1 < len(argv):
            only = argv[i + 1]

    res = build_all(only_channel=only)
    print(f"🗓️  Kalender geschrieben: {len(res['written'])} Dateien in "
          f"data/social/kalender/")
    for name in res["written"]:
        print("   ·", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
