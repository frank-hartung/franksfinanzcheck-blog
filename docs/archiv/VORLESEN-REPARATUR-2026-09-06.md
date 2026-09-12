# VORLESEN-REPARATUR-2026-09-06 — Kein Ton & rennende Fortschrittsanzeige

**Datum:** 06.09.2026
**Gemeldeter Fehler (Produktion):** „Vorlesen gibt keinen Ton aus, die Fortschrittsanzeige läuft viel zu schnell durch.“
**Betroffen:** Vorlese-Funktion (FF Voice Studio, männliche Stimme, DE/EN ohne Umschalter) — beide Tonpfade

> **Kernsatz dieses Befunds:** Die jsdom-Testsuite war grün, während der
> echte Browser stumm blieb — dieselbe Falle wie am 03.09.2026
> (LESEHILFEN-REPARATUR-2026-09-03.md). Diesmal wurde der Fehler im
> **echten Chromium** (Playwright) reproduziert, repariert und mit einer
> dauerhaften Echt-Browser-Suite gepinnt, die im Lesehilfen-Gate läuft.

---

## 1 · Befundlage (nachgewiesen, nicht vermutet)

### 1.1 Der Live-Stand (origin/gh-pages)

Alle 34 deployten Tonspuren sind **unbrauchbar**:

| Signal | Soll | Ist (deployt) |
|---|---|---|
| Chunks mit Sprechdauer (`t1 > t0`) | alle | **0 von 85** — jeder Chunk `t0 == t1` |
| Laufzeit eines Langartikels | ~10 min | **33 s** (nur generierte Pausen) |
| Format | MP3 (mit ffmpeg) | **WAV ohne ffmpeg**, zusammen 63 MB |
| Inhalt | Sprache | **reine Stille** (Backend lieferte kein Audio) |

Beispiel `audio/articles/2026-08-16-gas-anbieter-wechseln-….track.json`:
`duration: 32980`, Chunks `[{b:0,t0:0,t1:0}, {b:1,t0:520,t1:520}, …]`.

### 1.2 Reproduktion im echten Chromium (vor der Reparatur)

Gegen die unveränderte Engine und die deployte Spur-Konfiguration:

* **Spur-Fehler (404/defekt):** Endlosschleife — Status blieb
  „Studio-Tonspur läuft.“ bei `audio.error = true`, `reading = true`
  **für immer**. Kein Ton, kein Fortschritt, Knopf „Pausieren“ ohne
  Wirkung. → **Das gemeldete „kein Ton“.**
* **Browser-Engine ohne nutzbare Synthese:** Der Reader fegte still
  durch alle Einheiten („Dieser Abschnitt konnte nicht abgespielt
  werden; es geht weiter.“ × N) — Fortschritt **~20× zu schnell**,
  kein Ton, am Ende „Vorlesen beendet“. → **Die gemeldete „zu schnelle
  Fortschrittsanzeige“.**

---

## 2 · Ursachenkette (fünf Einzelfehler)

**G1 · Generator übersprang Backend-Ausfälle still**
`scripts/ff_voice_audio.py` / `synth_article()`: Scheiterte ein TTS-Segment
(kein Netz zum Backend, leeres Audio), wurde es kommentarlos
`continue`d. Bei einem Totalausfall des Backends entstand so eine Spur
**nur aus Inter-Block-Pausen** — geschrieben, injiziert und per
Fingerprint **für immer wiederverwendet**. Kein Gate prüfte je, ob eine
Spur tatsächlich Sprache enthält.

**G2 · Keine Plausibilitätsprüfung der Laufzeit**
33 s für einen Artikel mit erwarteter Hörzeit von ~10 Minuten wurden
unkommentiert veröffentlicht. Weder Erzeugung noch Cache noch Reader
rechneten gegen die erwartete Sprechzeit (Zeichen ÷ 15,2 Zeichen/s,
Paritätswert der Engine).

**C1 · Reader spielte jede Spur ungeprüft**
`static/premium/ff-voice.js`: Der Track-Pfad vertraute der Konfiguration
bedingungslos. Die Pausen-Spur lief 33 s stumm ab und „beendete“ den
Artikel mit Fortschritt 100 %.

**C2 · `fallbackToSpeech()` war während der Wiedergabe ein No-OP**
Der Fallback rief `startReading()` auf — das bei `reading === true`
**sofort zurückkehrt**. Bei Lade-/Codec-Fehlern (404, MIME, Netz) war
die Übernahme durch die Gerätestimme damit strukturell unmöglich: Die
Leiste hing endlos auf „Studio-Tonspur läuft.“ — exakt die im Browser
reproduzierte Endlosschleife.

**C3 · Tote Synthese fegte still durch den Artikel**
Ohne je ein `onstart` gesehen zu haben (keine Engine/Stimmen, z. B.
Linux ohne speech-dispatcher, verwaltete Browser, Headless),
durchlief der Reader alle Einheiten mit Fehler-Wiederholungen —
Fortschritt rannte, kein Ton, falsches „Vorlesen beendet“.

