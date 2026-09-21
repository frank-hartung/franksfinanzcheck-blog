#!/usr/bin/env python3
"""layout_audit.py – LAYOUT-AUTOMATISIERUNG (statischer Teil)

Prüft die gebaute Website (public/) auf Layout-Integrität:
  1) INTERNE LINKS:  alle relativen hrefs (ohne http, ohne Anker) müssen
     auf eine existierende Datei zeigen (404-Finder). Bei Hugo-Pretty-URLs
     wird "…/slug/" → "…/slug/index.html" aufgelöst.
  2) COVER-INTEGRITÄT: Frontmatter cover.image existiert + alle modernen
     Varianten (webp/avif/620/720) sind vorhanden.
  3) ALT-TEXTE:      JEDES Bild im Artikel-Inhalt des GEBAUTEN Stands hat
     einen Alt-Text (leer nur, wenn es ausdrücklich dekorativ ist). Zusätzlich
     als Warnung: veröffentlichte Beiträge mit Cover, aber ohne `cover.alt`.
  4) SCHEMA-JSON-LD: Article/WebSite/Person-Markup auf Artikel-Seiten.
  5) OG-IMAGE:       og:image + og:title auf jeder Artikel-Seite.
  6) HTML-GRUNDGERÜST: <title>, meta description, H1 vorhanden.
  7) DOM-BUDGET:     jede gebaute Seite wird browser-treu vermessen
     (scripts/dom_audit.py: Kinder je Element, Head-Kinder, Tiefe, Elemente).
     Vorher maß nur der Browser-Audit – und nur die Startseite + 3 Artikel.
  8) CHUNKER-VERTRAG: H2/H3 mit id im Artikel-Inhalt müssen direkte Blöcke
     des Inhalts sein (sonst hängt die Text-Teilung in
     sectioned_content.html Container auseinander).

Ausgabe: LAYOUT-REPORT.md (Repo) + Maschinenlesbare Zahlen in
`.cache/layout/dom-audit.json` (der Browser-Audit vergleicht dagegen ab).
Exit-Code 1 nur bei KRITISCHEN Problemen (kaputte interne Links, fehlende
Covers, gerissenes Lighthouse-DOM-Limit) – weiche Punkte sind Warnungen,
damit ein einzelner Hinweis nicht den ganzen Lauf kippt.

Aufruf:  python3 scripts/layout_audit.py            (prüft public/)
         LAYOUT_BASE_DIR=/pfad python3 scripts/layout_audit.py
         LAYOUT_DOM_JSON=/pfad.json (Default .cache/layout/dom-audit.json)
"""
import glob
import html
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dom_audit  # noqa: E402  (Browser-treue DOM-Vermessung, gleiche Wahrheit)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("LAYOUT_BASE_DIR", os.path.join(ROOT, "public"))
REPORT = os.path.join(ROOT, "LAYOUT-REPORT.md")
DOM_JSON = os.environ.get("LAYOUT_DOM_JSON",
                          os.path.join(ROOT, ".cache", "layout", "dom-audit.json"))

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
    # PHANTOM-BREMSE (11.09.2026): das quote-tolerante Muster sieht `href=`
    # überall – auch in <script> (`link.href = wf;` in der Pinterest-OAuth-
    # Landeseite) und in HTML-Kommentaren. Drei Phantom-„kaputte Links" waren
    # die Folge; eine Wache, die Phantome meldet, wird abgeschaltet. Also:
    # Skript-/Style-/Kommentar-Blöge vor dem Scannen entfernen. Echte Links
    # stehen nie in einem Skript-String, den der Browser nicht selbst setzt.
    NOISE_RE = re.compile(r"<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>",
                          re.S | re.I)
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        text = NOISE_RE.sub(" ", text)
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


