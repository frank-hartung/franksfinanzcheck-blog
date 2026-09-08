#!/usr/bin/env python3
# ============================================================
#  RESEARCH-ENGINE – tägliche Recherche (AGC-Parität, Stufe 2)
#  ------------------------------------------------------------
#  AGC Studio betreibt "6 Research-Teams", die täglich 15–30-seitige
#  strategische Reports erzeugen und automatisch an die Content-Agenten
#  geroutet werden. Dieses Skript bildet das DETERMINISTISCH + sicher ab:
#
#     TEAM 1 trending       – Signale aus data/aktuelle_entwicklungen.yaml
#     TEAM 2 news           – saisonale/frische Hooks (keine erfundenen News)
#     TEAM 3 evergreen      – langfristige Autoritätsthemen aus topics.yaml
#     TEAM 4 pain_points    – Schmerzpunkte aus data/research/pain_points.yaml
#     TEAM 5 viral_outliers – Top-Performer aus pinterest_plan/pinterest_perf
#     TEAM 6 niche_hooks    – Keyword-Lücken + ungenutzte Themen
#     TEAM 7 live_web       – OPTIONAL (hybrid): Web-Snippets, nur wenn
#                             SEARCH_API_KEY gesetzt ist. AUSSCHLIESSLICH als
#                             Winkel-Anregung, NIE als zitierfähiger Fakt.
#
#  KEINE HALLUZINATION (Dauervorgabe, siehe aktuelle_entwicklungen.yaml):
#  Harte Fakten (Gesetze, Paragraphen, Preise, Studien) kommen NUR aus
#  kuratierten Pools. Live-Web-Einträge sind explizit als "unverified"
#  markiert und werden im Routing nur als Inspirations-Winkel verwendet.
#
#  Ausgaben:
#    data/research/latest.yaml               – strukturierter Tages-Report
#    data/research/archive/<datum>.yaml      – Archiv (letzte 30 Tage)
#    AGC-FORSCHUNG-BERICHT.md                – lesbarer Tages-Report
#
#  Aufruf:
#    python3 scripts/research_engine.py --run [--dry-run] [--skip-live]
#    python3 scripts/research_engine.py --route "<Thema>" [--pillar X]
#    python3 scripts/research_engine.py --status
#    python3 scripts/research_engine.py --selftest
# ============================================================
import datetime
import hashlib
import json
import os
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH_DIR = os.path.join(BLOG_DIR, "data", "research")
ARCHIVE_DIR = os.path.join(RESEARCH_DIR, "archive")
LATEST_FILE = os.path.join(RESEARCH_DIR, "latest.yaml")
REPORT_FILE = os.path.join(BLOG_DIR, "AGC-FORSCHUNG-BERICHT.md")

AKTUELLE = os.path.join(BLOG_DIR, "data", "aktuelle_entwicklungen.yaml")
TOPICS = os.path.join(BLOG_DIR, "data", "topics.yaml")
PAIN = os.path.join(RESEARCH_DIR, "pain_points.yaml")
PINTEREST_PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")
PINTEREST_PERF = os.path.join(BLOG_DIR, "data", "pinterest_perf.yaml")
KEYWORD_SUGG = os.path.join(BLOG_DIR, ".keyword_suggestions.json")
UMAMI_CLICKS = os.path.join(BLOG_DIR, "data", "umami_clicks.json")

PILLARS = ["strom-sparen", "internet-dsl", "konto-karten",
           "versicherungen", "mietwagen", "frugalismus"]

PINTEREST_BOARDS = os.path.join(BLOG_DIR, "data", "pinterest_boards.yaml")

# kategorie (aktuelle_entwicklungen) → Pillar
KATEGORIE_PILLAR = {
    "energie": "strom-sparen",
    "versicherung": "versicherungen",
    "konto": "konto-karten",
    "internet": "internet-dsl",
    "saisonal": None,          # saisonal ist pillar-agnostisch
    "seo_qualitaet": None,     # rein intern, nie ins Content-Routing
}

