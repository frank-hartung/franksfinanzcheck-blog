#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LINKTEXT- UND ALT-WACHE (SEO-Sicht auf den fertigen Build).

WARUM ES DIESE WACHE GIBT (27.10.2026)
======================================
Der Seobility-Check der Startseite (Standard, ohne JavaScript) meldete
zwei Befunde, die keine Geschmacksfrage sind, sondern messbarer Verlust:

  · „8 Links haben keinen Linktext oder nur Inhalt in Alt- und
     Titelattributen." Die Trefferflächen der Artikelkarten waren
     absolut positionierte LEERE `<a class="entry-link">` mit
     `aria-label`. Barrierefrei war das zulässig (die Wache
     `a11y_audit.py` überspringt solche Overlays ausdrücklich) –
     für Suchmaschinen war es ein Link ohne Ankertext. Ein interner
     Link, dessen Text nur im Attribut steht, verschenkt genau das
     Signal, für das man intern verlinkt.
  · „1 Bild hat kein Alt-Attribut." Das Markenlogo trug `alt=""`
     (dekorativ korrekt, weil der Link zusätzlich sichtbaren Text
     hatte) – aber der Markenname fehlte damit im Linknamen und im
     Bildindex.

Beides ist in derselben Nacht geheilt worden (Titel trägt den Anker,
Overlay per `::after`; Logo trägt `alt="FranksFinanzcheck"`). Diese
Wache verhindert den Rückfall – an genau der Stelle, an der beide
Defekte entstanden sind: im gerenderten HTML, nicht im Template.

WAS GEPRÜFT WIRD (jede HTML-Datei in `public/`)
===============================================
  L1  LINK OHNE TEXT     `<a href>` (auch `<area href>`) hat keinen
                         sichtbaren Text. Bilder im Link zählen nur mit
                         NICHT-leerem `alt`. `aria-label`/`title` zählen
                         ausdrücklich NICHT – für Crawler ist das kein
                         Ankertext (genau der Seobility-Befund).
                         Ausnahmen (bewusst, nicht still):
                           · `data-ff-linktext-frei` am Link (begründet
                             im Template) – z. B. eine rein visuelle
                             Klickfläche, die eine Wache abdeckt
                           · `<a>` OHNE `href` (Sprungziel wie
                             `<a id="partner-kennzeichnung"></a>`) – kein
                             Link, sondern ein Anker
  L2  BILD OHNE ALT      `<img>` ohne `alt`-Attribut. `alt=""` ist nach
                         HTML5 „dekorativ" und deshalb KEIN Fehler –
                         es wird unter L3 als Hinweis gezählt, damit
                         niemand versehentlich Inhaltsbilder versteckt.
  L3  HINWEIS            Zählung von `alt=""` (dekorativ) und von
                         Ankertexten über `LANGTEXT_GRENZE` (60) Zeichen.
                         Beides beendet den Lauf nicht: Ein leerer
                         Alt-Text ist bei Schmuck korrekt, und ein
                         etwas längerer Ankertext ist eine Abwägung.
  L4  KARTENLINK ZU LANG Indexierbare Seite, Kartenlink (Klasse enthält
                         card/karte/tile/entry-title), Ankertext über
                         `LANGTEXT_FEHLER` (80) Zeichen – Fehler. Genau
                         diese Form war der Seobility-Befund „Linktexte
                         zu lang": eine Karte, die Titel, Anriss, Zähler
                         und CTA als EINEN Link trug. Redaktionelle Links
                         (Fließtext, Inhaltsverzeichnis, Quellenangabe)
                         sind ausgenommen, ebenso nicht indexierbare
                         Seiten (z. B. /go/-Weiterleitungen mit
                         noindex,nofollow).

Aufruf
======
  python3 scripts/linktext_wache.py                     # prüft public/
  python3 scripts/linktext_wache.py --public tmp/subdir
  python3 scripts/linktext_wache.py --selftest          # Sabotage-Proben
  python3 scripts/linktext_wache.py --json              # Maschinenlesbar

Exit: 0 sauber · 1 Befund · 2 Selbsttest-Sabotage nicht erkannt

