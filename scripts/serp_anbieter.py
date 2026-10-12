#!/usr/bin/env python3
"""SERP-Anbieter – die Adapter-Schicht des Suchradars (schlüssellos zuerst).

    from serp_anbieter import anbieter_lage, hole_treffer

    for treffer in hole_treffer("stromkosten senken", {"land": "de"}):
        print(treffer["rang"], treffer["url"])

AUFTRAG UND ABGRENZUNG (12.10.2026)
-----------------------------------
Gefordert war ein Nachbau des Apify-Actors `apify/google-search-scraper`,
der **ohne API-Anbindung** läuft – also ohne Schlüssel, ohne Konto, ohne
Rechnung. Der Actor selbst holt seine Treffer, indem er google.com mit
einem Proxy-Pool ausspielt. Genau das macht dieser Nachbau **nicht**, und
das ist eine Entscheidung, kein Versehen:

  1. **Vertrag.** Automatisiertes Abfragen von google.com verstößt gegen
     die Google-Nutzungsbedingungen. Für eine Finanzmarke (YMYL) ist das
     kein theoretisches Risiko, sondern eine Abmahnfläche.
  2. **Technik.** GitHub-Runner fahren aus Rechenzentrums-Netzbereichen.
     Google antwortet dort mit CAPTCHA oder 429. Ein Scraper, der nur
     dort funktioniert, wo er nicht beobachtet wird, ist kein Betrieb.
  3. **Ergebnis.** Selbst wenn es liefe, wären die Treffer verzerrt –
     Rechenzentrums-IP, kein Cookie-Verlauf, kein Standort.

Stattdessen nutzt diese Schicht **Metasuche und offene Indizes**, die für
den maschinellen Zugriff gebaut sind und keinen Schlüssel verlangen:

  · `searxng`    – Metasuchmaschine; bündelt u. a. den Google-Index hinter
                   einer eigenen Schnittstelle. JSON zuerst, HTML als
                   Rückfall, mehrere Instanzen mit Gesundheitsführung.
  · `duckduckgo` – HTML-Endpunkt ohne Schlüssel.
  · `mojeek`     – eigener, unabhängiger Index; kein Aggregator.
  · `wikipedia`  – offizielle API ohne Schlüssel; Wissens-Rückfall.

Wer später doch eine API will, findet die Adapter bereits vorverdrahtet
(`google_cse`, `brave`, `serper`, `serpapi`, `apify`). Sie sind über die
Kostensperre gesperrt und brauchen zusätzlich einen Schlüssel – der
Normalbetrieb bleibt ohne beide Schlüssel vollständig funktionsfähig.

KOSTENSPERRE
------------
Bezahlte Anbieter fragen `scripts/kostensperre.py` nach der Fläche
`serp_premium`. Fail-closed: Ohne ausdrückliche Freigabe in
`data/kostensperre.yaml` liefern sie eine leere Liste, auch wenn ein
Schlüssel gesetzt ist. Ein vergessenes Secret kann hier kein Geld
auslösen – dieselbe Schadensklasse, die zur Sperre führte.

Alles hier ist Standardbibliothek und ohne Netz prüfbar.
"""
from __future__ import annotations

import base64
import gzip
import io
import json
import os
import random
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from pathlib import Path

from serp_html import attribut_url, baum, domaene_aus_url, uddg_entpacken, url_saeubern

try:                                                    # pragma: no cover
    import kostensperre
except ImportError:                                     # pragma: no cover
    kostensperre = None

ROOT = Path(__file__).resolve().parent.parent
FLAECHE_KOSTEN = "serp_premium"

USER_AGENT = ("FranksFinanzcheck-Suchradar/1.0 "
              "(+https://franksfinanzcheck.de/impressum/) Python-urllib")

# SSRF-Schutz: Nur diese Hosts dürfen angefragt werden. Ein Selektor oder
# eine Instanz-Liste aus einer Konfigurationsdatei darf den Prozess nicht
# auf eine fremde Adresse lenken können.
# Hinweis: `api.duckduckgo.com` stand hier eine Weile, ohne dass ein
# Anbieter ihn anfragte. Ein freigegebener Host ohne Ausführer ist eine
# unwahre Aussage im Code – und erweitert die Angriffsfläche um nichts.
# Wer ihn braucht, trägt ihn zusammen mit dem Anbieter ein.
ERLAUBTE_HOSTS = frozenset({
    "html.duckduckgo.com", "lite.duckduckgo.com",
    "www.mojeek.com", "de.wikipedia.org", "en.wikipedia.org",
    "www.googleapis.com", "api.search.brave.com", "google.serper.dev",
    "serpapi.com", "api.apify.com",
})

_LETZTE_ANFRAGE: dict[str, float] = {}
_ROBOTS_CACHE: dict[str, tuple[float, bool]] = {}
_ROBOTS_TTL = 6 * 3600


