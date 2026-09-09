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
#  HÄRTUNG #233 (Wöchentliche SEO-Optimierung, 09.09.2026):
#    Der Lauf starb an "Pull von origin/main fehlgeschlagen – kein
#    Konflikt": ein EINMALIGER transienter Netzwerkfehler beim
#    `git pull` (fetch) reichte, weil nur der PUSH Retries hatte –
#    nicht der Fetch. Härtung in vier Lagen:
#      1. fetch_mit_retry(): fetch wird wiederholt (exponentielles
#         Backoff + Jitter), nach dem ersten Rückschlag zusätzlich mit
#         HTTP/1.1 (bekanntes Mittel gegen GitHubs „RPC failed; HTTP/2
#         stream"-Transients) und größerem postBuffer.
#      2. Fehlerklassifikation: Auth-/Berechtigungsfehler werden NICHT
#         wiederholt (sinnlos) sondern sofort und präzise gemeldet;
#         nur echte Transients werden wiederholt.
#      3. Rettungsanker: Schlägt der fetch endgültig fehl, wird ein
#         direkter Push versucht – ist origin nicht weitergelaufen,
#         geht er als Fast-Forward durch (Run bleibt grün).
#      4. Runden-Logik: Rebase+Push als Gesamtzyklus mit Wiederholung –
#         auch ein mitten im Rennen abgelehnter Push (paralleler Bot)
#         heilt sich durch erneutes Angleichen selbst.
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
#    GIT_SYNC_TRIES        Gesamt-Runden Rebase+Push   (Default: 3)
#    GIT_SYNC_FETCH_TRIES  Fetch-Versuche pro Runde    (Default: 3)
#    GIT_SYNC_BACKOFF      Backoff-Basis in Sekunden   (Default: 4)
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
GIT_SYNC_TRIES="${GIT_SYNC_TRIES:-3}"
GIT_SYNC_FETCH_TRIES="${GIT_SYNC_FETCH_TRIES:-3}"
GIT_SYNC_BACKOFF="${GIT_SYNC_BACKOFF:-4}"

# Warum der letzte Synchronisierungsversuch gescheitert ist:
#   netzwerk | auth | konflikt | rebase | autostash | leer
SYNC_FAIL_URSACHE=""

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

# ---------- Hilfen ------------------------------------------------------
# Auth-/Berechtigungsfehler erkennen: erneutes Versuchen ist sinnlos,
# sie müssen sofort, präzise und mit Handlungsempfehlung gemeldet werden.
ist_auth_fehler() {
  printf '%s' "$1" | grep -qiE \
    'could not read [Uu]sername|[Aa]uthentication failed|[Aa]uthorization failed|[Pp]ermission denied|[Aa]ccess denied|HTTP 403|403 [Ff]orbidden|remote: Permission to|supported authentication'
}

backoff_sekunden() {  # $1 = Rundennummer (1-basiert)
  local b="$GIT_SYNC_BACKOFF" d
  d=$(( b * (1 << ( ($1 - 1) > 4 ? 4 : ($1 - 1) )) ))
  d=$(( d + RANDOM % 3 ))   # Jitter gegen synchronisierte Bot-Retrys
  printf '%s' "$d"
}

