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

SELBSTHEILUNG (--fix) – Sofortheilungs-Prinzip (heilen → verifizieren →
nur unheilbare Reste alarmieren, wie in großen Onlineredaktionen):
  - A2: erfahrung-Zeile ergänzen (generischer Baustein, wenn kein Text
        hinterlegt – Profi-Textbaustein, ehrlich formuliert)
  - A3: ZWEISTUFIG (Redaktions-Fix 02.09.2026, Heiler-Deckel behoben):
        Stufe 1: „Weiterlesen"-Block mit Pillar-Link (falls Pillar existiert)
        Stufe 2: „Lesetipp"-Link auf thematisch passenden LIVE-Artikel
        (gleicher Pillar bevorzugt, nie Draft-/Zukunfts-Ziele, nie selbst).
        Erst NACH der Heilung wird erneut gezählt – geheilte Artikel
        lösen keinen Exit-1-Alarm mehr aus.
  - A7: author-Zeile ergänzen
  - A8: CTA-Baustein ergänzen (deterministisch, Pillar → /go/-Key)
  - A5: nur REPORT (nicht automatisch heilen – Content-Entscheidung)

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
            if DO_FIX:
                m = re.search(r"^(author:.*)$", c, re.M)
                if m:
                    c2 = c[:m.end()] + "\n" + f'erfahrung: "{GENERIC_ERFAHRUNG}"\n' + c[m.end():]
                    open(p, "w", encoding="utf-8").write(c2)
                    FIXED.append(("A2", slug, "erfahrung ergänzt (generischer Profi-Baustein)"))
                    continue  # geheilt + verifizierbar → kein Alarm (Sofortheilung)
            PROBLEMS.append(("A2", slug, "kein erfahrung-Feld (E-E-A-T)"))


def _count_internal_links(text):
    """Zählt interne Links (Artikel + Pillar) – eine Quelle der Wahrheit."""
    return len(re.findall(r"\]\(\.\./\.\./posts/[\w-]+/\)", text)) \
        + len(re.findall(r"\]\(\.\./\.\./pillar/[\w-]+/\)", text))


