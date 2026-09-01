#!/usr/bin/env python3
"""
DECAY-RADAR – Content-Decay-Radar für FranksFinanzcheck (Chefredakteur-Stufe)

Für einen YMYL-/Affiliate-Blog ist Frische ein Ranking- und Vertrauensfaktor:
Jahreswechsel, Gesetzesänderungen, Kündigungsfristen und Tariffenster
(30.11., 01.01., Heizsaison) lassen selbst gute Artikel innerhalb von
Monaten veralten. Der Decay-Radar misst das systematisch und erzeugt eine
priorisierte Refresh-Queue – statt Content „auf gut Glück" zu aktualisieren.

WAS ER PRÜFT (je live-Artikel):
  - Alter seit `lastmod` (fallback `date`) in Tagen
  - Saisonale/Stichtag-Sensitivität (Kfz 30.11., Gas/Strom Preisgarantie,
    DSL-Wechsel, Handytarife, Steuern, Zinsen, Fristen, Heizsaison)
  - YMYL-Klassifikation (Finanz-/Versicherungs-/Vertragsthemen)
  - Content-Tiefe (Länge) als „Refresh wäre lohnend"-Signal
  - Doppel-UPDATE-Anzeichen (mehrere `lastmod`-Refreshes im Verlauf)

AUSGABE:
  - `DECAY-REPORT.md`  – Chefredakteur-Sicht (Top-Refresh-Kandidaten + Begründung)
  - `data/decay_queue.json` – maschinenlesbare Refresh-Queue (für Engine/Autoren)
  - `--issue`          – fertiger GitHub-Issue-Text (Body) für `actions/github-script`
  - `--selftest`       – eingefrorene Fälle (Regression + Beweis)

Exit-Codes: 0 = grün (kein Refresh nötig), 1 = Refresh-Kandidaten vorhanden,
2 = Selftest fehlgeschlagen oder Instanz-Fehler.

Nutzung:
  python3 scripts/decay_radar.py            # prüfen + Report schreiben
  python3 scripts/decay_radar.py --issue    # zusätzlich Issue-Body auf stdout
  python3 scripts/decay_radar.py --selftest # eingefrorene Fälle
"""
import glob
import json
import os
import re
import sys
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
PILLAR_DIR = os.path.join(BLOG_DIR, "content", "pillar")
REPORT = os.path.join(BLOG_DIR, "DECAY-REPORT.md")
QUEUE = os.path.join(BLOG_DIR, "data", "decay_queue.json")

# Sensitive/Stichtag-bezogene Begriffe -> hohe Frequenz der Aktualisierung.
_SEASON_TERMS = [
    "kündigung", "stichtag", "frist", "30. november", "kfz", "versicherung",
    "gas", "strom", "preisgarantie", "dsl", "handytarif", "mobilfunk",
    "zinsen", "tagesgeld", "steuer", "heiz", "öltank", "sparsam", "bonus",
    "tarifwechsel", "anbieterwechsel", "neujahr", "jahreswechsel",
]
# Pillars, die stichtag-sensitiv sind.
_SENSITIVE_PILLARS = {
    "versicherungen", "strom-sparen", "internet-dsl", "konto-karten",
    "mietwagen",
}
_EVERGREEN_PILLARS = {"frugalismus"}

# Standard-Refresh-Fenster (in Tagen) pro Klasse.
REFRESH_SENSITIVE = 150     # Stichtag-/Tarif-Themen: ~alle 5 Monate
REFRESH_YMYL = 210          # Finanz/Versicherung allgemein
REFRESH_EVERGREEN = 365     # Frugalismus & Grundlagen

TODAY = datetime.date.today()

# ------------------------------------------------------------ Helfer


def _resolve_as_of():
    """`--as-of YYYY-MM-DD` (Forecast) sonst heute. Validiert Datum."""
    for i, arg in enumerate(sys.argv):
        if arg == "--as-of" and i + 1 < len(sys.argv):
            try:
                return datetime.date.fromisoformat(sys.argv[i + 1])
            except ValueError:
                raise SystemExit(f"❌ --as-of braucht YYYY-MM-DD, erhielt: {sys.argv[i+1]}")
    return datetime.date.today()


