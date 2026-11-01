# Befund Abdeckung

## Abdeckung (Search Console, Stand 2026-10-19, 13 Tage alt)

**Gesamtbild: 🟢 GRÜN** · Quelle: `google-search-console (Abdeckungsbericht, CSV-Export)` · Gegenprobe: `public/sitemap.xml`

| Kennzahl | Wert |
|---|---|
| Bekannte URLs | 437 |
| davon indexiert | 117 (26.8 %) |
| davon nicht indexiert | 320 |
| indexierbare Seiten im Repo | 104 |
| Index-Puffer (Altlasten) | 13 |
| Impressionen im Zeitraum | 62 (2.07/Tag, 6 Tage ohne) |

| Bestand (am Build gemessen) | Wert |
|---|---|
| Gebaute URLs | 401 |
| davon indexierbar (Sitemap) | 104 |
| davon bewusst nicht indexierbar | 297 (davon 251 Weiterleitungsseiten) |
| Crawl-Fläche je indexierbarer Seite | 3.86 : 1 |
| Klassen nicht indexierbar | Weiterleitungsseiten 251, /go/-Gateways 20, Pager-Seiten 19, Newsletter-Funnel 4, Veröffentlichungskalender 1, Pinterest-Autorisierung 1, Suche 1 |
| Indexierbar nach Sektion | posts 74, werkzeuge 10, pillar 7, studien 2, übrige Einzelseiten 11 |
| Nicht-Index-Einträge je gebauter URL | 0.8 (im Rahmen des Bestands) |

| Grund | Seiten | Erwartung | Urteil |
|---|---|---|---|
| Nicht gefunden (404) | 223 | 30 | offen |
| Gefunden – zurzeit nicht indexiert | 69 | ≤ 104 | plausibel |
| Durch robots.txt-Datei blockiert | 18 | 20 | plausibel |
| Durch „noindex“-Tag ausgeschlossen | 5 | 5 | vollständig erklärt |
| Gecrawlt – zurzeit nicht indexiert | 4 | ≤ 104 | plausibel |
| Seite mit Weiterleitung | 1 | 251 | plausibel |

### Widersprüche

- ℹ️ **W5** 117 Seiten sind im Index, indexierbar sind 104 – 13 Einträge sind Altlasten (entfernte, weitergeleitete oder abgeschaltete URLs). Sie kosten kein Crawl-Budget mehr, verzerren aber jede Quote.

### Vertrag: noindex-Bestand und Gateways — 🟢 in Ordnung

- 5 noindex-Seiten im Inhalt, 6 im Vertrag (`NOINDEX_VERTRAG`), 20 Gateways.

### Kandidatenraum (Obergrenze für die 404-Erklärung)

- 296 historische URLs aus dem Bestand ableitbar; 258 dokumentiert (Weiterleitung oder bewusst 404), 38 ohne Entscheidung.
- Das ist eine **Obergrenze**, kein Nachweis: Ob Google eine dieser URLs je gesehen hat, sagt nur die Detail-Liste (M1).

### Redaktionelle Verlinkung

- 0 von 79 Inhaltsseiten ohne redaktionellen Inlink, 0 ohne ausgehenden Link, Median 6 ausgehende Links je Seite.
- Verlinkungsauftrag: 1 Quelle-Ziel-Paar (`--verlinkung --apply`).

### Anfrage-Wellen (M2)

- Welle 1: 40 Seiten · Welle 2: 64 · Kontingent 200 Anfragen/Tag.

| Score | Seite | Impressionen | Inlinks | Grund |
|---|---|---|---|---|
| 13.45 | `/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/` | 58 | 2 | verlinkt |
| 13.1 | `/pillar/internet-dsl/` | 52 | 17 | verlinkt |
| 9.02 | `/posts/2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/` | 17 | 7 | verlinkt |
| 8.51 | `/impressum/` | 14 | 7 | verlinkt |
| 8.44 | `/pillar/` | 9 | 2 | verlinkt |
| 8.42 | `/datenschutz/` | 14 | 6 | verlinkt |
| 7.78 | `/posts/2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle/` | 7 | 2 | verlinkt |
| 7.77 | `/pillar/konto-karten/` | 14 | 11 | verlinkt |
| 7.58 | `/pillar/versicherungen/` | 7 | 6 | verlinkt |
| 7.17 | `/posts/` | 5 | 1 | nur ein Inlink |

### Sprünge im Verlauf

- **2026-10-17** · nicht_indexiert +59 – kein Beleg im Repo gefunden
- **2026-10-17** · indexiert -21 – Größenordnung passt – Ursache noch nicht belegt
  - Kandidat: /go/-Gateways (20), Abweichung 5 %
  - Kandidat: Pager-Seiten (19), Abweichung 10 %
  - Kandidat: Taxonomie-URLs (abgeschaltet) (23), Abweichung 10 %

### Abnahme

| Kriterium | Ziel | Status | Messung |
|---|---|---|---|
| Gate grün (kein Rückschritt, kein Widerspruch) | sofort | ✅ | Gate: gruen |
| Abdeckungsbefund nicht älter als 14 Tage | laufend | ✅ | Stand 2026-10-19 (13 Tage alt) |
| 404er mit Nachfrage triagiert | sofort | 🛑 | 193 ohne Erklärung im Bestand |
| Indexquote steigt | 14 Tage | ❔ | 26.8 % bei 1 Momentaufnahme(n) |
| Seiten ohne redaktionellen Inlink | 30 Tage | ✅ | 0 Seiten |

### Maßnahmen (Auszug)

| ID | Dringlichkeit | Maßnahme | Beleg |
|---|---|---|---|
| M1 | P1 | 404-Detail-Liste einlesen und triagieren | Übersicht: 223 × 404 · erklärbar 30 · offen 193 |
| M2 | P1 | Crawl-Nachfrage für gefundene, nicht abgerufene Seiten | 69 „Gefunden – zurzeit nicht indexiert“ bei 104 indexierbaren Seiten |
| M10 | P2 | Neuen Abdeckungs-Export einlesen | Stand 2026-10-19 · 13 Tage alt |
| M3 | P2 | Redaktions-Queue für „gecrawlt, nicht indexiert“ | 4 × „Gecrawlt – zurzeit nicht indexiert“ |
| M4 | P2 | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 104 indexierbaren Seiten · mit Nachfrage: /posts/kuehlschrank-strom-sparen-einstellung/ (6 Impr.), /posts/2026-08-07-frugalismus-fuer-den-erfolg/ (4 Impr.), /posts/elementarschadenversicherung-hochwasser-starkregen/ (1 Impr.), /tags/ (1 Impr.), /tags/dns-server-%C3%A4ndern/ (1 Impr.) |
| M7 | P2 | Sprung im Abdeckungsbericht erklären | Diagramm 2026-10-17: indexiert 138 → 117 |
| M9 | P2 | Indexquote als Zielgröße etablieren | 117 von 437 bekannten URLs |
| M5 | P3 | noindex-Bestand als Vertrag führen | 5 × robotsNoIndex in content/ · GSC 5 |
| M6 | P3 | robots.txt-Sperre der Gateways dokumentiert lassen | 18 blockiert bei 20 Gateways · 13 Roboter-Gruppen |
| M8 | P3 | Fehlende Detail-Listen nachziehen | 4 URL(s) triagierbar · fehlt: Nicht gefunden (404).csv, Gefunden – zurzeit nicht indexiert.csv, Seite mit Weiterleitung.csv … |

