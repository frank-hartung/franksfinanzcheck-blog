#!/usr/bin/env python3
"""KI-Provenienz – eine Wahrheit, alle Kanäle (#1028, Frist 02.12.2026).

WARUM DIESE DATEI EXISTIERT
---------------------------
Die maschinenlesbare Kennzeichnung lag seit dem 05.11.2026 auf vier Kanälen
(HTML-Kopf, schema.org, Bildattribut, IPTC-Feld in der Bilddatei). Die
Nachmessung am 07.11.2026 auf dem gebauten Bestand (406 Seiten) hat gezeigt,
dass die Wache dahinter drei blinde Flecken hatte – und alle drei sind
Deckungsfehler, keine Geschmacksfragen:

  · Das Gate zählte nur `content/posts`. Sechs Ratgeber-Seiten unter
    `content/pillar/` deklarierten `ai-generated-scope: audio`, ohne dass
    irgendeine Regel hinsah (78 von 109 regulären Seiten waren gedeckt).
  · Regel M4 („Kanaltreue") verglich das Meta-Signal gegen EINEN sichtbaren
    Anker: `data-ff-ki-label`, den Text-Hinweis. Die Tonspur hatte keinen
    sichtbaren Anker, weil es keinen gab – 84 Seiten spielten eine
    synthetische Stimme aus, 0 nannten sie beim Namen.
  · Der RSS-Feed, die Quelle des Pinterest-Auto-Publish, verteilte 50 Artikel
    weiter, ohne eine einzige Herkunftsangabe.

Diese Datei ist der gemeinsame Kern aus dem beide Seiten leben: die Wache
(`scripts/ki_provenienz_gate.py`, Regeln M1–M7) und der Selbstheilungs-Lauf
(`.github/workflows/ki-provenienz-wache.yml`). Vokabular, Anker, Pfade und
Heilregeln stehen hier genau einmal – wer einen Kanal anfasst, ändert eine
Datei und nicht drei.

EHRLICHE GRENZE (steht so auch in docs/KI-TRANSPARENZ-ABNAHME.md)
-----------------------------------------------------------------
Art. 50 Abs. 2 KI-VO ist eine Pflicht des ANBIETERS des generativen Systems.
Was hier geprüft und geheilt wird, ist die Betreiberebene: die eigene,
dokumentierte, maschinenlesbare Angabe und ihr sichtbares Gegenstück. Ein
grüner Lauf ist kein Herkunftsbeweis, kein Wasserzeichen, keine C2PA-Signatur
und keine Erfüllung der Anbieterpflicht.

Aufruf (als Bibliothek; CLI lebt im Gate)
-----------------------------------------
    from ki_provenienz import seiten, signale, kanal_vertrag, heilen
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
#  VOKABULAR – genau einmal, für Vorlagen und Wache zugleich
# --------------------------------------------------------------------------

#: Schutzvertrag für die konkret überwachte Bestandsfrist. Eine Änderung der
#: Rechtslage verlangt eine bewusste gemeinsame Anpassung des Kalenders.
FRIST_ID = "ki-vo-kennzeichnung-bestand"
FRIST_DATUM = "2026-12-02"

#: Reihenfolge ist Vertrag: `delimit` im Template erzeugt „text,image,audio".
MODALITAETEN = ("text", "image", "audio")

#: Sichtbarer Anker je Modalität im gebauten HTML. Fehlt der Anker, ist die
#: Modalität maschinenlesbar deklariert, aber für Menschen unsichtbar – genau
#: das verbietet Regel M4 (Kanaltreue).
ANKER = {
    "text": "data-ff-ki-label",
    "image": "data-ff-ki-image-label",
    "audio": "data-ff-ki-voice-label",
}

#: Namensraum der Betreiberangabe im Feed. XML-Namensräume sind Bezeichner,
#: keine Adressen; dokumentiert in docs/KI-TRANSPARENZ-ABNAHME.md §3b.
NAMESPACE = "https://franksfinanzcheck.de/ns/ki-provenance/1.0/"
NAMESPACE_KURZ = "ffki"

#: Ergänzende Angaben auf Verbreitungswegen. Sie unterscheiden Zielartikel,
#: dessen Cover und einen separat generierten Pin-Text. Die Präsenz in einem
#: Payload beweist weder eine Anbieter-Markierung noch die Plattformanzeige.
SOCIAL_TEXT = "Zielartikel: mit KI erstellt oder bearbeitet."
SOCIAL_BILD = "Zielartikel-Cover: mit KI erstellt oder bearbeitet."
SOCIAL_PIN = "Pin-Text: mit KI erstellt oder bearbeitet."

#: IPTC-Vokabular für die Bild-Erzeugungsart (dieselbe Liste wie in
#: scripts/ki_bild_markierung.py – dort steht sie als ERLAUBTE_TYPEN).
IPTC_VOKABULAR = "http://cv.iptc.org/newscodes/digitalsourcetype/"

IMPRESSUM = "content/impressum/index.md"
IMPRESSUM_ANKER = "{#ki-hinweis}"
HINWEIS_URL = "impressum/#ki-hinweis"
#: Suchmuster für die Überschrift, die den Anker tragen muss. Bewusst weit
#: („Hinweis zu KI … Inhalten"), weil die Formulierung redaktionell ist – die
#: Heilung soll den Anker wieder anbringen, nicht die Überschrift umtexten.
HINWEIS_UEBERSCHRIFT = re.compile(r"^(#{1,6})\s+(.*Hinweis zu KI.*Inhalten.*?)\s*$")

#: Beide RSS-Vorlagen müssen bytgleich bleiben (Hugo zieht je Version die
#: eine oder andere). Regel M7 prüft das, `heilen()` stellt es wieder her.
RSS_QUELLE = "layouts/rss.xml"
RSS_SPIEGEL = "layouts/_default/rss.xml"

LEDGER = "data/ki_provenienz_history.jsonl"
STATE = "data/ki_provenienz_state.json"

BAU = "public"

# Einmal kompiliert, zeilenweise verankert – keine rückverfolgenden Ketten
# auf mehrzeilige Eingaben (Hausregel 6, CLAUDE.md).
_RE_KOPF_ENDE = re.compile(r"^(---|\.\.\.)\s*$")
_RE_ZEILE = re.compile(r"^(\s*)([A-Za-z0-9_.\-]+):\s*(.*?)\s*$")
_RE_LISTE = re.compile(r"^\s+-\s+(.*?)\s*$")
_RE_WERT = re.compile(r"^(true|false)$", re.I)


class WerkzeugFehler(RuntimeError):
    """Ein Messwerkzeug fehlt – die Wache ist blind, nicht „grün"."""


# --------------------------------------------------------------------------
#  Frontmatter: zeilenweise, verschachtelt, ohne Abhängigkeiten
# --------------------------------------------------------------------------

def kopf_von(text: str) -> str:
    """Roher Frontmatter-Block ohne Begrenzer (leer, wenn keiner da ist)."""
    if not text.startswith("---"):
        return ""
    zeilen = text.splitlines()
    for i, zeile in enumerate(zeilen[1:], start=1):
        if _RE_KOPF_ENDE.match(zeile):
            return "\n".join(zeilen[1:i])
    return ""


