#!/usr/bin/env bash
# Holt die beiden einzigartigen Inhalte aus den Session-Branches, mit Blob-Beweis.
# Details + Bewertungen: BRANCH-RETENTION.md im Repo-Root.
set -Eeuo pipefail
OUT="${1:-geborgen}"; mkdir -p "$OUT"
API="https://api.github.com/repos/frank-hartung/franksfinanzcheck-blog/git/blobs"
fetch() { curl -fsSL -H "Accept: application/vnd.github.raw" "$API/$1" -o "$OUT/$2"; [ "$(git hash-object "$OUT/$2")" = "$1" ] && echo "✅ $2 ($(wc -c <"$OUT/$2") bytes)" || { echo "❌ Hash weicht ab: $2"; exit 1; }; }
fetch b90652b0dff3b97e4931437c4df35d1dede787a0 strom-sparen-pinterest.mp4
fetch 86f09eae793f202ba9e155352080de1229ce35d1 pinterest_trust_shield.py
