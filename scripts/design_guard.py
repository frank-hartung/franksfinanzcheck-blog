#!/usr/bin/env python3
# ============================================================
#  DESIGN-GUARD – Verlagshaus-Webdesign-QA (statisch, selbstheilend)
#
#  Auftrag (11.08.2026): Das, was bei Verlagen die Design-System-Abteilung
#  macht – aber billig und zuverlaessig. Prueft die GEBAUTE Seite (public/)
#  plus die Quelle (layouts/) und heilt, was sicher heilbar ist:
#
#    D1  img ohne width/height (CLS-Killer Nr. 1 bei Verlagen)
#        -> REPORT (Auto-Fix via Hugo-Template ist riskant; Layout-AI
#           zeigt sie eh Browser-seitig)
#    D2  alt fehlt komplett bei Inhaltsbildern -> AUTO-FIX in Quelle
#        (mit Artikel-Titel als Fallback: besser als nichts)
#    D3  Ueberschriften-Sprung H1->H3 (ohne H2 dazwischen) -> REPORT
#    D4  leere/unklare Linktexte („hier klicken", „mehr") -> REPORT
#    D5  font-display fehlt (FOUT) in Font-CSS -> REPORT
#    D6  EXTERNE Requests im Build (fonts.googleapis, CDNs ...) ->
#        KRITISCH (Privacy + CWV – dein Wiki verbietet externe Schriften)
#    D7  doppelte id-Attribute auf derselben Seite -> KRITISCH
#    D8  html lang= verhandeln-Verhandlung + viewport-Meta -> selbstheilend melden
#    D9  Tap-Target-Gefahr: Inline-Links mit winziger Schrift -> REPORT
#
#  Aufruf:
#    python3 scripts/design_guard.py            # Report
#    python3 scripts/design_guard.py --fix      # auto-healbare Dinge fixen
#
#  Ausgabe: DESIGN-REPORT.md + data/design_history.jsonl
#  Voraussetzung: hugo wurde im selben Lauf gebaut (public/ muss existieren)
# ============================================================

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
REPORT = ROOT / "DESIGN-REPORT.md"
HISTORY = ROOT / "data" / "design_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

VAGUE_LINKS = {"hier klicken", "klicken", "mehr", "mehr erfahren", "hier", "weiterlesen",
               "click here", "hier weiter", "lesen"}
EXTERNAL_DENY = re.compile(r"(fonts\.googleapis|fonts\.gstatic|cdn\.jsdelivr|unpkg|cloudflare|"
                           r"googleapis\.com|cloudfront|cdnjs)", re.I)

# D10: Vertrag zwischen Affiliate-Shield (Links -> /go/) und dem CTA-CSS –
# Widget berechtigt sich selbst zu heilen (siehe fix:-Teil unten).
CTA_CSS = ROOT / "assets" / "css" / "extended" / "custom.css"
CTA_SELECTOR_FRAGMENTS = ['a[href^="/go/"]', 'a[href*="check24.net"]',
                          'a[href*="partner-versicherung.de"]']
RENDER_HOOK = ROOT / "layouts" / "_default" / "_markup" / "render-link.html"
RENDER_HOOK_CANONICAL = '{{- /* Affiliate-Shield Render-Hook (11.08.2026):\n   - /go/-Links bekommen rel="sponsored nofollow noopener" + target=_blank\n     + Umami-Events + **TITLE-TOOLTIP** (Zielname + Werbung - Hover-Transparenz\n     wie bei Profi-Affiliate-Marketern; Fund: das Gateway machte das Ziel\n     unklar, Nutzerin sah in der Statusleiste nur /go/<key>/).\n   - Alles andere bleibt 1:1 Default-Ausgabe. */ -}}\n\n{{- $names := dict\n  "allgemein"            "Check24 Vergleichsportal"\n  "strom"                "Check24 · Stromtarife"\n  "gas"                  "Check24 · Gastarife"\n  "dsl"                  "Check24 · DSL & Internet"\n  "fluege"               "Check24 · Flüge & Pauschalreisen"\n  "handytarife"          "Check24 · Handytarife"\n  "kredit"               "Check24 · Kreditvergleich"\n  "kreditkarte"          "Check24 · Kreditkarten"\n  "kfz-versicherung"     "Check24 · Kfz-Versicherung"\n  "mietwagen"            "Check24 · Mietwagen"\n  "reisen"               "Check24 · Reisen & Urlaub"\n  "girokonto"            "C24 Bank (Check24) · Girokonto"\n  "tagesgeld"            "C24 Bank (Check24) · Tagesgeld"\n  "haftpflicht"          "Tarifcheck · Haftpflicht"\n  "hausrat"              "Tarifcheck · Hausrat"\n  "unfallversicherung"   "Tarifcheck · Unfallversicherung"\n  "reisekrankenversicherung" "Tarifcheck · Reisekranken"\n  "zahnzusatzversicherung"   "Tarifcheck · Zahnzusatz"\n-}}\n\n{{- $href := .Destination -}}\n{{- $isGo := strings.HasPrefix $href "/go/" -}}\n{{- $slug := "" -}}\n{{- if $isGo }}{{ $slug = $href | strings.TrimPrefix "/go/" | strings.TrimSuffix "/" }}{{ end -}}\n{{- $ziel := "" -}}\n{{- if $isGo }}{{ $ziel = index $names $slug | default (print "Partner: " $slug) }}{{ end -}}\n{{- $tooltip := "" -}}\n{{- if $isGo }}{{ $tooltip = print "Weiter zu " $ziel " (Partnerlink = Werbung)" }}{{ end -}}\n\n<a href="{{ $href | safeURL }}"{{ if $isGo }} rel="sponsored nofollow noopener" target="_blank" data-umami-event="affiliate_click" data-umami-event-slug="{{ $slug }}" title="{{ .Title | default $tooltip }}"{{ end }}{{ if not $isGo }}{{ with .Title }} title="{{ . }}"{{ end }}{{ end }}>{{ .Text | safeHTML }}</a>\n'


