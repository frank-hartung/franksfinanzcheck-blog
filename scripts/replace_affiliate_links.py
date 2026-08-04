#!/usr/bin/env python3
"""
Ersetzt CHECK24-Links durch deine persönlichen Awin-Affiliate-Links
in ALLEN Blog-Artikeln auf einmal.

Nutzung:
    python3 scripts/replace_affiliate_links.py               # ersetzen
    python3 scripts/replace_affiliate_links.py --dry-run     # nur Vorschau (nichts ändern)
    python3 scripts/replace_affiliate_links.py --topics      # auch data/topics.yaml ersetzen

Mapping-Datei:  scripts/affiliate_links.yaml
                (Vorlage: scripts/affiliate_links.example.yaml → kopieren und ausfüllen)

Format der Mapping-Datei:
    mappings:
      https://www.check24.de/strom/: "https://www.awin1.com/cread.php?awinmid=123456&p=..."
"""

import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
MAPPING_FILE = os.path.join(BLOG_DIR, "scripts", "affiliate_links.yaml")


def load_mappings():
    """Liest die Mapping-Datei (einfacher YAML-Parser, nur unser Format)."""
    if not os.path.exists(MAPPING_FILE):
        sys.exit(
            "FEHLER: scripts/affiliate_links.yaml nicht gefunden.\n"
            "  Vorlage kopieren:  cp scripts/affiliate_links.example.yaml scripts/affiliate_links.yaml\n"
            "  Dann deine Awin-Links eintragen."
        )
    mappings = {}
    with open(MAPPING_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"^  (\S+):\s*[\"']?(.+?)[\"']?\s*$", line)
            if m and not line.strip().startswith("#"):
                old, new = m.group(1), m.group(2)
                if new and not new.startswith("#"):
                    mappings[old] = new
    if not mappings:
        sys.exit("FEHLER: Keine Zuordnungen in der Mapping-Datei gefunden.")
    return mappings


def process_file(path, mappings, dry_run):
    """Ersetzt alle Vorkommen. Gibt (Anzahl Ersetzungen, Dateiname) zurück."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    total = 0
    for old, new in mappings.items():
        count = content.count(old)
        if count:
            content = content.replace(old, new)
            total += count
    if total == 0:
        return 0, os.path.basename(path)
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return total, os.path.basename(path)


def verify(posts_dir, mappings):
    """Simuliert die Ersetzung im Speicher und meldet direkte CHECK24-Links,
    die nach dem Ersetzen ÜBRIG bleiben würden (echte Lücken der Mapping-Datei)."""
    leftovers = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(posts_dir, fn)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Ersetzung im Speicher simulieren (liest nur, ändert nichts)
        for old, new in mappings.items():
            content = content.replace(old, new)
        for m in re.finditer(r"https?://[^\s\)\"]*check24\.de[^\s\)\"]*", content):
            url = m.group(0)
            if "awin1.com" not in url:
                leftovers.append((fn, url))
    return leftovers


def main():
    dry_run = "--dry-run" in sys.argv
    also_topics = "--topics" in sys.argv

    mappings = load_mappings()
    print(f"Mapping geladen: {len(mappings)} URL-Zuordnungen")
    print("Modus: " + ("VORSCHAU (dry-run) – es wird nichts geändert" if dry_run else "ERSETZEN"))

    files = sorted(os.listdir(POSTS_DIR))
    md_files = [f for f in files if f.endswith(".md")]
    grand_total = 0
    print(f"\nDurchsuche {len(md_files)} Artikel …")
    for fn in md_files:
        path = os.path.join(POSTS_DIR, fn)
        count, name = process_file(path, mappings, dry_run)
        if count:
            action = "würde ersetzen" if dry_run else "ersetzt"
            print(f"  ✓ {name}: {count} Link(s) {action}")
            grand_total += count

    if also_topics:
        count, _ = process_file(TOPICS_FILE, mappings, dry_run)
        if count:
            action = "würde ersetzen" if dry_run else "ersetzt"
            print(f"  ✓ data/topics.yaml: {count} Link(s) {action}")
            grand_total += count

    print(f"\nGesamt: {grand_total} Link(s) " + ("betroffen (Vorschau)." if dry_run else "ersetzt."))

    leftovers = verify(POSTS_DIR, mappings)
    if leftovers:
        print("\n⚠ Diese Links bleiben NACH der Ersetzung übrig (nicht in der Mapping-Datei):")
        for fn, url in leftovers[:15]:
            print(f"  - {fn}: {url}")
        print("  → In scripts/affiliate_links.yaml ergänzen und erneut ausführen.")
    else:
        print("\n✓ Alle CHECK24-Links werden abgedeckt – nach der Ersetzung bleibt kein direkter Link übrig.")

    if dry_run and grand_total:
        print("\nZum echten Ersetzen ohne --dry-run ausführen.")


if __name__ == "__main__":
    main()
