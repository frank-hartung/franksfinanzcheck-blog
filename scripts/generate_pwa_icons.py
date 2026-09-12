#!/usr/bin/env python3
"""generate_pwa_icons.py – PWA-Grundlage: Manifest + Icons (deterministisch).

Warum (Premium-Audit 11.09.2026):
Die Site registriert seit Monaten einen Service Worker (layouts/index.sw.js,
Caching, Offline-Fallback) – aber es gab KEIN Manifest. Ein Service Worker ohne
Manifest ist die halbe Miete: Chrome/Edge zeigen dadurch nie den
„Zum Startbildschirm hinzufügen"-Dialog, iOS startet nicht im Vollbild, und
die Adresszeile frisst auf Mobilgeräten genau den Raum, den der
Lesehilfen-Block braucht. Für eine Seite, deren Traffic zu 100 % von
Pinterest und Suche kommt (Einmal-Klick-Publikum), ist der Startbildschirm-
Shortcut der billigste Rückhol-Kanal, den es gibt.

Das Skript ist der Single Source of Truth für:
  static/manifest.json                    (Manifest, aus hugo.toml abgeleitet)
  static/images/pwa/icon-192.png          (192×192, any)
  static/images/pwa/icon-512.png          (512×512, any)
  static/images/pwa/icon-maskable-512.png (512×512, maskable – Safe Area)

Quelle ist static/pinterest-app-icon.png (das quadratische Markenbildzeichen,
512×512, 1:1 first-party). Kein externes Tool, kein CDN, keine Schrift-Datei.

Nutzung:
    python3 scripts/generate_pwa_icons.py           # schreiben (idempotent)
    python3 scripts/generate_pwa_icons.py --check   # prüfen, Exit 1 bei Drift
    python3 scripts/generate_pwa_icons.py --selftest

Exit: 0 = ok · 1 = Drift/Funde (--check) · 2 = Ausführungsfehler
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(BLOG_DIR, "static")
SOURCE_ICON = os.path.join(STATIC, "pinterest-app-icon.png")
PWA_DIR = os.path.join(STATIC, "images", "pwa")
MANIFEST = os.path.join(STATIC, "manifest.json")
BRAND_COLOR = "#0E5A43"          # Smaragdgrün der Site (params.assets.theme_color)
ICONS = [("icon-192.png", 192, "any"),
         ("icon-512.png", 512, "any"),
         ("icon-maskable-512.png", 512, "maskable")]
SHORTCUTS = [
    ("/pillar/strom-sparen/", "Strom & Gas sparen"),
    ("/pillar/internet-dsl/", "Internet & DSL"),
    ("/pillar/versicherungen/", "Versicherungen"),
    ("/pillar/frugalismus/", "Frugalismus & Budget"),
]


def _toml_string(path: str, key: str, section: str | None = None) -> str:
    """Wert eines Top-Level-/Section-Keys aus hugo.toml (ohne toml-Parser)."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return ""
    if section:
        # Hugo-Dateien rücken Sektionen gern ein (`  [params.assets]`) –
        # beides erlauben, sonst fällt die Wache still auf den Hardcoding-Wert.
        m = re.search(rf"(?ms)^\s*\[{re.escape(section)}\]\s*$"
                      r"(.*?)(?=^\s*\[|\Z)", text)
        text = m.group(1) if m else ""
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*[\"']([^\"']*)[\"']", text, re.M)
    return m.group(1).strip() if m else ""


def site_meta() -> dict:
    cfg = os.path.join(BLOG_DIR, "hugo.toml")
    base = _toml_string(cfg, "baseURL") or "https://franksfinanzcheck.de/"
    title = _toml_string(cfg, "title") or "FranksFinanzcheck"
    desc = _toml_string(cfg, "description", "params")
    desc = desc or ("Geld sparen leicht gemacht: Praxis-Ratgeber für Strom, Gas, "
                    "DSL, Versicherungen und Finanzen.")
    theme = _toml_string(cfg, "theme_color", "params.assets") or BRAND_COLOR
    return {"base": base.rstrip("/") + "/", "title": title,
            "description": desc, "theme": theme}


def _load_image(path: str):
    from PIL import Image  # noqa: F401  (Bewusst spät importiert: --check läuft ohne Pillow)
    return Image.open(path).convert("RGBA")


