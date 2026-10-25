# Anleitung: Offsite-Backup einrichten, prüfen, wiederherstellen

> Vorgang WF-9E5A · Meldung #761 · Stand 24.10.2026 (Highend-Dauerheilung)
> Workflows `.github/workflows/backup-offsite.yml` + `backup-frischwache.yml` · Prüfer `scripts/backup_einrichtung.py` ·
> Frische-Wache `scripts/backup_freshness_guard.py` · Probe `scripts/restore_drill.sh` · Export `scripts/kv_backup.py`

## Kurz: Was ist zu tun?

Die nächtliche Sicherung der Abonnenten und Einwilligungsnachweise (Job
„KV-/D1-Backup“) ist **absichtlich rot**, bis die Zugänge unten eingerichtet
sind. Das kann nur der Inhaber: An Secrets und an das Cloudflare-Konto kommen
Agenten nicht heran, und das ist auch richtig so. Aufwand: etwa 10 Minuten,
alle Links sind vorbelegt.

| # | Was | Wohin | Prüfpunkt |
|---|---|---|---|
| 1 | Environment `backup` absichern (nur `main`) – **zuerst** | Settings → Environments → `backup` | E8 |
| 2 | Privates Backup-Repository | Variable `BACKUP_REPO` (Repository) | E1 |
| 3 | Passphrase (zufällig, 32+ Zeichen) | Secret `BACKUP_PASSPHRASE` (Environment `backup`) | E3 |
| 4 | GitHub-Schreibzugang (fine-grained, 366 Tage) | Secret `BACKUP_REPO_TOKEN` (Environment `backup`) | E2 |
| 5 | Cloudflare-Lesezugang (nur KV lesen) | Secret `CF_KV_BACKUP_TOKEN` (Environment `backup`) | E5 |
| 6 | ID des KV-Namespace ABO | Variable `KV_NAMESPACE_ID_ABO` (Repository) | E6 |
| – | Cloudflare-Konto-ID | Secret `CLOUDFLARE_ACCOUNT_ID` – **schon vorhanden** | E4 |
| – | optional: D1-Datenbank (Klick-Zähler) | Variable `D1_DATABASE_ID` (Repository) – nur wenn der Klick-Zähler mitgesichert werden soll | E7 |

**Erst absichern, dann befüllen:** Schritt 1 kommt vor jedes Secret. Sonst
liegen die Zugänge, und sei es nur für Minuten, in einem Environment, das
jeder Branch nutzen darf. Die Einrichtungsprüfung im Lauf setzt denselben
Hinweis an den Anfang ihrer Liste („Zuerst E8“), solange das zutrifft.

**Komfort-Weg (seit 25.10.2026):** Statt der sechs Klickstrecken führt
`bash scripts/backup_einrichten_wizard.sh` am eigenen Rechner interaktiv
durch dieselben Schritte (erst E8, dann E1–E7; Geheimnisse werden verdeckt
abgefragt, nie geloggt; PAT-/Cloudflare-Formulare werden vorbelegt
geöffnet). `bash scripts/backup_einrichten_wizard.sh --check` prüft den
Stand jederzeit ohne Änderung. Beide Wege enden an derselben Stelle.

Danach: Actions → „Offsite-Backup“ → „Run workflow“ (Branch `main`). Grün
heißt gesichert. Die offene Meldung schließt sich beim ersten grünen Lauf
von selbst.

**Dringlichkeit:** Das Anmeldeformular ist geschaltet (`newsletterFormAction`
in `hugo.toml`), und der Worker antwortet (Newsletter-Lauf vom 13.10.2026:
0 aktive Abonnenten). Jede Anmeldung erzeugt einen Einwilligungsnachweis
(Art. 7 Abs. 1 DSGVO), der ohne diese Einrichtung **nur** in Cloudflare
liegt. Deshalb jetzt einrichten, vor den ersten Anmeldungen.

## Was gesichert wird – und wo

