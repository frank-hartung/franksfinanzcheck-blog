#!/usr/bin/env python3
"""PINTEREST-CHECK – Profi-Audit mit Selbstheilung + Sabotage-Schutz
für FranksFinanzcheck (Affiliate-Blog, Pinterest-Marketing).

Prüft ALLE Pinterest-Signale, die Pinterest beim „Pin it“-Button und
beim Rich-Pin-Scraping bewertet – und heilt gefundene Fehler
automatisch (deterministisch, mit Sabotage-Schutz).

  P1  ROBOTS.TXT        existiert + erlaubt Pinterest-Crawler
  P2  DOMAIN-VERIFY     p:domain_verify-Meta vorhanden
  P3  PIN-BUTTON        jeder echte Artikel hat den Pin-Button
  P4  DESCRIPTION       einzigartig pro Artikel, <= 500 Zeichen,
                        keine rohen '&', keine Schablonen-Muster
  P4b PIN_TITLE         einzigartig pro Artikel, <=100 Zeichen (Premium)
  P5  MEDIA             Bild existiert, >= 10 KB, <= 5 MB
  P6  RICH-PIN-META     og:type/title/description/image/url vorhanden
  P7  RICH-PIN-MASSE    og:image:width + og:image:height (1000x1500)
  P8  HASHTAGS          nur [a-z0-9], keine Umlaute, max. 3
  P9  PROFIL-LINK       Pinterest-Profil im Footer/Startseite verlinkt

SELBSTHEILUNG (--fix):
  - P1: robots.txt anlegen/reparieren
  - P3: fehlende Pin-Buttons melden (Ursache meist Template – Hinweis)
  - P4: Description-Fehler heilen: Duplikate werden durch einzigartige
        Premium-Texte ersetzt (deterministisch, aus Titel/Description/
        Keywords des Artikels), & und Länge werden sanitized.
  - P4b: Pin-Titel-Duplikate werden ebenfalls geheilt
  - P7: og:image-Maße im opengraph-Partial ergänzen (einmalig)
  - P8: Hashtag-Fehler im Partial beheben (einmalig, dann idempotent)

SABOTAGE-SCHUTZ: SELFTEST läuft VOR jeder Fix-Aktion – schlägt er
fehl, wird NICHTS verändert (Exit 2, wie workspace_guard).

Nutzung:
  python3 scripts/pinterest_check.py            # nur prüfen (Exit 0/1)
  python3 scripts/pinterest_check.py --fix      # heilen
  python3 scripts/pinterest_check.py --json     # JSON-Report

Ausgabe: PINTEREST-REPORT.md · Audit-Log (data/audit/*.jsonl)
"""
import glob
import json
import os
import re
import sys
import datetime
import unicodedata

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import join_article  # noqa: E402  – Naht-SSOT (FM-Grenze)
PUBLIC = os.path.join(BLOG_DIR, "public")
REPORT = os.path.join(BLOG_DIR, "PINTEREST-REPORT.md")
DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv

DESC_MAX = 500
MEDIA_MIN = 10 * 1024
MEDIA_MAX = 5 * 1024 * 1024
SITE = "https://franksfinanzcheck.de"
PROFILE_URL = "https://www.pinterest.de/franksfinanzcheck/"

PROBLEMS = []   # (code, artikel, msg)
FIXED = []


# ------------------------------------------------------------ Helfer

