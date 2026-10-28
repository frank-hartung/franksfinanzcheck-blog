#!/usr/bin/env python3
"""Social-Vorschau vor der Veröffentlichung (28.10.2026).

WARUM DIESE DATEI EXISTIERT
===========================
Die OG-Tags des Blogs sind vorhanden und werden von
`scripts/schema_seo_gate.py` auf Existenz geprüft. Geprüft wurde aber nie,
was ein Leser SIEHT: Wie schneidet X den Titel ab? Bleibt von der
Description bei LinkedIn mehr als der erste Halbsatz? Und vor allem: Fehlt
das Cover – dann ist die Karte bildlos, egal wie gut der Text ist.

Yoast Premium zeigt diese Vorschau im Editor. Hier ist sie ein eigenes,
lokales Werkzeug: Es liest die QUELLE (Frontmatter bzw. optional den
gebauten HTML-Build), bewertet Titel, Beschreibung und Bild gegen die
Kanalgrenzen aus `scripts/social_limits.py` – und rendert daraus eine
statische Seite. Kein Netz, kein Dienst, keine Konten.

WOHER DIE DATEN KOMMEN (und was daran Annäherung ist)
-----------------------------------------------------
`--quelle frontmatter` (Standard, wenn kein Build vorliegt) bildet die
OG-Tags aus dem Frontmatter nach: `seoTitle | title`, bei kurzen Titeln
zusätzlich „ | FranksFinanzcheck" (dieselbe Regel wie
layouts/_partials/seo_title.html). Das ist eine ANNAHME über das Template.
`--quelle build` liest stattdessen die tatsächlich gerenderten `<meta>`-Tags
aus `public/` – maßgeblich, wenn ein Build existiert. `auto` wählt den Build,
sobald `public/index.html` da ist, sonst das Frontmatter. Die Vorschau nennt
die benutzte Quelle in der Kopfzeile, damit niemand eine Annahme für eine
Messung hält.

BILDMASSE OHNE PILLOW
---------------------
Breite und Höhe werden aus dem Dateikopf gelesen (PNG, JPEG, GIF, WebP) –
deterministisch, ohne Abhängigkeit. Unbekannte Formate liefern `None` und
werden als „nicht messbar" gemeldet, nicht geschätzt: Ein Bild, dessen Maße
geraten sind, ist ein grünes Licht ohne Deckung.

Nutzung:
    python3 scripts/social_vorschau.py                 # Seite bauen
    python3 scripts/social_vorschau.py --quelle build
    python3 scripts/social_vorschau.py --serve         # lokal ansehen
    python3 scripts/social_vorschau.py --json          # Daten auf stdout
    python3 scripts/social_vorschau.py --selftest

Ausgabe: .cache/social-vorschau/ (index.html, vorschau.json, befunde.csv).
Die Seite ist kein Bestandteil des Blog-Deploys.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import glob
import io
import json
import mimetypes
import os
import struct
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import social_limits  # noqa: E402
from fokus_keywords import ist_live, split_frontmatter  # noqa: E402

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUSGABE = os.path.join(BLOG_DIR, ".cache", "social-vorschau")
WERKZEUG = os.path.join(BLOG_DIR, "tools", "social-vorschau")
STATIC = os.path.join(BLOG_DIR, "static")
POSTS = os.path.join(BLOG_DIR, "content", "posts")
PILLAR = os.path.join(BLOG_DIR, "content", "pillar")

SEITEN_MUSTER = ("content/posts/*/index.md", "content/posts/*.md", "content/pillar/*/index.md")


# --------------------------------------------------------------------------
#  Bildmaße aus dem Dateikopf (ohne Pillow)
# --------------------------------------------------------------------------
def bild_masse(pfad: str) -> tuple[int | None, int | None]:
    """Breite/Höhe aus PNG-, JPEG-, GIF- oder WebP-Kopf. (None, None) = unbekannt."""
    try:
        with open(pfad, "rb") as fh:
            kopf = fh.read(64 * 1024)
    except OSError:
        return None, None
    if len(kopf) < 10:
        return None, None
    # PNG: Signatur, IHDR-Chunk mit Breite/Höhe ab Byte 16
    if len(kopf) >= 24 and kopf.startswith(b"\x89PNG\r\n\x1a\n") and kopf[12:16] == b"IHDR":
        return struct.unpack(">II", kopf[16:24])
    # GIF: logische Bildschirmbreite/-höhe, Little Endian
    if kopf[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", kopf[6:10])
    # WebP: VP8 (verlustbehaftet), VP8L (verlustfrei), VP8X (erweitert)
    if kopf[:4] == b"RIFF" and kopf[8:12] == b"WEBP":
        art = kopf[12:16]
        if art == b"VP8 " and len(kopf) >= 30:
            w, h = struct.unpack("<HH", kopf[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if art == b"VP8L" and len(kopf) >= 25:
            bits = int.from_bytes(kopf[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if art == b"VP8X" and len(kopf) >= 30:
            w = int.from_bytes(kopf[24:27], "little") + 1
            h = int.from_bytes(kopf[27:30], "little") + 1
            return w, h
        return None, None
    # JPEG: Segmente durchsuchen, SOF0–SOF3/SOF5–SOF7/SOF9–SOF15 tragen die Maße
    if kopf[:2] == b"\xff\xd8":
        pos = 2
        while pos + 9 < len(kopf):
            if kopf[pos] != 0xFF:
                pos += 1
                continue
            marker = kopf[pos + 1]
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                pos += 2
                continue
            laenge = struct.unpack(">H", kopf[pos + 2:pos + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                hoehe, breite = struct.unpack(">HH", kopf[pos + 5:pos + 9])
                return breite, hoehe
            if laenge < 2:
                break
            pos += 2 + laenge
    return None, None


# --------------------------------------------------------------------------
#  Quelle: Frontmatter oder gebauter Build
# --------------------------------------------------------------------------
class MetaLeser(HTMLParser):
    """Liest title/canonical/og:*/twitter:*-Tags aus einer gebauten Seite."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.titel = ""
        self.canonical = ""
        self.robots = ""
        self.weiterleitung = False
        self._im_titel = False
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            return
        if tag == "meta":
            schluessel = (a.get("property") or a.get("name") or "").lower()
            wert = a.get("content") or ""
            if schluessel and schluessel not in self.meta:
                self.meta[schluessel] = wert
            if schluessel == "robots":
                self.robots = wert.lower()
            if (a.get("http-equiv") or "").lower() == "refresh":
                self.weiterleitung = True
        elif tag == "title":
            self._im_titel = True
        elif tag == "link" and "canonical" in (a.get("rel") or "").split():
            self.canonical = a.get("href") or ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._im_titel = False

    def handle_data(self, data):
        if self._im_titel:
            self.titel += data


