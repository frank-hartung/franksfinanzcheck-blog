#!/usr/bin/env python3
# ============================================================================
#  COPY-EDITING-GATE – FranksFinanzcheck Highend-Orchestrierung
#  --------------------------------------------------------------------------
#  Steuert die bereits installierte Offline-Engine-Kette in einem festen,
#  wiederholbaren Highend-Prozess (Seven Sweeps + YMYL + Schwellen).
#
#  Engines (SSOT – Single Source of Truth, nichts wird ersetzt):
#    1 grammar_check.py        – LT1–LT4 Grammatik/Rechtschreibung (offline)
#    2 hardcases_guard.py      – H1–H9 deutsche Fest-Fehler (offline)
#    3 zeit_rechtschreibung.py – ZEIT-Niveau (LanguageTool-kompatibel, Premium/offline)
#    4 sprachglatt.py          – DW1–DW9 Glättung + V1 Vorschläge (offline)
#    5 lektor_guard.py         – L1–L12 Verlags-Lektorat
#    6 readability_check.py    – Flesch-Amstad, Satzlänge, Schachtelsätze …
#
#  Vertrag (aus CLAUDE.md / sprachkern.py):
#    - Schutzzonen (Code, Links inkl. Ankertext, Shortcodes, URLs, HTML) werden
#      längentreu maskiert und nie verändert.
#    - Jeder Schreibvorgang läuft über sprachkern.write_verified +
#      Kontext-Probe am Offset.
#    - Selbsttest vor JEDEM Schreibvorgang; Abweichung = Exit 2, kein Schreiben.
#    - Titel/Frontmatter-Anker/Shortcodes/URLs nie schreiben.
#
#  Aufruf:
#    python3 scripts/copy_editing_gate.py                    # voller Highend-Lauf
#    python3 scripts/copy_editing_gate.py --file X.md        # einzelner Artikel
#    python3 scripts/copy_editing_gate.py --new-only         # nur Artikel von heute
#    python3 scripts/copy_editing_gate.py --include-drafts   # Entwürfe mit einbeziehen
#    python3 scripts/copy_editing_gate.py --fix              # Auto-Fix erlauben (harte Allowlist)
#    python3 scripts/copy_editing_gate.py --strict           # Exit 1 bei offenen kritischen Funden
#    python3 scripts/copy_editing_gate.py --json             # maschinenlesbar
#    python3 scripts/copy_editing_gate.py --selftest         # Sabotage-Schutz aller Engines
#    python3 scripts/copy_editing_gate.py --report COPY-EDITING-REPORT.md
#
#  Exit-Codes:
#    0 = sauber / gelaufen
#    1 = offene kritische Funde (nur mit --strict)
#    2 = Selbsttest / Sabotage rot (keine Datei wird angefasst)
# ============================================================================
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

SCRIPTS = {
    "grammar": "grammar_check.py",
    "hardcases": "hardcases_guard.py",
    "zeit": "zeit_rechtschreibung.py",
    "sprachglatt": "sprachglatt.py",
    "lektor": "lektor_guard.py",
    "readability": "readability_check.py",
}

REPORT_DEFAULT = ROOT / "COPY-EDITING-REPORT.md"
JSON_DEFAULT = ROOT / ".copy_editing_report.json"
HISTORY = ROOT / "data" / "copy_editing_history.jsonl"

# Schwellen (Highend-Profi-Agentur)
THRESHOLDS = {
    "flesch_min_neu": 60.0,
    "flesch_target_bestand": 62.0,
    "flesch_floor": 55.0,
    "sent_max": 16,
    "long_word_max_pct": 15.0,
    "nested_max_pct": 10.0,
}

# ---------------------------------------------------------------- Helfer