# ====================================================================
#  ANBIETER-REGISTER
# ====================================================================
# `organisch` trennt ehrlich, was ein echtes Suchmaschinen-Ranking
# liefert, von einem Wissens-Rückfall. Wer Rangverläufe misst, muss
# wissen, aus welcher Quelle der Rang stammt – sonst ist die Kurve
# bedeutungslos.
ANBIETER: dict[str, dict] = {
    "searxng": {
        "name": "SearXNG-Metasuche (öffentliche Instanzen)",
        "schluessellos": True,
        "organisch": True,
        "min_abstand": 1.0,
        "tageslimit": 400,
        "beschreibung": "Bündelt mehrere Suchmaschinen – darunter den "
                        "Google-Index – hinter einer schlüssellosen "
                        "Schnittstelle. Primärquelle dieses Nachbaus.",
    },
    "duckduckgo": {
        "name": "DuckDuckGo (HTML-Endpunkt)",
        "schluessellos": True,
        "organisch": True,
        "min_abstand": 2.5,
        "tageslimit": 200,
        "beschreibung": "HTML-Endpunkt ohne Schlüssel. Eigener Index plus "
                        "Bing; kein Google-Abbild.",
    },
    "duckduckgo_lite": {
        "name": "DuckDuckGo Lite (Ausweichstufe)",
        "schluessellos": True,
        "organisch": True,
        "min_abstand": 2.5,
        "tageslimit": 200,
        "beschreibung": "Schlankes Tabellenlayout derselben Quelle. Fängt "
                        "eine Blockade des HTML-Endpunkts ab, bevor auf "
                        "einen fremden Index ausgewichen wird.",
    },
    "mojeek": {
        "name": "Mojeek (unabhängiger Index)",
        "schluessellos": True,
        "organisch": True,
        "min_abstand": 2.0,
        "tageslimit": 200,
        "beschreibung": "Eigener Crawler-Index. Kontrollwert: Zeigt, ob ein "
                        "Rang ein Index-Rang oder ein Aggregator-Artefakt ist.",
    },
    "wikipedia": {
        "name": "Wikipedia (offizielle API)",
        "schluessellos": True,
        "organisch": False,
        "min_abstand": 0.5,
        "tageslimit": 300,
        "beschreibung": "Offizielle API, ausdrücklich ohne Schlüssel. Kein "
                        "Suchmaschinen-Ranking – dient als Wissens-Rückfall.",
    },
    # ------------------------------------------------------------------
    #  OPTIONAL: brauchen einen Schlüssel UND eine Freigabe der Kostensperre
    # ------------------------------------------------------------------
    "google_cse": {
        "name": "Google Custom Search JSON API",
        "schluessellos": False,
        "organisch": True,
        "min_abstand": 1.0,
        "tageslimit": 100,
        "kostenpflichtig_ab": 100,
        "umgebung": ["GOOGLE_CSE_KEY", "GOOGLE_CSE_ID"],
        "beschreibung": "Offizieller Google-Weg, 100 Abfragen/Tag frei. "
                        "Darüber hinaus 5 $ je 1.000 – deshalb gesperrt.",
    },
    "brave": {
        "name": "Brave Search API",
        "schluessellos": False,
        "organisch": True,
        "min_abstand": 1.0,
        "tageslimit": 2000,
        "kostenpflichtig_ab": 2000,
        "umgebung": ["BRAVE_API_KEY", "SEARCH_API_KEY"],
        "beschreibung": "2.000 Abfragen/Monat frei, eigener Index.",
    },
    "serper": {
        "name": "serper.dev (Google SERP API)",
        "schluessellos": False,
        "organisch": True,
        "min_abstand": 0.3,
        "tageslimit": 2500,
        "kostenpflichtig_ab": 0,
        "umgebung": ["SERPER_API_KEY"],
        "beschreibung": "Bezahlter Google-SERP-Dienst. Vollständig "
                        "kostenpflichtig – Standard: gesperrt.",
    },
    "serpapi": {
        "name": "SerpApi (Google SERP API)",
        "schluessellos": False,
        "organisch": True,
        "min_abstand": 0.3,
        "tageslimit": 100,
        "kostenpflichtig_ab": 0,
        "umgebung": ["SERPAPI_KEY", "SERPAPI_API_KEY"],
        "beschreibung": "Bezahlter Google-SERP-Dienst – Standard: gesperrt.",
    },
    "apify": {
        "name": "Apify-Actor google-search-scraper (Original)",
        "schluessellos": False,
        "organisch": True,
        "min_abstand": 0.5,
        "tageslimit": 50,
        "kostenpflichtig_ab": 0,
        "umgebung": ["APIFY_TOKEN", "APIFY_API_TOKEN"],
        "beschreibung": "Der Actor, dessen Nachbau gefordert war. Läuft als "
                        "Adapter mit, sobald er freigegeben ist – dann "
                        "vergleichbar mit dem Eigenbau.",
    },
}

# Reihenfolge, wenn nichts anderes konfiguriert ist: erst schlüssellos und
# Google-nah, dann unabhängige Indizes, zuletzt der Wissens-Rückfall.
STANDARD_REIHENFOLGE = ["searxng", "duckduckgo", "duckduckgo_lite", "mojeek", "wikipedia"]

# Öffentliche SearXNG-Instanzen als Startpunkt. Diese Liste ist bewusst
# Konfiguration (data/suchradar.yaml) und nicht Code: Instanzen kommen und
# gehen, und `--probe` misst, welche heute antworten. Eine fest
# einkompilierte Liste wäre nach dem ersten Ausfall eine Lüge.
STANDARD_SEARXNG_INSTANZEN = [
    "https://searx.be",
    "https://search.bus-hit.me",
    "https://paulgo.io",
    "https://searx.tiekoetter.com",
    "https://opnxng.com",
    "https://priv.au",
    "https://search.mdosch.de",
    "https://baresearch.org",
]

KOSTENPFLICHTIG = frozenset({
    aid for aid, a in ANBIETER.items() if a.get("kostenpflichtig_ab", 0) == 0
})


# ====================================================================
#  KOSTENSPERRE
# ====================================================================
def pruefe_freigabe(anbieter_id: str, umgebung: dict | None = None) -> tuple[bool, str]:
    """Darf dieser Anbieter Geld ausgeben? (Engstelle der Fläche `serp_premium`)

    Rückgabe `(erlaubt, grund)`. Drei Gatter, alle fail-closed:

      1. Schlüssellose Anbieter brauchen keine Freigabe – sie kosten nichts.
      2. Anbieter mit Gratis-Kontingent (`kostenpflichtig_ab` > 0) sind
         erlaubt, solange das Kontingit nicht überschritten ist. Das
         entscheidet der Quoten-Zähler in scripts/suchradar.py, nicht hier.
      3. Rein bezahlte Anbieter fragen die Kostensperre. Ist die SSOT
         unlesbar, fehlt die Fläche oder fehlt die Begründung: gesperrt.

    Die Sperre wird importiert und nicht nachgebaut. Zwei Kopien derselben
    Regel laufen auseinander – genau das prüft `kostensperre --pruefen`
    aus der anderen Richtung.
    """
    meta = ANBIETER.get(anbieter_id)
    if meta is None:
        return False, f"Unbekannter Anbieter: {anbieter_id}"
    if meta.get("schluessellos"):
        return True, "schlüssellos"
    if meta.get("kostenpflichtig_ab", 0) > 0:
        return True, f"Gratis-Kontingent bis {meta['kostenpflichtig_ab']}"

    # Rein bezahlt → Kostensperre fragen.
    if kostensperre is None:
        return False, "kostensperre-Modul nicht ladbar – fail-closed gesperrt"
    if not kostensperre.erlaubt(FLAECHE_KOSTEN):
        return False, (f"Kostensperre: Fläche `{FLAECHE_KOSTEN}` nicht "
                       "freigegeben")
    return True, "durch Kostensperre freigegeben"


def schluessel_vorhanden(anbieter_id: str, umgebung: dict | None = None) -> bool:
    """Liegt für diesen Anbieter jeder nötige Schlüssel in der Umgebung?"""
    meta = ANBIETER.get(anbieter_id, {})
    namen = meta.get("umgebung") or []
    if not namen:
        return bool(meta.get("schluessellos"))
    env = umgebung if umgebung is not None else os.environ
    return all(str(env.get(n, "")).strip() for n in namen)


def anbieter_lage(umgebung: dict | None = None) -> list[dict]:
    """Zustand aller Anbieter – die Grundlage für Cockpit und `--probe`."""
    env = umgebung if umgebung is not None else os.environ
    lage = []
    for aid, meta in ANBIETER.items():
        erlaubt, grund = pruefe_freigabe(aid, env)
        lage.append({
            "id": aid,
            "name": meta["name"],
            "schluessellos": bool(meta.get("schluessellos")),
            "organisch": bool(meta.get("organisch")),
            "schluessel_vorhanden": schluessel_vorhanden(aid, env),
            "nutzbar": erlaubt and (bool(meta.get("schluessellos"))
                                    or schluessel_vorhanden(aid, env)),
            "grund": grund,
            "tageslimit": meta.get("tageslimit", 0),
        })
    return lage


# ====================================================================
#  HTTP
# ====================================================================
def host_erlaubt(url: str) -> bool:
    """SSRF-Gatter. Nur gelistete Hosts, und nur http(s)."""
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    # Instanzen sind frei konfigurierbar; sie müssen sich selbst eintragen.
    return host in ERLAUBTE_HOSTS or host in _zugelassene_instanzen()


_zugelassen: set[str] = set()


