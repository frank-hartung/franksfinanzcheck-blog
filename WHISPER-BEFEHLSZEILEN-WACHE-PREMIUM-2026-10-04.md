# 🔐 PREMIUM-REPORT: Whisper-Befehlszeilen-Wache (Code-Scanning-Alert 60)

> **Rollout 04.10.2026 · Auftrag Frank Hartung · Meldung #559 · Profi-Agentur-Niveau**
> **Leitlinie: Externe Werte erreichen nie ungeprüft eine Prozesszeile — dauerhaft, per Vertrag erzwungen.**

---

## 1. Auftrag & Befund

> „Potential fix for code scanning alert no. 60: Uncontrolled command line — #559.
> Bitte dauerhaft auf Premium-Level einer Profi-Agentur beheben.“

**Befund (CWE-78, „Uncontrolled command line“ / `py/command-line-injection`):**
In `scripts/whisper_engine.py` floss der Audiodatei-Pfad ungeprüft in die
Prozesszeile des whisper.cpp-Backends:

```python
cmd = [bin_path, "-m", f"models/ggml-{self.model}.bin", "-f", audio_path, "-l", language, "-oj"]
subprocess.run(cmd, ...)
```

**Das war kein theoretisches Laborergebnis, sondern ein realer Angriffspfad.**
Der n8n-Bridge-Server (`scripts/n8n_bridge.py`) nimmt HTTP-Webhooks an und
verarbeitet darin `audio_file`/`file_path` **direkt** an die Engine:

```
POST /  →  do_POST()  →  handle_inbound_payload()  →  daten["audio_file"]
       →  WhisperEngine.transcribe()  →  _transcribe_whisper_cpp()  →  argv
```

Wer den Bridge-Port erreicht, kontrollierte damit ein Prozessargument des
whisper.cpp-Aufrufs (Options-Verwechslung, beliebige Dateien als Eingabe,
Übersteuern von Ausgabepfaden). Zwei weitere Einträge mit demselben Muster:
CLI (`--input`, `--model`, `--language`) und die Inbox-Wache
(`process_inbox_directory`).

---

## 2. Reparatur-Architektur: vier Schichten

### Schicht 1 — Eingangs-Wacht (`_safe_audio_path`)

Ein einziges Tor, durch das **jeder** Aufrufer (CLI, Webhook, Inbox, Schaltwerk)
gehen muss, bevor irgendein Backend den Pfad sieht:

| Prüfung | Wirkung |
|---|---|
| `os.path.realpath` | absoluter, symlink-freier Kanon; `..`-Verschleierung und relative Pfade werden aufgelöst |
| NUL-Zeichen → `ValueError` | verhindert Format-String-/System-API-Missbrauch |
| Dateiname beginnt mit `-` → `ValueError` | schließt Options-Verwechslung aus |
| reguläre Datei erzwungen (echte Backends) | keine Verzeichnisse, Devices, FIFOs; Fehler bleibt `FileNotFoundError` wie bisher |
| **Verzeichnis-Confinement** (echte Backends) | Audiodateien liegen zwingend innerhalb vertrauenswürdiger Wurzeln: Repo (`BLOG_DIR`), System-Temp und optional `WHISPER_AUDIO_ROOTS` — ein Webhook-Pfad kann damit nie beliebige Host-Dateien als Transkriptionsquelle missbrauchen |
| Mock-Backend ausgenommen | hermetische Selbsttests & CI bleiben ohne Modell lauffähig |

`transcribe()` kanonisiert genau einmal und reicht **nur** den Kanon weiter —
auch an `res["file_path"]`, `verify_audio_parity` und alle Exporte.

### Schicht 2 — Deskriptor-Übergabe statt Pfad-Übergabe (Kernstück)

Das whisper.cpp-Backend öffnet die geprüfte Datei **selbst** und übergibt dem
Kindprozess ausschließlich einen Datei-Deskriptor:

```python
fd = os.open(safe_path, os.O_RDONLY)          # exakt der geprüfte Inode
assert stat.S_ISREG(os.fstat(fd).st_mode)     # schließt die Prüfen-Öffnen-Lücke
cmd = [bin_path, "-m", model_path, "-f", f"/proc/self/fd/{fd}", "-l", lang, "-oj", "-of", out_base]
subprocess.run(cmd, ..., pass_fds=(fd,))
```

Damit hält die finale Prozesszeile **strukturell keinen extern kontrollierten
Wert** mehr: Binary aus `shutil.which` (Literale), Modellpfad aus
Repo-Konstante + Whitelist, Sprache aus Whitelist, Audio als Deskriptor-Zahl,
Ausgabe-JSON in einem engine-kontrollierten Tempverzeichnis
(`-of …/whisper_cpp_…/transcript` statt bisher `<audio>.json` neben der
Quelle). Nebeneffekt: Der Kindprozess liest garantiert denselben Inode, den die
Wacht geprüft hat — ein Austausch des Pfades zwischen Prüfung und Ausführung
(TOCTOU) ist ausgeschlossen.

