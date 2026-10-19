#!/usr/bin/env python3
# ============================================================
#  AUTO-CLOSE-GATE – „Behoben“ nur mit Job-Beweis (WF-E813 / #809)
#  ------------------------------------------------------------
#  WARUM ES DAS GIBT (19.10.2026, Folge von Meldung #809):
#    Der resolve-Job des Fehler-Alertings schloss offene Meldungen bei
#    JEDEM grünen Lauf des Workflows auf main. Für die Sicherheits-Wache
#    lief der Job „Live-Messung (täglich und auf Zuruf)“ aber nur bei
#    `schedule`/`workflow_dispatch` – Push-Läufe führten ausschließlich
#    den Offline-Job „Quellseite“ aus und ließen die Live-Messung
#    ausgesetzt. Genau diese Push-Läufe schrieben „✅ Behoben: Der
#    Vorgang läuft wieder fehlerfrei auf main“ und schlossen die
#    Meldung, obwohl der betroffene Job seit dem ersten Alarm keinen
#    einzigen grünen Lauf hatte:
#
#      #782 (16.10.) → geschlossen durch Push-Lauf 38923824627 (Live: skipped)
#      #798 (17.10.) → geschlossen durch Push-Lauf 39125154809 (Live: skipped)
#      #809 (19.10.) → Nachfolger derselben Lüge; WF-E813 meldete sich
#                      innerhalb von fünf Tagen zum vierten Mal.
#
#    Ein „Behoben“ ohne den Job, der rot war, ist keine Feststellung,
#    sondern Alarm-Müdigkeit (Governance-Vertrag C4): Der Mensch lernt,
#    der Meldung zu misstrauen – und überliest irgendwann den echten Alarm.
#
#  DIE REGEL (eine Quelle der Wahrheit – diese Datei):
#    Eine Meldung wird NUR geschlossen, wenn jeder Job, den sie als
#    fehlgeschlagen benannt hat, im auflösenden Lauf vorhanden UND
#    `success` ist. Fehlt ein genannter Job in diesem Lauf (typisch:
#    bedingte Jobs wie die Live-Messung), bleibt die Meldung offen.
#    Kein Beweis im Lauf (Job-Liste leer/unlesbar) heißt ebenfalls:
#    offen. Nur Meldungen aus der Zeit vor der Job-Marker-Pflicht ohne
#    jede Job-Angabe im Body greifen auf den Altvertrag zurück (grüner
#    Lauf genügt) – der Fallback ist im Grund der Entscheidung benannt.
#
#  JOB-ANGABE IN DER MELDUNG (zwei Formen, eine Bedeutung):
#    1. <!-- alert-jobs: ["Job-Name"] -->   (JSON-Liste, Neuform)
#    2. Fallback: „- Job **„Job-Name“**“ aus „Fehlgeschlagene Schritte“
#
#  EINGABE: Body der Meldung (Datei oder -) und die Jobs des Laufs
#           (JSON wie GET /actions/runs/{id}/jobs, auch als nackte Liste).
#  AUSGABE: JSON {"schliessen": bool, "grund": str, "gemessen": [...],
#                 "fehlend": [...]}  ·  Exit 0 = gültige Entscheidung,
#           2 = Werkzeugfehler (nie schließen auf Fehler – fail-safe).
#
#  SELBSTTEST: `--selftest` führt die Gegenproben des Vorfalls #809 aus
#  (Live-Messung skipped → nicht schließen; Live-Messung grün → schließen).
#  Regression: `python3 -m unittest scripts.tests.test_alert_resolve_gate`.
# ============================================================
"""Job-Beweis für das Auto-Close des Fehler-Alertings (WF-E813 / #809)."""

from __future__ import annotations

import argparse
import json
import re
import sys

MARKER = re.compile(r"<!--\s*alert-jobs:\s*(?P<liste>\[.*\])\s*-->", re.S)
# Altform: „- Job **„Name“**“ im Abschnitt „Fehlgeschlagene Schritte“.
# Die Anführungszeichen sind typografisch („ … “), deshalb als Zeichenklasse.
JOBSZEILE = re.compile(r"^[ \t]*- Job \*\*[„\"](?P<name>.+?)[“\"]\*\*", re.M)
ABGESCHNITT = re.compile(r"^[ \t]*- Job \*\*", re.M)

GRUENE_KLUSSEL = ("success",)


def jobs_aus_body(body: str) -> list[str]:
    """Welche Jobs hat die Meldung als fehlgeschlagen benannt?

    Form 1 (Marker, JSON) hat Vorrang; sonst Form 2 (lesbare Zeilen).
    Reihenfolge bleibt erhalten, Duplikate fallen weg.
    """
    text = body or ""
    treffer = MARKER.search(text)
    if treffer:
        try:
            liste = json.loads(treffer.group("liste"))
        except ValueError:
            liste = []
        if isinstance(liste, list):
            namen = [str(n) for n in liste if str(n).strip()]
            if namen:
                return _ohne_doppelte(namen)
    namen = [m.group("name").strip() for m in JOBSZEILE.finditer(text)]
    return _ohne_doppelte([n for n in namen if n])


