#!/usr/bin/env python3
"""cadence_guard.py – KADENZ-GUARD (Single Source of Truth, 26.08.2026)

Harte, durchgängige Durchsetzung der DAUERVORGABE (CADENCE-REPORT.md,
Regel 2; festgelegt 19.08.2026, Frank):

  • Veröffentlichung NUR montags, mittwochs, freitags (Mo=0, Mi=2, Fr=4).
  • 2 bis 3 Artikel pro Publikationstag (MIN_ARTIKEL_PRO_TAG=2 bis
    MAX_ARTIKEL_PRO_TAG=3, Defaults; Env-übersteuerbar, Floor bei 2).

Warum diese Wache existiert (Befund 26.08.2026):
  Die Engine (engine_generate.py) hatte zwar einen Wochentags-Guard –
  aber der galt NUR für die Artikel, die die Engine selbst erzeugt.
  Artikel, die über andere Pfade in den Bestand gelangten (manuelle
  Commits, publish.py, Batch-Neupflege), konnten die Routine trotzdem
  brechen – und deploy.yml hatte KEINEN Gate-Schritt: Was auf main lag,
  ging ungeprüft live. Ergebnis waren Live-Posts an Di/So und Tage mit
  4 Posts (z. B. 16.08./18.08./20.08. So/Di/Do, 14.08./26.08. mit 4).

  Ab sofort ist die Kadenz an ALLEN Publikations-Punkten hart:
    1. content-engine-v2.yml  – Kadenz-Heilung VOR der Generierung
    2. publish.py             – manuelles Veröffentlichen wird an
                                Wochentag + Tageslimit gebunden
    3. deploy.yml             – harte Vor-Veröffentlichungs-Kontrolle:
                                Verstöße werden ZUM BUILD-ZEITPUNKT
                                geheilt (Zurückstufung auf draft),
                                nie veröffentlicht
    4. blog-health-daily.yml  – tägliche Selbstheilung (auch ohne Deploy)

Selbstheilung (sofortig, konvergent, nichts geht verloren):
  • Verstöße (off-day published / > MAX an einem Tag) werden auf
    `draft: true` zurückgestuft UND mit `cadence_wait: true` in die
    Re-Queue gelegt. Der LIVE-BLOG ist damit SOFORT wieder korrekt.
  • Beim nächsten Publikationstag (Engine-Slot) promotes
    requeue_to_capacity() die wartenden Posts – in der Reihenfolge
    ihres Erzeugungsdatums – bis das Tageslimit (MAX) erreicht ist und
    datiert sie auf den Veröffentlichungstag neu. So bleibt die Routine
    (2–3/Tag) zu 100 % gewahrt, aber kein Content geht verloren.
  • Re-queue-Promotions passieren NUR auf Publikationstagen und NUR
    innerhalb des Tageslimits – die Engine füllt danach den Rest mit
    neuen Artikeln auf (bestehende Logik, zählt die promoted Posts mit).

Niemals:
  • Entwürfe (draft: true OHNE cadence_wait) werden nie angefasst.
  • Es wird nie gelöscht – nur zurückgestuft/geheilt.

Aufruf:
  python3 scripts/cadence_guard.py             # Audit (Alias: --check)
  python3 scripts/cadence_guard.py --check     # nur prüfen, Exit 1 bei Verstoß
  python3 scripts/cadence_guard.py --fix       # prüfen + heilen (Zurückstufung
                                               #   + Re-Queue + Report)
  python3 scripts/cadence_guard.py --requeue   # wartende Posts bis zum
                                               #   Tageslimit promoten (Engine)
  python3 scripts/cadence_guard.py --selftest  # Selbsttest mit Fixtures
                                               #   (Exit 2 = Guard defekt)

Report: CADENCE-GATE-REPORT.md (im Repo-Root, commit-freundlich).
Exit-Codes: 0 = sauber (oder geheilt) · 1 = Verstöße gefunden (--check)
            · 2 = Selbsttest/Interna defekt (Gate muss abbrechen).
"""
import datetime
import glob
import os
import re
import sys
import tempfile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
REPORT_PATH = os.path.join(BLOG_DIR, "CADENCE-GATE-REPORT.md")

sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import slug_of, frontmatter_date  # noqa: E402

# ---------------------------------------------------------------------------
# DAUERVORGABE (CADENCE-REPORT.md Regel 2, 19.08.2026): Mo/Mi/Fr, 2–3/Tag.
# PUBLICATION_DAYS ist die EINZIGE Definition – Engine und alle Guards
# importieren von hier (keine zweite Kopie mehr, die sich driftet).
# ---------------------------------------------------------------------------
PUBLICATION_DAYS = {0, 2, 4}  # Montag, Mittwoch, Freitag (Python.weekday)

DAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
           "Samstag", "Sonntag"]


def effective_limits():
    """(min_per_day, max_per_day) aus Env, Default 2/3, mit Floor.

    Dauervorgabe-Floor: Werte unter 2 werden auf 2 angehoben (der
    Workflow-Legacy-Fallback „1“ darf die Kadenz nicht drücken)."""
    try:
        max_d = int(os.environ.get("MAX_ARTIKEL_PRO_TAG") or "3")
    except ValueError:
        max_d = 3
    try:
        min_d = int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2")
    except ValueError:
        min_d = 2
    max_d = max(2, max_d)
    min_d = max(2, min_d)
    if min_d > max_d:
        min_d = max_d
    return min_d, max_d


def is_publication_day(day):
    """True für Mo/Mi/Fr (Day mit .weekday() oder datetime.date)."""
    return day.weekday() in PUBLICATION_DAYS


def now_utc_iso():
    """UTC-Zeitstempel (1 Minute zurück – nie ein Future-Post)."""
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_posts(posts_dir=None):
    """Alle Posts mit den Kadenz-relevanten Feldern.

    Das Datum-FELD (frontmatter `date:`) ist die Single Source of Truth
    für den Veröffentlichungstag – nicht der Ordner-Datumspräfix (der
    bleibt bei Re-Queue/Re-Dating bewusst erhalten, damit URLs, Covers
    und interne Links stabil bleiben)."""
    posts_dir = posts_dir or POSTS_DIR
    posts = []
    if not os.path.isdir(posts_dir):
        return posts
    paths = sorted(
        glob.glob(os.path.join(posts_dir, "*.md"))
        + glob.glob(os.path.join(posts_dir, "*", "index.md"))
    )
    for path in set(paths):
        if os.path.basename(path) == "_index.md":
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        date_iso = frontmatter_date(content)
        # Vollständiger Zeitstempel für deterministische Reihenfolge
        # ("zum Letzten" veröffentlicht = späterer Zeitstempel)
        m_raw = re.search(r"(?m)^date:\s*[\"']?([0-9T:\-Z]+)", content)
        raw_iso = m_raw.group(1) if m_raw else (date_iso or "")
        if not date_iso:
            # Fallback: Ordner-Datumspräfix (Legacy/Defensive)
            m = re.match(r"(\d{4}-\d{2}-\d{2})", slug_of(path))
            date_iso = m.group(1) if m else None
        if not date_iso:
            continue
        try:
            day = datetime.date.fromisoformat(date_iso)
        except ValueError:
            continue
        posts.append({
            "path": path,
            "slug": slug_of(path),
            "date": day,
            "date_raw": raw_iso or date_iso,
            "draft": bool(re.search(r"(?m)^draft:\s*true\s*$", content)),
            "wait": bool(re.search(r"(?m)^cadence_wait:\s*true\s*$", content)),
        })
    return posts


def published_on(posts, day):
    """Alle VERÖFFENTLICHTE Posts eines Datums (draft: false)."""
    return [p for p in posts if p["date"] == day and not p["draft"]]


