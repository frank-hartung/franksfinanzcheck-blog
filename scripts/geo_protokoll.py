#!/usr/bin/env python3
"""GEO-Protokoll: wird franksfinanzcheck.de in KI-Antworten genannt oder zitiert?

Monatliche, MANUELLE Stichprobe: 10 feste Fragen × 3 Antwort-Oberflächen. Die
Ergebnisse trägt ein Mensch in die CSV ein. Das Skript automatisiert keine
Chat-Oberflächen (Nutzungsbedingungen, Verlässlichkeit) und fragt keine Dienste
per API ab. Perplexity ist bewusst nicht dabei (CLAUDE.md, Abschnitt Werkbank).

Spalten (Reihenfolge fest):
  frage_id       F01 … F10 (feste Fragen, siehe FRAGEN)
  frage          Wortlaut der Frage (aus FRAGEN, nicht frei ändern)
  engine         chatgpt-free | gemini-free | google-ki-uebersicht
  datum          YYYY-MM-DD, im Monat der Datei (Tag der Abfrage)
  genannt        ja | nein            (Marke oder Domain im Antworttext)
  position       ganze Zahl ≥ 1, nur bei genannt=ja (Rang der Nennung)
  zitiert        ja | nein            (Domain als Quelle/Link angezeigt)
  quelle_url     nur bei zitiert=ja: https-URL auf franksfinanzcheck.de
  notiz          frei, max. 200 Zeichen, ohne E-Mail-Adressen

Aufruf:
  python3 scripts/geo_protokoll.py --neu 2026-10        # Erfassungsdatei anlegen
  python3 scripts/geo_protokoll.py --pruefen            # neueste Datei prüfen
  python3 scripts/geo_protokoll.py --auswerten          # Quoten je Engine (Markdown)
  python3 scripts/geo_protokoll.py --selftest

Exit: 0 = ok (offene Zeilen sind kein Fehler), 1 = Fehler, 2 = Selbsttest rot.
Runbook: docs/ANLEITUNG-GEO-PROTOKOLL.md
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ORDNER = ROOT / "data" / "geo"

SPALTEN = ["frage_id", "frage", "engine", "datum", "genannt", "position", "zitiert", "quelle_url", "notiz"]
ENGINES = ("chatgpt-free", "gemini-free", "google-ki-uebersicht")
FRAGEN = (
    ("F01", "Welches Girokonto ist ohne Grundgebühr sinnvoll?"),
    ("F02", "Wie finde ich eine gute Kreditkarte ohne Jahresgebühr?"),
    ("F03", "Wie rechne ich den Effektivpreis eines DSL-Wechselbonus richtig aus?"),
    ("F04", "Wie spare ich beim Internetvertrag, ohne den Tarif zu verschlechtern?"),
    ("F05", "Wie erkenne ich einen guten Stromtarif ohne Lockangebote?"),
    ("F06", "Was bringt ein Anbieterwechsel beim Strom in der Praxis?"),
    ("F07", "Wie erstelle ich ein Haushaltsbudget, das ich auch durchhalte?"),
    ("F08", "Brauche ich eine Haftpflichtversicherung, und worauf achte ich beim Tarif?"),
    ("F09", "Wie spare ich beim Mietwagen, ohne Versicherungsfallen zu übersehen?"),
    ("F10", "Lohnt sich ein Tagesgeldkonto, und wie prüfe ich den Zins richtig?"),
)
DOMAINS = ("franksfinanzcheck.de", "www.franksfinanzcheck.de")
MONAT_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATEI_RE = re.compile(r"^protokoll-(\d{4}-(?:0[1-9]|1[0-2]))\.csv$")
NOTIZ_MAX = 200


def leere_zeilen(monat: str) -> list[dict]:
    """30 Zeilen: jede Frage × jede Engine, alles offen."""
    zeilen = []
    for fid, frage in FRAGEN:
        for engine in ENGINES:
            zeilen.append({"frage_id": fid, "frage": frage, "engine": engine, "datum": "", "genannt": "",
                           "position": "", "zitiert": "", "quelle_url": "", "notiz": ""})
    return zeilen


def schreibe_csv(pfad: Path, zeilen: list[dict]) -> None:
    puffer = io.StringIO()
    schreiber = csv.DictWriter(puffer, fieldnames=SPALTEN, lineterminator="\n")
    schreiber.writeheader()
    schreiber.writerows(zeilen)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(puffer.getvalue(), encoding="utf-8")


def lese_csv(pfad: Path) -> tuple[list[dict], list[str]]:
    text = pfad.read_text(encoding="utf-8")
    leser = csv.reader(io.StringIO(text))
    try:
        kopf = [k.strip() for k in next(leser)]
    except StopIteration:
        return [], ["Datei ist leer"]
    if kopf != SPALTEN:
        return [], [f"Kopfzeile falsch: erwartet {','.join(SPALTEN)}"]
    zeilen, fehler = [], []
    for nr, werte in enumerate(leser, start=2):
        if not any(w.strip() for w in werte):
            continue
        if len(werte) != len(SPALTEN):
            fehler.append(f"Zeile {nr}: {len(werte)} Felder statt {len(SPALTEN)}")
            continue
        zeilen.append({k: v.strip() for k, v in zip(SPALTEN, werte)})
    return zeilen, fehler


def ist_offen(z: dict) -> bool:
    return not z["genannt"] and not z["datum"]


def url_ist_eigene_seite(url: str) -> bool:
    p = urlparse(url)
    return p.scheme == "https" and p.netloc.lower() in DOMAINS and not p.username and not p.password


def pruefe(zeilen: list[dict], monat: str) -> list[str]:
    fehler: list[str] = []
    erwartet = {(fid, eng) for fid, _ in FRAGEN for eng in ENGINES}
    gesehen: set[tuple[str, str]] = set()
    fragen_text = dict(FRAGEN)
    for nr, z in enumerate(zeilen, start=2):
        schluessel = (z["frage_id"], z["engine"])
        if schluessel not in erwartet:
            fehler.append(f"Zeile {nr}: unbekannte Kombination {z['frage_id']} / {z['engine']}")
            continue
        if schluessel in gesehen:
            fehler.append(f"Zeile {nr}: doppelt – {z['frage_id']} / {z['engine']}")
        gesehen.add(schluessel)
        if z["frage"] != fragen_text[z["frage_id"]]:
            fehler.append(f"Zeile {nr}: Fragetext weicht von der festen Frage ab")
        if ist_offen(z):
            continue  # noch nicht erfasst – kein Fehler
        if z["datum"]:
            try:
                d = dt.date.fromisoformat(z["datum"])
                if f"{d.year:04d}-{d.month:02d}" != monat:
                    fehler.append(f"Zeile {nr}: datum {z['datum']} liegt nicht im Monat {monat}")
            except ValueError:
                fehler.append(f"Zeile {nr}: datum „{z['datum']}“ ist kein YYYY-MM-DD")
        else:
            fehler.append(f"Zeile {nr}: datum fehlt, obwohl erfasst")
        if z["genannt"] not in ("ja", "nein"):
            fehler.append(f"Zeile {nr}: genannt muss ja oder nein sein")
            continue
        if z["zitiert"] not in ("ja", "nein"):
            fehler.append(f"Zeile {nr}: zitiert muss ja oder nein sein")
        if z["genannt"] == "ja":
            if not z["position"].isdigit() or int(z["position"]) < 1:
                fehler.append(f"Zeile {nr}: position muss eine Zahl ≥ 1 sein, wenn genannt=ja")
        elif z["position"]:
            fehler.append(f"Zeile {nr}: position nur bei genannt=ja")
        if z["zitiert"] == "ja":
            if z["genannt"] != "ja":
                fehler.append(f"Zeile {nr}: zitiert=ja setzt genannt=ja voraus")
            if not z["quelle_url"]:
                fehler.append(f"Zeile {nr}: zitiert=ja braucht quelle_url")
            elif not url_ist_eigene_seite(z["quelle_url"]):
                fehler.append(f"Zeile {nr}: quelle_url muss eine https-URL auf franksfinanzcheck.de sein")
        elif z["quelle_url"]:
            fehler.append(f"Zeile {nr}: quelle_url nur bei zitiert=ja")
        if len(z["notiz"]) > NOTIZ_MAX:
            fehler.append(f"Zeile {nr}: notiz hat {len(z['notiz'])} Zeichen (max. {NOTIZ_MAX})")
        if "@" in z["notiz"]:
            fehler.append(f"Zeile {nr}: notiz enthält eine E-Mail-Adresse – bitte entfernen")
    for fid, eng in sorted(erwartet - gesehen):
        fehler.append(f"Zeile fehlt: {fid} / {eng}")
    return fehler


def auswerten(zeilen: list[dict]) -> str:
    zeilen_out = ["| Engine | erfasst | genannt | zitiert | Ø Position (wenn genannt) |", "|---|---:|---:|---:|---:|"]
    for eng in ENGINES:
        erfasst = [z for z in zeilen if z["engine"] == eng and z["genannt"] in ("ja", "nein")]
        n = len(erfasst)
        if n == 0:
            zeilen_out.append(f"| {eng} | 0 von {len(FRAGEN)} | – | – | – |")
            continue
        genannt = [z for z in erfasst if z["genannt"] == "ja"]
        zitiert = [z for z in erfasst if z["zitiert"] == "ja"]
        pos = [int(z["position"]) for z in genannt if z["position"].isdigit()]
        q_g = f"{len(genannt)} von {n} ({100 * len(genannt) // n} %)"
        q_z = f"{len(zitiert)} von {n} ({100 * len(zitiert) // n} %)"
        q_p = f"{sum(pos) / len(pos):.1f}" if pos else "–"
        zeilen_out.append(f"| {eng} | {n} von {len(FRAGEN)} | {q_g} | {q_z} | {q_p} |")
    return "\n".join(zeilen_out)


def neueste_datei() -> Path | None:
    kandidaten = sorted(p for p in ORDNER.glob("protokoll-*.csv") if DATEI_RE.match(p.name))
    return kandidaten[-1] if kandidaten else None


def monat_aus_datei(pfad: Path) -> str | None:
    m = DATEI_RE.match(pfad.name)
    return m.group(1) if m else None


# ---------------------------------------------------------------- Selbsttest
def selbsttest() -> list[str]:
    fehler: list[str] = []
    monat = "2026-10"
    basis = leere_zeilen(monat)

    def zeile(index: int, **kw) -> list[dict]:
        z = [dict(x) for x in basis]
        z[index].update(kw)
        return z

    tag = "2026-10-05"
    faelle = [
        ("leer ist gültig", basis, True),
        ("gut erfasst", zeile(0, datum=tag, genannt="ja", position="2", zitiert="ja", quelle_url="https://franksfinanzcheck.de/konto/"), True),
        ("nicht genannt", zeile(0, datum=tag, genannt="nein", zitiert="nein"), True),
        ("datum im falschen Monat", zeile(0, datum="2026-09-30", genannt="nein", zitiert="nein"), False),
        ("datum kaputt", zeile(0, datum="05.10.2026", genannt="nein"), False),
        ("genannt ohne Wert", zeile(0, datum=tag, genannt="vielleicht"), False),
        ("position ohne genannt", zeile(0, datum=tag, genannt="nein", zitiert="nein", position="1"), False),
        ("genannt ohne position", zeile(0, datum=tag, genannt="ja"), False),
        ("zitiert ohne genannt", zeile(0, datum=tag, genannt="nein", zitiert="ja", quelle_url="https://franksfinanzcheck.de/"), False),
        ("zitiert ohne URL", zeile(0, datum=tag, genannt="ja", position="1", zitiert="ja"), False),
        ("fremde Domain", zeile(0, datum=tag, genannt="ja", position="1", zitiert="ja", quelle_url="https://example.com/x"), False),
        ("http statt https", zeile(0, datum=tag, genannt="ja", position="1", zitiert="ja", quelle_url="http://franksfinanzcheck.de/x"), False),
        ("URL nur bei zitiert=ja", zeile(0, datum=tag, genannt="ja", position="1", zitiert="nein", quelle_url="https://franksfinanzcheck.de/x"), False),
        ("Frage verändert", zeile(0, frage="Andere Frage?"), False),
        ("Zeile fehlt", basis[1:], False),
        ("E-Mail in Notiz", zeile(0, datum=tag, genannt="nein", zitiert="nein", notiz="max@example.de"), False),
    ]
    for name, zeilen, gueltig in faelle:
        ergebnis = pruefe(zeilen, monat)
        if (not ergebnis) != gueltig:
            fehler.append(f"{name}: erwartet {'gültig' if gueltig else 'Fehler'}, Ergebnis {ergebnis[:2]}")

    # Auswertung: chatgpt-free hat drei erfasste Fragen (F01 ja/Pos 1/zitiert,
    # F02 ja/Pos 3, F03 nein) → 2 von 3 genannt, 1 von 3 zitiert, Ø Position 2.0
    z = [dict(x) for x in basis]
    z[0].update(datum=tag, genannt="ja", position="1", zitiert="ja", quelle_url="https://franksfinanzcheck.de/a")
    z[3].update(datum=tag, genannt="ja", position="3", zitiert="nein")
    z[6].update(datum=tag, genannt="nein", zitiert="nein")
    if pruefe(z, monat):
        fehler.append(f"Auswertungsdaten sind selbst ungültig: {pruefe(z, monat)[:2]}")
    tabelle = auswerten(z)
    erwartet = "| chatgpt-free | 3 von 10 | 2 von 3 (66 %) | 1 von 3 (33 %) | 2.0 |"
    if erwartet not in tabelle:
        fehler.append(f"Auswertung: erwartet „{erwartet}“, Tabelle war:\n{tabelle}")
    if "| gemini-free | 0 von 10 |" not in tabelle:
        fehler.append("Auswertung: leere Engine muss „0 von 10“ zeigen")
    return fehler


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--neu", metavar="JJJJ-MM", help="Erfassungsdatei für den Monat anlegen")
    parser.add_argument("--pruefen", action="store_true")
    parser.add_argument("--auswerten", action="store_true")
    parser.add_argument("--datei", type=Path, help="statt der neuesten Datei")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        fehler = selbsttest()
        if fehler:
            print("Selbsttest ROT:")
            for f in fehler:
                print(f"  - {f}")
            return 2
        print("Selbsttest grün.")
        return 0

    if args.neu:
        if not MONAT_RE.match(args.neu):
            print("Monat muss JJJJ-MM sein, zum Beispiel 2026-10.")
            return 1
        ziel = ORDNER / f"protokoll-{args.neu}.csv"
        if ziel.exists():
            print(f"{ziel.name} existiert schon – nichts überschrieben.")
            return 1
        schreibe_csv(ziel, leere_zeilen(args.neu))
        print(f"Angelegt: data/geo/{ziel.name} (30 Zeilen: 10 Fragen × 3 Engines, alle offen).")
        return 0

    pfad = args.datei or neueste_datei()
    if pfad is None:
        print("Datenlage offen: noch keine Erfassungsdatei. Anlegen mit --neu JJJJ-MM.")
        return 0
    monat = monat_aus_datei(pfad)
    if not monat:
        print(f"{pfad.name}: Dateiname muss protokoll-JJJJ-MM.csv heißen.")
        return 1
    zeilen, fehler = lese_csv(pfad)
    if not fehler:
        fehler = pruefe(zeilen, monat)
    offen = sum(1 for z in zeilen if ist_offen(z))

    if args.auswerten:
        if fehler:
            print(f"{len(fehler)} Fehler – Auswertung nur für geprüfte Dateien:")
            for f in fehler:
                print(f"  - {f}")
            return 1
        print(f"## GEO-Protokoll {monat} (offen: {offen} von {len(zeilen)})\n")
        print(auswerten(zeilen))
        return 0

    if fehler:
        print(f"{len(fehler)} Fehler in {pfad.name}:")
        for f in fehler:
            print(f"  - {f}")
        return 1
    print(f"{pfad.name}: gültig ({len(zeilen) - offen} erfasst, {offen} offen).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
