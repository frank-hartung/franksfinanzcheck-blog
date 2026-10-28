# Befund Abdeckung

## Abdeckung (Search Console, Stand 2026-10-19, 9 Tage alt)

**Gesamtbild: 🟢 GRÜN** · Quelle: `google-search-console (Abdeckungsbericht, CSV-Export)` · Gegenprobe: `content/ (Näherung, kein Build gemessen)`

| Kennzahl | Wert |
|---|---|
| Bekannte URLs | 437 |
| davon indexiert | 117 (26.8 %) |
| davon nicht indexiert | 320 |
| indexierbare Seiten im Repo | 101 |
| Index-Puffer (Altlasten) | 16 |
| Impressionen im Zeitraum | 62 (2.07/Tag, 6 Tage ohne) |

| Grund | Seiten | Erwartung | Urteil |
|---|---|---|---|
| Nicht gefunden (404) | 223 | 32 | offen |
| Gefunden – zurzeit nicht indexiert | 69 | ≤ 101 | plausibel |
| Durch robots.txt-Datei blockiert | 18 | 20 | plausibel |
| Durch „noindex“-Tag ausgeschlossen | 5 | 5 | vollständig erklärt |
| Gecrawlt – zurzeit nicht indexiert | 4 | ≤ 101 | plausibel |
| Seite mit Weiterleitung | 1 | 250 | plausibel |

### Widersprüche

- ℹ️ **W5** 117 Seiten sind im Index, indexierbar sind 101 – 16 Einträge sind Altlasten (entfernte, weitergeleitete oder abgeschaltete URLs). Sie kosten kein Crawl-Budget mehr, verzerren aber jede Quote.
- ℹ️ **W11** 2 Linkziel(e) im Inhalt werden nicht gebaut (Entwurf oder gelöscht). Das Rendering zeigt dort nur Text – die Verlinkung ist wirkungslos: veröffentlichen oder entlinken.

### Vertrag: noindex-Bestand und Gateways — 🟢 in Ordnung

- 5 noindex-Seiten im Inhalt, 6 im Vertrag (`NOINDEX_VERTRAG`), 20 Gateways.

### Kandidatenraum (Obergrenze für die 404-Erklärung)

- 291 historische URLs aus dem Bestand ableitbar; 257 dokumentiert (Weiterleitung oder bewusst 404), 34 ohne Entscheidung.
- Das ist eine **Obergrenze**, kein Nachweis: Ob Google eine dieser URLs je gesehen hat, sagt nur die Detail-Liste (M1).

### Redaktionelle Verlinkung

- 2 von 76 Inhaltsseiten ohne redaktionellen Inlink, 0 ohne ausgehenden Link, Median 6 ausgehende Links je Seite.
- Verlinkungsauftrag: 5 Quelle-Ziel-Paare (`--verlinkung --apply`).

### Links ins Leere

- `/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/` – 2 Quelle(n); die Seite wird nicht gebaut, der Link erscheint als Text.
- `/posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/` – 1 Quelle(n); die Seite wird nicht gebaut, der Link erscheint als Text.

### Anfrage-Wellen (M2)

- Welle 1: 40 Seiten · Welle 2: 61 · Kontingent 200 Anfragen/Tag.

| Score | Seite | Impressionen | Inlinks | Grund |
|---|---|---|---|---|
| 11.0 | `/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/` | 54 | 2 | verlinkt |
| 7.54 | `/pillar/internet-dsl/` | 13 | 17 | verlinkt |
| 7.0 | `/posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/` | 0 | 0 | kein redaktioneller Inlink |
| 7.0 | `/posts/2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen/` | 0 | 0 | kein redaktioneller Inlink |
| 5.54 | `/pillar/` | 9 | 2 | verlinkt |
| 5.43 | `/impressum/` | 13 | 7 | verlinkt |
| 4.92 | `/datenschutz/` | 12 | 6 | verlinkt |
| 4.61 | `/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/` | 4 | 3 | verlinkt |
| 4.53 | `/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/` | 3 | 2 | verlinkt |
| 4.37 | `/posts/2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet/` | 2 | 2 | verlinkt |

### Sprünge im Verlauf

- **2026-10-17** · nicht_indexiert +59 – kein Beleg im Repo gefunden
- **2026-10-17** · indexiert -21 – Größenordnung passt – Ursache noch nicht belegt
  - Kandidat: Taxonomie-URLs (abgeschaltet) (25), Abweichung 19 %

### Abnahme

| Kriterium | Ziel | Status | Messung |
|---|---|---|---|
| Gate grün (kein Rückschritt, kein Widerspruch) | sofort | ✅ | Gate: gruen |
| Abdeckungsbefund nicht älter als 14 Tage | laufend | ✅ | Stand 2026-10-19 (9 Tage alt) |
| 404er mit Nachfrage triagiert | sofort | 🛑 | 191 ohne Erklärung im Bestand |
| Indexquote steigt | 14 Tage | ❔ | 26.8 % bei 1 Momentaufnahme(n) |
| Seiten ohne redaktionellen Inlink | 30 Tage | 🛑 | 2 Seiten |

### Maßnahmen (Auszug)

| ID | Dringlichkeit | Maßnahme | Beleg |
|---|---|---|---|
| M1 | P1 | 404-Detail-Liste einlesen und triagieren | Übersicht: 223 × 404 · erklärbar 32 · offen 191 |
| M2 | P1 | Crawl-Nachfrage für gefundene, nicht abgerufene Seiten | 69 „Gefunden – zurzeit nicht indexiert“ bei 101 indexierbaren Seiten |
| M10 | P2 | Neuen Abdeckungs-Export einlesen | Stand 2026-10-19 · 9 Tage alt |
| M3 | P2 | Redaktions-Queue für „gecrawlt, nicht indexiert“ | 4 × „Gecrawlt – zurzeit nicht indexiert“ |
| M4 | P2 | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 101 indexierbaren Seiten · mit Nachfrage: /posts/kuehlschrank-strom-sparen-einstellung/ (7 Impr.), /posts/2026-08-07-frugalismus-fuer-den-erfolg/ (6 Impr.), /posts/depot-umzug-steuerfrei-wechseln/ (1 Impr.), /posts/elementarschadenversicherung-hochwasser-starkregen/ (1 Impr.), /tags/ (1 Impr.) |
| M7 | P2 | Sprung im Abdeckungsbericht erklären | Diagramm 2026-10-17: indexiert 138 → 117 |
| M9 | P2 | Indexquote als Zielgröße etablieren | 117 von 437 bekannten URLs |
| M5 | P3 | noindex-Bestand als Vertrag führen | 5 × robotsNoIndex in content/ · GSC 5 |
| M6 | P3 | robots.txt-Sperre der Gateways dokumentiert lassen | 18 blockiert bei 20 Gateways · 13 Roboter-Gruppen |
| M8 | P3 | Fehlende Detail-Listen nachziehen | 4 URL(s) triagierbar · fehlt: Nicht gefunden (404).csv, Gefunden – zurzeit nicht indexiert.csv, Seite mit Weiterleitung.csv … |

