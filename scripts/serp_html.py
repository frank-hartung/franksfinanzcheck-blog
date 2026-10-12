#!/usr/bin/env python3
"""Minimaler HTML-Baum mit CSS-Teilmenge – die Grundlage aller Schlüssellos-Anbieter.

    from serp_html import baum, auswerten

    dokument = baum(html_text)
    for karte in dokument.waehle("article.result"):
        titel = karte.waehle_eins("h2 a").text()

WARUM EIGENER BAUM STATT REGEX ODER FREMDBIBLIOTHEK
---------------------------------------------------
Ohne API-Anbindung (Auftrag vom 12.10.2026) ist die einzige Quelle rohes
HTML. Drei Wege standen zur Wahl:

  · **Regex** – scheitert an verschachtelten Tags, Kommentaren und an der
    Tatsache, dass Suchmaschinen ihr Markup laufend umbauen. Ein Regex,
    der heute passt, liefert morgen still eine leere Liste. Genau die
    Schadensklasse, die dieses Repo unter #514 kennengelernt hat.
  · **BeautifulSoup / lxml** – Fremdabhängigkeit. Der Rest dieses Repos
    arbeitet in der Automatisierung ausschließlich mit der
    Standardbibliothek, und ein CI-Lauf, der an `pip install` hängt, ist
    ein Ausfall, den niemand sieht.
  * **Eigener Baum auf `html.parser`** – Standardbibliothek, fehlertolerant,
    prüfbar. `html.parser` bricht bei kaputtem HTML nicht ab, es liefert,
    was es findet. Genau das braucht ein Scraper.

Der Baum ist bewusst klein: Tag-Name, Attribute, Kinder, Text. Keine
Skripte, kein CSS, kein Layout. Er existiert nur, damit die Anbieter
dieselbe Frage stellen können: „Welche Knoten passen auf diesen Selektor?"

BEWUSSTE GRENZEN
----------------
Kein `>` (Kind), kein `+`/`~` (Geschwister), keine Pseudo-Klassen. Nur
Nachfahr, Klasse, ID, Attribut und Komma-Alternative. Das deckt alle
Trefferkarten der unterstützten Suchmaschinen ab; mehr Selektor-Sprache
wäre ungenutzte Fläche, die gewartet werden müsste.

Alles hier läuft ohne Netz und ist in scripts/tests/test_suchradar.py
mit echten HTML-Proben festgenagelt.
"""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from url_host import ist_host_oder_subdomain  # noqa: E402  (Host-exakte URL-Wahrheit)

__all__ = ["baum", "Knoten", "attribut_url", "uddg_entpacken", "domaene_aus_url"]

# Elemente ohne Inhalt. Ohne diese Liste würde <br> den Rest des Dokuments
# in sich hineinschlucken – und damit jeden folgenden Treffer.
LEERE_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})

# Wird beim Textsammeln als Wortgrenze behandelt. Ein <div>-Wechsel ohne
# Trennzeichen klebt sonst „Strom sparenTipps" zusammen.
BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
    "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
    "pre", "section", "table", "td", "th", "tr", "ul",
})

# Alles, was niemals Trefferinhalt ist. Ohne diese Liste landet
# `var dataLayer = [...]` als Snippet im Bericht.
UEBERSPRINGEN = frozenset({"script", "style", "noscript", "template", "svg"})

# Ein Selektor ist eine Kette einfacher Selektoren, durch Leerzeichen
# getrennt (Nachfahr). Beispiel: "article.result h2 a[href]"
_SELEKTOR_RE = re.compile(r"([#.]?[\w*-]+|\[[\w:-]+\])")


