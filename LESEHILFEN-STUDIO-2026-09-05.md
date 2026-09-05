# LESEHILFEN-STUDIO — Rückbau und Neubau der Vorlese-Funktion

**Datum:** 05.09.2026 · **Projekt:** FranksFinanzcheck · **Umfang:** Vollständiger Rückbau des alten TTS-Modells, Neubau auf Profi-Agentur-Niveau

---

## 1 · Auftrag

Das bestehende TTS-Modell (Vorlese-Funktion, männliche Stimme, Deutsch und Englisch ohne Umschalter) **vollständig entfernen** und danach ein **neues** Modell mit derselben Aufgabe auf **High-End-Level einer Profi-Agentur** aufbauen.

Umsetzung: Rückbau betrifft auch die **Kurzfassung** (beide Lesehilfen teilen sich Toolbar, Styling und Test-Infrastruktur). Die neue Architektur nutzt **zwei Tonpfade** (serverseitig vorvertonte MP3 + Browser-Engine als Fallback), und **Tests, Gates, CI und Doku** wurden vollständig neu gebaut und auf die neuen Dateien umgestellt.

---

## 2 · Rückbau — was entfernt wurde

### 2.1 Frontend

| Datei | Inhalt |
|---|---|
| `static/premium/ff-reader.js` | 4.386 Zeilen Reader-Engine (Vorlesen v7–v11 + Kurzfassung v5) |
| `assets/css/extended/ff-reader.css` | 756 Zeilen Styling |
| `layouts/_partials/reader_toolbar.html` | Toolbar-Markup |

### 2.2 Serverseite (Tonspur-Erzeugung)

| Datei | Inhalt |
|---|---|
| `scripts/generate_reader_audio.py` | 2.352 Zeilen Generator |
| `scripts/reader_tts_backends.py` | 2.237 Zeilen Stimmen-Kette, Aussprache, Prosodie |
| `scripts/reader_prosody_parity_check.py` | Paritäts-Gate |
| `scripts/reader_blocks_dump.py` | Block-Diagnose |
| `scripts/reader_voice_ab.py` | A/B-Hörtest |

### 2.3 Tests & Infrastruktur

`scripts/reader_functional_test.mjs`, `reader_qa_lib.mjs`, `reader_structure_loudness_test.mjs`, `reader_table_progress_test.mjs`, `reader_engine_check.js`, `reader_male_voice_highend_test.js`, `reader_parity_probe.js`, `reader_playback_function_test.js`, `reader_v7_function_test.js`, `summary_engine_check.js`, `tools/reader-qa/**`

### 2.4 Doku & Patches

`VORLESEN-HIGHEND-REPORT.md`, `VORLESEN-NATUERLICHKEIT-REPORT.md`, `VORLESEN-STRUKTUR-LAUTHEIT-REPORT.md`, `VORLESEN-TABELLEN-FETTDRUCK-FORTSCHRITT-REPORT.md`, `VORLESEN-ZEIT-STANDARD-REPORT.md`, `VORLESEN-deploy-fertig.yml`, `KURZFASSUNG-HIGHEND-REPORT.md`, `LESEHILFEN-REPARATUR-2026-09-04.md`, `patches/lesehilfen-gate-2026-09-04-*`

### 2.5 Nachlauf

- `layouts/single.html`, `layouts/_default/single.html`, `layouts/pillar/single.html` → Partial-Verweis auf `ff_voice_toolbar.html` umgestellt
- `.gitignore`, `README.md`, `.github/workflows/deploy.yml` bereinigt
- **Nachweis:** `scripts/ff_voice_toolbar_check.py` prüft dauerhaft, dass **keine Datei und keine Referenz** des alten Modells mehr existiert (Scan über `layouts`, `static`, `scripts`, `assets`, `content`, `tools`, `.github`, `docs`, `patches`).

---

## 3 · Neubau — FF Voice Studio

### 3.1 Dateien

