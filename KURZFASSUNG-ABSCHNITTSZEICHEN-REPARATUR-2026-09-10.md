# KURZFASSUNG-ABSCHNITTSZEICHEN-REPARATUR — „§“ in der Kurzfassung ist dauerhaft entfernt (v1)

Datum: 10.09.2026 · Status: **Repariert, beprobt, in CI verriegelt**

## 1 · Befund

Im gesamten Blog zeigte die **Kurzfassung** an jeder Gliederung ein **„§“**
(Bsp. `/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/`).
Betroffen waren nicht nur die Ansicht „In diesem Artikel“ im Dialog, sondern
die gesamte Textausbeute der Lesehilfen:

| Ort | Symptom |
|---|---|
| Kurzfassung → „In diesem Artikel“ | Jeder Eintrag endete mit „§“ |
| „Kurzfassung kopieren“ (Klartext) | Jede Gliederungszeile mit „§“ |
| Vorlesen (Browser-Engine) | Jede Überschrift wurde mit „§“ gesprochen (als „paragraph“) |
| „Gerade vorgelesen“-Zelle | Label endete mit „§“ |

## 2 · Ursache (Wurzel)

`static/premium/ff-premium.js` (`addHeadingCopyButtons`) injiziert hinter jede
Abschnitts-Überschrift (`h2[id]`/`h3[id]`) einen **Abschnitts-Link-Kopierer** —
ein `<button class="ff-heading-copy">` mit dem sichtbaren Glyph **„§“**.
Das Glyph war roher Text im Button. Alle Textextraktoren von
`static/premium/ff-voice.js` lesen `textContent`/`readableText()` der
Überschrift — und haben so das UI-Schmuckzeichen als Inhalt ausgegeben.
Die Kurzfassung-Gliederung (`buildToc`) wischte es nicht weg (im Gegensatz zur
ff-mini-toc, die per Regex rasiert).

Kurz: **UI-Steuerung stand im Inhaltselement und war als Inhalt markiert.**

## 3 · Reparatur — drei Wände, ein Prinzip

Prinzip: *Das „§“ ist Dekoration eines Buttons — es ist nie Artikeltext.*

| Wand | Datei | Maßnahme |
|---|---|---|
| 1 · Glyph dekorativ | `static/premium/ff-premium.js` | „§“ lebt jetzt in `<span class="ff-heading-copy__glyph" aria-hidden="true">` — für Textextraktoren unsichtbar, auf dem Bildschirm unverändert |
| 2 · Konventions-Attribut | `static/premium/ff-premium.js` | Der Button trägt zusätzlich `data-ff-skip-read` — die etablierte Konvention, die alle ff-voice.js-Extraktoren respektieren |
| 3 · Extraktor-Immunisierung | `static/premium/ff-voice.js` | `readableText()` entfernt jetzt **jegliche `<button>`-Knoten** vor jeder Extraktion (Kurzfassung, Klartext, Vorlesen, Fortschritt); `buildToc()` wäscht zusätzlich `§/¶/#` aus den Labels (`cleanHeadingLabel`, gleiche Konvention wie ff-mini-toc) |

Zusätzlich (Premium-Politur):

- **Kopier-Feedback**: Nach erfolgreichem Copy wird das Glyph zu **„✓“**
  (grüner Zustand via `.ff-copied`, Rückfall nach 1,5 s) — statt nur Farbwechsel.
- **CSS** (`assets/css/extended/z-premium-blog.css`): Glyph ist
  `user-select: none` (keine Textmarkierung, kein Kopier-Artefakt) + ruhige
  Zeilenhöhe.
- **Zugänglichkeit bleibt**: Der Button behält sein `aria-label`
  („Link zu diesem Abschnitt kopieren“ / „Link kopiert“) — Screenreader
  annoncierten das „§“ nie als Inhalt; jetzt ist das Markup auch
  semantisch korrekt (dekoratives Glyph = aria-hidden).
- **Redaktioneller „§“-Text bleibt erhalten**: „§ 8 EinSiG“ im Artikeltext
  (Rechtsgrundlagen) wird von der Kurzfassung weiterhin korrekt übernommen —
  nur UI-Schmuck wird entfernt, nie Inhalt.