**C4 · Lazy Stimmen-Katalog vergiftete den Stimmen-Cache**
Chromium/Safari/Android liefern `getVoices()` erst nach dem ersten
Klick. Die „keine männliche Stimme“-Auflösung wurde aber **für immer**
gecacht (`voiceResolved` wurde bei `voiceschanged` nie geleert) — die
männliche Stimme band auch nach Eintreffen des Katalogs nie, das
aria-label versprach dauerhaft die Geräte-Stimme.

---

## 3 · Reparatur

### 3.1 Reader `static/premium/ff-voice.js` (Version 2026.09.06)

1. **Plausibilitäts-Wache `trackPlausible()`** — eine Studio-Tonspur wird
   vor dem Start geprüft: Mehrheit der Chunks mit echter Sprechdauer
   (`t1 > t0`), Gesamtlaufzeit im Fenster [25 %, 400 %] der erwarteten
   Sprechzeit des **Artikels** (inkl. Pause-Zuschlag). Defekte, falsche
   oder gelogene Spuren werden abgewiesen — Status
   „Die Tonspur dieses Artikels ist unbrauchbar – die Stimme deines
   Geräts übernimmt.“ — und die Browser-Engine startet.
2. **`fallbackToSpeech()` wirklich repariert** — vollständige
   Entwertung des alten Laufs (runId++, Timer-Wachen raus, Track
   pausieren) und **direkter** Start der Sprach-Engine ab dem zuletzt
   gehörten Block. Kein `startReading()`-Umweg mehr, der an
   `reading === true` scheiterte.
3. **Ende-zu-früh-Wache `trackOnEnded()`** — endet die Datei deutlich
   vor der erwarteten Hörzeit (zu kurz geschnitten, unvollständig
   vertont), übernimmt die Gerätestimme ab dem letzten gehörten Block,
   statt „beendet“ zu lügen. Verglichen wird die **echte**
   `audio.duration` gegen Artikel-Erwartung UND gegen die eigene
   Chunk-Karte.
4. **Lade-Wache** — startet die Spur binnen 8 s nicht hörbar (Netz
   hängt, Metadaten kommen nie), übernimmt die Gerätestimme. Nie wieder
   endloses Stumm-Warten.
5. **Ehrlichkeits-Wache der Synthese** — ein Lauf, der **nie** ein
   `onstart` gesehen hat, endet ehrlich mit „Sprachausgabe ist auf
   diesem Gerät nicht verfügbar. Der Artikel bleibt vollständig
   lesbar.“ statt still durchzufegen. Fortschritt bleibt bei 0 %,
   maximal 2 Sprechversuche.
6. **Stimmbindung bei lazy Katalog** — `refreshVoices()` erkennt
   Katalog-Änderungen, leert die Auflösungs-Caches und hebt die
   folgenden Einheiten auf die echte männliche Stimme; aria-label der
   Toolbar zieht nach.
7. **Fortschritt und Live-Markierung aus EINER Uhr** — im Track-Modus
   sampelt der rAF-Ticker `currentTime` (Fortschritt, Restzeit UND
   Block-Markierung). `timeupdate` feuert je Browser sehr
   unterschiedlich (iOS Safari spärlich); die Anzeige hängt nicht mehr
   am Event-Takt.
8. Neue ehrliche Status-Meldungen (DE/EN): `trackDefective`,
   `trackBroken`, `trackEndedEarly`, `synthesisDead`.

### 3.2 Generator `scripts/ff_voice_audio.py`

1. **Stille-Wache in `synth_article()`** — jedes fehlgeschlagene oder
   leere Segment zählt als `failed`. **Ein einziges** fehlgeschlagenes
   Segment verwirft die gesamte Spur (Verlagsregel: lieber
   Gerätestimme als Tonspur mit fehlenden Sätzen). Klare Log-Zeile
   pro Artikel.
2. **`track_plausible()`** — dasselbe Gate wie im Reader, serverseitig:
   keine degenerierten Chunks, Laufzeit im Fenster [30 %, 400 %] der
   erwarteten Sprechzeit. Defekte Spuren werden **nicht geschrieben,
   nicht injiziert, nicht gecacht**.
3. **Cache-Wache** — auch WIEDERVERWENDETE Spuren durchlaufen das Gate
   gegen den aktuellen Artikeltext. Die deployten Pausen-Spuren werden
   beim nächsten Deploy erkannt, verworfen („Cache-Spur … verworfen“)
   und neu vertont — oder der Artikel bleibt ehrlich auf der
   Browser-Stimme.
4. **`RECIPE_VERSION` → `ff-voice-2026.09.06`** (ff_voice_backends.py)
   — invalidiert alle bestehenden (defekten) Caches weltweit.
5. Selbsttest von 54 auf **77 Prüfungen** erweitert: deploytes
   Defektmuster, Dauer-Lügen, Einzel-Lücken, Backend-Totalausfall
   (monkeygepatcht, offline), funktionierende Spur komplett.

### 3.3 Infrastruktur

