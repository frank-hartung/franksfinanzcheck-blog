#!/usr/bin/env python3
"""SITECHECK-WACHE – die vier Prüfbereiche des Pergamon Website Check (2016)
gegen den GEBAUTEN Blog.

Quelle der Regeln: https://www.pergamon-interactive.de/sitecheck-2016.html
und die vierteilige Serie dazu (Meta-Elemente, Webseiten-Struktur, Website
Technik, Konfiguration). Der Check bewertet eine EINZELNE URL – diese Wache
bewertet alle indexierbaren Seiten des Builds, weil ein Fehler auf Seite 73
genauso zählt wie auf der Startseite.

Warum nicht „einfach den Online-Check laufen lassen“: Der Dienst ist 2016
geschrieben. Einige Empfehlungen sind inzwischen falsch oder wirkungslos
(meta keywords, meta expires, mod_pagespeed, JS-Dateien um jeden Preis
zusammenfassen). Sie werden deshalb NICHT umgesetzt, sondern im Report
`SITECHECK-2016-OPTIMIERUNG-2026-10-27.md` begründet. Was bleibt, ist der
messbare Kern – Titel/Description-Fenster, echte Überschriftenhierarchie,
semantisches HTML, erreichbare interne Links, schlanke Technik, robots.txt
und Sitemap.

Regeln (harte Funde = Exit 1, Hinweise = Exit 0):
  M1  Doctype vorhanden                 M2  html lang + charset
  M3  viewport                         M4  Title 1–60 Zeichen
  M5  Description 110–156 Zeichen      M6  genau ein https-Canonical
  M7  kein generator-Tag               M8  Title/Description eindeutig
  S1  genau eine H1, max. 80 Zeichen   S2  keine Überschriftensprünge
  S3  keine obsoleten Tags             S4  Bilder mit alt/Maßen/loading
  S5  Tabellen sind Datentabellen      S6  interne Links mit Ziel
  S7  kein `href="#"` / leeres href    S8  mind. 600 Zeichen Fließtext
  T1  keine Frames/Flash/Plugins       T2  Skripte gebündelt & defer/async
  T3  keine fremden Skript-Hosts       T4  Stylesheets gebündelt
  K1  robots.txt mit Sitemap           K2  sitemap.xml nur https/eigene URLs
  K3  Sitemap == indexierbare Canonicals (keine noindex-URL)
  K4  404-Seite vorhanden              K5  HTML übertragbar (gzip-Probe)

Hinweise (kein Fehler): <b>/<i>/<u> sind in HTML5 erlaubt, aber <strong>/
<em> sind die bessere semantische Wahl (Empfehlung des Checks).

Nutzung:
  python3 scripts/sitecheck_wache.py                  # public/ prüfen
  python3 scripts/sitecheck_wache.py --site /tmp/public
  python3 scripts/sitecheck_wache.py --json          # Maschinenausgabe
  python3 scripts/sitecheck_wache.py --selftest      # Detektor prüfen (offline)

Exit: 0 = grün (Hinweise erlaubt) · 1 = harte Funde · 2 = Selbsttest/Setup.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import tempfile
from urllib.parse import unquote
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
STANDARD_SITE = BLOG_DIR / "public"

TITLE_MAX = 60
DESC_MIN = 110
DESC_MAX = 156
H1_MAX = 80
TEXT_MIN = 600
SCRIPT_MAX = 6
CSS_MAX = 2
GZIP_MAX = 120_000
PLUGIN_TAGS = frozenset({"object", "embed"})
OBSOLETE = frozenset({
    "acronym", "applet", "basefont", "big", "blink", "center", "dir",
    "font", "frame", "frameset", "isindex", "marquee", "noframes",
    "strike", "tt",
})
HINWEIS_TAGS = frozenset({"b", "i", "u"})
IGNORIERT = frozenset({"script", "style", "noscript", "template"})
HEADING = re.compile(r"^h[1-6]$")
EIGENE_DOMAIN = "franksfinanzcheck.de"


@dataclass(frozen=True)
class Befund:
    regel: str
    bereich: str
    datei: str
    text: str
    schwere: str = "fehler"

    def als_dict(self) -> dict:
        return {"regel": self.regel, "bereich": self.bereich,
                "datei": self.datei, "text": self.text,
                "schwere": self.schwere}


@dataclass
class Seite:
    rel: str
    bytes: int
    doctype: bool = False
    lang: str = ""
    charset: bool = False
    metas: list = None
    canonical: list = None
    title: str = ""
    description: str = ""
    robots: str = ""
    generator: bool = False
    headings: list = None
    imgs: list = None
    tables: list = None
    links: list = None
    scripts: list = None
    stylesheets: list = None
    iframes: list = None
    obsolete: list = None
    hinweise: list = None
    plugins: list = None
    ids: set = None
    sichtbarer_text: str = ""

    def __post_init__(self):
        for feld in ("metas", "canonical", "headings", "imgs", "tables",
                     "links", "scripts", "stylesheets", "iframes",
                     "obsolete", "hinweise", "plugins"):
            if getattr(self, feld) is None:
                setattr(self, feld, [])
        for feld in ("ids",):
            if getattr(self, feld) is None:
                setattr(self, feld, [])

    @property
    def indexierbar(self) -> bool:
        return self.robots.strip().lower().startswith("index")

    def meta(self, name: str) -> str:
        for eintrag in self.metas:
            if str(eintrag.get("name", "")).lower() == name:
                return str(eintrag.get("content", ""))
        return ""


class SeitenParser(HTMLParser):
    """Liest eine gebaute HTML-Datei – ohne Fremdpakete, ohne Netz.

    Zwei Fallen sind bewusst gelöst: `<title>` in eingebetteten SVG-Diagrammen
    ist KEIN Seitentitel (sonst werden Titel 250 Zeichen lang), und Text in
    `<script>/<style>/<svg>` ist KEIN Fließtext.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.doctype = False
        self.lang = ""
        self.metas: list[dict] = []
        self.links: list[dict] = []
        self.scripts: list[dict] = []
        self.stylesheets: list[dict] = []
        self.imgs: list[dict] = []
        self.tables: list[bool] = []
        self.iframes: list[dict] = []
        self.href: list[str] = []
        self.obsolete: list[str] = []
        self.hinweise: list[str] = []
        self.plugins: list[str] = []
        self.ids: set[str] = set()
        self.headings: list[list] = []
        self.title = ""
        self.text_teile: list[str] = []
        self._kopf = False
        self._fokus = ""
        self._svg = 0
        self._ignoriert = 0
        self._tabelle = -1

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(unquote(str(a["id"])))
        if tag in IGNORIERT:
            self._ignoriert += 1
        if tag == "svg":
            self._svg += 1
        if tag == "head":
            self._kopf = True
        if tag == "html":
            self.lang = str(a.get("lang", ""))
        if tag == "meta":
            self.metas.append(a)
        if tag == "link":
            self.links.append(a)
            if a.get("rel") == "stylesheet":
                self.stylesheets.append(a)
        if tag == "title" and self._kopf and not self._svg:
            self._fokus = "title"
        if HEADING.match(tag) and not self._svg and not self._ignoriert:
            self.headings.append([int(tag[1]), "", bool(a.get("id"))])
            self._fokus = tag
        if tag == "img" and not self._svg:
            self.imgs.append(a)
        if tag == "table":
            self.tables.append(False)
            self._tabelle = len(self.tables) - 1
        if tag == "th" and self._tabelle >= 0:
            self.tables[self._tabelle] = True
        if tag == "iframe":
            self.iframes.append(a)
        if tag == "a" and "href" in a:
            # <a id="anker"> ohne href ist ein SPRUNGZIEL, kein Link.
            self.href.append(str(a.get("href") or ""))
        if tag == "script":
            if a.get("src"):
                self.scripts.append(a)
        if tag in OBSOLETE:
            self.obsolete.append(tag)
        if tag in HINWEIS_TAGS:
            self.hinweise.append(tag)
        if tag in PLUGIN_TAGS:
            self.plugins.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in IGNORIERT and self._ignoriert:
            self._ignoriert -= 1
        if tag == "svg" and self._svg:
            self._svg -= 1
        if tag == "head":
            self._kopf = False
        if tag == "table":
            self._tabelle = -1
        if tag == self._fokus:
            self._fokus = ""

    def handle_data(self, data):
        if self._fokus == "title":
            self.title += data
        elif self._fokus and self.headings:
            lvl, text, hat_id = self.headings[-1]
            self.headings[-1] = [lvl, text + data, hat_id]
        if not self._kopf and not self._ignoriert and not self._svg:
            self.text_teile.append(data)


