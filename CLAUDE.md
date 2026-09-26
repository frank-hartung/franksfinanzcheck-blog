# CLAUDE.md – Leitfaden für KI-Agenten in diesem Repository

> Rollout 12.09.2026 (Design-Skills-Premium-Integration).
> Diese Datei lesen Agenten (Claude Code & kompatible) automatisch beim Start.

## Das Repository in einem Satz

Hugo-Blog **franksfinanzcheck.de** (PaperMod, stark angepasst) mit einem
vollautomatisierten Redaktions-/Qualitäts-Betrieb: 45+ GitHub-Workflows,
Python-Gates in `scripts/`, ausführliche Zustands-Reports im Root.
**Nichts hier ist eine Spielwiese – main deployt auf Produktion.**

## Verhalten beim UI-/Design-Arbeiten (PFLICHT)

1. **Skills nutzen** – installiert in `.claude/skills/`:
   | Skill | Wann |
   |---|---|
   | `impeccable` | Designen/Polierten/Kritisieren/Auditieren von UI (liest PRODUCT.md + DESIGN.md zuerst!) |
   | `web-design-guidelines` (Vercel) | UI-Code-Review gegen Web Interface Guidelines |
   | `frontend-design` (Anthropic) | Neue Oberflächen mit eigener visueller Identität |
   | `design-taste-frontend` (taste-skill) | Anti-Slop-Disziplin bei Frontend-Arbeiten |
   | `webapp-testing` (Anthropic) | Browser-Interaktion/Test mit Playwright |
   | `agent-reach` | **Jede** Internet-Recherche/Suche/URL-Lektüre (Twitter, Reddit, YouTube, GitHub, RSS, Web …) – auch bei deutschen Aufträgen („recherchiere …", „suche …", „was sagt man über …") |
   Aktualisierung: `npx skills update` (Quellen in `skills-lock.json`).
2. **PRODUCT.md und DESIGN.md lesen, bevor eine Farbe geändert wird.**
   Sie enthalten die Marken-Tokens, Anti-References und harten Gates.
   **Layout-Umbauten gehören in eine Variante, nicht in die Basis**
   (seit 26.09.2026): `assets/css/varianten/<id>.css` + Eintrag in
   `data/design/varianten.yaml`, dann messen und einem Menschen zur
   Freigabe vorlegen. Direkt in `assets/css/extended/` zu schreiben,
   heißt: ohne Messung und ohne Unterschrift deployen.
   Runbook: `docs/ANLEITUNG-DESIGN-VARIANTEN.md`.
3. **Dark Mode mitdenken**: `defaultTheme: auto` → jede Farbe braucht eine
   `:root[data-theme="dark"]`-Variante. Kontraste messen:
   `node e2e/design-metrics.mjs` (liefert hell+dunkel als JSON).
4. **Keine Inline-Farben in Templates** – Klassen + CSS-Dateien
   (Vorbild: `.ff-pc-*` in `layouts/pillar/single.html`).
5. **Figma/Relume nur über den Handoff-Vertrag** – externe Entwürfe müssen
   `data/design/handoff.yaml` und die generierten Artefakte unter
   `design/handoff/` verwenden. Generierte Dateien nie von Hand ändern;
   `python3 scripts/design_handoff.py --check` prüft Marken- und Exportdrift.
   Runbook: `docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md`.

## Test- und Verifikations-Pipeline

```bash
hugo --destination public            # Build (Hugo Extended 0.164 nötig)
npm run test:e2e                     # Build + 25 Playwright-Tests (Desktop+Mobile)
npx playwright test                  # nur Tests (nutzt vorhandenes public/)
node e2e/design-metrics.mjs          # messbarer Design-Audit (stdout = JSON)
node e2e/design-shots.mjs            # Screenshots für Design-Reviews → shots/
python3 scripts/layout_audit.py      # statisches Layout-Gate (Links, Covers, Alt-Texte, DOM-Budget, Chunker-Vertrag)
python3 scripts/dom_audit.py --top 15 # DOM-Budget jeder Seite (Kinder/Head/Tiefe/Elemente, browser-treu ohne Chrome)
node scripts/layout_browser_check.js # Browser-Audit (Puppeteer; braucht CHROME_PATH) – siehe docs/LAYOUT-AUTOMATISIERUNG.md
python3 -m unittest discover -s scripts/tests        # Unit-Tests (u. a. Alarm-Routing)
python3 scripts/alert_router.py --selftest           # Routing-Regeln (Besitz/Kadenz/Schließpfad)

# Design-Varianten-Werkbank (26.09.2026) – Details: docs/ANLEITUNG-DESIGN-VARIANTEN.md
python3 scripts/design_variant_gate.py               # Marke + Messvertrag + Freigabe
python3 scripts/design_variant_gate.py --produktionswache   # läuft im Deploy VOR dem Build
python3 scripts/design_variant_lab.py --lauf <id>    # baut Basis+Variante, misst statisch
node e2e/variant-metrics.mjs --variante <id>         # Browser-Messung + Lighthouse
python3 scripts/design_reach_briefing.py             # Agent-Reach-Signale → Hypothesen
python3 scripts/design_handoff.py                     # Figma-/Relume-Artefakte erzeugen
python3 scripts/design_handoff.py --check             # SSOT-/Exportdrift blockieren
```

E2E-Architektur (Details in `e2e/`-Datei-Köpfen): zero-dependency
Static-Server (`e2e/server.mjs`), hermetische Produktions-URL-Umleitung
(`e2e/fixtures.mjs`), Browser-Resolver mit CDN-Fallback (`e2e/browser.mjs`).
Mobile-Projekt: `browserName: 'chromium'` explizit setzen – sonst startet
Playwright heimlich WebKit (device-`defaultBrowserType`-Falle).

## CI

- `.github/workflows/e2e.yml` – Playwright bei PRs auf main + dienstags
  07:00 MESZ; HTML-Report als Artifact.
- `.github/workflows/integrity-lock.yml` – PR-Gate, Pflicht-Check
  **`Integritäts-Siegel`**. Der Job-Anzeigename ist ein Vertrag mit dem
  Ruleset (Governance-Regel C18, Konstante `PFLICHT_CHECK_NAME`): **nie
  umbenennen, keinen `paths`-Filter, kein `if:` am Job** – sonst friert `main`
  ein oder das Gate wird Scheingrün. Umbenennen nur nach
  `docs/PFLICHT-CHECK-RUNBOOK.md`.
  Der Meta-Schritt `pflichtcheck_guard.py` meldet den auf diesem Repo **nicht
  erfüllbaren** Teil (kein Ruleset verlangt den Check; Rulesets ändern ist
  Admin-Aufgabe, C15) als **bekannten Dauerzustand**: Exit 0 mit `::warning::`,
  das 🛑 bleibt in Log und Summary – Erklärung `PFLICHT_CHECK_DAUERZUSTAND`,
  Prüffrist bis 31.12.2026, harter Ausweg `--strict`. Nicht „reparieren“, nicht
  grün waschen, nicht im Workflow auf `--strict` umstellen; Rückbau und Ablauf
  stehen im Runbook-Abschnitt „Dauerzustand“.
- Agenten-Tokens haben KEINE `workflows`-Permission: Workflow-Dateien nur
  per Patch/PR mit vollwertigem Token ändern (siehe README, Known Issue).

## Alarm-Routing (seit #272, 12.09.2026)

**Nie wieder einen Befund ohne Besitzer melden.** Jeder neue Melde-Befund
braucht `owner` (`auto` = Maschine heilt, `human` = nur ein Mensch), `severity`
(P1–P3) und `channel` (Label, dem das Ticket gehört). Menschliche Befunde
öffnen **kein** Automations-Ticket und halten keins offen – sonst entsteht der
Dauer-Alarm ohne Schließpfad, der #272 erzeugt hat.

- SSOT: `scripts/alert_router.py` (Planung rein/testbar, `gh`-Aufrufe abgesichert)
- Anwender: `scripts/bot_watchdog.py --route`
- Vertrag: `governance_contract.py` **C14** (prüft Besitz-Trennung + Schließpfad)
- Betriebsmodell: `docs/ALARMROUTING-2026-09-12.md`

## Internet-Recherche (Agent Reach, seit 12.09.2026)

- **Ad-hoc-Recherche/Suche/URL-Lektüre:** immer über den Skill
  `.claude/skills/agent-reach/` (Routing-Tabelle + `references/` beachten;
  vor Login-/Multi-Backend-Plattformen `agent-reach doctor --json` prüfen).
  Nichts „aus dem Gedächtnis" erfinden, wenn das Netz die Antwort hat.
- **Geplante Signalsammlung:** `scripts/agent_reach_research.py` liest den
  kuratierten Themenplan (`data/agent_reach/themenplan.yaml`) und legt
  Briefs unter `data/research/` ab (CI: `.github/workflows/agent-reach-research.yml`,
  Mo 08:15 MESZ). Gesundheitscheck: `scripts/agent_reach_gate.py`.
- **Leitplanken:** nur LESEN (nie posten/schreiben), keine Cookies/Logins in
  CI, Facts aus Briefs erst nach menschlicher Prüfung in kuratierte Pools
  (`data/aktuelle_entwicklungen.yaml`, `data/topics.yaml`) übernehmen.
- Installations- und Betriebsdetails: `docs/ANLEITUNG-AGENT-REACH.md`.

## Maschinen-Artefakte niemals mergen (seit 22.09.2026, Issue #346)

`data/integrity_lock.json` ist ein **Siegel**, kein Quelltext: SHA-256-Map,
verkettete Akte, eigene Prüfsummen. Es wird ausschließlich von
`scripts/integrity_guard.py` geschrieben.

- **Bei Merge-Konflikt: niemals beide Seiten zusammensetzen.** Eine Fassung
  wählen und neu signieren (`--set-current`) — oder das Siegel belegt heilen
  lassen: `python3 scripts/integrity_guard.py --repair-lock`.
- `.gitattributes` setzt `merge=binary`: Ein Text-Merge ist damit gar nicht
  mehr möglich (am 21.09.2026 hat genau so ein Zusammenschnitt die
  Content-Engine im ersten Schritt gestoppt, Issue #346).
- Zustand prüfen statt raten: `python3 scripts/integrity_guard.py --drift-audit`
  nennt Siegel-Zustand (gesund / Legacy / zerstört / Chimäre), Bruchstelle und
  Herkunft. Ein zerstörtes Siegel heißt **nicht** „6 Kerndateien ohne
  Signatur" — es heißt, dass keine Aussage möglich ist.
- Schreiben ist atomar + rückgelesen: Ein abgebrochener Lauf hinterlässt den
  vorigen Stand, nie ein halbes Siegel.

## Wichtige Konventionen

- Commits: Conventional Style mit deutschprachiger Beschreibung
  (`feat:`, `fix(gate):`, `chore:` …) – siehe `git log`.
- Reports/Dokumentation: Deutsch, datierte Dateinamen im Root
  (`*-2026-09-12.md`), auto-generierte `*-REPORT.md` sind gegittet.
- CSS: `assets/css/extended/` lädt alphabetisch – `zzz-agency-polish.css`
  ist der Politur-Layer und bleibt zuletzt.
- Bilder: immer `width`/`height` (CLS-Gate), Varianten via
  `scripts/check_covers.py --fix`.
