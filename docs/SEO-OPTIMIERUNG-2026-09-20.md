# SEO-Optimierung & kostenloser OpenSEO-inspirierter Nachbau

**Stand:** 20.09.2026 · **Website:** franksfinanzcheck.de

## Zusammenfassung

Ein eigenständiges, lokales SEO-Cockpit wurde im Repository implementiert.
Kein OpenSEO-Abo, keine kostenpflichtigen API-Aufrufe, keine Accountänderung
und keine zusätzlichen Skripte im Besucher-Blog. Es bildet sinnvolle
Onpage-/Site-Audit-Funktionen nach, **nicht** die vollständige OpenSEO-
Datenplattform. Die Änderungen liegen auf dem Arbeitsbranch; ein produktiver
Rollout und Google-seitige Auswirkungen sind damit noch nicht nachgewiesen.

## Messbarer Vorher-/Nachher-Vergleich

Beide Messungen mit Hugo Extended 0.164.0, Produktionskonfiguration und dem
neuen `seo_cockpit.py`. Ausgangslayouts und -inhalte wurden für die
Vergleichsmessung unverändert aus Git-Commit
`2da4f26ecc36c7d11edb1955fe24a258f11e5a3d` in ein isoliertes,
Git-ignoriertes Verzeichnis exportiert. Kein Vergleich mit erfundenen Rankings.

| Lokaler Messwert | Vorher | Nachher |
|---|---:|---:|
| Geprüfte HTML-Originalseiten (ohne Redirects/statische Hilfsseiten) | 215 | 198 |
| Per Meta-Robots indexierbare Seiten | 58 | 49 |
| URLs in der Sitemap | 48 | 49 |
| Indexierbare Originalseiten mit Sitemap-Abdeckung | 48 von 58 | 49 von 49 |
| P1-Befunde | 9 | 0 |
| P2-Befunde | 66 | 0 |
| P3-Hinweise | 7 | 0 |

**Einordnung:** Die Befundzähler sind keine Zahl unabhängiger Ursachen und
kein Ranking-Score. Der Paginationfehler erzeugte unter anderem doppelte
Metadaten, falsche Canonicals und unnötige Seiten. Weniger gebaute Seiten
bedeutet hier weniger fehlerhafte Listen-Kopien, nicht gelöschte Artikel.
Alle 37 veröffentlichten Artikel und sechs Themen-Ratgeber bleiben erhalten.

## Umgesetzte Verbesserungen

### 1. Pagination und Crawl-Hygiene

- `.RelPermalink` bleibt bei Hugos Folgeseiten die Basisadresse. Der frühere
  Regex konnte `/page/2/` deshalb nicht zuverlässig erkennen.
- `seo_context.html` initialisiert die Pagination mit **derselben
  Seitenauswahl wie die Listenansicht**, bevor der Head gerendert wird.
- Folgeseiten tragen nach bestehender Blog-Strategie `noindex, follow`,
  eigene Canonicals, eigene Open-Graph-URLs und Titles mit Seitenzahl.
- Keine `CollectionPage`-Auszeichnung für Folgeseiten als vermeintlich
  unveränderte zentrale Blog-Übersicht.
- Das vorhandene `schema_seo_gate.py` prüft jetzt auch Folgeseiten tatsächlich
  auf noindex; vorher war dies dokumentiert, aber in S6 nicht umgesetzt.

Diese noindex-Strategie wird bewusst aus dem vorhandenen Blog übernommen.
Sie ist kein allgemeines Gebot für jede paginierte Website. Artikel bleiben
über Themenwelten, Bloglisten und Sitemap erreichbar.

### 2. Sitemap und ehrliche Aktualität

- `/posts/` als bislang fehlenden zentralen Einstieg ergänzt.
- Ausschlüsse über `robotsNoIndex`/`sitemap.disable` auch für Hubs,
  Themen-Ratgeber, Rechtsseiten und Home berücksichtigt.
- Undatierte Über-/Rechtsseiten erben nicht mehr das Datum eines fremden
  neuen Artikels. Ohne belegtes Datum entfällt `lastmod`.
- Listen dürfen die Aktualität enthaltener veröffentlichter Artikel
  einschließlich belegter Änderungen abbilden. Zukunftsdaten werden nicht
  als heutige redaktionelle Änderung ausgegeben.
- Article-JSON-LD und Open Graph verwenden gemeinsame Publikations- und
  Änderungsdaten aus `article_dates.html`.

### 3. Suchdarstellung und Vertrauen

- Startseiten-Title beschreibt erstmals den Nutzen („Geld sparen im Alltag
  & Tarife vergleichen“) statt ausschließlich den Markennamen.
- Optionales `seoTitle` trennt Suchdarstellung und sichtbare Überschrift.
  HTML-Title, Open Graph und Twitter-Titel verwenden dieselbe Vorlage.
- Beschreibung des Ratgeber-Hubs auf 157 Zeichen verdichtet, ohne
  pauschales 2.000-Euro-Ersparnisversprechen in der Description.
- `max-image-preview:large` erlaubt größere Bildvorschauen für indexierbare
  Seiten; es garantiert keine Discover-Aufnahme.
- Autorenrolle im Article-Schema entspricht jetzt der vorhandenen
  Person-Auszeichnung: „Autor & Betreiber von FranksFinanzcheck“ statt
  einer zusätzlichen, dort nicht belegten Experten-/Redaktionsleiterrolle.
  Keine neuen Referenzen, Qualifikationen oder Tests erfunden.

### 4. Kostenloser Betrieb

- Standardbibliothek-Auditor, JSON- und gegen Formel-Injection gehärteter
  CSV-Export, Such-/Statusfilter, Linkgraph und Snippet-Werkstatt.
