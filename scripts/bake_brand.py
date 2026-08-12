#!/usr/bin/env python3
# ============================================================
#  BAKE-BRAND – backt das FranksFinanzcheck-Markenzeichen deterministisch
#
#  AUFTRAG (Frank, 12.08.2026, Runde 2): Die Cover-Wortmarke
#  (goldenes Haeckchen-Signet + "FranksFinanz" + "check" in Gold)
#  wird das offizielle Logo des GESAMTEN Blogs: Header, Favicon,
#  Apple-Touch-Icon. Damit niemand das Logo verfaelschen kann und
#  es bei Verlust EXAKT wiederhergestellt wird, backt dieses Skript
#  alle Marken-Artefakte deterministisch aus static/fonts/Inter-Bold.ttf.
#
#  DETERMINISMUS = SABOTAGESCHUTZ: brand_guard.py vergleicht SHA-256
#  der Artefakte mit data/brand_lock.yaml; Abweichung → dieses Skript
#  erzeugt das kanonische Original bytegleich neu (Selbstheilung).
#
#  Aufruf:
#    python3 scripts/bake_brand.py            # backen (idempotent)
#    python3 scripts/bake_brand.py --check    # nur pruefen (Exit 0/1)
# ============================================================
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "static" / "fonts" / "Inter-Bold.ttf"

# Markenfarben (Masterplan; identisch zu generate_covers.py + custom.css)
EMERALD = "#0E5A43"   # Smaragdgruen (Wortmarke auf hellem Grund)
GOLD = "#FFB300"      # Signalgold (Signet + "check")
WHITE = "#FFFFFF"     # Wortmarke dunkel-Variante (fuer dunkle Flaechen)
DARK = "#072E22"      # sehr tiefes Gruen (Band/Favicon-Grund)

# Artefakte --------------------------------------------------------------
OUT_SVG = ROOT / "static" / "images" / "brand" / "logo.svg"          # heller Grund (Header)
OUT_SVG_DARK = ROOT / "static" / "images" / "brand" / "logo-light.svg"  # dunkler Grund (Footer)
OUT_FAVICON = ROOT / "static" / "favicon.svg"
OUT_APPLE = ROOT / "static" / "apple-touch-icon.png"

FONT_SIZE = 56        # SVG-Einheiten der Wortmarke
WORD1, WORD2 = "FranksFinanz", "check"
SIGNET_W, SIGNET_GAP = 46, 10   # Haeckchen-Kasten + Abstand zur Wortmarke


def _text_paths():
    """Wandelt WORD1/WORD2 via fonttools in SVG-Pfad-Daten um.

    Liefert (path1, path2, w1, w2, asc, desc) — Pfade im Font-Unit-Raum
    skaliert auf FONT_SIZE, Baseline y=0. Schlaegt der Font fehl,
    wird LAUT abgebrochen (Font-Pact: nie auf Fremdfonts ausweichen).
    """
    try:
        from fontTools.ttLib import TTFont
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.transformPen import TransformPen
        from fontTools.misc.transform import Transform
    except ImportError:
        sys.exit("FEHLER: fonttools fehlt – pip install fonttools brotli")
    if not FONT_PATH.exists():
        sys.exit("🛑 FONT-PACT VERLETZT: static/fonts/Inter-Bold.ttf fehlt! "
                 "Erst `python3 scripts/bake_fonts.py --file Inter-Bold.ttf`.")
    font = TTFont(str(FONT_PATH))
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upem = font["head"].unitsPerEm
    hhea = font["hhea"]
    scale = FONT_SIZE / upem

    def word(word_text):
        pen = SVGPathPen(glyphs)
        x = 0.0
        width = 0.0
        # Kerning-Paare aus GPOS waeren Luxus; Inter Bold Kunst-Setting: fix -0.2%
        for ch in word_text:
            gname = cmap[ord(ch)]
            # Glyph bei x zeichnen (y gespiegelt: SVG y waechst nach unten)
            tp = TransformPen(pen, Transform(scale, 0, 0, -scale, x, 0))
            glyphs[gname].draw(tp)
            width = x + glyphs[gname].width * scale
            x += glyphs[gname].width * scale * 0.998  # hauchdichter Sperrsatz
        return pen.getCommands(), width

    p1, w1 = word(WORD1)
    p2, w2 = word(WORD2)
    asc = hhea.ascent * scale
    desc = -hhea.descent * scale
    return p1, p2, w1, w2, asc, desc


