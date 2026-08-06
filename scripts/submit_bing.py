#!/usr/bin/env python3
"""
Automatische Indexierung bei Bing (kostenlose Bing-Webmaster-API).

Reicht alle neuen Artikel-URLs bei Bing ein, damit sie schnell indexiert
werden (Bing liefert auch Daten an DuckDuckGo & ChatGPT-Suche).

Voraussetzung (einmalig, kostenlos, ~5 Min.):
  1. Bing Webmaster Tools: https://www.bing.com/webmasters → kostenlos anmelden
     (kann Daten aus der Google Search Console importieren!)
  2. Website hinzufügen: https://frank-hartung.github.io/franksfinanzcheck-blog
  3. Verifizieren (wie bei Google – Meta-Tag oder Datei)
  4. API-Key: Einstellungen → API-Zugriff → API-Key kopieren

Nutzung:
    BING_API_KEY=... python3 scripts/submit_bing.py
    BING_API_KEY=... python3 scripts/submit_bing.py --dry-run   # Vorschau

Das Skript merkt sich eingereichte URLs in .bing_submitted.json
(liegt im Repo, damit jeder Artikel nur einmal eingereicht wird).
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
STATE_FILE = os.path.join(BLOG_DIR, ".bing_submitted.json")

BASE_URL = "https://frank-hartung.github.io/franksfinanzcheck-blog"
BING_URL = "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl"


def load_published_urls():
    urls = []
    for fn in sorted(os.listdir(POSTS_DIR)):
        if not fn.endswith(".md"):
            continue
        content = open(os.path.join(POSTS_DIR, fn), encoding="utf-8").read()
        if "draft: false" in content:
            urls.append(f"{BASE_URL}/posts/{fn[:-3]}/")
    return urls


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(state), f, indent=1)


def submit_url(api_key, url):
    data = json.dumps({"url": url}).encode()
    req = urllib.request.Request(
        f"{BING_URL}?apikey={api_key}",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    dry_run = "--dry-run" in sys.argv
    api_key = os.environ.get("BING_API_KEY", "").strip()

    if not api_key and not dry_run:
        sys.exit("FEHLER: BING_API_KEY fehlt (siehe Anleitung im Skript-Kopf).")

    urls = load_published_urls()
    submitted = load_state()
    new_urls = [u for u in urls if u not in submitted]

    print(f"{len(urls)} Artikel veröffentlicht, davon {len(new_urls)} noch nicht bei Bing eingereicht.")
    if not new_urls:
        print("✅ Alles bereits eingereicht – nichts zu tun.")
        return

    if dry_run:
        print("\n(Vorschau – würde einreichen:)")
        for u in new_urls:
            print(f"  • {u}")
        return

    ok = 0
    for url in new_urls:
        try:
            status = submit_url(api_key, url)
            submitted.add(url)
            ok += 1
            print(f"  ✅ Eingereicht ({status}): {url}")
            time.sleep(1)  # Rate-Limit schonen
        except urllib.error.HTTPError as e:
            print(f"  ❌ Fehler bei {url}: HTTP {e.code}")
        except Exception as e:
            print(f"  ❌ Fehler bei {url}: {e}")

    save_state(submitted)
    print(f"\nFertig: {ok} URLs bei Bing eingereicht.")


if __name__ == "__main__":
    main()
