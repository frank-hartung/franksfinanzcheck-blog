#!/usr/bin/env python3
"""Forced-Reflow Optimizer für FranksFinanzcheck.

Prüft, dass Premium-JavaScript keine bekannten Layout-Thrash-/ScrollTrigger-
Muster in den kritischen Pfad bringt. Hintergrund: ScrollTrigger misst
Start-/Endpositionen und kann in Lighthouse als erzwungener dynamischer Umbruch
auftauchen. Für einen Blog reichen IntersectionObserver-Reveals aus.

Nutzung:
    hugo --minify
    python3 scripts/reflow_optimizer.py --fix
    python3 scripts/reflow_optimizer.py --check
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
PUBLIC_DIR = BLOG_DIR / "public"
MANIFEST = BLOG_DIR / "data" / "reflow_optimizer_manifest.json"
PREMIUM_JS = BLOG_DIR / "static" / "premium" / "ff-premium.js"
EXTEND_FOOTER = BLOG_DIR / "layouts" / "_partials" / "extend_footer.html"

BUDGETS = {
    "maxScrollTriggerScripts": 0,
    "maxScrollTriggerUsages": 0,
    "maxHotPathGeometryReads": 0,
}

GEOMETRY_APIS = (
    "offsetWidth", "offsetHeight", "offsetTop", "offsetLeft",
    "clientWidth", "clientHeight", "scrollWidth", "scrollHeight",
    "getBoundingClientRect",
)


@dataclass
class JsAudit:
    file: str
    scrollTriggerUsages: int
    geometryReads: dict[str, int]
    hotPathGeometryReads: int


def rel(path: Path) -> str:
    return path.relative_to(BLOG_DIR).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def count_scrolltrigger_scripts() -> int:
    count = 0
    if PUBLIC_DIR.exists():
        for html in PUBLIC_DIR.rglob("*.html"):
            text = read(html)
            count += text.count("ScrollTrigger.min.js")
    else:
        count += read(EXTEND_FOOTER).count("ScrollTrigger.min.js")
    return count


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def audit_js(path: Path) -> JsAudit:
    raw = read(path)
    code = strip_comments(raw)
    geometry = {api: code.count(api) for api in GEOMETRY_APIS}

    # Hot path heuristic: geometry reads inside the actual listener function for
    # scroll/pointermove are risky. Cached pointerenter reads and resize/load reads
    # are ok. Keep the regex deliberately narrow to avoid counting nearby helper
    # functions that are not executed in the hot path.
    hot = 0
    for event in ("scroll", "pointermove", "mousemove", "touchmove"):
        pattern = re.compile(
            r"addEventListener\(\s*['\"]" + re.escape(event) +
            r"['\"]\s*,\s*function\s*\([^)]*\)\s*\{(?P<body>.*?)\}\s*,",
            re.S,
        )
        for match in pattern.finditer(code):
            fragment = match.group('body')
            hot += sum(fragment.count(api) for api in GEOMETRY_APIS)

    return JsAudit(
        file=rel(path),
        scrollTriggerUsages=code.count("ScrollTrigger") + code.count("scrollTrigger"),
        geometryReads=geometry,
        hotPathGeometryReads=hot,
    )


def build_manifest() -> dict[str, Any]:
    js = audit_js(PREMIUM_JS)
    return {
        "version": 1,
        "generatedBy": "scripts/reflow_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "budgets": BUDGETS,
        "strategy": {
            "noScrollTriggerInRuntime": True,
            "scrollReveals": "IntersectionObserver",
            "heroMotion": "GSAP timeline only, no layout measuring plugin",
            "geometryReads": "batch or cache outside scroll/pointermove hot paths",
        },
        "audits": [asdict(js)],
        "scrollTriggerScriptsInBuiltHtml": count_scrolltrigger_scripts(),
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def check(manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    scripts = manifest.get("scrollTriggerScriptsInBuiltHtml", 0)
    if scripts > BUDGETS["maxScrollTriggerScripts"]:
        problems.append(f"ScrollTrigger wird im HTML geladen: {scripts} Vorkommen")
    for audit in manifest.get("audits", []):
        if audit["scrollTriggerUsages"] > BUDGETS["maxScrollTriggerUsages"]:
            problems.append(f"{audit['file']}: ScrollTrigger-Nutzung gefunden ({audit['scrollTriggerUsages']})")
        if audit["hotPathGeometryReads"] > BUDGETS["maxHotPathGeometryReads"]:
            problems.append(f"{audit['file']}: Geometry Reads im Scroll/Move-Hotpath ({audit['hotPathGeometryReads']})")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Forced-Reflow Optimizer")
    parser.add_argument("--fix", action="store_true", help="Manifest schreiben")
    parser.add_argument("--check", action="store_true", help="gegen Reflow-Budget prüfen")
    parser.add_argument("--json", action="store_true", help="JSON ausgeben")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)
    problems = check(manifest) if args.check else []
    report = {
        "manifest": rel(MANIFEST),
        "scrollTriggerScriptsInBuiltHtml": manifest["scrollTriggerScriptsInBuiltHtml"],
        "audits": manifest["audits"],
        "problems": problems,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Reflow Optimizer: ScrollTrigger-Skripte {report['scrollTriggerScriptsInBuiltHtml']} | Probleme {len(problems)}")
        for problem in problems[:40]:
            print("  ❌", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