| Datei | Zeilen | Aufgabe |
|---|---:|---|
| `static/premium/ff-voice.js` | ~2.600 | Reader-Engine: Dokumentmodell, Aussprache, Prosodie, Stimmen-Regie, zwei Tonpfade, Fortschritt, Kurzfassung |
| `assets/css/extended/ff-voice.css` | ~430 | Styling: Slot ohne Layout-Sprung, Mini-Player, Fortschritt, Dialog, Darkmode, Reduced-Motion, Print |
| `layouts/_partials/ff_voice_toolbar.html` | ~120 | Toolbar + Konfigurationsblock |
| `scripts/ff_voice_backends.py` | ~700 | Stimmen-Kette, Aussprache-Regie, Prosodie, WAV-Werkzeuge, Mastering |
| `scripts/ff_voice_audio.py` | ~900 | Generator: Block-Extraktion, Synthese, Zeitachse, Injektion, Cache |
| `scripts/ff_voice_qa_lib.mjs` | ~430 | Echte-DOM-Testfundament (jsdom) |
| `scripts/ff_voice_functional_test.mjs` | — | 145 Gates Funktionstest |
| `scripts/ff_voice_voice_test.js` | — | 71 Gates Stimmen-Regie |
| `scripts/ff_voice_parity_check.py` | — | 176 Gates Parität |
| `scripts/ff_voice_toolbar_check.py` | — | 89 Gates Infrastruktur & Rückbau |
| `scripts/ff_voice_probe.mjs` | — | Messfühler für das Paritäts-Gate |

### 3.2 Architektur

```
Seiten-HTML
    │
    ├─► Dokumentmodell     Anmoderation → Vorab-Boxen → DOM-Reihenfolge → Abmoderation
    │
    ├─► Aussprache-Regie   Schreibsprache ──► Sprechsprache (DE/EN getrennt)
    │
    ├─► Studio-Regie       Rolle × Dichte × Melodie ──► Tempo, Tonlage, Lautstärke, Pausen
    │
    ├─► Atemgruppen        Sätze ──► Konnektoren/Kommas ──► harte Obergrenze 220 Zeichen
    │
    └──► Transport
            ├─ (a) Studio-Tonspur   MP3 im HTML5-Player, Block-Zeitachse {b,t0,t1,lang}
            └─ (b) Browser-Engine   Web Speech, männliche Stimme, Watchdog & Retry
```

**Der kritische Punkt ist die Block-Parität.** Die Tonspur adressiert Blöcke über ihren Index `b`. Stimmt die Reihenfolge nicht exakt mit `collectBlocks()` des Readers überein, wandert die Live-Markierung am gesprochenen Text vorbei. Deshalb baut `extract_blocks()` (Python) dieselbe Reihenfolge serverseitig nach, und `ff_voice_parity_check.py` vergleicht beide Block für Block — über drei Fixtures und 30 Aussprache-Beispiele.

### 3.3 Was gegenüber dem alten Modell besser ist

| Thema | Alt | Neu |
|---|---|---|
| **Testfundament** | teils Fake-DOM, teils echte DOM; Suiten mit überlappenden Versionen (v7/v10/v11) | eine Bibliothek, **immer echte DOM**, eine Version |
| **Tabellen** | `<tfoot>`-Summen wurden im Generator nicht erkannt; Titel von Premium-Übersichten fehlten | `<tfoot>`, colspan, ARIA-Rollen und Titel über dem Tablewrapper – in **beiden** Implementierungen identisch |
| **Fettdruck** | konnte denselben Satz doppelt sprechen (Absatz **und** `<strong>`) | genau einmal, an seiner Stelle |
| **Blockquote** | wurde übersprungen, weil `closest()` auch das Element selbst traf | Vorfahren-Prüfung: das Zitat wird gelesen, sein Inhalt nicht doppelt |
| **Stimmen-Auswahl** | Teilstring-Vergleich („Sam“ traf „Samantha“) | Wort-Token, Frauen-Namen **zuerst** geprüft |
| **Test-Schnittstelle** | `mode` als Momentaufnahme | Getter; `buildTimeline()` sammelt Blöcke selbst |
| **Doku** | acht Reports mit Versionsgeschichte | **ein** Report, eine Wahrheit |

