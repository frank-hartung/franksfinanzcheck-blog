#!/usr/bin/env python3
"""Dauerhafte Blog-Gesundheitsprüfung und Selbstheilung."""
import os, re, glob, yaml

REPO = "/home/user/repo"

def fix_article(path):
    with open(path) as f:
        content = f.read()
    original = content
    # Draft fixen
    content = content.replace("draft: true", "draft: false")
    # Generische Alts ersetzen
    content = re.sub(r'alt: "Spar-Tipp:[^"]+"', 'alt: "Tipp von FranksFinanzcheck"', content)
    # Fehlende description ergänzen (aus title)
    if "description:" not in content:
        title = re.search(r'title: "([^"]+)"', content)
        if title:
            desc = title.group(1) + " – Jetzt lesen und sparen!"
            content = content.replace("date:", "description: \"" + desc + "\"\ndate:")
    # Fehlende H1 (erste Überschrift nach Frontmatter) ergänzen
    lines = content.split("\n")
    in_front = True
    h1_found = False
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.startswith("---") and in_front:
            in_front = not in_front
            continue
        if line.strip() == "---" and not in_front:
            in_front = False
            if not h1_found:
                title = re.search(r'title: "([^"]+)"', content)
                if title:
                    new_lines.append("")
                    new_lines.append("# " + title.group(1))
                    new_lines.append("")
                    h1_found = True
    content = "\n".join(new_lines)
    if content != original:
        with open(path, "w") as f:
            f.write(content)
        print("Repariert:", path)

for p in glob.glob(f"{REPO}/content/**/*.md", recursive=True):
    fix_article(p)
print("Blog-Gesundheits-Check abgeschlossen.")
