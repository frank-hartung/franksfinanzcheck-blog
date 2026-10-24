# Wartung · Betriebspflege · Vorgang WF-E813 (#815) — Highend-Dauerheilung auf Profi-Agentur-Niveau (24.10.2026)

**Auftrag:** `Wartung · Betriebspflege · Vorgang WF-E813 #815 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 24.10.2026 · **Branch:** `arena/41b69185-franksfinanzcheck-blog` · **Basis:** `8a0ac6b` (`main`, 24.10.2026)
**Vorgänger:** `SICHERHEITS-WACHE-WF-E813-DAUERHEILUNG-PREMIUM-2026-10-15.md` · `WF-E813-809-DAUERHEILUNG-PREMIUM-2026-10-19.md` · `SICHERHEITS-WACHE-WF-E813-809-DAUERHEILUNG-2026-10-19.md`

---

## 1. Forensischer Ist-Befund (belegt an den Live-Läufen bis 24.10.2026)

Die Check-Annotationen der jüngsten Produktionsläufe auf `main` belegen lückenlos, warum Vorgang **WF-E813 (#815)** seit dem 19.10.2026 offen steht und warum **selbst nach Ausführung der bisherigen Runbook-Schritte zwei garantierte Folgefehler im Repository gelauert hätten**:

### 1.1 Was live rot ist (Run `40086795921` vom 24.10.2026, Check-Run `120851312423`, sowie Run `39945360551`)

1. **Säule 1 — `F-01 BEFUND` (10 Einzel-Annotationen):**
   Auf `https://franksfinanzcheck.de/` und `https://franksfinanzcheck.de/methodik/` fehlen live alle fünf Pflicht-Kopfzeilen (`strict-transport-security`, `x-content-type-options`, `x-frame-options`, `referrer-policy`, `content-security-policy`), weil die Zone in Cloudflare noch nicht auf `Proxied` + Transform Rule `FF Sicherheits-Header` umgestellt wurde (Inhaber-Aufgabe Runbook A1).
2. **Säule 2 — `Worker STOERUNG` (2 Einzel-Annotationen):**
   > `Authentifiziertes Betriebsbild unvollständig (Felder fehlen: budget, turnstile, schluesselrollen, exporte). Öffentliche /healthz-Antwort, falscher Leseschlüssel oder veralteter Worker-Deploy; kein Schutzstatus belegt.`
3. **Warum der Worker-Deploy nie lief (Run `40100342025` vom 24.10.2026, 13:57 UTC, `worker-deploy.yml`):**
   - Job `Deploy planen` lief **grün (`success`)**, obwohl `newsletter-worker/` geändert wurde.
   - Versteckt in einer `::notice::`-Annotation stand die echte Ursache:
     > `newsletter-worker wird nicht deployt: Repository-Variable KV_NAMESPACE_ID_ABO fehlt (ersetzt „HIER-DIE-ID-NACH-ERSTELLUNG“)`
   - Job `Deploy ${{ matrix.worker }}` wurde **`skipped`**, der gesamte Workflow meldete **`success` (Schein-Grün)**.

---

### 1.2 Fünf reale Code- und Architektur-Defekte im Bestand (Highend-Audit 24.10.2026)

Eine Profi-Agentur begnügt sich nicht mit dem Hinweis „Dashboard einrichten“, sondern prüft die gesamte Werkzeug- und Wachen-Kette Ende-zu-Ende. Dabei wurden **fünf echte Defekte im Code** gefunden und dauerhaft behoben:

