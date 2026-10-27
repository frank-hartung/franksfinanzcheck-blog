#!/usr/bin/env python3
# ============================================================
#  SERP-GRENZEN – eine Quelle für Snippet-Länge und Snippet-Breite
#  (Dauerheilung 27.10.2026, Screaming-Frog-Spiegel)
#
#  WARUM ES DIESE DATEI GIBT
#  -------------------------
#  Am 27.10.2026 meldete ein fremder Crawl (Screaming Frog) für die
#  Startseite zwei Befunde derselben Ursache: „Meta Description über
#  155 Zeichen" und „über 985 Pixel". Die Description war 156 Zeichen
#  lang – unser eigenes Gate (metadaten_wache M2) erlaubte 160 und
#  schwieg, das SEO-Cockpit erlaubte 165 und schwieg ebenfalls. Zwei
#  Grenzen im Haus, keine davon die des Marktes: Der Befund war damit
#  nicht „falsch", sondern **unser Maßstab war zu großzügig**.
#
#  Seitdem stehen die Grenzen an EINER Stelle, und beide Messstellen
#  (Quelle: metadaten_wache.py · gebaute Seite: seo_cockpit.py) lesen
#  sie hier – nicht als Kopie, sondern als Import. Eine Zahl, die in
#  zwei Dateien steht, ist eine Zahl, die irgendwann auseinanderläuft.
#
#  WIE GEMESSEN WIRD (und was daran ehrlich ist)
#  ---------------------------------------------
#  Google zeigt das Desktop-Snippet in Arial 14 px und bricht bei rund
#  985 px ab. Diese Datei misst Textbreite deshalb mit den
#  **Advance-Breiten der Kernschrift Helvetica** (Adobe-Kernmetrik,
#  1/1000 em) – Arial ist metrisch identisch mit Helvetica, die
#  Zeichenbreiten stimmen also überein. Es ist und bleibt eine
#  Schätzung der Google-Darstellung, keine Messung im Browser; sie
#  ist aber **deterministisch** (kein Browser, kein Font, kein Netz)
#  und liegt bewusst auf derselben Seite wie das Marktwerkzeug.
#
#  Zeichen ohne Metrik (z. B. Emoji, kyrillisch, CJK) werden NICHT
#  geschätzt: `breite_px()` gibt dann `None` zurück und der Aufrufer
#  meldet „nicht messbar". Ein Melder, der für unbekannte Zeichen eine
#  Zahl erfindet, produziert ein Grün, das nichts belegt.
# ============================================================
"""Grenzen und Breitenmaß für Meta-Descriptions (SSOT, ohne Abhängigkeiten)."""

from __future__ import annotations

import re

# --------------------------------------------------------------- Grenzen (SSOT)
# Zeichenfenster: Untergrenze 100 (sonst verschenkt das Snippet Platz),
# Obergrenze 155 (Google-Desktop, deckungsgleich mit dem Marktwerkzeug).
DESC_MIN_ZEICHEN = 100
DESC_MAX_ZEICHEN = 155

# Pixelgrenze des Desktop-Snippets und die Schrift, in der sie gilt.
DESC_MAX_PX = 985
SCHRIFT_PX = 14.0
SCHRIFT_NAME = "Arial/Helvetica 14 px (Adobe-Kernmetrik, 1/1000 em)"

