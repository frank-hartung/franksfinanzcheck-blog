#!/usr/bin/env python3
"""
Automatische Indexierung über IndexNow (Bing/Seznam/Naver/Yandex – kostenlos).

IndexNow ist das offizielle Push-Protokoll von Microsoft/Bing: Man meldet
neue/geänderte URLs sofort – ohne Bing-API-Key, ohne Konto-Verwirrung.
Funktioniert mit GitHub-Pages-Unterordnern zuverlässig (anders als die
klassische Bing SubmitUrl-API).

Voraussetzung (einmalig):
  - Eine Datei NAMENS <dein-key>.txt liegt im Wurzelverzeichnis der Website
    (static/ im Repo) und enthält nur den Key. → SCHON EINGERICHT!

Nutzung:
    python3 scripts/submit_indexnow.py            # alle neuen URLs einreichen
    python3 scripts/submit_indexnow.py --dry-run  # Vorschau
    python3 scripts/submit_indexnow.py --all      # alle URLs (auch schon eingereichte)

Das Skript merkt sich eingereichte URLs in .indexnow_submitted.json.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths, slug_of
KEY_FILE = os.path.join(BLOG_DIR, "scripts", "indexnow_key.txt")
STATE_FILE = os.path.join(BLOG_DIR, ".indexnow_submitted.json")

HOST = "franksfinanzcheck.de"
BASE_URL = f"https://{HOST}"
INDEXNOW = "https://api.indexnow.org/indexnow"


def get_key():
    if not os.path.exists(KEY_FILE):
        sys.exit("FEHLER: scripts/indexnow_key.txt fehlt.")
    return open(KEY_FILE, encoding="utf-8").read().strip()


def load_published_urls():
    urls = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        if "draft: false" in content:
            urls.append(f"{BASE_URL}/posts/{slug_of(path)}/")
    # GEO/SEO-PREMIUM 21.09.2026: Die sechs Themen-Ratgeber sind die
    # umsatzstärksten URLs der Site – sie wurden nie per IndexNow an
    # Bing/Yandex/Naver/Seznam gemeldet (nur Posts + Home). Gleiches gilt
    # für die beiden Hubs und die Vertrauensseite Methodik. Bereits
    # gemeldete URLs filtert der State (.indexnow_submitted.json) heraus,
    # ein Re-Push kostet also nichts und hält die Money-Pages frisch.
    for slug in ("strom-sparen", "internet-dsl", "versicherungen",
                 "konto-karten", "frugalismus", "mietwagen"):
        urls.append(f"{BASE_URL}/pillar/{slug}/")
    for hub in ("posts", "pillar", "methodik"):
        urls.append(f"{BASE_URL}/{hub}/")
    urls.append(f"{BASE_URL}/")
    return urls


def refresh_llms_txt():
    """GEO-Begleitdatei static/llms.txt aus den Live-Inhalten erneuern.

    Läuft bei jedem IndexNow-Lauf mit (wöchentlich + bei jedem neuen
    Artikel); die Workflows committen das Ergebnis per `git add -A`.
    Absichtlich feuerfest: Ein Fehler hier darf die Indexierung nie
    blockieren (Premium-Härtung #233 lässt grüßen).
    """
    try:
        import subprocess
        gen = os.path.join(BLOG_DIR, "scripts", "generate_llms_txt.py")
        r = subprocess.run([sys.executable, gen], capture_output=True,
                           text=True, timeout=120)
        print((r.stdout or "").strip() or "llms.txt: Generator ohne Ausgabe.")
        if r.returncode != 0:
            print(f"⚠️ llms.txt-Generator meldete Exit {r.returncode}: "
                  f"{(r.stderr or '')[:200]}")
    except Exception as e:  # noqa: BLE001 – Feuerfest-Prinzip, siehe oben
        print(f"⚠️ llms.txt-Aktualisierung übersprungen: {e}")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(state), f, indent=1)


def submit(urls, key):
    """Sendet URLs an IndexNow (Batch)."""
    body = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/{key}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(
        INDEXNOW,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    dry_run = "--dry-run" in sys.argv
    all_urls = "--all" in sys.argv
    key = get_key()

    urls = load_published_urls()
    submitted = load_state()
    if all_urls:
        new_urls = urls
    else:
        new_urls = [u for u in urls if u not in submitted]

    print(f"{len(urls)} URLs verfügbar, davon {len(new_urls)} neu für IndexNow.")
    refresh_llms_txt()
    if not new_urls:
        print("✅ Alles bereits eingereicht – nichts zu tun.")
        return

    if dry_run:
        print("\n(Vorschau – würde einreichen:)")
        for u in new_urls[:10]:
            print(f"  • {u}")
        if len(new_urls) > 10:
            print(f"  … und {len(new_urls)-10} weitere")
        return

    try:
        status = submit(new_urls, key)
        if status in (200, 202):
            print(f"✅ {len(new_urls)} URLs erfolgreich bei IndexNow eingereicht (HTTP {status})")
            submitted.update(new_urls)
            save_state(submitted)
        else:
            print(f"⚠️ IndexNow antwortete mit HTTP {status}")
    except urllib.error.HTTPError as e:
        print(f"❌ IndexNow-Fehler: HTTP {e.code}")
        print(f"   {e.read().decode()[:300]}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
