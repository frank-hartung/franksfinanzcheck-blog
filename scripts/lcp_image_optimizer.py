#!/usr/bin/env python3
"""Automatischer LCP-Optimierer für Bilder.

Dieses Tool berechnet pro relevanter Hugo-Seite den wahrscheinlich größten
Above-the-fold-Bildkandidaten und schreibt ein Hugo-Datenmanifest nach
`data/lcp_images.json`. Das Head-Template liest dieses Manifest und setzt den
passenden AVIF-Preload mit exakt denselben `imagesizes` wie das spätere
`<picture>`.

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
    path: str
    rel_permalink: str
    title: str
    date: str
    timestamp: float
    cover: str
    hidden_in_home: bool
    draft: bool


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
    m = re.search(r"^cover:\s*\n(?P<body>(?:\s+[^\n]+\n?)+)", fm, re.M)
    if m:
        cm = re.search(r"^\s*image:\s*[\"']?([^\"'\n]+)[\"']?\s*$", m.group("body"), re.M)
        if cm:
            cover = cm.group(1).strip()

    def boolean(name: str) -> bool:
        value = scalar(name, "false").lower()
        return value in {"true", "yes", "1"}

    date = scalar("date")
    try:
        dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
        timestamp = dt.timestamp()
    except Exception:
        timestamp = 0.0

    return {
        "title": scalar("title", path.stem),
        "date": date,
        "timestamp": timestamp,
        "cover": cover,
        "hiddenInHomeList": boolean("hiddenInHomeList"),
        "draft": boolean("draft"),
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
        if not cover or fm.get("draft", False):
            continue
        posts.append(Post(
            path=rel(path),
            rel_permalink=post_permalink(path),
            title=fm.get("title", path.stem),
            date=fm.get("date", ""),
            timestamp=float(fm.get("timestamp", 0.0)),
            cover=cover,
            hidden_in_home=bool(fm.get("hiddenInHomeList", False)),
            draft=bool(fm.get("draft", False)),
        ))
    posts.sort(key=lambda p: (p.timestamp, p.rel_permalink), reverse=True)
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

    visible_posts = [p for p in posts if not p.hidden_in_home]
    if visible_posts:
        first = visible_posts[0]
        # Home + Blogliste: Erste Karte ist der Bild-LCP-Kandidat.
        for permalink, page_type in (("/", "home"), ("/posts/", "section")):
            pages[permalink] = image_rule(
                first.cover,
                page_type=page_type,
                reason="erstes sichtbares Listen-Cover",
                sizes="(min-width: 768px) 620px, 100vw",
            )

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