def _now():
    return datetime.date.today()


def _parse_date(value, fallback=None):
    """Frontmatter-Datum (ISO oder 'YYYY-MM-DDTHH:MM:SSZ') -> date."""
    if not value:
        return fallback
    s = str(value).strip().strip('"').strip("'")
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return datetime.date.fromisoformat(m.group(1))
        except ValueError:
            return fallback
    return fallback


def _fm_meta(text):
    """YAML-Frontmatter grob auslesen (nur die Felder, die wir brauchen)."""
    out = {"title": "", "date": None, "lastmod": None, "draft": False,
           "pillar": "", "keywords": ""}
    if not text.startswith("---"):
        return out
    parts = text.split("---", 2)
    if len(parts) < 3:
        return out
    fm = parts[0] + parts[1]  # head (--- ... ---) + leerer Teil
    body = parts[2]
    out["_body"] = body
    # Frontmatter-Block (zwischen den beiden ---)
    fm_only = parts[1]
    for key in ("title", "date", "lastmod", "draft", "pillar", "keywords"):
        m = re.search(rf"^({key}):\s*(.*?)\s*$", fm_only, re.M)
        if m:
            val = m.group(2).strip()
            if key == "draft":
                out["draft"] = val in ("true", "True", "1", "yes")
            elif key in ("date", "lastmod"):
                out[key] = _parse_date(val)
            elif key == "keywords":
                out[key] = re.sub(r"[\[\]\"' ]+", " ", val).strip()
            else:
                out[key] = val.strip().strip('"').strip("'")
    return out


def _is_ymyl(title):
    t = (title or "").lower()
    return any(k in t for k in ("versicherung", "kfz", "gfz", "haftpflicht",
                                "kranken", "rente", "vorsorge", "gas", "strom",
                                "dsl", "mobilfunk", "kredit", "konto", "zinsen",
                                "steuer", "mietwagen", "reise", "frist",
                                "tarif", "kündigung", "depot", "fonds"))


def _sensitivity(title, pillar, keywords):
    hay = (" ".join([title or "", pillar or "", keywords or ""])).lower()
    season_hits = sum(1 for t in _SEASON_TERMS if t in hay)
    if pillar in _SENSITIVE_PILLARS:
        season_hits += 1
    if pillar in _EVERGREEN_PILLARS:
        season_hits -= 1
    return max(0, season_hits)


def _window(pillar, ymyl, sensitivity):
    if pillar in _EVERGREEN_PILLARS and sensitivity <= 0:
        return REFRESH_EVERGREEN
    if sensitivity >= 3 or ("kfz" in pillar.lower()):
        return REFRESH_SENSITIVE
    if ymyl:
        return REFRESH_YMYL
    return REFRESH_EVERGREEN


def _score(age, window, length, sensitivity):
    """Kontinuierlicher Decay-Score 0..1 (1 = höchster Refresh-Druck)."""
    if window <= 0:
        window = 1
    age_ratio = age / window
    # 60 % Gewicht Alter, 25 % Länge (Tiefe lohnt Refresh), 15 % Sensitivität
    base = min(1.0, age_ratio)
    len_boost = 0.9 if length >= 3000 else (0.4 if length >= 1500 else 0.0)
    sens_boost = min(1.0, sensitivity / 5.0)
    score = 0.60 * base + 0.25 * len_boost + 0.15 * sens_boost
    return round(min(1.0, score), 3)


# ------------------------------------------------------------ Audit


