# VORLESEN-ZEIT-STANDARD-REPORT — Vorab vertonte Artikel wie bei zeit.de (v7)

**Datum:** 03.09.2026
**Ziel:** Die Vorlese-Funktion klingt mit einer **männlichen Stimme in Deutsch und Englisch**
automatisch (ohne Umschalter) und **dauerhaft auf allen Geräten und Browsern** — iPhone, Mac,
Tablet, Android, PC; Chrome, Safari, Firefox, Edge.

---

## 1. Das Kernproblem (warum Web Speech allein nicht reicht)

Die lokale Web-Speech-API liest mit den Stimmen des **Betriebssystems**. Diese sind nicht
garantierbar:

- **Firefox** liefert auf vielen Linux-/Snap-Systemen eine **leere Stimmliste**
  (`getVoices() == []`) und kann daher gar nicht sprechen.
- **Safari/iOS** und **Android** stellen je nach Systemsprache oft **keine männliche deutsche
  Stimme** bereit.
- Die konkreten Stimmen (Name, Geschlecht, Sprache) unterscheiden sich **pro Gerät**.

Die bisherige Engine (v6) kann deshalb nur die beste **verfügbare** Stimme nehmen — eine
echte Garantie „männlich DE & EN auf jedem Gerät“ ist mit Web Speech technisch unmöglich.

## 2. Die Lösung: zeit.de-Modell (Vorab-Vertonung + HTML5-Audio)

zeit.de vertont Artikel **serverseitig** (aktuell ElevenLabs) und spielt sie in einem
**eingebauten Audio-Player** ab — die Tonspur ist auf jedem Endgerät identisch, weil sie nicht
vom Gerät erzeugt wird. Genau dieses Modell übernehmen wir:

1. **Generator** (`scripts/generate_reader_audio.py`): vertont jeden Artikel **vorab** mit der
   männlichen DE-Stimme `Fritz-PlayAI` und der männlichen EN-Stimme `Atlas-PlayAI` über
   Groq `playai-tts` (serverseitig gerendert → eine einzige, überall identische Tonspur).
   Deutsch und Englisch werden pro Satz automatisch erkannt und mit der jeweils passenden
   männlichen Stimme gesprochen (zweisprachiger Hörfunk-Moderator, wie die v6-Engine).
2. **Tonspur**: pro Artikel eine MP3 (`audio/articles/<slug>.mp3`, Mono, 24 kHz, 48 kbit/s,
   ffmpeg; ohne ffmpeg Fallback WAV) plus `audio/articles/<slug>.audio.json` mit den
   Zeitmarken je Block.
3. **Injektion**: der Generator schreibt die Tonspur-Konfiguration direkt in die gebaute HTML
   (`<script type="application/json" id="ff-reader-audio-config">{"audio":{src,chunks}}`).
4. **Reader** (`static/premium/ff-reader.js`, v7): bevorzugt die Tonspur im nativen
   `<audio>`-Element (Play/Pause/Stop, Abschnittssprung, Live-Markierung, Fortschritt,
   Sperrbildschirm/Media-Session) — **identisch auf allen Geräten**. Ohne Tonspur (z. B. noch
   nicht generiert) fällt er **automatisch und nahtlos** auf die lokale Web-Speech-Engine zurück.

### Garantie-Stufen

| Stufe | Pfad | Garantie |
|---|---|---|
| **1 (Standard, immer)** | lokale Web-Speech-Engine (v6/v7) | männliche Stimme DE & EN sofern das Gerät sie anbietet; sonst hörbarer Fallback + ehrliche Kennzeichnung |
| **2 (ZEIT-Standard)** | vorab vertonte Tonspur (Groq `playai-tts`) im HTML5-Player | **identische männliche DE-/EN-Stimme auf JEDEM Gerät/Browser** (HTML5-Audio ist überall nativ) |

Stufe 2 benötigt den Repo-Secret `GROQ_API_KEY`. **Ohne den Key bricht der Deploy nie ab** —
der Blog erscheint normal, Vorlesen nutzt Stufe 1.

---

## 3. Architektur & Datenvertrag

### `cfg.audio` (vom Generator in die HTML geschrieben)

```json
{
  "audio": {
    "src": "/audio/articles/hausratversicherung-kosten-leistungen-vergleich.mp3",
    "chunks": [
      { "b": 0, "t0": 0,    "t1": 4200, "lang": "de" },
      { "b": 1, "t0": 4200, "t1": 9200, "lang": "de" },
      { "b": 2, "t0": 9200, "t1": 11000, "lang": "en" }
    ]
  }
}
```

- `b` = 0-basierter Block-Index in der Lesereihenfolge (0 = Anmoderation, 1..N = Artikelblöcke
  in DOM-Reihenfolge, letzter = Abmoderation) — **exakt die Ordnung von `collectBlocks()`** im
  Reader. Der Generator ist ein 1:1-Port dieser Funktion (inkl. Tabellen, Boxen, Listen,
  Abmoderation), daher stimmen Audio-Zeitmarken und Live-Markierung immer überein.
- `t0`/`t1` = Millisekunden in der Tonspur.
- Fehlt `audio` (noch nicht generiert) → Web-Speech-Pfad aktiv.

### Generator-Aufruf

