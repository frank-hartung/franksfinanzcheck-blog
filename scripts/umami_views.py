#!/usr/bin/env python3
"""
UMAMI-VIEWS – Seitenaufrufe je URL automatisch holen (Nenner der Klick-Trichter)

WARUM: Die Umsatzmessung braucht zwei Zahlen, die nur zusammen Sinn ergeben:
Klicks auf /go/-Partnerlinks (`umami_clicks.py`) UND Besuche der Seiten, auf
denen diese Klicks passieren können. Ohne Besuche gibt es keine
Outbound-CTR (Klicks ÷ Besuche), keinen Umsatz pro 100 Besuche und keine
Antwort auf die Frage „wenig Klicks = wenig Traffic oder schwacher CTA?".
`scripts/revenue_funnel.py` rechnet genau diesen Trichter – und diese Datei
liefert ihm den Nenner.

DIESES SKRIPT:
  1. Liest Website-ID + Token wie `umami_clicks.py` (hugo.toml + Environment) –
     eine Wahrheit, kein zweiter Konfigurationsort.
  2. Holt `/pages` (Besuche je URL) und `/total` (Seitenaufrufe, Besuche,
     Besucher) über die Umami-API (Cloud `https://api.umami.is/v1` mit
     `x-umami-api-key`, selbst-gehostet via `UMAMI_API_BASE`).
  3. Schreibt `data/umami_views.json` (nur Pfade + Zähler) und
     `data/umami_views.meta.json` (Stand, Quelle, Grund eines fehlenden Imports).

DSGVO: Es landen ausschließlich **aggregierte Zähler je Pfad** im Repo –
keine IPs, keine User-IDs, keine Referrer, keine Session-Rohevents. Query-/
Fragment-Parameter werden vor der Aggregation entfernt, Token werden nie
geloggt und nie in Dateien geschrieben.

EHRLICHE DEGRADATION (identische Hausregel wie umami_clicks.py):
  - Kein Token   → Hinweis + Exit 0; die Meta-Datei dokumentiert den Grund
                   („unbekannt" ≠ „0 Besuche").
  - API krank    → letzter Bestand bleibt erhalten; ein Analytics-Ausfall
                   darf nie wie „0 Besuche" aussehen.
  - 0 Besuche    → wird als echtes Ergebnis geschrieben (mit Zeitfenster).

Nutzung:
  python3 scripts/umami_views.py --fetch            # API → data/umami_views.json
  python3 scripts/umami_views.py --fetch --days 30
  python3 scripts/umami_views.py --status
  python3 scripts/umami_views.py --selftest

Exit-Codes: 0 = befüllt oder sauber übersprungen, 1 = Fehler (bei --strict),
             2 = Selftest/Hausfehler.
"""
import datetime
import json
import os
import re
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from umami_clicks import (api_base, api_token, website_id, _get_retry,  # noqa: E402
                          _redact, _write_atomic, PAGE_SIZE)

OUT = os.path.join(BLOG_DIR, "data", "umami_views.json")
META = os.path.join(BLOG_DIR, "data", "umami_views.meta.json")

TODAY = datetime.date.today()
MAX_PAGES = 8            # /pages ist Top-N; 8×1000 Zeilen reichen jeden Blog-Korpus
KEEP_PATHS = 400         # Report-Größe: Top-Seiten genügen dem Trichter


# ------------------------------------------------------------------ Normalisieren

def norm_path(raw):
    """'https://site.de/posts/x/?utm=1#s' → '/posts/x/' – Pfad ist der Schlüssel.

    Query/Fragment runter (UTM-Kanäle dürfen dieselbe Seite nicht spalten),
    fehlende Schrägstriche ergänzen, Domain-/Pfadpräfixe kappen. Leere oder
    unsaubere Werte → '' (Zeile wird verworfen)."""
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.startswith(("http://", "https://")):
        s = urllib.parse.urlparse(s).path or "/"
    s = s.split("?", 1)[0].split("#", 1)[0]
    if not s.startswith("/"):
        s = "/" + s
    if not s.endswith("/"):
        s += "/"
    if re.search(r"[\x00-\x1f\"'<>\\]", s):
        return ""
    return s[:160]