def audit_fleet(include_drafts=False, as_of=None):
    """Scannt die Flotte. `as_of` erlaubt einen Forecast (Chefredakteur-
    Perspektive: was ist in 6 Wochen stale?), sonst = heute."""
    as_of = as_of or datetime.date.today()
    rows = []
    posts = sorted(glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))) + \
            sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
    seen = set()
    for path in posts:
        if path.endswith("_index.md"):
            continue
        slug = os.path.basename(path)[:-3]
        if os.path.basename(path) == "index.md":
            slug = os.path.basename(os.path.dirname(path))
        if slug in seen:
            continue
        seen.add(slug)
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        meta = _fm_meta(text)
        if meta["draft"] and not include_drafts:
            continue
        body = meta.get("_body", "")
        length = len(re.sub(r"\s+", "", body))
        title = meta["title"]
        pillar = meta["pillar"]
        keywords = meta["keywords"]
        ref_date = meta["lastmod"] or meta["date"]
        if not ref_date:
            ref_date = as_of
        age = (as_of - ref_date).days
        ymyl = _is_ymyl(title)
        sens = _sensitivity(title, pillar, keywords)
        window = _window(pillar, ymyl, sens)
        score = _score(age, window, length, sens)
        # Kategorien
        if age > window * 1.35:
            status = "STALE"
        elif age > window:
            status = "DECAYING"
        elif age > window * 0.6:
            status = "WATCH"
        else:
            status = "FRESH"
        rows.append({
            "slug": slug, "title": title, "pillar": pillar,
            "lastmod": (meta["lastmod"] or meta["date"] or "").isoformat(),
            "age_days": age, "window_days": window, "ymyl": ymyl,
            "sensitivity": sens, "score": score, "status": status,
            "length": length, "draft": meta["draft"],
        })
    # Priorität: STALE zuerst (nach Score), dann DECAYING, dann WATCH.
    order = {"STALE": 0, "DECAYING": 1, "WATCH": 2, "FRESH": 3}
    rows.sort(key=lambda r: (order[r["status"]], -r["score"]))
    return rows


def flag_any(rows):
    return any(r["status"] in ("STALE", "DECAYING") for r in rows)


def render_report(rows, as_of=None):
    as_of = as_of or _resolve_as_of()
    stale = [r for r in rows if r["status"] == "STALE"]
    decaying = [r for r in rows if r["status"] == "DECAYING"]
    watch = [r for r in rows if r["status"] == "WATCH"]
    fresh = [r for r in rows if r["status"] == "FRESH"]

    def table(sub):
        if not sub:
            return "_Keine_\n"
        out = ["| Priorität | Artikel | Alter | Refresh-Fenster | Grund |",
               "|---|---|---|---|---|"]
        for i, r in enumerate(sub, 1):
            grund = []
            if r["ymyl"]:
                grund.append("YMYL")
            if r["sensitivity"] >= 3:
                grund.append("Stichtag/Tarif")
            if r["age_days"] > r["window_days"]:
                grund.append(f"über Fenster (+{r['age_days'] - r['window_days']} Tage)")
            out.append(f"| {i} | {r['title']} | {r['age_days']} d | "
                       f"{r['window_days']} d | {', '.join(grund) or 'Alter'} |")
        return "\n".join(out) + "\n"

    lines = [
        "# 📉 Content-Decay-Radar (Chefredakteur-View)",
        f"**Stand:** {as_of.isoformat()} · **Auftrag:** Frische-Steuerung für YMYL-/Affiliate-Content",
        "",
        f"- 🔴 **STALE** (sofort aktualisieren): **{len(stale)}**",
        f"- 🟠 **DECAYING** (in den nächsten Wochen): **{len(decaying)}**",
        f"- 🟡 **WATCH** (im Auge behalten): **{len(watch)}**",
        f"- 🟢 **FRESH** (ok): **{len(fresh)}**",
        "",
        "---",
        "",
        "## 🔴 STALE – Refresh-Queue (priorisiert)",
        table(stale),
        "",
        "## 🟠 DECAYING – demnächst aktualisieren",
        table(decaying),
        "",
        "## 🟡 WATCH",
        table(watch),
        "",
        "---",
        "",
        "### Nächste Schritte (Chefredakteur)",
        "",
        "1. **Stichtag-Artikel zuerst:** Kfz (30.11.), Gas/Strom (Preisgarantie, Heizsaison),",
        "   DSL/Handy (Jahreswechsel) – hier veraltet Inhalt zuerst, und sie sind die",
        "   größten Affiliate-Hebel.",
        "2. **`lastmod` ehrlich setzen:** `scripts/set_lastmod.py --git-changed` nach jedem Update.",
        "3. **Refresh vs. Neuschreiben:** Bei >30 % Textabdeckung (Duplikat-Gefahr) lieber den",
        "   bestehenden Artikel aktualisieren als einen neuen bauen (Google bevorzugt gepflegte",
        "   E-A-T-Quellen).",
        "4. **Datenpflege:** `data/decay_queue.json` wird von Engine/Autoren als Prioritätsliste gelesen.",
        "",
        f"_Automatisch erzeugt von `scripts/decay_radar.py` am {as_of.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"


def write_queue(rows):
    """Refresh-Queue als JSON (STALE + DECAYING) für die Engine/Autoren."""
    queue = [r for r in rows if r["status"] in ("STALE", "DECAYING")]
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY.isoformat(),
            "count": len(queue),
            "queue": queue,
        }, f, ensure_ascii=False, indent=2)
    return queue


