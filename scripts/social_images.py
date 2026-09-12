#!/usr/bin/env python3
# ============================================================
#  SOCIAL-IMAGES – Format-Varianten der Cover (kanalgenau)
#  ------------------------------------------------------------
#  Das Cover des Blogs ist 2:3 (1000×1500) – perfekt für Pinterest,
#  aber AUSSERHALB des zulässigen Bereichs von Instagram (4:5 bis
#  1,91:1). Würde man es direkt senden, lehnt die API den Post ab
#  oder beschneidet Motiv und Schrift.
#
#  Dieses Skript rendert deshalb je Kanal eine eigene Variante:
#    static/images/social/<slug>-<format>.jpg
#
#  Eigenschaften (bewusst betriebssicher):
#    · MITTIGER Beschnitt – die Schrift des Covers liegt zentriert,
#      damit Text nicht abgeschnitten wird
#    · idempotent: gleiche Quelle → kein erneutes Rendern
#    · ohne Pillow kein Abbruch: dann wird das Original verwendet
#      (das Gate meldet die Abweichung, der Lauf bleibt heil)
#    · Aufräumen: --prune entfernt Varianten veröffentlichter
#      Beiträge, damit das Repo nicht vollläuft
# ============================================================
from __future__ import annotations

import os
import sys
import time

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BLOG_DIR, "static")
OUT_DIR = os.path.join(STATIC_DIR, "images", "social")

# Format → (Breite, Höhe) in Pixeln
RATIOS = {
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "5:4": (1080, 864),
    "3:2": (1200, 800),
    "16:9": (1200, 675),
    "1.91:1": (1200, 628),
    "2:3": (1000, 1500),
    "9:16": (1080, 1920),
}

TAG_BY_RATIO = {"1:1": "1x1", "4:5": "4x5", "5:4": "5x4", "3:2": "3x2",
                "16:9": "16x9", "1.91:1": "191x100", "2:3": "2x3", "9:16": "9x16"}


def target_path(slug: str, ratio: str) -> str:
    tag = TAG_BY_RATIO.get(ratio, ratio.replace(":", "x").replace(".", ""))
    return os.path.join(OUT_DIR, f"{slug}-{tag}.jpg")


def static_rel(abs_path: str) -> str:
    return os.path.relpath(abs_path, STATIC_DIR).replace(os.sep, "/")


def ensure_variant(src: str, slug: str, ratio: str, force: bool = False) -> str | None:
    """Rendert die Kanal-Variante eines Covers. Liefert den absoluten Pfad."""
    if not src or not os.path.isfile(src):
        return None
    if ratio not in RATIOS:
        return src
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001 – ohne Pillow: Original verwenden
        print("    ⚠ Pillow fehlt – nutze das Original-Cover.")
        return src

    dst = target_path(slug, ratio)
    try:
        if os.path.isfile(dst) and not force:
            if os.path.getmtime(dst) >= os.path.getmtime(src):
                return dst
        os.makedirs(OUT_DIR, exist_ok=True)
        with Image.open(src) as img:
            img = img.convert("RGB")
            tw, th = RATIOS[ratio]
            target = tw / th
            w, h = img.size
            current = w / h
            if abs(current - target) > 0.001:
                # Mittig beschneiden (Schrift sitzt in der Cover-Mitte)
                if current > target:
                    new_w = int(round(h * target))
                    left = max(0, (w - new_w) // 2)
                    img = img.crop((left, 0, left + new_w, h))
                else:
                    new_h = int(round(w / target))
                    top = max(0, (h - new_h) // 2)
                    img = img.crop((0, top, w, top + new_h))
            img = img.resize((tw, th), Image.LANCZOS)
            img.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        return dst
    except Exception as exc:  # noqa: BLE001
        print(f"    ⚠ Bildvariante fehlgeschlagen ({exc}) – nutze das Original.")
        return src


def prune(keep_slugs: set[str], max_age_days: int = 30) -> int:
    """Löscht Varianten, die veröffentlicht und alt sind (Repo-Hygiene)."""
    if not os.path.isdir(OUT_DIR):
        return 0
    removed = 0
    limit = time.time() - max_age_days * 86400
    for name in sorted(os.listdir(OUT_DIR)):
        if not name.endswith(".jpg"):
            continue
        slug = name.rsplit("-", 1)[0]
        path = os.path.join(OUT_DIR, name)
        try:
            if slug not in keep_slugs and os.path.getmtime(path) < limit:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    return removed


def url_is_live(url: str, timeout: int = 12) -> bool:
    """Ist die Bild-URL öffentlich erreichbar? (Instagram braucht das.)"""
    import urllib.error
    import urllib.request

    if not url:
        return False
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "FranksFinanzcheck-SocialAutopilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as exc:
        if exc.code == 405:  # HEAD nicht erlaubt – mit GET-Range prüfen
            try:
                req2 = urllib.request.Request(url, method="GET",
                                              headers={"User-Agent": "FranksFinanzcheck/1.0",
                                                       "Range": "bytes=0-0"})
                with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                    return resp2.status < 400
            except Exception:  # noqa: BLE001
                return False
    except Exception:  # noqa: BLE001
        return False
    return False


if __name__ == "__main__":  # pragma: no cover
    if "--prune" in sys.argv:
        days = 30
        if "--days" in sys.argv:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        print(f"🧹 {prune(set(), max_age_days=days)} alte Bildvarianten entfernt.")
    else:
        print("Nutzung: python3 scripts/social_images.py --prune [--days N]")
