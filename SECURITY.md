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


## Zugangs-Namensvertrag (seit Code-Scanning-Alert #78, 05.10.2026)

Der Betrieb veröffentlicht laufend Statusberichte (Social-Preflight, Cockpit,
Redaktions-Scorecard, Governance-Kontrakt, Schaltwerk-Ereignisse) nach STDOUT,
in Markdown-Dateien und in JSON-Artefakte. Darin dürfen **Namen** von
Umgebungsvariablen stehen (`MASTODON_ACCESS_TOKEN`), **niemals deren Werte**.
Damit diese Trennung nicht nur gemeint, sondern lesbar und maschinell prüfbar
ist, gilt:

1. **Felder, die Variablennamen führen, heißen `pflicht_env` / `fehlende_env`**
   (in der stabilen JSON-Oberfläche: `required_env_names`, `missing_env_names`,
   `required_var_names`, `missing_var_names`). Felder, die Ampel- oder
   Nachweis-Metadaten führen, tragen das Präfix `zugang_` / `zugangsalter_`.
2. **Verboten als Namensbestandteil** in berichtsnahen Strukturen sind
   `secret`, `trusted`, `confidential`, `pass*` (`password`, `passcode`,
   `passphrase`, …), `oauth`, `api_key` / `api_tok` und `mfa` – das ist exakt
   die Menge, die CodeQLs `SensitiveDataHeuristics` als „führt Zugangsdaten“
   liest (reine Namensheuristik, auch für Funktionsnamen). Ein Name aus dieser
   Menge ist eine Behauptung über den Inhalt; wo nur Namen und Ampeln
   transportiert werden, ist sie falsch – für Menschen die Vorstufe eines
   echten Lecks, für die Analyse ein Befund.
3. **Werte bleiben draußen.** Kein Bericht darf den Inhalt einer
   Umgebungsvariablen in Ausgabe, Datei oder Artefakt tragen.
4. **Clear-Text-Funde werden nie unterdrückt.** Für die Regeln
   `py/clear-text-logging-sensitive-data` und
   `py/clear-text-storage-sensitive-data` gibt es keine `# codeql[...]`-
   Unterdrückung – sie stehen auch nicht in der Unterdrückungs-Whitelist der
   CodeQL-Wache. Funde dieser Klasse werden an der Quelle geheilt.

Erzwungen wird der Vertrag durch `scripts/tests/test_zugangs_namensvertrag.py`
(21 Tests, drei Beine): Er baut die CodeQL-Heuristik 1:1 nach und prüft damit
rekursiv jeden Schlüssel der erzeugten Berichtsstrukturen; er vergiftet
zusätzlich alle Zugangsvariablen mit einem Marker, der in keiner erzeugten
Ausgabe (Konsole, JSON, Markdown, Historie) auftauchen darf; und er verbietet
Clear-Text-Unterdrückungen im gesamten Bestand. Alle Beine tragen Gegenproben,
die fehlschlagen, wenn der Vertrag selbst stumpf wird.
Hintergrund und Fundstellen: `CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md`.