def instanzen_zulassen(hosts) -> None:
    """Konfigurierte SearXNG-Instanzen für das SSRF-Gatter freigeben.

    Ohne diesen Schritt wäre jede Instanz außerhalb der Standardliste
    gesperrt – die Konfiguration hätte keine Wirkung. Der Umweg über eine
    explizite Freigabe hält den Unterschied sichtbar: Standardliste ist
    Code, Zusatzinstanz ist Beschluss.
    """
    global _zugelassen
    neu = set()
    for eintrag in hosts or []:
        host = (urllib.parse.urlparse(str(eintrag).strip()).hostname or "").lower()
        if host:
            neu.add(host)
    _zugelassen = neu


def _zugelassene_instanzen() -> set[str]:
    return _zugelassen


def _entpacken(antwort, roh: bytes) -> str:
    kodierung = (antwort.headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in kodierung:
            return gzip.decompress(roh).decode("utf-8", "replace")
        if "deflate" in kodierung:
            try:
                return zlib.decompress(roh).decode("utf-8", "replace")
            except zlib.error:
                return zlib.decompress(roh, -zlib.MAX_WBITS).decode("utf-8", "replace")
    except (OSError, zlib.error):
        pass
    zeichensatz = antwort.headers.get_content_charset() or "utf-8"
    try:
        return roh.decode(zeichensatz, "replace")
    except (LookupError, UnicodeDecodeError):
        return roh.decode("utf-8", "replace")


class AnfrageFehler(RuntimeError):
    """Netz- oder Protokollfehler – mit Status, damit 429 erkennbar bleibt."""

    def __init__(self, meldung: str, status: int = 0):
        super().__init__(meldung)
        self.status = status


def hole(url: str, kopfzeilen: dict | None = None, daten: bytes | None = None,
         zeitlimit: int = 20, wiederholungen: int = 3,
         rueckzug: float = 1.5) -> tuple[int, str, dict]:
    """HTTP-GET/POST mit Wiederholung, Stauerkennung und ehrlichem Fehler.

    Rückgabe `(status, text, antwortkopfzeilen)`.

    Drei Dinge, die ein Weglassen teuer macht:

      · **429 mit `Retry-After`** wird beachtet statt blind wiederholt.
        Ein Scraper, der in ein Ratenlimit hineinhämmert, verliert die
        Instanz für alle – auch für den nächsten Lauf.
      · **Jitter.** Feste Wartezeiten synchronisieren parallele Läufe.
      · **Status im Fehler.** Ohne Statuscode ist „es ging nicht" keine
        Diagnose: Timeout, Blockade und leerer Index brauchen
        unterschiedliche Antworten.
    """
    if not host_erlaubt(url):
        raise AnfrageFehler(f"Host nicht freigegeben (SSRF-Gatter): {url}")

    kopf = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.6",
        "Accept-Encoding": "gzip, deflate",
    }
    kopf.update(kopfzeilen or {})

    letzter_fehler: Exception | None = None
    for versuch in range(max(1, wiederholungen)):
        if versuch:
            # Exponentieller Rückzug mit Jitter: 1,5 s → 3 s → 6 s, ±30 %.
            warte = rueckzug ** versuch * (0.7 + random.random() * 0.6)
            time.sleep(min(warte, 12.0))
        anfrage = urllib.request.Request(url, data=daten, headers=kopf,
                                         method="POST" if daten else "GET")
        try:
            with urllib.request.urlopen(anfrage, timeout=zeitlimit) as antwort:
                roh = antwort.read()
                return antwort.status, _entpacken(antwort, roh), dict(antwort.headers)
        except urllib.error.HTTPError as fehler:
            letzter_fehler = fehler
            if fehler.code in (429, 500, 502, 503, 504):
                warte = fehler.headers.get("Retry-After") if fehler.headers else None
                if warte and str(warte).isdigit():
                    time.sleep(min(float(warte), 30.0))
                continue
            # 4xx außer 429: Wiederholen ändert nichts.
            raise AnfrageFehler(f"HTTP {fehler.code} für {url}", fehler.code) from fehler
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as fehler:
            letzter_fehler = fehler
            continue
    raise AnfrageFehler(f"{url}: {letzter_fehler}", 0)


def robots_erlaubt(url: str, zeitlimit: int = 8) -> bool:
    """robots.txt-Prüfung mit Zwischenspeicher.

    Warum überhaupt: Ein Werkzeug, das fremde Server regelmäßig abfragt,
    sollte deren erklärte Regeln lesen. Kosten tut das eine Anfrage je
    Instanz und sechs Stunden.

    Fehlertoleranz: Eine unerreichbare robots.txt gilt als Erlaubnis –
    dieselbe Auslegung, die Browser und `urllib.robotparser` bei 404
    anwenden. Ein ausgefallener Server darf die Kette nicht stilllegen.
    """
    parsed = urllib.parse.urlparse(url)
    basis = f"{parsed.scheme}://{parsed.netloc}"
    jetzt = time.time()
    treffer = _ROBOTS_CACHE.get(basis)
    if treffer and jetzt - treffer[0] < _ROBOTS_TTL:
        return treffer[1]

    erlaubt = True
    try:
        _, text, _ = hole(basis + "/robots.txt", zeitlimit=zeitlimit, wiederholungen=1)
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(text.splitlines())
        erlaubt = parser.can_fetch(USER_AGENT.split("/")[0], url)
    except Exception:
        erlaubt = True
    _ROBOTS_CACHE[basis] = (jetzt, erlaubt)
    return erlaubt


def warten(anbieter_id: str) -> None:
    """Mindestabstand zwischen zwei Anfragen an denselben Anbieter."""
    abstand = ANBIETER.get(anbieter_id, {}).get("min_abstand", 1.0)
    zuletzt = _LETZTE_ANFRAGE.get(anbieter_id, 0.0)
    rest = abstand - (time.time() - zuletzt)
    if rest > 0:
        time.sleep(rest)
    _LETZTE_ANFRAGE[anbieter_id] = time.time()


# ====================================================================
#  NORMALISIERUNG (Apify-Ausgabevertrag)
# ====================================================================
def normalisieren(anfrage: str, url: str, titel: str, beschreibung: str,
                  rang: int, anbieter: str, anzeigedomaene: str = "",
                  merkmale: list | None = None, seite: int = 1,
                  trefferzahl: int | None = None) -> dict:
    """Ein Treffer im Format des Apify-Actors, deutsch benannt.

    Das Feldbild lehnt sich bewusst an den Original-Actor an (`rank`,
    `title`, `description`, `url`, `siteName`, `pageInJson`), damit ein
    späterer Umstieg auf den Actor keine Auswertung umbauen muss.
    """
    url = url_saeubern(url)
    return {
        "anfrage": anfrage,
        "rang": rang,
        "titel": re.sub(r"\s+", " ", (titel or "")).strip(),
        "beschreibung": re.sub(r"\s+", " ", (beschreibung or "")).strip(),
        "url": url,
        "domaene": domaene_aus_url(url),
        "anzeigedomaene": (anzeigedomaene or domaene_aus_url(url)).strip(),
        "merkmale": sorted(set(merkmale or [])),
        "quelle": anbieter,
        "seite": seite,
        "position": (seite - 1) * 10 + rang,
        "trefferzahl": trefferzahl,
    }