def _run(engine: str, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    """Führt eine Engine im Repo-Root aus, fängt stdout/stderr, wirft keine Exception."""
    cmd = [sys.executable, str(ROOT / "scripts" / SCRIPTS[engine])] + (extra_args or [])
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def _selftest(engine: str) -> tuple[bool, str]:
    """Läuft den Selbsttest einer Engine. Liefert (grün, ausgabe)."""
    res = _run(engine, ["--selftest"])
    return res.returncode == 0, (res.stdout or "") + (res.stderr or "")


def _analyse(engine: str, args: list[str]) -> tuple[int, str, str]:
    res = _run(engine, args)
    return res.returncode, res.stdout, res.stderr


def _load_json(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- Hauptlauf


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    do_fix = "--fix" in argv
    strict = "--strict" in argv
    as_json = "--json" in argv
    selftest_only = "--selftest" in argv
    include_drafts = "--include-drafts" in argv
    new_only = "--new-only" in argv
    only_file = None
    report_path = REPORT_DEFAULT
    for i, a in enumerate(argv):
        if a == "--file" and i + 1 < len(argv):
            only_file = argv[i + 1]
        elif a.startswith("--file="):
            only_file = a.split("=", 1)[1]
        elif a == "--report" and i + 1 < len(argv):
            report_path = Path(argv[i + 1])

    engine_args: list[str] = []
    if do_fix:
        engine_args.append("--fix")
    if include_drafts:
        engine_args.append("--include-drafts")
    if new_only:
        engine_args.append("--new-only")
    if only_file:
        engine_args += ["--file", only_file]
    # readability_check liefert seinen Flesch-Ø nur über --json auf stdout;
    # das brauchen wir für den Schwellen-Check, also immer mitgeben.
    engine_args.append("--json")

    # ========================================================================
    # PHASE 0 – Selbsttests aller Engines (Sabotage-Schutz, fail-closed)
    # ========================================================================
    st_results: dict[str, tuple[bool, str]] = {}
    for name in SCRIPTS:
        ok, out = _selftest(name)
        st_results[name] = (ok, out)

    if selftest_only:
        print("🔍 COPY-EDITING-GATE – Selbsttest aller Engines")
        print("=" * 60)
        alle_grün = True
        for name, (ok, out) in st_results.items():
            status = "✅ grün" if ok else "❌ ROT"
            if not ok:
                alle_grün = False
            print(f"  {name:14s} {status}")
            if not ok:
                for line in out.splitlines()[:5]:
                    print(f"      {line}")
        if not alle_grün:
            print("\n🛑 SELBSTTEST ROT – mindestens eine Engine sabotagegefährdet.")
            return 2
        print("\n✅ Alle Engines-Selbsttests grün – Gate ist scharf.")
        return 0

    if not all(ok for ok, _ in st_results.values()):
        print("🛑 SELBSTTEST ROT – Copy-Editing-Gate bricht vor jedem Schreiben ab (Exit 2).")
        for name, (ok, out) in st_results.items():
            if not ok:
                print(f"  {name}: {out.strip().splitlines()[:3]}")
        return 2

    # ========================================================================
    # PHASE 1–6 – Engines in fixer Reihenfolge
    # ========================================================================
    engine_results: dict[str, dict] = {}
    alle_strict_rot = False

    for name in SCRIPTS:
        args = list(engine_args)
        if strict:
            args.append("--strict")

        rc, out, err = _analyse(name, args)
        result = {"rc": rc, "stdout": out, "stderr": err, "json": None}

        # JSON-Report parsen, falls vorhanden
        json_map = {
            "grammar": ROOT / ".grammar_report.json",
            "hardcases": ROOT / "HARDCASES-REPORT.md",  # kein JSON, nur Report
            "zeit": ROOT / ".zeit_rechtschreibung_report.json",
            "sprachglatt": ROOT / ".sprachglatt_report.json",
            "lektor": ROOT / "LEKTOR-REPORT.md",  # kein JSON
        }
        # Lesbarkeit schreibt kein JSON-File, sondern gibt es auf stdout aus
        # (wird immer mit --json aufgerufen, siehe engine_args). Direkt aus stdout parsen.
        if name == "readability":
            try:
                result["json"] = json.loads(out)
            except json.JSONDecodeError:
                result["json"] = None
        else:
            jp = json_map.get(name)
            if jp:
                result["json"] = _load_json(jp)

        engine_results[name] = result

        # strict-Rot detektieren (Exit 1 bei offenen Funden)
        if strict and rc == 1:
            alle_strict_rot = True

    # ========================================================================
    # PHASE 7 – Auswertung & Schwellen-Check
    # ========================================================================
    summary = _auswerten(engine_results, THRESHOLDS)

    # ========================================================================
    # PHASE 8 – Report schreiben
    # ========================================================================
    report_md = _bericht_schreiben(summary, engine_results, do_fix, strict)
    report_path.write_text(report_md, encoding="utf-8")

    # JSON
    if as_json or True:  # immer maschinenlesbar mitschreiben
        JSON_DEFAULT.write_text(
            json.dumps(
                {
                    "generated": _now(),
                    "gate": "copy-editing-gate (highend, profi-agentur)",
                    "do_fix": do_fix,
                    "strict": strict,
                    "summary": summary,
                    "engines": {
                        k: {
                            "rc": v["rc"],
                            "json": v["json"],
                        }
                        for k, v in engine_results.items()
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    # History (versioniert, dedupliziert pro Tag)
    _history_append(summary, do_fix)

    # Ausgabe
    print(report_md.splitlines()[0])
    print(f"📊 Funde: {summary['total_funde']} | geheilt: {summary['total_geheilt']} | offen: {summary['total_offen']}")
    f_oa = summary["flesch_oa"]
    if f_oa is not None:
        print(f"📈 Flesch-Amstad Ø: {f_oa:.1f} | Ziel ≥ {THRESHOLDS['flesch_target_bestand']}")
    else:
        print(f"📈 Flesch-Amstad Ø: n/a | Ziel ≥ {THRESHOLDS['flesch_target_bestand']}")
    print(f"📄 Report: {report_path}")

    if strict and alle_strict_rot:
        print("🛑 STRICT: Offene kritische Funde – Exit 1.")
        return 1

    return 0


# ---------------------------------------------------------------- Auswertung


def _auswerten(engine_results: dict, thresholds: dict) -> dict:
    total_funde = 0
    total_geheilt = 0
    total_offen = 0
    flesch_oa = None
    details: list[dict] = []

    for name, res in engine_results.items():
        j = res["json"] or {}
        funde = j.get("findings", j.get("DW", 0)) or 0
        fixed = j.get("fixed", 0) or 0
        offen = j.get("open", max(0, funde - fixed)) or 0
        total_funde += funde
        total_geheilt += fixed
        total_offen += offen
        details.append(
            {
                "engine": name,
                "rc": res["rc"],
                "funde": funde,
                "geheilt": fixed,
                "offen": offen,
            }
        )

        # Lesbarkeit auswerten (Key: avg_flesch)
        if name == "readability" and j:
            flesch_oa = j.get("avg_flesch") or None

    return {
        "total_funde": total_funde,
        "total_geheilt": total_geheilt,
        "total_offen": total_offen,
        "flesch_oa": flesch_oa,
        "flesch_target": thresholds["flesch_target_bestand"],
        "flesch_min_neu": thresholds["flesch_min_neu"],
        "flesch_floor": thresholds["flesch_floor"],
        "details": details,
    }


# ---------------------------------------------------------------- Report


def _bericht_schreiben(summary: dict, engine_results: dict, do_fix: bool, strict: bool) -> str:
    L = [
        "# 📋 COPY-EDITING-REPORT (Highend, Profi-Agentur)",
        "",
        f"**Stand:** {_now()} UTC",
        f"**Modus:** {'FIX (Auto-Allowlist)' if do_fix else 'REPORT (nur melden)'}",
        f"**Strict:** {'ja' if strict else 'nein'}",
        "",
        "## Zusammenfassung",
        "",
        f"- **Engines:** {len(engine_results)} (grammar, hardcases, zeit, sprachglatt, lektor, readability)",
        f"- **Funde gesamt:** {summary['total_funde']}",
        f"- **Geheilt (Auto-Fix):** {summary['total_geheilt']}",
        f"- **Offen (menschliche Entscheidung):** {summary['total_offen']}",
        f"- **Flesch-Amstad Ø:** {summary['flesch_oa']:.1f} (Ziel ≥ {summary['flesch_target']}, Mindest {summary['flesch_min_neu']})" if summary["flesch_oa"] is not None else "- **Flesch-Amstad Ø:** n/a (keine Artikel gemessen)",
        "",
        "## Engine-Detail",
        "",
        "| Engine | Status | Funde | Geheilt | Offen |",
        "|---|---|---:|---:|---:|",
    ]
    for d in summary["details"]:
        status = "✅ grün" if d["rc"] == 0 else ("⚠️ offen" if d["rc"] == 1 else "❌ rot")
        L.append(
            f"| {d['engine']} | {status} | {d['funde']} | {d['geheilt']} | {d['offen']} |"
        )

    L += [
        "",
        "## Schwellen-Check (Highend)",
        "",
        (f"- Flesch-Amstad Ø: {summary['flesch_oa']:.1f} → Ziel ≥ {summary['flesch_target']}: "
         f"{'✅ erfüllt' if summary['flesch_oa'] >= summary['flesch_target'] else '❌ unter Ziel'}")
        if summary["flesch_oa"] is not None
        else f"- Flesch-Amstad Ø: n/a → Ziel ≥ {summary['flesch_target']}: ⚠️ nicht gemessen",
        f"- Offene kritische Funde: {summary['total_offen']} → Soll 0: "
        f"{'✅ sauber' if summary['total_offen'] == 0 else '❌ nachbessern'}",
        "",
        "## Nächster Schritt",
        "",
        "- Automatisierte Funde sind geheilt (Allowlist) oder im Report dokumentiert.",
        "- Grauzonen und V1/L1–L12-Vorschläge werden durch die menschliche Endredaktion entschieden.",
        "- Danach: `scripts/endredaktion.py` für finale Prüfung + Freigabe (Seven Sweeps + AI-Tell-Check + YMYL-Panel).",
        "",
        "---",
        "_Copy-Editing-Gate v3.0.0 – FranksFinanzcheck Highend (de-DE, YMYL). Offline, ohne API, ohne externen Dienst._",
    ]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- History


def _history_append(summary: dict, do_fix: bool) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    eintrag = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "mode": "FIX" if do_fix else "REPORT",
        "funde": summary["total_funde"],
        "geheilt": summary["total_geheilt"],
        "offen": summary["total_offen"],
        "flesch_oa": summary["flesch_oa"],
    }
    # Dedupe: gleichen Tag nicht doppelt schreiben
    zeilen = []
    if HISTORY.exists():
        zeilen = HISTORY.read_text(encoding="utf-8").splitlines()
    if zeilen:
        try:
            letzter = json.loads(zeilen[-1])
            if letzter.get("date") == eintrag["date"]:
                zeilen[-1] = json.dumps(eintrag, ensure_ascii=False)
                HISTORY.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
                return
        except Exception:
            pass
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sys.exit(main())
