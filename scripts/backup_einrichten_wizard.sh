#!/usr/bin/env bash
# ============================================================
#  backup_einrichten_wizard.sh – Offsite-Backup einrichten (E1–E8)
#  ------------------------------------------------------------
#  Vorgang WF-9E5A / Meldung #761: Der Job „KV-/D1-Backup“ in
#  backup-offsite.yml ist ABSICHTLICH rot (fail-closed), bis Ziel,
#  Passphrase und Lesezugänge eingerichtet sind. Das kann nur der
#  Inhaber: An Secrets, PAT-Formulare und das Cloudflare-Konto kommen
#  Agenten nicht heran – und das soll so bleiben (CLAUDE.md, N-17).
#
#  Dieses Skript führt Schritt für Schritt durch die Einrichtung aus
#  docs/ANLEITUNG-OFFSITE-BACKUP.md und prüft den Stand jederzeit:
#
#    bash scripts/backup_einrichten_wizard.sh --check   # nur prüfen (E1–E8)
#    bash scripts/backup_einrichten_wizard.sh           # interaktiv einrichten
#    bash scripts/backup_einrichten_wizard.sh --ziel besitzer/name   # anderes Ziel-Repo
#
#  VORAUSSETZUNGEN:
#    · `gh auth login` als Inhaber (Schreibrecht auf frank-hartung/
#      franksfinanzcheck-blog, Recht „administration“ für Environments)
#    · Ausführung aus dem Repo-Wurzelverzeichnis (oder beliebig – das
#      Skript findet die Wurzel selbst)
#    · bash, gh, python3, curl, openssl (Standard auf macOS/Linux/WSL)
#
#  SICHERHEIT:
#    · Geheimnisse werden verdeckt abgefragt (keine Terminal-Echo, keine
#      Shell-History, keine Prozessliste – Übergabe an gh per stdin).
#    · Kein Secret-Wert wird ausgegeben, geloggt oder in eine Datei
#      geschrieben. E2 wird mit dem eingegebenen Token live gegen das
#      Ziel-Repo verifiziert (nur der ZUSTAND erscheint im Protokoll);
#      den Cloudflare-Token prüft E5 im ersten Offsite-Lauf live – der
#      Wizard ruft die Verwaltungs-API bewusst nicht selbst auf
#      (T6-Vertrag: scripts/ki_transportweg.py).
#    · Erst E8 (Environment nur für main), dann Secrets – genau die
#      Reihenfolge der Anleitung.
#    · In CI (GITHUB_ACTIONS) verweigert sich das Skript: Einrichtung
#      ist ein Menschen-Schritt am eigenen Rechner.
#
#  GRENZEN (ehrlich):
#    · GitHub zeigt Secret-Namen, aber nie Secret-Werte: --check prüft
#      deshalb ANWESENHEIT, Format und Zugriff – die TIEFPRÜFUNG
#      (Token-Gültigkeit, Namespace lesbar, Ablauf-Fristen) macht
#      scripts/backup_einrichtung.py im Lauf (Job-Zusammenfassung).
#    · Ein feingranularer PAT lässt sich nicht per CLI erzeugen – das
#      Skript öffnet das vorbelegte Formular und nimmt den Token danach
#      verdeckt entgegen.
#
#  Abschluss: Der erste grüne Lauf von „Offsite-Backup“ schließt die
#  offene Meldung #761 automatisch. Danach einmal die Wiederherstellung
#  proben: bash scripts/restore_drill.sh --repo <ziel>
# ============================================================
set -uo pipefail

HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WURZEL="$(dirname "$HIER")"

QUELLE="${QUELLE:-frank-hartung/franksfinanzcheck-blog}"
ZIEL="frank-hartung/franksfinanzcheck-backup"
UMGEBUNG="backup"
ANLEITUNG="docs/ANLEITUNG-OFFSITE-BACKUP.md"

