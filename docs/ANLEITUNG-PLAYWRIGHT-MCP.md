# Playwright-MCP: Browserdiagnose nur auf Abruf

| Auftrag | Richtiger Weg |
|---|---|
| Recherche, Text, Code oder Prüfung ohne gerenderte Seite | Normale Sitzung. [`.mcp.json`](../.mcp.json) hat **keinen Server**: kein projektseitiger Playwright-Start, kein Browserkatalog. |
| Eine offene Frage zu einer gerenderten Seite | Den Projektagenten [`ff-browserdiagnose`](../.claude/agents/ff-browserdiagnose.md) für genau diesen Auftrag aufrufen. |
| Wiederholbare Prüfung oder Freigabe | Vorhandene [E2E-Specs](../e2e/) ausführen bzw. eine Regression dort festhalten. Ein MCP-Befund schließt kein Gate. |

## In Claude Code starten und beenden

Aus der **Projektwurzel** und in einem bewusst als vertrauenswürdig bestätigten Checkout arbeiten. Benötigt werden ein Client mit [agentengebundenen MCP-Servern und Hooks](https://code.claude.com/docs/en/sub-agents#scope-mcp-servers-to-a-subagent), `python3`, `npx` und ein lokal startbarer Browser. Fehlt Chrome, einen vorhandenen, verwalteten Chromium über `PLAYWRIGHT_MCP_EXECUTABLE_PATH` für die Sitzung angeben; bei fehlenden Voraussetzungen stoppen, nicht Rechte erweitern.

1. Ohne Browserauftrag einfach wie bisher starten. Nach der Umstellung alte Sitzungen beenden und neu öffnen. Ein selbst im Benutzerprofil eingetragener Playwright-Server gehört **nicht** zum Projektstandard; falls vorhanden, dort separat deaktivieren.
2. Für eine offene Browserfrage im Chat `@` tippen und **ff-browserdiagnose (agent)** auswählen. Beispiel: »Untersuche auf dem lokalen Build unter `/suche/`, welches Element die zweite Beschriftung „Suchbegriff“ liefert.« Alternativ eine einmalige Diagnosesitzung im Terminal öffnen:

   ```bash
   npm run mcp:check && claude --agent ff-browserdiagnose
   ```

3. Der Agent verbindet den Server über stdio; die Hauptunterhaltung erhält bei Delegation nur den Befund. Mit dem Ende des letzten nutzenden Agenten bzw. der Diagnosesitzung endet die Verbindung. Kein `claude mcp add`, kein Umschreiben der `.mcp.json`, kein Dienst im Hintergrund.

Für lokale Diagnosen muss der Build erreichbar sein. Falls er noch nicht läuft: `npm run build`, dann in einem separaten Terminal `node e2e/server.mjs` (Loopback `127.0.0.1:4173`; danach mit `Strg+C` beenden). Für **automatisierte Tests** startet und beendet Playwright den Testserver selbst.

## Kleiner Befund statt ganzer Seite

Der Server bleibt `@playwright/mcp@0.0.83`; der Agent bekommt **fünf Werkzeuge**, nicht sämtliche vom Server annoncierten Methoden. Kein Shell-Zugang, kein allgemeines Schreib- oder Upload-Werkzeug und kein frei ausführbarer Browsercode. `--snapshot-mode none` unterdrückt den **automatischen** Seitenbaum nach der Navigation, nicht die ausdrücklich angeforderte Momentaufnahme. `--codegen none` unterdrückt Codebeispiele, `--no-webmcp` zusätzliche von der Seite registrierte Werkzeuge.

| Werkzeug | Beispiel / Grenze |
|---|---|
| `browser_navigate` | `{"url":"http://127.0.0.1:4173/suche/"}` – Seite öffnen, nicht sofort den Baum anfordern. |
| `browser_find` | `{"text":"Suchbegriff"}` – bei bekanntem Text zuerst die Treffer mit kurzem Umfeld lesen. Ein fehlender Treffer beweist nicht, dass das Element fehlt. |
| `browser_snapshot` | `{"target":"#ff-suche-eingabe","depth":2}` – Referenz/Selektor gezielt prüfen. Ohne bekanntes Ziel ist z. B. `{"depth":2}` zulässig. |
| `browser_console_messages` | `{"level":"warning"}` oder `error`; keine komplette Info-Konsole. |
| `browser_network_requests` | `{"filter":"pagefind"}` – nur zur Fragestellung passende Requests. Für umfangreiche Protokolle einen lokalen Beleg anfordern. |

**Was technisch blockiert wird:** Ein `PreToolUse`-Hook **nur in diesem Agenten** lehnt einen Snapshot ohne Ziel, Tiefenlimit oder Belegdatei ab. Inline ist `depth`, wenn gesetzt, auf 1–3 begrenzt. Ein großer Zielbereich kann trotzdem viele Treffer liefern: bei umfangreichen Rohdaten `filename` verwenden. Ungefilterte Netzwerklisten gehen nur in eine Datei. Eine Ablehnung nennt die Korrektur; ein gültiger Aufruf überspringt **keine** Berechtigungsabfrage.

**Beleg statt Chat-Ausgabe:** z. B. `browser_snapshot({"filename":".cache/mcp/suche-befund.yml"})`. Explizite Dateinamen sind beim gepinnten Server **workspace-relativ**, nicht relativ zu `--output-dir`. Der Hook akzeptiert nur `.cache/mcp/<dateiname>` ab Projektwurzel, keine Umwege über Symlinks. Einen neuen, aussagekräftigen Dateinamen wählen. `.cache/mcp/` ist gitignoriert; keine Logs, Querystrings mit Nutzerdaten oder Screenshots in den Chat oder ins Repository kopieren. Antwortformat: **Seitenpfad · Element · Befund · Belegpfad (falls angelegt)**.

## Vom Befund zum Test

Sobald die Beobachtung reproduzierbar ist, endet die Erkundung. Für »Hat das Suchfeld den richtigen zugänglichen Namen?« gibt es bereits eine [Spec](../e2e/suche.spec.mjs): Sie prüft am tatsächlich benutzten Feld die Rolle `searchbox` und den vollständigen zugänglichen Namen `Suchbegriff`. Nach dem Build gezielt laufen lassen:

```bash
npm run test:suche:browser -- --project=desktop --grep 'Suchmaske ist beschriftet'
```

Für WCAG-Verstöße gilt weiterhin die [axe-Spec](../e2e/a11y-axe.spec.mjs); Ausnahmen, Siegel oder Freigaben werden nicht über ein Gespräch geändert.

## Andere MCP-Clients

Das Frontmatter des Agenten ist die **einzige gepflegte Startdefinition** (JSON ist gültiges YAML). Für einen Client mit expliziten Sitzungsprofilen das geprüfte MCP-JSON **nur bei Bedarf** exportieren:

```bash
mkdir -p .cache/mcp
python3 scripts/mcp_wache.py --export-profil > .cache/mcp/diagnose.json
```

Diese Datei nur der Browsersitzung übergeben und die Sitzung anschließend schließen; nicht in globale oder automatisch geladene Projekteinstellungen kopieren. Der Export enthält **nur den stdio-Server**: Werkzeugauswahl und Aufruf-Hook sind Clientfunktionen, kein Bestandteil des MCP-Serverformats. Die fünf Werkzeuge und entsprechende Aufrufregeln müssen im anderen Client separat einschränkbar sein. Fehlt das, für denselben begrenzten Diagnoseweg den Projektagenten bzw. die Specs verwenden. Fehlendes Vertrauen oder eine Organisationssperre nicht umgehen.

## Leitplanken und Prüfung

Die [MCP-Wache](../scripts/mcp_wache.py) bleibt im Governance-Vertrag C6. M1–M6 prüfen das **aktive** Profil weiter auf gültige Struktur, Geheimnisse, exakten Pin, erlaubten Server, Härtung und Platzhalter. M7 prüft zusätzlich den leeren Projektstandard, den engen Werkzeugkatalog, den Hook und die ausgabearmen Startargumente. Der Export liefert bei einem Befund keine Konfiguration.

```bash
npm run mcp:check     # echte Standard- und Diagnosekonfiguration, kein Browserstart
npm run test:mcp      # Selbsttest + Offline-Regressionen inkl. Aufruf-Hook
```

Nur Headless-Betrieb, isoliertes Profil, blockierte Service Worker und die zwei vorgesehenen Origins (`https://franksfinanzcheck.de`, `http://127.0.0.1:4173`). **`--allowed-origins` ist keine Sicherheitsgrenze** (u. a. Redirects). Keine Anmeldung, keine Secrets, kein freier Dateizugriff, keine Extension, kein Deploy. Erfordert ein Befund weitergehende Rechte, endet die Diagnose. Bei einem Pinwechsel die Wache, die tatsächlichen Tool-Schemata und die gezielte Browserprobe erneut prüfen.
