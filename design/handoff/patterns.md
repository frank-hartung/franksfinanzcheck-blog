# PATTERNS.md – Musterbibliothek für den Figma-Handoff

**Erzeugt aus** `data/design/handoff.yaml` · Stand 2026-10-31 · **Nicht von Hand bearbeiten.**

Ein Inventar sagt, was es gibt. Ein Muster sagt, wann es eingesetzt wird,
wie es atmet und was es niemals tut. Ohne diese Ebene baut jeder Entwurf die
Komponenten neu zusammen.

## 1. Der Seitenrhythmus

| Zone | Zweck | Typografie | Abstand danach |
|---|---|---|---|
| Einstieg | Eine Aussage, ein nächster Schritt | `h1_home` / `h1_article` + `lead` | 64 px |
| Beweis | Warum man das glauben darf | `meta` + `trust-pill` | 32 px |
| Kern | Die eigentliche Arbeit | `h2` + `body` | 44 px |
| Werkzeug | Etwas tun, nicht nur lesen | `h2` + Komponente | 44 px |
| Abschluss | Ein Angebot, keine Falle | `h2` + `button-primary` | 64 px |

**Die tragende Regel:** Der Einstieg ist nie länger als zwei Zeilen H1.
Passt die Aussage nicht in zwei Zeilen, ist sie eine Zusammenfassung –
und die gehört in den Lead.

## 2. Typografie im Einsatz

| Stil | Desktop | Mobil | Familie | Aufgabe |
|---|---|---|---|---|
| `h1_home` | 56 px / 700 | 34 px | Inter | Startseiten-H1 (Saisonkopf), genau einmal pro Seite |
| `h1_article` | 36 px / 700 | 28 px | Inter | Artikel-H1 (.post-title) |
| `h2` | 24 px / 700 | 21 px | Inter | Abschnittsüberschrift + 2px Signalgelb-Unterstreichung |
| `h3` | 19 px / 700 | 18 px | Inter | Unterabschnitt, Abstand 44px über / 16px unter |
| `body` | 18 px / 400 | 17 px | system-ui | Fließtext, Messweite 65ch |
| `lead` | 20 px / 400 | 18 px | system-ui | GEO-Lead unter der H1 |
| `meta` | 14 px / 500 | 13 px | system-ui | Meta-Zeile mit Mittel-Punkten (Datum · Lesezeit) |
| `label` | 12 px / 600 | 12 px | system-ui | Chips, Badges, Feldlabels – nie als Eyebrow über H1 |
| `subline` | 22 px / 400 | 20 px | Playfair Display | Subline-Akzent, ausschließlich auf Smaragdflächen |

Skala: 390 / 768 / 1280 px. Inhalt 720 px breit,
Navigation 1024 px. Grundraster 8 px mit den dokumentierten Feinstufen 14, 18, 22 px.

## 3. Tiefe und Fläche

| Ebene | Schatten | Radius | Wann |
|---|---|---|---|
| Ruhende Karte | `0 2px 6px rgba(0,0,0,0.05)` | md (12) | Teaser, Cluster |
| Angehobene Karte | `0 6px 20px rgba(14,90,67,0.14)` | md (12) | Hover, nur ohne reduced-motion |
| Schwebende Fläche | `0 8px 24px rgba(15,52,43,0.08)` | lg (16) | Callout, Autorenbox |
| Handlung | `0 3px 10px rgba(255,179,0,0.40)` | pill (999) | ausschließlich Primär-Button |

**Schatten oder Rand, nie beides hart übereinander.** Das System kennt vier
Schattenstufen; wer eine fünfte braucht, hat ein Hierarchieproblem.

## 4. Muster im Einsatz

### `Content/Callout` — `.ff-callout`

Vier Typen: Tipp, Info, Warnung, Gefahr. Der Typ steht als Text in der Überschrift, nicht nur als Farbe. Linker Rand 3–4 px, Fläche getönt.

Zustände: tip, warning, info, dark.  Typ und Überschrift als Text; Kontrast mindestens 4,5:1

### `Content/Kurzantwort` — `.ff-kurzantwort`

Steht direkt unter H1 und Lead. Ein Absatz, höchstens drei Sätze. Das Signet ist dekorativ (`aria-hidden`), die Antwort ist echter Text.

Zustände: default, dark, print.  Antwort als echter Text; Signet rein dekorativ (aria-hidden)

### `Conversion/Newsletter form` — `.ff-nl__form`

Ein Feld, ein Knopf, ein Satz zum Zweck. Fehler unter dem Feld mit einem Satz, der den nächsten Schritt nennt. Kein Overlay, kein Countdown.

Zustände: default, focus, error, success, disabled, dark.  Persistente Labels; verständliche Fehlertexte; Tastaturbedienung

### `Navigation/Header` — `.header`

Skip-Link zuerst, aktuelle Seite sichtbar markiert, Tastaturreihenfolge gleich Lesereihenfolge.

Zustände: desktop, mobile, keyboard, dark.  Skip-Link, Landmark und sichtbarer aktueller Navigationspunkt

### `Trust/Author box` — `.ff-trust-box`

Avatar, Name, Qualifikation, Prüfhinweis – alles als Text. Eine Autorenbox ohne nachvollziehbare Qualifikation schadet E-E-A-T.

Zustände: default, dark.  Autor und Prüfhinweis als echter Text

### `Brand/Kostenprofil` — `.ff-kostenprofil`

Das Markenobjekt: immer dieselben vier Schritte in derselben Reihenfolge. Hier sind Indexzahlen erlaubt, weil der Inhalt eine Reihenfolge ist – auf jeder anderen Fläche bleiben 01/02/03 verboten.

Zustände: default, article, dark.  4K-Prüfpfad als geordnete Liste; Indexzahlen sind Inhalt, keine Deko

### `Data/Spar-Matrix` — `.ff-spar-matrix-table`

Fünf Spalten, `tabular-nums`, Zebra, Sticky-Kopf. Unter 760 px wird jede Zeile zur Karte (Feldnamen aus `data-label`, kein zweites Markup). Fehlt eine Quelle, fehlt die Zeile.

Zustände: default, hover, focus-visible, dark, mobile-gestapelt.  Unter 760 px wird jede Zeile zur Karte; Feldnamen aus data-label

## 5. Was das System niemals tut

1. Zwei Primärhandlungen in einem Viewport.
2. Signalgelb als Textfarbe auf hellem Grund.
3. Karussell, Autoplay oder Parallax auf Leseflächen.
4. Layout-Properties animieren (`width`, `height`, `top`, `margin`).
5. `outline: none` ohne sichtbaren Ersatz.
6. Externe CDNs, Fremdfonts im Fließtext, Tracking ohne Einwilligung.
7. Erfundene Bewertungen, Siegel, Sparbeträge oder Testimonials.
8. Eine zweite H1 pro Seite, auch nicht unsichtbar.

## 6. Abnahme je Entwurf

- [ ] Genau eine H1, maximal zwei Zeilen, kein Label darüber.
- [ ] Alle Farben als Variablen, keine Hex-Werte im Entwurf.
- [ ] Hell und Dunkel vollständig, inklusive Fokusring.
- [ ] 390 px ohne horizontalen Überlauf, Tap-Ziele ≥ 44 px.
- [ ] Hover, Fokus, Fehler, Leer- und Ladezustand gezeichnet.
- [ ] `prefers-reduced-motion` bedacht.
- [ ] Jede Zahl hat eine Quelle; keine Platzhalter-Fakten.
