#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FRONTMATTER-WACHE – eine Zeile Content darf den Bau nicht töten.

WARUM ES DIESE WACHE GIBT (Vorgang WF-9FD5, Meldung #901, 26.10.2026)
=====================================================================
Der wöchentliche Layout-AI-Lauf auf `main` fiel am 26.10.2026 um 15:03 UTC
aus – nicht an einer Prüfung, sondern am **Bau**:

    Website bauen (identisch zur Produktion, minifiziert)   ✗ failure
    Statisches Layout-Audit                                 ⊘ skipped
    Lauf rot stellen, wenn Befunde offen sind               ✗ failure

Die Meldung #901 riet daraufhin zu „API-Key abgelaufen". Die echte Ursache
stand in einer einzigen Zeile Content:

    content/posts/2026-10-09-balkonkraftwerk-…/index.md:2
    description: Stromkosten senken: Balkonkraftwerk-Förderung regional …

Ein Doppelpunkt **innerhalb** eines unquotierten YAML-Werts. Ab da liest
jeder YAML-Parser `description: Stromkosten senken` und danach einen
Verschachtelungsschlüssel – Hugo bricht ab:

    ERROR error building site: assemble: failed to create page from
    pageMetaSource …: [2:14] mapping value is not allowed in this context

Die Folge war nicht „ein Artikel fehlt", sondern: **kein Build, keine
Auslieferung, keine Messung** – für den ganzen Bestand. Und weil der Bau
vor jeder Prüfung steht, konnte keine der vorhandenen Wachen das melden,
was wirklich kaputt war.

DIE LEHRE (und darum diese Wache)
---------------------------------
Die teuerste Blindstelle des Repos war bisher „stiller Build-Tod"
(`docs/ANLEITUNG-HUGO-BUILD.md`, Vertrag H1–H9). Diese Wache schließt die
letzte Lücke davor: Sie prüft das Frontmatter **bevor** Hugo es sieht –
mit Datei, Zeile und Spalte, nach derselben Klasse, die Hugo tötet.

Sie läuft an drei Stellen:
  1. in `.github/actions/hugo-build` – also vor **jedem** Bau dieses Repos
     (Deploy, E2E, Layout-AI, Publication-Reliability). Ein kaputter Bau
     nennt jetzt die Zeile statt „assemble: failed to create page".
  2. als PR-Gate in `e2e.yml` (Quelle, vor dem Bau).
  3. lokal: `npm run frontmatter:check`.

DIE REGELN
----------
Bewertung: **BLOCKER** = Hugo kann die Seite nicht bauen oder liest den
Wert anders, als er dasteht. **HINWEIS** = baut, ist aber eine stille
Falle (z. B. Kommentar schneidet den Wert ab).

WF-990 (01.11.2026, Duplikat statt Hinweis): Ein doppelter Schlüssel war
hier als HINWEIS eingestuft, mit der Begründung „YAML nimmt still den
letzten Wert". Das stimmt für PyYAML und ist für Hugo FALSCH: Hugo bricht
den Bau mit „mapping key \"description\" already defined" ab. Genau diese
Einstufung hat am 01.11.2026 den Squash-Merge von PR #1004 durchgelassen –
der Wächter sah den Fund, der Schritt blieb grün, `main` war danach nicht
mehr baubar. Die Konsequenz: Die Doppelt-Prüfung des Scanners (F3) ist die
EINZIGE Stelle, die den Fall ohne Parser sieht – der YAML-Parser ist hier
blind, weil er den letzten Wert nimmt und den ersten still verwirft. Ein
Befund, der den Bau tötet, darf kein Hinweis sein.

  F1  GERÜST      Frontmatter vorhanden und geschlossen (`---`, `+++`
                  oder JSON-Objekt am Dateianfang). Offenes Frontmatter
                  ist ein Bau-Abbruch, kein Stilthema.
  F2  PARSER      Der eingesetzte Parser (YAML/TOML/JSON) nimmt den Block
                  an. YAML wird – wenn PyYAML vorhanden ist – wirklich
                  geparst; sonst greift F3 (siehe „Zwei Schichten").
  F3  PLAIN-SKALAR  Die Klasse vom 26.10.2026, ohne Parser erkennbar:
                  `: ` im unquotierten Wert, Wert endet auf `:`,
                  unbalancierte Anführungszeichen, nicht geschlossene
                  Flow-Sammlung, Tabulator-Einrückung, reservierte
                  Indikatoren (`@`, `` ` ``, `%`), unbekannter Alias,
                  doppelter Schlüssel.
  F4  TYP-VERTRAG  `title`/`description`/`slug` sind Text (kein Wahrheits-
                  wert, keine Zahl – Hugo schriebe „True" in den `<title>`),
                  Datumsfelder sind ISO-Daten (`date`, `publishDate`,
                  `lastmod`, `expiryDate`), `draft` ist kein Objekt.
  F5  YAML-1.1    `yes/no/on/off/y/n` als unquotierter Text: PyYAML (1.1)
                  liest einen Wahrheitswert, Hugos Parser (1.2) einen Text.
                  Zwei Werkzeuge, zwei Bedeutungen – also zitieren.
  F6  KOMMENTAR   ` #` in einem unquotierten Wert: Alles dahinter ist
                  Kommentar. Der Wert ist kürzer als das, was dasteht.

ZWEI SCHICHTEN – UND WARUM DIE UNTERE ALLEIN TRÄGT
--------------------------------------------------
Die kritische Schicht (F1, F3–F6) ist **stdlib-only**. Sie muss auch dort
laufen, wo kein PyYAML installiert ist (die `hugo-build`-Action baut in
einem nackten Runner). Die obere Schicht (F2/F4 über einen echten Parser)
schaltet sich zu, sobald PyYAML importierbar ist, und sagt im Bericht,
welche Schicht aktiv war – stille Degradierung wäre derselbe Fehler wie
ein `--quiet` (H4).

NUTZUNG
-------
  python3 scripts/frontmatter_wache.py                 # Bestand prüfen (content/)
  python3 scripts/frontmatter_wache.py --pfad content  # anderer Pfad
  python3 scripts/frontmatter_wache.py --json          # Maschinenbefund
  python3 scripts/frontmatter_wache.py --md            # Markdown (Job-Summary)
  python3 scripts/frontmatter_wache.py --md-datei X    # Markdown in Datei X
  python3 scripts/frontmatter_wache.py --kurzbefund    # eine Zeile, für Annotationen
  python3 scripts/frontmatter_wache.py --fix           # heilt genau die F3-Klasse
  python3 scripts/frontmatter_wache.py --streng        # HINWEISE zählen als Befund
  python3 scripts/frontmatter_wache.py --selftest      # Sabotage-Proben

EXIT: 0 = kein BLOCKER · 1 = BLOCKER (oder HINWEIS mit `--streng`) ·
      2 = Selbsttest/Setup defekt.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD_PFAD = "content"

BLOCKER = "BLOCKER"
HINWEIS = "HINWEIS"

# Dateiendungen, die Hugo als Inhalt liest.
INHALT_ENDUNGEN = (".md", ".markdown")

# Felder mit Typ-Vertrag (F4). Bewusst nur die, die Hugo wirklich auswertet.
TEXT_FELDER = ("title", "description", "kurzantwort", "slug", "subtitle",
               "summary", "linkTitle")
DATUM_FELDER = ("date", "publishDate", "lastmod", "expiryDate",
                "reserve_published")

# YAML 1.1 liest diese Wörter als Wahrheitswert, YAML 1.2 als Text (F5).
YAML11_BOOLE = {"y", "n", "yes", "no", "on", "off"}

# Reservierte Indikatoren, die am Anfang eines Plain-Skalars nie stehen dürfen.
RESERVIERT = "@`%"

ISO_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?"
                       r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$")

# `key: wert` – Schlüssel ohne Doppelpunkt, Wert alles nach dem ersten Doppelpunkt.
SCHLUESSEL_ZEILE = re.compile(r"^(?P<einzug>[ \t]*)(?P<key>[^\s:#][^:#]*?):(?P<rest>.*)$")
BLOCK_KOPF = re.compile(r"^[|>][-+]?[0-9]?\s*(?:#.*)?$")


# ======================================================================
#  Befund
# ======================================================================
class Befund(dict):
    """Ein Befund als dict – JSON-fähig, mit stabiler Sortierung."""

    def __init__(self, regel: str, schwere: str, pfad: str, zeile: int,
                 spalte: int, meldung: str, heilbar: bool = False):
        super().__init__(regel=regel, schwere=schwere, pfad=pfad,
                         zeile=zeile, spalte=spalte, meldung=meldung,
                         heilbar=heilbar)

    def kurz(self) -> str:
        ort = f"{self['pfad']}:{self['zeile']}"
        if self["spalte"]:
            ort += f":{self['spalte']}"
        return f"{self['regel']} {ort} – {self['meldung']}"


# ======================================================================
#  Frontmatter-Gerüst (F1)
# ======================================================================
def frontmatter_bereich(text: str) -> tuple[str, str, int, str | None, int]:
    """Zerlegt eine Inhaltsdatei in (art, frontmatter, startzeile, fehler, ende).

    `art` ist "yaml", "toml", "json" oder "" (kein Frontmatter).
    `frontmatter` ist der Text ZWISCHEN den Trennern, `startzeile` die
    1-basierte Zeile der ersten Frontmatter-Zeile, `fehler` eine Meldung, wenn
    das Gerüst selbst kaputt ist, und `ende` die 1-basierte Zeile des
    schließenden Trenners (0 = kein Frontmatter).

    `ende` ist nicht Kosmetik: Ohne sie heilt `heile_datei` auch Fließtext,
    der zufällig wie ein Schlüssel aussieht – und genau das ist am 29.10.2026
    in einer Generalprobe passiert („Annahme: Die Anlage kostet …" wurde
    zitiert). Eine Heilung, die den Artikel umschreibt, ist keine Heilung.
    """
    if text.startswith("\ufeff"):            # BOM entfernt Hugo ebenfalls
        text = text[1:]
    # JSON-Frontmatter: das Objekt steht am Dateianfang, ohne Trenner.
    if text.lstrip().startswith("{"):
        try:
            _, ende = json.JSONDecoder().raw_decode(text.lstrip())
        except ValueError as exc:
            return "json", "", 1, f"JSON-Frontmatter nicht lesbar: {exc}", 0
        roh = text.lstrip()[:ende]
        return "json", roh, 1, None, roh.count("\n") + 1

    zeilen = text.splitlines(keepends=True)
    if not zeilen:
        return "", "", 1, None, 0
    trenner = zeilen[0].rstrip("\r\n")
    if trenner not in ("---", "+++"):
        return "", "", 1, None, 0
    art = "yaml" if trenner == "---" else "toml"
    for nr, zeile in enumerate(zeilen[1:], start=2):
        if zeile.rstrip("\r\n") == trenner:
            return art, "".join(zeilen[1:nr - 1]), 2, None, nr
    return art, "".join(zeilen[1:]), 2, (
        f"Frontmatter wird nie geschlossen – der Trenner `{trenner}` fehlt "
        f"ein zweites Mal. Hugo liest die Datei dann gar nicht als Seite."), 0


# ======================================================================
#  Schicht 1: Plain-Skalar-Scanner (F3–F6) – ohne Abhängigkeiten
# ======================================================================
def _zaehl_quotes(wert: str) -> tuple[bool, bool]:
    """(doppelt geschlossen, einfach geschlossen) für einen Zitat-Skalar."""
    if wert.startswith('"'):
        i, geschlossen = 1, False
        while i < len(wert):
            if wert[i] == "\\":
                i += 2
                continue
            if wert[i] == '"':
                geschlossen = True
                break
            i += 1
        return geschlossen, True
    if wert.startswith("'"):
        i, geschlossen = 1, False
        while i < len(wert):
            if wert[i] == "'":
                if i + 1 < len(wert) and wert[i + 1] == "'":
                    i += 2
                    continue
                geschlossen = True
                break
            i += 1
        return True, geschlossen
    return True, True


def _zitat_schluss(wert: str) -> int | None:
    """Index des schließenden Anführungszeichens im Wert – None, wenn keins.

    Gebraucht für die Klasse, die am 29.10.2026 auf `main` stand:
    ``reserve_reaktiviert: "… Klasse „heilbar" ist heilbar, …"`` – das
    ASCII-Zeichen nach „heilbar beendet den Wert zu früh, der Rest der Zeile
    ist Text. Der Parser sieht das als Fehler; diese Funktion sieht es auch,
    ohne Parser.
    """
    if not wert or wert[0] not in ('"', "'"):
        return None
    quote, i = wert[0], 1
    while i < len(wert):
        if quote == '"' and wert[i] == "\\":
            i += 2
            continue
        if wert[i] == quote:
            if quote == "'" and i + 1 < len(wert) and wert[i + 1] == "'":
                i += 2
                continue
            return i
        i += 1
    return None


def _zitat_ende(folge: list[str], quote: str) -> int | None:
    """Zeilenindex, in dem ein mehrzeiliges Zitat geschlossen wird – oder None.

    Ein Zitat darf in YAML über mehrere Zeilen laufen (`description: "a\n  b"`).
    Es ist aber nur dann ein mehrzeiliges Zitat, wenn die schließende Zeile
    WIRKLICH existiert. Genau diese Unterscheidung fehlte am 26.10.2026 nicht –
    sie fehlt in jedem Regex, der nur die eine Zeile ansieht.
    """
    for idx, zeile in enumerate(folge):
        i = 0
        while i < len(zeile):
            z = zeile[i]
            if quote == '"' and z == "\\":
                i += 2
                continue
            if z == quote:
                if quote == "'" and i + 1 < len(zeile) and zeile[i + 1] == "'":
                    i += 2
                    continue
                return idx
            i += 1
    return None


def _flow_geschlossen(wert: str, klammer: str) -> bool:
    """Ist eine Flow-Sammlung (`[…]`, `{…}`) in diesem Wert geschlossen?"""
    gegen = {"[": "]", "{": "}"}[klammer]
    tiefe, in_quote, i = 0, "", 0
    while i < len(wert):
        z = wert[i]
        if in_quote:
            if z == "\\" and in_quote == '"':
                i += 2
                continue
            if z == in_quote:
                in_quote = ""
        elif z in ('"', "'"):
            in_quote = z
        elif z in "[{":
            tiefe += 1
        elif z in "]}":
            tiefe -= 1
            if tiefe == 0:
                return z == gegen
        i += 1
    return False


def scanne_yaml(fm: str, startzeile: int, pfad: str,
                anker: set[str] | None = None) -> list[Befund]:
    """Prüft jeden Schlüsselwert ohne Parser. Die Klasse vom 26.10.2026."""
    befunde: list[Befund] = []
    anker = anker if anker is not None else set()
    gesehen: dict[str, int] = {}
    block_einzug: int | None = None      # aktiver Block-Skalar (`|`, `>`)
    offene_quote: tuple[str, int, str] | None = None   # (art, startzeile, key)

    for nr, rohzeile in enumerate(fm.splitlines(), start=startzeile):
        zeile = rohzeile.rstrip("\r")
        if not zeile.strip():
            continue
        einzug = len(zeile) - len(zeile.lstrip(" "))

        # ---- Block-Skalar: alles tiefer Eingerückte gehört zum Text ----
        if block_einzug is not None:
            if einzug > block_einzug:
                continue
            block_einzug = None

        if zeile.lstrip().startswith("#"):
            continue
        if "\t" in zeile[:einzug + 1]:
            befunde.append(Befund(
                "F3", BLOCKER, pfad, nr, zeile.index("\t") + 1,
                "Tabulator in der Einrückung – YAML erlaubt dort nur "
                "Leerzeichen. Hugo bricht mit „found character that cannot "
                "start any token\" ab."))

        # Mehrzeilige Zitate: Bis zur schließenden Zeile nichts bewerten.
        if offene_quote is not None:
            art, qzeile, qkey = offene_quote
            d, e = _zaehl_quotes(zeile.strip())
            if (d if art == '"' else e):
                offene_quote = None
            continue

        rest_zeile = zeile[einzug:]
        # Sequenz-Eintrag: `- key: wert` oder `- wert`
        if rest_zeile.startswith("- "):
            rest_zeile = rest_zeile[2:]
        elif rest_zeile == "-":
            continue

        treffer = SCHLUESSEL_ZEILE.match(rest_zeile)
        if not treffer:
            continue                      # Fortsetzung eines mehrzeiligen Texts
        key = treffer.group("key").strip()
        wert = treffer.group("rest")
        spalte = einzug + len(treffer.group("key")) + 2

        if not wert.strip():
            continue                      # verschachtelter Block folgt
        if not wert.startswith(" "):
            continue                      # `key:` ohne Leerzeichen ist kein Mapping
        wert = wert.lstrip(" ")

        if einzug == 0 and not rest_zeile.startswith("-"):
            if key in gesehen:
                # WF-990: BLOCKER, nicht HINWEIS. Hugo bricht an einem
                # doppelten Mapping-Schlüssel den ganzen Bau ab – PyYAML
                # nimmt still den letzten Wert, deshalb sieht der Parser
                # (Schicht 2) den Fall nie. Dieser Scanner ist die einzige
                # Instanz, die ihn vor dem Bau findet.
                befunde.append(Befund(
                    "F3", BLOCKER, pfad, nr, 1,
                    f"Schlüssel `{key}` steht doppelt (zuerst Zeile "
                    f"{gesehen[key]}). Hugo bricht den Bau daran ab "
                    f"(mapping key already defined); ein YAML-Parser nimmt "
                    f"still den letzten Wert und verschweigt den ersten."))
            gesehen.setdefault(key, nr)

        # ---- Wert klassifizieren ----
        if wert.startswith("#"):
            befunde.append(Befund(
                "F6", HINWEIS, pfad, nr, spalte,
                f"`{key}` hat keinen Wert, nur einen Kommentar – der Wert "
                f"ist leer, obwohl die Zeile gefüllt aussieht."))
            continue
        if wert[0] in ("|", ">"):
            if not BLOCK_KOPF.match(wert):
                befunde.append(Befund(
                    "F3", BLOCKER, pfad, nr, spalte,
                    f"Ungültiger Block-Skalar-Kopf `{wert.strip()[:20]}` – "
                    f"erlaubt sind `|`, `>` mit optionalem `-`/`+` oder "
                    f"Ziffer."))
            block_einzug = einzug + len(key) + 2
            continue
        if wert[0] in ('"', "'"):
            schluss = _zitat_schluss(wert)
            if schluss is not None:
                dahinter = wert[schluss + 1:].strip()
                if dahinter and not dahinter.startswith("#"):
                    befunde.append(Befund(
                        "F3", BLOCKER, pfad, nr, spalte + schluss + 2,
                        f"Text hinter dem schließenden Anführungszeichen von "
                        f"`{key}`: „{dahinter[:40]}“. YAML beendet den Wert "
                        f"beim ersten `\"` – steht dort ein deutsches "
                        f"Schlusszeichen als ASCII-Zeichen (`„heilbar\"` "
                        f"statt `„heilbar“`), bricht Hugo ab. Heilung: das "
                        f"schließende Zitat als „ “ schreiben (`--fix`).",
                        heilbar=True))
                    continue
            d, e = _zaehl_quotes(wert)
            if not (d if wert[0] == '"' else e):
                folge = fm.splitlines()[nr - startzeile + 1:]
                wenn_da = _zitat_ende(folge, wert[0])
                if wenn_da is None:
                    befunde.append(Befund(
                        "F3", BLOCKER, pfad, nr, spalte + 1,
                        f"Anführungszeichen in `{key}` wird nie geschlossen "
                        f"– der Rest der Datei wird Text. Hugo meldet "
                        f"„while scanning a quoted scalar\"."))
                else:
                    offene_quote = (wert[0], nr, key)
            continue
        if wert[0] in ("[", "{"):
            if not _flow_geschlossen(wert, wert[0]):
                befunde.append(Befund(
                    "F3", BLOCKER, pfad, nr, spalte,
                    f"Flow-Sammlung in `{key}` ist nicht geschlossen – "
                    f"Hugo meldet „expected ',' or ']'\", wenn die Klammer "
                    f"nirgends zugemacht wird."))
            continue
        if wert[0] == "*":
            name = re.match(r"\*([^\s,\]\}]+)", wert)
            if name and name.group(1) not in anker:
                befunde.append(Befund(
                    "F3", BLOCKER, pfad, nr, spalte,
                    f"`*{name.group(1)}` ist ein Alias auf einen Anker, den "
                    f"diese Datei nirgends setzt (`&{name.group(1)}`) – "
                    f"Hugo bricht mit „found undefined alias\" ab."))
            continue
        if wert[0] == "&":
            anker.update(re.findall(r"&([^\s,\]\}]+)", wert))
            continue
        if wert[0] in RESERVIERT:
            befunde.append(Befund(
                "F3", BLOCKER, pfad, nr, spalte,
                f"`{wert[0]}` ist ein reserviertes YAML-Zeichen und darf "
                f"einen Plain-Skalar nicht beginnen – Wert zitieren."))
            continue

        # ---- Ab hier: echter Plain-Skalar ----
        if ": " in wert or wert.rstrip().endswith(":"):
            stelle = wert.find(": ")
            befunde.append(Befund(
                "F3", BLOCKER, pfad, nr, spalte + max(stelle, 0) + 1,
                f"Doppelpunkt im unquotierten Wert von `{key}`: "
                f"„{wert.strip()[:60]}“. YAML liest danach eine "
                f"Verschachtelung – Hugo bricht ab mit „mapping value is not "
                f"allowed in this context\" (genau der Ausfall vom "
                f"26.10.2026). Heilung: Wert in Anführungszeichen setzen "
                f"(`--fix`).",
                heilbar=True))
            continue
        if " #" in wert:
            vor = wert.split(" #")[0].strip()
            # Ein Kommentar hinter einem Einzelwort (`preload: false  # Bild …`)
            # ist normaler YAML-Stil. Erst wenn davor ein MEHRWORTIGER Text
            # steht, war es Prosa, die jemand mit einem Rautenzeichen beendet
            # hat – dann ist der gespeicherte Wert kürzer als der geschriebene.
            if " " in vor:
                befunde.append(Befund(
                    "F6", HINWEIS, pfad, nr, spalte + wert.index(" #") + 3,
                    f"` #` mitten in `{key}` beginnt einen Kommentar – "
                    f"gespeichert wird nur „{vor[:40]}“. Soll das "
                    f"Rautenzeichen im Text stehen, den Wert zitieren."))
        if key.lower() in YAML11_BOOLE_FELDER and wert.strip().lower() in YAML11_BOOLE:
            befunde.append(Befund(
                "F5", HINWEIS, pfad, nr, spalte,
                f"`{key}: {wert.strip()}` ist für YAML 1.1 ein "
                f"Wahrheitswert, für Hugos Parser (1.2) Text. Zwei Werkzeuge, "
                f"zwei Bedeutungen – zitieren: `{key}: \"{wert.strip()}\"`."))
        if key in DATUM_FELDER and not ISO_DATUM.match(wert.strip()):
            befunde.append(Befund(
                "F4", BLOCKER, pfad, nr, spalte,
                f"`{key}` ist kein ISO-Datum („{wert.strip()[:40]}“) – Hugo "
                f"kann das Feld dann nicht als Datum lesen; Sortierung und "
                f"Sitemap-Lastmod fallen still aus. Erwartet: JJJJ-MM-TT "
                f"oder JJJJ-MM-TTThh:mm:ssZ."))
    return befunde


YAML11_BOOLE_FELDER = tuple(f.lower() for f in TEXT_FELDER)


# ======================================================================
#  Schicht 2: echter Parser (F2, F4)
# ======================================================================
def _yaml_modul():
    try:
        import yaml  # noqa: PLC0415  (optionale Abhängigkeit, siehe Modulkopf)
    except ImportError:  # pragma: no cover - hängt vom Runner ab
        return None
    return yaml


def tiefenpruefung_yaml(fm: str, startzeile: int, pfad: str,
                        yaml=None) -> tuple[list[Befund], bool]:
    """Vollständiger YAML-Parse. Ohne PyYAML: (keine Befunde, False)."""
    yaml = yaml or _yaml_modul()
    if yaml is None:
        return [], False
    befunde: list[Befund] = []
    try:
        daten = yaml.safe_load(fm)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        zeile = startzeile + (mark.line if mark is not None else 0)
        spalte = (mark.column + 1) if mark is not None else 0
        problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        befunde.append(Befund(
            "F2", BLOCKER, pfad, zeile, spalte,
            f"YAML-Parser lehnt das Frontmatter ab: {problem}. Die Datei "
            f"kann so nicht gebaut werden."))
        return befunde, True
    if daten is None:
        return befunde, True
    if not isinstance(daten, dict):
        befunde.append(Befund(
            "F1", BLOCKER, pfad, startzeile, 1,
            f"Frontmatter ist kein Schlüssel-Wert-Block, sondern "
            f"{type(daten).__name__} – Hugo erwartet Felder."))
        return befunde, True
    befunde.extend(_typvertrag(daten, startzeile, pfad))
    return befunde, True


def _typvertrag(daten: dict, startzeile: int, pfad: str) -> list[Befund]:
    befunde: list[Befund] = []
    for feld in TEXT_FELDER:
        if feld not in daten:
            continue
        wert = daten[feld]
        if isinstance(wert, bool) or isinstance(wert, (int, float)):
            befunde.append(Befund(
                "F4", BLOCKER, pfad, startzeile, 1,
                f"`{feld}` ist ein {type(wert).__name__} ({wert!r}), kein "
                f"Text. Hugo schreibt den Wert unverändert ins `<title>` "
                f"bzw. in die Description – zitieren."))
        elif isinstance(wert, (dict, list)):
            befunde.append(Befund(
                "F4", BLOCKER, pfad, startzeile, 1,
                f"`{feld}` ist eine Sammlung ({type(wert).__name__}), kein "
                f"Text – Hugo rendert sie als Map/Liste in die Metazeile."))
    for feld in DATUM_FELDER:
        if feld not in daten:
            continue
        wert = daten[feld]
        if isinstance(wert, (_dt.date, _dt.datetime)):
            continue
        if isinstance(wert, str) and ISO_DATUM.match(wert.strip()):
            continue
        befunde.append(Befund(
            "F4", BLOCKER, pfad, startzeile, 1,
            f"`{feld}` = {wert!r} ist kein lesbares Datum."))
    if "draft" in daten and isinstance(daten["draft"], (dict, list)):
        befunde.append(Befund(
            "F4", BLOCKER, pfad, startzeile, 1,
            "`draft` ist eine Sammlung – Hugo wertet nur Wahrheitswerte."))
    for feld in ("tags", "categories", "keywords"):
        if feld in daten and isinstance(daten[feld], (dict, int, bool)):
            befunde.append(Befund(
                "F4", HINWEIS, pfad, startzeile, 1,
                f"`{feld}` ist {type(daten[feld]).__name__} – erwartet wird "
                f"eine Liste (`[\"a\", \"b\"]`)."))
    return befunde


def tiefenpruefung_toml(fm: str, startzeile: int, pfad: str) -> list[Befund]:
    try:
        import tomllib  # noqa: PLC0415  (Python ≥ 3.11; sonst F2 entfällt)
    except ImportError:  # pragma: no cover
        return []
    try:
        tomllib.loads(fm)
    except Exception as exc:  # tomllib.TOMLDecodeError
        zeile = getattr(exc, "lineno", None) or startzeile
        return [Befund("F2", BLOCKER, pfad, zeile, 0,
                       f"TOML-Parser lehnt das Frontmatter ab: {exc}. "
                       f"Hugo kann die Seite nicht bauen.")]
    return []


def tiefenpruefung_json(fm: str, startzeile: int, pfad: str) -> list[Befund]:
    try:
        daten = json.loads(fm)
    except ValueError as exc:
        return [Befund("F2", BLOCKER, pfad, startzeile, 0,
                       f"JSON-Frontmatter ist kein gültiges JSON: {exc}")]
    if not isinstance(daten, dict):
        return [Befund("F1", BLOCKER, pfad, startzeile, 1,
                       "JSON-Frontmatter ist kein Objekt.")]
    return _typvertrag(daten, startzeile, pfad)


# ======================================================================
#  Eine Datei
# ======================================================================
def pruefe_datei(pfad: Path, text: str, *, anzeige: str | None = None,
                 yaml=None) -> tuple[list[Befund], bool]:
    """(Befunde, Tiefenprüfung aktiv?) für eine Inhaltsdatei."""
    anzeige = anzeige or str(pfad)
    art, fm, start, fehler, _ende = frontmatter_bereich(text)
    if fehler:
        return [Befund("F1", BLOCKER, anzeige, start, 1, fehler)], False
    if not art:
        return [], False
    befunde: list[Befund] = []
    tief = False
    if art == "yaml":
        befunde.extend(scanne_yaml(fm, start, anzeige))
        tiefbefunde, tief = tiefenpruefung_yaml(fm, start, anzeige, yaml=yaml)
        befunde.extend(tiefbefunde)
    elif art == "toml":
        befunde.extend(tiefenpruefung_toml(fm, start, anzeige))
        tief = True
    else:
        befunde.extend(tiefenpruefung_json(fm, start, anzeige))
        tief = True
    return befunde, tief


def _anzeige(pfad: Path) -> str:
    """Pfad relativ zum Repo, wenn er darin liegt – sonst absolut."""
    try:
        return str(pfad.relative_to(ROOT))
    except ValueError:
        return str(pfad)


def sammle_dateien(pfade: list[str]) -> list[tuple[Path, str]]:
    dateien: list[tuple[Path, str]] = []
    for basis in pfade:
        wurzel = (ROOT / basis) if not os.path.isabs(basis) else Path(basis)
        if wurzel.is_file():
            dateien.append((wurzel, _anzeige(wurzel)))
            continue
        for pfad in sorted(wurzel.rglob("*")):
            if pfad.is_file() and pfad.suffix.lower() in INHALT_ENDUNGEN:
                dateien.append((pfad, _anzeige(pfad)))
    return dateien


def run(pfade: list[str]) -> tuple[list[Befund], int, bool]:
    befunde: list[Befund] = []
    dateien = sammle_dateien(pfade)
    tief_irgendwo = False
    for pfad, anzeige in dateien:
        try:
            text = pfad.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            befunde.append(Befund("F1", BLOCKER, anzeige, 1, 0,
                                  f"Datei nicht als UTF-8 lesbar: {exc}"))
            continue
        gefunden, tief = pruefe_datei(pfad, text, anzeige=anzeige)
        tief_irgendwo = tief_irgendwo or tief
        befunde.extend(gefunden)
    return befunde, len(dateien), tief_irgendwo


# ======================================================================
#  Heilung (nur die beweisbare Klasse)
# ======================================================================
def _zitiere(wert: str) -> str:
    """Plain-Skalar als YAML-Doppelpunkt-Zitat – verlustfrei."""
    return json.dumps(wert, ensure_ascii=False)


def heile_datei(pfad: Path, text: str) -> tuple[str, list[Befund]]:
    """Quotet Werte, die am `: ` scheitern. Gibt (neuer Text, Belege) zurück.

    Beweis statt Behauptung: Der eingesetzte Text ist exakt der bisherige
    Plain-Skalar (ohne die Leerzeichen, die YAML ohnehin trimmt). Es wird
    nichts umgeschrieben, nichts gekürzt, nichts umformuliert – nur zitiert.
    """
    art, fm, start, fehler, ende = frontmatter_bereich(text)
    if fehler or art != "yaml" or not fm:
        return text, []
    zeilen = text.splitlines(keepends=True)
    belege: list[Befund] = []
    neu = list(zeilen)
    block_einzug: int | None = None
    i = 0
    while i < len(neu) and i < len(zeilen):
        roh = zeilen[i]
        zeile = roh.rstrip("\r\n")
        nr = i + 1
        if nr < start or (ende and nr >= ende):
            i += 1
            continue
        einzug = len(zeile) - len(zeile.lstrip(" "))
        if block_einzug is not None:
            if einzug > block_einzug:
                i += 1
                continue
            block_einzug = None
        rest = zeile.lstrip(" ")
        if rest.startswith("- "):
            rest = rest[2:]
        treffer = SCHLUESSEL_ZEILE.match(rest)
        if treffer:
            wert = treffer.group("rest")
            if wert.startswith(" ") and wert.strip():
                wert_text = wert.lstrip(" ")
                if wert_text[0] in ("|", ">"):
                    block_einzug = einzug + len(treffer.group("key")) + 2
                elif wert_text[0] == '"':
                    # Deutsches Schlusszeichen als ASCII-Zeichen
                    # (`„heilbar"` statt `„heilbar“`): Das erste `"` beendet
                    # den Wert zu früh. Ersetzt wird GENAU dieses Zeichen –
                    # und nur, wenn danach der Wert sauber schließt.
                    schluss = _zitat_schluss(wert_text)
                    if schluss is not None:
                        dahinter = wert_text[schluss + 1:].strip()
                        if (dahinter and not dahinter.startswith("#")
                                and "\u201e" in wert_text[:schluss]):
                            repariert = (wert_text[:schluss] + "\u201c"
                                         + wert_text[schluss + 1:])
                            neu_schluss = _zitat_schluss(repariert)
                            rest = (repariert[neu_schluss + 1:].strip()
                                    if neu_schluss is not None else "x")
                            if neu_schluss is not None and (not rest or rest.startswith("#")):
                                neu[i] = (zeile[:len(zeile) - len(wert_text)]
                                          + repariert + "\n")
                                belege.append(Befund(
                                    "F3", BLOCKER, str(pfad), nr, 1,
                                    f"deutsches Schlusszeichen ersetzt: "
                                    f"`{treffer.group('key').strip()}` – Text "
                                    f"unverändert übernommen"))
                elif wert_text[0] not in ("'", "[", "{", "#", "*", "&"):
                    if ": " in wert_text or wert_text.rstrip().endswith(":"):
                        neu[i] = (zeile[:len(zeile) - len(wert_text)]
                                  + _zitiere(wert_text.rstrip()) + "\n")
                        belege.append(Befund(
                            "F3", BLOCKER, str(pfad), nr, 1,
                            f"zitiert: `{treffer.group('key').strip()}` – "
                            f"Wert unverändert übernommen"))
        i += 1
    return "".join(neu), belege


def heile(pfade: list[str], *, schreiben: bool = True) -> list[Befund]:
    belege: list[Befund] = []
    for pfad, anzeige in sammle_dateien(pfade):
        try:
            text = pfad.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        neuer_text, datei_belege = heile_datei(pfad, text)
        if neuer_text == text:
            continue
        for beleg in datei_belege:
            beleg["pfad"] = anzeige
        belege.extend(datei_belege)
        if schreiben:
            tmp = pfad.with_suffix(pfad.suffix + ".tmp")
            tmp.write_text(neuer_text, encoding="utf-8")
            os.replace(tmp, pfad)
    return belege


# ======================================================================
#  Ausgabe
# ======================================================================
def _sortiert(befunde: list[Befund]) -> list[Befund]:
    return sorted(befunde, key=lambda b: (b["pfad"], b["zeile"], b["spalte"],
                                          b["regel"]))


def bericht_json(befunde: list[Befund], dateien: int, tief: bool) -> str:
    return json.dumps({
        "dateien": dateien,
        "tiefenpruefung": "yaml-parser" if tief else "scanner",
        "blocker": sum(1 for b in befunde if b["schwere"] == BLOCKER),
        "hinweise": sum(1 for b in befunde if b["schwere"] == HINWEIS),
        "befunde": _sortiert(befunde),
    }, ensure_ascii=False, indent=1)


def bericht_md(befunde: list[Befund], dateien: int, tief: bool) -> str:
    zeilen = ["### 🧾 Frontmatter-Vertrag (vor dem Bau)", ""]
    blocker = [b for b in befunde if b["schwere"] == BLOCKER]
    hinweise = [b for b in befunde if b["schwere"] == HINWEIS]
    zeilen.append(f"**{dateien} Inhaltsdateien** geprüft · "
                  f"**{len(blocker)} Blocker** · **{len(hinweise)} Hinweise** · "
                  f"Tiefenprüfung: "
                  f"{'YAML-Parser + Scanner' if tief else 'Scanner (kein PyYAML im Runner)'}")
    if blocker:
        zeilen += ["", "| Datei:Zeile | Regel | Befund |", "|---|---|---|"]
        for b in blocker[:40]:
            meldung = b["meldung"].replace("|", "\\|").replace("\n", " ")
            zeilen.append(f"| `{b['pfad']}:{b['zeile']}` | {b['regel']} | {meldung} |")
        if len(blocker) > 40:
            zeilen.append(f"| … | | {len(blocker) - 40} weitere Blocker |")
        zeilen += ["", "Heilung der zitierten Klasse: "
                       "`python3 scripts/frontmatter_wache.py --fix`"]
    if hinweise:
        zeilen += ["", f"<details><summary>{len(hinweise)} Hinweise "
                       f"(bauen, sind aber stille Fallen)</summary>", ""]
        for b in hinweise[:40]:
            zeilen.append(f"- `{b['pfad']}:{b['zeile']}` ({b['regel']}): "
                          f"{b['meldung']}")
        zeilen += ["", "</details>"]
    return "\n".join(zeilen) + "\n"


# ======================================================================
#  Selbsttest
# ======================================================================
_GUT = """---
title: "Strom sparen im Alltag"
description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."
date: 2026-10-14T14:57:58Z
draft: false
tags: ["Strom sparen", "Tarife"]
quellen:
  - titel: "Bundesnetzagentur"
    url: "https://example.org/a?b=1"
---

Annahme: Die Anlage kostet 500 Euro. Rechenbeispiel: 600 kWh mal 0,35 Euro.
"""

# Der Originalzustand vom 26.10.2026, Zeile 2 der Datei.
_KAPUTT_2610 = _GUT.replace(
    'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
    "description: Stromkosten senken: Balkonkraftwerk-Förderung regional – "
    "Antrag und Anmeldung")


def run_selftest() -> int:
    yaml = _yaml_modul()
    faelle: list[tuple[str, str, list[str]]] = []

    def erwartet(text: str) -> list[str]:
        befunde, _ = pruefe_datei(Path("content/x/index.md"), text, yaml=yaml)
        return sorted({b["regel"] for b in befunde})

    def blocker(text: str) -> list[str]:
        befunde, _ = pruefe_datei(Path("content/x/index.md"), text, yaml=yaml)
        return sorted({b["regel"] for b in befunde if b["schwere"] == BLOCKER})

    # 1) Der Ausfall selbst: unquotierter Doppelpunkt.
    faelle.append(("26.10.2026 – Doppelpunkt im Plain-Skalar", _KAPUTT_2610, ["F3"]))
    # 2) Wert endet auf einem Doppelpunkt.
    faelle.append(("Wert endet auf ':'", _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        "description: So sparst du:"), ["F3"]))
    # 3) Saubere Fassung: genau ein Befund darf NICHT entstehen.
    faelle.append(("sauberes Frontmatter", _GUT, []))
    # 4) Doppelpunkt im Zitat ist Text, kein Fehler.
    faelle.append(("zitierter Doppelpunkt", _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        'description: "Strom sparen: Tarife vergleichen und Abschläge planen, '
        'mit Rechenbeispielen für jeden Haushalt."'), []))
    # 5) URL mit Doppelpunkt (Schema) bleibt erlaubt.
    faelle.append(("URL im Wert", _GUT.replace(
        'url: "https://example.org/a?b=1"', "url: https://example.org/a?b=1"), []))
    # 6) Block-Skalar darf Doppelpunkte enthalten.
    faelle.append(("Block-Skalar mit Doppelpunkt", _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        "description: |\n  Strom sparen: Tarife vergleichen"), []))
    # 7) Offenes Frontmatter.
    faelle.append(("Frontmatter nie geschlossen", _GUT.replace(
        "\n---\n\nAnnahme:", "\n\nAnnahme:"), ["F1"]))
    # 8) Unbalanciertes Zitat. Zwei Fassungen, weil sie zwei Schichten
    #    prüfen: ohne jedes Zitatende sieht es schon der Scanner (F3), mit
    #    einem Zitat in einer Folgezeile entscheidet erst der Parser (F2).
    faelle.append(("Anführungszeichen nirgends geschlossen",
                   '---\ntitle: "Offen\n---\n\nText.\n', ["F3"]))
    if yaml is not None:
        faelle.append(("Zitat läuft in die nächste Zeile", _GUT.replace(
            'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
            'description: "Stromfresser finden'), ["F2"]))
    # 9) Nicht geschlossene Flow-Sammlung.
    faelle.append(("Flow-Liste offen", _GUT.replace(
        'tags: ["Strom sparen", "Tarife"]', 'tags: ["Strom sparen", "Tarife"'), ["F3"]))
    # 10) Tabulator in der Einrückung.
    faelle.append(("Tabulator-Einrückung", _GUT.replace(
        "  - titel: \"Bundesnetzagentur\"", "\t- titel: \"Bundesnetzagentur\""), ["F3"]))
    # 11) Unbekannter Alias.
    faelle.append(("unbekannter Alias", _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        "description: *unbekannt"), ["F3"]))
    # 12) Doppelter Schlüssel.
    faelle.append(("doppelter Schlüssel", _GUT.replace(
        "draft: false", "draft: false\ndraft: true"), ["F3"]))
    # 13) Kommentar schneidet den Wert ab.
    faelle.append(("Kommentar im Wert", _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        "description: Strom sparen # und Tarife"), ["F6"]))
    # 14) YAML-1.1-Wahrheitswert als Text.
    faelle.append(("yes als Titel", _GUT.replace(
        'title: "Strom sparen im Alltag"', "title: yes"), ["F5"]))
    # 15) Datum, das Hugo nicht lesen kann.
    faelle.append(("Datum als Text", _GUT.replace(
        "date: 2026-10-14T14:57:58Z", "date: 14.10.2026"), ["F4"]))
    # 16) TOML-Frontmatter kaputt.
    faelle.append(("TOML kaputt", "+++\ntitle = \"x\"\ndate = \n+++\n\nText.\n", ["F2"]))
    # 17) JSON-Frontmatter kaputt.
    faelle.append(("JSON kaputt", '{"title": "x",}\n\nText.\n', ["F1"]))
    # 18b) Deutsches Schlusszeichen als ASCII-Zeichen im Zitat – die Klasse,
    #      die am 29.10.2026 auf `main` stand (`„heilbar"` statt `„heilbar“`).
    #      Das erste `"` beendet den Wert zu früh; ein Parser sieht es, der
    #      Scanner muss es auch sehen (die Build-Action läuft ohne PyYAML).
    faelle.append(("ASCII-Schlusszeichen im Zitat", _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        'description: "Klasse \u201eheilbar" ist heilbar, mit Wirkungsnachweis."'),
        ["F3"]))
    # 18) Sequenz-Eintrag mit Doppelpunkt im Zitat bleibt sauber.
    faelle.append(("Sequenz mit zitiertem Doppelpunkt", _GUT.replace(
        'titel: "Bundesnetzagentur"', 'titel: "Netzagentur: Marktstammdaten"'), []))

    fehler: list[str] = []
    for name, text, soll in faelle:
        ist = erwartet(text)
        # Geprüft wird ZWEI Dinge: die erwartete Regel MUSS greifen – und
        # eine saubere Datei darf keinen BLOCKER erzeugen (keine Fehlalarme;
        # HINWEISE sind dort erlaubt und werden eigens geprüft).
        fehlend = [r for r in soll if r not in ist]
        if fehlend:
            fehler.append(f"{name}: Regel(n) {fehlend} fehlen, bekommen {ist}")
        if not soll and blocker(text):
            fehler.append(f"{name}: Fehlalarm – Blocker {blocker(text)} auf "
                          f"sauberem Frontmatter")

    # Die Heilung muss den Wert exakt erhalten – nicht bloß den Fehler beheben.
    geheilt, belege = heile_datei(Path("content/x/index.md"), _KAPUTT_2610)
    if not belege:
        fehler.append("Heilung: 26.10.2026-Datei wurde nicht repariert")
    elif erwartet(geheilt):
        fehler.append(f"Heilung: danach noch Befunde {erwartet(geheilt)}")
    else:
        soll_wert = ("Stromkosten senken: Balkonkraftwerk-Förderung regional – "
                     "Antrag und Anmeldung")
        if yaml is not None:
            _, fm, _, _, _ = frontmatter_bereich(geheilt)
            if (yaml.safe_load(fm) or {}).get("description") != soll_wert:
                fehler.append("Heilung: Wert wurde verändert (Beweis verletzt)")
        if f'description: "{soll_wert}"' not in geheilt:
            fehler.append("Heilung: erwartetes Zitat fehlt im Text")
    # Heilung des deutschen Schlusszeichens: Zitat wird korrekt, Text bleibt.
    ascii_fall = _GUT.replace(
        'description: "Stromfresser finden, Tarife vergleichen und Abschläge planen."',
        'description: "Klasse \u201eheilbar" ist heilbar, mit Wirkungsnachweis."')
    geheilt_de, belege_de = heile_datei(Path("content/x/index.md"), ascii_fall)
    soll_de = "Klasse \u201eheilbar\u201c ist heilbar, mit Wirkungsnachweis."
    if not belege_de:
        fehler.append("Heilung: deutsches Schlusszeichen wurde nicht ersetzt")
    elif f'description: "{soll_de}"' not in geheilt_de:
        fehler.append(f"Heilung: deutsches Schlusszeichen falsch repariert: "
                      f"{[z for z in geheilt_de.splitlines() if 'description' in z]}")
    elif erwartet(geheilt_de):
        fehler.append(f"Heilung: danach noch Befunde {erwartet(geheilt_de)}")

    # Heilung darf den FLIESSTEXT nicht anfassen – auch nicht, wenn dort
    # Zeilen wie `Annahme: …` stehen (Regression der Generalprobe 29.10.2026).
    if "Annahme: Die Anlage kostet 500 Euro." not in geheilt:
        fehler.append("Heilung: Fließtext wurde verändert (Kolons im Body "
                      "dürfen nie zitiert werden)")
    # Heilung darf saubere Dateien nicht anfassen.
    unveraendert, belege_sauber = heile_datei(Path("content/x/index.md"), _GUT)
    if unveraendert != _GUT or belege_sauber:
        fehler.append("Heilung: saubere Datei wurde verändert")

    if fehler:
        print("🛑 Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ Selbsttest: {len(faelle) + 2} Proben bestanden – Wache ist "
          f"scharf (Tiefenprüfung: "
          f"{'YAML-Parser' if yaml is not None else 'Scanner'}).")
    return 0


