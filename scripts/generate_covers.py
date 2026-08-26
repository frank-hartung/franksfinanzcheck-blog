#!/usr/bin/env python3
"""
Generiert für jeden Blog-Artikel ein Branding-Cover (Smaragdgrün/Gelb –
Stil des Pinterest-Masterplans) und trägt es ins Frontmatter ein.

- Bilder: static/images/covers/<slug>.jpg (1000x1500, 2:3 – Pinterest-Format)
- Frontmatter: cover.image, cover.alt, cover.caption (nur falls noch keins existiert)
- Das Theme rendert das Cover im Artikel und als og:image

PREMIUM-DESIGN (Upgrade 25.08.2026, DESIGN_VERSION 3):
- Pillar-Badge: „STROM & GAS SPAREN", „INTERNET & DSL" etc. statt generisch
  (Quelle: Frontmatter `pillar:`, Fallback: Keyword-Scan von Slug/Titel)
- Gold-Zahlen im Titel („5 Tricks", „800 €", „50-30-20-Regel")
- Goldene Spar-Pille unter dem Titel – aus description/title auto-erkannt
  („bis zu 800 € …" nur MIT Spar-Kontext) ODER wörtlich via Frontmatter:
  `savings: "bis zu 300 € im Jahr sparen"` (max. ~30 Zeichen empfohlen)
- Trust-Line über dem Brand-Band, dezente Premium-Vignette im Verlauf
- Design-Drift: Ändern sich Badge/Pille/Version, rendert der nächste Lauf
  das Cover automatisch neu (Fingerprint in data/covers_manifest.json)

Nutzung:
    python3 scripts/generate_covers.py                  # neue + gedriftete Cover
    python3 scripts/generate_covers.py --force          # ALLE neu rendern
    python3 scripts/generate_covers.py --slug <slug>    # einzelnes Cover neu
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


def manifest_set(slug, title, design=None):
    m = load_manifest()
    entry = {"title": title,
             "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
    if design is not None:
        # Design-Fingerprint (Premium 25.08.): Badge/Spar-Pille/Version.
        # Abweichung = Design-Drift → Cover wird neu gerendert.
        entry["design"] = design
    m[slug] = entry
    save_manifest(m)


# --- Farben aus dem Masterplan ---
EMERALD = (14, 90, 67)        # Smaragdgrün
EMERALD_DARK = (8, 58, 43)    # dunkleres Grün für Verlauf
GOLD = (255, 179, 0)          # Signalgelb
WHITE = (255, 255, 255)
CREAM = (240, 245, 242)

# --- Premium-Upgrade 25.08.2026 (Pinterest-Agentur-Paket) ----------------
# DESIGN_VERSION hochzählen, wenn sich das Design ändert: Der nächste Lauf
# (auch OHNE --force) rendert betroffene Cover automatisch neu (Design-Drift
# wird über data/covers_manifest.json erkannt).
DESIGN_VERSION = 3
INK = (7, 46, 34)             # tiefes Emerald (Brand-Band, Text auf Gold-Pille)
VIGNETTE = 0.14               # Premium-Tiefe: dezente Randabdunklung (0=aus)

# Pillar-Badges: Das Badge spricht die Sprache des Silos statt generisch
# „GELD SPAREN" (Fix des Befunds: DSL-Cover trug „FRUGALISMUS"-Badge).
# Quelle 1: Frontmatter-Feld `pillar:` (Single Source of Truth).
# Quelle 2 (Fallback): Keyword-Scan aus Slug+Titel, Reihenfolge = Priorität.
PILLAR_BADGES = {
    "strom-sparen": "STROM & GAS SPAREN",
    "internet-dsl": "INTERNET & DSL",
    "versicherungen": "VERSICHERUNGEN",
    "mietwagen": "GÜNSTIG REISEN",
    "konto-karten": "KONTO & FINANZEN",
    "frugalismus": "GELD SPAREN & FRUGALISMUS",
}
FALLBACK_BADGE = "GELD SPAREN & FRUGALISMUS"
BADGE_KEYWORDS = [
    (("strom", "gas", "energie", "heiz", "kwh"), "STROM & GAS SPAREN"),
    (("dsl", "internet", "wlan", "wi-fi", "fritzbox", "dns", "handy", "glasfaser"), "INTERNET & DSL"),
    (("versicherung", "kfz", "haftpflicht", "gebaeude", "gebäude", "police"), "VERSICHERUNGEN"),
    (("mietwagen", "reise", "urlaub", "flug", "hotel"), "GÜNSTIG REISEN"),
    (("girokonto", "konto", "kreditkarte", "tagesgeld", "kredit", "zins"), "KONTO & FINANZEN"),
    (("frugal", "sparen", "budget", "haushaltsbuch", "notgroschen", "50-30-20", "gehalt"), "GELD SPAREN & FRUGALISMUS"),
]

# Spar-Kontext: Nur mit einem dieser Signale darf eine Gold-Pille gerendert
# werden – Guard gegen falsche Versprechen (siehe extract_savings).
_SPAR_CTX = re.compile(
    r"spar|ersparn|bonus|prämie|praemie|cashback|rabatt|günstig|guenstig|"
    r"gratis|kostenlos|senk|reduzier|weniger|wechselbonus", re.I)

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


def detect_badge(pillar, slug, title):
    """Pillar-Badge bestimmen (Premium 25.08.). Quelle 1: Frontmatter
    `pillar:`. Quelle 2: Keyword-Scan aus Slug+Titel."""
    p = (pillar or "").strip().lower()
    if p in PILLAR_BADGES:
        return PILLAR_BADGES[p]
    hay = f"{slug} {title}".lower()
    for keys, label in BADGE_KEYWORDS:
        if any(k in hay for k in keys):
            return label
    return FALLBACK_BADGE


def _pill_period(text):
    """Zeitraum für die Pille erkennen (Premium-Genauigkeit: nie „im Jahr"
    behaupten, wenn „im Monat" gemeint ist). Wortgrenzen beachten – ein
    nacktes „pa" (z. B. in „sparen") ist KEIN „p. a."!"""
    if re.search(r"pro\s+jahr|im\s+jahr|j[aä]hrlich|\bp\.\s?a\.", text, re.I):
        return " im Jahr"
    if re.search(r"pro\s+monat|im\s+monat|monatlich", text, re.I):
        return " im Monat"
    return ""