# ====================================================================
#  KNOTEN
# ====================================================================
class Knoten:
    """Ein Element im Baum. `roh_text` ist bei Textknoten gesetzt, `tag` dann leer."""

    __slots__ = ("tag", "attribute", "kinder", "eltern", "roh_text")

    def __init__(self, tag: str = "", attribute: dict | None = None,
                 eltern: "Knoten | None" = None, text: str = ""):
        self.tag = tag
        self.attribute = attribute or {}
        self.kinder: list[Knoten] = []
        self.eltern = eltern
        self.roh_text = text

    # ------------------------------------------------------------ Ausgabe
    def text_inhalt(self, trenner: str = " ") -> str:
        """Sichtbarer Text dieses Teilbaums, normalisiert.

        Normalisiert heißt: Entities aufgelöst, Whitespace kollabiert.
        Suchmaschinen liefern Snippets mit Zeilenumbrüchen und
        mehrfachen Leerzeichen – ungeglättet landet das 1:1 im Bericht.
        """
        teile: list[str] = []
        _sammle_text(self, teile)
        roh = trenner.join(t for t in (p.strip() for p in teile) if t)
        return re.sub(r"\s+", " ", roh).strip()

    # Kurzform; `text()` liest sich im Anbieter wie eine Frage.
    def text(self) -> str:                                   # noqa: A003
        return self.text_inhalt()

    def attr(self, name: str, vorgabe: str = "") -> str:
        return str(self.attribute.get(name, vorgabe) or vorgabe)

    def klassen(self) -> frozenset:
        return frozenset((self.attribute.get("class") or "").split())

    # ------------------------------------------------------------ Suche
    def waehle(self, selektor: str) -> list["Knoten"]:
        """Alle Nachfahren, die auf den Selektor passen – in Dokumentreihenfolge."""
        return auswerten(self, selektor)

    def waehle_eins(self, selektor: str) -> "Knoten | None":
        treffer = auswerten(self, selektor)
        return treffer[0] if treffer else None

    def vorfahren(self):
        knoten = self.eltern
        while knoten is not None:
            yield knoten
            knoten = knoten.eltern

    def naechster(self, selektor: str) -> "Knoten | None":
        """Erster Knoten, der auf den Selektor passt – Suche in Dokumentreihenfolge.

        Braucht es, weil Suchmaschinen Trefferkarten unterschiedlich
        verschachteln: Mal steht der Titel in der Karte, mal in einem
        Geschwisterknoten. Eine Suche ab der Wurzel findet beides.
        """
        for kandidat in _durchlauf(self):
            if kandidat is self:
                continue
            if _passt_einfach(kandidat, selektor.strip()):
                return kandidat
        return None

    def __repr__(self) -> str:                                # pragma: no cover
        return f"<Knoten {self.tag or '#text'} {self.attribute}>"


def _sammle_text(knoten: Knoten, teile: list[str]) -> None:
    if knoten.tag in UEBERSPRINGEN:
        return
    if not knoten.tag:
        if knoten.roh_text:
            teile.append(knoten.roh_text)
        return
    for kind in knoten.kinder:
        _sammle_text(kind, teile)
    if knoten.tag in BLOCK_TAGS:
        teile.append(" ")


def _durchlauf(knoten: Knoten):
    """Tiefensuche in Dokumentreihenfolge (Vorderordnung)."""
    for kind in knoten.kinder:
        yield kind
        yield from _durchlauf(kind)


