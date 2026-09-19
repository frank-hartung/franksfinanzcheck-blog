#!/usr/bin/env python3
"""
REVENUE-FUNNEL – die komplette Umsatzmessung: Besuch → Klick → Antrag → Provision

WARUM: Eine Profi-Agentur investiert keinen Euro in Reichweite, bevor der
Monetarisierungs-Trichter sichtbar ist. Die Einzelteile existieren (Umami-
Klickimport, Awin-Provisionen, Klick-Attribution), aber die EINHEIT – der
Trichter mit allen acht Kennzahlen je Woche – fehlte. Ohne ihn heißt es
„0 Klicks, 0.00 €“ – und das ist kein Messwert, sondern Unwissen. Dieses
Skript übersetzt Unwissen in eine dokumentierte Datenlücke und misst alles,
was messbar ist:

  1. Besuche je kaufnaher Seite   (Umami /pages ÷ Seiten mit /go/-CTA)
  2. Affiliate-Klicks             (Umami `affiliate_click` je Stelle/Artikel)
  3. Outbound-CTR                 (Klicks ÷ Besuche kaufnaher Seiten)
  4. Klick → Antrag               (Awin-Transaktionen jeglichen Status ÷ Klicks)
  5. Antrag → bestätigter Abschluss (approved ÷ alle Anträge)
  6. Stornoquote                  (declined ÷ abgeschlossene Anträge)
  7. Provision pro 100 Besuche    (Awin-Provision ÷ Besuche × 100)
  8. EPC                          (Provision ÷ Affiliate-Klicks)

EHRLICHE REGELN (Hausrecht der Messkette, siehe umami_clicks.py):
  - Fehlende Quelle ⇒ Kennzahl = „unbekannt“, NIE eine 0. Eine 0 ist eine
    Aussage über die Realität; „unbekannt“ ist eine Aussage über unsere Pipeline.
  - Jede Quelle trägt Alter + Status ins Report; der Governance-Gate macht aus
    „Messlücken: N“ einen gelben, handlungsbedürftigen Befund – das bleibt
    sichtbar, bis die Lücke zu ist. Kein Dauer-Alarm-Müll, aber auch kein
    Vergessen.
  - Keine Rohdaten im Report: nur Aggregat + Pfade (DSGVO wie die Importe).

AUSGABEN:
  - data/revenue_funnel.json           – maschinenlesbar (Scorecard, Engine, Dashboard)
  - data/revenue_funnel_history.jsonl  – Wochenreihen für Trend + WoW-Delta
  - REVENUE-FUNNEL-REPORT.md (root)    – Wochenseite mit Tabellen + Empfehlungen

Nutzung:
  python3 scripts/revenue_funnel.py            # berechnen + schreiben
  python3 scripts/revenue_funnel.py --print    # nur stdout (lokal, ohne Schreiblast)
  python3 scripts/revenue_funnel.py --selftest # Logik-Beweis, schreibt nichts ins Repo

Exit: 0 = kompletter Trichter gemessen, 1 = Messlücken dokumentiert (kein Crash,
      aber Handlungsbedarf), 2 = Selbsttest/Hausfehler.
"""
import datetime
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

DATA = os.path.join(BLOG_DIR, "data")
VIEWS = os.path.join(DATA, "umami_views.json")
VIEWS_META = os.path.join(DATA, "umami_views.meta.json")
CLICKS = os.path.join(DATA, "umami_clicks.json")
CLICKS_META = os.path.join(DATA, "umami_clicks.meta.json")
CTAS = os.path.join(DATA, "umami_ctas.json")
AWIN = os.path.join(DATA, "awin_provisions.json")
AWIN_META = os.path.join(DATA, "awin_fetch.meta.json")
OUT_JSON = os.path.join(DATA, "revenue_funnel.json")
HISTORY = os.path.join(DATA, "revenue_funnel_history.jsonl")
REPORT = os.path.join(BLOG_DIR, "REVENUE-FUNNEL-REPORT.md")

TODAY = datetime.date.today()
STALE_DAYS = 14         # Import älter als zwei Wochen ⇒ Quelle „veraltet“
MAX_HISTORY = 260       # gut 5 Jahre Wochenläufe

