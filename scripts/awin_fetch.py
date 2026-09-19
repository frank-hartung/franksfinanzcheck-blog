#!/usr/bin/env python3
"""
AWIN-FETCH – Awin-Transaktionen automatisch holen (Klicks → Umsatz, ohne Handarbeit)

WARUM: `scripts/awin_provisions.py` kann den Awin-Transaktions-Report (CSV)
lesen – aber der Export war bisher ein HANDWERK: Awin-Dashboard → Reports →
Transactions → CSV herunterladen → ins Repo legen. Ein manueller Schritt in
einer Automatisierung passiert nachweislich nie (Governance-Report #206 ließ
grüßen: „0.00 € Provision“, weil niemand exportiert hat). Awin stellt für
Publisher eine dokumentierte REST-API zu (https://api.awin.com,
`GET /publishers/{publisherId}/transactions/`, Bearer-Token aus dem
Awin-UI → User Settings → API Credentials). DIESES SKRIPT ersetzt den
Hand-Export durch einen nächtlichen API-Abruf.

SO FUNKTIONIERT ES:
  1. Konfiguration aus Environment: `AWIN_API_TOKEN` (Secret) +
     `AWIN_PUBLISHER_ID` (Secret oder Repo-Variable). Beides fehlt? → sauber
     übersprungen, Grund dokumentiert (eine Agentur scheitert hörbar, nicht still).
  2. Abruf in Zeitfenstern ≤ 31 Tagen (Awin-Limit je Request), paginiert
     (limit/offset), mit Backoff auf 429/5xx.
  3. Antwort-Felder (Cent-Beträge → Euro) werden in exakt das CSV-Schema
     gemappt, das `awin_provisions.py` bereits versteht:
     Transaction ID, Transaction Date, Click Reference, Commission,
     Order Value, Commission Status, Currency, Programme.
  4. Ergebnis nach `data/awin_transactions.csv` (Standard) – die rohe Datei
     liegt in gitignore; der Workflow lässt sie im Lauf-Verzeichnis und
     speist sie per `--awin-csv` direkt in die Provisionen-Wache.

DATENSCHUTZ/Compliance:
  - Awin liefert Publishern KEINE Käuferdaten; die Datei enthält Transaction-/
    Click-Referenzen, Beträge, Daten und Status – keine IP, kein Name.
  - Token: nie im Log, nie in Dateien (Redaction wie in umami_clicks.py).
  - Transaktions-IDs bleiben lokal/im Workflow-Arbeitsverzeichnis; committed
    wird nur die Aggregation `data/awin_provisions.json` (Beträge je Artikel).

EHRLICHE DEGRADATION (Hausregel der Messkette):
  - Kein Token/ID → Status „skipped“ + Grund, Bestand bleibt, Exit 0.
  - API-Fehler   → letzter Bestand bleibt (ein Awin-Ausfall darf nie wie
                   „0 Provisionen“ aussehen), Meta dokumentiert den Versuch.
  - 0 Transaktionen im Fenster → wird als echtes Ergebnis geschrieben.

Nutzung:
  python3 scripts/awin_fetch.py --fetch                # API → data/awin_transactions.csv
  python3 scripts/awin_fetch.py --fetch --days 62 --out /tmp/awin.csv
  python3 scripts/awin_fetch.py --status
  python3 scripts/awin_fetch.py --selftest

Exit: 0 = befüllt oder sauber übersprungen, 1 = Fehler (bei --strict),
      2 = Selftest/Hausfehler.
"""
import csv
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

OUT = os.path.join(BLOG_DIR, "data", "awin_transactions.csv")
META = os.path.join(BLOG_DIR, "data", "awin_fetch.meta.json")

TODAY = datetime.date.today()
DEFAULT_BASE = "https://api.awin.com"
DEFAULT_TZ = "Europe/Berlin"
PAGE_SIZE = 1000          # Awin-Doku: große Fenster drosseln; 1000 je Request
MAX_PAGES = 20            # 20k Transaktionen im Fenster = mehr als jeder Blog braucht
SLICE_DAYS = 30           # API-Limit je Request: max. 31 Tage – 30 ist die sichere Wahl
TIMEOUT = 30
RETRIES = 3
AMOUNT_DIVISOR_DEFAULT = 100   # Awin liefert Beträge in Kleinst-Einheiten (Cent)