| Job | Inhalt | Verschlüsselung | Ziel | Aufbewahrung |
|---|---|---|---|---|
| `backup` | Git-Bundle von `main` + Arbeitskopie (öffentlicher Code) | AES-256-CBC, PBKDF2 200 000 | privates Repo, **Entwurfs**-Release `backup-…` | 14 |
| `kv-backup` | Workers KV `ABO`: `abo:`, `token:`, `nachweis:` (+ optional D1) | AES-256-CBC, PBKDF2 600 000 | privates Repo, Entwurfs-Release `kv-backup-…` | 35 (5 Wochen) |

Die Grundsätze stammen aus dem Sicherheitsaudit (M-11) und der
Marken-Oberflächen-Wache vom 20.09.2026:

- **Nie öffentlich.** Vor jedem Upload wird live geprüft, dass das Ziel privat ist.
- **Nie als Actions-Artefakt.** Bei öffentlichen Repos kann jeder angemeldete
  GitHub-Nutzer Artefakte laden.
- **Jede Verschlüsselung mit Rückweg-Probe.** Die Datei wird testweise
  entschlüsselt und bytegenau verglichen.
- **Jeder Upload wird nachgelesen.** Geprüft werden die Größe und ob das
  Release ein Entwurf ist.
- **Fehlt etwas, ist der Lauf rot.** Kein Schein-Grün.

### Betriebszusagen (Profi-Niveau: SLA · RPO · RTO · Abdeckung)

| Zusage | Wert | Beleg |
|---|---|---|
| **RPO** (max. Datenverlust) | 24 h + Scheduler-Toleranz (52 h) | Täglich 03:00 UTC; GitHub-Scheduler belegt 09:53–12:03 MESZ; **automatisierte** Frischwache `backup-frischwache.yml` (13:00 UTC) rot ab 52 h, gelb ab 36 h |
| **RTO** (Wiederherstellung) | < 30 Min. für KV, < 60 Min. für Repo | Probe `restore_drill.sh` in < 5 Min.; Ernstfall-Anleitung unten mit `gh release download` + `openssl` + `wrangler kv bulk put --remote` |
| **Aufbewahrung** | Repo 14, KV 35 Releases (Entwürfe) | `backup-offsite.yml` KEEP=14 / 35; älteste darüber automatische Löschung |
| **Verschlüsselung** | AES-256-CBC/PBKDF2, Bundle 200k, KV 600k | Workflow + Prüfer `backup_einrichtung.py` E3 (≥ 20 Zeichen, empfohlen 32+) |
| **Prüfung** | 8 Live-Punkte E1–E8 je Lauf, 3 Frist-Stufen, 17 Fallgruppen Selbsttest | `backup_einrichtung.py --selftest`, `test_backup_einrichtung` (26 Tests) |
| **Ablauf-Warnung** | 30 Tage gelb, 14 Tage rot (nach Sicherung) | `BACKUP_FRIST_TAGE` → letzter Schritt `Fristwarnung` + Alerting `backup-frist` |
| **Operative Wache** | Täglich 13:00 UTC, beide Familien `backup-*` + `kv-backup-*` | `backup_freshness_guard.py` (12 Fälle) + Workflow `backup-frischwache.yml` → Alerting `backup-frisch` |

**Was gesichert wird – vollständig:**

| KV-Präfix | Inhalt | DSGVO-Relevanz | Quelle |
|---|---|---|---|
| `abo:` | Aktive Abonnenten (Status, Zeitstempel) | Art. 7 (1) Nachweis der Einwilligung | Worker `ABO` |
| `token:` | Bestätigungs-/Abmelde-Tokens (→ abo:) | Technisch für Double-Opt-In | Worker `ABO` |
| `nachweis:` | Einwilligungsnachweis (IP, Zeit, Text-Stand) | Art. 7 (1) Nachweispflicht | Worker `ABO` |
| `budget:` | Tagesbudget Anmeldung/Feedback (TTL) | Betrieb, nicht personenbezogen | Worker `ABO` |
| `exportlog:` | Export-Protokoll (TTL 30 d) | Betrieb | Worker `ABO` |
| `takt:` | Taktgeber letzte Läufe | Betrieb | Worker `ABO` |
| `feedback:` + `fbtag:` | Artikel-Feedback je Tag | Betrieb | Worker `ABO` |
| D1 | Klick-Zähler (optional) | Betrieb | Cloudflare D1 |

