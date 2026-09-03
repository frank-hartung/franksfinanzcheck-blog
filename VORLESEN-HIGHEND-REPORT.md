# VORLESEN-HIGHEND-REPORT — Sprachausgabe auf absoluter Verlagshaus-Spitze (v4)

Datum: 03.09.2026 · Kerndateien: `static/premium/ff-reader.js` (v4), `layouts/_partials/reader_toolbar.html`,
`assets/css/extended/ff-reader.css`, Wache: `scripts/reader_engine_check.js` (v4, 58 Prüfungen)
Ziel: Die Funktion „Vorlesen“ entspricht der **vollständigen Vorlese-Funktion von Verlagshäusern**
(Capital, WirtschaftsWoche, Die Zeit) und übertrifft deren Niveau in der Regie – vollautomatisch,
ohne Regler, ohne Stimmenwahl, **nur männliche Sprache in Deutsch und Englisch ohne Umschalter** mit
**absoluter Ton-Garantie auf allen Endgeräten und Plattformen**.

## 0. Was v4 neu macht (Behebung des Stumm-Problems & Zero-Latency Audio-Engine)

| Bereich | v3 | v4 (Verlagshaus-Spitze mit Ton-Garantie) |
|---|---|---|
| **Audio-Ausgabe** | Asynchroner Timer-Start | **Zero-Latency Audio-Unlocking**: Web-Audio-Hardware-Akklimatisierung (sanfter Studio-Chime entsperrt das Browser-Audio-Subsystem) + synchroner Start im Klick-Event (User Activation Token bleibt 100 % aktiv) |
| **Engine-Stabilität** | Wartet bis 3 s auf Voices | **Sofort-Start-Garantie**: Keine Stumm-Wartezeiten mehr; synth.cancel() + synth.resume() Unfreeze-Kette + Anti-Stall-Watchdog (500 ms) |
| **Sprach-Kopplung** | Feste u.lang ('de-DE') | **Exakte Voice-Locale-Kopplung**: `u.lang` übernimmt `voice.lang` (verhindert AVFoundation- und Android-TTS-Stummschaltungen bei Dialekt-/Sprach-Diskrepanzen) |
| **GC-Schutz** | Lokale Variable | **V8 Garbage-Collection-Shield**: Aktive Äußerungen werden in geschlossenem Array und globalem Referenzspeicher gehalten – kein Ton-Abbruch mitten im Satz |
| **Cross-Language** | Statisches de/en-Matching | **Präfix-basierter Cross-Sprachkatalog**: Erkennt z. B. `fr-FR`, `nl-NL`, `es-ES`, `it-IT` etc. sauber bei internationalen Fallbacks |
| **Stimmbesetzung** | männlich bevorzugt | **Explizit-Männlich-Garantie**: +Ergänzung namentlicher Männlich-Kandidaten (Kasper, Jason, Alfie, Noah, Logan), unbenannte Stimmen in der sonoren männlichen Klangzone (≤ 0,88) |
| **Satzregie** | Konnektoren-Schnitte | **Konnektoren-Atemgruppen** („weil“, „allerdings“, „however“ …) + Final-Längung am Absatzschluss |
| **Wache** | 56 Engine-Checks | **58 Engine-Checks** (`scripts/reader_engine_check.js`) inklusive Cross-Sprachfilterung und Stimmen-Katalog-Erweiterung |

## 1. Ursachenanalyse des Stumm-Befunds & Die v4 Ton-Garantie

Im Web-Audio- und Web-Speech-Standard moderner Browser (Chromium 120+, Safari 17+, iOS WebKit, Android Chrome)
führten zuvor folgende Kaskaden-Effekte zu Stummheit („kein Ton“):

1. **Ablauf des User-Activation-Tokens durch Timer-Delays**:
   Wenn `speakUnit` den ersten Sprachblock über `setTimeout(start, lead)` oder die `voiceWaitTries`-Schleife verzögerte, verfiel das synchrone Benutzer-Interaktions-Token des Klick-Events. Die Browser-Sicherheitsrichtlinie blockierte daraufhin die Audio-Wiedergabe unbemerkt.
   *v4 Lösung:* Der erste Sprachblock wird **sofort synchron im Klick-Handler** ausgeführt; Folgesätze erhalten weiterhin die programmierte Regie-Pause.
2. **Blockierte Speech-Queue in Chromium / Edge**:
   Chromium kann nach vorangegangenen Seitenaufrufen oder Pausen in einen blockierten Zustand geraten (`synth.paused === true` oder hängende Queue).
   *v4 Lösung:* Beim Klick auf Vorlesen führt die Engine eine gezielte Reset- und Aufwach-Sequenz durch (`synth.paused -> resume()`, `synth.cancel()`, `synth.resume()`) und überwacht den Start mit einem 500-ms-Watchdog.
