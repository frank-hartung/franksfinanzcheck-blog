# Wartung · Lesbarkeit & Gestaltung · Vorgang WF-D0C9 #897 — Dauerheilung auf Highend-Agentur-Niveau

**Auftrag:** `Wartung · Lesbarkeit & Gestaltung · Vorgang WF-D0C9 #897 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 29.10.2026 · **Branch:** `arena/1d71adc0-franksfinanzcheck-blog` · **Basis:** `2e4c7ae` (`main`)
**Status:**LAUFEND – Phase 1 (Lesbarkeit): 8 von 25 Artikeln bearbeitet, 2 erfolgreich auf ≥62, Ø Flesch 66,4.

---

## 1. Forensischer Ist-Befund

### 1.1 Lesbarkeit: Der Live-Bestand hat Flesch-Lücken

Beim Lesbarkeits-Audit (Skript `readability_check.py`, Stand 29.10.2026) zeigt sich:

| Metrik | Ist | Soll | Bewertung |
|---|---|---|---|
| Ø Flesch gesamt | 66,4 | ≥ 62,0 | ✅ Boden ok |
| Ø Score gesamt | 97/100 | ≥ 75 | ✅ Boden ok |
| Artikel mit Flesch < 62 | **23** | **0** | 🔴 Problem |
| Artikel mit Flesch < 55 | 0 | **0** | ✅ Behoben |

Die 23 verbleibenden Artikel mit Flesch < 62 verteilen sich auf:
- Füllwörter und Nominalstil (die häufigste Ursache)
- Zu lange Sätze (> 14 Wörter durchschnittlich)
- Hohe Schachtelungstiefe (> 4,5 %)

### 1.2 Design: Systemdokumentation vorhanden, aber operative Lücken

Das Design-System ist in `DESIGN.md` dokumentiert. Es gibt:
- Farb-Tokens (hell & dunkel)
- Typografie-Spezifikation
- Abstands-Raster (8px-Skala)
- Elevation-Stufen
- Komponenten-Standards (Button, Card, Callout, etc.)

Offene Prüfpunkte:
- CSS-Dateien in `assets/css/extended/` müssen Korrespondenz mit DESIGN.md zeigen
- Dark-Mode-Konsistenz über alle Komponenten muss verifiziert sein
- Design-Varianten-Wache (`design-varianten.yml`) Filter prüfen

---

## 2. Lesbarkeits-Heilung: Fortschrittsstatus

### 2.1 Bearbeitete Artikel (9 von 25)

| # | Artikel | Flesch vorher | Flesch nachher | Status |
|---|---|---|---|---|
| 1 | `2026-10-28-dsl-und-internet-flat-guenstig-sicher` | 56,0 | 60,9 | 🔄 Noch unter 62 |
| 2 | `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | 61,6 | 61,6 | 🔄 Unverändert |
| 3 | `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | 60,4 | 64,0 | ✅ Erfolgreich |
| 4 | `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | 60,1 | 63,3 | ✅ Erfolgreich |
| 5 | `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | 60,4 | 60,6 | 🔄 Noch unter 62 |
| 6 | `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | 60,9 | 61,0 | 🔄 Noch unter 62 |
| 7 | `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | 60,7 | 60,7 | 🔄 Unverändert |
| 8 | `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | 61,3 | 61,6 | 🔄 Noch unter 62 |
| 9 | `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | 60,4 | 60,3 | 🔄 Unverändert |

**Erfolgreich auf ≥62:** 2 Artikel (DSL-Tarif, geringeren Monatskosten)

### 2.2 Verbleibende Artikel mit niedrigsten Scores (23 verbleibend)

Priorität für weitere Heilungen:

| Artikel | Flesch | Priorität |
|---|---|---|
| `2026-09-20-gasrechnung-senken-so-bereitest-du-di` | 60,3 | 🔴 Hoch |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-` | 60,5 | 🔴 Hoch |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinns` | 60,6 | 🔴 Hoch |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-te` | 61,3 | 🟡 Mittel |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufn` | 60,9 | 🔴 Hoch |

### 2.3 Heilungspattern (aus LESBARKEIT-LIVE-KONSISTENZ-PREMIUM-2026-10-05.md)

Beim Lesbarkeits-Update vom 05.10. wurden 9 Artikel auf Flesch ≥ 62 gebracht durch:

1. **Nominalstil → Verben:** „eine Prüfung durchführen" → „prüfen"
2. **Komposita → Alltagswörter:** „Bandbreitenanforderung" → „wie viel Geschwindigkeit"
3. **Satzlänge:** Von ~13 auf 8–10 Wörter
4. **Absätze:** Höchstens 3 Sätze
5. **Schachtelung:** Tiefe auf < 3 % reduzieren
6. **Tabellen, Listen, Links, CTAs, Affiliate-Hinweise:** Bleiben unangetastet
7. **NBSP vor €/%:** SOWIEDER geschützte Bindestriche

---

## 3. Gestaltungs-Heilung: CSS & Design-System

### 3.1 CSS-Versionsprüfung

Die CSS-Dateien in `assets/css/extended/` sind:

| Datei | Inhalt | Prüfpunkt |
|---|---|---|
| `custom.css` | Basis-Tokens, :root | Korrespondenz mit DESIGN.md §1–§4 |
| `z-premium-blog.css` | Blog-spezifische Typografie | Abstands-Raster dokumentieren |
| `zz-agency-polish.css` | Agentur-Polish, Klassen | Design-Varianten-Konsistenz |
| `zzz-seo-und-teilen.css` | SEO/sparing | Meta-Titel-Kontrast |
| … | weitere Dateien | Jede auf Konsistenz checken |

### 3.2 Abnahmekriterien Design

1. Alle Farb-Tokens aus DESIGN.md §1 haben eine CSS-Entsprechung
2. Dark-Mode hat für jede Komponente einen definierten Zustand
3. Kontraste werden gemessen (Skript `e2e/design-metrics.mjs`,Requires Playwright)
4. Design-Varianten-Wache läuft sauber (Filter prüfen)

---

## 4. Ablaufplan

### Phase 1: Lesbarkeit (priorisiert)

| Schritt | Aktion | Artikelliste |
|---|---|---|
| 1 | Stufe-1-Artikel umschreiben | 5 Artikel mit Flesch < 58 |
| 2 | Stufe-2-Artikel umschreiben | 20 Artikel mit Flesch 58–62 |
| 3 | Gate-Check | `python3 scripts/readability_check.py --gate-bestand` → Exit 0 |
| 4 | Dokumentation der Heilungen | Dieses Dokument aktualisieren |

### Phase 2: Gestaltung

| Schritt | Aktion |
|---|---|
| 1 | CSS-Dateien gegen DESIGN.md abgleichen |
| 2 | Design-Varianten-Wache prüfen |
| 3 | Kontrast-Messung (wenn Playwright verfügbar) |
| 4 | Dokumentation |

---

## 5. Verifikationsplan

Nach Abschluss beider Phasen:

```bash
# Lesbarkeit
python3 scripts/readability_check.py --gate-bestand
# Soll: Exit 0, Ø Flesch ≥ 62, 0 Artikel < 55

# Design-Varianten (wenn Workflow verfügbar)
npm run design:varianten
```

---

## 6. Verbleibende Aufgaben

### Phase 1: Lesbarkeit (offen)

- [ ] 23 Artikel mit Flesch < 62 auf ≥62 heben
- [ ] Priorisierte Artikel: gasrechnung-senken-so-bereitest-du-di, gasrechnung-senken-spaetsommer-check, haushaltskosten-reduzieren, umzug-mit-internet-anschluss, frugalismus-tipps-so-vermeidest-du-te
- [ ] Gate-Check: `python3 scripts/readability_check.py --gate-bestand` → Exit 0
- [ ] Ø Flesch ≥ 62, 0 Artikel unter 55

### Phase 2: Gestaltung (offen)

- [ ] CSS-Dateien gegen DESIGN.md abgleichen
- [ ] Design-Varianten-Wache prüfen (`design-varianten.yml`)
- [ ] Kontrast-Messung (wenn Playwright verfügbar)
- [ ] Dokumentation

### Dokumentation

- [ ] Finale Zusammenfassung aller Heilungen
- [ ] PR erstellen / Commit auf `arena/1d71adc0-franksfinanzcheck-blog`