def _ohne_doppelte(namen: list[str]) -> list[str]:
    gesehen: set[str] = set()
    aus: list[str] = []
    for n in namen:
        if n not in gesehen:
            gesehen.add(n)
            aus.append(n)
    return aus


def jobs_aus_lauf(roh) -> dict[str, str]:
    """Job-Name → conclusion aus der API-Antwort (oder einer nackten Liste)."""
    if isinstance(roh, dict):
        liste = roh.get("jobs")
    else:
        liste = roh
    if not isinstance(liste, list):
        return {}
    tabelle: dict[str, str] = {}
    for j in liste:
        if not isinstance(j, dict):
            continue
        name = str(j.get("name") or "").strip()
        if name:
            tabelle[name] = str(j.get("conclusion") or "")
    return tabelle


def entscheiden(body: str, lauf_jobs) -> dict:
    """Die einzige Regel: Ohne den grünen Job, der rot war, kein „Behoben“."""
    gemeldet = jobs_aus_body(body)
    lauf = jobs_aus_lauf(lauf_jobs)

    if not gemeldet:
        # Altvertrag (Meldung ohne jede Job-Angabe): ein grüner Lauf auf main
        # genügte bisher. Solange der Lauf wenigstens EINEN Job zeigt, gilt
        # das weiter – aber der Grund sagt es ausdrücklich, statt es zu
        # verstecken. Ohne jeden Job-Beweis im Lauf gilt auch hier: offen.
        if not lauf:
            return {
                "schliessen": False,
                "grund": ("Kein Job-Beweis im Lauf (Job-Liste leer oder unlesbar) "
                          "und die Meldung nennt selbst keine Jobs – ohne Beweis "
                          "bleibt sie offen."),
                "gemessen": [],
                "fehlend": [],
            }
        return {
            "schliessen": True,
            "grund": ("Job-Lage der Meldung unbekannt (Altvertrag) – der grüne "
                      "Lauf auf main genügt für diese Meldung."),
            "gemessen": sorted(lauf),
            "fehlend": [],
        }

    if not lauf:
        return {
            "schliessen": False,
            "grund": ("Kein Job-Beweis im Lauf (Job-Liste leer oder unlesbar) – "
                      "„Behoben“ ohne den Job, der rot war, wäre eine Behauptung "
                      "ohne Messung."),
            "gemessen": [],
            "fehlend": list(gemeldet),
        }

    fehlt_im_lauf = [n for n in gemeldet if n not in lauf]
    if fehlt_im_lauf:
        return {
            "schliessen": False,
            "grund": ("Job „" + fehlt_im_lauf[0] + "“ ist in diesem Lauf nicht "
                      "gelaufen – der Lauf beweist nichts über den Fehler, der "
                      "die Meldung erzeugt hat."),
            "gemessen": sorted(lauf),
            "fehlend": list(gemeldet),
        }

    nicht_gruen = [n for n in gemeldet if lauf.get(n) not in GRUENE_KLUSSEL]
    if nicht_gruen:
        name = nicht_gruen[0]
        return {
            "schliessen": False,
            "grund": (f"Job „{name}“ ist in diesem Lauf "
                      f"‚{lauf.get(name) or 'unbekannt'}‘ – nicht grün."),
            "gemessen": sorted(lauf),
            "fehlend": list(gemeldet),
        }

    return {
        "schliessen": True,
        "grund": ("Alle gemeldeten Jobs sind in diesem Lauf grün: "
                  + ", ".join(f"„{n}“" for n in gemeldet) + "."),
        "gemessen": sorted(lauf),
        "fehlend": [],
    }


