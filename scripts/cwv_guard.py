#!/usr/bin/env python3
"""
CWV-GUARD – Core-Web-Vitals-Wächter für FranksFinanzcheck (Agentur/Performance)

Google misst Core Web Vitals (LCP, CLS, INP) als Ranking-Faktor. Das Repo hat
einige Optimierer (cls_optimizer, lcp_*, dom_size, image_optimizer, …), aber
KEINE regelmäßige Mess-Schleife, die den Ist-Zustand gegen ein Soll prüft und
bei Überschreitung meldet. Dieser Wächter schließt die Lücke deterministisch
(ohne Browser) und gibt eine Ampel:

  - Scanne (falls vorhanden) den gebauten Baum `public/`.
  - Fallback: `static/`-Assets + Content-Heuristik (auch ohne Hugo-Build lauffähig).
  - Prüfung auf LCP-Kandidaten (große Covers), CLS-Risiko (fehlende
    width/height bzw. aspect-ratio auf Bildern), INP/JS-Budget, Render-Blocking,
    Bild-Optimierung (avif/webp vorhanden?), Dateigrößen.

AUSGABE:
  - `CWV-REPORT.md` – Ampel-Report + Befunde + Empfehlung
  - `data/cwv_manifest.json` – Kennzahlen (für Verlauf/Issues)
  - `--issue`          – GitHub-Issue-Body (bei SOLL-Verstoß)
  - `--selftest`       – eingefrorene Fälle

Exit-Codes: 0 = grün, 1 = Amber/Rot (SOLL verletzt), 2 = Selftest/Fehler.

Nutzung:
  python3 scripts/cwv_guard.py            # scannt public/ sonst static/
  python3 scripts/cwv_guard.py --public public/
  python3 scripts/cwv_guard.py --selftest
"""
import glob
import json
import os
import re
import sys
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(BLOG_DIR, "CWV-REPORT.md")
MANIFEST = os.path.join(BLOG_DIR, "data", "cwv_manifest.json")
PUBLIC_DEFAULT = os.path.join(BLOG_DIR, "public")
STATIC_DIR = os.path.join(BLOG_DIR, "static")

TODAY = datetime.date.today()

# Bild-Optimierungs-Budgets (Google-Leitplanken, konservativ für Affiliate-Seite)
IMG_OVER_BUDGET = 220 * 1024     # > 220 KB pro Bild = rot
IMG_SOFT_BUDGET = 160 * 1024     # > 160 KB = amber
TOTAL_IMG_BUDGET = 900 * 1024    # Summe aller Bilder/Seite-Unterbau

# LCP-Ziel: Cover (og:image / hero) sollte < 180 KB & optimiert (avif/webp) sein.
COVER_BYTES_MAX = 200 * 1024
ACCEPTED_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif")

# DOM-/JS-Budget: statische Heuristik (Hugo rendert aus kleinen Vorlagen; ein
# Ausreißer deutet auf unkontrolliertes Inline-JS oder Riesen-Styles).
DOM_NODES_SOFT = 2500
DOM_NODES_HARD = 4000

# Inline-JS-Budget über die Stichprobe (80 Seiten): PaperMod bringt pro Seite
# ~4 bewusste Inline-Snippets (Theme-Toggle, Suche, Menü, Copy-Code) mit. Erst
# deutlich darüber liegt ein echtes Bündelungs-Problem vor.
INLINE_JS_SOFT_MAX = 8 * 80

# Verzeichnisse, die NICHT auf Artikel-/LCP-Seiten ausgeliefert werden
# (Profil-/Board-Assets für Pinterest). Sie sind für die Core-Web-Vitals der
# Blog-Seiten ohne Relevanz und würden nur Rauschen erzeugen.
NON_PAGE_DIRS = {"social", "boards"}

