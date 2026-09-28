#!/usr/bin/env python3
"""Deterministic guard against accidental adjacent word repetitions.

Generated copy occasionally contains ``senken senken`` after a keyword
healing pass.  This guard is deliberately narrow: it only repairs the same
word repeated next to itself on one prose line, never across paragraph
boundaries, and never front matter.  It is idempotent and safe to run after
any copy-editing step.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
# Words and numbers are both covered; hyphens remain part of a word.
REPEAT = re.compile(
    r"(?i)(?<![\wÄÖÜäöüß-])"
    r"([\wÄÖÜäöüß]+(?:[-'][\wÄÖÜäöüß]+)*)"
    r"([ \t]+)\1"
    r"(?![\wÄÖÜäöüß-])"
)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end < 0:
        return "", text
    boundary = end + len("\n---")
    if boundary < len(text) and text[boundary] == "\n":
        boundary += 1
    return text[:boundary], text[boundary:]


def repetitions(text: str) -> list[tuple[int, str]]:
    """Return (line number, repeated phrase) without mutating *text*."""
    _, body = split_frontmatter(text)
    findings: list[tuple[int, str]] = []
    for line_no, line in enumerate(body.splitlines(), 1):
        # Headings and fenced code are not prose; avoid changing examples.
        if line.lstrip().startswith("#") or line.lstrip().startswith("```"):
            continue
        for match in REPEAT.finditer(line):
            findings.append((line_no, match.group(0)))
    return findings


def fix_text(text: str) -> tuple[str, int]:
    front, body = split_frontmatter(text)
    count = 0
    out = []
    in_fence = False
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if in_fence or stripped.startswith("#"):
            out.append(line)
            continue
        new_line, n = REPEAT.subn(r"\1", line)
        count += n
        out.append(new_line)
    return front + "".join(out), count


def selftest() -> None:
    cases = [
        ("Wer Gasrechnung senken senken will.", "Wer Gasrechnung senken will.", 1),
        ("Der Tarif ist sehr gut.", "Der Tarif ist sehr gut.", 0),
        ("Erste Zeile\n\nErste Zeile", "Erste Zeile\n\nErste Zeile", 0),
        ("---\ntitle: \"senken senken\"\n---\n\nsenken senken", "---\ntitle: \"senken senken\"\n---\n\nsenken", 1),
        ("```text\nsenken senken\n```", "```text\nsenken senken\n```", 0),
    ]
    for source, expected, count in cases:
        got, actual = fix_text(source)
        if got != expected or actual != count:
            raise AssertionError((source, got, actual, expected, count))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--new-only", action="store_true", help="only posts dated today")
    args = parser.parse_args()
    selftest()
    if args.selftest:
        print("Repetition-Guard-Selbsttest bestanden.")
        return 0
    today = __import__("datetime").date.today().isoformat()
    files = sorted(POSTS.glob("*/index.md"))
    if args.new_only:
        files = [p for p in files if p.parent.name.startswith(today)]
    total = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        found = repetitions(text)
        if found and args.fix:
            healed, count = fix_text(text)
            if healed != text:
                path.write_text(healed, encoding="utf-8")
            total += count
            print(f"✅ {path.relative_to(ROOT)}: {count} Doppelwort/Doppelwörter entfernt")
        elif found:
            for line, phrase in found:
                print(f"❌ {path.relative_to(ROOT)}:{line}: {phrase}")
    if total:
        print(f"Repetition-Guard: {total} Wiederholung(en) geheilt.")
    return 1 if any(repetitions(p.read_text(encoding="utf-8")) for p in files) and not args.fix else 0


if __name__ == "__main__":
    raise SystemExit(main())
