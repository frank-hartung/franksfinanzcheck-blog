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


# ------------------------------------------------------------
# C2: BRAND-GATE (12.08. Runde 2, Frank: Marke auf Covers strikt sichtbar)
#  Signet-Band unten (80–100 % Hoehe): goldene Fuehrungslinie +
#  goldenes Haeckchen + "check" in Gold. Brandwalk: Energie-Messung
#  goldener Pixel im Brand-Band — jedes Cover beweist Branding
#  mechanisch, nie blind. Selbstheilung: generate_covers --slug --force.
# ------------------------------------------------------------
BRAND_PROBE_RATIO_MIN = 0.004    # ≥ 0,4 % goldene Pixel im Brand-Band

# C2b: Signet-Praesenz links im Band (das goldene Haeckchen-Bildzeichen).
SIGNET_PROBE_RATIO_MIN = 0.002   # ≥ 0,2 % gold im Signet-Quadrant


def brand_strength(image_path):
    """Energie der Brandzone: viele goldene Pixel im Band → Ratio. None bei Fehler."""
    try:
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        W, H = img.size
    except Exception:
        return None
    # Brand-Band (12.08. Runde 2): y 80–97 % H, x 10–90 % W
    y0, y1 = int(H * 0.82), int(H * 0.97)
    x0, x1 = int(W * 0.10), int(W * 0.90)
    px = img.load()
    gold = total = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            total += 1
            if r > 180 and 110 < g < 210 and b < 90:   # Gold (Linie/Haeckchen/"check")
                gold += 1
    return gold / max(1, total)


def signet_strength(image_path):
    """C2b: Goldenes Haeckchen-Signet im linken Band-Quadranten vorhanden?"""
    try:
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        W, H = img.size
    except Exception:
        return None
    # Signet-Bereich: links des Wortmarke-Blocks (x 12–26 % W), Mitte des Bands
    y0, y1 = int(H * 0.855), int(H * 0.93)
    x0, x1 = int(W * 0.12), int(W * 0.26)
    px = img.load()
    gold = total = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            total += 1
            if r > 180 and 110 < g < 210 and b < 90:
                gold += 1
    return gold / max(1, total)


def check_brand(covers):
    """C2+C2b (12.08. R2): Brand-Band + Signet muessen messbar vorhanden sein."""
    out = []
    for it in covers:
        base = os.path.basename(it["image"])
        p = os.path.join(STATIC_DIR, base)
        s = brand_strength(p) if os.path.exists(p) else None
        g = signet_strength(p) if os.path.exists(p) else None
        if s is None:
            out.append((it, "unlesbar/fehlt"))
        elif s < BRAND_PROBE_RATIO_MIN:
            out.append((it, f"Brandzone {s:.4f} < {BRAND_PROBE_RATIO_MIN}"))
        elif g is None or g < SIGNET_PROBE_RATIO_MIN:
            out.append((it, f"Signet {g if g is not None else 'unlesbar'} < {SIGNET_PROBE_RATIO_MIN}"))
    return out


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
    brand_bad = check_brand(covers)   # C2 (12.08., Frank): Brand-Chip presenza

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
        if brand_bad:
            print(f"{len(brand_bad)} Cover ohne messbaren Brand-Chip – generiere neu …")
            gen = os.path.join(BLOG_DIR, "scripts", "generate_covers.py")
            for it, warum in brand_bad:
                print(f"  → {it.get('slug', it['file'])}: {warum}")
                subprocess.run([sys.executable, gen, "--slug", it.get("slug",
                                   os.path.splitext(os.path.basename(it["image"]))[0]), "--force"],
                               cwd=BLOG_DIR, check=False)
            covers = collect_covers()
            brand_bad = check_brand(covers)
    elif not os.path.exists(os.path.join(BLOG_DIR, "data", "covers_manifest.json")):
        # Manifest initial befüllen (einmalig, nach Konsistenz-Check):
        # generiert keine Bilder neu, aktualisiert nur die Manifeste.
        subprocess.run([sys.executable, os.path.join(BLOG_DIR, "scripts", "generate_covers.py")],
                       cwd=BLOG_DIR, check=False)

    total = len(problems) + len(stale) + len(brand_bad)
    print(f"Cover-Check: {len(covers)} Covers | Probleme: {len(problems)} | "
          f"Stale: {len(stale)} | Brand: {len(brand_bad)}")
    for it, warum in brand_bad:
        print(f"  ❌ BRAND {it['file']}: {warum}")
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
