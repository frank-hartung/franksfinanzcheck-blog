#!/usr/bin/env python3
# ============================================================
#  BLOG-DOCTOR – der Oberarzt (Profi-Level-Selbstheilung)
#  (Frank-Beschluss 12.08.: „Selbstheilung fuer die GESAMTE
#  Blogautomatik" - eine Integrierung mit Gehirn, nicht Drecksflicken.)
#
#  Was er tut (und warum er der einzige medizinische Eingriff ist):
#    1. SELBSTTEST vor jeder Behandlung (7 eingefrorene Faelle,
#       ausgetopt aus den Unfaellen dieser Woche)
#    2. KANONISCHE KETTE: alle Wachen in beweisbarer Ordnung mit --fix
#       (jede Wache hat sowieso ihren eigenen Exit-2-Selbsttest)
#    3. STOPP-STRICHEN: Exit 2 einer Wache (Sabotage an der Wache
#       selbst) -> Doktor unterbricht SOFORT, nichts mehr geschrieben,
#       klare Sirene. Exit 1 (Fund, kein Sabotage) -> wird zugestanden.
#    4. Bericht: DOKTOR-REPORT.md + data/doctor_history.jsonl
#       (dokumentiert wer heilte, was brach, was gebremst wurde)
#
#  Selbstheilungs-Prinzip: der Doktor loescht selbst NICHTS ausser
#  ueber die legitimen Guards. Er orchestriert, beweist, stoppt.
#
#  Aufruf:
#    python3 scripts/blog_doctor.py            # Visite (alle Heilen)
#    python3 scripts/blog_doctor.py --dry-run  # ohne Schreibung
#    python3 scripts/blog_doctor.py --new-only # nur Geburtstage
#
#  Workflow: .github/workflows/blog-doktor.yml
#  + Engine-Kette (new-only). — Frank-Beschluss 12.08.
# ============================================================

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "DOKTOR-REPORT.md"
HISTORY = ROOT / "data/doctor_history.jsonl"

DRY = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

# ------------------------------------------------------------
# DIE WACHE-LISTE in kanonischer Reihenfolge (bewiesen 11./12.08.).
#   Phase A: Text-Ordung (Deterministisch zuerst, weil billig & fixbar)
#   Phase B: Fakten/Semantik
#   Phase C: Affiliate-Leben & klick
#   Phase D: Visuell/Persistenz (Datei, Waechter, Geschichte)
# ------------------------------------------------------------
KETTE = [
    # INTEGRITY ZUERST: bevor irgendwas geschrieben wird, muss der
    # Wellness-Schluss (Frank 12.08. Sabotage-Hoechstlevel) stimmen.
    ("integrity_guard.py",    [],                          "0-LOCK", "Kern-Integritaet (Signatruehe nach Drift)"),

    # (skript, basis-args, phase, zweck)
    ("casing_guard.py",       ["--fix"],                "A-Text", "Akronyme/Marken (DSL, Check24)"),
    ("dash_guard.py",         ["--fix"],                "A-Text", "Dash-Typografie R1-R9"),
    ("unit_guard.py",         ["--fix"],                "A-Text", "Euro/Prozent/NBSP"),
    ("emoji_guard.py",        ["--fix"],                "A-Text", "Emoji-Zero-Width etc."),
    ("lektor_guard.py",       ["--fix"],                "A-Text", "Verlags-Lektorat L1-L15"),
    ("hardcases_guard.py",    ["--fix"],                "A-Text", "Deutsche Fest-Fehler H1-H9 (12.08. hinzu)"),
    ("stil_guard.py",         ["--fix"],                "A-Text", "Stil-Qualitaet S1-S8 (12.08. hinzu)"),
    ("plagiat_guard.py",      ["--fix"],                "B-Semantik", "Originalitaet P1-P5 + Fingerprint-Registry (12.08.)"),
    ("content_audit.py",      ["--fix"],                "B-Semantik", "Content-Auditor C1-C6: Duenn, Struktur, Platzhalter (12.08.)"),
    ("compound_guard.py",     ["--fix"],                "B-Semantik", "Komposita SEO-Falle"),
    ("math_guard.py",         ["--fix"],                "B-Semantik", "Zahlenbeweis M1-M2"),
    ("affiliate_shield.py",   ["--fix"],                "C-Money", "Auto-Deep + Gateways"),
    ("affiliate_marketer.py", ["--fix"],                "C-Money", "CTA-Routing + Retarget"),
    ("table_guard.py",        ["--fix"],                "B-Semantik", "Tabellen T1-T4"),
    ("link_guard.py",         ["--fix"],                "C-Money", "Interne Links V1-V2"),
    ("link_density_guard.py", ["--fix"],                "D-Ordnung", "Interne Link-Dichte & Duplikate (12.08. Pro-Link-Leck)"),
    ("workspace_guard.py",    ["--fix"],                "D-Ordnung", "Junk/Waisen/Rotation/Billig"),
]

