#!/usr/bin/env python3
"""pinterest_engine.py – PINTEREST-AUTOMATISIERUNG (Top-Level)

Erweitert die einfache generate_pins.py um eine vollständige Pin-Engine:

  1) PIN-TEXT-OPTIMIERUNG:  Titel ≤ 100 Zeichen (API-Limit), Beschreibung =
     Meta-Description + Ziel-Keyword + Call-to-Action + automatisch
     generierte Hashtags (aus Tags/Keywords/Silo). Keine Duplikate.
  2) PIN-QUEUE (ohne Token): Wenn PINTEREST_ACCESS_TOKEN fehlt, werden alle
     vorbereiteten Pins als data/pin_queue.yaml exportiert + PIN-STATUS.md
     geschrieben. Der Workflow skippt sauber (exit 0, KEIN Fehler-Alert).
  3) AUTO-POSTING (mit Token): Postet alle Artikel mit pinned:false über
     die Pinterest API v5 (Cover-Bild vom Blog), setzt pinned:true und
     aktualisiert PIN-STATUS.md.
  4) REPIN-ROTATION: Artikel, deren Pin älter als ROTATE_DAYS (Default 60)
     ist, werden als „Refresh-Vorschlag" in die Queue aufgenommen –
     menschlicher Repin oder neues Bild.

Aufruf:
  python3 scripts/pinterest_engine.py --auto              # posting oder queue
  python3 scripts/pinterest_engine.py --dry-run           # nur anzeigen
  python3 scripts/pinterest_engine.py --list-boards       # Boards (Token nötig)
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths  # noqa: E402

BASE_URL = os.environ.get("BLOG_BASE_URL", "https://franksfinanzcheck.de")
API = "https://api.pinterest.com/v5"
# Token-Priorität: 1) Auto-Refresh aus data/pinterest_tokens.enc (pinterest_auth.py –
# Token läuft nach 30 Tagen ab, refresh hält ihn automatisch am Leben)
# 2) Fallback: klassisches Secret PINTEREST_ACCESS_TOKEN
try:
    import pinterest_auth
    TOKEN = pinterest_auth.get_access_token() or os.environ.get("PINTEREST_ACCESS_TOKEN", "")
except Exception as _auth_err:
    print(f"⚠ Pinterest-Token-Refresh übersprungen ({_auth_err}) – nutze Env-Token.")
    TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "")
ROTATE_DAYS = int(os.environ.get("PINTEREST_ROTATE_DAYS", "60"))
QUEUE_FILE = os.path.join(BLOG_DIR, "data", "pin_queue.yaml")
STATUS_FILE = os.path.join(BLOG_DIR, "PIN-STATUS.md")


def load_posts():
    posts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        d = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        c = re.search(r'^cover:\s*\n\s*image:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        pinned = re.search(r"^pinned:\s*(true|false)", content, re.M)
        tags = re.search(r"^tags:\s*\[(.*?)\]", content, re.M)
        slug = os.path.basename(os.path.dirname(path))
        posts.append({
            "slug": slug, "path": path, "content": content,
            "title": (m.group(1) if m else slug).strip().replace("<br>", " "),
            "description": (d.group(1) if d else "").strip(),
            "cover": (c.group(1) if c else "").strip(),
            "tags": [t.strip().strip('"') for t in (tags.group(1).split(",") if tags else [])],
            "pinned": (pinned.group(1) if pinned else "false") == "true",
        })
    return posts


def hashtags_for(post):
    """Erzeugt 3–4 relevante Hashtags aus Tags + Titel (ohne Sonderzeichen)."""
    pool = [t for t in post["tags"] if t] + [post["slug"].replace("-", " ")]
    tags = []
    for p in pool:
        words = re.findall(r"[a-zäöüß0-9]+", p.lower())
        tag = "".join(words)
        if 3 <= len(tag) <= 24 and tag not in tags:
            tags.append(tag)
        if len(tags) >= 4:
            break
    return " ".join("#" + t for t in tags)


def pin_text(post):
    """Optimierter Pin-Text: Kennzeichnung + Description + CTA + Hashtags (≤ 500 Zeichen)."""
    desc = post["description"]
    if not desc:
        desc = post["title"]
    hashtags = hashtags_for(post)
    # Werbekennzeichnung (deutsches Recht): Artikel enthalten Affiliate-Links,
    # daher Pins vorangestellt als Werbung deklarieren.
    text = f"*Werbung | {desc} Mehr Spartipps auf FranksFinanzcheck! {hashtags}"
    return text[:500]


def write_status(lines):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    header = ["# 📌 PIN-STATUS (Pinterest-Automatisierung)", "",
              f"**Stand:** {now}", ""]
    with open(STATUS_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header + lines))


def write_queue(queue):
    """Schreibt vorbereitete Pins als YAML-Queue (ohne Token nutzbar)."""
    lines = ["# PIN-QUEUE – von der Pinterest-Engine vorbereitete Pins",
             "# (wird nach erfolgreichem Posting geleert)", ""]
    for p in queue:
        lines += [
            f"- slug: \"{p['slug']}\"",
            f"  title: \"{p['title'][:100]}\"",
            f"  description: \"{p['text']}\"",
            f"  link: \"{BASE_URL}/posts/{p['slug']}/\"",
            f"  image: \"{BASE_URL}/{p['cover']}\"",
            "",
        ]
    with open(QUEUE_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return len(queue)


# ---------------------------------------------------------------------------
# Pinterest API
# ---------------------------------------------------------------------------

def api_get(path, token):
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def api_post_pin(token, board_id, post):
    body = {
        "board_id": board_id,
        "media_source": {"source_type": "image_url", "content_type": "image/jpeg",
                         "data": f"{BASE_URL}/{post['cover']}"},
        "description": pin_text(post),
        "link": f"{BASE_URL}/posts/{post['slug']}/",
        "title": post["title"][:100],
    }
    req = urllib.request.Request(f"{API}/pins", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def mark_pinned(post):
    content = post["content"]
    if re.search(r"^pinned:\s*(true|false)", content, re.M):
        content = re.sub(r"^pinned:\s*(true|false)", "pinned: true", content, count=1, flags=re.M)
    else:
        content = re.sub(r"^(draft:.*)$", r"\1\npinned: true", content, count=1, flags=re.M)
    with open(post["path"], "w", encoding="utf-8") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ANTI-SPAM-RATE-LIMIT (Pinterest): Max. Pins PRO LAUF + Pause dazwischen.
# Pinterest flaggt massenhaftes Pinnen in kurzer Zeit als Spam (Fehler
# „möglicher Spam“ beim manuellen Pinnen). Daher: 3 Pins pro Workflow-Lauf,
# je 45 s Abstand – statt 10 am Stück. Über PINS_PRO_TAG konfigurierbar.
PINS_PRO_TAG = int(os.environ.get("PINS_PRO_TAG", "3"))
PIN_PAUSE_S = int(os.environ.get("PIN_PAUSE_S", "45"))


def main():
    dry_run = "--dry-run" in sys.argv
    list_boards = "--list-boards" in sys.argv

    posts = load_posts()
    unpinned = [p for p in posts if not p["pinned"]]
    # Refresh-Kandidaten (Pin älter als ROTATE_DAYS)
    refresh = []
    if not dry_run and not list_boards:
        cutoff = datetime.date.today() - datetime.timedelta(days=ROTATE_DAYS)
        for p in posts:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", p["slug"])
            if m and p["pinned"] and m.group(1) < cutoff.isoformat():
                refresh.append(p)

    print(f"Pinterest-Engine: {len(posts)} Artikel, {len(unpinned)} unpinned, {len(refresh)} Refresh-Kandidaten.")

    if list_boards:
        if not TOKEN:
            print("FEHLER: PINTEREST_ACCESS_TOKEN fehlt.")
            return 1
        for b in api_get("/boards?page_size=50", TOKEN).get("items", []):
            print(f"  {b['id']}  {b['name']}")
        return 0

    if dry_run:
        for p in unpinned[:PINS_PRO_TAG]:
            print(f"  - {p['slug']}: {pin_text(p)[:90]}…")
        print(f"Würde {len(unpinned)} Pins erstellen.")
        return 0

    if not TOKEN or not BOARD_ID:
        # QUEUE-MODUS: vorbereiten, sauber skippen (kein Fehler!)
        queue = [{"slug": p["slug"], "title": p["title"], "text": pin_text(p),
                  "cover": p["cover"]} for p in unpinned[:PINS_PRO_TAG]]
        n = write_queue(queue)
        lines = [f"**Modus:** Queue (kein PINTEREST_ACCESS_TOKEN/BOARD_ID)",
                 "", f"- {n} Pins vorbereitet in `data/pin_queue.yaml`",
                 f"- {len(unpinned)} Artikel warten aufs Posting",
                 f"- {len(refresh)} Refresh-Kandidaten (älter als {ROTATE_DAYS} Tage)",
                 "",
                 "**So aktivierst du das Posting:** Pinterest Developer App → Token als "
                 "Secret `PINTEREST_ACCESS_TOKEN`, Board-ID als Variable `PINTEREST_BOARD_ID`."]
        write_status(lines)
        print("Kein Token – Pin-Queue geschrieben, Workflow skippt sauber (kein Fehler).")
        return 0

    # POSTING-MODUS
    ok, fail = 0, 0
    for p in unpinned[:PINS_PRO_TAG]:
        try:
            api_post_pin(TOKEN, BOARD_ID, p)
            mark_pinned(p)
            ok += 1
            print(f"  ✓ Pin erstellt: {p['slug']}")
            if ok < min(PINS_PRO_TAG, len(unpinned)):
                time.sleep(PIN_PAUSE_S)  # Anti-Spam-Abstand
        except urllib.error.HTTPError as e:
            fail += 1
            detail = e.read().decode()[:150] if hasattr(e, "read") else ""
            print(f"  ✗ {p['slug']}: HTTP {e.code} {detail}")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"  ✗ {p['slug']}: {e}")
    write_queue([])
    write_status([f"**Modus:** Auto-Posting (Board {BOARD_ID})",
                  "", f"- {ok} Pins erstellt, {fail} Fehler",
                  f"- {len(refresh)} Refresh-Kandidaten für die nächste Runde"])
    print(f"Fertig: {ok} Pins erstellt, {fail} Fehler.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
