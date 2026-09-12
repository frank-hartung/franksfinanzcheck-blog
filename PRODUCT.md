# PRODUCT.md – FranksFinanzcheck

> Produkt-Kontext für Design-Entscheidungen. Impeccable (`.claude/skills/impeccable/`)
> lädt diese Datei vor jeder Design-Arbeit – sie ist die Single Source of Truth
> für Produkt, Publikum, Marke und Qualitätsgrenzen. Rollout: 12.09.2026
> (Design-Skills-Premium-Integration).

## Was das Produkt ist

**FranksFinanzcheck** (franksfinanzcheck.de) ist ein deutschsprachiger
Finanz-Ratgeber-Blog von Frank Hartung – seriös, ehrlich, ohne Fachchinesisch
und ohne Verkaufsdruck. Ehemalige >10 Jahre Praxis im Finanzbereich; die
Erfahrung (E-E-A-T) ist das Redaktions-Fundament. Geschäftsmodell: Affiliate
(CHECK24, Awin) + organische Reichweite über Google und Pinterest.

- **Plattform:** Hugo 0.164 (Extended) + PaperMod (stark angepasst), GitHub Pages
- **Umfang:** ~180 Ratgeber-Artikel, 6 Themenwelten („Pillar"/Cluster), tägliche
  Veröffentlichungen durch eine KI-gestützte Redaktions-Pipeline
- **Betrieb:** vollautomatisiertes Qualitäts- und Publishing-System (45+
  GitHub-Workflows, Gates für SEO, Affiliate-Integrität, Kadenz, CWV)

## Publikum

Deutsche Privathaushalte, 30–60, preisbewusst, überwiegend Laien in
Finanzfragen. Sie kommen über Google-Suche („Tagesgeld Zinsen 2026",
„Hausratversicherung Vergleich") und Pinterest (Visual-Pins zu Strom,
Versicherungen, Spartipps). Lesen überwiegend **mobil**, oft abends,
entschlossen aber zeitknapp: Sie wollen konkrete Zahlen, ehrliche Vor- und
Nachteile und einen klaren nächsten Schritt.

## Marken-Stimme

Klartext-Verlagston: freundlich-seriös, konkret, du-Form, keine Angstmache,
kein Hype. Fehler werden transparent korrigiert (WiWo-Standard, Korrektur-
Boxen). Meta-Zeile mit Mittel-Punkten („11.09.2026 · 9 Minuten") ist
Redaktions-Konvention.

## Visuelle Identität (Pinterest-Masterplan, 2025)

| Rolle | Wert | Einsatz |
|---|---|---|
| Smaragdgrün | `#0E5A43` (dunkel `#0A4634`) | Marke, Überschriften, Links, Hero-Verläufe |
| Smaragd hell | `#EAF4EF` | Soft-Flächen, Badges |
| Smaragd-Bright | `#7FD1B4` | Überschriften im Dark Mode (10.3:1) |
| Anthrazit | `#2E2E33` | Fließtext |
| Signalgelb | `#FFB300` (hell `#FFD15A`) | CTAs, Fokus-Ringe, Auswahl, Progress |
| Inter | 700/800 | Überschriften („das ruhige G") |
| Playfair Display | italic | Subline-Akzente |
| System-UI | – | Fließtext (kein Webfont im Body → Performance) |

Farb-Logik: Grün = Vertrauen/Finanzen, Gelb = Handlungsaufforderung.
Gelb ist NIEMALS Textfarbe auf hellem Grund (1.79:1) – nur Fläche/Akzent
oder Text auf Smaragd (dann `#FFD15A`, 5.8:1).

## Anti-References (was wir NICHT sind)

- Keine Bank-/Versicherer-Website (kein Corporate-Blau, keine Stock-Fotos
  mit Anzügen)
- Kein AI-Slop: keine Purple-Gradiente, keine Glassmorphism-Deko, keine
  identischen Karten-Reihen ohne Hierarchie, keine bounce/elastic-Easings
- Keine Clickbait-Optik (gelbe Fläche + rote Pfeile + unterstrichene
  Superlative)
- Kein Redesign-Enthusiasmus: die Marke ist etabliert, Evolution statt
  Revolution

## Harte Qualitätsgrenzen (Gates des Betriebssystems)

1. **Core Web Vitals sind heilig:** CLS ≈ 0 (dimensionierte Bilder, Slots
   reserviert), LCP-Cover mit fetchpriority, kein Layout-Shift durch
   Politur. Jede Änderung läuft durch CWV-REPORT-Gate.
2. **Dark Mode ist live** (`defaultTheme: auto`): jede Farbe braucht eine
   Dark-Variante (`:root[data-theme="dark"]`), Kontrast ≥ 4.5:1 Text /
   ≥ 3:1 große Typo. Gemessen wird, nicht geraten (`e2e/design-metrics.mjs`).
3. **Affiliate-Compliance:** /go/-Links immer `rel="sponsored nofollow
   noopener"` + `target="_blank"` + SubID (E2E-Wache prüft das im Browser).
4. **Keine externen Assets:** Fonts/Icons/Bilder self-hosted, kein CDN-
   Flash, kein Drittanbieter-Blocking im Critical Path.
5. **Mobile first:** 390px ist die primäre Breite. Kein horizontaler
   Overflow, Tap-Ziele ≥ 24px (AA), Best Practice 44px via Pseudo-Fläche.
6. **Redaktions-Standards schlagen Design-Moden:** Typo-Hierarchie der
   Artikel (H1→H2→H3, TOC, FAQ-Schema, Kurzfassung/Vorlesen-Toolbar) ist
   funktional und wird nicht weggdesignet.

## Design-Qualitätsfloor (aus den Skills übernommen)

- Messweite Fließtext 65–75ch (aktuell: 65ch ✓)
- Schatten = Versatz + weiches Blur, aus 2–3 Ebenen, nie 0-Offset-Halo
- Radius-Skala 8/12/16/999 (Karten 12–16px)
- Ein authored Motion-Moment statt verstreuter Effekte; Exponential-Ease-Out;
  `prefers-reduced-motion` respektiert
- Browser-Flächen themen: ::selection, caret, Fokus-Ringe (3px Signalgelb)
- Übergänge nur auf transform/opacity/Farbe – nie auf Layout-Eigenschaften
  (Ausnahme dokumentiert: Voice-Progress-Balken)

## Bezugsdateien

- `DESIGN.md` – technisches Design-System (Tokens, Komponenten, Regeln)
- `assets/css/extended/zzz-agency-polish.css` – Politur-Layer (geladen als
  letztes) mit Audit-Herleitung je Regel
- `e2e/design-metrics.mjs` – messbarer Design-Audit (Kontraste, Typo,
  Rhythmus, Tap-Ziele, Fokus)
- `DESIGN-SKILLS-ROLLOUT-2026-09-12.md` – Rollout-Report mit Vorher/Nachher