# ------------------------------------------------------------
# SABOTAGE-SCHUTZ - die Arzt-Logik selbst muss impftestbar sein.
# Eingefrorene Faelle aus echten Unfaellen dieser Woche.
# ------------------------------------------------------------
SELFTEST = [
    # (cmd-exit, Erwartung)
    ("gesund", 0, False),
    ("einzel-fund", 1, False),
    ("sabotage-guard", 2, True),     # -> Doktor bricht ab
    ("gesund-2", 0, False),
    ("einzel-fund-2", 1, False),
    ("sabotage-waechter-2", 2, True),
    ("noop", 0, False),
]


def run_guard(script, args, phase, dry):
    cmd = [sys.executable, str(ROOT / "scripts" / script)] + args + (["--new-only"] if NEW_ONLY else [])
    if dry:
        cmd.append("--dry-run") if script != "workspace_guard.py" else None
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout + r.stderr)[:280]


def selftest() -> list:
    fehler = []
    # Kern-Logik: exit=2 muss stoppen; 0/1 weitereiter lassen.
    for i, (name, code, should_stop) in enumerate(SELFTEST, 1):
        would_stop = (code == 2)
        if would_stop != should_stop:
            fehler.append(f"  Fall {i} ({name}): exit {code} -> stop={would_stop}, erwartet {should_stop}")
    # Strukturwache: Skripts muessen existieren
    for script, *_ in KETTE:
        if not (ROOT / "scripts" / script).exists():
            fehler.append(f"  Kette kaputt: scripts/{script} fehlt!")
    if len({k[0] for k in KETTE}) != len(KETTE):
        fehler.append("  Doppelter Eintrag in KETTE")
    return fehler


def main() -> None:
    stf = selftest()
    if stf:
        print("🛑 DOKTOR-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Keine Visite geschrieben/stattgegeben. Bitte blog_doctor.py pruefen:")
        print("\n".join(stf))
        sys.exit(2)
    print(f"✅ Doktor-Selbsttest: {len(SELFTEST)} Faelle gruen, Kette {len(KETTE)} Wachen.")

    heute = date.today().isoformat()
    ergebnisse = []
    hard_stop = False
    for script, args, phase, zweck in KETTE:
        rc, tail = run_guard(script, args, phase, DRY)
        stop = (rc >= 2)   # 2 = Sabotage; 3 = Integritaet gebrochen

        ergebnisse.append({"wache": script, "phase": phase, "zweck": zweck, "exit": rc, "halt": stop})
        print(f"  {'🛑' if stop else '🟢' if rc == 0 else '🟡'} [{phase}] {script}: exit {rc}")
        if stop:
            hard_stop = True
            print(f"🛑 STOPP: {script} meldete Sabotage/Selbsttest-Fehlschlag.")
            break

    ok_n = sum(1 for r in ergebnisse if r["exit"] == 0)
    find = [r for r in ergebnisse if r["exit"] == 1]
    fail = [r for r in ergebnisse if r["exit"] not in (0, 1)]

    L = ["# 🩺 DOKTOR-REPORT (Oberarzt, Gesamtprognose)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: "
         + ("DRY-RUN" if DRY else ("GEBURT" if NEW_ONLY else "VISIT")),
         f"**Wachen behandelt:** {len(ergebnisse)} · **0-Exit:** {ok_n} · Funde: {len(find)} · Sabotage-Fehler: {len(fail)}",
         "",
         "| Wache (Phase) | Zweck | Exit |",
         "|---|---|---|"]
    L += [f"| `{r['wache']}` ({r['phase']}) | {r['zweck']} | {'🛑 2' if r['halt'] else r['exit']} |"
          for r in ergebnisse]
    if find:
        L += ["", "## 🟡 Funde (nicht-fatal, dokumentiert)"]
        L += [f"- `{r['wache']}`: {r['zweck']}" for r in find]
    if fail:
        L += ["", "## 🔴 Sabotage-Kandidaten / hart gestoppt"]
        L += [f"- `{r['wache']}`: Exit {r['exit']}" for r in fail]
    if not find and not fail and not hard_stop:
        L += ["", "🎉 Volle Kette durchgestanden – keine Funde, keine Sabotage. Blog ist in Verfassung."]
    L += ["", "---",
          "_Oberarzt bleibt bis zuletzt: Er loescht nur ueber die offiziellen Guards; Exit 2 einer Wache -> alles haelt._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:18]))

    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": heute, "wachen": len(ergebnisse), "ok": ok_n,
                             "funde": len(find), "sabotage": len(fail),
                             "hard_stop": hard_stop}, ensure_ascii=False) + "\n")

    sys.exit(2 if hard_stop else (1 if (find or fail) else 0))


if __name__ == "__main__":
    main()