# ====================================================================
#  PARSER
# ====================================================================
class _Baumbauer(HTMLParser):
    """Baut den Baum. `html.parser` liefert Events; hier entsteht Struktur.

    Fehlertoleranz ist Absicht: Ein nicht geschlossenes </div> darf nicht
    bedeuten, dass die Hälfte der Treffer verschwindet. Deshalb wird bei
    einem End-Tag gesucht, ob es im Stapel überhaupt vorkommt – wenn ja,
    wird bis dorthin geschlossen; wenn nein, wird es ignoriert.
    """

    def __init__(self):
        # convert_charrefs=True: Entities werden beim Daten-Event bereits
        # aufgelöst. Sonst steht &amp; im Snippet statt &.
        super().__init__(convert_charrefs=True)
        self.wurzel = Knoten(tag="#dokument")
        self._stapel: list[Knoten] = [self.wurzel]

    # ------------------------------------------------------------ Helfer
    def _anhaengen(self, knoten: Knoten) -> None:
        self._stapel[-1].kinder.append(knoten)

    # ------------------------------------------------------------ Events
    def handle_starttag(self, tag, attribute):
        knoten = Knoten(tag=tag, attribute=dict(attribute), eltern=self._stapel[-1])
        self._anhaengen(knoten)
        if tag not in LEERE_TAGS:
            self._stapel.append(knoten)

    def handle_startendtag(self, tag, attribute):
        self._anhaengen(Knoten(tag=tag, attribute=dict(attribute),
                               eltern=self._stapel[-1]))

    def handle_endtag(self, tag):
        if tag in LEERE_TAGS:
            return
        namen = [k.tag for k in self._stapel]
        if tag not in namen:
            # Fremd-Endtag (typisch für minimiertes HTML). Ignorieren ist
            # sicherer als raten: Der Stapel bleibt gültig.
            return
        ziel = len(namen) - 1 - namen[::-1].index(tag)
        del self._stapel[ziel:]

    def handle_data(self, daten):
        if daten:
            self._anhaengen(Knoten(text=daten, eltern=self._stapel[-1]))


def baum(html: str) -> Knoten:
    """HTML-Text → Baum. Wirft nie: kaputtes HTML liefert einen Teilbaum."""
    parser = _Baumbauer()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:                                        # pragma: no cover
        # Ein Parser, der am Markup des Gegenübers stirbt, verwandelt eine
        # Layout-Änderung in einen Ausfall der ganzen Kette.
        pass
    return parser.wurzel


# ====================================================================
#  SELEKTOREN
# ====================================================================
def _zerlege_einfach(selektor: str) -> dict:
    """`article.result__body > ` → {tag, klassen, id, attribut}."""
    regel: dict = {"tag": "", "klassen": [], "id": "", "attribut": ""}
    for teil in _SELEKTOR_RE.findall(selektor):
        if teil.startswith("."):
            regel["klassen"].append(teil[1:])
        elif teil.startswith("#"):
            regel["id"] = teil[1:]
        elif teil.startswith("["):
            regel["attribut"] = teil[1:-1]
        elif teil != "*":
            regel["tag"] = teil.lower()
    return regel


def _passt_einfach(knoten: Knoten, selektor: str) -> bool:
    regel = _zerlege_einfach(selektor)
    if regel["tag"] and knoten.tag != regel["tag"]:
        return False
    if regel["id"] and knoten.attr("id") != regel["id"]:
        return False
    if regel["klassen"]:
        vorhanden = knoten.klassen()
        if any(k not in vorhanden for k in regel["klassen"]):
            return False
    if regel["attribut"] and regel["attribut"] not in knoten.attribute:
        return False
    return True


def auswerten(wurzel: Knoten, selektor: str) -> list[Knoten]:
    """CSS-Teilmenge: Nachfahr-Ketten und Komma-Alternativen.

    `auswerten(baum, "article.result, .web-result")` liefert die
    Vereinigung beider Muster, in Dokumentreihenfolge und ohne Duplikate.
    """
    if not selektor or not selektor.strip():
        return []
    treffer: list[Knoten] = []
    gesehen: set[int] = set()
    for alternative in selektor.split(","):
        kette = [s for s in alternative.split() if s and s != ">"]
        if not kette:
            continue
        for kandidat in _durchlauf(wurzel):
            if id(kandidat) in gesehen:
                continue
            if _passt_kette(kandidat, kette):
                gesehen.add(id(kandidat))
                treffer.append(kandidat)
    return treffer


