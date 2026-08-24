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
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths, slug_of
OUT_DIR = os.path.join(BLOG_DIR, "static", "images", "covers")
MANIFEST_PATH = os.path.join(BLOG_DIR, "data", "covers_manifest.json")

# --- Cover-Manifest (Stale-Erkennung) --------------------------------------
# data/covers_manifest.json: { "<slug>": {"title": "<Titel bei Generierung>",
#                                          "ts": "<ISO-Zeitstempel>"} }
# check_covers.py vergleicht den aktuellen Frontmatter-Titel mit dem
# Manifest-Eintrag. Weicht er ab, wurde der Titel geändert, ohne das Cover
# neu zu rendern → Cover zeigt veralteten Text (Selbstheilung: --fix).
import json
import datetime as _dt


def load_manifest():
    try:
        return json.load(open(MANIFEST_PATH, encoding="utf-8"))
    except Exception:
        return {}


def save_manifest(manifest):
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    tmp = MANIFEST_PATH + ".tmp"
    json.dump(manifest, open(tmp, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    os.replace(tmp, MANIFEST_PATH)


def manifest_set(slug, title):
    m = load_manifest()
    m[slug] = {"title": title,
               "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    save_manifest(m)


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


def save_modern_variants(img, out_path, force=False):
    """Erzeugt responsive JPEG/WebP/AVIF-Varianten über das zentrale
    Profi-Tool scripts/image_optimizer.py.

    Damit haben Cover-Generierung, CI-Checks und Theme-Templates exakt dieselbe
    Breiten-/Qualitätslogik für Mobile und Desktop.
    """
    try:
        from image_optimizer import optimize_cover_image
    except Exception as exc:
        print(f"WARNUNG: image_optimizer konnte nicht geladen werden: {exc}")
        return []
    return optimize_cover_image(out_path, image=img, force=force)


def load_font(size):
    """Cover-Font: nur Inter Bold (Frank-Wahl 11.08. spaet - das ruhige G)."""
    candidates = [
        os.path.join(BLOG_DIR, "static", "fonts", "Inter-Bold.ttf"),
        "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Sabotage-Schutz: NIEMALS auf einen anderen Font ausweichen - lieber
    # laut scheitern als leise falsch branden (Lektion vom "G bei Geld").
    print("🛑 FONT-PACT VERLETZT: static/fonts/Inter-Bold.ttf fehlt!")
    print("   Kein Cover wird falsch gerendert. `python3 scripts/bake_fonts.py --file Inter-Bold.ttf` zuerst.")
    sys.exit(2)


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


# Präpositionen/Konjunktionen, die NIE am Zeilenende stehen dürfen
# (hängende Zeilen wirken unprofessionell auf den Cover-Bildern).
NO_LINE_END = {
    "ab", "als", "am", "an", "auch", "auf", "aufs", "aus", "bei", "beim", "bis", "das", "den", "der", "die", "durch", "ein", "eine", "einer", "für", "gegen", "im", "in", "ins", "mit", "nach", "oder", "ohne", "seit", "sich", "um", "und", "unter", "vom", "von", "vor", "wegen", "zum", "zur", "zwischen", "über",
}


def wrap_text_no_hang(text, font, max_width, draw):
    """Wie wrap_text, aber ohne hängende Präpositionen am Zeilenende."""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                # Letztes Wort der Zeile ist eine Präposition → in nächste
                # Zeile verschieben (außer die Zeile bestünde dann nur aus
                # diesem einen Wort).
                parts = cur.split()
                if len(parts) > 1 and parts[-1].strip(":;,.!?") in NO_LINE_END:
                    lines.append(" ".join(parts[:-1]))
                    cur = parts[-1] + " " + w
                else:
                    lines.append(cur)
                    cur = w
            else:
                cur = w
    if cur:
        lines.append(cur)
    return lines


def smart_wrap(title, font, max_width, draw):
    """Semantischer Titel-Umbruch für Cover (dauerhafte Regel):

    1) BEVORZUGT nach dem ersten Doppelpunkt brechen – alle Blog-Titel
       folgen dem Muster "Hauptkeyword: Untertitel" (z. B. "Flug buchen:
       9 Tricks für günstige Flugtickets"). Der Teil vor dem Doppelpunkt
       (inkl. ":") wird zur ersten Zeile, der Rest danach umgebrochen.
    2) Fallback: Wort-Umbruch ohne hängende Präpositionen.
    """
    if ":" in title:
        head, tail = title.split(":", 1)
        head = head.strip() + ":"
        tail = tail.strip()
        # Kopf (inkl. Doppelpunkt) muss in eine Zeile passen
        if draw.textlength(head, font=font) <= max_width:
            tail_lines = wrap_text_no_hang(tail, font, max_width, draw)
            # Balance: Kopf + max. 4 Folgezeilen ist ok (Cover-Design)
            if len(tail_lines) <= 4:
                return [head] + tail_lines
    return wrap_text_no_hang(title, font, max_width, draw)


def make_cover(title, slug, out_path, force=False):
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

    # KEIN Punktmuster mehr (Frank 12.08., Runde 2: Punkte stoeren → raus).
    # Lektion: alpha=(255,255,255,18) wurde im RGB-Modus still verworfen und
    # renderte die Dots KNALLWEISS statt dezent. Konsequent FLAECHENFREI.
    #
    # Profi-Hierarchie (Pinterest-Look): Kategorie-Badge oben (semantisch
    # statt dekorativ) → Titel Mitte → Marke unten im Signet-Band.
    badge_font = load_font(26)
    badge_txt = "GELD SPAREN & FRUGALISMUS"
    btw = d.textlength(badge_txt, font=badge_font)
    bth = badge_font.size
    pad_x, pad_y = 30, 13
    bw_box, bh_box = btw + 2 * pad_x, bth + 2 * pad_y
    bx0 = (W - bw_box) / 2
    badge_y = 150
    d.rounded_rectangle([bx0, badge_y, bx0 + bw_box, badge_y + bh_box],
                        radius=bh_box / 2, outline=GOLD, width=3)
    d.text((bx0 + pad_x, badge_y + pad_y - 4), badge_txt, font=badge_font, fill=GOLD)

    # Brand-Zone unten: tiefes, fast schwarzes Emerald-Band + klare
    # Wortmarke mit goldenem Haeckchen-Signet (FinanzCHECK!).
    band_y0 = H - 300
    d.rectangle([0, band_y0, W, H], fill=(7, 46, 34))            # sehr tiefes Gruen
    d.line([(0, band_y0), (W, band_y0)], fill=GOLD, width=6)     # kraeftige Gold-Fuehrung

    brand_font = load_font(68)
    part1, part2 = "FranksFinanz", "check"
    w1 = d.textlength(part1, font=brand_font)
    w2 = d.textlength(part2, font=brand_font)
    sign = 56                       # Hoehe des Haeckchen-Signets
    gap = 28
    total_w = sign + gap + w1 + w2
    x0 = (W - total_w) / 2
    cy = band_y0 + (H - band_y0) // 2 + 8
    # Goldenes Haeckchen mit rundem Gelenk (joint="curve") als Logo-Zeichen
    hx, hy = x0, cy - sign // 2
    d.line([(hx + 4, hy + sign * 0.54),
            (hx + sign * 0.42, hy + sign - 5),
            (hx + sign, hy + 2)],
           fill=GOLD, width=12, joint="curve")
    # Wortmarke, vertikal auf das Haeckchen zentriert
    ty = cy - brand_font.size * 0.66
    d.text((x0 + sign + gap, ty), part1, font=brand_font, fill=WHITE)
    d.text((x0 + sign + gap + w1, ty), part2, font=brand_font, fill=GOLD)

    # Titel (zentriert, automatischer Umbruch, Skalierung)
    title_font = load_font(78)
    margin = 90
    max_w = W - 2 * margin

    # Skaliere Schriftgröße: ZIEL max. 3 Zeilen (gute Balance, kompakte
    # Covers) UND keine Zeile breiter als max_w (lange Wörter wie
    # „Reisekrankenversicherung:“ dürfen NICHT über den Rand laufen).
    # smart_wrap bricht semantisch um (bevorzugt nach dem Doppelpunkt).
    # Fallback: nie mehr als 6 Zeilen (sehr lange Titel).
    for size in (78, 68, 58, 50, 44, 38, 32):
        title_font = load_font(size)
        lines = smart_wrap(title, title_font, max_w, d)
        # Abbruch nur, wenn ALLE Zeilen in die Breite passen
        if len(lines) <= 3 and all(d.textlength(l, font=title_font) <= max_w for l in lines):
            break
    if len(lines) > 6 or any(d.textlength(l, font=title_font) > max_w for l in lines):
        # Letzte Rettung: kleinste Schrift, längste Wörter ggf. hart trennen
        title_font = load_font(32)
        lines = smart_wrap(title, title_font, max_w, d)
        if any(d.textlength(l, font=title_font) > max_w for l in lines):
            # Wort-Hyphenation als allerletzte Option (nur bei Übergrößen)
            lines = wrap_text_no_hang(title, title_font, max_w, d)

    line_h = int(title_font.size * 1.25)
    total_h = len(lines) * line_h
    # Titel optisch zentriert im Raum zwischen Badge (endet ~y=202) und Band:
    zone_top, zone_bottom = 202, band_y0
    y_start = (zone_top + zone_bottom) // 2 - total_h // 2 - 20
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=title_font)
        x = (W - lw) / 2
        d.text((x, y_start + i * line_h), line, font=title_font, fill=WHITE)

    img.save(out_path, "JPEG", quality=88)
    print(f"  ✓ Cover: {os.path.basename(out_path)}")

    # Responsive Varianten + moderne Formate über das zentrale Profi-Tool.
    # Mobile: 360/480, Desktop: 620/720, Full-Fallback: 1000 WebP/AVIF.
    modern = save_modern_variants(img, out_path, force=force)
    print(f"  ✓ Responsive/Modern: {len(modern)} Varianten für {os.path.basename(out_path)}")


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


def ensure_responsive_variants(out_path, force=False):
    """Erzeugt Mobile-/Desktop-JPEGs und WebP/AVIF-Varianten für ein bestehendes
    Cover. Ohne force nur falls fehlend (Nachzieh-Funktion); mit force werden
    ALLE Varianten neu aus der (ggf. neu generierten) JPG erzeugt – wichtig,
    wenn sich die Cover-Generierung (z. B. Titel-Umbruch) geändert hat."""
    if not os.path.exists(out_path):
        return False
    img = Image.open(out_path).convert("RGB")
    modern = save_modern_variants(img, out_path, force=force)
    return bool(modern)


def main():
    force = "--force" in sys.argv  # alle Covers neu generieren (neue Umbruch-Regel)
    only_slug = None
    if "--slug" in sys.argv:
        i = sys.argv.index("--slug")
        if i + 1 < len(sys.argv):
            only_slug = sys.argv[i + 1].strip()
    os.makedirs(OUT_DIR, exist_ok=True)
    files = list_post_paths()
    covers = 0
    frontmatter = 0
    variants = 0
    for path in files:
        slug = slug_of(path)
        if only_slug and slug != only_slug:
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        title = (m.group(1) if m else slug).strip()
        out_path = os.path.join(OUT_DIR, f"{slug}.jpg")
        if force or only_slug or not os.path.exists(out_path):
            make_cover(title, slug, out_path, force=force or bool(only_slug))
            covers += 1
        if ensure_responsive_variants(out_path, force=force or bool(only_slug)):
            variants += 1
        if ensure_cover_in_frontmatter(path, slug):
            frontmatter += 1
        if only_slug or force or slug not in load_manifest():
            # Einzel-Lauf/Force: Manifest immer aktualisieren; Gesamtlauf:
            # fehlende Einträge nachtragen (Stale-Erkennung lückenlos).
            manifest_set(slug, title)
    try:
        from lcp_image_optimizer import build_manifest as build_lcp_manifest, write_manifest as write_lcp_manifest
        write_lcp_manifest(build_lcp_manifest())
        print("  ✓ LCP-Manifest aktualisiert (data/lcp_images.json)")
    except Exception as exc:
        print(f"WARNUNG: LCP-Manifest konnte nicht aktualisiert werden: {exc}")

    print(f"\nFertig: {covers} Cover erstellt, {frontmatter} Frontmatter ergänzt, "
          f"{variants} responsive Varianten nachgezogen "
          f"(von {len(files)} Artikeln).")


if __name__ == "__main__":
    main()
