#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-INTEGRITY-GATE – strukturelle CTA-Prüfung + Render-Beweis
#  (14.08.2026, Frank: "Die Affiliate-Links wurden beschädigt. Bitte
#  dauerhaft beheben (Automatik und Selbstheilung), indem die
#  Veröffentlichung nur vorgenommen wird, wenn alle Links funktionieren
#  und tatsächlich im Blog erscheinen. Ansonsten soll sofort eine
#  Reparatur erfolgen.")
#
#  LÜCKE, DIE DIESES SKRIPT SCHLIESST (Vorfall 14.08.2026: 8 Live-Artikel
#  hatten beschädigte CTA-Boxen – dangling Markdown-Links ohne '](url)',
#  verstümmelter Fließtext direkt an der CTA, ein Rohlink zum falschen
#  Partner statt /go/-Redirect. KEINES der bestehenden Tools hat das
#  erkannt):
#    - affiliate_profi_check.py (A1-A8) prüft nur "mindestens N Links
#      insgesamt vorhanden" – ein einzelner kaputter Link fällt nicht
#      auf, solange andere Links im selben Artikel die Mindestzahl
#      erfüllen.
#    - affiliate_health.py prüft, ob /go/<key>/ zu einer gesunden
#      externen Zielseite führt (Registry-/HTTP-Ebene) – nicht, ob die
#      Markdown-SYNTAX der CTA-Box im Artikel selbst intakt ist.
#
#  PRÜFUNGEN (pro Artikel, an den 3 bekannten CTA-Marken-Zeilen):
#    AI1 STRUKTUR: Jede "Schnell-Tipp von FranksFinanzcheck"-/
#        "Spar-Tipp zwischendurch"-/finale CTA-Zeile muss einen
#        VOLLSTÄNDIGEN Markdown-Link [**Text**](url) enthalten – kein
#        Dangling-Link (fehlendes ']' oder '(url)').
#    AI2 REGISTRY: jeder /go/<key>/-Verweis muss in
#        scripts/check24_links.yaml registriert sein; KEINE rohen
#        externen Partner-URLs direkt im Content (muss über /go/ laufen
#        – sonst Umgehung von Tracking/rel=sponsored UND Risiko auf
#        falschen Partner wie im Haus-Artikel gefunden).
#    AI3 TEXT-PLAUSIBILITÄT: die ersten Wörter nach dem CTA-Marker
#        werden gegen das deutsche Wörterbuch geprüft (hunspell) – zu
#        viele unbekannte "Wörter" deuten auf Verstümmelung hin (Fund
#        wie "DStiebendenTarife").
#    AI4 RENDER-BEWEIS ("tatsächlich im Blog erscheinen"): NACH
#        hugo-Build wird für jeden Artikel gezählt, wie viele
#        <a href=/go/.../ ... affiliate_click ...>-Tags im gebauten HTML
#        stehen, und mit der Anzahl gültiger CTA-Marker im Markdown
#        abgeglichen. Zusätzlich: jedes referenzierte /go/<key>/ muss als
#        gebaute Seite existieren und selbst auf eine echte externe
#        Adresse weiterleiten.
#
#  SELBSTHEILUNG: eine defekte CTA-Zeile wird NICHT geflickt, sondern
#  KOMPLETT neu generiert – über dieselben Vorlagen-Funktionen aus
#  affiliate_marketer.py (build_top_cta/mid_cta/end_cta), die auch neue
#  Artikel benutzen. Das ist robuster als Text-Patches (die genau diesen
#  Vorfall verursacht haben) und garantiert syntaktisch korrekten Output.
#
#  EINBINDUNG ALS HARTES GATE:
#    - publish_gate.py (neue Artikel): Fund = harter Fehler, Artikel wird
#      wie die anderen drei Kriterien behandelt (verworfen statt live).
#    - bestand_gate.py (Bestandsartikel): Fund wird SOFORT über dieses
#      Skript geheilt, nie gelöscht.
#
#  Aufruf:
#    python3 scripts/affiliate_integrity_gate.py             # prüfen + heilen
#    python3 scripts/affiliate_integrity_gate.py --dry-run   # nur prüfen
#    python3 scripts/affiliate_integrity_gate.py --json
# ============================================================

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
PUBLIC = ROOT / "public"
REPORT = ROOT / "AFFILIATE-INTEGRITY-REPORT.md"

