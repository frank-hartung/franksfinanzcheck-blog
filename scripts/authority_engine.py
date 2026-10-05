#!/usr/bin/env python3
"""Authority Engine: Quartals-Asset-Gate, Evidenzregister und KPI-Radar.

Automatisiert Nachweis und Takt – niemals Outreach oder Behauptungen.

  python3 scripts/authority_engine.py --check
  python3 scripts/authority_engine.py --as-of 2027-02-16
  python3 scripts/authority_engine.py --import-gsc export.csv --period 2026-10
  python3 scripts/authority_engine.py --import-audience aggregate.json --period 2026-10
  python3 scripts/authority_engine.py --selftest

GSC-Importe werden ausschließlich als Aggregate unter
``data/authority_measurements/`` gespeichert. Suchanfragen bleiben draußen.
Exit 0 = Vertrag erfüllt, 1 = Handlungsbedarf, 2 = ungültige Daten.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml fehlt: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / "data/authority_strategy.yaml"
EVIDENCE = ROOT / "data/authority_evidence.yaml"
MEASUREMENTS = ROOT / "data/authority_measurements"
REPORT = ROOT / "AUTHORITY-RADAR.md"
BRAND_RE = re.compile(r"franks?\s*finanzcheck|frank\s+hartung", re.I)
VALID_EVIDENCE = {"editorial_link", "media_mention", "interview", "cooperation"}
VALID_SOURCES = {"google-search-console-csv", "first-party-audience-aggregate"}
RATE_KEYS = {"newsletter_click_rate", "returning_reader_rate", "conversion_rate"}
PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def valid_period(value):
    return bool(PERIOD_RE.fullmatch(str(value or "")))


def atomic_json_write(path, payload):
    """Replace a measurement atomically so a cancelled run cannot leave half JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_date(value):
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def quarter_for(day):
    return f"{day.year}-Q{((day.month - 1) // 3) + 1}"


