#!/usr/bin/env python3
# ============================================================
#  KV-/D1-BACKUP – Abonnenten, Einwilligungsnachweise, Zähler
#
#  Sicherheitsaudit 14.10.2026 (M-11): Das Offsite-Backup sicherte nur das
#  ohnehin öffentliche Git-Repo. Die UNERSETZLICHEN Daten lagen allein in
#  Cloudflare:
#    · Workers KV `ABO`: Abonnenten (abo:), Tokens (token:) und die
#      Einwilligungsnachweise (nachweis:) – Nachweispflicht nach
#      Art. 7 Abs. 1 DSGVO
#    · optional D1 (Klick-Zähler)
#    · zusätzlich alle Betriebspräfixe (budget:, exportlog:, takt:, feedback:/fbtag:) –
#      nicht personenbezogen, aber betriebskritisch (Highend 22.10.2026,
#      vollständige Abdeckung siehe docs/ANLEITUNG-OFFSITE-BACKUP.md)
#
#  Dieses Skript exportiert beides über die Cloudflare-API in EINE
#  JSON-Datei (alle KV-Schlüssel, kein Präfix-Filter – vollständiger Export).
#  Verschlüsselung und Ablage übernimmt der Workflow
#  (backup-offsite.yml, Job „kv-backup“) – und zwar NUR in ein privates
#  Ziel. NIEMALS als Actions-Artefakt: Artefakte öffentlicher Repos kann
#  jeder angemeldete GitHub-Nutzer laden, und eine verschlüsselte Datei
#  wäre dann offline per Passphrasen-Raten angreifbar.
#
#  Umgebung:
#    CF_API_TOKEN       API-Token NUR mit „Workers KV Storage: Read“
#                       (+ „D1: Read“, falls D1 gesichert wird)
#    CF_ACCOUNT_ID      Cloudflare-Account-ID
#    KV_NAMESPACE_ID    ID des Namespace ABO
#    D1_DATABASE_ID     optional
#
#  Aufruf:
#    python3 scripts/kv_backup.py --out kv-export.json
#    python3 scripts/kv_backup.py --pruefen kv-export.json   # Wiederherstellungs-Probe
#    python3 scripts/kv_backup.py --selftest
#
#  Wiederherstellung (docs/ANLEITUNG-OFFSITE-BACKUP.md): JSON entschlüsseln, dann
#    python3 scripts/kv_backup.py --wrangler-bulk kv-export.json > bulk.json
#    npx wrangler kv bulk put bulk.json --namespace-id <ID> --remote
#  `--remote` ist Pflicht: Wrangler 4 (gepinnt 4.149.0) schreibt KV-Befehle
#  ohne Angabe in die LOKALE Simulation (isLocal, Vorgabe true) und meldet
#  trotzdem Erfolg – ein Rückspielen ohne `--remote` stellt nichts wieder her
#  (geprüft 15.10.2026, WF-9E5A; Test: test_backup_einrichtung.py).
# ============================================================
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.cloudflare.com/client/v4"
PFLICHT_PRAEFIXE = ("abo:", "token:", "nachweis:")


def _http(methode: str, url: str, token: str, koerper: dict | None = None) -> dict:
    daten = json.dumps(koerper).encode() if koerper is not None else None
    anfrage = urllib.request.Request(url, data=daten, method=methode, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "ff-kv-backup/1",
    })
    with urllib.request.urlopen(anfrage, timeout=60) as antwort:
        roh = antwort.read().decode("utf-8")
    try:
        return json.loads(roh)
    except ValueError:
        return {"success": True, "_roh": roh}


HTTP = _http  # im Selbsttest austauschbar


def kv_schluessel(token: str, konto: str, ns: str) -> list[dict]:
    alle, cursor = [], ""
    while True:
        q = {"limit": "1000"}
        if cursor:
            q["cursor"] = cursor
        url = f"{API}/accounts/{konto}/storage/kv/namespaces/{ns}/keys?{urllib.parse.urlencode(q)}"
        d = HTTP("GET", url, token)
        if not d.get("success", False):
            raise RuntimeError(f"KV-Schlüsselliste fehlgeschlagen: {d.get('errors')}")
        alle.extend(d.get("result") or [])
        cursor = ((d.get("result_info") or {}).get("cursor") or "")
        if not cursor:
            return alle