### Schicht 3 — Whitelists statt Freitext

* **Modell:** nur offizielle ggml-Namen (tiny … large-v3-turbo, distil-Varianten);
  der Modellpfad ist fest an `<Repo>/models/` gebunden und wird vor dem Start
  auf Existenz geprüft (freundlicher Download-Hinweis statt Absturz im Kindprozess).
  Gilt ausschließlich für das whisper.cpp-Backend — faster-whisper/openai-whisper
  behalten ihren offenen Modellnamensraum (kein Prozessstart, kein Angriffspfad).
* **Sprache:** Abbildung über das Whisper-Tokenizer-Vokabular (ISO-639-1 +
  „auto“ + deutsche/englische Aliasse); alles Unbekannte fällt **fail-safe auf
  „auto“** (Spracherkennung durchs Modell), statt beliebiges Freitext-Argument
  durchzureichen. Implementiert als `dict.get(raw, "auto")`: der Schlüssel kann
  das Ergebnis nie beeinflussen.

### Schicht 4 — Fail-closed überall

* Binary fehlt → `RuntimeError` (bisher: `None` als argv[0] → kryptischer TypeError).
* Fehlercode ≠ 0 oder fehlendes/unlesbares JSON → `RuntimeError` mit
  stderr-Schwanz (bisher: **stummer Leertext** — der schlimmste Ausfallmodus,
  weil er wie Erfolg aussieht).
* Segmenttexte werden vollständig verbunden (bisher wurde nur das erste
  Segment als Transkript zurückgegeben — latenter Teiltext-Bug mitbehoben).
* Webhook (`n8n_bridge.py`): abgelehnte Aufnahmen kippen den Server nicht mehr,
  sondern fallen auf Text/Fallback-Entwurf zurück; Quelldatei-Namen werden vor
  dem Frontmatter gehärtet (`whisper_audio_source`), damit externe Namen weder
  YAML noch Markdown brechen können.
* Inbox-Wache: eine abgelehnte Aufnahme blockiert die Warteschlange nicht —
  sie bleibt zur manuellen Prüfung liegen.
* CLI: saubere deutsche Fehlermeldungen mit Exit-Codes (2 = Eingangs-Wacht,
  3 = Backend) statt Traceback.

---

### Nachtrag (gleicher Tag): Pfad-Confinement schließt die Folge-Befunde

Der CodeQL-Lauf zum Pull Request bestätigte die Befehlszeilen-Reparatur (kein
„Uncontrolled command line“ mehr) und meldete als Folgebefunde zwei neue
**Pfad-Befunde (High)** desselben Webhook-Flusses — `os.path.isfile` und
`os.open` mit dem externen Pfad: Wer den Bridge-Port erreicht, könnte die
Engine beliebige Host-Dateien lesen lassen (Transkript landet im Webhook-Feedback
bzw. Entwurf). Das war kein neuer Fehler der Reparatur, sondern das gleiche
Eingangsproblem in der Datei-Zugriffsschicht — und wird mit derselben Disziplin
geschlossen: **Confinement auf vertrauenswürdige Wurzeln** (`str.startswith`-
Wächter, das von CodeQL als SafeAccessCheck anerkannte Muster) — als zweistufige
Wache: einmal in der Eingangs-Wacht vor der Backend-Weitergabe und zusätzlich
direkt am Dateizugriff jedes echten Backends (whisper.cpp-Deskriptor-Öffnung,
local-api-Upload-Lesung). Die Engine liest Audiodateien nur noch innerhalb des
Repos, des System-Temp-Verzeichnisses und per `WHISPER_AUDIO_ROOTS` freigegebener
Betreiber-Ordner. Das hermetische Mock-Backend bleibt ausgenommen (es öffnet
keine Dateien).

## 3. Bewusste Abweichung vom Copilot-Autofix (mit Beleg)

Der Autofix zu Meldung #559 schlug u. a. ein „`--`“ vor dem Dateiargument vor.
Das wurde **nicht** umgesetzt — nach Prüfung des whisper.cpp-Argument-Parsers
(`examples/cli/cli.cpp`, Stand 04.10.2026): Ein einzelnes „--“ ist dort kein
End-of-Options-Zeichen, sondern fällt in den Zweig
`error: unknown argument → whisper_print_usage → exit(0)`. Der Aufruf würde
also **mit Exit-Code 0 und leerem Ergebnis abbrechen** — der alte Code hätte
das als Erfolg mit leerem Transkript verbucht. Statt eines Schein-Trennzeichens
garantiert die Kombination aus absolutem Kanon (beginnt mit `/`), führendem
Bindestrich-Verbot und Deskriptor-Übergabe dieselbe Sicherheitsgarantie — ohne
funktionalem Bruch. Die übrigen Vorschläge des Autofixs (Kanonisierung,
Regular-Datei-Zwang, Bindestrich-Ablehnung, fail-closed Binary-Prüfung) sind
aufgegangen und verschärft worden.

