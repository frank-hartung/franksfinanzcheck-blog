#!/usr/bin/env python3
"""
Setzt deine persönlichen CHECK24-Partner-Links in ALLE Blog-Artikel ein.

Vorbereitung (einmalig):
    cp scripts/check24_links.example.yaml scripts/check24_links.yaml
    # Datei öffnen und pro Kategorie deinen persönlichen Link eintragen

Nutzung:
    python3 scripts/set_check24_links.py            # alle Artikel ersetzen
    python3 scripts/set_check24_links.py --dry-run  # nur Vorschau (ändert nichts)
    python3 scripts/set_check24_links.py --topics   # auch data/topics.yaml (für den Bot)

Die persönliche Konfiguration (scripts/check24_links.yaml) steht in .gitignore
und wird nicht ins Repository committet.
"""

import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
LINKS_FILE = os.path.join(BLOG_DIR, "scripts", "check24_links.yaml")
EXAMPLE_FILE = os.path.join(BLOG_DIR, "scripts", "check24_links.example.yaml")

CATEGORIES = ["allgemein", "strom", "gas", "dsl", "girokonto", "kredit",
              "kfz-versicherung", "reisen", "mietwagen", "fluege"]


def load_links():
    """Liest scripts/check24_links.yaml – liefert {kategorie: persönlicher_link}."""
    if not os.path.exists(LINKS_FILE):
        sys.exit(
            "FEHLER: scripts/check24_links.yaml nicht gefunden.\n"
            f"  Vorlage kopieren:  cp {os.path.relpath(EXAMPLE_FILE, BLOG_DIR)} {os.path.relpath(LINKS_FILE, BLOG_DIR)}\n"
            "  Dann deine persönlichen CHECK24-Links eintragen."
        )
    links = {}
    with open(LINKS_FILE, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*([a-z-]+):\s*[\"'](.+?)[\"']\s*(?:#.*)?$", line)
            if m:
                cat, url = m.group(1), m.group(2)
                if url != "DEIN-LINK":
                    links[cat] = url
    if not links:
        sys.exit(
            "FEHLER: Keine Links eingetragen.\n"
            "  Öffne scripts/check24_links.yaml und ersetze 'DEIN-LINK' durch deine persönlichen Links."
        )
    return links


def replace_in_text(content, links):
    """Ersetzt Standard-Check24-URLs durch persönliche Links. Liefert (neuer_text, anzahl)."""
    total = 0
    for cat in CATEGORIES:
        personal = links.get(cat)
        if not personal:
            continue
        if cat == "allgemein":
            # generischer Link check24.de/ (direkt vor ) oder Leerzeichen/Zeilenende)
            pattern = re.compile(r"https://www\.check24\.de/(?=[)\s])")
            matches = list(pattern.finditer(content))
        else:
            pattern = re.compile(rf"https://www\.check24\.de/{cat}/?")
            matches = list(pattern.finditer(content))
        for m in matches:
            # Bereits ersetzte Links überspringen (idempotent)
            if content[m.start():m.start() + len(personal)] == personal:
                continue
            content = content[:m.start()] + personal + content[m.end():]
            total += 1
    return content, total


def process_file(path, links, dry_run):
    """Ersetzt in einer Datei. Liefert (anzahl, name)."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content, total = replace_in_text(content, links)
    if total and not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return total, os.path.basename(path)


def verify(posts_dir, links):
    """Simuliert die Ersetzung und meldet verbleibende Standard-Check24-URLs (Lücken)."""
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
        print("\n⚠ Diese Standard-Check24-URLs bleiben übrig (Kategorie fehlt evtl. in der Konfiguration):")
        for fn, url in leftovers[:15]:
            print(f"  - {fn}: {url}")
    else:
        print("✓ Alle Standard-Check24-Links sind durch deine persönlichen Links ersetzt.")

    if dry_run and grand_total:
        print("\nZum echten Ersetzen ohne --dry-run ausführen.")


if __name__ == "__main__":
    main()
