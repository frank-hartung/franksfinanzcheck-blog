#!/usr/bin/env python3
"""
reserve_converge.py – Konvergenz-Stufe der Content-Reserve (Premium-Fix #295)

WARUM DIESE DATEI EXISTIERT (Root-Cause 15.09.2026):
  Der nächtliche Reserve-Lauf (03:25 UTC) endete jeden Tag erneut mit
  „🛑 RESERVE-ENGPAẞ: N/6 Kandidaten gate-fertig“ – obwohl Produktion,
  Veredelung und Zertifizierung technisch einwandfrei liefen. Zwei Ursachen:

  1. Der Top-up produzierte HÖCHSTENS EINEN Roh-Kandidaten pro Lauf. Der
     Vorrat wird an Publikationstagen aber mit 1–3 Artikeln verbraucht
     (`reserve_pool.publish_to_min` als Brandschutzlinie). Ein Vorrat, der
     mit 1/Nacht aufgefüllt und mit bis zu 3/Tag geleert wird, kann das Ziel
     strukturell nie halten – er pendelt unter RESERVE_TARGET und macht den
     harten End-Gate („Stock shortage must not look successful“) jede Nacht rot.

  2. Der In-Flight-Schutz in `engine_generate._reserve_topup` blockierte den
     Nachschub INNERHALB desselben Laufs: `reserve_finisher` hebt jeden
     offenen Kandidaten auf HEUTE – danach gilt jeder unzertifizierte
     Kandidat als „in flight“, also lief die frühere Stufe-4-Konvergenz
     (ein einzelner Nachschub-Block) garantiert ins Leere. Ergebnis: ein
     Tagesbedarf, der nie aufgeholt werden konnte.

  Diese Stufe schließt die Lücke mit einer BEGRENZTEN, ZIELGERICHTETEN
  Schleife, die bis zum Zielbestand nachproduziert und jede Runde neu
  zertifiziert – mit echten Abbruchkriterien statt Endlosschleife:

      Runde 1..max_runden:
        brauche := RESERVE_TARGET − zertifizierte Kandidaten
        wenn brauche == 0        → fertig (grün)
        Produktion   (engine_generate --reserve-only, force, Batch = brauche)
        Veredelung   (reserve_finisher --finish)
        Zertifizierung (reserve_readiness.py)
        wenn kein Fortschritt (weder READY noch Pool gewachsen) → aufhören

  Der Abbruch ist EHRLICH: Bleibt der Pool unter dem Ziel, exitet die Stufe
  mit 1 (der harte End-Gate `reserve_gate.py` meldet den Engpass ohnehin).
  Sie erfindet keinen Erfolg – sie stellt nur sicher, dass die Automation
  jede Nacht ihr Möglichstes getan hat, statt es gar nicht erst zu versuchen.

  ZEITBUDGET (Nachtrag 15.09.2026, Issue #295): Konvergenz ist nach oben
  doppelt begrenzt – Runden UND Wanduhr. Ohne die zweite Grenze konnte eine
  langsame Nacht (KI-Wartezeiten, Hugo-Builds je Kandidat) den 90-Minuten-Job
  überschreiten; GitHub killt dann den JOB und damit auch die Schritte
  „sichern“ und „End-Gate“ – der Lauf wäre rot UND ohne Diagnose, der
  erarbeitete Pool-Stand nicht mehr in main. Die Stufe bricht deshalb sauber
  vor dem Budget ab (`--max-minuten`, Default 45, env
  RESERVE_CONVERGE_MAX_MINUTES), meldet den Abbruchgrund `zeit-budget` und
  übergibt den nachfolgenden Schritten einen intakten Arbeitsbaum.

MODI:
  python3 scripts/reserve_converge.py                 # Workflow (Runden)
  python3 scripts/reserve_converge.py --status        # nur lesen/melden
  python3 scripts/reserve_converge.py --selftest      # Sabotage-Schutz

EXIT: 0 = Zielbestand erreicht · 1 = Engpass nach erschöpfter Konvergenz
      · 2 = Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT = ROOT / "data" / "reserve-readiness.json"
PY = sys.executable


def target() -> int:
    try:
        return int(os.environ.get("RESERVE_TARGET") or "6")
    except ValueError:
        return 6


def cert_state(cert_path: Path = CERT) -> dict:
    """Aktueller Pool-Zustand: (target, ready, pool_size).

    `ready` wird – wie im harten End-Gate – aus der Kandidatenliste gezählt,
    nie dem gespeicherten Feld vertraut (#287-Klasse: veraltete Zählung).
    """
    goal = target()
    state = {"target": goal, "ready": 0, "pool_size": 0, "exists": False}
    try:
        data = json.loads(cert_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state
    cands = list(data.get("candidates") or [])
    state["exists"] = True
    state["target"] = int(data.get("target", goal))
    state["ready"] = sum(1 for r in cands if r.get("ready") is True)
    state["pool_size"] = len(cands)
    return state


def _run(cmd: list, env_extra: dict | None = None, timeout: int = 2400) -> int:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    print(f"    $ {' '.join(cmd)}"
          + (f"   [env: {', '.join(sorted(env_extra))}]" if env_extra else ""))
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), env=env, timeout=timeout)
        return proc.returncode
    except subprocess.TimeoutExpired:
        print(f"    ⚠ Zeitüberschreitung nach {timeout}s – Runde wird beendet.")
        return 124


def converge(*, runner=_run, state_reader=cert_state, max_runden: int = 3,
             max_sekunden: int | None = None, now=time.monotonic,
             log=print) -> dict:
    """Führt die begrenzte Konvergenz aus und liefert den Abschlussbericht.

    `runner`/`state_reader`/`now` sind injizierbar (Selbsttest ohne API/Hugo).
    `max_sekunden` ist das Wanduhr-Budget: Runde 1 läuft immer (sonst täte
    die Stufe gar nichts), jede weitere nur, wenn noch Budget übrig ist.
    """
    start = now()
    verlauf = []
    for runde in range(1, max_runden + 1):
        verbraucht = now() - start
        # Zustand IMMER frisch lesen – auch der Budget-Abbruch meldet damit
        # den echten Stand (nie einen erfundenen).
        vorher = state_reader()
        if max_sekunden is not None and runde > 1 and verbraucht >= max_sekunden:
            ok = vorher["ready"] >= vorher["target"]
            log(f"  ⏱ Zeitbudget erschöpft nach {int(verbraucht)}s "
                f"(Grenze {max_sekunden}s) – keine weitere Runde. "
                f"Stand: READY {vorher['ready']}/{vorher['target']}.")
            return {"ok": ok, "runden": runde - 1, "state": vorher,
                    "verlauf": verlauf, "abbruch": "zeit-budget"}
        # Verbleibendes Budget als Deckel für JEDEN Schritt der Runde:
        # kein Einzelschritt kann mehr über das Budget hinauslaufen.
        rest = (2400 if max_sekunden is None
                else max(300, int(max_sekunden - verbraucht)))
        brauche = max(0, vorher["target"] - vorher["ready"])
        log(f"  🔄 Konvergenz-Runde {runde}/{max_runden}: "
            f"READY {vorher['ready']}/{vorher['target']} "
            f"(Pool {vorher['pool_size']} Entwürfe)")
        if brauche == 0:
            log("  ✅ Zielbestand erreicht – keine weitere Nachproduktion.")
            return {"ok": True, "runden": runde - 1, "state": vorher,
                    "verlauf": verlauf, "abbruch": "ziel-erreicht"}
        # Batch = exakter Fehlbestand (Deckel im Generator: 4) – so kostet die
        # Konvergenz nur so viele KI-Aufrufe wie wirklich fehlen.
        batch = max(1, min(brauche, 4))
        env = {"RESERVE_FORCE_TOPUP": "1", "RESERVE_TOPUP_BATCH": str(batch),
               "RESERVE_TARGET": str(vorher["target"])}
        log(f"    → {brauche} zertifizierte(r) Kandidat(en) fehlen – "
            f"Nachschub-Charge (Batch {batch}):")
        runner([PY, str(ROOT / "scripts" / "engine_generate.py"),
                "--reserve-only"], env, timeout=rest)
        runner([PY, str(ROOT / "scripts" / "reserve_finisher.py"), "--finish"],
               timeout=rest)
        # Die Zertifizierung zieht die Quarantäne nach (reserve_quarantine):
        # Ein Kandidat, der zum zweiten Mal am SELBEN Fund scheitert, verlässt
        # den Pool – die nächste Runde produziert dann Ersatz für ihn. Ohne
        # diesen Abgang bliebe der Zielbestand unerreichbar, sobald die
        # Themen-Dedup keinen Nachschub mehr hergibt (Nachtrag #295).
        runner([PY, str(ROOT / "scripts" / "reserve_readiness.py")],
               timeout=rest)
        nachher = state_reader()
        fortschritt = (nachher["ready"] > vorher["ready"]
                       or nachher["pool_size"] > vorher["pool_size"])
        verlauf.append({**nachher, "runde": runde, "vorher_ready":
                        vorher["ready"], "fortschritt": fortschritt})
        if nachher["ready"] >= nachher["target"]:
            log(f"  ✅ Zielbestand erreicht: READY {nachher['ready']}/"
                f"{nachher['target']} nach {runde} Runde(n).")
            return {"ok": True, "runden": runde, "state": nachher,
                    "verlauf": verlauf, "abbruch": "ziel-erreicht"}
        if not fortschritt:
            log("  ⏹ Kein Fortschritt möglich (keine freien Themen, KI-Ausfall "
                "oder Schutz aktiv) – Abbruch ohne weitere API-Kosten.")
            return {"ok": False, "runden": runde, "state": nachher,
                    "verlauf": verlauf, "abbruch": "kein-fortschritt"}
        log(f"    ↳ Zwischenstand: READY {nachher['ready']}/{nachher['target']}, "
            f"Pool {nachher['pool_size']} – nächste Runde.")
    after = state_reader()
    ok = after["ready"] >= after["target"]
    log(f"  {'✅' if ok else '🛑'} Nach {max_runden} Runde(n): READY "
        f"{after['ready']}/{after['target']}.")
    return {"ok": ok, "runden": max_runden, "state": after,
            "verlauf": verlauf, "abbruch": "runden-erschöpft"}


def write_summary(res: dict, summary_path: str | None) -> None:
    """Lauf-Zusammenfassung für die Redaktion (GitHub Step Summary)."""
    if not summary_path:
        return
    s = res["state"]
    lines = ["", "## 🛟 Content-Reserve – Konvergenz", "",
             f"- **READY:** {s['ready']}/{s['target']} "
             f"(Pool {s['pool_size']} Entwürfe)",
             f"- **Ergebnis:** {'Zielbestand erreicht ✅' if res['ok'] else 'Engpass ⛔'}"
             f" · Abbruch: `{res['abbruch']}`",
             f"- **Runden:** {res['runden']}"]
    for step in res["verlauf"]:
        lines.append(f"  - Runde {step['runde']}: READY "
                     f"{step['vorher_ready']} → {step['ready']} · Pool "
                     f"{step['pool_size']} · Fortschritt: "
                     f"{'ja' if step['fortschritt'] else 'nein'}")
    try:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
#  Sabotage-Schutz: die Konvergenz wird mit einem FAKE-Runner und einer
#  FAKE-Zertifikatsquelle geprüft – nie gegen API, Hugo oder das Netz.
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    fehler = []

    rufe = []

    def fake_runner(cmd, env_extra=None, timeout=0):
        # Label = Skriptname (cmd[1]); so prüfen die Fälle Reihenfolge & Env.
        label = Path(cmd[1]).name if len(cmd) > 1 else Path(cmd[0]).name
        rufe.append((label, env_extra or {}))
        return 0

    # Fall 1: Ziel bereits erreicht -> keine Produktion, keine Runden
    res = converge(runner=fake_runner,
                   state_reader=lambda: {"target": 6, "ready": 6,
                                         "pool_size": 6, "exists": True},
                   log=lambda *_: None)
    if not res["ok"] or res["runden"] != 0 or rufe:
        fehler.append(f"Fall 'Ziel erreicht' falsch: {res}, Aufrufe {rufe}")

    # Fall 2: Engpass -> Nachschub hebt den Pool in Runde 1 über das Ziel
    rufe.clear()
    zustände = iter([{"target": 6, "ready": 3, "pool_size": 5, "exists": True},
                     {"target": 6, "ready": 6, "pool_size": 8, "exists": True}])
    res = converge(runner=fake_runner, state_reader=lambda: next(zustände),
                   log=lambda *_: None)
    if not res["ok"] or res["runden"] != 1:
        fehler.append(f"Fall 'Konvergenz in Runde 1' falsch: {res}")
    namen = [c[0] for c in rufe]
    if namen != ["engine_generate.py", "reserve_finisher.py",
                 "reserve_readiness.py"]:
        fehler.append(f"Runden-Kette falsch: {namen}")
    if rufe and (rufe[0][1].get("RESERVE_FORCE_TOPUP") != "1"
                 or rufe[0][1].get("RESERVE_TOPUP_BATCH") != "3"):
        fehler.append(f"Konvergenz-Env falsch: {rufe[0][1]}")

    # Fall 3: kein Fortschritt -> sofortiger, ehrlicher Abbruch (keine
    # Endlosschleife, keine weiteren API-Aufrufe)
    rufe.clear()
    zustände = iter([{"target": 6, "ready": 2, "pool_size": 2, "exists": True},
                     {"target": 6, "ready": 2, "pool_size": 2, "exists": True},
                     {"target": 6, "ready": 2, "pool_size": 2, "exists": True}])
    res = converge(runner=fake_runner, state_reader=lambda: next(zustände),
                   log=lambda *_: None)
    if res["ok"] or res["abbruch"] != "kein-fortschritt" or len(rufe) != 3:
        fehler.append(f"Fall 'kein Fortschritt' falsch: {res}, Aufrufe {len(rufe)}")

    # Fall 4: harter Deckel – nie mehr als max_runden Runden, auch bei
    # ständigem Fortschritt ohne Zielerreichung
    rufe.clear()
    zähler = {"n": 0}

    def steigend():
        zähler["n"] += 1
        return {"target": 9, "ready": zähler["n"] - 1, "pool_size": 4,
                "exists": True}
    res = converge(runner=fake_runner, state_reader=steigend, max_runden=3,
                   log=lambda *_: None)
    if res["ok"] or res["runden"] != 3 or len(rufe) != 9:
        fehler.append(f"Runden-Deckel falsch: {res}, Aufrufe {len(rufe)}")

    # Fall 5: fehlendes/defektes Zertifikat zählt als leerer Pool (ehrlich),
    # und der Batch folgt dem Fehlbestand (nie > 4 – API-Deckel)
    leer = cert_state(Path(tempfile.gettempdir()) / "gibt-es-nicht.json")
    if leer["ready"] != 0 or leer["exists"]:
        fehler.append(f"Fehlendes Zertifikat muss leer zählen: {leer}")
    with tempfile.TemporaryDirectory() as tmp:
        cert = Path(tmp) / "reserve-readiness.json"
        cert.write_text(json.dumps({
            "target": 6, "ready": 6,  # gelogen – Liste ist maßgeblich
            "candidates": [{"slug": "a", "ready": True},
                           {"slug": "b", "ready": False}],
        }), encoding="utf-8")
        st = cert_state(cert)
        if st["ready"] != 1 or st["pool_size"] != 2:
            fehler.append(f"Zählung muss aus der Liste kommen: {st}")
        cert.write_text("{kaputt", encoding="utf-8")
        st = cert_state(cert)
        if st["ready"] != 0:
            fehler.append(f"Defektes Zertifikat muss leer zählen: {st}")

    # Fall 6: Wanduhr-Budget – Runde 1 läuft, danach wird ehrlich abgebrochen
    # (und der nachfolgende Speicher-Schritt findet einen intakten Baum vor)
    rufe.clear()
    uhr = {"t": 0.0}
    zustand = {"n": 0}

    def tick():
        uhr["t"] += 1.0
        return uhr["t"]

    def langsamer_runner(cmd, env_extra=None, timeout=0):
        rufe.append((Path(cmd[1]).name, env_extra or {}))
        uhr["t"] += 400.0  # jede Stufe kostet ~6,7 Minuten
        return 0

    def steigend_klein():
        zustand["n"] += 1
        return {"target": 6, "ready": zustand["n"],
                "pool_size": zustand["n"] + 1, "exists": True}

    res = converge(runner=langsamer_runner, state_reader=steigend_klein,
                   max_runden=3, max_sekunden=900, now=tick,
                   log=lambda *_: None)
    if res["abbruch"] != "zeit-budget" or res["runden"] != 1:
        fehler.append(f"Zeitbudget-Abbruch falsch: {res}")
    if len(rufe) != 3:
        fehler.append(f"Nach Budget-Ende darf keine Runde mehr starten: {rufe}")
    # Der Abbruch meldet den frisch gelesenen Stand (3) – keine Runde startet.
    if res["state"]["ready"] != 3:
        fehler.append(f"Budget-Abbruch muss den ehrlichen Stand melden: {res}")

    rufe.clear()
    zähler_b = {"n": -1}

    def wachsend():
        zähler_b["n"] += 1
        return {"target": 12, "ready": zähler_b["n"], "pool_size": 1,
                "exists": True}
    converge(runner=fake_runner, state_reader=wachsend, max_runden=3,
             log=lambda *_: None)
    batches = [c[1].get("RESERVE_TOPUP_BATCH") for c in rufe
               if c[0] == "engine_generate.py"]
    if batches != ["4", "4", "4"]:
        fehler.append(f"Batch-Deckel (max 4) verletzt: {batches}")

    if fehler:
        print("🛑 RESERVE-CONVERGE-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Reserve-Converge-Selbsttest grün (Ziel-Abbruch, Fortschritts-"
          "Abbruch, Runden-/Batch-/Zeitbudget-Deckel, ehrliche Zählung aus "
          "der Liste).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Konvergenz-Stufe der "
                                            "Content-Reserve")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--runden", type=int, default=3,
                    help="maximale Konvergenz-Runden (Default 3)")
    ap.add_argument("--max-minuten", type=float,
                    default=float(os.environ.get("RESERVE_CONVERGE_MAX_MINUTES")
                                  or 45),
                    help="Wanduhr-Budget der Stufe (Default 45, env "
                         "RESERVE_CONVERGE_MAX_MINUTES) – danach laufen "
                         "Sichern + End-Gate garantiert noch")
    ap.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"),
                    help="Pfad zur Lauf-Zusammenfassung")
    ap.add_argument("--cert", default=str(CERT))
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.status:
        st = cert_state(Path(args.cert))
        print(json.dumps(st, ensure_ascii=False))
        return 0 if st["ready"] >= st["target"] else 1
    budget = max(300, int(args.max_minuten * 60)) if args.max_minuten else None
    res = converge(max_runden=max(1, args.runden), max_sekunden=budget)
    write_summary(res, args.summary)
    if res["ok"]:
        return 0
    print("🛑 RESERVE-ENGPAẞ nach erschöpfter Konvergenz – der harte "
          "End-Gate (reserve_gate.py) entscheidet über den Lauf-Status. "
          "Diagnose je Kandidat: data/reserve-readiness.json (Feld `reason`).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