def _basis(root: str) -> str:
    import tomllib
    with open(os.path.join(root, "hugo.toml"), "rb") as fh:
        return str(tomllib.load(fh).get("baseURL") or "https://franksfinanzcheck.de/").rstrip("/") + "/"


def _og_titel(titel: str, seo_titel: str | None, marke: str = "FranksFinanzcheck") -> str:
    """Nachbildung von layouts/_partials/seo_title.html (bei Quelle=frontmatter)."""
    if seo_titel:
        return seo_titel
    return f"{titel} | {marke}" if len(titel) < 40 else titel


def seiten_aus_frontmatter(root: str, heute: str | None = None) -> tuple[list[dict], str]:
    basis = _basis(root)
    static = os.path.join(root, "static")
    heute = heute or os.environ.get("FF_HEUTE") or date.today().isoformat()
    seiten: list[dict] = []
    for muster in SEITEN_MUSTER:
        for pfad in sorted(glob.glob(os.path.join(root, muster))):
            if os.path.basename(pfad) == "_index.md":
                continue
            with open(pfad, encoding="utf-8") as fh:
                fm, _ = split_frontmatter(fh.read())
            if not fm or not ist_live(fm, heute):
                continue
            sektion = "pillar" if os.sep + "pillar" + os.sep in pfad else "posts"
            slug = os.path.basename(os.path.dirname(pfad)) if os.path.basename(pfad) == "index.md" \
                else os.path.basename(pfad)[:-3]
            titel = str(fm.get("title") or "")
            beschreibung = str(fm.get("description") or "")
            cover = fm.get("cover") if isinstance(fm.get("cover"), dict) else {}
            bild = str(cover.get("image") or "")
            if bild and cover.get("relative"):
                bild_abs = basis + sektion + "/" + slug + "/" + bild.lstrip("/")
            elif bild:
                bild_abs = basis + bild.lstrip("/")
            else:
                bild_abs = ""
            seiten.append({
                "slug": slug,
                "sektion": sektion,
                "pfad": os.path.relpath(pfad, root),
                "url": f"{basis}{sektion}/{slug}/",
                "titel": titel,
                "titel_og": _og_titel(titel, fm.get("seoTitle")),
                "beschreibung": beschreibung,
                "bild": {"url": bild_abs, "alt": str(cover.get("alt") or "")},
                "_bild_datei": os.path.join(static, bild.lstrip("/")) if bild else "",
            })
    return seiten, "Frontmatter (og:title aus seo_title.html nachgebildet)"


