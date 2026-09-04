# VORLESEN-NATUERLICHKEIT-REPORT — die männliche Stimme klingt wie ein Mensch (v9)

**Datum:** 04.09.2026
**Ziel:** Vorlese-Funktion **kostenlos** deutlich natürlicher machen — **männliche Stimme**, **Deutsch und Englisch**, **ohne Sprach-Umschalter**.
**Produktivcode:** `static/premium/ff-reader.js` (Browser-Pfad) · `scripts/reader_tts_backends.py` + `scripts/generate_reader_audio.py` (Tonspur) · `.github/workflows/deploy.yml` (Automatik)
**Vorgänger:** `VORLESEN-HIGHEND-REPORT.md` (v6, Reparatur des Klickpfads) — dieser Report beschreibt die **Klang**-Stufe.

---

## 1. Befund: Warum es bisher nach Maschine klang

| Problem | Auswirkung |
|---|---|
| Der Vertonungs-Backend „Groq playai-tts" ist zum **31.12.2025 abgeschaltet** worden | Der Pfad für vorab vertonte Artikel lieferte **kein Deutsch** mehr; der Ersatz (Orpheus) kann nur Englisch |
| Fallback war ausschließlich die **Web Speech API** des Betriebssystems | Stimme = die Blechstimme des Geräts: auf Android/Windows oft `espeak`-Klasse, auf iOS/Google „Compact"-Varianten |
| **Ein** Sprecher pro Sprache, aber Satz-für-Satz neu gewählt | Englische Fachbegriffe im deutschen Satz kippten in eine andere Stimme → hörbarer **Timbresprung** mitten im Satz |
| Zahlen, Währungen, Daten, Abkürzungen gingen **unbearbeitet** an die Engine | „1.299,50 €" wurde als „eins Punkt zwei neun neun…" gelesen, „z. B." als „z Punkt B", „§ 35 SGB II" als „Paragraph Zeichen" |
| Alle Blöcke mit **gleicher Prosodie** gesprochen | Überschriften klangen wie Fließtext, Warnboxen wie Aufzählungen — monoton, kein Rhythmus |
| Keine Lautheits-Normierung | Leise Sätze neben lauten; unterwegs regelt niemand nach |

**Kurz:** Nicht die Technik war kaputt, sondern es fehlte die **Regie** — und ein Sprachdienst, der Deutsch in Neural-Qualität **ohne Abo** liefert.

---

## 2. Entscheidung: kostenlose Backend-Kette (ohne Key-Pflicht)

Neu ist eine Kette, die **ohne Konto, ohne Abo und ohne Pflicht-API-Key** auskommt. Der Deploy probiert sie in dieser Reihenfolge und nimmt das erste verfügbare Backend:

```
edge  →  Microsoft-Edge-Neuralstimmen über das Open-Source-Paket edge-tts (7.2.8)
piper →  lokale ONNX-Stimmen über piper-tts (1.7.0), offline & unbegrenzt
groq  →  nur als Englisch-Notnagel, falls GROQ_API_KEY gesetzt ist (nie Pflicht)
```

### Stimmen (alle männlich, je Profil und Backend)

| Profil | Backend | Deutsch | Englisch |
|---|---|---|---|
| **natural** (Voreinstellung) | edge | `de-DE-FlorianMultilingualNeural`, `de-DE-ConradNeural`, `de-DE-BerndNeural` … | `en-US-AndrewMultilingualNeural`, `en-US-BrianMultilingualNeural`, `en-GB-RyanNeural` … |
| **natural** | piper | `de_DE-thorsten-high`, `de_DE-thorsten-medium`, `de_DE-karlsson-low` | `en_US-ryan-high`, `en_GB-alba-medium`, `en_US-lessac-medium` |
| **narrator** (Erzähler) | edge | `de-DE-ConradNeural`, `de-DE-FlorianMultilingualNeural` … | `en-GB-RyanNeural`, `en-US-GuyNeural`, `en-US-ChristopherNeural` … |
| **narrator** | piper | `de_DE-thorsten-high`, `de_DE-thorsten-medium` | `en_GB-alba-medium`, `en_US-ryan-high` |
| (Notnagel) | groq | — (kein Deutsch) | `daniel`, `troy`, `austin` … |

