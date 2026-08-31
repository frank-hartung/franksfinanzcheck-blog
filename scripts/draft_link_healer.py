#!/usr/bin/env python3
"""draft_link_healer.py – DRAFT-LINK-HEILER (Premium 26.08.2026)

DAUERAUFTRAG (Fehlerursache: defekte interne Links nach Kadenz-Heilung):
  Kadenz-Selbstheilung (cadence_guard --fix) stuft Verstöße auf draft +
  Re-Queue zurück. Ihre URLs verschwinden aus dem Build – aber die
  kontextuellen Links in andern (live) Artikeln zeigen weiterhin auf sie.
  Ergebnis: defekte interne Links im Live-Blog, rotes Qualitäts-Gate,
  offenes Issue, geschwächte Link-Struktur.

ZWEI EBNEN (Arbeitsteilung seit Issue #129, 31.08.2026):
  1) RENDERING (verlustfrei, immer aktuell):
     layouts/_default/_markup/render-link.html erkennt Links auf Seiten, die
     Hugo gerade NICHT baut (draft · Zukunfts-Zeitstempel · abgelaufen ·
     gelöscht) und gibt den Ankertext als Klartext aus. Der Link lebt
     automatisch wieder auf, sobald das Ziel zurück im Build ist.
  2) DIESER HEILER (Inhalts-Ebene):
     - findet in JEDEM Artikel alle internen Post-Links
       (Formen: ../../posts/<slug>/  ·  /posts/<slug>/  ·
        https://(www.)franksfinanzcheck.de/posts/<slug>/  (+ UTM/Anker))
     - Ziel GELÖSCHT (Datei existiert nicht) → Link wird zum Klartext
       (Ankertext bleibt 1:1 erhalten – nie Content-Verlust)
     - Ziel nur VORÜBERGEHEND nicht im Build (Draft/Zukunft/Ablauf) →
       wird NUR GEMELDET, nicht mehr entlinkt: Ebene 1) schützt den
       Live-Blog, und kuratierte Listen (z. B. „Cluster-Reihenfolge" in
       content/pillar/) bleiben dauerhaft intakt statt bei jedem
       Kadenz-Hin-und-Her Links zu verlieren.
     - --strict stellt das alte Verhalten wieder her (auch Draft-/
       Zukunfts-Ziele entlinken) – für den Notfall.
     - idempotent + konvergent: zweiter Lauf findet nichts mehr zum Heilen
     - „Zukunfts-Post" wird ZEITSTEMPEL-genau beurteilt (post_utils.
       build_state) – wie Hugo es tut. Die alte Tag-Genauigkeit ließ einen
       am selben Tag später terminierten Post „live" erscheinen, obwohl der
       Build ihn nicht erzeugte (→ genau der #129-Nachfall vom 31.08.).

ABSPERRUNG (Sabotage-Schutz): --selftest mit eingefrorenen Fällen;
Fehlschlag → Exit 2, nichts wird verändert.

AUFRUF:
  python3 scripts/draft_link_healer.py --check
  python3 scripts/draft_link_healer.py --fix
  python3 scripts/draft_link_healer.py --fix --strict
  python3 scripts/draft_link_healer.py --selftest
"""
import datetime
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import build_state, list_post_paths, slug_of  # noqa: E402

REPORT = os.path.join(BLOG_DIR, "DRAFT-LINK-REPORT.md")

