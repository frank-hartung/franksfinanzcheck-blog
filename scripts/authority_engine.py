#!/usr/bin/env python3
"""Authority Engine: Quartals-Asset-Gate, Messlage und Autoritäts-Radar.

Automatisiert Nachweis und Takt – niemals Outreach oder Behauptungen.

  python3 scripts/authority_engine.py --check
  python3 scripts/authority_engine.py --as-of 2026-11-05
  python3 scripts/authority_engine.py --import-gsc export.csv --period 2026-10
  python3 scripts/authority_engine.py --import-audience aggregate.json --period 2026-10
  python3 scripts/authority_engine.py --template > /tmp/audience-2026-10.json
  python3 scripts/authority_engine.py --json /tmp/radar.json
  python3 scripts/authority_engine.py --selftest

WARUM „MESSLAGE“ UND NICHT NUR „IMPORT“ (05.11.2026, #1076)
-----------------------------------------------------------
Der Radar verlangte bis zu diesem Datum für **jeden laufenden Monat** einen
GSC-Import – an einem Tag (dem 5.), an dem der Monat noch nicht einmal vorbei
ist. Diesen Import konnte es nie geben: Google liefert finale Daten verzögert,
und der Monat selbst war noch nicht abgeschlossen. Die Folge war ein
Dauerbefund ohne Adressat, also ein Ticket, das sich nicht schließen lässt.

Gleichzeitig lagen 44 Tage echte Search-Console-Daten längst im Repo:
`data/gsc/tagesdaten.jsonl`, täglich geschrieben von `scripts/gsc_import.py`.
Der Radar sah sie nicht, weil er auf einem zweiten, manuell zu füllenden
Speicher (`data/authority_measurements/*-gsc.json`) beharrte. Zwei Wahrheiten
für dieselbe Zahl – die schlechtere gewinnt.

Seit diesem Datum gilt:

  1. **Eine Quelle pro Zahl.** GSC-Monatswerte werden aus dem Tages-Ledger
     *abgeleitet*, nicht kopiert. Ein CSV-Import bleibt als ausdrücklicher
     Vorrang möglich (nur er kennt Marken-Suchanfragen).
  2. **Berichtsmonat statt Kalendermonat.** Gemessen wird der letzte
     abgeschlossene Monat (Verzögerung aus dem Vertrag). Der laufende Monat
     wird gezeigt, aber nie eingefordert.
  3. **Jeder KPI hat einen Modus.** `automatisch` (ableitbar), `manuell`
     (monatlicher Export, mit Fälligkeit), `nicht_messbar`/`nicht_aktiv`
     (bewusste Entscheidung mit Grund und Datum). Was nicht messbar ist,
     wird nicht eingefordert – und nie als `0` behauptet.
  4. **`null` ist niemals `0`.** Im Report steht `—` für unbekannt und `0`
     nur für gemessen-null.

Exit 0 = Vertrag erfüllt, 1 = Handlungsbedarf, 2 = ungültige Daten.
"""
from __future__ import annotations

import argparse
import calendar
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

# Die eine Quelle für Reichweite: der Tages-Ledger des GSC-Imports.
GSC_DIR = ROOT / "data/gsc"
GSC_LEDGER = GSC_DIR / "tagesdaten.jsonl"
GSC_META = GSC_DIR / "meta.json"
GSC_QUERIES = GSC_DIR / "top_suchbegriffe_28t.json"

# Menschlicher Teil der Distribution: Vorlagen, nie automatischer Versand.
OUTREACH = ROOT / "docs/outreach"

# Signale dafür, dass ein als „nicht aktiv“ geführter Kanal Messdaten liefert.
KLICKMESSUNG = ROOT / "data/klickmessung.yaml"
PROVISIONEN_AGGREGAT = ROOT / "data/provisionen_aggregat.json"

BRAND_RE = re.compile(r"franks?\s*finanzcheck|frank\s+hartung", re.I)
VALID_EVIDENCE = {"editorial_link", "media_mention", "interview", "cooperation"}
EVIDENCE_LABEL = {
    "editorial_link": "Redaktioneller Link",
    "media_mention": "Mediennennung",
    "interview": "Experteninterview",
    "cooperation": "Kooperation",
}
VALID_SOURCES = {"google-search-console-csv", "first-party-audience-aggregate"}
GSC_KEYS = ("clicks", "impressions", "brand_clicks", "brand_impressions")
RATE_KEYS = {"newsletter_click_rate", "returning_reader_rate", "conversion_rate"}
AUDIENCE_KEYS = {
    "newsletter_subscribers", "newsletter_click_rate",
    "returning_reader_rate", "conversions", "conversion_rate",
}
# Kennzahlen, die eine Messperiode im Vertrag erklären darf.
PERIOD_VALUE_KEYS = AUDIENCE_KEYS | {
    "gsc_clicks", "gsc_impressions", "gsc_brand_clicks",
    "editorial_links", "media_mentions", "expert_interviews", "active_cooperations",
}
PERIOD_STATUS = {"offen", "teilweise", "belegt"}
SOURCE_MODES = {"automatisch", "manuell", "nicht_messbar", "nicht_aktiv"}
AUTO_SOURCES = {"gsc"}
# Was der Radar heute selbst ableiten kann – alles andere braucht einen Beleg.
DEFAULT_MEASUREMENT = {
    "reporting_lag_days": 4,
    "manual_due_day": 5,
    "gsc_max_age_days": 5,
    "sources": [],
}
PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
TRACKING_PREFIX = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")


# --------------------------------------------------------------------- Basis

def valid_period(value):
    return bool(PERIOD_RE.fullmatch(str(value or "")))


def period_of(day):
    return f"{day.year}-{day.month:02d}"


def parse_date(value):
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def quarter_for(day):
    return f"{day.year}-Q{((day.month - 1) // 3) + 1}"


def month_days(period):
    year, month = (int(part) for part in str(period).split("-"))
    return calendar.monthrange(year, month)[1]


def next_month(period):
    year, month = (int(part) for part in str(period).split("-"))
    return f"{year + 1}-01" if month == 12 else f"{year}-{month + 1:02d}"


def reporting_month(as_of, lag_days=4):
    """Der letzte Monat, der zum Stichtag final messbar ist.

    Der Radar läuft am 5. – der Vormonat ist dann abgeschlossen, die
    Search Console hat ihn aber erst nach ihrer Verzögerung final.
    """
    kandidat = as_of.replace(day=1) - dt.timedelta(days=1)
    if as_of.day <= int(lag_days):
        kandidat = kandidat.replace(day=1) - dt.timedelta(days=1)
    return period_of(kandidat)


def manual_due(period, due_day):
    """Fälligkeit des manuellen Exports für einen Berichtsmonat."""
    jahr, monat = (int(part) for part in str(period).split("-"))
    folge = dt.date(jahr + (monat == 12), 1 if monat == 12 else monat + 1, 1)
    return folge.replace(day=max(1, min(int(due_day), calendar.monthrange(folge.year, folge.month)[1])))


def load_yaml(path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def local_path(url):
    return ROOT / "static" / str(url or "").lstrip("/") if str(url).startswith("/downloads/") else None


def content_path(canonical):
    slug = str(canonical or "").strip("/")
    return ROOT / "content" / slug / "index.md"


def slugify(text):
    text = str(text or "").strip().lower()
    for zeichen, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(zeichen, ersatz)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def anchor_present(text, anchor):
    """Ist der Methodik-Anker wirklich in der Inhaltsseite vorhanden?

    Hugo vergibt Überschriften-IDs selbst; `{#anker}` ist die ausdrückliche
    Form. Beides wird erkannt – sonst behauptet der Vertrag einen Link,
    der ins Leere springt.
    """
    ziel = slugify(anchor)
    if not ziel:
        return False
    if re.search(r"\{#" + re.escape(str(anchor)) + r"\}", text):
        return True
    for zeile in text.splitlines():
        treffer = re.match(r"^#{1,6}\s+(.+?)\s*$", zeile)
        if treffer:
            ueberschrift = re.sub(r"\s*\{#[^}]*\}\s*$", "", treffer.group(1))
            if slugify(ueberschrift) == ziel:
                return True
    return False


def de_int(value):
    return f"{int(value):,}".replace(",", ".")


def de_quote(value):
    """Anteil (0..1) als deutsche Prozentangabe, `None` bleibt unbekannt."""
    if value is None:
        return "—"
    return f"{value * 100:.1f}".replace(".", ",") + " %"


def de_num(value):
    if value is None:
        return "—"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.2f}".replace(".", ",")
    return de_int(value)


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


