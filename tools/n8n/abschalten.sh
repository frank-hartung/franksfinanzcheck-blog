#!/usr/bin/env bash
# ============================================================
#  n8n SICHER ABSCHALTEN – Sicherheitsaudit 14.10.2026 (H-06, N-11)
#
#  Läuft AUF DEM n8n-RECHNER (dort, wo `docker compose` den Stack
#  ff-n8n-automation / ff-whisper-api betreibt). Ein Befehl:
#
#      bash tools/n8n/abschalten.sh            # Workflows aus + gehärtet neu starten
#      bash tools/n8n/abschalten.sh --stoppen  # zusätzlich n8n + Whisper ganz stoppen
#      bash tools/n8n/abschalten.sh --pruefen  # nur Zustand anzeigen, nichts ändern
#
#  Was das Skript tut (idempotent, bricht bei Fehlern laut ab):
#    1. Sicherung aller Workflows (verschlüsselt im n8n-Volume, nicht im Repo)
#    2. ALLE Workflows deaktivieren (n8n-CLI im Container)
#    3. Prüfen, dass kein Workflow mehr aktiv ist
#    4. Container mit der gehärteten docker-compose.yml neu erstellen:
#       Ports nur 127.0.0.1, Image 2.44.3, Execute-Command gesperrt,
#       Repo nur lesend
#    5. Prüfen, dass 5678/8765 nicht mehr von außen lauschen
#    6. Nächste Schritte ausgeben (Token-Rotation)
# ============================================================
set -euo pipefail

MODUS="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="${N8N_CONTAINER:-ff-n8n-automation}"
STEMPEL="$(date -u +%Y%m%d-%H%M%S)"

rot()  { printf '\033[31m%s\033[0m\n' "$*"; }
gruen(){ printf '\033[32m%s\033[0m\n' "$*"; }
gelb() { printf '\033[33m%s\033[0m\n' "$*"; }

command -v docker >/dev/null 2>&1 || { rot "docker fehlt – bitte auf dem n8n-Rechner ausführen."; exit 2; }
if docker compose version >/dev/null 2>&1; then DC=(docker compose); elif command -v docker-compose >/dev/null 2>&1; then DC=(docker-compose); else rot "docker compose fehlt."; exit 2; fi

laeuft() { docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; }
n8n_cli() { docker exec -u node "$CONTAINER" n8n "$@"; }

aktive_workflows() {
  # n8n 1.x/2.x: list:workflow --active=true gibt "id|name" je Zeile aus.
  n8n_cli list:workflow --active=true 2>/dev/null | grep -E '^[A-Za-z0-9]+\|' || true
}

ports_zeigen() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk 'NR==1 || /:5678 |:8765 /'
  else
    docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E "ff-n8n|ff-whisper" || true
  fi
}

oeffentlich_lauschend() {
  # true, wenn 5678/8765 auf 0.0.0.0/:: lauschen
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq '^(0\.0\.0\.0|\[::\]|\*):(5678|8765)$'
  else
    docker ps --format '{{.Ports}}' | grep -Eq '0\.0\.0\.0:(5678|8765)|:::(5678|8765)'
  fi
}

echo "== n8n-Abschaltung (Audit H-06) – $(date) =="

if [ "$MODUS" = "--pruefen" ]; then
  if laeuft; then
    echo "Container $CONTAINER läuft."
    echo "Aktive Workflows:"; aktive_workflows | sed 's/^/  /'
  else
    echo "Container $CONTAINER läuft nicht."
  fi
  echo "Lauschende Ports:"; ports_zeigen
  if oeffentlich_lauschend; then rot "⚠ 5678/8765 lauschen öffentlich!"; exit 1; fi
  gruen "Keine öffentlich lauschenden n8n/Whisper-Ports."
  exit 0
fi

# 1 + 2 + 3: nur möglich, solange der Container läuft
if laeuft; then
  echo "1) Sicherung der Workflows (bleibt im n8n-Volume, nicht im Repo) …"
  n8n_cli export:workflow --all --output="/home/node/.n8n/sicherung-workflows-${STEMPEL}.json" >/dev/null \
    && gruen "   ✔ /home/node/.n8n/sicherung-workflows-${STEMPEL}.json" \
    || gelb "   ⚠ Sicherung fehlgeschlagen – fahre trotzdem mit der Deaktivierung fort."

  echo "2) Alle Workflows deaktivieren …"
  if ! n8n_cli update:workflow --all --active=false 2>/dev/null; then
    # n8n 2.x: Veröffentlichung zurücknehmen
    n8n_cli unpublish:workflow --all 2>/dev/null || true
  fi

  echo "3) Kontrolle …"
  REST="$(aktive_workflows)"
  if [ -n "$REST" ]; then
    rot "   ✖ Noch aktiv:"; echo "$REST" | sed 's/^/     /'
    rot "   Bitte in der n8n-Oberfläche (http://127.0.0.1:5678) von Hand deaktivieren und erneut starten."
    exit 1
  fi
  gruen "   ✔ Kein Workflow mehr aktiv."
else
  gelb "Container $CONTAINER läuft nicht – Schritte 1–3 entfallen (nichts aktiv)."
fi

echo "4) Gehärtete Konfiguration anwenden (docker-compose.yml aus dem Repo) …"
cd "$SCRIPT_DIR"
grep -q '127.0.0.1:5678:5678' docker-compose.yml || { rot "docker-compose.yml ist nicht die gehärtete Fassung – erst 'git pull' im Repo."; exit 2; }
"${DC[@]}" pull n8n >/dev/null 2>&1 || gelb "   ⚠ pull fehlgeschlagen (offline?) – nutze vorhandenes Image."
if [ "$MODUS" = "--stoppen" ]; then
  "${DC[@]}" down
  gruen "   ✔ n8n und Whisper gestoppt (Daten-Volumes bleiben erhalten)."
else
  "${DC[@]}" up -d --force-recreate
  gruen "   ✔ Neu erstellt: Ports nur 127.0.0.1, Image 2.44.3, Execute-Command gesperrt, Repo nur lesend."
  sleep 5
  if laeuft; then
    REST="$(aktive_workflows)"
    if [ -n "$REST" ]; then rot "   ✖ Nach Neustart wieder aktiv: $REST"; exit 1; fi
  fi
fi

echo "5) Netzwerk-Kontrolle …"
ports_zeigen
if oeffentlich_lauschend; then
  rot "   ✖ 5678/8765 lauschen weiterhin öffentlich – Firewall/Portfreigabe im Router prüfen!"
  exit 1
fi
gruen "   ✔ Keine öffentlich lauschenden n8n/Whisper-Ports."

cat <<'HINWEIS'

6) Jetzt noch (5 Minuten, siehe Umsetzungs-Runbook):
   • GitHub-Token des n8n-Rechners widerrufen (github.com → Settings →
     Developer settings → Tokens). Er konnte repository_dispatch auslösen.
   • Eine eventuelle Portfreigabe 5678/8765 im Router löschen.
   • Falls n8n wieder gebraucht wird: nur hinter Cloudflare Access/Tunnel,
     Workflows ohne Execute-Command, Token nur mit actions:write auf EIN Repo.
HINWEIS
gruen "Fertig."
