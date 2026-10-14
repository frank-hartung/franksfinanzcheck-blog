#!/usr/bin/env bash
# ============================================================
#  CLEANUP-ISSUES – Erledigte Fehlermeldungen ARCHIVIEREN
#
#  Sicherheitsaudit 14.10.2026 (M-08): Bis dahin löschte dieses Skript
#  geschlossene Bot-Issues nach 14 Tagen ENDGÜLTIG – mit einem Admin-PAT
#  im CI. Damit gingen Fehler- und Vorfallshistorie verloren, die für
#  Forensik und Nachweisführung gebraucht wird, und ein Admin-Token lag
#  in einem Workflow, den jeder mit Schreibrecht auf main ändern kann.
#
#  Jetzt: Geschlossene Bot-Issues werden nach der Schonfrist GESPERRT
#  (lock, Grund „resolved“) und mit dem Label „archiviert“ versehen.
#  Sie verschwinden aus der Standardansicht (is:open), bleiben aber
#  nachweisbar. Dafür reicht der GITHUB_TOKEN mit `issues: write` –
#  kein Admin-PAT mehr.
#
#  SICHERHEITSREGELN (wer wird archiviert?):
#    • NUR geschlossene Issues
#    • NUR Issues von Automations-Bots (github-actions[bot])
#    • NUR Issues, die älter als GRACE_DAYS Tage geschlossen wurden
#    • Bereits gesperrte Issues werden übersprungen (idempotent)
#
#  Umgebungsvariablen:
#    GH_TOKEN     GITHUB_TOKEN (issues: write)
#    GRACE_DAYS   Schonfrist in Tagen (Standard: 14)
#    DRY_RUN      "true" nur anzeigen (Standard: false)
#    BOT_AUTHOR   Autor-Filter (Standard: github-actions[bot])
# ============================================================
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-}"
GRACE_DAYS="${GRACE_DAYS:-14}"
DRY_RUN="${DRY_RUN:-false}"
BOT_AUTHOR="${BOT_AUTHOR:-github-actions[bot]}"
LABEL="archiviert"

if [ -z "$REPO" ]; then
  echo "FEHLER: GITHUB_REPOSITORY ist nicht gesetzt."
  exit 1
fi
if [ -z "${GH_TOKEN:-}" ]; then
  echo "FEHLER: GH_TOKEN fehlt (GITHUB_TOKEN mit issues: write)."
  exit 1
fi
case "$GRACE_DAYS" in
  ''|*[!0-9]*) echo "FEHLER: GRACE_DAYS muss eine Zahl sein: '$GRACE_DAYS'"; exit 1 ;;
esac

CUTOFF="$(date -u -d "${GRACE_DAYS} days ago" +%s)"

if [ "$DRY_RUN" = "true" ]; then
  echo "MODE: DRY-RUN (zeigt nur an) · Schonfrist: ${GRACE_DAYS} Tage"
else
  echo "MODE: ARCHIVIEREN (sperren + Label „${LABEL}“, NICHT löschen) · Schonfrist: ${GRACE_DAYS} Tage"
  gh label create "$LABEL" --repo "$REPO" --color "BFBFBF" \
    --description "Erledigt, gesperrt und archiviert (nicht gelöscht – Nachweis)" >/dev/null 2>&1 || true
fi

mapfile -t ISSUES < <(gh issue list --repo "$REPO" --state closed \
  --author "$BOT_AUTHOR" --limit 1000 \
  --json number,title,closedAt,labels \
  --jq ".[] | select(.closedAt != null) | select([.labels[].name] | index(\"${LABEL}\") | not) | [.number, .closedAt, .title] | @tsv")

if [ "${#ISSUES[@]}" -eq 0 ]; then
  echo "Keine noch nicht archivierten geschlossenen Bot-Issues – nichts zu tun."
  exit 0
fi

ARCHIVIERT=0; BEHALTEN=0; FEHLER=0
for line in "${ISSUES[@]}"; do
  [ -z "$line" ] && continue
  num="$(printf '%s' "$line" | cut -f1)"
  closed="$(printf '%s' "$line" | cut -f2)"
  title="$(printf '%s' "$line" | cut -f3-)"
  closed_ts="$(date -u -d "$closed" +%s 2>/dev/null || echo 0)"
  if [ "$closed_ts" -ge "$CUTOFF" ]; then
    BEHALTEN=$((BEHALTEN + 1))
    continue
  fi
  if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY-RUN] würde archivieren: #${num} (geschlossen ${closed}) – ${title}"
    continue
  fi
  ok=true
  gh issue edit "$num" --repo "$REPO" --add-label "$LABEL" >/dev/null || ok=false
  # lock ist idempotent genug: ein bereits gesperrtes Issue liefert einen Fehler,
  # der hier bewusst nicht zählt.
  gh issue lock "$num" --repo "$REPO" --reason resolved >/dev/null 2>&1 || true
  if $ok; then
    echo "→ #${num} archiviert: ${title}"
    ARCHIVIERT=$((ARCHIVIERT + 1))
  else
    echo "→ #${num} konnte NICHT archiviert werden: ${title}"
    FEHLER=$((FEHLER + 1))
  fi
done

echo ""
echo "Fertig: ${ARCHIVIERT} archiviert · ${BEHALTEN} innerhalb der Schonfrist · ${FEHLER} Fehler."
[ "$FEHLER" -eq 0 ]
