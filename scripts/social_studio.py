#!/usr/bin/env python3
# ============================================================
#  SOCIAL-STUDIO – der Autopilot (Planung · Text · Freigabe · Versand)
#  ------------------------------------------------------------
#  Ein Lauf = eine komplette Redaktionssitzung:
#
#    1 PLANEN   14-Tage-Plan prüfen/erneuern (social_planner)
#    2 BAUEN    kanalnative Fassung je Beitrag (social_copywriter)
#    3 PRÜFEN   hartes Gate, fail-closed (social_gate)
#    4 BILD     Format-Variante rendern, Erreichbarkeit prüfen
#    5 SENDEN   Adapter des Kanals, mit Protokoll und Selbstheilung
#    6 BERICHT  Cockpit SOCIAL-AUTOPILOT-STATUS.md + State fortschreiben
#
#  BETRIEBSREGELN (Dauervorgabe):
#    · Fehlendes Token = Standby, KEIN Fehler, KEIN Alarm
#      (der Kanal erscheint im Cockpit als „nicht eingerichtet")
#    · Ein gescheiterter Versuch wird nicht sofort verworfen: erst
#      nach 3 Versuchen gilt der Post als fehlgeschlagen
#    · Vollausfall (≥3 Fehler, kein Erfolg) → Exit 2 → Alarmierung
#    · Alles bleibt offline testbar: --dry-run und --selftest
#
#  AUFRUF:
#    python3 scripts/social_studio.py --run [--dry-run] [--channel x] [--limit n]
#    python3 scripts/social_studio.py --plan
#    python3 scripts/social_studio.py --status
#    python3 scripts/social_studio.py --selftest
# ============================================================
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_channels as sch          # noqa: E402
import social_copywriter as copy       # noqa: E402
import social_gate as gate             # noqa: E402
import social_images as images         # noqa: E402
import social_planner as planner       # noqa: E402

COCKPIT = os.path.join(BLOG_DIR, "SOCIAL-AUTOPILOT-STATUS.md")
MAX_ATTEMPTS = 3

def channel_report(cfg: dict) -> list[dict]:
    """Zustand je Kanal: konfiguriert? letzter Post? heute? geplant?"""
    state = planner.load_state()
    schedule = planner.load_schedule()
    now = planner.berlin_now()
    today = now.date().isoformat()
    rows = []
    for cid, ch in sorted(sch.channel_map(cfg).items(),
                          key=lambda kv: int((kv[1] or {}).get("priority") or 99)):
        ad = sch.get_adapter(cid, cfg)
        configured, reason = (False, "Kanal deaktiviert")
        if not (ch or {}).get("enabled"):
            configured, reason = (False, "in channels.yaml deaktiviert")
        elif ad:
            configured, reason = ad.configured()
        elif (ch or {}).get("enabled"):
            reason = "Adapter nicht ladbar"
        hist = [e for e in (state.get("history") or [])
                if e.get("channel") == cid and e.get("ok")]
        last = hist[-1] if hist else None
        planned = sum(1 for it in planner.planned_items(schedule) if it.get("channel") == cid)
        rows.append({
            "id": cid,
            "label": (ch or {}).get("label") or cid,
            "enabled": bool((ch or {}).get("enabled")),
            "configured": configured,
            "reason": "" if configured else reason,
            "profile": (ch or {}).get("profile") or "",
            "last_post": (last or {}).get("posted_at", "")[:16] if last else "",
            "last_title": (last or {}).get("title", "") if last else "",
            "today": planner.posts_on_day(state, cid, now.date()),
            "planned": planned,
            "limit": int((((ch or {}).get("cadence")) or {}).get("max_per_day") or 0),
            "queued_today": sum(1 for it in planner.planned_items(schedule)
                                if it.get("channel") == cid and it.get("date") == today),
        })
    return rows


# --------------------------------------------------------------------- Bilder
def resolve_media(article: dict, channel_cfg: dict, meta: dict) -> tuple[str, str]:
    """Liefert (lokaler Pfad, öffentliche URL) für den Beitrag."""
    media_cfg = (channel_cfg or {}).get("media") or {}
    if not media_cfg.get("supported", True):
        return "", ""
    rel = article.get("cover") or ""
    src = os.path.join(BLOG_DIR, "static", rel) if rel else ""
    if not src or not os.path.isfile(src):
        # Fallback: Cover nach Slug-Konvention
        guess = os.path.join(BLOG_DIR, "static", "images", "covers",
                             f"{article['slug']}.jpg")
        src = guess if os.path.isfile(guess) else ""
    if not src:
        return "", ""
    variant = media_cfg.get("variant")
    if variant:
        src = images.ensure_variant(src, article["slug"], variant) or src
    url = f"{str(meta.get('base_url') or '').rstrip('/')}/{images.static_rel(src)}"
    return src, url


