# VORLESEN-TON-REPARATUR-2026-09-07 — Der Ton ist zurück

**Datum:** 07.09.2026
**Gemeldeter Fehler (Produktion, unverändert seit 06.09.2026):**
„Die Vorlese-Funktion gibt keinen Ton aus, und die Fortschrittsanzeige
rennt viel zu schnell durch.“
**Auftrag:** dauerhaft reparieren **und** das Vorlese-Modell auf
High-End-Niveau robust machen.
**Betroffen:** FF Voice Studio (männliche Stimme, Deutsch und Englisch
ohne Umschalter) — Server-Kette *und* Reader.

> **Kernsatz dieses Befunds:** Am 06.09.2026 wurden die *Symptome*
> abgesichert (Wachen, Fallbacks, ein Gate gegen unplausible Spuren) —
> die *Ursache* blieb unentdeckt. Sie lautet in einem Satz:
> **`edge-tts` liefert einen MP3-Strom, die Kette schrieb ihn in eine
> `.wav`-Datei und las sie mit dem `wave`-Modul.** Jedes einzelne
> Segment scheiterte, veröffentlicht wurden 34 Tonspuren aus reiner
> Digitalstille. Kein Gate der Welt bringt so eine Spur zum Klingen —
> deshalb wurde diesmal die Kette selbst repariert, gemessen und gegen
> Rückfall verriegelt.

---

## 1 · Ursache, nachgewiesen statt vermutet

### 1.1 Die Server-Kette (der eigentliche Fehler)

| Schritt | Was passierte | Folge |
|---|---|---|
| `synth_edge()` | `edge-tts` schreibt **MP3** — gespeichert wurde als `…​.wav` | Datei ohne RIFF-Kopf |
| Messung | `wave.open()` auf dieselbe Datei | `Error: file does not start with RIFF id` |
| Fehlerbehandlung | Segment wurde still übersprungen | Spur = nur Inter-Block-Pausen |
| Veröffentlichung | Fingerprint-Cache übernahm die Stille | 34 stumme Spuren, `peak = 0`, 27,94 s statt ~10 min |

Damit ist auch das zweite Symptom erklärt: Wo keine Tonspur trägt,
springt der Reader auf die Browserstimme — und auf Geräten ohne
funktionierende Sprachsynthese (Linux ohne `speech-dispatcher`,
verwaltete Firmenbrowser, manche Android-WebViews) meldet die Engine
brav `onstart`/`onend`, **ohne zu sprechen**. Der Reader glaubte ihr und
schob den Balken in Sekunden auf 100 %.

### 1.2 Das Fehlerbild im Reader

* kein Ton,
* Fortschrittsbalken rast durch,
* am Ende die Meldung „Vorlesen beendet.“ — eine Unwahrheit.

---

## 2 · Die Reparatur in drei Schichten

### 2.1 Server · `scripts/ff_voice_backends.py` (Rezept `ff-voice-2026.09.07`)

Neu ist ein **formatunabhängiger Mess- und Dekodierbaukasten** — die
Kette rät nie mehr, was sie erzeugt hat, sondern sieht nach:

| Funktion | Aufgabe |
|---|---|
| `audio_kind()` / `is_riff_wav()` | erkennt MP3, WAV, OGG am Dateikopf |
| `decode_audio_mono()` | dekodiert über **ffmpeg** oder **miniaudio**, WAV auch nativ |
| `audio_stats()` | `peak`, `rms`, `audible_ratio`, `duration_ms` (gestreift, auch bei 10-Minuten-Spuren schnell) |
| `has_audible_speech()` | Urteil mit Begründung: Pegel `rms ≥ 60`, hörbarer Anteil `≥ 12 %` |
| `verify_segment()` | prüft **jedes** Segment sofort nach der Synthese |
| `synthesize(…, attempts, allow_engine_fallback)` | 3 Versuche, Backoff 0,8 s / 2,0 s, danach Engine-Wechsel |

