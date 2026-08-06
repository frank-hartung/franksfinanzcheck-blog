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
KEY_FILE = os.path.join(BLOG_DIR, "scripts", "indexnow_key.txt")
STATE_FILE = os.path.join(BLOG_DIR, ".indexnow_submitted.json")

HOST = "frank-hartung.github.io"
BASE_URL = f"https://{HOST}/franksfinanzcheck-blog"
INDEXNOW = "https://api.indexnow.org/indexnow"


def get_key():
    if not os.path.exists(KEY_FILE):
        sys.exit("FEHLER: scripts/indexnow_key.txt fehlt.")
    return open(KEY_FILE, encoding="utf-8").read().strip()


def load_published_urls():
    urls = []
    for fn in sorted(os.listdir(POSTS_DIR)):
        if not fn.endswith(".md"):
            continue
        content = open(os.path.join(POSTS_DIR, fn), encoding="utf-8").read()
        if "draft: false" in content:
            urls.append(f"{BASE_URL}/posts/{fn[:-3]}/")
    urls.append(f"{BASE_URL}/")
    return urls


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
        "keyLocation": f"https://{HOST}/franksfinanzcheck-blog/{key}.txt",
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