# -------------------------------------------------------------------- Senden
def build_package(article: dict, cid: str, ch: dict, angle: str, meta: dict,
                  use_llm: bool) -> dict:
    pkg = copy.compose(article, cid, ch, angle, meta, use_llm=use_llm)
    path, url = resolve_media(article, ch, meta)
    pkg["media_path"] = path
    pkg["media_url"] = url if url and str(url).startswith("https://") else ""
    return pkg


def run_once(cfg: dict, *, dry_run: bool = False, channel: str = "",
             limit: int = 0, now=None, force: bool = False) -> dict:
    """Ein kompletter Autopilot-Lauf."""
    now = now or planner.berlin_now()
    meta = sch.meta_of(cfg)
    channels = sch.channel_map(cfg)
    state = planner.load_state()
    schedule = planner.load_schedule()

    pool = copy.article_pool(base_url=str(meta.get("base_url") or copy.DEFAULT_BASE))
    by_slug = {a["slug"]: a for a in pool}

    # 1) Plan erneuern, wenn nötig
    planned_before = len(planner.planned_items(schedule))
    if planned_before < int(meta.get("min_planned_items") or 12):
        schedule = planner.build_plan(cfg, pool, state, now=now)
        planner.prune(schedule)
        print(f"🗓️  Plan erneuert: {len(planner.planned_items(schedule))} geplante Beiträge "
              f"(Horizont {schedule.get('horizon_days')} Tage).")
    else:
        print(f"🗓️  Plan steht: {planned_before} geplante Beiträge.")

    due = planner.due_items(schedule, now=now)
    if channel:
        due = [it for it in due if it.get("channel") == channel]
    if limit:
        due = due[:limit]

    print(f"⏰ {len(due)} Beitrag/Beiträge jetzt fällig.")

    llm_left = int(((meta.get("llm") or {}).get("max_per_run")) or 0)
    results = {"sent": 0, "failed": 0, "blocked": 0, "standby": 0, "deferred": 0}
    log_lines: list[str] = []

    for item in due:
        cid = item.get("channel") or ""
        ch = channels.get(cid) or {}
        if not ch.get("enabled"):
            continue
        slug = item.get("slug") or ""
        article = by_slug.get(slug)
        if not article:
            planner.set_status(schedule, item["id"], "blocked", "Artikel nicht mehr im Bestand")
            results["blocked"] += 1
            continue

        ad = sch.get_adapter(cid, cfg)
        if not ad:
            planner.set_status(schedule, item["id"], "blocked", "Adapter fehlt")
            results["blocked"] += 1
            continue
        configured, reason = ad.configured()
        if not configured and not force:
            # Standby: kein Fehler, keine Alarmierung – nur notieren.
            item["status"] = "standby"
            item["reason"] = reason
            results["standby"] += 1
            print(f"   ⚪ {cid}: {reason} – Beitrag bleibt geplant.")
            continue

        # Frequenzschutz: Mindestabstand zum letzten Post dieses Kanals
        min_gap = int(((ch.get("cadence")) or {}).get("min_gap_min") or 0)
        last_at = planner.last_channel_post(state, cid)
        if last_at and min_gap and (now - last_at) < timedelta(minutes=min_gap):
            results["deferred"] += 1
            print(f"   ⏳ {cid}: Mindestabstand {min_gap} min noch nicht erreicht – verschoben.")
            continue

        # Bildpflicht: bei Kanälen mit öffentlicher Bild-URL erst senden,
        # wenn die Datei wirklich live ist (sonst nächster Lauf).
        pkg_preview = build_package(article, cid, ch, item.get("angle") or "nutzen",
                                    meta, use_llm=False)
        if (((ch.get("media")) or {}).get("required")
                and not dry_run
                and not images.url_is_live(pkg_preview.get("media_url") or "")):
            item["status"] = "planned"
            item["reason"] = "Bild-URL noch nicht live (Deploy abgewartet)"
            results["deferred"] += 1
            print(f"   🖼️  {cid}: Bild noch nicht öffentlich erreichbar – nächster Lauf.")
            continue

        # Text + Gate (mit Winkel-Fallback: bis zu 3 Versuche)
        angles = list(ch.get("angles") or ["nutzen"])
        start = angles.index(item["angle"]) if item.get("angle") in angles else 0
        order = [angles[(start + i) % len(angles)] for i in range(len(angles))]
        pkg, violations, used_angle = None, [], item.get("angle")
        for ang in order[:3]:
            use_llm = bool(llm_left > 0)
            candidate = build_package(article, cid, ch, ang, meta, use_llm=use_llm)
            if candidate.get("ai_polished"):
                llm_left -= 1
            ok, viol, _metrics = gate.check(candidate, ch, meta,
                                            history=state.get("history") or [])
            if ok:
                pkg, used_angle = candidate, ang
                break
            violations = viol
        if pkg is None:
            planner.set_status(schedule, item["id"], "blocked", "; ".join(violations)[:280])
            planner.record_failure(state, {"at": planner.iso(now), "channel": cid,
                                           "slug": slug, "reason": "; ".join(violations)[:200]})
            results["blocked"] += 1
            print(f"   🛑 {cid}/{slug}: Gate blockiert – {violations[0] if violations else '?'}")
            continue

        if dry_run:
            print("=" * 72)
            print(f"[DRY-RUN] {cid} · {used_angle} · {item.get('scheduled_at')}")
            print("-" * 72)
            print(pkg["text"])
            if pkg.get("comment"):
                print(f"— Kommentar: {pkg['comment']}")
            print(f"— Bild: {pkg.get('media_url') or pkg.get('media_path') or 'keins'}")
            results["sent"] += 1
            continue

        # Senden
        res = ad.publish(pkg)
        if res.ok:
            planner.set_status(schedule, item["id"], "published", "")
            planner.record_history(state, {
                "posted_at": planner.iso(now),
                "channel": cid,
                "slug": slug,
                "title": article.get("title") or slug,
                "angle": used_angle,
                "url": res.url or pkg.get("url") or "",
                "ok": True,
                "text": pkg.get("text") or "",
                "ref": res.ref or "",
                "ai": bool(pkg.get("ai_polished")),
            })
            results["sent"] += 1
            log_lines.append(f"✅ {cid}: {article.get('title')} → {res.url or pkg.get('url')}")
            print(f"   ✅ {cid}: {article.get('title')[:52]} → {res.url or 'ok'}")
        else:
            attempts = int(item.get("attempts") or 0) + 1
            item["attempts"] = attempts
            item["reason"] = (res.error or "unbekannt")[:280]
            if attempts >= MAX_ATTEMPTS:
                item["status"] = "failed"
                planner.record_failure(state, {"at": planner.iso(now), "channel": cid,
                                               "slug": slug, "reason": item["reason"]})
                results["failed"] += 1
                print(f"   ❌ {cid}: endgültig fehlgeschlagen – {item['reason']}")
            else:
                results["failed"] += 1
                print(f"   ↻ {cid}: Versuch {attempts}/{MAX_ATTEMPTS} – {item['reason']}")

    if not dry_run:
        planner.save_state(state)
        planner.save_schedule(schedule)
    write_cockpit(cfg, state, schedule, results, log_lines, dry_run=dry_run)
    return {"results": results, "log": log_lines, "state": state, "schedule": schedule}


