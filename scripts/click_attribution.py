#!/usr/bin/env python3
"""
CLICK-ATTRIBUTION – Anonymes Klick-Tracking im /go/-Gateway (Profi-Affiliate)

WARUM: Der Blog misst bisher Traffic, aber nicht, WELCHER Artikel WIE VIELE
Klicks auf CHECK24 (/go/<key>/) erzeugt. Als Affiliate-Manager ist der erste
Investitionsschritt laut eigener Audit-Roadmap genau das: Content nach
**Umsatz-Hebel** priorisieren statt nach Bauchgefühl / nur Traffic.

DSGVO-GRUNDLAGE:
  - Umami ist cookielos (kein Consent-Zwang), setzt `data-do-not-track=true`
    und respektiert DNT. Das Event `affiliate_click` wird am **Artikel-Link**
    gefeuert (vor der Navigation), trägt Ziel-/go/-Key + Quelle-Artikel + Pillar
    (seit 01.09.2026, siehe layouts/_default/_markup/render-link.html).
  - Dieses Skript liest NUR aggregierte Indikatoren (Counts je
    Artikel/Stelle/Pillar) – keine IPs, keine Profile. Es enthält einen
    Identifikator-Schutz, der URL-/Artikelfelder kürzt/escaped.

DATENQUELLEN (jede wählbar):
  1. `--umami-file <json|csv>`  – Export der Umami-`affiliate_click`-Events.
     Erwartet Felder: event, slug (oder /go/<key>), article (optional),
     pillar (optional), count oder x/Zeilen.
  2. `data/umami_clicks.json`    – Standardpfad (wird von einem manuellen
     Umami-Export oder einem Fetch-Job dorthin gelegt).
  3. `data/click_stats.yaml`     – kuratierte Zusammenfassung (manuell).

AUSGABE:
  - `CLICK-REPORT.md`            – Top-Artikel nach Klicks (Umsatz-Hebel),
    Pillar-Aggregation, /go/-Stellen-Statistik, Empfehlung.
  - `data/click_stats.json`      – maschinenlesbar (für Scorecard/Engine).
  - `--issue`                    – GitHub-Issue-Body.

Exit: 0 = ok, 1 = Klicks vorhanden/Handlungsbedarf, 2 = Selftest/Fehler.
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
REPORT = os.path.join(BLOG_DIR, "CLICK-REPORT.md")
STATS = os.path.join(BLOG_DIR, "data", "click_stats.json")
DEFAULT_UMA = os.path.join(BLOG_DIR, "data", "umami_clicks.json")
TODAY = datetime.date.today()

# Sensitive Feldlängen/Kürzung (Datenschutz: keine langen URLs/Slugs
# mit Elementen, die Rückschlüsse erlauben).
MAX_FIELD = 80


def _safe(v):
    """Kürzt/escaped Felder – Identifikator-Schutz."""
    s = re.sub(r"[\x00-\x1f]", "", str(v or ""))
    return s[:MAX_FIELD]


def _norm_go_key(raw):
    """Ermittelt den /go/-Zielschlüssel (aus 'slug', '/go/<key>/' oder URL)."""
    s = str(raw or "")
    m = re.search(r"/go/([\w\-]+)/", s)
    if m:
        return m.group(1)
    m = re.match(r"^([\w\-]+)$", s)
    if m:
        return m.group(1)
    return _safe(s)


def _read_umami(path):
    """Liest Umami-Export (JSON-Array von Events ODER CSV)."""
    path = Path(path)
    if not path.exists():
        return []
    try:
        txt = path.read_text(encoding="utf-8")
    except OSError:
        return []
    # CSV?
    if path.suffix.lower() == ".csv":
        return _read_csv(path)
    # JSON: Array von Objekten { event, slug, article, pillar, count/x }
    try:
        data = json.loads(txt)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get("events") or data.get("data") or []
    rows = []
    for ev in data:
        if not isinstance(ev, dict):
            continue
        event = ev.get("event") or ev.get("type") or ""
        if event and "affiliate_click" not in str(event):
            continue
        rows.append({
            "slug": ev.get("slug") or ev.get("url") or "",
            "article": ev.get("article") or ev.get("path") or ev.get("page") or "",
            "pillar": ev.get("pillar") or ev.get("article_pillar") or "",
            "count": int(ev.get("count") or ev.get("x") or 1),
        })
    return rows


def _read_csv(path):
    rows = []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            for rec in csv.DictReader(f):
                row = {}
                for k, v in rec.items():
                    kk = (k or "").strip().lower()
                    v = (v or "").strip()
                    if kk in ("event", "type") and "affiliate_click" not in v:
                        row = None
                        break
                    if kk in ("slug", "go", "go_key", "url", "href"):
                        row["slug"] = v
                    elif kk in ("article", "page", "path", "source"):
                        row["article"] = v
                    elif kk in ("pillar", "category", "board"):
                        row["pillar"] = v
                    elif kk in ("count", "x", "clicks", "events"):
                        row["count"] = v
                if row and (row.get("slug") or row.get("article")):
                    row["count"] = int(row.get("count") or 1)
                    rows.append(row)
    except (OSError, csv.Error, ValueError):
        return []
    return rows


def _aggregate(rows):
    """Aggregiert Klicks pro Artikel, Pillar und /go/-Stelle."""
    per_article = {}
    per_pillar = {}
    per_go = {}
    for r in rows:
        slug = _norm_go_key(r.get("slug"))
        article = _safe(r.get("article") or "")
        pillar = _safe(r.get("pillar") or "").strip().lower()
        count = max(0, int(r.get("count") or 1))
        if article:
            per_article.setdefault(article, {"clicks": 0, "go": {}, "pillar": pillar})
            per_article[article]["clicks"] += count
            per_article[article]["go"][slug] = per_article[article]["go"].get(slug, 0) + count
        if pillar:
            per_pillar.setdefault(pillar, {"clicks": 0, "articles": set(), "go": {}})
            per_pillar[pillar]["clicks"] += count
            per_pillar[pillar]["go"][slug] = per_pillar[pillar]["go"].get(slug, 0) + count
            if article:
                per_pillar[pillar]["articles"].add(article)
        per_go.setdefault(slug, {"clicks": 0, "articles": set()})
        per_go[slug]["clicks"] += count
        if article:
            per_go[slug]["articles"].add(article)
    for d in per_pillar.values():
        d["articles"] = len(d["articles"])
    for d in per_go.values():
        d["articles"] = len(d["articles"])
    return per_article, per_pillar, per_go


def _render(per_article, per_pillar, per_go, source):
    top_articles = sorted(per_article.items(), key=lambda kv: -kv[1]["clicks"])[:15]
    top_go = sorted(per_go.items(), key=lambda kv: -kv[1]["clicks"])[:15]
    top_pillar = sorted(per_pillar.items(), key=lambda kv: -kv[1]["clicks"])
    lines = [
        "# 🖱️ Affiliate-Klick-Attribution (/go/-Gateway)",
        f"**Stand:** {TODAY.isoformat()} · **Quelle:** {source}",
        "",
        f"- Erfasste Positionen: **{len(per_article)}** Artikel · "
        f"**{len(per_go)}** /go/-Stellen · **{len(per_pillar)}** Pillars",
        "",
        "## 🏆 Top-Artikel nach Affiliate-Klicks (Umsatz-Hebel)",
        "",
        "| Artikel | Pillar | Klicks | Top-/go/-Stelle |",
        "|---|---|---|---|",
    ]
    for a, d in top_articles:
        topgo = max(d["go"], key=d["go"].get) if d["go"] else "-"
        lines.append(f"| {a} | {d['pillar'] or '-'} | {d['clicks']} | {topgo} |")
    lines += ["", "## 📊 /go/-Stellen-Ranking", "", "| /go/-Stelle | Klicks | Artikel |",
              "|---|---|---|"]
    for g, d in top_go:
        lines.append(f"| /go/{g}/ | {d['clicks']} | {d['articles']} |")
    lines += ["", "## 🧭 Pillar-Aggregation", "", "| Pillar | Klicks | Artikel |",
              "|---|---|---|"]
    for p, d in top_pillar:
        lines.append(f"| {p} | {d['clicks']} | {d['articles']} |")
    lines += ["", "## 🎯 Empfehlung (Affiliate-Manager)", "",
              "1. **Höchste Klicks → mehr Wasser:** In den Top-Artikeln die CTA-/",
              "   Vergleichs-Anreize stärken (Kurzantworten, Tarifvergleich-Shortcode,",
              "   Trust-Box). Sie sind die Umsatz-Maschine.",
              "2. **Niedrige = Nachfrage-Lücke:** Themen mit wenig Klicks, aber viel",
              "   Traffic → Anzeige-Problem statt Content-Problem (CTA platzieren).",
              "3. **Datenpflege:** `data/click_stats.json` speist die Scorecard;",
              "   Umami-Export regelmäßig einlesen (siehe Premium-Governance).",
              "",
              f"_Erzeugt von `scripts/click_attribution.py` am {TODAY.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"


def _selftest():
    import tempfile
    failures = []
    # _norm_go_key
    if _norm_go_key("/go/kfz-versicherung/") != "kfz-versicherung":
        failures.append("_norm_go_key (URL)")
    if _norm_go_key("strom") != "strom":
        failures.append("_norm_go_key (plain)")
    # aggregation & ranking
    rows = [
        {"slug": "/go/kfz-versicherung/", "article": "a-kfz.md", "pillar": "versicherungen", "count": 5},
        {"slug": "/go/kfz-versicherung/", "article": "a-kfz.md", "pillar": "versicherungen", "count": 3},
        {"slug": "/go/strom/", "article": "a-strom.md", "pillar": "strom-sparen", "count": 2},
    ]
    pa, pp, pg = _aggregate(rows)
    if pa["a-kfz.md"]["clicks"] != 8:
        failures.append(f"Artikel-Summe kfz: {pa['a-kfz.md']['clicks']}")
    if pg["kfz-versicherung"]["clicks"] != 8:
        failures.append(f"/go/-Stelle kfz: {pg['kfz-versicherung']['clicks']}")
    if pp["versicherungen"]["clicks"] != 8:
        failures.append(f"Pillar versicherungen: {pp['versicherungen']['clicks']}")
    # Datenschutz: _safe kürzt
    if len(_safe("x" * 200)) > MAX_FIELD:
        failures.append("_safe kürzt nicht")
    if failures:
        print("❌ CLICK-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ CLICK-SELFTEST bestanden (go-Key-Normalisierung, Aggregation, Datenschutz).")
    return 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    # Quelle wählen
    source = "data/umami_clicks.json"
    path = DEFAULT_UMA
    for i, arg in enumerate(sys.argv):
        if arg == "--umami-file" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
            source = path
    rows = _read_umami(path)
    if not rows:
        # Fallback: kuratierte click_stats.yaml (manuell)
        import yaml as _yaml
        yp = os.path.join(BLOG_DIR, "data", "click_stats.yaml")
        if os.path.exists(yp):
            try:
                data = _yaml.safe_load(open(yp, encoding="utf-8")) or {}
                for e in data.get("clicks") or []:
                    rows.append({
                        "slug": e.get("go") or e.get("slug", ""),
                        "article": e.get("article", ""),
                        "pillar": e.get("pillar", ""),
                        "count": int(e.get("count", 1)),
                    })
                source = "data/click_stats.yaml"
            except Exception as exc:  # noqa: BLE001
                print(f"⚠ click_stats.yaml nicht lesbar: {exc}")
    if not rows:
        print("ℹ️ Keine Klick-Daten gefunden. Erwarte Daten in "
              "data/umami_clicks.json (oder --umami-file).")
        Path(REPORT).write_text(
            f"# 🖱️ Affiliate-Klick-Attribution\n\n**Stand:** {TODAY.isoformat()}\n\n"
            "_Noch keine Daten – Umami-Export (events=affiliate_click) einmalig "
            "nach `data/umami_clicks.json` legen._\n", encoding="utf-8")
        return 0
    per_article, per_pillar, per_go = _aggregate(rows)
    report = _render(per_article, per_pillar, per_go, source)
    Path(REPORT).write_text(report, encoding="utf-8")
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    with open(STATS, "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY.isoformat(),
            "articles": {a: {"clicks": d["clicks"], "pillar": d["pillar"]}
                         for a, d in per_article.items()},
            "pillars": {p: {"clicks": d["clicks"]} for p, d in per_pillar.items()},
            "go": {g: {"clicks": d["clicks"]} for g, d in per_go.items()},
        }, f, ensure_ascii=False, indent=2)
    print(report)
    if "--issue" in sys.argv:
        print("\n===== ISSUE BODY =====\n")
        print(f"## 🖱️ Affiliate-Klick-Attribution\n\n{report}")
    return 1 if per_article else 0


if __name__ == "__main__":
    sys.exit(main())