## 4. Warum das Ergebnis den Scanner dauerhaft beruhigt

Die Analyse der aktiven CodeQL-Regel (`py/command-line-injection`,
Quelle: HTTP-Webhook-Payload via `BaseHTTPRequestHandler`) zeigt: Einzig
Konstantenvergleiche unterbrechen den Taint-Fluss; `realpath`/`isfile`-Prüfungen
alone tun das nicht. Deshalb greift die Reparatur tiefer — der externe Wert
**erscheint schlicht nicht mehr in der Prozesszeile** (Deskriptor-Zahl,
Whitelist-Konstanten, engine-eigene Temp-Pfade). Der Fluss ist strukturell
unterbrochen, nicht nur weggefiltert; das gilt für alle Eingänge gleichzeitig.

## 5. Beweise (alle grün)

| Verifikation | Ergebnis |
|---|---|
| `python3 scripts/whisper_engine.py --selftest` (inkl. neuer Abschnitt 6: Eingangs-Wacht & Prozesszeilen-Vertrag) | ✅ BESTANDEN |
| `npm run test:blogautomatik` (38 Unit-Tests: u. a. `TestEingangsWacht`, `TestVerzeichnisConfinement`, `TestWhisperCppProzessvertrag`, `TestInboxFehlerisolation`, `TestQuelldateiHaertung`, `TestSprachNormalisierung`) | ✅ 38/38 |
| `scripts/tests/test_command_execution_security.py` + neuer `WhisperEngineExternalPathContract` | ✅ inkl. „roher Pfad erreicht nie die Prozesszeile“ |
| Gesamtdiscovery `python3 -m unittest discover -s scripts/tests` | ✅ 1731 Tests OK |
| CI-Selbsttests (engine_generate, reserve_pool, cadence_guard, fm_boundary_guard ×2, social_studio, blogautomatik_orchestrator) | ✅ alle OK |
| CLI-Angriffsproben (`-angriff.mp3`, NUL-Pfad, fehlende Datei auf echtem Backend) | ✅ Exit 2 mit klarer Meldung, kein Prozessstart |

## 6. Betriebshinweise

* **Linux/macOS:** Deskriptor-Übergabe nutzt `/proc/self/fd` bzw. `/dev/fd`
  (beide im Standardbetrieb vorhanden). GitHub-Actions-Runner (ubuntu) laufen
  unverändert.
* **Windows:** Das whisper.cpp-Backend ist dort jetzt bewusst fail-closed
  gesperrt (kein `/dev/fd`-Kontrakt) und verweist auf faster-whisper. Franks
  dokumentierter Stack (Linux-Server, n8n/Docker, CI) ist nicht betroffen.
* **Eigene Aufnahme-Ordner:** Liegen Sprachaufnahmen außerhalb des Repos
  (z. B. `~/Aufnahmen`), werden sie über die Umgebungsvariable
  `WHISPER_AUDIO_ROOTS` (Doppelpunkt-getrennte Pfadliste) freigegeben —
  bewusste Betreiber-Entscheidung statt stiller Freigabe.
* **Modelle:** ggml-Dateien liegen wie bisher unter `models/` — jetzt
  auflösungsunabhängig vom Arbeitsverzeichnis (bisher brach der relative Pfad,
  wenn die Engine aus n8n/Schaltwerk heraus gestartet wurde).
* Das JSON-Ergebnis liegt während der Verarbeitung in einem privaten
  Tempverzeichnis und wird nach dem Einlesen vollständig entfernt — die Inbox
  wird nicht länger mit `<audio>.json`-Dateien zugemüllt.

## 7. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/whisper_engine.py` | Eingangs-Wacht, Deskriptor-Übergabe, Whitelists, fail-closed, Selftest-Abschnitt 6, CLI-Fehlerpfade, Frontmatter-Härtung, Inbox-Isolation |
| `scripts/n8n_bridge.py` | Webhook-Fehlerisolation um `transcribe()` |
| `scripts/tests/test_whisper_engine.py` | +23 Regressionstests (Eingangs-Wacht, Verzeichnis-Confinement inkl. Backend-Wächter, Prozessvertrag, Inbox, Frontmatter, Sprache) |
| `scripts/tests/test_command_execution_security.py` | +`WhisperEngineExternalPathContract` (2 Tests) gemäß SECURITY.md-Pflicht |
| `SECURITY.md` | Vertrag „Externe Dateipfade“ dokumentiert |
| `docs/ANLEITUNG-WHISPER-N8N-GITHUB-PAGES.md` | Abschnitt 7 „Sicherheits-Vertrag der Whisper-Engine“ |
| `CLAUDE.md` | Testzahl `test:blogautomatik` auf den realen Stand (31) korrigiert |

**Nachweispfad:** Pull Request mit `Closes #559`; Abschlussvermerk automatisch
über `vorgangs-abschluss.yml` beim Zusammenführen.
