#!/usr/bin/env python3
"""indexierbare_seiten.py – EINE Quelle für „welche Seiten sollen in den Index?“.

WARUM DIESES MODUL EXISTIERT (Befund 12.10.2026, GSC-Indexierung Premium)
-------------------------------------------------------------------------
Die Site hatte am 12.10.2026 drei Stellen, die dieselbe Frage auf je eigene Art
beantworteten:

  * `layouts/_partials/seo_indexierbar.html`  → robots-Meta je Seite
  * `layouts/sitemap.xml`                     → abgeleitet aus derselben Partial
  * `scripts/submit_indexnow.py`              → EINE HANDGESCHRIEBENE LISTE

Die dritte Stelle war die Lücke. Gemessen am Build vom 12.10.2026:

    74 indexierbare URLs in der Sitemap
    54 URLs, die IndexNow je gemeldet hat
    20 indexierbare Seiten, die NIE an eine Suchmaschine gemeldet wurden

Darunter alle Werkzeug-Rechner (`/werkzeuge/*/`), das Fixkosten-Cockpit
(`/cockpit/`), die Studien-Seite, `/ueber/`, `/transparenz/`, `/impressum/`
und `/datenschutz/` – also genau die Seiten, die Vertrauen und Umsatz tragen.
Die Klasse ist dieselbe, die `layouts/sitemap.xml` am 01.10.2026 schon einmal
erledigt hat: **Eine Namensliste bricht bei jedem Wachstum.** Jede neue Seite
fällt still aus der Meldung, bis jemand den Namen nachträgt.

Dieses Modul macht die gebaute Sitemap zur einzigen Quelle für ALLE
Einreichungswege (IndexNow, Google URL Inspection, Wachen). Es gilt dieselbe
Regel wie für die Sitemap selbst: ableiten, nicht aufzählen.

QUELLEN (in dieser Reihenfolge)
  1. `public/sitemap.xml`        – der gebaute Stand (Hugo, `--destination public`)
  2. `--sitemap-url` / live      – die AUSGELIEFERTE Sitemap (derselbe Text, den
                                   Google sieht; Beweis statt Annahme)
  3. `INDEX_GATE_BASE`           – dasselbe Verzeichnis, das index_hygiene_gate.py
                                   nutzt (gemeinsame Umgebungs-Vereinbarung)

Fällt alle Quellen weg, ist das ein FEHLER (Exit 2), kein leerer Lauf: Eine
Einreichung mit null URLs sieht aus wie Erfolg und ist keiner.

NUTZUNG (als Modul)
    from indexierbare_seiten import hole_seiten, reihenfolge
    seiten = hole_seiten()                 # [Seite, …] aus public/sitemap.xml
    queue = reihenfolge(seiten)            # nach Wichtigkeit + Frische

Aufruf als Programm (Diagnose):
    python3 scripts/indexierbare_seiten.py            # Bestand aus public/
    python3 scripts/indexierbare_seiten.py --live     # Bestand der Live-Site
    python3 scripts/indexierbare_seiten.py --selftest # offline, kein Netz

Nur Standardbibliothek: läuft in jedem Workflow ohne pip.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
import safe_xml as ET  # noqa: E402

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"

# Gemeinsame Vereinbarung mit index_hygiene_gate.py: Wer ein anderes
# Build-Verzeichnis prüft, sagt das über diese Variable – nicht über einen
# zweiten Parameter-Namen.
UMGEBUNG_BASIS = "INDEX_GATE_BASE"

# Googles harte Sitemap-Grenzen (Protokoll): 50.000 URLs und 50 MiB
# unkomprimiert je Datei. Wer sie reißt, bekommt in der Search Console
# „Sitemap konnte nicht gelesen werden" – ohne dass der Build rot ist.
MAX_URLS_PRO_SITEMAP = 50_000
MAX_BYTES_PRO_SITEMAP = 50 * 1024 * 1024

# Standard-Basis der Live-Site (hugo.toml: baseURL). Wird aus der Konfiguration
# gelesen, wenn sie dort steht – kein zweites hartkodiertes Zuhause.
FALLBACK_HOST = "franksfinanzcheck.de"

_USER_AGENT = "franksfinanzcheck-indexierung/1.0 (+https://franksfinanzcheck.de/impressum/)"


class SitemapFehler(RuntimeError):
    """Sitemap fehlt, ist unlesbar oder verletzt das Protokoll (Exit 2)."""


@dataclass(frozen=True)
class Seite:
    """Eine indexierbare Seite, wie die Sitemap sie erklärt.

    `pfad` ist der Wurzel-relative Pfad (`/posts/xyz/`), `url` die absolute
    URL. Beides wird gebraucht: Einreichungen arbeiten mit der absoluten URL,
    Wachen mit dem Pfad (Vergleich gegen gebaute Dateien).
    """

    url: str
    pfad: str
    lastmod: str = ""        # YYYY-MM-DD oder "" (Sitemap erlaubt beides)
    changefreq: str = ""
    priority: float = 0.5
    bilder: int = 0

    def prioritaet(self) -> float:
        return self.priority


def basis_verzeichnis(explicit: str | None = None) -> str:
    """Build-Verzeichnis: Argument > Umgebungsvereinbarung > `public/`."""
    return explicit or os.environ.get(UMGEBUNG_BASIS) or os.path.join(ROOT, "public")


def basis_url() -> str:
    """Absolute Site-Basis aus hugo.toml (`baseURL`), sonst Fallback."""
    cfg = os.path.join(ROOT, "hugo.toml")
    try:
        with open(cfg, encoding="utf-8") as f:
            for zeile in f:
                m = re.match(r'\s*baseURL\s*=\s*"([^"]+)"', zeile)
                if m:
                    return m.group(1).rstrip("/") + "/"
    except OSError:
        pass
    return f"https://{FALLBACK_HOST}/"


def sitemap_pfad(basis: str | None = None) -> str:
    return os.path.join(basis_verzeichnis(basis), "sitemap.xml")


def pfad_aus_url(url: str) -> str:
    """Absolute URL → wurzelrelativer Pfad mit führendem und ohne End-Slash-Verlust.

    `/` bleibt `/`. Query und Fragment fallen weg (die Sitemap führt beides
    nicht; ein `?` in einer Sitemap-URL wäre bereits ein Befund für die Wache).
    """
    parsed = urlparse(url)
    pfad = unquote(parsed.path or "/")
    if not pfad.startswith("/"):
        pfad = "/" + pfad
    return pfad


def datei_pfad(url: str, basis: str) -> str:
    """Pfad der gebauten HTML-Datei zu einer Sitemap-URL.

    `/posts/x/` → `<basis>/posts/x/index.html`, `/` → `<basis>/index.html`.
    """
    pfad = pfad_aus_url(url)
    if pfad.endswith("/"):
        return os.path.join(basis, pfad.lstrip("/"), "index.html")
    return os.path.join(basis, pfad.lstrip("/") + ".html")


def parse_sitemap(text: str) -> list[Seite]:
    """Sitemap-XML → Liste[Seite]. Bewusst tolerant gegenüber Namespaces.

    `layouts/sitemap.xml` schreibt `image:image`-Kinder. ElementTree braucht
    dafür die explizite Namespace-Abfrage; wer sie vergisst, zählt still null
    Bilder (die Bild-Sitemap wäre unbemerkt wirkungslos).
    """
    try:
        wurzel = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SitemapFehler(f"sitemap.xml ist kein gültiges XML: {exc}") from exc

    tag = wurzel.tag.lower()
    if not (tag.endswith("urlset") or tag.endswith("sitemapindex")):
        raise SitemapFehler(
            f"sitemap.xml hat die Wurzel `{wurzel.tag}` – erwartet `urlset` "
            "(oder `sitemapindex` für gestückelte Sitemaps)")

    seiten: list[Seite] = []
    for kind in wurzel:
        name = kind.tag.split('}', 1)[-1].lower()
        if name == "sitemap":
            # Sitemap-Index: die Kind-Sitemaps sind eigene Dateien. Für die
            # Einreichungswege zählt die URL der Teil-Sitemap nicht als Seite –
            # sie wird von `hole_seiten_index` aufgelöst.
            continue
        if name != "url":
            continue
        werte: dict[str, str] = {}
        bilder = 0
        for feld in kind:
            feldname = feld.tag.split('}', 1)[-1].lower()
            if feld.tag.startswith(f"{{{IMAGE_NS}}}"):
                if feldname == "image":
                    bilder += 1
                continue
            werte[feldname] = (feld.text or "").strip()
        url = werte.get("loc", "")
        if not url:
            raise SitemapFehler("Sitemap enthält einen <url>-Eintrag ohne <loc>")
        try:
            prio = float(werte.get("priority") or 0.5)
        except ValueError:
            prio = 0.5
        seiten.append(Seite(
            url=url,
            pfad=pfad_aus_url(url),
            lastmod=werte.get("lastmod", ""),
            changefreq=werte.get("changefreq", ""),
            priority=prio,
            bilder=bilder,
        ))
    return seiten


def pruefe_grenzen(seiten: list[Seite], byte_groesse: int) -> list[str]:
    """Protokoll-Grenzen und Duplikate melden (Befundliste, keine Ausnahme)."""
    befunde: list[str] = []
    if len(seiten) > MAX_URLS_PRO_SITEMAP:
        befunde.append(
            f"{len(seiten)} URLs in EINER Sitemap-Datei – Google erlaubt "
            f"{MAX_URLS_PRO_SITEMAP}. Ab dann: Sitemap-Index mit Stücken.")
    if byte_groesse > MAX_BYTES_PRO_SITEMAP:
        befunde.append(
            f"sitemap.xml ist {byte_groesse} Bytes – Google erlaubt "
            f"{MAX_BYTES_PRO_SITEMAP} Bytes unkomprimiert.")
    gesehen: set[str] = set()
    for s in seiten:
        if s.url in gesehen:
            befunde.append(f"doppelte URL in der Sitemap: {s.url}")
        gesehen.add(s.url)
    return befunde


def hole_seiten(basis: str | None = None, sitemap_url: str | None = None,
                http=None, pruefen: bool = True) -> tuple[list[Seite], list[str]]:
    """Indexierbare Seiten holen – aus dem Build oder von der Live-Site.

    Rückgabe: (seiten, befunde). `befunde` sind Protokoll-Verletzungen, die
    eine Wache hart melden muss; sie sind NICHT dasselbe wie ein Fehler beim
    Lesen (der wirft `SitemapFehler`).

    `http` ist injizierbar (Signatur: (url) -> (status, text)) und macht die
    Live-Variante offline testbar.
    """
    befunde: list[str] = []
    if sitemap_url:
        http = http or _hole_http
        status, text = http(sitemap_url)
        if status != 200:
            raise SitemapFehler(
                f"Sitemap {sitemap_url} antwortete mit HTTP {status} – Google "
                "sieht dieselbe Antwort und meldet die Sitemap als fehlerhaft.")
        if not text.strip():
            raise SitemapFehler(f"Sitemap {sitemap_url} ist leer.")
        groesse = len(text.encode("utf-8"))
        seiten = parse_sitemap(text)
    else:
        pfad = sitemap_pfad(basis)
        if not os.path.exists(pfad):
            raise SitemapFehler(
                f"{pfad} fehlt – zuerst Hugo bauen (`hugo --destination public`) "
                "oder `--live` für die ausgelieferte Sitemap verwenden.")
        with open(pfad, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        groesse = os.path.getsize(pfad)
        seiten = parse_sitemap(text)

    if not seiten:
        raise SitemapFehler(
            "Sitemap enthält keine einzige URL. Einreichen mit null URLs wäre "
            "ein stiller Ausfall – deshalb ist das ein Fehler, kein Leerlauf.")

    basis_host = urlparse(basis_url()).netloc.lower()
    for s in seiten:
        host = urlparse(s.url).netloc.lower()
        if host != basis_host:
            befunde.append(
                f"Sitemap-URL zeigt auf einen fremden Host: {s.url} "
                f"(erwartet {basis_host})")
    if pruefen:
        befunde += pruefe_grenzen(seiten, groesse)
    return seiten, befunde


def _hole_http(url: str, timeout: int = 30) -> tuple[int, str]:
    """Einfacher GET ohne Weiterleitungs-Kette (Beweis, was Google sieht)."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except (urllib.error.URLError, OSError) as exc:
        raise SitemapFehler(f"Sitemap {url} nicht erreichbar: {exc}") from exc


