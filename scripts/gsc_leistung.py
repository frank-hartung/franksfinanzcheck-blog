#!/usr/bin/env python3
"""gsc_leistung.py – die LEISTUNGS-Zentrale der Search Console.

WARUM DIESES MODUL EXISTIERT (Vorgang #1065, „GSC-Leistungsdaten 2026-11-04“)
---------------------------------------------------------------------------
Das Projekt holt seit dem 12.10.2026 täglich die Search-Console-Leistungsdaten
(`scripts/gsc_import.py`) – Klicks, Impressionen, CTR und Position je Tag, je
Seite, je Suchbegriff. Die Automatik funktioniert: am 05.11.2026 liegen 44
Messtage, 35 Seiten und 53 Suchbegriffe in `data/gsc/`. Was fehlt, ist die
Auswertung. Genau deshalb steht im täglichen Issue (#1065) der Abschnitt „Was zu
prüfen ist“ – drei Fragen an einen Menschen, obwohl jede davon aus denselben
vier Dateien beantwortbar ist.

Die Lücke ist nicht klein. Im Runbook steht seit dem 27.10.2026 die
redaktionelle Reihenfolge:

    „Seiten mit ausreichend Impressionen und Position 4–20 zuerst …“

– und kein einziges Skript erzeugt diese Liste. Eine Regel, die nur in Prosa
steht, befolgt niemand, der sie nicht gelesen hat; und niemand liest 74 KB
Optimierungsplan, bevor er einen Titel ändert. Die Daten lagen damit als Zahlen
vor, ohne je eine Entscheidung zu produzieren: 311 Impressionen in 44 Tagen,
null Klicks, 109 Live-Beiträge, von denen der Index fast keinen kennt.

Dieses Modul schließt die Lücke. Es ist das Gegenstück zum Abdeckungs-Bericht
(`scripts/gsc_abdeckung.py`): Der beantwortet „warum ist eine URL nicht im
Index?“, dieser beantwortet „was tun die Zahlen, die der Index bereits liefert?“.
Beide sind offline, deterministisch und ohne Netz – ein Befund ist
reproduzierbar, auch in einem Jahr.

WAS GEMESSEN WIRD (L1–L9)
  L1  DATEN-FRESCHE      Wie alt ist der letzte Import? Ein stehengebliebener
                         Lauf ist der teuerste Defekt, weil er aussieht wie
                         Ruhe: die Zahlen bleiben gültig, nur nicht mehr aktuell.
  L2  FENSTER            Deckt der Ledger das Fenster des Kopfs? Jeder Tag ohne
                         Zeile ist ein Tag, den Google gemessen hat und das Repo
                         nicht kennt.
  L3  TREND              Impressionen, Klicks, CTR über 7/28/90 Tage; Messtage
                         mit Impression; bester Tag; Richtung gegen das
                         Vorfenster. Ohne Vergleich ist eine Zahl keine Aussage.
  L4  SCHLAGDISTANZ      Inhaltsseiten mit Impressionen, null Klicks und
                         Position ≤ 20 – die dokumentierte Reihenfolge
                         („4–20 zuerst“), hier als Liste statt als Satz.
  L5  UNSICHTBARE SEITEN Live-Inhaltsseiten ohne eine einzige Impression im
                         Fenster. Das ist die eigentliche Reichweiten-Bremse.
  L6  NACHFRAGE          Suchbegriffe in Positions-Bänder. Ein Begriff mit
                         Nachfrage in Position 60 ist eine Inhalts-Aufgabe,
                         keine Meta-Aufgabe.
  L7  CTR-AUSFALL        Position ≤ 10, mindestens 5 Impressionen, null Klicks.
                         Hier kann es kein Zufall mehr sein – das Snippet trägt
                         nicht.
  L8  TOP-20-DRIFT       `data/top20_abbildungen.yaml` ist eine eingefrorene
                         Auswahl (Stand 19.10.2026), gewählt nach genau diesen
                         Impressionen. Driftet sie, gilt die Regel nicht mehr –
                         und die Abbildungs-Wache prüft eine veraltete Auswahl.
  L9  KREUZPRÜFUNG       Kopf gegen Ledger, Listen gegen Ledger: Summen, Tage,
                         CTR, Positionswerte. Zwei gültige Dateien können sich
                         weiterhin widersprechen – genau diese Klasse sieht
                         kein Syntax-Wächter.

WAS DAS MODUL AUSDRÜCKLICH NICHT TUT
  * Es ruft keine Suchmaschine auf. Google liefert die Zahlen, hier werden sie
    gelesen. Netz würde den Lauf un reproduzierbar machen.
  * Es schreibt keinen Artikel, keinen Titel, keine Description. Jede Aufgabe
    landet in `data/gsc/leistung/warteschlange.json` mit Eigentümer „Mensch“ –
    Text ist Redaktionsarbeit (CLAUDE.md, KI-Statut).
  * Es erfindet keine URL. Was nicht in den Listen steht, hat keine Impression –
    nicht „wenige“, keine.
  * Es bewertet kein Ranking als „gut“ oder „schlecht“. Es nennt die Zahl und
    die Regel, die auf sie passt.
  * Es wählt die Top-20-Auswahl NICHT täglich neu (L8). Ein Neuwählen würde 20
    Artikel jeden Tag anfassen; gemeldet wird die Drift, entschieden wird von
    Hand.

AUFRUF
  python3 scripts/gsc_leistung.py                  # rechnen + Artefakte schreiben
  python3 scripts/gsc_leistung.py --md             # Bericht für die Lauf-Zusammenfassung
  python3 scripts/gsc_leistung.py --json           # maschinenlesbar
  python3 scripts/gsc_leistung.py --issue          # Issue-Text auf stdout
  python3 scripts/gsc_leistung.py --check          # Tor: Exit 1 bei hartem Befund
  python3 scripts/gsc_leistung.py --selftest       # eingefrorene Fälle, offline

ARTEFAKTE
  data/gsc/leistung/befund.json         Befund (maschinenlesbar)
  data/gsc/leistung/befund.md           derselbe Befund als Bericht
  data/gsc/leistung/warteschlange.json  redaktionelle Aufgaben (P1–P3)
  data/gsc/leistung/verlauf.jsonl       eine Zeile je Lauf (append-only)

EXIT: 0 = grün · 1 = harter Befund (nur `--check`) · 2 = Werkzeugfehler
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
BERLIN = ZoneInfo("Europe/Berlin")
SCHEMA = 1


class LeistungsFehler(RuntimeError):
    """Werkzeugfehler: die Eingaben sind nicht einmal lesbar (Exit 2)."""


# --------------------------------------------------------------------------
#  Pfade – ein Ort, ein Satz. Der Selbsttest fährt dasselbe Modul gegen einen
#  Wegwerf-Baum, statt die globale Konstante zu verdrehen (Dauerregel: ein
#  Selbsttest urteilt über den Code, nicht über den Bestand).
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Pfade:
    wurzel: Path

    @property
    def gsc(self) -> Path:
        return self.wurzel / "data" / "gsc"

    @property
    def meta(self) -> Path:
        return self.gsc / "meta.json"

    @property
    def ledger(self) -> Path:
        return self.gsc / "tagesdaten.jsonl"

    @property
    def top_seiten(self) -> Path:
        return self.gsc / "top_seiten_28t.json"

    @property
    def top_suchbegriffe(self) -> Path:
        return self.gsc / "top_suchbegriffe_28t.json"

    @property
    def top20(self) -> Path:
        return self.wurzel / "data" / "top20_abbildungen.yaml"

    @property
    def content(self) -> Path:
        return self.wurzel / "content"

    @property
    def leistung(self) -> Path:
        return self.gsc / "leistung"

    @property
    def befund_json(self) -> Path:
        return self.leistung / "befund.json"

    @property
    def befund_md(self) -> Path:
        return self.leistung / "befund.md"

    @property
    def warteschlange(self) -> Path:
        return self.leistung / "warteschlange.json"

    @property
    def verlauf(self) -> Path:
        return self.leistung / "verlauf.jsonl"


PFADE = Pfade(ROOT)

# --------------------------------------------------------------------------
#  Schwellen – EINMAL hier, nicht an der Lesestelle. Hauskonvention: eine Zahl
#  mit Einheit braucht einen Ort (`serp_limits.py` für Metadaten, diese Datei
#  für die Leistungs-Schwellen).
# --------------------------------------------------------------------------
# Der Import läuft täglich. Zwei Tage Luft heißen: der dritte Tag ohne neuen
# Stand ist ein stehengebliebener Lauf (L1), nicht bloß ein ruhiger Tag.
FRISCH_TAGE = 2
# Unter dieser Anzahl Impressionen ist eine CTR-Aussage ein Rauschen. Google
# liefert für 3 Impressionen keine Schlussfolgerung – auch nicht „0 %“.
MIN_IMPRESSIONEN = 3
# Dokumentierte Reihenfolge aus docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md §6:
# „Seiten mit ausreichend Impressionen und Position 4–20 zuerst“.
POSITION_SCHLAGDISTANZ = 20
# Ab hier spricht nichts mehr für Zufall: Seite eins, und der Klick bleibt aus.
POSITION_CTR_ALARM = 10
# Ab dieser Impressionszahl gilt ein Suchbegriff als Nachfrage, nicht als
# Streifschuss eines einzelnen Nutzers.
MIN_NACHFRAGE = 5
# Jenseits der Schlagdistanz ist kein Klick realistisch: Ein Suchbegriff mit
# Nachfrage dort ist eine INHALTS-Aufgabe, keine Meta-Aufgabe. Deshalb
# dieselbe Grenze wie L4 – ein zweiter Wert wäre ein zweiter Maßstab.
# Mindest-Trefferquote der eingefrorenen Top-20-Auswahl gegen die aktuelle
# Reichweite, damit die Auswahlregel ihre Gültigkeit behält (L8).
DRIFT_GRENZE = 0.5
# Fenster der Top-Listen: `gsc_import.py` zieht sie über `ende - 27 … ende`.
TOP_FENSTER_TAGE = 28
# Toleranz der Kreuzprüfung zwischen Seiten-Liste und Tages-Ledger. Google
# aggregiert je Dimension und anonymisiert einzelne Suchbegriffe – die Summen
# sind deshalb NIE exakt gleich. Ein Unterschied innerhalb dieser Grenze ist
# Messtechnik, keiner ein Defekt; jenseits davon sind zwei Messungen nicht
# mehr vergleichbar und werden gemeldet (L9).
ABWEICHUNG_GRENZE = 0.25
# Hubs und Rechtsseiten tragen Vertrauen, keine Reichweite. Ein schwacher Title
# ist dort keine Aufgabe: Die Seite wird über die Navigation gefunden und über
# den Seitennamen gesucht. Gleiche Logik wie HUBS in `gsc_abdeckung.py`.
HUBS = ("/", "/posts/", "/pillar/", "/werkzeuge/", "/studien/", "/cockpit/")
RECHT = ("/impressum/", "/datenschutz/", "/ueber/", "/transparenz/", "/presse/",
         "/methodik/", "/aenderungsprotokoll/", "/so-entstehen-unsere-vergleiche/",
         "/newsletter/", "/newsletter-abmelden/", "/newsletter-bestaetigung/",
         "/newsletter-checkliste/", "/newsletter-praeferenzen/", "/suche/")
# Wer eine Aufgabe bekommt. Redaktion ist ein Mensch (CLAUDE.md, KI-Statut).
EIGENTUEMER = "Mensch (Redaktion)"


# --------------------------------------------------------------------------
#  Befunde
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Fund:
    """Ein Befund mit Regel, Beleg und nächstem Schritt.

    `beleg` ist Pflicht: Ein Befund ohne Zahl aus derselben Datei ist eine
    Meinung. `naechster_schritt` ist Pflicht: Ein Befund, den niemand bedienen
    kann, ist nur Lärm.
    """

    regel: str
    schwere: str          # "hart" | "hinweis"
    text: str
    beleg: str
    naechster_schritt: str

    def als_dict(self) -> dict:
        return {
            "regel": self.regel,
            "schwere": self.schwere,
            "text": self.text,
            "beleg": self.beleg,
            "naechster_schritt": self.naechster_schritt,
        }


# --------------------------------------------------------------------------
#  Lesen – nur die vier Dateien des Imports, nichts vom Netz
# --------------------------------------------------------------------------

def _les_json(pfad: Path):
    if not pfad.exists():
        raise LeistungsFehler(f"{pfad.name} fehlt – der Import hat nie geschrieben")
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LeistungsFehler(f"{pfad.name} ist nicht lesbar: {e}")


def les_meta(pfade: Pfade = PFADE) -> dict:
    daten = _les_json(pfade.meta)
    if not isinstance(daten, dict):
        raise LeistungsFehler("meta.json ist kein Objekt")
    return daten


def les_ledger(pfade: Pfade = PFADE) -> list[dict]:
    """Tagesledger: eine Zeile je Tag. Google liefert nur Tage mit Daten – ein
    Tag ohne Zeile ist kein Tag mit 0, sondern ein Tag, den die API nicht meldet."""
    if not pfade.ledger.exists():
        raise LeistungsFehler("tagesdaten.jsonl fehlt – der Import hat nie geschrieben")
    zeilen: list[dict] = []
    for roh in pfade.ledger.read_text(encoding="utf-8").splitlines():
        roh = roh.strip()
        if not roh:
            continue
        try:
            zeilen.append(json.loads(roh))
        except ValueError as e:
            raise LeistungsFehler(f"tagesdaten.jsonl: Zeile kein gültiges JSON ({e})")
    if not zeilen:
        raise LeistungsFehler("tagesdaten.jsonl ist leer – es gibt keinen Messtag")
    return zeilen


def les_top(pfad: Path, schluessel: str) -> list[dict]:
    daten = _les_json(pfad)
    if not isinstance(daten, list):
        raise LeistungsFehler(f"{pfad.name} ist keine Liste")
    for eintrag in daten:
        if schluessel not in eintrag:
            raise LeistungsFehler(f"{pfad.name}: Eintrag ohne „{schluessel}“")
    return daten


# --------------------------------------------------------------------------
#  Bestand: URL-Pfad → Seite (ableiten, nicht aufzählen)
# --------------------------------------------------------------------------

def _feld(front: str, key: str) -> str:
    m = re.search(rf'^\s*{key}:\s*"?([^"\n]*?)"?\s*$', front, re.M)
    return m.group(1).strip() if m else ""


def _front_und_body(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    teile = text[4:].split("\n---\n", 1)
    if len(teile) != 2:
        return "", text
    return teile[0], teile[1]


def url_pfad(datei: Path, wurzel: Path) -> str:
    """content/posts/<slug>/index.md → /posts/<slug>/ (Hugo-Permalinks des Projekts).

    Nur DIE Homepage (`content/_index.md`) mapped auf „/“. Der Fehler, der hier
    zuerst stand, nahm jedes `_index.md` als Homepage – damit landete
    `content/posts/_index.md` auf „/“, überschrieb den echten Homepage-Eintrag
    und die Beitrags-Übersicht tauchte im Bestand gar nicht auf. Ein stiller
    Vertauscher, den nur die Klassenprüfung sieht („/“ und „/posts/“ sind beide
    Hubs – die Auswirkung blieb klein, die Ursache bleibt ein Defekt).
    """
    rel = datei.relative_to(wurzel / "content")
    if rel.as_posix() == "_index.md":
        return "/"
    return "/" + rel.parent.as_posix() + "/"


def klasse(pfad_url: str) -> str:
    """Seitentyp. Nur beitrag/pillar/rechner/studie bekommen redaktionelle Aufgaben."""
    if pfad_url in RECHT:
        return "recht"
    if pfad_url in HUBS:
        return "hub"
    if pfad_url.startswith("/posts/"):
        return "beitrag"
    if pfad_url.startswith("/pillar/"):
        return "pillar"
    if pfad_url.startswith("/werkzeuge/"):
        return "rechner"
    if pfad_url.startswith("/studien/"):
        return "studie"
    return "sonstige"


def les_bestand(pfade: Pfade = PFADE) -> dict[str, dict]:
    """Alle Inhaltsseiten des Baums: URL-Pfad → {titel, description, lastmod, live, klasse}.

    Sowohl `index.md` (Einzelseiten) als auch `_index.md` (Abschnitts- und
    Homepage) werden gelesen. Der erste Wurf nahm nur `index.md` – damit fehlten
    die Homepage und jede Listenansicht im Bestand, und die Klassen-Regel
    überspielte die Lücke still. Eine Liste, die behauptet vollständig zu sein,
    darf keine Seite verschweigen.
    """
    bestand: dict[str, dict] = {}
    for datei in sorted(list(pfade.content.rglob("index.md"))
                        + list(pfade.content.rglob("_index.md"))):
        front, _body = _front_und_body(datei.read_text(encoding="utf-8"))
        pfad = url_pfad(datei, pfade.wurzel)
        bestand[pfad] = {
            "pfad": str(datei.relative_to(pfade.wurzel)),
            "titel": _feld(front, "title"),
            "description": _feld(front, "description"),
            "lastmod": _feld(front, "lastmod"),
            "live": not re.search(r"^draft:\s*true", front, re.M),
            "klasse": klasse(pfad),
        }
    return bestand


def pfad_aus_url(url: str) -> str:
    """https://franksfinanzcheck.de/posts/x/ → /posts/x/ (Prozent-Kodierung zurück)."""
    return unquote(urlparse(url).path) or "/"


