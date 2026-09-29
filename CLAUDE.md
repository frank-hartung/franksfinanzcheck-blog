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
`data/schreibstil.yaml` unter `eigenstaendigkeit`; Generierung und Stilpolitur
müssen sie berücksichtigen.

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
python3 scripts/zeit_rechtschreibung.py --selftest   # ZEIT-Niveau-Rechtschreibungs-Wache (offline, Sabotage-Schutz)
npm run test:rechtschreibung                          # Selbsttest + 23 Unit-Tests der Wache
npm run offenlegung                                   # Build + Werbe-Offenlegung O1–O7 (artikelgenau, sichtbar)
npm run test:offenlegung                              # Selbsttest (13 Sabotage-Proben) + 36 Unit-Tests

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
- **CI in einem Schritt:** `workflow-ready/zeit-rechtschreibung.yml`
  montags 04:35 UTC – einmalig per Admin-Token nach
  `.github/workflows/` kopieren.
- Runbook + Datenschutz + Premium-Aktivierung:
  `docs/ANLEITUNG-ZEIT-RECHTSCHREIBUNG.md`.

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

## Tags kommen aus dem Register, nie aus Keywords (Wache seit 29.09.2026)

Die Search Console meldete 237 nicht indexierte Seiten. Ursache war nicht der
Content, sondern die Taxonomie-Automatik: beide Generatoren setzten
`tags = keywords[:4]`. Keywords sind long-tail und pro Artikel einmalig – jeder
Artikel prägte damit **vier neue Tags = acht nutzlose URLs** (Archiv +
`/page/1/`-Alias). Nach 63 Artikeln: 217 Roh-Tags, 147 Archive, 193 davon mit
genau einem Artikel, insgesamt 347 nicht indexierbare URLs auf 58 echte Seiten.

**Eine Quelle:** `data/seo/tag_register.yaml` – 25 kanonische Tags, jeder einem
Pillar zugeordnet, mit vollständiger Synonymliste. `tag_governance.tags_fuer()`
ist die **einzige** erlaubte Tag-Quelle für neuen Content (nutzen
`engine_generate.py` und `generate_drafts.py`). Ein Tag wird **nie erfunden**:
greift nichts, entscheidet die Redaktion über einen Registereintrag – oder der
Begriff bleibt ein Keyword. Keywords gehören ins `keywords`-Feld, wo sie Schema
und Related-Matching speisen, **ohne je eine URL zu bauen**.

**Zwei Wachen, zwei Ebenen:**
`python3 scripts/tag_governance.py` (T1–T8, **mit** `--apply`) prüft das
Frontmatter: unbekannte Tags, Synonyme statt kanonischer Namen, Thin-Archive
(< 2 Artikel), Tag-Menge, Sonderzeichen (U+202F/U+00A0 erzeugen kaputte Slugs),
Kategorie, tote Registerzeilen.
`python3 scripts/index_hygiene_gate.py` (H1–H8, **ohne** `--fix`) misst die
**Crawl-Fläche des Builds** gegen ein Budget: Sitemap-Deckung,
`/page/1/`-Aliase, Tag-Budget (max. 35), Kategorie-Archive, Verhältnis
indexierbar : nicht indexierbar (max. 2,0 : 1), kaputte Slugs, Waisenseiten,
`noindex` in der Sitemap.

**Merke:** `schema_seo_gate.py` S6 war die ganze Zeit grün – es fragt „trägt
dieses Archiv ein noindex?“, nicht „darf es dieses Archiv geben?“. Eine Seite
kann einzeln korrekt und in der Menge trotzdem ein Defekt sein. Deshalb misst
`index_hygiene_gate.py` Anzahlen, nicht Attribute.

**Nicht anfassen:** `[pagination] disableAliases = true` und der
`[taxonomies]`-Block ohne `category` in `hugo.toml` – beide sind dokumentierte
Index-Hygiene-Entscheidungen, keine Altlast. Bericht:
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

## Wichtige Konventionen

- Commits: Conventional Style mit deutschprachiger Beschreibung
  (`feat:`, `fix(gate):`, `chore:` …) – siehe `git log`.
- Reports/Dokumentation: Deutsch, datierte Dateinamen im Root
  (`*-2026-09-12.md`), auto-generierte `*-REPORT.md` sind gegittet.
- CSS: `assets/css/extended/` lädt alphabetisch – `zzz-agency-polish.css`
  ist der Politur-Layer und bleibt zuletzt.
- Bilder: immer `width`/`height` (CLS-Gate), Varianten via
  `scripts/check_covers.py --fix`.
