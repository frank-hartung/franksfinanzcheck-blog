#!/usr/bin/env python3
"""
reserve_pool.py – Redaktions-Reserve-Pool („Zwingend 2–3 LIVE an Mo/Mi/Fr“)

WARUM (Premium-Fix 03.09.2026, Auftrag „Mi 02.09.: nur 1 Artikel live“):
  Die Content-Engine produziert 2–3 Artikel pro Publikationstag aus
  KI-Generierung + Re-Queue-Recycling. Beide Quellen können an einem Tag
  versagen (Provider-Ausfall, wiederholte Gate-Stopps). Damit die
  Dauervorgabe „Mo/Mi/Fr 2–3 Artikel live“ NICHT mehr von der KI-Verfügbarkeit
  abhängt, hält die Redaktion einen kleinen POOL fertiger Premium-Evergreen-
  Artikel als Entwürfe vor (Frontmatter: `reserve: true`).

  Nur die Kadenz-Endkontrolle (kadenz-endkontrolle.yml, 21:05 UTC an
  Mo/Mi/Fr, NACH dem letzten Engine-Slot) bzw. die Engine selbst dürfen
  Reserve-Artikel VERÖFFENTLICHEN – und nur, wenn der Tag sonst unter dem
  LIVE-Mindestziel bliebe. Veröffentlichte Reserve-Artikel sind normale
  live-Posts (draft: false, Datum = heute) und durchlaufen danach exakt
  dieselben Deploy-Gates wie jeder andere Artikel.

  Die Engine füllt den Pool nach erfolgreichen Produktionstagen selbsttätig
  wieder auf (Reserve-Top-up) – der Pool trocknet also nie aus.

SICHERHEIT:
  * reserve:true-Entwürfe haben KEINE cadence_*-Felder → park_state liest
    sie als „manual“ (Frank-Schutz): keine andere Automatik fasst sie an.
  * Veröffentlicht wird NUR bis zum LIVE-Mindestziel und NUR an Mo/Mi/Fr
    (Guard identisch zu cadence_guard.PUBLICATION_DAYS).
  * Kein Reserve-Artikel wird je gelöscht oder überschrieben.

MODI:
  python3 scripts/reserve_pool.py --status          # Pool + heutige LIVE-Zahl
  python3 scripts/reserve_pool.py --publish-to-min  # Lücke bis Min füllen
  python3 scripts/reserve_pool.py --selftest        # Sabotage-Schutz
"""

import datetime
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"

sys.path.insert(0, str(ROOT / "scripts"))
import cadence_guard  # noqa: E402 – PUBLICATION_DAYS/load_posts (SSOT)


def now_utc_iso() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 and parts[0] == "" else ""


def is_reserve(text: str) -> bool:
    m = re.search(r"(?m)^reserve:\s*(true|yes|1)\s*$", _frontmatter(text))
    return bool(m)


def is_draft(text: str) -> bool:
    return bool(re.search(r"(?m)^draft:\s*true\s*$", _frontmatter(text)))


def reserve_drafts(posts_dir: Path = POSTS) -> list:
    """Alle Reserve-Entwürfe (draft: true + reserve: true), älteste zuerst."""
    out = []
    if not posts_dir.is_dir():
        return out
    for index in sorted(posts_dir.glob("*/index.md")):
        text = index.read_text(encoding="utf-8")
        if is_draft(text) and is_reserve(text):
            out.append(index)
    return out


def live_count_today(posts_dir: Path = POSTS) -> int:
    today = datetime.date.today()
    posts = cadence_guard.load_posts(posts_dir)
    return len(cadence_guard.published_on(posts, today))


def publish_one(index: Path, when=None) -> str:
    """Veröffentlicht EINEN Reserve-Artikel: draft:false, Datum = heute,
    reserve-Marke wird durch reserve_published ersetzt (Audit-Trail)."""
    text = index.read_text(encoding="utf-8")
    iso = when or now_utc_iso()
    text = re.sub(r"(?m)^date:\s*.*$", f"date: {iso}", text, count=1)
    text = re.sub(r"(?m)^draft:\s*true\s*$", "draft: false", text, count=1)
    text = re.sub(r"(?m)^reserve:\s*(true|yes|1)\s*$\n?",
                  f"reserve_published: {iso[:10]}\n", text, count=1)
    index.write_text(text, encoding="utf-8")
    return iso