def find_violations(posts, min_d, max_d):
    """Liefert (off_day, over_cap, under_days):
      off_day:  [post]  – veröffentlicht an Di/Do/Sa/So
      over_cap: [post]  – Posts, die über dem Tages-Max liegen (so viele,
                          dass der Resttag exakt max_d hat)
      under_days: [(day, count)] – Publikationstage unter Mindestziel
                 (NUR Hinweis – die Engine-Slots heilen per Auffüllung)
    Deterministische Sortierung: erst nach Zeitstempel, dann nach Slug."""
    off_day = [p for p in posts
               if not p["draft"] and not is_publication_day(p["date"])]

    over_cap = []
    by_day = {}
    for p in posts:
        if not p["draft"]:
            by_day.setdefault(p["date"], []).append(p)
    for day in sorted(by_day):
        live = by_day[day]
        if not is_publication_day(day):
            continue  # Off-Day-Posts werden oben komplett erfasst
        excess = len(live) - max_d
        if excess > 0:
            # Die ZUM LETZTEN veröffentlichten Posts fliegen raus
            # (Zeitstempel → Slug, deterministisch).
            live_sorted = sorted(live, key=lambda p: (p["date_raw"], p["slug"]))
            over_cap.extend(live_sorted[-excess:])

    under_days = []
    today = datetime.date.today()
    for day in sorted(by_day):
        if is_publication_day(day) and day <= today:
            n = len(by_day[day])
            # Nur volle Tage bewerten: heutiger Tag läuft bis zum
            # letzten Slot (19:40 MESZ) noch – wird vom Engine-Report
            # geführt, hier nicht doppelt.
            if day < today and n < min_d:
                under_days.append((day, n))
    return off_day, over_cap, under_days


def _set_frontmatter_flag(path, key, value=True):
    """Setzt/ersetzt eine Flag-Zeile im Frontmatter (nach `draft:`).
    value=False entfernt die Zeile. Idempotent, berührt sonst nichts."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    # Frontmatter-Region: zwischen den ersten zwei '---'
    if not (lines and lines[0].strip() == "---"):
        return False
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return False

    key_re = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    existing = [i for i in range(1, end) if lines[i].startswith(key + ":")]
    draft_i = next((i for i in range(1, end)
                    if lines[i].startswith("draft:")), None)
    anchor = (draft_i + 1) if draft_i is not None else end

    if value is False:
        if existing:
            del lines[existing[0]]
            # (bei mehreren Duplikaten nur das erste entfernen;
            #  Duplikate wären ohnehin ein Frontmatter-Fehler)
        else:
            return False
    else:
        text = f"{key}: {value}\n" if not isinstance(value, bool) else \
            f"{key}: {'true' if value else 'false'}\n"
        if existing:
            lines[existing[0]] = text
        else:
            lines.insert(anchor, text)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def _set_draft(path, draft):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new = re.sub(r"(?m)^draft:\s*(true|false)\s*$",
                 f"draft: {'true' if draft else 'false'}", content, count=1)
    if new != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return True
    return False


def _set_date(path, iso):
    """Setzt die `date:`-Zeile auf einen neuen ISO-Wert (Re-Dating)."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new = re.sub(r"(?m)^date:\s*.*$", f"date: {iso}", content, count=1)
    if new != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return True
    return False


def demote(posts, paths, reason, do_fix):
    """Stuft Verstöße auf draft: true + cadence_wait: true zurück."""
    healed = []
    by_path = {p["path"]: p for p in posts}
    for path in paths:
        p = by_path.get(path)
        if not p or p["draft"]:
            continue
        if not do_fix:
            continue
        if _set_draft(path, True):
            _set_frontmatter_flag(path, "cadence_wait", True)
            _set_frontmatter_flag(path, "cadence_demoted", now_utc_iso())
            healed.append(p)
            print(f"  🛡️  {p['slug']} → draft + Re-Queue ({reason})")
    return healed


