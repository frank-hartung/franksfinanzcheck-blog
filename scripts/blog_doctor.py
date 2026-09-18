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
#  TRENNUNG Beweis/Visite (Folge-Reparatur 18.09.2026 aus dem
#  Qualitäts-Gate-Vorfall): `--selftest` leitete bis dahin nur auf
#  Trockenlauf um und lief die GANZE Visite mit – das ist ein Lauf,
#  kein Test: Er schrieb den Bericht und data/*.jsonl (deshalb war
#  der Doktor im Selftest-Runner als „Kettenleiter“ ausgenommen), und
#  in der dunklen Vorversion heilte ein Beweis-Aufruf sogar den
#  Live-Bestand (unit_guard/dash_guard legten 13 Artikel um, ein
#  Agent hatte nur den Selbsttest sehen wollen; danach noch einmal
#  10 Artikel + 60 gelöschte Deckbilder über den Dry-Run).
#  Deshalb gilt jetzt:
#    · `--selftest` ist ein REINER LOGIK-BEWEIS: keine Kette, kein
#      Bericht, kein data/*.jsonl, kein einziger Schreibzugriff.
#      Unsere Struktur-Garantie: main() verzweigt VOR der Visite
#      (`laeuft_kette`), nicht in ihr. Die Laufzeit-Kopie steht im
#      Selftest-Runner – jeder Selbsttest, der den Arbeitsbaum
#      anfasst, wird dort zum Befund (Vertragsregel C15), und die
#      Uhr-Probe beweist Datumsfreiheit.
#    · die Visite hat eine eigene Flagge: `--visite` (ein nackter
#      Aufruf bleibt aus Kompatibilität ebenfalls die Visite –
#      README, Engine-Kette und Gewohnheit rufen ihn so).
#
#  Aufruf (EIN Aufruf = EIN Modus):
#    python3 scripts/blog_doctor.py --visite    # Visite (alle Heilen; = nackter Aufruf)
#    python3 scripts/blog_doctor.py --dry-run   # Kette ohne Schreibung
#    python3 scripts/blog_doctor.py --new-only  # nur Geburtstage
#    python3 scripts/blog_doctor.py --selftest  # NUR Logik-Beweis (schreibt nie)
#
#  Workflow: blog-health-daily.yml (Umgebung) + Engine-Kette (new-only).
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


def beweis(argv) -> bool:
    """`--selftest` = reiner Logik-Beweis. Die Kette wird in diesem Modus
    strukturell nie erreicht – ein Beweis ist kein Eingriff, auch kein
    getarnter („nur mal eben gucken“ durfte hier schon zweimal heilen)."""
    return "--selftest" in argv


def laeuft_kette(argv) -> bool:
    """Die Kette läuft genau dann, wenn NICHT bewiesen wird.

    Bis 18.09.2026 galt hier nur „trocken“: `--selftest` lief die ganze
    Visite mit allen Seiteneffekten der Kette im Trockenlauf. Ein Beweis,
    der das System anfasst, das er misst, ist keiner – deshalb endet der
    Beweis-Pfad in main() VOR `besuch()`, nicht in ihm.
    """
    return not beweis(argv)


def trocken(argv) -> bool:
    """Trockenlauf = die Kette schreibt nichts.

    Der Selbsttest zaehlt seit 15.09.2026 dazu (Zweitverteidigung, falls je
    jemand die Modus-Trennung oberhalb bricht): main() fuehrte NACH dem
    Selbsttest die ganze Kette aus, und ein nacktes `--selftest` reichte, um
    Live-Artikel zu heilen – real passiert, als ein Agent den Selbsttest
    verlangte: unit_guard und dash_guard schrieben dabei 10 Artikel um
    (NBSP vor €, Gedankenstriche in Zahlbereichen). Wer einen Beweis
    verlangt, darf keinen Eingriff bekommen.
    """
    return "--dry-run" in argv or "--selftest" in argv