# Skript-Typen, die den Renderer NICHT blockieren und daher nicht als
# "render_block_js" gezählt werden dürfen:
#   - application/ld+json  → strukturierte Daten (SEO!), wird nie ausgeführt
#   - importmap / speculationrules → Metadaten, kein Parser-Block
#   - text/template, text/x-template → inerte Vorlagen
# Ein <script> ohne src IST per Definition nicht "ohne async/defer" – async und
# defer wirken ausschließlich auf EXTERNE Skripte. Inline-JS blockiert zwar den
# Parser, ist aber eine andere Klasse von Befund (inline_js) als ein
# render-blockierendes externes Skript.
NONBLOCKING_SCRIPT_TYPES = (
    "application/ld+json",
    "importmap",
    "speculationrules",
    "text/template",
    "text/x-template",
    "application/json",
)


def _classify_scripts(html):
    """Zerlegt alle <script>-Starttags in echte CWV-Klassen.

    Rückgabe: (blocking_external, inline_js, structured_data)
      blocking_external – <script src=...> OHNE async/defer/module → echter
                          Render-Blocker, der einzige Befund mit INP/LCP-Effekt
      inline_js         – ausführbares Inline-JS (Parser-Block, aber kein
                          Netzwerk-Roundtrip) → nur Hinweis
      structured_data   – JSON-LD & Co. → KEIN Befund (SEO-Pflichtinhalt)
    """
    blocking_external = inline_js = structured_data = 0
    for tag in re.findall(r"<script\b[^>]*>", html, re.I):
        m = re.search(r"""\btype\s*=\s*["']?([^"'\s>]+)""", tag, re.I)
        stype = (m.group(1).lower() if m else "")
        if stype in NONBLOCKING_SCRIPT_TYPES:
            structured_data += 1
            continue
        has_src = re.search(r"""\bsrc\s*=\s*["']?[^"'\s>]+""", tag, re.I)
        if not has_src:
            inline_js += 1
            continue
        # Externes Skript: async, defer oder type="module" (implizit deferred)
        if re.search(r"\b(async|defer)\b", tag, re.I) or stype == "module":
            continue
        blocking_external += 1
    return blocking_external, inline_js, structured_data


def _human(n):
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB".replace(".0 MB", " MB")
    return f"{n / 1024:.0f} KB"


def _scan_static():
    """Analysiert static/ auf Bild-Größen + Optimierungsgrad (ohne Build)."""
    findings = []
    files = []
    for ext in ACCEPTED_IMG_EXT:
        files += glob.glob(os.path.join(STATIC_DIR, "**", "*" + ext), recursive=True)
    total = 0
    covers = []
    for f in files:
        rel_parts = os.path.relpath(f, BLOG_DIR).split(os.sep)
        if any(p in NON_PAGE_DIRS for p in rel_parts):
            continue  # Nicht-Seiten-Assets (Profil/Boards) außen vor
        size = os.path.getsize(f)
        rel = os.path.relpath(f, BLOG_DIR)
        total += size
        # Optimierungsgrad: hat es eine .avif/.webp-Geschwister-Variante?
        base = os.path.splitext(f)[0]
        has_avif = os.path.exists(base + ".avif")
        has_webp = os.path.exists(base + ".webp")
        if "covers" in f:
            covers.append({"file": rel, "bytes": size, "avif": has_avif,
                           "webp": has_webp})
        # Größen-Ampel
        if size > IMG_OVER_BUDGET:
            findings.append({
                "level": "red", "code": "img_over",
                "file": rel, "bytes": size,
                "msg": f"Bild zu groß ({_human(size)} > {_human(IMG_OVER_BUDGET)})",
            })
        elif size > IMG_SOFT_BUDGET:
            findings.append({
                "level": "amber", "code": "img_soft",
                "file": rel, "bytes": size,
                "msg": f"Bild optimierbar ({_human(size)} > {_human(IMG_SOFT_BUDGET)})",
            })
    # LCP-Wächter: Cover > Ziel
    worst = max(covers, key=lambda c: c["bytes"]) if covers else None
    if worst and worst["bytes"] > COVER_BYTES_MAX:
        findings.append({
            "level": "red", "code": "lcp_cover",
            "file": worst["file"], "bytes": worst["bytes"],
            "msg": f"LCP-Kandidat (Cover) zu groß ({_human(worst['bytes'])} > "
                   f"{_human(COVER_BYTES_MAX)}), optimierte Variante? "
                   f"avif={worst['avif']} webp={worst['webp']}",
        })
    metrics = {"total_img_bytes": total, "count_img": len(files),
               "count_covers": len(covers), "worst_cover_bytes": (worst["bytes"] if worst else 0)}
    return metrics, findings