> Alle KV-Schlüssel werden gesichert – nicht nur die drei Pflicht-Präfixe.
> Die Probe `kv_backup.py --pruefen` und `restore_drill.sh` beweisen die
> Wiederherstellbarkeit (Struktur, keine verwaisten Tokens, Zähler).

**Was NICHT gesichert wird (bewusst, mit Mitigation):**

| Nicht im Backup | Warum | Mitigation |
|---|---|---|
| GitHub Issues/PRs/Discussions | Nicht im Git, API-limitiert | Wöchentlich manuell exportieren oder `gh issue list` archivieren (nicht automatisiert – geringes Volumen) |
| GitHub Secrets/Variablen | GitHub gibt Secrets nie heraus | In 1Password dokumentieren (Anleitung Schritt 3–5) |
| Cloudflare-Zone (DNS, Regeln) | Nicht im KV, nicht im Repo | `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` A1 dokumentiert Sollstand; `edge:freigabe` misst |
| `gh-pages` Branch | Regenerierbar (Build-Artefakt) | Quelle `main` ist gesichert; `deploy.yml` baut neu |
| Worker-Logs (> 200k Zeilen/Tag) | Flüchtig (Free 1 d) | Nicht kritisch; bei Incident vorher exportieren |

**Frische operativ überwachen (automatisiert seit 24.10.2026):**

```bash
# Lokal oder in CI (braucht Lese-Token auf Backup-Repo):
python3 scripts/backup_freshness_guard.py --repo frank-hartung/franksfinanzcheck-backup
python3 scripts/backup_freshness_guard.py --selftest   # 12 Fälle offline
npm run backup:frische   # Kurzform
```

- **Automatisch:** Workflow `backup-frischwache.yml` läuft täglich **13:00 UTC** (nach
  dem 03:00 UTC-Sicherungslauf + Puffer für GitHub-Scheduler-Verspätung bis 12:03 MESZ).
  Urteil `fehler` (>52 h oder fehlende Familie) → Workflow rot → Alerting `backup-frisch`
  mit RPO-Rat; `warnung` (>36 h) → gelber Hinweis in der Summary (Frühwarnung).
- **Manuell:** Zusätzlich vor Releases oder nach Token-Tausch: `npm run backup:frische`.

Die Frische-Wache ergänzt E1–E8: Sie misst, ob die Sicherung *jüngst* wirklich
lief (täglich erwartet, 52 h Toleranz). Ein grünes `backup_einrichtung` ohne
frisches Backup ist eine Konfigurations-, aber keine Betriebsgarantie – deshalb
laufen beide Wachen unabhängig.

## Einrichtung Schritt für Schritt

Ablage-Regel: **Secrets** ins Environment `backup` (Settings → Environments →
`backup` → „Environment secrets“), **Variablen** auf Repository-Ebene
(Settings → Secrets and variables → Actions → Variables). Beide Jobs des
Workflows laufen im Environment `backup` und sehen deshalb beides.

### Schritt 1 – Environment `backup` absichern (E8)

**Zuerst, bevor ein einziges Secret eingetragen wird.** Das Environment besteht
seit dem ersten Lauf am 15.10.2026, steht aber jedem Branch offen. Wer erst
befüllt und dann absichert, lässt die Zugänge eine Weile ungeschützt liegen.
(Fehlt es, unter „New environment“ mit dem Namen `backup` anlegen.)

Settings → Environments → `backup`: <https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments>

- **Deployment branches and tags → „Selected branches and tags“ → nur `main`.**
  Ohne diese Regel kommt jeder Branch an die Backup-Zugänge, etwa ein
  Arbeitszweig mit geänderter Workflow-Datei (Sicherheitsaudit F-07).
- **Keine „Required reviewers“.** Sonst wartet jeder nächtliche Lauf auf
  einen Klick und bricht nach 30 Tagen ab.

Der Prüfer liest diese Einstellungen bei jedem Lauf und meldet Abweichungen
als Hinweis; die Sicherung läuft trotzdem. Solange Zugänge fehlen und das
Environment offensteht, setzt er „Zuerst E8“ an den Anfang der Prüfliste.

### Schritt 2 – Privates Backup-Repository anlegen (E1)

