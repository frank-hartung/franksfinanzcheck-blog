# VORLESEN v11 — Tabellenstruktur, Fettdruck an seiner Stelle, korrekter Fortschritt

**Datum:** 05.09.2026
**Produktivcode:** `static/premium/ff-reader.js` (Browser-Stimme) ·
`scripts/generate_reader_audio.py` + `scripts/reader_tts_backends.py` (Tonspur)
**Dauerwache:** `scripts/reader_table_progress_test.mjs` (neu) ·
`scripts/reader_blocks_dump.py` (neu) · `.github/workflows/lesehilfen-gate.yml`

Drei gemeldete Fehler, alle drei bestätigt — und alle drei hatten eine
messbare Ursache, keine vermutete:

1. **Fett gedruckter Text wurde übersprungen** (Beispielseite
   `pillar/strom-sparen/`, „Das Wichtigste auf einen Blick",
   `**Tarifwechsel als größter Hebel:**`).
2. **Zeilen und Spalten von Tabellen wurden nicht erkannt.**
3. **Die Fortschrittsanzeige arbeitete nicht korrekt.**

Grundlage war keine Vermutung, sondern ein Protokoll: Die echte
`ff-reader.js` lief in einer echten DOM (jsdom) über den echten Klickpfad, und
parallel lief die echte Block-Extraktion des Tonspur-Generators über dieselbe
HTML. Beide Protokolle liegen diesem Report zugrunde.

---

## 1. Befund: Was nachweislich falsch war

### 1.1 Fettdruck wurde nicht übersprungen — er wurde ans Satzende verschoben

Der Text **war** in der Tonspur, aber an der falschen Stelle. Gemessen an
`pillar/strom-sparen/`:

```
Browser (ff-reader.js):  „Tarifwechsel als größter Hebel: Ein Wechsel … pro Jahr."
Tonspur (Generator):     „Ein Wechsel … pro Jahr. Tarifwechsel als größter Hebel:"
```

**Ursache:** `DocParser` in `scripts/generate_reader_audio.py` sammelte den
gesamten direkten Text eines Elements in einem Feld `node.text` und hängte die
Kind-Elemente danach an. `element_text()` gab erst `node.text` aus, dann die
Kinder:

```python
if n.text:            # „Ein Wechsel … pro Jahr."
    parts.append(n.text)
for c in n.children:  # <strong>Tarifwechsel als größter Hebel:</strong>
    walk(c)
```

Damit landete **jedes** `<strong>`, `<a>`, `<em>`, `<code>` und `<span>` am
Ende seines Blocks. Gemessen: **27 von 93 Blöcken** des Ratgebers wichen
zwischen Tonspur und Browser ab. Für die Hörerin klingt eine Einleitung, die
nach dem Satz kommt, wie ein übersprungener Fettdruck — die Meldung war
exakt richtig, nur die Beschreibung der Ursache nicht.

Zusätzlich trennte `element_text()` die Textstücke mit `" ".join(parts)`:
Aus `Ein <strong>fett</strong>er Teil` wurde `„fett er"`.

### 1.2 Tabellen: fünf verschiedene Erkennungsfehler

| # | Fall | Befund (gemessen) |
|---|---|---|
| 1 | Tabelle **ohne `<thead>`** | Kopfzeile wurde als Datenzeile gesprochen: `„Anbieter. Zeile 1 von 3. Preis: Preis. Bonus: Bonus."` |
| 2 | **`<tfoot>`** | Summenzeile verschwand komplett — `360 €` wurde nie gesprochen |
| 3 | **`colspan`** | `„Übersicht mit 5 Spalten"`, Zeile als `„Öko. Test: 31 Cent. Tarif: 1,5."` — Spaltennamen verschoben |
| 4 | **Link in der ersten Zelle** | `len(rest) < 12` warf die Zeile weg: `„Übersicht mit 2 Spalten und **0 Zeilen**"` |
| 5 | **`role="table"` ohne `rowgroup`** | Tonspur: die ganze Übersicht blieb **stumm** (0 Tabellen-Blöcke) |

Dazu: Der Tabellen-Titel fiel nicht auf die vorangehende Überschrift zurück
(nur der Browser-Pfad tat das), und die Summenzeile der Einsparübersicht
erklang doppelt (`„Zusammengerechnet: Summe. Ersparnis: 450 Euro."`).

### 1.3 Fortschrittsanzeige