def _datei_aus_url(root: str, basis: str, url: str) -> str:
    """Lokale Datei zu einer Marken-URL – nur innerhalb von static/."""
    teile = urlsplit(url)
    if not teile.netloc.endswith("franksfinanzcheck.de"):
        return ""
    rel = unquote(teile.path).lstrip("/")
    pfad = os.path.join(root, "static", rel)
    return pfad if os.path.isfile(pfad) else ""


def seiten_aus_build(root: str, heute: str | None = None) -> tuple[list[dict], str]:
    public = os.path.join(root, "public")
    basis = _basis(root)
    seiten: list[dict] = []
    for pfad in sorted(glob.glob(os.path.join(public, "**", "index.html"), recursive=True)):
        rel = os.path.relpath(pfad, public)
        if rel.startswith(("tags" + os.sep, "categories" + os.sep)) or rel.startswith("page" + os.sep):
            continue
        with open(pfad, encoding="utf-8") as fh:
            leser = MetaLeser(fh.read())
        if leser.weiterleitung or "noindex" in leser.robots:
            continue
        url = leser.canonical or (basis + rel.replace(os.sep, "/").replace("index.html", ""))
        bild_url = leser.meta.get("og:image", "")
        seiten.append({
            "slug": os.path.basename(os.path.dirname(pfad)) or "startseite",
            "sektion": "build",
            "pfad": os.path.relpath(pfad, root),
            "url": url,
            "titel": leser.titel,
            "titel_og": leser.meta.get("og:title") or leser.titel,
            "beschreibung": leser.meta.get("og:description", ""),
            "bild": {"url": bild_url, "alt": leser.meta.get("og:image:alt", "")},
            "_bild_datei": _datei_aus_url(root, basis, bild_url) if bild_url else "",
            "_og_bild_fehlt": not bild_url,
        })
    return seiten, "geborter Build (meta og:* direkt gelesen)"


def bewerte_seite(seite: dict, ausgabe: str) -> dict:
    titel = seite.get("titel_og") or ""
    beschreibung = seite.get("beschreibung") or ""
    breite = hoehe = groesse = None
    datei = seite.pop("_bild_datei", "")
    if datei:
        breite, hoehe = bild_masse(datei)
        try:
            groesse = os.path.getsize(datei)
        except OSError:
            groesse = None
    befunde = social_limits.text_befunde(titel, beschreibung)
    if seite.get("_og_bild_fehlt"):
        befunde += social_limits.bild_befunde(None, None)
    elif seite["bild"]["url"]:
        if datei and not os.path.isfile(datei):
            befunde.append({"kanal": "*", "code": "social-bild-datei", "schwere": "P2",
                            "detail": f"og:image zeigt auf {seite['bild']['url']}, "
                                      f"die Datei fehlt aber in static/.",
                            "massnahme": "Bildpfad korrigieren oder Datei ergänzen."})
        befunde += social_limits.bild_befunde(breite, hoehe, groesse)
    else:
        befunde += social_limits.bild_befunde(None, None)
    if seite["bild"]["url"] and not seite["bild"].get("alt"):
        befunde.append({"kanal": "*", "code": "social-bild-alt", "schwere": "P3",
                        "detail": "og:image ohne og:image:alt.",
                        "massnahme": "`cover.alt` setzen – Screenreader und Pinterest nennen das Bild damit."})
    seite = {k: v for k, v in seite.items() if not k.startswith("_")}
    seite.update({
        "bild_breite": breite, "bild_hoehe": hoehe, "bild_groesse": groesse,
        "bild_datei": (os.path.relpath(datei, ausgabe) if datei else ""),
        "befunde": befunde,
        "schwere": min((b["schwere"] for b in befunde), default=""),
    })
    return seite


