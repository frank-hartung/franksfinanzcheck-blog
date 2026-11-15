#!/usr/bin/env python3
# ============================================================
#  PR-BESTANDS-WACHE – kein Änderungsvorschlag altert unbemerkt
#  ------------------------------------------------------------
#  WARUM ES DAS GIBT (14.11.2026)
#    Am 14.11.2026 lagen fünf Änderungsvorschläge offen (#1167, #1171,
#    #1173, #1174, #1217), die ältesten seit vier Tagen. In dieser Zeit
#    bekam `main` 170 bis 210 Commits und löste ihre Themen auf anderem
#    Weg – teils übernommen, teils bewusst anders entschieden. Keiner der
#    fünf ließ sich danach noch zusammenführen, ohne Heilungen zurück-
#    zudrehen; drei trugen rote Prüfungen, die niemand mehr ansah. Einer
#    enthielt Redaktionsentscheidungen, die mit jedem Tag weniger zum
#    Text passten: von 140 galten am Ende noch 8.
#
#    Kein Skript und kein Workflow sah offene Vorschläge an. Die einzige
#    Stelle, die Vorschläge liest (`vorgangs_abschluss.py`), liest nur
#    bereits zusammengeführte. Ein Vorschlag ohne Bewegung war damit ein
#    Alarm ohne Besitzer und ohne Schließpfad (D12) – er kostete erst
#    dann etwas, als seine Arbeit schon verfallen war.
#
#  WAS DIE WACHE MISST
#    Jeden offenen Vorschlag, der seit RUHE_TAGE Tagen ohne Bewegung ist
#    (letzte Änderung laut GitHub: Commit, Kommentar, Prüfung). Entwürfe
#    und maschinell erzeugte Vorschläge zählen mit: Auch sie warten auf
#    eine Entscheidung.
#
#  WAS SIE NICHT TUT
#    Sie schließt nichts, kommentiert nichts und führt nichts zusammen.
#    Ob ein Vorschlag zusammengeführt, aktualisiert oder geschlossen
#    wird, entscheidet ein Mensch. Die Wache sorgt nur dafür, dass die
#    Frage gestellt wird, solange die Antwort noch billig ist.
#
#  SCHLIESSPFAD
#    Der Befund verschwindet von selbst aus Messung und Bericht, sobald
#    kein Vorschlag mehr über der Ruhefrist liegt. Geführt wird er vom
#    Bot-Watchdog im Voll-Lauf (`scripts/bot_watchdog.py`, Check 11) als
#    Befund mit menschlichem Besitzer. Das Fach-Ticket dazu schließt der
#    Mensch, der entschieden hat – so hält es der Alarm-Router bei jedem
#    Befund mit menschlichem Besitzer (`scripts/alert_router.py`).
#
#  NICHT MESSBAR IST NICHT GRÜN (C2)
#    Antwortet GitHub nicht oder unlesbar, meldet die Wache „nicht
#    messbar“ (Exit 2) – nie „keine offenen Vorschläge“.
#
#  BEFEHLE
#    (ohne)        messen und im Klartext berichten
#    --json        Messung als JSON
#    --selftest    Beweis ohne Netz
#
#  Exit: 0 = kein Vorschlag über der Ruhefrist · 1 = Befund
#        2 = nicht messbar (Werkzeug, Netz, unlesbare Antwort)
# ============================================================
"""Offene Änderungsvorschläge, die ohne Bewegung liegen – sichtbar, mit Besitzer."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys

# Ruhefrist in Tagen. Drei Tage sind in diesem Repo viel: Am 14.11.2026 lagen
# zwischen einem drei Tage alten Vorschlag und `main` bereits über 170 Commits.
RUHE_TAGE = 3
# Mehr Vorschläge liest die Wache nicht ein. Wird die Grenze erreicht, ist die
# Messung unvollständig – und damit nicht messbar statt grün.
LESE_GRENZE = 200
FELDER = "number,createdAt,updatedAt,isDraft,mergeable,author"
BEFUND_ID = "pr-bestand"


class NichtMessbar(Exception):
    """Die offenen Vorschläge ließen sich nicht vollständig lesen."""


def _zeit(wert) -> dt.datetime:
    """ISO-Zeitstempel von GitHub („…Z“) als UTC-Zeit. Unlesbar → NichtMessbar."""
    if not isinstance(wert, str) or not wert:
        raise NichtMessbar(f"Zeitstempel fehlt oder ist kein Text: {wert!r}")
    try:
        zeit = dt.datetime.fromisoformat(wert.replace("Z", "+00:00"))
    except ValueError as fehler:
        raise NichtMessbar(f"Zeitstempel unlesbar: {wert!r}") from fehler
    if zeit.tzinfo is None:
        zeit = zeit.replace(tzinfo=dt.timezone.utc)
    return zeit.astimezone(dt.timezone.utc)


def aus_antwort(text: str) -> list[dict]:
    """Die Antwort von `gh pr list --json …` streng lesen."""
    try:
        daten = json.loads(text)
    except (TypeError, ValueError) as fehler:
        raise NichtMessbar(f"Antwort ist kein JSON: {str(text)[:120]!r}") from fehler
    if not isinstance(daten, list):
        raise NichtMessbar("Antwort ist keine Liste")
    if len(daten) >= LESE_GRENZE:
        raise NichtMessbar(
            f"{len(daten)} offene Vorschläge erreichen die Lesegrenze "
            f"({LESE_GRENZE}) – die Liste ist womöglich abgeschnitten")
    for eintrag in daten:
        if not isinstance(eintrag, dict) or not isinstance(eintrag.get("number"), int):
            raise NichtMessbar("Eintrag ohne Nummer in der Antwort")
    return daten


def lies_offene(lauf=subprocess.run) -> list[dict]:
    """Alle offenen Vorschläge über die GitHub-CLI. Jeder Fehler → NichtMessbar."""
    argv = ["gh", "pr", "list", "--state", "open", "--limit", str(LESE_GRENZE),
            "--json", FELDER]
    try:
        ergebnis = lauf(argv, capture_output=True, text=True, timeout=60,
                        check=False)
    except (OSError, subprocess.SubprocessError) as fehler:
        raise NichtMessbar(f"GitHub-CLI nicht ausführbar: {fehler}") from fehler
    if ergebnis.returncode != 0:
        raise NichtMessbar(
            f"GitHub-CLI Exit {ergebnis.returncode}: "
            f"{(ergebnis.stderr or '').strip()[:200]}")
    vorschlaege = aus_antwort(ergebnis.stdout)
    if len(vorschlaege) >= LESE_GRENZE:
        # Eine volle Seite kann abgeschnitten sein: Was dahinter liegt, sähe
        # die Wache nicht – und meldete trotzdem „keiner liegt“ (C2).
        raise NichtMessbar(
            f"Lesegrenze von {LESE_GRENZE} offenen Vorschlägen erreicht – "
            f"der Bestand ist möglicherweise nicht vollständig gelesen")
    return vorschlaege


def urteile(vorschlaege: list[dict], jetzt: dt.datetime,
            ruhe_tage: int = RUHE_TAGE) -> list[dict]:
    """Die Vorschläge über der Ruhefrist – der älteste Stillstand zuerst.

    Rein, ohne Netz und ohne Uhr: `jetzt` kommt vom Aufrufer. Gemessen wird
    in ganzen Tagen seit der letzten Änderung; genau `ruhe_tage` zählt schon.
    """
    if ruhe_tage < 1:
        raise ValueError("Die Ruhefrist muss mindestens einen Tag betragen")
    if jetzt.tzinfo is None:
        jetzt = jetzt.replace(tzinfo=dt.timezone.utc)
    liegend = []
    for eintrag in vorschlaege:
        bewegt = _zeit(eintrag.get("updatedAt"))
        erstellt = _zeit(eintrag.get("createdAt"))
        ruhe = (jetzt - bewegt).days
        if ruhe < ruhe_tage:
            continue
        autor = eintrag.get("author") if isinstance(eintrag.get("author"), dict) else {}
        liegend.append({
            "_bewegt": bewegt,
            "nummer": eintrag["number"],
            "ruhe_tage": ruhe,
            "alter_tage": max(ruhe, (jetzt - erstellt).days),
            "entwurf": bool(eintrag.get("isDraft")),
            "konflikt": eintrag.get("mergeable") == "CONFLICTING",
            "maschinell": bool(autor.get("is_bot")),
        })
    liegend.sort(key=lambda e: (e["_bewegt"], e["nummer"]))
    for eintrag in liegend:
        del eintrag["_bewegt"]
    return liegend


def zeile(eintrag: dict) -> str:
    """Ein Vorschlag als eine Zeile – nur Nummer und Messwerte, kein Titel.

    Der Text landet in einem öffentlichen Ticket. Titel von Vorschlägen
    tragen Betriebssprache; die Nummer genügt, um ihn zu finden.
    """
    zusatz = [wort for wort, wahr in (("Entwurf", eintrag["entwurf"]),
                                      ("Konflikt mit main", eintrag["konflikt"]),
                                      ("maschinell erzeugt", eintrag["maschinell"]))
              if wahr]
    text = (f"#{eintrag['nummer']}: seit {eintrag['ruhe_tage']} Tagen ohne "
            f"Bewegung, offen seit {eintrag['alter_tage']} Tagen")
    return text + (f" ({', '.join(zusatz)})" if zusatz else "")


def kurztext(liegend: list[dict], gesamt: int, ruhe_tage: int = RUHE_TAGE) -> str:
    if not liegend:
        return (f"{gesamt} offen, keiner seit {ruhe_tage} Tagen oder länger "
                f"ohne Bewegung")
    return (f"{len(liegend)} von {gesamt} offenen seit {ruhe_tage} Tagen oder "
            f"länger ohne Bewegung, ältester Stillstand "
            f"{liegend[0]['ruhe_tage']} Tage (#{liegend[0]['nummer']})")


NAECHSTER_SCHRITT = (
    "Je Vorschlag entscheiden: zusammenführen, auf den Stand von `main` "
    "bringen oder schließen. Vor dem Schließen prüfen, was `main` schon "
    "übernommen hat (`git diff origin/main...<Zweig>`), und was noch fehlt, "
    "in einem neuen Vorschlag nachziehen. Liste: `python3 "
    "scripts/pr_bestand_wache.py`. Meldet die Liste keinen liegenden "
    "Vorschlag mehr, dieses Ticket schließen.")


def messe(jetzt: dt.datetime | None = None, lauf=subprocess.run,
          ruhe_tage: int = RUHE_TAGE) -> dict:
    """Lesen und urteilen. Wirft NichtMessbar – nie ein stilles Grün."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    vorschlaege = lies_offene(lauf)
    liegend = urteile(vorschlaege, jetzt, ruhe_tage)
    return {"gemessen": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ruhe_tage": ruhe_tage, "offen": len(vorschlaege),
            "liegend": liegend,
            "kurztext": kurztext(liegend, len(vorschlaege), ruhe_tage)}


