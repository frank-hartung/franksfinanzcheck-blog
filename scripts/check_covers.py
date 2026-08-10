"""Cover-Validierung (vollautomatisch, Top-Level) für FranksFinanzcheck.

Prüft für JEDEN Post/Pillar mit cover-Feld, dass ALLE Cover-Varianten
existieren:
  - Original (static/images/covers/<datei>)
  - 620/, 720/ (JPEG-Varianten)
  - avif/, webp/ (Original-Formate)
  - avif/620/, avif/720/, webp/620/, webp/720/ (responsive Varianten)

Hintergrund: Beim Umbenennen eines Posts (z. B. Datumskorrektur) wurden
bisher nur die Original-JPGs mitbenannt – AVIF/WebP-Varianten fehlten
→ 404 im <picture>-srcset (Lighthouse/Crawl-Fund).

Modi:
  python3 scripts/check_covers.py            # nur prüfen (Exit 0/1)
  python3 scripts/check_covers.py --fix      # fehlende Varianten via
                                             # generate_covers.py nachziehen
  python3 scripts/check_covers.py --json     # JSON-Output

Exit: 0 = alles ok · 1 = Probleme (Workflow kann alerten)
"""
import os
import re
import sys
import json
import glob
import subprocess

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BLOG_DIR, "static", "images", "covers")

# Varianten-Unterordner, die für jede Cover-Datei existieren müssen
VARIANTS = ["620", "720", "avif", "webp", "avif/620", "avif/720", "webp/620", "webp/720"]


def collect_covers():
    """Alle cover.image-Pfade aus Posts + Pillar-Seiten."""
    covers = []
    for pattern in ["content/posts/*/index.md", "content/pillar/*/index.md"]:
        for f in glob.glob(os.path.join(BLOG_DIR, pattern)):
            content = open(f, encoding="utf-8").read()
            m = re.search(r'^cover:\s*\n\s*image:\s*"?([^"\n]+)"?', content, re.M)
            if m:
                tm = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
                title = (tm.group(1).strip() if tm else "").strip('"')
                covers.append({"file": f, "image": m.group(1).strip(), "title": title})
    return covers


def normalize_dash_image(img):
    """Korrigiert Gedankenstriche (–/—) in Cover-DATEINAMEN zu Bindestrichen.

    Selbstheilung nach Fund: Frontmatter referenzierte
    „images/covers/50–30–20-regel…jpg" (Gedankenstrich), die Datei hieß
    „50-30-20-regel…jpg" (Bindestrich) → 404 im <picture>-srcset.
    Deterministik: Nur wenn die Bindestrich-Variante existiert und die
    referenzierte nicht, wird die Referenz angepasst (--fix).
    """
    if "–" not in img and "—" not in img:
        return img
    base = os.path.basename(img)
    fixed = os.path.join(os.path.dirname(img), base.replace("–", "-").replace("—", "-"))
    if (not os.path.exists(os.path.join(STATIC_DIR, base))
            and os.path.exists(os.path.join(STATIC_DIR, os.path.basename(fixed)))):
        return fixed
    return img


def check(covers):
    problems = []
    for c in covers:
        img = c["image"]
        base = os.path.basename(img)
        stem = os.path.splitext(base)[0]
        original = os.path.join(STATIC_DIR, base)
        if not os.path.exists(original):
            problems.append({"file": c["file"], "image": img, "missing": ["ORIGINAL"]})
            continue
        missing = []
        for v in VARIANTS:
            # Varianten: 620/<base>.jpg, avif/<stem>.avif, avif/620/<stem>.avif, ...
            if "/" in v:
                sub, w = v.split("/")
                if sub in ("620", "720"):
                    p = os.path.join(STATIC_DIR, sub, base)
                else:  # avif/620, avif/720, webp/620, webp/720
                    ext = "avif" if sub == "avif" else "webp"
                    p = os.path.join(STATIC_DIR, sub, w, f"{stem}.{ext}")
            else:
                if v in ("620", "720"):
                    p = os.path.join(STATIC_DIR, v, base)
                else:
                    ext = "avif" if v == "avif" else "webp"
                    p = os.path.join(STATIC_DIR, v, f"{stem}.{ext}")
            if not os.path.exists(p):
                missing.append(v)
        if missing:
            problems.append({"file": c["file"], "image": img, "missing": missing})
    return problems