Nur Python-Standardbibliothek, rein lesend, keine Netzverbindung.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
# Ab hier ist ein Ankertext ein HINWEIS (Abwägung: Karten mit Anriss,
# Zitat-Titel, Pagination mit Artikeltitel sind legitim länger).
LANGTEXT_GRENZE = 60
# Ab hier ist ein Ankertext ein FEHLER – aber nur auf indexierbaren Seiten.
# 80 Zeichen decken jeden echten Kartentitel ab und liegen weit unter den
# 115–158-Zeichen-Kartenlinks, die der Seobility-Check vom 27.10.2026
# gemeldet hat (Titel + Beschreibung + Zähler + CTA in einem Link).
LANGTEXT_FEHLER = 80
# L4 gilt für KARTEN-LINKS, nicht für redaktionelle Links im Fließtext.
# Der Grund ist die Fehlerklasse: Ein langer Ankertext entsteht im Template,
# wenn eine ganze Karte (Titel + Anriss + Zähler + CTA) EIN Link ist – genau
# der Seobility-Befund vom 27.10.2026. Ein Link MITTEN im Satz, ein
# Inhaltsverzeichnis-Sprungziel oder eine Quellenangabe darf dagegen lang
# sein: dort ist der Text die Aussage, nicht das Etikett eines Ziels.
KARTEN_KLASSEN = re.compile(
    r"(?:^|-)(?:card|karte|tile|entry-title)(?:$|__|-)")


def ist_kartenlink(eintrag: dict) -> bool:
    for klasse in (eintrag["klasse"] or "").split():
        if KARTEN_KLASSEN.search(klasse):
            return True
    return False

# Elemente, deren Inhalt nie sichtbarer Text eines Links ist.
# `noscript` steht bewusst NICHT darin: Wer ohne JavaScript crawlt, sieht
# genau diesen Inhalt – die Links darin tragen ihren Text.
NICHT_TEXT = {"script", "style", "template", "svg"}
# Leerraum-Varianten, die einen Linktext nicht tragen.
LEERLAUF = re.compile(r"[\s\u00a0\u200b\u202f]+")


