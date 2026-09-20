# Kostenloses SEO-Cockpit für FranksFinanzcheck

Stand: 20.09.2026. Eigenständige Implementierung, funktional von OpenSEO
inspiriert, keine Kopie seines Codes, keine Anbindung oder Zugehörigkeit.

## Starten

Voraussetzungen: Hugo **Extended 0.164.0**, Python **ab 3.11**, Node.js/npm.
Der Auditor selbst benötigt ausschließlich die Python-Standardbibliothek.

```bash
npm run seo:audit
npm run seo:serve
```

Im eigenen Browser `http://127.0.0.1:4174` öffnen. Server mit `Strg+C`
beenden. Alternativ `.cache/seo-cockpit/index.html` direkt im Browser öffnen;
auch ohne Webserver funktionieren Audit, Filter und Import. Der
Kopierknopf kann je nach Browser/Datei-Kontext verweigert werden; dann
werden die Frontmatter-Felder zum manuellen Kopieren angezeigt.

**Vor jeder Auswertung neu bauen:** Der Bericht ist ein Snapshot und
aktualisiert sich nicht selbst. `seo:audit` verwendet einen bereinigten
Produktionsbuild; Entwürfe/Zukunftsartikel bleiben gemäß Hugo-Konfiguration
unveröffentlicht. Bei Bedarf zunächst `source .venv/bin/activate`, wenn
Hugo in der lokalen virtuellen Python-Umgebung installiert wurde.

Für Arena-Vorschauen muss der Server auf `0.0.0.0` binden. Auf dem eigenen
Computer bindet `seo:serve` absichtlich nur auf `127.0.0.1`. Eine Vorschau ist
kein authentifiziertes Admin-Backend; nicht öffentlich als Verwaltungsbereich
deployen. `noindex` ist **kein Zugriffsschutz**.

## Fünf Arbeitsbereiche

1. **Überblick:** echte Anzahl geprüfter und laut HTML indexierbarer Seiten;
   P1/P2/P3-Befunde statt eines unbelegten „Google-SEO-Scores“.
2. **Maßnahmen:** Priorität, konkrete URL, Befund, Korrekturvorschlag und
   Verantwortungsart. P1 = zuerst technisch beheben; P2 = Struktur;
   P3 = redaktioneller Hinweis. Filter und CSV-Export.
3. **Seiten & Struktur:** Titel, Canonical im Audit-JSON, Sitemap-Zugehörigkeit,
   eingehende verlinkende Seiten, kürzeste Klicktiefe ab Startseite und
   Befundanzahl. Klicktiefe ignoriert Redirect-Ketten; „nicht erreicht“
   bedeutet nicht automatisch „Google kennt die Seite nicht“.
4. **Suchdaten & Chancen:** eigener GSC-CSV-Import, deutsche/englische
   Spalten, Kennzahlen und filterbare Chancenliste.
5. **Snippet-Werkstatt:** bestehende Metadaten auswählen, Änderungen
   ausprobieren, `seoTitle` und `description` als YAML-Felder kopieren.
   Vorhandene Felder **ersetzen**, keine doppelten YAML-Schlüssel einfügen.
   Bewusst keine automatische Veröffentlichung oder Änderung von Artikeln.

## Search Console importieren

1. Die Property `https://franksfinanzcheck.de/` beziehungsweise
   `sc-domain:franksfinanzcheck.de` in Google Search Console öffnen.
2. **Leistung → Suchergebnisse**, Suchtyp/Zeitraum/Land dokumentieren.
3. **Exportieren → CSV**. Ein heruntergeladenes ZIP vorher entpacken.
4. Im Cockpit **Suchdaten & Chancen → CSV-Datei auswählen**.
5. `Suchanfragen.csv`/`Queries.csv` oder `Seiten.csv`/`Pages.csv` auswählen.
   Datums-, Geräte- und Länder-Tabellen sind absichtlich keine gültigen
   Eingaben. Eine Datei bis maximal 5 MB; keine Excel-/ZIP-Datei.
6. Optional den im Export gewählten Zeitraum eintragen. Das Eingabefeld
   **filtert die Daten nicht**, sondern dokumentiert den gewählten Zeitraum.

