#!/usr/bin/env python3
"""
KLICK-IMPORT – holt die cookielosen /go/-Tageszähler aus Cloudflare D1
und legt sie im Format ab, das `scripts/click_attribution.py` bereits liest.

WARUM: Die Umami-API ist im kostenfreien Plan nicht verfügbar (kostenpflichtig),
deshalb ist der Umami-Import abgeschaltet. Dieser Import ersetzt ihn durch eine eigene,
kostenlose Zählung am /go/-Beacon (Worker: cloudflare/klick-zaehler).

AUFRUF:
  python3 scripts/klick_import.py                 # Import (Zeitraum: alle Tage)
  python3 scripts/klick_import.py --tage 90       # nur die letzten 90 Tage
  python3 scripts/klick_import.py --bake-keys     # Schlüsselliste für den Worker erzeugen
  python3 scripts/klick_import.py --pruefe-keys   # Drift-Check Registry ↔ Worker (Exit 1 bei Abweichung)
  python3 scripts/klick_import.py --selftest      # Offline-Selbsttest (ohne Netz)

ZUGANG (nur in GitHub Actions bzw. lokal, nie im Repo):
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_D1_DATABASE_ID, CLOUDFLARE_API_TOKEN
  Token-Recht: „Account › D1 › Read“ (nur lesen).
  Fehlt ein Wert, schreibt der Import den Status „nicht_konfiguriert“ und
  endet mit Exit 0 – die Datenlage ist dann schlicht offen, kein Fehlalarm.

AUSGABE:
  data/klicks_eigen.json       Zeilen im Format von click_attribution.py
  data/klicks_eigen.meta.json  Stand, Zeitraum, Summen, Status (ohne Personenbezug)

DATENSCHUTZ: Es kommen nur Tagessummen je Gateway-Schlüssel und Artikel an.
Keine IP, kein Cookie, keine Kennung. Siehe docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
KEYS_MJS = ROOT / "cloudflare" / "klick-zaehler" / "gateway-keys.mjs"
POSTS = ROOT / "content" / "posts"
OUT_ROWS = ROOT / "data" / "klicks_eigen.json"
OUT_META = ROOT / "data" / "klicks_eigen.meta.json"
API = "https://api.cloudflare.com/client/v4"
ARTIKEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,119}$")
SQL = "SELECT tag, go_key, artikel, anzahl FROM klicks WHERE tag >= ? ORDER BY tag, go_key, artikel"


class ImportFehler(RuntimeError):
    pass


# ---------------------------------------------------------------- Schlüssel

def registry_keys(path: Path = REGISTRY) -> list[str]:
    """Gateway-Schlüssel aus der Registry (Quelle der Wahrheit für /go/)."""
    import yaml  # Repo-Abhängigkeit (PyYAML), wie in den übrigen Gates

    daten = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return sorted((daten.get("links") or {}).keys())


def render_keys_mjs(keys: list[str]) -> str:
    zeilen = ",\n".join(f'  "{k}"' for k in keys)
    return (
        "// GENERIERT von scripts/klick_import.py --bake-keys aus scripts/check24_links.yaml.\n"
        "// Nicht von Hand ändern. Drift prüft: python3 scripts/klick_import.py --pruefe-keys\n"
        "export const GATEWAY_KEYS = [\n"
        f"{zeilen},\n"
        "];\n"
    )


def bake_keys() -> int:
    keys = registry_keys()
    KEYS_MJS.write_text(render_keys_mjs(keys), encoding="utf-8")
    return len(keys)


def pruefe_keys() -> bool:
    """True, wenn die Worker-Schlüsselliste zur Registry passt."""
    soll = render_keys_mjs(registry_keys())
    ist = KEYS_MJS.read_text(encoding="utf-8") if KEYS_MJS.exists() else ""
    return soll == ist


# ---------------------------------------------------------------- Artikel-Pillar

def pillar_index(posts_dir: Path = POSTS) -> dict[str, str]:
    """Artikel-Slug → Pillar, aus dem Frontmatter (ohne YAML-Abhängigkeit)."""
    index: dict[str, str] = {}
    if not posts_dir.exists():
        return index
    for datei in posts_dir.glob("*/index.md"):
        text = datei.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        pm = re.search(r'^pillar:\s*"?([^"\n]+?)"?\s*$', m.group(1), re.M)
        index[datei.parent.name] = pm.group(1).strip() if pm else ""
    return index


# ---------------------------------------------------------------- Cloudflare D1

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


def d1_abfrage(http, konto: str, db: str, token: str, sql: str, params: list) -> list[dict]:
    url = f"{API}/accounts/{konto}/d1/database/{db}/query"
    body = json.dumps({"sql": sql, "params": params}).encode("utf-8")
    status, antwort = http(
        "POST",
        url,
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body,
    )
    if status != 200 or not antwort.get("success"):
        fehler = antwort.get("errors") or [{"message": f"HTTP {status}"}]
        raise ImportFehler(f"D1-Abfrage fehlgeschlagen: {fehler}")
    ergebnisse = antwort.get("result") or []
    return list(ergebnisse[0].get("results") or []) if ergebnisse else []


def berlin_heute(now: dt.datetime | None = None) -> dt.date:
    """Geschäftstag in Europe/Berlin (Sommer-/Winterzeit über zoneinfo)."""
    from zoneinfo import ZoneInfo

    now = now or dt.datetime.now(dt.timezone.utc)
    return now.astimezone(ZoneInfo("Europe/Berlin")).date()


# ---------------------------------------------------------------- Aufbereitung

def baue_zeilen(d1_zeilen: list[dict], pillar: dict[str, str]) -> list[dict]:
    """D1-Tageszeilen → Zeilen im Format von click_attribution.py."""
    zeilen = []
    for z in d1_zeilen:
        go_key = str(z.get("go_key") or "")
        artikel = str(z.get("artikel") or "unbekannt")
        anzahl = int(z.get("anzahl") or 0)
        if not go_key or anzahl <= 0:
            continue
        kennung = artikel if ARTIKEL_RE.match(artikel) else ""
        zeilen.append({
            "event": "affiliate_click",
            "slug": go_key,
            # Gleiche Form wie der Render-Hook (Hugo File.Path)
            "article": f"posts/{kennung}/index.md" if kennung else "",
            "pillar": pillar.get(kennung, "") if kennung else "",
            "count": anzahl,
            "tag": str(z.get("tag") or ""),
        })
    return zeilen


def baue_meta(zeilen: list[dict], von: str, status: str, grund: str = "", stand: dt.datetime | None = None) -> dict:
    stand = stand or dt.datetime.now(dt.timezone.utc)
    return {
        "stand": stand.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quelle": "cloudflare-d1 (klick-zaehler)",
        "zeitraum": {"von": von, "bis": berlin_heute(stand).isoformat()},
        "summe_klicks": sum(z["count"] for z in zeilen),
        "zeilen": len(zeilen),
        "status": status,
        "grund": grund,
        "datenschutz": "aggregierte Tageszähler je Gateway und Artikel; keine IP, kein Cookie, keine Personenbezüge",
    }


def schreibe(zeilen: list[dict], meta: dict, rows_path: Path = OUT_ROWS, meta_path: Path = OUT_META) -> None:
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    rows_path.write_text(json.dumps(zeilen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- Lauf

def lauf(tage: int, http=default_http, env: dict | None = None,
         rows_path: Path = OUT_ROWS, meta_path: Path = OUT_META, now: dt.datetime | None = None) -> dict:
    env = os.environ if env is None else env
    now = now or dt.datetime.now(dt.timezone.utc)
    konto = env.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    db = env.get("CLOUDFLARE_D1_DATABASE_ID", "").strip()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    heute = berlin_heute(now)
    von = (heute - dt.timedelta(days=tage - 1)) if tage > 0 else dt.date(2000, 1, 1)

    if not (konto and db and token):
        meta = baue_meta([], von.isoformat(), "nicht_konfiguriert",
                         "CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_D1_DATABASE_ID / CLOUDFLARE_API_TOKEN fehlen", now)
        schreibe([], meta, rows_path, meta_path)
        return meta

    try:
        d1 = d1_abfrage(http, konto, db, token, SQL, [von.isoformat()])
    except ImportFehler as e:
        meta = baue_meta([], von.isoformat(), "fehler", str(e), now)
        schreibe([], meta, rows_path, meta_path)
        return meta

    zeilen = baue_zeilen(d1, pillar_index())
    meta = baue_meta(zeilen, von.isoformat(), "ok", "", now)
    schreibe(zeilen, meta, rows_path, meta_path)
    return meta


# ---------------------------------------------------------------- Selbsttest

def _selftest() -> int:
    import tempfile as tf

    fehler = []
    # 1) Schlüssel-Drift: Registry muss zur Worker-Liste passen (nach --bake-keys)
    if not pruefe_keys():
        fehler.append("gateway-keys.mjs weicht von der Registry ab (--bake-keys ausführen)")

    # 2) Aufbereitung: Artikel-Pillar, unbekannter Artikel, leere Zeilen
    pillar = {"2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig": "strom-sparen"}
    d1 = [
        {"tag": "2026-10-10", "go_key": "gas", "artikel": "2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig", "anzahl": 3},
        {"tag": "2026-10-10", "go_key": "dsl", "artikel": "unbekannt", "anzahl": 2},
        {"tag": "2026-10-10", "go_key": "dsl", "artikel": "KAPUTT ../../x", "anzahl": 1},
        {"tag": "2026-10-10", "go_key": "strom", "artikel": "x", "anzahl": 0},
    ]
    zeilen = baue_zeilen(d1, pillar)
    if len(zeilen) != 3:
        fehler.append(f"erwartet 3 Zeilen (leere verworfen), bekommen {len(zeilen)}")
    if zeilen and (zeilen[0]["pillar"] != "strom-sparen" or zeilen[0]["count"] != 3):
        fehler.append("Pillar-Zuordnung oder Zähler falsch")
    if any(z["article"] and "KAPUTT" in z["article"] for z in zeilen):
        fehler.append("ungültiger Slug wurde nicht verworfen")

    # 3) Lauf ohne Zugang → Status nicht_konfiguriert, Exit-freundlich
    with tf.TemporaryDirectory() as tmp:
        rp, mp = Path(tmp) / "r.json", Path(tmp) / "m.json"
        meta = lauf(90, env={}, rows_path=rp, meta_path=mp)
        if meta["status"] != "nicht_konfiguriert" or json.loads(rp.read_text()) != []:
            fehler.append("ohne Zugang muss der Status nicht_konfiguriert sein")

    # 4) Lauf mit Fake-API → Summen und Dateiformat
    def fake_http(method, url, headers, body):
        if "/d1/database/" not in url or method != "POST":
            return 404, {}
        return 200, {"success": True, "result": [{"results": d1, "success": True}], "errors": []}

    with tf.TemporaryDirectory() as tmp:
        rp, mp = Path(tmp) / "r.json", Path(tmp) / "m.json"
        meta = lauf(90, http=fake_http,
                    env={"CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_D1_DATABASE_ID": "d", "CLOUDFLARE_API_TOKEN": "t"},
                    rows_path=rp, meta_path=mp)
        if meta["status"] != "ok" or meta["summe_klicks"] != 6:
            fehler.append(f"Fake-Lauf: Status/Summe falsch ({meta.get('status')}, {meta.get('summe_klicks')})")

    if fehler:
        print("❌ KLICK-IMPORT-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ KLICK-IMPORT-SELBSTTEST bestanden (Schlüssel-Drift, Aufbereitung, Status, Fake-Lauf).")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--bake-keys" in argv:
        n = bake_keys()
        print(f"✅ {n} Gateway-Schlüssel nach {KEYS_MJS.relative_to(ROOT)} geschrieben.")
        return 0
    if "--pruefe-keys" in argv:
        if pruefe_keys():
            print("✅ Gateway-Schlüssel stimmen mit der Registry überein.")
            return 0
        print("❌ Drift: cloudflare/klick-zaehler/gateway-keys.mjs ist veraltet → --bake-keys ausführen.")
        return 1
    tage = 0
    if "--tage" in argv:
        tage = int(argv[argv.index("--tage") + 1])
    meta = lauf(tage)
    print(f"Klick-Import: Status={meta['status']} · Klicks={meta['summe_klicks']} · Zeitraum ab {meta['zeitraum']['von']}")
    if meta.get("grund"):
        print(f"   Grund: {meta['grund']}")
    return 1 if meta["status"] == "fehler" and "--streng" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