Ein stummes Segment ist jetzt ein **Fehler mit Grund**, kein
`continue`. Fehlt jeder Dekoder, sagt `--engines` das im Klartext:
`edge-tts ist installiert, aber ohne Dekoder unbrauchbar`.

### 2.2 Server · `scripts/ff_voice_audio.py`

* `expected_speech_ms()` / `track_plausible()` — Laufzeit gegen den
  Artikeltext (15,2 Zeichen/s), keine 33-Sekunden-Spur für 10 Minuten Text.
* `audio_health(pfad, erwartet_ms)` — misst die fertige Datei.
* `verify_tracks(html_dir, out_dir, heal=True)` — Endkontrolle über den
  gesamten Veröffentlichungsstand. Was durchfällt, verliert Datei **und**
  Konfigurationsblock; der Reader nimmt dann sofort die Gerätestimme.
* Reparaturbefehl für die Hand:
  `python3 scripts/ff_voice_audio.py --verify --heal --html-dir public --out-dir public/audio/articles`

**Leitsatz:** Lieber eine ehrliche Browserstimme als eine stumme
Studiospur.

### 2.3 Reader · `static/premium/ff-voice.js` (Version `2026.09.07`)

| Härtung | Wirkung |
|---|---|
| **Physik-Deckel** (`SPEECH_FLOOR_CPS = 60`) | Der Balken kann der Wanduhr nicht davonlaufen: angezeigt wird höchstens `Startstand + 60 + Sekunden × 60` Zeichen. Kein rasender Balken mehr — konstruktiv unmöglich. |
| **Stumm-Sweep-Wache** | Wer schneller „spricht“, als Sprache physikalisch geht (≥ 2 Einheiten **und** ≥ 400 gemessene Zeichen), wird enttarnt: ehrlicher Stopp, Balken bleibt bei 0 %, Status benennt den fehlenden Ton — **nie** „Vorlesen beendet“. |
| **Zweistufige Sanft-Wache** | Verschlucktes `speak()` (bekanntes Chrome-Rennen) wird nach 1,5 s und 2,5 s **leise wiederholt**, statt Alarm zu schlagen. Erst nach 4,5 s ohne jedes Lebenszeichen greift die harte Stufe. |
| **Chrome-Keep-Alive** | `pause()`/`resume()`-Impuls im 9-Sekunden-Takt gegen den 15-Sekunden-Frost; nach dem Ende sofort still. |
| **Fortsetzen wiederholt die Einheit** | Nach Pause wird der unterbrochene Satz neu gesprochen — plattformgleich, nichts verschluckt (Safari „resumed“ ohne Ton). |
| **Hänger-Wache Tonspur** | Läuft der Player, steht aber seine Uhr (6 s), übernimmt die Gerätestimme am zuletzt gehörten Block. |
| **Stille-Sonde** | Web-Audio-Analyse der laufenden Spur: 2,5 s ohne Pegel ⇒ Übernahme durch die Gerätestimme. |
| **Haftende Begründung** | Der Grund einer Übernahme („Die Tonspur hängt – die Stimme deines Geräts übernimmt.“) bleibt 6 s stehen und wird nicht von Routinemeldungen überschrieben. Jede Bedienhandlung hebt die Sperre sofort auf. |
| **Diagnose** | `window.__ffVoice.diagnostics()` und `?ffvoice=debug` (Befund als Attribut `data-ff-voice-diagnostics` an der Leiste — die Seite schreibt nie in die Konsole). `?ffvoice=nostudio` erzwingt den Browserpfad. |

Neue Seiten-Schalter: `speechFloorCps` (`0` = Deckel aus), `audioProbe: false`.

---

## 3 · Absicherung: die Wachen laufen dauerhaft mit

Neue Suite **`scripts/ff_voice_tts_hardening_test.mjs`** (jsdom, echte
Engine-Datei, Sprach-Attrappe mit **echten Zeiten** und Wortgrenzen):

