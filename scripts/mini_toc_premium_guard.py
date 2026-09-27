#!/usr/bin/env python3
# ============================================================
#  „IM ARTIKEL"-WACHE – Premium-Vertrag der Artikel-Navigation
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 27.09.2026): „Die IM ARTIKEL-Box auf den
#  Blogartikel-Seiten sollte DAUERHAFT auf Premium-Level einer
#  Profi-Agentur in Layout und Design optimiert werden."
#
#  „Dauerhaft" ist der eigentliche Auftrag. Eine einmalige
#  Politur hält genau bis zum nächsten CSS-Refactoring – am
#  26.09.2026 hat exakt das die Box zweimal zerlegt (Deckel bei
#  9 Einträgen; Überlappung des Newsletter-Kopfes). Diese Wache
#  friert die Eigenschaften ein, die den Premium-Eindruck
#  ERZEUGEN, und bricht, sobald eine davon verschwindet.
#
#  GEPRÜFTE VERTRÄGE (Fundstelle jeweils im Befund):
#    V1  Vollständigkeit  – kein Deckel (`slice(0, n)`) auf der
#                           Überschriftenliste
#    V2  Kopfzeile        – Titel, Positionszähler, Fortschritt
#    V3  Eigener Scroll   – nur die Liste scrollt, Kopf steht
#    V4  Lesemarke        – aria-current wird gesetzt
#    V5  Geometrie        – Verankerung an --main-width (nicht an
#                           einer erfundenen Pixelzahl)
#    V6  Ruhzustand       – Box startet idle (Newsletter-Kopf frei)
#    V7  Breakpoint       – < 1280 px ausgeblendet
#    V8  Druck            – @media print blendet aus
#    V9  Reduced Motion   – Animationen abschaltbar
#    V10 Dark Mode        – jede neue Fläche hat eine dunkle Fassung
#    V11 Materialtiefe    – mehrstufiger Schatten + Innenlicht
#    V12 Fokus            – :focus-visible-Ring auf den Einträgen
#    V13 Keine Inline-Farben in der JS-Erzeugung (CLAUDE.md §4)
#    V14 Kein Line-Clamp  – deutsche Komposita werden nicht
#                           mitten im Wort abgeschnitten
#
#  NUTZUNG
#    python3 scripts/mini_toc_premium_guard.py            # prüfen
#    python3 scripts/mini_toc_premium_guard.py --json     # maschinenlesbar
#    python3 scripts/mini_toc_premium_guard.py --selftest # Wache prüft sich
#
#  EXIT: 0 grün · 1 Vertrag verletzt · 2 Selbsttest/Datei-Fehler
# ============================================================
from __future__ import annotations

import argparse
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PFAD = os.path.join(BLOG_DIR, "assets", "css", "extended", "z-premium-blog.css")
JS_PFAD = os.path.join(BLOG_DIR, "static", "premium", "ff-premium.js")


def _mini_toc_js(js: str) -> str:
    """Nur der Abschnitt, der die Navigation erzeugt (createMiniToc …)."""
    start = js.find("function createMiniToc")
    if start < 0:
        return js
    return js[start:start + 12000]


