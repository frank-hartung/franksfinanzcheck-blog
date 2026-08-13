#!/usr/bin/env python3
# ============================================================
#  SOCIAL-POSTER (Social-Media-Automatisierung)
#
#  Postet neue Blogartikel automatisch auf Social Media:
#    - Mastodon  (kostenlos, Token läuft NICHT ab) – Hauptkanal
#    - LinkedIn  (optional; Token läuft nach ~60 Tagen ab!)
#
#  Ablauf:
#    1. Findet alle veröffentlichten Artikel-Bundles
#       (content/posts/<slug>/index.md) ohne "social_posted: true"
#    2. Baut den Post-Text: Titel + Kurzantwort-Hook + Link + Hashtags
#    3. Lädt das Cover-Bild hoch (falls vorhanden) und postet
#    4. Setzt "social_posted: true" + schreibt Log & SOCIAL-STATUS.md
#
#  OHNE Token: zeigt eine Setup-Anleitung und endet SAUBER (exit 0,
#  kein Fehler-Alerting) – wie pinterest_engine.py.
#
#  Konfiguration (Settings → Secrets and variables → Actions):
#    Secret:   MASTODON_ACCESS_TOKEN   (Setup siehe ANLEITUNG-SOCIAL-MEDIA.md)
#    Variable: MASTODON_INSTANCE       (optional, Default: https://mastodon.social)
#    Secret:   LINKEDIN_ACCESS_TOKEN   (optional)
#    Variable: LINKEDIN_PERSON_URN     (optional, z. B. "urn:li:person:AbC123")
#    Variable: SOCIAL_MAX_PRO_LAUF     (optional, Default: 4)
#
#  Lokale Tests:
#    python3 scripts/social_poster.py --dry-run      # zeigt Posts, sendet nichts
#    python3 scripts/social_poster.py --mark-all-posted  # alle Altb estand als "gepostet" markieren
# ============================================================

import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"
STATUS_FILE = ROOT / "SOCIAL-STATUS.md"
LOG_FILE = ROOT / "data" / "social_log.jsonl"
BASE_URL = "https://franksfinanzcheck.de"

# ACHTUNG: GitHub-Actions setzt nicht existierende Vars als LEEREN String
# ("${{ vars.X }}" -> "") – daher "or" statt get-Default!
MASTODON_TOKEN = (os.environ.get("MASTODON_ACCESS_TOKEN") or "").strip()
MASTODON_INSTANCE = (os.environ.get("MASTODON_INSTANCE") or "https://mastodon.social").strip().rstrip("/")
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
LINKEDIN_URN = os.environ.get("LINKEDIN_PERSON_URN", "").strip()
MAX_PER_RUN = int(os.environ.get("SOCIAL_MAX_PRO_LAUF") or "4")
DRY_RUN = "--dry-run" in sys.argv
MARK_ALL = "--mark-all-posted" in sys.argv


# ------------------------------------------------------------- Hilfsfunktionen

def _frontmatter_span(text: str):
    """Findet den Front-Matter-Block tolerant.

    Robust gegen defekte Dateien, bei denen das schließende '---' NICHT auf
    eigener Zeile steht (z. B. '---Die WLAN-Verbindung …' – echtes Vorkommnis
    im Repo). Gibt (fm_text, fence_start, fence_end) zurück oder None.
    """
    if not text.startswith("---\n"):
        return None
    m = re.search(r"(?m)^---", text[4:])
    if not m:
        return None
    fence_start = 4 + m.start()
    fence_end = 4 + m.end()
    return text[4:fence_start], fence_start, fence_end


def read_frontmatter(index_md: Path) -> dict:
    """Liest die YAML-Frontmatter grob aus (tolerant, ohne PyYAML-Zwang)."""
    text = index_md.read_text(encoding="utf-8")
    span = _frontmatter_span(text)
    if not span:
        return {"broken": True}
    fm = span[0]
    def field(name):
        m2 = re.search(rf'^{name}:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
        return m2.group(1) if m2 else ""
    def list_field(name):
        m2 = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.MULTILINE)
        if not m2:
            return []
        return [t.strip().strip('"').strip("'") for t in m2.group(1).split(",") if t.strip()]
    return {
        "title": field("title"),
        "description": field("description"),
        "kurzantwort": field("kurzantwort"),
        "tags": list_field("tags"),
        "draft": field("draft").lower() == "true",
        "broken": False,
        "raw": fm,
    }


