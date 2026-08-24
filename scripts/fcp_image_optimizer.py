#!/usr/bin/env python3
"""Automatischer FCP-Optimierer für Bilder.

FCP wird bei einem Blog meist durch frühe Text-/Header-Renderbarkeit bestimmt.
Bilder dürfen den kritischen Pfad deshalb nicht unnötig blockieren oder dem
LCP-Cover Bandbreite wegnehmen. Dieses Tool erzeugt ein FCP-Policy-Manifest und
prüft den gebauten Hugo-Output auf Agentur-Regeln:

- genau priorisierte LCP-Bilder, keine konkurrierenden High-Priority-Bilder
- Logo klein/dimensioniert/low-priority statt inline SVG-DOM-Baum
- Nicht-LCP-Bilder lazy + async + fetchpriority=low
- alle Bilder mit width/height gegen CLS

Nutzung:
    python3 scripts/fcp_image_optimizer.py --fix
    hugo --minify
    python3 scripts/fcp_image_optimizer.py --check
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
MANIFEST = BLOG_DIR / "data" / "fcp_images.json"
LCP_MANIFEST = BLOG_DIR / "data" / "lcp_images.json"
IMAGE_MANIFEST = BLOG_DIR / "data" / "image_optimizer_manifest.json"


@dataclass
class FcpPolicy:
    role: str
    selector: str
    loading: str | None
    decoding: str
    fetchpriority: str
    reason: str


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest() -> dict[str, Any]:
    lcp = load_json(LCP_MANIFEST)
    images = load_json(IMAGE_MANIFEST)
    policies = [
        FcpPolicy(
            role="logo",
            selector='img[data-ff-fcp-image="logo"]',
            loading="eager",
            decoding="async",
            fetchpriority="low",
            reason="kleines Logo darf FCP nicht mit LCP-Bild konkurrieren",
        ),
        FcpPolicy(
            role="lcp",
            selector='img[data-ff-lcp="candidate"]',
            loading="eager",
            decoding="async",
            fetchpriority="high",
            reason="nur der echte Above-the-fold-Bildkandidat bekommt hohe Priorität",
        ),
        FcpPolicy(
            role="deferred",
            selector='img[data-ff-fcp-image="deferred"]',
            loading="lazy",
            decoding="async",
            fetchpriority="low",
            reason="Nicht-kritische Bilder nach FCP/LCP verschieben",
        ),
    ]
    return {
        "version": 1,
        "generatedBy": "scripts/fcp_image_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": {
            "goal": "Bildrequests dürfen FCP nicht verzögern und nicht mit dem LCP-Cover konkurrieren.",
            "maxHighPriorityImagesPerPage": 1,
            "requireDimensions": True,
            "requireAsyncDecoding": True,
            "deferNonCriticalImages": True,
        },
        "inputs": {
            "lcpManifestPages": len((lcp.get("pages") or {})),
            "imageManifestSources": len((images.get("images") or [])),
        },
        "policies": [asdict(p) for p in policies],
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict[str, str]] = []
        self.lcp_preloads = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "img":
            self.images.append(data)
        elif tag.lower() == "link" and data.get("rel") == "preload" and data.get("as") == "image":
            if data.get("data-ff-lcp-optimizer") == "true":
                self.lcp_preloads += 1


def is_content_image(img: dict[str, str]) -> bool:
    src = img.get("src", "")
    return "/images/" in src or src.startswith("/images/") or "images/" in src


def audit_html_file(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    parser = ImageParser()
    parser.feed(html)
    problems: list[str] = []
    if not parser.images:
        return problems

    high_images = [img for img in parser.images if img.get("fetchpriority") == "high"]
    if len(high_images) > 1:
        problems.append(f"{rel(path)}: mehr als ein High-Priority-Bild ({len(high_images)})")

    lcp_candidates = [img for img in parser.images if img.get("data-ff-lcp") == "candidate"]
    if len(lcp_candidates) > 1:
        problems.append(f"{rel(path)}: mehr als ein data-ff-lcp=candidate ({len(lcp_candidates)})")

    for img in parser.images:
        if not is_content_image(img):
            continue
        role = img.get("data-ff-fcp-image", "")
        src = img.get("src", "")
        if not img.get("width") or not img.get("height"):
            problems.append(f"{rel(path)}: Bild ohne width/height: {src}")
        if img.get("decoding") != "async":
            problems.append(f"{rel(path)}: Bild ohne decoding=async: {src}")
        if img.get("data-ff-lcp") == "candidate":
            if img.get("fetchpriority") != "high" or img.get("loading") != "eager":
                problems.append(f"{rel(path)}: LCP-Bild nicht eager/high: {src}")
        elif role == "logo":
            if img.get("fetchpriority") != "low":
                problems.append(f"{rel(path)}: Logo nicht fetchpriority=low: {src}")
        else:
            if img.get("loading") != "lazy":
                problems.append(f"{rel(path)}: Nicht-LCP-Bild nicht lazy: {src}")
            if img.get("fetchpriority") not in ("", "low"):
                problems.append(f"{rel(path)}: Nicht-LCP-Bild konkurriert mit Priorität {img.get('fetchpriority')}: {src}")
    return problems


def audit_public() -> list[str]:
    if not PUBLIC_DIR.exists():
        return ["public/ fehlt – zuerst `hugo --minify` ausführen"]
    problems: list[str] = []
    for path in sorted(PUBLIC_DIR.rglob("*.html")):
        problems.extend(audit_html_file(path))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatischer FCP-Bildoptimierer")
    parser.add_argument("--fix", action="store_true", help="FCP-Manifest schreiben")
    parser.add_argument("--check", action="store_true", help="gebautes HTML prüfen")
    parser.add_argument("--json", action="store_true", help="JSON-Report ausgeben")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)

    problems = audit_public() if args.check else []
    report = {"manifest": rel(MANIFEST), "policies": len(manifest["policies"]), "problems": problems}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"FCP Image Optimizer: {len(manifest['policies'])} Policies | Probleme: {len(problems)}")
        for problem in problems[:40]:
            print("  ❌", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
