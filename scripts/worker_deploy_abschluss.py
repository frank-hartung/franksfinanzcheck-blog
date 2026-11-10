#!/usr/bin/env python3
# ============================================================
#  DEPLOY-ABSCHLUSS – „Grün“ nur mit ausgeführter Auslieferung
#  ------------------------------------------------------------
#  WARUM (WF-829B / #922, 10.11.2026)
#  ------------------------------------------------------------
#  Vorfall vom 24.10.2026 (Run 40100342025): Ein Deploy wurde übersprungen
#  und der Lauf meldete trotzdem grün. Die Antwort darauf war ein
#  Stellvertreter-Gate: `worker_environment_guard.py --check` liest die
#  Schutzregeln des GitHub-Environments und bricht den Lauf rot ab, solange
#  sie fehlen. Richtig – aber diese Regeln kann das Repository nicht selbst
#  setzen (live gemessen: PUT → 403, `administration=write` fehlt;
#  `can_admins_bypass` hat in REST und GraphQL keinen Schreibweg).
#
#  Die Folge war ein strukturell unmöglicher Lauf: Jeder `push` nach `main`
#  auf einen Worker-Pfad löste EINEN Produktions-Deploy aus, der vor dem
#  Secret-Zugriff garantiert rot wurde. Acht rote Läufe seit dem 27.10.,
#  bei jedem wurde #922 nachgeführt. Und der „Selbstheilungs"-Lauf war
#  fünfmal grün, ohne je eine Zeile am Environment zu ändern.
#
#  ZWEI VERTRÄGE, die dieses Skript erzwingt:
#    V1  Eine Auslieferung ist ein WILLENSakt: `workflow_dispatch` auf
#        `refs/heads/main`. Auf `push`/`pull_request` läuft ausschließlich
#        der geheimnisfreie Testjob; JEDER dort ausgeführte Deploy-Job ist
#        ein harter Befund, kein „nicht nötig".
#    V2  Ein geplanter Deploy darf nie still ausbleiben: Plan, Produktions-
#        Gate und Deploy müssen `success` sein. `skipped`, `failure` und
#        `cancelled` sind rot – mit dem Job beim Namen genannt.
#
#  Das Skript liest nur `needs.*.result` und `github`-Werte aus der
#  Umgebung (jeder Wert kommt über `env:` aus dem Workflow, nie direkt aus
#  `${{ github.event.* }}` im `run:`-Block). Kein Netz, keine Secrets,
#  keine Schreibrechte, keine Wanduhr.
#
#  AUFRUF
#    python3 scripts/worker_deploy_abschluss.py --selftest
#    python3 scripts/worker_deploy_abschluss.py --pruefen [--md PFAD] [--json]
#
#  EXIT  0 = Beweis erbracht · 1 = blockiert/übersprungen (rot) ·
#        2 = Werkzeugfehler: Eingabe nicht belegbar (rot, nie grün)
# ============================================================
"""Verhaltensbeweis für den Worker-Deploy: kein Grün ohne ausgeführten Deploy."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Mapping, Sequence

from github_kommando import annotation

EREIGNIS_DEPLOY = "workflow_dispatch"
EREIGNISSE_TESTS = frozenset({"push", "pull_request"})
EREIGNISSE = EREIGNISSE_TESTS | {EREIGNIS_DEPLOY}
ERGEBNISSE = frozenset({"success", "failure", "cancelled", "skipped"})
GRUEN = "success"
AUSGESETZT = "skipped"
HAUPTZWEIG = "refs/heads/main"

CODE_GRUEN = 0
CODE_ROT = 1
CODE_WERKZEUG = 2

UMGEBUNG_FELDER = {
    "plan": "ERGEBNIS_PLAN",
    "tests": "ERGEBNIS_TESTS",
    "production-policy": "ERGEBNIS_POLICY",
    "deploy": "ERGEBNIS_DEPLOY",
}


class WerkzeugFehler(RuntimeError):
    """Die Lage ist nicht belegbar – ohne Beweis kein Grün."""

    exit_code = CODE_WERKZEUG


def _wert(umgebung: Mapping[str, str], feld: str) -> str:
    wert = str(umgebung.get(feld, "")).strip()
    if wert not in ERGEBNISSE:
        raise WerkzeugFehler(f"{feld} fehlt oder ist kein Job-Ergebnis.")
    return wert


def _geplant(roh: str, *, ereignis: str) -> list[str]:
    """Die Plan-Ausgabe ist eine JSON-Liste – auch `[]` ist eine Aussage."""
    # Ein übersprungener Plan-Job hat keine Ausgabe: auf Push/PR ist das die
    # erwartete, belegbare Aussage „kein Deploy geplant", kein Werkzeugfehler.
    roh = roh or "[]"
    try:
        daten = json.loads(roh)
    except (ValueError, TypeError) as exc:
        raise WerkzeugFehler("GEPLANT ist kein gültiges JSON.") from exc
    if not isinstance(daten, list) or any(not isinstance(e, str) for e in daten):
        raise WerkzeugFehler("GEPLANT ist keine Liste von Worker-Namen.")
    if ereignis == EREIGNIS_DEPLOY and not daten:
        raise WerkzeugFehler("Ein ausgelöster Deploy hat keinen geplanten Worker.")
    return daten


def entscheiden(umgebung: Mapping[str, str]) -> dict:
    """Ein Urteil aus der Lage DIESES Laufs. Reine Funktion, kein Netz."""
    ereignis = str(umgebung.get("EREIGNIS", "")).strip()
    if ereignis not in EREIGNISSE:
        raise WerkzeugFehler(f"Unbekanntes Ereignis: {ereignis or 'leer'}.")
    ref = str(umgebung.get("REF", "")).strip()
    if not ref:
        raise WerkzeugFehler("REF fehlt; der Zweig ist nicht belegbar.")
    ergebnisse = {job: _wert(umgebung, feld) for job, feld in UMGEBUNG_FELDER.items()}
    geplant = _geplant(str(umgebung.get("GEPLANT", "")).strip(), ereignis=ereignis)

    befunde: list[str] = []
    if ereignis == EREIGNIS_DEPLOY:
        if ref != HAUPTZWEIG:
            befunde.append(f"Deploy lief auf {ref}, erlaubt ist nur {HAUPTZWEIG}.")
        for job in ("plan", "production-policy", "deploy"):
            if ergebnisse[job] != GRUEN:
                befunde.append(f"Job `{job}` ist `{ergebnisse[job]}`, nicht `{GRUEN}`.")
        if ergebnisse["tests"] != AUSGESETZT:
            befunde.append(f"Testjob lief im Deploy-Lauf ({ergebnisse['tests']}).")
        titel = "Deploy-Beweis" if not befunde else "Deploy-Beweis fehlgeschlagen"
        einsatz = f"Auslieferung von {', '.join(geplant)}"
    else:
        if ergebnisse["tests"] != GRUEN:
            befunde.append(f"Testjob ist `{ergebnisse['tests']}`, nicht `{GRUEN}`.")
        for job in ("plan", "production-policy", "deploy"):
            if ergebnisse[job] != AUSGESETZT:
                befunde.append(
                    f"Job `{job}` lief auf `{ereignis}` ({ergebnisse[job]}); "
                    "Produktions-Deploy ist ausschließlich `workflow_dispatch`."
                )
        titel = "Kein Deploy beabsichtigt" if not befunde else "Deploy-Sperre verletzt"
        einsatz = f"Worker-Tests auf `{ereignis}` (ohne Environment, ohne Secrets)"

    return {
        "code": CODE_ROT if befunde else CODE_GRUEN,
        "ereignis": ereignis,
        "einsatz": einsatz,
        "geplant": geplant,
        "ergebnisse": ergebnisse,
        "befunde": befunde,
        "titel": titel,
    }


def als_md(urteil: dict) -> str:
    zeilen = [
        "## " + ("✅ " if urteil["code"] == CODE_GRUEN else "❌ ") + urteil["titel"],
        "",
        f"- Ereignis: `{urteil['ereignis']}` · Einsatz: {urteil['einsatz']}",
        "- Job-Lage: " + ", ".join(
            f"`{job}` = `{stand}`" for job, stand in urteil["ergebnisse"].items()
        ),
        "",
    ]
    if urteil["befunde"]:
        zeilen += ["**Befunde:**"] + [f"- {text}" for text in urteil["befunde"]] + [""]
        zeilen += ["_Ein übersprungener Deploy wird nie als Erfolg gebucht._", ""]
    else:
        zeilen += ["_Beweis: kein geplanter Deploy wurde übersprungen oder "
                   "still als grün gemeldet._", ""]
    return "\n".join(zeilen)


def _fall(**kwargs) -> Mapping[str, str]:
    lage = {
        "EREIGNIS": EREIGNIS_DEPLOY,
        "REF": HAUPTZWEIG,
        "GEPLANT": '["newsletter-worker"]',
        "ERGEBNIS_PLAN": GRUEN,
        "ERGEBNIS_TESTS": AUSGESETZT,
        "ERGEBNIS_POLICY": GRUEN,
        "ERGEBNIS_DEPLOY": GRUEN,
    }
    lage.update(kwargs)
    return lage


def _selftest() -> int:
    """Gegenproben: genau die Lügen, die dieser Beweis unmöglich macht."""
    fehler: list[str] = []
    tests_lage = _fall(EREIGNIS="push", ERGEBNIS_PLAN=AUSGESETZT,
                       ERGEBNIS_TESTS=GRUEN, ERGEBNIS_POLICY=AUSGESETZT,
                       ERGEBNIS_DEPLOY=AUSGESETZT, GEPLANT="[]")

    def probe(name: str, lage: Mapping[str, str], erwartet: int) -> None:
        try:
            code = entscheiden(lage)["code"]
        except WerkzeugFehler as exc:
            code = exc.exit_code
        if code != erwartet:
            fehler.append(f"{name}: erwartet {erwartet}, erhalten {code}")

    probe("1 echter Deploy ist grün", _fall(), CODE_GRUEN)
    probe("2 reiner Test-Push ist grün", tests_lage, CODE_GRUEN)
    probe("3 reiner Test-PR ist grün", dict(tests_lage, EREIGNIS="pull_request"), CODE_GRUEN)
    probe("4 Deploy-Job skipped", _fall(ERGEBNIS_DEPLOY=AUSGESETZT), CODE_ROT)
    probe("5 Deploy-Job failure", _fall(ERGEBNIS_DEPLOY="failure"), CODE_ROT)
    probe("6 Produktions-Gate skipped", _fall(ERGEBNIS_POLICY=AUSGESETZT), CODE_ROT)
    probe("7 Deploy auf fremdem Zweig", _fall(REF="refs/heads/feature"), CODE_ROT)
    probe("8 Push deployt doch", dict(tests_lage, ERGEBNIS_DEPLOY=GRUEN), CODE_ROT)
    probe("9 Push ohne Tests", dict(tests_lage, ERGEBNIS_TESTS=AUSGESETZT), CODE_ROT)
    probe("10 leerer Plan bei Dispatch", _fall(GEPLANT="[]"), CODE_WERKZEUG)
    probe("11 unlesbarer Plan", _fall(GEPLANT="kein json"), CODE_WERKZEUG)
    probe("12 unbekanntes Ereignis", _fall(EREIGNIS="schedule"), CODE_WERKZEUG)
    probe("13 fehlendes Ergebnis", _fall(ERGEBNIS_POLICY=""), CODE_WERKZEUG)
    probe("14 Matrix nur teilweise grün", _fall(ERGEBNIS_DEPLOY="cancelled"), CODE_ROT)

    # Das Urteil muss den blockierenden Job beim Namen nennen (kein stummes Rot).
    urteil = entscheiden(_fall(ERGEBNIS_DEPLOY=AUSGESETZT))
    if not any("deploy" in text for text in urteil["befunde"]):
        fehler.append("15 Befund nennt den übersprungenen Job nicht")
    if "Beweis" not in als_md(entscheiden(_fall())):
        fehler.append("16 Zusammenfassung nennt den Beweis nicht")

    if fehler:
        for text in fehler:
            print("❌ " + text)
        return 2
    print(f"✅ SELBSTTEST OK — {16} Lagen geprüft: echter Deploy grün, "
          "jeder Skip, jede Teillieferung und jeder Push-Deploy rot.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verhaltensbeweis: kein grüner Worker-Deploy ohne ausgeführten Deploy.")
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--selftest", action="store_true", help="Gegenproben ohne Netz")
    gruppe.add_argument("--pruefen", action="store_true", help="Lage dieses Laufs bewerten")
    parser.add_argument("--md", help="Markdown an diese Datei hängen (Job-Zusammenfassung)")
    parser.add_argument("--json", action="store_true", help="Urteil als JSON ausgeben")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    try:
        urteil = entscheiden(os.environ)
    except WerkzeugFehler as exc:
        annotation("error", f"Lage nicht belegbar: {exc}", titel="Deploy-Beweis")
        return CODE_WERKZEUG

    if args.json:
        print(json.dumps(urteil, ensure_ascii=False, sort_keys=True))
    print(als_md(urteil))
    if args.md:
        try:
            with open(args.md, "a", encoding="utf-8") as ziel:
                ziel.write(als_md(urteil))
        except OSError as exc:
            annotation("error", f"Zusammenfassung nicht schreibbar ({type(exc).__name__}).",
                       titel="Deploy-Beweis")
            return CODE_WERKZEUG
    if urteil["code"] == CODE_ROT:
        annotation("error", " | ".join(urteil["befunde"]), titel=urteil["titel"])
    else:
        annotation("notice", urteil["einsatz"] + " – Beweis erbracht.",
                   titel=urteil["titel"])
    return int(urteil["code"])


if __name__ == "__main__":
    sys.exit(main())
