#!/usr/bin/env python3
# ============================================================
#  FAKTENFRISCHE-KAPAZITÄT – die Deckungsrechnung des Bestands
#  (Auftrag Frank, 29.10.2026, Issue #912 „Release-Scorecard:
#   Produktionswahrheit rot (Bestand blockiert) – bitte dauerhaft
#   auf Highend-Level einer Profi-Agentur beheben.“)
#
#  DER BEFUND
#  ----------
#  Die Release-Scorecard war ab dem 27.10.2026 jeden Tag rot, und das
#  Ticket #912 ließ sich nicht schließen. Die Ursache war keine
#  Inhaltskrise, sondern eine Rechenaufgabe, die niemand gerechnet
#  hatte:
#
#    Bedarf   = Σ 1/Intervall über alle 106 Seiten
#             = 2,58 Prüfungen je Tag = rund 18 je Woche
#    Angebot  = budget.max_artikel_pro_lauf (3) × 2 Läufe je Woche
#             = 6 je Woche = 0,86 je Tag
#    Deckung  = 33 %
#
#  Jede Woche wurden also zwölf Seiten mehr überfällig, als geprüft
#  werden konnten. Die Scorecard konnte NIE grün werden – ein
#  Dauer-Alarm ohne Schließpfad, den die eigene Governance (C14)
#  verbietet. Die Intervalle waren richtig; geliefert wurde zu wenig.
#
#  DIE HEILUNG (nicht „weniger messen“)
#  ------------------------------------
#  1. Diese Datei rechnet den Bedarf aus der EINEN Fälligkeitsregel
#     (`faktenfrische.faelligkeit`) und das Angebot aus dem ECHTEN
#     Plan (cron der Workflow-Datei) – keine abgetippte Zahl, kein
#     zweiter Maßstab (C19, Lektion #521).
#  2. `faktenfrische.py` skaliert sein Budget selbst: Es nimmt so
#     viele Seiten, wie für einen fristgerechten Abbau nötig sind,
#     begrenzt durch `budget.hartes_limit_pro_lauf`.
#  3. Der Vorlauf (`planung.vorlauf_tage`) macht aus der roten Kante
#     einen Arbeitsvorrat: Eine Seite wird ARBEITBAR, eine Woche
#     bevor sie fällig wird. Wer erst am Stichtag anfängt, arbeitet
#     an einer roten Scorecard.
#  4. Ein Rückstand hat eine Frist (`planung.nachhol_frist_tage`).
#     Ist er darin nicht abbaubar, wird der Lauf rot – das ist ein
#     Alarm MIT Schließpfad (C14), kein Dauerzustand.
#  5. Der BÜNDELTAG wird mitgemessen (04.11.2026, #1039): „heute“ ist
#     der ruhigste Tag des Jahres. Seitdem prüft dieselbe Wache den
#     Spitzentag im Horizont (`spitzenlast_stichtag`) – mit derselben
#     Planrechnung. „Nicht gemessen“ steht nie wie „grün“ aus
#     (`spitze_geprueft` in jeder Ausgabe, C33).
#  6. Die PROJEKTION rechnet den Weg des Bots (06.11.2026, #1107). Ein
#     Stichtag in der Zukunft wird nicht mit dem eingefrorenen Prüfdatum
#     von heute gemessen – das unterstellte, der Bot prüfe bis dahin nichts,
#     und erzeugte „rot am 26.11. und 31.12.“. `bestand_trajektorie`
#     simuliert dieselbe EDF-Auswahl wie `faktenfrische.py` ab heute.
#     Ein echter Engpass bleibt rot (Gegenprobe in den Tests).
#
#  WAS HIER NICHT PASSIERT
#  -----------------------
#  * Keine zweite Fälligkeitsregel: `faelligkeit()` liefert Frist und
#    Restlaufzeit; dieses Modul addiert nur.
#  * Keine Heilung: Das Modul liest (Frontmatter, SSOT, Workflow) und
#    rechnet. Es schreibt keine Artikel, keine Fristen, keine Belege.
#  * Kein Uhr-Zufall: Alle Rechenfunktionen nehmen einen `stichtag`.
#    `--selftest` läuft gegen eingefrorene Probetage (Uhr-Zwang).
#
#  NUTZUNG
#    python3 scripts/faktenfrische_kapazitaet.py            # Klartext
#    python3 scripts/faktenfrische_kapazitaet.py --json     # maschinell
#    python3 scripts/faktenfrische_kapazitaet.py --wache    # Exit 1, wenn
#                                        der Rückstand nicht fristgerecht
#                                        abbaubar ist ODER der Spitzentag
#                                        reißt (Workflow-Schritt)
#    python3 scripts/faktenfrische_kapazitaet.py --budget-empfehlung
#                                        # nur die Zahl für --max
#    python3 scripts/faktenfrische_kapazitaet.py --selftest # Sabotage-Proben
#
#  EXIT: 0 = Plan gedeckt · 1 = Rückstand nicht fristgerecht abbaubar
#        oder Spitzentag reißt die Frist (nur mit --wache) ·
#        2 = Werkzeugfehler (fail-closed)
# ============================================================
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import faktenfrische as ff  # noqa: E402

WORKFLOW_PFAD = os.path.join(BLOG_DIR, ".github", "workflows", "faktenfrische.yml")

# Planungs-Vorgaben, falls die SSOT sie (noch) nicht nennt. Sie sind
# bewusst identisch mit `data/agent_reach/faktenfrische.yaml`; die SSOT
# gewinnt immer. Ein fehlender Block ist kein Grund für eine stille 0.
PLANUNG_DEFAULTS = {
    "vorlauf_tage": 7,
    "nachhol_frist_tage": 7,
    "horizont_tage": 120,
    "min_deckung_prozent": 110,
}

BUDGET_DEFAULTS = {
    "max_artikel_pro_lauf": 3,
    "auto_skalierung": True,
    "hartes_limit_pro_lauf": 10,
}


# ============================================================
#  Plan lesen: cron → Läufe je Tag (nie abgetippt)
# ============================================================
def feld_werte(feld: str, lo: int, hi: int) -> set[int] | None:
    """Ein cron-Feld als Zahlenmenge. `None` = nicht verstanden.

    Verstanden werden `*`, `*/n`, `a-b`, `a-b/n` und Listen daraus –
    das ist der gesamte Wortschatz der Repo-Zeitpläne. Alles andere
    wird NICHT geraten: Ein falsch geratener Plan wäre schlimmer als
    ein sichtbarer Fehler (dieselbe Disziplin wie `slot_wache.py`).
    """
    werte: set[int] = set()
    for teil in str(feld).strip().split(","):
        teil = teil.strip()
        if not teil:
            return None
        schritt = 1
        if "/" in teil:
            basis, _, schritt_text = teil.partition("/")
            if not schritt_text.isdigit() or int(schritt_text) <= 0:
                return None
            schritt = int(schritt_text)
            teil = basis.strip()
        if teil == "*":
            start, ende = lo, hi
        elif re.fullmatch(r"\d+", teil):
            start = ende = int(teil)
        elif re.fullmatch(r"\d+-\d+", teil):
            a, _, b = teil.partition("-")
            start, ende = int(a), int(b)
        else:
            return None
        if start < lo or ende > hi or start > ende:
            return None
        werte.update(range(start, ende + 1, schritt))
    return werte or None


