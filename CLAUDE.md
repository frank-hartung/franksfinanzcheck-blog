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
npm run test:release                                 # Release-Scorecard: Selbsttest + 41 Unit-Tests (Produktionswahrheit)
python3 scripts/release_scorecard.py                 # Release-Scorecard: acht Dimensionen je Live-Artikel + Siegel
python3 scripts/alert_router.py --selftest           # Routing-Regeln (Besitz/Kadenz/Schließpfad)
python3 scripts/zeit_rechtschreibung.py --selftest   # ZEIT-Niveau-Rechtschreibungs-Wache (offline, Sabotage-Schutz)
npm run test:rechtschreibung                          # Selbsttest + 23 Unit-Tests der Wache
npm run offenlegung                                   # Build + Werbe-Offenlegung O1–O7 (artikelgenau, sichtbar)
npm run test:offenlegung                              # Selbsttest (13 Sabotage-Proben) + 36 Unit-Tests
npm run vergleiche:check                              # Bewertungsraster V1–V8: Selbsttest + Quellen + Build + HTML-Beweis
npm run test:vergleiche                               # Selbsttest der Vergleichs-Wache (10 Sabotage-Proben, offline)
npm run werkzeuge:check                               # Werkzeuge W1–W7: Selbsttest + Quelle + Build + public/
npm run test:werkzeuge                                # 18 Gate-Unit-Tests + 55 Rechenkern-Tests (jsdom)

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

**Beim Layout-Arbeiten:** Die Kennzeichnung hängt in **vier** Layouts
(`single.html`, `_default/single.html`, `pillar/single.html`,
`pillar/list.html` – letzteres mit `extraKeys`, weil Template-CTAs nicht in
`.Content` stehen). Sie muss im `<header>` bleiben: `python3
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

## Wichtige Konventionen

- Commits: Conventional Style mit deutschprachiger Beschreibung
  (`feat:`, `fix(gate):`, `chore:` …) – siehe `git log`.
- Reports/Dokumentation: Deutsch, datierte Dateinamen im Root
  (`*-2026-09-12.md`), auto-generierte `*-REPORT.md` sind gegittet.
- CSS: `assets/css/extended/` lädt alphabetisch – `zzz-agency-polish.css`
  ist der Politur-Layer und bleibt zuletzt.
- Bilder: immer `width`/`height` (CLS-Gate), Varianten via
  `scripts/check_covers.py --fix`.
