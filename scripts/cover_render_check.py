#!/usr/bin/env python3
"""Cover-Render-Wache: Stimmt das gespeicherte JPG noch mit seinem Titel?

Hintergrund (Audit #743, Nachschärfung 14.10.2026): Der Cover-Generator
erneuerte ein Cover nur bei Design-Drift. Eine Titeländerung aktualisierte
zwar das Manifest, nicht aber das Bild – `check_covers.py` meldete daher
„Stale: 0“, obwohl 63 von 96 Covers nicht mehr ihrem Titel bzw. ihrer
Spar-Pille entsprachen. Diese Wache rendert jedes Cover im Speicher neu und
vergleicht die Pixel mit der gespeicherten Datei. Der Generator ist
deterministisch: ein korrektes Cover ist pixelidentisch (Diff 0).

Modi:
  python3 scripts/cover_render_check.py            # alle Cover prüfen (Exit 0/1)
  python3 scripts/cover_render_check.py --selftest # Sabotage-Proben (Exit 0 = scharf)
  python3 scripts/cover_render_check.py --json     # Befunde als JSON

Reparatur eines Befunds (Pipeline, nicht von Hand):
  python3 scripts/generate_covers.py --slug <slug>           # Artikel
  python3 scripts/generate_covers.py --pillars --slug pillar-<silo>
"""
import json
import os
import re
import sys
import tempfile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))


def _gc():
    import generate_covers as gc  # Lazy: braucht Pillow + Inter-Schrift
    return gc


def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("&nbsp;", " ").replace("\u00a0", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def expected_inputs(gc, content_path, content):
    """(slug, title, badge, savings) exakt wie der Generator sie ableitet."""
    is_pillar = "/pillar/" in content_path.replace(os.sep, "/")
    if is_pillar:
        silo = os.path.basename(os.path.dirname(content_path))
        slug = f"pillar-{silo}"
        title = _clean(gc._title_from_content(content) or silo.replace("-", " "))
    else:
        slug = gc.slug_of(content_path)
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        title = _clean(m.group(1) if m else slug)
    pm = re.search(r'^pillar:\s*["\']?([\w\-]+)["\']?\s*$', content, re.M)
    dm = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', content, re.M)
    sm = re.search(r'^savings:\s*["\']?(.+?)["\']?\s*$', content, re.M)
    desc = dm.group(1) if dm else ""
    if is_pillar:
        badge = gc.PILLAR_BADGES.get(slug.replace("pillar-", "")) or gc.detect_badge(
            slug.replace("pillar-", ""), slug, title)
    else:
        badge = gc.detect_badge(pm.group(1) if pm else None, slug, title)
    savings = gc.extract_savings(title, desc, sm.group(1) if sm else None)
    return slug, title, badge, savings


def render_to(gc, title, badge, savings, out_path):
    """Rendert nur das Original-JPG (Varianten werden hier nicht geschrieben)."""
    original = gc.save_modern_variants
    gc.save_modern_variants = lambda *a, **k: []
    try:
        gc.make_cover(title, "render-check", out_path, force=True,
                      badge=badge, savings=savings)
    finally:
        gc.save_modern_variants = original


def same_pixels(path_a, path_b):
    from PIL import Image, ImageChops
    a = Image.open(path_a).convert("RGB")
    b = Image.open(path_b).convert("RGB")
    if a.size != b.size:
        return False
    return ImageChops.difference(a, b).getbbox() is None


def run(root=BLOG_DIR):
    gc = _gc()
    import glob
    paths = list(gc.list_post_paths()) + [p for _, p in gc.pillar_paths()]
    findings = []
    with tempfile.TemporaryDirectory(prefix="cover-render-") as tmp:
        for path in sorted(paths):
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            slug, title, badge, savings = expected_inputs(gc, path, content)
            cover = os.path.join(gc.OUT_DIR, f"{slug}.jpg")
            if not os.path.exists(cover):
                findings.append({"slug": slug, "problem": "Cover-Datei fehlt"})
                continue
            out = os.path.join(tmp, f"{slug}.jpg")
            render_to(gc, title, badge, savings, out)
            if not same_pixels(cover, out):
                findings.append({"slug": slug, "problem": "Bild weicht vom Titel/Design ab",
                                 "titel": title, "pille": savings})
    return findings, len(paths)


def run_selftest():
    gc = _gc()
    fails = []
    with tempfile.TemporaryDirectory(prefix="cover-render-selftest-") as tmp:
        a = os.path.join(tmp, "a.jpg")
        b = os.path.join(tmp, "b.jpg")
        c = os.path.join(tmp, "c.jpg")
        render_to(gc, "Strom sparen: Ratgeber", "STROM & GAS SPAREN", None, a)
        render_to(gc, "Strom sparen: Ratgeber", "STROM & GAS SPAREN", None, b)
        render_to(gc, "Gas sparen: Anderer Titel", "STROM & GAS SPAREN", None, c)
        if not same_pixels(a, b):
            fails.append("Gegenprobe: gleicher Titel muss pixelidentisch sein")
        if same_pixels(a, c):
            fails.append("Sabotage: geänderter Titel wurde NICHT erkannt")
        d = os.path.join(tmp, "d.jpg")
        render_to(gc, "Strom sparen: Ratgeber", "STROM & GAS SPAREN", "bis zu 360 € sparen", d)
        if same_pixels(a, d):
            fails.append("Sabotage: geänderte Spar-Pille wurde NICHT erkannt")
    if fails:
        print("🛑 Cover-Render-Selbsttest FEHLGESCHLAGEN:")
        for f in fails:
            print("   -", f)
        return 2
    print("✅ Cover-Render-Selbsttest: Gegenprobe + 2 Sabotage-Proben bestanden.")
    return 0


def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    if run_selftest() != 0:
        return 2
    findings, count = run()
    if "--json" in argv:
        print(json.dumps({"covers": count, "findings": findings}, ensure_ascii=False, indent=1))
    else:
        for f in findings:
            print(f"  {f['slug']}: {f['problem']}")
        print(f"Cover-Render-Wache: {count} Cover geprüft | Befunde: {len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
