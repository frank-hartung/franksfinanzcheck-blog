# VORLESEN v10 — Vollständige Struktur & automatische Lautstärkenanpassung

**Datum:** 05.09.2026
**Produktivcode:** `static/premium/ff-reader.js` (Browser-Stimme) ·
`scripts/generate_reader_audio.py` + `scripts/reader_tts_backends.py` (Tonspur)
**Dauerwache:** `scripts/reader_structure_loudness_test.mjs` (neu) ·
`.github/workflows/lesehilfen-gate.yml`

Zwei Aufträge: (1) Überschriften, Teil-Überschriften, Tabellen und Übersichten
**vollständig** auf Agentur-Niveau vorlesen, (2) eine **automatische
Lautstärkenanpassung** der männlichen Stimme für Deutsch und Englisch **ohne
Umschalter**.

Grundlage war kein Umbau auf Verdacht, sondern eine Messung: Die echte
`ff-reader.js` lief in einer echten DOM (jsdom) über den echten Klickpfad, und
jeder `speak()`-Aufruf wurde mit Text, Sprache, Tempo, Tonlage und Pegel
protokolliert. Die folgenden Befunde stammen aus diesem Protokoll.

---

## 1. Befund: Was nachweislich fehlte

| # | Befund | Wirkung für die Hörerin |
|---|---|---|
| 1 | **`h5`/`h6` wurden nie gesprochen.** Der Selektor endete bei `h4`. | Ganze Gliederungsebenen fehlten lautlos. |
| 2 | **Kopfzeile, Unterzeile und Fußnote der Premium-Übersichten fehlten.** `.ff-tv-title`, `.ff-tv-sub`, `.ff-tv-footnote` (und `.ff-es-*`) stehen **außerhalb** der Tabelle und waren in keinem Selektor. | „Tarifvergleich Strom“ und der Hinweis „Alle Preise gelten für das erste Vertragsjahr“ wurden nie vorgelesen. |
| 3 | **Die mobile Kartenansicht wurde zusätzlich gelesen.** `.ff-tv-cards` / `.ff-es-cards` enthalten denselben Inhalt wie die Tabelle (CSS schaltet um). | Jede Zahl wurde doppelt gesprochen. |
| 4 | **`<br>` verschmolz Wörter.** `1200 Euro<br><small>pro Jahr</small>` ergab `textContent` = **„1200 Europro Jahr“**. | Hörbar falsche Wörter in genau den Zellen, in denen die Zahlen stehen. |
| 5 | **Tabellen hießen alle „Übersichtstabelle“.** Der Titel wurde nicht aus der Übersichts-Kopfzeile gelesen. | Bei mehreren Tabellen war nicht unterscheidbar, welche gemeint war. |
| 6 | **„Übersicht mit 3 Spalten und 1 Zeilen“.** Keine Zahlwort-Kongruenz. | Der klassische Roboter-Verräter. |
| 7 | **Reine Button-Zeilen wurden als Datenzeile vorgelesen** und verfälschten die Zählung („Zeile 3 von 3: Stromanbieter vergleichen“). | Zählung und Inhalt wurden unbrauchbar. |
| 8 | **Die Lautstärke war statisch.** Nur drei feste Werte (`0.98`, `0.99`, `1.00`) aus der Rollentabelle, ohne jeden Ausgleich. | Tabellenzeilen (schneller + höher + leiser) wirkten deutlich leiser als Überschriften. |

---

## 2. Automatische Lautstärkenanpassung (Auto-Gain)

Neu in `static/premium/ff-reader.js`: `autoVolume()` — eine Lautheitsregelung
nach dem Prinzip einer Sendestudio-Regie (EBU R128 / ITU-R BS.1770 im Prinzip;
eine echte Messung ist unmöglich, weil die Web Speech API kein Ausgangssignal
liefert). Sie ersetzt die starre Rollen-Amplitude:

1. **Ziel-Lautheit je Rolle** (`LOUDNESS_TARGET`) statt fester Amplitude.
2. **Wahrnehmungs-Ausgleich:** schneller und höher gesprochene Einheiten wirken
   leiser und werden angehoben (Fletcher-Munson-Näherung).
3. **Kurze Einheiten** (Tabellenzellen, Aufzählungen) bekommen einen Zuschlag —
   sie sind sonst „weggehuscht“.
4. **Sprach-Ausgleich DE/EN:** englische Stimmen derselben Familie sind im
   Katalog im Mittel leiser gemastert (+0.02). Das ist der Kern von
   „**ohne Umschalter**“: Ein englischer Satz im deutschen Artikel wird nicht
   leiser.
5. **Stimmenklasse:** einfache (nicht-neurale) Stimmen klingen dumpfer und
   erhalten mehr Pegel (bis +0.05).
6. **Soft-Limiter** statt harter Kappung — nichts verzerrt, nichts übersteuert.
7. **Nachbarschafts-Glättung:** der Sprung zwischen zwei aufeinanderfolgenden
   Einheiten bleibt unter `LOUDNESS_MAX_STEP` (0.06).

Grenzen: `LOUDNESS_FLOOR = 0.72` (nie unhörbar), `LOUDNESS_CEIL = 1.00` (nie
übersteuert). Die Funktion ist **deterministisch** — gleiche Eingabe, gleicher
Pegel —, damit Tonspur-Parität und Tests reproduzierbar bleiben.

**Gemessen** (Fixture mit Gliederung h2–h6, zwei Übersichten, drei Tabellen):

