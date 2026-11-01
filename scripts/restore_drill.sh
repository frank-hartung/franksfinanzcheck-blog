#!/usr/bin/env bash
# ============================================================
#  restore_drill.sh – WIEDERHERSTELLUNGS-PROBE für das Offsite-Backup
#  ------------------------------------------------------------
#  Ein nie zurückgespieltes Backup ist kein Backup. Diese Probe holt die
#  NEUESTEN Sicherungen aus dem privaten Backup-Repo (Entwurfs-Releases aus
#  backup-offsite.yml), entschlüsselt sie und beweist die Wiederherstellung:
#
#    Repo  backup-*     backup.bundle(.enc) → entschlüsseln (PBKDF2 200k) →
#                       git clone → HEAD · hugo.toml · ≥ 20 Artikel ·
#                       Impressum/Datenschutz · optional Hugo-Beweis-Build
#    KV    kv-backup-*  kv-export.json.enc → entschlüsseln (PBKDF2 600k) →
#                       scripts/kv_backup.py --pruefen (Struktur, Zähler,
#                       keine verwaisten Tokens) – im Log nur Zähler
#    Alter              neueste Sicherung älter als 48 h → Warnung
#
#  Stand 15.10.2026 (Vorgang WF-9E5A / #761): Die Fassung vom 27.08.2026
#  lud `backup.bundle` aus den Releases des ÖFFENTLICHEN Blog-Repos. Dort
#  liegen seit dem 20.09.2026 keine Sicherungen mehr (Marken-Oberfläche),
#  verschlüsselte Dateien konnte sie nicht öffnen, und die Abonnenten-Daten
#  (KV) fehlten ganz. Diese Fassung folgt dem echten Weg.
#
#  Klartexte entstehen nur in einem Temp-Verzeichnis (Rechte 0700) und
#  werden am Ende gelöscht – auch bei Abbruch. Die Passphrase kommt aus
#  BACKUP_PASSPHRASE oder wird verdeckt abgefragt (nicht in der History).
#
#  KEIN SCHEIN-GRÜN (01.11.2026, Vorgang WF-9E5A / #923):
#    Bis hierher endete der Aufruf mit `--nur-git --nur-kv` (oder einem
#    Setzen beider Schalter) mit Exit 0 und dem Satz „RESTORE-DRILL
#    BESTANDEN“ – ohne eine einzige Datei geprüft zu haben. Genau diese
#    Zeile wäre im Betrieb als Wiederherstellungs-Nachweis zitiert worden.
#    Jetzt gilt: Beide Familien sind voreingestellt; wird eine ausdrücklich
#    abgewählt (`--nur-git`/`--nur-kv`), steht das im Abschluss, und ohne
#    geprüfte Familie endet der Lauf mit Exit 2 (Aufruf verstanden, aber
#    nichts bewiesen) statt mit einem falschen Bestanden.
#
#  Exit: 0 = Wiederherstellung bewiesen · 1 = GESCHEITERT (laut) · 2 = Aufruf
#  AUFRUF (aus dem Repo-Wurzelverzeichnis, mit `gh auth login` angemeldet):
#    bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup
#    bash scripts/restore_drill.sh --repo … --nur-kv          # nur Abonnenten
#    bash scripts/restore_drill.sh --repo … --nur-git         # nur Repo
#    bash scripts/restore_drill.sh --bundle X.bundle[.enc]    # lokale Datei
#    bash scripts/restore_drill.sh --kv kv-export.json[.enc]  # lokale Datei
#  Anleitung: docs/ANLEITUNG-OFFSITE-BACKUP.md (Abschnitt „Wiederherstellung“)
# ============================================================
set -uo pipefail

HIER="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/restore-drill.XXXXXX")"
chmod 700 "$WORK"
REPO="${BACKUP_REPO:-}"
BUNDLE=""
KVDATEI=""
GIT=1
KV=1
GEPRUEFT=""
MAX_ALTER_H=48

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

# Meldungen auf stderr: Sie bleiben sichtbar, auch wenn eine Funktion in
# einer Befehlsersetzung $(…) scheitert.
fail() { echo "❌ RESTORE-DRILL GESCHEITERT: $1" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)    REPO="${2:-}"; shift 2 ;;
    --bundle)  BUNDLE="${2:-}"; shift 2 ;;
    --kv)      KVDATEI="${2:-}"; shift 2 ;;
    --nur-git) KV=0; shift ;;
    --nur-kv)  GIT=0; shift ;;
    -h|--help) sed -n '2,35p' "$0"; exit 0 ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done