| # | Defekt im bisherigen Bestand | Konkrete Auswirkung im Betrieb | Schwere |
|---|---|---|---|
| **D1** | **Squash-Kollision in `scripts/worker_betrieb_wache.py` (`schema_fehler` vs. `wartet`):** `newsletter-worker/src/index.js` liefert bei gesetztem `TURNSTILE_SECRET` und leerem `TURNSTILE_SITEKEY` (= aktueller Repo-Stand) in `/healthz` `"turnstile": "wartet"`. `bewerte()` kannte `"wartet"`, aber `schema_fehler()` erlaubte nur `("aktiv", "inaktiv")`! | **Garantierter Folgefehler:** Unmittelbar nach dem ersten erfolgreichen Worker-Deploy wäre `sicherheits-wache.yml` jeden Tag weiter mit **Exit 2 (`Worker STOERUNG: Turnstile-Zustand ist unbekannt.`)** gescheitert. | **Kritisch** |
| **D2** | **TLS-Downgrade & unvollständige Regelprüfung in `scripts/cloudflare_edge_freigabe.py`:** `pruefen()` wies `Full (strict)` (`strict`) als Fehler ab (`soll 'full'`), und `--apply` **stufte eine `Full (strict)`-Zone aktiv auf `Full` herab** – direkter Verstoß gegen Runbook A1! Zudem prüfte `pruefen()` weder `enabled != false` (deaktivierte Regel im Dashboard) noch Host-Filter (`expression`) oder `operation == "set"`. | Sicherheits-Downgrade bei `--apply`; Falsch-Rot bei `Full (strict)`; Falsch-Grün bei deaktivierter Transform Rule im Dashboard. | **Kritisch** |
| **D3** | **Mehrdeutige 3-Wege-Vermutung bei Worker-`STOERUNG`:** `/healthz` trug keinen Build-Stempel, und `sicherheits-wache.yml` reichte `vars.KV_NAMESPACE_ID_ABO` nicht an die Wache weiter. | Betreiber sah täglich „Öffentliche Antwort, falscher Schlüssel **oder** veralteter Deploy“ statt der exakten Ursache (`KV_NAMESPACE_ID_ABO` leer → Deploy übersprungen). | **Hoch** |
| **D4** | **Schein-Grün bei manuellem `worker-deploy.yml` (`workflow_dispatch`) & fehlender Live-Nachweis nach Deploy:** Selbst bei ausdrücklich manuell gestartetem Deploy (`Run workflow` → `newsletter-worker`) lieferte `--plan` bei fehlender `KV_NAMESPACE_ID_ABO` `worker=[]` und **Exit 0 (grüner Haken!)**. Nach `wrangler deploy` wurde außerdem nie gegen `/healthz` geprüft, ob der neue Stand wirklich live antwortet. | Ein manuell angestoßener Deploy konnte komplett übersprungen werden und trotzdem grün melden; Routen-Drift blieb beim Deploy unentdeckt. | **Hoch** |
| **D5** | **Früher Abbruch in `sicherheits_nachweis.py` + fehlende B7-Automatik & CI-Lücken:** `live_pruefen()` brach nach `header: BEFUND` sofort ab, ohne `worker` gegen `pruefe_messung()` zu validieren oder `worker: STOERUNG` im Gesamturteil zu nennen. Für Runbook B7 fehlte ein idempotenter Befehl + Live-Drift-Hinweis, und `cloudflare_edge_freigabe` / `worker_deploy_vorbereiten` / `alert_resolve_gate` liefen in `sicherheits-wache.yml` nicht mit. | Ein kaputtes `worker-live.json` (`WACHE-FEHLER`) blieb hinter `header: BEFUND` unsichtbar; Datenschutz-Angleich B7 nach Proxy-Start war fehleranfällige Handarbeit. | **Mittel–Hoch** |

---

## 2. Dauerhafte technische Heilung (alle 5 Schichten)

### H1 — Schema-Vertrag für Turnstile `"wartet"` geschlossen (`scripts/worker_betrieb_wache.py`)
- `TURNSTILE_ZUSTAENDE = ("aktiv", "wartet", "inaktiv")` in `schema_fehler()` verankert.
- Neuer Ende-zu-Ende-Test über `worker.netz_pruefen()` **und** `sicherheits_nachweis.live_pruefen()` beweist: Ein frisch ausgerollter `newsletter-worker` im Übergangszustand `"wartet"` (Anmeldung offen, Secret bereit, Site-Key noch leer) besteht das Schema mit `Exit 0` / Klasse `OK` (samt lauter Warnung) und blockiert den Live-Nachweis nicht künstlich.

