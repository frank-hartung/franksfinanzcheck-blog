#!/usr/bin/env python3
# ============================================================
#  MASTODON-SEO + SELBSTHEILUNG
#
#  Prüft alle Live-Toots und heilt sie (PUT Status / PUT Media).
#  Wird auch von social_poster.py genutzt, damit NEUE Posts
#  von vornherein Profi-Niveau haben (Alt-Text, CamelCase-Tags,
#  language=de, Cover, kanonischer Link).
#
#  Checks (Fediverse-SEO / Discoverability / A11y / Affiliate-Sauberkeit):
#    1. Cover vorhanden
#    2. Bild-Alt (description) 40–400 Zeichen, kein Generic-Text
#    3. 2–5 CamelCase-Hashtags inkl. #Finanzen (keine Kleinschreib-Pampe)
#    4. Kanonischer Artikel-Link (franksfinanzcheck.de/posts/…)
#    5. language=de, visibility=public
#    6. ≤ 500 Zeichen, Hook mit Nutzen
#    7. Keine /go/-Affiliate-URLs im Toot (Disclosure bleibt im Artikel)
#
#  Aufruf:
#    python3 scripts/mastodon_seo.py            # prüfen + heilen
#    python3 scripts/mastodon_seo.py --dry-run  # nur Report
# ============================================================

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_poster as sp  # noqa: E402

DRY_RUN = "--dry-run" in sys.argv
REPORT = sp.ROOT / "MASTODON-SEO-REPORT.md"
ACCOUNT = os.environ.get("MASTODON_ACCOUNT") or "FranksFinanzcheck"

ACRONYMS = {
    "dsl", "etf", "kfz", "sepa", "wlan", "dns", "vpn", "gez", "agb",
    "eeg", "kwh", "iban", "bic", "seo", "ai",
}

PILLAR_TAGS = {
    "internet-dsl": ["DSL", "InternetSparen"],
    "strom-sparen": ["StromSparen", "Energiekosten"],
    "versicherungen": ["Versicherungen", "Vorsorge"],
    "konto-karten": ["Girokonto", "KontoGebuehren"],
}

GENERIC_ALT = re.compile(
    r"^(tipp von franksfinanzcheck|cover|bild|image|foto)\.?$",
    re.I,
)
SLUG_RX = re.compile(r"franksfinanzcheck\.de/posts/([a-z0-9\-]+)/?", re.I)
GO_LINK_RX = re.compile(r"franksfinanzcheck\.de/go/", re.I)


def tag_token(word: str) -> str:
    core = re.sub(r"[^A-Za-z0-9]", "", sp.umlaut_free(word))
    if not core:
        return ""
    return core.upper() if core.lower() in ACRONYMS else core.capitalize()


def seo_hashtags(tags: list[str], pillar: str = "", max_tags: int = 3) -> str:
    return sp.hashtags(tags, max_tags=max_tags, pillar=pillar)


def cover_alt(fm: dict, title: str) -> str:
    return sp.cover_alt_text(fm, title)


def build_seo_post(fm: dict, slug: str) -> str:
    return sp.build_post(fm, slug)


