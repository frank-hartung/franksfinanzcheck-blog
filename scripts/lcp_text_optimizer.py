#!/usr/bin/env python3
"""LCP Text Render Optimizer.

Wenn Lighthouse als LCP-Element die Hero-Headline meldet, darf diese Headline
nicht durch JavaScript-Animationen versteckt oder verschoben werden. Dieses
Quality-Gate prüft genau das.

Nutzung:
    hugo --minify
    python3 scripts/lcp_text_optimizer.py --fix
    python3 scripts/lcp_text_optimizer.py --check
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLOG_DIR = Path(__file__).resolve().parents[1]
MANIFEST = BLOG_DIR / "data" / "lcp_text_optimizer_manifest.json"
PREMIUM_JS = BLOG_DIR / "static" / "premium" / "ff-premium.js"
PREMIUM_CSS = BLOG_DIR / "assets" / "css" / "extended" / "z-premium-blog.css"


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def build_manifest() -> dict[str, Any]:
    js = read(PREMIUM_JS)
    css = read(PREMIUM_CSS)
    return {
        "version": 1,
        "generatedBy": "scripts/lcp_text_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": {
            "heroTextVisibleFromFirstPaint": True,
            "noHeroTextTransform": True,
            "noHeroMoneyTextRewrite": True,
            "animateOnlyNonTextHeroControls": True,
        },
        "guards": {
            "heroTextNotInGsapSelector": ".home-info .entry-header h1, .home-info .entry-content p" not in js,
            "heroEnhancementsOnly": "var heroEnhancements = qsa('.ff-home-ctas a, .ff-trust-row span')" in js,
            "noHeroYTransform": "y: 24" not in js and "y: 0" not in js,
            "noMoneyTextRewrite": "format(Math.round(state.value))" not in js and "el.textContent =" not in js,
            "cssHeroTextVisible": ".first-entry.home-info .entry-header h1" in css and "visibility: visible !important" in css,
            "heroMoneyWidthReserved": ".first-entry.home-info .entry-content strong" in css and "min-width: 7ch" in css,
        },
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def check(manifest: dict[str, Any]) -> list[str]:
    return [f"Guard fehlt: {k}" for k, ok in manifest.get("guards", {}).items() if not ok]


def main() -> int:
    parser = argparse.ArgumentParser(description="LCP Text Render Optimizer")
    parser.add_argument("--fix", action="store_true", help="Manifest schreiben")
    parser.add_argument("--check", action="store_true", help="Guards prüfen")
    parser.add_argument("--json", action="store_true", help="JSON ausgeben")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)
    problems = check(manifest) if args.check else []
    report = {"manifest": rel(MANIFEST), "guards": manifest["guards"], "problems": problems}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"LCP Text Optimizer: Probleme {len(problems)}")
        for problem in problems:
            print("  ❌", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