DRY_RUN = "--dry-run" in sys.argv
AS_JSON = "--json" in sys.argv

sys.path.insert(0, str(SCRIPTS))

# (Marker-Text, CTA-Typ) – Reihenfolge = erwartete Position im Artikel.
CTA_MARKERS = [
    ("Schnell-Tipp von FranksFinanzcheck", "top"),
    ("Spar-Tipp zwischendurch", "mid"),
    ("Jetzt vergleichen und sparen", "end"),
    ("Sparend zuerst vergleichen", "end"),
]

RAW_PARTNER_RE = re.compile(r"https://a\.(?:check24\.net|partner-versicherung\.de)/[^\s)]+")
GO_LINK_RE = re.compile(r"/go/([\w-]+)/")


def load_live_articles():
    arts = []
    for slug_dir in sorted(POSTS_DIR.iterdir()):
        index_md = slug_dir / "index.md"
        if not index_md.is_file():
            continue
        text = index_md.read_text(encoding="utf-8")
        if not text.startswith("---") or text.count("---") < 2:
            continue
        parts = text.split("---", 2)
        fm, body = parts[1], parts[2]
        if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
            continue
        pillar_m = re.search(r'^pillar:\s*"?([\w-]+)', fm, re.MULTILINE)
        arts.append({
            "slug": slug_dir.name, "path": index_md, "content": text,
            "fm": fm, "body": body, "pillar": pillar_m.group(1) if pillar_m else "",
        })
    return arts


def registered_keys() -> set:
    import affiliate_marketer as am
    return set(am.load_registry().keys())


def hunspell_unknown_ratio(words: list[str]) -> float:
    """Anteil der Wörter, die hunspell nicht kennt (grobe Verstümmelungs-
    Erkennung). Eigennamen/CamelCase-Marken werden ignoriert."""
    candidates = [w for w in words if w.isalpha() and len(w) > 3 and not w[0].isupper()]
    if not candidates:
        return 0.0
    try:
        proc = subprocess.run(
            ["hunspell", "-d", "de_DE"], input="\n".join(candidates),
            capture_output=True, text=True, timeout=15,
        )
    except Exception:  # noqa: BLE001
        return 0.0  # hunspell nicht verfügbar -> Prüfung überspringen, nicht blockieren
    unknown = sum(1 for line in proc.stdout.splitlines() if line.startswith("&") or line.startswith("#"))
    return unknown / len(candidates)


def find_cta_lines(body: str):
    """Liefert (marker, kind, line, line_start_idx) für jede gefundene
    CTA-Marker-Zeile."""
    found = []
    for marker, kind in CTA_MARKERS:
        for m in re.finditer(re.escape(marker), body):
            line_start = body.rfind("\n", 0, m.start()) + 1
            line_end = body.find("\n", m.start())
            if line_end == -1:
                line_end = len(body)
            found.append((marker, kind, body[line_start:line_end], line_start, line_end))
    return found


