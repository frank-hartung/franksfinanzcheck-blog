#!/usr/bin/env python3
"""
Professionelles SEO-Audit für den Blog (kostenlos, automatisch).

Prüft alle Artikel auf die wichtigsten On-Page-SEO-Faktoren:
  - Titel-Länge (50-60 Zeichen, SEO-optimal)
  - Meta-Description (120-160 Zeichen)
  - Keywords im Titel/Description
  - H1/H2-Struktur (genau 1 H1, 2+ H2)
  - Bilder mit Alt-Text
  - Interne Links (min. 2 pro Artikel)
  - Wortanzahl (min. 300 Wörter)
  - Cover-Bild vorhanden
  - Sitemap-Konsistenz (alle Artikel in sitemap.xml)

Nutzung:
    python3 scripts/seo_audit.py            # Standard-Audit
    python3 scripts/seo_audit.py --json     # Ausgabe als JSON (für Reports)

Exit-Code: 0 = ok, 1 = kritische SEO-Probleme gefunden
"""
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
PUBLIC_DIR = os.path.join(BLOG_DIR, "public")

# SEO-Schwellenwerte (Google-Best-Practices)
TITLE_MIN, TITLE_MAX = 30, 65
DESC_MIN, DESC_MAX = 70, 165
WORDS_MIN = 300
INTERNAL_LINKS_MIN = 2


def load_posts():
    """Lädt Artikel als Page-Bundles (content/posts/<slug>/index.md).

    13.08.2026 BUGFIX: Vorher wurde mit os.listdir(POSTS_DIR) + fn.endswith(".md")
    nach flachen .md-Dateien direkt in POSTS_DIR gesucht – die Seite nutzt aber
    ausschließlich Page-Bundles (content/posts/<slug>/index.md). Das listete
    IMMER 0 Artikel und der komplette Audit lief seit Einführung als No-Op
    ("Alles auf Profi-Niveau", ohne je einen Artikel geprüft zu haben).
    """
    posts = []
    for slug in sorted(os.listdir(POSTS_DIR)):
        bundle_dir = os.path.join(POSTS_DIR, slug)
        index_path = os.path.join(bundle_dir, "index.md")
        if not os.path.isdir(bundle_dir) or not os.path.isfile(index_path):
            continue
        content = open(index_path, encoding="utf-8").read()
        fm = content.split("---", 2)
        body = fm[2] if len(fm) == 3 else content

        def get(key):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm[1], re.M) if len(fm) > 1 else None
            return m.group(1).strip() if m else ""

        posts.append({
            "file": slug,
            "slug": slug,
            "title": get("title"),
            "description": get("description"),
            "keywords": get("keywords"),
            "cover": get("cover"),
            "draft": "draft: true" in (fm[1] if len(fm) > 1 else ""),
            "body": body,
        })
    return posts


def audit_post(p):
    issues = []
    tips = []
    title_len = len(p["title"])
    desc_len = len(p["description"])
    words = len(re.findall(r"\w+", p["body"]))
    h1s = len(re.findall(r"^#\s", p["body"], re.M))
    h2s = len(re.findall(r"^##\s", p["body"], re.M))
    images = re.findall(r"!\[([^\]]*)\]", p["body"])
    no_alt = sum(1 for a in images if not a.strip())
    internal = len(re.findall(
        r"\[[^\]]+\]\(/posts/|\[[^\]]+\]\(\./|\[[^\]]+\]\(\.\./\.\./posts/", p["body"]))

    # Titel
    if title_len < TITLE_MIN:
        issues.append(f"Titel zu kurz ({title_len} Zeichen, min. {TITLE_MIN})")
    elif title_len > TITLE_MAX:
        issues.append(f"Titel zu lang ({title_len} Zeichen, max. {TITLE_MAX})")
    # Description
    if desc_len < DESC_MIN:
        issues.append(f"Description zu kurz ({desc_len} Zeichen, min. {DESC_MIN})")
    elif desc_len > DESC_MAX:
        issues.append(f"Description zu lang ({desc_len} Zeichen, max. {DESC_MAX})")
    # Keywords im Titel/Description
    kws = [k.strip().lower() for k in p["keywords"].split(",") if k.strip()]
    if kws:
        tl = p["title"].lower()
        dl = p["description"].lower()
        if not any(k in tl for k in kws):
            tips.append("Kein Keyword im Titel")
        if not any(k in dl for k in kws):
            tips.append("Kein Keyword in der Description")
    # Struktur (H1 rendert PaperMod automatisch aus dem Titel)
    if h2s < 2:
        tips.append(f"Nur {h2s} H2-Abschnitte (empfohlen: 3+)")
    # Bilder
    if images and no_alt:
        issues.append(f"{no_alt} Bilder ohne Alt-Text")
    # Interne Links
    if internal < INTERNAL_LINKS_MIN:
        tips.append(f"Nur {internal} interne Links (empfohlen: {INTERNAL_LINKS_MIN}+)")
    # Wortanzahl
    if words < WORDS_MIN:
        issues.append(f"Nur {words} Wörter (min. {WORDS_MIN})")
    # Cover
    if not p["cover"]:
        tips.append("Kein Cover-Bild im Frontmatter")

    return {
        "file": p["file"],
        "title": p["title"][:50],
        "score_issues": len(issues),
        "issues": issues,
        "tips": tips,
        "words": words,
        "h2": h2s,
    }


def audit_sitemap(posts):
    """Prüft, ob alle veröffentlichten Artikel in der Sitemap stehen."""
    sitemap_path = os.path.join(PUBLIC_DIR, "sitemap.xml")
    if not os.path.exists(sitemap_path):
        return ["public/sitemap.xml fehlt – bitte hugo --minify ausführen"]
    sitemap = open(sitemap_path, encoding="utf-8").read()
    missing = []
    for p in posts:
        if p["draft"]:
            continue
        slug = p["slug"]
        if slug not in sitemap:
            missing.append(slug)
    return [f"{len(missing)} Artikel fehlen in sitemap.xml: {missing[:5]}" if missing else ""]


def main():
    as_json = "--json" in sys.argv
    posts = [p for p in load_posts() if not p["draft"]]
    results = [audit_post(p) for p in posts]

    total_issues = sum(r["score_issues"] for r in results)
    sitemap_issues = audit_sitemap(posts)

    if as_json:
        print(json.dumps({
            "audit_date": __import__("datetime").date.today().isoformat(),
            "articles": len(results),
            "total_issues": total_issues,
            "details": results,
            "sitemap_issues": sitemap_issues,
        }, ensure_ascii=False, indent=2))
        sys.exit(1 if total_issues > 0 or any(sitemap_issues) else 0)

    print(f"SEO-Audit: {len(results)} Artikel geprüft")
    print("=" * 60)
    for r in results:
        status = "✅" if r["score_issues"] == 0 else f"⚠️ ({r['score_issues']} Probleme)"
        print(f"\n{status} {r['title']}")
        for i in r["issues"]:
            print(f"   ❌ {i}")
        for t in r["tips"][:2]:
            print(f"   💡 {t}")
    print("\n" + "=" * 60)
    for s in sitemap_issues:
        if s:
            print(f"❌ {s}")
    print(f"\nErgebnis: {total_issues} Probleme in {len(results)} Artikeln")
    if total_issues > 0 or any(sitemap_issues):
        print("→ Kritische SEO-Probleme gefunden (Exit 1)")
        sys.exit(1)
    print("→ Alles auf Profi-Niveau (Exit 0)")


if __name__ == "__main__":
    main()
