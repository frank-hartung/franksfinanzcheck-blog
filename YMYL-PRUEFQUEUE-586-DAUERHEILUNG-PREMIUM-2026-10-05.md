# Redaktionelle YMYL-Prüfqueue #586 — Dauerhafte Behebung auf Premium-Niveau

**Datum:** 2026-10-05 · **Issue:** #586 · **Gate:** `scripts/editorial_review_gate.py`
**Prüfer:** Redaktion FranksFinanzcheck (Typ: `redaktion-mit-externer-belegkette`)

> Auftrag: „Redaktionelle YMYL-Prüfqueue #586 – bitte dauerhaft auf Premium-Level
> einer Profi-Agentur beheben." Alle 10 Queue-Posten wurden Fachprüfung,
> Belegkettenaufbau, Faktencorrection, CTA-Entrückung, Zahlendokumentation und
> fassungsgebundener Versiegelung unterzogen. Ergebnis: **62 Artikel geprüft,
> 9/9 Hochrisiko freigegeben, 0 blockiert.**

---

## 1. Ergebnis des Gates (nach Behebung)

```
Redaktionelle Prüfung: 62 Artikel · 9 Hochrisiko · 9 freigegeben · 0 blockiert
```

| Artikel | Siegel (inhalt_sha256, gekürzt) |
|---|---|
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | `39dbe649…6830` |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | `0495f346…dc82f` |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | `411c3509…aeecf` |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | `3ddcc9b1…94a7b2` |
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | `5c5a6861…daae3` |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | `42b77ec1…4e416` |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | `09d4e433…239a5` |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | `48a4af68…28fe7e` |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | `68d76712…60151c` |

Jede Freigabe ist an den exakten Inhaltshaushalt gebunden (E17-Drift-Schutz):
Jede spätere Text-, Protokoll- oder Quellenänderung bricht das Siegel und
sperrt den Artikel automatisch wieder (fail-closed). Prüfdatum 2026-10-05,
nächste Review-Punkte 2026-11-19.

## 2. Faktenkorrekturen (vorher → nachher, mit Beleg)

| Artikel | Korrektur | Beleg |
|---|---|---|
| dein-haus | Versicherungssumme **750–850 €/m² → rund 650 €/m²** (übliche Empfehlung der Verbraucherzentrale) | VZ 13889 |
| dein-haus | Wohnfläche 90 m²: **67.500–76.500 € → rund 58.500 €** | VZ 13889 (90 m² × 650 €) |
| kfz | Regionalklassen 2026: „**über 400** der 413 Bezirke neu eingestuft" → **99 von 413** (51 Bezirke besser/5,3 Mio., 48 schlechter/5,0 Mio., 314 unverändert/32,1 Mio.; Kasko 2,6/2,1 Mio. korrekt) | GDV-Regionalstatistik 2026 (gdv.de 181646) |
| kfz | SF-0-Beitragssatz **230–260 % → ca. 100 %** (alt vermischte Grundbeitrag mit Jugendzuschlägen; Skala SF5/SF10/SF20/SF35 = 60/40/28/20 % bleibt) | VZ 11490 |
| ratenkredit | Durchschnittszins **8,54 % → 7,60 %** (Konsumentenkredite Neugeschäft, Juli 2026; alle 6 Fundstellen + Kurzantwort; „Anfang" → „Mitte 2026") | Bundesbank MFI-Zinsstatistik v. 02.09.2026 (Tabelle 2) |
| ratenkredit | Umschuldungs-Rechenbeispiel **900 € → 950 €** Zinsen (440+270+240) und **360 € → 410 €** Ersparnis | Nachrechnung, VZ 10409 |
| geld-sparen | Bankvergleichstabelle „Stand 2024" → **Stand: Oktober 2026**: DKB 0 € nur ab 700 € Geldeingang (sonst 4,50 €/Monat), N26 1,70 % Fremdwährung (statt „nach 200 €"), ING ohne veraltete 3,75-%-Tagesgeldzusage, Dispozinsen DKB 7,91–8,51 % / ING 9,14 % | BaFin-Kontenvergleich, Bankenpreislisten 2026 |

