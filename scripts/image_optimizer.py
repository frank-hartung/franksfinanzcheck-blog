#!/usr/bin/env python3
"""FranksFinanzcheck Image Optimizer – responsive Bilder auf Agentur-Niveau.

Was das Tool automatisch erledigt:
- erzeugt mobile/Desktop-Bildbreiten für Cover: 360, 480, 620, 720 px
- erzeugt moderne Formate: AVIF + WebP + JPEG-Fallback
- hält 1000px-AVIF/WebP für OG/Fallback vor, bietet sie aber nicht im normalen
  srcset an (siehe cover.html)
- prüft echte Dateiformate per Magic Bytes (keine Fake-.avif/.webp mehr)
- schreibt ein Manifest mit Dateigrößen für Audits

Nutzung:
    python3 scripts/image_optimizer.py --fix
    python3 scripts/image_optimizer.py --check
    python3 scripts/image_optimizer.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("FEHLER: Pillow fehlt – installiere: pip install pillow pillow-avif-plugin") from exc

try:
    import pillow_avif  # noqa: F401 – registriert AVIF in Pillow
    AVIF_OK = True
except Exception:
    AVIF_OK = False

BLOG_DIR = Path(__file__).resolve().parents[1]
STATIC_IMAGES = BLOG_DIR / "static" / "images"
COVERS_DIR = STATIC_IMAGES / "covers"
MANIFEST = BLOG_DIR / "data" / "image_optimizer_manifest.json"

# Zielbreiten passend zum Layout:
# 360/480 = Mobile, 620 = Listen/Desktop, 720 = Single/Desktop.
RESPONSIVE_WIDTHS = (360, 480, 620, 720)
FULL_WIDTH = 1000
JPEG_QUALITY = 82
WEBP_QUALITY = 78
AVIF_QUALITY = 45

GENERATED_DIR_NAMES = {"360", "480", "620", "720", "webp", "avif"}
SUPPORTED_SOURCE_SUFFIXES = {".jpg", ".jpeg", ".png"}


@dataclass
class Variant:
    path: str
    width: int
    height: int
    format: str
    bytes: int


@dataclass
class OptimizedImage:
    source: str
    source_width: int
    source_height: int
    variants: list[Variant]


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def is_generated_path(path: Path) -> bool:
    try:
        parts = path.relative_to(COVERS_DIR).parts
    except ValueError:
        return False
    return bool(parts and parts[0] in GENERATED_DIR_NAMES)


def cover_sources() -> list[Path]:
    """Alle echten Cover-Originale, keine generierten Varianten."""
    if not COVERS_DIR.exists():
        return []
    out = []
    for path in sorted(COVERS_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES and path.name != "_index.jpg":
            out.append(path)
    return out


# --------------------------------------------------------------------------
#  KI-ORIGINALE BLEIBEN UNANGETASTET (#1028, 07.11.2026)
# --------------------------------------------------------------------------
#  Befund: Dieser Optimizer kannte `cover.ai_generated` nicht. Für ein als
#  KI deklariertes Cover hätte er JPEG/WebP/AVIF-Ableitungen in fünf Breiten
#  erzeugt – alle öffentlich erreichbar unter /images/covers/, keine mit der
#  IPTC-Markierung des Originals (die Ableitungen werden neu enkodiert, dabei
#  fällt jedes XMP-Paket weg). cover.html liefert deklarierte Originale
#  bewusst OHNE Umkodierung aus; die Ableitungen wären also weder verlinkt
#  noch gekennzeichnet gewesen – genau die Klasse „Markierung auf dem
#  Verbreitungsweg verloren", die der Verhaltenskodex der Kommission vom
#  10.06.2026 ausschließen will.
#
#  Regel: Ein deklariertes Original wird hier nicht angefasst. Vorhandene
#  Ableitungen meldet --check und entfernt scripts/ki_provenienz_gate.py
#  --heilen mit Belegzeile (Regel M6).
_KI_ORIGINAL_CACHE: frozenset[Path] | None = None
KI_ORIGINAL_UEBERSPRUNGEN: list[str] = []


def ki_originale(root: Path | None = None) -> frozenset[Path]:
    """Pfade aller Cover, die `cover.ai_generated: true` tragen.

    Quelle der Wahrheit ist scripts/ki_provenienz.py (dieselbe Datei, aus der
    auch das Provenienz-Gate liest) – kein zweiter Pflegeort für dieselbe
    Frage. Schlägt das Laden fehl, wird NICHT still weiteroptimiert: Ein
    Optimizer, der die Kennzeichnungspflicht nicht kennt, erzeugt Beweismittel
    gegen sich selbst. Fail-closed, wie beim Pillow-Import oben.
    """
    global _KI_ORIGINAL_CACHE
    if _KI_ORIGINAL_CACHE is not None:
        return _KI_ORIGINAL_CACHE
    basis = Path(root) if root else BLOG_DIR
    sys.path.insert(0, str(basis / "scripts"))
    try:
        import ki_provenienz  # noqa: PLC0415  (bewusst verzögert)
    except ImportError as exc:
        raise SystemExit(
            "FEHLER: scripts/ki_provenienz.py nicht ladbar – der Bild-Optimizer "
            "kann deklarierte KI-Originale nicht erkennen und läuft deshalb "
            f"nicht an (fail-closed, Regel M6): {exc}") from exc
    static = basis / "static"
    raus = set()
    for seite in ki_provenienz.seiten(basis):
        if not seite.ki_bild:
            continue
        original = ki_provenienz.pfad_wert(seite.kopf, ("cover", "image")) or ""
        if not original:
            continue
        pfad = (static / original.lstrip("/")).resolve()
        raus.add(pfad)
    _KI_ORIGINAL_CACHE = frozenset(raus)
    return _KI_ORIGINAL_CACHE


def ist_ki_original(source: Path) -> bool:
    try:
        return source.resolve() in ki_originale()
    except OSError:
        return False


def ki_ableitungen(source: Path, *, vorhanden: bool = False) -> list[str]:
    """Ableitungspfade einer Quelldatei, relativ zum Repo (Regel M6).

    `vorhanden=True` liefert nur, was wirklich auf der Platte liegt – das ist
    der Befund: eine öffentlich erreichbare, unmarkierte Kopie.
    """
    sys.path.insert(0, str(BLOG_DIR / "scripts"))
    try:
        import ki_provenienz  # noqa: PLC0415  (bewusst verzögert)
    except ImportError:
        return []
    try:
        relativ = source.resolve().relative_to((BLOG_DIR / "static").resolve())
    except (ValueError, OSError):
        return []
    raus = []
    for pfad in ki_provenienz.abgeleitete_pfade(str(relativ).replace(os.sep, "/")):
        datei = BLOG_DIR / "static" / pfad
        if not vorhanden or datei.is_file():
            raus.append(str(Path("static") / pfad))
    return raus


def ki_ableitungen_vorhanden(source: Path) -> list[str]:
    return ki_ableitungen(source, vorhanden=True)


def resize_to_width(img: Image.Image, width: int) -> Image.Image:
    src_w, src_h = img.size
    if width >= src_w:
        return img.copy()
    height = round(src_h * width / src_w)
    return img.resize((width, height), Image.LANCZOS)


def save_jpeg(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def save_webp(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "WEBP", quality=WEBP_QUALITY, method=6)


def save_avif(img: Image.Image, path: Path) -> None:
    if not AVIF_OK:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "AVIF", quality=AVIF_QUALITY, speed=6)


def variant_info(path: Path, width: int, height: int, fmt: str) -> Variant:
    return Variant(path=rel(path), width=width, height=height, format=fmt, bytes=path.stat().st_size)


def optimize_cover_image(source: str | Path, image: Image.Image | None = None, force: bool = False) -> list[str]:
    """Erzeugt Varianten für ein Cover und gibt relative Pfade zurück."""
    source = Path(source)
    if not source.is_absolute():
        source = BLOG_DIR / source
    if not source.exists() and image is None:
        raise FileNotFoundError(source)

    # KI-VO #1028: Ein als KI deklariertes Cover-Original (cover.ai_generated)
    # wird NICHT umkodiert. Jede Ableitung verlöre das IPTC-XMP-Paket des
    # Originals und wäre trotzdem öffentlich erreichbar – eine unmarkierte
    # Kopie synthetischen Inhalts. cover.html liefert das Original ohnehin
    # unverändert aus, die Ableitungen blieben also Waisendateien.
    if ist_ki_original(source):
        KI_ORIGINAL_UEBERSPRUNGEN.append(rel(source))
        return []

    img = (image.copy() if image is not None else Image.open(source)).convert("RGB")
    src_w, src_h = img.size
    base_dir = source.parent
    stem = source.stem
    filename = source.name
    made: list[str] = []

    # JPEG-Fallbacks für mobile/desktop Breiten.
    for width in RESPONSIVE_WIDTHS:
        if width > src_w:
            continue
        out = base_dir / str(width) / filename
        if force or not out.exists():
            save_jpeg(resize_to_width(img, width), out)
            made.append(rel(out))

    # WebP/AVIF in allen responsiven Breiten + 1000px-Rootvariante.
    for width in (*RESPONSIVE_WIDTHS, min(FULL_WIDTH, src_w)):
        if width > src_w:
            continue
        resized = resize_to_width(img, width)
        rw, rh = resized.size
        if width == min(FULL_WIDTH, src_w):
            webp = base_dir / "webp" / f"{stem}.webp"
            avif = base_dir / "avif" / f"{stem}.avif"
        else:
            webp = base_dir / "webp" / str(width) / f"{stem}.webp"
            avif = base_dir / "avif" / str(width) / f"{stem}.avif"
        if force or not webp.exists():
            save_webp(resized, webp)
            made.append(rel(webp))
        if AVIF_OK and (force or not avif.exists()):
            save_avif(resized, avif)
            made.append(rel(avif))
    return made


def looks_like_avif(path: Path) -> bool:
    try:
        head = path.read_bytes()[:32]
    except Exception:
        return False
    return b"ftyp" in head[:16] and (b"avif" in head[:32] or b"avis" in head[:32])


def looks_like_webp(path: Path) -> bool:
    try:
        head = path.read_bytes()[:16]
    except Exception:
        return False
    return head.startswith(b"RIFF") and b"WEBP" in head[:16]


def expected_variants(source: Path) -> list[Path]:
    img = Image.open(source)
    src_w, _ = img.size
    stem = source.stem
    filename = source.name
    base = source.parent
    out: list[Path] = []
    for width in RESPONSIVE_WIDTHS:
        if width <= src_w:
            out.append(base / str(width) / filename)
            out.append(base / "webp" / str(width) / f"{stem}.webp")
            out.append(base / "avif" / str(width) / f"{stem}.avif")
    out.append(base / "webp" / f"{stem}.webp")
    out.append(base / "avif" / f"{stem}.avif")
    return out



def remove_misplaced_modern_files() -> list[str]:
    """Entfernt Altlasten wie .jpg/.png in avif-/webp-Ordnern.

    Solche Dateien koennen von Browsern trotz Pfad/Ordnernamen falsch oder zu
    gross ausgeliefert werden und fuehren zu Lighthouse-Hinweisen.
    """
    removed: list[str] = []
    for folder in (COVERS_DIR / "avif", COVERS_DIR / "webp"):
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() not in {".avif", ".webp"}:
                removed.append(rel(path))
                path.unlink()
    return removed

def check_sources(sources: Iterable[Path]) -> list[str]:
    problems: list[str] = []
    for source in sources:
        # KI-Originale dürfen KEINE Ableitungen haben (siehe optimize_cover_image):
        # „FEHLT" wäre hier ein falscher Befund, und eine vorhandene Ableitung
        # ist der eigentliche Fund.
        if ist_ki_original(source):
            for ableitung in ki_ableitungen_vorhanden(source):
                problems.append(f"KI_ABLEITUNG_UNMARKIERT: {ableitung}")
            continue
        for path in expected_variants(source):
            if not path.exists():
                problems.append(f"FEHLT: {rel(path)}")
                continue
            if path.suffix == ".avif" and not looks_like_avif(path):
                problems.append(f"BAD_FORMAT_AVIF: {rel(path)}")
            if path.suffix == ".webp" and not looks_like_webp(path):
                problems.append(f"BAD_FORMAT_WEBP: {rel(path)}")
    return problems


def build_manifest(sources: Iterable[Path]) -> dict:
    items: list[dict] = []
    for source in sources:
        if ist_ki_original(source):
            # Manifest sagt die Wahrheit: dieses Cover hat bewusst keine
            # Ableitungen, weil es ein deklariertes KI-Original ist.
            items.append({"path": rel(source), "kiOriginal": True, "variants": []})
            continue
        img = Image.open(source)
        variants: list[Variant] = []
        for path in expected_variants(source):
            if not path.exists():
                continue
            try:
                vimg = Image.open(path)
                width, height = vimg.size
            except Exception:
                width = height = 0
            variants.append(variant_info(path, width, height, path.suffix.lstrip(".")))
        items.append(asdict(OptimizedImage(rel(source), img.width, img.height, variants)))
    return {
        "tool": "scripts/image_optimizer.py",
        "profile": "covers",
        "widths": list(RESPONSIVE_WIDTHS),
        "fullWidth": FULL_WIDTH,
        "quality": {"jpeg": JPEG_QUALITY, "webp": WEBP_QUALITY, "avif": AVIF_QUALITY},
        "images": items,
    }


def write_manifest(data: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def main() -> int:
    parser = argparse.ArgumentParser(description="Responsive Bildoptimierung für FranksFinanzcheck")
    parser.add_argument("--fix", action="store_true", help="fehlende/alte Varianten erzeugen")
    parser.add_argument("--force", action="store_true", help="alle Varianten neu encodieren")
    parser.add_argument("--check", action="store_true", help="nur prüfen")
    parser.add_argument("--json", action="store_true", help="JSON-Report ausgeben")
    args = parser.parse_args()

    sources = cover_sources()
    changed: list[str] = []
    removed: list[str] = []
    if args.fix or args.force:
        removed = remove_misplaced_modern_files()
        for source in sources:
            changed.extend(optimize_cover_image(source, force=args.force))

    manifest = build_manifest(sources)
    lcp_manifest = "data/lcp_images.json"
    if args.fix or args.force:
        write_manifest(manifest)
        # LCP-Preload-Manifest direkt mitziehen, damit neue/geänderte Cover
        # ohne manuellen Schritt im kritischen Pfad landen.
        try:
            import lcp_image_optimizer
            lcp_image_optimizer.write_manifest(lcp_image_optimizer.build_manifest())
        except Exception as exc:
            print(f"WARNUNG: LCP-Manifest konnte nicht aktualisiert werden: {exc}")
        try:
            import fcp_image_optimizer
            fcp_image_optimizer.write_manifest(fcp_image_optimizer.build_manifest())
        except Exception as exc:
            print(f"WARNUNG: FCP-Manifest konnte nicht aktualisiert werden: {exc}")

    problems = check_sources(sources)
    report = {"sources": len(sources), "changed": len(changed), "removed": len(removed), "problems": problems, "manifest": rel(MANIFEST), "lcpManifest": lcp_manifest, "fcpManifest": "data/fcp_images.json",
              # KI-VO #1028: deklarierte Originale werden nicht umkodiert.
              # Sichtbar im Report, damit niemand „0 Varianten" für einen
              # Optimizer-Fehler hält.
              "kiOriginale": len(ki_originale()),
              "kiOriginaleUebersprungen": len(KI_ORIGINAL_UEBERSPRUNGEN)}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Image Optimizer: {len(sources)} Quellen | {len(changed)} Varianten geschrieben | {len(removed)} Altlasten entfernt | Probleme: {len(problems)}")
        for problem in problems[:30]:
            print("  ❌", problem)
        if len(problems) > 30:
            print(f"  … {len(problems) - 30} weitere")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
