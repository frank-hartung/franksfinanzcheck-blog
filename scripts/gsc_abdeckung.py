#!/usr/bin/env python3
"""gsc_abdeckung.py – die Abdeckungs-Zentrale der Search Console.

WARUM DIESES MODUL EXISTIERT (Auftrag 26.10.2026: „Google Search Console auf
Highend-Niveau einer Profi-Agentur")
---------------------------------------------------------------------------
Das Projekt hatte bis heute zwei Search-Console-Schichten:

  * `scripts/gsc_import.py`       – Leistungsdaten (Klicks, Impressionen) per API
  * `scripts/gsc_indexierung.py`  – Indexierung anfragen / Status je URL

Was fehlte, ist das Stück, das in einer Agentur jeden Montag auf dem Tisch
liegt: der **Abdeckungsbericht** („Seiten“/Page Indexing) – die Frage, WARUM
eine URL nicht im Index ist, wie sich das über die Zeit entwickelt und welche
der gemeldeten Zahlen überhaupt zum eigenen Bestand passen.

Der Bericht ist die einzige Wahrheit über den Index, und er hat eine unangenehme
Eigenschaft: **Google stellt für ihn keine API bereit.** Man bekommt ihn nur als
CSV-Export aus der Oberfläche. Genau darum lagen die Zahlen bisher als
Bildschirmfoto vor und nicht als messbare Größe: Am 19.10.2026 meldete die
Search Console 320 nicht indexierte und 117 indexierte Seiten – bei rund 94
indexierbaren Seiten im Build. Diese Zahl stand nirgends im Repo, und niemand
konnte sie gegen den eigenen Bestand rechnen.

Dieses Modul schließt die Lücke auf drei Ebenen:

  1. EINLESEN (`--import`)
     Die vier Exporte des Abdeckungsberichts (Übersicht, Diagramm, Metadaten,
     optionale Detail-Listen) werden tolerant gelesen – Trennzeichen, BOM,
     Tausenderpunkte und deutsche Anführungszeichen inklusive – und auf
     Widersprüche geprüft, BEVOR sie zu einem Artefakt werden. Die Lehre vom
     21.10.2026 (`GSC-DATEN-INTEGRITAET-HIGHEND`) gilt auch hier: Wer schreibt,
     muss belegen, dass das Geschriebene in sich stimmt.

  2. GEGENRECHNEN (`--audit`)
     Jede gemeldete Zahl bekommt eine Erwartung aus dem Repo: die fünf
     noindex-Seiten aus `robotsNoIndex: true`, die /go/-Gateways aus `static/go/`,
     die Weiterleitungs-Quellen aus `data/weiterleitungen.yaml`, die
     Taxonomie-Fläche aus den Tags der Inhalte, die indexierbaren Seiten aus
     Sitemap bzw. `content/`. Daraus entsteht je Grund ein Urteil:
     „vollständig erklärt“, „plausibel“, „offen“ oder „unklar“ – mit der Zahl,
     die offen bleibt. Eine Zahl ohne Gegenprobe ist eine Behauptung.

  3. HANDELN (`--plan`)
     Aus den offenen Posten wird eine priorisierte Maßnahmenliste (P1–P3,
     Aufwand, erwartete Wirkung, Beleg, Eigentümer: Mensch oder Automat). Kein
     Vorschlag ohne Zahl, keine Zahl ohne Quelle.

WAS DAS MODUL AUSDRÜCKLICH NICHT TUT
  * Es erfindet keine URL. Fehlt die Detail-Liste, steht das als offene
    Beweisfrage im Befund – nicht als geschätzte Zahl in der Tabelle.
  * Es schreibt nie in `data/weiterleitungen.yaml` oder
    `data/url_entfallen.yaml`. Weiterleitungen sind eine Entscheidung mit
    Suchabsicht (Regeln A–E, siehe Dateikopf dort), kein Automatismus.
  * Es ruft keine Suchmaschine auf. Alles ist offline und deterministisch –
    der Befund ist reproduzierbar, auch in einem Jahr.

AUFRUF
    # 1) Export aus der Search Console einlesen (Verzeichnis mit den CSVs)
    python3 scripts/gsc_abdeckung.py --import ~/Downloads/search-console

    # 2) Gegen den eigenen Bestand rechnen (kein Netz)
    python3 scripts/gsc_abdeckung.py --audit
    python3 scripts/gsc_abdeckung.py --audit --json     # maschinenlesbar
    python3 scripts/gsc_abdeckung.py --audit --md       # Markdown für die Lauf-Zusammenfassung

    # 3) Tor für den Tageslauf: bricht bei Rückschritt oder Widerspruch
    python3 scripts/gsc_abdeckung.py --gate

    # 4) Aus einer 404-Detail-Liste Weiterleitungs-Vorschläge ableiten
    python3 scripts/gsc_abdeckung.py --vorschlaege details/"Nicht gefunden (404).csv"

    python3 scripts/gsc_abdeckung.py --selftest         # 78 Fälle, offline

WO DIE EXPORTE HERKOMMEN
    Search Console → Indexierung → Seiten → oben rechts „Exportieren“.
    Vier Dateien: Übersicht, Diagramm, Metadaten und – je Fehlergrund – eine
    Detail-Liste („Nicht gefunden (404).csv“ usw.). Die Detail-Listen sind der
    einzige Weg zu den betroffenen URLs; ohne sie bleibt jede Ursachenanalyse
    bei der Summe stehen. Runbook: docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md §5.

ARTEFAKTE
    data/gsc/abdeckung/<datum>.json     Momentaufnahme des Exports (ein Lauf = eine Messung)
    data/gsc/abdeckung/aktuell.json     dieselbe Momentaufnahme, fester Pfad für Leser
    data/gsc/abdeckung/verlauf.jsonl    eine Zeile je Momentaufnahme (append-only)
    data/gsc/abdeckung/befund.json      Ergebnis der Gegenrechnung (maschinenlesbar)
    data/gsc/abdeckung/befund.md        derselbe Befund als Bericht

EXIT: 0 = grün · 1 = Befund (Gate rot oder Export widersprüchlich) · 2 = Werkzeugfehler
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ABDECKUNG = ROOT / "data" / "gsc" / "abdeckung"
AKTUELL = ABDECKUNG / "aktuell.json"
VERLAUF = ABDECKUNG / "verlauf.jsonl"
BEFUND = ABDECKUNG / "befund.json"
REPORT = ABDECKUNG / "befund.md"
TOP_SEITEN = ROOT / "data" / "gsc" / "top_seiten_28t.json"
WEITERLEITUNGEN = ROOT / "data" / "weiterleitungen.yaml"
ENTFALLEN = ROOT / "data" / "url_entfallen.yaml"
PUBLIC_SITEMAP = ROOT / "public" / "sitemap.xml"
ROBOTS_QUELLEN = (ROOT / "public" / "robots.txt", ROOT / "layouts" / "robots.txt")
# Haus-Konvention mit index_hygiene_gate.py: wer ein anderes Build-Verzeichnis
# prüft, sagt das über INDEX_GATE_BASE – nicht über einen zweiten Parameternamen.
UMGEBUNG_BASIS = "INDEX_GATE_BASE"
GATEWAYS = ROOT / "static" / "go"

SCHEMA = 1
# Google-Kontingent der URL Inspection API je Property und Tag. Dieselbe Zahl
# führt `gsc_indexierung.py` – hier nur für die Kapazitätsrechnung der Wellen.
ANFRAGEN_PRO_TAG = 200
# Hubs und Rechtsseiten werden über Navigation verlinkt – ein fehlender
# redaktioneller Inlink ist dort kein Befund.
HUBS = ("/", "/posts/", "/pillar/", "/werkzeuge/", "/studien/")
# Kanonische Domain für absolute URLs (URL-Inspection-API will sie absolut).
SITE = "https://franksfinanzcheck.de"

# --------------------------------------------------------------------------
#  Grund-Katalog
# --------------------------------------------------------------------------
# Googles Gründe heißen in der Oberfläche deutsch und ändern ihren Wortlaut
# gelegentlich („Gefunden – zurzeit nicht indexiert“, „Gefunden, zurzeit nicht
# indexiert“). Verglichen wird deshalb auf einem normalisierten Kürzel, nicht
# auf dem abgeschriebenen Satz. Jeder Grund bekommt eine Klasse, weil er eine
# andere Antwort verlangt:
#
#   technik  – eine Entscheidung der Site (noindex, robots, canonical, 5xx)
#   historie – eine URL, die es nicht mehr gibt (404, soft 404)
#   inhalt   – Google hat gesehen und (noch) nicht aufgenommen
#   unbekannt– Google hat einen Grund ergänzt, den dieses Modul nicht kennt
#
# „unbekannt“ ist ein HARTES Gate-Kriterium: Ein neuer Grund in der Search
# Console ist eine Nachricht, keine Randnotiz.
GRUND_KATALOG = {
    "not_found": {
        "titel": "Nicht gefunden (404)",
        "klasse": "historie",
        "bedeutung": ("Die URL wurde aufgerufen und existiert nicht. Für Nutzer "
                      "harmlos, für Suchmaschinen ein Signal: Die Seite ist weg. "
                      "Handlungsbedarf entsteht nur dort, wo die URL noch Nachfrage "
                      "hat (Impressionen, Backlinks, interne Links)."),
    },
    "soft_404": {
        "titel": "Soft 404",
        "klasse": "historie",
        "bedeutung": ("Die URL antwortet mit 200, wirkt aber leer. Fast immer ein "
                      "Zeichen für eine Seite ohne Inhalt – nicht für einen Serverfehler."),
    },
    "noindex": {
        "titel": "Durch „noindex“-Tag ausgeschlossen",
        "klasse": "technik",
        "bedeutung": ("Die Seite sagt selbst, dass sie nicht in den Index gehört. "
                      "Richtig für Suche, Newsletter-Funnel und Gateways – falsch, "
                      "wenn ein Artikel betroffen ist."),
    },
    "robots_blocked": {
        "titel": "Durch robots.txt-Datei blockiert",
        "klasse": "technik",
        "bedeutung": ("Google darf die URL nicht abrufen. Gewollt für "
                      "/go/-Affiliate-Gateways; ein Defekt, sobald eine Inhaltsseite "
                      "betroffen ist. Solange gesperrt, kann Google ein noindex "
                      "nicht lesen – die Meldung bleibt dauerhaft stehen."),
    },
    "redirect": {
        "titel": "Seite mit Weiterleitung",
        "klasse": "technik",
        "bedeutung": ("Die URL leitet weiter (HTTP oder Meta-Refresh). GitHub Pages "
                      "kann keine echten 301 setzen; das Repo liefert deshalb "
                      "Weiterleitungsseiten mit noindex und Canonical aus."),
    },
    "alternate_canonical": {
        "titel": "Alternative Seite mit ordnungsgemäßem Canonical-Tag",
        "klasse": "technik",
        "bedeutung": ("Google hat die kanonische Fassung gefunden und die Dublette "
                      "stillgelegt. Kein Fehler – solange das Canonical das richtige "
                      "Ziel nennt."),
    },
    "duplicate_canonical": {
        "titel": "Duplikat ohne vom Nutzer gewähltes Canonical",
        "klasse": "inhalt",
        "bedeutung": ("Google wählt selbst eine andere Fassung. Ursache sind meist "
                      "zwei Seiten mit gleicher Suchabsicht oder ein fehlendes "
                      "Canonical."),
    },
    "crawled_not_indexed": {
        "titel": "Gecrawlt – zurzeit nicht indexiert",
        "klasse": "inhalt",
        "bedeutung": ("Google hat die Seite gelesen und sich gegen den Index "
                      "entschieden. Technisch ist alles in Ordnung; es fehlt an "
                      "Substanz, Einzigartigkeit oder Nachfrage. Redaktionelles "
                      "Signal, kein Technikdefekt."),
    },
    "discovered_not_indexed": {
        "titel": "Gefunden – zurzeit nicht indexiert",
        "klasse": "inhalt",
        "bedeutung": ("Google kennt die URL aus der Sitemap oder einem Link, hat sie "
                      "aber noch nicht abgerufen. Das ist eine Frage des Crawl-Budgets "
                      "und der Autorität, nicht der Auszeichnung."),
    },
    "server_error": {
        "titel": "Serverfehler (5xx)",
        "klasse": "technik",
        "bedeutung": "Der Server hat nicht geantwortet. Harte technische Störung.",
    },
    "redirect_error": {
        "titel": "Weiterleitungsfehler",
        "klasse": "technik",
        "bedeutung": ("Kette oder Schleife: Das Ziel leitet erneut weiter oder "
                      "verweist auf sich selbst."),
    },
    "unknown": {
        "titel": "Unbekannter Grund",
        "klasse": "unbekannt",
        "bedeutung": ("Diesen Grund kennt das Modul nicht. Entweder hat Google "
                      "einen neuen Zustand eingeführt oder der Export wurde "
                      "verändert – beides muss ein Mensch ansehen."),
    },
}

# Reihenfolge der Prüfung: spezifisch vor allgemein („noindex“ steckt sonst in
# „Durch robots.txt blockiert“ nicht, aber „Weiterleitung“ steckt in
# „Weiterleitungsfehler“ – deshalb erst die Fehlerklasse prüfen).
_MUSTER = (
    ("server_error", ("serverfehler", "5xx", "server error")),
    ("redirect_error", ("weiterleitungsfehler", "umleitungsfehler", "redirect error")),
    ("duplicate_canonical", ("duplikat", "duplicate")),
    ("alternate_canonical", ("alternative seite", "alternate page")),
    ("redirect", ("seite mit weiterleitung", "seite mit umleitung", "weiterleitung")),
    ("robots_blocked", ("robots.txt", "robots")),
    ("noindex", ("noindex",)),
    ("soft_404", ("soft 404", "soft-404")),
    ("not_found", ("nicht gefunden", "not found", "404")),
    ("crawled_not_indexed", ("gecrawlt", "crawled")),
    ("discovered_not_indexed", ("gefunden", "discovered")),
)


def normalisiere(text: str) -> str:
    """Kleinschreibung, Umlaute/ß aufgelöst, Striche vereinheitlicht, Leerraum flach."""
    t = unicodedata.normalize("NFKD", (text or "").strip().lower())
    t = t.replace("ß", "ss").replace("ä", "a").replace("ö", "o").replace("ü", "u")
    t = re.sub(r"[\u2010-\u2015\u2212]", "-", t)
    t = re.sub(r"[\"'`´‚‘’‚“”„“”]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def klassifiziere(grund: str) -> str:
    """GSC-Grund → Schlüssel aus GRUND_KATALOG. Nie leer, notfalls 'unknown'."""
    n = normalisiere(grund)
    for schluessel, nadeln in _MUSTER:
        if any(nadel in n for nadel in nadeln):
            return schluessel
    return "unknown"


def zahl(wert) -> int | None:
    """'1.234' → 1234, '' → None. Tausenderpunkte und Leerzeichen sind erlaubt,
    weil der deutsche Export sie liefert."""
    if wert is None:
        return None
    roh = str(wert).strip().replace("\u00a0", " ").replace(".", "").replace(" ", "")
    if roh in ("", "-", "–", "—"):
        return None
    if not re.fullmatch(r"-?\d+", roh):
        return None
    return int(roh)


def prozent(teil: int | float, ganzes: int | float) -> float:
    return round((teil / ganzes) * 100, 1) if ganzes else 0.0


# --------------------------------------------------------------------------
#  CSV lesen – tolerant, aber nicht blind
# --------------------------------------------------------------------------

def lese_csv(pfad: Path) -> list[dict]:
    """Liest eine GSC-CSV. Trennzeichen wird erkannt, nicht angenommen.

    Der Export kommt je nach Konto/Locale mit Komma, Semikolon oder Tabulator,
    mit BOM und mit Anführungszeichen um Felder, die selbst Anführungszeichen
    enthalten („Durch ""noindex""-Tag ausgeschlossen“). `csv.Sniffer` rät nur die
    Dialektmerkmale – die Struktur prüft der Aufrufer.
    """
    roh = Path(pfad).read_bytes()
    for kodierung in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = roh.decode(kodierung)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - praktisch unerreichbar
        raise ValueError(f"{pfad}: Kodierung nicht lesbar")

    zeilen = [z for z in text.splitlines() if z.strip()]
    if not zeilen:
        return []
    probe = "\n".join(zeilen[:20])
    try:
        dialekt = csv.Sniffer().sniff(probe, delimiters=",;\t")
        trenner = dialekt.delimiter
    except csv.Error:
        # Mehr Kommas als Semikolons? Dann ist es Komma. Sonst Semikolon.
        trenner = "," if probe.count(",") >= probe.count(";") else ";"

    leser = csv.DictReader(io.StringIO(text), delimiter=trenner)
    out: list[dict] = []
    for zeile in leser:
        sauber = {}
        for schluessel, wert in zeile.items():
            if schluessel is None:
                continue
            sauber[(schluessel or "").strip().lstrip("\ufeff")] = (wert or "").strip()
        # Leerzeilen am Ende erzeugen {'Grund': ''} – die sind kein Datensatz.
        if any(v for v in sauber.values()):
            out.append(sauber)
    return out


def _spalte(zeile: dict, *kandidaten: str) -> str | None:
    """Erste passende Spalte – Vergleich normalisiert (Groß/klein, Umlaute)."""
    index = {normalisiere(k): k for k in zeile}
    for kand in kandidaten:
        treffer = index.get(normalisiere(kand))
        if treffer is not None:
            return zeile.get(treffer, "")
    return None


def erkenne_art(zeilen: list[dict]) -> str:
    """Welcher der vier Exporte liegt vor? Erkannt am Kopf, nicht am Dateinamen.

    Dateinamen sind bei Exporten aus der Oberfläche beliebig („Export (3).csv“).
    Ein Verfahren, das am Namen hängt, bricht beim ersten umbenannten Download.
    """
    if not zeilen:
        return "leer"
    spalten = {normalisiere(k) for k in zeilen[0]}
    if {"datum"} & spalten:
        return "verlauf"
    if {"grund", "seiten"} <= spalten:
        return "uebersicht"
    if {"property"} & spalten and len(spalten) <= 3:
        return "metadaten"
    if {"url"} & spalten or {"seite"} & spalten:
        return "details"
    return "unbekannt"


def lade_export(pfad: Path) -> dict:
    """Liest ein Verzeichnis (alle CSVs) oder eine einzelne Datei."""
    pfad = Path(pfad)
    dateien = sorted(p for p in pfad.glob("*.csv")) if pfad.is_dir() else [pfad]
    if not dateien:
        raise FileNotFoundError(f"Keine CSV in {pfad}")
    export = {
        "quelle": str(pfad),
        "dateien": [],
        "uebersicht": [],
        "verlauf": [],
        "metadaten": {},
        "details": [],
        "unbekannt": [],
    }
    for datei in dateien:
        zeilen = lese_csv(datei)
        art = erkenne_art(zeilen)
        export["dateien"].append({"datei": datei.name, "art": art, "zeilen": len(zeilen)})
        if art == "uebersicht":
            for z in zeilen:
                export["uebersicht"].append({
                    "grund": (_spalte(z, "Grund") or "").strip(),
                    "quelle": (_spalte(z, "Quelle") or "").strip(),
                    "validierung": (_spalte(z, "Validierung") or "").strip(),
                    "seiten": zahl(_spalte(z, "Seiten")),
                })
        elif art == "verlauf":
            for z in zeilen:
                datum = (_spalte(z, "Datum") or "").strip()
                export["verlauf"].append({
                    "datum": datum,
                    "nicht_indexiert": zahl(_spalte(z, "Nicht indexiert")),
                    "indexiert": zahl(_spalte(z, "Indexiert")),
                    "impressionen": zahl(_spalte(z, "Impressionen")),
                })
        elif art == "metadaten":
            for z in zeilen:
                export["metadaten"][(_spalte(z, "Property") or "").strip()] = \
                    (_spalte(z, "Wert") or "").strip()
        elif art == "details":
            for z in zeilen:
                url = (_spalte(z, "URL", "Seite") or "").strip()
                if not url:
                    continue
                export["details"].append({
                    "url": url,
                    "zuletzt_gecrawlt": (_spalte(z, "Zuletzt gecrawlt") or "").strip(),
                    "status": (_spalte(z, "Status") or "").strip(),
                    "quelle": (_spalte(z, "Quelle") or "").strip(),
                    "alternative": (_spalte(z, "Alternative Seite", "Canonical") or "").strip(),
                    "datei": datei.name,
                })
        else:
            export["unbekannt"].append({"datei": datei.name, "art": art})
    return export


# --------------------------------------------------------------------------
#  Export prüfen, BEVOR er Artefakt wird
# --------------------------------------------------------------------------

def pruefe_export(export: dict, heute: dt.date | None = None) -> list[dict]:
    """Gibt Befunde zurück: {regel, schwere, text}. 'hart' blockiert das Schreiben."""
    heute = heute or dt.date.today()
    f: list[dict] = []

    def befund(regel: str, schwere: str, text: str) -> None:
        f.append({"regel": regel, "schwere": schwere, "text": text})

    if not export.get("uebersicht"):
        befund("E1", "hart", "Keine Übersicht gefunden (Spalten „Grund“ + „Seiten“).")
    if not export.get("verlauf"):
        befund("E2", "hart", "Kein Diagramm gefunden (Spalte „Datum“).")

    for eintrag in export.get("uebersicht") or []:
        if eintrag.get("seiten") is None:
            befund("E3", "hart", f"Seitenzahl fehlt/unlesbar bei „{eintrag.get('grund')}“.")
        if not eintrag.get("grund"):
            befund("E3", "hart", "Zeile ohne Grund in der Übersicht.")

    daten: list[dt.date] = []
    for zeile in export.get("verlauf") or []:
        try:
            tag = dt.date.fromisoformat(str(zeile.get("datum") or ""))
        except (ValueError, TypeError):
            befund("E4", "hart", f"Datum unlesbar: {zeile.get('datum')!r}")
            continue
        daten.append(tag)
        if tag > heute:
            befund("E5", "hart", f"Datum in der Zukunft: {tag.isoformat()}")
        if zeile.get("nicht_indexiert") is None and zeile.get("indexiert") is None:
            befund("E5", "hinweis", f"Tag {tag.isoformat()} hat keine Zahlen (nur Impressionen).")

    if len(daten) != len(set(daten)):
        doppelt = sorted({d.isoformat() for d in daten if daten.count(d) > 1})
        befund("E6", "hart", f"Datum doppelt im Diagramm: {', '.join(doppelt)}")
    if daten != sorted(daten):
        befund("E7", "hinweis", "Diagramm ist nicht chronologisch sortiert – wird beim Lesen sortiert.")

    # Die wichtigste Gegenprobe: Summe der Gründe == „nicht indexiert“ am letzten
    # Tag. Weicht das ab, sind Übersicht und Diagramm aus verschiedenen Momenten
    # (genau der Fehler, der am 21.10. drei GSC-Artefakte unlesbar machte).
    summe = sum(e.get("seiten") or 0 for e in export.get("uebersicht") or [])
    if export.get("verlauf"):
        letzter = [z for z in export["verlauf"] if z.get("nicht_indexiert") is not None]
        if letzter:
            letzte_zeile = max(letzter, key=lambda z: z["datum"])
            if letzte_zeile["nicht_indexiert"] != summe:
                befund("E8", "hart",
                       f"Summe der Gründe ({summe}) passt nicht zu „nicht indexiert“ am "
                       f"{letzte_zeile['datum']} ({letzte_zeile['nicht_indexiert']}). "
                       "Übersicht und Diagramm stammen aus verschiedenen Momenten.")

    if not export.get("metadaten"):
        befund("E9", "hinweis", "Keine Metadaten-Datei (Property/Sitemap) dabei.")
    if not export.get("details"):
        befund("E10", "hinweis",
               "Keine Detail-Liste dabei. Die Summen sind damit rechenbar, die "
               "betroffenen URLs nicht. Ohne sie bleibt jede Ursachenanalyse bei der Summe stehen.")
    for u in export.get("unbekannt") or []:
        befund("E11", "hinweis", f"Datei {u['datei']} nicht zugeordnet (Art: {u['art']}).")

    return f


# --------------------------------------------------------------------------
#  Repo-Wahrheit – wogegen gerechnet wird
# --------------------------------------------------------------------------

def _frontmatter(pfad: Path) -> str:
    try:
        text = pfad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    ende = text.find("\n---", 3)
    return text[3:ende] if ende > 0 else ""


def _fm_wert(fm: str, schluessel: str) -> str | None:
    treffer = re.search(rf"^{re.escape(schluessel)}:\s*(.+?)\s*$", fm, re.M)
    if not treffer:
        return None
    return treffer.group(1).strip().strip('"').strip("'")


def _fm_wahr(fm: str, schluessel: str) -> bool:
    return bool(re.search(rf"^{re.escape(schluessel)}:\s*true\s*$", fm, re.M | re.I))


def _fm_liste(fm: str, schluessel: str) -> list[str]:
    roh = re.search(rf"^{re.escape(schluessel)}:\s*\[(.*?)\]", fm, re.M | re.S)
    if not roh:
        return []
    return [x.strip().strip('"').strip("'") for x in roh.group(1).split(",") if x.strip()]


def hugo_urlize(name: str) -> str:
    """Hugo-`urlize` für Taxonomie-Slugs: klein, Leerzeichen zu '-', Umlaute
    bleiben stehen (im Link dann prozent-kodiert: `/tags/reiser%C3%BCcktritt/`,
    so stand es im Export vom 19.10.2026). Wer stattdessen transliteriert,
    rechnet gegen URLs, die es nie gab."""
    t = (name or "").strip().lower().replace("ß", "ß")
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"[^0-9a-zäöüß-]", "", t)
    return re.sub(r"-{2,}", "-", t).strip("-")


def inhalts_seiten(root: Path = ROOT) -> tuple[list[str], list[str], list[str]]:
    """(indexierbar, noindex, taxonomie) aus content/ – Hugo-Logik nachgebildet.

    Rückgabe: relative URLs mit führendem und schließendem Schrägstrich.
    Berücksichtigt `url:` im Frontmatter (die Wahrheit bei Hugo), Entwürfe,
    `robotsNoIndex` und `sitemap.disable`. Das ist eine NÄHERUNG an den Build –
    maßgeblich ist `public/sitemap.xml`; fehlt der Build, sagt der Befund das.
    """
    cdir = Path(root) / "content"
    indexierbar: list[str] = []
    noindex: list[str] = []
    tags: set[str] = set()
    kategorien: set[str] = set()
    if not cdir.exists():
        return [], [], []
    # `index.md` sind Blätter, `_index.md` sind Sektionen (inklusive Startseite).
    # Wer nur `index.md` liest, übersieht /, /posts/, /pillar/ … und damit jede
    # Sektion in jeder Quote.
    for pfad in sorted(list(cdir.rglob("index.md")) + list(cdir.rglob("_index.md"))):
        fm = _frontmatter(pfad)
        if _fm_wahr(fm, "draft"):
            continue
        rel = pfad.parent.relative_to(cdir).as_posix()
        url = _fm_wert(fm, "url")
        if not url:
            url = "/" if rel == "." else f"/{rel}/"
        if not url.endswith("/") and not url.endswith(".html"):
            url += "/"
        for tag in _fm_liste(fm, "tags"):
            tags.add(tag)
        for kat in _fm_liste(fm, "categories"):
            kategorien.add(kat)
        sitemap_aus = bool(re.search(r"^sitemap:\s*\n(?:\s+.*\n)*?\s+disable:\s*true",
                                     fm, re.M))
        if _fm_wahr(fm, "robotsNoIndex"):
            noindex.append(url)
        elif not sitemap_aus:
            indexierbar.append(url)
    taxonomie = [f"/tags/{hugo_urlize(t)}/" for t in sorted(tags)]
    taxonomie += [f"/categories/{hugo_urlize(k)}/" for k in sorted(kategorien)]
    taxonomie += ["/tags/", "/categories/"]
    return sorted(set(indexierbar)), sorted(set(noindex)), sorted(taxonomie)


def sitemap_seiten(pfad: Path = PUBLIC_SITEMAP) -> list[str]:
    """URLs aus der gebauten Sitemap. Leere Liste, wenn kein Build vorliegt."""
    if not Path(pfad).exists():
        return []
    import xml.etree.ElementTree as ET

    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    try:
        baum = ET.parse(pfad)
    except ET.ParseError:
        return []
    out: list[str] = []
    for eintrag in baum.getroot().iter(f"{ns}url"):
        loc = eintrag.find(f"{ns}loc")
        if loc is None or not loc.text:
            continue
        pfad_teil = re.sub(rf"^https?://[^/]+", "", loc.text.strip()) or "/"
        out.append(pfad_teil)
    return sorted(set(out))


def weiterleitungs_karte(root: Path = ROOT) -> tuple[dict, dict]:
    """Liest die eine Zeile je Eintrag aus den beiden YAML-Quellen.

    Bewusst ohne YAML-Bibliothek: Die Dateien sind ein Eintrag je Zeile in genau
    einer Form (`- {von: "…", nach: "…", regel: "A", grund: "…"}` bzw.
    `- {von: "…", regel: "D"}`). Ein Parser für zwei Formen ist kleiner als die
    Abhängigkeit und im Selbsttest ohne Installation prüfbar.
    """
    def eintraege(pfad: Path) -> list[dict]:
        if not pfad.exists():
            return []
        out = []
        for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
            if not zeile.strip().startswith("- {"):
                continue
            eintrag = dict(re.findall(r'(\w+):\s*"([^"]*)"', zeile))
            if eintrag.get("von"):
                out.append(eintrag)
        return out

    weiter = {e["von"]: e.get("nach", "")
              for e in eintraege(Path(root) / "data" / "weiterleitungen.yaml")}
    entfallen = {e["von"]: e.get("regel", "")
                 for e in eintraege(Path(root) / "data" / "url_entfallen.yaml")}
    return weiter, entfallen


def robots_regeln(root: Path = ROOT) -> dict:
    """Liest die wirksame robots.txt (Build zuerst, Quelle als Rückfall)."""
    kandidaten = (_oeffentlich(root) / "robots.txt", Path(root) / "layouts" / "robots.txt")
    for pfad in kandidaten:
        if pfad.exists():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            # Pfade im Befund sind relativ: Ein Artefakt mit /tmp/… darin ist
            # auf keinem anderen Rechner nachvollziehbar.
            try:
                anzeige = str(pfad.relative_to(root))
            except ValueError:
                try:
                    anzeige = "public/" + str(pfad.relative_to(_oeffentlich(root)))
                except ValueError:
                    anzeige = pfad.name
            return {
                "datei": anzeige,
                "go_gesperrt": bool(re.search(r"^Disallow:\s*/go/\s*$", text, re.M)),
                "sitemap_zeile": bool(re.search(r"^Sitemap:\s*\S+", text, re.M)),
                "sperrt_go_gruppen": len(re.findall(r"^Disallow:\s*/go/\s*$", text, re.M)),
            }
    return {"datei": None, "go_gesperrt": False, "sitemap_zeile": False,
            "sperrt_go_gruppen": 0}


def gateway_seiten(root: Path = ROOT) -> list[str]:
    """Die /go/-Affiliate-Weiterleitungen im Build (je Ordner eine Seite)."""
    basis = Path(root) / "static" / "go"
    if not basis.exists():
        return []
    return sorted(f"/go/{p.name}/" for p in basis.iterdir() if p.is_dir())


def top_seiten_nicht_live(live: set[str], weiter: dict, root: Path = ROOT) -> list[dict]:
    """Seiten aus den Top-28-Tagen, die es nicht mehr gibt – mit Nachfrage.

    Das ist der einzige URL-genaue Beleg, den das Repo ohne Detail-Export hat:
    Eine URL, die Impressionen sammelt und nicht mehr live ist, belegt eine
    Altlast im Index. Ohne diesen Abgleich wäre „Index-Puffer“ nur eine Zahl.
    """
    pfad = Path(root) / "data" / "gsc" / "top_seiten_28t.json"
    if not pfad.exists():
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for eintrag in daten if isinstance(daten, list) else []:
        url = str(eintrag.get("seite", ""))
        pfad_teil = re.sub(r"^https?://[^/]+", "", url) or "/"
        if pfad_teil in live:
            continue
        out.append({
            "url": pfad_teil,
            "impressionen": eintrag.get("impressions"),
            "klicks": eintrag.get("clicks"),
            "position": eintrag.get("position"),
            "weiterleitung": weiter.get(pfad_teil),
        })
    return sorted(out, key=lambda e: -(e.get("impressionen") or 0))


def _oeffentlich(root: Path = ROOT) -> Path:
    """Das Build-Verzeichnis. INDEX_GATE_BASE gilt nur für DIESES Repo – ein
    Selbsttest in einem temporären Baum darf nicht plötzlich das echte Build
    messen (und dessen Zahlen in den Test ziehen)."""
    if Path(root).resolve() == ROOT.resolve():
        aus_env = os.environ.get(UMGEBUNG_BASIS)
        if aus_env and Path(aus_env).exists():
            return Path(aus_env)
    return Path(root) / "public"


def bau_messen(public: Path) -> dict:
    """Die gebaute URL-Fläche zählen: was existiert, was darf in den Index?

    Das ist die Gegenprobe, die eine Summe aus der Search Console erst
    bewertbar macht. Ohne sie weiß niemand, ob „320 nicht indexiert“ viel oder
    wenig ist – mit ihr ist es eine Quote (320 gegen 258 gebaute URLs).

    Gemessen wird am ausgelieferten HTML, nicht an einer Liste: `public/` ist
    genau das, was GitHub Pages ausliefert. Ein `robots`-Meta entscheidet über
    indexierbar, ein Meta-Refresh über „Weiterleitungsseite“.
    """
    public = Path(public)
    if not public.exists():
        return {"vorhanden": False}
    seiten = list(public.rglob("index.html"))
    indexierbar = 0
    noindex = 0
    weiterleitung = 0
    gateway = 0
    pager = 0
    klassen: dict[str, int] = {}
    for pfad in seiten:
        try:
            kopf = pfad.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        treffer = re.search(
            r'<meta[^>]+name=["\']?robots["\']?[^>]*content=["\']([^"\']+)', kopf, re.I)
        inhalt = (treffer.group(1).lower() if treffer else "")
        if "noindex" in inhalt:
            noindex += 1
            teile = pfad.relative_to(public).parts
            rel = "/".join(teile)
            # Reihenfolge ist Absicht: eine Weiterleitungsseite erkennt man am
            # Marker des Generators, nicht am Ordner – sie liegt unter /posts/
            # wie ein Artikel und würde dort sonst als Inhalt gezählt.
            if "ff-weiterleitung" in kopf:
                klasse = "weiterleitung"
                weiterleitung += 1
            elif rel.startswith("go/"):
                klasse = "gateway"
                gateway += 1
            elif "/page/" in rel or rel.startswith("page/"):
                klasse = "pager"
                pager += 1
            else:
                klasse = teile[0] if len(teile) > 1 else "wurzel"
            klassen[klasse] = klassen.get(klasse, 0) + 1
        else:
            indexierbar += 1
    gesamt = indexierbar + noindex
    return {
        "vorhanden": True,
        "verzeichnis": str(public),
        "seiten": gesamt,
        "indexierbar": indexierbar,
        "noindex": noindex,
        "weiterleitung": weiterleitung,
        "gateway": gateway,
        "pager": pager,
        "noindex_klassen": dict(sorted(klassen.items(), key=lambda kv: -kv[1])),
        "verhaeltnis": round(gesamt / indexierbar, 2) if indexierbar else None,
    }


def repo_wahrheit(root: Path = ROOT) -> dict:
    """Alles, wogegen die Search-Console-Zahlen gerechnet werden."""
    indexierbar, noindex, taxonomie = inhalts_seiten(root)
    oeffentlich = _oeffentlich(root)
    sitemap = sitemap_seiten(oeffentlich / "sitemap.xml")
    bau = bau_messen(oeffentlich)
    basis = "public/sitemap.xml"
    live = sitemap
    if not live:
        basis = "content/ (Näherung, kein Build gemessen)"
        live = indexierbar
    weiter, entfallen = weiterleitungs_karte(root)
    gateways = gateway_seiten(root)
    befunde = []
    if not sitemap:
        befunde.append({
            "regel": "W1", "schwere": "hinweis",
            "text": ("Kein `public/sitemap.xml`: Die Zahl der indexierbaren Seiten ist "
                     "aus `content/` genähert. Für den Beweis einmal bauen "
                     "(`hugo --destination public`)."),
        })
    # Wie verteilt sich der indexierbare Bestand? Ohne diese Aufteilung lässt
    # sich eine GSC-Zahl nicht zuordnen: „69 gefunden, nicht indexiert“ ist
    # etwas anderes, wenn 69 Artikel in der Sitemap stehen und sonst nichts.
    sektionen: dict[str, int] = {}
    for url in live:
        teile = [t for t in url.split("/") if t]
        schluessel = teile[0] if teile else "startseite"
        sektionen[schluessel] = sektionen.get(schluessel, 0) + 1

    top_nicht_live = top_seiten_nicht_live(set(live), weiter, root)
    return {
        "basis": basis,
        "bau": bau,
        "indexierbar": sorted(set(live)),
        "anzahl_indexierbar": len(set(live)),
        "noindex": sorted(set(noindex)),
        "anzahl_noindex": len(set(noindex)),
        "gateways": gateways,
        "anzahl_gateways": len(gateways),
        "sektionen": dict(sorted(sektionen.items(), key=lambda kv: -kv[1])),
        "taxonomie_404": taxonomie,
        "anzahl_taxonomie": len(taxonomie),
        "weiterleitungen": weiter,
        "anzahl_weiterleitungen": len(weiter),
        "entfallen": entfallen,
        "anzahl_entfallen": len(entfallen),
        "robots": robots_regeln(root),
        "top_nicht_live": top_nicht_live,
        "befunde": befunde,
    }


# --------------------------------------------------------------------------
#  Kennzahlen und Anomalien
# --------------------------------------------------------------------------

def kennzahlen(export: dict, wahrheit: dict, heute: dt.date | None = None) -> dict:
    bau = wahrheit.get("bau") or {}
    heute = heute or dt.date.today()
    verlauf = sorted((z for z in export.get("verlauf") or [] if z.get("datum")),
                     key=lambda z: z["datum"])
    voll = [z for z in verlauf if z.get("nicht_indexiert") is not None]
    letzter = voll[-1] if voll else {}
    gruende: dict[str, int] = {}
    for e in export.get("uebersicht") or []:
        schluessel = klassifiziere(e.get("grund", ""))
        gruende[schluessel] = gruende.get(schluessel, 0) + (e.get("seiten") or 0)
    summe = sum(e.get("seiten") or 0 for e in export.get("uebersicht") or [])
    indexiert = letzter.get("indexiert")
    nicht_indexiert = letzter.get("nicht_indexiert")
    bekannt = (indexiert or 0) + (nicht_indexiert or 0) if (indexiert is not None
                                                            or nicht_indexiert is not None) else None

    def delta(tage: int, feld: str) -> int | None:
        if len(voll) <= tage:
            return None
        jetzt, vorher = voll[-1].get(feld), voll[-1 - tage].get(feld)
        if jetzt is None or vorher is None:
            return None
        return jetzt - vorher

    # Anomalien: Tages-Sprünge, die zu groß sind, um Zufall zu sein. Schwelle
    # bewusst relativ (10 %) UND absolut (8 Seiten) – kleine Bestände schwanken
    # sonst bei jeder Einzeländerung.
    anomalien = []
    for vorher, jetzt in zip(voll, voll[1:]):
        for feld in ("nicht_indexiert", "indexiert"):
            a, b = vorher.get(feld), jetzt.get(feld)
            if a is None or b is None:
                continue
            sprung = b - a
            if abs(sprung) >= max(8, round(0.10 * max(a, 1))):
                anomalien.append({
                    "datum": jetzt["datum"], "feld": feld, "von": a, "nach": b,
                    "delta": sprung, "prozent": prozent(abs(sprung), a),
                })

    # Deltas für alle Fristen, die im Betrieb vorkommen. Eine fest verdrahtete
    # 7-Tage-Zahl fehlt genau dann, wenn ein Export nur fünf Tage umfasst.
    deltas = {f"delta_{tage}_{feld}": delta(tage, feld)
              for tage in (1, 2, 3, 7, 14, 28)
              for feld in ("nicht_indexiert", "indexiert")}

    # Alter der Momentaufnahme. Der Bericht hat keine API: Er wird nur so
    # frisch, wie ein Mensch exportiert. Ein Befund ohne Altersangabe sieht
    # aus wie eine Live-Messung – und ist dann Wochen alt.
    alter = None
    if letzter.get("datum"):
        try:
            alter = (heute - dt.date.fromisoformat(letzter["datum"])).days
        except ValueError:
            alter = None

    # Die Detail-Listen (welche URL, welcher Grund) kommen nur per Export. Ihr
    # Alter entscheidet, ob aus dem Befund eine Arbeitsliste wird – deshalb
    # steht es in denselben Kennzahlen wie das Alter des Berichts (W8).
    detail = detail_stand(heute)
    impressionen = [z.get("impressionen") for z in verlauf if z.get("impressionen") is not None]
    live = wahrheit.get("anzahl_indexierbar") or 0
    return {
        "stand_datum": letzter.get("datum"),
        "export_alter_tage": alter,
        "detail_stand": detail["stand"],
        "detail_alter_tage": detail["alter_tage"],
        "detail_urls": detail["urls"],
        "sitemap_ohne_lastmod": lastmod_luecke(wahrheit),
        "tage_im_export": len(verlauf),
        "indexiert": indexiert,
        "nicht_indexiert": nicht_indexiert,
        "bekannt": bekannt,
        "quote_indexiert": prozent(indexiert or 0, bekannt or 0),
        "gruende": gruende,
        "summe_gruende": summe,
        **deltas,
        "impressionen_summe": sum(impressionen) if impressionen else None,
        "impressionen_je_tag": round(sum(impressionen) / len(impressionen), 2) if impressionen else None,
        "tage_ohne_impression": sum(1 for i in impressionen if i == 0),
        "tage_mit_impression": sum(1 for i in impressionen if i and i > 0),
        "live_indexierbar": live,
        "index_puffer": (indexiert or 0) - live if indexiert is not None else None,
        "build_seiten": bau.get("seiten"),
        "build_noindex": bau.get("noindex"),
        "build_weiterleitung": bau.get("weiterleitung"),
        "build_verhaeltnis": bau.get("verhaeltnis"),
        "build_noindex_klassen": bau.get("noindex_klassen") or {},
        # Wie oft jede gebaute URL in „nicht indexiert“ auftaucht. Über 1,0
        # bedeutet: Es sind mehr Nicht-Index-Einträge als gebaute URLs – dann
        # bestehen die Einträge überwiegend aus URLs, die es nicht mehr gibt.
        "nicht_indexiert_je_build_seite": (
            round((nicht_indexiert or 0) / bau["seiten"], 2)
            if bau.get("seiten") and nicht_indexiert is not None else None),
        "anomalien": anomalien,
        "robots_gesperrt": gruende.get("robots_blocked", 0),
    }


# --------------------------------------------------------------------------
#  Befund: je Grund eine Erwartung und ein Urteil
# --------------------------------------------------------------------------

def _urteil(ist: int, erwartung: int | None, art: str = "genau") -> tuple[str, int | None]:
    """(Urteil, offen). erwartung=None heißt: keine Gegenprobe möglich.

    `art` unterscheidet zwei Sorten Erwartung:
      genau      – der Bestand sagt die Zahl exakt voraus (noindex-Seiten)
      hoechstens – der Bestand ist die Obergrenze (Crawl-Rückstand beim Bestand)
    Eine Obergrenze als exakte Erwartung auszugeben wäre eine Scheingenauigkeit.
    """
    if erwartung is None:
        return "unklar", None
    offen = max(0, ist - erwartung)
    if offen:
        return "offen", offen
    if art == "hoechstens":
        return "plausibel", 0
    return ("vollstaendig" if ist == erwartung else "plausibel"), 0


def befund_gruende(export: dict, wahrheit: dict) -> list[dict]:
    """Jeder GSC-Grund mit Gegenprobe aus dem Repo."""
    erwartungen = {
        "noindex": (wahrheit["anzahl_noindex"], (
            f"{wahrheit['anzahl_noindex']} Seiten tragen im Inhalt `robotsNoIndex: true` "
            f"({', '.join(wahrheit['noindex'][:6])}{' …' if len(wahrheit['noindex']) > 6 else ''}). "
            "Mehr als diese Zahl wäre ein Leck: eine Seite, die nicht noindex sein darf.")),
        "robots_blocked": (wahrheit["anzahl_gateways"], (
            f"{wahrheit['anzahl_gateways']} /go/-Affiliate-Gateways, alle per robots.txt gesperrt "
            f"(`Disallow: /go/` in {wahrheit['robots']['sperrt_go_gruppen']} Roboter-Gruppen). "
            "Die Sperre ist Absicht: Ein Gateway ist eine Weiterleitung, keine Seite. "
            "Die Meldung bleibt dauerhaft stehen, weil Google ein noindex hinter einer "
            "Sperre nicht lesen kann – das ist erwartbar, kein Defekt.")),
        "redirect": (wahrheit["anzahl_weiterleitungen"], (
            f"{wahrheit['anzahl_weiterleitungen']} Weiterleitungs-Seiten in `static/` "
            "(Meta-Refresh + `noindex,follow` + Canonical). Gemeldet wird nur, was Google "
            "tatsächlich besucht hat – die Zahl darf kleiner sein, nie größer.")),
        "not_found": (wahrheit["anzahl_taxonomie"] + wahrheit["anzahl_entfallen"], (
            f"erklärbar sind {wahrheit['anzahl_taxonomie']} Taxonomie-URLs (seit 29.09.2026 "
            f"abgeschaltet: {len([t for t in wahrheit['taxonomie_404'] if t.startswith('/tags/')])} "
            f"Tag- und Kategorie-Archive) plus {wahrheit['anzahl_entfallen']} bewusst "
            "entfallene Alt-URLs (Regel D). Der Rest ist Historie, die nur die "
            "Detail-Liste aufklärt.")),
        "discovered_not_indexed": (wahrheit["anzahl_indexierbar"], (
            f"Obergrenze ist der Bestand: {wahrheit['anzahl_indexierbar']} indexierbare Seiten. "
            "Alles darunter ist ein Rückstand beim Abrufen, kein Auszeichnungsfehler."), "hoechstens"),
        "crawled_not_indexed": (wahrheit["anzahl_indexierbar"], (
            "Google hat gelesen und sich dagegen entschieden. Die Gegenprobe ist "
            "redaktionell: eigenständiger Inhalt, klare Suchabsicht, kein Duplikat."), "hoechstens"),
    }
    out = []
    for eintrag in sorted(export.get("uebersicht") or [],
                          key=lambda e: -(e.get("seiten") or 0)):
        schluessel = klassifiziere(eintrag.get("grund", ""))
        katalog = GRUND_KATALOG[schluessel]
        ist = eintrag.get("seiten") or 0
        eintrag_erwartung = erwartungen.get(schluessel, (None, "", "genau"))
        erwartung, basis = eintrag_erwartung[0], eintrag_erwartung[1]
        art = eintrag_erwartung[2] if len(eintrag_erwartung) > 2 else "genau"
        urteil, offen = _urteil(ist, erwartung, art)
        out.append({
            "grund": eintrag.get("grund"),
            "schluessel": schluessel,
            "titel": katalog["titel"],
            "klasse": katalog["klasse"],
            "bedeutung": katalog["bedeutung"],
            "quelle": eintrag.get("quelle"),
            "validierung": eintrag.get("validierung"),
            "seiten": ist,
            "erwartung": erwartung,
            "erwartung_art": art,
            "offen": offen,
            "urteil": urteil,
            "basis": basis,
        })
    return out


# Detail-Listen liegen als CSV in diesem Ordner; die Datei `.stand` nennt das
# Exportdatum. Beides im Repo, damit der Befund auch ohne Google-Zugriff
# nachvollziehbar bleibt.
DETAILS = ABDECKUNG / "details"


def detail_stand(heute: dt.date | None = None) -> dict:
    """Wie alt sind die Detail-Listen? Ohne sie bleibt jede Triage eine Summe."""
    heute = heute or dt.date.today()
    stand_datei = DETAILS / ".stand"
    stand = None
    if stand_datei.exists():
        stand = stand_datei.read_text(encoding="utf-8").strip()[:10] or None
    urls = 0
    for csv in sorted(DETAILS.glob("*.csv")) if DETAILS.exists() else []:
        try:
            with csv.open(encoding="utf-8-sig", newline="") as fh:
                kopf = next(csv.reader(fh), [])
            if any("url" in str(k).lower() for k in kopf):
                urls += max(0, sum(1 for _ in csv.open(encoding="utf-8-sig")) - 1)
        except (OSError, StopIteration, UnicodeDecodeError):
            continue
    alter = None
    if stand:
        try:
            alter = (heute - dt.date.fromisoformat(stand)).days
        except ValueError:
            alter = None
    return {"stand": stand, "alter_tage": alter, "urls": urls}


def lastmod_luecke(wahrheit: dict, root: Path = ROOT) -> int | None:
    """Sitemap-URLs ohne `lastmod` – ohne Datum crawlt Google nach Gefühl.

    Gibt None zurück, wenn kein Build vorliegt: Eine 0 wäre hier eine Lüge.
    """
    sitemap = _oeffentlich(root) / "sitemap.xml"
    if not sitemap.exists():
        return None
    import xml.etree.ElementTree as ET

    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    try:
        baum = ET.parse(sitemap)
    except (ET.ParseError, OSError):
        return None
    return len([e for e in baum.getroot().iter(f"{ns}url") if e.find(f"{ns}lastmod") is None])


def widersprueche(gruende: list[dict], kenn: dict, wahrheit: dict,
                  pruef: list[dict]) -> list[dict]:
    """Wo Zahlen und Bestand nicht zusammenpassen – mit Regel und Folge."""
    out: list[dict] = []
    nach = {g["schluessel"]: g for g in gruende}

    for bef in pruef:
        if bef["schwere"] == "hart":
            out.append({"regel": bef["regel"], "schwere": "hart",
                        "text": bef["text"]})

    noindex = nach.get("noindex")
    if noindex and noindex["offen"]:
        out.append({
            "regel": "W2", "schwere": "hart",
            "text": (f"{noindex['seiten']} Seiten sind laut Search Console per noindex "
                     f"ausgeschlossen, im Inhalt sind es {wahrheit['anzahl_noindex']}. "
                     f"{noindex['offen']} Seite(n) sind unerklärt – noindex-Leck möglich "
                     "(Seite liefert `X-Robots-Tag` oder ein Template setzt es)."),
        })

    robots = nach.get("robots_blocked")
    if robots and robots["offen"]:
        out.append({
            "regel": "W3", "schwere": "hart",
            "text": (f"{robots['seiten']} URLs sind per robots.txt gesperrt, es gibt aber nur "
                     f"{wahrheit['anzahl_gateways']} Gateways. {robots['offen']} gesperrte "
                     "URL(s) sind Inhalt – eine Sperre dort ist ein Indexierungsblocker."),
        })

    if not wahrheit["robots"]["go_gesperrt"] and wahrheit["anzahl_gateways"]:
        out.append({
            "regel": "W4", "schwere": "hart",
            "text": "robots.txt sperrt `/go/` nicht, obwohl Gateways existieren.",
        })

    if kenn.get("index_puffer") is not None and kenn["index_puffer"] > 0:
        out.append({
            "regel": "W5", "schwere": "hinweis",
            "text": (f"{kenn['indexiert']} Seiten sind im Index, indexierbar sind "
                     f"{kenn['live_indexierbar']} – {kenn['index_puffer']} Einträge sind "
                     "Altlasten (entfernte, weitergeleitete oder abgeschaltete URLs). "
                     "Sie kosten kein Crawl-Budget mehr, verzerren aber jede Quote."),
        })

    for g in gruende:
        if g["klasse"] == "unbekannt":
            out.append({
                "regel": "W6", "schwere": "hart",
                "text": (f"Unbekannter Grund in der Search Console: „{g['grund']}“ "
                         f"({g['seiten']} Seiten). Katalog in diesem Modul ergänzen, "
                         "sonst rechnet der Befund an dieser Stelle nicht."),
            })

    alter = kenn.get("export_alter_tage")
    if alter is not None and alter > 14:
        out.append({
            "regel": "W8", "schwere": "hinweis",
            "text": (f"Der Abdeckungsbericht ist {alter} Tage alt (Stand "
                     f"{kenn.get('stand_datum')}). Die Search Console liefert ihn nur als "
                     "CSV – ohne neuen Export misst dieser Befund die Vergangenheit."),
        })

    detail_alter = kenn.get("detail_alter_tage")
    if detail_alter is None or detail_alter > 14:
        out.append({
            "regel": "W9", "schwere": "hinweis",
            "text": (("Keine Detail-Liste im Bestand" if detail_alter is None
                      else f"Detail-Listen sind {detail_alter} Tage alt")
                     + " (`data/gsc/abdeckung/details/`). Ohne sie lassen sich die "
                     "gemeldeten URLs nicht triagieren – die Summen bleiben Summen."),
        })

    tote = kenn.get("tote_ziele") or 0
    if tote:
        out.append({
            "regel": "W11", "schwere": "hinweis",
            "text": (f"{tote} Linkziel(e) im Inhalt werden nicht gebaut "
                     "(Entwurf oder gelöscht). Das Rendering zeigt dort nur Text – "
                     "die Verlinkung ist wirkungslos: veröffentlichen oder entlinken."),
        })

    ohne_lastmod = kenn.get("sitemap_ohne_lastmod")
    if ohne_lastmod:
        out.append({
            "regel": "W10", "schwere": "hinweis",
            "text": (f"{ohne_lastmod} Sitemap-URL(s) ohne `lastmod`. Google entscheidet "
                     "dann selbst, wann neu gecrawlt wird – genau das Gegenteil von "
                     "Crawl-Nachfrage (M2)."),
        })

    if kenn.get("robots_gesperrt") and not wahrheit["robots"]["sitemap_zeile"]:
        out.append({
            "regel": "W7", "schwere": "hart",
            "text": "robots.txt nennt keine Sitemap-Zeile.",
        })

    return out


def beweisfragen(gruende: list[dict], export: dict, wahrheit: dict) -> list[dict]:
    """Was fehlt, um aus einer Summe eine Entscheidung zu machen."""
    fragen: list[dict] = []
    offen_404 = next((g["offen"] for g in gruende if g["schluessel"] == "not_found"), 0)
    hat_details = bool(export.get("details"))
    if offen_404:
        fragen.append({
            "frage": (f"Welche {offen_404} URLs liefern 404, und welche davon haben noch "
                      "Nachfrage?"),
            "braucht": ("Search Console → Indexierung → Seiten → „Nicht gefunden (404)“ → "
                        "Exportieren; Datei hier einlesen mit `--vorschlaege`."),
            "wirkung": ("Nur so lässt sich zwischen „vergessen“ (Weiterleitung) und "
                        "„richtig entsorgt“ (404 bleibt) unterscheiden. Ohne Liste wäre "
                        "jede Zuordnung geraten."),
            "blockiert": "P1-Weiterleitungsplan",
        })
    for g in gruende:
        if g["schluessel"] in ("crawled_not_indexed", "discovered_not_indexed") and not hat_details:
            fragen.append({
                "frage": f"Welche URLs stecken in „{g['grund']}“ ({g['seiten']})?",
                "braucht": (f"Detail-Export „{g['grund']}.csv“ aus demselben Bericht."),
                "wirkung": ("Erst die URL macht aus einer Quote eine Redaktionsliste: "
                            "welcher Artikel braucht Substanz, welcher nur einen internen Link."),
                "blockiert": "Inhalts- und Verlinkungsplan",
            })
    if not wahrheit["indexierbar"] or wahrheit["basis"].startswith("content/"):
        fragen.append({
            "frage": "Wie viele Seiten sind wirklich indexierbar?",
            "braucht": "Ein Build: `hugo --destination public` (oder Live-Sitemap).",
            "wirkung": ("Der Nenner jeder Quote. Ohne Build rechnet der Befund gegen eine "
                        "Näherung aus `content/` – ausgewiesen, nicht verschwiegen."),
            "blockiert": "Quote und Index-Puffer",
        })
    if not export.get("details"):
        fragen.append({
            "frage": "Sind die 115 Weiterleitungs-Seiten im Index angekommen?",
            "braucht": ("Detail-Export „Seite mit Weiterleitung.csv“ und "
                        "„Alternative Seite mit ordnungsgemäßem Canonical-Tag.csv“."),
            "wirkung": ("Gemeldet wird bisher genau eine Weiterleitung. Entweder hat Google "
                        "die 115 Meta-Refresh-Seiten noch nicht besucht, oder sie werden "
                        "anders gezählt. Beides ist eine Aussage – geraten wird sie nicht."),
            "blockiert": "Bewertung der Weiterleitungs-Strategie",
        })
    return fragen


# --------------------------------------------------------------------------
#  Maßnahmen
# --------------------------------------------------------------------------

def massnahmen(gruende: list[dict], kenn: dict, wahrheit: dict, export: dict) -> list[dict]:
    """Priorisierte Liste. P1 = diese Woche, P2 = dieser Monat, P3 = Beobachten."""
    out: list[dict] = []

    def add(mid, titel, dringlichkeit, aufwand, wirkung, beleg, owner, schritt):
        out.append({"id": mid, "titel": titel, "dringlichkeit": dringlichkeit,
                    "aufwand": aufwand, "wirkung": wirkung, "beleg": beleg,
                    "owner": owner, "schritt": schritt})

    nach = {g["schluessel"]: g for g in gruende}
    n404 = nach.get("not_found", {}).get("seiten", 0)
    offen404 = nach.get("not_found", {}).get("offen") or 0
    discovered = nach.get("discovered_not_indexed", {}).get("seiten", 0)
    crawled = nach.get("crawled_not_indexed", {}).get("seiten", 0)
    live = wahrheit["anzahl_indexierbar"] or 1

    if offen404:
        add("M1", "404-Detail-Liste einlesen und triagieren", "P1", "S",
            (f"{offen404} der {n404} 404er sind ohne Detail-Liste unerklärt. "
             "Die Triage trennt Nachfrage (Weiterleitung) von Entsorgung (404 bleibt)."),
            f"Übersicht: {n404} × 404 · erklärbar {n404 - offen404} · offen {offen404}",
            "Mensch (Export) + Automat",
            "Search Console → Indexierung → Seiten → „Nicht gefunden (404)“ → Exportieren, "
            "dann `python3 scripts/gsc_abdeckung.py --vorschlaege <datei>`.")

    if discovered >= max(20, round(0.4 * live)):
        add("M2", "Crawl-Nachfrage für gefundene, nicht abgerufene Seiten", "P1", "M",
            (f"{discovered} von {live} indexierbaren Seiten hat Google noch nicht abgerufen "
             f"({prozent(discovered, live)} % des Bestands). Das ist der größte Einzelposten "
             "und der einzige, der sich ohne Google-Zugriff bewegen lässt: interne Verlinkung, "
             "Aktualität, Autorität."),
            f"{discovered} „Gefunden – zurzeit nicht indexiert“ bei {live} indexierbaren Seiten",
            "Automat + Redaktion",
            "Interne Links auf die betroffenen Seiten verdichten (jede Seite aus mindestens "
            "zwei Artikeln erreichbar), Änderungsdatum ehrlich setzen, Publikations-Kadenz "
            "auf 2/Tag begrenzen; wöchentlich `scripts/gsc_indexierung.py --pruefen` für den "
            "Status je URL.")

    if crawled:
        add("M3", "Redaktions-Queue für „gecrawlt, nicht indexiert“", "P2", "M",
            (f"{crawled} Seiten wurden gelesen und abgelehnt. Das ist ein Inhaltsignal: "
             "Substanz, Einzigartigkeit, Passung zur Suchabsicht."),
            f"{crawled} × „Gecrawlt – zurzeit nicht indexiert“",
            "Redaktion",
            "Je URL: Suchabsicht (Kurzantwort), Einzigartigkeit (`duplikat_guard.py`), "
            "Faktenfrische (`faktenfrische.py`) prüfen; erst danach erneut anfragen.")

    if kenn.get("index_puffer") and kenn["index_puffer"] > 0:
        top = wahrheit["top_nicht_live"][:5]
        beleg = f"{kenn['indexiert']} indexiert bei {kenn['live_indexierbar']} indexierbaren Seiten"
        if top:
            beleg += (" · mit Nachfrage: " + ", ".join(
                f"{t['url']} ({t['impressionen']} Impr.)" for t in top))
        add("M4", "Index-Altlasten benennen statt mitzählen", "P2", "S",
            ("Der Index enthält mehr URLs als die Site hat. Die Quote ist deshalb zu hoch "
             "und jede Erfolgsmessung auf dieser Basis falsch."),
            beleg, "Automat",
            "`--audit` listet die Altlasten aus den Top-Seiten; für den Rest die "
            "Detail-Exporte je Grund. Bereinigung nur dort, wo die URL keine Nachfrage hat "
            "(Weiterleitung vorhanden oder 404 ohne Impressionen).")

    if wahrheit["anzahl_noindex"]:
        add("M5", "noindex-Bestand als Vertrag führen", "P3", "S",
            (f"{wahrheit['anzahl_noindex']} Seiten sind absichtlich noindex "
             "(Suche, Newsletter-Funnel). Steigt die Zahl in der Search Console darüber, "
             "ist es ein Leck – die Wache meldet das hart."),
            f"{wahrheit['anzahl_noindex']} × robotsNoIndex in content/ · GSC "
            f"{nach.get('noindex', {}).get('seiten', 0)}", "Automat",
            "Wache läuft im Tageslauf (`--gate`). Kein Handlungsbedarf, solange die "
            "Zahlen deckungsgleich bleiben.")

    if nach.get("robots_blocked", {}).get("seiten"):
        add("M6", "robots.txt-Sperre der Gateways dokumentiert lassen", "P3", "S",
            ("Die Meldung „durch robots.txt blockiert“ verschwindet nie, solange `/go/` "
             "gesperrt ist. Das ist die richtige Abwägung: 20 Gateways sind keine Inhalte, "
             "und Google soll sie nicht crawlen."),
            f"{nach['robots_blocked']['seiten']} blockiert bei {wahrheit['anzahl_gateways']} "
            f"Gateways · {wahrheit['robots']['sperrt_go_gruppen']} Roboter-Gruppen",
            "Automat",
            "Keine Änderung. Wächter: `schema_seo_gate.py` (S8) und `--gate` (W3) prüfen, "
            "dass die Sperre bleibt und keine Inhaltsseite hineingerät.")

    anomalien = kenn.get("anomalien") or []
    if anomalien:
        a = anomalien[-1]
        add("M7", "Sprung im Abdeckungsbericht erklären", "P2", "S",
            (f"Am {a['datum']} sind „{a['feld']}“ von {a['von']} auf {a['nach']} gesprungen "
             f"({a['delta']:+d}, {a['prozent']} %). Ein Sprung dieser Größe hat eine Ursache "
             "im Repo: Deploy, Sitemap-Änderung, Aufräumaktion."),
            f"Diagramm {a['datum']}: {a['feld']} {a['von']} → {a['nach']}",
            "Mensch",
            "Änderungsprotokoll (`/aenderungsprotokoll/`) und Deploy-Historie zum Datum "
            "abgleichen; Ergebnis im Bericht festhalten, damit der Sprung nicht als Rauschen gilt.")

    alter = kenn.get("export_alter_tage")
    if alter is not None and alter > 7:
        add("M10", "Neuen Abdeckungs-Export einlesen", "P1" if alter > 21 else "P2", "S",
            (f"Der Befund steht auf dem Stand von vor {alter} Tagen. Zahlen, die älter "
             "als vier Wochen sind, taugen nicht als Entscheidungsgrundlage."),
            f"Stand {kenn.get('stand_datum')} · {alter} Tage alt",
            "Mensch",
            "Search Console → Indexierung → Seiten → Exportieren, dann "
            "`python3 scripts/gsc_abdeckung.py --import <verzeichnis> --audit --schreiben`.")

    if not export.get("details"):
        add("M8", "Detail-Exporte in den Tageslauf aufnehmen", "P2", "S",
            ("Der Abdeckungsbericht hat keine API. Wer ihn nur als Bildschirmfoto liest, "
             "kann nicht gegen den Bestand rechnen – und merkt einen Rückschritt erst "
             "Wochen später."),
            "Export enthält 0 Detail-Zeilen", "Mensch + Automat",
            "Wöchentlich (Montag) die vier Exporte in die Search Console laden und "
            "`--import` ausführen. Der Vergleichslauf (`--gate`) erkennt Rückschritte "
            "automatisch.")

    if kenn.get("quote_indexiert") is not None and kenn["quote_indexiert"] < 50:
        add("M9", "Indexquote als Zielgröße etablieren", "P2", "S",
            (f"Nur {kenn['quote_indexiert']} % der bekannten URLs sind im Index. "
             "Die Kennzahl gehört in den Wochenbericht, nicht in ein Bildschirmfoto."),
            f"{kenn['indexiert']} von {kenn['bekannt']} bekannten URLs",
            "Automat",
            "`--audit --md` liefert die Zeile für den Wochenbericht; Ziel: Quote steigt "
            "vier Wochen in Folge, ohne dass die Zahl der 404er wächst.")

    rang = {"P1": 0, "P2": 1, "P3": 2}
    return sorted(out, key=lambda m: (rang.get(m["dringlichkeit"], 9), m["id"]))


# --------------------------------------------------------------------------
#  Gate
# --------------------------------------------------------------------------

def gate(auswertung: dict, vorheriger: dict | None) -> dict:
    """Hart bei Rückschritt und Widerspruch, still bei allem anderen."""
    funde: list[dict] = []
    kenn = auswertung["kennzahlen"]
    for w in auswertung["widersprueche"]:
        if w["schwere"] == "hart":
            funde.append({"regel": w["regel"], "schwere": "hart", "text": w["text"]})
    if kenn.get("bekannt") is None:
        funde.append({"regel": "G1", "schwere": "hart",
                      "text": "Der Export enthält keinen belastbaren Tageswert."})
    if vorheriger:
        alt = vorheriger.get("nicht_indexiert")
        neu = kenn.get("nicht_indexiert")
        if alt and neu and neu >= alt * 1.10:
            funde.append({"regel": "G2", "schwere": "hart",
                          "text": (f"Nicht indexierte Seiten von {alt} auf {neu} gestiegen "
                                   f"({prozent(neu - alt, alt)} %).")})
        altq = vorheriger.get("quote_indexiert")
        neuq = kenn.get("quote_indexiert")
        if altq is not None and neuq is not None and neuq <= altq - 5:
            funde.append({"regel": "G3", "schwere": "hart",
                          "text": (f"Indexquote von {altq} % auf {neuq} % gefallen "
                                   "(Schwelle 5 Prozentpunkte).")})
        if (vorheriger.get("summe_gruende") is not None
                and kenn.get("summe_gruende") is not None
                and vorheriger["summe_gruende"] == kenn["summe_gruende"]
                and vorheriger.get("nicht_indexiert") != kenn.get("nicht_indexiert")):
            funde.append({"regel": "G4", "schwere": "hart",
                          "text": ("Summe der Gründe unverändert, Gesamtzahl geändert – "
                                   "die Übersicht ist unvollständig.")})
    # Ein gebrochener Vertrag (noindex-Leck, unbegründete Sperre, fehlende
    # Gateway-Sperre) ist kein Hinweis: Er ändert, welche Seiten überhaupt in
    # den Index können. Deshalb hart – die Abnahme verlangt es so.
    vertrag_teil = auswertung.get("vertrag") or {}
    for f in vertrag_teil.get("funde") or []:
        if f.get("schwere") == "hart":
            funde.append({"regel": "G6", "schwere": "hart",
                          "text": f"[{f['regel']}] {f['text']}"})
    for a in kenn.get("anomalien") or []:
        funde.append({"regel": "G5", "schwere": "hinweis",
                      "text": (f"Sprung am {a['datum']}: {a['feld']} {a['von']} → "
                               f"{a['nach']} ({a['prozent']} %).")})
    hart = [f for f in funde if f["schwere"] == "hart"]
    return {"status": "rot" if hart else "gruen", "funde": funde,
            "anzahl_hart": len(hart)}


# --------------------------------------------------------------------------
#  Vorschläge aus einer Detail-Liste (Weiterleitungen)
# --------------------------------------------------------------------------

def slug_rest(pfad: str) -> str:
    """'/posts/2026-08-21-x(1)/' → 'x'. Datum und Dublettensuffix entfernt."""
    name = str(pfad).rstrip("/").split("/")[-1]
    name = re.sub(r"\(\d+\)$", "", name)
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    return name


def vorschlaege(urls: list[str], wahrheit: dict) -> list[dict]:
    """Aus 404-URLs machbare Weiterleitungs-Kandidaten – ohne zu entscheiden.

    Zuordnung ausschließlich über den datumsbereinigten Slug (Regel A der
    Weiterleitungs-Quelle) oder einen sehr hohen Textähnlichkeitswert. Alles
    darunter bleibt „kein Vorschlag“: Eine falsche Weiterleitung ist schlimmer
    als ein 404, weil sie Nutzer an die falsche Stelle schickt.
    """
    import difflib

    live = wahrheit["indexierbar"]
    rest_index = {}
    for u in live:
        if u.startswith("/posts/"):
            rest_index.setdefault(slug_rest(u), []).append(u)
    out = []
    for url in urls:
        if url in wahrheit["weiterleitungen"]:
            out.append({"url": url, "vorschlag": wahrheit["weiterleitungen"][url],
                        "weg": "bereits entschieden", "regel": "vorhanden", "sicherheit": "-"})
            continue
        if url in wahrheit["entfallen"]:
            out.append({"url": url, "vorschlag": None, "weg": "bewusst 404",
                        "regel": wahrheit["entfallen"][url], "sicherheit": "-"})
            continue
        rest = slug_rest(url)
        treffer = rest_index.get(rest, [])
        if len(treffer) == 1:
            out.append({"url": url, "vorschlag": treffer[0], "weg": "gleicher Slug-Rest",
                        "regel": "A", "sicherheit": "hoch"})
            continue
        if treffer:
            out.append({"url": url, "vorschlag": treffer[0], "weg": "mehrere Kandidaten",
                        "regel": "A", "sicherheit": "prüfen"})
            continue
        naechste = difflib.get_close_matches(rest, list(rest_index), n=1, cutoff=0.82)
        if naechste:
            ziel = rest_index[naechste[0]][0]
            out.append({"url": url, "vorschlag": ziel, "weg": "ähnlicher Slug",
                        "regel": "B", "sicherheit": "prüfen"})
            continue
        out.append({"url": url, "vorschlag": None, "weg": "kein Vorschlag",
                    "regel": "-", "sicherheit": "-"})
    return out


# --------------------------------------------------------------------------
#  Import / Auswertung / Ausgabe
# --------------------------------------------------------------------------

def _json_schreiben(pfad: Path, daten) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(pfad)


def importiere(pfad: Path, ziel: Path = ABDECKUNG, jetzt: dt.datetime | None = None,
               schreiben: bool = True) -> dict:
    """Der Verlauf liegt IMMER neben der Momentaufnahme (`<ziel>/verlauf.jsonl`).
    Sonst würde ein Selbsttest in einem temporären Baum den echten Verlauf
    fortschreiben – und die Prüfung wäre keine Prüfung mehr (Hausregel C15)."""
    """Liest Export, prüft ihn und legt eine Momentaufnahme ab. Ein Lauf = eine Messung."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    export = lade_export(pfad)
    pruef = pruefe_export(export)
    hart = [p for p in pruef if p["schwere"] == "hart"]
    if hart:
        return {"status": "ungueltig", "befunde": pruef, "export": export}
    sortiert = sorted((z for z in export["verlauf"] if z.get("datum")),
                      key=lambda z: z["datum"])
    if not sortiert:
        return {"status": "ungueltig", "befunde": pruef + [{
            "regel": "E12", "schwere": "hart", "text": "Keine Zeile mit Datum."}],
            "export": export}
    datum = sortiert[-1]["datum"]
    snapshot = {
        "schema": SCHEMA,
        "datum": datum,
        "importiert": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quelle": "google-search-console (Abdeckungsbericht, CSV-Export)",
        "metadaten": export["metadaten"],
        "uebersicht": export["uebersicht"],
        "verlauf": sortiert,
        "details": export["details"],
        "dateien": export["dateien"],
        "pruefung": pruef,
    }
    if schreiben:
        _json_schreiben(ziel / f"{datum}.json", snapshot)
        _json_schreiben(ziel / "aktuell.json", snapshot)
        # Eine Zeile je Momentaufnahme, append-only. Wird dieselbe Momentaufnahme
        # erneut eingelesen, bleibt der Verlauf unverändert (Idempotenz).
        verlauf = Path(ziel) / "verlauf.jsonl"
        bekannt = set()
        if verlauf.exists():
            for zeile in verlauf.read_text(encoding="utf-8").splitlines():
                try:
                    bekannt.add(json.loads(zeile).get("datum"))
                except json.JSONDecodeError:
                    continue
        if datum not in bekannt:
            zeile = {
                "datum": datum,
                "importiert": snapshot["importiert"],
                "indexiert": sortiert[-1].get("indexiert"),
                "nicht_indexiert": sortiert[-1].get("nicht_indexiert"),
                "impressionen": sortiert[-1].get("impressionen"),
                "gruende": {klassifiziere(e.get("grund", "")): e.get("seiten")
                            for e in export["uebersicht"]},
            }
            with verlauf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(zeile, ensure_ascii=False, sort_keys=True) + "\n")
    return {"status": "ok", "datum": datum, "befunde": pruef, "snapshot": snapshot}


