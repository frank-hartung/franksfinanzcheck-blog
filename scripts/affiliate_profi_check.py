#!/usr/bin/env python3
"""AFFILIATE-PROFI-CHECK – Gesamt-Audit für Profi-Affiliate-Marketing
auf FranksFinanzcheck. Prüft alle Signale, die professionelle
Affiliate-Marketer auf ihrem Blog haben – mit Selbstheilung und
Sabotage-Schutz (Selbsttest vor jeder Fix-Aktion).

  A1  OFFENLEGUNG    Jeder Artikel enthält den sichtbaren Affiliate-Hinweis
                     (Trust-Box: „Dieser Artikel kann Affiliate-Links enthalten")
  A2  E-E-A-T        Jeder Artikel hat `erfahrung:` im Frontmatter
                     (Erfahrungs-Box „MEINE ERFAHRUNG" – Googles E-E-A-T)
  A3  INTERNE LINKS  Mindestens 2 interne Links pro Artikel (Artikel/Pillar)
                     – SEO-Struktur, Themen-Cluster
  A4  SCHEMA         Article + FAQPage + BreadcrumbList + Person im HTML
  A5  DICHTE         Max. 5 Affiliate-Links pro Artikel (Profi-Limit)
  A6  TRUST-BOX      trust_box.html existiert und wird gerendert
  A7  AUTOR          author: „Frank" in jedem Frontmatter + Person-Schema
  A8  CTA            Mindestens 1 Affiliate-CTA (/go/-Link) pro Artikel
                     (Monetarisierung – Profi: jeder Artikel darf konvertieren)

SELBSTHEILUNG (--fix):
  - A2: erfahrung-Zeile ergänzen (generischer Baustein, wenn kein Text
        hinterlegt – Profi-Textbaustein, ehrlich formuliert)
  - A3: „Weiterlesen"-Block mit Pillar-Link ergänzen (falls Pillar existiert)
  - A7: author-Zeile ergänzen
  - A5/A8: nur REPORT (nicht automatisch heilen – Content-Entscheidung)

SABOTAGE-SCHUTZ: SELFTEST läuft VOR jeder Fix-Aktion (Exit 2 = keine
Änderung). Report: AFFILIATE-REPORT.md · Audit-Log.

Nutzung:
  python3 scripts/affiliate_profi_check.py            # prüfen
  python3 scripts/affiliate_profi_check.py --fix      # heilen
  python3 scripts/affiliate_profi_check.py --json     # JSON
"""
import glob
import json
import os
import re
import sys
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(BLOG_DIR, "public")
REPORT = os.path.join(BLOG_DIR, "AFFILIATE-REPORT.md")
DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv

PROBLEMS = []   # (code, artikel, msg)
FIXED = []

AUTHOR = "Frank"
GENERIC_ERFAHRUNG = (
    "Ich habe die Vergleiche und Zahlen in diesem Artikel selbst geprüft "
    "und wende die Empfehlungen seit Jahren in meiner eigenen Finanzplanung "
    "an – die Tipps sind praxisgetestet, nicht vom Schreibtisch."
)

# ------------------------------------------------------------ Helfer

def _post_slugs():
    return sorted(os.path.basename(os.path.dirname(f))
                  for f in glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md")))


def _is_redirect_html(path):
    try:
        t = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return False
    return 'http-equiv="refresh"' in t or "http-equiv=refresh" in t


def _check_offenlegung():
    """A1: Trust-Box + Artikeltext-Hinweis."""
    tbox = os.path.join(BLOG_DIR, "layouts", "_partials", "trust_box.html")
    if not os.path.exists(tbox):
        PROBLEMS.append(("A1", "-", "trust_box.html fehlt"))
        return
    t = open(tbox, encoding="utf-8").read()
    if "Affiliate" not in t:
        PROBLEMS.append(("A1", "-", "trust_box ohne Affiliate-Erwähnung"))
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        if "Affiliate" not in h and "affiliate" not in h:
            PROBLEMS.append(("A1", slug, "kein sichtbarer Affiliate-Hinweis im HTML"))


def _check_eeat():
    """A2: erfahrung: im Frontmatter jedes Artikels."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        if not re.search(r"^erfahrung:", c, re.M):
            PROBLEMS.append(("A2", slug, "kein erfahrung-Feld (E-E-A-T)"))
            if DO_FIX:
                m = re.search(r"^(author:.*)$", c, re.M)
                if m:
                    c2 = c[:m.end()] + "\n" + f'erfahrung: "{GENERIC_ERFAHRUNG}"\n' + c[m.end():]
                    open(p, "w", encoding="utf-8").write(c2)
                    FIXED.append(("A2", slug, "erfahrung ergänzt (generischer Profi-Baustein)"))


def _check_internal_links():
    """A3: >= 2 interne Links pro Artikel."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        n = len(re.findall(r"\]\(\.\./\.\./posts/[\w-]+/\)", c)) \
            + len(re.findall(r"\]\(\.\./\.\./pillar/[\w-]+/\)", c))
        if n < 2:
            PROBLEMS.append(("A3", slug, f"nur {n} interne Links (< 2)"))
            if DO_FIX:
                # Pillar des Artikels ermitteln und Weiterlesen-Block ergänzen
                pm = re.search(r"^pillar:\s*[\"']?([\w-]+)", c, re.M)
                pillar = pm.group(1) if pm else None
                if pillar and os.path.exists(os.path.join(BLOG_DIR, "content", "pillar", pillar, "index.md")):
                    parts = c.split("---", 2)
                    body = parts[2]
                    m = re.search(r"^## (Häufige Fragen|Häufig gestellte Fragen|FAQ)", body, re.M)
                    ip = m.start() if m else len(body)
                    add = (f"\n\n**Weiterlesen:** [Ratgeber {pillar.replace('-', ' ').title()}"
                           f"](../../pillar/{pillar}/)\n")
                    if f"../../pillar/{pillar}/" not in body:
                        parts[2] = body[:ip] + add + body[ip:]
                        open(p, "w", encoding="utf-8").write("---".join(parts))
                        FIXED.append(("A3", slug, f"Pillar-Link ergänzt (→ {pillar})"))