# ------------------------------------------------------------
#  Selbsttest – prüft dieses Modul, ohne Netz (D6)
# ------------------------------------------------------------
def selftest() -> int:
    fehler: list[str] = []
    faelle = [0]

    def pruefe(name, ist, soll):
        faelle[0] += 1
        if ist != soll:
            fehler.append(f"{name}: erwartet {soll!r}, bekam {ist!r}")

    def wirft(name, aufruf):
        faelle[0] += 1
        try:
            aufruf()
        except NichtMessbar:
            return
        except Exception as anderes:  # noqa: BLE001 – der Test nennt den Typ
            fehler.append(f"{name}: falscher Fehlertyp {type(anderes).__name__}")
            return
        fehler.append(f"{name}: kein NichtMessbar")

    jetzt = dt.datetime(2026, 11, 14, 18, 0, tzinfo=dt.timezone.utc)

    def vorschlag(nummer, bewegt, erstellt=None, **mehr):
        return dict({"number": nummer, "updatedAt": bewegt,
                     "createdAt": erstellt or bewegt, "isDraft": False,
                     "mergeable": "MERGEABLE",
                     "author": {"login": "mensch", "is_bot": False}}, **mehr)

    # Der Bestand vom 14.11.2026, wie GitHub ihn nannte.
    bestand = [
        vorschlag(1217, "2026-11-14T17:02:21Z", "2026-11-14T16:04:28Z"),
        vorschlag(1174, "2026-11-10T19:06:22Z"),
        vorschlag(1173, "2026-11-10T18:52:02Z", mergeable="CONFLICTING"),
        vorschlag(1171, "2026-11-11T12:57:39Z"),
        vorschlag(1167, "2026-11-11T12:47:41Z", "2026-11-10T09:00:00Z"),
    ]
    liegend = urteile(bestand, jetzt)
    pruefe("PB1 vier liegen, der frische nicht",
           [e["nummer"] for e in liegend], [1173, 1174, 1167, 1171])
    pruefe("PB2 Ruhe in ganzen Tagen", [e["ruhe_tage"] for e in liegend], [3, 3, 3, 3])
    pruefe("PB3 Alter ab Erstellung",
           {e["nummer"]: e["alter_tage"] for e in liegend}[1167], 4)
    pruefe("PB4 Konflikt wird genannt", zeile(liegend[0]),
           "#1173: seit 3 Tagen ohne Bewegung, offen seit 3 Tagen (Konflikt mit main)")
    pruefe("PB5 Kurztext Befund", kurztext(liegend, 5),
           "4 von 5 offenen seit 3 Tagen oder länger ohne Bewegung, "
           "ältester Stillstand 3 Tage (#1173)")

    # Grenze: genau die Ruhefrist zählt, eine Sekunde davor nicht.
    kante = jetzt - dt.timedelta(days=RUHE_TAGE)
    pruefe("PB6 genau an der Frist", len(urteile(
        [vorschlag(1, kante.strftime("%Y-%m-%dT%H:%M:%SZ"))], jetzt)), 1)
    knapp = kante + dt.timedelta(seconds=1)
    pruefe("PB7 eine Sekunde vor der Frist", urteile(
        [vorschlag(1, knapp.strftime("%Y-%m-%dT%H:%M:%SZ"))], jetzt), [])

    # Entwürfe und maschinell erzeugte Vorschläge zählen mit.
    sonder = urteile([
        vorschlag(7, "2026-11-01T00:00:00Z", isDraft=True),
        vorschlag(8, "2026-11-02T00:00:00Z",
                  author={"login": "app/dependabot", "is_bot": True}),
    ], jetzt)
    pruefe("PB8 Entwurf und Maschine zählen",
           [(e["nummer"], e["entwurf"], e["maschinell"]) for e in sonder],
           [(7, True, False), (8, False, True)])
    pruefe("PB9 Zusätze in der Zeile", zeile(sonder[1]),
           "#8: seit 12 Tagen ohne Bewegung, offen seit 12 Tagen (maschinell erzeugt)")

    # Leerer Bestand ist grün – aber nur, wenn er gemessen wurde.
    pruefe("PB10 leer ist grün", (urteile([], jetzt), kurztext([], 0)),
           ([], "0 offen, keiner seit 3 Tagen oder länger ohne Bewegung"))

    # Nicht messbar ist nie grün.
    wirft("PB11 kein JSON", lambda: aus_antwort("<html>"))
    wirft("PB12 keine Liste", lambda: aus_antwort('{"message": "Not Found"}'))
    wirft("PB13 Eintrag ohne Nummer", lambda: aus_antwort('[{"updatedAt": "x"}]'))
    wirft("PB14 Lesegrenze erreicht", lambda: aus_antwort(json.dumps(
        [vorschlag(n, "2026-11-14T00:00:00Z") for n in range(LESE_GRENZE)])))
    wirft("PB15 Zeitstempel unlesbar",
          lambda: urteile([vorschlag(1, "gestern")], jetzt))
    wirft("PB16 Zeitstempel fehlt",
          lambda: urteile([{"number": 1, "createdAt": "2026-11-01T00:00:00Z"}], jetzt))

    class Antwort:
        def __init__(self, code, aus="", fehl=""):
            self.returncode, self.stdout, self.stderr = code, aus, fehl

    gesehen: list[list[str]] = []

    def cli_ok(argv, **_):
        gesehen.append(list(argv))
        return Antwort(0, json.dumps(bestand))

    def cli_rot(argv, **_):
        return Antwort(4, "", "HTTP 403: Resource not accessible by integration")

    def cli_fehlt(argv, **_):
        raise FileNotFoundError("gh")

    messung = messe(jetzt, cli_ok)
    pruefe("PB17 Messung zählt alle", (messung["offen"], len(messung["liegend"])), (5, 4))
    pruefe("PB18 Aufruf ohne Shell, nur offene",
           gesehen[0][:5], ["gh", "pr", "list", "--state", "open"])
    wirft("PB19 CLI-Fehler ist nicht grün", lambda: messe(jetzt, cli_rot))
    wirft("PB20 CLI fehlt ist nicht grün", lambda: messe(jetzt, cli_fehlt))

    faelle[0] += 1
    try:
        urteile([], jetzt, ruhe_tage=0)
        fehler.append("PB21: Ruhefrist 0 wurde angenommen")
    except ValueError:
        pass

    if fehler:
        print("❌ Selbsttest PR-Bestands-Wache rot:")
        for f in fehler:
            print("   " + f)
        return 1
    print(f"✅ Selbsttest PR-Bestands-Wache: {faelle[0]} Fälle grün.")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    try:
        messung = messe()
    except NichtMessbar as grund:
        if "--json" in argv:
            print(json.dumps({"messbar": False, "grund": str(grund)},
                             ensure_ascii=False))
        else:
            print(f"⚠️ PR-Bestand nicht messbar: {grund}")
        return 2
    if "--json" in argv:
        print(json.dumps(dict(messung, messbar=True), ensure_ascii=False, indent=2))
    else:
        marke = "🟡" if messung["liegend"] else "✅"
        print(f"{marke} PR-Bestand: {messung['kurztext']}.")
        for eintrag in messung["liegend"]:
            print("   " + zeile(eintrag))
        if messung["liegend"]:
            print("   → " + NAECHSTER_SCHRITT)
    return 1 if messung["liegend"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