def is_generic_alt(value: str, tag: str) -> bool:
    """Alt-Text, der das Bild nicht beschreibt (Dateiname/Kürzel/Slug)."""
    low = value.lower()
    if len(value) < 3:
        return True
    if re.search(r"\.(jpe?g|png|webp|avif|gif|svg)|images?/|covers?/", low):
        return True
    src = re.search(r"""\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s'\"]+))""",
                    tag, re.I)
    src_value = next((g for g in src.groups() if g is not None), "") if src else ""
    stem = os.path.splitext(os.path.basename(src_value))[0].lower()
    # Dateistamm, optional mit Größen-Suffix („hero-1200", „cover_480wb")
    low_stem = re.sub(r"[-_]\d{2,4}(wb)?$", "", low)
    if stem and (low_stem == stem or low in ("bild", "image", "img", "cover",
                                             "logo", "foto", "photo", "grafik")):
        return True
    return False


def check_alts():
    """Alt-Texte – am GEBAUTEN Stand gemessen, nicht am Frontmatter.

    WARUM UMGEBAUT (Issue #338, 21.09.2026):
    Die alte Fassung sah nur `alt:` im Frontmatter und meldete damit einen
    ENTWURF ohne Cover als „kein alt-Text" – ein Fehlalarm, der jede Woche
    erneut ins Issue lief (ein Bild ohne Bild kann keinen Alt-Text haben,
    und Entwürfe sind nicht Teil der ausgelieferten Website).
    Jetzt gilt: geprüft wird, was Leser UND Screenreader bekommen – jedes
    `<img>` im gerenderten Inhalt. Ein leeres `alt` ist nur erlaubt, wenn das
    Bild ausdrücklich dekorativ ist (`aria-hidden="true"`/`role="presentation"`
    oder im Logo-Lockup, das seinen Namen am Link trägt).
    """
    pages = [f for f in glob.glob(os.path.join(BASE, "**", "*.html"),
                                  recursive=True)
             if "/page/" not in f]
    missing = []
    images_checked = 0
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        # nur der Inhaltsblock: Header-Logo/Footer-Deko haben eigene Verträge
        m = re.search(r"<article\b.*?</article>", text, re.S | re.I)
        body = m.group(0) if m else ""
        for img in re.finditer(r"<img\b[^>]*>", body, re.I):
            images_checked += 1
            tag = img.group(0)
            alt = re.search(r"""\balt\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s'\"]+))""",
                            tag, re.I)
            value = (alt.group(1) if alt and alt.group(1) is not None else
                     (alt.group(2) if alt and alt.group(2) is not None else
                      (alt.group(3) if alt else None)))
            decorative = bool(re.search(r'aria-hidden\s*=\s*["\']?true|'
                                        r'role\s*=\s*["\']?presentation', tag, re.I))
            if value is None:
                missing.append((os.path.relpath(page, BASE),
                                "Bild ohne alt-Attribut: " + tag[:80]))
                continue
            value = value.strip()
            if not value and not decorative:
                missing.append((os.path.relpath(page, BASE),
                                "leeres alt ohne role/aria-hidden: " + tag[:80]))
            elif value and is_generic_alt(value, tag):
                # „Generisch" ist messbar: ein Dateiname, ein Kürzel oder ein
                # Slug-ähnliches Fragment beschreibt das Bild nicht – es ist
                # derselbe Fehler wie kein Alt-Text, nur schwerer zu sehen.
                missing.append((os.path.relpath(page, BASE),
                                f'generischer Alt-Text "{value[:40]}": ' + tag[:60]))
    if missing:
        WARN.append(f"Alt-Texte: {len(missing)} Bild(er) im Inhalt ohne "
                    "sinnvollen Alt-Text:")
        for page, what in missing[:10]:
            WARN.append(f"  - {page}: {what}")
    else:
        OK.append(f"Alt-Texte: {images_checked} Bilder im Artikel-Inhalt "
                  f"geprüft ({len(pages)} Seiten), 0 ohne Alt-Text.")

    # Frontmatter-Seite: nur VERÖFFENTLICHTE Beiträge mit Cover, aber ohne alt
    problems, drafts_without_cover = [], []
    for f in glob.glob(os.path.join(ROOT, "content", "posts", "*", "index.md")):
        text = open(f, encoding="utf-8").read()
        fm = text.split("---")[1] if text.startswith("---") else ""
        slug = os.path.basename(os.path.dirname(f))
        draft = bool(re.search(r"^draft:\s*true", fm, re.M))
        has_cover = bool(re.search(r'image:\s*"images/covers/[^"]+"', fm))
        alt = re.search(r'alt:\s*"([^"]*)"', fm)
        if not has_cover:
            if draft:
                drafts_without_cover.append(slug)
            else:
                problems.append((slug, "kein Cover (og:image/Share-Bild fehlt)"))
        elif not alt or not alt.group(1).strip():
            problems.append((slug, "Cover ohne cover.alt"))
    if problems:
        WARN.append(f"Cover-Alt-Texte (Frontmatter): {len(problems)} Beitrag/"
                    "Beiträge ohne Alt-Text:")
        for slug, what in problems[:10]:
            WARN.append(f"  - {slug}: {what}")
    elif drafts_without_cover:
        OK.append(f"Cover-Alt-Texte: alle veröffentlichten Beiträge mit "
                  f"`cover.alt`; {len(drafts_without_cover)} Entwurf/Entwürfe "
                  "noch ohne Cover (Cover entsteht beim Publizieren).")


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