# Saison-Boost: Monat → (kategorie, boost). 2026: Herbst = Energie-Hochphase.
SEASON_BOOST = {
    1: {"energie": 0.10, "versicherung": 0.15},   # Jahreswechsel
    2: {"energie": 0.05},
    3: {"energie": 0.05, "versicherung": 0.05},
    4: {"energie": 0.05},
    5: {"versicherung": 0.05},
    6: {"reisen": 0.10},                          # Urlaubssaison (nicht genutzt hier)
    7: {"reisen": 0.10},
    8: {"energie": 0.10},                         # Spätsommer = Wechselfenster
    9: {"energie": 0.15, "internet": 0.05},       # Heizperiode beginnt
    10: {"energie": 0.15, "versicherung": 0.05},  # Heizperiode
    11: {"energie": 0.15, "versicherung": 0.10},  # Nachzahlungen + Jahreswechsel
    12: {"energie": 0.15, "versicherung": 0.15, "konto": 0.05},
}

# Live-Web-Queries je Pillar (nur Winkel-Anregung, nie Fakten).
LIVE_QUERIES = {
    "strom-sparen": ["Strompreise Entwicklung 2026 Haushalt",
                     "Gaspreise Herbst 2026"],
    "internet-dsl": ["DSL Wechselbonus 2026 Anbieter"],
    "konto-karten": ["Tagesgeld Zinsen 2026 Entwicklung"],
    "versicherungen": ["Kfz-Versicherung Beitragserhöhung 2026"],
    "mietwagen": ["Mietwagen Preise Herbst 2026"],
}


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso():
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------- Quellen laden
def _load_yaml(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def load_aktuelle():
    data = _load_yaml(AKTUELLE)
    return data if isinstance(data, list) else []


def load_topics():
    data = _load_yaml(TOPICS)
    topics = data.get("topics", []) if isinstance(data, dict) else []
    return [t for t in topics if isinstance(t, dict)]


def load_pain_points():
    data = _load_yaml(PAIN)
    pps = data.get("pain_points", []) if isinstance(data, dict) else []
    return [p for p in pps if isinstance(p, dict)]


def load_pinterest_plan():
    data = _load_yaml(PINTEREST_PLAN)
    pins = data.get("pins", []) if isinstance(data, dict) else []
    return [p for p in pins if isinstance(p, dict)]


def load_pinterest_perf():
    data = _load_yaml(PINTEREST_PERF)
    entries = data.get("entries", []) if isinstance(data, dict) else []
    return [e for e in entries if isinstance(e, dict)]


def load_umami_clicks():
    data = _load_json(UMAMI_CLICKS)
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------- Signal-Hilfen
def _in_window(entry, today):
    today_str = today if isinstance(today, str) else today.isoformat()
    ab = entry.get("ab")
    bis = entry.get("bis")
    if ab and today_str < str(ab):
        return False
    if bis and today_str > str(bis):
        return False
    return True


def _season_score(kategorie, month):
    return SEASON_BOOST.get(month, {}).get(kategorie, 0.0)


def _tokens(text):
    if not text:
        return set()
    return set(re.findall(r"[a-zäöüß0-9]{3,}", str(text).lower()))


def _pillar_from_pinwand(pinwand):
    """Pillar aus Board-Name (Single Source of Truth: data/pinterest_boards.yaml)."""
    boards = _load_yaml(PINTEREST_BOARDS)
    boards = boards.get("boards", []) if isinstance(boards, dict) else []
    pw = re.sub(r"\s+", " ", (pinwand or "").strip().lower())
    for b in boards:
        name = re.sub(r"\s+", " ", (b.get("name") or "").strip().lower())
        if name and name == pw:
            pillars = b.get("pillars") or []
            return pillars[0] if pillars else None
    return None


# ---------------------------------------------------------------- TEAMS
def team_trending(today):
    """Aktuelle Entwicklungen (gültige Fenster), nach Saison + Frische gewichtet."""
    out = []
    month = today.month
    for e in load_aktuelle():
        if not _in_window(e, today):
            continue
        kat = e.get("kategorie", "")
        if kat == "seo_qualitaet":
            continue
        pillar = KATEGORIE_PILLAR.get(kat)
        hook = e.get("hook", "").strip()
        if not hook:
            continue
        score = 0.6 + _season_score(kat, month)
        out.append({"topic": hook, "pillar": pillar,
                    "signal": "trending", "source": f"aktuelle_entwicklungen:{e.get('id')}",
                    "score": round(min(score, 1.0), 2)})
    out.sort(key=lambda x: -x["score"])
    return out


def team_news(today):
    """Frische saisonale Hooks (Label: News-Hooks; KEINE erfundenen Meldungen)."""
    out = []
    month = today.month
    for e in load_aktuelle():
        if not _in_window(e, today):
            continue
        kat = e.get("kategorie", "")
        pillar = KATEGORIE_PILLAR.get(kat)
        hook = e.get("hook", "").strip()
        if not hook:
            continue
        boost = _season_score(kat, month)
        if boost >= 0.10:  # nur saisonal "heiße" Signale als News-Hooks
            out.append({"topic": hook, "pillar": pillar,
                        "signal": "news", "source": f"aktuelle_entwicklungen:{e.get('id')}",
                        "score": round(0.7 + boost, 2)})
    out.sort(key=lambda x: -x["score"])
    return out


def team_evergreen(today):
    """Langfristige Autoritätsthemen: je Pillar ein stabiles Set aus topics.yaml."""
    topics = load_topics()
    by_pillar = {}
    for t in topics:
        pillar = t.get("pillar")
        title = (t.get("title") or "").strip()
        if not pillar or not title:
            continue
        by_pillar.setdefault(pillar, []).append(t)

    # Deterministische Auswahl (Hash auf Pillar+Monat) → stabile Rotation,
    # aber reproduzierbar über den Tag hinweg.
    out = []
    for pillar, items in by_pillar.items():
        if not items:
            continue
        digest = hashlib.sha256(f"{pillar}:{today.strftime('%Y-%m')}".encode()).digest()
        idx = digest[0] % len(items)
        pick = items[idx]
        kw = pick.get("keywords") or []
        out.append({"topic": pick.get("title"), "pillar": pillar,
                    "signal": "evergreen", "source": f"topics:{pick.get('title')}",
                    "score": 0.85, "keywords": kw[:5]})
    out.sort(key=lambda x: -x["score"])
    return out


def team_pain_points(today):
    """Schmerzpunkte aus dem kuratierten Pool (keine Halluzination)."""
    out = []
    for p in load_pain_points():
        hook = p.get("hook", "").strip()
        if not hook:
            continue
        out.append({"topic": hook, "pillar": p.get("pillar"),
                    "signal": "pain_point", "source": f"pain_points:{p.get('id')}",
                    "score": round(float(p.get("score", 0.7)), 2)})
    out.sort(key=lambda x: -x["score"])
    return out


def team_viral_outliers(today):
    """Top-Performer: echte Performance-Daten (pinterest_perf) oder Link-Score
    aus dem Pinterest-Plan als Stellvertreter. Leere Daten → leere Liste."""
    out = []
    perf = load_pinterest_perf()
    if perf:
        for e in perf:
            clicks = int(e.get("clicks", 0) or 0)
            saves = int(e.get("saves", 0) or 0)
            if clicks + saves <= 0:
                continue
            score = min(0.5 + 0.05 * (clicks + saves / 2), 1.0)
            out.append({"topic": e.get("title", "").strip(),
                        "pillar": e.get("pillar"),
                        "signal": "viral_outlier", "source": "pinterest_perf",
                        "score": round(score, 2),
                        "stats": {"clicks": clicks, "saves": saves}})
        out.sort(key=lambda x: -x["score"])
        return out

    # Fallback: Link-Score aus pinterest_plan.yaml (reale in-Repo-Daten).
    pins = load_pinterest_plan()
    for p in pins:
        score = p.get("link_score")
        if score is None:
            continue
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        if score < 1.5:  # nur überdurchschnittliche Pins
            continue
        out.append({"topic": p.get("titel", "").strip(),
                    "pillar": _pillar_from_pinwand(p.get("pinwand")),
                    "signal": "viral_outlier", "source": "pinterest_plan",
                    "score": round(min(0.5 + score / 8, 1.0), 2)})
    out.sort(key=lambda x: -x["score"])
    return out[:8]


def team_niche_hooks(today):
    """Keyword-Lücken + noch nicht abgedeckte Themen (Long-Tail-Nischen)."""
    out = []
    sugg = _load_json(KEYWORD_SUGG)
    if isinstance(sugg, dict):
        # Keys sind oft "[<keyword>]" (Listen-Strings) – robust parsen.
        for key, vals in sugg.items():
            base = key.strip("[]\"' ")
            base = re.sub(r"^\[|\]$", "", base).strip("\"'")
            if not base:
                continue
            for v in (vals if isinstance(vals, list) else [])[:3]:
                topic = f"{base} – {v}"
                out.append({"topic": topic, "pillar": None,
                            "signal": "niche_hook", "source": "keyword_suggestions",
                            "score": 0.6, "keywords": [v]})
    # Nicht abgedeckte Themen als Nischen-Hook (nur eine kleine Auswahl).
    topics = load_topics()
    rng = random.Random(f"niche:{today.isoformat()}")
    sample = rng.sample(topics, min(6, len(topics)))
    for t in sample:
        out.append({"topic": t.get("title"), "pillar": t.get("pillar"),
                    "signal": "niche_hook", "source": f"topics:{t.get('title')}",
                    "score": 0.55, "keywords": (t.get("keywords") or [])[:5]})
    # Determinismus: zufällige Reihenfolge fixieren
    out.sort(key=lambda x: (-x["score"], x["topic"]))
    return out[:20]


# ---------------------------------------------------------------- LIVE WEB (hybrid)
def team_live_web(today, skip=False):
    """Live-Web-Snippets – NUR wenn SEARCH_API_KEY gesetzt und nicht --skip-live.

    Liefert (findings, enabled). Alle Findings sind `unverified: true` und
    dienen ausschließlich als Winkel-Anregung.
    """
    key = os.environ.get("SEARCH_API_KEY")
    provider = os.environ.get("SEARCH_API_PROVIDER", "serper").lower()
    if skip or not key:
        return [], False
    findings = []
    for pillar, queries in LIVE_QUERIES.items():
        for q in queries:
            try:
                results = _search(provider, key, q)
            except Exception:
                continue
            for r in results[:3]:
                title = (r.get("title") or "").strip()
                snippet = (r.get("snippet") or r.get("snippet_extra") or "").strip()
                if not title and not snippet:
                    continue
                findings.append({
                    "query": q, "pillar": pillar, "title": title[:140],
                    "snippet": snippet[:280], "url": r.get("link", ""),
                    "unverified": True, "source": f"live_web:{provider}",
                })
    return findings, True


def _search(provider, key, query):
    if provider in ("serper", "serper.dev"):
        url = "https://google.serper.dev/search"
        req = urllib.request.Request(
            url, data=json.dumps({"q": query, "gl": "de", "hl": "de", "num": 3}).encode(),
            headers={"X-API-KEY": key, "Content-Type": "application/json"})
    elif provider in ("brave", "brave.search"):
        url = "https://api.search.brave.com/res/v1/web/search?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={
            "X-Subscription-Token": key, "Accept": "application/json"})
    else:
        raise ValueError(f"Unbekannter SEARCH_API_PROVIDER: {provider}")
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if provider.startswith("serper"):
        return data.get("organic", []) or []
    return (data.get("web", {}).get("results", []) or []) if provider.startswith("brave") else []