### H2 — Öffentlicher Build-Stempel (`bau`) + deterministische Deploy-/Zugangs-Diagnose
- **`newsletter-worker/src/index.js` + `wrangler.toml` + `test/index.test.js`:**
  - `BUILD = "ff-newsletter-2026-10-24"` steht in `wrangler.toml` und wird in `/healthz` öffentlich (`{ok, ts, bau}`) sowie authentifiziert ausgeliefert (verrät keinerlei Geheimnisse oder interne Struktur, 93/93 Node-Tests grün).
- **`scripts/worker_betrieb_wache.py` + `.github/workflows/sicherheits-wache.yml`:**
  - `sicherheits-wache.yml` übergibt die öffentliche Repository-Variable `KV_NAMESPACE_ID_ABO` an den Worker-Messschritt.
  - `diagnose_unvollstaendiges_bild()` trennt ohne zusätzliche Netzaufrufe und **ohne je Rohwerte aus der Antwort oder Umgebung in Berichte zu kopieren** exakt drei Fälle:
    1. `bau` fehlt + `KV_NAMESPACE_ID_ABO` leer/ungültig → **Übersprungener Deploy wegen fehlender Repository-Variable `KV_NAMESPACE_ID_ABO`** (inkl. exaktem GitHub-Pfad *Settings → Secrets and variables → Actions → Tab „Variables“*).
    2. `bau` fehlt oder weicht vom Repo-Soll ab + `KV_NAMESPACE_ID_ABO` gültig → **Veralteter Worker-Deploy live** → `worker-deploy.yml` starten.
    3. `bau == Repo-Soll`, aber Pflichtfelder fehlen → **Aktueller Worker läuft live, hat aber `x-ff-key` abgelehnt** → `NEWSLETTER_WORKER_EXPORT_KEY` mit `EXPORT_KEY` abgleichen.
  - `offline_pruefen()` überwacht dauerhaft, dass `BUILD` in `wrangler.toml` und `build_stempel` in `src/index.js` vorhanden bleiben.

### H3 — Härtung des Edge-Werkzeugs A1 + Ein-Befehl-Automatik B7 (`scripts/cloudflare_edge_freigabe.py`, `scripts/blog_header_gate.py`)
- **TLS-Downgrade-Sperre:** `ssl_bewerten()` akzeptiert `strict` (`Full (strict)`, bevorzugt) und `full`; lehnt `flexible` und `off` strikt ab. `ssl_ziel_bestimmen()` rührt ein bestehendes `strict` bei `--apply` **niemals** an (optional `--ssl strict` zum gezielten Hochstufen von `full` auf `strict`).
- **Vollständige Transform-Rule-Prüfung (`regel_abweichungen`):** Prüft `enabled != False`, `action == "rewrite"`, normalisierten Host-Filter (`AUSDRUCK` auf Hauptdomain + `www`), `operation == "set"` und exakte Werte aller 8 Kopfzeilen; `regel_koerper()` setzt explizit `"enabled": True`.
- **Kreuzbeweis im `--selftest`:** Beweist bei jedem Lauf maschinell, dass die aus `cloudflare/edge-schutz.md` gelesenen 8 Kopfzeilen `blog_header_gate.befunde_fuer()` mit **0 Fehlern und 0 Warnungen** bestehen.
- **Token- & Redirect-Schutz:** `_KeineWeiterleitung` verhindert jede Weitergabe des Bearer-Tokens über HTTP-3xx; Fehlermeldungen sind bereinigt.
- **Datenschutz B7 per Befehl (`npm run edge:b7` / `npm run edge:b7:apply`):** Stellt `content/datenschutz/index.md` nach Einschalten des Proxys idempotent auf Runbook B7 um (geprüft gegen `DatenschutzQuellvertrag` / `test_datenschutz_freigabe.py`). Solange der Proxy noch aus ist, bleibt `content/datenschutz/index.md` unangetastet wahrheitsgemäß; sobald live `cf-ray` aktiv ist, erinnert `blog_header_gate.py` automatisch an B7, falls noch der Vor-Proxy-Text steht.

