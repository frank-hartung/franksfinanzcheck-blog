#!/usr/bin/env python3
"""
OFFLINE-IMPORT – der manuelle Weg der Provisionen in die Umsatz-Messkette

WARUM: Die Provision ist die einzige Zahl der Messkette, die kein Automat
liefert: Sie steht in den Abrechnungen der Partner (CHECK24, Tarifcheck,
C24 Bank). Ohne diesen Import meldet `data/revenue_funnel.json` für Anträge,
Abschlüsse, Provision und EPC nur `null` – „unbekannt“ statt Messwert. Dieser
Import macht aus der lokalen Provisions-Tabelle das versionierte Aggregat, das
der Trichter liest.

DIESES SKRIPT:
  1. Liest die Provisions-Tabelle `data/provisionen/provisionen.csv` (lokal,
     gitignored; Schema + Prüfung: `scripts/provisionen_check.py`, Runbook:
     `docs/ANLEITUNG-PROVISIONEN.md`).
  2. Schreibt die Monatsaggregate nach `data/provisionen_aggregat.json` –
     versioniert, weil sie nur Summen je Monat und Partner enthalten: keine
     Abrechnungs-Details, keine Personenbezüge.
  3. Führt seine eigene Provenienz in `data/offline_import.meta.json`
     (`status: ok`, Stand, Zahl der Monate). So sieht der Trichter, wann und
     woher die Zahlen kamen.
  4. Rechnet den Trichter neu (`scripts/revenue_funnel.py`).

EHRLICHE REGELN (Hausrecht der Messkette):
  - Tabelle fehlt/leer ⇒ es wird NIX geschrieben, Exit 0, Hinweis. Ein
    ausgelassener Import darf nie wie „0 € Provision“ aussehen.
  - Nur Aggregat je Monat im Repo – keine Zeilen, keine Abrechnungsnummern.
  - Zeilen mit ungültigem Monat oder Betrag werden verworfen, nicht repariert.

Nutzung:
  python3 scripts/offline_import.py --template   # Tabelle aus der Vorlage anlegen
  python3 scripts/offline_import.py              # importieren + Trichter neu rechnen
  python3 scripts/offline_import.py --dry-run    # zeigen, was passieren würde
  python3 scripts/offline_import.py --status     # Stand der Messkette
  python3 scripts/offline_import.py --selftest

Exit-Codes: 0 = importiert oder sauber übersprungen, 1 = Tabelle nicht
             anlegbar, 2 = Selbsttest/Hausfehler.
Runbook: docs/UMSATZ-MESSUNG-PREMIUM.md – oder kurz:
`npm run mess:vorlage` → Tabelle ausfüllen → `npm run mess:import`.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import re
import shutil
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

DATA = os.path.join(BLOG_DIR, "data")
PROVISIONEN = os.path.join(DATA, "provisionen", "provisionen.csv")
VORLAGE = os.path.join(DATA, "provisionen", "provisionen-vorlage.csv")
# Aggregat der Monatssummen – die einzige Provisions-Datei, die versioniert
# werden darf (keine Abrechnungs-Details, keine Personenbezüge).
PROVISIONEN_AGG = os.path.join(DATA, "provisionen_aggregat.json")
# Eigene Meta des Imports: sie dokumentiert Stand und Herkunft der Zahlen.
OFFLINE_META = os.path.join(DATA, "offline_import.meta.json")
# Zustand des eigenen Klickzählers (nur zur Anzeige in --status).
KLICK_META = os.path.join(DATA, "klicks_eigen.meta.json")

TODAY = datetime.date.today()


def to_int(v, default=0) -> int:
    try:
        n = int(float(str(v).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return default
    return max(0, min(10 ** 9, n))


# ------------------------------------------------------------------ Provisions-Tabelle

def read_provisionen(path: str | None = None) -> dict:
    """Monatssummen der Partnerabrechnungen → Provision TRUE für den Trichter.

    Die Datei ist bewusst NICHT versioniert (`data/provisionen/provisionen.csv`
    liegt nur lokal, Schema + Prüfung: `scripts/provisionen_check.py`).
    Unbekannt bleibt unbekannt: fehlt die Datei, liefert das {} – der Trichter
    schreibt dann nirgends eine 0 hin.
    """
    try:
        with open(path or PROVISIONEN, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return {}
    zeilen = []
    try:
        for row in csv.DictReader(io.StringIO(text)):
            monat = str(row.get("monat") or "").strip()
            if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", monat):
                continue
            provision = str(row.get("provision_eur") or "0").strip().replace(",", ".")
            if not re.fullmatch(r"\d+(\.\d{1,2})?", provision):
                continue
            zeilen.append({
                "monat": monat,
                "partner": str(row.get("partner") or "sonstig").strip()[:40],
                "abschluesse": to_int(row.get("abschluesse")),
                "stornos": to_int(row.get("stornos")),
                "provision_eur": round(float(provision), 2),
            })
    except (csv.Error, ValueError):
        return {}
    if not zeilen:
        return {}
    monate = {}
    for z in zeilen:
        m = monate.setdefault(z["monat"], {"monat": z["monat"], "partner": set(),
                                           "abschluesse": 0, "stornos": 0,
                                           "provision_eur": 0.0})
        m["partner"].add(z["partner"])
        m["abschluesse"] += z["abschluesse"]
        m["stornos"] += z["stornos"]
        m["provision_eur"] = round(m["provision_eur"] + z["provision_eur"], 2)
    monatsliste = sorted(monate.values(), key=lambda d: d["monat"])
    letzter = monatsliste[-1]
    return {
        "monate": [{**m, "partner": sorted(m["partner"])} for m in monatsliste],
        "summe": {
            "monate": len(monatsliste),
            "abschluesse": sum(m["abschluesse"] for m in monatsliste),
            "stornos": sum(m["stornos"] for m in monatsliste),
            "provision_eur": round(sum(m["provision_eur"] for m in monatsliste), 2),
        },
        "letzter_monat": letzter["monat"],
        "provision_letzter_monat": letzter["provision_eur"],
        "written": TODAY.isoformat(),
        "quelle": "provisionen-tabelle (manuell, Abrechnungsnummer je Zeile)",
    }


# ------------------------------------------------------------------ Schreiben

def _write_atomic(path: str, text: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _read_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def import_provisionen(dry_run: bool = False, provisionen: str | None = None,
                       ziele: dict | None = None) -> dict:
    """Provisions-Tabelle → Aggregat + Meta. Gibt die Zusammenfassung zurück.

    `ziele` überschreibt die Zielpfade, `provisionen` den Pfad der Tabelle:
    Selbsttests und Unit-Tests laufen damit in einer Wegwerf-Kopie und fassen
    den echten Repo-Bestand nie an.
    """
    z = ziele or {}
    p_agg = z.get("provisionen_agg", PROVISIONEN_AGG)
    p_meta = z.get("offline_meta", OFFLINE_META)
    quelle = provisionen or PROVISIONEN
    prov = read_provisionen(quelle)
    if not prov:
        return {"status": "leer", "datei": quelle}
    summary = {
        "status": "ok",
        "datei": quelle,
        "monate": len(prov.get("monate") or []),
        "letzter_monat": prov.get("letzter_monat"),
        "provisionen": prov,
    }
    if dry_run:
        return summary
    _write_atomic(p_agg, json.dumps(prov, ensure_ascii=False, indent=2) + "\n")
    # Herkunfts-Nachweis: der Trichter liest Stand und Zahl der Monate hieraus.
    _write_atomic(p_meta, json.dumps({
        "written": TODAY.isoformat(),
        "status": "ok",
        "quelle": "provisionen-tabelle (manuell)",
        "provisionen_monate": summary["monate"],
        "letzter_monat": summary["letzter_monat"],
        "written_files": [os.path.relpath(p_agg, BLOG_DIR)],
    }, ensure_ascii=False, indent=2) + "\n")
    return summary


def status(provisionen: str | None = None, ziele: dict | None = None,
           klick_meta: str | None = None) -> dict:
    """Stand der Provisions-Brücke + Zustand des Klickzählers (read-only)."""
    z = ziele or {}
    meta = _read_json(z.get("offline_meta", OFFLINE_META), {})
    kmeta = _read_json(klick_meta or KLICK_META, {})
    prov = read_provisionen(provisionen or PROVISIONEN)
    return {
        "tabelle_da": os.path.isfile(provisionen or PROVISIONEN),
        "zuletzt_importiert": meta.get("written", "nie"),
        "import_status": meta.get("status", "unbekannt"),
        "provision_monate": len(prov.get("monate") or []),
        "provision_summe": (prov.get("summe") or {}).get("provision_eur"),
        "letzter_monat": prov.get("letzter_monat", "unbekannt"),
        "klickzaehler_status": kmeta.get("status", "nie versucht"),
    }


def anlegen(ziel: str | None = None, vorlage: str | None = None, force: bool = False) -> int:
    """Provisions-Tabelle aus der versionierten Vorlage (nur Kopfzeile) anlegen."""
    ziel = ziel or PROVISIONEN
    vorlage = vorlage or VORLAGE
    if os.path.exists(ziel) and not force:
        print(f"⛔ existiert bereits: {os.path.relpath(ziel, BLOG_DIR)} "
              f"(--force überschreibt nicht ungefragt)")
        return 1
    if not os.path.isfile(vorlage):
        print(f"⛔ Vorlage fehlt: {os.path.relpath(vorlage, BLOG_DIR)}")
        return 1
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    shutil.copyfile(vorlage, ziel)
    print(f"📝 Tabelle angelegt: {os.path.relpath(ziel, BLOG_DIR)} – Monatssummen "
          f"eintragen (Schema: docs/ANLEITUNG-PROVISIONEN.md), dann "
          f"`python3 scripts/offline_import.py`")
    return 0


# ------------------------------------------------------------------ Selftest

def _selftest() -> int:
    import tempfile
    failures = []
    # 1) Zahlen: Müll wird 0, nie ein Absturz; Obergrenze schützt vor Unsinn
    for raw, want in (("12", 12), ("3,7", 3), ("x", 0), (None, 0), ("-4", 0),
                      ("99999999999", 10 ** 9)):
        if to_int(raw) != want:
            failures.append(f"to_int({raw!r}) = {to_int(raw)}, erwartet {want}")
    with tempfile.TemporaryDirectory() as td:
        z = {k: os.path.join(td, f"{k}.json") for k in ("provisionen_agg", "offline_meta")}
        pv = os.path.join(td, "provisionen.csv")
        # 2) Leere Quelle erfindet nichts – und die Sandbox fasst den echten Bestand nie an
        if import_provisionen(provisionen=pv, ziele=z)["status"] != "leer":
            failures.append("fehlende Tabelle muss status=leer melden")
        with open(pv, "w", encoding="utf-8") as fh:
            fh.write("monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n")
        if import_provisionen(provisionen=pv, ziele=z)["status"] != "leer":
            failures.append("Tabelle nur mit Kopfzeile muss status=leer melden (unbekannt ≠ 0)")
        for pfad in z.values():
            if os.path.exists(pfad):
                failures.append("leere Quelle hat in der Sandbox Dateien geschrieben")
        # 3) Monatsaggregate, keine erfundenen Nullen
        with open(pv, "w", encoding="utf-8") as fh:
            fh.write("monat,partner,abschluesse,stornos,provision_eur,abrechnung_ref,notiz\n")
            fh.write("2026-09,CHECK24,3,1,49.50,CHECK24-Abr-2026-09,\n")
            fh.write("2026-09,Tarifcheck,1,0,18.00,TC-2026-09,\n")
            fh.write("falsch,CHECK24,9,9,9.00,x,\n")
            fh.write("2026-08,CHECK24,2,0,zwölf,x,\n")
        pr = read_provisionen(pv)
        if pr["summe"]["abschluesse"] != 4 or pr["summe"]["provision_eur"] != 67.5:
            failures.append(f"Provisions-Aggregat: {pr}")
        if len(pr["monate"]) != 1 or len(pr["monate"][0]["partner"]) != 2:
            failures.append("Partner je Monat nicht zusammengeführt oder ungültige Zeile nicht verworfen")
        if read_provisionen(os.path.join(td, "keine.csv")):
            failures.append("fehlende Provisionsdatei muss leer sein (unbekannt ≠ 0)")
        # 4) dry-run schreibt nichts
        if import_provisionen(dry_run=True, provisionen=pv, ziele=z)["status"] != "ok" \
                or any(os.path.exists(p) for p in z.values()):
            failures.append("dry-run schreibt oder meldet nicht ok")
        # 5) Echter Durchschrieb – alles in der Wegwerf-Kopie, mit Herkunfts-Meta
        res = import_provisionen(provisionen=pv, ziele=z)
        if res["status"] != "ok" or res["monate"] != 1:
            failures.append(f"Import-Zusammenfassung: {res}")
        meta = _read_json(z["offline_meta"], {})
        if meta.get("status") != "ok" or meta.get("provisionen_monate") != 1 \
                or meta.get("written") != TODAY.isoformat():
            failures.append(f"Meta-Herkunft fehlt: {meta}")
        if _read_json(z["provisionen_agg"], {}).get("letzter_monat") != "2026-09":
            failures.append("Aggregat der Abrechnungstabelle wurde nicht geschrieben")
        if any(k in json.dumps(_read_json(z["provisionen_agg"], {})) for k in ("abrechnung_ref", "CHECK24-Abr")):
            failures.append("Abrechnungsnummern gehören nicht ins öffentliche Aggregat")
        st = status(provisionen=pv, ziele=z, klick_meta=os.path.join(td, "keine.meta.json"))
        if st["import_status"] != "ok" or st["provision_monate"] != 1 \
                or st["klickzaehler_status"] != "nie versucht":
            failures.append(f"status() meldet den Stand falsch: {st}")
        # 6) Vorlage anlegen: nichts überschreiben, ohne es zu sagen
        vorl = os.path.join(td, "vorlage.csv")
        ziel = os.path.join(td, "sub", "neu.csv")
        with open(vorl, "w", encoding="utf-8") as fh:
            fh.write("monat,partner\n")
        if anlegen(ziel=ziel, vorlage=vorl) != 0 or not os.path.isfile(ziel):
            failures.append("Tabelle wird nicht aus der Vorlage angelegt")
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write("monat,partner\n2026-09,CHECK24\n")
        if anlegen(ziel=ziel, vorlage=vorl) != 1 or "CHECK24" not in open(ziel, encoding="utf-8").read():
            failures.append("bestehende Tabelle wurde ohne --force überschrieben")
    if failures:
        print("❌ OFFLINE-IMPORT-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ OFFLINE-IMPORT-SELFTEST bestanden (Provisions-Aggregat, leer≠0, "
          "Meta-Herkunft, dry-run, Vorlage, keine Abrechnungsnummern im Repo).")
    return 0


def run_funnel() -> int:
    try:
        import revenue_funnel
    except ImportError:  # pragma: no cover
        print("::warning:: revenue_funnel.py nicht importierbar – Trichter im "
              "nächsten Importlauf aktualisiert")
        return 0
    return revenue_funnel.main([])


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--status" in argv:
        st = status()
        print("Offline-Import – Stand der Messkette")
        for k, v in st.items():
            print(f"  {k:22} {v}")
        return 0
    if "--template" in argv:
        return anlegen(force="--force" in argv)
    res = import_provisionen(dry_run="--dry-run" in argv or "--print" in argv)
    if "--print" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if res.get("status") == "leer":
        print(f"⏭️  Keine befüllte Provisions-Tabelle gefunden "
              f"({os.path.relpath(res['datei'], BLOG_DIR)}) – Datenlücke bleibt "
              f"dokumentiert, keine erfundenen Nullen.")
        print("    Vorlage: python3 scripts/offline_import.py --template")
        return 0
    if "--dry-run" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    summe = (res["provisionen"].get("summe") or {}).get("provision_eur") or 0.0
    print(f"📥 Provisions-Import: {res['monate']} Monate · "
          f"letzter Monat {res['letzter_monat']} · {summe:.2f} € gesamt")
    return run_funnel()


if __name__ == "__main__":
    sys.exit(main())
