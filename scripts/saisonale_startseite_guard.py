#!/usr/bin/env python3
"""Verbindliches, schreibfreies Gate für die saisonale Startseite.

Die Startseite zeigt seit dem 20.09.2026 die Jahreszeit: ein Saison-Badge
und ein Saison-Hinweis im Hero sowie der Block „Saison-Fokus“ mit den
relevantesten LIVE-Artikeln der laufenden Saison. Quelle ist
`data/saisons.yaml` (kuratiert), gerendert von
`layouts/_partials/home_season.html` über
`layouts/_partials/_funcs/saison-kontext.html` bzw.
`_funcs/saison-aufloesung.html`, gestylt von
`assets/css/extended/zz-saisonale-startseite.css`.

Dieses Gate ist die Wache dahinter und prüft – wie
`scripts/themenwelten_guard.py` – BEIDE Ebenen, Quelle UND fertigen Build:

  python3 scripts/saisonale_startseite_guard.py --source-only
  python3 scripts/saisonale_startseite_guard.py --public public
  python3 scripts/saisonale_startseite_guard.py --public tmp/x --base-path /blog/
  python3 scripts/saisonale_startseite_guard.py --datum 2026-12-24 --public public
  python3 scripts/saisonale_startseite_guard.py --selftest
  python3 scripts/saisonale_startseite_guard.py --json

Prüfungen Quelle (S1–S8):
  S1 Schema/Pflichtfelder, Fenster im Format MM-DD, eindeutige IDs
  S2 Kalender: die vier Fenster decken ALLE Tage eines Schaltjahres
     (366) genau einmal ab – lückenlos UND überlappungsfrei. Ein Tag ohne
     Saison würde den Hugo-Build hart abbrechen (errorf), ein Tag mit zwei
     Saisons wäre Willkür.
  S3 Textqualität: Marken-Stimme (du, nie „Sie“), keine KI-Floskeln
     (Liste bewusst aus scripts/willkommenstext_guard.py dupliziert –
     gleiche Konvention wie dort), keine Markup-Reste, dazu die
     bestehenden Repo-Regeln R8 (verschachtelte Links) und R9
     (Klebewörter) aus textverstaendnis_guard.py
  S4 Farben: WCAG-2.x-Kontrast, gemessen nicht geraten –
       akzent        ≥ 4.5:1 auf #FFFFFF   (Kartenfläche hell)
       akzent_dunkel ≥ 4.5:1 auf #1E2023, #202E27, #25272A, #2E2E33
       hero_text     ≥ 4.5:1 auf #0E5A43   (vom Hero deklarierte
                     background-color – darauf löst effBg() in
                     e2e/design-metrics.mjs auf) UND ≥ 3:1 auf #1F6F5C
                     (hellster Verlauf-Stopp des Hero, konservative
                     Zusatzprüfung für große Typo)
       linie         ≥ 3:1 auf #FFFFFF     (Deko, kein Text)
       linie_dunkel  ≥ 3:1 auf #202E27
  S5 CSS-Deckung: `.ff-saison--<id>` existiert in der CSS-Datei und trägt
     EXAKT die Hex-Werte aus data/saisons.yaml (akzent, linie) – plus die
     Dark-Varianten für BEIDE Pfade (`:root[data-theme="dark"]` und
     `@media (prefers-color-scheme: dark)` auf `:root[data-theme="auto"]`,
     weil head.html den noscript-Fall nicht per JS umschreibt). Ohne diese
     Prüfung wären YAML und CSS zwei Wahrheiten.
  S6 Ratgeber-Ziele: jede `saison_pillars`-ID hat ein live veröffentlichtes
     content/pillar/<id>/index.md (draft: true = Fund)
  S7 Auswahl-Spiegel: dieselbe Logik wie das Template (Relevanz über
     `keywords`, Sortierung Relevanz absteigend → Datum absteigend, dann
     Fallback auf Saison-Pillars, dann auf die neuesten Artikel) für ALLE
     vier Saisons gegen den echten Content-Bestand. Meldet Quelle und
     Trefferzahl; `min_artikel` muss aus dem Bestand erreichbar sein.
  S8 LCP-Schutz: die Mobile-Reihenfolge `main.main > section.ff-saison
     { order: N }` existiert, und N hält die Artikel-Karten mit dem
     LCP-Cover (order: 1) vorne, liegt hinter der Pagination (order: 4)
     und nicht hinter den Clustern (order: 5).

Prüfungen Build (B1–B7) gegen public/index.html:
  B1 genau EIN H1 (Bestands-Test e2e/home.spec.mjs) und genau EIN
     section.ff-saison-Baum
  B2 Badge, Hinweis und Block tragen dieselbe Saison (`data-ff-saison`)
     wie der Stichtag erwartet; Texte sind bytegleich zur Quelle
  B3 Karten: Anzahl = min_artikel, REIHENFOLGE = Spiegel aus S7, jeder
     Link löst auf eine existente Datei unter public/ auf (kein toter
     Link), Titel nicht leer
  B4 Messung: jeder Saison-Link trägt cta_click mit slug, placement
     „start-saison“ und der Saison-Property – sonst ist der
     Revenue-Trichter (scripts/revenue_funnel.py) für diese Platzierung blind
  B5 das gebaute CSS-Bundle enthält die Saison-Klassen (Datei wirklich
     eingebunden, nicht nur im Repo)
  B6 Datenpfad: kein Layout der saisonalen Startseite fasst
     hugo.Data/site.Data an (dokumentierter Build-Killer vom 19.09.2026,
     data/ enthält *.jsonl-Protokolle)
  B7 DOM-Budget: Knotenzahl der Startseite unter dem cwv_guard-Softlimit

Keine Reparatur-Heuristik: Ein Defekt stoppt den Deploy (Exit 1), statt
Texte umzuschreiben oder eine Saison still zu unterschlagen. Exit 3 =
Quelle fehlt/kaputt (Build-Killer-Klasse), Exit 2 = Selbsttest bricht.
Nur Python-Standardbibliothek + PyYAML (im Repo ohnehin Standard,
siehe .github/workflows/deploy.yml) + textverstaendnis_guard.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from textverstaendnis_guard import check_klebewoerter, check_nested_links  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAISONS_YAML = ROOT / "data" / "saisons.yaml"
CSS_DATEI = ROOT / "assets" / "css" / "extended" / "zz-saisonale-startseite.css"
LAYOUTS = (
    ROOT / "layouts" / "_partials" / "home_season.html",
    ROOT / "layouts" / "_partials" / "saisons_data.html",
    ROOT / "layouts" / "_partials" / "_funcs" / "saison-kontext.html",
    ROOT / "layouts" / "_partials" / "_funcs" / "saison-aufloesung.html",
)
THEMENWELTEN = ROOT / "data" / "themenwelten.json"

PFLICHTFELDER_TEXT = (
    "name", "emoji", "zeitraum", "badge", "headline", "hinweis", "tipp", "pillar_link",
)
PFLICHTFELDER_FARBEN = ("akzent", "akzent_dunkel", "hero_text", "linie", "linie_dunkel")
SAISON_IDS = ("herbst", "winter", "fruehling", "sommer")

# Flächen aus dem echten CSS-Bestand (DESIGN.md §1 + zzz-agency-polish.css §1/§2
# + zz-themenwelten.css): gemessen wird gegen das, was der Browser wirklich
# unter den Text legt, nicht gegen eine Wunschfarbe.
FLAECHE_HELL = "#FFFFFF"            # --ff-surface / Kartenfläche hell
FLAECHEN_DUNKEL = ("#1E2023", "#202E27", "#25272A", "#2E2E33")
HERO_FLAECHENFARBE = "#0E5A43"           # background-color des Hero (agency-polish)
HERO_VERLAUF_HELL = "#1F6F5C"     # hellster Verlauf-Stopp des Hero
FLAECHE_LINIE_DUNKEL = "#202E27"

TEXT_MIN = 4.5
DEKO_MIN = 3.0
DOM_NODES_SOFT = 2500                # gleiches Softlimit wie scripts/cwv_guard.py

# Marken-Stimme: Der Blog spricht Leser konsequent mit „du“ an. Die Liste ist
# bewusst aus scripts/willkommenstext_guard.py dupliziert (dortige Konvention:
# duplizieren statt Cross-Import, damit jede Wache allein lauffähig bleibt).
FORMAL_ANREDE_RX = re.compile(r"\b(Sie|Ihnen|Ihrem|Ihrer|Ihren|Ihres|Ihr|Ihre)\b")
BANNED_PHRASES = (
    "in der heutigen schnelllebigen welt", "in der heutigen zeit",
    "es ist wichtig zu beachten", "zusammenfassend lässt sich sagen",
    "des weiteren", "wenn es darum geht", "heutzutage",
    "in der modernen welt", "tauchen wir ein", "lassen sie uns",
    "der schlüssel zum erfolg", "ein muss für jeden", "unverzichtbar für",
    "das a und o", "die welt der", "in einer welt, in der",
    "entdecke", "tauche ein", "willkommen in der welt",
)

FENSTER_RX = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")
HEX_RX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# --------------------------------------------------------------------------
#  WCAG-Kontrast (gleiche Formel wie e2e/design-metrics.mjs)
# --------------------------------------------------------------------------

def _kanal(hexc: str) -> tuple[int, int, int]:
    h = hexc.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminanz(hexc: str) -> float:
    def f(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = _kanal(hexc)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def kontrast(vorn: str, hinten: str) -> float:
    l1, l2 = _luminanz(vorn), _luminanz(hinten)
    heller, dunkler = max(l1, l2), min(l1, l2)
    return round((heller + 0.05) / (dunkler + 0.05), 2)


# --------------------------------------------------------------------------
#  S1/S2 – Schema und Kalender
# --------------------------------------------------------------------------

def fenster_schluessel(mm_dd: str) -> int:
    """MM-DD → Monat*100+Tag (also 09-01 → 901, 12-01 → 1201).

    Bewusst KEIN int("09"): Go wie Python behandeln eine führende Null
    als Oktal-Hinweis – Hugo bricht daran mit „strconv: invalid syntax“
    ab (am 20.09.2026 im Build beobachtet). Der Umweg über die Teilstrings
    mit abgeschnittener Null ist in _funcs/saison-aufloesung.html identisch.
    """
    monat, tag = mm_dd.split("-")
    return int(monat) * 100 + int(tag)


def saison_fuer(datum: datetime.date, saisons: list[dict]) -> dict | None:
    """Spiegel von layouts/_partials/_funcs/saison-aufloesung.html."""
    md = datum.month * 100 + datum.day
    for saison in saisons:
        ab = fenster_schluessel(str(saison.get("ab", "")))
        bis = fenster_schluessel(str(saison.get("bis", "")))
        if bis >= ab:
            treffer = ab <= md <= bis
        else:  # Fenster über den Jahreswechsel (Winter: 12-01 … 02-29)
            treffer = md >= ab or md <= bis
        if treffer:
            return saison
    return None


def kalender_abdeckung(saisons: list[dict]) -> list[str]:
    """Jeder Tag eines Schaltjahres (366) gehört zu GENAU EINER Saison."""
    fehler: list[str] = []
    jahr = 2028  # Schaltjahr → deckt den 29.02. mit ab
    tag = datetime.date(jahr, 1, 1)
    ende = datetime.date(jahr, 12, 31)
    while tag <= ende:
        treffer = [s for s in saisons
                   if saison_fuer(tag, [s]) is not None]
        if len(treffer) == 0:
            fehler.append(f"Kalender-Lücke: {tag.isoformat()} gehört zu keiner Saison")
        elif len(treffer) > 1:
            ids = ", ".join(str(s.get("id")) for s in treffer)
            fehler.append(f"Kalender-Überlappung: {tag.isoformat()} liegt in {ids}")
        tag += datetime.timedelta(days=1)
        if len(fehler) > 12:  # Bericht bleibt lesbar, die Ursache ist dieselbe
            fehler.append("… weitere Kalender-Fehler unterdrückt (gleiche Ursache)")
            break
    return fehler


def validate_schema(daten: object) -> tuple[list[dict], list[str]]:
    fehler: list[str] = []
    if not isinstance(daten, dict):
        return [], ["data/saisons.yaml muss ein Mapping mit `saisons`-Liste sein."]
    saisons = daten.get("saisons")
    if not isinstance(saisons, list) or not saisons:
        return [], ["data/saisons.yaml: `saisons` fehlt oder ist leer."]

    gesehen: set[str] = set()
    for eintrag in saisons:
        if not isinstance(eintrag, dict):
            fehler.append("Saisons: Eintrag ist kein Mapping.")
            continue
        sid = str(eintrag.get("id") or "")
        label = f"Saison {sid or '?'}"
        if not sid:
            fehler.append("Saisons: Eintrag ohne `id`.")
        elif sid in gesehen:
            fehler.append(f"{label}: doppelte ID.")
        elif sid not in SAISON_IDS:
            fehler.append(f"{label}: unbekannte ID (erwartet: {', '.join(SAISON_IDS)}). "
                          "Neue Saisons brauchen auch eine CSS-Klasse `.ff-saison--<id>`.")
        gesehen.add(sid)

        for feld in PFLICHTFELDER_TEXT:
            wert = eintrag.get(feld)
            if not isinstance(wert, str) or not wert.strip():
                fehler.append(f"{label}: `{feld}` muss ein nicht leerer Text sein.")
            elif re.search(r"[<>{}\r\n]", wert):
                fehler.append(f"{label}: `{feld}` darf kein Markup/Zeilenumschlag enthalten.")
            else:
                for _, regel, detail, _ in (check_klebewoerter(f"{label}/{feld}", wert)
                                            + check_nested_links(f"{label}/{feld}", wert)):
                    fehler.append(f"{label}: {regel}: {detail}")

        for feld in ("ab", "bis"):
            wert = str(eintrag.get(feld) or "")
            if not FENSTER_RX.match(wert):
                fehler.append(f"{label}: `{feld}` muss MM-DD sein (gefunden: {wert!r}).")

        badges = eintrag.get("badge")
        if isinstance(badges, str) and len(badges) > 52:
            fehler.append(f"{label}: `badge` ist {len(badges)} Zeichen lang – im Hero-Chip "
                          "brechen lange Badges um (Limit 52).")
        emoji = eintrag.get("emoji")
        if not isinstance(emoji, str) or not (1 <= len(emoji.strip()) <= 3):
            fehler.append(f"{label}: `emoji` muss genau ein Emoji sein (gefunden: {emoji!r}).")

        pillars = eintrag.get("saison_pillars")
        if not isinstance(pillars, list) or not pillars:
            fehler.append(f"{label}: `saison_pillars` muss eine nicht leere Liste sein.")
        elif not all(isinstance(p, str) and p.strip() for p in pillars):
            fehler.append(f"{label}: `saison_pillars` enthält einen leeren Eintrag.")

        keywords = eintrag.get("keywords")
        if not isinstance(keywords, list) or len(keywords) < 4:
            fehler.append(f"{label}: `keywords` braucht mindestens 4 Begriffe "
                          "(sonst ist die Relevanz-Auswahl Zufall).")
        elif any(not isinstance(k, str) or not k.strip() for k in keywords):
            fehler.append(f"{label}: `keywords` enthält einen leeren Begriff.")
        elif any(k != k.lower() for k in keywords if isinstance(k, str)):
            fehler.append(f"{label}: `keywords` müssen klein geschrieben sein "
                          "(das Template vergleicht per lowercase-Teilstring).")

        mindest = eintrag.get("min_artikel")
        if not isinstance(mindest, int) or mindest < 1 or mindest > 6:
            fehler.append(f"{label}: `min_artikel` muss eine ganze Zahl 1–6 sein "
                          f"(gefunden: {mindest!r}).")

        for feld in PFLICHTFELDER_FARBEN:
            wert = str(eintrag.get(feld) or "")
            if not HEX_RX.match(wert):
                fehler.append(f"{label}: `{feld}` muss ein Hex-Farbwert sein (gefunden: {wert!r}).")
    return [s for s in saisons if isinstance(s, dict)], fehler


def validate_stimme(saisons: list[dict]) -> list[str]:
    """Marken-Stimme: du-Form, keine KI-Floskeln (PRODUCT.md)."""
    fehler = []
    for saison in saisons:
        sid = saison.get("id")
        for feld in ("badge", "headline", "hinweis", "tipp", "pillar_link"):
            text = str(saison.get(feld) or "")
            if not text:
                continue
            if FORMAL_ANREDE_RX.search(text):
                fehler.append(f"Saison {sid}/{feld}: formelle Anrede „Sie“ – "
                              "die Marke spricht durchgehend mit „du“.")
            niedrig = text.lower()
            for floskel in BANNED_PHRASES:
                if floskel in niedrig:
                    fehler.append(f"Saison {sid}/{feld}: KI-Floskel „{floskel}“.")
    return fehler


def validate_farben(saisons: list[dict]) -> list[str]:
    fehler = []
    for saison in saisons:
        sid = saison.get("id")
        farben = {f: str(saison.get(f) or "") for f in PFLICHTFELDER_FARBEN}
        if not all(HEX_RX.match(w) for w in farben.values()):
            continue  # Schema-Fund wurde schon gemeldet

        akzent = kontrast(farben["akzent"], FLAECHE_HELL)
        if akzent < TEXT_MIN:
            fehler.append(f"Saison {sid}: `akzent` {farben['akzent']} auf Weiß = {akzent}:1 "
                          f"(Text braucht ≥ {TEXT_MIN}:1).")
        for flaeche in FLAECHEN_DUNKEL:
            dunkel = kontrast(farben["akzent_dunkel"], flaeche)
            if dunkel < TEXT_MIN:
                fehler.append(f"Saison {sid}: `akzent_dunkel` {farben['akzent_dunkel']} auf "
                              f"{flaeche} = {dunkel}:1 (Text braucht ≥ {TEXT_MIN}:1).")
        hero = kontrast(farben["hero_text"], HERO_FLAECHENFARBE)
        if hero < TEXT_MIN:
            fehler.append(f"Saison {sid}: `hero_text` {farben['hero_text']} auf Hero-Grün "
                          f"{HERO_FLAECHENFARBE} = {hero}:1 (≥ {TEXT_MIN}:1 nötig).")
        hero_verlauf = kontrast(farben["hero_text"], HERO_VERLAUF_HELL)
        if hero_verlauf < DEKO_MIN:
            fehler.append(f"Saison {sid}: `hero_text` {farben['hero_text']} auf dem hellsten "
                          f"Verlauf-Stopp {HERO_VERLAUF_HELL} = {hero_verlauf}:1 "
                          f"(≥ {DEKO_MIN}:1 als konservative Untergrenze).")
        linie = kontrast(farben["linie"], FLAECHE_HELL)
        if linie < DEKO_MIN:
            fehler.append(f"Saison {sid}: `linie` {farben['linie']} auf Weiß = {linie}:1 "
                          f"(Deko braucht ≥ {DEKO_MIN}:1).")
        linie_dunkel = kontrast(farben["linie_dunkel"], FLAECHE_LINIE_DUNKEL)
        if linie_dunkel < DEKO_MIN:
            fehler.append(f"Saison {sid}: `linie_dunkel` {farben['linie_dunkel']} auf "
                          f"{FLAECHE_LINIE_DUNKEL} = {linie_dunkel}:1 (Deko ≥ {DEKO_MIN}:1).")
    return fehler


def validate_css_parity(saisons: list[dict], css: str) -> list[str]:
    """YAML und CSS sind EINE Wahrheit: Werte müssen deckungsgleich sein."""
    fehler = []
    for saison in saisons:
        sid = str(saison.get("id"))
        block = re.search(r"\.ff-saison--" + re.escape(sid) + r"\s*\{([^}]*)\}", css)
        if not block:
            fehler.append(f"CSS: `.ff-saison--{sid}` fehlt in {CSS_DATEI.name} "
                          "(ohne Klasse bleibt die Saison farblos).")
            continue
        inhalt = block.group(1)
        for feld, variable in (("akzent", "--ff-saison-akzent"), ("linie", "--ff-saison-linie"),
                               ("hero_text", "--ff-saison-hero-text")):
            erwartet = str(saison.get(feld, "")).lower()
            m = re.search(re.escape(variable) + r"\s*:\s*(#[0-9a-fA-F]{3,8})", inhalt)
            if not m:
                fehler.append(f"CSS: `.ff-saison--{sid}` setzt {variable} nicht.")
            elif m.group(1).lower() != erwartet:
                fehler.append(f"CSS-Drift: `.ff-saison--{sid}` {variable} = {m.group(1)}, "
                              f"data/saisons.yaml `{feld}` = {erwartet} – eine Quelle muss "
                              "die andere gewinnen, bitte angleichen.")

        dunkel_js = re.search(r":root\[data-theme=[\"']?dark[\"']?\]\s*\.ff-saison--"
                              + re.escape(sid) + r"\s*\{([^}]*)\}", css)
        dunkel_auto = re.search(r":root\[data-theme=[\"']?auto[\"']?\]\s*\.ff-saison--"
                                + re.escape(sid) + r"\s*\{([^}]*)\}", css)
        if not dunkel_js:
            fehler.append(f"CSS: Dark-Variante `:root[data-theme=\"dark\"] .ff-saison--{sid}` "
                          "fehlt (PRODUCT.md Gate 2: jede Farbe braucht eine Dark-Variante).")
        if not dunkel_auto:
            fehler.append(f"CSS: Dark-Variante für den noscript-Pfad "
                          f"`:root[data-theme=\"auto\"] .ff-saison--{sid}` fehlt "
                          "(head.html setzt data-theme nur mit JS).")
        if dunkel_js and dunkel_auto and dunkel_js.group(1).split() != dunkel_auto.group(1).split():
            fehler.append(f"CSS: die beiden Dark-Pfade für `.ff-saison--{sid}` "
                          "unterscheiden sich – gleicher Modus, zwei Wahrheiten.")
        for pfad, block_text in (("data-theme=dark", dunkel_js), ("data-theme=auto", dunkel_auto)):
            if not block_text:
                continue
            erwartet = str(saison.get("akzent_dunkel", "")).lower()
            m = re.search(r"--ff-saison-akzent\s*:\s*(#[0-9a-fA-F]{3,8})", block_text.group(1))
            if m and m.group(1).lower() != erwartet:
                fehler.append(f"CSS-Drift: Dark-Akzent ({pfad}) für `.ff-saison--{sid}` = "
                              f"{m.group(1)}, YAML `akzent_dunkel` = {erwartet}.")
            erwartet_linie = str(saison.get("linie_dunkel", "")).lower()
            m = re.search(r"--ff-saison-linie\s*:\s*(#[0-9a-fA-F]{3,8})", block_text.group(1))
            if m and m.group(1).lower() != erwartet_linie:
                fehler.append(f"CSS-Drift: Dark-Linie ({pfad}) für `.ff-saison--{sid}` = "
                              f"{m.group(1)}, YAML `linie_dunkel` = {erwartet_linie}.")
    return fehler


def validate_pillars(saisons: list[dict], root: Path) -> list[str]:
    fehler = []
    for saison in saisons:
        sid = saison.get("id")
        for pid in saison.get("saison_pillars") or []:
            quelle = root / "content" / "pillar" / str(pid) / "index.md"
            if not quelle.is_file():
                fehler.append(f"Saison {sid}: Ratgeber-Quelle fehlt ({quelle.relative_to(root)}).")
                continue
            roh = quelle.read_text(encoding="utf-8")
            if re.search(r"^draft:\s*true\s*$", roh, re.M):
                fehler.append(f"Saison {sid}: Ratgeber /pillar/{pid}/ ist draft: true – "
                              "der Saison-Link würde ins Leere zeigen (Hugo baut ihn nicht).")
    return fehler


def validate_datenpfad(layouts=LAYOUTS) -> list[str]:
    """B6/S8-Vorläufer: kein hugo.Data/site.Data im Template-Code.

    data/ enthält *.jsonl-Protokolle; EIN site.Data-Zugriff lässt Hugo den
    ganzen Baum parsen und der Build stirbt (dokumentiert am 19.09.2026 in
    layouts/_partials/affiliate_ziele_data.html). Kommentare zählen nicht –
    sie sind genau der Ort, an dem die Begründung stehen muss.
    """
    fehler = []
    for pfad in layouts:
        if not pfad.is_file():
            fehler.append(f"Layout fehlt: {pfad.name}")
            continue
        text = pfad.read_text(encoding="utf-8")
        code = re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", " ", text, flags=re.S)
        for m in re.finditer(r"\b(hugo|site)\.Data\b", code):
            zeile = code[:m.start()].count("\n") + 1
            fehler.append(f"{pfad.name}:{zeile}: {m.group(0)} im Template-Code ist ein "
                          "Build-Killer (data/ enthält *.jsonl) – os.ReadFile + "
                          "transform.Unmarshal nutzen, siehe saisons_data.html.")
    return fehler


def validate_lcp_schutz(css: str) -> list[str]:
    """S8: Mobile-Reihenfolge hält das LCP-Cover vorne."""
    fehler = []
    m = re.search(r"main\.main\s*>\s*section\.ff-saison\s*\{\s*order:\s*(\d+)", css)
    if not m:
        fehler.append("CSS: `main.main > section.ff-saison { order: N }` fehlt – auf Mobile "
                      "landet der Saison-Block (order: auto = 0) VOR den Artikel-Karten und "
                      "schiebt das LCP-Cover aus dem Viewport.")
        return fehler
    order = int(m.group(1))
    if order <= 1:
        fehler.append(f"CSS: order: {order} für section.ff-saison – die Artikel-Karten mit dem "
                      "LCP-Cover haben order: 1 (custom.css) und müssen VORNE bleiben.")
    if order > 5:
        fehler.append(f"CSS: order: {order} für section.ff-saison – die Ratgeber-Cluster liegen "
                      "bei order: 5 (custom.css); der Saison-Block muss in derselben Reihe "
                      "VOR ihnen stehen (gleicher Wert + frühere DOM-Position genügt).")
    if "@media (max-width: 768px)" not in css:
        fehler.append("CSS: die Mobile-Reihenfolge der Startseite greift bei max-width 768px "
                      "(custom.css) – die Saison-Regel muss im selben Bereich stehen.")
    if "prefers-reduced-motion" not in css:
        fehler.append("CSS: prefers-reduced-motion fehlt (DESIGN.md §6: Lifts aus).")
    return fehler


# --------------------------------------------------------------------------
#  S7 – Auswahl-Spiegel (1:1 zu _funcs/saison-kontext.html)
# --------------------------------------------------------------------------

def _parse_datum(wert) -> datetime.datetime | None:
    if isinstance(wert, datetime.datetime):
        return wert if wert.tzinfo else wert.replace(tzinfo=datetime.timezone.utc)
    if isinstance(wert, datetime.date):
        return datetime.datetime(wert.year, wert.month, wert.day, tzinfo=datetime.timezone.utc)
    if isinstance(wert, str) and wert.strip():
        try:
            return datetime.datetime.fromisoformat(wert.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _frontmatter(pfad: Path) -> dict:
    roh = pfad.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", roh, re.S)
    if not m:
        return {}
    try:
        daten = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return daten if isinstance(daten, dict) else {}


def live_artikel(root: Path) -> list[dict]:
    """LIVE-Artikel genau wie das Template: Section posts, nicht draft,
    nicht hiddenInHomeList – und ohne _index.md (Sektionsseite, die in
    site.RegularPages ohnehin nicht vorkommt)."""
    artikel = []
    for pfad in sorted((root / "content" / "posts").rglob("*.md")):
        if pfad.name == "_index.md":
            continue
        meta = _frontmatter(pfad)
        if not meta or meta.get("draft"):
            continue
        if str(meta.get("hiddenInHomeList")) == "true":
            continue
        datum = _parse_datum(meta.get("date")) or _parse_datum(meta.get("lastmod"))
        if datum is None:
            datum = datetime.datetime.fromtimestamp(pfad.stat().st_mtime, datetime.timezone.utc)
        slug = pfad.parent.name if pfad.name == "index.md" else pfad.stem
        blob = " {} | {} | {} | {} | {} ".format(
            str(meta.get("title") or "").lower(),
            str(meta.get("description") or "").lower(),
            " ".join(str(t) for t in (meta.get("tags") or [])).lower(),
            " ".join(str(t) for t in (meta.get("keywords") or [])).lower(),
            f"/posts/{slug}/".lower(),
        )
        artikel.append({
            "pfad": pfad,
            "slug": slug,
            "titel": str(meta.get("title") or ""),
            "pillar": str(meta.get("pillar") or ""),
            "datum": datum,
            "zeit": datum.timestamp(),
            "blob": blob,
            "href": f"/posts/{slug}/",
        })
    return artikel


def auswahl(saison: dict, artikel: list[dict], mindest: int) -> tuple[list[dict], str, int]:
    """Spiegel der Template-Logik. Rang = Relevanz * 1e12 + Unix-Zeit:
    Hugo sortiert immer die ganze Liste neu, zwei verkettete sort()-Aufrufe
    würden die Relevanz wieder kippen (am 20.09.2026 im Build beobachtet)."""
    keywords = [str(k).lower() for k in (saison.get("keywords") or []) if str(k).strip()]
    relevant = []
    for art in artikel:
        wert = sum(1 for kw in keywords if kw in art["blob"])
        if wert > 0:
            rang = wert * 1_000_000_000_000 + int(art["zeit"])
            relevant.append((rang, wert, art))
    if len(relevant) >= mindest:
        relevant.sort(key=lambda x: -x[0])
        return [art for _, _, art in relevant[:mindest]], "keywords", len(relevant)

    pillars = [str(p) for p in (saison.get("saison_pillars") or [])]
    treffend = [a for a in artikel if a["pillar"] in pillars]
    if len(treffend) >= mindest:
        treffend.sort(key=lambda a: -a["zeit"])
        return treffend[:mindest], "pillar", len(treffend)

    alle = sorted(artikel, key=lambda a: -a["zeit"])
    return alle[:mindest], "neueste", len(alle)


def themen_namen(root: Path) -> dict[str, str]:
    try:
        daten = json.loads((root if root else ROOT).joinpath("data/themenwelten.json")
                           .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(t.get("id")): str(t.get("title")) for t in daten.get("topics", [])
            if isinstance(t, dict)}


# --------------------------------------------------------------------------
#  Build-Prüfung (B1–B7) – HTMLParser, weil `hugo --minify` Attribute
#  ohne Anführungszeichen schreibt (Regex wäre hier blind).
# --------------------------------------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr", "path", "circle", "rect", "use"}


class Knoten:
    __slots__ = ("tag", "attrs", "text", "kids", "reihenfolge")

    def __init__(self, tag: str, attrs: dict, reihenfolge: int):
        self.tag = tag
        self.attrs = attrs
        self.text = ""
        self.kids: list[Knoten] = []
        self.reihenfolge = reihenfolge

    def klasse(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    def hat_klasse(self, name: str) -> bool:
        return name in self.klasse()

    def volltext(self) -> str:
        teile = [self.text] + [k.volltext() for k in self.kids]
        return re.sub(r"\s+", " ", " ".join(t for t in teile if t)).strip()


class SeitenBaum(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.wurzel: list[Knoten] = []
        self.stapel: list[Knoten] = []
        self.flat: list[Knoten] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self._anfang(tag, dict(attrs))
        if tag not in VOID:
            self.stapel.append(self.flat[-1])

    def handle_startendtag(self, tag, attrs):
        self._anfang(tag, dict(attrs))

    def _anfang(self, tag: str, attrs: dict):
        knoten = Knoten(tag, attrs, len(self.flat))
        self.flat.append(knoten)
        (self.stapel[-1].kids if self.stapel else self.wurzel).append(knoten)

    def handle_endtag(self, tag):
        for i in range(len(self.stapel) - 1, -1, -1):
            if self.stapel[i].tag == tag:
                del self.stapel[i:]
                return

    def handle_data(self, data):
        if self.stapel and data.strip():
            self.stapel[-1].text += data

    def nach_klasse(self, name: str) -> list[Knoten]:
        return [k for k in self.flat if k.hat_klasse(name)]

    def nach_tag(self, tag: str) -> list[Knoten]:
        return [k for k in self.flat if k.tag == tag]


def output_path(public: Path, href: str, base_path: str) -> Path | None:
    if not href or href.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
        return None
    pfad = href.split("#")[0].split("?")[0]
    if base_path and base_path != "/" and pfad.startswith(base_path):
        pfad = "/" + pfad[len(base_path):]
    ziel = (public / pfad.lstrip("/")).resolve()
    if ziel.is_dir():
        kandidat = ziel / "index.html"
        return kandidat if kandidat.exists() else None
    if ziel.exists():
        return ziel
    return None if not (ziel.with_name(ziel.name + ".html")).exists() else ziel.with_name(ziel.name + ".html")


def validate_build(public: Path, saison: dict, erwartet: list[dict], quelle: str,
                   mindest: int, base_path: str = "/") -> list[str]:
    fehler: list[str] = []
    index = public / "index.html"
    if not index.is_file():
        return [f"Build fehlt: {index} – vorher `hugo --destination public` ausführen "
                "(kein stiller Skip, vgl. themenwelten_guard.py)."]
    html = index.read_text(encoding="utf-8", errors="ignore")
    seite = SeitenBaum(html)
    sid = str(saison.get("id"))

    # B1 – Struktur
    h1 = seite.nach_tag("h1")
    if len(h1) != 1:
        fehler.append(f"B1: Startseite hat {len(h1)} H1-Elemente, erwartet genau 1 "
                      "(Bestands-Test e2e/home.spec.mjs).")
    blocks = seite.nach_klasse("ff-saison")
    blocks = [b for b in blocks if b.tag == "section"]
    if len(blocks) != 1:
        fehler.append(f"B1: {len(blocks)} × section.ff-saison im Build, erwartet genau 1.")
        return fehler
    block = blocks[0]

    # B2 – Saison-Kohärenz
    for knoten, name in ((seite.nach_klasse("ff-saison-badge"), "Badge"),
                         (seite.nach_klasse("ff-saison-hinweis"), "Hinweis"),
                         ([block], "Block")):
        if not knoten:
            fehler.append(f"B2: {name} der saisonalen Startseite fehlt im Build.")
            continue
        for k in knoten:
            if k.attrs.get("data-ff-saison") != sid:
                fehler.append(f"B2: {name} trägt data-ff-saison="
                              f"{k.attrs.get('data-ff-saison')!r}, erwartet {sid!r}.")
    badge = seite.nach_klasse("ff-saison-badge")
    if badge and str(saison.get("badge", "")) not in badge[0].volltext():
        fehler.append(f"B2: Badge-Text weicht von data/saisons.yaml ab: "
                      f"{badge[0].volltext()!r} ≠ {saison.get('badge')!r}.")
    hinweis = seite.nach_klasse("ff-saison-hinweis")
    if hinweis and str(saison.get("hinweis", "")) not in hinweis[0].volltext():
        fehler.append(f"B2: Hinweis-Text weicht von data/saisons.yaml ab.")
    if block.attrs.get("data-ff-saison-quelle") != quelle:
        fehler.append(f"B2: Block meldet Auswahl-Quelle {block.attrs.get('data-ff-saison-quelle')!r}, "
                      f"der Spiegel erwartet {quelle!r} – Template und Wache laufen auseinander.")

    # B3 – Karten: Anzahl, Reihenfolge, Ziele
    karten = [k for k in seite.nach_klasse("ff-saison-card") if k.tag == "a"]
    if len(karten) != mindest:
        fehler.append(f"B3: {len(karten)} Saison-Karten gebaut, erwartet {mindest} "
                      "(`min_artikel` – der Block darf nie leer oder halb sein).")
    gebaut = [k.attrs.get("href", "") for k in karten]
    erwartet_hrefs = [a["href"] for a in erwartet]
    if gebaut[:len(erwartet_hrefs)] != erwartet_hrefs:
        fehler.append("B3: Karten-Reihenfolge weicht vom Auswahl-Spiegel ab.\n"
                      f"      gebaut:   {gebaut}\n      erwartet: {erwartet_hrefs}")
    for k in karten:
        href = k.attrs.get("href", "")
        ziel = output_path(public, href, base_path)
        if ziel is None:
            fehler.append(f"B3: Saison-Karte verlinkt ins Leere: {href}")
        titel = [x for x in k.kids if x.hat_klasse("ff-saison-card-titel")]
        if not titel or not titel[0].volltext():
            fehler.append(f"B3: Saison-Karte {href} hat keinen Titel-Text.")
        # B4 – Messung
        for attribut, soll in (("data-umami-event", "cta_click"),
                               ("data-umami-event-placement", "start-saison"),
                               ("data-umami-event-saison", sid)):
            if k.attrs.get(attribut) != soll:
                fehler.append(f"B4: Karte {href}: {attribut} = {k.attrs.get(attribut)!r}, "
                              f"erwartet {soll!r} (Revenue-Trichter wäre blind).")
        if not k.attrs.get("data-umami-event-slug", "").startswith(f"saison-{sid}-"):
            fehler.append(f"B4: Karte {href}: data-umami-event-slug muss mit "
                          f"„saison-{sid}-“ beginnen.")
        if not k.attrs.get("aria-labelledby"):
            fehler.append(f"B4: Karte {href}: aria-labelledby fehlt (a11y-Vertrag der "
                          "bestehenden Themenkarten).")

    pillar_link = [k for k in seite.nach_klasse("ff-saison-pillar") if k.tag == "a"]
    if not pillar_link:
        fehler.append("B3: Ratgeber-Link im Saison-Block fehlt.")
    else:
        ziel = output_path(public, pillar_link[0].attrs.get("href", ""), base_path)
        if ziel is None:
            fehler.append(f"B3: Ratgeber-Link zeigt ins Leere: {pillar_link[0].attrs.get('href')}")
        if pillar_link[0].attrs.get("data-umami-event") != "cta_click":
            fehler.append("B4: Ratgeber-Link ohne cta_click-Event.")

    # B5 – CSS wirklich eingebunden
    if ".ff-saison-card" not in html or f".ff-saison--{sid}" not in html:
        fehler.append("B5: Das gebaute CSS-Bundle enthält die Saison-Klassen nicht – "
                      "assets/css/extended/zz-saisonale-startseite.css wird nicht geladen.")

    # B7 – DOM-Budget
    if len(seite.flat) > DOM_NODES_SOFT:
        fehler.append(f"B7: Startseite hat {len(seite.flat)} DOM-Knoten "
                      f"(Softlimit {DOM_NODES_SOFT}, siehe scripts/cwv_guard.py).")
    return fehler


# --------------------------------------------------------------------------
#  Quelle laden / Gesamtlauf
# --------------------------------------------------------------------------

def quelle_laden(root: Path) -> tuple[dict, list[str]]:
    pfad = root / "data" / "saisons.yaml"
    if not pfad.is_file():
        return {}, [f"Quelle fehlt: {pfad}"]
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, [f"data/saisons.yaml ist nicht parsebar: {exc}"]
    return daten or {}, []


def pruefe_quelle(root: Path, datum: datetime.date, json_modus: bool = False) -> tuple[int, dict]:
    daten, fehler = quelle_laden(root)
    if fehler:
        return 3, {"fehler": fehler, "saisons": []}

    saisons, schema_fehler = validate_schema(daten)
    fehler += schema_fehler
    if schema_fehler:
        # Ohne gültiges Schema sind die Folgeprüfungen sinnlos (Hugo bricht
        # mit errorf ohnehin hart ab) → Exit 3 wie die KRITISCH-Klasse.
        return 3, {"fehler": fehler, "saisons": [s.get("id") for s in saisons]}

    fehler += kalender_abdeckung(saisons)
    fehler += validate_stimme(saisons)
    fehler += validate_farben(saisons)
    fehler += validate_pillars(saisons, root)
    fehler += validate_datenpfad()

    css_pfad = root / "assets" / "css" / "extended" / "zz-saisonale-startseite.css"
    css = css_pfad.read_text(encoding="utf-8") if css_pfad.is_file() else ""
    if not css:
        fehler.append(f"CSS fehlt: {css_pfad}")
    else:
        fehler += validate_css_parity(saisons, css)
        fehler += validate_lcp_schutz(css)

    artikel = live_artikel(root)
    namen = themen_namen(root)
    if not artikel:
        fehler.append("S7: keine LIVE-Artikel unter content/posts gefunden – "
                      "die Auswahl hätte nichts zur Auswahl.")
    spiegel: dict[str, dict] = {}
    for saison in saisons:
        mindest = int(saison.get("min_artikel") or daten.get("min_artikel_default") or 3)
        aus, quell, kandidaten = auswahl(saison, artikel, mindest)
        spiegel[str(saison["id"])] = {
            "quelle": quell,
            "mindest": mindest,
            "kandidaten": kandidaten,
            "artikel": [{"href": a["href"], "titel": a["titel"],
                         "datum": a["datum"].date().isoformat(),
                         "thema": namen.get(a["pillar"], a["pillar"])} for a in aus],
        }
        if len(aus) < mindest:
            fehler.append(f"S7: Saison {saison['id']} findet nur {len(aus)} von {mindest} "
                          "Artikeln im Bestand – der Block wäre unvollständig.")
        if quell != "keywords":
            fehler.append(f"S7: Saison {saison['id']} fällt auf Stufe „{quell}“ zurück – die "
                          "`keywords` treffen zu wenige LIVE-Artikel (Bestand prüfen oder "
                          "Begriffe ergänzen).")

    aktuelle = saison_fuer(datum, saisons)
    if not aktuelle:
        fehler.append(f"S2: kein Saison-Fenster deckt {datum.isoformat()} ab.")

    ergebnis = {
        "datum": datum.isoformat(),
        "saison": (aktuelle or {}).get("id"),
        "fehler": fehler,
        "spiegel": spiegel,
        "kontraste": {
            str(s["id"]): {f: str(s.get(f)) for f in PFLICHTFELDER_FARBEN} for s in saisons
        },
    }
    return (1 if fehler else 0), ergebnis


def pruefe_build(public: Path, root: Path, datum: datetime.date,
                 base_path: str = "/") -> tuple[int, dict]:
    daten, fehler = quelle_laden(root)
    if fehler:
        return 3, {"fehler": fehler}
    saisons, _ = validate_schema(daten)
    aktuelle = saison_fuer(datum, saisons)
    if not aktuelle:
        return 3, {"fehler": [f"kein Saison-Fenster deckt {datum.isoformat()} ab"]}
    artikel = live_artikel(root)
    mindest = int(aktuelle.get("min_artikel") or daten.get("min_artikel_default") or 3)
    aus, quell, _ = auswahl(aktuelle, artikel, mindest)
    fehler = validate_build(public, aktuelle, aus, quell, mindest, base_path)
    return (1 if fehler else 0), {
        "datum": datum.isoformat(),
        "saison": aktuelle.get("id"),
        "quelle": quell,
        "karten": [a["href"] for a in aus],
        "fehler": fehler,
    }


# --------------------------------------------------------------------------
#  Selbsttest (Exit 2 bei Bruch) – Logik-Beweis ohne Repo-Schreibzugriff
# --------------------------------------------------------------------------

def selbsttest() -> int:
    def muss(bedingung: bool, text: str):
        if not bedingung:
            print(f"❌ SELBSTTEST FEHLGESCHLAGEN: {text}")
            return False
        return True

    ok = True
    basis = [
        {"id": "herbst", "ab": "09-01", "bis": "11-30"},
        {"id": "winter", "ab": "12-01", "bis": "02-29"},
        {"id": "fruehling", "ab": "03-01", "bis": "05-31"},
        {"id": "sommer", "ab": "06-01", "bis": "08-31"},
    ]
    faelle = [
        ("2026-08-31", "sommer"), ("2026-09-01", "herbst"), ("2026-09-20", "herbst"),
        ("2026-11-30", "herbst"), ("2026-12-01", "winter"), ("2026-12-31", "winter"),
        ("2027-01-01", "winter"), ("2028-02-29", "winter"), ("2027-02-28", "winter"),
        ("2027-03-01", "fruehling"), ("2027-05-31", "fruehling"), ("2027-06-01", "sommer"),
    ]
    for datum, soll in faelle:
        tag = datetime.date.fromisoformat(datum)
        ist = saison_fuer(tag, basis)
        ok &= muss(bool(ist) and ist["id"] == soll,
                   f"{datum} → {soll} erwartet, {(ist or {}).get('id')} bekommen")

    ok &= muss(kalender_abdeckung(basis) == [], "lückenlose Vier-Saisons-Abdeckung "
               f"meldet Fehler: {kalender_abdeckung(basis)[:2]}")
    luecke = [s for s in basis if s["id"] != "sommer"]
    ok &= muss(bool(kalender_abdeckung(luecke)), "eine fehlende Saison muss als Kalender-Lücke "
               "auffallen")
    ueberlappung = basis + [{"id": "herbst", "ab": "09-01", "bis": "11-30"}]
    ok &= muss(any("Überlappung" in f for f in kalender_abdeckung(ueberlappung)),
               "doppelte Fenster müssen als Überlappung auffallen")

    # Kontrast-Referenzwerte (gegen WCAG-Beispiele gerechnet)
    ok &= muss(kontrast("#000000", "#FFFFFF") == 21.0, "Schwarz/Weiß muss 21:1 ergeben")
    ok &= muss(abs(kontrast("#767676", "#FFFFFF") - 4.54) < 0.05,
               "#767676 auf Weiß muss ≈ 4.54:1 ergeben (WCAG-Referenz)")
    ok &= muss(kontrast("#FFB300", "#FFFFFF") < 2.0,
               "Signalgelb auf Weiß muss unter 2:1 bleiben – genau deshalb ist es "
               "laut PRODUCT.md nie Textfarbe auf hellem Grund")

    # Auswahl-Spiegel: Relevanz schlägt Datum, Datum bricht Gleichstand
    artikel = [
        {"href": "/posts/a/", "titel": "A", "pillar": "strom-sparen", "zeit": 300.0,
         "datum": datetime.datetime(2026, 9, 3, tzinfo=datetime.timezone.utc),
         "blob": " heizkosten gas herbst "},
        {"href": "/posts/b/", "titel": "B", "pillar": "frugalismus", "zeit": 200.0,
         "datum": datetime.datetime(2026, 9, 2, tzinfo=datetime.timezone.utc),
         "blob": " budget haushaltsbuch "},
        {"href": "/posts/c/", "titel": "C", "pillar": "strom-sparen", "zeit": 100.0,
         "datum": datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
         "blob": " heizkosten "},
        {"href": "/posts/d/", "titel": "D", "pillar": "strom-sparen", "zeit": 400.0,
         "datum": datetime.datetime(2026, 9, 4, tzinfo=datetime.timezone.utc),
         "blob": " irgendwas ohne treffer "},
    ]
    saison = {"id": "herbst", "keywords": ["heizkosten", "gas", "herbst"],
              "saison_pillars": ["strom-sparen"], "min_artikel": 2}
    aus, quell, _ = auswahl(saison, artikel, 2)
    ok &= muss(quell == "keywords" and [a["href"] for a in aus] == ["/posts/a/", "/posts/c/"],
               f"Relevanz muss vor Datum sortieren, bekommen: {quell} "
               f"{[a['href'] for a in aus]}")
    saison_fallback = {"id": "x", "keywords": ["gibt-es-nicht"],
                       "saison_pillars": ["strom-sparen"], "min_artikel": 2}
    aus, quell, _ = auswahl(saison_fallback, artikel, 2)
    ok &= muss(quell == "pillar" and [a["href"] for a in aus] == ["/posts/d/", "/posts/a/"],
               f"Pillar-Fallback muss nach Datum wählen, bekommen: {quell} "
               f"{[a['href'] for a in aus]}")
    aus, quell, _ = auswahl({"id": "y", "keywords": [], "saison_pillars": ["konto-karten"],
                             "min_artikel": 2}, artikel, 2)
    ok &= muss(quell == "neueste", f"letzter Fallback muss „neueste“ sein, bekommen: {quell}")

    # Datenpfad-Detektor sieht site.Data im Template-Code, nicht im Kommentar
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "t.html"
        pfad.write_text("{{/* site.Data ist verboten */}}\n{{ with site.Data.x }}y{{ end }}\n",
                        encoding="utf-8")
        ok &= muss(bool(validate_datenpfad([pfad])),
                   "Datenpfad-Detektor muss site.Data im Code finden")
        pfad.write_text("{{/* nur ein Kommentar über hugo.Data */}}\n<p>ok</p>\n",
                        encoding="utf-8")
        ok &= muss(not validate_datenpfad([pfad]),
                   "Datenpfad-Detektor darf Kommentare nicht als Fund zählen")

        # CSS-Drift-Detektor
        css = (".ff-saison--herbst { --ff-saison-akzent: #9A5B12; --ff-saison-linie: #000000; "
               "--ff-saison-hero-text: #FFD15A; }\n"
               ':root[data-theme="dark"] .ff-saison--herbst { --ff-saison-akzent: #E9A94C; '
               "--ff-saison-linie: #E9A94C; }\n"
               "@media (prefers-color-scheme: dark) { :root[data-theme=\"auto\"] "
               ".ff-saison--herbst { --ff-saison-akzent: #E9A94C; --ff-saison-linie: #E9A94C; } }\n")
        fund = validate_css_parity([{"id": "herbst", "akzent": "#9A5B12", "linie": "#B26A00",
                                     "hero_text": "#FFD15A", "akzent_dunkel": "#E9A94C",
                                     "linie_dunkel": "#E9A94C"}], css)
        ok &= muss(any("CSS-Drift" in f for f in fund),
                   f"CSS-Drift muss auffallen, bekommen: {fund}")

        # LCP-Schutz-Detektor
        ok &= muss(bool(validate_lcp_schutz(".ff-saison { color: red; }")),
                   "fehlende order-Regel muss auffallen")
        ok &= muss(bool(validate_lcp_schutz("@media (max-width: 768px) { main.main > "
                                            "section.ff-saison { order: 0 } } "
                                            "@media (prefers-reduced-motion: reduce) {}")),
                   "order: 0 (vor den LCP-Karten) muss auffallen")
        ok &= muss(bool(validate_lcp_schutz("@media (max-width: 768px) { main.main > "
                                            "section.ff-saison { order: 6 } } "
                                            "@media (prefers-reduced-motion: reduce) {}")),
                   "order: 6 (hinter den Clustern) muss auffallen")
        ok &= muss(not validate_lcp_schutz("@media (max-width: 768px) { main.main > "
                                           "section.ff-saison { order: 5 } } "
                                           "@media (prefers-reduced-motion: reduce) {}"),
                   "order: 5 im 768px-Bereich muss durchgehen")

    # Build-Prüfung an synthetischem HTML
    with tempfile.TemporaryDirectory() as tmp:
        public = Path(tmp)
        (public / "posts" / "a").mkdir(parents=True)
        (public / "posts" / "a" / "index.html").write_text("<html></html>", encoding="utf-8")
        (public / "pillar" / "strom-sparen").mkdir(parents=True)
        (public / "pillar" / "strom-sparen" / "index.html").write_text("x", encoding="utf-8")
        gut = (
            "<html><body><main class=main>"
            "<article class='first-entry home-info'><h1>Start</h1>"
            "<div class='ff-saison-badge ff-saison--herbst' data-ff-saison=herbst>Herbst-Check</div>"
            "<p class='ff-saison-hinweis' data-ff-saison=herbst>Die Heizsaison startet.</p></article>"
            "<div class=ff-pinterest-cta></div>"
            "<section class='ff-saison ff-saison--herbst' data-ff-saison=herbst "
            "data-ff-saison-quelle=keywords data-ff-saison-treffer=1>"
            "<a class=ff-saison-pillar href=/pillar/strom-sparen/ data-umami-event=cta_click>Zum Ratgeber</a>"
            "<a class=ff-saison-card href=/posts/a/ data-umami-event=cta_click "
            "data-umami-event-placement=start-saison data-umami-event-saison=herbst "
            "data-umami-event-slug=saison-herbst-a aria-labelledby=a-title>"
            "<span class=ff-saison-card-titel id=a-title>Artikel A</span></a>"
            "</section><article class='post-entry lcp-card'></article></main>"
            "<style>.ff-saison-card{}.ff-saison--herbst{}</style></body></html>"
        )
        (public / "index.html").write_text(gut, encoding="utf-8")
        saison = {"id": "herbst", "badge": "Herbst-Check", "hinweis": "Die Heizsaison startet."}
        erwartet = [{"href": "/posts/a/"}]
        ok &= muss(validate_build(public, saison, erwartet, "keywords", 1) == [],
                   f"sauberer Build meldet Fehler: {validate_build(public, saison, erwartet, 'keywords', 1)}")
        (public / "index.html").write_text(gut.replace("/posts/a/", "/posts/fehlt/"),
                                           encoding="utf-8")
        ok &= muss(any("ins Leere" in f for f in
                       validate_build(public, saison, erwartet, "keywords", 1)),
                   "toter Karten-Link muss auffallen")
        (public / "index.html").write_text(gut.replace("data-ff-saison=herbst", "data-ff-saison=sommer"),
                                           encoding="utf-8")
        ok &= muss(bool(validate_build(public, saison, erwartet, "keywords", 1)),
                   "falsche Saison im Build muss auffallen")
        (public / "index.html").write_text(gut.replace("<h1>Start</h1>", "<h1>Start</h1><h1>zwei</h1>"),
                                           encoding="utf-8")
        ok &= muss(any(f.startswith("B1") for f in
                       validate_build(public, saison, erwartet, "keywords", 1)),
                   "zwei H1 müssen auffallen")

    print("✅ Selbsttest bestanden (Saison-Fenster, Kalender, Kontrast, Auswahl-Spiegel, "
          "Datenpfad, CSS-Drift, LCP-Schutz, Build-Prüfung)" if ok
          else "❌ Selbsttest FEHLGESCHLAGEN")
    return 0 if ok else 2


# --------------------------------------------------------------------------
#  main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--public", type=Path, default=None,
                        help="gebauter Baum (public/). Ohne Angabe: nur Quellen-Prüfung.")
    parser.add_argument("--source-only", action="store_true", help="nur data/saisons.yaml + CSS")
    parser.add_argument("--base-path", default="/", help="Basis-Pfad bei Unterordner-Builds")
    parser.add_argument("--datum", default=None,
                        help="Stichtag YYYY-MM-DD (Test anderer Saisons; Standard: heute)")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()

    if args.datum:
        try:
            datum = datetime.date.fromisoformat(args.datum)
        except ValueError:
            print(f"❌ --datum erwartet YYYY-MM-DD (gefunden: {args.datum})")
            return 3
    else:
        datum = datetime.datetime.now(datetime.timezone.utc).date()

    exit_quelle, bericht = pruefe_quelle(args.root, datum)
    exit_build = 0
    build_bericht: dict = {}
    if args.public and not args.source_only:
        exit_build, build_bericht = pruefe_build(args.public, args.root, datum, args.base_path)

    gesamt = {"quelle": bericht, "build": build_bericht,
              "stufe": "OK" if not (exit_quelle or exit_build) else "FUND"}
    if args.json:
        print(json.dumps(gesamt, ensure_ascii=False, indent=2, default=str))
    else:
        print("# 🍂 SAISONALE STARTSEITE – Wache (saisonale_startseite_guard.py)\n")
        print(f"**Stichtag:** {datum.isoformat()} · **Saison:** `{bericht.get('saison')}`\n")
        spiegel = bericht.get("spiegel") or {}
        if spiegel:
            print("| Saison | Auswahl-Quelle | Kandidaten | Artikel im Block |")
            print("|---|---|---|---|")
            for sid, info in spiegel.items():
                titel = " · ".join(a["titel"][:44] for a in info["artikel"]) or "–"
                print(f"| {sid} | {info['quelle']} | {info['kandidaten']} | {titel} |")
            print()
        if build_bericht:
            print(f"**Build:** {args.public} · Karten: {len(build_bericht.get('karten', []))}\n")
        alle = list(bericht.get("fehler", [])) + list(build_bericht.get("fehler", []))
        if alle:
            print(f"## ❌ {len(alle)} Fund(e)\n")
            for f in alle:
                print(f"- {f}")
        else:
            print("## ✅ Keine Funde\n"
                  "Schema, Kalender-Abdeckung (366 Tage), Marken-Stimme, WCAG-Kontraste, "
                  "CSS-/YAML-Deckung, Ratgeber-Ziele, Auswahl-Spiegel, Datenpfad und "
                  "(falls gebaut) der fertige Build sind sauber.")
    return max(exit_quelle, exit_build)


if __name__ == "__main__":
    sys.exit(main())
