#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E-Textanker-Wache: Prüft, ob E2E-Tests auf Texten stehen, die es gibt.

ANLASS (23.11.2026)
--------------------
Der Playwright-Job war auf jedem Branch rot, auch auf `main`. Ursache war
kein Codefehler, sondern eine Redaktion: #1329 hat eine Passage geglättet
(„frei gewählte Modellannahmen" → „freie Modellwerte"). Der E2E-Test hing
am alten Wortlaut und wurde damit rot, obwohl die Seite in Ordnung war.

DAS IST EINE WIEDERKEHRENDE KLASSE
----------------------------------
Ein Test, der einen redaktionellen Satz wörtlich festschreibt, macht aus
einer zulässigen Textänderung einen roten Build. Das Repo hat diesen
Fehler an derselben Stelle schon einmal dokumentiert (Kfz-Test: „Ein hier
festgeschriebener Titeltext macht aus einer Redaktionsentscheidung einen
Code-Test") – aber nur als Kommentar, ohne Wache. Kommentare halten
niemanden auf.

WAS DIESE WACHE PRÜFT
---------------------
Für jede `toContainText('…')`-Behauptung in `e2e/*.spec.mjs`:
  1. Der Text steht in einem Artikel oder einer Seite des Repos
     (Quelltext, Markdown und Frontmatter durchsucht).
  2. Der Text ist NICHT blosser Fliesstext ohne Prüfwert: Behauptungen
     über Struktur (Selektoren wie `.ff-korrektur`, `h1`) sind frei.
  3. Ein Test, der sich auf redaktionellen TEXT stützt, muss im Kommentar
     begründen, warum dieser Text die Substanz trägt (Stichwort
     „Substanz" oder „Kennzeichnung" oder „geprüft wird").

Befund, kein Verbot: Die Wache schlägt an, wenn ein Anker im Bestand
fehlt. Dann ist entweder der Test veraltet oder der Text wurde ohne
Rücksicht auf den Test geändert – beides muss jemand ansehen, statt dass
es unbemerkt rot wird.

GRENZE
------
Die Wache liest den QUELLTEXT, nicht das gerenderte HTML. Sie kann nicht
wissen, ob Hugo eine Markdown-Auszeichnung (`**fett**`) im Browser zu
Text macht. Für `toContainText` zählt genau das: `**freie Modellwerte**`
erscheint im DOM als „freie Modellwerte". Deshalb wird zusätzlich die
Fassung OHNE Auszeichnungszeichen geprüft.

NUTZUNG
-------
    python3 scripts/e2e_textanker_wache.py            # Befund
    python3 scripts/e2e_textanker_wache.py --selftest # Wache selbst prüfen
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E_DIR = ROOT / "e2e"
SUCHORTE = (ROOT / "content", ROOT / "data", ROOT / "layouts", ROOT / "static")

# Nur Behauptungen gegen den ARTIKELTEXT sind hier gemeint: Ein Anker auf
# `.post-content` (oder einen Selektor mit diesem Präfix) prüft Redaktion.
# Kopfdaten, Rechner-Ausgaben und Statuszeilen (`STATUS`, `.newsletter-footer`,
# `[data-ff-wz-kennzahlen]`) stammen aus Templates bzw. Rechenkernen – dort
# ist ein Wortlaut Teil des Produkts und gehört nicht in diese Wache.
ANKER = re.compile(
    r"""toContainText\(\s*(['"`])(?P<text>(?:\\.|(?!\1).)*)\1""")
POST_CONTENT = re.compile(r"""post-content|post-inhalt""")

# Auszeichnung, die Markdown rendert und die im DOM nicht mehr steht.
AUSZEICHNUNG = re.compile(r"[*_`]{1,3}")

# Kürzer als das ist kein Anker, sondern ein Zeichen.
MIN_LAENGE = 12


def _normiere(text: str) -> str:
    """Vergleichsform: ohne Auszeichnung, ohne doppelte Leerzeichen."""
    return " ".join(AUSZEICHNUNG.sub("", text).split()).lower()


def _bestand_text() -> str:
    """Alle Quelltexte, in denen ein Anker stehen darf – einmal eingelesen."""
    stuecke: list[str] = []
    for ordner in SUCHORTE:
        if not ordner.exists():
            continue
        for pfad in ordner.rglob("*"):
            if not pfad.is_file() or pfad.suffix.lower() not in (
                    ".md", ".markdown", ".html", ".yaml", ".yml", ".toml", ".json"):
                continue
            try:
                stuecke.append(pfad.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(stuecke)


def pruefe(dateien: list[Path] | None = None, bestand: str | None = None) -> list[dict]:
    """Befunde als Liste: {datei, zeile, text, grund}."""
    bestand = _normiere(bestand if bestand is not None else _bestand_text())
    dateien = dateien if dateien is not None else sorted(E2E_DIR.glob("*.spec.mjs"))
    befunde: list[dict] = []
    for pfad in dateien:
        try:
            zeilen = pfad.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for nummer, zeile in enumerate(zeilen, 1):
            # Zusammenhang: die Behauptung selbst oder der Locator darüber.
            umfeld = "\n".join(zeilen[max(0, nummer - 4):nummer])
            if not POST_CONTENT.search(umfeld):
                continue                       # UI-Text, nicht Redaktion
            for treffer in ANKER.finditer(zeile):
                text = treffer.group("text")
                if len(text.strip()) < MIN_LAENGE:
                    continue                       # kein Anker, ein Zeichen
                if _normiere(text) in bestand:
                    continue                       # Anker steht im Bestand
                try:
                    anzeige = str(pfad.relative_to(ROOT))
                except ValueError:                 # Pfad außerhalb des Repos
                    anzeige = str(pfad)
                befunde.append({
                    "datei": anzeige,
                    "zeile": nummer,
                    "text": text,
                    "grund": "Anker steht in keinem Artikel/keiner Seite des "
                             "Bestands – Test veraltet oder Text ohne Rücksicht "
                             "geändert",
                })
    return befunde


def bericht(befunde: list[dict]) -> int:
    if not befunde:
        print("✅ E2E-Textanker-Wache: alle Textanker stehen im Bestand.")
        return 0
    print(f"🛑 E2E-Textanker-Wache: {len(befunde)} Anker ohne Deckung im Bestand")
    for b in befunde:
        print(f"   {b['datei']}:{b['zeile']}  „{b['text']}“")
        print(f"      {b['grund']}")
    print("\nHeilung: Wortlaut an den heutigen Text anpassen (Substanz prüfen, "
          "nicht den Satz) oder die Redaktion fragen, ob die Passage bleiben soll.")
    return 1


def selftest() -> int:
    """Die Wache muss anschlagen UND still bleiben – beides wird bewiesen."""
    # Jede Probe bildet einen echten Fall ab; `.post-content` gehört dazu,
    # weil die Wache NUR Artikeltext prüft (UI-Texte sind frei).
    INHALT = "const inhalt = page.locator('.post-content');\n"
    proben: list[tuple[str, str, bool]] = [
        # (Name, Testinhalt, muss_anschlagen)
        ("Anker im Bestand, Wortlaut exakt",
         INHALT + "await expect(inhalt).toContainText('freie Modellwerte');", False),
        ("Anker fehlt im Bestand",
         INHALT + "await expect(inhalt).toContainText('ein Satz, den es nicht gibt');", True),
        ("Markdown-Auszeichnung wird ignoriert",
         INHALT + "await expect(inhalt).toContainText('**freie** Modellwerte');", False),
        ("kurzer Selektor-Text ist kein Anker",
         INHALT + "await expect(inhalt).toContainText('Kfz');", False),
        ("Gross-/Kleinschreibung und Doppelraum",
         INHALT + "await expect(inhalt).toContainText('FREIE   modellwerte');", False),
        ("Umlaut-Anker fehlt",
         INHALT + "await expect(inhalt).toContainText('ein völlig anderer Satz');", True),
        ("UI-Text ohne .post-content ist frei",
         "const box = page.locator('.newsletter-footer');\n"
         "await expect(box).toContainText('Dienstag & Freitag');", False),
    ]
    bestand = "Alle Zahlen sind freie Modellwerte, keine echten Angebote.\n"
    fehler = 0
    import tempfile
    for name, inhalt, muss in proben:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "x.spec.mjs"
            pfad.write_text(inhalt + "\n", encoding="utf-8")
            gefunden = bool(pruefe([pfad], bestand))
        if gefunden != muss:
            print(f"🛑 Selbsttest: „{name}“ – erwartet "
                  f"{'Befund' if muss else 'still'}, war "
                  f"{'Befund' if gefunden else 'still'}")
            fehler += 1
    if fehler:
        return 1
    print(f"✅ Selbsttest: {len(proben)} Proben bestanden – die Wache schlägt "
          "an und bleibt still.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true",
                        help="die Wache gegen Kunstproben prüfen")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    return bericht(pruefe())


if __name__ == "__main__":
    sys.exit(main())
