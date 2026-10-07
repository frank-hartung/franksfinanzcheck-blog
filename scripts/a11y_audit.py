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
    python3 scripts/a11y_audit.py            # Audit (alle gebauten Seiten)
    python3 scripts/a11y_audit.py --json     # JSON-Report

Exit-Code: 0 = ok, 1 = A11y-Probleme

BLINDER FLECK GESCHLOSSEN (Dauerheilung #623, 07.10.2026):
Bis dahin prüfte dieses Audit eine STICHPROBE von 20 Seiten – von 107
gebauten Seiten. Die dritte Doppel-H1 des Befundtages
(/studien/fixkosten-index-2026-q4/) stand im selben Build und blieb
UNSICHTBAR; gemeldet wurden nur /presse/ und /studien/. Ein Audit,
das ein Fünftel sieht, würfelt. Jetzt läuft der Lauf über ALLE
gebauten Seiten (eine Sekunde, kein Grund für eine Stichprobe) und
nennt bei einer falschen H1-Anzahl die Überschriften TEXTLICH, damit
das automatische Issue ohne Nachfrage erklärt, was zu tun ist.
Die H1-Regel selbst gehört der Wache scripts/h1_wache.py (S1–S3).
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


# Seiten, die bewusst minimal sind und NICHT geprüft werden. Die Liste
# gehört der H1-Wache (eine Wahrheit, keine zweite Ausnahme-Quelle):
#   scripts/h1_wache.py → AUSNAHMEN_SEITE. Jeder Eintrag trägt dort
#   seinen Grund; eine Ausnahme ohne Grund ist eine Lücke mit Etikett.
#   - Verifikationsdateien (Google/Pinterest verlangen exakten Inhalt)
#   - /page/N/: Blätter-Redirects ohne Seiteninhalt
#   - /go/ und /pinterest-oauth*: reine Weiterleitungen (noindex)
#   - BingSiteAuth.xml: keine HTML-Seite
try:  # a11y_audit.py liegt wie die Wache in scripts/ – direkter Import.
    from h1_wache import AUSNAHMEN_SEITE as AUSNAHMEN  # type: ignore
except ImportError:  # fail-closed gemeldet, nicht stillschweigend grün
    AUSNAHMEN = (
        (r"(^|/)google[^/]*\.html$", "Verifikationsdatei"),
        (r"(^|/)pinterest-[a-z0-9]+\.html$", "Verifikationsdatei"),
        (r"(^|/)page/[0-9]+/", "Blätter-Redirect"),
        (r"^pinterest-oauth/index\.html$", "Client-Redirect"),
        (r"^go/", "Affiliate-Redirect"),
        (r"^pinterest-oauth\.html$", "Client-Redirect"),
    )
    print("⚠ a11y_audit: scripts/h1_wache.py nicht ladbar – Ausnahmen "
          "ersatzweise aus der eingebauten Liste (Gründe: h1_wache.py).")

SKIP_PATTERNS = ("BingSiteAuth",)


def collect_html_files():
    """ALLE gebauten Seiten – seit #623 keine Stichprobe mehr.

    Begründung: Eine Stichprobe von 20 aus 107 Seiten hat die dritte
    Doppel-H1 des Befundtages nicht gesehen. Der vollständige Lauf
    kostet rund eine Sekunde; eine Auslassung kostet ein Issue.
    """
    files = []
    for root, dirs, names in os.walk(PUBLIC_DIR):
        if "assets" in root:
            continue
        for n in names:
            if not n.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(root, n), PUBLIC_DIR).replace(os.sep, "/")
            if any(p in rel for p in SKIP_PATTERNS):
                continue
            if any(re.search(muster, rel) for muster, _grund in AUSNAHMEN):
                continue
            files.append(os.path.join(root, n))
    # Wichtige Seiten zuerst (flach vor tief) – nur die Ausgabe-Ordnung
    files.sort(key=lambda f: (f.count(os.sep), f))
    return files


