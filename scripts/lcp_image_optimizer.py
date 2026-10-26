#!/usr/bin/env python3
"""Automatischer LCP-Optimierer für Bilder.

Dieses Tool katalogisiert Above-the-fold-Cover der Einzelartikel und
schreibt die Bild-Prioritäts-Policy nach `data/lcp_images.json`.
Das Head-Template wählt passende AVIF-Preloads direkt aus der Seitenquelle;
der Manifest-Check schützt die dazugehörigen Varianten und verhindert
versehentliches Vorladen von Listen-Covers unterhalb des Viewports.

Nutzung:
    python3 scripts/lcp_image_optimizer.py --fix
    python3 scripts/lcp_image_optimizer.py --check
    python3 scripts/lcp_image_optimizer.py --json
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLOG_DIR = Path(__file__).resolve().parents[1]
CONTENT_POSTS = BLOG_DIR / "content" / "posts"
STATIC_DIR = BLOG_DIR / "static"
MANIFEST = BLOG_DIR / "data" / "lcp_images.json"
LCP_WIDTHS = (360, 480, 620, 720)


@dataclass
class Post:
    rel_permalink: str
    cover: str


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = parts[1]

    def scalar(name: str, default: str = "") -> str:
        m = re.search(rf"^{re.escape(name)}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        return (m.group(1).strip().strip('"\'') if m else default)

    cover = ""
    cover_hidden = False
    cover_hidden_in_single = False
    cover_preload_false = False
    m = re.search(r"^cover:\s*\n(?P<body>(?:\s+[^\n]+\n?)+)", fm, re.M)
    if m:
        body = m.group("body")
        cm = re.search(r"^\s*image:\s*[\"']?([^\"'\n]+)[\"']?\s*$", body, re.M)
        if cm:
            cover = cm.group(1).strip()
        hm = re.search(r"^\s*hidden:\s*(true|yes|1)\b", body, re.M | re.I)
        if hm:
            cover_hidden = True
        hs = re.search(r"^\s*hiddenInSingle:\s*(true|yes|1)\b", body, re.M | re.I)
        if hs:
            cover_hidden_in_single = True
        cover_preload_false = bool(re.search(r"^\s*preload:\s*(false|no|0)\b", body, re.M | re.I))

    def boolean(name: str) -> bool:
        value = scalar(name, "false").lower()
        return value in {"true", "yes", "1"}

    return {
        "cover": cover,
        "coverHiddenInSingle": cover_hidden or cover_hidden_in_single or boolean("coverHiddenInSingle"),
        "coverPreloadFalse": cover_preload_false,
        "draft": boolean("draft") or boolean("cadence_wait"),
    }


def post_permalink(path: Path) -> str:
    # Bundle: content/posts/<slug>/index.md → /posts/<slug>/
    if path.name == "index.md":
        return f"/posts/{path.parent.name}/"
    # Leaf: content/posts/<slug>.md → /posts/<slug>/
    return f"/posts/{path.stem}/"


def collect_posts() -> list[Post]:
    paths = list(CONTENT_POSTS.glob("*.md")) + list(CONTENT_POSTS.glob("*/index.md"))
    posts: list[Post] = []
    for path in sorted(paths):
        if path.name == "_index.md":
            continue
        fm = parse_frontmatter(path)
        cover = fm.get("cover") or ""
        if not cover or fm.get("draft", False) or fm.get("coverHiddenInSingle", False) or fm.get("coverPreloadFalse", False):
            continue
        posts.append(Post(rel_permalink=post_permalink(path), cover=cover))
    posts.sort(key=lambda p: p.rel_permalink)
    return posts


def image_rule(image: str, *, page_type: str, reason: str, sizes: str) -> dict[str, Any]:
    return {
        "image": image,
        "type": page_type,
        "reason": reason,
        "sizes": sizes,
        "widths": list(LCP_WIDTHS),
        "format": "avif",
        "loading": "eager",
        "fetchpriority": "high",
        "decoding": "async",
    }


def build_manifest() -> dict[str, Any]:
    posts = collect_posts()
    pages: dict[str, dict[str, Any]] = {}

    # Artikel-Singles: Das Cover ist oben im Viewport und fast immer LCP.
    for post in posts:
        pages[post.rel_permalink] = image_rule(
            post.cover,
            page_type="single",
            reason="Artikel-Cover oberhalb des Falzes",
            sizes="(min-width: 768px) 720px, 100vw",
        )

    # Weder Startseite noch /posts/ brauchen einen Bild-Preload: Hero,
    # Themen und die redaktionelle Navigation stehen vor dem Feed. Die
    # erste Karte beginnt mobil erst > 2400px von oben (26.10.2026).
    return {
        "version": 1,
        "generatedBy": "scripts/lcp_image_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": {
            "preloadFormat": "avif",
            "widths": list(LCP_WIDTHS),
            "noOversized1000wInPreload": True,
            "priority": "fetchpriority=high + loading=eager for LCP candidates",
        },
        "pages": dict(sorted(pages.items())),
    }


def expected_avif_paths(rule: dict[str, Any]) -> list[Path]:
    image = rule.get("image", "")
    if not image:
        return []
    image_path = Path(image)
    directory = image_path.parent
    stem = image_path.stem
    out: list[Path] = []
    for width in rule.get("widths", LCP_WIDTHS):
        out.append(STATIC_DIR / directory / "avif" / str(width) / f"{stem}.avif")
    return out


def check_manifest(manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if manifest.get("pages") != build_manifest()["pages"]:
        problems.append("LCP-Manifest weicht von aktuellen Einzelartikel-Covers ab "
                        "(oder enthält alte Listen-Preloads) – --fix ausführen")
    seen_preloads: set[str] = set()
    for permalink, rule in manifest.get("pages", {}).items():
        image = rule.get("image", "")
        if not image:
            problems.append(f"{permalink}: kein image-Feld")
            continue
        original = STATIC_DIR / image
        if not original.exists():
            problems.append(f"{permalink}: Original fehlt: {image}")
        for path in expected_avif_paths(rule):
            key = path.as_posix()
            seen_preloads.add(key)
            if not path.exists():
                problems.append(f"{permalink}: LCP-AVIF fehlt: {rel(path)}")
            elif path.stat().st_size > 35_000:
                problems.append(f"{permalink}: LCP-AVIF zu groß ({path.stat().st_size} B): {rel(path)}")
    if len(seen_preloads) == 0:
        problems.append("Keine LCP-Preloads gefunden")
    return problems


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatischer LCP-Bildoptimierer")
    parser.add_argument("--fix", action="store_true", help="Manifest neu schreiben")
    parser.add_argument("--check", action="store_true", help="Manifest/Varianten prüfen")
    parser.add_argument("--json", action="store_true", help="JSON-Report ausgeben")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)
    elif MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass

    problems = check_manifest(manifest)
    report = {
        "pages": len(manifest.get("pages", {})),
        "manifest": rel(MANIFEST),
        "problems": problems,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"LCP Image Optimizer: {report['pages']} Seiten | Probleme: {len(problems)}")
        for problem in problems[:40]:
            print("  ❌", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
