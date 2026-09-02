#!/usr/bin/env python3
"""layout_audit.py – LAYOUT-AUTOMATISIERUNG (statischer Teil)

Prüft die gebaute Website (public/) auf Layout-Integrität:
  1) INTERNE LINKS:  alle relativen hrefs (ohne http, ohne Anker) müssen
     auf eine existierende Datei zeigen (404-Finder). Bei Hugo-Pretty-URLs
     wird "…/slug/" → "…/slug/index.html" aufgelöst.
  2) COVER-INTEGRITÄT: Frontmatter cover.image existiert + alle modernen
     Varianten (webp/avif/620/720) sind vorhanden.
  3) ALT-TEXTE:      cover.alt gesetzt (nicht leer, nicht generisch).
  4) SCHEMA-JSON-LD: Article/WebSite/Person-Markup auf Artikel-Seiten.
  5) OG-IMAGE:       og:image + og:title auf jeder Artikel-Seite.
  6) HTML-GRUNDGERÜST: <title>, meta description, H1 vorhanden.

Ausgabe: LAYOUT-REPORT.md (Repo), Exit-Code 1 nur bei KRITISCHEN Problemen
(kaputte interne Links oder fehlende Covers) – weiche Punkte (Alt-Texte,
Schema-Hinweise) sind Warnungen, damit der Workflow nicht kippt.

Aufruf:  python3 scripts/layout_audit.py            (prüft public/)
         LAYOUT_BASE_DIR=/pfad python3 scripts/layout_audit.py
"""
import glob
import html
import json
import os
import re
import sys
import urllib.parse

BASE = os.environ.get("LAYOUT_BASE_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public"))
REPORT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "LAYOUT-REPORT.md")

CRITICAL, WARN, OK = [], [], []


def resolve(base_dir, page_file, href):
    """Löst eine href gegen die public/-Struktur auf.
    Relative Links sind seitenrelativ; absolute (/...) gehen gegen BASE."""
    if not href or href.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:", "javascript:")):
        return None
    href = href.split("#")[0].split("?")[0]
    href = urllib.parse.unquote(href)
    if href.startswith("/"):
        path = os.path.normpath(os.path.join(base_dir, href.lstrip("/")))
    else:
        page_dir = os.path.dirname(page_file)
        path = os.path.normpath(os.path.join(page_dir, href))
    if os.path.isdir(path):
        cand = os.path.join(path, "index.html")
        return cand if os.path.exists(cand) else None
    if os.path.exists(path):
        return path
    # Hugo Pretty-URLs: ohne trailing slash → mit index.html probieren
    if os.path.exists(path + "/index.html"):
        return path + "/index.html"
    return None


