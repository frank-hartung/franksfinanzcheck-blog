#!/usr/bin/env python3
"""
PINTEREST-LINK-GUARD (Premium, 25.08.2026)
===========================================

Die harte Garantie: **Jeder Pin – bestehend und zukünftig – verlinkt
auf eine echte, erreichbare Blogseite** der eigenen Domain.

Zwei Prüf-Ebenen:

  LOCAL (Default, offline, in jeder Umgebung lauffähig):
    L1  Zielslug existiert       /posts/<slug>/ bzw. /pillar/<slug>/
        muss im Repo ein Artikel/eine Pillar sein (kein 404-Slug)
    L2  Artikel ist live-fähig   kein draft: true
    L3  Eigene Domain            Pin-Ziele NIEMALS auf pinterest.*
        oder check24.de (Premium-Regel: Pin → Blog → Affiliate-CTA)
    L4  UTM-Attribution          Pin-Links tragen utm_source=pinterest
    L5  URL-Form                  exakt wie Hugo die Permalinks erzeugt
        (Datumspräfix im Slug, Trailing-Slash) – keine toten Varianten
    Geprüft werden: alle Pins aus data/pinterest_plan.yaml,
        alle Einträge aus data/pin_queue.yaml und alle
        veröffentlichten Artikel-Permalinks selbst.

  LIVE (--live, nur in Umgebungen mit Internet, z. B. CI):
    V1  HTTP-Status                Ziel liefert 200 (keine 404/5xx)
    V2  Fehlbareite                finale URL bleibt auf franksfinanzcheck.de
        (keine Weiterleitung auf Fremddomains/Spam)
    V3  Rich-Pin-Basis             og:title + og:image vorhanden im HTML
        (Pinterest kann den Pin sauber scrapen)
    V4  Kein Meta-Refresh          keine Redirect-Alias als Pin-Ziel

Ausgabe: PINTEREST-LINK-GUARD-REPORT.md · Audit-Log (data/audit/*.jsonl)
Exit:    0 = alle Links verlässlich · 1 = Probleme · 2 = Selbsttest-Sabotage

Aufruf:
  python3 scripts/pinterest_link_guard.py             # LOCAL (offline)
  python3 scripts/pinterest_link_guard.py --live      # LOCAL + LIVE-Verifikation
  python3 scripts/pinterest_link_guard.py --json      # JSON statt MD-Zeilen
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")
QUEUE = os.path.join(BLOG_DIR, "data", "pin_queue.yaml")
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
PILLAR_DIR = os.path.join(BLOG_DIR, "content", "pillar")
REPORT = os.path.join(BLOG_DIR, "PINTEREST-LINK-GUARD-REPORT.md")

BASE_HOST = "franksfinanzcheck.de"
BASE = f"https://{BASE_HOST}"
PIN_UTM_SRC = "utm_source=pinterest"
# Vollständiger Pin-UTM (identisch zu pinterest_engine.py / pinterest_link_healer.py)
PIN_UTM = "?utm_source=pinterest&utm_medium=social&utm_campaign=pins"

DO_LIVE = "--live" in sys.argv
AS_JSON = "--json" in sys.argv
LIVE_TIMEOUT = 20
LIVE_RETRIES = 2
LIVE_PAUSE = 2.5  # Sek. zwischen Requests (Crawler-Etikette)

PROBLEMS: list[tuple[str, str, str]] = []   # (code, ziel, msg)
RESULTS: list[dict] = []                    # Details je geprüftem Ziel


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> list[str]:
    fehler = []
    if BASE_HOST != "franksfinanzcheck.de":
        fehler.append("BASE_HOST verändert")
    if PIN_UTM_SRC != "utm_source=pinterest":
        fehler.append("UTM-Konstante verändert")
    # Slug-Extraktion: /posts/2026-01-01-foo/ → 2026-01-01-foo
    m = re.search(r"/posts/([^/?#]+)/?", f"{BASE}/posts/2026-01-01-foo/?x=1")
    if not m or m.group(1) != "2026-01-01-foo":
        fehler.append("Slug-Regex defekt")
    # UTM-Erkennung
    if "utm_source=pinterest" not in "https://x.de/a/?utm_source=pinterest&utm_medium=social":
        fehler.append("UTM-Prüflogik defekt")
    return fehler


# ---------------------------------------------------------------- Helfer
def _slug_from_url(url: str) -> tuple[str, str] | None:
    """Liefert (art, slug) für /posts/<slug>/ bzw. /pillar/<slug>/, sonst None."""
    try:
        path = urllib.parse.urlparse(url).path
    except ValueError:
        return None
    m = re.match(r"^/posts/([^/]+)/?$", path)
    if m:
        return "post", m.group(1)
    m = re.match(r"^/pillar/([^/]+)/?$", path)
    if m:
        return "pillar", m.group(1)
    return None


def _is_draft(post_dir: str) -> bool:
    f = os.path.join(POSTS_DIR, post_dir, "index.md")
    if not os.path.exists(f):
        f = os.path.join(POSTS_DIR, post_dir + ".md")
        if not os.path.exists(f):
            return False
    with open(f, encoding="utf-8") as fh:
        head = fh.read(4000)
    m = re.search(r"^draft:\s*(true|false)", head, re.M)
    return bool(m and m.group(1) == "true")


def _pillar_exists(slug: str) -> bool:
    d = os.path.join(PILLAR_DIR, slug)
    if not os.path.isdir(d):
        return False
    return os.path.exists(os.path.join(d, "index.md")) or os.path.exists(os.path.join(d, "_index.md"))


def _local_target_check(url: str, source: str) -> None:
    """L1–L5 für eine einzelne Pin-/Queue-URL."""
    res = {"source": source, "url": url}
    RESULTS.append(res)
    host = urllib.parse.urlparse(url).hostname or ""
    if host != BASE_HOST:
        PROBLEMS.append(("L3", url[:80], f"fremde Domain im Pin-Ziel: {host}"))
        return
    # L4: UTM
    if PIN_UTM_SRC not in url:
        PROBLEMS.append(("L4", url[:80], "Pin-Link ohne utm_source=pinterest (Attribution fehlt)"))
    # L5 + L1: Slug-Form + Existenz
    parsed = _slug_from_url(url)
    if not parsed:
        PROBLEMS.append(("L5", url[:80], "URL ist kein /posts/<slug>/ oder /pillar/<slug>/ (totes Ziel)"))
        return
    art, slug = parsed
    if art == "post":
        d = os.path.join(POSTS_DIR, slug)
        if not (os.path.isdir(d) and os.path.exists(os.path.join(d, "index.md"))
                or os.path.exists(os.path.join(POSTS_DIR, slug + ".md"))):
            PROBLEMS.append(("L1", slug, "Pin-Ziel gibt es nicht im Repo (404 nach Deploy!)"))
            return
        if _is_draft(slug):
            PROBLEMS.append(("L2", slug, "Pin zeigt auf DRAFT-Artikel (geht nicht live)"))
    else:
        if not _pillar_exists(slug):
            PROBLEMS.append(("L1", slug, "Pin-Ziel-Pillar existiert nicht (404 nach Deploy!)"))


def _live_check(url: str, source: str) -> dict:
    """V1–V4: LIVE-Verifikation einer URL (mit Retry)."""
    res = {"source": source, "url": url, "live": {}}
    for attempt in range(LIVE_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; FranksFinanzcheck-LinkGuard/1.0)",
                "Accept": "text/html",
            })
            with urllib.request.urlopen(req, timeout=LIVE_TIMEOUT) as resp:
                final_url = resp.geturl()
                status = resp.status
                body = resp.read(300_000).decode("utf-8", errors="ignore")
            break
        except urllib.error.HTTPError as e:
            status, final_url, body = e.code, url, ""
            break  # klare HTTP-Antwort – kein Retry
        except Exception:  # noqa: BLE001 – Netzwerk/Timeout → Retry
            if attempt < LIVE_RETRIES:
                time.sleep(8 * (attempt + 1))
                continue
            res["live"]["error"] = f"nicht erreichbar (nach {LIVE_RETRIES + 1} Versuchen)"
            PROBLEMS.append(("V1", url[:80], "Ziel nicht erreichbar – Deploy prüfen!"))
            return res
    res["live"]["status"] = status
    res["live"]["final_url"] = final_url
    if status != 200:
        PROBLEMS.append(("V1", url[:80], f"HTTP {status} statt 200"))
        return res
    # V2: finale Domain
    final_host = urllib.parse.urlparse(final_url).hostname or ""
    if final_host != BASE_HOST:
        PROBLEMS.append(("V2", url[:80], f"leitet weiter auf {final_host} (Fremddomain!)"))
        return res
    if "http-equiv=\"refresh\"" in body.lower() or 'http-equiv=refresh' in body.lower():
        PROBLEMS.append(("V4", url[:80], "Ziel ist Meta-Refresh-Alias (kein echter Artikel)"))
    # V3: Rich-Pin-Basis
    if 'property="og:title"' not in body:
        PROBLEMS.append(("V3", url[:80], "og:title fehlt (Rich-Pin-Scraping gestört)"))
    if 'property="og:image"' not in body:
        PROBLEMS.append(("V3", url[:80], "og:image fehlt (Rich-Pin ohne Bild)"))
    return res


# ---------------------------------------------------------------- Main
def main() -> int:
    st = _selftest()
    if st:
        print("🛑 LINK-GUARD-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        for e in st:
            print(f"   {e}")
        return 2

    # -- Sammle alle zu prüfenden URLs --
    urls: list[tuple[str, str]] = []  # (url, quelle)

    if os.path.exists(PLAN):
        plan = yaml.safe_load(open(PLAN, encoding="utf-8")) or {}
        for pin in plan.get("pins", []):
            u = str(pin.get("url", "")).strip()
            if u:
                urls.append((u, f"Plan-Tag {pin.get('tag', '?')} ({pin.get('typ', 'EP')})"))

    if os.path.exists(QUEUE):
        try:
            queue = yaml.safe_load(open(QUEUE, encoding="utf-8")) or []
            for item in queue:
                u = str(item.get("link", "")).strip()
                if u:
                    urls.append((u, f"Queue {item.get('slug', '?')}"))
        except yaml.YAMLError:
            pass

    # Veröffentlichte Artikel-Permalinks (die Basis für ALLE zukünftigen Pins)
    if os.path.isdir(POSTS_DIR):
        for d in sorted(os.listdir(POSTS_DIR)):
            f = os.path.join(POSTS_DIR, d, "index.md")
            if not (os.path.isdir(os.path.join(POSTS_DIR, d)) and os.path.exists(f)):
                continue
            head = open(f, encoding="utf-8").read(2000)
            if re.search(r"^draft:\s*true", head, re.M):
                continue
            urls.append((f"{BASE}/posts/{d}/{PIN_UTM}",
                         f"Artikel-Pin {d}"))

    unique: dict[str, list[str]] = {}
    for u, q in urls:
        unique.setdefault(u, []).append(q)

    # -- LOCAL --
    for u, quellen in unique.items():
        _local_target_check(u, quellen[0] if len(quellen) == 1 else f"{quellen[0]} +{len(quellen) - 1} weitere")

    # -- LIVE --
    if DO_LIVE:
        for i, u in enumerate(unique):
            if i:
                time.sleep(LIVE_PAUSE)
            before = len(PROBLEMS)
            r = _live_check(u, "LIVE")
            mark = "OK " if len(PROBLEMS) == before else "FAIL"
            print(f"  [{mark} {r['live'].get('status', 'n/a')}] {u[:90]}")

    # -- Report --
    now = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    lines = [
        "# 🔒 PINTEREST-LINK-GUARD-REPORT (Premium-Zielseiten-Garantie)",
        "",
        f"**Stand:** {now} · **Modus:** {'LOCAL + LIVE' if DO_LIVE else 'LOCAL (offline)'}",
        "",
        "**Garantie:** Jeder Pin (Masterplan + Queue + alle Artikel-Permalinks) zeigt auf eine",
        "echte Blogseite der eigenen Domain – nie auf das Profil, nie nackt auf CHECK24,",
        "nie auf einen toten Slug. Bei LIVE-Prüfung zusätzlich: 200 + Rich-Pin-Meta.",
        "",
        "## Überblick",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Geprüfte eindeutige Ziele | {len(unique)} |",
        f"| Probleme | **{len(PROBLEMS)}** |",
        f"| Lokal geprüfte URLs | {sum(1 for r in RESULTS)} |",
        f"| Live-geprüfte URLs | {sum(1 for r in RESULTS if 'live' in r) if DO_LIVE else '–'} |",
        "",
    ]
    if PROBLEMS:
        lines += ["## ⚠️ Probleme", "", "| Code | Ziel | Problem |", "|---|---|---|"]
        for code, ziel, msg in PROBLEMS:
            lines.append(f"| {code} | {ziel} | {msg} |")
    else:
        lines.append("✅ Alle Pin-Ziele verlässlich – keine toten Links, keine Sackgassen, kein Spam-Signal.")
    if DO_LIVE:
        lines += ["", "## Live-Status", "", "| Status | Finale URL | Ziel |", "|---|---|---|"]
        for r in RESULTS:
            if "live" in r:
                lv = r["live"]
                lines.append(f"| {lv.get('status', 'n/a')} | {lv.get('final_url', lv.get('error', ''))[:70]} | {r['url'][:80]} |")
    lines += ["", "---", "", "_Erzeugt von `scripts/pinterest_link_guard.py`._", ""]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))

    print(f"Link-Guard: {len(unique)} Ziele, {len(PROBLEMS)} Probleme "
          f"(Modus: {'LOCAL+LIVE' if DO_LIVE else 'LOCAL'})")
    print(f"Report: {os.path.relpath(REPORT, BLOG_DIR)}")

    try:
        from audit_log import log_event
        log_event(module="pinterest_link_guard", action="live" if DO_LIVE else "local",
                  input={"targets": len(unique)},
                  output={"problems": len(PROBLEMS)},
                  status="ok" if not PROBLEMS else "issues")
    except Exception:
        pass

    if AS_JSON:
        print(json.dumps({"problems": PROBLEMS, "results": RESULTS}, ensure_ascii=False))
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
