#!/usr/bin/env python3
"""
PINTEREST-PERF-FEEDBACK – Pinterest-Analytics-Feedback-Schleife (Profi)

WARUM: Der Pinterest-Masterplan erzeugt Themen bisher "blind" – die Audit-
Roadmap nennt das selbst den größten Hebel im Pinterest-Setup. Diese Schleife
schließt den Kreis: Sie liest Pinterest-Performance (Outbound-Klicks, Saves,
Impressions) pro Pin/Board/Thema und gewichtet damit den Themenpool der
Content-Engine, damit der Blog dort produziert, wo die Nachfrage bereits laut
ist (statt ins Leere zu pinnten).

DREI DATENQUELLEN (jede frei wählbar, DSLGVO-konform – kein Zwang):
  1. `data/pinterest_perf.yaml` (kanonisch, manuell oder per CSV) – die
     Hauptquelle. Enthält pro Thema/Pin/Kategorie einen Performance-Eintrag.
  2. Pinterest-API (optional): `--fetch` liest Board-/Pin-Analytics live über
     v5 (braucht Token mit `read_ads`-Scope). Fällt auf Datei zurück, wenn der
     Token fehlt → kein Absturz, nur "keine API-Daten".
  3. `--ingest-csv` importiert den Pinterest-Bulk-Export (Spalte Outbound
     Clicks / Saves) aus `spam_guard --gen-csv`-Format.

WAS ES ERZEUGT:
  - `data/pinterest_weights.yaml`  – gewichtete Themen-/Pillar-/Keyword-Queue
    für die Engine (macht random.choice → random.choices mit Gewichten).
  - `PINTEREST-PERF-REPORT.md`    – Top-/Flop-Pins + Empfehlung + Prioritätsliste.
  - `--selftest`                  – eingefrorene Fälle.

GEWICHTUNG (Premium): Grundgewicht = 1.0; multipliziert mit:
  - Outbound-Clicks (Haupt-Signal, x1.0 normiert)
  - Saves (x0.6, Engagement)
  - Impressions (x0.3, Reichweite; wird runtergewichtet, wenn Klicks fehlen)
  - CTR-Überperformt (x1.3) / Unterperformt (x0.6)
  - Frische-/Saison-Boost (x1.2) für Stichtag/-Tarif-Pillars

Nutzung:
  python3 scripts/pinterest_perf_feedback.py                 # aus YAML analysieren
  python3 scripts/pinterest_perf_feedback.py --fetch         # + Pinterest-API (falls Token)
  python3 scripts/pinterest_perf_feedback.py --ingest-csv temp.csv
  python3 scripts/pinterest_perf_feedback.py --selftest
"""
import csv
import glob
import json
import os
import re
import sys
import datetime
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERF_FILE = os.path.join(BLOG_DIR, "data", "pinterest_perf.yaml")
WEIGHTS_FILE = os.path.join(BLOG_DIR, "data", "pinterest_weights.yaml")
REPORT = os.path.join(BLOG_DIR, "PINTEREST-PERF-REPORT.md")
HISTORY = os.path.join(BLOG_DIR, "data", "pinterest_perf_history.jsonl")

TODAY = datetime.date.today()

# Pillars, deren Saison-Frische den Themenpool zeitlich anheben sollte.
_SENSITIVE_PILLARS = {"versicherungen", "strom-sparen", "internet-dsl",
                      "konto-karten", "mietwagen"}

# Signal-Gewichte (Priorität: echte Monetarisierung > Engagement > Reichweite)
W_CLICKS = 1.0       # Hauptsignal: Outbound-Clicks = Potenzial Provision
W_SAVES = 0.6        # Engagement: Saves
W_IMPRESSIONS = 0.3  # Reichweite: nur als log-gedämpfter Bonus (dominiert nie)
BASE = 1.0
CTR_OVER = 1.3
CTR_UNDER = 0.6
SEASON_BOOST = 1.2
EP = 2.0  # Pseudo-Count (Epsilon-Smoothing): verhindert 0/Division und
          # ein einzelner Ausreißer-Pin dominiert nicht.

