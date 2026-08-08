#!/usr/bin/env python3
"""set_lastmod.py – setzt `lastmod:` im Frontmatter geänderter Artikel.

Modi:
  python3 scripts/set_lastmod.py --git-changed   # nur lokal geänderte Posts (git diff)
  python3 scripts/set_lastmod.py --all           # alle Posts ohne lastmod

Wird im SEO-Workflow nach den Optimierungen aufgerufen: Artikel, die in
diesem Lauf geändert wurden (Meta, Rechtschreibung, Links), bekommen
lastmod = heute → Hugo rendert article:modified_time + Sitemap-lastmod
(Frische-Signal für Google).
"""
import os
import re
import sys
import glob
import subprocess
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")


def set_lastmod(path, date):
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    fm = parts[1]
    if re.search(r"^lastmod:\s*", fm, re.M):
        fm2 = re.sub(r"^lastmod:.*$", f"lastmod: {date}", fm, count=1, flags=re.M)
    else:
        # Nach der date:-Zeile einfügen
        if re.search(r"^date:", fm, re.M):
            fm2 = re.sub(r"^(date:.*)$", rf"\1\nlastmod: {date}", fm, count=1, flags=re.M)
        else:
            fm2 = fm.rstrip() + f"\nlastmod: {date}\n"
    if fm2 == fm:
        return False
    open(path, "w", encoding="utf-8").write("---".join([parts[0], fm2, parts[2]]))
    return True


def main():
    mode_all = "--all" in sys.argv
    date = datetime.date.today().isoformat()

    if mode_all:
        files = glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
    else:
        # Nur lokal geänderte Posts (unstaged git diff)
        r = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=BLOG_DIR)
        changed = set(r.stdout.split())
        r2 = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, cwd=BLOG_DIR)
        changed |= set(r2.stdout.split())
        files = [os.path.join(BLOG_DIR, f) for f in changed
                 if f.startswith("content/posts/") and f.endswith("index.md")]

    n = 0
    for f in sorted(files):
        if os.path.exists(f) and set_lastmod(f, date):
            n += 1
            print(f"  ✓ lastmod={date}: {os.path.basename(os.path.dirname(f))}")
    print(f"lastmod gesetzt für {n} Artikel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
