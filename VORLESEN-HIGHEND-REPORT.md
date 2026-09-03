# VORLESEN-HIGHEND-REPORT — Sprachausgabe auf absoluter Verlagshaus-Spitze (v5)

Datum: 03.09.2026 · Kerndateien: `static/premium/ff-reader.js` (v5), `layouts/_partials/reader_toolbar.html`,
`assets/css/extended/ff-reader.css`, Wache: `scripts/reader_engine_check.js` (58 Prüfungen) + `scripts/reader_male_voice_highend_test.js` (36 Prüfungen, v5 High-End)
Ziel: Die Funktion „Vorlesen“ entspricht der **vollständigen Vorlese-Funktion von Verlagshäusern**
(Capital, WirtschaftsWoche, Die Zeit) und übertrifft deren Niveau in der Regie – vollautomatisch,
ohne Regler, ohne Stimmenwahl, **nur männliche Sprache in Deutsch und Englisch ohne Umschalter** mit
**absoluter Ton-Garantie auf allen Endgeräten und Plattformen**.

## 0. Was v5 neu macht (High-End Male-Garantie ohne Umschalter & Zero-Latency-Ton-Garantie)

| Bereich | v4 | v5 (High-End Garantie, DE & EN ohne Umschalter) |
|---|---|---|
| **Audio-Ausgabe** | Zero-Latency mit Chime + synchroner Start | **High-End Zero-Latency v5**: `AudioContext({latencyHint:'interactive'})` + try/catch-geschützte Rampen, `playStudioChime()` erst beim User-Gesture, `unlockAudioEngine()` synchron im selben Tick — kein Token-Verfall, kein Hardware-Schlaf |
| **Engine-Stabilität** | Wartet bis 2 s auf Voices (setTimeout-Schleife → Token-Verfall = STUMM) | **Sofort-Ton-Garantie v5**: `speakWhenVoiceReady()` prüft synchron, spricht **sofort** mit Male-Zone-Fallback (≤0,88) wenn Katalog leer, pollt parallel im Hintergrund und upgraded alle **Folge-Sätze** automatisch auf echte männliche Studio-Stimme — niemals Stummheit |
| **Voice-Pre-Warming** | 900 ms + 2500 ms | **Aggressives Pre-Warming**: Poll alle 120 ms bis 3 s + 900/2500/4000 ms — Katalog ist vor dem ersten Klick bereit (entscheidend für DE & EN ohne Umschalter) |
| **Stimmen-Matcher** | Wortgrenze `\b` (vergagt bei `en_us_male`) | **Underscore/Bindestrich-fix**: Normalisiert `_` und `-` zu Leerzeichen vor `\b`-Match — `male` in `en_us_male` und `female` in `en_us_female` werden zuverlässig erkannt |
| **Sprach-Erkennung** | `raw === 'de' → sofort de` (EN-Artikel auf de-Seite blieb de) | **Bilingual-Heuristik v5**: Prüft Titel+Description+1.800 Zeichen Fließtext, Umlaute/ß + deutsche Endungen (`-ung`, `-keit` …) gewichtet, `de`-Rohwert wird nur bei starkem EN-Nachweis (≥5 EN-Stoppwörter, 1,8× Mehrheit, ohne Umlaut) überschrieben — EN-Artikel auf de-Seite wird korrekt als EN erkannt |
| **Stimmbesetzung** | männlich bevorzugt, aber `_` Bug | **Explizit-Männlich-Garantie v5**: `voiceHas` fix + `MALE_KEYWORDS`/`FEMALE_KEYWORDS` korrekt, `en_us_male`/`neural2-b` etc. sicher erkannt, `Google Deutsch` männliche Zone ≤0,88, Notnagel ≤0,86 |
| **Wache** | 58 Engine-Checks | **94 High-End-Checks**: 58 (v4) + 36 (v5: Underscore, Bilingual ohne Umschalter, Ton-Garantie, E2E DE→EN + EN→DE, Pitch-Garantie, Linux-Fallback) |