def _amount_in_title(candidate, title):
    """True, wenn die im Pillen-Text genannte Zahl+Einheit bereits (fast
    wörtlich) im Titel steht – dann entfällt die Pille, denn der Titel
    hebt den Betrag ohnehin GOLD hervor (Doppelung = unprofessionell)."""
    m = re.search(r"(\d[\d\.\,]*)\s*(€|%)", candidate or "")
    if not (m and title):
        return False
    return bool(re.search(re.escape(m.group(1)) + r"\s*" + re.escape(m.group(2)), title))


def extract_savings(title, description, explicit=None):
    """Konkrete Spar-Zahl für die Gold-Pille (Premium-Hebel Nr. 1).

    Priorität:
      1) Frontmatter `savings:` – wird WÖRTLICH übernommen (volle Kontrolle,
         z. B. `savings: "bis zu 300 € im Jahr sparen"`).
      2) Auto-Erkennung in description/title: „bis zu 800 €" bzw.
         „bis zu 40 Prozent" NUR mit Spar-/Wert-Kontext (Guard gegen falsche
         Versprechen – aus „Tarif ab 9,99 €" wird nie ein Spar-Claim).
         Zins-Kontext wird als Rendite-Pille („… Zinsen") gerendert.
         Zeitraum („im Jahr"/„im Monat") wird präzise übernommen.
    Dedupe-Regel: Steht der Betrag bereits im Titel, gibt es KEINE Pille.
    Rückgabe: kurzer Pillen-Text (max. ~32 Zeichen) oder None."""
    if explicit and explicit.strip():
        pill = explicit.strip()
        return None if _amount_in_title(pill, title) else pill
    for text in (description or "", title or ""):
        if not text:
            continue
        pill = None
        m = re.search(r"bis\s+zu\s+(\d[\d\.\,]*)\s*€", text, re.I)
        if m:
            if re.search(r"zins", text, re.I) and not _SPAR_CTX.search(text):
                pill = f"bis zu {m.group(1)} € Zinsen"
            elif _SPAR_CTX.search(text):
                pill = f"bis zu {m.group(1)} €{_pill_period(text)} sparen"
        else:
            m = re.search(r"bis\s+zu\s+(\d[\d\.\,]*)\s*(?:%|prozent)", text, re.I)
            if m and re.search(r"zins", text, re.I):
                pill = f"bis zu {m.group(1)} % Zinsen"
            elif m and _SPAR_CTX.search(text):
                pill = f"bis zu {m.group(1)} % sparen"
        if pill:
            if _amount_in_title(pill, title):
                continue   # Betrag steht schon gold im Titel → keine Pille
            return pill
    return None


