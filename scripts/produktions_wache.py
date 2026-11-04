#!/usr/bin/env python3
# ============================================================
#  PRODUKTIONS-WACHE – Bewertung der Content-Engine (P1/P2/WARTEND)
#  ------------------------------------------------------------
#  AUFRUF: python3 scripts/produktions_wache.py --selftest
#
#  WARUM DIESES MODUL (Vorgang #1054, 04.11.2026)
#  Der Plan-Lauf der Produktions-Wache (Cron 20:00 UTC) wurde von
#  GitHub um Stunden verzögert und lief erst um 00:32 UTC des
#  FOLGETAGS. Die Bewertung stand bis dahin als Heredoc im Workflow
#  und kannte den Fall nicht: Sie las `date.today()` des neuen Tags
#  (Mittwoch, Publikationstag, 0 Artikel) und meldete P1 mit dem
#  Text „alle Slots vorbei“ – obwohl an diesem Tag noch kein einziger
#  Slot (06:10/14:10/17:40 UTC) gelaufen war; die Slot-Wache meldete
#  zeitgleich korrekt „verpasst: 0, alle Slots wartend“. Zwei Wachen,
#  zwei Wahrheiten, ein falscher P1-Alarm (#1054) – und am selben Tag
#  blieb die Engine tatsächlich aus, was der Fehlalarm verdeckte.
#
#  Die Bewertung ist deshalb jetzt eine reine, uhrzeit-geprüfte
#  Funktion in diesem Modul (Selbsttest unten, Regression in
#  scripts/tests/test_produktions_wache.py). Der Workflow lädt nur
#  noch Daten (cadence_guard-SSOT) und ruft `bewertung()` auf.
#
#  REGEL (unverändert hart, nur ehrlich getaktet):
#   - Publikationstag, 0 Artikel, Engine-Lauf fehlgeschlagen → P1 sofort.
#   - Publikationstag, 0 Artikel, letzter Slot noch nicht vorbei
#     → WARTEND (kein Alarm, kein Issue, kein Fachkanal-Beleg).
#     Das gilt in JEDEM Modus – auch für verzögerte Plan-Läufe.
#   - Publikationstag, 0 Artikel, alle Slots vorbei → P1.
#   - Letzter Publikationstag 0 → P1; unter Mindestziel → P2; sonst OK.
# ============================================================
from __future__ import annotations

import datetime
import sys

NAMEN = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
         "Freitag", "Samstag", "Sonntag"]

# Letzter Engine-Slot 17:40 UTC + Puffer. Erst danach darf „heute 0“
# als abgeschlossenes Defizit gelten (Kadenz-Feinheiten misst die
# Slot-Wache; hier zählt nur: kein Alarm in laufende Slots hinein).
LETZTER_SLOT_MINUTEN = 18 * 60 + 30


def bewertung(*, heute: datetime.date, jetzt_utc: datetime.datetime,
              ist_pubtag: bool, anzahl_heute: int | None,
              anzahl_letzter: int, letzter_pubtag: datetime.date,
              minimum: int, modus: str = "",
              engine_conclusion: str = "") -> tuple[str, str]:
    """Stufe + Meldung der Produktions-Wache (rein, ohne IO)."""
    nach_letztem_slot = (jetzt_utc.hour * 60 + jetzt_utc.minute) \
        >= LETZTER_SLOT_MINUTEN
    if ist_pubtag and anzahl_heute == 0:
        if engine_conclusion == "failure":
            return ("P1",
                    f"Heute ({NAMEN[heute.weekday()]}, {heute.isoformat()}) ist ein "
                    f"Publikationstag – der Engine-Lauf ist FEHLGESCHLAGEN und es "
                    f"sind 0 Artikel erschienen (Ziel: {minimum}).")
        if not nach_letztem_slot:
            return ("WARTEND",
                    "Publikationstag, bisher 0 Artikel – Fallback-Slots "
                    "(14:10 / 17:40 UTC) laufen noch. Kein Alarm.")
        return ("P1",
                f"Heute ({NAMEN[heute.weekday()]}, {heute.isoformat()}) ist ein "
                f"Publikationstag – alle Slots vorbei, **0 Artikel** erschienen "
                f"(Ziel: {minimum}).")
    if anzahl_letzter == 0:
        return ("P1",
                f"Am letzten Publikationstag ({NAMEN[letzter_pubtag.weekday()]}, "
                f"{letzter_pubtag.isoformat()}) sind **0 Artikel** erschienen "
                f"(Ziel: {minimum}).")
    if anzahl_letzter < minimum:
        return ("P2",
                f"Am letzten Publikationstag ({letzter_pubtag.isoformat()}) nur "
                f"{anzahl_letzter}/{minimum} Artikel – unter Mindestziel.")
    return ("OK",
            f"Letzter Publikationstag ({letzter_pubtag.isoformat()}): "
            f"{anzahl_letzter} Artikel – Ziel erfüllt.")


def selftest() -> int:
    """Sabotage-Proben: Der Rollover-Fall #1054 muss WARTEND bleiben."""
    fehler: list[str] = []
    mi = datetime.date(2026, 11, 4)   # Mittwoch = Publikationstag
    mo = datetime.date(2026, 11, 2)   # Montag davor, 2/2 erfüllt
    faelle = [
        # (heute, uhrzeit, ist_pub, heute_n, letzter_n, letzter, modus, concl, erwartet)
        (mi, (0, 32), True, 0, 2, mo, "schedule", "", "WARTEND"),      # #1054 Rollover
        (mi, (0, 32), True, 0, 2, mo, "workflow_run", "", "WARTEND"),
        (mi, (7, 0), True, 0, 2, mo, "schedule", "", "WARTEND"),
        (mi, (19, 0), True, 0, 2, mo, "schedule", "", "P1"),           # Slots vorbei
        (mi, (7, 0), True, 0, 2, mo, "workflow_run", "failure", "P1"),  # Lauf tot
        (mi, (19, 0), True, 1, 1, mi, "schedule", "", "P2"),
        (mi, (19, 0), True, 2, 2, mi, "schedule", "", "OK"),
        (datetime.date(2026, 11, 5), (0, 32), False, None, 0, mi,
         "schedule", "", "P1"),                                        # letzter Pubtag leer
    ]
    for heute, (h, m), ist_pub, n_heute, n_letzter, letzter, modus, concl, soll in faelle:
        jetzt = datetime.datetime(heute.year, heute.month, heute.day, h, m,
                                  tzinfo=datetime.timezone.utc)
        stufe, meldung = bewertung(
            heute=heute, jetzt_utc=jetzt, ist_pubtag=ist_pub,
            anzahl_heute=n_heute, anzahl_letzter=n_letzter,
            letzter_pubtag=letzter, minimum=2, modus=modus,
            engine_conclusion=concl)
        if stufe != soll:
            fehler.append(f"{heute} {h:02d}:{m:02d} modus={modus}: "
                          f"erwartet {soll}, bekam {stufe} ({meldung[:60]})")
    if fehler:
        print("🛑 PRODUKTIONS-WACHE-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print(f"✅ PRODUKTIONS-WACHE-SELBSTTEST bestanden: {len(faelle)} Fälle "
          "(inkl. Rollover #1054: verzögerter Plan-Lauf um 00:32 UTC bleibt "
          "WARTEND statt falschem P1).")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    print(__doc__.strip() if __doc__ else "produktions_wache: bewertung()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
