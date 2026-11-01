# Prüfkatalog – jede Änderung, jedes Gate, jeder Befund

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Test- und Verifikations-Pipeline

```bash
hugo --destination public            # Build (Hugo Extended 0.164 nötig)
npm ci && npm run browser:setup      # einmalig: gepinntes Chromium + JS-Smoke-Test
npm run test:e2e                     # Build + Playwright-Tests (Desktop+Mobile)
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
python3 scripts/themen_nachschub_waechter.py           # Themennachschub: Vorlauf der AUTO-Bahn in Produktionstagen (C44)
npm run test:themen:nachschub                        # Nachschub-Wache: Selbsttest + Füllwort-Grenze + Diagnose-Tests
python3 scripts/release_scorecard.py                 # Release-Scorecard: acht Dimensionen je Live-Artikel + Siegel
python3 scripts/skript_syntax_wache.py --selftest    # Skript-Syntax: der LIEGENDE Stand kompiliert (#864)
python3 scripts/skript_syntax_wache.py              # alle Skripte prüfen (Exit 1 bei Fund)
python3 scripts/skript_syntax_heiler.py --fix --commit   # Syntaxfehler heilen (letzte gültige Fassung, auditiert)
npm run trigger:check                                # Trigger-Wache: was ein Lauf prüft, löst ihn auch aus (W1/W2/W3)
npm run test:trigger                                 # Selbsttest (Sabotage) + 17 Vertragstests, inkl. PyYAML-Gegenprobe
npm run kommando:probe                               # Kommando-Melder: würde dieser Prozess Annotationen senden?
npm run test:kommando                                # Fluchtschutz (ein Befund = eine Zeile), Teststille, Notausgang
python3 scripts/alert_router.py --selftest           # Routing-Regeln (Besitz/Kadenz/Schließpfad)
python3 scripts/zeit_rechtschreibung.py --selftest   # ZEIT-Niveau-Rechtschreibungs-Wache (offline, Sabotage-Schutz)
python3 scripts/grammar_check.py --selftest       # Grammatik LT1–LT6 (Wendungen + Kongruenz, offline)
python3 scripts/grammar_check.py --lexikon-pruefen  # Genus-Lexikon (SSOT der Kongruenz): Format + Suffix-Plausibilität
python3 scripts/grammar_check.py --fix             # Selbstheilung Fließtext/description, nur eindeutige Ziele
python3 scripts/grammar_check.py --fix-titel       # + Titel-Kongruenz (Cover-Marken-Lock, nur mit Beweis)
npm run test:grammatik                             # Selbsttest (20 Fälle) + Lexikon-Prüfung + Unit-Tests
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
npm run suchradar:probe                               # Suchradar: welcher Suchanbieter antwortet heute? (schlüssellos, 0 €)
npm run test:suchradar                                # Suchradar: Selbsttest (24 Blöcke) + 73 Unit-Tests (Budget, Cache, Kette, Parser)
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
npm run metadaten:check                          # Metadaten-Wache M1–M6: Titel, Description, lastmod, Pflichtfelder, Zahlenversprechen
npm run test:metadaten                               # Metadaten-Wache: Selbsttest (11 Proben) + 13 Unit-Tests
npm run covers:render-check                          # Cover-Render-Wache: jedes JPG gegen seinen Titel neu gerendert (pixelgenau)
npm run test:covers:render                           # Cover-Render-Wache: Selbsttest (Sabotage + Gegenprobe)

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
python3 scripts/figma_quality_gate.py                 # 36 Kriterien: Vertrag, Kontrast, Hashes, Plugin
node scripts/tests/figma_plugin_sim.mjs               # Plugin ohne Figma bauen (idempotent, offline)

# Barrierefreiheit, Web Vitals, Browser-Diagnose (26.10.2026)
# Details: docs/ANLEITUNG-A11Y-AXE.md · docs/ANLEITUNG-WEB-VITALS.md · docs/ANLEITUNG-PLAYWRIGHT-MCP.md
npm run test:a11y:browser                            # axe-core im gerenderten DOM (WCAG 2.1/2.2 AA, Desktop + Mobile)
python3 scripts/cwv_feld_wache.py                    # Felddaten (CrUX/PSI) – verbindlich, Exit 0/1/2
node scripts/lighthouse_live.mjs                     # Laborwerte der AUSGELIEFERTEN Seite (Diagnose)
python3 scripts/mcp_wache.py                         # .mcp.json: Pinning, Server-Allowlist, Ziele, Ablage
```

E2E-Architektur (Details in `e2e/`-Datei-Köpfen): zero-dependency
Static-Server (`e2e/server.mjs`), hermetische Produktions-URL-Umleitung
(`e2e/fixtures.mjs`), gemeinsamer Browser-Resolver mit gelocktem Chromium-Fallback
(`e2e/browser.mjs`). Mobile-Projekt: `browserName: 'chromium'` explizit setzen –
sonst startet Playwright heimlich WebKit (device-`defaultBrowserType`-Falle).

**Browser-Pflicht:** Ein merge-fähiger Stand hat den vollen Playwright-Lauf hinter
sich – „in dieser Sandbox nicht startbar" ist kein akzeptabler PR-Zustand. Der
Chromium-Fallback `@sparticuz/chromium` ist exakt in `package.json` und
`package-lock.json` gepinnt. Nach `npm ci` führt `npm run browser:setup` einen
Start- und JavaScript-Render-Smoke-Test aus. Projekt-CI und lokale Browser-Checks
brauchen dadurch keinen Zugriff auf `cdn.playwright.dev` und keinen flüchtigen
`npm i --no-save`-Workaround mehr. Runbook: `docs/ANLEITUNG-CHROMIUM.md`.
