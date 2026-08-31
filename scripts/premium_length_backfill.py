#!/usr/bin/env python3
"""Idempotente Premium-Längen-Auffüllung (kein Fülltext).

Module: data/length_modules/<slug>.md
Zweite Runde: data/length_modules/<slug>__2.md
Marker verhindern Doppel-Inserts.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import length_policy as lp  # noqa: E402

MOD_DIR = ROOT / "data" / "length_modules"
MARKER = lp.MARKER
MARKER_B = "<!-- premium-length-2026-b -->"
MARKER_C = "<!-- premium-length-2026-c -->"


def insert_point(text: str) -> int | None:
    for pat in (r"\n## Fazit", r"\n## .*Fazit.*", r"\n## Häufige Fragen",
                r"\n---\s*\n👉", r"\n---\s*\n\*Dieser Artikel"):
        m = re.search(pat, text)
        if m:
            return m.start()
    return None


def apply_one(path: Path, module: str, marker: str) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False, "bereits markiert"
    typ = lp.classify(path)
    _w, chars = lp.measure(text)
    floor = lp.POLICY[typ]["opt_min_chars"] if typ == "posts" else lp.POLICY[typ]["heal_chars"]
    if chars >= floor:
        return False, f"bereits {chars} Zeichen (Korridor ok)"
    block = "\n\n" + marker + "\n\n" + module.strip() + "\n"
    idx = insert_point(text)
    if idx is None:
        new = text.rstrip() + block + "\n"
    else:
        new = text[:idx].rstrip() + block + text[idx:]
    today = date.today().isoformat()
    if re.search(r"^lastmod:", new, re.M):
        new = re.sub(r"^lastmod:.*$", f"lastmod: {today}", new, count=1, flags=re.M)
    else:
        new = re.sub(r"^(---\n.*?^date:.*$)",
                     r"\1\nlastmod: " + today, new, count=1, flags=re.S | re.M)
    path.write_text(new, encoding="utf-8")
    _nw, nc = lp.measure(new)
    return True, f"{chars} → {nc} Zeichen"


def main() -> int:
    if not MOD_DIR.is_dir():
        print("keine Module in data/length_modules/")
        return 1
    n_ok = n_skip = 0
    matches = list((ROOT / "content").rglob("index.md"))
    for md in sorted(MOD_DIR.glob("*.md")):
        slug = md.stem
        module = md.read_text(encoding="utf-8")
        if slug.endswith("__3"):
            marker, key = MARKER_C, slug[:-3]
        elif slug.endswith("__2"):
            marker, key = MARKER_B, slug[:-3]
        else:
            marker, key = MARKER, slug
        targets = [p for p in matches if p.parent.name == key]
        if not targets:
            print(f"  ⚠ kein Artikel für Modul {slug}")
            continue
        for p in targets:
            ok, info = apply_one(p, module, marker)
            print(f"  {'✅' if ok else '·'} {p.parent.name}: {info}")
            n_ok += int(ok)
            n_skip += int(not ok)
    print(f"Premium-Backfill: {n_ok} erweitert, {n_skip} übersprungen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
