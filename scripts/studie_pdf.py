#!/usr/bin/env python3
"""studie_pdf.py – erzeugt das zitierfähige Ein-Seiter-PDF einer Studie.

WARUM DIESES WERKZEUG EXISTIERT (26.10.2026)
--------------------------------------------
Die Studienseite `/studien/fixkosten-index-2026-q4/` versprach seit dem
02.10.2026 einen „PDF-Download: Vollständige Methodik + Rechnung (1 Seite)"
und verlinkte `/downloads/fixkosten-index-2026-q4.pdf`. Die Datei wurde nie
erzeugt. Aufgefallen ist das erst dem Layout-Audit als kaputter interner Link
– also nach Wochen, in denen Redaktionen und KI-Suchmaschinen auf einen
404-Download gestoßen sind. Ein Versprechen im Fließtext ist keine Datei.

Das PDF wird deshalb aus der veröffentlichten DATENQUELLE gebaut, nicht aus
einem zweiten Zahlenstand: Grundlage ist der CSV-Datensatz der Studie. Das
Werkzeug rechnet die Summe und den Monatswert nach und bricht ab, wenn die
Quelle in sich widersprüchlich ist (fail-closed, kein hübsches PDF über
falschen Zahlen).

Aufruf:
  python3 scripts/studie_pdf.py \
      --csv static/downloads/fixkosten-index-2026-q4.csv \
      --out static/downloads/fixkosten-index-2026-q4.pdf
  python3 scripts/studie_pdf.py --selftest      # offline, ohne Datei-Ausgabe

Exit: 0 = PDF geschrieben · 1 = Daten widersprüchlich · 2 = Werkzeug fehlt
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TITEL = "Fixkosten-Index Deutschland: Energie-Baseline Q4 2026"
AUTOR = "Frank Hartung · FranksFinanzcheck"
QUELLENZEILE = ("FranksFinanzcheck, „Fixkosten-Index Deutschland: Energie-Baseline "
                "Q4 2026“, veröffentlicht am 2. Oktober 2026, basierend auf "
                "BDEW-Preisanalysen.")
GRENZEN = (
    "Das Modell bildet Strom und Gas ab – nicht Miete, Internet, Mobilität "
    "oder Versicherungen. Die Verbrauchswerte sind Szenarioannahmen, keine "
    "Aussage über einen Durchschnittshaushalt. Grundpreis, Bonus, Region und "
    "Heizart verändern den individuellen Betrag. Der Wert ist keine Prognose "
    "und kein Tarifangebot."
)


def lade_csv(pfad: Path) -> list[dict]:
    with pfad.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pruefe_daten(zeilen: list[dict]) -> list[tuple[str, str, str, str]]:
    """Rechnet die Quelle nach. Rückgabe: Zeilen für die Tabelle.

    Wirft ValueError, wenn Summe oder Monatswert nicht zur Quelle passen –
    ein PDF mit stillschweigend „geglätteten“ Zahlen wäre schlimmer als keins.
    """
    if len(zeilen) < 3:
        raise ValueError("CSV braucht mindestens Strom-, Gas- und Summenzeile")
    einzel = [z for z in zeilen if z["segment"] != "Energie gesamt"]
    summe = next((z for z in zeilen if z["segment"] == "Energie gesamt"), None)
    if summe is None:
        raise ValueError("CSV ohne Summenzeile – keine Gegenprobe möglich")
    jahres = round(sum(float(z["annual_cost_eur"]) for z in einzel), 2)
    if abs(jahres - float(summe["annual_cost_eur"])) > 0.005:
        raise ValueError(
            f"Summe widersprüchlich: Einzel {jahres:.2f} ≠ gesamt "
            f"{summe['annual_cost_eur']}")
    monat = round(jahres / 12, 2)
    if abs(monat - float(summe["monthly_cost_eur"])) > 0.005:
        raise ValueError(
            f"Monatswert widersprüchlich: {monat:.2f} ≠ "
            f"{summe['monthly_cost_eur']}")
    return [(z["segment"], z["assumption"], z["unit_price"], z["annual_cost_eur"])
            for z in zeilen]


def _datum(iso: str) -> str:
    """ISO-Datum → deutsches Zitierformat (2026-09-28 → 28.09.2026)."""
    teile = (iso or "").split("-")
    return ".".join(reversed(teile)) if len(teile) == 3 else (iso or "–")


def _euro(wert: str) -> str:
    return f"{float(wert):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def schreibe_pdf(ziel: Path, zeilen: list[dict]) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                        TableStyle)
    except ImportError as exc:  # pragma: no cover - Build-Umgebung ohne reportlab
        raise SystemExit(f"reportlab fehlt: {exc}") from exc

    tabelle = pruefe_daten(zeilen)
    summe = next(z for z in zeilen if z["segment"] == "Energie gesamt")

    styles = getSampleStyleSheet()
    klein = ParagraphStyle("klein", parent=styles["BodyText"], fontSize=9,
                           leading=12)
    titel = ParagraphStyle("titel", parent=styles["Title"], fontSize=16,
                           leading=19, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11,
                        spaceBefore=8, spaceAfter=4)

    story = [
        Paragraph(TITEL, titel),
        Paragraph(f"{AUTOR} · Datenstand {_datum(zeilen[0]['source_checked'])} · "
                  f"Version 1.0 · Lizenz: Nutzung mit Quellenzeile", klein),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>{_euro(summe['annual_cost_eur'])} Euro pro Jahr</b> – "
                  f"{_euro(summe['monthly_cost_eur'])} Euro pro Monat für Strom "
                  "und Gas im definierten Modell. Reproduzierbare Planungsgröße "
                  "aus veröffentlichten Preisständen, kein Tarifpreis.", klein),
        Paragraph("Rechnung", h2),
    ]

    daten = [["Baustein", "Annahme", "Preis (EUR/Einheit)", "Kosten/Jahr (EUR)"]]
    for segment, annahme, preis, kosten in tabelle:
        daten.append([segment, annahme, preis.replace(".", ","), _euro(kosten)])
    table = Table(daten, colWidths=[32 * mm, 62 * mm, 34 * mm, 34 * mm])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, (0.6, 0.6, 0.6)),
        ("BACKGROUND", (0, 0), (-1, 0), (0.93, 0.95, 0.97)),
    ]))
    story += [table, Spacer(1, 4 * mm)]

    for zeile in [z for z in zeilen if z["segment"] != "Energie gesamt"]:
        story.append(Paragraph(
            f"{zeile['segment']}: {zeile['assumption']} × "
            f"{zeile['unit_price'].replace('.', ',')} {zeile['unit']} = "
            f"{_euro(zeile['annual_cost_eur'])} Euro", klein))
    story.append(Paragraph(
        f"Summe: {_euro(summe['annual_cost_eur'])} Euro · Monatswert: "
        f"{_euro(summe['annual_cost_eur'])} ÷ 12 = "
        f"{_euro(summe['monthly_cost_eur'])} Euro", klein))

    story += [Paragraph("Quellen", h2)]
    for zeile in [z for z in zeilen if z["segment"] != "Energie gesamt"]:
        story.append(Paragraph(
            f"{zeile['source']} – geprüft am {_datum(zeile['source_checked'])}: "
            f"{zeile['source_url']}", klein))
    story += [
        Paragraph("Grenzen der Aussage", h2),
        Paragraph(GRENZEN, klein),
        Paragraph("Zitierweise", h2),
        Paragraph(QUELLENZEILE, klein),
        Paragraph("Vollständige Methodik, Änderungsprotokoll und "
                  "Maschinenlesbarkeit: "
                  "https://franksfinanzcheck.de/studien/fixkosten-index-2026-q4/",
                  klein),
    ]

    ziel.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(ziel), pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title=TITEL, author="Frank Hartung",
                            subject="Fixkosten-Index Deutschland, Energie-Baseline Q4 2026")
    doc.build(story)


def selftest() -> int:
    zeilen = [
        {"segment": "Strom", "assumption": "2500 kWh", "unit_price": "0.3700",
         "unit": "EUR/kWh", "annual_cost_eur": "925.00",
         "monthly_cost_eur": "77.08", "source": "A", "source_url": "https://a",
         "source_checked": "2026-09-28"},
        {"segment": "Gas", "assumption": "12000 kWh", "unit_price": "0.1193",
         "unit": "EUR/kWh", "annual_cost_eur": "1431.60",
         "monthly_cost_eur": "119.30", "source": "B", "source_url": "https://b",
         "source_checked": "2026-09-28"},
        {"segment": "Energie gesamt", "assumption": "Summe", "unit_price": "",
         "unit": "", "annual_cost_eur": "2356.60",
         "monthly_cost_eur": "196.38", "source": "eigene Rechnung",
         "source_url": "https://c", "source_checked": "2026-10-02"},
    ]
    fehler = []
    try:
        pruefe_daten(zeilen)
    except ValueError as exc:
        fehler.append(f"gültige Daten abgelehnt: {exc}")

    def falsch(feld: str, wert: str):
        kopie = [dict(z) for z in zeilen]
        kopie[2][feld] = wert
        try:
            pruefe_daten(kopie)
        except ValueError:
            return True
        return False

    if not falsch("annual_cost_eur", "2400.00"):
        fehler.append("widersprüchliche Summe wird nicht erkannt")
    if not falsch("monthly_cost_eur", "200.00"):
        fehler.append("widersprüchlicher Monatswert wird nicht erkannt")
    if len(pruefe_daten(zeilen)) != 3:
        fehler.append("Tabellenzeilen unvollständig")
    if fehler:
        print("❌ studie_pdf-Selbsttest fehlgeschlagen:")
        for eintrag in fehler:
            print("   -", eintrag)
        return 2
    print("✅ studie_pdf: Quellen-Gegenprobe, Summen- und Monatsprüfung grün.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Studien-PDF aus der Datenquelle bauen")
    parser.add_argument("--csv", type=Path,
                        default=ROOT / "static/downloads/fixkosten-index-2026-q4.csv")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "static/downloads/fixkosten-index-2026-q4.pdf")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.csv.is_file():
        print(f"🛑 Datenquelle fehlt: {args.csv}")
        return 1
    zeilen = lade_csv(args.csv)
    try:
        schreibe_pdf(args.out, zeilen)
    except ValueError as exc:
        print(f"🛑 Daten widersprüchlich – kein PDF geschrieben: {exc}")
        return 1
    print(f"✅ PDF geschrieben: {args.out.relative_to(ROOT)} "
          f"({args.out.stat().st_size} Bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
