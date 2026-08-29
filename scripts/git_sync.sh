#!/usr/bin/env bash
# ============================================================
#  git_sync.sh – zentraler, robuster Commit+Push für ALLE Workflows
#  ------------------------------------------------------------
#  ERSETZT das in 16 von 27 Workflows kopierte Muster (31 Stellen):
#
#      git add <pfad> 2>/dev/null || true
#      ...
#      if git diff --cached --quiet; then ... else
#        git commit -m "..."
#        git pull --rebase --autostash origin main 2>/dev/null \
#            || git rebase --abort 2>/dev/null || true   # <- Fehler verschluckt
#        git push                                        # <- ungeschützt -> rejected
#      fi
#
#  DREI FEHLER DARIN:
#    1. Der Rebase-Fehler wird mit `|| true` verschluckt. Danach wird
#       trotzdem gepusht -> non-fast-forward -> "rejected" -> roter Run
#       MIT einer Meldung, die nichts über die eigentliche Ursache sagt.
#    2. `git push` ohne Retry: ein Transient-Fehler (GitHub-5xx, kurzer
#       Netzwerk-Blip) oder ein paralleler Commit eines ANDEREN deiner
#       27 Workflows macht den Lauf rot.
#    3. Kein Staging-Schutz: es wird blind alles gestagt (bei dir teils
#       `git add content/`, d.h. auch fremde, laufende Änderungen).
#
#  ZWEI BETRIEBSARTEN
#    a) Vollständig – stagen, committen, rebasen, pushen:
#         scripts/git_sync.sh "<commit-message>" <pfad1> [pfad2 ...]
#
#    b) Nur Rebase+Push – der Commit kam schon aus dem Workflow:
#         scripts/git_sync.sh --push-only
#       Das ist der Modus für die Bestandsumstellung: alle `git add`-
#       und `git commit`-Zeilen bleiben unangetastet, nur die zwei
#       kaputten Zeilen werden ersetzt. Minimaler Diff, maximale Wirkung.
#
#  Umgebung:
#    BRANCH       Zielbranch                    (Default: main)
#    GIT_USER     Committer-Name                (Default: Automation-Bot)
#    GIT_MAIL     Committer-E-Mail
#    DRY_RUN=1    nur anzeigen, nichts pushen
#    SYNC_OK_VAR  Name der Variable, die bei ERFOLG in $GITHUB_ENV
#                 geschrieben wird (Default: GEHEILT). Damit bleiben
#                 bestehende Auswertungen wie `if: env.ARTIKEL_ERSTELLT
#                 == 'true'` unverändert nutzbar – nur ehrlicher:
#                 gesetzt wird sie erst NACHweislich erfolgreichem Push.
#
#  Exit-Codes:
#    0 = alles ok (oder nichts zu committen / nichts zu pushen)
#    1 = KEIN Commit (sauber, kein Halb-Zustand) – Rebase/Push endgültig
#        fehlgeschlagen
# ============================================================
set -Eeuo pipefail

BRANCH="${BRANCH:-main}"
GIT_USER="${GIT_USER:-Automation-Bot}"
GIT_MAIL="${GIT_MAIL:-automation-bot@users.noreply.github.com}"
DRY_RUN="${DRY_RUN:-0}"
SYNC_OK_VAR="${SYNC_OK_VAR:-GEHEILT}"

PUSH_ONLY=0
if [ "${1:-}" = "--push-only" ]; then
  PUSH_ONLY=1
  shift
fi

MSG="${1:-}"
[ "$PUSH_ONLY" = "0" ] && { shift || true; }

# ---------- Identität ---------------------------------------------------
if [ "$PUSH_ONLY" = "1" ]; then
  # Der Commit kam aus dem Workflow – dessen Identität darf nicht
  # überschrieben werden (sonst ändert ein Rebase den Committer).
  # Nur setzen, falls noch gar nichts konfiguriert ist: `git stash`
  # (via --autostash) benötigt eine Identität.
  git config user.name  >/dev/null 2>&1 || git config user.name  "$GIT_USER"
  git config user.email >/dev/null 2>&1 || git config user.email "$GIT_MAIL"
else
  if [ -z "$MSG" ]; then
    echo "::error::git_sync.sh: Commit-Message fehlt. Benutzung: git_sync.sh \"<msg>\" <pfad...>"
    exit 1
  fi
  git config user.name  "$GIT_USER"
  git config user.email "$GIT_MAIL"
fi

# ---------- Erfolg an die Workflow-Umgebung melden ----------------------
sync_ok() {
  if [ -n "${GITHUB_ENV:-}" ]; then
    echo "${SYNC_OK_VAR}=true" >> "$GITHUB_ENV"
  fi
}