def _to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _payload_rows(payload):
    """/pages liefert {count, data:[…]} oder (älter/self-hosted) eine schlichte Liste."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
    return []


def parse_pages(payload):
    """Rows → [{path, views, visits}]. Versteht url/path/hostname+title,
    pageViews/views, visits; ignoriert Zeilen ohne zählbaren Wert."""
    rows = {}
    for item in _payload_rows(payload):
        if not isinstance(item, dict):
            continue
        path = norm_path(item.get("url") or item.get("path") or item.get("title") or "")
        if not path:
            continue
        views = _to_int(item.get("pageViews", item.get("views")))
        visits = _to_int(item.get("visits", views))
        if views == 0 and visits == 0:
            continue
        d = rows.setdefault(path, {"path": path, "views": 0, "visits": 0})
        d["views"] += views
        d["visits"] += visits
    return sorted(rows.values(), key=lambda r: (-r["visits"], r["path"]))[:KEEP_PATHS]


def parse_total(payload):
    """/total liefert {"x": {…}} – Schlüssel je nach Version unterschiedlich."""
    data = payload.get("x") if isinstance(payload, dict) else None
    if isinstance(data, list):                     # Zeitreihen-Variante: summieren
        acc = {"pageviews": 0, "visits": 0}
        for item in data:
            if not isinstance(item, dict):
                continue
            acc["pageviews"] += _to_int(item.get("pageViews", item.get("views", item.get("y"))))
            acc["visits"] += _to_int(item.get("visits", item.get("t", item.get("x"))))
        return acc
    if not isinstance(data, dict):
        data = payload if isinstance(payload, dict) else {}
    return {"pageviews": _to_int(data.get("pageViews", data.get("totalViewsWithoutBounce",
                                                       data.get("views")))),
            "visits": _to_int(data.get("visits", data.get("t")))}


# ------------------------------------------------------------------ Fetch

def fetch(days=90):
    """→ (result|None, meta). result=None heißt: API nicht nutzbar (Bestand bleibt)."""
    token, base, wid = api_token(), api_base(), website_id()
    meta = {"attempted": TODAY.isoformat(), "base": base, "website_id_set": bool(wid),
            "token_present": bool(token), "days": days, "source": "pages+total",
            "pages": 0, "reason": ""}
    if not token or not wid:
        meta["reason"] = ("kein UMAMI_API_TOKEN" if not token else "keine websiteId in hugo.toml")
        return None, meta
    headers = {"x-umami-api-key": token, "Accept": "application/json"}
    end_ms = int(datetime.datetime.now().timestamp() * 1000)
    start_ms = end_ms - int(days) * 86_400_000
    q = urllib.parse.urlencode({"startAt": start_ms, "endAt": end_ms,
                                "limit": PAGE_SIZE, "pageSize": PAGE_SIZE})
    # 1) Seiten je URL (Seitenaufrufe + Besuche)
    pages, page = [], 1
    while page <= MAX_PAGES:
        payload, err = _get_retry(f"{base}/websites/{wid}/pages?{q}&page={page}",
                                  headers, token)
        if payload is None:
            if not pages:
                meta["reason"] = _redact(err or "Antwort leer", token)
                return None, meta
            break                                        # Teilbestand ist besser als nichts
        got = parse_pages(payload)
        pages += got
        if len(got) < PAGE_SIZE or not got:
            break
        page += 1
    # 2) Gesamtzahlen (Seitenaufrufe/Besuche über die ganze Website)
    totals = {"pageviews": 0, "visits": 0}
    payload, err = _get_retry(f"{base}/websites/{wid}/total?{q}&eventType=page", headers, token)
    if payload is not None:
        totals = parse_total(payload)
    elif err and not pages:
        meta["reason"] = _redact(err, token)
    if not totals.get("visits") and pages:
        # /total krank oder leer: Summe aus den Seitendaten als redlicher Ersatz.
        totals = {"pageviews": sum(r["views"] for r in pages),
                  "visits": sum(r["visits"] for r in pages)}
        meta["reason"] = "totals aus Seiten-Summe (/total nicht nutzbar)"
    meta["pages"] = len(pages)
    meta["views"] = totals.get("pageviews", 0)
    meta["visits"] = totals.get("visits", 0)
    return {"generated": TODAY.isoformat(), "days": days,
            "totals": totals, "pages": pages}, meta


def cmd_fetch(days, strict, dry_run):
    result, meta = fetch(days=days)
    if result is None:
        why = meta.get("reason") or "unbekannt"
        print(f"ℹ️  Umami-Seitenaufrufe nicht geladen: {why}")
        print("    Folgen: Trichter- Kennzahlen (Outbound-CTR, Umsatz pro 100 Besuche) "
              "bleiben unbekannt. Abhilfe: GitHub-Secret `UMAMI_API_TOKEN` setzen "
              "(Anleitung: docs/UMSATZ-MESSUNG-PREMIUM.md).")
        _write_atomic(META, json.dumps({**meta, "status": "skipped"},
                                       ensure_ascii=False, indent=2) + "\n")
        if strict:
            print("::error::--strict gesetzt: Datenlücke gilt als Fehler.")
            return 1
        return 0
    print(f"📄 {meta['pages']} Seitenpfade · {meta['views']} Seitenaufrufe · "
          f"{meta['visits']} Besuche (Fenster {days}d)")
    if not dry_run:
        _write_atomic(OUT, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        _write_atomic(META, json.dumps({**meta, "status": "ok",
                                        "written": TODAY.isoformat()},
                                       ensure_ascii=False, indent=2) + "\n")
        print(f"→ geschrieben: {os.path.relpath(OUT, BLOG_DIR)} + "
              f"{os.path.relpath(META, BLOG_DIR)}")
    try:
        from audit_log import log_event
        log_event(module="umami_views", action="fetch",
                  input={"days": days}, output={"pages": meta["pages"],
                  "views": meta["views"], "visits": meta["visits"]}, status="ok")
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
    views = {}
    try:
        views = json.load(open(OUT, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    totals = views.get("totals") or {}
    print("Umami-Views-Pipeline")
    print(f"  Website-ID (hugo.toml): {'gesetzt' if website_id() else 'fehlt'}")
    print(f"  API-Token:              {'gesetzt' if api_token() else 'fehlt'}")
    print(f"  Bestand:                {len(views.get('pages') or [])} Pfade · "
          f"{totals.get('pageviews', 0)} Aufrufe · {totals.get('visits', 0)} Besuche")
    print(f"  Letzter Import:         {meta.get('written', meta.get('attempted', 'nie'))} "
          f"({meta.get('status', 'unbekannt')})")
    if meta.get("reason"):
        print(f"  Hinweis:                {meta['reason']}")
    return 0


# ------------------------------------------------------------------ Selftest

def _selftest():
    failures = []
    # --- Pfad-Normalisierung: Query/Fragment/Domain runter, Slash dazu
    for raw, want in (("https://franksfinanzcheck.de/posts/x/?utm_source=a", "/posts/x/"),
                      ("/pillar/strom", "/pillar/strom/"),
                      ("/", "/"),
                      ("", ""),
                      ("/a\" onmouseover=alert(1)/", ""),
                      ("/ok#frag", "/ok/")):
        got = norm_path(raw)
        if got != want:
            failures.append(f"norm_path({raw!r}) = {got!r}, erwartet {want!r}")
    # --- /pages: Cloud-Format {count, data:[…]}
    cloud = {"count": 3, "data": [
        {"url": "/posts/a/", "pageViews": 100, "visits": 70, "bounces": 5},
        {"url": "/pillar/strom-sparen", "pageViews": 40, "visits": 30},
        {"url": "/datenschutz/", "pageViews": 0, "visits": 0},
    ]}
    rows = parse_pages(cloud)
    if [r["path"] for r in rows] != ["/posts/a/", "/pillar/strom-sparen/"]:
        failures.append(f"parse_pages Pfade: {rows}")
    if not rows or rows[0]["views"] != 100 or rows[0]["visits"] != 70:
        failures.append("parse_pages Zähler")
    # --- doppelte Pfade (Query-Varianten) verschmelzen auf einen Schlüssel
    dup = {"data": [{"url": "/x/?a=1", "pageViews": 3}, {"url": "/x/?b=2", "pageViews": 4}]}
    rows2 = parse_pages(dup)
    if len(rows2) != 1 or rows2[0]["views"] != 7:
        failures.append(f"Query-Varianten nicht zusammengeführt: {rows2}")
    # --- self-hosted Listenformat + Titel-Pfade
    flat = {"data": [{"path": "/posts/b/", "views": 9, "visits": 9}]}
    if parse_pages(flat)[0]["views"] != 9:
        failures.append("flaches Seitenformat nicht gelesen")
    # --- /total Formate
    t1 = parse_total({"x": {"pageViews": 555, "visits": 321}})
    if t1 != {"pageviews": 555, "visits": 321}:
        failures.append(f"total dict: {t1}")
    t2 = parse_total({"x": [{"t": 2, "y": 5}, {"t": 3, "y": 7}]})
    if t2["visits"] != 5 or t2["pageviews"] != 12:
        failures.append(f"total list: {t2}")
    t3 = parse_total({})
    if t3 != {"pageviews": 0, "visits": 0}:
        failures.append("total leer soll 0/0 sein")
    # --- Müll darf nicht crashen
    for bad in (None, [], [1, None, "x"], {"data": "apfelsaft"}):
        try:
            parse_pages(bad)
            parse_total(bad)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"Müll-Payload {bad!r} wirft {exc.__class__.__name__}")
    # --- Ehrliche Degradation: ohne Token => None + Grund, keine Null-Besuche
    saved = dict(os.environ)
    try:
        for k in ("UMAMI_API_TOKEN", "UMAMI_API_KEY"):
            os.environ.pop(k, None)
        res, meta = fetch(days=30)
        if res is not None or "UMAMI_API_TOKEN" not in meta.get("reason", ""):
            failures.append("ohne Token wird keine Datenlücke dokumentiert")
    finally:
        os.environ.clear()
        os.environ.update(saved)
    # --- Konfigurationsquelle geteilt mit Klick-Pipeline (hugo.toml)
    if website_id() and not re.fullmatch(r"[0-9a-fA-F\-]{8,}", website_id()):
        failures.append("websiteId unplausibel")
    # --- Redaction: Token darf nirgends im Log auftauchen
    tok = "umami_GEHEIM_views_9"
    if tok in _redact(f"boom for {tok}", tok):
        failures.append("Token im Log sichtbar")
    if failures:
        print("❌ UMAMI-VIEWS-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ UMAMI-VIEWS-SELFTEST bestanden (Pfad-Normalisierung, Formate, "
          "Aggregation, ehrliche Degradation, Datenschutz).")
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
