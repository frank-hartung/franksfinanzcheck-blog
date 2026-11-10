#!/usr/bin/env bash
# Nur im isolierten Actions-Checkout: Projektion auf dem jeweils neuesten main
# erzeugen und ausschließlich als Fast-Forward veröffentlichen. Ein Rebase einer
# alten Projektion würde neuere Queue-/Textänderungen unsichtbar überschreiben.
set -Eeuo pipefail

if [[ "${GITHUB_ACTIONS:-}" != true || "${GITHUB_REF:-}" != refs/heads/main ]]; then
  echo '::error::Befundakten-Sync nur im Actions-Checkout von main erlaubt.' >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo '::error::Checkout nicht sauber; kein Reset und kein Push.' >&2
  exit 1
fi

git config user.name "${GIT_USER:-Faktenfrische-Akte-Bot}"
git config user.email "${GIT_MAIL:-faktenfrische-bot@users.noreply.github.com}"

for versuch in 1 2 3 4 5; do
  git fetch --no-tags origin refs/heads/main
  git reset --hard FETCH_HEAD
  python3 scripts/faktenfrische_befund_akte.py --schreiben
  if git diff -I'^[[:space:]]*"erzeugt":' --quiet -- BEFUND-AKTE.md data/faktenfrische_befunde_state.json; then
    git checkout -- BEFUND-AKTE.md data/faktenfrische_befunde_state.json
    echo 'Akte und Zustand sind aktuell.'
    exit 0
  fi
  git add -- BEFUND-AKTE.md data/faktenfrische_befunde_state.json
  python3 scripts/konfliktmarker_wache.py --staged
  git commit -m 'chore(faktenfrische): Akte und Stand nachgezogen [skip ci]'
  if git push origin HEAD:refs/heads/main; then
    echo 'Akte und Zustand auf demselben Quellstand veröffentlicht.'
    exit 0
  fi
  echo "::warning::Push fehlgeschlagen (Versuch $versuch); neuer main-Stand wird neu berechnet."
done
echo '::error::Akte konnte nach fünf Versuchen nicht veröffentlicht werden.' >&2
exit 1
