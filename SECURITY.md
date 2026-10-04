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
   (reguläre Datei, keine NUL-Zeichen, kein Dateiname mit führendem „-“).
2. Statt des Pfades selbst wird nur ein geöffneter Datei-Deskriptor durchgereicht
   (`-f /proc/self/fd/<n>` mit `pass_fds`): Die Prozesszeile enthält strukturell
   keinen extern kontrollierten Wert, und der Kindprozess liest exakt den
   geprüften Inode (kein Zeitfenster zwischen Prüfung und Ausführung).
3. Modell-, Sprach- und sonstige Optionswerte stammen ausschließlich aus
   Whitelists im Betreibercode — unbekannte Werte werden abgelehnt (fail-closed).
4. Kein „--“-Trennzeichen bei Tools, deren Parser unbekannte Argumente abbricht
   (whisper.cpp beendet sich dann mit Exit-Code 0 und Usage-Text); dort schützt
   die Kombination aus Kanonisierung und Deskriptor-Übergabe.

