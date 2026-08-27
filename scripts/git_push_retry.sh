#!/usr/bin/env bash
# ============================================================
#  git_push_retry.sh – KOLLISIONSSICHERES PUSHEN FÜR ALLE BOTS
#  ------------------------------------------------------------
#  PROBLEM (Audit 27.08.2026): 18 Workflows committen und pushen
#  nach main. Das bisherige Muster
#      git pull --rebase --autostash origin main 2>/dev/null \
#        || git rebase --abort 2>/dev/null || true
#      git push
#  verliert bei Race-Conditions STILL die Heilung:
#    - Rebase-Konflikt → abort → push abgelehnt (non-fast-forward)
#      → Fehler wurde von `|| true` geschluckt, Commit weg.
#    - Zwei Bots pushen zeitgleich → ein push wird abgelehnt,
#      kein Retry → Heilung verloren.
#  Reale Folgen (25./26.08.2026): Merge-Marker in main, 19 tote
#  Links (Issue #85), gescheiterte „Gate-Heilungen committen“-
#  Steps, verlorene Fix-Commits, History-Neuschreibung um 00:00.
#
#  LÖSUNG (dieses Skript, von allen Bots benutzt):
#    1. Bis zu 3 Versuche: fetch + rebase (autostash) + push.
#    2. Rebase-Konflikt → LAUT scheitern (Exit 1) → der Workflow
#       wird rot → Fehler-Alerting öffnet ein Issue. Nichts geht
#       mehr still verloren.
#    3. NIEMALS force-push. Kein History-Rewrite. Konvergent.
#
#  AUFRUF (in Workflows, nach `git add` + `git commit`):
#    bash scripts/git_push_retry.sh "optional: eigene Commit-Msg-Zeile"
#
#  Exit-Codes: 0 = gepusht (oder nichts zu pushen) · 1 = gescheitert
# ============================================================
set -uo pipefail

REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
TRIES="${TRIES:-3}"
SLEEP_BASE="${SLEEP_BASE:-10}"

# Nichts zu pushen? → sauber grün raus.
if git diff "${REMOTE}/${BRANCH}".."HEAD" --quiet 2>/dev/null && \
   ! git log "${REMOTE}/${BRANCH}..HEAD" --format=%h 2>/dev/null | grep -q .; then
  echo "git_push_retry: nichts zu pushen – clean."
  exit 0
fi

for attempt in $(seq 1 "$TRIES"); do
  # 1) Fernstand holen
  if ! git fetch "$REMOTE" "$BRANCH" >/dev/null 2>&1; then
    echo "⚠ git_push_retry: fetch fehlgeschlagen (Versuch ${attempt}/${TRIES})"
  fi

  # 2) Rebasen (autostash hält uncommittete Artefakte wie Reports)
  if ! git rebase --autostash "${REMOTE}/${BRANCH}" >/dev/null 2>&1; then
    git rebase --abort >/dev/null 2>&1 || true
    echo "❌ git_push_retry: Rebase-Konflikt gegen ${REMOTE}/${BRANCH} (Versuch ${attempt}/${TRIES}) – Commit bleibt lokal erhalten."
  elif git push "$REMOTE" "HEAD:${BRANCH}" >/dev/null 2>&1; then
    echo "✅ git_push_retry: gepusht (Versuch ${attempt}/${TRIES})."
    exit 0
  else
    echo "⚠ git_push_retry: push abgelehnt (Race mit anderem Bot) – Retry folgt (Versuch ${attempt}/${TRIES})."
  fi

  # 3) Backoff vor dem nächsten Versuch (10s/20s/30s entzerrt Bots)
  if [ "$attempt" -lt "$TRIES" ]; then
    sleep $(( SLEEP_BASE * attempt ))
  fi
done

# 4) Laut scheitern: Workflow wird rot → Fehler-Alerting schlägt Alarm.
echo "❌ git_push_retry: PUSH GESCHEITERT nach ${TRIES} Versuchen – Commit ist NICHT verloren (lokal im Runner vorhanden), aber NICHT in main. Bitte manuell prüfen."
exit 1
