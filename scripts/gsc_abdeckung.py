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

    python3 scripts/gsc_abdeckung.py --selftest         # 22 Fälle, offline

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

    impressionen = [z.get("impressionen") for z in verlauf if z.get("impressionen") is not None]
    live = wahrheit.get("anzahl_indexierbar") or 0
    return {
        "stand_datum": letzter.get("datum"),
        "export_alter_tage": alter,
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
    """Der vollständige Befund: Kennzahlen, Gründe, Widersprüche, Maßnahmen, Gate."""
    wahrheit = wahrheit or repo_wahrheit()
    kenn = kennzahlen(snapshot, wahrheit, heute)
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
    return auswertung


# --------------------------------------------------------------------------
#  Ausgabe
# --------------------------------------------------------------------------

# Anzeigenamen der Build-Klassen. Technische Schlüssel, lesbare Ausgabe.
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
        ("content/suche", "title: Suche\nrobotsNoIndex: true\nurl: \"/suche/\"\n"),
    ):
        p = wurzel / ordner
        p.mkdir(parents=True, exist_ok=True)
        (p / "index.md").write_text(f"---\n{fm}---\n\nText.\n", encoding="utf-8")
    (wurzel / "content" / "_index.md").write_text("---\ntitle: Start\n---\n", encoding="utf-8")
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
    """22 Fälle, alle offline. Geprüft wird die Klasse, nicht der Einzelfall."""
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
