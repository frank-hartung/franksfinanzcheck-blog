# VORLESEN-HIGHEND-REPORT — Sprachausgabe auf absoluter Verlagshaus-Spitze (v3)

Datum: 03.09.2026 · Kerndateien: `static/premium/ff-reader.js` (v3), `layouts/_partials/reader_toolbar.html`,
`assets/css/extended/ff-reader.css`, Wache: `scripts/reader_engine_check.js` (neu, 56 Prüfungen)
Ziel: Die Funktion „Vorlesen“ entspricht der **vollständigen Vorlese-Funktion von Verlagshäusern**
(Capital, WirtschaftsWoche, Die Zeit) und übertrifft deren Niveau in der Regie – vollautomatisch,
ohne Regler, ohne Stimmenwahl, **nur männliche Sprache in Deutsch und Englisch ohne Umschalter**.

## 0. Was v3 neu macht (aufbauend auf v2)

| Bereich | v2 | v3 (Verlagshaus-Spitze) |
|---|---|---|
| Stimmbesetzung | männlich bevorzugt | **Explizit-Männlich-Garantie**: unbenannte Stimmen werden in die männliche Klangzone (≤ 0,88) abgesenkt – die Vorlesung klingt immer männlich |
| Stimmen-Kataloge | Teilstring-Matching | **Wortgrenzen-sicher** („aria“ trifft nie „Bulgarian“), +40 aktuelle Natural-Stimmen (Windows 11, macOS, Google-Codes) |
| Satzregie | Komma-Schnitte | **Konnektoren-Atemgruppen** („weil“, „allerdings“, „however“ …): Schnitte dort, wo ein Sprecher atmet & intoniert |
| Satzschluss | – | **Final-Längung**: letzter Blockbogen minimal ruhiger (wie ein Sprecher am Absatzschluss) |
| Fortschritt | blockweise | **satzfortschrittts-genau** über Boundary-Ereignisse der Engine |
| Bedienung | Toolbar im Textfluss | **Schwebender Mini-Player** beim Scrollen (wie Verlagshaus-Audioplayer), Platzhalter-Slot hält das Layout stabil |
| Stabilität | Keep-Alive | + **Utterance-GC-Schutz** (Chrome-Abbruch-Bug), **Android-Pause-Härtung** (Abbruch- statt Einfrier-Strategie) |
| Lautschrift | Duden-Stufe 1 | + ISO-Daten, Uhrzeit ohne Suffix, Jahrzehnte (90er → Neunziger), SGB V–XII ausgeschrieben, v. a./z. T./o. Ä./zzgl./MwSt./etc., Mio./Mrd. auch ohne Punkt (Bugfix: „Mio. “ wurde nie erkannt), Währungs-Auffangnetz für jedes verbleibende €/%/$ |
| Wache | 18 Logik-Checks | **56 Engine-Checks** (`scripts/reader_engine_check.js`) gegen die echten Funktionskörper + Integrations-Rauchtest (Start→Pause→Resume→Ende) + Real-Content-Test |

## 1. Nur männliche Sprache (DE & EN, ohne Umschalter) — Garantie-Kette

1. **Nur-Männlich-Gate** (`isMaleCandidate`): weiblich benannte Stimmen (119 Namen + Google-Weiblich-Codes
   Neural2-A/C/E, Wavenet-A/C/E) werden grundsätzlich aussortiert – Matching **wortgrenzen-sicher**
   (`voiceHas`), damit „Ava“ nie „Available“ und „Anna“ nie zufällige Kontexte trifft.
