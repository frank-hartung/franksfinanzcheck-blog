#!/usr/bin/env python3
"""draft_link_healer.py – DRAFT-LINK-HEILER (Premium 26.08.2026)

DAUERAUFTRAG (Fehlerursache: defekte interne Links nach Kadenz-Heilung):
  Kadenz-Selbstheilung (cadence_guard --fix) stuft Verstöße auf draft +
  Re-Queue zurück. Ihre URLs verschwinden aus dem Build – aber die
  kontextuellen Links in andern (live) Artikeln zeigen weiterhin auf sie.
  Ergebnis: defekte interne Links im Live-Blog, rotes Qualitäts-Gate,
  offenes Issue, geschwächte Link-Struktur.

  DIESER HEILER LÖST DAS PROBLEM SYSTEMISCH (Safety-Net in der
  Deploy-Gate-Kette + Blog-Health-Wache + Content-Engine vor jedem Slot):
    - findet in JEDEM Artikel alle internen Post-Links
      (Formen: ../../posts/<slug>/  ·  /posts/<slug>/  ·
       https://(www.)franksfinanzcheck.de/posts/<slug>/  (+ UTM/Anker))
    - Ziel ist DRAFT, ZUKUNFTS-POST oder GELÖSCHT → Link wird zum
      Klartext (Ankertext bleibt 1:1 erhalten – nie Content-Verlust)
    - idempotent + konvergent: zweiter Lauf findet nichts mehr
    - wenn der Re-Queue-Post später wieder live geht, baut der
      internal_linker (seit Audit nur auf Live-Ziele) die Struktur wieder auf

ABSPERRUNG (Sabotage-Schutz): --selftest mit eingefrorenen Fällen;
Fehlschlag → Exit 2, nichts wird verändert.

AUFRUF:
  python3 scripts/draft_link_healer.py --check
  python3 scripts/draft_link_healer.py --fix
  python3 scripts/draft_link_healer.py --selftest
"""
import datetime
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths, slug_of          # noqa: E402

REPORT = os.path.join(BLOG_DIR, "DRAFT-LINK-REPORT.md")

# Alle drei Link-Formen auf Post-Ziele (Markdown-Links).
POST_LINK_RX = re.compile(
    r"\[([^\]]+)\]"                              # 1: Ankertext
    r"\(\s*"
    r"(?:"
    r"(?:\.\./)+posts/([a-z0-9\-]+)/?"           # 2: relativ
    r"|/posts/([a-z0-9\-]+)/?"                   # 3: absolut
    r"|https?://(?:www\.)?franksfinanzcheck\.de/posts/"
    r"([a-z0-9\-]+)/?(?:[?#][^)]*)?"             # 4: absolute URL
    r")\s*\)"
)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def load_posts_map():
    """slug → {path, draft, date, future} für ALLE Posts."""
    today = datetime.date.today().isoformat()
    posts = {}
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        slug = slug_of(path)
        c = re.search(r"^date:\s*[\"']?([0-9T:\-Z]+)", content, re.M)
        d_raw = (c.group(1) if c else "")[:10]
        posts[slug] = {
            "path": path,
            "draft": bool(re.search(r"^draft:\s*true\s*$", content, re.M)),
            "date": d_raw,
            "future": bool(d_raw) and d_raw > today,
        }
    return posts


def link_target_state(slug, posts):
    """(ok, begruendung) für ein Link-Ziel."""
    p = posts.get(slug)
    if p is None:
        return False, "Ziel existiert nicht (gelöscht)"
    if p["draft"]:
        return False, "Ziel ist Draft (Kadenz-Re-Queue)"
    if p["future"]:
        return False, f"Ziel ist Zukunfts-Post ({p['date']})"
    return True, "live"


def split_frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) == 3 and parts[0] == "":
        return parts[1], parts[2]
    return "", content