def set_social_flag(index_md: Path) -> None:
    """Fügt 'social_posted: true' in die Frontmatter ein (idempotent)."""
    text = index_md.read_text(encoding="utf-8")
    if re.search(r"^social_posted:", text, re.MULTILINE):
        return
    span = _frontmatter_span(text)
    if not span:
        return
    _, fence_start, _ = span
    new_text = text[:fence_start] + "social_posted: true\n" + text[fence_start:]
    index_md.write_text(new_text, encoding="utf-8")


def find_unposted() -> list[Path]:
    """Alle veröffentlichten Artikel ohne social_posted-Flag, NEUESTE zuerst."""
    bundles = []
    for slug_dir in sorted(POSTS_DIR.iterdir()):
        index_md = slug_dir / "index.md"
        if not index_md.is_file():
            continue
        fm = read_frontmatter(index_md)
        if fm.get("draft") or "social_posted: true" in fm.get("raw", ""):
            continue
        bundles.append(index_md)
    return list(reversed(bundles))  # neueste Slugs (YYYY-MM-DD-…) zuerst


def umlaut_free(s: str) -> str:
    return (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
             .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss"))


ACRONYMS = {"dsl", "etf", "kfz", "sepa", "wlan", "dns", "vpn", "gez", "agb", "eeg", "kwh", "iban", "bic"}


def hashtags(tags: list[str], max_tags: int = 3) -> str:
    """Baut CamelCase-Hashtags aus Artikel-Tags.

    BUGFIX (13.08.): reines .capitalize() pro Wort zerstörte bekannte
    Abkürzungen (z. B. 'ETF' -> '#Etf', 'DSL' -> '#Dsl') – wirkt auf Mastodon
    unprofessionell. Bekannte Abkürzungen (ACRONYMS) bleiben jetzt komplett
    großgeschrieben.
    """
    result = []
    for tag in tags[:max_tags]:
        parts = []
        for w in re.split(r"[\s\-]+", umlaut_free(tag)):
            core = re.sub(r"[^A-Za-z0-9]", "", w)
            if not core:
                continue
            parts.append(core.upper() if core.lower() in ACRONYMS else core.capitalize())
        camel = "".join(parts)
        if camel:
            result.append(f"#{camel}")
    if "#Finanzen" not in result:
        result.append("#Finanzen")
    return " ".join(result)


def build_post(fm: dict, slug: str) -> str:
    """Mastodon-Limit: 500 Zeichen. Kurzantwort bevorzugen (Hook!), sonst Description."""
    url = f"{BASE_URL}/posts/{slug}/"
    title = fm.get("title") or slug.replace("-", " ").title()
    hook = fm.get("kurzantwort") or fm.get("description") or ""
    # Hook auf max. 240 Zeichen am Wortende kürzen
    if len(hook) > 240:
        hook = hook[:240].rsplit(" ", 1)[0] + " …"
    tags = hashtags(fm.get("tags", []))
    text = f"📌 {title}\n\n{hook}\n\n🔗 {url}\n\n{tags}"
    return text[:497] + "…" if len(text) > 500 else text


def cover_path(slug_dir: Path, fm: dict) -> Path | None:
    """Löst den Cover-Pfad auf.

    BUGFIX (13.08.): 'cover.image' in der Frontmatter ist – wie vom Theme via
    '| absURL' behandelt (layouts/_partials/cover.html) – site-root-relativ
    (z. B. 'images/covers/<slug>.jpg' -> static/images/covers/<slug>.jpg),
    NICHT relativ zum Page-Bundle-Ordner. Die alte Version suchte fälschlich
    unter content/posts/<slug>/images/covers/... (existiert nie, da alle
    Cover unter static/ liegen) und fand dadurch NIE ein Bild – jeder bisherige
    Mastodon-Post ging ohne Bild raus. Fällt zur Sicherheit weiterhin auf einen
    Page-Bundle-Pfad zurück, falls doch mal ein Artikel sein Cover als
    Bundle-Resource mitbringt.
    """
    m = re.search(r"image:\s*[\"']?(.*?)[\"']?\s*$", fm.get("raw", ""), re.MULTILINE)
    if not m:
        return None
    rel = m.group(1)
    static_candidate = ROOT / "static" / rel
    if static_candidate.is_file():
        return static_candidate
    bundle_candidate = slug_dir / rel
    return bundle_candidate if bundle_candidate.is_file() else None


def http_json(url: str, data=None, headers=None, method="POST") -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


# ------------------------------------------------------------------ Mastodon

def mastodon_upload_media(image: Path) -> str | None:
    boundary = "----socialposter42"
    name = image.name
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{name}\"\r\nContent-Type: image/jpeg\r\n\r\n"
    ).encode() + image.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    try:
        resp = http_json(
            f"{MASTODON_INSTANCE}/api/v2/media",
            data=body,
            headers={
                "Authorization": f"Bearer {MASTODON_TOKEN}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        return resp.get("id")
    except Exception as exc:
        print(f"      ⚠ Medien-Upload fehlgeschlagen ({exc}) – poste ohne Bild.")
        return None


def post_mastodon(text: str, image: Path | None) -> tuple[bool, str]:
    media_id = mastodon_upload_media(image) if image else None
    payload = {"status": text, "visibility": "public"}
    if media_id:
        payload["media_ids[]"] = media_id
    body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in payload.items()).encode()
    try:
        resp = http_json(
            f"{MASTODON_INSTANCE}/api/v1/statuses",
            data=body,
            headers={
                "Authorization": f"Bearer {MASTODON_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        return True, resp.get("url", "")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode()[:200]}"
    except Exception as exc:
        return False, str(exc)[:200]


def get_status_mastodon(status_id: str) -> dict:
    req = urllib.request.Request(
        f"{MASTODON_INSTANCE}/api/v1/statuses/{status_id}",
        headers={"Authorization": f"Bearer {MASTODON_TOKEN}"} if MASTODON_TOKEN else {},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def edit_mastodon(status_id: str, text: str) -> tuple[bool, str]:
    """Bearbeitet einen bereits veröffentlichten Status (PUT statt POST) –
    z. B. um nachträglich bessere Hashtags zu setzen, ohne einen Duplikat-Post
    zu erzeugen. WICHTIG: Mastodon entfernt beim Edit angehängte Medien, wenn
    'media_ids[]' nicht erneut mitgeschickt werden – deshalb wird das
    vorhandene Bild zuerst per GET ausgelesen und unverändert mitgesendet."""
    try:
        current = get_status_mastodon(status_id)
    except Exception as exc:  # noqa: BLE001
        return False, f"Status nicht lesbar: {exc}"
    payload = {"status": text}
    media = current.get("media_attachments") or []
    if media:
        payload["media_ids[]"] = media[0]["id"]
    body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in payload.items()).encode()
    try:
        resp = http_json(
            f"{MASTODON_INSTANCE}/api/v1/statuses/{status_id}",
            data=body,
            headers={
                "Authorization": f"Bearer {MASTODON_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="PUT",
        )
        return True, resp.get("url", "")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode()[:200]}"
    except Exception as exc:
        return False, str(exc)[:200]


# ------------------------------------------------------------------ LinkedIn

def post_linkedin(text: str, url: str) -> tuple[bool, str]:
    """UGC-Post mit Link. HINWEIS: LinkedIn-Tokens laufen nach ~60 Tagen ab."""
    payload = {
        "author": LINKEDIN_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text[:1300]},
                "shareMediaCategory": "ARTICLE",
                "media": [{"status": "READY", "originalUrl": url}],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        resp = http_json(
            "https://api.linkedin.com/v2/ugcPosts",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {LINKEDIN_TOKEN}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        return True, resp.get("id", "")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode()[:200]}"
    except Exception as exc:
        return False, str(exc)[:200]


# -------------------------------------------------------------------- Status

def write_status(posted: list[str], remaining: int) -> None:
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    lines = [
        "# 📣 Social-Media-Status", "",
        f"> Automatisch aktualisiert: {now}", "",
        f"- **Mastodon:** {'🟢 aktiv' if MASTODON_TOKEN else '⚪ nicht eingerichtet'} ({MASTODON_INSTANCE})",
        f"- **LinkedIn:** {'🟢 aktiv' if LINKEDIN_TOKEN else '⚪ nicht eingerichtet'} (Achtung: Token läuft ~60 Tage)",
        f"- **Offene Artikel in der Queue:** {remaining}",
        f"- **Max. Posts pro Lauf:** {MAX_PER_RUN}", "",
    ]
    if posted:
        lines += ["## Zuletzt gepostet (dieser Lauf)", ""]
        lines += [f"- {p}" for p in posted]
        lines.append("")
    lines += ["---", "*Erzeugt von scripts/social_poster.py – Setup: ANLEITUNG-SOCIAL-MEDIA.md*"]
    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_log(slug: str, platform: str, ok: bool, ref: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "date": datetime.now(timezone.utc).isoformat(),
            "slug": slug, "platform": platform, "ok": ok, "ref": ref,
        }, ensure_ascii=False) + "\n")


# -------------------------------------------------------------------- Main

def main() -> None:
    if MARK_ALL:
        count = 0
        for slug_dir in POSTS_DIR.iterdir():
            index_md = slug_dir / "index.md"
            if index_md.is_file():
                before = index_md.stat().st_mtime
                set_social_flag(index_md)
                count += index_md.stat().st_mtime != before
        print(f"✔ {count} Artikel als gepostet markiert (kein Nachsenden von Altbeständen).")
        return

    if not MASTODON_TOKEN and not LINKEDIN_TOKEN:
        print("=" * 68)
        print("SOCIAL-POSTER: Kein API-Token gefunden – überspringe sauber (exit 0).")
        print("")
        print("AKTIVIEREN (Mastodon, kostenlos, ~5 Minuten):")
        print("  1. Account auf einer Mastodon-Instanz erstellen (z. B. mastodon.social)")
        print("  2. Dort: Einstellungen → Entwicklung → Neue Anwendung")
        print("     (Scopes: write:statuses write:media)")
        print("  3. Zugriffstoken kopieren → GitHub-Repo → Settings → Secrets and")
        print("     variables → Actions → Secret MASTODON_ACCESS_TOKEN")
        print("  4. Optional: Variable MASTODON_INSTANCE (Default: https://mastodon.social)")
        print("  Details: ANLEITUNG-SOCIAL-MEDIA.md")
        print("=" * 68)
        return

    unposted = find_unposted()
    print(f"📚 {len(unposted)} Artikel in der Social-Queue (neueste zuerst).")
    batch = unposted[:MAX_PER_RUN]
    posted_lines, failures = [], 0

    for index_md in batch:
        slug_dir = index_md.parent
        slug = slug_dir.name
        fm = read_frontmatter(index_md)
        text = build_post(fm, slug)
        url = f"{BASE_URL}/posts/{slug}/"
        image = cover_path(slug_dir, fm)
        print(f"  → {slug}")

        if DRY_RUN:
            print("    [DRY-RUN] Würde posten:")
            print("    " + text.replace("\n", "\n    "))
            continue

        any_success = False
        if MASTODON_TOKEN:
            ok, ref = post_mastodon(text, image)
            append_log(slug, "mastodon", ok, ref)
            print(f"    Mastodon: {'✅ ' + ref if ok else '❌ ' + ref}")
            any_success |= ok
            if not ok:
                failures += 1
        if LINKEDIN_TOKEN and LINKEDIN_URN:
            ok, ref = post_linkedin(text, url)
            append_log(slug, "linkedin", ok, ref)
            print(f"    LinkedIn: {'✅' if ok else '❌ ' + ref}")
            any_success |= ok

        if any_success:
            set_social_flag(index_md)
            posted_lines.append(f"{fm.get('title') or slug} → {url}")

    remaining = 0 if DRY_RUN else len(unposted) - len(posted_lines)
    write_status(posted_lines, remaining)
    print(f"\n✅ {len(posted_lines)} Artikel gepostet, {remaining} in der Queue. "
          f"Fehler: {failures}{' (DRY-RUN)' if DRY_RUN else ''}")

    # Komplettausfall = echter Fehler (→ Fehler-Alerting greift)
    if not DRY_RUN and batch and not posted_lines and failures:
        sys.exit("FEHLER: Alle Social-Posts in diesem Lauf sind fehlgeschlagen.")


if __name__ == "__main__":
    main()
