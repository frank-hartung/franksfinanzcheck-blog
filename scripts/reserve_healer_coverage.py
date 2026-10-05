#!/usr/bin/env python3
"""
reserve_healer_coverage.py – Deckungs-Wache der Reserve-Produktionslinie.

WARUM DIESE DATEI EXISTIERT (Reparatur 22.09.2026, Issue #349, Run
35706157938):
  Der nächtliche Reserve-Lauf zertifiziert seine Kandidaten mit den ECHTEN
  Produktions-Gates (quality_score + publish_gate STRICT). Jedes dieser Gates
  darf einen Kandidaten ablehnen. Damit der Vorrat sein Ziel (RESERVE_TARGET)
  überhaupt erreichen KANN, muss jede ablehnende Regel einen Heiler haben, der
  VOR der Zertifizierung läuft.

  Genau dieser Vertrag war am 22.09. verletzt – aber niemand prüfte ihn:

    * `publish_gate` erzwingt als Kriterium 5 den Intent-Wächter
      (`affiliate_intent_guard.py`, IW0–IW9).
    * Die Heiler-Kette der Reserve (`reserve_finisher.HEALER_CHAIN`) fuhr ihn
      NICHT – obwohl der Wächter seinen Heil-Aufruf `--heal --file <pfad>`
      ausdrücklich für die Reserve mitbringt.
    * Folge: Der Konvergenz-Nachschub erzeugte einen Kandidaten, der Wächter
      meldete „IW8 – Anker nennt kein Angebot“, die Zertifizierung läuft im
      STRICT-DRY-RUN (schreibt nicht) → 5/6. Das harte End-Gate
      („Stock shortage must not look successful“) wurde rot, der Lauf
      scheiterte – obwohl der Fund sieben Minuten später vom täglichen
      Affiliate-Lauf mit DEMSELBEN Skript byte-identisch geheilt wurde.

  Dieselbe Klasse hatte am 15.09.2026 schon den CTA-Heiler erwischt (#295:
  `affiliate_integrity_gate.py --heal` fehlte in der Kette). Die Reparatur
  damals war ein einzelner, handverdrahteter Eintrag – die Klasse blieb:
  Ein NEUES Gate ohne Heiler wäre wieder still durchgegangen und hätte den
  Vorrat Nacht für Nacht unerreichbar gemacht.

  Diese Wache schließt die Klasse. Sie ENTDECKT die Regeln, statt sie
  abzutippen (dasselbe Prinzip wie `selftest_runner.py`):

    1. Regeln des harten Publish-Gates werden aus `publish_gate.py` gelesen
       (jede Funktion `<regel>_failures` ist eine ablehnende Regel).
    2. Für jede Regel muss die Tabelle unten die Heiler nennen, die sie in
       `reserve_finisher.HEALER_CHAIN` decken – oder eine AUSNAHME mit
       Begründung (dann gehört der Befund ausdrücklich einem Menschen).
    3. Geprüft wird beides: Der genannte Heiler läuft in der Kette UND das
       Skript existiert wirklich in `scripts/` (ein Tippfehler deckt nichts).
    4. Eine Ausnahme, deren Regel es nicht mehr gibt, ist selbst ein Befund
       („eine Ausnahme für etwas, das es nicht mehr gibt, ist eine stille
       Lücke“ – Kodex des Selbsttest-Runners).
    5. Eine Regel, für die weder Heiler noch Ausnahme existiert, ist der
       Befund: fail-closed, mit Klartext-Diagnose.

  Der Deckungs-Bericht steht in RESERVE-FINISH-REPORT.md und im Lauf-Log;
  reserve_finisher.py ruft die Wache VOR seiner Heiler-Kette auf und bricht
  bei einer Lücke mit rc=1 ab – ein struktureller Fehler wird damit sofort
  und laut sichtbar, statt als „5/6 ohne Grund“ am End-Gate.

ERWEITERUNG 05.10.2026 (WF-B594, Issue #594): Zweite Deckung `loeschdeckung()`
  – dieselbe Logik für den Weg nach UNTEN. Siehe Kommentarblock vor der
  Funktion: Ein Triage-Blocker, der „heilbar" heißt, ohne dass sein Heiler in
  der Kette läuft, ist eine Todesfalle für Entwürfe; ein Blocker ohne Klasse
  ist eine unentschiedene Zuständigkeit. Beides stoppt jetzt den Lauf.

MODI:
    python3 scripts/reserve_healer_coverage.py            # Bericht (Mensch)
    python3 scripts/reserve_healer_coverage.py --json     # Maschine
    python3 scripts/reserve_healer_coverage.py --selftest # Sabotage-Schutz

EXIT: 0 = jede ablehnende Regel ist gedeckt · 1 = Lücke (fail-closed)
      · 2 = Werkzeugfehler/Selbsttest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PUBLISH_GATE = SCRIPTS / "publish_gate.py"

# ---------------------------------------------------------------------------
#  VERTRAG (eine Quelle): ablehnende Regel des Publish-Gates → Heiler in der
#  Reserve-Kette. Die Regel-Namen sind die Funktionsnamen in publish_gate.py
#  (`<regel>_failures`); sie werden dort GELESEN, nicht abgetippt.
# ---------------------------------------------------------------------------
REGEL_HEILER: dict[str, tuple[str, ...]] = {
    # Artikelgenaue Erst-/Folgerecherche: fehlende Faktennachweise werden
    # nicht heuristisch simuliert, sondern mit dem echten Rechercheweg
    # nachgezogen. Bleibt die Recherche ohne Beleg, blockiert das Gate.
    "faktenfrische_failures": ("faktenfrische.py",),
    # Länge/Struktur (Floor) – deterministischer Verlängerer, entwurfsfähig.
    "check_length_failures": ("check_length.py",),
    # SEO-Audit: Meta-Längen/Felder, Titel, Alt-Texte.
    "seo_audit_failures": ("meta_optimizer.py", "check_titles.py",
                           "check_covers.py"),
    # A1-A8 des Profi-Checks (Offenlegung, E-E-A-T, Trust-Box, CTA …).
    "affiliate_profi_failures": ("affiliate_profi_check.py",),
    # Strukturell intakte, gerenderte CTA-Boxen (Vorfall 14.08.2026).
    "affiliate_integrity_failures": ("affiliate_integrity_gate.py",),
    # IW0–IW9: Anker/Satz/Thema ↔ echtes Angebot (#349).
    "affiliate_intent_failures": ("affiliate_intent_guard.py",),
    # R5: unvollständiger/abgebrochener Titel (Cover-Text).
    "title_integrity_failures": ("check_titles.py",),
    # Keyword-Score < 60 (hart). Am Gate heilt nur der LIVE-Pfad selbst –
    # Entwürfe überspringt `keyword_self_heal_candidates()` bewusst (#349).
    "keyword_failures": ("keyword_optimizer.py",),
    # Lesbarkeit < 75. Es gibt KEINEN deterministischen Satzbau-Heiler; das
    # KI-Polish (`profi_polish.py`) kürzt Sätze/Absätze und ist der einzige
    # Hebel der Kette (Live-Kodex, Phase 2).
    "readability_failures": ("profi_polish.py",),
    # R2/R3/R5/R7/R8: Absatz-Splitter heilt R5, URL-Hygiene heilt R8-URL.
    "textverstaendnis_failures": ("r5_absatz_splitter.py",
                                  "fix_url_hygiene.py"),
}

# Ausnahmen brauchen eine Begründung – und altern nicht still. Die Liste ist
# Pflicht, damit eine künftige Regel nicht zwischen „gedeckt“ und „vergessen“
# fällt.
AUSNAHMEN: dict[str, str] = {
    # Werbe-Offenlegung O1–O7 (28.09.2026). Bewusst OHNE Heiler in der
    # Reserve-Kette: Die Kennzeichnung schreibt kein Artikeltext, sondern das
    # Layout (layouts/_partials/ff_offenlegung.html) aus dem Partnerregister
    # (data/affiliate_ziele.yaml). Ein Kandidat kann diese Regel also gar
    # nicht durch eigene Textarbeit verletzen – ein Befund heißt immer:
    # Template, CSS oder Register sind kaputt. Ein „Heiler“ am Entwurf würde
    # genau den Schaden übertünchen, den die Wache melden soll (Kodex C15:
    # Beweisen ist nicht Heilen). Zuständig ist ein Mensch; der nächste
    # Schritt steht in jedem Befund und in docs/ANLEITUNG-OFFENLEGUNG.md.
    "offenlegung_failures":
        "Kennzeichnung entsteht im Template, nicht im Artikeltext – ein "
        "Befund ist ein Layout-/Registerdefekt und gehört einem Menschen "
        "(C15). Heilung am Kandidaten würde den Defekt verdecken.",
    # YMYL-Freigabe (02.10.2026): Absichtlich KEIN Auto-Heiler. Prüfer,
    # Zahlenprotokoll, Änderungsgrund und Freigabe-Hash sind menschliche
    # Redaktionsakte. Die Reserve behält den Kandidaten zunächst; nach der
    # Quarantäne verlässt er nur den automatischen Pool, nie das Repository.
    "editorial_review_failures":
        "Fachliche Freigaben dürfen nicht automatisiert erzeugt werden. "
        "Hochrisiko-Kandidaten bleiben als Review-Hold erhalten; Quellen, "
        "Zahlen und Prüfer werden redaktionell dokumentiert und versiegelt.",
}

RE_REGEL = re.compile(r"(?m)^def ([a-z0-9_]+_failures)\(")
# (Hinweis auf Aufrufe wird nicht geparst: die Kette ist die Wahrheit.)


def gate_regeln(text: str) -> list[str]:
    """Ablehnende Regeln des Publish-Gates – aus dem Quelltext gelesen."""
    return sorted(set(RE_REGEL.findall(text or "")))


def chain_skripte(chain: list | None = None) -> set[str]:
    """Skriptnamen der Reserve-Heiler-Kette (SSOT: reserve_finisher)."""
    if chain is None:
        sys.path.insert(0, str(SCRIPTS))
        import reserve_finisher as rf
        chain = rf.HEALER_CHAIN
    return {eintrag[0] for eintrag in chain or []}


def deckung(publish_gate_text: str | None = None,
            chain: list | None = None,
            regeln: dict | None = None,
            ausnahmen: dict | None = None,
            scripts_dir: Path | None = None) -> dict:
    """Deckungs-Bericht: gedeckt / Ausnahmen / Lücken / tote Einträge.

    Rein lesend und injizierbar (Selbsttest ohne echtes Repo). Wer `regeln`
    injiziert, sollte auch `ausnahmen` injizieren: sonst prüft ein Fixture
    gegen die echten Ausnahmen und wird rot, sobald das Repo eine neue
    (völlig korrekte) Ausnahme bekommt.
    """
    scripts_dir = Path(scripts_dir) if scripts_dir else SCRIPTS
    if publish_gate_text is None:
        publish_gate_text = PUBLISH_GATE.read_text(encoding="utf-8")
    tabelle = dict(REGEL_HEILER if regeln is None else regeln)
    tabelle_ausnahmen = dict(AUSNAHMEN if ausnahmen is None
                             else ausnahmen)
    vorhanden = chain_skripte(chain)

    gefunden = gate_regeln(publish_gate_text)
    bericht = {"regeln": gefunden, "gedeckt": [], "ausnahmen": [],
               "luecken": [], "tote_ausnahmen": [], "fehlende_heiler": [],
               "unbenutzte_eintraege": []}

    for regel in gefunden:
        heiler = tabelle.get(regel)
        if heiler:
            fehlend = [h for h in heiler
                       if not (scripts_dir / h).is_file()]
            if fehlend:
                bericht["fehlende_heiler"].append(
                    {"regel": regel, "heiler": fehlend})
                bericht["luecken"].append(
                    {"regel": regel, "art": "heiler-fehlt-im-repo",
                     "heiler": fehlend})
                continue
            nicht_verdrahtet = [h for h in heiler if h not in vorhanden]
            if nicht_verdrahtet:
                bericht["luecken"].append(
                    {"regel": regel, "art": "nicht-in-der-kette",
                     "heiler": nicht_verdrahtet})
                continue
            bericht["gedeckt"].append({"regel": regel, "heiler": list(heiler)})
            continue
        grund = tabelle_ausnahmen.get(regel)
        if grund is None:
            bericht["luecken"].append(
                {"regel": regel, "art": "keine-deckung"})
            continue
        if not str(grund).strip():
            bericht["luecken"].append(
                {"regel": regel, "art": "ausnahme-ohne-begruendung"})
            continue
        bericht["ausnahmen"].append({"regel": regel, "grund": str(grund)})

    # Ausnahme/Deckungs-Eintrag für eine Regel, die es nicht mehr gibt:
    # eine stille Lücke, die niemand mehr prüft.
    for regel, heiler in tabelle.items():
        if regel in gefunden:
            continue
        bericht["tote_ausnahmen"].append(
            {"regel": regel, "art": "regel-verschwunden",
             "heiler": list(heiler)})
    for regel, grund in tabelle_ausnahmen.items():
        if regel not in gefunden and regel not in tabelle:
            bericht["tote_ausnahmen"].append(
                {"regel": regel, "art": "ausnahme-fuer-verschwundene-regel",
                 "grund": grund})
    # Ein Eintrag, der eine Regel deckt, die gar kein Gate mehr prüft:
    # harmlos, aber sichtbar (Hygiene) – kein Befund.
    bericht["unbenutzte_eintraege"] = [r for r in tabelle
                                       if r not in gefunden]
    return bericht


# ---------------------------------------------------------------------------
#  ZWEITE DECKUNG (05.10.2026, Vorgang WF-B594, Issue #594):
#  Triage-Blocker ↔ Heiler ↔ LÖSCHRECHT.
#
#  Die erste Deckung oben bewacht den Weg nach OBEN (Gate-Regel braucht einen
#  Heiler, sonst ist der Zielbestand unerreichbar). #594 hat gezeigt, dass der
#  Weg nach UNTEN genauso bewacht gehört: `reserve_janitor.py` löschte
#  Entwürfe, deren Blocker („laenge:", „interne links:") von KEINEM Werkzeug
#  der Kette bearbeitet wurden – die Löschliste war faktisch die
#  Produktionsliste der Nacht (Commit c56382b: 8 Artikel, 24 Cover).
#
#  Diese Wache prüft deshalb drei Dinge gegeneinander, alle drei GELESEN:
#    1. Welche Blocker kann `draft_triage.classify()` überhaupt erzeugen?
#       (`reserve_blocker_klassen.triage_blocker_praefixe()` liest die Quelle)
#    2. Ist jeder davon in `reserve_blocker_klassen.KLASSEN` klassifiziert?
#       Ein unklassifizierter Blocker ist fail-closed nie löschbar – aber er
#       ist eine Lücke, weil niemand entschieden hat, wem er gehört.
#    3. Hat jeder HEILBARE Blocker seinen Heiler WIRKLICH in
#       `reserve_finisher.HEALER_CHAIN`? Sonst ist „heilbar" eine Behauptung:
#       Der Entwurf bleibt blockiert, der Janitor sieht ihn jede Nacht wieder,
#       und die Reserve verliert Material, das nie eine Chance hatte.
#  Unheilbare Klassen brauchen stattdessen eine Begründung im Klartext – wer
#  Text vernichtet, muss sagen warum.
# ---------------------------------------------------------------------------
def loeschdeckung(praefixe: list[str] | None = None,
                  klassen: tuple[dict, ...] | None = None,
                  chain: list | None = None,
                  scripts_dir: Path | None = None) -> dict:
    """Deckungs-Bericht für das Löschrecht des Janitors (fail-closed).

    Rein lesend und injizierbar (Selbsttest ohne echtes Repo).
    """
    sys.path.insert(0, str(SCRIPTS))
    import reserve_blocker_klassen as bk

    scripts_dir = Path(scripts_dir) if scripts_dir else SCRIPTS
    tabelle = tuple(bk.KLASSEN if klassen is None else klassen)
    if praefixe is None:
        praefixe = bk.triage_blocker_praefixe()
    vorhanden = chain_skripte(chain)
    # Der Kettenläufer selbst ist ein Heiler: `reserve_finisher.lift_to_today()`
    # datiert jeden Kandidaten auf heute um und zieht dabei `lastmod` über
    # `sync_lastmod_to_date()` verlustfrei nach – noch vor dem ersten Eintrag
    # der Kette. Er steht deshalb nie IN der Liste, deckt aber nachweislich.
    vorhanden.add("reserve_finisher.py")

    bericht = {"blocker": sorted(praefixe), "heilbar": [], "unheilbar": [],
               "menschlich": [], "luecken": [], "tote_eintraege": []}
    index = {e["praefix"]: e for e in tabelle}

    for praefix in sorted(praefixe):
        treffer = next((e for e in tabelle
                        if praefix.startswith(e["praefix"])), None)
        if treffer is None:
            bericht["luecken"].append(
                {"blocker": praefix, "art": "unklassifiziert"})
            continue
        klasse = treffer["klasse"]
        if klasse == bk.HEILBAR:
            heiler = list(treffer.get("heiler") or ())
            if not heiler:
                bericht["luecken"].append(
                    {"blocker": praefix, "art": "heilbar-ohne-heiler"})
                continue
            fehlend = [h for h in heiler if not (scripts_dir / h).is_file()]
            if fehlend:
                bericht["luecken"].append(
                    {"blocker": praefix, "art": "heiler-fehlt-im-repo",
                     "heiler": fehlend})
                continue
            nicht_verdrahtet = [h for h in heiler if h not in vorhanden]
            if nicht_verdrahtet:
                bericht["luecken"].append(
                    {"blocker": praefix, "art": "nicht-in-der-kette",
                     "heiler": nicht_verdrahtet})
                continue
            bericht["heilbar"].append({"blocker": praefix, "heiler": heiler})
        elif klasse == bk.MENSCHLICH:
            bericht["menschlich"].append(
                {"blocker": praefix, "grund": treffer.get("grund", "")})
        elif klasse == bk.UNHEILBAR:
            if not str(treffer.get("grund") or "").strip():
                bericht["luecken"].append(
                    {"blocker": praefix, "art": "loeschgrund-fehlt"})
                continue
            bericht["unheilbar"].append(
                {"blocker": praefix, "grund": treffer["grund"]})
        else:
            bericht["luecken"].append(
                {"blocker": praefix, "art": f"unbekannte-klasse:{klasse}"})

    # Ein Klassen-Eintrag, den die Triage gar nicht mehr erzeugen kann, ist
    # kein harmloser Rest: Er kann ein Löschrecht für einen Befund behaupten,
    # den niemand mehr prüft (Kodex des Selbsttest-Runners).
    for praefix in index:
        if not any(p.startswith(praefix) for p in praefixe):
            bericht["tote_eintraege"].append(
                {"blocker": praefix, "art": "blocker-verschwunden"})
    return bericht


def loeschdeckung_text(b: dict) -> str:
    zeilen = [
        "# 🪦 Lösch-Deckung (Triage-Blocker ↔ Heiler ↔ Löschrecht)",
        "",
        f"- Blocker-Klassen der Triage: **{len(b['blocker'])}**",
        f"- Heilbar (mit Heiler in der Kette): **{len(b['heilbar'])}** · "
        f"unheilbar (löschbar, begründet): **{len(b['unheilbar'])}** · "
        f"Menschensache: **{len(b['menschlich'])}** · "
        f"Lücken: **{len(b['luecken'])}**",
        "",
    ]
    for e in b["heilbar"]:
        zeilen.append(f"- ✅ `{e['blocker']}` → heilbar via "
                      + ", ".join(f"`{h}`" for h in e["heiler"]))
    for e in b["menschlich"]:
        zeilen.append(f"- 🧑 `{e['blocker']}` → Menschensache: {e['grund']}")
    for e in b["unheilbar"]:
        zeilen.append(f"- 🪦 `{e['blocker']}` → löschbar: {e['grund']}")
    for e in b["luecken"]:
        if e["art"] == "nicht-in-der-kette":
            zeilen.append(
                f"- 🛑 `{e['blocker']}` → als heilbar deklariert, aber "
                f"{', '.join(e['heiler'])} läuft nicht in "
                "reserve_finisher.HEALER_CHAIN. Der Entwurf bleibt damit "
                "ewig blockiert – genau die Falle aus #594.")
        elif e["art"] == "heilbar-ohne-heiler":
            zeilen.append(f"- 🛑 `{e['blocker']}` → „heilbar\" ohne genannten "
                          "Heiler ist eine Behauptung.")
        elif e["art"] == "heiler-fehlt-im-repo":
            zeilen.append(f"- 🛑 `{e['blocker']}` → Heiler "
                          f"{', '.join(e['heiler'])} existiert nicht in "
                          "scripts/.")
        elif e["art"] == "loeschgrund-fehlt":
            zeilen.append(f"- 🛑 `{e['blocker']}` → unheilbar ohne "
                          "Begründung: Wer Text vernichtet, muss sagen warum.")
        else:
            zeilen.append(f"- 🛑 `{e['blocker']}` → {e['art']}: kein Eintrag "
                          "in reserve_blocker_klassen.KLASSEN – niemand hat "
                          "entschieden, wem dieser Befund gehört.")
    for e in b["tote_eintraege"]:
        zeilen.append(f"- 🛑 `{e['blocker']}` → {e['art']}: die Klasse "
                      "behauptet ein Löschrecht für einen Befund, den die "
                      "Triage nicht mehr erzeugt.")
    if not b["luecken"] and not b["tote_eintraege"]:
        zeilen += ["", "🎉 Jeder Triage-Blocker ist klassifiziert: heilbar "
                       "(mit verdrahtetem Heiler), Menschensache oder "
                       "begründet löschbar. Kein Entwurf kann mehr an einem "
                       "Mangel sterben, den kein Werkzeug anfasst."]
    zeilen += ["", "_Wahrheit: `draft_triage.classify()` (Blocker, gelesen), "
                   "`reserve_blocker_klassen.KLASSEN` (Klasse + Heiler) und "
                   "`reserve_finisher.HEALER_CHAIN` (Verdrahtung)._", ""]
    return "\n".join(zeilen)


def bericht_text(b: dict) -> str:
    zeilen = [
        "# 🧩 Reserve-Heiler-Deckung (Regel ↔ Heiler)",
        "",
        f"- Ablehnende Publish-Gate-Regeln: **{len(b['regeln'])}**",
        f"- Gedeckt: **{len(b['gedeckt'])}** · Ausnahmen mit Begründung: "
        f"**{len(b['ausnahmen'])}** · Lücken: **{len(b['luecken'])}**",
        "",
    ]
    for e in b["gedeckt"]:
        zeilen.append(f"- ✅ `{e['regel']}` → "
                      + ", ".join(f"`{h}`" for h in e["heiler"]))
    for e in b["ausnahmen"]:
        zeilen.append(f"- 🟠 `{e['regel']}` → Ausnahme: {e['grund']}")
    for e in b["luecken"]:
        if e["art"] == "nicht-in-der-kette":
            zeilen.append(f"- 🛑 `{e['regel']}` → Heiler "
                          f"{', '.join(e['heiler'])} fehlt in "
                          "reserve_finisher.HEALER_CHAIN – der Zielbestand "
                          "ist damit strukturell unerreichbar.")
        elif e["art"] == "heiler-fehlt-im-repo":
            zeilen.append(f"- 🛑 `{e['regel']}` → Heiler "
                          f"{', '.join(e['heiler'])} existiert nicht in "
                          "scripts/ – ein Tippfehler deckt nichts.")
        elif e["art"] == "ausnahme-ohne-begruendung":
            zeilen.append(f"- 🛑 `{e['regel']}` → Ausnahme ohne Begründung.")
        else:
            zeilen.append(f"- 🛑 `{e['regel']}` → keine Deckung: weder Heiler "
                          "noch begründete Ausnahme (fail-closed).")
    for e in b["tote_ausnahmen"]:
        zeilen.append(f"- 🛑 `{e['regel']}` → {e['art']}: der Eintrag deckt "
                      "nichts mehr und altert sonst still.")
    if not b["luecken"] and not b["tote_ausnahmen"]:
        zeilen += ["", "🎉 Jede ablehnende Regel des harten Publish-Gates hat "
                       "einen Heiler in der Reserve-Veredelung (oder eine "
                       "begründete Ausnahme) – der Zielbestand ist damit "
                       "strukturell erreichbar, keine Nacht läuft mehr "
                       "sehenden Auges in eine 5/6-Knappheit."]
    zeilen += ["", "_Wahrheit: `publish_gate.py` (Regeln, gelesen) und "
                   "`reserve_finisher.HEALER_CHAIN` (Heiler). Heilung: "
                   "Eintrag in REGEL_HEILER ergänzen und den Heiler in die "
                   "Kette aufnehmen._", ""]
    return "\n".join(zeilen)


def run_selftest() -> int:
    fehler: list[str] = []
    gate = ("def check_length_failures():\n    pass\n"
            "def affiliate_intent_failures(candidates=None):\n    pass\n"
            "def readability_failures(candidates):\n    pass\n")

    # 1) Der reale Befund #349: Intent-Regel im Gate, Heiler NICHT in der Kette.
    kette_ohne_intent = [("check_length.py", ["--fix"]),
                         ("profi_polish.py", ["--include-drafts"])]
    b = deckung(gate, kette_ohne_intent,
                regeln={"check_length_failures": ("check_length.py",),
                        "affiliate_intent_failures":
                            ("affiliate_intent_guard.py",),
                        "readability_failures": ("profi_polish.py",)},
                ausnahmen={}, scripts_dir=SCRIPTS)
    luecken = {(e["regel"], e["art"]) for e in b["luecken"]}
    if ("affiliate_intent_failures", "nicht-in-der-kette") not in luecken:
        fehler.append(f"fehlender Intent-Heiler nicht erkannt: {b['luecken']}")
    if ("check_length_failures", "nicht-in-der-kette") in luecken:
        fehler.append("verdrahteter Heiler fälschlich als Lücke gemeldet")

    # 2) Genau derselbe Fall MIT Heiler in der Kette -> grün.
    b2 = deckung(gate, kette_ohne_intent + [("affiliate_intent_guard.py",
                                             ["--fix", "--heal"], "file")],
                 regeln={"check_length_failures": ("check_length.py",),
                         "affiliate_intent_failures":
                             ("affiliate_intent_guard.py",),
                         "readability_failures": ("profi_polish.py",)},
                 ausnahmen={}, scripts_dir=SCRIPTS)
    if b2["luecken"] or b2["tote_ausnahmen"]:
        fehler.append(f"gedeckte Kette wird als Lücke gemeldet: {b2['luecken']}")

    # 3) Ein NEUES Gate ohne Tabelleintrag fällt auf (Klasse, nicht Symptom).
    b3 = deckung(gate + "def brand_new_failures(candidates):\n    pass\n",
                 kette_ohne_intent,
                 regeln={"check_length_failures": ("check_length.py",)},
                 ausnahmen={}, scripts_dir=SCRIPTS)
    if ("brand_new_failures", "keine-deckung") not in {
            (e["regel"], e["art"]) for e in b3["luecken"]}:
        fehler.append("neue Gate-Regel ohne Deckung nicht erkannt")

    # 4) Ausnahme mit Begründung ist gültig – ohne Begründung nicht.
    b4 = deckung(gate, kette_ohne_intent,
                 regeln={"check_length_failures": ("check_length.py",)},
                 ausnahmen={"affiliate_intent_failures":
                            "nicht heilbar, gehört der Redaktion",
                            "readability_failures": "   "},
                 scripts_dir=SCRIPTS)
    arten = {(e["regel"], e["art"]) for e in b4["luecken"]}
    if b4["ausnahmen"] != [{"regel": "affiliate_intent_failures",
                            "grund": "nicht heilbar, gehört der Redaktion"}]:
        fehler.append(f"begründete Ausnahme nicht akzeptiert: {b4['ausnahmen']}")
    if ("readability_failures", "ausnahme-ohne-begruendung") not in arten:
        fehler.append("Ausnahme ohne Begründung nicht erkannt")

    # 5) Verschwundene Regel: Deckung/Ausnahme, die nichts mehr deckt.
    b5 = deckung("def check_length_failures():\n    pass\n", kette_ohne_intent,
                 regeln={"check_length_failures": ("check_length.py",),
                         "affiliate_intent_failures":
                             ("affiliate_intent_guard.py",)},
                 ausnahmen={"keyword_failures": "am Gate selbst geheilt"},
                 scripts_dir=SCRIPTS)
    tote = {e["regel"] for e in b5["tote_ausnahmen"]}
    if "affiliate_intent_failures" not in tote or "keyword_failures" not in tote:
        fehler.append(f"verschwundene Regeln nicht erkannt: {b5['tote_ausnahmen']}")

    # 6) Tippfehler im Heiler-Namen deckt nichts.
    b6 = deckung(gate, kette_ohne_intent,
                 regeln={"check_length_failures": ("check_lenght.py",)},
                 ausnahmen={}, scripts_dir=SCRIPTS)
    if not any(e["art"] == "heiler-fehlt-im-repo" for e in b6["luecken"]):
        fehler.append("Heiler-Tippfehler nicht erkannt")

    # --- Lösch-Deckung (WF-B594): der Weg nach UNTEN ----------------------
    sys.path.insert(0, str(SCRIPTS))
    import reserve_blocker_klassen as bk

    fix_klassen = (
        {"praefix": "laenge:", "klasse": bk.HEILBAR,
         "heiler": ("check_length.py",), "grund": "Verlängerer"},
        {"praefix": "interne links:", "klasse": bk.HEILBAR,
         "heiler": ("internal_linker.py",), "grund": "Linker"},
        {"praefix": "titel:", "klasse": bk.UNHEILBAR, "heiler": (),
         "grund": "Torso ohne redaktionelle Aussage"},
    )
    kette_ohne_linker = [("check_length.py", ["--fix"], "file")]

    # 7) DER REALE BEFUND #594: „interne links:" ist als heilbar deklariert,
    #    aber kein Werkzeug der Kette setzt je einen Link.
    l1 = loeschdeckung(["laenge:", "interne links:", "titel:"], fix_klassen,
                       kette_ohne_linker, SCRIPTS)
    if ("interne links:", "nicht-in-der-kette") not in {
            (e["blocker"], e["art"]) for e in l1["luecken"]}:
        fehler.append(f"#594-Lücke (Blocker ohne Heiler) nicht erkannt: "
                      f"{l1['luecken']}")

    # 8) Mit verdrahtetem Linker ist dieselbe Tabelle grün.
    l2 = loeschdeckung(["laenge:", "interne links:", "titel:"], fix_klassen,
                       kette_ohne_linker + [("internal_linker.py",
                                             ["--apply"], "file")], SCRIPTS)
    if l2["luecken"] or l2["tote_eintraege"]:
        fehler.append(f"verdrahteter Linker wird als Lücke gemeldet: {l2}")

    # 9) Ein NEUER Triage-Blocker ohne Klasse ist eine Lücke (niemand hat
    #    entschieden, wem er gehört) – und bleibt fail-closed unlöschbar.
    l3 = loeschdeckung(["laenge:", "brandneu:"], fix_klassen,
                       kette_ohne_linker, SCRIPTS)
    if ("brandneu:", "unklassifiziert") not in {
            (e["blocker"], e["art"]) for e in l3["luecken"]}:
        fehler.append("neuer Triage-Blocker ohne Klasse nicht erkannt")
    if bk.loeschbar(["brandneu: irgendwas"])[0]:
        fehler.append("unklassifizierter Blocker darf nie löschbar sein")

    # 10) Unheilbar ohne Begründung: Wer Text vernichtet, muss sagen warum.
    l4 = loeschdeckung(["titel:"],
                       ({"praefix": "titel:", "klasse": bk.UNHEILBAR,
                         "heiler": (), "grund": "  "},),
                       kette_ohne_linker, SCRIPTS)
    if ("titel:", "loeschgrund-fehlt") not in {
            (e["blocker"], e["art"]) for e in l4["luecken"]}:
        fehler.append("Löschrecht ohne Begründung nicht erkannt")

    # 11) Eine Klasse für einen Blocker, den die Triage nicht mehr erzeugt,
    #     behauptet ein Löschrecht ins Leere.
    l5 = loeschdeckung(["laenge:"], fix_klassen, kette_ohne_linker, SCRIPTS)
    if "titel:" not in {e["blocker"] for e in l5["tote_eintraege"]}:
        fehler.append(f"toter Klassen-Eintrag nicht erkannt: "
                      f"{l5['tote_eintraege']}")

    # 12) Und der scharfe Fall: das ECHTE Repo muss grün sein.
    try:
        echt = loeschdeckung()
        if echt["luecken"] or echt["tote_eintraege"]:
            fehler.append(f"Lösch-Deckung im echten Repo lückenhaft: "
                          f"{echt['luecken']} {echt['tote_eintraege']}")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Lösch-Deckung nicht auswertbar: {exc}")

    if fehler:
        print("🛑 RESERVE-HEILER-DECKUNG-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Selbsttest reserve_healer_coverage: fehlender Heiler (#349), "
          "neue Gate-Regel, begründete/lückenhafte Ausnahme, verschwundene "
          "Regel und Heiler-Tippfehler werden erkannt – und die Lösch-"
          "Deckung (#594): Blocker ohne Heiler, unklassifizierter Blocker, "
          "Löschrecht ohne Begründung, toter Eintrag.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deckungs-Wache: Publish-Gate-Regeln ↔ Reserve-Heiler")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    try:
        b = deckung()
        lb = loeschdeckung()
    except Exception as exc:  # noqa: BLE001 – fail-closed, aber erklärbar
        print(f"🛑 Deckungs-Wache nicht auswertbar: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"gate_deckung": b, "loesch_deckung": lb},
                         ensure_ascii=False, indent=1))
    else:
        print(bericht_text(b))
        print(loeschdeckung_text(lb))
    offen = (b["luecken"] or b["tote_ausnahmen"]
             or lb["luecken"] or lb["tote_eintraege"])
    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main())