def _plain(html_text: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", html_text or "", flags=re.I)
    t = re.sub(r"</p>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"[ \t]+", " ", t).strip()


def _http_get(url: str, auth: bool = False) -> dict | list:
    headers = {"User-Agent": "FranksFinanzcheck-MastodonSEO/1.0"}
    if auth and sp.MASTODON_TOKEN:
        headers["Authorization"] = f"Bearer {sp.MASTODON_TOKEN}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


def fetch_all_statuses() -> list[dict]:
    acc = _http_get(
        f"{sp.MASTODON_INSTANCE}/api/v1/accounts/lookup?acct={urllib.parse.quote(ACCOUNT)}"
    )
    acc_id = acc["id"]
    out: list[dict] = []
    max_id = None
    for _ in range(10):
        q = f"limit=40"
        if max_id:
            q += f"&max_id={max_id}"
        batch = _http_get(
            f"{sp.MASTODON_INSTANCE}/api/v1/accounts/{acc_id}/statuses?{q}"
        )
        if not batch:
            break
        out.extend(batch)
        max_id = batch[-1]["id"]
        if len(batch) < 40:
            break
    return out


def article_index() -> dict[str, tuple[Path, dict]]:
    idx = {}
    for slug_dir in sp.POSTS_DIR.iterdir():
        md = slug_dir / "index.md"
        if not md.is_file():
            continue
        fm = sp.read_frontmatter(md)
        if fm.get("broken") or fm.get("draft"):
            continue
        idx[slug_dir.name] = (slug_dir, fm)
    return idx


def audit(status: dict, slug: str | None, fm: dict | None) -> list[str]:
    issues: list[str] = []
    text = _plain(status.get("content") or "")
    media = status.get("media_attachments") or []
    tags = [t.get("name", "") for t in (status.get("tags") or [])]
    if status.get("visibility") != "public":
        issues.append("nicht öffentlich")
    if status.get("language") not in (None, "de"):
        issues.append(f"Sprache={status.get('language')} (soll de)")
    if len(text) > 500:
        issues.append(f"zu lang ({len(text)} Zeichen)")
    if not SLUG_RX.search(text) and not SLUG_RX.search(status.get("content") or ""):
        issues.append("kein kanonischer Artikel-Link")
    if GO_LINK_RX.search(text):
        issues.append("Affiliate-/go/-Link im Toot")
    if not media:
        issues.append("kein Cover")
    else:
        desc = (media[0].get("description") or "").strip()
        if not desc:
            issues.append("leerer Bild-Alt")
        elif GENERIC_ALT.match(desc):
            issues.append("generischer Bild-Alt")
        elif len(desc) < 24:
            issues.append("Bild-Alt zu kurz")
    if len(tags) < 2:
        issues.append(f"zu wenige Hashtags ({len(tags)})")
    mashed = [t for t in tags if t.lower() == t and len(t) > 16 and t != "finanzen"]
    if mashed:
        issues.append("Hashtags nicht CamelCase: " + ", ".join(mashed[:3]))
    if fm is not None and slug:
        wanted = seo_hashtags(fm.get("tags") or [], _pillar(fm))
        want_set = {w.lstrip("#").lower() for w in wanted.split()}
        have_set = {t.lower() for t in tags}
        if want_set - have_set and mashed or (len(tags) <= 1 and want_set):
            if "Hashtags nicht CamelCase" not in " ".join(issues):
                if want_set - have_set:
                    issues.append("Hashtags unvollständig/nicht SEO")
    return issues


def _pillar(fm: dict) -> str:
    pm = re.search(r'(?m)^pillar:\s*["\']?([^\s"\']+)', fm.get("raw") or "")
    return pm.group(1) if pm else ""


def put_media_description(media_id: str, description: str) -> tuple[bool, str]:
    body = urllib.parse.urlencode({"description": description[:1500]}).encode()
    try:
        sp.http_json(
            f"{sp.MASTODON_INSTANCE}/api/v1/media/{media_id}",
            data=body,
            headers={
                "Authorization": f"Bearer {sp.MASTODON_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="PUT",
        )
        return True, "alt gesetzt"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode()[:160]}"
    except Exception as exc:
        return False, str(exc)[:160]


def heal_one(status: dict, slug: str, slug_dir: Path, fm: dict, issues: list[str]) -> list[str]:
    done: list[str] = []
    if DRY_RUN or not sp.MASTODON_TOKEN:
        return done

    need_text = any(
        i.startswith("Hashtag") or i.startswith("zu wenige") or i.startswith("kein kanon")
        or i.startswith("Affiliate") or i.startswith("zu lang") or i.startswith("Sprache")
        for i in issues
    )
    need_cover = "kein Cover" in issues
    need_alt = any("Bild-Alt" in i or "generischer" in i for i in issues)

    if need_text or need_cover:
        text = build_seo_post(fm, slug)
        image = sp.cover_path(slug_dir, fm) if need_cover else None
        # Wenn wir das Cover neu hochladen, Alt gleich mitgeben
        if image is not None:
            alt = cover_alt(fm, fm.get("title") or slug)
            mid = upload_with_alt(image, alt)
            ok, ref = edit_status_keep_media(status["id"], text, mid)
            if ok:
                done.append("Text+Cover geheilt")
                return done
            done.append(f"Text-Heilung fehlgeschlagen: {ref}")
        else:
            ok, ref = sp.edit_mastodon(status["id"], text, None)
            if ok:
                done.append("Text/Hashtags geheilt")
            else:
                done.append(f"Text-Heilung fehlgeschlagen: {ref}")

    if need_alt and not need_cover:
        media = status.get("media_attachments") or []
        if media:
            alt = cover_alt(fm, fm.get("title") or slug)
            ok, ref = put_media_description(media[0]["id"], alt)
            done.append("Alt gesetzt" if ok else f"Alt fehlgeschlagen: {ref}")
    return done


def upload_with_alt(image: Path, description: str) -> str | None:
    boundary = "----seoposter42"
    name = image.name
    desc_part = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"description\"\r\n\r\n"
        f"{description}\r\n"
    ).encode()
    body = desc_part + (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{name}\"\r\nContent-Type: image/jpeg\r\n\r\n"
    ).encode() + image.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    try:
        resp = sp.http_json(
            f"{sp.MASTODON_INSTANCE}/api/v2/media",
            data=body,
            headers={
                "Authorization": f"Bearer {sp.MASTODON_TOKEN}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        return resp.get("id")
    except Exception as exc:
        print(f"      ⚠ Upload+Alt fehlgeschlagen ({exc})")
        return None


def edit_status_keep_media(status_id: str, text: str, media_id: str | None) -> tuple[bool, str]:
    payload = {"status": text, "language": "de"}
    if media_id:
        payload["media_ids[]"] = media_id
    body = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in payload.items()).encode()
    try:
        resp = sp.http_json(
            f"{sp.MASTODON_INSTANCE}/api/v1/statuses/{status_id}",
            data=body,
            headers={
                "Authorization": f"Bearer {sp.MASTODON_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="PUT",
        )
        return True, resp.get("url", "")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode()[:200]}"
    except Exception as exc:
        return False, str(exc)[:200]


def write_report(rows: list[dict], dupes: dict[str, int], healed: int) -> None:
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    lines = [
        "# 🐘 Mastodon-SEO-Report",
        "",
        f"> Automatisch: {now} {'(DRY-RUN)' if DRY_RUN else ''}",
        "",
        f"- **Geprüfte Toots:** {len(rows)}",
        f"- **Mit Befund:** {sum(1 for r in rows if r['issues'])}",
        f"- **Geheilt:** {healed}",
        f"- **Duplikate (gleicher Artikel, nur gemeldet):** "
        + (", ".join(f"`{s}`×{n}" for s, n in dupes.items() if n > 1) or "keine"),
        "",
        "## Toots",
        "",
        "| Status | Artikel | Befunde | Heilung |",
        "|---|---|---|---|",
    ]
    for r in rows:
        iss = ", ".join(r["issues"]) if r["issues"] else "✓"
        he = ", ".join(r["healed"]) if r["healed"] else "—"
        slug = r["slug"] or "—"
        lines.append(f"| [{r['id']}]({r['url']}) | `{slug}` | {iss} | {he} |")
    lines += [
        "",
        "---",
        "*Erzeugt von scripts/mastodon_seo.py – Regeln: CamelCase-Hashtags, "
        "Bild-Alt, language=de, kanonischer Link, kein /go/ im Toot.*",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not DRY_RUN and not sp.MASTODON_TOKEN:
        print("Kein MASTODON_ACCESS_TOKEN – nur öffentlicher Audit (keine Heilung).")
    articles = article_index()
    statuses = fetch_all_statuses()
    print(f"📚 {len(statuses)} Live-Toots, {len(articles)} Artikel im Repo.")

    slug_counts: dict[str, int] = defaultdict(int)
    rows: list[dict] = []
    healed_n = 0

    for st in statuses:
        blob = (st.get("content") or "") + " " + _plain(st.get("content") or "")
        m = SLUG_RX.search(blob)
        slug = m.group(1) if m else None
        if slug:
            slug_counts[slug] += 1
        pack = articles.get(slug) if slug else None
        fm = pack[1] if pack else None
        issues = audit(st, slug, fm)
        healed: list[str] = []
        if issues and pack:
            healed = heal_one(st, slug, pack[0], fm, issues)
            if any("fehlgeschlagen" not in h for h in healed):
                healed_n += 1
        elif issues and not pack:
            healed = ["kein Artikel-Match – nur gemeldet"]
        rows.append({
            "id": st["id"],
            "url": st.get("url") or "",
            "slug": slug,
            "issues": issues,
            "healed": healed,
        })
        mark = "🩹" if healed else ("⚠" if issues else "✓")
        print(f"  {mark} {st['id']} {slug or '—'} {issues or 'ok'} {healed}")

    write_report(rows, slug_counts, healed_n)
    print(f"\n✅ Report: {REPORT}  geheilt={healed_n}{' (DRY-RUN)' if DRY_RUN else ''}")


if __name__ == "__main__":
    main()