Rezept-Unterschied zur Tonspur: **kein**. Der Server-Generator erzeugt die
Studio-Tonspur aus dem Markdown und sah den Button nie — die Browser-Engine
spricht jetzt exakt das, was die Tonspur schon immer gesagt hat.
`VOICE_VERSION`/`RECIPE_VERSION` bleiben `2026.09.11` (keine
Tonregenerierung nötig; Cache-Busting läuft über den Deploy-SHA).

## 4 · Betroffene Dateien

| Datei | Änderung |
|---|---|
| `static/premium/ff-premium.js` | `addHeadingCopyButtons`: aria-hidden-Glyph, `data-ff-skip-read`, ✓-Feedback |
| `static/premium/ff-voice.js` | `readableText()`: Buttons vor Extraktion entfernt; `cleanHeadingLabel()` + `buildToc()`-Wäsche |
| `assets/css/extended/z-premium-blog.css` | `.ff-heading-copy__glyph`: user-select/line-height |
| `scripts/ff_heading_glyph_guard_test.mjs` | **Neu** — 33 Gates, „§“-Wache (echte DOM, echte Produktions-Dateien) |
| `scripts/ff_voice_tts_hardening_test.mjs` | — (Version-Pin unverändert geblieben) |
| `.github/workflows/lesehilfen-gate.yml` | Neue Wache + Pfade `ff-premium.js`, `z-premium-blog.css`, Guard-Test |
| `README.md` | Wächter-Liste ergänzt |

## 5 · Verifikation (alle Grün, lokale Ausführung 10.09.2026)

| Suite | Ergebnis |
|---|---|
| `node --check static/premium/ff-premium.js` / `ff-voice.js` | Syntax OK |
| `node scripts/ff_heading_glyph_guard_test.mjs` (neue Wache) | **33/33** |
| `node scripts/ff_voice_functional_test.mjs` | **218/218** |
| `node scripts/ff_voice_voice_test.js` | **69/69** |
| `node scripts/ff_voice_repair_test.mjs` | **56/56** |
| `node scripts/ff_voice_tts_hardening_test.mjs` | **57/57** |
| `python3 scripts/ff_voice_parity_check.py` | **384/384** |
| `python3 scripts/ff_voice_toolbar_check.py` | **118/118** |

Inhalt der neuen Wache:

1. **Injection & Markup** — echte `ff-premium.js` setzt den Button an jede
   `h2[id]`/`h3[id]`; Glyph sichtbar, aber in aria-hidden-Span;
   `data-ff-skip-read` + `aria-label` + Position am Ende der Überschrift.
2. **Kurzfassung-Dialog/Klartext** — Dialog-Text, jeder Gliederungslink,
   Kopie: kein „§“; **Label-Vertrag**: Gliederung ≡ sichtbarem
   Überschriftentext (Zeichen für Zeichen).
3. **Vorlesen** — kein Sprechblock mit „§“; jeder H2-Block endet sauber
   mit Punkt/Fragezeichen.
4. **Inhaltsschutz** — „§ 8 EinSiG“ im Fließtext bleibt in Kernaussagen,
   Klartext und TTS; nur die Gliederung ist §-frei.
5. **Mini-TOC** — bleibt §-frei (Nur-H2-Vertrag).
6. **Im gesamten Blog** — alle 34 realen Artikel (Posts + Pillaren)
   durchlaufen Dialog, Klartext und Button-Markup: 0 Fehlende Buttons,
   0 „§“ in der Gliederung, 0 Label-Abweichungen.

## 6 · Dauerhafter Schutz

- **CI-Gate**: Die „§“-Wache läuft im **Lesehilfen-Gate**-Workflow bei jedem
  Push/PR auf `ff-premium.js`, `ff-voice.js`, `z-premium-blog.css`, den
  Lesehilfen-Layouts und Content — plus tägliche 08:20-MESZ-Wache.
  Bricht sie, blockiert der Deploy.
- **Strukturelle Immunität**: Selbst wenn künftig irgendeine UI-Komponente
  in einen Inhaltselemente injiziert wird, sehen Kurzfassung, Klartext-Kopie,
  Vorlesen und Fortschrittsanzeige sie nicht — Buttons sind für die
  Extraktion tote Materie, und Labels laufen zusätzlich durch
  `cleanHeadingLabel()`.