class LinkSammler(HTMLParser):
    """Sammelt Links samt Text und Bilder samt alt-Attribut."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self.bilder: list[dict] = []
        self.robots: list[str] = []
        self._stapel: list[dict] = []
        self._stumm = 0

    # -- Hilfen -------------------------------------------------------
    def _text_anhaengen(self, text: str) -> None:
        if self._stumm:
            return
        for eintrag in self._stapel:
            eintrag["text"].append(text)

    def _bild_anhaengen(self, attrs: dict) -> None:
        # Ein Bild im Link trägt den Linktext nur mit nicht-leerem alt.
        for eintrag in self._stapel:
            eintrag["bilder"].append(attrs.get("alt") or "")
        self.bilder.append(attrs)

    # -- Parser-Callbacks ---------------------------------------------
    def handle_starttag(self, tag, attrs):
        attr = {k: (v if v is not None else "") for k, v in attrs}
        if tag in NICHT_TEXT:
            self._stumm += 1
        if tag == "meta" and (attr.get("name") or "").lower() == "robots":
            self.robots.append(attr.get("content") or "")
        if tag in {"a", "area"}:
            eintrag = {
                "tag": tag,
                "href": attr.get("href"),
                "text": [],
                "bilder": [],
                "frei": "data-ff-linktext-frei" in attr,
                "aria": attr.get("aria-label") or attr.get("title") or "",
                "klasse": attr.get("class") or "",
            }
            self._stapel.append(eintrag)
            self.links.append(eintrag)
        elif tag == "img":
            self._bild_anhaengen(attr)

    def handle_startendtag(self, tag, attrs):
        if tag == "img":
            self._bild_anhaengen({k: (v if v is not None else "") for k, v in attrs})
        elif tag in {"a", "area"}:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in NICHT_TEXT and self._stumm:
            self._stumm -= 1
        if tag in {"a", "area"} and self._stapel:
            self._stapel.pop()

    def handle_data(self, data):
        self._text_anhaengen(data)


def linktext(eintrag: dict) -> str:
    text = LEERLAUF.sub(" ", "".join(eintrag["text"])).strip()
    if text:
        return text
    return " ".join(alt for alt in eintrag["bilder"] if alt.strip())


def pruefe_html(html: str) -> tuple[list[str], dict]:
    """Liefert (Befunde, Statistik) für ein HTML-Dokument."""
    sammler = LinkSammler()
    sammler.feed(html)
    befuende: list[str] = []
    statistik = {"links": 0, "ohne_text": 0, "lang": 0, "zu_lang": 0, "alt_leer": 0, "bilder": 0}
    robots = " ".join(sammler.robots).lower()
    indexierbar = "noindex" not in robots

    for eintrag in sammler.links:
        if not eintrag["href"]:
            continue  # Sprungziel, kein Link
        statistik["links"] += 1
        text = linktext(eintrag)
        if not text:
            if eintrag["frei"]:
                continue
            statistik["ohne_text"] += 1
            ziel = eintrag["href"][:70]
            hinweis = f" (aria-label/title: „{eintrag['aria'][:40]}“)" if eintrag["aria"] else ""
            befuende.append(f"L1: Link ohne Linktext → {ziel}{hinweis}")
        elif len(text) > LANGTEXT_GRENZE:
            statistik["lang"] += 1
            if (len(text) > LANGTEXT_FEHLER and indexierbar
                    and ist_kartenlink(eintrag)):
                statistik["zu_lang"] += 1
                befuende.append(
                    f"L4: Ankertext mit {len(text)} Zeichen (Grenze {LANGTEXT_FEHLER}) → "
                    f"„{text[:60]}…“ ({eintrag['href'][:50]})")

    for bild in sammler.bilder:
        statistik["bilder"] += 1
        if "alt" not in bild:
            befuende.append(f"L2: Bild ohne alt-Attribut → {(bild.get('src') or '')[:70]}")
        elif not (bild.get("alt") or "").strip():
            statistik["alt_leer"] += 1

    return befuende, statistik


def sammle_html(public: Path) -> list[Path]:
    return sorted(p for p in public.rglob("*.html") if p.is_file())


def pruefe_build(public: Path) -> dict:
    ergebnis = {"public": str(public), "seiten": 0, "befunde": [], "statistik": {}}
    if not public.is_dir():
        ergebnis["befunde"].append(f"Build-Verzeichnis fehlt: {public}")
        return ergebnis
    summe = {"links": 0, "ohne_text": 0, "lang": 0, "zu_lang": 0, "alt_leer": 0, "bilder": 0}
    for datei in sammle_html(public):
        rel = datei.relative_to(public).as_posix()
        try:
            html = datei.read_text(encoding="utf-8", errors="ignore")
        except OSError as fehler:
            ergebnis["befunde"].append(f"{rel}: nicht lesbar ({fehler})")
            continue
        ergebnis["seiten"] += 1
        befuende, statistik = pruefe_html(html)
        for schluessel, wert in statistik.items():
            summe[schluessel] += wert
        for befund in befuende:
            ergebnis["befunde"].append(f"{rel}: {befund}")
    ergebnis["statistik"] = summe
    return ergebnis


# ---------------------------------------------------------------- Selbsttest
GUTES_HTML = """<!doctype html><html lang="de"><body>
<main>
  <h1>Seite</h1>
  <a href="/artikel/">Artikel lesen</a>
  <a href="/bild/"><img src="/x.jpg" alt="Beschreibung"></a>
  <a id="sprungziel"></a>
  <a href="/frei/" data-ff-linktext-frei aria-label="Karte"></a>
  <img src="/deko.svg" alt="">
</main></body></html>"""

SCHLECHTES_HTML = """<!doctype html><html lang="de"><body>
<main>
  <h1>Seite</h1>
  <a class="entry-link" aria-label="Weiterlesen: Karte" href="/karte/"></a>
  <a href="/nur-icon/"><svg viewBox="0 0 1 1"><path d="M0 0"></path></svg></a>
  <img src="/ohne-alt.jpg">
