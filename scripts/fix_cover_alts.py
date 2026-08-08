#!/usr/bin/env python3
"""fix_cover_alts.py – ersetzt generische Cover-Alt-Texte durch natürliche,
keywordreiche Alt-Texte (aus dem Artikel-Titel).

Bot-Covers haben bisher Alt-Texte wie "Spar-Tipp: 2026 08 08 ...". Besser:
Der (plainifizierte) Titel des Artikels – enthält die Keywords und ist
natürlich formuliert. Für die Pillar-Seiten (ohne Cover) wird nichts geändert.

Modi:
  python3 scripts/fix_cover_alts.py            # Vorschau (dry)
  python3 scripts/fix_cover_alts.py --apply    # anwenden
"""
import os
import re
import sys
import glob

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_title(content):
    m = re.search(r'^title:\s*"?(.+?)"?\s*$', content.split("---", 2)[1], re.M)
    if not m:
        return None
    t = m.group(1).strip()
    # <br> und HTML-Reste entfernen
    t = re.sub(r"<[^>]+>", "", t).strip()
    return t


def fix_file(path, apply):
    content = open(path, encoding="utf-8").read()
    title = get_title(content)
    if not title:
        return 0
    # cover-Block finden
    m = re.search(r"(^cover:\s*\n\s*image:.*?\n)(\s*alt:.*?)(\n\s*caption:)", content, re.M | re.S)
    if not m:
        return 0
    new_alt = f'  alt: "{title}"'
    if m.group(2).strip() == new_alt.strip():
        return 0
    if apply:
        content = content[:m.start(2)] + new_alt + content[m.end(2):]
        open(path, "w", encoding="utf-8").write(content)
    return 1


def main():
    apply = "--apply" in sys.argv
    files = sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md")))
    n = 0
    for f in files:
        slug = os.path.basename(os.path.dirname(f))
        if fix_file(f, apply):
            n += 1
            print(f"  {'✓' if apply else '·'} {slug}")
    print(f"{'Angewendet' if apply else 'Vorschau'}: {n} Alt-Texte "
          f"{'ersetzt' if apply else 'würden ersetzt'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