CHECK_D = ("M6 24.5 L18.5 37 L40 10"   # Haeckchen als offener Pfad (stroke)
           )


def _logo_svg(word_fill: str) -> str:
    """Komplette Wortmarke als SVG. Klassen ermoeglichen Dark-Mode-Faerbung
    via CSS (fill-Fallback steht inline)."""
    p1, p2, w1, w2, asc, desc = _text_paths()
    text_h = asc + desc
    box_h = max(text_h, SIGNET_W)
    text_w = w1 + w2
    total_w = SIGNET_W + SIGNET_GAP + text_w
    y_base = (box_h - text_h) / 2 + asc          # Baseline der Wortmarke
    # Signet optisch auf x-Hoehe zentrieren
    sig_y = y_base - FONT_SIZE * 0.72            # Oberkante des Haeckchen-Kastens
    sx = SIGNET_W
    sy = sig_y
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="FranksFinanzcheck" '
        f'viewBox="0 0 {total_w:.2f} {box_h:.2f}" width="{total_w * 30 / box_h:.0f}" height="30">'
        f'<title>FranksFinanzcheck</title>'
        f'<g class="ff-signet" transform="translate(0,{sy:.2f}) scale({SIGNET_W / 46:.3f})">'
        f'<path d="{CHECK_D}" fill="none" stroke="{GOLD}" stroke-width="9" '
        f'stroke-linecap="round" stroke-linejoin="round"/></g>'
        f'<g class="ff-wordmark" transform="translate({sx + SIGNET_GAP:.2f},{y_base:.2f})">'
        f'<path class="ff-wm" d="{p1}" fill="{word_fill}"/>'
        f'<g transform="translate({w1:.2f},0)">'
        f'<path class="ff-wm-check" d="{p2}" fill="{GOLD}"/></g></g></svg>'
    )


def _favicon_svg() -> str:
    """Einfaches, sofort erkennbares Favicon: goldener Haken auf tiefem Gruen."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="14" fill="{DARK}"/>'
        f'<path d="{CHECK_D} " transform="translate(9,12) scale(1.15)" fill="none" '
        f'stroke="{GOLD}" stroke-width="9" stroke-linecap="round" '
        f'stroke-linejoin="round"/></svg>'
    )


def _apple_icon_png() -> bytes:
    """180x180 Apple-Touch-Icon (Emerald-Grund, goldener Haken)."""
    from PIL import Image, ImageDraw
    S = 180
    img = Image.new("RGB", (S, S), (7, 46, 34))
    d = ImageDraw.Draw(img)
    gold_rgb = (255, 179, 0)
    # Haken geometrisch wie CHECK_D (6,24.5)-(18.5,37)-(40,10) im 46er-Kasten:
    k = S / 46
    d.line([(6 * k, 24.5 * k), (18.5 * k, 37 * k), (40 * k, 10 * k)],
           fill=gold_rgb, width=int(9 * k), joint="curve")
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(14 * k / 64 * S / 3), outline=None)
    import io
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def artefacts():
    """Kanonischer Output: {relpfad: bytes}. Single Source of Truth."""
    return {
        str(OUT_SVG.relative_to(ROOT)): _logo_svg(EMERALD).encode("utf-8"),
        str(OUT_SVG_DARK.relative_to(ROOT)): _logo_svg(WHITE).encode("utf-8"),
        str(OUT_FAVICON.relative_to(ROOT)): _favicon_svg().encode("utf-8"),
        str(OUT_APPLE.relative_to(ROOT)): _apple_icon_png(),
    }


def main():
    check_only = "--check" in sys.argv
    arts = artefacts()
    drift = []
    for rel, data in arts.items():
        p = ROOT / rel
        if not p.exists() or p.read_bytes() != data:
            drift.append(rel)
    if check_only:
        if drift:
            print(f"❌ BRAND-DRIFT: {len(drift)} Artefakte weichen ab: {', '.join(drift)}")
            return 1
        print(f"✅ Brand-Artefakte bytegleich kanonisch ({len(arts)} Dateien)")
        return 0
    for rel, data in arts.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        prev = p.read_bytes() if p.exists() else None
        if prev != data:
            p.write_bytes(data)
            print(f"  ✓ gebacken: {rel} (sha256 {hashlib.sha256(data).hexdigest()[:12]})")
        else:
            print(f"  = unveraendert: {rel}")
    print(f"Fertig: {len(arts)} Marken-Artefakte kanonisch gebacken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
