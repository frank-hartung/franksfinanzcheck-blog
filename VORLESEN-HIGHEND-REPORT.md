# VORLESEN-HIGHEND-REPORT — Sprachausgabe auf Studio-Regie-Niveau

Datum: 03.09.2026 · Datei: `static/premium/ff-reader.js` (+493/−86 Zeilen)
Ziel: Die Funktion „Vorlesen“ übertrifft das Niveau von Verlagshaus-Vorlesefunktionen –
vollautomatisch, ohne Regler, ohne Stimmenwahl, ohne Umschalter.

## 1. Nur männliche Sprache (DE & EN, ohne Umschalter)

- **Nur-Männlich-Gate** (`isMaleCandidate`): weiblich benannte Stimmen werden grundsätzlich
  aussortiert (umfangreiche Namenslisten DE/EN, inkl. Querformen wie „Alexa“/„Daniela“).
- **Auswahl-Leiter** (`resolveMaleVoice`, je Sprache gecacht, `VOICE_EPOCH`-Invalidierung):
  1. beste männliche Studio-/Neural-Stimme der Artikelsprache (Modus `male`),
  2. beste männliche Stimme einer Nachbarsprache (Modus `cross`, z. B. macOS ohne deutsche
     Männerstimme) – niemals eine weibliche Stimme,
  3. einzige verfügbare Stimme der Sprache nur als Notnagel (Modus `fallback`) – die
     Tonlagen-Korrektur senkt sie dann automatisch in die männliche Zone ab (≤ 0.86).
- **Stimmen-Warte-Schutz**: Startet die Stimmenliste asynchron (Chrome), wartet die Engine
  bis zu 3 s, statt mit einer zufälligen (ggf. weiblichen) Standardstimme loszulesen.
- **Dubletten-Schutz** (`dedupeVoices`): Browser-Dubletten (gleicher Name/Sprache, andere
  voiceURI) werden entfernt – keine Zufalls-Auswahl mehr.
- **Satz-Routing wie ein zweisprachiger Hörfunk-Moderator**: Reine englische Sätze in einem
  deutschen Artikel liest automatisch die männliche EN-Stimme, deutsche Sätze in englischen
  Artikeln die männliche DE-Stimme. Erkennung über Stoppwort-Mehrheiten plus morphologische
  DE-Signale (Umlaute/ß, Endungen wie -ung/-keit/-iert) – bloße Lehnwörter („Online-Banking“,
  „ETF“) lösen keinen Sprecherwechsel aus. Beide Sprecher-Pools werden beim Start vorgewärmt.

## 2. Automatische Tempoanpassung

- Tempo = **Rolle** (Überschrift, Fließtext, Tabelle …) × **Stimmenklasse** × **Satz-Inhalt**:
  `contentRateFactor` erkennt lange Komposita, hohe Wortlängen, Zahlen und senkt das Tempo
  bis −9 %; kurze, alltagssprachliche Sätze werden bis +5 % flüssiger gelesen.
- Fragen/Ausrufe erhalten zusätzlich einen ruhigeren, betonenden Sprechfluss.
- Die Regie-Pausen vor Abschnitten sind an das zuletzt gesprochene Tempo gekoppelt.

## 3. Automatische maximale Chunk-Länge

- Kurze Sätze werden zu **natürlichen Atemgruppen** gebündelt (kein Einzelsatz-Stakkato).
- Lange Schachtelsätze werden an Nebensatz-/Komma-/Doppelpunkt-Grenzen geteilt.
- Obergrenze folgt der Stimmenklasse (`quality.maxChunk` 150–210); harte Kappe `HARD_CHUNK`
  240 Zeichen bleibt immer unter der Chrome-15-Sekunden-Abbruchgrenze.
- Fragen und Ausrufe sind immer eigenständige Sprecheinheiten (für Satzmelodie & Pausenraum).

## 4. Automatische Pausen-Skalierung

- Basis je Satzzeichen (Frage 340 ms > Doppelpunkt 300 ms > Ausruf 300 ms > Punkt 250 ms …).
- **Hör-Digest-Skala**: +1,5 % je Wort ab dem 7. Wort (max. +32 %) – lange Sätze bekommen
  mehr Verarbeitungszeit.
- Satzmelodie-Boni (Frage +80 ms, Ausruf +50 ms), dann Skalierung über die Stimmenklassen-
  Pausen-Skala (1.0 bis 1.22, adaptiv bis 1.5) und natürliche Tempo-Kopplung (schneller
  gesprochen → relativ kürzere Pause, nie unter 62 %).

## 5. Automatische Tonlagen-Korrektur

- Männliche Grund-Tonlage je Rolle und Stimmenklasse (`PROSODY`, `pitchShift`).
- **Satzmelodie**: Fragen steigen (+0.05), Ausrufe betonen (+0.02).
- **Mikro-Modulation gegen Monotonie** (`quality.dynamic`): nur bei einfachen Stimmen
  (standard/basic, mobil oder nach Fehler-Herabstufung), nie bei Neural-/Studio-Stimmen.
- **Korrektur-Eingriff**: weiblicher Notnagel wird abgesenkt, Clamping im sicheren Bereich.

## 6. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| Logik-Tests (Chunking, Routing, Pausen, Tonlage, Tempo) | 10/10 grün |
| Stimmen-Tests (Windows/Edge, macOS/Safari, Android, EN-Cross, Cache, Dedupe) | 8/8 grün |
| Real-Content-Test: 2.000 echte Artikel-Sätze | max. Chunk 240, 0 falsch EN-geroutet |
| `python3 scripts/reader_toolbar_check.py` (A11y-/Highend-Wache) | alle Gates grün |

Keine UI-Änderung: keine Tempo-Anzeige, keine Stimmenwahl, keine Tastenkürzel –
die Studio-Regie arbeitet vollautomatisch.
