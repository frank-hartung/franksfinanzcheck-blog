#!/usr/bin/env python3
"""Provisions-Tabelle: prüfen und zusammenfassen (Monatsaggregate je Partner).

Die Tabelle hält pro Monat und Partner nur Summen – keine Kundendaten, keine
Namen, keine Kontonummern. Die echte Datei liegt lokal unter
`data/provisionen/provisionen.csv` und ist per .gitignore aus Git herausgehalten
(das Repo ist öffentlich). Im Repo liegt nur die Vorlage
`data/provisionen/provisionen-vorlage.csv` (nur Kopfzeile).

Spalten (Pflicht, genau in dieser Reihenfolge):
  monat           YYYY-MM, nicht in der Zukunft
  partner         CHECK24 | Tarifcheck | C24 Bank | sonstig
  abschluesse     ganze Zahl >= 0 (vermittelte Abschlüsse im Monat)
  stornos         ganze Zahl >= 0 (Stornos, die im Monat gemeldet wurden)
  provision_eur   Dezimalpunkt, bis 2 Stellen, >= 0 (brutto, wie abgerechnet)
  abrechnung_ref  Verweis auf die Abrechnung (Nummer, nie der Name einer Person);
                  Pflicht, sobald provision_eur > 0
  notiz           frei, max. 200 Zeichen, ohne personenbezogene Angaben

Aufruf:
  python3 scripts/provisionen_check.py                  # prüfen (Standarddatei)
  python3 scripts/provisionen_check.py --summary        # Zusammenfassung
  python3 scripts/provisionen_check.py --datei PFAD     # andere Datei prüfen
  python3 scripts/provisionen_check.py --selftest       # Selbsttest

Exit: 0 = gültig oder noch keine Datei (Zustand „offen“), 1 = Fehler in der Tabelle,
      2 = Selbsttest rot. Runbook: docs/ANLEITUNG-PROVISIONEN.md
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD_DATEI = ROOT / "data" / "provisionen" / "provisionen.csv"

SPALTEN = ["monat", "partner", "abschluesse", "stornos", "provision_eur", "abrechnung_ref", "notiz"]
PARTNER = ("CHECK24", "Tarifcheck", "C24 Bank", "sonstig")
MONAT_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
GANZZAHL_RE = re.compile(r"^\d+$")
BETRAG_RE = re.compile(r"^\d+(\.\d{1,2})?$")
NOTIZ_MAX = 200

# Personenbezogenes erkennen, bevor es in eine öffentliche Datei gerät.
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}\b")  # mit oder ohne Leerzeichen
LANGE_ZAHL_RE = re.compile(r"\d{9,}")


def personenbezug(text: str) -> str | None:
    """Gibt den Befund zurück, wenn der Text nach Kontakt- oder Kontodaten aussieht."""
    if EMAIL_RE.search(text):
        return "E-Mail-Adresse"
    if IBAN_RE.search(text):
        return "IBAN-ähnliche Kontonummer"
    if LANGE_ZAHL_RE.search(text):
        return "lange Zahlenfolge (Konto- oder Vertragsnummer?)"
    return None


def heute_default() -> dt.date:
    return dt.date.today()


def pruefe_zeile(zeile: dict, zeilennr: int, heute: dt.date) -> list[str]:
    fehler: list[str] = []

    def f(text: str) -> None:
        fehler.append(f"Zeile {zeilennr}: {text}")

    monat = (zeile.get("monat") or "").strip()
    m = MONAT_RE.match(monat)
    if not m:
        f(f"monat „{monat}“ ist kein YYYY-MM")
    elif (int(m.group(1)), int(m.group(2))) > (heute.year, heute.month):
        f(f"monat {monat} liegt in der Zukunft")

    partner = (zeile.get("partner") or "").strip()
    if partner not in PARTNER:
        f(f"partner „{partner}“ unbekannt (erlaubt: {', '.join(PARTNER)})")

    for feld in ("abschluesse", "stornos"):
        wert = (zeile.get(feld) or "").strip()
        if not GANZZAHL_RE.match(wert):
            f(f"{feld} „{wert}“ ist keine ganze Zahl >= 0")

    betrag = (zeile.get("provision_eur") or "").strip()
    if not BETRAG_RE.match(betrag):
        f(f"provision_eur „{betrag}“: Dezimalpunkt, bis 2 Stellen, keine Tausendertrennung")
        betrag_wert = None
    else:
        betrag_wert = Decimal(betrag)

    ref = (zeile.get("abrechnung_ref") or "").strip()
    if betrag_wert and betrag_wert > 0 and not ref:
        f("abrechnung_ref fehlt, obwohl eine Provision gemeldet ist")
    for name, wert in (("abrechnung_ref", ref), ("notiz", (zeile.get("notiz") or "").strip())):
        befund = personenbezug(wert)
        if befund:
            f(f"{name} enthält {befund} – bitte ohne personenbezogene Angaben")
    notiz = (zeile.get("notiz") or "").strip()
    if len(notiz) > NOTIZ_MAX:
        f(f"notiz hat {len(notiz)} Zeichen (max. {NOTIZ_MAX})")
    return fehler


def pruefe_tabelle(zeilen: list[dict], heute: dt.date) -> list[str]:
    fehler: list[str] = []
    gesehen: set[tuple[str, str]] = set()
    for nr, zeile in enumerate(zeilen, start=2):  # Zeile 1 ist die Kopfzeile
        fehler.extend(pruefe_zeile(zeile, nr, heute))
        schluessel = ((zeile.get("monat") or "").strip(), (zeile.get("partner") or "").strip())
        if schluessel in gesehen:
            fehler.append(f"Zeile {nr}: doppelt – {schluessel[0]} / {schluessel[1]} gibt es schon")
        gesehen.add(schluessel)
    return fehler


def lese_text(text: str) -> tuple[list[dict], list[str]]:
    """CSV-Text lesen. Kopfzeile muss exakt SPALTEN sein (Reihenfolge zählt)."""
    leser = csv.reader(io.StringIO(text))
    try:
        kopf = next(leser)
    except StopIteration:
        return [], ["Datei ist leer – mindestens die Kopfzeile fehlt"]
    kopf = [k.strip() for k in kopf]
    if kopf != SPALTEN:
        return [], [f"Kopfzeile falsch: erwartet {','.join(SPALTEN)}, gefunden {','.join(kopf)}"]
    zeilen: list[dict] = []
    fehler: list[str] = []
    for nr, werte in enumerate(leser, start=2):
        if not any(w.strip() for w in werte):
            continue  # Leerzeilen sind erlaubt
        if len(werte) != len(SPALTEN):
            fehler.append(f"Zeile {nr}: {len(werte)} Felder statt {len(SPALTEN)} (Komma im Text? dann in „…“ setzen)")
            continue
        zeilen.append(dict(zip(SPALTEN, werte)))
    return zeilen, fehler


def pruefe_text(text: str, heute: dt.date) -> list[str]:
    zeilen, fehler = lese_text(text)
    if fehler:
        return fehler
    return pruefe_tabelle(zeilen, heute)


def _monate_zwischen(erster: str, letzter: str) -> list[str]:
    j, m = int(erster[:4]), int(erster[5:7])
    ende = (int(letzter[:4]), int(letzter[5:7]))
    out: list[str] = []
    while (j, m) <= ende:
        out.append(f"{j:04d}-{m:02d}")
        m += 1
        if m == 13:
            j, m = j + 1, 1
    return out


def zusammenfassung(zeilen: list[dict]) -> dict:
    """Summen je Partner, Gesamtsumme, Ø je Abschluss und Monate ohne jede Zeile."""
    je_partner: dict[str, dict] = {}
    monate: set[str] = set()
    for z in zeilen:
        p = z["partner"].strip()
        monate.add(z["monat"].strip())
        eintrag = je_partner.setdefault(p, {"abschluesse": 0, "stornos": 0, "provision": Decimal("0.00")})
        eintrag["abschluesse"] += int(z["abschluesse"])
        eintrag["stornos"] += int(z["stornos"])
        eintrag["provision"] += Decimal(z["provision_eur"])
    gesamt_abschluesse = sum(e["abschluesse"] for e in je_partner.values())
    gesamt_provision = sum((e["provision"] for e in je_partner.values()), Decimal("0.00"))
    luecken: list[str] = []
    if monate:
        luecken = [m for m in _monate_zwischen(min(monate), max(monate)) if m not in monate]
    return {
        "je_partner": je_partner,
        "abschluesse": gesamt_abschluesse,
        "provision": gesamt_provision,
        "schnitt_je_abschluss": (gesamt_provision / gesamt_abschluesse) if gesamt_abschluesse else None,
        "luecken": luecken,
        "zeilen": len(zeilen),
    }


def eur(betrag: Decimal) -> str:
    """Deutsche Schreibweise: 1.234,56 €"""
    text = f"{betrag:,.2f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".") + " €"


def drucke_zusammenfassung(z: dict) -> None:
    print("## Provisions-Zusammenfassung (Monatsaggregate)")
    if not z["zeilen"]:
        print("Datenlage offen: keine Zeilen erfasst.")
        return
    print(f"Zeilen: {z['zeilen']} · Abschlüsse: {z['abschluesse']} · Provision: {eur(z['provision'])}")
    if z["schnitt_je_abschluss"] is not None:
        print(f"Ø Provision je Abschluss: {eur(z['schnitt_je_abschluss'])}")
    print("")
    print("| Partner | Abschlüsse | Stornos | Provision |")
    print("|---|---:|---:|---:|")
    for name in sorted(z["je_partner"]):
        e = z["je_partner"][name]
        print(f"| {name} | {e['abschluesse']} | {e['stornos']} | {eur(e['provision'])} |")
    if z["luecken"]:
        print("")
        print("Monate ohne jede Zeile: " + ", ".join(z["luecken"]))


def selbsttest() -> list[str]:
    """Beweist zuerst, dass die Prüfung fängt, was sie fangen soll."""
    kopf = ",".join(SPALTEN) + "\n"
    heute = dt.date(2026, 10, 8)
    faelle: list[tuple[str, str, bool]] = [
        ("gültige Zeile", kopf + "2026-09,CHECK24,4,1,126.50,CHECK24-Abr-2026-09,Beispiel\n", True),
        ("Monat in der Zukunft", kopf + "2026-12,CHECK24,0,0,0,,\n", False),
        ("Monat falsch", kopf + "2026-13,CHECK24,0,0,0,,\n", False),
        ("unbekannter Partner", kopf + "2026-09,Irgendwer,1,0,0,,\n", False),
        ("Provision mit Komma", kopf + "2026-09,CHECK24,1,0,\"126,50\",CHECK24-Abr-1,\n", False),
        ("Provision ohne Abrechnung", kopf + "2026-09,CHECK24,1,0,10.00,,\n", False),
        ("negative Stornos", kopf + "2026-09,CHECK24,1,-1,0,,\n", False),
        ("doppelte Zeile", kopf + "2026-09,CHECK24,1,0,0,,\n2026-09,CHECK24,2,0,0,,\n", False),
        ("E-Mail in der Notiz", kopf + "2026-09,CHECK24,1,0,0,,max@example.de\n", False),
        ("IBAN in der Notiz", kopf + "2026-09,CHECK24,1,0,0,,DE89 3704 0044 0532 0130 00\n", False),
        ("falsche Kopfzeile", "monat,partner\n2026-09,CHECK24\n", False),
    ]
    fehlgeschlagen: list[str] = []
    for name, text, gueltig in faelle:
        ergebnis = pruefe_text(text, heute)
        if (not ergebnis) != gueltig:
            fehlgeschlagen.append(f"{name}: erwartet {'gültig' if gueltig else 'Fehler'}, Ergebnis {ergebnis}")
    # Zusammenfassung rechnet mit Cent-genauen Summen
    zeilen, _ = lese_text(kopf + "2026-08,CHECK24,2,0,10.10,CHECK24-1,\n2026-09,CHECK24,1,0,0.20,CHECK24-2,\n")
    z = zusammenfassung(zeilen)
    if z["provision"] != Decimal("10.30") or z["abschluesse"] != 3:
        fehlgeschlagen.append(f"Summen: erwartet 10,30 € / 3 Abschlüsse, bekommen {z['provision']} / {z['abschluesse']}")
    return fehlgeschlagen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--datei", type=Path, default=STANDARD_DATEI)
    parser.add_argument("--summary", action="store_true", help="Zusammenfassung ausgeben")
    parser.add_argument("--selftest", action="store_true", help="Selbsttest laufen lassen")
    parser.add_argument("--heute", help="Stichtag YYYY-MM-DD (nur für Tests)")
    args = parser.parse_args(argv)

    if args.selftest:
        fehler = selbsttest()
        if fehler:
            print("Selbsttest ROT:")
            for zeile in fehler:
                print(f"  - {zeile}")
            return 2
        print("Selbsttest grün.")
        return 0

    heute = dt.date.fromisoformat(args.heute) if args.heute else heute_default()
    if not args.datei.exists():
        print(f"Datenlage offen: {args.datei.relative_to(ROOT) if args.datei.is_relative_to(ROOT) else args.datei} fehlt noch.")
        print("Vorlage kopieren: cp data/provisionen/provisionen-vorlage.csv data/provisionen/provisionen.csv")
        return 0

    text = args.datei.read_text(encoding="utf-8")
    zeilen, fehler = lese_text(text)
    if not fehler:
        fehler = pruefe_tabelle(zeilen, heute)
    if fehler:
        print(f"{len(fehler)} Fehler in {args.datei.name}:")
        for zeile in fehler:
            print(f"  - {zeile}")
        return 1
    print(f"{args.datei.name}: gültig ({len(zeilen)} Zeilen).")
    if args.summary:
        drucke_zusammenfassung(zusammenfassung(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
