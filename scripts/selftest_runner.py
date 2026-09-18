#!/usr/bin/env python3
"""selftest_runner.py – alle Selbsttests laufen lassen: vollständig, registriert, uhrfest.

WARUM (18.09.2026 – Qualitäts-Gate rot auf main, Run 35312783057, Commit 83526d5)
-------------------------------------------------------------------------------
Zwei Befunde, dieselbe Wurzel: eine handgeschriebene Liste, die niemand prüft.

1) Das Gate führte die Selbsttests über eine in Bash ABGETIPPTE Liste. Die Kopie
   war still veraltet: fünf Wachen, die das Regelwerk
   (`governance_contract.GUARDS`) verlangt – readability_check, pinterest_auth,
   social_studio, alert_router, affiliate_integrity_gate – liefen im Gate nicht
   mehr mit. Der Kommentar über der Liste warnte ausdrücklich vor genau diesem
   Fall („eine Wache, die nicht läuft, weil sie im Loop vergessen wurde, ist der
   teurere Fehler"); die Liste widersprach ihm, und niemand hätte es gemerkt.

2) `draft_triage.py --selftest` war an einem Tag grün und sechs Tage später rot,
   ohne dass sich am Code etwas geändert hätte: Fixtures von der echten Wanduhr,
   Erwartung aus einem eingefrorenen Testdatum. Derselbe Selbsttest verbrannte
   danach 7½ Minuten im Content-Reserve-Lauf (Stufe 5, Issue #310). Eine zweite
   Bombe derselben Klasse (`audio_coverage_check.py`) lag bereits scharf im Repo
   und wäre am 24.12.2026 hochgegangen – jeden Tag, in jedem Lauf.

Dieser Runner ersetzt beides durch Nachweis:

  ENTDECKEN   jedes `scripts/*.py` mit echtem `--selftest` läuft – abtippen
              entfällt. Die Kennung muss in Anführungszeichen stehen, also dort,
              wo das Argument wirklich ausgewertet wird: Ein Skript, das die
              Flagge nur im Kommentar erwähnt, würde sonst seine Standard-Aktion
              ausführen (am 18.09.2026 real passiert – `publish_gate.py` stufte
              einen LIVE-Artikel auf `draft: true` herab).
  SSOT        jedes Mitglied von `governance_contract.GUARDS` muss entdeckt
              werden; verliert eine Wache ihren Selbsttest, ist das ein Befund.
  AUSNAHMEN   brauchen einen hinterlegten Grund und altern nicht still (Eintrag
              für ein geheiltes oder entferntes Skript wird selbst zum Befund).
  UHR-PROBE   jeder Selbsttest läuft zusätzlich unter einer um 97 und um 1461
              Tage VORGESTELLTEN Uhr (`scripts/selftest_clock.trap`). Eine
              Datums-Abhängigkeit kippt damit am Tag des Einbaus und nicht an
              einem Feiertag drei Monate später.
  C15         ändert sich der Arbeitsbaum während des Laufs, ist das ein Befund:
              ein Prüf-Aufruf heilt nicht (Vertragsregel C15).
  ZEITDECKEL  eine hängende Wache kostet ihr Budget und wird gemeldet – sie
              frisst nicht das Zeitlimit des ganzen Jobs.

Nutzung:
    python3 scripts/selftest_runner.py                 # Basis + Uhr-Proben
    python3 scripts/selftest_runner.py --ohne-uhr-probe # nur Basis (schnell)
    python3 scripts/selftest_runner.py --md            # Markdown für Step-Summary
    python3 scripts/selftest_runner.py --json
    python3 scripts/selftest_runner.py --selftest

Exit: 0 = alles grün · 1 = Befund · 2 = Runner-Fehler
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKRIPT_DIR = os.path.join(BLOG_DIR, "scripts")
UHR_PROBE_TAGE = (97, 1461)     # ~3 Monate und ~4 Jahre – beide nur vorwärts
# Zeitdeckel je Selbsttest. Die langsamste Wache braucht heute 8,5 s
# (ff_voice_audio.py); 240 s sind also reichlich. Der Deckel ist trotzdem
# Pflicht: Eine hängende Wache fräße sonst das 20-Minuten-Budget des Gates, und
# ein Timeout wird als Befund gemeldet – nicht als Grün.
ZEITDECKEL = 240

# Ausnahmen brauchen einen Grund. Der Runner prüft, dass der Grund nicht leer ist
# und dass die Ausnahme tatsächlich existiert – eine Ausnahme für ein Skript, das
# es nicht mehr gibt, ist eine stille Lücke.
AUSNAHMEN = {
    "blog_doctor.py":
        "Kettenleiter: sein `--selftest` läuft die ganze Visite (24 Wachen im "
        "Trockenlauf) und schreibt data/*.jsonl – das ist ein Lauf, kein "
        "Selbsttest. Heimat: blog-health-daily.yml / content-engine-v2.yml.",
    "selftest_runner.py":
        "Dieser Runner: sein Selbsttest baut eigene Probe-Skripte und würde sich "
        "hier selbst aufrufen (Rekursion). Läuft als eigener Schritt im Gate.",
}


# Entdeckungs-Kennung: das Argument QUOTIERT, also dort, wo es ein
# `add_argument("--selftest", …)` oder ein `"--selftest" in sys.argv` wirklich
# auswertet.
KENNUNG = re.compile(r"""["\']--selftest["\']""")


# Skripte, die `--selftest` erwähnen, ohne es zu implementieren: ein Aufruf mit
# der Flagge startet ihre Standard-Aktion. Der Runner führt sie NICHT, meldet sie
# aber als Hinweis – und der Hinweis altert nicht still: Implementiert eines der
# Skripte die Flagge doch (oder fällt es weg), wird der Listeneintrag zum Befund.
GEFAHREN = {
    "publish_gate.py":
        "erwähnt --selftest in einer Diagnose-Zeile, implementiert es nicht: ein "
        "Aufruf läuft als scharfer Publish-Gate und stuft bei Befunden LIVE-"
        "Artikel auf draft herab (am 18.09.2026 real ausgelöst).",
    "affiliate_marketer.py":
        "erwähnt --selftest in einem Kommentar zum Write-Guard, implementiert es "
        "nicht: ein Aufruf läuft als Report über alle Artikel.",
}


def entdecken(skript_dir: str = SKRIPT_DIR) -> tuple:
    """(echte Selbsttests, Erwähnungen ohne Implementierung) – aus dem Dateibaum.

    Die KENNUNG verlangt das Argument in ANFÜHRUNGSZEICHEN, also dort, wo es ein
    `add_argument("--selftest", …)` oder ein `"--selftest" in sys.argv` wirklich
    auswertet. Eine bloße Erwähnung im Kommentar genügt nicht: Wer sie laufen
    lässt, startet die Standard-Aktion des Skripts. Genau das hätte am
    18.09.2026 fast einen Live-Artikel gekostet (publish_gate.py).
    """
    echt, erwähnt = [], []
    for pfad in sorted(glob.glob(os.path.join(skript_dir, "*.py"))):
        try:
            with open(pfad, encoding="utf-8", errors="ignore") as fh:
                quelltext = fh.read()
        except OSError:
            continue
        if KENNUNG.search(quelltext):
            echt.append(pfad)
        elif "--selftest" in quelltext:
            erwähnt.append(pfad)
    return echt, erwähnt


def arbeitsbaum(root: str = BLOG_DIR):
    """`git status --porcelain` als Menge, oder None wenn Git nicht antwortet.

    None heißt: Die C15-Wache kann hier nicht beweisen – und das wird gemeldet,
    statt die Prüfung still auszuschalten.
    """
    try:
        r = subprocess.run(("git", "-C", root, "status", "--porcelain"),
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return {z.strip() for z in r.stdout.splitlines() if z.strip()}


def regelwerk(skript_dir: str = SKRIPT_DIR) -> list:
    """`governance_contract.GUARDS` – die Mindestmenge des Vertrags (SSOT).

    Der Import-Cache wird bewusst geleert: Wer einen anderen Skript-Ordner
    übergibt (der Selbsttest tut das mit einem Stub), muss auch dessen Regelwerk
    lesen und nicht das zuletzt importierte.
    """
    if skript_dir not in sys.path:
        sys.path.insert(0, skript_dir)
    sys.modules.pop("governance_contract", None)
    from governance_contract import GUARDS  # type: ignore
    return list(GUARDS)


def _laufen(befehl: list, deckel: int) -> tuple:
    """(Exit-Code, letzte Zeilen) – Timeout gilt als Befund, nicht als Grün."""
    start = time.time()
    try:
        r = subprocess.run(befehl, cwd=BLOG_DIR, capture_output=True, text=True,
                           timeout=deckel)
        text = (r.stdout or "") + (r.stderr or "")
        return r.returncode, [z for z in text.strip().splitlines() if z.strip()][-6:], \
            round(time.time() - start, 1)
    except subprocess.TimeoutExpired:
        return 124, [f"Zeitdeckel {deckel}s überschritten"], round(time.time() - start, 1)
    except OSError as exc:
        return 126, [f"nicht ausführbar: {exc.__class__.__name__}"], 0.0


def pruefen(python: str = "python3", uhr_probe: bool = True,
            skript_dir: str = SKRIPT_DIR, deckel: int = ZEITDECKEL,
            baum_wurzel: str = BLOG_DIR) -> dict:
    """Basis-Lauf + Uhr-Proben über alle entdeckten Selbsttests."""
    befunde: list = []
    hinweise: list = []
    vorher = arbeitsbaum(baum_wurzel)
    if vorher is None:
        hinweise.append(f"C15-Wache (Arbeitsbaum unverändert) ist ohne Git in "
                        f"{baum_wurzel} nicht beweisbar – Selbsttests könnten "
                        "unbemerkt schreiben.")
        vorher = set()
    wachen, erwaehnt = entdecken(skript_dir)
    for pfad in erwaehnt:
        datei = os.path.basename(pfad)
        if datei not in GEFAHREN:
            hinweise.append(f"scripts/{datei} erwähnt `--selftest`, implementiert es "
                            "aber nicht (Quote fehlt) – der Runner führt es NICHT. "
                            "Ein Aufruf mit der Flagge startet die Standard-Aktion.")
    for datei, grund in GEFAHREN.items():
        if not grund.strip():
            befunde.append(f"Gefahren-Eintrag {datei} ohne Begründung")
        pfad = os.path.join(skript_dir, datei)
        if not os.path.isfile(pfad):
            befunde.append(f"Gefahren-Eintrag für scripts/{datei}, die es nicht gibt – "
                           "Liste ist veraltet (stille Lücke)")
            continue
        with open(pfad, encoding="utf-8", errors="ignore") as fh:
            if KENNUNG.search(fh.read()):
                befunde.append(f"scripts/{datei} implementiert `--selftest` inzwischen – "
                               "der Gefahren-Eintrag ist veraltet und die Wache gehört "
                               "in den Lauf")
    if not wachen:
        befunde.append(f"Kein einziger Selbsttest in {skript_dir} entdeckt – "
                        "die Entdeckung ist kaputt (ein leeres Gate ist kein grünes Gate).")
    try:
        guards = regelwerk(skript_dir)
    except Exception as exc:  # noqa: BLE001
        guards, befunde = [], befunde + [
            f"Regelwerk nicht lesbar ({exc.__class__.__name__}: {exc}) – "
            "der SSOT-Abgleich fällt aus, das darf nicht still passieren."]
    namen = {os.path.basename(p) for p in wachen}
    for g in guards:
        datei = g if g.endswith(".py") else f"{g}.py"
        if datei in AUSNAHMEN:
            continue
        if datei not in namen:
            befunde.append(f"Regelwerk verlangt scripts/{datei} mit `--selftest` – "
                            "im Dateibaum ist sie nicht (entweder fehlt die Wache "
                            "oder ihr Selbsttest).")
    for grund, datei in ((v, k) for k, v in AUSNAHMEN.items()):
        if not grund.strip():
            befunde.append(f"Ausnahme {datei} ohne Begründung")
    for datei in AUSNAHMEN:
        if not os.path.isfile(os.path.join(skript_dir, datei)):
            befunde.append(f"Ausnahme für scripts/{datei}, die es nicht gibt – "
                            "stille Lücke in der Liste")

    laeufe, sonden = [], []
    clock = os.path.join(skript_dir, "selftest_clock.py")
    for pfad in wachen:
        datei = os.path.basename(pfad)
        if datei in AUSNAHMEN:
            continue
        code, tail, sek = _laufen([python, pfad, "--selftest"], deckel)
        laeufe.append({"wache": datei, "exit": code, "sekunden": sek, "tail": tail})
        if code != 0:
            befunde.append(f"scripts/{datei} --selftest Exit {code}: "
                            f"{tail[-1][:170] if tail else 'keine Ausgabe'}")
        if not uhr_probe:
            continue
        if not os.path.isfile(clock):
            befunde.append("scripts/selftest_clock.py fehlt – die Uhr-Probe kann "
                            "nicht laufen (Datums-Abhängigkeiten blieben unsichtbar).")
            break
        for tage in UHR_PROBE_TAGE:
            code2, tail2, sek2 = _laufen(
                [python, clock, "--trap", pfad, "--offset", str(tage)], deckel)
            sonden.append({"wache": datei, "offset": tage, "exit": code2,
                           "sekunden": sek2})
            if code2 != 0:
                befunde.append(
                    f"scripts/{datei} --selftest ist DATUMSABHÄNGIG (Uhr um {tage} "
                    f"Tage vorgestellt, Exit {code2}): "
                    f"{tail2[-1][:150] if tail2 else 'keine Ausgabe'} – "
                    "Fixtures müssen relativ zum Testdatum gebaut und absolut "
                    "gestempelt werden (scripts/selftest_clock.py).")
    nachher = arbeitsbaum(baum_wurzel)
    if nachher is None:
        nachher = set()
    for zeile in sorted(nachher - vorher):
        befunde.append(f"Selbsttest hat in den Arbeitsbaum geschrieben (C15: ein "
                       f"Prüf-Aufruf heilt nicht): {zeile}")

    return {"wachen": len(wachen),
            "hinweise": hinweise,
            "gelaufen": len(laeufe),
            "ausnahmen": sorted(AUSNAHMEN),
            "uhr_proben": len(sonden),
            "laufzeit_s": round(sum(l["sekunden"] for l in laeufe)
                                + sum(s["sekunden"] for s in sonden), 1),
            "laeufe": laeufe, "sonden": sonden, "befunde": befunde}


def als_md(erg: dict, stand=None) -> str:
    import datetime
    stand = (stand or datetime.date.today()).isoformat()
    aus = ["## 🧪 Selbsttest-Runner – Vollständigkeit und Uhr-Festigkeit",
           f"Stand {stand} · {erg['gelaufen']} Wachen entdeckt und gelaufen · "
           f"{erg['uhr_proben']} Uhr-Proben ({', '.join(f'+{t} d' for t in UHR_PROBE_TAGE)}) · "
           f"{erg['laufzeit_s']} s",
           "",
           f"Ausnahmen mit Grund: {len(erg['ausnahmen'])} "
           f"({', '.join(f'`{a}`' for a in erg['ausnahmen']) or 'keine'})", ""]
    if erg["befunde"]:
        aus += ["### 🔴 Befunde", ""]
        aus += [f"- {b}" for b in erg["befunde"]]
    else:
        aus += ["✅ Keine Befunde: jeder entdeckte Selbsttest ist grün, bleibt es "
                "unter einer vorgestellten Uhr, und keiner schreibt in den "
                "Arbeitsbaum (C15).", ""]
    if erg.get("hinweise"):
        aus += ["", "### ⚠️ Hinweise ohne Sperrwirkung", ""]
        aus += [f"- {h}" for h in erg["hinweise"]]
    return "\n".join(aus) + "\n"


# ---------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    """Baut einen Mini-Repo-Baum mit bekannten Fällen und prüft den Runner daran.

    Die Uhr-Probe läuft gegen das ECHTE `selftest_clock.py` (kopiert, nicht
    nachgebaut): Eine Probe, die sich ihr Werkzeug selbst erfindet, beweist nur
    sich selbst. Dasselbe gilt für die C15-Wache – sie wird an einem Stub
    bewiesen, der wirklich in einen Git-Baum schreibt.
    """
    import datetime as dt
    import shutil
    import tempfile
    fehler: list[str] = []
    tmp = tempfile.mkdtemp(prefix="selftest-runner-")
    alt_ausnahmen, alt_gefahren = dict(AUSNAHMEN), dict(GEFAHREN)
    try:
        skripte = os.path.join(tmp, "scripts")
        os.makedirs(skripte, exist_ok=True)

        def bauen(name: str, inhalt: str) -> None:
            # Die Entdeckungs-Kennung muss QUOTIERT sein – genau das ist der Punkt
            with open(os.path.join(skripte, name), "w", encoding="utf-8") as fh:
                fh.write(f'MARKER = "--selftest"  # Entdeckungs-Kennung\n{inhalt}')

        bauen("gut.py", "import sys\nprint('gruen')\nsys.exit(0)\n")
        bauen("kaputt.py", "import sys\nprint('rot')\nsys.exit(1)\n")
        # Datumsbombe: heute grün, unter vorgestellter Uhr rot (draft_triage-Fall)
        bauen("bombe.py",
              "import datetime, os, sys\n"
              "grenze = datetime.date.fromisoformat(os.environ['RUNNER_BOMB_GRENZE'])\n"
              "sys.exit(0 if grenze > datetime.date.today() else 1)\n")
        bauen("kettenleiter.py", "import sys\nsys.exit(0)\n")
        # Heiler: grün, schreibt aber in den Arbeitsbaum (C15-Fall)
        bauen("schreiber.py",
              "import os, sys\n"
              "with open(os.path.join(os.environ['RUNNER_BAUM'],\n"
              "                       'heiler-rest.md'), 'w') as fh:\n"
              "    fh.write('x')\nsys.exit(0)\n")
        # Ohne Kennung: darf gar nicht erst geprüft werden
        with open(os.path.join(skripte, "ohne_selbsttest.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("print('nichts zu prüfen')\n")
        # Erwähnung ohne Implementierung: Hinweis, kein Lauf (publish_gate-Fall)
        with open(os.path.join(skripte, "erwaehnung.py"), "w", encoding="utf-8") as fh:
            fh.write("# Diagnose: python3 scripts/x.py --selftest\n"
                     "import sys\nsys.exit(0)\n")
        # SSOT-Stub: verlangt eine vorhandene, eine fehlende und eine ausgenommene Wache
        with open(os.path.join(skripte, "governance_contract.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("GUARDS = ['gut.py', 'gibt_es_nicht.py', 'kettenleiter.py']\n")
        shutil.copy(os.path.join(SKRIPT_DIR, "selftest_clock.py"),
                    os.path.join(skripte, "selftest_clock.py"))
        subprocess.run(("git", "-C", tmp, "init", "-q", "."),
                       capture_output=True, text=True, timeout=60)

        os.environ["RUNNER_BOMB_GRENZE"] = (dt.date.today()
                                            + dt.timedelta(days=2)).isoformat()
        os.environ["RUNNER_BAUM"] = tmp
        globals()["AUSNAHMEN"] = {"kettenleiter.py": "Begründeter Kettenleiter"}
        globals()["GEFAHREN"] = {}
        erg = pruefen(python=sys.executable, uhr_probe=True, skript_dir=skripte,
                      deckel=180, baum_wurzel=tmp)
        texte, hinweise = " ".join(erg["befunde"]), " ".join(erg["hinweise"])
        if erg["wachen"] != 6:
            fehler.append(f"Entdeckung zählt {erg['wachen']} statt 6 (gut, kaputt, "
                          "bombe, kettenleiter, schreiber, selftest_clock)")
        if erg["gelaufen"] != 5:
            fehler.append(f"Gelaufen {erg['gelaufen']} statt 5 "
                          "(die begründete Ausnahme muss übersprungen werden)")
        if "kaputt.py --selftest Exit 1" not in texte:
            fehler.append("roter Selbsttest wird nicht gemeldet")
        if "DATUMSABHÄNGIG" not in texte or "bombe.py" not in texte:
            fehler.append("Datumsbombe wird von der Uhr-Probe nicht gefangen")
        if "gibt_es_nicht.py" not in texte:
            fehler.append("SSOT-Abgleich vermisst eine Regelwerk-Wache nicht")
        if "ohne_selbsttest" in texte + hinweise:
            fehler.append("Skript ohne --selftest wird fälschlich geprüft")
        if "erwaehnung.py" not in hinweise:
            fehler.append("Erwähnung ohne Implementierung bleibt ohne Hinweis")
        if "heiler-rest.md" not in texte or "C15" not in texte:
            fehler.append("C15-Wache sieht den schreibenden Selbsttest nicht")
        if erg["uhr_proben"] != 5 * len(UHR_PROBE_TAGE):
            fehler.append(f"Uhr-Proben {erg['uhr_proben']} statt "
                          f"{5 * len(UHR_PROBE_TAGE)}")

        # Ausnahmen und Gefahren-Liste dürfen nicht still altern
        globals()["AUSNAHMEN"] = {"kettenleiter.py": "   "}
        if not any("ohne Begründung" in b for b in
                   pruefen(python=sys.executable, uhr_probe=False,
                           skript_dir=skripte, deckel=180,
                           baum_wurzel=tmp)["befunde"]):
            fehler.append("Ausnahme ohne Begründung bleibt still")
        globals()["AUSNAHMEN"] = {"gibt_es_nicht.py": "existiert gar nicht"}
        if not any("die es nicht gibt" in b for b in
                   pruefen(python=sys.executable, uhr_probe=False,
                           skript_dir=skripte, deckel=180,
                           baum_wurzel=tmp)["befunde"]):
            fehler.append("Ausnahme für ein fehlendes Skript bleibt still")
        globals()["AUSNAHMEN"] = {}
        globals()["GEFAHREN"] = {"erwaehnung.py": "bekannt und begründet"}
        erg5 = pruefen(python=sys.executable, uhr_probe=False, skript_dir=skripte,
                       deckel=180, baum_wurzel=tmp)
        if any("erwaehnung.py" in h for h in erg5["hinweise"]):
            fehler.append("begründeter Gefahren-Eintrag warnt trotzdem doppelt")
        globals()["GEFAHREN"] = {"gut.py": "hat inzwischen einen echten Selbsttest"}
        if not any("inzwischen" in b for b in
                   pruefen(python=sys.executable, uhr_probe=False,
                           skript_dir=skripte, deckel=180,
                           baum_wurzel=tmp)["befunde"]):
            fehler.append("Gefahren-Eintrag für ein geheiltes Skript bleibt still")
        globals()["GEFAHREN"] = {"gibt_es_nicht.py": "weg"}
        if not any("Gefahren-Eintrag" in b for b in
                   pruefen(python=sys.executable, uhr_probe=False,
                           skript_dir=skripte, deckel=180,
                           baum_wurzel=tmp)["befunde"]):
            fehler.append("Gefahren-Eintrag für ein fehlendes Skript bleibt still")

        # Leerer Baum: ein leeres Gate ist kein grünes Gate
        leer = os.path.join(tmp, "leer")
        os.makedirs(leer, exist_ok=True)
        with open(os.path.join(leer, "governance_contract.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("GUARDS = []\n")
        globals()["GEFAHREN"] = {}
        if not any("Kein einziger Selbsttest" in b for b in
                   pruefen(python=sys.executable, uhr_probe=False, skript_dir=leer,
                           deckel=60, baum_wurzel=tmp)["befunde"]):
            fehler.append("leerer Dateibaum läuft als grün durch")

        # Markdown muss Befund, Hinweis UND Grün können – mit gegebenem Datum
        if "🔴 Befunde" not in als_md(erg, stand=dt.date(2026, 9, 18)):
            fehler.append("Markdown verschluckt die Befunde")
        if "Hinweise ohne Sperrwirkung" not in als_md(erg, stand=dt.date(2026, 9, 18)):
            fehler.append("Markdown verschluckt die Hinweise")
        if "Stand 2026-09-18" not in als_md(erg, stand=dt.date(2026, 9, 18)):
            fehler.append("Markdown datiert sich selbst statt über `stand`")
        if "Keine Befunde" not in als_md(dict(erg, befunde=[], hinweise=[]),
                                         stand=dt.date(2026, 9, 18)):
            fehler.append("Markdown meldet den grünen Fall nicht")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        globals()["AUSNAHMEN"] = alt_ausnahmen
        globals()["GEFAHREN"] = alt_gefahren
        os.environ.pop("RUNNER_BOMB_GRENZE", None)
        os.environ.pop("RUNNER_BAUM", None)
        sys.modules.pop("governance_contract", None)
        shutil.rmtree(tmp, ignore_errors=True)
    if fehler:
        print("🛑 selftest_runner-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print("✅ Runner-Selbsttest grün: Entdeckung (nur echte Kennung), SSOT-Abgleich, "
          "Ausnahmen- und Gefahren-Pflicht, rote Wache, Datumsbombe, C15-Wache, "
          "leerer Baum, Markdown.")
    return 0


def _annotation(text: str) -> str:
    """Escaping nach GitHub-Doku: nur %, CR und LF im Meldungstext.

    Doppelpunkt und Komma müssen ausschließlich in den `file=`/`line=`-
    Eigenschaften escaped werden – in der Meldung selbst würden sie den Text
    unlesbar machen, ohne dass GitHub etwas davon hätte.
    """
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    ap = argparse.ArgumentParser(description="Alle Selbsttests: vollständig, uhrfest")
    ap.add_argument("--python", default=sys.executable or "python3")
    ap.add_argument("--ohne-uhr-probe", action="store_true",
                    help="nur Basis-Lauf (schnell, aber ohne Datums-Nachweis)")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    try:
        erg = pruefen(python=args.python, uhr_probe=not args.ohne_uhr_probe)
    except Exception as exc:  # noqa: BLE001
        print(f"🛑 Runner-Fehler: {exc.__class__.__name__}: {exc}")
        return 2
    # Ein Lauf, zwei Kanäle: In GitHub Actions schreibt der Runner seine Tabelle
    # selbst in die Lauf-Zusammenfassung. Ein zweiter Aufruf nur für das Markdown
    # würde die ganze Flotte noch einmal laufen lassen.
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and not (args.md or args.json):
        try:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(als_md(erg))
        except OSError:
            pass
    if args.json:
        print(json.dumps(erg, ensure_ascii=False, indent=2))
    elif args.md:
        print(als_md(erg))
    else:
        print(f"SELBSTTEST-RUNNER · {erg['gelaufen']} Wachen gelaufen · "
              f"{erg['uhr_proben']} Uhr-Proben · {erg['laufzeit_s']} s · "
              f"Ausnahmen: {', '.join(erg['ausnahmen']) or 'keine'}")
        github = bool(os.environ.get("GITHUB_ACTIONS"))
        for b in erg["befunde"]:
            print(f"  ❌ {b}")
            if github:
                print(f"::error::{_annotation(b)}")
        for h in erg.get("hinweise", []):
            print(f"  ⚠ {h}")
            if github:
                print(f"::warning::{_annotation(h)}")
        if not erg["befunde"]:
            print("  ✅ Jeder Selbsttest grün – und unter einer um "
                  f"{', '.join(f'+{t}' for t in UHR_PROBE_TAGE)} Tage vorgestellten "
                  "Uhr ebenfalls.")
    return 1 if erg["befunde"] else 0


if __name__ == "__main__":
    sys.exit(main())
