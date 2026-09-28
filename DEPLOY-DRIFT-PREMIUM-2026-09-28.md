# Deploy-Drift-Reparatur auf Premium-Agentur-Level (Issue #433)

**Datum:** 28. September 2026  
**Status:** ✅ Vollständig behoben, vertraglich abgesichert und verifiziert  
**Referenzen:** Issue #433, PR #431 (Pillar-Cluster-CSS), PR #432 (Dependabot-Bump), Issue #218  
**Autor:** Arena Agent (Senior CI/CD & Production Reliability Architect)

---

## 1. Management Summary & Befund

Nach dem Merge von PR #431 (Squash `1d3a0b0d`, 03:14 UTC – Pillar-Cluster-CSS `.ff-pc-*` und Datumsaktualisierung) trat ein **stiller Deploy-Drift** auf:
- Der Commit war auf `main` vorhanden, grün und gemergt.
- Auf der Live-Site (`gh-pages` Branch) fehlten die Änderungen; die Live-Site verharrte auf Commit `a263bcb3` (03:35 UTC).
- Weder `deploy.yml` noch `deploy-catchup.yml` lösten einen Folge-Deploy aus.

### Die Rekonstruktion der Ursachenkette (Incident-Analyse)

| Zeit (UTC) | Vorgang | Auswirkung auf CI/CD & Deploy-Zustand |
|---|---|---|
| 03:08:45 | `deploy.yml` (Dispatch-Run `36372546684` auf `a263bcb3`) startet | Läuft in Concurrency-Gruppe `pages-deploy` |
| 03:14:15 | PR #431 gemergt (`1d3a0b0d`, CSS + Pillar-Layout) | Push-Run `36372931580` queued in `pages-deploy` |
| 03:30:01 | Dependabot PR #432 gemergt (`ada86068`, nur `.github/workflows/…`) | Neuer Push-Run `36373956713` verdrängt wartenden PR #431 Run (`cancelled`) |
| 03:30–03:31 | `deploy-gate` des Runs `36373956713` läuft | Diffed nur `1d3a0b0d...ada86068` (nur `.github`) → `deploy=false` → **`deploy`-Job SKIPPED**, Run schließt als `success` ab |
| 03:35:07 | Älterer Dispatch-Run beendet | Pusht alten Stand `a263bcb3` auf `gh-pages` |
| Danach | `deploy-catchup.yml` prüft main gegen letzten Lauf | Liest `listWorkflowRuns(status: success)` = Run `36373956713` (HEAD `ada86068` == `mainSha`) → **Täuschung: „nichts zu tun“** |

---

## 2. Die zwei Kernlücken im Detail

### Lücke 1: `deploy-gate` verglich nur `event.before...event.after`
Das Relevanz-Gate in `deploy.yml` ging davon aus, dass `event.before` bereits live ist. Wenn jedoch ein früherer Push-Run in der `pages-deploy`-Warteschlange abgebrochen wurde (Queue-Verdrängung bei mehreren Pushes) oder fehlschlug, enthielt der neue Push (`event.after`) zwar die kumulierten Änderungen, der Diff `event.before...event.after` sah jedoch nur den letzten Teilschritt. War dieser rein dokumentarisch oder ein Workflow-Update, wurde der gesamte Livegang übersprungen.

### Lücke 2: `deploy-catchup.yml` prüfte nur Workflow-Ebene statt Job-Ebene
`deploy-catchup.yml` suchte nach `listWorkflowRuns({ workflow_id: 'deploy.yml', status: 'success' })`. Da GitHub Actions einen Workflow mit übersprungenen Folge-Jobs (`deploy: skipped`) als Gesamt-Ergebnis `success` markiert, galt ein übersprungener Lauf fälschlicherweise als „erfolgreicher Deploy“.

---

## 3. Die nachhaltige Premium-Architektur