## 3. Belegketten (Alle Allowlist-Ränge 1–2, nur HTTPS, mit Abrufdatum)

- **Verbraucherzentrale:** 12605 (Versicherungsüberblick), 13891 (PHV), 13889
  (Hausrat/650 €/m²), 11490 (Kfz/30.11.), 62827 (Hochwasser), 10409 (Kredite),
  32448 (Restschuld), 10781 (Haustiere), 13888 (Unfall), 12943 + 50645
  (Zahnzusatz/Festzuschüsse 60/70/75 %)
- **GDV:** 104816 (Baukosten/Neuwert), Klimafolgenanpassung (Elementar),
  181646 (Regionalklassen 2026)
- **BaFin:** Produktseiten Haftpflicht (neue URL nach Relaunch),
  kontenvergleich.bafin.de (Dispo-/Überziehungszinsen je Bank)
- **Deutsche Bundesbank:** MFI-Zinsstatistik Juli 2026 (PDF, 02.09.2026)
- **Stiftung Warentest:** Hundekrankenversicherung-Vergleich (121 OP-Tarife,
  60 Prüfpunkte, 16.04.2025) — im Tierkranken-Artikel wörtlich verifiziert
- **gesetze-im-internet.de:** § 40 VVG (Sonderkündigung), § 502 BGB
  (Vorfälligkeit 1 %/0,5 %), GOT 2022 (1–3×/4× Satz, 59,50 € Notdienst)

Tote/veraltete URLs (u. a. alte BaFin-Haftpflicht-Seite, VZ-10642) wurden
komplett ersetzt; jede Quelle trägt Herausgeber und Abrufdatum 2026-10-05.

## 4. Prüfprotokoll je Artikel (Umfang)

| Artikel | Quellen | Verankerte Aussagen | Dokumentierte Zahlenstellen | Davon mit Rechenweg |
|---|---|---|---|---|
| privathaftpflicht | 3 | 4 | 13 | 1 |
| dein-haus | 3 | 4 | 22 | 5 |
| wohngebaeude | 3 | 4 | 14 | 3 |
| kfz | 3 | 5 | 34 | 3 |
| versicherung-update | 5 | 5 | 11 | 3 |
| ratenkredit | 5 | 5 | 45 | 10 |
| tierkranken | 3 | 5 | 25 | 5 |
| unfall | 2 | 5 | 20 | 5 |
| zahnzusatz | 2 | 5 | 30 | 5 |

Alle Rechenwege wurden extern nachgerechnet (Annuitäten, Staffeln,
Eigenanteile, Ersparnisse); Rundungstoleranzen sind im Protokoll ausgewiesen
(z. B. Ratentilgung 10,99 %: berechnet 11.686 €, Artikel rundet 11.750 €,
Toleranz < 1 %).

## 5. Strukturmaßnahmen (E15 — Trennung Werbung/Prüfung)

In allen 9 Hochrisiko-Artikeln wurde der Affiliate-CTA aus dem
Einstiegsbereich hinter die fachliche Grundlage (4–7 H2-Abschnitte,
600–1.100 Wörter Belegtiefe) verschoben. Reine Werbeversprechen ohne
Beleg bleiben gesperrt.

## 6. Dauerhaftigkeit

1. **Fail-closed-Gate:** Ohne Prüfer, Belegkette, Anker, Zahlenprotokoll,
   Prüfdatum, Änderungsgrund und Hash kein `draft: false` (E01–E19).
2. **Hash-Bindung:** Inhaltssiegel bricht bei jeder Änderung (E17).
3. **Review-Kalender:** Nächste Prüfung 2026-11-19 im Protokoll verankert.
4. **Queue-Datei:** `data/editorial_review_queue.json` zeigt 0 offene Posten;
   Historie in `data/editorial_review_history.jsonl` (9 Versiegelungen).

---
*Redaktion FranksFinanzcheck · Fachprüfung mit externer Belegkette ·
Prüfdatum 2026-10-05 · Nächste Prüfung 2026-11-19*