SOURCES = (
    # (Schlüssel, menschenlesbarer Name, Daten-/Meta-Pfade, Behebung)
    ("views", "Besuche (Umami /pages)", VIEWS, VIEWS_META,
     "Secret `UMAMI_API_TOKEN` setzen, dann läuft der Import automatisch "
     "(docs/UMSATZ-MESSUNG-PREMIUM.md) – oder `python3 scripts/umami_views.py --fetch`"),
    ("clicks", "Affiliate-Klicks (Umami event-data)", CLICKS, CLICKS_META,
     "Secret `UMAMI_API_TOKEN` setzen, dann läuft der Import automatisch "
     "(docs/UMSATZ-MESSUNG-PREMIUM.md) – oder `python3 scripts/umami_clicks.py --fetch`"),
    ("awin", "Awin-Transaktionen (Publisher API)", AWIN, AWIN_META,
     "Secrets `AWIN_API_TOKEN` + `AWIN_PUBLISHER_ID` setzen "
     "(Awin-UI → API Credentials) – oder CSV-Export nach `data/awin_transactions.csv`"),
)


# ------------------------------------------------------------------ IO-Helfer

def _read_json(path, default=None):
    try:
        with open(path if os.path.isabs(path) else os.path.join(BLOG_DIR, path),
                  encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _age_days(meta, keys=("written", "generated", "attempted")):
    """Alter einer Messung in Tagen (robust gegen Formatsuppe, None wenn unbekannt)."""
    for k in keys:
        v = (meta or {}).get(k)
        if isinstance(v, str):
            try:
                return (TODAY - datetime.date.fromisoformat(v[:10])).days
            except ValueError:
                continue
    return None


def _source_state(data, meta):
    """→ (status, age_days). status: ok | alt | skipped | fehlt."""
    if meta and meta.get("status") == "skipped":
        return "skipped", _age_days(meta)
    if not data:
        return "fehlt", None
    age = _age_days(meta or data)
    if age is not None and age > STALE_DAYS:
        return "alt", age
    return "ok", age


# ------------------------------------------------------------------ Kaufnahe Seiten

def kaufnahe_paths(root=None):
    """Seiten, die direkt Geld verdienen können: jeder Artikel mit /go/-Link,
    jeder Pillar-Ratgeber und die Ratgeber-Zentrale (/pillar/ – dort sitzt die
    Spar-Matrix mit sechs Gateway-Buttons).

    Die Startseite ist bewusst NICHT dabei: sie führt zu den kaufnahen Seiten,
    verkauft aber nichts direkt – ihre Wirkung misst der Trichter über die
    cta_click-Platzierungen, ihr Traffic steht in „Besuche gesamt“.
    Deterministisch aus dem Content-Scan (keine Laufzeit-Abhängigkeit von
    Umami-Namenskonventionen); die Layout-Plätze sind fix, weil ihre
    CTA-Verträge (pillar/list.html, render-link.html) bei jedem Build
    getestet werden (click_chain_guard.py + E2E)."""
    root = root or BLOG_DIR
    out = {"/pillar/"}
    for p in sorted(glob.glob(os.path.join(root, "content", "posts", "*", "index.md"))) + \
             sorted(glob.glob(os.path.join(root, "content", "posts", "*.md"))):
        try:
            body = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"/go/[A-Za-z0-9_\-]+/?", body) or re.search(
                r"(tarifvergleich|einspartabelle)", body):
            slug = os.path.basename(os.path.dirname(p)) if os.path.basename(p) == "index.md" \
                else os.path.basename(p)[:-3]
            if slug and not slug.startswith("_"):
                out.add(f"/posts/{slug}/")
    for p in sorted(glob.glob(os.path.join(root, "content", "pillar", "*", "index.md"))):
        out.add(f"/pillar/{os.path.basename(os.path.dirname(p))}/")
    return out


def article_to_path(article):
    """Umami-`article`-Attribut („posts/<slug>/index.md“, „pillar/<k>/index.md“
    oder Layout-Platzierungen) → Blog-Pfad. Leeres Ergebnis = Sonstiges."""
    a = str(article or "").strip().strip("/")
    if not a:
        return ""
    if a in ("posts", "pillar", "content", "_index"):
        # nackte Sektionsnamen sind keine Slugs (würde /pillar/posts/ erfinden)
        return "/pillar/" if a == "pillar" else ""
    if a in ("home", "pillar/_index"):
        return "/pillar/" if a == "pillar/_index" else "/"
    if a.startswith("posts/"):
        slug = a[len("posts/"):].removesuffix("/index.md").removesuffix(".md")
        slug = re.sub(r"/?_index$", "", slug)  # posts/x/_index.md → x
        return f"/posts/{slug}/" if slug and slug != "_index" else ""
    if a.startswith("pillar/"):
        seg = a[len("pillar/"):].removesuffix("/index.md").removesuffix(".md")
        return f"/pillar/{seg}/" if seg and seg != "_index" else "/pillar/"
    m = re.match(r"^([A-Za-z0-9_\-]+)$", a)  # roher SubID-Slug (Pillar-Name)
    return f"/pillar/{m.group(1)}/" if m else ""