def kv_werte(token: str, konto: str, ns: str, namen: list[str]) -> dict[str, str]:
    werte: dict[str, str] = {}
    for i in range(0, len(namen), 100):
        teil = namen[i:i + 100]
        url = f"{API}/accounts/{konto}/storage/kv/namespaces/{ns}/bulk/get"
        try:
            d = HTTP("POST", url, token, {"keys": teil, "type": "text"})
            if not d.get("success", False):
                raise RuntimeError(str(d.get("errors")))
            werte.update(((d.get("result") or {}).get("values")) or {})
        except (RuntimeError, urllib.error.HTTPError):
            # Rueckfall: einzeln lesen (aelteres API-Verhalten)
            for name in teil:
                url1 = f"{API}/accounts/{konto}/storage/kv/namespaces/{ns}/values/{urllib.parse.quote(name, safe='')}"
                d1 = HTTP("GET", url1, token)
                werte[name] = d1.get("_roh") if "_roh" in d1 else json.dumps(d1)
    return werte


def d1_export(token: str, konto: str, db: str) -> dict[str, list]:
    url = f"{API}/accounts/{konto}/d1/database/{db}/query"
    d = HTTP("POST", url, token, {"sql": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%'"})
    tabellen = [r["name"] for r in ((d.get("result") or [{}])[0].get("results") or [])]
    aus = {}
    for t in tabellen:
        if not t.replace("_", "").isalnum():
            continue
        dt = HTTP("POST", url, token, {"sql": f'SELECT * FROM "{t}"'})
        aus[t] = ((dt.get("result") or [{}])[0].get("results")) or []
    return aus


def exportieren(env: dict) -> dict:
    token = env.get("CF_API_TOKEN", "").strip()
    konto = env.get("CF_ACCOUNT_ID", "").strip()
    ns = env.get("KV_NAMESPACE_ID", "").strip()
    fehlend = [n for n, w in (("CF_API_TOKEN", token), ("CF_ACCOUNT_ID", konto), ("KV_NAMESPACE_ID", ns)) if not w]
    if fehlend:
        raise SystemExit(f"FEHLT: {', '.join(fehlend)} – KV-Backup nicht möglich (fail-closed).")
    schluessel = kv_schluessel(token, konto, ns)
    namen = [k["name"] for k in schluessel]
    werte = kv_werte(token, konto, ns, namen)
    ablauf = {k["name"]: k.get("expiration") for k in schluessel if k.get("expiration")}
    export = {
        "version": 1,
        "erstellt": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "kv": {"namespace": ns, "anzahl": len(namen), "werte": werte, "ablauf": ablauf},
    }
    db = env.get("D1_DATABASE_ID", "").strip()
    if db:
        export["d1"] = {"datenbank": db, "tabellen": d1_export(token, konto, db)}
    return export


def _kennung(name: str) -> str:
    """Schluessel fuers Log: Praefix + Kurzhash – nie Adresse oder Token."""
    import hashlib
    praefix = name.split(":", 1)[0]
    return f"{praefix}:#{hashlib.sha256(name.encode()).hexdigest()[:8]}"


def pruefen(export: dict) -> list[str]:
    """Wiederherstellungs-Probe: Struktur vollständig und konsistent?
    Meldungen enthalten keine Adressen/Tokens (Kurzhash statt Schluessel)."""
    fehler = []
    if export.get("version") != 1:
        fehler.append("version != 1")
    kv = export.get("kv") or {}
    werte = kv.get("werte")
    if not isinstance(werte, dict):
        return fehler + ["kv.werte fehlt"]
    if kv.get("anzahl") != len(werte):
        fehler.append(f"Anzahl {kv.get('anzahl')} != {len(werte)} Werte (unvollständig gelesen)")
    for name, wert in werte.items():
        if not isinstance(wert, str):
            fehler.append(f"{_kennung(name)}: Wert ist kein Text")
        elif name.startswith(("abo:", "nachweis:")):
            try:
                json.loads(wert)
            except ValueError:
                fehler.append(f"{_kennung(name)}: kein gültiges JSON")
    # Jeder token:-Schluessel zeigt auf ein vorhandenes Abo
    for name, wert in werte.items():
        if name.startswith("token:") and f"abo:{wert}" not in werte:
            fehler.append(f"{_kennung(name)}: verwaist (zugehöriges abo: fehlt)")
    return fehler


def wrangler_bulk(export: dict) -> list[dict]:
    jetzt = int(_dt.datetime.now(_dt.timezone.utc).timestamp())
    aus = []
    for name, wert in sorted((export.get("kv") or {}).get("werte", {}).items()):
        eintrag = {"key": name, "value": wert}
        abl = ((export.get("kv") or {}).get("ablauf") or {}).get(name)
        if abl:
            if abl <= jetzt + 60:
                continue  # waere sofort abgelaufen
            eintrag["expiration"] = int(abl)
        aus.append(eintrag)
    return aus


def zusammenfassung(export: dict) -> str:
    werte = (export.get("kv") or {}).get("werte", {})
    zaehler = {p: sum(1 for n in werte if n.startswith(p)) for p in PFLICHT_PRAEFIXE}
    rest = len(werte) - sum(zaehler.values())
    teile = [f"{p} {n}" for p, n in zaehler.items()] + [f"sonstige {rest}"]
    if "d1" in export:
        teile.append("D1-Tabellen " + str(len(export["d1"]["tabellen"])))
    return ", ".join(teile)


def selbsttest() -> int:
    global HTTP
    echt = HTTP
    kv = {"abo:a@x.de": json.dumps({"status": "active", "token": "t1"}),
          "token:t1": "a@x.de", "nachweis:abc": json.dumps({"ip": "1.2.3.4"}),
          "fbtag:2026-10-14": json.dumps({"n": 1})}
    namen = sorted(kv)

    def gefaelscht(methode, url, token, koerper=None):
        assert token == "tok"
        if "/keys" in url:
            if "cursor=c2" in url:
                return {"success": True, "result": [{"name": n} for n in namen[2:]], "result_info": {"cursor": ""}}
            return {"success": True, "result": [{"name": n, "expiration": 4102444800} for n in namen[:2]], "result_info": {"cursor": "c2"}}
        if url.endswith("/bulk/get"):
            return {"success": True, "result": {"values": {k: kv[k] for k in koerper["keys"]}}}
        if "/d1/" in url:
            if "sqlite_master" in koerper["sql"]:
                return {"success": True, "result": [{"results": [{"name": "klicks"}]}]}
            return {"success": True, "result": [{"results": [{"slug": "strom", "n": 3}]}]}
        raise AssertionError(url)

    try:
        HTTP = gefaelscht
        env = {"CF_API_TOKEN": "tok", "CF_ACCOUNT_ID": "acc", "KV_NAMESPACE_ID": "ns", "D1_DATABASE_ID": "db"}
        ex = exportieren(env)
        assert ex["kv"]["anzahl"] == 4 and ex["kv"]["werte"] == kv, ex
        assert ex["d1"]["tabellen"]["klicks"][0]["n"] == 3
        assert pruefen(ex) == [], pruefen(ex)
        kaputt = json.loads(json.dumps(ex))
        kaputt["kv"]["werte"]["token:t9"] = "fehlt@x.de"
        assert any("verwaist" in f for f in pruefen(kaputt))
        kaputt2 = json.loads(json.dumps(ex))
        kaputt2["kv"]["anzahl"] = 9
        assert any("unvollständig" in f for f in pruefen(kaputt2))
        bulk = wrangler_bulk(ex)
        assert len(bulk) == 4 and all("key" in b and "value" in b for b in bulk)
        try:
            exportieren({"CF_API_TOKEN": "", "CF_ACCOUNT_ID": "a", "KV_NAMESPACE_ID": "n"})
            raise AssertionError("ohne Token darf es nicht laufen")
        except SystemExit as e:
            assert "CF_API_TOKEN" in str(e)
        assert "abo: 1" in zusammenfassung(ex)
    finally:
        HTTP = echt
    print("✅ kv_backup-Selbsttest: Export, Paginierung, D1, Probe, Bulk-Format, fail-closed.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    ap.add_argument("--pruefen")
    ap.add_argument("--wrangler-bulk")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selbsttest()
    if a.pruefen or a.wrangler_bulk:
        with open(a.pruefen or a.wrangler_bulk, encoding="utf-8") as fh:
            ex = json.load(fh)
        if a.wrangler_bulk:
            json.dump(wrangler_bulk(ex), sys.stdout, ensure_ascii=False)
            return 0
        fehler = pruefen(ex)
        for f in fehler:
            print(f"❌ {f}")
        print(("✅ " if not fehler else "🛑 ") + "Probe: " + zusammenfassung(ex))
        return 1 if fehler else 0
    if not a.out:
        ap.error("--out, --pruefen, --wrangler-bulk oder --selftest angeben")
    ex = exportieren(dict(os.environ))
    fehler = pruefen(ex)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(ex, fh, ensure_ascii=False)
    os.chmod(a.out, 0o600)
    # Nur Zaehler ins Log – keine Adressen, keine Tokens.
    print(f"KV-Export: {zusammenfassung(ex)}")
    if fehler:
        for f in fehler[:20]:
            print(f"::warning::Probe: {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