def build_icons(source: str, out_dir: str, check_only: bool = False) -> list[str]:
    """Erzeugt die drei Icon-Dateien. Gibt Drift-Liste zurück (leer = alles aktuell)."""
    from PIL import Image
    drift: list[str] = []
    src = Image.open(source).convert("RGBA")
    for name, size, purpose in ICONS:
        target = os.path.join(out_dir, name)
        if purpose == "maskable":
            # Maskable: Marke auf_full-bleed Farbfläche, 80 % Safe Area.
            canvas = Image.new("RGBA", (size, size), _hex_rgba(BRAND_COLOR, 255))
            inner = int(size * 0.80)
            mark = src.resize((inner, inner), Image.LANCZOS)
            canvas.alpha_composite(mark, ((size - inner) // 2, (size - inner) // 2))
            data = _png_bytes(canvas.convert("RGB"))
        else:
            data = _png_bytes(src.resize((size, size), Image.LANCZOS).convert("RGB"))
        if check_only:
            if not os.path.exists(target):
                drift.append(f"Icon fehlt: {os.path.relpath(target, BLOG_DIR)}")
            elif open(target, "rb").read() != data:
                drift.append(f"Icon veraltet (Quelle oder Größe geändert): "
                             f"{os.path.relpath(target, BLOG_DIR)}")
        else:
            os.makedirs(out_dir, exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
    return drift


def _hex_rgba(hexcolor: str, alpha: int) -> tuple[int, int, int, int]:
    h = hexcolor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


def _png_bytes(image) -> bytes:
    import io
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_manifest() -> dict:
    meta = site_meta()
    base = meta["base"]
    return {
        "id": base,
        "name": meta["title"],
        "short_name": "Finanzcheck",
        "description": meta["description"],
        "start_url": base + "?utm_source=pwa&utm_medium=app",
        "scope": base,
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#FFFFFF",
        "theme_color": meta["theme"],
        "lang": "de-DE",
        "dir": "ltr",
        "categories": ["finance", "news", "utilities"],
        "icons": [{"src": f"/images/pwa/{name}", "sizes": f"{s}x{s}",
                   "type": "image/png", "purpose": p}
                  for name, s, p in ICONS],
        "shortcuts": [{"name": label, "url": base.strip("/") + path +
                       "?utm_source=pwa-shortcut",
                       "description": "Ratgeber-Kategorie öffnen"}
                      for path, label in SHORTCUTS],
    }


def main() -> int:
    check = "--check" in sys.argv
    if "--selftest" in sys.argv:
        return _selftest()
    if not os.path.exists(SOURCE_ICON):
        print(f"❌ Quellen-Icon fehlt: {SOURCE_ICON}")
        return 2
    try:
        drift = build_icons(SOURCE_ICON, PWA_DIR, check_only=check)
    except ImportError:
        print("ℹ️  Pillow fehlt – Icons werden nicht geprüft/erzeugt "
              "(pip install pillow). Manifest-Prüfung läuft trotzdem.")
        drift = []
    manifest = build_manifest()
    if check:
        if not os.path.exists(MANIFEST):
            drift.append("static/manifest.json fehlt")
        else:
            try:
                current = json.load(open(MANIFEST, encoding="utf-8"))
            except Exception as exc:
                drift.append(f"static/manifest.json ungültig: {exc}")
            else:
                if current != manifest:
                    diff = [k for k in set(current) | set(manifest)
                            if current.get(k) != manifest.get(k)]
                    drift.append("static/manifest.json weicht von hugo.toml ab: "
                                 + ", ".join(sorted(diff))
                                 + " – neu erzeugen: python3 scripts/generate_pwa_icons.py")
        if drift:
            print("PWA-Drift gefunden:")
            for d in drift:
                print("  ❌", d)
            return 1
        print("✅ PWA: Manifest und Icons stimmen mit hugo.toml überein.")
        return 0
    os.makedirs(PWA_DIR, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Manifest geschrieben: static/manifest.json")
    print("Icons: " + ", ".join(n for n, _, _ in ICONS))
    return 0


def _selftest() -> int:
    """4 Fälle: Manifest folgt hugo.toml, Drift wird gesehen, Größen stimmen,
    Maskable-Icon hat den Full-Bleed-Markenrand."""
    errs: list[str] = []
    root = tempfile.mkdtemp(prefix="pwa-selftest-")
    global BLOG_DIR
    keep = BLOG_DIR
    try:
        from PIL import Image
    except ImportError:
        print("ℹ️  Pillow fehlt – PWA-Selbsttest übersprungen.")
        return 0
    try:
        cfg = os.path.join(root, "hugo.toml")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write('baseURL = "https://test.example/"\ntitle = "Testsite"\n'
                    '[params]\n  description = "Text"\n'
                    '  [params.assets]\n    theme_color = "#123456"\n')
        BLOG_DIR = root
        meta = site_meta()
        if meta["base"] != "https://test.example/":
            errs.append(f"baseURL-Fallback falsch: {meta['base']}")
        if meta["theme"] != "#123456":
            errs.append(f"theme_color folgt nicht hugo.toml: {meta['theme']}")
        man = build_manifest()
        if man["name"] != "Testsite" or man["theme_color"] != "#123456":
            errs.append("Manifest spiegelt hugo.toml nicht")
        if len(man["icons"]) != 3 or not all("sizes" in i for i in man["icons"]):
            errs.append("Manifest-Icons unvollständig")

        src = os.path.join(root, "src.png")
        Image.new("RGB", (64, 64), (14, 90, 67)).save(src)
        out = os.path.join(root, "icons")
        if build_icons(src, out):
            errs.append("frisch erzeugte Icons melden Drift")
        if build_icons(src, out, check_only=True):
            errs.append("unveränderte Quelle meldet falschen Drift")
        Image.new("RGB", (64, 64), (200, 30, 30)).save(src)
        if not build_icons(src, out, check_only=True):
            errs.append("veränderte Quelle wird nicht als Drift erkannt")
        for name, size, _purpose in ICONS:
            with Image.open(os.path.join(out, name)) as im:
                if tuple(im.size) != (size, size):
                    errs.append(f"{name}: {im.size} statt {(size, size)}")
        with Image.open(os.path.join(out, "icon-maskable-512.png")) as im:
            edge = im.convert("RGB").getpixel((0, 0))
        if tuple(edge[:3]) != (14, 90, 67):
            errs.append("Maskable-Icon hat keinen Full-Bleed-Markenrand")
    except Exception as exc:  # noqa: BLE001
        errs.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        BLOG_DIR = keep
        import shutil
        shutil.rmtree(root, ignore_errors=True)
    if errs:
        print("🛑 PWA-Selbsttest FEHLGESCHLAGEN:")
        for e in errs:
            print("  -", e)
        return 2
    print("✅ PWA-Selbsttest: Manifest, Icon-Größen und Drift-Erkennung grün.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
