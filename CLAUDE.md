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

## README ist Markenfläche (DAUERVORGABE)

Das `README.md` wird indexiert und steht bei einer Markensuche neben dem
Ratgeber. **Dort steht nichts über die Maschine.** Keine Automatik, keine
Abläufe, keine Gates, keine Werkzeugnamen, keine Dateipfade, kein „0 € Stack" –
auch nicht als Stolz-Abschnitt über eine frische Integration (genau so entstand
Vorgang WF-A4E0 / Meldung #552 am 03.10.2026, nach demselben Fall am 01.10.).

- **Technisches gehört nach `docs/ENTWICKLER-WERKZEUGE.md`**, im README höchstens
  der Verweis darauf. Projektberichte bleiben im Root (`*-PREMIUM-*.md`).
- **Ausnahme nur mit Begründung** in `data/brand_surface_allowlist.txt`.
- **Vor jedem README-Commit:** `npm run marke:check`
- **Die Commit-Sperre stellt sich selbst scharf.** `scripts/haken_wache.py`
  hängt `.githooks/pre-commit` bei `npm install` (prepare) und bei jedem
  Marken-Lauf ein – vorhandene Haken bleiben dabei aktiv (`pre-commit.lokal`).
  Kontrolle: `npm run hooks:status`, von Hand: `npm run hooks:install`.
  **Niemals `core.hooksPath` von Hand setzen** – das legt alle anderen Haken
  still; der Wächter zieht solche Arbeitskopien um und begründet es.
- Regressionstest: `npm run test:marke` (Wache + Wächter) · Hintergrund:
  `MARKENFLAECHE-README-PREMIUM-2026-10-04.md` und
  `LEITPLANKEN-SELBSTSCHARF-PREMIUM-2026-10-04.md`, Runbook:
  `docs/MARKEN-OBERFLAECHE-RUNBOOK.md`.

## Vorgänge werden mit Nachweis geschlossen (DAUERVORGABE)

Eine behobene Meldung bekommt einen **Abschlussvermerk**, und zwar nicht von
Hand: Das persönliche Zugangsrecht darf keine Kommentare schreiben (HTTP 403,
belegt am 04.10.2026 an Meldung #552). Zuständig ist
`.github/workflows/vorgangs-abschluss.yml` – sofort beim Zusammenführen und
täglich als Nachlauf.

- **Im Vorschlag immer `Closes #<Nummer>`** schreiben; daraus leitet sich der
  Vermerk ab.
- Nie von Hand nachkommentieren; fehlt ein Vermerk, nachtragen lassen:
  `npm run vorgang:abschluss -- --pr <Nummer> --apply` (oder `vorgang:nachtrag`).
- **Issue-Kommentare sind Markenfläche.** Der Text läuft vor dem Absenden durch
  die Marken-Wache; Betriebssprache wird zurückgenommen, nicht veröffentlicht.
- Regressionstest: `npm run test:vorgang` · Doku:
  `docs/ENTWICKLER-WERKZEUGE.md`, Abschnitt „Abschlussvermerk an die Meldung".

## Redaktionelle Sprache (DAUERVORGABE)

Templates und wiederkehrende Formeln erzeugen Gleichförmigkeit. Für alle neuen
und überarbeiteten Texte gilt deshalb: sprachlich mindestens auf dem Niveau von
ZEIT.de, jedoch mit eigenständiger Stimme und ohne Nachahmung. Die Form folgt
dem konkreten Thema; Einstiege, Übergänge, Überschriftenrhythmus und Schlüsse
werden nicht schematisch wiederholt. Jeder Artikel braucht einen eigenen Blick,
eine konkrete Beobachtung oder ein tragfähiges Bild. Anspruch bedeutet Präzision
und gedankliche Beweglichkeit, nicht Ornament oder unnötige Komplexität.

Die ausführliche, maschinenlesbare Leitplanke steht in
`data/schreibstil.yaml` unter `eigenstaendigkeit`; Generierung und manuelle
Lesbarkeitsprüfung müssen sie berücksichtigen.

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
python3 scripts/audit_log.py --selftest              # Beweis-Ledger: Umlenkung/Stummschaltung (C27)
python3 scripts/repo_isolation.py --selftest         # Test-Sandbox: data/audit/ bleibt unberührt (C27)
python3 scripts/selftest_ki.py --trap-workflows      # KI-Probe: kein Selbsttest hängt an Modell/Netz (#138)
npm run test:release                                 # Release-Scorecard: Selbsttest + 41 Unit-Tests (Produktionswahrheit)
python3 scripts/release_scorecard.py                 # Release-Scorecard: acht Dimensionen je Live-Artikel + Siegel
python3 scripts/alert_router.py --selftest           # Routing-Regeln (Besitz/Kadenz/Schließpfad)
python3 scripts/zeit_rechtschreibung.py --selftest   # ZEIT-Niveau-Rechtschreibungs-Wache (offline, Sabotage-Schutz)
npm run test:rechtschreibung                          # Selbsttest + 23 Unit-Tests der Wache
npm run offenlegung                                   # Build + Werbe-Offenlegung O1–O7 (artikelgenau, sichtbar)
npm run test:offenlegung                              # Selbsttest (13 Sabotage-Proben) + 36 Unit-Tests
npm run vergleiche:check                              # Bewertungsraster V1–V8: Selbsttest + Quellen + Build + HTML-Beweis
npm run ki:transportweg                               # KI-Transportweg: Vertrag T1–T9 + Cockpit (ein Modell, drei Wege, 0 €)
npm run ki:status                                      # welche Gratis-Hoster sind gerade erreichbar?
npm run test:ki                                        # Gate-Selbsttest (10 Sabotage-Proben) + 28 Vertragstests
npm run test:vergleiche                               # Selbsttest der Vergleichs-Wache (10 Sabotage-Proben, offline)
npm run werkzeuge:check                               # Werkzeuge W1–W7: Selbsttest + Quelle + Build + public/
npm run test:werkzeuge                               # 18 Gate-Unit-Tests + 55 Rechenkern-Tests (jsdom)
npm run robustheit:check                              # Robustheit R1–R13: Selbsttest + Quelle + Build + gebaute Wahrheit
npm run test:robustheit                               # Robustheit: Gate-Selbsttest + Unit-Tests + Verhalten im jsdom
npm run test:suche                                    # Suche: jsdom + Suchindex-Wache (Selbsttest) + Python-Verträge (#644)
npm run test:suche:browser                            # Suche im Chromium: Trefferregel, Datenschutz, Tastatur, Mobil
python3 scripts/robustheits_gate.py --source-only     # Laufzeit-Fangnetze ohne Hugo (< 1 s, fail-closed im Deploy)
npm run h1:check                                      # H1-Wache: genau eine H1 pro Seite (Quelle + Build)
npm run test:h1                                       # H1-Wache + vollständiges A11y-Audit (46 Regressionstests, C30)
npm run test:a11y                                     # fokussierte Vollscan-/Fail-closed-Regressionen
npm run marke:check                                   # Markenfläche README: Selbsttest + Gate (offline, < 1 s)
npm run test:marke                                    # Wache (17 Fallgruppen) + Haken-Wächter (11) + 34 Regressionstests
npm run hooks:status                                  # steht die Commit-Sperre in dieser Arbeitskopie? (sonst: hooks:install)
npm run test:haken                                    # Selbstscharfstellung der Commit-Sperre (echte Wegwerf-Repos)
npm run vorgang:abschluss -- --pr <Nr>                # Abschlussvermerk an die Meldung (Plan; --apply schreibt)
npm run test:vorgang                                  # Abschlussvermerk: 12 Fallgruppen + 15 Verfahrenstests
npm run manifest:check                                # Manifest-Wache: package.json + Lockfile vor npm ci (J/K/F/D/L/P, Exit 1 bei Befund)
npm run test:manifest                                 # Manifest-Wache: Selbsttest (Sabotage + Gegenprobe) + Unit-Tests (#654)

# 0 € Blogautomatik (Whisper lokal + n8n self-hosted + Pages, 03.10.2026) – Details: docs/ANLEITUNG-WHISPER-N8N-GITHUB-PAGES.md
npm run blogautomatik:status                         # Live-Status aller drei Säulen (Whisper, n8n, Pages)
npm run blogautomatik:audit                          # 0 € Kosten- & Einsparungs-Audit
npm run blogautomatik:selftest                       # Offline-Selbsttest aller Säulen (Fail-Closed)
npm run test:blogautomatik                           # 39 Unit-Tests für Whisper, n8n-Bridge & Orchestrator
npm run whisper:inbox                                # Wartende Sprachaufnahmen in data/whisper_inbox/ verarbeiten
npm run n8n:ping                                     # Latenz- & Erreichbarkeits-Check für n8n

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

**Browser-Pflicht (seit #507, 01.10.2026):** Ein merge-fähiger Stand hat den
vollen Playwright-Lauf hinter sich – „in dieser Sandbox nicht startbar" ist
kein akzeptabler PR-Zustand mehr. Wenn `cdn.playwright.dev` blockiert ist
(TLS-Reset), läuft die Suite über den eingebauten Fallback:
`npm i --no-save @sparticuz/chromium` (Resolver greift automatisch) –
Hintergrund und weitere Rettungswege: `docs/ANLEITUNG-DESIGN-VARIANTEN.md`,
Abschnitt Troubleshooting, und `docs/INCIDENT-2026-10-01-e2e-suite-492.md`.

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

## Parallele Bearbeitung: der Bestand gewinnt (seit #590, 05.10.2026)

Menschen (PR-Merges) und Automatik arbeiten am selben Bestand. Kollidiert eine
**maschinelle Heilung** mit einer **fremden, neueren Fassung** desselben
Artikels, gewinnt die fremde Fassung – und die Heilung wird nachgezogen, nicht
vergessen. Unwiederbringlich ist Text; Heilung ist reproduzierbar.

- **Schalter (Opt-in, nicht global):** `GIT_SYNC_BESTAND_POLICY=bestand-gewinnt`
  in `content-engine-v2.yml`. Ohne die Variable bleibt ein Content-Konflikt in
  `scripts/git_sync.sh` ein **harter Stopp** – kein Blind-Merge, nirgends.
- **Nachheilung:** `scripts/git_sync.sh` protokolliert jeden abgegebenen
  Artikel in `.git_sync_nachheilung.txt` (gitignored),
  `scripts/nachheilung.py --fix` heilt ihn im selben Lauf auf dem neuen Text
  (offline, deterministisch, keine Geldfläche, < 1 s).
- **Reserve bleibt Maschinensache:** Bei zwei Reserve-Entwürfen gewinnt
  weiterhin der frische Lauf (#295) – diese Regel hat Vorrang.
- **Ehrlichkeit:** Ein nicht gepushter Tagesertrag bleibt rot, aber als eigene
  Klasse (`SYNCHRONVERLUST`) mit Datei und Ursache – nie wieder „API-Key
  prüfen", während ein Rebase klemmt.
- Vor jedem Umbau am Sync-Kern: `npm run test:sync` (47 Verträge) · Hintergrund:
  `SYNCHRONVERLUST-ENGINE-590-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

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

## Schaltwerk: Automationen statt Zapier (seit 01.10.2026)

`scripts/schaltwerk.py` ist der repo-eigene Zapier-Ersatz: **Trigger → Filter
→ Aktion**, deklariert in `data/automationen.yaml`, getaktet von
`.github/workflows/schaltwerk.yml` (alle 30 min, dazu `workflow_dispatch` und
`repository_dispatch` als kostenloser Webhook). Kein Fremddienst, keine
Task-Limits, keine Kosten.

- **Arbeitsteilung:** Der Social-Autopilot bleibt der Sender für neue Artikel
  und Evergreen-Recycling. Das Schaltwerk dirigiert und füllt Lücken
  (Update-Wellen, Reach-Kuratierung, Wachhunde, Planerneuerung, Ad-hoc-Posts).
  Jede sendende Regel braucht `dedupe_key` und `throttle` – sonst Doppelposts.
- **Leitplanken (durch Selbsttest + Unit-Tests erzwungen):** Agent-Reach-Signale
  nie direkt posten (nur `themen_vorschlag`); kostenpflichtige Kanäle (X) nicht
  fest verdrahten; Standby ist kein Fehler; `--dry-run` schreibt nichts;
  gescheiterte Ketten gelten nicht als erledigt.
- **Vor jedem Umbau am Regelwerk:** `npm run test:schaltwerk`, danach
  `python3 scripts/schaltwerk.py --dry-run`.
- Cockpit: `SCHALTWERK-STATUS.md` · Anleitung: `docs/ANLEITUNG-SCHALTWERK.md`.

## Faktenfrische: Recherche pro Artikel (seit 27.09.2026)

`scripts/faktenfrische.py` ist die **artikelgenaue** Schwester der breiten
Signalsammlung: Agent-Reach-Recherche + Claude-Fachprüfung (Puter-Brücke, ohne
Anthropic-API) für jeden bestehenden und jeden neuen Artikel.

- Zwei Takte: **Erstellung** (`--neu --apply` in `content-engine-v2.yml`,
  Phase 3) und **Bestand** (`faktenfrische.yml`, Di + Do). Fälligkeit nach
  Risikoklasse: saisonal 30, YMYL 45, Standard 90 Tage
  (SSOT `data/agent_reach/faktenfrische.yaml`).
- **Schreibrecht ist eng:** nur die Frontmatter-Felder `faktencheck` und
  `quellen`. Artikeltext **nie** automatisch, `lastmod` **nie** (Frische-
  Inflation). Fachliche Befunde → Report/Queue/Issue, Mensch entscheidet.
- **Anti-Halluzination (doppelter Deckel):** Eine Quelle darf nur in einen
  Artikel, wenn ihre URL wörtlich im Recherche-Dossier steht **und** ihre
  Domain auf der Allowlist liegt. Affiliate-Partner sind nicht belegfähig.
  Eingefroren in `--selftest` (ST3) – nicht aufweichen.
- Sichtbar wird das über `layouts/_partials/ff_quellen_box.html` („Quellen &
  Faktenstand“) und als `citation`/`sdDatePublished` im Article-JSON-LD.
  **Eine Quelle, zwei Ausspielwege** – nie einen der beiden separat pflegen.
- Runbook: `docs/ANLEITUNG-FAKTENFRISCHE.md`.

## Hugo-Build: eine Fehlerausgabe für alle Workflows (seit 03.10.2026)

**Jeder Hugo-Bau läuft über `./.github/actions/hugo-build`.** Direkte
`run: hugo …`-Zeilen sind ein Befund (H6).

```yaml
- name: Seite bauen
  uses: ./.github/actions/hugo-build
  with:
    args: "--minify"
    label: "Qualitäts-Gate"
```

**Warum.** Am 02.10.2026 starb der Build an einem leeren Verzeichnis unter
`content/`. Die Suche dauerte Stunden, weil fünf Workflows die Fehlerzeile
vernichteten: `> /dev/null 2>&1` (seo-weekly, 2×), `|| true` (bot-watchdog),
`--quiet` (e2e, layout-ai, visual-data-gate). Ein Schritt, der rot wird und
nichts sagt, ist teurer als einer, der grün durchläuft.

Die Action garantiert ohne Zutun des Aufrufers: `pipefail` + `PIPESTATUS[0]` +
`tee`, eine `::error title=…::`-Annotation, einen Block in
`$GITHUB_STEP_SUMMARY` und eine **Selbstdiagnose**, die aktiv nach leeren
Verzeichnissen sucht — die sieht `git status` grundsätzlich nicht.

**`--quiet` wird abgelehnt** (Exit 2). Ruhe gibt es über die Logdatei, nicht
durch Wegwerfen der Diagnose.

**Darf ein Bau scheitern?** Dann `weiter-bei-fehler: "true"` statt `|| true`.
Der Fehlschlag bleibt sichtbar, er stoppt nur den Job nicht. *Toleriert* und
*unbemerkt* sind zwei verschiedene Dinge.

Wache `scripts/hugo_build_vertrag.py` (H1–H8) läuft im Qualitäts-Gate.
Ausnahmen nur mit Begründung in `AUSNAHMEN` — ein toter Eintrag ist selbst ein
Befund. Runbook: `docs/ANLEITUNG-HUGO-BUILD.md`.

---

## Ein `--selftest` muss das Modul prüfen, dessen Namen er trägt

`scripts/hemingway_check.py` warb mit `--selftest`, reichte die Flagge aber nur
an `readability_check` weiter — und ersetzte in dessen grüner Zeile den
Modulnamen. Das Häkchen lautete `✅ hemingway_check --selftest OK`, geprüft war
davon keine Zeile. Der zugehörige Test bestätigte genau diese gefälschte
Zeichenkette (behoben 03.10.2026).

**Regel für Adapter-Module:** Der Selbsttest prüft die eigenen Versprechen
(Durchreichen, Exit-Codes, Umbenennung, JSON-Unversehrtheit) **und** ruft den
Selbsttest der Engine zusätzlich auf. Er darf die Flagge nie bloß weiterreichen.

**Gegenregel zum Weiterreichen:** Hat die Engine gar kein `--selftest`, startet
ein Aufruf mit der Flagge ihre Standard-Aktion — bei `publish_gate.py` wäre das
der scharfe Lauf, der am 18.09.2026 beinahe einen Live-Artikel auf `draft`
herabstufte. `selftest_runner.GEFAHREN` führt solche Module mit Begründung.

---

## Kostensperre: Geldflächen sind verriegelt, nicht gelöscht

**SSOT `data/kostensperre.yaml` · Wache `scripts/kostensperre.py` · Vertrag T10**

Zwei Flächen außerhalb der Textkette können Geld kosten: die
Vorlese-Stimme (ElevenLabs) und die Rechtschreibung auf ZEIT-Niveau.
Beide bleiben im Code, sind aber **fail-closed verriegelt**: Ein
gesetztes Secret allein löst nichts mehr aus. Entsichern geht nur über
einen Commit in der SSOT – mit `grund` und `datum`, sonst wirkt die
Freigabe nicht.

```bash
npm run kosten:sperre     # Bericht
npm run kosten:pruefen    # Wache (CI)
npm run test:kosten       # Selbsttest + Vertragstests
```

Regel: **Neue Geldfläche → Eintrag in `data/kostensperre.yaml` und
Aufruf von `kostensperre.wache(<id>)` an der Engstelle.** T10 wird sonst
rot. Runbook: `docs/ANLEITUNG-KOSTENSPERRE.md`.

## KI-Transportweg: ein Modell, drei Wege, 0 € (seit 03.10.2026)

Jeder Modell-Ruf des Blogs geht durch **einen** Zugang
(`scripts/llm_client.py`) und folgt **einer** Routing-Tabelle
(`data/ki_transportweg.yaml`). Gate: `scripts/ki_transportweg.py` (T1–T9,
fail-closed, Selbsttest mit zehn Sabotage-Proben).

- **„ChatGPT (Free)" ist keine Option – nicht aus Sparzwang, sondern
  weil es sie nicht gibt.** Keine API; die OpenAI-API hat keinen
  nutzbaren Gratis-Tier; das Web-UI zu automatisieren verstößt gegen die
  Nutzungsbedingungen; **GitHub Models ist seit 30.07.2026
  abgeschaltet**. Wer das „nur mal eben" nachrüstet, baut Issue #514 neu.
  Begründung: `CHATGPT-GRATIS-TRANSPORTWEG-PREMIUM-2026-10-03.md`.
- **Die OpenAI-Bahn:** `openai/gpt-oss-120b` – OpenAIs eigenes offenes
  Modell – bei **drei** unabhängigen Gratis-Hostern (Groq → NVIDIA NIM →
  Cloudflare Workers AI), danach Gemini als Gegenprobe aus einem anderen
  Modellhaus. Ein leeres Tageskontingent hält damit keine Automatik mehr an.
- **T1 ist eine Dauersperre (verschärft 03.10.2026):** Es gibt **keinen**
  kostenpflichtigen Weg mehr – die Provider `openai`/`claude` sind samt
  Endpunkten, Schlüsseln und `--provider`-Flags aus dem Repo entfernt.
  T1 prüft SSOT, Client, **alle** Skripte und **alle** Workflows auf
  Rückkehr (Schlüsselnamen *und* Endpunkte); T9 bewacht zusätzlich die
  vier KI-Workflows. Ein alter `chat("openai", …)`-Aufruf scheitert
  **laut** mit Klartext-Ansage, nicht still. Wer wieder eine Paid-API
  anschließen will, ändert zuerst diesen Vertrag – nicht nebenbei ein
  Skript.
- **T3/T4 sind Verfügbarkeitsregeln:** mindestens zwei Gratis-Glieder und
  mindestens ein OpenAI-Hoster je Kette. Eine Kette mit einem Glied ist
  ein Vertragsbruch, kein Betriebszustand.
- **T5 verbietet die Bauweise, nicht einen Namen:** keine Browser-Brücke,
  kein UI-Scraping (auch nicht von ChatGPT), kein geteiltes Fremdkonto –
  in Skripten **und** Workflows. Diese Regel hat am 03.10.2026 die
  anbieterspezifische Datei `test_keine_puter_abhaengigkeit.py` abgelöst.
- **Denkspuren-Filter:** GPT-OSS denkt laut. `llm_client._ohne_denkspuren()`
  entfernt `<think>`/`analysis…assistantfinal` zentral für alle Hoster –
  sonst landet es als R16-PROMPT-ECHO im Frontmatter (#521).
- **Standby ist grün, aber nicht still.** Kein Schlüssel = Offline-Gerüste,
  und das Cockpit sagt es laut. Genau diese Ehrlichkeit fehlte bei #514.
- **Vor jedem Umbau:** `npm run test:ki`, danach `npm run ki:transportweg`.
- Cockpit: `KI-TRANSPORTWEG-STATUS.md` · Anleitung:
  `docs/ANLEITUNG-KI-TRANSPORTWEG.md`.

## Werkbank: die eigene Antwortmaschine statt Perplexity (seit 03.10.2026)

`scripts/antwortwerk.py` beantwortet Recherchefragen **mit Belegen** und
ersetzt damit die Rolle, für die sonst ein Perplexity-Abo nötig wäre.
Kette: SearXNG sucht → Allowlist filtert → Crawl4AI liest → Playwright
beweist → Synthese zitiert. SSOT `data/werkbank.yaml`, Vertrag
`scripts/werkbank_gate.py` (B1–B9, fail-closed, `--selftest` mit zehn
Sabotage-Proben).

- **Perplexity nicht einbauen.** Bewusste Entscheidung, nicht aus Sparzwang:
  Volltext statt Snippet, Quellenrang statt Anbieterrelevanz, Affiliate-Sperre,
  Zitatprüfung im echten Browser, 0 €. Begründung in
  `WERKBANK-PREMIUM-2026-10-03.md`, Abschnitt 2. Das Dossier-Format folgt der
  Perplexity-Agent-API, damit ein späterer Anschluss ein Adapter bleibt.
- **Die vier Gewerke:** Antwortwerk (Faktenfrische + GEO-Check), Crawl4AI
  (Markdown-Lesen, löst Jina ab), Playwright (Browser-Beweis), Composio
  (Konnektor fürs Schaltwerk).
- **Ohne Beleg kein Satz.** Ohne `GROQ_API_KEY`/`GEMINI_API_KEY` arbeitet das
  Antwortwerk **extraktiv** – wörtliche Passagen mit `[1]`-Belegen, kein
  Sprachmodell, keine erfundene Zahl. Secret hinterlegen schaltet Synthese
  scharf, die Belegpflicht bleibt. Exit 3 = keine Quelle belegfähig (Warnung,
  kein Abbruch).
- **B9 ist nicht verhandelbar:** eigene Domain und alle aus
  `scripts/check24_links.yaml` abgeleiteten Partnerdomains sind als Quelle
  gesperrt. `domain_von()` entfernt dabei Port, Zugangsdaten und `www.` –
  sonst läuft `check24.de:443` an der Liste vorbei (war ein echter Bug).
- **Standby ist grün.** Fehlendes Secret oder fehlendes Modul = ⏸, Exit 0. Nur
  `--strict` (für CI) verlangt alle Gewerke aktiv.
- **Additiv:** `sammle_web()` in `agent_reach_research.py` versucht Crawl4AI
  zuerst und fällt auf Jina zurück. Ohne Crawl4AI ist das Verhalten
  unverändert. `faktenfrische.py` und `schaltwerk.py` sind unberührt – die
  Werkbank liefert Signale, nicht Freigaben.
- **Vor jedem Umbau:** `npm run test:werkbank`, danach
  `python3 scripts/werkbank_gate.py --selftest`.
- Cockpit: `WERKBANK-STATUS.md` · Anleitung: `docs/ANLEITUNG-WERKBANK.md`.

## ZEIT-Niveau-Rechtschreib-Wache (Dauerbetrieb seit 28.09.2026)

Dauerhafte Premium-Rechtschreibprüfung aller Artikel
(`scripts/zeit_rechtschreibung.py`, SSOT `data/zeit_rechtschreibung.json`).
Faktenlage: zeit.de bietet **keine** öffentliche Rechtschreib-API – die
ZEIT-Latte (s. Abschnitt Sprache) wird über die `/v2/check`-kompatible
Premium-Engine eingelöst. Provider-Kette: **Premium** (ENV `ZR_API_URL`
bzw. `ZR_USERNAME`/`ZR_API_KEY`) → **öffentlich** (nur `--oeffentlich`,
ToS verbieten Automation – im CI hart geblockt) → **offline**
(LT1–LT4-Nachbau, immer verfügbar).

- **Kosten-Regel:** kein Paid-/Netz-Provider als alleiniger Pfad –
  `require_online`/`offline_fallback` in der Config sind verboten
  (Selbsttest ST8, Exit 2).
- **Schreibvertrag:** Auto-Fix nur aus harter Regel-Allowlist mit genau
  einem Vorschlag, nie im Titel, nie in Schutzzonen (längentreue
  Maskierung), immer `sprachkern.write_verified`; Stil/Komma bleiben
  Agentur-Hand (Fund mit `owner=human`).
- **Quota:** `data/zeit_rechtschreibung_cache.json` (versioniert) –
  unveränderte Artikel kosten keine Anfrage; Verlauf in
  `data/zeit_rechtschreibung_history.jsonl`.
- **CI aktiv:** `.github/workflows/zeit-rechtschreibung.yml`
  montags 04:35 UTC (seit 28.09. aktiv; die einstige Vorlagen-Kopie in
  `workflow-ready/` ist am 30.09. entfernt – SSOT ist der aktive Workflow).
- Runbook + Datenschutz + Premium-Aktivierung:
  `docs/ANLEITUNG-ZEIT-RECHTSCHREIBUNG.md`.

## Politur-Ruinen: Wache R11–R15 (seit 30.09.2026, Issue #482)

Vier echte Textdefekte aus automatisierten Politur-Läufen waren live
gegangen („Du bist der 0 am deutschen Strommarkt“, „es ist der 2 Januar“,
„Nutze 20 26 gezielt Mindestbestellwerte“, „SATZ: | **CHECK24-Vergleich** |
– | | | | |“) — plus das Mietwagen-Doppel-Intro. Keine Wache maß sie,
`sprachkern.write_verified` prüfte nur Struktur (Links, Shortcodes,
Überschriften, Wortzahl), nie den Ergebnis-Text.

- **Eine Muster-SSOT:** `sprachkern.POLITUR_RUINEN` (R11 Jahreszahl-Split,
  R12 Zahl-Ruine, R13 Datum-ohne-Punkt, R14 Marker-Ruine).
  `write_verified` **verweigert jede Schrift, die eine NEUE Ruine
  einführt** (bestehende blockieren die Heilung nicht) — gilt damit für
  Sprachglatt, Grammatik-Check und ZEIT-Rechtschreibung automatisch.
- **Eine Wache:** `textverstaendnis_guard.py` R11–R14 (via SSOT) +
  **R15-PHRASEN-DOPPEL** (identische ≥-10-Wort-Sequenz im Fließtext eines
  Artikels; fingert Doppel-Intros, die duplikat_guard D1/D2 verpassen).
  Tägliches Audit (`blog-health-daily.yml`), Selbsttest mit den
  eingefrorenen echten Schadensfällen.
- **Publish-Gate blockt die Maschinen-Ruinen-Familie komplett:**
  R8-NESTED-LINK, R9, R10 und R11–R15 sind hart in
  `publish_gate.textverstaendnis_failures()` — genau diese Klasse ist
  früher live gegangen.
- R15 läuft bewusst **nur auf Artikel-Fließtext** (nicht auf Rechtsseiten:
  Impressum-Adressen wiederholen sich legitim) und nicht auf
  Überschriften/Listen/Tabellen/CTA-Boxen.
- **R16-PROMPT-ECHO / R16-PROMPT-ECHO-META** (seit 02.10.2026, Issue #521):
  Prompt-Marker (`TITLE:`, `DESCRIPTION:`, `KEYWORDS:` …) im Fließtext bzw.
  im Frontmatter. Realfall: `parse_article` erkannte den Prompt-Kopf nur
  positionsgebunden; eine Leerzeile zwischen den Markern genügte, und
  „TITLE: …“ stand in `description`, `pin_description` **und** im Artikel.
  R16-META ist die **erste Regel dieses Guards, die ins Frontmatter sieht** –
  `split_body()` schneidet es sonst ab, und genau dort geht der Text als
  Google-Snippet und Pin nach außen.
- **Die beiden harten Regelsätze müssen deckungsgleich bleiben**
  (`textverstaendnis_guard.hard_rules` ↔ `publish_gate.textverstaendnis_failures`).
  Am 02.10.2026 behauptete der Report-Kopf „harte Regeln R11–R15“, während
  die Liste des Guards sie gar nicht enthielt – eine Wache, die eine
  Blockade nur versprach. `test_prompt_echo.py` vergleicht beide Sätze jetzt
  dauerhaft.
- Runbook + Zahlen: `LESBARKEIT-ENTWUERFE-PREMIUM-2026-09-30.md`,
  `CONTENT-ENGINE-KAPAZITAET-PREMIUM-2026-10-02.md`.

## Die Endabnahme heilt Shortcode-Schaden und benennt Build-Crashs (WF-A535 #529, seit 02.10.2026)

Am 02.10.2026 ließ ein einziger Markdown-Link in einem
`rechner`-Shortcode-Parameter **alle** Hugo-Builds sterben; die
Content-Engine-Endabnahme (`publication_release.py`) endete in rohem
Traceback, der Reserve-Refill lief nie, und das Auto-Issue riet zu
API-Keys statt zur echten Ursache. Vertrag seither:

- `publication_release.py` führt am Anfang **jedes** Laufs
  `shortcode_guard.py --fix` aus (eine Quelle, alle Aufrufer: Engine,
  Kadenz-Backstop, Deploy-Refill) – best-effort, der Build bleibt hart.
- **Exit-Codes sind Vertrag:** 0 = ok · 1 = Tagesdefizit (ehrlich rot,
  aus `publication_check`) · 3 = Release-Crash (fail-closed, strukturiert
  diagnostiziert: echte Hugo-Fehlerzeile + Reparaturpfad + Audit-Event).
  Wer die Trennung einebnet, macht Crashs wieder ununterscheidbar von
  Defiziten – genau der Zustand, der #529 öffnete.
- Die Engine-Workflow führt die Shortcode-Wache **vor** der Endabnahme
  (Spiegel der Kadenz-Endkontrolle) und der Wächter-Schritt am Ende
  benennt die Klasse (`TAGESDEFIZIT` vs. `RELEASE-CRASH`) als Annotation.
- Verdrahtung ist gepinnt: `scripts/tests/test_publication_release_wache.py`.
  Runbook + Tathergang: `ENDABNAHME-WACHE-PREMIUM-2026-10-02.md`.

## Themen haben zwei Bahnen (seit 02.10.2026, Issue #521)

Am 02.10.2026 lief die Engine, schrieb vier Artikel und veröffentlichte
**null**. Nicht die Produktion war kaputt, sondern die Buchhaltung darüber.

- **AUTO vs. FACHFREIGABE:** YMYL-Themen (Versicherung, Rente, Kredit –
  46 von 187) können per Vertrag nie ohne menschliche Freigabe live gehen.
  Die Disposition war dafür blind, gab sie an die Automatik und verbuchte
  den unveröffentlichbaren Entwurf als Erfolg: Slot weg, Thema 180 Tage
  gesperrt, LIVE-Zähler unverändert. **Nur `engine_capacity.nur_auto()`
  beantwortet „schaffen wir das Tagesziel?“.**
- **Die Bahn ersetzt nie ein Gate.** Sie ist asymmetrisch konservativ: Ein
  bekanntes `hoch`-Thema kommt nicht in die Quote; ein als `auto`
  eingestuftes Thema, dessen Artikel sich doch als YMYL erweist, läuft
  weiterhin ins fail-closed `editorial_review_gate`.
- **Eine Klassifikation, nicht zwei:** `engine_capacity` ruft
  `editorial_review_gate.classify_text()`. Die Risikomuster nie kopieren –
  ein Test verbietet es.
- **Ein Maß für „frei“:** `engine_capacity.lage()` zählt ausschließlich über
  `reserve_topics.disponieren`. Vorher maß der Pre-Flight mit einer laxen
  60-%-Token-Regel (`157 frei`), während der Disponent **3** fand. Nie eine
  zweite Zählregel einführen.
- **Pre-Flight bricht bei Engpass NICHT ab** (`::warning::` statt Exit 1):
  Re-Queue und Reserve-Veröffentlichung brauchen keine neuen Themen. Ein
  leerer Pool heilt nicht dadurch, dass die Engine stillsteht.
- **`merke(ok=True, "produziert: …")` ist keine Garantie, dass es den
  Artikel gibt.** `reserve_topics.abgleich()` (läuft im Pre-Flight) prüft
  gegen den Bestand und löst Phantom-Sperren – am 02.10. waren das **47 von
  63** Einträgen; freie AUTO-Themen 3 → 37. Der Abgleich hebt nur den
  *Cooldown* auf, nie den Dubletten-Schutz.
  ⚠️ **Slug-Falle:** Das Ledger speichert ohne Datumspräfix, auf der Platte
  liegt `<datum>-<slug>` (ggf. mit `-N`). Immer über `_bestands_slugs()`
  normalisieren – die naive Prüfung meldet 51/63 Einträge falsch als
  Phantom und entsperrt den halben Pool.
- Bedienung: `npm run engine:kapazitaet`, `npm run engine:abgleich`.
  Anleitung: `docs/ANLEITUNG-ENGINE-KAPAZITAET.md`.

## „Im Artikel“ bleibt Premium (Wache seit 27.09.2026)

Die schwebende Artikel-Navigation ist zweimal (26.09.2026) an einem
harmlos aussehenden Refactoring zerbrochen. Deshalb ist ihr Premium-Zustand
jetzt ein **geprüfter Vertrag**, nicht eine Absicht:
`python3 scripts/mini_toc_premium_guard.py` (V1–V14: Vollständigkeit,
feste Kopfzeile, Geometrie an `--main-width`, Ruhzustand, Breakpoint,
Druck, Reduced Motion, Dark Mode, Materialtiefe, Fokus-Ring, keine
Inline-Farben, kein Line-Clamp). Der Selbsttest sabotiert die Wache selbst
und verlangt, dass sie es merkt. Läuft in `npm run test:toc`.

## Werbe-Offenlegung ist artikelgenau (Wache seit 28.09.2026)

Der ZEIT-Vergleich bewertete „Unabhängigkeit/Kommerz" mit 4 statt 5: Die
Offenlegung stand pauschal („kann Affiliate-Links enthalten") und bei 56 % der
Seiten **hinter** dem ersten Partnerlink. Jetzt gilt: Jede Seite nennt **über**
dem Text die echte Zahl ihrer Partnerlinks samt Partner und Produkt, werbefreie
Artikel sagen das aktiv.

**Eine Quelle:** `data/affiliate_ziele.yaml` → `_funcs/affiliate_offenlegung.html`
→ Kopf-Kennzeichnung (`ff_offenlegung.html`), Abbinder (`trust_box.html`),
Partnerregister (`/transparenz/`). Nie eine zweite Partnerliste anlegen.

**Beim Layout-Arbeiten:** Die Kennzeichnung hängt in **drei** Stellen
(`_partials/artikel_einzeln.html`, `pillar/single.html`,
`pillar/list.html` – letzteres mit `extraKeys`, weil Template-CTAs nicht in
`.Content` stehen). Bis zur Dauerheilung #623 (07.10.2026) hing sie in
*vier* Dateien, weil die Artikel-Ansicht doppelt lag (`single.html` und
`_default/single.html`); seitdem binden beide Templates denselben Baustein
ein – eine Änderung gehört dorthin, nie in eine zweite Kopie. Sie muss im `<header>` bleiben: `python3
scripts/offenlegung_gate.py` (O1–O7, fail-closed) prüft Position **vor** dem
ersten Partnerlink, Zahl/Partner artikelgenau, Pflichtangaben und
Sichtbarkeit (kein `hidden`/`display:none`/`font-size:0`/`aria-hidden`).
Läuft in Publish-Gate (Gate 6), Bestands-Gate, `npm run test:offenlegung` und
E2E. **Ohne `--fix`** – die Kennzeichnung erzeugt das Template, ein Befund ist
ein Layout-/Registerdefekt für einen Menschen (C15). Runbuch:
`docs/ANLEITUNG-OFFENLEGUNG.md`.

## Werkzeuge sind ein Produkt, kein Shortcode (Wache seit 02.10.2026)

Die acht Rechner unter `/werkzeuge/` sind der **zweite Produktkern** neben dem
Fixkosten-Cockpit. Ihr Wert hängt an Eigenschaften, die man einer Seite nicht
ansieht: vollständige Nutzbarkeit **ohne Affiliate-Klick**, Rechnen ohne
Datenabfluss, offengelegte Formeln und Quellen, Export als CSV/PDF/ICS.

**Eine Quelle:** `data/werkzeuge.yaml` → `werkzeuge_data.html` →
`ff_werkzeug.html` (Markup), `static/premium/ff-werkzeuge.js` (Rechenkern),
`layouts/werkzeuge/{single,list}.html`. Felder, Formeln, Annahmen und Quellen
nie ein zweites Mal pflegen.

**Harte Zusage im Text und im Gate:** „Du kannst das Tool vollständig nutzen,
ohne einen Affiliate-Link anzuklicken." – `python3 scripts/werkzeuge_gate.py`
prüft W1–W7 (Versprechen, Vollständigkeit, Werbefreiheit, Verdrahtung,
Nachvollziehbarkeit, Lokalität, offene Methodik), **ohne `--fix`** und zweimal
im Deploy: Quellvertrag vor dem Build, Produkt-Gate gegen `public/`. Skript und
Markup sprechen ausschließlich über `data-`-Hooks, nie über Klassen. Runbuch:
`docs/ANLEITUNG-WERKZEUGE.md`, Rollout-Report: `WERKZEUGE-PREMIUM-2026-10-02.md`.

## Tags kommen aus dem Register, nie aus Keywords (Wache seit 29.09.2026)

Die Search Console meldete 237 nicht indexierte Seiten. Ursache war nicht der
Content, sondern die Taxonomie-Automatik: beide Generatoren setzten
`tags = keywords[:4]`. Keywords sind long-tail und pro Artikel einmalig – jeder
Artikel prägte damit **vier neue Tags = acht nutzlose URLs** (Archiv +
`/page/1/`-Alias). Nach 63 Artikeln: 217 Roh-Tags, 147 Archive, 193 davon mit
genau einem Artikel, insgesamt 347 nicht indexierbare URLs auf 58 echte Seiten.

**Eine Quelle:** `data/seo/tag_register.yaml` – 25 kanonische Tags, jeder einem
Pillar zugeordnet, mit vollständiger Synonymliste. `tag_governance.tags_fuer()`
ist die **einzige** erlaubte Tag-Quelle für neuen Content. Die Grenze ist
fail-closed und wird an jeder Writer-Ausgabe erneut geprüft: `engine_generate.py`,
`generate_drafts.py`, `ki_shared.py` (Claude/News) und
`pinterest_seo_healer.py`. Ein Tag wird **nie erfunden**: greift nichts,
decidiert die Redaktion über einen Registereintrag – oder der Begriff bleibt
ein Keyword. Keywords gehören ins `keywords`-Feld, wo sie Schema und
Related-Matching speisen, **ohne je eine URL zu bauen**. Ein fehlendes Register
bricht den Writer ab; es gibt keinen Legacy-Fallback auf `keywords[:4]`.

**Zwei Wachen, zwei Ebenen:**
`python3 scripts/tag_governance.py` (T1–T8, **mit** `--apply`) prüft das
Frontmatter: unbekannte Tags, Synonyme statt kanonischer Namen, Thin-Archive
(< 2 Artikel), Tag-Menge, Sonderzeichen (U+202F/U+00A0 erzeugen kaputte Slugs),
Kategorie, tote Registerzeilen.
`python3 scripts/index_hygiene_gate.py` (H1–H8, **ohne** `--fix`) misst die
**Crawl-Fläche des Builds** gegen ein Budget: Sitemap-Deckung,
`/page/1/`-Aliase, Tag-Budget (0), Kategorie-Archive, Verhältnis
indexierbar : nicht indexierbar (max. 1,0 : 1), kaputte Slugs, Waisenseiten,
`noindex` in der Sitemap. Das Deploy-Gate ist hart: Ein Verstoß stoppt den
Publish, statt nur eine Warnung zu schreiben.

**Merke:** `schema_seo_gate.py` S6 war die ganze Zeit grün – es fragt „trägt
dieses Archiv ein noindex?“, nicht „darf es dieses Archiv geben?“. Eine Seite
kann einzeln korrekt und in der Menge trotzdem ein Defekt sein. Deshalb misst
`index_hygiene_gate.py` Anzahlen, nicht Attribute.

**Keine Taxonomie-Archive mehr (Entscheidung 29.09.2026, Frank).** Der
`[taxonomies]`-Block in `hugo.toml` ist **leer** – es gibt weder `/tags/` noch
`/categories/`. Die Tag-Leiste im Artikel-Footer war echte, sichtbare
Navigation, zeigte aber auf `noindex`-Archive: 42 Artikel verschenkten je 2–4
interne Links an Seiten, die nie ranken können. Ersetzt durch
`layouts/_partials/themenwelt_chips.html` – gleiche Position, gleiche Optik
(bewusst dieselben `.post-tags`-Klassen, kein neues CSS), aber Ziele sind die
sechs **indexierbaren** Pillar-Ratgeber. Aus Crawl-Last wurde Linkkraft auf die
Money-Pages.

**Drei Themen-Bausteine, keine Dopplung:** `pillar_box.html` = ein CTA in den
eigenen Ratgeber (nach dem Text) · `themenwelten.html` = Karten-Raster auf
Startseite und `/posts/` · `themenwelt_chips.html` = Quer-Navigation am
Artikelende. Alle drei fail-closed gegen fehlende Ratgeber.

**Nicht anfassen:** `[pagination] disableAliases = true` und der leere
`[taxonomies]`-Block – beide sind dokumentierte Index-Hygiene-Entscheidungen,
keine Altlast. Wer Archive zurückholt, muss `max_tag_archive` in
`index_hygiene_gate.py` mit anheben (steht dort kommentiert). Bericht:
`INDEX-HYGIENE-PREMIUM-2026-09-29.md`.

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

## Die Messlatte der Reserve gehört nicht dem Gemessenen (seit 26.09.2026, #393)

Zielbestand und Alarmschwelle der Content-Reserve haben **einen** Besitzer:
`scripts/reserve_economy.py`.

- `ziel()` kommt aus `RESERVE_TARGET` (Default 6), `alarmschwelle()` wird
  daraus **abgeleitet** (Ziel − Puffer, Default 2). Die Invariante
  `1 ≤ Alarm < Ziel` ist gerechnet, nicht konfiguriert – ohne diesen Abstand
  füllt die Linie exakt bis zur Alarmgrenze und das Ticket öffnet sich nach
  jeder Veröffentlichung neu (genau so entstand #393).
- **Nie wieder ein Ziel aus `data/reserve-readiness.json` lesen.** Das
  Zertifikat ist das geprüfte Artefakt; sein Feld `target` ist Protokoll
  („gegen diese Latte wurde gemessen“), nie Vorgabe. Vorher las der End-Gate
  es als Vorgabe – ein magerer Lauf schrieb `target: 4` und bekam dafür ein
  grünes „4/4“, die Konvergenz reichte die 4 an ihre Kindprozesse weiter und
  schrieb sie zurück: eine Ratsche, die das Produktionsziel aussperrte.
- Abweichung Zertifikat ↔ Produktionsziel ist ein benannter Befund
  (`MESSLATTE`), kein Schweigen.
- Keine zweite Kopie der Zahl anlegen – kein `minimum = 4` irgendwo.
  Verträge: `MesslattenBesitzTests` / `PufferInvarianteTests` in
  `scripts/tests/test_reserve_pipeline.py`.
- Vorfallbericht: `docs/INCIDENT-2026-09-26-bot-watchdog-393.md`.

## Die Reserve füllt sich aus dem Bestand, nicht nur aus Neuproduktion (DAUERVORGABE, seit #594, 05.10.2026)

Achter Vorfall der Klasse „Content-Reserve niedrig" (#251, #272, #281, #393,
#446, #462, #520, #594). Am 05.10. waren **14 Entwürfe reif** und **0** im
Pool: Die Reserve war nicht leer, sie war abgeschnitten. Wer den Vorrat nur
auffüllt, repariert den Melder – nicht die Linie. Deshalb gilt dauerhaft:

- **Übernahme ist ein Werkzeug, kein Handgriff.** `scripts/reserve_intake.py`
  entscheidet nach Triage-Reife, Risikoklasse, Themen-Dublette, Eigentum und
  Faktenfrische – und schreibt **jede** Entscheidung mit Grund nach
  `data/reserve-intake.json`. Auch jede Ablehnung. Eine Übernahme ohne
  Begründung ist ein Testfehler.
- **YMYL bleibt beim Menschen.** Risikoklasse `erhoeht` (Versicherung,
  Kredit, Steuer) wird nie automatisch in den Pool gezogen. Ein hoher Zähler
  ist kein Qualitätsnachweis.
- **Löschen braucht einen Beweis.** Unheilbare Klasse **und** zwei Läufe
  Beleg (`RESERVE_JANITOR_HITS`) **und** Karenz
  (`RESERVE_JANITOR_KARENZ_TAGE`). Trockenläufe zählen nicht, derselbe
  `run_key` zählt einmal. Geschontes erscheint im `--md`-Bericht mit
  Einzelbegründung – nichts verschwindet lautlos.
- **Keine Heilung ohne geprüfte Deckung.** `reserve_blocker_klassen.py` ist
  die einzige Stelle, die „heilbar" definiert; `reserve_healer_coverage.py`
  prüft sie gegen die Kette. Fehlt die Deckung: Aufräumer rc=0 mit
  `::error::` (der Nachtlauf darf daran nicht sterben), Finisher rc=1 ohne
  Schreibzugriff.
- **Identität schlägt Namensähnlichkeit.** Das Custody-Gedächtnis
  schlüsselt datumslos; zwei Entwürfe können denselben Stamm tragen.
  `--heal` setzt die Fahne nur auf dem **gemerkten** Slug, namensgleiche
  Geschwister werden berichtet, nie adoptiert.
- **CTA- und Offenlegungsblöcke sind für Heiler tabu.** Der interne Linker
  verlinkt Fließtext, nie Werbekennzeichnung (`cta_ranges()`).
- **Neue Wachen sind uhrfest.** Selbsttests laufen gegen feste Probetage und
  stempeln Dateialter absolut (`selftest_clock.stempel`) – nie „JETZT minus n
  Tage". Beide Wachen dieses Vorgangs fielen genau daran im PR-Gate auf.
- Verträge: `BestandsaufnahmeTests`, `LoeschRechtTests`,
  `LoeschDeckungsWacheTests`, `TriageFensterTests`, `CustodyIdentitaetTests`,
  `LinkerCtaSperrzoneTests`, `UhrZwangDerReserveWachenTests` in
  `scripts/tests/test_reserve_pipeline.py`.
- Vorgangsbericht: `BOT-WATCHDOG-RESERVE-594-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

## Release-Scorecard: die Produktionswahrheit (seit 03.10.2026)

Das Repo hat viele Gates, Reports, Zustandsdateien und Wachen – stark, aber
ohne EINEN Wahrheitsort kann niemand auf einen Blick sagen, was
veröffentlicht, was blockiert, wer entscheidet und ob die live gegangene
Version wirklich die geprüfte war. Die Antwort ist die **Release-Scorecard**:

- **Eine Zeile pro Artikel, acht Dimensionen:** Technik · Quellen ·
  Faktenalter · Affiliate-Integrität · Redundanz · YMYL-Risiko · menschliche
  Freigabe · nächste Überprüfung. Sichtbar in `RELEASE-SCORECARD.md`,
  maschinenlesbar in `data/release_scorecard_state.json` (Siegel) und
  `data/release_scorecard_history.jsonl` (Verlauf).
- **SSOT ist deklarativ:** `data/release_scorecard.yaml` erklärt jeden Check
  mit `wirkung: blockiert|warnung` (Fragen 1+2), Besitz
  (`entscheidung: auto|human`), Eskalationsmatrix, Falsch-Positiv-Protokoll,
  Freigabeprozess und Siegel-Mechanik (Fragen 3–6). Die Datei ist menschlich
  kuratiert – die Maschine liest sie, schreibt sie nie.
- **Keine zweite Messregel (C19):** `scripts/release_scorecard.py` misst
  ausschließlich über die Collector-Funktionen des Publish-Gates und die
  Prüffunktionen der Fachwachen (`editorial_review_gate.evaluate_path`,
  `faktenfrische.faelligkeit`, `duplikat_guard`). Die Governance-Regel **C19**
  erzwingt Deckungsgleichheit – eine harte Gate-Familie, die nicht als
  blockierend deklariert ist, bricht den Build.
- **Beweislauf ohne Heilung (C15):** Die Scorecard setzt
  `publish_gate.DRY_RUN = True` und schreibt ausschließlich ihre eigenen
  Artefakte. Ein nicht führbarer Beweis heißt „nicht beweisbar“ – nie
  „bestanden“ (Exit 2).
- **Siegel (Frage 6):** Beim Deploy versiegelt sie jeden Live-Artikel
  (SHA-256 der Quelldatei + Dimensionen + Deploy-Commit); Drift nach der
  Versiegelung wird im nächsten Lauf sichtbar.
- **Ausnahmen sind befristet:** Falsch-Alarme über `ausnahmen` in der SSOT –
  Pflichtfelder, Ablaufdatum, Unterschrift; downgraden auf warnung, nie auf
  grün; `M2-siegel-bindung` und `T7-render-beweis` sind nie ausnehmbar.
- **Takt:** Deploy hart über die heutigen Kandidaten (`deploy.yml`, vor der
  Auslieferung) + täglich 07:07 MESZ über den Bestand
  (`release-scorecard.yml`, ein Ticket bei Rot, Schließen bei Grün – C4/C12/C14).
- Bedienung: `npm run release:scorecard` · `npm run release:bestand` ·
  `npm run release:artikel -- <slug>` · `npm run test:release`.
  Runbook mit den sechs Antworten: `docs/ANLEITUNG-RELEASE-SCORECARD.md`.

## Verpasste Slots werden nachgeholt, nicht beklagt (Slot-Wache, seit #601, 05.10.2026)

Am 05.10.2026 endete ein Publikationstag mit 1/2 LIVE, obwohl die
Kapazität grün war – GitHubs Scheduler hatte 4 von 7 planmäßigen Slots der
Content-Linie nie gestartet (Engine 06:10 + 17:40, Kadenz 10:35 + 16:35;
der 16:35er kam erst 2 h 47 min später als einziger). Ein Lauf, der nie
startet, wird nie rot. Das Repo kannte die Klasse von der Newsletter-
Kadenz-Wache (23.09.) – nur die Content-Linie hatte keinen Schutz.

- **Soll-Plan geparsed, nie abgetippt:** `scripts/slot_wache.py` liest die
  cron-Zeilen aus `content-engine-v2.yml` und `kadenz-endkontrolle.yml` –
  wer den Plan verschiebt, verschiebt die Wache mit. Nicht verstandene
  cron-Syntax wird abgelehnt und gemeldet, nie geraten.
- **Urteil:** Slot + 45 min Gnadenfrist ohne einzigen Laufversuch =
  verpasst. Ein FEHLGESCHLAGENER oder LAUFENDER Lauf bedient den Slot
  (laut, kein Auto-Retry) – dieselbe Disziplin wie bei der Newsletter-
  Kadenz-Wache.
- **Eingriff begrenzt:** nur an Publikationstagen (SSOT
  `cadence_guard.PUBLICATION_DAYS`), nur solange LIVE < Mindestziel, ein
  Nachhol-Dispatch je Workflow und Tick (`gh workflow run`, dieselbe
  Freigabestufe wie der Cron). Der Doppel-Fall ist harmlos: concurrency-
  Gruppe `content-bot` reiht ein, das Kadenz-Gate deckelt 2–3 LIVE.
- **Notmeldung:** Nach dem letzten Slot + Gnadenfrist mit offener Quote
  meldet die Wache das Defizit selbst (`engine_issue.py --deficit`, nur
  wenn noch kein offenes existiert) – der Alarm geht auch raus, wenn jeder
  Cron UND jeder Dispatch versagte.
- **Das Defizit-Issue nennt die Ursache:** `engine_issue._diagnose()`
  hängt das Slot-Protokoll des Tages an (Soll-Slots / verpasst / LIVE).
- **Eigener Takt:** `slot-wache.yml` tickt alle 20 Minuten (häufige Ticks
  überleben Tick-Verluste am selben Haken), beweist sich bei jedem Merge
  (push auf die eigenen Pfade) und steht in der Wacht-Liste des Fehler-
  Alertings sowie in `governance_contract.GUARDS`.
- Bedienung: `npm run engine:slots` (Trockenlauf) ·
  `npm run test:engine:slots` (Selbsttest + 29 Unit-Tests).
  Vorgangsbericht: `TAGESDEFIZIT-ENGINE-601-DAUERHEILUNG-PREMIUM-2026-10-05.md`.

## Eine Quote ist ein Zustand, kein Arbeitsauftrag (Zustandskanal, seit #608, 07.10.2026)

Der 05.10.2026 endete mit 1/2 LIVE. Das Fach-Issue **#601** existierte
korrekt – wurde aber um 21:21 durch den Reparatur-Merge #603 geschlossen
(„Closes #601“), obwohl der gemessene Tag rot blieb. Am 06.10. (Dienstag)
übersprang `engine_issue.py` den Tag vollständig („Kein Publikationstag“),
also gab es keinen offenen, frischen Fachkanal. Der um 00:55 UTC
nachgelieferte Montags-Slot der Kadenz-Endkontrolle meldete daraufhin
ehrlich rot („TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig“) –
und das zentrale Fehler-Alerting musste **fail-open** melden: Es legte das
generische Wartungs-Issue **#608** mit API-Key-/GitHub-/Transient-Runbook
an. Doppelte Buchführung und eine falsche Handlungsanweisung.

Die Ursache war keine Alarmregel, sondern eine **Besitzfrage**: Ein
Arbeitsauftrag ist mit einem Merge erledigt – ein Zustand nur durch eine
neue Messung. Deshalb gilt für `engine_issue.py` (und seine Aufrufer):

- **Besitzer** des Kanals `engine-deficit` ist die Messung selbst – nicht
  der Vorschlag, der die Ursache heilt, und nicht die Hand.
- **Kadenz: jeder Tag.** Gemessen wird immer der jüngste Publikationstag
  (SSOT `cadence_guard.letzter_publikationstag`) – auch Di/Do/Sa/So belegt
  die Produktions-Wache den Kanal (`npm run engine:deficit` zeigt den
  Zustand). Ein Ruhetag vergisst keinen offenen Zustand.
- **Schließpfad: nur die eigene Messung**, in zwei ehrlichen Fällen – Ziel
  am Tag selbst noch erreicht, oder der Fehltag ist vorbei (nicht
  nachholbar, kein Nachtragen von Inhalten) und ein folgender
  Publikationstag erreicht das Ziel nachweislich. Der Vermerk sagt das
  ausdrücklich; repariert wird die Ursache, nicht die Statistik.
- **Reopen:** Wurde der Kanal geschlossen, während der gemessene Tag rot
  war (Merge, Hand, Missverständnis), öffnet die nächste Messung ihn
  wieder – mit Begründung. Danach schließt er sich von selbst, sobald ein
  Publikationstag das Ziel erreicht: kein Dauerläufer.
- **Das zentrale Alerting hängt daran:** Nur wenn der offene Fachkanal für
  denselben Lauf frisch belegt ist, schweigt die generische Meldung
  (#602-Regel). Wer den Kanal an einem Tag nicht belegt, erzeugt am
  nächsten roten Lauf wieder ein generisches Wartungs-Issue – genau #608.
- **Vertrag:** Regel **C23** in `governance_contract.py` friert Besitz,
  Kalender-SSOT, Ruhetag-Messung, Reopen und Marker/Label ein; sabotierte
  Fassungen werden im Kontrakt-Selbsttest rot.
- Bedienung: `npm run engine:deficit` (Zustand, Trockenlauf) ·
  `npm run test:engine:deficit` (Selbsttest + 39 Unit-Tests).
  Vorgangsbericht: `WF-1F8C-608-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

## Beweisen ist nicht Fabrizieren (Beweis-Ledger-Isolation, C27, seit 07.10.2026)

`data/audit/*.jsonl` ist kein Logfile, sondern ein **versioniertes
Beweis-Ledger**: `history_guard.py` bewacht es als append-only (Regel H6), und
jede Zeile behauptet einen echten Betriebsvorgang. Am 07.10.2026 – beim Siegeln
der Auslieferungs-Heilung #610 – fiel auf, dass **drei Unit-Tests echte Zeilen
hineinschrieben**. Die teuerste stand seit dem 03.10.2026 im Buch:

```json
{"module": "publish_gate", "action": "gate",
 "input": {"candidates": ["2026-09-07-r5-live"]},
 "output": {"gated": ["2026-09-07-r5-live"], "demoted": ["2026-09-07-r5-live"]}}
```

Ein am Gate verworfener Live-Artikel, den es nie gab – `2026-09-07-r5-live` ist
eine Test-Fixture. Vier weitere Zeilen bescheinigten `GROQ_API_KEY` einen Erfolg
`via content-engine-v2`, obwohl in CI ausschließlich `pinterest-ai.yml` und
`pinterest-token.yml` `--record-success` aufrufen, und nur für
`PINTEREST_TOKEN_KEY`. Genau die „fremde Erfolgsmeldung", die `secrets_age_guard`
selbst als `declared_foreign` abwertet, stand damit als Beweis im Buch.

- **Die Lehre ist die Schwester von C15:** Dort darf ein Beweislauf nicht
  heilen, was er prüft. Hier darf er nicht behaupten, was nie geschah. Beides
  sind Fälle, in denen die Messung ihre eigene Grundlage verändert.
- **Warum drei Stellen nicht reichen:** `run_gate()` → `publish_gate` →
  **Subprozess** `affiliate_profi_check.py --json`. Ein `mock.patch.object` im
  Testprozess erreicht das Kind nicht. Deshalb liegt der Vertrag in der
  **Umgebung**, die sich in jedes Kind erbt:
  `FFC_AUDIT_DIR` (Ziel umlenken) und `FFC_AUDIT_DISABLE` (harter No-Op).
- **Eine Zeile fehlt nicht, sie liegt woanders:** Die Sandbox schaltet das
  Protokollieren nicht ab. `beweis_ledger_unangetastet()` liefert den Pfad, und
  die Tests lesen die umgelenkte Zeile ausdrücklich zurück – sonst ginge eine
  zu grobe Stummschaltung als Heilung durch (Schein-Sicherheit).
- **Die dritte Leckstelle war latent:** `pg.main()` schreibt den gate-Entscheid
  nur, wenn ein Kandidat scheitert. Greift die R5-Heilung, bleibt `gated` leer.
  Der Pfad ist damit zufallsabhängig – und gerade deshalb nicht durch
  „passiert bei mir nicht" widerlegt. Die committete Zeile vom 03.10.2026 ist
  der Beweis, dass er feuert.
- **Gebrauch in Tests:**
  ```python
  from repo_isolation import beweis_ledger_unangetastet

  with beweis_ledger_unangetastet("bestand_gate"):
      findings, errors = bg.run_gate()
  ```
  Der Block bricht mit AssertionError ab, sobald im echten `data/audit/` eine
  Zeile entsteht, wächst oder verschwindet – der Beweis läuft **nach** dem
  Block, also auch dann, wenn die Prüfung selbst wirft. Das ältere Muster
  `patch.object(audit_log, "log_event")` bleibt gültig.
- **Empirisch statt statisch:** `publication-reliability-tests.yml` prüft nach
  dem Suite-Lauf `git status --porcelain -- data/audit` und wird rot, wenn auch
  nur eine Zeile entsteht – auch nach einem fehlgeschlagenen Testlauf
  (`if: !cancelled()`). Eine statische Regel allein würde nur bekannte Muster
  finden; die Leitplanke findet jeden künftigen.
- **Vertrag:** Regel **C27** in `governance_contract.py` friert Engpass,
  Sandbox, Regressionstest und Leitplanke ein; sabotierte Fassungen werden im
  Kontrakt-Selbsttest rot. Die Wache in
  `test_audit_ledger_isolation.py` meldet zusätzlich jeden Test, der einen
  bekannten Einstieg (`bestand_gate.run_gate`, `secrets_age_guard
  ._record_success`, `publish_gate.main`, `audit_log.log_event`) ohne Sandbox
  aufruft – mit Datei und Zeile.
- Bedienung: `python3 scripts/audit_log.py --selftest` ·
  `python3 scripts/repo_isolation.py --selftest` ·
  `python3 -m unittest scripts.tests.test_audit_ledger_isolation`.
  Vorgangsbericht: `BEWEIS-LEDGER-ISOLATION-C27-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

## Die Klasse geht dem Kanal vor (Auslieferungs-SLO, C28, seit #611, 07.10.2026)

Am 05.10.2026 endete der Montag bei **1/2 LIVE** (der 19:22 UTC nachgelieferte
Slot rettete genau einen Artikel). Am 06.10. lief der öffentliche Nachweis
(`Publication Delivery`) zweimal rot – um 01:17 und 14:10 UTC. Der Beleg sagte
die Ursache selbst:

```json
{"day": "2026-10-05", "source": ["…preiswert-surfen…"], "delivered": ["…preiswert-surfen…"],
 "errors": [], "ok": false, "minimum": 2, "maximum": 3}
```

`delivered == source`, keine Fehler: **Die Auslieferung war vollständig – der
Bestand trug den Tag nicht.** Weil der rote Sammel-Schritt („Missing public
delivery is a failed run“) keine Ursache nannte, legte das zentrale
Fehler-Alerting das generische Wartungs-Issue **#611** mit API-Key-/Transient-
Runbook an, obwohl der Fachkanal `engine-deficit` (C23) längst existierte –
dieselbe Doppelmeldung wie #602/#608, nur beim zweiten Melder derselben Sache.

`ok` ist die Summe zweier Wahrheiten mit zwei Besitzern; der Beleg trägt sie
jetzt getrennt (`publication_check.klasse()`):

| Klasse | Bedeutung | Besitzer |
|---|---|---|
| `ok` | Tag bestätigt (Mindestziel…Maximum öffentlich) | niemand – grün |
| `quelle_unter` | Bestand unter dem Mindestziel des gemessenen Tages | Fachkanal `engine-deficit` (Nachfüllung) |
| `quelle_ueber` | Bestand über dem Tagesmaximum | Kadenz-Gate (stuft im Deploy zurück) |
| `auslieferung` | Bestand im Zielband, öffentlich fehlt etwas | Deploy/CDN, P1-Kanal (#610) |
| `unbekannt` | kein lesbarer Beleg | fail-closed laut |

- **Die Klasse ist additiv.** `ok` behält seine Bedeutung; kein Aufrufer
  verliert ein Feld. Zusätzlich steht die Klasse in der versionierten Historie
  (`data/publication-delivery-history.jsonl`), damit ein roter Tag später
  seinem Besitzer zuordenbar bleibt.
- **Der Workflow antwortet der Klasse**, nicht dem Sammel-Boolean: eigener
  roter Schritt je Klasse. Nur `quelle_unter` ruft den Defizit-Fachkanal und
  belegt ihn **vor** dem roten Exit (`engine_issue.py --deficit`); sein
  Schrittname trägt beide Kennwörter („TAGESDEFIZIT“ + „engine-deficit“), an
  denen die Stummschaltung des Alertings hängt (#602-Regel). Überschuss und
  Auslieferungsdefizit bleiben laut mit ehrlichem Namen.
- **Ein bestätigter Tag hat keine Klasse nötig:** `ok` wird zuerst geprüft,
  ein unbekannter Beleg ist niemals still.
- **Vertrag:** Regel **C28** in `governance_contract.py` friert Klasse,
  Schritt-Namen, Reihenfolge (Beleg vor rotem Exit) und die beidseitige
  Alerting-Zuordnung ein; sechs Kunstbefunde werden im Kontrakt-Selbsttest rot.
- Bedienung: `npm run delivery:klasse` (Klasse des gültigen Belegs) ·
  `npm run test:delivery` (Regressionen) ·
  `python3 scripts/publication_check.py --selftest` (Logik-Beweis, uhrfest) ·
  `python3 scripts/publication_check.py --online` (voller Nachweis).
  Vorgangsbericht: `WF-7C1F-611-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

## Ein harter Blocker braucht einen Heiler (Content-Reserve, C29, seit #612, 07.10.2026)

Der harte End-Gate der Reserve („Stock shortage must not look successful“) war
rot, weil der Vorrat bei **Ziel 6 / bereit 2** stand – und er hatte recht: fünf
der letzten sechs Läufe endeten so. Die Zertifizierung hatte korrekt abgelehnt;
die Ursachen lagen davor:

- **Ein fertiger Kandidat hing an einem Politur-Rest.** R11/R13/R14
  (Politur-Ruinen) entscheiden seit #482 über die Veröffentlichung, aber keine
  Kette durfte sie heilen. `2026-10-07-wie-smart-home-…` scheiterte einzig an
  einem `SATZ: `-Präfix vor einer vollständig intakten Tabellenzeile
  (Zertifikat 0,95) und wurde als `reserve_blocked` aus dem Pool genommen.
  `scripts/politur_ruine_heiler.py` heilt die drei Klassen jetzt **beweisbar**
  (Tor T1–T4: keine Ruine bleibt, keine neue, Frontmatter/Links/Shortcodes
  stabil, Wortzahl ≥ 97 % − belegter Verlust) und **idempotent** – R12/R16
  werden nur gemeldet, Raten wäre eine Fälschung. Er läuft in Reserve- und
  Live-Kette, in der Deckung (`--wirkungsprobe`) und unter Siegel (FEST).
- **Die Geburt maß die Publish-Regel nicht.** `profi_quality_ok` prüfte alles
  außer der Lesbarkeit (Flesch ≥ 60 ist seit #585 hart): sieben Kandidaten
  wurden mit 53,1–59,9 geboren und fielen später geschlossen durch.
  `generate_drafts.lesbarkeits_befund` misst gegen die **importierte** SSOT
  `readability_check.NEW_FLESCH_MIN` – keine zweite Zahl.
- **Der Retry war blind.** Die Befunde des Vorversuchs gingen nie an den
  nächsten Versuch. `generate_article_text(…, hinweise=…)` baut daraus einen
  **KORREKTUR-AUFTRAG** im Prompt; `engine_generate.try_generate` reicht ihn
  weiter.
- **Der Trend-Beweis starb mit dem roten Lauf.** Die Chronik-Zeile entstand
  nach dem einzigen Commit-Schritt (letzter CI-Eintrag: 02.10.). Jetzt schreibt
  `reserve_gate.py --chronik` **vor** der Sicherung und ist je `lauf` idempotent;
  der End-Gate am Ende schreibt nichts doppelt.

- **Vertrag:** Regel **C29** in `governance_contract.py` friert alle vier
  Lektionen am echten Baum ein (Geburtsmessung, Retry-Gedächtnis,
  Chronik-Reihenfolge, Ruinen-Heiler in Kette/Deckung/Wirkungsprobe); sabotierte
  Fassungen werden im Kontrakt-Selbsttest rot. Klassen und Löschrechte stehen in
  `reserve_blocker_klassen.GATE_BEFUNDE` – R12/R16 bleiben bewusst „unbekannt“
  (fail-closed, nichts wird gelöscht, was niemand heilen kann).
- Bedienung: `python3 scripts/politur_ruine_heiler.py --selftest` ·
  `--wirkungsprobe` (Wirkung je Klasse + Idempotenz) ·
  `--file <pfad>` (Trockenlauf) bzw. `--fix`. Tests:
  `python3 -m unittest scripts.tests.test_reserve_pipeline`.
  Vorgangsbericht: `WF-D4E0-612-DAUERHEILUNG-PREMIUM-2026-10-07.md`.

## Die Seite darf nie stumm sterben (Robustheit der Laufzeit, C31, seit 07.10.2026)

**Lehre aus vier Befunden, die kein Build-Gate sehen konnte.** Dieser Blog hat
zwei Fehlerklassen. Die lauten fangen die übrigen Wachen: Der Build bricht ab,
ein Gate wird rot, der Deploy bleibt liegen. Die stillen sind teurer, weil die
Seite **baut** – der Ausfall passiert erst im Browser, bei einem Leser, auf
einem Gerät, das hier niemand hat. Am 07.10.2026 lagen vier solcher Fälle real
im Bestand:

1. `ff-rechner.js` initialisierte alle Rechner einer Seite in einer Schleife
   **ohne Fangnetz**. Ein einziger Rechner mit unerwartetem Markup warf – und
   nahm den übrigen die Verdrahtung mit: Formular sichtbar, Absenden lädt die
   Seite neu, keine Rechnung.
2. Die Newsletter-Anmeldung wartete **unbegrenzt** auf den Worker: `fetch` ohne
   Zeitlimit, Knopf `disabled`. Hing der Worker, stand „Wird übermittelt …" für
   immer; wiederholen ging nicht, abbrechen auch nicht.
3. Der Service Worker öffnete seinen Cache außerhalb jedes `try/catch`. Wirft
   das Cache-API (volle Quota, privater Modus), lehnte `respondWith` ab – ein
   Request, der ohne den SW problemlos durchgegangen wäre, kam nicht an.
4. Der Kopier-Knopf meldete „copied!" **bevor** die Zwischenablage antwortete
   und ließ ein abgelehntes Promise zurück.

**Die Regel daraus:** Ein gefangener Fehler ist erst behoben, wenn der Leser
weiß, woran er ist. Ein Knopf, der nichts tut, ist schlechter als ein Satz, der
sagt, was geht und was nicht.

**Zwei Stufen, eine Wahrheit.** Stufe 1 ist der Bootstrap im `<head>`
(`layouts/_partials/extend_head.html`, **im vorhandenen** Consent-Skript – kein
zusätzliches Head-Kind, 58 ist die Lighthouse-Grenze): Er sieht jeden Fehler,
auch den der Inline-Skripte, und stellt `FFRobust.hole()` – Fetch mit
Zeitlimit, das **nie** ablehnt. Stufe 2 ist `static/premium/ff-robust.js`
(defer, Fuß des Body): Fehlergrenzen (`insel`), Speicher-Fangnetz (`ablage`),
ehrliche Zwischenablage, Diagnose (`bericht()`). Beide sind idempotent
(`R.boot`), beide first-party, beide ohne Versand nach außen.

**Was ein Agent beim Bauen eines interaktiven Bausteins tut:**

1. Fangnetz **je Instanz**, nicht je Seite: `FFRobust.insel('name', init,
   { ziel: ergebnisFeld })` oder ein eigenes `try/catch` pro Element.
2. Im Ausfall einen Satz: `role="status"`, Marke, keine Technik.
3. Jeder Netzaufruf über `FFRobust.hole(url, { zeitlimit, versuche, quelle })`;
   der Knopf wird im Fehlerfall wieder freigegeben.
4. Web Storage nur mit Fangnetz (`FFRobust.ablage` oder `try/catch`) – die Seite
   bleibt ohne Speicher bedienbar.
5. Kein `innerHTML` aus Text, kein `document.write`, kein `eval()`.

**Zwei Vertragspunkte, die nicht verhandelbar sind.** `opaque` (Antwort aus
einem `no-cors`-Fetch) ist **kein** Fehler: Sie sagt „durchgekommen, Inhalt
nicht lesbar" – die Newsletter-Anmeldung sendet bewusst `no-cors`, und
`test_kein_erfolgsversprechen` hält fest, dass sie deshalb nie einen Erfolg
behauptet. Und: Wiederholt wird nur bei `netz`, nie bei `zeitlimit` – ein
Request, der ins Zeitlimit lief, hat den Dienst schon beschäftigt.

**Wache:** `scripts/robustheits_gate.py` (R1–R13, `--selftest` mit 14
Sabotage-Proben und 4 Gegenproben, `--public` für die gebaute Wahrheit). Sie
läuft in `robustheit.yml` (Push/PR/Nacht) und im Deploy **vor** dem Build,
fail-closed. Sie heilt nie selbst: Ein Fangnetz, das sich selbst wieder
einhängt, wäre keines.

**Ausnahmen** stehen in `data/robustheit_ausnahmen.yaml` – begründet, mit
Entscheidung und **Fälligkeit**, im Bericht genannt. Eine Ausnahme ohne
Fälligkeit ist eine stille Abschaffung. Für die Frist gilt R13, und R13 ist aus
einem echten Befund entstanden: Die CI-Uhr-Probe
(`publication-reliability-tests.yml`, ganze Suite mit +97 Tagen) fand am
07.10.2026 einen Test, der `faellig` gegen `date.today()` maß – die Suite wäre
ab dem Stichtag **jeden Tag rot** geworden, ohne Code-Änderung. Deshalb: Fristen
werden gegen das **Entscheidungsdatum aus den Daten** gemessen (Spanne ≥ 97 und
≤ 730 Tage), eine abgelaufene Frist steht im **Bericht** und als `::warning`,
nie im Exit-Code (Vorbild `fristen_check.py`), und
`selftest_clock.py --trap-modul scripts.tests.test_robustheits_gate --offset 97`
läuft im Robustheits-Lauf mit. Wer einen Test schreibt, der die Wanduhr liest,
baut eine Zeitbombe – `scripts/selftest_clock.py` erklärt die Klasse. Aktuell eine: `head.html` (KRITISCH
versiegelt, R8) – der nackte `localStorage`-Zugriff dort ist PaperMod-Erbe und
durch `disableThemeToggle = true` tot; ihn zu ändern braucht eine menschliche
Signatur.

Runbook: `docs/ANLEITUNG-ROBUSTHEIT.md` · Befund und Beweis:
`ROBUSTHEIT-PREMIUM-2026-10-07.md`

## Ein doppelter Schlüssel ist eine Bau-Falle (FM-Grenzen, F7/C32, seit #643, 08.10.2026)

Am 08.10.2026 starb der Produktions-Deploy (Run `37755044113`, Push 09:12 UTC)
im Bauschritt an **fünf Reserve-Artikeln**, die aus einem Merge je zwei
`tags:`-Zeilen trugen. go-yaml bricht bei einem wiederholten Mapping-Schlüssel
**hart** ab (`mapping key "tags" already defined at [7:1]`), PyYAML liest
dieselbe Datei still weiter (der letzte Wert gewinnt) – FM-Grenze, Taxonomie
und **alle** Gate-Reporte waren grün, der Deploy starb erst dort, wo niemand
mehr heilen kann. Zwei Dinge waren daran lehrreich:

- **Der Parser-Kurzschluss war die Blindstelle.** Solange „der Block parst“ als
  „sauber“ galt, konnte ein doppelter Schlüssel nie auffallen: PyYAML
  akzeptiert ihn. Die Wache (`scripts/fm_boundary_guard.py`) scannt deshalb
  **zeilenweise** die Mapping-Ebenen (Regel **F7**) – Erkennung **vor** dem
  Parser-Kurzschluss, Sequenzlisten (`quellen: - id: …`) und Block-Skalare sind
  eigene Container bzw. Inhalt und bleiben ruhig.
- **Heilung muss verlustfrei sein und belegt werden.** Listen werden vereinigt
  (kein Element geht verloren), alles andere folgt der YAML-Leseregel: der
  letzte Wert gilt, das frühere Vorkommen fällt weg – **jede** Änderung steht
  im `FM-GRENZEN-REPORT.md`. `--fix` heilt F7 **vor** dem Build (deploy.yml,
  selbstheilend wie F6), `--check` bleibt fail-closed (PR-Kette), `--staged`
  prüft die **Blobs aus dem Index** statt des Arbeitsbaums, `--wirkungsprobe`
  beweist die Klasse am Fixture (Erkennen, verlustfreies Heilen, Fixpunkt).
- **Ein Schreiber darf die Falle nicht unsichtbar machen.** Wer nur das ERSTE
  Vorkommen ersetzt (`count=1`), lässt die zweite Zeile stehen: Sieht geheilt
  aus, stirbt weiter. Die Schlussregel `post_utils.doppel_freies_feld` gilt
  darum für jeden FM-Schreiber (keyword_optimizer, tag_governance,
  pinterest_pin_text_sync) – nach dem Schreiben existiert der Schlüssel genau
  einmal.
- **Vertrag:** Regel **C32** in `governance_contract.py` (Haus-Nummern C24/C31
  gehören anderen Verträgen) friert Wache, Reihenfolge (Heilen VOR dem Build),
  PR-Pfad, Schreiber-Regel und die lebende Wirkung ein – fünf Kunstbefunde
  werden im Kontrakt-Selbsttest rot, der echte Baum bleibt still.

Bedienung: `python3 scripts/fm_boundary_guard.py --selftest` · `--check` ·
`--fix` · `--staged` · `--wirkungsprobe`. Tests:
`python3 -m unittest scripts.tests.test_fm_boundaries`.
Vorgangsbericht: `WF-54C4-643-DAUERHEILUNG-PREMIUM-2026-10-08.md`.

## Ein Selbsttest urteilt über den Code, nicht über das Modell (KI-Probe, seit #138, 08.10.2026)

Engine-Lauf **#138** (Run `37694986440`, 07.10.2026 22:15 UTC) starb in Phase
0.5 mit Exit 2 – vor Phase 1, ohne Artikel, ohne Endabnahme. Kein Code war
kaputt: `requeue_quality_holds.py --selftest` rief den Lesbarkeits-Heiler mit
`ki=True` **ohne Attrappe** auf. Lokal und im PR-CI fehlen Schlüssel → grün. In
Phase 0.5 stehen seit WACHE-609 echte GROQ/GEMINI-Schlüssel → das Live-Modell
schrieb den „schlechten“ Fixture-Text gut um (Flesch 2.9 → 86) und der Test
urteilte „Hold unter der Schwelle wird freigegeben“. #136/#137 waren am selben
Tag grün, weil das Modell zufällig schlechter antwortete. Ein Münzwurf im
kritischen Pfad.

- **Regel:** Jeder Selbsttest führt seinen KI-Weg über die vorhandene Attrappe
  (`lesbarkeit_heiler.KI_CALL`, `satz_heiler.KI_CALL`, Modul-`chat` austauschen,
  Netz-Trigger über `schaltwerk_triggers.NETZ_TRIGGER`) und erreicht **nie**
  den echten Transport. „Offline, da kein Key im Selbsttest“ ist eine Annahme,
  keine Garantie – Schritte bekommen Schlüssel nachträglich (genau so entstand
  #138). Muster: `requeue_quality_holds._KiAttrappe` (zählt Aufrufe, stellt
  zurück, prüft stumm / Vertragsbruch / gelungen / gar nicht gefragt).
- **Leitplanke (empirisch):** `scripts/selftest_ki.py --trap-workflows` fährt in
  `publication-reliability-tests.yml` JEDEN Selbsttest, den ein Workflow
  aufruft, mit Attrappen-Schlüsseln (SSOT `data/ki_transportweg.yaml`) und
  gesperrtem Netz (Loopback frei). Jeder Netzversuch wird mit Datei und Zeile
  protokolliert – auch wenn der Aufrufer die Ausnahme schluckt. Stand
  08.10.2026: 98/98 grün.
- **Diagnose:** Phase 0.5 nennt per ERR-Falle den exakten Befehl als
  Annotation; die Engine-Endkontrolle kennt die Klasse **FRÜHABBRUCH** (ein
  Pflichtschritt vor der Endabnahme ist gestorben) statt „Endabnahme ohne
  Exit-Code“.
- Bedienung: `python3 scripts/selftest_ki.py --selftest` ·
  `python3 scripts/selftest_ki.py --trap scripts/<skript>.py` ·
  `python3 scripts/selftest_ki.py --liste` (🔑 = läuft heute schon mit Schlüssel) ·
  `python3 -m unittest scripts.tests.test_selftest_ki`.
  Vorgangsbericht: `CONTENT-ENGINE-138-DAUERHEILUNG-PREMIUM-2026-10-08.md`.

## Das Manifest ist der Bau-Eingang (Manifest-Wache, seit WF-7B6B / #654, 08.10.2026)

Am 08.10.2026 brach `npm ci` in Sekunde 1 ab: Ein Merge (#647) hatte `package.json`
als **ungültiges JSON** auf `main` zurückgelassen (fehlendes Komma, `pagefind` doppelt).
Der E2E-Lauf und von 10:41 bis 12:50 UTC jeder Produktions-Deploy wurden rot. Die
automatische Meldung riet zu API-Keys – die Ursache stand in Zeile 181.

- **Vor jedem `npm ci` / `npm install` läuft `scripts/manifest_guard.py`** – Selbsttest
  zuerst, fail-closed. Geprüft werden JSON, Konfliktmarker, doppelte Schlüssel, Form
  und Lock ↔ Manifest (Wurzel-Sync, Vollständigkeit, exakte Pins). Befund = Datei +
  Zeile + Ursache, in GitHub als Annotation an der Zeile.
- **Verdrahtet** in `deploy.yml` (direkt nach dem Merge-Marker-Schutz), `e2e.yml`,
  `design-varianten.yml`, `lesehilfen-gate.yml`, `robustheit.yml`,
  `themenwelten-gate.yml`, `werkbank.yml`. Ein neuer Workflow mit `npm ci` ohne Wache
  fällt in `test_manifest_guard.VerdrahtungTests` rot.
- **Eine Quelle:** alle Manifeste des Repos (Wurzel, `tools/ff-voice-*`). Die einzige
  begründete Ausnahme (`OHNE_LOCKFILE_ERLAUBT`, `newsletter-worker`) gilt nur für ihren Pfad.
- **Die Wache ersetzt `npm ci` nicht.** Versions-Ranges entscheidet npm.
- **Der Alarm** nennt bei Install- und Manifest-Fehlern die Manifest-Diagnose statt des
  API-Key-Rats (`alert-on-failure.yml`, `installFailed`; Verhalten in
  `scripts/tests/sim/alert_scoping_sim.mjs`, Szenarien #654 und Deploy).
- Lock neu erzeugen: `npm install --package-lock-only --ignore-scripts`, dann Manifest
  und Lock **gemeinsam** committen. Den Lock nie von Hand auf einen Pin setzen.
- Bedienung: `npm run manifest:check` · `python3 scripts/manifest_guard.py --ref <sha>`
  (Vorfall nachspielen). Runbook: `docs/ANLEITUNG-MANIFEST-WACHE.md`.
  Vorgangsbericht: `WF-7B6B-654-DAUERHEILUNG-PREMIUM-2026-10-08.md`.

## Wichtige Konventionen

- Commits: Conventional Style mit deutschprachiger Beschreibung
  (`feat:`, `fix(gate):`, `chore:` …) – siehe `git log`.
- Reports/Dokumentation: Deutsch, datierte Dateinamen im Root
  (`*-2026-09-12.md`), auto-generierte `*-REPORT.md` sind gegittet.
- CSS: `assets/css/extended/` lädt alphabetisch – `zzz-agency-polish.css`
  ist der Politur-Layer und bleibt zuletzt.
- Bilder: immer `width`/`height` (CLS-Gate), Varianten via
  `scripts/check_covers.py --fix`.