def heal_content(content, posts):
    """Entlinkt defekte Post-Ziele im BODY (Frontmatter bleibt unangetastet).
    Rückgabe: (neuer_content, count, [(target_slug, warum), ...])."""
    fm, body = split_frontmatter(content)
    count = 0
    details = []

    def repl(m):
        nonlocal count
        anchor = m.group(1)
        slug = next(g for g in m.groups()[1:] if g)
        ok, why = link_target_state(slug, posts)
        if not ok:
            count += 1
            details.append((slug, why))
            return anchor
        return m.group(0)

    new_body = POST_LINK_RX.sub(repl, body)
    new_content = ("---" + fm + "---" + new_body) if fm else new_body
    return new_content, count, details


def list_section_pages():
    """Sektions-/Pillar-/Rechtsseiten (content/**/_index.md und
    content/<section>/<page>/index.md) – KADENZ-UNABHÄNGIG, aber sie
    verlinken oft hart auf Posts (Cluster/Navigation) → müssen mitgeheilt
    werden, sonst 404 auf Listen-/Pillar-Seiten."""
    content_dir = os.path.join(BLOG_DIR, "content")
    out = []
    for base, _dirs, files in os.walk(content_dir):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(base, fn)
            rel = os.path.relpath(path, content_dir)
            # Einzelartikel auslassen: posts/<slug>/index.md (3 Teile) und
            # Legacy posts/<slug>.md (2 Teile, ohne "_" im Namen) – die
            # laufen über list_post_paths(). posts/_index.md (Sektions-Intro,
            # enthält oft harte Post-Links) BLEIBT dabei.
            parts = rel.replace(os.sep, "/").split("/")
            if parts[0] == "posts":
                if len(parts) == 3:
                    continue
                if len(parts) == 2 and not parts[1].startswith("_"):
                    continue
            out.append(path)
    return sorted(out)


def scan(do_fix, dry_run=False):
    """Alle Posts + Sektions-/Pillar-Seiten prüfen (und mit --fix heilen).
    Rückgabe: (findings, healed) – findings = [(own, target, warum)]."""
    posts = load_posts_map()
    findings = []
    healed = []

    def process(path, own, is_post):
        nonlocal findings, healed
        content = open(path, encoding="utf-8").read()
        new_content, count, details = heal_content(content, posts)
        if not count:
            return
        if do_fix and not dry_run:
            open(path, "w", encoding="utf-8").write(new_content)
        tag = ""
        if is_post:
            own_p = posts.get(own) or {}
            if own_p.get("draft") or own_p.get("future"):
                tag = " (draft)"
        healed.append(f"{own}{tag}: {count} defekte Link(s) entlinkt")
        findings += [(own, s, w) for s, w in details]

    for path in sorted(list_post_paths()):
        process(path, slug_of(path), True)
    for path in list_section_pages():
        label = os.path.relpath(path, os.path.join(BLOG_DIR, "content"))
        process(path, label, False)
    return findings, healed


