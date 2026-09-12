# Premium-Audit & Säuberung – FranksFinanzcheck-Blog

**Stand:** 12.09.2026 · **Umfang:** gesamtes Repository (45 Workflows, 187+ Python-Skripte, 50 Content-Verzeichnisse, 129 State-Dateien) · **Methode:** statische Analyse, Voll-Builds, Voll-Test-Suites, Gate-Läufe im Check-Modus, Einzelfall-Rekonstruktion jedes Befunds

---

## 1 · Executive Summary

| # | Befund | Schwere | Status |
|---|--------|---------|--------|
| F1 | Deploy-Queue-Druck: jeder State-Push löste vollen Deploy aus (Build + bis zu 20 Min. TTS) | hoch | ✅ behoben |
| F2 | 4 nackte `git push` ohne Rebase-Schutz (Commit-Verlust bei parallelen Bots) | hoch | ✅ behoben |
| F3 | `git add` auf unversionierte Report-Pfade bricht die ganze Staging-Phase ab | hoch | ✅ behoben |
| F4 | Duplikat-Wache gebaut, aber in **keinem** Workflow verdrahtet | hoch | ✅ behoben + 6 korrupte Artikel geheilt |
| F5 | Duplikat-Wache: erste Kopie des Korruptions-Musters nie heilbar (Fingerprint-Bug) + Index-Drift-Bug im Fixer | hoch | ✅ behoben (Selftest 4→7 Fälle) |
| F6 | D3/D4 (Cross-Artikel-Duplikate) im Docstring versprochen, nie implementiert | mittel | ✅ implementiert (report-only) |
| F7 | 48 Root-Reports + Scorecard + 4 Dot-Caches versioniert, obwohl gitignored | mittel | ✅ ent-versioniert (3 Watchdog-Eingaben bleiben) |
| F8 | 32 One-Shot-Dokumente + 5 Anleitungen im Root | mittel | ✅ nach docs/archiv/ bzw. docs/ |
| F9 | Watchdog-Affiliate-Check: stiller Wache-Ausfall unsichtbar | mittel | ✅ State-first mit Frische-Check |
| F10 | Link-Checker: 266 Phantom-Funde (onerror-JS als Link geparst) | mittel | ✅ behoben → 0/2386 defekt |
| F11 | RSS: doppelte pin_description-Öffnung + F5-Heuristik zu stur | niedrig | ✅ diversifiziert → Feed F-OK |
| F12 | Unit-Test scheiterte in jedem vollen Clone (harte Schwelle 15 Spuren) | niedrig | ✅ relative Regression → grün |
| F13 | Einmaliger Migrations-Workflow an abgelaufenem Branch | niedrig | ✅ entfernt |
| F14 | E2E-Suite (Playwright) in Sandbox nicht ausführbar (Browser-CDN blockiert) | Info | 📋 nur in CI (PR + Di 05:00 UTC) |

---

## 2 · Interferenz-Analyse: wie sich die Automationen gegenseitig behindert haben

