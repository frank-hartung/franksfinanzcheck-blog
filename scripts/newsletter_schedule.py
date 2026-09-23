"""Gemeinsamer Versandvertrag: Dienstag/Freitag, maximal zwei Ausgaben pro Woche.

Zeitzone Europe/Berlin; Bestätigungsmails und explizite Einzeltests sind keine
Newsletter-Ausgaben. Reservierte Termine zählen auch bei unklarem Ausgang.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

ZEITZONE = ZoneInfo("Europe/Berlin")
VERSANDTAGE = (1, 4)  # datetime.weekday(): Dienstag, Freitag
RUECKBLICK_TAGE = 7    # überlappend; Artikel-Deduplizierung bleibt aktiv
MAX_PRO_WOCHE = 2


def jetzt() -> dt.datetime:
    return dt.datetime.now(ZEITZONE)


def versandpause(state: dict, zeit: dt.datetime | None = None) -> str:
    """Leer = erlaubt. Ungültige Historie sperrt statt den Zähler zurückzusetzen."""
    zeit = (zeit or jetzt()).astimezone(ZEITZONE)
    if not isinstance(state, dict):
        raise ValueError("Versandstatus ist kein Objekt")
    historie = state.get("versand_termine", [])
    if not isinstance(historie, list):
        raise ValueError("Versandhistorie ist keine Liste")
    termine = []
    for wert in historie:
        datum = dt.datetime.fromisoformat(wert.replace("Z", "+00:00"))
        if datum.tzinfo is None:
            raise ValueError("Versandtermin ohne Zeitzone")
        termine.append(datum.astimezone(ZEITZONE))
    # Konservative Migration: der alte Zeitstempel könnte auch ein Test sein.
    if "versand_termine" not in state and state.get("zuletzt_versandt"):
        alt = dict(state, versand_termine=[state["zuletzt_versandt"]])
        return versandpause(alt, zeit)
    if any(t > zeit for t in termine):
        raise ValueError("Versandtermin liegt in der Zukunft")
    if zeit.weekday() not in VERSANDTAGE:
        return "Versandpause: Newsletter erscheinen nur dienstags und freitags."
    if any(t.date() == zeit.date() for t in termine):
        return "Versandpause: der heutige Versandtermin ist bereits belegt."
    woche = zeit.isocalendar()[:2]
    if sum(t.isocalendar()[:2] == woche for t in termine) >= MAX_PRO_WOCHE:
        return "Versandpause: maximal zwei Newsletter pro Kalenderwoche."
    return ""