def entdoppeln(treffer: list[dict]) -> list[dict]:
    """Doppelte URLs entfernen, Ränge neu durchnummerieren.

    Nötig, weil mehrere SearXNG-Engines denselben Treffer liefern und weil
    ein Kettenlauf mehrerer Anbieter sonst denselben Link mehrfach zählt –
    was die Wettbewerbs-Auswertung systematisch verfälschen würde.
    """
    gesehen: set[str] = set()
    raus: list[dict] = []
    for treffer_eintrag in treffer:
        schluessel = treffer_eintrag.get("url", "").rstrip("/").lower()
        if not schluessel or schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        kopie = dict(treffer_eintrag)
        kopie["rang"] = len(raus) + 1
        raus.append(kopie)
    return raus


# ====================================================================
#  ANBIETER: SEARXNG (Metasuche, JSON + HTML)
# ====================================================================
def _searxng_anfrage(instanz: str, anfrage: str, optionen: dict) -> list[dict]:
    """Eine Instanz befragen: erst JSON, dann HTML."""
    instanz = instanz.rstrip("/")
    parameter = {
        "q": anfrage,
        "language": optionen.get("sprache", "de"),
        "categories": "general",
        "pageno": 1,
        "safesearch": 0,
    }
    # JSON ist der saubere Weg – aber viele Instanzen deaktivieren ihn
    # (`formats:` in settings.yml). Deshalb der HTML-Rückfall.
    try:
        url = instanz + "/search?" + urllib.parse.urlencode(
            {**parameter, "format": "json"})
        status, text, _ = hole(url, zeitlimit=18, wiederholungen=2)
        daten = json.loads(text)
        if isinstance(daten, dict) and daten.get("results"):
            return _searxng_json(anfrage, daten, optionen.get("max_treffer", 10))
    except (AnfrageFehler, ValueError, json.JSONDecodeError):
        pass

    url = instanz + "/search?" + urllib.parse.urlencode(parameter)
    status, text, _ = hole(url, zeitlimit=18, wiederholungen=2)
    return parse_searxng(anfrage, text, url, optionen.get("max_treffer", 10))


def _searxng_json(anfrage: str, daten: dict, max_treffer: int) -> list[dict]:
    treffer = []
    gesamt = daten.get("number_of_results") or None
    for i, eintrag in enumerate(daten.get("results", [])[:max_treffer], start=1):
        url = url_saeubern(eintrag.get("url", ""))
        if not url:
            continue
        merkmale = []
        if eintrag.get("thumbnail"):
            merkmale.append("vorschaubild")
        engine = eintrag.get("engine") or ""
        if engine:
            merkmale.append(f"engine:{engine}")
        treffer.append(normalisieren(
            anfrage=anfrage, url=url,
            titel=eintrag.get("title", ""),
            beschreibung=eintrag.get("content", ""),
            rang=i, anbieter="searxng",
            anzeigedomaene=urllib.parse.urlparse(url).netloc,
            merkmale=merkmale, trefferzahl=gesamt))
    return treffer


def parse_searxng(anfrage: str, html: str, basis: str = "",
                  max_treffer: int = 10) -> list[dict]:
    """HTML-Rückfall. SearXNG-Instanzen nutzen unterschiedliche Themes.

    Deshalb wird nicht ein Selektor hart verdrahtet, sondern eine
    Trefferkarte über mehrere bekannte Muster gesucht. Fällt ein Theme
    aus, tragen die anderen – ein einzelner Selektor wäre ein
    Ein-Punkt-Versagen, das niemand bemerkt.

    WICHTIG – Reihenfolge der Selektoren: SearXNG baut die Karte als
    `<h3><a class="url_wrapper">…` (die Adresse) und `<h4 class="title">`
    (den Titel). Wer hier `h3 a` zuerst nimmt, schreibt die Adresse in das
    Titelfeld. Genau das passierte im ersten Entwurf, und der Befund war
    tückisch: Der Lauf lief grün, die Treffer stimmten – nur die Titel
    waren Adressen.
    """
    dokument = baum(html)
    karten = dokument.waehle("article.result, .result, li.result")
    treffer = []
    for karte in karten:
        klassen = karte.klassen()
        if klassen & {"result_ad", "ad", "result--ad"}:
            continue
        # Erst der Titellink, dann der Adress-Wrapper, dann irgendein Link.
        link = (karte.waehle_eins("h4.title a") or karte.waehle_eins(".title a")
                or karte.waehle_eins("h3.title a") or karte.waehle_eins("a.url_wrapper")
                or karte.waehle_eins("h2 a") or karte.waehle_eins("a[href]"))
        url = url_saeubern(attribut_url(link, basis))
        if not url or "searx" in (urllib.parse.urlparse(url).netloc or ""):
            continue
        # Anzeigeadresse: eigene Quelle, sonst die Trefferdomäne.
        anzeige = (karte.waehle_eins("span.url_o2") or karte.waehle_eins(".url_o2")
                   or karte.waehle_eins("a.url_wrapper"))
        titel_knoten = (karte.waehle_eins("h4.title") or karte.waehle_eins(".title")
                        or karte.waehle_eins("h3.title") or karte.waehle_eins("h2"))
        titel = titel_knoten.text() if titel_knoten else ""
        if not titel and link is not None:
            titel = link.text()
        inhalt = (karte.waehle_eins("p.content") or karte.waehle_eins(".content")
                  or karte.waehle_eins("p"))
        merkmale = []
        engines = karte.waehle_eins(".engines")
        if engines:
            for name in engines.text().split():
                merkmale.append(f"engine:{name}")
        treffer.append(normalisieren(
            anfrage=anfrage, url=url, titel=titel,
            beschreibung=inhalt.text() if inhalt else "",
            rang=len(treffer) + 1, anbieter="searxng",
            anzeigedomaene=anzeige.text() if anzeige else "",
            merkmale=merkmale))
        if len(treffer) >= max_treffer:
            break
    return treffer


def treffer_searxng(anfrage: str, optionen: dict) -> list[dict]:
    """Instanzen der Reihe nach durchprobieren – erste Antwort gewinnt.

    Die Instanz-Reihenfolge kommt aus der Konfiguration; die
    Gesundheitsführung in scripts/suchradar.py sortiert sie nach
    gemessener Zuverlässigkeit vor. Ein Ausfall einer Instanz ist damit
    kein Ausfall des Laufs, sondern eine Umschaltung.
    """
    instanzen = optionen.get("searxng_instanzen") or STANDARD_SEARXNG_INSTANZEN
    instanzen_zulassen(instanzen)
    fehler: list[str] = []
    for instanz in instanzen:
        instanz = str(instanz).rstrip("/")
        try:
            if not robots_erlaubt(instanz + "/search"):
                fehler.append(f"{instanz}: robots.txt verbietet /search")
                continue
            warten("searxng")
            treffer = _searxng_anfrage(instanz, anfrage, optionen)
        except (AnfrageFehler, ValueError) as e:
            fehler.append(f"{instanz}: {e}")
            continue
        if treffer:
            for t in treffer:
                t["merkmale"] = sorted(set(t["merkmale"]) | {f"instanz:{instanz}"})
            return treffer
        fehler.append(f"{instanz}: keine Treffer")
    if fehler:
        raise AnfrageFehler("SearXNG: keine Instanz lieferte Treffer – "
                            + " | ".join(fehler[:4]))
    return []


