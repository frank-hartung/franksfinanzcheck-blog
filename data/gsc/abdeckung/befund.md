# Befund Abdeckung

## Abdeckung (Search Console, Stand 2026-10-19, 20 Tage alt)

**Gesamtbild: 🟢 GRÜN** · Quelle: `google-search-console (Abdeckungsbericht, CSV-Export)` · Gegenprobe: `content/ (Näherung, kein Build gemessen)`

| Kennzahl | Wert |
|---|---|
| Bekannte URLs | 437 |
| davon indexiert | 117 (26.8 %) |
| davon nicht indexiert | 320 |
| indexierbare Seiten im Repo | 109 |
| Index-Puffer (Altlasten) | 8 |
| Impressionen im Zeitraum | 62 (2.07/Tag, 6 Tage ohne) |

| Grund | Seiten | Erwartung | Urteil |
|---|---|---|---|
| Nicht gefunden (404) | 223 | 34 | offen |
| Gefunden – zurzeit nicht indexiert | 69 | ≤ 109 | plausibel |
| Durch robots.txt-Datei blockiert | 18 | 20 | plausibel |
| Durch „noindex“-Tag ausgeschlossen | 5 | 5 | vollständig erklärt |
| Gecrawlt – zurzeit nicht indexiert | 4 | ≤ 109 | plausibel |
| Seite mit Weiterleitung | 1 | 251 | plausibel |

### Widersprüche

- ℹ️ **W5** 117 Seiten sind im Index, indexierbar sind 109 – 8 Einträge sind Altlasten (entfernte, weitergeleitete oder abgeschaltete URLs). Sie kosten kein Crawl-Budget mehr, verzerren aber jede Quote.
- ℹ️ **W8** Der Abdeckungsbericht ist 20 Tage alt (Stand 2026-10-19). Die Search Console liefert ihn nur als CSV – ohne neuen Export misst dieser Befund die Vergangenheit.

### Vertrag: noindex-Bestand und Gateways — 🟢 in Ordnung

- 5 noindex-Seiten im Inhalt, 6 im Vertrag (`NOINDEX_VERTRAG`), 20 Gateways.

### Kandidatenraum (Obergrenze für die 404-Erklärung)

- 310 historische URLs aus dem Bestand ableitbar; 258 dokumentiert (Weiterleitung oder bewusst 404), 52 ohne Entscheidung.
- Das ist eine **Obergrenze**, kein Nachweis: Ob Google eine dieser URLs je gesehen hat, sagt nur die Detail-Liste (M1).

### Redaktionelle Verlinkung

- 0 von 84 Inhaltsseiten ohne redaktionellen Inlink, 0 ohne ausgehenden Link, Median 6 ausgehende Links je Seite.

### Anfrage-Wellen (M2)

- Welle 1: 40 Seiten · Welle 2: 69 · Kontingent 200 Anfragen/Tag.

| Score | Seite | Impressionen | Inlinks | Grund |
|---|---|---|---|---|
| 11.0 | `/pillar/internet-dsl/` | 151 | 17 | verlinkt |
| 11.0 | `/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/` | 59 | 2 | verlinkt |
| 9.0 | `/posts/2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/` | 24 | 7 | verlinkt |
| 8.33 | `/pillar/konto-karten/` | 22 | 11 | verlinkt |
| 7.55 | `/impressum/` | 20 | 7 | verlinkt |
| 6.44 | `/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/` | 9 | 4 | verlinkt |
| 6.04 | `/datenschutz/` | 15 | 6 | verlinkt |
| 6.03 | `/pillar/versicherungen/` | 13 | 9 | verlinkt |
| 5.94 | `/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/` | 8 | 6 | verlinkt |
| 5.83 | `/pillar/` | 10 | 2 | verlinkt |

### Sprünge im Verlauf

- **2026-10-17** · nicht_indexiert +59 – kein Beleg im Repo gefunden
- **2026-10-17** · indexiert -21 – Größenordnung passt – Ursache noch nicht belegt
  - Kandidat: Taxonomie-URLs (abgeschaltet) (27), Abweichung 29 %

### Abnahme

| Kriterium | Ziel | Status | Messung |
|---|---|---|---|
| Gate grün (kein Rückschritt, kein Widerspruch) | sofort | ✅ | Gate: gruen |
| Abdeckungsbefund nicht älter als 14 Tage | laufend | 🛑 | Stand 2026-10-19 (20 Tage alt) |
| 404er mit Nachfrage triagiert | sofort | 🛑 | 189 ohne Erklärung im Bestand |
| Indexquote steigt | 14 Tage | ❔ | 26.8 % bei 1 Momentaufnahme(n) |
| Seiten ohne redaktionellen Inlink | 30 Tage | ✅ | 0 Seiten |

### Maßnahmen (Auszug)

| ID | Dringlichkeit | Maßnahme | Beleg |
|---|---|---|---|
| M1 | P1 | 404-Detail-Liste einlesen und triagieren | Übersicht: 223 × 404 · erklärbar 34 · offen 189 |
| M2 | P1 | Crawl-Nachfrage für gefundene, nicht abgerufene Seiten | 69 „Gefunden – zurzeit nicht indexiert“ bei 109 indexierbaren Seiten |
| M10 | P2 | Neuen Abdeckungs-Export einlesen | Stand 2026-10-19 · 20 Tage alt |
| M3 | P2 | Redaktions-Queue für „gecrawlt, nicht indexiert“ | 4 × „Gecrawlt – zurzeit nicht indexiert“ |
| M4 | P2 | Index-Altlasten benennen statt mitzählen | 117 indexiert bei 109 indexierbaren Seiten · mit Nachfrage: /posts/kuehlschrank-strom-sparen-einstellung/ (4 Impr.), /posts/2026-08-07-frugalismus-fuer-den-erfolg/ (2 Impr.), /posts/elementarschadenversicherung-hochwasser-starkregen/ (2 Impr.), /tags/ (1 Impr.), /tags/dns-server-%C3%A4ndern/ (1 Impr.) |
| M7 | P2 | Sprung im Abdeckungsbericht erklären | Diagramm 2026-10-17: indexiert 138 → 117 |
| M9 | P2 | Indexquote als Zielgröße etablieren | 117 von 437 bekannten URLs |
| M5 | P3 | noindex-Bestand als Vertrag führen | 5 × robotsNoIndex in content/ · GSC 5 |
| M6 | P3 | robots.txt-Sperre der Gateways dokumentiert lassen | 18 blockiert bei 20 Gateways · 13 Roboter-Gruppen |
| M8 | P3 | Fehlende Detail-Listen nachziehen | 4 URL(s) triagierbar · fehlt: Nicht gefunden (404).csv, Gefunden – zurzeit nicht indexiert.csv, Seite mit Weiterleitung.csv … |