### 2.1 Deploy-Queue-Druck (die größte Selbstbehinderung)
`deploy.yml` hatte **keinen** Pfade-Filter. JEDER Push auf `main` löste Gates + Hugo-Build + TTS-Vertonung (20-Min-Budget, 120-Min-Schritt-Timeout) + gh-pages-Push aus. social-autopilot committet pro Lauf (alle 2 h, 8x/Tag) `data/social/` + Pin-Bilder; dazu Newsletter, Fristen, Mastodon, Status-Commits. Ergebnis: ~8 Deploys/Tag **ohne** Content-Änderung, die die `pages-deploy`-Warteschlange (Befund Issue #218: sechs Stunden Blockade) verstopften und echte Artikel-Deploys verdrängten.

**Repair:** neues Leicht-Gate-Job `deploy-gate` vor dem Deploy (GitHub Compare-API, kein Checkout). Negativliste-Logik: nur bekannte Zustands-/Doku-Pfade sind deploy-irrelevant (`data/social/`, `data/research/`, `data/audit/`, `data/*_state.json`, `data/*_history.jsonl`, `static/images/social/`, `docs/`, `scripts/`, `.github/`, Root-`.md`, …); **alles Neue ist per Default relevant** – ein zukünftiger State-Pfad kann keinen Livegang stoppen. Fehlsicherheit: Erst-Push, API-Fehler, Force-Push, manueller Lauf = immer Deploy. Die Gate-Abdeckung geht nicht verloren: `blog-health-daily` (täglich 07:45 MESZ) fährt dieselbe Heilkette, die Content-Workflows prüfen vor jedem Slot.

### 2.2 Nackte Pushes (Non-Fast-Forward = stummer Commit-Verlust)
Vier Workflows pushten ohne Rebase-Runde: `ki-redaktion.yml`, `agent-reach-research.yml`, `produktions-wache.yml`, `apply-verstaendnis-patches.yml`. Bei parallelen Bots (content-bot-Gruppe, Watchdogs, Status-Bots) droht `non-fast-forward`; zwei Stellen schluckten den Fehler per `|| echo warning` – der Commit ging **stumm** verloren. **Repair:** alle vier auf das zentrale `scripts/git_sync.sh --push-only` (3 Runden × Fetch mit Backoff, Rebase-Auflösung, Rettungsanker-Direktpush, präzise Fehlerklassifikation; Auth-Fehler ohne Retry). `apply-verstaendnis-patches.yml` (einmaliger Migrations-Workflow, eigener Kopf: „Danach löschen, optional", Aufgabe 01.09.2026 erledigt, hing an abgelaufenem Arena-Branch + GH_PAT) entfernt.

### 2.3 git add auf unversionierte Pfade (schwerster Interferenzfall)
`git add` auf einen ignorierten, **ungetrackten** Pfad bricht mit Exit 1 ab – und nimmt **alle Pfade desselben Befehls** mit (auch `content/`). Sechs Stellen ohne Guard: `content-engine-v2.yml` (Kadenz-Heilungs-Commit hätte wellend Content-Änderungen verloren), `affiliate-health.yml`, `fristen-check-*.yml`, `layout-ai.yml`, `mastodon-seo.yml`, `seo-weekly.yml`. Dazu 15 gemischte Staging-Listen mit Report-Pfaden (teilweise `|| true`-guardiert, dann aber tote Staging-Versuche). **Repair:** alle ungeguardeten Zeilen gefixt (funktionale Pfade bleiben, Reports raus), Report-only-Schritte entfallen (layout-ai, seo-weekly, bot-watchdog, engine-Phase-4), gemischte Listen auf das Repo-eigene pro-Pfad-Muster (Bugfix 14.08.2026) umgestellt.

### 2.4 `[skip ci]`-Menschen in Commit-Messages
`fristen-check`, `mastodon-manual-post`, `produktions-wache` signierten Status-Commits mit `[skip ci]` – **dekorativ**, weil `deploy.yml` auf jeden Push triggert. Seit dem Relevanz-Gate (2.1) werden solche Commits ohnehin nicht mehr deployed; die Message bleibt als Dokumentation bestehen.

### 2.5 Seriengruppen (konkurrenzfreies Verhalten, dokumentiert)
`content-bot`-Gruppe (engine + reserve + kadenz-endkontrolle, `cancel-in-progress: false`): kadenz-endkontrolle (10:35/16:35/19:35/21:35) wartet auf die Engine (Job-Timeout 90 Min.) – gewollt (Endkontrolle prüft, was der Slot geleistet hat), Endschiebungen möglich, aber abgedeckt durch die hart gedeckelte Deploy-Laufzeit (150 Min.). `willkommenstext-refresh` triggert nur auf zwei Pfade – kein Push-Loop. `e2e` (`e2e-${ref}`, cancel true) und Watchdogs laufen in eigenen Gruppen.

### 2.6 Breite Staging-Fläche (`git add -A`)
Elf Workflows stagen breit (seo-weekly, blog-health, pinterest-watchdog, repin-weekly, social-ai, content-engine, content-reserve, kadenz-endkontrolle, update-quarterly, ki-redaktion, gate-heilung in deploy.yml). Durch das Ent-versionieren aller Root-Reports (F7) + die `.gitignore`-Abdeckung ist `git add -A` jetzt deterministisch: es kann nur noch versionierte Content-/State-Änderungen aufnehmen.

---

## 3 · Content-Reparaturen

### 3.1 Intro-Duplikate in 6 Alt-Artikeln (24 Absätze)
Artikel 08-10 bis 08-24 enthielten je 2–5x eingefügte Kopien der Einleitung (Muster: `---` + Intro + Absatz, nach dem Transparenz-Block, vor der Schnell-Tipp-Box) – vermutlich eingefügt von einer frühen Kurzfassungs-/Heiler-Generation, deren Restkopien die damaligen Reparaturläufe (09-06…09-11) nicht erfassten. Rein löschende Reparatur, Struktur + CTA-Box + alle Links intakt (Differenz: nur 63 gelöschte Zeilen, keine anderen Änderungen).

### 3.2 Duplikat-Wache grundgesichert (`scripts/duplikat_guard.py`)
- **Fingerprint:** angeklebte `---`-Trennlinie läuft nicht mehr in den SHA-256/Near-Vergleich – davor war die **erste** Kopie des Musters nie heilbar (D1-Mismatch, D2-Präfix `---` vs. Text verfehlt sie ebenfalls). Selbst im `--fix`-Modus blieb sie für immer.
- **Index-Drift im Fixer:** der D2-Near-Fix adressierte `cand`-Indizes (nur Blöcke ≥ 120 Zeichen) statt `keep`-Indizes – bei kurzen Zwischensäetzen hätte der **falsche** Absatz gelöscht werden können. Behoben + als eingefrorener Selftest-Fall gesichert.
- **D3/D4 implementiert:** Cross-Artikel-Duplikate (exakt + near) wurden im Docstring versprochen, der `articles`-Parameter war tot. Jetzt aktiv, **report-only** (Sicherheit: Cross-Funde werden nie auto-gefixed), im `--new-only`-Modus zählt nur, was heutige Artikel berührt.
- **Boilerplate-Whitelist:** In-Text-CTA (`affiliate_marketer.py`) + Fazit-Formel (`fazit_schmiede.py`) – Haus-Templates, die abschriftlich in 10–24 Artikeln stehen; ohne Whitelist blendete jede Cross-Messung sie als Duplikat.
- **Verdrahtung:** `blog-health-daily` (täglich `--fix` im Bestand) + `content-engine-v2` (`--new-only --fix` vor dem Commit). Selftest: 4 → 7 Fälle.
- **Ergebnis:** 49 Artikel, D1…D6 alle 0.

### 3.3 RSS-Feed (Quelle des Pinterest-Auto-Publish)
zwei Gas-Artikel (08-24, 08-14) teilten sich den ersten Satz der `pin_description` – F5 (60-Präfix) flaggte sie. (a) `pin_description` des gasrechnung-Artikels diversifiziert (eigene Stoßrichtung, 304 Zeichen im Pin-Korridor 220–480). (b) F5-Heuristik: Ganztexthöhe (exakt oder Ratio ≥ 0.9) statt Präfix; Bild-Prüfung exakt. **Ergebnis:** Feed F-OK (31 Items, Kadenz-konform, Cover vorhanden, keine Duplikate), Spam-Selftest (22 Fälle) bestanden.

### 3.4 Interne Links
`check_internal_links.sh` meldete 266 defekte Cover-Links – alle Phantom-Funde aus dem `onerror`-Fallback des Cover-Partials (AVIF→JPG; `this.src='\/images\/…'` ist JS in einem Attribut, kein Markup-Link). onerror-Attribute werden vor der Extraktion entfernt, Backslash-Werte zusätzlich übersprungen. **Ergebnis:** 2386 interne Links, **0 defekt** (alle Bilder existieren im Build).

---

## 4 · Repository-Reinigung

### 4.1 Ent-versioniert (48 Report-/Scorecard-Dateien + 4 Dot-Caches)
Alle Root `*-REPORT.md`/`*-STATUS.md` + `EDITORIAL-SCORECARD.md` (neu in `.gitignore`): die Workflows schreiben sie weiterhin (sichtbar in den Lauf-Logs), sie landen aber nicht mehr im Git – das spart ~8 Pushes/Tag und nimmt der Bot-Flotte die Push-Rennen. **Bewusst versioniert bleiben (3):** `PRODUKTIONS-STATUS.md`, `AFFILIATE-INTEGRITY-REPORT.md`, `PINTEREST-REPORT.md` – `bot_watchdog.py` liest sie direkt aus dem frischen CI-Checkout (mtime-/Inhaltsprüfung); `report_hygiene.py --check` klassifiziert alle drei als geschützte Klasse (ci-dashboard/doku) und rührt sie nicht an.

Dot-Caches: `.grammar_report.json`, `.spellcheck_report.json`, `.keyword_suggestions.json`, `.affiliate_report.json` ent-versioniert (jedes Skript degradet graceful ohne Cache, verifiziert). **Ausnahme:** `.indexnow_submitted.json` bleibt versioniert – es ist der IndexNow-Dedup-State **über** CI-Läufe hinweg (sonst würden alle ~50 URLs bei jedem Lauf neu gepusht).

### 4.2 Gelöscht (Index + Platte, History bleibt)
- `patches/` (18 abgearbeitete Patches, `.gitignore`: „erledigt, nicht mehr benötigt")
- `static/audio/` (1 MP3 + 1 Time-Map – „Handwerksstück aus der Anfangszeit"; Referenzfrei verifiziert: Generator + Toolbar arbeiten ausschließlich über `/audio/articles/`, der von `deploy.yml` generiert wird)
- `strom-sparen-pinterest.mp4` (2,6 MB Upload-Rest, `*.mp4`-Pattern)

### 4.3 Reorganisation
- **32 One-Shot-Dokumente** (REPARATUR-Logs 09-03…09-11, PREMIUM-OPTIMIERUNG 09-01/02, GOVERNANCE-Dokus, BEFUND/AKTIONSPLAN, LESEHILFEN-STUDIO, VORLESEN-Dokus, KI-REDAKTION, AGC-AUTOPILOT, …) → `docs/archiv/` (git mv, Inhalt erhalten).
- **5 ANLEITUNG-Dateien** → `docs/` (Konsolidierung mit den dort bereits liegenden 8; alle Skript-Fehlermeldungen, Workflow-Kommentare, README-Links, CLAUDE.md und docs-Verweise auf die `docs/`-Pfade aktualisiert).
- `docs/README.md` neu geschrieben (aktueller Doku-Index inkl. Begründung der Ausnahme-Dateien).
- **Null echte Markdown-Links** auf die ent-versionierten Reports in README/docs (Verifikation) – keine tote Referenz.

### 4.4 Watchdog-Härtung
`check_affiliate_integrity` liest jetzt **state-first**: `.affiliate_integrity_state.json` (exit_code + content_problems + `generated_at`) mit Frische-Check – State > 30 h (täglicher Lauf 06:00 MESZ) = harter Befund. Damit ist ein stiller Wache-Ausfall sichtbar, der im reinen Report-Marker-Scan unsichtbar war. Der Report-Scan bleibt Fallback. Die beiden Eingaben (State + Report) werden in `affiliate-integrity-daily.yml` weiterhin versioniert (beide getrackt → `git add` trotz Ignore-Muster sicher).

---

## 5 · Verifikation (Nachweise)

| Prüfung | Ergebnis |
|---|---|
| Hugo-Build 0.164.0+extended (`--minify`) | ✅ 167 Pages, 24 Paginator, 121 Aliases, 0 Fehler/Warnungen (~1,2 s) |
| Unit-Tests (`pytest scripts/tests/`) | ✅ 174 passed, 0 failed (vorher: 172/1 fail), 312 Subtests |
| py_compile (alle 187+ Skripte) | ✅ alle OK |
| YAML-Validität (alle 45 Workflows) | ✅ 0 Fehler |
| Duplikat-Audit (49 Artikel, D1–D6) | ✅ alle 0 |
| report_hygiene --check | ✅ exit 0 (Root sortenrein) |
| Spam-Gate (blog + feed + csv) | ✅ Feed F-OK; Blog/CSV ohne hard Findings |
| Publish-Gate, Themenwelten (Quell- + Public-Gate) | ✅ grün |
| FM-Grenzen-Gate (62 Dateien), Anker-Wache | ✅ grün |
| Interne Links (2386) | ✅ 0 defekt |
| Bot-Watchdog Selftest + Check | ✅ (Sandbox-Exceptions: kein Internet/gh/Pinterest-Auth – in CI regulär) |
| E2E (Playwright) | 📋 nicht in Sandbox ausführbar (Chrome-CDN blockiert) – läuft in CI (PR + Di 05:00 UTC) |

**Commits:** (1) `fix(content)` Duplikate + Wache, (2) `refactor(automation+root)` Entlastung/Zentralisierung/Sauberkeit, (3) `fix(quality)` RSS/Link-Checker/Pin.

---

## 6 · Restrisiken & Empfehlungen

1. **E2E-Nachweis:** Die Playwright-Suite (SEO/A11y/Affiliate-Guard, Design-Metriken) läuft nur in CI. Empfehlung: nach dem Push auf `main` den E2E-Lauf (PR oder Tuesday-Slot) einmal abwarten, bevor die Säuberung als „live verifiziert" gilt.
2. **Fazit-Formel (`fazit_schmiede.py`):** die templatierte Fazit-Öffnung („Sich gezielt mit dem Thema **X** zu beschäftigen …") steht in ~10 Artikeln. Sie ist als Haus-Template gewollt (deshalb ge-whitelistet), aber aus Sicht von Googles Scaled-Content-Erkennung der fragilste Punkt des Bestands. Empfehlung: die Wache auf 5–6 varierte Formeln ausweiten.
3. **Pinterest-Token:** der lokale Check meldete Token-401 (Sandbox ohne Auth-Kontext) – in CI prüft die Token-Wache (continuous refresh) den echten Zustand; bei anhaltendem roten Stand: `docs/PINTEREST-TOKEN-RUNBOOK.md` (Actions → Pinterest-Token-Wache → Run workflow).
4. **Cadence-Automatik:** das manuelle Kadenz-Gate (`publish.py`, Mo/Mi/Fr, ≤3/Tag) bleibt bestehen; die automatische Engine wird täglich von `cadence_guard --fix` gegengeprüft (inkl. Zwischen-Slots durch blog-health-daily).
5. **Monitoring der neuen Gate-Logik:** `deploy-gate` loggt bei jedem Sprung „Nur Zustands-/Doku-Änderungen". Für zwei Wochen darauf achten, dass keine Content-Pushes fälschlich übersprungen werden (Fehlsicherheit deckt API-Fehler, nicht Logikfehler ab).

*Vorbereitet als Teil des Premium-Audit-Auftrags 12.09.2026 („Blog prüfen, säubern, sämtliche Fehler beseitigen, Blogautomatik gegenseitige Behindern prüfen").*
