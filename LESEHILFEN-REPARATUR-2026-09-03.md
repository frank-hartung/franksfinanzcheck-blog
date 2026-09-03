# LESEHILFEN-REPARATUR 2026-09-03 — Vorlesen + Kurzfassung

**Datum:** 03.09.2026
**Produktivcode:** `static/premium/ff-reader.js`, `assets/css/extended/ff-reader.css`,
`layouts/single.html`, `layouts/_default/single.html`
**Neue Wache:** `scripts/reader_functional_test.mjs` + `scripts/reader_qa_lib.mjs` (jsdom),
`.github/workflows/lesehilfen-gate.yml`

---

## 0. Was vorher falsch war — auch in unseren eigenen Reports

`VORLESEN-HIGHEND-REPORT.md` meldete am selben Tag **„106/106 grün“**. Diese Aussage war
**nicht falsch, aber wertlos**: Alle vier Reader-Suiten liefen gegen eine handgebaute
`FakeNode`-Klasse (`scripts/reader_playback_function_test.js`, ab Zeile 30) statt gegen eine
echte DOM. Selektoren, `closest()`, `<dialog>`, Event-Bubbling und Template-Struktur wurden
dabei nie ausgeführt. Genau dort saßen die Fehler.

Die neue Wache `scripts/reader_functional_test.mjs` läuft deshalb gegen **jsdom** mit

- der **unveränderten** `static/premium/ff-reader.js` (per `win.eval`),
- dem **echten** Toolbar-Markup, wörtlich aus `layouts/_partials/reader_toolbar.html` extrahiert,
- der **echten** Kurzantwort-Box, wörtlich aus `layouts/single.html` extrahiert,
- **echtem Inhalt** aus `content/posts/` (alle 28 Artikel).

Sie prüft bis unmittelbar vor die Audio-Ausgabe: Jede `speak()`-Aufruf wird mit
`voice`, `lang`, `rate`, `pitch`, `volume`, `text` und User-Gesture-Kontext aufgezeichnet.

---

## 1. Reparierte Fehler (jeder vorher reproduziert, danach mit Test belegt)

| # | Fehler | Ursache | Fix | Beleg |
|---|---|---|---|---|
| 1 | **Der grüne Kasten wurde nie vorgelesen.** | `.ff-kurzantwort` steht in `layouts/single.html` Zeile 59, `.post-content` beginnt erst Zeile 79. `collectBlocks()` suchte die Box per Selektor — aber **nur innerhalb von `.post-content`**. Der Code war toter Code. | `preContentBoxes()` sammelt Korrektur- und Kurzantwort-Box in Dokumentreihenfolge **vor** dem Fließtext. Die sichtbare Dachzeile wird dabei entfernt, sonst spräche der Reader „Kurzantwort: Kurz & knapp – die Antwort …“. | Test 3/3 grün |
| 2 | **„Weiterlesen“ sprach denselben Satz ein zweites Mal.** | `cursor` wurde beim *Start* einer Einheit gesetzt und beim *Ende* nie weitergezählt. Wer in der Atempause zwischen zwei Sätzen pausierte, bekam beim Fortsetzen den fertigen Satz erneut. Dasselbe galt für die Keep-Alive-Wache. | Neuer Zustand `nextIndex`; `resumeReading()`, Keep-Alive und Android-Pfad nutzen ihn. | Regressionstest in 9) |
| 3 | **Fokus landete nach dem Kurzfassungs-Dialog im Nirgendwo.** | Gemerkt wurde `doc.activeElement` — fast immer `<body>`, weil Safari auf macOS/iOS Buttons beim Klick bewusst **nicht** fokussiert. | `isFocusable()` prüft Element, Dokumentzugehörigkeit und `disabled`; sonst fällt der Fokus auf den Kurzfassung-Button zurück. | Test 8) grün |
| 4 | **Text markieren warf die Wiedergabe an eine andere Stelle.** | Der Klick-zum-Sprung-Handler reagierte auf das `click` am Ende einer Markierung. | Sprung nur bei kollabierter Auswahl (`getSelection().isCollapsed`). | — |
| 5 | **Der grüne Kasten hatte keinen Dunkelmodus.** | Komplett inline gestylt, dabei ist `hugo.toml` auf `defaultTheme = "auto"`. | Inline-Styling entfernt, echte CSS-Komponente mit `[data-theme="dark"]`. | Test 12) grün |
| 6 | **Falsches Versprechen für Screenreader.** | `aria-label` sagte immer „Artikel vorlesen (männliche Stimme)“ — auch auf Geräten, die keine haben. | `syncVoiceLabel()` setzt das Label aus dem tatsächlich aufgelösten Stimmenkatalog (`data-ff-voice="male"|"device"`). | Test 5) grün |

