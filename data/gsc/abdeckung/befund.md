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
- ℹ️ **W11** 4 Linkziel(e) im Inhalt werden nicht gebaut (Entwurf oder gelöscht). Das Rendering zeigt dort nur Text – die Verlinkung ist wirkungslos: veröffentlichen oder entlinken.
- ℹ️ **W10** 9 Sitemap-URL(s) ohne `lastmod`. Google entscheidet dann selbst, wann neu gecrawlt wird – genau das Gegenteil von Crawl-Nachfrage (M2).

### Vertrag: noindex-Bestand und Gateways — 🟢 in Ordnung

- 5 noindex-Seiten im Inhalt, 6 im Vertrag (`NOINDEX_VERTRAG`), 20 Gateways.

### Kandidatenraum (Obergrenze für die 404-Erklärung)

- 284 historische URLs aus dem Bestand ableitbar; 122 dokumentiert (Weiterleitung oder bewusst 404), 162 ohne Entscheidung.
- Das ist eine **Obergrenze**, kein Nachweis: Ob Google eine dieser URLs je gesehen hat, sagt nur die Detail-Liste (M1).

### Redaktionelle Verlinkung

- 0 von 74 Inhaltsseiten ohne redaktionellen Inlink, 0 ohne ausgehenden Link, Median 6 ausgehende Links je Seite.
- Verlinkungsauftrag: 1 Quelle-Ziel-Paar (`--verlinkung --apply`).

### Links ins Leere

- `/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/` – 2 Quelle(n); die Seite wird nicht gebaut, der Link erscheint als Text.
- `/posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/` – 7 Quelle(n); die Seite wird nicht gebaut, der Link erscheint als Text.
- `/posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/` – 1 Quelle(n); die Seite wird nicht gebaut, der Link erscheint als Text.
- `/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/` – 4 Quelle(n); die Seite wird nicht gebaut, der Link erscheint als Text.

### Anfrage-Wellen (M2)

- Welle 1: 40 Seiten · Welle 2: 59 · Kontingent 200 Anfragen/Tag.

| Score | Seite | Impressionen | Inlinks | Grund |
|---|---|---|---|---|
| 8.88 | `/pillar/internet-dsl/` | 10 | 17 | verlinkt |
| 8.15 | `/posts/2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet/` | 6 | 2 | verlinkt |
| 7.31 | `/pillar/` | 5 | 2 | verlinkt |
| 6.63 | `/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/` | 1 | 3 | verlinkt |
| 6.62 | `/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/` | 2 | 4 | verlinkt |
| 6.35 | `/posts/2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan/` | 0 | 1 | nur ein Inlink |
| 6.28 | `/posts/2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke/` | 1 | 9 | verlinkt |
| 6.13 | `/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/` | 1 | 2 | verlinkt |
| 6.07 | `/posts/` | 2 | 1 | nur ein Inlink |
| 5.83 | `/` | 3 | 0 | kein redaktioneller Inlink |

### Sprünge im Verlauf

- **2026-10-17** · nicht_indexiert +59 – belegt (Repo): Saldo +32 Beitragsentwürfe am 2026-10-14 (36 neu zurückgestuft), Google meldet den Sprung 3 Tage später
- **2026-10-17** · indexiert -21 – belegt (Repo): Saldo +32 Beitragsentwürfe am 2026-10-14 (36 neu zurückgestuft), Google meldet den Sprung 3 Tage später

### Abnahme

| Kriterium | Ziel | Status | Messung |
|---|---|---|---|
| Gate grün (kein Rückschritt, kein Widerspruch) | sofort | ✅ | Gate: gruen |
| Abdeckungsbefund nicht älter als 14 Tage | laufend | ✅ | Stand 2026-10-19 (7 Tage alt) |
| 404er mit Nachfrage triagiert | sofort | 🛑 | 193 ohne Erklärung im Bestand |
| Indexquote steigt | 14 Tage | ❔ | 26.8 % bei 1 Momentaufnahme(n) |
| Seiten ohne redaktionellen Inlink | 30 Tage | ✅ | 0 Seiten |

### Maßnahmen (Auszug)

| ID | Dringlichkeit | Maßnahme | Beleg |
|---|---|---|---|
| M1 | P1 | 404-Detail-Liste einlesen und triagieren | Übersicht: 223 × 404 · erklärbar 30 · offen 193 |
| M2 | P1 | Crawl-Nachfrage für gefundene, nicht abgerufene Seiten | 69 „Gefunden – zurzeit nicht indexiert“ bei 99 indexierbaren Seiten |
| M3 | P2 | Redaktions-Queue für „gecrawlt, nicht indexiert“ | 4 × „Gecrawlt – zurzeit nicht indexiert“ |
| M4 | P2 | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 99 indexierbaren Seiten · mit Nachfrage: /posts/kuehlschrank-strom-sparen-einstellung/ (9 Impr.), /posts/2026-08-07-frugalismus-fuer-den-erfolg/ (8 Impr.), /posts/depot-umzug-steuerfrei-wechseln/ (1 Impr.), /posts/elementarschadenversicherung-hochwasser-starkregen/ (1 Impr.), /tags/haushaltsbuch/ (1 Impr.) |
| M7 | P2 | Sprung im Abdeckungsbericht erklären | Diagramm 2026-10-17: indexiert 138 → 117 |
| M9 | P2 | Indexquote als Zielgröße etablieren | 117 von 437 bekannten URLs |
| M5 | P3 | noindex-Bestand als Vertrag führen | 5 × robotsNoIndex in content/ · GSC 5 |
| M6 | P3 | robots.txt-Sperre der Gateways dokumentiert lassen | 18 blockiert bei 20 Gateways · 13 Roboter-Gruppen |
| M8 | P3 | Fehlende Detail-Listen nachziehen | 4 URL(s) triagierbar · fehlt: Nicht gefunden (404).csv, Gefunden – zurzeit nicht indexiert.csv, Seite mit Weiterleitung.csv … |