# ----------------------------------------------------------- Messungen (Repo)

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


def _zahl(wert):
    return isinstance(wert, (int, float)) and not isinstance(wert, bool)


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
            for field in GSC_KEYS:
                value = values.get(field)
                if value is None:
                    continue
                if not _zahl(value) or value < 0:
                    errors.append(f"{name}: {field} muss eine nichtnegative Zahl sein.")
            klicks, impressionen = values.get("clicks"), values.get("impressions")
            if _zahl(klicks) and _zahl(impressionen) and klicks > impressionen:
                errors.append(f"{name}: Klicks dürfen Impressionen nicht übersteigen.")
            marke, marke_imp = values.get("brand_clicks"), values.get("brand_impressions")
            if _zahl(marke) and _zahl(klicks) and marke > klicks:
                errors.append(f"{name}: Marken-Klicks dürfen Gesamt-Klicks nicht übersteigen.")
            if _zahl(marke_imp) and _zahl(impressionen) and marke_imp > impressionen:
                errors.append(f"{name}: Marken-Impressionen dürfen Gesamt-Impressionen nicht übersteigen.")
        elif source == "first-party-audience-aggregate":
            values = item.get("metrics")
            if not isinstance(values, dict) or not values:
                errors.append(f"{name}: metrics-Aggregat fehlt.")
                continue
            if not str(item.get("provenance") or "").strip():
                errors.append(f"{name}: provenance fehlt.")
            for field, value in values.items():
                if field not in AUDIENCE_KEYS:
                    errors.append(f"{name}: unbekannte Kennzahl {field!r} (erlaubt: {', '.join(sorted(AUDIENCE_KEYS))}).")
                elif not _zahl(value) or value < 0:
                    errors.append(f"{name}: {field} muss eine nichtnegative Zahl sein.")
                elif field in RATE_KEYS and value > 1:
                    errors.append(f"{name}: {field} muss zwischen 0 und 1 liegen.")
    return errors


