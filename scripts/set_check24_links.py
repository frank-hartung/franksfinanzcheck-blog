#!/usr/bin/env python3
"""
Setzt deine persönlichen CHECK24-Partnerlinks in ALLE Blog-Artikel ein.
Du brauchst nur EINE Sache: deine CHECK24-Partner-ID (die Nummer aus
deinem Partnerlink, z. B. 123456789).

NUTZUNG:

    python3 scripts/set_check24_links.py --id 123456789        # alle Artikel ersetzen
    python3 scripts/set_check24_links.py --id 123456789 --save # ID dauerhaft speichern
    python3 scripts/set_check24_links.py                       # nutzt gespeicherte ID
    python3 scripts/set_check24_links.py --dry-run             # nur Vorschau
    python3 scripts/set_check24_links.py --topics              # auch data/topics.yaml (Bot)

Falls dein Link-Format anders ist (z. B. Parameter "partner" statt "pi"):
    python3 scripts/set_check24_links.py --beispiel "https://www.check24.de/?pi=123456789"
    → Das Skript erkennt Parameter und ID aus EINEM Beispiel-Link und baut
      daraus automatisch alle Kategorien-Links.

Das Skript ist idempotent: Bereits ersetzte Links werden nicht doppelt ersetzt.
Die gespeicherte ID liegt in scripts/check24_id.txt (steht in .gitignore).
"""

import os
import re
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
ID_FILE = os.path.join(BLOG_DIR, "scripts", "check24_id.txt")

# CHECK24-Kategorien, die in den Artikeln vorkommen
CATEGORIES = [
    "strom", "gas", "dsl", "girokonto", "kredit",
    "kfz-versicherung", "reisen", "mietwagen", "fluege",
]

# Link-Vorlage (Standard-Format von CHECK24: Parameter "pi").
# Falls dein Link-Generator ein anderes Format nutzt, passe diese
# EINE Zeile an – oder nutze --beispiel (siehe oben).
PARAM = "pi"


def get_id_and_param(args):
    """Ermittelt Partner-ID und Parametername: --beispiel > --id > gespeicherte Datei."""
    if args.get("beispiel"):
        url = args["beispiel"]
        m = re.search(r"https?://[^\s\"']*check24\.de[^\s\"']*", url)
        if not m:
            sys.exit("FEHLER: Ungültiger Beispiel-Link – er muss check24.de enthalten.")
        parsed = urllib.parse.urlparse(m.group(0))
        query = urllib.parse.parse_qsl(parsed.query)
        digits = [k for k, v in query if re.fullmatch(r"\d+", v)]
        if not digits:
            sys.exit("FEHLER: Keine Partner-ID (Ziffernfolge) im Beispiel-Link gefunden.")
        param = digits[0]
        pid = dict(query)[param]
        return pid, param

    pid = args.get("id") or os.environ.get("CHECK24_ID") or ""
    if pid:
        return pid, PARAM
    if os.path.exists(ID_FILE):
        with open(ID_FILE, encoding="utf-8") as f:
            content = f.read().strip().split()
        if len(content) == 2:
            return content[0], content[1]
        return content[0], PARAM
    sys.exit(
        "FEHLER: Keine CHECK24-Partner-ID gefunden.\n"
        "  Nutze:  python3 scripts/set_check24_links.py --id DEINE_ID\n"
        "  oder:   python3 scripts/set_check24_links.py --id DEINE_ID --save\n"
        "  oder:   python3 scripts/set_check24_links.py --beispiel 'https://www.check24.de/?pi=DEINE_ID'"
    )


def build_link(category, pid, param):
    """Baut einen persönlichen CHECK24-Link: https://www.check24.de/<kategorie>/?pi=<id>"""
    if category == "allgemein":
        return f"https://www.check24.de/?{param}={pid}"
    return f"https://www.check24.de/{category}/?{param}={pid}"


