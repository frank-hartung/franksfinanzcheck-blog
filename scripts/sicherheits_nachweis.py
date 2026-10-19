#!/usr/bin/env python3
"""WF-E813/#809: Messungen auswerten; nur ein echter Live-Nachweis schließt.

Ein grüner Quellseiten-Lauf auf main hat #798 geschlossen, obwohl sein
Live-Job übersprungen war. Deshalb braucht der Abschluss jetzt den erfolgreich
ausgeführten Nachweis-Schritt. Fehlende/kaputte Messdateien sind WACHE-FEHLER,
nicht BEFUND. Dieses Modul schreibt nie in Cloudflare und liest keine Secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from blog_header_gate import ZIELE

LIVE_JOB = "Live-Messung (täglich und auf Zuruf)"
HEADER_MESSUNG = "Sicherheits-Header der echten Seite messen (F-01)"
HEADER_AUSWERTUNG = "Sicherheits-Header auswerten (F-01) · Befund · Störung · grün"
WORKER_MESSUNG = "Worker-Zustand messen – Budget, Bot-Schutz, Exporte (F-02/F-03/F-08)"
WORKER_AUSWERTUNG = "Worker-Zustand auswerten (F-02/F-03/F-08) · Befund · Störung · grün"
LIVE_NACHWEIS = "Live-Nachweis abschließen (F-01/F-02/F-03/F-08)"
LIVE_SCHRITTE = (HEADER_MESSUNG, HEADER_AUSWERTUNG, WORKER_MESSUNG,
                 WORKER_AUSWERTUNG, LIVE_NACHWEIS)
KLASSEN = {"OK": 0, "TEILWEISE": 0, "BEFUND": 1, "STOERUNG": 2}


class NachweisFehler(ValueError):
    """Fehlender oder widersprüchlicher Messnachweis; niemals ein Seitenbefund."""


def laden(pfad: str | Path):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as fehler:
        # Keine Nutzdaten oder Parser-Auszüge veröffentlichen.
        raise NachweisFehler("Messdatei fehlt oder enthält kein gültiges JSON.") from fehler


def pruefe_messung(daten: dict, quelle: str, code: str) -> None:
    if not isinstance(daten, dict) or quelle not in ("header", "worker"):
        raise NachweisFehler("Messung hat nicht das erwartete Objektformat.")
    klasse = daten.get("klasse")
    if not isinstance(klasse, str) or klasse not in KLASSEN:
        raise NachweisFehler("Messklasse fehlt oder ist unbekannt (offline ist kein Live-Nachweis).")
    if quelle == "worker" and klasse == "TEILWEISE":
        raise NachweisFehler("Ein teilweiser Worker-Stand ist kein gültiges Betriebsbild.")
    if (type(daten.get("exit")) is not int or str(daten["exit"]) != code
            or daten["exit"] != KLASSEN[klasse]):
        raise NachweisFehler("Exit-Code und Messklasse widersprechen sich oder fehlen.")
    if type(daten.get("gemessen")) is not int or daten["gemessen"] < 0:
        raise NachweisFehler("Anzahl der tatsächlich gemessenen Ziele fehlt.")
    for name in ("fehlend", "warnungen", "stoerung"):
        if not isinstance(daten.get(name), list) or not all(
                isinstance(wert, str) and wert.strip() for wert in daten[name]):
            raise NachweisFehler(f"Messliste {name} fehlt oder hat ein ungültiges Format.")
    if not isinstance(daten.get("bericht"), str) or not daten["bericht"].strip():
        raise NachweisFehler("Lesbarer Messbericht fehlt.")
    if not isinstance(daten.get("naechster_schritt"), str):
        raise NachweisFehler("Handlungsempfehlung fehlt.")
    if klasse == "STOERUNG":
        if daten["gemessen"] != 0 or daten["fehlend"] or not daten["stoerung"]:
            raise NachweisFehler("Eine Nicht-Messung darf keine Sicherheitsbefunde behaupten.")
    elif daten["gemessen"] < 1:
        raise NachweisFehler("Die Messklasse behauptet eine Messung ohne gemessenes Ziel.")
    if klasse == "BEFUND" and not daten["fehlend"]:
        raise NachweisFehler("BEFUND ohne belegte Abweichung.")
    if klasse in ("OK", "TEILWEISE") and daten["fehlend"]:
        raise NachweisFehler("Eine grüne Messklasse enthält offene Befunde.")
    if klasse == "OK" and daten["stoerung"]:
        raise NachweisFehler("OK enthält nicht gemessene Ziele.")


def annotation(stufe: str, text: str) -> None:
    # HTTP-Antworten/Fehlermeldungen sind Daten, keine Workflow-Kommandos.
    sicher = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{stufe}::{sicher}")


def zusammenfassung(text: str) -> None:
    pfad = os.environ.get("GITHUB_STEP_SUMMARY")
    if pfad:
        with open(pfad, "a", encoding="utf-8") as ausgabe:
            ausgabe.write(text + "\n\n")


def auswerten(quelle: str, code: str, datenpfad: str, berichtpfad: str) -> int:
    name = "F-01" if quelle == "header" else "Worker"
    try:
        daten = laden(datenpfad)
        pruefe_messung(daten, quelle, code)
        bericht = Path(berichtpfad).read_text(encoding="utf-8")
        if bericht != daten["bericht"]:
            raise NachweisFehler("JSON und Markdown-Bericht gehören nicht zur selben Messung.")
    except (NachweisFehler, OSError, UnicodeError) as fehler:
        grund = str(fehler) if isinstance(fehler, NachweisFehler) else "Markdown-Bericht fehlt."
        text = f"{name} WACHE-FEHLER: {grund} Prüfung reparieren, nicht die Infrastruktur auf Verdacht ändern."
        annotation("error", text)
        zusammenfassung(f"## {name} · WACHE-FEHLER\n\n{text}")
        return 1

    zusammenfassung(bericht)
    klasse = daten["klasse"]
    if klasse in ("OK", "TEILWEISE"):
        if klasse == "TEILWEISE":
            annotation("warning", f"{name} TEILWEISE: kein vollständiger Live-Nachweis; nicht gemessene Ziele siehe Zusammenfassung.")
        else:
            annotation("notice", f"{name} grün: vollständig gemessen, Details siehe Zusammenfassung.")
        return 0
    # Jede Abweichung ist über die Checks-API sichtbar, auch ohne Log-Download.
    liste = daten["fehlend"] if klasse == "BEFUND" else daten["stoerung"]
    for grund in liste:
        annotation("error", f"{name} {klasse}: {grund}")
    if daten["naechster_schritt"]:
        annotation("error", f"{name} {klasse}: {daten['naechster_schritt']}")
    return 1


def live_pruefen(header: dict, worker: dict) -> tuple[bool, str]:
    try:
        for quelle, daten in (("header", header), ("worker", worker)):
            pruefe_messung(daten, quelle, str(daten.get("exit")) if isinstance(daten, dict) else "")
            if daten["klasse"] != "OK":
                return False, f"{quelle}: {daten['klasse']} – kein vollständiger Live-Nachweis."
        ziele = header.get("ziele")
        if (not isinstance(ziele, list) or len(ziele) != len(ZIELE)
                or any(not isinstance(ziel, dict) or not isinstance(ziel.get("url"), str)
                       for ziel in ziele)
                or {ziel.get("url") for ziel in ziele} != set(ZIELE)
                or header["gemessen"] != len(ZIELE) or header.get("nicht_gemessen") != []):
            raise NachweisFehler("F-01: Nicht alle vorgesehenen Ziele wurden gemessen.")
        for ziel in ziele:
            if (ziel.get("klasse") != "GEMESSEN" or type(ziel.get("status")) is not int
                    or not 200 <= ziel["status"] < 300 or ziel.get("fehlend") != []):
                raise NachweisFehler("F-01: Ein Ziel hat keinen erfolgreichen, befundfreien HTTP-Nachweis.")
        if worker["gemessen"] != 1:
            raise NachweisFehler("Worker: authentifiziertes Betriebsbild fehlt.")
    except NachweisFehler as fehler:
        return False, str(fehler)
    return True, "Header aller vorgesehenen Ziele und authentifizierter Worker-Zustand vollständig gemessen."


def abschluss_pruefen(jobs: list, ereignis: str) -> tuple[bool, str]:
    """Fail-closed: main/Erfolg prüft der Aufrufer; hier zählt die Live-Ausführung."""
    if ereignis not in ("schedule", "workflow_dispatch"):
        return False, "Offline-/Push-Läufe sind kein Live-Nachweis; Meldung bleibt offen."
    if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
        return False, "Job-Lage unbekannt; Meldung bleibt offen."
    live = [job for job in jobs if job.get("name") == LIVE_JOB]
    if len(live) != 1 or live[0].get("conclusion") != "success":
        return False, "Live-Job fehlt, wurde übersprungen oder war nicht erfolgreich; Meldung bleibt offen."
    schritte = live[0].get("steps")
    if not isinstance(schritte, list) or not all(isinstance(s, dict) for s in schritte):
        return False, "Live-Schritte nicht nachgewiesen; Meldung bleibt offen."
    for name in LIVE_SCHRITTE:
        treffer = [s for s in schritte if s.get("name") == name]
        if len(treffer) != 1 or treffer[0].get("conclusion") != "success":
            return False, f"Erfolgreicher Schritt fehlt: {name}. Meldung bleibt offen."
    return True, "Vollständiger erfolgreicher Live-Nachweis liegt vor; Abschluss zulässig."


def selftest() -> int:
    jobs = [{"name": LIVE_JOB, "conclusion": "success", "steps": [
        {"name": name, "conclusion": "success"} for name in LIVE_SCHRITTE]}]
    assert abschluss_pruefen(jobs, "schedule")[0]
    assert abschluss_pruefen(jobs, "workflow_dispatch")[0]
    assert not abschluss_pruefen(jobs, "push")[0]
    assert not abschluss_pruefen([], "schedule")[0]
    for name in LIVE_SCHRITTE:
        kopie = json.loads(json.dumps(jobs))
        next(s for s in kopie[0]["steps"] if s["name"] == name)["conclusion"] = "skipped"
        assert not abschluss_pruefen(kopie, "schedule")[0], name
    # Auch der Messvertrag wird sabotiert, nicht nur die Abschluss-Hülle.
    daten = {"exit": 0, "klasse": "OK", "gemessen": 1, "fehlend": [],
             "warnungen": [], "stoerung": [], "bericht": "Messbericht", "naechster_schritt": ""}
    pruefe_messung(daten, "worker", "0")
    for aenderung in ({"klasse": "OFFLINE"}, {"exit": 1}, {"gemessen": 0},
                      {"fehlend": ["offener Befund"]}, {"bericht": ""}):
        try:
            pruefe_messung({**daten, **aenderung}, "worker", "0")
        except NachweisFehler:
            continue
        raise AssertionError(f"Ungültiger Messnachweis akzeptiert: {aenderung}")
    print("✅ SELBSTTEST OK — Live-Abschluss, übersprungene Schritte und widersprüchliche Messnachweise erkannt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modus = parser.add_mutually_exclusive_group(required=True)
    modus.add_argument("--auswerten", choices=("header", "worker"))
    modus.add_argument("--live", nargs=2, metavar=("HEADER_JSON", "WORKER_JSON"))
    modus.add_argument("--abschluss", metavar="JOBS_JSON")
    modus.add_argument("--selftest", action="store_true")
    parser.add_argument("--code", default="")
    parser.add_argument("--daten")
    parser.add_argument("--bericht")
    parser.add_argument("--ereignis", default="")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.auswerten:
        if not args.daten or not args.bericht:
            parser.error("--auswerten benötigt --daten und --bericht")
        return auswerten(args.auswerten, args.code, args.daten, args.bericht)
    try:
        if args.abschluss:
            ok, text = abschluss_pruefen(laden(args.abschluss), args.ereignis)
            print(text)
            return 0 if ok else 1
        ok, text = live_pruefen(*(laden(pfad) for pfad in args.live))
    except NachweisFehler as fehler:
        ok, text = False, str(fehler)
    annotation("notice" if ok else "error", f"Live-Nachweis: {text}")
    zusammenfassung(f"## Live-Nachweis · {'vollständig' if ok else 'NICHT vollständig'}\n\n{text}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
