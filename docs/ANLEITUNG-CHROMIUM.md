# Chromium für gerenderte Prüfungen

**Ziel:** E2E-, SEO-Cockpit-, Design- und Werkbank-Browserprüfungen müssen auch
in Netzen laufen, die `cdn.playwright.dev` sperren. Chromium wird deshalb nicht
mehr als nicht versionierter Cache vorausgesetzt und nicht per `--no-save`
nachinstalliert.

## Einrichten und beweisen

Voraussetzung ist Node.js 22.17 oder neuer. Im Repository:

```bash
python3 scripts/manifest_guard.py --selftest
python3 scripts/manifest_guard.py
npm ci
npm run browser:setup
```

`npm run browser:setup` ist ein echter Smoke-Test, kein bloßer Dateicheck: Er
startet Chromium, öffnet eine Seite und prüft, dass JavaScript den DOM-Inhalt
verändert. Erfolg sieht ungefähr so aus:

```text
✅ Chromium bereit · 153.0.x · …/chromium
   JavaScript-Smoke-Test: bestanden · Playwright-CDN: nicht benötigt
```

Danach können die Browserprüfungen laufen, beispielsweise:

```bash
npm run test:e2e
npm run test:seo:browser
npm run design:messen basis
```

## Woher Chromium kommt

Der Resolver `e2e/browser.mjs` wählt deterministisch:

1. `FF_BROWSER_PATH` oder `CHROME_PATH`, wenn explizit gesetzt und vorhanden;
2. den Chromium aus dem Playwright-Cache, falls er schon vorhanden ist;
3. das im Root-`package.json` **und** `package-lock.json` exakt gepinnte
   `@sparticuz/chromium` (aktuell `153.0.0`, passend zur Playwright-Chromium-Major-Version).

Der Fallback bringt Chromium und die für schlanke Linux-Runner nötigen
Kompatibilitätsbibliotheken mit (Linux x64/arm64). Auf macOS/Windows nutzt der
Resolver stattdessen einen vorhandenen Playwright-Browser oder `CHROME_PATH`;
das Linux-Binary wird dort nicht irrtümlich gestartet. npm prüft das Archiv anhand der im Lockfile
hinterlegten Integrität. Das Browser-Binary wird erst bei Bedarf in einen
versionsspezifischen `/tmp`-Ordner entpackt; ein Dateilock verhindert Rennen
beim ersten parallelen Start und Upgrades können keinen alten Binary-Cache
wiederverwenden. Es wird nicht ins Git-Repository geschrieben. Für den
Fallback-Download ist `registry.npmjs.org` erforderlich, **nicht**
`cdn.playwright.dev`.

Jeder Pfad wird nach `stderr` protokolliert. Die E2E-Workflow-Jobs führen den
JavaScript-Smoke-Test nach `npm ci` aus, bevor sie gerenderte Tests starten.
Die auf `tools/ff-voice-browser` basierenden Tests verwenden weiterhin deren
eigenes gelocktes Browserpaket und brauchen ebenfalls keinen Playwright-CDN-
Download.

## Externen Browser bewusst wählen

Für einen bereits installierten und administrativ verwalteten Chromium lässt
sich ein konkreter Pfad übergeben:

```bash
CHROME_PATH="/usr/bin/chromium" npm run browser:setup
CHROME_PATH="/usr/bin/chromium" npm run test:e2e
```

Ein ungültiger Wert wird nicht still benutzt; der Resolver meldet ihn und
versucht die verwalteten Fallbacks. Der Smoke-Test ist bei einem kaputten oder
nicht startbaren Browser rot.

## Abgrenzung: Claude-SEO-Skill im Benutzerprofil

`~/.claude/skills/seo/scripts/claude-seo` liegt außerhalb dieses Repositories.
Der Repository-Resolver kann daher weder dieses globale Script ändern noch
seine private Browser-Erkennung überschreiben. Die hier beschriebene
Einrichtung behebt dauerhaft die gerenderten Prüfungen **dieses Projekts** und
seiner CI. Wenn genau der globale Skill weiterhin seine eigene Meldung ausgibt,
muss dessen Setup beziehungsweise Browserpfad separat konfiguriert werden;
`npm run browser:setup` allein ändert keine Dateien unter `~/.claude`.
