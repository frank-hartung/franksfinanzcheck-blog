# 🎙️ ANLEITUNG: Whisper lokal + n8n self-hosted + GitHub Pages

> **0 € laufende Kosten · Premium-Vollautomatisierung auf Profi-Agentur-Niveau**  
> Stand: 03.10.2026 · Autor: Frank Hartung · FranksFinanzcheck.de

---

## 1. Architektur-Übersicht: Das 0 € Ökosystem

Dieses Setup eliminiert alle monatlichen SaaS-Kosten für Automatisierung, Spracherkennung, Content-Transformation und Hosting. Statt hunderte Euro für Zapier, Make, OpenAI API und Managed Hosting auszugeben, greifen drei eigenständige, hochperformante Open-Source-Säulen nahtlos ineinander:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      0 € LAUFENDE KOSTEN ARCHITEKTUR                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [ 📱 Smartphone / Diktat / Telegram / Audio-Aufnahme ]                │
│                                │                                        │
│                                ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  1. WHISPER LOKAL (100% On-Premise / 0 € API-Kosten)            │   │
│   │  · faster-whisper (CTranslate2) / OpenAI Whisper / whisper.cpp  │   │
│   │  · scripts/whisper_engine.py & Docker Container (Port 8765)     │   │
│   │  · Füllwort-Bereinigung, Glättung & 4K-Prüfpfad-Strukturierung  │   │
│   │  · Audio-QA & WebVTT-Untertitel-Generierung                     │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  2. n8n SELF-HOSTED (Workflow Orchestrator / 0 € Zapier-Ersatz) │   │
│   │  · Docker Compose Stack (tools/n8n/docker-compose.yml)          │   │
│   │  · Webhook-Verarbeitung, Scheduling & Daten-Routing             │   │
│   │  · 4 Produktions-Workflows in tools/n8n/workflows/              │   │
│   │  · Anbindung via scripts/n8n_bridge.py                          │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  3. GITHUB PAGES & SCHALTWERK (0 € Hosting & Redaktions-Engine) │   │
│   │  · Hugo SSG Build & Edge Delivery (franksfinanzcheck.de)        │   │
│   │  · Schaltwerk (scripts/schaltwerk.py) für Social Media & Wellen │   │
│   │  · Harte Qualitäts-Gates, ZEIT-Stil & Barrierefreiheit (CWV)    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Kostenvergleich: Eigener Stack vs. SaaS-Dienste

| Gewerk / Funktion | Klassische SaaS-Lösung | Kosten / Monat | Eigener Stack (0 €) | Kosten / Monat |
|---|---|---|---|---|
| **Workflow-Automatisierung** | Zapier Professional / Make Pro | 79,00 € | n8n Self-Hosted (Docker) | **0,00 €** |
| **Spracherkennung / Diktate** | OpenAI Whisper API / Descript | 45,00 € | Whisper lokal (`faster-whisper`) | **0,00 €** |
| **Omnichannel Social Dispatch** | Buffer / Hootsuite / Zapier | 40,00 € | Schaltwerk + n8n Omnichannel | **0,00 €** |
| **Webhosting & CDN** | Managed WP Engine / Kinsta | 64,00 € | Hugo + GitHub Pages | **0,00 €** |
| **Uptime & Health Monitoring** | Datadog / StatusCake | 40,00 € | Blog Health Watchdog (n8n/Python) | **0,00 €** |
| **GESAMT** | | **268,00 € / Monat** | | **0,00 € / Monat** |
| **JÄHRLICHE ERSPARNIS** | | | | **3.216,00 € / Jahr** |

---

## 3. Schnellstart in 3 Schritten

### Schritt 1: Docker-Stack starten
Im Verzeichnis `tools/n8n/` liegt die vollständige Docker Compose Konfiguration:

```bash
cd tools/n8n
./start.sh
```

Dienste sind sofort erreichbar:
- **n8n Webhook- & UI-Zentrale:** `http://localhost:5678`
- **Lokaler Whisper-API-Server:** `http://localhost:8765/health`