def load_yaml(path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def local_path(url):
    return ROOT / "static" / str(url or "").lstrip("/") if str(url).startswith("/downloads/") else None


def content_path(canonical):
    slug = str(canonical or "").strip("/")
    return ROOT / "content" / slug / "index.md"


def validate(strategy, evidence):
    errors = []
    quarters = strategy.get("quarters") or []
    assets = strategy.get("assets") or []
    asset_by_id = {a.get("id"): a for a in assets}
    qids = [q.get("quarter") for q in quarters]
    if len(qids) != len(set(qids)):
        errors.append("Quartale sind doppelt vergeben.")
    minimum = int((strategy.get("meta") or {}).get("minimum_linkable_assets_per_quarter") or 0)
    if minimum < 1:
        errors.append("minimum_linkable_assets_per_quarter muss mindestens 1 sein.")
    for q in quarters:
        aid = q.get("asset_id")
        if not aid:
            errors.append(f"{q.get('quarter', '?')}: asset_id fehlt.")
        if q.get("status") == "live" and aid not in asset_by_id:
            errors.append(f"{q.get('quarter')}: Live-Asset {aid} fehlt im Assetregister.")
    for a in assets:
        aid = a.get("id") or "?"
        if a.get("status") != "live":
            continue
        for field in ("canonical", "methodology", "dataset", "press_asset", "published"):
            if not a.get(field):
                errors.append(f"{aid}: Pflichtfeld {field} fehlt.")
        if not a.get("source_urls") or len(a["source_urls"]) < 2:
            errors.append(f"{aid}: mindestens zwei transparente Quellen-URLs nötig.")
        if a.get("canonical") and not content_path(a["canonical"]).exists():
            errors.append(f"{aid}: Inhaltsseite fehlt: {content_path(a['canonical']).relative_to(ROOT)}")
        for field in ("dataset", "press_asset"):
            p = local_path(a.get(field))
            if p and not p.exists():
                errors.append(f"{aid}: Datei fehlt: {p.relative_to(ROOT)}")
    evidence_items = evidence.get("evidence") or []
    evidence_ids = [item.get("id") for item in evidence_items]
    if any(not ident for ident in evidence_ids):
        errors.append("Jeder Evidenzbeleg braucht eine id.")
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("Evidenz-IDs sind doppelt vergeben.")
    for item in evidence_items:
        ident = item.get("id") or "Evidenz ohne id"
        if item.get("kind") not in VALID_EVIDENCE:
            errors.append(f"{ident}: ungültiger kind-Wert.")
        url = str(item.get("url") or "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{ident}: öffentliche https-URL fehlt.")
        if any(key.lower().startswith(("utm_", "fbclid", "gclid")) for key in
               (part.split("=", 1)[0] for part in parsed.query.split("&") if part)):
            errors.append(f"{ident}: Beleg-URL enthält Tracking-Parameter.")
        if not parse_date(item.get("published")):
            errors.append(f"{ident}: published-Datum fehlt/ungültig.")
    # Belegte Zahlen dürfen nie ohne Evidenz existieren.
    for period in (strategy.get("measurement") or {}).get("periods") or []:
        numeric = [k for k, v in period.items() if k not in {"period", "status", "updated", "evidence"} and v is not None]
        if numeric and not period.get("evidence"):
            errors.append(f"Messperiode {period.get('period')}: Werte ohne Evidenz/Importbeleg.")
    return errors


def load_measurements():
    out = []
    if not MEASUREMENTS.exists():
        return out
    for path in sorted(MEASUREMENTS.glob("*.json")):
        try:
            display_path = str(path.relative_to(ROOT))
        except ValueError:
            display_path = str(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_file"] = display_path
            out.append(data)
        except (OSError, json.JSONDecodeError):
            out.append({"_file": display_path, "invalid": True})
    return out


def validate_measurements(measurements):
    """Validate persisted aggregates independently of the import path."""
    errors, seen = [], set()
    for item in measurements:
        name = item.get("_file", "unbekannte Datei")
        if item.get("invalid"):
            errors.append(f"{name}: ungültiges JSON.")
            continue
        period, source = item.get("period"), item.get("source")
        if item.get("schema") != 1:
            errors.append(f"{name}: nicht unterstütztes Schema.")
        if not valid_period(period):
            errors.append(f"{name}: period muss YYYY-MM und ein echter Monat sein.")
        if source not in VALID_SOURCES:
            errors.append(f"{name}: unbekannte Quelle {source!r}.")
        key = (period, source)
        if key in seen:
            errors.append(f"{name}: Quelle/Periode {source}/{period} ist doppelt.")
        seen.add(key)
        if not parse_date(item.get("imported")):
            errors.append(f"{name}: imported-Datum fehlt/ungültig.")
        if source == "google-search-console-csv":
            values = item.get("gsc")
            if not isinstance(values, dict):
                errors.append(f"{name}: gsc-Aggregat fehlt.")
                continue
            for field in ("clicks", "impressions", "brand_clicks", "brand_impressions"):
                value = values.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    errors.append(f"{name}: {field} muss eine nichtnegative Zahl sein.")
            if isinstance(values.get("clicks"), (int, float)) and isinstance(values.get("impressions"), (int, float)) and values["clicks"] > values["impressions"]:
                errors.append(f"{name}: Klicks dürfen Impressionen nicht übersteigen.")
        elif source == "first-party-audience-aggregate":
            values = item.get("metrics")
            if not isinstance(values, dict) or not values:
                errors.append(f"{name}: metrics-Aggregat fehlt.")
                continue
            if not item.get("provenance"):
                errors.append(f"{name}: provenance fehlt.")
            for field, value in values.items():
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    errors.append(f"{name}: {field} muss eine nichtnegative Zahl sein.")
                elif field in RATE_KEYS and value > 1:
                    errors.append(f"{name}: {field} muss zwischen 0 und 1 liegen.")
    return errors


def evaluate(strategy, evidence, as_of):
    current_q = quarter_for(as_of)
    actions = []
    qmap = {q.get("quarter"): q for q in strategy.get("quarters") or []}
    current = qmap.get(current_q)
    if not current:
        actions.append(("P1", f"Für {current_q} fehlt ein Quartals-Asset im Plan."))
    elif current.get("status") != "live":
        due = parse_date(current.get("release_due"))
        priority = "P1" if due and as_of > due else "P2"
        actions.append((priority, f"Quartals-Asset {current.get('asset_id')} ist {current.get('status')}, nicht live."))
    for q in strategy.get("quarters") or []:
        due = parse_date(q.get("release_due"))
        if q.get("status") != "live" and due and as_of > due:
            actions.append(("P1", f"Release überfällig: {q.get('quarter')} / {q.get('asset_id')} ({due})."))
    for a in strategy.get("assets") or []:
        if a.get("status") != "live":
            continue
        published = parse_date(a.get("published"))
        refresh = int(a.get("refresh_days") or 90)
        if published and (as_of - published).days > refresh:
            actions.append(("P1", f"Asset-Refresh fällig: {a.get('title')} (älter als {refresh} Tage)."))
    measurements = load_measurements()
    month = as_of.strftime("%Y-%m")
    current_measurements = [m for m in measurements if m.get("period") == month and not m.get("invalid")]
    if not any(m.get("source") == "google-search-console-csv" for m in current_measurements):
        actions.append(("P2", f"Für {month} fehlt der aggregierte GSC-Import (inklusive Markensuche)."))
    if not any(m.get("source") == "first-party-audience-aggregate" for m in current_measurements):
        actions.append(("P2", f"Für {month} fehlen Newsletter-, Retention- und Conversion-Aggregate."))
    evidence_count = len(evidence.get("evidence") or [])
    return current_q, actions, measurements, evidence_count


def num(value):
    text = str(value or "0").strip().replace(" ", "").replace("%", "")
    # Google-Exporte können 1.234,5 oder 1,234.5 verwenden.
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text or 0)


def import_gsc(path, period):
    if not valid_period(period):
        raise ValueError("Periode muss YYYY-MM und ein echter Monat sein.")
    raw = Path(path).read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",;\t")
    rows = list(csv.DictReader(raw.splitlines(), dialect=dialect))
    if not rows:
        raise ValueError("GSC-Datei enthält keine Zeilen.")
    aliases = {
        "query": ("Top queries", "Query", "Suchanfragen", "Suchanfrage"),
        "clicks": ("Clicks", "Klicks"),
        "impressions": ("Impressions", "Impressionen"),
    }
    headers = rows[0].keys()
    fields = {}
    for key, names in aliases.items():
        fields[key] = next((h for h in headers if h.strip() in names), None)
    if not fields["clicks"] or not fields["impressions"]:
        raise ValueError("Spalten Klicks/Clicks und Impressionen/Impressions fehlen.")
    clicks = impressions = brand_clicks = brand_impressions = 0.0
    for row in rows:
        c, i = num(row.get(fields["clicks"])), num(row.get(fields["impressions"]))
        if c < 0 or i < 0 or c > i:
            raise ValueError("GSC-Werte müssen nichtnegativ sein; Klicks dürfen Impressionen nicht übersteigen.")
        clicks += c; impressions += i
        if fields["query"] and BRAND_RE.search(row.get(fields["query"]) or ""):
            brand_clicks += c; brand_impressions += i
    payload = {
        "schema": 1, "period": period, "source": "google-search-console-csv",
        "imported": dt.date.today().isoformat(), "rows_aggregated": len(rows),
        "gsc": {"clicks": round(clicks), "impressions": round(impressions),
                "ctr": round(clicks / impressions, 6) if impressions else None,
                "brand_clicks": round(brand_clicks), "brand_impressions": round(brand_impressions)},
        "privacy": "Nur Aggregate; Suchanfragen wurden nicht gespeichert."
    }
    target = MEASUREMENTS / f"{period}-gsc.json"
    atomic_json_write(target, payload)
    return target