def analysiere(rel: str, rohtext: str) -> Seite:
    """Reine Funktion: HTML-Text -> Seitenbefund. Kein Dateisystem, kein Netz."""
    p = SeitenParser()
    try:
        p.feed(rohtext)
        p.close()
    except Exception as exc:  # ein Parser-Crash ist ein Befund, kein stilles Grün
        seite = Seite(rel=rel, bytes=len(rohtext.encode("utf-8")))
        seite.sichtbarer_text = ""
        seite.obsolete = [f"parserfehler:{exc.__class__.__name__}"]
        return seite
    metas = p.metas
    def meta(name: str) -> str:
        for eintrag in metas:
            if str(eintrag.get("name", "")).lower() == name:
                return str(eintrag.get("content", ""))
        return ""
    seite = Seite(
        rel=rel,
        bytes=len(rohtext.encode("utf-8")),
        doctype=p.doctype,
        lang=p.lang,
        charset=any("charset" in m for m in metas),
        metas=metas,
        canonical=[str(l.get("href", "")) for l in p.links
                   if l.get("rel") == "canonical"],
        title=" ".join(p.title.split()),
        description=meta("description"),
        robots=meta("robots"),
        generator=any(str(m.get("name", "")).lower() == "generator"
                      for m in metas),
        headings=[[lvl, " ".join(t.split()), hat_id]
                  for lvl, t, hat_id in p.headings],
        imgs=p.imgs,
        tables=p.tables,
        links=p.href,
        scripts=p.scripts,
        stylesheets=p.stylesheets,
        iframes=p.iframes,
        obsolete=p.obsolete,
        hinweise=p.hinweise,
        plugins=p.plugins,
        ids=p.ids,
        sichtbarer_text=" ".join(" ".join(p.text_teile).split()),
    )
    return seite


