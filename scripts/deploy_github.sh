#!/usr/bin/env bash
# ============================================================
#  Deploy-Skript: Blog auf GitHub hochladen + Pages aktivieren
#
#  Nutzung:
#    1) Auf GitHub ein LEERES Repo anlegen (z. B. franksfinanzcheck-blog)
#    2) Dieses Skript ausführen und GitHub-Benutzernamen eingeben
#    3) Einmalig in GitHub: Settings → Pages → Source: "GitHub Actions"
#    4) Fertig – bei jedem Push baut GitHub Pages automatisch neu
# ============================================================
set -e

cd "$(dirname "$0")/.."

# --- 1. GitHub-Benutzername abfragen ---
if [ -z "$1" ]; then
  read -rp "Dein GitHub-Benutzername: " GITHUB_USER
else
  GITHUB_USER="$1"
fi
REPO_NAME=$(basename "$(pwd)")
echo ""
echo "=== Repo: $GITHUB_USER/$REPO_NAME ==="

# --- 2. baseURL anpassen (einmalig, überschreibt Platzhalter) ---
PAGES_URL="https://$GITHUB_USER.github.io/$REPO_NAME/"
if grep -q "DEINE-DOMAIN.DE" hugo.toml; then
  sed -i "s|https://DEINE-DOMAIN.DE/|$PAGES_URL|" hugo.toml
  echo "✓ baseURL gesetzt: $PAGES_URL"
  git add hugo.toml
  git commit -m "config: baseURL auf GitHub Pages gesetzt" || true
else
  echo "✓ baseURL bereits gesetzt"
fi

# --- 3. Remote setzen, falls nötig ---
if ! git remote | grep -q origin; then
  git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
  echo "✓ Remote 'origin' hinzugefügt"
else
  echo "✓ Remote 'origin' existiert bereits"
fi

# --- 4. Pushen ---
git branch -M main
git push -u origin main || { echo "❌ Push fehlgeschlagen. Prüfe: Repo existiert? Zugriff? (ggf. git remote set-url origin …)"; exit 1; }

echo ""
echo "============================================================"
echo "✅ Push erfolgreich! Noch EIN manueller Schritt:"
echo ""
echo "   GitHub → Repo → Settings → Pages → Source: 'GitHub Actions'"
echo ""
echo "   Danach ist dein Blog live unter:"
echo "   $PAGES_URL"
echo "============================================================"