1. Vorbelegtes Formular öffnen – Sichtbarkeit **Private** ist gesetzt:
   <https://github.com/new?owner=frank-hartung&name=franksfinanzcheck-backup&visibility=private&description=Private+Sicherungen+%28verschl%C3%BCsselt%29>
   → „Create repository“. README und Lizenz sind nicht nötig.
2. Repository-Variable anlegen: <https://github.com/frank-hartung/franksfinanzcheck-blog/settings/variables/actions> → „New repository
   variable“ → Name `BACKUP_REPO`, Wert `frank-hartung/franksfinanzcheck-backup`.

### Schritt 3 – Passphrase erzeugen (E3)

1. Im Passwort-Manager einen Eintrag „FranksFinanzcheck – Backup-Passphrase“
   anlegen und ein zufälliges Passwort mit **mindestens 32 Zeichen** erzeugen
   lassen. Alternativ im Terminal: `openssl rand -base64 33`.
2. **Erst speichern, dann eintragen.** Die Passphrase ist der einzige
   Schlüssel zu allen Sicherungen. Geht sie verloren, ist jede Sicherung
   wertlos. Sie gehört nie in einen Chat, ein Issue, einen Commit oder eine Mail.
3. Environment `backup` → „Add environment secret“ → Name `BACKUP_PASSPHRASE`.

Der Prüfer verlangt mindestens 20 Zeichen (E3). Die Länge selbst gibt er nie aus.

### Schritt 4 – GitHub-Schreibzugang (E2)

1. Vorbelegtes Formular öffnen:
   <https://github.com/settings/personal-access-tokens/new?name=ff-offsite-backup&description=Offsite-Backup%3A+Entwurfs-Releases+im+privaten+Backup-Repo+%28nur+dieses+Repo%29&target_name=frank-hartung&expires_in=366&contents=write>
   Vorbelegt sind Name, Beschreibung, Besitzer, **Ablauf 366 Tage** und das
   Recht **Contents: Read and write**.
2. **Repository access → „Only select repositories“ → nur
   `franksfinanzcheck-backup`.** Diese Auswahl lässt sich nicht vorbelegen und
   muss von Hand gesetzt werden. „All repositories“ wäre ein Generalschlüssel.
3. „Generate token“ klicken, den Token kopieren und im Environment `backup`
   als Secret `BACKUP_REPO_TOKEN` speichern.

Warum 366 Tage? GitHub schlägt sonst 30 Tage vor – dann stünde die Sicherung
nach einem Monat. Der Prüfer liest das Ablaufdatum bei jedem Lauf und weist ab
30 Tagen vorher darauf hin. 14 Tage vorher meldet sich das Alerting (siehe
„Zugänge erneuern“). Ein klassischer Token (`ghp_…`) funktioniert auch, sieht
aber **alle** Repositories – der Prüfer markiert ihn mit einem Hinweis.

### Schritt 5 – Cloudflare-Lesezugang (E5)

1. Vorbelegte Vorlage für einen Konto-Token öffnen:
   <https://dash.cloudflare.com/?to=/:account/api-tokens&permissionGroupKeys=%5B%7B%22key%22%3A%22workers_kv_storage%22%2C%22type%22%3A%22read%22%7D%5D&name=ff-kv-backup+%28nur+lesen%29>
   Vorbelegt sind das Recht **Workers KV Storage: Read** und der Name
   „ff-kv-backup (nur lesen)“. Nur dieses Konto auswählen und keine weiteren
   Rechte vergeben, schon gar keine Schreibrechte.
2. „Create Token“ klicken, den Token kopieren und im Environment `backup` als
   Secret `CF_KV_BACKUP_TOKEN` speichern.

Hinweise:

- Konto-Tokens (Account API Tokens) sind für Automationen gedacht und hängen
  nicht am persönlichen Login. Ein Nutzer-Token (My Profile → API Tokens) mit
  demselben Recht funktioniert ebenfalls; der Prüfer erkennt beide Arten.
- Soll der Klick-Zähler (D1) mitgesichert werden, braucht der Token
  zusätzlich **D1: Read**: <https://dash.cloudflare.com/?to=/:account/api-tokens&permissionGroupKeys=%5B%7B%22key%22%3A%22workers_kv_storage%22%2C%22type%22%3A%22read%22%7D%2C%7B%22key%22%3A%22d1%22%2C%22type%22%3A%22read%22%7D%5D&name=ff-kv-backup+%28nur+lesen%29>