| Gruppe | Prüft |
|---|---|
| H1 | Stumm-Sweep (5000 Zeichen/s) ⇒ ehrlicher Stopp, Balken 0 % |
| H2 | schnell, aber möglich (40 Zeichen/s) ⇒ **kein** Fehlalarm |
| H3 | Physik-Deckel: Balken innerhalb der Wanduhr, aber in Bewegung |
| H4 | verschlucktes `speak()` ⇒ weicher Neustart mit demselben Text |
| H5 | Pause/Fortsetzen ⇒ genau eine Wiederholung, nichts verschluckt |
| H6 | Chrome-Keep-Alive ⇒ Impuls im Lauf, keiner nach dem Ende |
| H7 | hängende Tonspur ⇒ Gerätestimme übernimmt, Grund bleibt lesbar |
| H8 | Diagnose-Schnittstelle vollständig und belastbar |

**Stand aller Wachen (lokal, 07.09.2026):**

| Suite | Ergebnis |
|---|---|
| `ff_voice_functional_test.mjs` | 185/185 |
| `ff_voice_repair_test.mjs` | 56/56 |
| `ff_voice_tts_hardening_test.mjs` *(neu)* | 57/57 |
| `ff_voice_voice_test.js` | 96/96 |
| `ff_voice_parity_check.py` | 332/332 |
| `ff_voice_toolbar_check.py` | 93/93 |
| `ff_voice_audio.py --selftest` | 92/92 |
| `ff_voice_backends.py --selftest` | 67/67 |
| `ff_voice_browser_test.mjs` (echtes Chromium) | läuft im Gate |

---

## 4 · Veröffentlichungskette (`.github/workflows/deploy.yml`)

1. **Dekoder zuerst:** `ffmpeg` per `apt-get`, `miniaudio` als Reserve —
   ohne Dekoder ist `edge-tts` (MP3) wertlos. Genau dieser fehlende
   Baustein war die Ursache.
2. `--engines` protokolliert Engine, Rezept-Version **und** Dekoder.
3. Nach der Erzeugung: **`--verify --heal`** über den gesamten
   Veröffentlichungsstand, danach ein zweiter reiner Messlauf fürs
   Protokoll. Stumme Spuren erreichen die Leser nicht mehr.
4. Der Deploy bricht weiterhin **nie** wegen der Tonspur ab.

`ff_voice_toolbar_check.py` wacht ab sofort darüber, dass diese Schritte
im Workflow stehen bleiben und dass das Lesehilfen-Gate die neue Suite
ausführt.

---

## 5 · Was Leserinnen und Leser merken

* **Ton.** Entweder die Studiospur — oder, nachweisbar und sofort, die
  Stimme des Geräts. Nie mehr Stille mit laufendem Balken.
* **Ein ehrlicher Balken.** Er folgt der Uhr, nicht den Behauptungen der
  Engine.
* **Klare Ansagen.** Wenn etwas übernimmt, steht der Grund lesbar da.
* **Keine verschluckten Sätze** beim Pausieren und Fortsetzen.
* **Männliche Stimme, DE und EN, ohne Umschalter** — unverändert.

---

## 6 · Für den Störungsfall am fremden Gerät

```text
https://franksfinanzcheck.de/posts/…/?ffvoice=debug     → Befund als Attribut an der Leiste
https://franksfinanzcheck.de/posts/…/?ffvoice=nostudio  → Studiospur aus, Browserstimme testen
window.__ffVoice.diagnostics()                          → Version, Modus, Stimmen, Messwerte
```

`diagnostics()` meldet unter anderem `version`, `mode`, `trackReady`,
`trackPlausible`, `trackProbe`, `voiceCount`, `maleVoice`, `everStarted`,
`muteStop`, `speechFloorCps`, `measured` und `chromeKeepAlive`.
