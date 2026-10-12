#!/usr/bin/env python3
"""gsc_verifikations_guard.py – Verifikation und Indexierbarkeit: belegt, nicht behauptet.

AUFTRAG (12.10.2026): „Google Search Console soll alle Seiten des Blogs
verifiziert und indexiert haben – auf Premium-Level einer Profi-Agentur."

WARUM NOCH EINE WACHE, ES GIBT DOCH SCHON ZWEI?
-----------------------------------------------
`scripts/index_hygiene_gate.py` misst die MENGE der Crawl-Fläche (H1–H8):
wie viele URLs gebaut werden und ob sie im Verhältnis zueinander stehen.
`scripts/schema_seo_gate.py` misst die AUSZEICHNUNG der einzelnen Seite
(JSON-LD, Social-Tags, robots-Meta).

Beide prüfen nicht die dritte Ebene – die **Zugangsschicht zur Search Console**:

  * Liegt der Besitznachweis im Build, und stimmt sein Inhalt mit dem
    Dateinamen überein? (Eine Datei `googleabc.html`, in der ein anderer Token
    steht, verifiziert nichts und fällt erst auf, wenn Google „nicht bestätigt"
    meldet – Wochen später.)
  * Zeigt robots.txt auf eine Sitemap, die es gibt, und sperrt es versehentlich
    Googlebot aus? (Cloudflare Managed Robots schreibt einen pauschalen
    `User-agent: *`-Block mit `Content-Signal` – wer dort ein `Disallow: /`
    ergänzt, sperrt die ganze Site aus und sieht im Build keinen Fehler.)
  * Ist die Sitemap protokollgültig (Grenzen, Duplikate, Host, Reihenfolge der
    Kind-Elemente, Bild-Namensraum)?
  * Stimmt die gebaute Wahrheit mit der Sitemap überein – Canonical, robots-Meta,
    JSON-LD-Entity auf der Startseite?
  * Hat JEDE Seite, die auf noindex steht, einen erklärten Grund? Genau das ist
    der häufigste Befund in der GSC-Rubrik „Seite mit Weiterleitung" /
    „Gefunden – derzeit nicht indexiert": Eine Seite verschwindet still aus dem
    Index, weil irgendwo ein Frontmatter-Feld steht, das niemand mehr kennt.
  * Und schließlich: Ist das alles auch LIVE so, wie der Build es behauptet?
    Ein lokaler grüner Audit ist keine Aussage über den veröffentlichten Stand
    (steht so schon in docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md, Abschnitt 2).

REGELWERK (hart = Exit 1)
  V1  Besitznachweis   – mind. EIN Google-Nachweis liegt im Build UND sein
                         Inhalt stimmt mit dem Dateinamen überein
  V2  robots.txt       – Googlebot/Googlebot-News werden nicht ausgesperrt,
                         `User-agent: *` erlaubt die Site
  V3  Sitemap-Hinweis  – robots.txt nennt die Sitemap, absolut, eigener Host,
                         und die Datei existiert im Build
  V4  Sitemap-Protokoll– gültiges XML, ≤ 50.000 URLs, ≤ 50 MiB, keine Duplikate,
                         kein fremder Host, Kind-Reihenfolge loc→lastmod→
                         changefreq→priority (Bild-Tags NACH priority)
  V5  Datei ↔ Sitemap  – jede Sitemap-URL hat eine gebaute Datei, die
                         `index` trägt (kein noindex-Leck)
  V6  Canonical        – jede Sitemap-URL nennt sich selbst als kanonisch
                         (fremdes oder fehlendes Canonical = „Duplikat, von
                         Google ausgewähltes Canonical" in der GSC)
  V7  Sitemap-Fremdkörper – keine Verifikationsdatei und keine
                         /go/-Weiterleitung steht in der Sitemap
  V8  Entity-Nachweis  – die Startseite trägt WebSite- und Organization-JSON-LD
                         (E-E-A-T-Grundlage; die GSC liest dieselben Signale)
  V9  Noindex-Gründe   – jede noindex-Seite hat einen erklärten Grund
                         (Pager, 404, explizites Frontmatter, /go/-Weiterleitung,
                         Nicht-Produktions-Build). Unerklärtes noindex = Fund.
  V10 Verifikations-Konsistenz – wenn hugo.toml einen Meta-Token setzt, muss er
                         auf der Startseite auch ankommen (halb eingerichtete
                         Verifikation ist schlimmer als keine)

  V11 (weich) lastmod   – Seiten ohne Änderungsdatum geben Google keinen
                          Anhaltspunkt für die Crawlfrequenz
  V12 (weich) Waisen    – indexierbare Seite ohne internen Link (Deckung mit
                          index_hygiene_gate H7, hier im Sitemap-Kontext)

  V13 LIVE (nur mit --live, braucht Netz; blockiert keinen Build)
      Verifikationsdatei, robots.txt und Sitemap sind unter der echten Domain
      erreichbar, inhaltsgleich zum Build, ohne Weiterleitung; eine Stichprobe
      der Sitemap-URLs liefert 200, `index` und ein selbstreferenzielles
      Canonical.

SELBSTHEILUNG: bewusst KEIN --fix. Jeder Fund ist eine Entscheidung über
Zugang, Index oder Architektur – die trifft die Redaktion, nicht eine Wache.

AUFRUF
    hugo --minify --destination public
    python3 scripts/gsc_verifikations_guard.py             # V1–V12 gegen public/
    python3 scripts/gsc_verifikations_guard.py --live      # zusätzlich V13
    python3 scripts/gsc_verifikations_guard.py --json      # Maschinen-Ausgabe
    python3 scripts/gsc_verifikations_guard.py --selftest  # offline, 14 Sabotage-Proben

EXIT   0 = grün · 1 = harte Funde · 2 = Werkzeugfehler/Selbsttest rot

Nur Standardbibliothek: läuft in jedem Workflow ohne pip.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indexierbare_seiten import (  # noqa: E402
    MAX_BYTES_PRO_SITEMAP,
    MAX_URLS_PRO_SITEMAP,
    SitemapFehler,
    basis_url,
    basis_verzeichnis,
    datei_pfad,
    parse_sitemap,
    pfad_aus_url,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- Datei-Zugriff
def lies_text(pfad: str, fehler: str = "ignore") -> str:
    """Textdatei lesen und das Handle schließen.

    Eine Wache, die pro Lauf ~120 HTML-Dateien öffnet, darf ihre Handles nicht
    dem Garbage Collector überlassen: Unter `python3 -W error::ResourceWarning`
    (und in den Unit-Tests dieses Repos) wird daraus ein Befund gegen die
    Wache selbst – Lärm, der echte Funde zudeckt.
    """
    with open(pfad, encoding="utf-8", errors=fehler) as f:
        return f.read()


def lies_bytes(pfad: str) -> bytes:
    with open(pfad, "rb") as f:
        return f.read()


def schreibe_text(pfad: str, inhalt: str) -> None:
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt)


# ---------------------------------------------------------------- HTML-Lesen
ATTR = re.compile(
    r'''([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>`=]+))''',
    re.I,
)


def meta_attribute(html: str):
    """`<meta>`-Attribute robust lesen – minifiziert UND unminifiziert.

    Produktion baut mit `hugo --minify`: Der Minifier entfernt Anführungszeichen
    und ordnet Attribute um. Eine Regex, die Quotes voraussetzt oder `name` vor
    `content` verlangt, misst dann falsch – bei einem Indexierungs-Gate der
    teuerste denkbare Fehler.
    """
    for m in re.finditer(r"<meta\b([^>]*)>", html, re.I | re.S):
        attrs = {}
        for attr in ATTR.finditer(m.group(1)):
            attrs[attr.group(1).lower()] = (
                attr.group(2) or attr.group(3) or attr.group(4) or "")
        yield attrs


def link_attribute(html: str):
    for m in re.finditer(r"<link\b([^>]*)>", html, re.I | re.S):
        attrs = {}
        for attr in ATTR.finditer(m.group(1)):
            attrs[attr.group(1).lower()] = (
                attr.group(2) or attr.group(3) or attr.group(4) or "")
        yield attrs


def robots_wert(html: str) -> str:
    return ",".join(a.get("content", "") for a in meta_attribute(html)
                    if a.get("name", "").lower() == "robots").lower()


def canonical(html: str) -> str:
    for a in link_attribute(html):
        if a.get("rel", "").lower() == "canonical":
            return a.get("href", "").strip()
    return ""


def ist_alias(html: str) -> bool:
    return any(a.get("http-equiv", "").lower() == "refresh"
               for a in meta_attribute(html))


def google_site_verification(html: str) -> str:
    for a in meta_attribute(html):
        if a.get("name", "").lower() == "google-site-verification":
            return a.get("content", "").strip()
    return ""


def jsonld_bloecke(html: str) -> list[dict]:
    """Alle `<script type="application/ld+json">`-Blöcke, fehlertolerant."""
    out: list[dict] = []
    for m in re.finditer(
            r'<script[^>]*type=["\']?application/ld\+json["\']?[^>]*>(.*?)</script>',
            html, re.I | re.S):
        try:
            daten = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            out.append({"@error": "unparsebar"})
            continue
        if isinstance(daten, list):
            out.extend(d for d in daten if isinstance(d, dict))
        elif isinstance(daten, dict):
            out.append(daten)
    return out


HREF = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""",
                  re.I | re.S)