- Bewusst **nicht** wiederverwenden: `CLOUDFLARE_API_TOKEN` (Workers AI) und
  `CF_WORKERS_DEPLOY_TOKEN` (Deploy, schreibend). Ein Backup braucht nur Lesen.

### Schritt 6 – ID des KV-Namespace ABO (E6)

1. Die ID im Cloudflare-Dashboard holen: Workers & Pages → Worker
   `ff-newsletter` → Settings → Bindings → KV-Namespace **ABO**.
   Alternativ: Storage & Databases → Workers KV (<https://dash.cloudflare.com/?to=/:account/workers/kv/namespaces>) oder im
   Terminal `npx wrangler kv namespace list`.
2. Als Repository-Variable `KV_NAMESPACE_ID_ABO` eintragen. Gemeint ist die
   ID (32 Hex-Zeichen), **nicht** der Name „ABO“.

Wichtig: Es muss **der Namespace sein, an den der laufende Worker sein
Binding `ABO` hat**. Sonst sichert der Job einen leeren Namespace. Zur
Kontrolle zeigt der Prüfer den Titel des Namespace an.

**Kopplung mit dem Worker-Deploy:** `worker-deploy.yml` nutzt dieselbe
Variable. Bisher überspringt er den Newsletter-Worker „mangels ID“. Sobald
sie gesetzt ist, versucht er bei der nächsten Änderung unter
`newsletter-worker/**` einen Deploy. Dafür braucht er `CF_WORKERS_DEPLOY_TOKEN`
im Environment `cloudflare-produktion` (siehe
`docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md`, Schritt 4). Die gemeinsame
Variable ist Absicht: So können Backup und Worker nie auf verschiedene
Namespaces zeigen – auch nicht nach dem geplanten Umzug in einen EU-Namespace.

### Schritt 7 – Lauf starten

Actions → „Offsite-Backup“ → „Run workflow“ → Branch `main`. Danach:

- In der Job-Zusammenfassung „Offsite-Backup – Einrichtungsprüfung“ sind alle
  Pflichtpunkte ✅.
- Im Backup-Repo stehen zwei Entwurfs-Releases (`backup-…` und `kv-backup-…`).
- Die offene Meldung schließt sich beim ersten grünen Lauf automatisch.

Danach einmal die Wiederherstellung proben (Abschnitt „Wiederherstellung“).

## Was der Lauf prüft (E1–E8) – und was bei Rot zu tun ist

| Punkt | Prüfung | Typischer Befund | Abhilfe |
|---|---|---|---|
| E1 | `BACKUP_REPO` gesetzt, Format `besitzer/name`, nicht das Blog-Repo | fehlt · falsches Format | Schritt 2 |
| E2 | Token gültig, Ziel erreichbar, **privat**, nicht archiviert, Ablaufdatum | 401: ungültig/abgelaufen · 404: Repo fehlt oder Token sieht es nicht · ÖFFENTLICH | Schritt 4 (bei 404: Repo im Token auswählen) |
| E3 | Passphrase mit mindestens 20 Zeichen | fehlt · zu kurz | Schritt 3 |
| E4 | Konto-ID mit 32 Hex-Zeichen | fehlt · Format | Dashboard → Workers & Pages, rechte Spalte |
| E5 | Cloudflare-Token aktiv (Nutzer- oder Konto-Token), Ablaufdatum | nicht anerkannt · abgelaufen · deaktiviert | Schritt 5 |
| E6 | Namespace-ID: Format, mit **diesem** Token lesbar | Name statt ID · 403: Recht fehlt · 404: falsches Konto | Schritt 6 bzw. Schritt 5 |
| E7 | optional: D1-Datenbank lesbar | nicht lesbar | D1: Read ergänzen oder Variable entfernen |
| E8 | Environment nur für `main`, ohne Pflicht-Freigabe | Hinweis (vor dem Befüllen: „Zuerst E8“) | Schritt 1 |

„GitHub-API nicht erreichbar“ oder „Cloudflare-API nicht erreichbar“ ist
meist vorübergehend: den Lauf später neu starten.

### Fehlerbilder

Diese Fehler treten in den Schritten nach der Prüfung auf:

- **„Ablage in … fehlgeschlagen“:** Der Token darf nicht schreiben. Prüfen,
  ob er „Contents: Read and write“ hat und das Backup-Repo ausgewählt ist
  (Schritt 4).
- **„unvollständig oder kein Entwurf … Teil-Release wird entfernt“:** Der
  Upload ist abgebrochen; die halbe Sicherung wurde wieder entfernt. Meist
  vorübergehend, also neu starten.
- **„Verschlüsselung nicht umkehrbar“:** ein Problem auf dem Runner. Neu
  starten; bleibt der Fehler, ein Issue mit Lauf-Link anlegen.
- **Export schlägt fehl (`kv_backup.py`):** entweder eine Störung bei
  Cloudflare (<https://www.cloudflarestatus.com>) oder der Token wurde
  zwischenzeitlich widerrufen. Der nächste Lauf prüft ihn erneut (E5).
- **Repo-Job: „nicht nachweislich privat (Antwort: UNBEKANNT, API: …)“:**
  „Not Found“ heißt, das Repo fehlt oder der Token sieht es nicht.
  „Bad credentials“ heißt, der Token ist ungültig oder abgelaufen.

## Zugänge erneuern

Der Prüfer liest bei jedem Lauf die Ablaufdaten: bei GitHub aus der
Kopfzeile `github-authentication-token-expiration`, bei Cloudflare aus
`expires_on`.

| Resttage | Wirkung |
|---|---|
| 30 und mehr | nichts |
| unter 30 | gelber Hinweis in Prüfung und Zusammenfassung |
| unter 14 | Schritt „Fristwarnung“ wird rot und das Alerting meldet sich. **Die Sicherung des Tages ist trotzdem gelaufen.** |
| abgelaufen | Prüfung rot, keine Sicherung |

So wird erneuert:

- **GitHub-Token:** Settings → Developer settings → Fine-grained tokens →
  Token → „Regenerate token“ (Rechte und Repo-Auswahl bleiben erhalten).
  Danach den neuen Wert in `BACKUP_REPO_TOKEN` (Environment `backup`) ersetzen.
- **Cloudflare-Token:** API Tokens → Token → „Roll“. Danach den neuen Wert
  in `CF_KV_BACKUP_TOKEN` ersetzen.
- Anschließend „Run workflow“ starten; ein grüner Lauf schließt die Fristmeldung.

**Passphrase wechseln** nur mit Bedacht: Ältere Sicherungen bleiben mit der
**alten** Passphrase verschlüsselt. Deshalb beide im Passwort-Manager
behalten, mit dem Datum des Wechsels. Ist die Aufbewahrung abgelaufen
(35 Tage), wird die alte Passphrase nicht mehr gebraucht.

## Wiederherstellung

Voraussetzungen: `gh` (angemeldet mit `gh auth login`), `openssl` und
`python3`. Alle Befehle im Wurzelverzeichnis des Repos ausführen.

### Probe (nach der Einrichtung, danach vierteljährlich)

```bash
bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup
```

Die Probe läuft so ab:

1. Sie holt die neuesten Sicherungen (Entwürfe eingeschlossen) und fragt die
   Passphrase verdeckt ab.
2. Sie entschlüsselt in ein Temp-Verzeichnis (Rechte 0700), das am Ende
   gelöscht wird.
3. Sie beweist, dass der KV-Export vollständig und konsistent ist
   (`kv_backup.py --pruefen`; im Log stehen nur Zähler).
4. Sie beweist, dass sich das Git-Bundle klonen lässt und Artikel und
   Rechtsseiten enthält.

Ist die neueste Sicherung älter als 48 Stunden, warnt sie. Mit `--nur-kv`
oder `--nur-git` lässt sich die Probe eingrenzen.

### Ernstfall: Abonnenten zurückspielen

```bash
TAG=$(gh api "repos/frank-hartung/franksfinanzcheck-backup/releases?per_page=100" \
  --jq '[.[] | select(.tag_name | startswith("kv-backup-"))] | sort_by(.created_at) | last | .tag_name')
gh release download "$TAG" --repo frank-hartung/franksfinanzcheck-backup --pattern kv-export.json.enc
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in kv-export.json.enc -out kv-export.json
python3 scripts/kv_backup.py --pruefen kv-export.json
python3 scripts/kv_backup.py --wrangler-bulk kv-export.json > bulk.json
npx wrangler kv bulk put bulk.json --namespace-id <ID-des-Ziel-Namespace> --remote
shred -u kv-export.json bulk.json 2>/dev/null || rm -f kv-export.json bulk.json
```

- `openssl` fragt die Passphrase ab.
- **`--remote` ist Pflicht.** Wrangler 4 schreibt KV-Befehle ohne diese
  Angabe in eine *lokale* Simulation und meldet trotzdem Erfolg. Dann wäre
  nichts wiederhergestellt.
- Die Klartext-Dateien enthalten E-Mail-Adressen. Nach dem Einspielen löschen
  (letzte Zeile).
- Einträge, die schon abgelaufen wären (etwa offene Bestätigungen),
  überspringt `--wrangler-bulk` automatisch.
- D1, falls mitgesichert: Die Tabellen stehen im Export unter `d1.tabellen`.

### Ernstfall: Repository wiederherstellen

```bash
TAG=$(gh api "repos/frank-hartung/franksfinanzcheck-backup/releases?per_page=100" \
  --jq '[.[] | select(.tag_name | startswith("backup-"))] | sort_by(.created_at) | last | .tag_name')
gh release download "$TAG" --repo frank-hartung/franksfinanzcheck-backup --pattern backup.bundle.enc
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in backup.bundle.enc -out backup.bundle
git clone backup.bundle franksfinanzcheck-blog-wiederhergestellt
```

## Sicherheit

- Die Secrets liegen im Environment `backup` und sind nur für `main`
  erreichbar (Schritt 1).
- Der GitHub-Token sieht nur das Backup-Repo. Der Cloudflare-Token darf nur lesen.
- Der Prüfer gibt nie einen Secret-Wert aus, sondern nur Namen, Zustände und
  API-Antworten. Sein Selbsttest prüft das mit vergifteten Werten.
- **Gerät ein Token in falsche Hände:** Token sofort löschen (GitHub bzw.
  Cloudflare), neu erzeugen und das Secret ersetzen. Mit dem GitHub-Token
  allein lässt sich nur das Backup-Repo beschreiben; ohne Passphrase sind die
  Sicherungen unlesbar.

## Optional: Marken-Oberfläche

Läufe in einem Environment erscheinen auf der Startseite des Repos in der
Seitenleiste „Deployments“ – hier also `backup`. Ausblenden lässt sich das
über das Zahnrad bei „About“ → „Include in the home page“ → „Deployments“
abwählen.

## Hintergrund: Vorgang WF-9E5A / #761

Am 15.10.2026 war der KV-Job ab seinem ersten Lauf rot: Fünf von sechs
Voraussetzungen fehlten. Dass er rot war, ist richtig – ein Grün ohne
Sicherung wäre ein Schein-Grün. Behoben wurden die Umstände:

- **Rat:** Die Meldung riet zu „API-Key (GROQ/GEMINI)“ und „neu starten“.
  Jetzt nennt sie die Einrichtung und verlinkt diese Anleitung. Ändert sich
  die Einordnung, führt der nächste rote Lauf eine offene Meldung nach – auch
  #761 selbst.
- **Prüfung:** Die alte Prüfung sah nur, *ob* ein Wert gesetzt ist. Jetzt
  prüft sie, ob er wirkt (E1–E8).
- **Verweis:** „siehe Umsetzungs-Runbook“ zeigte auf keine Datei. Jetzt
  verweist er hierher.
- **Fristen:** Auslaufende Tokens hätten die Sicherung eines Tages still
  beendet. Jetzt gibt es eine Fristwarnung mit 14 Tagen Vorlauf.
- **Environment:** Der Repo-Job lief ohne Environment `backup` und hätte die
  dort abgelegten Secrets nicht gesehen.
- **Rückspielen:** Ohne `--remote` hätte das Rückspielen nur lokal
  geschrieben.

Details stehen im Bericht `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md`.
