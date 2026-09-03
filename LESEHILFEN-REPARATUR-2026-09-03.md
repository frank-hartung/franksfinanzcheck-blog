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
`content/posts/**` berührt, plus täglich um 08:20 MESZ. Es führt alle sechs Suiten aus;
ein roter Test blockiert.

Zusätzlich prüft der Funktionstest die **Verankerung in den Templates** (Abschnitt 0):
Bindet jemand `reader_toolbar.html` aus `layouts/single.html` oder
`layouts/pillar/single.html` aus, wird das rot — nicht erst im Browser.

---

## 5. Funktionstest — Ergebnis

| Suite | Ergebnis |
|---|---|
| `node scripts/reader_functional_test.mjs` **(neu, echte DOM)** | **139 grün, 0 rot** |
| `node scripts/reader_engine_check.js` | 58 grün, 0 rot |
| `node scripts/reader_male_voice_highend_test.js` | 36 grün, 0 rot |
| `node scripts/reader_playback_function_test.js` | 12 grün, 0 rot |
| `node scripts/summary_engine_check.js` | 26 grün, 0 rot |
| `python3 scripts/reader_toolbar_check.py` | alle Gates grün |
| **Gesamt** | **271 Prüfungen grün** |

Der Funktionstest wurde **dreimal in Folge** ausgeführt: 139/139 jedes Mal (kein Flackern).

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
- **Hugo-Build** der geänderten Templates. Die Templates sind syntaktisch geprüft und der
  Funktionstest liest ihr Markup wörtlich ein, aber `hugo` lief hier nicht.

Diese fünf Punkte gehören auf ein echtes Gerät, bevor die Änderung live geht.

---

## 6. Offene Entscheidung

Für eine **garantiert männliche Stimme auf jedem Gerät und in jedem Browser** ist
vorgerendertes First-Party-Audio nötig. Zur Einordnung der Größenordnung:
Die 28 Artikel haben 12.200–18.700 Zeichen Markdown; das sind je Artikel rund
12–19 Minuten Audio. Als MP3 (32 kbit/s, Mono, Sprache) sind das etwa 3–4 MB pro
Artikel und rund **100 MB für den Bestand** — plus je 8–12 Renderingschritte pro Artikel.

Eine deutlich schlankere Variante ist Audio **nur für die Kurzfassung**
(ca. 90 Sekunden, ~350 kB pro Artikel, ~10 MB gesamt, ein Rendering pro Artikel),
während der Volltext bei der Gerätstimme bleibt.

Beide Varianten sind technisch vorbereitet, aber noch **nicht** gebaut — das ist eine
Kosten-/Nutzen-Entscheidung, die nicht stillschweigend getroffen werden sollte.