**Warum „natural" die Voreinstellung ist:** Die **Multilingual-v2**-Stimmen (`Florian`, `Andrew`) sprechen englische Fachbegriffe *innerhalb* eines deutschen Satzes **mit derselben Stimme**. Genau das ist der häufigste Verräter bei Finanzblogs („Der ETF-Sparplan…“), und es ist der größte Einzelhebel für „klingt nach Mensch“.

**Warum Piper die zweite Stufe ist:** 100 % lokal, kein Dienst, keine Kontingente, keine Datenübertragung — und die Thorsten-Stimme gilt als beste freie deutsche Männerstimme. Qualität etwas unter Edge, dafür ausfallsicher und lizenzklar.

### Datenschutz (ehrlich)

| Backend | Datenfluss | Kosten |
|---|---|---|
| edge-tts | Artikeltext geht an den Microsoft-Sprachdienst (kein Konto, kein Key, keine Karte) | 0 € |
| piper | **bleibt auf dem Build-Runner** — keine Übertragung | 0 € |
| groq | Artikeltext (nur Englisch) an Groq, API-Key nötig | Free-Tier, ~100 Anfragen/Tag |

Wer keinerlei Textübertragung will, fährt `--backend piper` und hat trotzdem eine männliche DE-/EN-Stimme.

---

## 3. Die zehn Natürlichkeits-Hebel

1. **Ein Sprecher pro Artikel, nie pro Satz.** Die Backend-Wahl wird je Sprache **einmal** getroffen und für den ganzen Beitrag beibehalten (`Engine.by_lang`). Stimmenwechsel innerhalb eines Artikels klingt sofort nach Maschine.

2. **Multilingual v2 für Code-Switching.** „Der ETF-Sparplan kostet 25 € — the fees are lower than expected." wird von `Florian`/`Andrew` **durchgehend** gesprochen. Kein Timbresprung, kein zweiter Sprecher.

3. **Satzgenaues DE/EN-Routing — ohne Umschalter.** Jeder Satz wird einzeln erkannt (`sniff_lang`). Die Regel ist **bewusst konservativ**: Ein deutscher Absatz kippt nicht wegen eines englischen Fachbegriffs, ein echter englischer Satz wird aber englisch gesprochen. Mehrdeutige Token (`in`, `so`, `per`, `was`, `die`) fehlen in den Lexika absichtlich — sie waren die häufigste Fehlerquelle.
   **Wichtig:** Dieselbe Logik läuft im Browser-Pfad (`ff-reader.js`) und in der Tonspur (`reader_tts_backends.py`), mit **identischen Lexika** (146 EN-/196 DE-Tokens) und identischer Entscheidungsregel. Das Paritäts-Gate erzwingt das.

4. **Vollständige Aussprache-Normalisierung** (`speech_normalize`, Rezept `ff-norm-v2`):
   Zahlen → Wörter (`1299` → „eintausendzweihundertneunundneunzig"), Währungen (`1.299,50 €` → „eintausendzweihundertneunundneunzig Euro und fünfzig Cent"), Prozent, Kommazahlen, Tagesdaten (`12.08.2026` → „zwölfter August zweitausendsechsundzwanzig"), Jahreszahlen in deutscher Sprechweise, Abkürzungen (`z. B.`, `u. a.`, `bzw.`), Akronyme (`ETF` → „E T F"), URLs als Kurzform („Link zu check24 Punkt de"), römische Ziffern in Paragrafen (`§ 35 SGB II` → „SGB zwei"), Telefonnummern, Maßeinheiten.
   **Reihenfolge:** erst Sprach-Routing, **dann** Normalisierung — englische Sätze bekommen englische Zahlenregeln.

5. **Rollen-Prosodie statt Einheitsbrei.** Jede Block-Rolle hat Tempo, Tonlage, Lautstärke und Pausen (`PROSODY`, Rezept `ff-prosody-v4`) — **identisch** in Tonspur und Browser:

   | Rolle | Tempo | Tonlage | Lautstärke | Pause davor/danach |
   |---|---|---|---|---|
   | `h2` | 0.90 | 0.88 | 1.00 | 620 / 340 ms |
   | `h3` | 0.92 | 0.90 | 1.00 | 460 / 260 ms |
   | `p` | 1.00 | 0.96 | 1.00 | 130 / 190 ms |
   | `lead` | 0.96 | 0.95 | 1.00 | 180 / 260 ms |
   | `li` | 1.00 | 0.97 | 0.99 | 110 / 150 ms |
   | `blockquote` | 0.95 | 0.95 | 0.96 | 340 / 320 ms |
   | `callout` | 0.95 | 0.93 | 1.00 | 380 / 320 ms |
   | `warning` | 0.90 | 0.86 | 1.00 | 460 / 380 ms |
   | `table-row` | 1.02 | 0.97 | 0.98 | 90 / 210 ms |
   | `intro` / `outro` | 0.92 | 0.92 | 1.00 | 0 / 520 · 520 / 0 ms |

   Tiefere Tonlage + langsameres Tempo bei Überschriften = die klassische Sprecherroutine. Warnboxen werden **deutlich** gesetzt (0.90/0.86), Tabellenzeilen leicht schneller (1.02), damit Zahlenkolonnen nicht einschläfern.

