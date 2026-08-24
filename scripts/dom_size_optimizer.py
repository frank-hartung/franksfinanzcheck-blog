#!/usr/bin/env python3
"""Automatischer DOM-Größe-Optimierer für Hugo-Layouts.

Das Tool arbeitet wie ein Agentur-Quality-Gate für statische Layouts:
- misst Elementanzahl, DOM-Tiefe, direkte Kinder und Inline-SVGs pro HTML-Datei
- schreibt ein Manifest mit Budgets und Hotspots
- prüft den gebauten Output gegen feste DOM-Budgets
- macht Layout-Regeln sichtbar, damit neue Partials nicht wieder DOM-Ballast
  einschleppen

Nutzung:
    python3 scripts/dom_size_optimizer.py --fix
    hugo --minify
    python3 scripts/dom_size_optimizer.py --check
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
MANIFEST = BLOG_DIR / "data" / "dom_optimizer_manifest.json"

BUDGETS = {
    "maxElements": 700,
    "maxDepth": 15,
    "maxDirectChildren": 120,
    "maxInlineSvg": 4,
    "maxInlineSvgPaths": 8,
}


@dataclass
class PageStats:
    path: str
    elements: int
    maxDepth: int
    maxDirectChildren: int
    maxDirectChildrenNode: str
    inlineSvg: int
    inlineSvgPaths: int


class DomStatsParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.elements = 0
        self.max_depth = 0
        self.inline_svg = 0
        self.inline_svg_paths = 0
        self.children_count: dict[int, int] = {}
        self.node_labels: dict[int, str] = {}
        self.node_seq = 0
        self.node_stack: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self.elements += 1
        self.node_seq += 1
        node_id = self.node_seq
        label = tag
        classes = ""
        for k, v in attrs:
            if k == "class" and v:
                classes = "." + ".".join(v.split()[:3])
                break
        self.node_labels[node_id] = label + classes
        if self.node_stack:
            parent = self.node_stack[-1]
            self.children_count[parent] = self.children_count.get(parent, 0) + 1
        self.children_count.setdefault(node_id, 0)

        if tag == "svg":
            self.inline_svg += 1
        if tag == "path" and "svg" in self.stack:
            self.inline_svg_paths += 1

        depth = len(self.stack) + 1
        self.max_depth = max(self.max_depth, depth)
        if tag not in self.VOID:
            self.stack.append(tag)
            self.node_stack.append(node_id)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.VOID:
            return
        # HTML aus Hugo ist valide; defensiv bis zum passenden Tag zurückgehen.
        if tag in self.stack:
            while self.stack:
                popped = self.stack.pop()
                if self.node_stack:
                    self.node_stack.pop()
                if popped == tag:
                    break

    def stats(self, path: Path) -> PageStats:
        if self.children_count:
            node_id, max_children = max(self.children_count.items(), key=lambda item: item[1])
            node_label = self.node_labels.get(node_id, "unknown")
        else:
            max_children = 0
            node_label = "none"
        return PageStats(
            path=path.relative_to(BLOG_DIR).as_posix(),
            elements=self.elements,
            maxDepth=self.max_depth,
            maxDirectChildren=max_children,
            maxDirectChildrenNode=node_label,
            inlineSvg=self.inline_svg,
            inlineSvgPaths=self.inline_svg_paths,
        )


def parse_html(path: Path) -> PageStats:
    parser = DomStatsParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return parser.stats(path)


def collect_stats() -> list[PageStats]:
    if not PUBLIC_DIR.exists():
        return []
    return [parse_html(p) for p in sorted(PUBLIC_DIR.rglob("*.html"))]


def worst_pages(stats: list[PageStats], key: str, limit: int = 10) -> list[dict[str, Any]]:
    return [asdict(s) for s in sorted(stats, key=lambda s: getattr(s, key), reverse=True)[:limit]]


def build_manifest() -> dict[str, Any]:
    stats = collect_stats()
    return {
        "version": 1,
        "generatedBy": "scripts/dom_size_optimizer.py",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "budgets": BUDGETS,
        "strategy": {
            "externalizeComplexSvg": True,
            "avoidDecorativeInlineSvg": True,
            "preferAriaLabelOverHiddenTextNodesWhenEquivalent": True,
            "limitAboveFoldWrappers": True,
            "auditBuiltHtml": "hugo --minify && python3 scripts/dom_size_optimizer.py --check",
        },
        "summary": {
            "pages": len(stats),
            "maxElements": max((s.elements for s in stats), default=0),
            "maxDepth": max((s.maxDepth for s in stats), default=0),
            "maxDirectChildren": max((s.maxDirectChildren for s in stats), default=0),
            "maxInlineSvg": max((s.inlineSvg for s in stats), default=0),
            "maxInlineSvgPaths": max((s.inlineSvgPaths for s in stats), default=0),
        },
        "worstByElements": worst_pages(stats, "elements"),
        "worstByDepth": worst_pages(stats, "maxDepth"),
        "worstByChildren": worst_pages(stats, "maxDirectChildren"),
    }


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MANIFEST)


def check_stats(stats: list[PageStats]) -> list[str]:
    if not stats:
        return ["public/ fehlt oder enthält keine HTML-Dateien – zuerst `hugo --minify` ausführen"]
    problems: list[str] = []
    for s in stats:
        if s.elements > BUDGETS["maxElements"]:
            problems.append(f"{s.path}: {s.elements} Elemente > Budget {BUDGETS['maxElements']}")
        if s.maxDepth > BUDGETS["maxDepth"]:
            problems.append(f"{s.path}: DOM-Tiefe {s.maxDepth} > Budget {BUDGETS['maxDepth']}")
        if s.maxDirectChildren > BUDGETS["maxDirectChildren"]:
            problems.append(f"{s.path}: {s.maxDirectChildren} direkte Kinder in {s.maxDirectChildrenNode} > Budget {BUDGETS['maxDirectChildren']}")
        if s.inlineSvg > BUDGETS["maxInlineSvg"]:
            problems.append(f"{s.path}: {s.inlineSvg} inline SVGs > Budget {BUDGETS['maxInlineSvg']}")
        if s.inlineSvgPaths > BUDGETS["maxInlineSvgPaths"]:
            problems.append(f"{s.path}: {s.inlineSvgPaths} inline SVG-Pfade > Budget {BUDGETS['maxInlineSvgPaths']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="DOM-Größe-Optimierer für Hugo-Layouts")
    parser.add_argument("--fix", action="store_true", help="Manifest aus gebautem HTML schreiben")
    parser.add_argument("--check", action="store_true", help="gebautes HTML gegen DOM-Budget prüfen")
    parser.add_argument("--json", action="store_true", help="JSON-Report ausgeben")
    args = parser.parse_args()

    stats = collect_stats()
    manifest = build_manifest()
    if args.fix:
        write_manifest(manifest)
    problems = check_stats(stats) if args.check else []
    report = {
        "manifest": MANIFEST.relative_to(BLOG_DIR).as_posix(),
        "summary": manifest["summary"],
        "problems": problems,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "DOM Optimizer: "
            f"{manifest['summary']['pages']} Seiten | "
            f"Max Elemente {manifest['summary']['maxElements']} | "
            f"Max Tiefe {manifest['summary']['maxDepth']} | "
            f"Probleme {len(problems)}"
        )
        for problem in problems[:40]:
            print("  ❌", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