def sammle(root: str = BLOG_DIR, quelle: str = "auto", ausgabe: str = AUSGABE,
           heute: str | None = None) -> dict:
    """Baut den vollständigen Datensatz für Bericht, CSV und Vorschau."""
    build_da = os.path.isfile(os.path.join(root, "public", "index.html"))
    gewaehlt = quelle
    if quelle == "auto":
        gewaehlt = "build" if build_da else "frontmatter"
    if gewaehlt == "build" and not build_da:
        raise ValueError("--quelle build verlangt einen Hugo-Build (public/index.html fehlt).")
    seiten, herkunft = (seiten_aus_build(root, heute) if gewaehlt == "build"
                        else seiten_aus_frontmatter(root, heute))
    fertig = [bewerte_seite(seite, ausgabe) for seite in seiten]
    fertig.sort(key=lambda s: ({"P1": 0, "P2": 1, "P3": 2, "": 3}[s["schwere"]], s["url"]))
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quelle": gewaehlt,
        "herkunft": herkunft,
        "basis": _basis(root),
        "stand": social_limits.STAND,
        "kanaele": social_limits.kanaele(),
        "bild_regeln": {
            "min": [social_limits.BILD_MIN_BREITE, social_limits.BILD_MIN_HOEHE],
            "ideal": [social_limits.BILD_IDEAL_BREITE, social_limits.BILD_IDEAL_HOEHE],
            "max_bytes": social_limits.BILD_MAX_BYTES,
            "pin": list(social_limits.PIN_ZIEL),
        },
        "pages": fertig,
        "summary": social_limits.zusammenfassung(fertig),
    }


# --------------------------------------------------------------------------
#  Ausgabe
# --------------------------------------------------------------------------
def _csv_sicher(zeilen: list[list]) -> str:
    puffer = io.StringIO(newline="")
    schreiber = csv.writer(puffer)
    for zeile in zeilen:
        schreiber.writerow([
            "'" + str(w) if str(w).lstrip().startswith(("=", "+", "-", "@")) else w
            for w in zeile
        ])
    return puffer.getvalue()