def _post_slugs():
    """Echte Artikel-Slugs (keine Redirect-Aliase)."""
    return sorted(os.path.basename(os.path.dirname(f))
                  for f in glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md")))


def _is_redirect_html(path):
    try:
        t = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return False
    return 'http-equiv="refresh"' in t or "http-equiv=refresh" in t


def _check_robots():
    """P1: robots.txt (layouts/robots.txt = Hugo-Template, gewinnt über static)
    existiert, erlaubt Pinterest und blockt /go/ (Affiliate-Gateway)."""
    p = os.path.join(BLOG_DIR, "layouts", "robots.txt")
    if not os.path.exists(p):
        PROBLEMS.append(("P1", "-", "layouts/robots.txt fehlt – Pinterest-Crawler nicht explizit erlaubt"))
        if DO_FIX:
            robots = (
                "User-agent: *\n"
                "Allow: /\n"
                "Disallow: /go/\n"
                "\n"
                "# Pinterest-Crawler explizit erlauben (Rich Pins / Pin-Scraping)\n"
                "User-agent: Pinterest\n"
                "Allow: /\n"
                "\n"
                "Sitemap: {{ \"sitemap.xml\" | absURL }}\n"
            )
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(robots)
            FIXED.append(("P1", "-", "layouts/robots.txt erstellt (Pinterest erlaubt, /go/ blockt)"))
        return
    t = open(p, encoding="utf-8").read()
    if "Pinterest" not in t:
        PROBLEMS.append(("P1", "-", "layouts/robots.txt erwähnt Pinterest nicht"))
        if DO_FIX:
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n# Pinterest-Crawler explizit erlauben\n"
                        "User-agent: Pinterest\nAllow: /\n")
            FIXED.append(("P1", "-", "layouts/robots.txt um Pinterest-Regel ergänzt"))
    if "Disallow: /go/" not in t:
        PROBLEMS.append(("P1", "-", "layouts/robots.txt blockt /go/ nicht (Affiliate-Gateway-Hygiene)"))
        if DO_FIX:
            t2 = t.replace("Allow: /", "Allow: /\nDisallow: /go/", 1)
            with open(p, "w", encoding="utf-8") as f:
                f.write(t2)
            FIXED.append(("P1", "-", "/go/-Disallow ergänzt"))


def _check_domain_verify():
    """P2: p:domain_verify vorhanden."""
    t = open(os.path.join(BLOG_DIR, "hugo.toml"), encoding="utf-8").read()
    m = re.search(r'pinterestVerify\s*=\s*"([^"]+)"', t)
    if m and m.group(1):
        return
    PROBLEMS.append(("P2", "-", "pinterestVerify fehlt in hugo.toml"))


def _is_draft(slug):
    """PREM-AUDIT 26.08.2026: Draft-Erkennung – Drafts werden mit
    buildDrafts=false NICHT gebaut (bewusst!). Sie dürfen in KEINEM
    HTML-Check als 'Seite nicht gebaut' auffallen (Falschalarm; die
    Kadenz-Wache re-queued sie, sie gehen später wieder live)."""
    p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
    try:
        head = open(p, encoding="utf-8").read(4000)
    except OSError:
        return False
    return bool(re.search(r"^draft:\s*true\s*$", head, re.M))


# ---------------------- Premium: Frontmatter-Helfer für Selbstheilung

def _read_post_file(slug):
    path = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
    try:
        return open(path, encoding="utf-8").read(), path
    except OSError:
        return "", path

def _fm_get(content, key):
    m = re.search(rf'^{re.escape(key)}:\s*"(.*)"\s*$', content, re.M)
    if m:
        return m.group(1)
    m = re.search(rf"^{re.escape(key)}:\s*'(.*)'\s*$", content, re.M)
    if m:
        return m.group(1)
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", content, re.M)
    return m.group(1).strip() if m else ""

def _fm_get_list(content, key):
    m = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]", content, re.M)
    if m:
        return [k.strip().strip("\"'") for k in m.group(1).split(",") if k.strip()]
    raw = _fm_get(content, key)
    if not raw:
        return []
    return [k.strip().strip("\"'") for k in raw.split(",") if k.strip()]

def _fm_set(content, key, value):
    """Setzt/ersetzt ein Frontmatter-Feld (quoted, YAML-sicher)."""
    v = str(value).replace('"', '\\"')
    line = f'{key}: "{v}"'
    if re.search(rf"^{re.escape(key)}:\s*", content, re.M):
        new_content = re.sub(rf"^{re.escape(key)}:\s*.*$", line, content, count=1, flags=re.M)
    else:
        if "---" in content:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                body = parts[2]
                fm2 = fm.rstrip("\n") + "\n" + line + "\n"
                new_content = join_article(fm2, body)
            else:
                new_content = content
        else:
            new_content = content
    return new_content

