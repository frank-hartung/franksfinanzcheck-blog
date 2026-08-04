#!/usr/bin/env python3
"""
Setzt deine persönlichen CHECK24-Affiliate-Links in ALLE Blog-Artikel ein.

Die Links stehen in scripts/check24_links.yaml (bereits mit deinen
persönlichen Deep-Links aus dem Partner-Dashboard befüllt).

NUTZUNG:
    python3 scripts/set_check24_links.py            # alle Artikel ersetzen
    python3 scripts/set_check24_links.py --dry-run  # nur Vorschau (ändert nichts)
    python3 scripts/set_check24_links.py --topics   # auch data/topics.yaml (für den Bot)

NEUE LINKS ERGÄNZEN:
    1) scripts/check24_links.yaml öffnen, Kategorie eintragen
    2) python3 scripts/set_check24_links.py --topics ausführen
"""

import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
LINKS_FILE = os.path.join(BLOG_DIR, "scripts", "check24_links.yaml")

# Kategorien, die in Artikeln vorkommen können (Reihenfolge: längste zuerst für sauberes Matching)
CATEGORIES = [
    "kfz-versicherung", "zahnzusatzversicherung", "reisekrankenversicherung",
    "unfallversicherung", "handytarife", "girokonto", "mietwagen",
    "haftpflicht", "hausrat", "kreditkarte", "tagesgeld", "fluege",
    "kredit", "reisen", "strom", "gas", "dsl",
]


def load_links():
    """Liest scripts/check24_links.yaml – liefert {kategorie: persönlicher_link}."""
    if not os.path.exists(LINKS_FILE):
        sys.exit(f"FEHLER: {LINKS_FILE} nicht gefunden.")
    links = {}
    with open(LINKS_FILE, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*([a-z-]+):\s*[\"'](.+?)[\"']\s*(?:#.*)?$", line)
            if m:
                cat, url = m.group(1), m.group(2)
                if url and not url.startswith("DEIN-LINK"):
                    links[cat] = url
    return links


def replace_in_text(content, links):
    """Ersetzt Standard-Check24-URLs durch persönliche Links. Liefert (text, anzahl)."""
    total = 0
    # 1) Kategorie-Links (z. B. check24.de/strom/)
    for cat in CATEGORIES:
        personal = links.get(cat)
        if not personal:
            continue
        pattern = re.compile(rf"https://www\.check24\.de/{cat}/?")
        for m in list(pattern.finditer(content)):
            if content[m.start():m.start() + len(personal)] == personal:
                continue  # idempotent
            content = content[:m.start()] + personal + content[m.end():]
            total += 1
    # 2) Generischer Link (check24.de/ direkt vor ) oder Leerzeichen/Zeilenende)
    if links.get("allgemein"):
        personal = links["allgemein"]
        pattern = re.compile(r"https://www\.check24\.de/(?=[)\s])")
        for m in list(pattern.finditer(content)):
            if content[m.start():m.start() + len(personal)] == personal:
                continue
            content = content[:m.start()] + personal + content[m.end():]
            total += 1
    return content, total


def process_file(path, links, dry_run):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content, total = replace_in_text(content, links)
    if total and not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return total, os.path.basename(path)


def verify(posts_dir, links):
    """Meldet verbleibende Standard-Check24-URLs (Kategorien ohne Link-Eintrag)."""
    personal_values = list(links.values())
    leftovers = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(posts_dir, fn)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        content, _ = replace_in_text(content, links)
        for m in re.finditer(r"https?://[^\s\)\"]*check24\.de[^\s\)\"]*", content):
            url = m.group(0)
            if not any(url == v or url.startswith(v) for v in personal_values):
                leftovers.append((fn, url))
    return leftovers


def main():
    dry_run = "--dry-run" in sys.argv
    also_topics = "--topics" in sys.argv

    links = load_links()
    print(f"Persönliche Links geladen: {len(links)} Kategorien")
    print("Modus: " + ("VORSCHAU (--dry-run) – es wird nichts geändert" if dry_run else "ERSETZEN"))

    files = sorted(os.listdir(POSTS_DIR))
    md_files = [f for f in files if f.endswith(".md")]
    grand_total = 0
    print(f"\nDurchsuche {len(md_files)} Artikel …")
    for fn in md_files:
        count, name = process_file(os.path.join(POSTS_DIR, fn), links, dry_run)
        if count:
            action = "würde ersetzen" if dry_run else "ersetzt"
            print(f"  ✓ {name}: {count} Link(s) {action}")
            grand_total += count

    if also_topics:
        if os.path.exists(TOPICS_FILE):
            count, name = process_file(TOPICS_FILE, links, dry_run)
            if count:
                action = "würde ersetzen" if dry_run else "ersetzt"
                print(f"  ✓ {name}: {count} Link(s) {action}")
                grand_total += count
        else:
            print("  – data/topics.yaml nicht gefunden, übersprungen.")

    print(f"\nGesamt: {grand_total} Link(s) " + ("betroffen (Vorschau)." if dry_run else "ersetzt."))

    leftovers = verify(POSTS_DIR, links)
    if leftovers:
        print("\n⚠ Diese Standard-Check24-Links bleiben übrig (für diese Kategorien fehlt")
        print("  noch ein Link in scripts/check24_links.yaml):")
        for fn, url in leftovers[:15]:
            print(f"  - {fn}: {url}")
        print("  → Im Partner-Dashboard generieren, in die YAML eintragen, erneut ausführen.")
    else:
        print("✓ Alle Standard-Check24-Links sind durch deine persönlichen Links ersetzt.")

    if dry_run and grand_total:
        print("\nZum echten Ersetzen ohne --dry-run ausführen.")


if __name__ == "__main__":
    main()
