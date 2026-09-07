# VORLESEN-FORTSCHRITT-REPARATUR 2026-09-07 — „Was wird gerade vorgelesen?“

**Datum:** 07.09.2026
**Gemeldeter Fehler (Produktion):**
„Dem bestehenden TTS-Modell (Vorlese-Funktion: männliche Stimme,
Deutsch und Englisch ohne Umschalter) fehlt eine Profi-Fortschrittsanzeige,
damit der Leser weiß, was gerade vorgelesen wird.“
**Auftrag:** den Blog dauerhaft zuverlässiger und robuster auf
High-End-Niveau einer Profi-Agentur halten **und** diese Lücke schließen.
**Betroffen:** FF Voice Studio (Vorlesen + Kurzfassung) — Layout,
Styling, Engine und die Lesehilfen-Gates.

---

## 1 · Befund

Der Reader hatte bereits einen gelben Progress-Meter mit Prozentwert,
Modus-Badge und Rollen-Label. Aber er beantwortete die Frage des Lesers
nicht wirklich:

| Frage des Lesers | Alte Anzeige | Folge |
|---|---|---|
| „Wie viel ist schon vorgelesen?“ | Prozentbalken ✓ | — |
| **„Welcher Satz wird GERADE vorgelesen?“** | Nur der Blockanfang (Absatz-Start, gekürzt auf 72 Zeichen) | Bei längeren Absätzen (3–6 Sätze) stand die Anzeige still, während die Stimme weitersprach. Der Leser konnte den gehörten Satz nicht im Text verorten. |
| „Wo im Artikel bin ich?“ | Kein Zähler | Keine Orientierung über die Gesamtlänge |
| „Bleibt die Stelle beim Pausieren sichtbar?“ | Label blieb stehen, aber unklar welcher Satz | Beim Fortsetzen war die Hörposition unklar |

Dazu kam ein Robustheits-Aspekt: Die Anzeige war nicht als dauerhaft
reservierte Fläche gebaut — ein nachträgliches Einblenden von Zeilen
hätte Layout-Sprünge (CLS) riskiert, ein Kernwert der Seite.

## 2 · Die Reparatur: Profi-Fortschrittsanzeige („Gerade vorgelesen“)

Die Vorlese-Leiste zeigt jetzt auf Verlags-Niveau, **was** in diesem
Moment gesprochen wird:

```
[ Studio ]   Absatz                            37 %
● Gerade vorgelesen   „Der Arbeitspreis liegt bei 12 Cent pro
                      Kilowattstunde – wer wechselt, spart …“
█████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
              Abschnitt 3 von 12 · noch ca. 6 Min.
```

1. **„Gerade vorgelesen“-Zeile** (`ff-voice-live`, Engine-Version
   `2026.09.09`): zeigt den **aktuell gesprochenen Satz**.
   - **Browser-Engine:** satzgenau — jede Sprecheinheit (Atemgruppe)
     aktualisiert die Zeile aus der laufenden Einheit (`startActiveUnit`
     → `updateNowLine`). Niemals geraten, immer der echte Sprechtext.
   - **Studio-Tonspur (MP3):** blockgenau über die Chunk-Karte des
     Generators, satzgenau über die Zeitproportion innerhalb des
     Blocks (`t0`/`t1` je Block aus `ff-voice-track-config`). Dieselbe
     Satzzerlegung wie der Sprechplan (`speechNormalize` +
     `splitForSpeech`), je Block gecacht — der Ticker bleibt billig.
2. **Abschnittszähler** (`ff-voice-pos`): „Abschnitt n von m“ — der
   Leser sieht jederzeit, wo er im Artikel steht.
3. **Pause- und Stopp-Verhalten:** Beim Pausieren bleibt der zuletzt
   gehörte Satz stehen (man findet die Stelle im Text wieder); beim
   Beenden werden Zeile und Zähler geleert.
4. **Kein CLS:** Die Zeile ist im Layout dauerhaft reserviert und wird
   im Ruhezustand nur per `visibility: hidden` ausgeblendet — die
   Toolbar verändert beim Start keine einzige Höhe.
5. **Barrierefreiheit (WCAG 2.2 / BITV):** Die Zeile selbst ist für
   Screenreader `aria-hidden`; der Inhalt steht im
   `aria-valuetext` des Progress-Meters (Rolle, Prozent, Modus,
   Abschnitt, „Gerade vorgelesen: …“). Puls-Punkt nur im
   `playing`-Zustand und unter `prefers-reduced-motion` aus.