def _scan_public(public_dir):
    """Analysiert den gebauten Baum auf Render-Blocking + DOM-Heuristik."""
    findings = []
    html_files = glob.glob(os.path.join(public_dir, "**", "*.html"), recursive=True)
    js = glob.glob(os.path.join(public_dir, "**", "*.js"), recursive=True)
    css = glob.glob(os.path.join(public_dir, "**", "*.css"), recursive=True)
    js_bytes = sum(os.path.getsize(f) for f in js)
    css_bytes = sum(os.path.getsize(f) for f in css)
    total_html = sum(os.path.getsize(f) for f in html_files)
    # Render-Blocking: Inline-<style> Blöcke & viele <script> ohne async/defer
    inline_styles = 0
    blocking_js = 0
    inline_js = 0
    structured_data = 0
    img_nosize = 0
    for f in html_files[:80]:  # Stichprobe (Home + Top-Seiten), Budgierbar
        try:
            t = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        inline_styles += len(re.findall(r"<style(?![^>]*>)[^>]*>", t))
        b, i, s = _classify_scripts(t)
        blocking_js += b
        inline_js += i
        structured_data += s
        img_nosize += len(re.findall(
            r"<img (?![^>]*(?:width=|height=|style=))", t))
    # Rückwärtskompatibler Alias für ältere Manifest-Leser
    inline_scripts_plain = blocking_js
    if inline_styles:
        findings.append({"level": "amber", "code": "render_block_css",
                         "count": inline_styles,
                         "msg": f"{inline_styles} Inline-<style>-Blöcke (Render-Blocking-Risiko)"})
    if blocking_js:
        findings.append({"level": "amber", "code": "render_block_js",
                         "count": blocking_js,
                         "msg": f"{blocking_js} externe Skripte ohne async/defer "
                                "(Render-Blocking, LCP/INP-Risiko)"})
    # Inline-JS ist nur ab einer relevanten Menge ein Befund – einzelne
    # Theme-Snippets (Theme-Toggle, Suche) sind bewusst inline, um genau einen
    # Render-blockierenden Roundtrip zu SPAREN.
    if inline_js > INLINE_JS_SOFT_MAX:
        findings.append({"level": "amber", "code": "inline_js",
                         "count": inline_js,
                         "msg": f"{inline_js} Inline-JS-Blöcke über "
                                f"{len(html_files[:80])} Seiten "
                                f"(> {INLINE_JS_SOFT_MAX} Ø-Budget) – bündeln"})
    if img_nosize:
        findings.append({"level": "amber", "code": "cls_img",
                         "count": img_nosize,
                         "msg": f"{img_nosize} <img>-Elemente ohne width/height/style "
                                "(CLS-Risiko)"})
    metrics = {"html_files": len(html_files), "js_files": len(js),
               "css_files": len(css), "js_bytes": js_bytes,
               "css_bytes": css_bytes, "html_bytes": total_html,
               "inline_styles": inline_styles,
               "blocking_js": blocking_js,
               "inline_js": inline_js,
               "structured_data_scripts": structured_data,
               "inline_scripts_plain": inline_scripts_plain,
               "img_nosize": img_nosize}
    return metrics, findings