def load_gsc():
    """Liest den Tages-Ledger, den Kopf und die Top-Suchanfragen (read-only)."""
    lage = {"ledger": {}, "meta": {}, "queries": [], "errors": [], "datei": None}
    try:
        lage["datei"] = str(GSC_LEDGER.relative_to(ROOT))
    except ValueError:
        lage["datei"] = str(GSC_LEDGER)
    if GSC_LEDGER.exists():
        try:
            zeilen = GSC_LEDGER.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            lage["errors"].append(f"{lage['datei']}: nicht lesbar ({exc}).")
            zeilen = []
        for nummer, zeile in enumerate(zeilen, start=1):
            zeile = zeile.strip()
            if not zeile:
                continue
            try:
                satz = json.loads(zeile)
            except json.JSONDecodeError:
                lage["errors"].append(f"{lage['datei']}:{nummer}: ungültiges JSON.")
                continue
            tag = parse_date(satz.get("datum"))
            if not tag:
                lage["errors"].append(f"{lage['datei']}:{nummer}: datum fehlt/ungültig.")
                continue
            klicks, impressionen = satz.get("clicks"), satz.get("impressions")
            if not _zahl(klicks) or not _zahl(impressionen) or klicks < 0 or impressionen < 0:
                lage["errors"].append(f"{lage['datei']}:{nummer}: clicks/impressions müssen nichtnegative Zahlen sein.")
                continue
            if klicks > impressionen:
                lage["errors"].append(f"{lage['datei']}:{nummer}: Klicks übersteigen Impressionen.")
                continue
            lage["ledger"][tag] = {"clicks": klicks, "impressions": impressionen}
    if GSC_META.exists():
        try:
            lage["meta"] = json.loads(GSC_META.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            lage["errors"].append(f"{GSC_META.relative_to(ROOT)}: ungültiges JSON.")
    if GSC_QUERIES.exists():
        try:
            daten = json.loads(GSC_QUERIES.read_text(encoding="utf-8"))
            lage["queries"] = daten if isinstance(daten, list) else []
        except (OSError, json.JSONDecodeError):
            lage["errors"].append(f"{GSC_QUERIES.relative_to(ROOT)}: ungültiges JSON.")
    return lage


def gsc_month(ledger, period):
    """Monatsaggregat aus dem Tages-Ledger – abgeleitet, nicht kopiert."""
    tage = {tag: werte for tag, werte in ledger.items() if period_of(tag) == period}
    if not tage:
        return None
    klicks = sum(w["clicks"] for w in tage.values())
    impressionen = sum(w["impressions"] for w in tage.values())
    return {
        "period": period,
        "tage": len(tage),
        "erwartet": month_days(period),
        "clicks": int(round(klicks)),
        "impressions": int(round(impressionen)),
        "ctr": round(klicks / impressionen, 6) if impressionen else None,
        "von": min(tage).isoformat(),
        "bis": max(tage).isoformat(),
    }


def gsc_health(gsc, as_of, max_age):
    letzter = max(gsc["ledger"]) if gsc["ledger"] else None
    alter = (as_of - letzter).days if letzter else None
    status = "leer"
    if letzter:
        status = "frisch" if alter <= int(max_age) else "veraltet"
    meta = gsc.get("meta") or {}
    return {
        "letzter_tag": letzter,
        "alter_tage": alter,
        "status": status,
        "meta_status": meta.get("status"),
        "meta_grund": meta.get("grund") or "",
        "meta_stand": meta.get("stand"),
        "site": meta.get("site"),
    }


def brand_window(gsc):
    """Markensichtbarkeit im rollierenden 28-Tage-Fenster.

    Der Tages-Ledger führt keine Suchanfragen; markenscharf ist nur der
    Export aus der Search Console. Dieses Fenster ist ausdrücklich *nicht*
    monatsscharf und wird deshalb nie als Monatswert behauptet.
    """
    queries = gsc.get("queries") or []
    bis = parse_date(((gsc.get("meta") or {}).get("zeitraum") or {}).get("bis"))
    if not queries or not bis:
        return None
    vorhanden = [q for q in queries if _zahl(q.get("impressions")) and _zahl(q.get("clicks"))]
    if not vorhanden:
        return None
    marke = [q for q in vorhanden if BRAND_RE.search(str(q.get("suchbegriff") or ""))]
    impressionen = sum(q["impressions"] for q in vorhanden)
    marken_impressionen = sum(q["impressions"] for q in marke)
    return {
        "von": (bis - dt.timedelta(days=27)).isoformat(),
        "bis": bis.isoformat(),
        "abfragen": len(vorhanden),
        "marken_abfragen": len(marke),
        "clicks": int(round(sum(q["clicks"] for q in vorhanden))),
        "marken_clicks": int(round(sum(q["clicks"] for q in marke))),
        "impressionen": int(round(impressionen)),
        "marken_impressionen": int(round(marken_impressionen)),
        "anteil": (round(marken_impressionen / impressionen, 4) if impressionen else None),
        "datei": str(GSC_QUERIES.relative_to(ROOT)) if GSC_QUERIES.is_relative_to(ROOT) else str(GSC_QUERIES),
    }


# ------------------------------------------------------------------- Vertrag

def measurement_contract(strategy):
    """Normalisierte Messvertrags-Sicht mit sicheren Vorgaben."""
    roh = strategy.get("measurement") or {}
    vertrag = dict(DEFAULT_MEASUREMENT)
    vertrag.update({k: v for k, v in roh.items() if k != "sources" and v is not None})
    vertrag["sources"] = [s for s in (roh.get("sources") or []) if isinstance(s, dict)]
    return vertrag


def kpi_map(contract):
    """KPI → Quelle. Genau eine Quelle je Kennzahl."""
    zuordnung = {}
    for quelle in contract["sources"]:
        for kpi in quelle.get("kpi") or []:
            zuordnung.setdefault(kpi, []).append(quelle)
    return zuordnung


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
        if q.get("status") not in {"live", "planned"}:
            errors.append(f"{q.get('quarter')}: status muss live oder planned sein.")
        for feld in ("release", "release_due"):
            if q.get(feld) and not parse_date(q[feld]):
                errors.append(f"{q.get('quarter')}: {feld} ist kein ISO-Datum.")
    asset_ids = [a.get("id") for a in assets]
    if len(asset_ids) != len(set(asset_ids)):
        errors.append("Asset-IDs sind doppelt vergeben.")
    for a in assets:
        aid = a.get("id") or "?"
        if a.get("status") not in {"live", "planned"}:
            errors.append(f"{aid}: status muss live oder planned sein.")
        if a.get("status") != "live":
            continue
        for field in ("canonical", "methodology", "dataset", "press_asset", "published"):
            if not a.get(field):
                errors.append(f"{aid}: Pflichtfeld {field} fehlt.")
        quellen = a.get("source_urls") or []
        if len(quellen) < 2:
            errors.append(f"{aid}: mindestens zwei transparente Quellen-URLs nötig.")
        if len({str(u) for u in quellen}) != len(quellen):
            errors.append(f"{aid}: Quellen-URLs sind doppelt.")
        for url in quellen:
            teile = urlsplit(str(url))
            if teile.scheme != "https" or not teile.netloc:
                errors.append(f"{aid}: Quelle {url!r} ist keine öffentliche https-URL.")
        if not parse_date(a.get("published")):
            errors.append(f"{aid}: published-Datum fehlt/ungültig.")
        if isinstance(a.get("refresh_days"), (int, float)) and a["refresh_days"] < 1:
            errors.append(f"{aid}: refresh_days muss mindestens 1 sein.")
        canonical = a.get("canonical")
        if canonical:
            pfad = content_path(canonical)
            if not pfad.exists():
                errors.append(f"{aid}: Inhaltsseite fehlt: {pfad.relative_to(ROOT)}")
            else:
                methodik = str(a.get("methodology") or "")
                ziel, _, anker = methodik.partition("#")
                if ziel.rstrip("/") != str(canonical).rstrip("/"):
                    errors.append(f"{aid}: methodology muss auf die Inhaltsseite zeigen ({canonical}#…).")
                elif anker and not anchor_present(pfad.read_text(encoding="utf-8"), anker):
                    errors.append(f"{aid}: Methodik-Anker #{anker} fehlt in {pfad.relative_to(ROOT)}.")
        for field in ("dataset", "press_asset"):
            p = local_path(a.get(field))
            if p and not p.exists():
                errors.append(f"{aid}: Datei fehlt: {p.relative_to(ROOT)}")
            if a.get(field) and not p:
                errors.append(f"{aid}: {field} muss unter /downloads/ liegen (versioniert in static/).")

    evidence_items = evidence.get("evidence") or []
    evidence_ids = [item.get("id") for item in evidence_items]
    if any(not ident for ident in evidence_ids):
        errors.append("Jeder Evidenzbeleg braucht eine id.")
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("Evidenz-IDs sind doppelt vergeben.")
    gesehen = {}
    for item in evidence_items:
        ident = item.get("id") or "Evidenz ohne id"
        if item.get("kind") not in VALID_EVIDENCE:
            errors.append(f"{ident}: ungültiger kind-Wert.")
        for feld in ("title", "publisher"):
            if not str(item.get(feld) or "").strip():
                errors.append(f"{ident}: {feld} fehlt (ohne Herausgeber ist der Beleg nicht prüfbar).")
        url = str(item.get("url") or "")
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{ident}: öffentliche https-URL fehlt.")
        if host in {"franksfinanzcheck.de", "www.franksfinanzcheck.de"}:
            errors.append(f"{ident}: eigene Domain ist kein externer Beleg.")
        if any(key.split("=", 1)[0].lower().startswith(TRACKING_PREFIX)
               for key in parsed.query.split("&") if key):
            errors.append(f"{ident}: Beleg-URL enthält Tracking-Parameter.")
        if url and url in gesehen:
            errors.append(f"{ident}: URL ist bereits als {gesehen[url]} belegt (Doppelmeldung).")
        gesehen.setdefault(url, ident)
        if not parse_date(item.get("published")):
            errors.append(f"{ident}: published-Datum fehlt/ungültig.")
        ziel = str(item.get("target") or "")
        if ziel and not ziel.startswith(("/", "https://franksfinanzcheck.de/")):
            errors.append(f"{ident}: target muss auf eine eigene Seite zeigen.")

    # Messvertrag: jeder KPI hat genau eine Quelle, jeder Modus ist erklärt.
    contract = measurement_contract(strategy)
    if not contract["sources"]:
        errors.append("measurement.sources fehlt: ohne Quellenvertrag ist keine Kennzahl prüfbar.")
    if int(contract.get("reporting_lag_days") or 0) < 0:
        errors.append("reporting_lag_days muss >= 0 sein.")
    if not 1 <= int(contract.get("manual_due_day") or 0) <= 28:
        errors.append("manual_due_day muss zwischen 1 und 28 liegen.")
    if int(contract.get("gsc_max_age_days") or 0) < 1:
        errors.append("gsc_max_age_days muss mindestens 1 sein.")
    quellen_ids = [s.get("id") for s in contract["sources"]]
    if len(quellen_ids) != len(set(quellen_ids)):
        errors.append("Messquellen-IDs sind doppelt vergeben.")
    for quelle in contract["sources"]:
        qid = quelle.get("id") or "Quelle ohne id"
        if not quellen_ids or not qid:
            errors.append("Jede Messquelle braucht eine id.")
        if quelle.get("mode") not in SOURCE_MODES:
            errors.append(f"{qid}: mode muss einer von {sorted(SOURCE_MODES)} sein.")
        if not str(quelle.get("label") or "").strip():
            errors.append(f"{qid}: label fehlt.")
        if quelle.get("mode") == "automatisch" and qid not in AUTO_SOURCES:
            errors.append(f"{qid}: automatische Quelle ist nicht implementiert (bekannt: {sorted(AUTO_SOURCES)}).")
        if quelle.get("mode") in {"nicht_messbar", "nicht_aktiv"}:
            if not str(quelle.get("grund") or "").strip():
                errors.append(f"{qid}: nicht gemessene Quelle braucht grund.")
            if not parse_date(quelle.get("entschieden")):
                errors.append(f"{qid}: nicht gemessene Quelle braucht das Entscheidungsdatum entschieden.")
        if not quelle.get("kpi"):
            errors.append(f"{qid}: kpi fehlt.")
        optional = quelle.get("kpi_optional") or []
        if not isinstance(optional, list) or any(k not in (quelle.get("kpi") or []) for k in optional):
            errors.append(f"{qid}: kpi_optional muss eine Teilmenge von kpi sein.")
    for kpi, quellen in kpi_map(contract).items():
        if kpi not in PERIOD_VALUE_KEYS:
            errors.append(f"Kennzahl {kpi} ist im Vertrag nicht bekannt.")
        if len(quellen) > 1:
            errors.append(f"Kennzahl {kpi} ist mehreren Quellen zugeordnet.")

    # Messperioden dürfen nur Zahlen tragen, die auch belegt sind.
    evidence_id_set = {ident for ident in evidence_ids if ident}
    for period in (strategy.get("measurement") or {}).get("periods") or []:
        name = period.get("period")
        if not valid_period(name):
            errors.append(f"Messperiode {name!r}: period muss YYYY-MM sein.")
        if period.get("status") not in PERIOD_STATUS:
            errors.append(f"Messperiode {name}: status muss einer von {sorted(PERIOD_STATUS)} sein.")
        if period.get("updated") and not parse_date(period["updated"]):
            errors.append(f"Messperiode {name}: updated ist kein ISO-Datum.")
        zahlen = {k: v for k, v in period.items() if k in PERIOD_VALUE_KEYS and v is not None}
        fremd = {k for k in period if k not in PERIOD_VALUE_KEYS
                 and k not in {"period", "status", "updated", "evidence", "note", "quelle"}}
        if fremd:
            errors.append(f"Messperiode {name}: unbekannte Felder {sorted(fremd)}.")
        belege = period.get("evidence") or []
        if not isinstance(belege, list):
            errors.append(f"Messperiode {name}: evidence muss eine Liste von Beleg-IDs sein.")
            belege = []
        for ident in belege:
            if ident not in evidence_id_set:
                errors.append(f"Messperiode {name}: Beleg {ident!r} fehlt im Evidenzregister.")
        if zahlen and not belege:
            errors.append(f"Messperiode {name}: Werte ohne Evidenz/Importbeleg.")
    return errors


# ------------------------------------------------------------------ Messlage

def _pick(measurements, period, source):
    treffer = [m for m in measurements
               if m.get("period") == period and m.get("source") == source and not m.get("invalid")]
    return treffer[-1] if treffer else None


def month_facts(period, gsc, measurements):
    """Was ist für diesen Monat wirklich belegt – und wodurch?"""
    abgeleitet = gsc_month(gsc["ledger"], period)
    csv_import = _pick(measurements, period, "google-search-console-csv")
    audience = _pick(measurements, period, "first-party-audience-aggregate")
    werte, belege = {}, {}
    if abgeleitet:
        werte["gsc_clicks"] = abgeleitet["clicks"]
        werte["gsc_impressions"] = abgeleitet["impressions"]
        belege["gsc_clicks"] = belege["gsc_impressions"] = (
            f"`{gsc['datei']}` · {abgeleitet['tage']}/{abgeleitet['erwartet']} Tage")
    if csv_import:
        zahlen = csv_import.get("gsc") or {}
        for kpi, feld in (("gsc_clicks", "clicks"), ("gsc_impressions", "impressions"),
                          ("gsc_brand_clicks", "brand_clicks")):
            if zahlen.get(feld) is not None:
                werte[kpi] = zahlen[feld]
                belege[kpi] = f"`{csv_import['_file']}` (CSV-Import)"
    if audience:
        for kpi, wert in (audience.get("metrics") or {}).items():
            if kpi in AUDIENCE_KEYS:
                werte[kpi] = wert
                belege[kpi] = f"`{audience['_file']}` · {audience.get('provenance')}"
    return {
        "period": period,
        "werte": werte,
        "belege": belege,
        "abgeleitet": abgeleitet,
        "csv": csv_import,
        "audience": audience,
    }


def source_state(quelle, facts, contract, as_of):
    """Zustand einer Messquelle im Berichtsmonat – mit Beleg statt Behauptung."""
    qid = quelle.get("id")
    modus = quelle.get("mode")
    kpis = [k for k in quelle.get("kpi") or [] if k in PERIOD_VALUE_KEYS]
    optional = {k for k in (quelle.get("kpi_optional") or []) if k in kpis}
    pflicht = [k for k in kpis if k not in optional]
    gemessen = [k for k in kpis if facts["werte"].get(k) is not None]
    erfuellt = [k for k in pflicht if facts["werte"].get(k) is not None]
    zustand = {
        "id": qid,
        "label": quelle.get("label") or qid,
        "mode": modus,
        "grund": quelle.get("grund") or "",
        "entschieden": quelle.get("entschieden"),
        "kpi": kpis,
        "kpi_pflicht": pflicht,
        "gemessen": gemessen,
        "beleg": next((facts["belege"][k] for k in pflicht if k in facts["belege"]), None),
        "stand": None,
        "status": "unbekannt",
        "faellig": None,
    }
    period = facts["period"]
    if modus in {"nicht_messbar", "nicht_aktiv"}:
        zustand["status"] = "bewusst_nicht_gemessen"
        return zustand
    if modus == "manuell":
        zustand["faellig"] = manual_due(period, contract.get("manual_due_day") or 5)
    if qid == "gsc" and facts["abgeleitet"]:
        abgeleitet = facts["abgeleitet"]
        zustand["stand"] = f"{abgeleitet['von']}–{abgeleitet['bis']} · {abgeleitet['tage']}/{abgeleitet['erwartet']} Tage"
    if erfuellt and len(erfuellt) == len(pflicht):
        zustand["status"] = "belegt"
    elif erfuellt:
        zustand["status"] = "teilweise"
    elif modus == "manuell" and zustand["faellig"] and as_of < zustand["faellig"]:
        zustand["status"] = "noch_nicht_faellig"
    else:
        zustand["status"] = "offen"
    if qid == "gsc" and facts["abgeleitet"]:
        if facts["abgeleitet"]["tage"] < facts["abgeleitet"]["erwartet"]:
            zustand["status"] = "teilweise"
    return zustand


def outreach_artefakte():
    """Welche menschlichen Outreach-Vorlagen liegen im Repo?

    Der Radar belegt damit nur die *Vorbereitung*. Ob ein Pitch rausging und
    was er bewirkt hat, steht in keinem Repo-Artefakt – und wird deshalb
    nirgends behauptet.
    """
    if not OUTREACH.exists():
        return []
    artefakte = []
    for pfad in sorted(OUTREACH.glob("*.md")):
        try:
            relativ = pfad.relative_to(ROOT)
        except ValueError:
            relativ = pfad
        stand = ""
        try:
            for zeile in pfad.read_text(encoding="utf-8").splitlines()[:20]:
                treffer = re.search(r"Stand:?\**\s*(\d{2}\.\d{2}\.\d{4})", zeile)
                if treffer:
                    stand = treffer.group(1)
                    break
        except OSError:
            pass
        artefakte.append({"datei": str(relativ), "stand": stand})
    return artefakte


def conversion_signals():
    """Liefert Signale, dass ein als „nicht aktiv“ geführter Kanal Daten hat."""
    signale = []
    if KLICKMESSUNG.exists():
        try:
            daten = yaml.safe_load(KLICKMESSUNG.read_text(encoding="utf-8")) or {}
            if daten.get("aktiv") is True:
                signale.append("data/klickmessung.yaml: aktiv=true")
        except (OSError, yaml.YAMLError):
            pass
    if PROVISIONEN_AGGREGAT.exists():
        signale.append("data/provisionen_aggregat.json vorhanden")
    return signale


def build_lage(strategy, as_of, measurements=None):
    measurements = load_measurements() if measurements is None else measurements
    contract = measurement_contract(strategy)
    lag = int(contract.get("reporting_lag_days") or 4)
    gsc = load_gsc()
    berichtsmonat = reporting_month(as_of, lag)

    bekannte = {m.get("period") for m in measurements if valid_period(m.get("period"))}
    monate = {period_of(tag) for tag in gsc["ledger"]} | bekannte
    verlauf = {}
    for period in sorted(monate):
        verlauf[period] = month_facts(period, gsc, measurements)
    aktuell = month_facts(berichtsmonat, gsc, measurements)
    if berichtsmonat not in verlauf:
        verlauf[berichtsmonat] = aktuell

    quellen = [source_state(q, aktuell, contract, as_of) for q in contract["sources"]]
    return {
        "as_of": as_of,
        "berichtsmonat": berichtsmonat,
        "laufender_monat": period_of(as_of),
        "vertrag": contract,
        "measurements": measurements,
        "fakten": aktuell,
        "verlauf": dict(sorted(verlauf.items())),
        "quellen": quellen,
        "gsc": gsc,
        "gsc_health": gsc_health(gsc, as_of, int(contract.get("gsc_max_age_days") or 5)),
        "brand": brand_window(gsc),
        "signale": conversion_signals(),
        "outreach": outreach_artefakte(),
        "errors": list(gsc["errors"]),
    }


# ----------------------------------------------------------------- Bewertung

def declaration_actions(strategy, lage):
    """Hält die Deklaration in `authority_strategy.yaml` an der Messlage."""
    actions = []
    vertrag = lage["vertrag"]
    kpis = sorted(kpi_map(vertrag))
    for period in (strategy.get("measurement") or {}).get("periods") or []:
        name = period.get("period")
        if not valid_period(name) or name not in lage["verlauf"]:
            continue
        werte = lage["verlauf"][name]["werte"]
        vollstaendig = all(werte.get(k) is not None for k in kpis)
        status = period.get("status")
        if status == "belegt" and not vollstaendig:
            offen = ", ".join(k for k in kpis if werte.get(k) is None)
            actions.append(("P2", f"Deklaration für {name} sagt „belegt“, die Messlage nicht (offen: {offen}). "
                                  f"`data/authority_strategy.yaml` nachziehen – eine Deklaration ohne Beleg ist eine Behauptung."))
        elif status in {"offen", "teilweise"} and vollstaendig:
            actions.append(("P2", f"Deklaration für {name} steht auf „{status}“, alle Kennzahlen sind aber belegt. "
                                  f"`data/authority_strategy.yaml` auf „belegt“ setzen."))
    return actions


def evaluate(strategy, evidence, as_of, lage=None):
    lage = lage or build_lage(strategy, as_of)
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

    gesundheit = lage["gsc_health"]
    vertrag = lage["vertrag"]
    if gesundheit["status"] == "veraltet":
        actions.append(("P1", f"Google-Search-Console-Ledger steht seit {gesundheit['alter_tage']} Tagen "
                              f"(letzter Tag {gesundheit['letzter_tag']}, erwartet höchstens "
                              f"{vertrag.get('gsc_max_age_days')}). Ohne Tageslauf ist jede Reichweitenzahl unbelegt: "
                              f"`.github/workflows/gsc-import.yml` prüfen (Status: {gesundheit['meta_status'] or 'unbekannt'})."))
    elif gesundheit["status"] == "leer" and gesundheit["meta_status"] not in (None, "ok"):
        actions.append(("P1", "GSC-Import ist nicht eingerichtet "
                              f"({gesundheit['meta_status']}: {gesundheit['meta_grund'] or 'ohne Grund'}). "
                              "Einrichtung: docs/ANLEITUNG-GSC-API-ZUGRIFF.md – ohne Ledger bleibt Distribution ungemessen."))

    monat = lage["berichtsmonat"]
    fakten = lage["fakten"]
    for quelle in lage["quellen"]:
        status = quelle["status"]
        if quelle["mode"] == "manuell" and status in {"offen", "teilweise"}:
            faellig = quelle["faellig"]
            if lage["as_of"] >= faellig:
                fehlend = [k for k in quelle["kpi_pflicht"] if fakten["werte"].get(k) is None]
                kpis = ", ".join(fehlend or quelle["kpi_pflicht"])
                actions.append(("P2", f"{quelle['label']}: Aggregate für {monat} fehlen ({kpis}), fällig seit {faellig}. "
                                      f"Export belegen und einlesen: `python3 scripts/authority_engine.py --import-audience "
                                      f"<datei> --period {monat}` (Vorlage: `--template`; Runbook: "
                                      f"docs/AUTORITAET-DISTRIBUTION-RUNBOOK.md). Unbekannt bleibt unbekannt – eine 0 gilt nur mit Beleg."))
        if quelle["mode"] == "automatisch" and status in {"offen", "teilweise"}:
            abgeleitet = fakten["abgeleitet"]
            if abgeleitet and abgeleitet["tage"] >= abgeleitet["erwartet"]:
                continue
            if abgeleitet:
                actions.append(("P2", f"GSC-Tageszeilen für {monat} unvollständig "
                                      f"({abgeleitet['tage']}/{abgeleitet['erwartet']} Tage). Fehlende Tage in "
                                      f"`data/gsc/tagesdaten.jsonl` prüfen, bevor der Monat als belegt gilt."))
            else:
                actions.append(("P2", f"Für {monat} liegen keine GSC-Tageszeilen vor (0/{month_days(monat)}). "
                                      "Der Tageslauf muss den Ledger füllen – nachprüfen, nicht schätzen."))
        if quelle["mode"] == "nicht_aktiv" and quelle["id"] == "conversion" and lage["signale"]:
            actions.append(("P2", f"{quelle['label']} ist im Vertrag als nicht aktiv geführt, liefert aber Signale "
                                  f"({'; '.join(lage['signale'])}). `data/authority_strategy.yaml` nachziehen, "
                                  "sonst misst der Radar an der Wirklichkeit vorbei."))

    actions.extend(declaration_actions(strategy, lage))
    # P1 zuerst, dann P2 – und keine Doppelmeldung.
    gesehen, eindeutig = set(), []
    for prio, text in sorted(actions, key=lambda paar: (paar[0], paar[1])):
        if text not in gesehen:
            gesehen.add(text)
            eindeutig.append((prio, text))
    evidence_count = len(evidence.get("evidence") or [])
    return current_q, eindeutig, lage, evidence_count


# -------------------------------------------------------------------- Report

def _asset_reife(asset):
    """Prüfbare Reife eines Linkable Assets – ohne Selbstauskunft."""
    canonical = str(asset.get("canonical") or "")
    pfad = content_path(canonical) if canonical else None
    text = pfad.read_text(encoding="utf-8") if pfad and pfad.exists() else ""
    anker = str(asset.get("methodology") or "").partition("#")[2]
    return [
        ("Inhaltsseite", bool(pfad and pfad.exists())),
        ("Methodik-Anker", bool(text) and anchor_present(text, anker) if anker else False),
        ("Datensatz/CSV", bool(local_path(asset.get("dataset")) and local_path(asset.get("dataset")).exists())),
        ("Presseformat", bool(local_path(asset.get("press_asset")) and local_path(asset.get("press_asset")).exists())),
        ("Quellen (≥ 2)", len(asset.get("source_urls") or []) >= 2),
    ]


def write_report(strategy, evidence, lage, quarter, actions):
    as_of = lage["as_of"]
    monat = lage["berichtsmonat"]
    fakten = lage["fakten"]
    kpis = kpi_map(lage["vertrag"])
    counts = {k: 0 for k in VALID_EVIDENCE}
    for item in evidence.get("evidence") or []:
        if item.get("kind") in counts:
            counts[item["kind"]] += 1
    erhebbar = [q for q in lage["quellen"] if q["mode"] in {"automatisch", "manuell"}]
    belegt = [q for q in erhebbar if q["status"] == "belegt"]
    p1 = sum(1 for prio, _ in actions if prio == "P1")
    p2 = sum(1 for prio, _ in actions if prio == "P2")

    zeilen = [
        f"# Authority-Radar – {as_of.isoformat()}",
        "",
        "> Belegt externe Autorität, Distribution und Audience-Kennzahlen. "
        "`0` heißt **gemessen und null**. `—` heißt **unbekannt**. Unbekannt bleibt unbekannt.",
        "",
        f"**Berichtsmonat:** {monat} "
        f"({fakten['abgeleitet']['tage'] if fakten['abgeleitet'] else 0}/{month_days(monat)} Tage im GSC-Ledger) · "
        f"**Aktuelles Quartal:** {quarter} · "
        f"**Belegte Messquellen:** {len(belegt)}/{len(erhebbar)} · "
        f"**Handlungsbedarf:** {p1} × P1, {p2} × P2",
        "",
        "## Handlungsqueue",
        "",
    ]
    if actions:
        zeilen += [f"- **{prio}:** {text}" for prio, text in actions]
    else:
        zeilen.append("- Keine fällige Maßnahme.")
    zeilen += ["", "## Datenlage", "",
               "| Quelle | Modus | Stand | Status | Beleg |", "|---|---|---|---|---|"]
    for quelle in lage["quellen"]:
        status = quelle["status"]
        if status == "belegt":
            anzeige = "✅ belegt"
        elif status == "teilweise":
            anzeige = "⚠️ teilweise"
        elif status == "offen":
            anzeige = f"❌ offen seit {quelle['faellig']}" if quelle["faellig"] else "❌ offen"
        elif status == "noch_nicht_faellig":
            anzeige = f"🕒 fällig ab {quelle['faellig']}"
        elif status == "bewusst_nicht_gemessen":
            anzeige = "⏸ bewusst nicht gemessen"
        else:
            anzeige = "–"
        stand = quelle["stand"] or (
            f"Entscheidung {quelle['entschieden']}" if quelle["entschieden"] else "—")
        zeilen.append(f"| {quelle['label']} | {quelle['mode']} | {stand} | {anzeige} | "
                      f"{quelle['beleg'] or '—'} |")
    for quelle in lage["quellen"]:
        if quelle["grund"]:
            zeilen += ["", f"- **{quelle['label']}** ({quelle['mode']}): {quelle['grund']}"]
    gesundheit = lage["gsc_health"]
    zeilen += ["", f"Ledger-Kopf: letzter Tag **{gesundheit['letzter_tag'] or '—'}** "
                   f"({gesundheit['alter_tage'] if gesundheit['alter_tage'] is not None else '—'} Tage alt, "
                   f"Status {gesundheit['status']}, Import {gesundheit['meta_status'] or 'unbekannt'}). "
                   f"Der laufende Monat {lage['laufender_monat']} wird gezeigt, aber nie eingefordert – "
                   f"er ist noch nicht abgeschlossen.",
              "", f"## Audience-Kennzahlen {monat}", "",
              "| Kennzahl | Wert | Quelle | Beleg |", "|---|---:|---|---|"]
    reihenfolge = [
        "gsc_clicks", "gsc_impressions", "gsc_brand_clicks",
        "newsletter_subscribers", "newsletter_click_rate",
        "returning_reader_rate", "conversions", "conversion_rate",
    ]
    label = {
        "gsc_clicks": "GSC-Klicks", "gsc_impressions": "GSC-Impressionen",
        "gsc_brand_clicks": "Marken-Klicks", "newsletter_subscribers": "Newsletter-Abonnenten",
        "newsletter_click_rate": "Newsletter-Klickrate", "returning_reader_rate": "Wiederkehrende Leser",
        "conversions": "Conversions", "conversion_rate": "Conversion-Rate",
    }
    for kpi in [k for k in reihenfolge if k in kpis] + sorted(k for k in kpis if k not in reihenfolge):
        quelle = kpis[kpi][0]
        wert = fakten["werte"].get(kpi)
        anzeige = de_quote(wert) if kpi in RATE_KEYS else de_num(wert)
        beleg = fakten["belege"].get(kpi)
        if wert is None:
            if quelle["mode"] == "nicht_messbar":
                beleg = f"bewusst nicht gemessen: {quelle['grund']}"
            elif quelle["mode"] == "nicht_aktiv":
                beleg = f"nicht in Betrieb: {quelle['grund']}"
            elif kpi == "gsc_brand_clicks":
                beleg = "Tages-Ledger führt keine Suchanfragen (monatsscharf nur per CSV-Export)"
            else:
                beleg = beleg or "kein Beleg vorhanden"
        zeilen.append(f"| {label.get(kpi, kpi)} | {anzeige} | {quelle['label']} | {beleg} |")
    if fakten["abgeleitet"] and fakten["abgeleitet"]["ctr"] is not None:
        zeilen += ["", f"Abgeleiteter CTR aus dem Ledger: **{de_quote(fakten['abgeleitet']['ctr'])}** "
                       f"(Klicks {de_int(fakten['abgeleitet']['clicks'])} / "
                       f"Impressionen {de_int(fakten['abgeleitet']['impressions'])}, "
                       f"{fakten['abgeleitet']['von']}–{fakten['abgeleitet']['bis']})."]

    zeilen += ["", "## Markensichtbarkeit (rollierend, nicht monatsscharf)", ""]
    brand = lage["brand"]
    if brand:
        zeilen += [
            f"Fenster **{brand['von']}–{brand['bis']}** (28 Tage) aus `{brand['datei']}`: "
            f"{brand['abfragen']} Suchanfragen in den Top-500, davon {brand['marken_abfragen']} mit Markenbezug.",
            "",
            f"- Impressionen gesamt (Top-500): **{de_int(brand['impressionen'])}**, davon markenbezogen "
            f"**{de_int(brand['marken_impressionen'])}** ({de_quote(brand['anteil'])}).",
            f"- Klicks gesamt: **{de_int(brand['clicks'])}**, davon markenbezogen **{de_int(brand['marken_clicks'])}**.",
            "",
            "_Das Fenster ist rollierend und deckt die Top-500-Suchanfragen ab. Es ist kein Monatswert und "
            "ersetzt keinen Monats-Export mit Markensuche._",
        ]
    else:
        zeilen.append("_Keine belegbare Markensichtbarkeit: Es liegen keine Top-Suchanfragen mit Zeitfenster vor._")

    zeilen += ["", "## Verdiente externe Signale", "", "| Signal | Anzahl |", "|---|---:|"]
    signal_label = {
        "editorial_link": "Redaktionelle Links", "media_mention": "Mediennennungen",
        "interview": "Experteninterviews", "cooperation": "Aktive Kooperationen",
    }
    for kind, anzeige_name in signal_label.items():
        zeilen.append(f"| {anzeige_name} | {counts[kind]} |")
    zeilen += ["", "_Alle vier Register geprüft. `0` heißt: kein prüfbarer Beleg eingetragen – "
                   "das ist der belegte Ist-Stand, kein Nachweis von Wirkung._",
               "", "## Nachweisregister", ""]
    evidence_items = evidence.get("evidence") or []
    if evidence_items:
        zeilen += ["| Datum | Typ | Nachweis | Herausgeber |", "|---|---|---|---|"]
        for item in sorted(evidence_items, key=lambda value: str(value.get("published", "")), reverse=True):
            titel = str(item.get("title") or item.get("id")).replace("|", "\\|")
            herausgeber = str(item.get("publisher") or "—").replace("|", "\\|")
            typ = EVIDENCE_LABEL.get(item.get("kind"), str(item.get("kind")))
            zeilen.append(f"| {item.get('published')} | {typ} | [{titel}]({item.get('url')}) | {herausgeber} |")
    else:
        zeilen.append("_Keine externe Autorität behauptet: Im Evidenzregister liegt noch kein prüfbarer Beleg. "
                      "Eigene Posts, Verzeichnisse und Affiliate-Platzierungen zählen nicht._")

    zeilen += ["", "## Distribution (menschlich, nicht automatisiert)", "",
               "Der Radar versendet nichts und zählt keine Pitches. Belegt ist hier nur, welche "
               "Outreach-Vorlagen im Repo liegen – **nicht**, ob sie verschickt wurden oder gewirkt haben.",
               ""]
    if lage["outreach"]:
        for artefakt in lage["outreach"]:
            stand = f" (Stand {artefakt['stand']})" if artefakt["stand"] else ""
            zeilen.append(f"- `{artefakt['datei']}`{stand}")
    else:
        zeilen.append("- _Keine Outreach-Vorlage im Repo hinterlegt._")
    zeilen += ["", "Grenzen dieser Ausgabe: Der Markenanteil ist ein rollierendes 28-Tage-Fenster der "
                   "Top-500-Suchanfragen, kein Monatswert. Ohne Besucherzähler gibt es keine "
                   "Returning-Rate. Wirkung wird nicht kausal zugerechnet."]

    zeilen += ["", "## Quartalsprogramm und Asset-Reife", "",
               "| Quartal | Asset | Status | Termin | Reife |", "|---|---|---|---|---|"]
    assets = {a.get("id"): a for a in strategy.get("assets") or []}
    for q in strategy.get("quarters") or []:
        asset = assets.get(q.get("asset_id"))
        reife = _asset_reife(asset) if (asset and q.get("status") == "live") else []
        reife_text = (f"{sum(1 for _, ok in reife if ok)}/{len(reife)} Kriterien" if reife else "—")
        termin = q.get("release") or q.get("release_due") or "–"
        zeilen.append(f"| {q.get('quarter')} | `{q.get('asset_id')}` | {q.get('status')} | {termin} | {reife_text} |")
    live = [a for a in strategy.get("assets") or [] if a.get("status") == "live"]
    for asset in live:
        reife = _asset_reife(asset)
        kriterien = " · ".join(f"{'✅' if ok else '✖'} {name}" for name, ok in reife)
        zeilen += ["", f"**{asset.get('title')}** (live seit {asset.get('published')})", "",
                   f"- Reife: {kriterien}"]
        quellen = asset.get("source_urls") or []
        if quellen:
            zeilen.append("- Quellen: " + " · ".join(f"<{u}>" for u in quellen))

    zeilen += ["", "## Messverlauf", "",
               "| Monat | GSC-Klicks | GSC-Impressionen | Abdeckung | Audience-Aggregat |",
               "|---|---:|---:|---|---|"]
    for period, daten in list(lage["verlauf"].items())[-6:]:
        abgeleitet = daten["abgeleitet"]
        audience = "belegt" if daten["audience"] else "—"
        if abgeleitet:
            marker = " (laufend)" if period == lage["laufender_monat"] else ""
            zeilen.append(f"| {period}{marker} | {de_int(abgeleitet['clicks'])} | "
                          f"{de_int(abgeleitet['impressions'])} | "
                          f"{abgeleitet['tage']}/{abgeleitet['erwartet']} Tage | {audience} |")
        else:
            zeilen.append(f"| {period} | — | — | 0/{month_days(period)} Tage | {audience} |")

    offene_termine = [parse_date(q.get("release_due")) for q in strategy.get("quarters") or []
                      if q.get("status") != "live"]
    naechster_release = min((tag for tag in offene_termine if tag), default=None)

    zeilen += ["", "## Betriebsregel und Takt", "",
               "Ein Asset ist erst live, wenn Inhaltsseite, Methodik, Rohdaten/CSV, Quellen und Presseformat "
               "vorhanden sind. Outreach bleibt menschlich; der Radar versendet nichts.",
               "",
               "GSC wird aus `data/gsc/tagesdaten.jsonl` **abgeleitet** (ein Tageslauf, eine Wahrheit); "
               "der CSV-Import bleibt für Marken-Suchanfragen möglich. Manuelle Audience-Aggregate werden "
               "monatlich belegt (`--import-audience`). Was nicht messbar ist, steht mit Grund und "
               "Entscheidungsdatum im Vertrag – und wird nie als `0` behauptet.",
               "",
               f"Nächste Fälligkeiten: manueller Audience-Export für {monat} "
               f"({manual_due(monat, lage['vertrag'].get('manual_due_day') or 5)}) · "
               f"nächster Quartalsrelease ({naechster_release or '—'}) · "
               f"nächster Radar-Lauf am 5. des Folgemonats.",
               ""]
    REPORT.write_text("\n".join(zeilen), encoding="utf-8")


def radar_json(strategy, evidence, lage, quarter, actions):
    """Maschinenlesbare Fassung – ohne Suchanfragen, ohne Empfängerbezug."""
    return {
        "schema": 1,
        "as_of": lage["as_of"].isoformat(),
        "reporting_month": lage["berichtsmonat"],
        "current_month": lage["laufender_monat"],
        "quarter": quarter,
        "actions": [{"prio": prio, "text": text} for prio, text in actions],
        "sources": [
            {
                "id": quelle["id"],
                "label": quelle["label"],
                "mode": quelle["mode"],
                "status": quelle["status"],
                "faellig": quelle["faellig"].isoformat() if quelle["faellig"] else None,
                "stand": quelle["stand"],
                "beleg": quelle["beleg"],
                "kpi": quelle["kpi"],
                "gemessen": quelle["gemessen"],
                "nicht_gemessen": [k for k in quelle["kpi_pflicht"] if k not in quelle["gemessen"]],
                "grund": quelle["grund"],
                "entschieden": (quelle["entschieden"].isoformat()
                                if isinstance(quelle["entschieden"], dt.date)
                                else quelle["entschieden"]),
            }
            for quelle in lage["quellen"]
        ],
        "kpis": lage["fakten"]["werte"],
        "kpi_belege": lage["fakten"]["belege"],
        "evidence": {kind: sum(1 for item in evidence.get("evidence") or []
                               if item.get("kind") == kind) for kind in sorted(VALID_EVIDENCE)},
        "gsc": {
            "datei": lage["gsc"]["datei"],
            "letzter_tag": (lage["gsc_health"]["letzter_tag"].isoformat()
                            if lage["gsc_health"]["letzter_tag"] else None),
            "alter_tage": lage["gsc_health"]["alter_tage"],
            "status": lage["gsc_health"]["status"],
            "meta_status": lage["gsc_health"]["meta_status"],
        },
        "brand_window": lage["brand"],
        "outreach_artefakte": [artefakt["datei"] for artefakt in lage["outreach"]],
        "privacy": "Nur Aggregate; keine Suchanfragen, keine Empfänger- oder Nutzerkennungen.",
    }


# -------------------------------------------------------------------- Importe

def num(value):
    text = str(value or "0").strip().replace("\u202f", "").replace(" ", "").replace("%", "")
    # Google-Exporte können 1.234,5 oder 1,234.5 verwenden.
    if "," in text and "." in text:
        text = (text.replace(".", "").replace(",", ".")
                if text.rfind(",") > text.rfind(".") else text.replace(",", ""))
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text or 0)
    except ValueError:
        raise ValueError(f"Zahl nicht lesbar: {value!r}")


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
        fields[key] = next((h for h in headers if h and h.strip() in names), None)
    if not fields["clicks"] or not fields["impressions"]:
        raise ValueError("Spalten Klicks/Clicks und Impressionen/Impressions fehlen.")
    clicks = impressions = 0.0
    brand_clicks = brand_impressions = 0.0 if fields["query"] else None
    for row in rows:
        c, i = num(row.get(fields["clicks"])), num(row.get(fields["impressions"]))
        if c < 0 or i < 0 or c > i:
            raise ValueError("GSC-Werte müssen nichtnegativ sein; Klicks dürfen Impressionen nicht übersteigen.")
        clicks += c
        impressions += i
        if fields["query"] and BRAND_RE.search(row.get(fields["query"]) or ""):
            brand_clicks += c
            brand_impressions += i
    payload = {
        "schema": 1, "period": period, "source": "google-search-console-csv",
        "imported": dt.date.today().isoformat(), "rows_aggregated": len(rows),
        "gsc": {"clicks": round(clicks), "impressions": round(impressions),
                "ctr": round(clicks / impressions, 6) if impressions else None,
                "brand_clicks": None if brand_clicks is None else round(brand_clicks),
                "brand_impressions": None if brand_impressions is None else round(brand_impressions)},
        "privacy": "Nur Aggregate; Suchanfragen wurden nicht gespeichert.",
    }
    target = MEASUREMENTS / f"{period}-gsc.json"
    atomic_json_write(target, payload)
    return target


