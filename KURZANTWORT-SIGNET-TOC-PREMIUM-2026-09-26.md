# Inhaltsverzeichnis vollständig & beweglich + „Kurz & knapp“ mit Themen-Signet (26.09.2026)

**Auslöser:** Frank, drei Aufträge in einem:
1. *„Das Inhaltsverzeichnis der gesamten Blogartikel vollständig anzeigen.“*
2. *„Das Inhaltsverzeichnis soll nicht fest stehen, sondern beweglich sein.“*
3. *„Kurz & knapp – die Antwort sollte optimaler dargestellt werden. Das
   Glühbirnen-Symbol sollte gegen eine sinnvolle themenbezogene Animation
   ausgetauscht werden. Dauerhaft auf Premium-Level einer Profi-Agentur.“*

---

## Befund (reproduziert, nicht vermutet)

| # | Meldung | Gemessener Zustand im Build (Hugo 0.164.0) |
|---|---|---|
| 1 | Inhaltsverzeichnis „vollständig“ | Das Verzeichnis oben im Artikel (`details.toc`, PaperMod) war auf **jedem** Artikel **eingeklappt** – sichtbar war nur die Zeile „Inhaltsverzeichnis ▸“. Alle 23–45 Abschnitts-Links lagen klickverschlossen darunter. |
| 2 | „fest stehen“ | Die schwebende „Im Artikel“-Navigation (`.ff-mini-toc`) war `position: fixed` verdrahtet – geometrisch korrekt (Vorgänger-Reparatur), aber für den Leser unbeweglich angepinnt. |
| 3 | „Kurz & knapp“ | Die Antwort-Box `.ff-kurzantwort` existierte in **beiden** Single-Templates **ohne eine einzige Zeile CSS** – Trefferquote im gesamten Stylesheet-Bestand: exakt 0. Sie stand als unformatierter Kasten mit Browser-Default-Abständen im Artikelkopf (Screenshots im Arbeitsstand `shots/`, nur lokal). |
| 4 | Glühbirne | Statisches, generisches Lightbulb-SVG – ohne Themenbezug, für alle 54 Artikel identisch. |
| 5 | (Fund am Rand) Template-Drift | `layouts/single.html` (gewinnt die Hugo-Auflösung für alle Sections) und `layouts/_default/single.html` waren auseinandergelaufen: Die „Stand-Zeile“-Reparatur vom 21.09. (article_dates) steckte nur im _default-Zweig und lief damit **ins Leere**. Output-heute gleichwertig (GitInfo aus ⇒ `.Lastmod` == `.Date` ohne Frontmatter), aber brüchig bei jeder künftigen Config-Änderung. |

## Reparatur

### 1) Inhaltsverzeichnis: dauerhaft vollständig offen

- **`hugo.toml`:** `TocOpen = true` → `<details class="toc" open>` auf jeder
  Seite mit Abschnitten. Der komplette Baum (H2+H3) steht beim Ankommen
  vollständig sichtbar da – kein Schnitt, kein Deckel. Das `<details>`
  bleibt absichtlich zuklappbar (Leser-Kontrolle) und druckt aufgeklappt.
- **`z-premium-blog.css` Block „2. Inhaltsverzeichnis“:** Premium-Politur –
  Smaragd-Gradientfläche aus Marken-Tokens, kräftig gesetzter Titel
  („Inhaltsverzeichnis“), Akzent-Marker in Signalgelb-Mischung, ruhige
  Hover-Fläche hinter der Summary, volle Zeilenhöhe 1,5. Dark-Mode- und
  Print-Variante mitgeliefert (Dark: `entry`-Fläche + Emerald-Bright).

### 2) „Im Artikel“-Navigation: beweglich (Drag + Tastatur + Dock)

**`static/premium/ff-premium.js` → `makeMiniTocMovable(nav, head)`**

- Die Kopfzeile ist **Griff** (6-Punkt-Grip-Affordanz, rein dekorativ,
  `aria-hidden`) **und Tastatur-Schalter** (`tabindex="0"`,
  ehrliches `aria-label` statt falschem `role="button"`).
- **Drag** per Pointer Events (Maus/Stift/Touch): `setPointerCapture`,
  rAF-gebündelte Positionsupdates, 3-px-Löseschwelle gegen Fehlgriffe,
  `touch-action: none` nur auf dem Griff (die Liste darunter scrollt
  normal weiter).