# --------------------------------------------------------------------------
#  Kennzahlen
# --------------------------------------------------------------------------

def _zahl(wert) -> float:
    return float(wert or 0)


def fenster_summen(ledger: list[dict], tage: int) -> dict:
    """Summen der letzten `tage` MESSTAGE (nicht Kalendertage)."""
    teil = ledger[-tage:] if tage else []
    impressionen = sum(int(_zahl(r.get("impressions"))) for r in teil)
    klicks = sum(int(_zahl(r.get("clicks"))) for r in teil)
    return {
        "von": teil[0].get("datum") if teil else None,
        "bis": teil[-1].get("datum") if teil else None,
        "messtage": len(teil),
        "impressionen": impressionen,
        "klicks": klicks,
        "ctr": round(klicks / impressionen, 4) if impressionen else 0.0,
        "tage_mit_impression": sum(1 for r in teil if int(_zahl(r.get("impressions"))) > 0),
    }


def trend(ledger: list[dict]) -> dict:
    """7/28/90-Tage-Fenster plus Richtung des 28er-Fensters gegen das davor."""
    f7 = fenster_summen(ledger, 7)
    f28 = fenster_summen(ledger, 28)
    f90 = fenster_summen(ledger, 90)
    davor = ledger[-56:-28]
    impressionen_davor = sum(int(_zahl(r.get("impressions"))) for r in davor)
    klicks_davor = sum(int(_zahl(r.get("clicks"))) for r in davor)
    mit_daten = [r for r in ledger if int(_zahl(r.get("impressions"))) > 0]
    bester = max(ledger, key=lambda r: int(_zahl(r.get("impressions"))))
    return {
        "fenster_7": f7,
        "fenster_28": f28,
        "fenster_90": f90,
        "richtung": {
            "impressionen_vorher": impressionen_davor,
            "klicks_vorher": klicks_davor,
            "impressionen_delta": f28["impressionen"] - impressionen_davor,
            "klicks_delta": f28["klicks"] - klicks_davor,
        },
        "messtage_gesamt": len(ledger),
        "messtage_mit_impression": len(mit_daten),
        "bester_tag": {
            "datum": bester.get("datum"),
            "impressionen": int(_zahl(bester.get("impressions"))),
            "klicks": int(_zahl(bester.get("clicks"))),
        },
        "erster_tag": ledger[0].get("datum"),
        "letzter_tag": ledger[-1].get("datum"),
    }