# ------------------------------------------------------------------- Cockpit
# ------------------------------------------------------------ Altbestand
# Beim Umstieg auf den Autopiloten darf kein Artikel ein zweites Mal auf
# einen Kanal wandern, auf dem er schon stand. Der Alt-Bot hat seine Arbeit
# im Frontmatter markiert (social_posted / pinned) – diese Marken werden
# EINMALIG in den neuen Stand übernommen (idempotent, jederzeit
# wiederholbar). Danach greift die normale Sperrfrist.
LEGACY_FLAGS = (("social_posted", "mastodon"), ("pinned", "pinterest"))


def migrate_legacy(state: dict, pool: list[dict]) -> int:
    """Übernimmt Alt-Marken (social_posted/pinned) in den neuen Stand."""
    import re

    known = {(e.get("channel"), e.get("slug")) for e in (state.get("history") or [])}
    added = 0
    for art in pool:
        fm = art.get("raw_fm") or ""
        for flag, cid in LEGACY_FLAGS:
            if not re.search(rf"(?m)^{flag}:\s*true", fm):
                continue
            if (cid, art["slug"]) in known:
                continue
            state.setdefault("history", []).append({
                "posted_at": art.get("published") or planner.iso(planner.berlin_now()),
                "channel": cid,
                "slug": art["slug"],
                "title": art.get("title") or art["slug"],
                "angle": "nutzen",
                "url": art.get("url") or "",
                "ok": True,
                "text": "",
                "ref": "altbestand",
                "migrated": True,
            })
            known.add((cid, art["slug"]))
            added += 1
    return added


