#!/usr/bin/env python3
"""pinterest_engine.py – PINTEREST-AUTOMATISIERUNG (Top-Level, Premium 25.08.2026)

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
  4) MULTI-BOARD-ROUTING (Premium): Jeder Pin geht auf das Board, das zur
     Pinwand/Pillar des Artikels passt – Quelle: data/pinterest_boards.yaml
     (6 Premium-Boards). Board-IDs werden per API aufgelöst und gecacht
     (data/pinterest_boards_cache.json, TTL PINTEREST_BOARD_CACHE_TTL,
     Default 14 Tage). Fehlende Boards werden automatisch angelegt
     (Scope boards:write, Beschreibung aus der Konfiguration). Deaktivierbar
     mit PINTEREST_CREATE_BOARDS=0. Fallback-Board: PINTEREST_BOARD_ID.
  5) REPIN-ROTATION: Artikel, deren Pin älter als ROTATE_DAYS (Default 60)
     ist, werden als „Refresh-Vorschlag" in die Queue aufgenommen –
     menschlicher Repin oder neues Bild.
  6) LINK-GUARD: Vor jedem Lauf heilt der Link-Healer den Masterplan
     (heal_pin_links) – kein Pin kann auf Profil/CHECK24/toten Slug zeigen.

Aufruf:
  python3 scripts/pinterest_engine.py --auto              # posting oder queue
  python3 scripts/pinterest_engine.py --dry-run           # nur anzeigen
  python3 scripts/pinterest_engine.py --list-boards       # Boards + Mapping
  python3 scripts/pinterest_engine.py --audit-profile     # Profil-Audit
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
# UTM-Attribution (Premium 25.08.2026): Pins verlinken Artikel MIT
# Kanal-Markierung → Umami weist Sessions/Absprünge/Events dem Kanal
# „pinterest" sauber zu (Transaktions-Attribution = Analytics-Ebene, die
# Affiliate-Links selbst bleiben kanalneutral, siehe check24_links.yaml).
PIN_UTM = "?utm_source=pinterest&utm_medium=social&utm_campaign=pins"
API = "https://api.pinterest.com/v5"
# Token-Priorität: 1) Auto-Refresh aus data/pinterest_tokens.enc (pinterest_auth.py –
# Token läuft nach 30 Tagen ab, refresh hält ihn automatisch am Leben)
# 2) Fallback: klassisches Secret PINTEREST_ACCESS_TOKEN
try:
    import pinterest_auth
    TOKEN = pinterest_auth.get_access_token() or os.environ.get("PINTEREST_ACCESS_TOKEN", "")
except BaseException as _auth_err:  # noqa: BLE001 – auch SystemExit aus defekter Token-Datei abfangen
    print(f"⚠ Pinterest-Token-Refresh übersprungen ({_auth_err}) – nutze Env-Token.")
    TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "")
ROTATE_DAYS = int(os.environ.get("PINTEREST_ROTATE_DAYS", "60"))
CREATE_BOARDS = os.environ.get("PINTEREST_CREATE_BOARDS", "1") != "0"
QUEUE_FILE = os.path.join(BLOG_DIR, "data", "pin_queue.yaml")
STATUS_FILE = os.path.join(BLOG_DIR, "PIN-STATUS.md")
BOARDS_FILE = os.path.join(BLOG_DIR, "data", "pinterest_boards.yaml")
BOARD_CACHE = os.path.join(BLOG_DIR, "data", "pinterest_boards_cache.json")
BOARD_CACHE_TTL_DAYS = int(os.environ.get("PINTEREST_BOARD_CACHE_TTL", "14"))


# ---------------------------------------------------------------------------
# Board-Konfiguration + Routing (Premium 25.08.2026)
# ---------------------------------------------------------------------------

def _norm_board(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_board_config():
    """Lädt data/pinterest_boards.yaml → (boards, pillar_map, default_name)."""
    try:
        import yaml
        cfg = yaml.safe_load(open(BOARDS_FILE, encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Board-Konfiguration fehlt/ungültig ({e}) – Fallback-Board.")
        return [], {}, ""
    boards = [b for b in cfg.get("boards", []) if b.get("name")]
    pillar_map = {}
    for b in boards:
        for p in b.get("pillars", []) or []:
            pillar_map[str(p).strip().lower()] = b["name"]
    idx = cfg.get("default_board_index", 0)
    default = boards[idx]["name"] if 0 <= idx < len(boards) else (boards[0]["name"] if boards else "")
    return boards, pillar_map, default


def board_name_for(post, board_config):
    """Routet einen Artikel auf ein Board: pinwand → pillar → Default."""
    boards, pillar_map, default = board_config
    pinwand = _norm_board(post.get("pinwand", ""))
    for b in boards:
        if _norm_board(b["name"]) == pinwand:
            return b["name"]
    pillar = str(post.get("pillar", "")).strip().lower()
    if pillar in pillar_map:
        return pillar_map[pillar]
    return default


def load_board_cache():
    try:
        c = json.load(open(BOARD_CACHE, encoding="utf-8"))
        if time.time() - float(c.get("ts", 0)) < BOARD_CACHE_TTL_DAYS * 86400:
            return c.get("boards", {})
    except Exception:
        pass
    return {}


def save_board_cache(boards_map):
    try:
        json.dump({"ts": time.time(), "ttl_days": BOARD_CACHE_TTL_DAYS,
                   "boards": boards_map},
                  open(BOARD_CACHE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    except Exception:
        pass


def api_get(path, token):
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def resolve_boards(token, board_config):
    """Löst Board-Namen → -IDs live auf (mit Cache), legt fehlende Boards an.

    Liefert dict: Board-Name → Board-ID (nur Boards aus der Konfiguration).
    """
    boards, _pm, _default = board_config
    if not boards:
        return {}
    cached = load_board_cache()
    mapping = dict(cached)
    for b in boards:
        if b["name"] in mapping:
            continue
        mapping[b["name"]] = None  # noch zu lösen
    unresolved = [b["name"] for b in boards if mapping.get(b["name"]) is None]
    if not unresolved and mapping:
        return mapping

    try:
        live = api_get("/boards?page_size=100", token).get("items", [])
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Board-Auflösung fehlgeschlagen ({e}) – nutze Fallback-Board.")
        return {}
    for item in live:
        name = item.get("name", "")
        if name in mapping:
            mapping[name] = item["id"]
    # Fehlende Boards anlegen (Premium: 6 saubere Boards statt einem Gemischt)
    for b in boards:
        if mapping.get(b["name"]):
            continue
        if not CREATE_BOARDS:
            continue
        try:
            req = urllib.request.Request(
                f"{API}/boards",
                data=json.dumps({"name": b["name"],
                                 "description": (b.get("description") or "")[:500]}).encode(),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                created = json.loads(resp.read().decode())
            bid = (created.get("item") or {}).get("id") or created.get("id")
            if bid:
                mapping[b["name"]] = bid
                print(f"  ✓ Board angelegt: {b['name']} ({bid})")
        except Exception as e:  # noqa: BLE001
            print(f"⚠ Board-Anlage fehlgeschlagen: {b['name']} ({e})")
    mapping = {k: v for k, v in mapping.items() if v}
    if mapping:
        save_board_cache(mapping)
    return mapping


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

def load_posts():
    posts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        d = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        c = re.search(r'^cover:\s*\n\s*image:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        pinned = re.search(r"^pinned:\s*(true|false)", content, re.M)
        draft = re.search(r"^draft:\s*(true|false)", content, re.M)
        tags = re.search(r"^tags:\s*\[(.*?)\]", content, re.M)
        kws = re.search(r"^keywords:\s*\[(.*?)\]", content, re.M)
        pt = re.search(r"^pin_title:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        pd = re.search(r"^pin_description:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        pillar = re.search(r"^pillar:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        pinwand = re.search(r"^pinwand:\s*[\"']?(.+?)[\"']?\s*$", content, re.M)
        # Bundle- und Legacy-Slug
        if os.path.basename(path) == "index.md":
            slug = os.path.basename(os.path.dirname(path))
        else:
            slug = os.path.basename(path)[:-3]
        kw_list = [t.strip().strip('"') for t in (kws.group(1).split(",") if kws else []) if t.strip()]
        tag_list = [t.strip().strip('"') for t in (tags.group(1).split(",") if tags else []) if t.strip()]
        posts.append({
            "slug": slug, "path": path, "content": content,
            "title": (m.group(1) if m else slug).strip().replace("<br>", " "),
            "description": (d.group(1) if d else "").strip(),
            "cover": (c.group(1) if c else "").strip(),
            "tags": tag_list or kw_list,
            "keywords": kw_list,
            "pin_title": (pt.group(1).strip() if pt else ""),
            "pin_description": (pd.group(1).strip() if pd else ""),
            "pillar": (pillar.group(1).strip() if pillar else ""),
            "pinwand": (pinwand.group(1).strip() if pinwand else ""),
            "pinned": (pinned.group(1) if pinned else "false") == "true",
            # DRAFTS werden NIE gepinnt (Seite existiert nicht live → toter Pin):
            "draft": (draft.group(1) if draft else "false") == "true",
        })
    return posts


def _ascii_tag(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return s


def hashtags_for(post):
    """Erzeugt max. 3 ASCII-Hashtags (Pinterest 2026: keine Umlaute)."""
    pool = [t for t in (post.get("tags") or []) if t]
    pool += [t for t in (post.get("keywords") or []) if t]
    pool += [post["slug"].replace("-", " ")]
    tags = []
    for p in pool:
        words = re.findall(r"[a-z0-9]+", _ascii_tag(p))
        tag = "".join(words)
        if 3 <= len(tag) <= 24 and tag not in tags:
            tags.append(tag)
        if len(tags) >= 3:
            break
    return " ".join("#" + t for t in tags)


def pin_title_of(post):
    """Pin-Titel: Frontmatter pin_title (SEO-geheilt) oder Titel ≤100."""
    t = (post.get("pin_title") or post["title"] or post["slug"]).strip()
    t = re.sub(r"<[^>]+>", "", t)
    return t[:100]


def pin_text(post):
    """Optimierter Pin-Text: Kennzeichnung + Description + CTA + Hashtags (≤ 500).

    Nutzt vorgeheiltes pin_description aus dem Frontmatter (pinterest_seo_healer),
    falls vorhanden – sonst baut den Text frisch.
    """
    if post.get("pin_description"):
        text = post["pin_description"].replace("&", "und")
        return text[:500]
    desc = post["description"] or post["title"]
    desc = desc.replace("&", "und")
    hashtags = hashtags_for(post)
    # Werbekennzeichnung kam bereits über pin_description (Pin-Sync, Single
    # Source of Truth). Fallback hier NICHT generisch als *Werbung markieren,
    # sonst werden EP-Pins fälschlich als Werbung gekennzeichnet. TP-Pins
    # tragen ihren `*Werbung |`-Prefix in der synchronisierten Beschreibung.
    text = f"{desc} Mehr Spartipps auf FranksFinanzcheck! {hashtags}"
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
            f'- slug: "{p["slug"]}"',
            f'  board: "{p.get("board", "")}"',
            f'  title: "{p["title"][:100]}"',
            f'  description: "{p["text"]}"',
            f'  link: "{BASE_URL}/posts/{p["slug"]}/{PIN_UTM}"',
            f'  image: "{BASE_URL}/{p["cover"]}"',
            "",
        ]
    with open(QUEUE_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return len(queue)


# ---------------------------------------------------------------------------
# Pinterest API
# ---------------------------------------------------------------------------

def api_post_pin(token, board_id, post):
    body = {
        "board_id": board_id,
        "media_source": {"source_type": "image_url", "content_type": "image/jpeg",
                         "data": f"{BASE_URL}/{post['cover']}"},
        "description": pin_text(post),
        "link": f"{BASE_URL}/posts/{post['slug']}/{PIN_UTM}",
        "title": pin_title_of(post),
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

def heal_pin_links() -> None:
    """Premium-Guard: Vor jedem Lauf sicherstellen, dass kein Pin auf das
    Pinterest-Profil (Traffic-Sackgasse) oder direkt auf CHECK24 (Spam-Signal)
    zeigt. Heilt data/pinterest_plan.yaml auf die jeweils beste eigene
    Blogseite. Faellt der Healer aus, laeuft die Engine normal weiter."""
    healer = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "pinterest_link_healer.py")
    if not os.path.exists(healer):
        return
    try:
        import subprocess
        r = subprocess.run([sys.executable, healer, "--apply"],
                           capture_output=True, text=True, timeout=120)
        print("Link-Healer:", (r.stdout or r.stderr).strip().splitlines()[0]
              if (r.stdout or r.stderr).strip() else "ok")
    except Exception as e:  # nie den Pin-Lauf blockieren
        print(f"Link-Healer uebersprungen: {e}")


def heal_pin_text_sync() -> None:
    """Premium-Guard (2): Vor jedem Lauf Premium-Pin-Texte + pinwand-Feld
    aus dem Masterplan in die Artikel-Frontmatter synchronisieren.
    Faellt der Sync aus, laeuft die Engine normal weiter."""
    sync = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "pinterest_pin_text_sync.py")
    if not os.path.exists(sync):
        return
    try:
        import subprocess
        r = subprocess.run([sys.executable, sync, "--apply"],
                           capture_output=True, text=True, timeout=180)
        print("Pin-Text-Sync:", (r.stdout or r.stderr).strip().splitlines()[0]
              if (r.stdout or r.stderr).strip() else "ok")
    except Exception as e:  # nie den Pin-Lauf blockieren
        print(f"Pin-Text-Sync uebersprungen: {e}")


def main():
    dry_run = "--dry-run" in sys.argv
    list_boards = "--list-boards" in sys.argv
    audit_profile = "--audit-profile" in sys.argv

    if audit_profile:
        # Profil-Audit delegiert (Reporting, nie fatal für den Pin-Lauf)
        import subprocess
        r = subprocess.run([sys.executable,
                            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "pinterest_profile_audit.py")],
                           capture_output=True, text=True, timeout=300)
        print((r.stdout or "") + (r.stderr or ""))
        return r.returncode

    if not list_boards and not dry_run:
        heal_pin_links()
        heal_pin_text_sync()

    board_config = load_board_config()
    posts = load_posts()
    # Nur ARTIKEL, die live gehen (draft: false), dürfen Pins werden –
    # ein Pin auf eine nicht ausgelieferte Seite ist ein totes Ziel.
    pinnable = [p for p in posts if not p["draft"]]
    drafts_hidden = len(posts) - len(pinnable)
    unpinned = [p for p in pinnable if not p["pinned"]]
    # Refresh-Kandidaten (Pin älter als ROTATE_DAYS)
    refresh = []
    if not dry_run and not list_boards:
        cutoff = datetime.date.today() - datetime.timedelta(days=ROTATE_DAYS)
        for p in posts:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", p["slug"])
            if m and p["pinned"] and m.group(1) < cutoff.isoformat():
                refresh.append(p)

    print(f"Pinterest-Engine: {len(pinnable)} live-Artikel"
          + (f" ({drafts_hidden} Drafts ausgenommen)" if drafts_hidden else "")
          + f", {len(unpinned)} unpinned, {len(refresh)} Refresh-Kandidaten.")

    if list_boards:
        if not TOKEN:
            print("FEHLER: PINTEREST_ACCESS_TOKEN fehlt.")
            return 1
        live = api_get("/boards?page_size=100", TOKEN).get("items", [])
        wanted = {b["name"] for b in board_config[0]}
        for b in live:
            mark = " [SOLL]" if b.get("name") in wanted else " [fremd]"
            print(f"  {b['id']}  {b['name']}{mark}")
        missing = wanted - {b.get("name") for b in live}
        if missing:
            print("  Fehlende SOLL-Boards (werden beim Posten angelegt): "
                  + ", ".join(sorted(missing)))
        return 0

    if dry_run:
        for p in unpinned[:10]:
            board = board_name_for(p, board_config)
            print(f"  - {p['slug']} → [{board}] {pin_text(p)[:80]}…")
        print(f"Würde {len(unpinned)} Pins erstellen (Multi-Board-Routing "
              f"{'aktiv' if board_config[0] else 'aus: Fallback-Board'}).")
        return 0

    if not TOKEN:
        # QUEUE-MODUS: vorbereiten, sauber skippen (kein Fehler!)
        # PINTEREST_BOARD_ID ist in Queue-Modus KEINE Pflicht – das Board wird
        # beim Posten per Routing ermittelt (Board-Auto-Creation).
        queue = [{"slug": p["slug"], "title": pin_title_of(p), "text": pin_text(p),
                  "cover": p["cover"], "board": board_name_for(p, board_config)}
                 for p in unpinned[:10]]
        n = write_queue(queue)
        # DOMAIN-SPERR-WACHE (27.08.2026): Solange Pinterest die Domain
        # gesperrt hat, darf KEIN Pin (weder API noch manuell noch RSS-
        # Auto-Publish) gesetzt werden. Die Queue ist nur VORBEREITUNG.
        blocked_reason = ""
        try:
            import spam_guard as sg
            _blocked, blocked_reason = sg.domain_blocked()
        except Exception:
            _blocked = False
        if _blocked:
            lines = ["**Modus:** Queue (kein PINTEREST_ACCESS_TOKEN) – "
                     "🔴 **DOMAIN BEI PINTEREST GESPERRT**",
                     "",
                     f"- 🔴 **Sperrgrund:** {blocked_reason}",
                     "- ❗ **NICHT manuell pinnen, NICHT RSS-Auto-Publish aktiv,**",
                     "  solange die Sperre besteht (jeder Pin-Versuch verschärft die",
                     "  Abstrafung bis zur Kontolöschung). Vorgehen Schritt für Schritt:",
                     "  **`PINTEREST-SPAM-SPERRE-AKTIONSPLAN.md`**",
                     "- Die Queue unten ist nur VORBEREITUNG für die Zeit NACH der",
                     "  Entsperrung – dann getaktet 2–3 Pins/Tag, niemals alle auf einmal.",
                     "",
                     f"- {n} Pins vorbereitet in `data/pin_queue.yaml`",
                     f"- {len(unpinned)} Artikel warten aufs Posting (nach Entsperrung)",
                     f"- {len(refresh)} Refresh-Kandidaten (älter als {ROTATE_DAYS} Tage)"]
        else:
            lines = [f"**Modus:** Queue (kein PINTEREST_ACCESS_TOKEN)",
                     "", f"- {n} Pins vorbereitet in `data/pin_queue.yaml`",
                     f"- {len(unpinned)} Artikel warten aufs Posting",
                     f"- {len(refresh)} Refresh-Kandidaten (älter als {ROTATE_DAYS} Tage)",
                     "",
                     "**So aktivierst du das Posting:** Pinterest Developer App → Token als "
                     "Secret `PINTEREST_ACCESS_TOKEN` (Board-Routing läuft automatisch, "
                     "siehe `data/pinterest_boards.yaml`; Fallback-Board optional: `PINTEREST_BOARD_ID`)."]
        write_status(lines)
        print("Kein Token – Pin-Queue geschrieben, Workflow skippt sauber (kein Fehler).")
        return 0

    # POSTING-MODUS (Multi-Board-Routing)
    # SPAM-WACHE (26.08.2026): Daueraufsicht über den API-Kanal –
    # A1 Rate-Limit/Pause blockiert das gesamte Posting, A2 prüft jeden
    # Pin vor der Erstellung, A3 reagiert auf Spam-/Rate-Antworten der
    # API (eskalierende Pause), A4 protokolliert jede Erstellung in der
    # Cross-Channel-Pin-Registry. Unbypassbar: läuft IM Engine-Code.
    import spam_guard as sg
    pre_ok, pre_msg = sg.api_preflight()
    if not pre_ok:
        write_status(["**Modus:** Auto-Posting (BLOCKIERT durch Spam-Wache)",
                      "", f"- {pre_msg}",
                      "- NÄCHSTER LAUF: automatisch (Zähler laufen ab)"])
        print(f"Spam-Wache: {pre_msg} – nichts gepostet (keine Spam-Risiken).")
        return 0

    board_map = resolve_boards(TOKEN, board_config) if board_config[0] else {}
    if not board_map and not BOARD_ID:
        print("FEHLER: Kein Board auflösbar (API) und PINTEREST_BOARD_ID fehlt – "
              "nichts gepostet.")
        return 1

    ok, fail = 0, 0
    for p in unpinned[:10]:
        board_name = board_name_for(p, board_config)
        bid = board_map.get(board_name) or board_map.get(
            board_config[2]) or BOARD_ID
        if not bid:
            fail += 1
            print(f"  ✗ {p['slug']}: kein Board-ID für „{board_name}“ – übersprungen")
            continue
        # SPAM-WACHE A2: Pre-Create-Check (Claim/Stuffing/Repeat/Disclosure)
        pin_ok, pin_reasons = sg.api_check_pin({
            "title": pin_title_of(p),
            "description": pin_text(p),
            "link": f"{BASE_URL}/posts/{p['slug']}/{PIN_UTM}",
            "media": f"{BASE_URL}/{p['cover']}",
            "aff_links": len(re.findall(r"\]\(/go/", p["content"]))})
        if not pin_ok:
            fail += 1
            print(f"  ✗ {p['slug']}: Spam-Wache: " + ", ".join(pin_reasons))
            continue
        try:
            api_post_pin(TOKEN, bid, p)
            mark_pinned(p)
            sg.api_record_created({
                "title": pin_title_of(p),
                "description": pin_text(p),
                "link": f"{BASE_URL}/posts/{p['slug']}/{PIN_UTM}",
                "media": f"{BASE_URL}/{p['cover']}",
                "board": board_name, "source": "engine"})
            ok += 1
            print(f"  ✓ Pin erstellt: {p['slug']} → [{board_name}]")
        except urllib.error.HTTPError as e:
            fail += 1
            detail = e.read().decode()[:150] if hasattr(e, "read") else ""
            pause = sg.api_record_error(e.code, detail)
            print(f"  ✗ {p['slug']}: HTTP {e.code} {detail}"
                  + (f" → {pause}" if pause else ""))
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"  ✗ {p['slug']}: {e}")
    write_queue([])
    write_status([f"**Modus:** Auto-Posting (Multi-Board, "
                  f"{len(board_map) or 1} Boards aufgelöst)",
                  "", f"- {ok} Pins erstellt, {fail} Fehler",
                  f"- {len(refresh)} Refresh-Kandidaten für die nächste Runde"])
    print(f"Fertig: {ok} Pins erstellt, {fail} Fehler.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