if [ -n "$BUNDLE" ] || [ -n "$KVDATEI" ]; then
  # Lokaler Modus: genau die angegebenen Dateien prüfen.
  [ -n "$BUNDLE" ] || GIT=0
  [ -n "$KVDATEI" ] || KV=0
  QUELLE="lokale Dateien"
else
  if [ -z "$REPO" ]; then
    echo "Kein Ziel: --repo BESITZER/NAME angeben oder BACKUP_REPO setzen (oder --bundle/--kv für lokale Dateien)." >&2
    exit 2
  fi
  command -v gh >/dev/null 2>&1 || fail "gh CLI fehlt (https://cli.github.com) – oder lokale Dateien mit --bundle/--kv prüfen"
  QUELLE="$REPO (privat, Entwürfe)"
fi

echo "== Restore-Drill ($(date -u '+%Y-%m-%d %H:%M UTC')) · Quelle: $QUELLE =="

# Läuft immer im Hauptprozess (nie in $(…)): So bleibt die einmal
# eingegebene Passphrase für den zweiten Schritt erhalten.
passphrase_besorgen() {
  if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
    [ -t 0 ] || fail "BACKUP_PASSPHRASE fehlt und es gibt kein Terminal für die Abfrage"
    read -rs -p "Backup-Passphrase (wird nicht angezeigt): " BACKUP_PASSPHRASE
    echo >&2
    [ -n "$BACKUP_PASSPHRASE" ] || fail "keine Passphrase eingegeben"
    export BACKUP_PASSPHRASE
  fi
}

# $1 = Datei.enc, $2 = PBKDF2-Iterationen → druckt den Pfad der Klartext-Datei (in $WORK)
entschluesseln() {
  local aus
  aus="$WORK/$(basename "${1%.enc}")"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter "$2" -in "$1" -out "$aus" -pass env:BACKUP_PASSPHRASE 2>/dev/null \
    || fail "$(basename "$1") nicht entschlüsselbar – falsche Passphrase oder beschädigte Datei"
  echo "$aus"
}