# ========================================================================
#  Rebase gegen den aktuellen Stand (SICHTBAR, ohne `|| true`)
# ========================================================================
rebase_gegen_origin() {
  local out
  if ! out=$(git pull --rebase --autostash origin "$BRANCH" 2>&1); then
    printf '%s\n' "$out" | sed 's/^/  rebase: /'
    # Ursache unterscheiden: läuft noch ein Rebase, ist es ein echter
    # Konflikt. Sonst war es Netzwerk/Auth – eine völlig andere Maßnahme.
    if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
      git rebase --abort 2>/dev/null || true
      echo "::error::git_sync.sh: Rebase-Konflikt gegen origin/$BRANCH "\
           "(ein paralleler Workflow hat dieselben Zeilen geändert). "\
           "Kein Push – Arbeitsstand bleibt lokal sauber. "\
           "Nächster Lauf übernimmt es; bei Dauer-Konflikt Datei manuell mergen."
    else
      echo "::error::git_sync.sh: Pull von origin/$BRANCH fehlgeschlagen "\
           "(Netzwerk, Auth oder fehlende 'contents: write'-Berechtigung) – kein Konflikt."
    fi
    return 1
  fi
  printf '%s\n' "$out" | sed 's/^/  rebase: /'
  return 0
}

# ========================================================================
#  Push mit Retry
# ========================================================================
push_mit_retry() {
  local i ok=0
  for i in 1 2 3; do
    if git push origin "HEAD:$BRANCH" 2>&1 | sed 's/^/  push: /'; then
      ok=1
      break
    fi
    echo "  push: Versuch $i fehlgeschlagen – neuer Versuch in 5 s."
    sleep 5
    # Vor dem nächsten Versuch erneut angleichen: ein anderer Workflow
    # kann inzwischen committet haben.
    if ! git pull --rebase --autostash origin "$BRANCH" >/dev/null 2>&1; then
      git rebase --abort 2>/dev/null || true
      break
    fi
  done
  if [ "$ok" -ne 1 ]; then
    echo "::error::git_sync.sh: Push nach 3 Versuchen fehlgeschlagen. "\
         "Mögliche Ursachen: fehlende 'contents: write'-Berechtigung, "\
         "Branch-Schutz, oder ein anderer Workflow schreibt gleichzeitig."
    return 1
  fi
  return 0
}

# ========================================================================
#  b) --push-only: nur rebasen und pushen
# ========================================================================
if [ "$PUSH_ONLY" = "1" ]; then
  # Nichts zu pushen? Dann ist alles gut (z. B. identischer Commit
  # eines parallelen Laufs) – kein Fehler.
  #
  # WICHTIG: Der Kurzschluss darf NUR greifen, wenn das Remote-Ref
  # tatsächlich auflösbar ist. Sonst würde ein nicht erreichbares oder
  # noch leeres Remote als "nichts zu pushen" durchgehen – genau die
  # Verschleierung, die dieses Skript abschaffen soll.
  if git rev-parse --verify -q "origin/$BRANCH" >/dev/null 2>&1; then
    if [ -z "$(git log "origin/$BRANCH..HEAD" --oneline)" ]; then
      echo "git_sync.sh: nichts zu pushen (HEAD ist bereits in origin/$BRANCH)."
      sync_ok
      exit 0
    fi
  else
    echo "  hinweis: origin/$BRANCH hier nicht auflösbar – Push wird trotzdem versucht."
  fi
  if [ "$DRY_RUN" = "1" ]; then
    echo "DRY_RUN – würde pushen:"; git log origin/"$BRANCH"..HEAD --oneline
    sync_ok
    exit 0
  fi
  rebase_gegen_origin || exit 1
  push_mit_retry     || exit 1
  echo "git_sync.sh: Push erfolgreich."
  sync_ok
  exit 0
fi

# ========================================================================
#  a) Vollständig: stagen, committen, rebasen, pushen
# ========================================================================
staged=0
for p in "$@"; do
  [ -n "$p" ] || continue
  if [ -e "$p" ] || [ -d "$p" ] || git ls-files --error-unmatch "$p" >/dev/null 2>&1; then
    if git add -- "$p"; then
      staged=$((staged + 1))
      echo "  + gestagt: $p"
    else
      echo "::warning::git_sync.sh: '$p' konnte nicht gestagt werden – übersprungen."
    fi
  else
    echo "  - übersprungen (nicht vorhanden): $p"
  fi
done

if [ "$staged" -eq 0 ] || git diff --cached --quiet; then
  echo "git_sync.sh: keine Änderungen – nichts zu committen."
  exit 0
fi

echo "git_sync.sh: committe $staged Pfad(e) auf '$BRANCH'…"
if [ "$DRY_RUN" = "1" ]; then
  git diff --cached --stat
  echo "DRY_RUN – kein Commit, kein Push."
  exit 0
fi

git commit -m "$MSG"

rebase_gegen_origin || exit 1
push_mit_retry     || exit 1

echo "git_sync.sh: Push erfolgreich."
sync_ok