2. **Explizit-Männlich-Nachweis** (`explicitMale`, neu): Nur bei eindeutig männlich benannter Stimme
   (Stefan, Conrad, Andreas, Andrew, Brian, Davis, „#male“, Neural2-B/D …) spricht die Regie in
   natürlicher männlicher Tonlage.
3. **Männliche Klangzone als Garantie** (`autoPitch` v3): geschlechtsneutral/unbenannte Stimmen
   (z. B. „Google Deutsch“) werden automatisch auf ≤ 0,88 abgesenkt (+Regie-Kappe „standard“ mit
   mehr Pausen für klare Verständlichkeit), der absolute Notnagel auf ≤ 0,86. Ergebnis: **Die
   Vorlesung bleibt auf jeder Plattform männlich** – Windows/Edge, macOS/Safari, Android/Chrome,
   Chrome/Linux, Firefox.
4. **Auswahl-Leiter** (`resolveMaleVoice`, je Sprache gecacht, `VOICE_EPOCH`-Invalidierung):
   1. beste männliche Studio-/Neural-Stimme der Artikelsprache (`male`),
   2. männliche Nachbarsprachen-Stimme (`cross`, z. B. macOS ohne deutsche Männerstimme) – niemals weiblich,
   3. einzige Stimme der Sprache als Notnagel (`fallback`, Tonlagen-Absenkung ≤ 0,86).
5. **Stimmen-Warte-Schutz** (bis 3 s) und **Dubletten-Schutz** (`dedupeVoices`): nie ein Start mit
   zufälliger (ggf. weiblicher) Standardstimme, nie Zufalls-Auswahl aus Browser-Dubletten.
6. **Satz-Routing wie ein zweisprachiger Hörfunk-Moderator**: Reine EN-Sätze im DE-Artikel liest die
   männliche EN-Stimme (und umgekehrt); Lehnwörter („Online-Banking“, „ETF“) lösen keinen Wechsel aus.
   Beide Sprecher-Pools werden beim Start vorgewärmt.

## 2. Verlagshaus-Regie (vollautomatisch, ohne Regler)

- **Konnektoren-Atemgruppen**: Lange Sätze werden an Diskursmarkern („weil“, „jedoch“, „stattdessen“,
  „however“, „therefore“ …) geschnitten – genau dort, wo ein professioneller Sprecher atmet und den
  Intonationsbogen neu ansetzt. Mindeststücklänge 40 Zeichen verhindert Stakkato; die Stücke bleiben
  bewusst eigene Äußerungen (kein Zurück-Packen).
- **Final-Längung**: Der letzte Bogen jedes Blocks wird minimal ruhiger gesprochen und leicht in der
  Tonlage gesenkt – der klassische Absatzschluss eines Studio-Sprechers.
- **Tempo = Rolle × Stimmenklasse × Satz-Inhalt**: Zahlen, lange Komposita und Schachtelsätze ruhiger
  (bis −9 %), kurze Alltagssätze flüssiger (+5 %); Fragen/Ausrufe betont.
- **Pausen-Skalierung**: Basis je Satzzeichen, Hör-Digest-Zuschlag (+1,5 %/Wort ab dem 7., max +32 %),
  Satzmelodie-Boni, Stimmenklassen-Skala (1,0–1,5 adaptiv), Tempo-Kopplung (nie unter 62 %).
- **Tonlage**: männliche Grundlage je Rolle (Überschrift sonor 0,88–0,92, Zitat 0,95, Warnung 0,86),
  Fragen steigen (+0,05), Ausrufe betonen, Mikro-Modulation nur bei einfachen Stimmen.
- **Rollen-Profile** (`PROSODY`): h2/h3/h4, Lead, Fließtext, Listenpunkt, Zitat, Warnung, Tarifkarte,
  Tabellen-Intro/-Zeile/-Outro, Studio-An- und Abmoderation.

## 3. Redaktionelle Lautschrift (Chefredakteur-Duden, DE & EN)

- Zahlen/Daten: Tausenderpunkte, 03.09.2026 **und ISO 2026-09-03** → „3. September 2026“ (EN:
  „September 3, 2026“), Uhrzeiten mit und ohne Uhr-Suffix („14:30“ → „14 Uhr 30“), Jahrzehnte
  („90er“ → „Neunziger“), Bereiche (20–30 % → „20 bis 30 Prozent“).
- Recht & Finanzen: §§, Paragraf, SGB I–XII („SGB V“ → „Sozialgesetzbuch Fünf“), BGB, EStG, VVG,
  DSGVO, EZB, ETF/TER/API, BU, PKV/GKV, Kfz, IBAN, BIC, KfW, BaFin, CHECK24.
- Abkürzungen: z. B., d. h., u. a., **v. a., z. T., u. s. w., o. Ä., etc., zzgl., inkl., exkl., ggf.,
  evtl., mind., max., bzw., ca., MwSt., Min., Pkt., Tab., Abb., Jh., Anm.** — EN: e. g., i. e., etc.,
  approx., incl., excl., vs., min., max., No.
- Größen: Mio./Mrd./Tsd. **auch ohne Punkt** (inkl. Bugfix: die alte `\b`-Regel nach dem Punkt
  erfasste „Mio. “ nie), Std., ct/kWh, kWh, Mbit/s, Gbit/s, m², p. a., /Monat, /Jahr, km, kg.
- Währungs-Auffangnetz: jedes verbleibende €/%/$ wird sprechbar („Euro“, „Prozent“, „Dollars“).
- URLs/E-Mails hörbar („die Webseite franksfinanzcheck Punkt de“), Prioritäts-Emojis als Ansagen,
  restliche Emojis ohne „Emoji-Stottern“ entfernt.

## 4. Bedienung wie ein Verlagshaus-Audioplayer

- **Schwebender Mini-Player**: Scrollt die Leser:in während des Vorlesens, schwebt die Steuerung
  (Vorlesen/Pause, Abschnitt vor/zurück, Beenden, Restzeit, Fortschritt) als kompakte Leiste am
  unteren Rand (IntersectionObserver; Platzhalter-Slot `.ff-reader-slot` verhindert Layout-Springen;
  `prefers-reduced-motion` respektiert; ohne Vorlesen keinerlei Effekt).
- **Satzfortschrittts-genaue Fortschrittsleiste** über `onboundary`-Ereignisse.
- Media-Session (Sperrbildschirm/Kopfhörer), Hörposition-Merken je Artikel, Klick-to-Listen,
  Abschnitts-Navigation, Restzeit-Schätzung, WCAG 2.2 AAA / BITV inkl. zeilengenauer Tabellen-Sync.

## 5. Robustheit

- **Utterance-GC-Schutz**: aktuelle Äußerung bleibt referenziert – behebt Chromes Abbruch-Bug bei
  früher Garbage Collection.
- **Android-Pause-Härtung**: `synth.pause()/resume()` friert Android-Chrome ein – v3 bricht beim
  Pausen ab und spricht beim Fortsetzen die laufende Einheit sauber neu (bruchsicher).
- Keep-Alive-Wache (9 s, ohne pause/resume-Ping auf Android), adaptive Herabstufung nach Fehlern,
  Stimmen-Warte-Schutz, Tab-Wechsel-Pause, Aufräumen bei pagehide/beforeunload.

## 6. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `node scripts/reader_engine_check.js` — Lautschrift DE/EN, Satz-Routing, Stimmregie (Edge, macOS, Android, Chrome/Linux, Nur-Weiblich-Notnagel, Cross, Dubletten), Chunk-Regie, Tempo/Pausen/Tonlage | **56/56 grün** |
| Integrations-Rauchtest (Start → Pause → Resume → Ende, aufgezeichnete Äußerungen) | 12/12 grün: nur Stefan (männlich), Tonlage ≤ 1,0, alle Chunks ≤ 240, Outro korrekt |
| Real-Content-Test: 2.000 echte Artikel-Sätze | max. Chunk 239 (< 240 hart), 0 Crashes, 0 Leerausgaben, 0 falsch EN-geroutet |
| `python3 scripts/reader_toolbar_check.py` (A11y-/Highend-Wache) | alle Gates grün |
| Stimmen-Kataloge | de 53 / en 66 männliche Marker, 39 bekannte Männlich-Stimmen, 119 Weiblich-Ausschlüsse, 31 Studio-Stimmen – dublettenfrei |

Weiterhin keine UI-Änderung am Grundprinzip: kein Tempo-Regler, keine Stimmenwahl, kein
Umschalter, keine Tastenkürzel – die Studio-Regie arbeitet vollautomatisch und nur männlich.
