#!/usr/bin/env python3
# ============================================================
#  CLAUDE-STILPOLITUR – WIRKSAMKEITS-URTEIL (Reparatur Issue #468)
#  ------------------------------------------------------------
#  WARUM ES DIESE DATEI GIBT
#    scripts/claude_stilpolitur.py fängt jeden gescheiterten KI-Versuch
#    pro Artikel selbst ab („verworfen – KI-Antwort leer …") und endet
#    danach trotzdem mit Exit 0. Das ist richtig – ein einzelner
#    Fehlversuch darf die Redaktion nicht stoppen –, hat aber eine
#    gefährliche Nebenwirkung: Ein ABGELAUFENES PUTER_AUTH_TOKEN oder ein
#    erschöpftes Gratis-Kontingent sähe im Workflow ewig grün aus,
#    obwohl nie wieder ein Artikel poliert wird.
#
#  WAS ES TUT
#    Liest den Lauf-Report (.claude_stilpolitur_report.json) und fällt
#    ein ehrliches Urteil in EINER Zeile: „<status>|<klartext>"
#      ok           – es wurde poliert, oder es gab nichts zu tun
#      wirkungslos  – Kandidaten vorhanden, 0 poliert, nur Fehlversuche
#                     (typisch: Token abgelaufen / Kontingent leer)
#      unklar       – kein auswertbarer Report vorhanden
#    Exit ist IMMER 0: Das Urteil steuert nur die Meldung im Workflow
#    (gelbe Warnung statt Schein-Grün), niemals den Erfolg der eigenen
#    Offline-Premium-Politur.
#
#  NUTZUNG
#    python3 scripts/claude_stilpolitur_wirkung.py [--report PFAD]
#    python3 scripts/claude_stilpolitur_wirkung.py --selftest
# ============================================================
from __future__ import annotations

import argparse
import json
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(BLOG_DIR, ".claude_stilpolitur_report.json")

MAX_DETAIL = 220


def urteil(report: dict | None) -> tuple[str, str]:
    """Gibt (status, klartext) zurück – die einzige Regelstelle."""
    if not isinstance(report, dict):
        return "unklar", "Kein auswertbarer Lauf-Report vorhanden."

    kandidaten = int(report.get("kandidaten") or 0)
    poliert = int(report.get("poliert") or 0)
    verworfen = int(report.get("verworfen") or 0)

    if kandidaten and not poliert and verworfen:
        gruende = sorted({
            str(item.get("ergebnis") or "").strip()
            for item in report.get("items") or []
            if str(item.get("ergebnis") or "").strip()
        })
        detail = f"{verworfen} Versuch(e), 0 poliert"
        if gruende:
            detail += ": " + "; ".join(gruende)
        return "wirkungslos", detail[:MAX_DETAIL]

    return "ok", (f"{poliert} poliert, {verworfen} verworfen, "
                  f"{kandidaten} Kandidat(en).")


def lade(pfad: str) -> dict | None:
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, ValueError):
        return None
    return daten if isinstance(daten, dict) else None


def selftest() -> int:
    faelle = [
        ({"kandidaten": 3, "poliert": 2, "verworfen": 1}, "ok"),
        ({"kandidaten": 0, "poliert": 0, "verworfen": 0}, "ok"),
        ({"kandidaten": 44, "poliert": 0, "verworfen": 1,
          "items": [{"ergebnis": "verworfen – KI-Antwort leer"}]}, "wirkungslos"),
        ({"kandidaten": 5, "poliert": 0, "verworfen": 5}, "wirkungslos"),
        # Budget/Rotation: Kandidaten offen, aber nichts versucht = kein Defekt
        ({"kandidaten": 12, "poliert": 0, "verworfen": 0}, "ok"),
        (None, "unklar"),
        ("kein dict", "unklar"),
    ]
    fehler = []
    for daten, erwartet in faelle:
        status, text = urteil(daten if isinstance(daten, dict) else None)
        if status != erwartet:
            fehler.append(f"{daten!r} → {status} (erwartet {erwartet})")
        if not text:
            fehler.append(f"{daten!r} → leerer Klartext")

    # Der Klartext nennt den Grund, damit die Warnung im Lauf brauchbar ist.
    status, text = urteil({"kandidaten": 1, "poliert": 0, "verworfen": 1,
                           "items": [{"ergebnis": "verworfen – Token"}]})
    if "Token" not in text:
        fehler.append("Grund fehlt im Klartext des Urteils")
    if len(urteil({"kandidaten": 1, "poliert": 0, "verworfen": 1,
                   "items": [{"ergebnis": "x" * 500}]})[1]) > MAX_DETAIL:
        fehler.append("Klartext wird nicht gekürzt")

    if fehler:
        print("🛑 Wirksamkeits-Selbsttest ROT:")
        for f in fehler:
            print("   -", f)
        return 2
    print("✅ Wirksamkeits-Selbsttest: 9 Fälle grün (offline, ohne API).")
    return 0


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Wirksamkeits-Urteil über den Claude-Stilpolitur-Lauf")
    ap.add_argument("--report", default=REPORT, help="Pfad zum JSON-Report")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Schutz")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    status, text = urteil(lade(args.report))
    print(f"{status}|{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