def check_dom_budget():
    """DOM-/Layout-Budget für JEDE gebaute Seite (Issue #338).

    Der Browser-Audit maß Kinder/Tiefe/Elemente nur auf vier Seiten. Die
    Tag-Übersicht mit 136 Kindern einer einzigen Liste und zwei Artikel auf
    der 60-Kinder-Grenze waren deshalb unsichtbar. Hier wird der ganze Baum
    vermessen – browser-treu und ohne Chrome (siehe dom_audit.py), damit die
    Zahlen auch in einem Lauf ohne Browser-Download existieren. Die Rohdaten
    gehen als JSON an den Browser-Audit, der seine echten Browser-Messwerte
    damit vergleicht (Parser-Drift wird so sichtbar).
    """
    result = dom_audit.audit_dir(BASE)
    target = os.path.abspath(DOM_JSON)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    b, l = dom_audit.BUDGET, dom_audit.LIMIT
    rows = result["rows"]
    head = (f"DOM-Budget: {result['pages']} Seiten browser-treu vermessen "
            f"(ohne Chrome). Grenzen – Lighthouse: {l['children']} Kinder je "
            f"Element, {l['head_children']} im <head>, {l['depth']} Tiefe, "
            f"{l['elements']} Elemente; Frühwarnung: {b['children']} / "
            f"{b['head_children']} / {b['depth']} / {b['elements']}.")

    crit_pages = result["critical"]
    summary = []
    if rows:
        kids = max(rows, key=lambda r: r["maxchildren"])
        headrow = max(rows, key=lambda r: r["headchildren"])
        depth = max(rows, key=lambda r: r["depth"])
        elems = max(rows, key=lambda r: r["elements"])
        summary = [
            f"Kinder/Element: max. {kids['maxchildren']} "
            f"({kids['maxchildren_path']}) auf {kids['rel']}",
            f"Head-DOM: max. {headrow['headchildren']} Kinder "
            f"({headrow['rel']})",
            f"Tiefe: max. {depth['depth']}",
            f"Elemente: max. {elems['elements']} ({elems['rel']})",
        ]
    if crit_pages:
        CRITICAL.append(head)
        CRITICAL.append(f"{len(crit_pages)} Seite(n) über der Lighthouse-Grenze:")
        for row in crit_pages[:8]:
            for item in row["critical"]:
                CRITICAL.append(f"  - {row['rel']}: {item}")
        CRITICAL.extend(f"  · {line}" for line in summary)
    else:
        OK.append(head)
        OK.extend(f"{line} – im Budget." for line in summary)
    if result["warnings"]:
        WARN.append(f"DOM-Frühwarnung auf {len(result['warnings'])} Seite(n) "
                    "(Hinweis, kein Issue):")
        for row in result["warnings"][:8]:
            for item in row["warnings"]:
                WARN.append(f"  - {row['rel']}: {item}")
    return result


