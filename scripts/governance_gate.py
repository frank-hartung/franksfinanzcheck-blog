#!/usr/bin/env python3
"""
GOVERNANCE-GATE – eine Wahrheit, wann die Governance wirklich melden darf.

WARUM (Governance-Report #206, 07.09.2026):
Der Premium-Governance-Lauf hat jede Woche ein Issue geöffnet – auch wenn gar
nichts kaputt war. Ursache: Das Issue wurde an **Exit-Codes** der Schritte
festgemacht. Ein Schritt, der nur „noch keine Daten“ meldet (Umami-Export
fehlt, Awin-CSV fehlt, Pinterest-Analytics leer), lief mit Exit 1 und war damit
für die Pipeline ein Fehler. Ergebnis: Alarm-Müdigkeit – und die echten roten
Befunde gehen im Rauschen unter. Genau das ist für einen Betrieb mit 30+
Automatisierungen der gefährliche Fehler, nicht der Einzelfall.

DIESES SKRIPT TRENT DREI DINGE SAUBER:
  1. **Messung**  – jeder Wächter-Step meldet seinen Befund hier (`--emit`).
  2. **Bewertung** – der Gate entscheidet über eine dokumentierte Policy, ob
                    daraus Handlungsbedarf wird (`--decide`), und schreibt eine
                    kompakte, reproduzierbare Issue-Body statt Roh-Logs.
  3. **Nachvollziehbarkeit** – `data/governance_status.json` (Ist-Zustand) +
                    `data/governance_history.jsonl` (Verlauf pro Lauf) +
                    GitHub-Job-Summary. Ein Lauf ist damit rekonstruierbar.

SCHWERE-GRADE (Policy, bewusst eng):
  red     → Issue (Duplikat-freundlich: offenes Issue wird aktualisiert)
  amber   → Issue, wenn der Befund in ACTIONABLE_AMBER liegt (Kanal/API/Build)
  info    → NIE Issue (Datenlage offen, Hinweis, übersprungener Schritt)
  green   → offenes Governance-Issue wird geschlossen

Exit-Codes:
  0 = Entscheidung getroffen (auch „kein Issue")
  1 = mit --fail-on red und es liegt ROT vor (Workflow soll sichtbar rot werden)
  2 = Selftest/Fehler

Nutzung:
  python3 scripts/governance_gate.py --reset            # Ledger für neuen Lauf leeren
  python3 scripts/governance_gate.py --emit cwv --report CWV-REPORT.md --exit 0
  python3 scripts/governance_gate.py --decide --fail-on red
  python3 scripts/governance_gate.py --summary
  python3 scripts/governance_gate.py --rehearse          # Trockenlauf über den Bestand
  python3 scripts/governance_gate.py --selftest
"""
import datetime
import hashlib
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BLOG_DIR, "data", "governance_status.json")
# Ein Ledger-Eintrag gilt nur für den Lauf, der ihn geschrieben hat (wöchentlich +
# Puffer). Ältere Einträge werden bei der Entscheidung ignoriert – sonst jagt ein
# einzeln ausgelassener Schritt die Automation für immer denselben Alarm.
MAX_STEP_AGE_HOURS = 26
HISTORY = os.path.join(BLOG_DIR, "data", "governance_history.jsonl")
ISSUE_TITLE = "🗞️ Governance-Report: Redaktionelle & technische Handlungsfelder"
ISSUE_LABEL = "governance"
DEFAULT_BODY = "/tmp/governance_issue_body.md"

NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.date()

# Schritte in Anzeigereihenfolge + Report, aus dem der Befund zu lesen ist.
STEPS = {
    "build":   {"report": "",                    "label": "Hugo-Build (Grundlage CWV)"},
    "decay":   {"report": "DECAY-REPORT.md",      "label": "Content-Decay-Radar"},
    "cwv":     {"report": "CWV-REPORT.md",        "label": "Core-Web-Vitals"},
    "secrets": {"report": "SECRETS-REPORT.md",    "label": "Secrets-/Token-Wache"},
    "pinperf": {"report": "PINTEREST-PERF-REPORT.md", "label": "Pinterest-Performance"},
    "umami":   {"report": "data/umami_clicks.meta.json", "label": "Umami-Datenimport"},
    "clicks":  {"report": "CLICK-REPORT.md",      "label": "Affiliate-Klick-Attribution"},
    "awin":    {"report": "AWIN-REPORT.md",       "label": "Awin-Provisionen"},
    # Lesbarkeits-Wache: Befundtabelle aus readability_check --gate-bestand
    # --report LESBARKEIT-REPORT.md (read_avg = Ø < 62, read_floor = Artikel
    # < 55). Exit-Code allein wäre „exit_only“ (Info) – deshalb der Report.
    "lesbarkeit": {"report": "LESBARKEIT-REPORT.md", "label": "Lesbarkeits-Wache (Bestand)"},
    "scorecard": {"report": "EDITORIAL-SCORECARD.md", "label": "Chefredakteur-Scorecard"},
}