# --------------------------------------------------------------------------
#  L4 Schlagdistanz / L7 CTR-Ausfall
# --------------------------------------------------------------------------

def schlagdistanz(top_seiten: list[dict], bestand: dict[str, dict]) -> list[dict]:
    """Inhaltsseiten mit Impressionen, null Klicks, Position ≤ 20.

    Die dokumentierte Reihenfolge („4–20 zuerst“) – hier als Liste statt als
    Satz im Runbook. Hubs und Rechtsseiten bleiben Kontext: Einen Title auf
    „Impressum“ zu optimieren ist keine Reichweiten-Arbeit.
    """
    treffer = []
    for eintrag in top_seiten:
        impressionen = int(_zahl(eintrag.get("impressions")))
        klicks = int(_zahl(eintrag.get("clicks")))
        position = _zahl(eintrag.get("position"))
        if impressionen < MIN_IMPRESSIONEN or klicks > 0:
            continue
        if not 0 < position <= POSITION_SCHLAGDISTANZ:
            continue
        pfad = pfad_aus_url(eintrag.get("seite", ""))
        seite = bestand.get(pfad, {})
        treffer.append({
            "url": eintrag.get("seite"),
            "pfad": pfad,
            "klasse": seite.get("klasse") or klasse(pfad),
            "titel": seite.get("titel", ""),
            "impressionen": impressionen,
            "position": round(position, 2),
            "beleg": f"{impressionen} Impressionen, 0 Klicks, Position {position:.2f}",
        })
    return sorted(treffer, key=lambda t: (-t["impressionen"], t["position"]))


def ctr_ausfall(top_seiten: list[dict], bestand: dict[str, dict]) -> list[dict]:
    """Position ≤ 10, mindestens 5 Impressionen, null Klicks – kein Zufall mehr.

    Die Klassenangabe ist Pflicht: `/posts/` und `/pillar/` sind HUBS. Ein
    Präfix-Vergleich (`startswith("/posts/")`) nimmt sie mit – und schon steht
    „Title der Beitrags-Übersicht optimieren" in der Warteschlange. Deshalb
    entscheidet die Klasse, nicht der Anfang des Pfads.
    """
    treffer = []
    for eintrag in top_seiten:
        impressionen = int(_zahl(eintrag.get("impressions")))
        klicks = int(_zahl(eintrag.get("clicks")))
        position = _zahl(eintrag.get("position"))
        if impressionen < 5 or klicks > 0 or not 0 < position <= POSITION_CTR_ALARM:
            continue
        pfad = pfad_aus_url(eintrag.get("seite"))
        treffer.append({
            "url": eintrag.get("seite"),
            "pfad": pfad,
            "klasse": bestand.get(pfad, {}).get("klasse") or klasse(pfad),
            "impressionen": impressionen,
            "position": round(position, 2),
            "beleg": f"{impressionen} Impressionen auf Position {position:.2f}, 0 Klicks",
        })
    return sorted(treffer, key=lambda t: (-t["impressionen"], t["position"]))


# --------------------------------------------------------------------------
#  L5 Unsichtbare Seiten
# --------------------------------------------------------------------------

def unsichtbare(top_seiten: list[dict], bestand: dict[str, dict]) -> dict:
    """Live-Inhaltsseiten ohne eine einzige Impression im 28-Tage-Fenster.

    Bewusst nicht pro Seite ein Befund: 90 Beiträge ohne Impression sind EIN
    Befund über den Index, nicht 90 Befunde über Beiträge. Die Zahl ist die
    Aussage – und sie zeigt, dass Snippet-Arbeit hier die falsche Ebene wäre.
    """
    sichtbar = {pfad_aus_url(e.get("seite", "")) for e in top_seiten
                if int(_zahl(e.get("impressions"))) > 0}
    inhaltsseiten = [p for p, s in bestand.items()
                     if s["live"] and s["klasse"] in ("beitrag", "pillar", "rechner", "studie")]
    ohne = [p for p in inhaltsseiten if p not in sichtbar]
    mit = [p for p in inhaltsseiten if p in sichtbar]
    neueste = sorted(ohne, key=lambda p: (bestand[p].get("lastmod") or "", p), reverse=True)[:10]
    return {
        "inhaltsseiten_gesamt": len(inhaltsseiten),
        "mit_impression": len(mit),
        "ohne_impression": len(ohne),
        "quote_mit_impression": round(len(mit) / len(inhaltsseiten), 4) if inhaltsseiten else 0.0,
        "neueste_ohne_impression": neueste,
    }


# --------------------------------------------------------------------------
#  L6 Nachfrage
# --------------------------------------------------------------------------

def _band(position: float) -> str:
    if position <= 10:
        return "1-10"
    if position <= 20:
        return "11-20"
    if position <= 50:
        return "21-50"
    if position <= 100:
        return "51-100"
    return ">100"


def nachfrage(top_suchbegriffe: list[dict]) -> dict:
    """Suchbegriffe in Positions-Bänder. Nachfrage ist keine Meta-Aufgabe."""
    baender: dict[str, list[dict]] = {"1-10": [], "11-20": [], "21-50": [], "51-100": [], ">100": []}
    for eintrag in top_suchbegriffe:
        position = _zahl(eintrag.get("position"))
        baender[_band(position)].append({
            "suchbegriff": eintrag.get("suchbegriff"),
            "impressionen": int(_zahl(eintrag.get("impressions"))),
            "klicks": int(_zahl(eintrag.get("clicks"))),
            "position": round(position, 2),
        })
    for liste in baender.values():
        liste.sort(key=lambda t: -t["impressionen"])
    ohne_wirkung = [t for name in ("21-50", "51-100", ">100") for t in baender[name]
                    if t["impressionen"] >= MIN_NACHFRAGE]
    return {
        "begriffe_gesamt": len(top_suchbegriffe),
        "baender": baender,
        "nachfrage_ohne_wirkung": ohne_wirkung,
    }


# --------------------------------------------------------------------------
#  L8 Top-20-Drift
# --------------------------------------------------------------------------