def laeufe_je_tag(cron_ausdruecke: list[str]) -> tuple[float | None, list[str]]:
    """(Läufe je Tag, Hinweise) aus einer Liste von cron-Ausdrücken.

    `None` heißt: Plan nicht lesbar → der Aufrufer muss fail-closed
    reagieren (nie „0 Läufe, alles gut“).
    """
    gesamt = 0.0
    hinweise: list[str] = []
    if not cron_ausdruecke:
        return None, ["kein cron-Ausdruck gefunden"]
    for ausdruck in cron_ausdruecke:
        felder = str(ausdruck).strip().split()
        if len(felder) != 5:
            return None, [f"cron nicht verstanden: {ausdruck!r}"]
        minute, stunde, tag, monat, wochentag = felder
        minuten = feld_werte(minute, 0, 59)
        stunden = feld_werte(stunde, 0, 23)
        tage = feld_werte(tag, 1, 31)
        monate = feld_werte(monat, 1, 12)
        wochentage = feld_werte(wochentag, 0, 7)
        if None in (minuten, stunden, tage, monate, wochentage):
            return None, [f"cron nicht verstanden: {ausdruck!r}"]
        # Ein Plan über bestimmte Monats-/Tagesdaten ist nicht in eine
        # Tagesrate übersetzbar – dann lieber ehrlich „nicht lesbar“.
        if tage != set(range(1, 32)) or monate != set(range(1, 13)):
            return None, [f"cron mit Kalenderbindung nicht bewertbar: {ausdruck!r}"]
        tageslaeufe = len(minuten) * len(stunden)
        if wochentage == set(range(0, 8)):
            gesamt += tageslaeufe
        else:
            # 7 zählt wie 0 (Sonntag) – beide meinen denselben Tag.
            tage_der_woche = {0 if w == 7 else w for w in wochentage}
            gesamt += tageslaeufe * len(tage_der_woche) / 7.0
            hinweise.append(f"{ausdruck.strip()}: {len(tage_der_woche)}/7 Tage")
    return gesamt, hinweise


def crons_aus_workflow(text: str) -> list[str]:
    """Alle cron-Zeilen eines Workflow-Textes (YAML-Schreibweisen beide)."""
    treffer: list[str] = []
    for zeile in text.splitlines():
        m = re.match(r"\s*-\s*cron:\s*[\"']?([^\"'#]+)[\"']?\s*(?:#.*)?$", zeile)
        if m:
            treffer.append(m.group(1).strip())
    return treffer