# Amber-Befunde, die einen Menschen etwas angehen (Kanal/API/Build/CSS-JS-Hygiene).
ACTIONABLE_AMBER = {
    "aging", "untracked", "state_corrupt",                       # secrets
    "render_block_css", "render_block_js", "inline_js", "cls_img", "build_missing",
    "build_thin",                                                # cwv
    "stale_content", "unmatched_subid", "unattributed",          # decay / awin / clicks
    "scorecard_red",                                             # Chefredakteur-Sicht
}
# Amber-Befunde, die NUR Info sind (Bild-Feinschliff, Stil, Datenlage).
INFO_AMBER = {
    "img_soft", "no_data", "not_configured", "not_used", "untracked_optional",
    "probe_skipped", "foreign_proof", "style_advisory",
    # `unreachable` = die Live-Probe war nicht möglich (Netzwerk, 5xx, Rate-Limit).
    # Kein Handlungsfeld für den Blog – und genau hier wäre sonst die neue
    # Wochentäuschung entstanden: die Probe selbst ist die Maßnahme, ihr Ausfall
    # heilt von allein. Eskalation läuft über die Alters-Regel: bleibt der
    # Nachweis aus, wird der Befund beim Überschreiten der Frist ROT (`stale`).
    "unreachable",
}
# Step-spezifische Marker: Berichte ohne eigene Ampel/Befundtabelle (die beiden
# Monetarisierungs-Importe) werden über diese Zeilen auswertbar – sonst wäre ein
# echter Fund (verlorene Provisionen) „nur“ ein Exit-Code und damit Lärm.
STEP_MARKERS = {
    "awin": [(r"Es wurden (\d+) SubIDs? von keinem Artikel erkannt", "unmatched_subid", "amber")],
    "clicks": [(r"ohne Zuordnung: (\d+)", "unattributed", "amber")],
}

# Report-Zeilen, die „Datenlage offen“ bedeuten – kein Fehler, nie ein Issue.
DATA_GAP_PATTERNS = (
    "kein umami_api_token", "keine websiteid", "umami-klicks nicht geladen",
    "noch keine daten", "keine klick-daten", "keine awin-daten", "keine transaktionen",
    "einträge analysiert: **0**", "noch keine pin-", "kein Datensatz",
)


