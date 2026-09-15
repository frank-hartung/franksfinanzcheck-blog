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
#    H6  VERLUSTPRÜFUNG (rotation-bewusst, 15.09.2026): verglichen wird die
#        Arbeitstree-Datei mit dem letzten Commit-Stand (HEAD, sonst Index).
#        Anhängen ist erlaubt. Schrumpfen ist NUR erlaubt, wenn es die
#        dokumentierte W5-Rotation von workspace_guard ist (Kap HIST_MAX_LINES,
#        erhaltener Teil = exakter Schwanz des Vorzustands). Umschreiben im
#        Mittelteil oder Verlust über die Kapazität hinaus -> Exit 2.
#        Kein Befund, kein Verlust: ohne Git-Baseline (frischer Shallow-Klon,
#        CI ohne Blob) schweigt die Prüfung – eine Wache, die im Zweifel rot
#        meldet, macht ihren eigenen Bericht unbrauchbar.
#
#  Zusammenspiel W5/H6: workspace_guard.py „GESCHICHTSLINIE-ROTATION“ stutzt
#  jede data/*_history.jsonl jenseits von HIST_MAX_LINES (400) auf den neuesten
#  Teil – das ist erlaubt und dokumentiert, aber es ist eben auch ein Schrumpf-
#  ereignis. H6 ist deshalb so gebaut, dass es genau diese Form erkennt und
#  alles andere meldet; die Kapazität liest es aus workspace_guard.py aus und
#  meldet Auseinanderlaufen beider Werte.
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
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HISTORY_GLOB = "data/*_history.jsonl"
ROTATION_KAP = 400          # == workspace_guard.HIST_MAX_LINES (wird gegengeprüft)
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
# H6: Verlustprüfung gegen den Vorzustand – als reine Funktion auf Zeilenlisten,
# damit der Selbsttest sie ohne Git durchspielen kann.
# ------------------------------------------------------------
def rotation_kapazitaet() -> int:
    """Kapazität aus workspace_guard.py ablesen (kein Import – dort läuft
    Modulcode). Finst der Reader nichts, gilt die eigene Konstante."""
    try:
        txt = (ROOT / "scripts" / "workspace_guard.py").read_text(encoding="utf-8")
        m = re.search(r"^HIST_MAX_LINES\s*=\s*(\d+)", txt, re.M)
        return int(m.group(1)) if m else ROTATION_KAP
    except Exception:  # noqa: BLE001
        return ROTATION_KAP


def check_verlust(name: str, vorher: list, jetzt: list, kap=None):
    """(harte Fehler, Funde, Info) für einen Historien-Vergleich.

    vor = Zeilen des letzten Commit-Stands, jetzt = Arbeitstree. leer =
    keine Baseline (dann schweigt die Prüfung)."""
    hard: list = []
    warn: list = []
    info = ""
    kapz = kap if kap is not None else rotation_kapazitaet()
    if not vorher or not jetzt:
        return hard, warn, info
    if jetzt[:len(vorher)] == vorher:
        return hard, warn, (f"angewachsen um {len(jetzt) - len(vorher)}"
                            if len(jetzt) > len(vorher) else "unverändert")
    if len(vorher) > kapz and len(jetzt) == kapz and jetzt == vorher[-kapz:]:
        return hard, warn, f"W5-Rotation {len(vorher)} → {kapz} Records (erlaubt)"
    if len(jetzt) < len(vorher):
        hard.append(f"{name}: H6 Historie geschrumpft: {len(vorher)} → {len(jetzt)} "
                    f"Records, nicht als W5-Rotation erklärbar (Kapazität {kapz}) – "
                    f"Records fehlen oder Reihenfolge gedreht")
    else:
        hard.append(f"{name}: H6 Append-Only verletzt: die {len(vorher)} Zeilen des "
                    f"letzten Stands stehen nicht mehr unverändert am Anfang – "
                    f"Historie wurde umgeschrieben, nicht angehängt")
    return hard, warn, info


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