def lade_snapshot(pfad: Path | None = None) -> dict:
    ziel = Path(pfad) if pfad else AKTUELL
    if not ziel.exists():
        raise FileNotFoundError(
            f"{ziel} fehlt. Zuerst den Search-Console-Export einlesen: "
            "--import <verzeichnis>"
        )
    return json.loads(ziel.read_text(encoding="utf-8"))


def vorheriger_snapshot(datum: str, pfad: Path | None = None) -> dict | None:
    """Der jüngste Verlaufs-Eintrag VOR dem aktuellen Datum – die Vergleichsbasis."""
    quelle = Path(pfad) if pfad else VERLAUF
    if not quelle.exists():
        return None
    kandidaten = []
    for zeile in quelle.read_text(encoding="utf-8").splitlines():
        try:
            eintrag = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if eintrag.get("datum") and eintrag["datum"] < datum:
            kandidaten.append(eintrag)
    return max(kandidaten, key=lambda e: e["datum"]) if kandidaten else None


def auswerten(snapshot: dict, wahrheit: dict | None = None,
              verlauf_pfad: Path | None = None, heute: dt.date | None = None) -> dict:
    """Der vollständige Befund: Kennzahlen, Gründe, Widersprüche, Maßnahmen, Gate.

    Alles, was den Handlungsteil trägt, hängt an derselben Messung: Der
    Kandidatenraum schätzt, wie viel der 404er der Bestand erklären KANN, die
    Triage macht aus einer Detail-Liste eine Arbeitsliste, der Vertrag prüft
    noindex und Gateways, die Priorisierung ordnet die Anfragen, KPI und
    Abnahme machen den Erfolg messbar. Fehlt ein Eingang (kein Build, keine
    Detail-Liste), steht das als Befund da – nicht als erfundene Zahl.
    """
    wahrheit = wahrheit or repo_wahrheit()
    verlinkung = redaktionelle_links()
    kenn = kennzahlen(snapshot, wahrheit, heute)
    # Gezählt werden Inhaltsseiten. Start, Hubs und Rechtsseiten hängen an der
    # Navigation; sie als "unverlinkt" zu führen wäre ein Fehlalarm (und würde
    # den Verlinkungsauftrag mit sinnlosen Zielen füllen).
    inhalt = [u for u in verlinkung["seiten"]
              if u.startswith(("/posts/", "/pillar/")) and u not in HUBS]
    kenn["ohne_inlink"] = len([u for u in inhalt if verlinkung["seiten"][u]["ein"] == 0])
    kenn["ohne_auslink"] = len([u for u in inhalt if verlinkung["seiten"][u]["aus"] == 0])
    kenn["inhaltsseiten"] = len(inhalt)
    kenn["tote_ziele"] = len(tote_ziele())
    kenn["median_auslink"] = verlinkung["median_aus"]
    gruende = befund_gruende(snapshot, wahrheit)
    pruef = snapshot.get("pruefung") or []
    wid = widersprueche(gruende, kenn, wahrheit, pruef)
    auswertung = {
        "schema": SCHEMA,
        "stand": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quellen": {
            "export": snapshot.get("quelle"),
            "datum": snapshot.get("datum"),
            "metadaten": snapshot.get("metadaten"),
            "repo": wahrheit["basis"],
        },
        "kennzahlen": kenn,
        "gruende": gruende,
        "widersprueche": wid,
        "tote_ziele": tote_ziele(),
        "verlinkung": {"ohne_ein": verlinkung["ohne_ein"],
                       "ohne_aus": verlinkung["ohne_aus"],
                       "median_aus": verlinkung["median_aus"],
                       "summe": verlinkung["summe"]},
        "kandidaten": kandidatenraum(wahrheit, snapshot),
        "vertrag": vertrag(wahrheit, wahrheit.get("bau")),
        "prioritaet": prioritaet(wahrheit, verlinkung, snapshot, heute),
        "ursachen": ursachen(kenn, wahrheit, git_beleg_cache()),
        "beweisfragen": beweisfragen(gruende, snapshot, wahrheit),
        "massnahmen": massnahmen(gruende, kenn, wahrheit, snapshot),
        "wahrheit": {
            "indexierbar": wahrheit["anzahl_indexierbar"],
            "noindex": wahrheit["noindex"],
            "gateways": wahrheit["anzahl_gateways"],
            "weiterleitungen": wahrheit["anzahl_weiterleitungen"],
            "entfallen": wahrheit["anzahl_entfallen"],
            "taxonomie_404": wahrheit["taxonomie_404"],
            "sektionen": wahrheit.get("sektionen", {}),
            "robots": wahrheit["robots"],
            "top_nicht_live": wahrheit["top_nicht_live"],
            "befunde": wahrheit["befunde"],
        },
    }
    auswertung["gate"] = gate(auswertung, vorheriger_snapshot(snapshot.get("datum", ""),
                                                             verlauf_pfad))
    auswertung["kpi"] = kpi(verlauf_pfad, kenn)
    auswertung["abnahme"] = abnahme(auswertung)
    auswertung["verlinkungsauftrag"] = verlinkungs_auftrag(wahrheit, verlinkung)
    return auswertung