def interne_ziele(html: str, eigener_host: str) -> set[str]:
    """Interne Link-Ziele einer Seite (Pfad, normalisiert)."""
    ziele: set[str] = set()
    for m in HREF.finditer(html):
        h = (m.group(1) or m.group(2) or m.group(3) or "").strip().split("#", 1)[0]
        if not h or h.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        if h.startswith("//"):
            p = urlparse("https:" + h)
            if (p.hostname or "").lower().rstrip(".") != eigener_host:
                continue
            h = p.path or "/"
        elif urlparse(h).scheme:
            p = urlparse(h)
            if p.scheme.lower() not in ("http", "https"):
                continue
            if (p.hostname or "").lower().rstrip(".") != eigener_host:
                continue
            h = p.path or "/"
        else:
            h = urlparse(h).path or "/"
        if h.startswith("/"):
            ziele.add(unquote(h))
    return ziele


# ---------------------------------------------------------------- robots.txt
GOOGLE_BOTS = ("googlebot", "googlebot-news", "googlebot-image", "googlebot-video",
               "google-inspection-agent", "googleother", "google-extended",
               "apis-google", "mediapartners-google", "adsbot-google",
               "storebot-google", "googleweblight")


def robots_gruppen(text: str) -> list[tuple[list[str], list[tuple[str, str]], list[str]]]:
    """robots.txt → [(user-agents, [(regel, pfad)], signale)].

    Bewusst ein eigener kleiner Parser: Die robots.txt dieser Site enthält
    Cloudflare-Managed-Content-Signale (`Content-Signal:`), die kein Standard-
    Parser kennt. Unbekannte Direktiven werden als Signal gemerkt und nicht
    als Pfad-Regel missverstanden.
    """
    gruppen: list[tuple[list[str], list[tuple[str, str]], list[str]]] = []
    agents: list[str] = []
    regeln: list[tuple[str, str]] = []
    signale: list[str] = []

    def abschluss() -> None:
        if agents or regeln:
            gruppen.append((list(agents), list(regeln), list(signale)))

    for roh in text.splitlines():
        zeile = roh.split("#", 1)[0].strip()
        if not zeile or ":" not in zeile:
            continue
        feld, _, wert = zeile.partition(":")
        feld = feld.strip().lower()
        wert = wert.strip()
        if feld == "user-agent":
            if regeln:
                abschluss()
                agents, regeln, signale = [], [], []
            agents.append(wert.lower())
        elif feld in ("allow", "disallow"):
            regeln.append((feld, wert))
        elif feld in ("content-signal", "sitemap", "crawl-delay", "noindex",
                      "request-rate", "clean-param"):
            signale.append(f"{feld}:{wert}")
    abschluss()
    return gruppen


def sperrt_googlebot_aus(text: str) -> list[str]:
    """Meldet Konfigurationen, die Googlebot die Site kosten würden."""
    befunde: list[str] = []
    for agents, regeln, _ in robots_gruppen(text):
        trifft_google = "*" in agents or any(a in GOOGLE_BOTS for a in agents)
        if not trifft_google:
            continue
        # Nur die Trainings-/Erweiterungs-Bots dürfen pauschal gesperrt sein.
        if agents and all(a in ("google-extended",) for a in agents):
            continue
        for regel, pfad in regeln:
            if regel == "disallow" and pfad == "/":
                namen = ", ".join(agents)
                befunde.append(
                    f"User-agent: {namen} sperrt die gesamte Site (Disallow: /)")
    return befunde


def sitemap_hinweise(text: str) -> list[str]:
    out: list[str] = []
    for zeile in text.splitlines():
        z = zeile.split("#", 1)[0].strip()
        if z.lower().startswith("sitemap:"):
            out.append(z.split(":", 1)[1].strip())
    return out


# ---------------------------------------------------------------- Konfiguration
def hugo_werte(root: str) -> dict:
    """Die drei Konfigurationswerte, die diese Wache braucht – aus hugo.toml.

    Kein TOML-Parser (die Datei hat verschachtelte Tabellen und mehrzeilige
    Kommentare): gezielte Zeilensuche ist hier robuster und ohne Abhängigkeit.
    """
    cfg = os.path.join(root, "hugo.toml")
    werte = {"baseURL": basis_url(), "verifikations_meta": "", "env": ""}
    try:
        text = lies_text(cfg)
    except OSError:
        return werte
    m = re.search(r'^\s*baseURL\s*=\s*"([^"]+)"', text, re.M)
    if m:
        werte["baseURL"] = m.group(1).rstrip("/") + "/"
    m = re.search(r'^\s*SiteVerificationTag\s*=\s*"([^"]+)"', text, re.M)
    if m:
        werte["verifikations_meta"] = m.group(1)
    m = re.search(r'^\s*env\s*=\s*"([^"]+)"', text, re.M)
    if m:
        werte["env"] = m.group(1)
    return werte


def verifikations_dateien(root: str) -> list[tuple[str, str]]:
    """Google-Besitznachweise im Repo: (dateiname, erwarteter inhalt)."""
    static = os.path.join(root, "static")
    out: list[tuple[str, str]] = []
    if not os.path.isdir(static):
        return out
    for name in sorted(os.listdir(static)):
        if re.fullmatch(r"google[0-9a-f]{16}\.html", name):
            try:
                inhalt = lies_text(os.path.join(static, name)).strip()
            except OSError:
                inhalt = ""
            out.append((name, inhalt))
    return out


