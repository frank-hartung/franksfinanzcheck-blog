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
import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr, redirect_stdout

API = "https://api.cloudflare.com/client/v4"
PFLICHT_PRAEFIXE = ("abo:", "token:", "nachweis:")


class NetzwekFehler(RuntimeError):
    """Cloudflare ist nicht erreichbar – sauber gemeldet, nie als leere Liste."""


def _http(methode: str, url: str, token: str, koerper: dict | None = None) -> dict:
    daten = json.dumps(koerper).encode() if koerper is not None else None
    anfrage = urllib.request.Request(url, data=daten, method=methode, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "ff-kv-backup/1",
    })
    # #923 (02.11.2026): Ein TLS-Abbruch oder eine falsche Adresse endete
    # vorher in einem rohen Traceback. Der ist im Actions-Log unlesbar und
    # nennt keine Abhilfe; für den Betreiber ist wichtig, DASS es eine
    # Störung war und dass der nächste Lauf genügt – nicht der Stack.
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            roh = antwort.read().decode("utf-8")
    except urllib.error.HTTPError as fehler:
        try:
            roh = fehler.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 – ein Fehler beim Fehlerlesen darf nicht werfen
            roh = ""
        try:
            return json.loads(roh) if roh else {"success": False, "_status": fehler.code}
        except ValueError:
            return {"success": False, "_status": fehler.code, "_roh": roh[:200]}
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        raise NetzwekFehler(
            "Cloudflare-API nicht erreichbar "
            f"({type(fehler).__name__}) – vermutlich vorübergehend. "
            "Status: https://www.cloudflarestatus.com · Später erneut starten."
        ) from None
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


def _d1_abfrage(url: str, token: str, sql: str, zweck: str) -> list:
    """Eine D1-Abfrage, die einen Fehlschlag NICHT in eine leere Liste verwandelt.

    BEFUND (02.11.2026, WF-9E5A / #923): Die alte Fassung las
    `((d.get("result") or [{}])[0].get("results")) or []`. Antwortet Cloudflare
    mit `success: false` (z. B. HTTP 200 und `{"success": false, "errors":
    [...]}` bei einer internen Störung), stand dort keine `result`-Liste – und
    die Funktion lieferte `[]`. Der Export enthielt dann eine Tabelle mit null
    Zeilen, die Wiederherstellungs-Probe `pruefen()` sah eine gültige Struktur
    und der Lauf war grün: ein Klick-Zähler, der still auf 0 zurückfällt, wäre
    erst im Ernstfall aufgefallen. Jetzt bricht der Export mit der echten
    Cloudflare-Meldung ab (fail-closed) – die Meldung nennt keine Zählerdaten.
    """
    d = HTTP("POST", url, token, {"sql": sql})
    if not isinstance(d, dict):
        raise RuntimeError(f"D1-{zweck}: unerwartete Antwort (kein Objekt)")
    if d.get("success") is not True:
        fehler = "; ".join(
            f"{e.get('code', '?')}: {e.get('message', '')}".strip()
            for e in (d.get("errors") or []) if isinstance(e, dict)
        ) or "ohne Fehlermeldung"
        raise RuntimeError(f"D1-{zweck} fehlgeschlagen ({fehler})")
    seiten = d.get("result")
    if not isinstance(seiten, list) or not seiten or not isinstance(seiten[0], dict):
        raise RuntimeError(f"D1-{zweck}: Antwort ohne Ergebnisblock")
    zeilen = seiten[0].get("results")
    if not isinstance(zeilen, list):
        raise RuntimeError(f"D1-{zweck}: Antwort ohne Zeilenliste")
    return zeilen


def d1_export(token: str, konto: str, db: str) -> dict[str, list]:
    url = f"{API}/accounts/{konto}/d1/database/{db}/query"
    d = _d1_abfrage(url, token,
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%'",
                    "Tabellenliste")
    tabellen = [r["name"] for r in d if isinstance(r, dict) and isinstance(r.get("name"), str)]
    if not tabellen:
        # Eine leere Datenbank hat keine Nutztabellen – das ist ein Befund,
        # kein Grund, sie stillschweigend als gesichert zu zählen.
        raise RuntimeError("D1-Export: keine Nutztabelle gefunden – D1_DATABASE_ID prüfen "
                           "(falsche Datenbank?) oder Variable entfernen")
    aus = {}
    for t in tabellen:
        if not t.replace("_", "").isalnum():
            continue
        aus[t] = _d1_abfrage(url, token, f'SELECT * FROM "{t}"', f'Tabelle {t}')
    return aus


