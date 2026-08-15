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
from post_utils import list_post_paths
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
    """Ersetzt Standard-Check24-URLs durch persönliche Links. Liefert (text, anzahl).

    WICHTIG: Die URLs werden nur ersetzt, wenn danach ein Begrenzer folgt
    (Slash, Klammer, Leerzeichen, Anführungszeichen oder Zeilenende).
    So wird NIE mitten in Wörtern ersetzt (z. B. "Gasheizung" bleibt unangetastet).
    """
    total = 0
    # Begrenzer nach der Kategorie-URL: / ) Leerzeichen " ' oder Ende
    boundary = r'(?=/|\)|\s|["\']|$)'
    # 1) Kategorie-Links (z. B. check24.de/strom/)
    #    re.sub ersetzt alle Matches in einem Durchlauf korrekt (kein Offset-Problem).
    for cat in CATEGORIES:
        personal = links.get(cat)
        if not personal:
            continue
        pattern = re.compile(rf"https://www\.check24\.de/{cat}(?:/)?{boundary}")
        new_content, n = pattern.subn(lambda m: personal, content)
        total += n
        content = new_content
    # 2) Generischer Link (check24.de/ direkt vor ) oder Leerzeichen/Zeilenende)
    if links.get("allgemein"):
        personal = links["allgemein"]
        pattern = re.compile(r"https://www\.check24\.de/(?=[)\s])")
        new_content, n = pattern.subn(lambda m: personal, content)
        total += n
        content = new_content
    return content, total


def check_word_breaks(posts_dir, links):
    """Sicherheits-Check: Meldet URLs, die MITTEN IN WÖRTERN stecken
    (Zeichen vor der URL ist ein Buchstabe). Sollte nie vorkommen."""
    problems = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(posts_dir, fn)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"https?://", content):
            start = m.start()
            if start > 0 and content[start - 1].isalnum():
                problems.append((fn, content[max(0, start - 20):start + 40]))
    return problems


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
    for path in md_files:
        fn = os.path.relpath(path, BLOG_DIR)
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

    md_files = list_post_paths()
    grand_total = 0
    print(f"\nDurchsuche {len(md_files)} Artikel …")
    for fn in md_files:
        count, name = process_file(fn, links, dry_run)
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

    word_breaks = check_word_breaks(POSTS_DIR, links)
    if word_breaks:
        print("\n⚠ ACHTUNG: URLs mitten in Wörtern gefunden (Sicherheits-Check):")
        for fn, snippet in word_breaks[:10]:
            print(f"  - {fn}: …{snippet}…")
    else:
        print("✓ Sicherheits-Check: keine URLs mitten in Wörtern.")

    if dry_run and grand_total:
        print("\nZum echten Ersetzen ohne --dry-run ausführen.")


if __name__ == "__main__":
    main()