def kopf_zeilen(kopf: str) -> list[tuple[int, str, str]]:
    """(Einrückung, Schlüssel, Wert) je Frontmatter-Zeile.

    Kommentare und Leerzeilen fallen weg. Verschachtelung wird über die
    Einrückung gelesen – nicht über eine Regex, die über den ganzen Block
    läuft (ReDoS-Hausregel).
    """
    raus: list[tuple[int, str, str]] = []
    for zeile in kopf.splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        m = _RE_ZEILE.match(zeile)
        if not m:
            continue
        einzug, schlüssel, wert = m.groups()
        raus.append((len(einzug.replace("\t", "  ")), schlüssel, wert.strip().strip("\"'")))
    return raus


def kopf_baum(kopf: str) -> dict:
    """Frontmatter als verschachteltes Wörterbuch.

    Ein Durchlauf über die Zeilen, Einrückung als einzige Struktur-Quelle –
    keine Regex, die über den ganzen Block läuft (ReDoS-Hausregel 6).
    Listen (`- …`) fallen weg: Für die Herkunftsfragen zählt nur, was als
    Schlüssel-Wert-Paar dasteht.
    """
    wurzel: dict = {}
    stapel: list[tuple[int, dict]] = [(-1, wurzel)]
    for einzug, name, wert in kopf_zeilen(kopf):
        while len(stapel) > 1 and einzug <= stapel[-1][0]:
            stapel.pop()
        ziel = stapel[-1][1]
        if wert == "":
            kind: dict = {}
            ziel[name] = kind
            stapel.append((einzug, kind))
        else:
            ziel[name] = wert
    return wurzel


def pfad_wert(kopf: str, pfad: tuple[str, ...] | list[str]) -> str | None:
    """Wert eines verschachtelten Schlüssels, z. B. („cover", „ai_generated").

    Bewusst über den Baum und nicht über „Elterneinzug + 1": YAML rückt
    beliebig ein (hier zwei Leerzeichen), und ein Vergleich auf Gleichheit
    hätte jeden verschachtelten Wert übersehen – gemessen am 07.11.2026:
    `cover.ki_pruefung.digital_source_type` wäre immer None gewesen.
    """
    knoten: object = kopf_baum(kopf)
    for teil in pfad:
        if not isinstance(knoten, dict) or teil not in knoten:
            return None
        knoten = knoten[teil]
    return knoten if isinstance(knoten, str) else None


def wahr(wert: str | None) -> bool:
    return bool(wert) and _RE_WERT.match(wert) is not None and wert.lower() == "true"


# --------------------------------------------------------------------------
#  Bestand: jede reguläre Seite mit ihrem Bauprodukt
# --------------------------------------------------------------------------

@dataclass
class Seite:
    """Eine reguläre Inhaltsseite und was über ihre Herkunft feststeht."""

    pfad: Path
    abschnitt: str
    slug: str
    basis: str                     # URL-Pfad ohne führenden/schließenden /
    ki_text: bool
    ki_bild: bool
    quellentyp: str                # IPTC-Wert, nur wenn belegt
    entwurf: bool
    lesehilfe_aus: bool
    kopf: str = field(default="", repr=False)

    @property
    def bau_pfad(self) -> str:
        return f"{BAU}/{self.basis}/index.html" if self.basis else f"{BAU}/index.html"


def _basis_von(rel: Path, pfad: Path, kopf: str) -> str:
    """URL-Pfad einer Seite – aus `url:`/`slug:` oder der Verzeichnisstruktur.

    Am 07.11.2026 gegen den echten Bau geprüft: 109 von 109 regulären Seiten
    ohne Entwurf finden ihr Bauprodukt über diese Ableitung. Leaf-Bundles
    (`index.md`) tragen ihren Ordner als URL, einfache Dateien ihren Stamm.
    """
    url = pfad_wert(kopf, ("url",))
    if url:
        return url.strip("/")
    verz = rel.parent
    if pfad.name == "index.md":
        # Auch ein Leaf-Bundle kann in Hugo einen expliziten slug tragen.
        # Der Verzeichnisname ist dann NICHT der veröffentlichte URL-Pfad.
        slug = pfad_wert(kopf, ("slug",))
        teile = verz.parent.parts + (slug,) if slug else verz.parts
    else:
        slug = pfad_wert(kopf, ("slug",)) or pfad.stem
        teile = verz.parts + (slug,)
    return "/".join(teile)


def seiten(root: Path = ROOT, *, nur_abschnitte: tuple[str, ...] | None = None) -> list[Seite]:
    """Alle regulären Inhaltsseiten – NICHT nur posts/.

    Der Blindfleck bis zum 07.11.2026: `content/pillar/` und `content/werkzeuge/`
    liefen durch keine Regel, obwohl dieselbe Vorlage für sie Signale setzt.
    """
    inhalt = root / "content"
    raus: list[Seite] = []
    if not inhalt.is_dir():
        return raus
    for pfad in sorted(inhalt.rglob("*.md")):
        if pfad.name == "_index.md":
            continue                       # Branch-Bundle: keine reguläre Seite
        try:
            text = pfad.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        kopf = kopf_von(text)
        if not kopf:
            continue
        rel = pfad.relative_to(inhalt)
        abschnitt = rel.parts[0] if len(rel.parts) > 1 else rel.stem
        if nur_abschnitte and abschnitt not in nur_abschnitte:
            continue
        raus.append(Seite(
            pfad=pfad,
            abschnitt=abschnitt,
            slug=pfad.parent.name if pfad.name == "index.md" else pfad.stem,
            basis=_basis_von(rel, pfad, kopf),
            ki_text=wahr(pfad_wert(kopf, ("ai_generated",))),
            ki_bild=wahr(pfad_wert(kopf, ("cover", "ai_generated"))),
            quellentyp=(pfad_wert(kopf, ("cover", "ki_pruefung", "digital_source_type")) or ""),
            entwurf=wahr(pfad_wert(kopf, ("draft",))),
            lesehilfe_aus=wahr(pfad_wert(kopf, ("hideReaderToolbar",))),
            kopf=kopf,
        ))
    return raus


# --------------------------------------------------------------------------
#  Bauprodukt: was tatsächlich ausgeliefert wird
# --------------------------------------------------------------------------

_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                        "link", "meta", "param", "source", "track", "wbr"})
_ANZEIGETEXTE = {
    "text": ("mit ki erstellt oder bearbeitet",),
    "image": ("bild mit ki erstellt oder bearbeitet",),
    "audio": ("ki-stimme", "ai voice"),
}