# --------------------------------------------------------------------------
#  Redaktionelle Verlinkung (Grundlage für M2 und für die Priorisierung)
# --------------------------------------------------------------------------

# Interne Links in Markdown: `[Text](../../posts/x/)`, `[Text](/posts/x/)`,
# `[Text](https://franksfinanzcheck.de/posts/x/)`. Das `(?<!!)` schließt
# Bilder aus – `![alt](…)` ist kein Link und verlinkt nichts.
_MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
_DATUM_PRAEFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _pfad_normalisieren(href: str, quelle: str) -> str | None:
    """Ziel-Link → absoluter Pfad mit Schrägstrich am Ende. None = extern."""
    if not href or href.startswith(("mailto:", "tel:", "#", "javascript:")):
        return None
    if href.startswith(("http://", "https://")):
        if "franksfinanzcheck.de" not in href:
            return None
        href = re.sub(r"^https?://(www\.)?franksfinanzcheck\.de", "", href)
    href = href.split("#")[0].split("?")[0]
    if not href:
        return None
    if not href.endswith("/") and "." not in href.rsplit("/", 1)[-1]:
        href += "/"
    if href.startswith("/"):
        return href
    # relativ auflösen (../../posts/x/ aus /posts/<slug>/)
    teile = (os.path.dirname(quelle.rstrip("/")) + "/" + href).split("/")
    stapel: list[str] = []
    for teil in teile:
        if teil in ("", "."):
            continue
        if teil == "..":
            if stapel:
                stapel.pop()
            continue
        stapel.append(teil)
    return "/" + "/".join(stapel) + "/"


