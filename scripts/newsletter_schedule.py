"""Gemeinsamer Versandvertrag: Dienstag/Freitag, maximal zwei Ausgaben pro Woche.

Zeitzone Europe/Berlin; Bestätigungsmails und explizite Einzeltests sind keine
Newsletter-Ausgaben. Reservierte Termine zählen auch bei unklarem Ausgang.

Seit 23.09.2026 liegt hier auch der REDAKTIONSRAHMEN der beiden Termine: wie die
Versandtage heißen, wann die nächste Ausgabe fällt und wie beides im Text steht.
Website, Mail, Wache und Doku lesen dieselbe Stelle – vier Fassungen desselben
Versprechens sind der Anfang eines gebrochenen Versprechens.

LOCALE-FALLE (gemessen 23.09.2026): `strftime("%A")` liefert den Wochentagsnamen
der PROZESS-Locale. Auf GitHub-Runnern (en_US/C.UTF-8) steht dort „Tuesday“,
lokal je nach `LANG` mal so, mal so. Jede Bedingung der Form
`if tag == "Freitag"` läuft damit still ins Leere – genau das tat die
kadenzabhängige Betreffvariante des Studios: in CI hat sie nie ausgelöst. Namen,
die eine Entscheidung tragen, stehen deshalb als Tabelle in dieser Datei.
"""
from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

ZEITZONE = ZoneInfo("Europe/Berlin")
VERSANDTAGE = (1, 4)  # datetime.weekday(): Dienstag, Freitag
RUECKBLICK_TAGE = 7    # überlappend; Artikel-Deduplizierung bleibt aktiv
MAX_PRO_WOCHE = 2

# Der planmäßige Termin in Berliner Zeit. Der Cron steht auf 05:05 UTC; das ist
# 07:05 MESZ und 06:05 MEZ – beide Angaben sind dasselbe Versprechen in zwei
# Zeitzonen-Schreibweisen. Gerechnet wird in Berliner Zeit, damit die Umstellung
# im März und im Oktober keine zweite Wahrheit erzeugt.
SEND_UHRZEIT = dt.time(7, 5)

WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
              "Samstag", "Sonntag")
# Die Adverb-Form („dienstags“) – für Sätze, die eine Wiederholung meinen.
WOCHENTAGE_ADVERB = ("montags", "dienstags", "mittwochs", "donnerstags",
                     "freitags", "samstags", "sonntags")
MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember")


def jetzt() -> dt.datetime:
    return dt.datetime.now(ZEITZONE)


# --------------------------------------------------------------- Kalendertext
def _als_date(wert) -> dt.date:
    if isinstance(wert, dt.datetime):
        return wert.astimezone(ZEITZONE).date() if wert.tzinfo else wert.date()
    return wert


def wochentag(datum) -> str:
    """Locale-freier deutscher Wochentagsname („Dienstag“)."""
    return WOCHENTAGE[_als_date(datum).weekday()]


def tag_kurz(datum) -> str:
    """Die Zwei-Buchstaben-Form der Versandtage („Di“, „Fr“) – für Kopf und Betreff."""
    return wochentag(datum)[:2]


def datum_lang(datum, *, mit_jahr: bool = True) -> str:
    """„Dienstag, 23. September 2026“ – so verstehen Leser einen Termin.

    `mit_jahr=False` für Zeilen, in denen das Jahr Rauschen ist („Nächste
    Ausgabe: Freitag, 25. September“): gemeint ist immer der nächste Termin,
    nicht derselbe Tag in einem anderen Jahr.
    """
    d = _als_date(datum)
    basis = f"{wochentag(d)}, {d.day}. {MONATE[d.month - 1]}"
    return basis + (f" {d.year}" if mit_jahr else "")


def datum_kurz(datum) -> str:
    """„Di, 23.09.“ – die Form, die in eine Betreffzeile passt."""
    d = _als_date(datum)
    return f"{tag_kurz(d)}, {d.day:02d}.{d.month:02d}."


def ist_versandtag(datum) -> bool:
    return _als_date(datum).weekday() in VERSANDTAGE


def versandtage_text(und: str = " und ") -> str:
    """„Dienstag und Freitag“ – aus dem Vertrag, nicht abgetippt."""
    return und.join(WOCHENTAGE[t] for t in VERSANDTAGE)


def versandtage_adverb(und: str = " und ") -> str:
    """„dienstags und freitags“ – dieselbe Wahrheit als Wiederholung formuliert."""
    return und.join(WOCHENTAGE_ADVERB[t] for t in VERSANDTAGE)


def versandfenster_text() -> str:
    """Der vollständige Satz zum Versandversprechen (Site, Mail, Doku)."""
    return (f"{versandtage_adverb()}, morgens gegen "
            f"{SEND_UHRZEIT.strftime('%H:%M')} Uhr deutscher Zeit "
            "(06:05 Uhr im Winter) – höchstens zwei Ausgaben pro Kalenderwoche")


def naechster_termin(datum=None) -> dt.date:
    """Der nächste Versandtag NACH dem übergebenen Datum.

    Dienstags gefragt ist die Antwort Freitag, freitags gefragt Dienstag: eine
    Ausgabe kündigt nie sich selbst als „nächste“ an.
    """
    start = _als_date(datum or jetzt().date())
    for schritt in range(1, 8):
        kandidat = start + dt.timedelta(days=schritt)
        if kandidat.weekday() in VERSANDTAGE:
            return kandidat
    raise AssertionError("sieben Tage ohne Versandtag – Kalendervertrag verletzt")


def datum_lang_erkennen(text: str):
    """„Dienstag, 23. September 2026“ zurück in ein Datum – oder None.

    Die Wache braucht das, um eine gedruckte Terminzeile gegen den Vertrag zu
    prüfen: eine „Nächste Ausgabe: Mittwoch, …“ ist ein Fund, keine Meinung.
    Ohne Jahreszahl gilt das Jahr des genannten Tages nicht – dann liefert die
    Funktion nur Monat und Tag (`jahr` ist None), und der Aufrufer prüft, was
    prüfbar ist.
    """
    m = re.search(
        r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),\s*"
        r"(\d{1,2})\.\s*(Januar|Februar|M[aä]rz|April|Mai|Juni|Juli|August|"
        r"September|Oktober|November|Dezember)(?:\s*(\d{4}))?", text or "")
    if not m:
        return None
    tag_name, tag, monat_name, jahr = m.groups()
    return {"wochentag": tag_name, "tag": int(tag),
            "monat": MONATE.index(monat_name) + 1,
            "jahr": int(jahr) if jahr else None}


def naechste_ausgabe_text(datum=None) -> str:
    """„Nächste Ausgabe: Freitag, 26. September“ – Erwartung statt Funkstille."""
    return f"Nächste Ausgabe: {datum_lang(naechster_termin(datum), mit_jahr=False)}"


# ------------------------------------------------------------------ Freigabe
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
        return f"Versandpause: Newsletter erscheinen nur {versandtage_adverb()}."
    if any(t.date() == zeit.date() for t in termine):
        return "Versandpause: der heutige Versandtermin ist bereits belegt."
    woche = zeit.isocalendar()[:2]
    if sum(t.isocalendar()[:2] == woche for t in termine) >= MAX_PRO_WOCHE:
        return "Versandpause: maximal zwei Newsletter pro Kalenderwoche."
    return ""