def _passt_kette(knoten: Knoten, kette: list[str]) -> bool:
    """Die Kette wird rückwärts geprüft: letzter Selektor = der Knoten selbst."""
    if not _passt_einfach(knoten, kette[-1]):
        return False
    rest = kette[:-1]
    vorfahr = knoten.eltern
    while rest:
        if vorfahr is None:
            return False
        if _passt_einfach(vorfahr, rest[-1]):
            rest = rest[:-1]
        vorfahr = vorfahr.eltern
    return True


# ====================================================================
#  URL-HYGIENE
# ====================================================================
def attribut_url(knoten: Knoten | None, basis: str = "") -> str:
    """`href` eines Knotens – absolut, Entitäten aufgelöst, Fragment bereinigt."""
    if knoten is None:
        return ""
    roh = knoten.attr("href") or knoten.attr("data-href") or knoten.attr("data-url")
    return url_saeubern(roh, basis)


def url_saeubern(roh: str, basis: str = "") -> str:
    if not roh:
        return ""
    roh = unescape(roh).strip()
    if roh.startswith(("javascript:", "data:", "mailto:")):
        return ""
    if basis:
        roh = urljoin(basis, roh)
    elif roh.startswith("//"):
        roh = "https:" + roh
    return roh.split("#", 1)[0].strip()


def uddg_entpacken(url: str) -> str:
    """DuckDuckGo-Umleitungslink auf die Ziel-URL zurückführen.

    DuckDuckGo liefert Treffer nicht direkt, sondern als
    `//duckduckgo.com/l/?uddg=<urlencoded>&rut=…`. Ohne diesen Schritt
    stünde in jedem Bericht dieselbe Umleitungs-URL – und die
    Wettbewerbs-Auswertung zählte nur noch duckduckgo.com.

    Die Funktion ist absichtlich eng: Sie packt nur aus, wenn die URL
    tatsächlich auf eine DuckDuckGo-Umleitung zeigt. Alles andere geht
    unverändert durch.
    """
    if not url:
        return url
    parsed = urlparse(url)
    # Host-Vergleich statt Teilzeichenkette: `"duckduckgo.com" in netloc`
    # würde auch `https://duckduckgo.com.angreifer.example/l/?uddg=…`
    # „auspacken" und damit eine fremde URL für eine DuckDuckGo-Umleitung
    # halten (Code-Scanning-Alert #83,
    # py/incomplete-url-substring-sanitization).
    #
    # Das LEERE Schema ist ausdrücklich zugelassen: DuckDuckGo liefert Treffer
    # schema-relativ als `//duckduckgo.com/l/?uddg=…` (siehe Docstring oben).
    # `url_saeubern` setzt zwar `https:` davor, diese Funktion ist aber
    # öffentlich – sie darf auch am rohen Attribut nicht anders entscheiden.
    if not ist_host_oder_subdomain(url, "duckduckgo.com",
                                   schemata=("https", "http", "")) \
            or not parsed.path.startswith("/l/"):
        return url
    werte = parse_qs(parsed.query)
    ziel = (werte.get("uddg") or [""])[0]
    return unquote(ziel) if ziel else url


def domaene_aus_url(url: str) -> str:
    """Registrierbare Domaene: `www.example.co.uk/x` → `example.co.uk`.

    Eine naive `netloc`-Auswertung trennt `www.` nicht ab und kennt keine
    mehrteiligen Endungen. Für die Wettbewerbs-Auswertung wäre das fatal:
    `www.finanztest.de` und `finanztest.de` wären zwei Wettbewerber.
    """
    try:
        netloc = (urlparse(url).netloc or "").lower()
    except ValueError:
        return ""
    netloc = netloc.split("@")[-1].split(":")[0].strip(".")
    if not netloc or netloc.replace(".", "").isdigit():
        return netloc
    teile = netloc.split(".")
    if len(teile) <= 2:
        return netloc
    zweistufig = {"co.uk", "org.uk", "com.br", "co.nz", "com.au", "co.at"}
    if ".".join(teile[-2:]) in zweistufig:
        return ".".join(teile[-3:])
    return ".".join(teile[-2:])