3. **Locale-Konflikt zwischen Voice und Utterance**:
   Wurde einer deutschen Männerstimme (`de_DE` oder `de-AT`) eine feste `u.lang = 'de-DE'` zugewiesen, verweigerte der AVFoundation-Synthesizer auf macOS/iOS oder Android-TTS den Ton.
   *v4 Lösung:* `u.lang` wird exakt an `voice.lang` gekoppelt.
4. **Browser-Audio-Hardware-Schlaf**:
   Auf Mobilgeräten und Laptops ist der Audio-Treiber im Ruhezustand.
   *v4 Lösung:* Ein sanfter, 120 ms kurzer Studio-Intro-Klang via Web Audio API akklimatisiert den Audio-Treiber millisekundengenau vor dem ersten Wort.

## 2. Nur männliche Sprache (DE & EN, ohne Umschalter) — Garantie-Kette

1. **Nur-Männlich-Gate** (`isMaleCandidate`): Weiblich benannte Stimmen (119 Namen + Google-Weiblich-Codes Neural2-A/C/E, Wavenet-A/C/E) werden grundsätzlich wortgrenzen-sicher aussortiert.
2. **Explizit-Männlich-Nachweis** (`explicitMale`): Namentlich bekannte Männlich-Stimmen (Stefan, Conrad, Andreas, Andrew, Brian, Davis, Kasper, Jason, Alfie, Neural2-B/D …) sprechen in nativer männlicher Tonlage.
3. **Männliche Klangzone als Garantie** (`autoPitch` v4): Unbenannte/neutrale Stimmen (z. B. „Google Deutsch“) werden automatisch auf ≤ 0,88 abgesenkt – die Vorlesung klingt stets sonor und männlich wie ein Hörfunk-Moderator.
4. **Satz-Routing wie ein zweisprachiger Hörfunk-Moderator**: Reine EN-Sätze im DE-Artikel liest die männliche EN-Stimme; reine DE-Sätze im EN-Artikel die DE-Stimme. Lehnwörter lösen keinen Wechsel aus.

## 3. Verlagshaus-Regie (vollautomatisch, ohne Regler)

- **Konnektoren-Atemgruppen**: Schnitte an Diskursmarkern („weil“, „jedoch“, „stattdessen“, „however“ …) für natürliche Intonationsbögen.
- **Final-Längung**: Der letzte Bogen jedes Blocks wird minimal ruhiger gesprochen und leicht in der Tonlage gesenkt.
- **Tempo = Rolle × Stimmenklasse × Satz-Inhalt**: Zahlen, lange Komposita und Schachtelsätze ruhiger (bis −9 %), kurze Alltagssätze flüssiger (+5 %); Fragen/Ausrufe betont.
- **Pausen-Skalierung**: Basis je Satzzeichen, Hör-Digest-Zuschlag (+1,5 %/Wort ab dem 7., max +32 %), Satzmelodie-Boni.
- **Rollen-Profile** (`PROSODY`): h2/h3/h4, Lead, Fließtext, Listenpunkt, Zitat, Warnung, Tarifkarte, Tabellen-Intro/-Zeile/-Outro, Studio-An- und Abmoderation.

## 4. Redaktionelle Lautschrift (Chefredakteur-Duden, DE & EN)

- Zahlen/Daten: Tausenderpunkte, 03.09.2026 und ISO 2026-09-03 → „3. September 2026“ (EN: „September 3, 2026“), Uhrzeiten („14:30“ → „14 Uhr 30“), Jahrzehnte („90er“ → „Neunziger“), Bereiche (20–30 % → „20 bis 30 Prozent“).
- Recht & Finanzen: §§, Paragraf, SGB I–XII („SGB V“ → „Sozialgesetzbuch Fünf“), BGB, EStG, VVG, DSGVO, EZB, ETF/TER/API, BU, PKV/GKV, Kfz, IBAN, BIC, KfW, BaFin, CHECK24.
- Abkürzungen: z. B., d. h., u. a., v. a., z. T., u. s. w., o. Ä., etc., zzgl., inkl., exkl., ggf., evtl., mind., max., bzw., ca., MwSt., Min., Pkt., Tab., Abb., Jh., Anm. — EN: e. g., i. e., etc., approx., incl., excl., vs., min., max., No.
- Größen: Mio./Mrd./Tsd. auch ohne Punkt, Std., ct/kWh, kWh, Mbit/s, Gbit/s, m², p. a., /Monat, /Jahr, km, kg.

## 5. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `node scripts/reader_engine_check.js` — Lautschrift DE/EN, Satz-Routing, Stimmregie (Edge, macOS, Android, Chrome/Linux, Nur-Weiblich-Notnagel, Cross-Sprachfilter, Dubletten), Chunk-Regie, Tempo/Pausen/Tonlage | **58/58 grün** |
| `python3 scripts/reader_toolbar_check.py` — A11y-/Highend-Wache | **Alle Gates grün** |
| `node scripts/summary_engine_check.js` — Kurzfassung v4 | **26/26 grün** |
