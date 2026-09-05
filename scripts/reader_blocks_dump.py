#!/usr/bin/env python3
"""reader_blocks_dump.py — Blockliste der TONSPUR als JSON.

Zweck: Paritäts-Gate zwischen Tonspur und Browser-Reader.

    python3 scripts/reader_blocks_dump.py <artikel.html>

Gibt auf stdout eine JSON-Liste aus:

    [{"type": "table-row", "lang": "de", "text": "…"}, …]

Das ist exakt die Blockfolge, die scripts/generate_reader_audio.py für die
vorab vertonte Tonspur erzeugt. Der Funktionstest
scripts/reader_table_progress_test.mjs vergleicht sie Block für Block mit
collectBlocks() aus static/premium/ff-reader.js (echte DOM, jsdom).

Warum das nötig ist: Tonspur und Browser-Reader sind zwei getrennte
Implementierungen derselben Extraktion. Weichen sie ab, hört der Nutzer
einen anderen Text, als die Live-Markierung zeigt — und der Fortschritt
läuft aus dem Tritt. Ohne dieses Gate fällt das erst im Betrieb auf.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_generator():
    """generate_reader_audio.py laden, ohne den CLI-Teil auszuführen."""
    path = os.path.join(ROOT, "scripts", "generate_reader_audio.py")
    spec = importlib.util.spec_from_file_location("ff_reader_audio", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ff_reader_audio"] = module
    spec.loader.exec_module(module)
    return module


def blocks_for_html(html: str, title: str, lang: str, reading_time: str) -> list[dict]:
    gra = load_generator()
    parser = gra.DocParser()
    parser.feed(html)
    parser.close()
    blocks = gra.collect_blocks(parser.root, title, lang, reading_time)
    return [{"type": t, "lang": l, "text": x} for (l, t, x) in blocks]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        html = fh.read()
    title = argv[2] if len(argv) > 2 else "Testartikel"
    lang = argv[3] if len(argv) > 3 else "de"
    reading_time = argv[4] if len(argv) > 4 else "1"
    json.dump(blocks_for_html(html, title, lang, reading_time),
              sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
