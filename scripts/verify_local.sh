#!/usr/bin/env bash
# Reproduzierbare Linux-x86_64-Prüfung ohne globale pip-Installation.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-ci.txt -r requirements-hugo.txt
export PATH="$PWD/.venv/bin:$PATH"
python -c 'import subprocess; v=subprocess.check_output(["hugo", "version"], text=True); print(v.strip()); assert v.startswith("hugo v0.168.0-") and "+extended" in v, "Hugo-Version/Extended stimmt nicht"'
python -m unittest discover -s scripts/tests -v
python scripts/lesbarkeit_heiler.py --wirkungsprobe
# Frisches temporäres Ziel: kein falsches Grün durch alte Build-Artefakte.
ziel="$(mktemp -d)"
trap 'rm -rf "$ziel"' EXIT
hugo --minify --destination "$ziel" --cleanDestinationDir
test -s "$ziel/index.html"
test -s "$ziel/sitemap.xml"
