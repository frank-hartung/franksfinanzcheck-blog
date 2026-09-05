# VORLESEN · TABELLEN & ÜBERSICHTEN — High-End-Upgrade

**Datum:** 05.09.2026 · **Projekt:** FranksFinanzcheck · **Modul:** FF Voice Studio (Vorlese-Funktion)

---

## 1 · Auftrag

Das bestehende TTS-Modell (Vorlese-Funktion: männliche Stimme, Deutsch und Englisch ohne Umschalter) konnte **Tabellen und Übersichten nicht vollständig mit Zeilen und Spalten erkennen und vorlesen**. Befund und Behebung auf **High-End-Level einer Premium-Agentur**.

### Befund vor dem Upgrade (mit echter Engine reproduziert)

| Fall | Verhalten vorher |
|---|---|
| Markdown-Tabelle (Render-Hook `.ff-table-scroll`) | Titel verloren → „Übersichtstabelle“ statt der Überschrift davor |
| ARIA-Tabelle (`role="table"`/`"grid"` auf `<div>`, Zeilen über `role="row"`) | **0 Spalten, 0 Zeilen — nichts wurde gelesen** |
| `colspan`/`rowspan` | Zellen in falsche Spalten verschoben, Zeilen verrutscht |
| Mehrzeilige Kopfzeilen | zweite Kopfzeile wurde zur Datenzeile |
| Einspartabelle (Shortcode) | Summenzeile im `<tbody>` als normale Zeile; Emoji ❌ ✅ 🏆 💰 wörtlich mitgesprochen |
| Tarifvergleich (Shortcode) | Affiliate-Button-Zeile als Datenzeile („Anbieter A: Zum Tarif“) ohne Werbekennzeichnung |
| Ziertext `<small>` in Zellen | mit Kopftext verschmolzen („Vorher Alter Verbraucher“) |

---

## 2 · Lösung — Tabellenmodell, Generation 2

Das Tabellenmodell wurde im Reader (`static/premium/ff-voice.js`) neu gebaut und **wortgleich** in den Tonspur-Generator (`scripts/ff_voice_audio.py`) gespiegelt — die Block-Parität (Index `b` der Tonspur ≡ `collectBlocks()` des Readers) bleibt gewahrt und wird vom Paritäts-Gate Block für Block geprüft.

### 2.1 Vollständige Erkennung

- **HTML-Tabellen** wie bisher. Verschachtelte Innentabellen werden als Zelleninhalt der Außentabelle gesprochen — nie ein zweites Mal als eigene Tabelle, nie mit Geisterspalten.
- **ARIA-Tabellen**: `role="table"`, `role="grid"`, `role="treegrid"` auf `<div>`/`<span>`, Zeilen über `role="row"`, Zellen über `role="cell"`/`"gridcell"`/`"columnheader"`/`"rowheader"`, Spannen über `aria-colspan`/`aria-rowspan`.
- **Logisches Gitter**: `colspan`/`rowspan` werden aufgespannt. Jede Zelle erscheint in genau ihrer Spalte — colspan-Fortsetzungen schweigen, rowspan-Werte werden in jeder überspannten Zeile wiederholt (Screenreader-Konvention). Nichts verschoben, nichts verloren, nichts doppelt.
- **Mehrzeilige Köpfe**: die unterste Kopfzeile trägt die Spaltennamen; darüberliegende Zeilen werden angesagt („Kopfzeile 1: Energie, Wasser.“).
- **Zeilentitel**: `th scope="row"` / `role="rowheader"` werden zum Namen der Zeile („Zeile 1 von 2: Miete. Kosten: 900 Euro.“).

### 2.2 Eigene Rollen statt „alles ist Datenzeile“

| Rolle | Erkennung | Gesprochen |
|---|---|---|
| `table-intro` | — | „Tabelle: {Titel}. Übersicht mit {n} Spalten und {m} Zeilen.“ — zählt **nur echte Datenzeilen** |
| `table-header` | `<thead>` / reine Kopfzeilen | „Die Spalten lauten: …“ (+ je eine „Kopfzeile {n}: …“ darüber) |
| `table-row` | Datenzeile | „Zeile {i} von {n}. Spalte: Wert, …“ — mit Zeilentitel bei rowheader |
| `table-group` | Zeile nur aus Kopfzellen (z. B. `<th colspan>`) | „Gruppe: {Name}.“ |
| `table-sum` | `<tfoot>`, Klasse `ff-es-sum`/`ff-tv-sum` oder Summenwort (Summe, Gesamt, …) | „Zusammengerechnet: …“ — das Summenwort selbst fällt nicht doppelt |
| `table-cta` | Button/Partnerlink-Zeile (`ff-tv-btn`, `ff-es-btn`, `ff-cta`, `<button>`) | „Empfehlung: {Text}. Hinweis: Dies ist ein Partnerlink.“ — **Werbetransparenz auch im Audio** |
| `table-outro` | — | „Ende der Tabelle {Titel}.“ |

Leere Tabellen sprechen nichts; leere Zellen werden still übersprungen.

### 2.3 Titelauflösung (Kaskade)