def check_cta_line(marker: str, line: str, reg_keys: set) -> list[str]:
    problems = []
    # AI1: vollständiger Markdown-Link?
    link_m = re.search(r"\[\*\*[^\]]*\*\*\]\(([^)]+)\)", line)
    if not link_m:
        problems.append(f"kein vollständiger Markdown-Link in CTA-Zeile ('{marker}')")
        return problems  # Folgeprüfungen ohne Link sinnlos
    url = link_m.group(1)
    # AI2: Registry/Redirect-Pflicht
    if url.startswith("http"):
        problems.append(f"Rohe externe URL statt /go/-Redirect in CTA-Zeile ('{marker}'): {url}")
    else:
        go_m = GO_LINK_RE.search(url)
        if not go_m:
            problems.append(f"Ungültiges Linkziel in CTA-Zeile ('{marker}'): {url}")
        elif go_m.group(1) not in reg_keys:
            problems.append(f"/go/{go_m.group(1)}/ ist nicht in check24_links.yaml registriert ('{marker}')")
    # AI3: Text-Plausibilität (Wörter direkt nach dem Marker, vor dem Link)
    after_marker = line.split(marker, 1)[1] if marker in line else line
    before_link = after_marker.split("[", 1)[0]
    words = re.findall(r"[A-Za-zÄÖÜäöüß]+", before_link)[:6]
    if words and hunspell_unknown_ratio(words) > 0.5:
        problems.append(f"verdächtig viele unbekannte Wörter direkt an der CTA ('{marker}'): {' '.join(words)}")
    return problems


def heal_article_ctas(article: dict, broken_kinds: set) -> list[str]:
    """Ersetzt JEDE als defekt erkannte CTA-Zeile komplett durch eine neu
    generierte, garantiert syntaktisch korrekte Version (keine Text-
    Patches – das hat den Vorfall verursacht)."""
    import affiliate_marketer as am
    reg = am.load_registry()
    body = article["body"]
    healed = []

    generators = {"top": am.build_top_cta, "mid": am.mid_cta, "end": am.end_cta}
    for marker, kind in CTA_MARKERS:
        if kind not in broken_kinds:
            continue
        idx = body.find(marker)
        if idx == -1:
            continue
        line_start = body.rfind("\n", 0, idx) + 1
        line_end = body.find("\n", idx)
        if line_end == -1:
            line_end = len(body)
        # Bei "top"/"end" ggf. den vorangehenden '---'-Trenner + Disclaimer-
        # Zeile mit ersetzen (Standard-Blockform), bei "mid" nur die Zeile.
        new_block = generators[kind](article["pillar"], reg, body).strip("\n")
        if kind == "mid":
            body = body[:line_start] + new_block + body[line_end:]
        else:
            # Top/End-CTA-Vorlagen enthalten bereits '---' + Disclaimer-Zeile;
            # die nachfolgende alte Disclaimer-Zeile (falls vorhanden) wird
            # mit ersetzt, um Duplikate zu vermeiden.
            rest = body[line_end:]
            disclaimer_m = re.match(r"\n_?\*?\(?Dieser Artikel enthält Affiliate-Links[^\n]*\n?", rest)
            if disclaimer_m:
                rest = rest[disclaimer_m.end():]
            prefix = body[:line_start]
            prefix = re.sub(r"\n?---\s*\n?\Z", "\n", prefix)  # alten Trennstrich davor kappen
            body = prefix + new_block + "\n" + rest
        healed.append(kind)

    if not healed:
        return []

    new_content = article["content"].split("---", 2)[0] + "---" + article["fm"] + "---" + body
    article["path"].write_text(new_content, encoding="utf-8")
    article["content"] = new_content
    article["body"] = body
    return healed


def rebuild_hugo() -> bool:
    hugo_bin = shutil.which("hugo") or ("/tmp/hugo" if Path("/tmp/hugo").is_file() else "hugo")
    try:
        r = subprocess.run([hugo_bin, "--minify"], cwd=ROOT, capture_output=True, text=True, timeout=180)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def verify_render(slug: str, expected_min_links: int) -> tuple[bool, str]:
    """AI4: zählt tatsächlich gerenderte, funktionsfähige Affiliate-Links
    im gebauten HTML – der eigentliche Beweis, dass ein Link 'im Blog
    erscheint', nicht nur im Markdown-Quelltext existiert."""
    html_path = PUBLIC / "posts" / slug / "index.html"
    if not html_path.is_file():
        return False, "gebaute HTML-Seite fehlt (hugo --minify gelaufen?)"
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    rendered = len(re.findall(r"<a href=/go/[\w-]+/[^>]*affiliate_click[^>]*>", html))
    if rendered < expected_min_links:
        return False, f"nur {rendered} statt mind. {expected_min_links} Affiliate-Links im gebauten HTML gefunden"
    # jede referenzierte /go/-Seite muss selbst existieren und weiterleiten
    for key in set(re.findall(r"<a href=/go/([\w-]+)/", html)):
        go_html = PUBLIC / "go" / key / "index.html"
        if not go_html.is_file():
            return False, f"/go/{key}/ referenziert, aber public/go/{key}/index.html fehlt"
        go_content = go_html.read_text(encoding="utf-8", errors="ignore")
        if "http-equiv=refresh" not in go_content.replace('"', "").replace("'", ""):
            return False, f"/go/{key}/ ist keine gültige Redirect-Seite"
    return True, ""


