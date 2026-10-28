# FF SEO Spider

Eigenständiger, kostenlos nutzbarer Technical-SEO-Crawler als Ergänzung zu Hugos Build-Checks und dem vorhandenen SEO-Cockpit. Die Anwendung verwendet die Python-Standardbibliothek und die repository-eigene Snippet-Messung (`scripts/serp_limits.py`). Kein Screaming-Frog-Produkt, keine Lizenzumgehung und kein Anspruch auf vollständige Feature-Gleichheit mit einer kommerziellen SEO-Suite.

## Lokal starten

Im Repository-Root:

```bash
npm run seo:spider
```

Danach `http://127.0.0.1:8765` öffnen. Beenden mit `Strg+C`. Der Server bindet fest an `127.0.0.1`, prüft Cross-Origin-POSTs und persistiert keine Crawl-Daten.

## Crawl-Funktionen

- Same-host Spider und URL-Listenmodus, konfigurierbare Seitenobergrenze, Klicktiefe, Anfragepause, optionale `nofollow`-Verfolgung.
- `robots.txt` inklusive `Crawl-delay`; Sitemap- und Sitemap-Index-Dateien (bis zu 12) werden erkannt und mit gecrawlten URLs abgeglichen.
- Statuscodes, Weiterleitungen, Content-Type/-Größe, Antwortzeit, ETag, Last-Modified, Cache-Control, Server-Header und Noindex/X-Robots-Tag.
- Title, Description mit repository-eigener Zeichen-/Pixelmessung, Canonical-Konsistenz, H1/H2 und Heading-Sprünge, Sprache/Viewport, Open Graph, Twitter Cards, hreflang-Vorkommen, JSON-LD-Parsefehler und Schema-Typen.
- Wortanzahl, exakte Inhalts-Duplikate, doppelte Titel/Descriptions/Canonicals, Bilder und fehlende Alt-Texte.
- Interner und externer Linkgraph mit Ankertext/rel, Inlinks, Outlinks, Tiefe, leere Linktexte, bekannte defekte interne Ziele, Fragmentziele, Sitemap-Waisen und nicht gelistete indexierbare URLs.
- Such-/Issue-Filter, sortierbare Spalten, Seitenpaginierung, kompletter JSON-/Seiten-CSV-/Linkgraph-CSV-Export sowie Vorher/Nachher-Vergleich von Crawl-JSON-Berichten im Browser oder CLI. CSV-Zellen werden gegen Tabellenkalkulations-Formelinjektion geschützt.
- Optionale externe Linkprüfung per HEAD: höchstens 100 eindeutige Ziele, mindestens eine Sekunde zwischen Abfragen. Standardmäßig deaktiviert, da dabei Drittserver kontaktiert werden.

## Kommandozeile

```bash
npm run seo:spider:crawl -- --url https://franksfinanzcheck.de/ \
  --max-pages 500 --depth 10 --delay 0.5 --time-limit 900 \
  --json /tmp/seo-spider.json --csv /tmp/seo-spider-pages.csv \
  --links-csv /tmp/seo-spider-links.csv
```

Für den Verlauf einen früheren JSON-Bericht angeben: `--compare /pfad/zum/vorherigen.json --diff-json /tmp/seo-spider-diff.json`. Die interaktive Oberfläche kann ebenfalls einen früheren JSON-Export lokal im Browser vergleichen.

Weitere Optionen: `--sitemap URL`, `--seed-file datei.txt`, `--follow-nofollow`, `--check-external`, `--fail-on-errors`. URL-Listen sind zeilengetrennt; `#` am Zeilenanfang kommentiert eine Zeile. Externe Linkprüfung kann durch `--check-external` bewusst eingeschaltet werden.

## Automatischer Blog-Lauf

`.github/workflows/seo-spider-weekly.yml` prüft sonntags bis zu 500 Live-URLs, mit 0,5 Sekunden Mindestpause, 10 Sekunden Netzwerk-Timeout und 15 Minuten Gesamtbudget. Es erstellt JSON-, Seiten- und Linkgraph-CSV-Berichte als zeitlich befristetes GitHub-Actions-Artefakt (14 Tage), statt Ergebnisse in Blog-Inhalte oder Commits zu schreiben. HTTP-/Verbindungsfehler lassen den Workflow fehlschlagen; der Bericht wird dennoch, wenn vorhanden, hochgeladen. `workflow_dispatch` erlaubt manuelle Läufe.

## Kosten, Grenzen und Betrieb

- Keine bezahlte Crawl-API, kein Konto und keine externe SEO-Datenbank. Lokaler Betrieb benötigt nur den eigenen Rechner; der geplante Lauf verwendet die verfügbaren GitHub-Actions-Minuten und Artefaktquoten des Repositories. Das ist nicht pauschal ein unbegrenzter/garantiert kostenfreier Hostingdienst.
- Nur öffentliche HTTP-/HTTPS-Ziele. Private/lokale Adressen und domainfremde Weiterleitungen werden blockiert. Exakte Host-Grenze; keine Subdomain-Crawls.
- Antwort-Body-Limit 2 MB; 5.000 URL-Obergrenze; 900 Sekunden Standardzeitbudget.
- Kein JavaScript-Rendering/Headless Browser, Lighthouse, Core Web Vitals, Google Search Console, Backlink-Index, Keyword-/Suchvolumendaten oder SERP-Abfragen. Externe Links werden nicht standardmäßig geprüft.
- JSON-LD wird auf gültiges JSON geprüft, aber nicht vollständig fachlich gegen Schema.org-/Google-Richtlinien validiert. Wortzahl und Metadaten sind heuristische technische Hinweise, keine Rankingsignale.
- Der Crawler ändert keine Website-Dateien und ersetzt keine fachliche Priorisierung. Alle externen Prüfungen sind opt-in und erzeugen tatsächliche Requests an Zielserver.

## Tests

```bash
npm run test:seo:spider
```