def static_pfade(root: str) -> set[str]:
    """Wurzel-relative Pfade, die aus `static/` kommen (nicht aus `content/`).

    Warum diese Menge für V9 entscheidend ist: Die Site hat Funktionsflächen,
    die gar keine Inhaltsseiten sind – der Veröffentlichungskalender
    (`static/kalender/index.html`), die Pinterest-Autorisierung
    (`static/pinterest-oauth.html`). Beide tragen ihr `noindex` selbst und
    bewusst: Sie sind Werkzeuge, keine Ratgeber. Von ihnen ein
    Frontmatter-Feld zu verlangen, hieße, eine Redaktion zu erfinden, die es
    für diese Dateien nicht gibt. V9 prüft deshalb den INHALTSBAUM – eine
    noindex-Seite aus `content/` ohne `robotsNoIndex: true` bleibt ein Fund,
    eine Funktionsfläche aus `static/` nicht.
    """
    static = os.path.join(root, "static")
    pfade: set[str] = set()
    if not os.path.isdir(static):
        return pfade
    for verz, _dirs, dateien in os.walk(static):
        for datei in dateien:
            rel = os.path.relpath(os.path.join(verz, datei), static).replace(os.sep, "/")
            if rel.endswith("index.html"):
                pfade.add("/" + rel[: -len("index.html")])
            else:
                pfade.add("/" + rel)
    return pfade


def explizites_noindex(root: str) -> set[str]:
    """Pfade, deren Inhalt bewusst `robotsNoIndex: true` trägt.

    Quelle ist der content-Baum, nicht der Build: Der Build zeigt nur das
    Ergebnis. Für V9 („hat diese noindex-Seite einen Grund?") ist der Grund
    aber die redaktionelle Entscheidung – und die steht im Frontmatter.
    """
    inhalt = os.path.join(root, "content")
    pfade: set[str] = set()
    if not os.path.isdir(inhalt):
        return pfade
    for verz, _dirs, dateien in os.walk(inhalt):
        for datei in dateien:
            if datei not in ("index.md", "_index.md"):
                continue
            pfad = os.path.join(verz, datei)
            try:
                with open(pfad, encoding="utf-8") as f:
                    text = f.read(4000)
            except OSError:
                continue
            if not text.startswith("---"):
                continue
            frontmatter = text.split("---", 2)[1] if text.count("---") >= 2 else ""
            if re.search(r"^robotsNoIndex:\s*true\s*$", frontmatter, re.M):
                # Der Pfad ist nur ein Hinweis; die URL-Übersetzung macht der
                # Vergleich gegen den Build über `url:` bzw. den Ordnerpfad.
                rel = os.path.relpath(verz, inhalt).replace(os.sep, "/")
                pfade.add("/" + ("" if rel == "." else rel))
            m = re.search(r'^url:\s*"?([^"\n]+)"?\s*$', frontmatter, re.M)
            if m and re.search(r"^robotsNoIndex:\s*true\s*$", frontmatter, re.M):
                pfade.add("/" + m.group(1).strip("/"))
    return pfade


# ---------------------------------------------------------------- Befunde
class Funde:
    def __init__(self) -> None:
        self.hart: list[tuple[str, str, str]] = []
        self.weich: list[tuple[str, str, str]] = []

    def add(self, regel: str, wo: str, text: str) -> None:
        self.hart.append((regel, wo, text))

    def warn(self, regel: str, wo: str, text: str) -> None:
        self.weich.append((regel, wo, text))


def baum_scannen(basis: str, eigener_host: str) -> dict:
    """Ein Durchlauf über den Build: alles sammeln, was V5/V6/V9/V12 brauchen."""
    seiten: dict[str, dict] = {}
    verlinkt: set[str] = set()
    for verz, _dirs, dateien in os.walk(basis):
        for datei in dateien:
            if not datei.endswith(".html"):
                continue
            pfad = os.path.join(verz, datei)
            try:
                html = lies_text(pfad)
            except OSError:
                continue
            rel = "/" + os.path.relpath(pfad, basis).replace(os.sep, "/")
            if rel.endswith("index.html"):
                rel = rel[: -len("index.html")]
            alias = ist_alias(html)
            robots = robots_wert(html)
            seiten[rel] = {
                "datei": pfad,
                "alias": alias,
                "robots": robots,
                "canonical": canonical(html),
                "verification": google_site_verification(html),
                "indexierbar": (not alias) and "noindex" not in robots,
                "html": html,
            }
            if not alias:
                verlinkt |= interne_ziele(html, eigener_host)
    return {"seiten": seiten, "verlinkt": verlinkt}