def redaktionelle_links(root: Path = ROOT) -> dict:
    """Eingehende und ausgehende REDAKTIONELLE Links je Seite.

    Warum nicht am Build gemessen: Der Build verlinkt über Template-Blöcke
    (Themenwelten, „Ähnliche Artikel") jede Seite mehrfach. Diese Links zählen
    für Crawler, sagen aber nichts über die redaktionelle Verlinkung – und die
    ist der Hebel, den eine Redaktion tatsächlich bewegen kann. Am 26.10.2026
    waren 70 von 99 Seiten über Template-Links erreichbar, aber 14 ohne einen
    einzigen redaktionellen Inlink; die 14 waren fast alle aus September und
    Oktober – also genau die Seiten, die Google nicht indexiert.

    Rückgabe: {"seiten": {url: {"aus": n, "ein": n, "quellen": [...]}},
               "ohne_ein": [...], "ohne_aus": [...], "Median": …}
    """
    cdir = Path(root) / "content"
    seiten: dict[str, str] = {}
    for pfad in sorted(list(cdir.rglob("index.md")) + list(cdir.rglob("_index.md"))):
        fm = _frontmatter(pfad)
        if _fm_wahr(fm, "draft"):
            continue
        rel = pfad.parent.relative_to(cdir).as_posix()
        url = _fm_wert(fm, "url") or ("/" if rel == "." else f"/{rel}/")
        if not url.endswith("/"):
            url += "/"
        seiten[url] = pfad.read_text(encoding="utf-8", errors="replace")

    ein: dict[str, list[str]] = {u: [] for u in seiten}
    aus: dict[str, set[str]] = {}
    for quelle, inhalt in seiten.items():
        ziele: set[str] = set()
        for href in _MD_LINK.findall(inhalt):
            ziel = _pfad_normalisieren(href, quelle)
            if ziel and ziel in seiten and ziel != quelle:
                ziele.add(ziel)
        aus[quelle] = ziele
        for ziel in ziele:
            ein[ziel].append(quelle)

    werte = sorted(len(v) for v in aus.values())
    return {
        "seiten": {u: {"aus": len(aus[u]), "ein": len(ein[u]), "quellen": sorted(ein[u])}
                   for u in seiten},
        "ohne_ein": sorted(u for u in seiten if not ein[u]),
        "ohne_aus": sorted(u for u in seiten if not aus[u]),
        "median_aus": werte[len(werte) // 2] if werte else 0,
        "summe": sum(werte),
    }


# --------------------------------------------------------------------------
#  Kandidatenraum: wie viele der gemeldeten 404er KANN der Bestand erklären?
# --------------------------------------------------------------------------

def kandidaten(pfad_rest: str) -> list[str]:
    """Plausible URL-Varianten eines Slugs (nur Formen, die es real gab).

    Der Bestand kennt drei dokumentierte Alt-Formen (siehe
    `data/weiterleitungen.yaml`): Ordner ohne Datumspräfix
    (`/posts/<slug>/`), Ordner mit abweichendem Datum (`/posts/2026-08-28-…/`
    bei `/posts/2026-08-26-…/`) und Dubletten mit `(1)`. Genau diese Formen
    erzeugt der Kandidatenraum – keine Fantasie-URLs, keine Slug-Rateverfahren.
    """
    rest = _DATUM_PRAEFIX.sub("", str(pfad_rest).rstrip("/").split("/")[-1])
    if not rest:
        return []
    return [f"/posts/{rest}/", f"/posts/{rest}(1)/"]


def kandidatenraum(wahrheit: dict, snapshot: dict | None = None,
                   root: Path = ROOT) -> dict:
    """Obergrenze dessen, was der Repo-Bestand an 404ern erklären kann.

    Das ist bewusst eine **Obergrenze**, kein Nachweis: Sie zählt jede URL, die
    aus einer heute live stehenden Seite ableitbar ist und nicht live ist. Ob
    Google genau diese URL je gesehen hat, sagt nur die Detail-Liste.
    """
    live = set(wahrheit["indexierbar"])
    weiter = wahrheit["weiterleitungen"]
    entfallen = wahrheit["entfallen"]

    bekannt: dict[str, str] = {}
    # 1) dokumentierte Alt-URLs (Weiterleitung + bewusst entfallen)
    for url in list(weiter) + list(entfallen):
        bekannt[url] = "dokumentiert"
    # 2) Taxonomie (abgeschaltet, aber in der Historie)
    for url in wahrheit["taxonomie_404"]:
        bekannt.setdefault(url, "taxonomie")
    # 3) Varianten der live stehenden Seiten
    for url in live:
        if not url.startswith("/posts/"):
            continue
        for variante in kandidaten(url):
            if variante not in live:
                bekannt.setdefault(variante, "variante")
        for alt in weiter:
            if _DATUM_PRAEFIX.sub("", alt.rstrip("/").split("/")[-1]) == \
                    _DATUM_PRAEFIX.sub("", url.rstrip("/").split("/")[-1]):
                bekannt.setdefault(alt, "dokumentiert")
    # 4) Belege aus dem Snapshot und den Top-Seiten
    if snapshot:
        for url in snapshot.get("urls") or []:
            if str(url).endswith("/") and url not in live:
                bekannt.setdefault(url, "snapshot")
    for eintrag in wahrheit.get("top_nicht_live") or []:
        bekannt.setdefault(eintrag["url"], "top-seiten")

    offen = sorted(u for u in bekannt
                   if u not in live and u not in weiter and u not in entfallen)
    return {
        "gesamt": len(bekannt),
        "davon_dokumentiert": len([u for u in bekannt if u in weiter or u in entfallen]),
        "davon_taxonomie": len([u for u in bekannt if u in set(wahrheit["taxonomie_404"])]),
        "davon_ohne_entscheidung": len(offen),
        "ohne_entscheidung": offen[:400],
        "nach_herkunft": {herkunft: sum(1 for h in bekannt.values() if h == herkunft)
                          for herkunft in sorted(set(bekannt.values()))},
    }


# --------------------------------------------------------------------------
#  Triage der Detail-Listen (M1)
# --------------------------------------------------------------------------

# Was bei welchem Grund zu tun ist. Der Text erscheint in der Triage-Liste und
# ist bewusst eine HANDLUNG, keine Kategorie: Wer die Liste abarbeitet, soll
# nicht mehr nachdenken müssen, was gemeint ist.
AKTION = {
    # Ein unentschiedener 404 ist kein erledigter 404: Er steht im Bericht, ist
    # aber nie bewertet worden. Deshalb P2 (entscheiden), nicht P3 (belassen).
    "not_found": ("P2", "entscheiden: Weiterleitung oder bewusst 404",
                  "Kein Nachfolger, keine Nachfrage in den Top-Seiten."),
    "soft_404": ("P2", "Inhalt oder Weiterleitung", "Seite antwortet leer."),
    "noindex": ("P1", "noindex prüfen", "Absicht bestätigen oder Tag entfernen."),
    "robots_blocked": ("P3", "Sperre belassen", "Gateway, keine Inhaltsseite."),
    "redirect": ("P3", "Weiterleitung belassen", "Meta-Refresh, kein 301."),
    "alternate_canonical": ("P3", "Canonical belassen", "Google hat die Dublette erkannt."),
    "duplicate_canonical": ("P1", "Canonical setzen", "Zwei Seiten, eine Absicht."),
    "crawled_not_indexed": ("P2", "Redaktion prüfen", "Substanz, Einzigartigkeit, Absicht."),
    "discovered_not_indexed": ("P2", "Interne Verlinkung", "Kein redaktioneller Inlink?"),
    "server_error": ("P0", "Technik sofort", "Serverfehler."),
    "redirect_error": ("P1", "Kette auflösen", "Weiterleitung zeigt auf Weiterleitung."),
    "unknown": ("P0", "Grund ansehen", "Unbekannter GSC-Grund."),
}


def entwurfs_slugs(root: Path = ROOT) -> dict[str, str]:
    """Slug (ohne Datumspräfix) → Datei eines Entwurfs.

    Ein 404 auf eine URL, deren Artikel als Entwurf im Repo liegt, ist kein
    Rätsel: Die Seite existiert, sie wird nur nicht gebaut. Genau diese Fälle
    sind die billigsten – eine Entscheidung (veröffentlichen) statt einer
    Weiterleitung.
    """
    out: dict[str, str] = {}
    for pfad in (Path(root) / "content" / "posts").glob("*/index.md"):
        fm = _frontmatter(pfad)
        if not _fm_wahr(fm, "draft"):
            continue
        out[_DATUM_PRAEFIX.sub("", pfad.parent.name)] = pfad.parent.name
    return out


def triage(urls: list[dict], wahrheit: dict, kenn: dict,
           verlinkung: dict | None = None) -> dict:
    """Macht aus gemeldeten URLs eine abarbeitbare Liste.

    Eingabe ist die Detail-Liste der Search Console (`{"url", "grund"}`), wie
    `lade_export` sie liefert. Jede URL bekommt genau eine Aktion, eine
    Priorität und einen Beleg – und, wo möglich, einen Weiterleitungsvorschlag.
    Einträge, die der Bestand schon entschieden hat, werden als solche geführt:
    Eine Triage, die bereits getroffene Entscheidungen erneut vorschlägt, wird
    nach dem zweiten Lauf ignoriert.
    """
    live = set(wahrheit["indexierbar"])
    weiter = wahrheit["weiterleitungen"]
    entfallen = wahrheit["entfallen"]
    nachfrage = {e["url"]: e for e in wahrheit.get("top_nicht_live") or []}
    ohne_inlink = set((verlinkung or {}).get("ohne_ein") or [])
    entwuerfe = entwurfs_slugs()

    zeilen: list[dict] = []
    for eintrag in urls:
        url = _pfad_normalisieren(eintrag.get("url", ""), "/") or eintrag.get("url", "")
        grund = eintrag.get("grund") or ""
        schluessel = klassifiziere(grund)
        prio, aktion, hinweis = AKTION.get(schluessel, AKTION["unknown"])
        ziel = None
        beleg = ""
        if url in live:
            prio, aktion = "P3", "im Bestand – nichts tun"
            beleg = "URL wird gebaut und steht in der Sitemap."
        elif url in weiter:
            prio, aktion, ziel = "P3", "bereits entschieden (Weiterleitung)", weiter[url]
            beleg = "Eintrag in data/weiterleitungen.yaml."
        elif url in entfallen:
            prio, aktion = "P3", "bereits entschieden (bewusst 404)"
            beleg = f"Eintrag in data/url_entfallen.yaml, Regel {entfallen[url]}."
        elif schluessel == "not_found":
            vorschlag = vorschlaege([url], wahrheit)[0]
            if nachfrage.get(url):
                prio, aktion = "P1", "Weiterleitung prüfen (Nachfrage belegt)"
                beleg = (f"{nachfrage[url]['impressionen']} Impressionen bei Position "
                         f"{nachfrage[url]['position']} – die URL wird noch gefunden.")
            elif _DATUM_PRAEFIX.sub("", url.rstrip("/").split("/")[-1]) in entwuerfe:
                slug = entwuerfe[_DATUM_PRAEFIX.sub("", url.rstrip("/").split("/")[-1])]
                prio, aktion = "P1", "Seite liegt als Entwurf – veröffentlichen"
                beleg = f"`content/posts/{slug}/` ist `draft: true`; die Seite existiert."
            elif vorschlag.get("vorschlag"):
                prio, aktion, ziel = "P2", f"Vorschlag ({vorschlag['weg']})", vorschlag["vorschlag"]
                beleg = f"Slug-Deckung, Sicherheit {vorschlag['sicherheit']}."
            elif not url.startswith(("/posts/", "/pillar/")):
                prio, aktion = "P3", "belassen (keine Inhalts-URL)"
                beleg = "Keine Inhaltsseite – Taxonomie, Asset oder Fremdpfad."
            else:
                beleg = "Kein Nachfolger im Bestand, keine Nachfrage in den Top-Seiten."
        elif schluessel == "discovered_not_indexed" and url in ohne_inlink:
            prio, aktion = "P1", "Inlink fehlt – Redaktion verlinken"
            beleg = "Kein redaktioneller Inlink im Bestand (Template-Links zählen nicht)."
        elif schluessel == "discovered_not_indexed":
            beleg = "Mindestens ein redaktioneller Inlink vorhanden – Crawl-Budget."
        elif schluessel == "noindex" and url in set(wahrheit["noindex"]):
            prio, aktion = "P3", "noindex ist Vertrag"
            beleg = "Steht so im Inhalt (robotsNoIndex: true)."
        zeilen.append({"url": url, "grund": grund, "schluessel": schluessel,
                       "prioritaet": prio, "aktion": aktion, "ziel": ziel,
                       "beleg": beleg or hinweis})

    rang = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    zeilen.sort(key=lambda z: (rang.get(z["prioritaet"], 9), z["url"]))
    zaehler: dict[str, int] = {}
    for z in zeilen:
        zaehler[z["prioritaet"]] = zaehler.get(z["prioritaet"], 0) + 1
    return {
        "anzahl": len(zeilen),
        "nach_prioritaet": dict(sorted(zaehler.items())),
        "offen": [z for z in zeilen if z["prioritaet"] in ("P0", "P1", "P2")],
        "entschieden": [z for z in zeilen if z["prioritaet"] == "P3"],
        "zeilen": zeilen,
    }


def triage_markdown(t: dict, quelle: str) -> str:
    z = [f"## Triage ({quelle})", "",
         f"{t['anzahl']} gemeldete URLs · "
         + " · ".join(f"{k}: {v}" for k, v in t["nach_prioritaet"].items()), "",
         "| Prio | URL | Grund | Aktion | Beleg |", "|---|---|---|---|---|"]
    for zeile in t["offen"][:80]:
        ziel = f" → `{zeile['ziel']}`" if zeile["ziel"] else ""
        z.append(f"| {zeile['prioritaet']} | `{zeile['url']}` | {zeile['grund'][:40]} | "
                 f"{zeile['aktion']}{ziel} | {zeile['beleg'][:80]} |")
    if len(t["offen"]) > 80:
        z.append(f"| … | *{len(t['offen']) - 80} weitere* | | | |")
    z.append("")
    z.append(f"Bereits entschieden (nichts zu tun): {len(t['entschieden'])}.")
    return "\n".join(z)


# --------------------------------------------------------------------------
#  Vertrag: noindex-Bestand und Gateways (M5, M6)
# --------------------------------------------------------------------------

# Die noindex-Seiten sind eine ENTSCHEIDUNG, kein Zufall. Sie stehen hier mit
# Begründung; die Wache vergleicht den Inhalt dagegen. Kommt eine Seite ohne
# Vertrag hinzu, ist das ein Befund – und zwar der gute Fall: Jemand hat die
# Entscheidung bewusst getroffen und trägt sie hier ein.
NOINDEX_VERTRAG = {
    "/suche/": "Volltextsuche ohne eigenen Inhalt; Suchergebnisse sollen nicht indexiert werden.",
    "/newsletter/": "Anmeldefunnel: kein redaktioneller Inhalt, gehört nicht in den Index.",
    "/newsletter/bestaetigung/": "Double-Opt-In-Bestätigung: transaktionale Seite.",
    "/newsletter/abmelden/": "Abmeldung: transaktionale Seite.",
    "/newsletter/praeferenzen/": "Präferenzen: transaktionale Seite.",
    "/kalender/": "Veröffentlichungskalender: Funktionsfläche aus static/.",
}


def vertrag(wahrheit: dict, build: dict | None = None) -> dict:
    """Prüft die drei Verträge: noindex-Bestand, Gateways, robots.

    Das ist die Antwort auf M5 und M6: Die Meldung „durch noindex
    ausgeschlossen“ darf sich nur dann ändern, wenn sich der Vertrag ändert.
    """
    funde: list[dict] = []
    ist = set(wahrheit["noindex"])

    # Der Kalender liegt in static/ und trägt sein noindex selbst – er steht im
    # Vertrag, aber nicht im content-Baum. Er darf deshalb fehlen, ohne dass
    # das ein Leck ist; umgekehrt muss jede noindex-Seite im Inhalt einen
    # Vertragseintrag haben.
    inhalt_ist = {u for u in ist}
    ohne_vertrag = sorted(u for u in inhalt_ist if u not in NOINDEX_VERTRAG)
    if ohne_vertrag:
        funde.append({
            "regel": "V1", "schwere": "hart",
            "text": ("noindex ohne Vertragseintrag: " + ", ".join(ohne_vertrag)
                     + ". Entweder Tag entfernen oder in NOINDEX_VERTRAG begründen."),
        })
    erwartet_inhalt = {u for u in NOINDEX_VERTRAG if u not in ("/kalender/",)}
    fehlt = sorted(erwartet_inhalt - inhalt_ist)
    if fehlt:
        funde.append({
            "regel": "V2", "schwere": "hart",
            "text": ("Vertrag nennt noindex-Seiten, die es nicht (mehr) gibt: "
                     + ", ".join(fehlt) + ". Vertrag oder Inhalt ist veraltet."),
        })

    gateways = set(wahrheit["gateways"])
    gebaut = set((build or {}).get("gateway_liste") or [])
    if gebaut and gebaut != gateways:
        funde.append({
            "regel": "V3", "schwere": "hart",
            "text": (f"Gateways im Build ({len(gebaut)}) und in static/go/ "
                     f"({len(gateways)}) weichen ab."),
        })
    if gateways and not wahrheit["robots"]["go_gesperrt"]:
        funde.append({"regel": "V4", "schwere": "hart",
                      "text": "robots.txt sperrt /go/ nicht."})
    if gateways and wahrheit["robots"]["sperrt_go_gruppen"] < 1:
        funde.append({"regel": "V4", "schwere": "hart",
                      "text": "Keine Roboter-Gruppe sperrt /go/."})

    return {"status": "rot" if [f for f in funde if f["schwere"] == "hart"] else "gruen",
            "funde": funde,
            "noindex_ist": sorted(inhalt_ist),
            "noindex_vertrag": dict(sorted(NOINDEX_VERTRAG.items())),
            "gateways": sorted(gateways)}


# --------------------------------------------------------------------------
#  Priorisierung und Verlinkungsauftrag (M2)
# --------------------------------------------------------------------------

def _nachfrage_karte(kenn_top: list[dict] | None, root: Path = ROOT) -> dict:
    pfad = Path(root) / "data" / "gsc" / "top_seiten_28t.json"
    if not pfad.exists():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    karte = {}
    for eintrag in daten if isinstance(daten, list) else []:
        url = _pfad_normalisieren(str(eintrag.get("seite", "")), "/")
        if url:
            karte[url] = {"impressionen": eintrag.get("impressions") or 0,
                          "klicks": eintrag.get("clicks") or 0,
                          "position": eintrag.get("position")}
    return karte


def prioritaet(wahrheit: dict, verlinkung: dict, snapshot: dict | None = None,
               heute: dt.date | None = None, root: Path = ROOT) -> dict:
    """Welche Seite zuerst? (M2 – der operative Kern)

    Score aus vier belegbaren Größen, keine Blackbox:
      Nachfrage  3 × (Impressionen in 28 Tagen, gedeckelt) + Positionsbonus
      Verlinkung 2 × (fehlende redaktionelle Inlinks)
      Frische    1 × (Tage seit lastmod, gedeckelt)
      Absicht    1 × (Ratgeber/Pillar/Werkzeug vor Rechtsseite)
    Ausgabe ist eine Wellen-Reihenfolge für `gsc_indexierung.py` (200/Tag) –
    nicht „alle 99 gleichzeitig anfragen“, was Google als Muster erkennt und
    womit man das Tageskontingent an die falschen Seiten verliert.
    """
    heute = heute or dt.date.today()
    nachfrage = _nachfrage_karte(None, root)
    oeffentlich = _oeffentlich(root)
    sitemap = sitemap_seiten(oeffentlich / "sitemap.xml") or wahrheit["indexierbar"]
    lastmod = _lastmod_karte(oeffentlich / "sitemap.xml")
    seiten = verlinkung.get("seiten") or {}

    zeilen = []
    for url in sitemap:
        info = seiten.get(url) or {"ein": 0, "aus": 0}
        k = nachfrage.get(url) or {}
        impressionen = k.get("impressionen") or 0
        position = k.get("position")
        ein = info.get("ein") or 0
        tage = None
        if lastmod.get(url):
            try:
                tage = (heute - dt.date.fromisoformat(lastmod[url])).days
            except ValueError:
                tage = None
        # Navigationsseiten (Start, Hubs, Rechtsseiten) haben naturgemäß keinen
        # redaktionellen Inlink – sie zu „reparieren“ wäre ein Fehlalarm.
        inhaltsseite = (url.startswith(("/posts/", "/pillar/"))
                        and url not in HUBS)
        wert = min(impressionen, 30) / 3.0                      # 0 … 10
        if position:
            wert += max(0.0, (30 - min(position, 30)) / 30 * 3)   # 0 … 3
        if inhaltsseite:
            wert += 6.0 if ein == 0 else (3.0 if ein == 1 else 0.0)
        if tage is not None:
            wert += max(0.0, (60 - min(tage, 60)) / 60 * 3)      # 0 … 3
        if url.startswith(("/pillar/", "/posts/", "/werkzeuge/")):
            wert += 1.0
        if not inhaltsseite:
            wert -= 1.0
        elif url.startswith(("/impressum/", "/datenschutz/", "/transparenz/")):
            wert -= 2.0
        zeilen.append({"url": url, "score": round(wert, 2), "impressionen": impressionen,
                       "position": position, "inlinks": ein, "outlinks": info.get("aus"),
                       "lastmod_tage": tage,
                       "grund": ("kein redaktioneller Inlink" if ein == 0
                                 else ("nur ein Inlink" if ein == 1 else "verlinkt"))})
    zeilen.sort(key=lambda z: (-z["score"], z["url"]))
    # Welle 1 = die 40 dringendsten Seiten (Tageskontingent 200, aber jede
    # Anfrage soll auf eine Seite fallen, die davon profitiert). Welle 2 folgt.
    welle1 = [z["url"] for z in zeilen[:40]]
    return {
        "stand": heute.isoformat(),
        "seiten": zeilen,
        "welle1": welle1,
        "welle1_absolut": [SITE + u for u in welle1],
        "welle2": [z["url"] for z in zeilen if z["url"] not in set(welle1)],
        "ohne_inlink": len([z for z in zeilen if z["inlinks"] == 0]),
        "kontingent": ANFRAGEN_PRO_TAG,
    }


def _lastmod_karte(sitemap: Path) -> dict:
    if not Path(sitemap).exists():
        return {}
    import xml.etree.ElementTree as ET

    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    try:
        baum = ET.parse(sitemap)
    except ET.ParseError:
        return {}
    out = {}
    for eintrag in baum.getroot().iter(f"{ns}url"):
        loc = eintrag.find(f"{ns}loc")
        lm = eintrag.find(f"{ns}lastmod")
        if loc is None or lm is None or not loc.text or not lm.text:
            continue
        out[_pfad_normalisieren(loc.text.strip(), "/") or ""] = lm.text.strip()[:10]
    return out


def verlinkungs_auftrag(wahrheit: dict, verlinkung: dict, grenze: int = 2,
                        max_je_quelle: int = 1, root: Path = ROOT) -> list[dict]:
    """Für jede Seite mit zu wenigen redaktionellen Inlinks: konkrete Quellen.

    Ausgewählt wird nicht „irgendein Artikel“, sondern der inhaltlich nächste
    mit freier Kapazität: gleiche Sektion (Pillar) zuerst, dann ähnlicher Slug,
    dann die Seite mit den meisten ausgehenden Links (Verteiler-Seiten). Der
    Goldkorridor (max. 9 interne Links je Artikel) bleibt hart.
    """
    import difflib

    seiten = verlinkung.get("seiten") or {}
    pillar = _pillar_karte()
    # Nur Inhaltsseiten: Start, Hubs und Rechtsseiten werden über Navigation
    # verlinkt, nicht über „Weiterlesen“.
    offen = [u for u in (wahrheit["indexierbar"])
             if u.startswith(("/posts/", "/pillar/")) and u not in HUBS
             and (seiten.get(u, {}).get("ein") or 0) < grenze]
    offen.sort(key=lambda u: (seiten.get(u, {}).get("ein") or 0, u))

    auftrag: list[dict] = []
    belegt: dict[str, int] = {}
    for ziel in offen:
        braucht = grenze - (seiten.get(ziel, {}).get("ein") or 0)
        kandidaten_q = []
        for quelle, info in seiten.items():
            if quelle == ziel or (info.get("aus") or 0) >= 8:
                continue
            if not quelle.startswith(("/posts/", "/pillar/")) or quelle in HUBS:
                continue
            # Der Goldkorridor ist hart: 9 Links je Artikel, und der Guard
            # zählt Vorkommen. Wer bei 9 steht, bekommt keinen Zuwachs.
            datei = _datei_zu_url(quelle, root)
            if datei and datei.exists():
                if post_links_gezaehlt(datei.read_text(encoding="utf-8",
                                                       errors="replace")) >= 9:
                    continue
            if belegt.get(quelle, 0) >= max_je_quelle:
                continue
            if ziel in (info.get("quellen") or []):
                continue
            if quelle in (wahrheit["noindex"] + ["/404/"]):
                continue
            gleich = pillar.get(quelle) == pillar.get(ziel) and pillar.get(ziel)
            aehnlich = difflib.SequenceMatcher(
                None, _DATUM_PRAEFIX.sub("", quelle.rstrip("/").split("/")[-1]),
                _DATUM_PRAEFIX.sub("", ziel.rstrip("/").split("/")[-1])).ratio()
            rang = (0 if gleich else 1, -aehnlich, -(info.get("aus") or 0))
            kandidaten_q.append((rang, quelle))
        kandidaten_q.sort()
        for _rang, quelle in kandidaten_q[:braucht]:
            belegt[quelle] = belegt.get(quelle, 0) + 1
            auftrag.append({"ziel": ziel, "quelle": quelle,
                            "grund": ("gleicher Pillar" if pillar.get(quelle) == pillar.get(ziel)
                                      else "ähnliches Thema"),
                            "inlinks_jetzt": seiten.get(ziel, {}).get("ein") or 0})
    return auftrag


def _pillar_karte(root: Path = ROOT) -> dict:
    """URL → Pillar (aus dem Frontmatter). Grundlage der Themen-Nachbarschaft."""
    cdir = Path(root) / "content"
    karte = {}
    for pfad in cdir.rglob("index.md"):
        fm = _frontmatter(pfad)
        wert = _fm_wert(fm, "pillar")
        if not wert:
            continue
        rel = pfad.parent.relative_to(cdir).as_posix()
        url = _fm_wert(fm, "url") or f"/{rel}/"
        if not url.endswith("/"):
            url += "/"
        karte[url] = wert
    return karte


def anker_kurz(titel: str, grenze: int = 6) -> str:
    """Titel → kurzer Anker für die „Weiterlesen“-Zeile.

    Die Zeile ist eine kuratierte Liste, kein Fließtext: Ein voller Titel mit
    Untertitel („Bankgebühren senken: 7 Schritte zum günstigeren Konto“) macht
    sie unlesbar. Geschnitten wird am Doppelpunkt, dann an der Wortgrenze –
    der Anker bleibt immer ein Teil des echten Titels, nie eine Erfindung.
    """
    text = (titel or "").split(":")[0].split(" – ")[0].strip()
    woerter = text.split()
    if len(woerter) > grenze:
        text = " ".join(woerter[:grenze])
    return text or (titel or "").strip()


def link_einfuegen(pfad: Path, ziel_url: str, anker: str) -> tuple[bool, str]:
    """Hängt einen redaktionellen Link an die „Weiterlesen“-Zeile.

    Warum genau dort: Jeder Artikel dieses Blogs endet mit einer kuratierten
    Zeile `**Weiterlesen:** …`. Ein Link dort ist stilkonform, für den Leser
    sichtbar und – anders als ein Satz mitten im Fließtext – keine
    redaktionelle Aussage, die eine Maschine nicht treffen darf. Fehlt die
    Zeile, wird NICHTS eingefügt (dann entscheidet die Redaktion).
    """
    inhalt = pfad.read_text(encoding="utf-8", errors="replace")
    if ziel_url in inhalt:
        return False, "Ziel steht bereits im Artikel"
    treffer = re.search(r"^\*\*Weiterlesen:\*\*.*$", inhalt, re.M)
    if not treffer:
        return False, "keine „Weiterlesen“-Zeile"
    # Relative Form wie im Bestand: aus /posts/<slug>/ zwei Ebenen hoch.
    rest = ziel_url.lstrip("/").rstrip("/")
    neu = treffer.group(0).rstrip() + f" · [{anker}]({'../../' + rest}/)"
    ersetzt = inhalt[:treffer.start()] + neu + inhalt[treffer.end():]
    if ersetzt.count("[") <= inhalt.count("["):
        return False, "Änderung hätte nichts hinzugefügt"
    pfad.write_text(ersetzt, encoding="utf-8")
    return True, "eingefügt"


def tote_ziele(root: Path = ROOT) -> list[dict]:
    """Interne Links auf Seiten, die nicht gebaut werden (Entwurf, gelöscht).

    Das Rendering mildert sie ab (`render-link.html` gibt den Ankertext als
    Klartext aus), also entsteht daraus kein 404 – aber die Verlinkung ist
    wirkungslos: Der Text steht da, der Link fehlt. Für die Redaktion ist das
    eine Entscheidung (veröffentlichen oder entlinken), keine Panne.
    """
    cdir = Path(root) / "content"
    alle: dict[str, tuple[bool, str]] = {}
    for pfad in list(cdir.rglob("index.md")) + list(cdir.rglob("_index.md")):
        text = pfad.read_text(encoding="utf-8", errors="replace")
        fm, _, _ = text.partition("\n---")
        rel = pfad.parent.relative_to(cdir).as_posix()
        url = _fm_wert(fm, "url") or ("/" if rel == "." else f"/{rel}/")
        if not url.endswith("/"):
            url += "/"
        alle[url] = (_fm_wahr(fm, "draft"), text)
    live = {u for u, (draft, _t) in alle.items() if not draft}
    tot: dict[str, list[str]] = {}
    for url, (draft, text) in alle.items():
        if draft:
            continue
        for href in _MD_LINK.findall(text):
            ziel = _pfad_normalisieren(href, url)
            if ziel and ziel in alle and ziel not in live:
                tot.setdefault(ziel, []).append(url)
    return [{"ziel": z, "quellen": sorted(q)} for z, q in sorted(tot.items())]


def post_links_gezaehlt(inhalt: str) -> int:
    """Interne Post-Links so gezählt, wie `link_density_guard.py` sie zählt.

    Der Guard zählt VORKOMMEN der Form `[…](../../posts/…)`, nicht eindeutige
    Ziele – und er lässt Pillar-Links aus. Wer mit einer eigenen Zählweise
    einfügt, schiebt Artikel über den Goldkorridor (am 26.10.2026: fünf
    Artikel bei 10 statt 9). Deshalb dieselbe Regel, inklusive der absoluten
    Schreibweise, die der Guard (noch) nicht kennt.
    """
    relativ = len(re.findall(r"(?<!!)\[[^\]]*\]\(\.\./\.\./posts/[^)]+\)", inhalt))
    absolut = len(re.findall(r"(?<!!)\[[^\]]*\]\((?:https://franksfinanzcheck\.de)?/posts/[^)]+\)",
                             inhalt))
    return relativ + absolut


def _titel_karte(root: Path = ROOT) -> dict:
    """URL → Titel (für den Ankertext). Ohne Titel kein Link."""
    cdir = Path(root) / "content"
    karte = {}
    for pfad in cdir.rglob("index.md"):
        fm = _frontmatter(pfad)
        titel = _fm_wert(fm, "title")
        if not titel:
            continue
        rel = pfad.parent.relative_to(cdir).as_posix()
        url = _fm_wert(fm, "url") or f"/{rel}/"
        if not url.endswith("/"):
            url += "/"
        karte[url] = titel
    return karte


def _datei_zu_url(url: str, root: Path = ROOT) -> Path | None:
    """URL → Quelldatei (`content/<rel>/index.md`)."""
    cdir = Path(root) / "content"
    rel = url.strip("/")
    for kandidat in (cdir / rel / "index.md", cdir / rel / "_index.md"):
        if kandidat.exists():
            return kandidat
    # `url:`-Frontmatter kann von der Ordnerstruktur abweichen
    for pfad in cdir.rglob("index.md"):
        if (_fm_wert(_frontmatter(pfad), "url") or "").rstrip("/") == url.rstrip("/"):
            return pfad
    return None


def _historie_schreiben(getan: list[tuple[dict, str]]) -> None:
    """Beleg je eingefügtem Link – append-only, damit ein Lauf nachvollziehbar bleibt."""
    if not getan:
        return
    ziel = ROOT / "data" / "verlinkung_history.jsonl"
    jetzt = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with ziel.open("a", encoding="utf-8") as fh:
        for posten, _meldung in getan:
            fh.write(json.dumps({"ts": jetzt, "quelle": posten["quelle"],
                                 "ziel": posten["ziel"],
                                 "grund": posten.get("grund")},
                                ensure_ascii=False, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
#  KPI, Abnahme (M9) und Ursachen eines Sprungs (M7)
# --------------------------------------------------------------------------

def kpi(verlauf_pfad: Path | None = None, kenn: dict | None = None) -> dict:
    """Wochenbericht: die Kennzahlen, die eine Agentur montags zeigt."""
    quelle = Path(verlauf_pfad) if verlauf_pfad else VERLAUF
    reihen = []
    if quelle.exists():
        for zeile in quelle.read_text(encoding="utf-8").splitlines():
            try:
                reihen.append(json.loads(zeile))
            except json.JSONDecodeError:
                continue
    reihen.sort(key=lambda r: r.get("datum") or "")
    kenn = kenn or {}
    heute_kenn = dict(kenn)
    if reihen:
        letzte = reihen[-1]
        heute_kenn.setdefault("stand_datum", letzte.get("datum"))
        heute_kenn.setdefault("indexiert", letzte.get("indexiert"))
        heute_kenn.setdefault("nicht_indexiert", letzte.get("nicht_indexiert"))
    return {
        "reihen": reihen,
        "aktuell": heute_kenn,
        "wochen": [{"datum": r.get("datum"), "indexiert": r.get("indexiert"),
                    "nicht_indexiert": r.get("nicht_indexiert")} for r in reihen[-8:]],
    }


def abnahme(a: dict) -> list[dict]:
    """Die Abnahmekriterien aus dem Bericht – maschinell geprüft.

    Ein Kriterium ohne Datum ist ein Wunsch. Jedes hier trägt: Ziel, Status,
    Messgröße und – wenn offen – was fehlt. Geprüft wird nur, was das Repo
    messen kann; alles andere steht als „offen (menschlich)“ da.
    """
    k = a.get("kennzahlen", {})
    g = a.get("gate", {})
    gruende = {x.get("schluessel"): x for x in a.get("gruende", [])}
    offen_404 = (gruende.get("not_found") or {}).get("offen")
    alter = k.get("export_alter_tage")
    quote = k.get("quote_indexiert")

    def eintrag(kriterium, ziel, status, messung, naechster_schritt=""):
        return {"kriterium": kriterium, "ziel": ziel, "status": status,
                "messung": messung, "naechster_schritt": naechster_schritt}

    ergebnis = [
        eintrag("Gate grün (kein Rückschritt, kein Widerspruch)", "sofort",
                "erfuellt" if g.get("status") == "gruen" else "offen",
                f"Gate: {g.get('status')}",
                "" if g.get("status") == "gruen" else "Widersprüche im Befund abarbeiten"),
        eintrag("Abdeckungsbefund nicht älter als 14 Tage", "laufend",
                "erfuellt" if (alter is not None and alter <= 14) else "offen",
                f"Stand {k.get('stand_datum')} ({alter} Tage alt)",
                "Export einlesen (`--import`)"),
        eintrag("404er mit Nachfrage triagiert", "sofort",
                "offen" if offen_404 else "erfuellt",
                f"{offen_404} ohne Erklärung im Bestand",
                "Detail-Liste `Nicht gefunden (404).csv` einlesen"),
        eintrag("Indexquote steigt", "14 Tage",
                "unbekannt" if quote is None or len((a.get("kpi") or {}).get("reihen") or []) < 2
                else "offen",
                f"{quote} % bei {len((a.get('kpi') or {}).get('reihen') or [])} Momentaufnahme(n)",
                "zweite Momentaufnahme nötig, dann Vorlauf-Vergleich"),
        eintrag("Seiten ohne redaktionellen Inlink", "30 Tage",
                "offen" if (k.get("ohne_inlink") or 0) else "erfuellt",
                f"{k.get('ohne_inlink')} Seiten",
                "Verlinkungsauftrag (`--verlinkung --apply`)"),
    ]
    return ergebnis


def git_ereignisse(von: dt.date, bis: dt.date, root: Path = ROOT,
                   max_commits: int = 500) -> dict:
    """Was hat das Repo an diesen Tagen geändert? Beleg statt Vermutung.

    Ein Sprung in der Search Console hat eine Ursache – entweder im Repo oder
    außerhalb. Diese Funktion liefert den Repo-Teil: je Tag die Zahl der
    Commits, die berührten Content-Dateien und den Saldo der `draft:`-Flags.
    Der Saldo ist die entscheidende Größe: Was auf Entwurf steht, wird nicht
    gebaut, steht nicht in der Sitemap und kann nicht im Index bleiben.

    Grenze: In einem Shallow-Clone (CI-Standard) reicht die Historie nicht
    hinter den Klon-Zeitpunkt zurück. Das wird gemeldet, nicht verschwiegen –
    für den Belegweg muss der Job mit `fetch-depth: 0` auschecken.
    """
    import subprocess

    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(root), *args],
                                  capture_output=True, text=True, timeout=120).stdout
        except (OSError, subprocess.SubprocessError):
            return ""

    shallow = git("rev-parse", "--is-shallow-repository").strip() == "true"
    protokoll = git("log", f"--since={von.isoformat()} 00:00", f"--until={bis.isoformat()} 23:59",
                    "--format=%H|%ad|%s", "--date=short").strip().splitlines()
    if not protokoll:
        return {"verfuegbar": False, "shallow": shallow,
                "grund": ("keine Git-Historie für den Zeitraum" if not shallow else
                          "Shallow-Clone: der Zeitraum liegt vor dem Klon-Zeitpunkt "
                          "(Beleg nur mit `fetch-depth: 0` möglich)"),
                "tage": {}, "commits": 0}

    tage: dict[str, dict] = {}
    for zeile in protokoll[:max_commits]:
        sha, tag, betreff = zeile.split("|", 2)
        diff = git("show", sha, "--unified=0", "--", "content/")
        if not diff:
            continue
        # Beiträge sind der Bestand, der in der Sitemap steht; Rubriken und
        # Rechtstexte sind es auch, aber ihre Zahl bewegt sich kaum. Beides
        # getrennt ausweisen, damit die Zahl zum GSC-Befund passt.
        bloecke = re.split(r"^diff --git ", diff, flags=re.M)[1:]
        plus = minus = posts_neu = posts_weg = 0
        dateien = posts = 0
        for block in bloecke:
            dateien += 1
            ist_post = block.startswith("a/content/posts/")
            posts += 1 if ist_post else 0
            neu = block.count("+draft: true")
            weg = block.count("-draft: true")
            plus += neu
            minus += weg
            if ist_post:
                posts_neu += neu
                posts_weg += weg
        eintrag = tage.setdefault(tag, {"commits": 0, "content_dateien": 0,
                                        "draft_saldo": 0, "draft_neu": 0,
                                        "draft_neu_posts": 0, "posts_saldo": 0,
                                        "post_dateien": 0, "top": []})
        eintrag["commits"] += 1
        eintrag["content_dateien"] += dateien
        eintrag["post_dateien"] += posts
        eintrag["draft_saldo"] += plus - minus
        eintrag["draft_neu"] += plus
        eintrag["draft_neu_posts"] += posts_neu
        eintrag["posts_saldo"] += posts_neu - posts_weg
        if plus or dateien >= 20:
            eintrag["top"].append({"sha": sha[:8], "betreff": betreff[:90],
                                   "dateien": dateien, "draft_neu": plus,
                                   "draft_neu_posts": posts_neu})
    for tag in tage:
        tage[tag]["top"].sort(key=lambda x: (-x["draft_neu"], -x["dateien"]))
        tage[tag]["top"] = tage[tag]["top"][:3]
    return {"verfuegbar": True, "shallow": shallow, "tage": tage,
            "commits": len(protokoll),
            "von": von.isoformat(), "bis": bis.isoformat()}


def git_beleg_cache(max_tage: int = 14) -> dict | None:
    """Die Git-Ereignisse des letzten `--ursachen`-Laufs, wenn sie frisch sind.

    Warum ein Cache: Der Beleg kostet einen `git log` über Hunderte Commits.
    Das gehört nicht in jeden Audit – aber ein Befund, der „kein Beleg“ sagt,
    obwohl der Beleg zwei Zentimeter entfernt liegt, wäre auch falsch.
    """
    datei = ABDECKUNG / "ursachen.json"
    if not datei.exists():
        return None
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    ereignisse = daten.get("ereignisse")
    if not isinstance(ereignisse, dict) or not ereignisse.get("verfuegbar"):
        return None
    erzeugt = daten.get("erzeugt")
    if erzeugt:
        try:
            alter = (dt.date.today() - dt.date.fromisoformat(str(erzeugt)[:10])).days
        except ValueError:
            alter = 0
        if alter > max_tage:
            return None
    return ereignisse


def ursachen(kenn: dict, wahrheit: dict, ereignisse: dict | None = None) -> list[dict]:
    """Größenordnungen für einen Sprung – ausdrücklich als Hypothese.

    Ein Sprung von 59 Seiten hat eine Ursache, die im Repo liegt oder außerhalb.
    Was sich belegen lässt, ist die KAPAZITÄT: Welche Klassen im Bestand haben
    ungefähr diese Größe? Was sich nicht belegen lässt, steht als offene Frage
    da. Diese Funktion erfindet keine Ursache – sie sortiert die Kandidaten
    nach Passung und nennt für jeden den Prüfweg.
    """
    bau = wahrheit.get("bau") or {}
    klassen = bau.get("noindex_klassen") or {}
    befund: list[dict] = []
    for a in kenn.get("anomalien") or []:
        delta = abs(a.get("delta") or 0)
        kandidaten = []
        for name, zahl in klassen.items():
            if delta == 0:
                continue
            abweichung = abs(zahl - delta) / delta
            if abweichung <= 0.35:
                kandidaten.append({"klasse": KLASSEN_TEXT.get(name, name),
                                   "anzahl": zahl, "abweichung_prozent": round(abweichung * 100)})
        if wahrheit.get("anzahl_taxonomie") and delta:
            abweichung = abs(wahrheit["anzahl_taxonomie"] - delta) / delta
            if abweichung <= 0.35:
                kandidaten.append({"klasse": "Taxonomie-URLs (abgeschaltet)",
                                   "anzahl": wahrheit["anzahl_taxonomie"],
                                   "abweichung_prozent": round(abweichung * 100)})
        kandidaten.sort(key=lambda x: x["abweichung_prozent"])
        eintrag = {
            "datum": a.get("datum"), "feld": a.get("feld"), "delta": a.get("delta"),
            "kandidaten": kandidaten[:4],
            "pruefweg": ("Änderungsprotokoll der Seiten (git log auf content/), "
                         "Deploy-Protokoll und Sitemap-Diff zum Datum; die Klassen "
                         "oben sind Größenordnungen, kein Beweis."),
            "bewertung": ("kein Beleg im Repo gefunden" if not kandidaten
                          else "Größenordnung passt – Ursache noch nicht belegt"),
            "git": None,
        }
        # Der Beleg: In den sieben Tagen vor dem Sprung muss ein Tag mit
        # vielen neuen Entwürfen stehen. Google meldet mit Verzögerung – ein
        # Ereignis am Tag selbst wäre ungewöhnlich, deshalb das Fenster.
        if ereignisse and ereignisse.get("verfuegbar") and a.get("datum"):
            try:
                sprung = dt.date.fromisoformat(str(a["datum"])[:10])
            except ValueError:
                sprung = None
            if sprung:
                fenster = []
                for tag, e in ereignisse["tage"].items():
                    try:
                        d = dt.date.fromisoformat(tag)
                    except ValueError:
                        continue
                    if 0 <= (sprung - d).days <= 7 and (e["draft_neu"] or e["draft_saldo"]):
                        fenster.append((e["draft_neu"], tag, e))
                fenster.sort(reverse=True)
                if fenster:
                    _neu, tag, e = fenster[0]
                    verzug = (sprung - dt.date.fromisoformat(tag)).days
                    eintrag["git"] = {
                        "tag": tag, "draft_neu": e["draft_neu_posts"] or e["draft_neu"],
                        "saldo": e["posts_saldo"], "draft_neu_gesamt": e["draft_neu"],
                        "draft_saldo": e["draft_saldo"],
                        "content_dateien": e["content_dateien"],
                        "commits": e["commits"], "top": e["top"],
                        "verzug_tage": verzug,
                    }
                    # Der Beleg ersetzt die Größenordnungen: Wer den Commit hat,
                    # braucht keine Klassenähnlichkeit mehr.
                    eintrag["kandidaten"] = []
                    eintrag["bewertung"] = (
                        f"belegt (Repo): Saldo {e['posts_saldo']:+d} Beitragsentwürfe am "
                        f"{tag} ({e['draft_neu_posts']} neu zurückgestuft), Google meldet "
                        f"den Sprung {verzug} Tage später")
        befund.append(eintrag)
    return befund


# --------------------------------------------------------------------------
#  Ausgabe
# --------------------------------------------------------------------------

# Anzeigenamen der Build-Klassen. Technische Schlüssel, lesbare Ausgabe.
# Kontingent der URL-Inspection-API: 200 Abfragen je Property und Tag. Steht
# hier, weil die Wellen-Rechnung sonst eine magische Zahl enthielte.
ANFRAGEN_PRO_TAG = 200

KLASSEN_TEXT = {
    "weiterleitung": "Weiterleitungsseiten",
    "gateway": "/go/-Gateways",
    "pager": "Pager-Seiten",
    "newsletter": "Newsletter-Funnel",
    "suche": "Suche",
    "kalender": "Veröffentlichungskalender",
    "werkzeuge": "Werkzeug-Hub (noindex)",
    "pinterest-oauth": "Pinterest-Autorisierung",
    "wurzel": "Startseite",
}

URTEIL_TEXT = {
    "vollstaendig": "vollständig erklärt",
    "plausibel": "plausibel",
    "offen": "offen",
    "unklar": "unklar",
}


def als_markdown(a: dict) -> str:
    k = a["kennzahlen"]
    z = []
    alter = k.get("export_alter_tage")
    z.append(f"## Abdeckung (Search Console, Stand {k.get('stand_datum') or '?'}"
             + (f", {alter} Tage alt" if alter is not None else "") + ")")
    z.append("")
    z.append(f"**Gesamtbild: {'🔴 ROT' if a['gate']['status'] == 'rot' else '🟢 GRÜN'}**"
             f" · Quelle: `{a['quellen']['export']}` · Gegenprobe: `{a['quellen']['repo']}`")
    z.append("")
    z.append("| Kennzahl | Wert |")
    z.append("|---|---|")
    z.append(f"| Bekannte URLs | {k.get('bekannt')} |")
    z.append(f"| davon indexiert | {k.get('indexiert')} ({k.get('quote_indexiert')} %) |")
    z.append(f"| davon nicht indexiert | {k.get('nicht_indexiert')} |")
    z.append(f"| indexierbare Seiten im Repo | {k.get('live_indexierbar')} |")
    z.append(f"| Index-Puffer (Altlasten) | {k.get('index_puffer')} |")
    z.append(f"| Impressionen im Zeitraum | {k.get('impressionen_summe')} "
             f"({k.get('impressionen_je_tag')}/Tag, {k.get('tage_ohne_impression')} Tage ohne) |")
    z.append("")
    if k.get("build_seiten"):
        klassen = ", ".join(
            f"{KLASSEN_TEXT.get(name, name)} {zahl}"
            for name, zahl in (k.get("build_noindex_klassen") or {}).items())
        z.append("| Bestand (am Build gemessen) | Wert |")
        z.append("|---|---|")
        z.append(f"| Gebaute URLs | {k['build_seiten']} |")
        z.append(f"| davon indexierbar (Sitemap) | {k['build_seiten'] - (k.get('build_noindex') or 0)} |")
        z.append(f"| davon bewusst nicht indexierbar | {k.get('build_noindex')} "
                 f"(davon {k.get('build_weiterleitung')} Weiterleitungsseiten) |")
        z.append(f"| Crawl-Fläche je indexierbarer Seite | {k.get('build_verhaeltnis')} : 1 |")
        z.append(f"| Klassen nicht indexierbar | {klassen} |")
        sektionen = a["wahrheit"].get("sektionen") or {}
        if sektionen:
            gross = [(n, v) for n, v in sektionen.items() if v >= 2]
            klein = sum(v for _n, v in sektionen.items() if v < 2)
            text = ", ".join(f"{name} {zahl}" for name, zahl in gross)
            if klein:
                text += f", übrige Einzelseiten {klein}"
            z.append(f"| Indexierbar nach Sektion | {text} |")
        z.append(f"| Nicht-Index-Einträge je gebauter URL | {k.get('nicht_indexiert_je_build_seite')} "
                 f"({'mehr Einträge als URLs: überwiegend Historie' if (k.get('nicht_indexiert_je_build_seite') or 0) > 1 else 'im Rahmen des Bestands'}) |")
        z.append("")
    z.append("| Grund | Seiten | Erwartung | Urteil |")
    z.append("|---|---|---|---|")
    for g in a["gruende"]:
        if g["erwartung"] is None:
            erwartung = "keine"
        elif g.get("erwartung_art") == "hoechstens":
            erwartung = f"≤ {g['erwartung']}"
        else:
            erwartung = str(g["erwartung"])
        z.append(f"| {g['titel']} | {g['seiten']} | {erwartung} | "
                 f"{URTEIL_TEXT.get(g['urteil'], g['urteil'])} |")
    z.append("")
    if a["widersprueche"]:
        z.append("### Widersprüche")
        z.append("")
        for w in a["widersprueche"]:
            zeichen = "🛑" if w["schwere"] == "hart" else "ℹ️"
            z.append(f"- {zeichen} **{w['regel']}** {w['text']}")
        z.append("")
    v = a.get("vertrag") or {}
    if v:
        z.append(f"### Vertrag: noindex-Bestand und Gateways — "
                 f"{'🟢 in Ordnung' if v.get('status') == 'gruen' else '🔴 Abweichung'}")
        z.append("")
        z.append(f"- {len(v.get('noindex_ist') or [])} noindex-Seiten im Inhalt, "
                 f"{len(v.get('noindex_vertrag') or {})} im Vertrag "
                 f"(`NOINDEX_VERTRAG`), {len(v.get('gateways') or [])} Gateways.")
        for f in v.get("funde") or []:
            z.append(f"- 🛑 **{f['regel']}** {f['text']}")
        z.append("")

    k2 = a.get("kandidaten") or {}
    if k2:
        z.append("### Kandidatenraum (Obergrenze für die 404-Erklärung)")
        z.append("")
        z.append(f"- {k2.get('gesamt')} historische URLs aus dem Bestand ableitbar; "
                 f"{k2.get('davon_dokumentiert')} dokumentiert "
                 f"(Weiterleitung oder bewusst 404), "
                 f"{k2.get('davon_ohne_entscheidung')} ohne Entscheidung.")
        z.append("- Das ist eine **Obergrenze**, kein Nachweis: Ob Google eine "
                 "dieser URLs je gesehen hat, sagt nur die Detail-Liste (M1).")
        z.append("")

    vl = a.get("verlinkung") or {}
    if vl:
        z.append("### Redaktionelle Verlinkung")
        z.append("")
        z.append(f"- {k.get('ohne_inlink')} von {k.get('inhaltsseiten')} Inhaltsseiten "
                 f"ohne redaktionellen Inlink, {k.get('ohne_auslink')} ohne ausgehenden "
                 f"Link, Median {vl.get('median_aus')} ausgehende Links je Seite.")
        if a.get("verlinkungsauftrag"):
            anzahl = len(a["verlinkungsauftrag"])
            z.append(f"- Verlinkungsauftrag: {anzahl} "
                     f"{'Quelle-Ziel-Paar' if anzahl == 1 else 'Quelle-Ziel-Paare'} "
                     "(`--verlinkung --apply`).")
        z.append("")
    if a.get("tote_ziele"):
        z.append("### Links ins Leere")
        z.append("")
        for eintrag in a["tote_ziele"]:
            z.append(f"- `{eintrag['ziel']}` – {len(eintrag['quellen'])} Quelle(n); "
                     "die Seite wird nicht gebaut, der Link erscheint als Text.")
        z.append("")
    pr = a.get("prioritaet") or {}
    if pr.get("seiten"):
        z.append("### Anfrage-Wellen (M2)")
        z.append("")
        z.append(f"- Welle 1: {len(pr.get('welle1') or [])} Seiten · "
                 f"Welle 2: {len(pr.get('welle2') or [])} · "
                 f"Kontingent {pr.get('kontingent')} Anfragen/Tag.")
        z.append("")
        z.append("| Score | Seite | Impressionen | Inlinks | Grund |")
        z.append("|---|---|---|---|---|")
        for zeile in pr["seiten"][:10]:
            z.append(f"| {zeile['score']} | `{zeile['url']}` | {zeile['impressionen']} | "
                     f"{zeile['inlinks']} | {zeile['grund']} |")
        z.append("")
    if a.get("ursachen"):
        z.append("### Sprünge im Verlauf")
        z.append("")
        for u in a["ursachen"]:
            z.append(f"- **{u['datum']}** · {u['feld']} {u['delta']:+d} – {u['bewertung']}")
            for kandidat in u.get("kandidaten") or []:
                z.append(f"  - Kandidat: {kandidat['klasse']} ({kandidat['anzahl']}), "
                         f"Abweichung {kandidat['abweichung_prozent']} %")
        z.append("")
    if a.get("abnahme"):
        z.append("### Abnahme")
        z.append("")
        z.append("| Kriterium | Ziel | Status | Messung |")
        z.append("|---|---|---|---|")
        zeichen = {"erfuellt": "✅", "offen": "🛑", "unbekannt": "❔"}
        for x in a["abnahme"]:
            z.append(f"| {x['kriterium']} | {x['ziel']} | "
                     f"{zeichen.get(x['status'], x['status'])} | {x['messung']} |")
        z.append("")
    if a["massnahmen"]:
        z.append("### Maßnahmen (Auszug)")
        z.append("")
        z.append("| ID | Dringlichkeit | Maßnahme | Beleg |")
        z.append("|---|---|---|---|")
        for m in a["massnahmen"]:
            z.append(f"| {m['id']} | {m['dringlichkeit']} | {m['titel']} | {m['beleg']} |")
        z.append("")
    return "\n".join(z)


def drucke(a: dict) -> None:
    k = a["kennzahlen"]
    alter = k.get("export_alter_tage")
    print(f"GSC-ABDECKUNG · Stand {k.get('stand_datum') or '?'}"
          + (f" ({alter} Tage alt)" if alter is not None else "")
          + f" · Gate {a['gate']['status'].upper()}")
    print(f"  Quelle:     {a['quellen']['export']}")
    print(f"  Gegenprobe: {a['quellen']['repo']}")
    print()
    print(f"  Bekannt:          {k.get('bekannt')}")
    print(f"  Indexiert:        {k.get('indexiert')} ({k.get('quote_indexiert')} %)")
    print(f"  Nicht indexiert:  {k.get('nicht_indexiert')} "
          f"(7 Tage: {k.get('delta_7_nicht_indexiert'):+d})"
          if k.get("delta_7_nicht_indexiert") is not None else
          f"  Nicht indexiert:  {k.get('nicht_indexiert')}")
    print(f"  Indexierbar:      {k.get('live_indexierbar')} · "
          f"Puffer (Altlasten): {k.get('index_puffer')}")
    if k.get("build_seiten"):
        print(f"  Build:            {k['build_seiten']} URLs · "
              f"{k['build_seiten'] - (k.get('build_noindex') or 0)} indexierbar · "
              f"{k.get('build_noindex')} bewusst nicht · "
              f"Fläche {k.get('build_verhaeltnis')}:1 · "
              f"Nicht-Index je URL {k.get('nicht_indexiert_je_build_seite')}")
    print()
    print("  Gründe:")
    for g in a["gruende"]:
        if g["erwartung"] is None:
            erwartung = "?"
        elif g.get("erwartung_art") == "hoechstens":
            erwartung = f"<={g['erwartung']}"
        else:
            erwartung = str(g["erwartung"])
        print(f"    {g['seiten']:>4}  {g['titel'][:44]:<44} erwartet {erwartung:>4}  "
              f"{URTEIL_TEXT.get(g['urteil'], g['urteil'])}")
    v = a.get("vertrag") or {}
    if v:
        print(f"  Vertrag:          {'grün' if v.get('status') == 'gruen' else 'ROT'} "
              f"({len(v.get('noindex_ist') or [])} noindex, "
              f"{len(v.get('gateways') or [])} Gateways)")
    vl = a.get("verlinkung") or {}
    if vl:
        print(f"  Verlinkung:       {a['kennzahlen'].get('ohne_inlink')} von "
              f"{a['kennzahlen'].get('inhaltsseiten')} Inhaltsseiten ohne Inlink · "
              f"Median {vl.get('median_aus')} ausgehend")
    pr = a.get("prioritaet") or {}
    if pr.get("seiten"):
        print(f"  Anfrage-Wellen:   {len(pr.get('welle1') or [])} / "
              f"{len(pr.get('welle2') or [])} (Kontingent {pr.get('kontingent')}/Tag)")
        for zeile in pr["seiten"][:3]:
            print(f"    {zeile['score']:>5}  {zeile['url'][:64]:<64} {zeile['grund']}")
    k2 = a.get("kandidaten") or {}
    if k2:
        print(f"  Kandidatenraum:   {k2.get('gesamt')} ableitbar · "
              f"{k2.get('davon_ohne_entscheidung')} ohne Entscheidung (Obergrenze)")
    if a.get("abnahme"):
        offen = [x for x in a["abnahme"] if x["status"] != "erfuellt"]
        print(f"  Abnahme:          {len(a['abnahme']) - len(offen)} erfüllt, "
              f"{len(offen)} offen")
    if a["widersprueche"]:
        print()
        print("  Widersprüche:")
        for w in a["widersprueche"]:
            print(f"    [{'hart' if w['schwere'] == 'hart' else 'info'}] {w['regel']}: {w['text']}")
    if a["massnahmen"]:
        print()
        print("  Maßnahmen:")
        for m in a["massnahmen"]:
            print(f"    {m['id']} {m['dringlichkeit']} {m['titel']} ({m['aufwand']})")
            print(f"        {m['beleg']}")


# --------------------------------------------------------------------------
#  Selbsttest
# --------------------------------------------------------------------------

def _fixture_export(ordner: Path, *, summe_abweichung: int = 0,
                    noindex_seiten: int = 5, extra_grund: str | None = None,
                    bom: bool = True, trenner: str = ",") -> Path:
    """Schreibt einen Export im Format der Oberfläche – mit Schaltern für Defekte."""
    ordner.mkdir(parents=True, exist_ok=True)
    kodierung = "utf-8-sig" if bom else "utf-8"
    uebersicht = [
        ("Nicht gefunden (404)", "Website", "Fehlgeschlagen", 223),
        ('Durch ""noindex""-Tag ausgeschlossen', "Website", "Fehlgeschlagen", noindex_seiten),
        ("Seite mit Weiterleitung", "Website", "Fehlgeschlagen", 1),
        ("Gecrawlt – zurzeit nicht indexiert", "Google-Systeme", "Fehlgeschlagen", 4),
        ("Durch robots.txt-Datei blockiert", "Website", "Nicht gestartet", 18),
        ("Gefunden – zurzeit nicht indexiert", "Google-Systeme", "Gestartet", 69),
    ]
    if extra_grund:
        uebersicht.append((extra_grund, "Website", "Gestartet", 2))
    # Die Summe OHNE Abweichung ist der Wert, den das Diagramm zeigen müsste.
    gesamt = sum(z[3] for z in uebersicht)
    if summe_abweichung:
        # Defektfall: die Übersicht zählt mehr Seiten, als das Diagramm kennt.
        uebersicht[0] = (uebersicht[0][0], uebersicht[0][1], uebersicht[0][2],
                         uebersicht[0][3] + summe_abweichung)
    with (ordner / "Kritische Probleme.csv").open("w", encoding=kodierung, newline="") as fh:
        w = csv.writer(fh, delimiter=trenner)
        w.writerow(["Grund", "Quelle", "Validierung", "Seiten"])
        for zeile in uebersicht:
            w.writerow(zeile)
    with (ordner / "Diagramm.csv").open("w", encoding=kodierung, newline="") as fh:
        w = csv.writer(fh, delimiter=trenner)
        w.writerow(["Datum", "Nicht indexiert", "Indexiert", "Impressionen"])
        w.writerow(["2026-10-15", 261, 138, 3])
        w.writerow(["2026-10-16", 261, 138, 2])
        w.writerow(["2026-10-17", gesamt, 117, 1])
        w.writerow(["2026-10-18", gesamt, 117, 1])
        w.writerow(["2026-10-19", gesamt, 117, 7])
    with (ordner / "Metadaten.csv").open("w", encoding=kodierung, newline="") as fh:
        w = csv.writer(fh, delimiter=trenner)
        w.writerow(["Property", "Wert"])
        w.writerow(["Sitemap", "Alle bekannten Seiten"])
    with (ordner / "Nicht kritische Probleme.csv").open("w", encoding=kodierung, newline="") as fh:
        csv.writer(fh, delimiter=trenner).writerow(["Grund", "Quelle", "Validierung", "Seiten"])
    return ordner


def _mini_repo(wurzel: Path) -> Path:
    """Kleines Repo mit bekannter Wahrheit: 3 indexierbar, 1 noindex, 2 Gateways."""
    for ordner, fm in (
        ("content/posts/a", "title: A\ndate: 2026-10-01\ntags: [\"Sparen\"]\ncategories: [\"Ratgeber\"]\n"),
        ("content/posts/b", "title: B\ndate: 2026-10-02\n"),
        ("content/posts/c", "title: C\ndate: 2026-10-03\n"),
        ("content/suche", "title: Suche\nrobotsNoIndex: true\nurl: \"/suche/\"\n"),
    ):
        p = wurzel / ordner
        p.mkdir(parents=True, exist_ok=True)
        (p / "index.md").write_text(f"---\n{fm}---\n\nText.\n", encoding="utf-8")
    (wurzel / "content" / "_index.md").write_text("---\ntitle: Start\n---\n", encoding="utf-8")
    # A verlinkt auf B (redaktionell), B auf C. C hat damit einen Inlink,
    # A keinen – genau die Lage, die der Verlinkungsauftrag schließen soll.
    (wurzel / "content" / "posts" / "a" / "index.md").write_text(
        "---\ntitle: A\ndate: 2026-10-01\ntags: [\"Sparen\"]\ncategories: [\"Ratgeber\"]\n---\n\n"
        "Text mit [B](../../posts/b/).\n\n**Weiterlesen:** [B](../../posts/b/)\n",
        encoding="utf-8")
    (wurzel / "content" / "posts" / "b" / "index.md").write_text(
        "---\ntitle: B\ndate: 2026-10-02\n---\n\nText mit [C](../../posts/c/).\n\n"
        "**Weiterlesen:** [C](../../posts/c/)\n", encoding="utf-8")
    (wurzel / "content" / "posts" / "c" / "index.md").write_text(
        "---\ntitle: C\ndate: 2026-10-03\n---\n\nText ohne Link.\n", encoding="utf-8")
    (wurzel / "public").mkdir(parents=True, exist_ok=True)
    (wurzel / "public" / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url><loc>https://franksfinanzcheck.de/posts/a/</loc>'
        '<lastmod>2026-10-01</lastmod></url>\n'
        '  <url><loc>https://franksfinanzcheck.de/posts/b/</loc>'
        '<lastmod>2026-10-02</lastmod></url>\n'
        '  <url><loc>https://franksfinanzcheck.de/posts/c/</loc>'
        '<lastmod>2026-10-03</lastmod></url>\n'
        '</urlset>\n', encoding="utf-8")
    for name in ("dsl", "strom"):
        p = wurzel / "static" / "go" / name
        p.mkdir(parents=True, exist_ok=True)
        (p / "index.html").write_text('<meta name="robots" content="noindex,nofollow">',
                                      encoding="utf-8")
    (wurzel / "layouts").mkdir(parents=True, exist_ok=True)
    (wurzel / "layouts" / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nDisallow: /go/\n\n"
        "Sitemap: https://franksfinanzcheck.de/sitemap.xml\n", encoding="utf-8")
    (wurzel / "data").mkdir(parents=True, exist_ok=True)
    (wurzel / "data" / "weiterleitungen.yaml").write_text(
        'eintraege:\n'
        '  - {von: "/posts/alt-a/", nach: "/posts/a/", regel: "B", grund: "gleiches Thema"}\n',
        encoding="utf-8")
    (wurzel / "data" / "url_entfallen.yaml").write_text(
        'eintraege:\n  - {von: "/posts/weg/", regel: "D", grund: "kein Nachfolger"}\n',
        encoding="utf-8")
    return wurzel


def selbsttest() -> int:
    """78 Fälle, alle offline. Geprüft wird die Klasse, nicht der Einzelfall."""
    ok = 0
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool) -> None:
        nonlocal ok
        if bedingung:
            ok += 1
        else:
            fehler.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # --- Normalisierung und Klassifikation
        pruefe("K1 Umlaute", normalisiere("Durch „noindex“-Tag ausgeschlossen")
               == "durch noindex-tag ausgeschlossen")
        pruefe("K2 404 erkannt", klassifiziere("Nicht gefunden (404)") == "not_found")
        pruefe("K3 robots erkannt",
               klassifiziere("Durch robots.txt-Datei blockiert") == "robots_blocked")
        pruefe("K4 gecrawlt vor gefunden",
               klassifiziere("Gecrawlt – zurzeit nicht indexiert") == "crawled_not_indexed")
        pruefe("K5 gefunden erkannt",
               klassifiziere("Gefunden – zurzeit nicht indexiert") == "discovered_not_indexed")
        pruefe("K6 unbekannt bleibt unbekannt",
               klassifiziere("Wurde von einem Ausländer besucht") == "unknown")
        pruefe("K7 Zahlen mit Tausenderpunkt", zahl("1.234") == 1234)
        pruefe("K8 leere Zahl", zahl("") is None)

        # --- Einlesen: BOM, Anführungszeichen, Semikolon
        export_dir = _fixture_export(tmp / "export")
        export = lade_export(export_dir)
        pruefe("K9 vier Dateien erkannt", len(export["dateien"]) == 4)
        pruefe("K10 Übersicht gelesen", len(export["uebersicht"]) == 6)
        pruefe("K11 Anführungszeichen im Grund",
               any("noindex" in e["grund"] for e in export["uebersicht"]))
        pruefe("K12 Verlauf gelesen", len(export["verlauf"]) == 5)
        pruefe("K13 Metadaten gelesen", export["metadaten"].get("Sitemap") == "Alle bekannten Seiten")
        pruefe("K14 konsistenter Export ohne harte Befunde",
               not [p for p in pruefe_export(export) if p["schwere"] == "hart"])

        semikolon = _fixture_export(tmp / "semikolon", trenner=";", bom=False)
        export_sc = lade_export(semikolon)
        pruefe("K15 Semikolon erkannt", len(export_sc["uebersicht"]) == 6)
        pruefe("K16 Semikolon-Datensatz vollständig",
               sum(e["seiten"] or 0 for e in export_sc["uebersicht"]) == 320)

        # --- Widerspruch: Summe passt nicht zum Diagramm
        schief = _fixture_export(tmp / "schief", summe_abweichung=7)
        befunde = pruefe_export(lade_export(schief))
        pruefe("K17 Summenfehler ist hart",
               any(b["regel"] == "E8" and b["schwere"] == "hart" for b in befunde))
        ergebnis = importiere(schief, ziel=tmp / "ziel", schreiben=False)
        pruefe("K18 ungueltiger Export wird nicht geschrieben",
               ergebnis["status"] == "ungueltig")

        # --- Import schreibt Momentaufnahme + Verlauf, idempotent
        ziel = tmp / "ziel"
        ergebnis = importiere(tmp / "export", ziel=ziel)
        pruefe("K19 Import ok", ergebnis["status"] == "ok" and ergebnis["datum"] == "2026-10-19")
        pruefe("K20 Snapshot liegt", (ziel / "2026-10-19.json").exists()
               and (ziel / "aktuell.json").exists())
        importiere(tmp / "export", ziel=ziel)
        zeilen = (ziel / "verlauf.jsonl").read_text(encoding="utf-8").splitlines()
        pruefe("K21 Verlauf idempotent", len(zeilen) == 1)

        # --- Gegenrechnung gegen ein Mini-Repo
        repo = _mini_repo(tmp / "repo")
        wahrheit = repo_wahrheit(repo)
        pruefe("K22 Wahrheit: 3 indexierbar", wahrheit["anzahl_indexierbar"] == 3)
        pruefe("K23 Wahrheit: 1 noindex", wahrheit["anzahl_noindex"] == 1)
        pruefe("K24 Wahrheit: 2 Gateways", wahrheit["anzahl_gateways"] == 2)
        pruefe("K25 Wahrheit: 1 Weiterleitung", wahrheit["anzahl_weiterleitungen"] == 1)
        pruefe("K26 Wahrheit: 1 entfallen", wahrheit["anzahl_entfallen"] == 1)
        pruefe("K27 robots /go/ gesperrt", wahrheit["robots"]["go_gesperrt"])

        auswertung = auswerten(ergebnis["snapshot"], wahrheit)
        nach = {g["schluessel"]: g for g in auswertung["gruende"]}
        pruefe("K28 noindex-Leck erkannt (5 gemeldet, 1 erwartet)",
               nach["noindex"]["offen"] == 4)
        # Erklärbar sind 4 Taxonomie-URLs (/tags/, /categories/ und je ein
        # Eintrag aus dem Mini-Repo) plus 1 bewusst entfallene Alt-URL.
        pruefe("K29 404 offen (223 gemeldet, 5 erklärbar)",
               nach["not_found"]["offen"] == 218)
        pruefe("K30 Gate rot wegen Widersprüchen", auswertung["gate"]["status"] == "rot")
        pruefe("K31 Index-Puffer erkannt", auswertung["kennzahlen"]["index_puffer"] == 114)
        pruefe("K32 Anomalie am 17.10 erkannt",
               any(a["datum"] == "2026-10-17" for a in auswertung["kennzahlen"]["anomalien"]))
        pruefe("K33 Maßnahmen priorisiert",
               auswertung["massnahmen"][0]["dringlichkeit"] == "P1")

        # --- Unbekannter Grund ist hart
        fremd = _fixture_export(tmp / "fremd", extra_grund="Vom Ausland blockiert")
        auswertung_fremd = auswerten(importiere(fremd, ziel=tmp / "ziel2")["snapshot"], wahrheit)
        pruefe("K34 unbekannter Grund rot",
               auswertung_fremd["gate"]["status"] == "rot"
               and any(w["regel"] == "W6" for w in auswertung_fremd["widersprueche"]))

        # --- Vorschläge
        v = vorschlaege(["/posts/2026-10-01-a/", "/posts/alt-a/", "/posts/voellig-fremd/"],
                        wahrheit)
        pruefe("K35 gleicher Slug-Rest vorgeschlagen",
               v[0]["vorschlag"] == "/posts/a/" and v[0]["sicherheit"] == "hoch")
        pruefe("K36 vorhandene Weiterleitung erkannt", v[1]["regel"] == "vorhanden")
        pruefe("K37 kein Vorschlag ohne Deckung", v[2]["vorschlag"] is None)

        # --- Markdown bleibt lesbar
        md = als_markdown(auswertung)
        pruefe("K38 Markdown enthält Tabelle", "| Kennzahl | Wert |" in md)
        pruefe("K39 Markdown nennt Urteil", "offen" in md)

        # --- Gate-Vergleich mit Vorlauf
        alt = {"nicht_indexiert": 200, "quote_indexiert": 40.0, "summe_gruende": 200}
        neu = dict(auswertung["kennzahlen"], nicht_indexiert=300, quote_indexiert=30.0)
        g = gate({"kennzahlen": neu, "widersprueche": []}, alt)
        pruefe("K40 Rückschritt im Gate", g["status"] == "rot"
               and any(f["regel"] in ("G2", "G3") for f in g["funde"]))

        # --- Verlinkung, Triage, Vertrag, Priorität (M1–M9)
        pruefe("K41 relativer Link aufgelöst",
               _pfad_normalisieren("../../posts/a/", "/posts/b/") == "/posts/a/")
        pruefe("K42 absolute Domain aufgelöst",
               _pfad_normalisieren("https://franksfinanzcheck.de/posts/a/", "/") == "/posts/a/")
        pruefe("K43 externer Link ist kein interner",
               _pfad_normalisieren("https://example.org/x/", "/") is None)
        links = redaktionelle_links(repo)
        pruefe("K44 redaktioneller Inlink gezählt",
               links["seiten"]["/posts/b/"]["ein"] == 1
               and "/posts/a/" in links["ohne_ein"])
        pruefe("K45 Anker am Doppelpunkt gekürzt",
               anker_kurz("Bankgebühren senken: 7 Schritte zum günstigeren Konto")
               == "Bankgebühren senken")
        pruefe("K46 Anker bleibt kurz",
               len(anker_kurz("Ein sehr langer Titel mit vielen Wörtern über die Lage")
                   .split()) <= 6)

        t = triage([{"url": "/posts/a/", "grund": "Nicht gefunden (404)"},
                    {"url": "/posts/a/", "grund": "Durch noindex-Tag ausgeschlossen"},
                    {"url": "/posts/weg/", "grund": "Nicht gefunden (404)"},
                    {"url": "/posts/neu/", "grund": "Gefunden – zurzeit nicht indexiert"}],
                   wahrheit, {}, {"ohne_ein": ["/posts/neu/"]})
        nach_url = {z["url"]: z for z in t["zeilen"]}
        pruefe("K47 live-URL wird nicht als Fehler triagiert",
               nach_url["/posts/a/"]["prioritaet"] == "P3"
               and "Bestand" in nach_url["/posts/a/"]["aktion"])
        pruefe("K48 entschiedene 404 bleibt entschieden",
               "bereits entschieden" in nach_url["/posts/weg/"]["aktion"]
               and "url_entfallen" in nach_url["/posts/weg/"]["beleg"])
        pruefe("K49 fehlender Inlink ist P1",
               nach_url["/posts/neu/"]["prioritaet"] == "P1")
        pruefe("K50 Triage sortiert nach Priorität",
               [z["prioritaet"] for z in t["zeilen"]][0] == "P1"
               and t["offen"])

        k = kandidatenraum(wahrheit)
        pruefe("K51 Kandidatenraum kennt dokumentierte Alt-URL",
               "/posts/alt-a/" in k["ohne_entscheidung"] or k["davon_dokumentiert"] >= 1)
        pruefe("K52 Kandidatenraum führt keine Live-URL als offen",
               not [u for u in k["ohne_entscheidung"] if u in wahrheit["indexierbar"]])

        vertrag_original = dict(NOINDEX_VERTRAG)
        try:
            NOINDEX_VERTRAG.clear()
            NOINDEX_VERTRAG.update({"/suche/": "Test"})
            pruefe("K53 Vertrag grün, wenn jede noindex-Seite begründet ist",
                   vertrag(wahrheit)["status"] == "gruen")
            NOINDEX_VERTRAG.clear()
            pruefe("K54 noindex ohne Vertrag ist ein harter Fund",
                   any(f["regel"] == "V1" for f in vertrag(wahrheit)["funde"]))
            NOINDEX_VERTRAG.update({"/suche/": "Test", "/gibtsnicht/": "veraltet"})
            pruefe("K55 veralteter Vertragseintrag ist ein harter Fund",
                   any(f["regel"] == "V2" for f in vertrag(wahrheit)["funde"]))
        finally:
            NOINDEX_VERTRAG.clear()
            NOINDEX_VERTRAG.update(vertrag_original)

        p2 = prioritaet(wahrheit, links, root=repo)
        score = {z["url"]: z["score"] for z in p2["seiten"]}
        pruefe("K56 Seite ohne Inlink steht vorn",
               score["/posts/a/"] > score["/posts/b/"])
        pruefe("K57 Welle 1 ist gefüllt und disjunkt zu Welle 2",
               p2["welle1"] and not (set(p2["welle1"]) & set(p2["welle2"])))

        auftrag = verlinkungs_auftrag(wahrheit, links, root=repo)
        pruefe("K58 Verlinkungsauftrag zielt auf die unverlinkte Seite",
               any(a["ziel"] == "/posts/a/" for a in auftrag))

        opfer = repo / "content" / "posts" / "c" / "index.md"
        opfer.write_text(opfer.read_text(encoding="utf-8")
                         + "\n**Weiterlesen:** [Ratgeber](../../pillar/x/)\n",
                         encoding="utf-8")
        ok1, _ = link_einfuegen(opfer, "/posts/a/", "A")
        ok2, meldung2 = link_einfuegen(opfer, "/posts/a/", "A")
        pruefe("K59 Link wird angehängt und nicht doppelt gesetzt",
               ok1 and not ok2 and "bereits" in meldung2)

        ohne_zeile = repo / "content" / "posts" / "b" / "index.md"
        ohne_zeile.write_text("---\ntitle: B\ndate: 2026-10-02\n---\n\nText.\n",
                              encoding="utf-8")
        ok3, meldung3 = link_einfuegen(ohne_zeile, "/posts/a/", "A")
        pruefe("K60 ohne Weiterlesen-Zeile wird nichts erfunden",
               not ok3 and "Weiterlesen" in meldung3)

        pruefe("K61 KPI ohne Verlauf ist leer, nicht geschätzt",
               kpi(tmp / "gibtsnicht.jsonl")["reihen"] == [])
        abn = abnahme(auswertung)
        pruefe("K62 Abnahme liefert Status je Kriterium",
               abn and all(x["status"] in ("erfuellt", "offen", "unbekannt") for x in abn))
        pruefe("K63 Ursachen erfinden keinen Beleg",
               all(u["bewertung"] in ("kein Beleg im Repo gefunden",
                                      "Größenordnung passt – Ursache noch nicht belegt")
                   for u in ursachen(auswertung["kennzahlen"], wahrheit)))

        # --- Vertrag im Tor, Detail-Alter, lastmod, Goldkorridor
        g6 = gate({"kennzahlen": {}, "widersprueche": [],
                   "vertrag": {"funde": [{"regel": "V1", "schwere": "hart",
                                          "text": "noindex ohne Vertrag"}]}}, None)
        pruefe("K64 gebrochener Vertrag macht das Tor rot",
               g6["status"] == "rot" and any(f["regel"] == "G6" for f in g6["funde"]))
        pruefe("K65 lastmod-Lücke wird am Build gemessen",
               lastmod_luecke({"indexierbar": []}, repo) == 0)
        pruefe("K65b ohne Build keine erfundene lastmod-Zahl",
               lastmod_luecke({"indexierbar": []}, tmp / "ohne-build") is None)
        leer = detail_stand()
        pruefe("K66 ohne Detail-Ordner kein Stand", leer["stand"] is None and leer["urls"] == 0)
        DETAILS.mkdir(parents=True, exist_ok=True)
        (DETAILS / ".stand").write_text("2026-09-01\n", encoding="utf-8")
        try:
            pruefe("K67 Detail-Alter wird gerechnet",
                   detail_stand(dt.date(2026, 9, 21))["alter_tage"] == 20)
        finally:
            (DETAILS / ".stand").unlink()

        zaehl = ("[a](../../posts/a/) [b](../../posts/b/) [c](../../posts/c/) "
                 "[d](../../posts/d/) [e](../../posts/e/) [f](../../posts/f/) "
                 "[g](../../posts/g/) [h](../../posts/h/) [i](../../posts/i/) "
                 "[j](../../posts/j/)")
        pruefe("K68 Linkzählung folgt dem Goldkorridor-Guard",
               post_links_gezaehlt(zaehl) == 10)
        pruefe("K69 Bilder sind keine Links",
               post_links_gezaehlt("![alt](../../posts/a/)") == 0)
        pruefe("K70 Triage-Markdown trägt die Tabelle",
               "| Prio | URL | Grund | Aktion | Beleg |" in triage_markdown(t, "Test"))

        # --- Vertragsbruch färbt das Gate rot (M5/M6)
        g6 = gate({"kennzahlen": {}, "widersprueche": [],
                   "vertrag": {"funde": [{"regel": "V1", "schwere": "hart",
                                          "text": "noindex ohne Vertrag"}]}}, None)
        pruefe("K64 gebrochener Vertrag macht das Tor rot",
               g6["status"] == "rot" and any(f["regel"] == "G6" for f in g6["funde"]))
        pruefe("K65 Goldkorridor-Zählung folgt dem Guard",
               post_links_gezaehlt("[a](../../posts/a/) [b](../../posts/b/)") == 2)
        pruefe("K66 Bilder sind keine Links",
               post_links_gezaehlt("![alt](../../posts/a/)") == 0)
        pruefe("K67 keine erfundene lastmod-Zahl ohne Build",
               lastmod_luecke({"indexierbar": []}, tmp / "ohne-build") is None)
        pruefe("K68 Detail-Alter ohne Ordner ist leer",
               detail_stand()["stand"] is None)
        DETAILS.mkdir(parents=True, exist_ok=True)
        (DETAILS / ".stand").write_text("2026-09-01\n", encoding="utf-8")
        try:
            pruefe("K69 Detail-Alter wird gerechnet",
                   detail_stand(dt.date(2026, 9, 21))["alter_tage"] == 20)
        finally:
            (DETAILS / ".stand").unlink()
        pruefe("K70 Triage-Markdown trägt die Tabelle",
               "| Prio | URL | Grund | Aktion | Beleg |" in triage_markdown(t, "Test"))

    if fehler:
        print(f"🛑 GSC-ABDECKUNG SELBSTTEST: {len(fehler)} von {ok + len(fehler)} Fällen rot")
        for name in fehler:
            print(f"   ✗ {name}")
        return 2
    print(f"✅ GSC-ABDECKUNG SELBSTTEST: {ok} Fälle grün")
    return 0