def _fund(regel: str, bereich: str, seite: Seite, text: str,
          schwere: str = "fehler") -> Befund:
    return Befund(regel=regel, bereich=bereich, datei=seite.rel,
                  text=text, schwere=schwere)


def meta_befunde(s: Seite) -> list[Befund]:
    b: list[Befund] = []
    if not s.doctype:
        b.append(_fund("M1", "Meta", s, "Doctype fehlt"))
    if not s.lang or not s.charset:
        b.append(_fund("M2", "Meta", s,
                       f"lang={s.lang!r}, charset={s.charset}"))
    if "width=device-width" not in s.meta("viewport"):
        b.append(_fund("M3", "Meta", s, "viewport ohne width=device-width"))
    if not s.title or len(s.title) > TITLE_MAX:
        b.append(_fund("M4", "Meta", s,
                       f"Title {len(s.title)} Zeichen (max. {TITLE_MAX})"))
    laenge = len(s.description)
    if not (DESC_MIN <= laenge <= DESC_MAX):
        b.append(_fund("M5", "Meta", s,
                       f"Description {laenge} Zeichen "
                       f"(Zielfenster {DESC_MIN}–{DESC_MAX})"))
    if len(s.canonical) != 1 or not s.canonical[0].startswith("https://"):
        b.append(_fund("M6", "Meta", s,
                       f"Canonical: {s.canonical or 'fehlt'} (genau ein https-Link)"))
    if s.generator:
        b.append(_fund("M7", "Meta", s,
                       "generator-Tag nennt Bots das CMS inkl. Version"))
    return b


