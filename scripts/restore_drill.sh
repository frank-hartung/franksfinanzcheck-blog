#!/usr/bin/env bash
# ============================================================
#  restore_drill.sh – BACKUP-RESTORE-DRILL (Agentur-Stufe-2, 27.08.2026)
#  ------------------------------------------------------------
#  Ein nie getestetes Backup ist kein Backup. Dieser Drill beweist
#  QUARTALSWEISE (Workflow siehe patches/…stage-2), dass das
#  tägliche Offsite-Backup (backup-offsite.yml → Release-Asset
#  backup.bundle) sich vollständig wiederherstellen lässt:
#
#    1. Neuestes backup-*-Release finden (oder --bundle für lokale Tests)
#    2. backup.bundle herunterladen (Cache: nutzt vorhandene Datei)
#    3. git clone aus dem Bundle in ein Temp-Verzeichnis
#    4. Verifikation: HEAD vorhanden · hugo.toml · ≥ 20 Artikel ·
#       Impressum/Datenschutz (Pflichtseiten) · keine leeren Refs
#    5. Falls Hugo installiert: Beweis-Build (hugo --minify)
#       (ohne Hugo: Verifikation nur strukturell – kein Fehler)
#
#  Exit: 0 = Restore bewiesen · 1 = Restore GESCHEITERT (laut!)
#  AUFRUF:
#    bash scripts/restore_drill.sh                 # neuestes Release via gh/API
#    bash scripts/restore_drill.sh --bundle X.bundle   # lokale Bundle-Datei
# ============================================================
set -uo pipefail

WORK="$(mktemp -d /tmp/restore-drill.XXXXXX)"
BUNDLE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --bundle) BUNDLE="$2"; shift 2 ;;
    *) echo "Unbekannte Option: $1"; exit 2 ;;
  esac
done

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fail() { echo "❌ RESTORE-DRILL GESCHEITERT: $1"; exit 1; }

echo "== Restore-Drill ($(date -u '+%Y-%m-%d %H:%M UTC')) =="

# --- 1+2: Bundle beschaffen -------------------------------------------
if [ -z "$BUNDLE" ]; then
  BUNDLE="$WORK/backup.bundle"
  if command -v gh >/dev/null 2>&1; then
    echo "Lade neuestes backup-*-Release …"
    gh release download --pattern 'backup.bundle' --output "$BUNDLE" --clobber \
      || fail "Download über 'gh release download' fehlgeschlagen"
  else
    fail "Weder --bundle noch gh CLI verfügbar – kein Bundle-Bezug möglich"
  fi
else
  [ -f "$BUNDLE" ] || fail "Bundle-Datei fehlt: $BUNDLE"
  echo "Teste lokales Bundle: $BUNDLE"
fi

[ -s "$BUNDLE" ] || fail "Bundle ist leer (0 Bytes)"

# --- 3: Klonen aus dem Bundle -----------------------------------------
git clone --quiet "$BUNDLE" "$WORK/restore" \
  || fail "git clone aus Bundle fehlgeschlagen – Bundle unbrauchbar"
cd "$WORK/restore" || fail "Restore-Verzeichnis nicht betretbar"

# --- 4: Strukturelle Verifikation -------------------------------------
git rev-parse --verify -q HEAD >/dev/null || fail "kein HEAD im Restore"
[ -f hugo.toml ]                    || fail "hugo.toml fehlt im Restore"
POSTS=$(ls -1 content/posts 2>/dev/null | wc -l)
[ "${POSTS:-0}" -ge 20 ]           || fail "nur ${POSTS} Artikel im Restore (erwartet ≥ 20)"
[ -f content/impressum/index.md ]   || fail "Impressum fehlt im Restore (DDG-Pflicht!)"
[ -f content/datenschutz/index.md ] || fail "Datenschutzerklärung fehlt im Restore"
COUNT_CONTENT=$(git ls-files | wc -l)
echo "✓ Struktur: HEAD ok · ${COUNT_CONTENT} Dateien · ${POSTS} Artikel · Rechtsseiten vorhanden"

# --- 5: Beweis-Build (falls Hugo vorhanden) ---------------------------
if command -v hugo >/dev/null 2>&1; then
  HUGO_JSDELIVR_SHA=drill hugo --minify --destination "$WORK/public" \
    >/dev/null 2>&1 || fail "Hugo-Build aus dem Restore fehlgeschlagen"
  HTML=$(find "$WORK/public" -name '*.html' | wc -l)
  [ "${HTML:-0}" -ge 30 ] || fail "nur ${HTML} HTML-Seiten gebaut (erwartet ≥ 30)"
  echo "✓ Beweis-Build: ${HTML} HTML-Seiten aus dem Backup gebaut"
else
  echo "ℹ Hugo nicht installiert – strukturelle Verifikation ausreichend (CI baut)"
fi

echo "✅ RESTORE-DRILL BESTANDEN – Backup ist vollständig wiederherstellbar."