def schreibe(daten: dict, ausgabe: str = AUSGABE) -> dict[str, str]:
    os.makedirs(ausgabe, exist_ok=True)
    with open(os.path.join(WERKZEUG, "index.html"), encoding="utf-8") as fh:
        vorlage = fh.read()
    # `<` `>` `&` maskieren: Der Datensatz steht in einem <script>-Block.
    nutzlast = (json.dumps(daten, ensure_ascii=False)
                .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    pfade = {
        "html": os.path.join(ausgabe, "index.html"),
        "json": os.path.join(ausgabe, "vorschau.json"),
        "csv": os.path.join(ausgabe, "befunde.csv"),
    }
    with open(pfade["html"], "w", encoding="utf-8") as fh:
        fh.write(vorlage.replace("/*VORSCHAU_DATA*/", nutzlast))
    for name in ("app.js", "style.css"):
        with open(os.path.join(WERKZEUG, name), encoding="utf-8") as quelle, \
                open(os.path.join(ausgabe, name), "w", encoding="utf-8") as ziel:
            ziel.write(quelle.read())
    with open(pfade["json"], "w", encoding="utf-8") as fh:
        fh.write(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")
    zeilen = [["Seite", "URL", "Kanal", "Prüfung", "Schwere", "Befund", "Maßnahme"]]
    for seite in daten["pages"]:
        for b in seite["befunde"]:
            zeilen.append([seite["slug"], seite["url"], b["kanal"], b["code"],
                           b["schwere"], b["detail"], b["massnahme"]])
    with open(pfade["csv"], "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_csv_sicher(zeilen))
    return pfade


def bediene(daten: dict, ausgabe: str, bind: str, port: int) -> None:
    """Kleiner lokaler Server: Vorschau unter /, Bilder aus dem Repo.

    Nötig, weil die Vorschau ihre Cover aus `static/` lädt. Die Pfade in der
    Seite sind relativ zu `.cache/social-vorschau/` – für `file://` und für
    diesen Server gleichermaßen. Ausgeliefert wird ausschließlich innerhalb
    des Repos (Pfadprüfung), und der Server ist kein Admin-Backend.
    """
    from functools import partial
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (Standardname)
            pfad = unquote(urlsplit(self.path).path)
            if pfad in ("/", "/index.html"):
                datei = os.path.join(ausgabe, "index.html")
            else:
                kandidaten = [os.path.join(BLOG_DIR, pfad.lstrip("/")),
                              os.path.join(ausgabe, pfad.lstrip("/"))]
                datei = next((k for k in kandidaten if os.path.isfile(k)), "")
            ziel = os.path.realpath(datei) if datei else ""
            if not ziel or not ziel.startswith(os.path.realpath(BLOG_DIR)):
                self.send_error(404, "Nicht gefunden")
                return
            typ = mimetypes.guess_type(ziel)[0] or "application/octet-stream"
            with open(ziel, "rb") as fh:
                inhalt = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{typ}; charset=utf-8" if typ.startswith("text/") else typ)
            self.send_header("Content-Length", str(len(inhalt)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(inhalt)

        def log_message(self, fmt, *args):  # ruhig halten: keine Pfade im Terminal
            return

    server = HTTPServer((bind, port), partial(Handler))
    print(f"Social-Vorschau: http://{'127.0.0.1' if bind == '0.0.0.0' else bind}:{port}/")
    print("Beenden mit Strg+C. Es werden keine Daten übertragen.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


# --------------------------------------------------------------------------
#  Selbsttest
# --------------------------------------------------------------------------
def selftest() -> int:
    import tempfile

    fails: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        # PNG-Kopf mit 1200×630
        png = os.path.join(tmp, "a.png")
        with open(png, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
                     + struct.pack(">II", 1200, 630) + b"\x08\x02\x00\x00\x00")
        if bild_masse(png) != (1200, 630):
            fails.append(f"PNG-Maße falsch: {bild_masse(png)}")
        # JPEG-Kopf: SOI, APP0-Segment, SOF0 mit 800×600
        jpg = os.path.join(tmp, "a.jpg")
        with open(jpg, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                     + b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", 600, 800)
                     + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01")
        if bild_masse(jpg) != (800, 600):
            fails.append(f"JPEG-Maße falsch: {bild_masse(jpg)}")
        # GIF und WebP
        gif = os.path.join(tmp, "a.gif")
        with open(gif, "wb") as fh:
            fh.write(b"GIF89a" + struct.pack("<HH", 400, 300) + b"\x00\x00\x00")
        if bild_masse(gif) != (400, 300):
            fails.append(f"GIF-Maße falsch: {bild_masse(gif)}")
        webp = os.path.join(tmp, "a.webp")
        with open(webp, "wb") as fh:
            fh.write(b"RIFF" + struct.pack("<I", 30) + b"WEBP" + b"VP8X"
                     + b"\x0a\x00\x00\x00" + b"\x00" * 4  # Flags + Reserved
                     + (1200 - 1).to_bytes(3, "little")
                     + (630 - 1).to_bytes(3, "little"))
        if bild_masse(webp) != (1200, 630):
            fails.append(f"WebP-Maße falsch: {bild_masse(webp)}")
        # Unbekanntes Format wird NICHT geschätzt
        kaputt = os.path.join(tmp, "x.bin")
        with open(kaputt, "wb") as fh:
            fh.write(b"kein bild, nur text" * 4)
        if bild_masse(kaputt) != (None, None):
            fails.append("unbekanntes Format liefert erfundene Maße")
        if bild_masse(os.path.join(tmp, "fehlt.png")) != (None, None):
            fails.append("fehlende Datei liefert Maße")

        # og:titel-Regel entspricht seo_title.html
        if _og_titel("Kurz", None) != "Kurz | FranksFinanzcheck":
            fails.append("kurzer Titel bekommt keinen Marken-Zusatz")
        if _og_titel("K" * 40, None) != "K" * 40:
            fails.append("Titel ab 40 Zeichen bekommt fälschlich einen Zusatz")
        if _og_titel("Kurz", "Eigener SEO-Titel") != "Eigener SEO-Titel":
            fails.append("seoTitle wird nicht bevorzugt")

        # Mini-Repo: Frontmatter-Quelle, Bild vorhanden, Bewertung greift
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "content", "posts", "artikel"), exist_ok=True)
        os.makedirs(os.path.join(repo, "static", "images"), exist_ok=True)
        with open(os.path.join(repo, "hugo.toml"), "w", encoding="utf-8") as fh:
            fh.write('baseURL = "https://franksfinanzcheck.de/"\n')
        with open(os.path.join(repo, "static", "images", "cover.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
                     + struct.pack(">II", 1200, 630) + b"\x08\x02\x00\x00\x00")
        with open(os.path.join(repo, "content", "posts", "artikel", "index.md"),
                  "w", encoding="utf-8") as fh:
            fh.write('---\ntitle: "Strom sparen im Haushalt"\ndescription: "Strom sparen: '
                     'Stromfresser finden, Tarife vergleichen, Abschläge prüfen."\n'
                     'date: 2026-09-01\ndraft: false\ncover:\n  image: "images/cover.png"\n'
                     '  alt: "Stromzähler"\n---\n\nText.\n')
        daten = sammle(repo, "frontmatter", os.path.join(tmp, "out"), heute="2026-10-28")
        seite = daten["pages"][0]
        if daten["quelle"] != "frontmatter":
            fails.append("Quelle nicht als Frontmatter erkannt")
        if seite["bild_breite"] != 1200 or seite["bild_hoehe"] != 630:
            fails.append(f"Bildmaße nicht übernommen: {seite['bild_breite']}×{seite['bild_hoehe']}")
        if seite["befunde"]:
            fails.append(f"saubere Seite erzeugt Befunde: {seite['befunde']}")
        if not seite["bild_datei"].endswith(os.path.join("static", "images", "cover.png")):
            fails.append(f"relativer Bildpfad falsch: {seite['bild_datei']}")
        # Draft wird nicht angezeigt
        with open(os.path.join(repo, "content", "posts", "artikel", "index.md"),
                  "w", encoding="utf-8") as fh:
            fh.write('---\ntitle: "Entwurf"\ndescription: "x"\ndate: 2026-09-01\n'
                     'draft: true\n---\n\nText.\n')
        if sammle(repo, "frontmatter", os.path.join(tmp, "out"), heute="2026-10-28")["pages"]:
            fails.append("Draft erscheint in der Vorschau")
        # Fehlendes Bild ist ein P1-Befund
        with open(os.path.join(repo, "content", "posts", "artikel", "index.md"),
                  "w", encoding="utf-8") as fh:
            fh.write('---\ntitle: "Ohne Bild"\ndescription: "Beschreibung ohne Cover, '
                     'aber lang genug für die Kartenprüfung der Kanäle."\n'
                     'date: 2026-09-01\ndraft: false\n---\n\nText.\n')
        ohne = sammle(repo, "frontmatter", os.path.join(tmp, "out"), heute="2026-10-28")["pages"][0]
        if "social-bild" not in {b["code"] for b in ohne["befunde"]}:
            fails.append("fehlendes Bild wird nicht gemeldet")
        if ohne["schwere"] != "P1":
            fails.append(f"fehlendes Bild ergibt nicht P1, sondern {ohne['schwere']!r}")
        # Build-Modus: gerenderte og:*-Tags sind maßgeblich, nicht die Annahme
        public = os.path.join(repo, "public", "posts", "artikel")
        os.makedirs(public, exist_ok=True)
        with open(os.path.join(repo, "public", "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<html lang="de"><head><title>Start</title></head></html>')
        with open(os.path.join(public, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<html lang="de"><head><title>Gerendert</title>'
                     '<link rel="canonical" href="https://franksfinanzcheck.de/posts/artikel/">'
                     '<meta property="og:title" content="Gerenderter Titel">'
                     '<meta property="og:description" content="Gerenderte Beschreibung.">'
                     '<meta property="og:image" content="https://franksfinanzcheck.de/images/cover.png">'
                     '<meta property="og:image:alt" content="Alt">'
                     '</head><body><h1>Gerendert</h1></body></html>')
        # Der Entwurf von oben steht noch im Frontmatter – der Build ignoriert ihn.
        gebaut = sammle(repo, "auto", os.path.join(tmp, "out-build"), heute="2026-10-28")
        if gebaut["quelle"] != "build":
            fails.append("auto wählt bei vorhandenem Build nicht den Build")
        gebaut_seite = next((p for p in gebaut["pages"] if p["slug"] == "artikel"), None)
        if gebaut_seite is None or gebaut_seite["titel_og"] != "Gerenderter Titel":
            fails.append("Build-Modus liest og:title nicht")

        # Ausgabe: HTML maskiert den Datensatz, CSV neutralisiert Formeln
        with open(os.path.join(WERKZEUG, "index.html"), encoding="utf-8") as fh:
            if "/*VORSCHAU_DATA*/" not in fh.read():
                fails.append("Vorlage enthält den Platzhalter nicht")
        daten["pages"][0]["titel_og"] = "</script><img src=x onerror=alert(1)>"
        pfade = schreibe(daten, os.path.join(tmp, "out"))
        with open(pfade["html"], encoding="utf-8") as fh:
            html = fh.read()
        if "</script><img" in html:
            fails.append("Datensatz bricht aus dem <script>-Block aus")
        if "sauberkeit" in html:
            fails.append("unerwarteter Inhalt")
        # CSV: Formel-Anfänge werden neutralisiert, echte Befunde stehen drin.
        daten2 = json.loads(json.dumps(daten))
        daten2["pages"][0]["slug"] = "=HYPERLINK(\"http://x\")"
        daten2["pages"][0]["befunde"] = [{"kanal": "*", "code": "social-test",
                                          "schwere": "P3", "detail": "=1+1",
                                          "massnahme": "m"}]
        pfade2 = schreibe(daten2, os.path.join(tmp, "out2"))
        with open(pfade2["csv"], encoding="utf-8-sig") as fh:
            csv_text = fh.read()
        if "'=HYPERLINK" not in csv_text:
            fails.append("CSV neutralisiert Formel-Anfänge nicht")
        if "Prüfung" not in csv_text:
            fails.append("CSV hat keinen Kopf")
        if not os.path.isfile(os.path.join(tmp, "out", "app.js")):
            fails.append("app.js nicht mitkopiert")
    if fails:
        for f in fails:
            print(f"❌ Social-Vorschau: {f}")
        return 2
    print("✅ Social-Vorschau: Selbsttest bestanden – PNG/JPEG/GIF/WebP-Maße, "
          "og:titel-Regel, Frontmatter-Quelle, Draft-Ausschluss, P1 bei fehlendem "
          "Bild, Script-Escaping und CSV-Sicherheit sind belegt.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quelle", choices=("auto", "frontmatter", "build"), default="auto")
    parser.add_argument("--output", default=AUSGABE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4175)
    parser.add_argument("--root", default=BLOG_DIR)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.json:
        with contextlib.redirect_stdout(sys.stderr):
            if selftest() != 0:
                return 2
    elif selftest() != 0:
        return 2

    ausgabe = os.path.abspath(args.output)
    for unsicher in ("public", "static", "content", "layouts", ".git"):
        if ausgabe == os.path.join(BLOG_DIR, unsicher) or \
                ausgabe.startswith(os.path.join(BLOG_DIR, unsicher) + os.sep):
            print(f"❌ Ausgabe gehört nicht in {unsicher}/.", file=sys.stderr)
            return 2
    try:
        daten = sammle(args.root, args.quelle, ausgabe)
    except (OSError, ValueError) as fehler:
        print(f"❌ Social-Vorschau: {fehler}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(daten, ensure_ascii=False, indent=1))
        return 0
    pfade = schreibe(daten, ausgabe)
    s = daten["summary"]
    print(f"Social-Vorschau: {s['seiten']} Seiten, {s['ohne_bild']} ohne Bild, "
          f"{s['befunde']} Befunde (Quelle: {daten['quelle']}).")
    print(f"Öffnen: {pfade['html']}")
    if args.serve:
        bediene(daten, ausgabe, args.bind, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