def import_audience(path, period):
    """Importiert bereits aggregierte First-Party-KPIs, nie Empfängerdaten."""
    if not valid_period(period):
        raise ValueError("Periode muss YYYY-MM und ein echter Monat sein.")
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Audience-Datei muss ein JSON-Objekt sein.")
    fremd = {k for k, v in raw.items()
             if v is not None and k not in AUDIENCE_KEYS | {"provenance"}
             and not str(k).startswith("_")}
    if fremd:
        raise ValueError(f"Unbekannte Felder: {', '.join(sorted(fremd))} "
                         f"(erlaubt: {', '.join(sorted(AUDIENCE_KEYS))} und provenance).")
    metrics = {key: raw[key] for key in AUDIENCE_KEYS if raw.get(key) is not None}
    if not metrics:
        raise ValueError("Keine erlaubte Audience-Kennzahl vorhanden.")
    if not str(raw.get("provenance") or "").strip():
        raise ValueError("provenance (Export-/Dashboard-Beleg) fehlt.")
    if any(not _zahl(value) for value in metrics.values()):
        raise ValueError("Audience-Kennzahlen müssen Zahlen sein.")
    if any(value < 0 for value in metrics.values()):
        raise ValueError("Audience-Kennzahlen dürfen nicht negativ sein.")
    if any(metrics[key] > 1 for key in RATE_KEYS & metrics.keys()):
        raise ValueError("Audience-Raten müssen als Anteil zwischen 0 und 1 vorliegen.")
    payload = {
        "schema": 1, "period": period, "source": "first-party-audience-aggregate",
        "imported": dt.date.today().isoformat(), "metrics": metrics,
        "provenance": str(raw["provenance"]).strip(),
        "privacy": "Nur Aggregate; keine E-Mail-Adressen, IDs oder Ereigniszeilen.",
    }
    target = MEASUREMENTS / f"{period}-audience.json"
    atomic_json_write(target, payload)
    return target


