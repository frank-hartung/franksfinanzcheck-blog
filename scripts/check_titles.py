#!/usr/bin/env python3
"""
FrankAutoOps – Titel-Qualitätsgate (check_titles.py)

Prüft alle Blog-Titel (Überschrift + Cover-Text-Quelle) auf Qualitätsmuster
und korrigiert deterministische Fehler selbst (Self-Healing):

  R1 [Hinweis] Titel > 45 Zeichen ohne ":" und ohne "?" – der Cover-Umbruch
               (smart_wrap) bricht dann nur Wort für Wort; Konvention der
               Blog-Titel ist "Hauptkeyword: Untertitel".
  R2 [hart]    Anhängsel-Muster "dieses Jahr|diesen Jahres|dieses Monats"
               am Titelende OHNE Doppelpunkt – grammatisch lose Endung
               (Fall: "Riester Rente 2026 Weiterfördern oder kündigen
               dieses Jahr"). Titel mit solchen Endungen müssen von einem
               Menschen/Agenten umformuliert werden.
  R3 [fix]     Bekannte Komposita-Schreibfehler (deterministische Wortliste,
               z. B. "Riester Rente" -> "Riester-Rente"). Wird mit --fix
               automatisch korrigiert; bei Titeländerung wird das Cover
               (alle Varianten) neu gerendert.
  R4 [Hinweis] Cover-Layout-Simulation: Titel belegt auf dem Cover mehr als
               3 Zeilen oder eine Zeile breiter als 820 px -> Cover-Text
               überladen (wird bei Font 58 simuliert).

Nutzung:
    python3 scripts/check_titles.py            # Report + Exit-Code
    python3 scripts/check_titles.py --fix      # R3 + Cover-Neu-Render

Exit-Codes: 0 = sauber, 1 = nur Hinweise (nicht blockierend),
            2 = harte Verstöße (R2) -> Review nötig
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")

# ---------------------------------------------------------------------------
# R3: Deterministische Komposita-Schreibfehler (nur sichere, eindeutige Fälle)
# ---------------------------------------------------------------------------
KOMPOSITA_FIXES = [
    ("Riester Rente", "Riester-Rente"),
    ("Riester Vertrag", "Riester-Vertrag"),
    ("Riester Förderung", "Riester-Förderung"),
    ("ETF Sparplan", "ETF-Sparplan"),
    ("Kfz Versicherung", "Kfz-Versicherung"),
]

# R2: Lose Anhängsel am Titelende (ohne Doppelpunkt davor)
RE_ANHAENGSEL = re.compile(
    r"\s+(?:dieses Jahr|diesen Jahres|dieses Monats|diesen Monats)\s*$",
    re.IGNORECASE,
)

R1_LEN = 45  # Titel ab dieser Länge ohne ':'/'?' gelten als konventionsabweichend


def all_posts():
    return sorted(glob.glob(os.path.join(POSTS_DIR, "*", "index.md")))


def read_frontmatter_title(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
    return (m.group(1).strip() if m else None), content


def write_frontmatter_title(path, content, new_title):
    """Ersetzt title: im Frontmatter (nur erste Zeile, gequotet)."""
    new_content = re.sub(
        r'^title:\s*["\']?(.+?)["\']?\s*$',
        lambda m: f'title: "{new_title}"',
        content,
        count=1,
        flags=re.M,
    )
    # cover.alt nachziehen, falls er identisch mit dem alten Titel war
    old_title = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M).group(1).strip()
    new_content = new_content.replace(
        f'alt: "{old_title}"',
        f'alt: "{new_title}"',
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return old_title


def simulate_cover_layout(title):
    """R4: Simuliert smart_wrap bei Font 58 (typische Cover-Größe)."""
    try:
        from PIL import Image, ImageDraw
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        from generate_covers import load_font, smart_wrap

        img = Image.new("RGB", (1000, 1500))
        d = ImageDraw.Draw(img)
        font = load_font(58)
        if font is None:
            return None
        max_w = 1000 - 2 * 90
        lines = smart_wrap(title, font, max_w, d)
        over = [l for l in lines if d.textlength(l, font=font) > max_w]
        return len(lines), len(over), max_w
    except Exception:
        return None


def main():
    fix = "--fix" in sys.argv
    hard = 0
    hints = 0
    fixes = 0
    report = []

    for path in all_posts():
        slug = os.path.basename(os.path.dirname(path))
        title, content = read_frontmatter_title(path)
        if not title:
            continue
        orig = title

        # ---- R3: deterministische Komposita-Fixes (Self-Healing) ----
        new_title = title
        for wrong, right in KOMPOSITA_FIXES:
            if wrong in new_title:
                new_title = new_title.replace(wrong, right)
        if new_title != title:
            if fix:
                old = write_frontmatter_title(path, content, new_title)
                title = new_title
                fixes += 1
                report.append(f"  ✗ R3-FIX {slug}: '{old}' -> '{new_title}'")
            else:
                hard += 1
                report.append(f"  ✗ R3 {slug}: '{title}' (--fix korrigiert)")

        # ---- R2: lose Anhängsel ohne Doppelpunkt (hart) ----
        if ":" not in title and RE_ANHAENGSEL.search(title):
            hard += 1
            report.append(f"  ✗ R2 {slug}: '{title}' (Anhängsel-Muster, Review nötig)")

        # ---- R1: Konventions-Hinweis ----
        if len(title) > R1_LEN and ":" not in title and "?" not in title:
            hints += 1
            report.append(f"  • R1 {slug}: '{title}' ({len(title)} Z., kein ':' – Cover-Umbruch suboptimal)")

        # ---- R4: Cover-Layout-Simulation (Hinweis) ----
        layout = simulate_cover_layout(title)
        if layout:
            n_lines, n_over, max_w = layout
            if n_over > 0:
                hints += 1
                report.append(f"  • R4 {slug}: Cover-Zeile > {max_w} px bei Font 58")
            elif n_lines > 3:
                hints += 1
                report.append(f"  • R4 {slug}: Cover braucht {n_lines} Zeilen (Ziel <= 3)")

        # ---- Cover-Neu-Render bei Titeländerung (Self-Healing-Kette) ----
        if fix and new_title != orig:
            try:
                sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
                import generate_covers as gc

                out_path = os.path.join(gc.OUT_DIR, f"{slug}.jpg")
                if os.path.exists(out_path):
                    gc.make_cover(new_title, slug, out_path)
                    gc.ensure_responsive_variants(out_path, force=True)
                    report.append(f"  ✓ Cover neu gerendert: {slug} (alle Varianten)")
            except Exception as exc:  # noqa: BLE001
                report.append(f"  ⚠ Cover-Neu-Render fehlgeschlagen ({slug}): {exc}")

    # Report
    print("=" * 60)
    print(f"Titel-Gate: {len(all_posts())} Artikel geprüft")
    print(f"  harte Verstöße (R2/R3): {hard}")
    print(f"  Hinweise (R1/R4):       {hints}")
    if fixes:
        print(f"  Self-Healing-Fixes:    {fixes} (inkl. Cover-Neu-Render)")
    if report:
        print("-" * 60)
        print("\n".join(report))
    print("=" * 60)

    return 2 if hard else (1 if hints else 0)


if __name__ == "__main__":
    sys.exit(main())
