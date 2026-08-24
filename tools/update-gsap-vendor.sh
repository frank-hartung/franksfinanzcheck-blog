#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-3.13.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/static/premium/vendor"

curl -L --fail "https://cdn.jsdelivr.net/npm/gsap@${VERSION}/dist/gsap.min.js" \
  -o "$ROOT/static/premium/vendor/gsap.min.js"
curl -L --fail "https://cdn.jsdelivr.net/npm/gsap@${VERSION}/dist/ScrollTrigger.min.js" \
  -o "$ROOT/static/premium/vendor/ScrollTrigger.min.js"

printf 'GSAP %s wurde nach static/premium/vendor/ geladen.\n' "$VERSION"
