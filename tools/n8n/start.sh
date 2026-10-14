#!/usr/bin/env bash
set -e

# ============================================================
#  Start-Skript für n8n & lokales Whisper (0 € laufende Kosten)
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
  echo "📄 Erstelle .env aus .env.example..."
  cp .env.example .env
fi

echo "🚀 Starte n8n & Whisper-Container..."
docker compose up -d

echo ""
echo "✅ Dienste erfolgreich gestartet!"
echo "   n8n Webhook- & Workflow-UI: http://127.0.0.1:5678  (nur lokal erreichbar)"
echo "   Whisper API Health-Check:   http://127.0.0.1:8765/health"
echo ""
echo "Die Workflows in tools/n8n/workflows/ sind seit dem Sicherheitsaudit"
echo "(14.10.2026, H-06) deaktiviert und ohne Execute-Command. Abschalten:"
echo "   bash tools/n8n/abschalten.sh"
