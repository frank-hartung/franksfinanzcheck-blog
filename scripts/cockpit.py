#!/usr/bin/env python3
"""
COCKPIT – eine Ampel-Seite statt 70+ Status-Dateien
====================================================

WARUM (Frank, 03.10.2026): Der Blog hat für jede neue Automation eine
eigene *-STATUS.md/-REPORT.md bekommen – inzwischen über 70 Dateien im
Projekt-Root. Jede einzelne ist für sich genommen richtig und wichtig
(Nachvollziehbarkeit!), aber niemand liest morgens 70 Dateien durch, um
zu wissen: „Brennt irgendwo was?" Das Cockpit beantwortet GENAU diese
eine Frage, pro Bereich, in einer Zeile.

GRUNDPRINZIP – NUR SPIEGELN, NIE NEU MESSEN:
  Dieses Skript erzeugt KEINE neuen Messdaten, ruft KEIN Netz auf und
  dupliziert KEINE Prüflogik. Es liest ausschließlich bereits von
  anderen Wachen geschriebene Zustandsdateien (SSOT bleibt SSOT):

    data/governance_status.json   – Content/SEO/Build/Affiliate/Secrets
                                     (scripts/governance_contract.py,
                                     governance_gate.py, deploy_drift_guard.py)
    data/reserve-readiness.json   – Artikel-Vorrat (scripts/bot_watchdog.py)
    data/secrets_state.json       – welche Zugänge live geprüft sind
    data/social/channels.yaml     – welche Social-Kanäle existieren/aktiv sind
    data/social/state.yaml        – Post-Historie + Fehlversuche (Social)
    data/newsletter_journal.jsonl – echte Versand-Ereignisse (Newsletter)
    data/newsletter_state.json    – Warteschlange unversendeter Artikel

  Fehlt eine Quelle oder ist sie nicht lesbar, zeigt der betroffene
  Bereich ⚪ „keine Daten" statt abzustürzen oder einen Fehlalarm zu
  erzeugen (Standby ≠ Fehler – wie überall sonst im Repo).

AMPEL-LOGIK (pro Bereich, Details in den jeweiligen bucket_*-Funktionen):
  🔴 rot   – etwas blockiert Umsatz/Sichtbarkeit/Vertrauen, Handeln nötig
  🟡 gelb  – Rückstand oder einzelner Defekt, aber nicht akut
  🟢 grün  – im Rahmen der Erwartung
  ⚪ grau  – (noch) keine Daten / bewusster Standby (z. B. Kanal ohne Token)
  Die Gesamtampel ist die schlechteste Einzelampel (grau zählt nicht als
  schlecht – ein Blog ohne Umami-Daten ist nicht „kaputt").

AUSGABE:
  COCKPIT.md               – die eine Seite zum täglichen Lesen
  data/cockpit_status.json – maschinenlesbar (für den Telegram-Alarm
                              und für andere Wachen, die mitlesen wollen)

NICHT GEMACHT (bewusst, Scope-Grenze):
  * Kein Ersatz für die Einzel-Reports – die bleiben (Prüfbarkeit,
    Historie). Das Cockpit ist der Index, nicht das Archiv.
  * Kein eigener Alarmkanal – ein roter Gesamtbefund nutzt den
    bestehenden Telegram-Weg (wie PRODUKTIONS-STATUS.md/-wache.yml).

Nutzung:
  python3 scripts/cockpit.py              # schreibt COCKPIT.md + JSON
  python3 scripts/cockpit.py --print      # zusätzlich auf stdout
  python3 scripts/cockpit.py --selftest   # eingefrorene Fälle (Regression)

Exit-Codes: 0 immer (das Cockpit ist eine Übersicht, kein Gate) –
            außer --selftest: 0 ok, 2 Selftest fehlgeschlagen.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GOVERNANCE_PATH = os.path.join(BLOG_DIR, "data", "governance_status.json")
RESERVE_PATH = os.path.join(BLOG_DIR, "data", "reserve-readiness.json")
SECRETS_PATH = os.path.join(BLOG_DIR, "data", "secrets_state.json")
SOCIAL_CHANNELS_PATH = os.path.join(BLOG_DIR, "data", "social", "channels.yaml")
SOCIAL_STATE_PATH = os.path.join(BLOG_DIR, "data", "social", "state.yaml")
NEWSLETTER_JOURNAL_PATH = os.path.join(BLOG_DIR, "data", "newsletter_journal.jsonl")
NEWSLETTER_STATE_PATH = os.path.join(BLOG_DIR, "data", "newsletter_state.json")

OUT_MD_PATH = os.path.join(BLOG_DIR, "COCKPIT.md")
OUT_JSON_PATH = os.path.join(BLOG_DIR, "data", "cockpit_status.json")

LEVEL_RANK = {"grau": 0, "gruen": 1, "gelb": 2, "rot": 3}
LEVEL_EMOJI = {"grau": "⚪", "gruen": "🟢", "gelb": "🟡", "rot": "🔴"}
LEVEL_WORT = {"grau": "keine Daten", "gruen": "GRÜN", "gelb": "GELB", "rot": "ROT"}


# ------------------------------------------------------------ Hilfsfunktionen


def worst(levels):
    """Die schlechteste Ampel aus einer Liste (grau zählt nicht als schlecht)."""
    levels = list(levels)
    if not levels:
        return "grau"
    return max(levels, key=lambda l: LEVEL_RANK.get(l, 0))


def _level_from_governance(level: str) -> str:
    return {
        "green": "gruen", "ok": "gruen",
        "amber": "gelb", "orange": "gelb", "yellow": "gelb",
        "red": "rot",
        "info": "grau",
    }.get(str(level).lower(), "grau")


def _parse_ts(value):
    """Robustes ISO-Parsing (mit/ohne 'Z', mit/ohne Offset, ohne tz -> UTC)."""
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _hours_since(ts, now):
    if ts is None:
        return None
    return (now - ts).total_seconds() / 3600.0


def _slug_date(slug: str):
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", slug or "")
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def _load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default if default is not None else {}


def _load_jsonl(path):
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows


def _short(msg: str, limit: int = 170) -> str:
    """Eine Zeile, auf vernünftige Länge gekürzt (für Tabellen/Bullets)."""
    msg = re.sub(r"\s+", " ", msg or "").strip()
    if len(msg) <= limit:
        return msg
    return msg[: limit - 1].rstrip() + "…"


def _load_yaml(path, default=None):
    try:
        import yaml  # lokal importiert: nicht jede Umgebung braucht PyYAML
    except ImportError:
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, ValueError):
        return default if default is not None else {}
    return data if data is not None else (default if default is not None else {})


# ------------------------------------------------------------ Bereiche (Buckets)
#
# Jede bucket_*-Funktion bekommt bereits geladene Daten (nie Pfade) – das
# macht sie ohne Dateisystem/Netz testbar (siehe selftest()).


def bucket_content(governance: dict, reserve: dict):
    steps = governance.get("steps", {}) or {}
    keys = ["lesbarkeit", "decay", "scorecard", "automation"]
    present = [steps[k] for k in keys if k in steps]
    lvl = worst(_level_from_governance(s.get("level")) for s in present)
    bad_keys = [
        k for k in keys
        if k in steps and str(steps[k].get("level", "")).lower() in ("red", "amber", "orange", "yellow")
    ]
    details = [f"{k}: {_short(steps[k].get('message', ''))}" for k in bad_keys]

    reserve_note = None
    ready = reserve.get("ready")
    target = reserve.get("target")
    if target:
        if ready is None:
            pass
        elif ready < target:
            lvl = worst([lvl, "rot" if ready == 0 else "gelb"])
            reserve_note = f"Artikel-Reserve knapp: {ready}/{target} bereit – Nachschub nötig"
        else:
            reserve_note = f"Artikel-Reserve {ready}/{target} bereit"

    if bad_keys:
        headline = f"{len(bad_keys)} Prüfpunkt(e) auffällig ({', '.join(bad_keys)})"
    else:
        headline = "Kern-Checks (Lesbarkeit/Decay/Scorecard/Automation) in Ordnung"
    if reserve_note and (ready or 0) < (target or 0):
        headline += f" · {reserve_note}"

    lines = [headline] + details
    if reserve_note:
        lines.append(reserve_note)
    return lvl, lines, [
        "data/governance_status.json", "data/reserve-readiness.json", "PRODUKTIONS-STATUS.md",
    ]


def bucket_seo(governance: dict):
    steps = governance.get("steps", {}) or {}
    keys = ["cwv", "build", "live-policy", "umami", "umami-views"]
    present = [steps[k] for k in keys if k in steps]
    lvl = worst(_level_from_governance(s.get("level")) for s in present)
    bad_keys = [
        k for k in keys
        if k in steps and str(steps[k].get("level", "")).lower() in ("red", "amber", "orange", "yellow")
    ]
    details = [f"{k}: {_short(steps[k].get('message', ''))}" for k in bad_keys]
    info_only = [k for k in ("umami", "umami-views") if k in steps and str(steps[k].get("level")).lower() == "info"]

    if bad_keys:
        headline = f"{len(bad_keys)} Prüfpunkt(e) auffällig ({', '.join(bad_keys)})"
    elif info_only:
        headline = "Kernwerte (CWV/Build/Live-Policy) in Ordnung; Umami-Daten noch nicht importiert (Standby)"
    else:
        headline = "in Ordnung"
    return lvl, [headline] + details, ["data/governance_status.json"]


def bucket_affiliate(governance: dict):
    steps = governance.get("steps", {}) or {}
    keys = ["click-chain", "revenue-funnel", "awin", "awin-fetch", "clicks", "pinperf"]
    present = [steps[k] for k in keys if k in steps]
    lvl = worst(_level_from_governance(s.get("level")) for s in present)
    bad_keys = [
        k for k in keys
        if k in steps and str(steps[k].get("level", "")).lower() in ("red", "amber", "orange", "yellow")
    ]
    details = [f"{k}: {_short(steps[k].get('message', ''))}" for k in bad_keys]
    info_count = sum(1 for k in keys if k in steps and str(steps[k].get("level")).lower() == "info")
    if bad_keys:
        headline = f"{len(bad_keys)} Prüfpunkt(e) auffällig ({', '.join(bad_keys)})"
    elif lvl == "gruen":
        headline = f"in Ordnung ({info_count} Kennzahl(en) noch ohne Datenlage)" if info_count else "in Ordnung"
    else:
        headline = f"noch keine Datenlage ({info_count} Kennzahl(en) offen)" if info_count else "keine Daten"
    return lvl, [headline] + details, [
        "data/governance_status.json", "AFFILIATE-INTEGRITY-REPORT.md", "AFFILIATE-INTENT-REPORT.md",
    ]


def bucket_secrets(governance: dict, secrets_state: dict):
    steps = governance.get("steps", {}) or {}
    gov_lvl = None
    detail = None
    if "secrets" in steps:
        gov_lvl = _level_from_governance(steps["secrets"].get("level"))
        if gov_lvl in ("rot", "gelb"):
            detail = _short(steps["secrets"].get("message", ""), 200)

    entries = secrets_state.get("entries", {}) or {}
    proven = sorted(n for n, s in entries.items() if s.get("quality") == "proven")
    dead = sorted(n for n, s in entries.items() if s.get("verify") == "dead")

    if dead:
        lvl = "rot"
    elif gov_lvl is not None:
        lvl = gov_lvl
    elif proven:
        lvl = "gruen"
    else:
        lvl = "grau"

    if dead:
        headline = f"{len(dead)} Zugang/Zugänge abgelehnt: {', '.join(dead)} – Re-Auth nötig"
    elif proven:
        headline = f"{len(proven)} geprüfte Zugänge live, keine Ausfälle"
    else:
        headline = "keine Secrets live geprüft"

    lines = [headline]
    if detail:
        lines.append(detail)
    if proven:
        lines.append(f"geprüft & lebendig: {', '.join(proven)}")
    if dead:
        lines.append(f"abgelehnt (Re-Auth nötig): {', '.join(dead)}")
    return lvl, lines, ["data/governance_status.json", "data/secrets_state.json", "docs/PINTEREST-TOKEN-RUNBOOK.md"]


def bucket_social(secrets_state: dict, channels_cfg: dict, social_state: dict, now: datetime.datetime):
    channels = channels_cfg.get("channels", {}) or {}
    entries = secrets_state.get("entries", {}) or {}

    live, standby, dead = [], [], []
    enabled_total = 0
    for key, cfg in channels.items():
        if not cfg.get("enabled"):
            continue
        enabled_total += 1
        label = cfg.get("label", key)
        needed = cfg.get("pflicht_env", []) or []
        states = [entries.get(s) for s in needed]
        if any(s and s.get("verify") == "dead" for s in states):
            dead.append(label)
        elif needed and all(s and s.get("quality") == "proven" for s in states):
            live.append(label)
        else:
            standby.append(label)

    history = social_state.get("history", []) or []
    oks = [h for h in history if h.get("ok")]
    last_ok = None
    for h in oks:
        ts = _parse_ts(h.get("posted_at"))
        if ts and (last_ok is None or ts > last_ok):
            last_ok = ts
    hours_since = _hours_since(last_ok, now)

    failures = social_state.get("failures", []) or []
    recent_failures = []
    for f in failures:
        ts = _parse_ts(f.get("at"))
        if ts is not None and _hours_since(ts, now) <= 24 * 14:
            recent_failures.append(f)

    if enabled_total == 0:
        lvl = "grau"
    elif not live:
        lvl = "rot"
    elif dead:
        lvl = "gelb"
    elif hours_since is None or hours_since > 120:
        lvl = "rot"
    elif hours_since > 48:
        lvl = "gelb"
    else:
        lvl = "gruen"

    lines = [f"{len(live)}/{enabled_total} Kanäle live" + (f" ({', '.join(live)})" if live else "")]
    if standby:
        lines.append(f"{len(standby)} im Standby ohne Zugangsdaten ({', '.join(standby)}) – docs/RUNBUCH-SOCIAL-SECRETS.md")
    if dead:
        lines.append(f"Token abgelehnt: {', '.join(dead)}")
    if hours_since is not None:
        lines.append(f"letzter erfolgreicher Post vor {hours_since / 24:.1f} Tag(en)")
    else:
        lines.append("noch kein erfolgreicher Post protokolliert")
    if recent_failures:
        lines.append(f"{len(recent_failures)} Fehlversuch(e) in den letzten 14 Tagen")

    return lvl, lines, [
        "data/social/state.yaml", "data/social/channels.yaml", "SOCIAL-PERF-REPORT.md",
        "docs/RUNBUCH-SOCIAL-SECRETS.md",
    ]


_REAL_SEND_AUSGABE_RE = re.compile(r"^(test-|selftest|bestaetigung|abmelde)")


def bucket_newsletter(journal_rows: list, state: dict, now: datetime.datetime):
    real_sends = [
        r for r in journal_rows
        if r.get("modus") == "sendefile"
        and r.get("status") == "zugestellt"
        and not _REAL_SEND_AUSGABE_RE.match(r.get("ausgabe", ""))
    ]
    last_real = None
    for r in real_sends:
        ts = _parse_ts(r.get("ts"))
        if ts and (last_real is None or ts > last_real):
            last_real = ts

    pending = state.get("pending", []) or []
    oldest_pending_days = None
    if pending:
        dates = [d for d in (_slug_date(s) for s in pending) if d]
        if dates:
            oldest_pending_days = (now.date() - min(dates)).days

    lines = []
    if last_real is None:
        lines.append("noch kein echter Listenversand protokolliert (nur Tests/Bestätigungen)")
        if oldest_pending_days is not None:
            lines.append(f"{len(pending)} Artikel in der Warteschlange, ältester {oldest_pending_days} Tag(e) alt")
            if oldest_pending_days >= 7:
                lvl = "rot"
            elif oldest_pending_days >= 3:
                lvl = "gelb"
            else:
                lvl = "grau"
        else:
            lvl = "grau"
            lines.append("Warteschlange leer")
    else:
        hrs = _hours_since(last_real, now)
        lines.append(f"letzter echter Versand vor {hrs / 24:.1f} Tag(en)")
        if pending:
            lines.append(f"{len(pending)} Artikel in der Warteschlange")
        if hrs > 7 * 24:
            lvl = "rot"
        elif hrs > 4 * 24:
            lvl = "gelb"
        else:
            lvl = "gruen"

    return lvl, lines, ["data/newsletter_journal.jsonl", "data/newsletter_state.json", "data/newsletter_kadenz.json"]


# ------------------------------------------------------------ Zusammenbau


BUCKET_ORDER = [
    "Content-Pipeline", "SEO & Technik", "Affiliate & Umsatz",
    "Secrets & Zugänge", "Social-Automation", "Newsletter",
]


def build_cockpit(now, governance, reserve, secrets_state, channels_cfg, social_state,
                   journal_rows, newsletter_state):
    buckets = {}
    buckets["Content-Pipeline"] = bucket_content(governance, reserve)
    buckets["SEO & Technik"] = bucket_seo(governance)
    buckets["Affiliate & Umsatz"] = bucket_affiliate(governance)
    buckets["Secrets & Zugänge"] = bucket_secrets(governance, secrets_state)
    buckets["Social-Automation"] = bucket_social(secrets_state, channels_cfg, social_state, now)
    buckets["Newsletter"] = bucket_newsletter(journal_rows, newsletter_state, now)

    overall = worst(lvl for lvl, _, _ in buckets.values())
    return overall, buckets


def render_markdown(now, overall, buckets):
    lines = []
    lines.append("# 🚦 COCKPIT – franksfinanzcheck.de")
    lines.append("")
    lines.append(f"**Stand:** {now.strftime('%Y-%m-%d %H:%M UTC')} · generiert von `scripts/cockpit.py`")
    lines.append("")
    lines.append(
        "> Eine Seite statt 70+ Status-Dateien. Jeder Bereich bekommt eine Ampel "
        "und einen Satz Begründung. Wer tiefer graben will, findet die Quelle "
        "unter jedem Bereich – diese Datei archiviert nichts, sie verweist nur."
    )
    lines.append("")
    lines.append(f"## {LEVEL_EMOJI[overall]} Gesamtbild: {LEVEL_WORT[overall]}")
    lines.append("")
    lines.append("| Bereich | Ampel | Kurzbefund |")
    lines.append("|---|---|---|")
    for name in BUCKET_ORDER:
        lvl, blines, _ = buckets[name]
        lines.append(f"| {name} | {LEVEL_EMOJI[lvl]} | {blines[0]} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Details")
    lines.append("")
    for name in BUCKET_ORDER:
        lvl, blines, sources = buckets[name]
        lines.append(f"### {name} — {LEVEL_EMOJI[lvl]} {LEVEL_WORT[lvl]}")
        for b in blines:
            lines.append(f"- {b}")
        lines.append(f"\nQuellen: {', '.join(f'`{s}`' for s in sources)}")
        lines.append("")
    lines.append("---")
    lines.append(
        "\n_Automatisch erzeugt von `scripts/cockpit.py` – reine Aggregation "
        "bestehender Wachen, keine neuen Messdaten, kein Netzzugriff. "
        "Maschinenlesbar: `data/cockpit_status.json`. Siehe auch "
        "`docs/ANLEITUNG-COCKPIT.md`._\n"
    )
    return "\n".join(lines)


def build_status_json(now, overall, buckets):
    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": overall,
        "buckets": {
            name: {"level": lvl, "lines": blines, "sources": sources}
            for name, (lvl, blines, sources) in buckets.items()
        },
    }


# ------------------------------------------------------------ Selftest


def selftest() -> bool:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + name)
        ok = ok and bool(cond)

    now = datetime.datetime(2026, 10, 3, 10, 0, tzinfo=datetime.timezone.utc)

    # -- worst()/Level-Mapping -------------------------------------------
    check("worst() ignoriert grau, wenn es Besseres/Schlechteres gibt",
          worst(["grau", "gruen", "gelb"]) == "gelb")
    check("worst() liefert grau nur, wenn alles grau ist",
          worst(["grau", "grau"]) == "grau")
    check("_level_from_governance mappt amber->gelb, red->rot, info->grau",
          _level_from_governance("amber") == "gelb"
          and _level_from_governance("red") == "rot"
          and _level_from_governance("info") == "grau"
          and _level_from_governance("green") == "gruen")
    check("_parse_ts versteht 'Z'-Suffix und Offset gleich",
          _parse_ts("2026-10-01T10:00:00Z") == _parse_ts("2026-10-01T12:00:00+02:00"))
    check("_slug_date liest Datum aus Artikel-Slug",
          _slug_date("2026-09-27-wlan-verstaerker-vs-mesh") == datetime.date(2026, 9, 27))

    # -- bucket_content ----------------------------------------------------
    gov_red = {"steps": {
        "lesbarkeit": {"level": "red", "message": "Flesch zu niedrig in Artikel X"},
        "decay": {"level": "green", "message": "in Ordnung"},
        "scorecard": {"level": "green", "message": "in Ordnung"},
        "automation": {"level": "green", "message": "in Ordnung"},
    }}
    lvl, bl, _ = bucket_content(gov_red, {"ready": 6, "target": 6})
    check("bucket_content: rote Lesbarkeit zieht den Bereich auf rot", lvl == "rot")
    check("bucket_content: Reserve voll wird positiv vermerkt",
          any("6/6" in x for x in bl))

    lvl2, bl2, _ = bucket_content({"steps": {}}, {"ready": 1, "target": 6})
    check("bucket_content: knappe Reserve (1/6) zieht auf gelb, auch ohne governance-Befund",
          lvl2 == "gelb" and any("1/6" in x for x in bl2))

    lvl2b, _, _ = bucket_content({"steps": {}}, {"ready": 0, "target": 6})
    check("bucket_content: leere Reserve (0/6) zieht auf rot", lvl2b == "rot")

    # -- bucket_seo ----------------------------------------------------
    gov_seo_ok = {"steps": {
        "cwv": {"level": "green", "message": "in Ordnung"},
        "build": {"level": "green", "message": "in Ordnung"},
        "live-policy": {"level": "green", "message": "in Ordnung"},
        "umami": {"level": "info", "message": "Datenlage offen"},
        "umami-views": {"level": "info", "message": "Datenlage offen"},
    }}
    lvl3, bl3, _ = bucket_seo(gov_seo_ok)
    check("bucket_seo: nur info-Umami bei sonst grün bleibt grün (Standby != Fehler)",
          lvl3 == "gruen")

    # -- bucket_secrets ----------------------------------------------------
    secrets_mixed = {"entries": {
        "GEMINI_API_KEY": {"quality": "proven"},
        "PINTEREST_ACCESS_TOKEN": {"verify": "dead"},
    }}
    gov_secrets_red = {"steps": {"secrets": {"level": "red", "message": "Pinterest tot"}}}
    lvl4, bl4, _ = bucket_secrets(gov_secrets_red, secrets_mixed)
    check("bucket_secrets: totes Token -> rot, beide Listen in der Begründung",
          lvl4 == "rot" and any("GEMINI" in x for x in bl4) and any("PINTEREST" in x for x in bl4))

    # -- bucket_social ----------------------------------------------------
    channels_cfg = {"channels": {
        "mastodon": {"enabled": True, "label": "Mastodon", "pflicht_env": ["MASTODON_ACCESS_TOKEN"]},
        "pinterest": {"enabled": True, "label": "Pinterest", "pflicht_env": ["PINTEREST_ACCESS_TOKEN"]},
        "bluesky": {"enabled": True, "label": "Bluesky",
                    "pflicht_env": ["BLUESKY_IDENTIFIER", "BLUESKY_APP_PASSWORD"]},
    }}
    secrets_social = {"entries": {
        "MASTODON_ACCESS_TOKEN": {"quality": "proven"},
        "PINTEREST_ACCESS_TOKEN": {"verify": "dead"},
    }}
    state_fresh = {"history": [{"ok": True, "posted_at": "2026-10-02T10:00:00+00:00"}], "failures": []}
    lvl5, bl5, _ = bucket_social(secrets_social, channels_cfg, state_fresh, now)
    check("bucket_social: 1 live Kanal + frischer Post + 1 totes Token -> gelb (Re-Auth nötig)",
          lvl5 == "gelb" and any("Mastodon" in x for x in bl5))

    state_stale = {"history": [{"ok": True, "posted_at": "2026-09-01T10:00:00+00:00"}], "failures": []}
    secrets_only_mastodon = {"entries": {"MASTODON_ACCESS_TOKEN": {"quality": "proven"}}}
    lvl6, bl6, _ = bucket_social(secrets_only_mastodon, channels_cfg, state_stale, now)
    check("bucket_social: letzter Post vor Wochen -> rot", lvl6 == "rot")

    lvl7, _, _ = bucket_social({"entries": {}}, channels_cfg, {"history": [], "failures": []}, now)
    check("bucket_social: kein einziger Kanal live -> rot", lvl7 == "rot")

    # -- bucket_newsletter ----------------------------------------------------
    journal_never = [
        {"modus": "sendefile", "ausgabe": "test-2026-09-25", "status": "zugestellt", "ts": "2026-09-25T10:00:00+00:00"},
    ]
    state_pending_old = {"pending": ["2026-09-20-alter-artikel", "2026-10-01-neuer-artikel"]}
    lvl8, bl8, _ = bucket_newsletter(journal_never, state_pending_old, now)
    check("bucket_newsletter: nie echt versendet + alte Warteschlange (>7d) -> rot",
          lvl8 == "rot")

    journal_recent = journal_never + [
        {"modus": "sendefile", "ausgabe": "2026-10-02-ausgabe", "status": "zugestellt", "ts": "2026-10-02T06:30:00+00:00"},
    ]
    lvl9, bl9, _ = bucket_newsletter(journal_recent, {"pending": []}, now)
    check("bucket_newsletter: echter Versand vor 1 Tag -> grün", lvl9 == "gruen")

    # -- build_cockpit + render_markdown ----------------------------------------------------
    overall, buckets = build_cockpit(
        now, gov_red, {"ready": 6, "target": 6}, secrets_mixed, channels_cfg,
        state_fresh, journal_recent, {"pending": []},
    )
    check("build_cockpit: Gesamtbild ist die schlechteste Einzelampel (hier rot wg. Content)",
          overall == "rot")
    md = render_markdown(now, overall, buckets)
    check("render_markdown: enthält Überschrift und alle Bereichsnamen",
          md.startswith("# 🚦 COCKPIT") and all(name in md for name in BUCKET_ORDER))
    status = build_status_json(now, overall, buckets)
    check("build_status_json: ist JSON-serialisierbar und enthält 'overall'",
          json.loads(json.dumps(status))["overall"] == "rot")

    print("\n" + ("✅ SELFTEST OK" if ok else "❌ SELFTEST FEHLGESCHLAGEN"))
    return ok


# ------------------------------------------------------------ Main


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 2)

    now = datetime.datetime.now(datetime.timezone.utc)
    governance = _load_json(GOVERNANCE_PATH, {})
    reserve = _load_json(RESERVE_PATH, {})
    secrets_state = _load_json(SECRETS_PATH, {})
    channels_cfg = _load_yaml(SOCIAL_CHANNELS_PATH, {})
    social_state = _load_yaml(SOCIAL_STATE_PATH, {})
    journal_rows = _load_jsonl(NEWSLETTER_JOURNAL_PATH)
    newsletter_state = _load_json(NEWSLETTER_STATE_PATH, {})

    overall, buckets = build_cockpit(
        now, governance, reserve, secrets_state, channels_cfg, social_state,
        journal_rows, newsletter_state,
    )

    md = render_markdown(now, overall, buckets)
    with open(OUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md)

    status = build_status_json(now, overall, buckets)
    with open(OUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Gesamtbild: {LEVEL_EMOJI[overall]} {LEVEL_WORT[overall]}")
    for name in BUCKET_ORDER:
        lvl, blines, _ = buckets[name]
        print(f"  {LEVEL_EMOJI[lvl]} {name}: {blines[0]}")
    print(f"\n→ {os.path.relpath(OUT_MD_PATH, BLOG_DIR)} · {os.path.relpath(OUT_JSON_PATH, BLOG_DIR)}")

    if "--print" in sys.argv:
        print("\n" + "=" * 70 + "\n")
        print(md)

    sys.exit(0)


if __name__ == "__main__":
    main()