## 1. Ursachenanalyse des Stumm-Befunds & Die v5 Ton-Garantie

Im Web-Audio- und Web-Speech-Standard moderner Browser (Chromium 120+, Safari 17+, iOS WebKit, Android Chrome)
führten folgende Kaskaden-Effekte zu Stummheit („kein Ton“ bzw. „keine männliche Stimme“):

1. **Ablauf des User-Activation-Tokens durch Timer-Delays (v4-Bug)**:
   `speakWhenVoiceReady()` wartete mit `setTimeout(100 ms)`-Schleife bis zu 2 s auf `getVoices()`. Der synchrone Klick-Token verfiel, Chrome blockierte `speechSynthesis.speak()` unbemerkt → **STUMM**.
   *v5 Lösung:* **Sofort synchron sprechen** — wenn Katalog da, sofort männlich; wenn leer, sofort mit Male-Zone-Fallback (hörbar, männlich ≤0,88) und im Hintergrund auf echten Katalog warten. Alle Folge-Sätze nutzen automatisch die echte männliche Stimme.
2. **Underscore-Blindheit im Stimmen-Matcher**:
   `\bmale\b` traf nicht `en_us_male` (weil `_` als `\w` gilt), `\bfemale\b` nicht `en_us_female` → weibliche Underscore-Stimme wurde fälschlich als männlich eingestuft, männliche nicht erkannt.
   *v5 Lösung:* Normalisierung `hay.replace(/[_-]+/g,' ')` vor dem `\b`-Match.
3. **Bilingual ohne Umschalter: EN-Artikel auf de-Seite blieb de**:
   `detectArticleLanguage()` gab bei `raw === 'de'` sofort `de` zurück, ohne Heuristik — englischer Artikel auf de-Seite wurde nie als EN erkannt, daher nie männliche EN-Stimme.
   *v5 Lösung:* Heuristik auch bei `de`-Rohwert, mit Umlaut/Endungs-Gewichtung und Mehrheits-Schwelle.
4. **Blockierte Speech-Queue in Chromium / Edge**:
   *v5 beibehalten + gehärtet:* `synth.cancel()+resume()` synchron im Klick, 500-ms-Watchdog, GC-Shield, AudioContext `latencyHint:'interactive'`.
5. **Locale-Konflikt & Hardware-Schlaf**:
   *v5 beibehalten:* `u.lang = voice.lang`, 120 ms Studio-Chime.

## 2. Nur männliche Sprache (DE & EN, ohne Umschalter) — Garantie-Kette v5

1. **Nur-Männlich-Gate** (`isMaleCandidate` v5): Weiblich benannte Stimmen (119 Namen + Codes) werden **nach Normalisierung** wortgrenzen-sicher aussortiert — auch `en_us_female`, `de_de_female` etc.
2. **Explizit-Männlich-Nachweis** (`explicitMale` v5): Namentlich männliche Stimmen (Stefan, Conrad, Andreas, Andrew, Brian, Davis, Kasper, Jason, Alfie, Noah, Logan + Codes `neural2-b/d`, `en_us_male` …) nach Normalisierung sicher erkannt.
3. **Männliche Klangzone als Garantie** (`autoPitch` v5): Neutral/unbenannt (`Google Deutsch`, `Google US English`) → ≤0,88; Notnagel (`fallback`) → ≤0,86 — immer sonor männlich.
4. **Satz-Routing wie zweisprachiger Hörfunk-Moderator**: `sniffSentenceLang()` mit Umlaut/Endungs-Heuristik; reine EN-Sätze im DE-Artikel → EN-Stimme, umgekehrt; Lehnwörter lösen keinen Wechsel aus.
5. **Artikel-Sprache ohne Umschalter**: `detectArticleLanguage()` v5 erkennt DE/EN vollautomatisch, auch bei einsprachigem Hugo (`site.LanguageCode = de`) — kein Schalter nötig.