PAT_URL='https://github.com/settings/personal-access-tokens/new?name=ff-offsite-backup&description=Offsite-Backup%3A+Entwurfs-Releases+im+privaten+Backup-Repo+%28nur+dieses+Repo%29&target_name=frank-hartung&expires_in=366&contents=write'
CF_TOKEN_URL='https://dash.cloudflare.com/?to=/:account/api-tokens&permissionGroupKeys=%5B%7B%22key%22%3A%22workers_kv_storage%22%2C%22type%22%3A%22read%22%7D%5D&name=ff-kv-backup+%28nur+lesen%29'
CF_KV_URL='https://dash.cloudflare.com/?to=/:account/workers/kv/namespaces'
NEUES_REPO_URL='https://github.com/new?owner=frank-hartung&name=franksfinanzcheck-backup&visibility=private&description=Private+Sicherungen+%28verschl%C3%BCsselt%29'
EINSTELLUNGEN_UMGEBUNGEN='https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments'

if [ -t 1 ]; then
  FETT=$'\033[1m'; GRUEN=$'\033[32m'; ROT=$'\033[31m'; GELB=$'\033[33m'; ENDE=$'\033[0m'
else
  FETT=""; GRUEN=""; ROT=""; GELB=""; ENDE=""
fi

NUR_CHECK=0
OFFENE=0

# ------------------------------------------------------------ Argumente
hilfe() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  cat <<EOF

Aufruf:
  bash scripts/backup_einrichten_wizard.sh --check          # Stand prüfen
  bash scripts/backup_einrichten_wizard.sh                  # einrichten
  bash scripts/backup_einrichten_wizard.sh --ziel besitzer/name

Anleitung: $ANLEITUNG
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check) NUR_CHECK=1 ;;
    --ziel) shift; ZIEL="${1:-}" ;;
    --ziel=*) ZIEL="${1#--ziel=}" ;;
    --quelle) shift; QUELLE="${1:-}" ;;
    -h|--help) hilfe; exit 0 ;;
    *) echo "Unbekannte Option: $1 (--help zeigt die Nutzung)"; exit 2 ;;
  esac
  shift
done

