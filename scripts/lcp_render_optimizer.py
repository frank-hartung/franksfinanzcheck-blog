#!/usr/bin/env python3
"""LCP Render-Delay Optimizer.

Prüft, dass das LCP-Bild zwar früh geladen wird, aber nicht durch Animationen,
Reveal-Klassen, content-visibility oder JS bis nach dem Laden versteckt bleibt.
Genau dieser Fall erzeugt in Lighthouse hohe Werte bei
"Verzögerung beim Rendering des Elements".

Nutzung:
    hugo --minify
    python3 scripts/lcp_render_optimizer.py --fix
    python3 scripts/lcp_render_optimizer.py --check
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
MANIFEST = BLOG_DIR / "data" / "lcp_render_optimizer_manifest.json"
PREMIUM_JS = BLOG_DIR / "static" / "premium" / "ff-premium.js"
PREMIUM_CSS = BLOG_DIR / "assets" / "css" / "extended" / "z-premium-blog.css"


@dataclass
class PageLcpRenderStats:
    path: str
    lcpCandidates: int
    lcpHiddenByClass: bool
    lcpHasEager: bool
    lcpHasHighPriority: bool
    lcpHasDimensions: bool


class LcpParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lcp_imgs: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        data = {k.lower(): (v or "") for k, v in attrs}
        if data.get("data-ff-lcp") == "candidate":
            self.lcp_imgs.append(data)


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def parse_page(path: Path) -> PageLcpRenderStats:
    parser = LcpParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    img = parser.lcp_imgs[0] if parser.lcp_imgs else {}
    classes = img.get("class", "")
    return PageLcpRenderStats(
        path=rel(path),
        lcpCandidates=len(parser.lcp_imgs),
        lcpHiddenByClass="ff-will-reveal" in classes,
        lcpHasEager=img.get("loading") == "eager",
        lcpHasHighPriority=img.get("fetchpriority") == "high",
        lcpHasDimensions=bool(img.get("width") and img.get("height")),
    )


def collect_stats() -> list[PageLcpRenderStats]:
    if not PUBLIC_DIR.exists():
        return []
    return [parse_page(p) for p in sorted(PUBLIC_DIR.rglob("*.html"))]


def build_manifest() -> dict[str, Any]:
    stats = collect_stats()
    js = PREMIUM_JS.read_text(encoding="utf-8", errors="ignore") if PREMIUM_JS.exists() else ""
    css = PREMIUM_CSS.read_text(encoding="utf-8", errors="ignore") if PREMIUM_CSS.exists() else ""
    pages_with_lcp = [s for s in stats if s.lcpCandidates]
    return {
        "version": 1,
        "generatedBy": "scripts/lcp_render_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": {
            "neverRevealHideLcp": True,
            "excludeLcpFromIntersectionReveal": True,
            "defensiveCssGuard": True,
        },
        "summary": {
            "pages": len(stats),
            "pagesWithLcpCandidate": len(pages_with_lcp),
            "maxLcpCandidatesPerPage": max((s.lcpCandidates for s in stats), default=0),
        },
        "codeGuards": {
            "jsHasLcpCriticalFilter": "isLcpCriticalElement" in js and "!isLcpCriticalElement(el)" in js,
            "cssHasLcpGuard": "[data-ff-lcp=\"candidate\"]" in css and ".lcp-card.ff-will-reveal" in css,
        },
        "worst": [asdict(s) for s in stats if s.lcpCandidates > 1 or s.lcpHiddenByClass or (s.lcpCandidates and not (s.lcpHasEager and s.lcpHasHighPriority and s.lcpHasDimensions))][:20],
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def check(manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not manifest["codeGuards"].get("jsHasLcpCriticalFilter"):
        problems.append("ff-premium.js filtert LCP-Kandidaten nicht aus Reveal-Hiding heraus")
    if not manifest["codeGuards"].get("cssHasLcpGuard"):
        problems.append("CSS-Guard gegen ff-will-reveal auf LCP-Kandidaten fehlt")
    if manifest["summary"].get("maxLcpCandidatesPerPage", 0) > 1:
        problems.append("Mehr als ein LCP-Kandidat auf mindestens einer Seite")
    for item in manifest.get("worst", []):
        problems.append(f"{item['path']}: LCP-Kandidat nicht sauber renderbar/priorisiert: {item}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="LCP Render-Delay Optimizer")
    parser.add_argument("--fix", action="store_true", help="Manifest schreiben")
    parser.add_argument("--check", action="store_true", help="gegen Render-Delay-Regeln prüfen")
    parser.add_argument("--json", action="store_true", help="JSON ausgeben")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)
    problems = check(manifest) if args.check else []
    report = {
        "manifest": rel(MANIFEST),
        "summary": manifest["summary"],
        "codeGuards": manifest["codeGuards"],
        "problems": problems,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"LCP Render Optimizer: {manifest['summary']['pagesWithLcpCandidate']} Seiten mit LCP | Probleme {len(problems)}")
        for p in problems[:40]:
            print("  ❌", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
