#!/usr/bin/env python3
"""Build Pagefind without feeding Google's plain-text verification file to it.

Google's verification endpoint must remain a byte-for-byte plain-text file in
`public/` for deployment. Pagefind expects HTML and warns about this one file;
it is therefore removed only during indexing and restored even if Pagefind
fails. The final published tree still contains the original verification file.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]


def build(site: Path, executable: str = "pagefind",
          run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> int:
    site = site.resolve()
    verification_files = sorted(site.glob("google*.html"))
    originals = [(path, path.read_bytes(), path.stat().st_mode) for path in verification_files]
    try:
        for path, _, _ in originals:
            path.unlink()
        result = run([
            executable, "--site", str(site), "--force-language", "de",
            "--exclude-selectors", "a.anchor",
        ], check=False)
        return int(result.returncode)
    finally:
        for path, content, mode in originals:
            path.write_bytes(content)
            os.chmod(path, mode)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "public",
                        help="Hugo-Ausgabe (Standard: public)")
    parser.add_argument("--pagefind", default="pagefind",
                        help="Pagefind-Executable aus PATH")
    args = parser.parse_args(argv)
    return build(args.site, args.pagefind)


if __name__ == "__main__":
    raise SystemExit(main())