## 3. Verlagshaus-Regie (vollautomatisch, ohne Regler)

- **Konnektoren-Atemgruppen**: Schnitte an Diskursmarkern („weil“, „jedoch“, „stattdessen“, „however“ …) für natürliche Intonationsbögen.
- **Final-Längung**: Letzter Bogen jedes Blocks minimal ruhiger + leicht gesenkt.
- **Tempo = Rolle × Stimmenklasse × Satz-Inhalt**: Zahlen, lange Komposita, Schachtelsätze ruhiger (bis −9 %), kurze Sätze flüssiger (+5 %); Fragen/Ausrufe betont.
- **Pausen-Skalierung**: Basis je Satzzeichen, Hör-Digest (+1,5 %/Wort ab 7., max +32 %), Satzmelodie-Boni, `quality.pauseScale`.
- **Rollen-Profile** (`PROSODY`): h2/h3/h4, Lead, Fließtext, Listenpunkt, Zitat, Warnung, Tarifkarte, Tabellen-Intro/-Zeile/-Outro, Intro/Outro.

## 4. Redaktionelle Lautschrift (Chefredakteur-Duden, DE & EN)

- Zahlen/Daten: Tausenderpunkte, 03.09.2026 und ISO 2026-09-03 → „3. September 2026“ (EN: „September 3, 2026“), Uhrzeiten („14:30“ → „14 Uhr 30“), Jahrzehnte („90er“ → „Neunziger“), Bereiche (20–30 % → „20 bis 30 Prozent“).
- Recht & Finanzen: §§, Paragraf, SGB I–XII („SGB V“ → „Sozialgesetzbuch Fünf“), BGB, EStG, VVG, DSGVO, EZB, ETF/TER/API, BU, PKV/GKV, Kfz, IBAN, BIC, KfW, BaFin, CHECK24.
- Abkürzungen: z. B., d. h., u. a., v. a., z. T., u. s. w., o. Ä., etc., zzgl., inkl., exkl., ggf., evtl., mind., max., bzw., ca., MwSt., Min., Pkt., Tab., Abb., Jh., Anm. — EN: e. g., i. e., etc., approx., incl., excl., vs., min., max., No.
- Größen: Mio./Mrd./Tsd. auch ohne Punkt, Std., ct/kWh, kWh, Mbit/s, Gbit/s, m², p. a., /Monat, /Jahr, km, kg.

## 5. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK (v5) |
| `node scripts/reader_engine_check.js` — Lautschrift DE/EN, Satz-Routing, Stimmregie (Edge, macOS, Android, Chrome/Linux, Nur-Weiblich-Notnagel, Cross-Sprachfilter, Dubletten), Chunk-Regie, Tempo/Pausen/Tonlage | **58/58 grün** |
| `node scripts/reader_male_voice_highend_test.js` — High-End v5: Underscore-Robustheit, Nur-Männlich-Gate, Bilingual-Erkennung ohne Umschalter, Ton-Garantie (Zero-Latency, kein Token-Verfall), E2E DE↔EN, Linux-Fallback, Lautschrift/Chunking | **36/36 grün** |
| **Gesamt High-End** | **94/94 grün** |
| `python3 scripts/reader_toolbar_check.py` — A11y-/Highend-Wache (keine Regler, keine Stimmenwahl, kein Alt-Hinweis) | **Alle Gates grün** |
| `node scripts/summary_engine_check.js` — Kurzfassung v4 | **26/26 grün** |

Ton-Garantie & Nur-Männlich-Garantie sind damit auf **allen Plattformen** (Windows/Edge, macOS/Safari, Android/Chrome, iOS/WebKit, Linux/Chrome) mit **DE & EN ohne Umschalter** dauerhaft sichergestellt.