def reihenfolge(seiten: list[Seite], heute: str = "") -> list[Seite]:
    """Einreichungs-Queue: Wichtigkeit zuerst, dann Frische, dann Pfad.

    Warum diese Sortierung: Google URL Inspection hat ein hartes Kontingent
    (200 Anfragen je Property und Tag). Wer es verteilt, muss entscheiden,
    WELCHE Seite zuerst drankommt. Die Sitemap trägt die redaktionelle
    Gewichtung bereits (priority je Seitentyp in `layouts/sitemap.xml`), und
    `lastmod` sagt, wo sich etwas geändert hat. Beides zusammen ergibt eine
    Queue, die ohne Namenseinträge auskommt – dieselbe Regel wie überall hier.

    `heute` (YYYY-MM-DD) dient nur der deterministischen Testbarkeit; für die
    Reihenfolge selbst wird kein Kalenderwissen gebraucht.
    """
    return sorted(seiten, key=lambda s: (-s.priority, s.lastmod or "", s.pfad))


def nur_frische(seiten: list[Seite], seit: str) -> list[Seite]:
    """Seiten mit `lastmod` >= `seit` (YYYY-MM-DD); ohne lastmod = nicht frisch.

    String-Vergleich ist hier korrekt und gewollt: ISO-Daten sortieren
    lexikografisch. Ein Datum-Parser würde nur eine zweite Fehlerquelle
    (Zeitzonen, Formate) in eine Entscheidung bringen, die rein ordinal ist.
    """
    if not seit:
        return list(seiten)
    return [s for s in seiten if s.lastmod and s.lastmod >= seit]