# Alle drei Link-Formen auf Post-Ziele (Markdown-Links).
POST_LINK_RX = re.compile(
    r"\[([^\]]+)\]"                              # 1: Ankertext
    r"\(\s*"
    r"(?:"
    r"(?:\.\./)+posts/([a-z0-9\-]+)/?"             # 2: relativ
    r"|/posts/([a-z0-9\-]+)/?"                    # 4: absolut
    r"|https?://(?:www\.)?franksfinanzcheck\.de/posts/"
    r"([a-z0-9\-]+)/?(?:[?#][^)]*)?"              # 5: absolute URL
    r")\s*\)"
)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def load_posts_map(now=None):
    """slug → {path, draft, date, future, ok, grund} für ALLE Posts.

    `ok`/`grund` kommen aus post_utils.build_state() und damit exakt nach
    den Hugo-Gates (buildDrafts/buildFuture/buildExpired = false)."""
    posts = {}
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        slug = slug_of(path)
        ok, grund = build_state(content, now=now)
        c = re.search(r"^date:\s*[\"']?([0-9T:\-Z]+)", content, re.M)
        posts[slug] = {
            "path": path,
            "ok": ok,
            "grund": grund,
            "draft": bool(re.search(r"^draft:\s*true\s*$", content, re.M)),
            "date": (c.group(1) if c else "")[:10],
            "future": bool(ok is False and grund.startswith("Zukunfts-Post")),
        }
    return posts


def link_target_state(slug, posts):
    """(ok, begruendung, klassifikation) für ein Link-Ziel.

    Klassifikation: "live" | "transient" (Ziel existiert, ist aber gerade
    nicht im Build → Render-Guard grifft, kein Eingriff nötig) |
    "missing" (Ziel weg → Inhalt muss repariert werden)."""
    p = posts.get(slug)
    if p is None:
        return False, "Ziel existiert nicht (gelöscht)", "missing"
    if p["ok"]:
        return True, "live", "live"
    return False, p["grund"], "transient"


def split_frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) == 3 and parts[0] == "":
        return parts[1], parts[2]
    return "", content


def heal_content(content, posts, unlink_transient=False):
    """Entlinkt Post-Ziele, die nicht im Build sind (BODY – Frontmatter bleibt
    unangetastet). Ohne `unlink_transient` nur bei GELÖSCHTEN Zielen;
    vorübergehend fehlende (Draft/Zukunft/Ablauf) bleiben als Link stehen und
    werden vom Render-Guard in layouts/_default/_markup/render-link.html
    zur Laufzeit zu Klartext – verlustfrei und selbstreparierend.

    Rückgabe: (neuer_content, geaendert, [(target_slug, warum, klasse), ...])."""
    fm, body = split_frontmatter(content)
    geaendert = 0
    details = []

    def repl(m):
        nonlocal geaendert
        anchor = m.group(1)
        slug = next(g for g in m.groups()[1:] if g)
        ok, why, klasse = link_target_state(slug, posts)
        if ok:
            return m.group(0)
        details.append((slug, why, klasse))
        if klasse == "missing" or (klasse == "transient" and unlink_transient):
            geaendert += 1
            return anchor
        return m.group(0)

    new_body = POST_LINK_RX.sub(repl, body)
    new_content = ("---" + fm + "---" + new_body) if fm else new_body
    return new_content, geaendert, details


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


def scan(do_fix, dry_run=False, strict=False, now=None):
    """Alle Posts + Sektions-/Pillar-Seiten prüfen (und mit --fix heilen).

    Rückgabe: (findings, healed) – findings = [(own, target, warum, klasse)],
    healed = [Beschreibung der tatsächlich geänderten Dateien].
    `strict` entlinkt auch vorübergehend fehlende Ziele (altes Verhalten)."""
    posts = load_posts_map(now=now)
    findings = []
    healed = []

    def process(path, own, is_post):
        nonlocal findings, healed
        content = open(path, encoding="utf-8").read()
        new_content, count, details = heal_content(content, posts,
                                                    unlink_transient=strict)
        findings += [(own, s, w, k) for s, w, k in details]
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

    for path in sorted(list_post_paths()):
        process(path, slug_of(path), True)
    for path in list_section_pages():
        label = os.path.relpath(path, os.path.join(BLOG_DIR, "content"))
        process(path, label, False)
    return findings, healed


