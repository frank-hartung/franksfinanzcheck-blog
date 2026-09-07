# VORLESEN: Nur-Deutsch-Vertrag + wortgenaue Leseanzeige (Wort-Takt)

**Stand: 10.09.2026 · FF Voice Studio, Generation 4**
Auftrag: Die Vorlese-Funktion spricht **ausschließlich Deutsch** — und zwar
wie ein **männlicher, deutscher Nachrichtensprecher** (nüchterner
Hörfunkton, nicht Vorlese-Knistern). Die Leseanzeige wird **wortgenau**:
Was gerade gesprochen wird, leuchtet Wort für Wort im Artikeltext,
satzweise in der Leiste und zählt mit („Wort 214 von 1.286“) — auf
**hochwertigem, barrierefreiem Niveau**.

---

## 1 · Der Befund (warum das nötig war)

1. **Zweisprachigkeit als Programmierentscheidung.** Das Vorgängermodell
   routete englische Sätze (und sogar einzelne EN-Wortläufe mitten im
   Satz) auf eine englische Männerstimme (`en-US-AndrewMultilingualNeural`
   / Piper `en_US-ryan-high` / Groq-Notnagel). Für die Leserschaft war
   das nicht wählbar und nicht erwartet: ein deutscher Finanzblog-
   Sprecher, der plötzlich englisch klingt. **Entfall: ersatzlos** —
   inklusive der I18N.en-Oberflächentexte, der Spracherkennungs-
   Heuristiken und der Wortlauf-Regie.

2. **Die Leseanzeige hielt nur Satz-Anfänge ein.** Bisher wurde pro
   Sprecheinheit der ganze Satz markiert; welches Wort innerhalb des
   Satzes gerade klingt, wusste niemand. Dabei liegen diese Grenzen
   vor: bei der Browser-Engine im `onboundary`-Event, bei der
   Studio-Tonspur in den Wortgrenzen, die `edge-tts` bei der Synthese
   mitliefert. Sie wurden schlicht verworfen.

## 2 · Die Verträge (hart, gategeprüft)

| Vertrag | Sicherung |
|---|---|
| **Nur-Deutsch**: Reader und Generator kennen genau eine Sprechsprache `de`; englische Texte liest der deutsche Nachrichtensprecher nach deutschem Regelwerk | `ff_voice_parity_check.py` §5 verbietet `'en-US'`, `languageRuns`, `MONTHS_EN` im Reader und `def language_runs` im Generator; Toolbar-Wache prüft beide Richtungen zusätzlich |
| **Nachrichtenton**: Browser-Katalog-Reihenfolge `Conrad > Killian > Florian > Thorsten …`, Online/Natural vor Standard; Studio-Standardprofil `news` = `de-DE-ConradNeural`, Style `serious` | `NEWS_PRIORITY`-Scoring im Reader; `ttb.VOICE_PROFILES` + Deploy-Eingabe `audio_profile` (Standard `news`) |
| **Wort-Takt**: Es leuchtet NUR das Wort, das wirklich gesprochen wird. Quellen: `chunk.w`-Wortuhr (ms-genau) > `onboundary` > redliche Zeitschätzung; die Quelle steht offen an `data-ff-wordsync` | Generator `track_plausible()` verwirft eine Spur mit fehlerhafter Wortuhr komplett; Reader-`trackPlausible()` prüft die Indexgrenzen nach; Paritäts-Gate vergleicht Python-Aligner und JS-Aligner Wort für Wort (14 Fixpaare) |
| **DOM-Ruhe**: Wort-Spans existieren nur während des Vorlesens; danach ist der Artikeltext zurückgebaut (`unwrap`), Blöcke ohne sichere Wortzuordnung (Tabellen, Barren-Intro) werden nie wortweise geblendet | `clearWordSync(true)` in `clearHighlight`; Übereinstimmungs-Guard in `wrapBlockWords` (Rohtext-DOM-Vergleich, eine Ausnahme: der Generator-Punkt an Überschriften) |

## 3 · Tonspur-Seite (Python)

* `ff_voice_backends.py` — `normalize_speech` nur noch deutsch (das
  Sprachargument wird ignoriert); `synth_edge` liefert jetzt die
  **Wortgrenzen** (`WordBoundary`-Events, 100-ns-Offsets) zusammen mit
  dem Audio zurück; Trim-Korrektur `trim_edges_info` meldet die
  abgeschnittene Kopfzeit, damit die Wortuhr nicht verrutscht;
  Groq-Backend entfernt; Profile `news|natural|narrator`
  (`DEFAULT_PROFILE = "news"`, Rezept `ff-voice-2026.09.10`).
* `ff_voice_audio.py` — neuer **Wortuhr-Aligner**
  (`token_core`/`norm_tokens`/`align_norm_to_raw`): überführt die
  gesprochene, normalisierte Wortfolge auf die rohen Wörter des
  Blocks (Symbol-Erweiterung „€“→Euro, „–“→bis; Einheiten
  „kWh“→Kilowattstunden; Ziffern-Core-Containment für Daten wie
  02.01.2006; Resync-Fenster nach sechs Treffern). Je Chunk
  entsteht `w = [[rohesWort, ms], …]`; die Konfiguration erhält
  `voice: {de, style, lang:"de"}` und `profile`.
  `track_plausible()` lehnt die ganze Spur ab, wenn nur ein einziger
  Wort-Eintrag außerhalb des Blocks zeigt, unsortiert ist oder außerhalb
  ±1500 ms um sein Chunk liegt — eine halbe Wortuhr ist schlimmer als
  keine. Der Fingerprint ignoriert `voice_en` (Altbestand wird
  durch die Rezept-Version ohnehin invalidiert).

