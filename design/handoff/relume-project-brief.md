# Relume-Projektbrief – FranksFinanzcheck

> Generiert aus `data/design/handoff.yaml` · Stand 2026-09-26 · Strukturbrief, keine Veröffentlichungsfreigabe.

## Projekt-Prompt

```text
Erstelle eine mobile-first Sitemap und Wireframes für FranksFinanzcheck, Unabhängiger Finanz-Ratgeber für private Haushalte. 
Ziel: Fixkosten verständlich senken – ohne Verkaufsdruck. Ton: klar, ruhig, vertrauenswürdig, konkret. Sprache: de-DE. 
Bewahre bestehende Inhalte und Informationsarchitektur; erfinde keine Fakten, Bewertungen, Siegel, Preise oder Testimonials. 
Nutze klare visuelle Hierarchie, großzügige Leseflächen, exakt eine H1 je Seite und zugängliche Formulare. 
Das Ergebnis ist ein Strukturvorschlag. Die Implementierung erfolgt ausschließlich über die Varianten-Werkbank mit menschlicher Freigabe.
```

## Globale Leitplanken

- Keine erfundenen Testimonials, Siegel, Bewertungen oder Sparbeträge.
- Keine Preis-/Tarifdaten in statische UI schreiben.
- Pro Seite exakt eine H1; Überschriftenhierarchie nicht überspringen.
- Primäre Handlung klar, aber ohne künstliche Dringlichkeit oder Dark Patterns.
- Bestehende deutsche Texte sind verbindlich; Relume liefert Struktur, keine Fakten.
- Mobile-first; 390 px ist der Abnahme-Viewport.

## Sitemap und Section-Vertrag

### Startseite — `/`

**Nutzerabsicht:** Orientierung schaffen und passend in die Ratgeber führen

| Reihenfolge | Section-ID | Referenz | Aufgabe |
|---:|---|---|---|
| 1 | `hero` | `hero` | Nutzenversprechen plus eine Primärhandlung |
| 2 | `trust` | `trust-pill` | Unabhängigkeit und Praxisbezug belegen |
| 3 | `topics` | `article-card` | Themenwelten scannbar machen |
| 4 | `latest` | `article-card` | Aktuelle Ratgeber zeigen |
| 5 | `newsletter` | `newsletter-form` | Freiwilligen Wiedereinstieg anbieten |

### Ratgeber-Zentrale — `/pillar/`

**Nutzerabsicht:** Alle Themenwelten und Sparpfade verständlich ordnen

| Reihenfolge | Section-ID | Referenz | Aufgabe |
|---:|---|---|---|
| 1 | `intro` | `hero` | Aufgabe und Auswahl erklären |
| 2 | `clusters` | `article-card` | Ratgeber nach Bedarf gruppieren |
| 3 | `method` | `callout` | Vorgehen transparent machen |
| 4 | `faq` | `faq` | Häufige Orientierungsfragen beantworten |

### Artikel-Template — `artikel`

**Nutzerabsicht:** Eine konkrete Finanzfrage nachvollziehbar und handlungsnah lösen

| Reihenfolge | Section-ID | Referenz | Aufgabe |
|---:|---|---|---|
| 1 | `article-head` | `article-header` | Thema, Aktualität und Autor klären |
| 2 | `article-body` | `prose` | Schritte mit ruhigem Lesefluss vermitteln |
| 3 | `contextual-cta` | `button-primary` | Nur passende nächste Handlung anbieten |
| 4 | `author` | `author-trust-box` | Erfahrung und Verantwortung transparent machen |
| 5 | `related` | `article-card` | Sinnvoll weiterlesen |

## Übergabe zurück in den Code

1. Relume-Entwurf nur als Struktur- und UX-Hypothese exportieren.
2. In Figma die Tokens aus `figma-tokens.tokens.json` verwenden; keine neuen Farben oder Radien anlegen.
3. Abweichungen als Variante in `data/design/varianten.yaml` registrieren.
4. Playwright und Lighthouse messen; Messprotokoll einfrieren.
5. Erst nach menschlicher Freigabe über `designVariante` aktivieren.