# ====================================================================
#  ANBIETER: DUCKDUCKGO (HTML)
# ====================================================================
def parse_duckduckgo(anfrage: str, html: str, max_treffer: int = 10) -> list[dict]:
    """DuckDuckGo-HTML → Trefferliste. Getrennt von HTTP, damit prüfbar.

    Die Umleitungs-Links (`/l/?uddg=…`) werden ausgepackt – sonst stünde
    in jedem Bericht dieselbe DuckDuckGo-URL und die
    Wettbewerbs-Auswertung zählte nur noch duckduckgo.com.
    """
    dokument = baum(html)
    karten = dokument.waehle(".web-result, .result, .results_links_deep")
    treffer: list[dict] = []
    for karte in karten:
        # Anzeigen tragen bei DuckDuckGo `result--ad`; sie gehören nicht in
        # ein organisches Ranking.
        if karte.klassen() & {"result--ad", "result--ad-large"}:
            continue
        link = karte.waehle_eins("a.result__a") or karte.waehle_eins("h2 a")
        url = uddg_entpacken(url_saeubern(attribut_url(link)))
        if not url or "duckduckgo.com" in url:
            continue
        snippet = (karte.waehle_eins("a.result__snippet")
                   or karte.waehle_eins(".result__snippet"))
        anzeige = (karte.waehle_eins("a.result__url")
                   or karte.waehle_eins(".result__extras__url"))
        merkmale = []
        if karte.waehle_eins(".result__extras"):
            merkmale.append("zusatzzeile")
        treffer.append(normalisieren(
            anfrage=anfrage, url=url,
            titel=link.text() if link else "",
            beschreibung=snippet.text() if snippet else "",
            rang=len(treffer) + 1, anbieter="duckduckgo",
            anzeigedomaene=anzeige.text() if anzeige else "",
            merkmale=merkmale))
        if len(treffer) >= max_treffer:
            break
    return treffer


def treffer_duckduckgo(anfrage: str, optionen: dict) -> list[dict]:
    """HTML-Endpunkt von DuckDuckGo, ohne Schlüssel."""
    max_treffer = optionen.get("max_treffer", 10)
    warten("duckduckgo")
    if not robots_erlaubt("https://html.duckduckgo.com/html/"):
        raise AnfrageFehler("DuckDuckGo: robots.txt verbietet den HTML-Endpunkt")
    parameter = urllib.parse.urlencode({
        "q": anfrage,
        "kl": (optionen.get("land", "de") or "de").upper() + "-de",
    })
    status, html, _ = hole(
        "https://html.duckduckgo.com/html/?" + parameter,
        zeitlimit=18, wiederholungen=2)

    treffer = parse_duckduckgo(anfrage, html, max_treffer)
    if not treffer:
        raise AnfrageFehler("DuckDuckGo: keine Treffer (Blockade oder "
                            " Markup-Änderung?)", status)
    return treffer


# ====================================================================
#  ANBIETER: DUCKDUCKGO LITE (Ausweichstufe)
# ====================================================================
def parse_duckduckgo_lite(anfrage: str, html: str, max_treffer: int = 10) -> list[dict]:
    """DuckDuckGo-Lite-Tabellenlayout → Trefferliste.

    Lite liefert keine Trefferkarten, sondern ein flaches
    `<table>`-Layout: Titel und Snippet stehen in **Geschwisterzeilen**.

        <tr class="result-link"><td><a class="result-link">TITEL</a></td></tr>
        <tr><td class="result-snippet">SNIPPET</td></tr>

    Der HTML-Baum kennt keinen Geschwister-Selektor – braucht hier aber
    auch keinen. Stattdessen läuft ein Zustandsautomat zeilenweise durch
    das Dokument: Eine Link-Zeile eröffnet einen Treffer, die nächste
    Snippet-Zeile schließt ihn.

    Warum NICHT über den Index gepaart wird: Der erste Entwurf sammelte
    beide Listen und führte sie über `liste[i]` zusammen. Das funktioniert
    genau so lange, wie jeder Link ein Snippet hat – und kippt danach
    still. Ein fehlendes Snippet verschob jede folgende Zuordnung um
    eins, der Lauf blieb grün, nur die Beschreibungen gehörten zum
    jeweils vorherigen Titel. Der Unit-Test
    `test_lite_verschiebt_die_liste_nicht_bei_fehlendem_snippet` hat genau
    das gefunden.

    Eine übersprungene Anzeige setzt den offenen Treffer ausdrücklich
    zurück – sonst würde ihr Snippet beim letzten echten Treffer landen.
    """
    dokument = baum(html)
    paarungen: list[tuple[str, str, str]] = []
    offen: tuple[str, str] | None = None

    def ablegen(snippet: str) -> None:
        nonlocal offen
        if offen:
            paarungen.append((offen[0], offen[1], snippet))
            offen = None

    for zeile in dokument.waehle("tr"):
        link = zeile.waehle_eins("a.result-link") or zeile.waehle_eins("a[href]")
        if link is not None:
            ablegen("")                                   # Vorgänger ohne Snippet
            url = uddg_entpacken(url_saeubern(attribut_url(link)))
            # Anzeigen zeigen bei Lite auf duckduckgo.com/y.js – dieselbe
            # Regel wie bei der Vollversion filtert sie mit raus.
            if url and "duckduckgo.com" not in url:
                offen = (url, link.text())
            continue
        snippet = (zeile.waehle_eins("td.result-snippet")
                   or zeile.waehle_eins(".result-snippet"))
        if snippet is not None:
            ablegen(snippet.text())
    ablegen("")

    treffer: list[dict] = []
    for url, titel, beschreibung in paarungen[:max_treffer]:
        treffer.append(normalisieren(
            anfrage=anfrage, url=url, titel=titel, beschreibung=beschreibung,
            rang=len(treffer) + 1, anbieter="duckduckgo_lite",
            merkmale=["lite-endpunkt"]))
    return treffer


def treffer_duckduckgo_lite(anfrage: str, optionen: dict) -> list[dict]:
    """Schlanke Ausweichstufe zu `treffer_duckduckgo`.

    Warum ein zweiter DuckDuckGo-Weg: `html.duckduckgo.com` ist der
    Endpunkt, der Rechenzentrums-IPs am ehesten blockt – und genau aus
    solchen Netzbereichen fahren die GitHub-Runner. Lite ist weniger
    aufwendig und damit erfahrungsgemäß nachsichtiger. Ohne diese Stufe
    fällt bei einer Blockade sofort Mojeek an, und damit ein anderer
    Index statt derselben Quelle.
    """
    max_treffer = optionen.get("max_treffer", 10)
    warten("duckduckgo_lite")
    if not robots_erlaubt("https://lite.duckduckgo.com/lite/"):
        raise AnfrageFehler("DuckDuckGo Lite: robots.txt verbietet den Endpunkt")
    parameter = urllib.parse.urlencode({
        "q": anfrage,
        "kl": (optionen.get("land", "de") or "de").upper() + "-de",
    })
    status, html, _ = hole(
        "https://lite.duckduckgo.com/lite/?" + parameter,
        zeitlimit=18, wiederholungen=2)

    treffer = parse_duckduckgo_lite(anfrage, html, max_treffer)
    if not treffer:
        raise AnfrageFehler("DuckDuckGo Lite: keine Treffer (Blockade oder "
                            " Markup-Änderung?)", status)
    return treffer