1. `<caption>`
2. `aria-label` der Tabelle oder ihrer Wrapper — Allgemeinplätze wie „Tabelle“ (vom Table-Render-Hook automatisch gesetzt) werden verworfen
3. Premium-Headline (`.ff-tv-title`/`.ff-es-title`) bzw. `h3`/`h4` in der Wrapper-Kette nach oben
4. unmittelbar davorstehende Überschrift (`h2`–`h6`) — dadurch bekommen **alle Markdown-Tabellen den Titel ihrer Zwischenüberschrift**
5. Fallback „Übersichtstabelle“

### 2.4 Sprechsprache in Tabellen

- **Schmuck-Emoji und Pfeile** (💰 ❌ ✅ 🏆 → …) werden still entfernt — in Tabellen bei der Extraktion, global in der Aussprache-Normalisierung (DE & EN, Reader & Generator wortgleich).
- **`<small>`-Ziertext** wird mit Komma angebunden: „Vorher, Alter Verbraucher“, „890 Euro, pro Jahr“.
- Neue Prosodie-Profile für `table-group` und `table-cta` in beiden Regien (Rezept-Version `ff-voice-2026.09.05-b` — alte Tonspuren werden beim nächsten Lauf automatisch neu erzeugt, Fingerprint-Wechsel).

### 2.5 Kurzfassung (Dialog)

„Tabellen & Übersichten im Fokus“ zeigt jetzt eine **Mini-Vorschau** (Kopfzeile + erste drei Datenzeilen, `aria-hidden` — das Vorlese-Modell bleibt die einzige Audio-Quelle, nichts wird doppelt gesprochen) plus „+ N weitere Zeilen“. Die Kopieren-Funktion enthält die Tabellen jetzt ebenfalls.

---

## 3 · Beispiele — vorher / nachher

**ARIA-Tabelle** — vorher: *„Übersicht mit 0 Spalten und 0 Zeilen.“* (nichts) — nachher:

> Tabelle: Beispielhaushalt. Übersicht mit 2 Spalten und 2 Zeilen. Die Spalten lauten: Posten, Kosten. Zeile 1 von 2: Miete. Kosten: 900 Euro. Zeile 2 von 2: Strom. Kosten: 120 Euro. Ende der Tabelle Beispielhaushalt.

**Einspartabelle** — nachher:

> Tabelle: Einsparpotenziale im direkten Vergleich. Übersicht mit 4 Spalten und einer Zeile. Die Spalten lauten: Maßnahme, Vorher, Alter Verbraucher, Nachher, Optimierte Lösung, Ersparnis, pro Jahr. Zeile 1 von 1. Maßnahme: Alte Heizungspumpe tauschen, Vorher, Alter Verbraucher: 890 Euro, pro Jahr, … Zusammengerechnet: … Empfehlung: Stromanbieter vergleichen. Hinweis: Dies ist ein Partnerlink. Ende der Tabelle …

**Markdown-Tabelle unter Zwischenüberschrift** — nachher mit echtem Titel:

> Tabelle: Kosten im Überblick. Übersicht mit 3 Spalten und 2 Zeilen. …

---

## 4 · Tests & Gates (alle grün)

| Suite | Ergebnis | Neuerung |
|---|---|---|
| `ff_voice_functional_test.mjs` (echte DOM) | **174/174** (vorher 145) | neue Gruppen „3b) Tabellen vollständig: Zeilen, Spalten, ARIA, Werbelinks“ und „3c) Innentabellen einmal, leere Tabellen stumm“ + Dialog-Vorschau-Gates |
| `ff_voice_parity_check.py` | **269/269** (vorher 176) | 4. Fixture-Seite `PAGE_TABLES_PREMIUM` (Render-Hook-Wrapper, ARIA-Grid, colspan/rowspan, Summe im tbody, CTA, `<small>`, Innentabelle, leere Tabelle), Rollen `table-group`/`table-cta` geprüft |
| `ff_voice_audio.py --selftest` | **48/48** (vorher 31) | `FIXTURE_TABLES` mit 18 Tabellen-Prüfungen |
| `ff_voice_voice_test.js` | 71/71 | unverändert |
| `ff_voice_toolbar_check.py` | 89/89 | unverändert |
| `ff_voice_backends.py --selftest` | 44/44 | unverändert |

Vertrag bleibt bestehen: Reader, Generator und Kurzfassung teilen dieselbe Lesereihenfolge; die Parität wird bei jedem Lauf des Gates **gemessen**, nicht behauptet.

---

## 5 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `static/premium/ff-voice.js` | Tabellenmodell Gen. 2 (Gitter, ARIA, Rollen, Titel-Kaskade), Decor-Bereinigung, Prosodie-Rollen, Dialog-Vorschau, Version `2026.09.05-b` |
| `scripts/ff_voice_audio.py` | wortgleiche Spiegelung, `FIXTURE_TABLES`, Selbsttest erweitert |
| `scripts/ff_voice_backends.py` | Prosodie-Rollen, Decor-Regel in `normalize_speech`, Rezept-Version `-b` |
| `scripts/ff_voice_parity_check.py` | 4. Fixture-Seite, neue Rollen im Check |
| `scripts/ff_voice_functional_test.mjs` | Gruppe 3b, Dialog-Gates |
| `assets/css/extended/ff-voice.css` | Styling der Tabellen-Vorschau im Dialog |
| `README.md` | Vollständigkeits-Beschreibung und Gate-Zähler aktualisiert |

Keine neuen Abhängigkeiten, keine Fremd-CDNs, keine Laufzeit-Netzaufrufe — First-Party bleibt First-Party.
