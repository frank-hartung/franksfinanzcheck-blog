#!/usr/bin/env python3
"""audit_log.py – Zentrales Audit-Log für FrankAutoOps

Jede automatisierte Änderung erzeugt ein Audit-Event mit Zeitstempel,
Modul, Input, Output und Erfolg/Fehler. Logs liegen als JSON-Lines unter
data/audit/ (90 Tage Aufbewahrung; kritische Vorfälle 1 Jahr).

Event-Struktur:
{
  "ts": "2026-08-09T18:00:00Z",       # ISO-Zeitstempel (UTC)
  "module": "fix_spaces",              # Modul/Skript
  "action": "apply",                   # Aktion
  "input": {...},                      # kompakte Eingabe (z. B. Anzahl Dateien)
  "output": {...},                     # kompakte Ausgabe (z. B. Anzahl Fixes)
  "status": "ok" | "error",            # Erfolg/Fehler
  "critical": false,                   # kritischer Vorfall (1 Jahr Retention)
  "commit": "abc1234"                  # optional: zugehöriger Commit
}

Nutzung als Modul:
  from audit_log import log_event
  log_event(module="fix_spaces", action="apply", input={"files": 78},
            output={"fixes": 960}, status="ok")

CLI:
  python3 scripts/audit_log.py --event '{"module":"test",...}'
  python3 scripts/audit_log.py --report            # Statistik
  python3 scripts/audit_log.py --cleanup           # Retention durchsetzen
"""
import datetime
import glob
import json
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(BLOG_DIR, "data", "audit")
RETENTION_DAYS = 90
CRITICAL_RETENTION_DAYS = 365


def _ensure_dir() -> None:
    os.makedirs(AUDIT_DIR, exist_ok=True)


def _today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def log_event(module: str, action: str, input: dict | None = None,
              output: dict | None = None, status: str = "ok",
              critical: bool = False, commit: str | None = None) -> str:
    """Schreibt ein Audit-Event. Liefert den Pfad der Log-Datei."""
    _ensure_dir()
    event = {
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "module": module,
        "action": action,
        "input": input or {},
        "output": output or {},
        "status": status,
        "critical": critical,
        "commit": commit,
    }
    path = os.path.join(AUDIT_DIR, f"{_today()}.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def load_events() -> list[dict]:
    """Lädt alle Audit-Events (sortiert nach Zeitstempel)."""
    events = []
    for f in sorted(glob.glob(os.path.join(AUDIT_DIR, "*.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events


def report() -> dict:
    """Erzeugt eine kompakte Statistik über die Audit-Events."""
    events = load_events()
    stats = {"total": len(events), "ok": 0, "error": 0, "critical": 0, "by_module": {}}
    for e in events:
        if e.get("status") == "error":
            stats["error"] += 1
        else:
            stats["ok"] += 1
        if e.get("critical"):
            stats["critical"] += 1
        m = e.get("module", "?")
        stats["by_module"].setdefault(m, 0)
        stats["by_module"][m] += 1
    return stats


def cleanup() -> dict:
    """Durchsetzt die Retention: normale Events 90 Tage, kritische 365 Tage."""
    _ensure_dir()
    now = datetime.datetime.now(datetime.timezone.utc)
    removed = 0
    kept = 0
    for f in glob.glob(os.path.join(AUDIT_DIR, "*.jsonl")):
        # Dateiname = Datum (YYYY-MM-DD.jsonl) – alt genug zum Löschen?
        day = os.path.basename(f).replace(".jsonl", "")
        try:
            fdate = datetime.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        age = (now - fdate).days
        if age > CRITICAL_RETENTION_DAYS:
            os.remove(f)
            removed += 1
            continue
        if age > RETENTION_DAYS:
            # Nur löschen, wenn keine kritischen Events in der Datei
            critical_in_file = False
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        if json.loads(line).get("critical"):
                            critical_in_file = True
                            break
                    except json.JSONDecodeError:
                        pass
            if not critical_in_file:
                os.remove(f)
                removed += 1
            else:
                kept += 1
        else:
            kept += 1
    return {"removed": removed, "kept": kept}


def main() -> int:
    if "--event" in sys.argv:
        i = sys.argv.index("--event")
        payload = json.loads(sys.argv[i + 1])
        path = log_event(**payload)
        print(f"Event geschrieben: {path}")
        return 0
    if "--report" in sys.argv:
        print(json.dumps(report(), ensure_ascii=False, indent=2))
        return 0
    if "--cleanup" in sys.argv:
        print(json.dumps(cleanup(), ensure_ascii=False))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