# Wörter, vor denen eine Zahl auf dem Cover GOLD gesetzt wird
# („5 Tricks", „7 Gewohnheiten" – die Listen-Zahl ist der Blickfang).
EMPH_FOLLOW = {
    "tricks", "tipps", "schritte", "gewohnheiten", "fehler", "wege", "regel",
    "regeln", "fragen", "fakten", "gründe", "gruende", "methoden", "ideen",
    "hacks", "fallen", "geheimnisse", "signale", "checkliste", "punkte",
    "gründen", "energiediebe", "kostenfallen", "schritte",
}
_NUM_TOKEN = re.compile(r"\d+(?:[\.,:/\-–]\d+)*(?:\s*[€%])?")


def title_tokens(line):
    """Zerlegt eine Titelzeile in (wort, ist_gold)-Tokens (Premium 25.08.).

    Gold werden: „300 €" / „40 %" (Zahl + Einheit), Listen-Zahlen vor
    Schlüsselwörtern („5 Tricks") und Bindestrich-Serien wie „50-30-20-Regel".
    """
    words = line.split(" ")
    cores = [w.strip(":;,.!?()“„”\"'") for w in words]
    gold = [False] * len(words)
    for i, core in enumerate(cores):
        nxt = cores[i + 1].lower() if i + 1 < len(words) else ""
        if _NUM_TOKEN.fullmatch(core):
            if core.endswith(("€", "%")):
                gold[i] = True
            elif nxt in ("€", "%", "prozent", "euro"):
                gold[i] = True
            elif nxt in EMPH_FOLLOW:
                gold[i] = True
        elif core == "€" and i > 0 and _NUM_TOKEN.fullmatch(cores[i - 1]):
            gold[i] = True
        elif re.fullmatch(r"\d+(?:-\d+)+-[A-Za-zÄÖÜäöüß]+", core):
            gold[i] = True   # „50-30-20-Regel" komplett golden
    return list(zip(words, gold))


