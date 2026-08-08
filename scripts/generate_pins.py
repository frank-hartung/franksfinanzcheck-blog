#!/usr/bin/env python3
"""
Automatisches Nachpinnen der Blog-Artikel bei Pinterest (Pinterest API v5).

Funktionsweise:
  - Liest alle Artikel aus content/posts/ mit "pinned: false" im Frontmatter
  - Erstellt für jeden Artikel einen Pin über die Pinterest API v5
    (Bild = Artikel-Cover, Beschreibung = Meta-Description + Hashtags,
     Link = Artikel-URL)
  - Setzt danach "pinned: true" im Frontmatter (damit jeder Artikel nur
    EINMAL gepinnt wird)

Voraussetzungen (einmalig, siehe ANLEITUNG-PINTEREST-API.md):
  - Pinterest-Developer-App + Access-Token (Umgebungsvariable PINTEREST_ACCESS_TOKEN)
  - Board-ID (Umgebungsvariable PINTEREST_BOARD_ID) – per --list-boards ermittelbar

Nutzung:
    PINTEREST_ACCESS_TOKEN=... PINTEREST_BOARD_ID=... python3 scripts/generate_pins.py
    PINTEREST_ACCESS_TOKEN=... python3 scripts/generate_pins.py --list-boards
    python3 scripts/generate_pins.py --dry-run        # zeigt, was gepinnt würde
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths

BASE_URL = os.environ.get("BLOG_BASE_URL", "https://frank-hartung.github.io/franksfinanzcheck-blog")
API = "https://api.pinterest.com/v5"


def load_posts():
    """Liest alle Artikel mit pinned-Flag."""
    posts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        d = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        c = re.search(r'^cover:\s*\n\s*image:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        pinned = re.search(r"^pinned:\s*(true|false)", content, re.M)
        slug = fn[:-3]
        posts.append({
            "file": fn,
            "slug": slug,
            "title": (m.group(1) if m else slug).strip(),
            "description": (d.group(1) if d else "").strip(),
            "cover": (c.group(1) if c else "").strip(),
            "pinned": (pinned.group(1) if pinned else "false") == "true",
            "path": path,
            "content": content,
        })
    return posts


def get_boards(token):
    """Listet alle Boards (für --list-boards)."""
    req = urllib.request.Request(
        f"{API}/boards?page_size=50",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("items", [])


def create_pin(token, board_id, title, description, link, image_url):
    """Erstellt einen Pin über die API v5."""
    body = {
        "board_id": board_id,
        "media_source": {
            "source_type": "image_url",
            "content_type": "image/jpeg",
            "data": image_url,
        },
        "description": description,
        "link": link,
        "title": title[:100],
    }
    req = urllib.request.Request(
        f"{API}/pins",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def mark_pinned(post):
    """Setzt pinned: true im Frontmatter."""
    content = post["content"]
    if re.search(r"^pinned:\s*(true|false)", content, re.M):
        content = re.sub(r"^pinned:\s*(true|false)", "pinned: true", content, count=1, flags=re.M)
    else:
        # Nach der Zeile "draft: ..." einfügen (oder nach dem ersten ---)
        content = re.sub(r"^(draft:.*)$", r"\1\npinned: true", content, count=1, flags=re.M)
    with open(post["path"], "w", encoding="utf-8") as f:
        f.write(content)


def main():
    dry_run = "--dry-run" in sys.argv
    list_boards = "--list-boards" in sys.argv
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "").strip()
    board_id = os.environ.get("PINTEREST_BOARD_ID", "").strip()

    if list_boards:
        if not token:
            sys.exit("FEHLER: PINTEREST_ACCESS_TOKEN fehlt.")
        print("Deine Pinterest-Boards:")
        for b in get_boards(token):
            print(f"  {b.get('id')}  ←  {b.get('name')}")
        return

    if not token:
        if dry_run:
            print("(Trockenlauf ohne Token – nur Anzeige, nichts wird gepinnt)")
        else:
            sys.exit("FEHLER: PINTEREST_ACCESS_TOKEN fehlt (siehe ANLEITUNG-PINTEREST-API.md).")
    if not board_id and not dry_run:
        sys.exit("FEHLER: PINTEREST_BOARD_ID fehlt – erst mit --list-boards ermitteln.")

    posts = load_posts()
    to_pin = [p for p in posts if not p["pinned"]]
    print(f"{len(posts)} Artikel gefunden, davon {len(to_pin)} noch nicht gepinnt.")
    if not to_pin:
        print("✅ Alles ist bereits gepinnt – nichts zu tun.")
        return

    if dry_run:
        print("\n(Vorschau – nichts wird gepinnt)")
        for p in to_pin:
            print(f"  • {p['title'][:60]}")
            print(f"    → {BASE_URL}/posts/{p['slug']}/")
        return

    ok = 0
    for p in to_pin:
        image = p["cover"]
        if image.startswith("/"):
            image = BASE_URL + image
        elif not image.startswith("http"):
            image = f"{BASE_URL}/images/covers/{p['slug']}.jpg"
        link = f"{BASE_URL}/posts/{p['slug']}/"
        desc = (p["description"] or p["title"])[:490]
        desc += "\n\n#GeldSparen #Spartipps #FranksFinanzcheck"
        try:
            result = create_pin(token, board_id, p["title"], desc, link, image)
            mark_pinned(p)
            ok += 1
            print(f"  ✅ Gepinnt: {p['title'][:55]}")
            print(f"     Pin-ID: {result.get('id', '?')}")
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:200]
            print(f"  ❌ Fehler bei '{p['title'][:40]}': HTTP {e.code} – {err}")
        except Exception as e:
            print(f"  ❌ Fehler bei '{p['title'][:40]}': {e}")

    print(f"\nFertig: {ok} von {len(to_pin)} Artikeln gepinnt.")


if __name__ == "__main__":
    main()