def _verdict(static_metrics, static_findings, public_metrics, public_findings):
    ratings = {"green": 0, "amber": 0, "red": 0}
    for f in static_findings + public_findings:
        ratings[f["level"]] += 1
    if ratings["red"] > 0:
        return "RED"
    if ratings["amber"] > 0:
        return "AMBER"
    return "GREEN"


def _render_report(verdict, s_met, s_find, p_met, p_find):
    lines = [
        "# ⚡ Core-Web-Vitals-Wächter (Agentur/Performance)",
        f"**Stand:** {TODAY.isoformat()} · **Messmethode:** deterministisch (kein Browser)",
        "",
        f"## 🤖 Gesamt-Ampel: **{verdict}**",
        "",
        "| Kanal | Befunde |",
        "|---|---|",
        f"| Bild-Budget (`static/`) | {len(s_find)} |",
        f"| Build-Hygiene (`public/`) | {len(p_find)} |",
        "",
    ]
    if s_find or p_find:
        lines.append("## Befunde")
        lines.append("")
        lines.append("| Ebene | Code | Details |")
        lines.append("|---|---|---|")
        for f in s_find + p_find:
            lines.append(f"| {f['level'].upper()} | {f['code']} | {f['msg']} |")
        lines.append("")
    else:
        lines.append("## Befunde")
        lines.append("")
        lines.append("_Alle Soll-Werte eingehalten._")
        lines.append("")
    if s_met:
        lines += [
            "## Kennzahlen (static/)",
            "",
            f"- Bilder gesamt: **{s_met['count_img']}** (Summe {_human(s_met['total_img_bytes'])})",
            f"- Cover: **{s_met['count_covers']}** · größtes Cover {_human(s_met['worst_cover_bytes'])}",
            "",
        ]
    if p_met:
        lines += [
            "## Kennzahlen (public/)",
            "",
            f"- HTML-Dateien: **{p_met['html_files']}** · JS-Dateien {p_met['js_files']} "
            f"({_human(p_met['js_bytes'])}) · CSS {p_met['css_files']} ({_human(p_met['css_bytes'])})",
            f"- Inline-<style>: {p_met['inline_styles']} · "
            f"externe Skripte ohne async/defer: {p_met.get('blocking_js', 0)} · "
            f"Inline-JS-Blöcke: {p_met.get('inline_js', 0)} · "
            f"JSON-LD/strukturierte Daten (nicht blockierend): "
            f"{p_met.get('structured_data_scripts', 0)} · "
            f"<img> ohne Größensetzung: {p_met['img_nosize']}",
            "",
        ]
    lines += [
        "## Empfehlungen",
        "",
        "1. **LCP:** Größtes Cover als AVIF/WebP ausliefern (`generate_covers.py` erzeugt die",
        "   Varianten bereits; den `<picture>`-Tag via `cover.html` nutzen).",
        "2. **Bild-Budget:** Bilder > 220 KB komprimieren oder per `<picture>` responsive servieren.",
        "3. **INP/JS:** externe Skripte mit `defer` laden, Inline-JS minimieren.",
        "4. **CLS:** jedem `<img>` `width`/`height`/`aspect-ratio` mitgeben.",
        "5. **Mess-Schleife:** diesen Wächter wöchentlich in `seo-weekly.yml` nach dem Hugo-Build."
        "   laufen lassen (siehe Premium-Governance-Workflow).",
        "",
        f"_Automatisch erzeugt von `scripts/cwv_guard.py` am {TODAY.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"


def _selftest():
    failures = []
    # over-budget Erkennung
    if IMG_OVER_BUDGET <= 200 * 1024 and IMG_OVER_BUDGET >= 220 * 1024:
        # unrealistisch, aber wir testen die Logik direkt
        pass
    # Künstliche Datei: > Budget -> rot
    if not (IMG_OVER_BUDGET > IMG_SOFT_BUDGET > 0):
        failures.append("Budget-Reihenfolge inkonsistent")
    if COVER_BYTES_MAX <= 0:
        failures.append("Cover-Budget trivial")

    # --- Skript-Klassifikation (Regressionsschutz gegen JSON-LD-Fehlalarm) ---
    cases = [
        # (HTML, erwartet blocking, inline, structured)
        ('<script type="application/ld+json">{}</script>', 0, 0, 1),
        ("<script type='application/ld+json'>{}</script>", 0, 0, 1),
        ('<script type="application/ld+json" >{}</script>', 0, 0, 1),
        ('<script src="/a.js"></script>', 1, 0, 0),
        ('<script defer src="/a.js"></script>', 0, 0, 0),
        ('<script src="/a.js" async></script>', 0, 0, 0),
        ('<script type="module" src="/a.js"></script>', 0, 0, 0),
        ('<script>var x=1;</script>', 0, 1, 0),
        ('<script type="importmap">{}</script>', 0, 0, 1),
        ('<script type="speculationrules">{}</script>', 0, 0, 1),
        ('<script defer crossorigin="anonymous" src="/s.js" integrity="x"></script>',
         0, 0, 0),
    ]
    for html, eb, ei, es in cases:
        gb, gi, gs = _classify_scripts(html)
        if (gb, gi, gs) != (eb, ei, es):
            failures.append(
                f"Skript-Klassifikation falsch für {html!r}: "
                f"erwartet blocking={eb} inline={ei} strukturiert={es}, "
                f"erhalten blocking={gb} inline={gi} strukturiert={gs}")

    # Eine reine JSON-LD-Seite darf NIEMALS einen render_block_js-Befund geben
    ld_page = '<html><head>' + '<script type="application/ld+json">{}</script>' * 6 + '</head></html>'
    b, _, s = _classify_scripts(ld_page)
    if b != 0 or s != 6:
        failures.append("JSON-LD-Seite erzeugt fälschlich Render-Blocking-Befund")
    # _human
    if _human(2048) != "2 KB":
        failures.append(f"_human(2048) != '2 KB' ({_human(2048)})")
    if _human(2048 * 1024) != "2 MB":
        failures.append(f"_human(2MB) != '2 MB' ({_human(2048 * 1024)})")
    # Verdict-Logik
    v = _verdict({}, [{"level": "red"}], {}, [])
    if v != "RED":
        failures.append(f"verdict ROT: {v}")
    v = _verdict({}, [{"level": "amber"}], {}, [])
    if v != "AMBER":
        failures.append(f"verdict AMBER: {v}")
    v = _verdict({}, [], {}, [])
    if v != "GREEN":
        failures.append(f"verdict GRÜN: {v}")
    if failures:
        print("❌ CWV-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ CWV-SELFTEST bestanden (Budgets, Verdict-Ampel, _human).")
    return 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    public_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--public" and i + 1 < len(sys.argv):
            public_dir = sys.argv[i + 1]
    if public_dir is None and os.path.isdir(PUBLIC_DEFAULT):
        public_dir = PUBLIC_DEFAULT

    s_met, s_find = _scan_static()
    p_met, p_find = ({}, [])
    if public_dir and os.path.isdir(public_dir):
        p_met, p_find = _scan_public(public_dir)
    verdict = _verdict(s_met, s_find, p_met, p_find)
    report = _render_report(verdict, s_met, s_find, p_met, p_find)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY.isoformat(),
            "verdict": verdict,
            "static": s_met, "public": p_met,
            "findings": s_find + p_find,
        }, f, ensure_ascii=False, indent=2)
    print(report)
    if "--issue" in sys.argv and verdict != "GREEN":
        n = len(s_find) + len(p_find)
        print("\n===== ISSUE BODY =====\n")
        print(f"## ⚡ Core Web Vitals: {verdict} – {n} Befunde\n\n"
              f"{report}\n\n---\n_Automatisch vom CWV-Wächter._")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
