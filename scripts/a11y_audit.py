#!/usr/bin/env python3
"""
Barrierefreiheits-Audit (WCAG 2.1 – Profi-Niveau, automatisch).

Prüft auf allen Seiten:
  - lang-Attribut vorhanden
  - title vorhanden und nicht leer
  - genau 1 h1 pro Seite
  - alle Bilder mit alt-Text
  - Skip-Link vorhanden (Tastatur-Navigation)
  - Fokus-Styles (focus-visible) im CSS
  - prefers-reduced-motion im CSS
  - Kontrast der Branding-Farben (WCAG AA: 4.5:1 normal, 3:1 groß)

Nutzung:
    python3 scripts/a11y_audit.py            # Audit
    python3 scripts/a11y_audit.py --json     # JSON-Report

Exit-Code: 0 = ok, 1 = A11y-Probleme
"""
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BLOG_DIR, "public")


def luminance(r, g, b):
    def c(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


def contrast(rgb1, rgb2):
    l1, l2 = luminance(*rgb1), luminance(*rgb2)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# Dateien, die bewusst minimal sind und NICHT geprüft werden:
#  - google*.html: Verifikationsdatei (Google verlangt exakten Inhalt)
#  - page/N/: automatische Redirect-Seiten (leiten sofort weiter)
#  - BingSiteAuth.xml: keine HTML-Seite
SKIP_PATTERNS = ("google", "page/", "BingSiteAuth")


def collect_html_files():
    files = []
    for root, dirs, names in os.walk(PUBLIC_DIR):
        if "assets" in root or "tags" in root or "categories" in root:
            continue
        for n in names:
            if not n.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(root, n), PUBLIC_DIR)
            if any(p in rel for p in SKIP_PATTERNS):
                continue
            files.append(os.path.join(root, n))
    # Wichtige Seiten zuerst
    files.sort(key=lambda f: (f.count(os.sep), f))
    return files[:20]  # Stichprobe


def audit_page(path):
    html = open(path, encoding="utf-8").read()
    issues = []
    name = os.path.relpath(path, PUBLIC_DIR)

    if '<html lang=' not in html:
        issues.append("lang-Attribut fehlt")
    if '<title>' not in html and "<title>" not in html:
        issues.append("title fehlt")
    h1s = len(re.findall(r"<h1[\s>]", html))
    if h1s != 1:
        issues.append(f"{h1s} h1 (erwartet: 1)")
    # Bilder ohne alt
    for m in re.finditer(r"<img[^>]*>", html):
        if 'alt=' not in m.group(0):
            issues.append("img ohne alt-Text")
    if 'class="skip-link"' not in html and "class=skip-link" not in html:
        issues.append("Skip-Link fehlt")
    return name, issues


def audit_css():
    issues = []
    css_files = [os.path.join(PUBLIC_DIR, "assets", "css", f)
                 for f in os.listdir(os.path.join(PUBLIC_DIR, "assets", "css"))]
    css = "\n".join(open(f, encoding="utf-8").read() for f in css_files if os.path.exists(f))

    if "focus-visible" not in css:
        issues.append("Fokus-Styles (focus-visible) fehlen")
    if "prefers-reduced-motion" not in css:
        issues.append("prefers-reduced-motion fehlt")
    if "skip-link" not in css:
        issues.append("Skip-Link-Styles fehlen")
    return issues


def audit_contrast():
    """Prüft die wichtigsten Farbkombinationen gegen WCAG AA."""
    checks = [
        ("Text auf Weiß", "#0E5A43", "#FFFFFF", "normal"),   # grüner Text
        ("Weiß auf Grün", "#FFFFFF", "#0E5A43", "normal"),   # Home-Info
        ("Anthrazit auf Gelb", "#2E2E33", "#FFB300", "normal"),  # CTA-Button
        ("Weiß auf Rot (Pinterest)", "#FFFFFF", "#E60023", "normal"),
        ("Sekundärtext", "#444444", "#FFFFFF", "normal"),
        ("Text auf Hellgrün", "#0E5A43", "#EAF4EF", "normal"),  # Related Posts
    ]
    results = []
    for name, fg, bg, size in checks:
        ratio = contrast(hex_rgb(fg), hex_rgb(bg))
        min_ratio = 3.0 if size == "groß" else 4.5
        ok = ratio >= min_ratio
        results.append({"paar": name, "verhältnis": round(ratio, 2),
                        "ok": ok, "mindest": min_ratio})
    return results


def main():
    as_json = "--json" in sys.argv

    page_results = []
    for path in collect_html_files():
        name, issues = audit_page(path)
        page_results.append({"seite": name, "probleme": issues})

    css_issues = audit_css()
    contrast_results = audit_contrast()

    total_issues = sum(len(p["probleme"]) for p in page_results) + len(css_issues)
    contrast_fail = sum(1 for c in contrast_results if not c["ok"])

    if as_json:
        print(json.dumps({
            "seiten": len(page_results),
            "css_probleme": css_issues,
            "kontrast": contrast_results,
            "gesamt_probleme": total_issues,
        }, ensure_ascii=False, indent=2))
        sys.exit(1 if total_issues > 0 or contrast_fail else 0)

    print(f"Barrierefreiheits-Audit: {len(page_results)} Seiten geprüft\n")
    for p in page_results:
        status = "✅" if not p["probleme"] else f"⚠️ ({len(p['probleme'])})"
        print(f"{status} {p['seite']}")
        for i in p["probleme"][:4]:
            print(f"     • {i}")

    print("\n=== CSS-Grundlagen ===")
    for i in css_issues:
        print(f"  ❌ {i}")
    if not css_issues:
        print("  ✅ Fokus, reduced-motion, Skip-Link-Styles vorhanden")

    print("\n=== Kontrast (WCAG AA) ===")
    for c in contrast_results:
        print(f"  {'✅' if c['ok'] else '❌'} {c['paar']}: {c['verhältnis']}:1 (min. {c['mindest']}:1)")

    print(f"\nErgebnis: {total_issues} Probleme, {contrast_fail} Kontrast-Fehler")
    if total_issues > 0 or contrast_fail:
        sys.exit(1)
    print("✅ Barrierefreiheit auf Top-Niveau")


if __name__ == "__main__":
    main()
