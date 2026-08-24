#!/usr/bin/env python3
"""CLS Optimizer für FranksFinanzcheck.

Prüft Layout-Shift-Risiken im kritischen Hero-/Bildpfad:
- LCP/Hero-Elemente dürfen nicht per transform/y verschoben werden
- Hero-Geldbetrag darf nicht per JS von 0 auf finalen Wert umgeschrieben werden
- hervorgehobene Euro-Werte reservieren Breite ab First Paint
- Bilder behalten width/height

Nutzung:
    hugo --minify
    python3 scripts/cls_optimizer.py --fix
    python3 scripts/cls_optimizer.py --check
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

BLOG_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = BLOG_DIR / "public"
MANIFEST = BLOG_DIR / "data" / "cls_optimizer_manifest.json"
PREMIUM_JS = BLOG_DIR / "static" / "premium" / "ff-premium.js"
PREMIUM_CSS = BLOG_DIR / "assets" / "css" / "extended" / "z-premium-blog.css"


@dataclass
class ClsPageStats:
    path: str
    images: int
    imagesWithoutDimensions: int
    heroParagraphs: int
    lcpCandidates: int


class ClsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images = 0
        self.images_without_dimensions = 0
        self.lcp_candidates = 0
        self.hero_depth = 0
        self.hero_paragraphs = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k.lower(): (v or "") for k, v in attrs}
        classes = set((data.get("class") or "").split())
        if tag == "article" and "home-info" in classes:
            self.hero_depth += 1
        elif self.hero_depth and tag == "p":
            self.hero_paragraphs += 1
        if tag == "img":
            self.images += 1
            if not data.get("width") or not data.get("height"):
                self.images_without_dimensions += 1
            if data.get("data-ff-lcp") == "candidate":
                self.lcp_candidates += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self.hero_depth:
            self.hero_depth -= 1


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def parse_page(path: Path) -> ClsPageStats:
    parser = ClsParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return ClsPageStats(
        path=rel(path),
        images=parser.images,
        imagesWithoutDimensions=parser.images_without_dimensions,
        heroParagraphs=parser.hero_paragraphs,
        lcpCandidates=parser.lcp_candidates,
    )


def collect_stats() -> list[ClsPageStats]:
    if not PUBLIC_DIR.exists():
        return []
    return [parse_page(p) for p in sorted(PUBLIC_DIR.rglob("*.html"))]


def build_manifest() -> dict[str, Any]:
    js = PREMIUM_JS.read_text(encoding="utf-8", errors="ignore") if PREMIUM_JS.exists() else ""
    css = PREMIUM_CSS.read_text(encoding="utf-8", errors="ignore") if PREMIUM_CSS.exists() else ""
    stats = collect_stats()
    return {
        "version": 1,
        "generatedBy": "scripts/cls_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": {
            "heroReveal": "opacity-only",
            "heroMoney": "no text rewrite; reserve inline width",
            "imageDimensions": "required",
        },
        "guards": {
            "heroOpacityOnly": (
                ("gsap.set(heroItems, { autoAlpha: 0 })" in js or "var heroEnhancements = qsa('.ff-home-ctas a, .ff-trust-row span')" in js)
                and "y: 24" not in js
                and "y: 0" not in js
            ),
            "noMoneyTextRewrite": "format(Math.round(state.value))" not in js,
            "heroMoneyWidthReserved": ".first-entry.home-info .entry-content strong" in css and "min-width: 7ch" in css,
        },
        "summary": {
            "pages": len(stats),
            "images": sum(s.images for s in stats),
            "imagesWithoutDimensions": sum(s.imagesWithoutDimensions for s in stats),
            "maxLcpCandidates": max((s.lcpCandidates for s in stats), default=0),
        },
        "worst": [asdict(s) for s in stats if s.imagesWithoutDimensions or s.lcpCandidates > 1][:20],
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def check(manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for key, ok in manifest.get("guards", {}).items():
        if not ok:
            problems.append(f"CLS-Guard fehlt: {key}")
    summary = manifest.get("summary", {})
    if summary.get("imagesWithoutDimensions", 0):
        problems.append(f"Bilder ohne Dimensionen: {summary['imagesWithoutDimensions']}")
    if summary.get("maxLcpCandidates", 0) > 1:
        problems.append("Mehr als ein LCP-Kandidat auf einer Seite")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="CLS Optimizer")
    parser.add_argument("--fix", action="store_true", help="Manifest schreiben")
    parser.add_argument("--check", action="store_true", help="CLS-Guards prüfen")
    parser.add_argument("--json", action="store_true", help="JSON ausgeben")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)
    problems = check(manifest) if args.check else []
    report = {
        "manifest": rel(MANIFEST),
        "summary": manifest["summary"],
        "guards": manifest["guards"],
        "problems": problems,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"CLS Optimizer: Probleme {len(problems)} | Bilder ohne Dimensionen {manifest['summary']['imagesWithoutDimensions']}")
        for p in problems[:40]:
            print("  ❌", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