case "$ZIEL" in
  */*) ;;
  *) echo "${ROT}✗ --ziel erwartet besitzer/name (z. B. frank-hartung/franksfinanzcheck-backup)${ENDE}"; exit 2 ;;
esac

# ------------------------------------------------------------ Werkzeuge
fehlt() {
  echo "${ROT}✗ $*${ENDE}" >&2
  echo "  Dieses Skript braucht: bash, gh (angemeldet), python3, curl, openssl." >&2
  exit 1
}

command -v gh      >/dev/null 2>&1 || fehlt "gh (GitHub CLI) fehlt – https://cli.github.com/"
command -v python3 >/dev/null 2>&1 || fehlt "python3 fehlt"
command -v curl    >/dev/null 2>&1 || fehlt "curl fehlt"
command -v openssl >/dev/null 2>&1 || fehlt "openssl fehlt"

if [ -n "${GITHUB_ACTIONS:-}" ]; then
  echo "${ROT}✗ In CI verweigert: Die Einrichtung ist ein Menschen-Schritt am eigenen Rechner.${ENDE}" >&2
  echo "  Der Workflow prüft E1–E8 selbst: scripts/backup_einrichtung.py --pruefen." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "${ROT}✗ gh ist nicht angemeldet.${ENDE} Erst: gh auth login (Inhaber-Konto, Schreibrecht auf $QUELLE)." >&2
  exit 1
fi

[ -f "$WURZEL/scripts/backup_einrichtung.py" ] || fehlt "scripts/backup_einrichtung.py nicht gefunden (aus dem Repo-Wurzelverzeichnis starten?)"

# ------------------------------------------------------------ Bausteine
abschnitt() { printf '\n%s==> %s%s\n' "$FETT" "$*" "$ENDE"; }
ok()        { printf '  %s✅ %s%s\n' "$GRUEN" "$*" "$ENDE"; }
offen()     { printf '  %s❌ %s%s\n' "$ROT" "$*" "$ENDE"; OFFENE=$((OFFENE + 1)); }
hinweis()   { printf '  %s⚠️  %s%s\n' "$GELB" "$*" "$ENDE"; }
info()      { printf '  ·  %s\n' "$*"; }
link()      { printf '  🔗 %s\n' "$*" >&2; }

# Secret-Name bekannt? (GitHub zeigt Namen + Zeitstempel, nie Werte.)
# $1 = Name, $2 = eb (Environment backup) | repo
secret_bekannt() {
  local name="$1" bereich="$2" pfad json
  if [ "$bereich" = "eb" ]; then
    pfad="repos/$QUELLE/environments/$UMGEBUNG/secrets"
  else
    pfad="repos/$QUELLE/actions/secrets"
  fi
  json="$(gh api "$pfad" 2>/dev/null)" || return 2   # 2 = nicht lesbar (Rechte)
  printf '%s' "$json" | GEGEBENER_NAME="$name" python3 -c '
import json, os, sys
try:
    daten = json.load(sys.stdin)
except Exception:
    sys.exit(2)
namen = [s.get("name", "") for s in daten.get("secrets", [])]
sys.exit(0 if os.environ["GEGEBENER_NAME"] in namen else 1)
'
}

variable_wert() {  # $1 = Variablenname; stdout = Wert (leer, wenn nicht gesetzt)
  gh variable get "$1" --repo "$QUELLE" 2>/dev/null | tr -d '\r\n'
}

frage_ja() {  # $1 = Frage; Exit 0 bei j/J
  local antwort
  printf '  %s [j/N] ' "$1" >&2
  IFS= read -r antwort </dev/tty || return 1
  case "$antwort" in [jJ]*) return 0 ;; *) return 1 ;; esac
}

heimlich() {  # $1 = Prompt; stdout = Eingabe (ohne Zeilenumbruch, kein Echo)
  local prompt="$1" eingabe=""
  printf '  %s\n' "$prompt" >&2
  printf '  Eingabe (unsichtbar): ' >&2
  IFS= read -rs eingabe </dev/tty || true
  printf '\n' >&2
  printf '%s' "$eingabe"
}

oeffnen() {  # URL anzeigen; auf Wunsch im Browser öffnen
  local url="$1"
  link "$url"
  if frage_ja "Link jetzt im Browser öffnen?"; then
    if command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then open "$url" >/dev/null 2>&1 || true
    fi
  fi
}

umgebung_anlegen() {
  printf '{}' | gh api -X PUT "repos/$QUELLE/environments/$UMGEBUNG" --input - >/dev/null 2>&1
}

branch_regel_setzen() {
  printf '{"policy_type":"SELECTED_BRANCHES","allowed_branches":[{"name":"main"}]}' \
    | gh api -X PUT "repos/$QUELLE/environments/$UMGEBUNG/deployment-branch-policies" --input - >/dev/null 2>&1
}

branch_regel_status() {  # stdout: ok | offen | fremd | unlesbar
  local json
  json="$(gh api "repos/$QUELLE/environments/$UMGEBUNG" 2>/dev/null)" || { echo "unlesbar"; return; }
  printf '%s' "$json" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("unlesbar"); sys.exit(0)
regeln = [str((r or {}).get("type")) for r in (d.get("protection_rules") or [])]
politik = d.get("deployment_branch_policy")
if "required_reviewers" in regeln:
    print("reviewer"); sys.exit(0)
if politik is None:
    print("offen"); sys.exit(0)
if politik.get("custom_branch_policies"):
    print("custom"); sys.exit(0)
print("ok")
'
}

branch_regel_namen() {  # bei custom: erlaubte Branch-Namen (Zeilen)
  gh api "repos/$QUELLE/environments/$UMGEBUNG/deployment-branch-policies" 2>/dev/null \
    | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for p in d.get("branch_policies", []):
    print(p.get("name", ""))
'
}

pruefe_e8() {  # Return 0 = grün; zählt sonst OFFENE hoch
  local status
  status="$(branch_regel_status)"
  case "$status" in
    ok)
      ok "E8 Environment „$UMGEBUNG“: nur main darf die Backup-Zugänge nutzen" ;;
    custom)
      local namen; namen="$(branch_regel_namen | tr '\n' ' ')"
      if [ "$(echo "$namen" | tr -d ' ')" = "main" ]; then
        ok "E8 Environment „$UMGEBUNG“: Branch-Regel = main"
      else
        offen "E8 Branch-Regel erlaubt mehr als main: $namen"
        link "$EINSTELLUNGEN_UMGEBUNGEN"
      fi ;;
    reviewer)
      offen "E8 Pflicht-Freigabe (Required reviewers) ist aktiv – jeder Nachtlauf würde auf einen Klick warten und nach 30 Tagen abbrechen"
      link "$EINSTELLUNGEN_UMGEBUNGEN" ;;
    offen)
      offen "E8 Environment „$UMGEBUNG“ steht JEDEM Branch offen – Zugänge wären ungeschützt"
      link "$EINSTELLUNGEN_UMGEBUNGEN" ;;
    *)
      hinweis "E8 nicht prüfbar (Environment-API nicht lesbar: braucht Recht „administration“ für $QUELLE)"
      link "$EINSTELLUNGEN_UMGEBUNGEN"
      return 1 ;;
  esac
}

# ------------------------------------------------------------ Modus: --check
check() {
  OFFENE=0
  abschnitt "Offsite-Backup – Einrichtungsprüfung (lokal, E1–E8)"
  info "Quelle: $QUELLE · Ziel: $ZIEL · Environment: $UMGEBUNG"
  info "Tiefprüfung (Token-Gültigkeit, Namespace, Fristen): Lauf „Offsite-Backup“ → Job-Zusammenfassung"

  # E8 zuerst – die Anleitung verlangt: erst absichern, dann befüllen.
  pruefe_e8

  # E1 Ziel-Repository (Variable + Repo-Existenz + Sichtbarkeit)
  local ziel_wert repo_json sichtbar
  ziel_wert="$(variable_wert BACKUP_REPO)"
  if [ -z "$ziel_wert" ]; then
    offen "E1 Repository-Variable BACKUP_REPO fehlt"
    link "$NEUES_REPO_URL"
  else
    repo_json="$(gh api "repos/$ziel_wert" 2>/dev/null)" || repo_json=""
    if [ -z "$repo_json" ]; then
      offen "E1 BACKUP_REPO=$ziel_wert – Repository nicht auffindbar/kein Zugriff"
    else
      sichtbar="$(printf '%s' "$repo_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("private"))' 2>/dev/null)"
      if [ "$sichtbar" = "True" ]; then
        ok "E1 BACKUP_REPO=$ziel_wert (privat)"
      else
        offen "E1 BACKUP_REPO=$ziel_wert ist ÖFFENTLICH – Sicherungen gehören in ein privates Repo"
      fi
    fi
  fi

  # E2–E5 Secrets (Anwesenheit; Werte zeigt GitHub nie)
  local s
  for s in "BACKUP_PASSPHRASE:E3 Passphrase (Environment „$UMGEBUNG“)" \
           "BACKUP_REPO_TOKEN:E2 GitHub-Schreibzugang (Environment „$UMGEBUNG“)" \
           "CF_KV_BACKUP_TOKEN:E5 Cloudflare-Lesezugang (Environment „$UMGEBUNG“)"; do
    local name="${s%%:*}" label="${s#*:}"
    secret_bekannt "$name" eb
    case $? in
      0) ok "$label – Secret vorhanden" ;;
      1) offen "$label – Secret fehlt" ;;
      *) hinweis "$label – nicht prüfbar (Secret-Liste nicht lesbar: Recht „administration“ nötig)" ;;
    esac
  done

  # E4 Cloudflare-Konto (Environment- ODER Repo-Secret – der Lauf sieht beides)
  secret_bekannt "CLOUDFLARE_ACCOUNT_ID" eb
  case $? in
    0) ok "E4 CLOUDFLARE_ACCOUNT_ID – Environment-Secret vorhanden" ;;
    1) secret_bekannt "CLOUDFLARE_ACCOUNT_ID" repo
       case $? in
         0) ok "E4 CLOUDFLARE_ACCOUNT_ID – Repo-Secret vorhanden" ;;
         1) offen "E4 CLOUDFLARE_ACCOUNT_ID fehlt (weder Environment- noch Repo-Secret)" ;;
         *) hinweis "E4 CLOUDFLARE_ACCOUNT_ID – nicht prüfbar (Secret-Liste nicht lesbar)" ;;
       esac ;;
    *) hinweis "E4 CLOUDFLARE_ACCOUNT_ID – nicht prüfbar (Secret-Liste nicht lesbar)" ;;
  esac

  # E6 KV-Namespace (Variable, 32 Hex-Zeichen)
  local kv
  kv="$(variable_wert KV_NAMESPACE_ID_ABO)"
  if [ -z "$kv" ]; then
    offen "E6 Repository-Variable KV_NAMESPACE_ID_ABO fehlt"
    link "$CF_KV_URL"
  elif printf '%s' "$kv" | grep -Eq '^[0-9a-fA-F]{32}$'; then
    ok "E6 KV_NAMESPACE_ID_ABO gesetzt (Format 32 Hex-Zeichen)"
  else
    offen "E6 KV_NAMESPACE_ID_ABO hat nicht das Format einer Namespace-ID (32 Hex-Zeichen erwartet, Name „ABO“ ist falsch)"
  fi

  # E7 D1 (optional)
  local d1
  d1="$(variable_wert D1_DATABASE_ID)"
  if [ -n "$d1" ]; then
    ok "E7 D1_DATABASE_ID gesetzt (Klick-Zähler wird mitgesichert)"
  else
    info "E7 D1_DATABASE_ID nicht gesetzt – optional (nur nötig, wenn der Klick-Zähler mitgesichert werden soll)"
  fi

  abschnitt "Ergebnis"
  if [ "$OFFENE" -eq 0 ]; then
    echo "  ${GRUEN}${FETT}Alle Pflichtpunkte sind eingerichtet.${ENDE}"
    info "Nächster Schritt: gh workflow run backup-offsite.yml --ref main"
    info "Der erste grüne Lauf schließt Meldung #761 automatisch."
    return 0
  fi
  echo "  ${ROT}${FETT}$OFFENE Pflichtpunkt(e) offen.${ENDE} Einrichtung: bash scripts/backup_einrichten_wizard.sh"
  info "Anleitung: $ANLEITUNG"
  return 1
}

if [ "$NUR_CHECK" = "1" ]; then
  check
  exit $?
fi

# ------------------------------------------------------------ Modus: Einrichtung
cat <<EOF

${FETT}Offsite-Backup einrichten (WF-9E5A / #761)${ENDE}

  Quelle:       $QUELLE
  Ziel-Vorschlag: $ZIEL
  Environment:  $UMGEBUNG
  Anleitung:    $ANLEITUNG

  Reihenfolge wie in der Anleitung: ERST absichern (E8), dann befüllen.
  Geheimnisse werden verdeckt abgefragt und nie angezeigt oder geloggt.
  Jeder Schritt lässt sich überspringen (Eingabe leer lassen bzw. „n“).

EOF
if ! frage_ja "Jetzt einrichten?"; then
  echo "Abgebrochen – es wurde nichts geändert."
  exit 0
fi

# ---- Schritt 1 (E8): Environment absichern ------------------------------
abschnitt "Schritt 1/7 (E8) – Environment „$UMGEBUNG“ nur für main"
info "Ohne diese Regel kommt JEDER Branch an die Backup-Zugänge (Sicherheitsaudit F-07)."
umgebung_anlegen
branch_regel_setzen
pruefe_e8 || {
  hinweis "Automatisch setzen fehlte (Recht „administration“ nötig?). Bitte im Web nachholen:"
  link "$EINSTELLUNGEN_UMGEBUNGEN"
  info "Deployment branches and tags → „Selected branches and tags“ → nur main; KEINE Required reviewers."
  if ! frage_ja "Erledigt?"; then
    echo "${ROT}Abbruch: E8 muss sitzen, bevor Secrets eingetragen werden.${ENDE}"
    exit 1
  fi
}

# ---- Schritt 2 (E1): Privates Backup-Repository -------------------------
abschnitt "Schritt 2/7 (E1) – Privates Backup-Repository"
if gh repo view "$ZIEL" >/dev/null 2>&1; then
  ok "$ZIEL existiert bereits"
else
  info "$ZIEL existiert noch nicht."
  if frage_ja "Jetzt als PRIVATES Repository anlegen?"; then
    if gh repo create "$ZIEL" --private --description "Private Sicherungen (verschlüsselt) – Offsite-Ziel von $QUELLE"; then
      ok "$ZIEL angelegt (privat)"
    else
      hinweis "gh repo create fehlgeschlagen – bitte im Web anlegen (Sichtbarkeit PRIVATE):"
      oeffnen "$NEUES_REPO_URL"
    fi
  else
    oeffnen "$NEUES_REPO_URL"
  fi
fi
if [ "$(variable_wert BACKUP_REPO)" = "$ZIEL" ]; then
  ok "Repository-Variable BACKUP_REPO=$ZIEL ist gesetzt"
else
  if gh variable set BACKUP_REPO --repo "$QUELLE" --body "$ZIEL" 2>/dev/null; then
    ok "Repository-Variable BACKUP_REPO=$ZIEL gesetzt"
  else
    hinweis "Variable konnte nicht gesetzt werden – manuell: Settings → Secrets and variables → Actions → Variables → BACKUP_REPO = $ZIEL"
  fi
fi

# ---- Schritt 3 (E3): Passphrase -----------------------------------------
abschnitt "Schritt 3/7 (E3) – Passphrase (einziger Schlüssel zu allen Sicherungen)"
if secret_bekannt "BACKUP_PASSPHRASE" eb; then
  PASS_VORHANDEN=1
else
  PASS_VORHANDEN=0
fi
if [ "$PASS_VORHANDEN" = "1" ]; then
  ok "Secret BACKUP_PASSPHRASE ist bereits gesetzt"
  if frage_ja "Trotzdem NEU setzen? (Überschreibt die alte – ALLE bisherigen Sicherungen werden damit unlesbar!)"; then
    PASS_VORHANDEN=0
  else
    info "Überspringe – Secret bleibt wie es ist."
  fi
fi
if [ "$PASS_VORHANDEN" != "1" ]; then
  info "1) Im Passwort-Manager einen Eintrag „FranksFinanzcheck – Backup-Passphrase“ anlegen."
  info "2) Zufälliges Passwort mit MINDESTENS 32 Zeichen erzeugen (Vorschlag im Terminal: openssl rand -base64 33)."
  info "3) ERST speichern, dann hier einfügen. Ohne Passphrase ist jede Sicherung wertlos."
  while :; do
    PASSWORT="$(heimlich "Passphrase einfügen (32+ Zeichen – wird NICHT angezeigt):")"
    if [ -z "$PASSWORT" ]; then
      hinweis "Leere Eingabe – Schritt übersprungen. Secret später selbst setzen: BACKUP_PASSPHRASE (Environment „$UMGEBUNG“)."
      break
    fi
    if [ "${#PASSWORT}" -lt 32 ]; then
      hinweis "Zu kurz (${#PASSWORT} Zeichen, mindestens 32) – bitte neu."
      continue
    fi
    if printf '%s' "$PASSWORT" | gh secret set BACKUP_PASSPHRASE --repo "$QUELLE" --env "$UMGEBUNG"; then
      ok "Secret BACKUP_PASSPHRASE gesetzt (Länge ${#PASSWORT} Zeichen – Wert wurde nicht angezeigt)"
    else
      hinweis "gh secret set fehlgeschlagen – Secret manuell im Environment „$UMGEBUNG“ eintragen."
    fi
    PASSWORT=""
    break
  done
fi

# ---- Schritt 4 (E2): GitHub-Schreibzugang -------------------------------
abschnitt "Schritt 4/7 (E2) – Fine-grained PAT für das Backup-Repo"
info "Formular ist vorbelegt: Name, Ablauf 366 Tage, Recht „Contents: Read and write“."
info "WICHTIG – nicht vorbelegbar: Repository access → „Only select repositories“ → NUR $(printf '%s' "$ZIEL" | sed 's#.*/##')."
oeffnen "$PAT_URL"
info "„Generate token“ klicken, Token kopieren (beginnt mit github_pat_…), hier einfügen."
while :; do
  TOKEN="$(heimlich "BACKUP_REPO_TOKEN einfügen (leer lassen = überspringen):")"
  [ -z "$TOKEN" ] && { hinweis "Übersprungen – Secret später selbst setzen: BACKUP_REPO_TOKEN (Environment „$UMGEBUNG“)."; break; }
  # Live-Probe mit dem eingegebenen Token: gültig UND Ziel sichtbar?
  # Der Token selbst erscheint nirgends im Protokoll (nur der Zustand).
  PROBE="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" \
    -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$ZIEL" 2>/dev/null)" || PROBE="000"
  case "$PROBE" in
    200)
      if printf '%s' "$TOKEN" | gh secret set BACKUP_REPO_TOKEN --repo "$QUELLE" --env "$UMGEBUNG"; then
        ok "Secret BACKUP_REPO_TOKEN gesetzt (Probe: Token gültig, $ZIEL lesbar)"
      else
        hinweis "Token gültig, aber gh secret set fehlgeschlagen – manuell eintragen."
      fi
      TOKEN=""; break ;;
    401)
      hinweis "Probe HTTP 401: Token ungültig oder abgelaufen – bitte neu erzeugen."
      TOKEN="" ;;
    404)
      hinweis "Probe HTTP 404: Token sieht $ZIEL NICHT – beim Erzeugen „Only select repositories“ → genau dieses Repo wählen (oder Repo fehlt noch)."
      TOKEN="" ;;
    *)
      hinweis "Probe nicht möglich (HTTP $PROBE) – Token trotzdem setzen? Nur mit Vorsicht."
      if frage_ja "Token ohne erfolgreiche Probe als Secret setzen?"; then
        printf '%s' "$TOKEN" | gh secret set BACKUP_REPO_TOKEN --repo "$QUELLE" --env "$UMGEBUNG" \
          && ok "Secret BACKUP_REPO_TOKEN gesetzt (ohne Probe)" \
          || hinweis "gh secret set fehlgeschlagen – manuell eintragen."
      fi
      TOKEN=""; break ;;
  esac
