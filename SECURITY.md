# Sicherheitsrichtlinie

## Sicherheitslücken vertraulich melden

Bitte veröffentliche Sicherheitslücken **nicht** als öffentliches Issue.
Nutze stattdessen GitHubs private Sicherheitsmeldungen:

1. Öffne **Security → Advisories → New draft security advisory**.
2. Beschreibe Auswirkung, betroffene Dateien/Versionen und – soweit möglich – eine Reproduktion.
3. Teile keine Zugangsdaten, Tokens, personenbezogenen Daten oder Newsletter-Adressen in Logs oder Screenshots.

Falls private Meldungen auf GitHub nicht angeboten werden, kontaktiere den Betreiber über die im Impressum der Website genannte Adresse und kennzeichne die Nachricht mit „VERTRAULICH – SECURITY“.

## Reaktionsziel

- Eingangsbestätigung: möglichst innerhalb von 3 Werktagen
- Erste Risikobewertung: möglichst innerhalb von 7 Werktagen
- Veröffentlichung: erst nach Bereinigung oder abgestimmter Frist

## Unterstützte Version

Unterstützt wird ausschließlich der aktuelle Stand des Default-Branches `main` und die daraus veröffentlichte Website.

## Geheimnisse

GitHub-Tokens, API-Schlüssel und Newsletter-Geheimnisse gehören ausschließlich in GitHub Actions Secrets bzw. die dafür vorgesehene Betriebsumgebung. Ein versehentlich veröffentlichtes Geheimnis muss sofort widerrufen und ersetzt werden; das bloße Entfernen aus der Git-Historie genügt nicht.

## Prozessstarts

Produktive Python-Skripte starten externe Programme ausschließlich mit expliziten Argumentvektoren (`subprocess.run([...], shell=False)`). Shell-Ausführung (`shell=True`, `os.system`, `os.popen`) ist untersagt: dynamische Werte wie Slugs, Workflow-Namen und Pfade müssen jeweils ein einzelnes Argument bleiben und, wo sinnvoll, vorab validiert oder URL-kodiert werden.

Der Regressionstest `scripts/tests/test_command_execution_security.py` erzwingt diese Regel für alle produktiven Skripte. Änderungen an einem Prozessstart müssen diesen Test erweitern und dürfen keine Ausnahme von der Regel einführen.

### Externe Dateipfade (seit Meldung #559 / Code-Scanning-Alert 60, 04.10.2026)

Werden einem externen Programm Dateipfade aus offenen Eingängen (Webhook, CLI,
Inbox-Verzeichnis) übergeben, gilt ein verschärfter Vertrag, erzwungen durch
`WhisperEngineExternalPathContract` im selben Regressionstest:

1. Der Pfad wird vor der Übergabe zu einem absoluten Kanon aufgelöst und geprüft
   (reguläre Datei, keine NUL-Zeichen, kein Dateiname mit führendem „-“) und
   liegt zwingend innerhalb vertrauenswürdiger Verzeichnis-Wurzeln (Repo,
   System-Temp, optional `WHISPER_AUDIO_ROOTS`) — ein Webhook-Pfad kann damit
   keine beliebigen Host-Dateien als Eingabe missbrauchen.
2. Statt des Pfades selbst wird nur ein geöffneter Datei-Deskriptor durchgereicht
   (`-f /proc/self/fd/<n>` mit `pass_fds`): Die Prozesszeile enthält strukturell
   keinen extern kontrollierten Wert, und der Kindprozess liest exakt den
   geprüften Inode (kein Zeitfenster zwischen Prüfung und Ausführung).
3. Modell-, Sprach- und sonstige Optionswerte stammen ausschließlich aus
   Whitelists im Betreibercode — unbekannte Werte werden abgelehnt (fail-closed).
4. Kein „--“-Trennzeichen bei Tools, deren Parser unbekannte Argumente abbricht
   (whisper.cpp beendet sich dann mit Exit-Code 0 und Usage-Text); dort schützt
   die Kombination aus Kanonisierung und Deskriptor-Übergabe.

## Klartext-Logging sensibler Daten (seit Code-Scanning-Alert #77, verschärft mit #80, 05.10.2026)

Für `py/clear-text-logging-sensitive-data` und `py/clear-text-storage-sensitive-data` gilt im
gesamten Repository ein Namensvertrag, erzwungen durch `scripts/clear_text_logging_guard.py`
(„Klartext-Wache") und `scripts/tests/test_clear_text_logging_security.py`:

1. **Bezeichner sagen die Wahrheit.** Ein Name darf nur dann nach Geheimnis klingen
   (`secret`, `password`, `oauth`, `api_key`, …), wenn er tatsächlich Geheimmaterial trägt.
   Listen von Variablen-NAMEN heißen `pflicht_env`/`fehlende_env`
   (JSON-Oberfläche: `required_env_names`/`missing_env_names`), Befund-Listen heißen nach dem
   Befund (`c9_klartext_leck`), nicht nach dem Gesuchten.
2. **Echte Werte erreichen keine Ausgabe.** Zulässig sind Status-Strings (`vorhanden`/`FEHLT`),
   SHA-256-Kurzhashes (`hash16`), Fingerabdrücke und Positiv-Whitelists sicherer Telemetriefelder.
3. **Unterdrückung ist keine Heilung.** Ein `# codeql[py/clear-text-…]`-Kommentar ist für diese
   beiden Regeln untersagt und gilt der Wache selbst als Befund: Das GitHub-Default-Setup liest
   weder `paths-ignore` noch Inline-Kommentare – ein so „stillgelegter" Fund bleibt ein offener Alert.
4. **Jede Änderung ist bewacht.** Der CI-Job `klartext-wache` (`.github/workflows/codeql.yml`) läuft
   unabhängig vom SARIF-Upload über alle Python-Dateien und blockiert fail-closed.

Hintergrund, Beweisführung und Runbook: `CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md`.

