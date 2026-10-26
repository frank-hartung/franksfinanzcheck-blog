# Playwright MCP: der Browser als Diagnosewerkzeug für Agenten

**Ziel:** Ein KI-Agent kann in diesem Repo eine Seite öffnen, den
Accessibility-Baum lesen, ein Bildschirmfoto machen und ein Netzwerkprotokoll
ansehen – ohne dass dafür ein zweiter, ungepinnter Browserweg entsteht und ohne
dass Befunde aus einem Gespräch als Beweis gelten.

**Kurzfassung der Rollenverteilung:**

```
BEWEIS      Playwright-Specs, axe-core, Gates      deterministisch, blockierend, CI
DIAGNOSE    Playwright MCP                          erkundend, lokal, ohne Gate-Wirkung
```

MCP liefert **Hypothesen**. Eine Hypothese wird zur Zusicherung erst, wenn sie
als Spec, Skript oder Test im Repo steht. Ein Befund, der nur im Chat existiert,
verschwindet mit dem Chat.

## Konfiguration (`.mcp.json`)

Claude Code, Cursor und andere MCP-Clients lesen die Datei im Projektwurzel
automatisch:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y", "@playwright/mcp@0.0.83",
        "--headless",
        "--isolated",
        "--block-service-workers",
        "--console-level", "warning",
        "--output-dir", ".cache/mcp",
        "--allowed-origins", "https://franksfinanzcheck.de;http://127.0.0.1:4173"
      ]
    }
  }
}
```

Warum jedes Argument dasteht – und was es verhindert:

| Argument | Wirkung | Was ohne es passiert |
|---|---|---|
| `@playwright/mcp@0.0.83` | exakter Paketstand | `@latest` ist morgen ein anderes Programm; Werkzeugverhalten ändert sich unbemerkt |
| `--isolated` | Profil nur im Speicher | Profilreste (Cookies, Anmeldungen) liegen auf der Platte und wandern in spätere Läufe |
| `--block-service-workers` | Service Worker aus | Der SW-Cache liefert je nach `HUGO_JSDELIVR_SHA` alte Seiten – Diagnose am falschen Stand |
| `--headless` | kein Fenster | Auf Servern und in Containern startet sonst gar nichts |
| `--console-level warning` | nur Warnungen/Fehler | Info-Rauschen kostet Kontext und verdeckt den echten Fehler |
| `--output-dir .cache/mcp` | Belege in den ignorierten Ordner | Bildschirmfotos landen im Repo-Wurzel und werden Commit-Kandidaten |
| `--allowed-origins` | nur Produktion + lokaler Build | Der Browser dürfte jede URL laden (siehe Grenzen unten) |

Start ohne Client (zum Ausprobieren):

```bash
npx -y @playwright/mcp@0.0.83 --version    # muss 0.0.83 melden
npx -y @playwright/mcp@0.0.83 --help       # alle Schalter, nichts geraten
```

## Wofür er gedacht ist

- Ein A11y- oder Layout-Befund lässt sich nicht aus dem HTML erklären →
  Seite öffnen, Snapshot des Accessibility-Baums holen, gerendertes `aria` und
  die berechnete Farbe ansehen.
- Ein Gate ist rot, die Ursache unklar → nachstellen, Konsole und
  Netzwerkfehler lesen, **dann** eine Spec schreiben, die den Fehler festhält.
- Eine neue Seite prüfen, bevor ein Test dafür existiert (Reihenfolge:
  Diagnose → Heilung → Spec; nie Diagnose statt Spec).

## Wofür er ausdrücklich nicht gedacht ist

- **Keine Beweis-Ebene.** Kein Agent darf ein Gate mit „ich habe im Browser
  gesehen, dass …" schließen. Beweise sind reproduzierbar, sonst sind sie
  Meinungen.
- **Kein Deploy, kein Commit, kein Push.** Schreibende Schritte am Bestand
  laufen über die Skripte des Hauses, nicht über ein Gespräch.
- **Keine Geheimnisse.** Keine Tokens in Prompts, keine Anmeldung in
  Konten, keine `.env`-Inhalte. Der Browser ist auf zwei Origins begrenzt.
- **Keine Gates umgehen.** Ein MCP-Befund rechtfertigt keine Ausnahme in
  `data/a11y/axe_ausnahmen.json`.

## Grenzen, die man kennen muss

`--allowed-origins` ist laut Upstream **keine Sicherheitsgrenze**: Redirects
werden nicht geprüft, und der Server bindet nur an `localhost`. Die Grenze, die
wirklich hält, ist die Umgebung: MCP läuft lokal, mit einem isolierten Profil,
ohne Zugriff außerhalb des Arbeitsordners (kein
`--allow-unrestricted-file-access`). Wer mehr braucht, entscheidet das
bewusst – nicht per Default.

## Der Wächter

`.mcp.json` ist eine Abhängigkeit, eine Netzbefugnis und ein Dateizugriff in
einer Datei. Deshalb steht sie unter einer eigenen Wache:

```bash
python3 scripts/mcp_wache.py            # Arbeitsbaum prüfen (Exit 0/1)
python3 scripts/mcp_wache.py --json     # Maschinenausgabe
python3 scripts/mcp_wache.py --selftest # Sabotageproben, ohne Netz
npm run test:mcp                        # Selbsttest + Regressionstests
```

| Regel | Prüft |
|---|---|
| M1 Datei | `.mcp.json` existiert, ist gültiges JSON, hat `mcpServers` |
| M2 Geheimnis | kein Wert sieht wie ein Token aus; `${VAR}` ist erlaubt |
| M3 Pin | jedes Paket exakt (`paket@1.2.3`); `@latest`, `^`, `~`, `*` sind Befunde |
| M4 Erlaubt | nur Server aus der Allowlist (`playwright`); ein neuer Server ist eine Entscheidung |
| M5 Härtung | `--isolated`, `--block-service-workers`, `--headless`, `--output-dir` unter `.cache/`, `--allowed-origins` ohne `*` und ohne fremde Ziele; kein freier Dateizugriff, keine Extension |
| M6 Platzhalter | kein `CHANGE_ME`, `YOUR_`, `<…>` |

Die Wache steht in `GUARDS` (Governance-Kontrakt C6) – ihr Selbsttest läuft
also im Premium-Governance-Lauf mit. Eine Wache, die niemand verlangt, führt
irgendwann niemand aus.

## Abbruchbedingung

Der Einsatz endet und die Arbeit geht zurück in den Code, wenn eine dieser
Lagen eintritt:

1. **Der Befund ist reproduzierbar** → Spec schreiben (`e2e/`), nicht weiter
   klicken. Ab hier ist MCP nicht mehr zuständig.
2. **Es wird ein Zugang gebraucht** (Login, Token, fremde Domain, Datei außerhalb
   des Arbeitsordners) → **nein**. Das ist keine Diagnose mehr, sondern eine
   Befugniserweiterung; sie braucht eine Entscheidung des Inhabers.
3. **Es wird ein Ergebnis gebraucht, das ein Gate schließen soll** → **nein**.
   Gates schließen mit Läufen, nicht mit Gesprächen.
4. **Das Werkzeug antwortet anders als die gepinnte Version** (Versionsnummer
   nicht `0.0.83`) → Lauf abbrechen, `npm run test:mcp` prüfen. Ein anderer
   Stand ist eine andere Messung.
5. **Eine Änderung wäre nur an einer gesiegelten Datei möglich**
   (`data/integrity_lock.json`) → Patch dokumentieren
   (`docs/ANLEITUNG-A11Y-AXE.md`), Ausnahme mit Ablauf registrieren, Inhaber
   informieren.
