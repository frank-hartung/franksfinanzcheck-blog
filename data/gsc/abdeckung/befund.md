# Befund Abdeckung

## Abdeckung (Search Console, Stand 2026-10-19, 7 Tage alt)

**Gesamtbild: 🟢 GRÜN** · Quelle: `google-search-console (Abdeckungsbericht, CSV-Export)` · Gegenprobe: `public/sitemap.xml`

| Kennzahl | Wert |
|---|---|
| Bekannte URLs | 437 |
| davon indexiert | 117 (26.8 %) |
| davon nicht indexiert | 320 |
| indexierbare Seiten im Repo | 99 |
| Index-Puffer (Altlasten) | 18 |
| Impressionen im Zeitraum | 62 (2.07/Tag, 6 Tage ohne) |

| Bestand (am Build gemessen) | Wert |
|---|---|
| Gebaute URLs | 258 |
| davon indexierbar (Sitemap) | 99 |
| davon bewusst nicht indexierbar | 159 (davon 115 Weiterleitungsseiten) |
| Crawl-Fläche je indexierbarer Seite | 2.61 : 1 |
| Klassen nicht indexierbar | Weiterleitungsseiten 115, /go/-Gateways 20, Pager-Seiten 17, Newsletter-Funnel 4, Veröffentlichungskalender 1, Pinterest-Autorisierung 1, Suche 1 |
| Indexierbar nach Sektion | posts 69, werkzeuge 10, pillar 7, studien 2, übrige Einzelseiten 11 |
| Nicht-Index-Einträge je gebauter URL | 1.24 (mehr Einträge als URLs: überwiegend Historie) |

| Grund | Seiten | Erwartung | Urteil |
|---|---|---|---|
| Nicht gefunden (404) | 223 | 30 | offen |
| Gefunden – zurzeit nicht indexiert | 69 | ≤ 99 | plausibel |
| Durch robots.txt-Datei blockiert | 18 | 20 | plausibel |
| Durch „noindex“-Tag ausgeschlossen | 5 | 5 | vollständig erklärt |
| Gecrawlt – zurzeit nicht indexiert | 4 | ≤ 99 | plausibel |
| Seite mit Weiterleitung | 1 | 115 | plausibel |

### Widersprüche

- ℹ️ **W5** 117 Seiten sind im Index, indexierbar sind 99 – 18 Einträge sind Altlasten (entfernte, weitergeleitete oder abgeschaltete URLs). Sie kosten kein Crawl-Budget mehr, verzerren aber jede Quote.

### Maßnahmen (Auszug)

| ID | Dringlichkeit | Maßnahme | Beleg |
|---|---|---|---|
| M1 | P1 | 404-Detail-Liste einlesen und triagieren | Übersicht: 223 × 404 · erklärbar 30 · offen 193 |
| M2 | P1 | Crawl-Nachfrage für gefundene, nicht abgerufene Seiten | 69 „Gefunden – zurzeit nicht indexiert“ bei 99 indexierbaren Seiten |
| M3 | P2 | Redaktions-Queue für „gecrawlt, nicht indexiert“ | 4 × „Gecrawlt – zurzeit nicht indexiert“ |
| M4 | P2 | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 99 indexierbaren Seiten · mit Nachfrage: /posts/kuehlschrank-strom-sparen-einstellung/ (9 Impr.), /posts/2026-08-07-frugalismus-fuer-den-erfolg/ (8 Impr.), /posts/depot-umzug-steuerfrei-wechseln/ (1 Impr.), /posts/elementarschadenversicherung-hochwasser-starkregen/ (1 Impr.), /tags/haushaltsbuch/ (1 Impr.) |
| M7 | P2 | Sprung im Abdeckungsbericht erklären | Diagramm 2026-10-17: indexiert 138 → 117 |
| M8 | P2 | Detail-Exporte in den Tageslauf aufnehmen | Export enthält 0 Detail-Zeilen |
| M9 | P2 | Indexquote als Zielgröße etablieren | 117 von 437 bekannten URLs |
| M5 | P3 | noindex-Bestand als Vertrag führen | 5 × robotsNoIndex in content/ · GSC 5 |
| M6 | P3 | robots.txt-Sperre der Gateways dokumentiert lassen | 18 blockiert bei 20 Gateways · 13 Roboter-Gruppen |