```bash
GROQ_API_KEY=… python3 scripts/generate_reader_audio.py \
  --html-dir public \
  --out-dir public/audio/articles \
  --cache-dir /tmp/ff-audio-cache \
  [--only <slug>] [--dry-run] [--force] [--format mp3|wav|auto] [--no-inject]

# Selbsttest ohne Netzwerk/Key:
python3 scripts/generate_reader_audio.py --selftest
```

### Inkrementalität (kein ständiges Neu-Vertonen)

Jeder Artikel bekommt einen **Inhalts-Fingerprint** (SHA-256 über normierte Blocktexte +
Stimmen + Modell + Generator-Version). Im Deploy werden die Tonspuren des **letzten
gh-pages-Stands** als Cache genutzt:

- unveränderter Artikel → Tonspur wird **1:1 wiederverwendet** (kein TTS-Aufruf),
- neuer/geänderter Artikel → wird **neu vertont**,
- ohne `GROQ_API_KEY` → nur Wiederverwendung, keine Neuvertonung, kein Deploy-Abbruch.

---

## 4. Deploy-Integration (`.github/workflows/deploy.yml`)

Neuer Schritt **nach** dem letzten `hugo --minify` und **vor** dem gh-pages-Deploy:

1. `generate_reader_audio.py --selftest` (nicht blockierend),
2. vorherige Tonspuren aus `origin/gh-pages` als Cache holen,
3. `generate_reader_audio.py --html-dir public --out-dir public/audio/articles --cache-dir …`
   mit `GROQ_API_KEY` aus dem Secret,
4. `peaceiris/actions-gh-pages` veröffentlicht `public/` inkl. `audio/`.

Die Tonspuren liegen damit **first-party auf demselben Ursprung** (GitHub Pages / Cloudflare) —
kein Drittanbieter-CDN, keine zusätzlichen Cookies.

> Einrichtung: In den Repository-Einstellungen unter *Settings → Secrets and variables → Actions*
> den Secret **`GROQ_API_KEY`** anlegen (Console: console.groq.com → API Keys). Danach gilt
> Stufe 2 automatisch für alle bestehenden und zukünftigen Beiträge und Ratgeberseiten.

---

## 5. Reparaturen in der v7-Engine (zusätzlich)

- **Universelles Pause/Resume**: Pause ist immer „Cancel + Position merken“, Resume spricht die
  aktuelle Einheit neu. Kein stilles „Resume“ mehr auf Safari/Android/Firefox.
- **Gehärteter Start-Watchdog**: feuert nur, wenn die Engine nachweislich stillsteht
  (weder `speaking` noch `pending`); eine langsam anlaufende Stimme wird nicht abgewürgt.
- **Keep-Alive-Wache** mit `unitInFlight`-Schutz (kein Doppel-Speak).
- **Sauberer Audio-Fallback**: `error`/nicht ladbare Tonspur → `audioMode` aus, `endReading`,
  Neustart über Web Speech an derselben Blockposition — niemals stumm.
- **Klick-to-Listen & Abschnittssprung** auch im Audiomodus (Block-Index → Zeitmarke).

## 6. Kurzfassung v5 (Lesbarkeit, ZEIT-Redaktionsniveau)

Der Kurzfassungs-Dialog in `assets/css/extended/ff-reader.css` wurde auf Redaktions-Typografie
gehoben: 680 px breiter Dialog, verfeinerte Header-/Body-/Footer-Abstände, größere
Zeilenabstände (Fließtext ≈ 1.68, Hero ≈ 1.7), Versalien-Sektionslabels, verbesserte
Zahlen-Karten/Inhaltsverzeichnis/Tabellen und neue Mobile-Breakpoints (600 px/480 px).

## 7. Verifikation

Alle Prüfungen grün (03.09.2026):

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `scripts/reader_engine_check.js` | 58 grün / 0 rot |
| `scripts/reader_male_voice_highend_test.js` | 36 grün / 0 rot |
| `scripts/reader_playback_function_test.js` | 12 grün / 0 rot |
| `scripts/reader_v7_function_test.js` | 15 grün / 0 rot (inkl. ZEIT-Audioplayer + Injektionspfad) |
| `scripts/summary_engine_check.js` | 26 grün / 0 rot |
| `scripts/reader_toolbar_check.py` | alle Prüfungen grün |
| `scripts/generate_reader_audio.py --selftest` | 20 grün / 0 rot (Block-Port, Sprache, WAV, Fingerprint, Injektion, Dry-Run) |

## 8. Bekannte Grenzen (ehrlich dokumentiert)

- **Kein Hugo/Browser in dieser Umgebung**: Ein realer `hugo --minify`-Build und ein
  Browser-/Gerätetest (Screenshot der Kurzfassung, echte MP3-Ausgabe, echter
  `<audio>`-Klickpfad in Chrome/Safari/Firefox) konnten hier nicht ausgeführt werden. Der
  Client-Code ist per VM-Tests verifiziert; die **finale Geräte-/Browser-Probe** steht aus und
  sollte nach dem ersten Deploy mit `GROQ_API_KEY` einmalig durchgeführt werden.
- **Erstgenerierung**: Beim ersten Deploy mit Key werden alle Artikel einmalig vertont
  (einmalige Groq-Kosten); danach inkrementell.
- **Stimmen-Wahl**: `Fritz-PlayAI` (DE) und `Atlas-PlayAI` (EN) sind die Defaults und per
  `FF_AUDIO_VOICE_DE` / `FF_AUDIO_VOICE_EN` umstellbar.