# ------------------------------------------------------------------ Trichter

def _rate(num, den):
    """Prozentsatz oder None (unbekannt)."""
    if num is None or den is None or den <= 0:
        return None
    return round(100.0 * num / den, 2)


def _per100(revenue, visits):
    if revenue is None or not visits:
        return None
    return round(100.0 * revenue / visits, 2)


def _per_unit(revenue, clicks):
    if revenue is None or not clicks:
        return None
    return round(revenue / clicks, 2)


def fmt(v, kind="int"):
    if v is None:
        return "unbekannt"
    if kind == "int":
        return f"{int(v):,}".replace(",", ".")
    if kind == "pct":
        return f"{v:.2f} %".replace(".", ",")
    if kind == "eur":
        return f"{v:.2f} €".replace(".", ",")
    return f"{v:.4f}".replace(".", ",")


def compute(views_doc, clicks_rows, awin_doc, cta_rows, paths, measured=None):
    """Reine Trichter-Rechnung (testbar, ohne Dateizugriff).

    `measured` = {views, clicks, awin: bool}: „die Quelle wurde erfolgreich
    importiert“. Nur dann darf eine 0 als echte Null stehen – sonst gilt
    überall die Hausregel: nicht gemessen ⇒ unbekannt, nie eine Null."""
    views = (views_doc or {}).get("pages") if isinstance(views_doc, dict) else None
    views = views if isinstance(views, list) else []
    totals = (views_doc or {}).get("totals") if isinstance(views_doc, dict) else None
    totals = totals if isinstance(totals, dict) else {}
    clicks_rows = [r for r in (clicks_rows or []) if isinstance(r, dict)]
    awin_doc = awin_doc if isinstance(awin_doc, dict) else {}
    m = measured or {"views": bool(views_doc), "clicks": bool(clicks_rows),
                     "awin": bool(awin_doc)}

    # Besuche: ganze Seite + kaufnahe Teileschiene
    views_total = totals.get("visits") or 0
    pageviews_total = totals.get("pageviews") or 0
    per_path = {}
    for row in views:
        if isinstance(row, dict):
            per_path[row.get("path")] = {"views": int(row.get("views") or 0),
                                         "visits": int(row.get("visits") or 0)}
    views_kaufnah = sum(d["visits"] for p, d in per_path.items() if p in paths) \
        if m.get("views") else None
    if m.get("views") and views_kaufnah is None:
        views_kaufnah = 0 if views else None

    # Klicks je Pfad + gesamt (nur Affiliate-Events – cta_click bleibt draußen)
    aff = [r for r in clicks_rows if "affiliate_click" in str(r.get("event") or "affiliate_click")]
    clicks_total = sum(int(r.get("count") or 0) for r in aff) if m.get("clicks") else None
    clicks_by_path = {}
    for r in aff:
        p = article_to_path(r.get("article"))
        if p:
            clicks_by_path[p] = clicks_by_path.get(p, 0) + int(r.get("count") or 0)

    # Platzierungen (cta_click-Import von Start-/Pillar-CTAs)
    placements = {}
    for r in [x for x in (cta_rows or []) + clicks_rows if isinstance(x, dict)]:
        if str(r.get("event") or "") == "cta_click":
            label = str(r.get("slug") or "unbenannt")[:60]
            placements[label] = placements.get(label, 0) + int(r.get("count") or 0)

    # Awin-Trichter: Antrag → Abschluss → Storno
    st = awin_doc.get("status_totals") or {}
    has_awin = bool(m.get("awin"))
    antraege = sum(int(d.get("count") or 0) for d in st.values()) if st else (0 if has_awin else None)
    confirmed = int((st.get("approved") or {}).get("count") or 0)
    declined = int((st.get("declined") or {}).get("count") or 0)
    pending = int((st.get("pending") or {}).get("count") or 0)
    revenue = awin_doc.get("total_commission") if has_awin else None
    if revenue is not None:
        revenue = round(float(revenue), 2)
    provision_bezahlt = round(float(awin_doc.get("total_paid") or 0), 2) if has_awin else None

    # Provision je Seite (für die Trichter-Tabelle; SubID-Auflösung wie in awin_provisions:
    # Awin führt den Artikel als rohen Slug, Umami als content-Pfad – hier wird
    # beides auf denselben Blog-Pfad /posts/<slug>/ bzw. /pillar/<key>/ gebracht)
    per_article_rev = {}
    for key, v in (awin_doc.get("articles") or {}).items():
        art = str(v.get("article") or key)
        if re.match(r"^20\d{2}-", art):
            path = f"/posts/{art}/"
        else:
            path = article_to_path(art) or "sonstiges"
        d = per_article_rev.setdefault(path, {"revenue": 0.0, "orders": 0})
        d["revenue"] += float(v.get("commission") or 0)
        d["orders"] += int(v.get("orders") or 0)

    # Kennzahlen – None heißt „unbekannt“, das ist der ganze Witz.
    rates = {
        "outbound_ctr": _rate(clicks_total, views_kaufnah),
        "klick_antrag": _rate(antraege, clicks_total),
        "antrag_abschluss": _rate(confirmed, antraege),
        "stornoquote": _rate(declined, (confirmed or 0) + (declined or 0) if st else None),
        "rev_per_100_visits": _per100(revenue, views_total if m.get("views") else None),
        "rev_per_100_kaufnah": _per100(revenue, views_kaufnah),
        "epc": _per_unit(revenue, clicks_total),
    }

    # Top-Seiten des Trichters (kaufnahe Seiten mit Messwerten)
    per_page = []
    for p in sorted(paths):
        v = per_path.get(p, {}).get("visits")
        pv = per_path.get(p, {}).get("views")
        c = clicks_by_path.get(p)
        rev = per_article_rev.get(p, {}).get("revenue")
        if v is None and c is None and rev is None:
            continue
        per_page.append({"path": p, "views": pv, "visits": v, "clicks": c,
                         "ctr": _rate(c, pv),
                         "revenue": round(rev, 2) if rev is not None else None,
                         "epc": _per_unit(rev, c)})
    per_page.sort(key=lambda d: -(d.get("clicks") or 0))

    return {
        "generated": TODAY.isoformat(),
        "window_days": 90,
        "kaufnah_seiten": len(paths),
        "views": {"total": views_total if m.get("views") else None,
                  "pageviews": pageviews_total if m.get("views") else None,
                  "kaufnah": views_kaufnah},
        "affiliate_klicks": clicks_total,
        "transaktionen": {"antraege": antraege, "pending": pending, "bestaetigt": confirmed,
                          "stornos": declined, "quelle": "awin" if has_awin else None},
        "provision": {"gesamt": revenue, "bezahlt": provision_bezahlt},
        "raten": rates,
        "platzierungen": dict(sorted(placements.items(), key=lambda kv: -kv[1])),
        "seiten": per_page,
    }


