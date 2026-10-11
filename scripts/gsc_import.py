#!/usr/bin/env python3
"""
GSC-IMPORT – holt Search-Console-Leistungsdaten automatisch über die Search Console API.

WARUM: Die Search Console ist kostenlos. Ihre API ist für dieses Projekt kostenlos nutzbar.
Ein Dienstkonto (Service Account) liest die Daten ohne Anmeldung einer Person und ohne Cookies.
Das Repo bekommt täglich aggregierte Zahlen. Das Verhältnis zur Quelle bleibt dabei lesend.

AUFRUF:
  python3 scripts/gsc_import.py --sites            # Einrichtungs-Check: welche Properties sieht das Dienstkonto?
  python3 scripts/gsc_import.py                    # täglicher Import (letzte 90 Tage + Top-Seiten/-Suchbegriffe 28 Tage)
  python3 scripts/gsc_import.py --backfill         # Erstbefüllung: maximal 16 Monate (480 Tage)
  python3 scripts/gsc_import.py --selftest         # Offline-Selbsttest (Signatur mit echtem openssl, Pagination, Merge)

ZUGANG (nur als Umgebungsvariablen bzw. GitHub-Secrets, nie im Repo):
  GSC_SITE_URL                 z. B. "sc-domain:franksfinanzcheck.de" oder "https://franksfinanzcheck.de/"
  GSC_SERVICE_ACCOUNT_JSON     Inhalt der JSON-Schlüsseldatei des Dienstkontos
  (lokal alternativ GSC_SERVICE_ACCOUNT_FILE=/pfad/zur/datei.json)
  Die Dienstkonto-E-Mail muss in der Search Console als Nutzer mit „Eingeschränkt“ eingetragen sein.
  Fehlt ein Wert, schreibt der Import den Status „nicht_konfiguriert“ und endet mit Exit 0.

AUSGABE (alles aggregiert, keine Personenbezüge):
  data/gsc/tagesdaten.jsonl        Klicks/Impressionen/CTR/Position je Tag – wächst dauerhaft (über die 16-Monats-Grenze hinaus)
  data/gsc/top_seiten_28t.json     Top-500-Seiten, letzte 28 Tage
  data/gsc/top_suchbegriffe_28t.json  Top-500-Suchbegriffe, letzte 28 Tage
  data/gsc/meta.json               Stand, Zeitraum, Status

DATENLAGE: Google liefert finale Daten mit ca. 2–3 Tagen Verzögerung. Der Import endet deshalb drei Tage vor heute.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "gsc"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SITES_URL = "https://www.googleapis.com/webmasters/v3/sites"
QUERY_TMPL = "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
VERZOEGERUNG_TAGE = 3
ZEILEN_PRO_SEITE = 25000


class GscFehler(RuntimeError):
    pass


# ---------------------------------------------------------------- JWT / Signatur

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def rs256_signatur(nachricht: bytes, private_key_pem: str) -> bytes:
    """RS256-Signatur über das installierte openssl (keine Zusatz-Pakete nötig)."""
    with tempfile.TemporaryDirectory() as tmp:
        key_path = Path(tmp) / "key.pem"
        key_path.write_text(private_key_pem, encoding="utf-8")
        os.chmod(key_path, 0o600)
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", str(key_path)],
            input=nachricht, capture_output=True, check=False,
        )
    if proc.returncode != 0:
        raise GscFehler("Signatur mit openssl fehlgeschlagen (Schlüssel prüfen)")
    return proc.stdout


def jwt_assertion(sa: dict, jetzt: int, sign=rs256_signatur) -> str:
    kopf = {"alg": "RS256", "typ": "JWT"}
    nutzlast = {
        "iss": sa["client_email"],
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": jetzt,
        "exp": jetzt + 3600,
    }
    teile = _b64url(json.dumps(kopf, separators=(",", ":")).encode()) + "." + \
        _b64url(json.dumps(nutzlast, separators=(",", ":")).encode())
    signatur = sign(teile.encode("ascii"), sa["private_key"])
    return teile + "." + _b64url(signatur)


# ---------------------------------------------------------------- HTTP

HttpFn = None  # Platzhalter für Typhinweise; tatsächlich: (method, url, headers, body) -> (status, dict)


def default_http(method: str, url: str, headers: dict, body: bytes | None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return e.code, {}


def hole_token(http, sa: dict, jetzt: int, sign=rs256_signatur) -> str:
    assertion = jwt_assertion(sa, jetzt, sign)
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode()
    status, antwort = http("POST", TOKEN_URL,
                           {"Content-Type": "application/x-www-form-urlencoded"}, body)
    if status != 200 or "access_token" not in antwort:
        # Fehlertext ohne Schlüsselmaterial weitergeben
        grund = antwort.get("error_description") or antwort.get("error") or f"HTTP {status}"
        raise GscFehler(f"Token-Abruf fehlgeschlagen: {grund}")
    return antwort["access_token"]


def _api(http, token: str, method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    status, antwort = http(method, url, headers, data)
    if status != 200:
        fehler = (antwort.get("error") or {}).get("message") or f"HTTP {status}"
        raise GscFehler(f"Search-Console-API: {fehler}")
    return antwort


def hole_sites(http, token: str) -> list[dict]:
    return _api(http, token, "GET", SITES_URL).get("siteEntry", [])


def hole_zeilen(http, token: str, site: str, start: dt.date, ende: dt.date,
                dimensionen: list[str], max_zeilen: int = 50000) -> list[dict]:
    """Paginiert searchAnalytics.query bis max_zeilen oder bis keine Zeilen mehr kommen."""
    url = QUERY_TMPL.format(site=urllib.parse.quote(site, safe=""))
    zeilen: list[dict] = []
    start_zeile = 0
    while len(zeilen) < max_zeilen:
        body = {
            "startDate": start.isoformat(),
            "endDate": ende.isoformat(),
            "dimensions": dimensionen,
            "rowLimit": ZEILEN_PRO_SEITE,
            "startRow": start_zeile,
            "dataState": "final",
        }
        antwort = _api(http, token, "POST", url, body)
        rows = antwort.get("rows") or []
        zeilen.extend(rows)
        if len(rows) < ZEILEN_PRO_SEITE:
            break
        start_zeile += ZEILEN_PRO_SEITE
    return zeilen[:max_zeilen]


# ---------------------------------------------------------------- Aufbereitung

def tages_zeilen(rows: list[dict]) -> dict[str, dict]:
    """API-Zeilen (dimensions=[date]) → {YYYY-MM-DD: {clicks, impressions, ctr, position}}."""
    out = {}
    for r in rows:
        keys = r.get("keys") or []
        if not keys:
            continue
        out[keys[0]] = {
            "clicks": int(r.get("clicks") or 0),
            "impressions": int(r.get("impressions") or 0),
            "ctr": round(float(r.get("ctr") or 0.0), 4),
            "position": round(float(r.get("position") or 0.0), 2),
        }
    return out


def top_zeilen(rows: list[dict], dimension: str, limit: int = 500) -> list[dict]:
    out = []
    for r in rows[:limit]:
        keys = r.get("keys") or [""]
        out.append({
            dimension: keys[0],
            "clicks": int(r.get("clicks") or 0),
            "impressions": int(r.get("impressions") or 0),
            "ctr": round(float(r.get("ctr") or 0.0), 4),
            "position": round(float(r.get("position") or 0.0), 2),
        })
    return out


def merge_tagesdaten(bestand: dict[str, dict], neu: dict[str, dict]) -> dict[str, dict]:
    """Neue Tage überschreiben alte (Google korrigiert die letzten Tage nach); ältere bleiben erhalten."""
    gemergt = dict(bestand)
    gemergt.update(neu)
    return dict(sorted(gemergt.items()))


def lies_tagesdaten(pfad: Path) -> dict[str, dict]:
    if not pfad.exists():
        return {}
    out = {}
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        rec = json.loads(zeile)
        out[rec["datum"]] = {k: v for k, v in rec.items() if k != "datum"}
    return out


def schreibe_tagesdaten(pfad: Path, daten: dict[str, dict]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("w", encoding="utf-8") as f:
        for datum, werte in daten.items():
            f.write(json.dumps({"datum": datum, **werte}, ensure_ascii=False) + "\n")


def _berlin_heute(now: dt.datetime) -> dt.date:
    from zoneinfo import ZoneInfo
    return now.astimezone(ZoneInfo("Europe/Berlin")).date()


# ---------------------------------------------------------------- Lauf

def lauf(tage: int, http=default_http, env: dict | None = None, out_dir: Path = OUT_DIR,
         now: dt.datetime | None = None, sign=rs256_signatur) -> dict:
    env = os.environ if env is None else env
    now = now or dt.datetime.now(dt.timezone.utc)
    site = env.get("GSC_SITE_URL", "").strip()
    sa_text = env.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    sa_datei = env.get("GSC_SERVICE_ACCOUNT_FILE", "").strip()
    ende = _berlin_heute(now) - dt.timedelta(days=VERZOEGERUNG_TAGE)
    start = ende - dt.timedelta(days=tage - 1)
    meta = {
        "stand": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quelle": "google-search-console-api (Dienstkonto, nur lesen)",
        "site": site or None,
        "zeitraum": {"von": start.isoformat(), "bis": ende.isoformat()},
        "status": "ok",
        "grund": "",
        "datenschutz": "nur aggregierte Kennzahlen je Tag, Seite oder Suchbegriff; keine Nutzerkennungen",
    }

    if not (site and (sa_text or sa_datei)):
        meta["status"] = "nicht_konfiguriert"
        meta["grund"] = "GSC_SITE_URL und GSC_SERVICE_ACCOUNT_JSON (oder _FILE) fehlen"
        _schreibe_meta(out_dir, meta)
        return meta

    try:
        sa = json.loads(sa_text) if sa_text else json.loads(Path(sa_datei).read_text(encoding="utf-8"))
        token = hole_token(http, sa, int(now.timestamp()), sign)
        tage_daten = hole_zeilen(http, token, site, start, ende, ["date"])
        neu = tages_zeilen(tage_daten)
        bestand = lies_tagesdaten(out_dir / "tagesdaten.jsonl")
        gemergt = merge_tagesdaten(bestand, neu)
        schreibe_tagesdaten(out_dir / "tagesdaten.jsonl", gemergt)

        k28 = ende - dt.timedelta(days=27)
        seiten = hole_zeilen(http, token, site, k28, ende, ["page"], max_zeilen=500)
        suche = hole_zeilen(http, token, site, k28, ende, ["query"], max_zeilen=500)
        (out_dir / "top_seiten_28t.json").write_text(
            json.dumps(top_zeilen(seiten, "seite"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out_dir / "top_suchbegriffe_28t.json").write_text(
            json.dumps(top_zeilen(suche, "suchbegriff"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        meta["tage_neu"] = len(neu)
        meta["tage_gesamt"] = len(gemergt)
        meta["klicks_zeitraum"] = sum(v["clicks"] for v in neu.values())
    except GscFehler as e:
        meta["status"] = "fehler"
        meta["grund"] = str(e)
    _schreibe_meta(out_dir, meta)
    return meta


def _schreibe_meta(out_dir: Path, meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sites_check(http=default_http, env: dict | None = None, now: dt.datetime | None = None,
                sign=rs256_signatur) -> int:
    env = os.environ if env is None else env
    now = now or dt.datetime.now(dt.timezone.utc)
    site = env.get("GSC_SITE_URL", "").strip()
    sa_text = env.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    sa_datei = env.get("GSC_SERVICE_ACCOUNT_FILE", "").strip()
    if not (sa_text or sa_datei):
        print("❌ GSC_SERVICE_ACCOUNT_JSON fehlt.")
        return 1
    try:
        sa = json.loads(sa_text) if sa_text else json.loads(Path(sa_datei).read_text(encoding="utf-8"))
        token = hole_token(http, sa, int(now.timestamp()), sign)
        eintraege = hole_sites(http, token)
    except GscFehler as e:
        print(f"❌ {e}")
        return 1
    if not eintraege:
        print("⚠️  Dienstkonto sieht keine Property. In der Search Console unter „Einstellungen → Nutzer und Berechtigungen“ die Dienstkonto-E-Mail eintragen.")
        return 1
    print("Sichtbare Properties:")
    for e in eintraege:
        print(f"  - {e.get('siteUrl')}  ({e.get('permissionLevel')})")
    if site and site not in [e.get("siteUrl") for e in eintraege]:
        print(f"❌ GSC_SITE_URL „{site}“ ist nicht darunter. Exakt so eintragen, wie oben angezeigt.")
        return 1
    print("✅ Einrichtung in Ordnung.")
    return 0


# ---------------------------------------------------------------- Selbsttest

def _selftest() -> int:
    fehler: list[str] = []

    # 1) Signatur: echte RS256-Signatur mit openssl, Gegenprobe mit openssl verify
    with tempfile.TemporaryDirectory() as tmp:
        key = Path(tmp) / "k.pem"
        pub = Path(tmp) / "p.pem"
        subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], capture_output=True, check=True)
        subprocess.run(["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(pub)], capture_output=True, check=True)
        sa = {"client_email": "test@x.iam.gserviceaccount.com", "private_key": key.read_text()}
        jwt = jwt_assertion(sa, 1_700_000_000)
        kopf, nutzlast, sig = jwt.split(".")
        if len(jwt.split(".")) != 3 or "=" in jwt:
            fehler.append("JWT-Form falsch (3 Teile, ohne Padding erwartet)")
        msg = f"{kopf}.{nutzlast}".encode()
        sig_bytes = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
        sig_datei = Path(tmp) / "s.bin"
        msg_datei = Path(tmp) / "m.bin"
        sig_datei.write_bytes(sig_bytes)
        msg_datei.write_bytes(msg)
        ver = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(sig_datei), str(msg_datei)],
                             capture_output=True, text=True)
        if ver.returncode != 0:
            fehler.append("RS256-Signatur wird von openssl nicht bestätigt")

    # 2) Fake-API: Token, Pagination (zwei Seiten bei Tagesdaten), Top-Listen
    seiten_zaehler = {"n": 0}
    tag_zeilen = [{"keys": [f"2026-08-{i:02d}"], "clicks": i, "impressions": 10 * i, "ctr": 0.1, "position": 5.5}
                  for i in range(1, 11)]

    def fake(method, url, headers, body):
        if url == TOKEN_URL:
            return 200, {"access_token": "t-abc"}
        if url == SITES_URL:
            return 200, {"siteEntry": [{"siteUrl": "sc-domain:franksfinanzcheck.de", "permissionLevel": "siteRestrictedUser"}]}
        if "searchAnalytics/query" in url:
            b = json.loads(body)
            if b["dimensions"] == ["date"]:
                # Paginierung simulieren: rowLimit künstlich klein → hier 10 Zeilen, Limit 25000 → Ende nach Seite 1
                return 200, {"rows": tag_zeilen}
            seiten_zaehler["n"] += 1
            return 200, {"rows": [{"keys": ["https://franksfinanzcheck.de/posts/a/"], "clicks": 7, "impressions": 70, "ctr": 0.1, "position": 3.0}]}
        return 404, {}

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        # vorhandener Bestand mit einem älteren Tag, der erhalten bleiben muss (über 16-Monats-Grenze hinaus)
        schreibe_tagesdaten(out / "tagesdaten.jsonl", {"2024-01-01": {"clicks": 1, "impressions": 2, "ctr": 0.5, "position": 9.0}})
        env = {"GSC_SITE_URL": "sc-domain:franksfinanzcheck.de", "GSC_SERVICE_ACCOUNT_JSON": json.dumps(sa)}
        meta = lauf(10, http=fake, env=env, out_dir=out, now=dt.datetime(2026, 10, 11, 10, tzinfo=dt.timezone.utc), sign=lambda m, k: b"x")
        if meta["status"] != "ok":
            fehler.append(f"Fake-Lauf Status {meta['status']}: {meta.get('grund')}")
        gesamt = lies_tagesdaten(out / "tagesdaten.jsonl")
        if "2024-01-01" not in gesamt:
            fehler.append("Altbestand (älter als 16 Monate) wurde gelöscht – Merge ist nicht dauerhaft")
        if gesamt.get("2026-08-10", {}).get("clicks") != 10:
            fehler.append("Tageswerte nicht korrekt übernommen")
        if not (out / "top_seiten_28t.json").exists() or not (out / "top_suchbegriffe_28t.json").exists():
            fehler.append("Top-Listen fehlen")
        if not (out / "meta.json").exists():
            fehler.append("meta.json fehlt")
        meta_text = (out / "meta.json").read_text(encoding="utf-8")
        if "t-abc" in meta_text or "PRIVATE" in meta_text:
            fehler.append("Geheimnis taucht in meta.json auf")

    # 2b) Paginierung: Seitengröße künstlich auf 2 → 5 Zeilen ergeben 3 Anfragen (startRow 0, 2, 4)
    global ZEILEN_PRO_SEITE
    alt_seitengroesse = ZEILEN_PRO_SEITE
    ZEILEN_PRO_SEITE = 2
    starts: list[int] = []

    def fake_paged(method, url, headers, body):
        b = json.loads(body)
        starts.append(b["startRow"])
        alle = [{"keys": [f"q{i}"], "clicks": 1} for i in range(5)]
        return 200, {"rows": alle[b["startRow"]:b["startRow"] + 2]}

    try:
        seiten = hole_zeilen(fake_paged, "t", "sc-domain:x.de", dt.date(2026, 1, 1), dt.date(2026, 1, 5), ["query"])
    finally:
        ZEILEN_PRO_SEITE = alt_seitengroesse
    if starts != [0, 2, 4] or len(seiten) != 5:
        fehler.append(f"Paginierung falsch: startRow={starts}, Zeilen={len(seiten)}")

    # 3) Ohne Zugang: nicht_konfiguriert, Exit-freundlich
    with tempfile.TemporaryDirectory() as tmp:
        meta = lauf(10, env={}, out_dir=Path(tmp))
        if meta["status"] != "nicht_konfiguriert":
            fehler.append("ohne Zugang muss der Status nicht_konfiguriert sein")

    # 4) Tages-Merge: neue Werte überschreiben alte, Altes bleibt
    m = merge_tagesdaten({"2026-01-01": {"clicks": 1}, "2026-01-02": {"clicks": 2}}, {"2026-01-02": {"clicks": 9}})
    if m["2026-01-02"]["clicks"] != 9 or m["2026-01-01"]["clicks"] != 1:
        fehler.append("Merge-Regel verletzt")

    if fehler:
        print("❌ GSC-IMPORT-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ GSC-IMPORT-SELBSTTEST bestanden (JWT/RS256 mit openssl verifiziert, Paginierung, Merge, Geheimnisschutz, Status).")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--sites" in argv:
        return sites_check()
    tage = 480 if "--backfill" in argv else 90
    meta = lauf(tage)
    print(f"GSC-Import: Status={meta['status']} · Zeitraum {meta['zeitraum']['von']} bis {meta['zeitraum']['bis']}")
    if meta.get("grund"):
        print(f"   Grund: {meta['grund']}")
    return 1 if meta["status"] == "fehler" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
