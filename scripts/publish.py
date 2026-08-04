#!/usr/bin/env python3
"""
Veröffentlichungs-Helfer: Setzt 'draft: true' auf 'draft: false'.

Nutzung:
    python3 scripts/publish.py posts/2026-08-04-mein-artikel.md   # ein Artikel
    python3 scripts/publish.py --all                              # alle Entwürfe
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")


def publish(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "draft: true" not in content:
        print(f"  – übersprungen (kein Entwurf): {os.path.basename(path)}")
        return 0
    content = content.replace("draft: true", "draft: false", 1)
    # Entwurfs-Datum durch heutiges Datum ersetzen (wird beim Veröffentlichen neu datiert)
    content = re.sub(r"^date: \d{4}-\d{2}-\d{2}$", f"date: {__import__('datetime').date.today().isoformat()}", content, count=1, flags=re.M)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ veröffentlicht: {os.path.basename(path)}")
    return 1


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if args == ["--all"]:
        files = sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
        print(f"Veröffentliche alle {len(files)} Artikel in {POSTS_DIR}:")
        count = sum(publish(f) for f in files)
    else:
        count = 0
        for arg in args:
            path = arg if os.path.isabs(arg) else os.path.join(BLOG_DIR, arg)
            if os.path.exists(path):
                count += publish(path)
            else:
                print(f"  ✗ Datei nicht gefunden: {path}")
    print(f"\nFertig: {count} Artikel veröffentlicht. Jetzt committen & pushen, "
          "dann baut GitHub Pages automatisch neu.")


if __name__ == "__main__":
    main()
