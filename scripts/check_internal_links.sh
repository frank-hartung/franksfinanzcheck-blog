#!/usr/bin/env bash
# Prüft, dass alle INTERNEN Links (href/src mit absolutem Pfad) auf existierende
# Dateien zeigen. Externe Links (http/https, Affiliate-Links, mailto, tel, #Anker …)
# werden bewusst übersprungen, um Falschmeldungen zu vermeiden.
#
# Erwartete Umgebungsvariablen:
#   OUTPUT_DIR   Verzeichnis mit dem gebauten Blog (Standard: public)
#   SITE_PREFIX  optionaler Unterpfad, z. B. "/repo" bei GitHub-Pages-Projektseiten
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-public}"
SITE_PREFIX="${SITE_PREFIX:-}"

if [ ! -d "$OUTPUT_DIR" ]; then
  echo "FEHLER: Ausgabe-Verzeichnis '$OUTPUT_DIR' existiert nicht (Build fehlgeschlagen?)."
  exit 1
fi

found=0
broken=0

while IFS= read -r file; do
  # href/src extrahieren – egal ob "doppelt", 'einfach' oder ohne Anführungszeichen
  # (Hugo entfernt beim Minifizieren oft die Anführungszeichen – deshalb robust matchen)
  links="$(grep -oE "(href|src)=(\"[^\"]*\"|'[^']*'|[^[:space:]'\">]*)" "$file" 2>/dev/null \
    | sed -E "s/^(href|src)=//; s/^[\"']//; s/[\"']$//" || true)"

  for link in $links; do
    case "$link" in
      http://*|https://*|mailto:*|tel:*|javascript:*|data:*|//*|\#*) continue ;;
    esac

    # Anker (#…) und Query (?…) abtrennen
    path="${link%%#*}"
    path="${path%%\?*}"
    [ -z "$path" ] && continue

    # Optionalen Unterpfad abziehen
    if [ -n "$SITE_PREFIX" ] && [[ "$path" == "$SITE_PREFIX"* ]]; then
      path="${path#"$SITE_PREFIX"}"
    fi

    # Nur absolute Pfade prüfen; relative Links benötigen Datei-Kontext → überspringen
    [[ "$path" == /* ]] || continue
    [ -z "$path" ] && continue

    target="${OUTPUT_DIR}${path}"
    found=$((found + 1))

    if [ -d "$target" ]; then
      if [ ! -f "$target/index.html" ] && [ ! -f "$target/index.htm" ]; then
        broken=$((broken + 1)); echo "  KAPUTT: $link  →  $file"
      fi
    elif [ -f "$target" ]; then
      :
    elif [ -f "${target}.html" ]; then
      :
    else
      broken=$((broken + 1)); echo "  KAPUTT: $link  →  $file"
    fi
  done
done < <(find "$OUTPUT_DIR" -type f \( -name '*.html' -o -name '*.htm' \) 2>/dev/null | sort)

echo ""
echo "Geprüfte interne Links: $found – defekte: $broken"
if [ "$broken" -ne 0 ]; then
  echo "→ Es wurden $broken defekte interne Links gefunden."
  exit 1
fi
echo "→ Alle internen Links sind in Ordnung."