## 4 · Reader-Seite (JavaScript)

* **Sprachschalter-Kern entfernt**: I18N nur deutsch;
  `detectArticleLanguage`/`sniffSentenceLang`/`sniffLangOf` bleiben als
  Signaturen (immer `de`), damit Alt-Tests und der Generator-Spiegel
  nicht stolpern; `speechNormalize(text)` ignoriert ein zweites
  Argument.
* **Stimmen-Regie**: `isGermanVoice`-Pflicht (nicht-deutsche Stimmen
  scoring-seitig ausgeschlossen), `NEWS_PRIORITY`-Bonus,
  `LOCALE_CHAIN` nur `de`; `resolveMaleVoice` beantwortet JEDES Ziel
  mit dem deutschen Ranking — ein Katalog ohne deutsche Stimme liefert
  konsequent `voice: null` (dann spricht das Gerät auf `de-DE`, nie
  Englisch).
* **Sprechen**: eine Äußerung je Sprecheinheit (kein Run-Loop mehr);
  die Anti-Stall-Wache (2 Stufen) bleibt. `onboundary` speist jetzt
  die Wortanzeige statt nur den Zeichenfortschritt.
* **Modul 9a „Wort-Takt“**: `blockPlan` (je Block: Rohtoken, Aligner,
  Satzeinheiten mit erstem rohen Wort), `wrapBlockWords` (Spannen nur
  bei exakter DOM-Übereinstimmung), `markWord` (genau ein
  `ff-voice-w--now`), `applyTrackWord` (Binärsuche in der Wortuhr),
  `estimateSpeechWord` (nur wenn die Engine keine Grenzen liefert),
  `renderNowLine` (Satz wortweise in der Leiste, `ff-voice-live-w--now`),
  Wortzähler + Übernahme in `aria-valuetext` des
  Progressbar-Meters. Shift+←/→ springt **Satz für Satz**
  (`jumpSentence`; auf dem Tonspurpfad nur mit Wortuhr, sonst
  redlicher Abschnittssprung).
* **Diagnose**: `window.__ffVoice` erhält `alignNormToRaw`,
  `normTokens`, `blockPlan`, `jumpSentence`, `wordSyncSource`,
  `currentWord`; `diagnostics().wordSync` nennt Quelle, Block, rohen
  Index, Satz und Kartengröße.

## 5 · Styling & Partial

* `.ff-voice-w` ist Layout-neutral (`display:inline`, normale
  Textknoten bleiben selektierbar); das helle Wort trägt
  Gelb-Soft-Fläche + Unterstreicheinlauf mit Darkmode- und
  Forced-Colors-Variante (Highlight/HighlightText) und ohne
  Transition bei `prefers-reduced-motion`; der Scroll-Nudge bleibt
  auf 200 ms gedrosselt und respektiert reduzierte Bewegung.
* Neues ID `ff-voice-word-count` (Klasse
  `.ff-voice-meter__words`, `:empty` → ausgeblendet, damit kein CLS);
  die Toolbar-Wache führt ID und Klassen in ihrer Pflichtliste.

## 6 · Deploy

* `audio_backend`-Option `groq` entfernt (GROQ_API_KEY wird für die
  Tonspur nicht mehr gelesen; die Content-Workflows bleiben unberührt),
  `audio_profile`-Standard `news` (Auswahl `news|natural|narrator`),
  Shell-Fallback `'natural'` → `'news'`. Der Grundsatz bleibt: **kein
  Deploy-Abbruch wegen der Tonspur**; `--heal` und Nachmessen
  unverändert.

## 7 · Gates (alle grün, 10.09.2026)

```
node --check static/premium/ff-voice.js                     OK
functional_test.mjs      218/218   (neu: Gruppe 9b Wort-Takt)
voice_test.js             69/69    (neu geschrieben: Nur-Deutsch-Fallen)
repair_test.mjs           56/56    (Newsroom-Meldung angepasst)
tts_hardening_test.mjs    57/57    (Versionspinne 2026.09.10)
browser_test.mjs           übersprungen ohne Chromium — Fixture jetzt
                           mit chunk.w-Wortuhr + Leseanzeige-Assertionen
ff_voice_audio.py --selftest      105/105  (Aligner, Nur-Deutsch, Gate)
ff_voice_backends.py --selftest    71/71   (Profile, de-only, Grenzen)
ff_voice_parity_check.py           337/337 (neu: Aligner-Parität, §5-Verbote)
ff_voice_toolbar_check.py          118/118 (neu: Wortzähler + Wort-Takt-Gates)
```

## 8 · Bewusste Grenzen

* **Firefox** liefert keine brauchbaren `onboundary`-Ereignisse: Dort
  läuft die Wortanzeige aus der Zeitschätzung; sie bleibt sichtbar,
  aber das Attribut an der Leiste unterscheidet das.
* **Tabellen-/Overblicksblöcke** werden wegen ihrer gesprochenen
  Präfixe („Zeile 3 von 8: …“) nie wortweise geblendet — die Satzebene
  bleibt dort die Anzeige der Wahl.
* Die Wortuhr überlebt Artikelumschreibungen nicht stillschweigend:
  Der Fingerprint ändert sich mit dem Text, die Spur wird neu
  erzeugt; eine aus Versehen mitgeschleppte Wortuhr würde das
  Plausibilitäts-Gate im Reader sofort auf die Gerätestimme fallen
  lassen.