### Schritt 2: Workflows in n8n importieren
Öffne `http://localhost:5678` im Browser und importiere die vier produktionsfertigen JSON-Dateien aus `tools/n8n/workflows/`:
1. `1_voice_memo_to_blog_draft.json` (Voice-Memo & Diktat zu Hugo Blogartikel)
2. `2_blog_publish_omnichannel_dispatcher.json` (Publish-Welle & IndexNow)
3. `3_content_health_and_monitoring.json` (Täglicher Content-Health-Watchdog)
4. `4_audio_tts_and_whisper_qa.json` (TTS Audio-QA & Sprachparität)

### Schritt 3: Selbsttest aller 3 Säulen ausführen
```bash
npm run blogautomatik:selftest
```
Ergebnis:
```
🎉 Alle Whisper-Engine Selbsttests BESTANDEN!
🎉 Alle n8n-Bridge Selbsttests BESTANDEN!
✅ Schaltwerk-Selbsttest bestanden (11 Regeln, 14 Trigger, 12 Aktionen).
🎉 Alle Master-Orchestrator Selbsttests BESTANDEN!
```

---

## 4. Die Workflows im Detail

### Workflow 1: Voice-Memo zu Blogartikel-Entwurf
- **Auslöser:** Frank sendet ein Sprachmemo unterwegs per Telegram-Bot, iOS-Kurzbefehl oder Datei-Drop in `data/whisper_inbox/`.
- **Lokale Transkription:** Der lokale Whisper-Container (`whisper-api`) transkribiert die Audiodatei ohne ein Byte an Cloud-Dienste zu senden (100% DSGVO-konform).
- **Redaktionelle Veredelung:** `scripts/whisper_engine.py` filtert Füllwörter („äh“, „sozusagen“, „halt“), glättet die Syntax und baut den Artikel nach dem **4K-Prüfpfad** (Kosten sehen, Konditionen rechnen, Kündigungsfenster sichern, Kurs halten) auf ZEIT-Niveau auf.
- **Hugo-Entwurf:** Die Markdown-Datei wird unter `content/drafts/<slug>/index.md` mit fertigem Frontmatter und WebVTT-Untertiteln abgelegt.

### Workflow 2: Omnichannel Social Dispatcher & IndexNow
- **Auslöser:** Deploy-Ereignis oder Webhook nach Veröffentlichung eines Artikels.
- **IndexNow Instant-Indexierung:** Meldet neue URLs direkt per API an Bing und Yandex (0 €).
- **Schaltwerk Social Wave:** Verteilt den Artikel mit optimierten Snippets an Mastodon, Bluesky und Telegram.

### Workflow 3: Content-Health & System-Monitoring
- **Auslöser:** Täglich um 07:00 Uhr via n8n Cron.
- **Prüfung:** Führt `scripts/blog_health_gate.py` und Latenz-Pings aus.
- **Fail-Safe Alarmierung:** Bei Fehlern oder toten Links wird sofort ein Alarm über `scripts/alert_router.py` an Telegram / GitHub Issues abgesetzt.

### Workflow 4: Audio-TTS & Whisper Paritäts-QA
- **Auslöser:** Nach Vertonung eines Artikels durch `scripts/ff_voice_audio.py`.
- **Gegenprobe:** Lokales Whisper hört die generierte MP3-Tonspur ab und vergleicht das Transkript mit dem Blogartikel.
- **Qualitäts-Gate:** Bei Paritätswerten unter 65% wird Alarm geschlagen, um Aussprachefehler sofort zu stoppen.

---

## 5. Smartphone-Integration (iOS & Android)

### Option A: iOS Kurzbefehl (Apple Shortcuts)
1. Neuen Kurzbefehl „Diktat an FranksFinanzcheck“ anlegen.
2. Aktion: **Diktieren** oder **Audio aufnehmen**.
3. Aktion: **Inhalte von URL abrufen**:
   - URL: `https://dein-n8n-server.de/webhook/voice-memo`
   - Methode: `POST`
   - Body: Form-Data (`data` = Aufnahmedatei, `kategorie` = „strom-gas“)
4. Fertig: Ein Klick auf dem iPhone genügt, um eine Sprachnotiz in einen vollständigen Blog-Entwurf zu verwandeln.