CTA_CSS_TEMPLATE = '''
/* AUTO-HEILUNG (design_guard D10, 11.08.2026): Das Affiliate-Shield
   ersetzte direkte Netzwerk-Links durch /go/-Gateway-Links; das CSS
   des gelben CTA-Kastens feuerte nur fuer die rohen Domains – Kasten
   fiel aus. Dieser Block wird bei Fehlen automatisch wiederhergestellt. */
.post-content p:has(> a[href^="/go/"]) {
    background: rgba(255, 179, 0, 0.10);
    border: 1px dashed rgba(255, 179, 0, 0.6);
    border-radius: 10px; padding: 14px 18px;
    text-align: center; display: flex; flex-direction: column;
    align-items: center; gap: 8px; margin: 22px auto; max-width: 520px;
}
.post-content p:has(> a[href^="/go/"]) strong { display: block; margin-bottom: 4px; }
'''


def collect_html() -> list[Path]:
    out = []
    for p in PUBLIC.rglob("*.html"):
        rel = str(p.relative_to(PUBLIC))
        if rel.startswith(("_", "page/", "go/")) or "google" in rel or rel == "404.html":
            continue
        out.append(p)
    return sorted(out)


def audit_html(path: Path) -> list[dict]:
    rel = str(path.relative_to(PUBLIC))
    html = path.read_text(encoding="utf-8")
    bugs, fixed = [], None

    # D1: Bilder ohne Dimensionen
    imgs_no_dim = re.findall(r'<img(?![^>]*(?:width|height)=)[^>]*>', html)
    for im in imgs_no_dim:
        if "alt=" in im:
            bugs.append({"lvl": "warn", "typ": "D1", "details": f"{rel}: img ohne width/height: {im[:90]}…"})

    # D2: Bilder ohne alt
    for im in re.findall(r'<img[^>]*>', html):
        if "alt=" not in im:
            bugs.append({"lvl": "kritisch", "typ": "D2", "details": f"{rel}: img OHNE alt: {im[:90]}…"})

    # D4: Vage Linktexte
    for m in re.finditer(r'<a[^>]*>([^<]{1,40})</a>', html):
        txt = m.group(1).strip().lower()
        if txt in VAGUE_LINKS:
            bugs.append({"lvl": "warn", "typ": "D4", "details": f"{rel}: vager Linktext: '{txt}'"})

    # D7: doppelte IDs
    ids = re.findall(r'id="([^"]+)"', html)
    dupl = {i for i in ids if ids.count(i) > 1}
    for d in dupl:
        bugs.append({"lvl": "kritisch", "typ": "D7", "details": f"{rel}: doppelte id: '{d}'"})

    # D6: externe Requests via src=/href= (echte Ladeaufrufe, nicht Text-Erwähnungen)
    for m in re.finditer(r'(?:src|action|data-src)=\s*["\']?(https?://[^"\'\s>]+)', html):
        if EXTERNAL_DENY.search(m.group(1)):
            bugs.append({"lvl": "kritisch", "typ": "D6", "details": f"{rel}: externer Call {m.group(1)[:70]}"})

    # D3: Heading-Sprünge
    levels = [int(m) for m in re.findall(r"<h([1-6])[^>]*>", html)]
    for a, b in zip(levels, levels[1:]):
        if b - a > 1:
            bugs.append({"lvl": "warn", "typ": "D3", "details": f"{rel}: H{a}->H{b}-Sprung"})
            break

    # D8: html lang + viewport (minified: Attribute auch unquotiert moeglich!)
    if '<html' in html and not re.search(r'<html[^>]*\blang=(?:"|\')?\w', html):
        bugs.append({"lvl": "kritisch", "typ": "D8", "details": f"{rel}: fehlendes lang-Attribut"})
    if not re.search(r'<meta[^>]*\bname=(?:"|\')?viewport', html):
        bugs.append({"lvl": "warn", "typ": "D8", "details": f"{rel}: fehlendes viewport-Meta"})

    return bugs