# ---------------------------------------------------------------- ROUTING
def _route_score(entry, topic, pillar, keywords):
    score = 0.0
    if pillar and entry.get("pillar") == pillar:
        score += 0.4
    elif entry.get("pillar") is None:
        score += 0.1
    text = " ".join(str(x) for x in [entry.get("topic", ""),
                                     " ".join(entry.get("keywords", []))])
    topic_tok = _tokens(topic) | _tokens(" ".join(keywords or []))
    text_tok = _tokens(text)
    if topic_tok and text_tok:
        overlap = len(topic_tok & text_tok) / max(1, len(topic_tok))
        score += 0.5 * overlap
    score += 0.1 * float(entry.get("score", 0))
    return score


def route_topic(report, topic, pillar=None, keywords=None, limit=4):
    """Ordnet einem Thema die relevantesten Recherche-Signale zu (AGC:
    "System bestimmt, welche Reports relevant sind und füttert sie dem Agent")."""
    entries = []
    for team_key in ("trending", "news", "evergreen", "pain_points",
                     "viral_outliers", "niche_hooks"):
        for e in report.get("teams", {}).get(team_key, []):
            entries.append(e)
    # Live-Web-Findings separat (unverified) – nur als Winkel, niedriger gewichtet.
    for f in report.get("live_web", {}).get("findings", []):
        entries.append({"topic": f"{f['title']} — {f['snippet']}",
                        "pillar": f.get("pillar"), "signal": "live_web",
                        "source": f["source"], "score": 0.3,
                        "unverified": True, "url": f.get("url", "")})
    scored = [(e, _route_score(e, topic, pillar, keywords)) for e in entries]
    scored.sort(key=lambda x: -x[1])
    return [e for e, s in scored if s > 0.05][:limit]


