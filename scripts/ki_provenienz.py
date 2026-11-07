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

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
#  VOKABULAR – genau einmal, für Vorlagen und Wache zugleich
# --------------------------------------------------------------------------

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
        teile = verz.parts
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

_META = re.compile(r"""<meta\s+name=["']?ai-generated["']?\s+content=["']?(true|false)["']?""", re.I)
_SCOPE = re.compile(r"""<meta\s+name=["']?ai-generated-scope["']?\s+content=["']?([a-z,]*)["']?""", re.I)
_TOOLBAR = re.compile(r"""<(div|section)[^>]{0,120}class=["']?ff-voice-slot""", re.I)
_CREDIT = re.compile(r""""creditText"\s*:\s*"([^"]{0,200})" """, re.I)


def signale(html: str) -> dict:
    """Alle maschinenlesbaren und sichtbaren Angaben einer gebauten Seite.

    Bewusst aus dem BAUPRODUKT gelesen, nicht aus dem Frontmatter: Eine
    halbe Regression (ein Kanal da, der andere weg) fällt nur auf, wenn die
    ausgelieferte Wahrheit verglichen wird.

    Die Tonspur wird aus dem Vorhandensein der Lesehilfe abgeleitet – nicht
    aus einer nachgebauten Template-Bedingung. So folgt die Wache der
    Ausspielung, auch wenn jemand die Bedingung in ff_voice_toolbar.html
    ändert; ein zweiter Pflegeort wäre genau der Fehler, den M4 verhindern
    soll.
    """
    meta = _META.search(html)
    scope = _SCOPE.search(html)
    bereiche = tuple(b for b in (scope.group(1).split(",") if scope else ()) if b in MODALITAETEN)
    return {
        "meta": bool(meta and meta.group(1).lower() == "true"),
        "bereiche": bereiche,
        "describedby": "rel=describedby" in html or 'rel="describedby"' in html,
        "toolbar": bool(_TOOLBAR.search(html)),
        "anker": {m: (a in html) for m, a in ANKER.items()},
        "credit": (_CREDIT.search(html).group(1) if _CREDIT.search(html) else ""),
        "bild_attribut": "data-digital-source-type" in html,
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
#  Feed
# --------------------------------------------------------------------------

def feed_pfad(root: Path = ROOT) -> Path:
    return root / BAU / "index.xml"


def feed_items(pfad: Path) -> list[dict]:
    """Items des gebauten Feeds samt Herkunftsangaben.

    Ohne `xml.etree`-Namensraum-Falle: `bool(Element)` ist für ein Element
    ohne Kinder False – wer das übersieht, zählt 50 vorhandene Angaben als
    null. Deshalb wird hier auf `is None` geprüft.
    """
    import xml.etree.ElementTree as ET

    if not pfad.is_file():
        return []
    try:
        wurzel = ET.parse(pfad).getroot()
    except ET.ParseError as exc:
        raise WerkzeugFehler(f"Feed ist kein valides XML: {exc}") from exc
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "media": "http://search.yahoo.com/mrss/",
          NAMESPACE_KURZ: NAMESPACE}
    kanal = wurzel.find("channel")
    if kanal is None:
        return []
    raus = []
    for item in kanal.findall("item"):
        guid = item.findtext("guid") or item.findtext("link") or ""
        beschrieben = [a for a in item.findall("atom:link", ns)
                       if (a.get("rel") or "") == "describedby"]
        scope = item.find(f"{NAMESPACE_KURZ}:ai-generated-scope", ns)
        raus.append({
            "guid": guid,
            "slug": _slug_aus_url(guid),
            "scope": (scope.text or "").strip() if scope is not None else "",
            "ai_generated": item.find(f"{NAMESPACE_KURZ}:ai-generated", ns) is not None,
            "describedby": bool(beschrieben),
            "media_credit": item.find("media:credit", ns) is not None,
        })
    return raus


def feed_kanal_angabe(pfad: Path) -> bool:
    """Trägt der FEED (Kanal-Ebene) die IANA-Relation auf den Hinweis?"""
    import xml.etree.ElementTree as ET

    if not pfad.is_file():
        return False
    try:
        wurzel = ET.parse(pfad).getroot()
    except ET.ParseError:
        return False
    kanal = wurzel.find("channel")
    if kanal is None:
        return False
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    return any((a.get("rel") or "") == "describedby"
               for a in kanal.findall("atom:link", ns))


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


# --------------------------------------------------------------------------
#  Register: ungeklärte Herkunft (offener Punkt 3 aus #1028)
# --------------------------------------------------------------------------

def register(root: Path = ROOT) -> dict[str, set[str]]:
    """`maschinell`/`menschlich` aus data/ki_kennzeichnung.yaml.

    Bewusst abhängigkeitsfrei gelesen (derselbe Leser wie in
    scripts/ki_kennzeichnung_gate.py): Das Register muss auch dann lesbar
    bleiben, wenn PyYAML fehlt – sonst meldet die Wache blind.
    """
    daten: dict[str, set[str]] = {"maschinell": set(), "menschlich": set()}
    pfad = root / "data" / "ki_kennzeichnung.yaml"
    if not pfad.is_file():
        return daten
    aktuell = None
    for zeile in pfad.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-z_]+):\s*$", zeile)
        if m:
            aktuell = m.group(1) if m.group(1) in daten else None
            continue
        m = _RE_LISTE.match(zeile)
        if m and aktuell:
            wert = m.group(1).strip().strip("\"'")
            if re.fullmatch(r"[A-Za-z0-9._\-]+", wert):
                daten[aktuell].add(wert)
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
    if not pfad.is_file():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


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
