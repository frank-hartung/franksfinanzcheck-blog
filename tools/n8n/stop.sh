#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stoppe n8n & Whisper-Container..."
docker compose down

echo "✅ Alle Container sauber beendet."