6. **Rhythmus: Pausen, Trimmen, Mikro-Fades.** Neural-Engines liefern 200–500 ms „tote Luft" pro Satz. Die wird gekappt (`trim_silence`) und durch die **rollengerechte** Pause ersetzt (Obergrenze 900 ms, sonst wirkt es zerrissen). Jede Einheit bekommt ein 3-ms-Mikro-Fade — das entfernt die Klicks an den Schnittstellen, die sonst wie Schluckauf klingen.

7. **Mastering auf Podcast-Norm (EBU R128).** Hochpass 70 Hz (nimmt das Rumpeln), Ziellautheit **−16 LUFS**, True-Peak-Grenze **−1,5 dB**, Mono 24 kHz, MP3 mit 48 kbit/s (Sprache braucht nicht mehr). Ohne `ffmpeg` greift zumindest die Peak-Normalisierung — besser als unbearbeitet.

8. **Satzmelodie: Fragen steigen, Ausrufe betonen.** Ein Artikel, der nur aus Feststellungen besteht, klingt wie ein Kontoauszug — deshalb wird jeder Satz auf seine **Emotion** geprüft (`sentence_emotion`, Rezept `ff-prosody-v4`): Endet er auf `?`, wird er minimal **höher** gesprochen (+0,05 Tonlage) und erhält **mehr Pausenraum** (+80 ms, `EMO_AFTER_MS`); `!` bekommt +0,02 Tonlage und +50 ms. Gelesen wird er minimal ruhiger. **Parität:** Dieselbe Logik läuft im Browser-Pfad (`proseSentences` → `autoPitch`, `pauseAfterChunk`, `effectiveRateFor` — exakt +0,05/+0,02 Tonlage und +80/+50 ms), damit Tonspur und Web-Speech nicht auseinanderlaufen. Fragen/Ausrufe bleiben eigene Sprecheinheiten, Feststellungen werden im Browser zu Atemgruppen gebündelt.