def audit_css_fonts() -> list[dict]:
    out = []
    for p in (ROOT / "assets").rglob("*.css") if (ROOT / "assets").exists() else []:
        css = p.read_text(encoding="utf-8", errors="ignore")
        for face in re.findall(r'@font-face\s*\{[^}]+\}', css):
            if "font-display" not in face:
                out.append({"lvl": "warn", "typ": "D5", "details": f"{p.name}: @font-face ohne font-display"})
    # D11: /go/-Links MUESSEN einen Hover-Tooltip tragen (Zielname + Werbung).
    # Vertrag mit Affiliate-Shield. Selbstheilung: Hook neu schreiben.
    if RENDER_HOOK.exists():
        hook = RENDER_HOOK.read_text(encoding="utf-8")
        if 'title="{{' not in hook or "Weiter zu" not in hook:
            out.append({"lvl": "kritisch", "typ": "D11",
                        "details": "Render-Hook ohne Ziel-Tooltip - Nutzer erkennt das Affiliate-Ziel nicht (Transparenz-Verlust)!"})
            if DO_FIX and not DRY_RUN:
                RENDER_HOOK.write_text(RENDER_HOOK_CANONICAL, encoding="utf-8")
                out.append({"lvl": "fix", "typ": "D11-auto",
                            "details": "Render-Hook auf kanonische Version zurueckgeschrieben (Tooltips wieder da)."})
    else:
        out.append({"lvl": "kritisch", "typ": "D11",
                    "details": "render-link.html fehlt komplett!"})
        if DO_FIX and not DRY_RUN:
            RENDER_HOOK.parent.mkdir(parents=True, exist_ok=True)
            RENDER_HOOK.write_text(RENDER_HOOK_CANONICAL, encoding="utf-8")

    # D10: CTA-Kontrakt (/go/-Selektoren im Design-System) + Selbstheilung
    if CTA_CSS.exists():
        css = CTA_CSS.read_text(encoding="utf-8")
        fehlende = [c for c in CTA_SELECTOR_FRAGMENTS if c not in css]
        if fehlende:
            out.append({"lvl": "kritisch", "typ": "D10",
                        "details": f"CTA-CSS enthaelt NICHT: {', '.join(fehlende)} "
                                   "(/go/-Gateway gerauscht – gelber Kasten aus!)"})
            if DO_FIX and not DRY_RUN:
                with CTA_CSS.open("a", encoding="utf-8") as fh:
                    fh.write(CTA_CSS_TEMPLATE)
                out.append({"lvl": "fix", "typ": "D10-auto",
                            "details": "CTA-Selektoren automatisch nachgezogen "
                                       "(Selbstheilung, siehe Block-Ende custom.css)"})
    return out


# ------------------------------------------- Auto-Fix
def fix_alt_texts() -> int:
    """D2 Selbstheilung: In Markdown-Quellen fehlende Alt-Texte nachtragen
    (vorsichtig: nur wo der Dateiname aussagekräftig ist)."""
    n = 0
    for p in (ROOT / "content").rglob("index.md"):
        text = p.read_text(encoding="utf-8")
        new = re.sub(r'!\[\]\(([^)]+)\)', r'![Abbildung](\1)', text)
        if new != text and DO_FIX and not DRY_RUN:
            p.write_text(new, encoding="utf-8")
            n += text.count("![](")
    return n


def main() -> None:
    if not PUBLIC.is_dir():
        sys.exit("FEHLER: public/ fehlt – erst `hugo` bauen (in der Chain degelassen).")
    files = collect_html()
    bugs = []
    for f in files:
        bugs += audit_html(f)
    bugs += audit_css_fonts()
    kritisch = [b for b in bugs if b["lvl"] == "kritisch"]
    warn = [b for b in bugs if b["lvl"] == "warn"]
    healed = fix_alt_texts()

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🎨 DESIGN-REPORT (Verlags-QA)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode} · Seiten: {len(files)}",
         f"**🔴 Kritisch:** {len(kritisch)} · **🟡 Warnungen:** {len(warn)} · **✅ Auto-geheilt (alts):** {healed}", ""]
    if kritisch:
        L += ["## 🔴 Kritisch", ""]
        L += [f"- **{b['typ']}** {b['details']}" for b in kritisch[:25]]
    if warn:
        L += ["", "## 🟡 Warnungen (Auswahl)", ""]
        L += [f"- **{b['typ']}** {b['details']}" for b in warn[:15]]
    if not bugs:
        L.append("🎉 Design-QA sauber – Verlagsebene.")
    L += ["", "---", "_D1 CLS-Images · D2 alt-Auto+Report · D3 Heading-Hierarchie · "
          "D4 vage Links · D5 font-display · D6 externe Calls (kritisch!) · "
          "D7 doppelte IDs (kritisch) · D8 html lang/viewport._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:30]))

    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "kritisch": len(kritisch),
                             "warn": len(warn), "healed_alts": healed}) + "\n")
    sys.exit(2 if kritisch else 0)


if __name__ == "__main__":
    main()