def make_cover(title, slug, out_path, force=False, badge=None, savings=None):
    W, H = 1000, 1500
    # Vertikaler Verlauf Smaragdgrün → dunkel + dezente Premium-Vignette
    # (Randabdunklung für Tiefe). WICHTIG: Farben werden VORMISCHEND
    # berechnet – kein Alpha (siehe Punktmuster-Lektion unten)!
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        r = EMERALD[0] + (EMERALD_DARK[0] - EMERALD[0]) * t
        g = EMERALD[1] + (EMERALD_DARK[1] - EMERALD[1]) * t
        b = EMERALD[2] + (EMERALD_DARK[2] - EMERALD[2]) * t
        dy = 2.0 * y / H - 1.0
        for x in range(W):
            dx = 2.0 * x / W - 1.0
            f = 1.0 - VIGNETTE * (dx * dx + dy * dy) / 2.0
            px[x, y] = (int(r * f), int(g * f), int(b * f))

    d = ImageDraw.Draw(img)

    # KEIN Punktmuster mehr (Frank 12.08., Runde 2: Punkte stoeren → raus).
    # Lektion: alpha=(255,255,255,18) wurde im RGB-Modus still verworfen und
    # renderte die Dots KNALLWEISS statt dezent. Konsequent FLAECHENFREI.
    #
    # Profi-Hierarchie (Pinterest-Look): Pillar-Badge oben (semantisch
    # statt dekorativ) → Titel Mitte (mit Gold-Zahlen) → Spar-Pille →
    # Trust-Line → Marke unten im Signet-Band.
    badge_txt = badge or FALLBACK_BADGE
    badge_font = load_font(26)
    btw = d.textlength(badge_txt, font=badge_font)
    for bsize in (26, 24, 22, 20):
        badge_font = load_font(bsize)
        btw = d.textlength(badge_txt, font=badge_font)
        if btw + 2 * 30 <= W - 160:
            break
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
    # ACHTUNG Brand-Gate (check_covers.py C2/C2b): Positionen von Band,
    # Gold-Linie, Haeckchen und „check" hier NICHT veraendern!
    band_y0 = H - 300
    d.rectangle([0, band_y0, W, H], fill=INK)                     # sehr tiefes Gruen
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

    # ABSOLUTE-CLIP-PROOF (26.08.2026): Der Cover-Text darf NIEMALS aus
    # dem Bild laufen. Selbst wenn Wort-Umbruch scheitert (ein einziges
    # Wort > max_w), wird die Zeile zeichenweise getrennt. Dies ist die
    # allerletzte Notstufe – bei den üblichen Titeln (≤ 60 Zeichen,
    # safe_title_cut) wird sie nie erreicht.
    for i, l in enumerate(lines):
        if d.textlength(l, font=title_font) > max_w:
            parts, cur = [], ""
            for ch in l:
                if cur and d.textlength(cur + ch, font=title_font) > max_w:
                    parts.append(cur)
                    cur = ch
                else:
                    cur += ch
            if cur:
                parts.append(cur)
            lines[i:i + 1] = parts

    line_h = int(title_font.size * 1.25)
    total_h = len(lines) * line_h

    # Trust-Line (Premium 25.08.): E-E-A-T direkt über dem Brand-Band.
    # Wird nur gezeichnet, wenn Titel+Pille genug Abstand lassen.
    trust_font = load_font(26)
    trust_txt = "UNABHÄNGIG · VERSTÄNDLICH · MIT ECHTEN ZAHLEN"
    trust_sign = 26
    trust_gap = 16
    ttw = d.textlength(trust_txt, font=trust_font)
    trust_total = trust_sign + trust_gap + ttw
    trust_y = band_y0 - 70

    # Spar-Pille vorbereiten (Premium-Hebel Nr. 1: die konkrete Euro-Zahl)
    pill_text = (savings or "").strip()
    pill_font = None
    if pill_text:
        for psize in (58, 52, 46, 40, 34):
            pf = load_font(psize)
            if d.textlength(pill_text, font=pf) + 2 * 46 <= W - 160:
                pill_font = pf
                break
    pill_gap = 58 if pill_font else 0
    pill_box_h = (pill_font.size + 2 * 22) if pill_font else 0

    # Gesamtblock (Titel + Pille) optisch zentriert in der Zone zwischen
    # Badge und Trust-Line:
    zone_top = badge_y + bh_box + 26        # Badge (endet ~y=202) + Luft
    zone_bottom = trust_y - 30              # oberhalb der Trust-Line
    block_h = total_h + pill_gap + pill_box_h
    # CLAMP (26.08.2026): Bei pathologisch hohen Blöcken (sehr viele
    # Zeilen + Pille) darf der Block die Zone nicht nach OBEN verlassen –
    # sonst würde der obere Titeltext unter das Badge laufen/abgeschnitten.
    y_start = max((zone_top + zone_bottom) // 2 - block_h // 2, zone_top + 4)

    # Titel zeichnen – mit GOLD-Akzenten auf Zahlen („5 Tricks", „800 €"),
    # Premium-Blickfang im Feed. Wortweise, damit die Zentrierung exakt bleibt.
    sp = d.textlength(" ", font=title_font)
    y_text = y_start
    for line in lines:
        toks = title_tokens(line)
        widths = [d.textlength(wd, font=title_font) for wd, _ in toks]
        line_w = sum(widths) + sp * (len(toks) - 1)
        x = (W - line_w) / 2
        for (wd, gld), wpx in zip(toks, widths):
            d.text((x, y_text), wd, font=title_font,
                   fill=GOLD if gld else WHITE)
            x += wpx + sp
        y_text += line_h

    content_bottom = y_text - 24

    # Goldene Spar-Pille unter dem Titel (mit Solid-Schatten, KEIN Alpha!)
    if pill_font:
        pt_w = d.textlength(pill_text, font=pill_font)
        px_pad, py_pad = 46, 20
        pw, ph = pt_w + 2 * px_pad, pill_font.size + 2 * py_pad
        cx0 = (W - pw) / 2
        py0 = y_text + pill_gap - 24
        d.rounded_rectangle([cx0, py0 + 7, cx0 + pw, py0 + ph + 7],
                            radius=ph / 2, fill=(5, 36, 27))
        d.rounded_rectangle([cx0, py0, cx0 + pw, py0 + ph],
                            radius=ph / 2, fill=GOLD)
        d.text((cx0 + px_pad, py0 + py_pad - 3), pill_text,
               font=pill_font, fill=INK)
        content_bottom = py0 + ph + 7

    # Trust-Line zeichnen (nur wenn kein Overlap mit Titel/Pille)
    if trust_y > content_bottom + 26:
        tx0 = (W - trust_total) / 2
        cyy = trust_y
        d.line([(tx0 + 3, cyy + trust_sign * 0.52),
                (tx0 + trust_sign * 0.42, cyy + trust_sign - 4),
                (tx0 + trust_sign, cyy + 1)],
               fill=GOLD, width=6, joint="curve")
        d.text((tx0 + trust_sign + trust_gap, trust_y - 3), trust_txt,
               font=trust_font, fill=CREAM)

    img.save(out_path, "JPEG", quality=88)
    extra = f" [Pille: {pill_text}]" if (pill_font and pill_text) else ""
    print(f"  ✓ Cover: {os.path.basename(out_path)}{extra}")

    # Responsive Varianten + moderne Formate über das zentrale Profi-Tool.
    # Mobile: 360/480, Desktop: 620/720, Full-Fallback: 1000 WebP/AVIF.
    modern = save_modern_variants(img, out_path, force=force)
    print(f"  ✓ Responsive/Modern: {len(modern)} Varianten für {os.path.basename(out_path)}")


def _title_from_content(content):
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
    if not m:
        return None
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def ensure_cover_in_frontmatter(md_path, slug, title=None):
    """Legt Cover-Frontmatter an ODER heilt generische Alt-Texte.

    Alt-Text = Artikel-Titel (keywordreich, natürlich) – nie „Spar-Tipp: 2026…".
    """
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    plain_title = title or _title_from_content(content) or slug.replace("-", " ")
    plain_title = re.sub(r"<[^>]+>", "", plain_title).strip()
    image_path = f"images/covers/{slug}.jpg"   # OHNE Slash: Hugo absURL + Subdir-BaseURL

    if re.search(r"^cover:", content, re.M):
        # Alt heilen wenn generisch/slug-basiert
        m_alt = re.search(r'^(\s*alt:\s*)["\']?(.+?)["\']?\s*$', content, re.M)
        if m_alt:
            old_alt = m_alt.group(2).strip()
            # Nur generische/slug-basierte Alts heilen – bewusst keywordreiche
            # Alt-Texte (z. B. szenische Beschreibungen) bleiben erhalten.
            bad = (
                old_alt.startswith("Spar-Tipp:")
                or old_alt == "Tipp von FranksFinanzcheck"
                or re.search(r"\b20\d{2}\s+0\d\s+\d{2}\b", old_alt)
                or (plain_title and len(old_alt) < 12)
            )
            if bad and plain_title:
                content = (
                    content[: m_alt.start()]
                    + f'{m_alt.group(1)}"{plain_title}"'
                    + content[m_alt.end():]
                )
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
        return False
    block = (
        f"cover:\n"
        f'  image: "{image_path}"\n'
        f'  alt: "{plain_title}"\n'
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
        # Premium 25.08.: Pillar-Badge + Spar-Pille automatisch ableiten.
        # Frontmatter-Override: `pillar: "strom-sparen"` (Badge) und
        # `savings: "bis zu 300 € im Jahr sparen"` (Pille, wörtlich).
        desc_m = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        pillar_m = re.search(r'^pillar:\s*["\']?([\w\-]+)["\']?\s*$', content, re.M)
        savings_m = re.search(r'^savings:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        badge = detect_badge(pillar_m.group(1) if pillar_m else None, slug, title)
        savings = extract_savings(title,
                                  desc_m.group(1) if desc_m else "",
                                  savings_m.group(1) if savings_m else None)
        design = {"v": DESIGN_VERSION, "badge": badge, "savings": savings or ""}
        design_drift = load_manifest().get(slug, {}).get("design") != design
        out_path = os.path.join(OUT_DIR, f"{slug}.jpg")
        if force or only_slug or not os.path.exists(out_path) or design_drift:
            make_cover(title, slug, out_path,
                       force=force or bool(only_slug) or design_drift,
                       badge=badge, savings=savings)
            covers += 1
        if ensure_responsive_variants(out_path, force=force or bool(only_slug) or design_drift):
            variants += 1
        if ensure_cover_in_frontmatter(path, slug, title=title):
            frontmatter += 1
        if only_slug or force or slug not in load_manifest():
            # Einzel-Lauf/Force: Manifest immer aktualisieren; Gesamtlauf:
            # fehlende Einträge nachtragen (Stale-Erkennung lückenlos).
            manifest_set(slug, title, design=design)
        else:
            # Auch bei bestehendem Cover: Manifest-Titel + Design-Fingerprint
            # syncen (Stale- bzw. Drift-Erkennung braucht aktuelle Werte)
            m = load_manifest()
            if m.get(slug, {}).get("title") != title or design_drift:
                manifest_set(slug, title, design=design)
    try:
        from lcp_image_optimizer import build_manifest as build_lcp_manifest, write_manifest as write_lcp_manifest
        write_lcp_manifest(build_lcp_manifest())
        print("  ✓ LCP-Manifest aktualisiert (data/lcp_images.json)")
    except Exception as exc:
        print(f"WARNUNG: LCP-Manifest konnte nicht aktualisiert werden: {exc}")
    try:
        from fcp_image_optimizer import build_manifest as build_fcp_manifest, write_manifest as write_fcp_manifest
        write_fcp_manifest(build_fcp_manifest())
        print("  ✓ FCP-Manifest aktualisiert (data/fcp_images.json)")
    except Exception as exc:
        print(f"WARNUNG: FCP-Manifest konnte nicht aktualisiert werden: {exc}")

    print(f"\nFertig: {covers} Cover erstellt, {frontmatter} Frontmatter ergänzt, "
          f"{variants} responsive Varianten nachgezogen "
          f"(von {len(files)} Artikeln).")


if __name__ == "__main__":
    main()
