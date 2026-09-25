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

import argparse
import datetime as dt
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZEITZONE = ZoneInfo("Europe/Berlin")
VERSANDTAGE = (1, 4)  # datetime.weekday(): Dienstag, Freitag
RUECKBLICK_TAGE = 7    # überlappend; Artikel-Deduplizierung bleibt aktiv
MAX_PRO_WOCHE = 2

# Der planmäßige Termin in Berliner Zeit. Der Cron steht auf 04:30 UTC; das ist
# 06:30 MESZ und 05:30 MEZ – beide Angaben sind dasselbe Versprechen in zwei
# Zeitzonen-Schreibweisen. Gerechnet wird in Berliner Zeit, damit die Umstellung
# im März und im Oktober keine zweite Wahrheit erzeugt.
# 25.09.2026: 07:05 → 06:30 MESZ (Versandzeitpunkt-Optimierung, B2C-Frühpeak,
# siehe NEWSLETTER-VERSANDZEIT-0630-2026-09-25.md).
SEND_UHRZEIT = dt.time(6, 30)

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


def send_uhrzeit_utc() -> dt.time:
    """Der Termin in UTC (04:30) – gerechnet, nicht abgeschrieben.

    Der Cron steht auf 04:30 UTC. Wer die Berliner Uhrzeit daraus ableitet,
    statt sie zu notieren, hat nach der Zeitumstellung keine zweite Wahrheit.
    """
    sommer = dt.datetime.combine(dt.date(2026, 7, 1), SEND_UHRZEIT, ZEITZONE)
    return sommer.astimezone(dt.timezone.utc).time()


def send_uhrzeit_winter() -> dt.time:
    """Derselbe Termin in MEZ (05:30): UTC-Termin plus Winter-Versatz Berlins."""
    versatz = dt.datetime(2026, 1, 15, 12, 0, tzinfo=ZEITZONE).utcoffset()
    utc = dt.datetime.combine(dt.date(2026, 1, 15), send_uhrzeit_utc(),
                              dt.timezone.utc)
    return (utc + versatz).time()


def uhrzeit_zeile() -> str:
    """„morgens gegen 06:30 Uhr deutscher Zeit (05:30 Uhr im Winter)“."""
    return (f"morgens gegen {SEND_UHRZEIT:%H:%M} Uhr deutscher Zeit "
            f"({send_uhrzeit_winter():%H:%M} Uhr im Winter)")


def versandtage_oder_text() -> str:
    """„Dienstag oder Freitag“ – für Sätze über den NÄCHSTEN Termin."""
    return versandtage_text(" oder ")


def versandfenster_text() -> str:
    """Der vollständige Satz zum Versandversprechen (Site, Mail, Doku)."""
    return (f"{versandtage_adverb()}, {uhrzeit_zeile()} – höchstens zwei "
            "Ausgaben pro Kalenderwoche")


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


# ------------------------------------------------------- Website-Snapshot
# Die Website kann kein Python aufrufen. Damit sie dieselben FAKTEN nennt wie
# Versand, Wache und Doku (und nicht eine abgetippte vierte Fassung), schreibt
# dieser Vertrag einen Snapshot nach data/newsletter_kadenz.json:
#
#   python3 scripts/newsletter_schedule.py --export-site
#   python3 scripts/newsletter_schedule.py --pruefen-site   (Drift = Exit 1)
#
# Der Snapshot enthält bewusst KEIN Datum: ein „nächster Termin“ wäre am Tag
# nach dem Bau falsch, und eine Landingpage, die einen Termin von gestern
# ankündigt, ist ein gebrochenes Versprechen. Den nächsten Termin rechnet
# static/premium/ff-newsletter.js im Browser (Zeitzone Europe/Berlin); ohne
# JavaScript bleibt der kadenzrichtige Satz ohne Kalenderdatum stehen.
# Gelesen wird die Datei über layouts/_partials/newsletter_studio_data.html
# (os.ReadFile, NICHT site.Data – siehe Landmine im Kopf jener Datei).
SITE_KADENZ_REL = os.path.join("data", "newsletter_kadenz.json")


def kadenz_fuer_site() -> dict:
    """Die Fakten des Versandvertrags, wie die Website sie braucht."""
    return {
        "_doku": ("Snapshot des Versandvertrags für die Website – generiert von "
                  "`python3 scripts/newsletter_schedule.py --export-site`, nicht "
                  "handgepflegt. Drift prüft --pruefen-site bzw. "
                  "scripts/tests/test_newsletter_schedule.py. Enthält keine "
                  "Kalenderdaten: den nächsten Termin rechnet "
                  "static/premium/ff-newsletter.js in Europe/Berlin."),
        "max_pro_woche": MAX_PRO_WOCHE,
        "uhrzeit": f"{SEND_UHRZEIT:%H:%M}",
        "uhrzeit_winter": f"{send_uhrzeit_winter():%H:%M}",
        "uhrzeit_zeile": uhrzeit_zeile(),
        "versandtage_text": versandtage_text(),
        "versandtage_oder": versandtage_oder_text(),
        "versandtage_adverb": versandtage_adverb(),
        "versandfenster": versandfenster_text(),
        "tage": [
            {
                "schluessel": str(tag),
                "tag": WOCHENTAGE[tag],
                "tag_kurz": WOCHENTAGE[tag][:2],
                "adverb": WOCHENTAGE_ADVERB[tag],
            }
            for tag in VERSANDTAGE
        ],
    }


def site_kadenz_text() -> str:
    """Der Snapshot als Text – deterministisch, damit ein Diff nur Drift zeigt."""
    return json.dumps(kadenz_fuer_site(), ensure_ascii=False, indent=2) + "\n"


def site_kadenz_lesen(root: str = BLOG_DIR) -> str:
    pfad = os.path.join(root, SITE_KADENZ_REL)
    if not os.path.exists(pfad):
        return ""
    with open(pfad, encoding="utf-8") as fh:
        return fh.read()


def site_kadenz_schreiben(root: str = BLOG_DIR) -> str:
    """Schreibt den Snapshot und gibt den geschriebenen Text zurück."""
    pfad = os.path.join(root, SITE_KADENZ_REL)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    text = site_kadenz_text()
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Versandvertrag: Website-Snapshot schreiben oder prüfen.")
    parser.add_argument("--root", default=BLOG_DIR,
                        help="Repository-Wurzel (Default: dieses Repo)")
    parser.add_argument("--export-site", action="store_true",
                        help=f"{SITE_KADENZ_REL} aus dem Vertrag schreiben")
    parser.add_argument("--pruefen-site", action="store_true",
                        help="Abgleich: Datei == Vertrag (Exit 1 bei Drift)")
    args = parser.parse_args(argv)

    if args.export_site:
        site_kadenz_schreiben(args.root)
        print(f"{SITE_KADENZ_REL} geschrieben "
              f"({versandtage_text()}, {SEND_UHRZEIT:%H:%M} Uhr, "
              f"max. {MAX_PRO_WOCHE} pro Kalenderwoche)")
        return 0

    if args.pruefen_site:
        ist = site_kadenz_lesen(args.root)
        if not ist:
            print(f"Befund: {SITE_KADENZ_REL} fehlt – "
                  "`python3 scripts/newsletter_schedule.py --export-site`")
            return 1
        if ist != site_kadenz_text():
            print(f"Befund: {SITE_KADENZ_REL} weicht vom Versandvertrag ab – "
                  "`python3 scripts/newsletter_schedule.py --export-site`")
            return 1
        print(f"{SITE_KADENZ_REL} entspricht dem Versandvertrag "
              f"({versandtage_text()})")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