def build_brief(report, topic, pillar=None, keywords=None):
    """Baut den kompakten Recherche-Brief für die Prompt-Injektion."""
    routed = route_topic(report, topic, pillar, keywords)
    if not routed:
        return ""
    lines = ["TAGES-RECHERCHE (relevante Signale – als ANREGUNG nutzen, "
             "keine Fakten erfinden):"]
    for e in routed:
        label = e.get("signal", "signal")
        text = str(e.get("topic", "")).strip()
        if not text:
            continue
        tag = ""
        if e.get("unverified"):
            tag = " ⚠ LIVE-WEB (unverifizierter Winkel, nicht als Fakt zitieren)"
        lines.append(f"- [{label}] {text}{tag}")
    return "\n".join(lines)


# ---------------------------------------------------------------- REPORT bauen
def build_report(today=None, skip_live=False):
    today = today or datetime.date.today()
    live, live_enabled = team_live_web(today, skip=skip_live)
    report = {
        "generated_at": now_iso(),
        "day": today.isoformat(),
        "mode": "hybrid" if live_enabled else "deterministic",
        "teams": {
            "trending": team_trending(today),
            "news": team_news(today),
            "evergreen": team_evergreen(today),
            "pain_points": team_pain_points(today),
            "viral_outliers": team_viral_outliers(today),
            "niche_hooks": team_niche_hooks(today),
        },
        "live_web": {"enabled": live_enabled, "findings": live},
    }
    return report