### Option B: Telegram Bot
Über den Telegram-Node in n8n kann Frank Sprachnachrichten direkt an seinen privaten Telegram-Bot senden. n8n lädt die `.oga`/`.mp3`-Datei herunter, schickt sie an Whisper und legt den Artikel im Blog ab.

### Option C: Ordner-Überwachung (data/whisper_inbox/)
Audio-Dateien einfach in `data/whisper_inbox/` werfen und ausführen:
```bash
npm run whisper:inbox
```

---

## 6. CLI-Kommandoreferenz

| Befehl | Zweck |
|---|---|
| `npm run blogautomatik:status` | Zeigt den Live-Status aller drei Säulen |
| `npm run blogautomatik:audit` | Zeigt das Kosten- und Einsparungs-Audit |
| `npm run blogautomatik:pipeline` | Führt die End-to-End Voice-to-Draft Pipeline aus |
| `npm run blogautomatik:selftest` | Prüft alle Systeme offline auf Herz und Nieren |
| `npm run whisper:inbox` | Verarbeitet wartende Audiodateien in `data/whisper_inbox/` |
| `npm run n8n:ping` | Misst Latenz und Erreichbarkeit von n8n |
| `npm run test:blogautomatik` | Führt alle 31 Unit-Tests aus (inkl. Eingangs-Wacht & Prozesszeilen-Vertrag, Meldung #559) |

---

## 7. Sicherheits-Vertrag der Whisper-Engine (Meldung #559 / Code-Scanning-Alert 60)

Der 04.10.2026 hat die Prozesszeilen der Engine auf Agentur-Niveau gesichert.
Gilt für alle Eingänge — CLI, n8n-Webhook (`n8n_bridge.py`) und Inbox-Wache:

1. **Eingangs-Wacht (`_safe_audio_path`):** Jeder Audiodatei-Pfad wird vor der
   Backend-Weitergabe zu einem absoluten, symlink-freien Kanon aufgelöst
   (`os.path.realpath`). NUL-Zeichen und Dateinamen mit führendem „-“ werden
   abgelehnt (Schutz vor Options-Verwechslung); für echte Backends muss eine
   vorhandene, reguläre Datei existieren. Abgelehnte Aufnahmen blockieren die
   Inbox-Verarbeitung nicht, sondern bleiben zur manuellen Prüfung liegen.
2. **Deskriptor-Übergabe statt Pfad-Übergabe:** Das whisper.cpp-Backend öffnet
   die geprüfte Datei selbst und reicht dem Kindprozess ausschließlich
   `-f /proc/self/fd/<n>` (Linux) bzw. `/dev/fd/<n>` (macOS) mit `pass_fds`
   durch. Externe Werte stehen damit strukturell nicht mehr in der Prozesszeile,
   und der Kindprozess liest exakt den geprüften Inode (TOCTOU-sicher).
   Ein „--“-Trennzeichen wird bewusst nicht gesetzt — der whisper.cpp-Parser
   bricht bei unbekannten Argumenten ab.
3. **Whitelists:** Modellnamen (offizielle ggml-Namen, Modellpfad fest an
   `<Repo>/models/`) und Sprachwerte (Whisper-Tokenizer-Vokabular, fail-safe
   „auto“) kommen nur aus ENGINE-KONSTANTEN, nie aus der Anfrage.
4. **Fail-closed:** Fehlen Binary, Modell-Datei oder JSON-Antwort, oder endet
   whisper.cpp mit Fehlercode, wird abgebrochen — keine stummen Leertexte.
   Abgelehnte Webhook-Pfade fallen auf Text/Fallback-Entwurf zurück, statt den
   Bridge-Server zu kippen.

**Regressionsschutz (dauerhaft):** `npm run test:blogautomatik` (u. a.
`TestEingangsWacht`, `TestWhisperCppProzessvertrag`) und der übergreifende
Sicherheitsvertrag `scripts/tests/test_command_execution_security.py`
(`WhisperEngineExternalPathContract`) blockieren jede Rückkehr roher Pfade in
eine Prozesszeile. Hintergrund und Beweise:
`WHISPER-BEFEHLSZEILEN-WACHE-PREMIUM-2026-10-04.md`.