def audience_template(period):
    return {
        "newsletter_subscribers": None,
        "newsletter_click_rate": None,
        "conversions": None,
        "provenance": f"Newsletter-Studio/Resend Monatsauszug {period} (Bildschirm-Export oder CSV-Abzug)",
        "_hinweis": "Nur Zahlen eintragen, die im Dashboard/Export ablesbar sind. Unbekannt bleibt null – "
                    "null ist niemals 0. Raten als Anteil 0..1. Die Datei ist lokal; versioniert werden "
                    "nur die Aggregate unter data/authority_measurements/.",
        "_period": period,
    }


# ---------------------------------------------------------------- Selbsttest

def selftest():
    assert quarter_for(dt.date(2026, 10, 2)) == "2026-Q4"
    assert quarter_for(dt.date(2027, 3, 31)) == "2027-Q1"
    assert reporting_month(dt.date(2026, 11, 5)) == "2026-10"
    assert reporting_month(dt.date(2026, 11, 4)) == "2026-09"
    assert reporting_month(dt.date(2027, 1, 9)) == "2026-12"
    assert manual_due("2026-10", 5) == dt.date(2026, 11, 5)
    assert manual_due("2026-12", 5) == dt.date(2027, 1, 5)
    assert period_of(dt.date(2026, 2, 9)) == "2026-02" and month_days("2028-02") == 29
    assert BRAND_RE.search("Franks Finanzcheck")
    assert not BRAND_RE.search("strom sparen")
    assert abs(num("1.234,5") - 1234.5) < 0.01 and abs(num("1,234.5") - 1234.5) < 0.01
    assert de_num(None) == "—" and de_num(0) == "0" and de_int(1234) == "1.234"
    assert slugify("Methodik & Quellen") == "methodik-quellen"
    assert anchor_present("## Methodik\n", "methodik")
    assert anchor_present("Text {#methodik}\n", "methodik")
    assert not anchor_present("## Quellen\n", "methodik")
    ledger = {dt.date(2026, 10, 1): {"clicks": 2, "impressions": 10},
              dt.date(2026, 10, 31): {"clicks": 0, "impressions": 5},
              dt.date(2026, 11, 1): {"clicks": 1, "impressions": 4}}
    oktober = gsc_month(ledger, "2026-10")
    assert oktober["clicks"] == 2 and oktober["impressions"] == 15
    assert oktober["tage"] == 2 and oktober["erwartet"] == 31
    assert abs(oktober["ctr"] - 2 / 15) < 1e-6
    assert gsc_month(ledger, "2026-08") is None
    gesund = gsc_health({"ledger": ledger, "meta": {}}, dt.date(2026, 11, 5), 5)
    assert gesund["letzter_tag"] == dt.date(2026, 11, 1) and gesund["status"] == "frisch"
    assert gsc_health({"ledger": ledger, "meta": {}}, dt.date(2026, 11, 20), 5)["status"] == "veraltet"
    fenster = brand_window({"meta": {"zeitraum": {"bis": "2026-11-02"}},
                            "queries": [{"suchbegriff": "Franks Finanzcheck", "clicks": 3, "impressions": 7},
                                        {"suchbegriff": "strom sparen", "clicks": 1, "impressions": 3}]})
    assert fenster["marken_clicks"] == 3 and fenster["impressionen"] == 10
    assert fenster["anteil"] == 0.7 and fenster["von"] == "2026-10-06"
    assert brand_window({"meta": {}, "queries": []}) is None
    print("Authority Engine: Selbsttest grün (Berichtsmonat, Ledger, Markenfenster, Belegform)")