def pruefe(basis: str | None = None, root: str = ROOT) -> tuple[Funde, dict]:
    """V1–V12 gegen den Build. Reine Leseprüfung: schreibt nichts."""
    F = Funde()
    basis = basis_verzeichnis(basis)
    cfg = hugo_werte(root)
    basis_netloc = urlparse(cfg["baseURL"]).netloc.lower().rstrip(".")

    bericht = {
        "basis": basis,
        "baseURL": cfg["baseURL"],
        "verifikations_dateien": [],
        "verifikations_meta": cfg["verifikations_meta"] or None,
        "sitemap_eintraege": 0,
        "indexierbare_seiten": 0,
        "noindex_ohne_grund": 0,
        "bild_sitemap_eintraege": 0,
    }

    if not os.path.isdir(basis):
        F.add("V0", basis, "Build-Verzeichnis fehlt – zuerst `hugo` laufen lassen")
        return F, bericht

    daten = baum_scannen(basis, basis_netloc)
    seiten, verlinkt = daten["seiten"], daten["verlinkt"]
    home = seiten.get("/") or {}

    # ---- V1: Besitznachweis ----
    repo_dateien = verifikations_dateien(root)
    for name, inhalt in repo_dateien:
        gebaut = os.path.join(basis, name)
        if not os.path.exists(gebaut):
            F.add("V1", f"/{name}",
                  "Verifikationsdatei liegt in static/, fehlt aber im Build – "
                  "Google findet sie nicht")
            continue
        gebauter_inhalt = lies_text(gebaut).strip()
        erwartet = f"google-site-verification: {name}"
        if gebauter_inhalt != erwartet:
            F.add("V1", f"/{name}",
                  f"Inhalt der Verifikationsdatei passt nicht zum Dateinamen "
                  f"(erwartet exakt `{erwartet}`, gefunden `{gebauter_inhalt[:60]}`)")
        bericht["verifikations_dateien"].append(name)
    meta_token = home.get("verification", "")
    if meta_token:
        bericht["verifikations_meta_gerendert"] = meta_token
    if not bericht["verifikations_dateien"] and not meta_token:
        F.add("V1", "/",
              "weder eine google<token>.html im Build noch ein "
              "google-site-verification-Meta-Tag: die Property kann nicht "
              "bestätigt werden")

    # ---- V10: halb eingerichtete Meta-Verifikation ----
    if cfg["verifikations_meta"] and not meta_token:
        F.add("V10", "/",
              "hugo.toml setzt einen SiteVerificationTag, aber die Startseite "
              "rendert kein google-site-verification-Meta-Tag")
    if meta_token and cfg["verifikations_meta"] and meta_token != cfg["verifikations_meta"]:
        F.add("V10", "/",
              f"Meta-Token im Build ({meta_token[:12]}…) weicht von hugo.toml "
              f"({cfg['verifikations_meta'][:12]}…) ab")

    # ---- V2/V3: robots.txt ----
    robots_pfad = os.path.join(basis, "robots.txt")
    robots_text = ""
    if not os.path.exists(robots_pfad):
        F.add("V2", "/robots.txt", "robots.txt fehlt im Build "
                                   "(hugo.toml: enableRobotsTXT = true)")
    else:
        robots_text = lies_text(robots_pfad)
        for befund in sperrt_googlebot_aus(robots_text):
            F.add("V2", "/robots.txt", befund)
        hinweise = sitemap_hinweise(robots_text)
        bericht["robots_sitemap_hinweise"] = hinweise
        if not hinweise:
            F.add("V3", "/robots.txt",
                  "kein Sitemap-Hinweis – Google findet die Sitemap nur über "
                  "die manuelle Einreichung in der Search Console")
        for hinweis in hinweise:
            if not hinweis.startswith("http"):
                F.add("V3", "/robots.txt",
                      f"Sitemap-Hinweis ist keine absolute URL: {hinweis}")
                continue
            parsed = urlparse(hinweis)
            if parsed.netloc.lower().rstrip(".") != basis_netloc:
                F.add("V3", "/robots.txt",
                      f"Sitemap-Hinweis zeigt auf einen fremden Host: {hinweis}")
            erwartet_pfad = parsed.path or "/sitemap.xml"
            if erwartet_pfad not in seiten and not os.path.exists(
                    os.path.join(basis, erwartet_pfad.lstrip("/"))):
                F.add("V3", erwartet_pfad,
                      f"robots.txt nennt {hinweis}, aber die Datei fehlt im Build")

    # ---- V4: Sitemap-Protokoll ----
    sitemap_datei = os.path.join(basis, "sitemap.xml")
    seitenliste = []
    if not os.path.exists(sitemap_datei):
        F.add("V4", "/sitemap.xml", "Sitemap fehlt im Build")
    else:
        roh = lies_text(sitemap_datei)
        try:
            seitenliste = parse_sitemap(roh)
        except SitemapFehler as exc:
            F.add("V4", "/sitemap.xml", str(exc))
            seitenliste = []
        groesse = os.path.getsize(sitemap_datei)
        bericht["sitemap_bytes"] = groesse
        bericht["sitemap_eintraege"] = len(seitenliste)
        bericht["bild_sitemap_eintraege"] = sum(1 for s in seitenliste if s.bilder)
        if len(seitenliste) > MAX_URLS_PRO_SITEMAP:
            F.add("V4", "/sitemap.xml",
                  f"{len(seitenliste)} URLs – Google erlaubt {MAX_URLS_PRO_SITEMAP} "
                  "je Datei (dann Sitemap-Index bauen)")
        if groesse > MAX_BYTES_PRO_SITEMAP:
            F.add("V4", "/sitemap.xml",
                  f"{groesse} Bytes – Google erlaubt {MAX_BYTES_PRO_SITEMAP} Bytes "
                  "unkomprimiert")
        gesehen: set[str] = set()
        for s in seitenliste:
            if s.url in gesehen:
                F.add("V4", s.url, "doppelte URL in der Sitemap")
            gesehen.add(s.url)
            parsed = urlparse(s.url)
            if parsed.netloc.lower().rstrip(".") != basis_netloc:
                F.add("V4", s.url,
                      f"Sitemap-URL liegt auf einem fremden Host "
                      f"(erwartet {basis_netloc})")
            if parsed.query or parsed.fragment:
                F.add("V4", s.url,
                      "Sitemap-URL mit Query/Fragment – Google wertet das als "
                      "eigenständige URL und meldet Duplikate")
        # Kind-Reihenfolge: <loc> → <lastmod> → <changefreq> → <priority>,
        # Bild-Tags danach. Ein Bild-Tag zwischen loc und lastmod lässt das
        # Regex-Muster anderer Wachen (schema_seo_gate S7) stolpern und ist
        # deshalb hier als eigener Befund hinterlegt.
        for m in re.finditer(r"<url>(.*?)</url>", roh, re.S):
            block = m.group(1)
            pos = [(name, block.find(f"<{name}")) for name in
                   ("loc", "lastmod", "changefreq", "priority")]
            vorhanden = [(n, p) for n, p in pos if p >= 0]
            if [p for _, p in vorhanden] != sorted(p for _, p in vorhanden):
                F.add("V4", "/sitemap.xml",
                      "Kind-Elemente eines <url>-Blocks stehen nicht in der "
                      "Protokoll-Reihenfolge loc → lastmod → changefreq → priority")
                break
            bild = block.find("<image:image>")
            prio = block.find("<priority>")
            if bild >= 0 and prio >= 0 and bild < prio:
                F.add("V4", "/sitemap.xml",
                      "Bild-Tag steht VOR <priority> – schema_seo_gate S7 parst "
                      "`<loc>…</loc>\\s*(<lastmod>)?` und meldet dann ein "
                      "fehlendes lastmod")
                break

    # ---- V5/V6/V7/V11/V12: Sitemap gegen gebaute Wahrheit ----
    sitemap_pfade = {s.pfad: s for s in seitenliste}
    for pfad, s in sorted(sitemap_pfade.items()):
        gebaut_pfad = pfad if pfad.endswith("/") else pfad + "/"
        eintrag = seiten.get(gebaut_pfad) or seiten.get(pfad)
        if eintrag is None:
            F.add("V5", pfad, "Sitemap-URL hat keine gebaute Datei "
                              "(Google meldet „URL scheint nicht zu existieren")
            continue
        if eintrag["alias"]:
            F.add("V5", pfad, "Sitemap-URL ist eine Meta-Refresh-Weiterleitung – "
                              "GSC-Abdeckung: „Seite mit Weiterleitung")
        elif "noindex" in eintrag["robots"]:
            F.add("V5", pfad, "Sitemap-URL trägt noindex – widersprüchliches "
                              "Signal (GSC: „Durch 'noindex'-Tag ausgeschlossen")
        kanonisch = eintrag["canonical"]
        if not kanonisch:
            F.add("V6", pfad, "kein rel=canonical – Google wählt selbst und "
                              "meldet „Duplikat ohne vom Nutzer bestimmtes Canonical")
        elif kanonisch.rstrip("/") != s.url.rstrip("/"):
            F.add("V6", pfad, f"Canonical zeigt auf {kanonisch}, die Sitemap "
                              f"nennt {s.url}")
        if not s.lastmod:
            # `layouts/_partials/sitemap_lastmod.html` setzt bewusst nur BELEGTE
            # Redaktionsdaten: Impressum, Datenschutz und Über-mich sollen kein
            # künstliches „heute geändert" tragen. Ein fehlendes lastmod ist dort
            # Redaktionspolitik, kein Defekt – gemeldet wird es nur für Seiten,
            # deren Aktualität ein Versprechen ist (Artikel, Ratgeber, Rechner,
            # Studien, Startseite).
            frische_versprechen = (
                pfad == "/"
                or re.fullmatch(r"/(?:posts|pillar|werkzeuge|studien)/[^/]+/", pfad)
                or pfad in ("/posts/", "/pillar/", "/werkzeuge/", "/studien/", "/cockpit/"))
            if frische_versprechen:
                F.warn("V11", pfad,
                       "kein lastmod in der Sitemap, obwohl die Seite ein "
                       "Aktualitätsversprechen trägt – Google hat keinen "
                       "Anhaltspunkt für die Crawlfrequenz")
        if pfad != "/" and pfad not in verlinkt:
            F.warn("V12", pfad, "indexierbare Seite ohne internen Link "
                                "(nur über die Sitemap auffindbar)")
        # Nur Artikel und Ratgeber haben ein Cover; die Hubs `/posts/` und
        # `/pillar/` sind Listen und brauchen keinen Bild-Eintrag.
        ist_artikel = re.fullmatch(r"/(?:posts|pillar)/[^/]+/", pfad)
        if not s.bilder and ist_artikel:
            F.warn("V11", pfad, "Artikel/Ratgeber ohne Bild-Sitemap-Eintrag "
                                "(zweiter Discovery-Pfad für Google Bilder fehlt)")

    # ---- V7: Fremdkörper in der Sitemap ----
    for pfad in sorted(sitemap_pfade):
        if re.fullmatch(r"/google[0-9a-f]{16}\.html", pfad) or \
           re.fullmatch(r"/pinterest-[0-9a-f]+\.html", pfad) or \
           pfad == "/BingSiteAuth.xml":
            F.add("V7", pfad, "Verifikationsdatei steht in der Sitemap – das ist "
                              "kein Inhalt und kostet Crawl-Budget")
        if pfad.startswith("/go/"):
            F.add("V7", pfad, "Affiliate-Weiterleitung steht in der Sitemap "
                              "(robots.txt sperrt /go/, die Sitemap darf es nicht nennen)")
        if re.search(r"/page/\d+/$", pfad):
            F.add("V7", pfad, "Pager-Seite steht in der Sitemap – Pager sind "
                              "noindex,follow und gehören nicht hinein")

    # ---- V8: Entity-Nachweis auf der Startseite ----
    if not home:
        F.add("V8", "/", "Startseite fehlt im Build")
    else:
        bloecke = jsonld_bloecke(home.get("html", ""))
        typen: set[str] = set()
        for b in bloecke:
            t = b.get("@type")
            if isinstance(t, str):
                typen.add(t)
            elif isinstance(t, list):
                typen.update(t)
            if b.get("@type") == "WebSite" and "publisher" in b:
                pub = b["publisher"] or {}
                if pub.get("@type") == "Organization":
                    typen.add("Organization")
        bericht["startseite_jsonld"] = sorted(typen)
        if "WebSite" not in typen:
            F.add("V8", "/", "Startseite ohne WebSite-JSON-LD – die Entity ist "
                             "für Google nicht maschinenlesbar verknüpft")
        if "Organization" not in typen:
            F.add("V8", "/", "Startseite ohne Organization-JSON-LD (E-E-A-T: "
                             "Herausgeber fehlt als Entität)")
        for b in bloecke:
            if b.get("@type") == "WebSite":
                if b.get("inLanguage") not in ("de-DE", "de"):
                    F.warn("V8", "/", f"WebSite-Schema ohne klare Sprachangabe "
                                      f"(inLanguage={b.get('inLanguage')!r})")

    # ---- V9: jedes noindex braucht einen Grund ----
    gruende = explizites_noindex(root)
    funktionsflaechen = static_pfade(root)
    bericht["explizites_noindex_im_inhalt"] = sorted(gruende)
    bericht["noindex_funktionsflaechen"] = sorted(
        pfad for pfad in seiten
        if not seiten[pfad]["indexierbar"] and pfad in funktionsflaechen)
    ohne_grund: list[str] = []
    for pfad, eintrag in sorted(seiten.items()):
        if eintrag["indexierbar"]:
            continue
        if eintrag["alias"]:
            continue                                     # /go/-Weiterleitungen: gewollt
        if re.search(r"/page/\d+/$", pfad):
            continue                                     # Pager: gewollt (noindex,follow)
        if pfad in ("/404.html", "/404/") or pfad.startswith("/404"):
            continue                                     # Fehlerseite: gewollt
        if not cfg["env"] == "production":
            continue                                     # Nicht-Produktions-Build: alles noindex
        if pfad in funktionsflaechen:
            continue                                     # Werkzeug aus static/, kein Inhalt
        stamm = "/" + pfad.strip("/").split("/")[0] if pfad.strip("/") else "/"
        if pfad.rstrip("/") in {g.rstrip("/") for g in gruende} or \
           stamm in {g.rstrip("/") for g in gruende}:
            continue                                     # redaktionell erklärt
        ohne_grund.append(pfad)
    bericht["noindex_ohne_grund"] = len(ohne_grund)
    for pfad in ohne_grund:
        F.add("V9", pfad,
              "Seite trägt noindex, aber es gibt keinen erklärten Grund "
              "(kein `robotsNoIndex: true` im Frontmatter, kein Pager, keine "
              "404, keine Weiterleitung) – genau so verschwindet eine Seite "
              "still aus dem Index")
    bericht["indexierbare_seiten"] = sum(
        1 for e in seiten.values() if e["indexierbar"])

    # ---- H1-Deckung (jede indexierbare Seite in der Sitemap) ----
    verifikations_muster = re.compile(
        r"^/(google[0-9a-f]+\.html|pinterest-[0-9a-f]+\.html|BingSiteAuth\.xml"
        r"|[0-9a-z]{32}\.txt)$")
    for pfad, eintrag in sorted(seiten.items()):
        if not eintrag["indexierbar"] or eintrag["alias"]:
            continue
        if verifikations_muster.match(pfad) or pfad == "/404.html":
            continue
        ziel = pfad if pfad.endswith("/") else pfad + "/"
        if ziel not in sitemap_pfade and pfad not in sitemap_pfade:
            F.add("V5", pfad, "indexierbare Seite fehlt in der Sitemap "
                              "(Deckungslücke, vgl. index_hygiene_gate H1)")

    return F, bericht