Unterstützte Spalten: Suchanfragen/Häufigste Suchanfragen/Top queries/Query
oder Seiten/Häufigste Seiten/Top pages/Page, Klicks/Clicks,
Impressionen/Impressions, Position/Average position. CSV mit Komma,
Semikolon oder Tab; UTF-8 mit/ohne BOM. Zahlenformat anhand der Sprache des
Exports: Deutsch `1.234` und `8,5`, Englisch `1,234` und `8.5`.

CTR wird aus Klicks ÷ Impressionen errechnet. Die zusammengefasste Position
ist nach Impressionen gewichtet. Die Summen gelten **nur für die importierten
Zeilen**. Ausgelassene/anonymisierte Suchanfragen und Exportlimits führen zu
Abweichungen vom Property-Bericht. Impressionen sind kein Suchvolumen.

Die Chancen-Heuristik (Position 4–20, mindestens 100 Impressionen) ist ein
Arbeitsfilter, kein Rankingversprechen. Ergebnisse nach Impressionen
sortiert, Anzeige auf 1.000 Zeilen begrenzt; Kennzahlen verwenden alle
importierten Zeilen. Kein Keyword-Page-Mapping aus getrennten Exporten
erraten. Keine Zeitreihe und kein automatisches Rank-Tracking.

## Datenschutz und Sicherheit

- Auditor führt **keine Netzwerkanfragen** aus, liest nur den Build.
- CSV-Datei wird per Browser-File-API verarbeitet. Kein Upload, keine
  Cookies, kein LocalStorage/IndexedDB für Suchdaten, keine API-Schlüssel.
- CSV-Inhalte leben nur im aktuellen Tab. „Import löschen“ oder Neuladen
  entfernt sie. Auch JSON-/CSV-Audit-Downloads enthalten **keine GSC-Daten**.
- Content Security Policy verbietet Verbindungen (`connect-src 'none'`)
  und externe Skripte. Kein CDN, kein Tracking, keine externen Fonts.
- Importtexte/Metadaten werden als Text gerendert; eingebettetes JSON wird
  gegen `</script>`-Injection geschützt; CSV-Export neutralisiert Formeln.
- Ausgabe ausschließlich in `.cache/seo-cockpit/` (bereits Git-ignoriert),
  außerhalb von `static/`, `content/` und `public/`. Nicht hochladen.
- Keine Änderungen an Abos, Accounts, GitHub-Secrets oder Workflows.

## Prüfungen und Exits

```bash
npm run seo:check
npm run test:seo
# Browser einmalig installieren:
npm ci
npx playwright install chromium
npm run test:seo:browser
npm run test:e2e
```

`seo:check` liefert 1 bei P1-Befunden. Auditor: Exit 2 bei fehlendem Build,
ungültiger Sitemap oder anderen Eingabefehlern. P2/P3 stoppen den Prozess
nicht. Die Tools schreiben keine automatischen GitHub-Issues.
Alle Cockpit-Befunde tragen `owner=human`: Dieses Werkzeug heilt nicht
selbst, Änderungen benötigen den Betreiber beziehungsweise die Redaktion.
`owner=auto` bleibt im bestehenden Alarmrouting ausschließlich echten
Selbstheilern vorbehalten. Jeder Befund hat `severity` und
`channel=seo-cockpit`; es gibt keinen neuen dauerhaften Alarm-Workflow.

Vorhandene vertiefte Prüfung bleibt zusätzlich relevant:

```bash
python3 scripts/schema_seo_gate.py --json
python3 scripts/layout_audit.py
```

## Was dieses Werkzeug nicht behauptet

Keine Live-Erreichbarkeit, Google-Indexbestätigung, Backlink-Datenbank,
Wettbewerbermessung, Suchvolumen, Core-Web-Vitals-Feldmessung oder komplette
inhaltliche/rechtliche Prüfung. HTML-`index` bedeutet nur „Indexierung nicht
per Meta-Robots untersagt“. Google entscheidet unabhängig über Aufnahme,
Canonical und Rankings. Titel-/Description-Längen sind Orientierung, keine
starren Rankingfaktoren. JSON-LD-Syntax ist kein Rich-Result-Anspruch.

OpenSEO bietet weitere datenbankgestützte Funktionen. Sein vollständiges
Leistungsspektrum wird hier **nicht** nachgebildet. Dieser lokale Baustein
verursacht keine externen SEO-Dienstgebühren; eigene Infrastruktur und
bestehende CI-Kontingente bleiben davon unabhängig.