def write_cockpit(cfg: dict, state: dict, schedule: dict, results: dict,
                  log_lines: list[str], dry_run: bool = False) -> None:
    now = planner.berlin_now()
    rows = channel_report(cfg)
    lines = [
        "# 🛰️ Social-Autopilot – Cockpit",
        "",
        f"> Automatisch aktualisiert: {now:%d.%m.%Y %H:%M} (Europe/Berlin)"
        f"{' · TROCKENLAUF' if dry_run else ''}",
        "",
        "## Kanäle",
        "",
        "| Kanal | Status | Heute | Geplant | Letzter Post |",
        "|---|---|---:|---:|---|",
    ]
    for r in rows:
        if r["configured"]:
            status = "🟢 aktiv"
        elif not r["enabled"]:
            status = "⚫ aus"
        else:
            status = f"⚪ Standby ({r['reason']})"
        lines.append(
            f"| {r['label']} | {status} | {r['today']}/{r['limit'] or '–'} | "
            f"{r['planned']} | {(r['last_post'] or '–').replace('T', ' ')} |")

    planned = planner.planned_items(schedule)
    upcoming = sorted(planned, key=lambda it: it.get("scheduled_at") or "")[:14]
    if upcoming:
        lines += ["", "## Nächste geplante Beiträge", ""]
        for it in upcoming:
            ch = sch.channel_map(cfg).get(it.get("channel") or "") or {}
            when = (it.get("scheduled_at") or "").replace("T", " ")[:16]
            lines.append(f"- **{when}** · {ch.get('label') or it.get('channel')} · "
                         f"`{it.get('angle')}` · {it.get('slug')}")

    history = list(state.get("history") or [])
    if history:
        lines += ["", "## Zuletzt gesendet", ""]
        for entry in history[-12:][::-1]:
            when = (entry.get("posted_at") or "").replace("T", " ")[:16]
            lines.append(f"- {when} · {entry.get('channel')} · {entry.get('slug')} "
                         f"→ {entry.get('url') or 'ok'}")

    failures = list(state.get("failures") or [])[-8:]
    if failures:
        lines += ["", "## Blockaden & Fehler", ""]
        for f in failures[::-1]:
            lines.append(f"- {(f.get('at') or '')[:16]} · {f.get('channel')} · "
                         f"{f.get('slug')} · {f.get('reason')}")

    r = results or {}
    lines += ["", "## Dieser Lauf", "",
              f"- gesendet: **{r.get('sent', 0)}** · fehlgeschlagen: {r.get('failed', 0)} · "
              f"blockiert: {r.get('blocked', 0)} · Standby: {r.get('standby', 0)} · "
              f"verschoben: {r.get('deferred', 0)}",
              "",
              "---",
              "*Erzeugt von scripts/social_studio.py · Kanal-Playbook: "
              "data/social/channels.yaml · Anleitung: docs/ANLEITUNG-SOCIAL-AUTOPILOT.md*"]
    with open(COCKPIT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ----------------------------------------------------------------- Selftest
def selftest() -> int:
    """Beweisführung, dass Wache, Planer und Textwerkzeug wirklich greifen."""
    errors: list[str] = []
    cfg = sch.load_config()
    if not cfg:
        return _fail(["channels.yaml fehlt oder ist leer"])
    channels = sch.channel_map(cfg)
    if not channels:
        return _fail(["keine Kanäle konfiguriert"])

    meta = sch.meta_of(cfg)
    gate_cfg = meta.get("gate") or {}

    # 1) Adapter sind ladbar
    for cid, ch in channels.items():
        if sch.adapter_class(cid) is None:
            errors.append(f"Adapter für {cid} nicht ladbar")

    # 2) Textwerkzeug hält die Kanal-Limits (über echte Artikel!)
    pool = copy.article_pool()
    if not pool:
        errors.append("kein Artikel im Bestand gefunden")
    sample = (pool[-1:] or [])[:1]
    for art in sample:
        for cid, ch in channels.items():
            for ang in (ch.get("angles") or [])[:3]:
                pkg = copy.compose(art, cid, ch, ang, meta, use_llm=False)
                w = int(((ch.get("text")) or {}).get("link_weight") or 0)
                n = copy.effective_length(pkg["text"], pkg["url"], w)
                if n > int(((ch.get("text")) or {}).get("max_chars") or 500):
                    errors.append(f"{cid}/{ang}: {n} Zeichen über Limit")

    # 3) Gate schlägt an (fünf Beweisfälle)
    art = sample[0] if sample else {"slug": "x", "title": "T", "takeaways": [],
                                    "hook_sentences": ["Satz eins."], "hook": "Satz eins.",
                                    "numbers": [], "pillar": "", "tags": [], "keywords": [],
                                    "kurzantwort": "", "description": "", "url": "",
                                    "pin_title": "", "cover": "", "cover_alt": ""}
    mast = channels.get("mastodon") or {}
    base = copy.compose(art, "mastodon", mast, "nutzen", meta, use_llm=False)
    cases = [
        ("Länge", {**base, "text": "x" * 900}, False),
        ("Affiliate-Link", {**base, "text": base["text"].replace(base["url"],
                                                                 "https://franksfinanzcheck.de/go/dsl/")}, False),
        ("Hashtag-Flut", {**base, "text": base["text"] + " #A #B #C #D #E #F"}, False),
        ("Werbeversprechen", {**base, "text": base["text"] + " garantiert risikofrei"}, False),
        ("Sauberer Beitrag", base, True),
    ]
    for name, pkg, expect_ok in cases:
        ok, viol, _ = gate.check(pkg, mast, meta, history=[])
        if ok != expect_ok:
            errors.append(f"Gate-Fall „{name}“: erwartet {expect_ok}, bekommen {ok} ({viol[:1]})")

    # 4) Duplikat-Erkennung
    hist = [{"channel": "mastodon", "posted_at": "2026-01-01T10:00:00+01:00",
             "text": base["text"], "ok": True}]
    ok, _viol, _ = gate.check(base, mast, meta, history=hist)
    if ok:
        errors.append("Duplikat-Schutz greift nicht (identischer Text wäre erneut gesendet)")

    # 5) Planer hält Kadenz, Sperrfrist und Tagesgrenzen
    state = {"history": [], "failures": []}
    plan = planner.build_plan(cfg, pool, state,
                              now=planner.localize(datetime(2026, 9, 14, 6, 0)))
    items = planner.planned_items(plan)
    if not items:
        errors.append("Planer erzeugt keine Beiträge")
    seen = set()
    per_day: dict[str, int] = {}
    for it in items:
        key = (it.get("channel"), it.get("slug"))
        if key in seen:
            errors.append(f"Doppelplanung {key}")
        seen.add(key)
        day_key = f"{it.get('channel')}|{it.get('date')}"
        per_day[day_key] = per_day.get(day_key, 0) + 1
        ch = channels.get(it.get("channel")) or {}
        cap = int(((ch.get("cadence")) or {}).get("max_per_day") or 99)
        if per_day[day_key] > cap:
            errors.append(f"Tagesgrenze überschritten: {day_key}")
        when = planner.parse_dt(it.get("scheduled_at") or "")
        if when and when.weekday() not in set(((ch.get("cadence")) or {}).get("days")
                                              or [0, 1, 2, 3, 4, 5, 6]):
            errors.append(f"Kadenzverstoß: {it.get('channel')} am {it.get('date')}")

    # 6) Planer respektiert die Sperrfrist (Evergreen)
    if items:
        first = items[0]
        state2 = {"history": [{"channel": first["channel"], "slug": first["slug"],
                               "posted_at": planner.iso(planner.berlin_now()),
                               "ok": True, "text": "x", "angle": "nutzen"}],
                  "failures": []}
        plan2 = planner.build_plan(cfg, pool, state2, now=planner.berlin_now())
        again = [it for it in planner.planned_items(plan2)
                 if it.get("channel") == first["channel"] and it.get("slug") == first["slug"]]
        if again:
            errors.append("Sperrfrist greift nicht (frisch geposteter Artikel erneut geplant)")

    # 7) Ungerüstete Kanäle senden nicht (skip statt crash)
    sch_mast = sch.get_adapter("mastodon", cfg)
    if sch_mast and not sch_mast.configured()[0]:
        res = sch_mast.publish({"text": "Test", "url": "", "media_path": "", "alt": ""})
        if not res.skipped:
            errors.append("Kanal ohne Token sendet trotzdem (Standby-Regel verletzt)")

    return _fail(errors) if errors else _ok()


def _ok() -> int:
    print("✅ SOCIAL-STUDIO-SELFTEST bestanden "
          "(Kanäle, Limits, Gate, Duplikat-Schutz, Planung, Standby-Regel).")
    return 0


def _fail(errors: list[str]) -> int:
    print("🛑 SOCIAL-STUDIO-SELFTEST FEHLGESCHLAGEN:")
    for e in errors:
        print(f"   - {e}")
    return 2


# ---------------------------------------------------------------------- CLI
def main() -> int:
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()

    cfg = sch.load_config()
    if not cfg:
        print("⚠ data/social/channels.yaml fehlt – Autopilot ohne Konfiguration (exit 0).")
        return 0

    def _val(flag: str, default: str = "") -> str:
        return argv[argv.index(flag) + 1] if flag in argv and len(argv) > argv.index(flag) + 1 else default

    channel = _val("--channel").strip()
    limit = int(_val("--limit", "0") or 0)
    dry = "--dry-run" in argv
    force = "--force" in argv
    # --now "<ISO>": Probelauf für einen anderen Zeitpunkt (z. B. "wie
    # sieht der Lauf morgen früh aus?") – ohne Netz, ohne Versand.
    now = planner.parse_dt(_val("--now")) if _val("--now") else None

    if "--plan" in argv:
        meta = sch.meta_of(cfg)
        pool = copy.article_pool(base_url=str(meta.get("base_url") or copy.DEFAULT_BASE))
        state = planner.load_state()
        plan = planner.build_plan(cfg, pool, state)
        planner.prune(plan)
        planner.save_schedule(plan)
        print(f"🗓️  {len(planner.planned_items(plan))} Beiträge über "
              f"{plan['horizon_days']} Tage geplant.")
        return 0

    if "--migrate" in argv:
        # Einmaliger Altbestand-Import (idempotent): was der alte Bot schon
        # gepostet hat, gilt als gepostet – keine Doppelposts beim Umstieg.
        meta = sch.meta_of(cfg)
        pool = copy.article_pool(base_url=str(meta.get("base_url") or copy.DEFAULT_BASE))
        state = planner.load_state()
        n = migrate_legacy(state, pool)
        planner.save_state(state)
        print(f"📦 Altbestand übernommen: {n} Einträge (social_posted → Mastodon, "
              f"pinned → Pinterest). Stand jetzt: {len(state.get('history') or [])} Einträge.")
        return 0

    if "--status" in argv or "--report" in argv:
        rows = channel_report(cfg)
        for r in rows:
            mark = "🟢" if r["configured"] else ("⚫" if not r["enabled"] else "⚪")
            print(f"{mark} {r['label']:18s} heute {r['today']}/{r['limit'] or '-'} · "
                  f"geplant {r['planned']} · zuletzt {r['last_post'] or '–'}"
                  f"{'' if r['configured'] else ' · ' + r['reason']}")
        write_cockpit(cfg, planner.load_state(), planner.load_schedule(), {}, [])
        print(f"\n📄 Cockpit geschrieben: {os.path.basename(COCKPIT)}")
        return 0

    # Standard: --run
    out = run_once(cfg, dry_run=dry, channel=channel, limit=limit,
                   force=force, now=now)
    r = out["results"]
    print(f"\n📊 gesendet {r['sent']} · fehlgeschlagen {r['failed']} · "
          f"blockiert {r['blocked']} · Standby {r['standby']} · verschoben {r['deferred']}")
    print(f"📄 Cockpit: {os.path.basename(COCKPIT)}")

    # Vollausfall = echter Vorfall (Alarmierung greift). Standby zählt nicht.
    if (not dry and r["failed"] >= 3 and r["sent"] == 0
            and any(row["configured"] for row in channel_report(cfg))):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