# ----------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description="Authority-Radar: Nachweise, Distribution, Messlage.")
    p.add_argument("--check", action="store_true", help="Vertrag prüfen und Report schreiben")
    p.add_argument("--as-of", help="Stichtag YYYY-MM-DD (Standard: heute)")
    p.add_argument("--import-gsc", help="GSC-CSV exportieren (nur Aggregate, optional)")
    p.add_argument("--import-audience", help="aggregierte Audience-Kennzahlen (JSON)")
    p.add_argument("--period", help="Messperiode YYYY-MM für Importe")
    p.add_argument("--template", action="store_true", help="Vorlage für den Audience-Export ausgeben")
    p.add_argument("--json", help="Messlage zusätzlich als JSON-Datei schreiben")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)
    if args.selftest:
        selftest()
        return 0
    if args.template:
        if not valid_period(args.period):
            print("Vorlage braucht --period YYYY-MM mit echtem Monat", file=sys.stderr)
            return 2
        print(json.dumps(audience_template(args.period), ensure_ascii=False, indent=2))
        return 0
    if args.import_gsc or args.import_audience:
        if not valid_period(args.period):
            print("Import braucht --period YYYY-MM mit echtem Monat", file=sys.stderr)
            return 2
        try:
            if args.import_gsc:
                target = import_gsc(args.import_gsc, args.period)
                print(f"GSC aggregiert: {target.relative_to(ROOT)}")
            if args.import_audience:
                target = import_audience(args.import_audience, args.period)
                print(f"Audience aggregiert: {target.relative_to(ROOT)}")
        except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
            print(f"Importfehler: {exc}", file=sys.stderr)
            return 2
    strategy, evidence = load_yaml(STRATEGY), load_yaml(EVIDENCE)
    errors = validate(strategy, evidence)
    errors += validate_measurements(load_measurements())
    if errors:
        print("\n".join(f"FEHLER: {e}" for e in errors), file=sys.stderr)
        return 2
    as_of = parse_date(args.as_of) if args.as_of else dt.date.today()
    if not as_of:
        print("--as-of muss YYYY-MM-DD sein", file=sys.stderr)
        return 2
    lage = build_lage(strategy, as_of)
    if lage["errors"]:
        print("\n".join(f"FEHLER: {e}" for e in lage["errors"]), file=sys.stderr)
        return 2
    quarter, actions, lage, _ = evaluate(strategy, evidence, as_of, lage=lage)
    write_report(strategy, evidence, lage, quarter, actions)
    if args.json:
        ziel = Path(args.json)
        if not ziel.is_absolute():
            ziel = ROOT / ziel
        atomic_json_write(ziel, radar_json(strategy, evidence, lage, quarter, actions))
    print(f"Authority-Radar: {len(actions)} Maßnahme(n), {REPORT.relative_to(ROOT)}")
    return 1 if actions else 0


if __name__ == "__main__":
    sys.exit(main())