| # | Befund | Wirkung |
|---|---|---|
| 1 | Der Zeit-Ticker startete erst mit `onstart` | Stimmen, die `onstart` spät oder nie liefern, ließen die Leiste stehen |
| 2 | Die Schätzung nutzte `unit.effRate`, gesprochen wurde der auf 0,5–1,25 **begrenzte** Wert | Die Leiste lief der Stimme systematisch davon |
| 3 | Obergrenze 98,5 %, am Ende sofort `scaleX(0)` | „Fertig" war nie sichtbar; gemessen: `0.9767 → 0.0000` |
| 4 | `highlight()` setzte die Leiste bei jedem Satz auf `spokenChars` | Beim Fortsetzen aus einer Atempause sprang sie sichtbar zurück |
| 5 | Restzeit rechnete mit einem eigenen Zeichen/Minute-Wert | Leiste und „noch ca. X Min." liefen auseinander |
| 6 | `„Hördauer etwa 1 Minuten"` | Zahlwort-Fehler im Intro jedes einminütigen Artikels |

---

## 2. Reparatur

### 2.1 Dokumentreihenfolge (Tonspur)

`Node` führt Text jetzt als eigenes Kind (`tag == "#text"`), der Parser hängt
ihn an seiner Stelle im Dokument an. `element_text()` und
`element_text_without()` laufen in Dokumentreihenfolge und **konkatenieren**
statt mit Leerzeichen zu joinen — der Quelltext bringt seine Leerzeichen
selbst mit. Ergebnis: `„Tarifwechsel als größter Hebel: Ein Wechsel …"`.

### 2.2 Ein Tabellenmodell für beide Tonpfade

`table_model()` (Python) und `buildTableModel()` (JS) bauen dieselbe Struktur:

- **Zeilen** in Dokumentreihenfolge aus `thead`/`tbody`/`tfoot`, direkten
  `<tr>` und ARIA (`[role=rowgroup] > [role=row]` sowie `[role=row]` direkt).
- **Kopfzeile** aus `thead`; fehlt es, gilt die erste Zeile nur dann als Kopf,
  wenn sie ausschließlich aus `<th>`/`[role=columnheader]` besteht und weitere
  Zeilen folgen.
- **Spalten** mit aufgelöstem `colspan` (`{ col, cell, span }`) — der
  Spaltenindex ist die Position im Raster, nicht der Zellenzähler. Bei
  gestapelten Kopfzeilen gewinnt die untere (genauere); der Gruppentitel
  füllt nur Lücken.
- **Aktionszeilen** werden nur noch verworfen, wenn **außerhalb** von
  Links/Buttons kein Text steht. Datenzeilen mit Link bleiben erhalten.
- **Summenzeilen** über `.ff-es-sum`/`.ff-tv-sum`, `<tfoot>` oder ein
  Etikett wie `Summe`/`Gesamt`/`Insgesamt`; bei genau einem Wert entfällt
  der Spaltenname (`„Zusammengerechnet: 450 Euro."`).
- **Titel-Kaskade**: `aria-label` → `caption`/`figcaption` →
  `.ff-tv-title`/`.ff-es-title` → vorangehende Überschrift → Standard.

### 2.3 Fortschritts-Engine

Ein Zeiger, drei Quellen, eine Regel:

1. Der Ticker läuft, **sobald die Einheit in die Sprach-Queue geht**;
   `onstart` verankert die Schätzung neu (`_progressReanchor`), statt den
   Ticker erst zu starten.
2. `boundary` korrigiert präzise, `onend` setzt exakt.
3. Der Zeiger ist **monoton**. Zurückgesetzt wird er ausschließlich durch
   Benutzeraktionen (`resetProgressChars`: Neustart, Abschnittssprung,
   Beenden) — nie durch ein verspätetes Callback.
4. Am Ende wird **100 %** gezeigt (`completeProgress`), 1,2 s gehalten und
   dann in den Ruhezustand zurückgesetzt.
5. Die **Restzeit** summiert dieselben `estimatedSpeechMs()`-Werte wie die
   Leiste — ein Rechenweg statt zweier.
6. `estimatedSpeechMs()` rechnet mit dem Tempo, das die Utterance wirklich
   bekommt (0,5–1,25), nicht mit dem ungebremsten `effRate`.
7. Im Tonspur-Modus zeigt der Balken beim Wiedereinstieg sofort die richtige
   Position (`paintAudioProgress`) statt bis zum ersten `timeupdate` bei 0.

### 2.4 Zahlwort-Kongruenz