def top20_drift(pfade: Pfade, top_seiten: list[dict]) -> dict:
    """Die eingefrorene Top-20-Auswahl gegen die aktuellen Impressionen.

    `data/top20_abbildungen.yaml` ist eine Momentaufnahme (Stand 19.10.2026),
    gewählt nach genau diesen Impressionen. Der Import schreibt die Quelle
    täglich neu – die Auswahl selbst steht. Driftet sie unter die Grenze, gilt
    die Regel „Top-20 = Beiträge mit Impressionen“ nicht mehr, und
    `abbildungen_ableiten.py --check` prüft eine Auswahl, die niemand mehr
    begründen kann. Deshalb WIEDERVORLAGE, nicht Automatik: Ein tägliches
    Neuwählen würde 20 Artikel jeden Tag anfassen.
    """
    if not pfade.top20.exists():
        return {"vorhanden": False}
    text = pfade.top20.read_text(encoding="utf-8")
    slugs = re.findall(r'^\s*-\s*slug:\s*"([^"]+)"', text, re.M)
    m = re.search(r"^#.*?Stand\s+(\d{2})\.(\d{2})\.(\d{4})", text, re.M)
    stand = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""
    auswahl = {f"/posts/{s}/" for s in slugs}
    mit_impression = {pfad_aus_url(e.get("seite", "")) for e in top_seiten
                      if int(_zahl(e.get("impressions"))) > 0}
    beitraege = {p for p in mit_impression if p.startswith("/posts/")}
    treffer = auswahl & beitraege
    return {
        "vorhanden": True,
        "stand": stand,
        "auswahl": len(auswahl),
        "noch_mit_impression": len(treffer),
        "quote": round(len(treffer) / len(auswahl), 4) if auswahl else 0.0,
        "abgewaehlt": sorted(auswahl - beitraege),
        "neu_in_reichweite": sorted(beitraege - auswahl),
    }


# --------------------------------------------------------------------------
#  L1/L2/L9 Frische, Fenster, Kreuzprüfung
# --------------------------------------------------------------------------

