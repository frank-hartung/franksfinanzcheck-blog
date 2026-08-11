#!/usr/bin/env python3
"""Font-Backerei (11.08.2026 spaet): Baut aus den gelockten Variable-Fonts in
static/fonts/_src/ die einzelnen statischen woff2-Dateien mit exakt dem
Gewicht, das der Dateiname verspricht. Aufgerufen von font_guard --fix."""
import os
import sys
from fontTools import ttLib
from fontTools.varLib.instancer import instantiateVariableFont

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BLOG_DIR, "static", "fonts", "_src")
OUT = os.path.join(BLOG_DIR, "static", "fonts")

# Dateiname -> (Quelle, Gewicht, italic?)   [Inter-Aera, 11.08. spaet]
FONT_PLAN = {
    "Inter-Bold.ttf":                      ("Inter-var.ttf", 700, False),  # Cover-Font (kein flavor)
    "playfairdisplay-normal-500.woff2":   ("PlayfairDisplay-var.ttf", 500, False),
    "playfairdisplay-normal-600.woff2":   ("PlayfairDisplay-var.ttf", 600, False),
    "playfairdisplay-italic-500.woff2":   ("PlayfairDisplay-Italic-var.ttf", 500, True),
}


def font_family(f):
    return f["name"].getDebugName(16) or f["name"].getDebugName(1) or "?"


def verify(path, expect_weight):
    f = ttLib.TTFont(path)
    wc = f["OS/2"].usWeightClass
    fam = font_family(f)
    return wc == expect_weight, wc, fam


def build_one(filename, src, weight, italic):
    src_path = os.path.join(SRC, src)
    if not os.path.exists(src_path):
        return False, f"Quelle fehlt: {src}"
    f = ttLib.TTFont(src_path)
    instantiateVariableFont(f, {"wght": weight}, inplace=True)
    fam_base = "Inter" if "Inter" in font_family(f) else ("Montserrat" if "Montserrat" in font_family(f) else "Playfair Display")
    name = f["name"]
    sub_by_weight = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
    sub = sub_by_weight.get(weight, str(weight)) + (" Italic" if italic else "")
    for plat, enc in ((3, 1), (0, 3)):
        name.setName(fam_base, 1, plat, enc, 1033)          # Familie sauber
        name.setName(sub, 2, plat, enc, 1033)               # Subfamily
        name.setName(f"{fam_base} {sub}", 4, plat, enc, 1033)
        name.setName(fam_base, 16, plat, enc, 1033)
        name.setName(sub.replace(" Italic", ""), 17, plat, enc, 1033)
    out_path = os.path.join(OUT, filename)
    if not filename.endswith(".ttf"):
        f.flavor = "woff2"
    f.save(out_path)
    ok, wc, fam = verify(out_path, weight)
    return ok, f"{wc}/{fam}"


def main():
    only = sys.argv[sys.argv.index("--file") + 1] if "--file" in sys.argv else None
    all_ok = True
    for filename, (src, weight, italic) in FONT_PLAN.items():
        if only and only != filename:
            continue
        ok, info = build_one(filename, src, weight, italic)
        mark = "OK " if ok else "FAIL"
        print(f"  {mark} {filename}: weightClass={info}")
        all_ok = all_ok and ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
