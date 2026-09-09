#!/usr/bin/env python3
# ============================================================
#  HISTORY-GUARD – Wache für alle Append-Only-Historien
#  (Profi-Level, 09.09.2026 – nach Merge-Artefakt-Fund)
#
#  Anlass (Frank-Fund): data/{doctor,integrity,redaktion,table}_history.jsonl
#  trugen seit Mitte August unaufgelöste Git-Konfliktmarker
#  (<<<<<<< HEAD / ======= / >>>>>>> <commit>) aus einem schlechten Merge.
#  Kein Skript las diese Zeilen – aber eine append-only Historie,
#  die Konfliktmarker enthält, ist ein Beweis-/Audit-Risiko.
#
#  Auftrag der Wache (rein lesend, KEINE Heilung):
#    H1  KONFLIKT-MARKER: Zeilen, die als <<<<<<<, |||||||, =======,
#        >>>>>>> beginnen -> Exit 2 (Sabotage an der Beweiskette).
#    H2  JSON-REINHEIT: jede Zeile muss ein JSON-Objekt sein.
#    H3  SCHEMA: bekannte Historien (doctor/integrity/redaktion/table)
#        müssen ihre Pflichtfelder mit richtigem Typ tragen
#        (Zusatzfelder sind erlaubt – Schemas dürfen wachsen).
#    H4  CHRONOLOGIE: date-Felder müssen ISO-formatig und monoton
#        nicht-fallend sein (Append-Only-Beweis der Tagesläufe).
#        ts-Felder werden nur FORMATgeprüft: Parallel-/Nachzügler-Jobs
#        dürfen legitim asynchron anhängen (realer Fall: audit-08-31),
#        ts-Reihenfolge ist deshalb KEIN Beweis.
#    H5  BLANKZEILEN: leere Zeilen im Log -> Fund (kein Sabotage).
#
#  KEINE Dedupe: gleiche Werte mehrfach = echte Einzelläufe
#  (Konvention aller *_history.jsonl). Die Wache entfernt NICHTS –
#  eine bewusste Heilung gehört in einen dokumentierten Eingriff.
#
#  SABOTAGE-SCHUTZ: eingefrorene Selbsttest-Fälle; Abweichung -> Exit 2
#  bevor IRGENDETWAS geprüft wird (Wache-immun-Prinzip wie alle Guards).
#
#  Aufruf:
#    python3 scripts/history_guard.py              # Prüfung (read-only)
#    python3 scripts/history_guard.py --dry-run    # identisch (Wache schreibt nie)
#    python3 scripts/history_guard.py --new-only   # vom Doktor durchgereicht, no-op
#
#  Eingehängt: scripts/blog_doctor.py (Kette, Phase 0-LOCK, nach integrity)
# ============================================================

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HISTORY_GLOB = "data/*_history.jsonl"
AUDIT_GLOB = "data/audit/*.jsonl"

# Doktor/Engine reichen --dry-run / --new-only durch; die Wache ist
# immer read-only, beide Flags sind bewusste No-Ops.
_ = "--dry-run" in sys.argv
_ = "--new-only" in sys.argv
if "--fix" in sys.argv:
    print("ℹ history_guard ist eine reine Wache – keine Auto-Heilung.")
    print("  Bewusste Bereinigung (Union/chronologisch) gehört in einen "
          "dokumentierten, eigenen Commit.")

MARKER = re.compile(r"^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\||={7,})")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# ISO-8601 optional mit Sekundenbruchteilen und Z/±Offset (µs-Zeitstempel echt).
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
                    r"(?:Z|[+-]\d{2}:\d{2})?)?$")

# Pflichtschema der vier betroffenen Historien (Zusatzfelder erlaubt).
KNOWN_SCHEMAS = {
    "doctor_history.jsonl": {"date": str, "wachen": int, "ok": int,
                             "funde": int, "sabotage": int, "hard_stop": bool},
    "integrity_history.jsonl": {"date": str, "kritisch": int, "fest": int},
    "redaktion_history.jsonl": {"date": str, "artikel": int, "alle_ok": bool},
    "table_history.jsonl": {"date": str, "funde": int, "geheilt": int},
}


