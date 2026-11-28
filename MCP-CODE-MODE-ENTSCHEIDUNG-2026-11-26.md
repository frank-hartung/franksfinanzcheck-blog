# Entscheidung: Playwright-MCP behalten, Cloudflare Code Mode nicht ausrollen

**Stand: 26.11.2026 · Geprüfter Repository-Stand: `84ee9f8`**

**Empfehlung: Keinen MCP-Server ersetzen und keinen Cloudflare-Tarif buchen.** Für FranksFinanzcheck ist der erste Sparhebel, dem Modell bei einer Browserdiagnose nur die benötigten Werkzeuge und Befunde zu zeigen. Code Mode lohnt einen Versuch, wenn danach regelmäßig mehrere große Zwischenergebnisse durch den Modellkontext laufen.

**Umsetzung von Punkt 1 (26.11.2026):** Der [Projektstandard](.mcp.json) enthält jetzt keinen Server. Nur der [Browserdiagnose-Agent](.claude/agents/ff-browserdiagnose.md) lädt Playwright mit fünf Werkzeugen, ohne automatischen Seitenbaum. Ein auf diesen Agenten beschränkter Hook prüft Snapshots, Protokolle und Belegpfade vor dem Aufruf. Start, Ausstieg und Spec-Nachweis stehen im [Runbook](docs/ANLEITUNG-PLAYWRIGHT-MCP.md). Die folgende Bestandsmessung ist die **Ausgangslage vor der Umstellung**; Verbrauchsmessung und Code-Mode-Pilot wurden nicht gestartet.

**Lokale Abnahme der Umsetzung:** `claude mcp list` meldete mit isoliertem Benutzerprofil keinen Server. Claude Code 2.1.332 lud die Agentendatei und bot einem lokalen Testgegenüber genau die fünf Diagnosewerkzeuge an; ein unbeschränkter Inline-Snapshot wurde vor der Ausführung abgewiesen. Mit dem gepinnten MCP-Server und Chromium lieferte die Navigation keinen Seitenbaum, `browser_find` den gesuchten Ausschnitt und `browser_snapshot` wahlweise den Zielknoten oder einen lokalen Dateiverweis. Die 35 MCP-Regressionstests und alle 184 Playwright-E2E-Tests bestanden. Das ist ein Funktionsnachweis, keine Hochrechnung auf Sitzungstokens.

## Was im geprüften Ausgangsstand konfiguriert war

