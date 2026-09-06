# VORLESEN-HIGHEND-REPORT — Sprachausgabe auf High-End-Verlagshaus-Niveau (v6)

**Datum:** 03.09.2026
**Produktivcode:** `static/premium/ff-reader.js`
**UI:** `layouts/_partials/reader_toolbar.html` · `assets/css/extended/ff-reader.css`

> **Korrektur 03.09.2026:** Die unten genannte Prüfung (106/106 grün) lief gegen eine
> handgebaute `FakeNode`-DOM, nicht gegen echtes DOM. Sie war grün, während die Funktion
> im Browser sichtbar fehlerhaft war. Die tatsächlichen Fehler, ihre Ursachen und die
> neue Wache stehen in **LESEHILFEN-REPARATUR-2026-09-03.md**. Maßgeblich ist ab jetzt
> `scripts/reader_functional_test.mjs` (jsdom, echte Engine-Datei, echte Templates).

## Befund und vollständige Reparatur

Die bisherige Vorlese-Engine bestand zwar aus Unit-Checks, hatte aber Fehler im realen Klickpfad:

- Der Voice-Katalog kann beim ersten Klick noch leer sein. Eine Warte-Schleife verzögerte `speechSynthesis.speak()` und konnte dadurch zu Stille führen.
- `SpeechSynthesisUtterance.voice` und `utterance.lang` waren nicht konsequent als Paar abgesichert. Dadurch konnte der Browser einen falschen Sprach- oder Standard-Voice verwenden.
- Die redaktionelle Aussprache-Normalisierung lief vor dem DE-/EN-Routing. Englische Sätze in deutschen Artikeln erhielten dadurch deutsche Zahlen- und Währungsregeln.
- Ein verspätetes `onend`/`onerror` eines abgebrochenen Utterance konnte die neue Wiedergabe fortschalten, doppelte Einheiten erzeugen oder die Position verlieren.
- Der Web-Audio-Chime war eine unnötige zusätzliche Autoplay-/Sperrfläche und konnte die eigentliche Speech-Queue auf mobilen Geräten stören.
- Der Kurzfassungsdialog gab bei nativer ESC-Schließung die Scroll-Sperre nicht zuverlässig frei; im Fallback fehlte die gleichwertige Fokusfalle.

### Reparatur auf v6-Niveau

1. **Deterministische männliche Voice-Auswahl**
   - Explizit männliche Stimmen werden je Sprache bevorzugt und direkt an die Utterance gebunden.
   - DE und EN werden pro Sprecheinheit automatisch erkannt; ein Umschalter ist nicht erforderlich.
   - `_` und `-` werden beim Erkennen von Voice-Kennungen korrekt behandelt; weiblich benannte Stimmen werden aussortiert.
   - Region und Locale der gewählten Stimme werden gemeinsam gesetzt (`voice.lang`), damit die Ausgabe nicht am Sprach-Mismatch scheitert.

2. **Sofortiger, robuster Tonpfad**
   - `speak()` wird beim Klick synchron aufgerufen, auch wenn `getVoices()` noch leer ist.
   - Ein Start-Watchdog erkennt Browser, die `speak()` akzeptieren, aber kein `onstart` liefern, und wiederholt die Einheit kontrolliert.
   - `voiceschanged` und ein begrenztes Pre-Warming übernehmen später geladene Stimmen automatisch für die folgenden Einheiten.
   - Kein künstlicher Chime, keine externe Audioquelle und kein Tracking.

3. **Stabiler Playback-Zustandsautomat**
   - Jede Wiedergabe erhält eine Generation; alte Callback-Ereignisse können neue Sprünge, Pausen oder Stops nicht mehr überschreiben.
   - Fehler werden pro Einheit maximal zweimal wiederholt. Danach geht der Artikel zugänglich weiter, statt komplett stumm zu bleiben.
   - Pause, Fortsetzen, Abschnittssprung, Stop, Sichtbarkeitswechsel und Media-Session sind gegen Queue-Rennen abgesichert.
   - Der Keep-Alive prüft die Queue, pausiert aber keine laufende Stimme mehr künstlich und erzeugt damit keine hörbaren Klicks.

4. **Aussprache und Barrierefreiheit**
   - Erst DE-/EN-Segmentierung, danach sprachabhängige Aussprache-Normalisierung; Zahlen, Daten, Währungen, Abkürzungen, URLs und Tabellen bleiben korrekt.
   - Tabellen, Listen, Warnboxen und Absätze werden weiterhin live markiert und mit der passenden Sprache gesprochen.
   - Native und nicht-native Kurzfassung unterstützen Fokusfalle, ESC, Scroll-Sperre, Fokus-Rückgabe und `aria-modal` gleichwertig.
   - Kontrast-Fallbacks und Forced-Colors-Regeln verhindern eine unbrauchbare Toolbar in älteren WebViews und High-Contrast-Modi.

> **Technische Grenze der Web Speech API:** Eine echte Geschlechtsgarantie ist nur möglich, wenn das Betriebssystem beziehungsweise der Browser eine männliche Stimme bereitstellt. Für jede bereitgestellte männliche DE-/EN-Stimme ist die Auswahl jetzt explizit und deterministisch. Wenn ein System keine männliche Stimme anbietet, startet der Reader nicht stumm, sondern hörbar mit der gewünschten Locale und kennzeichnet diesen technischen Fallback ehrlich.

## Funktionstest

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `node scripts/reader_engine_check.js` | **58/58 grün** |
| `node scripts/reader_male_voice_highend_test.js` | **36/36 grün** |
| `node scripts/reader_playback_function_test.js` | **12/12 grün** — echter Klickpfad, explizite DE-/EN-Voice, kein Doppel-/Skip-Aufruf, leerer/lazy Voice-Katalog |
| **Reader-Engine gesamt** | **106/106 grün** |
| `python3 scripts/reader_toolbar_check.py` | **Alle Gates grün** |
| `node scripts/summary_engine_check.js` | **26/26 grün** |

Der neue Playback-Test prüft bewusst den kompletten Aufruf bis zur Web-Speech-API: erster synchroner Klick, männliche deutsche Stimme, automatische englische Stimme innerhalb eines deutschen Artikels, Ausschluss weiblicher Stimmen, vollständiges Ende ohne Doppel-/Skip-Aufrufe sowie das Verhalten bei einem verzögert eintreffenden Voice-Katalog.
