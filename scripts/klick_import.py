#!/usr/bin/env python3
"""
KLICK-IMPORT – holt die cookielosen /go/-Tageszähler aus Cloudflare D1
und legt sie im Format ab, das `scripts/click_attribution.py` bereits liest.

WARUM: Die Klickzahlen kommen aus einer eigenen, kostenlosen und cookielosen Zählung
am /go/-Beacon (Worker: cloudflare/klick-zaehler) – kein Fremdanbieter, keine laufenden
Kosten. Die Datenschutz-Prüfung vor dem Einschalten steht in
docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md (Abschnitt 7). Fehlt der Zähler, bleiben
die Klicks „unbekannt“.

AUFRUF:
  python3 scripts/klick_import.py                 # Import (Zeitraum: alle Tage)
  python3 scripts/klick_import.py --tage 90       # nur die letzten 90 Tage
  python3 scripts/klick_import.py --bake-keys     # Schlüsselliste für den Worker erzeugen
  python3 scripts/klick_import.py --pruefe-keys   # Drift-Check Registry ↔ Worker (Exit 1 bei Abweichung)
  python3 scripts/klick_import.py --selftest      # Offline-Selbsttest (ohne Netz)

ZUGANG (nur in GitHub Actions bzw. lokal, nie im Repo):
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
  Token-Recht: „Account › D1 › Read“ (nur lesen).
  Die Datenbank-ID steht in cloudflare/klick-zaehler/wrangler.toml (keine Secret-Größe).
  Der Abruf läuft über den offiziellen Wrangler-CLI (devDependency des Workers):
  `wrangler d1 execute DB --remote --json`. Dieses Skript spricht keinen Cloudflare-
  Endpunkt direkt an.
  Fehlt ein Wert oder ist die database_id noch Platzhalter, schreibt der Import den
  Status „nicht_konfiguriert“ und endet mit Exit 0 – die Datenlage ist dann schlicht
  offen, kein Fehlalarm.

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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
WORKER_DIR = ROOT / "cloudflare" / "klick-zaehler"
KEYS_MJS = WORKER_DIR / "gateway-keys.mjs"
WRANGLER_TOML = WORKER_DIR / "wrangler.toml"
POSTS = ROOT / "content" / "posts"
OUT_ROWS = ROOT / "data" / "klicks_eigen.json"
OUT_META = ROOT / "data" / "klicks_eigen.meta.json"
D1_BINDING = "DB"  # Binding in wrangler.toml (Datenbank ff-klicks)
WRANGLER_TIMEOUT = 180
ARTIKEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,119}$")
DATUM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SQL_TEMPLATE = ("SELECT tag, go_key, artikel, anzahl FROM klicks "
                "WHERE tag >= '{von}' ORDER BY tag, go_key, artikel")


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


# ---------------------------------------------------------------- Cloudflare D1 (über Wrangler)

def wrangler_exe() -> str | None:
    """Lokal installierter Wrangler des Workers, sonst der Wrangler im PATH."""
    lokal = WORKER_DIR / "node_modules" / ".bin" / "wrangler"
    if lokal.exists():
        return str(lokal)
    return shutil.which("wrangler")


def d1_db_id_gesetzt(toml: Path = WRANGLER_TOML) -> tuple[bool, str]:
    """True, wenn in wrangler.toml eine echte database_id eingetragen ist."""
    if not toml.exists():
        return False, "wrangler.toml fehlt"
    m = re.search(r'^\s*database_id\s*=\s*"([^"]*)"', toml.read_text(encoding="utf-8"), re.M)
    if not m or not m.group(1).strip() or m.group(1).startswith("EINTRAGEN"):
        return False, ("database_id in cloudflare/klick-zaehler/wrangler.toml ist noch Platzhalter "
                       "(Runbook Abschnitt 3: wrangler d1 create)")
    return True, ""


def sql_fuer(von: str) -> str:
    """Baut das SQL. Wrangler kennt keine Parameter-Bindung bei --command,
    deshalb wird das Datum vorher strikt geprüft – nur YYYY-MM-DD ist erlaubt."""
    if not DATUM_RE.match(von):
        raise ImportFehler(f"ungültiges Datum für die Abfrage: {von!r}")
    return SQL_TEMPLATE.format(von=von)


def d1_ergebnis_aus_wrangler(stdout: str) -> list[dict]:
    """Wrangler --json liefert ein Array je Statement: [{results, success, meta}]."""
    text = (stdout or "").strip()
    try:
        antwort = json.loads(text)
    except ValueError:
        # Fallback: Hinweise vor dem JSON-Array ignorieren
        idx = text.find("\n[")
        try:
            antwort = json.loads(text[idx + 1:]) if idx >= 0 else None
        except ValueError:
            antwort = None
    if not isinstance(antwort, list) or not antwort or not isinstance(antwort[0], dict):
        raise ImportFehler("Wrangler-Ausgabe nicht lesbar (kein JSON-Ergebnis)")
    erstes = antwort[0]
    if not erstes.get("success"):
        raise ImportFehler("D1-Abfrage meldet success=false")
    return list(erstes.get("results") or [])


def _kurz(text: str, geheim: list[str]) -> str:
    for g in geheim:
        if g:
            text = text.replace(g, "***")
    text = " ".join((text or "").split())
    return text[:300]


def wrangler_abfrage(sql: str, env: dict) -> list[dict]:
    """Führt das SQL remote über `wrangler d1 execute` aus (ohne Shell, mit Timeout)."""
    exe = wrangler_exe()
    if not exe:
        raise ImportFehler("wrangler fehlt – in cloudflare/klick-zaehler `npm ci` ausführen")
    token = env["CLOUDFLARE_API_TOKEN"]
    cmd = [exe, "d1", "execute", D1_BINDING, "--remote", "--json",
           "-c", str(WRANGLER_TOML), "-y", "--command", sql]
    umgebung = {
        **os.environ,
        "CLOUDFLARE_API_TOKEN": token,
        "CLOUDFLARE_ACCOUNT_ID": env["CLOUDFLARE_ACCOUNT_ID"],
        "WRANGLER_SEND_METRICS": "false",
        "NO_COLOR": "1",
    }
    try:
        p = subprocess.run(cmd, cwd=str(WORKER_DIR), capture_output=True, text=True,
                           timeout=WRANGLER_TIMEOUT, env=umgebung, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ImportFehler(f"wrangler: Zeitüberschreitung nach {WRANGLER_TIMEOUT}s") from exc
    if p.returncode != 0:
        raise ImportFehler(f"wrangler d1 execute beendet mit Exit {p.returncode}: "
                           f"{_kurz(p.stderr or p.stdout, [token])}")
    return d1_ergebnis_aus_wrangler(p.stdout)


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

def lauf(tage: int, abfrage: Callable[[str, dict], list[dict]] = wrangler_abfrage,
         env: dict | None = None, rows_path: Path = OUT_ROWS, meta_path: Path = OUT_META,
         now: dt.datetime | None = None, db_pruefung: Callable[[], tuple[bool, str]] = d1_db_id_gesetzt) -> dict:
    env = os.environ if env is None else env
    now = now or dt.datetime.now(dt.timezone.utc)
    konto = env.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = env.get("CLOUDFLARE_API_TOKEN", "").strip()
    heute = berlin_heute(now)
    von = (heute - dt.timedelta(days=tage - 1)) if tage > 0 else dt.date(2000, 1, 1)

    if not (konto and token):
        meta = baue_meta([], von.isoformat(), "nicht_konfiguriert",
                         "CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN fehlen", now)
        schreibe([], meta, rows_path, meta_path)
        return meta

    db_ok, db_grund = db_pruefung()
    if not db_ok:
        meta = baue_meta([], von.isoformat(), "nicht_konfiguriert", db_grund, now)
        schreibe([], meta, rows_path, meta_path)
        return meta

    try:
        d1 = abfrage(sql_fuer(von.isoformat()), {"CLOUDFLARE_ACCOUNT_ID": konto, "CLOUDFLARE_API_TOKEN": token})
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
    with tempfile.TemporaryDirectory() as tmp:
        rp, mp = Path(tmp) / "r.json", Path(tmp) / "m.json"
        meta = lauf(90, env={}, rows_path=rp, meta_path=mp)
        if meta["status"] != "nicht_konfiguriert" or json.loads(rp.read_text()) != []:
            fehler.append("ohne Zugang muss der Status nicht_konfiguriert sein")

    # 4) Platzhalter-database_id → nicht_konfiguriert (kein Abruf)
    with tempfile.TemporaryDirectory() as tmp:
        rp, mp = Path(tmp) / "r.json", Path(tmp) / "m.json"
        aufrufe = []
        meta = lauf(90, abfrage=lambda s, e: aufrufe.append(s) or [],
                    env={"CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_API_TOKEN": "t"},
                    rows_path=rp, meta_path=mp,
                    db_pruefung=lambda: (False, "Platzhalter"))
        if meta["status"] != "nicht_konfiguriert" or aufrufe:
            fehler.append("Platzhalter-database_id darf keinen Abruf auslösen")

    # 5) Lauf mit Fake-Abfrage → Summen, Datum im SQL, Dateiformat
    aufrufe_sql: list[str] = []

    def fake_abfrage(sql: str, env: dict) -> list[dict]:
        aufrufe_sql.append(sql)
        return d1

    with tempfile.TemporaryDirectory() as tmp:
        rp, mp = Path(tmp) / "r.json", Path(tmp) / "m.json"
        meta = lauf(90, abfrage=fake_abfrage,
                    env={"CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_API_TOKEN": "t"},
                    rows_path=rp, meta_path=mp, db_pruefung=lambda: (True, ""))
        if meta["status"] != "ok" or meta["summe_klicks"] != 6:
            fehler.append(f"Fake-Lauf: Status/Summe falsch ({meta.get('status')}, {meta.get('summe_klicks')})")
        if not aufrufe_sql or "tag >= '" not in aufrufe_sql[0]:
            fehler.append("SQL-Abfrage fehlt oder hat kein Datumsfilter")

    # 6) Datumsvalidierung: keine Injektion über das Datum
    try:
        sql_fuer("2026-10-01' OR 1=1 --")
        fehler.append("ungültiges Datum wurde akzeptiert")
    except ImportFehler:
        pass

    # 7) Wrangler-Ausgabe: echtes Format (Array je Statement), Hinweiszeile davor, Fehler
    echt = ('[\n  {\n    "results": [\n      {\n        "tag": "2026-10-10",\n        "go_key": "gas",\n'
            '        "artikel": "x-artikel",\n        "anzahl": 3\n      }\n    ],\n'
            '    "success": true,\n    "meta": {\n      "duration": 1\n    }\n  }\n]\n')
    try:
        if d1_ergebnis_aus_wrangler(echt) != [{"tag": "2026-10-10", "go_key": "gas", "artikel": "x-artikel", "anzahl": 3}]:
            fehler.append("Wrangler-Format wird falsch gelesen")
        if len(d1_ergebnis_aus_wrangler("Hinweis vorab\n" + echt)) != 1:
            fehler.append("Hinweiszeile vor dem JSON bricht das Parsen")
    except ImportFehler as exc:
        fehler.append(f"Wrangler-Format: {exc}")
    for kaputt in ('{"success": true}', "kein json", '[{"success": false, "results": []}]'):
        try:
            d1_ergebnis_aus_wrangler(kaputt)
            fehler.append(f"kaputte Wrangler-Ausgabe akzeptiert: {kaputt!r}")
        except ImportFehler:
            pass

    if fehler:
        print("❌ KLICK-IMPORT-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ KLICK-IMPORT-SELBSTTEST bestanden (Schlüssel-Drift, Aufbereitung, Status, SQL, Wrangler-Format).")
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
