#!/usr/bin/env python3
"""fix_linebreaks.py – VOLLAUTOMATISCHER ZEILENUMBRUCH-GENERATOR (PROFI-LEVEL)

Entscheidet SELBST, ob ein Zeilenumbruch sinnvoll ist – und ist
SELBSTHEILEND (idempotent + Rückbau unpassender Umbrüche).

WAS ER KANN:
  A) GEDANKENSTRICH-NACHSATZ: Nach „ – " im normalen Fließtext wird ein
     Markdown-Hard-Break (2 Spaces + Newline) gesetzt, wenn ein
     erläuternder Nachsatz folgt („die, der, das, ein, wer, was, …").
     Kein Umbruch bei Fortsetzungen („und, oder, für, mit, z. B., …").
  B) ÜBERSCHRIFTEN-DOPPELPUNKT: In H2/H3 wird nach „:" ein <br> gesetzt,
     wenn ein nicht-klein beginnender Untertitel folgt.
  C) SELBSTHEILUNG: Umbrüche in unpassenden Kontexten (FAQ-Antworten,
     Listenelemente, Tabellen, Code, Blockquotes) werden erkannt und
     zurückgebaut; bereits korrekt gesetzte bleiben (idempotent).
  D) ENTSCHEIDUNG: Kontext-Erkennung (FAQ-Bereich, Listen, Tabellen,
     Code, Überschriften, Blockquotes) + Wortlisten für Nachsatz vs.
     Fortsetzung + Großschreibungs-Check.

Aufruf:  python3 scripts/fix_linebreaks.py            (alle Dateien)
         python3 scripts/fix_linebreaks.py --dry-run  (nur anzeigen)
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------- Wortlisten (Entscheidungslogik) ----------------
NACHSATZ_WORDS = (
    "die der das ein eine einer einem einen wer was wem wen man es "
    "sprich konkret genau wichtig entscheidend dabei außerdem zudem "
    "nämlich deshalb darum deswegen kurz kurzum letztlich letztendlich "
    "so dann damit hier dort alles nichts viel mehr weniger besser "
    "schlechter günstiger teurer schneller langsamer einfacher "
    "schwieriger sinnvoll ratsam empfehlenswert viele einige manche "
).split()
NACHSATZ_PHRASES = ("das heißt", "der Trick", "die Regel", "die Idee", "der Unterschied",
    "der Vorteil", "der Nachteil", "das Ergebnis", "das Fazit", "der Schlüssel",
    "die Antwort", "die Lösung", "die Wahrheit", "die Sache", "das Ganze",
    "die meisten", "die wenigsten", "am Ende", "im Kern")
KEIN_WORDS = (
    "und oder aber denn doch jedoch sowie auch nicht kein keine keinen "
    "keinem nie immer oft meist manchmal wirklich eigentlich eben ja nein "
    "für mit von bei auf zu um aus nach über unter vor bis an in im zum "
    "zur vom beim gegen ohne durch zwischen wegen als wie wenn weil dass "
    "damit obwohl während seit ab außer trotz laut dank je pro plus minus "
    "mal etwa rund ungefähr fast nur gerade schon noch bereits erst"
).split()
KEIN_PHRASES = ("z. B.", "zum Beispiel", "eine Provision", "ein paar", "ein wenig",
    "ein bisschen", "viele Jahre")

_NACH = sorted(set(NACHSATZ_WORDS) | set(NACHSATZ_PHRASES), key=len, reverse=True)
_KEIN = sorted(set(KEIN_WORDS) | set(KEIN_PHRASES), key=len, reverse=True)

RE_NACHSATZ = re.compile(r" \u2013 (" + "|".join(re.escape(w) for w in _NACH) + r")(?![a-zäöüß])")
RE_KEIN = re.compile(r" \u2013 (" + "|".join(re.escape(w) for w in _KEIN) + r")(?![a-zäöüß])")
RE_FAQ_START = re.compile(
    r"^#{1,2}\s*(Häufige Fragen|Häufig gestellte Fragen|Häufige Fragen \(FAQ\)|FAQ)\s*$",
    re.I)
RE_HEADING_COLON = re.compile(r"^(#{2,3})\s+([^:\n]+?):([ \t]+)(\S.*)$")
RE_LOWER_START = re.compile(r"^[a-zäöüß]")
RE_BROKEN_END = re.compile(r"[ \u00a0]{2,}$")       # Zeile endet mit Hard-Break-Spuren
RE_HEADING_BROKEN = re.compile(r":[ \u00a0]{2,}$")  # Überschrift mit Hard-Break-Spur


def _is_list_item(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*]|\d+\.)\s+", line))


def _is_quote(line: str) -> bool:
    return bool(re.match(r"^\s*&?gt;?\s*", line)) or line.lstrip().startswith(">")


def fix_body(body: str) -> tuple[str, int]:
    """Wendet alle Zeilenumbruch-Regeln an. Liefert (neuer_body, anzahl)."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    in_faq = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Kontext-Tracking
        if re.match(r"^#{1,6}\s+", line):
            if RE_FAQ_START.match(line):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", line):
                in_faq = False

        is_heading = bool(re.match(r"^#{2,3}\s+", line))
        no_break_ctx = (
            in_faq
            or _is_list_item(line)
            or _is_quote(line)
            or "|" in line          # Tabelle
            or "`" in line          # Inline-Code
            or line.lstrip().startswith("#")  # Überschrift (für Regel A)
        )

        # ---------- SELBSTHEILUNG: unpassende Umbrüche zurückbauen ----------
        if no_break_ctx and RE_BROKEN_END.search(line) and i + 1 < n:
            nxt = lines[i + 1].strip()
            if nxt and not RE_BROKEN_END.search(nxt) and not re.match(r"^#{1,6}\s+", nxt):
                line = line.rstrip() + " " + nxt
                i += 1
                changed += 1

        # ---------- REGEL B: Überschriften-Doppelpunkt (H2/H3) ----------
        if is_heading and not in_faq and ":<br>" not in line:
            m = RE_HEADING_COLON.match(line)
            if m and not RE_LOWER_START.match(m.group(4)):
                heading = m.group(1) + " " + m.group(2) + ":"
                rest = m.group(4)
                out.append(heading + "<br>" + rest)
                changed += 1
                i += 1
                continue

        # ---------- REGEL A: Gedankenstrich-Nachsatz (nur Fließtext) ----------
        if not no_break_ctx and not is_heading:
            if not RE_BROKEN_END.search(line):  # idempotent
                m = RE_NACHSATZ.search(line)
                if m and not RE_KEIN.search(line):
                    pos = m.start() + 3  # Länge von „ – "
                    out.append(line[:pos] + "  ")
                    out.append(line[pos:])
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
            print(f"  {f.split('/')[-2]}: {n} Änderung(en)")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Zeilenumbruch-Generator: {total} Änderungen in {len(files)} Dateien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