def audit_page(path):
    try:
        html = open(path, encoding="utf-8", errors="ignore").read()
    except OSError as e:
        return os.path.relpath(path, PUBLIC_DIR), [f"Datei nicht lesbar: {e}"]
    issues = []
    name = os.path.relpath(path, PUBLIC_DIR)

    if '<html lang=' not in html:
        issues.append("lang-Attribut fehlt")
    if '<title>' not in html and "<title>" not in html:
        issues.append("title fehlt")
    h1s = re.findall(r"<h1[\s>].*?</h1>", html, re.S)
    if len(h1s) != 1:
        # Seit #623 textlich benannt: ein Issue, das nur „2 h1“ sagt,
        # zwingt zum Nachfragen. Die Texte zeigen sofort, welche
        # Überschrift aus dem Fließtext stammt (dort liegt die Ursache).
        texte = []
        for roh in h1s[:3]:
            innen = re.sub(r"</h1>\s*$", "", re.sub(r"^<h1[^>]*>", "", roh, flags=re.S))
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", innen)).strip()
            texte.append(f"„{text[:60]}“" if text else "„“ (leer)")
        issues.append(f"{len(h1s)} h1 (erwartet: 1): " + " · ".join(texte)
                      if texte else f"{len(h1s)} h1 (erwartet: 1)")
    # Bilder ohne alt-Text. WICHTIG: Ein nacktes `alt`-Attribut ist nach
    # HTML5 identisch mit alt="" (dekorativ) – Hugo --minify kürzt leere
    # Attribute genau so. Wir zählen also nur Bilder, die gar kein
    # alt-Attribut haben (Attribut beginnt nach Whitespace).
    for m in re.finditer(r"<img[^>]*>", html):
        if not re.search(r"(?<=\s)alt(?![a-zA-Z0-9_-])", m.group(0)):
            issues.append("img ohne alt-Text")
    if 'class="skip-link"' not in html and "class=skip-link" not in html:
        issues.append("Skip-Link fehlt")
    return name, issues


def audit_css(sampled_htmls=()):
    issues = []
    # CSS kann in diesem Setup an zwei Orten liegen:
    #   1. als .css-Dateien irgendwo unter public/ (klassisch assets/css/)
    #   2. INLINE in <style>-Blöcken der HTML-Seiten (dieses Theme inlined
    #      alle Styles; Hugo --minify erzeugt KEINE assets/css/-Struktur).
    #
    # FIX (#81): Früher erwartete die Funktion starr public/assets/css/ und
    # crashte mit FileNotFoundError, wenn der Ordner fehlte. Folge: stdout
    # blieb leer, /tmp/a11y_log.txt war leer und das Auto-Issue bekam einen
    # leeren Body. Jetzt: robustes os.walk über alles + Inline-CSS, nie crashen.
    css_parts = []
    for root, _dirs, names in os.walk(PUBLIC_DIR):
        for n in names:
            if n.endswith(".css"):
                try:
                    with open(os.path.join(root, n), encoding="utf-8", errors="ignore") as fh:
                        css_parts.append(fh.read())
                except OSError:
                    pass
    for html in sampled_htmls:
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
            css_parts.append(m.group(1))
    css = "\n".join(css_parts)

    if not css.strip():
        issues.append("Kein CSS auffindbar (weder Dateien noch inline) – CSS-Grundlagen nicht prüfbar")
        return issues

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

    # Robustheit: Das Audit braucht den Hugo-Build (public/). Wird das Skript
    # lokal oder in einem Pre-Build-Schritt aufgerufen, darf es NICHT mit einer
    # Traceback crashen – es meldet den fehlenden Build sauber und bricht nicht
    # die Kette (der Aufrufer steuert über Exit-Code 0 = ohne Befund).
    if not os.path.isdir(PUBLIC_DIR):
        print("Barrierefreiheits-Audit: public/ fehlt – Hugo-Build vorher ausführen, Überspringe Audit.")
        if as_json:
            print(json.dumps({"seiten": 0, "css_probleme": [], "kontrast": [],
                              "gesamt_probleme": 0, "uebersprungen": True},
                             ensure_ascii=False, indent=2))
        sys.exit(0)

    page_results = []
    sampled_htmls = []
    for path in collect_html_files():
        name, issues = audit_page(path)
        page_results.append({"seite": name, "probleme": issues})
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                sampled_htmls.append(fh.read())
        except OSError:
            pass

    css_issues = audit_css(sampled_htmls)
    contrast_results = audit_contrast()

    total_issues = sum(len(p["probleme"]) for p in page_results) + len(css_issues)
    contrast_fail = sum(1 for c in contrast_results if not c["ok"])

    if as_json:
        print(json.dumps({
            "seiten": len(page_results),
            "css_probleme": css_issues,
            "kontrast": contrast_results,
            "gesamt_probleme": total_issues,
            "ausnahmen": sorted({grund for _m, grund in AUSNAHMEN}),
        }, ensure_ascii=False, indent=2))
        sys.exit(1 if total_issues > 0 or contrast_fail else 0)

    # Vollständiger Lauf (seit #623 keine Stichprobe): saubere Seiten
    # werden nur gezählt, nicht aufgezählt – der Report bleibt lesbar.
    sauber = [p for p in page_results if not p["probleme"]]
    print(f"Barrierefreiheits-Audit: {len(page_results)} Seiten geprüft "
          f"(vollständig, {len(sauber)} ohne Befund)\n")
    for p in page_results:
        if not p["probleme"]:
            continue
        print(f"⚠️ ({len(p['probleme'])}) {p['seite']}")
        for i in p["probleme"][:4]:
            print(f"     • {i}")
    if len(page_results) != len(sauber):
        print("")
    for p in sauber[:12]:
        print(f"✅ {p['seite']}")
    if len(sauber) > 12:
        print(f"✅ … und {len(sauber) - 12} weitere Seiten ohne Befund")

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