def struktur_befunde(s: Seite) -> list[Befund]:
    b: list[Befund] = []
    h1 = [text for lvl, text, _ in s.headings if lvl == 1]
    if len(h1) != 1:
        b.append(_fund("S1", "Struktur", s,
                       f"{len(h1)} H1 statt genau einer"))
    elif len(h1[0]) > H1_MAX:
        b.append(_fund("S1", "Struktur", s,
                       f"H1 {len(h1[0])} Zeichen (max. {H1_MAX})"))
    vorher = 0
    for lvl, text, _ in s.headings:
        if vorher and lvl > vorher + 1:
            b.append(_fund("S2", "Struktur", s,
                           f"Überschriftensprung h{vorher} → h{lvl} "
                           f"bei {text[:50]!r}"))
            break
        vorher = lvl
    if s.obsolete:
        b.append(_fund("S3", "Struktur", s,
                       "obsolete Tags: " + ", ".join(sorted(set(s.obsolete))[:8])))
    if s.hinweise:
        b.append(_fund("S3", "Struktur", s,
                       "HTML5 erlaubt, aber semantisch schwächer: "
                       + ", ".join(f"<{t}>" for t in sorted(set(s.hinweise))),
                       schwere="hinweis"))
    for i, bild in enumerate(s.imgs):
        fehlt = [k for k in ("alt", "width", "height", "loading")
                 if k not in bild]
        if fehlt:
            b.append(_fund("S4", "Struktur", s,
                           f"img #{i + 1} ({str(bild.get('src',''))[:60]}): "
                           f"{', '.join(fehlt)} fehlt"))
    ohne_th = sum(1 for hat_th in s.tables if not hat_th)
    if ohne_th:
        b.append(_fund("S5", "Struktur", s,
                       f"{ohne_th} Tabelle(n) ohne <th> – Layout-Tabelle?"))
    ziele = " ".join(s.links)
    for pflicht in ("/impressum/", "/datenschutz/"):
        if pflicht not in ziele:
            b.append(_fund("S6", "Struktur", s,
                           f"Pflicht-Link {pflicht} fehlt"))
    tote = [h for h in s.links if h in ("", "#")]
    if tote:
        b.append(_fund("S7", "Struktur", s,
                       f"{len(tote)} Link(s) ohne Ziel (href=\"#\" oder leer)"))
    verwaist = [h for h in s.links
                if h.startswith("#") and len(h) > 1
                and unquote(h[1:]) not in s.ids]
    if verwaist:
        b.append(_fund("S7", "Struktur", s,
                       f"{len(verwaist)} Anker ohne Ziel, z. B. {verwaist[0][:60]}"))
    if len(s.sichtbarer_text) < TEXT_MIN:
        b.append(_fund("S8", "Struktur", s,
                       f"nur {len(s.sichtbarer_text)} Zeichen Fließtext "
                       f"(mind. {TEXT_MIN})"))
    return b


def technik_befunde(s: Seite) -> list[Befund]:
    b: list[Befund] = []
    if any(t in s.obsolete for t in ("frame", "frameset", "noframes")):
        b.append(_fund("T1", "Technik", s, "Frameset/Frame statt HTML5"))
    if s.plugins:
        b.append(_fund("T1", "Technik", s,
                       "Plugin-Objekt (Flash-Klasse): "
                       + ", ".join(sorted(set(s.plugins)))))
    for rahmen in s.iframes:
        if not rahmen.get("title"):
            b.append(_fund("T1", "Technik", s, "iframe ohne title"))
    if len(s.scripts) > SCRIPT_MAX:
        b.append(_fund("T2", "Technik", s,
                       f"{len(s.scripts)} externe Skripte (max. {SCRIPT_MAX})"))
    for skript in s.scripts:
        if "defer" not in skript and "async" not in skript:
            b.append(_fund("T2", "Technik", s,
                           f"Skript ohne defer/async: {skript.get('src')}"))
    for skript in s.scripts:
        src = str(skript.get("src", ""))
        if src.startswith("//") or re.match(r"^https?://", src):
            if EIGENE_DOMAIN not in src:
                b.append(_fund("T3", "Technik", s,
                               f"fremder Skript-Host: {src[:90]}"))
    if len(s.stylesheets) > CSS_MAX:
        b.append(_fund("T4", "Technik", s,
                       f"{len(s.stylesheets)} externe Stylesheets "
                       f"(max. {CSS_MAX}; CSS zusammenfassen)"))
    return b


def seiten_befunde(s: Seite) -> list[Befund]:
    return meta_befunde(s) + struktur_befunde(s) + technik_befunde(s)


def duplikat_befunde(seiten: list[Seite]) -> list[Befund]:
    b: list[Befund] = []
    for feld, regel in (("title", "M8"), ("description", "M8")):
        gesehen: dict[str, Seite] = {}
        for s in seiten:
            wert = getattr(s, feld)
            if not wert:
                continue
            if wert in gesehen:
                erste = gesehen[wert]
                b.append(Befund(
                    regel=regel, bereich="Meta", datei=s.rel,
                    text=f"{feld} doppelt mit {erste.rel}: {wert[:60]!r}"))
            else:
                gesehen[wert] = s
    return b


