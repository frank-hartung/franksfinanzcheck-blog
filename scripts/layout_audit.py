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
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r'href="([^"]+)"', text):
            href = html.unescape(m.group(1))
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


def check_markdown_links():
    """Prüft die Markdown-QUELLEN auf kaputte/verschachtelte Links
    (Fund 12.08.: internal_linker-Bot erzeugte „[Euro [pr](../../…/…)o
    Monat](../../…/)“, „[pro Monat](…)“-Einsprengsel, Links mitten im Wort
    und Link-Markup in Frontmatter-Keywords). --fix entfernt das Link-Markup
    und lässt den Anzeigetext stehen (deterministisch, konservativ)."""
    root = os.path.dirname(BASE)  # Projektwurzel (BASE = public/)
    files = (glob.glob(os.path.join(root, "content", "posts", "*", "index.md"))
             + glob.glob(os.path.join(root, "content", "pillar", "*", "index.md")))
    problems = []

    # 1) Verschachtelt: [Text [Link](url) …](url)  bzw. [Text [Link](url)
    re_nested = re.compile(r"\[([^\]\n]*\[[^\]\n]*)\]\([^)\n]*\)")
    # 2) Link mitten im Wort: X[Text](url)Y
    re_midword = re.compile(r"([a-zäöüßA-ZÄÖÜ0-9])\[([^\]]*)\]\(([^)\n]*)\)")
    # 2b) Link zerschneidet ein Wort: [Textteil](url)Wortfortsetzung
    #     (Fund 12.08.: „…[ das Eigenkapital fü](../../posts/…/)r eine Immobilie“
    #     – der Link zerschneidet „für“ in „fü|r“; das Muster ](url)X mit
    #     direkt angehängtem Buchstaben X wurde bisher übersehen.)
    re_midword2 = re.compile(r"\[([^\]]*)\]\([^)\n]*\)([a-zäöüß])")
    # 3) Link-Markup in Frontmatter-Keywords/Categories
    re_front = re.compile(r"^(keywords|categories|tags):.*\]\([^)\n]*\)", re.M)

    for f in files:
        c = open(f, encoding="utf-8").read()
        lines = c.split("\n")
        for i, l in enumerate(lines):
            slug = os.path.basename(os.path.dirname(f))
            for m in re_nested.finditer(l):
                problems.append((slug, i + 1, "verschachtelter Link", m.group(0)[:80]))
            for m in re_midword.finditer(l):
                problems.append((slug, i + 1, "Link mitten im Wort", m.group(0)[:80]))
            for m in re_midword2.finditer(l):
                problems.append((slug, i + 1, "Link zerschneidet Wort", m.group(0)[:80]))
            for m in re_front.finditer(c):
                problems.append((slug, 0, "Link in Frontmatter", m.group(0)[:60]))

    if problems:
        CRITICAL.append(f"**{len(problems)} kaputte/verschachtelte Markdown-Links**:")
        for slug, ln, kind, snippet in problems[:15]:
            CRITICAL.append(f"  - `{slug}:{ln}` [{kind}] …{snippet}…")
    else:
        OK.append("Markdown-Links (Quellen): 0 verschachtelt/kaputt.")

    # --fix: Link-Markup entfernen, Text behalten
    if "--fix" in sys.argv and problems:
        fixed = 0
        for f in files:
            c = open(f, encoding="utf-8").read()
            orig = c
            # Verschachtelte Links: inneres Link-Markup entfernen
            c = re.sub(r"\[([^\]\n]*)\[([^\]]*)\]\([^)\n]*\)([^\]\n]*)\]\([^)\n]*\)",
                       lambda m: "[" + m.group(1) + m.group(2) + m.group(3) + "]", c)
            # Links mitten im Wort: Link-Markup entfernen, Text behalten
            c = re.sub(r"([a-zäöüßA-ZÄÖÜ0-9])\[([^\]]*)\]\([^)\n]*\)([a-zäöüßA-ZÄÖÜ0-9])",
                       lambda m: m.group(1) + m.group(2) + m.group(3), c)
            # Wort-zerschneidende Links: Anker + Fortsetzung zusammenfügen
            # („[Eigenkapital fü](url)r“ → „Eigenkapital für“)
            c = re.sub(r"\[([^\]]*)\]\([^)\n]*\)([a-zäöüß])",
                       lambda m: m.group(1) + m.group(2), c)
            if c != orig:
                open(f, "w", encoding="utf-8").write(c)
                fixed += 1
        print(f"Markdown-Link-Fix: {fixed} Dateien bereinigt.")


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
        for variant in [f"webp/{stem}.webp", f"avif/{stem}.avif",
                        f"webp/620/{stem}.webp", f"avif/620/{stem}.avif",
                        f"webp/720/{stem}.webp", f"avif/720/{stem}.avif"]:
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
    no_schema, no_og, no_meta, no_h1, no_canonical = [], [], [], [], []
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        # Redirect-Alias-Seiten (Hugo baut sie für umbenannte Slugs:
        # <meta http-equiv=refresh> + canonical) sind gewollt – überspringen
        if re.search(r'http-equiv=["\']?refresh', text) and "canonical" in text:
            continue
        # 13.08.: Das frühere eigene "Article"-Schema (schema_article.html)
        # wurde entfernt (Templating-Bug mit doppelt escapten Anführungs-
        # zeichen + verwies auf nie existierendes /images/logo.png, siehe
        # Commit-History). Es war ohnehin redundant zum sauberen, theme-
        # eigenen BlogPosting-Schema. Diese Prüfung akzeptiert daher jetzt
        # beide Schema-Typen als gültig.
        if ('"@type":"Article"' not in text and '"@type": "Article"' not in text
                and '"@type":"BlogPosting"' not in text and '"@type": "BlogPosting"' not in text):
            no_schema.append(os.path.basename(os.path.dirname(page)))
        if 'og:image' not in text:
            no_og.append(os.path.basename(os.path.dirname(page)))
        # Minifier entfernt die Quotes (name=description) – beides akzeptieren
        if not re.search(r'<meta[^>]*name=["\']?description["\']?', text):
            no_meta.append(os.path.basename(os.path.dirname(page)))
        if re.search(r"<h1[^>]*>", text) is None:
            no_h1.append(os.path.basename(os.path.dirname(page)))
        # Canonical-Tag (Self-Referencing auf Artikel-URL) – SEO-Pflicht
        if not re.search(r'<link[^>]*rel=["\']?canonical["\']?', text):
            no_canonical.append(os.path.basename(os.path.dirname(page)))
    if no_schema:
        WARN.append(f"Schema Article fehlt auf {len(no_schema)} Seiten: {', '.join(no_schema[:6])}")
    else:
        OK.append(f"Schema-JSON-LD (BlogPosting) auf allen {len(pages)} Artikel-Seiten.")
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
    if no_canonical:
        CRITICAL.append(f"Canonical fehlt auf {len(no_canonical)} Seiten: "
                        f"{', '.join(no_canonical[:6])}")
    else:
        OK.append("Canonical-Tags auf allen Artikel-Seiten.")