`durationPhrase()` (beide Sprachen): `eine Minute` / `one minute` statt
`1 Minuten`. Ebenso `1 Spalte` statt `1 Spalten`.

### 2.5 Entity-Reste

`&nbsp;`, `&amp;`, `&shy;`, `&euro;` und übrige Zeichenreferenzen werden vor
der Aussprache aufgelöst — `„300 und nbsp Euro"` ist damit ausgeschlossen.

---

## 3. Parität als Dauergate (neu)

Tonspur und Browser-Reader sind zwei Implementierungen derselben Extraktion.
Weichen sie ab, hört der Nutzer einen anderen Text, als die Live-Markierung
zeigt. Neu:

- `scripts/reader_blocks_dump.py` gibt die Blockliste der Tonspur als JSON aus.
- `scripts/reader_table_progress_test.mjs` vergleicht sie **Block für Block**
  mit `collectBlocks()` aus der echten `ff-reader.js` (jsdom) — für sieben
  Konstrukt-Fixtures und für den echten Ratgeber `pillar/strom-sparen/`.

**Ergebnis: 93 Blöcke, 0 Abweichungen** (vorher 27).

---

## 4. Funktionstest

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `node scripts/reader_table_progress_test.mjs` (neu) | **125/125 grün** |
| `python3 scripts/generate_reader_audio.py --selftest` | **104/104 grün** |
| `node scripts/reader_functional_test.mjs` | **172/172 grün** |
| `node scripts/reader_structure_loudness_test.mjs` | **51/51 grün** |
| `node scripts/reader_engine_check.js` | **58/58 grün** |
| `node scripts/reader_male_voice_highend_test.js` | **58/58 grün** |
| `node scripts/reader_playback_function_test.js` | **12/12 grün** |
| `node scripts/reader_v7_function_test.js` | **17/17 grün** |
| `node scripts/summary_engine_check.js` | grün |
| `python3 scripts/reader_tts_backends.py --selftest` | **79/79 grün** |
| `python3 scripts/reader_prosody_parity_check.py` | grün |
| `python3 scripts/reader_toolbar_check.py` | grün |

Die neue Suite prüft in echter DOM: Fettdruck an seiner Stelle in Liste,
nummerierter Liste, Absatz und Tabellenzelle; Links und `<em>` in
Satzmitte; 13 Tabellen-Konstrukte (ohne `<thead>`, ARIA mit und ohne
`rowgroup`, `colspan`, Link in der Zelle, Aktionszeile, leere Zellen,
`<tfoot>`, `scope="row"`, mehrere `<tbody>`, Einsparübersicht, Titel aus der
Überschrift); Zahlwort-Kongruenz; Fortschritt (Start, Monotonie, Pause,
Fortsetzen, Abschnittssprung, 100 %, Ruhezustand); Entity-Reste; und die
Block-Parität beider Tonpfade.

Ein Test wurde **bewusst geändert**, nicht gelockert: Am Artikelende muss die
Leiste jetzt `scaleX(1)` zeigen und danach in den Ruhezustand zurückkehren.
Die Prüfung beobachtet den Ausschlag (`maxProgressRatio >= 0.999`) und zählt
Rückwärtssprünge während der Wiedergabe (`0`).

Zwei weitere Korrekturen betrafen die **Messumgebung**, nicht das Produkt:

- `scripts/reader_qa_lib.mjs` escapte `&` blind, machte aus `&nbsp;` also
  `&amp;nbsp;` und ließ die Suite `„300 und nbsp Euro"` messen. Goldmark
  reicht Zeichenreferenzen unverändert durch — die Fixture tut das jetzt auch.
- Die Zählung nummerierter Listen zählte Textknoten mit (`Punkt 2` statt
  `Punkt 1`), seit Text eigene Kinder sind.

---

## 5. Ehrliche Grenze

Nicht geprüft bleibt der **physisch hörbare Ton**: jsdom synthetisiert nichts,
und die Tonspur entsteht erst im Deploy. Verifiziert ist der vollständige
Vertrag bis unmittelbar vor die Audio-Ausgabe — Text, Sprache, Stimme, Tempo,
Tonlage und Pegel jeder Sprech-Einheit sowie die Blockfolge der Tonspur.
Weiterhin gilt: Eine echte Geschlechtsgarantie kann nur ein Betriebssystem
geben, das eine männliche Stimme bereitstellt; ohne eine solche startet der
Reader hörbar in der richtigen Sprache und kennzeichnet den Fallback ehrlich.