done

# ---- Schritt 5 (E5): Cloudflare-Lesezugang ------------------------------
abschnitt "Schritt 5/7 (E5) – Cloudflare-API-Token (NUR Workers KV: Read)"
info "Vorbelegt: Konto-Token, Recht „Workers KV Storage: Read“, Name „ff-kv-backup (nur lesen)“."
info "Keine weiteren Rechte, keine Schreibrechte. Soll der Klick-Zähler (D1) mitgesichert"
info "werden, zusätzlich „D1: Read“ (Link in der Anleitung, Schritt 5)."
oeffnen "$CF_TOKEN_URL"
while :; do
  CF_TOKEN="$(heimlich "CF_KV_BACKUP_TOKEN einfügen (leer lassen = überspringen):")"
  [ -z "$CF_TOKEN" ] && { hinweis "Übersprungen – Secret später selbst setzen: CF_KV_BACKUP_TOKEN (Environment „$UMGEBUNG“)."; break; }
  # Bewusst KEINE eigene Verify-Abfrage an die Cloudflare-Verwaltungs-API:
  # Der Transportweg-Wächter T6 (scripts/ki_transportweg.py) hält direkte
  # Anbieter-Endpunkte aus neuen Skripten heraus – Ausnahmen gibt es nur
  # mit Ausgleichstest. Die Tiefprüfung des Tokens (Art, Recht „Workers KV:
  # Read“, Ablauf-Frist) leistet E5 im Offsite-Lauf live, mit Abhilfe-Link;
  # dieser Wizard bietet am Ende an, den Lauf sofort zu starten.
  if printf '%s' "$CF_TOKEN" | gh secret set CF_KV_BACKUP_TOKEN --repo "$QUELLE" --env "$UMGEBUNG"; then
    ok "Secret CF_KV_BACKUP_TOKEN gesetzt (Gültigkeit + Rechte prüft E5 im ersten Offsite-Lauf live)"
  else
    hinweis "gh secret set fehlgeschlagen – Secret manuell im Environment „$UMGEBUNG“ eintragen."
  fi
  CF_TOKEN=""
  break