- Echter GSC-CSV-Import statt künstlicher Keyword-Volumina; deutsche und
  englische Exporte, gewichtete Position, nachvollziehbare Chancen-Heuristik.
- Dark Mode, mobile Navigation, Tastaturfokus und klare Fehler-/Leerzustände.
- Kein Upload der Suchdaten, keine Speicherung im Repository oder Browser-
  Storage. Content Security Policy blockiert Verbindungen.
- Bestehende Deploy-/CI-Workflows nicht geändert. Neue Befunde tragen
  `owner=human`, Priorität und `channel=seo-cockpit`. Kein unbeaufsichtigtes
  Umtexten und keine automatisch eröffneten Dauertickets.

## Verifikation

- Produktionsbuild mit `--minify --cleanDestinationDir` erfolgreich.
- Neues SEO-Cockpit: **198 geprüfte Seiten, 49 indexierbare Originalseiten,
  49 Sitemap-URLs, keine P1/P2/P3-Befunde** in seinen definierten Prüfungen.
- Bestehendes Schema-/SEO-Gate und Selbsttest ohne harte/weiche Befunde.
- Layout-Audit: **2.061 interne Links, keine defekten Ziele**; Bilder,
  Article-Schema, Descriptions und H1-Präsenz bestanden.
- 19 vorhandene Schema-Gate-Unit-Tests, 17 neue Python-Tests und neun
  CSV-/GSC-Parser-Tests erfolgreich.
- Fünf Cockpit-Browsertests: Navigation, Suche/Filter, Snippet-Übernahme,
  CSV-Import/Reset/Fehler, keine Übertragung beim Import, XSS-Text,
  mobile Breite 390 px und Dark Mode.
- 33 bestehende Blog-E2E-Tests plus drei neue SEO-Regressionstests
  erfolgreich. Die bestehende Suite filtert erwartete Drittanbieterfehler;
  das Cockpit lädt keine Drittanbieter-Ressourcen.
- Chromium-CDN in der Arbeitsumgebung nicht erreichbar; vorhandener
  Repository-Fallback über `@sparticuz/chromium` verwendet, nicht als
  neue Projektabhängigkeit eingetragen.

## Was als Nächstes professionell geprüft werden sollte

Kein Accountzugriff, keine Suchdaten und kein externer Live-Audit lagen vor.
Deshalb bleiben diese Aufgaben **offen**, auch bei null technischen Befunden:

| Priorität | Aufgabe | Zuständig (`owner`) | Kanal | Nachweis/Abschluss |
|---|---|---|---|---|
| P1 | Änderungen nach Review veröffentlichen; live Canonicals, HTTP-Status, Robots und Sitemap prüfen | human | seo-cockpit | Live-Stichprobe stimmt mit Build überein |
| P2 | Richtige GSC-Property, Indexierungsstatus und gewählte Canonicals prüfen | human | seo-cockpit | GSC-Nachweis, kein lokales Ersatzsignal |
| P2 | Einheitlichen 28-Tage-GSC-Export mit Zeitraum und Filtern sichern | human | seo-cockpit | CSV importiert, Ausgangswerte dokumentiert |
| P2 | Gaspreisgarantie-Artikel auf gleiche Suchintention untersuchen | human | seo-cockpit | Suchanfragen-/Seitenüberschneidungen geprüft; Entscheidung dokumentiert |
| P2 | YMYL-Review: Rechtsgrundlagen, Euro-Versprechen, Tarifstände und persönliche Erfahrungsnachweise | human | seo-cockpit | Primärquellen + Datum je relevanter Aussage |
| P2 | Core Web Vitals mit echten Felddaten/Live-Tests prüfen | human | seo-cockpit | LCP/INP/CLS mit Messfenster und Datenquelle |
| P3 | Nach 28 Tagen CTR/Klicks und Intent-Passung vergleichbarer URLs überprüfen | human | seo-cockpit | Vergleich mit identischen Filtern, Saisonalität berücksichtigt |

### Redaktionelle Priorisierung ohne erfundene Keyworddaten

- **Strom/Gas:** vorhandene Gaspreisgarantie-Artikel vom 10.08., 12.08. und
  24.08. auf Überschneidungen prüfen. Ähnliche Titel allein beweisen keine
  Kannibalisierung. Ohne GSC keine automatischen Zusammenlegungen/Redirects.
- **Herbst/Winter:** `/pillar/strom-sparen/` und die vorhandenen Heizkosten-,
  Heizungscheck- und Standby-Ratgeber zuerst auf aktuelle Rechenannahmen,
  Primärquellen und passende interne Verweise prüfen.
- **Versicherungen:** den bestehenden Kfz-Ratgeber vor der Wechselphase auf
  Vertragsjahre, Ausnahmen und belegte Ersparnisspannen prüfen, keine
  pauschale Frist für jeden Vertrag behaupten.
- **Vertrauen:** Erfahrungs- und Ersparnisbehauptungen nur stehen lassen,
  wenn nachvollziehbar belegt. Insbesondere die bestehende Aussage im
  Ratgeber-Hub zur gesetzlichen Absicherung von Energie **und Telefon**
  unter derselben EnWG-Norm benötigt einen separaten Rechtsquellencheck.
  Dieser technische Auftrag ersetzt keine Rechtsberatung.

Ein vollständiges Agenturmandat würde diese Schritte mit echten
Performance-, Wettbewerbs- und Qualitätsdaten ergänzen. Rankings,
Umsatzzuwächse, Indexierung und Rich Results werden nicht garantiert.

## Bedienung

[SEO-Cockpit starten und verwenden](ANLEITUNG-SEO-COCKPIT.md) ·
[Search Console einrichten](ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md)