def import_audience(path, period):
    """Importiert bereits aggregierte First-Party-KPIs, nie Empfängerdaten."""
    if not valid_period(period):
        raise ValueError("Periode muss YYYY-MM und ein echter Monat sein.")
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed = {
        "newsletter_subscribers", "newsletter_click_rate",
        "returning_reader_rate", "conversions", "conversion_rate",
    }
    metrics = {key: raw[key] for key in allowed if raw.get(key) is not None}
    if not metrics:
        raise ValueError("Keine erlaubte Audience-Kennzahl vorhanden.")
    if not raw.get("provenance"):
        raise ValueError("provenance (Export-/Dashboard-Beleg) fehlt.")
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in metrics.values()):
        raise ValueError("Audience-Kennzahlen müssen Zahlen sein.")
    if any(value < 0 for value in metrics.values()):
        raise ValueError("Audience-Kennzahlen dürfen nicht negativ sein.")
    if any(metrics[key] > 1 for key in RATE_KEYS & metrics.keys()):
        raise ValueError("Audience-Raten müssen als Anteil zwischen 0 und 1 vorliegen.")
    payload = {
        "schema": 1, "period": period, "source": "first-party-audience-aggregate",
        "imported": dt.date.today().isoformat(), "metrics": metrics,
        "provenance": str(raw["provenance"]),
        "privacy": "Nur Aggregate; keine E-Mail-Adressen, IDs oder Ereigniszeilen."
    }
    target = MEASUREMENTS / f"{period}-audience.json"
    atomic_json_write(target, payload)
    return target