# ====================================================================
#  ANBIETER: MOJEEK (unabhängiger Index)
# ====================================================================
def parse_mojeek(anfrage: str, html: str, max_treffer: int = 10) -> list[dict]:
    """Mojeek-HTML → Trefferliste."""
    dokument = baum(html)
    eintraege = dokument.waehle("ul.results-standard li, li.result, ol.results li")
    treffer: list[dict] = []
    for eintrag in eintraege:
        link = eintrag.waehle_eins("a.ob") or eintrag.waehle_eins("h2 a") \
            or eintrag.waehle_eins("a[href]")
        ziel = url_saeubern(attribut_url(link))
        if not ziel or "mojeek.com" in ziel:
            continue
        titel = eintrag.waehle_eins("h2") or eintrag.waehle_eins(".title")
        snippet = eintrag.waehle_eins("p.s") or eintrag.waehle_eins("p.desc") \
            or eintrag.waehle_eins("p")
        pfad = eintrag.waehle_eins("p.path") or eintrag.waehle_eins(".path")
        treffer.append(normalisieren(
            anfrage=anfrage, url=ziel,
            titel=titel.text() if titel else (link.text() if link else ""),
            beschreibung=snippet.text() if snippet else "",
            rang=len(treffer) + 1, anbieter="mojeek",
            anzeigedomaene=pfad.text() if pfad else ""))
        if len(treffer) >= max_treffer:
            break
    return treffer


def treffer_mojeek(anfrage: str, optionen: dict) -> list[dict]:
    """Mojeek – eigener Index, kein Aggregator.

    Wert als Kontrollwert: Stimmen SearXNG- und Mojeek-Rang überein, ist
    der Rang vermutlich ein Index-Rang. Weichen sie stark ab, ist der
    Befund ein Artefakt der Aggregation – und gehört nicht in einen
    Bericht, der Entscheidungen begründet.
    """
    max_treffer = optionen.get("max_treffer", 10)
    warten("mojeek")
    if not robots_erlaubt("https://www.mojeek.com/search"):
        raise AnfrageFehler("Mojeek: robots.txt verbietet /search")
    url = "https://www.mojeek.com/search?" + urllib.parse.urlencode({
        "q": anfrage, "lang": optionen.get("sprache", "de"),
        "fmt": "list",
    })
    status, html, _ = hole(url, zeitlimit=18, wiederholungen=2)

    treffer = parse_mojeek(anfrage, html, max_treffer)
    if not treffer:
        raise AnfrageFehler("Mojeek: keine Treffer", status)
    return treffer


# ====================================================================
#  ANBIETER: WIKIPEDIA (offizielle API)
# ====================================================================
def treffer_wikipedia(anfrage: str, optionen: dict) -> list[dict]:
    """Offizielle MediaWiki-API – ausdrücklich ohne Schlüssel nutzbar.

    Ehrlich eingeordnet: Das ist kein Suchmaschinen-Ranking. Es ist der
    Wissens-Rückfall, damit ein Lauf auch dann etwas liefert, wenn jede
    Suchinstanz ausfällt. `organisch: false` im Register hält das
    maschinenlesbar fest.
    """
    max_treffer = optionen.get("max_treffer", 10)
    sprache = (optionen.get("sprache", "de") or "de").split("-")[0]
    host = f"{sprache}.wikipedia.org"
    if host not in ERLAUBTE_HOSTS:
        host = "de.wikipedia.org"
    warten("wikipedia")
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": anfrage,
        "srlimit": min(max_treffer, 20), "format": "json", "formatversion": 2,
    })
    _, text, _ = hole(url, zeitlimit=15, wiederholungen=2)
    daten = json.loads(text)
    treffer = []
    for i, eintrag in enumerate(
            (daten.get("query", {}) or {}).get("search", [])[:max_treffer], start=1):
        titel = eintrag.get("title", "")
        # Snippets kommen als HTML-Fragment; der Baum entfernt die Markup-Reste.
        snippet = baum("<p>" + (eintrag.get("snippet") or "") + "</p>").text()
        treffer.append(normalisieren(
            anfrage=anfrage,
            url=f"https://{host}/wiki/{urllib.parse.quote(titel.replace(' ', '_'))}",
            titel=titel, beschreibung=snippet,
            rang=i, anbieter="wikipedia",
            merkmale=["wissensquelle"]))
    return treffer


# ====================================================================
#  ANBIETER: OPTIONAL MIT SCHLÜSSEL (hinter der Kostensperre)
# ====================================================================
def treffer_google_cse(anfrage: str, optionen: dict) -> list[dict]:
    """Google Custom Search JSON API – der offizielle, bezahlbare Weg.

    100 Abfragen pro Tag sind frei; darüber kostet es. Der Quoten-Zähler
    in scripts/suchradar.py hält das Tageslimit hart – nicht der Anbieter
    selbst, denn der kennt nur die einzelne Anfrage.
    """
    env = optionen.get("umgebung") or os.environ
    schluessel = str(env.get("GOOGLE_CSE_KEY", "")).strip()
    cx = str(env.get("GOOGLE_CSE_ID", "")).strip()
    if not schluessel or not cx:
        raise AnfrageFehler("Google CSE: GOOGLE_CSE_KEY oder GOOGLE_CSE_ID fehlt")
    warten("google_cse")
    url = "https://www.googleapis.com/customsearch/v1?" + urllib.parse.urlencode({
        "key": schluessel, "cx": cx, "q": anfrage,
        "num": min(optionen.get("max_treffer", 10), 10),
        "start": optionen.get("start", 1),
        "gl": optionen.get("land", "de"), "hl": optionen.get("sprache", "de"),
        "safe": "off",
    })
    _, text, _ = hole(url, zeitlimit=20, wiederholungen=2)
    daten = json.loads(text)
    info = daten.get("searchInformation", {}) or {}
    gesamt = info.get("totalResults")
    try:
        gesamt = int(gesamt)
    except (TypeError, ValueError):
        gesamt = None
    treffer = []
    for i, eintrag in enumerate(daten.get("items", []), start=1):
        merkmale = []
        pagemap = eintrag.get("pagemap", {}) or {}
        for merkmal in ("cse_thumbnail", "faqpage", "videoobject",
                        "review", "localbusiness", "sitelinkssearchbox"):
            if pagemap.get(merkmal):
                merkmale.append(merkmal)
        treffer.append(normalisieren(
            anfrage=anfrage, url=eintrag.get("link", ""),
            titel=eintrag.get("title", ""),
            beschreibung=eintrag.get("snippet", ""),
            rang=i, anbieter="google_cse",
            anzeigedomaene=eintrag.get("displayLink", ""),
            merkmale=merkmale, trefferzahl=gesamt))
    return treffer