# ======================================================================
#  CLI
# ======================================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prüft das Frontmatter aller Inhaltsdateien vor dem Bau.")
    parser.add_argument("--pfad", action="append", default=None,
                        help=f"Pfad oder Datei (mehrfach möglich, Standard: {STANDARD_PFAD})")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON")
    parser.add_argument("--md", action="store_true", help="Markdown-Bericht nach stdout")
    parser.add_argument("--md-datei", metavar="PFAD", help="Markdown-Bericht in Datei")
    parser.add_argument("--kurzbefund", action="store_true",
                        help="nur die erste Blocker-Zeile (für Annotationen)")
    parser.add_argument("--fix", action="store_true",
                        help="heilt unquotierte Doppelpunkte (beweisbar verlustfrei)")
    parser.add_argument("--streng", action="store_true",
                        help="HINWEISE zählen als Befund (Exit 1)")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    pfade = args.pfad or [STANDARD_PFAD]

    if args.fix:
        belege = heile(pfade)
        for beleg in belege:
            print(f"  🔧 {beleg['pfad']}:{beleg['zeile']} – {beleg['meldung']}")
        print(f"Frontmatter-Heilung: {len(belege)} Wert(e) zitiert.")
        if not belege:
            print("Nichts zu heilen – die Klasse „Doppelpunkt im Plain-Skalar\" "
                  "kommt im Bestand nicht vor.")

    befunde, dateien, tief = run(pfade)
    blocker = [b for b in befunde if b["schwere"] == BLOCKER]
    hinweise = [b for b in befunde if b["schwere"] == HINWEIS]
    rot = bool(blocker) or (args.streng and bool(hinweise))

    if args.md_datei:
        Path(args.md_datei).write_text(bericht_md(befunde, dateien, tief),
                                       encoding="utf-8")
    if args.kurzbefund:
        print(blocker[0].kurz() if blocker else "")
        return 1 if rot else 0
    if args.json:
        print(bericht_json(befunde, dateien, tief))
        return 1 if rot else 0
    if args.md:
        print(bericht_md(befunde, dateien, tief))
        return 1 if rot else 0

    for b in _sortiert(befunde):
        zeichen = "✗" if b["schwere"] == BLOCKER else "!"
        print(f"  {zeichen} [{b['regel']}] {b['pfad']}:{b['zeile']}"
              f"{':' + str(b['spalte']) if b['spalte'] else ''} – {b['meldung']}")
    print(f"Frontmatter-Wache: {dateien} Dateien | Blocker: {len(blocker)} | "
          f"Hinweise: {len(hinweise)} | Tiefenprüfung: "
          f"{'YAML-Parser' if tief else 'Scanner'}")
    if blocker:
        # WF-990: Ein Duplikat ist NICHT von --fix heilbar, und die alte
        # Zeile behauptete genau das. Ein Reparaturhinweis, der ins Leere
        # führt, ist schlimmer als keiner – er erzieht zum Wegsehen.
        doppelt = [b for b in blocker if "steht doppelt" in b["meldung"]]
        if doppelt:
            print(f"ACHTUNG: {len(doppelt)} Blocker sind doppelte Schlüssel – "
                  "die kann --fix NICHT heilen. Es fehlt eine Angabe, und nur "
                  "ein Mensch entscheidet, welche gilt (die Beschreibung gilt "
                  "dort, wo sie inhaltlich richtig ist, nicht die letzte).")
        if len(doppelt) < len(blocker):
            print("Heilung: python3 scripts/frontmatter_wache.py --fix "
                  "(zitiert die betroffenen Werte, ohne den Text zu ändern)")
    return 1 if rot else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