DRY = trocken(sys.argv)
NEW_ONLY = "--new-only" in sys.argv
# --visite ist die explizite Selbstbezeichnung des Standard-Modus –
# dokumentiert, damit „die Visite hat eine eigene Flagge" nicht nur eine
# Konvention bleibt. Kein eigener Zustand: visite == nackter Aufruf.

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
    # HISTORY-GUARD (09.09.): Append-Only-Beweisketten zuerst –
    # Merge-Artefakte/Marker in *_history.jsonl = Sabotage (Exit 2).
    ("history_guard.py",      [],                          "0-LOCK", "Append-Only-Historien: marker-frei, JSON-rein, chronologisch, verlustfrei (H6)"),

    # (skript, basis-args, phase, zweck)
    ("heading_guard.py",      ["--fix"],                "A-Text", "Überschriften-Hygiene H1-H3: kein <br>, Anker-stabil (27.08. hinzu)"),
    # LISTEN-GUARD (15.09.): vor den uebrigen Text-Wachen – er verschiebt
    # Zeilengrenzen (geleimte Aufzählungen), und Dash-/Unit-/Stil-Wachen
    # sollen das Ergebnis sehen, nicht den Fehler.
    ("listen_guard.py",        ["--fix"],              "A-Text", "Geleimte Listenpunkte L1, Marker-Stil je Ebene L2 (Wortbeweis)"),
    # Casing fuehrt die Textkette: es stellt Marken-/Akronym-Kanon und
    # Tagschreibung her, worauf Dash-/Compound-/Unit-Wachen aufsetzen. Der
    # --plan-Schritt heilt data/pinterest_plan.yaml (Quelle der Pin-Texte)
    # mit – sonst ueberschreibt der naechste Pin-Sync die Korrektur.
    ("casing_guard.py",       ["--fix", "--plan"],      "A-Text", "Groß-/Kleinschreibung C1–C17 + T1 (Akronyme, Marken, Tags, HeadGlue-/Komposita-Kanon, Pinterest-Plan)"),
    ("dash_guard.py",         ["--fix"],                "A-Text", "Dash-Typografie R1-R9"),
    ("unit_guard.py",         ["--fix"],                "A-Text", "Euro/Prozent/NBSP"),
    ("emoji_guard.py",        ["--fix"],                "A-Text", "Emoji-Zero-Width etc."),
    ("lektor_guard.py",       ["--fix"],                "A-Text", "Verlags-Lektorat L1-L15"),
    ("hardcases_guard.py",    ["--fix"],                "A-Text", "Deutsche Fest-Fehler H1-H9 (12.08. hinzu)"),
    ("stil_guard.py",         ["--fix"],                "A-Text", "Stil-Qualitaet S1-S8 (12.08. hinzu)"),
    ("plagiat_guard.py",      ["--fix"],                "B-Semantik", "Originalitaet P1-P5 + Fingerprint-Registry (12.08.)"),
    ("content_audit.py",      ["--fix"],                "B-Semantik", "Content-Auditor C1-C6: Duenn, Struktur, Platzhalter (12.08.)"),
    ("length_guard.py",       ["--fix"],                "B-Semantik", "Premium-Zeichenlänge Google+Pinterest (SSOT length_policy.py)"),
    ("fazit_schmiede.py",     ["--fix"],                "B-Semantik", "Fazit- & FAQ-Schmiede mit Selbstheilung"),
    ("redaktions_standard.py",["--fix"],                "B-Semantik", "Redaktions-Standard RS1-RS8 (Capital/WiWo/ZEIT, 02.09.)"),
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


def kinder_args(script: str, args: list, dry: bool, new_only: bool) -> list:
    """Argument-Bau fuer eine Wache – eigen, damit der Selbsttest ihn pruefen kann.

    DRY-RUN bedeutet: nichts schreiben. Frueher wurde nur --dry-runanhaengt, und das
    zweimal schief: (a) kennen mehrere Wachen (u. a. link_density_guard, casing_guard)
    kein --dry-run, sondern schreiben bei --fix trotzdem – der Dry-Run hat Live-Artikel
    umgeschrieben; (b) war workspace_guard vom --dry-run ausgenommen und hat im Dry-Run
    ungenutzte Deckbilder geloescht (60 Dateien). Deshalb im Dry-Run: --fix abziehen.
    """
    eff = [a for a in args if not (dry and a == "--fix")]
    return [sys.executable, str(ROOT / "scripts" / script)] + eff + (["--new-only"] if new_only else [])