# ------------------------------------------------------------- Breiten (1/1000 em)
# Quelle der Zahlen: Adobe-Kernmetrik der Schrift Helvetica (WinAnsi-Zeichensatz,
# 219 belegte Zeichen). Arial ist metrisch identisch – deshalb gilt dieselbe
# Tabelle für Googles Snippet-Schrift. Erzeugt und geprüft am 27.10.2026:
#   Adobe-Helvetica-AFM → width(ch)/1000 em; Stichprobe gegen die
#   veröffentlichten Breiten (a = 556, i = 222, W = 944, M = 833, Leerzeichen = 278).
BREITEN: dict[str, int] = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667, "'": 191, '(': 333,
    ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278, '0': 556, '1': 556,
    '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556, '8': 556, '9': 556, ':': 278,
    ';': 278, '<': 584, '=': 584, '>': 584, '?': 556, '@': 1015, 'A': 667, 'B': 667, 'C': 722,
    'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278, 'J': 500, 'K': 667, 'L': 556,
    'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722,
    'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469,
    '_': 556, '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556,
    'h': 556, 'i': 222, 'j': 222, 'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556, 'p': 556,
    'q': 556, 'r': 333, 's': 500, 't': 278, 'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500,
    'z': 500, '{': 334, '|': 260, '}': 334, '~': 584, '\x7f': 761, '\xa0': 278, '¡': 333, '¢': 556,
    '£': 556, '¤': 556, '¥': 556, '¦': 260, '§': 556, '¨': 333, '©': 737, 'ª': 370, '«': 556,
    '¬': 584, '\xad': 333, '®': 737, '¯': 333, '°': 400, '±': 584, '²': 333, '³': 333, '´': 333,
    'µ': 556, '¶': 537, '·': 278, '¸': 333, '¹': 333, 'º': 365, '»': 556, '¼': 834, '½': 834,
    '¾': 834, '¿': 611, 'À': 667, 'Á': 667, 'Â': 667, 'Ã': 667, 'Ä': 667, 'Å': 667, 'Æ': 1000,
    'Ç': 722, 'È': 667, 'É': 667, 'Ê': 667, 'Ë': 667, 'Ì': 278, 'Í': 278, 'Î': 278, 'Ï': 278,
    'Ð': 722, 'Ñ': 722, 'Ò': 778, 'Ó': 778, 'Ô': 778, 'Õ': 778, 'Ö': 778, '×': 584, 'Ø': 778,
    'Ù': 722, 'Ú': 722, 'Û': 722, 'Ü': 722, 'Ý': 667, 'Þ': 667, 'ß': 611, 'à': 556, 'á': 556,
    'â': 556, 'ã': 556, 'ä': 556, 'å': 556, 'æ': 889, 'ç': 500, 'è': 556, 'é': 556, 'ê': 556,
    'ë': 556, 'ì': 278, 'í': 278, 'î': 278, 'ï': 278, 'ð': 556, 'ñ': 556, 'ò': 556, 'ó': 556,
    'ô': 556, 'õ': 556, 'ö': 556, '÷': 584, 'ø': 611, 'ù': 556, 'ú': 556, 'û': 556, 'ü': 556,
    'ý': 500, 'þ': 556, 'ÿ': 500, 'Œ': 1000, 'œ': 944, 'Š': 667, 'š': 500, 'Ÿ': 667, 'Ž': 611,
    'ž': 500, 'ƒ': 556, 'ˆ': 333, '˜': 333, '–': 556, '—': 1000, '‘': 222, '’': 222, '‚': 222,
    '“': 333, '”': 333, '„': 333, '†': 556, '‡': 556, '•': 350, '…': 1000, '‰': 1000, '‹': 333,
    '›': 333, '€': 556, '™': 1000,
}


def normalisiere(text: str | None) -> str:
    """Snippet-Wahrheit: HTML-Leerraum und NBSP kollabieren, Ränder weg.

    Google rendert Folgen von Leerraum als ein Leerzeichen; eine
    Description mit doppelten Leerzeichen ist im Code länger als im
    Snippet. Gemessen wird, was der Nutzer sieht.
    """
    roh = str(text or "").replace("\u00a0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", roh).strip()


def unbekannte_zeichen(text: str | None) -> list[str]:
    """Zeichen ohne Breitenmaß – sortiert und eindeutig, für die Meldung."""
    return sorted({z for z in normalisiere(text) if z not in BREITEN})


def breite_px(text: str | None) -> float | None:
    """Breite in Pixeln bei 14 px – `None`, wenn ein Zeichen keine Metrik hat.

    `None` ist die einzige ehrliche Antwort für unbekannte Zeichen; eine
    Ersatzbreite würde aus „nicht messbar" ein „passt schon" machen.
    """
    zeichen = normalisiere(text)
    if any(z not in BREITEN for z in zeichen):
        return None
    return sum(BREITEN[z] for z in zeichen) / 1000.0 * SCHRIFT_PX


def befunde(text: str | None, *, min_zeichen: int = DESC_MIN_ZEICHEN) -> list[tuple[str, str]]:
    """Alle Snippet-Verstöße als (Code, Begründung) – leer heißt: passt.

    Codes sind stabil und werden von beiden Messstellen verwendet:
      ``zu-kurz``    Description unter dem Zeichenfenster
      ``zu-lang``    über 155 Zeichen (Google kürzt ab)
      ``zu-breit``   über 985 Pixel, obwohl die Zeichenzahl passt
      ``unmessbar``  Zeichen ohne Breitenmaß
    """
    text = normalisiere(text)
    ergebnis: list[tuple[str, str]] = []
    if not text:
        return [("zu-kurz", "Description fehlt")]
    if len(text) < min_zeichen:
        ergebnis.append(("zu-kurz", f"{len(text)} Zeichen (min. {min_zeichen})"))
    if len(text) > DESC_MAX_ZEICHEN:
        ergebnis.append(("zu-lang", f"{len(text)} Zeichen (max. {DESC_MAX_ZEICHEN})"))
    breite = breite_px(text)
    if breite is None:
        zeichen = ", ".join(repr(z) for z in unbekannte_zeichen(text)[:8])
        ergebnis.append(("unmessbar", f"Zeichen ohne Metrik: {zeichen}"))
    elif breite > DESC_MAX_PX:
        ergebnis.append(("zu-breit",
                         f"{breite:.0f} px (max. {DESC_MAX_PX} px bei {SCHRIFT_NAME})"))
    return ergebnis


def passt(text: str | None, *, min_zeichen: int = DESC_MIN_ZEICHEN) -> bool:
    """Kurzform für Aufrufer, die nur ein Ja/Nein brauchen."""
    return not befunde(text, min_zeichen=min_zeichen)


def masse(text: str | None) -> tuple[int, float | None]:
    """(Zeichen, Pixel) – für Berichte. Pixel sind `None`, wenn unmessbar."""
    return len(normalisiere(text)), breite_px(text)