</main></body></html>"""


def selftest() -> int:
    fehler = 0
    befuende, _ = pruefe_html(GUTES_HTML)
    if befuende:
        print("SELFTEST FEHLER: sauberes Dokument erzeugt Befunde:", befuende)
        fehler += 1
    befuende, statistik = pruefe_html(SCHLECHTES_HTML)
    erwartet = [
        any(b.startswith("L1:") and "/karte/" in b for b in befuende),
        any(b.startswith("L1:") and "/nur-icon/" in b for b in befuende),  # SVG ist kein Text
        any(b.startswith("L2:") and "/ohne-alt.jpg" in b for b in befuende),
    ]
    if not all(erwartet):
        print("SELFTEST FEHLER: Sabotageproben nicht erkannt:", befuende)
        fehler += 1
    if statistik["ohne_text"] != 2 or statistik["bilder"] != 1:
        print("SELFTEST FEHLER: Statistik falsch:", statistik)
        fehler += 1
    # L4: Ein Kartenlink über der Fehlergrenze muss auffallen, derselbe
    # Text als redaktioneller Link (ohne Karten-Klasse) nicht.
    langer_text = "Ein Satz, der so lang ist, dass er als Ankertext nichts mehr über das Ziel sagt " * 2
    karte = f'<main><h1>T</h1><a class="ff-topic-card__title-link" href="/x/">{langer_text}</a></main>'
    if not any(b.startswith("L4:") for b in pruefe_html(karte)[0]):
        print("SELFTEST FEHLER: L4 erkennt einen zu langen Kartenlink nicht.")
        fehler += 1
    redaktion = f'<main><h1>T</h1><a class="ff-quellen__link" href="/x/">{langer_text}</a></main>'
    if pruefe_html(redaktion)[0]:
        print("SELFTEST FEHLER: L4 bestraft einen redaktionellen Quellenlink.")
        fehler += 1
    # aria-label allein darf NICHT als Linktext gelten (Seobility-Kern).
    if not any("aria-label" in b for b in befuende):
        print("SELFTEST FEHLER: aria-label wurde als Linktext gewertet.")
        fehler += 1
    if fehler:
        print(f"❌ Selbsttest: {fehler} Probe(n) nicht bestanden.")
        return 2
    print("✅ Selbsttest: L1 (Linktext inkl. SVG-Falle), L2 (alt) und L4 (Kartenlink-Länge) sind scharf.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--public", type=Path, default=PUBLIC_DIR)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    ergebnis = pruefe_build(Path(args.public))
    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 1 if ergebnis["befunde"] else 0

    print("== Linktext-/Alt-Wache –", ergebnis["public"])
    if not ergebnis["befunde"]:
        print("  ✅ L1: kein Link ohne Linktext")
        print("  ✅ L2: jedes Bild trägt ein alt-Attribut")
        print(f"  ✅ L4: kein Ankertext über {LANGTEXT_FEHLER} Zeichen auf indexierbaren Seiten")
    else:
        for befund in ergebnis["befunde"][:40]:
            print("  ❌", befund)
        if len(ergebnis["befunde"]) > 40:
            print(f"  … und {len(ergebnis['befunde']) - 40} weitere")
    s = ergebnis["statistik"]
    print(f"  Seiten: {ergebnis['seiten']} · Links: {s.get('links', 0)} · Bilder: {s.get('bilder', 0)}")
    print(f"  Hinweis L3: {s.get('alt_leer', 0)} dekorative Bilder mit alt=\"\" · "
          f"{s.get('lang', 0)} Ankertexte über {LANGTEXT_GRENZE} Zeichen "
          f"(davon {s.get('zu_lang', 0)} über der Fehlergrenze {LANGTEXT_FEHLER})")
    if ergebnis["befunde"]:
        print("Ergebnis: NICHT bestanden – Linktexte/Alt-Texte reparieren (SEO-Sicht).")
        return 1
    print("✅ Ergebnis: Linktexte und Alt-Texte sind crawlerlesbar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