def check_stale(covers):
    """Stale-Covers: Cover-Bild wurde mit anderem Titel gerendert als der
    aktuelle Frontmatter-Titel (Titel-Änderung ohne Cover-Re-Generierung).

    Basis: data/covers_manifest.json (geschrieben von generate_covers.py).
    Fehlt das Manifest, gilt alles als unbekannt (wird beim ersten
    Gesamtlauf befüllt).
    """
    manifest_path = os.path.join(BLOG_DIR, "data", "covers_manifest.json")
    if not os.path.exists(manifest_path):
        return []
    try:
        manifest = json.load(open(manifest_path, encoding="utf-8"))
    except Exception:
        return []
    stale = []
    for c in covers:
        base = os.path.basename(c["image"])
        slug = os.path.splitext(base)[0]
        entry = manifest.get(slug)
        if entry is None:
            continue  # unbekannt → nicht als Fehler werten
        m_title = (entry.get("title") or "").strip()
        f_title = (c.get("title") or "").strip()
        if m_title and f_title and m_title != f_title:
            stale.append({
                "file": c["file"], "slug": slug,
                "manifest_title": m_title, "frontmatter_title": f_title,
            })
    return stale


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    covers = collect_covers()
    problems = check(covers)
    stale = check_stale(covers)

    # Selbstheilung: Gedankenstrich im Cover-Dateinamen → Bindestrich
    # (wenn die Bindestrich-Datei existiert; --fix schreibt die Referenz um)
    dash_fixes = 0
    for c in covers:
        img = c["image"]
        if "–" in img or "—" in img:
            fixed = normalize_dash_image(img)
            if fixed != img and fix:
                content = open(c["file"], encoding="utf-8").read()
                content = content.replace(img, fixed)
                open(c["file"], "w", encoding="utf-8").write(content)
                dash_fixes += 1

    if fix:
        if problems:
            print(f"{len(problems)} Cover mit fehlenden Varianten – ziehe nach …")
            subprocess.run([sys.executable, os.path.join(BLOG_DIR, "scripts", "generate_covers.py")],
                           cwd=BLOG_DIR, check=False)
            covers = collect_covers()
            problems = check(covers)
        if stale:
            print(f"{len(stale)} Cover mit veraltetem Text – generiere neu …")
            gen = os.path.join(BLOG_DIR, "scripts", "generate_covers.py")
            for s in stale:
                print(f"  → {s['slug']}: '{s['manifest_title']}' ≠ "
                      f"'{s['frontmatter_title']}'")
                subprocess.run([sys.executable, gen, "--slug", s["slug"], "--force"],
                               cwd=BLOG_DIR, check=False)
            covers = collect_covers()
            stale = check_stale(covers)
    elif not os.path.exists(os.path.join(BLOG_DIR, "data", "covers_manifest.json")):
        # Manifest initial befüllen (einmalig, nach Konsistenz-Check):
        # generiert keine Bilder neu, aktualisiert nur die Manifeste.
        subprocess.run([sys.executable, os.path.join(BLOG_DIR, "scripts", "generate_covers.py")],
                       cwd=BLOG_DIR, check=False)

    total = len(problems) + len(stale)
    print(f"Cover-Check: {len(covers)} Covers | Probleme: {len(problems)} | "
          f"Stale: {len(stale)}")
    for p in problems:
        print(f"  ❌ {os.path.basename(os.path.dirname(p['file']))}: {p['image']} → fehlt: {', '.join(p['missing'])}")
    for s in stale:
        print(f"  ❌ STALE {s['slug']}: Cover zeigt '{s['manifest_title']}', "
              f"Frontmatter '{s['frontmatter_title']}'")

    if as_json:
        print(json.dumps({"total": len(covers), "problems": len(problems),
                          "stale": len(stale),
                          "items": problems + stale}, ensure_ascii=False))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
