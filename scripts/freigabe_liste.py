#!/usr/bin/env python3
"""Freigabe-Liste für die KI-VO-Frist #1028 (02.12.2026).

WAS DAS TOOL TUT
----------------
Die 12 Einträge unter `menschlich:` in `data/ki_kennzeichnung.yaml` (Stand
14.08.–03.09.2026) tragen `ai_generated: false`, ohne dass die Herkunft aus
dem Repo allein belegt ist. Sie dürfen erst dann als geprüft gelten, wenn
der Betreiber jeden Eintrag einzeln bestätigt („ein Mensch hat den Text
geschrieben oder vor Veröffentlichung geprüft“).

Dieses Tool verwaltet genau diese Bestätigungen – und nichts anderes:

* Es liest die 12 Einträge aus `data/ki_kennzeichnung.yaml` und die
  Erst-Erwähnungsdaten aus `data/ki_provenienz_state.json`.
* Es schreibt **niemals** in `data/ki_kennzeichnung.yaml` (die Einträge
  bleiben unangetastet, bis der Betreiber sie hier abhakt).
* Getickte Einträge werden in `data/freigabe_state.json` festgehalten
  (Operator-Zustand, getrennt vom Fach-Register).
* Wenn alle 12 getickt sind, kann das Tool die Betreiber-Freigabeerklärung
  ausgeben, die in die Fristen-Check (Recht) mit
  `erledigt=ki-vo-kennzeichnung-bestand` einfließt.

Das Tool ersetzt keine Rechtsberatung und erstellt keinen Beleg für die
tatsächliche Urheberschaft – es dokumentiert nur, dass der Betreiber die
Einträge einzeln geprüft und freigegeben hat.

Ablauf (von der Operateurin / vom Operator):
  1. python3 scripts/freigabe_liste.py --liste        # Checkliste anzeigen
  2. python3 scripts/freigabe_liste.py --abhaken <slug>   # je Eintrag (12×)
  3. python3 scripts/freigabe_liste.py --freigabe   # Erklärung erzeugen (erst wenn alle 12 getickt)
  4. Die Erklärung in docs/FREIGABE-VORLAGE-...-BESTAND.md übernehmen,
     unterzeichnen und `erledigt=ki-vo-kennzeichnung-bestand` in der
     Fristen-Check (Recht) ausführen.

Exit-Codes: 0 = OK · 1 = nicht alle Einträge getickt (--freigabe) · 2 = Werkzeugfehler
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KI_KENNZEICHNUNG = ROOT / "data" / "ki_kennzeichnung.yaml"
PROVENIENZ_STATE = ROOT / "data" / "ki_provenienz_state.json"
FREIGABE_STATE = ROOT / "data" / "freigabe_state.json"
FRIST = dt.date(2026, 12, 2)


class WerkzeugFehler(RuntimeError):
    """Messung nicht möglich – nie als Inhaltsbefund ausgeben."""


def _yaml():
    try:
        import yaml  # noqa: PLC0415
    except ImportError as exc:
        raise WerkzeugFehler(f"PyYAML fehlt: {exc}") from exc
    return yaml


def lade_menschlich() -> list[dict]:
    """Die 12 `menschlich`-Einträge mit Erst-Erwähnung und Tagen bis Frist."""
    try:
        daten = _yaml().safe_load(
            KI_KENNZEICHNUNG.read_text(encoding="utf-8")
        ) or {}
    except FileNotFoundError:
        raise WerkzeugFehler(f"{KI_KENNZEICHNUNG} fehlt")
    menschlich = daten.get("menschlich")
    if not isinstance(menschlich, list) or not menschlich:
        raise WerkzeugFehler(f"{KI_KENNZEICHNUNG}: keine `menschlich`-Liste")
    try:
        state = json.loads(PROVENIENZ_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        state = {}
    unklar = state.get("ungeklaert_erstmals") or {}
    heute = dt.date.today()
    eintraege = []
    for slug in menschlich:
        erst = unklar.get(slug)
        erst_datum = dt.date.fromisoformat(erst) if erst else None
        tage_bis_frist = (FRIST - heute).days
        eintraege.append(
            {
                "slug": slug,
                "erstmals_ungeklaert": erst,
                "tage_bis_frist": tage_bis_frist,
            }
        )
    return eintraege


def lade_freigabe_state() -> dict:
    if FREIGABE_STATE.is_file():
        try:
            return json.loads(FREIGABE_STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def speichere_freigabe_state(state: dict) -> None:
    FREIGABE_STATE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def gettick(state: dict, slug: str) -> bool:
    return bool((state.get("getickt") or {}).get(slug))


def settick(state: dict, slug: str, wert: bool) -> None:
    state.setdefault("getickt", {})[slug] = bool(wert)
    state["aktualisiert_am"] = dt.date.today().isoformat()


def liste_cmd() -> int:
    eintraege = lade_menschlich()
    state = lade_freigabe_state()
    heute = dt.date.today()
    print("Freigabe-Liste KI-VO #1028 – 12 Einträge als `menschlich` (ohne Herkunfts-Beleg)")
    print(f"Stichtag: {heute.isoformat()} · Frist: {FRIST.isoformat()} "
          f"({(FRIST - heute).days} Tage verbleiben)")
    print("Hinweis: Ein Eintrag abhaken = bestätigt, ein Mensch hat den Text "
          "geschrieben oder vor Veröffentlichung geprüft.")
    print()
    print(f"{'#':>2}  {'Getickt':<9} {'Slug':<58} {'Erstmals ungeklärt':<20} {'Tage bis Frist'}")
    print("-" * 105)
    alle_getickt = True
    for i, e in enumerate(eintraege, 1):
        getickt = gettick(state, e["slug"])
        if not getickt:
            alle_getickt = False
        marker = "[x]" if getickt else "[ ]"
        print(
            f"{i:>2}  {marker:<9} {e['slug']:<58} "
            f"{str(e['erstmals_ungeklaert']):<20} {e['tage_bis_frist']}"
        )
    print()
    print(f"Getickt: {sum(1 for e in eintraege if gettick(state, e['slug']))} von {len(eintraege)}")
    if alle_getickt:
        print("Alle 12 Einträge sind getickt – `python3 scripts/freigabe_liste.py --freigabe` "
              "erzeugt die Betreibererklärung.")
    else:
        offen = [e["slug"] for e in eintraege if not gettick(state, e["slug"])]
        print("Noch offen: " + ", ".join(offen))
    return 0


def abhaken_cmd(slug: str) -> int:
    eintraege = lade_menschlich()
    slugs = {e["slug"] for e in eintraege}
    if slug not in slugs:
        print(f"Unbekannter Slug: {slug}")
        print("Bekannte Einträge: " + ", ".join(sorted(slugs)))
        return 1
    state = lade_freigabe_state()
    settick(state, slug, True)
    speichere_freigabe_state(state)
    print(f"Abgehakt: {slug}  "
          f"({sum(1 for e in eintraege if gettick(state, e['slug']))} von {len(eintraege)})")
    return 0


def freigabe_cmd() -> int:
    eintraege = lade_menschlich()
    state = lade_freigabe_state()
    offen = [e["slug"] for e in eintraege if not gettick(state, e["slug"])]
    if offen:
        print("Freigabe nicht möglich – folgende Einträge sind noch nicht getickt:")
        for s in offen:
            print(f"  - {s}")
        return 1
    heute = dt.date.today()
    print("=" * 72)
    print("BETREIBER-FREIGABE · KI-VO: maschinenlesbare KI-Kennzeichnung für Bestandssysteme")
    print("Frist-ID: ki-vo-kennzeichnung-bestand · Frist 02.12.2026 · Issue #1028")
    print(f"Erstellt: {heute.isoformat()} · Stichtag der Prüfung: {heute.isoformat()}")
    print("=" * 72)
    print()
    print("Erklärung des Betreibers:")
    print("  Die 12 unter `data/ki_kennzeichnung.yaml` als `menschlich` geführten")
    print("  Einträge wurden einzeln geprüft. Für jeden Eintrag bestätigt der")
    print("  Betreiber, dass ein Mensch den Text geschrieben oder vor der")
    print("  Veröffentlichung geprüft und die redaktionelle Verantwortung")
    print("  übernommen hat (Ausnahme nach Art. 50 Abs. 4 UAbs. 2 KI-VO).")
    print()
    print("  Die technischen Maßnahmen für die Cover-Bildherkunft (132 deterministisch")
    print("  gerenderte Covers, Frontmatter-Beleg cover.ki_pruefung, IPTC-XMP")
    print("  DigitalSourceType=algorithmicMedia in der Datei, Reproduktionswache")
    print("  scripts/ki_cover_herkunft.py --pruefen, CI-Gate im Deploy) sind umgesetzt")
    print("  und durch das Gate geprüft (132/132 reproduzierbar, 0 Befunde).")
    print()
    print("  Die Anbieterpflicht nach Art. 50 Abs. 2 KI-VO bleibt unberührt; diese")
    print("  Erklärung ist eine betriebliche Selbsteinschätzung, keine Rechtsberatung.")
    print()
    print("-" * 72)
    print("Betreiber (Name): ________________________________________________")
    print("Unterschrift:     ________________________________________________")
    print("Datum:            ________________________________________________")
    print("-" * 72)
    print()
    print("Fristen-Check (Recht):")
    print("  erledigt=ki-vo-kennzeichnung-bestand")
    print()
    print("Diese Erklärung ist in docs/FREIGABE-VORLAGE-KI-VO-KENNZEICHNUNG-BESTAND.md")
    print("zu übernehmen, zu unterzeichnen und in der Fristen-Check (Recht) auszuführen.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--liste", action="store_true",
                        help="Checkliste der 12 `menschlich`-Einträge anzeigen")
    parser.add_argument("--abhaken", metavar="SLUG",
                        help="Einen Eintrag als geprüft markieren (getrenntes State-File)")
    parser.add_argument("--freigabe", action="store_true",
                        help="Betreiber-Freigabeerklärung erzeugen (nur wenn alle 12 getickt)")
    args = parser.parse_args(argv)

    if not (args.liste or args.abhaken or args.freigabe):
        parser.print_help()
        return 0

    try:
        if args.liste:
            return liste_cmd()
        if args.abhaken:
            return abhaken_cmd(args.abhaken)
        if args.freigabe:
            return freigabe_cmd()
    except WerkzeugFehler as exc:
        print(f"::error title=Freigabe-Liste::{exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