done

# ---- Schritt 6 (E6): KV-Namespace ABO -----------------------------------
abschnitt "Schritt 6/7 (E6) – ID des KV-Namespace ABO"
info "Gemeint ist die ID (32 Hex-Zeichen), NICHT der Name „ABO“."
info "Zu finden: Cloudflare → Workers & Pages → Worker ff-newsletter → Settings → Bindings → KV ABO,"
info "oder Storage & Databases → Workers KV, oder: npx wrangler kv namespace list"
link "$CF_KV_URL"
while :; do
  KV_ID="$(heimlich "KV_NAMESPACE_ID_ABO einfügen (leer lassen = überspringen):")"
  [ -z "$KV_ID" ] && { hinweis "Übersprungen – Variable später selbst setzen: KV_NAMESPACE_ID_ABO (Repository-Variable)."; break; }
  if ! printf '%s' "$KV_ID" | grep -Eq '^[0-9a-fA-F]{32}$'; then
    hinweis "Keine Namespace-ID (32 Hex-Zeichen erwartet) – bitte die ID kopieren, nicht den Namen."
    continue
  fi
  if gh variable set KV_NAMESPACE_ID_ABO --repo "$QUELLE" --body "$KV_ID" 2>/dev/null; then
    ok "Repository-Variable KV_NAMESPACE_ID_ABO gesetzt"
  else
    hinweis "Variable konnte nicht gesetzt werden – manuell eintragen (Settings → Variables)."
  fi
  break
