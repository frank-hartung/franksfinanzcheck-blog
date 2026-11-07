#!/usr/bin/env python3
"""F-01: opt-in Edge-Reparatur nach belegtem Befund; kein Ersatz für den Live-Nachweis."""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import unittest

import blog_header_gate as header
import cloudflare_edge_freigabe as edge
import sicherheits_nachweis as nachweis

ZONE = "franksfinanzcheck.de"
OWNER = ("Betreiber: B7 rechtlich prüfen und veröffentlichen; anschließend "
         "Zone-Token CF_EDGE_HEAL_TOKEN und CF_EDGE_AUTOHEAL=true bewusst einrichten "
         "(Runbook A1c). Worker-Deploy und Environment bleiben Betreiberaufgaben.")


def eintrag(pfad: Path, status: str, **daten) -> None:
    """Append-only Laufprotokoll, ohne Token, API-Antworten oder Roh-Header."""
    satz = {"zeit": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": status, **daten}
    with pfad.open("a", encoding="utf-8") as out:
        out.write(json.dumps(satz, ensure_ascii=False) + "\n")
        out.flush()
        os.fsync(out.fileno())


def vollstaendige_ziele(daten, *, sauber=False):
    ziele = daten.get("ziele")
    return (daten.get("stoerung") == [] and daten.get("nicht_gemessen") == []
            and isinstance(ziele, list) and len(ziele) == len(header.ZIELE)
            and daten.get("gemessen") == len(header.ZIELE)
            and all(isinstance(z, dict) and z.get("klasse") == "GEMESSEN"
                    and isinstance(z.get("url"), str) and type(z.get("status")) is int
                    and 200 <= z["status"] < 300
                    and (not sauber or z.get("fehlend") == []) for z in ziele)
            and {z["url"] for z in ziele} == set(header.ZIELE))


def ausfuehren(daten, code, token, freigabe, ledger, *, api_pruefen=None,
               anwenden=None, live_messen=None, b7_pfad=None):
    api_pruefen = api_pruefen or edge.pruefen
    anwenden = anwenden or edge.anwenden
    live_messen = live_messen or header.netz_pruefen
    b7_pfad = b7_pfad or edge.DATENSCHUTZ
    ledger = Path(ledger)

    def ende(code, status, text):
        eintrag(ledger, status, exit=code)
        return code, text

    eintrag(ledger, "start")
    try:
        nachweis.pruefe_messung(daten, "header", str(code))
    except (nachweis.NachweisFehler, TypeError):
        return ende(2, "messung_ungueltig", "Ungültiger Messnachweis; keine Änderung.")
    klasse = daten["klasse"]
    eintrag(ledger, "vorher", klasse=klasse, gemessen=daten["gemessen"])
    if klasse == "OK":
        return ende(0, "nicht_noetig", "F-01 OK; keine Änderung. Gesamtabschluss bleibt unabhängig.")
    if klasse != "BEFUND":
        return ende(2, "nicht_belegt", f"F-01 {klasse}: keine Heilung ohne belegten Befund.")
    # Kein API-Write bei nur teilweise messbaren oder fremden Zielen.
    if not vollstaendige_ziele(daten):
        return ende(2, "unvollstaendig", "F-01 nicht vollständig messbar; keine Änderung.")
    if freigabe != "true" or not token or not token.strip():
        return ende(2, "freigabe_fehlt", "Automatische Heilung gesperrt. " + OWNER)
    # B7 vor jedem Eingriff als zusätzliche Schranke: ein nicht vorhandener oder
    # alter Text darf nicht durch eine technische Reparatur überspielt werden.
    try:
        text = Path(b7_pfad).read_text(encoding="utf-8")
        if (edge.datenschutz_b7_offen(text) or edge.B7_MIT_PROXY_SATZ not in text
                or edge.B7_TABELLE_NEU not in text or edge.B7_DIENSTLEISTER_NEU not in text):
            return ende(2, "b7_offen", "Datenschutz B7 nicht vollständig im Repo. " + OWNER)
    except (OSError, UnicodeError):
        return ende(2, "b7_fehlt", "Datenschutz B7 nicht prüfbar. " + OWNER)
    try:
        vorher, _ = api_pruefen(token, ZONE)
        eintrag(ledger, "api_vorher", exit=vorher)
        if vorher == 0:
            return ende(1, "api_bereits_soll", "API im Soll, öffentliche Header abweichend; keine blinde Änderung. Runbook A1 prüfen.")
        if vorher != 1:
            return ende(2, "api_ungeprueft", "Cloudflare-API nicht belegbar; keine Änderung. " + OWNER)
        # Start wird vor dem ersten API-Write dauerhaft ins Artefakt geschrieben.
        eintrag(ledger, "aenderung_begonnen")
        resultat, _ = anwenden(token, ZONE, b7=False)
        eintrag(ledger, "api_nachher", exit=resultat)
        if resultat != 0:
            return ende(1 if resultat == 1 else 2, "api_nicht_soll", "API-Gegenmessung nicht erfolgreich; Teiländerungen möglich. Runbook A1 prüfen.")
        live_code, bericht, live = live_messen()
        live["bericht"] = bericht
        nachweis.pruefe_messung(live, "header", str(live_code))
        eintrag(ledger, "live_nachher", klasse=live["klasse"], exit=live_code,
                abschluss_blocker=len(live.get("abschluss_blocker", [])))
        if (live["klasse"] != "OK" or live.get("abschluss_blocker")
                or not vollstaendige_ziele(live, sauber=True)):
            return ende(1 if live["klasse"] == "BEFUND" or live.get("abschluss_blocker") else 2,
                        "live_nicht_soll", "Gegenmessung nicht vollständig grün; ursprünglicher Nachweis bleibt rot.")
        return ende(0, "gegenmessung_ok", "F-01 nach Heilung live OK. Ursprünglicher Lauf bleibt unverändert; erneuter vollständiger Live-Lauf erforderlich.")
    except Exception:
        # Keine API-Antworten oder Ausnahmen ausgeben: sie könnten Secrets enthalten.
        return ende(2, "stoerung", "Heilung oder Gegenmessung gestört; Teiländerungen möglich. Runbook A1 prüfen.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modus = parser.add_mutually_exclusive_group(required=True)
    modus.add_argument("--selftest", action="store_true")
    modus.add_argument("--run", action="store_true")
    parser.add_argument("--daten")
    parser.add_argument("--bericht")
    parser.add_argument("--code")
    parser.add_argument("--ledger", default="f01-heilung.jsonl")
    args = parser.parse_args()
    if args.selftest:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        suite = unittest.defaultTestLoader.loadTestsFromName("scripts.tests.test_live_selbstheilung")
        return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1
    if not args.daten or not args.bericht or args.code is None:
        parser.error("--run benötigt --daten, --bericht und --code")
    try:
        daten = nachweis.laden(args.daten)
        bericht = Path(args.bericht).read_text(encoding="utf-8")
        if not isinstance(daten, dict) or daten.get("bericht") != bericht:
            raise nachweis.NachweisFehler("Berichte widersprechen sich")
        code, text = ausfuehren(daten, args.code, os.environ.get("CF_EDGE_HEAL_TOKEN", ""),
                                os.environ.get("CF_EDGE_AUTOHEAL", ""), args.ledger)
    except (nachweis.NachweisFehler, OSError, UnicodeError):
        code, text = 2, "Messdatei oder Audit-Protokoll nicht lesbar/schreibbar; keine verlässliche Heilung."
    print("F-01 Selbstheilung: " + text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## F-01 Selbstheilung\n\n" + text + "\n\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