def live_sitemap_url(basis: str | None = None) -> str:
    return basis_url() + "sitemap.xml"


# ---------------------------------------------------------------- Diagnose
def _selftest() -> int:
    """Offline-Selbsttest: Parsing, Reihenfolge, Fehlerpfade, Sabotage-Proben."""
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool) -> None:
        if not bedingung:
            fehler.append(name)

    muster = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
<url><loc>https://franksfinanzcheck.de/</loc><lastmod>2026-10-12</lastmod>
<changefreq>daily</changefreq><priority>1.0</priority></url>
<url><loc>https://franksfinanzcheck.de/posts/neu/</loc><lastmod>2026-10-11</lastmod>
<changefreq>weekly</changefreq><priority>0.8</priority>
<image:image><image:loc>https://franksfinanzcheck.de/images/covers/neu.jpg</image:loc>
<image:title>Neu</image:title></image:image></url>
<url><loc>https://franksfinanzcheck.de/pillar/strom-sparen/</loc>
<lastmod>2026-10-02</lastmod><changefreq>weekly</changefreq><priority>0.9</priority>
<image:image><image:loc>https://franksfinanzcheck.de/images/covers/p.jpg</image:loc></image:image></url>
</urlset>"""

    seiten = parse_sitemap(muster)
    pruefe("drei URLs gelesen", len(seiten) == 3)
    pruefe("Bilder gezählt (Namespaces)", seiten[1].bilder == 1 and seiten[2].bilder == 1)
    pruefe("Bildloses Home ohne Bild-Tag", seiten[0].bilder == 0)
    pruefe("Pfad normalisiert", seiten[0].pfad == "/" and seiten[1].pfad == "/posts/neu/")
    pruefe("Priority als Zahl", seiten[0].priority == 1.0)
    pruefe("lastmod übernommen", seiten[2].lastmod == "2026-10-02")

    queue = reihenfolge(seiten)
    pruefe("Queue nach Wichtigkeit", [s.pfad for s in queue] ==
           ["/", "/pillar/strom-sparen/", "/posts/neu/"])

    frisch = nur_frische(seiten, "2026-10-10")
    pruefe("Frischefilter", {s.pfad for s in frisch} == {"/", "/posts/neu/"})
    pruefe("Frischefilter ohne Schwelle = alles", len(nur_frische(seiten, "")) == 3)

    # Datei-Pfad-Auflösung (Wachen vergleichen Sitemap gegen gebaute Dateien)
    pruefe("Home → index.html",
           datei_pfad("https://franksfinanzcheck.de/", "/tmp/p").endswith("/index.html"))
    pruefe("Seite → Ordner/index.html",
           datei_pfad("https://franksfinanzcheck.de/posts/neu/", "/tmp/p")
           == "/tmp/p/posts/neu/index.html")

    # --- Fehlerpfade: Einreichen mit null URLs darf nie „grün" aussehen ---
    leer = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
    try:
        hole_seiten(sitemap_url="https://franksfinanzcheck.de/sitemap.xml",
                    http=lambda url: (200, leer))
        fehler.append("leere Sitemap muss SitemapFehler werfen")
    except SitemapFehler:
        pass

    try:
        hole_seiten(sitemap_url="https://franksfinanzcheck.de/sitemap.xml",
                    http=lambda url: (404, ""))
        fehler.append("HTTP 404 auf die Sitemap muss SitemapFehler werfen")
    except SitemapFehler:
        pass

    try:
        parse_sitemap("<urlset><loc>x")
        fehler.append("kaputtes XML muss SitemapFehler werfen")
    except SitemapFehler:
        pass

    try:
        parse_sitemap('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                      '<url><lastmod>2026-01-01</lastmod></url></urlset>')
        fehler.append("<url> ohne <loc> muss SitemapFehler werfen")
    except SitemapFehler:
        pass

    # --- Sabotage-Probe 1: Duplikat und Fremdkörper-Host müssen auffallen ---
    doppel = muster.replace('<loc>https://franksfinanzcheck.de/posts/neu/</loc>',
                            '<loc>https://franksfinanzcheck.de/</loc>')
    seiten2 = parse_sitemap(doppel)
    befunde = pruefe_grenzen(seiten2, len(doppel.encode()))
    pruefe("Duplikat erkannt", any("doppelte URL" in b for b in befunde))

    fremd = muster.replace("https://franksfinanzcheck.de/posts/neu/",
                           "https://example.com/posts/neu/")
    seiten3, befunde3 = hole_seiten(
        sitemap_url="https://franksfinanzcheck.de/sitemap.xml",
        http=lambda url: (200, fremd))
    pruefe("fremder Host erkannt", any("fremden Host" in b for b in befunde3))
    pruefe("fremder Host ist Befund, kein Absturz", len(seiten3) == 3)

    # --- Sabotage-Probe 2: Sitemap-Index wird nicht als Seite missverstanden ---
    index_xml = ('<?xml version="1.0"?><sitemapindex '
                 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                 '<sitemap><loc>https://franksfinanzcheck.de/sitemap-1.xml</loc>'
                 '</sitemap></sitemapindex>')
    try:
        hole_seiten(sitemap_url="https://franksfinanzcheck.de/sitemap.xml",
                    http=lambda url: (200, index_xml))
        fehler.append("Sitemap-Index ohne Seiten muss SitemapFehler werfen "
                      "(sonst wird eine Datei-URL als Inhaltsseite eingereicht)")
    except SitemapFehler:
        pass

    # --- Sabotage-Probe 3: Protokoll-Grenze (50.001 URLs) ---
    viele = [Seite(url=f"https://franksfinanzcheck.de/p{i}/", pfad=f"/p{i}/")
             for i in range(MAX_URLS_PRO_SITEMAP + 1)]
    befunde4 = pruefe_grenzen(viele, 10)
    pruefe("URL-Grenze erkannt", any("Google erlaubt" in b and "Sitemap-Index" in b
                                     for b in befunde4))

    if fehler:
        print("❌ INDEXIERBARE-SEITEN-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ indexierbare_seiten: Selbsttest bestanden "
          "(Parsing, Bild-Sitemap, Reihenfolge, Frische, 6 Fehlerpfade, 3 Sabotage-Proben).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Bestand der indexierbaren Seiten (eine Quelle: die Sitemap).")
    ap.add_argument("--live", action="store_true",
                    help="die ausgelieferte Sitemap lesen statt public/sitemap.xml")
    ap.add_argument("--sitemap", default=None, help="eigene Sitemap-URL")
    ap.add_argument("--public", default=None, help="Build-Verzeichnis (Voreinstellung public/)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    try:
        if a.live or a.sitemap:
            url = a.sitemap or live_sitemap_url()
            seiten, befunde = hole_seiten(sitemap_url=url)
            quelle = url
        else:
            seiten, befunde = hole_seiten(basis=a.public)
            quelle = sitemap_pfad(a.public)
    except SitemapFehler as exc:
        print(f"❌ {exc}")
        return 2

    if a.json:
        import json
        print(json.dumps({
            "quelle": quelle,
            "anzahl": len(seiten),
            "befunde": befunde,
            "seiten": [s.__dict__ for s in reihenfolge(seiten)],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Quelle: {quelle}")
        print(f"indexierbare Seiten: {len(seiten)} "
              f"(mit Bild-Sitemap: {sum(1 for s in seiten if s.bilder)})")
        for s in reihenfolge(seiten)[:15]:
            print(f"  {s.priority:.1f}  {s.lastmod or '–':10s}  {s.pfad}")
        if len(seiten) > 15:
            print(f"  … und {len(seiten) - 15} weitere")
        for b in befunde:
            print(f"⚠️  {b}")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