Die [damalige Projektkonfiguration](https://github.com/frank-hartung/franksfinanzcheck-blog/blob/84ee9f82487a4a45355d22fa4b1019aa4abf85ab/.mcp.json) definiert genau einen Server: `playwright`, lokal über `npx`, mit dem exakten Paket-Pin `@playwright/mcp@0.0.83`. Der Browser nutzt ein isoliertes Profil; als Ziele sind die eigene Domain und der lokale Build eingetragen. Diese URL-Liste allein ist keine Sandbox. Der Server dient der **Erkundung**, nicht der Freigabe: Ein Agent kann etwa untersuchen, warum die Suche für einen Screenreader falsch beschriftet ist. Den reproduzierbaren Nachweis liefern weiterhin [Playwright-Specs und axe](e2e/a11y-axe.spec.mjs), nicht die Chat-Antwort. Das ist im [Diagnose-Runbook](docs/ANLEITUNG-PLAYWRIGHT-MCP.md) festgelegt.

[Agent Reach](docs/ANLEITUNG-AGENT-REACH.md) arbeitet hier bewusst über Skill und CLI; DataForSEO und Firecrawl sind [optionale Skill-Integrationen](.claude/skills/seo/SKILL.md), keine weiteren konfigurierten Server. Auch die Modellaufrufe der Redaktion über [`llm_client.py`](scripts/llm_client.py) werden durch einen Umbau des Diagnosewerkzeugs nicht kürzer. Private oder organisationsweite MCP-Profile außerhalb des Repos sind nicht Gegenstand dieser Inventur.

## Messung: Wie groß ist der Werkzeugkatalog?

| Auswahl aus dem tatsächlichen `tools/list` | Werkzeuge | UTF-8-Bytes | Referenz-Tokens (`o200k_base`) |
|---|---:|---:|---:|
| Vollständiger Playwright-Katalog mit den Projektargumenten | 25 | 17.591 | 3.764 |
| Nur Navigation, Textsuche, Snapshot, Konsole und Netzwerkliste | 5 | 3.852 | 797 |

Für die Messung wurde der gepinnte Server in einem temporären Verzeichnis per MCP initialisiert und nur `tools/list` abgefragt. Gezählt wurde das kompakte JSON-Array aus `name`, `description` und `inputSchema` in Serverreihenfolge, mit `tiktoken@1.0.22`. Die Vergleichsauswahl umfasst `browser_navigate`, `browser_find`, `browser_snapshot`, `browser_console_messages` und `browser_network_requests`. Kein Browser- oder Modellaufruf.

**2.967 Tokens weniger im Beispielkatalog sind keine Ersparnis pro Sitzung.** Der Client kann Definitionen bereits bedarfsgerecht laden, anders serialisieren oder cachen; das Modell kann anders tokenisieren. Es liegt keine vergleichende Verbrauchsmessung realer Diagnosen vor. Separat geprüft: `npm run mcp:check` sowie `npm run test:mcp` waren grün (Selbsttest und 21 Regressionstests).

## Was Cloudflare ändert – und was nicht

[Cloudflares Code Mode](https://blog.cloudflare.com/code-mode/) ändert die Art des Aufrufs, nicht das Protokoll: Das Modell schreibt Code für eine aus den MCP-Werkzeugen abgeleitete TypeScript-Schnittstelle. Der Code kann in einer Sandbox mehrere Antworten filtern und verknüpfen; nur der relevante Befund muss zurück ans Modell. Der Browser und seine Werkzeuge werden weiterhin gebraucht. Bei einer einzelnen kurzen Abfrage können Typbeschreibungen, generierter Code und Fehlerwiederholungen mehr Tokens kosten als der direkte Aufruf. Auch [Cloudflares Entscheidungshilfe](https://developers.cloudflare.com/agents/tools/codemode/) unterscheidet einfache Aufträge von solchen Ketten.

Die oft zitierten **99,9 %** betreffen den Vergleich der Werkzeugbeschreibungen für die **gesamte Cloudflare-API** mit deren `search`/`execute`-Schnittstelle ([Cloudflares Messung](https://blog.cloudflare.com/code-mode-mcp/)), nicht den Gesamtverbrauch einer Playwright-Sitzung. Ein gehosteter Worker hat zudem keinen direkten Zugriff auf den lokalen Build unter `127.0.0.1:4173` oder den lokalen `npx`-Prozess. Gehostete Dynamic Workers setzen laut [Preisdokumentation](https://developers.cloudflare.com/dynamic-workers/pricing/) einen Workers-Paid-Tarif voraus. Für diesen Versuch weder eine Browser-Brücke öffnen noch die [Kostensperre](data/kostensperre.yaml) lockern.

## Konkreter Auftrag und Abbruchkriterium

1. **Sofort, ohne Umbau:** Playwright nur für Browseraufträge laden; falls der Client Werkzeuge nachladen kann, mit der kleinen Diagnoseauswahl beginnen. Einen bekannten Text mit `browser_find` suchen, statt den ganzen Seitenbaum zu übertragen. Falls ein Snapshot nötig ist, `target` oder `depth` setzen. Rohbelege lokal unter `.cache/mcp` lassen; im Chat genügen Seitenpfad, betroffenes Element, Befund und Belegpfad. Wiederholbare Prüfungen als Spec ausführen. [MCP-Wache und Allowlist](scripts/mcp_wache.py) unverändert lassen.
2. **Bei den nächsten zehn Diagnosen messen:** Pro Aufgabe Modell, Zahl der abhängigen Aufrufe, Input-/Output-Tokens laut Client, Cache-Anteil, Wiederholungen, Dauer und korrekten Befund erfassen – keine Seiteninhalte oder Zugangsdaten protokollieren. Zeigt sich keine wiederkehrende, tokenintensive Diagnose, die über eine feste Spec hinausgeht, endet die Prüfung hier.
3. **Nur bei wiederkehrenden, mehrstufigen Fällen:** Den optimierten Direktaufruf (A) gegen einen lokalen Code-Mode-Prototyp (B) testen. Beispiel: Aus Seitenbaum, Konsole und Netzwerkliste die Ursache eines Suchfehlers eingrenzen. Beide Varianten erhalten dieselben bereinigten Testdaten als aufgezeichnete Werkzeugantworten, dieselbe Aufgabe, Modellversion und Cache-Bedingung. Die Sandbox bekommt nur die freigegebenen Leseoperationen, keinen freien Netzzugang, keine Secrets und keine Schreib- oder Deployrechte. Kein Produktionsdeploy.

**Vorgeschlagene Freigabeschwelle:** B nur für diese Aufgabenklasse übernehmen, wenn pro korrekter Diagnose **mindestens 30 % weniger Tokens** als bei A anfallen. Dafür die Input- und Output-Tokens aller Versuche addieren und durch die Zahl korrekter Diagnosen teilen. Die bekannten Fehler müssen weiterhin erkannt werden; es darf weder länger dauern noch zusätzliche Rechte oder Betriebskosten erfordern. Das ist ein Entscheidungskriterium, keine Prognose. Andernfalls den Versuch beenden; der direkte Playwright-Weg bleibt verfügbar.