### H4 — Fail-Closed für manuellen Worker-Deploy + Live-Beweis nach `wrangler deploy` (`scripts/worker_deploy_vorbereiten.py`, `.github/workflows/worker-deploy.yml`)
- **Manueller Aufruf (`workflow_dispatch`):** Fehlt für den gewählten Worker `KV_NAMESPACE_ID_ABO` bzw. `D1_DATABASE_ID`, bricht `Deploy planen` jetzt **fail-closed mit Exit 1 + `::error::` + Einrichtungs-Tabelle in `GITHUB_STEP_SUMMARY`** ab – kein still übersprungener grüner Handlauf mehr!
- **Push-Lauf (`push`):** Schreibt eine sichtbare `::warning::` + Step-Summary-Erklärung (warum nicht deployt wurde und dass die Variable unter *Tab „Variables“* statt *Secrets* liegen muss), ohne Duplikat-Issues neben WF-E813 zu erzeugen.
- **Post-Deploy-Beweis (`--nachweis`):** Direkt nach `wrangler deploy` prüft `worker-deploy.yml` live gegen `https://abos.franksfinanzcheck.de/healthz` (mit 4 Versuchen über 2 s / 5 s / 10 s für Edge-Propagation), dass der erwartete `BUILD`-Stempel aus `wrangler.toml` tatsächlich ausgeliefert wird.

### H5 — Vollständiger Live-Nachweis & lückenlose CI-Verdrahtung (`scripts/sicherheits_nachweis.py`, `.github/workflows/sicherheits-wache.yml`, `.github/workflows/alert-on-failure.yml`, `package.json`)
- `sicherheits_nachweis.live_pruefen()` validiert immer **beide** Messdateien (`header` und `worker`) vor der Statusentscheidung und nennt bei Mehrfach-Rot alle offenen Säulen gemeinsam (`header: BEFUND, worker: STOERUNG – kein vollständiger Live-Nachweis.`).
- `sicherheits-wache.yml` und `npm run test:sicherheit` führen jetzt sämtliche 8 Selbsttests und 8 Unit-Test-Module der Sicherheits- und Deploy-Kette gemeinsam aus.
- `alert-on-failure.yml` liefert für `sicherheit-live`, `sicherheit-worker` und `sicherheit-wache` den geschärften Handlungsweg inkl. `KV_NAMESPACE_ID_ABO`-, `edge:freigabe:apply`- und `edge:b7:apply`-Schritten (abgesichert in `alert_scoping_sim.mjs`).

---

## 3. Verifikation (alle Prüfungen lokal grün am 24.10.2026)

| Prüfung | Ergebnis |
|---|---|
| `npm run test:sicherheit` | ✅ **8 Selbsttest-Suiten + 196 Unit-Tests (163 + 33) + 4 Offline-Wachen grün** |
| `cd newsletter-worker && node --test` | ✅ **93/93 Tests grün** (inkl. neuem `healthz`-Build-Stempel-Vertrag) |
| `cd cloudflare/klick-zaehler && node --test test/worker.test.mjs` | ✅ **34/34 Tests grün** |
| `cd cloudflare/ki-assistent && node --test test/worker.test.mjs` | ✅ **17/17 Tests grün** |
| `python3 -m unittest scripts.tests.test_datenschutz_freigabe` | ✅ **6/6 Tests grün** |
| `python3 scripts/ki_transportweg.py --selftest` | ✅ **19 Proben grün** (T6-Transportvertrag unverletzt) |
| `python3 scripts/manifest_guard.py --selftest && python3 scripts/manifest_guard.py` | ✅ **19 Proben + 13 Manifeste grün** |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ **10 Fallgruppen, 60 Workflows grün** |
| Workflow-YAML (`sicherheits-wache.yml`, `worker-deploy.yml`, `alert-on-failure.yml`) | ✅ `yaml.safe_load` + echte `bash -e -o pipefail` Shell-Regressionen grün |