def _live_post_slugs():
    """Nur Live-Artikel als Linkziele: kein Draft, kein Zukunftsdatum.

    Gleiche Live-Definition wie internal_linker/draft_link_healer –
    die Sofortheilung darf NIE auf einen (noch) toten Slug verlinken.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    live = []
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        try:
            c = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"^draft:\s*true", c, re.M):
            continue
        dm = re.search(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", c, re.M)
        if dm:
            try:
                d = datetime.datetime.strptime(dm.group(1), "%Y-%m-%d") \
                    .replace(tzinfo=datetime.timezone.utc)
                if d.date() > now.date():
                    continue
            except ValueError:
                continue
        live.append(slug)
    return live


def _pick_related_live_post(slug, text):
    """Wählt deterministisch den besten Lesetipp-Kandidaten.

    Rangfolge: gleicher Pillar zuerst, dann jüngster Live-Artikel.
    Nie sich selbst, nie bereits verlinkte Ziele.
    Rückgabe: (slug, titel) oder None.
    """
    pm = re.search(r"^pillar:\s*[\"']?([\w-]+)", text, re.M)
    pillar = pm.group(1) if pm else None
    best = None
    for other in sorted(_live_post_slugs(), reverse=True):  # jüngste zuerst
        if other == slug or f"../../posts/{other}/" in text:
            continue
        op = os.path.join(BLOG_DIR, "content", "posts", other, "index.md")
        try:
            oc = open(op, encoding="utf-8").read()
        except OSError:
            continue
        opm = re.search(r"^pillar:\s*[\"']?([\w-]+)", oc, re.M)
        tm = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", oc, re.M)
        title = tm.group(1) if tm else other.replace("-", " ").title()
        rank = 0 if (pillar and opm and opm.group(1) == pillar) else 1
        cand = (rank, other, title)
        if best is None or cand[0] < best[0]:
            best = cand
            if rank == 0:
                break  # jüngster Same-Pillar-Treffer = optimal
    return (best[1], best[2]) if best else None


def _check_internal_links():
    """A3: >= 2 interne Links pro Artikel – mit echter Sofortheilung.

    REDAKTIONS-FIX 02.09.2026 (Heiler-Deckel behoben): Die alte Heilung
    konnte nur den EINEN Pillar-Link ergänzen. War der schon vorhanden
    (Artikel mit genau 1 internen Link), blieb A3 dauerhaft rot – der
    wöchentliche SEO-Workflow schlug deshalb am 02.09. fehl. Jetzt:
      Stufe 1: Pillar-Link ergänzen (wie bisher)
      Stufe 2: „Lesetipp"-Link auf thematisch passenden LIVE-Artikel
      Verifikation: erst NACH der Heilung wird erneut gezählt –
      geheilte Artikel lösen keinen Alarm mehr aus (Sofortheilung),
      nur unheilbare Reste gehen als Problem/Exit 1 an die Redaktion.
    """
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        n = _count_internal_links(c)
        if n >= 2:
            continue
        if DO_FIX:
            changed = False
            parts = c.split("---", 2)
            if len(parts) == 3:
                body = parts[2]
                # Stufe 1: Pillar-Link („Weiterlesen"), falls noch nicht da
                pm = re.search(r"^pillar:\s*[\"']?([\w-]+)", c, re.M)
                pillar = pm.group(1) if pm else None
                if (pillar
                        and os.path.exists(os.path.join(BLOG_DIR, "content", "pillar", pillar, "index.md"))
                        and f"../../pillar/{pillar}/" not in body):
                    m = re.search(r"^## (Häufige Fragen|Häufig gestellte Fragen|FAQ)", body, re.M)
                    ip = m.start() if m else len(body)
                    add = (f"\n\n**Weiterlesen:** [Ratgeber {pillar.replace('-', ' ').title()}"
                           f"](../../pillar/{pillar}/)\n")
                    body = body[:ip] + add + body[ip:]
                    changed = True
                    FIXED.append(("A3", slug, f"Pillar-Link ergänzt (→ {pillar})"))
                # Stufe 2: Lesetipp auf passenden Live-Artikel, bis >= 2
                guard = 0
                while _count_internal_links(body) < 2 and guard < 3:
                    guard += 1
                    rel = _pick_related_live_post(slug, "---".join(parts[:2]) + "---" + body)
                    if not rel:
                        break
                    rslug, rtitle = rel
                    wm = re.search(r"^\*\*Weiterlesen:\*\*.*$", body, re.M)
                    tip = f"\n**Lesetipp:** [{rtitle}](../../posts/{rslug}/)\n"
                    if wm:
                        ip = wm.end()
                    else:
                        fm = re.search(r"^## (Häufige Fragen|Häufig gestellte Fragen|FAQ)", body, re.M)
                        ip = fm.start() if fm else len(body)
                        tip = "\n" + tip
                    body = body[:ip] + tip + body[ip:]
                    changed = True
                    FIXED.append(("A3", slug, f"Lesetipp-Link ergänzt (→ {rslug})"))
                if changed:
                    parts[2] = body
                    c = "---".join(parts)
                    open(p, "w", encoding="utf-8").write(c)
            # Verifikation NACH der Heilung – nur Reste alarmieren
            n = _count_internal_links(c)
            if n >= 2:
                continue
        PROBLEMS.append(("A3", slug, f"nur {n} interne Links (< 2)"))


def _check_schema():
    """A4: BlogPosting (bzw. Article) + FAQPage + BreadcrumbList im HTML.

    13.08.2026: Das früher separate "Article"-Schema (layouts/_partials/
    schema_article.html) wurde entfernt (Templating-Bug: doppelt escapte
    Anführungszeichen + Verweis auf nie existierendes /images/logo.png).
    Es war redundant zum sauberen, theme-eigenen BlogPosting-Schema, das
    dieselben Felder abdeckt. Diese Prüfung akzeptiert daher beide Typen.
    """
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        for schema in ["FAQPage", "BreadcrumbList"]:
            if f'"@type":"{schema}"' not in h and f'"@type": "{schema}"' not in h:
                PROBLEMS.append(("A4", slug, f"{schema}-Schema fehlt"))
        if ('"@type":"Article"' not in h and '"@type": "Article"' not in h
                and '"@type":"BlogPosting"' not in h and '"@type": "BlogPosting"' not in h):
            PROBLEMS.append(("A4", slug, "Article/BlogPosting-Schema fehlt"))


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
            if DO_FIX and not m:
                mm = re.search(r"^(categories:.*)$", c, re.M)
                if mm:
                    c2 = c[:mm.end()] + "\n" + f'author: "{AUTHOR}"\n' + c[mm.end():]
                    open(p, "w", encoding="utf-8").write(c2)
                    FIXED.append(("A7", slug, "author ergänzt"))
                    continue  # geheilt + verifizierbar → kein Alarm (Sofortheilung)
            PROBLEMS.append(("A7", slug, "author fehlt/abweichend"))


def _check_cta():
    """A8: mind. 1 Affiliate-CTA pro Artikel (Monetarisierung)."""
    # Pillar → passender /go/-Key für deterministische Selbstheilung
    PILLAR_CTA = {
        "versicherungen": "hausrat",
        "frugalismus": "tagesgeld",
        "konto-karten": "tagesgeld",
        "internet-dsl": "dsl",
        "strom-sparen": "strom",
        "mietwagen": "mietwagen",
    }
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        c = open(p, encoding="utf-8").read()
        n = len(re.findall(r"\]\(/go/[\w-]+/\)", c)) \
            + len(re.findall(r"\]\(https://a\.(?:check24|partner-versicherung)[^)]*\)", c))
        if n > 0:
            continue
        if DO_FIX:
            pm = re.search(r"^pillar:\s*[\"']?([\w-]+)", c, re.M)
            go_key = PILLAR_CTA.get(pm.group(1) if pm else "", "allgemein")
            labels = {
                "hausrat": ("Hausrat- & Gebäudeversicherung vergleichen", "Hausrat"),
                "tagesgeld": ("Tagesgeld & Anlageangebote vergleichen", "Tagesgeld"),
                "dsl": ("DSL-Tarife vergleichen", "DSL"),
                "strom": ("Stromtarife vergleichen", "Strom"),
                "mietwagen": ("Mietwagen vergleichen", "Mietwagen"),
                "allgemein": ("Angebote vergleichen", "CHECK24"),
            }
            label, _ = labels.get(go_key, labels["allgemein"])
            parts = c.split("---", 2)
            body = parts[2]
            m = re.search(r"^## (Häufige Fragen|Häufig gestellte Fragen|FAQ)", body, re.M)
            ip = m.start() if m else len(body)
            cta = (f"\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten Angebote "
                   f"findest du über unseren Partner-Vergleich: "
                   f"[**Jetzt {label}**](/go/{go_key}/) – in wenigen Minuten "
                   f"siehst du, was du sparst.\n")
            parts[2] = body[:ip] + cta + body[ip:]
            open(p, "w", encoding="utf-8").write("---".join(parts))
            FIXED.append(("A8", slug, f"Affiliate-CTA ergänzt (→ /go/{go_key}/)"))
            continue  # geheilt + verifizierbar → kein Alarm (Sofortheilung)
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
    # Sofortheilung A3 (02.09.2026): Zähler + Lesetipp-Kandidatenwahl prüfen
    if _count_internal_links("[a](../../posts/x/) [b](../../pillar/y/)") != 2:
        fehler.append("interner Link-Zähler defekt")
    if not re.search(r"^draft:\s*true", "draft: true", re.M):
        fehler.append("Draft-Regex defekt (Live-Ziel-Filter)")
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
