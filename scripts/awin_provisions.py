#!/usr/bin/env python3
"""
AWIN-PROVISIONS – Awin-Provisions-Import (Klicks -> Umsatz, Profi-Affiliate)

WARUM: Der Blog weiß nun, WELCHER Artikel WIE VIELE /go/-Klicks erzeugt
(click_attribution.py -> Umsatz-Hebel nach Traffic). Es fehlt die letzte Stufe:
wie viel davon tatsächlich UMSATZ (Provision) gebracht hat. Dieser Import
schließt die Lücke: Awin (das Netzwerk hinter CHECK24/Tarifcheck) stellt einen
Transaktions-Report (CSV) bereit – der wird eingelesen, auf Artikel/Pillar
aggreggiert und in die Scorecard gespeist.

DSGVO / Datenschutz:
  - Es werden nur SUN-Provisionssummen verarbeitet (keine Kundendaten).
  - Das Awin-Report-CSV enthält keine personenbezogenen Käuferdaten (nur
    Transaction-ID, Commission, Click-Reference/SubID, Datum, Status).
  - Das Skript erzeugt KEINE Roh-CSV-Kopie; es liest nur und schreibt
    aggregierte Umsatz-Kennzahlen nach data/awin_provisions.json.

SUBID -> ARTIKEL-MAPPING:
  Awin trägt die von uns gesetzte "Click Reference" (SubID) in jede
  Transaktion. Wir setzen die SubID = Artikel-Slug (siehe /go/-Link-Bau).
  Zusätzlich lässt sich eine manuelle Zuordnung in data/subid_map.yaml pflegen.

DATENQUELLEN:
  1. `data/awin_transactions.csv`   – Standardpfad. Füllt sich seit der
     Premium-Messkette VOLLSTÄNDIG AUTOMATISCH über die Awin Publisher API
     (`scripts/awin_fetch.py`, Secrets `AWIN_API_TOKEN` + `AWIN_PUBLISHER_ID`).
  2. `--awin-csv <pfad>`             – beliebiger Awin-Transaktions-Report
     (Dashboard-Export: Reports → Transactions), z. B. das Lauf-CSV des
     Workflows im Arbeitsverzeichnis.

AUSGABE:
  - `AWIN-REPORT.md`              – Umsatz pro Artikel/Pillar + Kommentar.
  - `data/awin_provisions.json`   – maschinenlesbar (für Scorecard/Engine).
  - `--gen-subid-map`             – erzeugt data/subid_map.yaml aus den Artikeln.

Exit: 0 = ok, 1 = Handlungsbedarf (z. B. SubIDs fehlen), 2 = Selftest/Fehler.
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
REPORT = os.path.join(BLOG_DIR, "AWIN-REPORT.md")
STATS = os.path.join(BLOG_DIR, "data", "awin_provisions.json")
SUBMAP = os.path.join(BLOG_DIR, "data", "subid_map.yaml")
DEFAULT_CSV = os.path.join(BLOG_DIR, "data", "awin_transactions.csv")
TODAY = datetime.date.today()

# Awin-Status-Vokabular → Trichter-Stufen (Antrag → Abschluss → Storno).
# Der Partner liefert je Programm leichte Varianten (Paid/Approved/Confirmed);
# alle hier normalisiert, damit der Funnel eine Wahrheit und nicht vier liest.
PAID_STATUSES = ("paid", "bezahlt", "approved", "bestätigt", "bestaetigt", "confirmed")
OPEN_STATUSES = ("pending", "offen", "open", "new", "neu")
REVERSAL_STATUSES = ("declined", "abgelehnt", "reversal", "storno", "returned",
                     "cancelled", "gelöscht", "geloescht", "deleted")


def _stage_of(status):
    """Roh-Status → eine der vier Trichter-Stufen (pending/approved/declined/unknown)."""
    s = str(status or "").strip().lower()
    if s in PAID_STATUSES:
        return "approved"
    if s in OPEN_STATUSES:
        return "pending"
    if s in REVERSAL_STATUSES:
        return "declined"
    return "unknown"


def _read_submap():
    """Liest data/subid_map.yaml {subid: artikel_slug}."""
    out = {}
    if not os.path.exists(SUBMAP):
        return out
    try:
        import yaml as _yaml
        data = _yaml.safe_load(open(SUBMAP, encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return out
    mapping = data.get("mapping") or data.get("subids") or data
    for k, v in mapping.items():
        # v kann str (slug) oder dict {slug: ...}
        if isinstance(v, dict):
            out[str(k)] = str(v.get("slug") or "")
        else:
            out[str(k)] = str(v)
    return out


def _read_transactions(path):
    """Liest den Awin-Transaktions-CSV. Gibt Liste von Dicts zurück.
    Felder-Normalisierung: Erkennt übliche Spaltennamen (Case-insensitive)."""
    path = Path(path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for rec in reader:
                d = {}
                for k, v in rec.items():
                    if v is None:
                        continue
                    kk = (k or "").strip().lower()
                    v = v.strip()
                    if kk in ("transaction id", "transaction_id", "transid"):
                        d["transaction_id"] = v
                    elif kk in ("click reference", "click_reference", "subid", "sub_id", "clickref"):
                        d["subid"] = v
                    elif kk in ("commission", "commission amount", "commission_amount"):
                        d["commission"] = v
                    elif kk in ("order value", "sale amount", "sale_value", "order_value"):
                        d["order_value"] = v
                    elif kk in ("commission status", "commission_status", "status"):
                        d["status"] = v
                    elif kk in ("currency", "currency code", "currency_code"):
                        d["currency"] = v
                    elif kk in ("programme", "program", "programme name"):
                        d["programme"] = v
                    elif kk in ("transaction date", "transaction_date", "date"):
                        d["date"] = v
                    elif kk in ("device", "cookie"):
                        d["device"] = v
                if d.get("transaction_id") or d.get("subid") or d.get("commission"):
                    rows.append(d)
            return rows
    except (OSError, csv.Error) as exc:
        print(f"⚠ Awin-CSV nicht lesbar: {exc}")
        return []


def _to_float(s):
    """Wandelt einen Geldbetrag (deutsch '12,50' oder englisch '12.50') in float.
    Erkennt das Format an der Trennstelle: Komma = deutsch (Punkt = Tausender),
    Punkt = englisch (Komma = Tausender). Ohne Trennzeichen = schlichter float."""
    s = str(s or "").strip()
    if not s:
        return 0.0
    s = s.replace("\u00a0", "").replace(" ", "").replace("€", "").replace(",00", "")
    try:
        if "," in s:
            # deutsches Format: '1.234,56'
            s = s.replace(".", "").replace(",", ".")
        elif s.count(".") > 1:
            # mehrere Punkte = Tausendertrennung (1.234.56 -> 1234.56)
            s = s.replace(".", "")
        # sonst: Punkt als Dezimaltrenner (englisch) bleibt
        return float(s)
    except ValueError:
        try:
            return float(re.sub(r"[^\d.\-]", "", s.replace(",", ".")))
        except ValueError:
            return 0.0


def _aggregate(rows, submap):
    """Aggregiert Provisionen pro Artikel (SubID) und Pillar/Programme.

    Rückgabe zusätzlich `status_totals`: Status → {count, commission}. Das ist
    der Rohstoff des Trichters (`revenue_funnel.py`): pending = Antrag gestellt,
    approved = Abschluss bestätigt, declined = Storno. Awin-Status-Vokabular
    wird dabei auf die vier Trichter-Stufen normalisiert."""
    per_subid = {}
    per_programme = {}
    per_status = {}
    total = 0.0
    total_paid = 0.0
    unmatched = set()
    for r in rows:
        subid = str(r.get("subid") or "").strip()
        commission = _to_float(r.get("commission"))
        order_value = _to_float(r.get("order_value"))
        status = (r.get("status") or "Unbekannt").strip()
        programme = (r.get("programme") or "Unbekannt").strip()
        total += commission
        if status.lower() in PAID_STATUSES:
            total_paid += commission
        stage = _stage_of(status)
        d = per_status.setdefault(stage, {"count": 0, "commission": 0.0})
        d["count"] += 1
        d["commission"] = round(d["commission"] + commission, 2)
        per_programme.setdefault(programme, {"commission": 0, "orders": 0, "status": {}})
        per_programme[programme]["commission"] += commission
        per_programme[programme]["orders"] += 1
        per_programme[programme]["status"][status] = per_programme[programme]["status"].get(status, 0) + 1
        # Artikel-Zuordnung über SubID
        article = submap.get(subid, "").strip()
        if not article:
            # SubID = Slug direkt? (Fallback)
            if _slug_exists(subid):
                article = subid
            elif _pillar_target(subid):
                # Layout-CTAs (Pillar/Start): Ziel exists, aber kein posts/Slug
                article = _pillar_target(subid)
            else:
                unmatched.add(subid)
        key = article or ("subid:" + subid)
        per_subid.setdefault(key, {"subid": subid, "article": article,
                                   "commission": 0, "orders": 0, "status": {}})
        per_subid[key]["commission"] += commission
        per_subid[key]["orders"] += 1
        per_subid[key]["status"][status] = per_subid[key]["status"].get(status, 0) + 1
    return per_subid, per_programme, per_status, total, total_paid, unmatched


def _slug_exists(slug):
    return os.path.exists(os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")) or \
           os.path.exists(os.path.join(BLOG_DIR, "content", "posts", slug + ".md"))


def _pillar_target(subid):
    """SubIDs, die von Layout-CTAs stammen (Pillar-Ratgeber, Ratgeber-Zentrale,
    Startseite): hier aufgelöst statt als „unmatched“ verloren zu gehen.
    Erzeugt werden sie identisch in render-link.html/affiliate_anchor_attrs.html."""
    if not subid:
        return ""
    if subid == "home":
        return "home"
    if subid == "pillar-index":
        return "pillar/_index"
    if os.path.exists(os.path.join(BLOG_DIR, "content", "pillar", subid, "index.md")):
        return f"pillar:{subid}"
    return ""


def _pillar_of(slug):
    # Layout-SubIDs: „pillar:<key>“ trägt die Pillar bereits in sich.
    if slug.startswith("pillar:"):
        return slug.split(":", 1)[1]
    path = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
    if not os.path.exists(path):
        path = os.path.join(BLOG_DIR, "content", "posts", slug + ".md")
    try:
        t = open(path, encoding="utf-8").read()
        m = re.search(r"^pillar:\s*[\"']?([^\"'\n]+)", t, re.M)
        return m.group(1).strip().strip("'\"") if m else ""
    except OSError:
        return ""


def render(per_subid, per_programme, total, total_paid, unmatched, source, per_status=None):
    top_articles = sorted(per_subid.items(), key=lambda kv: -kv[1]["commission"])[:15]
    top_prog = sorted(per_programme.items(), key=lambda kv: -kv[1]["commission"])
    per_status = per_status or {}
    st = ", ".join(f"{k}: {v['count']} ({v['commission']:.2f} €)"
                   for k, v in sorted(per_status.items(),
                                      key=lambda kv: -kv[1]["count"])) or "keine"
    lines = [
        "# 💶 Awin-Provisions-Import (Klicks → Umsatz)",
        f"**Stand:** {TODAY.isoformat()} · **Quelle:** {source}",
        "",
        f"- **Gesamt-Provision:** {total:.2f} € "
        f"({total_paid:.2f} € bezahlt) · **Status:** {len(per_subid)} Artikel/SubIDs · "
        f"**Programme:** {len(per_programme)}",
        f"- **Trichter-Status:** {st}",
        "",
        "## 🏆 Umsatz pro Artikel (SubID→Artikel)",
        "",
        "| Artikel | Provision (€) | Aufträge | Status | Pillar |",
        "|---|---|---|---|---|",
    ]
    for key, d in top_articles:
        article = d.get("article") or ""
        pillar = _pillar_of(article)
        status = ", ".join(f"{k}: {v}" for k, v in d["status"].items())[:30]
        lines.append(f"| {article or d['subid']} | {d['commission']:.2f} | {d['orders']} | "
                     f"{status} | {pillar or '-'} |")
    lines += ["", "## 📊 Programme", "", "| Programm | Provision (€) | Aufträge |",
              "|---|---|---|"]
    for p, d in top_prog:
        lines.append(f"| {p} | {d['commission']:.2f} | {d['orders']} |")
    lines += ["", "## ⚠️ Nicht zugeordnete SubIDs", "",
              f"_Es wurden {len(unmatched)} SubIDs von keinem Artikel erkannt._"]
    if unmatched:
        lines += ["- " + ", ".join(sorted(list(unmatched))[:25]) +
                  (" …" if len(unmatched) > 25 else "")]
    lines += ["", "## 🎯 Empfehlung (Affiliate-Manager)", "",
              "1. **Umsatz-Maschinen stärken:** Artikel mit höchster Provision sind die",
              "   Geld-Lieferanten – dort mehr CTA/Tiefe/Anreize.",
              "2. **SubID-Lücken schließen:** Nicht zugeordnete SubIDs deuten auf",
              "   fehlende/abweichende SubID im Link (siehe `data/subid_map.yaml`).",
              "3. **Status pflegen:** Bezahlte vs. unbezahlte Provisionen getrennt",
              "   auswerten (Kasseneingang vs. offen).",
              "",
              f"_Erzeugt von `scripts/awin_provisions.py` am {TODAY.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"


def _selftest():
    failures = []
    # _to_float deutsche + englische Formate
    if abs(_to_float("12,50") - 12.50) > 0.001:
        failures.append(f"_to_float dt: {_to_float('12,50')}")
    if abs(_to_float("12.50") - 12.50) > 0.001:
        failures.append(f"_to_float en: {_to_float('12.50')}")
    if _to_float("") != 0:
        failures.append("_to_float leer")
    # _slug_exists
    if not _slug_exists("2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen"):
        failures.append("_slug_exists echtes Artikel")
    if _slug_exists("gibts-nicht"):
        failures.append("_slug_exists falsch-positiv")
    # Aggregation mit Test-Rows
    rows = [
        {"subid": "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen",
         "commission": "15,00", "status": "Paid", "programme": "CHECK24", "currency": "EUR"},
        {"subid": "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen",
         "commission": "7,50", "status": "Pending", "programme": "CHECK24", "currency": "EUR"},
        {"subid": "unbekannt-xyz", "commission": "3,00", "status": "Paid",
         "programme": "Tarifcheck", "currency": "EUR"},
    ]
    per_subid, per_prog, _st, total, total_paid, unmatched = _aggregate(rows, {})
    if abs(total - 25.50) > 0.01:
        failures.append(f"total: {total}")
    if abs(total_paid - 18.00) > 0.01:
        failures.append(f"paid: {total_paid}")
    if "unbekannt-xyz" in unmatched:
        pass
    else:
        failures.append("unmatched fehlt")
    k = "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen"
    if abs(per_subid[k]["commission"] - 22.50) > 0.01:
        failures.append(f"artikel commission: {per_subid[k]['commission']}")
    if per_subid[k]["orders"] != 2:
        failures.append(f"artikel orders: {per_subid[k]['orders']}")
    # Trichter-Stufen: Partner-Vokababel wird auf pending/approved/declined normalisiert
    for raw, want in (("Paid", "approved"), ("Approved", "approved"), ("Confirmed", "approved"),
                      ("Pending", "pending"), ("Declined", "declined"), ("Reversal", "declined"),
                      ("Gelöscht", "declined"), ("irgendwas", "unknown"), ("", "unknown")):
        if _stage_of(raw) != want:
            failures.append(f"_stage_of({raw!r}) = {_stage_of(raw)}, erwartet {want}")
    st_tot = _aggregate(rows, {})[2]
    if st_tot.get("approved", {}).get("count") != 2 or st_tot.get("pending", {}).get("count") != 1:
        failures.append(f"status_totals zählt die Trichter-Stufen falsch: {st_tot}")
    if abs(st_tot["approved"]["commission"] - 18.0) > 0.01:
        failures.append(f"status_totals Kommission approved: {st_tot['approved']}")
    # Pillar-Fallback: SubID aus Layout-CTA (Pillar-Ordner existiert) ≠ „unmatched“
    prow = [{"subid": "strom-sparen", "commission": "20,00", "status": "Approved",
             "programme": "CHECK24"}]
    psub, _pp, _ps, _pt, _ppl, punm = _aggregate(prow, {})
    if "pillar:strom-sparen" not in psub or punm:
        failures.append(f"Pillar-SubID nicht aufgelöst: {list(psub)} unmatched={sorted(punm)}")
    if _pillar_of("pillar:strom-sparen") != "strom-sparen":
        failures.append("_pillar_of ignoriert pillar:-Präfix")
    rep = render(psub, {"CHECK24": {"commission": 20.0, "orders": 1}}, 20.0, 20.0, set(),
                 "test", {"approved": {"count": 1, "commission": 20.0}})
    if "Trichter-Status" not in rep:
        failures.append("Report zeigt keine Trichter-Statuszeile")
    if failures:
        print("❌ AWIN-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ AWIN-SELFTEST bestanden (Geldformat, Slug-Erkennung, Aggregation, Unmatched).")
    return 0


def gen_subid_map():
    """Erzeugt data/subid_map.yaml aus Artikeln UND Layout-CTA-Stellen.

    Neu (Premium-Messkette 19.09.2026): Startseiten- und Pillar-CTAs tragen
    jetzt eigene SubIDs (`home`, `pillar-index`, Pillar-Slug). Ohne Mapping
    landeten diese Transaktionen als „unmatched“ – genau die Umsatz-Lücke,
    die der Trichter schließen soll. Hier werden sie dokumentiert zugeordnet."""
    posts = sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md"))) + \
            sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*.md")))
    lines = [
        "# SubID → Artikel-Zuordnung (Awin 'Click Reference' = Artikel-Slug).",
        f"# Generiert: {TODAY.isoformat()}",
        "# Tragt hier manuelle Abweichungen ein (falls SubID != Slug).",
        "# `pillar:<key>` = Provisionen, die ein Pillar-Ratgeber erwirtschaftet;",
        "# `home` / `pillar/_index` = CTA-Stellen Startseiten- bzw. Ratgeber-Zentrale.",
        "",
        "mapping:",
    ]
    count = 0
    for p in posts:
        if p.endswith("_index.md"):
            continue
        slug = os.path.basename(os.path.dirname(p)) if os.path.basename(p) == "index.md" \
            else os.path.basename(p)[:-3]
        lines.append(f'  "{slug}": "{slug}"')
        count += 1
    pillars = sorted(glob.glob(os.path.join(BLOG_DIR, "content", "pillar", "*", "index.md")))
    for p in pillars:
        slug = os.path.basename(os.path.dirname(p))
        lines.append(f'  "{slug}": "pillar:{slug}"')
        count += 1
    lines.append('  "home": "home"')
    lines.append('  "pillar-index": "pillar/_index"')
    Path(SUBMAP).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ SubID-Mapping erzeugt: {SUBMAP} ({count} Seiten/Platzierungen)")
    return count


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    if "--gen-subid-map" in sys.argv:
        return 0 if gen_subid_map() else 1
    csv_path = DEFAULT_CSV
    source = "data/awin_transactions.csv"
    for i, arg in enumerate(sys.argv):
        if arg == "--awin-csv" and i + 1 < len(sys.argv):
            csv_path = sys.argv[i + 1]
            source = csv_path
    rows = _read_transactions(csv_path)
    if not rows:
        Path(REPORT).write_text(
            f"# 💶 Awin-Provisions-Import\n\n**Stand:** {TODAY.isoformat()}\n\n"
            f"_Keine Transaktionen gefunden in {csv_path}. Export: Awin-Dashboard → "
            "Reports → Transactions (CSV) und nach `data/awin_transactions.csv` "
            "legen (oder `--awin-csv <pfad>`)._\n", encoding="utf-8")
        print(f"ℹ️ Keine Awin-Daten unter {source}")
        return 0
    submap = _read_submap()
    per_subid, per_prog, per_status, total, total_paid, unmatched = _aggregate(rows, submap)
    report = render(per_subid, per_prog, total, total_paid, unmatched, source, per_status)
    Path(REPORT).write_text(report, encoding="utf-8")
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    with open(STATS, "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY.isoformat(),
            "total_commission": round(total, 2),
            "total_paid": round(total_paid, 2),
            "transactions": sum(int(d.get("count") or 0) for d in per_status.values()),
            # Trichter-Stufen je Status-Aggregat: Rohstoff für revenue_funnel.py
            # (Antrag=pending+approved+declined, bestätigt=approved, Storno=declined).
            "status_totals": {k: {"count": int(v["count"]),
                                  "commission": round(float(v["commission"]), 2)}
                              for k, v in per_status.items()},
            "articles": {k: {"commission": round(v["commission"], 2),
                             "orders": v["orders"],
                             "subid": v.get("subid", "")}
                         for k, v in per_subid.items()},
            "programmes": {k: {"commission": round(v["commission"], 2),
                               "orders": v["orders"]} for k, v in per_prog.items()},
            "unmatched": len(unmatched),
        }, f, ensure_ascii=False, indent=2)
    print(report)
    return 1 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