def laeufe_aus_workflow(pfad: str = WORKFLOW_PFAD) -> tuple[float | None, list[str]]:
    try:
        with open(pfad, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return None, [f"{os.path.basename(pfad)} nicht lesbar: {exc}"]
    return laeufe_je_tag(crons_aus_workflow(text))



def lauf_tage(cron_ausdruecke: list[str], stichtag: dt.date,
              horizont_tage: int) -> set[dt.date] | None:
    """Echte Lauftage, keine mittlere Tagesrate für die Simulation.

    Nur derselbe tägliche/wochentliche cron-Wortschatz wie `laeufe_je_tag`.
    Mehrere Ausdrücke vereinigen ihre Tage (kein Doppelbudget am selben Tag).
    Kalenderbindung oder ungültige Syntax: nicht beweisbar, nicht geraten.
    """
    if laeufe_je_tag(cron_ausdruecke)[0] is None:
        return None
    wochentage: set[int] = set()
    for ausdruck in cron_ausdruecke:
        feld = ausdruck.strip().split()[4]
        werte = feld_werte(feld, 0, 7)
        if werte is None:
            return None
        wochentage.update(0 if wert == 7 else wert for wert in werte)
    return {stichtag + dt.timedelta(days=offset)
            for offset in range(max(0, horizont_tage) + 1)
            if (stichtag + dt.timedelta(days=offset)).isoweekday() % 7
            in wochentage}


def lauftage_aus_workflow(stichtag: dt.date, horizont_tage: int,
                          pfad: str = WORKFLOW_PFAD) -> set[dt.date] | None:
    try:
        text = Path(pfad).read_text(encoding="utf-8")
    except OSError:
        return None
    return lauf_tage(crons_aus_workflow(text), stichtag, horizont_tage)


# ============================================================
#  Bedarf und Angebot
# ============================================================
def planung(cfg: dict) -> dict:
    werte = dict(PLANUNG_DEFAULTS)
    werte.update({k: v for k, v in (cfg.get("planung") or {}).items()
                  if v is not None})
    return werte


def budget_vorgaben(cfg: dict) -> dict:
    werte = dict(BUDGET_DEFAULTS)
    werte.update({k: v for k, v in (cfg.get("budget") or {}).items()
                  if v is not None})
    return werte


def bedarf_je_tag(artikel: list[dict], cfg: dict,
                  stichtag: dt.date | None = None) -> float:
    """Σ 1/Intervall – die einzige Bedarfszahl, aus `faelligkeit()`.

    Eine Seite mit Intervall 30 Tage braucht 1/30 Prüfung je Tag. Die
    Summe ist der Dauerbedarf des Bestands; sie ist unabhängig davon,
    wie viele Seiten heute zufällig überfällig sind.
    """
    stichtag = stichtag or ff.heute()
    bedarf = 0.0
    for art in artikel:
        status = ff.faelligkeit(art, cfg, stichtag)
        intervall = int(status.get("intervall") or 0)
        if intervall > 0:
            bedarf += 1.0 / intervall
    return bedarf


def kapazitaet_je_tag(budget: int, laeufe: float) -> float:
    return max(0.0, float(budget) * float(laeufe))


# ============================================================
#  Simulation (EDF – earliest deadline first)
# ============================================================
def eintraege_bauen(artikel: list[dict], cfg: dict, stichtag: dt.date) -> list[dict]:
    """Arbeitsvorrat mit Frist und Vorlauf-Zieltag.

    `ziel`  = Tag, ab dem die Seite ARBEITBAR ist (Frist − Vorlauf).
    `frist` = Tag, an dem sie rot wird (None = Erstrecherche: sofort).
    """
    vorlauf = int(planung(cfg)["vorlauf_tage"])
    eintraege = []
    for art in artikel:
        status = ff.faelligkeit(art, cfg, stichtag)
        frist = status.get("frist")
        if frist is None:
            frist = stichtag
            ziel = stichtag
        else:
            ziel = frist - dt.timedelta(days=vorlauf)
        eintraege.append({
            "slug": art.get("slug") or "",
            "titel": art.get("titel") or "",
            "bereich": art.get("bereich", "artikel"),
            "klasse": status.get("klasse") or "standard",
            "prio": int(status.get("prio") or 9),
            "intervall": int(status.get("intervall") or 0),
            "frist": frist,
            "ziel": ziel,
            "_vorlauf": vorlauf,
            "bereits_faellig": bool(status.get("faellig")),
            "restlaufzeit": status.get("restlaufzeit"),
        })
    return eintraege


def simuliere(eintraege: list[dict], budget: int, stichtag: dt.date,
              horizont_tage: int, lauftage: set[dt.date],
              *, beobachte: set[dt.date] | None = None) -> dict:
    """EDF mit ganzzahligem Budget an ECHTEN Lauftagen, inklusive Folgeterminen.

    Nicht gearbeitete Plätze verfallen am Tagesende. Drei Plätze am Dienstag
    können keine Freitag-Frist retten. Ein erfolgreicher Check erzeugt den
    nächsten Termin ab dem tatsächlichen Prüftag, nicht ab dem Wunschtermin.

    `letzte_pruefung` (slug → Prüftag) ist der Stand, den der Bot hinterlässt.
    `beobachte` nimmt Tagesschnappschüsse dieses Stands zu BEGINN des Tages
    (`snapshots`) – die Grundlage für `bestand_trajektorie` (#1107).
    """
    if budget < 1 or horizont_tage < 0:
        raise ValueError("Budget muss positiv, Horizont darf nicht negativ sein")
    if len({e["slug"] for e in eintraege}) != len(eintraege):
        raise ValueError("Doppelter Slug im Arbeitsvorrat")
    offen = {}
    for e in eintraege:
        status = {"prio": e["prio"], "frist": e["frist"]}
        offen[e["slug"]] = dict(e, runde=0, _vorlauf=e.get("_vorlauf", 7), _faellig=status)
    erledigt: dict[str, int] = {}
    letzte_pruefung: dict[str, dt.date] = {}
    snapshots: dict[dt.date, dict[str, dt.date]] = {}
    verletzt: list[dict] = []
    gemeldet: set[tuple[str, int]] = set()
    abbau_tag: int | None = None
    alt_rueckstand = {e["slug"] for e in eintraege if e["bereits_faellig"]}
    for offset in range(horizont_tage + 1):
        tag = stichtag + dt.timedelta(days=offset)
        # Stand zu BEGINN des Tages (#1107): Ein Restart an diesem Tag verarbeitet
        # den Tag selbst genau einmal. Ein Stand nach der Verarbeitung würde den
        # Tagesplatz doppelt zählen.
        if beobachte and tag in beobachte:
            snapshots[tag] = dict(letzte_pruefung)
        def melde_verspaetungen():
            for e in offen.values():
                key = (e["slug"], e["runde"])
                if e["frist"] < tag and key not in gemeldet:
                    verletzt.append({"slug": e["slug"], "titel": e["titel"],
                                     "frist": e["frist"].isoformat(),
                                     "tage_zu_spaet": (tag - e["frist"]).days,
                                     "vorher_faellig": e["slug"] in alt_rueckstand,
                                     "folgeprüfung": e["runde"] > 0})
                    gemeldet.add(key)
        melde_verspaetungen()
        if tag in lauftage:
            bereit = sorted((e for e in offen.values() if e["ziel"] <= tag),
                            key=lambda e: ff.edf_schluessel(e, dict(
                                e["_faellig"],
                                prio=e["_faellig"]["prio"] if e["_faellig"]["prio"] == 0 else
                                (2 if e["klasse"] == "standard" else 1) if tag >= e["frist"] else 9)))
            for e in bereit[:budget]:
                slug = e["slug"]
                erledigt.setdefault(slug, offset)
                letzte_pruefung[slug] = tag
                if e["intervall"] <= 0:
                    del offen[slug]
                    continue
                frist = tag + dt.timedelta(days=e["intervall"])
                offen[slug] = dict(e, frist=frist, runde=e["runde"] + 1,
                                   ziel=frist - dt.timedelta(days=e["_vorlauf"]),
                                   bereits_faellig=False,
                                   _faellig=dict(e["_faellig"], frist=frist,
                                                 prio=2 if e["klasse"] == "standard" else 1))
        melde_verspaetungen()
        if alt_rueckstand and alt_rueckstand <= set(erledigt) and abbau_tag is None:
            abbau_tag = offset
    return {"erledigt": erledigt, "verletzungen": verletzt,
            "abbau_tag": abbau_tag,
            "offen": [{"slug": e["slug"], "frist": e["frist"].isoformat()}
                      for e in sorted(offen.values(), key=lambda e: e["frist"])[:20]],
            "offen_gesamt": len(offen),
            "letzte_pruefung": letzte_pruefung,
            "snapshots": snapshots}


def _lauftage_ab(basis: dt.date, tage: int, laeufe: float) -> set[dt.date]:
    """Echte Lauftage ab `basis` über `tage` Tage. Nicht beweisbar → ValueError."""
    if laeufe == 1.0:
        return {basis + dt.timedelta(days=i) for i in range(max(0, tage) + 1)}
    lauftage = lauftage_aus_workflow(basis, tage)
    if lauftage is None:
        raise ValueError(f"Laufkalender ab {basis.isoformat()} nicht beweisbar – "
                         "der Bestand an einem Zukunftstag wäre geraten.")
    return lauftage


def bestand_trajektorie(artikel: list[dict], cfg: dict, budget: int, laeufe: float,
                        basis: dt.date, ziele: set[dt.date]) -> dict[dt.date, list[dict]]:
    """Der Bestand an jedem Tag in `ziele`, so wie der Bot ihn ab `basis` hinterlässt.

    WARUM (#1107, 06.11.2026): Die Projektion rechnete bisher einen Stichtag
    in der Zukunft mit dem HEUTIGEN, eingefrorenen Prüfdatum jeder Seite – als hätte
    der Bot die nächsten zwanzig Tage nichts geprüft. Daraus entstand „rot am
    26.11. und 31.12.“: 30 Seiten wirkten überfällig, obwohl sie in der Zwischenzeit
    längst fällig geworden und geprüft worden wären. Die Trajektorie ist dieselbe
    EDF-Auswahl wie `faktenfrische.py` (C19: eine Regel, zwei Aufrufer). Sie simuliert
    den Lauf von `basis` bis zum spätesten Ziel und gibt den Stand je Tag zurück.

    Vergangene oder heutige Ziele liefern den Bestand unverändert.
    """
    stande: dict[dt.date, list[dict]] = {}
    spaet = {z for z in ziele if z > basis}
    for z in ziele:
        if z <= basis:
            stande[z] = [dict(a) for a in artikel]
    if not spaet:
        return stande
    tage = (max(spaet) - basis).days
    lauftage = _lauftage_ab(basis, tage, laeufe)
    lauf = simuliere(eintraege_bauen(artikel, cfg, basis), budget, basis, tage,
                     lauftage, beobachte=spaet)
    for z in spaet:
        letzte = lauf["snapshots"][z]
        stande[z] = [dict(a, faktencheck=letzte[a["slug"]]) if a.get("slug") in letzte
                     else dict(a) for a in artikel]
    return stande


def plan(artikel: list[dict], cfg: dict, budget: int, laeufe: float,
         stichtag: dt.date, horizont_tage: int | None = None,
         *, lauftage: set[dt.date] | None = None,
         basis: dt.date | None = None) -> dict:
    """Der komplette Deckungsnachweis für EINEN Tag und EIN Budget.

    `basis` (#1107): Liegt der Stichtag in der Zukunft, wird der Bestand am
    Stichtag als Trajektorie ab `basis` (in der Regel heute) gerechnet – nie als
    eingefrorener Stand. Ohne `basis` gilt der Stichtag selbst als Ausgangspunkt.
    """
    if basis is not None and basis > stichtag:
        raise ValueError("Ausgangspunkt der Projektion liegt nach dem Stichtag.")
    if basis is not None and basis < stichtag:
        artikel = bestand_trajektorie(artikel, cfg, budget, laeufe, basis,
                                      {stichtag})[stichtag]
    p = planung(cfg)
    horizont = int(horizont_tage or p["horizont_tage"])
    eintraege = eintraege_bauen(artikel, cfg, stichtag)
    kapazitaet = kapazitaet_je_tag(budget, laeufe)
    bedarf = bedarf_je_tag(artikel, cfg, stichtag)
    if lauftage is None:
        if laeufe != 1.0:
            raise ValueError("Ohne echten Laufkalender ist nur ein täglicher Plan beweisbar")
        lauftage = {stichtag + dt.timedelta(days=i) for i in range(horizont + 1)}
    lauf = simuliere(eintraege, budget, stichtag, horizont, lauftage)

    faellig = [e for e in eintraege if e["bereits_faellig"]]
    ueberfaellig = [e for e in eintraege
                    if e["restlaufzeit"] is not None and e["restlaufzeit"] < 0]
    kuenftig = sorted((e for e in eintraege if not e["bereits_faellig"]
                       and e["restlaufzeit"] is not None),
                      key=lambda e: e["frist"])

    alt_verletzt = [v for v in lauf["verletzungen"] if v["vorher_faellig"]]
    neu_verletzt = [v for v in lauf["verletzungen"]
                    if not v["vorher_faellig"] and not v["folgeprüfung"]]
    folge_verletzt = [v for v in lauf["verletzungen"] if v["folgeprüfung"]]

    deckung = (kapazitaet / bedarf * 100.0) if bedarf > 0 else 100.0
    return {
        "stichtag": stichtag.isoformat(),
        "artikel": len(artikel),
        "faellig": len(faellig),
        "ueberfaellig": len(ueberfaellig),
        "ueberfaellig_max_tage": max((abs(e["restlaufzeit"]) for e in ueberfaellig),
                                     default=0),
        "naechste_frist": ({"slug": kuenftig[0]["slug"],
                            "frist": kuenftig[0]["frist"].isoformat(),
                            "restlaufzeit": kuenftig[0]["restlaufzeit"]}
                           if kuenftig else None),
        "budget": budget,
        "laeufe_je_tag": round(laeufe, 3),
        "kapazitaet_je_tag": round(kapazitaet, 3),
        "bedarf_je_tag": round(bedarf, 3),
        "bedarf_je_woche": round(bedarf * 7, 1),
        "deckung_prozent": round(deckung, 1),
        "horizont_tage": horizont,
        "vorlauf_tage": int(p["vorlauf_tage"]),
        "nachhol_frist_tage": int(p["nachhol_frist_tage"]),
        "abbau_tage": lauf["abbau_tag"],
        "verletzungen_alt": len(alt_verletzt),
        "verletzungen_neu": len(neu_verletzt),
        "verletzungen_folge": len(folge_verletzt),
        "verletzungen_folge_seiten": len({v["slug"] for v in folge_verletzt}),
        "verletzungen": (alt_verletzt + neu_verletzt + folge_verletzt)[:20],
        "offen_im_horizont": lauf["offen_gesamt"],
        "puenktlich": not neu_verletzt and not folge_verletzt,
        "rueckstand_abgebaut": (not alt_verletzt) or (
            lauf["abbau_tag"] is not None
            and lauf["abbau_tag"] <= int(p["nachhol_frist_tage"])),
    }


def empfohlenes_budget(artikel: list[dict], cfg: dict, laeufe: float,
                       stichtag: dt.date, horizont_tage: int | None = None,
                       *, lauftage: set[dt.date] | None = None,
                       basis: dt.date | None = None) -> dict:
    """Kleinstes Budget, das Rückstand fristgerecht abbaut – ohne neue Frist.

    Gesucht ist die kleinste Zahl im Korridor
    `max_artikel_pro_lauf … hartes_limit_pro_lauf`, bei der
      a) keine Seite mit ZUKÜNFTIGER Frist in die Verspätung läuft und
      b) der Alt-Rückstand binnen `nachhol_frist_tage` weg ist.
    Findet sich keine, ist die Kadenz strukturell unterdeckt – das ist
    ein Befund für die Governance, keine stille Obergrenze.
    """
    b = budget_vorgaben(cfg)
    sockel = max(1, int(b["max_artikel_pro_lauf"]))
    limit = max(sockel, int(b["hartes_limit_pro_lauf"]))
    for budget in range(sockel, limit + 1):
        p = plan(artikel, cfg, budget, laeufe, stichtag, horizont_tage,
                 lauftage=lauftage, basis=basis)
        if p["puenktlich"] and p["rueckstand_abgebaut"]:
            return {"budget": budget, "erreicht": True, "limit": limit,
                    "sockel": sockel, "plan": p}
    return {"budget": limit, "erreicht": False, "limit": limit,
            "sockel": sockel,
            "plan": plan(artikel, cfg, limit, laeufe, stichtag, horizont_tage,
                         lauftage=lauftage, basis=basis)}


# ============================================================
#  Spitzenlast: der Bündeltag wird mitgemessen (#1039)
# ============================================================
def spitzenlast_stichtage(artikel: list[dict], cfg: dict,
                          stichtag: dt.date,
                          horizont_tage: int | None = None) -> list[dt.date]:
    """Die Tage im Horizont, an denen Prüftermine BÜNDELN (#1039).

    WARUM ES DIESE FUNKTION GIBT (04.11.2026, dauerhaft 06.11.2026)
    --------------------------------------------------------------
    Am 04.11.2026 war die Deckungswache grün – geprüft am Stichtag „heute“.
    Drei Wochen später kippten 23 Seiten mit demselben Prüfdatum gemeinsam
    in die Überfälligkeit, und derselbe Lauf meldete „Frist gerissen“. Die
    Wache hatte also den ruhigsten Tag des Jahres gemessen und daraus einen
    Dauerbefund abgeleitet.

    Das ist keine Messung, sondern ein Blick aus dem Fenster. Die Fristen
    sind BÜNDEL (am 06.11.2026: 115 Seiten auf 35 Fristtage, davon 23 am
    27.11.2026). Ein Stichtag, der zufällig zwischen zwei Schüben liegt,
    sieht Reserve, wo eine Woche später keine ist – der Fehler findet sich
    erst, wenn der Kalender ihn schreibt.

    Rückgabe: der Stichtag selbst plus jeder Tag, an dem SEIN Bindungsbild
    wechselt – also jede Frist im Horizont und jeder Vorlauf-Beginn
    (`frist − vorlauf_tage`). Nur an diesen Tagen kann sich das Urteil
    drehen; alle anderen Tage sind Wiederholungen. Bewusst KEIN Tag, an
    dem längst alles überfällig ist: Dort misst man den Rückstand, nicht
    die Kadenz, und jeder Bestand wäre „rot“ (das wäre eine Schwelle
    durch die Hintertür, und die gehört in die SSOT, nicht in die Wache).
    """
    p = planung(cfg)
    horizont = max(0, int(horizont_tage if horizont_tage is not None else p["horizont_tage"]))
    vorlauf = int(p["vorlauf_tage"])
    ende = stichtag + dt.timedelta(days=horizont)
    tage: set[dt.date] = {stichtag}
    for art in artikel:
        frist = ff.faelligkeit(art, cfg, stichtag).get("frist")
        if frist is None:
            continue
        if stichtag <= frist <= ende:
            tage.add(frist)
        beginn = frist - dt.timedelta(days=vorlauf)
        if stichtag <= beginn <= ende:
            tage.add(beginn)
    return sorted(tage)


def spitzenlast_stichtag(artikel: list[dict], cfg: dict, budget: int,
                         laeufe: float, stichtag: dt.date,
                         horizont_tage: int | None = None,
                         *, basis: dt.date | None = None) -> dict | None:
    """Der Bündeltag im Horizont, an dem eine HEUTE frische Seite zu spät käme.

    Gemessen wird mit DERSELBEN Planrechnung wie am Stichtag – keine zweite
    Schwelle, keine neue Formel. Nur der Beweis ist neu:

    Eine Seite, die am Stichtag NOCH NICHT überfällig ist, wird an jedem
    späteren Bündeltag erneut geprüft. Ist sie dort überfällig, hat der
    Kalender sie überholt, nicht der Rückstand: Der Lauf war zu klein, um
    seinen eigenen Zulauf zu bedienen. Genau das war am 04.11.2026 der
    Befund – die Wache war grün, und drei Wochen später standen 23 Seiten
    mit demselben Prüfdatum gemeinsam zu spät.

    Der Zustand AN dem Bündeltag ist die Trajektorie ab `basis` (#1107) –
    nicht der eingefrorene Stand von heute. Wer die Arbeit zwischen heute und
    dem Bündeltag wegdenkt, misst eine Seite, die der Bot längst geprüft hätte.

    Bewusst NICHT gemessen wird der Tag, an dem längst alles überfällig
    ist: Dort prüft man den Alt-Rückstand (dafür gibt es
    `rueckstand_abgebaut` am Stichtag), nicht die Kadenz. Würde die Wache
    dort anschlagen, wäre jeder Bestand „rot“ – eine Schwelle durch die
    Hintertür, und die gehört in die SSOT, nicht in die Wache.

    Bei einem Nicht-Tages-Plan wird der echte Laufkalender je Bündeltag
    aus dem Workflow gelesen (kein Wochenmittel als Tagesplan). Ist er
    nicht beweisbar, wirft die Messung einen ValueError – der Aufrufer
    muss fail-closed „nicht beweisbar“ melden, nicht raten.
    """
    return _spitze_auswertung(artikel, cfg, budget, laeufe, stichtag,
                              horizont_tage, basis)[1]


def _spitze_auswertung(artikel: list[dict], cfg: dict, budget: int,
                       laeufe: float, stichtag: dt.date,
                       horizont_tage: int | None,
                       basis: dt.date | None) -> tuple[list[dt.date], dict | None]:
    """(Kandidaten-Bündeltage, schlechtester Bündeltag oder None).

    EINE Rechnung für Befund und Zahlen (C19): `spitze_zahlen` und
    `spitzenlast_stichtag` lesen beide hieraus, damit „geprüft“ und „Befund“
    nie aus zwei Läufen stammen.

    Die Stände kommen aus EINER Trajektorie ab `basis` (Standard: stichtag).
    Kandidaten sind Stichtag und jede Frist/Vorlaufbeginn im Horizont – sowohl
    aus dem heutigen Stand als auch aus dem Stand am Horizontende, denn der Bot
    erzeugt selbst neue Fristen (Prüfung + Intervall).
    """
    p = planung(cfg)
    horizont = max(0, int(horizont_tage if horizont_tage is not None
                          else p["horizont_tage"]))
    base = basis if basis is not None else stichtag
    if base > stichtag:
        raise ValueError("Ausgangspunkt der Projektion liegt nach dem Stichtag.")
    ende = stichtag + dt.timedelta(days=horizont)
    tage = {stichtag + dt.timedelta(days=i) for i in range(horizont + 1)}
    stande = bestand_trajektorie(artikel, cfg, budget, laeufe, base, tage)
    kandidaten = sorted(_bindungstage(stande[stichtag], cfg, stichtag, horizont)
                        | _bindungstage(stande[ende], cfg, stichtag, horizont))
    schlechtester: dict | None = None
    for tag in kandidaten:
        if tag <= stichtag:
            continue
        frisch = [art for art in stande[tag]
                  if not (ff.faelligkeit(art, cfg, tag) or {}).get("faellig")]
        if not frisch:
            continue
        if laeufe == 1.0:
            lauftage = None   # plan() baut den täglichen Kalender deterministisch
        else:
            lauftage = lauftage_aus_workflow(tag, horizont)
            if lauftage is None:
                raise ValueError(
                    f"Laufkalender ab {tag.isoformat()} nicht beweisbar – "
                    "die Spitzenlast wäre geraten.")
        plan_ergebnis = plan(frisch, cfg, budget, laeufe, tag, horizont,
                             lauftage=lauftage)
        if plan_ergebnis["puenktlich"]:
            continue
        offen = plan_ergebnis["verletzungen_neu"] + plan_ergebnis["verletzungen_folge"]
        kennzahl = (offen, len(frisch))
        if schlechtester is None or kennzahl > schlechtester["rang"]:
            schlechtester = {"rang": kennzahl, "stichtag": tag,
                             "offen": offen, "frisch": len(frisch),
                             "puenktlich": False}
    return kandidaten, schlechtester


def _bindungstage(artikel: list[dict], cfg: dict, stichtag: dt.date,
                  horizont: int) -> set[dt.date]:
    """Die Bindungstage eines Standes (Stichtag, Fristen, Vorlaufbeginne)."""
    return set(spitzenlast_stichtage(artikel, cfg, stichtag, horizont))


def spitze_zahlen(artikel: list[dict], cfg: dict, budget: int,
                  laeufe: float, stichtag: dt.date,
                  horizont_tage: int | None = None,
                  *, basis: dt.date | None = None) -> dict:
    """Die Spitzenlast-Messung als Zahlen-Block – die EINE Stelle dafür.

    Wer die Deckung misst, fragt diese Funktion; kein Konsument rechnet die
    Bündeltage ein zweites Mal selbst (C19, Lektion #521). `spitze_geprueft`
    steht IMMER in den Zahlen – "nicht gemessen" darf nie wie "grün"
    aussehen (C33). Erst bei einem Befund kommen die Befund-Felder dazu:

      spitze_geprueft   Anzahl geprüfter Bündeltage im Horizont (immer)
      spitze_stichtag   der schlechteste Bündeltag (nur bei Befund)
      spitze_offen      Seiten, die dort zu spät kämen (nur bei Befund)
      spitze_frisch     damals noch frische Seiten (nur bei Befund)
      spitze_puenktlich False = Befund (nur bei Befund)
    """
    kandidaten, finde = _spitze_auswertung(artikel, cfg, budget, laeufe,
                                           stichtag, horizont_tage, basis)
    zahlen = {"spitze_geprueft": len(kandidaten)}
    if finde is not None:
        zahlen["spitze_stichtag"] = finde["stichtag"].isoformat()
        zahlen["spitze_offen"] = int(finde["offen"])
        zahlen["spitze_frisch"] = int(finde["frisch"])
        zahlen["spitze_puenktlich"] = False
    return zahlen


# ============================================================
#  C45-Urteil: Plan, Reserve und Dauer-Spitze getrennt (#1023)
# ============================================================
C45_SSOT_PFAD = "data/agent_reach/faktenfrische.yaml"


def c45_urteil(zahlen: dict, ssot_pfad: str = C45_SSOT_PFAD) -> list[str]:
    """Das Urteil der Deckungswache – rein, ohne Dateizugriff.

    `zahlen` sind die Messwerte aus `_c45_deckung` (Governance-Vertrag)
    oder aus dem Hauptlauf. Diese Funktion ist die EINE Urteilsstelle:
    Der Vertrag darf nicht eine zweite, abweichende Schwelle erfinden
    (C19, Lektion #521). Sie prüft den Plan, den der Lauf wirklich
    fährt – nicht den Sockel als vermeintlichen Alltag.

    Der Sockel ist die Untergrenze, das harte Limit die Obergrenze.
    Bei `auto_skalierung` ist das empfohlene Budget der Plan; es muss
    den Bedarf decken und unter dem Limit bleiben (Reserve). Ohne
    Auto-Skalierung ist der Sockel der Plan. Eine Kadenz, die nur mit
    dauerhaft ausgereiztem Limit aufgeht, ist ein Dauer-Stau.
    """
    seiten = int(zahlen["seiten"])
    bedarf = float(zahlen["bedarf"])
    mindest = int(zahlen["mindest"])
    laeufe = float(zahlen["laeufe"])
    sockel = int(zahlen["sockel"])
    limit = int(zahlen["limit"])
    budget = int(zahlen["budget"])
    kapazitaet = float(zahlen["kapazitaet"])
    kapazitaet_spitze = float(zahlen["kapazitaet_spitze"])
    auto = bool(zahlen.get("auto"))
    erreicht = bool(zahlen.get("empfehlung_erreicht", True))
    puenktlich = bool(zahlen.get("plan_puenktlich", True))
    rueckstand = bool(zahlen.get("plan_rueckstand_abgebaut", True))
    noetig = bedarf * mindest / 100.0
    funde: list[str] = []

    if sockel > limit:
        funde.append(
            f"Ungültiger Korridor: Sockel {sockel} > hartes Limit {limit} – "
            f"{ssot_pfad} muss einen Sockel unter dem Limit nennen (#912).")
    if kapazitaet_spitze + 1e-9 < noetig:
        funde.append(
            f"Kadenz strukturell unterdeckt: {seiten} Seiten brauchen "
            f"{bedarf:.2f} Prüfungen/Tag ({noetig:.2f} bei {mindest} % "
            f"Mindestdeckung); selbst das harte Limit von {limit} je Lauf "
            f"liefert nur {kapazitaet_spitze:.2f}/Tag. Takt, Limit oder "
            f"Intervall in {ssot_pfad} entscheiden (#912).")
        return funde
    if auto:
        if not erreicht:
            funde.append(
                f"Kadenz strukturell unterdeckt: {seiten} Seiten brauchen "
                f"{bedarf:.2f} Prüfungen/Tag ({noetig:.2f} bei {mindest} % "
                f"Mindestdeckung); auch das harte Limit von {limit} je Lauf "
                f"({kapazitaet_spitze:.2f}/Tag) baut den Rückstand nicht "
                f"fristgerecht ab. Takt, Limit oder Intervall in "
                f"{ssot_pfad} entscheiden (#912).")
        elif budget >= limit:
            funde.append(
                f"Frischhalte-Kadenz nur im Dauer-Spitzenbetrieb: {seiten} "
                f"Seiten brauchen {bedarf:.2f} Prüfungen/Tag ({noetig:.2f} "
                f"bei {mindest} % Mindestdeckung); der Plan verbraucht das "
                f"harte Limit von {limit} je Lauf "
                f"({kapazitaet_spitze:.2f}/Tag) vollständig. Ohne Reserve "
                f"ist das ein Dauer-Stau. Limit oder Intervall in "
                f"{ssot_pfad} entscheiden (#912).")
        elif kapazitaet + 1e-9 < noetig:
            funde.append(
                f"Frischhalte-Kadenz unterdeckt: {seiten} Seiten brauchen "
                f"{bedarf:.2f} Prüfungen/Tag ({noetig:.2f} bei {mindest} % "
                f"Mindestdeckung), der Lauf liefert {kapazitaet:.2f}/Tag "
                f"({budget} je Lauf × {laeufe:.2f} Läufe/Tag). Takt, Limit "
                f"oder Intervall in {ssot_pfad} entscheiden (#912).")
    else:
        if kapazitaet + 1e-9 < noetig:
            funde.append(
                f"Frischhalte-Kadenz unterdeckt: {seiten} Seiten brauchen "
                f"{bedarf:.2f} Prüfungen/Tag ({noetig:.2f} bei {mindest} % "
                f"Mindestdeckung), der Sockel liefert {kapazitaet:.2f}/Tag "
                f"({budget} je Lauf × {laeufe:.2f} Läufe/Tag); selbst mit "
                f"dem harten Limit wären es {kapazitaet_spitze:.2f}/Tag. "
                f"Takt, Limit oder Intervall in {ssot_pfad} entscheiden "
                f"(#912).")
        elif budget >= limit:
            funde.append(
                f"Frischhalte-Kadenz nur im Dauer-Spitzenbetrieb: {seiten} "
                f"Seiten brauchen {bedarf:.2f} Prüfungen/Tag ({noetig:.2f} "
                f"bei {mindest} % Mindestdeckung); der Sockel verbraucht "
                f"das harte Limit von {limit} je Lauf vollständig. "
                f"Limit oder Intervall in {ssot_pfad} entscheiden (#912).")
    if not puenktlich or not rueckstand:
        funde.append(
            f"Der Plan reißt eine Frist oder baut den Rückstand nicht "
            f"fristgerecht ab ({budget} je Lauf × {laeufe:.2f} Läufe/Tag). "
            f"Die Deckungsrechnung nennt die Ursache (#912).")
    # Der Spitzentag (04.11.2026, #1039). Dieselbe Aussage, derselbe Plan –
    # nur an dem Tag gemessen, an dem eine heute frische Seite zu spät käme.
    # Ohne diese Zeile ist die Wache am ruhigen Tag grün und am Bündeltag
    # rot, ohne dass sich Code oder Vertrag geändert hätten.
    if zahlen.get("spitze_stichtag") and not zahlen.get("spitze_puenktlich", True):
        funde.append(
            f"Spitzenlast reißt die Frist: am {zahlen['spitze_stichtag']} "
            f"kämen {int(zahlen.get('spitze_offen', 0))} Seiten zu spät, die "
            f"heute noch frisch sind. Das Budget von {budget} je Lauf × "
            f"{laeufe:.2f} Läufe/Tag bedient den Zulauf nicht – die Bündelung "
            f"der Prüftermine (`faktencheck` in den Seiten), der Takt oder das "
            f"Limit in {ssot_pfad} entscheidet. Nur den Stichtag zu messen "
            f"heißt, den ruhigsten Tag des Jahres zu prüfen (#1039).")
    return funde


# ============================================================
#  Texte
# ============================================================
def _zahl(wert: float, stellen: int = 2) -> str:
    """Deutsche Zahlenschreibweise – der Bericht ist ein Lesetext."""
    return f"{wert:.{stellen}f}".replace(".", ",")


def diagnose_zeilen(p: dict, markdown: bool = True) -> list[str]:
    """Die Deckungs-Wahrheit in Sätzen, die ein Mensch planen kann."""
    fett = (lambda s: f"**{s}**") if markdown else (lambda s: str(s))
    bedarf = _zahl(p["bedarf_je_tag"])
    angebot = _zahl(p["kapazitaet_je_tag"])
    deckung = _zahl(p["deckung_prozent"], 0) + " %"
    zeilen = [
        f"- Bestand: {fett(p['artikel'])} Seiten · "
        f"fällig heute: {fett(p['faellig'])} · "
        f"überfällig: {fett(p['ueberfaellig'])} "
        f"(max. {p['ueberfaellig_max_tage']} Tage)",
        f"- Bedarf: {fett(bedarf)} Prüfungen/Tag "
        f"({_zahl(p['bedarf_je_woche'], 1)}/Woche) · Angebot: "
        f"{fett(angebot)}/Tag "
        f"(Budget {p['budget']} × {_zahl(p['laeufe_je_tag'])} Läufe/Tag) · "
        f"Deckung {fett(deckung)}",
    ]
    if p.get("verletzungen_folge") and p["puenktlich"] is False:
        zeilen.append(f"- ⚠️ {p['verletzungen_folge_seiten']} Seiten reißen eine "
                      "Folgeprüfung im Simulationshorizont – Mehrbedarf ist eingeplant")
    if p["abbau_tage"] is not None:
        ab = f"{p['abbau_tage']} Tagen"
        zeilen.append(f"- Rückstand abgebaut in {fett(ab)} "
                      f"(Frist: {p['nachhol_frist_tage']} Tage)")
    elif p["ueberfaellig"] or p["faellig"]:
        zeilen.append(f"- Rückstand: {fett('nicht abbaubar')} im Horizont von "
                      f"{p['horizont_tage']} Tagen – Kadenz unterdeckt")
    if p["naechste_frist"]:
        n = p["naechste_frist"]
        zeilen.append(f"- Nächste Frist: `{n['slug']}` am {n['frist']} "
                      f"(in {n['restlaufzeit']} Tagen)")
    if p.get("spitze_geprueft"):
        if p.get("spitze_stichtag") and not p.get("spitze_puenktlich", True):
            zeilen.append(
                f"- ⚠️ Spitzentag: Am {p['spitze_stichtag']} kämen "
                f"{int(p.get('spitze_offen', 0))} von {int(p.get('spitze_frisch', 0))} "
                f"heute noch frischen Seiten zu spät – das Budget von "
                f"{p['budget']} je Lauf bedient den Zulauf nicht (#1039)")
        else:
            zeilen.append(f"- Spitzentag mitgemessen: {p['spitze_geprueft']} "
                          "Bündeltage im Horizont – kein Befund")
    if p["verletzungen_neu"]:
        seiten = "Seite" if p["verletzungen_neu"] == 1 else "Seiten"
        zeilen.append(f"- ⚠️ {p['verletzungen_neu']} {seiten} mit ZUKÜNFTIGER "
                      "Frist würden gerissen – das ist die Zahl, die zählt")
    return zeilen


def klartext(p: dict, hinweise: list[str] | None = None) -> str:
    zeilen = ["Faktenfrische-Deckung (einzige Fälligkeitsregel: faktenfrische.faelligkeit)", ""]
    zeilen += diagnose_zeilen(p, markdown=False)
    if hinweise:
        zeilen += ["", "Plan: " + " · ".join(hinweise)]
    return "\n".join(zeilen)


# ============================================================
#  Selbsttest (eingefrorene Probetage – Uhr-Zwang)
# ============================================================
PROBETAG = dt.date(2026, 10, 29)


def _cfg_probe(budget: int = 3, limit: int = 10, laeufe: float = 1.0) -> dict:
    return {
        "intervalle": {"ymyl_tage": 45, "standard_tage": 90, "saison_tage": 30,
                       "erstrecherche_bei_erstellung": True},
        "budget": {"max_artikel_pro_lauf": budget, "auto_skalierung": True,
                   "hartes_limit_pro_lauf": limit},
        "planung": {"vorlauf_tage": 7, "nachhol_frist_tage": 7,
                    "horizont_tage": 120, "min_deckung_prozent": 110},
    }


def _probe_ueberfaellig(n: int, start: int = 0) -> list[dict]:
    """`n` saisonale Seiten, alle seit gestern überfällig (Intervall 30)."""
    basis = PROBETAG - dt.timedelta(days=31)   # Frist = gestern
    return [{"slug": f"probe-{start + i:03d}",
             "titel": "Heizung Winter saisonal",
             "beschreibung": "", "keywords": ["Heizung"], "pillar": "energie",
             "faktencheck": basis}
            for i in range(n)]


def _probe_gestreut(n: int, abstand: int = 1) -> list[dict]:
    """`n` saisonale Seiten mit gestreuten Prüfdaten (kein Stau-Muster)."""
    return [{"slug": f"streu-{i:03d}",
             "titel": "Heizung Winter saisonal",
             "beschreibung": "", "keywords": ["Heizung"], "pillar": "energie",
             "faktencheck": PROBETAG - dt.timedelta(days=5 + i * abstand)}
            for i in range(n)]


def selftest() -> int:
    fehler: list[str] = []
    faelle = [0]

    def pruefe(name, ist, soll):
        faelle[0] += 1
        if ist != soll:
            fehler.append(f"{name}: {ist!r} != {soll!r}")

    # ST1 – cron wird gelesen, nicht geraten ---------------------------
    pruefe("ST1a", laeufe_je_tag(["40 4 * * 2,4"])[0], 2 / 7)
    pruefe("ST1b", laeufe_je_tag(["40 4 * * *"])[0], 1.0)
    pruefe("ST1c", laeufe_je_tag(["0 */6 * * *"])[0], 4.0)
    pruefe("ST1d", laeufe_je_tag(["0 6 * * 1-5"])[0], 5 / 7)
    pruefe("ST1e", laeufe_je_tag(["0 6 1 * *"])[0], None)   # Kalenderbindung
    pruefe("ST1f", laeufe_je_tag(["quatsch"])[0], None)
    pruefe("ST1g", laeufe_je_tag([])[0], None)
    pruefe("ST1h", laeufe_je_tag(["0 6 * * 7"])[0], 1 / 7)   # Sonntag = 7
    pruefe("ST1i", feld_werte("*/0", 0, 23), None)

    # ST2 – Bedarf ist Σ 1/Intervall, nicht die Anzahl Fälliger --------
    cfg = _cfg_probe()
    gestreut = _probe_gestreut(30, abstand=1)   # 30 saisonale Seiten
    pruefe("ST2a", round(bedarf_je_tag(gestreut, cfg, PROBETAG), 4), 1.0)
    alt = _probe_ueberfaellig(60)               # 60 überfällige Seiten
    pruefe("ST2b", round(bedarf_je_tag(alt, cfg, PROBETAG), 4), 2.0)
    pruefe("ST2c", len([e for e in eintraege_bauen(alt, cfg, PROBETAG)
                        if e["bereits_faellig"]]), 60)
    # Der Bedarf ändert sich nicht, weil Seiten überfällig sind.
    pruefe("ST2d", round(bedarf_je_tag(alt, cfg, PROBETAG), 4),
           round(bedarf_je_tag(_probe_gestreut(60, abstand=0), cfg, PROBETAG), 4))

    # ST3 – Dieselbe Rechnung, die den Dauer-Alarm #912 erklärt --------
    p_schwach = plan(alt, cfg, 3, 2 / 7, PROBETAG,
                     lauftage=lauf_tage(["40 4 * * 2,4"], PROBETAG, 120))     # Budget 3, Di+Do
    pruefe("ST3a", round(p_schwach["deckung_prozent"]), 43)   # 6/7 gegen 2,0
    pruefe("ST3b", p_schwach["rueckstand_abgebaut"], False)
    p_stark = plan(alt, cfg, 10, 1.0, PROBETAG)        # täglich, Limit 10
    pruefe("ST3c", p_stark["rueckstand_abgebaut"], True)
    pruefe("ST3d", p_stark["abbau_tage"], 5)           # 60 Seiten / 10 je Tag
    pruefe("ST3e", p_stark["deckung_prozent"] >= 110, True)
    pruefe("ST3f", p_schwach["deckung_prozent"] < 110, True)

    # ST4 – EDF: Die früheste Frist wird zuerst bedient -----------------
    gemischt = _probe_ueberfaellig(5) + [{
        "slug": "spaet-1", "titel": "Heizung Winter saisonal",
        "beschreibung": "", "keywords": ["Heizung"], "pillar": "energie",
        "faktencheck": PROBETAG - dt.timedelta(days=20)}]   # Frist in 10 Tagen
    p_edf = plan(gemischt, cfg, 2, 1.0, PROBETAG)
    pruefe("ST4a", p_edf["abbau_tage"], 2)      # 5 Altlasten / 2 je Tag → Tag 2
    pruefe("ST4b", p_edf["verletzungen_neu"], 0)

    # ST5 – Vorlauf: Arbeit beginnt, BEVOR die Frist reißt --------------
    eintrag = eintraege_bauen(_probe_gestreut(1, abstand=0), cfg, PROBETAG)[0]
    # Prüfung vor 5 Tagen → Frist in 25 Tagen, arbeitbar ab Tag 18.
    pruefe("ST5a", eintrag["frist"], PROBETAG + dt.timedelta(days=25))
    pruefe("ST5b", eintrag["ziel"], PROBETAG + dt.timedelta(days=18))
    cfg_ohne = _cfg_probe()
    cfg_ohne["planung"]["vorlauf_tage"] = 0
    pruefe("ST5c", eintraege_bauen(_probe_gestreut(1, abstand=0), cfg_ohne,
                                   PROBETAG)[0]["ziel"],
           PROBETAG + dt.timedelta(days=25))

    # ST6 – Empfehlung: kleinste Zahl, die den Rückstand fristgerecht abbaut
    emp = empfohlenes_budget(alt, cfg, 1.0, PROBETAG)
    pruefe("ST6a", emp["erreicht"], True)
    pruefe("ST6b", emp["budget"], 8)     # 60 Seiten / 8 je Tag = 8 Kalendertage
    pruefe("ST6c", emp["budget"] <= emp["limit"], True)

    # ST7 – Strukturelle Unterdeckung wird ausgesprochen, nicht versteckt
    emp_viele = empfohlenes_budget(_probe_ueberfaellig(200), cfg, 1.0, PROBETAG)
    pruefe("ST7a", emp_viele["erreicht"], False)      # 200 Seiten, Limit 10/Tag
    pruefe("ST7b", emp_viele["budget"], 10)

    # ST8 – Kein Wunder bei leerem Bestand ------------------------------
    leer = plan([], cfg, 3, 1.0, PROBETAG)
    pruefe("ST8a", (leer["faellig"], leer["puenktlich"]), (0, True))
    pruefe("ST8b", leer["deckung_prozent"], 100.0)

    # ST9 – Erstrecherche hat keine Frist, ist aber sofort arbeitbar -----
    neu = [{"slug": "neu-1", "titel": "Kfz-Versicherung", "beschreibung": "",
            "keywords": ["Kfz-Versicherung"], "pillar": "", "faktencheck": None}]
    e_neu = eintraege_bauen(neu, cfg, PROBETAG)[0]
    pruefe("ST9a", (e_neu["frist"], e_neu["ziel"]), (PROBETAG, PROBETAG))
    pruefe("ST9b", plan(neu, cfg, 1, 1.0, PROBETAG)["rueckstand_abgebaut"], True)

    # ST10 – Die Urteilsformel ist monoton in der Kapazität -------------
    vorher = plan(alt, cfg, 4, 1.0, PROBETAG)["abbau_tage"]
    nachher = plan(alt, cfg, 8, 1.0, PROBETAG)["abbau_tage"]
    pruefe("ST10a", nachher <= vorher, True)

    # ST11 – Der Rückstand wird benannt, nicht als „alles gut“ verkauft --
    zeilen = "\n".join(diagnose_zeilen(p_schwach, markdown=False))
    pruefe("ST11a", "Deckung 43 %" in zeilen, True)
    pruefe("ST11b", p_schwach["rueckstand_abgebaut"], False)

    # ST12 – C45-Urteil: Plan, Reserve und Dauer-Spitze getrennt (#1023)
    basis = {
        "seiten": 112, "bedarf": 2.73, "mindest": 110, "laeufe": 1.0,
        "sockel": 4, "limit": 10, "budget": 4,
        "kapazitaet": 4.0, "kapazitaet_spitze": 10.0,
        "auto": True, "empfehlung_erreicht": True,
        "plan_puenktlich": True, "plan_rueckstand_abgebaut": True,
    }
    pruefe("ST12a", c45_urteil(basis), [])
    pruefe("ST12b", any("Dauer-Spitzenbetrieb" in f
                        for f in c45_urteil(dict(basis, budget=10,
                                                 kapazitaet=10.0))), True)
    pruefe("ST12c", any("unterdeckt" in f
                        for f in c45_urteil(dict(basis, budget=3,
                                                 kapazitaet=3.0))), True)
    pruefe("ST12d", any("strukturell" in f
                        for f in c45_urteil(dict(basis, budget=10,
                                                 kapazitaet=10.0,
                                                 empfehlung_erreicht=False))), True)
    pruefe("ST12e", c45_urteil(dict(basis, auto=False)), [])
    pruefe("ST12f", any("Ungültiger Korridor" in f
                        for f in c45_urteil(dict(basis, sockel=11, limit=10,
                                                 budget=11, kapazitaet=11.0,
                                                 kapazitaet_spitze=10.0))), True)
    pruefe("ST12g", any("Frist" in f
                        for f in c45_urteil(dict(basis, plan_puenktlich=False))), True)

    # ST13 – Der Bündeltag wird mitgemessen (#1039) -----------------------
    stau = _probe_ueberfaellig(0) + [{
        "slug": f"bundel-{i:03d}", "titel": "Heizung Winter saisonal",
        "beschreibung": "", "keywords": ["Heizung"], "pillar": "energie",
        "faktencheck": PROBETAG - dt.timedelta(days=20)}   # 10 Seiten, Frist gleich
        for i in range(10)]
    kandidaten = spitzenlast_stichtage(stau, cfg, PROBETAG)
    pruefe("ST13a", [d.isoformat() for d in kandidaten],
           [PROBETAG.isoformat(), (PROBETAG + dt.timedelta(days=3)).isoformat(),
            (PROBETAG + dt.timedelta(days=10)).isoformat()])
    finde = spitzenlast_stichtag(stau, cfg, 1, 1.0, PROBETAG)
    pruefe("ST13b", (finde["stichtag"].isoformat(), finde["offen"],
                     finde["frisch"]),
           ((PROBETAG + dt.timedelta(days=3)).isoformat(), 2, 10))
    pruefe("ST13c", spitzenlast_stichtag(stau, cfg, 4, 1.0, PROBETAG), None)
    # "Nicht gemessen" darf nie wie "grün" aussehen (C33):
    # spitze_geprueft steht immer in den Zahlen.
    zahlen_gruen = spitze_zahlen(stau, cfg, 4, 1.0, PROBETAG)
    pruefe("ST13d", ("spitze_geprueft" in zahlen_gruen,
                     "spitze_stichtag" in zahlen_gruen), (True, False))
    zahlen_rot = spitze_zahlen(stau, cfg, 1, 1.0, PROBETAG)
    pruefe("ST13e", (zahlen_rot["spitze_puenktlich"],
                     zahlen_rot["spitze_stichtag"], zahlen_rot["spitze_offen"]),
           (False, (PROBETAG + dt.timedelta(days=3)).isoformat(), 2))
    pruefe("ST13f", any("Spitzenlast" in f for f in c45_urteil(
        dict(basis, **zahlen_rot))), True)

    if fehler:
        print("❌ Selbsttest Faktenfrische-Kapazität rot:")
        for f in fehler:
            print("   " + f)
        return 1
    print(f"✅ Selbsttest Faktenfrische-Kapazität: {faelle[0]} Fälle grün.")
    return 0


# ============================================================
#  Hauptlauf
# ============================================================
def bestand(scope: str = "alle") -> list[dict]:
    return ff.alle_artikel(scope)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Faktenfrische-Deckung: Bedarf, Angebot, Abbauplan")
    p.add_argument("--json", action="store_true", help="maschinenlesbar")
    p.add_argument("--wache", action="store_true",
                   help="Exit 1, wenn der Rückstand nicht fristgerecht abbaubar ist")
    p.add_argument("--budget-empfehlung", action="store_true",
                   help="nur das empfohlene Budget je Lauf ausgeben")
    p.add_argument("--budget", type=int, help="Budget je Lauf überschreiben")
    p.add_argument("--laeufe", type=float, help="Läufe je Tag überschreiben")
    p.add_argument("--scope", choices=("alle", "posts", "pillar"), default="alle")
    p.add_argument("--stichtag", help="Probetag (ISO) – nur für Nachweise")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        return selftest()

    try:
        cfg = ff.lade_config()
    except SystemExit as exc:  # Vertrag nicht ladbar → Werkzeugfehler
        print(f"🛑 {exc}", file=sys.stderr)
        return 2

    try:
        stichtag = (dt.date.fromisoformat(args.stichtag) if args.stichtag
                    else ff.heute())
    except ValueError:
        print("🛑 --stichtag ist kein ISO-Datum", file=sys.stderr)
        return 2

    laeufe, hinweise = laeufe_aus_workflow()
    if args.laeufe:
        laeufe = float(args.laeufe)
    if not laeufe:
        # Ohne lesbaren Plan ist jede Deckungsaussage geraten (fail-closed).
        print("🛑 Laufplan nicht lesbar – Deckung nicht beweisbar "
              f"({'; '.join(hinweise)})", file=sys.stderr)
        return 2

    horizont = int(planung(cfg)["horizont_tage"])
    lauftage = lauftage_aus_workflow(stichtag, horizont)
    if args.laeufe:
        lauftage = ({stichtag + dt.timedelta(days=i) for i in range(horizont + 1)}
                    if args.laeufe == 1 else None)
    if lauftage is None:
        print("🛑 Laufkalender nicht beweisbar – keine Wochenmittel als Tagesplan", file=sys.stderr)
        return 2

    artikel = bestand(args.scope)
    if not artikel:
        print("🛑 Kein Bestand lesbar – Deckung nicht beweisbar", file=sys.stderr)
        return 2

    b = budget_vorgaben(cfg)
    budget = int(args.budget or b["max_artikel_pro_lauf"])
    # Ausgangspunkt der Projektion ist HEUTE (#1107): Ein Stichtag in der
    # Zukunft wird als Trajektorie gerechnet, die der Bot bis dahin zurücklegt.
    basis = ff.heute()
    try:
        emp = empfohlenes_budget(artikel, cfg, laeufe, stichtag,
                                 lauftage=lauftage, basis=basis)
    except ValueError as exc:
        print(f"🛑 Deckung nicht beweisbar: {exc}", file=sys.stderr)
        return 2

    if args.budget_empfehlung:
        print(emp["budget"])
        return 0

    # Die Wache prüft den Plan, den die Automatik wirklich fährt:
    # bei Auto-Skalierung das empfohlene Budget, nicht nur den Sockel.
    if not args.budget and b.get("auto_skalierung"):
        budget = int(emp["budget"])
    try:
        aktueller = plan(artikel, cfg, budget, laeufe, stichtag,
                         lauftage=lauftage, basis=basis)
        ergebnis = dict(aktueller)
        ergebnis["empfohlenes_budget"] = emp["budget"]
        ergebnis["empfehlung_erreicht"] = emp["erreicht"]
        ergebnis["hartes_limit"] = emp["limit"]
        ergebnis["sockel"] = emp["sockel"]
        ergebnis["plan_hinweise"] = hinweise
        # Der Spitzentag wird IMMER gemessen und IMMER berichtet (#1039).
        # "Nicht gemessen" darf nie wie "grün" aussehen (C33).
        ergebnis.update(spitze_zahlen(artikel, cfg, budget, laeufe,
                                      stichtag, horizont, basis=basis))
    except ValueError as exc:
        print(f"🛑 Spitzenlast nicht beweisbar: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 0

    print(klartext(ergebnis, hinweise))
    if emp["erreicht"] and emp["budget"] > budget:
        print(f"\n→ Empfohlenes Budget für diesen Lauf: {emp['budget']} "
              f"(Sockel {emp['sockel']}, Limit {emp['limit']})")
    elif not emp["erreicht"]:
        print(f"\n⚠️ Auch mit dem harten Limit von {emp['limit']} je Lauf ist der "
              "Rückstand nicht fristgerecht abbaubar – Kadenz oder Intervall "
              "müssen entschieden werden (SSOT faktenfrische.yaml).")

    if args.wache:
        if not emp["erreicht"]:
            print("::error::Faktenfrische strukturell unterdeckt – auch das harte "
                  "Limit baut den Rückstand nicht fristgerecht ab (#912).")
            return 1
        if not aktueller["puenktlich"] or not aktueller["rueckstand_abgebaut"]:
            print("::error::Der laufende Plan reißt eine Frist oder baut den Rückstand "
                  "nicht rechtzeitig ab – Kapazität erhöhen (#912).")
            return 1
        if ergebnis.get("spitze_stichtag") and not ergebnis.get("spitze_puenktlich", True):
            print(f"::error::Spitzentag reißt die Frist: am {ergebnis['spitze_stichtag']} "
                  f"kämen {int(ergebnis.get('spitze_offen', 0))} von "
                  f"{int(ergebnis.get('spitze_frisch', 0))} heute noch frischen Seiten "
                  f"zu spät – Bündelung der Prüftermine, Takt oder Limit in "
                  f"data/agent_reach/faktenfrische.yaml entscheiden (#1039).")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