def konfig_befunde(ordner: Path, seiten: list[Seite]) -> list[Befund]:
    b: list[Befund] = []
    robot = ordner / "robots.txt"
    sitemap = ordner / "sitemap.xml"
    if not robot.is_file():
        b.append(Befund("K1", "Konfiguration", "robots.txt", "Datei fehlt"))
    else:
        text = robot.read_text(encoding="utf-8", errors="replace")
        treffer = re.search(r"^Sitemap:\s*(\S+)", text, re.M)
        if not treffer or not treffer.group(1).startswith("https://"):
            b.append(Befund("K1", "Konfiguration", "robots.txt",
                            "keine https-Sitemap-Zeile"))
        # Nur die Wildcard-Gruppe zählt: gezielte `Disallow: /` für
        # Trainings-Crawler (CCBot, GPTBot …) sind gewollte Policy, kein
        # Versehen. Ein globales `Disallow: /` in `User-agent: *` wäre es.
        gruppen = re.split(r"(?im)^User-agent:\s*(.+?)\s*$", text)
        wildcard = ""
        for i in range(1, len(gruppen) - 1, 2):
            if gruppen[i].strip() == "*":
                wildcard = gruppen[i + 1]
                break
        if re.search(r"^Disallow:\s*/\s*$", wildcard, re.M):
            b.append(Befund("K1", "Konfiguration", "robots.txt",
                            "Disallow: / in User-agent: * sperrt alles"))
        if re.search(r"^Disallow:\s*(/css|/js|/static|/premium|\*\.css|\*\.js)",
                     wildcard, re.M):
            b.append(Befund("K1", "Konfiguration", "robots.txt",
                            "CSS/JS für Crawler gesperrt (Rendering!)"))
    if not (ordner / "404.html").is_file():
        b.append(Befund("K4", "Konfiguration", "404.html", "Datei fehlt"))
    if not sitemap.is_file():
        b.append(Befund("K2", "Konfiguration", "sitemap.xml", "Datei fehlt"))
        return b
    inhalt = sitemap.read_text(encoding="utf-8", errors="replace")
    locs = set(re.findall(r"<loc>\s*(.*?)\s*</loc>", inhalt))
    if len(locs) < 10:
        b.append(Befund("K2", "Konfiguration", "sitemap.xml",
                        f"nur {len(locs)} URLs – Sitemap unvollständig?"))
    for loc in sorted(locs):
        if not loc.startswith("https://") or EIGENE_DOMAIN not in loc:
            b.append(Befund("K2", "Konfiguration", "sitemap.xml",
                            f"fremde/unsichere URL: {loc[:90]}"))
        if re.search(r"/(page|go|tags|suche)/", loc):
            b.append(Befund("K2", "Konfiguration", "sitemap.xml",
                            f"nicht indexierbare URL: {loc[:90]}"))
    # Sitemap und robots-Meta dürfen nie auseinanderlaufen.
    indexierbar = {s.canonical[0] for s in seiten
                   if s.indexierbar and len(s.canonical) == 1}
    for loc in sorted(locs - indexierbar):
        b.append(Befund("K3", "Konfiguration", "sitemap.xml",
                        f"URL ohne index, follow: {loc[:90]}"))
    for url in sorted(indexierbar - locs):
        b.append(Befund("K3", "Konfiguration", "sitemap.xml",
                        f"indexierbare Seite fehlt: {url[:90]}"))
    return b


