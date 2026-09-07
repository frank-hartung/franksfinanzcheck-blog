#!/usr/bin/env python3
"""
UMAMI-CLICKS – Klick-Daten automatisch holen (Geschäftsgrundlage Affiliate)

WARUM: Der Governance-Report #206 stand jede Woche gleich:
  `Affiliate-Klicks (Umsatz-Hebel) | 0 über 0 Artikel | 🟡`
  `Awin-Provision (Klicks→Umsatz)  | 0.00 € ... | 🟡`
Das ist kein Content-Problem, sondern eine **Datenlücke**: Die Blog-Seite feuert
das Umami-Event `affiliate_click` längst (inkl. `slug`/`article`/`pillar`, siehe
`layouts/_default/_markup/render-link.html`), aber die Auswertung in
`scripts/click_attribution.py` brauchte bisher einen **manuellen** JSON-Export
aus dem Umami-Dashboard. Manuelle Schritte in einer Automatisierung sind der
Anfang von jedem stillen Stillstand – sie passieren halt nicht.

DIESES SKRIPT SCHLIESST DIE LÜCKE:
  1. Liest Website-ID automatisch aus `hugo.toml` (`[params.umami] websiteId`) –
     keine zweite Stelle, die man pflegen müsste.
  2. Holt Event-Daten über die Umami-API (Cloud `https://api.umami.is/v1` mit
     `x-umami-api-key`, selbst-gehostet via `UMAMI_API_BASE`).
  3. Schreibt `data/umami_clicks.json` in genau dem Schema, das
     `click_attribution.py` bereits versteht (+ Meta-Datei mit Stand).

DSGVO: Es werden ausschließlich **aggregierte Zähler** je /go/-Stelle, Artikel
und Pillar gelandet – keine IPs, keine User-IDs, keine Session-Rohevents.
Token werden nie geloggt und nie in Dateien geschrieben.

EHRLICHE DEGRADATION (das eigentliche Anti-#206-Verhalten):
  - Kein Token  → Hinweis + Exit 0 (Konfigurationslücke, kein Laufzeitfehler)
                  und `data/umami_clicks.meta.json` dokumentiert den Grund.
  - API krank (Netzwerk/5xx) → letzter Bestand bleibt erhalten, nie
                  ein leeres `umami_clicks.json` (ein Ausfall der Analytics-
                  Infrastruktur darf nicht wie „0 Klicks" aussehen!).
  - 0 Klicks    → wird als echtes Ergebnis geschrieben (mit Zeitfenster).

Nutzung:
  python3 scripts/umami_clicks.py --fetch              # API → data/umami_clicks.json
  python3 scripts/umami_clicks.py --fetch --days 180
  python3 scripts/umami_clicks.py --status             # Pipeline-Stand anzeigen
  python3 scripts/umami_clicks.py --selftest

Exit-Codes: 0 = befüllt oder sauber übersprungen, 1 = Fehler (bei --strict),
             2 = Selftest/Hausfehler.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

OUT = os.path.join(BLOG_DIR, "data", "umami_clicks.json")
META = os.path.join(BLOG_DIR, "data", "umami_clicks.meta.json")
HUGO_TOML = os.path.join(BLOG_DIR, "hugo.toml")

TODAY = datetime.date.today()
DEFAULT_BASE = "https://api.umami.is/v1"
DEFAULT_EVENT = "affiliate_click"
PAGE_SIZE = 1000
MAX_PAGES = 12
TIMEOUT = 25
RETRIES = 3


# ------------------------------------------------------------------ Konfiguration

def website_id():
    """Website-ID aus hugo.toml – die eine Wahrheit, kein zweiter Secret-Wirrwarr."""
    env = os.environ.get("UMAMI_WEBSITE_ID", "").strip()
    if env:
        return env
    try:
        txt = open(HUGO_TOML, encoding="utf-8").read()
    except OSError:
        return ""
    m = re.search(r"^\[params\.umami\]$(.*?)(?=^\[|\Z)", txt, re.M | re.S)
    block = m.group(1) if m else txt
    m = re.search(r"websiteId\s*=\s*\"([0-9a-fA-F\-]{8,})\"", block)
    return m.group(1) if m else ""


def api_token():
    for var in ("UMAMI_API_TOKEN", "UMAMI_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return ""


def api_base():
    return (os.environ.get("UMAMI_API_BASE") or DEFAULT_BASE).strip().rstrip("/")


def _redact(text, *secrets):
    out = str(text or "")
    for sec in secrets:
        if sec and len(sec) >= 4:
            out = out.replace(sec, "***")
    return out[:200]


# ------------------------------------------------------------------ HTTP

def _get(url, headers, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "franksfin-gov/2.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(4_000_000)
        return getattr(resp, "status", 200), json.loads(body.decode("utf-8") or "{}"), None
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTP {exc.code}"
    except json.JSONDecodeError as exc:
        return 500, None, f"Antwort kein JSON ({exc.msg})"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, None, exc.__class__.__name__


def _get_retry(url, headers, secret):
    last = "unbekannt"
    for attempt in range(1, RETRIES + 1):
        status, payload, err = _get(url, headers)
        if status == 200 and payload is not None:
            return payload, None
        last = _redact(err or f"HTTP {status}", secret)
        if status in (401, 403, 404):        # falsch/konfiguriert: retryn hilft nicht
            break
        if attempt < RETRIES:
            time.sleep(2 * attempt)
    return None, last


# ------------------------------------------------------------------ Parsing (robust)

def _prop_value(event_props, key):
    """Umami liefert Eigenschaften je nach Version als Liste {dataKey,value}
    oder als flache Felder. Beides wird unterstützt."""
    if isinstance(event_props, dict):
        return event_props.get(key)
    if isinstance(event_props, list):
        for p in event_props:
            if isinstance(p, dict) and p.get("dataKey") == key:
                for alt in ("stringValue", "numberValue", "value"):
                    if p.get(alt) not in (None, ""):
                        return p[alt]
    return None


def _rows_from_event_data(payload):
    """`/event-data` (Zeilen mit Eigenschaften) → Klick-Reihen für click_attribution."""
    rows = []
    if not isinstance(payload, dict):
        return rows
    data = payload.get("data")
    if data is None:
        data = payload.get("rows")
    if not isinstance(data, list):
        return rows
    for item in data:
        if not isinstance(item, dict):
            continue
        props = item.get("eventProperties") or item
        slug = _prop_value(props, "slug") or _prop_value(props, "go") or ""
        article = _prop_value(props, "article") or ""
        pillar = _prop_value(props, "pillar") or ""
        try:
            count = int(_prop_value(props, "count") or 1)
        except (TypeError, ValueError):
            count = 1
        rows.append({"event": DEFAULT_EVENT, "slug": str(slug)[:120],
                     "article": str(article)[:120], "pillar": str(pillar)[:60],
                     "count": max(1, count)})
    return rows


def _rows_from_series(payload):
    """Fallback `/events` (Zeitreihe x/t/y): nur Gesamtzahl je Tag, ohne
    Artikel-Zuordnung. Besser als gar keine Zahl – und als `unknown` markiert."""
    rows = []
    if not isinstance(payload, dict):
        return rows
    data = payload.get("data")
    if not isinstance(data, dict):
        return rows
    xs = data.get("x") if isinstance(data.get("x"), list) else []
    ys_raw = data.get("y")
    if not isinstance(ys_raw, list):
        ys_raw = data.get("events")
    ys = ys_raw if isinstance(ys_raw, list) else []
    for x, y in zip(xs, ys):
        try:
            n = int(y)
        except (TypeError, ValueError):
            continue
        if n > 0:
            rows.append({"event": DEFAULT_EVENT, "slug": "unknown", "article": str(x)[:20],
                         "pillar": "", "count": n})
    return rows


def aggregate(rows):
    """Zähler je (slug, article, pillar) bündeln – Identifikator-schonend."""
    out = {}
    for r in rows:
        key = (str(r.get("slug") or "unknown")[:80], str(r.get("article") or "")[:80],
               str(r.get("pillar") or "")[:60])
        d = out.setdefault(key, {"event": DEFAULT_EVENT, "slug": key[0], "article": key[1],
                                 "pillar": key[2], "count": 0})
        d["count"] += int(r.get("count") or 1)
    return sorted(out.values(), key=lambda d: -d["count"])


# ------------------------------------------------------------------ Fetch

def fetch(days=90, event_key=DEFAULT_EVENT):
    """→ (rows|None, meta). rows=None bedeutet: API nicht nutzbar (Bestand bleibt!)."""
    token, base, wid = api_token(), api_base(), website_id()
    meta = {"attempted": TODAY.isoformat(), "base": base, "website_id_set": bool(wid),
            "token_present": bool(token), "days": days, "event": event_key,
            "endpoint": None, "rows": 0, "total": 0, "reason": ""}
    if not token or not wid:
        meta["reason"] = ("kein UMAMI_API_TOKEN" if not token else "keine websiteId in hugo.toml")
        return None, meta
    headers = {"x-umami-api-key": token, "Accept": "application/json"}
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(days) * 86_400_000
    q = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms,
                                "limit": PAGE_SIZE, "pageSize": PAGE_SIZE})
    # 1) Reichhaltige Variante: Event-Rohdaten mit Eigenschaften (Artikel/Pillar).
    rows, page = [], 1
    endpoint = f"{base}/websites/{wid}/event-data?{q}&eventName={event_key}"
    while page <= MAX_PAGES:
        payload, err = _get_retry(f"{endpoint}&page={page}", headers, token)
        if payload is None:
            meta["reason"] = err or "Antwort leer"
            meta["endpoint"] = "event-data"
            if rows:
                break                      # Teilbestand ist besser als nichts
            return None, meta
        got = _rows_from_event_data(payload)
        rows += got
        meta["endpoint"] = "event-data"
        total = payload.get("count") if isinstance(payload, dict) else None
        if len(got) < PAGE_SIZE or (total is not None and len(rows) >= int(total)):
            break
        page += 1
    # 2) Fallback: Zeitreihe (nur Aggregat). Nur wenn Schritt 1 nichts lieferte.
    if not rows:
        payload, err = _get_retry(
            f"{base}/websites/{wid}/events?{q}&eventType=event&eventKey={event_key}&unit=day",
            headers, token)
        if payload is not None:
            rows = _rows_from_series(payload)
            meta["endpoint"] = "events(series)"
            if rows:
                meta["reason"] = ("nur Aggregat: Umami liefert keine Event-Eigenschaften "
                                  "über diesen Endpunkt – Attribute `slug/article/pillar` "
                                  "werden am Link gesetzt und hier erst mit `/event-data` nutzbar")
        elif err:
            meta["reason"] = _redact(err, token)
    meta["rows"] = len(rows)
    meta["total"] = sum(r["count"] for r in rows)
    return rows, meta


def _write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def cmd_fetch(days, strict, dry_run):
    rows, meta = fetch(days=days)
    if rows is None:
        why = meta.get("reason") or "unbekannt"
        print(f"ℹ️  Umami-Klicks nicht geladen: {why}")
        print("    Folgen: Dashboard-Export von Hand nach `data/umami_clicks.json` "
              "legen ODER GitHub-Secret `UMAMI_API_TOKEN` setzen "
              "(Website-ID steht bereits in `hugo.toml`).")
        _write_atomic(META, json.dumps({**meta, "status": "skipped"}, ensure_ascii=False, indent=2) + "\n")
        if strict:
            print("::error::--strict gesetzt: Datenlücke gilt als Fehler.")
            return 1
        return 0
    agg = aggregate(rows)
    print(f"📈 {len(agg)} Attributionen, {meta['total']} Affiliate-Klicks "
          f"(Quelle: {meta['endpoint']}, Fenster {days}d)")
    if not dry_run:
        _write_atomic(OUT, json.dumps(agg, ensure_ascii=False, indent=2) + "\n")
        _write_atomic(META, json.dumps({**meta, "status": "ok", "written": TODAY.isoformat()},
                                       ensure_ascii=False, indent=2) + "\n")
        print(f"→ geschrieben: {os.path.relpath(OUT, BLOG_DIR)} "
              f"({len(agg)} Zeilen) + {os.path.relpath(META, BLOG_DIR)}")
    try:
        from audit_log import log_event
        log_event(module="umami_clicks", action="fetch", input={"days": days, "endpoint": meta["endpoint"]},
                  output={"rows": len(agg), "clicks": meta["total"]}, status="ok")
    except Exception:  # noqa: BLE001
        pass
    if meta.get("reason"):
        print(f"⚠️  Hinweis zur Datenqualität: {meta['reason']}")
    return 0


def cmd_status():
    meta = {}
    try:
        meta = json.load(open(META, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    rows = []
    try:
        rows = json.load(open(OUT, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    clicks = sum(int(r.get("count") or 0) for r in rows if isinstance(r, dict))
    print("Umami-Klickpipeline")
    print(f"  Website-ID (hugo.toml): {'gesetzt' if website_id() else 'fehlt'}")
    print(f"  API-Token:              {'gesetzt' if api_token() else 'fehlt'}")
    print(f"  Bestand:                {len(rows)} Attributionen, {clicks} Klicks")
    print(f"  Letzter Import:         {meta.get('written', meta.get('attempted', 'nie'))} "
          f"({meta.get('status', 'unbekannt')})")
    if meta.get("reason"):
        print(f"  Grund des letzten Fehlversuchs: {meta['reason']}")
    return 0


# ------------------------------------------------------------------ Selftest

def _selftest():
    failures = []
    # --- Schema A: eventProperties als Liste (Umami Cloud v1)
    payload = {"count": 3, "data": [
        {"eventId": "e1", "eventName": "affiliate_click",
         "eventProperties": [{"dataKey": "slug", "stringValue": "check24-gas", "numberValue": None},
                             {"dataKey": "article", "stringValue": "content/posts/2026-08-16-gas-anbieter-wechseln/index.md"},
                             {"dataKey": "pillar", "stringValue": "strom-sparen"}]},
        {"eventId": "e2", "eventName": "affiliate_click",
         "eventProperties": [{"dataKey": "slug", "stringValue": "check24-gas"},
                             {"dataKey": "pillar", "stringValue": "strom-sparen"}]},
        {"eventId": "e3", "eventName": "affiliate_click", "eventProperties": []},
    ]}
    rows = _rows_from_event_data(payload)
    if len(rows) != 3:
        failures.append(f"eventProperties-Liste: erwartet 3 Zeilen, erhalten {len(rows)}")
    if rows[0]["pillar"] != "strom-sparen" or rows[0]["slug"] != "check24-gas":
        failures.append("Eigenschaften werden falsch zugeordnet")
    # identische Zeilen bündeln, unterschiedliche Artikel bleiben getrennt
    agg = aggregate(rows + [rows[0]])
    if sum(r["count"] for r in agg) != 4:
        failures.append(f"Aggregation verliert Zähler: {agg}")
    top = agg[0]
    if top["count"] != 2 or top["slug"] != "check24-gas":
        failures.append(f"doppelte Zeile nicht gebündelt: {top}")
    if len(agg) != 3:
        failures.append(f"Granularität (slug, article, pillar) nicht erhalten: {len(agg)} Gruppen")
    # --- Schema B: flache Eigenschaften (ältere/self-hosted Varianten)
    flat = {"data": [{"slug": "awin-konto", "article": "a.md", "pillar": "konto-karten", "count": 7}]}
    rows_b = _rows_from_event_data(flat)
    if not rows_b or rows_b[0]["count"] != 7:
        failures.append("flache Eigenschaften werden nicht gelesen")
    # --- Schema C: Zeitreihen-Fallback
    series = {"data": {"x": ["2026-09-01", "2026-09-02"], "y": [12, 5]}}
    rows_c = _rows_from_series(series)
    if sum(r["count"] for r in rows_c) != 17:
        failures.append("Zeitreihen-Fallback zählt falsch")
    # --- Müll darf nicht crashen, sondern liefert leere Listen
    for bad in (None, [], {"data": "apfelsaft"}, {"data": [1, "x", None]}):
        try:
            _rows_from_event_data(bad)
            _rows_from_series(bad)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"Müll-Payload {bad!r} wirft {exc.__class__.__name__}")
    # --- Kürzung/Identifikator-Schutz
    long_rows = [{"slug": "x" * 300, "article": "y" * 300, "pillar": "z" * 300, "count": 1}]
    for r in aggregate(long_rows):
        if any(len(str(v)) > 120 for v in (r["slug"], r["article"], r["pillar"])):
            failures.append("Felder werden nicht gekürzt (Datenschutz)")
    # --- Konfigurationsquelle: Website-ID aus hugo.toml
    wid = website_id()
    if not re.fullmatch(r"[0-9a-fA-F\-]{8,}", wid or ""):
        failures.append(f"websiteId nicht aus hugo.toml lesbar: {wid!r}")
    # --- Redaction: Token darf in keiner Fehlermeldung auftauchen
    tok = "umami_SUPERGEHEIM_123"
    if tok in _redact(f"fetch failed for {tok} at api.umami.is", tok):
        failures.append("Token im Log sichtbar")
    # --- Ehrliche Degradation: ohne Token => rows None, Grund dokumentiert, Exit 0
    _env = dict(os.environ)
    try:
        for k in ("UMAMI_API_TOKEN", "UMAMI_API_KEY"):
            os.environ.pop(k, None)
        rows_none, meta = fetch(days=30)
        if rows_none is not None or "UMAMI_API_TOKEN" not in meta.get("reason", ""):
            failures.append("ohne Token wird keine Datenlücke dokumentiert")
    finally:
        os.environ.clear()
        os.environ.update(_env)
    if failures:
        print("❌ UMAMI-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ UMAMI-SELFTEST bestanden (Payload-Schemata, Aggregation, Datenschutz, "
          "Konfigurationsquelle, ehrliche Degradation).")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--status" in argv:
        return cmd_status()
    days = 90
    if "--days" in argv:
        try:
            days = max(1, min(365, int(argv[argv.index("--days") + 1])))
        except (ValueError, IndexError):
            pass
    return cmd_fetch(days=days, strict="--strict" in argv, dry_run="--dry-run" in argv)


if __name__ == "__main__":
    sys.exit(main())