9. **DC-Offset entfernen (Knackschutz an Schnittstellen).** Neural-Engines und Konvertierungsschritte hinterlassen oft einen kleinen konstanten Versatz der Wellenform um die Nulllinie (`dc_offset_remove`, Rezept `ff-backends-v3`). Zwei beim Überblenden antreffende Segmente beginnen dann nicht bei 0 und erzeugen an der Schnittstelle hörbare **Knackser**. Das Subtrahieren des Mittelwerts ist verlustfrei und bleibt ein No-Op, solange der Offset unter 8 LSB liegt (kein „Aufdrehen" von Rauschen).

10. **Broadband-Denoise gegen Grund- und Zischrauschen.** Ein Hochpass allein entfernt nur das tiefe Brummen. `broadband_denoise_wav` (ffmpeg `afftdn=nr=9:nf=-32:tn=1`, Rezept `ff-backends-v3`) senkt das Rauschband über die gesamte Sprachbreite — konservativ (nr=9), damit die Stimme lebendig bleibt. Drei Fallback-Stufen (`afftdn=nr=9:nf=-32:tn=1` → `afftdn=nr=9` → `afftdn` → unverändert), damit auch ältere ffmpeg-Builds ein Ergebnis liefern; ohne ffmpeg bleibt der Puffer unverändert und das Mastering (Hochpass, DC-Offset, Lautheit) greift trotzdem.

### Zusätzliche Absicherung: Nur-Männlich-Garantie (v8)

Die Stimmenwahl im Browser-Pfad ist verschärft worden, weil eine naive Namenserkennung **weibliche** Stimmen als männlich durchwinken konnte:

- **Female-Veto zuerst.** Trifft ein Frauenname zu (`Katja`, `Emma`, `Ava`, `Anna`, `Seraphina`, `Petra`, `Elke` …), ist die Stimme raus — auch wenn derselbe Name männliche Teile enthält.
- **Sicherer Neural-Matcher.** Ein Namensteil gilt nur dann als Stimme, wenn er **≥ 10 Zeichen** lang ist **und** auf `neural`, `neural2`, `multilingual`, `natural`, `online`, `wavenet` oder `journey` endet. Damit trifft `ConradNeural` und `FlorianMultilingualNeural` — aber `ava` in „Avai­lable" oder `nora` in „Norbert" **nie** mehr.
- **Qualitäts-Rangliste** (`PREMIUM_TIERS`): `multilingual` 85 > `natural` 70 > `neural`/`wavenet`/`journey` 60 > `studio`/`enhanced`/`premium` 50 > `online` 40 > `siri`/`google` 30. Nur die **beste** Stufe zählt (keine Addition) — sonst gewinnt ein Sammelsurium aus Mittelklasse-Merkmalen.
- **Desktop-Fallback bleibt männlich:** Findet ein Gerät gar keine Neural-Stimme, wird trotzdem explizit nach `male`/`#male`/bekannten Männernamen gefiltert, statt die System-Standardstimme zu nehmen.

---

## 4. Robustheit: Der Deploy darf nie wegen der Tonspur brechen

| Schutz | Wirkung |
|---|---|
| **Vorab-Test** (`Engine.preflight()`) | Ein Testwörtchen je Sprache, **bevor** Artikel abgearbeitet werden. Ist der Dienst down, wird die Neuvertonung im Lauf übersprungen — statt 25 Artikel × 19 Sätze × Wiederholungen (Minuten ohne Ergebnis) |
| **Schutzschalter** (`MAX_CONSECUTIVE_FAILURES = 6`) | Fällt der Dienst mitten im Artikel aus, wird abgebrochen; Wiederholung/Wartezeit nur beim ersten Fehler |
| **Keine lückenhaften Tonspuren** | Fehlt auch nur ein Satz, wird **keine** Datei geschrieben — der Reader bleibt beim Browser-Fallback. Lieber komplett gesprochen als ein Satz, der fehlt (`--keep-partial` zum Erzwingen) |
| **Inkrementell + Fingerprint** | Unveränderte Artikel werden aus dem letzten `gh-pages`-Stand wiederverwendet. Der Fingerprint enthält Text **und** Rezept (Stimme, Prosodie, Lautheit, `ff-norm-v2`/`ff-prosody-v4`/`ff-backends-v3`) — wer die Stimme wechselt, bekommt neu vertont, statt alte und neue Tracks zu mischen |
| **`--limit-new 25`** | Begrenzt die Neuvertonung je Lauf (Gratis-Kontingente, CI-Zeit). Wiederverwendung aus dem Cache bleibt unbegrenzt. Im manuellen Deploy per `audio_backfill` aufhebbar |
| **`|| echo …`** | Jeder Audio-Schritt ist nicht-blockierend; der Deploy läuft weiter |
| **Browser-Fallback** | Ohne Tonspur greift automatisch die Web-Speech-Regie (v6/v7) — dieselbe Prosodie, dieselbe männliche Stimmenwahl, dasselbe DE/EN-Routing |

---

## 5. Bedienung

### Im Deploy (GitHub Actions → „Run workflow")

| Input | Bedeutung |
|---|---|
| `audio_backend` | `auto` (Voreinstellung: edge → piper → groq), oder fest `edge` / `piper` / `groq` |
| `audio_profile` | `natural` (Multilingual v2, Voreinstellung) oder `narrator` (Conrad/Ryan) |
| `audio_backfill` | `true` = **alle** fehlenden Tonspuren neu vertonen (hebt das 25er-Limit auf) |

### Lokal

```bash
pip install edge-tts            # kostenlose Neuralstimmen (braucht ffmpeg fürs MP3)
pip install piper-tts           # alternative: lokale Offline-Stimmen

# Auskunft: welche Backends/Stimmen sind verfügbar?
python3 scripts/generate_reader_audio.py --engines --backend auto --profile natural

# Alles neu vertonen (nach `hugo --minify`)
python3 scripts/generate_reader_audio.py --html-dir public \
        --out-dir static/audio/articles --backend auto --profile natural --force

# Nur ein Artikel, ruhigeres Tempo, Erzähler-Profil
python3 scripts/generate_reader_audio.py --only stromvergleich --profile narrator --rate 0.94
```

### A/B-Hörtest — entscheiden mit den Ohren

„Natürlicher" ist eine Hör-Entscheidung, keine Messgröße. Deshalb:

```bash
python3 scripts/reader_voice_ab.py --open
```

vertont **denselben** Text mit jeder verfügbaren Stimme und legt `tmp/ab/index.html` an (in `.gitignore` — nichts wird veröffentlicht). Vergleichbar sind Backend × Profil × Tempo, auf Wunsch auch **mit/ohne Regie** (`--no-prosody-variant`), damit man hört, was Prosodie und Pausen bringen. Probetexte: `finanz` (Zahlen/Währungen/Daten), `gemischt` (Code-Switching), `english`.

**Nach der Entscheidung** das Gewünschte im Deploy eintragen (`audio_profile`) oder dauerhaft in `scripts/reader_tts_backends.py → VOICE_PRESETS` vorziehen.

---

## 6. Testmatrix

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `python3 scripts/reader_prosody_parity_check.py` (neu: JS ≡ Tonspur) | **94/94 grün** |
| `python3 scripts/generate_reader_audio.py --selftest` | **80/80 grün** (inkl. CLI-Integration, Vorab-Test, Schutzschalter) |
| `python3 scripts/reader_tts_backends.py --selftest` | **68/68 grün** (inkl. Satzmelodie, DC-Offset, Denoise) |
| `node scripts/reader_engine_check.js` | **58/58 grün** |
| `node scripts/reader_male_voice_highend_test.js` | **58/58 grün** (Abschnitt 8: Multilingual/Neural/Stufen, Female-Veto) |
| `node scripts/reader_playback_function_test.js` | **12/12 grün** |
| `node scripts/reader_v7_function_test.js` | **15/15 grün** |
| `node scripts/summary_engine_check.js` | **26/26 grün** |
| `python3 scripts/reader_toolbar_check.py` | **Alle Gates grün** |
| `.github/workflows/deploy.yml` | YAML gültig, 24 Schritte, Audio-Schritte nicht-blockierend |

**Was das Paritäts-Gate prüft** (`scripts/reader_prosody_parity_check.py` + `scripts/reader_parity_probe.js`): Rollen-Prosodie identisch, Sprach-Lexika **exakt** gleich, dieselbe Sprach-Entscheidung für dieselben Sätze in beiden Pfaden, die Stimmen der Tonspur sind im Reader als männlich hinterlegt (Frauennamen werden dort aussortiert), der Reader-Vertrag `{src, chunks:[{b,t0,t1,lang}]}` wird eingehalten (keine Satz-/Wortdaten in der HTML), Injektions-ID stimmt überein, Deploy kommt ohne Pflicht-Key aus. **Driften Tonspur und Browser-Pfad auseinander, wird es rot** — genau das verhindert „auf dem Handy klingt es anders als auf dem Mac".

---

## 7. Grenzen — ehrlich benannt

1. **Kein Live-Rendering in dieser Arbeitsumgebung.** Der Microsoft-Sprachdienst und Hugging Face (Piper-Stimmen) sind hier blockiert, `ffmpeg` fehlt. Alle Prüfungen laufen daher mit **Stub-Synthese** (echte Sinustöne, echte Pipeline) und mit den Selbsttests. Die erste echte Hörprobe entsteht im Deploy oder lokal nach `pip install edge-tts`.
2. **`ffmpeg` entscheidet über MP3 und Lautheit.** Ohne `ffmpeg` gibt es WAV (24 kHz Mono) und nur Peak-Normalisierung statt −16 LUFS. Im Deploy ist `ffmpeg` auf dem Ubuntu-Runner vorhanden; lokal ggf. nachinstallieren.
3. **edge-tts ist ein inoffizieller Zugang** zum Edge-Sprachdienst. Microsoft kann Kontingente oder Stimmen ändern. Deshalb die Kette mit Piper als zweiter Stufe und dem Browser-Fallback als dritter — ein Ausfall kostet Klang, nie Funktion.
4. **Web Speech bleibt die Notstufe.** Ohne Tonspur ist die Qualität geräteabhängig; die Nur-Männlich-Garantie gilt dort nur, soweit das Gerät eine männliche Stimme anbietet (sonst startet der Reader hörbar mit der Locale-Stimme und kennzeichnet den Fallback ehrlich).
5. **Piper-Stimmen sind groß** (je ~60–110 MB) und liegen in `.cache/ff-tts/` (gitignored). Im Deploy werden sie je Lauf geladen — bei `--backend piper` lohnt ein Actions-Cache, falls die Laufzeit stört.

---

## 8. Nächste Schritte (optional, alle kostenlos)

Mit v9 sind drei weitere Kostenlos-Hebel eingebaut (Satzmelodie, DC-Offset-Entfernung, Broadband-Denoise). Da „natürlicher" eine Hör-Entscheidung ist, lohnt ein A/B-Vergleich **mit und ohne** diese Effekte, bevor sie dauerhaft bleiben.

1. **Hörprobe A/B fahren** (`scripts/reader_voice_ab.py --open`) und `natural` gegen `narrator` entscheiden — bei Finanz-Ratgebern gewinnt erfahrungsgemäß `narrator` (Conrad) für lange Texte, `natural` (Florian) für Texte mit vielen englischen Begriffen.
2. **Actions-Cache für Piper-Stimmen** ergänzen, falls `piper` als feste Stufe genutzt wird (spart ~1–2 min je Deploy).
3. **Kapitelmarken** aus `h2`-Positionen in die Sidecar-JSON schreiben und im Player als Sprungmarken anbieten (die Timeline liegt bereits vor; die HTML bleibt schlank).
4. **`audio_backfill` einmalig auf `true`** stellen, um den Bestand zu vertonen; danach wieder auf `false`.


---

## 9. Anhang: `.github/workflows/deploy.yml` (Änderung zum Einspielen)

Der Bot dieser Arbeitsumgebung darf keine Workflow-Dateien pushen
(`workflows`-Berechtigung fehlt), deshalb liegt die Änderung hier **wortgleich**
zum Einfügen. Zwei Stellen:

**Stelle 1 — `workflow_dispatch` bekommt drei Eingaben** (manuelle Deploys steuerbar):

```yaml
  workflow_dispatch:
    inputs:
      audio_backfill:
        description: 'Vorlese-Audio: alle fehlenden Tonspuren neu vertonen (sonst max. 25 je Lauf)'
        type: boolean
        default: false
      audio_backend:
        description: 'TTS-Backend für die Vorlese-Tonspur'
        type: choice
        default: auto
        options: [auto, edge, piper, groq]
      audio_profile:
        description: 'Stimmen-Profil (natural = Multilingual v2, narrator = Conrad/Ryan)'
        type: choice
        default: natural
        options: [natural, narrator]
```

**Stelle 2 — die Audio-Schritte** ersetzen den alten, auf `GROQ_API_KEY` angewiesenen
Block; sie stehen **nach** `hugo --minify` und **vor** `Deploy auf gh-pages`:

```yaml
      # ================= VORLESE-AUDIO (ZEIT-Standard, v8 04.09.2026) ========
      # Vorab vertonte Artikel mit einer MÄNNLICHEN DE-/EN-Stimme – wie bei
      # zeit.de. Die Tonspur (MP3) läuft über das native HTML5-<audio>-Element
      # und klingt damit IDENTISCH auf iPhone, Mac, Tablet, Android, PC und in
      # jedem Browser, unabhängig von den Stimmen des Betriebssystems.
      #
      # KOSTENLOS & OHNE KEY (v8): Groq hat playai-tts am 31.12.2025
      # abgeschaltet, der Ersatz (Orpheus) kann kein Deutsch. Neu ist deshalb
      # eine Backend-Kette ohne Abo und ohne Pflicht-Secret:
      #   edge  → Microsoft-Edge-Neuralstimmen via Open-Source-Paket edge-tts
      #           (de-DE-FlorianMultilingualNeural / en-US-AndrewMultilingual-
      #           Neural, männlich; Multilingual v2 spricht englische
      #           Fachbegriffe im deutschen Satz ohne Timbresprung)
      #   piper → lokale ONNX-Stimmen (de_DE-thorsten-high / en_US-ryan-high),
      #           offline, unbegrenzt, lizenzsauber
      #   groq  → nur EN-Notnagel, falls GROQ_API_KEY gesetzt ist
      #
      # Robustheit: (1) Ohne verfügbares Backend wird keine Tonspur
      # geschrieben; der Reader fällt automatisch auf die lokale Browser-
      # stimme zurück – der Deploy bricht NIEMALS wegen der Tonspur ab.
      # (2) Inkrementell: unveränderte Artikel werden per Inhalts-Fingerprint
      # (inkl. Stimmen-/Rezept-Version) aus dem letzten gh-pages-Stand
      # wiederverwendet. (3) --limit-new begrenzt die Neuvertonung je Lauf,
      # damit ein Backfill den Deploy nicht zum Stundenjob macht.
      - name: Vorlese-Audio-Selbsttests (Generator + Stimmen-Kette + Parität)
        run: |
          python3 scripts/generate_reader_audio.py --selftest || echo "⚠ Generator-Selftest – Funde im Log (kein Deploy-Stopp)"
          python3 scripts/reader_tts_backends.py --selftest || echo "⚠ Backends-Selftest – Funde im Log (kein Deploy-Stopp)"
          python3 scripts/reader_prosody_parity_check.py || echo "⚠ Paritäts-Gate – Funde im Log (kein Deploy-Stopp)"

      - name: TTS-Backend installieren (edge-tts, optional piper-tts)
        run: |
          # edge-tts: kostenlos, kein Key, männliche Neuralstimmen DE/EN.
          python3 -m pip install -q edge-tts 2>/dev/null \
            || python3 -m pip install -q --break-system-packages edge-tts \
            || echo "⚠ edge-tts nicht installierbar → Piper/Browser-Fallback"
          # piper-tts: lokale Offline-Stimmen als lizenzsichere zweite Stufe.
          python3 -m pip install -q piper-tts 2>/dev/null \
            || python3 -m pip install -q --break-system-packages piper-tts \
            || echo "⚠ piper-tts nicht installierbar → edge/Browser-Fallback"
          ffmpeg -version | head -1 || echo "⚠ ffmpeg fehlt → nur WAV ohne Mastering"
          python3 scripts/generate_reader_audio.py --engines \
            --backend "${{ github.event.inputs.audio_backend || 'auto' }}" \
            --profile "${{ github.event.inputs.audio_profile || 'natural' }}" || true

      - name: Vorlese-Audio generieren (männliche DE/EN-Stimme, kostenlos)
        env:
          # Optional: nur als EN-Notnagel nötig, nie Pflicht.
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          FF_PIPER_VOICES: /tmp/ff-piper-voices
        run: |
          mkdir -p /tmp/ff-audio-cache /tmp/ff-piper-voices
          # Vorherige Tonspuren vom letzten Deploy holen (inkrementell).
          if git fetch --quiet origin gh-pages:refs/remotes/origin/gh-pages 2>/dev/null; then
            git restore --source=origin/gh-pages -- audio/articles 2>/dev/null || true
            if [ -d audio/articles ]; then
              cp -r audio/articles/. /tmp/ff-audio-cache/ 2>/dev/null || true
              rm -rf audio
            fi
          fi
          if [ "${{ github.event.inputs.audio_backfill }}" = "true" ]; then
            LIMIT_NEW=0
          else
            LIMIT_NEW=25
          fi
          python3 scripts/generate_reader_audio.py \
            --html-dir public \
            --out-dir public/audio/articles \
            --cache-dir /tmp/ff-audio-cache \
            --backend "${{ github.event.inputs.audio_backend || 'auto' }}" \
            --profile "${{ github.event.inputs.audio_profile || 'natural' }}" \
            --limit-new "$LIMIT_NEW" \
            || echo "⚠ Vorlese-Audio unvollständig – Deploy läuft weiter (Browser-Fallback aktiv)"
          echo "✅ Vorlese-Audio-Schritt abgeschlossen."
```

Wer es per Patch einspielen will: Die Änderung liegt auf dem Arbeitszweig
`arena/01a06c52-franksfinanzcheck-blog` als eigener Commit
(`git cherry-pick`/`git push` mit eigenem Token genügt).

### Kontrollfragen nach dem Einspielen

| Frage | Erwartung |
|---|---|
| Braucht der Deploy ein Secret? | **Nein** — `GROQ_API_KEY` ist optional (nur EN-Notnagel) |
| Bricht der Deploy ab, wenn kein Backend installierbar ist? | **Nein** — jeder Schritt endet mit `|| echo …`; der Reader nutzt die Browser-Stimme |
| Wie lange dauert die Tonspur? | Vorab-Test + max. 25 Neuvertonungen je Lauf; Wiederverwendung aus dem Cache ist unbegrenzt |
| Wie wird der Bestand vertont? | Einmalig „Run workflow" mit `audio_backfill = true` |