done

# ---- Schritt 7 (E7): D1 optional ----------------------------------------
abschnitt "Schritt 7/7 (E7, optional) – D1-Datenbank des Klick-Zählers"
if frage_ja "Soll der Klick-Zähler (D1) mitgesichert werden?"; then
  info "ID: Cloudflare → Storage & Databases → D1 → Datenbank des Klick-Zählers (32 Hex-Zeichen)."
  info "Der CF-Token aus Schritt 5 braucht dafür zusätzlich „D1: Read“."
  while :; do
    D1_ID="$(heimlich "D1_DATABASE_ID einfügen (leer lassen = überspringen):")"
    [ -z "$D1_ID" ] && { hinweis "Übersprungen."; break; }
    if ! printf '%s' "$D1_ID" | grep -Eq '^[0-9a-fA-F]{32}$'; then
      hinweis "Keine D1-ID (32 Hex-Zeichen erwartet) – bitte neu."
      continue
    fi
    gh variable set D1_DATABASE_ID --repo "$QUELLE" --body "$D1_ID" 2>/dev/null \
      && ok "Repository-Variable D1_DATABASE_ID gesetzt" \
      || hinweis "Variable konnte nicht gesetzt werden – manuell eintragen."
    break
  done
else
  info "Übersprungen – der Klick-Zähler wird nicht gesichert (E7 bleibt optional)."
fi

# ---- Abschluss -----------------------------------------------------------
abschnitt "Abschluss – Stand prüfen"
if check; then
  echo
  if frage_ja "Ersten Sicherungslauf jetzt starten (gh workflow run backup-offsite.yml --ref main)?"; then
    if gh workflow run backup-offsite.yml --ref main --repo "$QUELLE"; then
      ok "Lauf gestartet – Stand: gh run list --workflow=backup-offsite.yml"
      info "Der erste GRÜNE Lauf schließt Meldung #761 automatisch."
      info "Danach einmal die Wiederherstellung proben: bash scripts/restore_drill.sh --repo $ZIEL"
    else
      hinweis "Lauf konnte nicht gestartet werden – Actions → „Offsite-Backup“ → Run workflow (Branch main)."
    fi
  fi
else
  echo
  hinweis "Es sind noch Punkte offen – die Liste oben nennt jeden mit Link."
  info "Jederzeit nachprüfen: bash scripts/backup_einrichten_wizard.sh --check"
  exit 1
fi
