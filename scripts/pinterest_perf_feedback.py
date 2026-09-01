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

def _get_token():
    """Löst einen gültigen Pinterest-Access-Token (Auth-Datei oder Env)."""
    if os.environ.get("PINTEREST_ACCESS_TOKEN"):
        return os.environ["PINTEREST_ACCESS_TOKEN"]
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        import pinterest_auth as pa
        t = pa.get_access_token()  # erneuert ggf. Token (continuous refresh)
        return t or ""
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Pinterest-Auth-Refresh übersprungen ({exc}) – nutze Env-Token.")
        return ""


def _api_get(path, token, params=None):
    """GET gegen die Pinterest API v5 (mit Rate-Limit-Respekt)."""
    import urllib.parse
    import urllib.request
    import urllib.error
    url = "https://api.pinterest.com/v5" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Pinterest API {path}: HTTP {exc.code} – "
                           f"{exc.read().decode()[:200]}") from exc


def _fetch_pin_analytics(token, pin_id, days=60):
    """Pin-Analytics (lifetime) für einen Pin. Liefert clicks/saves/impressions.
    Rückgabe als dict {clicks, saves, impressions}. Kein Schreib-Zwang."""
    import datetime as _d
    start = (_d.date.today() - _d.timedelta(days=days)).isoformat()
    end = _d.date.today().isoformat()
    # metric_types (Kap. Pin-Analytics): pin_impression, pin_save,
    # pin_outbound_click (organic). Fehlende Werte werden defensiv behandelt.
    try:
        data = _api_get(f"/pins/{pin_id}/analytics", token, {
            "start_date": start, "end_date": end,
            "metric_types": "pin_impression,pin_outbound_click,pin_save",
            "app_types": "ALL", "split_field": "NO_SPLIT",
        })
        allm = ((data or {}).get("all") or {}).get("lifetime_metrics") or {}
        return {
            "clicks": int(allm.get("pin_outbound_click") or allm.get("pin_click") or 0),
            "saves": int(allm.get("pin_save") or 0),
            "impressions": int(allm.get("pin_impression") or 0),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Pin {pin_id}: Analytics nicht lesbar ({exc})")
        return {"clicks": 0, "saves": 0, "impressions": 0}


def _build_title_index(topics):
    """Normierter Titel -> topic-Eintrag. Für den Pin→Thema-Abgleich."""
    norm = lambda s: re.sub(r"[\W_]+", "", s.lower())  # noqa: E731
    out = {}
    for t in topics:
        tt = (t.get("title") or "").strip()
        if tt:
            out[norm(tt)] = t
    return out


def _build_slug_index(topics):
    """Post-Slug -> topic-Eintrag. Ein Pin-Link zeigt auf /posts/<slug>/; der
    Artikel entstand aus einem Thema. Verknüpfung: der Artikel-Titel == Thema-
    Titel (Engine generiert aus topics.yaml). Wir lesen Posts und matchen deren
    Titel auf den Themenpool."""
    norm = lambda s: re.sub(r"[\W_]+", "", s.lower())  # noqa: E731
    title_index = _build_title_index(topics)
    out = {}
    posts = sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md"))) + \
            sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*.md")))
    for p in posts:
        if os.path.basename(p) == "index.md":
            slug = os.path.basename(os.path.dirname(p))
        else:
            slug = os.path.basename(p)[:-3]
        try:
            body = Path(p).read_text(encoding="utf-8")
        except OSError:
            continue
        # Zuverlässigste Quelle: die eigenen Frontmatter-Felder des Artikels.
        title = ""
        pillar = ""
        kw = ""
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", body, re.M)
        if m:
            title = m.group(1).strip()
        m = re.search(r"^pillar:\s*[\"']?([^\"'\n]+)", body, re.M)
        if m:
            pillar = m.group(1).strip().strip("'\"")
        m = re.search(r"^keywords:\s*\[(.*?)\]", body, re.M)
        if m:
            kw = ", ".join(k.strip().strip('\"') for k in m.group(1).split(",") if k.strip())
        # Prio: Thema mit passendem Titel (holst Board/Keywords/Exaktheit),
        # sonst eigenes Frontmatter (Pillar garantiert vorhanden).
        t = title_index.get(norm(title))
        if t:
            out[slug] = {"title": (t.get("title") or title), "pillar": t.get("pillar") or pillar,
                         "keywords": t.get("keywords") or kw}
        else:
            out[slug] = {"title": title, "pillar": pillar, "keywords": kw}
    return out


def _map_pin_to_entry(pin, topics, title_index=None, slug_index=None):
    """Ordnet einen Pin (title/link/description) einem topics.yaml-Eintrag zu.
    Matching-Reihenfolge: 1) normalisierter Titel, 2) Post-Slug aus dem Link."""
    title = (pin.get("title") or "").strip()
    link = (pin.get("link") or "")
    link_slug = ""
    m = re.search(r"/posts/([^\?#/]+)/?$", link)
    if m:
        link_slug = m.group(1)
    norm = lambda s: re.sub(r"[\W_]+", "", s.lower())  # noqa: E731
    if title_index is None:
        title_index = _build_title_index(topics)
    # 1) Titel-Abgleich
    t = title_index.get(norm(title))
    if t:
        return {"title": (t.get("title") or title), "pillar": t.get("pillar") or "",
                "keywords": t.get("keywords") or ""}
    # 2) Slug-Abgleich über Artikel-Titel
    if slug_index is None:
        slug_index = _build_slug_index(topics)
    if link_slug in slug_index:
        t = slug_index[link_slug]
        return {"title": t.get("title") or title, "pillar": t.get("pillar") or "",
                "keywords": t.get("keywords") or ""}
    return None