def replace_in_text(content, pid, param):
    """Ersetzt Standard-Check24-URLs durch persönliche Links. Liefert (text, anzahl)."""
    total = 0
    for cat in ["allgemein"] + CATEGORIES:
        personal = build_link(cat, pid, param)
        if cat == "allgemein":
            pattern = re.compile(r"https://www\.check24\.de/(?=[)\s])")
            matches = list(pattern.finditer(content))
        else:
            pattern = re.compile(rf"https://www\.check24\.de/{cat}/?")
            matches = list(pattern.finditer(content))
        for m in matches:
            if content[m.start():m.start() + len(personal)] == personal:
                continue  # bereits ersetzt (idempotent)
            content = content[:m.start()] + personal + content[m.end():]
            total += 1
    return content, total


def process_file(path, pid, param, dry_run):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content, total = replace_in_text(content, pid, param)
    if total and not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return total, os.path.basename(path)


def verify(posts_dir, pid, param):
    """Simuliert die Ersetzung und meldet verbleibende Standard-Check24-URLs."""
    personal_links = [build_link(c, pid, param) for c in ["allgemein"] + CATEGORIES]
    leftovers = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(posts_dir, fn)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        content, _ = replace_in_text(content, pid, param)
        for m in re.finditer(r"https?://[^\s\)\"]*check24\.de[^\s\)\"]*", content):
            url = m.group(0)
            if not any(url == p or url.startswith(p) for p in personal_links):
                leftovers.append((fn, url))
    return leftovers


def main():
    args = {
        "dry_run": "--dry-run" in sys.argv,
        "topics": "--topics" in sys.argv,
        "save": "--save" in sys.argv,
        "beispiel": None,
        "id": None,
    }
    if "--beispiel" in sys.argv:
        idx = sys.argv.index("--beispiel")
        if idx + 1 < len(sys.argv):
            args["beispiel"] = sys.argv[idx + 1]
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        if idx + 1 < len(sys.argv):
            args["id"] = sys.argv[idx + 1]

    pid, param = get_id_and_param(args)
    if not re.fullmatch(r"\d+", pid):
        sys.exit(f"FEHLER: '{pid}' ist keine gültige CHECK24-Partner-ID (nur Ziffern).")

    print(f"CHECK24-Partner-ID: {pid} | Parameter: ?{param}=")
    print("Modus: " + ("VORSCHAU (--dry-run) – nichts wird geändert" if args["dry_run"] else "ERSETZEN"))

    files = sorted(os.listdir(POSTS_DIR))
    md_files = [f for f in files if f.endswith(".md")]
    grand_total = 0
    print(f"\nDurchsuche {len(md_files)} Artikel …")
    for fn in md_files:
        count, name = process_file(os.path.join(POSTS_DIR, fn), pid, param, args["dry_run"])
        if count:
            action = "würde ersetzen" if args["dry_run"] else "ersetzt"
            print(f"  ✓ {name}: {count} Link(s) {action}")
            grand_total += count

    if args["topics"]:
        if os.path.exists(TOPICS_FILE):
            count, name = process_file(TOPICS_FILE, pid, param, args["dry_run"])
            if count:
                action = "würde ersetzen" if args["dry_run"] else "ersetzt"
                print(f"  ✓ {name}: {count} Link(s) {action}")
                grand_total += count
        else:
            print("  – data/topics.yaml nicht gefunden, übersprungen.")

    print(f"\nGesamt: {grand_total} Link(s) " + ("betroffen (Vorschau)." if args["dry_run"] else "ersetzt."))

    leftovers = verify(POSTS_DIR, pid, param)
    if leftovers:
        print("\n⚠ Diese Standard-Check24-URLs bleiben übrig (Kategorie fehlt evtl. in der Liste):")
        for fn, url in leftovers[:15]:
            print(f"  - {fn}: {url}")
    else:
        print("✓ Alle Standard-Check24-Links sind durch deine persönlichen Links ersetzt.")

    if args["save"] and not args["dry_run"]:
        with open(ID_FILE, "w", encoding="utf-8") as f:
            f.write(f"{pid} {param}")
        print("✓ ID gespeichert in scripts/check24_id.txt (Datei ist in .gitignore).")

    if args["dry_run"] and grand_total:
        print("\nZum echten Ersetzen ohne --dry-run ausführen.")


if __name__ == "__main__":
    main()