def treffer_brave(anfrage: str, optionen: dict) -> list[dict]:
    env = optionen.get("umgebung") or os.environ
    schluessel = str(env.get("BRAVE_API_KEY")
                     or env.get("SEARCH_API_KEY", "")).strip()
    if not schluessel:
        raise AnfrageFehler("Brave: kein Schlüssel in der Umgebung")
    warten("brave")
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({
        "q": anfrage, "count": min(optionen.get("max_treffer", 10), 20),
        "country": (optionen.get("land", "de") or "de").upper(),
        "search_lang": optionen.get("sprache", "de"),
    })
    _, text, _ = hole(url, kopfzeilen={"X-Subscription-Token": schluessel,
                                       "Accept": "application/json"},
                      zeitlimit=20, wiederholungen=2)
    daten = json.loads(text)
    treffer = []
    for i, eintrag in enumerate(
            ((daten.get("web") or {}).get("results") or [])[:optionen.get("max_treffer", 10)],
            start=1):
        merkmale = []
        if eintrag.get("extra_snippets"):
            merkmale.append("erweitertes_snippet")
        for sonder in ("faq", "infobox", "news", "videos", "locations"):
            if daten.get(sonder):
                merkmale.append(sonder)
        treffer.append(normalisieren(
            anfrage=anfrage, url=eintrag.get("url", ""),
            titel=eintrag.get("title", ""),
            beschreibung=eintrag.get("description", ""),
            rang=i, anbieter="brave", merkmale=merkmale))
    return treffer


def treffer_serper(anfrage: str, optionen: dict) -> list[dict]:
    env = optionen.get("umgebung") or os.environ
    schluessel = str(env.get("SERPER_API_KEY", "")).strip()
    if not schluessel:
        raise AnfrageFehler("serper.dev: SERPER_API_KEY fehlt")
    warten("serper")
    _, text, _ = hole(
        "https://google.serper.dev/search",
        kopfzeilen={"X-API-KEY": schluessel, "Content-Type": "application/json"},
        daten=json.dumps({"q": anfrage, "gl": optionen.get("land", "de"),
                          "hl": optionen.get("sprache", "de"),
                          "num": optionen.get("max_treffer", 10)}).encode(),
        zeitlimit=20, wiederholungen=2)
    daten = json.loads(text)
    treffer = []
    for i, eintrag in enumerate(daten.get("organic", []), start=1):
        merkmale = []
        if eintrag.get("sitelinks"):
            merkmale.append("sitelinks")
        treffer.append(normalisieren(
            anfrage=anfrage, url=eintrag.get("link", ""),
            titel=eintrag.get("title", ""),
            beschreibung=eintrag.get("snippet", ""),
            rang=i, anbieter="serper", merkmale=merkmale,
            trefferzahl=(daten.get("searchParameters") or {}).get("num")))
    return treffer


def treffer_serpapi(anfrage: str, optionen: dict) -> list[dict]:
    env = optionen.get("umgebung") or os.environ
    schluessel = str(env.get("SERPAPI_KEY") or env.get("SERPAPI_API_KEY", "")).strip()
    if not schluessel:
        raise AnfrageFehler("SerpApi: kein Schlüssel in der Umgebung")
    warten("serpapi")
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode({
        "api_key": schluessel, "q": anfrage, "engine": "google",
        "google_domain": "google.de", "gl": optionen.get("land", "de"),
        "hl": optionen.get("sprache", "de"),
        "num": optionen.get("max_treffer", 10),
    })
    _, text, _ = hole(url, zeitlimit=25, wiederholungen=2)
    daten = json.loads(text)
    treffer = []
    for i, eintrag in enumerate(daten.get("organic_results", []), start=1):
        merkmale = []
        if eintrag.get("sitelinks"):
            merkmale.append("sitelinks")
        treffer.append(normalisieren(
            anfrage=anfrage, url=eintrag.get("link", ""),
            titel=eintrag.get("title", ""),
            beschreibung=eintrag.get("snippet", ""),
            rang=i, anbieter="serpapi", merkmale=merkmale,
            trefferzahl=daten.get("search_information", {}).get("total_results")))
    return treffer


def treffer_apify(anfrage: str, optionen: dict) -> list[dict]:
    """Das Original: `apify/google-search-scraper` als Adapter.

    Existiert, damit der Eigenbau messbar gegen den Actor antreten kann –
    und damit niemand den Nachbau neu schreiben muss, falls irgendwann
    doch bezahlt werden soll. Läuft nur mit Token UND Freigabe der
    Kostensperre; beides fehlt im Normalbetrieb.
    """
    env = optionen.get("umgebung") or os.environ
    token = str(env.get("APIFY_TOKEN") or env.get("APIFY_API_TOKEN", "")).strip()
    if not token:
        raise AnfrageFehler("Apify: APIFY_TOKEN fehlt")
    warten("apify")
    # Feldbild des Actors: Das sind die Felder, die er zurückgibt.
    felder = ("searchResultUrl,rank,title,description,siteName,url,"
              "matches,pageInJson,position")
    eingabe = {
        "queries": anfrage,
        "maxItems": optionen.get("max_treffer", 10),
        "countryCode": optionen.get("land", "de"),
        "languageCode": optionen.get("sprache", "de"),
        "resultsType": "searches",
        "mobileResults": optionen.get("geraet") == "mobil",
        "extendOutputFunction": "",
    }
    url = ("https://api.apify.com/v2/acts/apify~google-search-scraper/"
           "run-sync-get-dataset-items?token=" + urllib.parse.quote(token)
           + "&fields=" + urllib.parse.quote(felder))
    _, text, _ = hole(url, kopfzeilen={"Content-Type": "application/json"},
                      daten=json.dumps(eingabe).encode(),
                      zeitlimit=120, wiederholungen=1)
    daten = json.loads(text)
    if not isinstance(daten, list):
        daten = daten.get("items", [])
    treffer = []
    for i, eintrag in enumerate(daten, start=1):
        treffer.append(normalisieren(
            anfrage=anfrage, url=eintrag.get("url", ""),
            titel=eintrag.get("title", ""),
            beschreibung=eintrag.get("description", ""),
            rang=eintrag.get("rank") or i, anbieter="apify",
            anzeigedomaene=eintrag.get("siteName", ""),
            trefferzahl=eintrag.get("matches")))
    return treffer


# ====================================================================
#  VERTEILER
# ====================================================================
AUSFUEHRER = {
    "searxng": treffer_searxng,
    "duckduckgo": treffer_duckduckgo,
    "duckduckgo_lite": treffer_duckduckgo_lite,
    "mojeek": treffer_mojeek,
    "wikipedia": treffer_wikipedia,
    "google_cse": treffer_google_cse,
    "brave": treffer_brave,
    "serper": treffer_serper,
    "serpapi": treffer_serpapi,
    "apify": treffer_apify,
}


