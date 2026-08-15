#!/usr/bin/env python3
"""fix_heading_breaks.py – Teilüberschriften-Generator (PROFI-LEVEL)

Dauerhafte Regel: Bei Teilüberschriften (H2/H3) mit Doppelpunkt wird nach
dem Doppelpunkt ein <br> eingefügt – der Untertitel beginnt auf einer
NEUEN Zeile innerhalb derselben Überschrift.

WICHTIG (gelernt): Ein Markdown-Hard-Break (2 Spaces + Newline) funktioniert
in ATX-Überschriften NICHT – die zweite Zeile würde als normaler Absatz
gerendert. Deshalb wird das rohe <br> direkt in die Überschrift geschrieben
(hugo.toml: goldmark.renderer.unsafe = true).

REGELN (Profi-Level, verhindert alle bekannten Fehlfälle):
1) NUR H2/H3 („## " / „### ") – H1 (Artikel-Titel) wird nie angefasst.
2) Doppelpunkt + Leerzeichen + nicht-leerer Untertitel. Doppelpunkte am
   ZEILENENDE („### Das Wichtigste in Kürze:") bleiben – nichts umzubrechen.
3) KEIN Umbruch, wenn der Untertitel mit einem KLEINBUCHSTABEN beginnt
   (z. B. „## Der wichtigste Wert: der effektive Jahreszins").
4) KEIN Umbruch in FAQ-BEREICHEN („## Häufige Fragen" / „## Häufig
   gestellte Fragen" / „## FAQ" bis zur nächsten #/##-Überschrift):
   ###-Fragen dort werden als FAQPage-JSON-LD gerendert.
5) Idempotent: Bereits umgebrochene Überschriften („:<br>") bleiben.
6) RÜCKBAU: Falsch gesetzte Hard-Break-Umbrüche in Überschriften
   (Zeile endet mit „:  ", Fortsetzung in der nächsten Zeile) werden
   zusammengeführt und dann korrekt mit <br> gesetzt.
7) URLs/Uhrzeiten („https://", „10:30") sind automatisch ausgenommen,
   da nach ihrem Doppelpunkt kein Leerzeichen folgt.

Aufruf:  python3 scripts/fix_heading_breaks.py          (alle Dateien)
         python3 scripts/fix_heading_breaks.py --dry-run (nur anzeigen)
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RE_HEADING = re.compile(r"^(#{2,3})\s+([^:\n]+?):([ \t]+)(\S.*)$")
RE_BROKEN_END = re.compile(r":[ \u00a0]{2,}$")     # Zeile endet mit „:  " (falscher Hard-Break)
RE_FAQ_START = re.compile(
    r"^#{1,2}\s*(Häufige Fragen|Häufig gestellte Fragen|Häufige Fragen \(FAQ\)|FAQ)\s*$",
    re.I)
RE_LOWER_START = re.compile(r"^[a-zäöüß]")


def fix_body(body: str) -> tuple[str, int]:
    """Wendet die Teilüberschriften-Regel an. Liefert (neuer_body, anzahl)."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    in_faq = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Kontext: FAQ-Bereich (wird von #/## beendet, ###-Fragen bleiben drin)
        if re.match(r"^#{1,6}\s+", line):
            if RE_FAQ_START.match(line):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", line):
                in_faq = False

        is_heading = bool(re.match(r"^#{2,3}\s+", line))

        if is_heading and RE_BROKEN_END.search(line) and i + 1 < n:
            # Falscher Hard-Break-Umbruch in Überschrift: zusammenführen,
            # damit er unten korrekt mit <br> neu gesetzt wird.
            nxt = lines[i + 1].strip()
            if nxt and not re.match(r"^#{1,6}\s+", nxt) and not RE_BROKEN_END.search(nxt):
                line = line.rstrip() + " " + nxt
                i += 1  # Fortsetzungszeile konsumieren

        # Umbruch mit <br> setzen?
        if is_heading and not in_faq and ":<br>" not in line:
            m = RE_HEADING.match(line)
            if m and not RE_LOWER_START.match(m.group(4)):
                heading = m.group(1) + " " + m.group(2) + ":"
                rest = m.group(4)
                out.append(heading + "<br>" + rest)
                changed += 1
                i += 1
                continue

        out.append(line)
        i += 1
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
            print(f"  {f.split('/')[-2]}: {n} Überschrift/Überschriften")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Fertig: {total} Teilüberschriften umgebrochen in {len(files)} Dateien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
