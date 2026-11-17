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
  # Die F4-Vorlage ist ebenfalls eine Projektion: Sie muss auf demselben
  # Ledger-/Text- und Aktenstand liegen, sonst fehlen offene Live-Befunde.
  python3 scripts/f4_entscheidungsvorlage.py
  # Und die Queue: `befund`/`unvollstaendig` sind BELEGTE Fakten (Ledger,
  # `abbrueche`) – nicht Besitz des letzten Laufs. Am 17.11.2026 stand eine
  # Seite als ARBEIT in `offen`, deren Text inzwischen überholt war: Der
  # Lauf war durch, die Behauptung blieb (#1126-Klasse). Diese Zeile leitet
  # sie auf jedem Inhalts-Push neu ab; ohne Änderung schreibt sie nichts.
  python3 scripts/faktenfrische.py --queue-normalisieren --apply
  if git diff -I'^[[:space:]]*"erzeugt":' --quiet -- BEFUND-AKTE.md data/faktenfrische_befunde_state.json F4-ENTSCHEIDUNGSVORLAGE.md data/faktenfrische_queue.json; then
    git checkout -- BEFUND-AKTE.md data/faktenfrische_befunde_state.json F4-ENTSCHEIDUNGSVORLAGE.md data/faktenfrische_queue.json
    echo 'Akte, Zustand, Queue und F4-Vorlage sind aktuell.'
    exit 0
  fi
  git add -- BEFUND-AKTE.md data/faktenfrische_befunde_state.json F4-ENTSCHEIDUNGSVORLAGE.md data/faktenfrische_queue.json
  python3 scripts/konfliktmarker_wache.py --staged
  git commit -m 'chore(faktenfrische): Akte, Stand und Queue nachgezogen [skip ci]'
  if git push origin HEAD:refs/heads/main; then
    echo 'Akte und Zustand auf demselben Quellstand veröffentlicht.'
    exit 0
  fi
  echo "::warning::Push fehlgeschlagen (Versuch $versuch); neuer main-Stand wird neu berechnet."
done
echo '::error::Akte konnte nach fünf Versuchen nicht veröffentlicht werden.' >&2
exit 1
