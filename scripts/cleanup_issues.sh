#!/usr/bin/env bash
# ============================================================
#  CLEANUP-ISSUES – Erledigte Fehlermeldungen DAUERHAFT löschen
#
#  Sorgt dafür, dass auf GitHub nur OFFENE Fehlermeldungen sichtbar
#  bleiben: Geschlossene, automatisch erzeugte Issues werden nach
#  Ablauf der Schonfrist (GRACE_DAYS) endgültig gelöscht – nicht nur
#  "geschlossen" gelassen.
#
#  SICHERHEITSREGELN (wer wird gelöscht?):
#    • NUR geschlossene Issues
#    • NUR Issues von Automations-Bots (github-actions[bot]) –
#      von dir manuell geschriebene Issues bleiben IMMER erhalten
#    • NUR Issues, die älter als GRACE_DAYS Tage geschlossen wurden
#
#  ACHTUNG: Löschen ist endgültig (nicht wiederherstellbar) und
#  benötigt Admin-Rechte am Repo! → ANLEITUNG-ISSUE-MANAGEMENT.md
#
#  Umgebungsvariablen:
#    GH_TOKEN     PAT eines Repo-Admins (Secret "GH_PAT")
#    GRACE_DAYS   Schonfrist in Tagen (Standard: 14)
#    DRY_RUN      "true" nur anzeigen, was gelöscht würde (Standard: false)
#    BOT_AUTHOR   Autor-Filter (Standard: github-actions[bot])
# ============================================================
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-}"
GRACE_DAYS="${GRACE_DAYS:-14}"
DRY_RUN="${DRY_RUN:-false}"
BOT_AUTHOR="${BOT_AUTHOR:-github-actions[bot]}"

if [ -z "$REPO" ]; then
  echo "FEHLER: GITHUB_REPOSITORY ist nicht gesetzt."
  exit 1
fi

# Ohne Admin-PAT kann GitHub keine Issues löschen (GITHUB_TOKEN reicht nicht!).
if [ -z "${GH_TOKEN:-}" ]; then
  cat <<'EOF'
❌ GH_TOKEN (Secret GH_PAT) ist NICHT gesetzt – Löschen nicht möglich!

Damit erledigte Fehlermeldungen DAUERHAFT verschwinden, brauchst du ein
Personal Access Token (PAT) eines Repo-Admins:

  1. GitHub → Settings → Developer settings → Personal access tokens
     → Tokens (classic) → "Generate new token (classic)"
     → Scope: "repo"
  2. Im Blog-Repo: Settings → Secrets and variables → Actions
     → New repository secret → Name: GH_PAT → Wert: <dein Token>
  3. Sicherstellen, dass der Token-Account ADMIN (Owner) des Repos ist.

Mehr dazu: ANLEITUNG-ISSUE-MANAGEMENT.md
EOF
  exit 1
fi

CUTOFF="$(date -u -d "${GRACE_DAYS} days ago" +%s 2>/dev/null || echo 0)"

# Klare Status-Zeile, damit das Log sofort zeigt, was passiert
if [ "$DRY_RUN" = "true" ]; then
  echo "MODE: DRY-RUN (zeigt nur an – löscht nichts) · Schonfrist: ${GRACE_DAYS} Tage"
else
  echo "MODE: ECHT-LÖSCHEN · Schonfrist: ${GRACE_DAYS} Tage"
fi

# Alle geschlossenen Bot-Issues mit Schließzeitpunkt einsammeln (TSV)
mapfile -t ISSUES < <(gh issue list --repo "$REPO" --state closed \
  --author "$BOT_AUTHOR" --limit 1000 \
  --json number,title,closedAt \
  --jq '.[] | select(.closedAt != null) | [.number, .closedAt, .title] | @tsv' 2>/dev/null || true)

if [ "${#ISSUES[@]}" -eq 0 ]; then
  echo "Keine geschlossenen Bot-Issues (Autor: ${BOT_AUTHOR}) gefunden – nichts zu tun."
  echo "→ Falls es welche gibt, die hier fehlen: Autor-Filter BOT_AUTHOR prüfen."
  exit 0
fi

echo "Geschlossene Bot-Issues gefunden: ${#ISSUES[@]}"

DELETED=0
KEPT=0
SKIPPED=0
CANDIDATES=0

for line in "${ISSUES[@]}"; do
  [ -z "$line" ] && continue
  num="$(printf '%s' "$line" | cut -f1)"
  closed="$(printf '%s' "$line" | cut -f2)"
  title="$(printf '%s' "$line" | cut -f3-)"

  closed_ts="$(date -u -d "$closed" +%s 2>/dev/null || echo 0)"

  # Noch innerhalb der Schonfrist? → behalten
  if [ "$closed_ts" -ge "$CUTOFF" ]; then
    KEPT=$((KEPT + 1))
    continue
  fi

  CANDIDATES=$((CANDIDATES + 1))

  if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY-RUN] würde löschen: #${num} (geschlossen ${closed}) – ${title}"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  if gh issue delete "$num" --repo "$REPO" --yes; then
    echo "→ #${num} dauerhaft gelöscht: ${title}"
    DELETED=$((DELETED + 1))
  else
    echo "→ #${num} konnte NICHT gelöscht werden (Admin-Rechte am Token prüfen): ${title}"
    SKIPPED=$((SKIPPED + 1))
  fi
done

echo ""
echo "Fertig: ${DELETED} gelöscht · ${KEPT} innerhalb der Schonfrist behalten · ${SKIPPED} übersprungen."

# Selbst-Diagnose: Wenn im ECHT-Modus Kandidaten vorhanden waren, aber KEINE
# gelöscht wurde, stimmt etwas nicht (Token fehlt / keine Admin-Rechte).
if [ "$DRY_RUN" != "true" ] && [ "$CANDIDATES" -gt 0 ] && [ "$DELETED" -eq 0 ]; then
  echo ""
  echo "⚠️  WARNUNG: Es waren ${CANDIDATES} Meldungen zum Löschen vorgesehen,"
  echo "    aber KEINE wurde gelöscht. Mögliche Ursachen:"
  echo "      1. Secret GH_PAT fehlt oder ist falsch benannt (muss exakt \"GH_PAT\" heißen)"
  echo "      2. Der Token-Account ist kein ADMIN des Repos (Löschen braucht Admin-Rechte)"
  exit 1
fi