* **`scripts/ff_voice_repair_test.mjs`** (jsdom, 55 Prüfungen) — pingt
  jede Reparatur einzeln fest: Spur-Abweisung vor Start, Laufzeit-
  Fallback, Ende-zu-früh-Fallback, ehrliches Ende, tote Synthese,
  stumme Engine, lazy Stimmkatalog, Pause/Resume/Sprung-Regression,
  deployte Defektmuster.
* **`scripts/ff_voice_browser_test.mjs`** (Playwright/Chromium,
  60 Prüfungen) — der „gründliche Funktionstest“ auf Echtgerät-Ebene:
  echte DOM, echte Timer, echtes rAF, **echte WAV-Datei im echten
  `<audio>`-Player** (selbst generiert, sprachähnlich moduliert),
  echte Web-Speech-API ohne Stimmen (Headless-Realität), steuerbare
  Engine-Attrappe mit realistischen Timern. Acht Szenarien S1–S8
  decken beide gemeldeten Symptome und alle Reparaturen ab.
  Browser-Suche: `FF_BROWSER_PATH` → Playwright-Cache (CI) →
  bundled `@sparticuz/chromium` (Sandbox); ohne Browser deutlicher
  Übersprung (Exit 0).
* **`tools/ff-voice-browser/`** — eigenes QA-Paket (playwright-core,
  @sparticuz/chromium) mit Package-Lock, analog zu tools/ff-voice-qa.
* **Lesehilfen-Gate (.github/workflows/lesehilfen-gate.yml)** —
  installiert Chromium (`npx playwright-core install --with-deps`) und
  lässt Reparatur-Pinne + Echt-Browser-Suite bei jedem Lesehilfen-Push,
  jedem PR und täglich laufen. **Bricht der echte Browser-Test, bricht
  das Gate.**
* **Altlasten beseitigt** (Rückbau-Wache hatte bereits gefordert):
  `scripts/reader_functional_test.mjs`, `scripts/reader_qa_lib.mjs`,
  `scripts/audio_pipeline_test.mjs`, `scripts/prepare_audio_chunks.mjs`,
  `scripts/mp3_join.mjs`, `scripts/audio_render_next.mjs`,
  `tools/reader-qa/` und der alte Gate-Snapshot
  `patches/lesehilfen-gate-2026-09-03-workflow-ready.yml` — alles
  Totcode des Gen-1-Readers, der eine nicht mehr existierende
  `ff-reader.js` lud.

### 3.4 Technische Randnotiz aus dem Testaufbau

`window.speechSynthesis` ist in Chromium ein **nur-lesbarer Accessor**
auf `Window.prototype` — eine einfache Zuweisung versagt STILL (die
Attrappe installierte sich nie, die Tests liefen gegen die echte,
stumme API). Die Suite installiert ihre Attrappe deshalb per
`Object.defineProperty`. Genau diese Klasse stiller Versager ist der
Grund, warum der Befund in jsdom unsichtbar war.

---

## 4 · Funktionstest (alles grün)

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-voice.js` | Syntax OK |
| `node scripts/ff_voice_functional_test.mjs` | **185/185** (inkl. aller echten Artikel) |
| `node scripts/ff_voice_voice_test.js` | **96/96** (männliche Stimme, DE/EN, ohne Umschalter) |
| `node scripts/ff_voice_repair_test.mjs` | **55/55** (neu — Reparatur-Pinne) |
| `node scripts/ff_voice_browser_test.mjs` | **60/60** (neu — echter Chromium, echtes Audio) |
| `python3 scripts/ff_voice_audio.py --selftest` | **77/77** (vorher 54) |
| `python3 scripts/ff_voice_backends.py --selftest` | **44/44** |
| `python3 scripts/ff_voice_parity_check.py` | **332/332** |
| `python3 scripts/ff_voice_toolbar_check.py` | **89/89** (vorher 85/89) |
| **Summe Lesehilfen-QA** | **938/938** |

Reproduktion des gemeldeten Fehlers nach der Reparatur (echtes
Chromium): Defekte Spur → ehrliche Abweisung **innerhalb 0,5 s**,
Gerätestimme übernimmt; tote Synthese → ehrlicher Stopp **innerhalb
0,5 s**, Fortschritt bleibt 0 %. Kein Auffrischen, kein Rennen, kein
Endlos-Zustand mehr.

## 5 · Wirkung beim nächsten Deploy

1. Der Deploy stellt die Tonspur-Generierung neu an (`RECIPE_VERSION`
   gebumpt); die defekten WAVs aus `gh-pages` bestehen das Cache-Gate
   nicht und verschwinden aus dem Veröffentlichungsstand.
2. Kann das Backend vertonen, gibt es erstmals **geprüfte** Spuren
   (vollständige Segmente, plausible Laufzeit); kann es nicht, bleibt
   der Reader auf der Browser-Stimme — hörbar, ehrlich, ohne 63 MB
   tote WAVs.
3. Selbst wenn erneut eine schlechte Spur ausgeliefert würde, lehnt der
   Reader sie clientseitig ab und liest mit der Gerätestimme vor.
