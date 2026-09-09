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
#    BRANCH       Zielbranch (Default: GITHUB_HEAD_REF/REF_NAME, sonst main)
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

# Auf GitHub Actions immer den tatsächlich ausgecheckten Ref verwenden.
# So kann ein workflow_dispatch auf einem Prüf-/Feature-Branch niemals
# versehentlich dessen HEAD nach main pushen.
BRANCH="${BRANCH:-${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-main}}}"
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
# Automatische Konfliktlösung für rein generierte Bot-Artefakte.
# Hintergrund: Lange SEO-/Content-Läufe starten auf einem alten main-Stand,
# während andere Bots Reports/JSONL-Historien fortschreiben. Das ist kein
# fachlicher Konflikt und soll keinen roten Run erzeugen (#233-Klasse).
# Content-Dateien bleiben bewusst tabu: echter Textkonflikt => harter Fehler.
auto_resolve_generated_rebase_conflicts() {
  local conflicts f safe=1
  conflicts=$(git diff --name-only --diff-filter=U || true)
  [ -n "$conflicts" ] || return 1

  echo "  rebase: prüfe automatisch lösbare Bot-Artefakt-Konflikte:"
  printf '%s\n' "$conflicts" | sed 's/^/    - /'

  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      data/*.jsonl|data/**/*.jsonl|*.jsonl)
        # JSONL-Historien sind append-only. Nimm beide Seiten, entferne
        # exakte Duplikate und halte die Datei valides zeilenbasiertes JSON.
        python3 - "$f" <<'PY'
import pathlib, subprocess, sys
path = pathlib.Path(sys.argv[1])
parts = []
for stage in (2, 3):
    r = subprocess.run(["git", "show", f":{stage}:{path.as_posix()}"], text=True, capture_output=True)
    if r.returncode == 0:
        parts.extend(r.stdout.splitlines())
seen = set()
out = []
for line in parts:
    if not line.strip():
        continue
    if line in seen:
        continue
    seen.add(line)
    out.append(line)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
PY
        git add -- "$f"
        ;;
      *-REPORT.md|*REPORT.md|*STATUS.md|BOT-STATUS.md|PRODUKTIONS-STATUS.md|PIN-STATUS.md|SOCIAL-STATUS.md|ENGINE-STATUS.md)
        # Reports/Statusseiten werden vollständig aus dem aktuellen Lauf
        # erzeugt. Beim Rebase ist --theirs der gerade zu pushende Bot-Commit.
        git checkout --theirs -- "$f" >/dev/null 2>&1 || safe=0
        git add -- "$f"
        ;;
      .meta_cache.json|.meta_report.json|.keyword_suggestions.json|.affiliate_report.json|.affiliate_integrity_state.json|.indexnow_submitted.json)
        git checkout --theirs -- "$f" >/dev/null 2>&1 || safe=0
        git add -- "$f"
        ;;
      *)
        safe=0
        ;;
    esac
  done <<< "$conflicts"

  if [ "$safe" -ne 1 ]; then
    echo "  rebase: enthält nicht automatisch lösbare Dateien – kein Blind-Merge."
    return 1
  fi

  if git diff --name-only --diff-filter=U | grep -q .; then
    echo "  rebase: Restkonflikte vorhanden – Abbruch."
    return 1
  fi

  GIT_EDITOR=true git rebase --continue 2>&1 | sed 's/^/  rebase: /'
}

rebase_gegen_origin() {
  local out
  if ! out=$(git pull --rebase --autostash origin "$BRANCH" 2>&1); then
    printf '%s\n' "$out" | sed 's/^/  rebase: /'
    # Ursache unterscheiden: läuft noch ein Rebase, ist es ein echter
    # Konflikt. Sonst war es Netzwerk/Auth – eine völlig andere Maßnahme.
    if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
      if auto_resolve_generated_rebase_conflicts; then
        echo "  rebase: generierte Bot-Artefakt-Konflikte automatisch gelöst."
        return 0
      fi
      git rebase --abort 2>/dev/null || true
      echo "::error::git_sync.sh: Rebase-Konflikt gegen origin/$BRANCH "\
           "(ein paralleler Workflow hat dieselben Zeilen geändert). "\
           "Kein Push – Arbeitsstand bleibt lokal sauber. "\
           "Nur echte Content-Konflikte benötigen manuelles Mergen; "\
           "generierte Report-/JSONL-Konflikte werden automatisch geheilt."
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
    # kann inzwischen committet haben. Dabei dieselbe Premium-Konflikt-
    # Selbstheilung nutzen wie beim ersten Rebase (JSONL/Reports).
    if ! rebase_gegen_origin; then
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