def namespace_titel(token: str, konto: str, ns: str) -> str:
    """Liest den Titel des Namespace – der einzige Beleg, DASS er existiert.

    Der Titel ist kein Geheimnis und keine personenbezogene Angabe; er zeigt
    in Log und Export, welcher Speicher gesichert wurde („ABO“ statt nur einer
    ID). Nicht lesbar = fail-closed: Dann ist der Leerstand nicht belegt.
    """
    url = f"{API}/accounts/{konto}/storage/kv/namespaces/{ns}"
    d = HTTP("GET", url, token)
    if not isinstance(d, dict) or d.get("success") is not True:
        fehler = "; ".join(
            f"{e.get('code', '?')}: {e.get('message', '')}".strip()
            for e in ((d or {}).get("errors") or []) if isinstance(e, dict)
        ) or "ohne Fehlermeldung"
        raise RuntimeError(f"KV-Namespace {ns} nicht lesbar ({fehler}) – "
                           "KV_NAMESPACE_ID_ABO und Leserecht des Tokens prüfen")
    titel = ((d.get("result") or {}) if isinstance(d.get("result"), dict) else {}).get("title")
    return str(titel) if titel else "ohne Titel"


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
    # LEERSTAND BELEGEN, NICHT VERSCHWEIGEN (#923, 02.11.2026): Ein Export mit
    # null Schlüsseln kann legitim sein (frischer Bestand), meistens ist er
    # aber die Folge einer falschen Namespace-ID. Die Probe `pruefen()` soll
    # ihn deshalb nur akzeptieren, wenn der Namespace live als lesbar bestätigt
    # wurde – der Titel steht dann im Export und im Log (kein Schlüsselwert).
    if not namen:
        titel = namespace_titel(token, konto, ns)
        export["leer_bestaetigt"] = True
        export["kv"]["titel"] = titel
        print(f"::warning::KV-Namespace „{titel}“ wurde live gelesen und enthält 0 Schlüssel – "
              "das ist belegt leer, keine fehlgeschlagene Sicherung.", file=sys.stderr)
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

    Meldungen enthalten keine Adressen/Tokens (Kurzhash statt Schluessel).

    #923-NACHTRAG (02.11.2026, „grün, ohne geprüft zu haben“):
    Die alte Fassung meldete für einen Export mit **null** Schlüsseln und für
    D1-Tabellen **ohne** Zeilenliste `[]` – also „vollständig“. Zwei Folgen,
    beide still:

      · Ein leerer Namespace (falsche `KV_NAMESPACE_ID_ABO`, neu angelegter
        Namespace, falsches Konto) galt als gesicherte Abonnentenliste. Der
        Drill sagte dann „Abonnenten (KV): vollständig“.
      · Ein D1-Export, dessen Tabellen der Export gar nicht lesen konnte,
        bestand die Probe ebenfalls.

    Beides ist jetzt ein Befund. Ein bewusst leerer Bestand wird nicht
    bestraft, sondern belegt: `exportieren()` schreibt `leer_bestaetigt`,
    nachdem es die Schlüsselliste und den Namespace-Titel live gesehen hat.
    """
    fehler = []
    if export.get("version") != 1:
        fehler.append("version != 1")
    kv = export.get("kv") or {}
    werte = kv.get("werte")
    if not isinstance(werte, dict):
        return fehler + ["kv.werte fehlt"]
    if kv.get("anzahl") != len(werte):
        fehler.append(f"Anzahl {kv.get('anzahl')} != {len(werte)} Werte (unvollständig gelesen)")
    if not werte and export.get("leer_bestaetigt") is not True:
        fehler.append("kein einziger KV-Schlüssel im Export – Namespace-ID/Konto prüfen "
                      "(ein leerer Export ist keine Sicherung)")
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
    # D1: jede gesicherte Tabelle muss eine gelesene Zeilenliste tragen.
    if "d1" in export:
        tabellen = (export.get("d1") or {}).get("tabellen")
        if not isinstance(tabellen, dict) or not tabellen:
            fehler.append("d1.tabellen fehlt oder ist leer – D1 wurde nicht gesichert")
        else:
            for t, zeilen in tabellen.items():
                if not isinstance(zeilen, list):
                    fehler.append(f"d1.{t}: keine Zeilenliste (nicht gelesen)")
    return fehler


def ablauf_verlust(export: dict, jetzt: int | None = None) -> list[str]:
    """Schlüssel, die beim Rückspielen STILL verschwinden würden.

    BEFUND (02.11.2026): `wrangler_bulk()` überspringt jeden Schlüssel, dessen
    Ablaufzeit schon vorbei ist („waere sofort abgelaufen“). Das ist für das
    Rückspielen richtig – aber niemand hat es gesagt. Ein Export, dessen
    Ablaufzeiten in der Vergangenheit liegen (falsche Systemzeit beim Export,
    falsch interpretierte Einheit), spielte eine LEERE Sicherung zurück und
    meldete Erfolg. Jetzt wird jeder übersprungene Schlüssel gezählt und
    benannt (Präfix + Kurzhash, nie der Schlüssel selbst).
    """
    jetzt = int(_dt.datetime.now(_dt.timezone.utc).timestamp()) if jetzt is None else jetzt
    kv = export.get("kv") or {}
    ablauf = kv.get("ablauf") or {}
    verloren = []
    for name in (kv.get("werte") or {}):
        abl = ablauf.get(name)
        if abl and int(abl) <= jetzt + 60:
            verloren.append(name)
    return verloren



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
        tabellen = (export.get("d1") or {}).get("tabellen") or {}
        zeilen = sum(len(z) for z in tabellen.values() if isinstance(z, list))
        teile.append(f"D1-Tabellen {len(tabellen)} ({zeilen} Zeilen)")
    return ", ".join(teile)


def selbsttest() -> int:
    global HTTP
    echt = HTTP
    kv = {"abo:a@x.de": json.dumps({"status": "active", "token": "t1"}),
          "token:t1": "a@x.de", "nachweis:abc": json.dumps({"ip": "1.2.3.4"}),
          "fbtag:2026-10-14": json.dumps({"n": 1})}
    namen = sorted(kv)

    # Schaltbare Attrappen-Welt für die Fehlerfälle ab F-E (#923, 02.11.2026).
    schalter = {"d1_ausfall": False, "d1_leer": False, "ns_unlesbar": False}

    def gefaelscht(methode, url, token, koerper=None):
        assert token == "tok"
        if url.rstrip("/").endswith("/namespaces/ns"):
            if schalter["ns_unlesbar"]:
                return {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}
            return {"success": True, "result": {"id": "ns", "title": "ABO"}}
        if "/keys" in url:
            if "cursor=c2" in url:
                return {"success": True, "result": [{"name": n} for n in namen[2:]], "result_info": {"cursor": ""}}
            return {"success": True, "result": [{"name": n, "expiration": 4102444800} for n in namen[:2]], "result_info": {"cursor": "c2"}}
        if url.endswith("/bulk/get"):
            return {"success": True, "result": {"values": {k: kv[k] for k in koerper["keys"]}}}
        if "/d1/" in url:
            # D1-Fehlerbilder aus der Praxis: HTTP 200 mit success=false
            # (interne Störung) und eine leere Datenbank ohne Nutztabelle.
            if schalter["d1_ausfall"] and "sqlite_master" not in koerper["sql"]:
                return {"success": False, "errors": [{"code": 7403, "message": "internal error"}]}
            if "sqlite_master" in koerper["sql"]:
                if schalter["d1_leer"]:
                    return {"success": True, "result": [{"results": []}]}
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

        # ---- F-E1: D1-Störung (HTTP 200, success=false) wird NICHT zur
        # leeren Tabelle. Vorher lieferte die Abfrage [] und der Export galt
        # als vollständig – der Klick-Zähler wäre still auf 0 zurückgefallen.
        schalter["d1_ausfall"] = True
        try:
            exportieren(env)
            raise AssertionError("F-E1: D1-Störung darf den Export nicht still leeren")
        except RuntimeError as e:
            assert "Tabelle klicks" in str(e) and "7403" in str(e), str(e)
        schalter["d1_ausfall"] = False

        # ---- F-E2: leere D1-Datenbank ist ein Befund, kein grünes „0 Zeilen“.
        schalter["d1_leer"] = True
        try:
            exportieren(env)
            raise AssertionError("F-E2: Datenbank ohne Nutztabelle muss auffallen")
        except RuntimeError as e:
            assert "keine Nutztabelle" in str(e), str(e)
        schalter["d1_leer"] = False

        # ---- F-E3: Ein KV-Export ohne einen einzigen Schlüssel ist keine
        # Sicherung – außer der Namespace wurde live als leer bestätigt.
        leer = {"version": 1, "kv": {"namespace": "ns", "anzahl": 0, "werte": {}, "ablauf": {}}}
        assert any("kein einziger KV-Schlüssel" in f for f in pruefen(leer)), \
            "F-E3: leerer Export galt als vollständig"
        leer_bestaetigt = dict(leer, leer_bestaetigt=True, kv=dict(leer["kv"], titel="ABO"))
        assert pruefen(leer_bestaetigt) == [], pruefen(leer_bestaetigt)

        # ---- F-E4: Leerstand wird live belegt (Namespace-Titel), nicht
        # behauptet – und ohne lesbaren Namespace fail-closed abgebrochen.
        # 03.11.2026 (#923): Die `::warning::`-Meldung des belegten Leerstands
        # gehört in ECHTE Läufe – der Selbsttest fängt sie ein, sonst erzeugt
        # jede Ausführung eine falsche Annotation im Actions-Lauf (belegt an
        # Lauf 41533983322). Eingefangen wird ausdrücklich MIT Gegenprobe:
        # Die Meldung muss weiterhin ausgegeben werden, nur eben nicht hier.
        original = kv_schluessel
        try:
            globals()["kv_schluessel"] = lambda t, k, n: []
            errpuffer = io.StringIO()
            with redirect_stderr(errpuffer):
                belegt = exportieren({"CF_API_TOKEN": "tok", "CF_ACCOUNT_ID": "acc", "KV_NAMESPACE_ID": "ns"})
                assert belegt.get("leer_bestaetigt") is True and belegt["kv"]["titel"] == "ABO", belegt
                assert pruefen(belegt) == []
                schalter["ns_unlesbar"] = True
                try:
                    exportieren({"CF_API_TOKEN": "tok", "CF_ACCOUNT_ID": "acc", "KV_NAMESPACE_ID": "ns"})
                    raise AssertionError("F-E4: nicht lesbarer Namespace darf nicht als leer gelten")
                except RuntimeError as e:
                    assert "nicht lesbar" in str(e), str(e)
            assert "::warning::" in errpuffer.getvalue() and "belegt leer" in errpuffer.getvalue(), \
                "F-E4: der belegte Leerstand muss im echten Lauf eine Workflow-Warnung bleiben"
        finally:
            globals()["kv_schluessel"] = original
            schalter["ns_unlesbar"] = False

        # ---- F-E5: Was beim Rückspielen still abläuft, wird vorher benannt
        # (und eine leere Rückspiel-Datei ist ein Fehler, kein Erfolg).
        abgelaufen = json.loads(json.dumps(ex))
        abgelaufen["kv"]["ablauf"]["abo:a@x.de"] = 1000
        assert ablauf_verlust(abgelaufen, jetzt=2_000_000_000) == ["abo:a@x.de"], \
            "F-E5: abgelaufener Schlüssel wird beim Rückspielen nicht gemeldet"
        assert len(wrangler_bulk(abgelaufen)) == 3
        alle_abgelaufen = json.loads(json.dumps(ex))
        alle_abgelaufen["kv"]["ablauf"] = {n: 1000 for n in ex["kv"]["werte"]}
        assert len(ablauf_verlust(alle_abgelaufen, jetzt=2_000_000_000)) == 4
        with tempfile.TemporaryDirectory() as ordner:
            datei = os.path.join(ordner, "alle.json")
            with open(datei, "w", encoding="utf-8") as fh:
                json.dump(alle_abgelaufen, fh)
            fertig = subprocess.run([sys.executable, __file__, "--wrangler-bulk", datei],
                                    capture_output=True, text=True, timeout=60)
            assert fertig.returncode == 1, f"F-E5: leere Rückspiel-Datei war grün ({fertig.returncode})"
            assert "LEER" in fertig.stderr, fertig.stderr
            assert fertig.stdout.strip() == "[]", fertig.stdout

        # ---- F-E6: Eine Probe, die den Export bemängelt, beendet den
        # Export-Lauf rot – kein Hochladen einer Datei, die sie selbst ablehnt.
        # (Die Datei entsteht trotzdem: Sie hilft bei der Diagnose, aber sie
        # wird nicht abgelegt, weil der Workflow nach Exit 1 abbricht.)
        with tempfile.TemporaryDirectory() as ordner:
            ziel = os.path.join(ordner, "export.json")
            fehlend = {"version": 1,
                       "kv": {"namespace": "ns", "anzahl": 5,
                              "werte": {"abo:a@x.de": json.dumps({"status": "active"})},
                              "ablauf": {}}}
            # 03.11.2026 (#923): `::error::Probe: …` ist für den echten Lauf
            # gedacht. Uneingefangen wurde aus dem Selbsttest eine echte
            # failure-Annotation („Probe: Anzahl 5 != 1 Werte“, Lauf
            # 41533983322) – mitten in einem erfolgreichen Schritt.
            outpuffer, errpuffer = io.StringIO(), io.StringIO()
            with redirect_stdout(outpuffer), redirect_stderr(errpuffer):
                aus = main(["--out", ziel], _export=lambda _env: fehlend)
            assert aus == 1, f"F-E6: unvollständiger Export war grün ({aus})"
            assert "::error::Probe:" in outpuffer.getvalue(), \
                "F-E6: der Probe-Befund muss im echten Lauf eine Annotation bleiben"
            assert "NICHTS" in errpuffer.getvalue() or "nichts abgelegt" in errpuffer.getvalue(), \
                "F-E6: der Abbruch bleibt ausdrücklich benannt (kein stilles Rot)"

        # ---- F-E7: Eine Störung der Cloudflare-API wird als Satz gemeldet,
        # nicht als Traceback (im Actions-Log ist der Stack keine Abhilfe).
        echt_netz = _http
        try:
            def kaputtes_netz(*_a, **_k):
                raise urllib.error.URLError("TLS/SSL connection has been closed")
            globals()["_http"] = kaputtes_netz
            HTTP = kaputtes_netz
            with tempfile.TemporaryDirectory() as ordner:
                ziel = os.path.join(ordner, "nichts.json")
                vorher = dict(os.environ)
                try:
                    os.environ.clear()
                    os.environ.update({"CF_API_TOKEN": "tok", "CF_ACCOUNT_ID": "acc",
                                       "KV_NAMESPACE_ID": "ns"})
                    # 03.11.2026 (#923): Die Störungsmeldung ist eine
                    # Workflow-Annotation – im Selbsttest wird sie eingefangen,
                    # nicht ins Log entlassen (sonst „failure“ im grünen Lauf).
                    errpuffer = io.StringIO()
                    with redirect_stderr(errpuffer):
                        rc = main(["--out", ziel])
                    assert "::error::KV-Export abgebrochen:" in errpuffer.getvalue(), \
                        "F-E7: die Störungsmeldung muss im echten Lauf eine Annotation bleiben"
                finally:
                    os.environ.clear()
                    os.environ.update(vorher)
                assert rc == 1, f"F-E7: Netzausfall war grün ({rc})"
                assert not os.path.exists(ziel), "F-E7: bei Netzausfall darf keine Exportdatei entstehen"
        finally:
            globals()["_http"] = echt_netz
        HTTP = gefaelscht
        del schalter
    finally:
        HTTP = echt
    print("✅ kv_backup-Selbsttest: Export, Paginierung, D1, Probe, Bulk-Format, fail-closed "
          "sowie die #923-Fälle (D1-Störung ≠ leere Tabelle, Leerstand nur mit Beleg, "
          "Ablaufverlust beim Rückspielen, Probe-Befund beendet den Export rot). "
          "Seit 03.11.2026 entlässt der Selbsttest keine ::error::/::warning::-Befehle mehr "
          "in das echte Lauf-Log (F-E4/F-E6/F-E7 fangen sie ein UND prüfen ihr Vorhandensein).")
    return 0


def main(argv=None, *, _export=None) -> int:
    """`_export` ist der Prüfhaken des Selbsttests (F-E6): Der echte Lauf
    exportiert immer selbst; der Test setzt einen Export mit bekanntem
    Mangel ein, damit die Schleuse (Probe-Befund → Exit 1) wirklich
    ausgeführt wird und nicht nur im Code steht."""
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
            # Was beim Rückspielen still verschwindet, wird VORHER gesagt
            # (#923): Eine leere Rückspiel-Datei darf nicht als Erfolg
            # durchgehen. Der Hinweis geht auf stderr, die Datei bleibt stdout
            # (der Aufruf leitet sie um).
            verloren = ablauf_verlust(ex)
            if verloren:
                print(f"::warning::{len(verloren)} Schlüssel sind beim Rückspielen bereits "
                      f"abgelaufen und werden übersprungen: "
                      f"{', '.join(_kennung(n) for n in verloren[:10])}"
                      f"{' …' if len(verloren) > 10 else ''}", file=sys.stderr)
            bulk = wrangler_bulk(ex)
            if not bulk:
                print("::error::Die Rückspiel-Datei wäre LEER – es würde nichts "
                      "wiederhergestellt. Export prüfen (Ablaufzeiten, Systemzeit) statt "
                      "ein leeres Ergebnis als Erfolg zu melden.", file=sys.stderr)
                json.dump(bulk, sys.stdout, ensure_ascii=False)
                return 1
            json.dump(bulk, sys.stdout, ensure_ascii=False)
            return 0
        fehler = pruefen(ex)
        for f in fehler:
            print(f"❌ {f}")
        print(("✅ " if not fehler else "🛑 ") + "Probe: " + zusammenfassung(ex))
        return 1 if fehler else 0
    if not a.out:
        ap.error("--out, --pruefen, --wrangler-bulk oder --selftest angeben")
    try:
        ex = (_export or exportieren)(dict(os.environ))
    except (RuntimeError, urllib.error.URLError, OSError) as fehler:
        # NetzwekFehler ist ein RuntimeError; URLError/OSError stehen hier für
        # den Fall, dass die HTTP-Schicht ersetzt wurde (Selbsttest) oder eine
        # Störung vor der Umwandlung auftritt. Immer eine Zeile, nie ein Stack.
        print(f"::error::KV-Export abgebrochen: {fehler}", file=sys.stderr)
        print("🛑 Es wurde NICHTS gesichert – kein Schein-Grün (fail-closed).", file=sys.stderr)
        return 1
    fehler = pruefen(ex)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(ex, fh, ensure_ascii=False)
    os.chmod(a.out, 0o600)
    # Nur Zaehler ins Log – keine Adressen, keine Tokens.
    print(f"KV-Export: {zusammenfassung(ex)}")
    if fehler:
        # #923 (02.11.2026): Früher waren das nur Warnungen – der Workflow
        # schrieb die Datei, verschlüsselte sie und lud sie hoch, und der Job
        # war grün. Eine Sicherung, deren eigene Probe sie bemängelt, ist
        # keine Sicherung: Exit 1, damit kein unvollständiger Export als
        # „erledigt“ in der Ablage landet.
        for f in fehler[:20]:
            print(f"::error::Probe: {f}")
        print("🛑 Export ist nicht vollständig bzw. nicht konsistent – "
              "es wird nichts abgelegt (fail-closed).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
