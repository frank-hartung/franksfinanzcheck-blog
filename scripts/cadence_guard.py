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

Park-Zustände (SSOT scripts/park_state.py, 31.08.2026):
  Jeder Zurückstufungs-Schreibvorgang nennt seinen Grund, damit ein geparkter
  Post nie wieder mehrdeutig ist:
    queue  draft:true + cadence_wait:true        → wird automatisch gefördert
    hold   draft:true + cadence_grund (ohne wait)→ braucht Korrektur, wird
           bewusst NICHT gefördert (publish_gate, check_uniqueness)
    manual draft:true ohne cadence_*             → Franks Entwurf, nie anfassen
    lost   draft:true + cadence_demoted ohne wait/grund → Bug (Flag verloren,
           Post für immer unsichtbar): wird von --fix / --integrity rearmt.
  Der Selbsttest friert alle fünf Zustände + Idempotenz + Promotion-Hygiene ein.

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
  python3 scripts/cadence_guard.py --integrity # nur Park-Zustände klären
                                               #   (rearmen/bereinigen, ohne
                                               #   Kadenz-Heilung und ohne
                                               #   Promotion – für Wartung)
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
import park_state  # noqa: E402  (SSOT für draft/cadence_wait/cadence_demoted/cadence_grund)

# Halte-Frist: so lange darf ein Post höchstens geparkt (hold) bleiben, bevor
# der Report ihn als Content-Verlust markiert (31.08.2026, Issue #129-Folge).
HOLD_WARN_TAGE = 7

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
        park = park_state.read(content)
        posts.append({
            "path": path,
            "slug": slug_of(path),
            "date": day,
            "date_raw": raw_iso or date_iso,
            "draft": bool(re.search(r"(?m)^draft:\s*true\s*$", content)),
            "wait": bool(re.search(r"(?m)^cadence_wait:\s*true\s*$", content)),
            # Park-Zustand (single source of truth: scripts/park_state.py)
            "state": park["state"],          # live|queue|hold|manual|lost
            "grund": park["grund"],
            "demoted": park["demoted"],
            "age_days": park["age_days"],
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
    """Abgelegt in park_state.set_field (SSOT) – hier nur als Kompatibilitäts-
    Alias, damit es genau EINE Implementierung der Frontmatter-Schreibweise
    gibt. value=False/None entfernt die Zeile."""
    return park_state.set_field(path, key, None if value is False else value)


def _set_draft(path, draft):
    """Alias auf park_state (draft-Zeile schreiben, sonst nichts)."""
    return park_state.set_draft(path, draft)


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
    """Stuft Verstöße auf draft zurück UND legt sie verbindlich in die
    Re-Queue (park_state.park: draft + cadence_wait + Zeitstempel + Grund).

    Draft-Schutz bleibt absolute Regel: ein bereits geparkter Post wird hier
    nicht noch einmal angefasst (dafür sorgt queue_integrity(), das den
    Zustand explizit unterscheidt: queue / hold / manual / lost)."""
    healed = []
    by_path = {p["path"]: p for p in posts}
    for path in paths:
        p = by_path.get(path)
        if not p or p["draft"]:
            continue
        if not do_fix:
            continue
        grund = f"kadenz: {reason}" if reason else "kadenz"
        if park_state.park(path, grund, now_utc_iso(), do_fix=True):
            healed.append(p)
            print(f"  🛡️  {p['slug']} → draft + Re-Queue ({reason})")
    return healed


def queue_integrity(posts, do_fix=False, verbose=None):
    """Re-Queue-INTEGRITÄT: macht den Park-Zustand wieder eindeutig.

    Fund der Klasse (Issue #129/Nachlese): Posts, deren `cadence_wait`-Flag
    auf einem der vielen Schreibwege verloren ging, sind für die Automatik
    nicht mehr von Franks manuellen Entwürfen zu unterscheiden – sie bleiben
    für immer unsichtbar (4 fertige Artikel) und ihre fehlenden URLs
    produzierten die defekten internen Links.

    Regeln (in dieser Reihenfolge, mehrfaches Laufen ist idempotent):
      lost   → Flag rearmen (NUR das Flag; Content und draft bleiben).
               publicationstag + Tageslimit entscheiden weiterhin allein über
               die Promotion, ein verlorener Post geht also nicht ungefragt
               live.
      stale  → Park-Rest an einem live-Post (cadence_wait, Grund oder
               Demoted-Marke) ist Müll der letzten Promotion → entfernen.
      hold   → Bewusste Blockade (publish_gate/check_uniqueness). Wird NIE
               rearmt, aber ab HOLD_WARN_TAGE im Report als Content-Verlust
               markiert (Verlust-Radar).
      manual → nie anfassen (Frank-Schutz).
    Rückgabe: dict(rearmed, cleaned, holds, aging).
    `verbose` (Default: wie do_fix) – Funde werden beim reinen Prüfen leise
    gezählt, damit ein Audit-Lauf nicht doppelt meldet."""
    if verbose is None:
        verbose = do_fix
    out = {"rearmed": [], "cleaned": [], "holds": [], "aging": []}
    for p in posts:
        if p["state"] == "lost":
            if do_fix:
                park_state.rearm(p["path"], "kadenz: Re-Queue-Flag "
                                            "wiederhergestellt (verloren)",
                                 now_utc_iso(), do_fix=True)
            out["rearmed"].append(p)
            if verbose:
                print(f"  🔁  {p['slug']} → Re-Queue-Flag wiederhergestellt "
                      f"(draft behalten, Promotion folgt am nächsten Slot)")
        elif p["state"] == "live" and park_state.rest_fields(p):
            # Rest einer Promotion: Park-Feld an einem live-Post. Harmlos,
            # aber der Zustand ist mehrdeutig – und eine saubere Promotion sähe
            # später wieder aus wie ein "lost"-Fall.
            out["cleaned"].append(p)
            if do_fix:
                park_state.clean_stale(p["path"], do_fix=True)
            if verbose:
                print(f"  🧹  {p['slug']} → Park-Rest am live-Post "
                      f"({', '.join(park_state.rest_fields(p))}): "
                      f"{'entfernt' if do_fix else 'geprüft (weg mit --fix)'}")
        elif p["state"] == "hold":
            out["holds"].append(p)
            if (p["age_days"] or 0) > HOLD_WARN_TAGE:
                out["aging"].append(p)
                if verbose:
                    print(f"  ⚠️  {p['slug']} seit {p['age_days']} Tagen "
                          f"gehalten ({p['grund']}) – bitte korrigieren "
                          f"oder freigeben")
    return out


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
        # release() = draft: false + SÄMTLICHE Park-Felder weg. Das ist der
        # entscheidende Unterschied zum alten Einzelflaggen-Löschen: danach ist
        # der Post wieder eindeutig "live" und kann nicht als "lost" fehl-
        # gedeutet werden (und ein spätes Gate-Halten schreibt seinen Grund).
        park_state.release(p["path"], do_fix=True)
        promoted.append(p)
        print(f"  ♻️  Re-Queue → live: {p['slug']} (neu datiert {today.isoformat()})")
    return promoted


def write_report(off_day, over_cap, under_days, healed, promoted,
                 min_d, max_d, count_by_day=None, integrity=None):
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
    # ---------- Re-Queue-Integrität (Park-Zustände) ----------
    posts_all = load_posts()
    states = {"queue": [], "hold": [], "manual": [], "lost": []}
    for p in posts_all:
        if p["state"] in states:
            states[p["state"]].append(p)
    L += ["", "## Re-Queue-Integrität (Park-Zustände)", "",
          f"- 🕓 in der Re-Queue (werden am nächsten Slot gefördert): "
          f"**{len(states['queue'])}**",
          f"- ✋ gehalten (Korrektur nötig, NIEMALS automatisch): "
          f"**{len(states['hold'])}**",
          f"- ✍️ manuelle Entwürfe (von der Automatik unberührt): "
          f"**{len(states['manual'])}**",
          f"- 🔁 wiederhergestellte Re-Queue-Flags: "
          f"**{len(integrity['rearmed']) if integrity else 0}**",
          f"- 🧹 Park-Reste an live-Posts (gefunden, weg mit --fix): "
          f"**{len(integrity['cleaned']) if integrity else 0}**", ""]
    if states["hold"]:
        L.append("### Gehaltene Posts (bitte prüfen/freigeben)")
        L.append("")
        for p in sorted(states["hold"], key=lambda x: x["slug"]):
            age = p["age_days"]
            war = f" · seit {age} Tagen" if age is not None else ""
            fahne = "⚠️ " if (age or 0) > HOLD_WARN_TAGE else ""
            L.append(f"- {fahne}`{p['slug']}` – {p['grund'] or 'Grund unbekannt'}"
                     f"{war}")
        L.append("")
    if integrity and integrity["aging"]:
        L.append(f"> 🛑 **Verlust-Radar:** {len(integrity['aging'])} Post(s) "
                 f"liegen länger als {HOLD_WARN_TAGE} Tage gehalten fest – "
                 f"jeder davon ist ein fertiger Artikel, der nicht sichtbar "
                 f"ist. Korrigieren und `draft: false` setzen (oder "
                 f"`cadence_grund`-Zeile löschen) → der nächste Slot fördert.")
        L.append("")

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
    under_days, healed, promoted, integrity).

    Reihenfolge ist Absicht: erst Park-Zustände klären (rearmen/bereinigen),
    dann Kadenz heilen, dann Re-Queue bis zum Tageslimit füllen – so wird ein
    wiederhergestellter Post im selben Lauf gefördert, statt auf den nächsten
    Tag zu warten, und die Integrität bleibt trotzdem unabhängig davon
    erhalten (Promotion entscheidet allein Publikationstag + Kapazität)."""
    min_d, max_d = effective_limits()
    posts = load_posts(posts_dir)
    integrity = queue_integrity(posts, do_fix=do_fix)
    if do_fix and (integrity["rearmed"] or integrity["cleaned"]):
        posts = load_posts(posts_dir)          # reparierte Zustandsdaten sehen
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

    # Report-Sicht auf die Park-Zustände (nach allen Heilungen, ohne
    # nochmal zu reparieren – der Pass oben ist idempotent).
    integrity_report = queue_integrity(load_posts(posts_dir), do_fix=False,
                                       verbose=False)
    write_report(off_day, over_cap, under_days, healed, promoted, min_d, max_d,
                 count_by_day=_count_by_day(posts), integrity=integrity_report)
    return off_day, over_cap, under_days, healed, promoted, integrity


def load_post_state(posts_root, slug):
    """Park-Felder eines Fixtures lesen – True, wenn NOCH eins steht.
    Nur für den Selbsttest (Reinigungs-Nachweis)."""
    path = os.path.join(posts_root, slug, "index.md")
    content = open(path, encoding="utf-8").read()
    st = park_state.read(content)
    return bool(st["wait"] or st["demoted"] or st["grund"])


def run_selftest():
    """Selbsttest mit synthetischen Fixtures in einem Temp-Verzeichnis.
    Beweist: Off-Day-Erkennung, Over-Cap-Heilung, Re-Queue-Kapazität,
    Draft-Schutz. Exit 2, wenn der Guard selbst defekt ist."""
    errors = []
    min_d, max_d = 2, 3

    def mk(tmp, slug, date_raw, draft, wait=False, demoted=None,
           grund=None):
        d = os.path.join(tmp, "content", "posts", slug)
        os.makedirs(d, exist_ok=True)
        extra = ""
        if wait:
            extra += "cadence_wait: true\n"
        if demoted:
            extra += f"cadence_demoted: {demoted}\n"
        if grund:
            extra += f'cadence_grund: "{grund}"\n'
        fm = (f"---\ntitle: \"{slug[:20]}\"\n"
              f"description: \"Test\"\ndate: {date_raw}\ndraft: {'true' if draft else 'false'}\n"
              + extra
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
        # Park-Zustände (31.08.2026 – Issue #129-Nachlese): verlorenes Flag,
        # bewusste Gate-Hemmung, Re-Queue-Rest an einem Live-Post.
        mk(tmp, "2026-08-20-verloren-a", "2026-08-31T04:02:49Z", True,
           demoted="2026-08-26T13:46:19Z")
        mk(tmp, "2026-08-20-gehemmt-b", "2026-08-30T06:00:00Z", True,
           demoted="2026-08-30T06:05:00Z",
           grund="publish-gate: Zeichenlänge nicht bestanden")
        mk(tmp, "2026-08-10-stale-flag", "2026-08-10T04:00:00Z", False,
           wait=True, demoted="2026-08-09T06:00:00Z")  # Promotion ohne
                                                       # Feldbereinigung
        # derselbe Rest, nur als Grund-Marke ohne Flag (Live-Artikel mit
        # Gate-Spur) – muss ebenfalls weg, sonst bleibt er ewig stehen
        mk(tmp, "2026-08-12-rest-marke", "2026-08-12T04:00:00Z", False,
           grund="publish-gate: Rest nach Freigabe")

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

        # Park-Zustände müssen unterscheidbar sein (SSOT park_state)
        states = {p["slug"]: p["state"] for p in posts}
        for slug, want in (("2026-08-19-wartend-a", "queue"),
                           ("2026-08-19-draft-frei", "manual"),
                           ("2026-08-17-mo-post-a", "live"),
                           ("2026-08-20-verloren-a", "lost"),
                           ("2026-08-20-gehemmt-b", "hold")):
            if states.get(slug) != want:
                errors.append(f"Park-Zustand {slug}: {states.get(slug)} "
                              f"statt {want}")

        # Integritäts-Pass: rearmt verlorene Flags, lässt Hemmung + manuelle
        # Entwürfe unberührt, idempotent.
        integ = queue_integrity(load_posts(posts_root), do_fix=True)
        if [p["slug"] for p in integ["rearmed"]] != ["2026-08-20-verloren-a"]:
            errors.append(f"Rearm falsch: {[p['slug'] for p in integ['rearmed']]}")
        again = queue_integrity(load_posts(posts_root), do_fix=True)
        if again["rearmed"] or again["cleaned"]:
            errors.append("Integritäts-Pass nicht idempotent")
        post_fix = {p["slug"]: p for p in load_posts(posts_root)}
        pf = post_fix["2026-08-20-verloren-a"]
        if not (pf["wait"] and pf["draft"] and pf["state"] == "queue"):
            errors.append("Rearm hat draft/Inhalt verändert oder wirkt nicht")
        body = open(os.path.join(posts_root, "2026-08-20-verloren-a",
                                 "index.md"), encoding="utf-8").read()
        if "Body." not in body:
            errors.append("Rearm hat den Body beschädigt")
        held = post_fix["2026-08-20-gehemmt-b"]
        if held["wait"] or held["state"] != "hold":
            errors.append("Gate-Hemmung wurde rearmt (verbotene Promotion!)")
        if post_fix["2026-08-19-draft-frei"]["state"] != "manual":
            errors.append("Manueller Entwurf durch Integrität verändert")

        # Stale-Rest an einem LIVE-Post wird entfernt (sonst sieht jede
        # saubere Promotion später wie ein "lost"-Fall aus).
        stale = [p["slug"] for p in integ["cleaned"]]
        if "2026-08-10-stale-flag" not in stale:
            errors.append(f"Stale-Flag nicht bereinigt: {stale}")
        if load_post_state(posts_root, "2026-08-10-stale-flag"):
            errors.append("Stale-Flag steht noch im Frontmatter")
        if "2026-08-12-rest-marke" not in stale:
            errors.append(f"Grund-Marke am live-Post nicht bereinigt: {stale}")
        rest = {p["slug"]: p for p in load_posts(posts_root)}["2026-08-12-rest-marke"]
        if rest["state"] != "live" or rest["draft"] or rest["grund"]:
            errors.append("live-Post durch Rest-Bereinigung beschädigt "
                          f"(state: {rest['state']})")

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
        # Promotion räumt ALLE Park-Felder ab – sonst wäre der nächste
        # Hin-und-Her wieder ein "lost"-Fall (Ursache von Issue #129).
        if not promoted:
            errors.append("Re-Queue fördert nichts (Kapazitäts-Regression?)")
        else:
            promoted_now = {p["slug"]: p for p in posts}[promoted[0]["slug"]]
            if (promoted_now["wait"] or promoted_now["demoted"]
                    or promoted_now["grund"] or promoted_now["state"] != "live"):
                errors.append("Promotion hat Park-Felder nicht vollständig "
                              f"geräumt: {promoted_now}")

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
        print("✅ CADENCE-SELFTEST bestanden (Off-Day, Over-Cap, Re-Queue, "
              "Draft-Schutz, Park-Zustände queue/hold/manual/lost/stale, "
              "Promotion-Hygiene, Idempotenz).")
        sys.exit(0)

    do_fix = "--fix" in args
    if "--integrity" in args:
        # Nur die Park-Zustände klären – KEINE Kadenz-Heilung, KEINE
        # Promotion. Für Wartung von Hand und für CI-Schritte, die Flags
        # reparieren sollen, ohne den Veröffentlichungszeitpunkt zu verschieben.
        posts = load_posts()
        integ = queue_integrity(posts, do_fix=True)
        posts = load_posts()
        min_d, max_d = effective_limits()
        off_day, over_cap, under_days = find_violations(posts, min_d, max_d)
        write_report(off_day, over_cap, under_days, [], [], min_d, max_d,
                     count_by_day=_count_by_day(posts),
                     integrity=queue_integrity(posts, do_fix=False))
        print(f"Re-Queue-Integrität: {len(integ['rearmed'])} Flag(s) "
              f"wiederhergestellt, {len(integ['cleaned'])} Rest-Flag(s) "
              f"bereinigt, {len(integ['holds'])} gehalten, "
              f"{len(integ['aging'])} davon über Frist.")
        sys.exit(0)
    if "--requeue" in args:
        _, max_d = effective_limits()
        posts = load_posts()
        # Vor der Förderung die Park-Zustände klären: ein "lost"-Post wäre
        # sonst unsichtbar, obwohl er fertig und förderfähig ist.
        queue_integrity(posts, do_fix=True)
        posts = load_posts()
        promoted = requeue_to_capacity(posts, max_d, do_fix=True)
        min_d, _ = effective_limits()
        off_day, over_cap, under_days = find_violations(load_posts(), min_d, max_d)
        write_report(off_day, over_cap, under_days, [], promoted, min_d, max_d,
                     count_by_day=_count_by_day(load_posts()),
                     integrity=queue_integrity(load_posts(), do_fix=False,
                                                verbose=False))
        print(f"Re-Queue: {len(promoted)} Post(s) bis zum Tageslimit promoted.")
        sys.exit(0)

    lost = [p for p in load_posts() if p["state"] == "lost"]
    if lost and not do_fix and "--integrity" not in args:
        # Verlorene Re-Queue-Flags = stiller Content-Verlust: im Prüfmodus
        # harter Fund (1), damit die Kette nicht "alles grün" meldet, während
        # fertige Artikel unsichtbar liegen. --fix heilt sie.
        print(f"🛑 {len(lost)} Post(s) in der Kadenz-Parkliste OHNE "
              f"cadence_wait-Feld – die Flagge ist verloren, die Artikel "
              f"bleiben dauerhaft unsichtbar.")
        for p in lost:
            print(f"   - {p['slug']} (gedemotet {p['demoted'] or '?'})")
        print("   Heilung: python3 scripts/cadence_guard.py --fix "
              "(setzt nur das Flag – keine Promotion, kein Publish)")
        sys.exit(1)

    off_day, over_cap, under_days, healed, promoted, integrity = run_audit(
        do_fix=do_fix)
    if integrity["rearmed"] or integrity["cleaned"]:
        ruhm = "bereinigt" if do_fix else "gefunden (weg mit --fix)"
        print(f"🔧 Re-Queue-Integrität: {len(integrity['rearmed'])} Flag(s) "
              f"wiederhergestellt, {len(integrity['cleaned'])} Park-Rest(e) "
              f"an live-Posts {ruhm}.")
    if integrity["aging"]:
        print(f"⚠️  Verlust-Radar: {len(integrity['aging'])} gehaltene(r) "
              f"Post(s) länger als {HOLD_WARN_TAGE} Tage (siehe "
              f"CADENCE-GATE-REPORT.md).")
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