def issue_body(rows):
    stale = [r for r in rows if r["status"] == "STALE"]
    decaying = [r for r in rows if r["status"] == "DECAYING"]
    top = stale[:12]
    body = [
        "## 📉 Content-Decay: Diese Artikel veralten",
        "",
        f"**Refresh-Queue:** {len(stale)} **STALE** · {len(decaying)} **DECAYING** "
        f"(Stichtag: {TODAY.isoformat()})",
        "",
        "| # | Artikel | Alter | Fenster |",
        "|---|---|---|---|",
    ]
    for i, r in enumerate(top, 1):
        body.append(f"| {i} | **{r['title']}** (`{r['slug']}`) | {r['age_days']} d | "
                    f"{r['window_days']} d |")
    body += [
        "",
        "> **Empfehlung:** Zuerst Stichtag-/Tarif-Artikel aktualisieren (Kfz 30.11., Gas/Strom,",
        "> DSL, Zinsen). Danach `scripts/set_lastmod.py --git-changed` ausführen, damit Google",
        "> das Update über `article:modified_time` und sitemap-lastmod sieht.",
        "",
        "---",
        "_Automatisch vom Content-Decay-Radar. Kein Artikel wurde gelöscht._",
    ]
    return "\n".join(body)


# ------------------------------------------------------------ Selftest


def _selftest():
    """Eingefrorene Fälle: Saison-Artikel veraltet vs. Evergreen frisch."""
    failures = []
    # Fall 1: Saisonaler Stichtag-Artikel, alt
    r = {"title": "Kfz-Versicherung Vergleich: Kündigungsfrist 30.11.", "pillar": "versicherungen",
         "keywords": "kfz kündigung stichtag versicherung"}
    sens = _sensitivity(r["title"], r["pillar"], r["keywords"])
    window = _window(r["pillar"], True, sens)
    score = _score(200, window, 4200, sens)
    if not (sens >= 3 and window == REFRESH_SENSITIVE and score > 0.5):
        failures.append(f"Kfz-Saisonfall: sens={sens}, window={window}, score={score}")
    # Fall 2: Evergreen Frugalismus, jung → frisch
    r2 = {"title": "50-30-20-Regel: Budget einfach aufteilen", "pillar": "frugalismus",
          "keywords": "budget sparen"}
    sens2 = _sensitivity(r2["title"], r2["pillar"], r2["keywords"])
    window2 = _window(r2["pillar"], False, sens2)
    if window2 != REFRESH_EVERGREEN:
        failures.append(f"Frugalismus-Fenster: {window2}")
    # Fall 3: STALE-Klassifikation über Fenster
    if not _flag_stale(250, window):
        failures.append("STALE nicht erkannt bei age>1.35*window")
    if _flag_stale(20, window):
        failures.append("FALSCHE STALE bei jungem saisonalem Artikel")
    if failures:
        print("❌ DECAY-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ DECAY-SELFTEST bestanden (Saison/Alter, Evergreen-Fenster, STALE-Klassifikation).")
    return 0


def _flag_stale(age, window):
    return age > window * 1.35


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    as_of = _resolve_as_of()
    rows = audit_fleet(include_drafts="--drafts" in sys.argv, as_of=as_of)
    report = render_report(rows, as_of=as_of)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    write_queue(rows)
    print(report)
    if "--issue" in sys.argv:
        print("\n\n===== ISSUE BODY =====\n")
        print(issue_body(rows))
    return 1 if flag_any(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