def messwerte(ordner: Path, seiten: list[Seite]) -> dict:
    idx = [s for s in seiten if s.indexierbar]
    if not idx:
        return {"indexierbare_seiten": 0}
    groesse = sorted(s.bytes for s in idx)
    probe = idx[len(idx) // 2]
    komprimiert = len(gzip.compress(
        (ordner / probe.rel).read_bytes(), compresslevel=9))
    return {
        "gebaute_html_dateien": len(seiten),
        "indexierbare_seiten": len(idx),
        "html_bytes_median": groesse[len(groesse) // 2],
        "html_bytes_max": groesse[-1],
        "gzip_bytes_median_probe": komprimiert,
        "externe_skripte_max": max(len(s.scripts) for s in idx),
        "externe_stylesheets_max": max(len(s.stylesheets) for s in idx),
        "bilder": sum(len(s.imgs) for s in idx),
        "tabellen": sum(len(s.tables) for s in idx),
    }


def pruefe_site(ordner: Path) -> tuple[list[Befund], dict]:
    if not ordner.is_dir():
        raise FileNotFoundError(f"Build-Verzeichnis fehlt: {ordner}")
    seiten = []
    for pfad in sorted(ordner.rglob("*.html")):
        rel = pfad.relative_to(ordner).as_posix()
        seiten.append(analysiere(
            rel, pfad.read_text(encoding="utf-8", errors="replace")))
    befunde: list[Befund] = []
    idx = [s for s in seiten if s.indexierbar]
    if not idx:
        befunde.append(Befund("K0", "Konfiguration", "-",
                              "keine einzige indexierbare Seite – "
                              "Build oder robots-Meta prüfen"))
        return befunde, {"indexierbare_seiten": 0}
    for s in idx:
        befunde.extend(seiten_befunde(s))
    befunde.extend(duplikat_befunde(idx))
    befunde.extend(konfig_befunde(ordner, seiten))
    werte = messwerte(ordner, seiten)
    if werte.get("gzip_bytes_median_probe", 0) > GZIP_MAX:
        befunde.append(Befund(
            "K5", "Konfiguration", "HTML",
            f"Median-HTML gzip {werte['gzip_bytes_median_probe']} Byte "
            f"über Budget {GZIP_MAX} – Markup/Bilder verkleinern"))
    return befunde, werte


# ---------------------------------------------------------------------------
# Selbsttest: prüft den DETEKTOR, nicht den liegenden Blog (DAUERVORGABE).
# ---------------------------------------------------------------------------
SAUBER = """<!DOCTYPE html><html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index, follow">
<title>Ein Titel mit genau sechzig Zeichen maximal im Fenster</title>
<meta name="description" content="Eine Seitenbeschreibung im Fenster des Website Checks: Sie nennt das Thema, bleibt konkret und ist lang genug, damit Google sie nicht abschneidet.">
<link rel="canonical" href="https://franksfinanzcheck.de/beispiel/">
</head><body>
<h1>Eine klare Hauptüberschrift</h1>
<h2>Erster Abschnitt</h2>
<p>""" + ("Dies ist ein lesbarer Fließtext über Fixkosten. " * 20) + """</p>
<h2>Zweiter Abschnitt</h2>
<p><img src="/bild.avif" alt="Beispiel" width="800" height="450" loading="lazy"></p>
<table><tr><th>Spalte</th></tr><tr><td>Wert</td></tr></table>
<a href="/impressum/">Impressum</a> <a href="/datenschutz/">Datenschutz</a>
<script defer src="/premium/ff-premium.js"></script>
</body></html>"""
ROBOTS = "User-agent: *\nAllow: /\nDisallow: /go/\nSitemap: https://franksfinanzcheck.de/sitemap.xml\n"
SITEMAP = ('<?xml version="1.0" encoding="utf-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           '<url><loc>https://franksfinanzcheck.de/beispiel/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/zwei/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/drei/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/vier/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/fuenf/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/sechs/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/sieben/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/acht/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/neun/</loc></url>'
           '<url><loc>https://franksfinanzcheck.de/zehn/</loc></url>'
           '</urlset>')


SEITEN = ["beispiel", "zwei", "drei", "vier", "fuenf",
          "sechs", "sieben", "acht", "neun", "zehn"]


def _temp_site(ordner: Path, html_text: str = SAUBER,
               robots: str = ROBOTS, sitemap: str = SITEMAP) -> None:
    """Zehn kleine, aber voneinander verschiedene Seiten (M8, K3 prüfbar)."""
    for i, slug in enumerate(SEITEN, start=1):
        text = html_text.replace("<title>", f"<title>{i}. ")
        text = text.replace("Eine Seitenbeschreibung",
                            f"{i}. Eine Seitenbeschreibung")
        text = text.replace("https://franksfinanzcheck.de/beispiel/",
                            f"https://franksfinanzcheck.de/{slug}/")
        if slug == "beispiel":
            ziel = ordner / "index.html"
        else:
            ziel = ordner / slug / "index.html"
            ziel.parent.mkdir(exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
    (ordner / "404.html").write_text(
        '<!doctype html><html lang="de"><head>'
        '<meta name="robots" content="noindex, follow"></head>'
        "<body><h1>Nicht gefunden</h1></body></html>", encoding="utf-8")
    (ordner / "robots.txt").write_text(robots, encoding="utf-8")
    (ordner / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def _regeln(befunde: list[Befund]) -> set[str]:
    return {f.regel for f in befunde if f.schwere == "fehler"}


def selftest() -> int:
    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ordner = Path(tmp)
        _temp_site(ordner)
        gute, _ = pruefe_site(ordner)
        if _regeln(gute):
            fehler.append("saubere Testseite wird beanstandet: "
                          + ", ".join(sorted(_regeln(gute))))

        faelle = [
            ("M1", SAUBER.replace("<!DOCTYPE html>", "", 1), ROBOTS, SITEMAP),
            ("M2", SAUBER.replace('<html lang="de">', "<html>"), ROBOTS, SITEMAP),
            ("M3", SAUBER.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', ""), ROBOTS, SITEMAP),
            ("M4", SAUBER.replace("Ein Titel mit genau sechzig Zeichen maximal im Fenster",
                                  "Ein viel zu langer Seitentitel, der in den Suchergebnissen abgeschnitten wird"), ROBOTS, SITEMAP),
            ("M5", SAUBER.replace("Eine Seitenbeschreibung im Fenster des Website Checks: Sie nennt das Thema, bleibt konkret und ist lang genug, damit Google sie nicht abschneidet.", "Zu kurz."), ROBOTS, SITEMAP),
            ("M6", SAUBER.replace("https://franksfinanzcheck.de/beispiel/", "http://example.com/beispiel/"), ROBOTS, SITEMAP),
            ("M7", SAUBER.replace("<title>", '<meta name="generator" content="Hugo 1.2"><title>'), ROBOTS, SITEMAP),
            ("S1", SAUBER.replace("<h2>Erster Abschnitt</h2>", "<h1>Zweite H1</h1><h2>Erster Abschnitt</h2>"), ROBOTS, SITEMAP),
            ("S2", SAUBER.replace("<h2>Erster Abschnitt</h2>", "<h3>Erster Abschnitt</h3>"), ROBOTS, SITEMAP),
            ("S3", SAUBER.replace("<h2>Erster Abschnitt</h2>", '<font color="red">Alt</font><h2>Erster Abschnitt</h2>'), ROBOTS, SITEMAP),
            ("S4", SAUBER.replace('alt="Beispiel"', ""), ROBOTS, SITEMAP),
            ("S5", SAUBER.replace("<th>Spalte</th>", "<td>Spalte</td>"), ROBOTS, SITEMAP),
            ("S6", SAUBER.replace('<a href="/impressum/">Impressum</a> ', ""), ROBOTS, SITEMAP),
            ("S7", SAUBER.replace('<a href="/impressum/">', '<a href="#">'), ROBOTS, SITEMAP),
            ("S7", SAUBER.replace('<a href="/impressum/">', '<a href="#gibts-nicht">'), ROBOTS, SITEMAP),
            ("S8", SAUBER.replace("Dies ist ein lesbarer Fließtext über Fixkosten. " * 20, "Kurz."), ROBOTS, SITEMAP),
            ("T1", SAUBER.replace("<body>", "<body><frameset><frame src='/x.html'></frameset>"), ROBOTS, SITEMAP),
            ("T1", SAUBER.replace("<body>", '<body><embed src="/spiel.swf">'), ROBOTS, SITEMAP),
            ("K5", SAUBER.replace("</body>", "<p>" + os.urandom(160_000).hex() + "</p></body>"), ROBOTS, SITEMAP),
            ("T2", SAUBER.replace('<script defer src="/premium/ff-premium.js">', '<script src="/premium/ff-premium.js">'), ROBOTS, SITEMAP),
            ("T3", SAUBER.replace('<script defer src="/premium/ff-premium.js">', '<script defer src="https://cdn.fremd.de/x.js">'), ROBOTS, SITEMAP),
            ("T4", SAUBER.replace("<title>", '<link rel="stylesheet" href="/a.css"><link rel="stylesheet" href="/b.css"><link rel="stylesheet" href="/c.css"><title>'), ROBOTS, SITEMAP),
            ("K1", SAUBER, "User-agent: *\nAllow: /\n", SITEMAP),
            ("K1", SAUBER, "User-agent: *\nDisallow: /\nSitemap: https://franksfinanzcheck.de/sitemap.xml\n", SITEMAP),
            ("K1", SAUBER, "User-agent: *\nDisallow: /css/\nSitemap: https://franksfinanzcheck.de/sitemap.xml\n", SITEMAP),
            ("K2", SAUBER, ROBOTS, SITEMAP.replace("https://franksfinanzcheck.de/beispiel/", "http://example.com/beispiel/")),
            ("K3", SAUBER, ROBOTS, SITEMAP.replace('<url><loc>https://franksfinanzcheck.de/beispiel/</loc></url>', "")),
        ]
        for regel, html_text, robots, sitemap in faelle:
            for eintrag in sorted(ordner.rglob("*"), reverse=True):
                if eintrag.is_file():
                    eintrag.unlink()
                elif eintrag.is_dir():
                    eintrag.rmdir()
            _temp_site(ordner, html_text, robots, sitemap)
            fund, _ = pruefe_site(ordner)
            if regel not in _regeln(fund):
                fehler.append(f"{regel}: Sabotage nicht erkannt "
                              f"({', '.join(sorted(_regeln(fund))) or 'nichts'})")

        # M8: doppelte Metadaten über zwei Seiten hinweg.
        dup = duplikat_befunde([analysiere("a.html", SAUBER),
                                analysiere("b.html", SAUBER)])
        if "M8" not in _regeln(dup):
            fehler.append("M8: doppelter Title/Description nicht erkannt")

        # Gegenprobe: <title> in SVG-Diagrammen darf den Seitentitel nicht
        # verlängern (realer Fehler in zwei Artikeln mit Chart-SVGs).
        for eintrag in sorted(ordner.rglob("*"), reverse=True):
            if eintrag.is_file():
                eintrag.unlink()
            elif eintrag.is_dir():
                eintrag.rmdir()
        _temp_site(ordner, SAUBER.replace(
            "<body>", "<body><svg><title>Diagrammtitel</title></svg>"))
        svg_fund, _ = pruefe_site(ordner)
        if "M4" in _regeln(svg_fund):
            fehler.append("SVG-<title> wird fälschlich als Seitentitel gezählt")

        # K4: 404 fehlt.
        (ordner / "404.html").unlink()
        k4, _ = pruefe_site(ordner)
        if "K4" not in _regeln(k4):
            fehler.append("K4: fehlende 404-Seite nicht erkannt")

    if fehler:
        print("🛑 SITECHECK-Selbsttest rot:")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ SITECHECK-Selbsttest: {len(faelle)} Sabotageproben + "
          "Gegenprobe (SVG) + saubere Seite erkannt.")
    return 0


def bericht(befunde: list[Befund], werte: dict, ordner: Path) -> str:
    hart = [f for f in befunde if f.schwere == "fehler"]
    hinweise = [f for f in befunde if f.schwere == "hinweis"]
    L = ["# SITECHECK-WACHE – vier Prüfbereiche", "",
         f"**Build:** `{ordner}` · **Stand:** gebautes HTML, kein Netz", ""]
    for k, v in werte.items():
        L.append(f"- {k.replace('_', ' ')}: **{v}**")
    L += ["", f"**Harte Funde:** {len(hart)} · **Hinweise:** {len(hinweise)}", ""]
    if not hart:
        L.append("✅ Meta, Struktur, Technik und Konfiguration im grünen Bereich.")
    else:
        for bereich in ("Meta", "Struktur", "Technik", "Konfiguration"):
            gruppe = [f for f in hart if f.bereich == bereich]
            if not gruppe:
                continue
            L += [f"## {bereich} – {len(gruppe)} Fund(e)", ""]
            for f in gruppe[:25]:
                L.append(f"- `{f.regel}` **{f.datei}** – {f.text}")
            if len(gruppe) > 25:
                L.append(f"- … {len(gruppe) - 25} weitere")
            L.append("")
    if hinweise:
        L += ["## Hinweise (kein Fehler)", ""]
        for f in hinweise[:10]:
            L.append(f"- `{f.regel}` {f.datei} – {f.text}")
        if len(hinweise) > 10:
            L.append(f"- … {len(hinweise) - 10} weitere")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sitecheck-Wache (4 Prüfbereiche)")
    ap.add_argument("--site", default=str(STANDARD_SITE),
                    help="Build-Verzeichnis (Vorgabe: public/)")
    ap.add_argument("--json", action="store_true", help="Maschinenausgabe")
    ap.add_argument("--selftest", action="store_true",
                    help="Detektor offline prüfen")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    ordner = Path(args.site).expanduser().resolve()
    try:
        befunde, werte = pruefe_site(ordner)
    except (OSError, UnicodeError) as exc:
        print(f"🛑 Sitecheck nicht prüfbar: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"site": str(ordner), "messwerte": werte,
                          "befunde": [f.als_dict() for f in befunde]},
                         ensure_ascii=False, indent=2))
    else:
        print(bericht(befunde, werte, ordner))
    return 1 if any(f.schwere == "fehler" for f in befunde) else 0


if __name__ == "__main__":
    sys.exit(main())
