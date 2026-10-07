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

Das Ledger ist ein BEWEISMITTEL, kein Logfile
--------------------------------------------
`data/audit/*.jsonl` ist versioniert und wird von `history_guard.py` als
append-only bewacht (Regel H6). Eine Zeile darin behauptet: „Das ist im
Betrieb wirklich passiert." Deshalb darf ein TESTLAUF niemals eine echte
Zeile schreiben – er fabriziert sonst Beweise (Nebenbefund zu #610,
07.10.2026; Governance-Regel C27 „Beweisen ist nicht Fabrizieren").

Zwei Umgebungsvariablen schalten das Ledger für einen Prozess um:

  FFC_AUDIT_DIR      Zielverzeichnis umlenken (z. B. ein Temp-Verzeichnis).
                     Die Zeilen entstehen dann vollständig und sind lesbar,
                     landen aber nicht im Beweis-Ledger des Repos.
  FFC_AUDIT_DISABLE  Harter No-Op: `log_event()` schreibt nichts und
                     liefert None.

Beide stehen bewusst in der UMGEBUNG und nicht in einer Prozess-Variable:
Die Wachen rufen einander als Subprozesse auf (`publish_gate.
affiliate_profi_failures()` → `scripts/affiliate_profi_check.py --json`).
Ein Monkeypatch im Testprozess erreicht das Kind nicht – die Umgebung erbt
sich in jedes Kind. Benutzung aus Tests über `scripts/repo_isolation.py`:

  from repo_isolation import ledger_sandbox
  with ledger_sandbox():
      bestand_gate.run_gate()      # schreibt kein Wort ins echte Ledger

CLI:
  python3 scripts/audit_log.py --selftest          # Vertrag in beide Richtungen
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

# Isolation des Beweis-Ledgers (C27). Namen sind Vertrag: repo_isolation.py,
# test_audit_ledger_isolation.py und governance_contract.c27_ledger_isolation()
# prüfen genau diese beiden Konstanten.
AUDIT_DIR_ENV = "FFC_AUDIT_DIR"
AUDIT_OFF_ENV = "FFC_AUDIT_DISABLE"
_WAHRHEIT = {"1", "true", "yes", "on", "ja"}


def audit_abgeschaltet() -> bool:
    """True, wenn das Ledger für diesen Prozess hart stummgeschaltet ist."""
    return os.environ.get(AUDIT_OFF_ENV, "").strip().lower() in _WAHRHEIT


def audit_verzeichnis() -> str:
    """Wirksames Zielverzeichnis des Ledgers (Umlenkung vor Repo-Pfad).

    Jeder Schreib- UND Lesepfad dieses Moduls geht hier durch, damit ein
    umgelenkter Lauf seine eigenen Zeilen liest und nicht die des Repos.
    """
    ziel = os.environ.get(AUDIT_DIR_ENV, "").strip()
    return ziel or AUDIT_DIR


def _ensure_dir() -> None:
    os.makedirs(audit_verzeichnis(), exist_ok=True)


def _today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def log_event(module: str, action: str, input: dict | None = None,
              output: dict | None = None, status: str = "ok",
              critical: bool = False, commit: str | None = None) -> str | None:
    """Schreibt ein Audit-Event. Liefert den Pfad der Log-Datei.

    Liefert None und schreibt nichts, wenn das Ledger über FFC_AUDIT_DISABLE
    stummgeschaltet ist (C27) – ein Testlauf darf keine Beweise fabrizieren.
    """
    if audit_abgeschaltet():
        return None
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
    path = os.path.join(audit_verzeichnis(), f"{_today()}.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def load_events() -> list[dict]:
    """Lädt alle Audit-Events (sortiert nach Zeitstempel)."""
    events = []
    for f in sorted(glob.glob(os.path.join(audit_verzeichnis(), "*.jsonl"))):
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
    for f in glob.glob(os.path.join(audit_verzeichnis(), "*.jsonl")):
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


def selftest() -> list:
    """Beweist den Isolations-Vertrag in BEIDE Richtungen (C6/C27).

    Ohne diese Probe wäre die Umlenkung eine Behauptung: Sie muss nachweislich
    (a) im Normalfall nichts ändern, (b) unter FFC_AUDIT_DIR das echte Ledger
    unberührt lassen und (c) unter FFC_AUDIT_DISABLE ganz stumm bleiben.
    Der Selbsttest schreibt ausschließlich in ein Temp-Verzeichnis.
    """
    import tempfile

    def fingerabdruck(verzeichnis):
        """{Dateiname: Größe} – Anhängen UND Anlegen fallen beide auf."""
        try:
            namen = sorted(glob.glob(os.path.join(verzeichnis, "*.jsonl")))
        except OSError:
            return {}
        return {os.path.basename(p): os.path.getsize(p) for p in namen}

    fehler = []
    alt_dir = os.environ.get(AUDIT_DIR_ENV)
    alt_off = os.environ.get(AUDIT_OFF_ENV)
    echt = AUDIT_DIR
    echt_vorher = fingerabdruck(echt)
    tmp = tempfile.mkdtemp(prefix="audit-selftest-")
    try:
        # (a) Normalfall: kein Vertrag ohne Wirkung im Betrieb
        os.environ.pop(AUDIT_DIR_ENV, None)
        os.environ.pop(AUDIT_OFF_ENV, None)
        if audit_verzeichnis() != echt:
            fehler.append("ohne Umlenkung zeigt audit_verzeichnis() nicht auf das "
                          "echte Ledger (data/audit)")
        if audit_abgeschaltet():
            fehler.append("ohne FFC_AUDIT_DISABLE meldet sich das Ledger stumm – "
                          "der Betrieb würde keine Beweise mehr schreiben")

        # (b) Umlenkung: Zeile entsteht, aber NICHT im Repo
        os.environ[AUDIT_DIR_ENV] = tmp
        pfad = log_event(module="audit_selftest", action="umlenkung",
                         input={}, output={}, status="ok")
        if not pfad or os.path.dirname(pfad) != tmp:
            fehler.append(f"FFC_AUDIT_DIR wird ignoriert: Zeile ging nach {pfad}")
        elif not os.path.isfile(pfad):
            fehler.append("FFC_AUDIT_DIR: es entstand keine lesbare Zeile")
        elif len(load_events()) != 1:
            fehler.append("load_events() folgt der Umlenkung nicht – ein umgelenkter "
                          "Lauf liest das echte Ledger")

        # (c) Stummschaltung: harter No-Op
        os.environ[AUDIT_OFF_ENV] = "1"
        if log_event(module="audit_selftest", action="stumm") is not None:
            fehler.append("FFC_AUDIT_DISABLE=1 schreibt trotzdem eine Zeile")
        vor = len(glob.glob(os.path.join(tmp, "*.jsonl")))
        log_event(module="audit_selftest", action="stumm")
        if len(glob.glob(os.path.join(tmp, "*.jsonl"))) != vor:
            fehler.append("FFC_AUDIT_DISABLE=1 legt eine neue Datei an")
        os.environ.pop(AUDIT_OFF_ENV, None)

        # Die Wahrheit liegt in der Umgebung, nicht im Prozess: ein Kindprozess
        # muss dieselbe Umlenkung sehen (publish_gate → affiliate_profi_check).
        if audit_verzeichnis() != tmp:
            fehler.append("audit_verzeichnis() liest die Umgebung nicht bei jedem "
                          "Aufruf – geerbte Umlenkung würde verloren gehen")
    finally:
        for name, wert in ((AUDIT_DIR_ENV, alt_dir), (AUDIT_OFF_ENV, alt_off)):
            if wert is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = wert
        for datei in glob.glob(os.path.join(tmp, "*.jsonl")):
            try:
                os.remove(datei)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass

    # Schlussbeweis: Der Selbsttest selbst darf das Ledger nicht antasten –
    # sonst wäre die Probe Teil des Problems, das sie prüft.
    if fingerabdruck(echt) != echt_vorher:
        fehler.append("SELBSTTEST hat data/audit/ verändert – Sofortstopp")
    return fehler


def main() -> int:
    if "--selftest" in sys.argv:
        fehler = selftest()
        if fehler:
            print("🛑 AUDIT-LOG-SELBSTTEST FEHLGESCHLAGEN – Ledger-Isolation defekt.")
            for f in fehler:
                print(f"   {f}")
            return 2
        print(f"✅ Audit-Log-Selbsttest ok: {AUDIT_DIR_ENV} lenkt um, "
              f"{AUDIT_OFF_ENV} schaltet stumm, Normalfall schreibt nach data/audit.")
        return 0
    if "--event" in sys.argv:
        i = sys.argv.index("--event")
        payload = json.loads(sys.argv[i + 1])
        path = log_event(**payload)
        if path is None:
            print(f"Event verworfen: {AUDIT_OFF_ENV} ist gesetzt (Ledger stumm).")
            return 0
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