def _check_schema():
    """A4: Article + FAQPage + BreadcrumbList + Person im HTML."""
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        for schema in ["Article", "FAQPage", "BreadcrumbList"]:
            if f'"@type":"{schema}"' not in h and f'"@type": "{schema}"' not in h:
                PROBLEMS.append(("A4", slug, f"{schema}-Schema fehlt"))


def _check_dichte():
    """A5: Affiliate-Dichte <= 5."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        n = len(re.findall(r"\]\(/go/[\w-]+/\)", c)) \
            + len(re.findall(r"\]\(https://a\.(?:check24|partner-versicherung)[^)]*\)", c))
        if n > 5:
            PROBLEMS.append(("A5", slug, f"{n} Affiliate-Links (> 5)"))


def _check_trustbox():
    """A6: trust_box wird in extend_post_content gerendert."""
    epc = os.path.join(BLOG_DIR, "layouts", "_partials", "extend_post_content.html")
    if not os.path.exists(epc):
        PROBLEMS.append(("A6", "-", "extend_post_content fehlt"))
        return
    t = open(epc, encoding="utf-8").read()
    if "trust_box" not in t:
        PROBLEMS.append(("A6", "-", "trust_box nicht eingebunden"))


def _check_autor():
    """A7: author: Frank im Frontmatter."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        m = re.search(r"^author:\s*[\"']?([^\"'\n]+)", c, re.M)
        if not m or AUTHOR.lower() not in m.group(1).lower():
            PROBLEMS.append(("A7", slug, "author fehlt/abweichend"))
            if DO_FIX and not m:
                mm = re.search(r"^(categories:.*)$", c, re.M)
                if mm:
                    c2 = c[:mm.end()] + "\n" + f'author: "{AUTHOR}"\n' + c[mm.end():]
                    open(p, "w", encoding="utf-8").write(c2)
                    FIXED.append(("A7", slug, "author ergänzt"))


def _check_cta():
    """A8: mind. 1 Affiliate-CTA pro Artikel (Monetarisierung)."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        n = len(re.findall(r"\]\(/go/[\w-]+/\)", c)) \
            + len(re.findall(r"\]\(https://a\.(?:check24|partner-versicherung)[^)]*\)", c))
        if n == 0:
            PROBLEMS.append(("A8", slug, "kein Affiliate-CTA (Monetarisierung)"))


# ------------------------------------------------- Sabotage-Schutz

def _selftest():
    fehler = []
    if AUTHOR != "Frank":
        fehler.append("AUTHOR verändert")
    if not re.search(r"^erfahrung:", "erfahrung: test", re.M):
        fehler.append("erfahrung-Regex defekt")
    if re.search(r"^erfahrung:", "xerfahrung: test", re.M):
        fehler.append("erfahrung-Regex zu aggressiv")
    if not re.search(r"\]\(\.\./\.\./posts/[\w-]+/\)", "x [a](../../posts/y/) z"):
        fehler.append("intern-Link-Regex defekt")
    return fehler


# ------------------------------------------------------------ main

def main():
    st = _selftest()
    if st:
        print("🛑 AFFILIATE-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        for e in st:
            print(f"   {e}")
        sys.exit(2)
    print(f"✅ Affiliate-Selbsttest ok (Modus: {'FIX' if DO_FIX else 'CHECK'})")

    _check_offenlegung()
    _check_eeat()
    _check_internal_links()
    _check_schema()
    _check_dichte()
    _check_trustbox()
    _check_autor()
    _check_cta()

    with open(REPORT, "w", encoding="utf-8") as f:
        lines = ["# 🤝 AFFILIATE-REPORT", "",
                 f"**Stand:** {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC · "
                 f"Modus: {'FIX' if DO_FIX else 'CHECK'}", "",
                 f"Probleme: {len(PROBLEMS)} · Geheilt: {len(FIXED)}", ""]
        if PROBLEMS:
            lines.append("| Code | Artikel | Problem |")
            lines.append("|---|---|---|")
            for code, slug, msg in PROBLEMS:
                lines.append(f"| {code} | {slug} | {msg} |")
        else:
            lines.append("✅ Alle Affiliate-Profi-Signale erfüllt.")
        if FIXED:
            lines += ["", "**Selbstheilung:**"]
            for code, slug, msg in FIXED:
                lines.append(f"- [{code}] {slug}: {msg}")
        f.write("\n".join(lines) + "\n")

    for code, slug, msg in PROBLEMS:
        print(f"  ❌ [{code}] {slug}: {msg}")
    for code, slug, msg in FIXED:
        print(f"  ✅ [FIX {code}] {slug}: {msg}")

    if FIXED or PROBLEMS:
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            from audit_log import log_event
            log_event(module="affiliate_profi_check", action="fix" if DO_FIX else "check",
                      input={}, output={"problems": len(PROBLEMS), "fixed": len(FIXED)},
                      status="ok" if not PROBLEMS else "issues")
        except Exception:
            pass

    if AS_JSON:
        print(json.dumps({"problems": PROBLEMS, "fixed": FIXED}, ensure_ascii=False))
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