### 3.4 Stimmen (männlich, DE + EN, kein Umschalter)

| Backend | DE | EN | Bedingung |
|---|---|---|---|
| **edge** (Vorzug) | `de-DE-FlorianMultilingualNeural` | `en-US-AndrewMultilingualNeural` | kostenlos, kein Key, kein Konto |
| **edge** (Profil „narrator“) | `de-DE-ConradNeural` | `en-GB-RyanNeural` | kostenlos, kein Key |
| **piper** | `de_DE-thorsten-high` | `en_US-ryan-high` | offline, unbegrenzt, lizenzsauber |
| **groq** | — | Orpheus (nur EN) | nur als Notnagel, `GROQ_API_KEY` optional |

Multilingual-v2 spricht englische Fachbegriffe im deutschen Satz mit **derselben** Stimme – kein Timbresprung.

**Nie stumm.** Ist der Stimmen-Katalog beim Klick noch leer (Chromium, Safari und Android füllen ihn lazy), wird sofort mit der angeforderten Sprache gesprochen und beim Eintreffen des Katalogs auf die echte männliche Stimme angehoben. Warten würde das User-Activation-Token verbrennen und genau die Stummheit erzeugen, die dieses Modell ausschließt.

---

## 4 · Qualitätssicherung

| Suite | Gates | Prüft |
|---|---:|---|
| `ff_voice_functional_test.mjs` | 145 | Echte DOM: Toolbar, Lesereihenfolge, Tabellen, Aussprache DE/EN, Zweisprachigkeit, Atemgruppen, Wiedergabe/Pause/Sprung, Tonspur+Fallback, Kurzfassung, **alle 32 echten Artikel** |
| `ff_voice_voice_test.js` | 71 | 7 Geräte-Kataloge (macOS, Windows/Edge, Android, Google Cloud, Linux/eSpeak, nur Frauenstimmen, nur neutrale Stimmen) |
| `ff_voice_parity_check.py` | 176 | Tonspur ≡ Browser-Engine: 30 Aussprache-Beispiele, 3 Seiten-Fixtures Block für Block, Rollenprofile |
| `ff_voice_toolbar_check.py` | 89 | Partial-IDs, Einbindung in 3 Layouts, CSS-Klassen, Engine (First-Party, kein Tracking), Rückbau, Workflow |
| `ff_voice_backends.py --selftest` | 44 | Aussprache, Satzzerlegung, Prosodie, Stimmen, WAV-Werkzeuge |
| `ff_voice_audio.py --selftest` | 31 | Block-Extraktion, Determinismus, Fingerprint, HTML-Injektion, Artikelsuche |

**Stand:** alle Suiten grün (556 Gates).

**CI:** Der Workflow **„Lesehilfen-Gate (Vorlesen + Kurzfassung)“** führt alle Suiten bei jedem Push/PR auf Lesehilfen oder Content sowie täglich um 08:20 MESZ aus. Der Deploy erzeugt die Tonspuren inkrementell und **bricht nie wegen Audio ab**.

---

## 5 · Betrieb

```bash
# Tonspuren lokal erzeugen (nach hugo --minify)
python3 scripts/ff_voice_audio.py --html-dir public \
    --out-dir public/audio/articles --cache-dir /tmp/ff-voice-cache \
    --backend auto --profile natural --limit-new 25

# Nur prüfen, nichts schreiben
python3 scripts/ff_voice_audio.py --html-dir public --dry-run

# Diagnose
python3 scripts/ff_voice_audio.py --engines
```

**Wiederverwendung:** Unveränderte Artikel werden über einen Inhalts-Fingerprint (Rezept-Version, Backend, Stimme, Blocktexte) erkannt und 1:1 aus dem Cache übernommen. Ein Wechsel der Stimme oder des Rezepts erzeugt automatisch neue Tonspuren.

**Mastering:** Hochpass 80 Hz, Declick, Soft-Limit, EBU R128 −16 LUFS / −1,5 dBTP, MP3 64 kbit/s Mono 24 kHz. Ohne ffmpeg bleibt es bei einer sauber gemasterten WAV.
