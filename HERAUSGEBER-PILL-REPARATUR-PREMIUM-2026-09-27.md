# Willkommenstext: Herausgeber-Pill ragt über die innere Box – behoben (27.09.2026)

**Auslöser (Frank):** „Siehe dir den Willkommenstext auf franksfinanzcheck.de
vollständig an. Herausgegeben von Frank Hartung ragt über die innere Box im
Willkommenstext. Bitte auf Premium-Level einer Profi-Agentur beheben.“

**Betroffen:** Startseite, saisonaler Hero (Willkommenstext), Trust-Pills –
konkret die editoriale Pill „Herausgegeben von Frank Hartung“ im Fakten-Panel
der aktiven Variante `v-hero-premium`. Befund bestätigt am Live-Stand
(Deploy des PR #420-Merges, 27.09.2026 14:26 UTC).

---

## 1 · Befund (nachgestellt und messbar gemacht)

Im Desktop-Panel der Hero-Variante ist die Trust-Spalte nur 235–266 px breit.
Die Herausgeber-Pill wurde aber als **eine einzige, unumbrechbare Zeile**
„✓ Herausgegeben von Frank Hartung“ gerendert – 288 px breit (Inter, Autor
fett; 276 px mit dem bisherigen Schriftschnitt) – und ragte damit **22–34 px
über die rechte Kante des Fakten-Panels hinaus** („innere Box“), lokal am
nachgebauten Live-Stand gemessen (Desktop 1280 px und 1024 px; Mobil war die
Pill in der horizontalen Umbruch-Reihe zwar breit, aber noch enthalten).

## 2 · Ursachen – zwei Fehler, die sich gegenseitig verstärkten

1. **`<br>` ist in einem Flex-Item kein Zeilenumbruch.** Die Pill ist
   `display:inline-flex`. In einem Flex-Container wird `<br>` zu einem eigenen,
   nullbreiten Flex-Item – Blink, WebKit und Gecko verhalten sich identisch.
   Die gedachte zweite Zeile blieb in jedem Browser aus; Label und Autoren-Link
   lagen in einer Flex-Zeile nebeneinander.
2. **`white-space:nowrap`** auf `.ff-trust-pill--editorial` (Live-Stand)
   verbot zusätzlich jeden Textumbruch. Damit konnte der Inhalt nirgends
   ausweichen und lief über die Panel-Kante.

Der Commit `1c82ab9` (#421, „Fix responsive editorial trust pill wrapping“)
hat das Symptom mit Umbrech-Guards (`max-width:100%`, `min-width:0`,
`overflow-wrap:anywhere`) eingedämmt – die Pill blieb dabei aber typografisch
kaputt: Der tote `<br>` blieb wirkungslos, der Autoren-Name quetschte sich
als „Frank/Hartung“-Stapel neben das Label statt darunter. **Kein CSS kann
einen Zeilenwechsel wiederherstellen, den die Struktur nie erzeugt hat.**

## 3 · Reparatur – Struktur statt Zeichen

**`layouts/_partials/home_info.html`** – die zweizeilige Verantwortungsangabe
ist jetzt eine echte Flex-Spalte, kein `<br>`-Trick:

```html
<span class="ff-trust-pill ff-trust-pill--editorial"
  ><span class="ff-trust-check" aria-hidden="true">✓</span
  ><span class="ff-trust-editorial"
    ><span class="ff-trust-editorial-label">Herausgegeben von</span
    ><a class="ff-trust-author" href="/ueber/">Frank Hartung</a
  ></span
></span>
```

**`assets/css/extended/zzz-agency-polish.css`** – Editorial-Block neu gebaut:

- `.ff-trust-editorial`: Flex-Spalte (`column`, `gap:2px`, `min-width:0`) –
  der Zeilenwechsel kommt aus der Box-Struktur und greift in jeder Engine,
  unabhängig von Font-Metrik, Zoom, Fallback-Fonts und `text-wrap`-Support.
- `.ff-trust-editorial-label`: 0.92em, gesperrt, **100 % Weiß**. Eine erste
  Entwurfsstufe mit 82 % Weiß wurde nach eigener Kontrastrechnung verworfen:
  auf dem hellsten Hero-Gradientwert (#1f6f5c) nur 3.6–3.9:1, unter WCAG AA.
  Hierarchie entsteht über Größe und Schriftschnitt, nicht über Kontrast.
- Autoren-Name: `font-weight:700`, `max-width:100%`, `overflow-wrap:anywhere`
  (Sicherheitsnetz für extreme Viewports).
- Sicherheitsnetz bleibt: `min-width:0` + `max-width:100%` auf der Pill –
  sie kann ihre Box strukturell nicht mehr verlassen.
- Kaskaden-Falle entschärft: `.ff-trust-row span` (z-premium-blog.css,
  Specificität 0,1,1) vergibt an *jedes* Span der Reihe Border + Backdrop.
  Die Struktur-Spans überschreiben mit 0,2,0 – ein Klassenname allein
  (0,1,0) würde trotz späterer Datei verlieren.
- Toter Rest code entfernt (`.ff-trust-pill--editorial strong` für ein
  `<strong>`-Markup, das es nicht mehr gibt).

Unverändert bleiben: E-E-A-T-Verlinkung auf `/ueber/`, dezente Unterstreichung,
Hover in `--ff-accent-2`, Trefferfläche `::after{inset:-8px}` (Tap-AA),
Goldkante der Premium-Variante, Dark-Mode-Flächen.

## 4 · Beweis – Messung vor/nach (geladene Webfonts, je 11 Viewports)

| Messung | Vor (Live-Stand) | Nach (Reparatur) |
|---|---|---|
| Zeilen der Verantwortungsangabe | 1 (toter `<br>`) | **2** (Label über Name, Abstand 2 px) |
| Pill-Breite Desktop 1280 | 288 px | 245 px (= Panelbreite, 9 px Luft) |
| Ragt über Panel-Kante | **+22 bis +34 px** | **−9 px** (enthalten) |
| Horizontaler Dokument-Overflow | – | **0 px** (1920/1440/1280/1024/900/820/414/390/360/320/280) |
| Kontrast Label/Autor (real, Pixel-gemessen) | – | **6.3:1 / 6.4:1** (WCAG AA ✓, nahe AAA) |

Geprüft in **allen drei Design-Varianten** (Basis, `v-hero-conversion`
freigegeben, `v-hero-premium` aktiv) – 33 Kombinationen, alle enthalten,
alle zweizeilig. Beweisfotos: `shots/herausgeber-pill-{vor,nach}-{desktop-1280,mobile-390}.png`.

## 5 · Dauerhafte Absicherung (Regressionswächter)

- `e2e/home.spec.mjs` (Desktop-Projekt): **„Herausgeber-Pill: zweizeilig und
  vollständig innerhalb der inneren Box“** – prüft Zweizeiligkeit (fängt die
  tote-`<br>`-Bugklasse), Enthaltensein aller Pills in Reihe und Hero-Box,
  innere Überläufe (`scrollWidth`), Dokument-Overflow, `/ueber/`-Verlinkung.
- `e2e/mobile.spec.mjs` (iPhone-14-Projekt): mobile Schwester des Tests plus
  Thumb-gerechte Mindesthöhe (≥ 40 px).
- **Mutationstest:** Mit nachgestelltem Live-Bug ( `<br>` + `nowrap`) failen
  beide Tests exakt; mit der Reparatur laufen sie grün. Die Wächter treffen
  die Bugklasse, nicht nur diesen einen Bug.

## 6 · Qualitätspipeline (alles grün)

- `hugo --destination public` – Build fehlerfrei (205 Seiten).
- `npx playwright test` – **70/70 bestanden** (Desktop + Mobile, inkl. der
  beiden neuen Wächter).
- Kontrast: Pixelgenaue Messung im gerenderten Hero (siehe §4); House-Standard
  „keine Kontrastreduktion für Hierarchie“ eingehalten.

## 7 · Beobachtungen außerhalb des Auftrags (bewusst unangetastet)

- Unterhalb von ~300 px Viewport erzeugen die Artikel-Karten (`.post-entry`,
  min. 270 px) einen geringen horizontalen Dokument-Overflow (4 px bei 280 px).
  Bestehendes Verhalten unterhalb der 320-px-Floor, unabhängig vom Hero –
  gehört in ein eigenes Ticket, nicht in diese Reparatur.
- Die Basis-Pill-Texte (100 % Weiß auf 14 % Weiß-Fläche) liegen im
  konstruierten Worst Case (hellster Gradientwert) bei 4.47:1 – systemisches
  Muster aller Pills, real deutlich besser (6.3+:1). Ebenfalls kein Teil
  dieses Auftrags.

**Stand:** 27.09.2026 · Reparatur auf Branch `arena/01a0e350-franksfinanzcheck-blog`