- **Tastatur:** Pfeiltasten 16 px, Shift+Pfeil 64 px – Seitenscroll wird
  pro Tastendruck unterbunden (`preventDefault`).
- **Pos1** dockt die Box wieder an die freigegebene Standardposition
  (24 px rechts neben der Textspalte) an – Inline-Styles werden gelöscht,
  das Stylesheet-Dock greift wieder.
- **Fenster-Clamp:** Die Box bleibt beim Ziehen UND bei Resize vollständig
  im Viewport (8 px Kante).
- **Kinematik robust:** `baseTop()` liest Y transform-frei wie
  `measureWindow()` – ein Griff mitten im 0,3-s-Einblenden (translateY)
  vererbt keinen Restweg; draggerzeugte Sprünge sind dadurch per Vertrag
  ausgeschlossen (e2e-pinnt das Verhalten).
- **Privacy-Hausregel:** Es wird **nichts** gespeichert – geparkte
  Positionen gelten für die Seitensitzung (kein Cookie, kein Storage).
- Unberührt bleibt das freigegebene Lesefenster (Sichtbarkeit nur in der
  Lesephase, Consent-Ausweiche, reduced-motion-Verträge).

### 3) „Kurz & knapp – die Antwort“: Antwort-Karte auf Agentur-Niveau

**`z-premium-blog.css` Block „1. Kurzantwort-Box“** (vorher: 0 Zeilen CSS):

- Antwort-Karte: Smaragd-Weichgradient auf `entry`, Haarlinie
  (`emerald 16 %`-Mix), 4-px-Akzentkante links, Stufe-1-Elevation
  (`--ff-shadow-1`), Radius `--ff-radius-lg`.
- Kopfzeile: Signet-Medaillon (36 px Plakette) + uppercase Eyebrow
  (0,74 rem, 800, Smaragd) + Haarlinien-Teiler.
- Text: 1,03 rem / 1,62, Messweite 65 ch, `text-wrap: pretty`.
- Light + Dark + Print (flach, `break-inside: avoid`) + reduced-motion.
- **Kontraste gemessen:** Eyebrow 7,29:1 (hell) / 11,68:1 (dunkel),
  Text 12,02:1 / 15,03:1, Signet auf Medaillon rechnerisch 7,3:1 / 6,1:1
  – alle über WCAG-AA-Soll (≥ 4,5 bzw. ≥ 3 für Dekoratives).

### 4) Themen-Signet statt Glühbirne

**`layouts/_partials/kurzantwort_icon.html` (neu):** Animierte SVG-Marke
je Themenwelt (`.Params.pillar`), Haus-Standard: lokal, stroke-basiert,
kein JS, keine Fonts/Emojis. CSS-Keyframes in `z-premium-blog.css`:
Grundzustand **vollständig sichtbar**, die Keyframes modulieren nur
(nur `transform`/`opacity`/`stroke-dashoffset`; Kreisfrequenzen
1,8–4,2 s; kein bounce/elastic – DESIGN.md §6/§7).

| Themenwelt | Motiv | Animation |
|---|---|---|
| Strom & Gas (`strom-sparen`, auch Legacy-`energie`) | Blitz + 2 Funken | ruhiges Pulsieren, Funken twinkeln versetzt |
| Internet, DSL & Handy | WLAN-Signet | Bögen leuchten der Reihe nach auf, Punkt atmet |
| Versicherungen & Vorsorge | Schild + Häkchen | Häkchen zeichnet sich nach (dash-draw, 3,8 s) |
| Konto, Karten & Zinsen | €-Münze | Münze dreht sich ruhig (scaleX-Flip) |
| Frugalismus & Budget | Spross | Blätter wiegen sich sanft (±2,6°) |
| Mietwagen & Reisen | Fahrzeug | Räder drehen, Straßen-Dashes fließen |
| Fallback (fehlende/unbekannte Pillar) | Ring + Häkchen | Häkchen-Draw + ruhiges Atmen |

`prefers-reduced-motion`: Signet steht vollständig, aber ruhig
(globaler §8-Reset + lokaler Block-Wall). `ff-kurzantwort__icon` bleibt
der Klassen-Vertrag der Vorlese-/QA-Maschine; komplettes SVG
`aria-hidden`. QA-Fixture `ff_voice_qa_lib.mjs` spiegelt das neue Markup.

### 5) Drift-Heilung Single-Templates