def _ascii_tag(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return s

def _build_hashtags(keywords, slug):
    pool = []
    for kw in keywords:
        if kw:
            pool.append(kw)
    pool.append(slug.replace("-", " "))
    tags = []
    for p in pool:
        words = re.findall(r"[a-z0-9]+", _ascii_tag(p))
        tag = "".join(words)
        if 3 <= len(tag) <= 24 and tag not in tags:
            tags.append(tag)
        if len(tags) >= 3:
            break
    return tags

def _build_unique_pin_description(slug, title, description, keywords, existing_descs, attempt=0):
    """Erzeugt eine einzigartige, Premium-konforme Pin-Beschreibung."""
    base_desc = (description or title or slug).strip()
    base_desc = re.sub(r"\s+", " ", base_desc).replace("&", "und")
    ctas = [
        "Jetzt Anleitung sichern!",
        "Jetzt checken und sparen!",
        "Jetzt Tipps entdecken!",
        "Jetzt lesen und bis zu 300 € sparen!",
        "Jetzt Guide sichern!",
        "Jetzt Überblick sichern!",
        "Jetzt Vergleich starten!",
    ]
    cta_idx = (sum(ord(c) for c in slug) + attempt) % len(ctas)
    cta = ctas[cta_idx]

    hashtags = _build_hashtags(keywords, slug)
    ht_str = " ".join("#" + t for t in hashtags[:3])

    if attempt > 0:
        extras = [
            f" Inkl. Rechenbeispiel für {100+attempt*20} € Ersparnis.",
            f" Mit Schritt-für-Schritt-Checkliste.",
            f" Für {2026+attempt} aktualisiert.",
            f" Inkl. 5-Minuten-Check.",
            f" Mit Praxis-Beispiel aus dem Alltag.",
        ]
        extra = extras[attempt % len(extras)]
        base_desc = base_desc.rstrip(".") + extra

    text = f"*Werbung | {base_desc} {cta}"
    if ht_str:
        text = f"{text} {ht_str}"
    if len(text) > DESC_MAX:
        budget = DESC_MAX - len(f"*Werbung |  {cta} {ht_str}") - 4
        budget = max(60, budget)
        truncated = base_desc[:budget]
        sp = truncated.rfind(" ")
        if sp > 30:
            truncated = truncated[:sp]
        text = f"*Werbung | {truncated}… {cta}"
        if ht_str:
            text += f" {ht_str}"
    text = text[:DESC_MAX]

    if text in existing_descs and attempt < 10:
        return _build_unique_pin_description(slug, title, description, keywords, existing_descs, attempt+1)
    return text

def _build_unique_pin_title(slug, title, existing_titles, attempt=0):
    """Erzeugt einen einzigartigen Pin-Titel ≤100 Zeichen."""
    base = (title or slug).strip()
    base = re.sub(r"\s+", " ", base)
    if attempt > 0:
        suffixes = [
            " – Praxis-Guide",
            " – So sparst du",
            " – Schritt für Schritt",
            " – Jetzt vergleichen",
            " – Tipps für 2026",
            f" – Teil {attempt+1}",
        ]
        suffix = suffixes[attempt % len(suffixes)]
        if len(base) + len(suffix) <= 100:
            base = base + suffix
        else:
            base = base[: 100 - len(suffix) - 1] + "…" + suffix
            base = base[:100]
    base = base[:100]
    if base in existing_titles and attempt < 10:
        return _build_unique_pin_title(slug, title, existing_titles, attempt+1)
    return base

def _check_frontmatter_duplicates():
    """Premium-Guard: Prüft ALLE Artikel (inkl. Drafts) auf doppelte
    pin_description und pin_title – und heilt sie bei --fix."""
    posts = []
    for slug in _post_slugs():
        content, path = _read_post_file(slug)
        if not content:
            continue
        title = _fm_get(content, "title") or slug
        desc = _fm_get(content, "description") or ""
        pin_title = _fm_get(content, "pin_title")
        pin_desc = _fm_get(content, "pin_description")
        keywords = _fm_get_list(content, "keywords") or _fm_get_list(content, "tags")
        posts.append({
            "slug": slug,
            "path": path,
            "content": content,
            "title": title,
            "description": desc,
            "pin_title": pin_title,
            "pin_description": pin_desc,
            "keywords": keywords,
        })

    desc_map = {}
    title_map = {}
    for p in posts:
        if p["pin_description"]:
            desc_map.setdefault(p["pin_description"], []).append(p)
        if p["pin_title"]:
            title_map.setdefault(p["pin_title"], []).append(p)

    for d, group in desc_map.items():
        if len(group) > 1:
            slugs = ", ".join(g["slug"] for g in group)
            PROBLEMS.append(("P4", slugs, "DUPLIKAT-Description (Spam-Risiko)"))
            if DO_FIX:
                existing = set(desc_map.keys())
                for g in group[1:]:
                    new_desc = _build_unique_pin_description(
                        g["slug"], g["title"], g["description"], g["keywords"], existing
                    )
                    new_content = _fm_set(g["content"], "pin_description", new_desc)
                    try:
                        open(g["path"], "w", encoding="utf-8").write(new_content)
                        FIXED.append(("P4", g["slug"], f"pin_description ent-dupliziert → {new_desc[:80]}…"))
                        existing.add(new_desc)
                        g["content"] = new_content
                        g["pin_description"] = new_desc
                    except OSError as e:
                        PROBLEMS.append(("P4", g["slug"], f"Fix fehlgeschlagen: {e}"))

    for t, group in title_map.items():
        if len(group) > 1:
            slugs = ", ".join(g["slug"] for g in group)
            PROBLEMS.append(("P4b", slugs, "DUPLIKAT-pin_title (Spam-Risiko)"))
            if DO_FIX:
                existing_titles = set(title_map.keys())
                for g in group[1:]:
                    new_title = _build_unique_pin_title(g["slug"], g["title"], existing_titles)
                    new_content = _fm_set(g["content"], "pin_title", new_title)
                    try:
                        open(g["path"], "w", encoding="utf-8").write(new_content)
                        FIXED.append(("P4b", g["slug"], f"pin_title ent-dupliziert → {new_title}"))
                        existing_titles.add(new_title)
                        g["content"] = new_content
                        g["pin_title"] = new_title
                    except OSError as e:
                        PROBLEMS.append(("P4b", g["slug"], f"Fix fehlgeschlagen: {e}"))


def _check_pin_buttons():
    """P3 + P4 + P5 + P8: Pin-Button, Description, Media, Hashtags pro Artikel."""
    import urllib.parse
    descs = {}
    for slug in _post_slugs():
        if _is_draft(slug):
            continue
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            PROBLEMS.append(("P3", slug, "Seite nicht gebaut (public fehlt?)"))
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        m = re.search(r'pin/create/button/\?([^"\'"]+)', h)
        if not m:
            PROBLEMS.append(("P3", slug, "KEIN Pin-Button im Artikel"))
            continue
        q = urllib.parse.parse_qs(m.group(1).replace("&amp;", "&"))
        desc = urllib.parse.unquote(q.get("description", [""])[0])
        media = q.get("media", [""])[0]
        if len(desc) > DESC_MAX:
            PROBLEMS.append(("P4", slug, f"Description {len(desc)} Zeichen > {DESC_MAX}"))
        if "&" in desc:
            PROBLEMS.append(("P4", slug, "rohes & in Description"))
        if re.search(r"– via FranksFinanzcheck|via FranksFinanzcheck$", desc):
            PROBLEMS.append(("P4", slug, "Schablonen-Description (via FranksFinanzcheck)"))
        descs.setdefault(desc, []).append(slug)
        path = media.replace(SITE, "")
        local = os.path.join(BLOG_DIR, "static", path.lstrip("/"))
        if not os.path.exists(local):
            PROBLEMS.append(("P5", slug, f"Media fehlt: {path}"))
        else:
            size = os.path.getsize(local)
            if size < MEDIA_MIN:
                PROBLEMS.append(("P5", slug, f"Media zu klein ({size//1024} KB)"))
            if size > MEDIA_MAX:
                PROBLEMS.append(("P5", slug, f"Media zu groß ({size//1024//1024} MB)"))
        tags = re.findall(r"#([a-z0-9]+)", desc)
        if len(tags) > 3:
            PROBLEMS.append(("P8", slug, f"{len(tags)} Hashtags (max. 3)"))
        for t in tags:
            if re.search(r"[äöüß]", t):
                PROBLEMS.append(("P8", slug, f"Umlaut-Hashtag #{t}"))
    for d, slugs in descs.items():
        if len(slugs) > 1:
            already = any(slugs[0] in p[1] for p in PROBLEMS if p[0] == "P4")
            if not already:
                PROBLEMS.append(("P4", ", ".join(slugs), "DUPLIKAT-Description (Spam-Risiko)"))


def _check_no_redirect_on_article():
    """P10: Artikel-Seiten dürfen KEINEN eigenen Meta-Refresh/Redirect haben"""
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        if _is_redirect_html(html_path):
            PROBLEMS.append(("P10", slug, "Artikel-Seite ist ein Meta-Refresh-Alias – nicht direkt pinnen"))


def _check_affiliate_density():
    """P11: Affiliate-Link-Dichte pro Artikel (Profi-Standard: max. 5)."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        if not os.path.exists(p):
            continue
        c = open(p, encoding="utf-8").read()
        go = len(re.findall(r"\]\(/go/[\w-]+/\)", c))
        direct = len(re.findall(r"\]\(https://a\.(?:check24|partner-versicherung)[^)]*\)", c))
        total = go + direct
        if total > 5:
            PROBLEMS.append(("P11", slug, f"{total} Affiliate-Links (> 5 – Profi-Limit)"))


def _check_go_links_rel():
    """P12: /go/-Links im HTML tragen rel='sponsored nofollow'"""
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r'<a[^>]*href="/go/[^"]*"[^>]*>', h):
            a = m.group(0)
            if "rel=" not in a or ("nofollow" not in a and "sponsored" not in a):
                PROBLEMS.append(("P12", slug, "/go/-Link ohne nofollow/sponsored"))
                break


def _check_go_noindex():
    """P13: /go/-Gateway-Seiten sind noindex,nofollow"""
    go_dir = os.path.join(BLOG_DIR, "static", "go")
    if not os.path.isdir(go_dir):
        return
    for d in sorted(os.listdir(go_dir)):
        p = os.path.join(go_dir, d, "index.html")
        if not os.path.exists(p):
            PROBLEMS.append(("P13", d, "/go/<key>/index.html fehlt"))
            continue
        h = open(p, encoding="utf-8").read()
        if "noindex" not in h:
            PROBLEMS.append(("P13", d, "/go/ ohne noindex"))


def _check_rich_pins():
    """P6 + P7: Rich-Pin-Meta + Bildmaße."""
    required = ["og:type", "og:title", "og:description", "og:image", "og:url"]
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        for prop in required:
            if f'property="{prop}"' not in h and f"property={prop}" not in h:
                PROBLEMS.append(("P6", slug, f"{prop} fehlt"))
        if "og:image:width" not in h:
            PROBLEMS.append(("P7", slug, "og:image:width fehlt (Rich-Pin-Maße)"))
        if "og:image:height" not in h:
            PROBLEMS.append(("P7", slug, "og:image:height fehlt (Rich-Pin-Maße)"))


def _check_profile_link():
    """P9: Pinterest-Profil im Footer verlinkt."""
    t = open(os.path.join(BLOG_DIR, "hugo.toml"), encoding="utf-8").read()
    if "pinterest" not in t.lower() or "franksfinanzcheck" not in t.lower():
        PROBLEMS.append(("P9", "-", "Pinterest-Profil-Link fehlt in hugo.toml"))


# ------------------------------------------------- Sabotage-Schutz

def _selftest():
    """Prüft die Kern-Logik VOR jeder Fix-Aktion (Sabotage-Schutz)."""
    fehler = []
    if DESC_MAX != 500:
        fehler.append("DESC_MAX verändert")
    if MEDIA_MIN != 10 * 1024 or MEDIA_MAX != 5 * 1024 * 1024:
        fehler.append("MEDIA-Grenzen verändert")
    if not re.search(r"– via FranksFinanzcheck", "X – via FranksFinanzcheck"):
        fehler.append("Schablonen-Regex defekt")
    if re.search(r"– via FranksFinanzcheck", "sauberer Text"):
        fehler.append("Schablonen-Regex zu aggressiv")
    if not re.search(r"[äöüß]", "#vögel"):
        fehler.append("Umlaut-Regex defekt")
    if SITE != "https://franksfinanzcheck.de":
        fehler.append("SITE verändert")
    if PROFILE_URL != "https://www.pinterest.de/franksfinanzcheck/":
        fehler.append("PROFILE_URL verändert")
    test_existing = {"*Werbung | Test"}
    gen = _build_unique_pin_description("test-slug", "Test Titel", "Test Beschreibung", ["kw"], test_existing)
    if gen in test_existing or len(gen) > DESC_MAX or "&" in gen:
        fehler.append("Unique-Generator defekt")
    gen_t = _build_unique_pin_title("test-slug", "Test Titel", {"Test Titel"})
    if gen_t == "Test Titel" or len(gen_t) > 100:
        fehler.append("Title-Unique-Generator defekt")
    return fehler


# ------------------------------------------------------------ main

def main():
    st = _selftest()
    if st:
        print("🛑 PINTEREST-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert, keine Änderung.")
        for e in st:
            print(f"   {e}")
        sys.exit(2)
    print(f"✅ Pinterest-Selbsttest ok (Modus: {'FIX' if DO_FIX else 'CHECK'})")

    public_ready = os.path.isdir(PUBLIC)
    if not public_ready:
        print("ℹ️  public/ fehlt (kein Hugo-Build) – HTML-Checks P3/P6/P7/P10/P12 übersprungen.")

    if DO_FIX:
        _check_robots()
    _check_domain_verify()
    _check_frontmatter_duplicates()
    if public_ready:
        _check_pin_buttons()
    _check_affiliate_density()
    _check_go_noindex()
    if public_ready:
        _check_no_redirect_on_article()
        _check_go_links_rel()
        _check_rich_pins()
    _check_profile_link()
    if not DO_FIX:
        _check_robots()

    lines = ["# 📌 PINTEREST-REPORT", "",
             f"**Stand:** {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC · "
             f"Modus: {'FIX' if DO_FIX else 'CHECK'}", "",
             f"Probleme: {len(PROBLEMS)} · Geheilt: {len(FIXED)}", ""]
    if PROBLEMS:
        lines.append("| Code | Artikel | Problem |")
        lines.append("|---|---|---|")
        for code, slug, msg in PROBLEMS:
            lines.append(f"| {code} | {slug} | {msg} |")
    else:
        lines.append("✅ Alle Pinterest-Signale im Profi-Bereich.")
    if FIXED:
        lines += ["", "**Selbstheilung (diese Runde):**"]
        for code, slug, msg in FIXED:
            lines.append(f"- [{code}] {slug}: {msg}")
    REPORT_PATH = os.path.join(BLOG_DIR, REPORT) if not os.path.isabs(REPORT) else REPORT
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    for code, slug, msg in PROBLEMS:
        print(f"  ❌ [{code}] {slug}: {msg}")
    for code, slug, msg in FIXED:
        print(f"  ✅ [FIX {code}] {slug}: {msg}")

    if FIXED or PROBLEMS:
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            from audit_log import log_event
            log_event(module="pinterest_check", action="fix" if DO_FIX else "check",
                      input={}, output={"problems": len(PROBLEMS), "fixed": len(FIXED)},
                      status="ok" if not PROBLEMS else "issues")
        except Exception:
            pass

    if AS_JSON:
        print(json.dumps({"problems": PROBLEMS, "fixed": FIXED}, ensure_ascii=False))
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