# H6-Faelle: (name, vorher, jetzt, erwartete harte Fehler, Info-Pflichtwort)
SELBSTTEST_VERLUST = [
    ("anhangen", ['{"ts": "2026-08-12T00:00:00Z"}', '{"ts": "2026-08-13T00:00:00Z"}'],
     ['{"ts": "2026-08-12T00:00:00Z"}', '{"ts": "2026-08-13T00:00:00Z"}',
      '{"ts": "2026-08-14T00:00:00Z"}'], 0, "angewachsen"),
    ("unveraendert", ['{"ts": "2026-08-12T00:00:00Z"}'],
     ['{"ts": "2026-08-12T00:00:00Z"}'], 0, "unverändert"),
    ("rotation-erlaubt", ['{"n": %d}' % n for n in range(1, 41)],
     ['{"n": %d}' % n for n in range(13, 41)], 0, "W5-Rotation"),
    ("schwunderhalb", ['{"ts": "2026-08-01T00:00:00Z"}', '{"ts": "2026-08-02T00:00:00Z"}',
                       '{"ts": "2026-08-03T00:00:00Z"}'],
     ['{"ts": "2026-08-02T00:00:00Z"}', '{"ts": "2026-08-03T00:00:00Z"}'], 1, "geschrumpft"),
    ("mittelteil-umgeschrieben", ['{"ts": "2026-08-01T00:00:00Z"}', '{"ts": "2026-08-02T00:00:00Z"}'],
     ['{"ts": "2026-08-01T00:00:00Z"}', '{"ts": "2026-08-09T00:00:00Z"}',
      '{"ts": "2026-08-03T00:00:00Z"}'], 1, "Append-Only verletzt"),
    ("austausch-same-length", ['{"ts": "2026-08-01T00:00:00Z"}', '{"ts": "2026-08-02T00:00:00Z"}'],
     ['{"ts": "2026-08-11T00:00:00Z"}', '{"ts": "2026-08-12T00:00:00Z"}'], 1, "umgeschrieben"),
    ("keine-baseline", [], ['{"ts": "2026-08-01T00:00:00Z"}'], 0, ""),
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
    # H6 – Verlustprüfung, mit fest vorgegebener Kapazität (28), damit der Fall
    # nicht von der workspace_guard-Konstanten abhängt
    for name, vorher, jetzt, exp_hard, info_pflicht in SELBSTTEST_VERLUST:
        hard, warn, info = check_verlust(name + ".jsonl", vorher, jetzt, kap=28)
        if len(hard) != exp_hard:
            fehler.append(f"  H6-Fall '{name}': erwartet {exp_hard} hart, "
                          f"bekam {len(hard)} ({hard[:1]})")
        # Harte Faelle beweisen ueber ihre Meldung, saubere ueber die Info-Zeile.
        beleg = (hard[0] if hard else info)
        if info_pflicht and info_pflicht not in beleg:
            fehler.append(f"  H6-Fall '{name}': Beleg „{info_pflicht}“ fehlt ({beleg!r})")
    if rotation_kapazitaet() != 400:
        fehler.append(f"  H6: Rotationskapazität läuft auseinander – history_guard "
                      f"kennt 400, workspace_guard meldet {rotation_kapazitaet()}")
    return fehler


def baseline_zeilen(rel: str) -> list:
    """Zeilen des letzten Commit-Stands; erst HEAD, dann der Index. Kein Git,
    kein Blob, flacher Klon ohne Objekt -> leere Liste (Prüfung schweigt)."""
    for rev in (f"HEAD:{rel}", f":{rel}"):
        try:
            r = subprocess.run(["git", "show", rev], cwd=ROOT,
                               capture_output=True, timeout=25)
        except Exception:  # noqa: BLE001
            return []
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace").splitlines()
    return []


def main() -> int:
    stf = selftest()
    if stf:
        print("🛑 HISTORY-GUARD-SELBSTTEST FEHLGESCHLAGEN – Wache geschützt.")
        print("   Bitte scripts/history_guard.py pruefen:")
        print("\n".join(stf))
        return 2
    print(f"✅ History-Guard-Selbsttest: {len(SELFTEST) + len(SELBSTTEST_VERLUST)} Fälle grün.")

    paths = sorted(DATA.glob("*.jsonl")) + sorted((DATA / "audit").glob("*.jsonl"))
    paths = [p for p in paths if p.name.endswith("_history.jsonl")
             or p.parent.name == "audit"]
    total_hard, total_warn, files_ok = 0, 0, 0
    rotationen = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        hard, warn = check_lines(path.name, lines)
        rel = str(path.relative_to(ROOT))
        v_hard, v_warn, v_info = check_verlust(path.name, baseline_zeilen(rel), lines)
        hard += v_hard
        warn += v_warn
        if "W5-Rotation" in v_info:
            rotationen.append(path.name)
        elif v_info and v_info.startswith("angewachsen"):
            pass    # normaler Betrieb: Anhängen ist der Erwartungsfall
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

    if rotationen:
        print(f"  📜 Rotation (W5, erlaubt): {len(rotationen)} Historie(n) auf "
              f"{rotation_kapazitaet()} Records gestutzt – "
              + ", ".join(rotationen[:6])
              + (" …" if len(rotationen) > 6 else ""))
    print(f"🧾 {files_ok}/{len(paths)} Historien sauber · "
          f"{total_hard} harte Fehler · {total_warn} Funde.")
    if total_hard:
        return 2
    if total_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
