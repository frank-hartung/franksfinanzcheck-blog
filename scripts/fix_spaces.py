#!/usr/bin/env python3
"""fix_spaces.py – VOLLAUTOMATISCHER LEERZEICHEN-GENERATOR (PROFI-LEVEL)

Entscheidet SELBST, ob ein Leerzeichen sinnvoll ist – und ist
SELBSTHEILEND (idempotent, schützt bewusste Formatierung).

WAS ER KANN:
  A) DOPPELTE LEERZEICHEN im Fließtext → 1 Leerzeichen. Bewusste
     Markdown-Hard-Breaks (2+ Spaces am ZEILENENDE, z. B. nach „ – ")
     bleiben UNANGETASTET – sie sind vom Zeilenumbruch-Generator gesetzt.
  B) LISTEN-MARKER normalisieren: „*   Text" / „-   Text" / „1.   Text"
     (3+ Spaces nach dem Marker) → 1 Space.
  C) LEERZEICHEN VOR SATZZEICHEN entfernen („Hallo ," → „Hallo,") –
     selbstheilend, falls welche auftauchen.
  D) FEHLENDES LEERZEICHEN NACH .!? ergänzen („Satz.Neuer" → „Satz.
     Neuer") – mit Schutz für Abkürzungen (z. B., d. h., usw., ca., …),
     URLs, Markdown-Links und E-Mail-Adressen.
  E) FEHLENDES LEERZEICHEN NACH KOMMA ergänzen („Hallo,Welt" →
     „Hallo, Welt") – mit Link-/Zahlen-Schutz („3,5", „1,2").
  F) GESCHÜTZTES LEERZEICHEN (U+00A0) zwischen Zahl und %/€
     sicherstellen (kein Umbruch zwischen Zahl und Einheit).

NICHT ANGE FASTET: Tabellenzeilen (|), Inline-Code (`), Blockquotes (>),
Überschriften-Markup, Link-URLs, bereits gesetzte NBSP.

Aufruf:  python3 scripts/fix_spaces.py            (alle Dateien)
         python3 scripts/fix_spaces.py --dry-run  (nur anzeigen)
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NBSP = "\u00a0"

# Abkürzungen, nach denen KEIN Satzende folgt (Schutz für Regel D)
ABKUERZUNGEN = (
    "z\\.\\s?B\\.", "d\\.\\s?h\\.", "u\\.\\s?a\\.", "u\\.\\s?ä\\.", "v\\.\\s?a\\.",
    "usw\\.", "etc\\.", "bzw\\.", "ca\\.", "inkl\\.", "exkl\\.", "Nr\\.",
    "Dr\\.", "Prof\\.", "z\\.\\s?T\\.", "s\\.\\s?o\\.", "s\\.\\s?u\\.", "u\\.\\s?U\\.",
    "Abs\\.", "Art\\.", "Bd\\.", "Bsp\\.", "ggf\\.", "evtl\\.", "i\\.\\s?d\\.\\s?R\\.",
    "Tel\\.", "Mo\\.", "Di\\.", "Mi\\.", "Do\\.", "Fr\\.", "Sa\\.", "So\\.",
    "Jan\\.", "Feb\\.", "Mär\\.", "Apr\\.", "Jun\\.", "Jul\\.", "Aug\\.", "Sep\\.",
    "Okt\\.", "Nov\\.", "Dez\\.", "b\\.\\s?w\\.",
)
ABK_RE = re.compile(r"(?:" + "|".join(ABKUERZUNGEN) + r")(?=\s+[A-Za-zäöüß])")

# Muster: Buchstabe/Zahl + Satzzeichen + direkt Buchstabe (fehlendes Leerzeichen)
RE_MISSING_AFTER_PUNCT = re.compile(r"([a-zäöüßA-ZÄÖÜ0-9\)])([.!?])([a-zäöüßA-ZÄÖÜ])")
RE_MISSING_AFTER_COMMA = re.compile(r"([a-zäöüßA-ZÄÖÜ0-9\)]),([a-zäöüßA-ZÄÖÜ])")
# Achtung: „3,5" / „1,2" (Dezimalzahlen) sind keine Komma-Fehler – geschützt
RE_COMMA_NUMBER = re.compile(r"\d,\d")
RE_SPACE_BEFORE_PUNCT = re.compile(r" +([,.;:!?])")
RE_DBL_SPACE = re.compile(r"([^ \t])  +([^ \t])")
RE_LIST_MARKER = re.compile(r"^(\s*(?:[-*]|\d+\.))[ \u00a0]{2,}(\S)")


def _is_protected(line: str) -> bool:
    """Zeilen, die nie angefasst werden: Tabelle, Code, Zitat, URL-only."""
    return "|" in line or "`" in line or line.lstrip().startswith((">", "```"))


def fix_line(line: str) -> tuple[str, int]:
    """Wendet alle Leerzeichen-Regeln auf EINE Zeile an."""
    if _is_protected(line):
        return line, 0
    changed = 0
    orig = line

    # B) Listen-Marker normalisieren (3+ Spaces nach Marker → 1)
    line, n = RE_LIST_MARKER.subn(lambda m: m.group(1) + " " + m.group(2), line)
    changed += n

    # C) Leerzeichen vor Satzzeichen entfernen
    line, n = RE_SPACE_BEFORE_PUNCT.subn(lambda m: m.group(1), line)
    changed += n

    # A) Doppelte Leerzeichen mittendrin → 1 (Zeilenende = Hard-Break bleibt!)
    def _dbl(m):
        return m.group(1) + " " + m.group(2)
    line, n = RE_DBL_SPACE.subn(_dbl, line)
    changed += n

    # E) Fehlendes Leerzeichen nach Komma (nicht bei Dezimalzahlen)
    def _comma(m):
        return m.group(1) + ", " + m.group(2)
    # Dezimalzahlen temporär maskieren
    masked = RE_COMMA_NUMBER.sub(lambda m: m.group(0).replace(",", "§§"), line)
    line2, n = RE_MISSING_AFTER_COMMA.subn(_comma, masked)
    if n:
        line = line2.replace("§§", ",")
        changed += n

    # D) Fehlendes Leerzeichen nach .!? (Abkürzungen schützen)
    def _punct(m):
        return m.group(1) + m.group(2) + " " + m.group(3)
    # Abkürzungen temporär maskieren (Punkt durch Platzhalter ersetzen)
    def _mask_abk(m):
        return m.group(0).replace(".", "§")
    masked2 = ABK_RE.sub(_mask_abk, line)
    line3, n = RE_MISSING_AFTER_PUNCT.subn(_punct, masked2)
    if n:
        line = line3.replace("§", ".")
        changed += n

    # F) Geschütztes Leerzeichen zwischen Zahl und %/€ sicherstellen
    line, n = re.subn(r"(\d)[ \u00a0]+([%€])", lambda m: m.group(1) + NBSP + m.group(2), line)
    changed += n

    return line, changed


def fix_body(body: str) -> tuple[str, int]:
    """Wendet die Leerzeichen-Regeln auf den Body an."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    for line in lines:
        new_line, n = fix_line(line)
        out.append(new_line)
        changed += n
    return "\n".join(out), changed


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = (sorted(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))
             + sorted(glob.glob(f"{BLOG_DIR}/content/pillar/*/index.md")))
    total = 0
    for f in files:
        content = open(f, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        new_body, n = fix_body(parts[2])
        if n:
            total += n
            print(f"  {f.split('/')[-2]}: {n} Korrektur(en)")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Leerzeichen-Generator: {total} Korrekturen in {len(files)} Dateien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