---

## 2. Kurzfassung / grüner Kasten: Lesbarkeit auf Highend-Niveau

Vorher: `font-size:.95em` (kleiner als der Fließtext), `line-height:1.55`, keine
Zeilenlängen-Begrenzung, kein Dunkelmodus, keine Druck- und High-Contrast-Regeln.

Jetzt (`assets/css/extended/ff-reader.css`, Abschnitt „KURZFASSUNG – LESEBARKEIT“):

| Merkmal | Wert |
|---|---|
| Textgröße | `1rem` — identisch zum Fließtext |
| Zeilenhöhe | `1.68` |
| Zeilenlänge | `max-inline-size: 68ch` (Dialog: 66ch) |
| Umbruch | `text-wrap: pretty` + `hyphens: auto` (deutsch) |
| Innenabstand | `clamp()` — flüssig zwischen Mobil und Desktop |
| Semantik | `role="note"` + `aria-labelledby` |

**Kontraste (WCAG 2.2), gerechnet und im Test festgeschrieben:**

| Paar | Wert | Stufe |
|---|---|---|
| Kasten-Label hell `#0B4A37` auf `#F2F8F5` | **9,53:1** | AAA |
| Kasten-Text hell `#16211D` auf `#F2F8F5` | **15,38:1** | AAA |
| Kasten-Label dunkel `#86D8BB` auf `#10211B` | **10,00:1** | AAA |
| Kasten-Text dunkel `#E8F1EC` auf `#10211B` | **14,52:1** | AAA |
| Dialog-Sekundärtext hell `#5A6360` | **6,20:1** | AA |
| Dialog-Sekundärtext dunkel `#A8B4AF` | **7,82:1** | AAA |

Der Dialog lief vorher für Meta, Zahlen-Labels und TOC-Teaser über `--secondary`
(`#6C6C6C` → 5,25:1). Jetzt eigene, geprüfte Token. Zusätzlich: `@media print`,
`@media (forced-colors: active)`, `@media (prefers-reduced-motion: reduce)`,
Mobile-Aufhebung der Zeilenlänge unter 640 px.

---

## 3. Die ehrliche Antwort zur männlichen Stimme

**Die Web Speech API kann eine männliche Stimme nicht garantieren.** Das ist keine
Implementierungsschwäche, sondern eine Grenze der Plattform. Belege:

- Der Standard kennt **kein Geschlechts-Merkmal**; welche Stimmen existieren, entscheiden
  Betriebssystem und Browser ([Stack Overflow](https://stackoverflow.com/questions/50341775/speech-synthesis-how-to-change-gender/50341971#50341971)).
- **Chrome/Android mit Google-TTS** liefert für Deutsch genau **eine** Stimme
  („Google Deutsch“) — ohne männliche Variante
  ([Chromium Issue 331977824](https://issues.chromium.org/issues/331977824),
  [talkrapp.com](https://talkrapp.com/speechSynthesis.html)).
- **iOS/iPadOS Safari** blendet installierte Premium-Stimmen (Anna, Markus, Viktor,
  Yannick) für Web Speech **aus**; betroffen sind Safari, Chrome und Firefox auf iOS
  gleichermaßen ([Apple Developer Forum 723503](https://developer.apple.com/forums/thread/723503)).
- **Firefox für Android** implementiert die Synthese-Hälfte der Web Speech API
  nur eingeschränkt ([Browser-Support-Matrix](https://www.testmuai.com/learning-hub/speech-synthesis-api-browser-support/)).

Was die Engine jetzt tut:

| Gerät | Ergebnis (im Test gemessen) |
|---|---|
| macOS · Chrome / Safari | `Markus` — **männlich** ✅ |
| Windows · Chrome / Edge | `Microsoft Conrad Online (Natural)` — **männlich** ✅ |
| Android · Chrome (Google-TTS) | `Google Deutsch` — Gerätstimme, **ehrlich gekennzeichnet** |
| iOS · Safari | `Anna` — Gerätstimme, **ehrlich gekennzeichnet** |
| Linux · Firefox (espeak) | `deutsch` — Gerätstimme, **ehrlich gekennzeichnet** |

In allen fünf Fällen startet die Wiedergabe, keine weibliche Stimme wird gewählt, wenn das
Gerät eine männliche hergibt, und der Button verspricht nur das, was das Gerät einlöst.

**Eine echte Garantie liefert ausschließlich vorgerendertes Audio** (First-Party-MP3,
HTML5-`<audio>`) — das läuft auf jedem Gerät und in jedem Browser, weil keine
Stimmenbibliothek des Betriebssystems beteiligt ist. Diese Entscheidung ist offen,
siehe Abschnitt 6.

---

## 4. Was dauerhaft sichert, dass es nicht wieder kaputtgeht

`.github/workflows/lesehilfen-gate.yml` läuft bei jedem Push/PR, der Lesehilfen oder
`content/posts/**` berührt, plus täglich um 08:20 MESZ. Es führt alle **sieben** Suiten
aus; ein roter Test blockiert.

> GitHub verweigert dieser Integration das `workflows`-Schreibrecht. Die fertige Datei
> liegt deshalb unter `patches/lesehilfen-gate-2026-09-03-workflow-ready.yml` (plus
> anwendbares `.patch`) und muss einmalig nach `.github/workflows/` gelegt werden.

Zusätzlich prüft der Funktionstest die **Verankerung in den Templates** (Abschnitt 0):
Bindet jemand `reader_toolbar.html` aus `layouts/single.html` oder
`layouts/pillar/single.html` aus, wird das rot — nicht erst im Browser.

---

## 5. Funktionstest — Ergebnis

| Suite | Ergebnis |
|---|---|
| `node scripts/reader_functional_test.mjs` **(echte DOM)** | **161 grün, 0 rot** |
| `node scripts/reader_engine_check.js` | 58 grün, 0 rot |
| `node scripts/reader_male_voice_highend_test.js` | 36 grün, 0 rot |
| `node scripts/reader_playback_function_test.js` | 12 grün, 0 rot |
| `node scripts/summary_engine_check.js` | 26 grün, 0 rot |
| `node scripts/audio_pipeline_test.mjs` **(neu, 6 Gruppen)** | **145 grün, 0 rot** |
| `python3 scripts/reader_toolbar_check.py` | alle Gates grün |
| **Gesamt** | **438 Prüfungen grün** |

Der Funktionstest wurde **dreimal in Folge** ausgeführt: 139/139 jedes Mal (kein Flackern);
nach der Erweiterung auf 161 Prüfungen ebenfalls stabil.

Die Audio-Suite (`audio_pipeline_test.mjs`) deckt sechs Gruppen ab: Bestands-Regressionen
der Sprechtext-Heilungen, Rahmenkopf-Decodierung und Joiner mit synthetischem Rahmenstrom,
die gerenderten Fassungen (Rahmenstrom lückenlos, einheitliche Kodierung, Zeitkarte gegen
Rahmenstrom), die Aussprache-Normalisierung als **Direkttest der Engine** sowie die
Plausibilität der Sprechdauer je Teil. Beide wirksamen Gruppen sind **per Mutation belegt**:
Wird eine tote `\b`-Regel wieder eingebaut, wird Gruppe 5 rot (102/1); wird ein gerenderter
Teil verstümmelt, wird Gruppe 6 rot (144/1). Danach jeweils wiederhergestellt.

Abgedeckt: Klickpfad, vollständiges Abspielen aller 28 Artikel, Voice-Bindung,
DE/EN-Routing ohne Umschalter, 240-Zeichen-Chunk-Grenze, Texttreue (H2 + Absätze +
Tabellenzeilen), Geräte-Matrix (8 Kombinationen), lazy Voice-Katalog, Browser ohne
Sprachausgabe, Dialog (Fokus-Falle, Esc, Scroll-Sperre, Sprungmarken, Kopieren),
Pause/Weiter/Stop/Abschnittssprung, Kontraste, Template-Verankerung.

### Nicht geprüft — und warum

In dieser Umgebung war **kein Browser und kein Hugo-Binary installierbar**
(Download von `release-assets.githubusercontent.com` und vom Playwright-CDN
blockiert). Konkret ungeprüft:

- **physisch hörbarer Ton** und das Timbre einer Stimme,
- **Rendering** des grünen Kastens (jsdom layoutet nicht — Kontraste sind gerechnet, nicht gemessen),
- **natives `<dialog>`**-Verhalten (jsdom-`showModal` ist hier nachgebaut),
- **reale WebKit-Autoplay-Politik** auf iOS (geprüft ist nur, dass `speak()` synchron im
  Klick-Handler liegt — die notwendige, nicht die hinreichende Bedingung),
- **Hugo-Build** der geänderten Templates. Geprüft ist die Klammerbilanz und die
  `define`/`if`/`range`/`with`-zu-`end`-Paarung (`layouts/single.html` 68/68, 16 `end`
  auf 16 Block-Öffner; `_default/single.html` identisch; `reader_toolbar.html` 26/26,
  4 auf 4) sowie die CSS-Klammerbilanz (Endtiefe 0, 8 `@media`-Blöcke). Das ist **keine**
  Go-Template-Parser-Prüfung — `hugo` lief in dieser Umgebung nicht. Der Funktionstest
  liest das Markup der Templates wörtlich ein und schlägt an, wenn sich die Struktur ändert.

Diese fünf Punkte gehören auf ein echtes Gerät, bevor die Änderung live geht.

---

## 6. Entscheidung: vorgerendertes Audio für den Volltext

**Entschieden am 03.09.2026:** Es wird vorgerendertes First-Party-Audio **für den Volltext
aller 28 Artikel** gebaut. Nur das ist eine Garantie — die Browser-Stimme bleibt als
Zusatzangebot erhalten, ist aber nicht mehr der Träger der Zusage.

Zur Einordnung der Größenordnung: Die 28 Artikel haben 12.200–18.700 Zeichen Markdown;
das sind je Artikel rund 12–19 Minuten Audio. Als MP3 (32 kbit/s, Mono, Sprache) sind das
etwa 2,5–3,5 MB pro Artikel und rund 100 MB für den Bestand.

### Gebaute Pipeline

| Datei | Aufgabe |
|---|---|
| `scripts/prepare_audio_chunks.mjs` | Zerlegt jeden Artikel in Sprechtexte von höchstens 1400 Zeichen. Lädt die echte Engine über den Export-Hook in jsdom — die Chunks sind also exakt das, was gesprochen wird. Harte Assertion bei Überschreitung. |
| `data/audio/<slug>.chunks.json` | 28 Dateien, **270 Teile**, längster exakt 1400 Zeichen. |
| `scripts/mp3_join.mjs` | Verbindet die Teile und entfernt dabei den Xing-Kopf jedes Teils (ein mitgeführter Kopf erzeugt hörbare Klicks). Erzeugt die Zeitkarte. |
| `scripts/mp3_info.mjs` | Abhängigkeitsfreier, versions- und layer-gewahrer MP3-Reader — nötig, weil in dieser Umgebung kein `ffprobe` installierbar war. |
| `scripts/audio_render_next.mjs` | Wiederaufnehmbarer Fortschritts-Tracker. Ohne Argument: Stand und nächster Artikel. |
| `static/audio/<slug>.mp3` + `.timemap.json` | Auslieferung. Der Service Worker hält MP3 **bewusst** nicht im Cache — Cache-first würde Range-Anfragen und Springen brechen. |

Die Wiedergabe wählt die Audio-Fassung automatisch, wenn sie vorhanden ist, und fällt
sonst auf die Browser-Stimme zurück. Für den Nutzer gibt es **keinen** Umschalter.

### Stand

**1 von 28 Artikeln verbunden** (`2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife`,
11:17 min, 2,58 MB, 119 Zeitstempel). **14 von 270 Teilen** gerendert.

Das Rendering ist der Engpass: Die Sprachsynthese ist auf zehn Clips pro Arbeitsschritt
begrenzt, also rund **26 weitere Runden** bis zum vollständigen Bestand. Der Fortschritt
ist jederzeit mit `node scripts/audio_render_next.mjs` abrufbar.

### Dabei gefundene und behobene Sprachtext-Fehler

Der Bau der Chunks hat eine eigene Fehlerklasse sichtbar gemacht, die kein Bestandsscan
findet: **Vier Regeln in `speechNormalize` waren tot**, weil `\b` vor oder nach einem
Nicht-Wortzeichen in JavaScript nie matcht (`\bØ`, `\bà`, `m²\b`, `m³\b`). Dazu kamen
rund fünfzehn Symbol- und Einheitenklassen (`Mbit/s` → „Megabit oder s", `kWh/Jahr`,
`CO₂`, `°C`, `Ø`, Währungsumbrüche, Klammer-Dopplungen) sowie drei Folgefehler aus den
neu eingeführten Regeln. Insgesamt wurden in dieser Sitzung **33 Fehler** behoben.

Zwei unabhängige Verfahren bestätigen den Bestand jetzt als sauber: ein vollständiges
Zeicheninventar über alle 270 Teile (84 Zeichen, nichts außerhalb der sicheren Sprechmenge)
und ein Zwölf-Muster-Census (alle null). Beide sind als Prüfungen in
`scripts/audio_pipeline_test.mjs` verankert.