# ========================================================================
#  fetch mit Retry – die eigentliche #233-Reparatur.
#  Ein einzelner Transient (GitHub-5xx, „Empty reply", „RPC failed;
#  curl 92 HTTP/2 stream", DNS-Hickser) darf keinen Lauf mehr rot machen.
# ========================================================================
fetch_mit_retry() {
  local i out versuche="$GIT_SYNC_FETCH_TRIES"
  for (( i = 1; i <= versuche; i++ )); do
    if out=$(git fetch origin "$BRANCH" --prune --no-tags 2>&1); then
      [ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/  fetch: /'
      return 0
    fi
    printf '%s\n' "$out" | sed 's/^/  fetch: /'
    if ist_auth_fehler "$out"; then
      SYNC_FAIL_URSACHE=auth
      echo "::error::git_sync.sh: fetch von origin/$BRANCH abgelehnt "\
           "(Auth/Berechtigung). Kein Retry sinnvoll – prüfe "\
           "'contents: write' im Workflow und den Token-Zugriff."
      return 1
    fi
    if (( i < versuche )); then
      echo "  fetch: Versuch $i/$versuche fehlgeschlagen (transient?) – "\
           "erneuter Versuch in $(backoff_sekunden "$i") s."
      sleep "$(backoff_sekunden "$i")"
      # Bekannte Gegenmittel bei HTTP/2-/Buffer-Transients nachrüsten
      # (schadet nie, hilft bei großen Pushes und Proxy-Zickereien):
      git config http.version HTTP/1.1        2>/dev/null || true
      git config http.postBuffer 33554432     2>/dev/null || true  # 32 MiB
    fi
  done
  SYNC_FAIL_URSACHE=netzwerk
  echo "::error::git_sync.sh: fetch von origin/$BRANCH nach $versuche "\
       "Versuchen fehlgeschlagen (Netzwerk-/GitHub-Transient)."
  return 1
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
  local conflicts f safe=1 guard=0
  conflicts=$(git diff --name-only --diff-filter=U || true)
  [ -n "$conflicts" ] || return 1

  # Mehrere Commits können nacheinander konflikten – solange heilen,
  # bis der Rebase durch ist (Guard gegen Endlosschleifen).
  while [ -n "$(git diff --name-only --diff-filter=U || true)" ]; do
    guard=$(( guard + 1 ))
    if [ "$guard" -gt 25 ]; then
      echo "  rebase: zu viele Konfliktwellen – Abbruch."
      return 1
    fi
    conflicts=$(git diff --name-only --diff-filter=U || true)
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

    GIT_EDITOR=true git rebase --continue 2>&1 | sed 's/^/  rebase: /' || true
  done

  # Der Rebase muss jetzt WIRKLICH beendet sein (kein rebase-merge/-apply
  # mehr vorhanden), sonst war die letzte Welle doch nicht heilbar.
  if [ -d "$(git rev-parse --git-path rebase-merge 2>/dev/null)" ] || \
     [ -d "$(git rev-parse --git-path rebase-apply 2>/dev/null)" ]; then
    echo "  rebase: trotz Konfliktlösung nicht abgeschlossen – Abbruch."
    return 1
  fi
  return 0
}

rebase_gegen_origin() {
  local out ahead rebase_dir

  # 1) Aktuellen Stand holen – MIT Retry (die #233-Ursache war genau hier).
  fetch_mit_retry || return 1

  # 2) Rebase überhaupt nötig? (spart Autostash-Risiken im Normalfall)
  if ahead=$(git rev-list --count "HEAD..origin/$BRANCH" 2>/dev/null) \
     && [ "$ahead" -eq 0 ]; then
    echo "  rebase: origin/$BRANCH nicht weitergelaufen – kein Rebase nötig."
    return 0
  fi

  # 3) Rebase mit Autostash gegen den frischen Stand.
  if ! out=$(git rebase --autostash "origin/$BRANCH" 2>&1); then
    printf '%s\n' "$out" | sed 's/^/  rebase: /'
    rebase_dir=$(git rev-parse --git-path rebase-merge 2>/dev/null || true)
    if [ -d "$rebase_dir" ] || [ -d "$(git rev-parse --git-path rebase-apply 2>/dev/null || true)" ]; then
      if auto_resolve_generated_rebase_conflicts; then
        echo "  rebase: generierte Bot-Artefakt-Konflikte automatisch gelöst."
        return 0
      fi
      git rebase --abort 2>/dev/null || true
      SYNC_FAIL_URSACHE=konflikt
      echo "::error::git_sync.sh: Rebase-Konflikt gegen origin/$BRANCH "\
           "(ein paralleler Workflow hat dieselben Zeilen geändert). "\
           "Kein Push – Arbeitsstand bleibt lokal sauber. "\
           "Nur echte Content-Konflikte benötigen manuelles Mergen; "\
           "generierte Report-/JSONL-Konflikte werden automatisch geheilt."
    elif printf '%s' "$out" | grep -qi 'autostash'; then
      # Extremfall: Rebase selbst ok, aber das Wiedereinsetzen des Autostash
      # stand in Konflikt. Die Änderungen liegen sicher im Stash – laut
      # melden statt halb zurücklassen.
      SYNC_FAIL_URSACHE=autostash
      echo "::error::git_sync.sh: Autostash konnte nach dem Rebase nicht "\
           "wieder eingesetzt werden. Die lokalen Änderungen liegen sicher "\
           "im Stash ('git stash list') – bitte aufräumen und erneut laufen "\
           "lassen. Kein Push."
    else
      SYNC_FAIL_URSACHE=rebase
      echo "::error::git_sync.sh: Rebase gegen origin/$BRANCH ohne Konflikt-"\
           "Marker gescheitert (siehe rebase-Ausgabe oben). Kein Push."
    fi
    return 1
  fi
  printf '%s\n' "$out" | sed 's/^/  rebase: /'
  return 0
}

# ========================================================================
#  Synchronisieren ALS GANZES mit Runden-Logik:
#    Runde = fetch(+Retry) → rebase(Selbstheilung) → push
#  Schlägt ein Teil ab (paralleler Bot, Transient), wird die Runde
#  wiederholt – bis zu GIT_SYNC_TRIES Mal mit exponentiellem Backoff.
# ========================================================================
sync_und_push() {
  local runde out
  for (( runde = 1; runde <= GIT_SYNC_TRIES; runde++ )); do
    SYNC_FAIL_URSACHE=""

    if rebase_gegen_origin; then
      if out=$(git push origin "HEAD:$BRANCH" 2>&1); then
        printf '%s\n' "$out" | sed 's/^/  push: /'
        return 0
      fi
      printf '%s\n' "$out" | sed 's/^/  push: /'
      if ist_auth_fehler "$out"; then
        SYNC_FAIL_URSACHE=auth
        echo "::error::git_sync.sh: Push auf origin/$BRANCH abgelehnt "\
             "(Auth/Berechtigung) – kein Retry sinnvoll. Prüfe "\
             "'contents: write' im Workflow, Branch-Schutz und den Token."
        return 1
      fi
      echo "  push: Versuch $runde/$GIT_SYNC_TRIES fehlgeschlagen – "\
           "angleichen und erneut versuchen."
    else
      case "$SYNC_FAIL_URSACHE" in
        netzwerk)
          # RETTUNGSANKER: Der fetch ist an Netzwerk/Transient gescheitert.
          # Ist origin/$BRANCH gar nicht weitergelaufen (sehr wahrscheinlich
          # bei einem Gesamt-Ausfall), ist ein direkter Push trotzdem ein
          # sauberes Fast-Forward – dann bleibt der Lauf grün.
          echo "  push: Rettungsanker – direkter Push-Versuch ohne fetch …"
          if out=$(git push origin "HEAD:$BRANCH" 2>&1); then
            printf '%s\n' "$out" | sed 's/^/  push: /'
            echo "  push: Rettungsanker erfolgreich (origin war nicht weitergelaufen)."
            return 0
          fi
          printf '%s\n' "$out" | sed 's/^/  push: /'
          if ist_auth_fehler "$out"; then
            SYNC_FAIL_URSACHE=auth
            echo "::error::git_sync.sh: Auch der Rettungsanker-Push wurde "\
                 "abgelehnt (Auth/Berechtigung) – kein Retry sinnvoll."
            return 1
          fi
          ;;
        auth)
          return 1
          ;;
        *)
          # konflikt / rebase / autostash: gezielt gescheitert –
          # ein Repeat ändert daran nichts, kein Blind-Versuch.
          return 1
          ;;
      esac
    fi

    if (( runde < GIT_SYNC_TRIES )); then
      local w
      w=$(backoff_sekunden "$runde")
      echo "  sync: neue Runde in ${w} s (Versuch $(( runde + 1 ))/$GIT_SYNC_TRIES)…"
      sleep "$w"
    fi
  done

  SYNC_FAIL_URSACHE="${SYNC_FAIL_URSACHE:-netzwerk}"
  echo "::error::git_sync.sh: Synchronisation nach $GIT_SYNC_TRIES Runden "\
       "fehlgeschlagen (zuletzt: $SYNC_FAIL_URSACHE). Mögliche Ursachen: "\
       "GitHub-Transient, fehlende 'contents: write'-Berechtigung, "\
       "Branch-Schutz oder ein anderer Workflow schreibt gleichzeitig."
  return 1
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
  sync_und_push    || exit 1
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

sync_und_push    || exit 1

echo "git_sync.sh: Push erfolgreich."
sync_ok