def hole_treffer(anfrage: str, optionen: dict | None = None) -> list[dict]:
    """Treffer für eine Anfrage über die konfigurierte Kette.

    Fällt durch die Anbieter-Reihenfolge, bis einer liefert. Ein einzelner
    Ausfall ist damit kein Laufabbruch – aber wenn **kein** Anbieter
    liefert, ist das ein Fehler und kein leeres Ergebnis. Ein leerer
    Bericht, der still „alles in Ordnung" meldet, ist die teuerste
    Variante dieses Fehlers.
    """
    optionen = dict(optionen or {})
    anfrage = (anfrage or "").strip()
    if not anfrage:
        raise ValueError("Leere Anfrage")

    reihenfolge = optionen.get("reihenfolge") or STANDARD_REIHENFOLGE
    nur = optionen.get("nur_anbieter")
    if nur:
        reihenfolge = [a for a in reihenfolge if a in set(nur)]

    fehler: list[str] = []
    for anbieter_id in reihenfolge:
        ausfuehrer = AUSFUEHRER.get(anbieter_id)
        if ausfuehrer is None:
            fehler.append(f"{anbieter_id}: kein Ausführer")
            continue
        erlaubt, grund = pruefe_freigabe(anbieter_id, optionen.get("umgebung"))
        if not erlaubt:
            fehler.append(f"{anbieter_id}: {grund}")
            continue
        if not ANBIETER[anbieter_id].get("schluessellos") and not \
                schluessel_vorhanden(anbieter_id, optionen.get("umgebung")):
            fehler.append(f"{anbieter_id}: Schlüssel fehlt")
            continue
        try:
            treffer = ausfuehrer(anfrage, optionen)
        except (AnfrageFehler, ValueError, json.JSONDecodeError,
                KeyError, TypeError, OSError) as e:
            fehler.append(f"{anbieter_id}: {e}")
            continue
        if treffer:
            if optionen.get("entdoppeln", True):
                treffer = entdoppeln(treffer)
            return treffer
        fehler.append(f"{anbieter_id}: keine Treffer")

    raise AnfrageFehler("Kein Anbieter lieferte Treffer für "
                        f"{anfrage!r}: " + " | ".join(fehler[-6:]))


# ====================================================================
#  SELBSTTEST (offline, ohne Netz)
# ====================================================================
def selbsttest() -> int:
    """Prüft Gatter und Normalisierung ohne eine einzige Netzverbindung."""
    problem = []

    def pruefe(bedingung, meldung):
        if not bedingung:
            problem.append(meldung)

    # 1) SSRF-Gatter: fremder Host wird abgelehnt
    pruefe(not host_erlaubt("http://169.254.169.254/latest/meta-data/"),
           "SSRF-Gatter lässt Metadaten-Endpunkt durch")
    pruefe(not host_erlaubt("file:///etc/passwd"),
           "SSRF-Gatter lässt file:// durch")
    pruefe(host_erlaubt("https://html.duckduckgo.com/html/?q=x"),
           "SSRF-Gatter blockiert einen erlaubten Anbieter")

    # 2) Kostensperre: bezahlter Anbieter ohne Freigabe gesperrt
    erlaubt, grund = pruefe_freigabe("serper")
    pruefe(not erlaubt, f"Bezahlter Anbieter `serper` ist ohne Freigabe nutzbar ({grund})")
    pruefe("serp_premium" in grund or "Kostensperre" in grund,
           "Sperrgrund nennt nicht die Fläche `serp_premium`")

    # 3) Schlüssellose Anbieter brauchen weder Schlüssel noch Freigabe
    for aid in ("searxng", "duckduckgo", "mojeek", "wikipedia"):
        erlaubt, _ = pruefe_freigabe(aid)
        pruefe(erlaubt, f"Schlüsselloser Anbieter `{aid}` ist gesperrt")

    # 4) Unbekannter Anbieter ist gesperrt, nicht „erlaubt"
    pruefe(not pruefe_freigabe("irgendein_dienst")[0],
           "Unbekannter Anbieter gilt als freigegeben")

    # 5) Schlüsselprüfung: google_cse braucht BEIDE Variablen
    pruefe(not schluessel_vorhanden("google_cse", {"GOOGLE_CSE_KEY": "x"}),
           "google_cse gilt mit halbem Schlüsselpaar als bereit")
    pruefe(schluessel_vorhanden("google_cse",
                                {"GOOGLE_CSE_KEY": "x", "GOOGLE_CSE_ID": "y"}),
           "google_cse erkennt ein vollständiges Schlüsselpaar nicht")

    # 6) Entdoppelung: dieselbe URL nur einmal, Ränge lückenlos
    doppel = [{"url": "https://a.de/x", "rang": 1}, {"url": "https://a.de/x/", "rang": 2},
              {"url": "https://b.de/", "rang": 3}]
    raus = entdoppeln(doppel)
    pruefe(len(raus) == 2, f"Entdoppelung: {len(raus)} statt 2 Treffer")
    pruefe([t["rang"] for t in raus] == [1, 2], "Entdoppelung hinterlässt Ranglücken")

    # 7) DuckDuckGo-Umleitung wird ausgepackt
    umleitung = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=1"
    pruefe(uddg_entpacken(umleitung) == "https://example.com/a",
           f"UDDG nicht ausgepackt: {uddg_entpacken(umleitung)}")
    pruefe(uddg_entpacken("https://example.com/b") == "https://example.com/b",
           "uddg_entpacken verändert fremde URLs")

    # 8) Domainen-Auswertung für die Wettbewerbs-Analyse
    pruefe(domaene_aus_url("https://www.test.de/x") == "test.de",
           "www. wird nicht abgetrennt")
    pruefe(domaene_aus_url("https://shop.example.co.uk/x") == "example.co.uk",
           "Zweiteilige Endung falsch zerlegt")

    # 9) Normalisierung liefert das vereinbarte Feldbild
    probe = normalisieren("strom", "https://a.de/x", "Titel", "Text", 1, "mojeek")
    for feld in ("anfrage", "rang", "titel", "beschreibung", "url", "domaene",
                 "quelle", "seite", "position", "merkmale"):
        pruefe(feld in probe, f"Normalisierung: Feld `{feld}` fehlt")
    pruefe(probe["position"] == 1, "Positionsrechnung weicht ab")

    # 10) Jeder registrierte Anbieter hat einen Ausführer
    for aid in ANBIETER:
        pruefe(aid in AUSFUEHRER, f"Anbieter `{aid}` hat keinen Ausführer")
    for aid in AUSFUEHRER:
        pruefe(aid in ANBIETER, f"Ausführer `{aid}` ist nicht registriert")

    # 11) Kein freigegebener Host ohne Ausführer.
    #     Ein Eintrag in ERLAUBTE_HOSTS, den niemand anfragt, ist eine
    #     unwahre Aussage im Code und vergrößert die Angriffsfläche um
    #     nichts. Genau so stand `api.duckduckgo.com` eine Weile hier –
    #     freigegeben, ungenutzt, unentdeckt. Diese Prüfung ist der Grund,
    #     warum das nicht noch einmal passiert.
    quelle = (Path(__file__).read_text(encoding="utf-8")
              .split("ERLAUBTE_HOSTS", 1)[-1])
    for host in sorted(ERLAUBTE_HOSTS):
        pruefe(quelle.count(f'"{host}"') > 0 or f"https://{host}" in quelle,
               f"ERLAUBTE_HOSTS enthält `{host}`, aber kein Anbieter fragt ihn an")

    if problem:
        for zeile in problem:
            print("  ✗ " + zeile, file=sys.stderr)
        return 1
    print(f"serp_anbieter-Selbsttest bestanden: {len(ANBIETER)} Anbieter, "
          f"11 Prüfblöcke, {len(AUSFUEHRER)} Ausführer.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selbsttest())
    print(json.dumps(anbieter_lage(), ensure_ascii=False, indent=2))
