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
echo "   n8n Webhook- & Workflow-UI: http://localhost:5678"
echo "   Whisper API Health-Check:   http://localhost:8765/health"
echo ""
echo "Importiere die Workflows aus tools/n8n/workflows/ in deine n8n-Instanz."