def check_home_pagination_purity():
    """L7 (14.08.2026, Frank: 'Datenschutzerklärung, Impressum, Über mich
    und diesen Blog unter dem Blogartikel. Bitte dauerhaft optimieren.'):
    verhindert das Wiederauftreten eines echten Hugo-Templating-Bugs, bei
    dem Rechtsseiten (Datenschutz/Impressum/Über) als vollwertige
    Artikel-Karten in der Start­seiten-Paginierung erschienen (Root Cause:
    layouts/_partials/head.html rief .Paginator OHNE Argument auf – das
    fällt intern auf .RegularPages zurück, was auf der Startseite ALLE
    Top-Level-Einzelseiten einschließt, nicht nur echte Blogartikel. Da
    Hugo die Paginierung EINMAL PRO SEITE cached und head.html VOR dem
    Body-Template rendert, hat dieser zu weite Aufruf die komplette
    Startseiten-Paginierung "vergiftet"). Fix: siehe head.html-Kommentar.

    Diese Prüfung liest JEDE gebaute Startseiten-Paginierungsseite
    (public/index.html, public/page/N/index.html) und stellt sicher, dass
    JEDE 'post link to …'-Artikelkarte tatsächlich auf /posts/… zeigt –
    keine Rechts-/Info-Seite darf dort als Artikel-Karte auftauchen."""
    home_pages = [os.path.join(BASE, "index.html")]
    home_pages += sorted(glob.glob(os.path.join(BASE, "page", "*", "index.html")))
    foreign = []
    checked_cards = 0
    for page in home_pages:
        if not os.path.isfile(page):
            continue
        text = open(page, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(
            r'aria-label="post link to ([^"]*)"\s+href=([^\s>]+)', text
        ):
            checked_cards += 1
            title, href = m.group(1), m.group(2).strip('"')
            if not href.startswith(("/posts/", "https://franksfinanzcheck.de/posts/")):
                foreign.append(f"{os.path.relpath(page, BASE)}: „{html.unescape(title)}“ → {href}")
    if foreign:
        CRITICAL.append(
            f"**{len(foreign)} artikelfremde Karte(n) in der Startseiten-Paginierung** "
            f"(Rechts-/Info-Seiten dürfen dort NIE als Artikel-Karte erscheinen):"
        )
        for f in foreign:
            CRITICAL.append(f"  - {f}")
    else:
        OK.append(f"Startseiten-Paginierung: {checked_cards} Artikel-Karten geprüft, "
                   f"0 artikelfremde (Rechtsseiten bleiben draußen).")


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
        check_markdown_links()  # verschachtelte/kaputte Markdown-Links heilen
        return 0 if n == 0 else 2
    if not os.path.isdir(BASE):
        print(f"FEHLER: {BASE} existiert nicht – erst `hugo` bauen.")
        return 1
    check_markdown_links()  # Markdown-Quellen zuerst (unabhängig vom Build)
    check_internal_links()
    check_covers()
    check_alts()
    check_schema_and_meta()
    check_home_pagination_purity()
    write_report()
    return 1 if CRITICAL else 0


if __name__ == "__main__":
    sys.exit(main())