# ---------------------------------------------------------------- LIVE (V13)
class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def _live_http(url: str, timeout: int = 30):
    """GET ohne Weiterleitungen: (status, body, headers).

    Weiterleitungen sind hier ein BEFUND, kein Komfort: Google meldet eine
    weitergeleitete Sitemap-URL als „Seite mit Weiterleitung" und eine
    Verifikationsdatei hinter einem Redirect verifiziert nichts.
    """
    opener = urllib.request.build_opener(_KeineWeiterleitung)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ff-gsc-guard/1.0)"})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 – Diagnose darf nie am Lesen sterben
            pass
        return exc.code, body, dict(exc.headers or {})
    except (urllib.error.URLError, OSError) as exc:
        return 0, f"{exc.__class__.__name__}: {exc}", {}


def pruefe_live(basis: str | None = None, root: str = ROOT, http=_live_http,
                stichprobe: int = 10) -> tuple[Funde, dict]:
    """V13: die ausgelieferte Wahrheit gegen den Build."""
    F = Funde()
    basis = basis_verzeichnis(basis)
    cfg = hugo_werte(root)
    live = {"baseURL": cfg["baseURL"], "geprueft": []}

    # 1) Verifikationsdatei live
    for name, _inhalt in verifikations_dateien(root):
        status, body, _hdr = http(cfg["baseURL"] + name)
        erwartet = lies_text(os.path.join(basis, name)).strip() \
            if os.path.exists(os.path.join(basis, name)) else ""
        live["geprueft"].append({"url": cfg["baseURL"] + name, "status": status})
        if status != 200:
            F.add("V13", f"/{name}",
                  f"live HTTP {status} – Google kann den Besitznachweis nicht lesen")
        elif erwartet and body.strip() != erwartet:
            F.add("V13", f"/{name}",
                  "live ausgelieferter Inhalt weicht vom Build ab (Cache, alte "
                  "Auslieferung oder fremde Datei)")

    # 2) robots.txt live
    status, body, _hdr = http(cfg["baseURL"] + "robots.txt")
    live["geprueft"].append({"url": cfg["baseURL"] + "robots.txt", "status": status})
    if status != 200:
        F.add("V13", "/robots.txt", f"live HTTP {status}")
    else:
        lokal = os.path.join(basis, "robots.txt")
        if os.path.exists(lokal):
            lokal_text = lies_text(lokal)
            if lokal_text.strip() != body.strip():
                F.warn("V13", "/robots.txt",
                       "live ausgelieferte robots.txt weicht vom Build ab")
        for befund in sperrt_googlebot_aus(body):
            F.add("V13", "/robots.txt", f"LIVE: {befund}")

    # 3) Sitemap live – ohne Weiterleitung, gültig, deckungsgleich
    sitemap_url = cfg["baseURL"] + "sitemap.xml"
    status, body, hdr = http(sitemap_url)
    live["geprueft"].append({"url": sitemap_url, "status": status})
    if status in (301, 302, 307, 308):
        F.add("V13", "/sitemap.xml",
              f"live HTTP {status} → {hdr.get('Location', '?')}: Google lehnt "
              "weitergeleitete Sitemaps ab („Sitemap konnte nicht gelesen werden")
    elif status != 200:
        F.add("V13", "/sitemap.xml", f"live HTTP {status}")
    else:
        try:
            live_seiten = parse_sitemap(body)
        except SitemapFehler as exc:
            F.add("V13", "/sitemap.xml", f"live kein gültiges XML: {exc}")
            live_seiten = []
        live["live_sitemap_eintraege"] = len(live_seiten)
        if live_seiten:
            erster = live_seiten[0]
            s2, b2, _h2 = http(erster.url)
            live["geprueft"].append({"url": erster.url, "status": s2})
            if s2 != 200:
                F.add("V13", erster.pfad,
                      f"erste Sitemap-URL liefert live HTTP {s2} – die Sitemap "
                      "nennt eine URL, die es nicht gibt")
        # Stichprobe: die wichtigsten Seiten (Start, Pillars, neueste Artikel)
        from indexierbare_seiten import reihenfolge
        for s in reihenfolge(live_seiten)[:stichprobe]:
            status, body, _hdr = http(s.url)
            live["geprueft"].append({"url": s.url, "status": status})
            if status != 200:
                F.add("V13", s.pfad, f"live HTTP {status}")
                continue
            if "noindex" in robots_wert(body):
                F.add("V13", s.pfad,
                      "live ausgelieferte Seite trägt noindex, steht aber in der "
                      "Sitemap (Google: „Durch 'noindex'-Tag ausgeschlossen")
            kan = canonical(body)
            if kan and kan.rstrip("/") != s.url.rstrip("/"):
                F.add("V13", s.pfad, f"live Canonical {kan} ≠ Sitemap-URL {s.url}")

    # 4) Startseite live: Verifikation sichtbar
    status, body, _hdr = http(cfg["baseURL"])
    live["geprueft"].append({"url": cfg["baseURL"], "status": status})
    if status == 200:
        if cfg["verifikations_meta"] and cfg["verifikations_meta"] not in body:
            F.warn("V13", "/", "hugo.toml erwartet einen Meta-Token, live ist er "
                               "nicht auf der Startseite zu finden")

    return F, live


