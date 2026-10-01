#!/usr/bin/env python3
# ============================================================
#  SCHALTWERK – der eigene Zapier-Nachbau (Trigger → Filter → Aktion)
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 01.10.2026): Vollautomatisierung der Social-Media-
#  Kanäle OHNE Zapier, OHNE Zapier-API, OHNE laufende Kosten. Statt
#  eines externen Dienstes läuft die Verdrahtung hier im Repository:
#  GitHub Actions ist der Scheduler, dieses Skript ist die Engine,
#  `data/automationen.yaml` ist die Regelsammlung ("Zaps").
#
#  WAS ZAPIER KANN – UND WO ES HIER STEHT
#    Zapier-Begriff      Hier
#    ------------------  ------------------------------------------
#    Zap                 Regel in data/automationen.yaml
#    Trigger             scripts/schaltwerk_triggers.py
#    Filter / Paths      filter: [...] je Regel (Operatorenliste)
#    Action              scripts/schaltwerk_actions.py
#    Multi-Step-Zap      aktionen: [...] (Liste, der Reihe nach)
#    Task-History        data/schaltwerk_log.jsonl + Cockpit
#    Dedupe/Throttle     dedupe_key + throttle je Regel (State)
#    Webhooks            repository_dispatch → --event <json>
#    Task-Limit/Kosten   entfällt (GitHub Actions, öffentliches Repo)
#
#  LEITPLANKEN (nicht aufweichen):
#    · FAIL-SAFE: Eine kaputte Regel darf nie den Lauf killen. Fehler
#      werden protokolliert, die übrigen Regeln laufen weiter.
#    · STANDBY IST KEIN FEHLER: Fehlt einem Kanal sein Token, meldet
#      die Aktion "standby" – grüner Lauf, sichtbar im Cockpit.
#    · AGENT REACH BLEIBT LESEND: Recherche-Signale werden nur als
#      Trigger genutzt und für die menschliche Kuratierung abgelegt –
#      nie direkt gepostet (docs/ANLEITUNG-AGENT-REACH.md, Abschnitt 6).
#    · KOSTEN-REGEL: keine kostenpflichtige Fremd-API im Pflichtpfad.
#
#  AUFRUF:
#    python3 scripts/schaltwerk.py --run            # scharf
#    python3 scripts/schaltwerk.py --dry-run        # zeigt nur an
#    python3 scripts/schaltwerk.py --list           # Regeln auflisten
#    python3 scripts/schaltwerk.py --status         # Cockpit neu schreiben
#    python3 scripts/schaltwerk.py --selftest       # offline, fail-closed
#    python3 scripts/schaltwerk.py --run --regel neuer-artikel-social
#    python3 scripts/schaltwerk.py --run --event '{"typ":"webhook",...}'
# ============================================================
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from datetime import datetime, timedelta, timezone

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

REGELN_PATH = os.path.join(BLOG_DIR, "data", "automationen.yaml")
STATE_PATH = os.path.join(BLOG_DIR, "data", "schaltwerk_state.json")
LOG_PATH = os.path.join(BLOG_DIR, "data", "schaltwerk_log.jsonl")
COCKPIT_PATH = os.path.join(BLOG_DIR, "SCHALTWERK-STATUS.md")

STATE_KEEP_DAYS = 45
LOG_KEEP_LINES = 4000


# --------------------------------------------------------------------- Zeit
def _eu_offset(dt_utc: datetime) -> int:
    """Sommerzeit-Offset für Europe/Berlin ohne externe Bibliothek."""
    jahr = dt_utc.year
    maerz = datetime(jahr, 3, 31, 1, 0, tzinfo=timezone.utc)
    maerz -= timedelta(days=(maerz.weekday() + 1) % 7)
    oktober = datetime(jahr, 10, 31, 1, 0, tzinfo=timezone.utc)
    oktober -= timedelta(days=(oktober.weekday() + 1) % 7)
    return 2 if maerz <= dt_utc < oktober else 1


def berlin_now() -> datetime:
    jetzt = datetime.now(timezone.utc)
    return jetzt + timedelta(hours=_eu_offset(jetzt))


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def parse_dt(wert: str) -> datetime | None:
    if not wert:
        return None
    try:
        return datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except ValueError:
        return None


# ------------------------------------------------------------------ Dateien
def load_regeln(pfad: str | None = None) -> dict:
    """Lädt data/automationen.yaml. Unlesbar → leeres Regelwerk (fail-safe)."""
    import yaml

    pfad = pfad or REGELN_PATH
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {"version": 1, "meta": {}, "regeln": []}
    except Exception as exc:  # noqa: BLE001 – Konfig darf den Lauf nie killen
        print(f"⚠ automationen.yaml nicht lesbar ({exc}) – Schaltwerk läuft leer.")
        return {"version": 1, "meta": {}, "regeln": []}
    daten.setdefault("meta", {})
    daten.setdefault("regeln", [])
    return daten