def _read(path):
    try:
        with open(path if os.path.isabs(path) else os.path.join(BLOG_DIR, path),
                  encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _resolve(path):
    return path if os.path.isabs(path) else os.path.join(BLOG_DIR, path)


def _verdict_from_report(text):
    """Ampel aus einem Report-Text (verschiedene Formate der Wächter)."""
    m = re.search(r"(?:Gesamt-Ampel|Gesamt-Score|Ampel)[^\n]*?\*\*(GREEN|AMBER|RED)\*\*", text)
    if m:
        return m.group(1)
    m = re.search(r"(?:Gesamt-Ampel|Ampel)[:\s]*(GREEN|AMBER|RED)", text)
    if m:
        return m.group(1)
    return None


def _findings_from_report(text):
    """Zeilen `| LEVEL | code | Meldung |` → [(level, code, msg)]."""
    out = []
    for m in re.finditer(r"^\|\s*(RED|AMBER)\s*\|\s*([A-Za-z0-9_\-]+)\s*\|([^|]*)\|", text, re.M):
        out.append((m.group(1).lower(), m.group(2), m.group(3).strip()))
    # Decay-Radar nutzt Zählerzeilen statt einer Befundtabelle.
    for label, level in (("STALE", "red"), ("DECAYING", "amber")):
        m = re.search(rf"[-•]\s*(?:🔴|🟠)?\s*\*\*{label}\*\*[^\n]*?:\s*\*\*(\d+)\*\*", text)
        if m and int(m.group(1)) > 0:
            out.append((level, "stale_content" if level == "red" else "aging",
                        f"{label}: {m.group(1)} Artikel"))
    return out


def _data_gap(text):
    low = text.lower()
    return any(p in low for p in DATA_GAP_PATTERNS)


def _marker_findings(step, report_text):
    out = []
    for pattern, code, level in STEP_MARKERS.get(step, ()):
        m = re.search(pattern, report_text or "")
        if m and int(m.group(1)) > 0:
            out.append((level, code, f"{code}: {m.group(1)} Fundstelle(n) im Report"))
    return out


def classify(step, report_text="", log_text="", exit_code=0, producer="", require_green=False):
    """Ein Wächter-Lauf → dict(level, code, findings, message, actionable).

    Level: green | info | amber | red
    `require_green`: Schritt hat keinen Report-Befund, aber jeder nicht-Null-Exit
    ist ein echtes Problem (z. B. der Hugo-Build – der liefert keine Befundtabelle).
    """
    exit_code = int(exit_code or 0)
    report_text = report_text or ""
    log_text = log_text or ""
    crashed = exit_code >= 2 or "Traceback (most recent call last)" in log_text
    if crashed:
        tail = ""
        for line in reversed([l for l in log_text.splitlines() if l.strip()]):
            if re.search(r"[A-Za-zÄÖÜäöüß]", line) and not line.startswith("  "):
                tail = line.strip()[:200]
                break
        return {"level": "red", "code": "run_crashed", "findings": 1,
                "actionable": True, "producer": producer,
                "message": f"Schritt lief nicht sauber durch (Exit {exit_code}): "
                           f"{tail or 'kein Log – Logdatei prüfen'}"}

    if require_green and exit_code == 0 and not report_text:
        return {"level": "green", "code": "ok", "findings": 0, "actionable": False,
                "producer": producer, "message": "Schritt erfolgreich (Report folgt nicht)"}
    if require_green and exit_code != 0:
        tail = next((l.strip()[:180] for l in reversed(log_text.splitlines()) if l.strip()), "")
        return {"level": "red", "code": "step_failed", "findings": 1, "actionable": True,
                "producer": producer,
                "message": f"Schritt `{step}` nicht erfolgreich (Exit {exit_code})"
                           + (f": {tail}" if tail else "")}

    findings = _findings_from_report(report_text) + _marker_findings(step, report_text)
    verdict = _verdict_from_report(report_text)
    # Erzeuger-Version zählt: ein Report der v1-Wache (Secrets ohne `Nachweis`-
    # Spalte) konnte gar nicht live prüfen – seine „untracked"-Meldung ist dann
    # ein Format-Artefakt, kein Alarm. Verbraucher dürfen keine stricter sein als
    # ihr Erzeuger (sonst hängt das Issue an einem Bericht, den niemand mehr
    # erzeugen kann).
    v1_tabelle = bool(re.search(r"^\|\s*Secret\s*\|\s*Status\s*\|\s*$", report_text or "", re.M))
    if step == "secrets" and v1_tabelle and "Nachweis" not in report_text:
        findings = [(lvl if lvl == "red" else "info", code, msg) for lvl, code, msg in findings]
    # Die Scorecard ist eine ANSICHT, kein Messinstrument: ihre eigene Ampel darf
    # kein zweites Issue auslösen (sonst meldet dieselbe Lage twice). Ausnahme:
    # ein roter Gesamt-Score – dann hat kein Einzelschritt alone alarmiert und
    # der Bündelungs-Hinweis ist der einzige Wecker.
    if step == "scorecard" and verdict == "RED":
        findings.append(("amber", "scorecard_red",
                          "Chefredakteur-Scorecard rot (< 70) – siehe Report"))
    hard = [(lvl, code, msg) for lvl, code, msg in findings
            if (lvl == "red") or (lvl == "amber" and (code in ACTIONABLE_AMBER
                                                       or (code not in INFO_AMBER and verdict == "AMBER")))]
    soft = [(lvl, code, msg) for lvl, code, msg in findings if (lvl, code, msg) not in hard]

    if any(lvl == "red" for lvl, _, _ in hard):
        return {"level": "red", "code": "red_finding", "findings": len(hard),
                "actionable": True, "producer": producer,
                "message": "; ".join(msg for _, _, msg in hard[:4]) or "roter Befund"}
    if hard:
        return {"level": "amber", "code": hard[0][1], "findings": len(hard),
                "actionable": True, "producer": producer,
                "message": "; ".join(msg for _, _, msg in hard[:4]) or "gelber Befund"}
    if verdict == "AMBER":
        # Ampel gelb, aber kein Befund mit Actionable-Code → Hinweis (z. B. nur
        # Bild-Feinschliff). Das ist KEIN Grund für ein Issue.
        return {"level": "info", "code": "advisory_only", "findings": len(soft),
                "actionable": False, "producer": producer,
                "message": "Hinweis ohne Handlungsstufen-Effekt (nur Report)"}
    if exit_code == 1 and not findings:
        # Exit 1 ohne Befundtabelle: die Wache meldet, kann es aber nicht sagen.
        # Als Info werten – sonst lebt die Exit-Code-Kopplung als Alarm-Quelle auf.
        return {"level": "info", "code": "exit_only", "findings": 0, "actionable": False,
                "producer": producer,
                "message": "Wächter meldet Exit 1 ohne Befund – Policy: prüfen und "
                           "Befundtabelle nachziehen"}
    if verdict is None and _data_gap(report_text or log_text):
        return {"level": "info", "code": "no_data", "findings": 0, "actionable": False,
                "producer": producer, "message": "Datenlage offen (noch kein Export/Import)"}
    if verdict is None and not report_text:
        return {"level": "info", "code": "no_report", "findings": 0, "actionable": False,
                "producer": producer, "message": "kein Report erzeugt (Schritt übersprungen?)"}
    return {"level": "green", "code": "ok", "findings": len(soft), "actionable": False,
            "producer": producer, "message": "in Ordnung" + (
                f" ({len(soft)} Hinweis(e))" if soft else "")}


def rehearse():
    """Trockenlauf über die Reports im Bestand – ohne einen einzigen Schreibvorgang.

    Beantwortet die Frage, die im Betrieb immer zuerst kommt: „Was würde der
    Governance-Lauf heute entscheiden?" (und damit: warum meldet er, oder eben
    nicht). Wichtig nach #206: der Lauf darf aus Hinweis-Stufen kein Issue bauen.
    """
    print("🧪 Governance-Rehearsal (liest die Reports, schreibt nichts)")
    steps = {}
    for step, meta in STEPS.items():
        rep = _read(meta["report"]) if meta.get("report") else ""
        info = classify(step, rep, "", 0, meta["report"] or "-")
        steps[step] = {"level": info["level"], "code": info["code"], "findings": info["findings"],
                       "actionable": bool(info["actionable"]), "message": info["message"],
                       "report": meta.get("report") or "", "ts": NOW.isoformat(timespec="seconds")}
        icon = {"red": "🔴", "amber": "🟠", "info": "ℹ️", "green": "🟢"}[info["level"]]
        print(f"  {icon} {meta['label']:<34} {info['level']:<5} {info['message'][:78]}")
    # Dieselbe Policy-Funktion wie im echten Lauf – Rehearsal und Run dürfen
    # nie auseinanderlaufen (sonst beweist der Trockenlauf nichts).
    verdict, action, counts = decide_policy(steps)
    print(f"\n  Entscheidung: Ampel {verdict} → Issue-Aktion '{action}' "
          f"(Fingerabdruck {fingerprint(steps)}, rot={counts['red']} "
          f"gelb={counts['amber']} hinweise={counts['info']} grün={counts['green']})")
    folge = "Issue schließen" if action == "close" else (
        "Issue öffnen/aktualisieren" if action == "report" else "Ruhe – nichts gemeldet")
    print(f"  Konsequenz für GitHub: {folge}.")
    return 0 if action != "report" else 1


# ------------------------------------------------------------------ State

def _load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("steps"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 1, "generated": "", "steps": {}, "verdict": "UNKNOWN",
            "issue_action": "none", "fingerprint": ""}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = f"{STATE}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE)


def _append_history(row):
    try:
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        with open(HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        # Retention: die letzten 260 Läufe reichen für ein Quartal Governance.
        lines = open(HISTORY, encoding="utf-8").read().splitlines()
        if len(lines) > 260:
            with open(HISTORY, "w", encoding="utf-8") as f:
                f.write("\n".join(lines[-260:]) + "\n")
    except OSError:
        pass


def fingerprint(steps):
    """Stabiler Fingerabdruck der handlungsbedürftigen Befunde (Dedupe-Hilfe)."""
    key = sorted((name, info.get("code"), int(info.get("findings") or 0))
                 for name, info in steps.items() if info.get("actionable"))
    return hashlib.sha256(json.dumps(key).encode()).hexdigest()[:12]


# ------------------------------------------------------------------ emit / decide

def emit(step, report=None, log=None, exit_code=0, producer="", require_green=False):
    if step not in STEPS:
        print(f"⚠️  Governance-Gate: unbekannter Schritt '{step}' – wird als Hinweis geführt.")
    meta = STEPS.get(step, {})
    rep_path = report or meta.get("report") or ""
    report_text = _read(rep_path) if rep_path else ""
    log_text = _read(log) if log else ""
    info = classify(step, report_text, log_text, exit_code, producer or rep_path,
                    require_green=require_green)
    state = _load_state()
    state["steps"][step] = {
        "level": info["level"], "code": info["code"], "findings": info["findings"],
        "actionable": bool(info["actionable"]), "message": info["message"][:300],
        "report": rep_path, "exit": int(exit_code or 0), "ts": NOW.isoformat(timespec="seconds"),
    }
    state["generated"] = NOW.isoformat(timespec="seconds")
    _save_state(state)
    icon = {"red": "🔴", "amber": "🟠", "info": "ℹ️", "green": "🟢"}[info["level"]]
    print(f"{icon} {meta.get('label', step)}: {info['level']} – {info['message']}")
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        from audit_log import log_event
        log_event(module="governance_gate", action=f"emit:{step}",
                  input={"exit": int(exit_code or 0), "report": rep_path},
                  output={"level": info["level"], "code": info["code"]},
                  status="ok" if info["level"] != "red" else "error",
                  critical=info["level"] == "red")
    except Exception:  # noqa: BLE001  – Audit darf nie blockieren
        pass
    return 0


def reset():
    """Ledger für einen frischen Lauf leeren (Workflow ruft das als ersten Schritt).

    Ohne Reset könnte ein Schritt, der in einem Lauf gar nicht läuft (Job
    abgebrochen, Schritt umbenannt, manuell ausgelassen), als Altlast immer
    wieder dasselbe Issue auslösen – der genaue Gegenfall zum behobenen
    Dauer-Alarm aus #206.
    """
    _save_state({"version": 1, "generated": NOW.isoformat(timespec="seconds"),
                 "steps": {}, "verdict": "UNKNOWN", "issue_action": "none",
                 "fingerprint": ""})
    print("🧹 Governance-Gate: Ledger geleert (data/governance_status.json).")
    return 0


def _fresh(steps, max_age_hours=MAX_STEP_AGE_HOURS, now=None):
    """Nur Schritte des laufenden Laufs werten; alte Einträge als Hinweis führen."""
    now = now or NOW
    keep, dropped = {}, []
    for name, info in steps.items():
        ts = str(info.get("ts") or "")
        try:
            age = (now - datetime.datetime.fromisoformat(ts)).total_seconds() / 3600.0
        except ValueError:
            age = 1e9
        if age <= max_age_hours:
            keep[name] = info
        else:
            dropped.append(name)
    if dropped:
        keep = dict(keep)
        keep["_stale_steps"] = {"level": "info", "actionable": False, "code": "stale_step",
                                "findings": 0,
                                "message": "Einträge aus einem früheren Lauf ignoriert: "
                                           + ", ".join(sorted(dropped))}
    return keep


def decide_policy(steps):
    """Reine Entscheidungsfunktion (testbar): Ampel + Issue-Aktion aus dem Ledger.

    Policy (bewusst so eng wie möglich, so weit wie nötig):
      report – es gibt einen handlungsbedürftigen Befund (rot oder gelb)
      close  – nichts Handlungsbedürftiges mehr (auch wenn Hinweis-Stufen bleiben:
               „Datenlage offen" ist kein Grund, ein Issue offen zu halten)
      none   – leeres/halbes Ledger (Lauf abgebrochen, Schritte nie.emit) →
               niemals schließen, weil die Messung fehlt, nicht weil es grün ist
    """
    actionable = {k: v for k, v in steps.items() if v.get("actionable")}
    reds = {k: v for k, v in actionable.items() if v.get("level") == "red"}
    ambers = {k: v for k, v in actionable.items() if v.get("level") == "amber"}
    infos = {k: v for k, v in steps.items() if v.get("level") == "info"}
    if reds:
        verdict = "RED"
    elif ambers:
        verdict = "AMBER"
    elif infos:
        verdict = "INFO"
    else:
        verdict = "GREEN"
    if not steps:
        action = "none"
    elif reds or ambers:
        action = "report"
    else:
        action = "close"
    return verdict, action, {"red": len(reds), "amber": len(ambers), "info": len(infos),
                             "green": sum(1 for v in steps.values() if v.get("level") == "green")}


def decide(fail_on=None, max_age_hours=MAX_STEP_AGE_HOURS):
    state = _load_state()
    steps = _fresh(state.get("steps") or {}, max_age_hours=max_age_hours)
    state["steps"] = steps
    actionable = {k: v for k, v in steps.items() if v.get("actionable")}
    reds = {k: v for k, v in actionable.items() if v.get("level") == "red"}
    ambers = {k: v for k, v in actionable.items() if v.get("level") == "amber"}
    infos = {k: v for k, v in steps.items() if v.get("level") == "info"}
    verdict, action, counts = decide_policy(steps)
    fp = fingerprint(steps)
    prev = {}
    if os.path.exists(STATE):
        try:
            prev = json.load(open(STATE, encoding="utf-8")).get("last") or {}
        except (OSError, json.JSONDecodeError):
            prev = {}
    state["verdict"] = verdict
    state["issue_action"] = action
    state["fingerprint"] = fp
    state["counts"] = counts
    state["last"] = {"verdict": verdict, "action": action, "fingerprint": fp,
                     "changed": prev.get("fingerprint") != fp}
    _save_state(state)
    _append_history({"ts": NOW.isoformat(timespec="seconds"), "verdict": verdict,
                     "action": action, "fingerprint": fp, **state["counts"],
                     "steps": {k: v.get("level") for k, v in steps.items()}})

    out = [f"verdict={verdict}", f"action={action}", f"fingerprint={fp}",
           f"changed={'true' if state['last']['changed'] else 'false'}",
           f"red={len(reds)}", f"amber={len(ambers)}", f"info={len(infos)}"]
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
    print("·".join(out))
    for name, info in sorted(actionable.items(), key=lambda kv: (kv[1].get("level") != "red", kv[0])):
        print(f"  → {name}: {info['message']}")
    for name, info in sorted(infos.items()):
        print(f"  ℹ️ {name}: {info['message']}")
    if fail_on == "red" and reds:
        print("::error::Governance ROT – " + "; ".join(f"{k}: {v['message']}" for k, v in reds.items()))
        return 1
    return 0


def render_body():
    """Kompakte Issue-Body: nur Befunde mit Handlung, plus Datenlage-Block."""
    return _render_from(_load_state())


def summary():
    state = _load_state()
    steps = state.get("steps") or {}
    order = list(STEPS)
    lines = ["## 🗞️ Governance-Cockpit", "",
             f"**Ampel:** {state.get('verdict', 'UNKNOWN')} · **Issue-Aktion:** "
             f"{state.get('issue_action', '-')} · **Fingerabdruck:** `{state.get('fingerprint', '-')}`",
             "", "| Schritt | Level | Befund |", "|---|---|---|"]
    icon = {"red": "🔴", "amber": "🟠", "info": "ℹ️", "green": "🟢"}
    for name in order:
        if name in steps:
            info = steps[name]
            lines.append(f"| {STEPS[name]['label']} | {icon.get(info.get('level'), '⚪')} "
                         f"{info.get('level')} | {info.get('message')} |")
    body = "\n".join(lines) + "\n"
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(body + "\n")
        except OSError:
            pass
    print(body)
    return 0


# ------------------------------------------------------------------ Selftest

def _selftest():
    failures = []
    # 1) Der #206-Fall: Info-Stufen allein dürfen KEIN Issue auslösen.
    cases = [
        ("secrets", "| Secret | Status | Nachweis |\n|---|---|---|\n## Gesamt-Ampel: **GREEN**\n"
                    "\n## Befunde\n\n_Alle Secret-Kanäle bestätigt einsatzfähig._\n", "", 0, "green"),
        ("cwv", "## 🤖 Gesamt-Ampel: **GREEN**\n\n## Befunde\n\n_Alle Soll-Werte eingehalten._", "", 0, "green"),
        ("cwv", "## 🤖 Gesamt-Ampel: **AMBER**\n\n| AMBER | img_soft | Bild optimierbar |", "", 1, "info"),
        ("cwv", "## 🤖 Gesamt-Ampel: **RED**\n\n| RED | img_over | Bild 900 KB |", "", 1, "red"),
        ("clicks", "_Noch keine Daten – Umami-Export …_", "ℹ️ Keine Klick-Daten gefunden.", 0, "info"),
        ("awin", "_Keine Transaktionen gefunden in data/awin_transactions.csv_", "", 0, "info"),
        ("secrets", "## Gesamt-Ampel: **RED**\n\n| RED | dead | `PINTEREST` – tot |", "", 1, "red"),
        ("secrets", "## Gesamt-Ampel: **AMBER**\n\n| AMBER | aging | `MASTODON` – 30d |", "", 1, "amber"),
        # Transienter Probe-Ausfall darf kein Wochen-Issue werden (sonst hätte die
        # Live-Probe den alten Dauer-Alarm nur durch einen neuen ersetzt).
        ("secrets", "## Gesamt-Ampel: **AMBER**\n\n| AMBER | unreachable | `X` – URLError |", "", 1, "info"),
        ("cwv", "", "Traceback (most recent call last):\n  File x\nValueError: bad", 2, "red"),
        ("decay", "- 🔴 **STALE** (sofort aktualisieren): **3**\n- 🟢 **FRESH** (ok): **27**", "", 1, "red"),
        ("decay", "- 🔴 **STALE** (sofort aktualisieren): **0**\n- 🟢 **FRESH** (ok): **30**", "", 0, "green"),
        ("scorecard", "## Gesamt-Score: **83/100** · Ampel: **AMBER**", "", 0, "info"),
        # Lesbarkeits-Wache: Report liefert Ampel + Befundtabelle, Exit-Code
        # allein darf NICHT alarmieren (exit_only-Policy, vgl. #206).
        ("lesbarkeit", "Gesamt-Ampel: **GREEN**\n\n| Level | Code | Befund |\n|---|---|---|\n", "", 0, "green"),
        ("lesbarkeit", "Gesamt-Ampel: **AMBER**\n\n| AMBER | read_avg | Ø Flesch 58.0 < Ziel 62 |", "", 1, "amber"),
        ("lesbarkeit", "Gesamt-Ampel: **RED**\n\n| RED | read_floor | content/posts/x – Flesch 53.0 < Floor 55 |", "", 1, "red"),
    ]
    for step, rep, log, rc, want in cases:
        got = classify(step, rep, log, rc, "test")
        if got["level"] != want:
            failures.append(f"{step}: erwartet {want}, erhalten {got['level']} ({got['message'][:70]})")
        if want in ("green", "info") and got["actionable"]:
            failures.append(f"{step}: {want} darf nicht handlungsbedürftig sein")
        if want in ("red", "amber") and not got["actionable"]:
            failures.append(f"{step}: {want} muss handlungsbedürftig sein")
    # 2) Body enthält keine Roh-Logs und keinen Hinweis als „zu beheben"
    state = {"version": 1, "generated": "x", "verdict": "AMBER", "fingerprint": "abc",
             "steps": {"clicks": {"level": "info", "actionable": False, "message": "Datenlage offen",
                                  "code": "no_data", "findings": 0},
                       "secrets": {"level": "red", "actionable": True, "code": "dead",
                                   "message": "Pinterest-Token tot", "report": "SECRETS-REPORT.md"}}}
    body = _render_from(state)
    if "Zu beheben" not in body or "Pinterest-Token tot" not in body:
        failures.append("Body enthält den roten Befund nicht")
    if "Datenlage offen" not in body:
        failures.append("Body verliert die Datenlagen-Info")
    if body.count("| Schritt |") != 1:
        failures.append("Body-Struktur inkonsistent")
    # 3) Fingerabdruck stabil, aber empfindlich gegen echte Änderung
    a = fingerprint(state["steps"])
    b = fingerprint(json.loads(json.dumps(state["steps"])))
    c = fingerprint({"secrets": {**state["steps"]["secrets"], "findings": 2}})
    if a != b:
        failures.append("Fingerabdruck nicht deterministisch")
    if a == c:
        failures.append("Fingerabdruck ignoriert Befundanzahl")
    # 4) Exit-Code-Policy: kein Alarm aus Exit 1 ohne Befundtabelle
    if classify("awin", "whatever", "", 1)["actionable"]:
        failures.append("Exit 1 ohne Befunde erzeugt Alarm (alter #206-Zustand)")
    # 5) Frische-Policy: Altlasten aus Vorläufen dürfen nie erneut alarmieren
    old = {"cwv": {"level": "red", "actionable": True, "code": "red_finding", "findings": 1,
                   "message": "alt", "ts": (NOW - datetime.timedelta(days=9)).isoformat(timespec="seconds")}}
    fresh = _fresh(old)
    if any(v.get("actionable") for v in fresh.values()):
        failures.append("alter RED-Eintrag alarmiert erneut (Dauer-Alarm-Klasse)")
    if "_stale_steps" not in fresh:
        failures.append("verworfene Schritte bleiben unsichtbar")
    if _fresh({"cwv": {"level": "red", "actionable": True, "ts": NOW.isoformat(timespec="seconds")}}
              )["cwv"]["level"] != "red":
        failures.append("frischer RED-Eintrag wird fälschlich verworfen")
    # 6) require-green: ein Build ohne Report-Tabelle darf nicht als „Info" verpuffen
    if classify("build", "", "hugo: Fehler beim Rendern", 1, "hugo", require_green=False)["actionable"]:
        failures.append("exit_only-Regel greift nicht (Build ohne --require-green soll still sein)")
    r = classify("build", "", "hugo: Fehler beim Rendern", 1, "hugo", require_green=True)
    if r["level"] != "red" or not r["actionable"]:
        failures.append("--require-green: fehlgeschlagener Build wird nicht rot")
    if classify("build", "", "ok", 0, "hugo", require_green=True)["level"] != "green":
        failures.append("--require-green: grüner Build wird fälschlich gemeldet")
    # 6b) Scorecard: gelb = Ansicht (info), rot = Alarm (amber, actionierbar)
    if classify("scorecard", "## Gesamt-Score: **68/100** · Ampel: **RED**", "", 1)["level"] != "amber":
        failures.append("rote Scorecard löst keinen gebündelten Alarm aus")
    # 6c) Marker: verlorene Awin-Zuordnung muss sichtbar sein
    aw = classify("awin", "_Es wurden 3 SubIDs von keinem Artikel erkannt._", "", 1)
    if aw["level"] != "amber" or not aw["actionable"]:
        failures.append("Awin: verlorene SubIDs bleiben ohne Alarm")
    if classify("awin", "_Es wurden 0 SubIDs von keinem Artikel erkannt._", "", 0)["level"] != "green":
        failures.append("Awin: sauberer Import meldet trotzdem")
    # 6d) v1-Report der Secrets-Wache: kein Alarm aus einem Format ohne Live-Probe
    legacy = ("# 🔐 Secrets-/Token-Alters-Wache\n**Stand:** 2026-09-07\n\n"
              "## Gesamt-Ampel: **AMBER**\n\n| Secret | Status |\n|---|---|\n\n"
              "## Befunde\n\n| AMBER | untracked | `PINTEREST` – kein Erfolgs-Log |\n")
    lg = classify("secrets", legacy, "", 1)
    if lg["actionable"]:
        failures.append("v1-Secrets-Report (ohne Live-Probe-Möglichkeit) alarmiert trotzdem")
    v2 = legacy.replace("| Secret | Status |", "| Secret | Status | Nachweis |")
    if not classify("secrets", v2, "", 1)["actionable"]:
        failures.append("v2-Secrets-Report mit untracked-Befund wird nicht gemeldet")
    # 7) decide_policy: keine Zombie-Issues, kein Schließen ohne Messung
    if decide_policy({}) != ("GREEN", "none", {"red": 0, "amber": 0, "info": 0, "green": 0}):
        failures.append("leeres Ledger darf nichts schließen (Messung fehlt!)")
    v, a, _c = decide_policy({"secrets": {"level": "info", "actionable": False,
                                          "code": "no_data", "findings": 0}})
    if (v, a) != ("INFO", "close"):
        failures.append(f"Hinweis-Lage schließt das Issue nicht (v={v}, a={a}) – "
                        "Zombie-Issue-Klasse aus #206")
    v, a, _c = decide_policy({"cwv": {"level": "amber", "actionable": True, "code": "cls_img"}})
    if (v, a) != ("AMBER", "report"):
        failures.append("gelber Build-Befund meldet nicht")
    v, a, _c = decide_policy({"cwv": {"level": "green", "actionable": False},
                              "decay": {"level": "green", "actionable": False}})
    if (v, a) != ("GREEN", "close"):
        failures.append("grüne Lage schließt nicht")
    # 7b) Verdict-Reihenfolge in decide() wird über Counts korrekt abgeleitet
    if not (STEPS.keys() >= {"cwv", "secrets", "scorecard"}):
        failures.append("Pflicht-Schritte fehlen im Gate")
    if failures:
        print("❌ GOVERNANCE-GATE-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ GOVERNANCE-GATE-SELFTEST bestanden (Issue-Policy, Info-Stufen, "
          "Fingerabdruck, Body-Format).")
    return 0


def _render_from(state):
    """Body-Renderer als reine Funktion (testbar) – render_body() nutzt den Live-State."""
    steps = state.get("steps") or {}
    lines = [
        "## 🗞️ Governance-Befunde", "",
        f"**Stand:** {TODAY.isoformat()} · **Ampel:** {state.get('verdict', 'UNKNOWN')} · "
        f"**Fingerabdruck:** `{state.get('fingerprint', '-')}`", "",
        "Der Premium-Governance-Lauf meldet nur noch **Befunde mit Handlungswert** "
        "(rot/gelb). Hinweis-Stufen wie „Datenlage offen“ stehen unten im Block "
        "*Datenlagen* und erzeugen kein Issue mehr (Policy: `scripts/governance_gate.py`).", "",
    ]
    hard = {k: v for k, v in steps.items() if v.get("actionable")}
    if hard:
        lines += ["### Zu beheben", "", "| Schritt | Ebene | Befund | Report |", "|---|---|---|---|"]
        for name, info in sorted(hard.items(), key=lambda kv: (kv[1].get("level") != "red", kv[0])):
            lvl = "🔴 ROT" if info.get("level") == "red" else "🟠 AMBER"
            lines.append(f"| {STEPS.get(name, {}).get('label', name)} | {lvl} | "
                         f"{info.get('message', '-')} | `{info.get('report') or '-'}` |")
        lines.append("")
    infos = {k: v for k, v in steps.items() if v.get("level") == "info"}
    greens = {k: v for k, v in steps.items() if v.get("level") == "green"}
    if infos or greens:
        lines += ["### Datenlagen & Status", ""]
        for name, info in sorted(infos.items()):
            lines.append(f"- ℹ️ **{STEPS.get(name, {}).get('label', name)}** – {info.get('message')}")
        for name, info in sorted(greens.items()):
            lines.append(f"- 🟢 **{STEPS.get(name, {}).get('label', name)}** – {info.get('message')}")
        lines.append("")
    lines += ["### Runbook (Kurzform)", "",
              "- Scorecard: `python3 scripts/editorial_scorecard.py`",
              "- CWV: `python3 scripts/cwv_guard.py --public public/ --strict-build`",
              "- Secrets live: `python3 scripts/secrets_age_guard.py --verify`",
              "- Klick-Daten füllen: `python3 scripts/umami_clicks.py --fetch`",
              "- Awin: `python3 scripts/awin_provisions.py --gen-subid-map` + CSV nach "
              "`data/awin_transactions.csv`",
              "- Regressionen dieser Klasse: `python3 scripts/governance_contract.py`", "",
              f"---\n*Automatisch vom Premium-Governance-Workflow · Label `{ISSUE_LABEL}` · "
              f"Update statt Duplikat, schließen bei Grün.*"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--summary" in argv:
        return summary()
    if "--rehearse" in argv:
        return rehearse()
    if "--reset" in argv:
        return reset()
    if "--decide" in argv:
        fail_on = None
        if "--fail-on" in argv:
            fail_on = argv[argv.index("--fail-on") + 1]
        rc = decide(fail_on=fail_on)
        body = render_body()
        target = argv[argv.index("--body-file") + 1] if "--body-file" in argv else DEFAULT_BODY
        try:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(body)
            print(f"→ Issue-Body geschrieben: {target}")
        except OSError as exc:
            print(f"⚠️  Issue-Body konnte nicht geschrieben werden: {exc}")
        return rc
    if "--emit" in argv:
        i = argv.index("--emit") + 1
        step = argv[i] if i < len(argv) else "unknown"

        def val(flag, default=""):
            return argv[argv.index(flag) + 1] if flag in argv else default
        return emit(step, report=val("--report") or None, log=val("--log") or None,
                    exit_code=int(val("--exit", "0") or 0), producer=val("--producer"),
                    require_green="--require-green" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
