# Live-Proben · security.txt 404 + sw.js ohne SHA + Backup-Wizard (25.10.2026)

**Auftrag:** Fahrplan des Inhabers vom 25.10.2026 – „Patch 1 als PR mergen,
Deploy abwarten. Probe: `/.well-known/security.txt` zeigt `Contact:`,
`/sw.js` trägt eine SHA. Danach Sicherung einrichten (WF-9E5A / #761),
Abnahme, danach Patch 2 (Hugo 0.168) als eigener PR.“
**Datum:** 25.10.2026 · **Branch:** `arena/68dd96be-franksfinanzcheck-blog` · **Basis:** `6cfd0d1` (main)
**Bearbeiter:** Arena Agent

---

## 1. Befund (Live-Messung 25.10.2026, vor dem Eingriff)

Beide Proben des Fahrplans waren **rot** – und beide waren von außen nicht
als Build-Fehler sichtbar (Quelle, Gates und `gh-pages`-Zweig waren grün):

| Probe | Live-Zustand 25.10., ~12:20 UTC | Erwartung |
|---|---|---|
| `GET /.well-known/security.txt` | **HTTP 404** (eigene 404-Seite, auch mit Cache-Buster) | `Contact:` (RFC 9116) |
| `GET /sw.js` | `const VERSION="dev"` – alle Precache-URLs `?v=dev` | `VERSION="<Commit-SHA>"` |

### 1.1 Ursache security.txt-404: `upload-pages-artifact` schließt Dotfiles aus

- `static/.well-known/security.txt` liegt seit dem 14.10.2026 (#750,
  Befund I-03) korrekt im Bestand (Contact ×2, Expires 2027-10-01, Policy).
- Der `gh-pages`-Zweig (peaceiris-Push desselben `public/`) **enthält** die
  Datei (487 Bytes) – die Audit-Spur war also grün.
- Das offizielle Pages-Deployment (Quelle der Wahrheit seit #537) entsteht
  über `actions/upload-pages-artifact@v5.0.0`. Die Action archiviert seit
  v4 mit `tar --exclude=.[^/]*`, sofern nicht `include-hidden-files: true`
  gesetzt ist. **Nachbau am 25.10. mit dem Real-Build:**
  - mit Ausschluss: `0` well-known-Einträge im Artefakt-Tar
  - ohne Ausschluss: `./.well-known/security.txt` enthalten
- Ergebnis: 11 Tage Schein-Grün der #537-Klasse – Quelle richtig,
  Audit-Spur richtig, **Auslieferung falsch**. Die Sicherheits-Wache prüft
  Header/Worker (F-01–F-08), aber nicht die Erreichbarkeit der
  security.txt; deshalb fiel es keinem Gate auf.

Versteckte Pfade des Builds sind ausschließlich `.well-known/` und
`.nojekyll` (Bestand am 25.10. verifiziert) – `include-hidden-files`
publiziert also nichts Unerwartetes; `.git`/`.github` schließt die Action
weiterhin immer aus.

### 1.2 Ursache sw.js ohne SHA: `HUGO_JSDELIVR_SHA` wurde nie injiziert

- Der Cache-Generationen-Vertrag steht in `layouts/index.sw.js`:
  `const VERSION = '{{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}'` –
  beim Aktivieren einer neuen Generation fliegen alte Caches.
- Verbraucher: `asset_url.html`, `cover.html`, `ff_fontfaces.html`,
  `index.sw.js`, dokumentiert in `hugo.toml` und `docs/INFRASTRUKTUR.md`
  („HUGO_JSDELIVR_SHA=<sha> als Cache-Buster“).
- `e2e.yml`, `layout-ai.yml` und `pinterest-watchdog.yml` bauen längst mit
  `HUGO_JSDELIVR_SHA: ${{ github.sha }}` – **nur `deploy.yml` und
  `notfall-deploy.yml` nicht**. Live lief deshalb jeder Browser mit der
  Cache-Generation `dev`: kein Rotationspunkt nach Deploys, Asset-Frische
  allein über Pages' `max-age=600`.

## 2. Reparatur (Patch 1)

| Datei | Änderung |
|---|---|
| `.github/workflows/deploy.yml` | Job `deploy` bekommt `env: HUGO_JSDELIVR_SHA: ${{ github.sha }}` (Job-Ebene → gilt für Erst-Build UND Rebuild nach Gate-Heilungen). Upload-Schritt bekommt `include-hidden-files: true`. |
| `.github/workflows/notfall-deploy.yml` | Gleichlautend für Job `bauen` + Upload – der Notfall-Pfad muss dieselbe Auslieferungsqualität liefern. |
| `scripts/tests/test_pages_deployment_guard.py` | Neue Klasse `AuslieferungsProbenTestCase` (4 Tests): `include-hidden-files` in BEIDEN Pfaden, `HUGO_JSDELIVR_SHA=${{ github.sha }}` in BEIDEN Build-Jobs, security.txt-Quelle mit `Contact:`/`Expires:`, Allowlist der versteckten `static/`-Pfade (`.well-known`, `.nojekyll`). |

Bewusst **nicht** geändert: `layouts/index.sw.js` (steht unter
Integritäts-Siegel und ist korrekt – nur die Zufuhr fehlte) und
`robustheits_gate.py` R5 (prüft die gebaute Wahrheit; ein lokaler Build
ohne Env bleibt legitim `dev` – der Vertrag sitzt jetzt auf der
Workflow-Ebene, wo die Variable gesetzt wird).

**Lokaler Wirkungsnachweis (25.10., Hugo Extended 0.164.0, `--minify`):**
`HUGO_JSDELIVR_SHA=probe123sha` → `public/sw.js` trägt
`VERSION="probe123sha"`, Font-URLs im HTML `?v=probe123sha`,
`public/.well-known/security.txt` vorhanden. Tar-Nachbau der Action:
mit Flag reist die Datei mit, ohne Flag nicht (siehe 1.1).

## 3. Backup-Einrichtung (WF-9E5A / #761) – Stand und Wizard

Die Einrichtungsprüfung des letzten Offsite-Laufs (25.10., Run 40174807888)
listet offen: **E1** (`BACKUP_REPO` + privates Ziel-Repo fehlt),
**E2** (`BACKUP_REPO_TOKEN`), **E3** (`BACKUP_PASSPHRASE`),
**E5** (`CF_KV_BACKUP_TOKEN`), **E6** (`KV_NAMESPACE_ID_ABO`),
**E8** (Environment „backup“ ohne Branch-Regel). E4
(`CLOUDFLARE_ACCOUNT_ID`) ist vorhanden. Diese Punkte brauchen den
Inhaber: Secrets, PAT-Formulare, Passwort-Manager und das
Cloudflare-Konto sind für Agenten unerreichbar – und das bleibt so
(CLAUDE.md N-17).

**Neu:** `scripts/backup_einrichten_wizard.sh`

- `--check`: prüft E1–E8 lokal über die GitHub-API (Environment-Regel,
  Variablen-Werte, Secret-**Namen** – Werte zeigt GitHub nie), ehrliche
  „nicht prüfbar“-Pfade bei fehlenden Rechten, Exit 1 bei offenem
  Pflichtpunkt.
- Interaktiv: führt in Anleitung-Reihenfolge (erst E8, dann E1–E7) durch
  die Einrichtung – Environment anlegen + Branch-Regel „nur main“ per API,
  privates Ziel-Repo anlegen (`gh repo create`), Variable `BACKUP_REPO`,
  Passphrase verdeckt (32+ Zeichen, Übergabe per stdin, nie im Log),
  fine-grained PAT mit **Live-Probe gegen das Ziel-Repo** (401/404 werden
  benannt, Token erscheint nirgends), Cloudflare-Token mit Verify-Probe,
  KV-/D1-IDs mit Formatprüfung (32 Hex-Zeichen), Abschluss-Check und
  optionalem Start des ersten Laufs.
- Grenzen (im Kopf dokumentiert): die **Tiefprüfung** (Token-Gültigkeit im
  Backup-Kontext, Namespace lesbar, Ablauf-Fristen) macht weiterhin
  `scripts/backup_einrichtung.py` im Lauf; ein feingranularer PAT lässt
  sich nicht per CLI erzeugen (das Formular wird vorbelegt geöffnet).
- `docs/ANLEITUNG-OFFSITE-BACKUP.md` verweist auf den Wizard;
  `backup-frischwache.yml` prüft täglich `bash -n` des Wizards
  (derselbe Schritt wie `restore_drill.sh`).

**Abnahme-Fahrplan (Inhaber, eigener Rechner, `gh auth login`):**

1. `bash scripts/backup_einrichten_wizard.sh --check` (Stand)
2. `bash scripts/backup_einrichten_wizard.sh` (Einrichtung E8→E7)
3. `gh workflow run backup-offsite.yml --ref main` – der erste **grüne**
   Lauf schließt #761 automatisch
4. `gh workflow run backup-frischwache.yml --ref main` (RPO-Wache)
5. `bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup`

## 4. Prüfungen (lokal, vor dem Push)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_pages_deployment_guard` | ✅ 11/11 (7 Bestand + 4 neu) |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` | ✅ 29/29 (inkl. FrischwacheVertrag) |
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 17 Fallgruppen |
| `python3 scripts/automation_premium_audit.py --strict` | ✅ Exit 0 |
| `python3 scripts/hugo_build_vertrag.py` (+ `--selftest`) | ✅ H1–H8 |
| `python3 scripts/blustradius_register.py` (+ `--selftest`) | ✅ 69 Schritte |
| `bash -n scripts/backup_einrichten_wizard.sh` | ✅ |
| Wizard `--check` gegen Live-Repo | ✅ Befund deckungsgleich mit Run 40174807888 |
| YAML-Parse aller drei geänderten Workflows | ✅ |

## 5. Abnahme nach dem Merge (offen)

1. Deploy abwarten (Push auf `main` → „Deploy auf GitHub Pages“ +
   `pages-deployment`).
2. Probe 1: `https://franksfinanzcheck.de/.well-known/security.txt` →
   HTTP 200, `Contact:` sichtbar.
3. Probe 2: `https://franksfinanzcheck.de/sw.js` → `VERSION="<40-hex-sha>"`
   des Deploy-Commits (nicht mehr `dev`).
4. Danach Patch 2 (Hugo 0.164.0 → 0.168.0) als **eigener** PR.
