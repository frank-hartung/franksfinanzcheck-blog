# LESEHILFEN-REPARATUR 2026-09-04 — Zusammenführung #169 auf main

**Datum:** 04.09.2026
**Kontext:** PR #169 (`fix(lesehilfen): Vorlesen + Kurzfassung repariert, echte DOM-Wache`)
war gegen `main` in Konflikt geraten, weil zwischenzeitlich PR #170
(Vorlesen v7 ZEIT-Standard + Kurzfassung v5) gemergt wurde. Dieser Stand löst den
Konflikt auf: Die Reparaturen und die **echte DOM-Wache** aus #169 kommen auf den
aktuellen main, ohne die v5-Design-Entscheidungen aus #170 zu verwerfen.

**Produktivcode:** `static/premium/ff-reader.js`, `assets/css/extended/ff-reader.css`,
`layouts/single.html`, `layouts/_default/single.html`
**Neue Wache:** `scripts/reader_functional_test.mjs` + `scripts/reader_qa_lib.mjs`
(jsdom), `scripts/hugo_shortcodes.mjs`, `tools/reader-qa/` (jsdom ^30),
`.github/workflows/lesehilfen-gate.yml` (liegt als Patch bereit, siehe unten)

---

## 1. Was übernommen wurde (#169 → main)

| Bereich | Fix | Stand jetzt |
|---|---|---|
| **Echte DOM-Wache** | Die alten Reader-Suiten liefen gegen eine handgebaute `FakeNode`-DOM und waren grün, während die Funktion im Browser fehlerhaft war. Neu: `scripts/reader_functional_test.mjs` lädt die **unveränderte** `static/premium/ff-reader.js` in **jsdom**, mit echtem Seiten-Skelett aus `layouts/single.html` und echtem Inhalt aus `content/posts/` (28 Artikel). | integriert, **161 grün / 0 rot** |
| **Kurzantwort-Box wird vorgelesen** | Die Box steht im Template **vor** `.post-content`; `collectBlocks()` fand sie nie. Reader und Audio-Generator sammeln Vorab-Boxen (`preContentBoxes`) jetzt in Dokument-Reihenfolge, ohne die Dachzeile doppelt zu sprechen. | integriert + Parität im Generator |
| **„Weiterlesen“ verdoppelt Sätze nicht mehr** | `nextIndex`-Zustand; Resume/Keep-Alive/Android-Pfad setzen an der nächsten Einheit fort statt am bereits gesprochenen Satz. | integriert |
| **Dunkelmodus für den grünen Kasten** | `:root[data-theme="dark"] .ff-kurzantwort …` mit geprüfter Palette (`#86D8BB`/`#E8F1EC` auf `#10211B`, AAA). | ergänzt (v5-Box blieb unangetastet) |
| **Druckdarstellung** | `@media print`: Lesehilfen-UI (Toolbar, Summary-Dialog, Live-Markierung) wird nicht gedruckt. | ergänzt |
| **Semantik/Barrierefreiheit** | Kasten als `role="note"` mit `aria-labelledby`; kein Inline-Styling im Template (v5 hatte es bereits entfernt). | ergänzt in beiden Single-Layouts |
| **Fokus-Rückkehr** | Nach dem Kurzfassungs-Dialog fällt der Fokus auf einen wirklich fokussierbaren Anker zurück (Safari fokussiert Buttons beim Klick nicht). | integriert |
| **Markieren ≠ Sprung** | Textmarkierung löst keinen Abschnittssprung mehr aus (nur kollabierte Auswahl). | integriert |
| **Ehrliches Screenreader-Label** | `syncVoiceLabel()` spricht den tatsächlich aufgelösten Stimmenkatalog aus. | integriert |

## 2. Konflikt-Auflösung: #169-Palette vs. v5-Design (#170)

Beide PRs hatten denselben Fehler (Inline-Styling, kein Dunkelmodus, keine
Zeilenlängen-Begrenzung) unabhängig repariert — mit unterschiedlichen Design-Tokens:

| Merkmal | #169 (Kasten) | #170/main (v5, bleibt) |
|---|---|---|
| Kasten-Akzent hell | `#0B4A37` | `#0E5A43` (Marken-Smaragd) |
| Textgröße | `1rem` | `.97em` (≈ Fließtext, da Body 18 px; em-basiert) |
| Zeilenlänge | `max-inline-size: 68ch` | `max-width: 68ch` |
| Zeilenhöhe / Umbruch | `1.68`, `text-wrap: pretty` | `1.68`, `text-wrap: pretty` |

Da #170 bereits auf main gemergt und damit maßgeblich ist, wurde **nicht** die
#169-Palette über #170 gelegt. Der Funktions- und Kontrasttest prüft die
tatsächlich ausgelieferten Tokens (Smaragd-Palette hell + `#86D8BB`/`#E8F1EC`
dunkel) auf WCAG-AA/AAA — die Anforderung „Textgröße wie Fließtext, 68-ch-Zeile,
1,68er-Zeilenabstand“ bleibt normativ erhalten und ist gegen die Live-CSS-Datei
festgeschrieben.

## 3. Audio-Parität: Generator folgt der Reader-Reihenfolge

Der ZEIT-Audio-Generator (`scripts/generate_reader_audio.py`, aus #170) muss für
die injizierte Tonspur (`#ff-reader-audio-config`, `chunks[].b`) exakt dieselbe
Blockreihenfolge erzeugen wie `collectBlocks()` im Browser. Nachgezogen:

- **Kurzantwort-Box vor `.post-content`** wird als Block `callout` mit Cue
  „Kurzantwort: …“ aufgenommen (Box-Dachzeile wird entfernt, keine Dopplung).
- **FAQ-H2** bleiben Fragen („…kündigst?“ statt „…kündigst.“) — Regel identisch
  zum Reader.
- Neuer `--selftest` prüft beides (23 grün / 0 rot).

## 4. Gate-Workflow (kann der Agent-Token nicht pushen)

GitHub verweigert App-Pushes auf `.github/workflows/` (fehlender
`workflows`-Scope). Wie bei #169 liegt der Workflow deshalb repo-konform bereit:

- `patches/lesehilfen-gate-2026-09-04-workflow-ready.yml` (lesbare Quelle)
- `patches/lesehilfen-gate-2026-09-04-workflows.patch` (anwendbar via
  `git apply patches/lesehilfen-gate-2026-09-04-workflows.patch`)

Einmal anlegen:

```bash
cp patches/lesehilfen-gate-2026-09-04-workflow-ready.yml \
   .github/workflows/lesehilfen-gate.yml
```

Der Gate läuft bei jedem Push/PR mit Lesehilfen-/Content-Berührung plus täglich
(08:20 MESZ) und führt aus: echten jsdom-Funktionstest, Engine-/Stimmen-/
Kurzfassungs-Suiten, Vorlesen-v7-Test, Audio-Generator-Selftest und die
Toolbar-/A11y-Wache.

## 5. Verifikation (alle lokal grün)

```
node scripts/reader_functional_test.mjs   → 161 grün, 0 rot  (jsdom, echte DOM)
node scripts/reader_engine_check.js       →  58 grün, 0 rot
node scripts/reader_male_voice_highend_test.js → 36 grün, 0 rot
node scripts/reader_playback_function_test.js → 12 grün, 0 rot
node scripts/reader_v7_function_test.js   →  15 grün, 0 rot
node scripts/summary_engine_check.js      →  26 grün, 0 rot
python3 scripts/reader_toolbar_check.py   →   alle Prüfungen erfolgreich
python3 scripts/generate_reader_audio.py --selftest → 23 grün, 0 rot
node --check static/premium/ff-reader.js  →  ok
```

Abgedeckte Regressionsfälle im DOM-Test (Auszug): Artikel wird vollständig
gesprochen (144 Sprecheinheiten), Klick startet synchron, explizite Locale,
keine weiblich benannte Stimme, „Weiterlesen“ ohne Doppel-Satz, „Beenden“
setzt Toolbar/Markierung/Balken zurück, alle H2, Tabellenzeilen (6),
28 Artikel ohne Crash, jeder Artikel mit verwertbarer Kurzantwort und ≥ 3
Kernaussagen, 163 Sprungmarken, 161 Zahlen-Karten, Kontrast-Checks inkl.
Dunkelmodus, Druck- und Forced-Colors-Regeln, `role="note"` ohne Inline-Styling.