# --------------------------------------------------------------------------
#  Hauptlauf
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Abdeckungsbericht der Search Console einlesen, gegenrechnen, bewerten.")
    p.add_argument("--import", dest="import_pfad", metavar="PFAD",
                   help="Verzeichnis oder Datei mit den CSV-Exporten")
    p.add_argument("--audit", action="store_true", help="gegen den Repo-Bestand rechnen")
    p.add_argument("--gate", action="store_true", help="Tor für den Tageslauf (Exit 1 bei Befund)")
    p.add_argument("--json", action="store_true", help="Befund als JSON ausgeben")
    p.add_argument("--md", action="store_true", help="Befund als Markdown ausgeben")
    p.add_argument("--schreiben", action="store_true",
                   help="Befund nach data/gsc/abdeckung/befund.json + .md schreiben")
    p.add_argument("--snapshot", metavar="DATEI", help="statt aktuell.json eine Momentaufnahme")
    p.add_argument("--vorschlaege", metavar="CSV",
                   help="Detail-Export mit URLs: Weiterleitungs-Vorschläge ableiten")
    p.add_argument("--triage", nargs="?", const=str(DETAILS),
                   metavar="CSV_ODER_VERZEICHNIS",
                   help="Detail-Listen einlesen und in eine abarbeitbare Liste "
                        "übersetzen (ohne Angabe: data/gsc/abdeckung/details/)")
    p.add_argument("--altlasten", action="store_true",
                   help="Index-Altlasten benennen (Index-Puffer gegen Sitemap)")
    p.add_argument("--kandidaten", action="store_true",
                   help="Obergrenze zeigen: welche 404er kann der Bestand erklären?")
    p.add_argument("--vertrag", action="store_true",
                   help="noindex-Bestand und Gateways gegen den Vertrag prüfen")
    p.add_argument("--prioritaet", action="store_true",
                   help="Anfrage-Wellen und Verlinkungsauftrag zeigen")
    p.add_argument("--verlinkung", action="store_true",
                   help="Verlinkungsauftrag zeigen (mit --apply einfügen)")
    p.add_argument("--apply", action="store_true",
                   help="Verlinkungsauftrag in die „Weiterlesen“-Zeilen schreiben")
    p.add_argument("--max", type=int, default=10, metavar="N",
                   help="höchstens N Links je Lauf einfügen (Standard 10)")
    p.add_argument("--kpi", action="store_true", help="Wochenkennzahlen zeigen")
    p.add_argument("--abnahme", action="store_true", help="Abnahmekriterien prüfen")
    p.add_argument("--ursachen", action="store_true",
                   help="Sprünge im Bericht einordnen – mit Git-Beleg, wo möglich")
    p.add_argument("--ohne-git", action="store_true",
                   help="bei --ursachen keine Git-Historie lesen (schneller)")
    p.add_argument("--selftest", action="store_true", help="offline, ohne Netz")
    args = p.parse_args(argv)

    if args.selftest:
        return selbsttest()

    try:
        if args.import_pfad:
            ergebnis = importiere(Path(args.import_pfad))
            # Diagnose geht nach stderr, Daten nach stdout: Nur so ist
            # `--json > datei` eine Datei und kein Tagebuch.
            for bef in ergebnis.get("befunde") or []:
                zeichen = "🛑" if bef["schwere"] == "hart" else "ℹ️"
                print(f"{zeichen} [{bef['regel']}] {bef['text']}", file=sys.stderr)
            if ergebnis["status"] != "ok":
                print("Export NICHT übernommen. Erst die Widersprüche klären – "
                      "ein Artefakt mit zwei Momenten ist keine Messung.",
                      file=sys.stderr)
                return 1
            print(f"✅ Export übernommen: Stand {ergebnis['datum']} → "
                  f"data/gsc/abdeckung/{ergebnis['datum']}.json", file=sys.stderr)
            if not (args.audit or args.gate or args.json or args.md):
                return 0

        if args.triage:
            quelle = Path(args.triage)
            if not quelle.exists():
                print(f"🛑 Keine Detail-Liste gefunden: {quelle}.\n"
                      "   In der Search Console je Grund exportieren und als CSV in "
                      "diesen Ordner legen; das Exportdatum in `.stand` (JJJJ-MM-TT) "
                      "eintragen.", file=sys.stderr)
                return 1
            roh = lade_export(quelle)
            eintraege = []
            for d in roh.get("details") or []:
                # Der Grund steckt im Dateinamen – die Detail-CSV selbst trägt
                # keine Spalte „Grund“ (sie ist je Grund eine eigene Datei).
                grund = Path(d.get("datei") or "").stem or "unbekannt"
                eintraege.append({"url": d["url"], "grund": grund})
            if not eintraege:
                print("🛑 Keine URL in der Detail-Liste gefunden (Spalte „URL“).",
                      file=sys.stderr)
                return 1
            wahrheit = repo_wahrheit()
            t = triage(eintraege, wahrheit, kennzahlen(lade_snapshot(), wahrheit),
                       redaktionelle_links())
            _json_schreiben(ABDECKUNG / "triage.json", t)
            markdown = triage_markdown(t, str(quelle))
            (ABDECKUNG / "triage.md").write_text(
                "# Triage der Search-Console-Liste\n\n" + markdown + "\n",
                encoding="utf-8")
            # M3: Die Redaktions-Queue ist die Schnittstelle zwischen Automat und
            # Mensch. Sie enthält nur, was eine Redaktion entscheiden kann –
            # Technik und bereits Entschiedenes bleiben draußen.
            queue = ["# Redaktions-Queue (aus der Triage)", ""]
            for zeile in t["zeilen"]:
                if zeile["prioritaet"] in ("P0", "P1", "P2") and \
                        zeile["schluessel"] in ("crawled_not_indexed", "soft_404",
                                                "discovered_not_indexed",
                                                "duplicate_canonical"):
                    queue.append(f"- [ ] `{zeile['url']}` – {zeile['aktion']} "
                                 f"({zeile['grund']}) · {zeile['beleg']}")
            (ABDECKUNG / "redaktions_queue.md").write_text(
                "\n".join(queue) + "\n", encoding="utf-8")
            print(markdown)
            print(f"\n→ data/gsc/abdeckung/triage.json · triage.md · redaktions_queue.md")
            return 0

        if args.altlasten:
            wahrheit = repo_wahrheit()
            snap = lade_snapshot()
            k = kennzahlen(snap, wahrheit)
            print(f"Index-Altlasten: {k['index_puffer']} "
                  f"({k['indexiert']} im Index, {k['live_indexierbar']} indexierbar)")
            print("Das sind entfernte, weitergeleitete oder abgeschaltete URLs. "
                  "Sie stehen für Suchanfragen noch im Index.")
            nachfrage = _nachfrage_karte(None)
            live = set(wahrheit["indexierbar"])
            benannt = [(u, v) for u, v in nachfrage.items() if u not in live and v["impressionen"]]
            if benannt:
                print("\nMit belegter Nachfrage (Top-Seiten, 28 Tage):")
                for url, wert in sorted(benannt, key=lambda x: -x[1]["impressionen"])[:20]:
                    print(f"  {wert['impressionen']:3d} Impr.  Pos. {wert['position']}  {url}")
                print("\nEntscheidung je URL: Weiterleitung (data/weiterleitungen.yaml) "
                      "oder bewusst 404 (data/url_entfallen.yaml).")
            else:
                print("\nKeine dieser URLs hat in den letzten 28 Tagen Impressionen – "
                      "sie kosten kein Crawl-Budget, verzerren aber die Quote.")
            print("\nDie vollständige Liste der 117 indexierten URLs liefert nur die "
                  "Search Console (Indexierung → Seiten → „Indexierte Seiten“ "
                  "exportieren) – danach `--triage`.")
            return 0

        if args.kandidaten or args.vertrag or args.prioritaet or args.verlinkung:
            wahrheit = repo_wahrheit()
            if args.kandidaten:
                k = kandidatenraum(wahrheit, lade_snapshot() if AKTUELL.exists() else None)
                _json_schreiben(ABDECKUNG / "kandidaten.json", k)
                print(f"Kandidatenraum: {k['gesamt']} historische URLs ableitbar")
                print(f"  dokumentiert (Weiterleitung/404): {k['davon_dokumentiert']}")
                print(f"  ohne Entscheidung:                {k['davon_ohne_entscheidung']}")
                print(f"  Herkunft: {k['nach_herkunft']}")
                print("  Obergrenze, kein Nachweis – die Detail-Liste entscheidet.")
            if args.vertrag:
                v = vertrag(wahrheit, wahrheit.get("bau"))
                _json_schreiben(ABDECKUNG / "vertrag.json", v)
                print(f"\nVertrag: {v['status'].upper()}")
                for f in v["funde"]:
                    print(f"  🛑 [{f['regel']}] {f['text']}")
                print(f"  {len(v['noindex_ist'])} noindex-Seiten im Inhalt, "
                      f"{len(v['noindex_vertrag'])} im Vertrag, "
                      f"{len(v['gateways'])} Gateways")
            if args.prioritaet or args.verlinkung:
                vl = redaktionelle_links()
                if args.verlinkung:
                    auftrag = verlinkungs_auftrag(wahrheit, vl)
                    if args.apply:
                        titel = _titel_karte()
                        getan, fehl = [], []
                        for posten in auftrag[:args.max]:
                            pfad = _datei_zu_url(posten["quelle"])
                            if not pfad or not pfad.exists():
                                fehl.append((posten, "Quelldatei nicht gefunden"))
                                continue
                            ok, meldung = link_einfuegen(
                                pfad, posten["ziel"],
                                anker_kurz(titel.get(posten["ziel"], "Weiterlesen")))
                            (getan if ok else fehl).append((posten, meldung))
                        _historie_schreiben(getan)
                        print(f"Verlinkung: {len(getan)} eingefügt, {len(fehl)} nicht möglich")
                        for posten, meldung in getan:
                            print(f"  ✅ {posten['quelle']} → {posten['ziel']}")
                        for posten, meldung in fehl[:8]:
                            print(f"  ℹ️  {posten['quelle']}: {meldung}")
                    else:
                        _json_schreiben(ABDECKUNG / "verlinkungsauftrag.json", auftrag)
                        print(f"\nVerlinkungsauftrag: {len(auftrag)} Paare "
                              f"(mit `--apply --max N` schreiben)")
                        for posten in auftrag[:15]:
                            print(f"  {posten['quelle'][:56]:<56} → {posten['ziel'][:56]}")
                if args.prioritaet:
                    p2 = prioritaet(wahrheit, vl)
                    _json_schreiben(ABDECKUNG / "prioritaet.json", p2)
                    print(f"\nAnfrage-Wellen: {len(p2['welle1'])} / {len(p2['welle2'])} "
                          f"(Kontingent {p2['kontingent']}/Tag)")
                    print(f"  Seiten ohne redaktionellen Inlink: {p2['ohne_inlink']}")
                    for zeile in p2["seiten"][:10]:
                        print(f"  {zeile['score']:>5}  {zeile['url'][:60]:<60} "
                              f"{zeile['impressionen']:>3} Impr.  {zeile['grund']}")
            return 0

        if args.vorschlaege:
            roh = lade_export(Path(args.vorschlaege))
            urls = [d["url"] for d in roh.get("details") or []]
            if not urls:
                print("🛑 Keine URL in der Detail-Liste gefunden (Spalte „URL“).")
                return 1
            wahrheit = repo_wahrheit()
            for v in vorschlaege(urls, wahrheit):
                ziel = v["vorschlag"] or "–"
                print(f"{v['sicherheit']:<8} {v['url']:<60} → {ziel}  [{v['weg']}, Regel {v['regel']}]")
            print("\nKein Eintrag wurde geschrieben: Weiterleitungen entscheidet ein Mensch "
                  "(Regeln A–E in data/weiterleitungen.yaml).")
            return 0

        snapshot = lade_snapshot(Path(args.snapshot) if args.snapshot else None)
        wahrheit = repo_wahrheit()
        for bef in wahrheit.get("befunde") or []:
            print(f"ℹ️ [{bef['regel']}] {bef['text']}", file=sys.stderr)
        auswertung = auswerten(snapshot, wahrheit)

        if args.schreiben:
            _json_schreiben(BEFUND, auswertung)
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text("# Befund Abdeckung\n\n" + als_markdown(auswertung) + "\n",
                              encoding="utf-8")
        if args.kpi:
            k = auswertung["kpi"]
            print(f"Wochenkennzahlen ({len(k['reihen'])} Momentaufnahme(n))")
            print("| Datum | indexiert | nicht indexiert |")
            print("|---|---|---|")
            for w in k["wochen"]:
                print(f"| {w['datum']} | {w['indexiert']} | {w['nicht_indexiert']} |")
            return 0
        if args.abnahme:
            print("Abnahme")
            for x in auswertung["abnahme"]:
                zeichen = {"erfuellt": "✅", "offen": "🛑", "unbekannt": "❔"}.get(x["status"], "•")
                print(f"  {zeichen} {x['kriterium']}: {x['status']} ({x['messung']})")
                if x["naechster_schritt"] and x["status"] != "erfuellt":
                    print(f"      → {x['naechster_schritt']}")
            return 1 if any(x["status"] == "offen" for x in auswertung["abnahme"]) else 0
        if args.ursachen:
            ereignisse = None
            if not args.ohne_git:
                daten = [a["datum"] for a in auswertung["kennzahlen"]["anomalien"]
                         if a.get("datum")]
                if daten:
                    frueh = min(str(d)[:10] for d in daten)
                    try:
                        von = dt.date.fromisoformat(frueh) - dt.timedelta(days=10)
                        bis = dt.date.fromisoformat(max(str(d)[:10] for d in daten))
                    except ValueError:
                        von = bis = None
                    if von:
                        ereignisse = git_ereignisse(von, bis)
                        print(f"Git-Historie {von} … {bis}: "
                              f"{ereignisse.get('commits', 0)} Commits"
                              + ("  ⚠ Shallow-Clone – Beleg nur mit fetch-depth: 0"
                                 if ereignisse.get("shallow") else ""))
                        if not ereignisse.get("verfuegbar"):
                            print(f"  ⚠ {ereignisse.get('grund')}")
                        else:
                            for tag in sorted(ereignisse["tage"]):
                                e = ereignisse["tage"][tag]
                                print(f"  {tag}: {e['commits']:2d} Commits, "
                                      f"{e['content_dateien']:3d} Content-Dateien, "
                                      f"Entwürfe {e['draft_saldo']:+d}")
                                for top in e["top"]:
                                    print(f"      {top['sha']} {top['draft_neu']:+3d} Entwürfe  "
                                          f"{top['betreff'][:70]}")
            ursachen_liste = ursachen(
                auswertung["kennzahlen"],
                {"anzahl_taxonomie": sum(1 for g in auswertung.get("gruende", [])
                                         if g.get("schluessel") == "taxonomie")},
                ereignisse)
            _json_schreiben(ABDECKUNG / "ursachen.json",
                            {"erzeugt": dt.date.today().isoformat(),
                             "ereignisse": ereignisse, "ursachen": ursachen_liste})
            for u in ursachen_liste:
                print(f"\n{u['datum']} · {u['feld']} {u['delta']:+d} – {u['bewertung']}")
                if u.get("git"):
                    print(f"   Beleg: {u['git']['tag']}, {u['git']['draft_neu']} neue "
                          f"Beitragsentwürfe in {u['git']['content_dateien']} Dateien")
                for kandidat in u["kandidaten"]:
                    print(f"   Kandidat: {kandidat['klasse']} ({kandidat['anzahl']}), "
                          f"Abweichung {kandidat['abweichung_prozent']} %")
                print(f"   Prüfweg: {u['pruefweg']}")
            return 0

        if args.json:
            print(json.dumps(auswertung, ensure_ascii=False, indent=1))
        elif args.md:
            print(als_markdown(auswertung))
        else:
            drucke(auswertung)
        if args.gate:
            return 1 if auswertung["gate"]["status"] == "rot" else 0
        return 0
    except FileNotFoundError as exc:
        print(f"🛑 {exc}")
        return 2
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"🛑 Daten nicht lesbar: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