# $1 = Tag-Präfix, $2… = Asset-Namen in Wunschreihenfolge → druckt den lokalen Pfad.
# Entwürfe zählen mit: gelesen über die API, nicht über `gh release list`.
holen() {
  local praefix="$1" zeile tag erstellt alter name
  shift
  zeile="$(gh api "repos/$REPO/releases?per_page=100" \
    --jq "[.[] | select(.tag_name | startswith(\"$praefix\"))] | sort_by(.created_at) | last | select(. != null) | .tag_name + \" \" + .created_at")" \
    || fail "Releases von $REPO nicht lesbar – mit 'gh auth login' angemeldet und Zugriff auf das private Repo?"
  [ -n "$zeile" ] || fail "kein ${praefix}*-Release in $REPO – lief das Backup schon einmal grün?"
  tag="${zeile%% *}"
  erstellt="${zeile#* }"
  alter="$(python3 -c 'import sys, datetime as d; t = d.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")); print(int((d.datetime.now(d.timezone.utc) - t).total_seconds() // 3600))' "$erstellt" 2>/dev/null || echo "?")"
  echo "· neueste Sicherung: $tag (vor ${alter} h)" >&2
  if [ "$alter" != "?" ] && [ "$alter" -gt "$MAX_ALTER_H" ]; then
    echo "⚠️  $tag ist älter als ${MAX_ALTER_H} h – läuft der nächtliche Workflow „Offsite-Backup“ noch grün?" >&2
  fi
  for name in "$@"; do
    if gh release download "$tag" --repo "$REPO" --pattern "$name" --dir "$WORK" --clobber >/dev/null 2>&1; then
      echo "$WORK/$name"
      return 0
    fi
  done
  fail "$tag enthält keine der Dateien: $*"
}

# --- Abonnenten-Sicherung (KV) ----------------------------------------
if [ "$KV" = 1 ]; then
  echo "== Abonnenten und Einwilligungsnachweise (KV) =="
  if [ -z "$KVDATEI" ]; then
    KVDATEI="$(holen kv-backup- kv-export.json.enc)" || exit 1
  fi
  [ -f "$KVDATEI" ] || fail "KV-Datei fehlt: $KVDATEI"
  case "$KVDATEI" in
    *.enc) passphrase_besorgen; KVDATEI="$(entschluesseln "$KVDATEI" 600000)" || exit 1 ;;
  esac
  python3 "$HIER/kv_backup.py" --pruefen "$KVDATEI" \
    || fail "KV-Sicherung ist strukturell nicht wiederherstellbar (Meldungen oben)"
  GEPRUEFT="${GEPRUEFT:+$GEPRUEFT, }Abonnenten (KV)"
  echo "✓ KV: entschlüsselt und vollständig – Rückspielen: Anleitung, Abschnitt „Ernstfall“ (wrangler kv bulk put … --remote)"
fi

# --- Repo-Sicherung (Git-Bundle) ---------------------------------------
if [ "$GIT" = 1 ]; then
  echo "== Repository (Git-Bundle) =="
  if [ -z "$BUNDLE" ]; then
    BUNDLE="$(holen backup- backup.bundle.enc backup.bundle)" || exit 1
  fi
  [ -f "$BUNDLE" ] || fail "Bundle-Datei fehlt: $BUNDLE"
  case "$BUNDLE" in
    *.enc) passphrase_besorgen; BUNDLE="$(entschluesseln "$BUNDLE" 200000)" || exit 1 ;;
  esac
  [ -s "$BUNDLE" ] || fail "Bundle ist leer (0 Bytes)"

  R="$WORK/restore"
  # Enthaltenen Branch ausdrücklich wählen (01.11.2026, #923): Ein Bundle, in
  # dem HEAD auf keinen der mitgelieferten Refs zeigt, lässt `git clone` mit
  # einer bloßen WARNUNG einen LEEREN Arbeitsbaum anlegen – der Drill hätte
  # danach „kein HEAD im Restore“ gemeldet, obwohl das Bundle in Ordnung ist.
  # `main` hat Vorrang, sonst der erste enthaltene Branch.
  KOPF_BRANCH="$(git bundle list-heads "$BUNDLE" 2>/dev/null \
    | awk '{print $2}' | sed -n 's#^refs/heads/##p' | grep -x 'main' || true)"
  if [ -z "$KOPF_BRANCH" ]; then
    KOPF_BRANCH="$(git bundle list-heads "$BUNDLE" 2>/dev/null \
      | awk '{print $2}' | sed -n 's#^refs/heads/##p' | head -n 1)"
  fi
  [ -n "$KOPF_BRANCH" ] || fail "Bundle enthält keinen Branch (nur Tags/HEAD) – nicht wiederherstellbar"
  git clone --quiet --branch "$KOPF_BRANCH" "$BUNDLE" "$R" 2>/dev/null \
    || fail "git clone aus dem Bundle fehlgeschlagen – Bundle unbrauchbar"
  git -C "$R" rev-parse --verify -q HEAD >/dev/null || fail "kein HEAD im Restore"
  [ -f "$R/hugo.toml" ]                    || fail "hugo.toml fehlt im Restore"
  POSTS=$(ls -1 "$R/content/posts" 2>/dev/null | wc -l | tr -d ' ')
  [ "${POSTS:-0}" -ge 20 ]                 || fail "nur ${POSTS} Artikel im Restore (erwartet ≥ 20)"
  [ -f "$R/content/impressum/index.md" ]   || fail "Impressum fehlt im Restore (DDG-Pflicht!)"
  [ -f "$R/content/datenschutz/index.md" ] || fail "Datenschutzerklärung fehlt im Restore"
  DATEIEN=$(git -C "$R" ls-files | wc -l | tr -d ' ')
  GEPRUEFT="${GEPRUEFT:+$GEPRUEFT, }Repository (Git-Bundle, ${DATEIEN} Dateien)"
  echo "✓ Struktur: HEAD ok · ${DATEIEN} Dateien · ${POSTS} Artikel · Rechtsseiten vorhanden"

  if command -v hugo >/dev/null 2>&1; then
    HUGO_JSDELIVR_SHA=drill hugo --minify --source "$R" --destination "$WORK/public" \
      >/dev/null 2>&1 || fail "Hugo-Build aus dem Restore fehlgeschlagen"
    HTML=$(find "$WORK/public" -name '*.html' | wc -l | tr -d ' ')
    [ "${HTML:-0}" -ge 30 ] || fail "nur ${HTML} HTML-Seiten gebaut (erwartet ≥ 30)"
    echo "✓ Beweis-Build: ${HTML} HTML-Seiten aus dem Backup gebaut"
  else
    echo "ℹ Hugo nicht installiert – strukturelle Verifikation ausreichend (CI baut)"
  fi
fi

if [ -z "$GEPRUEFT" ]; then
  echo "🛑 RESTORE-DRILL: Es wurde NICHTS geprüft (--nur-git und --nur-kv zugleich)." >&2
  echo "   Ein Lauf ohne Prüfung darf nicht „bestanden“ heißen. Aufruf: --nur-git ODER --nur-kv ODER ohne Schalter (beides)." >&2
  exit 2
fi
echo "✅ RESTORE-DRILL BESTANDEN – geprüft: $GEPRUEFT."
echo "   Vollständig wiederherstellbar: aus dem Backup lässt sich ein Arbeitsstand bauen (HEAD, Rechtsseiten, Abonnenten-Daten)."
