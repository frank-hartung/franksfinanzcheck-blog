#!/usr/bin/env python3
"""
Setzt deine persönlichen Awin-Affiliate-Links in ALLE Blog-Artikel ein.

Du brauchst nur EINE Sache: deine Awin-Partner-ID (die Zahl nach awinmid=,
z. B. 1234567). Das Skript baut daraus automatisch die richtigen
Deep-Links für jede CHECK24-Kategorie (Strom, Gas, DSL, Girokonto,
Kredit, Kfz, Reisen, Mietwagen, Flüge + generische Links) und ersetzt
alle direkten check24.de-Links in den Artikeln.

NUTZUNG (3 Möglichkeiten, gleichwertig):

    python3 scripts/set_awin_links.py --awin-id 1234567   # direkt
    AWIN_ID=1234567 python3 scripts/set_awin_links.py     # Umgebungsvariable
    python3 scripts/set_awin_links.py                     # liest scripts/awin_id.txt

Optionen:
    --dry-run   Nur Vorschau (ändert nichts)
    --topics    Auch data/topics.yaml umstellen (für künftige Bot-Artikel)
    --save      ID dauerhaft in scripts/awin_id.txt speichern (wird nicht committet)

Das Skript ist idempotent: Es überschreibt auch bereits gesetzte Awin-Links,
wenn sich deine ID ändert.
"""

import os
import re
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
ID_FILE = os.path.join(BLOG_DIR, "scripts", "awin_id.txt")

# CHECK24-Kategorien, die in den Artikeln vorkommen
CATEGORIES = [
    "strom", "gas", "dsl", "girokonto", "kredit",
    "kfz-versicherung", "reisen", "mietwagen", "fluege",
]


def get_awin_id(args):
    """Ermittelt die Awin-ID: Argument > Umgebungsvariable > Datei."""
    if args.get("awin_id"):
        return args["awin_id"]
    env = os.environ.get("AWIN_ID")
    if env:
        return env
    if os.path.exists(ID_FILE):
        with open(ID_FILE, encoding="utf-8") as f:
            return f.read().strip()
    sys.exit(
        "FEHLER: Keine Awin-ID gefunden.\n"
        "  Nutze:  python3 scripts/set_awin_links.py --awin-id DEINE_ID\n"
        "  oder:   AWIN_ID=DEINE_ID python3 scripts/set_awin_links.py\n"
        "  oder:   ID einmalig mit --save speichern."
    )


def build_awin_link(awin_id, target_url):
    """Baut einen Awin-Deep-Link: https://www.awin1.com/cread.php?awinmid=X&p=<urlencoded>"""
    encoded = urllib.parse.quote(target_url, safe="")
    return f"https://www.awin1.com/cread.php?awinmid={awin_id}&p={encoded}"


def replace_in_text(text, awin_id):
    """Ersetzt in einem Text alle check24.de-Links durch Awin-Links.
    Liefert (neuer_text, anzahl_ersetzungen)."""
    count = 0

    def sub_check24(match, target):
        nonlocal count
        count += 1
        return build_awin_link(awin_id, target)

    # 1) Kategorie-Links zuerst (mit/ohne Slash am Ende)
    for cat in CATEGORIES:
        pattern = re.compile(rf"https://www\.check24\.de/{cat}/?")
        text = pattern.sub(lambda m: sub_check24(m, f"https://www.check24.de/{cat}/"), text)

    # 2) Generische Links (check24.de/ direkt, gefolgt von ) oder Leerzeichen/Ende)
    pattern = re.compile(r"https://www\.check24\.de/(?=[)\s])")
    text = pattern.sub(lambda m: sub_check24(m, "https://www.check24.de/"), text)

    # 3) Bereits gesetzte Awin-Links auf neue ID aktualisieren (idempotent)
    old_id_count = len(re.findall(r"awinmid=\d+", text))
    text = re.sub(r"awinmid=\d+", f"awinmid={awin_id}", text)
    if old_id_count:
        count += old_id_count

    return text, count


def process_file(path, awin_id, dry_run):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content, count = replace_in_text(content, awin_id)
    if count == 0:
        return 0, os.path.basename(path)
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return count, os.path.basename(path)


def verify(posts_dir, awin_id):
    """Simuliert die Ersetzung im Speicher und meldet verbleibende direkte
    check24.de-Links (echte Lücken der Kategorien-Liste). Ändert nichts."""
    leftovers = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(posts_dir, fn)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Ersetzung simulieren (liest nur)
        content, _ = replace_in_text(content, awin_id)
        for m in re.finditer(r"https?://[^\s\)\"]*check24\.de[^\s\)\"]*", content):
            url = m.group(0)
            if "awin1.com" not in url:
                leftovers.append((fn, url))
    return leftovers


def main():
    args = {
        "dry_run": "--dry-run" in sys.argv,
        "topics": "--topics" in sys.argv,
        "save": "--save" in sys.argv,
    }
    if "--awin-id" in sys.argv:
        idx = sys.argv.index("--awin-id")
        if idx + 1 < len(sys.argv):
            args["awin_id"] = sys.argv[idx + 1]

    awin_id = get_awin_id(args)
    if not re.fullmatch(r"\d+", awin_id):
        sys.exit(f"FEHLER: '{awin_id}' ist keine gültige Awin-ID (nur Ziffern).")

    print(f"Awin-ID: {awin_id}")
    print("Modus: " + ("VORSCHAU (--dry-run) – nichts wird geändert" if args["dry_run"] else "ERSETZEN"))

    files = sorted(os.listdir(POSTS_DIR))
    md_files = [f for f in files if f.endswith(".md")]
    grand_total = 0
    print(f"\nDurchsuche {len(md_files)} Artikel …")
    for fn in md_files:
        count, name = process_file(os.path.join(POSTS_DIR, fn), awin_id, args["dry_run"])
        if count:
            action = "würde ersetzen" if args["dry_run"] else "ersetzt"
            print(f"  ✓ {name}: {count} Link(s) {action}")
            grand_total += count

    if args["topics"]:
        count, name = process_file(TOPICS_FILE, awin_id, args["dry_run"])
        if count:
            action = "würde ersetzen" if args["dry_run"] else "ersetzt"
            print(f"  ✓ {name}: {count} Link(s) {action}")
            grand_total += count

    print(f"\nGesamt: {grand_total} Link(s) " + ("betroffen (Vorschau)." if args["dry_run"] else "ersetzt."))

    leftovers = verify(POSTS_DIR, awin_id)
    if leftovers:
        print("\n⚠ Diese check24-Links sind übrig geblieben (Kategorien evtl. nicht in der Liste):")
        for fn, url in leftovers[:15]:
            print(f"  - {fn}: {url}")
    else:
        print("✓ Keine direkten check24.de-Links mehr in den Artikeln.")

    if args["save"] and not args["dry_run"]:
        with open(ID_FILE, "w", encoding="utf-8") as f:
            f.write(awin_id)
        print(f"✓ ID in scripts/awin_id.txt gespeichert (Datei ist in .gitignore, wird nicht committet).")

    if args["dry_run"] and grand_total:
        print("\nZum echten Ersetzen ohne --dry-run ausführen.")


if __name__ == "__main__":
    main()