def write_report(findings, healed, mode, strict=False):
    now = now_utc().strftime("%Y-%m-%d %H:%M UTC")
    missing = [f for f in findings if f[3] == "missing"]
    transient = [f for f in findings if f[3] == "transient"]
    lines = [
        "# 🔗 DRAFT-LINK-REPORT (draft_link_healer.py)",
        "",
        f"**Stand:** {now} · Modus: {mode}",
        "",
    ]
    if missing:
        lines += [f"## Repariert: Ziel existiert nicht ({len(missing)})", ""]
        lines += [f"- `{own}` → `{target}` ({why})"
                  for own, target, why, _k in missing]
        lines.append("")
    if transient:
        lines += [f"## Gemeldet: Ziel gerade nicht im Build ({len(transient)})",
                  "",
                  "Kein Eingriff nötig – der Render-Guard "
                  "`layouts/_default/_markup/render-link.html` gibt diese "
                  "Links als Klartext aus (kein 404), und sie leben "
                  "automatisch wieder auf, sobald das Ziel zurück im Build "
                  "ist. Entlinken würde nur kuratierte Listen dauerhaft "
                  "ausdünnen.",
                  ""]
        lines += [f"- `{own}` → `{target}` ({why})"
                  for own, target, why, _k in transient]
        lines.append("")
    if not findings:
        lines += ["## Bestand", "",
                  "✅ Keine defekten internen Post-Links – alle Ziele live.",
                  ""]
    if healed:
        lines += ["## Geheilt (dieser Lauf)", ""]
        lines += [f"- ✅ {h}" for h in healed]
        lines.append("")
    elif missing:
        lines += ["## Geheilt (dieser Lauf)", "",
                  "– (nur Prüfung, keine Änderung)", ""]
    if strict and transient:
        lines += ["> ⚠️ `--strict`: auch vorübergehende Ziele wurden entlinkt.",
                  ""]
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

    # Fixierte "jetzt"-Zeit: bestimmt, was als Zukunfts-Post gilt – der
    # Selbsttest darf nie von der Uhrzeit des CI-Laufs abhängen.
    FIXED_NOW = datetime.datetime(2026, 8, 31, 12, 0, tzinfo=datetime.timezone.utc)

    def make(slug, draft=False, date="2026-08-24", clock="08:00:00 +0200",
             body=""):
        d = os.path.join(posts_dir, slug)
        os.makedirs(d, exist_ok=True)
        fm = (f'---\ntitle: "Test {slug}"\n'
              f'date: "{date} {clock}"\n'
              f'draft: {"true" if draft else "false"}\n---\n')
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as f:
            f.write(fm + (body or "Inhalt."))

    make("live-a", body="Link zu [Ziel B](../../posts/draft-b/) und "
                        "[Ziel C](../../posts/future-c/) und "
                        "[Ziel D](../../posts/geloescht-d/) und "
                        "[Ziel E](https://www.franksfinanzcheck.de/"
                        "posts/live-e/?utm_source=x) und "
                        "[Ziel F](/posts/live-f/) und "
                        "[Ziel G](../../posts/future-today/).")
    make("live-f")
    make("live-e")
    make("draft-b", draft=True)
    make("future-c", date="2999-01-01")
    # Heute, aber später als FIXED_NOW → von Hugo nicht gebaut (buildFuture=
    # false vergleicht den ZEITSTEMPEL). Die alte Tag-Genauigkeit sah hier
    # "live" und ließ den toten Link durch (Kern von Issue #129).
    make("future-today", date="2026-08-31", clock="23:59:00 +0000")
    # geloescht-d existiert nicht

    list_post_paths = lambda: sorted(          # noqa: E731
        [os.path.join(posts_dir, s, "index.md")
         for s in ("live-a", "live-e", "live-f", "draft-b", "future-c",
                   "future-today")])
    list_section_pages = lambda: []            # noqa: E731 (Isolation!)
    live_a = os.path.join(posts_dir, "live-a", "index.md")
    try:
        # 1) CHECK findet alle Nicht-Build-Ziele, klassifiziert sie, behält
        #    live-Ziele
        findings, _ = scan(do_fix=False, now=FIXED_NOW)
        targets = {t for _o, t, _w, _k in findings}
        check("check findet draft-/future-/gelöschte Ziele",
              targets == {"draft-b", "future-c", "future-today",
                          "geloescht-d"})
        check("check behält live-Ziele (absolut-e, live-f)",
              not (targets & {"absolut-e", "live-f"}))
        klass = {t: k for _o, t, _w, k in findings}
        check("Ziel-Klassen: nur gelöschtes ist „missing“",
              klass.get("geloescht-d") == "missing"
              and all(klass.get(s) == "transient"
                      for s in ("draft-b", "future-c", "future-today")))
        check("Zeitstempel-Genauigkeit: heute 23:59 UTC ist Zukunfts-Post",
              any("Zukunfts-Post" in w for _o, t, w, _k in findings
                  if t == "future-today"))
        check("check zählt 1 dauerhaftes + 3 transiente Ziele",
              sum(1 for f in findings if f[3] == "missing") == 1
              and sum(1 for f in findings if f[3] == "transient") == 3)

        # 2) FIX (Standard): nur totes Ziel wird entlinkt
        _f, healed = scan(do_fix=True, now=FIXED_NOW)
        a = open(live_a, encoding="utf-8").read()
        check("fix entlinkt gelöschtes Ziel (D)", "posts/geloescht-d/" not in a)
        check("fix BEHÄLT draft-/future-Links (Render-Guard schützt live)",
              all(f"posts/{s}/" in a for s in
                  ("draft-b", "future-c", "future-today")))
        check("fix behält live-Ziele als Links",
              "posts/live-e/" in a and "posts/live-f/" in a)
        check("fix erhält Ankertext (Ziel D)", "Ziel D" in a)

        # 3) Idempotenz + Konvergenz: zweiter Lauf hat nichts mehr zu heilen
        findings2, healed2 = scan(do_fix=True, now=FIXED_NOW)
        check("idempotent: zweiter Lauf heilt nichts mehr",
              not healed2 and all(f[3] != "missing" for f in findings2))

        # 4) --strict: altes Verhalten, auch transient wird entlinkt
        open(live_a, "w", encoding="utf-8").write(
            "Vorher: [Ziel B](../../posts/draft-b/) und "
            "[Ziel C](../../posts/future-c/).")
        scan(do_fix=True, strict=True, now=FIXED_NOW)
        a2 = open(live_a, encoding="utf-8").read()
        check("strict entlinkt auch Draft-/Zukunfts-Ziele",
              "posts/draft-b/" not in a2 and "posts/future-c/" not in a2
              and "Ziel B" in a2 and "Ziel C" in a2)
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
    strict = "--strict" in sys.argv
    if "--selftest" in sys.argv:
        return run_selftest()
    mode = "FIX" if do_fix else "CHECK"
    if strict:
        mode += " · strict"
    findings, healed = scan(do_fix=do_fix, strict=strict)
    write_report(findings, healed, mode, strict=strict)
    # Heilungsbedarf = nur Ziele, die es gar nicht mehr gibt (transiente
    # Ziele erledigt der Render-Guard verlustfrei).
    repair = [f for f in findings if f[3] == "missing"]
    transient = [f for f in findings if f[3] == "transient"]
    if do_fix:
        zusatz = (f" · {len(transient)} transiente(r) gemeldet "
                  f"(Render-Guard, kein Eingriff)" if transient else "")
        print(f"Draft-Link-Heiler: {len(repair)} zu heilende(r) Link(s) in "
              f"{len(healed)} Artikel(n) entlinkt, {len(transient)} "
              f"transiente(r) unverändert gelassen.{zusatz}")
        return 0
    if repair:
        print(f"Draft-Link-Heiler: {len(repair)} defekte interne Links "
              f"(Ziel fehlt dauerhaft) – Details: DRAFT-LINK-REPORT.md.")
        return 1
    if transient:
        print(f"Draft-Link-Heiler: {len(transient)} Link(s) auf "
              f"Nicht-Build-Ziele (Draft/Zukunft) – verlustfrei durch "
              f"Render-Guard abgedeckt, kein Eingriff nötig.")
    else:
        print("Draft-Link-Heiler: keine defekten internen Links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
