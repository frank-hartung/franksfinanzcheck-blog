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

Exit-Code: 0 = bestanden · 1 = A11y-Befund · 2 = Audit nicht prüfbar

BLINDER FLECK GESCHLOSSEN (Dauerheilung #623, 07.10.2026):
Bis dahin prüfte dieses Audit eine STICHPROBE von 20 Seiten – von 107
gebauten Seiten. Die dritte Doppel-H1 des Befundtages
(/studien/fixkosten-index-2026-q4/) stand im selben Build und blieb
UNSICHTBAR; gemeldet wurden nur /presse/ und /studien/. Ein Audit,
das ein Fünftel sieht, würfelt. Jetzt läuft der Lauf über ALLE
gebauten Seiten und nennt bei einer falschen H1-Anzahl die Überschriften
TEXTLICH, damit das automatische Issue ohne Nachfrage erklärt, was zu tun
ist. Die H1-Regel samt HTML-Parser und begründeten Ausnahmen gehört der
Wache scripts/h1_wache.py (S1–S3). Fehlt die Wache, der Build oder eine
prüfbare Seite, meldet das Audit Exit 2 statt eines falschen Grün.
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


# Seiten, die bewusst minimal sind und NICHT vom Voll-Audit geprüft werden.
# Die Liste kommt ausschließlich aus scripts/h1_wache.py: Jede Ausnahme
# hat dort einen dokumentierten Grund. Ist die Wache nicht importierbar,
# wird das Audit rot – ein zweiter Fallback würde eine zweite Wahrheit und
# damit eine stille Driftstelle schaffen.
_H1_WACHE_IMPORT_ERROR = None
AUSNAHMEN = None
h1_der_seite = None
h1_ist_gefuellt = None
try:
    from h1_wache import AUSNAHMEN_SEITE as AUSNAHMEN, h1_der_seite, h1_ist_gefuellt
except ImportError as exc:  # sichtbar fail-closed, niemals Ersatzliste
    _H1_WACHE_IMPORT_ERROR = f"{exc.__class__.__name__}: {exc}"


def _require_h1_contract():
    """Stoppt den Audit, wenn sein H1-SSOT fehlt oder nicht nutzbar ist."""
    if (_H1_WACHE_IMPORT_ERROR is not None or AUSNAHMEN is None
            or not callable(h1_der_seite) or not callable(h1_ist_gefuellt)):
        detail = f" ({_H1_WACHE_IMPORT_ERROR})" if _H1_WACHE_IMPORT_ERROR else ""
        raise RuntimeError(
            "H1-Wache scripts/h1_wache.py nicht ladbar; das A11y-Audit "
            f"bricht fail-closed ab{detail}. Es gibt keine Ersatz-Ausnahmeliste."
        )


def collect_html_files(public_dir=None):
    """Alle prüfbaren, gebauten HTML-Dateien – keine Stichprobe, kein Blindfilter.

    Nur die begründeten Routen-Ausnahmen aus der H1-Wache werden
    ausgelassen. Insbesondere gibt es keine pauschalen Verzeichnisfilter
    (z. B. ``assets``) oder substring-basierten Skip-Listen.
    """
    _require_h1_contract()
    public_root = os.fspath(public_dir or PUBLIC_DIR)
    files = []
    for root, _dirs, names in os.walk(public_root):
        for n in names:
            if not n.lower().endswith(".html"):
                continue
            full_path = os.path.join(root, n)
            rel = os.path.relpath(full_path, public_root).replace(os.sep, "/")
            if any(re.search(muster, rel) for muster, _grund in AUSNAHMEN):
                continue
            files.append(full_path)
    # Flache Seiten zuerst – ausschließlich die Ausgabe-Ordnung.
    files.sort(key=lambda f: (f.count(os.sep), f))
    return files


def audit_page(path, public_dir=None):
    _require_h1_contract()
    public_root = os.fspath(public_dir or PUBLIC_DIR)
    name = os.path.relpath(path, public_root)
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            html = fh.read()
    except OSError as e:
        return name, [f"Datei nicht lesbar: {e}"]
    issues = []

    if '<html lang=' not in html:
        issues.append("lang-Attribut fehlt")
    if '<title>' not in html and "<title>" not in html:
        issues.append("title fehlt")
    # Die H1-Erkennung ist dieselbe HTML-aware Implementierung wie im
    # Build-Gate. Kommentare, Skriptstrings und Entities können den Zähler
    # daher weder aufblähen noch eine leere H1 kaschieren.
    h1s = h1_der_seite(html)
    if len(h1s) != 1:
        texte = [f"„{text[:60]}“" if text else "„“ (leer)" for text in h1s[:3]]
        issues.append(f"{len(h1s)} h1 (erwartet: 1): " + " · ".join(texte)
                      if texte else f"{len(h1s)} h1 (erwartet: 1)")
    elif not h1_ist_gefuellt(h1s[0]):
        issues.append("H1 ist leer oder enthält nur unsichtbare Zeichen (erwartet: nicht-leere H1)")
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


def audit_css(page_htmls=(), public_dir=None):
    issues = []
    public_root = os.fspath(public_dir or PUBLIC_DIR)
    # CSS kann in diesem Setup an zwei Orten liegen:
    #   1. als .css-Dateien irgendwo unter public/ (klassisch assets/css/)
    #   2. INLINE in <style>-Blöcken der HTML-Seiten (dieses Theme inlined
    #      alle Styles; Hugo --minify erzeugt KEINE assets/css/-Struktur).
    #
    # FIX (#81): Früher erwartete die Funktion starr public/assets/css/ und
    # crashte mit FileNotFoundError, wenn der Ordner fehlte. Folge: stdout
    # blieb leer, /tmp/a11y_log.txt war leer und das Auto-Issue bekam einen
    # leeren Body. Jetzt: robustes os.walk über den Build + Inline-CSS.
    css_parts = []
    for root, _dirs, names in os.walk(public_root):
        for n in names:
            if n.endswith(".css"):
                try:
                    with open(os.path.join(root, n), encoding="utf-8", errors="ignore") as fh:
                        css_parts.append(fh.read())
                except OSError:
                    pass
    for html in page_htmls:
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


def _audit_unavailable(message, as_json=False):
    """Meldet eine nicht prüfbare Grundlage als Fehler, nie als Grün."""
    if as_json:
        print(json.dumps({
            "ok": False,
            "seiten": 0,
            "css_probleme": [],
            "kontrast": [],
            "gesamt_probleme": 1,
            "ausnahmen": [],
            "uebersprungen": True,
            "fehler": [message],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"🛑 Barrierefreiheits-Audit nicht prüfbar: {message}")
    return 2


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args

    # Fail-closed: Ohne kanonische H1-Wache gäbe es eine zweite,
    # driftende Ausnahmeliste oder eine unprüfbare H1-Erkennung.
    try:
        _require_h1_contract()
    except RuntimeError as exc:
        return _audit_unavailable(str(exc), as_json)

    public_root = os.fspath(PUBLIC_DIR)
    if not os.path.isdir(public_root):
        return _audit_unavailable(
            "public/ fehlt – zuerst den Hugo-Build ausführen; kein Audit ohne Build.",
            as_json,
        )

    paths = collect_html_files(public_root)
    if not paths:
        return _audit_unavailable(
            "keine prüfbare HTML-Seite im Build gefunden; ein leerer oder "
            "vollständig ausgenommener Build ist kein grünes Audit.",
            as_json,
        )

    page_results = []
    page_htmls = []
    for path in paths:
        name, issues = audit_page(path, public_root)
        page_results.append({"seite": name, "probleme": issues})
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                page_htmls.append(fh.read())
        except OSError:
            pass

    css_issues = audit_css(page_htmls, public_root)
    contrast_results = audit_contrast()

    total_issues = sum(len(p["probleme"]) for p in page_results) + len(css_issues)
    contrast_fail = sum(1 for c in contrast_results if not c["ok"])
    ok = total_issues == 0 and contrast_fail == 0

    if as_json:
        print(json.dumps({
            "ok": ok,
            "seiten": len(page_results),
            "css_probleme": css_issues,
            "kontrast": contrast_results,
            "gesamt_probleme": total_issues,
            "ausnahmen": sorted({grund for _m, grund in AUSNAHMEN}),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1

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
    if not ok:
        return 1
    print("✅ Barrierefreiheit auf Top-Niveau")
    return 0


if __name__ == "__main__":
    sys.exit(main())