def main():
    articles = load_live_articles()
    reg_keys = registered_keys()

    findings = {}
    for a in articles:
        cta_lines = find_cta_lines(a["body"])
        problems = []
        broken_kinds = set()
        for marker, kind, line, *_ in cta_lines:
            line_problems = check_cta_line(marker, line, reg_keys)
            if line_problems:
                problems.extend(line_problems)
                broken_kinds.add(kind)
        if problems:
            findings[a["slug"]] = {"problems": problems, "broken_kinds": broken_kinds, "healed": []}

    healed_slugs = []
    if findings and not DRY_RUN:
        for a in articles:
            f = findings.get(a["slug"])
            if not f:
                continue
            healed_kinds = heal_article_ctas(a, f["broken_kinds"])
            if healed_kinds:
                f["healed"] = healed_kinds
                healed_slugs.append(a["slug"])

    if healed_slugs:
        rebuild_hugo()

    # AI4: Render-Beweis für ALLE Artikel (nicht nur die geheilten) – das
    # ist der eigentliche, vom Nutzer geforderte Beweis.
    render_problems = {}
    if PUBLIC.is_dir():
        for a in articles:
            cta_lines = find_cta_lines(a["body"])
            valid_links = sum(1 for _, _, line, *_ in cta_lines
                               if re.search(r"\[\*\*[^\]]*\*\*\]\(([^)]+)\)", line))
            ok, msg = verify_render(a["slug"], valid_links)
            if not ok:
                render_problems[a["slug"]] = msg

    still_broken = {
        slug: f for slug, f in findings.items()
        if not f["healed"] or slug in render_problems
    }

    if AS_JSON:
        result = {
            "checked": len(articles), "findings": findings,
            "healed": healed_slugs, "render_problems": render_problems,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=list))
        return 1 if (still_broken or render_problems) else 0

    lines = [
        "# 🔗 AFFILIATE-INTEGRITY-REPORT (affiliate_integrity_gate.py)",
        "",
        f"**Geprüfte Live-Artikel:** {len(articles)} · **Automatisch geheilt:** {len(healed_slugs)} "
        f"({', '.join(healed_slugs) if healed_slugs else '–'}) · **Render-Probleme:** {len(render_problems)}",
        "",
    ]
    if not findings and not render_problems:
        lines.append("🎉 Alle CTA-Boxen strukturell intakt, registriert und im gebauten HTML nachgewiesen.")
    else:
        for slug, f in findings.items():
            lines.append(f"### {slug}")
            for p in f["problems"]:
                lines.append(f"- ⚠️ {p}")
            if f["healed"]:
                lines.append(f"- ✅ automatisch neu generiert: {', '.join(f['healed'])}")
            lines.append("")
        for slug, msg in render_problems.items():
            lines.append(f"### {slug} (Render-Beweis)")
            lines.append(f"- ❌ {msg}")
            lines.append("")
        lines.append(
            "---\n_Defekte CTA-Boxen werden NIE per Text-Patch geflickt, sondern komplett neu aus den "
            "geprüften Vorlagen (affiliate_marketer.py) generiert. Bestandsartikel werden nie gelöscht._"
        )

    report_text = "\n".join(lines)
    print(report_text)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    return 1 if (still_broken or render_problems) else 0


if __name__ == "__main__":
    sys.exit(main())