def run_guard(script, args, phase, dry):
    cmd = kinder_args(script, args, dry, NEW_ONLY)
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
    # Dry-Run darf nichts schreiben: keiner Wache darf im Dry-Run --fix erreichen.
    # (Regel-Lock, weil 2026-09-14 genau dort Live-Artikel umgeschrieben und 60
    #  Deckbilder geloescht wurden – trotz --dry-run.)
    for script, args, *_ in KETTE:
        eff = kinder_args(script, args, True, False)
        if "--fix" in eff:
            fehler.append(f"  Dry-Run schreibt: {script} bekommt --fix weitergereicht!")
    if "--fix" not in kinder_args("dash_guard.py", ["--fix"], False, False):
        fehler.append("  Dry-Run-Regel kaputt: im scharfen Lauf fehlt --fix")
    # ------------------------------------------------------------
    # MODUS-TRENNUNG (Folge-Reparatur 18.09.2026): Ein Beweis-Aufruf darf
    # die Kette NIEMALS erreichen – nicht einmal trocken. Bis dahin lief
    # `--selftest` als getarnter Trockenlauf der ganzen Visite mit und
    # schrieb Bericht + data/*.jsonl; im Selftest-Runner war der Doktor
    # deshalb der einzige begründet ausgenommene „Prüfer" im Haus.
    # Die Wahrheitstabelle unten nagelt die Trennung fest; ihre
    # Laufzeit-Kopie ist die C15-Arbeitsbaum-Wache des Runners.
    # ------------------------------------------------------------
    for argv, soll_kette, soll_trocken in (
        ([], True, False),                          # nackt = Visite (Kompat)
        (["--visite"], True, False),                # Visite als eigene Flagge
        (["--new-only"], True, False),              # Geburten, scharf
        (["--dry-run"], True, True),                # Kette, aber lesend
        (["--new-only", "--dry-run"], True, True),  # Geburten lesend
        (["--selftest"], False, True),              # DER Beweis: nie die Kette
        (["--selftest", "--new-only"], False, True),
        (["--selftest", "--dry-run"], False, True),
        (["--selftest", "--visite"], False, True),  # Beweis schlägt Visite
        (["--selftest", "--fix"], False, True),     # auch nicht mit Heil-Flag
    ):
        if laeuft_kette(argv) != soll_kette:
            fehler.append(f"  Modus-Trennung kaputt: {argv!r} erreicht "
                          f"{'die Kette' if laeuft_kette(argv) else 'die Kette nicht'} – "
                          "ein Beweis darf die Kette nie erreichen, ein Aufruf ohne "
                          "--selftest muss sie erreichen")
        if trocken(argv) != soll_trocken:
            fehler.append(f"  Trockenregel unverstaendlich: {argv!r} -> trocken="
                          f"{trocken(argv)}, erwartet {soll_trocken}")
    # Historisch dokumentierte Folge-Faelle der alten Semantik (dort blieb
    # `--selftest` auf der Kette und schrieb im Trockenlauf):
    if not trocken(["--selftest"]):
        fehler.append("  Zweitverteidigung fehlt: --selftest gilt nicht als trocken")
    for script, args, *_ in KETTE:
        if "--fix" in kinder_args(script, args, trocken(["--selftest"]), False):
            fehler.append(f"  Selbsttest schreibt: {script} bekommt --fix weitergereicht!")
    return fehler


def besuch() -> None:
    """Die Visite: Selbsttest als Einlass, dann die kanonische Kette,
    Bericht (DOKTOR-REPORT.md) und Historie (data/doctor_history.jsonl).
    Wird ausschließlich von main() erreicht – und dort nur, wenn NICHT
    bewiesen wird (`laeuft_kette`)."""
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


def main() -> None:
    # WEICHE VOR DER VISITE: Ein Beweis-Aufruf betritt die Visite nie.
    # (18.09.2026: bis dahin war `--selftest` nur ein Trockenlauf-Schalter
    #  und lief die ganze Kette mit – ein Lauf, kein Test.)
    if not laeuft_kette(sys.argv):
        stf = selftest()
        if stf:
            print("🛑 DOKTOR-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
            print("   (Reiner Beweis: die Kette wurde nicht betreten, nichts geschrieben.)")
            print("\n".join(stf))
            sys.exit(2)
        print(f"✅ Doktor-Selbsttest: {len(SELFTEST)} Faelle gruen, Kette {len(KETTE)} Wachen "
              "– reiner Beweis, kein Eingriff, kein Schreibzugriff.")
        return

    stf = selftest()
    if stf:
        print("🛑 DOKTOR-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Keine Visite geschrieben/stattgegeben. Bitte blog_doctor.py pruefen:")
        print("\n".join(stf))
        sys.exit(2)
    print(f"✅ Doktor-Selbsttest: {len(SELFTEST)} Faelle gruen, Kette {len(KETTE)} Wachen.")
    besuch()


if __name__ == "__main__":
    main()