def pruefe(css: str, js: str) -> list[dict]:
    """Liste der Verletzungen. Leer = Premium-Vertrag erfüllt."""
    befunde: list[dict] = []
    toc_js = _mini_toc_js(js)

    def fordere(vertrag: str, bedingung: bool, beschreibung: str, fundstelle: str):
        if not bedingung:
            befunde.append({"vertrag": vertrag, "beschreibung": beschreibung,
                            "fundstelle": fundstelle})

    # V1 – Vollständigkeit: kein stiller Deckel auf der Abschnittsliste.
    deckel = re.search(r"headings[^\n;]*\.slice\s*\(\s*0\s*,\s*\d+", toc_js)
    fordere("V1", deckel is None,
            "Die Abschnittsliste wird wieder abgeschnitten (slice-Deckel) – "
            "„Fazit\" und „Häufige Fragen\" verschwinden aus der Navigation.",
            "static/premium/ff-premium.js → createMiniToc")

    # V2 – Kopfzeile mit Titel, Zähler, Fortschritt.
    for klasse in ("ff-mini-toc__title", "ff-mini-toc__count",
                   "ff-mini-toc__pos", "ff-mini-toc__rail"):
        fordere("V2", klasse in toc_js and klasse in css,
                f"Kopfzeilen-Element `{klasse}` fehlt in JS oder CSS.",
                "createMiniToc + z-premium-blog.css")
    fordere("V2", "--ff-toc-progress" in css and "--ff-toc-progress" in js,
            "Der Lesefortschritt (--ff-toc-progress) wird nicht mehr gesetzt.",
            "z-premium-blog.css / ff-premium.js")

    # V3 – Kopf steht, nur die Liste scrollt.
    listenblock = re.search(r"\.ff-mini-toc__list\s*\{[^}]*\}", css, re.DOTALL)
    fordere("V3", bool(listenblock) and "overflow-y: auto" in listenblock.group(0),
            "Der Eintrags-Container scrollt nicht mehr eigenständig – bei langen "
            "Artikeln wird die Liste wieder abgeschnitten.",
            "z-premium-blog.css → .ff-mini-toc__list")
    kopfblock = re.search(r"\.ff-mini-toc__head\s*\{[^}]*\}", css, re.DOTALL)
    fordere("V3", bool(kopfblock) and "flex: 0 0 auto" in kopfblock.group(0),
            "Die Kopfzeile ist nicht mehr fixiert (flex: 0 0 auto) – „Im Artikel "
            "7 / 24\" scrollt aus dem Blick.",
            "z-premium-blog.css → .ff-mini-toc__head")

    # V4 – Lesemarke.
    fordere("V4", "aria-current" in js,
            "Die aktive Lesemarke (aria-current) wird nicht mehr gesetzt.",
            "ff-premium.js → setupMiniTocSpy")

    # V5 – Geometrie an der echten Textspalte.
    geometrie = re.search(r"\.ff-mini-toc\s*\{[^}]*\}", css, re.DOTALL)
    geo_text = geometrie.group(0) if geometrie else ""
    fordere("V5", "var(--main-width)" in geo_text,
            "Die Box hängt nicht mehr an der echten Textspalte (--main-width) – "
            "auf mittleren Desktops rutscht sie in den Text.",
            "z-premium-blog.css → .ff-mini-toc { right: … }")

    # V6 – Ruhzustand (Newsletter-Kopf bleibt frei).
    fordere("V6", ".ff-mini-toc--idle" in css and "ff-mini-toc--idle" in js,
            "Der Ruhzustand fehlt – die Navigation überlagert wieder den "
            "Newsletter-Kopf über dem Artikel.",
            "z-premium-blog.css + ff-premium.js")

    # V7 – Breakpoint.
    fordere("V7", re.search(r"@media\s*\(max-width:\s*127\d px\)", css.replace("px", " px"))
            is not None or "max-width: 1279px" in css,
            "Der Mobil-/Tablet-Breakpoint (< 1280 px) fehlt – die Box würde auf "
            "schmalen Fenstern in den Text laufen.",
            "z-premium-blog.css → @media (max-width: 1279px)")

    # V8 – Druck.
    fordere("V8", re.search(r"@media print\s*\{[^}]*\.ff-mini-toc", css, re.DOTALL) is not None,
            "Die Navigation wird im Druck nicht mehr ausgeblendet.",
            "z-premium-blog.css → @media print")

    # V9 – Bewegungsarmut.
    reduced = re.findall(r"@media \(prefers-reduced-motion: reduce\)\s*\{(.*?)\n\}",
                         css, re.DOTALL)
    fordere("V9", any("ff-mini-toc" in block for block in reduced),
            "prefers-reduced-motion wird für die Navigation nicht mehr beachtet.",
            "z-premium-blog.css")

    # V10 – Dark Mode für jede Fläche.
    fordere("V10", ':root[data-theme="dark"] .ff-mini-toc' in css,
            "Die Navigation hat keine Dark-Mode-Fassung – defaultTheme ist auto.",
            "z-premium-blog.css")

    # V11 – Materialtiefe: mehrstufiger Schatten inkl. Innenlicht.
    # Nur die HELLE Grundfläche zählt – eine Dark-Mode-Regel darf den Befund
    # nicht überdecken (genau so würde eine Politur unbemerkt verschwinden).
    hell = re.findall(r"(?m)^\.ff-mini-toc\s*\{[^}]*\}", css)
    schatten = [m.group(1) for block in hell
                for m in [re.search(r"box-shadow:([^;]+);", block, re.DOTALL)] if m]
    tiefe = any(s.count(",") >= 2 and "inset" in s for s in schatten)
    fordere("V11", tiefe,
            "Die Materialtiefe ist weg (mehrstufiger Schatten + inset-Innenlicht) – "
            "die Box wirkt wieder wie ein flacher Standard-Kasten.",
            "z-premium-blog.css → .ff-mini-toc { box-shadow: … }")

    # V12 – Tastaturführung.
    fokus = re.search(r"(?m)^\.ff-mini-toc a:focus-visible\s*\{[^}]*outline:[^;]+;", css)
    fordere("V12", fokus is not None,
            "Der eigene Fokus-Ring der Einträge fehlt (Tastatur-Bedienung).",
            "z-premium-blog.css → .ff-mini-toc a:focus-visible")

    # V13 – keine Inline-Farben aus dem JS.
    inline_farbe = re.search(r"style\.(?:background|color|borderColor)\s*=", toc_js)
    fordere("V13", inline_farbe is None,
            "Farbe wird per Inline-Style aus dem JS gesetzt (CLAUDE.md §4: "
            "Klassen + CSS, sonst bricht der Dark Mode).",
            "static/premium/ff-premium.js")

    # V14 – kein Line-Clamp auf den Einträgen.
    eintrag = re.search(r"\.ff-mini-toc a\s*\{[^}]*\}", css, re.DOTALL)
    eintrag_text = eintrag.group(0) if eintrag else ""
    fordere("V14", "-webkit-line-clamp: unset" in eintrag_text,
            "Der Clamp-Schutz fehlt – lange deutsche Komposita werden wieder "
            "mitten im Wort abgeschnitten.",
            "z-premium-blog.css → .ff-mini-toc a")

    return befunde