def write_report(findings, healed, mode):
    now = now_utc().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 🔗 DRAFT-LINK-REPORT (draft_link_healer.py)",
        "",
        f"**Stand:** {now} · Modus: {mode}",
        "",
    ]
    if findings:
        lines += [f"## Defekte interne Links ({len(findings)})", ""]
        for own, target, why in findings:
            lines.append(f"- `{own}` → `{target}` ({why})")
        lines.append("")
    else:
        lines += ["## Bestand", "",
                  "✅ Keine defekten internen Post-Links – alle Ziele live.",
                  ""]
    if healed:
        lines += ["## Geheilt (dieser Lauf)", ""]
        lines += [f"- ✅ {h}" for h in healed]
        lines.append("")
    lines += ["---",
              "_Heiler: Ankertext bleibt 1:1 erhalten (kein Content-Verlust). "
              "Läuft in der Deploy-Gate-Kette vor dem Hugo-Build, in der "
              "Content-Engine vor jedem Slot und im Blog-Gesundheits-Check._"]
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def run_selftest():
    """Eingefrorene Fälle in einem isolierten Temp-Blog. Fehlschlag → Exit 2."""
    import tempfile
    global list_post_paths, list_section_pages
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(("  ✓ " if cond else "  ✗ ") + name)

    tmp = tempfile.mkdtemp(prefix="draft_link_healer_selftest_")
    saved_list = list_post_paths
    saved_sections = list_section_pages
    posts_dir = os.path.join(tmp, "posts")
    os.makedirs(posts_dir, exist_ok=True)

    def make(slug, draft=False, date="2026-08-24", body=""):
        d = os.path.join(posts_dir, slug)
        os.makedirs(d, exist_ok=True)
        fm = (f'---\ntitle: "Test {slug}"\n'
              f'date: "{date} 08:00:00 +0200"\n'
              f'draft: {"true" if draft else "false"}\n---\n')
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as f:
            f.write(fm + (body or "Inhalt."))

    make("live-a", body="Link zu [Ziel B](../../posts/draft-b/) und "
                        "[Ziel C](../../posts/future-c/) und "
                        "[Ziel D](../../posts/geloescht-d/) und "
                        "[Ziel E](https://www.franksfinanzcheck.de/"
                        "posts/live-e/?utm_source=x) und "
                        "[Ziel F](/posts/live-f/).")
    make("live-f")
    make("live-e")
    make("draft-b", draft=True)
    make("future-c", date="2999-01-01")
    # geloescht-d existiert nicht

    list_post_paths = lambda: sorted(          # noqa: E731
        [os.path.join(posts_dir, s, "index.md")
         for s in ("live-a", "live-e", "live-f", "draft-b", "future-c")])
    list_section_pages = lambda: []            # noqa: E731 (Isolation!)
    try:
        # CHECK findet alle toten Ziele, behält live-Ziele
        findings, _ = scan(do_fix=False)
        targets = {t for _o, t, _w in findings}
        check("check findet draft-/future-/gelöschte Ziele",
              targets == {"draft-b", "future-c", "geloescht-d"})
        check("check behält live-Ziele (absolut-e, live-f)",
              not (targets & {"absolut-e", "live-f"}))
        # FIX heilt
        _f, healed = scan(do_fix=True)
        a = open(os.path.join(posts_dir, "live-a", "index.md"),
                 encoding="utf-8").read()
        check("fix entlinkt draft-/future-/gelöschte Ziele",
              all(f"posts/{s}/" not in a for s in
                  ("draft-b", "future-c", "geloescht-d")))
        check("fix behält live-Ziele als Links",
              "posts/live-e/" in a and "posts/live-f/" in a)
        check("fix erhält Ankertexte (Ziel B, C, D)",
              "Ziel B" in a and "Ziel C" in a and "Ziel D" in a)
        # Idempotenz: zweiter Lauf findet nichts mehr
        findings2, _ = scan(do_fix=False)
        check("idempotent: zweiter Lauf findet nichts", not findings2)
    finally:
        list_post_paths = saved_list
        list_section_pages = saved_sections
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [n for n, ok in results if not ok]
    if failed:
        print(f"🛑 DRAFT-LINK-SELFTEST FEHLGESCHLAGEN ({len(failed)}): {failed}")
        return 2
    print(f"✅ DRAFT-LINK-SELFTEST bestanden ({len(results)} Fälle).")
    return 0


def main():
    do_fix = "--fix" in sys.argv
    if "--selftest" in sys.argv:
        return run_selftest()
    mode = "FIX" if do_fix else "CHECK"
    findings, healed = scan(do_fix=do_fix)
    write_report(findings, healed, mode)
    if do_fix:
        print(f"Draft-Link-Heiler: {len(findings)} defekte Links in "
              f"{len(healed)} Artikeln – geheilt "
              f"(Ankertexte erhalten).")
    else:
        print(f"Draft-Link-Heiler: {len(findings)} defekte interne Links "
              f"gefunden (Details: DRAFT-LINK-REPORT.md).")
    return 1 if findings and not do_fix else 0


if __name__ == "__main__":
    sys.exit(main())
