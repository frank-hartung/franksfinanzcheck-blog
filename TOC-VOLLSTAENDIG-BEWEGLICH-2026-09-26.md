# Inhaltsverzeichnis: vollständig + beweglich, Spar-Signet statt Glühbirne (26.09.2026)

**Auslöser (Frank):** „Inhaltsverzeichnis der gesamten Blogartikel vollständig
anzeigen · nicht fest stehen, sondern beweglich · Glühbirnen-Symbol gegen eine
sinnvolle themenbezogene Animation austauschen · dauerhaft auf Premium-Level.“

---

## 1 · Vollständig

| vorher | jetzt |
|---|---|
| nur H2-Abschnitte | **alle H2 *und* H3** in Dokumentreihenfolge, H3 eingerückt (`.ff-mini-toc--sub`) |
| Etiketten gekürzt („Fazit…“, Schnitt am Doppelpunkt) | **voller Überschriftentext** sichtbar, kein `…`, kein Clamp |
| Zähler zählte nur Hauptabschnitte | Zähler + Fortschrittsbalken über alle Sprungziele |

Zusätzlich steht das Inhaltsverzeichnis **im Artikel** (mobil/Tablet, `details.toc`)
jetzt offen: `TocOpen = true` in `hugo.toml` – vollständig sichtbar statt hinter
einem zusätzlichen Klick.

## 2 · Beweglich

`static/premium/ff-premium.js` → neu `setupMiniTocDrag()`:

- **Ziehen an der Kopfzeile** (Pointer-Events: Maus, Finger, Stift), `touch-action: none`,
  Zeigerfang (`setPointerCapture`), Griffpunkte-Signet und `cursor: grab/grabbing`.
- **Tastatur:** Kopfzeile ist fokussierbar (`tabindex="0"`), Pfeiltasten schieben
  8 px (mit Shift 32 px), `Home`/`Esc` stellt den Standardplatz wieder her.
- **Merkt sich die Position** pro Gerät (`localStorage: ff:toc:pos:v1`) – auch über
  Artikelwechsel hinweg; privater Modus fällt still auf „nur diese Seite“ zurück.
- **Nie aussperrbar:** jede Position wird mit 12 px Rand in den sichtbaren Bereich
  geklemmt (auch beim Wiederherstellen und bei `resize`); Doppelklick oder der
  ⤺-Knopf (erscheint nur im verschobenen Zustand) setzt zurück.
- Während des Zugs keine Transitions (kein Nachschwimmen), leichte Anhebe-Schattierung.
- Das bestehende Lesefenster (Ein-/Ausblenden zwischen Artikelkopf und Fuß) misst
  nach jedem Zug neu (`spy.remeasure`), rechnet also nie mit alter Geometrie.

## 3 · Spar-Signet statt 💡

Die Glühbirne war ein themenfremdes Emoji („Idee“) und auf jedem Betriebssystem
anders gezeichnet. Ersatz: `layouts/_partials/ff-icon-tipp.html` – ein hauseigenes
SVG-Signet aus **drei wachsenden Sparbalken und einer aufsteigenden Euro-Münze**,
animiert in reinem CSS (`.ff-icon-tipp*` in `zzz-agency-polish.css`).

- kein JS, kein Netzwerk-Asset, feste Kastengröße → **kein Layout-Shift**
- `aria-hidden` (Bedeutung trägt der Text „Tipp:“ / „Hinweis:“)
- `prefers-reduced-motion` hält das Signet still (DESIGN.md §6)
- eingesetzt in `callout.html` (type=tip), `einspartabelle.html`, `tarifvergleich.html`

## 4 · Dauerhaft abgesichert

| Wache | Ergebnis |
|---|---|
| `node scripts/ff_toc_beweglich_test.mjs` (**neu**, 19 Prüfungen) | grün – Vollständigkeit, Ziehen, Tastatur, Merken, Zurücksetzen, Klemmen |
| `node scripts/ff_heading_glyph_guard_test.mjs` (erweitert) | 47/47 grün – Label-Vertrag jetzt „sichtbarer Text ≡ voller Überschriftentext“ |
| `node scripts/ff_voice_functional_test.mjs` | 252/252 grün |
| `python3 scripts/emoji_guard.py` | grün |

Sammelaufruf: `npm run test:toc`.
