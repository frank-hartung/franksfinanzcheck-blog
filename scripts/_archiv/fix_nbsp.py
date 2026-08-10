#!/usr/bin/env python3
"""fix_nbsp.py – Geschütztes Leerzeichen (U+00A0) zwischen Zahl und Einheit.

Ersetzt in ALLEN Content-Dateien (Posts, Pillars, topics.yaml):
  1) NORMALES Leerzeichen zwischen Ziffer und % bzw. € → geschütztes
     Leerzeichen (Non-Breaking Space, U+00A0). Damit kann der Browser NIE
     zwischen Zahl und Einheit umbrechen („10 %" darf nicht am Zeilenende
     auseinandergerissen werden).
  2) HTML-Entity &nbsp; (Überbleibsel der alten Generatoren) → echtes U+00A0
     überall (Body UND Frontmatter/Kurzantwort – dort wäre die Entity
     sichtbarer Text).

Idempotent: Bereits geschützte Leerzeichen werden nicht erneut ersetzt.

Aufruf:  python3 scripts/fix_nbsp.py
"""
import glob
import re
import sys

NBSP = "\u00a0"
FILES = (
    sorted(glob.glob("content/posts/*/index.md"))
    + sorted(glob.glob("content/pillar/*/index.md"))
    + ["data/topics.yaml"]
)
# Ziffer + beliebige Mischung aus normalen/geschützten Leerzeichen + Einheit (% oder €)
RE = re.compile(r"(\d)[ \u00a0]+([%€])")
# HTML-Entity überall (z. B. 50&nbsp;% oder z.&nbsp;B.)
RE_ENT = re.compile(r"&nbsp;")


def fix_text(text: str) -> tuple[str, int]:
    """Ersetzt alle Vorkommen; liefert (neuer Text, Anzahl)."""
    new, n1 = RE.subn(lambda m: m.group(1) + NBSP + m.group(2), text)
    new, n2 = RE_ENT.subn(NBSP, new)
    return new, n1 + n2


def main() -> int:
    changed = 0
    total = 0
    for f in FILES:
        with open(f, encoding="utf-8") as fh:
            text = fh.read()
        new, n = fix_text(text)
        if n:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new)
            changed += 1
            total += n
            print(f"  {f}: {n} Ersetzung(en)")
    print(f"\nFertig: {changed} Datei(en), {total} Ersetzung(en).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