def load_state(pfad: str | None = None) -> dict:
    pfad = pfad or STATE_PATH
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = json.load(fh) or {}
    except (FileNotFoundError, json.JSONDecodeError):
        daten = {}
    daten.setdefault("version", 1)
    daten.setdefault("ausgeloest", {})      # "<regel>::<dedupe>" → ISO-Zeit
    daten.setdefault("zaehler", {})         # "<regel>" → {"JJJJ-MM-TT": n}
    daten.setdefault("letzter_lauf", {})    # "<regel>" → ISO-Zeit
    daten.setdefault("slots", {})           # "<regel>::<slot>" → ISO-Zeit
    daten.setdefault("marker", {})          # freie Merker der Trigger
    return daten


def save_state(state: dict, pfad: str | None = None) -> None:
    pfad = pfad or STATE_PATH
    prune_state(state)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = f"{pfad}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, pfad)


def prune_state(state: dict, keep_days: int = STATE_KEEP_DAYS) -> dict:
    """Alte Dedupe-Marken verfallen – sonst wächst der State unbegrenzt."""
    grenze = berlin_now() - timedelta(days=keep_days)
    for feld in ("ausgeloest", "slots"):
        behalten = {}
        for key, wert in (state.get(feld) or {}).items():
            dt = parse_dt(wert)
            if dt is None or dt.replace(tzinfo=None) >= grenze.replace(tzinfo=None):
                behalten[key] = wert
        state[feld] = behalten
    tag_grenze = (berlin_now() - timedelta(days=keep_days)).date().isoformat()
    for regel, tage in list((state.get("zaehler") or {}).items()):
        state["zaehler"][regel] = {t: n for t, n in (tage or {}).items() if t >= tag_grenze}
        if not state["zaehler"][regel]:
            state["zaehler"].pop(regel, None)
    return state


def log_append(eintraege: list[dict], pfad: str | None = None) -> None:
    """Task-History (wie Zapiers Task-Log), eine JSON-Zeile je Aktion."""
    if not eintraege:
        return
    pfad = pfad or LOG_PATH
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "a", encoding="utf-8") as fh:
        for e in eintraege:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    _log_trim(pfad)


def _log_trim(pfad: str, keep: int = LOG_KEEP_LINES) -> None:
    try:
        with open(pfad, encoding="utf-8") as fh:
            zeilen = fh.readlines()
    except OSError:
        return
    if len(zeilen) <= keep:
        return
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.writelines(zeilen[-keep:])


def log_read(pfad: str | None = None, limit: int = 200) -> list[dict]:
    pfad = pfad or LOG_PATH
    try:
        with open(pfad, encoding="utf-8") as fh:
            zeilen = fh.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for z in zeilen:
        try:
            out.append(json.loads(z))
        except json.JSONDecodeError:
            continue
    return out


# ------------------------------------------------------- Werte & Templates
def get_path(daten: dict, pfad: str):
    """Punktpfad-Zugriff: 'artikel.slug' → daten['artikel']['slug']."""
    wert = daten
    for teil in str(pfad).split("."):
        if isinstance(wert, dict):
            wert = wert.get(teil)
        elif isinstance(wert, (list, tuple)):
            try:
                wert = wert[int(teil)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if wert is None:
            return None
    return wert


_TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.\[\]]+)\s*\}\}|\{([a-zA-Z0-9_.]+)\}")


def render(text, daten: dict):
    """Platzhalter füllen: '{artikel.title}' oder '{{ artikel.title }}'."""
    if isinstance(text, list):
        return [render(t, daten) for t in text]
    if isinstance(text, dict):
        return {k: render(v, daten) for k, v in text.items()}
    if not isinstance(text, str):
        return text

    def ersetze(m):
        schluessel = m.group(1) or m.group(2)
        wert = get_path(daten, schluessel)
        if wert is None:
            return ""
        if isinstance(wert, (dict, list)):
            return json.dumps(wert, ensure_ascii=False)
        return str(wert)

    return _TEMPLATE_RE.sub(ersetze, text)


