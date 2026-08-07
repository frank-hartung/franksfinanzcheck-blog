#!/usr/bin/env python3
"""
Generiert für jeden Blog-Artikel ein Branding-Cover (Smaragdgrün/Gelb –
Stil des Pinterest-Masterplans) und trägt es ins Frontmatter ein.

- Bilder: static/images/covers/<slug>.jpg (1000x1500, 2:3 – Pinterest-Format)
- Frontmatter: cover.image, cover.alt, cover.caption (nur falls noch keins existiert)
- Das Theme rendert das Cover im Artikel und als og:image

Nutzung:
    python3 scripts/generate_covers.py
"""
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
OUT_DIR = os.path.join(BLOG_DIR, "static", "images", "covers")

# --- Farben aus dem Masterplan ---
EMERALD = (14, 90, 67)        # Smaragdgrün
EMERALD_DARK = (8, 58, 43)    # dunkleres Grün für Verlauf
GOLD = (255, 179, 0)          # Signalgelb
WHITE = (255, 255, 255)
CREAM = (240, 245, 242)

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit("FEHLER: pillow nicht installiert –  pip install pillow")

try:
    import pillow_avif  # noqa: F401 – Aktiviert AVIF-Support in Pillow
    AVIF_OK = True
except ImportError:
    AVIF_OK = False
    print("HINWEIS: pillow-avif-plugin fehlt – AVIF-Varianten werden übersprungen "
          "(pip install pillow-avif-plugin)")


def save_modern_variants(img, out_path):
    """Speichert WebP- und AVIF-Varianten (1000/620/720px) für ein Cover.

    Struktur:
        webp/<name>.webp          avif/<name>.avif          (1000px)
        webp/620/<name>.webp      avif/620/<name>.avif      (620px)
        webp/720/<name>.webp      avif/720/<name>.avif      (720px)

    AVIF ~50 % kleiner als WebP, WebP ~30-50 % kleiner als JPEG –
    so liefert <picture> jedem Browser das kleinste passende Format.
    """
    W, H = img.size
    base = os.path.dirname(out_path)
    name = os.path.basename(out_path)
    made = []

    def store(fmt_dir, w, ext, save_kwargs):
        d = os.path.join(base, fmt_dir, str(w) if w != W else "")
        os.makedirs(d, exist_ok=True)
        vpath = os.path.join(d, os.path.splitext(name)[0] + ext)
        if os.path.exists(vpath):
            return  # bereits vorhanden – nicht neu encodieren
        v = img if w == W else img.resize((w, int(H * w / W)), Image.LANCZOS)
        v.save(vpath, **save_kwargs)
        made.append(os.path.relpath(vpath, base))

    # WebP (immer)
    store("webp", W, ".webp", {"format": "WEBP", "quality": 80, "method": 6})
    store("webp", 620, ".webp", {"format": "WEBP", "quality": 80, "method": 6})
    store("webp", 720, ".webp", {"format": "WEBP", "quality": 80, "method": 6})

    # AVIF (nur wenn verfügbar)
    if AVIF_OK:
        for w in (W, 620, 720):
            store("avif", w, ".avif", {"format": "AVIF", "quality": 50, "speed": 6})

    return made