def publish_to_min(min_per_day: int | None = None,
                   posts_dir: Path = POSTS) -> list:
    """Füllt die heutige LIVE-Lücke bis zum Mindestziel aus dem Reserve-Pool.

    Nur an Publikationstagen (Mo/Mi/Fr). Rückgabe: Liste veröffentlichter
    Slugs. Ist der Pool leer, bleibt die Lücke – die Endkontrolle meldet
    das Defizit dann als Issue (engine_issue --deficit)."""
    today = datetime.date.today()
    if today.weekday() not in cadence_guard.PUBLICATION_DAYS:
        print(f"Kein Publikationstag ({cadence_guard.DAYS_DE[today.weekday()]}) "
              f"– Reserve-Pool bleibt unangetastet.")
        return []
    if min_per_day is None:
        min_per_day = cadence_guard.effective_limits()[0]
    published = []
    for index in reserve_drafts(posts_dir):
        if live_count_today(posts_dir) >= min_per_day:
            break
        iso = publish_one(index)
        published.append(index.parent.name)
        print(f"  🆘 RESERVE live geschaltet: {index.parent.name} "
              f"(datiert {iso[:10]})")
    if published:
        print(f"Reserve-Pool: {len(published)} Artikel veröffentlicht – "
              f"jetzt {live_count_today(posts_dir)} live heute "
              f"(Ziel ≥ {min_per_day}).")
    else:
        live = live_count_today(posts_dir)
        pool = len(reserve_drafts(posts_dir))
        print(f"Reserve-Pool: keine Veröffentlichung nötig/möglich – "
              f"{live} live heute, Ziel ≥ {min_per_day}, Pool: {pool}.")
    return published


def run_selftest() -> list:
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        fx = Path(tmp) / "content" / "posts"
        fx.mkdir(parents=True)
        # Reserve-Entwurf
        d1 = fx / "2026-09-01-reserve-a"
        d1.mkdir()
        (d1 / "index.md").write_text(
            "---\ntitle: \"Reserve A\"\n"
            "date: 2026-09-01T06:00:00Z\ndraft: true\n"
            "reserve: true\n---\n\nBody.\n", encoding="utf-8")
        # normaler manueller Entwurf (ohne reserve) – darf NIE angefasst werden
        d2 = fx / "2026-09-01-manuell"
        d2.mkdir()
        (d2 / "index.md").write_text(
            "---\ntitle: \"Manuell\"\n"
            "date: 2026-09-01T06:00:00Z\ndraft: true\n"
            "---\n\nBody.\n", encoding="utf-8")
        pool = reserve_drafts(fx)
        if len(pool) != 1 or pool[0].parent.name != "2026-09-01-reserve-a":
            fehler.append(f"reserve_drafts filtert falsch: {[p.parent.name for p in pool]}")

        # publish_one: draft false, Datum heute, reserve-Marke ersetzt
        # (direkter Funktionsaufruf – unabhängig vom Wochentag testbar)
        published = pool[0]
        publish_one(published, when="2026-09-04T06:00:00Z")
        text = published.read_text(encoding="utf-8")
        if "draft: false" not in text or "reserve: true" in text:
            fehler.append("publish_one ließ draft/reserve-Marke falsch zurück")
        if "reserve_published: 2026-09-04" not in text:
            fehler.append("reserve_published-Audit-Zeile fehlt")
        if "date: 2026-09-04T06:00:00Z" not in text:
            fehler.append("Re-Dating auf heute fehlt")

        # manueller Entwurf bleibt unangetastet (Pool-Liste leer danach)
        if len(reserve_drafts(fx)) != 0:
            fehler.append("manueller Entwurf wurde in den Pool gezählt")
    return fehler


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        errs = run_selftest()
        if errs:
            print("🛑 RESERVE-POOL-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"   - {e}")
            return 2
        print("✅ Reserve-Pool-Selbsttest grün (Filter, Publish, "
              "Draft-Schutz, Audit-Zeile).")
        return 0

    if "--status" in args or not args:
        pool = reserve_drafts()
        live = live_count_today()
        min_d, max_d = cadence_guard.effective_limits()
        today = datetime.date.today()
        pub = today.weekday() in cadence_guard.PUBLICATION_DAYS
        print(f"Reserve-Pool: {len(pool)} Artikel (Ziel-Obergrenze siehe "
              f"Engine-Env RESERVE_TARGET)")
        for p in pool:
            print(f"  - {p.parent.name}")
        print(f"Heute ({cadence_guard.DAYS_DE[today.weekday()]}, "
              f"{today.isoformat()}): {live} live · Ziel {min_d}–{max_d} · "
              f"{'Publikationstag' if pub else 'kein Publikationstag'}.")
        return 0

    if "--publish-to-min" in args:
        publish_to_min()
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