def check_internal_links():
    pages = glob.glob(os.path.join(BASE, "**", "*.html"), recursive=True)
    checked = 0
    broken = []
    # QUOTE-TOLERANT (02.09.2026): `hugo --minify` gibt einfache Attributwerte
    # OHNE Quotes aus (`href=/go/gas/`). Das alte Muster `href="([^"]+)"` sah
    # dadurch in einem minifizierten Build nur 108 statt 1101 Links – ein
    # FALSE-GREEN: genau die unquotierten Links (u. a. alle /go/-Affiliate-
    # Links) wären ungeprüft geblieben. Gleiche Fehlerklasse wie der
    # Render-Beweis der Affiliate-Integritäts-Wache, deshalb hier dieselbe
    # Härtung: Attribut-Wert mit oder ohne Quotes erkennen.
    href_pat = re.compile(r"""href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", re.I)
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        for m in href_pat.finditer(text):
            raw = m.group(1) if m.group(1) is not None else (
                m.group(2) if m.group(2) is not None else (m.group(3) or ""))
            href = html.unescape(raw)
            if href.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:", "javascript:")):
                continue
            checked += 1
            if resolve(BASE, page, href) is None:
                # Zukunfts-Link? (posts/-Link auf noch nicht existierenden Slug
                # mit Fuzzy-Match-Potenzial = geplant) → Warnung statt kritisch
                m = re.search(r"/posts/([a-z0-9\-]+?)/?$", href)
                if m and href.startswith(("../", "/")):
                    import difflib
                    real = _post_slugs()
                    if not difflib.get_close_matches(m.group(1), real, n=1, cutoff=0.6):
                        WARN.append(f"Zukunfts-Link (geplant): {os.path.relpath(page, BASE)} → {href}")
                        continue
                broken.append((os.path.relpath(page, BASE), href))
    if broken:
        CRITICAL.append(f"**{len(broken)} kaputte interne Links** (von {checked} geprüft):")
        for page, href in broken[:15]:
            CRITICAL.append(f"  - `{page}` → `{href}`")
    else:
        OK.append(f"Interne Links: {checked} geprüft, 0 kaputt.")


def check_covers():
    posts = glob.glob(os.path.join(os.path.dirname(BASE), "content", "posts", "*", "index.md"))
    missing = []
    for f in posts:
        text = open(f, encoding="utf-8").read()
        m = re.search(r'image:\s*"(images/covers/[^"]+)"', text)
        if not m:
            continue
        rel = m.group(1)
        full = os.path.join(os.path.dirname(BASE), "static", rel)
        if not os.path.exists(full):
            missing.append((os.path.basename(os.path.dirname(f)), rel + " (Original fehlt)"))
            continue
        base = rel.rsplit(".", 1)[0]
        stem = os.path.basename(base)
        variants = [f"webp/{stem}.webp", f"avif/{stem}.avif"]
        for w in ("360", "480", "620", "720"):
            variants.extend([f"webp/{w}/{stem}.webp", f"avif/{w}/{stem}.avif"])
        for variant in variants:
            if not os.path.exists(os.path.join(os.path.dirname(BASE), "static", "images", "covers", variant)):
                missing.append((os.path.basename(os.path.dirname(f)), f"images/covers/{variant} fehlt"))
    if missing:
        CRITICAL.append(f"**{len(missing)} Cover-Probleme:**")
        for slug, what in missing[:15]:
            CRITICAL.append(f"  - {slug}: {what}")
    else:
        OK.append("Covers: alle Originale + WebP/AVIF-Varianten vorhanden.")


def check_alts():
    posts = glob.glob(os.path.join(os.path.dirname(BASE), "content", "posts", "*", "index.md"))
    generic = []
    for f in posts:
        text = open(f, encoding="utf-8").read()
        m = re.search(r'alt:\s*"([^"]*)"', text)
        if not m or not m.group(1).strip():
            generic.append((os.path.basename(os.path.dirname(f)), "kein alt-Text"))
        elif m.group(1).lower().startswith(("spar-tipp", "cover", "bild")):
            generic.append((os.path.basename(os.path.dirname(f)), f"generisch: {m.group(1)[:40]}"))
    if generic:
        WARN.append(f"Alt-Texte: {len(generic)} generisch/fehlend (SEO-Hinweis):")
        for slug, what in generic[:10]:
            WARN.append(f"  - {slug}: {what}")
    else:
        OK.append("Alt-Texte: alle gesetzt und aussagekräftig.")


def check_schema_and_meta():
    pages = glob.glob(os.path.join(BASE, "posts", "*", "index.html"))
    no_schema, no_og, no_meta, no_h1 = [], [], [], []
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        if '"@type":"Article"' not in text and '"@type": "Article"' not in text:
            no_schema.append(os.path.basename(os.path.dirname(page)))
        if 'og:image' not in text:
            no_og.append(os.path.basename(os.path.dirname(page)))
        # QUOTE-TOLERANT (02.09.2026): minifiziert steht dort
        # `<meta name=description content="…">` – der Literal-Vergleich meldete
        # dann fälschlich "Meta-Description fehlt auf N Seiten" (FALSE-CRITICAL).
        if not re.search(r'<meta[^>]+name\s*=\s*["\']?description["\']?', text, re.I):
            no_meta.append(os.path.basename(os.path.dirname(page)))
        if re.search(r"<h1[^>]*>", text) is None:
            no_h1.append(os.path.basename(os.path.dirname(page)))
    if no_schema:
        WARN.append(f"Schema Article fehlt auf {len(no_schema)} Seiten: {', '.join(no_schema[:6])}")
    else:
        OK.append(f"Schema-JSON-LD (Article) auf allen {len(pages)} Artikel-Seiten.")
    if no_og:
        WARN.append(f"og:image fehlt auf {len(no_og)} Seiten.")
    else:
        OK.append("og:image auf allen Artikel-Seiten.")
    if no_meta:
        CRITICAL.append(f"Meta-Description fehlt auf {len(no_meta)} Seiten.")
    else:
        OK.append("Meta-Description überall vorhanden.")
    if no_h1:
        WARN.append(f"H1 fehlt auf {len(no_h1)} Seiten.")
    else:
        OK.append("H1 überall vorhanden.")


def write_report():
    lines = ["# 📐 LAYOUT-REPORT (Layout-Automatisierung)", ""]
    lines.append("**Stand:** " + __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M UTC"))
    lines.append("")
    if CRITICAL:
        lines.append(f"## ❌ Kritisch ({len(CRITICAL)})")
    if WARN:
        lines.append(f"## ⚠️ Warnungen ({len(WARN)})")
    if OK:
        lines.append(f"## ✅ OK ({len(OK)})")
    lines.append("")
    for section, items in (("## ❌ Kritisch", CRITICAL), ("## ⚠️ Warnungen", WARN), ("## ✅ OK", OK)):
        lines.append(section)
        lines.extend(items)
        lines.append("")
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("\n".join(lines))




def _post_slugs():
    """Echte Post-Ordnernamen (Slugs MIT Datumspräfix, wie sie existieren)."""
    return set(os.path.basename(os.path.dirname(f))
               for f in glob.glob(os.path.join(os.path.dirname(BASE), "content", "posts", "*", "index.md")))


def _match_slugs():
    """Slugs für den Fuzzy-Match: echte Namen + Varianten ohne Datumspräfix."""
    slugs = _post_slugs()
    extra = set()
    for s in slugs:
        m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)", s)
        if m:
            extra.add(m.group(1))
    return slugs | extra


def auto_fix_links():
    """--fix: Korrigiert kaputte interne /posts/-Links per Fuzzy-Match.
    Läuft gegen die CONTENT-Dateien (nicht public/)."""
    import difflib
    content_dir = os.path.dirname(BASE)  # Projektwurzel
    real_slugs = _post_slugs()      # nur echte Ordnernamen
    fixed_total = 0
    files = (glob.glob(os.path.join(content_dir, "content", "posts", "*", "index.md"))
             + glob.glob(os.path.join(content_dir, "content", "pillar", "*", "index.md")))
    for f in files:
        text = open(f, encoding="utf-8").read()
        changed = 0
        for m in re.finditer(r"((?:\.\./)+posts/)([a-z0-9\-]+?)(/|\])", text):
            target = m.group(2)
            if target in real_slugs:
                continue  # Ziel existiert wirklich – nichts zu tun
            # Fuzzy: finde ähnlichsten ECHTEN Ordnernamen (mit Datumspräfix).
            # get_close_matches gegen die echten Namen → nie die identische
            # (nicht existierende) Variante ohne Datum wählen.
            best = difflib.get_close_matches(target, real_slugs, n=1, cutoff=0.6)
            if best:
                new = m.group(1) + best[0] + m.group(3)
                text = text[:m.start()] + new + text[m.end():]
                fixed_total += 1
                changed += 1
                print(f"  ✓ {os.path.basename(os.path.dirname(f))}: {target} → {best[0]}")
            else:
                # Kein Match = geplanter/künftiger Artikel – als Warnung merken
                WARN.append(f"Link ohne Ziel (geplant?): {os.path.basename(os.path.dirname(f))} → {target}")
        if changed:
            open(f, "w", encoding="utf-8").write(text)
    if fixed_total:
        print(f"Auto-Fix: {fixed_total} Links korrigiert.")
    else:
        print("Auto-Fix: keine korrigierbaren Links.")
    return fixed_total


def main():
    if "--fix" in sys.argv:
        n = auto_fix_links()
        return 0 if n == 0 else 2
    if not os.path.isdir(BASE):
        print(f"FEHLER: {BASE} existiert nicht – erst `hugo` bauen.")
        return 1
    check_internal_links()
    check_covers()
    check_alts()
    check_schema_and_meta()
    write_report()
    return 1 if CRITICAL else 0


if __name__ == "__main__":
    sys.exit(main())