def requeue_to_capacity(posts, max_d, do_fix=True, now_fn=None):
    """Promotiert die ältesten wartenden Posts (cadence_wait) bis das
    Tageslimit (max_d) erreicht ist – mit Re-Dating auf heute.

    now_fn: Zeitstempel-Lieferant (Default: now_utc_iso) – injizierbar
    für den deterministischen Selbsttest.
    Rückgabe: Liste der gepromoted Posts (leer bei 0 Kapazität)."""
    now_fn = now_fn or now_utc_iso
    today = datetime.date.today()
    if not is_publication_day(today):
        return []
    capacity = max_d - len(published_on(posts, today))
    if capacity <= 0:
        return []
    waiting = [p for p in posts if p["draft"] and p["wait"]]
    waiting.sort(key=lambda p: (p["date_raw"], p["slug"]))
    promoted = []
    for p in waiting[:capacity]:
        if not do_fix:
            break
        iso = now_fn()
        _set_date(p["path"], iso)
        _set_draft(p["path"], False)
        _set_frontmatter_flag(p["path"], "cadence_wait", False)
        promoted.append(p)
        print(f"  ♻️  Re-Queue → live: {p['slug']} (neu datiert {today.isoformat()})")
    return promoted


def write_report(off_day, over_cap, under_days, healed, promoted,
                 min_d, max_d, count_by_day=None):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = [
        "# 📅 CADENCE-GATE-REPORT (Kadenz-Wache, 26.08.2026)",
        "",
        f"**Letzter Lauf:** {now}",
        "",
        f"**Dauervorgabe:** nur Mo/Mi/Fr · {min_d}–{max_d} Artikel pro Publikationstag",
        f"**Regelwerk:** `CADENCE-REPORT.md` Regel 2 · `scripts/cadence_guard.py`",
        "",
    ]
    if count_by_day:
        L += ["## Live-Posts pro Tag", ""]
        for day in sorted(count_by_day):
            n = count_by_day[day]
            wd = DAYS_DE[day.weekday()]
            ok = is_publication_day(day) and min_d <= n <= max_d
            mark = "✅" if ok else ("⚠️" if is_publication_day(day) else "🛑")
            note = "" if ok else (" (über Max)" if n > max_d else
                                  (" (unter Min)" if n < min_d else " (kein Publikationstag)"))
            L.append(f"- {mark} {day.isoformat()} ({wd}): {n}{note}")
        L.append("")
    L += ["## Aktiver Befund", ""]
    if not off_day and not over_cap:
        L.append("- ✅ Keine Kadenz-Verstöße im Bestand.")
    for p in off_day:
        L.append(f"- 🛑 Off-Day veröffentlicht: `{p['slug']}` ({p['date'].isoformat()}, "
                 f"{DAYS_DE[p['date'].weekday()]})")
    for p in over_cap:
        L.append(f"- 🛑 Über Tages-Max: `{p['slug']}` ({p['date'].isoformat()})")
    if under_days:
        L.append("")
        L += ["### Mindestziel-Defizit (Engine-Slots füllen auf)", ""]
        for day, n in under_days:
            L.append(f"- ⚠️ {day.isoformat()} ({DAYS_DE[day.weekday()]}): "
                     f"nur {n} von {min_d}–{max_d} (Fallback-Slots heilen nach)")
    L += ["", "## Letzte Heilungen", ""]
    if healed:
        for p in healed:
            L.append(f"- Zurückgestuft + Re-Queue: `{p['slug']}`")
    if promoted:
        for p in promoted:
            L.append(f"- Aus Re-Queue live gesetzt: `{p['slug']}`")
    if not healed and not promoted:
        L.append("- – (nichts in diesem Lauf)")
    L += [
        "",
        "_Wird von `cadence_guard.py` bei jedem Kadenz-Lauf aktualisiert "
        "(Deploy-Gate, Content-Engine, Blog-Health)._",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return REPORT_PATH


def _count_by_day(posts):
    c = {}
    for p in posts:
        if not p["draft"]:
            c[p["date"]] = c.get(p["date"], 0) + 1
    return c


def run_audit(posts_dir=None, do_fix=False):
    """Audit + optionale Heilung. Rückgabe: (off_day, over_cap,
    under_days, healed, promoted)."""
    min_d, max_d = effective_limits()
    posts = load_posts(posts_dir)
    off_day, over_cap, under_days = find_violations(posts, min_d, max_d)

    healed = []
    if (off_day or over_cap) and do_fix:
        print(f"Kadenz-Heilung: {len(off_day)} Off-Day + {len(over_cap)} Over-Cap …")
        healed = demote(posts, [p["path"] for p in off_day],
                        f"kein Publikationstag ({DAYS_DE[off_day[0]['date'].weekday()]})"
                        if off_day else "", do_fix)
        healed += demote(posts, [p["path"] for p in over_cap],
                         "über Tages-Max", do_fix)
        # Nach der Heilung neu laden (doppelte Liste vermeiden)
        posts = load_posts(posts_dir)
        off_day, over_cap, under_days = find_violations(posts, min_d, max_d)

    promoted = []
    if do_fix:
        promoted = requeue_to_capacity(posts, max_d, do_fix=True)
        posts = load_posts(posts_dir)

    write_report(off_day, over_cap, under_days, healed, promoted, min_d, max_d,
                 count_by_day=_count_by_day(posts))
    return off_day, over_cap, under_days, healed, promoted


def run_selftest():
    """Selbsttest mit synthetischen Fixtures in einem Temp-Verzeichnis.
    Beweist: Off-Day-Erkennung, Over-Cap-Heilung, Re-Queue-Kapazität,
    Draft-Schutz. Exit 2, wenn der Guard selbst defekt ist."""
    errors = []
    min_d, max_d = 2, 3

    def mk(tmp, slug, date_raw, draft, wait=False):
        d = os.path.join(tmp, "content", "posts", slug)
        os.makedirs(d, exist_ok=True)
        fm = (f"---\ntitle: \"{slug[:20]}\"\n"
              f"description: \"Test\"\ndate: {date_raw}\ndraft: {'true' if draft else 'false'}\n"
              + (f"cadence_wait: {'true' if wait else 'false'}\n" if wait else "")
              + 'categories: ["Ratgeber"]\n---\n\nBody.\n')
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as f:
            f.write(fm)

    with tempfile.TemporaryDirectory() as tmp:
        posts_root = os.path.join(tmp, "content", "posts")
        # 2026-08-17 = Montag, 2026-08-18 = Dienstag (Off-Day),
        # 2026-08-19 = Mittwoch, 2026-08-16 = Sonntag (Off-Day)
        mk(tmp, "2026-08-17-mo-post-a", "2026-08-17T06:00:00Z", False)
        mk(tmp, "2026-08-17-mo-post-b", "2026-08-17T06:10:00Z", False)
        mk(tmp, "2026-08-17-mo-post-c", "2026-08-17T06:20:00Z", False)
        mk(tmp, "2026-08-17-mo-post-d", "2026-08-17T06:30:00Z", False)  # 4. am Mo → über Cap
        mk(tmp, "2026-08-18-di-post-a", "2026-08-18T06:00:00Z", False)  # Off-Day
        mk(tmp, "2026-08-16-so-post-a", "2026-08-16T06:00:00Z", False)  # Off-Day
        mk(tmp, "2026-08-19-mi-post-a", "2026-08-19T06:00:00Z", False)
        mk(tmp, "2026-08-19-mi-post-b", "2026-08-19T06:10:00Z", False)
        mk(tmp, "2026-08-19-wartend-a", "2026-08-10T06:00:00Z", True, wait=True)
        mk(tmp, "2026-08-19-wartend-b", "2026-08-11T06:00:00Z", True, wait=True)
        mk(tmp, "2026-08-19-draft-frei", "2026-08-19T00:00:00Z", True)  # NICHT warten

        posts = load_posts(posts_root)
        off_day, over_cap, _ = find_violations(posts, min_d, max_d)
        slugs_off = sorted(p["slug"] for p in off_day)
        if slugs_off != ["2026-08-16-so-post-a", "2026-08-18-di-post-a"]:
            errors.append(f"Off-Day-Erkennung falsch: {slugs_off}")
        if sorted(p["slug"] for p in over_cap) != ["2026-08-17-mo-post-d"]:
            errors.append(f"Over-Cap-Erkennung falsch: "
                          f"{[p['slug'] for p in over_cap]}")

        # Heilung
        demote(posts, [p["path"] for p in off_day + over_cap], "test", True)
        posts = load_posts(posts_root)
        still_live = [p["slug"] for p in posts
                      if p["date"].isoformat() in ("2026-08-17",) and not p["draft"]]
        if len(still_live) != 3:
            errors.append(f"Over-Cap-Heilung falsch: noch {len(still_live)} live am Mo")
        if not all(p["wait"] for p in posts
                   if p["slug"] in ("2026-08-18-di-post-a", "2026-08-16-so-post-a")):
            errors.append("Off-Day-Posts wurden nicht in die Re-Queue gelegt")
        if any(p["wait"] for p in posts if p["slug"] == "2026-08-19-draft-frei"):
            errors.append("Fremd-Entwurf wurde angefasst (Draft-Schutz verletzt)")

        # Re-Queue-Kapazität: Mi 2026-08-19 hat 2 live; requeue-to-max-3
        # dürfte genau 1 der 2 Wartenden fördern (den ältesten). Für
        # Determinismus werden "heute" (FakeDate) und der neue
        # Zeitstempel (now_fn) injiziert.
        real_today = datetime.date
        fake_day = datetime.date(2026, 8, 19)

        class FakeDate(datetime.date):
            @classmethod
            def today(cls):
                return fake_day
        try:
            datetime.date = FakeDate  # type: ignore
            posts = load_posts(posts_root)
            promoted = requeue_to_capacity(
                posts, max_d, do_fix=True,
                now_fn=lambda: "2026-08-19T06:30:00Z")
        finally:
            datetime.date = real_today  # type: ignore
        if [p["slug"] for p in promoted] != ["2026-08-19-wartend-a"]:
            errors.append(f"Re-Queue-Kapazität falsch: "
                          f"{[p['slug'] for p in promoted]}")
        posts = load_posts(posts_root)
        mi_live = [p for p in posts if p["date"].isoformat() == "2026-08-19"
                   and not p["draft"]]
        if len(mi_live) != 3:
            errors.append(f"Re-Queue-Resultat falsch: {len(mi_live)} live am Mi "
                          f"(erwartet 3 = Cap)")

    return errors


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        errs = run_selftest()
        if errs:
            print("🛑 CADENCE-SELFTEST FEHLGESCHLAGEN – der Guard ist defekt:")
            for e in errs:
                print(f"   - {e}")
            sys.exit(2)
        print("✅ CADENCE-SELFTEST bestanden (Off-Day, Over-Cap, Re-Queue, Draft-Schutz).")
        sys.exit(0)

    do_fix = "--fix" in args
    if "--requeue" in args:
        _, max_d = effective_limits()
        posts = load_posts()
        promoted = requeue_to_capacity(posts, max_d, do_fix=True)
        min_d, _ = effective_limits()
        off_day, over_cap, under_days = find_violations(load_posts(), min_d, max_d)
        write_report(off_day, over_cap, under_days, [], promoted, min_d, max_d,
                     count_by_day=_count_by_day(load_posts()))
        print(f"Re-Queue: {len(promoted)} Post(s) bis zum Tageslimit promoted.")
        sys.exit(0)

    off_day, over_cap, under_days, healed, _ = run_audit(do_fix=do_fix)
    total = len(off_day) + len(over_cap)
    if total == 0:
        print(f"✅ Kadenz sauber: nur Mo/Mi/Fr, keine Über-Max-Tage "
              f"({len(off_day)} Off-Day, {len(over_cap)} Over-Cap).")
        if under_days:
            for day, n in under_days:
                print(f"   ⚠️ {day.isoformat()}: nur {n} Posts (Min {effective_limits()[0]}) "
                      f"– Fallback-Slots heilen nach.")
        sys.exit(0)
    if do_fix:
        print(f"✅ Kadenz-Heilung abgeschlossen: {len(healed)} Post(s) "
              f"→ draft + Re-Queue. Live-Blog ist wieder konform.")
        sys.exit(0)
    print(f"🛑 {total} Kadenz-Verstöße gefunden (Off-Day: {len(off_day)}, "
          f"Over-Cap: {len(over_cap)}). Heilung: python3 scripts/cadence_guard.py --fix")
    for p in off_day + over_cap:
        print(f"   - {p['slug']} ({p['date'].isoformat()})")
    sys.exit(1)


if __name__ == "__main__":
    main()