| Kennzahl | vorher | nachher |
|---|---|---|
| verschiedene Pegel | 3 (starr) | 17 (geregelt) |
| größter Sprung zwischen Einheiten | — | **0.021** (Grenze 0.06) |
| Pegelfenster | 0.98 – 1.00 | 0.966 – 0.997 |
| ⌀-Abstand DE ↔ EN | ungeregelt | **≤ 0.05** (gleiches Fenster) |

---

## 3. Vollständigkeit auf Agentur-Niveau

- **Gliederung:** `h2`–`h6` vollständig, jeweils mit Satzschluss; FAQ-Fragen
  behalten ihr Fragezeichen (eine Frage bleibt hörbar eine Frage).
- **Übersichten:** Titel (`overview-title`), Unterzeile und Fußnote
  (`overview-note`) werden als eigene Rollen mit eigener Regie gesprochen —
  die Übersicht wird angekündigt, der Hinweis danach ruhiger nachgereicht.
- **Tabellen:** echter Titel aus der Übersichts-Kopfzeile statt
  „Übersichtstabelle“; korrekte Zahlwort-Kongruenz („und **einer Zeile**“);
  bei genau einer Zeile entfällt das überflüssige „Zeile 1 von 1“;
  **Summenzeilen** (`.ff-es-sum`) werden als `table-sum` angekündigt
  („Zusammengerechnet: …“) statt als beliebige Zeile unterzugehen.
- **Keine Doppelung:** die mobile Kartenansicht bleibt stumm, die Tabelle ist
  die vollständigere Quelle.
- **Reine Button-/Deko-Zeilen** werden vor der Zählung entfernt, damit
  „Zeile 2 von 3“ wieder stimmt.
- **`<br>` und Blockgrenzen** sind Wortgrenzen. Inline-Auszeichnungen
  (`strong`, `em`, `span`, `small`) werden bewusst **nicht** getrennt — sonst
  würde aus `<strong>fett</strong>er` ein gesprochenes „fett er“. Dieser Fall
  ist als Test abgesichert.

---

## 4. Parität: Browser-Stimme ≡ vorab vertonte Tonspur

Der Reader hat zwei Regien (lokale Web-Speech-Stimme und die serverseitig
erzeugte Tonspur). Laufen sie auseinander, klingt derselbe Artikel je nach
Gerät anders. Alle Änderungen wurden daher **beidseitig** nachgezogen:

- neue Rollen `h5`, `h6`, `table-sum`, `overview-title`, `overview-note` in
  `reader_tts_backends.py` (`PROSODY`) — wertgleich zum JS;
- Block-Extraktion in `generate_reader_audio.py`: h5/h6, Übersichts-Kopf/-Fuß,
  Karten-Unterdrückung, CTA-Zeilen-Filter, Summenzeilen, echter Tabellentitel,
  Singular/Plural;
- `element_text()` trennt jetzt `<br>` und Blockgrenzen wie `readableText()`.

Das Paritäts-Gate hat die Abweichung während der Arbeit **selbst gemeldet**
(„Keine Leserolle ohne Tonspur-Pendant → h5, h6, overview-note, overview-title,
table-sum“) und ist nach dem Nachziehen wieder grün.

---

## 5. Prüfergebnis

Alle Suiten laufen lokal grün; die neue Suite ist im `lesehilfen-gate`-Workflow
verdrahtet (inklusive des bisher dort fehlenden Paritäts-Gates).

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `node scripts/reader_functional_test.mjs` | **163/163 grün** |
| `node scripts/reader_structure_loudness_test.mjs` *(neu)* | **51/51 grün** |
| `node scripts/reader_engine_check.js` | **58/58 grün** |
| `node scripts/reader_male_voice_highend_test.js` | **58/58 grün** |
| `node scripts/reader_playback_function_test.js` | **12/12 grün** |
| `node scripts/reader_v7_function_test.js` | **17/17 grün** |
| `node scripts/summary_engine_check.js` | **26/26 grün** |
| `python3 scripts/generate_reader_audio.py --selftest` | **86/86 grün** |
| `python3 scripts/reader_tts_backends.py --selftest` | **79/79 grün** |
| `python3 scripts/reader_prosody_parity_check.py` | **107/107 grün** |
| `python3 scripts/reader_toolbar_check.py` | Alle Gates grün |

Die neue Suite prüft in echter DOM: Gliederung h2–h6, Tabellenwerte und
Spaltenzuordnung, Übersichts-Kopf/-Unterzeile/-Fußnote, Summenzeilen,
Nicht-Doppelung der Kartenansicht, `<br>`-Worttrennung, Zahlwort-Kongruenz,
das Lautheitsfenster, den maximalen Pegelsprung sowie **denselben Nachweis auf
Englisch** und mit einem einfachen Stimmenkatalog.

---

## 6. Ehrliche Grenze

Nicht geprüft (und technisch nicht prüfbar) bleibt der **physisch hörbare
Ton**: jsdom synthetisiert nichts. Verifiziert ist der vollständige Vertrag bis
unmittelbar vor die Audio-Ausgabe — Text, Sprache, Stimme, Tempo, Tonlage und
Pegel jeder einzelnen Sprech-Einheit. Ebenso gilt weiterhin: Eine echte
Geschlechtsgarantie kann nur ein Betriebssystem geben, das eine männliche
Stimme bereitstellt; ohne eine solche startet der Reader hörbar in der
richtigen Sprache und kennzeichnet den Fallback ehrlich.