def _fetch_live(entries, topics, days, max_pins):
    """Lädt Live-Analytics über die Pinterest API v5 und MERGED sie in `entries`.

    Ablauf: Boards → Pins je Board bis max_pins → Pin-Analytics je Pin →
    Map auf topics.yaml → Merge (dedup nach Titel, übernimmt echte Werte).
    Rückgabe (entries, fetched_count, messages)."""
    import time as _t
    token = _get_token()
    if not token:
        return entries, 0, ["Kein Pinterest-Token (PINTEREST_ACCESS_TOKEN)."]
    try:
        boards = _api_get("/boards?page_size=100", token).get("items", [])
    except Exception as exc:  # noqa: BLE001
        return entries, 0, [f"Boards nicht abrufbar: {exc}"]
    if not boards:
        return entries, 0, ["Keine Boards gefunden."]

    # Titel-Bekannter-Einträge als Ordner (dedup) + Indizes für den Abgleich
    entry_by_title = {}
    for e in entries:
        t = (e.get("title") or "").strip().lower()
        if t:
            entry_by_title[t] = e
    title_index = _build_title_index(topics)
    slug_index = _build_slug_index(topics)

    merged = list(entries)
    fetched_count = 0
    messages = []
    for board in boards:
        board_name = board.get("name", "")
        try:
            pins = _api_get(f"/boards/{board['id']}/pins", token,
                            {"page_size": max_pins}).get("items", [])
        except Exception as exc:  # noqa: BLE001
            messages.append(f"Board '{board_name}': Pins nicht abrufbar ({exc})")
            continue
        for pin in pins:
            pin_id = pin.get("id")
            if not pin_id or fetched_count >= max_pins:
                continue
            # Rate-Limit-Respekt (gesetzt; API erlaubt Limit pro Sekunde)
            _t.sleep(0.35)
            m = _map_pin_to_entry(pin, topics, title_index, slug_index)
            if not m:
                continue
            perf = _fetch_pin_analytics(token, pin_id, days)
            if perf["impressions"] + perf["clicks"] + perf["saves"] == 0:
                continue  # keine Daten -> nicht rauschen
            title = m["title"]
            key = title.lower()
            entry = entry_by_title.get(key)
            if entry is not None:
                entry["clicks"] = int(entry.get("clicks") or 0) + perf["clicks"]
                entry["saves"] = int(entry.get("saves") or 0) + perf["saves"]
                entry["impressions"] = int(entry.get("impressions") or 0) + perf["impressions"]
                if not entry.get("pillar"):
                    entry["pillar"] = m["pillar"]
                if not entry.get("keywords"):
                    entry["keywords"] = m["keywords"]
            else:
                new = {"title": title, "pillar": m["pillar"],
                       "keywords": m["keywords"], "board": board_name,
                       "clicks": perf["clicks"], "saves": perf["saves"],
                       "impressions": perf["impressions"]}
                merged.append(new)
                entry_by_title[key] = new
            fetched_count += 1
    return merged, fetched_count, messages


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    entries = _read_yaml_text(PERF_FILE) or []
    fetched = False
    fetch_msgs = []
    if "--fetch" in sys.argv:
        days = 60
        max_pins = 200
        for i, arg in enumerate(sys.argv):
            if arg == "--days" and i + 1 < len(sys.argv):
                days = int(sys.argv[i + 1])
            if arg == "--max-pins" and i + 1 < len(sys.argv):
                max_pins = int(sys.argv[i + 1])
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            import generate_drafts as g  # noqa: E402
            topics = g.load_topics()
        except Exception:  # noqa: BLE001
            topics = []
        entries, n, fetch_msgs = _fetch_live(entries, topics, days, max_pins)
        if n:
            fetched = True
            _save_yaml(PERF_FILE, entries)
            print(f"✅ Pinterest-API-Fetch: {n} Pin(s) mit Analytics ergänzt "
                  f"(Fenster {days}d, max {max_pins} Pins).")
        else:
            print("ℹ️ Pinterest-API-Fetch: keine neuen Analysen "
                  f"({'; '.join(fetch_msgs) or 'keine Token/Daten'}).")
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
    if fetch_msgs:
        report += "\n### Hinweise zum Live-Fetch\n\n" + "\n".join(f"- {m}" for m in fetch_msgs) + "\n"
    Path(REPORT).write_text(report, encoding="utf-8")
    _append_history(per_topic)
    print(report)
    return 0


def _save_yaml(path, entries):
    """Persistiert die (ggf. live ergänzten) Einträge als Top-Level-Liste im
    gleichen Format, das `_read_yaml_text` wieder liest."""
    lines = [
        "# Pinterest-Performance-Feedback – EINGABEDATEI (Live-Fetch / manuell)",
        f"# Zuletzt geschrieben: {TODAY.isoformat()}",
        "",
    ]
    for e in entries:
        lines.append(f'- title: "{str(e.get("title") or "").strip()}"')
        if e.get("pillar"):
            lines.append(f'  pillar: "{e["pillar"]}"')
        if e.get("keywords"):
            lines.append(f'  keywords: "{e["keywords"]}"')
        if e.get("board"):
            lines.append(f'  board: "{e["board"]}"')
        for k in ("clicks", "saves", "impressions"):
            if e.get(k) is not None:
                lines.append(f"  {k}: {int(e[k])}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")

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