def check_lines(name: str, lines: list[str]) -> tuple[list[str], list[str]]:
    """Prüft Zeilen einer History. Rückgabe: (Harte-Fehler, Warn-Funde)."""
    hard: list[str] = []
    warn: list[str] = []
    schema = KNOWN_SCHEMAS.get(name)
    dates: list[str] = []

    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            warn.append(f"{name}:{n}: leere Zeile im Log")
            continue
        if MARKER.match(raw):
            # Nur wenn die Zeile KEINE valide JSON-Zeile sein kann:
            # `=======` als Feldinhalt (z. B. "ueberschrift") ist ausgeschlossen,
            # weil wir auf Zeilenanfang + reines Marker-Muster prüfen.
            hard.append(f"{name}:{n}: Git-Konfliktmarker im Append-Only-Log: "
                        f"{raw[:40]!r}")
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:
            hard.append(f"{name}:{n}: keine gültige JSON-Zeile ({exc})")
            continue
        if not isinstance(obj, dict):
            hard.append(f"{name}:{n}: JSON ist kein Objekt "
                        f"(Typ {type(obj).__name__})")
            continue
        if schema:
            for key, typ in schema.items():
                if key not in obj:
                    hard.append(f"{name}:{n}: Pflichtfeld '{key}' fehlt")
                elif not isinstance(obj[key], typ):
                    hard.append(f"{name}:{n}: Feld '{key}' muss {typ.__name__} "
                                f"sein, ist {type(obj[key]).__name__} "
                                f"({obj[key]!r})")
        if isinstance(obj.get("date"), str):
            if not DATE_RE.match(obj["date"]):
                hard.append(f"{name}:{n}: date nicht ISO (JJJJ-MM-TT): "
                            f"{obj['date']!r}")
            else:
                dates.append(obj["date"])
        if isinstance(obj.get("ts"), str) and not TS_RE.match(obj["ts"]):
            hard.append(f"{name}:{n}: ts nicht ISO: {obj['ts']!r}")

    # date-Folge = Append-Only-Beweis der Tagesläufe (hart).
    # ts-Folge wird bewusst nicht geprüft (parallele/verzögerte Jobs).
    if dates and any(a > b for a, b in zip(dates, dates[1:])):
        hard.append(f"{name}: Append-Only verletzt: date-Folge nicht "
                    f"chronologisch ({dates[0]} … {dates[-1]})")
    return hard, warn


# ------------------------------------------------------------
# SELBSTTEST (eingefroren, Wache-immun): Abweichung -> Exit 2
# ------------------------------------------------------------
SELFTEST = [
    ("gesund", ['{"date": "2026-08-12", "kritisch": 0, "fest": 0}',
                '{"date": "2026-08-13", "kritisch": 1, "fest": 2}'], 0, 0),
    ("konflikt-marker", ['{"date": "2026-08-12", "kritisch": 0, "fest": 0}',
                         '<<<<<<< HEAD'], 1, 0),
    ("non-json", ['{"date": "2026-08-12"', '{"date": "2026-08-13", "kritisch": 0, "fest": 0}'], 1, 0),
    ("datum-ruecklaeufig", ['{"date": "2026-08-13", "kritisch": 0, "fest": 0}',
                            '{"date": "2026-08-12", "kritisch": 0, "fest": 0}'], 1, 0),
    ("pflichtfeld-typ", ['{"date": "2026-08-12", "kritisch": "x", "fest": 0}'], 1, 0),
    ("blank-zeile", ['{"date": "2026-08-12", "kritisch": 0, "fest": 0}', ""], 0, 1),
]


def selftest() -> list[str]:
    fehler = []
    proben = {
        "konflikt-marker": "integrity_history.jsonl",
        "non-json": "integrity_history.jsonl",
        "datum-ruecklaeufig": "integrity_history.jsonl",
        "pflichtfeld-typ": "integrity_history.jsonl",
        "blank-zeile": "integrity_history.jsonl",
    }
    for name, lines, exp_hard, exp_warn in SELFTEST:
        hard, warn = check_lines(proben.get(name, name + ".jsonl"), lines)
        if len(hard) != exp_hard or len(warn) != exp_warn:
            fehler.append(f"  Fall '{name}': erwartet {exp_hard} hard/"
                          f"{exp_warn} warn, bekam {len(hard)}/{len(warn)} "
                          f"({hard[:1]})")
    return fehler


def main() -> int:
    stf = selftest()
    if stf:
        print("🛑 HISTORY-GUARD-SELBSTTEST FEHLGESCHLAGEN – Wache geschützt.")
        print("   Bitte scripts/history_guard.py pruefen:")
        print("\n".join(stf))
        return 2
    print(f"✅ History-Guard-Selbsttest: {len(SELFTEST)} Fälle grün.")

    paths = sorted(DATA.glob("*.jsonl")) + sorted((DATA / "audit").glob("*.jsonl"))
    paths = [p for p in paths if p.name.endswith("_history.jsonl")
             or p.parent.name == "audit"]
    total_hard, total_warn, files_ok = 0, 0, 0
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        hard, warn = check_lines(path.name, lines)
        if lines and lines[-1] == "":
            warn.append(f"{path.name}:EOF: überflüssige Leerzeile")
        total_hard += len(hard)
        total_warn += len(warn)
        if not hard and not warn:
            files_ok += 1
            print(f"  🟢 {path.name}: {len(lines)} Records sauber")
        else:
            print(f"  {'🔴' if hard else '🟡'} {path.name}: "
                  f"{len(lines)} Records, {len(hard)} hart, {len(warn)} Funde")
            for msg in hard + warn:
                print(f"      - {msg}")

    print(f"🧾 {files_ok}/{len(paths)} Historien sauber · "
          f"{total_hard} harte Fehler · {total_warn} Funde.")
    if total_hard:
        return 2
    if total_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