def evaluate(sources):
    """→ (gaps, notations): welche Quellen sind Löcher, was kostet die Behebung?"""
    gaps = []
    for key, label, data_state, age in sources:
        if data_state == "ok":
            continue
        why = {"fehlt": "noch nie importiert", "skipped": "Import übersprungen (Secret fehlt)",
               "alt": f"Import {age or '?'}d alt (Frist {STALE_DAYS}d)"}[data_state]
        gaps.append(f"{label}: {why}")
    return gaps


# ------------------------------------------------------------------ Report

def render(f, gaps, fix_hints, wow=None):
    """Markdown-Wochenseite. Enthält die Markerzeile `Messlücken: N` und die
    Gesamt-Ampel – der Governance-Gate liest beides (kein Exit-Code-Raten)."""
    rate = f["raten"]
    tx = f["transaktionen"]
    rows = [
        ("Besuche gesamt", fmt(f["views"]["total"])),
        ("Besuche kaufnaher Seiten", fmt(f["views"]["kaufnah"])),
        ("Affiliate-Klicks", fmt(f["affiliate_klicks"])),
        ("Outbound-CTR (Klicks ÷ Besuche kaufnah)", fmt(rate["outbound_ctr"], "pct")),
        ("Anträge (Awin, alle Status)", fmt(tx["antraege"])),
        ("Klick → Antrag", fmt(rate["klick_antrag"], "pct")),
        ("Antrag → bestätigter Abschluss", fmt(rate["antrag_abschluss"], "pct")),
        ("Stornoquote (declined ÷ abgeschlossene)", fmt(rate["stornoquote"], "pct")),
        ("Provision (gesamt)", fmt(f["provision"]["gesamt"], "eur")),
        ("Provision bezahlt (Awin-Kasse)", fmt(f["provision"]["bezahlt"], "eur")),
        ("Provision pro 100 Besuche (gesamte Site)",
         fmt(rate["rev_per_100_visits"], "eur")),
        ("Provision pro 100 Besuche (kaufnahe Seiten)",
         fmt(rate["rev_per_100_kaufnah"], "eur")),
        ("EPC (Einnahmen pro Affiliate-Klick)", fmt(rate["epc"], "eur")),
    ]
    ampel = "GREEN" if not gaps else "AMBER"
    out = ["# 📈 Umsatz-Funnel – Besuch → Klick → Antrag → Provision",
           f"**Stand:** {f['generated']} · **Fenster:** {f['window_days']} Tage · "
           f"**Ampel:** **{ampel}** · **Messlücken: {len(gaps)}**",
           "",
           "## 🚦 Gesamt-Ampel: **" + ampel + "**",
           "",
           "| Kennzahl | Wert |",
           "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    if wow:
        out += ["", "## 🔁 Vorwoche (Woche für Woche)", "",
                "| Kennzahl | letzte Woche | Δ |", "|---|---|---|"]
        out += [f"| {k} | {prev} | {d} |" for k, prev, d in wow]
    if f["seiten"]:
        out += ["", "## 🧭 Trichter je kaufnahe Seite (Top 15)", "",
                "| Seite | Besuche | Klicks | Outbound-CTR | Provision | EPC |",
                "|---|---|---|---|---|---|"]
        for p in f["seiten"][:15]:
            out.append(f"| `{p['path']}` | {fmt(p['visits'])} | {fmt(p['clicks'])} | "
                       f"{fmt(p['ctr'], 'pct')} | {fmt(p['revenue'], 'eur')} | "
                       f"{fmt(p['epc'], 'eur')} |")
    if f["platzierungen"]:
        out += ["", "## 🎯 CTA-Platzierungen (cta_click: Start-/Pillar-CTAs)", "",
                "| Platzierung | Klicks |", "|---|---|"]
        out += [f"| `{k}` | {v} |" for k, v in list(f["platzierungen"].items())[:15]]
    out += ["", "## 🧾 Datenqualität der Messkette", ""]
    if gaps:
        out += ["| Level | Code | Befund |", "|---|---|---|"]
        out += [f"| AMBER | funnel_gap | {g} |" for g in gaps]
        out += ["", "Behebung (Reihenfolge = Wirkung):"]
        out += [f"- {h}" for h in fix_hints]
    else:
        out += ["_keine Befunde_ – alle Quellen gemessen und frisch (≤ 14 Tage)."]
    out += ["", "## 🎯 Empfehlung (Agentur-Modus)", "",
            "1. **Reichweite nur auf bewiesenen Trichter:** EPC < 0,10 € auf einer",
            "   kaufnahen Seite ⇒ CTA/Anker überarbeiten, BEVOR Traffic gekauft wird.",
            "2. **Storno > 15 %** ⇒ Partner-Ziel prüfen (falsches Produkt versprochen?",
            "   Intent-Gate IW3) – Stornos sind verlorene Margen, keine Petitesse.",
            "3. **Outbound-CTR < 1 % bei hohem Traffic** ⇒ Seite ist Leser-, keine",
            "   Wechsel-Seite: CTA nach oben, Vergleichs-Shortcode setzen, Fazit-Anker.",
            "4. **Antrag → Abschluss < 40 %** ⇒ Erwartungsmanagement am Link prüfen",
            "   (Tooltip/Anker müssen halten, was sie versprechen – siehe Intent-Wache).",
            "",
            "_Erzeugt von `scripts/revenue_funnel.py`; Quelle der Zahlen: Umami-API +",
            "Awin-Publisher-API. „unbekannt“ heißt: Messkette noch nicht befüllt –",
            "siehe Datenqualität oben, nicht „nichts verdient“._",
            ""]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ History + WoW

def _history_row(f):
    r = f["raten"]
    return {"date": f["generated"],
            "views_total": f["views"]["total"], "views_kaufnah": f["views"]["kaufnah"],
            "clicks": f["affiliate_klicks"], "ctr_pct": r["outbound_ctr"],
            "antraege": f["transaktionen"]["antraege"],
            "confirmed": f["transaktionen"]["bestaetigt"],
            "storno_pct": r["stornoquote"], "revenue": f["provision"]["gesamt"],
            "epc": r["epc"], "rev_per_100": r["rev_per_100_visits"]}


def _prev_metrics():
    """Letzte abgeschlossene Woche aus der History (für Δ), None wenn keine."""
    try:
        lines = [l for l in open(HISTORY, encoding="utf-8").read().splitlines() if l.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("date") != TODAY.isoformat():
            return d
    return None


def _wow(cur, prev):
    """Zeilen (Kennzahl, Vorwoche, Δ) – Δ bleibt None, wenn eine Seite fehlt."""
    if not prev:
        return []
    out = []
    for label, key, kind in (("Besuche gesamt", "views_total", "int"),
                             ("Besuche kaufnah", "views_kaufnah", "int"),
                             ("Affiliate-Klicks", "clicks", "int"),
                             ("Outbound-CTR (%)", "ctr_pct", "pct"),
                             ("Anträge", "antraege", "int"),
                             ("Stornoquote (%)", "storno_pct", "pct"),
                             ("Provision (€)", "revenue", "eur"),
                             ("EPC (€)", "epc", "eur"),
                             ("Provision/100 Besuche (€)", "rev_per_100", "eur")):
        a, b = cur.get(key), prev.get(key)
        diff = round(a - b, 2) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None
        delta = "unbekannt" if diff is None else ("+" if diff >= 0 else "") + fmt(diff, kind)
        out.append((label, fmt(b, kind), delta))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    print_only = "--print" in argv
    paths = kaufnahe_paths()
    views_doc = _read_json(VIEWS, {}) or {}
    views_meta = _read_json(VIEWS_META, {}) or {}
    clicks_rows = _read_json(CLICKS, []) or []
    clicks_meta = _read_json(CLICKS_META, {}) or {}
    cta_rows = _read_json(CTAS, []) or []
    awin_doc = _read_json(AWIN, {}) or {}
    awin_meta = _read_json(AWIN_META, {}) or {}

    # „gemessen“ = Import sagt ok ODER Bestand mit Datum (manueller Export zählt auch).
    measured = {
        "views": bool(views_doc) and (views_meta.get("status") or "ok") != "skipped",
        "clicks": (clicks_meta.get("status") or ("ok" if clicks_rows else "fehlt")) == "ok",
        "awin": bool(awin_doc),
    }
    src = [("views", SOURCES[0][1], *_source_state(views_doc, views_meta)),
           ("clicks", SOURCES[1][1], *_source_state(clicks_rows, clicks_meta)),
           ("awin", SOURCES[2][1], *_source_state(awin_doc, awin_meta))]
    # Ein leeres, aber frisch als ok geschriebenes Import-File ist eine MES-SUNG
    # (echte 0), kein Loch – evaluate darf das nicht doppelt zählen.
    def _state_of(state, age, key):
        if state == "fehlt" and measured[key]:
            return "ok", age
        return state, age
    src = [(k, label, *_state_of(state, age, k)) for k, label, state, age in src]
    gaps = evaluate(src)
    fixes = [SOURCES[i][4] for i, (_k, _l, state, _a) in enumerate(src) if state != "ok"]
    f = compute(views_doc, clicks_rows, awin_doc, cta_rows, paths, measured=measured)
    # Fenster ehrlich machen: die Importe schreiben ihr Zeitfenster in die Meta.
    for meta in (clicks_meta, views_meta):
        if isinstance(meta, dict) and isinstance(meta.get("days"), int):
            f["window_days"] = meta["days"]
            break
    f["quellen"] = [{"quelle": k, "status": state, "alter_tage": age}
                   for k, _l, state, age in src]

    prev = _prev_metrics()
    wow = _wow(_history_row(f), prev)
    body = render(f, gaps, fixes, wow)

    if print_only:
        print(body)
    else:
        _write_atomic(REPORT, body)
        _write_atomic(OUT_JSON, json.dumps({**f, "messluecken": len(gaps),
                                            "quellen": f["quellen"]},
                                           ensure_ascii=False, indent=2) + "\n")
        try:
            os.makedirs(DATA, exist_ok=True)
            row = json.dumps(_history_row(f), ensure_ascii=False)
            lines = []
            if os.path.exists(HISTORY):
                lines = [l for l in open(HISTORY, encoding="utf-8").read().splitlines()
                         if l.strip()]
            # Idempotenz pro Tag: Mehrfachläufe am selben Tag überschreiben die
            # letzte Zeile – sonst zählt die Woche doppelt und Δ wird Unsinn.
            if lines:
                try:
                    same_day = json.loads(lines[-1]).get("date") == TODAY.isoformat()
                except json.JSONDecodeError:
                    same_day = False
                lines = lines[:-1] if same_day else lines
            lines.append(row)
            _write_atomic(HISTORY, "\n".join(lines[-MAX_HISTORY:]) + "\n")
        except (OSError, json.JSONDecodeError):
            pass
        print(f"📈 Umsatz-Funnel: {fmt(f['affiliate_klicks'])} Klicks · "
              f"{fmt(f['provision']['gesamt'], 'eur')} Provision · "
              f"EPC {fmt(f['raten']['epc'], 'eur')} · Messlücken: {len(gaps)}")
    try:
        from audit_log import log_event
        log_event(module="revenue_funnel", action="report",
                  input={"views": v_state[0], "clicks": c_state[0], "awin": a_state[0]},
                  output={"gaps": len(gaps), "clicks": f["affiliate_klicks"],
                          "revenue": f["provision"]["gesamt"]}, status="ok")
    except Exception:  # noqa: BLE001
        pass
    print(f"\nMesslücken: {len(gaps)}")
    return 1 if gaps else 0


def _write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


# ------------------------------------------------------------------ Selftest

def _selftest():
    failures = []
    # --- Artikel-Attribut → Pfad (die Brücke Klick↔Besuch muss sitzen)
    for art, want in (("posts/2026-08-16-gas-anbieter-wechseln/index.md",
                       "/posts/2026-08-16-gas-anbieter-wechseln/"),
                      ("pillar/strom-sparen/index.md", "/pillar/strom-sparen/"),
                      ("strom-sparen", "/pillar/strom-sparen/"),
                      ("home", "/"), ("pillar/_index", "/pillar/"),
                      ("", ""), ("posts/", ""), ("unsinn/tief/hier", "")):
        got = article_to_path(art)
        if got != want:
            failures.append(f"article_to_path({art!r}) = {got!r}, erwartet {want!r}")
    # --- Kaufnahe-Menge: Zentrale + Ratgeber drin, Startseite draußen
    k = kaufnahe_paths()
    if "/pillar/" not in k:
        failures.append("Ratgeber-Zentrale fehlt in der kaufnahen Menge")
    if "/" in k:
        failures.append("Startseite gehört nicht in den CTR-Nenner (kein direkter Verkauf) – "
                        "ihre CTA-Wirkung läuft über cta_click-Platzierungen")
    if not any(p.startswith("/pillar/") and p != "/pillar/" for p in k):
        failures.append("Pillar-Ratgeber fehlen in der kaufnahen Menge")
    # --- Trichter-Synthese: alle acht Kennzahlen mit Absichtswerten
    views = {"totals": {"visits": 1000, "pageviews": 1500},
             "pages": [{"path": "/posts/2026-08-16-gas-anbieter-wechseln/",
                        "views": 200, "visits": 150},
                       {"path": "/pillar/strom-sparen/", "views": 100, "visits": 80},
                       {"path": "/", "views": 500, "visits": 400}]}
    clicks = [{"event": "affiliate_click", "slug": "gas",
               "article": "posts/2026-08-16-gas-anbieter-wechseln/index.md",
               "pillar": "", "count": 40},
              {"event": "cta_click", "slug": "home-strom", "article": "home", "count": 25}]
    awin = {"generated": TODAY.isoformat(), "total_commission": 210.0, "total_paid": 150.0,
            "status_totals": {"pending": {"count": 6, "commission": 60.0},
                              "approved": {"count": 9, "commission": 150.0},
                              "declined": {"count": 3, "commission": 0.0}},
            "articles": {"2026-08-16-gas-anbieter-wechseln":
                         {"commission": 120.0, "orders": 8,
                          "subid": "2026-08-16-gas-anbieter-wechseln"}}}
    f = compute(views, clicks, awin, [], {"/pillar/", "/posts/2026-08-16-gas-anbieter-wechseln/",
                                          "/pillar/strom-sparen/"})
    r = f["raten"]
    if f["affiliate_klicks"] != 40:
        failures.append(f"cta_click verunreinigt Affiliate-Zähler: {f['affiliate_klicks']}")
    if f["views"]["kaufnah"] != 150 + 80:
        failures.append(f"Besuche kaufnah: {f['views']['kaufnah']}")
    if abs(r["outbound_ctr"] - 100 * 40 / 230) > 0.01:
        failures.append(f"Outbound-CTR: {r['outbound_ctr']}")
    if f["transaktionen"]["antraege"] != 18:
        failures.append(f"Anträge gesamt: {f['transaktionen']['antraege']}")
    if abs(r["antrag_abschluss"] - 50.0) > 0.01:
        failures.append(f"Antrag→Abschluss: {r['antrag_abschluss']}")
    if abs(r["stornoquote"] - 25.0) > 0.01:
        failures.append(f"Stornoquote: {r['stornoquote']}")
    if abs(r["epc"] - 5.25) > 0.01:
        failures.append(f"EPC: {r['epc']}")
    if abs(r["rev_per_100_visits"] - 21.0) > 0.01:
        failures.append(f"Provision/100 gesamt: {r['rev_per_100_visits']}")
    if f["platzierungen"].get("home-strom") != 25:
        failures.append(f"Platzierungen: {f['platzierungen']}")
    top = f["seiten"][0]
    if (top["path"] != "/posts/2026-08-16-gas-anbieter-wechseln/" or top["clicks"] != 40
            or top["revenue"] != 120.0 or top["epc"] != 3.0):
        failures.append(f"Seiten-Trichter Top: {top}")
    if top["ctr"] != 20.0:
        failures.append(f"Seiten-CTR (Klicks ÷ Seitenaufrufe): {top['ctr']}")
    # --- „unbekannt“ ≠ 0: leere Quellen dürfen nirgends Nullen gebären
    empty = compute({}, [], {}, [], {"/", "/pillar/"})
    for name, v in list(empty["raten"].items()) + [("klicks", empty["affiliate_klicks"]),
                                                   ("prov", empty["provision"]["gesamt"]),
                                                   ("antraege", empty["transaktionen"]["antraege"])]:
        if v is not None:
            failures.append(f"ohne Quellen erfindet der Trichter {name}={v} (soll unbekannt)")
    if "unbekannt" not in render(empty, ["Besuche: fehlt", "Klicks: fehlt", "Awin: fehlt"],
                                 ["Secrets setzen"], []):
        failures.append("Report versteckt das Wort „unbekannt“")
    # --- Ampel + Marker + Befundtabelle für den Governance-Gate
    rep = render(empty, ["a", "b", "c"], ["d"], [])
    if "Messlücken: 3" not in rep or "**AMBER**" not in rep:
        failures.append("Report-Linie `Messlücken: N` / Ampel fehlt (Gate wäre blind)")
    if "funnel_gap" not in rep:
        failures.append("Lücken stehen nicht als AMBER/funnel_gap-Befunde da – "
                        "der Gate-Filter (ACTIONABLE_AMBER) läuft ins Leere")
    rep_ok = render(f, [], [], [])
    if "Messlücken: 0" not in rep_ok or "GREEN" not in rep_ok:
        failures.append("grüner Trichter meldet nicht grün")
    # --- Datenqualitäts-Logik
    if evaluate([("views", "V", "ok", 0), ("clicks", "K", "ok", 2)]) != []:
        failures.append("frische Quellen werden als Lücke gemeldet")
    g = evaluate([("views", "V", "alt", 30), ("clicks", "K", "skipped", 1),
                  ("awin", "A", "fehlt", None)])
    if len(g) != 3 or "30d" not in " ".join(g):
        failures.append(f"Lückentext unvollständig: {g}")
    # --- Alter aus Meta
    if _age_days({"written": TODAY.isoformat()}) != 0:
        failures.append("_age_days heute ≠ 0")
    if _source_state([], {"status": "skipped", "attempted": "2026-01-01"})[0] != "skipped":
        failures.append("skipped-Meta muss als skipped durchkommen (nie als „fehlt“)")
    if _source_state({"pages": []}, {"generated": "2026-01-01"})[0] != "alt":
        failures.append("uralt-Bestand muss „alt“ heißen")
    # --- Zahlenformat
    if fmt(None) != "unbekannt" or fmt(1234) != "1.234" or fmt(12.5, "eur") != "12,50 €":
        failures.append("fmt-Formatierung (1.234 / 12,50 € / unbekannt)")
    # --- Müll crashet nie
    for bad in (None, {}, [], {"pages": "apfelsaft", "totals": 7}):
        try:
            compute(bad, bad if isinstance(bad, list) else [], bad, [], set())
        except Exception as exc:  # noqa: BLE001
            failures.append(f"Müll {bad!r} wirft {exc.__class__.__name__}")
    if failures:
        print("❌ REVENUE-FUNNEL-SELFTEST FEHLGESCHLAGEN:")
        for x in failures:
            print("   -", x)
        return 2
    print("✅ REVENUE-FUNNEL-SELFTEST bestanden (Trichter-Rechnung, unbekannt≠0, "
          "Ampel+Marker für den Gate, Platzierungen, Robustheit).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
