# Google Search Console für franksfinanzcheck.de

Aktualisiert: 20.09.2026. Die frühere github.io-Anleitung ist ersetzt.
Der tatsächliche Verifikations- und Indexierungsstatus ist ohne Zugriff
auf dein Google-Konto **nicht bekannt**.

## 1. Richtige Property wählen

[Google Search Console](https://search.google.com/search-console) öffnen
und selbst mit dem berechtigten Google-Konto anmelden. Falls vorhanden,
die bestehende Property verwenden:

- **Domain-Property:** `franksfinanzcheck.de` (fasst Protokolle/Subdomains
  zusammen). Besitz über den von Google ausgegebenen DNS-TXT-Eintrag beim
  DNS-Anbieter bestätigen.
- **URL-Präfix-Property:** `https://franksfinanzcheck.de/` (nur dieses
  HTTPS-Präfix). Beispielsweise mit der von Google bereitgestellten
  HTML-Verifikationsdatei bestätigen. Datei unverändert unter `static/`
  ablegen, deployen, Erreichbarkeit prüfen, in GSC bestätigen.

Keine neue Property anlegen, wenn eine passende bereits existiert.
Keine Passwörter, OAuth-Tokens oder privaten Schlüssel in Chat/Git ablegen.

## 2. Sitemap einreichen

Unter **Sitemaps** die URL
`https://franksfinanzcheck.de/sitemap.xml` eintragen. Erst nach Deployment
der Änderungen den live ausgelieferten Inhalt prüfen. Ein lokaler grüner
Audit ist keine Aussage über den bereits veröffentlichten Stand.

Die Sitemap enthält Originalseiten, keine Tag-/Kategoriearchive und keine
Paginierung. Die URL-Anzahl verändert sich mit den Veröffentlichungen.
Google garantiert weder die Indexierung jeder URL noch eine feste Frist.

## 3. Indexierungs- und Performance-Basis schaffen

- URL-Prüfung für Startseite, `/posts/` und die sechs `/pillar/`-Ratgeber.
- Gewählte Canonical, Crawling-Status und Ausschlussgründe prüfen.
- Bei Bedarf einzelne **wesentlich aktualisierte** Seiten zur Indexierung
  anfragen; nicht täglich unveränderte URLs einreichen.
- **Leistung → Suchergebnisse:** Suchtyp Web, Zeitraum und Länderfilter
  konsistent halten. Klicks, Impressionen, CTR und Position vergleichen.
- Aktualisierungsdatum, Messfenster und Google-seitige Datenverzögerung
  dokumentieren. Nicht aus einem einzigen Tag einen Trend ableiten.

## 4. Kostenlos im SEO-Cockpit auswerten

**Leistung → Suchergebnisse → Exportieren → CSV**. ZIP entpacken und
Suchanfragen- oder Seiten-Datei im lokalen Cockpit importieren:

```bash
npm run seo:audit
npm run seo:serve
```

Anleitung: [SEO-Cockpit](ANLEITUNG-SEO-COCKPIT.md).
Der Import benötigt keine Search-Console-API, kein Google-Cloud-Projekt,
keinen OpenSEO-Account und keine Zugangsdaten. Es wird nichts hochgeladen.

## 5. Nächste redaktionelle Entscheidungen

Seiten mit ausreichend Impressionen und Position 4–20 zuerst ansehen.
Suchintention prüfen, konkrete Fakten/Quellen aktualisieren, intern passend
verlinken und erst danach Titles überarbeiten. Eine niedrige CTR kann auch
an Suchintention, SERP-Features oder Position liegen – nicht pauschal an
„schlechten Titeln“.

Für Bing kann dieselbe Sitemap zusätzlich in den
[Bing Webmaster Tools](https://www.bing.com/webmasters) hinterlegt werden.
Auch dort ist eine Indexierung nicht garantiert.