# ----------------------------------------------------------------- Filter
def _zahl(wert):
    try:
        return float(str(wert).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def pruefe_filter(bedingung: dict, daten: dict) -> tuple[bool, str]:
    """Ein Filter. Rückgabe: (erfüllt?, Begründung)."""
    feld = bedingung.get("feld") or ""
    op = (bedingung.get("operator") or "nicht_leer").strip()
    soll = bedingung.get("wert")
    ist = get_path(daten, feld) if feld else None
    ist_txt = "" if ist is None else str(ist)
    soll_txt = "" if soll is None else str(soll)

    def ergebnis(ok: bool) -> tuple[bool, str]:
        return ok, f"{feld} {op} {soll_txt!r} → ist {ist_txt[:60]!r}"

    if op in ("gleich", "=="):
        return ergebnis(ist_txt.strip().lower() == soll_txt.strip().lower())
    if op in ("ungleich", "!="):
        return ergebnis(ist_txt.strip().lower() != soll_txt.strip().lower())
    if op == "enthaelt":
        return ergebnis(soll_txt.lower() in ist_txt.lower())
    if op == "enthaelt_nicht":
        return ergebnis(soll_txt.lower() not in ist_txt.lower())
    if op == "enthaelt_eines":
        kandidaten = soll if isinstance(soll, list) else [soll]
        return ergebnis(any(str(k).lower() in ist_txt.lower() for k in kandidaten))
    if op == "beginnt_mit":
        return ergebnis(ist_txt.lower().startswith(soll_txt.lower()))
    if op == "endet_mit":
        return ergebnis(ist_txt.lower().endswith(soll_txt.lower()))
    if op == "regex":
        try:
            return ergebnis(bool(re.search(soll_txt, ist_txt, re.IGNORECASE)))
        except re.error:
            return False, f"{feld}: ungültiger regulärer Ausdruck {soll_txt!r}"
    if op in ("groesser", ">"):
        a, b = _zahl(ist), _zahl(soll)
        return ergebnis(a is not None and b is not None and a > b)
    if op in ("groesser_gleich", ">="):
        a, b = _zahl(ist), _zahl(soll)
        return ergebnis(a is not None and b is not None and a >= b)
    if op in ("kleiner", "<"):
        a, b = _zahl(ist), _zahl(soll)
        return ergebnis(a is not None and b is not None and a < b)
    if op in ("kleiner_gleich", "<="):
        a, b = _zahl(ist), _zahl(soll)
        return ergebnis(a is not None and b is not None and a <= b)
    if op == "ist_wahr":
        return ergebnis(ist is True or ist_txt.strip().lower() in ("true", "1", "ja", "yes"))
    if op == "ist_falsch":
        return ergebnis(ist is False or ist is None
                        or ist_txt.strip().lower() in ("false", "0", "nein", "no", ""))
    if op == "leer":
        return ergebnis(not ist_txt.strip())
    if op == "nicht_leer":
        return ergebnis(bool(ist_txt.strip()))
    if op == "in_liste":
        kandidaten = soll if isinstance(soll, list) else [soll]
        return ergebnis(ist_txt.strip().lower() in [str(k).strip().lower() for k in kandidaten])
    if op == "laenger_als":
        b = _zahl(soll)
        return ergebnis(b is not None and len(ist_txt) > b)
    if op == "kuerzer_als":
        b = _zahl(soll)
        return ergebnis(b is not None and len(ist_txt) < b)
    return False, f"{feld}: unbekannter Operator {op!r}"


def filter_erfuellt(regel: dict, daten: dict) -> tuple[bool, str]:
    """Alle Filter einer Regel (UND-Verknüpfung, wie Zapiers Filter-Step)."""
    for bedingung in regel.get("filter") or []:
        if not isinstance(bedingung, dict):
            continue
        ok, grund = pruefe_filter(bedingung, daten)
        if not ok:
            return False, grund
    return True, ""


# -------------------------------------------------------------- Throttle
def throttle_ok(regel: dict, state: dict, jetzt: datetime) -> tuple[bool, str]:
    """Frequenzschutz: Tageslimit und Mindestabstand (Anti-Spam)."""
    rid = regel.get("id") or "?"
    th = regel.get("throttle") or {}
    max_tag = int(th.get("max_pro_tag") or 0)
    if max_tag:
        heute = jetzt.date().isoformat()
        genutzt = int(((state.get("zaehler") or {}).get(rid) or {}).get(heute) or 0)
        if genutzt >= max_tag:
            return False, f"Tageslimit erreicht ({genutzt}/{max_tag})"
    cooldown = int(th.get("cooldown_minuten") or 0)
    if cooldown:
        letzter = parse_dt((state.get("letzter_lauf") or {}).get(rid) or "")
        if letzter and (jetzt.replace(tzinfo=None) - letzter.replace(tzinfo=None)) \
                < timedelta(minutes=cooldown):
            return False, f"Sperrfrist aktiv ({cooldown} min)"
    return True, ""


def zaehler_hoch(state: dict, rid: str, jetzt: datetime) -> None:
    heute = jetzt.date().isoformat()
    state.setdefault("zaehler", {}).setdefault(rid, {})
    state["zaehler"][rid][heute] = int(state["zaehler"][rid].get(heute) or 0) + 1
    state.setdefault("letzter_lauf", {})[rid] = iso(jetzt)


def dedupe_key(regel: dict, event: dict) -> str:
    """Eindeutiger Schlüssel: verhindert, dass dasselbe Ereignis doppelt feuert."""
    vorlage = regel.get("dedupe_key")
    if vorlage:
        gerendert = render(str(vorlage), event.get("daten") or {}).strip()
        if gerendert:
            return gerendert
    return str(event.get("key") or "")


# ----------------------------------------------------------------- Lauf
def regel_aktiv(regel: dict) -> bool:
    return bool(regel.get("enabled", True)) and bool(regel.get("id"))


def sammle_events(regel: dict, ctx: dict) -> tuple[list[dict], str]:
    """Fragt den Trigger-Provider der Regel ab. Fehler → leere Liste + Grund."""
    import schaltwerk_triggers as trg

    trigger = regel.get("trigger") or {}
    typ = (trigger.get("typ") or "").strip()
    params = trigger.get("params") or {}
    provider = trg.PROVIDER.get(typ)
    if not provider:
        return [], f"unbekannter Trigger {typ!r}"
    try:
        events = provider(params, ctx) or []
    except Exception as exc:  # noqa: BLE001 – Trigger-Fehler isolieren
        return [], f"Trigger {typ} gescheitert: {exc}"
    saubere = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        ev.setdefault("trigger", typ)
        ev.setdefault("daten", {})
        ev.setdefault("zeit", iso(ctx.get("jetzt") or berlin_now()))
        saubere.append(ev)
    return saubere, ""


def fuehre_aktionen(regel: dict, event: dict, ctx: dict) -> list[dict]:
    """Aktionskette der Regel – Multi-Step-Zap, der Reihe nach."""
    import schaltwerk_actions as act

    ergebnisse = []
    daten = dict(event.get("daten") or {})
    daten.setdefault("jetzt", iso(ctx.get("jetzt") or berlin_now()))
    daten.setdefault("regel", regel.get("id"))
    for nr, aktion in enumerate(regel.get("aktionen") or [], start=1):
        if not isinstance(aktion, dict):
            continue
        typ = (aktion.get("typ") or "").strip()
        params = render(aktion.get("params") or {}, daten)
        handler = act.AKTION.get(typ)
        if not handler:
            ergebnisse.append({"schritt": nr, "typ": typ, "status": "fehler",
                               "meldung": f"unbekannte Aktion {typ!r}"})
            if aktion.get("stoppe_bei_fehler", True):
                break
            continue
        try:
            res = handler(params, daten, ctx)
        except Exception as exc:  # noqa: BLE001 – Aktionen dürfen nie den Lauf killen
            res = {"status": "fehler", "meldung": f"{type(exc).__name__}: {exc}"}
            if ctx.get("verbose"):
                traceback.print_exc()
        res = res if isinstance(res, dict) else {"status": "ok", "meldung": str(res)}
        res.setdefault("status", "ok")
        res.setdefault("meldung", "")
        res["schritt"] = nr
        res["typ"] = typ
        ergebnisse.append(res)
        # Ergebnis der Aktion steht den Folgeschritten zur Verfügung
        daten.setdefault("schritte", {})[str(nr)] = res
        if res["status"] == "fehler" and aktion.get("stoppe_bei_fehler", True):
            break
    return ergebnisse


def run(regeln: dict, *, dry_run: bool = False, nur_regel: str = "",
        event_json: str = "", jetzt: datetime | None = None,
        state: dict | None = None, verbose: bool = False) -> dict:
    """Ein kompletter Schaltwerk-Lauf über alle Regeln."""
    jetzt = jetzt or berlin_now()
    state = state if state is not None else load_state()
    meta = regeln.get("meta") or {}
    max_aktionen = int(meta.get("max_aktionen_pro_lauf") or 25)

    extern = None
    if event_json:
        try:
            extern = json.loads(event_json)
        except json.JSONDecodeError as exc:
            print(f"⚠ --event ist kein gültiges JSON ({exc}) – wird ignoriert.")

    ctx = {
        "jetzt": jetzt,
        "dry_run": dry_run,
        "state": state,
        "meta": meta,
        "blog_dir": BLOG_DIR,
        "event": extern,
        "verbose": verbose,
    }

    bericht = {"zeit": iso(jetzt), "dry_run": dry_run, "regeln": [],
               "aktionen_gesamt": 0, "fehler": 0, "standby": 0, "ausgefuehrt": 0}
    logzeilen = []
    budget = max_aktionen

    for regel in regeln.get("regeln") or []:
        if not isinstance(regel, dict):
            continue
        rid = regel.get("id") or "?"
        zeile = {"id": rid, "name": regel.get("name") or rid,
                 "treffer": 0, "uebersprungen": 0, "aktionen": [], "notiz": ""}

        if not regel_aktiv(regel):
            zeile["notiz"] = "deaktiviert"
            bericht["regeln"].append(zeile)
            continue
        if nur_regel and rid != nur_regel:
            zeile["notiz"] = "nicht angefragt"
            bericht["regeln"].append(zeile)
            continue

        events, fehler = sammle_events(regel, ctx)
        if fehler:
            zeile["notiz"] = fehler
            bericht["fehler"] += 1
            logzeilen.append({"zeit": iso(jetzt), "regel": rid, "status": "fehler",
                              "meldung": fehler})
            bericht["regeln"].append(zeile)
            continue
        if not events:
            zeile["notiz"] = "kein Auslöser"
            bericht["regeln"].append(zeile)
            continue

        max_je_lauf = int((regel.get("throttle") or {}).get("max_pro_lauf") or 0)
        gefeuert = 0

        for event in events:
            if budget <= 0:
                zeile["notiz"] = "Lauf-Budget erschöpft"
                break
            if max_je_lauf and gefeuert >= max_je_lauf:
                zeile["notiz"] = f"Lauf-Limit der Regel erreicht ({max_je_lauf})"
                break

            daten = dict(event.get("daten") or {})
            ok, grund = filter_erfuellt(regel, daten)
            if not ok:
                zeile["uebersprungen"] += 1
                if verbose:
                    print(f"   · {rid}: Filter greift – {grund}")
                continue

            key = dedupe_key(regel, event)
            marke = f"{rid}::{key}" if key else ""
            if marke and marke in (state.get("ausgeloest") or {}):
                zeile["uebersprungen"] += 1
                if verbose:
                    print(f"   · {rid}: schon erledigt ({key})")
                continue

            ok, grund = throttle_ok(regel, state, jetzt)
            if not ok:
                zeile["notiz"] = grund
                break

            zeile["treffer"] += 1
            gefeuert += 1
            budget -= 1

            ergebnisse = fuehre_aktionen(regel, event, ctx)
            zeile["aktionen"].extend(ergebnisse)
            bericht["aktionen_gesamt"] += len(ergebnisse)
            bericht["fehler"] += sum(1 for r in ergebnisse if r.get("status") == "fehler")
            bericht["standby"] += sum(1 for r in ergebnisse if r.get("status") == "standby")
            bericht["ausgefuehrt"] += sum(1 for r in ergebnisse if r.get("status") == "ok")

            harter_fehler = any(r.get("status") == "fehler" for r in ergebnisse)
            for r in ergebnisse:
                logzeilen.append({
                    "zeit": iso(jetzt), "regel": rid, "trigger": event.get("trigger"),
                    "key": key, "schritt": r.get("schritt"), "aktion": r.get("typ"),
                    "status": r.get("status"), "meldung": str(r.get("meldung"))[:400],
                    "dry_run": dry_run,
                })

            if not dry_run:
                # Nur erfolgreiche Ketten gelten als erledigt – ein Fehlschlag
                # darf beim nächsten Lauf erneut versucht werden (Self-Healing).
                if marke and not harter_fehler:
                    state.setdefault("ausgeloest", {})[marke] = iso(jetzt)
                zaehler_hoch(state, rid, jetzt)

        bericht["regeln"].append(zeile)

    if not dry_run:
        save_state(state)
        log_append(logzeilen)
    return bericht


# ---------------------------------------------------------------- Ausgabe
def drucke_bericht(bericht: dict) -> None:
    modus = "PROBELAUF (nichts gesendet)" if bericht.get("dry_run") else "SCHARF"
    print(f"\n🔌 Schaltwerk – {modus} · {bericht.get('zeit')}")
    print("─" * 64)
    for z in bericht.get("regeln") or []:
        symbol = "·"
        if z.get("treffer"):
            symbol = "✅" if not any(a.get("status") == "fehler" for a in z.get("aktionen") or []) else "❌"
        notiz = f" – {z['notiz']}" if z.get("notiz") else ""
        print(f" {symbol} {z['id']}: {z['treffer']} Auslöser, "
              f"{z['uebersprungen']} übersprungen{notiz}")
        for a in z.get("aktionen") or []:
            marke = {"ok": "→", "standby": "⏸", "fehler": "✖", "uebersprungen": "·"}.get(
                a.get("status"), "→")
            print(f"      {marke} [{a.get('typ')}] {str(a.get('meldung'))[:110]}")
    print("─" * 64)
    print(f" Aktionen: {bericht.get('aktionen_gesamt')} · ausgeführt "
          f"{bericht.get('ausgefuehrt')} · Standby {bericht.get('standby')} "
          f"· Fehler {bericht.get('fehler')}")


def liste_regeln(regeln: dict) -> None:
    print("\n🔌 Regelwerk (data/automationen.yaml)")
    print("─" * 78)
    for r in regeln.get("regeln") or []:
        zustand = "aktiv  " if r.get("enabled", True) else "AUS    "
        trig = (r.get("trigger") or {}).get("typ") or "?"
        aktionen = ", ".join((a or {}).get("typ", "?") for a in r.get("aktionen") or [])
        print(f" {zustand} {r.get('id'):34s} {trig:20s} → {aktionen}")
    print("─" * 78)
    print(f" {len(regeln.get('regeln') or [])} Regeln insgesamt.\n")


def schreibe_cockpit(regeln: dict, state: dict | None = None,
                     bericht: dict | None = None, pfad: str | None = None) -> str:
    """Menschliche Übersicht im Repo-Root (wie die übrigen Cockpits)."""
    import schaltwerk_actions as act

    pfad = pfad or COCKPIT_PATH
    state = state if state is not None else load_state()
    jetzt = berlin_now()
    protokoll = log_read(limit=40)

    zeilen = [
        "# 🔌 SCHALTWERK – Status",
        "",
        f"> Automatisch erzeugt: {jetzt.strftime('%d.%m.%Y %H:%M')} (Europe/Berlin) ·",
        "> Engine: `scripts/schaltwerk.py` · Regeln: `data/automationen.yaml` ·",
        "> Anleitung: `docs/ANLEITUNG-SCHALTWERK.md`",
        "",
        "Der eigene Zapier-Ersatz: Trigger → Filter → Aktion, betrieben von",
        "GitHub Actions. Keine Zapier-API, keine Fremdkosten, keine Task-Limits.",
        "",
        "## Regeln",
        "",
        "| Regel | Trigger | Aktionen | Zustand | Heute gefeuert | Zuletzt |",
        "|---|---|---|---|---|---|",
    ]
    heute = jetzt.date().isoformat()
    for r in regeln.get("regeln") or []:
        rid = r.get("id") or "?"
        trig = (r.get("trigger") or {}).get("typ") or "?"
        aktionen = ", ".join(f"`{(a or {}).get('typ','?')}`" for a in r.get("aktionen") or [])
        zustand = "✅ aktiv" if r.get("enabled", True) else "⏸ aus"
        heute_n = int(((state.get("zaehler") or {}).get(rid) or {}).get(heute) or 0)
        zuletzt = ((state.get("letzter_lauf") or {}).get(rid) or "")[:16].replace("T", " ")
        zeilen.append(f"| `{rid}` | `{trig}` | {aktionen} | {zustand} | {heute_n} | {zuletzt or '–'} |")

    zeilen += ["", "## Kanäle", "",
               "| Kanal | Zustand | Hinweis |", "|---|---|---|"]
    for kanal in act.kanal_zustand():
        symbol = "✅ sendebereit" if kanal["bereit"] else (
            "⏸ Standby" if kanal["enabled"] else "⏹ deaktiviert")
        zeilen.append(f"| {kanal['label']} | {symbol} | {kanal['grund'] or '–'} |")

    zeilen += ["", "## Letzte Vorgänge", "",
               "| Zeit | Regel | Aktion | Status | Meldung |", "|---|---|---|---|---|"]
    if protokoll:
        for p in reversed(protokoll[-20:]):
            meldung = str(p.get("meldung") or "").replace("|", "¦")[:90]
            zeilen.append(f"| {str(p.get('zeit'))[5:16].replace('T',' ')} | `{p.get('regel')}` | "
                          f"`{p.get('aktion')}` | {p.get('status')} | {meldung} |")
    else:
        zeilen.append("| – | – | – | – | noch kein Lauf protokolliert |")

    if bericht:
        zeilen += ["", "## Letzter Lauf", "",
                   f"- Zeitpunkt: {bericht.get('zeit')}",
                   f"- Modus: {'Probelauf' if bericht.get('dry_run') else 'scharf'}",
                   f"- Aktionen: {bericht.get('aktionen_gesamt')} "
                   f"(ausgeführt {bericht.get('ausgefuehrt')}, "
                   f"Standby {bericht.get('standby')}, Fehler {bericht.get('fehler')})"]

    zeilen += ["", "---", "",
               "**Kanal scharf schalten:** Secret hinterlegen "
               "(Settings → Secrets and variables → Actions). Beim nächsten Lauf",
               "erkennt das Schaltwerk den Kanal von selbst – fehlt ein Token, bleibt",
               "der Kanal im Standby, ohne Fehlalarm. Runbuch: `docs/ANLEITUNG-SCHALTWERK.md`.",
               ""]
    text = "\n".join(zeilen)
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


# -------------------------------------------------------------- Selbsttest
def selftest() -> int:
    """Offline, fail-closed: Engine-Logik, Regelwerk-Vertrag, Operatoren."""
    import schaltwerk_actions as act
    import schaltwerk_triggers as trg

    fehler: list[str] = []

    def pruefe(bedingung: bool, meldung: str) -> None:
        if not bedingung:
            fehler.append(meldung)

    # ST1 – Punktpfade und Templates
    daten = {"artikel": {"slug": "abc", "title": "Strom sparen"}, "n": 7}
    pruefe(get_path(daten, "artikel.slug") == "abc", "ST1: Punktpfad defekt")
    pruefe(get_path(daten, "artikel.fehlt") is None, "ST1: fehlender Pfad liefert nicht None")
    pruefe(render("Neu: {artikel.title}", daten) == "Neu: Strom sparen",
           "ST1: Template-Ersetzung defekt")
    pruefe(render("{{ artikel.slug }}", daten) == "abc", "ST1: geschweifte Doppelklammer defekt")
    pruefe(render("{nicht.da}", daten) == "", "ST1: unbekannter Platzhalter bleibt stehen")

    # ST2 – Operatoren
    faelle = [
        ({"feld": "artikel.title", "operator": "enthaelt", "wert": "strom"}, True),
        ({"feld": "artikel.title", "operator": "enthaelt", "wert": "gas"}, False),
        ({"feld": "n", "operator": "groesser", "wert": 3}, True),
        ({"feld": "n", "operator": "kleiner", "wert": 3}, False),
        ({"feld": "artikel.slug", "operator": "nicht_leer"}, True),
        ({"feld": "artikel.fehlt", "operator": "leer"}, True),
        ({"feld": "artikel.title", "operator": "regex", "wert": r"^Strom"}, True),
        ({"feld": "artikel.title", "operator": "in_liste", "wert": ["Strom sparen", "x"]}, True),
    ]
    for bedingung, erwartet in faelle:
        ok, _ = pruefe_filter(bedingung, daten)
        pruefe(ok is erwartet, f"ST2: Operator {bedingung.get('operator')} liefert {ok}")
    ok, grund = pruefe_filter({"feld": "n", "operator": "quatsch"}, daten)
    pruefe(ok is False and "unbekannter Operator" in grund,
           "ST2: unbekannter Operator muss fail-closed sein")

    # ST3 – Dedupe & Throttle
    state = {"ausgeloest": {}, "zaehler": {"r": {berlin_now().date().isoformat(): 3}},
             "letzter_lauf": {}, "slots": {}, "marker": {}}
    ok, _ = throttle_ok({"id": "r", "throttle": {"max_pro_tag": 3}}, state, berlin_now())
    pruefe(ok is False, "ST3: Tageslimit greift nicht")
    ok, _ = throttle_ok({"id": "r", "throttle": {"max_pro_tag": 5}}, state, berlin_now())
    pruefe(ok is True, "ST3: Tageslimit sperrt zu früh")
    state["letzter_lauf"]["r"] = iso(berlin_now())
    ok, _ = throttle_ok({"id": "r", "throttle": {"cooldown_minuten": 60}}, state, berlin_now())
    pruefe(ok is False, "ST3: Sperrfrist greift nicht")
    key = dedupe_key({"dedupe_key": "{artikel.slug}"}, {"daten": daten})
    pruefe(key == "abc", "ST3: dedupe_key-Vorlage defekt")

    # ST4 – Regelwerk-Vertrag (jede Regel muss ausführbar sein)
    regeln = load_regeln()
    pruefe(bool(regeln.get("regeln")), "ST4: data/automationen.yaml enthält keine Regeln")
    ids = set()
    for r in regeln.get("regeln") or []:
        rid = r.get("id")
        pruefe(bool(rid), "ST4: Regel ohne id")
        pruefe(rid not in ids, f"ST4: doppelte Regel-id {rid}")
        ids.add(rid)
        typ = (r.get("trigger") or {}).get("typ")
        pruefe(typ in trg.PROVIDER, f"ST4: Regel {rid} nutzt unbekannten Trigger {typ!r}")
        pruefe(bool(r.get("aktionen")), f"ST4: Regel {rid} hat keine Aktion")
        for a in r.get("aktionen") or []:
            pruefe((a or {}).get("typ") in act.AKTION,
                   f"ST4: Regel {rid} nutzt unbekannte Aktion {(a or {}).get('typ')!r}")
        for f in r.get("filter") or []:
            pruefe(bool((f or {}).get("feld")), f"ST4: Regel {rid} hat Filter ohne Feld")

    # ST5 – Kosten-Regel: keine kostenpflichtige Pflicht-API
    verbotene_kanaele = {"x"}
    for r in regeln.get("regeln") or []:
        for a in r.get("aktionen") or []:
            kanal = ((a or {}).get("params") or {}).get("kanal")
            pruefe(str(kanal or "").lower() not in verbotene_kanaele,
                   f"ST5: Regel {r.get('id')} verdrahtet den kostenpflichtigen Kanal {kanal!r} fest")

    # ST6 – Agent Reach bleibt lesend: Recherche-Signale dürfen nicht direkt posten
    for r in regeln.get("regeln") or []:
        if (r.get("trigger") or {}).get("typ") != "recherche_signal":
            continue
        for a in r.get("aktionen") or []:
            pruefe((a or {}).get("typ") not in ("social_post", "social_autopilot_lauf"),
                   f"ST6: Regel {r.get('id')} postet Recherche-Signale ungeprüft "
                   "(Agent Reach ist lesend – Kuratierung ist Pflicht)")

    # ST7 – Trockenlauf der kompletten Engine schreibt nichts
    vorher = load_state()
    probe = run(regeln, dry_run=True, state=json.loads(json.dumps(vorher)), verbose=False)
    pruefe(isinstance(probe, dict) and "regeln" in probe, "ST7: Probelauf liefert keinen Bericht")
    pruefe(load_state() == vorher, "ST7: Probelauf hat den State verändert")

    # ST8 – Fehlerhafte Aktion killt den Lauf nicht
    kaputt = {"id": "kaputt", "aktionen": [{"typ": "gibtsnicht"}, {"typ": "protokoll",
                                                                  "params": {"text": "x"}}]}
    res = fuehre_aktionen(kaputt, {"daten": {}}, {"jetzt": berlin_now(), "dry_run": True})
    pruefe(res and res[0].get("status") == "fehler", "ST8: unbekannte Aktion meldet keinen Fehler")

    if fehler:
        print("❌ Schaltwerk-Selbsttest fehlgeschlagen:")
        for f in fehler:
            print(f"   · {f}")
        return 1
    print(f"✅ Schaltwerk-Selbsttest bestanden "
          f"({len(ids)} Regeln, {len(trg.PROVIDER)} Trigger, {len(act.AKTION)} Aktionen).")
    return 0


# ---------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Schaltwerk – Zapier-Nachbau für FranksFinanzcheck "
                    "(Trigger → Filter → Aktion, ohne Fremdkosten).")
    p.add_argument("--run", action="store_true", help="Regeln scharf ausführen")
    p.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts senden")
    p.add_argument("--regel", default="", help="nur diese Regel-id ausführen")
    p.add_argument("--event", default="", help="externes Ereignis als JSON (Webhook)")
    p.add_argument("--list", action="store_true", help="Regelwerk auflisten")
    p.add_argument("--status", action="store_true", help="nur das Cockpit neu schreiben")
    p.add_argument("--selftest", action="store_true", help="Offline-Selbsttest (fail-closed)")
    p.add_argument("--verbose", action="store_true", help="ausführliche Begründungen")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()

    regeln = load_regeln()

    if args.list:
        liste_regeln(regeln)
        return 0

    if args.status and not (args.run or args.dry_run):
        schreibe_cockpit(regeln)
        print(f"📋 Cockpit aktualisiert: {os.path.relpath(COCKPIT_PATH, BLOG_DIR)}")
        return 0

    if not (args.run or args.dry_run):
        p.print_help()
        return 0

    bericht = run(regeln, dry_run=args.dry_run, nur_regel=args.regel,
                  event_json=args.event, verbose=args.verbose)
    drucke_bericht(bericht)
    if not args.dry_run:
        schreibe_cockpit(regeln, bericht=bericht)
        print(f"📋 Cockpit aktualisiert: {os.path.relpath(COCKPIT_PATH, BLOG_DIR)}")

    # Exit-Vertrag: 0 = alles gut (Standby zählt NICHT als Fehler),
    #               2 = mindestens eine Aktion ist hart gescheitert.
    return 2 if bericht.get("fehler") else 0


if __name__ == "__main__":
    sys.exit(main())