`layouts/single.html` erhielt den article_dates-Stand-Zeilen-Block aus
`_default/single.html` (dort hing er seit dem 21.09. im toten Ast) –
beide Dateien sind wieder deckungsgleich, Kommentar verbucht.

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `hugo.toml` | `TocOpen = true` (Inhaltsverzeichnis offen) |
| `layouts/_partials/kurzantwort_icon.html` | **neu:** animiertes Themen-Signet |
| `layouts/single.html` | Signet-Partial statt Glühbirne + Drift-Heilung (article_dates) |
| `layouts/_default/single.html` | Signet-Partial statt Glühbirne (deckungsgleich gehalten) |
| `assets/css/extended/z-premium-blog.css` | Sicherungsblock: Kurzantwort-Karte, Signet-Keyframes, TOC-Politur, Mini-TOC-Griff (Light+Dark+Print+RM) |
| `static/premium/ff-premium.js` | `makeMiniTocMovable` (Drag/Tastatur/Clamp/Dock) |
| `scripts/ff_voice_qa_lib.mjs` | QA-Fixture spiegelt neues Signet-Markup |
| `e2e/article.spec.mjs` | **4 neue Regressionstests** (s. u.) |
| `DESIGN.md` §5 | Komponenten-Register: Antwort-Box verzeichnet |

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| Hugo-Build (0.164.0, extended) | fehlerfrei; `details.toc open` auf allen Artikeln; Signet-Klasse je `pillar` korrekt über alle 6 Themenwelten + Legacy-`energie`; Glühbirnen-Pfad 0× im Build |
| `node scripts/ff_heading_glyph_guard_test.mjs` | **43/43 grün** (Label-Vertrag unberührt) |
| `node scripts/ff_voice_functional_test.mjs` | **252/252 grün** (Kopf der Box bleibt vorlese-frei) |
| `python3 scripts/layout_audit.py` | keine neuen Befunde (nur bekannte Frühwarnungen) |
| `npm run design:gate` | BESTANDEN (kein Abweichen vom Regelwerk) |
| Interaktive Abnahme (Playwright/Chromium, Skript-Stand `e2e/tmp_*`) | Alle 6 Motive animieren (`animationName ≠ none`); Drag landet pixelgenau (−200/+120); Pfeil = 16 px; Shift+Pfeil = 64 px; Pos1 → Dock (x 1128 / y 108 wiederhergestellt); Clamp an allen Rändern; Reduced-Motion: `none` |
| Kontraste (gemessen + rechnerisch) | siehe Abschnitt 3 – alle über Soll |
| `npx playwright test` (Desktop + Mobile) | **68/68 grün** inkl. der 4 neuen Dauerwachen |

## Dauer-Wache (CI, `e2e/article.spec.mjs`)

1. *„Inhaltsverzeichnis oben im Artikel: steht offen und listet JEDEN
   Abschnitt“* – `open`-Flag + Mengenvertrag: jeder H2/H3-Anker des
   Artikels hat exakt einen Link im Verzeichnis (URL-Dekodierung wie im
   Browser). Ein künftiger Deckel oder ein Schließen läuft rot.
2. *„Schwebende Artikel-Navigation ist beweglich: Drag, Tastatur,
   Pos1-Dock, Fenster-Clamp“* – pinnt Drag-Genauigkeit, 16-/64-px-Schritte,
   Pos1-Rückkehr und den Rand-Clamp.
3. *„‚Kurz & knapp‘ trägt ein animiertes Themen-Signet statt der
   Glühbirne“* – Signet-Klasse aus der Motiv-Menge, `aria-hidden`,
   Glühbirnen-Pfad verboten, Animation läuft (`computed style`).
4. *„Signet-Animation: bei reduzierter Bewegung steht das Signet ruhig“* –
   alle `.ff-kz-*` auf `animation-name: none` unter
   `prefers-reduced-motion`.

## Hinweise (kein Handlungsbedarf)

- Das obere Inhaltsverzeichnis steht jetzt bewusst **offen** – bei einem
  23-Abschnitte-Ratgeber ist das ein langer, aber ehrlicher Block
  (zuklappbar bleibt es). Sollte die Redaktion ihn kürzen wollen, wäre
  die Abschnitts-Zusammenführung aus der offenen Empfehlung in
  `TOC-IM-ARTIKEL-PREMIUM-2026-09-26.md` der passende Hebel.
- Die bewegliche Navigation speichert nichts (Privacy). Ein
  „Position-merken über Seiten hinweg“ wäre ein eigener, storage-
  begründungspflichtiger Schritt – nicht Teil dieses Auftrags.