def write_report(report, dry_run=False):
    if dry_run:
        return
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(LATEST_FILE, "w", encoding="utf-8") as fh:
        yaml.safe_dump(report, fh, allow_unicode=True, sort_keys=False)
    with open(os.path.join(ARCHIVE_DIR, f"{report['day']}.yaml"), "w",
              encoding="utf-8") as fh:
        yaml.safe_dump(report, fh, allow_unicode=True, sort_keys=False)
    _prune_archive(keep=30)


def _prune_archive(keep=30):
    if not os.path.isdir(ARCHIVE_DIR):
        return
    files = sorted(os.listdir(ARCHIVE_DIR))
    for f in files[:-keep]:
        path = os.path.join(ARCHIVE_DIR, f)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def render_markdown(report):
    lines = [
        "# AGC-Forschungsbericht (Autopilot)",
        "",
        f"- Erstellt: {report['generated_at']}",
        f"- Modus: **{report['mode']}** "
        f"({'Live-Web aktiv' if report['live_web']['enabled'] else 'nur kuratierte Pools'})",
        "- Vertrauensprinzip: harte Fakten NUR aus kuratierten Pools; "
        "Live-Web-Einträge sind ausdrücklich **unverifizierte Winkel**, keine Quellen.",
        "",
    ]
    labels = {
        "trending": "📈 Trending (aktuelle Entwicklungen)",
        "news": "📰 News-Hooks (saisonal)",
        "evergreen": "🌲 Evergreen (Autoritätsthemen)",
        "pain_points": "😣 Pain Points (Schmerzpunkte)",
        "viral_outliers": "🔥 Viral Outliers (Top-Performer)",
        "niche_hooks": "🎯 Nischen-Hooks (Keyword-Lücken)",
    }
    for key, label in labels.items():
        entries = report["teams"].get(key, [])
        lines.append(f"## {label} ({len(entries)})")
        lines.append("")
        if not entries:
            lines.append("_keine Signale (Pool leer / keine Performance-Daten)_")
        for e in entries:
            pillar = e.get("pillar") or "–"
            lines.append(f"- **{e['topic']}** · Pillar `{pillar}` · Score {e['score']}")
        lines.append("")
    live = report["live_web"].get("findings", [])
    lines.append(f"## 🌐 Live-Web-Signale ({len(live)})")
    lines.append("")
    if live:
        lines.append("> ⚠️ Diese Einträge stammen aus einer Live-Suche und sind "
                     "NICHT verifiziert. Sie dienen nur als Inspirations-Winkel "
                     "– im Artikel niemals als Fakt/Studie zitieren.")
        lines.append("")
    for f in live:
        lines.append(f"- {f['title']} — {f['snippet']} ({f['url']})")
    if not live:
        lines.append("_deaktiviert (kein SEARCH_API_KEY gesetzt)_")
    lines.append("")
    return "\n".join(lines)