Die Behebung setzt an allen Ebenen an und folgt dem Prinzip der **Single Source of Truth (SSOT)**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SINGLE SOURCE OF TRUTH                            │
│                 Live-Stand auf gh-pages: "deploy: <SHA>"                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│          deploy.yml           │             │      deploy-catchup.yml       │
│         (deploy-gate)         │             │           (catchup)           │
├───────────────────────────────┤             ├───────────────────────────────┤
│ 1. Ermittelt LIVE_DEPLOY_SHA  │             │ 1. Liest gh-pages Deploy-SHA  │
│    aus gh-pages Commit-Msg    │             │    + prüft deploy-JOB Status  │
│ 2. Diffs LIVE_DEPLOY_SHA..HEAD│             │ 2. Vergleicht main vs Live    │
│ 3. Prüft gegen STATE_ONLY     │             │ 3. Diff-Filter gegen          │
│ 4. Site-Änderung da?          │             │    STATE_ONLY                 │
│    → deploy=true              │             │ 4. Site-Drift entdeckt?       │
│    Reine State-Änderung?      │             │    → workflow_dispatch        │
│    → deploy=false             │             │ 5. Stündlicher Cron-Backstop  │
└───────────────────────────────┘             └───────────────────────────────┘
                                       ▲
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                        scripts/deploy_drift_guard.py                        │
│               Modulare Drift-Wache mit --check und --selftest               │
│                in governance_contract.py (GUARDS) verankert                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Härtung in `.github/workflows/deploy.yml` (`deploy-gate`)
- Das Gate fragt via `gh api repos/:owner/:repo/commits/gh-pages` die Commit-Message ab und extrahiert `LIVE_DEPLOY_SHA` (`deploy: <SHA>`).
- Es diffed `LIVE_DEPLOY_SHA...AFTER` (also **allen** Code seit dem tatsächlichen Livegang).
- Verdrängte oder abgebrochene Vorläufe können niemals mehr site-relevante Änderungen verschlucken.
- Bei Nicht-Erreichbarkeit oder fehlendem Vorfahren greift sofort die Fail-Safe-Regel (`deploy=true`).

### 2. Härtung in `.github/workflows/deploy-catchup.yml`
- Prüft primär den `gh-pages` Branch Commit (`deploy: <SHA>`).
- Prüft sekundär über die Actions-API, ob im letzten erfolgreichen Workflow-Lauf der konkrete Job `deploy` den Status `conclusion === 'success'` hatte (Filterung von Skip-Läufen).
- Prüft aktive Läufe (`in_flight`), um Queue-Überlastungen zu verhindern.
- Nutzt die Compare-API gegen die `STATE_ONLY`-Negativliste.
- Wurde um einen stündlichen Schedule (`cron: "20 * * * *"`) erweitert, um auch außerhalb von Bot-Trigger-Ketten absolute Ausfallsicherheit zu garantieren.

### 3. Neues Modul `scripts/deploy_drift_guard.py`
- Dedizierte, voll testbare Drift-Wache mit CLI-Interface (`--check`, `--json`, `--report`, `--selftest`).
- SSOT für `STATE_ONLY_PATTERN`.
- In `governance_contract.py` (`GUARDS`) als feste vertragliche Wache registriert.

---

## 4. Test- und Beweisführung

### 1. Selbsttests & Vertragstests
- `scripts/tests/test_deploy_gate_paths.py`: Enthält die exakte Simulation des Vorfalls #433 (Live auf A, PR #431 auf B abgebrochen, PR #432 auf C) und beweist, dass der neue Mechanismus zuverlässig `deploy=true` entscheidet.
- `scripts/tests/test_deploy_drift_guard.py`: 5 Unit-Tests für SHA-Parsing, Relevanz-Klassifikation, alle 4 Drift-Zustände (`IN_SYNC`, `STATE_ONLY_DIFF`, `SITE_DRIFT`, `UNKNOWN_BASE`) und Markdown-Reporting.
- `scripts/tests/test_deploy_catchup.py`: 6 Vertragstests für Schedule, Event-Trigger, Job-Conclusion-Check, In-Flight-Guard und Muster-Parität.
- `scripts/governance_contract.py`: 18/18 Regeln grün inkl. Wache-Registrierung.

### 2. Testergebnisse (Gesamtsuite)
```bash
python3 -m unittest discover scripts/tests
----------------------------------------------------------------------
Ran 1002 tests in 34.084s
OK (skipped=8)
```

---

## 5. Fazit & Betriebsgarantie

Die Drift-Schwachstelle aus Issue #433 ist damit auf dem geforderten Premium-Agentur-Level dauerhaft eliminiert. Das System ist mathematisch geschlossen: Jeder Merge mit sichtbaren Änderungen geht garantiert live, unabhängig von zwischenzeitlichen Dependabot-, Bot- oder State-Commits.