CSV_HEADER = ("Transaction ID,Transaction Date,Click Reference,Commission,"
              "Order Value,Commission Status,Currency,Programme")


# ------------------------------------------------------------------ Konfiguration

def api_token():
    for var in ("AWIN_API_TOKEN", "AWIN_PUBLISHER_API_TOKEN"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return ""


def publisher_id():
    val = os.environ.get("AWIN_PUBLISHER_ID", "").strip()
    return val if val.isdigit() else ""


def api_base():
    return (os.environ.get("AWIN_API_BASE") or DEFAULT_BASE).strip().rstrip("/")


def timezone_name():
    return (os.environ.get("AWIN_TIMEZONE") or DEFAULT_TZ).strip()


def amount_divisor():
    try:
        d = float(os.environ.get("AWIN_AMOUNT_DIVISOR", "") or AMOUNT_DIVISOR_DEFAULT)
    except ValueError:
        d = AMOUNT_DIVISOR_DEFAULT
    return d if d > 0 else AMOUNT_DIVISOR_DEFAULT


def _redact(text, *secrets):
    out = str(text or "")
    for sec in secrets:
        if sec and len(sec) >= 4:
            out = out.replace(sec, "***")
    return out[:200]


# ------------------------------------------------------------------ HTTP

def _get(url, headers, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "franksfin-rev/1.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(8_000_000)
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
        if status in (401, 403, 404, 400):   # falsche Konfig: Retryn hilft nicht
            break
        if attempt < RETRIES:
            time.sleep(min(30, 2 * attempt * (3 if status == 429 else 1)))
    return None, last


# ------------------------------------------------------------------ Parsing

def parse_transactions(payload):
    """Awin-Antwort → Zeilen im CSV-Schema von awin_provisions.py.

    Versteht {"count": n, "transactions": [...]} (Publisher-API) und rohe
    Listen; ignoriert alles andere sang- und klanglos (nie ein Crash wegen
    Netzwerk-Müll). Beträge: Cent → Euro (Divisor konfigurierbar)."""
    rows = []
    items = None
    if isinstance(payload, dict):
        items = payload.get("transactions")
        if items is None:
            items = payload.get("data")
    elif isinstance(payload, list):
        items = payload
    if not isinstance(items, list):
        return rows
    div = amount_divisor()

    def money(v):
        try:
            return f"{(float(v) / div):.2f}"
        except (TypeError, ValueError):
            return "0.00"

    for t in items:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("transactionId") or t.get("transaction_id") or "").strip()[:40]
        clickref = str(t.get("clickRef") or t.get("clickref") or "").strip()[:120]
        if not tid and not clickref:
            continue
        date = str(t.get("transactionDate") or t.get("insertionDate") or "")[:19].replace("T", " ")
        rows.append({
            "Transaction ID": tid,
            "Transaction Date": date,
            "Click Reference": clickref,
            # commissionPaid = ausgezahlt; sonst Standard+Discount als Stand von heute
            "Commission": money(t.get("commissionPaid",
                                      float(t.get("standardCommission") or 0) +
                                      float(t.get("discountCommission") or 0))),
            "Order Value": money(t.get("saleAmount", 0)),
            "Commission Status": str(t.get("status") or "unknown")[:40],
            "Currency": str(t.get("currency") or "EUR")[:8].upper(),
            "Programme": str(t.get("advertiserName") or t.get("advertiser") or "Awin")[:80],
        })
    return rows


def status_totals(rows):
    """Kompakte Status-Zähler für Meta/Report (pending/approved/declined/deleted)."""
    out = {}
    for r in rows:
        s = (r.get("Commission Status") or "unknown").lower()
        d = out.setdefault(s, {"count": 0, "commission": 0.0})
        d["count"] += 1
        try:
            d["commission"] = round(d["commission"] + float(r.get("Commission") or 0), 2)
        except ValueError:
            pass
    return out


def slices(days):
    """Zeitfenster in ≤ SLICE_DAYS-Scheiben (heute → zurück): Liste (start,end) als
    'yyyy-MM-ddTHH:mm:ss'. Awin limitiert Requests auf 31 Tage Abstand."""
    days = max(1, min(365, int(days)))
    end = datetime.datetime.now()
    start_full = end - datetime.timedelta(days=days)
    out, cursor_end = [], end
    while cursor_end > start_full:
        cursor_start = max(start_full, cursor_end - datetime.timedelta(days=SLICE_DAYS))
        out.append((cursor_start.strftime("%Y-%m-%dT%H:%M:%S"),
                    cursor_end.strftime("%Y-%m-%dT%H:%M:%S")))
        cursor_end = cursor_start
    out.reverse()  # chronologisch (alt → neu) = deterministische CSV-Reihenfolge
    return out


# ------------------------------------------------------------------ Fetch + Schreiben

def fetch(days=90, fetcher=None):
    """→ (rows|None, meta). rows=None: API nicht nutzbar (Bestand bleibt!).

    `fetcher(url, headers)` ist nur für den Selbsttest injectierbar – die
    Produktionsbahn nutzt _get_retry (Netzwerk), der Test liefert Kunst-Antworten."""
    token, pid, base = api_token(), publisher_id(), api_base()
    meta = {"attempted": TODAY.isoformat(), "base": base, "publisher_id_set": bool(pid),
            "token_present": bool(token), "days": days, "timezone": timezone_name(),
            "rows": 0, "statuses": {}, "reason": ""}
    if not token or not pid:
        missing = []
        if not token:
            missing.append("AWIN_API_TOKEN")
        if not pid:
            missing.append("AWIN_PUBLISHER_ID")
        meta["reason"] = "fehlt: " + ", ".join(missing)
        return None, meta
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    call = fetcher or (lambda url, hdrs: _get_retry(url, hdrs, token))
    rows, errors = [], []
    for start, end in slices(days):
        offset = 0
        while offset // PAGE_SIZE < MAX_PAGES:
            q = urllib.parse.urlencode({"startDate": start, "endDate": end,
                                        "dateType": "transaction",
                                        "timezone": timezone_name(),
                                        "limit": PAGE_SIZE, "offset": offset})
            # accessToken zusätzlich als Query-Parameter: ältere Awin-Endpoints
            # kennen nur diesen Weg, neuere ignorieren ihn harmlos.
            url = (f"{base}/publishers/{pid}/transactions/?{q}"
                   f"&accessToken={urllib.parse.quote(token)}")
            payload, err = call(url, headers)
            if payload is None:
                errors.append(err or "Antwort leer")
                break
            got = parse_transactions(payload)
            rows += got
            if len(got) < PAGE_SIZE:
                break                    # letzte Seite erreicht
            offset += PAGE_SIZE
        time.sleep(0.3)  # Rate-Limit-Höflichkeit über die Slices hinweg
    if errors and not rows:
        meta["reason"] = _redact("; ".join(errors[:2]), token)
        return None, meta
    meta["rows"] = len(rows)
    meta["statuses"] = status_totals(rows)
    if errors:
        meta["reason"] = _redact("Teilbestand: " + "; ".join(errors[:2]), token)
    return rows, meta


def _write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_csv(rows, path):
    buf = [CSV_HEADER]
    for r in rows:
        vals = []
        for col in CSV_HEADER.split(","):
            v = str(r.get(col, ""))
            v = v.replace('"', "'").replace("\n", " ").replace("\r", " ")
            vals.append(f'"{v}"' if "," in v else v)
        buf.append(",".join(vals))
    _write_atomic(path, "\n".join(buf) + "\n")


def cmd_fetch(days, strict, dry_run, out):
    rows, meta = fetch(days=days)
    if rows is None:
        why = meta.get("reason") or "unbekannt"
        print(f"ℹ️  Awin-Transaktionen nicht geladen: {why}")
        print("    Folgen: Provisionen bleiben UNBEKANNT (nicht null!). Abhilfe: "
              "Awin-UI → User Settings → API Credentials → Token, dann Secrets "
              "`AWIN_API_TOKEN` + `AWIN_PUBLISHER_ID` setzen "
              "(Anleitung: docs/UMSATZ-MESSUNG-PREMIUM.md). Alternativ: CSV-Export "
              "von Hand nach `data/awin_transactions.csv` legen – die Import-Wache "
              "liest beides.")
        _write_atomic(META, json.dumps({**meta, "status": "skipped"},
                                       ensure_ascii=False, indent=2) + "\n")
        if strict:
            print("::error::--strict gesetzt: Datenlücke gilt als Fehler.")
            return 1
        return 0
    st = meta["statuses"]
    print(f"💶 {meta['rows']} Awin-Transaktionen im Fenster {days}d · Status: " +
          (", ".join(f"{k}={v['count']}" for k, v in sorted(st.items())) or "keine"))
    if not dry_run:
        write_csv(rows, out)
        _write_atomic(META, json.dumps({**meta, "status": "ok", "written": TODAY.isoformat(),
                                        "out": os.path.relpath(out, BLOG_DIR)
                                        if out.startswith(BLOG_DIR) else out},
                                       ensure_ascii=False, indent=2) + "\n")
        print(f"→ geschrieben: {out} + {os.path.relpath(META, BLOG_DIR)}")
    try:
        from audit_log import log_event
        log_event(module="awin_fetch", action="fetch", input={"days": days},
                  output={"rows": meta["rows"], "statuses": st}, status="ok")
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
    print("Awin-Import-Pipeline (Publisher API)")
    print(f"  Publisher-ID:  {'gesetzt' if publisher_id() else 'fehlt'}")
    print(f"  API-Token:     {'gesetzt' if api_token() else 'fehlt'}")
    print(f"  Letzter Abruf: {meta.get('written', meta.get('attempted', 'nie'))} "
          f"({meta.get('status', 'unbekannt')})")
    if meta.get("rows") is not None:
        statuses = ", ".join(f"{k}: {v.get('count', 0)}"
                             for k, v in (meta.get("statuses") or {}).items()) or "keine"
        print(f"  Zeilen:        {meta['rows']} ({statuses})")
    if meta.get("reason"):
        print(f"  Grund des letzten Fehlversuchs: {meta['reason']}")
    return 0


# ------------------------------------------------------------------ Selftest

def _selftest():
    failures = []
    # --- Feld-Mapping inkl. Cent → Euro
    payload = {"count": 2, "transactions": [
        {"transactionId": "T-1", "transactionDate": "2026-09-01T10:00:00",
         "clickRef": "2026-08-16-gas-anbieter-wechseln", "commissionPaid": 1500,
         "saleAmount": 10000, "status": "approved", "currency": "EUR",
         "advertiserName": "CHECK24"},
        {"transactionId": "T-2", "insertionDate": "2026-09-02 11:00:00",
         "clickRef": "", "standardCommission": 500, "discountCommission": 250,
         "saleAmount": 4999, "status": "pending", "currency": "EUR",
         "advertiserName": "CHECK24"},
    ]}
    rows = parse_transactions(payload)
    if len(rows) != 2:
        failures.append(f"erwartet 2 Zeilen, erhalten {len(rows)}")
    if rows and rows[0]["Commission"] != "15.00":
        failures.append(f"cent→euro: {rows[0]['Commission']}")
    if rows and rows[1]["Commission"] != "7.50":
        failures.append(f"standard+discount: {rows[1]['Commission']}")
    if rows and rows[0]["Click Reference"] != "2026-08-16-gas-anbieter-wechseln":
        failures.append("clickRef (SubID) geht verloren – Artikel-Zuordnung unmöglich")
    # --- Status-Aggregation
    st = status_totals(rows)
    if st.get("approved", {}).get("count") != 1 or st.get("pending", {}).get("commission") != 7.5:
        failures.append(f"status_totals: {st}")
    # --- Müll und leere Antworten crashen nie
    for bad in (None, [], "x", {"count": 1}, {"transactions": [None, 1, {"sinnlos": True}]}):
        try:
            parse_transactions(bad)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"Müll-Payload {bad!r} wirft {exc.__class__.__name__}")
    # --- Fenster-Slicing respektiert das 31-Tage-API-Limit
    sl = slices(62)
    if not sl or any(
            (datetime.datetime.strptime(e, "%Y-%m-%dT%H:%M:%S")
             - datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")).days > SLICE_DAYS for s, e in sl):
        failures.append(f"slices überschreiten {SLICE_DAYS} Tage: {sl}")
    if len(slices(1)) != 1 or len(slices(365)) > 13:
        failures.append(f"slices Anzahl unplausibel: {len(slices(1))}/{len(slices(365))}")
    if [s for s, _e in sl] != sorted([s for s, _e in sl]):
        failures.append("slices nicht chronologisch (CSV-Reihenfolge driftet)")
    # --- CSV-Rundlauf: muss von awin_provisions._read_transactions lesbar sein
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "awin.csv")
        write_csv(rows, p)
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        import awin_provisions as aw  # noqa: E402
        back = aw._read_transactions(p)
        if len(back) != 2 or back[0].get("subid") != "2026-08-16-gas-anbieter-wechseln":
            failures.append(f"CSV nicht provisions-kompatibel: {back}")
        if abs(aw._to_float(back[0].get("commission", "")) - 15.00) > 0.01:
            failures.append("Kommission geht im CSV-Rundlauf verloren")
    # --- HTTP-Error-Müll im Fetch-Pfad (injectbarer Fetcher, kein Netz)
    def fake_ok(url, hdrs):
        return payload, None
    saved = dict(os.environ)
    try:
        os.environ.update({"AWIN_API_TOKEN": "awin_GEHEIM_123", "AWIN_PUBLISHER_ID": "98765"})
        meta1 = None
        # days=20 → exakt ein Slice: der Fake-Fetcher liefert jede (einzige) Abfrage
        rows1, meta1 = fetch(days=20, fetcher=fake_ok)
        if not rows1 or meta1["rows"] != 2:
            failures.append(f"injectbarer Abruf: {meta1}")
        if "awin_GEHEIM" in json.dumps(meta1):
            failures.append("Token in Meta gelandet")

        def fake_err(url, hdrs):
            return None, "HTTP 401"
        rows2, meta2 = fetch(days=45, fetcher=fake_err)
        if rows2 is not None or "HTTP 401" not in meta2.get("reason", ""):
            failures.append("API-Fehler überschreibt nicht den Bestand-Weg")
    finally:
        os.environ.clear()
        os.environ.update(saved)
    # --- Ehrliche Degradation: ohne Secrets => skip mit Grund, nie „0 Provisionen“
    for k in ("AWIN_API_TOKEN", "AWIN_API_KEY", "AWIN_PUBLISHER_ID"):
        os.environ.pop(k, None)
    rows3, meta3 = fetch(days=30)
    if rows3 is not None or "AWIN_API_TOKEN" not in meta3.get("reason", ""):
        failures.append("ohne Token/ID wird keine Datenlücke dokumentiert")
    # --- Publisher-ID-Validierung (kein Token-Müll als ID auf Reisen)
    os.environ["AWIN_PUBLISHER_ID"] = "12ab"
    if publisher_id() != "":
        failures.append("nicht-numerische Publisher-ID wird durchgelassen")
    os.environ.pop("AWIN_PUBLISHER_ID", None)
    if failures:
        print("❌ AWIN-FETCH-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ AWIN-FETCH-SELFTEST bestanden (Feld-Mapping, Cent→Euro, 31-Tage-Slicing, "
          "CSV-Kompatibilität zur Provisions-Wache, Token-Redaction, ehrliche Degradation).")
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
    out = OUT
    if "--out" in argv:
        try:
            out = argv[argv.index("--out") + 1] or OUT
        except IndexError:
            pass
    return cmd_fetch(days=days, strict="--strict" in argv, dry_run="--dry-run" in argv, out=out)


if __name__ == "__main__":
    sys.exit(main())
