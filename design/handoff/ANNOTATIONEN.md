# ANNOTATIONEN.md – Barrierefreiheit für den Figma-Handoff

**Erzeugt aus** `data/design/handoff.yaml` und `data/design/regelwerk.yaml` · Stand 2026-10-31 · **Nicht von Hand bearbeiten.**

Ein Entwurf ist erst übergabefähig, wenn jede Rolle ihre Kontrast-
anforderung kennt und nicht erst im Audit erfährt. Die Werte sind nach
WCAG 2.2 gerechnet (relative Luminanz), nicht behauptet.

## 1. Kontrast-Matrix

| Modus | Paarung | Vordergrund | Hintergrund | Kontrast | Soll |
|---|---|---|---|---|---|
| light | Fließtext auf Seite | `anthracite` #2E2E33 | `page-light` #FAFCFB | ✅ 13.11:1 | 4,5:1 |
| light | Fließtext auf Karte | `anthracite` #2E2E33 | `white` #FFFFFF | ✅ 13.51:1 | 4,5:1 |
| light | Sekundärtext auf Seite | `secondary-light` #6C6C6C | `page-light` #FAFCFB | ✅ 5.10:1 | 4,5:1 |
| light | Sekundärtext auf Karte | `secondary-light` #6C6C6C | `white` #FFFFFF | ✅ 5.25:1 | 4,5:1 |
| light | Überschrift auf Seite | `emerald` #0E5A43 | `page-light` #FAFCFB | ✅ 7.95:1 | 4,5:1 |
| light | Überschrift auf Karte | `emerald` #0E5A43 | `white` #FFFFFF | ✅ 8.20:1 | 4,5:1 |
| light | Überschrift auf Soft-Fläche | `emerald` #0E5A43 | `emerald-soft` #EAF4EF | ✅ 7.29:1 | 4,5:1 |
| light | Beschriftung auf Aktion | `anthracite` #2E2E33 | `yellow` #FFB300 | ✅ 7.53:1 | 4,5:1 |
| light | Beschriftung auf Aktion-Hover | `anthracite` #2E2E33 | `yellow-dark` #E6A100 | ✅ 6.09:1 | 4,5:1 |
| light | Invertiert auf Marke | `white` #FFFFFF | `emerald` #0E5A43 | ✅ 8.20:1 | 4,5:1 |
| light | Fehlertext auf Seite | `fehler-light` #A32B2B | `page-light` #FAFCFB | ✅ 6.94:1 | 4,5:1 |
| light | Erfolgstext auf Karte | `emerald` #0E5A43 | `white` #FFFFFF | ✅ 8.20:1 | 4,5:1 |
| dark | Fließtext auf Seite | `white` #FFFFFF | `page-dark` #1D1E20 | ✅ 16.68:1 | 4,5:1 |
| dark | Fließtext auf Karte | `white` #FFFFFF | `anthracite` #2E2E33 | ✅ 13.51:1 | 4,5:1 |
| dark | Sekundärtext auf Seite | `secondary-dark` #9B9C9D | `page-dark` #1D1E20 | ✅ 6.07:1 | 4,5:1 |
| dark | Sekundärtext auf Karte | `secondary-dark` #9B9C9D | `anthracite` #2E2E33 | ✅ 4.91:1 | 4,5:1 |
| dark | Überschrift auf Seite | `emerald-bright` #7FD1B4 | `page-dark` #1D1E20 | ✅ 9.28:1 | 4,5:1 |
| dark | Überschrift auf Karte | `emerald-bright` #7FD1B4 | `anthracite` #2E2E33 | ✅ 7.51:1 | 4,5:1 |
| dark | Überschrift auf Soft-Fläche | `emerald-bright` #7FD1B4 | `anthracite` #2E2E33 | ✅ 7.51:1 | 4,5:1 |
| dark | Beschriftung auf Aktion | `anthracite` #2E2E33 | `yellow` #FFB300 | ✅ 7.53:1 | 4,5:1 |
| dark | Beschriftung auf Aktion-Hover | `anthracite` #2E2E33 | `yellow-dark` #E6A100 | ✅ 6.09:1 | 4,5:1 |
| dark | Invertiert auf Marke | `page-dark` #1D1E20 | `emerald-bright` #7FD1B4 | ✅ 9.28:1 | 4,5:1 |
| dark | Fehlertext auf Seite | `fehler-dark` #FF9A9A | `page-dark` #1D1E20 | ✅ 8.21:1 | 4,5:1 |
| dark | Erfolgstext auf Karte | `emerald-bright` #7FD1B4 | `anthracite` #2E2E33 | ✅ 7.51:1 | 4,5:1 |

## 2. Was daraus folgt

- **Fließtext** erreicht mindestens 4.5:1.
- **Große Typografie** (ab 24 px) darf 3.0:1 nutzen, kleinere Grade nicht.
- **Meta und Sekundärtext** sind klein: 4.5:1, keine Ausnahme.
- **Signalgelb** trägt Anthrazit (7.53:1), niemals Weiß. Auf Smaragd ist `accent-2` die Textfarbe (5.67:1).
- **Fokusring**: 3 px Signalgelb, 2 px Abstand, auf jeder Fläche sichtbar.

## 3. Zustände, die gezeichnet sein müssen

| Komponententyp | Pflichtzustände | Zusätzlich bei YMYL |
|---|---|---|
| Aktion | Standard, Hover, Fokus, Deaktiviert | Ladezustand mit Text |
| Formular | Standard, Fokus, Fehler, Erfolg, Deaktiviert | Fehlerzusammenfassung |
| Karte/Link | Standard, Hover, Fokus | besucht, nur wenn relevant |
| Navigation | Desktop, Mobil, Tastatur, aktuell | Skip-Link sichtbar |
| Fläche | hell, dunkel | Druck bei Ratgebern |

## 4. Nicht verhandelbar

1. Farbe ist nie der einzige Träger einer Aussage.
2. Jedes Eingabefeld hat ein persistentes Label, keinen Placeholder als Label.
3. Fehlermeldungen benennen Feld und nächsten Schritt.
4. Tap-Ziele mindestens 24 px, angestrebt 44 px.
5. `prefers-reduced-motion` wird respektiert; nichts Wesentliches hängt an Animation.
6. Die DOM-Reihenfolge ist die Lesereihenfolge.