def load_font(size):
    """Versucht Montserrat Bold (Masterplan-Font), sonst DejaVuSans-Bold."""
    candidates = [
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        os.path.join(BLOG_DIR, "static", "fonts", "Montserrat-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Letzter Ausweg: Default-Font
    return ImageFont.load_default()


def wrap_text(text, font, max_width, draw):
    """Bricht Text in Zeilen um (max_width Pixel)."""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_cover(title, slug, out_path):
    W, H = 1000, 1500
    # Vertikaler Verlauf Smaragdgrün → dunkel
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        r = int(EMERALD[0] + (EMERALD_DARK[0] - EMERALD[0]) * t)
        g = int(EMERALD[1] + (EMERALD_DARK[1] - EMERALD[1]) * t)
        b = int(EMERALD[2] + (EMERALD_DARK[2] - EMERALD[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)

    d = ImageDraw.Draw(img)

    # Dezentes Punktmuster oben/unten
    for i in range(0, W, 40):
        for j in range(80, 220, 40):
            d.ellipse([i, j, i + 6, j + 6], fill=(255, 255, 255, 18))
    for i in range(0, W, 40):
        for j in range(H - 220, H - 80, 40):
            d.ellipse([i, j, i + 6, j + 6], fill=(255, 255, 255, 18))

    # Gelber Akzentbalken oben
    d.rounded_rectangle([120, 120, 180, 132], radius=6, fill=GOLD)

    # Titel (zentriert, automatischer Umbruch, Skalierung)
    title_font = load_font(78)
    margin = 90
    max_w = W - 2 * margin

    # Skaliere Schriftgröße, bis der Titel in max. 6 Zeilen passt
    for size in (78, 68, 58, 50, 44, 38, 32):
        title_font = load_font(size)
        lines = wrap_text(title, title_font, max_w, d)
        if len(lines) <= 6:
            break

    line_h = int(title_font.size * 1.25)
    total_h = len(lines) * line_h
    y_start = (H // 2) - (total_h // 2) - 60
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=title_font)
        x = (W - lw) / 2
        d.text((x, y_start + i * line_h), line, font=title_font, fill=WHITE)

    # Untertitel-Zeile: "Geld sparen & Frugalismus"
    sub_font = load_font(34)
    sub = "GELD SPAREN & FRUGALISMUS"
    sw = d.textlength(sub, font=sub_font)
    d.text(((W - sw) / 2, y_start + total_h + 50), sub, font=sub_font, fill=CREAM)

    # Footer: Branding + Pinterest-Pfeil-Symbol (simplifiziert)
    brand_font = load_font(40)
    brand = "FranksFinanzcheck"
    bw = d.textlength(brand, font=brand_font)
    d.text(((W - bw) / 2, H - 170), brand, font=brand_font, fill=GOLD)

    # Kleine Pins (pinterest-artige Punkte) unten
    for i, cx in enumerate([W // 2 - 60, W // 2, W // 2 + 60]):
        d.ellipse([cx - 7, H - 105, cx + 7, H - 91], fill=GOLD if i == 1 else (255, 255, 255, 120))

    img.save(out_path, "JPEG", quality=88)
    print(f"  ✓ Cover: {os.path.basename(out_path)}")

    # --- Responsive Varianten (srcset): 620px und 720px Breite ---
    # Die Covers werden in Listen (620px) und Single-Seiten (720px) angezeigt.
    # Ohne kleinere Varianten lädt der Browser immer das 1000px-Original →
    # Lighthouse "Properly size images". Die Varianten laufen über jsDelivr
    # (gleiche SHA-URLs → gleicher 1-Jahres-Cache).
    for variant_w in (620, 720):
        scale = variant_w / W
        vh = int(H * scale)
        v = img.resize((variant_w, vh), Image.LANCZOS)
        vdir = os.path.join(os.path.dirname(out_path), str(variant_w))
        os.makedirs(vdir, exist_ok=True)
        v.save(os.path.join(vdir, os.path.basename(out_path)), "JPEG", quality=82, optimize=True)
    print(f"  ✓ Responsive: 620px + 720px für {os.path.basename(out_path)}")

    # Moderne Formate (WebP + AVIF) für alle Größen
    modern = save_modern_variants(img, out_path)
    print(f"  ✓ Modern: {len(modern)} WebP/AVIF-Varianten für {os.path.basename(out_path)}")


def ensure_cover_in_frontmatter(md_path, slug):
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    if re.search(r"^cover:", content, re.M):
        return False  # Cover existiert bereits
    image_path = f"images/covers/{slug}.jpg"   # OHNE Slash: Hugo absURL + Subdir-BaseURL
    block = (
        f"cover:\n"
        f'  image: "{image_path}"\n'
        f'  alt: "Spar-Tipp: {slug.replace("-", " ").title()}"\n'
        f'  caption: "Tipp von FranksFinanzcheck"\n'
    )
    # Nach dem Frontmatter-Ende (---) einfügen, vor der ersten Inhaltszeile
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            content = parts[0] + "---" + parts[1] + block + "---" + parts[2]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def ensure_responsive_variants(out_path):
    """Erzeugt 620px-/720px-JPEGs und WebP/AVIF-Varianten für ein bestehendes
    Cover, falls fehlend (Nachzieh-Funktion für Bestandsbilder)."""
    if not os.path.exists(out_path):
        return False
    img = Image.open(out_path)
    W, H = img.size
    made = False
    # JPEG 620/720
    for variant_w in (620, 720):
        vpath = os.path.join(os.path.dirname(out_path), str(variant_w), os.path.basename(out_path))
        if not os.path.exists(vpath):
            scale = variant_w / W
            vh = int(H * scale)
            v = img.resize((variant_w, vh), Image.LANCZOS)
            os.makedirs(os.path.dirname(vpath), exist_ok=True)
            v.save(vpath, "JPEG", quality=82, optimize=True)
            made = True
    # WebP/AVIF (prüft intern, ob bereits vorhanden)
    modern = save_modern_variants(img, out_path)
    if modern:
        made = True
    if made:
        print(f"  ✓ Responsive/Modern-Varianten ergänzt: {os.path.basename(out_path)}")
    return made


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
    covers = 0
    frontmatter = 0
    variants = 0
    for fn in files:
        slug = fn[:-3]
        with open(os.path.join(POSTS_DIR, fn), encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        title = (m.group(1) if m else slug).strip()
        out_path = os.path.join(OUT_DIR, f"{slug}.jpg")
        if not os.path.exists(out_path):
            make_cover(title, slug, out_path)
            covers += 1
        if ensure_responsive_variants(out_path):
            variants += 1
        if ensure_cover_in_frontmatter(os.path.join(POSTS_DIR, fn), slug):
            frontmatter += 1
    print(f"\nFertig: {covers} Cover erstellt, {frontmatter} Frontmatter ergänzt, "
          f"{variants} responsive Varianten nachgezogen "
          f"(von {len(files)} Artikeln).")


if __name__ == "__main__":
    main()