def _parse_stand(meta: dict) -> dt.datetime | None:
    stand = meta.get("stand")
    if not isinstance(stand, str):
        return None
    try:
        return dt.datetime.strptime(stand, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def frische(meta: dict, heute: dt.date) -> dict:
    stand = _parse_stand(meta)
    if stand is None:
        return {"lesbar": False, "alter_tage": None, "stand": meta.get("stand"),
                "status": meta.get("status")}
    return {
        "lesbar": True,
        "stand": meta.get("stand"),
        "alter_tage": (heute - stand.astimezone(dt.timezone.utc).date()).days,
        "status": meta.get("status"),
    }


def top_fenster(meta: dict) -> tuple[dt.date | None, dt.date | None]:
    """Dasselbe Fenster, in dem `gsc_import.py` die Top-Listen zieht:
    `ende - 27 … ende`. Wer die Listen gegen ein anderes Fenster rechnet,
    erfindet einen Widerspruch, den die Daten nicht hergeben.
    """
    bis = (meta.get("zeitraum") or {}).get("bis")
    if not bis:
        return None, None
    try:
        ende = dt.date.fromisoformat(bis)
    except ValueError:
        return None, None
    return ende - dt.timedelta(days=TOP_FENSTER_TAGE - 1), ende


def fenster_meldungen(meta: dict, ledger: list[dict]) -> list[str]:
    """L2: Deckt der Ledger das Fenster des Kopfs?

    Bewusst NICHT gegen die Kalendertage gerechnet: Google liefert für die
    Datums-Dimension nur Tage MIT Daten. Ein 90-Tage-Fenster hat deshalb
    legitimerweise 44 Zeilen – das zu melden wäre ein Dauer-Befund ohne Defekt.
    Geprüft wird, was der Import selbst zusagt: der jüngste Messtag muss das
    Fensterende treffen (der Lauf endet immer am selben Tag), und
    `tage_gesamt` muss die Zeilen des Ledgers zählen.
    """
    meldungen: list[str] = []
    zeitraum = meta.get("zeitraum") or {}
    von, bis = zeitraum.get("von"), zeitraum.get("bis")
    gesamt = meta.get("tage_gesamt")
    if isinstance(gesamt, int) and gesamt != len(ledger):
        meldungen.append(f"meta.tage_gesamt={gesamt}, der Ledger hat {len(ledger)} Zeilen")
    letzter = ledger[-1].get("datum")
    if bis and letzter and letzter < bis:
        rueckstand = (dt.date.fromisoformat(bis) - dt.date.fromisoformat(letzter)).days
        meldungen.append(
            f"Jüngster Messtag {letzter} liegt {rueckstand} Tag(e) hinter zeitraum.bis {bis}")
    if von and letzter and letzter < von:
        meldungen.append(f"Jüngster Messtag {letzter} liegt vor zeitraum.von {von}")
    return meldungen


def kreuz_meldungen(meta: dict, ledger: list[dict], top_seiten: list[dict],
                    top_suchbegriffe: list[dict]) -> list[dict]:
    """L9: Kopf gegen Ledger, Listen gegen Ledger.

    Zwei gültige Dateien können sich weiterhin widersprechen – genau diese
    Klasse sieht kein Syntax-Wächter. Unterschieden wird zwischen zwei Arten:

    * RECHNEN (hart): `klicks_zeitraum`, CTR je Eintrag, Positionswerte. Das
      sind Zahlen DIESER Dateien; ein Widerspruch ist ohne Google prüfbar.
    * MESSEN (Hinweis): Die Summe der Seiten-Liste gegen das Tages-Ledger.
      Google aggregiert je Dimension und anonymisiert – die Summen sind nie
      exakt gleich. Jenseits der Toleranz sind zwei Messungen nicht mehr
      vergleichbar; WELCHE recht hat, kann nur die Search Console sagen.
      Deshalb Hinweis mit beiden Zahlen, kein Rot.
    """
    meldungen: list[dict] = []

    def hart(text: str) -> None:
        meldungen.append({"schwere": "hart", "text": text})

    def hinweis(text: str) -> None:
        meldungen.append({"schwere": "hinweis", "text": text})

    zeitraum = meta.get("zeitraum") or {}
    von, bis = zeitraum.get("von"), zeitraum.get("bis")
    tage_drin = [r for r in ledger if von and bis and von <= r.get("datum", "") <= bis]
    klicks = sum(int(_zahl(r.get("clicks"))) for r in tage_drin)
    if "klicks_zeitraum" in meta and meta["klicks_zeitraum"] != klicks:
        hart(f"meta.klicks_zeitraum={meta['klicks_zeitraum']}, der Ledger im Fenster hat {klicks}")
    for eintrag in top_seiten + top_suchbegriffe:
        name = eintrag.get("seite") or eintrag.get("suchbegriff") or "?"
        imp = int(_zahl(eintrag.get("impressions")))
        kli = int(_zahl(eintrag.get("clicks")))
        ctr = _zahl(eintrag.get("ctr"))
        position = _zahl(eintrag.get("position"))
        if imp > 0 and abs(ctr - kli / imp) > 0.01:
            hart(f"CTR weicht ab bei {name}: {ctr} statt {kli / imp:.2f}")
        if imp > 0 and not 0 < position <= 100:
            hart(f"Position außerhalb 1–100 bei {name}: {position}")
    von28, bis28 = top_fenster(meta)
    schnitt = sum(int(_zahl(e.get("impressions"))) for e in top_seiten)
    if von28 and bis28:
        # ISO-Strings vergleichen (das Ledger führt Datumszeichenketten).
        grenzen = (von28.isoformat(), bis28.isoformat())
        tage28 = [r for r in ledger if grenzen[0] <= r.get("datum", "") <= grenzen[1]]
        if tage28:
            summe28 = sum(int(_zahl(r.get("impressions"))) for r in tage28)
            if summe28 and abs(schnitt - summe28) > summe28 * ABWEICHUNG_GRENZE:
                hinweis(
                    f"top_seiten_28t.json summiert {schnitt} Impressionen, der Tages-Ledger "
                    f"im selben Fenster {grenzen[0]}…{grenzen[1]} hat {summe28}")
    return meldungen


# --------------------------------------------------------------------------
#  Befund
# --------------------------------------------------------------------------

def _de(zahl, stellen: int = 2) -> str:
    """Deutsche Zahlendarstellung – derselbe Lesestil wie in den Berichten."""
    if zahl is None:
        return "–"
    if isinstance(zahl, float):
        return f"{zahl:.{stellen}f}".replace(".", ",")
    return f"{zahl:,}".replace(",", ".")


def berechne_befund(meta: dict, ledger: list[dict], top_seiten: list[dict],
                    top_suchbegriffe: list[dict], bestand: dict[str, dict],
                    heute: dt.date, pfade: Pfade = PFADE) -> dict:
    frisch = frische(meta, heute)
    trend_daten = trend(ledger)
    schlag = schlagdistanz(top_seiten, bestand)
    ausfall = ctr_ausfall(top_seiten, bestand)
    unsicht = unsichtbare(top_seiten, bestand)
    nachfrage_daten = nachfrage(top_suchbegriffe)
    drift = top20_drift(pfade, top_seiten)
    funde: list[Fund] = []

    # ---- L1 Frische -----------------------------------------------------
    if not frisch["lesbar"]:
        funde.append(Fund(
            "L1", "hart", "meta.json trägt keinen lesbaren Stand.",
            f"stand={meta.get('stand')!r}",
            "Lauf prüfen: `.github/workflows/gsc-import.yml`, Schritt „Leistungsdaten holen“."))
    elif frisch["status"] != "ok":
        funde.append(Fund(
            "L1", "hinweis", f"Der Import meldet Status „{frisch['status']}“.",
            f"meta.json: {meta.get('grund') or 'kein Grund angegeben'}",
            "Status und Grund beheben (docs/ANLEITUNG-GSC-API-ZUGRIFF.md, Fehlerbilder)."))
    elif frisch["alter_tage"] > FRISCH_TAGE:
        funde.append(Fund(
            "L1", "hart",
            f"Der Leistungs-Import steht: Stand {frisch['stand']} ist {frisch['alter_tage']} Tage alt.",
            f"meta.json stand={frisch['stand']}",
            "Workflow-Lauf `gsc-import.yml` prüfen – die Zahlen bleiben gültig, "
            "aber sie beschreiben die Vergangenheit."))

    # ---- L2 Fenster -----------------------------------------------------
    for meldung in fenster_meldungen(meta, ledger):
        funde.append(Fund(
            "L2", "hinweis", "Kopf und Ledger decken sich nicht.", meldung,
            "Import-Lauf prüfen; `gsc_artefakte_guard.py --check` prüft die Dateien für sich."))

    # ---- L9 Kreuz -------------------------------------------------------
    for meldung in kreuz_meldungen(meta, ledger, top_seiten, top_suchbegriffe):
        if meldung["schwere"] == "hart":
            funde.append(Fund(
                "L9", "hart", "Zwei gültige Dateien widersprechen sich.", meldung["text"],
                "Nicht von Hand zusammensetzen – ein Lauf = eine Messung "
                "(`gsc_artefakte_guard.py --heal --rev <sha>`)."))
        else:
            funde.append(Fund(
                "L9", "hinweis", "Zwei Messungen desselben Fensters weichen ab.",
                meldung["text"],
                "In der Search Console „Leistung → Seiten“ gegen „Leistung → Täglich“ "
                "im selben Fenster vergleichen – Google aggregiert je Dimension."))

    # ---- L3 Trend -------------------------------------------------------
    f28 = trend_daten["fenster_28"]
    if f28["impressionen"] == 0:
        funde.append(Fund(
            "L3", "hinweis", "Keine einzige Impression in den letzten 28 Tagen.",
            f"Fenster {f28['von']}…{f28['bis']}: 0 Impressionen",
            "Indexierung zuerst (Abdeckungsbefund) – Reichweiten-Arbeit hat keine Grundlage."))
    elif f28["klicks"] == 0:
        funde.append(Fund(
            "L3", "hinweis",
            f"{_de(f28['impressionen'], 0)} Impressionen und null Klicks in 28 Tagen.",
            f"Fenster {f28['von']}…{f28['bis']}: CTR 0,00 %",
            "Reihenfolge beachten: erst Index (L5), dann Inhalt (L4/L6), dann Snippet."))
    delta = trend_daten["richtung"]["impressionen_delta"]
    if delta < 0:
        funde.append(Fund(
            "L3", "hinweis",
            f"Impressionen fallen: {_de(trend_daten['richtung']['impressionen_vorher'], 0)} → "
            f"{_de(f28['impressionen'], 0)} im 28-Tage-Vergleich.",
            f"Delta {delta}",
            "Gegen den Abdeckungsbefund rechnen (`npm run gsc:abdeckung:md`) – "
            "ein Rückgang ist meist ein Index-Rückgang."))

    # ---- L4 Schlagdistanz ----------------------------------------------
    aufgaben_faehig = [t for t in schlag if t["klasse"] in ("beitrag", "pillar", "rechner")]
    if aufgaben_faehig:
        funde.append(Fund(
            "L4", "hinweis",
            f"{len(aufgaben_faehig)} Inhaltsseite(n) in Schlagdistanz: Impressionen, null Klicks, "
            f"Position ≤ {POSITION_SCHLAGDISTANZ}.",
            "; ".join(f"{t['pfad']} ({t['beleg']})" for t in aufgaben_faehig[:6]),
            "Dokumentierte Reihenfolge: Suchintention prüfen, Fakten/Quellen aktualisieren, "
            "intern verlinken – erst dann Title/Description."))

    # ---- L7 CTR-Ausfall -------------------------------------------------
    if ausfall:
        funde.append(Fund(
            "L7", "hinweis",
            f"{len(ausfall)} Seite(n) auf Position ≤ {POSITION_CTR_ALARM} mit null Klicks.",
            "; ".join(f"{t['pfad']} ({t['beleg']})" for t in ausfall[:6]),
            "Title und Description gegen die Suchintention lesen; "
            "Snippet-Grenzen: `scripts/serp_limits.py`."))

    # ---- L5 Unsichtbare -------------------------------------------------
    if unsicht["inhaltsseiten_gesamt"]:
        quote = unsicht["quote_mit_impression"]
        if quote < 0.5:
            funde.append(Fund(
                "L5", "hinweis",
                f"Nur {unsicht['mit_impression']} von {unsicht['inhaltsseiten_gesamt']} Inhaltsseiten "
                f"hatten im Fenster eine Impression ({_de(quote * 100, 0)} %).",
                f"top_seiten_28t.json: {len(top_seiten)} Einträge",
                "Index-Arbeit hat Vorrang: `npm run gsc:abdeckung` und `npm run gsc:triage`."))
        else:
            funde.append(Fund(
                "L5", "hinweis",
                f"{unsicht['ohne_impression']} Inhaltsseite(n) ohne Impression im Fenster.",
                f"von {unsicht['inhaltsseiten_gesamt']} Inhaltsseiten",
                "Neueste zuerst prüfen – eine neue Seite braucht Crawl-Zeit, keine Eile."))

    # ---- L6 Nachfrage ---------------------------------------------------
    if nachfrage_daten["nachfrage_ohne_wirkung"]:
        funde.append(Fund(
            "L6", "hinweis",
            f"{len(nachfrage_daten['nachfrage_ohne_wirkung'])} Suchbegriff(e) mit Nachfrage "
            f"(≥ {MIN_NACHFRAGE} Impressionen) jenseits von Position {POSITION_SCHLAGDISTANZ} "
            "– dort ist kein Klick realistisch.",
            "; ".join(f"„{t['suchbegriff']}“ ({t['impressionen']}, Position {_de(t['position'])})"
                      for t in nachfrage_daten["nachfrage_ohne_wirkung"][:5]),
            "Inhalt vertiefen (Abschnitte, Belege, interne Links) – nicht den Title."))

    # ---- L8 Top-20-Drift ------------------------------------------------
    if drift.get("vorhanden") and drift["quote"] < DRIFT_GRENZE:
        funde.append(Fund(
            "L8", "hinweis",
            f"Die Top-20-Auswahl (Stand {drift['stand']}) trifft nur noch "
            f"{_de(drift['quote'] * 100, 0)} % der aktuellen Reichweite.",
            f"data/top20_abbildungen.yaml: {drift['noch_mit_impression']} von {drift['auswahl']}",
            "Auswahl erneuern (`python3 scripts/abbildungen_ableiten.py`) und `--check` fahren – "
            "dann erst die Abbildungen."))

    return {
        "schema": SCHEMA,
        "stand": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "heute": heute.isoformat(),
        "import": frisch,
        "trend": trend_daten,
        "seiten_mit_impression": sum(1 for e in top_seiten if int(_zahl(e.get("impressions"))) > 0),
        "schlagdistanz": schlag,
        "ctr_ausfall": ausfall,
        "unsichtbare": unsicht,
        "nachfrage": nachfrage_daten,
        "top20_drift": drift,
        "funde": [f.als_dict() for f in funde],
        "hart": [f.als_dict() for f in funde if f.schwere == "hart"],
    }


# --------------------------------------------------------------------------
#  Warteschlange – was zu tun ist, in Reihenfolge
# --------------------------------------------------------------------------

def warteschlange(befund: dict) -> list[dict]:
    """Redaktionelle Aufgaben aus den Befunden, absteigend nach Wirkung.

    ZWEI REGELN, DIE DIESE LISTE EINHAELT

    1. INDEX VOR INHALT, INHALT VOR SNIPPET. Ein Title auf einer Seite, die
       Google nicht kennt, ist Arbeit ohne Leser. Deshalb steht die Index-Arbeit
       (L5) immer oben – und pro Seite gilt die dokumentierte Reihenfolge aus
       docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md §6: Suchintention prüfen, Fakten
       und Quellen aktualisieren, intern verlinken – und ERST DANN den Title.

    2. EINE SEITE, EINE AUFGABE. L4 (Schlagdistanz) und L7 (Seite eins ohne
       Klick) können dieselbe Seite treffen. Zwei Einträge mit derselben URL
       und demselben Beleg sind keine zwei Aufgaben, sondern Rauschen. Die
       Priorität kommt aus dem stärkeren Signal.

    Klassen entscheiden, nicht Pfad-Anfänge: `/posts/` und `/pillar/` sind
    Hubs. Sie erscheinen im Befund als Kontext und bekommen keine Aufgabe.
    """
    aufgaben: list[dict] = []

    def aufgabe(prio: str, titel: str, url: str, beleg: str, schritt: str, regel: str) -> None:
        aufgaben.append({
            "prio": prio,
            "titel": titel,
            "url": url,
            "beleg": beleg,
            "naechster_schritt": schritt,
            "regel": regel,
            "eigentuemer": EIGENTUEMER,
        })

    # ---- 1 · Index (L5): ohne ihn ist jede andere Arbeit hier wirkungslos --
    unsicht = befund["unsichtbare"]
    if unsicht.get("inhaltsseiten_gesamt") and unsicht["quote_mit_impression"] < 0.5:
        aufgabe(
            "P1", "Index-Arbeit: Abdeckungsbefund und Triage gegen den Bestand rechnen", "",
            f"{unsicht['mit_impression']} von {unsicht['inhaltsseiten_gesamt']} Inhaltsseiten mit "
            f"Impression, {unsicht['ohne_impression']} ohne",
            "`npm run gsc:abdeckung` → `npm run gsc:triage` → Entscheidungen festhalten "
            "(`--entscheiden`)", "L5")

    # ---- 2 · Inhalt vor Snippet (L4 + L7 zusammengeführt) -----------------
    schritt_seite = ("Suchintention prüfen, Fakten/Quellen aktualisieren, intern verlinken – "
                     "erst dann Title/Description")
    seiten: dict[str, dict] = {}
    for treffer in befund["ctr_ausfall"]:
        if treffer["klasse"] in ("beitrag", "pillar", "rechner", "studie"):
            seiten[treffer["pfad"]] = {**treffer, "prio": "P1"}
    for treffer in befund["schlagdistanz"]:
        if treffer["klasse"] in ("beitrag", "pillar", "rechner", "studie"):
            seiten.setdefault(treffer["pfad"], {**treffer, "prio": "P2"})
    for pfad in sorted(seiten, key=lambda p: (seiten[p]["prio"], -seiten[p]["impressionen"])):
        treffer = seiten[pfad]
        aufgabe(treffer["prio"], f"Inhalt und Snippet prüfen: {pfad}", treffer["url"],
                treffer["beleg"], schritt_seite,
                "L7" if treffer["prio"] == "P1" else "L4")

    # ---- 3 · Nachfrage bedienen (L6) --------------------------------------
    for begriff in befund["nachfrage"]["nachfrage_ohne_wirkung"][:10]:
        aufgabe(
            "P2", f"Nachfrage bedienen: „{begriff['suchbegriff']}“", "",
            f"{begriff['impressionen']} Impressionen, Position {_de(begriff['position'])}",
            "Thema im passenden Beitrag vertiefen (Abschnitt, Belege, interne Links)", "L6")

    # ---- 4 · Auswahl erneuern (L8) ----------------------------------------
    drift = befund["top20_drift"]
    if drift.get("vorhanden") and drift["quote"] < DRIFT_GRENZE:
        aufgabe(
            "P3", "Top-20-Auswahl der Abbildungen erneuern", "",
            f"data/top20_abbildungen.yaml Stand {drift['stand']}: "
            f"{drift['noch_mit_impression']} von {drift['auswahl']} noch in Reichweite",
            "`python3 scripts/abbildungen_ableiten.py` → `--check`", "L8")

    return aufgaben


# --------------------------------------------------------------------------
#  Ausgabe
# --------------------------------------------------------------------------

def als_markdown(befund: dict) -> str:
    f28 = befund["trend"]["fenster_28"]
    import_status = befund["import"]
    zeilen = [
        "### 📈 Leistung (Search Console, 28 Tage)",
        "",
        f"Stand: **{import_status.get('stand') or '–'}** · Status: "
        f"**{import_status.get('status') or '–'}** · Fenster: {f28['von']} … {f28['bis']}",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Impressionen (28 Tage) | {_de(f28['impressionen'], 0)} |",
        f"| Klicks (28 Tage) | {_de(f28['klicks'], 0)} |",
        f"| CTR | {_de(f28['ctr'] * 100)} % |",
        f"| Messtage mit Impression | {f28['tage_mit_impression']} von {f28['messtage']} |",
        f"| Bester Tag | {befund['trend']['bester_tag']['datum']} "
        f"({_de(befund['trend']['bester_tag']['impressionen'], 0)}) |",
        f"| Seiten mit Impression | {befund['seiten_mit_impression']} |",
        f"| Inhaltsseiten mit Impression | {befund['unsichtbare']['mit_impression']} von "
        f"{befund['unsichtbare']['inhaltsseiten_gesamt']} |",
        f"| Suchbegriffe mit Impression | {befund['nachfrage']['begriffe_gesamt']} |",
        "",
    ]
    if befund["funde"]:
        zeilen += ["**Befunde**", "", "| Regel | Schwere | Befund | Beleg |", "|---|---|---|---|"]
        for fund in befund["funde"]:
            zeilen.append(f"| {fund['regel']} | {fund['schwere']} | {fund['text']} | {fund['beleg']} |")
        zeilen.append("")
    else:
        zeilen += ["✅ Kein Befund: Daten frisch, Fenster vollständig, in sich stimmig.", ""]
    aufgaben = warteschlange(befund)
    if aufgaben:
        zeilen += ["**Was zu tun ist (Warteschlange)**", "",
                   "| Prio | Aufgabe | Beleg | Nächster Schritt |", "|---|---|---|---|"]
        for a in aufgaben[:12]:
            zeilen.append(f"| {a['prio']} | {a['url'] or a['titel']} | {a['beleg']} | "
                          f"{a['naechster_schritt']} |")
        zeilen.append("")
    zeilen += ["Reihenfolge: erst Index, dann Inhalt, dann Snippet. "
               "Vollständiger Befund: `data/gsc/leistung/befund.md`."]
    return "\n".join(zeilen) + "\n"


def als_issue(befund: dict) -> str:
    f28 = befund["trend"]["fenster_28"]
    import_status = befund["import"]
    aufgaben = warteschlange(befund)
    zeilen = [
        "Automatische Auswertung der Search-Console-Leistungsdaten "
        f"({import_status.get('stand') or '–'}).",
        "",
        "**Zahlen**",
        "",
        f"- Impressionen (28 Tage): **{_de(f28['impressionen'], 0)}** "
        f"({f28['tage_mit_impression']} von {f28['messtage']} Messtagen)",
        f"- Klicks (28 Tage): **{_de(f28['klicks'], 0)}** · CTR {_de(f28['ctr'] * 100)} %",
        f"- Inhaltsseiten mit Impression: **{befund['unsichtbare']['mit_impression']} von "
        f"{befund['unsichtbare']['inhaltsseiten_gesamt']}**",
        f"- Suchbegriffe mit Impression: **{befund['nachfrage']['begriffe_gesamt']}**",
        "",
    ]
    if befund["hart"]:
        zeilen += ["**Harte Befunde (Daten oder Lauf)**", ""]
        zeilen += [f"- 🛑 **{f['regel']}** {f['text']} — Beleg: {f['beleg']} → {f['naechster_schritt']}"
                   for f in befund["hart"]]
        zeilen.append("")
    if aufgaben:
        zeilen += ["**Was zu tun ist**", ""]
        zeilen += [f"- **{a['prio']}** {a['url'] or a['titel']} — {a['beleg']} → "
                   f"{a['naechster_schritt']}" for a in aufgaben[:12]]
        zeilen.append("")
    zeilen += [
        "Keine Schlüssel, keine Tokens, keine Personenbezüge in diesem Issue.",
        "Erzeuger: `scripts/gsc_leistung.py` · Befund: `data/gsc/leistung/befund.md`.",
    ]
    return "\n".join(zeilen) + "\n"


def schreibe(befund: dict, pfade: Pfade = PFADE) -> list[str]:
    """Artefakte schreiben. Der Verlauf ist append-only – ein Lauf = eine Zeile."""
    pfade.leistung.mkdir(parents=True, exist_ok=True)
    pfade.befund_json.write_text(json.dumps(befund, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    pfade.befund_md.write_text(als_markdown(befund), encoding="utf-8")
    aufgaben = warteschlange(befund)
    pfade.warteschlange.write_text(
        json.dumps({"schema": SCHEMA, "stand": befund["stand"], "aufgaben": aufgaben},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zeile = {
        "stand": befund["stand"],
        "import_status": befund["import"].get("status"),
        "import_alter_tage": befund["import"].get("alter_tage"),
        "impressionen_28": befund["trend"]["fenster_28"]["impressionen"],
        "klicks_28": befund["trend"]["fenster_28"]["klicks"],
        "seiten_mit_impression": befund["seiten_mit_impression"],
        "inhaltsseiten_mit_impression": befund["unsichtbare"]["mit_impression"],
        "inhaltsseiten": befund["unsichtbare"]["inhaltsseiten_gesamt"],
        "begriffe": befund["nachfrage"]["begriffe_gesamt"],
        "funde": len(befund["funde"]),
        "hart": len(befund["hart"]),
        "aufgaben": len(aufgaben),
    }
    with pfade.verlauf.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    return [str(p.relative_to(pfade.wurzel)) for p in
            (pfade.befund_json, pfade.befund_md, pfade.warteschlange, pfade.verlauf)]


# --------------------------------------------------------------------------
#  Selbsttest – prüft DIESES Modul, ohne Netz, ohne den echten Bestand
# --------------------------------------------------------------------------

def _fixture(tmp: Path) -> Pfade:
    """Ein vollständiger Minit-Baum: vier Import-Dateien + vier Inhaltsseiten."""
    pfade = Pfade(tmp)
    pfade.gsc.mkdir(parents=True, exist_ok=True)
    (tmp / "data" / "top20_abbildungen.yaml").write_text(
        "# Top-20 für eigene Abbildungen – verbindlich, Stand 19.10.2026.\n"
        'beitraege:\n  - slug: "a-sichtbar"\n  - slug: "b-sichtbar"\n', encoding="utf-8")
    pfade.meta.write_text(json.dumps({
        "stand": "2026-11-04T10:00:00Z",
        "quelle": "test", "site": "sc-domain:x.de",
        "zeitraum": {"von": "2026-10-30", "bis": "2026-11-01"},
        "status": "ok", "grund": "",
        "tage_neu": 3, "tage_gesamt": 3, "klicks_zeitraum": 1,
    }), encoding="utf-8")
    pfade.ledger.write_text(
        '{"datum": "2026-10-30", "clicks": 0, "impressions": 10, "ctr": 0.0, "position": 12.0}\n'
        '{"datum": "2026-10-31", "clicks": 1, "impressions": 20, "ctr": 0.05, "position": 8.0}\n'
        '{"datum": "2026-11-01", "clicks": 0, "impressions": 6, "ctr": 0.0, "position": 15.0}\n',
        encoding="utf-8")
    pfade.top_seiten.write_text(json.dumps([
        {"seite": "https://x.de/posts/a-sichtbar/", "clicks": 0, "impressions": 12, "ctr": 0.0, "position": 9.0},
        {"seite": "https://x.de/posts/b-sichtbar/", "clicks": 0, "impressions": 8, "ctr": 0.0, "position": 4.5},
        {"seite": "https://x.de/impressum/", "clicks": 0, "impressions": 9, "ctr": 0.0, "position": 3.0},
        {"seite": "https://x.de/posts/c-unsichtbar/", "clicks": 0, "impressions": 4, "ctr": 0.0, "position": 41.0},
    ]), encoding="utf-8")
    pfade.top_suchbegriffe.write_text(json.dumps([
        {"suchbegriff": "nachfrage ohne wirkung", "clicks": 0, "impressions": 9, "ctr": 0.0, "position": 61.0},
        {"suchbegriff": "kurzer treffer", "clicks": 0, "impressions": 1, "ctr": 0.0, "position": 12.0},
    ]), encoding="utf-8")
    for slug, lastmod in (("a-sichtbar", "2026-10-01"), ("b-sichtbar", "2026-10-02"),
                          ("c-unsichtbar", "2026-10-03"), ("d-nie-gesehen", "2026-10-04")):
        ordner = tmp / "content" / "posts" / slug
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "index.md").write_text(
            "---\n"
            f'title: "Titel {slug}"\n'
            'description: "Beschreibung"\n'
            f"lastmod: {lastmod}\n"
            "draft: false\n"
            "---\n\nText.\n", encoding="utf-8")
    return pfade


def _selftest() -> int:
    import tempfile

    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool, detail: str = "") -> None:
        if bedingung:
            print(f"  ✅ {name}")
        else:
            fehler.append(f"{name}{(': ' + detail) if detail else ''}")
            print(f"  ❌ {name}{(': ' + detail) if detail else ''}")

    # ---- 1) Der gute Lauf: frische Daten, vollständiges Fenster -----------
    with tempfile.TemporaryDirectory() as tmp:
        pfade = _fixture(Path(tmp))
        heute = dt.date(2026, 11, 4)
        meta = les_meta(pfade)
        ledger = les_ledger(pfade)
        seiten = les_top(pfade.top_seiten, "seite")
        begriffe = les_top(pfade.top_suchbegriffe, "suchbegriff")
        bestand = les_bestand(pfade)
        befund = berechne_befund(meta, ledger, seiten, begriffe, bestand, heute, pfade)

        pruefe("Fixture: vier Inhaltsseiten gelesen", len(bestand) == 4, str(len(bestand)))
        pruefe("L1: frischer Stand ist kein Fund",
               not any(f["regel"] == "L1" for f in befund["funde"]))
        pruefe("L2: vollständiges Fenster ist kein Fund",
               not any(f["regel"] == "L2" for f in befund["funde"]))
        pruefe("L9: stimmige Kreuzprüfung ist kein Fund",
               not any(f["regel"] == "L9" for f in befund["funde"]))
        pruefe("kein harter Fund im guten Lauf", not befund["hart"],
               str([f["regel"] for f in befund["hart"]]))

        # L4: a-sichtbar (9,0) und b-sichtbar (4,5) sind in Schlagdistanz,
        # c-unsichtbar (41,0) nicht. /impressum/ (3,0) ist Recht: Kontext im
        # Befund, aber NIE eine redaktionelle Aufgabe.
        pfade_schlag = {t["pfad"] for t in befund["schlagdistanz"]}
        pruefe("L4: genau die drei Seiten in Schlagdistanz",
               pfade_schlag == {"/posts/a-sichtbar/", "/posts/b-sichtbar/", "/impressum/"},
               str(sorted(pfade_schlag)))
        pruefe("L4: Rechtsseite wird als Recht erkannt",
               all(t["klasse"] == "recht" for t in befund["schlagdistanz"]
                   if t["pfad"] == "/impressum/"))
        # Eine Seite, eine Aufgabe: L7 (P1) schlägt L4 (P2) für dieselbe URL.
        aufgaben_seite = [a for a in warteschlange(befund) if a["regel"] in ("L4", "L7")]
        pruefe("Warteschlange: genau zwei Seiten-Aufgaben (eine je URL)",
               sorted(a["url"] for a in aufgaben_seite) ==
               ["https://x.de/posts/a-sichtbar/", "https://x.de/posts/b-sichtbar/"],
               str([a["url"] for a in aufgaben_seite]))
        pruefe("Warteschlange: Hubs bekommen keine Aufgabe",
               all(not a["url"].endswith(("/posts/", "/pillar/")) for a in aufgaben_seite),
               str([a["url"] for a in aufgaben_seite]))
        pruefe("Warteschlange: Reihenfolge Inhalt vor Snippet",
               all("erst dann Title" in a["naechster_schritt"] for a in aufgaben_seite),
               str([a["naechster_schritt"] for a in aufgaben_seite]))
        pruefe("Warteschlange: L7-Seite ist P1",
               all(a["prio"] == "P1" for a in aufgaben_seite
                   if a["regel"] == "L7"),
               str([(a["regel"], a["prio"]) for a in aufgaben_seite]))

        # L7: Position ≤ 10, Impressionen ≥ 5, null Klicks → a-sichtbar (9,0),
        # b-sichtbar (4,5) und /impressum/ (3,0). c-unsichtbar (41,0) liegt
        # jenseits der Schwelle.
        l7 = {t["pfad"] for t in befund["ctr_ausfall"]}
        pruefe("L7: alle Seiten auf Position ≤ 10 mit ≥ 5 Impressionen",
               l7 == {"/posts/a-sichtbar/", "/posts/b-sichtbar/", "/impressum/"},
               str(sorted(l7)))
        pruefe("L7: Rechtsseite wird als Recht erkannt",
               all(t["klasse"] == "recht" for t in befund["ctr_ausfall"]
                   if t["pfad"] == "/impressum/"))

        unsicht = befund["unsichtbare"]
        pruefe("L5: eine von vier Inhaltsseiten ohne Impression",
               unsicht["ohne_impression"] == 1 and unsicht["mit_impression"] == 3,
               f"{unsicht['ohne_impression']}/{unsicht['mit_impression']}")
        pruefe("L5: neueste unsichtbare Seite zuerst",
               unsicht["neueste_ohne_impression"] == ["/posts/d-nie-gesehen/"],
               str(unsicht["neueste_ohne_impression"]))

        begriffe_nachfrage = {t["suchbegriff"] for t in befund["nachfrage"]["nachfrage_ohne_wirkung"]}
        pruefe("L6: nur der Begriff mit Nachfrage jenseits Position 20",
               begriffe_nachfrage == {"nachfrage ohne wirkung"}, str(begriffe_nachfrage))

        pruefe("L8: Stand der Auswahl wird gelesen",
               befund["top20_drift"]["stand"] == "2026-10-19", befund["top20_drift"]["stand"])
        pruefe("L8: 50 % Treffer ist kein Befund",
               not any(f["regel"] == "L8" for f in befund["funde"]),
               f"quote={befund['top20_drift']['quote']}")

        f28 = befund["trend"]["fenster_28"]
        pruefe("Trend: 36 Impressionen, 1 Klick über drei Messtage",
               f28["impressionen"] == 36 and f28["klicks"] == 1,
               f"{f28['impressionen']}/{f28['klicks']}")
        pruefe("Trend: bester Tag ist der 31.10.",
               befund["trend"]["bester_tag"]["datum"] == "2026-10-31")

        md = als_markdown(befund)
        pruefe("Markdown nennt Impressionen und CTR",
               "Impressionen (28 Tage)" in md and "| CTR |" in md)
        issue = als_issue(befund)
        pruefe("Issue nennt die Zahlen und keinen Schlüssel",
               "Impressionen (28 Tage)" in issue and "PRIVATE" not in issue)

        geschrieben = schreibe(befund, pfade)
        pruefe("Schreiben: vier Artefakte", len(geschrieben) == 4, str(geschrieben))
        pruefe("Schreiben: Verlauf hat genau eine Zeile",
               len(pfade.verlauf.read_text(encoding="utf-8").strip().splitlines()) == 1)
        pruefe("Schreiben: Warteschlange ist gültiges JSON",
               isinstance(json.loads(pfade.warteschlange.read_text(encoding="utf-8"))["aufgaben"], list))
        pruefe("Schreiben: Befund ist gültiges JSON",
               json.loads(pfade.befund_json.read_text(encoding="utf-8"))["schema"] == SCHEMA)

    # ---- 2) Stehender Import: L1 hart ------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        pfade = _fixture(Path(tmp))
        daten = json.loads(pfade.meta.read_text(encoding="utf-8"))
        daten["stand"] = "2026-10-20T10:00:00Z"      # 15 Tage alt
        pfade.meta.write_text(json.dumps(daten), encoding="utf-8")
        frisch = frische(daten, dt.date(2026, 11, 4))
        pruefe("L1: 15 Tage Alter erkannt", frisch["alter_tage"] == 15, str(frisch["alter_tage"]))
        befund = berechne_befund(daten, les_ledger(pfade), les_top(pfade.top_seiten, "seite"),
                                 les_top(pfade.top_suchbegriffe, "suchbegriff"),
                                 les_bestand(pfade), dt.date(2026, 11, 4), pfade)
        fund = [f for f in befund["hart"] if f["regel"] == "L1"]
        pruefe("L1: stehengebliebener Import ist HART", len(fund) == 1,
               str([f["regel"] for f in befund["hart"]]))
        pruefe("L1: Befund nennt Stand und nächsten Schritt",
               bool(fund) and "2026-10-20" in fund[0]["text"] and bool(fund[0]["naechster_schritt"]))

    # ---- 3) Widerspruch zwischen Kopf und Ledger: L9 hart ---------------
    with tempfile.TemporaryDirectory() as tmp:
        pfade = _fixture(Path(tmp))
        meta = {
            "stand": "2026-11-04T10:00:00Z", "status": "ok",
            "zeitraum": {"von": "2026-10-01", "bis": "2026-11-01"},
            "tage_gesamt": 99, "klicks_zeitraum": 77,
        }
        ledger = [{"datum": "2026-10-30", "clicks": 1, "impressions": 10, "ctr": 0.1, "position": 5.0}]
        meldungen = kreuz_meldungen(meta, ledger, [], [])
        rechnung = [m for m in meldungen if "klicks_zeitraum" in m["text"]]
        pruefe("L9: klicks_zeitraum gegen Ledger erkannt", len(rechnung) == 1, str(meldungen))
        pruefe("L9: Rechen-Widerspruch ist HART",
               bool(rechnung) and rechnung[0]["schwere"] == "hart", str(meldungen))
        fenster = fenster_meldungen(meta, ledger)
        pruefe("L2: tage_gesamt gegen Ledger erkannt",
               any("tage_gesamt" in m for m in fenster), str(fenster))
        pruefe("L2: zurückliegender jüngster Messtag erkannt",
               any("hinter zeitraum.bis" in m for m in fenster), str(fenster))
        befund = berechne_befund(meta, ledger, [], [], {}, dt.date(2026, 11, 4), pfade)
        pruefe("L9: Widerspruch ist HART",
               any(f["regel"] == "L9" for f in befund["hart"]),
               str([f["regel"] for f in befund["hart"]]))
        pruefe("L2: Fensterlücke ist HINWEIS, nicht hart",
               any(f["regel"] == "L2" and f["schwere"] == "hinweis" for f in befund["funde"]))
        # meta ohne klicks_zeitraum: nur die Mess-Abweichung bleibt übrig.
        meta_messung = {k: v for k, v in meta.items() if k != "klicks_zeitraum"}
        abweichung = kreuz_meldungen(
            meta_messung, ledger,
            [{"seite": "https://x.de/a/", "clicks": 0, "impressions": 99,
              "ctr": 0.0, "position": 5.0}], [])
        pruefe("L9: große Abweichung der Messungen wird gemeldet",
               any("summiert" in m["text"] for m in abweichung), str(abweichung))
        pruefe("L9: Abweichung der Messungen ist HINWEIS, nicht hart",
               all(m["schwere"] == "hinweis" for m in abweichung), str(abweichung))
        pruefe("L9: kleine Abweichung bleibt stumm",
               not kreuz_meldungen(meta_messung, ledger,
                                   [{"seite": "https://x.de/a/", "clicks": 0, "impressions": 11,
                                     "ctr": 0.0, "position": 5.0}], []))
        pruefe("L9: CTR-Arithmetik ist HART",
               all(m["schwere"] == "hart" for m in kreuz_meldungen(
                   meta_messung, ledger,
                   [{"seite": "https://x.de/a/", "clicks": 3, "impressions": 10,
                     "ctr": 0.9, "position": 5.0}], [])))

    # ---- 4) Kaputte Eingabe ist ein Werkzeugfehler, kein Befund ----------
    with tempfile.TemporaryDirectory() as tmp:
        pfade = Pfade(Path(tmp))          # leerer Baum, data/gsc/ existiert nicht
        try:
            les_meta(pfade)
            pruefe("fehlende meta.json wirft LeistungsFehler", False)
        except LeistungsFehler:
            pruefe("fehlende meta.json wirft LeistungsFehler", True)
        pfade.gsc.mkdir(parents=True, exist_ok=True)
        pfade.ledger.write_text('{"datum": "2026-10-30"}\nkein json\n', encoding="utf-8")
        try:
            les_ledger(pfade)
            pruefe("kaputte Ledger-Zeile wirft LeistungsFehler", False)
        except LeistungsFehler:
            pruefe("kaputte Ledger-Zeile wirft LeistungsFehler", True)
        pfade.ledger.write_text("", encoding="utf-8")
        try:
            les_ledger(pfade)
            pruefe("leerer Ledger wirft LeistungsFehler", False)
        except LeistungsFehler:
            pruefe("leerer Ledger wirft LeistungsFehler", True)

    if fehler:
        print("❌ GSC-LEISTUNG-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ GSC-LEISTUNG-SELBSTTEST bestanden (L1–L9, Warteschlange, Artefakte, Fehlerpfad).")
    return 0


# --------------------------------------------------------------------------
#  Hauptprogramm
# --------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    heute = dt.datetime.now(dt.timezone.utc).astimezone(BERLIN).date()
    try:
        meta = les_meta()
        ledger = les_ledger()
        seiten = les_top(PFADE.top_seiten, "seite")
        begriffe = les_top(PFADE.top_suchbegriffe, "suchbegriff")
        bestand = les_bestand()
    except LeistungsFehler as e:
        print(f"🛑 {e}")
        return 2

    befund = berechne_befund(meta, ledger, seiten, begriffe, bestand, heute)

    if "--selftest" in argv:
        return _selftest()
    if "--md" in argv:
        if "--schreiben" in argv:
            schreibe(befund)
        print(als_markdown(befund), end="")
        return 0
    if "--json" in argv:
        print(json.dumps(befund, ensure_ascii=False, indent=2))
        return 0
    if "--issue" in argv:
        print(als_issue(befund), end="")
        return 0
    if "--check" in argv:
        for fund in befund["funde"]:
            zeichen = "🛑" if fund["schwere"] == "hart" else "⚠️ "
            print(f"  {zeichen} [{fund['regel']}] {fund['text']} (Beleg: {fund['beleg']})")
        print(f"GSC-Leistung: {len(befund['funde'])} Befund(e), {len(befund['hart'])} hart")
        return 1 if befund["hart"] else 0
    if "--schreiben" in argv:
        for pfad in schreibe(befund):
            print(f"geschrieben: {pfad}")
        return 0

    for pfad in schreibe(befund):
        print(f"geschrieben: {pfad}")
    print(als_markdown(befund), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
