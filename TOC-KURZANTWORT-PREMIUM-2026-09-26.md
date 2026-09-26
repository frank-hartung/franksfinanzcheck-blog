# Inhaltsverzeichnis vollständig + beweglich, Kurzantwort-Box repariert (26.09.2026)

**Auslöser (Frank):** „Bitte das Inhaltsverzeichnis der gesamten Blogartikel
vollständig anzeigen. Zudem sollte das Inhaltsverzeichnis […] nicht fest
stehen, sondern beweglich sein. Kurz & knapp – die Antwort sollte optimaler
dargestellt werden. Das Glühbirnen-Symbol sollte gegen eine sinnvolle
themenbezogene Animation ausgetauscht werden.“

Die Meldung betrifft zwei verschiedene Bausteine jedes Artikels:

1. die schwebende Navigation **„Im Artikel“** rechts neben dem Text
   (`.ff-mini-toc`, `static/premium/ff-premium.js`),
2. die Box **„Kurz & knapp – die Antwort“** direkt unter der H1
   (`.ff-kurzantwort`, `layouts/single.html` + `layouts/_default/single.html`).

## Befund (reproduziert im Code, nicht vermutet)

| # | Baustein | Problem |
|---|---|---|
| 1 | `.ff-mini-toc` | Listete nur H2-Kapitel. Bei Ratgebern mit H3-Unterpunkten (z. B. 23 H2 + 22 H3 im Tierkrankenversicherungs-Artikel) fehlte fast die Hälfte der echten Gliederung – „vollständig“ war es nie. |
| 2 | `.ff-mini-toc` | Die aktive Zeile wechselte nur ihre Textfarbe. Kein Element bewegte sich sichtbar – die Navigation wirkte „fest stehend“, obwohl sie technisch `position: fixed` ist. |
| 3 | `.ff-kurzantwort` | **Keine einzige CSS-Regel** in der gesamten Codebasis (`grep -rli kurzantwort assets/` → 0 Treffer). Die Box fiel auf unformatiertes `<div>`/`<svg>`/`<p>` zurück – „die Antwort sollte optimaler dargestellt werden“ trifft es genau. |
| 4 | `.ff-kurzantwort__icon` | Das SVG war eine klassische Glühbirne (`M12 2a7 7 0 0 0-4 12.7…`, Symbol für „Idee“) – ohne jede Bewegung und thematisch unpassend: Die Box zeigt eine **geprüfte** Kurzantwort, keine Idee. |

## Reparatur

### 1. Vollständige Gliederung (`createMiniToc`, `ff-premium.js`)
H3-Überschriften werden jetzt zusätzlich zu H2 eingesammelt
(`qsa('h2[id], h3[id]', content)`) und im Verzeichnis eingerückt unter ihrem
Kapitel dargestellt (`.ff-mini-toc--top` / `.ff-mini-toc--sub`). Die
Erscheinungsschwelle bleibt an der H2-Zahl (≥ 3 Kapitel) hängen – kurze
Artikel bekommen weiterhin keine Navigation. Zähler und Fortschrittsbalken
rechnen jetzt über die volle Anzahl (H2 + H3), die Lesemarke bleibt exakt.

### 2. Beweglicher Lesemarker statt Farbwechsel
Ein neuer, schmaler Balken (`.ff-mini-toc__cursor`) gleitet per
CSS-`transition` (0.32 s, Haus-Easing) zur jeweils aktiven Zeile – Position
und Höhe kommen aus `--ff-toc-cursor-y`/`-h`, gesetzt von
`setupMiniTocSpy()`. Das ist die sichtbare Antwort auf „nicht fest stehen,
sondern beweglich sein“: Die Navigation bewegt sich jetzt tatsächlich, statt
nur Farben zu tauschen. `prefers-reduced-motion` schaltet die Gleitbewegung
auf einen Sprung ohne Animation.

### 3. Kurzantwort-Box: vollständige Premium-Gestaltung
Neuer CSS-Block in `assets/css/extended/z-premium-blog.css`
(„KURZ & KNAPP – DIE ANTWORT“): eigenständige Karte in Marken-Grün
(`--ff-green`), linker Akzentstreifen, Schatten, Radius nach
`--ff-radius-md`, Dark-Mode-Variante, Mobil-Anpassung, Print-Regel.

### 4. Glühbirne → Häkchen-Badge mit „Sonar“-Animation
Das SVG zeigt jetzt ein Häkchen in einem Ring (`.ff-kurzantwort__icon-ring`,
`.ff-kurzantwort__icon-check`) – bewusst gewählt, weil die Box eine
**geprüfte** Aussage zeigt (Bezug zum Markennamen „Franks**Finanz-Check**“),
nicht eine Idee. Die Animation liegt in zwei auslaufenden Ringen
(`@keyframes ff-kurzantwort-sonar`, versetzt gestartet), die um das Icon
pulsieren – das Häkchen selbst bleibt jederzeit scharf und lesbar. Bei
`prefers-reduced-motion: reduce` und im Druck ist die Pulsanimation aus.
Geändert in `layouts/single.html`, `layouts/_default/single.html` und dem
Vorschau-Werkzeug `tools/heading-anchor-preview/index.html`.

## Verifikation

Hugo und ein Browser stehen in dieser Sandbox nicht zur Verfügung
(Netzwerksperre auf `objects.githubusercontent.com` / `cdn.playwright.dev`
verhindert den Download von Hugo-Binary und Playwright-Chromium). Geprüft
wurde deshalb auf Quellcode- und DOM-Ebene:

| Prüfung | Ergebnis |
|---|---|
| `node scripts/ff_heading_glyph_guard_test.mjs` | 44/44 grün (Mini-TOC-Vertrag für H2 **und** H3 neu geprüft) |
| `node scripts/ff_voice_functional_test.mjs` | 252/252 grün |
| `node scripts/ff_voice_repair_test.mjs` | 56/56 grün |
| `node scripts/ff_voice_tts_hardening_test.mjs` | 57/57 grün |
| `python3 scripts/ff_voice_audio.py --selftest` | 123/123 grün |
| `python3 -m unittest discover -s scripts/tests` | 825 Tests, 5 Failures/12 Errors – **identisch** zum unveränderten Ausgangszustand (per `git stash`-Gegenprobe verifiziert), keine neuen Befunde |
| Eigene jsdom-Probe (6-Kapitel-Fixture, 2 mit Unterpunkten) | Verzeichnis zeigt alle 6 Einträge korrekt eingerückt, Zähler „6 / 6“, Cursor-Element vorhanden |
| CSS-Parser (`css-tree`) auf `z-premium-blog.css` | keine Parse-Fehler |
| Klammerbilanz Go-Templates (`single.html`, `_default/single.html`) | ausgeglichen |

**Offen für die nächste CI-/Review-Runde** (in dieser Sandbox nicht
ausführbar): `npm run test:e2e` (Playwright) und
`python3 scripts/layout_audit.py` gegen einen echten `hugo --minify`-Build,
um die neue Gestaltung zusätzlich pixelgenau zu bestätigen.