6. **Zweisprachig ohne Umschalter:** Die Beschriftung folgt der
   Artikelsprache („Gerade vorgelesen“ / „Now reading“, „Abschnitt n
   von m“ / „Section n of m“). DE-/EN-Wortlauf-Regie unverändert.

### Robuste Details (High-End-Anspruch)

- `updateNowLine()` schreibt DOM nur bei Textwechsel — im rAF-Ticker
  der Tonspur entsteht keine Schreiblast.
- Die Tonspur-Schätzung ist gegen leere Chunks, fehlende `duration`
  und Endlos-Bereiche abgesichert (`trackBlockTimeRange` fällt auf die
  Karten-Gesamtdauer zurück; Verhältnis wird auf [0,1] geklemmt).
- Fallback bei fehlenden DOM-Knoten: alle neuen Elemente werden
  optional behandelt (`if (nowEl) …`) — ein altes, gecachtes Layout
  kann die Engine nie zu Fall bringen.
- Der Block-Index wird nie geraten: `blockIndexOf`/`trackBlock` liefern
  die Position, Zähler und Zeile bleiben konsistent zur Live-Markierung
  (`ff-voice-active`) im Artikel.

## 3 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `layouts/_partials/ff_voice_toolbar.html` | Neue Zeile `ff-voice-live` mit `ff-voice-live-label`, `ff-voice-now`, `ff-voice-pos` |
| `static/premium/ff-voice.js` | Version `2026.09.09`; I18N DE/EN; Now-/Pos-Zustand, `updateNowLine`, Tonspur-Satzschätzung, aria-valuetext, Anbindung an Start/Satzwechsel/Pause/Stopp/Sprung |
| `assets/css/extended/ff-voice.css` | Styling der Live-Zeile (reservierte Fläche, Puls, Abschnittszähler), Dark-Mode, mobil, `prefers-reduced-motion`, Floating |
| `scripts/ff_voice_qa_lib.mjs` | Test-Skelett um die neue Zeile ergänzt (1:1 zum Partial) |
| `scripts/ff_voice_functional_test.mjs` | 14 neue Gates für die Profi-Fortschrittsanzeige |
| `scripts/ff_voice_browser_test.mjs` | Browser-Fixture um die neue Zeile ergänzt |
| `scripts/ff_voice_toolbar_check.py` | Neue Pflicht-IDs und CSS-Klassen in der Infrastruktur-Wache |
| `scripts/ff_voice_tts_hardening_test.mjs` | Versionserwartung auf `2026.09.09` |
| `README.md` | Feature-Beschreibung + aktuelle Gate-Zahlen |

## 4 · Absicherung — alle Wachen grün

| Suite | Ergebnis |
|---|---|
| `node --check static/premium/ff-voice.js` | Syntax OK |
| `node scripts/ff_voice_functional_test.mjs` | **207/207** (u. a. „Gerade vorgelesen“-Zeile initial leer, startet mit Anmoderation, bleibt in Pause sichtbar, wird nach Stop geleert; Tonspur zeigt den Startabschnitt und den Zähler) |
| `node scripts/ff_voice_voice_test.js` | **96/96** |
| `node scripts/ff_voice_repair_test.mjs` | **56/56** |
| `node scripts/ff_voice_tts_hardening_test.mjs` | **57/57** |
| `python3 scripts/ff_voice_parity_check.py` | **332/332** |
| `python3 scripts/ff_voice_toolbar_check.py` | **108/108** |
| `python3 scripts/ff_voice_backends.py --selftest` | **67/67** |
| `python3 scripts/ff_voice_audio.py --selftest` | **92/92** |
| `node scripts/ff_voice_browser_test.mjs` (echtes Chromium) | **60/60** |

Manuell verifiziert (echte jsdom-DOM, reale Engine):
- DE-Seite: Zeile startet mit „Satztest.“, wechselt satzgenau auf
  „Erster Satz hier.“, Zähler „Abschnitt 1 von 6“, nach Stop geleert.
- EN-Seite: Beschriftung „Now reading“.
- Tonspur-Modus: nach Sprung auf 25 s steht der passende Satz des
  Blocks samt korrektem Abschnittszähler in der Zeile.

## 5 · Was Leserinnen und Leser jetzt merken

- Sie sehen beim Zuhören **den gerade gesprochenen Satz** in der
  Leiste und finden ihn durch die Live-Markierung im Artikel.
- Der Abschnittszähler sagt ihnen, wo sie im Beitrag stehen.
- Beim Pausieren bleibt die Stelle sichtbar; beim Beenden wird die
  Anzeige sauber geleert.
- Kein Layout-Sprung, keine neue Abhängigkeit, kein Tracking, kein
  Fremd-CDN — First-Party wie gehabt.