---

## 4. Bewusste Grenzen (Ehrlichkeits- & Sicherheits-Doktrin)

- **Kein künstliches Grün und kein manuelles Schließen von #815:** In der Sandbox existieren weder produktive Cloudflare-Tokens noch produktive Worker-Secrets. Die Wache **soll** rot bleiben, bis Edge-Proxy/Header (A1) und Worker-Deploy (D2) live aktiv sind; der Auto-Close (`alert-on-failure.yml` + `sicherheits_nachweis.py --abschluss` + `alert_resolve_gate.py`) schließt #815 danach vollautomatisch beim ersten echten grünen Live-Lauf.
- **`content/datenschutz/index.md` noch nicht vorab umgeschaltet:** Solange der Cloudflare-Proxy live noch aus ist, wäre die Behauptung eines aktiven Cloudflare-CDNs unzutreffend. Dafür steht `npm run edge:b7:apply` bereit – ein einziger idempotenter Befehl direkt nach `npm run edge:freigabe:apply`.

---

## 5. Einmalige Inhaber-Checkliste nach dem Merge (~10 Minuten bis zum automatischen Abschluss von #815)

Nach dem Merge dieses Branches nach `main`:

1. **Cloudflare Edge A1 + Datenschutz B7 herstellen (F-01):**
   ```bash
   CLOUDFLARE_API_TOKEN="<Zonen-Token mit DNS:Edit, Settings:Edit, Transform Rules:Edit>" \
     npm run edge:freigabe:apply
   npm run edge:b7:apply
   git add content/datenschutz/index.md && git commit -m "docs(datenschutz): Cloudflare-Proxy B7 nach Freigabe aktiviert" && git push origin main
   ```
2. **GitHub Repository-Variable für den Newsletter-Worker eintragen (Ursache des übersprungenen Deploys):**
   - GitHub → **Settings → Secrets and variables → Actions → Tab „Variables“ → New repository variable**
   - Name: `KV_NAMESPACE_ID_ABO` · Wert: die vorhandene 32-stellige Hex-ID des produktiven `ABO`-KV-Namespaces aus Cloudflare (ausdrücklich unter **Variables**, nicht unter *Secrets*).
   - Prüfen, dass im Environment `cloudflare-produktion` `CF_WORKERS_DEPLOY_TOKEN` und `CLOUDFLARE_ACCOUNT_ID` hinterlegt sind sowie `NEWSLETTER_WORKER_EXPORT_KEY` (= Worker `EXPORT_KEY`) und `NEWSLETTER_WORKER_WRITE_KEY` (= Worker `EXPORT_KEY_WRITE`, verschieden vom Leseschlüssel) in den Repository-Secrets stimmen (Runbook A4/D2).
3. **Newsletter-Worker von `main` ausrollen (mit automatischem `/healthz`-Build-Nachweis):**
   ```bash
   gh workflow run worker-deploy.yml --ref main -f worker=newsletter-worker
   ```
   *(Im Environment `cloudflare-produktion` freigeben → Schritt prüft live `bau == ff-newsletter-2026-10-24`.)*
4. **Live-Abnahme starten – schließt #815 automatisch:**
   ```bash
   gh workflow run sicherheits-wache.yml --ref main
   ```
   Sobald `Live-Messung (täglich und auf Zuruf)` inklusive `Live-Nachweis abschließen` grün durchläuft, schließt der `resolve`-Job des Fehler-Alertings Vorgang **#815** automatisch mit echtem Live-Beweis.