def write_markdown(report, dry_run=False):
    if dry_run:
        return
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))


# ---------------------------------------------------------------- CLI
def run_selftest():
    errs = []
    report = build_report(datetime.date.today(), skip_live=True)
    for key in ("trending", "news", "evergreen", "pain_points",
                "viral_outliers", "niche_hooks"):
        if key not in report["teams"]:
            errs.append(f"Team {key} fehlt im Report")
    if "mode" not in report:
        errs.append("mode fehlt")
    if not errs:
        # Routing-Smoke-Test
        brief = build_brief(report, "Stromanbieter wechseln",
                            pillar="strom-sparen",
                            keywords=["Stromvergleich", "Stromkosten senken"])
        if not brief:
            errs.append("Routing lieferte keinen Brief für Strom-Thema")
    return errs


def main():
    if "--selftest" in sys.argv:
        errs = run_selftest()
        if errs:
            print("🛑 RESEARCH-ENGINE-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"   - {e}")
            return 2
        print("✅ RESEARCH-ENGINE-SELFTEST bestanden (6 Teams + Routing).")
        return 0

    if "--route" in sys.argv:
        idx = sys.argv.index("--route")
        topic = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else ""
        pillar = None
        if "--pillar" in sys.argv:
            pidx = sys.argv.index("--pillar")
            if len(sys.argv) > pidx + 1:
                pillar = sys.argv[pidx + 1]
        report = _load_yaml(LATEST_FILE)
        if not report or "teams" not in report:
            print("⚠ Kein frischer Report vorhanden – erst `--run` ausführen.")
            return 1
        print(build_brief(report, topic, pillar=pillar))
        return 0

    if "--status" in sys.argv:
        report = _load_yaml(LATEST_FILE)
        if not report or "teams" not in report:
            print("Kein Recherche-Report vorhanden.")
            return 1
        total = sum(len(report["teams"].get(k, [])) for k in report["teams"])
        print(f"Letzter Report: {report.get('generated_at')} "
              f"(Tag {report.get('day')}) · Modus {report.get('mode')}")
        for key in report["teams"]:
            print(f"  {key:15s} {len(report['teams'].get(key, []))} Signale")
        print(f"  live_web        {len(report.get('live_web', {}).get('findings', []))} "
              f"({'aktiv' if report.get('live_web', {}).get('enabled') else 'aus'})")
        print(f"  GESAMT          {total} Signale")
        return 0

    # Default: --run
    dry = "--dry-run" in sys.argv
    skip_live = "--skip-live" in sys.argv
    report = build_report(datetime.date.today(), skip_live=skip_live)
    write_report(report, dry_run=dry)
    write_markdown(report, dry_run=dry)
    total = sum(len(report["teams"][k]) for k in report["teams"])
    print(f"🧠 Recherche {report['day']} · Modus {report['mode']} · "
          f"{total} Signale in 6 Teams "
          f"({'dry-run' if dry else 'gespeichert'})")
    for key in ("trending", "news", "evergreen", "pain_points",
                "viral_outliers", "niche_hooks"):
        print(f"   {key:15s} {len(report['teams'][key])}")
    live = report["live_web"]["findings"]
    print(f"   live_web        {len(live)} "
          f"({'unverifizierte Winkel' if live else 'aus/leer'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
