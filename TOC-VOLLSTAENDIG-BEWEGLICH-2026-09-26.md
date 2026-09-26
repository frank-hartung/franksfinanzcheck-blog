# Inhaltsverzeichnis: vollständig + beweglich; Themen-Signet statt Glühbirne (26.09.2026)

**Auslöser (Frank):** „Inhaltsverzeichnis der gesamten Blogartikel vollständig
anzeigen · nicht fest stehen, sondern beweglich · Glühbirnen-Symbol gegen eine
sinnvolle themenbezogene Animation austauschen · dauerhaft auf Premium-Level.“

> **Zusammenführung #407 / #408:** Die finale Bewegungslogik ist die
> privacy-schonende #407-Variante. Sie speichert **keine** Leserposition (kein
> `localStorage`, keine Cookies). Frühere Hinweise auf eine positionsübergreifende
> Speicherung oder auf einen Reset-Knopf sind damit überholt.

---

## 1 · Vollständig

| vorher | jetzt |
|---|---|
| nur ein Teil der Sprungziele | **alle H2 und H3** in Dokumentreihenfolge, H3 eingerückt (`.ff-mini-toc--sub`) |
| Etiketten gekürzt („Fazit…“, Schnitt am Doppelpunkt) | **voller Überschriftentext** sichtbar, kein `…`, kein Clamp |
| Inhaltsverzeichnis im Artikel eingeklappt | mit `TocOpen = true` sofort offen, weiterhin von Lesern zuklappbar |

Der Zähler und der Fortschrittsbalken der schwebenden Navigation berücksichtigen
alle Sprungziele. Der scrollbare Listenbereich bewahrt dabei das Lesefenster.

## 2 · Beweglich – ohne Persistenz

`static/premium/ff-premium.js` → `makeMiniTocMovable()`:

- **Ziehen an der Kopfzeile** per Pointer Events (Maus, Finger, Stift),
  `touch-action: none`, Zeigerfang und sichtbarem Griff.
- **Tastatur:** Der Griff ist fokussierbar; Pfeiltasten bewegen um 16 px,
  `Shift` + Pfeiltaste um 64 px. `Pos1` (`Home`) dockt wieder an der
  freigegebenen Standardposition an.
- **Sichtbar im Fenster:** Eine 8-px-Kante klemmt die Box beim Ziehen und bei
  `resize` vollständig in das Viewport-Fenster.
- **Datenschutz:** Die Position gilt nur in der aktiven Seite. Sie wird weder
  lokal noch serverseitig gespeichert.
- Während des Zugs gibt es keinen Positions-Transition-Nachlauf; die
  Lesefenster-Logik für Artikelkopf, Footer und Consent-Banner bleibt erhalten.

## 3 · Signet statt Glühbirne

„Kurz & knapp – die Antwort“ erhält über
`layouts/_partials/kurzantwort_icon.html` ein lokales, themenbezogenes SVG:

| Themenwelt | Signet |
|---|---|
| Strom & Gas | Blitz |
| Internet, DSL & Handy | WLAN |
| Versicherungen | Schild mit Check |
| Konto, Karten & Zinsen | €-Münze |
| Frugalismus & Budget | Spross |
| Mietwagen & Reisen | Fahrzeug |
| unbekannt | Antwort-Check |

Die Animationen sind reine CSS-Animationen (`transform`, `opacity`,
`stroke-dashoffset`), haben eine feste Größe und ruhen bei
`prefers-reduced-motion`. Die Antwort-Karte besitzt außerdem Medaillon,
Eyebrow, Haarlinie und eine auf 65 Zeichen begrenzte Lesebreite.

## 4 · Dauerhaft abgesichert

- `npm run test:toc` prüft vollständige H2/H3-Navigation, Griff, Ziehen,
  Tastatur-Dock und das Nicht-Persistieren der Position.
- Playwright deckt offenes Artikel-TOC, Drag/Clamp/Tastatur/Dock sowie die
  animierten und ruhenden Themen-Signets ab.
- Die Theme-Partial ist als dekorativ markiert (`aria-hidden`); die sprachliche
  Bedeutung bleibt beim sichtbaren Antwort-Label.