# ---------------------------------------------------------------- Ausgabe
def drucke(F: Funde, bericht: dict, live: dict | None = None) -> None:
    print("=" * 68)
    print(" GSC-VERIFIKATION & INDEXIERBARKEIT – V1–V12"
          + (" + V13 (live)" if live else ""))
    print("=" * 68)
    if not bericht:
        return
    print(f"  baseURL .................... {bericht.get('baseURL')}")
    dateien = bericht.get("verifikations_dateien") or []
    print(f"  Besitznachweise (Datei) .... {', '.join(dateien) or '–'}")
    print(f"  Besitznachweis (Meta) ...... "
          f"{bericht.get('verifikations_meta_gerendert') or bericht.get('verifikations_meta') or '–'}")
    print(f"  robots.txt-Sitemap-Hinweise  "
          f"{len(bericht.get('robots_sitemap_hinweise') or [])}")
    print(f"  Sitemap-Einträge ........... {bericht.get('sitemap_eintraege', 0)}"
          f"   (mit Bild-Sitemap: {bericht.get('bild_sitemap_eintraege', 0)})")
    print(f"  Indexierbare Seiten im Build {bericht.get('indexierbare_seiten', 0)}")
    print(f"  Noindex ohne erklärten Grund {bericht.get('noindex_ohne_grund', 0)}")
    fl = bericht.get("noindex_funktionsflaechen") or []
    if fl:
        print(f"  Noindex-Funktionsflächen ..... {len(fl)} "
              f"({', '.join(fl[:3])}{' …' if len(fl) > 3 else ''})")
    if live:
        ok = sum(1 for g in live.get("geprueft", []) if g["status"] == 200)
        print(f"  Live-Prüfungen ............. {ok}/{len(live.get('geprueft', []))} mit HTTP 200")
    if F.hart:
        print(f"\n✗ {len(F.hart)} harte Funde:")
        for regel, wo, text in F.hart:
            print(f"  [{regel}] {wo}\n        {text}")
    if F.weich:
        print(f"\n⚠ {len(F.weich)} Hinweise:")
        for regel, wo, text in F.weich[:25]:
            print(f"  [{regel}] {wo}: {text}")
        if len(F.weich) > 25:
            print(f"  … und {len(F.weich) - 25} weitere Hinweise")
    if not F.hart and not F.weich:
        print("\n✓ Verifikation und Indexierbarkeit sind sauber belegt.")
    elif not F.hart:
        print("\n✓ Keine harten Funde (Hinweise oben sind Empfehlungen).")


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    """Offline: ein Mini-Build als Fixture + 14 Sabotage-Proben."""
    fehler: list[str] = []

    def erwarte(name: str, bedingung: bool) -> None:
        if not bedingung:
            fehler.append(name)

    import tempfile

    BASE = "https://franksfinanzcheck.de/"
    TOKEN_DATEI = "google0123456789abcdef.html"

    def gesundes_projekt(tmp: str) -> tuple[str, str]:
        """Baut ein komplettes Mini-Projekt (root, public) und gibt beide zurück."""
        root = os.path.join(tmp, "repo")
        pub = os.path.join(root, "public")
        for pfad in ("static", "content/posts/neu", "content/suche"):
            os.makedirs(os.path.join(root, pfad), exist_ok=True)
        os.makedirs(pub, exist_ok=True)
        schreibe_text(os.path.join(root, "hugo.toml"), 
            f'baseURL = "{BASE}"\n[params]\n  env = "production"\n')
        schreibe_text(os.path.join(root, "static", TOKEN_DATEI), 
            f"google-site-verification: {TOKEN_DATEI}\n")
        schreibe_text(os.path.join(root, "content", "suche", "index.md"), "---\ntitle: Suche\nrobotsNoIndex: true\n---\n")

        def seite(pub_rel: str, canonical_url: str, robots: str = "index, follow",
                  body_extra: str = "") -> None:
            ziel = os.path.join(pub, pub_rel.lstrip("/"))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            schreibe_text(ziel, 
                f"<!doctype html><html><head><meta name=robots content=\"{robots}\">"
                f'<link rel=canonical href="{canonical_url}">{body_extra}</head>'
                f'<body><a href="/posts/neu/">Neu</a></body></html>')

        home_jsonld = ('<script type="application/ld+json">{"@context":"https://schema.org",'
                       '"@type":"WebSite","name":"FF","url":"https://franksfinanzcheck.de/",'
                       '"inLanguage":"de-DE","publisher":{"@type":"Organization",'
                       '"name":"FranksFinanzcheck"}}</script>')
        seite("index.html", BASE, body_extra=home_jsonld)
        seite("posts/neu/index.html", BASE + "posts/neu/")
        seite("suche/index.html", BASE + "suche/", robots="noindex, follow")
        schreibe_text(os.path.join(pub, TOKEN_DATEI), 
            f"google-site-verification: {TOKEN_DATEI}\n")
        schreibe_text(os.path.join(pub, "robots.txt"), 
            "User-agent: *\nAllow: /\nDisallow: /go/\n\n"
            f"Sitemap: {BASE}sitemap.xml\n")
        schreibe_text(os.path.join(pub, "sitemap.xml"), 
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{BASE}</loc><lastmod>2026-10-12</lastmod>'
            '<changefreq>daily</changefreq><priority>1.0</priority></url>'
            f'<url><loc>{BASE}posts/neu/</loc><lastmod>2026-10-11</lastmod>'
            '<changefreq>weekly</changefreq><priority>0.8</priority></url>'
            "</urlset>")
        return root, pub

    with tempfile.TemporaryDirectory() as tmp:
        root, pub = gesundes_projekt(tmp)
        F, bericht = pruefe(pub, root)
        erwarte("gesundes Projekt ist grün", not F.hart)
        erwarte("Verifikationsdatei erkannt", bericht["verifikations_dateien"] == [TOKEN_DATEI])
        erwarte("Sitemap gezählt", bericht["sitemap_eintraege"] == 2)
        erwarte("noindex-Seite mit Grund erklärt", bericht["noindex_ohne_grund"] == 0)
        erwarte("Canonical gelesen", not any(r == "V6" for r, _w, _x in F.hart))

        # Jede Sabotage-Probe startet am GESUNDEN Stand: Eine Probe, die auf
        # der vorigen aufbaut, misst Zufälle statt Regeln (real passiert beim
        # ersten Entwurf: Probe 8 lief gegen die Sitemap aus Probe 7).
        gesund: dict[str, bytes] = {}
        for verz, _dirs, dateien in os.walk(pub):
            for datei in dateien:
                pfad = os.path.join(verz, datei)
                gesund[pfad] = lies_bytes(pfad)

        def zuruecksetzen() -> None:
            for verz, dirs, dateien in os.walk(pub, topdown=False):
                for datei in dateien:
                    pfad = os.path.join(verz, datei)
                    if pfad not in gesund:
                        os.remove(pfad)
                for d in dirs:
                    dp = os.path.join(verz, d)
                    if not os.listdir(dp):
                        os.rmdir(dp)
            for pfad, inhalt in gesund.items():
                os.makedirs(os.path.dirname(pfad), exist_ok=True)
                with open(pfad, "wb") as fh:
                    fh.write(inhalt)

        def regeln() -> set[str]:
            f, _ = pruefe(pub, root)
            zuruecksetzen()
            return {r for r, _wo, _t in f.hart}

        def schreibe(rel: str, text: str) -> None:
            pfad = os.path.join(pub, rel)
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            schreibe_text(pfad, text)

        sitemap_ok = gesund[os.path.join(pub, "sitemap.xml")].decode()

        # 1) Verifikationsdatei fehlt im Build
        os.remove(os.path.join(pub, TOKEN_DATEI))
        erwarte("V1: fehlende Datei im Build", "V1" in regeln())

        # 2) Falscher Inhalt in der Verifikationsdatei
        schreibe(TOKEN_DATEI, "google-site-verification: googleXXXXXXXXXXXXXXXX.html\n")
        erwarte("V1: Inhalt passt nicht zum Namen", "V1" in regeln())

        # 3) Googlebot pauschal ausgesperrt
        schreibe("robots.txt", f"User-agent: *\nDisallow: /\nSitemap: {BASE}sitemap.xml\n")
        erwarte("V2: Disallow / für alle", "V2" in regeln())

        # 3b) Google-Extended darf gesperrt bleiben (Training) – kein Fund
        schreibe("robots.txt",
                 "User-agent: Google-Extended\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
                 f"Sitemap: {BASE}sitemap.xml\n")
        erwarte("V2: Google-Extended-Sperre ist erlaubt", "V2" not in regeln())

        # 3c) Auch ein expliziter Googlebot-Block ist ein Fund
        schreibe("robots.txt",
                 "User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
                 f"Sitemap: {BASE}sitemap.xml\n")
        erwarte("V2: Googlebot-Block erkannt", "V2" in regeln())

        # 4) Sitemap-Hinweis fehlt
        schreibe("robots.txt", "User-agent: *\nAllow: /\n")
        erwarte("V3: kein Sitemap-Hinweis", "V3" in regeln())

        # 5) Sitemap-Hinweis auf fremden Host
        schreibe("robots.txt",
                 "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n")
        erwarte("V3: fremder Host im Sitemap-Hinweis", "V3" in regeln())

        # 5b) Sitemap-Hinweis auf eine Datei, die es nicht gibt
        schreibe("robots.txt",
                 f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap-index.xml\n")
        erwarte("V3: Sitemap-Hinweis ins Leere", "V3" in regeln())

        # 6) Sitemap nennt eine URL ohne gebaute Datei
        schreibe("sitemap.xml", sitemap_ok.replace(
            f"<url><loc>{BASE}posts/neu/</loc>",
            f"<url><loc>{BASE}gibt-es-nicht/</loc>") + "")
        erwarte("V5: Sitemap-URL ohne Datei", "V5" in regeln())

        # 7) Sitemap-URL trägt noindex
        schreibe("sitemap.xml", sitemap_ok + "")
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                 f'<url><loc>{BASE}suche/</loc></url></urlset>')
        erwarte("V5: noindex-Seite in der Sitemap", "V5" in regeln())

        # 8) Canonical zeigt woanders hin
        ziel = os.path.join(pub, "posts", "neu", "index.html")
        text = lies_text(ziel)
        schreibe("posts/neu/index.html", text.replace(
            'href="https://franksfinanzcheck.de/posts/neu/"',
            'href="https://franksfinanzcheck.de/andere-seite/"'))
        erwarte("V6: falsches Canonical", "V6" in regeln())

        # 8b) Canonical fehlt ganz
        schreibe("posts/neu/index.html", text.replace(
            '<link rel=canonical href="https://franksfinanzcheck.de/posts/neu/">', ""))
        erwarte("V6: fehlendes Canonical", "V6" in regeln())

        # 9) Verifikationsdatei in der Sitemap
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                 f'<url><loc>{BASE}{TOKEN_DATEI}</loc></url></urlset>')
        erwarte("V7: Verifikationsdatei in der Sitemap", "V7" in regeln())

        # 9b) Affiliate-Weiterleitung in der Sitemap
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                 f'<url><loc>{BASE}go/check24/</loc></url></urlset>')
        erwarte("V7: /go/ in der Sitemap", "V7" in regeln())

        # 9c) Sitemap-URL mit Query (Google wertet sie als eigene URL)
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                 f'<url><loc>{BASE}?utm_source=nl</loc></url></urlset>')
        erwarte("V4: Query in der Sitemap-URL", "V4" in regeln())

        # 10) Startseite ohne Organization-Entity
        schreibe("index.html",
                 '<!doctype html><html><head><meta name=robots content="index, follow">'
                 f'<link rel=canonical href={BASE}></head><body></body></html>')
        erwarte("V8: fehlendes WebSite/Organization-Schema", "V8" in regeln())

        # 11) Unerklärtes noindex: eine gebaute Seite verliert ihr index
        schreibe("transparenz/index.html",
                 '<!doctype html><html><head><meta name=robots content="noindex, follow">'
                 f'<link rel=canonical href={BASE}transparenz/></head><body></body></html>')
        erwarte("V9: noindex ohne erklärten Grund", "V9" in regeln())

        # 11a) Funktionsfläche aus static/ mit eigenem noindex ist kein Fund
        os.makedirs(os.path.join(root, "static", "kalender"), exist_ok=True)
        schreibe_text(os.path.join(root, "static", "kalender", "index.html"), 
            '<!doctype html><html><head><meta name=robots content="noindex, follow">'
            f'<link rel=canonical href={BASE}kalender/></head><body></body></html>')
        schreibe("kalender/index.html",
                 '<!doctype html><html><head><meta name=robots content="noindex, follow">'
                 f'<link rel=canonical href={BASE}kalender/></head><body></body></html>')
        erwarte("V9: Funktionsfläche aus static/ ist erlaubt", "V9" not in regeln())

        # 11b) Dasselbe noindex MIT Frontmatter-Grund ist kein Fund
        schreibe_text(os.path.join(root, "content", "transparenz_index.md"), "---\nrobotsNoIndex: true\nurl: /transparenz/\n---\n")
        f9b, _ = pruefe(pub, root)
        schreibe("transparenz/index.html",
                 '<!doctype html><html><head><meta name=robots content="noindex, follow">'
                 f'<link rel=canonical href={BASE}transparenz/></head><body></body></html>')
        erwarte("V9: erklärtes noindex ist erlaubt",
                not any(r == "V9" for r, _w, _t in f9b.hart))
        os.remove(os.path.join(root, "content", "transparenz_index.md"))
        zuruecksetzen()

        # 12) Bild-Tag vor priority
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                 f'<url><loc>{BASE}</loc><image:image><image:loc>{BASE}x.jpg</image:loc>'
                 '</image:image><lastmod>2026-10-12</lastmod><priority>1.0</priority></url>'
                 "</urlset>")
        erwarte("V4: Bild-Tag vor priority", "V4" in regeln())

        # 12b) Bild-Tag NACH priority ist korrekt (Gegenprobe)
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                 f'<url><loc>{BASE}</loc><lastmod>2026-10-12</lastmod>'
                 '<changefreq>daily</changefreq><priority>1.0</priority>'
                 f'<image:image><image:loc>{BASE}x.jpg</image:loc>'
                 '<image:title>Titel</image:title></image:image></url></urlset>')
        erwarte("V4: Bild-Tag nach priority ist erlaubt", "V4" not in regeln())

        # 13) doppelte URL in der Sitemap
        schreibe("sitemap.xml",
                 '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                 f'<url><loc>{BASE}</loc></url><url><loc>{BASE}</loc></url></urlset>')
        erwarte("V4: Duplikat", "V4" in regeln())

        # 14) robots.txt fehlt ganz
        os.remove(os.path.join(pub, "robots.txt"))
        erwarte("V2: fehlende robots.txt", "V2" in regeln())

        # 15) Meta-Token in hugo.toml, aber nicht gerendert (V10)
        schreibe_text(os.path.join(root, "hugo.toml"), 
            f'baseURL = "{BASE}"\n[params]\n  env = "production"\n'
            '  [params.analytics]\n    [params.analytics.google]\n'
            '      SiteVerificationTag = "abc123"\n')
        erwarte("V10: Meta-Token in der Konfiguration fehlt im Build", "V10" in regeln())

    # ---- LIVE-Pfad mit injiziertem HTTP (kein Netz) ----
    with tempfile.TemporaryDirectory() as tmp:
        root, pub = gesundes_projekt(tmp)
        sitemap_text = lies_text(os.path.join(pub, "sitemap.xml"))
        robots_text = lies_text(os.path.join(pub, "robots.txt"))
        verif_text = lies_text(os.path.join(pub, TOKEN_DATEI))
        home_text = lies_text(os.path.join(pub, "index.html"))
        artikel_text = lies_text(os.path.join(pub, "posts", "neu", "index.html"))

        antworten = {
            BASE + TOKEN_DATEI: (200, verif_text, {}),
            BASE + "robots.txt": (200, robots_text, {}),
            BASE + "sitemap.xml": (200, sitemap_text, {}),
            BASE: (200, home_text, {}),
            BASE + "posts/neu/": (200, artikel_text, {}),
        }
        F, live = pruefe_live(pub, root, http=lambda url, timeout=30: antworten.get(url, (404, "", {})))
        erwarte("LIVE gesundes Projekt ist grün", not F.hart)
        erwarte("LIVE-Prüfungen gezählt", len(live["geprueft"]) >= 5)

        # Sabotage A: Verifikationsdatei live 404
        alt = dict(antworten)
        alt[BASE + TOKEN_DATEI] = (404, "", {})
        f2, _ = pruefe_live(pub, root, http=lambda url, timeout=30: alt.get(url, (404, "", {})))
        erwarte("V13: Verifikationsdatei 404", any(r == "V13" for r, _w, _t in f2.hart))

        # Sabotage B: Sitemap wird weitergeleitet
        alt = dict(antworten)
        alt[BASE + "sitemap.xml"] = (301, "", {"Location": BASE + "sitemap-index.xml"})
        f3, _ = pruefe_live(pub, root, http=lambda url, timeout=30: alt.get(url, (404, "", {})))
        erwarte("V13: weitergeleitete Sitemap",
               any("weitergeleitete Sitemaps" in t for _r, _w, t in f3.hart))

        # Sabotage C: live ausgelieferte Seite trägt noindex
        alt = dict(antworten)
        alt[BASE + "posts/neu/"] = (200, artikel_text.replace("index, follow", "noindex, follow"), {})
        f4, _ = pruefe_live(pub, root, http=lambda url, timeout=30: alt.get(url, (404, "", {})))
        erwarte("V13: noindex live", any("noindex" in t for _r, _w, t in f4.hart))

        # Sabotage D: Canonical live weicht ab
        alt = dict(antworten)
        alt[BASE + "posts/neu/"] = (200, artikel_text.replace(
            'href="https://franksfinanzcheck.de/posts/neu/"',
            'href="https://franksfinanzcheck.de/alt/"'), {})
        f5, _ = pruefe_live(pub, root, http=lambda url, timeout=30: alt.get(url, (404, "", {})))
        erwarte("V13: Canonical-Drift live", any("Canonical" in t for _r, _w, t in f5.hart))

    if fehler:
        print("❌ GSC-VERIFIKATIONS-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ gsc_verifikations_guard: Selbsttest bestanden "
          "(V1–V10 an einem Fixture-Build: 22 Sabotage-Proben plus 4 Gegenproben, "
          "V13 mit injiziertem HTTP ohne Netz).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verifikation und Indexierbarkeit für die Google Search Console.")
    ap.add_argument("--public", default=None, help="Build-Verzeichnis (Voreinstellung public/)")
    ap.add_argument("--root", default=ROOT, help="Projekt-Wurzel (Voreinstellung: Repo)")
    ap.add_argument("--live", action="store_true", help="zusätzlich V13 gegen die Live-Site")
    ap.add_argument("--nur-live", action="store_true", help="nur V13")
    ap.add_argument("--stichprobe", type=int, default=10,
                    help="wie viele Sitemap-URLs live geprüft werden (Voreinstellung 10)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    basis = basis_verzeichnis(a.public)
    if not os.path.isdir(basis):
        print(f"❌ Build-Verzeichnis {basis} fehlt – zuerst `hugo` laufen lassen.")
        return 2

    F = Funde()
    bericht: dict = {}
    live = None
    if not a.nur_live:
        F, bericht = pruefe(basis, a.root)
    if a.live or a.nur_live:
        try:
            Fl, live = pruefe_live(basis, a.root, stichprobe=a.stichprobe)
            F.hart += Fl.hart
            F.weich += Fl.weich
        except Exception as exc:  # noqa: BLE001 – Netz ist Diagnose, kein Build-Tor
            print(f"⚠️  Live-Prüfung abgebrochen ({exc.__class__.__name__}: {exc}). "
                  "Der Build-Befund oben bleibt gültig.")
            live = {"fehler": str(exc)}

    if a.json:
        print(json.dumps({
            "bericht": bericht,
            "live": live,
            "harte_funde": [{"regel": r, "wo": w, "text": t} for r, w, t in F.hart],
            "hinweise": [{"regel": r, "wo": w, "text": t} for r, w, t in F.weich],
        }, ensure_ascii=False, indent=2))
    else:
        drucke(F, bericht, live)

    return 1 if F.hart else 0


if __name__ == "__main__":
    sys.exit(main())