# ------------------------------------------------------------------ Selbsttest
def selftest() -> int:
    faelle = 0
    LIVE = "Live-Messung (täglich und auf Zuruf)"
    QUELLE = "Quellseite (offline, mit Selbsttests)"
    body_neu = (f"<!-- alert-key: WF-E813 -->\n<!-- alert-jobs: "
                + json.dumps([LIVE], ensure_ascii=False)
                + " -->\n- Job **„" + LIVE + "“** ([Log](https://x)) – „F-01“")
    body_alt = ("- Job **„" + LIVE + "“** ([Log](https://x)) – Schritte")

    # Gegenprobe 1 (DER Vorfall #809): Push-Lauf ohne Live-Job schließt die
    # Live-Meldung NICHT – auch wenn der Lauf insgesamt grün ist.
    e = entscheiden(body_neu, {"jobs": [{"name": QUELLE, "conclusion": "success"}]})
    assert e["schliessen"] is False and LIVE in e["grund"], e
    faelle += 1

    # Gegenprobe 2: Derselbe Job im selben Lauf grün → schließen.
    e = entscheiden(body_neu, {"jobs": [{"name": QUELLE, "conclusion": "success"},
                                        {"name": LIVE, "conclusion": "success"}]})
    assert e["schliessen"] is True and LIVE in e["grund"], e
    faelle += 1

    # Gegenprobe 3: Job vorhanden, aber ausgesetzt (skipped) → kein Beweis.
    e = entscheiden(body_neu, {"jobs": [{"name": LIVE, "conclusion": "skipped"}]})
    assert e["schliessen"] is False, e
    faelle += 1

    # Gegenprobe 4: Job vorhanden, aber nicht grün → offen.
    e = entscheiden(body_neu, {"jobs": [{"name": LIVE, "conclusion": "failure"}]})
    assert e["schliessen"] is False and "nicht grün" in e["grund"], e
    faelle += 1

    # Gegenprobe 5: Zwei gemeldete Jobs, nur einer grün → offen.
    zwo = '<!-- alert-jobs: ["A", "B"] -->\n- Job **„A“**\n- Job **„B“**'
    e = entscheiden(zwo, {"jobs": [{"name": "A", "conclusion": "success"},
                                   {"name": "B", "conclusion": "failure"}]})
    assert e["schliessen"] is False and "B" in e["grund"], e
    faelle += 1

    # Gegenprobe 6: Altform ohne Marker wird geparst – die Regel greift auch
    # für Bestandsmeldungen (z. B. #782/#798/#809 aus der Zeit davor).
    e = entscheiden(body_alt, {"jobs": [{"name": QUELLE, "conclusion": "success"}]})
    assert e["schliessen"] is False, e
    faelle += 1

    # Gegenprobe 7: Job-Namen mit Klammern/Umlauten überleben den Marker-Rundlauf.
    sonder = "Live-Messung (täglich & auf Zuruf) – „prüfen“"
    e = entscheiden('<!-- alert-jobs: ' + json.dumps([sonder], ensure_ascii=False)
                    + " -->", {"jobs": [{"name": sonder, "conclusion": "success"}]})
    assert e["schliessen"] is True, e
    faelle += 1

    # Gegenprobe 8: Leerlauf – kein Job-Beweis im Lauf, egal was die Meldung
    # sagt: niemals schließen.
    e = entscheiden(body_neu, {"jobs": []})
    assert e["schliessen"] is False and "ohne Messung" in e["grund"], e
    e = entscheiden("ohne alles", [])
    assert e["schliessen"] is False and "ohne Beweis" in e["grund"], e
    faelle += 1

    # Gegenprobe 9: Altvertrag – Meldung ohne Job-Angabe, Lauf mit grünen
    # Jobs → schließen (altes Verhalten bleibt für Bestand erhalten).
    e = entscheiden("nur Text", {"jobs": [{"name": QUELLE, "conclusion": "success"}]})
    assert e["schliessen"] is True and "Altvertrag" in e["grund"], e
    faelle += 1

    # Gegenprobe 10: Kaputter Marker (kein JSON) fällt nicht durch – er wird
    # ignoriert und die lesbare Zeile rettet die Regel.
    kaputt = "<!-- alert-jobs: [kein json -->\n- Job **„" + LIVE + "“**"
    e = entscheiden(kaputt, {"jobs": [{"name": LIVE, "conclusion": "success"}]})
    assert e["schliessen"] is True, e
    faelle += 1

    # Gegenprobe 11: JSON-Antwort der API in beiden Shapes (Liste | {jobs}).
    assert jobs_aus_lauf([{"name": "X", "conclusion": "success"}])["X"] == "success"
    assert jobs_aus_lauf({"jobs": [{"name": "X", "conclusion": "success"}]})["X"] == "success"
    faelle += 1

    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (Job-Beweis statt „irgendein "
          "grüner Lauf“, WF-E813 / #809).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auto-Close-Gate: „Behoben“ nur mit Job-Beweis (WF-E813 / #809).")
    parser.add_argument("--body", help="Body der Meldung (Datei oder - für stdin)")
    parser.add_argument("--jobs", help="Jobs des Laufs als JSON-Datei")
    parser.add_argument("--json", action="store_true", help="Entscheidung als JSON")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.body or not args.jobs:
        print("❌ --body und --jobs werden benötigt (oder --selftest).",
              file=sys.stderr)
        return 2
    try:
        body = (sys.stdin.read() if args.body == "-"
                else open(args.body, encoding="utf-8").read())
        with open(args.jobs, encoding="utf-8") as f:
            lauf_jobs = json.load(f)
    except OSError as fehler:
        print(f"❌ Eingabe nicht lesbar: {fehler}", file=sys.stderr)
        return 2
    except ValueError as fehler:
        print(f"❌ Job-JSON nicht lesbar: {fehler}", file=sys.stderr)
        return 2

    e = entscheiden(body, lauf_jobs)
    if args.json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
    else:
        print(("SCHLIESSEN" if e["schliessen"] else "OFFEN") + ": " + e["grund"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