class _DokumentSignale(HTMLParser):
    """Tatsächliche Elemente statt Treffer in Kommentaren oder fremden Links.

    HTMLParser berücksichtigt unquotierte/minifizierte Attribute. Versteckte
    oder leere Marker zählen nicht als Hinweis. CSS und Screenreader-Verhalten
    sind damit nicht nachgewiesen und bleiben Teil der Live-Abnahme.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stapel = []
        self.meta = []
        self.scope = []
        self.ziele = []
        self.marker = {m: [] for m in ANKER}
        self.bilder = []
        self.toolbar = False
        self.jsonld = []

    def handle_starttag(self, tag, attrs):
        werte = {k.lower(): (v or "") for k, v in attrs}
        im_kopf = any(frame["tag"] == "head" for frame in self.stapel)
        if im_kopf and tag == "meta":
            name = werte.get("name", "").lower()
            if name == "ai-generated":
                self.meta.append(werte.get("content", ""))
            elif name == "ai-generated-scope":
                self.scope.append(werte.get("content", ""))
        if im_kopf and tag == "link" and "describedby" in werte.get("rel", "").lower().split():
            self.ziele.append(werte.get("href", ""))
        klassen = werte.get("class", "").split()
        if tag in ("div", "section") and "ff-voice-slot" in klassen:
            self.toolbar = True
        if tag == "img":
            self.bilder.append(werte)

        stil = re.sub(r"\s+", "", werte.get("style", "").lower())
        versteckt = (bool(self.stapel and self.stapel[-1]["versteckt"])
                      or "hidden" in werte or tag in ("template", "script", "style", "noscript")
                      or "display:none" in stil or "visibility:hidden" in stil
                      or bool({"sr-only", "visually-hidden", "hidden"} & set(klassen)))
        marker = []
        for modalitaet, attribut in ANKER.items():
            if attribut in werte:
                eintrag = {"versteckt": versteckt, "text": []}
                self.marker[modalitaet].append(eintrag)
                marker.append(eintrag)
        if tag not in _VOID_TAGS:
            self.stapel.append({"tag": tag, "versteckt": versteckt, "marker": marker,
                                "jsonld": [] if im_kopf and tag == "script" and
                                werte.get("type", "").lower() == "application/ld+json"
                                else None})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stapel) - 1, -1, -1):
            if self.stapel[index]["tag"] == tag:
                for frame in self.stapel[index:]:
                    if frame["jsonld"] is not None:
                        self.jsonld.append("".join(frame["jsonld"]))
                del self.stapel[index:]
                break

    def handle_data(self, daten):
        if not self.stapel:
            return
        if not self.stapel[-1]["versteckt"]:
            for frame in self.stapel:
                for marker in frame["marker"]:
                    marker["text"].append(daten)
        for frame in self.stapel:
            if frame["jsonld"] is not None:
                frame["jsonld"].append(daten)


def signale(html: str) -> dict:
    """Signale der gebauten Seite strukturiert lesen; keine CSS-Liveprüfung."""
    parser = _DokumentSignale()
    parser.feed(html)
    parser.close()
    artikel = []
    json_fehler = []

    def artikel_sammeln(daten):
        if isinstance(daten, list):
            for eintrag in daten:
                artikel_sammeln(eintrag)
        elif isinstance(daten, dict):
            typ = daten.get("@type")
            if typ == "Article" or (isinstance(typ, list) and "Article" in typ):
                artikel.append(daten)
            if "@graph" in daten:
                artikel_sammeln(daten["@graph"])

    for block in parser.jsonld:
        try:
            artikel_sammeln(json.loads(block))
        except (TypeError, ValueError) as exc:
            json_fehler.append(str(exc))
    sichtbare = {}
    for modalitaet, eintraege in parser.marker.items():
        sichtbare[modalitaet] = any(
            not eintrag["versteckt"] and any(
                erwartung in " ".join("".join(eintrag["text"]).lower().split())
                for erwartung in _ANZEIGETEXTE[modalitaet])
            for eintrag in eintraege)
    scope = parser.scope[0] if parser.scope else ""
    return {
        "meta": parser.meta == ["true"], "meta_werte": parser.meta,
        "bereiche": tuple(b for b in scope.split(",") if b in MODALITAETEN),
        "scope_werte": parser.scope,
        "describedby": bool(parser.ziele), "describedby_ziele": parser.ziele,
        "toolbar": parser.toolbar, "anker": sichtbare,
        "anker_vorhanden": {m: bool(e) for m, e in parser.marker.items()},
        "artikel": artikel, "json_fehler": json_fehler,
        "credit": artikel[0].get("creditText", "") if artikel else "",
        "bilder": parser.bilder,
        "bild_attribut": any("data-digital-source-type" in bild for bild in parser.bilder),
    }


def erwartet(seite: Seite, sig: dict) -> tuple[str, ...]:
    """Welche Modalitäten diese Seite deklarieren MUSS.

    Text und Bild kommen aus dem Frontmatter (Quelle der Wahrheit), die
    Tonspur aus dem Bau: Wird die Lesehilfe ausgeliefert, ist synthetische
    Sprache im Spiel – unabhängig davon, was im Frontmatter steht.
    """
    raus = []
    if seite.ki_text:
        raus.append("text")
    if seite.ki_bild:
        raus.append("image")
    if sig["toolbar"] and not seite.lesehilfe_aus:
        raus.append("audio")
    return tuple(b for b in MODALITAETEN if b in raus)


# --------------------------------------------------------------------------
#  Feed und Social-Verbreitung
# --------------------------------------------------------------------------

def _social_fakten(kopf: str, root: Path | None = None) -> tuple[bool, bool, Path | None]:
    """Deklaration und, bei KI-Covern, fassungsgebundenen Bildnachweis lesen.

    Publisher laufen unabhängig vom Hugo-Deploy. Defektes/mehrdeutiges YAML
    ist nicht „keine Angabe“. Fehlende Flags sind kein Herkunftsnachweis. Ein
    deklariertes KI-Cover muss dieselbe Hash-/Quellen-/Datum-/Deepfake-Prüfung
    wie beim Deploy bestehen und das erwartete IPTC-Feld tragen.
    """
    if not kopf.strip():
        raise WerkzeugFehler("Frontmatter für Pinterest fehlt")
    try:
        import yaml  # Publisher-Workflows installieren requirements-ci.txt
        from yaml.nodes import MappingNode, ScalarNode
        baum = yaml.compose(kopf, Loader=yaml.SafeLoader)
    except ImportError as exc:
        raise WerkzeugFehler("PyYAML für Pinterest-Kennzeichnung fehlt") from exc
    except Exception as exc:
        raise WerkzeugFehler(f"Frontmatter für Pinterest ungültig: {exc}") from exc
    if not isinstance(baum, MappingNode):
        raise WerkzeugFehler("Frontmatter für Pinterest ist kein YAML-Objekt")

    def feld(knoten, name):
        if any(isinstance(k, ScalarNode) and k.tag == "tag:yaml.org,2002:merge"
               for k, _ in knoten.value):
            raise WerkzeugFehler("Frontmatter für Pinterest: YAML-Merge nicht eindeutig messbar")
        treffer = [v for k, v in knoten.value
                   if isinstance(k, ScalarNode) and k.value.lower() == name]
        if len(treffer) > 1:
            raise WerkzeugFehler(f"Frontmatter für Pinterest: {name} mehrfach")
        return treffer[0] if treffer else None

    def boolean(knoten, name):
        if knoten is None:
            return False
        if (not isinstance(knoten, ScalarNode)
                or knoten.tag != "tag:yaml.org,2002:bool"
                or knoten.value.lower() not in ("true", "false")):
            raise WerkzeugFehler(f"Frontmatter für Pinterest: {name} ist kein true/false")
        return knoten.value.lower() == "true"

    def zeichen(knoten):
        if (isinstance(knoten, ScalarNode)
                and knoten.tag in ("tag:yaml.org,2002:str", "tag:yaml.org,2002:timestamp")):
            return knoten.value
        return None

    text = boolean(feld(baum, "ai_generated"), "ai_generated")
    cover = feld(baum, "cover")
    original = None
    if cover is None or (isinstance(cover, ScalarNode) and
                         cover.tag == "tag:yaml.org,2002:null"):
        bild = False
    elif isinstance(cover, MappingNode):
        bild = boolean(feld(cover, "ai_generated"), "cover.ai_generated")
        if bild:
            pruefung = feld(cover, "ki_pruefung")
            if not isinstance(pruefung, MappingNode):
                raise WerkzeugFehler("Social: Nachweis des KI-Covers fehlt")
            deepfake = feld(pruefung, "deepfake")
            if deepfake is None or boolean(deepfake, "cover.ki_pruefung.deepfake"):
                raise WerkzeugFehler("Social: KI-Cover ohne dokumentierte Deepfake-Freigabe; nicht senden")
            nachweis = {name: zeichen(feld(pruefung, name)) for name in
                        ("sha256", "quelle", "geprueft_am", "digital_source_type")}
            nachweis["deepfake"] = False
            daten = {"image": zeichen(feld(cover, "image")), "ai_generated": True,
                     "ki_pruefung": nachweis}
            try:
                import ki_cover_provenienz as cover_provenienz
                import ki_bild_markierung as markierung
                original, _ = cover_provenienz.pruefe_ki_cover(Path(root or ROOT), daten)
                typ = markierung.typ_aus(daten)
                if typ not in markierung.ERLAUBTE_TYPEN:
                    raise ValueError("gültiger IPTC DigitalSourceType im Nachweis fehlt")
                stand = markierung.lesen(original)
                if stand["format"] != "jpeg" or stand["digital_source_type"] != typ:
                    raise ValueError("KI-Cover trägt nicht den belegten IPTC DigitalSourceType")
            except (ImportError, OSError, ValueError) as exc:
                raise WerkzeugFehler(f"Social: KI-Cover nicht nachweisbar: {exc}") from exc
    else:
        raise WerkzeugFehler("Frontmatter für Pinterest: cover ist kein Objekt")
    return text, bild, original


def social_erklaerungen(kopf: str, root: Path | None = None) -> tuple[bool, bool]:
    """Nur explizit deklarierte Modalitäten; KI-Cover müssen belegt sein."""
    text, bild, _ = _social_fakten(kopf, root)
    return text, bild


def social_cover_original(kopf: str, root: Path | None = None) -> Path | None:
    """Belegtes KI-Original oder None bei unbekannter/anderer Herkunft."""
    return _social_fakten(kopf, root)[2]


def social_hinweis(text: str, *, ki_text: bool = False, ki_bild: bool = False,
                    ki_pin: bool = False) -> str:
    """Deklarierte Angaben früh einfügen; die Werbung bleibt gegebenenfalls vorn.

    Fallback für Empfänger, die den eigenen RSS-Namensraum nicht auswerten.
    Er behauptet nichts über ein separat erstelltes Pin-Bild und garantiert
    nicht, dass eine Fremdplattform die Beschreibung übernimmt oder anzeigt.
    """
    hinweise = ([SOCIAL_TEXT] if ki_text is True else [])
    hinweise += [SOCIAL_BILD] if ki_bild is True else []
    hinweise += [SOCIAL_PIN] if ki_pin is True else []
    if not hinweise:
        return text
    beschreibung = str(text or "").strip()
    prefix = ""
    if beschreibung.startswith("*Werbung"):
        beschreibung = beschreibung[len("*Werbung"):].lstrip()
        if beschreibung.startswith("|"):
            beschreibung = beschreibung[1:].lstrip()
        prefix = "*Werbung | "
    hinweis = " ".join(hinweise)
    if not beschreibung.startswith(hinweis):
        beschreibung = f"{hinweis} {beschreibung}".rstrip()
    return prefix + beschreibung


def social_beschreibung_pruefen(text: str, *, ki_text: bool, ki_bild: bool,
                                 ki_pin: bool = False, limit: int = 500) -> None:
    """An der Sendegrenze weder Hinweise abschneiden noch Widersprüche senden."""
    if limit <= 0 or len(text) > limit:
        raise WerkzeugFehler(f"Pinterest-Beschreibung mit Herkunftshinweisen "
                             f"überschreitet das Limit ({len(text)}/{limit})")
    if not text.startswith("*Werbung | "):
        raise WerkzeugFehler("Pinterest: Werbekennzeichnung fehlt am Anfang")
    if social_hinweis(text, ki_text=ki_text, ki_bild=ki_bild, ki_pin=ki_pin) != text:
        raise WerkzeugFehler("Pinterest-Herkunftshinweis fehlt am Anfang")
    for hinweis, erwartet in ((SOCIAL_TEXT, ki_text), (SOCIAL_BILD, ki_bild),
                              (SOCIAL_PIN, ki_pin)):
        if text.count(hinweis) != int(erwartet):
            raise WerkzeugFehler("Pinterest-Beschreibung enthält doppelte oder "
                                 "nicht deklarierte Herkunftshinweise")


def social_post_quelle(post: dict, root: Path | None = None) -> str:
    """Die Ausgangsdatei vor dem POST erneut lesen und mit dem Snapshot binden."""
    root = Path(root or ROOT).resolve()
    if not isinstance(post, dict) or not isinstance(post.get("path"), str):
        raise WerkzeugFehler("Pinterest-Artikelpfad fehlt")
    try:
        pfad = Path(post["path"]).resolve(strict=True)
        posts = (root / "content/posts").resolve()
        if not pfad.is_relative_to(posts) or pfad.suffix != ".md":
            raise ValueError("Artikelpfad liegt nicht unter content/posts")
        slug = pfad.parent.name if pfad.name == "index.md" else pfad.stem
        if post.get("slug") != slug:
            raise ValueError("Artikelpfad und Slug passen nicht zusammen")
        inhalt = pfad.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise WerkzeugFehler(f"Pinterest-Artikelquelle nicht lesbar: {exc}") from exc
    if not isinstance(post.get("content"), str) or inhalt != post["content"]:
        raise WerkzeugFehler("Pinterest-Artikel hat sich seit dem Laden geändert")
    kopf = kopf_von(inhalt)
    text, bild = social_erklaerungen(kopf, root)
    if post.get("ki_text") is not text or post.get("ki_bild") is not bild:
        raise WerkzeugFehler("Pinterest-Angaben passen nicht zur Artikelquelle")
    return kopf


def social_artikel_quelle(artikel: dict, slug: str, root: Path | None = None) -> tuple[str, str]:
    """Social-Studio-Snapshot an tatsächliche Artikeldatei und URL binden."""
    root = Path(root or ROOT).resolve()
    if not isinstance(artikel, dict) or not isinstance(artikel.get("path"), str):
        raise WerkzeugFehler("Social: Artikelquelle fehlt")
    try:
        pfad = Path(artikel["path"]).resolve(strict=True)
        if not pfad.is_relative_to((root / "content/posts").resolve()) or pfad.suffix != ".md":
            raise ValueError("Artikelpfad liegt nicht unter content/posts")
        datei_slug = pfad.parent.name if pfad.name == "index.md" else pfad.stem
        if not slug or slug != datei_slug or artikel.get("slug") != slug:
            raise ValueError("Artikelpfad und Slug passen nicht zusammen")
        inhalt = pfad.read_text(encoding="utf-8")
        if hashlib.sha256(inhalt.encode("utf-8")).hexdigest() != artikel.get("source_sha256"):
            raise ValueError("Artikel hat sich seit der Planung geändert")
        kopf = kopf_von(inhalt)
        if kopf.strip() != str(artikel.get("raw_fm") or "").strip():
            raise ValueError("Frontmatter passt nicht zur Artikelquelle")
        url = urlsplit(str(artikel.get("url") or ""))
        suffix = "/posts/" + quote(slug) + "/"
        if (url.scheme != "https" or not url.netloc or url.username is not None
                or url.password is not None or url.query or url.fragment
                or not url.path.endswith(suffix)):
            raise ValueError("Artikel-URL passt nicht zur Quelle")
        basis = f"{url.scheme}://{url.netloc}{url.path[:-len(suffix)]}/"
    except (OSError, UnicodeError, ValueError) as exc:
        raise WerkzeugFehler(f"Social: Artikelquelle nicht nachweisbar: {exc}") from exc
    social_erklaerungen(kopf, root)
    return kopf, basis


def social_ziel_pruefen(link: str, slug: str, basis: str) -> None:
    """Ein Pin darf nicht die Angaben eines anderen Zielartikels verwenden."""
    try:
        erwartet = urlsplit(urljoin(basis.rstrip("/") + "/", "posts/" + quote(slug) + "/"))
        aktuell = urlsplit(link)
        if (aktuell.scheme != erwartet.scheme or aktuell.netloc != erwartet.netloc
                or aktuell.path != erwartet.path or aktuell.fragment):
            raise ValueError("URL passt nicht zur geprüften Artikelquelle")
    except (TypeError, ValueError) as exc:
        raise WerkzeugFehler(f"Pinterest-Ziel nicht eindeutig: {exc}") from exc


def social_bild_pruefen(kopf: str, bild_url: str, basis: str, root: Path | None = None) -> None:
    """Ein deklariertes KI-Cover nur als belegtes, nicht umkodiertes Original senden."""
    root = Path(root or ROOT).resolve()
    original = social_cover_original(kopf, root)
    if original is None:
        return  # Herkunft einer anderen Bildquelle bleibt ausdrücklich offen
    rel = original.relative_to((root / "static").resolve()).as_posix()
    erwartet = urljoin(basis.rstrip("/") + "/", quote(rel, safe="/"))
    if bild_url != erwartet:
        raise WerkzeugFehler("Social: Bild ist nicht das geprüfte KI-Cover-Original; "
                             "abweichende Pin-/Social-Datei gesondert prüfen")


def social_pinterest_beschreibung(paket: dict, limit: int = 500) -> str:
    """Finale Pinterest-Copy; fehlende Herkunftsquelle oder Überlänge blockieren.

    Ein fremdes `pin_image` oder eine Plattformkopie ist nicht durch das
    Cover-Flag belegt. Eine KI-Politur des Pin-Textes ist dagegen separat im
    Paket vermerkt und bekommt einen eigenen Hinweis.
    """
    artikel = paket.get("article") or {}
    if not isinstance(artikel, dict):
        raise WerkzeugFehler("Pinterest-Artikelquelle fehlt")
    ki_text, ki_bild = social_erklaerungen(str(artikel.get("raw_fm") or ""))
    ki_pin = paket.get("ai_polished", False)
    if type(ki_pin) is not bool:
        raise WerkzeugFehler("Pinterest: Kennzeichnung der Pin-Text-Politur ist ungültig")
    roh = str(paket.get("text") or "").strip()
    if not roh.startswith("*Werbung"):
        roh = "*Werbung | " + roh
    beschreibung = social_hinweis(roh, ki_text=ki_text, ki_bild=ki_bild, ki_pin=ki_pin)
    social_beschreibung_pruefen(beschreibung, ki_text=ki_text, ki_bild=ki_bild,
                                ki_pin=ki_pin, limit=limit)
    return beschreibung


def feed_pfad(root: Path = ROOT) -> Path:
    return root / BAU / "index.xml"


def feed_daten(pfad: Path) -> tuple[list[dict], list[str]]:
    """RSS-Items und Kanalziele strukturiert lesen, ohne Werte zu erraten.

    Das tatsächliche Template legt ``media:credit`` IN ``media:content`` ab.
    Wir bewahren deshalb auch den Bildbezug, Rollen, Werte und Mehrfacheinträge
    auf. Ein vorhandenes Element mit dem Text ``false`` ist kein ``true``.
    """
    import xml.etree.ElementTree as ET

    if not pfad.is_file():
        raise WerkzeugFehler(f"Feed fehlt: {pfad}")
    try:
        wurzel = ET.parse(pfad).getroot()
    except ET.ParseError as exc:
        raise WerkzeugFehler(f"Feed ist kein valides XML: {exc}") from exc
    kanaele = wurzel.findall("channel")
    if wurzel.tag != "rss" or len(kanaele) != 1:
        raise WerkzeugFehler("Feed muss genau einen RSS-channel enthalten")
    kanal = kanaele[0]
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "media": "http://search.yahoo.com/mrss/",
          NAMESPACE_KURZ: NAMESPACE}

    def ziele(element):
        return [(a.get("href") or "").strip() for a in element.findall("atom:link", ns)
                if (a.get("rel") or "").strip() == "describedby"]

    def credit(element):
        return {"wert": (element.text or "").strip(),
                "rolle": (element.get("role") or "").strip(),
                "schema": (element.get("scheme") or "").strip()}

    raus = []
    for item in kanal.findall("item"):
        guids = [(g.text or "").strip() for g in item.findall("guid")]
        links = [(link.text or "").strip() for link in item.findall("link")]
        werte = [(e.text or "").strip() for e in
                 item.findall(f"{NAMESPACE_KURZ}:ai-generated", ns)]
        scopes = [(e.text or "").strip() for e in
                  item.findall(f"{NAMESPACE_KURZ}:ai-generated-scope", ns)]
        medien = [{"url": (m.get("url") or "").strip(),
                   "credits": [credit(c) for c in m.findall("media:credit", ns)]}
                  for m in item.findall("media:content", ns)]
        freie_credits = [credit(c) for c in item.findall("media:credit", ns)]
        beschrieben = ziele(item)
        beschreibungen = [(e.text or "").strip() for e in item.findall("description")]
        guid = guids[0] if guids else ""
        raus.append({
            "guid": guid, "guids": guids, "links": links,
            "slug": _slug_aus_url(guid),
            "scope": scopes[0] if scopes else "", "scopes": scopes,
            "ai_generated": werte == ["true"], "ai_werte": werte,
            "describedby": bool(beschrieben), "describedby_ziele": beschrieben,
            "media_credit": bool(freie_credits or any(m["credits"] for m in medien)),
            "medien": medien, "freie_credits": freie_credits,
            "description": beschreibungen[0] if beschreibungen else "",
            "descriptions": beschreibungen,
        })
    return raus, ziele(kanal)


def feed_items(pfad: Path) -> list[dict]:
    """Items des gebauten Feeds; widersprüchliche Einzelwerte bleiben sichtbar."""
    return feed_daten(pfad)[0]


def feed_kanal_angabe(pfad: Path) -> bool:
    """Ob ein Kanal-Verweis existiert; M5 prüft zusätzlich sein exaktes Ziel."""
    try:
        return bool(feed_daten(pfad)[1])
    except (OSError, WerkzeugFehler):
        return False


def _slug_aus_url(url: str) -> str:
    """`https://…/posts/2026-10-28-xyz/?utm…` → `2026-10-28-xyz`."""
    pfad = url.split("?", 1)[0].rstrip("/")
    return pfad.rsplit("/", 1)[-1] if pfad else ""


# --------------------------------------------------------------------------
#  Vorlagen- und Bestandsvertrag (Regeln M2, M6, M7)
# --------------------------------------------------------------------------

@dataclass
class Vertrag:
    """Eine Stelle, die stimmen muss – samt Weg, sie wiederherzustellen."""

    regel: str
    datei: str
    nadel: str
    meldung: str
    heilbar: str = ""          # "neu" | "spiegel" | "anker" | "" (nur melden)


def kanal_vertrag(root: Path = ROOT) -> list[Vertrag]:
    return [
        Vertrag("M2", "layouts/_partials/head.html", "ki_provenienz.html",
                "head.html bindet ki_provenienz.html nicht mehr ein"),
        Vertrag("M2", "layouts/_partials/_funcs/ki_modalitaeten.html", "return $bereiche",
                "die gemeinsame Modalitäten-Funktion fehlt – Kopf und Feed "
                "würden wieder getrennt rechnen"),
        Vertrag("M2", "layouts/_partials/ki_provenienz.html",
                'partial "_funcs/ki_modalitaeten.html"',
                "ki_provenienz.html rechnet die Modalitäten wieder selbst "
                "statt über die gemeinsame Funktion"),
        Vertrag("M2", "layouts/_partials/schema_article.html", "creditText",
                "schema_article.html emittiert kein creditText mehr"),
        Vertrag("M2", "layouts/_partials/cover.html", "data-digital-source-type",
                "cover.html emittiert kein data-digital-source-type mehr"),
        # K1 (07.11.2026): sichtbare Ebene der Tonspur
        Vertrag("M2", "layouts/_partials/ff_voice_toolbar.html", ANKER["audio"],
                "die Lesehilfe trägt kein sichtbares KI-Siegel mehr – die "
                "Tonspur wäre maschinenlesbar deklariert, aber unsichtbar"),
        Vertrag("M2", "layouts/_partials/ff_voice_toolbar.html", "ff-voice-ki-hinweis",
                "die Barrierefrei-Beschreibung der Tonspur fehlt "
                "(aria-describedby läuft ins Leere)"),
        Vertrag("M2", "assets/css/extended/ff-voice.css", ".ff-voice-btn__ki",
                "das KI-Siegel der Lesehilfe ist nicht gestaltet"),
        Vertrag("M2", "static/premium/ff-voice.js", "maschinell erzeugte Stimme",
                "ff-voice.js überschreibt die aria-label ohne Herkunftsangabe "
                "– nach dem ersten Klick wäre die Angabe für Screenreader weg"),
        # K2 (07.11.2026): Feed-Kanal
        Vertrag("M2", RSS_QUELLE, "ffki:ai-generated-scope",
                "der Feed trägt keine Herkunftsangabe mehr – auf dem "
                "Verbreitungsweg zu Pinterest ginge die Kennzeichnung verloren"),
        Vertrag("M2", RSS_QUELLE, 'rel="describedby"',
                "dem Feed fehlt die IANA-Relation auf den menschenlesbaren Hinweis"),
        Vertrag("M2", IMPRESSUM, IMPRESSUM_ANKER,
                "der Anker #ki-hinweis im Impressum fehlt – rel=\"describedby\" "
                "läuft ins Leere", heilbar="anker"),
        # K5 (07.11.2026): abgeleitete Bildformate
        Vertrag("M6", "scripts/image_optimizer.py", "def ki_originale(",
                "der Bild-Optimizer kennt deklarierte KI-Originale nicht – er "
                "würde unmarkierte AVIF/WebP/JPEG-Geschwister erzeugen, die "
                "öffentlich erreichbar sind und die Markierung nicht tragen"),
    ]


def rss_spiegel_abweichung(root: Path = ROOT) -> str:
    """M7: Beide RSS-Vorlagen müssen bytgleich sein.

    Rückgabe: "" = gleich · "quelle" = nur die Quelle trägt den Kanal ·
    "spiegel" = nur der Spiegel · "beide" = beide tragen ihn, unterscheiden
    sich aber sonst (dann wird NICHT geraten, sondern gemeldet).
    """
    quelle = root / RSS_QUELLE
    spiegel = root / RSS_SPIEGEL
    if not quelle.is_file() or not spiegel.is_file():
        return "beide" if quelle.is_file() != spiegel.is_file() else ""
    a = quelle.read_bytes()
    b = spiegel.read_bytes()
    if a == b:
        return ""
    nadel = b"ffki:ai-generated-scope"
    if nadel in a and nadel not in b:
        return "quelle"
    if nadel in b and nadel not in a:
        return "spiegel"
    return "beide"


# --------------------------------------------------------------------------
#  Bildbestand: abgeleitete Formate eines deklarierten KI-Originals
# --------------------------------------------------------------------------

#: Spiegel von RESPONSIVE_WIDTHS in scripts/image_optimizer.py.
BREITEN = ("360", "480", "620", "720")


def abgeleitete_pfade(original: str) -> list[str]:
    """Pfade, die der Bild-Optimizer aus einem Cover erzeugt.

    Exakt spiegelbildlich zu `expected_variants()` in
    scripts/image_optimizer.py – dieselben Breiten, dieselben Ordner. Die
    Funktion dort braucht Pillow UND die Datei (`Image.open`); diese hier
    rechnet nur aus dem Pfad, damit Regel M6 auch dann prüft, wenn das
    Original fehlt oder Pillow ausfällt. `expected_variants` kann nicht
    importiert werden: image_optimizer.py wirft beim Import ein SystemExit,
    wenn Pillow fehlt – das würde die Wache töten statt sie blind zu melden.

    Obermenge statt Teilmenge: `expected_variants` nennt nur Breiten ≤
    Quellbreite. Hier stehen alle; gemeldet wird ausschließlich, was wirklich
    auf der Platte liegt.
    """
    p = Path(original)
    stamm = p.stem
    verz = str(p.parent)
    raus = []
    for breite in BREITEN:
        raus.append(f"{verz}/{breite}/{p.name}")
        raus.append(f"{verz}/webp/{breite}/{stamm}.webp")
        raus.append(f"{verz}/avif/{breite}/{stamm}.avif")
    raus.append(f"{verz}/webp/{stamm}.webp")
    raus.append(f"{verz}/avif/{stamm}.avif")
    return raus


def ki_originale(root: Path = ROOT) -> list[Seite]:
    """Seiten, deren Cover ausdrücklich als KI-Bild deklariert ist."""
    return [s for s in seiten(root) if s.ki_bild]


def unmarkierte_ableitungen(root: Path = ROOT) -> list[tuple[Seite, str]]:
    """M6: abgeleitete Bilddateien zu einem deklarierten KI-Original.

    Jede dieser Dateien ist öffentlich erreichbar, trägt die IPTC-Markierung
    des Originals aber nicht – eine unmarkierte Kopie synthetischen Inhalts.
    """
    raus = []
    for seite in ki_originale(root):
        original = (pfad_wert(seite.kopf, ("cover", "image")) or "")
        if not original:
            continue
        for rel in abgeleitete_pfade(original.lstrip("/")):
            datei = root / "static" / rel
            if datei.is_file():
                raus.append((seite, rel))
    return raus


def social_ableitungen(root: Path = ROOT) -> list[tuple[Seite, str]]:
    """Bereits vorhandene Social-Varianten deklarierter KI-Cover melden.

    Der Dateiname weist auf einen möglichen Ableitungsweg, beweist aber nicht,
    dass die alte Datei aus dem aktuellen Original stammt. Nicht automatisch
    löschen oder ihre Herkunft behaupten: eine Person muss sie prüfen/entfernen.
    """
    ordner = root / "static/images/social"
    if not ordner.is_dir():
        return []
    dateien = [p for p in ordner.iterdir() if p.is_file() and p.suffix.lower() == ".jpg"]
    raus = []
    for seite in ki_originale(root):
        if seite.abschnitt != "posts":
            continue
        prefix = seite.slug + "-"
        for datei in dateien:
            if datei.stem.startswith(prefix) and re.fullmatch(r"\d+x\d+", datei.stem[len(prefix):]):
                raus.append((seite, datei.relative_to(root / "static").as_posix()))
    return raus


# --------------------------------------------------------------------------
#  Register: ungeklärte Herkunft (offener Punkt 3 aus #1028)
# --------------------------------------------------------------------------

def register(root: Path = ROOT) -> dict[str, set[str]]:
    """Das Register der gewählten Repository-Wurzel lesen."""
    return register_datei(root / "data" / "ki_kennzeichnung.yaml")


def register_datei(pfad: Path) -> dict[str, set[str]]:
    """Register im dokumentierten Listenformat strikt und ohne PyYAML lesen.

    Eine fehlende Datei, ein Tippfehler oder eine unbeachtete YAML-Zeile darf
    die offene Warteschlange nicht unbemerkt auf null reduzieren. Andere
    YAML-Schreibweisen werden bewusst als nicht messbar zurückgewiesen.
    """
    daten: dict[str, set[str]] = {"maschinell": set(), "menschlich": set()}
    if not pfad.is_file():
        raise WerkzeugFehler(f"Register fehlt: {pfad}")
    try:
        zeilen = pfad.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise WerkzeugFehler(f"Register nicht lesbar: {exc}") from exc
    aktuell = None
    koepfe: set[str] = set()
    for nummer, zeile in enumerate(zeilen, 1):
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        m = re.fullmatch(r"(maschinell|menschlich):\s*(\[\])?\s*(?:#.*)?", zeile)
        if m:
            aktuell = m.group(1)
            if aktuell in koepfe:
                raise WerkzeugFehler(f"Register Zeile {nummer}: doppelter Abschnitt {aktuell}")
            koepfe.add(aktuell)
            if m.group(2):
                aktuell = None  # nach einer explizit leeren Liste kein weiterer Eintrag
            continue
        m = re.fullmatch(r"\s+-\s+([A-Za-z0-9._-]+|'[A-Za-z0-9._-]+'|"
                         r'"[A-Za-z0-9._-]+")\s*(?:#.*)?', zeile)
        if not m or aktuell is None:
            raise WerkzeugFehler(f"Register Zeile {nummer}: unbekanntes Listenformat")
        wert = m.group(1).strip("\"'")
        if wert in daten[aktuell]:
            raise WerkzeugFehler(f"Register Zeile {nummer}: doppelter Eintrag {wert}")
        daten[aktuell].add(wert)
    if koepfe != set(daten) or daten["maschinell"] & daten["menschlich"]:
        raise WerkzeugFehler("Register unvollständig oder maschinell/menschlich widersprüchlich")
    return daten


def ungeklaert(root: Path = ROOT) -> list[str]:
    """`menschlich`-Einträge ohne Beleg in der veröffentlichten Fassung.

    Diese Liste ist KEIN Befund, den ein Skript entscheiden darf: Ob ein
    Mensch die redaktionelle Verantwortung übernommen hat, weiß nur der
    Betreiber. Die Wache macht daraus Alter, Sichtbarkeit und Eskalation –
    und erfindet keine Prüfung (docs/KI-TRANSPARENZ-ABNAHME.md §3).
    """
    reg = register(root)
    return sorted(reg["menschlich"])


# --------------------------------------------------------------------------
#  Zustand und Beleg-Ledger
# --------------------------------------------------------------------------

def _jetzt() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_lesen(root: Path = ROOT) -> dict:
    pfad = root / STATE

    def eindeutig(paare):
        daten = {}
        for schluessel, wert in paare:
            if schluessel in daten:
                raise ValueError(f"doppelter Zustandsschlüssel: {schluessel}")
            daten[schluessel] = wert
        return daten

    try:
        # Der versionierte Zustand darf nicht durch Löschen als leer gelten.
        daten = json.loads(pfad.read_text(encoding="utf-8"), object_pairs_hook=eindeutig)
        if not isinstance(daten, dict):
            raise ValueError("Zustand ist kein Objekt")
        erstmals = daten.get("ungeklaert_erstmals")
        if not isinstance(erstmals, dict):
            raise ValueError("ungeklaert_erstmals fehlt oder ist kein Objekt")
        for slug, zeit in erstmals.items():
            if (not isinstance(slug, str) or not slug or not isinstance(zeit, str)
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", zeit)):
                raise ValueError("ungültiger Eintrag im Altersregister")
            date.fromisoformat(zeit)
        return daten
    except (OSError, UnicodeError, ValueError) as exc:
        raise WerkzeugFehler(f"Wachzustand nicht lesbar: {exc}") from exc


def state_schreiben(root: Path, daten: dict) -> None:
    pfad = root / STATE
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    os.replace(tmp, pfad)


def ledger(root: Path, eintrag: dict) -> None:
    """Append-only-Beleg: Jeder Eingriff hinterlässt eine Zeile."""
    pfad = root / LEDGER
    pfad.parent.mkdir(parents=True, exist_ok=True)
    zeile = {"zeit": _jetzt(), **eintrag}
    with pfad.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(zeile, ensure_ascii=False, sort_keys=True) + "\n")


def _git_sha(root: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                              capture_output=True, text=True, timeout=15,
                              check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# --------------------------------------------------------------------------
#  Selbstheilung
# --------------------------------------------------------------------------

def heilen(root: Path = ROOT, *, trocken: bool = False) -> dict:
    """Repariert, was deterministisch reparierbar ist – und sagt, was nicht.

    Drei Eingriffe, alle idempotent, alle mit Belegzeile:

      1. `anker`   – fehlt `{#ki-hinweis}` im Impressum, wird die
                     Überschrift wieder verankert. Ohne Anker läuft
                     `rel="describedby"` auf 84 Seiten und im Feed ins Leere.
      2. `spiegel` – weicht eine der beiden RSS-Vorlagen ab und trägt genau
                     eine den Herkunfts-Kanal, wird die andere angeglichen.
                     Tragen BEIDE den Kanal und unterscheiden sich trotzdem,
                     wird nicht geraten: Das ist ein Konflikt für Menschen.
      3. `bilder`  – abgeleitete Formate eines deklarierten KI-Originals
                     werden entfernt. Das Cover-Template liefert deklarierte
                     Originale bewusst ohne Umkodierung aus (cover.html);
                     die Geschwister sind weder referenziert noch markiert.

    Alles Übrige (Vorlagenvertrag, Anbieter-Auskunft, Bildherkunft,
    `menschlich`-Belege) geht nach `eskalation` – mit Grund. Eine Heilung,
    die eine Entscheidung erfindet, ist schlimmer als keine.
    """
    eingriffe: list[dict] = []
    eskalation: list[dict] = []
    sha = _git_sha(root)

    # 1) Impressum-Anker ---------------------------------------------------
    imp = root / IMPRESSUM
    if not imp.is_file():
        eskalation.append({"grund": "anker", "datei": IMPRESSUM,
                           "text": "Impressum nicht gefunden – Ankerziel fehlt"})
    elif IMPRESSUM_ANKER not in imp.read_text(encoding="utf-8", errors="ignore"):
        text = imp.read_text(encoding="utf-8")
        neu = _anker_einsetzen(text)
        if neu == text:
            eskalation.append({
                "grund": "anker", "datei": IMPRESSUM,
                "text": "Überschrift zum KI-Hinweis nicht gefunden – Anker "
                        "kann nicht sicher ergänzt werden"})
        else:
            eingriffe.append({"art": "anker", "datei": IMPRESSUM,
                              "text": "Anker {#ki-hinweis} wiederhergestellt"})
            if not trocken:
                imp.write_text(neu, encoding="utf-8")

    # 2) RSS-Spiegel -------------------------------------------------------
    abweichung = rss_spiegel_abweichung(root)
    if abweichung in ("quelle", "spiegel"):
        von = RSS_QUELLE if abweichung == "quelle" else RSS_SPIEGEL
        auf = RSS_SPIEGEL if abweichung == "quelle" else RSS_QUELLE
        eingriffe.append({"art": "spiegel", "datei": auf,
                          "text": f"bytgleich aus {von} angeglichen"})
        if not trocken:
            (root / auf).write_bytes((root / von).read_bytes())
    elif abweichung == "beide":
        eskalation.append({
            "grund": "spiegel", "datei": f"{RSS_QUELLE} / {RSS_SPIEGEL}",
            "text": "beide RSS-Vorlagen weichen voneinander ab und tragen den "
                    "Herkunfts-Kanal – welche Fassung gilt, ist eine "
                    "Entscheidung, kein Heilauftrag"})

    # 3) Abgeleitete Bildformate ------------------------------------------
    for seite, rel in unmarkierte_ableitungen(root):
        eingriffe.append({"art": "bilder", "datei": f"static/{rel}",
                          "text": f"unmarkierte Ableitung von {seite.slug} entfernt "
                                  "(Original trägt IPTC, Ableitung nicht)"})
        if not trocken:
            (root / "static" / rel).unlink()

    # 4) Vorlagenvertrag: melden, nicht selbst an fassbaren Code gehen -----
    for v in kanal_vertrag(root):
        datei = root / v.datei
        if not datei.is_file():
            eskalation.append({"grund": v.regel, "datei": v.datei, "text": "Datei fehlt"})
            continue
        if v.nadel not in datei.read_text(encoding="utf-8", errors="ignore"):
            eskalation.append({"grund": v.regel, "datei": v.datei, "text": v.meldung})

    if not trocken and (eingriffe or eskalation):
        for e in eingriffe:
            ledger(root, {"schritt": "heilen", "revision": sha, **e})

    return {"eingriffe": eingriffe, "eskalation": eskalation, "revision": sha,
            "trocken": trocken}


def _anker_einsetzen(text: str) -> str:
    """Verankert die Hinweis-Überschrift im Impressum, ohne Inhalt zu ändern.

    Gesucht wird die Überschrift, die auf den KI-Hinweis zeigt – in jeder
    Überschriftenstufe. Gefunden wird zeilenweise; ersetzt wird genau diese
    eine Zeile. Findet sich keine, bleibt der Text unverändert (dann meldet
    `heilen()` Eskalation statt zu raten).
    """
    zeilen = text.splitlines(keepends=True)
    for i, zeile in enumerate(zeilen):
        m = HINWEIS_UEBERSCHRIFT.match(zeile.rstrip("\n"))
        if not m:
            continue
        if IMPRESSUM_ANKER in m.group(2):
            return text
        zeilen[i] = f"{m.group(1)} {m.group(2)} {IMPRESSUM_ANKER}\n"
        return "".join(zeilen)
    return text


# --------------------------------------------------------------------------
#  Abhängigkeiten sichtbar machen (K4, 07.11.2026)
# --------------------------------------------------------------------------

def abhaengigkeiten(root: Path = ROOT) -> list[str]:
    """Welche Messwerkzeuge fehlen – Klartext statt Traceback.

    Befund: Ohne PyYAML starb das Gate mit `ModuleNotFoundError` und Exit 1.
    Exit 1 heißt im Deploy „Inhalts-Fund"; ein Abhängigkeitsausfall ist aber
    ein Werkzeugfehler (Exit 2) und gehört über den einen Meldeweg
    (scripts/werkzeugbefund.py, C38). Wer den Unterschied nicht sieht, jagt
    einen Phantom-Bestand.
    """
    fehlen = []
    try:
        import yaml  # noqa: F401
    except ImportError:
        fehlen.append("pyyaml (Register- und Cover-Provenienz-Leser)")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        fehlen.append("pillow (IPTC-Feld in der Bilddatei, Regel M3)")
    # Auch das Geschwister-Modul ist Messwerkzeug: Ist es nicht ladbar, ist
    # M3 blind. Geprüft wird gegen das VERZEICHNIS DIESER DATEI und nicht
    # gegen `root` – sonst meldete jede Testfassung ein fehlendes Werkzeug.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import ki_bild_markierung  # noqa: F401, PLC0415
    except ImportError:
        fehlen.append("ki_bild_markierung (IPTC-Feld in der Bilddatei, Regel M3)")
    return fehlen


def werkzeugbefund_melden(schritt: str, text: str, root: Path = ROOT) -> None:
    """Befund über den einen Meldeweg – schlägt selbst nie fehl."""
    sys.path.insert(0, str(root / "scripts"))
    try:
        import werkzeugbefund  # noqa: PLC0415
    except ImportError:
        return
    try:
        werkzeugbefund.melden(schritt, text)
    except Exception:  # pragma: no cover – ein Melder darf nie selbst töten
        pass


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(
        "ki_provenienz.py ist eine Bibliothek. CLI: scripts/ki_provenienz_gate.py "
        "(--gate, --heilen, --wache, --selftest, --json)")