def selftest() -> int:
    """Die Wache muss Verletzungen ERKENNEN, nicht nur grün melden."""
    try:
        css = open(CSS_PFAD, encoding="utf-8").read()
        js = open(JS_PFAD, encoding="utf-8").read()
    except OSError as exc:
        print(f"🛑 Datei nicht lesbar: {exc}", file=sys.stderr)
        return 2

    fehler = []
    if pruefe(css, js):
        fehler.append("ST0: Der echte Bestand verletzt den Vertrag (siehe Lauf ohne --selftest)")

    # Sabotage-Proben: jede muss genau ihren Vertrag auslösen.
    proben = [
        ("V1", css, js.replace("var headings = qsa('h2[id], h3[id]', content)",
                               "var headings = qsa('h2[id]', content).slice(0, 9)")),
        ("V3", re.sub(r"(\.ff-mini-toc__list\s*\{[^}]*?)overflow-y: auto;", r"\1",
                      css, flags=re.DOTALL), js),
        ("V5", css.replace("var(--main-width)", "1120px"), js),
        ("V11", re.sub(r"(\.ff-mini-toc \{[^}]*?)inset 0 1px 0 rgba\(255, 255, 255, \.55\)",
                       r"\1none", css, count=1, flags=re.DOTALL), js),
        ("V12", css.replace(".ff-mini-toc a:focus-visible {", ".ff-tot a:focus-visible {"), js),
        ("V14", css.replace("-webkit-line-clamp: unset", "-webkit-line-clamp: 2"), js),
    ]
    for vertrag, c, j in proben:
        verletzt = {b["vertrag"] for b in pruefe(c, j)}
        if vertrag not in verletzt:
            fehler.append(f"ST-{vertrag}: Sabotage blieb unentdeckt")

    if fehler:
        print("🛑 Selbsttest „Im Artikel\"-Wache rot:")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ Selbsttest „Im Artikel\"-Wache: Bestand grün, "
          f"{len(proben)}/{len(proben)} Sabotage-Proben erkannt.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Premium-Vertrag der „Im Artikel\"-Navigation")
    p.add_argument("--json", action="store_true", help="Befunde maschinenlesbar")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        return selftest()

    try:
        css = open(CSS_PFAD, encoding="utf-8").read()
        js = open(JS_PFAD, encoding="utf-8").read()
    except OSError as exc:
        print(f"🛑 Datei nicht lesbar: {exc}", file=sys.stderr)
        return 2

    befunde = pruefe(css, js)
    if args.json:
        print(json.dumps({"befunde": befunde, "grün": not befunde},
                         ensure_ascii=False, indent=2))
        return 1 if befunde else 0

    if not befunde:
        print("✅ „Im Artikel\"-Navigation: Premium-Vertrag V1–V14 erfüllt.")
        return 0
    print(f"🛑 „Im Artikel\"-Navigation: {len(befunde)} Vertragsverletzung(en)")
    for b in befunde:
        print(f"   [{b['vertrag']}] {b['beschreibung']}\n        → {b['fundstelle']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