def write_report(strategy, evidence, as_of, quarter, actions, measurements):
    counts = {k: 0 for k in VALID_EVIDENCE}
    for item in evidence.get("evidence") or []:
        if item.get("kind") in counts:
            counts[item["kind"]] += 1
    lines = [f"# Authority-Radar – {as_of.isoformat()}", "",
        "> Belegt externe Autorität, Distribution und Audience-Kennzahlen. Unbekannt bleibt unbekannt: `null` ist niemals `0`.", "",
        f"**Aktuelles Quartal:** {quarter} · **Messimporte:** {len(measurements)}", "",
        "## Handlungsqueue", ""]
    if actions:
        lines += [f"- **{prio}:** {text}" for prio, text in actions]
    else:
        lines.append("- Keine fällige Maßnahme.")
    lines += ["", "## Belegte externe Signale", "", "| Signal | Anzahl |", "|---|---:|",
        f"| Redaktionelle Links | {counts['editorial_link']} |",
        f"| Mediennennungen | {counts['media_mention']} |",
        f"| Experteninterviews | {counts['interview']} |",
        f"| Aktive Kooperationen | {counts['cooperation']} |", "",
        "## Nachweisregister", ""]
    evidence_items = evidence.get("evidence") or []
    if evidence_items:
        lines += ["| Datum | Typ | Nachweis |", "|---|---|---|"]
        for item in sorted(evidence_items, key=lambda value: str(value.get("published", "")), reverse=True):
            label = str(item.get("title") or item.get("publisher") or item.get("id")).replace("|", "\\|")
            lines.append(f"| {item.get('published')} | {item.get('kind')} | [{label}]({item.get('url')}) |")
    else:
        lines.append("_Keine externe Autorität behauptet: Im Evidenzregister liegt noch kein prüfbarer Beleg._")
    lines += ["", "## Quartalsprogramm", "", "| Quartal | Asset | Status/Termin |", "|---|---|---|"]
    for q in strategy.get("quarters") or []:
        timing = q.get("release") or q.get("release_due") or "–"
        lines.append(f"| {q.get('quarter')} | `{q.get('asset_id')}` | {q.get('status')} · {timing} |")
    lines += ["", "## Messdaten", ""]
    if not measurements:
        lines.append("_Noch kein belegter Import. GSC, Newsletter, Conversion und Retention werden daher nicht behauptet._")
    for m in measurements:
        lines.append(f"- **{m.get('period', '?')}** · {m.get('source', 'unbekannt')} · `{m.get('_file')}`")
    lines += ["", "## Betriebsregel", "",
        "Ein Asset ist erst live, wenn Inhaltsseite, Methodik, Rohdaten/CSV, Quellen und Presseformat vorhanden sind. Outreach bleibt menschlich; der Radar versendet nichts.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def selftest():
    assert quarter_for(dt.date(2026, 10, 2)) == "2026-Q4"
    assert quarter_for(dt.date(2027, 3, 31)) == "2027-Q1"
    assert BRAND_RE.search("Franks Finanzcheck")
    assert not BRAND_RE.search("strom sparen")
    assert abs(num("1.234,5") - 1234.5) < 0.01
    print("Authority Engine: Selbsttest grün")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--as-of")
    p.add_argument("--import-gsc")
    p.add_argument("--import-audience")
    p.add_argument("--period")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)
    if args.selftest:
        selftest(); return 0
    if args.import_gsc or args.import_audience:
        if not valid_period(args.period):
            print("Import braucht --period YYYY-MM mit echtem Monat", file=sys.stderr); return 2
        try:
            if args.import_gsc:
                target = import_gsc(args.import_gsc, args.period)
                print(f"GSC aggregiert: {target.relative_to(ROOT)}")
            if args.import_audience:
                target = import_audience(args.import_audience, args.period)
                print(f"Audience aggregiert: {target.relative_to(ROOT)}")
        except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
            print(f"Importfehler: {exc}", file=sys.stderr); return 2
    strategy, evidence = load_yaml(STRATEGY), load_yaml(EVIDENCE)
    errors = validate(strategy, evidence)
    errors += validate_measurements(load_measurements())
    if errors:
        print("\n".join(f"FEHLER: {e}" for e in errors), file=sys.stderr); return 2
    as_of = parse_date(args.as_of) if args.as_of else dt.date.today()
    if not as_of:
        print("--as-of muss YYYY-MM-DD sein", file=sys.stderr); return 2
    quarter, actions, measurements, _ = evaluate(strategy, evidence, as_of)
    write_report(strategy, evidence, as_of, quarter, actions, measurements)
    print(f"Authority-Radar: {len(actions)} Maßnahme(n), {REPORT.relative_to(ROOT)}")
    return 1 if actions else 0


if __name__ == "__main__":
    sys.exit(main())
