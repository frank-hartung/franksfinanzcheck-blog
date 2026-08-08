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
                covers.append({"file": f, "image": m.group(1).strip()})
    return covers


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


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    covers = collect_covers()
    problems = check(covers)

    if fix and problems:
        print(f"{len(problems)} Cover mit fehlenden Varianten – ziehe nach …")
        subprocess.run([sys.executable, os.path.join(BLOG_DIR, "scripts", "generate_covers.py")],
                       cwd=BLOG_DIR, check=False)
        problems = check(covers)  # erneut prüfen

    print(f"Cover-Check: {len(covers)} Covers | Probleme: {len(problems)}")
    for p in problems:
        print(f"  ❌ {os.path.basename(os.path.dirname(p['file']))}: {p['image']} → fehlt: {', '.join(p['missing'])}")

    if as_json:
        print(json.dumps({"total": len(covers), "problems": len(problems),
                          "items": problems}, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