def check_chunker_contract():
    """Vertrag der Text-Teilung (sectioned_content.html) im gebauten HTML.

    Die Teilung ist eine Text-Operation auf dem gerenderten Markdown: sie
    schiebt vor jede von Goldmark erzeugte H2/H3 mit `id` eine Gruppengrenze
    ein. Wäre eine solche Überschrift in einem Container (Shortcode-Box,
    Listenpunkt, Tabellenzelle), würde die Grenze den Container aufreißen –
    Layout kaputt, ohne dass eine Zählung das merkt. Deshalb prüft der Audit
    die Struktur nach: H2/H3 mit id im Artikel-Inhalt müssen direkt im
    Inhaltsblock oder in einer Gruppe liegen.
    """
    violations = []
    pages = [f for f in glob.glob(os.path.join(BASE, "**", "*.html"),
                                  recursive=True)
             if "/page/" not in f]
    checked = 0
    for page in pages:
        text = open(page, encoding="utf-8", errors="ignore").read()
        if "ff-content-chunk" not in text:
            continue
        root, _nodes = dom_audit.parse_document(text)
        if root is None:
            continue
        stack = [(root, ())]
        while stack:
            node, chain = stack.pop()
            parent = chain[-1] if chain else None
            if node.tag in ("h2", "h3"):
                in_content = any(
                    "md-content" in a.cls or "post-content" in a.cls
                    for a in chain)
                has_id = bool(node.id)
                if in_content and has_id:
                    checked += 1
                    container_ok = parent is not None and (
                        "ff-content-chunk" in parent.cls
                        or "post-content" in parent.cls
                        or "md-content" in parent.cls)
                    if not container_ok:
                        violations.append((os.path.relpath(page, BASE),
                                           dom_audit.path_of(node)))
            stack.extend((child, chain + (node,)) for child in node.children)
    if violations:
        CRITICAL.append(f"Chunker-Vertrag: {len(violations)} Überschrift(en) "
                        "mit id in einem Container (Text-Teilung würde den "
                        "Container aufreißen):")
        for page, path in violations[:10]:
            CRITICAL.append(f"  - {page}: {path}")
    else:
        OK.append(f"Chunker-Vertrag: {checked} Überschriften im Artikel-"
                  "Inhalt geprüft, alle auf Blockebene (Text-Teilung greift nur "
                  "dort).")


def write_report():
    lines = ["# 📐 LAYOUT-REPORT (Layout-Automatisierung)", ""]
    lines.append("**Stand:** " + __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M UTC"))
    lines.append("")
    # Zählung ohne Fortsetzungszeilen („  - …"): die Zahl im Kopf soll die
    # Zahl der BEFUNDE sein, nicht die Zahl der Zeilen.
    def findings(items):
        return sum(1 for i in items if not i.startswith("  -"))

    if CRITICAL:
        lines.append(f"## ❌ Kritisch ({findings(CRITICAL)})")
    if WARN:
        lines.append(f"## ⚠️ Warnungen ({findings(WARN)})")
    if OK:
        lines.append(f"## ✅ OK ({findings(OK)})")
    lines.append("")
    for section, items in (("## ❌ Kritisch", CRITICAL),
                           ("## ⚠️ Warnungen", WARN),
                           ("## ✅ OK", OK)):
        if not items:
            continue
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
    check_dom_budget()
    check_chunker_contract()
    write_report()
    return 1 if CRITICAL else 0


if __name__ == "__main__":
    sys.exit(main())
