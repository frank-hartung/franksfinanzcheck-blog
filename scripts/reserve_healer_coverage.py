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

ERWEITERUNG 07.10.2026 (BOT-WATCHDOG-614): Derselbe Nachweis gilt jetzt
  auch für `textverstaendnis_failures`. Die Regel stand als „gedeckt" in der
  Tabelle, obwohl die genannten Heiler nur R5 (Absatz) und R8-URL kennen –
  die harten Politur-Regeln R7/R11–R16 hatten keinen Heiler. Beweis aus dem
  Reserve-Zertifikat vom 07.10.2026: „R14-MARKER-RUINE … manuell reparieren",
  „R15-PHRASEN-DOPPEL … manuell reparieren". Der neue `politur_heiler.py`
  heilt die Klasse und ist über `PROBEN_PFLICHT` an seinen
  `--wirkungsprobe`-Nachweis gebunden.

ERWEITERUNG 07.10.2026 (WACHE-609): Dritte Deckung `wirkungsdeckung()`
  – „Deckung heißt Wirkung". Der Auslöser ist die zweite Hälfte des Befunds:
  `readability_failures` galt als gedeckt, weil `profi_polish.py` in der Kette
  stand – und der Vorrat stand trotzdem bei 2/6, sieben Kandidaten allein an
  der Lesbarkeit geparkt (Flesch 53,1–59,9). Ein Name in der Kette beweist
  keine Wirkung: Ein Heiler, der eine Schwelle verspricht, muss sie BEWEGEN
  können – maschinell nachgewiesen (`--wirkungsprobe`), ohne Netz, ohne
  Kontingent. Fehlt der Nachweis, ist der Lauf fail-closed rot.

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
    # Lesbarkeit (Flesch ≥ 60 als Publish-Kriterium, #585). REPARATUR
    # 07.10.2026 (WACHE-609): Bis hierher stand nur `profi_polish.py` in
    # der Tabelle – ein Name, keine Wirkung: Der Vorrat lag bei 2/6, sieben
    # Kandidaten allein an der Lesbarkeit geparkt (53,1–59,9), und kein
    # Werkzeug der Kette konnte sie über die Schwelle heben. Der
    # Lesbarkeits-Heiler ist genau dafür gebaut (Stufe A deterministisch,
    # Stufe B KI-gezielt auf die Silben je Wort, Tor T1–T4 fail-closed) und
    # beweist seine Wirkung als Maschinenvertrag (`--wirkungsprobe`).
    # ERWEITERUNG 07.10.2026 (BOT-WATCHDOG-614): Der Satz-Heiler heilt die
    # Klasse satzweise (siehe reserve_finisher.HEALER_CHAIN). Der
    # Lesbarkeits-Heiler bleibt in der Kette - er ist die zweite Chance für
    # Texte, die satzweise nicht über die Schwelle kommen.
    "readability_failures": ("satz_heiler.py", "lesbarkeit_heiler.py",
                             "profi_polish.py"),
    # R2/R3/R5/R7/R8: Absatz-Splitter heilt R5, URL-Hygiene heilt R8-URL.
    # REPARATUR 07.10.2026: Die Zeile stand für den GANZEN Regel-Ordner
    # `textverstaendnis_failures` – obwohl die genannten Heiler zunächst nur
    # R5 und R8-URL kannten. Zwei Reparaturen desselben Tages schließen die
    # Klasse jetzt von zwei Seiten:
    #   * WF-D4E0 (#612, aus main): R11/R13/R14 (Politur-Ruinen, harte
    #     Publish-Regeln seit #482) hatten KEINEN Schreiber. Der reale Fall
    #     `2026-10-07-wie-smart-home-…` scheiterte einzig an der
    #     Marker-Ruine „SATZ: | Thread | …“; die Quarantäne nahm ihn als
    #     `reserve_blocked` aus dem Spiel, der Vorrat fiel unter das Ziel.
    #   * BOT-WATCHDOG #614: R7-Intro-Formel, R15-PHrasen-Doppel und
    #     R16-Prompt-Echo standen als „manuell reparieren“ im Zertifikat,
    #     obwohl der breite Politur-Heiler sie fail-closed heilt – und genau
    #     diese Rest-Hartfunde ließen das Tor T2 des Lesbarkeits-Heilers
    #     JEDE KI-Heilung verwerfen.
    "textverstaendnis_failures": ("politur_ruine_heiler.py",
                                  "politur_heiler.py",
                                  "r5_absatz_splitter.py",
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

# ---------------------------------------------------------------------------
#  WIRKUNGS-NACHWEISE (WACHE-609, 07.10.2026, Issue #609)
# ---------------------------------------------------------------------------
#  Eine Zahl, die ein Heiler verspricht, braucht einen Maschinenbeweis –
#  sonst ist „gedeckt“ eine Behauptung. Die Probe läuft OHNE Netz und ohne
#  API-Kontingent (Fixture → Stufe A) und Exit 0 heißt: die Schwelle wird
#  wirklich bewegt, und das Tor T1–T4 hält.
WIRKUNGS_PROBEN: dict[str, tuple[str, ...]] = {
    "lesbarkeit_heiler.py": ("--wirkungsprobe",),
    # WF-D4E0 (#612, aus main): die Politur-Ruinen-Familie verschwindet
    # nachweislich (Fixture je Klasse, Tor T1–T4, zweiter Lauf = Fixpunkt).
    "politur_ruine_heiler.py": ("--wirkungsprobe",),
    # ERWEITERUNG 07.10.2026 (BOT-WATCHDOG-614): Der Politur-Heiler heilt die
    # harten Regeln R7/R11–R16 und beweist das an einem Fixture (alle fünf
    # Defekte hinein, keiner heraus, Tor T1–T3 hält, idempotent).
    "politur_heiler.py": ("--wirkungsprobe",),
    # ERWEITERUNG 07.10.2026 (BOT-WATCHDOG-614): Der Satz-Heiler beweist seine
    # Wirkung an der ECHTEN Flesch-Formel (readability_check) - ein schwerer
    # Fixture-Text geht über die importierte Schwelle, das Ganztext-Tor T1–T4
    # hält, und die Probe läuft ohne Netz (KI injiziert).
    "satz_heiler.py": ("--wirkungsprobe",),
}

#  Regeln mit Zahlen-Versprechen: Mindestens einer ihrer Heiler MUSS eine
#  grüne Wirkungsprobe haben. Die Liste wächst mit jedem neuen Zahlen-Heiler,
#  nicht mit jedem Heiler (Alt-Werkzeuge ohne Schwelle bleiben unberührt).
#  `textverstaendnis_failures` ist der zweite Eintrag: Die Regel galt als
#  gedeckt, während im Zertifikat „manuell reparieren" stand (#614) – genau
#  die Bauart, gegen die diese Liste existiert (#609).
PROBEN_PFLICHT: tuple[str, ...] = ("readability_failures",
                                   "textverstaendnis_failures")

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
def wirkungsdeckung(proben: dict | None = None,
                    scripts_dir: Path | None = None,
                    timeout: int = 300) -> dict:
    """Führt die Wirkungsproben aus – Deckung muss Wirkung beweisen (#609).

    Rückgabe: {"nachgewiesen": [...], "luecken": [...]}. `proben` ist
    injizierbar, damit der Selbsttest rote/fehlende/abgestürzte Proben zeigen
    kann, ohne echte Werkzeuge zu beschädigen.
    """
    import subprocess

    tabelle = dict(WIRKUNGS_PROBEN if proben is None else proben)
    scripts_dir = Path(scripts_dir) if scripts_dir else SCRIPTS
    bericht: dict = {"nachgewiesen": [], "luecken": []}

    # a) Jede Regel mit Zahlen-Versprechen braucht mindestens eine Probe.
    for regel in PROBEN_PFLICHT:
        heiler = REGEL_HEILER.get(regel, ())
        if not [h for h in heiler if h in tabelle]:
            bericht["luecken"].append(
                {"heiler": ", ".join(heiler) or "–",
                 "art": "regel-ohne-wirkungsprobe", "regel": regel})

    # b) Jede Probe muss laufen UND bestehen (Exit 0).
    for heiler, args in tabelle.items():
        skript = scripts_dir / heiler
        if not skript.is_file():
            bericht["luecken"].append({"heiler": heiler, "art": "skript-fehlt"})
            continue
        try:
            lauf = subprocess.run([sys.executable or "python3", str(skript), *args],
                                  cwd=str(ROOT), capture_output=True, text=True,
                                  timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:  # noqa: BLE001
            bericht["luecken"].append(
                {"heiler": heiler, "art": f"probe-{exc.__class__.__name__}"})
            continue
        if lauf.returncode != 0:
            ausgabe = (lauf.stdout or lauf.stderr or "").strip().splitlines()
            bericht["luecken"].append(
                {"heiler": heiler, "art": "probe-rot",
                 "befund": ausgabe[-1][:200] if ausgabe else ""})
            continue
        zeilen = (lauf.stdout or "").strip().splitlines()
        bericht["nachgewiesen"].append(
            {"heiler": heiler,
             "befund": zeilen[-1][:200] if zeilen else "Exit 0"})
    return bericht


def volldeckung(chain: list | None = None) -> dict:
    """Beide Deckungen + Wirkung in EINEM Bericht (Wahrheit der Wache, #609).

    Die Wirkungs-Lücken wandern zusätzlich in `luecken`, damit JEDER Aufrufer,
    der bisher nur `luecken`/`tote_ausnahmen` prüft (reserve_finisher und der
    harte End-Gate-Pfad), ohne Änderung fail-closed bleibt.
    """
    b = deckung(chain=chain)
    try:
        w = wirkungsdeckung()
    except Exception as exc:  # noqa: BLE001 – nie ohne Urteil weiterlaufen
        w = {"nachgewiesen": [], "luecken": [
            {"heiler": "–", "art": "wirkung-nicht-auswertbar",
             "befund": str(exc)[:160]}]}
    b["wirkung"] = w
    for e in w["luecken"]:
        b["luecken"].append(
            {"regel": f"Wirkungsprobe `{e['heiler']}`", "art": e["art"],
             "heiler": [e["heiler"]], "befund": e.get("befund", "")})
    return b


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
    wirkung = b.get("wirkung")
    if wirkung is not None:
        zeilen += ["", "## Wirkungs-Nachweise (Deckung heißt Wirkung, #609)", ""]
        for e in wirkung["nachgewiesen"]:
            zeilen.append(f"- 🧪 `{e['heiler']}` → {e['befund']}")
        for e in wirkung["luecken"]:
            zeilen.append(f"- 🛑 `{e['heiler']}` → {e['art']}: "
                          f"{e.get('befund') or 'keine grüne Wirkungsprobe'}")
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


# ---------------------------------------------------------------------------
#  VORRATSSCHUTZ-BEWEIS (Reparatur 07.10.2026, BOT-WATCHDOG #614)
# ---------------------------------------------------------------------------
#  Am 07.10.2026 nahm ein einziger Lauf zehn Kandidaten die Pool-Fahne
#  (Zertifikat 2/6, Pool 12 -> 2) – Grund: `reserve_quarantine` zählte nur
#  LÄUFE mit gleichem Befund und fragte nie nach der KLASSE. Die Befunde
#  standen alle in `GATE_BEFUNDE` und waren dort als heilbar geführt.
#  Dieser Beweis friert die Gegenregel ein und läuft in jedem CI-Durchgang
#  (`--selftest`), nicht nur im Kopf des Autors.
VORFALL_614 = "37645894042"

VORFALL_614_BEFUNDE: tuple[str, ...] = (
    ("Lesbarkeits-Gate nicht bestanden: Flesch 58.0 (Mindestwert 60) – ein "
     "Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach "
     "unten (#585)"),
    ("Lesbarkeits-Gate nicht bestanden: Flesch 59.9 (Mindestwert 60) – ein "
     "Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach "
     "unten (#585)"),
    ("Lesbarkeits-Gate nicht bestanden: Flesch 55.8 (Mindestwert 60) – ein "
     "Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach "
     "unten (#585)"),
    ("Lesbarkeits-Gate nicht bestanden: Lesbarkeits-Score 70/100 (Mindestwert "
     "75): Flesch 52 (Ziel ≥ 60); 2 Absätze > 4 Sätze; 9 "
     "Passiv-Formulierungen; Flesch 52.3 (Mindestwert 60)"),
    "Zeichenlänge (check_length.py) nicht bestanden",
    ("quality-score 0.839 < 0.85 (schwach: structure 0.70, readability 0.75, "
     "typography 0.84)"),
    ("Textverständnis-Gate nicht bestanden: R14-MARKER-RUINE: Politur-Ruine "
     "„SATZ:“ – Überrest eines automatisierten Politur-Laufs, manuell "
     "reparieren"),
)


def vorratsschutz() -> dict:
    """Beweist, dass der Vorrat nicht mehr für heilbare Befunde blutet (#614).

    Vier Zusagen, ohne Netz, in einem temporären Bestand:
      1. Heilbarer Befund -> Fahne bleibt, Schonung begründet (Klasse+Heiler)
         – geprüft mit den ORIGINAL-Befunden des Vorfalls.
      2. Unheilbarer Befund -> Fahne fällt (die Zusage #295 bleibt scharf).
      3. Unbekannter Befund -> Fahne bleibt (fail-closed).
      4. Rückholung: ausgemustert + heilbare Klasse + Wirkungsnachweis in der
         Kette -> Fahne zurück; ohne Wirkungsnachweis -> bleibt ausgemustert.
    """
    import tempfile
    import reserve_quarantine as rq
    import reserve_custody as cu
    import reserve_blocker_klassen as bk
    import reserve_finisher as fin

    fehler: list[str] = []
    geprueft = {"vorfall_befunde": 0, "geschont": 0, "ausgemustert": 0,
                "fail_closed": 0, "rueckgeholt": 0, "rueckholung_verweigert": 0}

    def _post(posts, slug, fm):
        ordner = posts / slug
        ordner.mkdir(parents=True, exist_ok=True)
        ziel = ordner / "index.md"
        ziel.write_text(f"---\n{fm}\n---\n\nText.\n", encoding="utf-8")
        return ziel

    with tempfile.TemporaryDirectory() as tmp:
        root = __import__("pathlib").Path(tmp)
        posts = root / "posts"
        lesbarkeit = VORFALL_614_BEFUNDE[0]

        # 1) Die Original-Befunde des Vorfalls dürfen nie eine Fahne kosten.
        for i, grund in enumerate(VORFALL_614_BEFUNDE):
            _post(posts, f"vorfall-{i}", 'title: "Vorfall"\ndate: 2026-10-07\n'
                                         'draft: true\nreserve: true')
            zustand = root / f"zustand-{i}.json"
            blockiert: list[dict] = []
            geschont_je_fall: list[dict] = []
            for lauf in (f"run:{VORFALL_614}A", f"run:{VORFALL_614}B"):
                blockiert += rq.record([{"slug": f"vorfall-{i}", "ready": False,
                                         "reason": grund}], zustand, posts,
                                       apply=True, run_key=lauf,
                                       geschont_out=geschont_je_fall)
            text = (posts / f"vorfall-{i}" / "index.md").read_text("utf-8")
            if blockiert or "reserve_blocked" in text:
                fehler.append(f"Vorfall-Befund kostete die Fahne: {grund[:60]}")
            if "reserve: true" not in text:
                fehler.append(f"Vorfall-Befund vertrieb den Kandidaten: "
                              f"{grund[:60]}")
            if not geschont_je_fall:
                fehler.append(f"Schonung nicht begründet gemeldet: {grund[:60]}")
            if bk.gate_befund_klasse(grund)["klasse"] != bk.HEILBAR:
                fehler.append(f"Vorfall-Befund gilt nicht als heilbar: "
                              f"{grund[:60]}")
            geprueft["vorfall_befunde"] += 1
            geprueft["geschont"] += 1

        # 2) Unheilbar mustert weiterhin aus (Zusage #295 bleibt scharf).
        _post(posts, "torso", 'title: "Torso"\ndate: 2026-10-07\ndraft: true\n'
                              'reserve: true')
        dublette = ("Dublette: identischer Inhalt zu "
                    "2026-09-01-energie-update-tarife (0.97)")
        for lauf in ("run:t1", "run:t2"):
            blockiert = rq.record([{"slug": "torso", "ready": False,
                                    "reason": dublette}], root / "t.json",
                                  posts, apply=True, run_key=lauf)
        text = (posts / "torso" / "index.md").read_text("utf-8")
        if not blockiert or "reserve_blocked" not in text:
            fehler.append("unheilbarer Befund mustert nicht mehr aus")
        if "reserve: true" in text:
            fehler.append("unheilbarer Befund behielt die Fahne")
        geprueft["ausgemustert"] += len(blockiert)

        # 3) Unbekannt bleibt fail-closed im Pool (Fahne ist kein Zufall).
        _post(posts, "unbekannt", 'title: "Unbekannt"\ndate: 2026-10-07\n'
                                  'draft: true\nreserve: true')
        for lauf in ("run:u1", "run:u2"):
            rq.record([{"slug": "unbekannt", "ready": False,
                        "reason": "brandneuer Befund ohne Klasse"}],
                      root / "u.json", posts, apply=True, run_key=lauf)
        text = (posts / "unbekannt" / "index.md").read_text("utf-8")
        if "reserve_blocked" in text or "reserve: true" not in text:
            fehler.append("unbekannter Befund wurde ausgemustert (nicht "
                          "fail-closed)")
        geprueft["fail_closed"] += 1

        # 4) Rückholung mit Beweis – und die Verweigerung ohne Beweis.
        ausgemustert = _post(
            posts, "rueckhol-kandidat",
            'title: "Rückholkandidat"\ndate: 2026-10-07\ndraft: true\n'
            f'reserve_blocked: "{lesbarkeit}"\n'
            'reserve_blocked_at: 2026-10-07T16:07:55Z')
        lage = cu.bestandsaufnahme(posts, pfad=root / "custody.json")
        if not [e for e in lage["blockiert"]]:
            fehler.append("ausgemusterter Kandidat nicht als solcher gelesen")
        zurueck = cu.rueckholen(lage, posts, jetzt=__import__("datetime").date(2026, 10, 7))
        text = ausgemustert.read_text(encoding="utf-8")
        if len(zurueck) != 1 or "reserve: true" not in text:
            fehler.append(f"Rückholung griff nicht: {zurueck}")
        if "reserve_blocked" in text or "reserve_reaktiviert" not in text:
            fehler.append("Rückholung ohne saubere Belegzeile")
        else:
            geprueft["rueckgeholt"] += 1

        # Ohne Wirkungsnachweis in der Kette bleibt der Kandidat ausgemustert:
        # Hier wird die Kette kurzzeitig beschnitten (Heiler raus) – der
        # Beweis muss dann NEIN sagen, obwohl die Klasse heilbar heißt.
        opfer = _post(posts, "ohne-nachweis",
                      'title: "Ohne Nachweis"\ndate: 2026-10-07\ndraft: true\n'
                      f'reserve_blocked: "{lesbarkeit}"')
        echte_kette = fin.HEALER_CHAIN
        try:
            fin.HEALER_CHAIN = tuple(
                e for e in echte_kette
                if e[0] not in ("lesbarkeit_heiler.py", "satz_heiler.py"))
            lage2 = cu.bestandsaufnahme(posts, pfad=root / "custody2.json")
            cu.rueckholen(lage2, posts)
        finally:
            fin.HEALER_CHAIN = echte_kette
        if "reserve: true" in opfer.read_text(encoding="utf-8"):
            fehler.append("Rückholung ohne Wirkungsnachweis in der Kette")
        else:
            geprueft["rueckholung_verweigert"] += 1

    return {"ok": not fehler, "fehler": fehler, "geprueft": geprueft,
            "vorfall": VORFALL_614}


def vorratsschutz_text(b: dict) -> str:
    marke = "✅" if b["ok"] else "🛑"
    g = b["geprueft"]
    zeilen = [f"{marke} Vorratsschutz (#614, Lauf {b['vorfall']}): "
              f"{g['vorfall_befunde']} Original-Befunde ohne Fahnenverlust · "
              f"{g['ausgemustert']} unheilbare Ausmusterung(en) · "
              f"{g['fail_closed']} fail-closed gehalten · "
              f"{g['rueckgeholt']} Rückholung mit Beweis · "
              f"{g['rueckholung_verweigert']} Verweigerung ohne Beweis"]
    zeilen += [f"   - {f}" for f in b["fehler"]]
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

    # --- Wirkungs-Deckung (WACHE-609): Deckung ohne Wirkung ist Papier --
    # 13) Eine Regel mit Zahlen-Versprechen, aber ohne Wirkungsprobe.
    wd_leer = wirkungsdeckung(proben={}, scripts_dir=SCRIPTS)
    if not [e for e in wd_leer["luecken"]
            if e["art"] == "regel-ohne-wirkungsprobe"]:
        fehler.append("Regel mit Zahlen-Versprechen ohne Wirkungsprobe bleibt "
                      "unentdeckt (#609)")
    # 14) Eine rote Probe (Werkzeug verweigert) und ein fehlendes Skript.
    wd_rot = wirkungsdeckung(proben={"lesbarkeit_heiler.py": ("--gibtsnicht",)},
                             scripts_dir=SCRIPTS)
    if not [e for e in wd_rot["luecken"] if e["art"] == "probe-rot"]:
        fehler.append("rote Wirkungsprobe bleibt unentdeckt (#609)")
    wd_fehlt = wirkungsdeckung(proben={"gibtsnicht.py": ("--wirkungsprobe",)},
                               scripts_dir=SCRIPTS)
    if not [e for e in wd_fehlt["luecken"] if e["art"] == "skript-fehlt"]:
        fehler.append("fehlendes Probe-Skript bleibt unentdeckt (#609)")
    # 15) Und der scharfe Fall: die echten Proben müssen grün sein.
    try:
        wd = wirkungsdeckung()
        if wd["luecken"] or not wd["nachgewiesen"]:
            fehler.append(f"Wirkungsproben im echten Repo nicht grün: "
                          f"{wd['luecken'] or 'keine Probe nachgewiesen'}")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Wirkungsproben nicht auswertbar: {exc}")

    # --- Vorratsschutz (#614): heilbare Befunde dürfen keine Fahne kosten --
    # 16) Der scharfe Fall: Die Original-Befunde des Vorfalls, unheilbare
    #     Torsi, unbekannte Befunde und die Rückholung – alles im Echtzustand.
    try:
        vs = vorratsschutz()
        if not vs["ok"]:
            fehler.append(f"Vorratsschutz nicht bewiesen: {vs['fehler']}")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Vorratsschutz nicht auswertbar: {exc}")

    if fehler:
        print("🛑 RESERVE-HEILER-DECKUNG-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Selbsttest reserve_healer_coverage: fehlender Heiler (#349), "
          "neue Gate-Regel, begründete/lückenhafte Ausnahme, verschwundene "
          "Regel und Heiler-Tippfehler werden erkannt – und die Lösch-"
          "Deckung (#594): Blocker ohne Heiler, unklassifizierter Blocker, "
          "Löschrecht ohne Begründung, toter Eintrag – und die Wirkungs-"
          "Deckung (#609): Regel ohne Probe, rote Probe, fehlendes Skript – "
          "und der Vorratsschutz (#614): kein Fahnenverlust für heilbare "
          "Befunde, Ausmusterung nur für Unheilbares, Rückholung nur mit "
          "Wirkungsnachweis.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deckungs-Wache: Publish-Gate-Regeln ↔ Reserve-Heiler")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--vorratsschutz", action="store_true",
                    help="Maschinenbeweis: heilbare Befunde kosten keine Fahne")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.vorratsschutz:
        b = vorratsschutz()
        print(json.dumps(b, ensure_ascii=False) if args.json
              else vorratsschutz_text(b))
        return 0 if b["ok"] else 2
    try:
        b = volldeckung()
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
        print(vorratsschutz_text(vorratsschutz()))
    offen = (b["luecken"] or b["tote_ausnahmen"]
             or lb["luecken"] or lb["tote_eintraege"])
    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main())