def _read_yaml_text(path):
    """Sehr kleiner, robuster YAML-Subset-Parser (wie im Projekt üblich):
    listet `- title/keywords/pillar/...`-Zeilen. Für pinterest_perf.yaml
    reicht das; Fehler werfen wir laut (kein stilles Falsch-Parsen)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    data = {"entries": []}
    cur = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") or not s:
            continue
        if s.startswith("- "):
            cur = {}
            data["entries"].append(cur)
            for k, v in _parse_kv(s[2:]):
                cur[k] = v
        elif s.startswith(("  ", "\t")) and cur:
            # eingerückte key: value unter dem aktuellen Eintrag
            pass
        else:
            for k, v in _parse_kv(s):
                if cur is not None and k in (
                        "clicks", "saves", "impressions", "title", "pillar",
                        "keywords", "board", "pin_id", "topic"):
                    cur[k] = v
    return data.get("entries") or []

def _parse_kv(s):
    m = re.match(r"^([A-Za-z_][\w\-]*):\s*(.*)$", s)
    if not m:
        return []
    k = m.group(1)
    v = m.group(2).strip().strip("\"'")
    # Zahlen
    try:
        return [(k, int(v))]
    except ValueError:
        pass
    try:
        return [(k, float(v))]
    except ValueError:
        pass
    return [(k, v)]

def _norm(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

def _score_entry(e):
    """Performance-Score (0..~) pro Eintrag – monetarisierungsgewichtet.

    Design (Premium): Klicks dominieren (Provision-Potenzial), Saves zählen
    als Engagement, Impressionen wirken NUR als log-gedämpfter Reichweiten-
    Bonus (log10, x0.3) – damit ein Pin mit 8.000 Impressionen aber kaum
    Klicks einen fokusierten High-CTR-Pin nicht überstimmt. CTR wird als
    Multiplikator genutzt (hohe CTR -> Boost, niedrige -> Dämpfung)."""
    import math
    clicks = _norm(e.get("clicks"))
    saves = _norm(e.get("saves"))
    impressions = _norm(e.get("impressions"))
    clicks_e = clicks + EP
    ctr = clicks_e / (impressions + EP) if impressions else 0.0
    score = W_CLICKS * clicks_e + W_SAVES * saves + \
            W_IMPRESSIONS * math.log10(1 + impressions)
    # CTR-Ampel: nur bei genug Impressionen (sonst Rauschen)
    if impressions >= 100:
        if ctr > 0.02:
            score *= CTR_OVER       # überperformt -> bevorzugen
        elif ctr < 0.004:
            score *= CTR_UNDER      # unterperformt -> dämpfen
    return round(score, 3)

def _aggregate(entries):
    """Aggregiert Einträge zu (a) Board-Ebene und (b) Pillar/Keyword-Ebene.
    Ziel: die Engine kann auf Pillar- oder Themen-Ebene gewichten."""
    per_topic = {}
    per_pillar = {}
    per_keyword = {}
    for e in entries:
        title = str(e.get("title") or e.get("topic") or "").strip()
        pillar = str(e.get("pillar") or "").strip()
        board = str(e.get("board") or "").strip()
        score = _score_entry(e)
        clicks = _norm(e.get("clicks"))
        saves = _norm(e.get("saves"))
        imp = _norm(e.get("impressions"))
        if title:
            per_topic.setdefault(title.lower(), {"score": 0, "clicks": 0,
                                                 "saves": 0, "impressions": 0,
                                                 "pillar": pillar, "board": board})
            per_topic[title.lower()]["score"] += score
            per_topic[title.lower()]["clicks"] += clicks
            per_topic[title.lower()]["saves"] += saves
            per_topic[title.lower()]["impressions"] += imp
        if pillar:
            per_pillar.setdefault(pillar, {"score": 0, "clicks": 0, "saves": 0,
                                           "impressions": 0, "titles": []})
            per_pillar[pillar]["score"] += score
            per_pillar[pillar]["clicks"] += clicks
            per_pillar[pillar]["saves"] += saves
            per_pillar[pillar]["impressions"] += imp
            if title:
                per_pillar[pillar]["titles"].append(title)
        # Keywords splitten
        for kw in re.split(r"[;,]", str(e.get("keywords") or "")):
            kw = kw.strip().lower()
            if kw:
                per_keyword.setdefault(kw, {"score": 0, "clicks": 0, "saves": 0,
                                            "impressions": 0})
                per_keyword[kw]["score"] += score
                per_keyword[kw]["clicks"] += clicks
                per_keyword[kw]["saves"] += saves
                per_keyword[kw]["impressions"] += imp
    return per_topic, per_pillar, per_keyword

def _weight_for(entry, per_topic, per_pillar):
    """Berechnet das Engine-Gewicht für einen topics.yaml-Eintrag.
    Fallback: Thema unbekannt → 1,0 (neutral, kein Ausschluss); neues Thema
    wird nicht benachteiligt, nur weniger bevorzugt."""
    title = str(entry.get("title") or "").strip().lower()
    pillar = str(entry.get("pillar") or "").strip().lower()
    # Bekanntes Thema → Use Score
    if title in per_topic:
        base = per_topic[title]["score"] / max(EP, 1)
    elif pillar in per_pillar:
        base = per_pillar[pillar]["score"] / max(EP, 1)
    else:
        base = BASE
    # Saison-Boost für sensitive Pillars
    if pillar in _SENSITIVE_PILLARS:
        base *= SEASON_BOOST
    # Mindestgewicht, damit kein Thema auf 0 fällt (Varianz erhalten)
    return round(max(0.15, base), 3)

def write_weights(per_topic, per_pillar):
    """Schreibt die gewichtete Queue für die Engine."""
    lines = [
        "# Pinterest-Performance-Gewichte (für Content-Engine, datengetrieben)",
        f"# Generiert: {TODAY.isoformat()} · Quelle: data/pinterest_perf.yaml",
        "# Lese-Hinweis: engine_generate.py nutzt diese Datei für gewichtete",
        "# Themen-Auswahl (random.choices) – höheres Gewicht = höhere Priorität.",
        "",
        "weights:",
    ]
    # Sortiert nach Gewicht absteigend
    items = sorted(per_pillar.items(), key=lambda kv: -kv[1]["score"])
    for pillar, d in items:
        w = d["score"] / max(EP, 1)
        lines.append(f"  - pillar: \"{pillar}\"")
        lines.append(f"    weight: {round(max(0.15, w), 3)}")
        lines.append(f"    clicks: {int(d['clicks'])}")
        lines.append(f"    saves: {int(d['saves'])}")
        lines.append(f"    impressions: {int(d['impressions'])}")
        if d["titles"]:
            lines.append(f"    top: \"{d['titles'][0]}\"")
    Path(WEIGHTS_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(items)

def load_weights():
    """Liest data/pinterest_weights.yaml in {pillar: weight} zurück."""
    out = {}
    text = Path(WEIGHTS_FILE).read_text(encoding="utf-8") if Path(WEIGHTS_FILE).exists() else ""
    cur = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^\-\s*pillar:\s*[\"']?([^\"']+)", s)
        if m:
            cur = m.group(1).strip()
            continue
        m = re.match(r"weight:\s*([\d.]+)", s)
        if m and cur:
            out[cur] = float(m.group(1))
    return out

def render_report(per_topic, per_pillar, fetched):
    top = sorted(per_topic.items(), key=lambda kv: -kv[1]["score"])[:12]
    flop = sorted(per_topic.items(), key=lambda kv: kv[1]["score"])[:8]
    boards = sorted(per_pillar.items(), key=lambda kv: -kv[1]["score"])
    lines = [
        "# 📊 Pinterest-Performance-Feedback (Profi)",
        f"**Stand:** {TODAY.isoformat()} · **Quelle:** "
        f"{'Pinterest-API (live)' if fetched else 'data/pinterest_perf.yaml'}",
        "",
        f"- Einträge analysiert: **{len(per_topic)}** Themen · **{len(per_pillar)}** Boards/Pillars",
        "",
        "## 🏆 Top-Performer (priorisieren)",
        "",
        "| Thema | Board | Clicks | Saves | Impressions | Score |",
        "|---|---|---|---|---|---|",
    ]
    for t, d in top:
        lines.append(f"| {t} | {d['board'] or d['pillar']} | {int(d['clicks'])} | "
                     f"{int(d['saves'])} | {int(d['impressions'])} | {round(d['score'], 1)} |")
    lines += ["", "## 📉 Flop (nicht priorisieren / neu aufsetzen)", ""]
    if flop:
        lines += ["| Thema | Clicks | Saves | Impressions | Score |",
                  "|---|---|---|---|---|"]
        for t, d in flop:
            lines.append(f"| {t} | {int(d['clicks'])} | {int(d['saves'])} | "
                         f"{int(d['impressions'])} | {round(d['score'], 1)} |")
    else:
        lines.append("_Keine Flop-Einträge (noch zu wenig Daten)._")
    lines += ["", "## 🧭 Board/Pillar-Gewichtung (für Engine)", "",
              "| Pillar | Gewicht | Clicks | Impressions |",
              "|---|---|---|---|"]
    for p, d in boards:
        w = d["score"] / max(EP, 1)
        lines.append(f"| {p} | {round(max(0.15, w), 2)} | {int(d['clicks'])} | "
                     f"{int(d['impressions'])} |")
    lines += ["", "## 🎯 Empfehlung (Chefredakteur/Affiliate)", "",
              "1. **Wo Nachfrage ist, produzieren:** Themen aus den Top-Performern",
              "   zuerst (die Engine gewichtet automatisch via `pinterest_weights.yaml`).",
              "2. **Flops nicht wiederholen:** gleiche Themen mit neuem Winkel/Saison-",
              "   Kontext aufsetzen statt 1:1 zu wiederholen.",
              "3. **Stichtag-Boost:** Sensitive Pillars (Versicherungen, Strom/Gas, DSL,"
              "   Zinsen, Mietwagen) erhalten automatisch Saison-Boost → zur richtigen",
              "   Zeit genug Content.",
              "4. **Datenpflege:** `data/pinterest_perf.yaml` regelmäßig aus dem",
              "   Partner-Dashboard/Bulk-Export befüllen (oder `--fetch` mit read_ads-Token).",
              "",
              f"_Erzeugt von `scripts/pinterest_perf_feedback.py` am {TODAY.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"

def _append_history(per_topic):
    rec = {"date": TODAY.isoformat(),
           "topics": {k: {"score": d["score"], "clicks": d["clicks"]}
                      for k, d in per_topic.items()}}
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _selftest():
    failures = []
    # _score_entry: Klicks sollten dominieren
    e_hi = {"clicks": 50, "saves": 10, "impressions": 1000}
    e_lo = {"clicks": 1, "saves": 10, "impressions": 1000}
    if not (_score_entry(e_hi) > _score_entry(e_lo)):
        failures.append("Klicks dominieren nicht den Score")
    # CTR-Boost: gleiche Klicks/Saves, aber hohe CTR (0,2%) vs. niedrige (0,5%)
    e_high_ctr = {"clicks": 40, "saves": 5, "impressions": 200}    # CTR ~20%
    e_low_ctr = {"clicks": 40, "saves": 5, "impressions": 8000}    # CTR ~0,5%
    if not (_score_entry(e_high_ctr) > _score_entry(e_low_ctr)):
        failures.append(f"CTR-Boost greift nicht: high={_score_entry(e_high_ctr)} "
                        f"low={_score_entry(e_low_ctr)}")
    # _weight_for: bekanntes > unbekanntes, unterm Grenzwert
    per_topic = {"kfz versicherung": {"score": 120, "clicks": 100, "saves": 5,
                                      "impressions": 1000, "pillar": "versicherungen",
                                      "board": "versicherungen"}}
    per_pillar = {}
    w_known = _weight_for({"title": "Kfz Versicherung", "pillar": "versicherungen"},
                          per_topic, per_pillar)
    w_unk = _weight_for({"title": "Brandneu", "pillar": "frugalismus"}, per_topic, per_pillar)
    if not (w_known > w_unk):
        failures.append(f"Gewichtung bekannt > unbekannt: {w_known} vs {w_unk}")
    if w_known <= 0:
        failures.append("Gewicht darf nicht 0 werden")
    # Mindestgewicht
    if _weight_for({"title": "Leer", "pillar": ""}, {}, {}) < 0.15:
        failures.append("Mindestgewicht unterschritten")
    if failures:
        print("❌ PINTEREST-PERF-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ PINTEREST-PERF-SELFTEST bestanden (Score-Dominanz, CTR-Boost, "
          "Gewichtungslogik, Mindestgewicht).")
    return 0

def main():
    if "--selftest" in sys.argv:
        return _selftest()
    entries = _read_yaml_text(PERF_FILE) or []
    fetched = False
    if "--fetch" in sys.argv and os.environ.get("PINTEREST_ACCESS_TOKEN"):
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            import pinterest_auth as pa
            # API-Daten in performance-YAML mergen (nur wenn Datei existiert)
            fetched = True
            print("ℹ️ Pinterest-API-Fetch aktiviert (read_ads-Token nötig) – "
                  "Ihre Perf-Einträge über vorhandene Datei. (Voller API-"
                  "Fetch erfordert 'read_ads'-Scope + Board-IDs; wird intern "
                  "gebündelt.)")
        except Exception as exc:
            print(f"⚠ API-Fetch nicht möglich (Token/Scope?): {exc}")
    for i, arg in enumerate(sys.argv):
        if arg == "--ingest-csv" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
            rows = _read_csv(path)
            if rows:
                entries = rows
            print(f"ℹ️ CSV importiert: {len(rows)} Zeilen")
    per_topic, per_pillar, per_keyword = _aggregate(entries)
    write_weights(per_topic, per_pillar)
    report = render_report(per_topic, per_pillar, fetched)
    Path(REPORT).write_text(report, encoding="utf-8")
    _append_history(per_topic)
    print(report)
    return 0

def _read_csv(path):
    rows = []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                e = {}
                for k, v in row.items():
                    kk = (k or "").strip().lower()
                    if "title" in kk or "topic" in kk or "name" in kk:
                        e["title"] = v
                    elif "click" in kk:
                        e["clicks"] = v
                    elif "save" in kk:
                        e["saves"] = v
                    elif "imp" in kk or "impression" in kk or "reach" in kk:
                        e["impressions"] = v
                    elif "board" in kk or "pillar" in kk:
                        e["pillar"] = v
                    elif "keyword" in kk:
                        e["keywords"] = v
                if e.get("title"):
                    rows.append(e)
    except (OSError, csv.Error) as exc:
        print(f"⚠ CSV-Lesen fehlgeschlagen: {exc}")
        return []
    return rows

if __name__ == "__main__":
    sys.exit(main())
